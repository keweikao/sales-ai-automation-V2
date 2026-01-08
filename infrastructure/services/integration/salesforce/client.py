"""
Salesforce API Client.

使用 Simple Salesforce 封裝 Salesforce REST API 操作。

Migration note: From crm-service/src/salesforce_client.py
"""

import logging
import os
from typing import Any, Dict, List, Optional

from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceError

logger = logging.getLogger(__name__)


# Salesforce Configuration from environment
SF_CLIENT_ID = os.environ.get("SF_CLIENT_ID")
SF_CLIENT_SECRET = os.environ.get("SF_CLIENT_SECRET")
SF_USERNAME = os.environ.get("SF_USERNAME")
SF_PASSWORD = os.environ.get("SF_PASSWORD")
SF_SECURITY_TOKEN = os.environ.get("SF_SECURITY_TOKEN", "")
SF_DOMAIN = os.environ.get("SF_DOMAIN", "login")  # 'login' for production, 'test' for sandbox
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "sales-ai-automation-v2")


def load_secret(secret_name: str) -> Optional[str]:
    """
    Load a secret from GCP Secret Manager.

    Falls back to environment variable if Secret Manager is unavailable.
    """
    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{GCP_PROJECT_ID}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.warning(f"Failed to load secret '{secret_name}' from Secret Manager: {e}")
        # Fallback to environment variable
        return os.environ.get(secret_name.upper().replace("-", "_"))


def get_salesforce_credentials() -> dict:
    """
    Get Salesforce credentials from environment or Secret Manager.

    Returns dict with: username, password, security_token, client_id, client_secret, domain
    """
    return {
        "username": SF_USERNAME or load_secret("sf-username"),
        "password": SF_PASSWORD or load_secret("sf-password"),
        "security_token": SF_SECURITY_TOKEN or load_secret("sf-security-token") or "",
        "client_id": SF_CLIENT_ID or load_secret("sf-client-id"),
        "client_secret": SF_CLIENT_SECRET or load_secret("sf-client-secret"),
        "domain": SF_DOMAIN,
    }


class SalesforceClient:
    """
    Salesforce API 客戶端.

    封裝 Opportunity 的讀取與更新操作。
    """

    def __init__(self):
        self._sf: Optional[Salesforce] = None

    def _ensure_connection(self) -> Salesforce:
        """確保 Salesforce 連線已建立."""
        if self._sf is None:
            creds = get_salesforce_credentials()

            if not all([creds["username"], creds["password"], creds["client_id"], creds["client_secret"]]):
                raise ValueError("Missing Salesforce credentials. Check environment variables.")

            self._sf = Salesforce(
                username=creds["username"],
                password=creds["password"],
                security_token=creds["security_token"],
                consumer_key=creds["client_id"],
                consumer_secret=creds["client_secret"],
                domain=creds["domain"],
            )
            logger.info("Connected to Salesforce successfully")

        return self._sf

    def get_assigned_opportunities(
        self,
        stage_name: str = "Assigned",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        取得指定階段的 Opportunities.

        Args:
            stage_name: 要查詢的階段名稱
            limit: 最大回傳筆數

        Returns:
            List of Opportunity records
        """
        sf = self._ensure_connection()

        query = f"""
            SELECT Id, Name, StageName, Customer_ID__c,
                   LastModifiedDate, CreatedDate, OwnerId
            FROM Opportunity
            WHERE StageName = '{stage_name}'
            ORDER BY LastModifiedDate DESC
            LIMIT {limit}
        """

        try:
            result = sf.query(query)
            records = result.get("records", [])
            logger.info(f"Fetched {len(records)} opportunities with stage '{stage_name}'")
            return records
        except SalesforceError as e:
            logger.error(f"Failed to query opportunities: {e}")
            raise

    def update_opportunity_stage(
        self,
        opportunity_id: str,
        stage_name: str,
    ) -> bool:
        """
        更新 Opportunity 的 StageName.

        Args:
            opportunity_id: Salesforce Opportunity ID
            stage_name: 新的階段名稱

        Returns:
            True if successful
        """
        sf = self._ensure_connection()

        try:
            sf.Opportunity.update(opportunity_id, {"StageName": stage_name})
            logger.info(f"Updated Opportunity {opportunity_id} to stage '{stage_name}'")
            return True
        except SalesforceError as e:
            logger.error(f"Failed to update opportunity {opportunity_id}: {e}")
            raise

    def update_opportunity(
        self,
        opportunity_id: str,
        fields: Dict[str, Any],
    ) -> bool:
        """
        更新 Opportunity 的多個欄位.

        Args:
            opportunity_id: Salesforce Opportunity ID
            fields: 欄位名稱與值的字典

        Returns:
            True if successful
        """
        sf = self._ensure_connection()

        try:
            sf.Opportunity.update(opportunity_id, fields)
            logger.info(f"Updated Opportunity {opportunity_id} with fields: {list(fields.keys())}")
            return True
        except SalesforceError as e:
            logger.error(f"Failed to update opportunity {opportunity_id}: {e}")
            raise

    def get_opportunity_by_customer_id(
        self,
        customer_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        根據客戶編號查詢 Opportunity.

        Args:
            customer_id: 客戶編號 (Customer_ID__c)

        Returns:
            Opportunity record or None
        """
        sf = self._ensure_connection()

        query = f"""
            SELECT Id, Name, StageName, Customer_ID__c,
                   LastModifiedDate, CreatedDate, OwnerId
            FROM Opportunity
            WHERE Customer_ID__c = '{customer_id}'
            ORDER BY LastModifiedDate DESC
            LIMIT 1
        """

        try:
            result = sf.query(query)
            records = result.get("records", [])
            return records[0] if records else None
        except SalesforceError as e:
            logger.error(f"Failed to query opportunity by customer_id {customer_id}: {e}")
            raise

    # Async wrappers for future compatibility
    async def connect(self) -> bool:
        """Establish connection to Salesforce (async wrapper)."""
        self._ensure_connection()
        return True

    async def get_opportunity(self, opportunity_id: str) -> dict:
        """Get opportunity details (async wrapper)."""
        sf = self._ensure_connection()
        try:
            return sf.Opportunity.get(opportunity_id)
        except SalesforceError as e:
            logger.error(f"Failed to get opportunity {opportunity_id}: {e}")
            raise

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
            related_to: Related record ID (WhatId)
            due_date: Due date string (YYYY-MM-DD)

        Returns:
            Created task ID
        """
        sf = self._ensure_connection()

        task_data = {
            "Subject": subject,
            "Description": description,
            "WhatId": related_to,
            "Status": "Not Started",
        }
        if due_date:
            task_data["ActivityDate"] = due_date

        try:
            result = sf.Task.create(task_data)
            task_id = result.get("id")
            logger.info(f"Created task {task_id} for {related_to}")
            return task_id
        except SalesforceError as e:
            logger.error(f"Failed to create task: {e}")
            raise

    async def log_activity(
        self,
        related_to: str,
        activity_type: str,
        subject: str,
        description: str,
    ) -> str:
        """Log a call or meeting activity."""
        sf = self._ensure_connection()

        task_data = {
            "Subject": subject,
            "Description": description,
            "WhatId": related_to,
            "Status": "Completed",
            "Type": activity_type,
        }

        try:
            result = sf.Task.create(task_data)
            task_id = result.get("id")
            logger.info(f"Logged activity {task_id} for {related_to}")
            return task_id
        except SalesforceError as e:
            logger.error(f"Failed to log activity: {e}")
            raise
