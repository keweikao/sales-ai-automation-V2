import os
import subprocess
import requests
from google.cloud import storage, firestore
from pathlib import Path

# Config
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "sales-ai-automation-v2")
BUCKET_NAME = "sales-ai-audio-bucket"
CASE_ID = "202512-IC002"
# Original URI from previous checks
ORIGINAL_GCS_URI = "gs://sales-ai-audio-bucket/slack/202512-IC002/202511-122428_ZodiacPour-Solo_-_鍾志杰.m4a"

def main():
    db = firestore.Client(project=PROJECT_ID)
    storage_client = storage.Client(project=PROJECT_ID)
    
    # 1. Download
    print(f"Downloading {ORIGINAL_GCS_URI}...")
    blob_name = ORIGINAL_GCS_URI.replace(f"gs://{BUCKET_NAME}/", "")
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_name)
    
    local_input = "temp_input.m4a"
    blob.download_to_filename(local_input)
    
    # 2. Convert
    local_output = "temp_output.mp3"
    print("Converting to MP3...")
    subprocess.run([
        "ffmpeg", "-i", local_input, "-ac", "1", "-ar", "16000", "-y", local_output
    ], check=True)
    
    # 3. Upload
    new_blob_name = str(Path(blob_name).with_suffix(".mp3"))
    print(f"Uploading to gs://{BUCKET_NAME}/{new_blob_name}...")
    new_blob = bucket.blob(new_blob_name)
    new_blob.upload_from_filename(local_output)
    
    new_gcs_uri = f"gs://{BUCKET_NAME}/{new_blob_name}"
    
    # 4. Update Firestore
    print(f"Updating case {CASE_ID}...")
    case_ref = db.collection("cases").document(CASE_ID)
    case_ref.update({
        "gcsUri": new_gcs_uri,
        "status": "queued_for_batch",
        "updatedAt": firestore.SERVER_TIMESTAMP
    })
    
    # 5. Trigger Batch
    print("Triggering batch...")
    service_url = "https://transcription-service-acv3ye2faq-de.a.run.app/trigger-batch"
    try:
        response = requests.post(service_url, timeout=10)
        print(f"Trigger response: {response.status_code} {response.text}")
    except Exception as e:
        print(f"Failed to trigger batch: {e}")

    # Cleanup
    if os.path.exists(local_input):
        os.remove(local_input)
    if os.path.exists(local_output):
        os.remove(local_output)

if __name__ == "__main__":
    main()
