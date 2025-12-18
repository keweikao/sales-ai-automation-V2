import os
import logging
import json
import tempfile
from typing import Optional

import requests
from flask import Flask, request, jsonify
from google.cloud import storage, tasks_v2, firestore
from google.api_core.exceptions import NotFound

from .pipeline import get_pipeline
from .status_tracker import TranscriptionStatusTracker

# --- Initialization ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

# DEBUG: Print version
try:
    with open(os.path.join(os.path.dirname(__file__), "version.txt"), "r") as f:
        version = f.read().strip()
        print(f"DEBUG: APP VERSION: {version}")
        logger.info(f"DEBUG: APP VERSION: {version}")
except Exception as e:
    print(f"DEBUG: VERSION FILE NOT FOUND: {e}")
    logger.error(f"DEBUG: VERSION FILE NOT FOUND: {e}")


# --- Configuration ---
MODEL_SIZE = os.environ.get("MODEL_SIZE", "medium")
DEVICE = os.environ.get("DEVICE", "cpu")
COMPUTE_TYPE = os.environ.get("COMPUTE_TYPE", "int8")
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "3"))
TARGET_CHUNK_DURATION = int(os.environ.get("TARGET_CHUNK_DURATION", "600"))
OVERLAP_DURATION = float(os.environ.get("OVERLAP_DURATION", "2"))
VAD_PRESET = os.environ.get("VAD_PRESET", "meeting")
TRANSCRIPTION_LANGUAGE = os.environ.get("TRANSCRIPTION_LANGUAGE", "zh")
TRANSCRIPTION_ENGINE = "gemini"  # Hardcoded to use Gemini API only (STT Batch API removed)
ENABLE_DIARIZATION = os.getenv("ENABLE_DIARIZATION", "false").lower() == "true"
DIARIZATION_MODEL = os.environ.get("DIARIZATION_MODEL", "pyannote/speaker-diarization")
DIARIZATION_ALLOW_OVERLAP = (
    os.environ.get("DIARIZATION_ALLOW_OVERLAP", "false").lower() == "true"
)
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "sales-ai-automation-v2")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GCP_LOCATION = os.getenv("GCP_LOCATION", "asia-southeast1")

# --- Instantiate Pipeline ---
# We instantiate the pipeline globally to preload the model.
# This is crucial for reducing response time on Cloud Run.
pipeline = None

try:
    get_pipeline() # Initialize pipeline on startup
except Exception as e:
    logger.error(f"Failed to load transcription pipeline: {e}", exc_info=True)
    pipeline = None # Ensure pipeline is None if initialization fails

# --- Firestore Client ---
try:
    db = firestore.Client(project=GCP_PROJECT_ID)
    logger.info(f"Firestore client initialized successfully for project: {GCP_PROJECT_ID}")
except Exception as e:
    logger.error(f"Failed to initialize Firestore: {e}", exc_info=True)
    db = None

status_tracker = TranscriptionStatusTracker(db)

# --- Cloud Tasks Client ---
try:
    tasks_client = tasks_v2.CloudTasksClient()
    logger.info("Cloud Tasks client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Cloud Tasks: {e}", exc_info=True)
    tasks_client = None

# --- Configuration for Analysis Trigger ---
ANALYSIS_QUEUE = "analysis-queue"
ANALYSIS_LOCATION = "asia-east1"
ANALYSIS_SERVICE_URL = os.environ.get(
    "ANALYSIS_SERVICE_URL",
    "https://analysis-service-497329205771.asia-east1.run.app/analyze"
)
SERVICE_ACCOUNT_EMAIL = os.environ.get(
    "SERVICE_ACCOUNT_EMAIL",
    "497329205771-compute@developer.gserviceaccount.com"
)
SLACK_PROGRESS_ENDPOINT = os.environ.get("SLACK_PROGRESS_ENDPOINT")
SLACK_PROGRESS_TOKEN = os.environ.get("SLACK_PROGRESS_TOKEN")


def notify_slack_progress(*, case_id: Optional[str], file_id: Optional[str], status: str) -> None:
    """Send transcription progress to Slack service when configured."""
    if not SLACK_PROGRESS_ENDPOINT or not case_id:
        return

    payload = {
        "caseId": case_id,
        "fileId": file_id,
        "status": status,
    }
    headers = {"Content-Type": "application/json"}
    if SLACK_PROGRESS_TOKEN:
        headers["X-Progress-Token"] = SLACK_PROGRESS_TOKEN

    try:
        response = requests.post(
            SLACK_PROGRESS_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=10,
        )
        if response.status_code >= 300:
            logger.warning(
                "Slack progress webhook returned status %s: %s",
                response.status_code,
                response.text[:256],
            )
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Failed to notify Slack progress endpoint: %s", exc)

