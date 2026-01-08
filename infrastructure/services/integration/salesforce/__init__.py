"""
Salesforce Integration

Syncs data between Sales AI and Salesforce CRM.

NOTE: Current implementation in crm-service/src/
Will be migrated here.

Usage:
    from infrastructure.services.integration.salesforce import SalesforceClient

    client = SalesforceClient()
    await client.update_opportunity(opportunity_id, data)
"""

from .client import SalesforceClient

__all__ = ["SalesforceClient"]
