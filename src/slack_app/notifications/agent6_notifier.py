"""
Agent 6 Slack Notifier

Sends formatted sales coaching analysis results (Agent 6) to Slack.
Displays sales stage, deal health, key decision makers, and next actions.
"""

import logging
from typing import Dict, Any, List, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from google.cloud import firestore

logger = logging.getLogger(__name__)


class Agent6Notifier:
    """
    Handles Slack notifications for Agent 6 (Sales Coaching) results.
    """

    def __init__(self, slack_client: WebClient, db_client: firestore.Client):
        """
        Initialize Agent 6 notifier.

        Args:
            slack_client: Slack SDK WebClient
            db_client: Firestore client
        """
        self.client = slack_client
        self.db = db_client

    def build_agent6_blocks(
        self,
        case_id: str,
        agent6_data: Dict[str, Any],
        case_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Build Slack Block Kit blocks for Agent 6 results.

        Args:
            case_id: Case ID
            agent6_data: Agent 6 analysis results (structured object)
            case_metadata: Optional case metadata (storeName, customerId)

        Returns:
            List of Block Kit blocks
        """
        # Extract Agent 6 results (matching actual output structure)
        sales_stage = agent6_data.get('salesStage', '未知')  # String, not object
        deal_health = agent6_data.get('dealHealth', {})
        key_decision_maker = agent6_data.get('keyDecisionMaker', {})  # Singular
        next_actions = agent6_data.get('nextActions', [])  # Note: nextActions, not nextSteps
        maximum_risk = agent6_data.get('maximumRisk', {})
        rep_feedback = agent6_data.get('repFeedback', {})

        # Build header
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📊 銷售分析報告 (Agent 6)",
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

        # Sales Stage (string field)
        stage_emoji = self._get_stage_emoji(sales_stage)
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{stage_emoji} 銷售階段*\n`{sales_stage}`"
            }
        })

        # Deal Health
        health_score = deal_health.get('score', 0)
        health_sentiment = deal_health.get('sentiment', 'neutral')
        health_reasoning = deal_health.get('reasoning', '')
        health_emoji = self._get_health_emoji(health_score)

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{health_emoji} 成交健康度*\n`{health_sentiment.upper()}` ({health_score}/100)\n_{health_reasoning[:100]}_"
            }
        })

        blocks.append({"type": "divider"})

        # Key Decision Maker (singular)
        if key_decision_maker:
            dm_name = key_decision_maker.get('name', '未知')
            dm_role = key_decision_maker.get('role', '未知')
            dm_concerns = key_decision_maker.get('primaryConcerns', [])

            dm_text = f"*👤 關鍵決策者*\n• {dm_name} ({dm_role})"
            if dm_concerns:
                dm_text += "\n\n_主要考量：_\n"
                for concern in dm_concerns[:2]:  # Show top 2
                    dm_text += f"　• {concern}\n"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": dm_text
                }
            })

        # Maximum Risk (if any)
        if maximum_risk:
            risk_description = maximum_risk.get('risk', '')
            risk_mitigation = maximum_risk.get('mitigation', '')
            if risk_description:
                risk_text = f"*⚠️ 最大風險*\n{risk_description}"
                if risk_mitigation:
                    risk_text += f"\n\n_對策：_ {risk_mitigation[:100]}..."
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": risk_text
                    }
                })

        blocks.append({"type": "divider"})

        # Next Actions (sorted by priority)
        if next_actions:
            action_text = "*🎯 建議下一步行動*\n"
            # Sort by priority (1 = highest)
            sorted_actions = sorted(next_actions, key=lambda x: x.get('priority', 99))
            for action in sorted_actions[:4]:  # Show top 4
                priority = action.get('priority', 99)
                deadline = action.get('deadline', '')
                action_desc = action.get('action', '未知行動')

                # Priority emoji based on number
                if priority == 1:
                    priority_emoji = "🔴"
                elif priority == 2:
                    priority_emoji = "🟡"
                else:
                    priority_emoji = "🟢"

                action_text += f"{priority}. {priority_emoji} {action_desc}"
                if deadline:
                    action_text += f" _{deadline}_"
                action_text += "\n"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": action_text
                }
            })

        # Action buttons
        blocks.extend([
            {"type": "divider"},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📄 查看完整分析",
                            "emoji": True
                        },
                        "value": f"view_full_agent6_{case_id}",
                        "action_id": "view_full_agent6"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "💬 詢問 Agent 8",
                            "emoji": True
                        },
                        "value": f"ask_agent8_{case_id}",
                        "action_id": "ask_agent8"
                    }
                ]
            }
        ])

        return blocks

    def _get_stage_emoji(self, stage: str) -> str:
        """Get emoji for sales stage."""
        stage_emojis = {
            "初步接觸": "👋",
            "需求探索": "🔍",
            "需要證明型": "🎯",  # Actual value from Agent 6
            "方案提案": "📋",
            "商務談判": "💼",
            "合約簽訂": "✍️",
            "已結案": "✅"
        }
        return stage_emojis.get(stage, "📊")

    def _get_health_emoji(self, score: int) -> str:
        """Get emoji for deal health score."""
        if score >= 80:
            return "🟢"
        elif score >= 60:
            return "🟡"
        elif score >= 40:
            return "🟠"
        else:
            return "🔴"

    def send_agent6_notification(
        self,
        case_id: str,
        user_id: str,
        thread_ts: Optional[str] = None
    ) -> bool:
        """
        Send Agent 6 results notification to Slack.

        Args:
            case_id: Case ID
            user_id: Slack user ID
            thread_ts: Optional thread timestamp to reply in

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
            agents_data = analysis_data.get('agents', {})
            agent6_result = agents_data.get('agent6', {})

            # Check if Agent 6 completed successfully
            if agent6_result.get('status') != 'success':
                logger.warning(f"Agent 6 not successful for case {case_id}")
                return False

            agent6_data = agent6_result.get('data', {})
            if not agent6_data:
                logger.error(f"No Agent 6 data for case {case_id}")
                return False

            # Build message blocks
            case_metadata = {
                'storeName': case_data.get('storeName'),
                'customerId': case_data.get('customerId')
            }
            blocks = self.build_agent6_blocks(case_id, agent6_data, case_metadata)

            # Send message
            response = self.client.chat_postMessage(
                channel=user_id,
                thread_ts=thread_ts,
                text=f"📊 銷售分析報告 - {case_metadata.get('storeName', case_id)}",
                blocks=blocks
            )

            if response['ok']:
                logger.info(f"Sent Agent 6 notification for case {case_id} to {user_id}")

                # Update Firestore with notification timestamp
                case_ref.update({
                    'analysis.agents.agent6.notificationSentAt': firestore.SERVER_TIMESTAMP
                })

                return True
            else:
                logger.error(f"Failed to send Agent 6 notification: {response}")
                return False

        except SlackApiError as e:
            logger.error(f"Slack API error sending Agent 6 notification for {case_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending Agent 6 notification for {case_id}: {e}", exc_info=True)
            return False
