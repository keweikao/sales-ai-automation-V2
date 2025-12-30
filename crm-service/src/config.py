"""
CRM Service Configuration.

從環境變數或 Secret Manager 載入 Salesforce 憑證。
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Salesforce Configuration
SF_CLIENT_ID = os.environ.get("SF_CLIENT_ID")
SF_CLIENT_SECRET = os.environ.get("SF_CLIENT_SECRET")
SF_USERNAME = os.environ.get("SF_USERNAME")
SF_PASSWORD = os.environ.get("SF_PASSWORD")
SF_SECURITY_TOKEN = os.environ.get("SF_SECURITY_TOKEN", "")
SF_DOMAIN = os.environ.get("SF_DOMAIN", "login")  # 'login' for production, 'test' for sandbox

# GCP Configuration
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "sales-ai-automation-v2")

# Slack Notification (for errors)
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

# Internal Service Communication
ANALYSIS_SERVICE_URL = os.environ.get("ANALYSIS_SERVICE_URL")


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
