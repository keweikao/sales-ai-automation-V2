"""
Transcription Service API routes.

FastAPI router for transcription endpoints.
Will be integrated with the main service after migration.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/transcription", tags=["transcription"])


class TranscribeRequest(BaseModel):
    """Request body for transcription."""
    audio_uri: str
    language: str = "zh"
    provider: str = "groq_whisper"
    callback_url: Optional[str] = None


class TranscribeResponse(BaseModel):
    """Response from transcription."""
    transcript_id: str
    status: str
    message: str


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(request: TranscribeRequest):
    """
    Start transcription of an audio file.

    The transcription runs asynchronously.
    Use callback_url or poll status endpoint for results.
    """
    # TODO: Connect to TranscriptionService after migration
    # Currently, use existing src/transcription/main.py endpoints

    return TranscribeResponse(
        transcript_id="placeholder",
        status="pending",
        message="Transcription service migration in progress. Use legacy endpoints.",
    )


@router.get("/status/{transcript_id}")
async def get_status(transcript_id: str):
    """Get transcription status."""
    # TODO: Implement status checking
    raise HTTPException(
        status_code=501,
        detail="Status endpoint not yet implemented in V2.1"
    )
