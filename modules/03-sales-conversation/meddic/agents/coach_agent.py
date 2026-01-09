"""
Agent 5: Sales Coach - 即時銷售教練

在每次分析完成後評估是否需要發送提醒給業務或主管。
支援 Slack Thread 互動對話。

Migration note: From analysis-service/src/agents/agent5_coach.py
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from google.cloud import firestore

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None

logger = logging.getLogger(__name__)


@dataclass
class ManagerAlert:
    """Structure for a Manager-facing Alert (主管警示)"""
    alert_type: str  # 'consecutive_low_scores', 'high_risk_deal'
    rep_id: str
    rep_name: str
    case_id: str
    reason: str
    severity: str = "medium"  # medium, high
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_type": self.alert_type,
            "rep_id": self.rep_id,
            "rep_name": self.rep_name,
            "case_id": self.case_id,
            "reason": self.reason,
            "severity": self.severity,
            "timestamp": self.timestamp,
            "sent": False
        }


@dataclass
class CoachAlert:
    """教練提醒資料結構"""
    case_id: str
    rep_id: str
    rep_name: str
    store_name: str
    alert_type: str  # close_now | missed_dm | excellent | low_progress | competitor
    message: str
    suggestion: str
    progress_score: int
    urgency: str
    decision_maker: str


class CoachAgent:
    """
    即時銷售教練 Agent

    Phase 1: 規則引擎判斷是否發送提醒
    Phase 2: 支援 Slack Thread 互動對話
    """

    # 提醒訊息模板
    ALERT_TEMPLATES = {
        "close_now": {
            "emoji": "🔥",
            "title": "立即成交機會",
            "message": "客戶急迫度高且決策者到場，這是成交的絕佳時機！",
            "suggestion": "建議 24 小時內發送報價，把握成交機會。",
        },
        "missed_dm": {
            "emoji": "⚠️",
            "title": "錯失關鍵人物",
            "message": "客戶需求急迫，但本次 Demo 僅員工接待。",
            "suggestion": "建議盡快約老闆或主管進行第二次 Demo。",
        },
        "excellent": {
            "emoji": "🏆",
            "title": "優異表現",
            "message": "這次 Demo 推進力極高，做得非常好！",
            "suggestion": "繼續保持，這個客戶很有機會成交。",
        },
        "low_progress": {
            "emoji": "📉",
            "title": "需要關注",
            "message": "這次 Demo 推進力偏低，可能需要調整策略。",
            "suggestion": "建議回顧對話，找出客戶的真正顧慮並跟進。",
        },
    }

    def __init__(
        self,
        db_client: firestore.Client,
        gemini_api_key: Optional[str] = None,
    ):
        self.db = db_client
        self.collection_name = "coach_alerts"

        # 初始化 Gemini (用於 Phase 2 對話)
        if GENAI_AVAILABLE and gemini_api_key:
            genai.configure(api_key=gemini_api_key)
            self.gemini_model = genai.GenerativeModel("gemini-2.0-flash")
            logger.info("CoachAgent: Gemini initialized for conversation")
        else:
            self.gemini_model = None
            logger.warning("CoachAgent: Gemini not available")

    # =========================================================================
    # Phase 1: 規則引擎
    # =========================================================================

    def evaluate(
        self,
        case_id: str,
        rep_id: str,
        rep_name: str,
        store_name: str,
        context_data: Dict[str, Any],
        buyer_data: Dict[str, Any],
        seller_data: Dict[str, Any],
    ) -> Optional[CoachAlert]:
        """
        評估是否需要發送即時提醒

        Args:
            case_id: 案件 ID
            rep_id: 業務 Slack User ID
            rep_name: 業務姓名
            store_name: 客戶店名
            context_data: Agent 1 結果
            buyer_data: Agent 2 結果
            seller_data: Agent 3 結果

        Returns:
            CoachAlert if alert needed, None otherwise
        """
        # 取得關鍵指標
        progress_score = seller_data.get("progress_score", 0)
        strategy = seller_data.get("recommended_strategy", "")
        urgency = context_data.get("urgency_level", "中")
        decision_maker = context_data.get("decision_maker", "")

        # 規則 1: 立即成交機會
        if progress_score >= 80 and "CloseNow" in strategy:
            return self._build_alert(
                "close_now", case_id, rep_id, rep_name, store_name,
                progress_score, urgency, decision_maker
            )

        # 規則 2: 錯失關鍵人物
        if self._is_high_urgency(urgency) and self._is_staff_only(decision_maker):
            return self._build_alert(
                "missed_dm", case_id, rep_id, rep_name, store_name,
                progress_score, urgency, decision_maker
            )

        # 規則 3: 優異表現
        if progress_score >= 90:
            return self._build_alert(
                "excellent", case_id, rep_id, rep_name, store_name,
                progress_score, urgency, decision_maker
            )

        # 規則 4: 低推進力（暫時不啟用，避免過多通知）
        # if progress_score < 40:
        #     return self._build_alert("low_progress", ...)

        logger.info(f"Case {case_id}: No coach alert triggered (progress={progress_score})")
        return None

    def _is_high_urgency(self, urgency: str) -> bool:
        """判斷是否為高急迫度"""
        return any(k in urgency.lower() for k in ["高", "high", "urgent", "緊急"])

    def _is_staff_only(self, decision_maker: str) -> bool:
        """判斷是否只有員工接待"""
        dm_lower = decision_maker.lower()
        staff_keywords = ["員工", "staff", "店員", "服務員"]
        boss_keywords = ["老闆", "owner", "主管", "manager", "經理"]

        has_staff = any(k in dm_lower for k in staff_keywords)
        has_boss = any(k in dm_lower for k in boss_keywords)

        return has_staff and not has_boss

    def _build_alert(
        self,
        alert_type: str,
        case_id: str,
        rep_id: str,
        rep_name: str,
        store_name: str,
        progress_score: int,
        urgency: str,
        decision_maker: str,
    ) -> CoachAlert:
        """建立提醒物件"""
        template = self.ALERT_TEMPLATES.get(alert_type, self.ALERT_TEMPLATES["close_now"])

        return CoachAlert(
            case_id=case_id,
            rep_id=rep_id,
            rep_name=rep_name,
            store_name=store_name,
            alert_type=alert_type,
            message=template["message"],
            suggestion=template["suggestion"],
            progress_score=progress_score,
            urgency=urgency,
            decision_maker=decision_maker,
        )

    # =========================================================================
    # Slack 訊息格式
    # =========================================================================

    def build_alert_blocks(self, alert: CoachAlert) -> List[Dict]:
        """建立 Slack Block Kit 訊息"""
        template = self.ALERT_TEMPLATES.get(alert.alert_type, {})
        emoji = template.get("emoji", "💡")
        title = template.get("title", "銷售教練提醒")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} 【{title}】",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*客戶：*\n{alert.store_name}"},
                    {"type": "mrkdwn", "text": f"*推進分數：*\n{alert.progress_score}"},
                ]
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": alert.message}
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"💡 *建議：*\n{alert.suggestion}"}
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": "有疑慮請直接在此 thread 回覆，我會查看對話記錄回應你。"}
                ]
            }
        ]

        return blocks

    # =========================================================================
    # Phase 2: Slack Thread 對話
    # =========================================================================

    def respond(
        self,
        case_id: str,
        user_message: str,
        original_suggestion: str,
        thread_history: Optional[List[Dict]] = None,
    ) -> str:
        """
        回應業務在 Thread 中的疑慮

        Args:
            case_id: 案件 ID
            user_message: 業務的回覆
            original_suggestion: 原始建議
            thread_history: Thread 中的對話歷史

        Returns:
            AI 回覆
        """
        if not self.gemini_model:
            return "抱歉，AI 對話功能暫時無法使用。"

        try:
            # 載入逐字稿
            transcript = self._load_transcript(case_id)

            # 搜尋相關片段
            relevant_segments = self._search_relevant_segments(transcript, user_message)

            # 組裝 Prompt
            history_text = ""
            if thread_history:
                for msg in thread_history[-5:]:  # 最多取最近 5 則
                    role = "業務" if msg.get("is_user") else "教練"
                    history_text += f"{role}：{msg.get('text', '')}\n"

            prompt = f"""你是銷售教練，業務對你的建議有疑慮。請用繁體中文回覆。

