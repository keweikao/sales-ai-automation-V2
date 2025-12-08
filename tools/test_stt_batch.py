import os
import time
import requests
import json
import subprocess

# Configuration
PROJECT_ID = "sales-ai-automation-v2"
REGION = "asia-east1"
SERVICE_NAME = "transcription-service"

def get_service_url():
    print("Fetching Service URL...")
    try:
        result = subprocess.run(
            ["gcloud", "run", "services", "describe", SERVICE_NAME, 
             "--platform", "managed", "--region", REGION, "--format", "value(status.url)"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error fetching service URL: {e}")
        return None

def test_workflow():
    base_url = get_service_url()
    if not base_url:
        print("Could not determine service URL. Exiting.")
        return

    print(f"Target Service: {base_url}")

    # 1. Queue a file
    print("\n--- Step 1: Queueing File ---")
    # Use a sample file that exists in GCS. 
    # Assuming 'gs://sales-ai-automation-v2_cloudbuild/sample_audio.m4a' or similar exists?
    # Or just use a dummy path since we are testing the FLOW, not the actual STT (unless we have a real file).
    # Let's use the file from the previous context if available, or a placeholder.
    # The user mentioned '202512-IC001_transcript_fixed.txt' but that's a transcript.
    # I'll use a dummy GCS path for testing the queue logic.
    
    test_gcs_uri = "gs://sales-ai-automation-v2-audio/test_audio.m4a" 
    case_id = f"test_case_{int(time.time())}"
    
    payload = {
        "gcs_uri": test_gcs_uri,
        "caseId": case_id,
        "fileId": "test_file_id"
    }
    
    try:
        resp = requests.post(f"{base_url}/transcribe", json=payload)
        print(f"Response: {resp.status_code} - {resp.text}")
        if resp.status_code != 202:
            print("Failed to queue file.")
            return
    except Exception as e:
        print(f"Request failed: {e}")
        return

    # 2. Trigger Batch
    print("\n--- Step 2: Triggering Batch ---")
    try:
        resp = requests.post(f"{base_url}/trigger-batch")
        print(f"Response: {resp.status_code} - {resp.text}")
        if resp.status_code != 200:
            print("Failed to trigger batch.")
            return
        
        data = resp.json()
        if "Batch submitted" not in data.get("message", ""):
            print("Batch was not submitted (maybe no files queued?).")
            # This might happen if the file validation in submit_batch fails (e.g. bucket inference).
            # But our code infers bucket from URI.
    except Exception as e:
        print(f"Request failed: {e}")
        return

    # 3. Check Results (Polling)
    print("\n--- Step 3: Checking Results ---")
    # In a real test, we'd wait. Here we just trigger the check to see if it runs without error.
    try:
        resp = requests.post(f"{base_url}/check-results")
        print(f"Response: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_workflow()
