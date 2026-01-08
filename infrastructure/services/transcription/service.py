"""
Transcription Service implementation.

Orchestrates transcription using configured providers.
This is a facade that will delegate to the existing transcription code
in src/transcription/ during the migration period.
"""

from typing import Optional
from core.schemas.conversation import Transcript, TranscriptSegment


class TranscriptionService:
    """
    Service for transcribing audio to text.

    During migration, this delegates to existing code in src/transcription/.
    After migration, the logic will be moved here.
    """

    def __init__(self, provider: str = "groq_whisper"):
        """
        Initialize transcription service.

        Args:
            provider: Transcription provider ("groq_whisper" or "google_stt")
        """
        self.provider = provider

    async def transcribe(
        self,
        audio_uri: str,
        language: str = "zh",
        include_segments: bool = True,
    ) -> Transcript:
        """
        Transcribe an audio file.

        Args:
            audio_uri: GCS URI or Slack file URL
            language: Language code (default: Chinese)
            include_segments: Include timestamped segments

        Returns:
            Transcript object with full text and segments
        """
        # TODO: Migrate logic from src/transcription/groq_whisper_pipeline.py
        # For now, this is a placeholder that will be connected to existing code

        raise NotImplementedError(
            "Transcription service not yet migrated. "
            "Use src/transcription/ directly during migration."
        )

    async def transcribe_from_gcs(
        self,
        bucket: str,
        blob_path: str,
        language: str = "zh",
    ) -> Transcript:
        """
        Transcribe audio from GCS.

        Args:
            bucket: GCS bucket name
            blob_path: Path to audio file in bucket
            language: Language code

        Returns:
            Transcript object
        """
        audio_uri = f"gs://{bucket}/{blob_path}"
        return await self.transcribe(audio_uri, language)

    async def transcribe_from_slack(
        self,
        file_url: str,
        slack_token: str,
        language: str = "zh",
    ) -> Transcript:
        """
        Transcribe audio from Slack file.

        Args:
            file_url: Slack private file URL
            slack_token: Bot token for downloading
            language: Language code

        Returns:
            Transcript object
        """
        # Download file and transcribe
        # TODO: Implement after migration
        raise NotImplementedError("Slack transcription not yet migrated.")

    def _convert_to_transcript(self, raw_result: dict, transcript_id: str) -> Transcript:
        """Convert raw transcription result to Transcript schema."""
        segments = []

        for seg in raw_result.get("segments", []):
            segments.append(TranscriptSegment(
                speaker_label=seg.get("speaker"),
                text=seg.get("text", ""),
                start_time=seg.get("start"),
                end_time=seg.get("end"),
                confidence=seg.get("confidence"),
            ))

        return Transcript(
            id=transcript_id,
            segments=segments,
            full_text=raw_result.get("text", ""),
            language=raw_result.get("language", "zh-TW"),
            duration_seconds=raw_result.get("duration"),
            provider=self.provider,
        )
