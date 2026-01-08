"""
Journey Logger interface for tracking customer journey events.

Provides a consistent way to log events across all modules.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from core.schemas.events import Event, EventType


class JourneyLogger(ABC):
    """
    Abstract interface for logging customer journey events.

    Implementations may write to:
    - Firestore (for persistence)
    - BigQuery (for analytics)
    - Pub/Sub (for real-time processing)
    """

    @abstractmethod
    async def log_event(
        self,
        event_type: EventType,
        source_module: str,
        conversation_id: Optional[str] = None,
        lead_id: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> Event:
        """
        Log a journey event.

        Args:
            event_type: Type of event from EventType enum
            source_module: Module generating the event (e.g., "03-sales-conversation")
            conversation_id: Related conversation ID if applicable
            lead_id: Related lead ID if applicable
            payload: Additional event data
            correlation_id: ID to correlate related events

        Returns:
            The created Event object
        """
        pass

    @abstractmethod
    async def get_journey(
        self,
        lead_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[Event]:
        """
        Retrieve journey events for a lead or conversation.

        Args:
            lead_id: Filter by lead ID
            conversation_id: Filter by conversation ID
            start_date: Filter events after this date
            end_date: Filter events before this date

        Returns:
            List of events in chronological order
        """
        pass


class FirestoreJourneyLogger(JourneyLogger):
    """
    Firestore implementation of JourneyLogger.

    Stores events in the 'journey_events' collection.
    """

    COLLECTION = "journey_events"

    def __init__(self, db=None):
        from google.cloud import firestore
        self.db = db or firestore.Client()
        self.collection = self.db.collection(self.COLLECTION)

    async def log_event(
        self,
        event_type: EventType,
        source_module: str,
        conversation_id: Optional[str] = None,
        lead_id: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> Event:
        import uuid

        event = Event(
            id=f"evt_{uuid.uuid4().hex[:12]}",
            type=event_type,
            source_module=source_module,
            conversation_id=conversation_id,
            lead_id=lead_id,
            payload=payload or {},
            correlation_id=correlation_id,
            timestamp=datetime.utcnow(),
        )

        self.collection.document(event.id).set(event.model_dump())
        return event

    async def get_journey(
        self,
        lead_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[Event]:
        query = self.collection

        if lead_id:
            query = query.where("lead_id", "==", lead_id)
        if conversation_id:
            query = query.where("conversation_id", "==", conversation_id)
        if start_date:
            query = query.where("timestamp", ">=", start_date)
        if end_date:
            query = query.where("timestamp", "<=", end_date)

        query = query.order_by("timestamp")

        docs = query.stream()
        return [Event(**doc.to_dict()) for doc in docs]
