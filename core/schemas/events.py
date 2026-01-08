"""
Event schema definitions.

Defines event structures for the event-driven architecture.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of events in the system."""
    # Lead events
    LEAD_CREATED = "lead.created"
    LEAD_UPDATED = "lead.updated"
    LEAD_QUALIFIED = "lead.qualified"

    # Conversation events
    CONVERSATION_STARTED = "conversation.started"
    CONVERSATION_UPLOADED = "conversation.uploaded"
    CONVERSATION_TRANSCRIBED = "conversation.transcribed"
    CONVERSATION_ANALYZED = "conversation.analyzed"
    CONVERSATION_COMPLETED = "conversation.completed"
    CONVERSATION_FAILED = "conversation.failed"

    # Notification events
    NOTIFICATION_REQUESTED = "notification.requested"
    NOTIFICATION_SENT = "notification.sent"
    NOTIFICATION_FAILED = "notification.failed"

    # User interaction events
    SUMMARY_EDITED = "summary.edited"
    SUMMARY_APPROVED = "summary.approved"
    SUMMARY_SENT_TO_CUSTOMER = "summary.sent_to_customer"

    # System events
    WEEKLY_REPORT_GENERATED = "report.weekly_generated"
    ERROR_OCCURRED = "error.occurred"

    # Salesforce events
    SALESFORCE_SYNCED = "salesforce.synced"
    SALESFORCE_SYNC_FAILED = "salesforce.sync_failed"


class Event(BaseModel):
    """
    Base event model for inter-module communication.

    Used for:
    - Triggering downstream processes
    - Audit logging
    - Analytics tracking
    """
    id: str = Field(..., description="Unique event identifier")
    type: EventType

    # Source
    source_module: str  # e.g., "03-sales-conversation", "transcription"
    source_service: Optional[str] = None

    # References
    conversation_id: Optional[str] = None
    lead_id: Optional[str] = None
    user_id: Optional[str] = None

    # Payload
    payload: dict[str, Any] = Field(default_factory=dict)

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None  # For tracing related events

    # Error info (for error events)
    error_message: Optional[str] = None
    error_code: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "evt_abc123",
                "type": "conversation.analyzed",
                "source_module": "03-sales-conversation",
                "conversation_id": "case_20250108_001",
                "payload": {
                    "meddic_score": 72,
                    "insights_count": 5
                }
            }
        }


class EventPublisher(BaseModel):
    """Configuration for event publishing."""
    topic: str  # Pub/Sub topic or queue name
    enabled: bool = True
    retry_count: int = 3


class EventSubscriber(BaseModel):
    """Configuration for event subscription."""
    event_types: list[EventType]
    handler_url: Optional[str] = None  # Cloud Run endpoint
    handler_function: Optional[str] = None  # Function name for direct calls
