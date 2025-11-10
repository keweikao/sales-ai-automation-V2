
import os
import logging
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from .agents.conversational_agent8 import ConversationalAgent8

# --- Initialization ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

# --- Instantiate Agent & Clients ---
try:
    agent8 = ConversationalAgent8()
    slack_client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
    logger.info("ConversationalAgent8 and SlackClient initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize services: {e}", exc_info=True)
    agent8 = None
    slack_client = None

# --- Flask Routes ---

@flask_app.route("/ask-agent8", methods=["POST"])
def ask_agent8_task_handler():
    """Handles an asynchronous task from Cloud Tasks to ask Agent 8 a question."""
    if not agent8 or not slack_client:
        logger.error("Service is not properly configured.")
        return jsonify({"status": "error", "message": "Service not initialized"}), 500

    data = request.get_json()
    if not data or "question" not in data or "user_id" not in data or "slack_context" not in data:
        logger.error(f"Invalid task payload: {data}")
        return jsonify({"status": "error", "message": "Invalid payload"}), 400

    question = data["question"]
    user_id = data["user_id"]
    slack_context = data["slack_context"]
    channel_id = slack_context.get("channel_id")
    thread_ts = slack_context.get("thread_ts")

    logger.info(f"Processing task for user={user_id}, question='{question}'")

    try:
        result = agent8.generate_answer(question, user_id)

        if result.get("success"):
            answer_text = f"💬 *問題*：{question}\n\n🤖 *Agent 8 回答*：\n{result.get('answer', '無法取得回答。')}"
            slack_client.chat_postMessage(channel=channel_id, thread_ts=thread_ts, text=answer_text)
            logger.info(f"Successfully sent Agent 8 response to thread {thread_ts}")
        else:
            error_msg = result.get("error", "分析服務回傳未知錯誤。")
            slack_client.chat_postMessage(channel=channel_id, thread_ts=thread_ts, text=f"❌ 分析失敗：{error_msg}")
            logger.error(f"Analysis service returned an error: {error_msg}")
        
        return jsonify({"status": "success"}), 200

    except Exception as e:
        logger.error(f"Error during Agent 8 execution or Slack post: {e}", exc_info=True)
        try:
            slack_client.chat_postMessage(channel=channel_id, thread_ts=thread_ts, text=f"❌ 執行分析時發生未預期的系統錯誤。")
        except Exception as slack_err:
            logger.error(f"Unable to send final error message to Slack: {slack_err}")
        # Return 500 to allow Cloud Tasks to potentially retry
        return jsonify({"status": "error", "message": str(e)}), 500

@flask_app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Cloud Run startup probe."""
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)