# --- Flask Routes ---

@flask_app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    """
    Endpoint to transcribe an audio file using Gemini API.
    
    This endpoint now executes transcription DIRECTLY instead of queuing for batch.
    The response is synchronous - it will wait until transcription completes.
    
    Note: Cloud Tasks should set a long timeout (e.g. 30 minutes) for this endpoint.
    """
    from google.cloud import storage as gcs_storage
    import tempfile
    
    logger.info("Received transcription request (Direct Gemini Mode)")
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing request body"}), 400

    gcs_uri = data.get("gcs_uri") or data.get("gcsPath")
    if not gcs_uri:
        return jsonify({"error": "Missing 'gcs_uri' or 'gcsPath'"}), 400

    case_id = data.get("caseId")
    file_id = data.get("fileId")
    
    if not case_id:
        return jsonify({"error": "Missing 'caseId'"}), 400

    logger.info(f"Processing case {case_id} with Gemini Direct Mode...")
    
    # 1. Update Firestore status to 'transcribing'
    if db:
        try:
            case_ref = db.collection('cases').document(case_id)
            case_ref.set({
                "status": "transcribing",
                "gcsUri": gcs_uri,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }, merge=True)
            if file_id:
                db.collection("processed_files").document(file_id).set({
                    "status": "transcribing",
                    "updatedAt": firestore.SERVER_TIMESTAMP
                }, merge=True)
            
            status_tracker.update(case_id=case_id, file_id=file_id, step="transcribing", detail="開始轉錄...")
            notify_slack_progress(case_id=case_id, file_id=file_id, status="transcribing")
            
        except Exception as e:
            logger.error(f"Failed to update Firestore status: {e}")
            # Continue anyway - transcription is more important

    # 2. Download audio from GCS
    try:
        storage_client = gcs_storage.Client()
        bucket_name = gcs_uri.replace("gs://", "").split("/")[0]
        blob_path = "/".join(gcs_uri.replace("gs://", "").split("/")[1:])
        
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        
        # Create temp file with correct extension
        file_ext = blob_path.split(".")[-1] if "." in blob_path else "mp3"
        with tempfile.NamedTemporaryFile(suffix=f".{file_ext}", delete=False) as tmp_file:
            blob.download_to_filename(tmp_file.name)
            local_path = tmp_file.name
        
        logger.info(f"Downloaded audio to {local_path}")
        
    except Exception as e:
        error_msg = f"Failed to download audio: {e}"
        logger.error(error_msg, exc_info=True)
        if db:
            db.collection('cases').document(case_id).update({
                "status": "transcription_failed",
                "error": error_msg,
                "updatedAt": firestore.SERVER_TIMESTAMP
            })
        return jsonify({"error": error_msg}), 500

    # 3. Transcribe with Gemini
    try:
        gemini_pipeline = get_pipeline()  # Uses global singleton
        result = gemini_pipeline.transcribe(local_path)
        
        # Cleanup temp file
        os.remove(local_path)
        
        if result.get("success"):
            # Save to Firestore
            transcription_data = {
                "text": result.get("full_text", ""),
                "segments": result.get("segments", []),
                "speakers": result.get("speakers", []),
            }
            
            if db:
                db.collection('cases').document(case_id).update({
                    "transcription": transcription_data,
                    "status": "transcribed",
                    "updatedAt": firestore.SERVER_TIMESTAMP
                })
                if file_id:
                    db.collection("processed_files").document(file_id).update({
                        "status": "transcribed",
                        "updatedAt": firestore.SERVER_TIMESTAMP
                    })
            
            # Trigger Analysis
            _trigger_analysis(case_id)
            notify_slack_progress(case_id=case_id, file_id=file_id, status="transcribed")
            
            logger.info(f"Case {case_id} transcribed successfully!")
            return jsonify({
                "status": "success",
                "message": "Transcription completed",
                "caseId": case_id,
                "segmentCount": len(transcription_data.get("segments", [])),
            }), 200
        else:
            error_msg = result.get("error", "Unknown transcription error")
            logger.error(f"Transcription failed: {error_msg}")
            if db:
                db.collection('cases').document(case_id).update({
                    "status": "transcription_failed",
                    "error": error_msg,
                    "updatedAt": firestore.SERVER_TIMESTAMP
                })
            return jsonify({"error": error_msg, "caseId": case_id}), 500
            
    except Exception as e:
        error_msg = f"Transcription exception: {e}"
        logger.error(error_msg, exc_info=True)
        # Cleanup temp file if exists
        try:
            os.remove(local_path)
        except:
            pass
        if db:
            db.collection('cases').document(case_id).update({
                "status": "transcription_failed",
                "error": error_msg,
                "updatedAt": firestore.SERVER_TIMESTAMP
            })
        return jsonify({"error": error_msg, "caseId": case_id}), 500


