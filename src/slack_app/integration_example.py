"""
Integration Example for Task 6.1, 6.2, 6.3

This file shows how to integrate the new Agent 6/7 notifications
and summary editor into the main Slack app.

Usage:
1. Add these handlers to your main.py or app.py
2. Register the action handlers with your Slack app
3. Call the notifiers when Agent 6/7 complete
"""

import os
import logging
from slack_bolt import App
from google.cloud import firestore

# Import our new modules
from notifications.agent6_notifier import Agent6Notifier
from notifications.agent7_notifier import Agent7Notifier
from interactions.summary_editor import SummaryEditor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Slack app
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

# Initialize Firestore
db = firestore.Client()

# Initialize our handlers
agent6_notifier = Agent6Notifier(app.client, db)
agent7_notifier = Agent7Notifier(app.client, db)
summary_editor = SummaryEditor(app.client, db)


# ============================================================================
# Task 6.1: Agent 6 Result Display
# ============================================================================

def send_agent6_notification(case_id: str, user_id: str, thread_ts: str = None):
    """
    Call this function when Agent 6 completes analysis.

    Example usage:
        # In your analysis completion handler
        if agent6_completed:
            send_agent6_notification(case_id, user_id, thread_ts)
    """
    success = agent6_notifier.send_agent6_notification(
        case_id=case_id,
        user_id=user_id,
        thread_ts=thread_ts
    )
    if success:
        logger.info(f"✅ Agent 6 notification sent for {case_id}")
    else:
        logger.error(f"❌ Failed to send Agent 6 notification for {case_id}")
    return success


# ============================================================================
# Task 6.2: Agent 7 Summary Preview & Buttons
# ============================================================================

def send_agent7_preview(case_id: str, channel_id: str, thread_ts: str = None):
    """
    Call this function when Agent 7 completes customer summary.

    Example usage:
        # In your analysis completion handler
        if agent7_completed:
            send_agent7_preview(case_id, channel_id, thread_ts)
    """
    success = agent7_notifier.send_agent7_preview(
        case_id=case_id,
        channel_id=channel_id,
        thread_ts=thread_ts
    )
    if success:
        logger.info(f"✅ Agent 7 preview sent for {case_id}")
    else:
        logger.error(f"❌ Failed to send Agent 7 preview for {case_id}")
    return success


# ============================================================================
# Task 6.3: Summary Editor Handlers
# ============================================================================

@app.action("edit_summary")
def handle_edit_summary_button(ack, body, logger):
    """Handle 'Edit Summary' button click."""
    ack()

    trigger_id = body["trigger_id"]
    action_value = body["actions"][0]["value"]
    case_id = action_value.replace("edit_summary_", "")

    logger.info(f"Opening edit modal for case {case_id}")

    success = summary_editor.open_edit_modal(
        trigger_id=trigger_id,
        case_id=case_id
    )

    if not success:
        # Send ephemeral error message
        app.client.chat_postEphemeral(
            channel=body["user"]["id"],
            user=body["user"]["id"],
            text="❌ 無法開啟編輯視窗，請稍後再試"
        )


@app.action("preview_summary")
def handle_preview_summary_button(ack, body, logger):
    """Handle 'Full Preview' button click."""
    ack()

    trigger_id = body["trigger_id"]
    action_value = body["actions"][0]["value"]
    case_id = action_value.replace("preview_summary_", "")

    logger.info(f"Opening preview modal for case {case_id}")

    success = summary_editor.open_preview_modal(
        trigger_id=trigger_id,
        case_id=case_id
    )

    if not success:
        app.client.chat_postEphemeral(
            channel=body["user"]["id"],
            user=body["user"]["id"],
            text="❌ 無法開啟預覽視窗，請稍後再試"
        )


@app.view("edit_summary_modal")
def handle_edit_summary_submission(ack, body, view, logger):
    """Handle summary edit modal submission."""
    user_id = body["user"]["id"]

    logger.info(f"Processing summary edit submission by {user_id}")

    # Handle submission (returns errors dict if validation fails)
    response = summary_editor.handle_modal_submission(
        view=view,
        user_id=user_id
    )

    # Acknowledge with validation errors (if any)
    ack(response)

    # If successful (no errors), update the preview message
    if not response:
        case_id = view.get('private_metadata')

        # Get message info to update
        # Note: You'll need to store the channel and message_ts somewhere
        # when you send the original Agent 7 preview
        # For now, we'll just send a new message

        logger.info(f"✅ Summary edited successfully for case {case_id}")

        # Send updated preview
        # (In production,你應更新原訊息；此處示範重新開啟 DM 後推送)
        dm_channel = app.client.conversations_open(users=user_id)["channel"]["id"]
        agent7_notifier.send_agent7_preview(
            case_id=case_id,
            channel_id=dm_channel,
            is_edited=True
        )


@app.action("confirm_send_summary")
def handle_confirm_send(ack, body, logger):
    """Handle 'Confirm Send' button click."""
    ack()

    action_value = body["actions"][0]["value"]
    case_id = action_value.replace("confirm_send_", "")
    user_id = body["user"]["id"]

    logger.info(f"User {user_id} confirmed sending summary for case {case_id}")

    # TODO: Implement actual send logic (Task 6.5, 6.6, 6.7)
    # This should:
    # 1. Generate web page (Task 6.5)
    # 2. Send SMS to customer (Task 6.6)
    # 3. Update case status to "approved"

    # For now, just send confirmation
    app.client.chat_postEphemeral(
        channel=body["channel"]["id"],
        user=user_id,
        text=f"✅ 已確認送出案件 {case_id}。\n\n_（網頁生成與簡訊發送功能即將推出）_"
    )


# ============================================================================
# Example: Complete Analysis Flow
# ============================================================================

def example_complete_analysis_flow(case_id: str, channel_id: str):
    """
    Example of how to use all three tasks together when analysis completes.

    Call this from your analysis service when Agent 1-7 finish.
    """
    logger.info(f"Starting notification flow for case {case_id}")

    # Step 1: Send Agent 6 results (Sales Coaching)
    agent6_success = send_agent6_notification(
        case_id=case_id,
        user_id=channel_id
    )

    if not agent6_success:
        logger.warning(f"Agent 6 notification failed for {case_id}")

    # Step 2: Send Agent 7 preview (Customer Summary)
    agent7_success = send_agent7_preview(
        case_id=case_id,
        channel_id=channel_id
    )

    if not agent7_success:
        logger.error(f"Agent 7 preview failed for {case_id}")
        return False

    logger.info(f"✅ Complete analysis notifications sent for {case_id}")
    return True


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    logger.info("Starting Slack app with Agent 6/7 integration...")

    # Example: Trigger notifications for a test case
    # send_agent6_notification("TEST_CASE_001", "D01234567")
    # send_agent7_preview("TEST_CASE_001", "D01234567")

    # Start the app
    from slack_bolt.adapter.socket_mode import SocketModeHandler
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
