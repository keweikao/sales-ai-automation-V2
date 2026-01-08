"""
Rep performance leaderboard.

Generates rankings and team statistics for sales reps.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from google.cloud import firestore

# 台灣時區 (UTC+8)
TW_TZ = timezone(timedelta(hours=8))


@dataclass
class PerformerStats:
    """Statistics for a single performer in the leaderboard."""
    rank: int
    rep_id: str
    rep_name: str
    conversation_count: int
    analyzed_count: int
    avg_meddic_score: float
    score_trend: str  # 'up', 'down', 'stable'
    top_strengths: List[str] = field(default_factory=list)


@dataclass
class TeamStats:
    """Aggregated team statistics."""
    total_reps: int
    total_conversations: int
    total_analyzed: int
    avg_meddic_score: float
    top_performer: Optional[str]
    score_distribution: Dict[str, int]  # score ranges -> count
    period_start: datetime
    period_end: datetime


class RepLeaderboard:
    """Generates sales rep leaderboards and team statistics."""

    COLLECTION = "cases"

    def __init__(self, db: Optional[firestore.Client] = None):
        self.db = db or firestore.Client()

    async def get_top_performers(
        self,
        limit: int = 10,
        period_days: int = 7
    ) -> List[PerformerStats]:
        """
        Get top performing sales reps.

        Args:
            limit: Maximum number of performers to return
            period_days: Number of days to analyze (default 7)

        Returns:
            List of PerformerStats sorted by average MEDDIC score
        """
        # Calculate date range
        end_date = datetime.now(TW_TZ)
        start_date = end_date - timedelta(days=period_days)

        # Query all cases in period
        cases = self._query_cases(start_date, end_date)

        # Aggregate by rep
        rep_data = self._aggregate_by_rep(cases)

        # Sort by average MEDDIC score and assign ranks
        sorted_reps = sorted(
            rep_data.values(),
            key=lambda x: x["avg_score"],
            reverse=True
        )

        results = []
        for i, data in enumerate(sorted_reps[:limit]):
            results.append(PerformerStats(
                rank=i + 1,
                rep_id=data["rep_id"],
                rep_name=data["rep_name"],
                conversation_count=data["conversation_count"],
                analyzed_count=data["analyzed_count"],
                avg_meddic_score=data["avg_score"],
                score_trend=data["trend"],
                top_strengths=data["strengths"][:3],
            ))

        return results

    async def get_team_stats(self, period_days: int = 7) -> TeamStats:
        """
        Get aggregated team statistics.

        Args:
            period_days: Number of days to analyze

        Returns:
            TeamStats with aggregated metrics
        """
        # Calculate date range
        end_date = datetime.now(TW_TZ)
        start_date = end_date - timedelta(days=period_days)

        # Query all cases in period
        cases = self._query_cases(start_date, end_date)

        # Aggregate by rep
        rep_data = self._aggregate_by_rep(cases)

        # Calculate totals
        total_conversations = sum(d["conversation_count"] for d in rep_data.values())
        total_analyzed = sum(d["analyzed_count"] for d in rep_data.values())

        # Calculate overall average MEDDIC score
        all_scores = []
        for data in rep_data.values():
            all_scores.extend(data["scores"])

        avg_meddic = sum(all_scores) / len(all_scores) if all_scores else 0.0

        # Find top performer
        top_performer = None
        if rep_data:
            top_rep = max(rep_data.values(), key=lambda x: x["avg_score"])
            top_performer = top_rep["rep_name"]

        # Calculate score distribution
        distribution = self._calculate_score_distribution(all_scores)

        return TeamStats(
            total_reps=len(rep_data),
            total_conversations=total_conversations,
            total_analyzed=total_analyzed,
            avg_meddic_score=avg_meddic,
            top_performer=top_performer,
            score_distribution=distribution,
            period_start=start_date,
            period_end=end_date,
        )

    def _query_cases(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Query cases from Firestore within date range."""
        from google.cloud.firestore_v1.base_query import FieldFilter

        start_utc = start_date.astimezone(timezone.utc)
        end_utc = end_date.astimezone(timezone.utc)

        query = (
            self.db.collection(self.COLLECTION)
            .where(filter=FieldFilter("createdAt", ">=", start_utc))
            .where(filter=FieldFilter("createdAt", "<=", end_utc))
        )

        cases = []
        for doc in query.stream():
            data = doc.to_dict()
            data["caseId"] = doc.id
            cases.append(data)

        return cases

    def _aggregate_by_rep(self, cases: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Aggregate case data by sales rep."""
        rep_data: Dict[str, Dict[str, Any]] = {}

        for case in cases:
            rep_name = (
                case.get("uploadedByName")
                or case.get("salesRepName")
                or "未知業務"
            )
            rep_id = case.get("salesRepId") or case.get("uploadedBy") or rep_name

            if rep_name not in rep_data:
                rep_data[rep_name] = {
                    "rep_id": rep_id,
                    "rep_name": rep_name,
                    "conversation_count": 0,
                    "analyzed_count": 0,
                    "scores": [],
                    "avg_score": 0.0,
                    "trend": "stable",
                    "strengths": [],
                }

            rep_data[rep_name]["conversation_count"] += 1

            if case.get("status") == "completed":
                rep_data[rep_name]["analyzed_count"] += 1

            # Extract MEDDIC score
            score = self._extract_meddic_score(case)
            if score is not None:
                rep_data[rep_name]["scores"].append(score)

            # Extract strengths from coaching insights
            analysis = case.get("analysis", {})
            coaching = analysis.get("sellerCoaching", {}) or analysis.get("seller_coaching", {})
            if coaching:
                insights = coaching.get("insights", [])
                for insight in insights:
                    if isinstance(insight, dict):
                        if insight.get("category") == "strength":
                            content = insight.get("content", "")
                            if content and content not in rep_data[rep_name]["strengths"]:
                                rep_data[rep_name]["strengths"].append(content)

        # Calculate averages and trends
        for data in rep_data.values():
            if data["scores"]:
                data["avg_score"] = sum(data["scores"]) / len(data["scores"])
                data["trend"] = self._calculate_trend(data["scores"])

        return rep_data

    def _extract_meddic_score(self, case: Dict[str, Any]) -> Optional[float]:
        """Extract MEDDIC score from case."""
        analysis = case.get("analysis", {})
        if not analysis:
            return None

        meddic = analysis.get("meddic", {})
        if isinstance(meddic, dict):
            score = meddic.get("total_score") or meddic.get("totalScore")
            if score is not None:
                return float(score)

        score = analysis.get("meddicScore") or analysis.get("meddic_score")
        if score is not None:
            return float(score)

        return None

    def _calculate_trend(self, scores: List[float]) -> str:
        """Calculate score trend from recent scores."""
        if len(scores) < 3:
            return "stable"

        recent = scores[-3:]
        older = scores[:-3] if len(scores) > 3 else []

        if not older:
            return "stable"

        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)

        diff = recent_avg - older_avg
        if diff > 5:
            return "up"
        elif diff < -5:
            return "down"
        return "stable"

    def _calculate_score_distribution(self, scores: List[float]) -> Dict[str, int]:
        """Calculate score distribution by ranges."""
        distribution = {
            "0-30": 0,
            "31-50": 0,
            "51-70": 0,
            "71-85": 0,
            "86-100": 0,
        }

        for score in scores:
            if score <= 30:
                distribution["0-30"] += 1
            elif score <= 50:
                distribution["31-50"] += 1
            elif score <= 70:
                distribution["51-70"] += 1
            elif score <= 85:
                distribution["71-85"] += 1
            else:
                distribution["86-100"] += 1

        return distribution
