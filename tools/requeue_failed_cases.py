#!/usr/bin/env python3
"""Requeue failed transcription cases from yesterday."""

import datetime
from datetime import timezone
from google.cloud import firestore

# Initialize Firestore
db = firestore.Client(project='sales-ai-automation-v2')

# Calculate yesterday's date (midnight UTC)
yesterday = datetime.datetime.now(timezone.utc) - datetime.timedelta(days=1)
yesterday_midnight = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)

print(f"Looking for failed cases since: {yesterday_midnight.isoformat()}")
print("=" * 80)

# Query all cases
cases_ref = db.collection('cases')
cases = cases_ref.stream()

requeued_count = 0
for case in cases:
    data = case.to_dict()
    case_id = case.id
    created_at = data.get('createdAt')
    status = data.get('status')
    
    # Check if case was created recently and failed
    if created_at and isinstance(created_at, datetime.datetime):
        if created_at >= yesterday_midnight:
            if status in ['failed', 'transcription_failed', 'pending']:
                print(f"Requeuing case: {case_id}")
                print(f"  Original status: {status}")
                print(f"  GCS URI: {data.get('gcsUri', 'N/A')}")
                
                # Reset status to trigger re-transcription
                case.reference.update({
                    'status': 'queued_for_batch',
                    'error': firestore.DELETE_FIELD,
                    'updatedAt': firestore.SERVER_TIMESTAMP,
                })
                
                requeued_count += 1
                print(f"  ✅ Status updated to 'queued_for_batch'")
                print("-" * 40)

print("\n" + "=" * 80)
print(f"Summary: {requeued_count} case(s) requeued for transcription")
print("\nNote: Cases will be processed when the /trigger-batch endpoint is called")
print("or automatically by Cloud Scheduler if configured.")
