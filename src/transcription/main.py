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
TRANSCRIPTION_ENGINE = os.environ.get("TRANSCRIPTION_ENGINE", "groq_whisper")
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

# --- Serial Processing Configuration ---
# Key in Firestore to store pending transcription queue
SERIAL_QUEUE_COLLECTION = "transcription_queue"
SERIAL_QUEUE_DOC = "pending_cases"

# --- Cloud Tasks Configuration for Transcription Queue ---
TRANSCRIPTION_QUEUE = "transcription-queue"
TRANSCRIPTION_LOCATION = "asia-east1"
TRANSCRIPTION_SERVICE_URL = os.environ.get(
    "TRANSCRIPTION_SERVICE_URL",
    "https://transcription-service-497329205771.asia-east1.run.app"
)


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

    # 2. Get pipeline and determine processing method
    try:
        pipeline_instance = get_pipeline()  # Uses global singleton
        engine = os.environ.get("TRANSCRIPTION_ENGINE", "groq_whisper")

        # Groq Whisper and Gemini require local file - download from GCS
        if True:  # Always download for groq_whisper and gemini
            # Download from GCS
            from google.cloud import storage as gcs_storage
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
            result = pipeline_instance.transcribe(local_path)
            
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


@flask_app.route("/transcribe-single", methods=["POST"])
def transcribe_single():
    """
    Process a SINGLE transcription case. Called by Cloud Tasks.
    Expects JSON body: { "caseId": "...", "serial": true/false }

    If "serial" is true, will trigger next case from the queue after completion.
    """
    if not db:
        return jsonify({"error": "Firestore not initialized"}), 500

    data = request.get_json()
    case_id = data.get("caseId") if data else None
    is_serial = data.get("serial", False) if data else False

    if not case_id:
        return jsonify({"error": "Missing caseId"}), 400

    logger.info(f"Processing single case: {case_id} (serial={is_serial})")

    # Fetch case from Firestore
    doc_ref = db.collection("cases").document(case_id)
    doc = doc_ref.get()

    if not doc.exists:
        # If serial mode, trigger next even if this case not found
        if is_serial:
            _trigger_next_transcription()
        return jsonify({"error": f"Case {case_id} not found"}), 404

    case_data = doc.to_dict()
    gcs_uri = case_data.get("gcsUri")

    if not gcs_uri:
        if is_serial:
            _trigger_next_transcription()
        return jsonify({"error": f"Case {case_id} has no gcsUri"}), 400

    engine = os.getenv("TRANSCRIPTION_ENGINE", "groq_whisper").strip().lower()

    try:
        # Update status to transcribing
        doc_ref.update({
            "status": "transcribing",
            "updatedAt": firestore.SERVER_TIMESTAMP
        })
        notify_slack_progress(case_id=case_id, file_id=None, status="transcribing")

        # Use get_pipeline() to handle any engine (Faster-Whisper, STT V2, Gemini)
        current_pipeline = get_pipeline()
        result = current_pipeline.transcribe(gcs_uri)

        if result.get("success"):
            # Normalize result structure for Firestore
            transcription_text = result.get("text") or result.get("full_text") or ""
            segments = result.get("segments", [])
            speakers = result.get("speakers", [])

            doc_ref.update({
                "status": "transcribed",
                "transcription": {
                    "text": transcription_text,
                    "segments": segments,
                    "speakers": speakers,
                    "engine": engine,
                    "model": os.getenv("WHISPER_MODEL", "large-v3-turbo") if "whisper" in engine else "default",
                },
                "updatedAt": firestore.SERVER_TIMESTAMP
            })
            notify_slack_progress(case_id=case_id, file_id=None, status="transcribed")

            # Trigger analysis
            _trigger_analysis(case_id)

            logger.info(f"Case {case_id} transcribed successfully using {engine}")

            # If serial mode, trigger next case
            if is_serial:
                _trigger_next_transcription()

            return jsonify({"success": True, "caseId": case_id}), 200
        else:
            error_msg = result.get("error", "Unknown error")
            doc_ref.update({
                "status": "transcription_failed",
                "error": error_msg,
                "updatedAt": firestore.SERVER_TIMESTAMP
            })
            notify_slack_progress(case_id=case_id, file_id=None, status="transcription_failed")
            logger.error(f"Case {case_id} transcription failed: {error_msg}")

            # If serial mode, trigger next case even on failure
            if is_serial:
                _trigger_next_transcription()

            return jsonify({"success": False, "error": error_msg}), 500

    except Exception as e:
        logger.error(f"Error processing case {case_id}: {e}", exc_info=True)
        doc_ref.update({
            "status": "transcription_failed",
            "error": str(e),
            "updatedAt": firestore.SERVER_TIMESTAMP
        })
        notify_slack_progress(case_id=case_id, file_id=None, status="transcription_failed")

        # If serial mode, trigger next case even on exception
        if is_serial:
            _trigger_next_transcription()

        return jsonify({"error": str(e)}), 500


