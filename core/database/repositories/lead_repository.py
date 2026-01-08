"""
Repository for Lead documents in Firestore.

Handles CRUD operations for leads.
"""

from datetime import datetime
from typing import Optional
from google.cloud import firestore

from core.schemas.lead import Lead, LeadStatus


class LeadRepository:
    """
    Repository for managing Lead documents.

    Collection: leads
    """

    COLLECTION = "leads"

    def __init__(self, db: Optional[firestore.Client] = None):
        self.db = db or firestore.Client()
        self.collection = self.db.collection(self.COLLECTION)

    async def get(self, lead_id: str) -> Optional[Lead]:
        """Get a lead by ID."""
        doc = self.collection.document(lead_id).get()
        if doc.exists:
            return Lead(id=doc.id, **doc.to_dict())
        return None

    async def get_by_email(self, email: str) -> Optional[Lead]:
        """Get a lead by email address."""
        docs = self.collection.where("email", "==", email).limit(1).stream()
        for doc in docs:
            return Lead(id=doc.id, **doc.to_dict())
        return None

    async def create(self, lead: Lead) -> Lead:
        """Create a new lead."""
        doc_ref = self.collection.document(lead.id)
        doc_ref.set(lead.model_dump(exclude={"id"}))
        return lead

    async def update(self, lead_id: str, **kwargs) -> None:
        """Update specific fields of a lead."""
        kwargs["updated_at"] = datetime.utcnow()
        self.collection.document(lead_id).update(kwargs)

    async def update_status(self, lead_id: str, status: LeadStatus) -> None:
        """Update lead status."""
        await self.update(lead_id, status=status.value)

    async def update_score(self, lead_id: str, score: int) -> None:
        """Update lead score."""
        await self.update(lead_id, score=score)

    async def list_by_status(self, status: LeadStatus, limit: int = 50) -> list[Lead]:
        """List leads by status."""
        docs = (
            self.collection
            .where("status", "==", status.value)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        return [Lead(id=doc.id, **doc.to_dict()) for doc in docs]

    async def list_recent(self, limit: int = 50) -> list[Lead]:
        """List most recent leads."""
        docs = (
            self.collection
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        return [Lead(id=doc.id, **doc.to_dict()) for doc in docs]
