
import os
import logging
import json
import tempfile
from typing import Optional

import requests
from flask import Flask, request, jsonify
from google.cloud import storage, tasks_v2, firestore

from .pipeline import OptimizedTranscriptionPipeline
from .status_tracker import TranscriptionStatusTracker

# --- Initialization ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

# --- Configuration ---
MODEL_SIZE = os.environ.get("MODEL_SIZE", "medium")
DEVICE = os.environ.get("DEVICE", "cpu")
COMPUTE_TYPE = os.environ.get("COMPUTE_TYPE", "int8")
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "3"))
TARGET_CHUNK_DURATION = int(os.environ.get("TARGET_CHUNK_DURATION", "600"))
OVERLAP_DURATION = float(os.environ.get("OVERLAP_DURATION", "2"))
VAD_PRESET = os.environ.get("VAD_PRESET", "meeting")
TRANSCRIPTION_LANGUAGE = os.environ.get("TRANSCRIPTION_LANGUAGE", "zh")
ENABLE_DIARIZATION = os.environ.get("ENABLE_DIARIZATION", "false").lower() == "true"
DIARIZATION_MODEL = os.environ.get("DIARIZATION_MODEL", "pyannote/speaker-diarization")
DIARIZATION_ALLOW_OVERLAP = (
    os.environ.get("DIARIZATION_ALLOW_OVERLAP", "false").lower() == "true"
)
HUGGINGFACE_TOKEN = os.environ.get("HUGGINGFACE_TOKEN")

# --- Instantiate Pipeline ---
# We instantiate the pipeline globally to preload the model.
# This is crucial for reducing response time on Cloud Run.
logger.info(f"Loading transcription pipeline with model: {MODEL_SIZE}...")
try:
    pipeline = OptimizedTranscriptionPipeline(
        model_size=MODEL_SIZE,
        device=DEVICE,
        compute_type=COMPUTE_TYPE,
        max_workers=MAX_WORKERS,
        target_chunk_duration=TARGET_CHUNK_DURATION,
        overlap_duration=OVERLAP_DURATION,
        vad_preset=VAD_PRESET,
        language=TRANSCRIPTION_LANGUAGE,
        enable_diarization=ENABLE_DIARIZATION,
        diarization_model=DIARIZATION_MODEL,
        diarization_auth_token=HUGGINGFACE_TOKEN,
        diarization_allow_overlap=DIARIZATION_ALLOW_OVERLAP,
    )
    logger.info("Transcription pipeline loaded successfully.")
    logger.info(
        "Pipeline configuration: workers=%s, target_chunk=%ss, overlap=%ss, "
        "diarization=%s (%s, allow_overlap=%s)",
        MAX_WORKERS,
        TARGET_CHUNK_DURATION,
        OVERLAP_DURATION,
        ENABLE_DIARIZATION,
        DIARIZATION_MODEL,
        DIARIZATION_ALLOW_OVERLAP,
    )
except Exception as e:
    logger.error(f"Failed to load transcription pipeline: {e}", exc_info=True)
    pipeline = None

# --- GCS Client ---
storage_client = storage.Client()

