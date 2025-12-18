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
        Build Slack Block Kit blocks for analysis results (V2 Architecture).
        
        This is the main summary notification. Detailed agent reports are sent
        as separate messages to the thread.

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
                        "text": f"*客戶:*\n{case_data.get('customerName') or case_data.get('storeName') or 'N/A'}"
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

        # V2 Architecture Agent names
        agent_names = {
            'agent1': '🔍 戰場偵查',
            'agent2': '🧠 買家分析',
            'agent3': '📈 銷售教練',
            'agent4': '📝 會議摘要',
        }

        agent_section_fields = []
        for agent_id in ['agent1', 'agent2', 'agent3', 'agent4']:
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
                        "text": "⚠️ 部分分析項目失敗，結果可能不完整。"
                    }
                ]
            })

        blocks.append({"type": "divider"})

        # --- Add Summary Content from Agent 4 ---
        summary_base_url = "https://summary-web-service-497329205771.asia-east1.run.app"
        edit_url = f"{summary_base_url}/edit/{case_id}"
        preview_url = f"{summary_base_url}/summary/{case_id}"
        
        # Get Agent 4 data for summary
        agent4_data = agents.get('agent4', {}).get('data', {})
        
        # Build summary text from Agent 4 data
        summary_parts = []
        
        # Pain points
        pain_points = agent4_data.get('pain_points', [])
        if pain_points:
            summary_parts.append("*🔴 客戶痛點:*")
            for pp in pain_points[:3]:
                summary_parts.append(f"   • {pp[:80]}...")
        
        # Solutions provided
        solutions = agent4_data.get('solutions', [])
        if solutions:
            summary_parts.append("\n*🟢 解決方案:*")
            for sol in solutions[:3]:
                summary_parts.append(f"   • {sol[:80]}...")
        
        # Key decisions
        key_decisions = agent4_data.get('key_decisions', [])
        if key_decisions:
            summary_parts.append("\n*📋 關鍵決策:*")
            for kd in key_decisions[:3]:
                summary_parts.append(f"   • {kd[:80]}...")
        
        if summary_parts:
            summary_text = "\n".join(summary_parts)
        else:
            summary_text = "_摘要內容解析中..._"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"📝 *會議記錄摘要*\n\n{summary_text}"
            }
        })
        
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"<{preview_url}|👁️ 預覽完整頁面>"
                }
            ]
        })
        
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
                    "action_id": "edit_summary_link",
                    "url": edit_url,
                    "value": "edit_summary"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📱 發送簡訊",
                        "emoji": True
                    },
                    "style": "primary",
                    "action_id": "open_send_sms_modal",
                    "value": case_id
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📧 發送 Email",
                        "emoji": True
                    },
                    "action_id": "open_send_email_modal",
                    "value": case_id
                }
            ]
        })

        # Add retry button for failures
        if status == 'failed':
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "🔄 重新分析"
                        },
                        "style": "danger",
                        "value": f"retry_analysis_{case_id}",
                        "action_id": "retry_analysis"
                    }
                ]
            })

        # Note: Agent reports to thread have been disabled per user request
        # The block below was removed to avoid confusion
        # blocks.append({
        #     "type": "context",
        #     "elements": [
        #         {
        #             "type": "mrkdwn",
        #             "text": "💡 詳細分析報告已發送至討論串，請往下查看。"
        #         }
        #     ]
        # })

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
                text=f"分析完成：{case_data.get('customerName') or case_data.get('storeName') or case_id}",
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

                # Send detailed agent reports to the thread
                try:
                    self.send_agent_reports_from_firestore(
                        case_id=case_id,
                        channel=final_channel,
                        thread_ts=final_thread_ts,
                        agents_data=analysis_data.get('agents', {}),
                    )
                except Exception as e:
                    logger.error(f"Failed to send agent reports for {case_id}: {e}")
                    # Don't fail the entire notification

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
    
    def send_agent_reports_from_firestore(
        self,
        case_id: str,
        channel: str,
        thread_ts: str,
        agents_data: Dict[str, Any],
    ) -> bool:
        """
        Send Agent 1-3 detailed reports to a Slack thread.
        
        Args:
            case_id: Case ID
            channel: Slack channel ID
            thread_ts: Thread timestamp
            agents_data: Dictionary of agent results from Firestore
            
        Returns:
            True if reports sent successfully
        """
        # Agent info for formatting
        agent_info = {
            'agent1': {
                'name': '🔍 Agent 1：戰場偵查 (Context)',
                'formatter': self._format_agent1_report
            },
            'agent2': {
                'name': '🧠 Agent 2：買家分析 (Buyer)',
                'formatter': self._format_agent2_report
            },
            'agent3': {
                'name': '📈 Agent 3：銷售教練 (Seller)',
                'formatter': self._format_agent3_report
            },
        }
        
        success_count = 0
        
        # Only send Agent 1, 2, 3 (Agent 4 is shown via the web link)
        for agent_id in ['agent1', 'agent2', 'agent3']:
            agent_result = agents_data.get(agent_id, {})
            if agent_result.get('status') != 'success':
                continue
            
            agent_data = agent_result.get('data', {})
            if not agent_data:
                continue
            
            info = agent_info.get(agent_id)
            if not info:
                continue
            
            # Format the report using agent-specific formatter
            report_text = info['formatter'](agent_data)
            if not report_text:
                continue
            
            # Build message
            message_text = f"{info['name']}\n\n{report_text}"
            
            # Truncate if too long (Slack limit is about 4000 chars for text)
            if len(message_text) > 3500:
                message_text = message_text[:3500] + "\n\n_(內容過長已截斷)_"
            
            try:
                response = self.client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text=message_text,
                    mrkdwn=True,
                )
                if response['ok']:
                    success_count += 1
                    logger.info(f"Sent {agent_id} report to thread for case {case_id}")
            except SlackApiError as e:
                logger.error(f"Failed to send {agent_id} report: {e}")
        
        logger.info(f"Sent {success_count}/3 agent reports for case {case_id}")
        return success_count > 0
    
    def _format_agent1_report(self, data: Dict[str, Any]) -> str:
        """Format Agent 1 (Context/戰場偵查) report with V2 structure."""
        sections = []
        
        # Authority Status - 權威驗證
        authority = data.get('authority_status', '')
        if authority:
            authority_emoji = {
                'Confirmed Owner': '✅',
                'Suspected Owner': '🔸',
                'Employee': '🔹',
                'Unknown': '❓',
            }.get(authority, '❓')
            sections.append(f"👤 *權威驗證*: {authority_emoji} {authority}")
        
        # Urgency - 急迫性評估
        urgency = data.get('urgency', {})
        if urgency:
            level = urgency.get('level', 'Unknown')
            level_emoji = {'High': '🔴', 'Medium': '🟡', 'Low': '🟢'}.get(level, '⚪')
            urgency_text = f"⏰ *急迫性*: {level_emoji} {level}"
            
            deadline = urgency.get('deadline_date')
            if deadline:
                urgency_text += f"\n    📅 預計時程：{deadline}"
            
            driver = urgency.get('primary_driver')
            if driver:
                urgency_text += f"\n    🎯 主要驅動因素：{driver}"
            
            sections.append(urgency_text)
        
        # Constraints - 硬性限制
        constraints = data.get('constraints', [])
        if constraints:
            constraint_text = "🚧 *硬性限制*:\n"
            for c in constraints:
                constraint_text += f"    • {c}\n"
            sections.append(constraint_text.strip())
        
        # Meta Validation - 資訊驗證
        meta_validation = data.get('meta_validation', '')
        if meta_validation:
            validation_emoji = {
                'Consistent': '✅',
                'Partial Match': '🔸',
                'Inconsistent': '❌',
            }.get(meta_validation, '❓')
            sections.append(f"📋 *資訊驗證*: {validation_emoji} {meta_validation}")
        
        return "\n\n".join(sections) if sections else ""
    
    def _format_agent2_report(self, data: Dict[str, Any]) -> str:
        """Format Agent 2 (Buyer 買家分析) report with V2 structure."""
        lines = []
        
        # Buyer Type - 買家類型
        buyer_type = data.get('buyer_type', {})
        if buyer_type:
            type_name = buyer_type.get('type', '') if isinstance(buyer_type, dict) else str(buyer_type)
            type_emoji = {
                'Impulsive': '⚡',
                'Calculated': '🧮',
                'Skeptical': '🤔',
            }.get(type_name, '👤')
            lines.append(f"*{type_emoji} 買家類型*: {type_name}")
        
        # Trust Score - 信任度
        trust_score = data.get('trust_score', '')
        if trust_score:
            trust_emoji = {'High': '🟢', 'Medium': '🟡', 'Low': '🔴'}.get(trust_score, '⚪')
            lines.append(f"*🤝 信任度*: {trust_emoji} {trust_score}")
        
        # Primary Blocker - 主要阻礙
        primary_blocker = data.get('primary_blocker', '')
        if primary_blocker:
            lines.append(f"*🚧 主要阻礙*:\n{primary_blocker}")
        
        # Hesitations - 猶豫點
        hesitations = data.get('hesitations', [])
        if hesitations:
            hesitation_text = "*❓ 猶豫點*:\n"
            for h in hesitations[:3]:  # 最多顯示 3 個
                if isinstance(h, dict):
                    topic = h.get('topic', '')
                    hesitation_text += f"    • {topic}\n"
                else:
                    hesitation_text += f"    • {h}\n"
            lines.append(hesitation_text.strip())
        
        # Implementation Fear - 導入恐懼
        impl_fear = data.get('implementation_fear', {})
        if impl_fear and impl_fear.get('detected'):
            topic = impl_fear.get('topic', '未指定')
            complexity = impl_fear.get('complexity', 'Unknown')
            lines.append(f"*😰 導入恐懼*: {topic} (複雜度: {complexity})")
        
        # Missed Buying Signals - 錯失的購買信號
        missed_signals = data.get('missed_buying_signals', [])
        if missed_signals:
            signal_text = "*📡 錯失的購買信號*:\n"
            for s in missed_signals[:3]:
                signal_text += f"    • {s}\n"
            lines.append(signal_text.strip())
        
        # MEDDIC
        meddic = data.get('meddic', {})
        if meddic:
            meddic_lines = []
            if meddic.get('identified_pain'):
                pain = meddic['identified_pain'][:100] + '...' if len(meddic['identified_pain']) > 100 else meddic['identified_pain']
                meddic_lines.append(f"*Pain*: {pain}")
            if meddic.get('decision_criteria'):
                criteria = meddic['decision_criteria'][:100] + '...' if len(meddic['decision_criteria']) > 100 else meddic['decision_criteria']
                meddic_lines.append(f"*Decision Criteria*: {criteria}")
            
            if meddic_lines:
                lines.append(f"*📈 MEDDIC*:\n" + "\n".join([f"    {l}" for l in meddic_lines]))
        
        return "\n\n".join(lines) if lines else ""
    
    def _format_agent3_report(self, data: Dict[str, Any]) -> str:
        """Format Agent 3 (Seller/Coach 逼單教練) report with V2 structure."""
        lines = []
        
        # Closing Score - 逼單評分
        closing_score = data.get('closing_score', 0)
        if closing_score:
            score_emoji = "🟢" if closing_score >= 70 else "🟡" if closing_score >= 50 else "🔴"
            lines.append(f"*{score_emoji} 逼單評分*: {closing_score}/100")
        
        # Strategy Mode - 策略模式
        strategy_mode = data.get('strategy_mode', '')
        if strategy_mode:
            mode_zh = {
                'HardClose': '🔥 強力逼單',
                'MicroCommit': '🔸 微承諾推進',
                'PullBack': '🔄 暫停後退',
            }.get(strategy_mode, strategy_mode)
            lines.append(f"*📋 策略模式*: {mode_zh}")
        
        # Recommended CE - 建議 CE
        recommended_ce = data.get('recommended_ce', '')
        if recommended_ce:
            ce_zh = {
                'CE1': 'CE1 - 預約安裝',
                'CE2': 'CE2 - 索取菜單資料',
                'CE3': 'CE3 - 同意提供報價',
            }.get(recommended_ce, recommended_ce)
            lines.append(f"*🎯 建議下一步*: {ce_zh}")
        
        # Safety Alert - 安全警示
        safety_alert = data.get('safety_alert')
        if safety_alert:
            lines.append("*⚠️ 安全警示*: 客戶可能有抵觸情緒，建議放緩節奏")
        
        # Pitch Diagnosis - 簡報診斷
        pitch_diagnosis = data.get('pitch_diagnosis', {})
        if pitch_diagnosis:
            pain_addressed = pitch_diagnosis.get('pain_addressed', False)
            pain_emoji = "✅" if pain_addressed else "❌"
            lines.append(f"*💡 痛點覆蓋*: {pain_emoji}")
            
            improvements = pitch_diagnosis.get('improvement_areas', [])
            if improvements:
                lines.append(f"*📝 改進建議*:\n" + "\n".join([f"    • {i}" for i in improvements[:3]]))
        
        # Coach Tips - 教練提示
        coach_tips = data.get('coach_tips', [])
        if coach_tips:
            lines.append(f"*💬 教練提示*:\n" + "\n".join([f"    • {t}" for t in coach_tips[:3]]))
        
        # Killer Line - 必殺話術
        killer_line = data.get('killer_line', '')
        if killer_line:
            lines.append(f"*🗡️ 必殺話術*:\n「{killer_line}」")
        
        return "\n\n".join(lines) if lines else ""

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
