"""
Transcription Service API routes.

FastAPI router for transcription endpoints.
"""

import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from .service import TranscriptionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/transcription", tags=["transcription"])

# In-memory storage for async transcription status (use Redis/Firestore in production)
_transcription_jobs: Dict[str, Dict[str, Any]] = {}


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


class TranscriptSegment(BaseModel):
    """A segment of the transcript."""
    speaker_label: Optional[str] = None
    text: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    confidence: Optional[float] = None


class TranscriptResult(BaseModel):
    """Full transcription result."""
    transcript_id: str
    status: str
    full_text: Optional[str] = None
    segments: Optional[List[TranscriptSegment]] = None
    duration_seconds: Optional[float] = None
    provider: Optional[str] = None
    error: Optional[str] = None


async def _run_transcription(
    transcript_id: str,
    audio_uri: str,
    language: str,
    provider: str,
    callback_url: Optional[str] = None,
):
    """Background task to run transcription."""
    try:
        _transcription_jobs[transcript_id]["status"] = "processing"

        service = TranscriptionService(provider=provider)
        result = await service.transcribe(audio_uri, language)

        _transcription_jobs[transcript_id] = {
            "status": "completed",
            "result": {
                "transcript_id": transcript_id,
                "full_text": result.full_text,
                "segments": [
                    {
                        "speaker_label": seg.speaker_label,
                        "text": seg.text,
                        "start_time": seg.start_time,
                        "end_time": seg.end_time,
                        "confidence": seg.confidence,
                    }
                    for seg in result.segments
                ],
                "duration_seconds": result.duration_seconds,
                "provider": result.provider,
            },
        }

        # TODO: Call callback_url if provided
        if callback_url:
            logger.info(f"Would call callback: {callback_url}")

    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        _transcription_jobs[transcript_id] = {
            "status": "failed",
            "error": str(e),
        }


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(request: TranscribeRequest, background_tasks: BackgroundTasks):
    """
    Start transcription of an audio file.

    The transcription runs asynchronously.
    Use callback_url or poll status endpoint for results.
    """
    import uuid

    transcript_id = str(uuid.uuid4())[:8]

    # Initialize job status
    _transcription_jobs[transcript_id] = {
        "status": "pending",
        "audio_uri": request.audio_uri,
    }

    # Queue background task
    background_tasks.add_task(
        _run_transcription,
        transcript_id,
        request.audio_uri,
        request.language,
        request.provider,
        request.callback_url,
    )

    return TranscribeResponse(
        transcript_id=transcript_id,
        status="pending",
        message="Transcription started. Poll /status/{transcript_id} for results.",
    )


@router.post("/transcribe/sync", response_model=TranscriptResult)
async def transcribe_sync(request: TranscribeRequest):
    """
    Synchronously transcribe an audio file.

    Blocks until transcription is complete.
    Use this for shorter audio files or when immediate results are needed.
    """
    import uuid

    transcript_id = str(uuid.uuid4())[:8]

    try:
        service = TranscriptionService(provider=request.provider)
        result = await service.transcribe(request.audio_uri, request.language)

        return TranscriptResult(
            transcript_id=transcript_id,
            status="completed",
            full_text=result.full_text,
            segments=[
                TranscriptSegment(
                    speaker_label=seg.speaker_label,
                    text=seg.text,
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                    confidence=seg.confidence,
                )
                for seg in result.segments
            ],
            duration_seconds=result.duration_seconds,
            provider=result.provider,
        )

    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}",
        )


@router.get("/status/{transcript_id}", response_model=TranscriptResult)
async def get_status(transcript_id: str):
    """Get transcription status and results."""
    if transcript_id not in _transcription_jobs:
        raise HTTPException(
            status_code=404,
            detail=f"Transcription job not found: {transcript_id}",
        )

    job = _transcription_jobs[transcript_id]
    status = job["status"]

    if status == "completed":
        result = job["result"]
        return TranscriptResult(
            transcript_id=transcript_id,
            status="completed",
            full_text=result.get("full_text"),
            segments=[
                TranscriptSegment(**seg) for seg in result.get("segments", [])
            ],
            duration_seconds=result.get("duration_seconds"),
            provider=result.get("provider"),
        )
    elif status == "failed":
        return TranscriptResult(
            transcript_id=transcript_id,
            status="failed",
            error=job.get("error"),
        )
    else:
        return TranscriptResult(
            transcript_id=transcript_id,
            status=status,
        )
