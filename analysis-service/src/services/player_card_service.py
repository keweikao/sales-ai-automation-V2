"""
Player Card Service - 銷售動能球員卡生成服務

生成業務人員的球員卡，包含五大指標、趨勢分析和 AI 教練評語。
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from google.cloud import firestore

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None

from .stats_service import StatsService

logger = logging.getLogger(__name__)


class PlayerCardService:
    """
    銷售動能球員卡服務
    
    生成包含以下內容的球員卡：
    - 五大核心指標 (Activity, Quality, Opportunity, Execution, Risk)
    - 綜合戰鬥力 (SHI: Sales Health Index)
    - 週環比趨勢
    - AI 教練評語
    """
    
    # 指標權重
    WEIGHTS = {
        "activity": 0.25,
        "quality": 0.15,
        "opportunity": 0.25,
        "execution": 0.35,
    }
    
    # 指標滿分基準
    ACTIVITY_MAX_UPLOADS = 10  # 一週 10 件為滿分
    
    def __init__(
        self,
        db_client: firestore.Client,
        stats_service: StatsService,
        gemini_api_key: Optional[str] = None,
    ):
        self.db = db_client
        self.stats = stats_service
        self.collection_name = "player_cards"
        
        # 初始化 Gemini (用於教練評語)
        if GENAI_AVAILABLE and gemini_api_key:
            genai.configure(api_key=gemini_api_key)
            self.gemini_model = genai.GenerativeModel("gemini-2.0-flash-exp")
            logger.info("PlayerCardService: Gemini initialized for coach notes")
        else:
            self.gemini_model = None
            logger.warning("PlayerCardService: Gemini not available for coach notes")
    
    def generate_weekly_player_cards(self, week_of: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        為所有業務生成本週球員卡
        
        Args:
            week_of: ISO 週格式 (e.g., "2024-W52")，預設為本週
            
        Returns:
            List of generated player cards
        """
        if not week_of:
            week_of = self._get_current_week()
        
        # 取得週統計資料
        start_date, end_date = self._parse_week(week_of)
        weekly_stats = self.stats.get_weekly_stats(start_date, end_date)
        
        cards = []
        for rep_id, rep_data in weekly_stats.get("reps", {}).items():
            try:
                card = self.generate_player_card(
                    rep_id=rep_id,
                    rep_data=rep_data,
                    week_of=week_of,
                )
                cards.append(card)
            except Exception as e:
                logger.error(f"Failed to generate card for {rep_id}: {e}")
        
        logger.info(f"Generated {len(cards)} player cards for {week_of}")
        return cards
    
    def generate_player_card(
        self,
        rep_id: str,
        rep_data: Optional[Dict] = None,
        week_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        為單一業務生成球員卡
        
        Args:
            rep_id: 業務 Slack User ID
            rep_data: 業務統計資料 (可選，若未提供會從 Firestore 查詢)
            week_of: ISO 週格式
            
        Returns:
            Player card dictionary
        """
        if not week_of:
            week_of = self._get_current_week()
        
        # 如果沒有提供 rep_data，從 Firestore 查詢
        if not rep_data:
            start_date, end_date = self._parse_week(week_of)
            weekly_stats = self.stats.get_weekly_stats(start_date, end_date)
            rep_data = weekly_stats.get("reps", {}).get(rep_id, {})
        
        if not rep_data:
            logger.warning(f"No data found for rep {rep_id} in {week_of}")
            return {}
        
        # 取得案件詳細資料 (用於 Opportunity 計算)
        high_priority_ids = rep_data.get("high_priority_cases", [])
        risk_case_ids = rep_data.get("risk_cases", [])
        all_case_ids = list(set(high_priority_ids + risk_case_ids))
        cases = self._fetch_cases(all_case_ids) if all_case_ids else []
        
        # 計算五大指標
        indices = self._calculate_indices(rep_data, cases)
        
        # 計算趨勢
        trends = self._calculate_trends(rep_id, week_of, indices)
        
        # 生成亮點
        highlights = self._generate_highlights(rep_data, cases)
        
        # 生成 AI 教練評語
        coach_note = self._generate_coach_note(rep_data, indices, trends, highlights)
        
        # 組裝球員卡
        card = {
            "repId": rep_id,
            "repName": rep_data.get("name", "Unknown"),
            "weekOf": week_of,
            "generatedAt": datetime.utcnow(),
            "indices": indices,
            "trends": trends,
            "highlights": highlights,
            "stats": {
                "uploadCount": rep_data.get("demo_count", 0),  # TODO: 區分 upload vs demo
                "demoCount": rep_data.get("demo_count", 0),
                "avgProgressScore": self._safe_avg(
                    rep_data.get("total_score", 0),
                    rep_data.get("demo_count", 0)
                ),
                "closeNowCount": len(high_priority_ids),
                "riskCount": len(risk_case_ids),
            },
            "coachNote": coach_note,
        }
        
        # 儲存到 Firestore
        self._save_player_card(card)
        
        return card
    
    def _calculate_indices(self, rep_data: Dict, cases: List[Dict]) -> Dict[str, int]:
        """計算五大核心指標"""
        demo_count = rep_data.get("demo_count", 0)
        upload_count = rep_data.get("demo_count", 0)  # TODO: 區分 upload vs demo
        total_score = rep_data.get("total_score", 0)
        
        # 1. 產出指標 (Activity)
        activity = min(int(upload_count / self.ACTIVITY_MAX_UPLOADS * 100), 100)
        
        # 2. 品質指標 (Quality) - 目前用 demo_count / upload_count，暫時 100%
        quality = 100 if upload_count > 0 else 0  # TODO: 追蹤實際 upload_count
        
        # 3. 潛力指標 (Opportunity)
        opportunity = self._calculate_opportunity_index(cases)
        
        # 4. 執行指標 (Execution)
        execution = self._safe_avg(total_score, demo_count)
        
        # 5. 風險指標 (Risk) - 反向指標
        risk_count = len(rep_data.get("risk_cases", []))
        risk = max(0, 100 - (risk_count * 20))  # 每個風險案件扣 20 分
        
        # 綜合戰鬥力 (SHI)
        overall = int(
            activity * self.WEIGHTS["activity"] +
            quality * self.WEIGHTS["quality"] +
            opportunity * self.WEIGHTS["opportunity"] +
            execution * self.WEIGHTS["execution"]
        )
        
        return {
            "activity": activity,
            "quality": quality,
            "opportunity": opportunity,
            "execution": execution,
            "risk": risk,
            "overall": overall,
        }
    
    def _calculate_opportunity_index(self, cases: List[Dict]) -> int:
        """
        計算潛力指標
        
        基於案件的 urgency_level 和 decision_maker
        """
        if not cases:
            return 50  # 預設中等分數
        
        scores = []
        for case in cases:
            analysis = case.get("analysis", {})
            agent1 = analysis.get("agents", {}).get("agent1", {}).get("data", {})
            
            urgency = agent1.get("urgency_level", "").lower()
            decision_maker = agent1.get("decision_maker", "").lower()
            
            # 計算單一案件分數
            score = 50  # 基礎分
            
            if "高" in urgency or "high" in urgency:
                if "老闆" in decision_maker or "owner" in decision_maker:
                    score = 100
                elif "主管" in decision_maker or "manager" in decision_maker:
                    score = 80
                else:
                    score = 40  # 急件但員工接待
            elif "中" in urgency or "medium" in urgency:
                if "老闆" in decision_maker or "owner" in decision_maker:
                    score = 70
                else:
                    score = 50
            else:
                score = 30
            
            scores.append(score)
        
        return int(sum(scores) / len(scores)) if scores else 50
    
    def _calculate_trends(
        self,
        rep_id: str,
        current_week: str,
        current_indices: Dict[str, int],
    ) -> Dict[str, int]:
        """計算週環比趨勢"""
        # 取得上週球員卡
        previous_week = self._get_previous_week(current_week)
        previous_card = self._get_player_card(rep_id, previous_week)
        
        if not previous_card:
            return {
                "activity": 0,
                "quality": 0,
                "opportunity": 0,
                "execution": 0,
                "overall": 0,
            }
        
        previous_indices = previous_card.get("indices", {})
        trends = {}
        
        for key in ["activity", "quality", "opportunity", "execution", "overall"]:
            current = current_indices.get(key, 0)
            previous = previous_indices.get(key, 0)
            
            if previous > 0:
                change = int((current - previous) / previous * 100)
            else:
                change = 100 if current > 0 else 0
            
            trends[key] = change
        
        return trends
    
    def _generate_highlights(self, rep_data: Dict, cases: List[Dict]) -> Dict[str, List]:
        """生成案件亮點"""
        high_priority_ids = rep_data.get("high_priority_cases", [])
        risk_case_ids = rep_data.get("risk_cases", [])
        
        top_wins = []
        risk_cases = []
        
        for case in cases:
            case_id = case.get("caseId", "")
            store_name = case.get("storeName", "Unknown")
            analysis = case.get("analysis", {})
            agent3 = analysis.get("agents", {}).get("agent3", {}).get("data", {})
            score = agent3.get("progress_score", 0)
            strategy = agent3.get("recommended_strategy", "")
            
            if case_id in high_priority_ids:
                top_wins.append({
                    "caseId": case_id,
                    "storeName": store_name,
                    "score": score,
                    "strategy": strategy,
                })
            
            if case_id in risk_case_ids:
                agent1 = analysis.get("agents", {}).get("agent1", {}).get("data", {})
                risk_reason = self._get_risk_reason(score, agent1)
                risk_cases.append({
                    "caseId": case_id,
                    "storeName": store_name,
                    "reason": risk_reason,
                })
        
        # 按分數排序，取前 3
        top_wins.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return {
            "topWins": top_wins[:3],
            "riskCases": risk_cases[:3],
        }
    
    def _get_risk_reason(self, score: int, agent1_data: Dict) -> str:
        """取得風險原因"""
        reasons = []
        
        if score < 40:
            reasons.append(f"推進力低 ({score})")
        
        urgency = agent1_data.get("urgency_level", "")
        decision_maker = agent1_data.get("decision_maker", "")
        
        if ("高" in urgency or "High" in urgency) and ("員工" in decision_maker or "Staff" in decision_maker):
            reasons.append("急件但員工接待")
        
        return "、".join(reasons) if reasons else "系統判定風險"
    
    def _generate_coach_note(
        self,
        rep_data: Dict,
        indices: Dict,
        trends: Dict,
        highlights: Dict,
    ) -> str:
        """使用 Gemini 生成 AI 教練評語"""
        if not self.gemini_model:
            return self._generate_simple_coach_note(rep_data, indices, trends, highlights)
        
        try:
            prompt = f"""你是一位銷售教練，請根據以下業務數據，用繁體中文撰寫簡短的教練評語（50-80字）。

業務名稱：{rep_data.get('name', 'Unknown')}

本週指標：
- 產出: {indices.get('activity', 0)} (週環比: {trends.get('activity', 0):+d}%)
- 品質: {indices.get('quality', 0)}
- 潛力: {indices.get('opportunity', 0)}
- 執行: {indices.get('execution', 0)} (週環比: {trends.get('execution', 0):+d}%)
- 綜合: {indices.get('overall', 0)}

案件數：{rep_data.get('demo_count', 0)}
立即成交機會：{len(highlights.get('topWins', []))} 個
風險案件：{len(highlights.get('riskCases', []))} 個

請根據以上數據：
1. 先肯定做得好的地方
2. 給出具體的改善建議
3. 如果有立即成交機會，提醒優先處理

只需要輸出評語文字，不要加任何標題或格式。"""

            response = self.gemini_model.generate_content(prompt)
            return response.text.strip()
        
        except Exception as e:
            logger.error(f"Failed to generate coach note with Gemini: {e}")
            return self._generate_simple_coach_note(rep_data, indices, trends, highlights)
    
    def _generate_simple_coach_note(
        self,
        rep_data: Dict,
        indices: Dict,
        trends: Dict,
        highlights: Dict,
    ) -> str:
        """生成簡單的教練評語（無 Gemini 時使用）"""
        notes = []
        
        # 產出評語
        activity = indices.get("activity", 0)
        if activity >= 80:
            notes.append("本週揮棒次數極高")
        elif activity >= 50:
            notes.append("本週活動量適中")
        else:
            notes.append("本週活動量偏低，建議增加名單開發")
        
        # 執行力評語
        execution = indices.get("execution", 0)
        if execution >= 80:
            notes.append("執行力優異")
        elif execution < 50:
            notes.append("執行力需加強，建議進行銷售技巧訓練")
        
        # 立即成交提醒
        close_now = len(highlights.get("topWins", []))
        if close_now > 0:
            notes.append(f"目前有 {close_now} 個『立即成交』案源，請優先處理")
        
        # 風險提醒
        risk_count = len(highlights.get("riskCases", []))
        if risk_count > 0:
            notes.append(f"⚠️ {risk_count} 個風險案件需關注")
        
        return "。".join(notes) + "。"
    
    def _save_player_card(self, card: Dict) -> None:
        """儲存球員卡到 Firestore"""
        doc_id = f"{card['repId']}_{card['weekOf']}"
        self.db.collection(self.collection_name).document(doc_id).set(card)
        logger.info(f"Saved player card: {doc_id}")
    
    def _get_player_card(self, rep_id: str, week_of: str) -> Optional[Dict]:
        """取得球員卡"""
        doc_id = f"{rep_id}_{week_of}"
        doc = self.db.collection(self.collection_name).document(doc_id).get()
        return doc.to_dict() if doc.exists else None
    
    def _fetch_cases(self, case_ids: List[str]) -> List[Dict]:
        """批次取得案件"""
        if not case_ids:
            return []
        
        refs = [self.db.collection("cases").document(cid) for cid in case_ids[:20]]
        snapshots = self.db.get_all(refs)
        
        return [doc.to_dict() for doc in snapshots if doc.exists]
    
    def _get_current_week(self) -> str:
        """取得當前 ISO 週"""
        now = datetime.utcnow()
        return now.strftime("%G-W%V")
    
    def _get_previous_week(self, week_of: str) -> str:
        """取得上一週"""
        start_date, _ = self._parse_week(week_of)
        previous = start_date - timedelta(days=7)
        return previous.strftime("%G-W%V")
    
    def _parse_week(self, week_of: str) -> tuple:
        """解析 ISO 週格式為日期範圍"""
        # Parse "2024-W52" format
        year, week = week_of.split("-W")
        year = int(year)
        week = int(week)
        
        # 計算週一
        jan4 = datetime(year, 1, 4)
        start = jan4 - timedelta(days=jan4.weekday())
        start = start + timedelta(weeks=week - 1)
        
        # 週日
        end = start + timedelta(days=6)
        
        return start, end
    
    def _safe_avg(self, total: int, count: int) -> int:
        """安全計算平均值"""
        return int(total / count) if count > 0 else 0
