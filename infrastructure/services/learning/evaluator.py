"""
Agent Evaluator - Measures agent performance against outcomes.

Provides metrics that enable data-driven improvements to agents.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from statistics import mean, stdev
import math

from core.schemas.outcome import (
    DealOutcome,
    DealStatus,
    AgentMetrics,
    SystemMetrics,
    LearningSignal,
)

logger = logging.getLogger(__name__)


@dataclass
class EvaluationReport:
    """Results of an evaluation cycle."""
    period: str
    period_start: datetime
    period_end: datetime

    # Overall metrics
    total_cases: int
    cases_with_outcomes: int

    # Prediction accuracy
    meddic_correlation: float  # Correlation between MEDDIC score and win rate
    qualification_accuracy: float  # % of correct qualified/disqualified predictions
    close_rate_by_score: Dict[str, float]  # Win rate by score bucket

    # Coaching effectiveness
    suggestion_acceptance_rate: float
    accepted_suggestion_win_rate: float
    ignored_suggestion_win_rate: float

    # Quality metrics
    summary_edit_rate: float
    average_edit_distance: float

    # Improvement opportunities
    improvement_areas: List[str]
    recommended_actions: List[str]

    @property
    def summary(self) -> str:
        """Generate human-readable summary."""
        return f"""
Evaluation Report: {self.period}
================================
Cases Analyzed: {self.total_cases} ({self.cases_with_outcomes} with outcomes)

Prediction Accuracy:
- MEDDIC-Win Correlation: {self.meddic_correlation:.2f}
- Qualification Accuracy: {self.qualification_accuracy:.1%}

Coaching Effectiveness:
- Suggestion Acceptance: {self.suggestion_acceptance_rate:.1%}
- Win Rate (Accepted): {self.accepted_suggestion_win_rate:.1%}
- Win Rate (Ignored): {self.ignored_suggestion_win_rate:.1%}

Quality:
- Summary Edit Rate: {self.summary_edit_rate:.1%}
- Avg Edit Distance: {self.average_edit_distance:.2f}

