"""
Transcription Service

Converts audio files to text transcripts.

Supported providers:
- Groq Whisper (default): Fast, accurate, cost-effective
- Google STT: Alternative for specific use cases

Supported sources:
- GCS: Google Cloud Storage audio files
- Slack: Direct Slack file downloads

Usage:
    from infrastructure.services.transcription import TranscriptionService

    service = TranscriptionService()
    result = await service.transcribe(audio_uri="gs://bucket/audio.mp3")
"""

from .service import TranscriptionService

__all__ = ["TranscriptionService"]
