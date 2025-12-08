import os
from google.cloud import storage
import subprocess

BUCKET_NAME = "sales-ai-audio-bucket"
BLOB_NAME = "slack/202512-IC001/202411-122257_桔日員林-Solo_-_鍾志杰.m4a"
LOCAL_FILE = "temp_audio_silence.m4a"

def detect_silence():
    try:
        # Download
        if not os.path.exists(LOCAL_FILE):
            print(f"Downloading gs://{BUCKET_NAME}/{BLOB_NAME}...")
            storage_client = storage.Client()
            bucket = storage_client.bucket(BUCKET_NAME)
            blob = bucket.blob(BLOB_NAME)
            blob.download_to_filename(LOCAL_FILE)
            print(f"Downloaded to {LOCAL_FILE}")

        # Detect silence
        # noise=-30dB (anything quieter is silence), d=1 (minimum 1 second duration)
        cmd = [
            "ffmpeg", 
            "-i", LOCAL_FILE, 
            "-af", "silencedetect=noise=-30dB:d=1", 
            "-f", "null", 
            "-"
        ]
        print("Running silence detection...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # ffmpeg prints silence info to stderr
        print(result.stderr)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if os.path.exists(LOCAL_FILE):
            os.remove(LOCAL_FILE)

if __name__ == "__main__":
    detect_silence()