Top Improvement Areas:
{chr(10).join(f'- {area}' for area in self.improvement_areas[:3])}
"""


class AgentEvaluator:
    """
    Evaluates agent performance using real outcomes.

    This is the "mirror" that shows agents how well they're doing
    and where they need to improve.
    """

    def __init__(
        self,
        firestore_client,
        feedback_collector=None,
    ):
        self.firestore = firestore_client
        self.feedback_collector = feedback_collector

    # =========================================================================
    # Weekly Evaluation
    # =========================================================================

    async def evaluate_weekly(self) -> EvaluationReport:
        """
        Run weekly evaluation of all agents.

        This should be scheduled to run every week.
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)

        # Gather data
        outcomes = await self._get_outcomes(start_date, end_date)
        feedback = await self._get_feedback(start_date, end_date)
        cases = await self._get_cases(start_date, end_date)

        # Calculate metrics
        prediction_metrics = self._evaluate_predictions(outcomes)
        coaching_metrics = self._evaluate_coaching(feedback, outcomes)
        quality_metrics = self._evaluate_quality(feedback)

        # Identify improvement areas
        improvement_areas = self._identify_improvement_areas(
            prediction_metrics, coaching_metrics, quality_metrics
        )

        # Generate recommendations
        recommended_actions = self._generate_recommendations(improvement_areas)

        report = EvaluationReport(
            period="weekly",
            period_start=start_date,
            period_end=end_date,
            total_cases=len(cases),
            cases_with_outcomes=len(outcomes),
            meddic_correlation=prediction_metrics.get("meddic_correlation", 0.0),
            qualification_accuracy=prediction_metrics.get("qualification_accuracy", 0.0),
            close_rate_by_score=prediction_metrics.get("close_rate_by_score", {}),
            suggestion_acceptance_rate=coaching_metrics.get("acceptance_rate", 0.0),
            accepted_suggestion_win_rate=coaching_metrics.get("accepted_win_rate", 0.0),
            ignored_suggestion_win_rate=coaching_metrics.get("ignored_win_rate", 0.0),
            summary_edit_rate=quality_metrics.get("edit_rate", 0.0),
            average_edit_distance=quality_metrics.get("avg_edit_distance", 0.0),
            improvement_areas=improvement_areas,
            recommended_actions=recommended_actions,
        )

        # Store report
        await self._store_report(report)

        # Create learning signals for significant findings
        await self._create_signals_from_report(report)

        return report

    async def _get_outcomes(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[DealOutcome]:
        """Get outcomes in date range."""
        docs = (
            self.firestore.collection("outcomes")
            .where("recorded_at", ">=", start_date)
            .where("recorded_at", "<=", end_date)
            .stream()
        )
        return [DealOutcome(**doc.to_dict()) for doc in docs]

    async def _get_feedback(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Get feedback in date range."""
        docs = (
            self.firestore.collection("feedback")
            .where("timestamp", ">=", start_date)
            .where("timestamp", "<=", end_date)
            .stream()
        )
        return [doc.to_dict() for doc in docs]

    async def _get_cases(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Get cases in date range."""
        docs = (
            self.firestore.collection("cases")
            .where("completedAt", ">=", start_date)
            .where("completedAt", "<=", end_date)
            .stream()
        )
        return [doc.to_dict() for doc in docs]

    # =========================================================================
    # Prediction Evaluation
    # =========================================================================

    def _evaluate_predictions(self, outcomes: List[DealOutcome]) -> Dict[str, Any]:
        """Evaluate prediction accuracy."""
        if not outcomes:
            return {
                "meddic_correlation": 0.0,
                "qualification_accuracy": 0.0,
                "close_rate_by_score": {},
            }

        # Separate by outcome
        won = [o for o in outcomes if o.actual_outcome == DealStatus.CLOSED_WON]
        lost = [o for o in outcomes if o.actual_outcome == DealStatus.CLOSED_LOST]

        # Calculate MEDDIC-Win correlation
        if won and lost:
            avg_win_score = mean(o.predicted_meddic_score for o in won)
            avg_loss_score = mean(o.predicted_meddic_score for o in lost)
            # Simple correlation: if wins have higher scores, positive correlation
            score_diff = avg_win_score - avg_loss_score
            meddic_correlation = min(1.0, max(-1.0, score_diff / 50.0))
        else:
            meddic_correlation = 0.0

        # Calculate qualification accuracy
        correct_quals = sum(
            1 for o in outcomes
            if self._qualification_was_correct(o)
        )
        qualification_accuracy = correct_quals / len(outcomes) if outcomes else 0.0

        # Calculate close rate by score bucket
        close_rate_by_score = self._calculate_close_rate_by_score(outcomes)

        return {
            "meddic_correlation": meddic_correlation,
            "qualification_accuracy": qualification_accuracy,
            "close_rate_by_score": close_rate_by_score,
            "avg_win_score": mean(o.predicted_meddic_score for o in won) if won else 0,
            "avg_loss_score": mean(o.predicted_meddic_score for o in lost) if lost else 0,
        }

    def _qualification_was_correct(self, outcome: DealOutcome) -> bool:
        """Check if qualification prediction was correct."""
        if outcome.actual_outcome == DealStatus.CLOSED_WON:
            return outcome.predicted_qualification == "qualified"
        elif outcome.actual_outcome == DealStatus.CLOSED_LOST:
            return outcome.predicted_qualification in ["nurture", "disqualified"]
        return True  # Ongoing deals are considered correct

    def _calculate_close_rate_by_score(
        self,
        outcomes: List[DealOutcome]
    ) -> Dict[str, float]:
        """Calculate win rate for each score bucket."""
        buckets = {
            "0-20": [],
            "21-40": [],
            "41-60": [],
            "61-80": [],
            "81-100": [],
        }

        for o in outcomes:
            score = o.predicted_meddic_score
            if score <= 20:
                buckets["0-20"].append(o)
            elif score <= 40:
                buckets["21-40"].append(o)
            elif score <= 60:
                buckets["41-60"].append(o)
            elif score <= 80:
                buckets["61-80"].append(o)
            else:
                buckets["81-100"].append(o)

        result = {}
        for bucket, cases in buckets.items():
            if cases:
                wins = sum(1 for c in cases if c.actual_outcome == DealStatus.CLOSED_WON)
                result[bucket] = wins / len(cases)
            else:
                result[bucket] = 0.0

        return result

    # =========================================================================
    # Coaching Evaluation
    # =========================================================================

    def _evaluate_coaching(
        self,
        feedback: List[Dict],
        outcomes: List[DealOutcome]
    ) -> Dict[str, Any]:
        """Evaluate coaching effectiveness."""
        suggestion_feedback = [
            f for f in feedback
            if f.get("feedback_type") == "suggestion_response"
        ]

        if not suggestion_feedback:
            return {
                "acceptance_rate": 0.0,
                "accepted_win_rate": 0.0,
                "ignored_win_rate": 0.0,
            }

        # Acceptance rate
        accepted = [f for f in suggestion_feedback if f.get("response") == "accepted"]
        acceptance_rate = len(accepted) / len(suggestion_feedback)

        # Build outcome lookup
        outcome_map = {o.case_id: o for o in outcomes}

        # Win rate for accepted suggestions
        accepted_cases = [f.get("case_id") for f in accepted]
        accepted_with_outcome = [
            outcome_map[cid] for cid in accepted_cases
            if cid in outcome_map and outcome_map[cid].actual_outcome in [
                DealStatus.CLOSED_WON, DealStatus.CLOSED_LOST
            ]
        ]
        if accepted_with_outcome:
            accepted_wins = sum(
                1 for o in accepted_with_outcome
                if o.actual_outcome == DealStatus.CLOSED_WON
            )
            accepted_win_rate = accepted_wins / len(accepted_with_outcome)
        else:
            accepted_win_rate = 0.0

        # Win rate for ignored suggestions
        ignored = [f for f in suggestion_feedback if f.get("response") in ["rejected", "ignored"]]
        ignored_cases = [f.get("case_id") for f in ignored]
        ignored_with_outcome = [
            outcome_map[cid] for cid in ignored_cases
            if cid in outcome_map and outcome_map[cid].actual_outcome in [
                DealStatus.CLOSED_WON, DealStatus.CLOSED_LOST
            ]
        ]
        if ignored_with_outcome:
            ignored_wins = sum(
                1 for o in ignored_with_outcome
                if o.actual_outcome == DealStatus.CLOSED_WON
            )
            ignored_win_rate = ignored_wins / len(ignored_with_outcome)
        else:
            ignored_win_rate = 0.0

        return {
            "acceptance_rate": acceptance_rate,
            "accepted_win_rate": accepted_win_rate,
            "ignored_win_rate": ignored_win_rate,
            "total_suggestions": len(suggestion_feedback),
        }

    # =========================================================================
    # Quality Evaluation
    # =========================================================================

    def _evaluate_quality(self, feedback: List[Dict]) -> Dict[str, Any]:
        """Evaluate output quality based on edit patterns."""
        edit_feedback = [
            f for f in feedback
            if f.get("feedback_type") == "summary_edit"
        ]

        if not edit_feedback:
            return {
                "edit_rate": 0.0,
                "avg_edit_distance": 0.0,
            }

        total_cases = len(set(f.get("case_id") for f in feedback))
        cases_with_edits = len(set(f.get("case_id") for f in edit_feedback))

        edit_rate = cases_with_edits / total_cases if total_cases else 0.0
        avg_edit_distance = mean(f.get("edit_distance", 0) for f in edit_feedback)

        return {
            "edit_rate": edit_rate,
            "avg_edit_distance": avg_edit_distance,
            "total_edits": len(edit_feedback),
        }

    # =========================================================================
    # Improvement Identification
    # =========================================================================

    def _identify_improvement_areas(
        self,
        prediction_metrics: Dict,
        coaching_metrics: Dict,
        quality_metrics: Dict
    ) -> List[str]:
        """Identify areas needing improvement."""
        areas = []

        # Check prediction accuracy
        if prediction_metrics.get("meddic_correlation", 0) < 0.5:
            areas.append("MEDDIC scoring not predictive of outcomes")

        if prediction_metrics.get("qualification_accuracy", 0) < 0.7:
            areas.append("Qualification predictions frequently incorrect")

        # Check score calibration
        close_rates = prediction_metrics.get("close_rate_by_score", {})
        if close_rates.get("81-100", 0) < 0.7:
            areas.append("High MEDDIC scores not resulting in wins")
        if close_rates.get("0-20", 0) > 0.3:
            areas.append("Low MEDDIC scores still winning - scoring too conservative")

        # Check coaching effectiveness
        if coaching_metrics.get("acceptance_rate", 0) < 0.5:
            areas.append("Coaching suggestions frequently rejected")

        accepted_wr = coaching_metrics.get("accepted_win_rate", 0)
        ignored_wr = coaching_metrics.get("ignored_win_rate", 0)
        if accepted_wr < ignored_wr:
            areas.append("Following suggestions not improving outcomes")

        # Check quality
        if quality_metrics.get("edit_rate", 0) > 0.3:
            areas.append("Summaries frequently require editing")

        if quality_metrics.get("avg_edit_distance", 0) > 0.3:
            areas.append("Summary edits are substantial")

        return areas

    def _generate_recommendations(
        self,
        improvement_areas: List[str]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        for area in improvement_areas:
            if "MEDDIC scoring not predictive" in area:
                recommendations.append(
                    "Review MEDDIC criteria weights - analyze which components "
                    "best correlate with actual outcomes"
                )

            if "Qualification predictions" in area:
                recommendations.append(
                    "Adjust qualification thresholds - current thresholds "
                    "may be too aggressive or too conservative"
                )

            if "High MEDDIC scores not resulting" in area:
                recommendations.append(
                    "Investigate high-score losses - may be missing key "
                    "qualification factors like timing or competition"
                )

            if "suggestions frequently rejected" in area:
                recommendations.append(
                    "Analyze rejection reasons - suggestions may not be "
                    "actionable or may conflict with rep knowledge"
                )

            if "Following suggestions not improving" in area:
                recommendations.append(
                    "Review suggestion quality - current coaching advice "
                    "may not be effective; consider A/B testing alternatives"
                )

            if "Summaries frequently require editing" in area:
                recommendations.append(
                    "Analyze edit patterns - identify common corrections "
                    "to improve summary generation prompts"
                )

        return recommendations

    # =========================================================================
    # Storage and Signals
    # =========================================================================

    async def _store_report(self, report: EvaluationReport):
        """Store evaluation report."""
        doc_id = f"eval_{report.period_start.strftime('%Y%m%d')}"
        doc_ref = self.firestore.collection("evaluation_reports").document(doc_id)
        await doc_ref.set({
            "period": report.period,
            "period_start": report.period_start,
            "period_end": report.period_end,
            "total_cases": report.total_cases,
            "cases_with_outcomes": report.cases_with_outcomes,
            "meddic_correlation": report.meddic_correlation,
            "qualification_accuracy": report.qualification_accuracy,
            "suggestion_acceptance_rate": report.suggestion_acceptance_rate,
            "summary_edit_rate": report.summary_edit_rate,
            "improvement_areas": report.improvement_areas,
            "recommended_actions": report.recommended_actions,
            "created_at": datetime.utcnow(),
        })

    async def _create_signals_from_report(self, report: EvaluationReport):
        """Create learning signals for significant findings."""
        import uuid

        for area in report.improvement_areas:
            signal = LearningSignal(
                signal_id=f"sig_{uuid.uuid4().hex[:12]}",
                signal_type="negative",
                source_feedback_ids=[],
                agent_id=self._area_to_agent(area),
                insight=area,
                action_recommended=self._get_action_for_area(area, report.recommended_actions),
                confidence=0.8,  # Weekly evaluation has high confidence
                priority="medium",
                sample_size=report.cases_with_outcomes,
                status="pending_review",
            )

            await self.firestore.collection("learning_signals").add(
                signal.model_dump()
            )

    def _area_to_agent(self, area: str) -> str:
        """Map improvement area to responsible agent."""
        if "MEDDIC" in area or "scoring" in area:
            return "agent2"  # Buyer agent
        if "Qualification" in area:
            return "agent2"
        if "suggestion" in area or "coaching" in area:
            return "agent3"  # Seller/coach agent
        if "Summary" in area or "edit" in area:
            return "agent4"  # Summary agent
        return "orchestrator"

    def _get_action_for_area(
        self,
        area: str,
        recommendations: List[str]
    ) -> str:
        """Get action for improvement area."""
        for rec in recommendations:
            if any(word in rec.lower() for word in area.lower().split()[:3]):
                return rec
        return "Review and investigate this issue"
