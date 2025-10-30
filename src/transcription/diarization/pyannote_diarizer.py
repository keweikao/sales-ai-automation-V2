"""
Speaker diarization utilities using pyannote.audio.

The diarizer assigns speaker labels to audio segments so downstream
consumers can distinguish between different participants in a call.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List, Optional, Dict

import numpy as np
import torchaudio

logger = logging.getLogger(__name__)

if not hasattr(torchaudio, "set_audio_backend"):
    def _set_audio_backend_stub(name: str):  # type: ignore
        logger.debug("torchaudio.set_audio_backend stub used (%s)", name)

    torchaudio.set_audio_backend = _set_audio_backend_stub  # type: ignore

if not hasattr(np, "NaN"):
    np.NaN = np.nan  # type: ignore[attr-defined]


@dataclass
class SpeakerSegment:
    """Represents a diarized speaker segment."""

    start: float
    end: float
    speaker: str


class PyannoteDiarizer:
    """
    Wrapper around pyannote.audio speaker diarization pipeline.

    The diarizer requires a Hugging Face token with access to the
    `pyannote/speaker-diarization` model. The token can be provided via the
    `use_auth_token` constructor argument or the `HUGGINGFACE_TOKEN`
    environment variable.
    """

    def __init__(
        self,
        model_name: str = "pyannote/speaker-diarization",
        use_auth_token: Optional[str] = None,
        enable_overlap: bool = False,
    ):
        try:
            from pyannote.audio import Pipeline  # type: ignore
        except Exception as exc:  # pragma: no cover - handled by runtime checks
            raise RuntimeError(
                "pyannote.audio could not be initialized. "
                "Ensure it is installed and compatible with the current torchaudio version."
            ) from exc

        token = use_auth_token or os.getenv("HUGGINGFACE_TOKEN")
        if not token:
            raise RuntimeError(
                "Missing Hugging Face token for pyannote.audio diarization. "
                "Set the HUGGINGFACE_TOKEN environment variable or provide "
                "`use_auth_token` when constructing PyannoteDiarizer."
            )

        logger.info(
            "Initializing pyannote diarization pipeline (model=%s, overlap=%s)",
            model_name,
            enable_overlap,
        )

        self.pipeline = Pipeline.from_pretrained(model_name, use_auth_token=token)
        self.enable_overlap = enable_overlap

    def diarize(
        self,
        audio_path: str,
        transcript_segments: Optional[List[Dict]] = None,
    ) -> List[SpeakerSegment]:
        """
        Run speaker diarization on the provided audio file.

        Args:
            audio_path: Path to the audio file.

        Returns:
            List[SpeakerSegment]: Ordered list of speaker segments.
        """
        logger.info("Running speaker diarization on %s", audio_path)

        diarization = self.pipeline(
            audio_path, num_speakers=None, min_speakers=1, max_speakers=5
        )

        segments: List[SpeakerSegment] = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append(
                SpeakerSegment(
                    start=float(turn.start),
                    end=float(turn.end),
                    speaker=str(speaker),
                )
            )

        segments.sort(key=lambda seg: seg.start)

        if not self.enable_overlap:
            segments = self._remove_overlaps(segments)

        logger.info("Diarization produced %d segments", len(segments))

        return segments

    def _remove_overlaps(self, segments: List[SpeakerSegment]) -> List[SpeakerSegment]:
        """
        Merge overlapping segments by keeping the dominant speaker.

        This keeps the diarization output simple for downstream consumers that
        expect a single speaker per time range.
        """
        if not segments:
            return segments

        merged: List[SpeakerSegment] = [segments[0]]

        for current in segments[1:]:
            previous = merged[-1]
            if current.start < previous.end:
                # Overlap detected – truncate the previous segment
                if current.end <= previous.end:
                    # Current segment is entirely within previous; skip it.
                    continue

                logger.debug(
                    "Adjusting overlapping segments: %s -> %s",
                    previous,
                    current,
                )

                previous.end = current.start
                merged.append(current)
            else:
                merged.append(current)

        return merged

    def summarize(self, segments: List[SpeakerSegment]) -> List[Dict[str, float]]:
        """Summarize speaker activity."""
        return self._summarize_segments(segments)

    @staticmethod
    def _summarize_segments(segments: List[SpeakerSegment]) -> List[Dict[str, float]]:
        """
        Produce aggregate statistics per speaker.

        Args:
            segments: diarized speaker segments

        Returns:
            List of dictionaries containing speaker statistics.
        """
        summary: Dict[str, Dict[str, float]] = {}

        for segment in segments:
            duration = max(0.0, segment.end - segment.start)
            info = summary.setdefault(
                segment.speaker,
                {"speaker": segment.speaker, "duration": 0.0, "segment_count": 0},
            )
            info["duration"] += duration
            info["segment_count"] += 1

        return list(summary.values())
