"""
Feedback Collector - Captures all forms of user feedback for learning.

Collects explicit feedback (ratings), implicit feedback (edits, ignores),
and outcome feedback (deal results) to enable agent improvement.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from difflib import SequenceMatcher
import uuid

from core.schemas.outcome import (
    Feedback,
    ExplicitFeedback,
    SuggestionFeedback,
    SummaryEditFeedback,
    OutcomeFeedback,
    SuggestionResponse,
    FeedbackType,
    LearningSignal,
)

logger = logging.getLogger(__name__)


class FeedbackCollector:
    """
    Collects and processes feedback from multiple sources.

    Feedback is the fuel for learning - without it, agents stay static.
    """

    def __init__(self, firestore_client, pubsub_client=None):
        self.firestore = firestore_client
        self.pubsub = pubsub_client  # For async processing

    # =========================================================================
    # Explicit Feedback
    # =========================================================================

    async def record_rating(
        self,
        case_id: str,
        component: str,
        rating: int,
        comment: Optional[str],
        rated_by: str,
    ) -> ExplicitFeedback:
        """Record explicit rating from a user."""
        feedback = ExplicitFeedback(
            feedback_id=f"fb_{uuid.uuid4().hex[:12]}",
            case_id=case_id,
            feedback_type=FeedbackType.EXPLICIT_RATING,
            rating=rating,
            comment=comment,
            rated_by=rated_by,
            rated_component=component,
            source="web_ui",
        )

        await self._store_feedback(feedback)
        await self._emit_learning_signal(feedback)

        return feedback

    # =========================================================================
    # Suggestion Feedback
    # =========================================================================

    async def record_suggestion_response(
        self,
        case_id: str,
        suggestion_id: str,
        suggestion_text: str,
        response: SuggestionResponse,
        rep_id: str,
        rep_comment: Optional[str] = None,
        response_time_seconds: Optional[int] = None,
    ) -> SuggestionFeedback:
        """Record how a rep responded to a coaching suggestion."""
        feedback = SuggestionFeedback(
            feedback_id=f"fb_{uuid.uuid4().hex[:12]}",
            case_id=case_id,
            suggestion_id=suggestion_id,
            suggestion_text=suggestion_text,
            response=response,
            rep_id=rep_id,
            rep_comment=rep_comment,
            time_to_respond=response_time_seconds,
            source="slack",
        )

        await self._store_feedback(feedback)

        # Emit different signals based on response
        if response == SuggestionResponse.REJECTED:
            await self._analyze_rejection(feedback)
        elif response == SuggestionResponse.ACCEPTED:
            await self._record_acceptance(feedback)

        return feedback

    async def _analyze_rejection(self, feedback: SuggestionFeedback):
        """Analyze why a suggestion was rejected."""
        if not feedback.rep_comment:
            return

        # Categorize rejection reason
        rejection_categories = await self._categorize_rejection(feedback.rep_comment)

        # Store rejection analysis
        rejection_doc = {
            "feedback_id": feedback.feedback_id,
            "suggestion_id": feedback.suggestion_id,
            "suggestion_text": feedback.suggestion_text,
            "rejection_reason": feedback.rep_comment,
            "categories": rejection_categories,
            "timestamp": datetime.utcnow(),
        }

        await self.firestore.collection("suggestion_rejections").add(rejection_doc)

        # If we see a pattern, create a learning signal
        similar_rejections = await self._find_similar_rejections(feedback.suggestion_text)
        if len(similar_rejections) >= 3:
            await self._create_rejection_pattern_signal(feedback, similar_rejections)

    async def _categorize_rejection(self, comment: str) -> List[str]:
        """Categorize the rejection reason."""
        categories = []
        comment_lower = comment.lower()

        if any(word in comment_lower for word in ["不適用", "not applicable", "doesn't apply"]):
            categories.append("not_applicable")
        if any(word in comment_lower for word in ["已經", "already", "did that"]):
            categories.append("already_done")
        if any(word in comment_lower for word in ["客戶", "customer", "不可能"]):
            categories.append("customer_constraint")
        if any(word in comment_lower for word in ["時機", "timing", "太早", "太晚"]):
            categories.append("bad_timing")
        if any(word in comment_lower for word in ["不懂", "unclear", "什麼意思"]):
            categories.append("unclear_suggestion")

        return categories if categories else ["other"]

    async def _find_similar_rejections(self, suggestion_text: str) -> List[Dict]:
        """Find similar suggestions that were also rejected."""
        rejections = self.firestore.collection("suggestion_rejections").stream()

        similar = []
        for doc in rejections:
            data = doc.to_dict()
            similarity = SequenceMatcher(
                None, suggestion_text, data.get("suggestion_text", "")
            ).ratio()

            if similarity > 0.7:
                similar.append(data)

        return similar

    async def _create_rejection_pattern_signal(
        self,
        feedback: SuggestionFeedback,
        similar_rejections: List[Dict]
    ):
        """Create a learning signal when we detect a rejection pattern."""
        # Aggregate rejection reasons
        all_categories = []
        for rejection in similar_rejections:
            all_categories.extend(rejection.get("categories", []))

        # Find most common category
        from collections import Counter
        category_counts = Counter(all_categories)
        most_common = category_counts.most_common(1)[0] if category_counts else ("unknown", 0)

        signal = LearningSignal(
            signal_id=f"sig_{uuid.uuid4().hex[:12]}",
            signal_type="negative",
            source_feedback_ids=[r.get("feedback_id") for r in similar_rejections],
            agent_id="agent3",  # Coach agent
            insight=f"Suggestion pattern frequently rejected: {most_common[0]}",
            action_recommended=f"Review and revise suggestions related to: {feedback.suggestion_text[:100]}",
            confidence=min(0.9, len(similar_rejections) / 10.0),
            priority="high" if len(similar_rejections) >= 5 else "medium",
            sample_size=len(similar_rejections),
            status="pending_review",
        )

        await self._store_learning_signal(signal)

    async def _record_acceptance(self, feedback: SuggestionFeedback):
        """Record that a suggestion was accepted for positive reinforcement."""
        acceptance_doc = {
            "feedback_id": feedback.feedback_id,
            "suggestion_id": feedback.suggestion_id,
            "suggestion_text": feedback.suggestion_text,
            "rep_id": feedback.rep_id,
            "timestamp": datetime.utcnow(),
        }

        await self.firestore.collection("suggestion_acceptances").add(acceptance_doc)

    # =========================================================================
    # Summary Edit Feedback
    # =========================================================================

    async def record_summary_edit(
        self,
        case_id: str,
        original_summary: str,
        edited_summary: str,
        editor_id: str,
    ) -> SummaryEditFeedback:
        """Record when a rep edits the generated summary."""
        # Calculate edit distance
        edit_distance = 1.0 - SequenceMatcher(
            None, original_summary, edited_summary
        ).ratio()

        # Categorize the types of edits
        edit_categories = self._categorize_edits(original_summary, edited_summary)

        feedback = SummaryEditFeedback(
            feedback_id=f"fb_{uuid.uuid4().hex[:12]}",
            case_id=case_id,
            original_summary=original_summary,
            edited_summary=edited_summary,
            editor_id=editor_id,
            edit_distance=edit_distance,
            edit_categories=edit_categories,
            source="slack",
        )

        await self._store_feedback(feedback)

        # Significant edits are learning opportunities
        if edit_distance > 0.2:  # More than 20% changed
            await self._analyze_significant_edit(feedback)

        return feedback

    def _categorize_edits(self, original: str, edited: str) -> List[str]:
        """Categorize what types of edits were made."""
        categories = []

        # Length comparison
        if len(edited) > len(original) * 1.2:
            categories.append("added_content")
        elif len(edited) < len(original) * 0.8:
            categories.append("removed_content")

        # Check for tone changes (simplified)
        formal_words = ["您", "貴司", "敬請", "please", "kindly"]
        informal_words = ["你", "我們", "ok", "okay"]

        orig_formal = sum(1 for w in formal_words if w in original)
        edit_formal = sum(1 for w in formal_words if w in edited)

        if edit_formal > orig_formal:
            categories.append("more_formal")
        elif edit_formal < orig_formal:
            categories.append("less_formal")

        return categories if categories else ["minor_adjustments"]

    async def _analyze_significant_edit(self, feedback: SummaryEditFeedback):
        """Analyze significant edits to understand what the agent got wrong."""
        # Store for pattern analysis
        edit_analysis = {
            "feedback_id": feedback.feedback_id,
            "case_id": feedback.case_id,
            "edit_distance": feedback.edit_distance,
            "categories": feedback.edit_categories,
            "original_length": len(feedback.original_summary),
            "edited_length": len(feedback.edited_summary),
            "timestamp": datetime.utcnow(),
        }

        await self.firestore.collection("significant_edits").add(edit_analysis)

        # Check if this editor frequently makes similar edits
        editor_pattern = await self._check_editor_pattern(
            feedback.editor_id,
            feedback.edit_categories
        )

        if editor_pattern:
            # This editor consistently changes things a certain way
            # Could mean: personal preference OR consistent agent error
            await self._create_edit_pattern_signal(feedback, editor_pattern)

    async def _check_editor_pattern(
        self,
        editor_id: str,
        current_categories: List[str]
    ) -> Optional[Dict]:
        """Check if this editor has a consistent editing pattern."""
        # Get this editor's past edits
        past_edits = (
            self.firestore.collection("significant_edits")
            .where("editor_id", "==", editor_id)
            .limit(20)
            .stream()
        )

        category_counts = {}
        for doc in past_edits:
            for cat in doc.to_dict().get("categories", []):
                category_counts[cat] = category_counts.get(cat, 0) + 1

        # Check for consistent pattern (>50% of edits have same category)
        total = sum(category_counts.values())
        if total >= 5:
            for cat, count in category_counts.items():
                if count / total > 0.5:
                    return {"category": cat, "frequency": count / total}

        return None

    async def _create_edit_pattern_signal(
        self,
        feedback: SummaryEditFeedback,
        pattern: Dict
    ):
        """Create learning signal from edit pattern."""
        signal = LearningSignal(
            signal_id=f"sig_{uuid.uuid4().hex[:12]}",
            signal_type="negative",
            source_feedback_ids=[feedback.feedback_id],
            agent_id="agent4",  # Summary agent
            insight=f"Consistent edit pattern detected: {pattern['category']}",
            action_recommended=f"Adjust summary generation to address: {pattern['category']}",
            confidence=pattern["frequency"],
            priority="medium",
            sample_size=1,
            status="pending_review",
        )

        await self._store_learning_signal(signal)

    # =========================================================================
    # Storage and Signals
    # =========================================================================

    async def _store_feedback(self, feedback: Feedback):
        """Store feedback in Firestore."""
        doc_ref = self.firestore.collection("feedback").document(feedback.feedback_id)
        await doc_ref.set(feedback.model_dump())

    async def _store_learning_signal(self, signal: LearningSignal):
        """Store learning signal for processing."""
        doc_ref = self.firestore.collection("learning_signals").document(signal.signal_id)
        await doc_ref.set(signal.model_dump())

        # Optionally publish to PubSub for async processing
        if self.pubsub:
            await self.pubsub.publish(
                "learning-signals",
                signal.model_dump_json().encode()
            )

    async def _emit_learning_signal(self, feedback: Feedback):
        """Emit learning signal based on feedback type."""
        # This can be expanded based on feedback type
        pass

    # =========================================================================
    # Aggregation Methods
    # =========================================================================

    async def get_feedback_summary(
        self,
        days: int = 7,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get summary of feedback collected."""
        cutoff = datetime.utcnow()
        # Would filter by date in production

        docs = self.firestore.collection("feedback").stream()
        feedback_list = [doc.to_dict() for doc in docs]

        return {
            "total_feedback": len(feedback_list),
            "by_type": self._count_by_type(feedback_list),
            "suggestion_acceptance_rate": self._calc_acceptance_rate(feedback_list),
            "average_edit_distance": self._calc_avg_edit_distance(feedback_list),
        }

    def _count_by_type(self, feedback_list: List[Dict]) -> Dict[str, int]:
        """Count feedback by type."""
        counts = {}
        for fb in feedback_list:
            fb_type = fb.get("feedback_type", "unknown")
            counts[fb_type] = counts.get(fb_type, 0) + 1
        return counts

    def _calc_acceptance_rate(self, feedback_list: List[Dict]) -> float:
        """Calculate suggestion acceptance rate."""
        suggestions = [
            fb for fb in feedback_list
            if fb.get("feedback_type") == FeedbackType.SUGGESTION_RESPONSE.value
        ]

        if not suggestions:
            return 0.0

        accepted = sum(
            1 for s in suggestions
            if s.get("response") == SuggestionResponse.ACCEPTED.value
        )

        return accepted / len(suggestions)

    def _calc_avg_edit_distance(self, feedback_list: List[Dict]) -> float:
        """Calculate average edit distance for summary edits."""
        edits = [
            fb for fb in feedback_list
            if fb.get("feedback_type") == FeedbackType.SUMMARY_EDIT.value
        ]

        if not edits:
            return 0.0

        total_distance = sum(e.get("edit_distance", 0) for e in edits)
        return total_distance / len(edits)
