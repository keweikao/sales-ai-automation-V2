import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from google.cloud import firestore
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from .stats_service import StatsService

logger = logging.getLogger(__name__)

class ReportService:
    def __init__(self, db_client: firestore.Client, stats_service: StatsService, slack_client: WebClient, manager_channel_id: str):
        self.db = db_client
        self.stats = stats_service
        self.slack = slack_client
        self.manager_channel_id = manager_channel_id

    def generate_daily_risk_report(self) -> Dict[str, Any]:
        """
        Generates and sends the Daily Risk Alert to the manager channel.
        Scans yesterday's stats for risk cases.
        """
        yesterday = datetime.utcnow() - timedelta(days=1)
        risk_case_ids = self.stats.get_daily_risk_cases(yesterday)
        
        if not risk_case_ids:
            logger.info("No risk cases found for yesterday.")
            return {"status": "skipped", "reason": "no_risks"}

        # Fetch case details
        cases = self._fetch_cases(risk_case_ids)
        
        # Format Message
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"🚨 {yesterday.strftime('%Y-%m-%d')} 風險案件提醒", "emoji": True}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"系統在過去 24 小時內偵測到 *{len(cases)}* 筆高風險案件，請留意："}
            },
            {"type": "divider"}
        ]

        for case in cases:
            rep_name = case.get("salesRep", {}).get("name", "Unknown")
            customer = case.get("storeName", "Unknown Store")
            analysis = case.get("analysis", {})
            
            # Extract Risk Reasons
            reasons = []
            agent3 = analysis.get("agents", {}).get("agent3", {}).get("data", {})
            if agent3.get("progress_score", 0) < 40:
                reasons.append(f"⚠️ 推進力低 ({agent3.get('progress_score')})")
            
            agent1 = analysis.get("agents", {}).get("agent1", {}).get("data", {})
            if "高" in agent1.get("urgency_level", "") and "只有員工" in agent1.get("decision_maker", ""):
                reasons.append("🚫 無效急單 (急件但老闆不在)")

            reason_str = "、".join(reasons) or "系統判定風險"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"• *[{rep_name}] {customer}*\n   {reason_str}"
                }
            })

        # Send to Slack
        try:
            self.slack.chat_postMessage(channel=self.manager_channel_id, blocks=blocks, text="🚨 風險案件提醒")
            return {"status": "sent", "count": len(cases)}
        except SlackApiError as e:
            logger.error(f"Failed to send risk report: {e}")
            return {"status": "error", "error": str(e)}

    def generate_weekly_reports(self) -> Dict[str, Any]:
        """
        Generates Weekly Reports:
        1. Personal Report (DM to each Rep)
        2. Manager Report (Channel)
        """
        # Define Week Range (Assuming run on Friday afternoon for Mon-Fri)
        today = datetime.utcnow()
        start_of_week = today - timedelta(days=today.weekday()) # Monday
        end_of_week = today # Today (Friday)
        
        # Aggregated Stats
        stats = self.stats.get_weekly_stats(start_of_week, end_of_week)
        
        results = {
            "personal_sent": 0,
            "manager_sent": False
        }

        # 1. Send Personal Reports
        for uid, rep_data in stats["reps"].items():
            try:
                self._send_personal_report(uid, rep_data, start_of_week, end_of_week)
                results["personal_sent"] += 1
            except Exception as e:
                logger.error(f"Failed to send report to {uid}: {e}")

        # 2. Send Manager Report
        try:
            self._send_manager_report(stats, start_of_week, end_of_week)
            results["manager_sent"] = True
        except Exception as e:
            logger.error(f"Failed to send manager report: {e}")

        return results

    def _send_personal_report(self, user_id: str, data: Dict, start: datetime, end: datetime):
        """Send Weekly DM to Sales Rep"""
        demo_count = data.get("demo_count", 0)
        total_score = data.get("total_score", 0)
        avg_score = int(total_score / demo_count) if demo_count > 0 else 0
        
        # Fetch Opportunities
        high_priority_ids = data.get("high_priority_cases", [])
        opportunities = self._fetch_cases(high_priority_ids[:5]) # Limit 5
        
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "👋 本週個人戰報", "emoji": True}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*📊 本週 Demo 數:*\n{demo_count}"},
                    {"type": "mrkdwn", "text": f"*🔥 平均推進力:*\n{avg_score}"}
                ]
            }
        ]
        
        if opportunities:
            blocks.append({"type": "divider"})
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*🔥 優先處理 (快成交了)*"}})
            for case in opportunities:
                store_name = case.get("storeName", "Unknown")
                agent3 = case.get("analysis", {}).get("agents", {}).get("agent3", {}).get("data", {})
                score = agent3.get("progress_score", 0)
                next_step = agent3.get("next_action", {}).get("action", "跟進")
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"• *{store_name}* (分數: {score})\n   💡 建議: {next_step}"}
                })

        self.slack.chat_postMessage(channel=user_id, blocks=blocks, text="📊 您的本週個人戰報")

    def _send_manager_report(self, stats: Dict, start: datetime, end: datetime):
        """Send Weekly Team Report to Manager Channel"""
        total_demos = stats.get("total_demos", 0)
        weighted_sum = stats.get("weighted_score_sum", 0)
        team_avg = int(weighted_sum / total_demos) if total_demos > 0 else 0
        
        # Sort Reps by Score (Quality)
        reps_list = []
        for uid, r in stats["reps"].items():
            count = r.get("demo_count", 0)
            avg = int(r.get("total_score", 0) / count) if count > 0 else 0
            reps_list.append({
                "name": r.get("name", "Unknown"),
                "count": count,
                "avg": avg
            })
        
        # Sort by Count DESC, then Avg DESC
        reps_list.sort(key=lambda x: (x["count"], x["avg"]), reverse=True)
        
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "📊 團隊業務週報", "emoji": True}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*📈 團隊總 Demo:*\n{total_demos}"},
                    {"type": "mrkdwn", "text": f"*⭐ 平均推進力:*\n{team_avg}"}
                ]
            },
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": "*🏆 成員績效排行*"}}
        ]
        
        # Build Table-like text
        table_text = "*Rank | 業務 | Demo | 分數*\n"
        metrics = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        
        for i, rep in enumerate(reps_list[:10]): # Top 10
            rank = metrics[i] if i < len(metrics) else f"{i+1}."
            status = "🔥" if rep["avg"] >= 80 else "⚠️" if rep["avg"] < 50 else ""
            table_text += f"{rank} | {rep['name']} | {rep['count']} | {rep['avg']} {status}\n"
            
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": table_text}})
        
        self.slack.chat_postMessage(channel=self.manager_channel_id, blocks=blocks, text="📊 團隊業務週報")

    def _fetch_cases(self, case_ids: List[str]) -> List[Dict]:
        """Helper to batch fetch cases"""
        if not case_ids:
            return []
        
        # Firestore supports max 10 in 'in' query, or we can use getAll
        # getAll is better for ID lists
        refs = [self.db.collection("cases").document(cid) for cid in case_ids]
        snapshots = self.db.get_all(refs)
        
        return [doc.to_dict() for doc in snapshots if doc.exists]
