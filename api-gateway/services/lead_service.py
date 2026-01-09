"""
Lead Service for Firestore operations.
"""

from typing import Optional


from deps.firestore import FirestoreService


class LeadService(FirestoreService):
    """Service for lead-related Firestore operations."""

    COLLECTION = "leads"

    def list_leads(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        List leads with optional status filter.

        Args:
            status: Filter by status (new/contacted/qualified/converted)
            limit: Maximum leads to return
        """
        filters = []
        if status:
            filters.append(("status", "==", status))

        return self.list_documents(
            collection=self.COLLECTION,
            filters=filters if filters else None,
            order_by="createdAt",
            order_direction="DESCENDING",
            limit=limit,
        )

    def get_lead(self, lead_id: str) -> Optional[dict]:
        """Get a single lead by ID."""
        return self.get_document(self.COLLECTION, lead_id)

    def get_lead_stats(self) -> dict:
        """Get lead statistics by status."""
        stats = {
            "total": 0,
            "new": 0,
            "contacted": 0,
            "qualified": 0,
            "converted": 0,
        }

        for doc in self.db.collection(self.COLLECTION).stream():
            stats["total"] += 1
            status = doc.to_dict().get("status", "new")
            if status in stats:
                stats[status] += 1

        return stats
