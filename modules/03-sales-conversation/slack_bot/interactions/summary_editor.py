"""
Summary Editor

Handles editing of customer-facing summaries (Agent 4/7 output).
Provides modal editor, saves changes to Firestore, and tracks edit history.

Migration note: From src/slack_app/interactions/summary_editor.py
"""

import logging
from typing import Dict, Any, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from google.cloud import firestore

logger = logging.getLogger(__name__)


class SummaryEditor:
    """
    Handles summary editing interactions and persistence.
    """

    def __init__(self, slack_client: WebClient, db_client: firestore.Client):
        """
        Initialize summary editor.

        Args:
            slack_client: Slack SDK WebClient
            db_client: Firestore client
        """
        self.client = slack_client
        self.db = db_client

    def open_edit_modal(
        self,
        trigger_id: str,
        case_id: str,
        current_summary: Optional[str] = None
    ) -> bool:
        """
        Open modal for editing summary.

        Args:
            trigger_id: Slack trigger_id from button click
            case_id: Case ID
            current_summary: Current summary markdown (if None, fetch from Firestore)

        Returns:
            True if modal opened successfully
        """
        try:
            # Fetch current summary if not provided
            if current_summary is None:
                case_ref = self.db.collection('cases').document(case_id)
                case_doc = case_ref.get()

                if not case_doc.exists:
                    logger.error(f"Case {case_id} not found")
                    return False

                case_data = case_doc.to_dict()
                analysis_data = case_data.get('analysis', {})
                customer_summary = analysis_data.get('customerSummary', {})
                current_summary = customer_summary.get('markdown', '')

            # Build modal view
            modal_view = {
                "type": "modal",
                "callback_id": "edit_summary_modal",
                "private_metadata": case_id,  # Pass case_id to submission handler
                "title": {
                    "type": "plain_text",
                    "text": "編輯客戶摘要"
                },
                "submit": {
                    "type": "plain_text",
                    "text": "儲存"
                },
                "close": {
                    "type": "plain_text",
                    "text": "取消"
                },
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "📝 請編輯客戶摘要內容（支援 Markdown 格式）"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "summary_content_block",
                        "label": {
                            "type": "plain_text",
                            "text": "摘要內容"
                        },
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "summary_content_input",
                            "multiline": True,
                            "initial_value": current_summary,
                            "max_length": 3000,
                            "placeholder": {
                                "type": "plain_text",
                                "text": "輸入客戶摘要..."
                            }
                        },
                        "hint": {
                            "type": "plain_text",
                            "text": "最多 3000 字元"
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "💡 *Markdown 格式範例:* `**粗體**`, `*斜體*`, `### 標題`, `- 列表項目`"
                            }
                        ]
                    }
                ]
            }

            # Open modal
            response = self.client.views_open(
                trigger_id=trigger_id,
                view=modal_view
            )

            if response['ok']:
                logger.info(f"Opened edit modal for case {case_id}")
                return True
            else:
                logger.error(f"Failed to open edit modal: {response}")
                return False

        except SlackApiError as e:
            logger.error(f"Slack API error opening edit modal for {case_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error opening edit modal for {case_id}: {e}", exc_info=True)
            return False

    def handle_modal_submission(
        self,
        view: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Handle modal submission (save edited summary).

        Args:
            view: Slack view payload
            user_id: Slack user ID who submitted

        Returns:
            Response dict (empty for success, errors for validation failures)
        """
        try:
            # Extract case_id from private_metadata
            case_id = view.get('private_metadata')
            if not case_id:
                logger.error("No case_id in modal private_metadata")
                return {
                    "response_action": "errors",
                    "errors": {
                        "summary_content_block": "系統錯誤：無法識別案件"
                    }
                }

            # Extract submitted content
            values = view.get('state', {}).get('values', {})
            summary_content_block = values.get('summary_content_block', {})
            summary_content_input = summary_content_block.get('summary_content_input', {})
            new_summary = summary_content_input.get('value', '').strip()

            # Validation
            if not new_summary:
                return {
                    "response_action": "errors",
                    "errors": {
                        "summary_content_block": "摘要內容不能為空"
                    }
                }

            if len(new_summary) > 3000:
                return {
                    "response_action": "errors",
                    "errors": {
                        "summary_content_block": f"內容過長（{len(new_summary)} 字元），請縮減至 3000 字元以內"
                    }
                }

            # Save to Firestore
            success = self.save_edited_summary(
                case_id=case_id,
                new_summary=new_summary,
                edited_by=user_id
            )

            if not success:
                return {
                    "response_action": "errors",
                    "errors": {
                        "summary_content_block": "儲存失敗，請稍後再試"
                    }
                }

            logger.info(f"Successfully saved edited summary for case {case_id} by user {user_id}")

            # Return empty response for success (modal will close)
            return {}

        except Exception as e:
            logger.error(f"Error handling modal submission: {e}", exc_info=True)
            return {
                "response_action": "errors",
                "errors": {
                    "summary_content_block": "系統錯誤，請聯繫技術支援"
                }
            }

    def save_edited_summary(
        self,
        case_id: str,
        new_summary: str,
        edited_by: str
    ) -> bool:
        """
        Save edited summary to Firestore with edit history.

        Args:
            case_id: Case ID
            new_summary: New summary content
            edited_by: User ID who made the edit

        Returns:
            True if save successful
        """
        try:
            case_ref = self.db.collection('cases').document(case_id)

            # Use transaction to ensure consistency
            @firestore.transactional
            def update_in_transaction(transaction):
                # Read current data
                case_doc = case_ref.get(transaction=transaction)
                if not case_doc.exists:
                    raise ValueError(f"Case {case_id} not found")

                case_data = case_doc.to_dict()
                analysis_data = case_data.get('analysis', {})
                customer_summary = analysis_data.get('customerSummary', {})

                # Get previous summary for history
                previous_summary = customer_summary.get('markdown', '')

                # Build edit history entry
                edit_history = customer_summary.get('editHistory', [])
                edit_history.append({
                    'previousContent': previous_summary,
                    'editedAt': firestore.SERVER_TIMESTAMP,
                    'editedBy': edited_by,
                    'changes': {
                        'charactersDiff': len(new_summary) - len(previous_summary)
                    }
                })

                # Update summary
                transaction.update(case_ref, {
                    'analysis.customerSummary.markdown': new_summary,
                    'analysis.customerSummary.lastEditedAt': firestore.SERVER_TIMESTAMP,
                    'analysis.customerSummary.editedBy': edited_by,
                    'analysis.customerSummary.isEdited': True,
                    'analysis.customerSummary.editCount': firestore.Increment(1),
                    'analysis.customerSummary.editHistory': edit_history
                })

            # Execute transaction
            transaction = self.db.transaction()
            update_in_transaction(transaction)

            logger.info(f"Saved edited summary for case {case_id}")
            return True

        except ValueError as e:
            logger.error(f"Validation error saving summary: {e}")
            return False
        except Exception as e:
            logger.error(f"Error saving edited summary for {case_id}: {e}", exc_info=True)
            return False

    def open_preview_modal(
        self,
        trigger_id: str,
        case_id: str
    ) -> bool:
        """
        Open modal showing full summary preview (read-only).

        Args:
            trigger_id: Slack trigger_id from button click
            case_id: Case ID

        Returns:
            True if modal opened successfully
        """
        try:
            # Fetch summary from Firestore
            case_ref = self.db.collection('cases').document(case_id)
            case_doc = case_ref.get()

            if not case_doc.exists:
                logger.error(f"Case {case_id} not found")
                return False

            case_data = case_doc.to_dict()
            analysis_data = case_data.get('analysis', {})
            customer_summary = analysis_data.get('customerSummary', {})
            summary_markdown = customer_summary.get('markdown', '')

            # Build preview modal
            modal_view = {
                "type": "modal",
                "callback_id": "preview_summary_modal",
                "title": {
                    "type": "plain_text",
                    "text": "完整摘要預覽"
                },
                "close": {
                    "type": "plain_text",
                    "text": "關閉"
                },
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "📄 *完整客戶摘要*"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": summary_markdown or "_（無內容）_"
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"📊 字數: {len(summary_markdown)} 字元"
                            }
                        ]
                    }
                ]
            }

            # Open modal
            response = self.client.views_open(
                trigger_id=trigger_id,
                view=modal_view
            )

            if response['ok']:
                logger.info(f"Opened preview modal for case {case_id}")
                return True
            else:
                logger.error(f"Failed to open preview modal: {response}")
                return False

        except SlackApiError as e:
            logger.error(f"Slack API error opening preview modal for {case_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error opening preview modal for {case_id}: {e}", exc_info=True)
            return False
