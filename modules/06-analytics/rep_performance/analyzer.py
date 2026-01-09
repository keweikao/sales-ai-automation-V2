"""
Rep performance analyzer.

Analyzes individual sales rep performance trends and comparisons.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from google.cloud import firestore

# 台灣時區 (UTC+8)
TW_TZ = timezone(timedelta(hours=8))


@dataclass
class RepPerformance:
    """Detailed performance metrics for a sales rep."""
    rep_id: str
    rep_name: str
    conversation_count: int
    analyzed_count: int
    avg_meddic_score: float
    score_trend: str  # 'up', 'down', 'stable'
    strengths: List[str]
    improvement_areas: List[str]
    comparison_to_team: float  # percentile 0-100
    meddic_breakdown: Dict[str, float]  # Individual MEDDIC element scores
    recent_scores: List[float]  # Last N MEDDIC scores for trend
    period_start: datetime
    period_end: datetime


class RepPerformanceAnalyzer:
    """Analyzes individual sales rep performance."""

    COLLECTION = "cases"

    def __init__(self, db: Optional[firestore.Client] = None):
        self.db = db or firestore.Client()

    async def analyze(
        self,
        rep_id: str,
        period_days: int = 30
    ) -> RepPerformance:
        """
        Analyze a sales rep's performance over a period.

        Args:
            rep_id: Sales rep ID or name
            period_days: Number of days to analyze (default 30)

        Returns:
            RepPerformance with detailed metrics
        """
        # Calculate date range
        end_date = datetime.now(TW_TZ)
        start_date = end_date - timedelta(days=period_days)

        # Query rep's cases
        rep_cases = self._query_rep_cases(rep_id, start_date, end_date)

        # Query all team cases for comparison
        team_cases = self._query_all_cases(start_date, end_date)

        # Calculate metrics
        conversation_count = len(rep_cases)
        analyzed_count = sum(1 for c in rep_cases if c.get("status") == "completed")

        # Extract MEDDIC scores
        meddic_scores = []
        meddic_breakdowns = []

        for case in rep_cases:
            score = self._extract_meddic_score(case)
            if score is not None:
                meddic_scores.append(score)

            breakdown = self._extract_meddic_breakdown(case)
            if breakdown:
                meddic_breakdowns.append(breakdown)

        avg_meddic = sum(meddic_scores) / len(meddic_scores) if meddic_scores else 0.0

        # Calculate trend
        score_trend = self._calculate_trend(meddic_scores)

        # Calculate team comparison (percentile)
        team_avg_scores = self._calculate_team_averages(team_cases)
        comparison = self._calculate_percentile(avg_meddic, team_avg_scores)

        # Aggregate MEDDIC breakdown
        avg_breakdown = self._aggregate_meddic_breakdown(meddic_breakdowns)

        # Extract strengths and improvement areas
        strengths, improvements = self._analyze_coaching_insights(rep_cases)

        # Get rep name from cases
        rep_name = rep_id
        if rep_cases:
            rep_name = (
                rep_cases[0].get("uploadedByName")
                or rep_cases[0].get("salesRepName")
                or rep_id
            )

        return RepPerformance(
            rep_id=rep_id,
            rep_name=rep_name,
            conversation_count=conversation_count,
            analyzed_count=analyzed_count,
            avg_meddic_score=avg_meddic,
            score_trend=score_trend,
            strengths=strengths,
            improvement_areas=improvements,
            comparison_to_team=comparison,
            meddic_breakdown=avg_breakdown,
            recent_scores=meddic_scores[-10:],  # Last 10 scores
            period_start=start_date,
            period_end=end_date,
        )

    def _query_rep_cases(
        self,
        rep_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Query cases for a specific rep."""
        from google.cloud.firestore_v1.base_query import FieldFilter

        start_utc = start_date.astimezone(timezone.utc)
        end_utc = end_date.astimezone(timezone.utc)

        # Try querying by different rep identifier fields
        cases = []

        # Query by uploadedBy (user ID)
        query = (
            self.db.collection(self.COLLECTION)
            .where(filter=FieldFilter("uploadedBy", "==", rep_id))
            .where(filter=FieldFilter("createdAt", ">=", start_utc))
            .where(filter=FieldFilter("createdAt", "<=", end_utc))
        )
        for doc in query.stream():
            data = doc.to_dict()
            data["caseId"] = doc.id
            cases.append(data)

        # If no results, try by name
        if not cases:
            query = (
                self.db.collection(self.COLLECTION)
                .where(filter=FieldFilter("uploadedByName", "==", rep_id))
                .where(filter=FieldFilter("createdAt", ">=", start_utc))
                .where(filter=FieldFilter("createdAt", "<=", end_utc))
            )
            for doc in query.stream():
                data = doc.to_dict()
                data["caseId"] = doc.id
                cases.append(data)

        # Also try salesRepName
        if not cases:
            query = (
                self.db.collection(self.COLLECTION)
                .where(filter=FieldFilter("salesRepName", "==", rep_id))
                .where(filter=FieldFilter("createdAt", ">=", start_utc))
                .where(filter=FieldFilter("createdAt", "<=", end_utc))
            )
            for doc in query.stream():
                data = doc.to_dict()
                data["caseId"] = doc.id
                cases.append(data)

        return cases

    def _query_all_cases(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Query all team cases for comparison."""
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

    def _extract_meddic_breakdown(self, case: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """Extract individual MEDDIC element scores."""
        analysis = case.get("analysis", {})
        if not analysis:
            return None

        meddic = analysis.get("meddic", {})
        if not isinstance(meddic, dict):
            return None

        breakdown = {}
        elements = ["metrics", "economicBuyer", "decisionCriteria",
                   "decisionProcess", "identifyPain", "champion"]

        for element in elements:
            # Try camelCase and snake_case
            score = meddic.get(f"{element}Score") or meddic.get(f"{element}_score")
            if score is not None:
                breakdown[element] = float(score)

        return breakdown if breakdown else None

    def _calculate_trend(self, scores: List[float]) -> str:
        """Calculate score trend from recent scores."""
        if len(scores) < 3:
            return "stable"

        recent = scores[-5:]  # Last 5 scores
        older = scores[-10:-5] if len(scores) >= 10 else scores[:-5]

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

    def _calculate_team_averages(self, cases: List[Dict[str, Any]]) -> List[float]:
        """Calculate average scores for each team member."""
        rep_scores: Dict[str, List[float]] = {}

        for case in cases:
            rep_name = (
                case.get("uploadedByName")
                or case.get("salesRepName")
                or "unknown"
            )
            score = self._extract_meddic_score(case)
            if score is not None:
                if rep_name not in rep_scores:
                    rep_scores[rep_name] = []
                rep_scores[rep_name].append(score)

        # Calculate average for each rep
        return [
            sum(scores) / len(scores)
            for scores in rep_scores.values()
            if scores
        ]

    def _calculate_percentile(self, score: float, all_scores: List[float]) -> float:
        """Calculate percentile rank of a score."""
        if not all_scores:
            return 50.0

        count_below = sum(1 for s in all_scores if s < score)
        percentile = (count_below / len(all_scores)) * 100
        return min(100, max(0, percentile))

    def _aggregate_meddic_breakdown(
        self,
        breakdowns: List[Dict[str, float]]
    ) -> Dict[str, float]:
        """Aggregate multiple MEDDIC breakdowns into averages."""
        if not breakdowns:
            return {
                "metrics": 0,
                "economicBuyer": 0,
                "decisionCriteria": 0,
                "decisionProcess": 0,
                "identifyPain": 0,
                "champion": 0,
            }

        elements = ["metrics", "economicBuyer", "decisionCriteria",
                   "decisionProcess", "identifyPain", "champion"]

        result = {}
        for element in elements:
            values = [b.get(element, 0) for b in breakdowns if element in b]
            result[element] = sum(values) / len(values) if values else 0

        return result

    def _analyze_coaching_insights(
        self,
        cases: List[Dict[str, Any]]
    ) -> tuple[List[str], List[str]]:
        """Extract strengths and improvement areas from coaching insights."""
        strengths = []
        improvements = []

        for case in cases:
            analysis = case.get("analysis", {})
            coaching = analysis.get("sellerCoaching", {}) or analysis.get("seller_coaching", {})
            if not coaching:
                continue

            insights = coaching.get("insights", [])
            for insight in insights:
                if isinstance(insight, dict):
                    category = insight.get("category", "")
                    content = insight.get("content", "")
                    if category == "strength" and content:
                        strengths.append(content)
                    elif category == "improvement" and content:
                        improvements.append(content)

        # Deduplicate and return top items
        unique_strengths = list(dict.fromkeys(strengths))
        unique_improvements = list(dict.fromkeys(improvements))

        return unique_strengths[:5], unique_improvements[:5]
