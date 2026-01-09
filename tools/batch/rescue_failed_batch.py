import os
import json
import logging
import requests
from google.cloud import firestore

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ID = "sales-ai-automation-v2"
BATCH_STATE_FILE = "tools/batch/.batch_state.completed.json"
TRANSCRIPTION_SERVICE_URL = "https://transcription-service-acv3ye2faq-de.a.run.app"
ANALYSIS_SERVICE_URL = "https://analysis-service-acv3ye2faq-de.a.run.app"

def rescue():
    db = firestore.Client(project=PROJECT_ID)
    
    if not os.path.exists(BATCH_STATE_FILE):
        logger.error(f"State file not found: {BATCH_STATE_FILE}")
        return

    with open(BATCH_STATE_FILE, "r") as f:
        data = json.load(f)

    case_ids = [c['case_id'] for c in data['cases']]
    
    transcribed_count = 0
    failed_count = 0
    
    for case_id in case_ids:
        doc_ref = db.collection("cases").document(case_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            continue
            
        case_data = doc.to_dict()
        status = case_data.get("status")
        
        if status == "transcribed":
            # Check if analysis exists
            if "analysis" not in case_data or not case_data.get("analysis"):
                logger.info(f"Triggering analysis for successful case: {case_id}")
                try:
                    resp = requests.post(f"{ANALYSIS_SERVICE_URL}/analyze", json={"caseId": case_id}, timeout=10)
                    logger.info(f"  Response: {resp.status_code}")
                except Exception as e:
                    logger.error(f"  Failed to trigger analysis: {e}")
            transcribed_count += 1
        else:
            # Re-trigger transcription
            logger.info(f"Re-triggering transcription for failed/pending case: {case_id} (Current status: {status})")
            try:
                # We use /transcribe-single endpoint
                resp = requests.post(f"{TRANSCRIPTION_SERVICE_URL}/transcribe-single", json={"caseId": case_id}, timeout=600)
                logger.info(f"  Response: {resp.status_code}")
                failed_count += 1
            except Exception as e:
                logger.error(f"  Failed to re-trigger transcription: {e}")

    logger.info("="*30)
    logger.info("Rescued Summary:")
    logger.info(f"Successfully Transcribed & Analyzed: {transcribed_count}")
    logger.info(f"Re-triggered for Gemini 3.0: {failed_count}")
    logger.info("="*30)

if __name__ == "__main__":
    rescue()
