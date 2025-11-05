import math

from ..quality import calculate_transcription_quality


def _build_segment(text: str, start: float, end: float, speaker: str = "Speaker-1"):
    return {"text": text, "start": start, "end": end, "speaker": speaker}


def test_quality_scoring_basic():
    merged_result = {
        "segments": [
            _build_segment("感謝您今天的時間，我們先談需求。", 0.0, 5.0),
            _build_segment("目前最在意的是提升翻桌率。", 5.0, 9.5),
            _build_segment("了解，那我們建議掃碼點餐。", 9.5, 14.5),
        ],
        "full_text": (
            "感謝您今天的時間，我們先談需求。 "
            "目前最在意的是提升翻桌率。 "
            "了解，那我們建議掃碼點餐。"
        ),
        "statistics": {"total_duration": 15.0, "total_segments": 3},
    }
    chunk_results = [
        {
            "success": True,
            "language": "zh",
            "language_probability": 0.97,
        },
        {
            "success": True,
            "language": "zh",
            "language_probability": 0.95,
        },
    ]
    audio_info = {"duration": 15.0}

    quality = calculate_transcription_quality(
        merged_result=merged_result,
        chunk_results=chunk_results,
        audio_info=audio_info,
        diarization_enabled=True,
    )

    assert 0 <= quality["score"] <= 100
    components = quality["components"]
    assert components["language_confidence"]["score"] >= 90
    assert components["char_time_ratio"]["value"] > 0
    assert components["repetition"]["unique_segment_ratio"] >= 0.5
    assert not math.isnan(quality["score"])


def test_quality_without_diarization_marks_component_unavailable():
    merged_result = {
        "segments": [
            _build_segment("感謝今天的討論。", 0.0, 4.0, speaker=None),
        ],
        "full_text": "感謝今天的討論。",
        "statistics": {"total_duration": 4.0, "total_segments": 1},
    }
    chunk_results = [
        {
            "success": True,
            "language": "zh",
            "language_probability": 0.8,
        }
    ]
    audio_info = {"duration": 4.0}

    quality = calculate_transcription_quality(
        merged_result=merged_result,
        chunk_results=chunk_results,
        audio_info=audio_info,
        diarization_enabled=False,
    )

    speaker_component = quality["components"]["speaker_separation"]
    assert speaker_component["available"] is False
    assert speaker_component["score"] is None