# --- Firestore Client ---
try:
    db = firestore.Client()
    logger.info("Firestore client initialized successfully")
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
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "sales-ai-automation-v2")
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
    Main endpoint to transcribe an audio file from a GCS URI.
    Expects a JSON payload: {"gcs_uri": "gs://your-bucket/your-audio.m4a"}
    """
    if not pipeline:
        return jsonify({"error": "Transcription pipeline is not available."}), 500

    # --- 1. Get GCS URI from request ---
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing request body"}), 400

    # Accept both 'gcs_uri' and 'gcsPath' for compatibility
    gcs_uri = data.get("gcs_uri") or data.get("gcsPath")
    if not gcs_uri:
        return jsonify({"error": "Missing 'gcs_uri' or 'gcsPath' in request body"}), 400

    logger.info(f"Received transcription request for GCS URI: {gcs_uri}")

    case_id = data.get("caseId")
    file_id = data.get("fileId")

    def emit_progress(**kwargs):
        if not status_tracker.is_enabled() or not case_id:
            return
        status_tracker.update(case_id=case_id, file_id=file_id, **kwargs)

    def progress_callback(event):
        emit_progress(**event)

    emit_progress(step="downloading", detail="下載音檔中")

    try:
        # --- 2. Download file from GCS ---
        bucket_name, blob_name = gcs_uri.replace("gs://", "").split("/", 1)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(blob_name)[1]) as temp_audio_file:
            logger.info(f"Downloading gs://{bucket_name}/{blob_name} to {temp_audio_file.name}")
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.download_to_filename(temp_audio_file.name)
            
            local_audio_path = temp_audio_file.name

        # --- 3. Process audio file ---
        emit_progress(step="chunking", detail="切割音檔並準備轉錄")
        logger.info(f"Starting transcription process for {local_audio_path}")
        result = pipeline.process_audio(
            audio_path=local_audio_path,
            save_transcription=False,
            progress_callback=progress_callback,
        )
        logger.info("Transcription process finished.")

        # --- 4. Save to Firestore and trigger analysis ---
        os.remove(local_audio_path)

        if result and result.get("success"):
            # Extract case_id from request
            if case_id and db:
                try:
                    # Save transcription to Firestore
                    logger.info(f"Saving transcription to Firestore for case {case_id}")
                    case_ref = db.collection('cases').document(case_id)

                    # Extract audio duration from audio_info
                    audio_info = result.get("audio_info", {})
                    audio_duration = audio_info.get("duration", 0)

                    transcription_data = {
                        "text": result.get("full_text", ""),
                        "segments": result.get("segments", []),
                        "speakers": result.get("speakers", []),
                        "duration": audio_duration,
                        "language": result.get("language", "zh"),
                    }

                    case_ref.update({
                        "transcription": transcription_data,
                        "status": "transcribed",
                        "updatedAt": firestore.SERVER_TIMESTAMP,
                    })
                    logger.info(f"Transcription saved successfully for case {case_id}")

                    emit_progress(step="transcribed", detail="轉錄完成，等待分析", progress=1.0)
                    if file_id:
                        db.collection("processed_files").document(file_id).set(
                            {
                                "status": "transcribed",
                                "updatedAt": firestore.SERVER_TIMESTAMP,
                                "transcriptionDetail": "轉錄完成",
                            },
                            merge=True,
                        )
                    status_tracker.mark_completed(case_id=case_id, file_id=file_id)
                    notify_slack_progress(case_id=case_id, file_id=file_id, status="transcribed")

                    # Trigger analysis via Cloud Tasks
                    if tasks_client:
                        try:
                            queue_path = tasks_client.queue_path(
                                GCP_PROJECT_ID,
                                ANALYSIS_LOCATION,
                                ANALYSIS_QUEUE
                            )

                            task_payload = {
                                "caseId": case_id,
                            }

                            task = {
                                "http_request": {
                                    "http_method": tasks_v2.HttpMethod.POST,
                                    "url": ANALYSIS_SERVICE_URL,
                                    "headers": {"Content-Type": "application/json"},
                                    "body": json.dumps(task_payload).encode(),
                                    "oidc_token": {
                                        "service_account_email": SERVICE_ACCOUNT_EMAIL
                                    }
                                }
                            }

                            response = tasks_client.create_task(
                                request={"parent": queue_path, "task": task}
                            )
                            logger.info(f"Analysis task created for case {case_id}: {response.name}")
                        except Exception as task_error:
                            logger.error(f"Failed to create analysis task: {task_error}", exc_info=True)
                            # Don't fail the transcription if analysis trigger fails

                except Exception as firestore_error:
                    logger.error(f"Failed to save to Firestore: {firestore_error}", exc_info=True)
                    # Don't fail the transcription if Firestore write fails

            return jsonify(result)
        else:
            error_message = result.get("error", "Unknown error during transcription.")
            logger.error(f"Transcription failed: {error_message}")
            status_tracker.mark_failed(case_id=case_id, file_id=file_id, error=error_message)
            return jsonify({"error": error_message}), 500

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        status_tracker.mark_failed(case_id=case_id, file_id=file_id, error=str(e))
        return jsonify({"error": "An internal server error occurred."}), 500


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
