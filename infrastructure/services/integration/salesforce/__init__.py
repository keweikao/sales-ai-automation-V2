"""
Salesforce Integration

Syncs data between Sales AI and Salesforce CRM.

Migration note: From crm-service/src/

Usage:
    from infrastructure.services.integration.salesforce import SalesforceClient

    client = SalesforceClient()
    client.update_opportunity_stage(opportunity_id, "Needs Analysis")
"""

from .client import (
    SalesforceClient,
    get_salesforce_credentials,
    load_secret,
)

__all__ = [
    "SalesforceClient",
    "get_salesforce_credentials",
    "load_secret",
]
