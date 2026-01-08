"""
Firestore client dependency for FastAPI.

Provides a singleton Firestore client for use across API routes.
"""

import os
from functools import lru_cache
from typing import Optional

from google.cloud import firestore


@lru_cache()
def get_firestore_client() -> firestore.Client:
    """
    Get a cached Firestore client instance.

    Uses GOOGLE_CLOUD_PROJECT environment variable if set,
    otherwise relies on Application Default Credentials.
    """
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if project:
        return firestore.Client(project=project)
    return firestore.Client()


async def get_db() -> firestore.Client:
    """
    FastAPI dependency for Firestore client.

    Usage:
        @router.get("/items")
        async def list_items(db: firestore.Client = Depends(get_db)):
            ...
    """
    return get_firestore_client()


class FirestoreService:
    """
    Base service class for Firestore operations.

    Provides common query patterns and error handling.
    """

    def __init__(self, db: Optional[firestore.Client] = None):
        self.db = db or get_firestore_client()

    def get_document(self, collection: str, doc_id: str) -> Optional[dict]:
        """Get a single document by ID."""
        doc = self.db.collection(collection).document(doc_id).get()
        if doc.exists:
            data = doc.to_dict()
            data["id"] = doc.id
            return data
        return None

    def list_documents(
        self,
        collection: str,
        filters: Optional[list[tuple]] = None,
        order_by: Optional[str] = None,
        order_direction: str = "DESCENDING",
        limit: int = 100,
    ) -> list[dict]:
        """
        List documents with optional filtering and ordering.

        Args:
            collection: Collection name
            filters: List of (field, op, value) tuples
            order_by: Field to order by
            order_direction: ASCENDING or DESCENDING
            limit: Maximum documents to return
        """
        query = self.db.collection(collection)

        if filters:
            for field, op, value in filters:
                query = query.where(field, op, value)

        if order_by:
            direction = (
                firestore.Query.DESCENDING
                if order_direction == "DESCENDING"
                else firestore.Query.ASCENDING
            )
            query = query.order_by(order_by, direction=direction)

        query = query.limit(limit)

        results = []
        for doc in query.stream():
            data = doc.to_dict()
            data["id"] = doc.id
            results.append(data)

        return results

    def count_documents(
        self,
        collection: str,
        filters: Optional[list[tuple]] = None,
    ) -> int:
        """Count documents matching filters."""
        query = self.db.collection(collection)

        if filters:
            for field, op, value in filters:
                query = query.where(field, op, value)

        # Firestore doesn't have a direct count, so we stream and count
        return sum(1 for _ in query.stream())
