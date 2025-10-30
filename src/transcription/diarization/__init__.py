"""
Diarization module entrypoint.

Provides helper utilities to build a speaker diarizer, preferring
pyannote.audio when available and falling back to other implementations
when necessary.
"""

from typing import Optional

from .pyannote_diarizer import PyannoteDiarizer, SpeakerSegment  # noqa: F401
from .embedding_diarizer import EmbeddingClusterDiarizer  # noqa: F401


def create_diarizer(
    use_auth_token: Optional[str] = None,
    allow_overlap: bool = False,
    model_name: str = "pyannote/speaker-diarization",
) -> Optional[object]:
    """
    Create the best available diarizer implementation.

    Returns:
        Instance of a diarizer implementing `diarize(audio_path)` and
        `summarize(segments)` methods, or None if no implementation is
        available.
    """
    try:
        return PyannoteDiarizer(
            model_name=model_name,
            use_auth_token=use_auth_token,
            enable_overlap=allow_overlap,
        )
    except Exception as exc:  # pragma: no cover - environment dependent
        # Fallback to SpeechBrain-based diarizer if pyannote is unavailable.
        try:
            return EmbeddingClusterDiarizer()
        except Exception as fallback_exc:
            raise RuntimeError(f"{exc} | {fallback_exc}") from fallback_exc
