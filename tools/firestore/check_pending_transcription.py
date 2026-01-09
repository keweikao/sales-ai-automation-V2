"""
查詢 12/16 至今尚未完成轉錄的音檔
"""
import os
from datetime import datetime, timezone
from google.cloud import firestore

# Initialize Firestore client
project_id = os.environ.get("GCP_PROJECT_ID", "sales-ai-automation-v2")
db = firestore.Client(project=project_id)

# Query cases collection
cases_ref = db.collection("cases")

# Get all cases since 2025-12-16 (use timezone-aware datetime)
start_date = datetime(2025, 12, 16, tzinfo=timezone.utc)

# Query all cases
print("=" * 60)
print("查詢 2025-12-16 以來的案件 (Case ID: 202512*)...")
print("=" * 60)

# Get all documents and filter
all_cases = list(cases_ref.stream())

# Filter for 202512 cases only
all_cases = [doc for doc in all_cases if doc.id.startswith('202512')]

pending_transcription = []
completed_transcription = []
failed_cases = []

for doc in all_cases:
    data = doc.to_dict()
    case_id = doc.id
    
    # Check created date (handle various date formats)
    created_at = data.get('createdAt') or data.get('created_at') or data.get('uploadedAt')
    
    # Skip if we can't determine the date or if it's before 12/16
    if created_at:
        if hasattr(created_at, 'timestamp'):  # Firestore Timestamp
            created_dt = created_at
            # Convert to datetime for comparison
            if hasattr(created_at, 'seconds'):
                created_dt = datetime.fromtimestamp(created_at.seconds, tz=timezone.utc)
        elif isinstance(created_at, datetime):
            # Make sure it's timezone-aware
            if created_at.tzinfo is None:
                created_dt = created_at.replace(tzinfo=timezone.utc)
            else:
                created_dt = created_at
        else:
            continue
            
        if created_dt < start_date:
            continue
    else:
        # If no date, check if case_id starts with 202512 or later
        if not (case_id.startswith('202512') or case_id.startswith('202601')):
            continue
    
    status = data.get('status', 'unknown')
    transcription = data.get('transcription')
    customer_name = data.get('customerName', 'N/A')
    rep_name = data.get('repName', 'N/A')
    gcs_uri = data.get('gcsUri', 'N/A')
    
    # Check if transcription exists and is complete
    has_transcription = (
        transcription is not None and 
        isinstance(transcription, dict) and 
        (transcription.get('text') or transcription.get('segments'))
    )
    
    case_info = {
        'case_id': case_id,
        'customer_name': customer_name,
        'rep_name': rep_name,
        'status': status,
        'gcs_uri': gcs_uri,
        'created_at': str(created_at) if created_at else 'N/A'
    }
    
    if status == 'failed' or status == 'error':
        failed_cases.append(case_info)
    elif not has_transcription:
        pending_transcription.append(case_info)
    else:
        completed_transcription.append(case_info)

# Print summary
print("\n📊 統計摘要 (2025-12-16 至今)")
print("-" * 40)
print(f"✅ 已完成轉錄: {len(completed_transcription)} 個")
print(f"⏳ 尚未轉錄:   {len(pending_transcription)} 個")
print(f"❌ 失敗案件:   {len(failed_cases)} 個")
print(f"📁 總計案件:   {len(completed_transcription) + len(pending_transcription) + len(failed_cases)} 個")

if pending_transcription:
    print("\n\n📋 尚未轉錄的案件樣例 (前 5 筆):")
    print("-" * 60)
    for i, case in enumerate(pending_transcription[:5], 1):
        print(f"\n{i}. Case ID: {case['case_id']}")
        print(f"   客戶: {case['customer_name']}")
        print(f"   業務: {case['rep_name']}")
        print(f"   狀態: {case['status']}")
        print(f"   建立時間: {case['created_at']}")

if failed_cases:
    print("\n\n❌ 失敗的案件樣例 (前 5 筆):")
    print("-" * 60)
    for i, case in enumerate(failed_cases[:5], 1):
        print(f"\n{i}. Case ID: {case['case_id']}")
        print(f"   客戶: {case['customer_name']}")
        print(f"   狀態: {case['status']}")

# Print summary at the very end to ensure visibility
print("\n" + "=" * 60)
print("📊 最終統計摘要 (2025-12-16 至今, Case ID: 202512*)")
print("-" * 40)
print(f"✅ 已完成轉錄: {len(completed_transcription)} 個")
print(f"⏳ 尚未轉錄:   {len(pending_transcription)} 個")
print(f"❌ 失敗案件:   {len(failed_cases)} 個")
print(f"📁 總計案件:   {len(completed_transcription) + len(pending_transcription) + len(failed_cases)} 個")
print("=" * 60)
