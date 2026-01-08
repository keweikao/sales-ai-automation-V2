"""
Groq Whisper transcription provider.

Uses Groq's hosted Whisper API for fast, accurate transcription.

NOTE: During migration, the actual implementation is in:
    src/transcription/groq_whisper_pipeline.py

This file will contain the migrated code.
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class WhisperConfig:
    """Configuration for Whisper transcription."""
    model: str = "whisper-large-v3-turbo"
    language: str = "zh"
    response_format: str = "verbose_json"
    temperature: float = 0.0


class GroqWhisperProvider:
    """
    Groq Whisper transcription provider.

    Provides high-speed transcription using Groq's LPU inference.

    Migration status: PENDING
    Current implementation: src/transcription/groq_whisper_pipeline.py
    """

    def __init__(self, api_key: Optional[str] = None, config: Optional[WhisperConfig] = None):
        self.api_key = api_key
        self.config = config or WhisperConfig()

    async def transcribe(self, audio_path: str) -> dict:
        """
        Transcribe audio file using Groq Whisper.

        Args:
            audio_path: Local path to audio file

        Returns:
            Dict with transcription result including segments
        """
        # TODO: Migrate from src/transcription/groq_whisper_pipeline.py
        raise NotImplementedError(
            "GroqWhisperProvider not yet migrated. "
            "Use GroqWhisperPipeline from src/transcription/ during migration."
        )

    async def transcribe_with_segments(self, audio_path: str) -> dict:
        """Transcribe with word-level timestamps."""
        # TODO: Migrate segment extraction logic
        raise NotImplementedError("Not yet migrated.")
