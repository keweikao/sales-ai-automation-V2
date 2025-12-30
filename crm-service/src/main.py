"""
CRM Service - Main Flask Application.

提供 Salesforce 整合的 REST API endpoints。
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional

from flask import Flask, jsonify, request
from google.cloud import firestore

from .config import GCP_PROJECT_ID, SLACK_WEBHOOK_URL
from .salesforce_client import SalesforceClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize clients
db: Optional[firestore.Client] = None
sf_client: Optional[SalesforceClient] = None

try:
    db = firestore.Client(project=GCP_PROJECT_ID)
    logger.info(f"Connected to Firestore project: {GCP_PROJECT_ID}")
except Exception as e:
    logger.error(f"Failed to initialize Firestore: {e}")

try:
    sf_client = SalesforceClient()
    logger.info("Salesforce client initialized")
except Exception as e:
    logger.warning(f"Salesforce client initialization deferred: {e}")


def notify_slack_error(error_message: str, context: dict = None):
    """Send error notification to Slack."""
    if not SLACK_WEBHOOK_URL:
        return
    
    try:
        import requests
        
        payload = {
            "text": f"⚠️ CRM Service Error",
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "⚠️ CRM Service Error"}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"```{error_message}```"}
                },
            ]
        }
        
        if context:
            payload["blocks"].append({
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"Context: {json.dumps(context, ensure_ascii=False)}"}
                ]
            })
        
        requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
    except Exception as e:
        logger.error(f"Failed to send Slack notification: {e}")


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "crm-service",
        "timestamp": datetime.utcnow().isoformat(),
    })


@app.route("/sync-opportunities", methods=["POST"])
def sync_opportunities():
    """
    從 Salesforce 同步 Assigned 狀態的 Opportunities 到 Firestore.
    
    由 Cloud Scheduler 每日 8PM 觸發。
    """
    try:
        if sf_client is None:
            raise ValueError("Salesforce client not initialized")
        
        # 取得 Assigned 狀態的 Opportunities
        opportunities = sf_client.get_assigned_opportunities(stage_name="Assigned")
        
        synced_count = 0
        for opp in opportunities:
            customer_id = opp.get("Customer_ID__c")
            if not customer_id:
                continue
            
            # 查詢 Firestore 中是否有對應的 case
            cases_query = (
                db.collection("cases")
                .where("customer.id", "==", customer_id)
                .limit(1)
            )
            
            cases = list(cases_query.stream())
            
            if cases:
                # 更新現有 case
                case_ref = cases[0].reference
                case_ref.update({
                    "sfOpportunityId": opp["Id"],
                    "sfAssignedAt": opp.get("LastModifiedDate"),
                    "sfSyncedAt": firestore.SERVER_TIMESTAMP,
                })
                synced_count += 1
            else:
                # 建立 pending record (等待音檔上傳)
                db.collection("sf_pending_opportunities").document(customer_id).set({
                    "customerId": customer_id,
                    "sfOpportunityId": opp["Id"],
                    "sfOpportunityName": opp.get("Name"),
                    "sfAssignedAt": opp.get("LastModifiedDate"),
                    "syncedAt": firestore.SERVER_TIMESTAMP,
                    "status": "pending",
                })
        
        logger.info(f"Synced {synced_count} opportunities, created {len(opportunities) - synced_count} pending records")
        
        return jsonify({
            "status": "success",
            "synced": synced_count,
            "pending": len(opportunities) - synced_count,
            "total": len(opportunities),
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"sync-opportunities failed: {error_msg}")
        notify_slack_error(error_msg, {"endpoint": "sync-opportunities"})
        return jsonify({"status": "error", "message": error_msg}), 500


@app.route("/update-status", methods=["POST"])
def update_status():
    """
    更新 Salesforce Opportunity 的 StageName.
    
    Request body:
    {
        "customerId": "CU123",
        "stageName": "Meeting Completed"
    }
    """
    try:
        data = request.get_json()
        customer_id = data.get("customerId")
        stage_name = data.get("stageName", "Meeting Completed")
        
        if not customer_id:
            return jsonify({"status": "error", "message": "Missing customerId"}), 400
        
        if sf_client is None:
            raise ValueError("Salesforce client not initialized")
        
        # 查詢對應的 Opportunity
        opp = sf_client.get_opportunity_by_customer_id(customer_id)
        
        if not opp:
            return jsonify({
                "status": "not_found",
                "message": f"No opportunity found for customer {customer_id}"
            }), 404
        
        # 更新 StageName
        sf_client.update_opportunity_stage(opp["Id"], stage_name)
        
        # 更新 Firestore
        if db:
            cases_query = (
                db.collection("cases")
                .where("customer.id", "==", customer_id)
                .limit(1)
            )
            
            for case in cases_query.stream():
                case.reference.update({
                    "sfStageUpdatedAt": firestore.SERVER_TIMESTAMP,
                    "sfStageName": stage_name,
                })
        
        return jsonify({
            "status": "success",
            "opportunityId": opp["Id"],
            "newStage": stage_name,
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"update-status failed: {error_msg}")
        notify_slack_error(error_msg, {"endpoint": "update-status", "customerId": customer_id})
        return jsonify({"status": "error", "message": error_msg}), 500


@app.route("/backfill-fields", methods=["POST"])
def backfill_fields():
    """
    將 Agent 6 擷取的欄位回填到 Salesforce.
    
    Request body:
    {
        "customerId": "CU123",
        "fields": {
            "StageName": "Needs Analysis",
            "Budget__c": "50萬-100萬",
            "Next_Steps__c": "下週約老闆 Demo"
        }
    }
    """
    try:
        data = request.get_json()
        customer_id = data.get("customerId")
        fields = data.get("fields", {})
        
        if not customer_id:
            return jsonify({"status": "error", "message": "Missing customerId"}), 400
        
        if not fields:
            return jsonify({"status": "error", "message": "No fields to update"}), 400
        
        if sf_client is None:
            raise ValueError("Salesforce client not initialized")
        
        # 查詢對應的 Opportunity
        opp = sf_client.get_opportunity_by_customer_id(customer_id)
        
        if not opp:
            return jsonify({
                "status": "not_found",
                "message": f"No opportunity found for customer {customer_id}"
            }), 404
        
        # 更新多個欄位
        sf_client.update_opportunity(opp["Id"], fields)
        
        return jsonify({
            "status": "success",
            "opportunityId": opp["Id"],
            "updatedFields": list(fields.keys()),
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"backfill-fields failed: {error_msg}")
        notify_slack_error(error_msg, {"endpoint": "backfill-fields", "customerId": customer_id})
        return jsonify({"status": "error", "message": error_msg}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
