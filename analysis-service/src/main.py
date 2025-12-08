"""
Analysis Service - Multi-Agent Orchestration for Sales AI Automation

This service provides two main endpoints:
1. /analyze - Execute Agent 1-5 analysis on transcribed sales calls
2. /ask-agent8 - Conversational AI queries (Agent 8)

Architecture:
- Agent 1-5: Parallel analysis of sales call transcripts
- Agent 6-7: Sequential synthesis and summary (Phase 4)
- Agent 8: Conversational Q&A interface
"""

import json
import os
import logging
import asyncio
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from datetime import datetime

from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from google.cloud import firestore

from .orchestrator import MultiAgentOrchestrator, InsufficientDataError
from .agents.conversational_agent8 import ConversationalAgent8
from .slack_notifier import SlackNotifier

# --- Initialization ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

# --- Model Configuration ---
# Using Gemini 2.0 Flash for all agents as requested
GEMINI_MODEL_FAST = "gemini-2.0-flash-exp"
GEMINI_MODEL_PRO = "gemini-2.0-flash-exp"
GEMINI_MODEL_DEFAULT = "gemini-2.0-flash-exp"

AGENT6_NOTIFICATION_ENDPOINT = os.environ.get("AGENT6_NOTIFICATION_ENDPOINT")
AGENT6_NOTIFICATION_TOKEN = os.environ.get("AGENT6_NOTIFICATION_TOKEN")
AGENT7_NOTIFICATION_ENDPOINT = os.environ.get("AGENT7_NOTIFICATION_ENDPOINT")
AGENT7_NOTIFICATION_TOKEN = os.environ.get("AGENT7_NOTIFICATION_TOKEN")

# --- Initialize Clients ---
try:
    # Firestore client for reading transcripts and writing analysis results
    db = firestore.Client()
    logger.info("Firestore client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Firestore: {e}", exc_info=True)
    db = None

try:
    # Multi-Agent Orchestrator for Agent 1-4 (3+1 Architecture)
    orchestrator = MultiAgentOrchestrator(
        model_name=GEMINI_MODEL_DEFAULT,
        model_config={
            "agent1": GEMINI_MODEL_FAST,  # Context
            "agent2": GEMINI_MODEL_PRO,   # Buyer (Complex)
            "agent3": GEMINI_MODEL_PRO,   # Seller (Complex)
            "agent4": GEMINI_MODEL_FAST,  # Summary
        },
        min_success_threshold=3,  # Require at least 3/4 agents
        enable_agent_retry=True,
        agent_retry_attempts=2,
        db_client=db,
    )
    logger.info("Multi-Agent Orchestrator initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Multi-Agent Orchestrator: {e}", exc_info=True)
    orchestrator = None

try:
    # Agent 8 for conversational queries - uses pro model for complex reasoning
    agent8 = ConversationalAgent8(model_name=GEMINI_MODEL_PRO)
    slack_client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
    logger.info("ConversationalAgent8 and SlackClient initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Agent 8: {e}", exc_info=True)
    agent8 = None
    slack_client = None

try:
    # Slack notifier for analysis completion notifications
    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    if db and slack_client and slack_token:
        slack_notifier = SlackNotifier(
            slack_token=slack_token,
            db=db
        )
        logger.info("Slack Notifier initialized successfully")
    else:
        slack_notifier = None
        missing_deps = []
        if not db:
            missing_deps.append("Firestore")
        if not slack_client:
            missing_deps.append("slack_client")
        if not slack_token:
            missing_deps.append("SLACK_BOT_TOKEN")
        logger.warning(f"Slack Notifier not initialized (missing: {', '.join(missing_deps)})")
except Exception as e:
    logger.error(f"Failed to initialize Slack Notifier: {e}", exc_info=True)
    slack_notifier = None





# --- Helper Functions ---

