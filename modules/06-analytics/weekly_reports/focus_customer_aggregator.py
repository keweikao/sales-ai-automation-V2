"""
Focus Customer aggregator for weekly reports.

Extracts high-value potential customers from analyzed cases
based on engagement scores and generates manager-focused insights.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from .focus_customer_models import FocusCustomer, ManagerQuestion
except ImportError:
    # Fallback for dynamic module loading (e.g., test scripts)
    from focus_customer_models import FocusCustomer, ManagerQuestion


class FocusCustomerAggregator:
    """聚合關注客戶資料。"""

    def get_focus_customers(
        self,
        cases: List[Dict[str, Any]],
        top_n: int = 10,
        min_score: Optional[int] = None,
    ) -> List[FocusCustomer]:
        """
        從 cases 中提取關注客戶。

        Args:
            cases: MTD 期間的 cases
            top_n: 顯示前 N 名（預設 10）
            min_score: 最低分數門檻（可選）

        Returns:
            List of FocusCustomer sorted by engagement score
        """
        # 篩選有分析結果的 cases (status == completed)
        analyzed_cases = [
            c for c in cases
            if c.get("analysis") and c.get("analysis", {}).get("status") == "completed"
        ]

        # 按綜合分數排序
        sorted_cases = sorted(
            analyzed_cases,
            key=lambda x: self._calculate_score(x),
            reverse=True,
        )

        # 應用最低分數篩選條件
        if min_score is not None:
            sorted_cases = [
                c for c in sorted_cases if self._calculate_score(c) >= min_score
            ]

        # 取前 N 名
        top_cases = sorted_cases[:top_n]

        # 轉換為 FocusCustomer
        return [self._build_focus_customer(c) for c in top_cases]

    def _get_agent_data(self, analysis: Dict[str, Any], agent_name: str) -> Dict[str, Any]:
        """取得特定 agent 的 data。"""
        return analysis.get("agents", {}).get(agent_name, {}).get("data", {})

    def _get_trust_score(self, agent2_data: Dict[str, Any]) -> int:
        """取得信任分數，支援新舊格式。"""
        # 新格式 (Jan 2026+): trust_score (1-5 scale)
        if "trust_score" in agent2_data:
            trust_val = agent2_data.get("trust_score", 0)
            # 確保是數字，處理字串或其他類型
            if isinstance(trust_val, (int, float)):
                return int(trust_val * 20)
            elif isinstance(trust_val, str):
                try:
                    return int(float(trust_val) * 20)
                except (ValueError, TypeError):
                    return 0
            return 0
        # 舊格式 (Nov 2025): trustLevel (0-100 scale)
        trust_level = agent2_data.get("trustLevel", 0)
        if isinstance(trust_level, (int, float)):
            return int(trust_level)
        return 0

    def _get_engagement_level(self, agent2_data: Dict[str, Any]) -> int:
        """取得互動程度，支援新舊格式。"""
        # 舊格式: engagementLevel (0-100)
        if "engagementLevel" in agent2_data:
            return agent2_data.get("engagementLevel", 0) or 0
        # 新格式: 根據 hesitations 和 identifiedNeeds 推算
        hesitations = agent2_data.get("hesitations", []) or []
        needs = agent2_data.get("identifiedNeeds", []) or []
        # 有需求表示有互動，猶豫多表示互動深入
        engagement = min(len(needs) * 15 + len(hesitations) * 10, 100)
        return engagement

    def _get_urgency(self, analysis: Dict[str, Any]) -> str:
        """取得急迫程度，支援新舊格式。"""
        # 舊格式: agent3.data.decisionTimeline.urgency
        agent3_data = self._get_agent_data(analysis, "agent3")
        decision_timeline = agent3_data.get("decisionTimeline", {}) or {}
        urgency = decision_timeline.get("urgency", "")
        if urgency:
            return urgency.lower()

        # 新格式: agent6.data.timeline.urgency
        agent6_data = self._get_agent_data(analysis, "agent6")
        timeline = agent6_data.get("timeline", {}) or {}
        urgency = timeline.get("urgency", "")
        if urgency:
            return urgency.lower()

        return ""

    def _get_buying_signals(self, agent2_data: Dict[str, Any]) -> List[Any]:
        """取得購買訊號，支援新舊格式。"""
        # 舊格式: buyingSignals
        if "buyingSignals" in agent2_data:
            return agent2_data.get("buyingSignals", []) or []
        # 新格式: identifiedNeeds 作為訊號
        return agent2_data.get("identifiedNeeds", []) or []

    def _check_decision_maker_confirmed(self, analysis: Dict[str, Any]) -> bool:
        """檢查是否確認決策者，支援新舊格式。"""
        # 舊格式: agent1.data.participants
        agent1_data = self._get_agent_data(analysis, "agent1")
        participants = agent1_data.get("participants", []) or []
        if any(
            p.get("role", "").lower() in ("decision_maker", "owner", "老闆", "決策者")
            for p in participants if isinstance(p, dict)
        ):
            return True

        # 新格式: agent6.data.decision_makers
        agent6_data = self._get_agent_data(analysis, "agent6")
        decision_makers = agent6_data.get("decision_makers", []) or []
        if any(
            dm.get("role", "").lower() in ("owner", "decision_maker", "老闆", "決策者")
            or dm.get("influence", "").lower() == "high"
            for dm in decision_makers if isinstance(dm, dict)
        ):
            return True

        return False

    def _calculate_score(self, case: Dict[str, Any]) -> int:
        """
        計算綜合分數 (0-100)。

        基於：
        - trust score (0-100)
        - engagement level (0-100)
        - urgency (high=30, medium=15, low=0)
        - buying signals 數量
        """
        analysis = case.get("analysis", {})
        agent2_data = self._get_agent_data(analysis, "agent2")

        # 使用相容方法取得數據
        trust_level = self._get_trust_score(agent2_data)
        engagement_level = self._get_engagement_level(agent2_data)
        buying_signals = self._get_buying_signals(agent2_data)
        urgency = self._get_urgency(analysis)

        # 計算分數
        urgency_score = 30 if urgency == "high" else (15 if urgency == "medium" else 0)
        signal_score = min(len(buying_signals) * 5, 20)  # 最多 20 分

        # 綜合分數 (加權平均)
        score = int(
            trust_level * 0.3 +
            engagement_level * 0.3 +
            urgency_score +
            signal_score
        )

        return min(score, 100)

    def _build_focus_customer(self, case: Dict[str, Any]) -> FocusCustomer:
        """建構關注客戶物件。"""
        analysis = case.get("analysis", {})

        # 取得各 agent 數據
        agent2_data = self._get_agent_data(analysis, "agent2")
        _ = self._get_agent_data(analysis, "agent6")  # Reserved for future use
        agent7_data = self._get_agent_data(analysis, "agent7")

        # 處理 created_at
        created_at = case.get("createdAt")
        if created_at is None:
            created_at = datetime.now(timezone.utc)
        elif hasattr(created_at, "seconds"):
            # Firestore Timestamp
            created_at = datetime.fromtimestamp(created_at.seconds, tz=timezone.utc)
        elif not hasattr(created_at, "tzinfo") or created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        # 取得急迫程度 (支援新舊格式)
        urgency = self._get_urgency(analysis)
        urgency_level = "高" if urgency == "high" else ("中" if urgency == "medium" else "低")

        # 取得摘要
        executive_summary = (
            analysis.get("customerSummary") or
            agent7_data.get("customerSummary") or
            agent2_data.get("meddic_pain", "") or  # 新格式備選
            ""
        )

        # 決策者確認 (支援新舊格式)
        decision_maker_confirmed = self._check_decision_maker_confirmed(analysis)

        return FocusCustomer(
            case_id=case.get("caseId", ""),
            customer_id=case.get("customerId", ""),
            customer_name=case.get("customerName", "未命名"),
            rep_name=case.get("uploadedByName") or case.get("salesRepName") or "未知業務",
            created_at=created_at,
            meddic_score=self._calculate_score(case),
            qualification_status=self._get_qualification_status(case),
            executive_summary=executive_summary,
            urgency_level=urgency_level,
            decision_maker_confirmed=decision_maker_confirmed,
            manager_questions=self._generate_manager_questions(case),
            next_steps=self._extract_next_steps(case),
            risk_alerts=self._extract_risk_alerts(case),
        )

    def _get_qualification_status(self, case: Dict[str, Any]) -> str:
        """判斷資格狀態。"""
        score = self._calculate_score(case)
        if score >= 70:
            return "qualified"
        elif score >= 40:
            return "partially_qualified"
        else:
            return "unqualified"

    def _generate_manager_questions(
        self, case: Dict[str, Any]
    ) -> List[ManagerQuestion]:
        """根據分析結果生成主管詢問問題。"""
        questions: List[ManagerQuestion] = []
        analysis = case.get("analysis", {})

        # 取得各 agent 數據
        agent2_data = self._get_agent_data(analysis, "agent2")
        agent4_data = self._get_agent_data(analysis, "agent4")
        agent6_data = self._get_agent_data(analysis, "agent6")

        # 決策者相關問題 (新格式優先)
        if not self._check_decision_maker_confirmed(analysis):
            questions.append(
                ManagerQuestion(
                    question="這個案子的決策者是誰？有直接接觸到嗎？",
                    context="分析顯示尚未確認決策者",
                )
            )

        # 急迫程度相關問題
        urgency = self._get_urgency(analysis)
        if urgency == "high":
            # 嘗試取得決策日期 (舊格式 agent3 或新格式 agent6)
            agent3_data = self._get_agent_data(analysis, "agent3")
            decision_timeline = agent3_data.get("decisionTimeline", {}) or {}
            expected_date = decision_timeline.get("expectedDecisionDate", "")
            if not expected_date:
                timeline = agent6_data.get("timeline", {}) or {}
                expected_date = timeline.get("decision_date", "")

            if expected_date:
                questions.append(
                    ManagerQuestion(
                        question=f"客戶預計 {expected_date} 做決定，我們的跟進計畫是什麼？",
                        context=f"急迫程度高，預期決策日期：{expected_date}",
                    )
                )
            else:
                questions.append(
                    ManagerQuestion(
                        question="客戶急迫程度高，具體的決策時間點確認了嗎？",
                        context="急迫程度高但未確認決策日期",
                    )
                )

        # 預算相關問題 (支援新舊格式)
        agent3_data = self._get_agent_data(analysis, "agent3")
        budget = agent3_data.get("budget", {}) or agent6_data.get("budget", {}) or {}
        budget_mentioned = budget.get("mentioned", False)
        budget_range = budget.get("range") or budget.get("value", "")

        if not budget_mentioned:
            questions.append(
                ManagerQuestion(
                    question="客戶的預算確認了嗎？有討論過價格嗎？",
                    context="對話中未提及預算",
                )
            )
        elif budget_range:
            questions.append(
                ManagerQuestion(
                    question=f"客戶預算約 {budget_range}，這個案子的利潤空間如何？",
                    context=f"客戶預算：{budget_range}",
                )
            )

        # 競爭對手問題
        competitors = agent4_data.get("competitors", []) or []
        if competitors:
            competitor_names = []
            for c in competitors[:2]:
                if isinstance(c, dict):
                    competitor_names.append(c.get("name", c.get("competitor", "")))
                elif isinstance(c, str):
                    competitor_names.append(c)
            if competitor_names:
                names_str = ", ".join(filter(None, competitor_names))
                if names_str:
                    questions.append(
                        ManagerQuestion(
                            question=f"客戶有在比較 {names_str}，我們的差異化優勢是什麼？",
                            context=f"競爭對手：{names_str}",
                        )
                    )

        # 信任度問題 (使用相容方法)
        trust_level = self._get_trust_score(agent2_data)
        if trust_level < 50:
            questions.append(
                ManagerQuestion(
                    question="這個客戶的信任度偏低，有什麼方法可以增加信任？",
                    context=f"信任度：{trust_level}/100",
                )
            )

        # 猶豫/異議問題 (新格式)
        hesitations = agent2_data.get("hesitations", []) or []
        if hesitations and len(hesitations) > 0:
            first_hesitation = hesitations[0]
            if isinstance(first_hesitation, dict):
                pain_point = first_hesitation.get("pain_point", "")
                if pain_point:
                    questions.append(
                        ManagerQuestion(
                            question=f"客戶對「{pain_point[:30]}」有疑慮，打算怎麼處理？",
                            context=f"客戶猶豫點：{pain_point[:50]}",
                        )
                    )

        # 互動程度問題 (使用相容方法)
        engagement_level = self._get_engagement_level(agent2_data)
        if engagement_level >= 80:
            questions.append(
                ManagerQuestion(
                    question="客戶互動積極，是否可以加速推進成交？",
                    context=f"互動程度：{engagement_level}/100",
                )
            )

        return questions[:3]  # 最多 3 個問題

    def _extract_next_steps(self, case: Dict[str, Any]) -> List[str]:
        """提取下一步行動建議。"""
        next_steps: List[str] = []
        analysis = case.get("analysis", {})

        # 取得 agent 數據
        agent2_data = self._get_agent_data(analysis, "agent2")
        agent3_data = self._get_agent_data(analysis, "agent3")
        agent6_data = self._get_agent_data(analysis, "agent6")

        # 從 agent6 next_steps 提取 (新格式優先)
        agent6_next_steps = agent6_data.get("next_steps", []) or []
        for step in agent6_next_steps[:2]:
            if isinstance(step, str) and step:
                next_steps.append(step)
            elif isinstance(step, dict):
                action = step.get("action", step.get("step", ""))
                if action:
                    next_steps.append(action)

        # 從決策時程提取行動 (舊格式)
        decision_timeline = agent3_data.get("decisionTimeline", {}) or {}
        drivers = decision_timeline.get("drivers", []) or []
        for driver in drivers[:2]:
            if driver and len(next_steps) < 3:
                next_steps.append(f"跟進：{driver}")

        # 從需求提取行動 (新格式: identifiedNeeds, 舊格式: explicitNeeds)
        needs = agent2_data.get("identifiedNeeds", []) or agent3_data.get("explicitNeeds", []) or []
        for need in needs[:1]:
            if len(next_steps) >= 3:
                break
            if isinstance(need, str) and need:
                next_steps.append(f"滿足需求：{need[:40]}")
            elif isinstance(need, dict):
                need_text = need.get("need", need.get("description", ""))
                if need_text:
                    next_steps.append(f"滿足需求：{need_text[:40]}")

        # 從買方信號提取行動 (舊格式)
        buying_signals = agent2_data.get("buyingSignals", []) or []
        for signal in buying_signals[:2]:
            if len(next_steps) >= 3:
                break
            if isinstance(signal, dict):
                signal_text = signal.get("signal", "")
                if signal_text and signal.get("strength") == "strong":
                    next_steps.append(f"強化：{signal_text}")

        return next_steps[:3]  # 最多 3 個

    def _extract_risk_alerts(self, case: Dict[str, Any]) -> List[str]:
        """提取風險提醒。"""
        risks: List[str] = []
        analysis = case.get("analysis", {})

        # 取得 agent 數據
        agent2_data = self._get_agent_data(analysis, "agent2")
        agent3_data = self._get_agent_data(analysis, "agent3")
        agent6_data = self._get_agent_data(analysis, "agent6")

        # 從猶豫點提取風險 (新格式)
        hesitations = agent2_data.get("hesitations", []) or []
        for hesitation in hesitations[:2]:
            if isinstance(hesitation, dict):
                intensity = hesitation.get("intensity", "").lower()
                pain_point = hesitation.get("pain_point", "")
                if intensity in ("high", "強") and pain_point:
                    risks.append(f"客戶疑慮：{pain_point[:40]}")

        # 從轉換顧慮提取風險 (新格式)
        switch_concerns = agent2_data.get("switch_concerns", {}) or {}
        if switch_concerns.get("detected"):
            worry = switch_concerns.get("worry_about", "")
            complexity = switch_concerns.get("complexity", "")
            if worry:
                risks.append(f"轉換顧慮：{worry[:40]}")
            elif complexity in ("high", "高"):
                risks.append("轉換複雜度高，可能影響決策")

        # 從反對訊號提取風險 (舊格式)
        objection_signals = agent2_data.get("objectionSignals", []) or []
        for objection in objection_signals[:2]:
            if len(risks) >= 2:
                break
            if isinstance(objection, dict):
                obj_text = objection.get("objection", objection.get("signal", ""))
                if obj_text:
                    risks.append(f"客戶異議：{obj_text[:40]}")

        # 價格敏感度風險 (舊格式)
        price_sensitivity = agent3_data.get("priceSensitivity", {}) or {}
        sensitivity_level = price_sensitivity.get("level", "").lower()
        if sensitivity_level == "high" and len(risks) < 2:
            reason = price_sensitivity.get("sensitivityReason", "客戶對價格敏感")
            risks.append(f"價格風險：{reason[:40]}")

        # 從 pain_points 提取 (新格式 agent6)
        pain_points = agent6_data.get("pain_points", []) or []
        for pain in pain_points[:1]:
            if len(risks) >= 2:
                break
            if isinstance(pain, str) and pain:
                risks.append(f"痛點：{pain[:40]}")

        # 整體評估風險 (舊格式)
        overall = agent2_data.get("overall", "").lower()
        if overall == "negative" and len(risks) < 2:
            risks.append("整體評估偏負面，需注意客戶態度")

        # 信任度低風險
        trust_level = self._get_trust_score(agent2_data)
        if trust_level < 40 and len(risks) < 2:
            risks.append(f"信任度偏低 ({trust_level}/100)，需建立關係")

        return risks[:2]  # 最多 2 個風險提醒