@flask_app.route("/trigger-batch", methods=["POST"])
def trigger_batch():
    """
    Triggered by Cloud Scheduler or manually.
    For stt_batch engine: Collects 'queued_for_batch' cases and submits them to STT Batch API.
    For gemini engine: Processes cases one by one using Gemini API.
    """
    if not db:
        return jsonify({"error": "Firestore not initialized"}), 500
    
    engine = os.getenv("TRANSCRIPTION_ENGINE", "stt_batch").strip().lower()
    logger.info(f"Trigger batch called with engine: {engine}")
        
    # 1. Query queued cases
    docs = db.collection("cases").where("status", "==", "queued_for_batch").stream()
    
    queued_cases = []
    audio_uris = []
    
    for doc in docs:
        data = doc.to_dict()
        if data.get("gcsUri"):
            queued_cases.append(doc)
            audio_uris.append(data.get("gcsUri"))
            
    if not queued_cases:
        return jsonify({"message": "No cases to process"}), 200
        
    logger.info(f"Found {len(queued_cases)} cases to process.")
    
    # --- Gemini Engine: Process one by one ---
    if engine == "gemini":
        from google.cloud import storage as gcs_storage
        import tempfile
        
        gemini_pipeline = get_pipeline()  # Will use global singleton
        storage_client = gcs_storage.Client()
        processed_count = 0
        
        for doc in queued_cases:
            case_id = doc.id
            data = doc.to_dict()
            gcs_uri = data.get("gcsUri")
            
            logger.info(f"Processing case {case_id} with Gemini...")
            
            try:
                # Update status to processing
                doc.reference.update({
                    "status": "transcribing",
                    "updatedAt": firestore.SERVER_TIMESTAMP
                })
                notify_slack_progress(case_id=case_id, file_id=None, status="transcribing")
                
                # Download audio from GCS
                bucket_name = gcs_uri.replace("gs://", "").split("/")[0]
                blob_path = "/".join(gcs_uri.replace("gs://", "").split("/")[1:])
                
                bucket = storage_client.bucket(bucket_name)
                blob = bucket.blob(blob_path)
                
                # Create temp file with correct extension
                file_ext = blob_path.split(".")[-1] if "." in blob_path else "mp3"
                with tempfile.NamedTemporaryFile(suffix=f".{file_ext}", delete=False) as tmp_file:
                    blob.download_to_filename(tmp_file.name)
                    local_path = tmp_file.name
                
                logger.info(f"Downloaded audio to {local_path}")
                
                # Transcribe with Gemini
                result = gemini_pipeline.transcribe(local_path)
                
                # Cleanup temp file
                os.remove(local_path)
                
                if result.get("success"):
                    # Save to Firestore
                    transcription_data = {
                        "text": result.get("full_text", ""),
                        "segments": result.get("segments", []),
                        "speakers": result.get("speakers", []),
                    }
                    
                    doc.reference.update({
                        "transcription": transcription_data,
                        "status": "transcribed",
                        "updatedAt": firestore.SERVER_TIMESTAMP
                    })
                    
                    # Trigger Analysis
                    _trigger_analysis(case_id)
                    notify_slack_progress(case_id=case_id, file_id=None, status="transcribed")
                    processed_count += 1
                    logger.info(f"Case {case_id} transcribed successfully.")
                else:
                    error_msg = result.get("error", "Unknown error")
                    doc.reference.update({
                        "status": "transcription_failed",
                        "error": error_msg,
                        "updatedAt": firestore.SERVER_TIMESTAMP
                    })
                    logger.error(f"Case {case_id} transcription failed: {error_msg}")
                    
            except Exception as e:
                logger.error(f"Error processing case {case_id}: {e}", exc_info=True)
                doc.reference.update({
                    "status": "transcription_failed",
                    "error": str(e),
                    "updatedAt": firestore.SERVER_TIMESTAMP
                })
        
        return jsonify({"message": f"Gemini transcription complete", "count": processed_count}), 200
    
    # --- STT Batch Engine: Submit to Batch API ---
    else:
        pipeline = get_pipeline(engine="stt_batch", project_id=GCP_PROJECT_ID, location=GCP_LOCATION)
        
        try:
            # 2. Submit Batch
            op_name = pipeline.submit_batch(audio_uris)
            
            # 3. Update Firestore with Operation Name
            batch_ref = db.collection("transcription_batches").document()
            batch_ref.set({
                "operationName": op_name,
                "caseIds": [d.id for d in queued_cases],
                "status": "submitted",
                "createdAt": firestore.SERVER_TIMESTAMP
            })
            
            for doc in queued_cases:
                doc.reference.update({
                    "status": "batch_submitted",
                    "batchId": batch_ref.id,
                    "operationName": op_name,
                    "updatedAt": firestore.SERVER_TIMESTAMP
                })
                # Notify Slack
                notify_slack_progress(case_id=doc.id, file_id=None, status="batch_submitted")
                
            return jsonify({"message": f"Batch submitted: {op_name}", "count": len(queued_cases)}), 200
            
        except Exception as e:
            logger.error(f"Batch submission failed: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500


@flask_app.route("/check-results", methods=["POST"])
def check_results():
    """
    Triggered by Cloud Scheduler.
    Checks status of submitted batches and processes results.
    """
    if not db:
        return jsonify({"error": "Firestore not initialized"}), 500
        
    pipeline = get_pipeline(engine="stt_batch", project_id=GCP_PROJECT_ID, location=GCP_LOCATION)
    
    # 1. Query submitted batches
    batches = db.collection("transcription_batches").where("status", "==", "submitted").stream()
    
    processed_count = 0
    
    for batch_doc in batches:
        batch_data = batch_doc.to_dict()
        op_name = batch_data.get("operationName")
        
        if not op_name:
            continue
            
        try:
            # 2. Check Status
            if pipeline.check_batch_status(op_name):
                logger.info(f"Batch {op_name} completed. Processing results...")
                
                # 3. Get Results
                results_map = pipeline.get_results(op_name)
                
                # 4. Update Cases
                case_ids = batch_data.get("caseIds", [])
                for case_id in case_ids:
                    case_ref = db.collection("cases").document(case_id)
                    case_snap = case_ref.get()
                    if not case_snap.exists:
                        continue
                        
                    case_data = case_snap.to_dict()
                    gcs_uri = case_data.get("gcsUri")
                    
                    if gcs_uri in results_map:
                        result = results_map[gcs_uri]
                        
                        # Save to Firestore
                        transcription_data = {
                            "text": result.get("full_text", ""),
                            "segments": result.get("segments", []),
                            "language": result.get("language", "zh"),
                        }
                        
                        case_ref.update({
                            "transcription": transcription_data,
                            "status": "transcribed",
                            "updatedAt": firestore.SERVER_TIMESTAMP
                        })
                        
                        # Trigger Analysis
                        _trigger_analysis(case_id)
                        notify_slack_progress(case_id=case_id, file_id=None, status="transcribed")
                        
                    else:
                        logger.warning(f"Result not found for case {case_id} (URI: {gcs_uri})")
                        case_ref.update({"status": "transcription_failed", "error": "Result missing in batch output"})

                # 5. Mark Batch as Done
                batch_doc.reference.update({"status": "completed", "updatedAt": firestore.SERVER_TIMESTAMP})
                processed_count += 1
                
        except Exception as e:
            logger.error(f"Error checking batch {op_name}: {e}", exc_info=True)
            
    return jsonify({"message": "Check complete", "batches_processed": processed_count}), 200

def _trigger_analysis(case_id):
    """Helper to trigger analysis service."""
    if tasks_client:
        try:
            queue_path = tasks_client.queue_path(GCP_PROJECT_ID, ANALYSIS_LOCATION, ANALYSIS_QUEUE)
            task_payload = {"caseId": case_id}
            task = {
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": ANALYSIS_SERVICE_URL,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(task_payload).encode(),
                    "oidc_token": {"service_account_email": SERVICE_ACCOUNT_EMAIL}
                }
            }
            tasks_client.create_task(request={"parent": queue_path, "task": task})
            logger.info(f"Analysis triggered for {case_id}")
        except Exception as e:
            logger.error(f"Failed to trigger analysis: {e}")

@flask_app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Cloud Run startup probe."""
    if pipeline:
        return jsonify({"status": "healthy", "pipeline_loaded": True}), 200
    else:
        return jsonify({"status": "unhealthy", "pipeline_loaded": False}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)
