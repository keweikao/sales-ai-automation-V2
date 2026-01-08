"""
Transcription Service implementation.

Orchestrates transcription using configured providers.
"""

import os
import logging
from typing import Optional

from core.schemas.conversation import Transcript, TranscriptSegment
from .providers.whisper import GroqWhisperPipeline

logger = logging.getLogger(__name__)


class TranscriptionService:
    """
    Service for transcribing audio to text.

    Uses Groq's hosted Whisper API for fast, accurate transcription.
    """

    def __init__(self, provider: str = "groq_whisper"):
        """
        Initialize transcription service.

        Args:
            provider: Transcription provider (default: "groq_whisper")
        """
        self.provider = provider
        self._pipeline = None

    def _get_pipeline(self):
        """Lazy initialization of transcription pipeline."""
        if self._pipeline is None:
            if self.provider == "groq_whisper":
                api_key = os.getenv("GROQ_API_KEY")
                if not api_key:
                    raise ValueError("GROQ_API_KEY environment variable is required")
                self._pipeline = GroqWhisperPipeline(api_key=api_key)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        return self._pipeline

    async def transcribe(
        self,
        audio_uri: str,
        language: str = "zh",
        include_segments: bool = True,
    ) -> Transcript:
        """
        Transcribe an audio file.

        Args:
            audio_uri: GCS URI (gs://...) or local file path
            language: Language code (default: Chinese)
            include_segments: Include timestamped segments

        Returns:
            Transcript object with full text and segments
        """
        logger.info(f"Starting transcription for: {audio_uri}")

        pipeline = self._get_pipeline()
        result = pipeline.transcribe(audio_uri)

        if not result.get("success"):
            error_msg = result.get("error", "Unknown transcription error")
            logger.error(f"Transcription failed: {error_msg}")
            raise RuntimeError(f"Transcription failed: {error_msg}")

        # Generate transcript ID from audio URI
        transcript_id = self._generate_transcript_id(audio_uri)

        return self._convert_to_transcript(result, transcript_id)

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
        import tempfile
        import httpx

        # Download file from Slack
        with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as tmp_file:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    file_url,
                    headers={"Authorization": f"Bearer {slack_token}"},
                    follow_redirects=True,
                )
                response.raise_for_status()
                tmp_file.write(response.content)
                local_path = tmp_file.name

        try:
            return await self.transcribe(local_path, language)
        finally:
            # Clean up temp file
            os.unlink(local_path)

    def _generate_transcript_id(self, audio_uri: str) -> str:
        """Generate a transcript ID from the audio URI."""
        import hashlib
        from datetime import datetime

        # Create hash from URI + timestamp
        hash_input = f"{audio_uri}_{datetime.now().isoformat()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

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

        audio_info = raw_result.get("audio_info", {})

        return Transcript(
            id=transcript_id,
            segments=segments,
            full_text=raw_result.get("full_text", ""),
            language=raw_result.get("language", "zh-TW"),
            duration_seconds=audio_info.get("duration"),
            provider=self.provider,
        )
