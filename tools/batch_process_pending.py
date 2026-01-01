import os
import json
import logging
from datetime import datetime, timezone
from google.cloud import firestore, tasks_v2

# Configuration
PROJECT_ID = "sales-ai-automation-v2"
LOCATION = "asia-east1"
QUEUE = "transcription-queue"
TRANSCRIPTION_SERVICE_URL = "https://transcription-service-497329205771.asia-east1.run.app"
SERVICE_ACCOUNT_EMAIL = "497329205771-compute@developer.gserviceaccount.com"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    db = firestore.Client(project=PROJECT_ID)
    tasks_client = tasks_v2.CloudTasksClient()
    queue_path = tasks_client.queue_path(PROJECT_ID, LOCATION, QUEUE)

    # 1. Query pending cases
    start_date = datetime(2025, 12, 16, tzinfo=timezone.utc)
    cases_ref = db.collection("cases")
    all_cases = list(cases_ref.stream())
    
    pending_cases = []
    
    print("Scanning for pending cases...")
    
    for doc in all_cases:
        data = doc.to_dict()
        case_id = doc.id
        
        # Filter by date and ID
        created_at = data.get('createdAt') or data.get('created_at') or data.get('uploadedAt')
        is_recent = False
        
        if created_at:
             if hasattr(created_at, 'timestamp'):
                 created_dt = created_at
                 if hasattr(created_at, 'seconds'):
                     created_dt = datetime.fromtimestamp(created_at.seconds, tz=timezone.utc)
             elif isinstance(created_at, datetime):
                 created_dt = created_at
                 if created_dt.tzinfo is None:
                     created_dt = created_dt.replace(tzinfo=timezone.utc)
             else:
                 created_dt = None
                 
             if created_dt and created_dt >= start_date:
                 is_recent = True
        
        if not is_recent:
            if not (case_id.startswith('202512') or case_id.startswith('202601')):
                continue
                
        # Filter by status
        status = data.get('status', 'unknown')
        transcription = data.get('transcription')
        
        has_transcription = (
            transcription is not None and 
            isinstance(transcription, dict) and 
            (transcription.get('text') or transcription.get('segments'))
        )
        
        if not has_transcription:
            pending_cases.append(doc)

    print(f"Found {len(pending_cases)} pending cases.")
    if not pending_cases:
        return

    # 2. Process each case
    processed_count = 0
    for doc in pending_cases:
        case_id = doc.id
        data = doc.to_dict()
        gcs_uri = data.get("gcsUri")
        
        if not gcs_uri:
            print(f"Skipping {case_id}: No GCS URI")
            continue
            
        print(f"Queueing case {case_id} ({gcs_uri})...")
        
        # Update Firestore
        try:
            doc.reference.update({
                "status": "queued_for_batch",
                "updatedAt": firestore.SERVER_TIMESTAMP
            })
        except Exception as e:
            print(f"Failed to update Firestore for {case_id}: {e}")
            continue

        # Enqueue Task
        try:
            task = {
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": f"{TRANSCRIPTION_SERVICE_URL}/transcribe-single",
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"caseId": case_id}).encode(),
                    "oidc_token": {
                        "service_account_email": SERVICE_ACCOUNT_EMAIL,
                    },
                }
            }
            tasks_client.create_task(request={"parent": queue_path, "task": task})
            processed_count += 1
            print(f"Task created for {case_id}")
            
        except Exception as e:
            print(f"Failed to create task for {case_id}: {e}")
            
    print(f"Successfully queued {processed_count} cases.")

if __name__ == "__main__":
    main()
