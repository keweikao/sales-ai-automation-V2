"""
Base transcription pipeline interface.

All transcription providers must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class TranscriptionPipeline(ABC):
    """Abstract base class for transcription pipelines."""

    @abstractmethod
    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe an audio file.

        Args:
            audio_path: Path to audio file (local or GCS URI)

        Returns:
            Dict with keys:
                - success: bool
                - full_text: str
                - segments: List[Dict] with start, end, speaker, text
                - speakers: List[str]
                - audio_info: Dict with duration, processing_time
                - error: str (if success=False)
        """
        pass
