"""
Seller Coaching Skill.

Wraps Agent 3 (Seller/Coach) as a Skill.
Provides sales coaching insights and recommendations.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from core.skills import (
    Skill,
    SkillCategory,
    SkillContext,
    SkillMetadata,
    SkillResult,
)


@dataclass
class SellerInput:
    """Input for Seller Coaching Skill."""
    transcript_segments: list[dict[str, Any]]
    context_insights: Optional[dict[str, Any]] = None
    buyer_insights: Optional[dict[str, Any]] = None


@dataclass
class CoachingInsight:
    """A single coaching insight."""
    category: str  # "strength", "improvement", "action"
    content: str
    priority: Optional[str] = None  # "high", "medium", "low"


@dataclass
class SellerOutput:
    """Output from Seller Coaching Skill."""
    progress_score: Optional[int] = None
    recommended_strategy: Optional[str] = None
    insights: list[CoachingInsight] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    improvement_areas: list[str] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)


class SellerCoachingSkill(Skill[SellerInput, SellerOutput]):
    """
    Skill that provides sales coaching insights.

    Wraps the existing SellerAgent (Agent 3) from the MEDDIC system.
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="meddic.seller-coaching",
            name="Seller Coaching",
            version="1.0.0",
            description="Provides sales coaching insights and recommendations",
            category=SkillCategory.ANALYSIS,
            tags=["meddic", "sales", "coaching", "seller"],
            requires_llm=True,
            estimated_duration_seconds=20.0,
        )

    def execute(
        self,
        input_data: SellerInput,
        context: SkillContext,
    ) -> SkillResult[SellerOutput]:
        """Execute seller coaching analysis using the underlying agent."""
        try:
            # Import the underlying agent
            from ..meddic.agents import SellerAgent

            # Create agent instance
            agent = SellerAgent()

            # Execute analysis
            response = agent.analyze(
                transcript_segments=input_data.transcript_segments,
                context_insights=input_data.context_insights or {},
                buyer_insights=input_data.buyer_insights or {},
            )

            # Map to output structure
            data = response.data or {}

            # Parse insights
            insights = []
            for insight_data in data.get("insights", []):
                insights.append(CoachingInsight(
                    category=insight_data.get("category", "improvement"),
                    content=insight_data.get("content", ""),
                    priority=insight_data.get("priority"),
                ))

            output = SellerOutput(
                progress_score=data.get("progress_score") or data.get("progressScore"),
                recommended_strategy=data.get("recommendedStrategy"),
                insights=insights,
                next_steps=data.get("nextSteps", []),
                strengths=data.get("strengths", []),
                improvement_areas=data.get("improvementAreas", []),
                raw_data=data,
            )

            return SkillResult.ok(
                data=output,
                report=response.report,
                metadata={"model": response.model_name},
            )

        except Exception as e:
            return SkillResult.fail(error=str(e))

    def validate_input(self, input_data: SellerInput) -> Optional[str]:
        """Validate input data."""
        if not input_data.transcript_segments:
            return "transcript_segments is required and cannot be empty"
        return None
