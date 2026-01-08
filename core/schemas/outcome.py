"""
Outcome and Feedback Schemas for Learning Agent System.

These schemas capture the "ground truth" that enables agents to learn
from real-world results rather than just performing static analysis.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


class DealStatus(str, Enum):
    """Possible outcomes for a sales deal."""
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"
    ONGOING = "ongoing"
    STALLED = "stalled"
    NURTURING = "nurturing"


class FeedbackType(str, Enum):
    """Types of feedback signals."""
    EXPLICIT_RATING = "explicit_rating"
    SUGGESTION_RESPONSE = "suggestion_response"
    SUMMARY_EDIT = "summary_edit"
    OUTCOME_SIGNAL = "outcome_signal"


class SuggestionResponse(str, Enum):
    """How a rep responded to a coaching suggestion."""
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"
    IGNORED = "ignored"


# =============================================================================
# Outcome Tracking
# =============================================================================

class DealOutcome(BaseModel):
    """
    Tracks the actual outcome of a deal for comparison with agent predictions.
    This is the core feedback that enables learning.
    """
    case_id: str
    salesforce_opportunity_id: Optional[str] = None

    # Agent Predictions (captured at analysis time)
    predicted_meddic_score: int = Field(..., ge=0, le=100)
    predicted_qualification: Literal["qualified", "nurture", "disqualified"]
    predicted_close_probability: float = Field(..., ge=0.0, le=1.0)
    predicted_close_date: Optional[datetime] = None
    coaching_suggestions_given: List[str] = Field(default_factory=list)

    # Actual Results (synced from CRM)
    actual_outcome: DealStatus
    actual_close_date: Optional[datetime] = None
    actual_deal_value: Optional[float] = None
    days_in_pipeline: Optional[int] = None
    loss_reason: Optional[str] = None  # If closed_lost

    # Action Tracking
    suggestions_followed: List[str] = Field(default_factory=list)
    suggestions_ignored: List[str] = Field(default_factory=list)

    # Computed Metrics
    prediction_error: Optional[float] = None  # Difference between predicted and actual
    coaching_effectiveness_score: Optional[float] = None

    # Metadata
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
    synced_from_crm_at: Optional[datetime] = None
    rep_id: str
    rep_name: str

    def calculate_prediction_accuracy(self) -> float:
        """Calculate how accurate the MEDDIC prediction was."""
        if self.actual_outcome == DealStatus.CLOSED_WON:
            # High score should predict win
            return self.predicted_meddic_score / 100.0
        elif self.actual_outcome == DealStatus.CLOSED_LOST:
            # High score but lost = prediction error
            return 1.0 - (self.predicted_meddic_score / 100.0)
        return 0.5  # Ongoing deals are neutral


class OutcomePattern(BaseModel):
    """A discovered pattern from analyzing multiple outcomes."""
    pattern_id: str
    pattern_type: Literal["success", "failure", "risk"]
    description: str
    conditions: Dict[str, Any]  # e.g., {"industry": "retail", "deal_size": ">100k"}
    occurrence_count: int
    success_rate: float
    confidence: float
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    examples: List[str] = Field(default_factory=list)  # case_ids


# =============================================================================
# Feedback Collection
# =============================================================================

class Feedback(BaseModel):
    """Base feedback model."""
    feedback_id: str
    case_id: str
    feedback_type: FeedbackType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str  # "slack", "web_ui", "crm_sync"


class ExplicitFeedback(Feedback):
    """Direct feedback from users (ratings, comments)."""
    feedback_type: FeedbackType = FeedbackType.EXPLICIT_RATING
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None
    rated_by: str
    rated_component: str  # "meddic_score", "coaching_suggestion", "summary"


class SuggestionFeedback(Feedback):
    """Feedback on coaching suggestions."""
    feedback_type: FeedbackType = FeedbackType.SUGGESTION_RESPONSE
    suggestion_id: str
    suggestion_text: str
    response: SuggestionResponse
    rep_comment: Optional[str] = None
    rep_id: str
    time_to_respond: Optional[int] = None  # seconds


class SummaryEditFeedback(Feedback):
    """Implicit feedback from summary edits."""
    feedback_type: FeedbackType = FeedbackType.SUMMARY_EDIT
    original_summary: str
    edited_summary: str
    editor_id: str
    edit_distance: float  # Normalized edit distance
    edit_categories: List[str] = Field(default_factory=list)
    # Categories: tone_change, factual_correction, added_context, removed_content


class OutcomeFeedback(Feedback):
    """Feedback from deal outcomes."""
    feedback_type: FeedbackType = FeedbackType.OUTCOME_SIGNAL
    outcome: DealStatus
    prediction_was_correct: bool
    prediction_error_magnitude: float
    contributing_factors: List[str] = Field(default_factory=list)


# =============================================================================
# Learning Signals
# =============================================================================

class LearningSignal(BaseModel):
    """A processed signal that can be used for agent improvement."""
    signal_id: str
    signal_type: Literal["positive", "negative", "neutral"]
    source_feedback_ids: List[str]
    agent_id: str  # Which agent this applies to

    # What we learned
    insight: str
    action_recommended: str

    # Confidence and priority
    confidence: float = Field(..., ge=0.0, le=1.0)
    priority: Literal["high", "medium", "low"]
    sample_size: int

    # Status
    status: Literal["pending_review", "approved", "applied", "rejected"]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_by: Optional[str] = None
    applied_at: Optional[datetime] = None


class PromptImprovement(BaseModel):
    """A proposed improvement to an agent's prompt based on learning signals."""
    improvement_id: str
    agent_id: str
    signal_ids: List[str]  # Learning signals that led to this

    # The change
    original_prompt_section: str
    improved_prompt_section: str
    change_rationale: str

    # Testing
    experiment_id: Optional[str] = None
    test_results: Optional[Dict[str, float]] = None

    # Status
    status: Literal["proposed", "testing", "approved", "deployed", "rolled_back"]
    proposed_at: datetime = Field(default_factory=datetime.utcnow)
    deployed_at: Optional[datetime] = None


# =============================================================================
# Agent Performance Metrics
# =============================================================================

class AgentMetrics(BaseModel):
    """Performance metrics for a single agent."""
    agent_id: str
    period_start: datetime
    period_end: datetime

    # Accuracy Metrics
    prediction_accuracy: float  # % of correct predictions
    meddic_score_mae: float  # Mean Absolute Error of MEDDIC scores
    qualification_precision: float
    qualification_recall: float

    # Effectiveness Metrics
    suggestion_acceptance_rate: float
    suggestion_to_outcome_correlation: float

    # Quality Metrics
    summary_edit_rate: float
    average_edit_distance: float

    # Efficiency Metrics
    average_processing_time_ms: float
    average_token_cost: float

    # Trends
    vs_previous_period: Dict[str, float] = Field(default_factory=dict)


class SystemMetrics(BaseModel):
    """Overall system performance metrics."""
    period_start: datetime
    period_end: datetime

    # Volume
    total_cases_processed: int
    total_feedback_collected: int
    total_outcomes_recorded: int

    # Per-Agent Metrics
    agent_metrics: Dict[str, AgentMetrics]

    # Learning Metrics
    learning_signals_generated: int
    improvements_applied: int
    experiments_completed: int

    # Business Impact
    estimated_rep_time_saved_hours: float
    prediction_accuracy_improvement: float
