#!/usr/bin/env python3
"""
Fix cases missing gcsUri by downloading from Slack and uploading to GCS.

This script:
1. Finds cases with status=queued_for_batch but no gcsUri
2. Downloads audio from Slack using the fileUrl
3. Uploads to GCS
4. Updates the case with gcsUri

Usage:
    export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"
    export SLACK_BOT_TOKEN="xoxb-..."
    python tools/fix_missing_gcs_uploads.py
"""

import os
import sys
import tempfile
import datetime
from datetime import timezone
from pathlib import Path

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from google.cloud import firestore, storage

# Configuration
GCP_PROJECT = "sales-ai-automation-v2"
GCS_BUCKET = "sales-ai-audio-bucket"


def get_slack_token() -> str:
    """Get Slack token from env var or GCP Secret Manager."""
    token = os.getenv("SLACK_BOT_TOKEN")
    if token:
        return token
    
    # Try to get from Secret Manager
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{GCP_PROJECT}/secrets/slack-bot-token/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"Failed to get Slack token from Secret Manager: {e}")
        return None


SLACK_BOT_TOKEN = get_slack_token()

def download_from_slack(file_url: str, file_name: str) -> Path:
    """Download file from Slack private URL."""
    print(f"  Downloading from Slack: {file_name}")
    
    response = requests.get(
        file_url,
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        stream=True,
        timeout=300,
    )
    response.raise_for_status()
    
    suffix = Path(file_name).suffix or ".m4a"
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    
    with temp_file as fp:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                fp.write(chunk)
    
    file_size = Path(temp_file.name).stat().st_size / 1024 / 1024
    print(f"  Downloaded: {file_size:.2f} MB")
    return Path(temp_file.name)


def upload_to_gcs(local_path: Path, bucket_name: str, destination_blob: str) -> str:
    """Upload file to GCS with retry."""
    print(f"  Uploading to GCS: gs://{bucket_name}/{destination_blob}")
    
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob)
    
    # Use resumable upload with retries
    blob.upload_from_filename(str(local_path), timeout=900, num_retries=3)
    
    gcs_uri = f"gs://{bucket_name}/{destination_blob}"
    print(f"  Uploaded: {gcs_uri}")
    return gcs_uri


def fix_case(db, case_id: str, case_data: dict) -> bool:
    """Fix a single case by downloading from Slack and uploading to GCS."""
    print(f"\nProcessing case: {case_id}")
    
    # Get file info
    audio_info = case_data.get("audio", {})
    file_name = audio_info.get("fileName", f"{case_id}.m4a")
    file_url = case_data.get("fileUrl")
    
    if not file_url:
        print(f"  ❌ No fileUrl found, skipping")
        return False
    
    # Create GCS destination path
    created_at = case_data.get("createdAt", datetime.datetime.now(timezone.utc))
    year_month = created_at.strftime("%Y-%m")
    destination_blob = f"audio/{year_month}/{case_id}/{file_name}"
    
    local_path = None
    try:
        # Download from Slack
        local_path = download_from_slack(file_url, file_name)
        
        # Upload to GCS
        gcs_uri = upload_to_gcs(local_path, GCS_BUCKET, destination_blob)
        
        # Update Firestore
        db.collection("cases").document(case_id).update({
            "gcsUri": gcs_uri,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })
        
        print(f"  ✅ Case updated with gcsUri")
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
        
    finally:
        if local_path and local_path.exists():
            local_path.unlink()


def main():
    if not SLACK_BOT_TOKEN:
        print("Error: SLACK_BOT_TOKEN environment variable is required")
        print("Set it with: export SLACK_BOT_TOKEN='xoxb-...'")
        sys.exit(1)
    
    # Initialize Firestore
    db = firestore.Client(project=GCP_PROJECT)
    
    # Find cases needing fix
    print("Looking for cases with status=queued_for_batch but no gcsUri...")
    print("=" * 80)
    
    yesterday = datetime.datetime.now(timezone.utc) - datetime.timedelta(days=2)
    yesterday_midnight = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    cases = db.collection("cases").stream()
    
    cases_to_fix = []
    for doc in cases:
        data = doc.to_dict()
        created_at = data.get("createdAt")
        status = data.get("status")
        gcs_uri = data.get("gcsUri")
        
        # Only process recent cases that need fixing
        if (created_at and isinstance(created_at, datetime.datetime) and 
            created_at >= yesterday_midnight and
            status in ["queued_for_batch", "pending", "failed", "transcription_failed"] and
            not gcs_uri and
            data.get("fileUrl")):
            cases_to_fix.append((doc.id, data))
    
    print(f"Found {len(cases_to_fix)} case(s) to fix")
    
    if not cases_to_fix:
        print("No cases need fixing!")
        return
    
    # Process each case
    success_count = 0
    for case_id, case_data in cases_to_fix:
        if fix_case(db, case_id, case_data):
            success_count += 1
    
    print("\n" + "=" * 80)
    print(f"Summary: {success_count}/{len(cases_to_fix)} case(s) fixed successfully")
    
    if success_count > 0:
        print("\nNext step: Trigger transcription with:")
        print("  curl -X POST https://transcription-service-497329205771.asia-east1.run.app/trigger-batch")


if __name__ == "__main__":
    main()
