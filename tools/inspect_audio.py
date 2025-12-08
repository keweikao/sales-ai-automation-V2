import os
from google.cloud import storage
import subprocess

BUCKET_NAME = "sales-ai-audio-bucket"
BLOB_NAME = "slack/202512-IC001/202411-122257_桔日員林-Solo_-_鍾志杰.m4a"
LOCAL_FILE = "temp_audio.m4a"

def inspect_audio():
    try:
        # Download
        print(f"Downloading gs://{BUCKET_NAME}/{BLOB_NAME}...")
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(BLOB_NAME)
        blob.download_to_filename(LOCAL_FILE)
        print(f"Downloaded to {LOCAL_FILE} ({os.path.getsize(LOCAL_FILE)} bytes)")

        # Inspect with ffprobe
        cmd = [
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration,bit_rate:stream=codec_type,codec_name", 
            "-of", "json", 
            LOCAL_FILE
        ]
        print("Running ffprobe...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"ffprobe failed: {result.stderr}")
        else:
            print(result.stdout)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if os.path.exists(LOCAL_FILE):
            os.remove(LOCAL_FILE)

if __name__ == "__main__":
    inspect_audio()
