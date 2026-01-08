"""
Salesforce client for CRM integration.

NOTE: Current implementation in crm-service/src/salesforce_client.py
This will contain the migrated code.
"""

from typing import Any, Optional


class SalesforceClient:
    """
    Client for Salesforce API operations.

    Migration status: PENDING
    Current implementation: crm-service/src/salesforce_client.py
    """

    def __init__(
        self,
        instance_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        self.instance_url = instance_url
        self.client_id = client_id
        self.client_secret = client_secret
        self._session = None

    async def connect(self) -> bool:
        """Establish connection to Salesforce."""
        # TODO: Migrate OAuth flow from crm-service
        raise NotImplementedError(
            "Salesforce client not yet migrated. "
            "Use crm-service directly during migration."
        )

    async def get_opportunity(self, opportunity_id: str) -> dict:
        """Get opportunity details."""
        raise NotImplementedError("Not yet migrated")

    async def update_opportunity(
        self,
        opportunity_id: str,
        data: dict[str, Any],
    ) -> bool:
        """
        Update opportunity with analysis data.

        Args:
            opportunity_id: Salesforce opportunity ID
            data: Fields to update

        Returns:
            Success status
        """
        raise NotImplementedError("Not yet migrated")

    async def create_task(
        self,
        subject: str,
        description: str,
        related_to: str,
        due_date: Optional[str] = None,
    ) -> str:
        """
        Create a follow-up task.

        Args:
            subject: Task subject
            description: Task description
            related_to: Related record ID
            due_date: Due date string

        Returns:
            Created task ID
        """
        raise NotImplementedError("Not yet migrated")

    async def log_activity(
        self,
        related_to: str,
        activity_type: str,
        subject: str,
        description: str,
    ) -> str:
        """Log a call or meeting activity."""
        raise NotImplementedError("Not yet migrated")
