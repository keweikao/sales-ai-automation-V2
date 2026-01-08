"""
Focus Customer data models for weekly reports.

Models for representing high-value potential customers that managers
should focus on during weekly business meetings.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class ManagerQuestion:
    """主管可詢問的問題。"""

    question: str
    context: str  # 為什麼要問這個問題


@dataclass
class FocusCustomer:
    """需要關注的客戶。"""

    case_id: str
    customer_id: str
    customer_name: str
    rep_name: str
    created_at: datetime

    # MEDDIC 評分
    meddic_score: int  # 0-100
    qualification_status: str  # qualified/partially_qualified/unqualified

    # AI 分析摘要
    executive_summary: str
    urgency_level: str  # 高/中/低
    decision_maker_confirmed: bool

    # 建議行動
    manager_questions: List[ManagerQuestion] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    risk_alerts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "case_id": self.case_id,
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "rep_name": self.rep_name,
            "created_at": (
                self.created_at.isoformat()
                if isinstance(self.created_at, datetime)
                else self.created_at
            ),
            "meddic_score": self.meddic_score,
            "qualification_status": self.qualification_status,
            "executive_summary": self.executive_summary,
            "urgency_level": self.urgency_level,
            "decision_maker_confirmed": self.decision_maker_confirmed,
            "manager_questions": [
                {"question": q.question, "context": q.context}
                for q in self.manager_questions
            ],
            "next_steps": self.next_steps,
            "risk_alerts": self.risk_alerts,
        }
