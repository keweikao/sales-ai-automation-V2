"""
Repository for Conversation documents in Firestore.

Handles CRUD operations for sales conversations (cases).
"""

from datetime import datetime
from typing import Optional
from google.cloud import firestore

from core.schemas.conversation import Conversation


class ConversationRepository:
    """
    Repository for managing Conversation documents.

    Collection: sales_cases
    """

    COLLECTION = "sales_cases"

    def __init__(self, db: Optional[firestore.Client] = None):
        self.db = db or firestore.Client()
        self.collection = self.db.collection(self.COLLECTION)

    async def get(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        doc = self.collection.document(conversation_id).get()
        if doc.exists:
            return Conversation(id=doc.id, **doc.to_dict())
        return None

    async def create(self, conversation: Conversation) -> Conversation:
        """Create a new conversation."""
        doc_ref = self.collection.document(conversation.id)
        doc_ref.set(conversation.model_dump(exclude={"id"}))
        return conversation

    async def update(self, conversation_id: str, **kwargs) -> None:
        """Update specific fields of a conversation."""
        kwargs["updated_at"] = datetime.utcnow()
        self.collection.document(conversation_id).update(kwargs)

    async def update_status(self, conversation_id: str, status: str) -> None:
        """Update conversation status."""
        await self.update(conversation_id, status=status)

    async def list_by_status(self, status: str, limit: int = 50) -> list[Conversation]:
        """List conversations by status."""
        docs = (
            self.collection
            .where("status", "==", status)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        return [Conversation(id=doc.id, **doc.to_dict()) for doc in docs]

    async def list_by_sales_rep(
        self,
        sales_rep_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50
    ) -> list[Conversation]:
        """List conversations for a specific sales rep."""
        query = self.collection.where("sales_rep_id", "==", sales_rep_id)

        if start_date:
            query = query.where("occurred_at", ">=", start_date)
        if end_date:
            query = query.where("occurred_at", "<=", end_date)

        query = query.order_by("occurred_at", direction=firestore.Query.DESCENDING)
        query = query.limit(limit)

        docs = query.stream()
        return [Conversation(id=doc.id, **doc.to_dict()) for doc in docs]
