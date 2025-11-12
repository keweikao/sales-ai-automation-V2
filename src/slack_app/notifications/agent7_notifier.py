"""
Agent 7 Slack Notifier

Sends customer-facing summary preview (Agent 7) to Slack.
Provides edit, preview, and send confirmation buttons.
"""

import logging
from typing import Dict, Any, List, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from google.cloud import firestore

logger = logging.getLogger(__name__)


class Agent7Notifier:
    """
    Handles Slack notifications for Agent 7 (Customer Summary) results.
    """

    def __init__(self, slack_client: WebClient, db_client: firestore.Client):
        """
        Initialize Agent 7 notifier.

        Args:
            slack_client: Slack SDK WebClient
            db_client: Firestore client
        """
        self.client = slack_client
        self.db = db_client

    def build_agent7_preview_blocks(
        self,
        case_id: str,
        summary_markdown: str,
        case_metadata: Optional[Dict[str, Any]] = None,
        is_edited: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Build Slack Block Kit blocks for Agent 7 summary preview.

        Args:
            case_id: Case ID
            summary_markdown: Customer summary in Markdown
            case_metadata: Optional case metadata
            is_edited: Whether summary has been edited

        Returns:
            List of Block Kit blocks
        """
        # Truncate summary for preview (first 500 characters)
        preview_length = 500
        if len(summary_markdown) > preview_length:
            preview_text = summary_markdown[:preview_length] + "..."
            has_more = True
        else:
            preview_text = summary_markdown
            has_more = False

        # Build header
        header_text = "📝 客戶摘要預覽"
        if is_edited:
            header_text += " (已編輯)"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": header_text,
                    "emoji": True
                }
            }
        ]

        # Case info
        if case_metadata:
            blocks.append({
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*案件編號:*\n{case_id}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*客戶:*\n{case_metadata.get('storeName', 'N/A')}"
                    }
                ]
            })

        blocks.append({"type": "divider"})

        # Quick Summary (one-liner from customerSummary.summary if available)
        # This is extracted from the full data in send_agent7_preview()
        # For now, show preview of markdown

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*摘要預覽:*\n{preview_text}"
            }
        })

        # More indicator
        if has_more:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "_...查看完整摘要請點擊「完整預覽」按鈕_"
                    }
                ]
            })

        blocks.append({"type": "divider"})

        # Character count and metadata
        char_count = len(summary_markdown)
        lines_count = summary_markdown.count('\n') + 1
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"📊 字數: {char_count} 字元 | 行數: {lines_count}"
                }
            ]
        })

        # Action buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✏️ 編輯摘要",
                        "emoji": True
                    },
                    "value": f"edit_summary_{case_id}",
                    "action_id": "edit_summary"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "👁️ 完整預覽",
                        "emoji": True
                    },
                    "value": f"preview_summary_{case_id}",
                    "action_id": "preview_summary"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✅ 確認送出",
                        "emoji": True
                    },
                    "style": "primary",
                    "value": f"confirm_send_{case_id}",
                    "action_id": "confirm_send_summary"
                }
            ]
        })

        # Warning about sending
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "⚠️ 點擊「確認送出」後，系統將生成網頁並發送簡訊給客戶"
                }
            ]
        })

        return blocks

    def send_agent7_preview(
        self,
        case_id: str,
        channel_id: str,
        thread_ts: Optional[str] = None,
        is_edited: bool = False
    ) -> bool:
        """
        Send Agent 7 summary preview notification to Slack.

        Args:
            case_id: Case ID
            channel_id: Slack channel (DM) ID
            thread_ts: Optional thread timestamp to reply in
            is_edited: Whether the summary has been edited

        Returns:
            True if notification sent successfully
        """
        try:
            # Fetch case data from Firestore
            case_ref = self.db.collection('cases').document(case_id)
            case_doc = case_ref.get()

            if not case_doc.exists:
                logger.error(f"Case {case_id} not found")
                return False

            case_data = case_doc.to_dict()
            analysis_data = case_data.get('analysis', {})
            customer_summary = analysis_data.get('customerSummary', {})

            # Get summary markdown
            summary_markdown = customer_summary.get('markdown', '')
            if not summary_markdown:
                logger.error(f"No customer summary markdown for case {case_id}")
                return False

            if not channel_id:
                logger.error("No Slack channel provided for Agent 7 preview (%s)", case_id)
                return False

            # Build message blocks
            case_metadata = {
                'storeName': case_data.get('storeName'),
                'customerId': case_data.get('customerId')
            }
            blocks = self.build_agent7_preview_blocks(
                case_id,
                summary_markdown,
                case_metadata,
                is_edited
            )

            # Send message
            response = self.client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=f"📝 客戶摘要預覽 - {case_metadata.get('storeName', case_id)}",
                blocks=blocks
            )

            if response['ok']:
                logger.info("Sent Agent 7 preview for case %s to channel %s", case_id, channel_id)

                # Update Firestore with notification timestamp
                update_payload = {
                    'analysis.customerSummary.previewSentAt': firestore.SERVER_TIMESTAMP,
                    'notification.agent7MessageTs': response['ts'],
                    'notification.agent7ChannelId': channel_id,
                }
                if thread_ts:
                    update_payload['notification.agent7ThreadTs'] = thread_ts

                case_ref.update(update_payload)

                return True
            else:
                logger.error(f"Failed to send Agent 7 preview: {response}")
                return False

        except SlackApiError as e:
            logger.error(f"Slack API error sending Agent 7 preview for {case_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending Agent 7 preview for {case_id}: {e}", exc_info=True)
            return False

    def update_preview_message(
        self,
        case_id: str,
        channel: str,
        message_ts: str
    ) -> bool:
        """
        Update an existing Agent 7 preview message (e.g., after edit).

        Args:
            case_id: Case ID
            channel: Slack channel ID
            message_ts: Message timestamp to update

        Returns:
            True if update successful
        """
        if not channel or not message_ts:
            logger.warning("Cannot update Agent 7 preview without channel or message_ts (%s)", case_id)
            return False

        try:
            # Fetch updated case data
            case_ref = self.db.collection('cases').document(case_id)
            case_doc = case_ref.get()

            if not case_doc.exists:
                logger.error(f"Case {case_id} not found")
                return False

            case_data = case_doc.to_dict()
            analysis_data = case_data.get('analysis', {})
            customer_summary = analysis_data.get('customerSummary', {})
            summary_markdown = customer_summary.get('markdown', '')
            is_edited = customer_summary.get('isEdited', False)

            if not summary_markdown:
                logger.warning("No summary markdown available when updating Agent 7 preview (%s)", case_id)
                return False

            # Build updated blocks
            case_metadata = {
                'storeName': case_data.get('storeName'),
                'customerId': case_data.get('customerId')
            }
            blocks = self.build_agent7_preview_blocks(
                case_id,
                summary_markdown,
                case_metadata,
                is_edited=is_edited
            )

            # Update message
            response = self.client.chat_update(
                channel=channel,
                ts=message_ts,
                text=f"📝 客戶摘要預覽 (已編輯) - {case_metadata.get('storeName', case_id)}",
                blocks=blocks
            )

            if response['ok']:
                logger.info(f"Updated Agent 7 preview message for case {case_id}")
                return True
            else:
                logger.error(f"Failed to update Agent 7 preview: {response}")
                return False

        except SlackApiError as e:
            logger.error(f"Slack API error updating Agent 7 preview for {case_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error updating Agent 7 preview for {case_id}: {e}", exc_info=True)
            return False
