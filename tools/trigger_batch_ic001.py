import json
import logging
import requests
import google.auth.transport.requests
import google.oauth2.id_token

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERVICE_URL = "https://transcription-service-497329205771.asia-east1.run.app/transcribe_batch"
CASE_ID = "202512-IC001"
GCS_URI = "gs://sales-ai-audio-bucket/slack/202512-IC001/202411-122257_桔日員林-Solo_-_鍾志杰.m4a"

def get_id_token(url):
    """Get OIDC ID token for authentication."""
    auth_req = google.auth.transport.requests.Request()
    return google.oauth2.id_token.fetch_id_token(auth_req, url)

def trigger_batch_transcription():
    logger.info(f"Triggering Batch Transcription for {CASE_ID}...")
    
    try:
        # Get ID Token
        token = get_id_token(SERVICE_URL)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "caseId": CASE_ID,
            "gcs_uri": GCS_URI
        }
        
        response = requests.post(SERVICE_URL, json=payload, headers=headers)
        
        if response.status_code == 200:
            logger.info("Batch Job Submitted Successfully!")
            logger.info(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        else:
            logger.error(f"Failed to submit batch job. Status: {response.status_code}")
            logger.error(f"Response: {response.text}")
            
    except Exception as e:
        logger.error(f"Error triggering batch transcription: {e}")

if __name__ == "__main__":
    trigger_batch_transcription()
