"""
Analysis Service - Multi-Agent Orchestration for Sales AI Automation

This service provides the main /analyze endpoint:
- /analyze - Execute Agent 1-4 analysis on transcribed sales calls

Architecture:
- Agent 1: Context extraction
- Agent 2: Buyer analysis  
- Agent 3: Seller coaching
- Agent 4: Summary generation
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
from .slack_notifier import SlackNotifier
from .metrics import metrics, send_slack_alert
from .services.stats_service import StatsService
from .services.report_service import ReportService
from .services.player_card_service import PlayerCardService
from .agents.agent5_coach import CoachAgent
from .templates.player_card_slack import (
    build_personal_player_card_blocks,
    build_team_dashboard_blocks,
)

# --- Initialization ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

# --- Model Configuration ---
# Read from environment variables with sensible defaults
# Using stable Gemini 2.5 models for production reliability
# - FAST: 2.5 Flash for simple/quick tasks (context extraction, summary)
# - PRO: 2.5 Pro for complex reasoning (buyer analysis, seller coaching)
GEMINI_MODEL_FAST = os.environ.get("GEMINI_MODEL_FAST", "gemini-2.5-flash")
GEMINI_MODEL_PRO = os.environ.get("GEMINI_MODEL_PRO", "gemini-2.5-pro-preview-06-05")
GEMINI_MODEL_DEFAULT = os.environ.get("GEMINI_MODEL_DEFAULT", "gemini-2.5-flash")



# Initialize global services
stats_service: Optional[StatsService] = None
report_service = None
player_card_service: Optional[PlayerCardService] = None
coach_agent: Optional[CoachAgent] = None
slack_client = None
slack_notifier = None
orchestrator = None

# --- Initialize Clients ---
# 1. Initialize Firestore first (core dependency)
db: Optional[firestore.Client] = None
try:
    project_id = os.environ.get("GCP_PROJECT_ID")
    if project_id:
        db = firestore.Client(project=project_id)
    else:
        # Fallback to default credentials
        db = firestore.Client()
        logger.warning(f"GCP_PROJECT_ID not set, using default project: {db.project}")
    logger.info("Firestore client initialized successfully")
    
    # Initialize Stats Service
    stats_service = StatsService(db)
    logger.info("StatsService initialized successfully")

except Exception as e:
    logger.error(f"Failed to initialize Firestore or StatsService: {e}", exc_info=True)
    db = None

# 2. Initialize Slack client (needed by ReportService and SlackNotifier)
try:
    slack_client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
    logger.info("SlackClient initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize SlackClient: {e}", exc_info=True)
    slack_client = None

try:
    manager_channel_id = os.environ.get("MANAGER_CHANNEL_ID")
    if db and stats_service and slack_client and manager_channel_id:
        report_service = ReportService(db, stats_service, slack_client, manager_channel_id)
        logger.info("ReportService initialized successfully")
    else:
        missing = []
        if not db: missing.append("Firestore")
        if not stats_service: missing.append("StatsService")
        if not slack_client: missing.append("SlackClient")
        if not manager_channel_id: missing.append("MANAGER_CHANNEL_ID")
        logger.warning(f"ReportService skipped (missing: {', '.join(missing)})")
except Exception as e:
    logger.error(f"Failed to initialize ReportService: {e}", exc_info=True)

# 3.5. Initialize PlayerCardService
try:
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if db and stats_service:
        player_card_service = PlayerCardService(
            db_client=db,
            stats_service=stats_service,
            gemini_api_key=gemini_api_key,
        )
        logger.info("PlayerCardService initialized successfully")
    else:
        logger.warning("PlayerCardService skipped (missing Firestore or StatsService)")
except Exception as e:
    logger.error(f"Failed to initialize PlayerCardService: {e}", exc_info=True)
    player_card_service = None

# 3.6. Initialize CoachAgent (Agent 5)
try:
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if db:
        coach_agent = CoachAgent(
            db_client=db,
            gemini_api_key=gemini_api_key,
        )
        logger.info("CoachAgent (Agent 5) initialized successfully")
    else:
        logger.warning("CoachAgent skipped (missing Firestore)")
except Exception as e:
    logger.error(f"Failed to initialize CoachAgent: {e}", exc_info=True)
    coach_agent = None

# 4. Initialize Multi-Agent Orchestrator
try:
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
            # Handle both string format (Gemini) and object format (STT Batch)
            if isinstance(speaker, str):
                speaker_id = speaker
                speaker_stats[speaker_id] = 0  # No percentage available
            elif isinstance(speaker, dict):
                speaker_id = speaker.get('speakerId', 'Unknown')
                percentage = speaker.get('percentage', 0)
                speaker_stats[speaker_id] = percentage
            else:
                continue

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


        # V2 Architecture: Promote Agent 4 (Summary) to customerSummary
        agent4_result = analysis_result.agent_results.get('agent4')
        if agent4_result and agent4_result.success and agent4_result.data:
            agent4_data = agent4_result.data
            email_subject = agent4_data.get('email_subject', '')
            email_body = agent4_data.get('email_body', '')
            action_items = agent4_data.get('action_items', {})
            
            if email_body:
                # Create markdown from email_subject and email_body
                markdown = f"# {email_subject}\n\n{email_body}" if email_subject else email_body
                
                analysis_data['customerSummary'] = {
                    'markdown': markdown,
                    'originalMarkdown': markdown,
                    'subject': email_subject,
                    'emailBody': email_body,
                    'actionItems': action_items,
                    'metadata': agent4_data.get('metadata', {}),
                    'isEdited': False,
                    'editCount': 0,
                    'editedBy': None,
                    'editHistory': [],
                }

        # Update Firestore
        case_ref.update({
            'analysis': analysis_data,
            'status': status,
            'updatedAt': firestore.SERVER_TIMESTAMP,
        })

        logger.info(f"Saved analysis results for case {case_id} with status: {status}")

        # Trigger Stats Update (Aggregation on Write)
        if stats_service and status in ['completed', 'partial_success']:
            try:
                updated_snapshot = case_ref.get()
                if updated_snapshot.exists:
                    stats_service.update_daily_stats(case_id, updated_snapshot.to_dict())
            except Exception as stats_error:
                logger.error(f"Failed to update daily stats for case {case_id}: {stats_error}")

        return True

    except Exception as e:
        logger.error(f"Error saving analysis for case {case_id}: {e}", exc_info=True)
        return False


def _trigger_coach_alert(case_id: str, analysis_result: Any) -> None:
    """
    Trigger Agent 5 Coach Alert if conditions are met.
    
    Evaluates the analysis result and sends immediate Slack alert
    to the sales rep if action is needed.
    """
    if not coach_agent or not slack_client or not db:
        return
    
    try:
        # Get agent results
        agent_results = analysis_result.agent_results
        
        agent1_result = agent_results.get("agent1")
        agent3_result = agent_results.get("agent3")
        
        if not agent1_result or not agent1_result.success:
            logger.debug("Agent 1 failed, skipping coach alert")
            return
        if not agent3_result or not agent3_result.success:
            logger.debug("Agent 3 failed, skipping coach alert")
            return
        
        context_data = agent1_result.data or {}
        seller_data = agent3_result.data or {}
        buyer_data = agent_results.get("agent2", {})
        if hasattr(buyer_data, 'data'):
            buyer_data = buyer_data.data or {}
        
        # Get case metadata
        case_doc = db.collection("cases").document(case_id).get()
        if not case_doc.exists:
            return
        
        case_data = case_doc.to_dict() or {}
        rep_id = case_data.get("uploadedBy", "")
        rep_name = case_data.get("uploadedByName", case_data.get("salesRepName", "Unknown"))
        store_name = case_data.get("storeName", "Unknown")
        
        if not rep_id:
            logger.warning(f"Case {case_id} has no uploadedBy, skipping coach alert")
            return
        
        # Evaluate if alert is needed
        alert = coach_agent.evaluate(
            case_id=case_id,
            rep_id=rep_id,
            rep_name=rep_name,
            store_name=store_name,
            context_data=context_data,
            buyer_data=buyer_data,
            seller_data=seller_data,
        )
        
        if not alert:
            logger.info(f"Case {case_id}: No coach alert needed")
            return
        
        # Build and send Slack message
        blocks = coach_agent.build_alert_blocks(alert)
        
        # Send as DM to the sales rep
        response = slack_client.chat_postMessage(
            channel=rep_id,
            blocks=blocks,
            text=f"{alert.alert_type}: {alert.store_name}"
        )
        
        if response.get("ok"):
            # Save alert to Firestore
            slack_ts = response.get("ts", "")
            coach_agent.save_alert(
                alert=alert,
                slack_channel=rep_id,
                slack_ts=slack_ts,
            )
            logger.info(f"Coach alert sent for case {case_id}: {alert.alert_type}")
        else:
            logger.error(f"Failed to send coach alert: {response}")
            
    except Exception as e:
        logger.error(f"Error in _trigger_coach_alert for {case_id}: {e}", exc_info=True)


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

        # Trigger Agent 5 Coach Alert (if applicable)
        if coach_agent and slack_client:
            try:
                _trigger_coach_alert(
                    case_id=case_id,
                    analysis_result=analysis_result,
                )
            except Exception as e:
                logger.error(f"Error triggering coach alert: {e}", exc_info=True)
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


@flask_app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Cloud Run startup probe."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "firestore": db is not None,
            "orchestrator": orchestrator is not None,
            "slack": slack_client is not None,
            "slack_notifier": slack_notifier is not None,
        }
    }

    return jsonify(health_status), 200


@flask_app.route("/metrics", methods=["GET"])
def get_metrics():
    """Get current metrics summary for monitoring dashboard."""
    summary = metrics.get_summary()
    return jsonify(summary), 200


@flask_app.route("/metrics/slack", methods=["POST"])
def send_metrics_to_slack():
    """Send metrics summary to Slack (for scheduled reports)."""
    webhook_url = os.environ.get("SLACK_METRICS_WEBHOOK")
    if not webhook_url:
        return jsonify({"status": "error", "message": "SLACK_METRICS_WEBHOOK not configured"}), 500
    
    message = metrics.format_slack_message()
    success = send_slack_alert(webhook_url, message)
    
    return jsonify({"status": "success" if success else "error"}), 200 if success else 500


@flask_app.route("/metrics/check-alerts", methods=["POST"])
def check_and_send_alerts():
    """Check alert conditions and send to Slack if triggered."""
    webhook_url = os.environ.get("SLACK_ALERTS_WEBHOOK")
    if not webhook_url:
        return jsonify({"status": "error", "message": "SLACK_ALERTS_WEBHOOK not configured"}), 500
    
    alert_message = metrics.should_alert()
    if alert_message:
        success = send_slack_alert(webhook_url, f"⚠️ *監控告警*\n\n{alert_message}")
        return jsonify({"status": "alert_sent", "success": success}), 200
    
    return jsonify({"status": "no_alerts"}), 200


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


# --- Report Routes (Scheduled) ---

@flask_app.route("/reports/daily-risk", methods=["POST"])
def trigger_daily_risk_report():
    """Trigger Daily Risk Report (Cron)"""
    if not report_service:
        return jsonify({"status": "error", "message": "ReportService not initialized"}), 503
        
    try:
        result = report_service.generate_daily_risk_report()
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Daily risk report failed: {e}", exc_info=True)
        return jsonify({"status": "error", "error": str(e)}), 500


@flask_app.route("/reports/weekly", methods=["POST"])
def trigger_weekly_reports():
    """Trigger Weekly Reports (Cron)"""
    if not report_service:
        return jsonify({"status": "error", "message": "ReportService not initialized"}), 503
        
    try:
        result = report_service.generate_weekly_reports()
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Weekly report failed: {e}", exc_info=True)
        return jsonify({"status": "error", "error": str(e)}), 500


# --- Player Card Routes ---

@flask_app.route("/reports/player-cards/weekly", methods=["POST"])
def trigger_weekly_player_cards():
    """
    Trigger Weekly Player Cards Generation and Send to Slack
    Called by Cloud Scheduler (週一 9:00 AM)
    """
    if not player_card_service:
        return jsonify({"status": "error", "message": "PlayerCardService not initialized"}), 503
    
    if not slack_client:
        return jsonify({"status": "error", "message": "Slack client not initialized"}), 503
    
    try:
        data = request.get_json() or {}
        week_of = data.get("weekOf")  # Optional, defaults to current week
        
        # Generate all player cards
        cards = player_card_service.generate_weekly_player_cards(week_of=week_of)
        
        if not cards:
            return jsonify({"status": "skipped", "reason": "no_data"}), 200
        
        # Calculate rankings
        sorted_cards = sorted(cards, key=lambda c: c.get("indices", {}).get("overall", 0), reverse=True)
        rank_map = {c["repId"]: i + 1 for i, c in enumerate(sorted_cards)}
        
        # Send personal player cards to each rep
        sent_count = 0
        for card in cards:
            try:
                rank = rank_map.get(card["repId"], 0)
                blocks = build_personal_player_card_blocks(card, rank=rank, total_reps=len(cards))
                slack_client.chat_postMessage(
                    channel=card["repId"],
                    blocks=blocks,
                    text=f"👤 {card.get('repName', 'Unknown')} 的本週球員卡"
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send player card to {card.get('repId')}: {e}")
        
        # Send team dashboard to manager channel
        manager_channel = os.environ.get("MANAGER_CHANNEL_ID")
        if manager_channel:
            try:
                team_blocks = build_team_dashboard_blocks(
                    cards=sorted_cards,
                    week_of=week_of or cards[0].get("weekOf", ""),
                    team_stats={}
                )
                slack_client.chat_postMessage(
                    channel=manager_channel,
                    blocks=team_blocks,
                    text="📊 團隊球員卡週報"
                )
            except Exception as e:
                logger.error(f"Failed to send team dashboard: {e}")
        
        return jsonify({
            "status": "success",
            "cardsGenerated": len(cards),
            "cardsSent": sent_count,
            "weekOf": week_of or cards[0].get("weekOf", "")
        }), 200
        
    except Exception as e:
        logger.error(f"Weekly player cards failed: {e}", exc_info=True)
        return jsonify({"status": "error", "error": str(e)}), 500


@flask_app.route("/reports/player-cards/generate", methods=["POST"])
def generate_single_player_card():
    """
    Generate a single player card for a specific rep
    Used for manual testing or on-demand generation
    """
    if not player_card_service:
        return jsonify({"status": "error", "message": "PlayerCardService not initialized"}), 503
    
    data = request.get_json() or {}
    rep_id = data.get("repId")
    week_of = data.get("weekOf")
    send_slack = data.get("sendSlack", False)
    
    if not rep_id:
        return jsonify({"status": "error", "message": "Missing repId"}), 400
    
    try:
        card = player_card_service.generate_player_card(rep_id=rep_id, week_of=week_of)
        
        if not card:
            return jsonify({"status": "error", "message": "No data for this rep"}), 404
        
        # Optionally send to Slack
        if send_slack and slack_client:
            try:
                blocks = build_personal_player_card_blocks(card)
                slack_client.chat_postMessage(
                    channel=rep_id,
                    blocks=blocks,
                    text=f"👤 {card.get('repName', 'Unknown')} 的球員卡"
                )
                card["slackSent"] = True
            except Exception as e:
                logger.error(f"Failed to send player card to Slack: {e}")
                card["slackSent"] = False
        
        return jsonify({"status": "success", "card": card}), 200
        
    except Exception as e:
        logger.error(f"Generate player card failed: {e}", exc_info=True)
        return jsonify({"status": "error", "error": str(e)}), 500


@flask_app.route("/reports/player-cards/<rep_id>", methods=["GET"])
def get_player_card(rep_id: str):
    """
    Get a player card for a specific rep (for Web Dashboard)
    """
    if not player_card_service:
        return jsonify({"status": "error", "message": "PlayerCardService not initialized"}), 503
    
    week_of = request.args.get("weekOf")
    
    try:
        if not week_of:
            week_of = player_card_service._get_current_week()
        
        card = player_card_service._get_player_card(rep_id, week_of)
        
        if not card:
            return jsonify({"status": "error", "message": "Player card not found"}), 404
        
        return jsonify({"status": "success", "card": card}), 200
        
    except Exception as e:
        logger.error(f"Get player card failed: {e}", exc_info=True)
        return jsonify({"status": "error", "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting Analysis Service on port {port}")
    flask_app.run(host="0.0.0.0", port=port)