原始建議：{original_suggestion}

業務回覆：{user_message}

相關對話片段：
{relevant_segments}

{f"之前的討論：{history_text}" if history_text else ""}

請注意：
1. 如果業務說的有道理，請承認並修正建議
2. 如果需要更多資訊，可以詢問
3. 回覆簡短（50-100字），親切專業
4. 引用對話時標註時間戳"""

            response = self.gemini_model.generate_content(prompt)
            return response.text.strip()

        except Exception as e:
            logger.error(f"CoachAgent respond failed: {e}", exc_info=True)
            return "抱歉，我在處理你的問題時遇到了一些困難。請稍後再試。"

    def _load_transcript(self, case_id: str) -> str:
        """載入案件的逐字稿"""
        try:
            case_doc = self.db.collection("cases").document(case_id).get()
            if not case_doc.exists:
                return ""

            case_data = case_doc.to_dict() or {}
            segments = case_data.get("transcriptSegments", [])

            # 組裝逐字稿文字
            lines = []
            for seg in segments:
                speaker = seg.get("speaker", "Unknown")
                text = seg.get("text", "")
                start_time = seg.get("startTime", 0)

                # 格式化時間
                minutes = int(start_time // 60)
                seconds = int(start_time % 60)
                time_str = f"{minutes:02d}:{seconds:02d}"

                lines.append(f"[{time_str}] {speaker}: {text}")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Failed to load transcript for {case_id}: {e}")
            return ""

    def _search_relevant_segments(self, transcript: str, query: str) -> str:
        """
        搜尋與問題相關的對話片段

        簡單實作：關鍵字匹配
        進階可用 embedding search
        """
        if not transcript:
            return "（無可用的對話記錄）"

        # 提取關鍵字
        keywords = self._extract_keywords(query)

        # 搜尋包含關鍵字的行
        lines = transcript.split("\n")
        relevant = []

        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(kw in line_lower for kw in keywords):
                # 取得該行及前後各一行
                start = max(0, i - 1)
                end = min(len(lines), i + 2)
                context = lines[start:end]
                relevant.extend(context)

        if not relevant:
            # 如果沒找到，返回最後幾行
            return "\n".join(lines[-5:]) if lines else "（無可用的對話記錄）"

        # 去重並限制長度
        seen = set()
        unique = []
        for line in relevant:
            if line not in seen:
                seen.add(line)
                unique.append(line)

        return "\n".join(unique[:10])

    def _extract_keywords(self, text: str) -> List[str]:
        """提取關鍵字"""
        # 簡單實作：移除常見詞，取重要詞
        stopwords = ["但", "是", "的", "了", "在", "有", "我", "你", "他", "她", "它",
                     "說", "客戶", "這個", "那個", "什麼", "怎麼"]

        words = []
        for word in text:
            if len(word) >= 2 and word not in stopwords:
                words.append(word.lower())

        # 也加入整個 query 的子串
        if len(text) >= 2:
            words.append(text.lower())

        return list(set(words))[:5]

    # =========================================================================
    # 資料持久化
    # =========================================================================

    def save_alert(
        self,
        alert: CoachAlert,
        slack_channel: str,
        slack_ts: str,
    ) -> str:
        """儲存提醒到 Firestore"""
        doc_id = f"{alert.case_id}_{alert.alert_type}_{int(datetime.utcnow().timestamp())}"

        data = {
            "caseId": alert.case_id,
            "repId": alert.rep_id,
            "repName": alert.rep_name,
            "storeName": alert.store_name,
            "alertType": alert.alert_type,
            "message": alert.message,
            "suggestion": alert.suggestion,
            "progressScore": alert.progress_score,
            "slackChannel": slack_channel,
            "slackTs": slack_ts,
            "status": "active",
            "createdAt": firestore.SERVER_TIMESTAMP,
        }

        self.db.collection(self.collection_name).document(doc_id).set(data)
        logger.info(f"Saved coach alert: {doc_id}")

        return doc_id

    def get_alert_by_thread_ts(self, thread_ts: str) -> Optional[Dict]:
        """根據 Slack Thread TS 取得提醒 (搜尋 Coach Alerts 和 Manager Alerts)"""
        try:
            # 1. Search Coach Alerts
            query = (
                self.db.collection(self.collection_name)
                .where("slackTs", "==", thread_ts)
                .limit(1)
            )
            docs = list(query.stream())
            if docs:
                return docs[0].to_dict()

            # 2. Search Manager Alerts
            query_manager = (
                self.db.collection("manager_alerts")
                .where("slackTs", "==", thread_ts)
                .limit(1)
            )
            docs_manager = list(query_manager.stream())
            if docs_manager:
                return docs_manager[0].to_dict()

            return None

        except Exception as e:
            logger.error(f"Failed to get alert by thread_ts: {e}")
            return None

    # =========================================================================
    # Phase 5: Manager Alerting
    # =========================================================================

    def evaluate_manager_alert(self, case_id: str, rep_id: str, current_score: int) -> Optional[ManagerAlert]:
        """
        Check if a Manager Alert should be triggered based on history.
        Rule: 3 consecutive cases with progress_score < 50.
        """
        if not self.db or not rep_id:
            return None

        # 1. Check current score condition first
        if current_score >= 50:
            return None

        try:
            # 2. Query last 2 COMPLETED cases for this rep
            cases_ref = (
                self.db.collection("cases")
                .where("uploadedBy", "==", rep_id)
                .where("status", "==", "completed")
                .order_by("createdAt", direction=firestore.Query.DESCENDING)
                .limit(2)
            )

            docs = list(cases_ref.stream())

            if len(docs) < 2:
                return None

            prev_scores = []
            for doc in docs:
                data = doc.to_dict()
                agent3 = data.get("analysis", {}).get("agents", {}).get("agent3", {}).get("data", {})
                score = agent3.get("progress_score", 100)

                if score < 50:
                    prev_scores.append(score)
                else:
                    return None

            rep_name = docs[0].to_dict().get("uploadedByName") or docs[0].to_dict().get("salesRepName", "Unknown")
            scores_str = f"{current_score}, " + ", ".join(map(str, prev_scores))

            return ManagerAlert(
                alert_type="consecutive_low_scores",
                rep_id=rep_id,
                rep_name=rep_name,
                case_id=case_id,
                reason=f"連續 3 筆案件推進力低於 50 (近期分數: {scores_str})",
                severity="high"
            )

        except Exception as e:
            logger.error(f"Error checking manager alert: {e}")
            return None

    def save_manager_alert(self, alert: ManagerAlert, slack_channel: str = None, slack_ts: str = None):
        """Save manager alert to Firestore"""
        if not self.db:
            return

        try:
            data = alert.to_dict()
            if slack_channel:
                data["slackChannel"] = slack_channel
            if slack_ts:
                data["slackTs"] = slack_ts

            self.db.collection("manager_alerts").add(data)
            logger.info(f"Saved manager alert for {alert.rep_name}")
        except Exception as e:
            logger.error(f"Failed to save manager alert: {e}")

    def build_manager_alert_blocks(self, alert: ManagerAlert) -> List[Dict]:
        """Build Slack Block Kit message for Manager"""
        return [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🚨 業務異常狀況警示", "emoji": True}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*業務:* {alert.rep_name}"},
                    {"type": "mrkdwn", "text": "*類型:* 連續表現低落"},
                    {"type": "mrkdwn", "text": f"*嚴重性:* {alert.severity.upper()}"}
                ]
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*原因:* {alert.reason}"}
            },
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"Latest Case ID: {alert.case_id}"}]
            }
        ]
