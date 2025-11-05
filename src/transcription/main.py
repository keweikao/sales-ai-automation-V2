
import os
import logging
from flask import Flask, request, jsonify
from google.cloud import storage
import tempfile

from .pipeline import OptimizedTranscriptionPipeline

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
    if not data or "gcs_uri" not in data:
        return jsonify({"error": "Missing 'gcs_uri' in request body"}), 400

    gcs_uri = data["gcs_uri"]
    logger.info(f"Received transcription request for GCS URI: {gcs_uri}")

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
        logger.info(f"Starting transcription process for {local_audio_path}")
        result = pipeline.process_audio(
            audio_path=local_audio_path,
            save_transcription=False  # We will handle the result here
        )
        logger.info("Transcription process finished.")

        # --- 4. Clean up and respond ---
        os.remove(local_audio_path)

        if result and result.get("success"):
            return jsonify(result)
        else:
            error_message = result.get("error", "Unknown error during transcription.")
            logger.error(f"Transcription failed: {error_message}")
            return jsonify({"error": error_message}), 500

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
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
