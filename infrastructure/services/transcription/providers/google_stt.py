"""
Google Speech-to-Text transcription provider.

Uses Google Cloud Speech-to-Text API.

NOTE: During migration, the actual implementation is in:
    src/transcription/pipeline.py
    src/transcription/batch_service.py

This file will contain the migrated code.
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class GoogleSTTConfig:
    """Configuration for Google STT."""
    model: str = "chirp_2"
    language_code: str = "zh-TW"
    enable_word_time_offsets: bool = True
    enable_automatic_punctuation: bool = True


class GoogleSTTProvider:
    """
    Google Speech-to-Text provider.

    Migration status: PENDING
    Current implementation: src/transcription/pipeline.py
    """

    def __init__(self, config: Optional[GoogleSTTConfig] = None):
        self.config = config or GoogleSTTConfig()

    async def transcribe(self, gcs_uri: str) -> dict:
        """
        Transcribe audio from GCS using Google STT.

        Args:
            gcs_uri: GCS URI of audio file

        Returns:
            Dict with transcription result
        """
        # TODO: Migrate from src/transcription/pipeline.py
        raise NotImplementedError(
            "GoogleSTTProvider not yet migrated. "
            "Use existing pipeline from src/transcription/ during migration."
        )

    async def transcribe_batch(self, gcs_uris: list[str]) -> list[dict]:
        """Batch transcribe multiple files."""
        # TODO: Migrate from src/transcription/batch_service.py
        raise NotImplementedError("Not yet migrated.")
