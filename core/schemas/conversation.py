"""
Conversation schema definitions.

Defines data structures for sales conversations and transcripts.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ConversationType(str, Enum):
    """Type of sales conversation."""
    DISCOVERY = "discovery"
    DEMO = "demo"
    NEGOTIATION = "negotiation"
    FOLLOW_UP = "follow_up"
    CLOSING = "closing"
    CHECK_IN = "check_in"
    SUPPORT = "support"
    OTHER = "other"


class Speaker(BaseModel):
    """Represents a participant in the conversation."""
    id: str
    name: Optional[str] = None
    role: Optional[str] = None  # e.g., "sales_rep", "customer", "decision_maker"
    is_internal: bool = False


class TranscriptSegment(BaseModel):
    """A segment of the transcript with timing and speaker info."""
    speaker_id: Optional[str] = None
    speaker_label: Optional[str] = None  # e.g., "Speaker 1", "John"
    text: str
    start_time: Optional[float] = None  # seconds
    end_time: Optional[float] = None
    confidence: Optional[float] = None


class Transcript(BaseModel):
    """
    Full transcript of a conversation.

    Output from infrastructure/services/transcription/
    Input to modules/03-sales-conversation/
    """
    id: str = Field(..., description="Unique transcript identifier")

    # Content
    segments: list[TranscriptSegment] = Field(default_factory=list)
    full_text: Optional[str] = None  # Concatenated text

    # Metadata
    language: str = "zh-TW"
    duration_seconds: Optional[float] = None
    word_count: Optional[int] = None

    # Quality metrics
    transcription_confidence: Optional[float] = None

    # Processing info
    provider: str = "groq_whisper"  # or "google_stt"
    processed_at: datetime = Field(default_factory=datetime.utcnow)


class Conversation(BaseModel):
    """
    Core Conversation model representing a sales interaction.

    Central entity linking:
    - Lead (who)
    - Transcript (what was said)
    - AnalysisResult (insights)
    """
    id: str = Field(..., description="Unique conversation identifier, e.g., case_id")

    # References
    lead_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    salesforce_id: Optional[str] = None

    # Participants
    sales_rep_id: Optional[str] = None
    sales_rep_name: Optional[str] = None
    speakers: list[Speaker] = Field(default_factory=list)

    # Type and context
    conversation_type: ConversationType = ConversationType.OTHER
    title: Optional[str] = None

    # Audio source
    audio_file_uri: Optional[str] = None  # GCS URI
    audio_duration_seconds: Optional[float] = None

    # Transcript
    transcript: Optional[Transcript] = None

    # Status tracking
    status: str = "pending"  # pending, transcribing, analyzing, completed, failed

    # Timestamps
    occurred_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Slack context
    slack_channel_id: Optional[str] = None
    slack_thread_ts: Optional[str] = None
    slack_user_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "case_20250108_001",
                "sales_rep_name": "Alice Wang",
                "conversation_type": "demo",
                "status": "completed",
                "audio_duration_seconds": 1847.5,
            }
        }
