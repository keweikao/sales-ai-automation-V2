"""
Quality scoring helpers for the transcription pipeline.

Implements FR-010 quality scoring requirements by evaluating several
dimensions of the transcription output:

- Language detection confidence
- Text coherence (average segment length)
- Character-per-second ratio
- Repetition detection
- Speaker separation coverage (when diarization is enabled)
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, median
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class QualityComponent:
    """Represents a single quality metric component."""

    name: str
    score: float
    value: float
    details: Dict[str, float]


DEFAULT_WEIGHTS = {
    "language_confidence": 0.2,
    "coherence": 0.2,
    "char_time_ratio": 0.2,
    "repetition": 0.2,
    "speaker_separation": 0.2,
}


def calculate_transcription_quality(
    merged_result: Dict,
    chunk_results: Iterable[Dict],
    audio_info: Dict,
    diarization_enabled: bool,
) -> Dict[str, object]:
    """
    Compute composite transcription quality score (0-100).

    Args:
        merged_result: Final merged pipeline output containing `segments`,
            `full_text`, and `statistics`.
        chunk_results: Per-chunk transcription results (before merging).
        audio_info: Metadata extracted from ffprobe.
        diarization_enabled: Whether speaker diarization was requested.

    Returns:
        Dictionary containing overall quality score, component breakdown,
        and diagnostic metrics.
    """
    segments: List[Dict] = merged_result.get("segments", [])
    statistics: Dict = merged_result.get("statistics", {})
    total_duration: float = (
        float(statistics.get("total_duration") or 0.0)
        or float(audio_info.get("duration") or 0.0)
    )
    full_text: str = merged_result.get("full_text", "")

    chunk_results_list: List[Dict] = list(chunk_results)

    components: List[QualityComponent] = []

    # 1. Language confidence -------------------------------------------------
    language_probs: List[float] = [
        float(r.get("language_probability"))
        for r in chunk_results_list
        if r.get("success") and r.get("language_probability") is not None
    ]
    language_confidence = mean(language_probs) * 100 if language_probs else 0.0
    components.append(
        QualityComponent(
            name="language_confidence",
            score=_clamp(language_confidence, 0, 100),
            value=language_confidence,
            details={
                "avg_language_probability": language_confidence / 100 if language_confidence else 0.0,
                "detected_language": _most_common_language(chunk_results_list),
            },
        )
    )

    # 2. Coherence score -----------------------------------------------------
    cleaned_segments = [seg for seg in segments if seg.get("text")]
    segment_lengths = [len(seg["text"].strip()) for seg in cleaned_segments]
    avg_segment_len = mean(segment_lengths) if segment_lengths else 0.0
    med_segment_len = median(segment_lengths) if segment_lengths else 0.0
    coherence_score = _bounded_score(
        value=avg_segment_len,
        lower_opt=12.0,
        upper_opt=80.0,
        lower_min=4.0,
        upper_max=160.0,
    )
    components.append(
        QualityComponent(
            name="coherence",
            score=coherence_score,
            value=avg_segment_len,
            details={
                "avg_segment_chars": avg_segment_len,
                "median_segment_chars": med_segment_len,
                "segment_count": len(segment_lengths),
            },
        )
    )

    # 3. Character-per-second ratio -----------------------------------------
    characters = len(full_text.replace(" ", "").replace("\n", ""))
    char_per_second = (characters / total_duration) if total_duration > 0 else 0.0
    char_time_score = _bounded_score(
        value=char_per_second,
        lower_opt=2.3,
        upper_opt=4.2,
        lower_min=1.0,
        upper_max=6.5,
    )
    components.append(
        QualityComponent(
            name="char_time_ratio",
            score=char_time_score,
            value=char_per_second,
            details={
                "total_characters": characters,
                "audio_duration_seconds": total_duration,
                "characters_per_second": char_per_second,
            },
        )
    )

    # 4. Repetition detection ------------------------------------------------
    unique_ratio, duplicate_ratio = _compute_uniqueness_ratio(cleaned_segments)
    repetition_score = max(0.0, 100.0 - duplicate_ratio * 150.0)
    components.append(
        QualityComponent(
            name="repetition",
            score=repetition_score,
            value=unique_ratio,
            details={
                "unique_segment_ratio": unique_ratio,
                "duplicate_segment_ratio": duplicate_ratio,
            },
        )
    )

    # 5. Speaker separation --------------------------------------------------
    if diarization_enabled and cleaned_segments:
        assigned_count = sum(
            1
            for seg in cleaned_segments
            if seg.get("speaker") and seg.get("speaker") != "Speaker-Unknown"
        )
        speaker_ratio = assigned_count / len(cleaned_segments)
        speaker_score = speaker_ratio * 100.0
        components.append(
            QualityComponent(
                name="speaker_separation",
                score=_clamp(speaker_score, 0, 100),
                value=speaker_ratio,
                details={
                    "assigned_segments": assigned_count,
                    "total_segments": len(cleaned_segments),
                    "speaker_ratio": speaker_ratio,
                },
            )
        )
    else:
        # If diarization is disabled, mark component as unavailable so that
        # its weight can be redistributed to other components.
        components.append(
            QualityComponent(
                name="speaker_separation",
                score=-1.0,  # sentinel for unavailable
                value=0.0,
                details={
                    "assigned_segments": 0,
                    "total_segments": len(cleaned_segments),
                    "speaker_ratio": 0.0,
                    "available": False,
                },
            )
        )

    # Combine weighted score -------------------------------------------------
    overall_score, component_payload = _combine_components(components, DEFAULT_WEIGHTS)

    return {
        "score": round(overall_score, 1),
        "components": component_payload,
        "diagnostics": {
            "duration_seconds": total_duration,
            "segment_count": len(segment_lengths),
            "characters": characters,
        },
    }


def _combine_components(
    components: Iterable[QualityComponent],
    weights: Dict[str, float],
) -> Tuple[float, Dict[str, Dict[str, float]]]:
    """Combine component scores using the provided weights."""
    available_components: List[QualityComponent] = [
        comp for comp in components if comp.score >= 0
    ]
    if not available_components:
        return 0.0, {}

    total_weight = sum(weights.get(comp.name, 0.0) for comp in available_components)
    if total_weight == 0:
        total_weight = float(len(available_components))  # equal weights fallback

    overall = 0.0
    payload: Dict[str, Dict[str, float]] = {}

    for comp in components:
        weight = weights.get(comp.name, 0.0)
        if comp.score < 0:
            payload[comp.name] = {
                "available": False,
                "score": None,
                **comp.details,
            }
            continue

        normalized_weight = weight / total_weight if total_weight else 0.0
        overall += comp.score * normalized_weight
        payload[comp.name] = {
            "score": round(comp.score, 2),
            "weight": round(normalized_weight, 4),
            "value": round(comp.value, 4),
            **comp.details,
        }

    return overall, payload


def _bounded_score(
    *,
    value: float,
    lower_opt: float,
    upper_opt: float,
    lower_min: float,
    upper_max: float,
) -> float:
    """
    Map a value to a 0-100 score given an optimal range and hard bounds.

    Within [lower_opt, upper_opt] the score is 100. Outside that range the
    score decreases linearly until reaching 0 at the min/max bounds.
    """
    if value <= 0:
        return 0.0

    if lower_opt <= value <= upper_opt:
        return 100.0

    if value < lower_opt:
        if value <= lower_min:
            return 0.0
        return 100.0 * (value - lower_min) / (lower_opt - lower_min)

    if value > upper_opt:
        if value >= upper_max:
            return 0.0
        return 100.0 * (upper_max - value) / (upper_max - upper_opt)

    return 0.0


def _compute_uniqueness_ratio(segments: List[Dict]) -> Tuple[float, float]:
    """
    Compute the ratio of unique segments to total segments and the duplicate ratio.
    """
    if not segments:
        return 1.0, 0.0

    normalized = [
        seg["text"].strip().lower()
        for seg in segments
        if seg.get("text") and seg["text"].strip()
    ]
    if not normalized:
        return 1.0, 0.0

    unique_count = len(set(normalized))
    total_count = len(normalized)

    unique_ratio = unique_count / total_count if total_count else 1.0
    duplicate_ratio = 1.0 - unique_ratio
    return unique_ratio, duplicate_ratio


def _most_common_language(chunk_results: Iterable[Dict]) -> Optional[str]:
    """Return the most frequently detected language from chunk results."""
    lang_counts: Dict[str, int] = {}
    for result in chunk_results:
        if not result.get("success"):
            continue
        language = result.get("language")
        if not language:
            continue
        lang_counts[language] = lang_counts.get(language, 0) + 1

    if not lang_counts:
        return None

    return max(lang_counts.items(), key=lambda item: item[1])[0]


def _clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp value between minimum and maximum."""
    return max(minimum, min(maximum, value))
