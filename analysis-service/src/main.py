
import os
import logging
from flask import Flask, request, jsonify

# --- Initialization ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

# --- Flask Routes ---

@flask_app.route("/analyze", methods=["POST"])
def analyze_transcript():
    """
    Main endpoint to analyze a transcription.
    This is a placeholder and will be implemented later.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request"}), 400

    logger.info(f"Received analysis request with data: {data}")

    # Mock response for now
    mock_response = {
        "status": "received",
        "message": "Analysis request received and will be processed.",
        "slack_channel": data.get("slack_channel"),
        "slack_thread_ts": data.get("slack_thread_ts")
    }
    
    return jsonify(mock_response), 200


@flask_app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Cloud Run startup probe."""
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)