@flask_app.route("/transcribe-serial", methods=["POST"])
def transcribe_serial():
    """
    Start serial (one-by-one) transcription for a list of cases.
    This avoids rate limits by processing one case at a time.

    Expects JSON body: { "caseIds": ["202601-IC001", "202601-IC002", ...] }

    The first case will be processed immediately, and each subsequent case
    will be triggered after the previous one completes.
    """
    if not db:
        return jsonify({"error": "Firestore not initialized"}), 500

    if not tasks_client:
        return jsonify({"error": "Cloud Tasks not initialized"}), 500

    data = request.get_json()
    case_ids = data.get("caseIds", []) if data else []

    if not case_ids:
        return jsonify({"error": "Missing or empty 'caseIds' array"}), 400

    logger.info(f"Starting serial transcription for {len(case_ids)} cases")

    # Store the queue in Firestore (excluding the first one which we'll process immediately)
    queue_ref = db.collection(SERIAL_QUEUE_COLLECTION).document(SERIAL_QUEUE_DOC)

    if len(case_ids) > 1:
        queue_ref.set({
            "pending": case_ids[1:],  # All except the first
            "currentlyProcessing": case_ids[0],
            "totalCount": len(case_ids),
            "createdAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP
        })
    else:
        queue_ref.set({
            "pending": [],
            "currentlyProcessing": case_ids[0],
            "totalCount": 1,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP
        })

    # Trigger the first case immediately with serial=True
    first_case_id = case_ids[0]
    queue_path = tasks_client.queue_path(GCP_PROJECT_ID, TRANSCRIPTION_LOCATION, TRANSCRIPTION_QUEUE)
    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": f"{TRANSCRIPTION_SERVICE_URL}/transcribe-single",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"caseId": first_case_id, "serial": True}).encode(),
        }
    }
    tasks_client.create_task(parent=queue_path, task=task)

    logger.info(f"Serial transcription started. First case: {first_case_id}, Queue size: {len(case_ids) - 1}")

    return jsonify({
        "success": True,
        "message": f"Serial transcription started for {len(case_ids)} cases",
        "firstCase": first_case_id,
        "queueSize": len(case_ids) - 1
    }), 200


@flask_app.route("/transcribe-serial-status", methods=["GET"])
def transcribe_serial_status():
    """Get the current status of the serial transcription queue."""
    if not db:
        return jsonify({"error": "Firestore not initialized"}), 500

    queue_ref = db.collection(SERIAL_QUEUE_COLLECTION).document(SERIAL_QUEUE_DOC)
    queue_doc = queue_ref.get()

    if not queue_doc.exists:
        return jsonify({
            "status": "idle",
            "message": "No serial transcription queue active"
        }), 200

    queue_data = queue_doc.to_dict()
    pending = queue_data.get("pending", [])
    currently_processing = queue_data.get("currentlyProcessing")
    total_count = queue_data.get("totalCount", 0)

    completed_count = total_count - len(pending) - (1 if currently_processing else 0)

    return jsonify({
        "status": "processing",
        "currentlyProcessing": currently_processing,
        "pendingCount": len(pending),
        "completedCount": completed_count,
        "totalCount": total_count,
        "pendingCases": pending[:5]  # Show first 5 pending
    }), 200


