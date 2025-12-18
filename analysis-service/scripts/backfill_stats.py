import os
import sys
import logging
from datetime import datetime
from google.cloud import firestore

# Setup path to import 'src'
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '../src')
sys.path.append(src_path)

from services.stats_service import StatsService

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def backfill_stats(start_date_str: str):
    """
    Backfill stats from a given start date.
    """
    project_id = os.environ.get("GCP_PROJECT_ID", "sales-ai-automation-v2")
    logger.info(f"Initializing Firestore with project: {project_id}")
    db = firestore.Client(project=project_id)
    
    stats_service = StatsService(db)
    
    # Parse start date
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    logger.info(f"Scanning cases created on or after: {start_date}")

    # Query Cases
    # Note: 'createdAt' might be a string or Timestamp. 
    # For safety in this script, we'll fetch recent cases and filter in Python if needed, 
    # but querying is better. Let's try string (ISO) comparison first as my model usually uses strings,
    # but Firestore often stores as Map. Let's check a case structure if we fail, but for now assume typical usage.
    # Actually, in main.py we saw 'createdAt': case_data.get('createdAt'). 
    # If it is ISO string, lexical comparison works.
    
    cases_ref = db.collection("cases")
    # We will just fetch all recent ones to be safe and filter in memory to avoid index issues if they don't exist
    # (unless volume is huge, but user said "this week", so volume is likely manageable).
    
    all_cases = cases_ref.stream()
    
    count = 0
    updated = 0
    
    for case in all_cases:
        data = case.to_dict()
        created_at_raw = data.get("createdAt")
        
        if not created_at_raw:
            continue
            
        case_date = None
        if isinstance(created_at_raw, datetime):
            case_date = created_at_raw
        elif isinstance(created_at_raw, str):
            try:
                # Handle ISO 8601
                case_date = datetime.fromisoformat(created_at_raw.replace('Z', '+00:00'))
            except ValueError:
                continue
                
        if case_date and case_date >= start_date.replace(tzinfo=case_date.tzinfo):
            logger.info(f"Processing case: {case.id} ({case_date})")
            
            # Patch missing SalesRep if uploadedBy exists
            if not data.get("salesRep") and data.get("uploadedBy"):
                uploaded_by = data.get("uploadedBy")
                if uploaded_by.startswith("U"): # Simple check for Slack ID
                    logger.info(f"Patching salesRep for {case.id} using uploadedBy: {uploaded_by}")
                    sales_rep_patch = {
                        "slack_id": uploaded_by,
                        "name": f"User {uploaded_by}" # Placeholder name
                    }
                    # Update local data object for stats
                    data["salesRep"] = sales_rep_patch
                    
                    # Update Firestore Case (Optional, but good for consistency)
                    try:
                        cases_ref.document(case.id).update({"salesRep": sales_rep_patch})
                    except Exception as patch_e:
                        logger.warning(f"Failed to persist salesRep patch for {case.id}: {patch_e}")

            try:
                stats_service.update_daily_stats(case.id, data)
                updated += 1
            except Exception as e:
                logger.error(f"Failed to update stats for {case.id}: {e}")
        
        count += 1
        
    logger.info(f"Backfill Complete. Scanned {count} cases. Updated {updated} stats entries.")

if __name__ == "__main__":
    # Default to 2025-12-16 as requested
    backfill_stats("2025-12-16")
