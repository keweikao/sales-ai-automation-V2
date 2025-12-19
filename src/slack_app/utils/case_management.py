"""
Case management helpers for Slack ingestion flow.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

from google.cloud import firestore


def allocate_case_id(
    db: firestore.Client,
    transaction: firestore.Transaction,
    unit: str = "IC"
) -> Tuple[str, str]:
    """
    Allocate a new case ID using a Firestore-backed counter.

    Case IDs follow the pattern: YYYYMM-<UNIT><###>
    (e.g., 202511-IC001). We maintain counters per month/unit
    as documents under the `case_counters` collection to avoid conflicts.

    Returns:
        tuple: (case_id, counter_doc_path)
    """
    unit = unit.upper() if unit else "IC"
    now = datetime.now(tz=timezone.utc)
    month_key = now.strftime("%Y%m")
    doc_id = f"{month_key}_{unit}"
    counter_ref = db.collection("case_counters").document(doc_id)

    snapshot = counter_ref.get(transaction=transaction)
    if snapshot.exists:
        data = snapshot.to_dict() or {}
        current_seq = int(data.get("sequence", 0)) + 1
        transaction.update(counter_ref, {
            "sequence": current_seq,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })
    else:
        current_seq = 1
        transaction.set(counter_ref, {
            "sequence": current_seq,
            "unit": unit,
            "month": month_key,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })

    case_id = f"{month_key}-{unit}{current_seq:03d}"
    return case_id, doc_id


def build_initial_case_document(
    case_id: str,
    customer: Dict[str, Optional[str]],
    sales_rep: Dict[str, Optional[str]],
    file_info: Dict[str, Any],
    channel_id: str,
    message_ts: Optional[str],
    thread_ts: Optional[str],
    notes: Optional[str] = None,
    demo_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Prepare the initial Firestore document for `cases/{case_id}`.
    
    Args:
        demo_meta: Optional dict with keys: store_type, service_type, 
                   decision_maker_onsite, current_pos
    """
    unit = (sales_rep.get("unit") or "IC").upper()
    customer_phone = customer.get("phone", "") or ""
    customer_email = customer.get("email", "") or ""

    case_doc = {
        "caseId": case_id,
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP,
        "status": "pending",
        "sourceType": "slack",
        "customerName": customer.get("name", ""),
        "customerId": customer.get("id", ""),
        "customerPhone": customer_phone,
        "customerEmail": customer_email,
        "salesRepName": sales_rep.get("name", ""),
        "salesRepEmail": sales_rep.get("email", ""),
        "salesRepSlackId": sales_rep.get("slack_id", ""),
        "uploadedBy": sales_rep.get("slack_id", ""),
        "uploadedByName": sales_rep.get("name", ""),
        "uploadedBySlackName": sales_rep.get("slack_display_name", "") or sales_rep.get("name", ""),
        "channelId": channel_id,
        "channelName": None,
        "threadTs": thread_ts or message_ts,
        "fileUrl": file_info.get("url_private", ""),
        "unit": unit,
        "notes": notes or "",
        "audio": {
            "fileName": file_info.get("name", ""),
            "slackFileId": file_info.get("id", ""),
            "fileSize": file_info.get("size"),
            "format": file_info.get("type", ""),
            "duration": file_info.get("duration"),
            "uploadedAt": firestore.SERVER_TIMESTAMP,
        },
        "notification": {
            "slackChannelId": channel_id,
            "slackThreadTs": thread_ts or message_ts,
            "slackFileId": file_info.get("id", ""),
            "messageTs": message_ts,
        },
        "retryCount": 0,
        "metadata": {
            "ingestSource": "slack",
            "ingestedAt": firestore.SERVER_TIMESTAMP,
        },
    }

    # Add demo_meta if provided
    if demo_meta:
        case_doc["demoMeta"] = {
            "storeType": demo_meta.get("store_type", ""),
            "serviceType": demo_meta.get("service_type", ""),
            "decisionMakerOnsite": demo_meta.get("decision_maker_onsite"),
            "currentPos": demo_meta.get("current_pos", ""),
        }

    return case_doc


def build_processed_file_document(
    case_id: str,
    file_info: Dict[str, Any],
    customer: Dict[str, Optional[str]],
    sales_rep: Dict[str, Optional[str]],
    channel_id: str,
    message_ts: Optional[str],
    thread_ts: Optional[str],
) -> Dict[str, Any]:
    """Prepare the initial Firestore document for `processed_files/{file_id}`."""
    return {
        "slackFileId": file_info.get("id", ""),
        "status": "processing",
        "locked": True,
        "lockedAt": firestore.SERVER_TIMESTAMP,
        "processedBy": sales_rep.get("slack_id", ""),
        "channelId": channel_id,
        "messageTs": message_ts,
        "threadTs": thread_ts or message_ts,
        "fileName": file_info.get("name", ""),
        "fileSize": file_info.get("size"),
        "customerName": customer.get("name", ""),
        "customerId": customer.get("id", ""),
        "customerPhone": customer.get("phone", "") or "",
        "caseId": case_id,
        "submittedAt": firestore.SERVER_TIMESTAMP,
    }
