"""
Salesforce API Client.

使用 Simple Salesforce 封裝 Salesforce REST API 操作。
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceError

from .config import get_salesforce_credentials

logger = logging.getLogger(__name__)


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
