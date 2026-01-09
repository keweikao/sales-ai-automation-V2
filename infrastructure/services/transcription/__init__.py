"""
Transcription Service

Converts audio files to text transcripts.

Supported providers:
- Groq Whisper (default): Fast, accurate, cost-effective
- Google Gemini: Alternative with speaker detection

Supported sources:
- GCS: Google Cloud Storage audio files
- Slack: Direct Slack file downloads

Usage:
    from infrastructure.services.transcription import get_pipeline

    # Get default pipeline (Groq Whisper)
    pipeline = get_pipeline()
    result = pipeline.transcribe("gs://bucket/audio.mp3")

    # Or use specific provider
    from infrastructure.services.transcription.providers import GroqWhisperPipeline
    pipeline = GroqWhisperPipeline(api_key="...")
    result = pipeline.transcribe("audio.mp3")
"""

import os
import logging

logger = logging.getLogger(__name__)

# Global pipeline instance
_pipeline = None


def get_pipeline(engine: str = None):
    """
    Get or create transcription pipeline.

    Uses lazy imports to minimize memory footprint.
    Only imports the specific pipeline module when needed.

    Args:
        engine: Engine to use ("groq_whisper" or "gemini")
                Defaults to TRANSCRIPTION_ENGINE env var or "groq_whisper"

    Returns:
        TranscriptionPipeline instance
    """
    global _pipeline

    # Determine which engine to use
    if engine is None:
        engine = os.getenv("TRANSCRIPTION_ENGINE", "groq_whisper").strip().lower()

    # If singleton mode and already initialized, return existing
    if _pipeline is not None and engine is None:
        return _pipeline

    logger.info(f"Initializing Pipeline. Engine: '{engine}'")

    # Lazy import based on engine
    if engine == "gemini":
        from .providers.gemini import GeminiTranscriptionPipeline
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for Gemini engine")
        result = GeminiTranscriptionPipeline(api_key=api_key)

    elif engine == "groq_whisper":
        from .providers.whisper import GroqWhisperPipeline
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is required for Groq Whisper engine")
        result = GroqWhisperPipeline(api_key=api_key)

    else:
        # Fallback to groq_whisper as default
        logger.warning(f"Unknown engine '{engine}', falling back to groq_whisper")
        from .providers.whisper import GroqWhisperPipeline
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is required for Groq Whisper engine (fallback)")
        result = GroqWhisperPipeline(api_key=api_key)

    # Set global singleton if this was the first call
    if _pipeline is None:
        _pipeline = result

    return result


# Export commonly used classes
from .providers import GroqWhisperPipeline, GeminiTranscriptionPipeline, TranscriptionPipeline  # noqa: E402
from .status_tracker import TranscriptionStatusTracker  # noqa: E402

__all__ = [
    "get_pipeline",
    "TranscriptionPipeline",
    "GroqWhisperPipeline",
    "GeminiTranscriptionPipeline",
    "TranscriptionStatusTracker",
]
