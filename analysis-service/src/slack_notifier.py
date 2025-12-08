"""
Slack Notification Module for Analysis Results

Sends Block Kit interactive messages to sales reps when analysis is complete.
"""

import logging
from typing import Dict, Any, List, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from google.cloud import firestore

logger = logging.getLogger(__name__)


class SlackNotifier:
    """
    Handles Slack notifications for analysis completion.
    """

    def __init__(self, slack_token: str, db: firestore.Client):
        """
        Initialize Slack notifier.

        Args:
            slack_token: Slack bot token
            db: Firestore client
        """
        self.client = WebClient(token=slack_token)
        self.db = db

    @staticmethod
    def _serialize_firestore_data(data: Any) -> Any:
        """
        Convert Firestore data with special types to JSON-serializable format.

        Recursively converts DatetimeWithNanoseconds objects to ISO format strings.

        Args:
            data: Data from Firestore (dict, list, or primitive type)

        Returns:
            JSON-serializable version of the data
        """
        from google.cloud.firestore_v1._helpers import DatetimeWithNanoseconds

        if isinstance(data, DatetimeWithNanoseconds):
            return data.isoformat()
        elif isinstance(data, dict):
            return {k: SlackNotifier._serialize_firestore_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [SlackNotifier._serialize_firestore_data(item) for item in data]
        else:
            return data

    def get_user_slack_id(self, uploaded_by: str) -> Optional[str]:
        """
        Get Slack user ID from email or user identifier.

        Args:
            uploaded_by: User email or identifier

        Returns:
            Slack user ID or None if not found
        """
        try:
            # Check if uploaded_by is already a Slack ID (starts with U)
            if uploaded_by.startswith('U') and len(uploaded_by) >= 9:
                logger.info(f"uploaded_by {uploaded_by} appears to be a Slack ID, using it directly.")
                return uploaded_by

            # Try to find user in Firestore users collection
            users_ref = self.db.collection('users')
            query = users_ref.where('email', '==', uploaded_by).limit(1)
            docs = list(query.stream())

            if docs:
                user_data = docs[0].to_dict()
                slack_id = user_data.get('slackUserId') or user_data.get('userId')
                if slack_id:
                    logger.info(f"Found Slack ID {slack_id} for user {uploaded_by}")
                    return slack_id

            # Fallback: try to lookup by email via Slack API
            response = self.client.users_lookupByEmail(email=uploaded_by)
            if response['ok']:
                slack_id = response['user']['id']
                logger.info(f"Found Slack ID {slack_id} via API for {uploaded_by}")
                return slack_id

        except SlackApiError as e:
            if e.response['error'] != 'users_not_found':
                logger.error(f"Error looking up Slack user: {e}")
        except Exception as e:
            logger.error(f"Error getting Slack ID for {uploaded_by}: {e}")

        return None

    def build_analysis_blocks(
        self,
        case_id: str,
        case_data: Dict[str, Any],
        analysis_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Build Slack Block Kit blocks for analysis results.

        Args:
            case_id: Case ID
            case_data: Case metadata
            analysis_data: Analysis results

        Returns:
            List of Block Kit blocks
        """
        status = analysis_data.get('status', 'unknown')
        agents = analysis_data.get('agents', {})

        # Count successes and failures
        success_count = sum(1 for a in agents.values() if a.get('status') == 'success')
        total_agents = len(agents)

        # Determine status emoji and text
        if status == 'completed':
            status_emoji = '✅'
            status_text = '分析完成'
        elif status == 'partial_success':
            status_emoji = '⚠️'
            status_text = '部分完成'
        else:
            status_emoji = '❌'
            status_text = '分析失敗'

        # Build blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji} 銷售通話分析 {status_text}",
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*案件編號:*\n{case_id}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*客戶:*\n{case_data.get('storeName', 'N/A')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*客戶ID:*\n{case_data.get('customerId', 'N/A')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*分析狀態:*\n{success_count}/{total_agents} 項完成"
                    },
                ]
            },
            {"type": "divider"},
        ]

        # Add agent results
        agent_names = {
            'agent1': '👥 參與者分析',
            'agent2': '😊 情緒態度分析',
            'agent3': '📋 產品需求分析',
            'agent4': '🏢 競品情報分析',
            'agent5': '📝 問卷分析',
        }

        agent_section_fields = []
        for agent_id in ['agent1', 'agent2', 'agent3', 'agent4', 'agent5']:
            agent_result = agents.get(agent_id, {})
            agent_status = agent_result.get('status', 'unknown')
            agent_name = agent_names.get(agent_id, agent_id)

            if agent_status == 'success':
                status_mark = '✅'
            else:
                status_mark = '❌'
                error = agent_result.get('error', '未知錯誤')
                agent_name += f'\n   _{error[:50]}_'

            agent_section_fields.append({
                "type": "mrkdwn",
                "text": f"{status_mark} {agent_name}"
            })

        blocks.append({
            "type": "section",
            "fields": agent_section_fields
        })

        # Add warning for partial success
        if status == 'partial_success':
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "⚠️ 部分分析項目失敗，結果可能不完整。系統已自動重試但仍無法完成。"
                    }
                ]
            })

        # Add Agent 6 (Sales Coach) content directly
        agent6_result = agents.get('agent6', {})
        if agent6_result.get('status') == 'success' and agent6_result.get('data'):
            data = agent6_result.get('data', {})
            # Try to get structured data first, then rawOutput
            structured = data.get('structured', {})
            
            # Extract key insights
            strengths = structured.get('strengths', [])
            weaknesses = structured.get('weaknesses', [])
            advice = structured.get('advice', [])
            
            # Fallback to raw output if structured is empty but raw exists
            if not (strengths or weaknesses or advice) and data.get('rawOutput'):
                # Simple fallback: just show a snippet of raw output
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*👨‍🏫 銷售教練建議:*\n{data.get('rawOutput')[:500]}..."
                    }
                })
            else:
                # Format structured data
                coach_text = "*👨‍🏫 銷售教練建議:*\n\n"
                
                if strengths:
                    coach_text += "*💪 優點:*\n" + "\n".join([f"• {s}" for s in strengths]) + "\n\n"
                
                if weaknesses:
                    coach_text += "*📉 待改進:*\n" + "\n".join([f"• {w}" for w in weaknesses]) + "\n\n"
                    
                if advice:
                    coach_text += "*💡 具體建議:*\n" + "\n".join([f"• {a}" for a in advice])
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": coach_text
                    }
                })
            
            blocks.append({"type": "divider"})

        # Add Agent 7 (Customer Summary) Edit Link
        # URL: https://summary-web-service-acv3ye2faq-de.a.run.app/summary/{case_id}
        summary_url = f"https://summary-web-service-acv3ye2faq-de.a.run.app/summary/{case_id}"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "📝 *客戶摘要 (Agent 7)*\n請點擊下方按鈕檢視並編輯摘要，確認後再發送給團隊。"
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "✏️ 編輯摘要 & 發送",
                    "emoji": True
                },
                "value": "edit_summary",
                "url": summary_url,
                "action_id": "edit_summary_link"
            }
        })
        blocks.append({"type": "divider"})

        # Add action buttons (View Full Analysis)
        if success_count > 0:
            blocks.extend([
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "📊 查看完整分析詳情"
                            },
                            "value": f"view_analysis_{case_id}",
                            "action_id": "view_full_analysis"
                        }
                    ]
                }
            ])

        # Add retry button for failures
        if status == 'failed':
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "🔄 重新分析"
                        },
                        "style": "primary",
                        "value": f"retry_analysis_{case_id}",
                        "action_id": "retry_analysis"
                    }
                ]
            })

        return blocks

    def send_analysis_notification(
        self,
        case_id: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Send analysis completion notification to Slack.

        Args:
            case_id: Case ID
            user_id: Slack user ID (optional, will lookup from case data)

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

            # Serialize Firestore data to handle DatetimeWithNanoseconds objects
            case_data = self._serialize_firestore_data(case_data)

            analysis_data = case_data.get('analysis', {})

            if not analysis_data:
                logger.error(f"No analysis data for case {case_id}")
                return False

            # Determine target channel and thread_ts
            target_channel = None
            target_thread_ts = None

            # Prioritize original message context from case_data
            original_channel_id = case_data.get('channel_id')
            original_message_ts = case_data.get('message_ts')
            original_thread_ts = case_data.get('thread_ts')

            if original_channel_id and (original_message_ts or original_thread_ts):
                target_channel = original_channel_id
                target_thread_ts = original_thread_ts or original_message_ts
                logger.info(f"Found original Slack context for case {case_id}: channel={target_channel}, thread_ts={target_thread_ts}")
            else:
                # Fallback to user's DM if no original context
                if not user_id:
                    uploaded_by = case_data.get('uploadedBy')
                    if not uploaded_by:
                        logger.error(f"No uploadedBy field for case {case_id} and no original Slack context found.")
                        return False

                    user_id = self.get_user_slack_id(uploaded_by)
                    if not user_id:
                        logger.error(f"Could not find Slack user for {uploaded_by} and no original Slack context found.")
                        return False
                target_channel = user_id
                logger.info(f"No original Slack context found for case {case_id}, sending to user DM: {target_channel}")

            if not target_channel:
                logger.error(f"No target Slack channel determined for case {case_id}.")
                return False

            # Build message blocks
            blocks = self.build_analysis_blocks(case_id, case_data, analysis_data)

            # Send message
            response = self.client.chat_postMessage(
                channel=target_channel,
                text=f"分析完成：{case_data.get('storeName', case_id)}",
                blocks=blocks,
                thread_ts=target_thread_ts, # Use thread_ts if available
            )

            if response['ok']:
                # Store thread_ts in Firestore for future reference
                # If it was a new message, store its ts. If it was a reply, store the thread_ts.
                final_thread_ts = response.get('ts') or target_thread_ts
                final_channel = response.get('channel') or target_channel

                logger.info(f"Sent notification for case {case_id} to {final_channel}, thread: {final_thread_ts}")

                case_ref.update({
                    'notification': {
                        'slackThreadTs': final_thread_ts,
                        'slackChannelId': final_channel, # Store the actual channel where it was posted
                        'sentAt': firestore.SERVER_TIMESTAMP,
                    }
                })

                return True
            else:
                logger.error(f"Failed to send Slack message: {response}")
                return False

        except SlackApiError as e:
            logger.error(f"Slack API error sending notification for {case_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending notification for {case_id}: {e}", exc_info=True)
            return False

    def send_agent_reports(
        self,
        case_id: str,
        agent_results: Dict[str, Any],
    ) -> bool:
        """
        Send individual Agent reports to the original Slack thread.
        
        Args:
            case_id: Case ID
            agent_results: Dictionary of agent results with metadata containing reports
            
        Returns:
            True if all reports sent successfully
        """
        try:
            # Fetch case data to get thread_ts
            case_ref = self.db.collection('cases').document(case_id)
            case_doc = case_ref.get()

            if not case_doc.exists:
                logger.error(f"Case {case_id} not found")
                return False

            case_data = case_doc.to_dict()
            case_data = self._serialize_firestore_data(case_data)

            # Get original Slack context
            original_channel_id = case_data.get('channel_id')
            original_message_ts = case_data.get('message_ts')
            original_thread_ts = case_data.get('thread_ts')

            if not original_channel_id or not (original_message_ts or original_thread_ts):
                logger.warning(f"No original Slack context for case {case_id}, skipping agent reports")
                return False

            target_channel = original_channel_id
            target_thread_ts = original_thread_ts or original_message_ts

            # Agent names and emojis
            agent_info = {
                'agent1': {'name': 'Agent 1：戰場偵查 (Context & Structure)', 'emoji': '🔍'},
                'agent2': {'name': 'Agent 2：買家心理畫像 (MEDDIC)', 'emoji': '🧠'},
                'agent3': {'name': 'Agent 3：銷售教練 (Deal Strategist)', 'emoji': '📈'},
                'agent4': {'name': 'Agent 4：會議記錄秘書 (Executive Summary)', 'emoji': '📝'},
            }

            # Send each agent's report to the thread
            success_count = 0
            for agent_id in ['agent1', 'agent2', 'agent3', 'agent4']:
                agent_result = agent_results.get(agent_id)
                if not agent_result or not agent_result.success:
                    logger.warning(f"{agent_id} failed or not found, skipping report")
                    continue

                # Get report from metadata
                report = agent_result.metadata.get('report') if agent_result.metadata else None
                if not report:
                    logger.warning(f"{agent_id} has no report in metadata, skipping")
                    continue

                # Format the message
                info = agent_info.get(agent_id, {'name': agent_id, 'emoji': '📊'})
                
                # For Agent 4, add action buttons
                if agent_id == 'agent4':
                    # Build blocks with buttons for Agent 4
                    blocks = [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"{info['emoji']} *{info['name']}*\n\n{report}"
                            }
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "📝 編輯",
                                        "emoji": True
                                    },
                                    "action_id": "edit_summary",
                                    "value": case_id
                                },
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "📤 發送給客戶",
                                        "emoji": True
                                    },
                                    "style": "primary",
                                    "action_id": "send_to_customer",
                                    "value": case_id,
                                    "confirm": {
                                        "title": {
                                            "type": "plain_text",
                                            "text": "確認發送"
                                        },
                                        "text": {
                                            "type": "mrkdwn",
                                            "text": "確定要將會議記錄發送給客戶嗎？\n\n簡訊將包含網頁連結，客戶可以查看完整的會議記錄。"
                                        },
                                        "confirm": {
                                            "type": "plain_text",
                                            "text": "發送"
                                        },
                                        "deny": {
                                            "type": "plain_text",
                                            "text": "取消"
                                        }
                                    }
                                }
                            ]
                        }
                    ]
                    
                    # Send with blocks
                    try:
                        response = self.client.chat_postMessage(
                            channel=target_channel,
                            thread_ts=target_thread_ts,
                            text=f"{info['emoji']} *{info['name']}*\n\n{report}",
                            blocks=blocks,
                            mrkdwn=True,
                        )
                    except SlackApiError as e:
                        logger.error(f"Slack API error sending {agent_id} report: {e}")
                        continue
                else:
                    # For other agents, send simple message
                    message_text = f"{info['emoji']} *{info['name']}*\n\n{report}"
                    
                    try:
                        response = self.client.chat_postMessage(
                            channel=target_channel,
                            thread_ts=target_thread_ts,
                            text=message_text,
                            mrkdwn=True,
                        )
                    except SlackApiError as e:
                        logger.error(f"Slack API error sending {agent_id} report: {e}")
                        continue

            logger.info(f"Sent {success_count}/4 agent reports to Slack thread for case {case_id}")
            return success_count > 0

        except Exception as e:
            logger.error(f"Error sending agent reports for {case_id}: {e}", exc_info=True)
            return False

    def send_error_notification(
        self,
        case_id: str,
        error_message: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Send error notification to Slack.

        Args:
            case_id: Case ID
            error_message: Error description
            user_id: Slack user ID

        Returns:
            True if notification sent successfully
        """
        try:
            if not user_id:
                # Try to get from case data
                case_ref = self.db.collection('cases').document(case_id)
                case_doc = case_ref.get()
                if case_doc.exists:
                    case_data = case_doc.to_dict()
                    # Serialize Firestore data to handle DatetimeWithNanoseconds objects
                    case_data = self._serialize_firestore_data(case_data)
                    uploaded_by = case_data.get('uploadedBy')
                    if uploaded_by:
                        user_id = self.get_user_slack_id(uploaded_by)

            if not user_id:
                logger.error(f"Cannot send error notification, no user ID for case {case_id}")
                return False

            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "❌ 分析失敗"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*案件編號:* {case_id}\n\n*錯誤訊息:*\n{error_message}"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "🔄 重新分析"
                            },
                            "style": "primary",
                            "value": f"retry_analysis_{case_id}",
                            "action_id": "retry_analysis"
                        }
                    ]
                }
            ]

            response = self.client.chat_postMessage(
                channel=user_id,
                text=f"分析失敗：{case_id}",
                blocks=blocks,
            )

            return response['ok']

        except Exception as e:
            logger.error(f"Error sending error notification: {e}", exc_info=True)
            return False