def get_transcript_from_firestore(case_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch transcript data from Firestore.

    Args:
        case_id: Case document ID

    Returns:
        Dictionary with transcript_segments, speaker_statistics, metadata
        None if not found or error
    """
    if not db:
        logger.error("Firestore client not initialized")
        return None

    try:
        # Fetch case document
        case_ref = db.collection('cases').document(case_id)
        case_doc = case_ref.get()

        if not case_doc.exists:
            logger.error(f"Case {case_id} not found in Firestore")
            return None

        case_data = case_doc.to_dict()

        # Extract transcript data
        transcription = case_data.get('transcription', {})

        if not transcription.get('text'):
            logger.error(f"Case {case_id} has no transcription text")
            return None

        # Get segments (required for agents)
        segments = transcription.get('segments', [])
        if not segments:
            logger.warning(f"Case {case_id} has no transcript segments, will use text only")
            # Fallback: create a single segment from full text
            segments = [{
                'start': 0,
                'end': 0,
                'speaker': 'Speaker 1',
                'text': transcription['text']
            }]

        # Get speaker statistics
        speakers = transcription.get('speakers', [])
        speaker_stats = {}
        for speaker in speakers:
            speaker_id = speaker.get('speakerId', 'Unknown')
            speaking_time = speaker.get('speakingTime', 0)
            percentage = speaker.get('percentage', 0)
            speaker_stats[speaker_id] = percentage

        # Get metadata
        metadata = {
            'customerId': case_data.get('customerId'),
            'storeName': case_data.get('storeName'),
            'uploadedBy': case_data.get('uploadedBy'),
            'createdAt': case_data.get('createdAt'),
            'audioFileName': case_data.get('audioFileName'),
        }

        logger.info(
            f"Retrieved transcript for case {case_id}: "
            f"{len(segments)} segments, {len(speaker_stats)} speakers"
        )

        return {
            'transcript_segments': segments,
            'speaker_statistics': speaker_stats,
            'conversation_metadata': metadata,
        }

    except Exception as e:
        logger.error(f"Error fetching transcript for case {case_id}: {e}", exc_info=True)
        return None


def save_analysis_to_firestore(case_id: str, analysis_result: Any) -> bool:
    """
    Save analysis results to Firestore.

    Args:
        case_id: Case document ID
        analysis_result: AnalysisResult from orchestrator

    Returns:
        True if successful, False otherwise
    """
    if not db:
        logger.error("Firestore client not initialized")
        return False

    try:
        case_ref = db.collection('cases').document(case_id)

        # Determine status
        if analysis_result.success:
            status = 'completed'
        elif len([r for r in analysis_result.agent_results.values() if r.success]) >= 3:
            status = 'partial_success'
        else:
            status = 'failed'

        # Build analysis document
        analysis_data = {
            'status': status,
            'completedAt': firestore.SERVER_TIMESTAMP,
            'totalDuration': analysis_result.total_duration,
            'agents': {}
        }

        # Add individual agent results
        for agent_id, agent_result in analysis_result.agent_results.items():
            analysis_data['agents'][agent_id] = {
                'status': 'success' if agent_result.success else 'failed',
                'duration': agent_result.duration,
                'retryCount': agent_result.retry_count,
            }

            if agent_result.success and agent_result.data:
                analysis_data['agents'][agent_id]['data'] = agent_result.data

            if agent_result.error:
                analysis_data['agents'][agent_id]['error'] = agent_result.error
                analysis_data['agents'][agent_id]['errorType'] = agent_result.error_type

        # Promote Agent 6 structured/raw outputs to top-level analysis fields
        agent6_result = analysis_result.agent_results.get('agent6')
        if agent6_result and agent6_result.success and agent6_result.data:
            structured = agent6_result.data.get('structured')
            raw_output = agent6_result.data.get('rawOutput')
            if structured:
                analysis_data['structured'] = structured
            if raw_output:
                analysis_data['rawOutput'] = raw_output

        # Promote Agent 7 customerSummary to top-level analysis fields
        agent7_result = analysis_result.agent_results.get('agent7')
        if agent7_result and agent7_result.success and agent7_result.data:
            customer_summary = agent7_result.data.get('customerSummary')
            markdown = agent7_result.data.get('markdown')
            if customer_summary or markdown:
                summary_doc = customer_summary.copy() if customer_summary else {}
                if markdown:
                    summary_doc['markdown'] = markdown
                    summary_doc.setdefault('originalMarkdown', markdown)
                summary_doc.setdefault('isEdited', False)
                summary_doc.setdefault('editCount', 0)
                summary_doc.setdefault('editedBy', None)
                summary_doc.setdefault('editHistory', [])
                analysis_data['customerSummary'] = summary_doc

        # Update Firestore
        case_ref.update({
            'analysis': analysis_data,
            'status': status,
            'updatedAt': firestore.SERVER_TIMESTAMP,
        })

        logger.info(f"Saved analysis results for case {case_id} with status: {status}")
        return True

    except Exception as e:
        logger.error(f"Error saving analysis for case {case_id}: {e}", exc_info=True)
        return False


# --- Flask Routes ---

@flask_app.route("/analyze", methods=["POST"])
def analyze_transcript():
    """
    Execute multi-agent analysis on a transcribed sales call.

    Expected payload from Cloud Tasks:
    {
        "caseId": "CASE123",
        "transcriptionId": "optional-transcript-id"
    }

    Process:
    1. Fetch transcript from Firestore
    2. Execute Agent 1-5 in parallel
    3. Save results to Firestore
    4. Return success/failure

    Returns:
        200: Analysis completed (full or partial success)
        400: Invalid request
        404: Case not found
        500: Analysis failed (triggers Cloud Tasks retry)
    """
    if not db or not orchestrator:
        logger.error("Service not properly configured")
        return jsonify({"status": "error", "message": "Service not initialized"}), 500

    # Parse request
    data = request.get_json()
    if not data or "caseId" not in data:
        logger.error(f"Invalid request payload: {data}")
        return jsonify({"status": "error", "message": "Missing caseId"}), 400

    case_id = data["caseId"]
    logger.info(f"Received analysis request for case {case_id}")

    # Fetch transcript from Firestore
    transcript_data = get_transcript_from_firestore(case_id)
    if not transcript_data:
        logger.error(f"Could not fetch transcript for case {case_id}")
        return jsonify({
            "status": "error",
            "message": f"Transcript not found for case {case_id}"
        }), 404

    # Execute analysis
    try:
        # Run orchestrator in async context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        analysis_result = loop.run_until_complete(
            orchestrator.analyze_transcript(
                case_id=case_id,
                transcript_segments=transcript_data['transcript_segments'],
                speaker_statistics=transcript_data['speaker_statistics'],
                conversation_metadata=transcript_data['conversation_metadata'],
            )
        )

        loop.close()

        # Save results to Firestore
        save_success = save_analysis_to_firestore(case_id, analysis_result)
        if not save_success:
            logger.error(f"Failed to save analysis results for case {case_id}")
            # Continue anyway, don't fail the request

        # Send Slack notification (async, don't fail if this fails)
        if slack_notifier:
            try:
                notification_sent = slack_notifier.send_analysis_notification(case_id)
                if notification_sent:
                    logger.info(f"Slack notification sent for case {case_id}")
                else:
                    logger.warning(f"Slack notification failed for case {case_id}")
            except Exception as e:
                logger.error(f"Error sending Slack notification: {e}", exc_info=True)
                # Don't fail the request

        # Agent 6 & 7 notifications are now handled directly in slack_notifier.py
        # Removed redundant trigger_agent6_notification and trigger_agent7_notification calls

        # Determine response based on analysis result
        if analysis_result.success:
            # Full or partial success (>= 3/5 agents succeeded)
            success_count = len([r for r in analysis_result.agent_results.values() if r.success])

            response = {
                "status": "success",
                "caseId": case_id,
                "successCount": success_count,
                "totalAgents": len(analysis_result.agent_results),
                "duration": analysis_result.total_duration,
            }

            if success_count < 5:
                response["warning"] = "Partial success - some agents failed"
                failed_agents = [
                    aid for aid, r in analysis_result.agent_results.items()
                    if not r.success
                ]
                response["failedAgents"] = failed_agents

            logger.info(f"Analysis completed for case {case_id}: {success_count}/5 agents succeeded")
            return jsonify(response), 200

        else:
            # Insufficient data (< 3/5 agents succeeded)
            logger.error(f"Analysis failed for case {case_id}: {analysis_result.error}")

            # Return 500 to trigger Cloud Tasks retry
            return jsonify({
                "status": "error",
                "message": analysis_result.error,
                "caseId": case_id,
                "retryable": True,
            }), 500

    except Exception as e:
        logger.error(f"Unexpected error during analysis for case {case_id}: {e}", exc_info=True)

        # Return 500 to trigger Cloud Tasks retry
        return jsonify({
            "status": "error",
            "message": str(e),
            "caseId": case_id,
            "retryable": True,
        }), 500


@flask_app.route("/ask-agent8", methods=["POST"])
def ask_agent8_task_handler():
    """
    Handles an asynchronous task from Cloud Tasks to ask Agent 8 a question.

    This is the conversational AI interface for managers to query sales data.
    """
    if not agent8 or not slack_client:
        logger.error("Agent 8 service is not properly configured")
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

    logger.info(f"Processing Agent 8 query for user={user_id}, question='{question}'")

    try:
        result = agent8.generate_answer(question, user_id)

        if result.get("success"):
            answer_text = f"💬 *問題*：{question}\n\n🤖 *Agent 8 回答*：\n{result.get('answer', '無法取得回答。')}"
            slack_client.chat_postMessage(channel=channel_id, thread_ts=thread_ts, text=answer_text)
            logger.info(f"Successfully sent Agent 8 response to thread {thread_ts}")
        else:
            error_msg = result.get("error", "分析服務回傳未知錯誤。")
            slack_client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=f"❌ 分析失敗：{error_msg}"
            )
            logger.error(f"Agent 8 returned an error: {error_msg}")

        return jsonify({"status": "success"}), 200

    except Exception as e:
        logger.error(f"Error during Agent 8 execution: {e}", exc_info=True)
        try:
            slack_client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=f"❌ 執行分析時發生未預期的系統錯誤。"
            )
        except Exception as slack_err:
            logger.error(f"Unable to send error message to Slack: {slack_err}")

        # Return 500 to allow Cloud Tasks to potentially retry
        return jsonify({"status": "error", "message": str(e)}), 500


@flask_app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Cloud Run startup probe."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "firestore": db is not None,
            "orchestrator": orchestrator is not None,
            "agent8": agent8 is not None,
            "slack": slack_client is not None,
            "slack_notifier": slack_notifier is not None,
        }
    }

    return jsonify(health_status), 200


@flask_app.route("/test-notification", methods=["POST"])
def test_notification():
    """Test endpoint to manually trigger Slack notification."""
    if not slack_notifier:
        return jsonify({"status": "error", "message": "Slack notifier not initialized"}), 500

    data = request.get_json()
    case_id = data.get("caseId")
    user_id = data.get("userId")

    if not case_id:
        return jsonify({"status": "error", "message": "Missing caseId"}), 400

    try:
        success = slack_notifier.send_analysis_notification(case_id, user_id=user_id)
        if success:
            return jsonify({"status": "success", "message": f"Notification sent for {case_id}"}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to send notification"}), 500
    except Exception as e:
        logger.error(f"Error in test notification: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting Analysis Service on port {port}")
    flask_app.run(host="0.0.0.0", port=port)