@flask_app.route("/process-queue", methods=["POST"])
def process_queue():
    """
    Triggered by Cloud Scheduler or manually.
    Enqueues each 'queued_for_batch' case as an independent Cloud Task.
    Returns immediately after enqueuing.
    """
    if not db:
        return jsonify({"error": "Firestore not initialized"}), 500
    
    engine = os.getenv("TRANSCRIPTION_ENGINE", "groq_whisper").strip().lower()
    logger.info(f"Trigger batch called with engine: {engine}")
        
    if not tasks_client:
        return jsonify({"error": "Cloud Tasks not initialized"}), 500
    
    # Query queued cases
    docs = db.collection("cases").where("status", "==", "queued_for_batch").stream()
    
    queued_cases = []
    for doc in docs:
        data = doc.to_dict()
        if data.get("gcsUri"):
            queued_cases.append(doc)
            
    if not queued_cases:
        return jsonify({"message": "No cases to process"}), 200
        
    logger.info(f"Found {len(queued_cases)} cases to enqueue.")
    
    # Enqueue each case as a Cloud Task
    enqueued_count = 0
    queue_path = tasks_client.queue_path(GCP_PROJECT_ID, TRANSCRIPTION_LOCATION, TRANSCRIPTION_QUEUE)
    
    for doc in queued_cases:
        case_id = doc.id
        
        try:
            # Create task payload
            task = {
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": f"{TRANSCRIPTION_SERVICE_URL}/transcribe-single",
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"caseId": case_id}).encode(),
                    "oidc_token": {
                        "service_account_email": SERVICE_ACCOUNT_EMAIL,
                    },
                }
            }
            
            # Create the task
            tasks_client.create_task(parent=queue_path, task=task)
            enqueued_count += 1
            logger.info(f"Enqueued task for case {case_id}")
            
        except Exception as e:
            logger.error(f"Failed to enqueue task for case {case_id}: {e}")
    
    return jsonify({
        "message": f"Enqueued {enqueued_count} cases for processing",
        "count": enqueued_count
    }), 200


# --- LEGACY: Direct processing endpoints (kept for backward compatibility) ---

@flask_app.route("/process-queue-sync", methods=["POST"])
def process_queue_sync():
    """
    LEGACY: Synchronous processing. Use /process-queue for Cloud Tasks version.
    """
    if not db:
        return jsonify({"error": "Firestore not initialized"}), 500
    
    engine = os.getenv("TRANSCRIPTION_ENGINE", "groq_whisper").strip().lower()
    logger.info(f"Sync processing with engine: {engine}")
    
    docs = db.collection("cases").where("status", "==", "queued_for_batch").stream()
    
    queued_cases = []
    for doc in docs:
        data = doc.to_dict()
        if data.get("gcsUri"):
            queued_cases.append(doc)
            
    if not queued_cases:
        return jsonify({"message": "No cases to process"}), 200
        
    logger.info(f"Found {len(queued_cases)} cases to process.")
    
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
    
    # --- Unsupported engine ---
    else:
        logger.error(f"Unsupported engine: {engine}. Use 'groq_whisper' or 'gemini'.")
        return jsonify({
            "error": f"Unsupported engine: {engine}. Please use 'groq_whisper' (recommended) or 'gemini'."
        }), 400


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


def _trigger_next_transcription():
    """
    Trigger the next case in the serial transcription queue.
    This enables one-by-one processing to avoid rate limits.
    """
    if not db or not tasks_client:
        logger.warning("Cannot trigger next transcription: db or tasks_client not initialized")
        return

    try:
        # Get the queue document
        queue_ref = db.collection(SERIAL_QUEUE_COLLECTION).document(SERIAL_QUEUE_DOC)
        queue_doc = queue_ref.get()

        if not queue_doc.exists:
            logger.info("No serial transcription queue found")
            return

        queue_data = queue_doc.to_dict()
        pending_cases = queue_data.get("pending", [])

        if not pending_cases:
            logger.info("Serial transcription queue is empty")
            # Clean up the queue document
            queue_ref.delete()
            return

        # Pop the first case from the queue
        next_case_id = pending_cases[0]
        remaining_cases = pending_cases[1:]

        # Update the queue
        if remaining_cases:
            queue_ref.update({
                "pending": remaining_cases,
                "currentlyProcessing": next_case_id,
                "updatedAt": firestore.SERVER_TIMESTAMP
            })
        else:
            queue_ref.update({
                "pending": [],
                "currentlyProcessing": next_case_id,
                "updatedAt": firestore.SERVER_TIMESTAMP
            })

        # Create Cloud Task for the next case
        queue_path = tasks_client.queue_path(GCP_PROJECT_ID, TRANSCRIPTION_LOCATION, TRANSCRIPTION_QUEUE)
        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": f"{TRANSCRIPTION_SERVICE_URL}/transcribe-single",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"caseId": next_case_id, "serial": True}).encode(),
            }
        }
        tasks_client.create_task(parent=queue_path, task=task)
        logger.info(f"Triggered next transcription: {next_case_id} (remaining: {len(remaining_cases)})")

    except Exception as e:
        logger.error(f"Failed to trigger next transcription: {e}", exc_info=True)

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
