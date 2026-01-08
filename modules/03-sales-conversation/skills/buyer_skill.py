"""
Buyer Analysis Skill.

Wraps Agent 2 (Buyer Psychology) as a Skill.
Analyzes buyer needs, hesitations, pain points, and MEDDIC criteria.
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
class BuyerInput:
    """Input for Buyer Analysis Skill."""
    transcript_segments: list[dict[str, Any]]
    context_insights: Optional[dict[str, Any]] = None


@dataclass
class MEDDICData:
    """MEDDIC analysis data."""
    metrics: Optional[str] = None
    economic_buyer: Optional[str] = None
    decision_criteria: Optional[str] = None
    decision_process: Optional[str] = None
    identify_pain: Optional[str] = None
    champion: Optional[str] = None


@dataclass
class BuyerPsychology:
    """Buyer psychology analysis."""
    hesitations: list[str] = field(default_factory=list)
    trust_score: Optional[int] = None
    engagement_level: Optional[str] = None
    buying_signals: list[str] = field(default_factory=list)


@dataclass
class BuyerOutput:
    """Output from Buyer Analysis Skill."""
    identified_needs: list[str] = field(default_factory=list)
    pain_points: list[str] = field(default_factory=list)
    meddic: Optional[MEDDICData] = None
    psychology: Optional[BuyerPsychology] = None
    raw_data: dict[str, Any] = field(default_factory=dict)


class BuyerAnalysisSkill(Skill[BuyerInput, BuyerOutput]):
    """
    Skill that analyzes buyer psychology and needs.

    Wraps the existing BuyerAgent (Agent 2) from the MEDDIC system.
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="meddic.buyer-analysis",
            name="Buyer Analysis",
            version="1.0.0",
            description="Analyzes buyer needs, hesitations, pain points, and MEDDIC criteria",
            category=SkillCategory.ANALYSIS,
            tags=["meddic", "sales", "buyer", "psychology"],
            requires_llm=True,
            estimated_duration_seconds=20.0,
        )

    def execute(
        self,
        input_data: BuyerInput,
        context: SkillContext,
    ) -> SkillResult[BuyerOutput]:
        """Execute buyer analysis using the underlying agent."""
        try:
            # Import the underlying agent
            from ..meddic.agents import BuyerAgent

            # Create agent instance
            agent = BuyerAgent()

            # Execute analysis
            response = agent.analyze(
                transcript_segments=input_data.transcript_segments,
                context_insights=input_data.context_insights or {},
            )

            # Map to output structure
            data = response.data or {}

            # Parse MEDDIC data
            meddic_raw = data.get("meddic", {})
            meddic = MEDDICData(
                metrics=meddic_raw.get("metrics"),
                economic_buyer=meddic_raw.get("economicBuyer"),
                decision_criteria=meddic_raw.get("decisionCriteria"),
                decision_process=meddic_raw.get("decisionProcess"),
                identify_pain=meddic_raw.get("pain") or meddic_raw.get("identifyPain"),
                champion=meddic_raw.get("champion"),
            )

            # Parse psychology data
            psych_raw = data.get("psychology", {})
            psychology = BuyerPsychology(
                hesitations=psych_raw.get("hesitations", []),
                trust_score=psych_raw.get("trustScore"),
                engagement_level=psych_raw.get("engagementLevel"),
                buying_signals=psych_raw.get("buyingSignals", []),
            )

            output = BuyerOutput(
                identified_needs=data.get("identifiedNeeds", []),
                pain_points=data.get("painPoints", []),
                meddic=meddic,
                psychology=psychology,
                raw_data=data,
            )

            return SkillResult.ok(
                data=output,
                report=response.report,
                metadata={"model": response.model_name},
            )

        except Exception as e:
            return SkillResult.fail(error=str(e))

    def validate_input(self, input_data: BuyerInput) -> Optional[str]:
        """Validate input data."""
        if not input_data.transcript_segments:
            return "transcript_segments is required and cannot be empty"
        return None

    def refine(
        self,
        input_data: BuyerInput,
        previous_result: BuyerOutput,
        feedback: str,
        context: SkillContext,
    ) -> SkillResult[BuyerOutput]:
        """Refine previous analysis based on feedback."""
        try:
            from ..meddic.agents import BuyerAgent

            agent = BuyerAgent()

            response = agent.refine(
                transcript_segments=input_data.transcript_segments,
                previous_result=previous_result.raw_data,
                feedback=feedback,
            )

            data = response.data or {}

            meddic_raw = data.get("meddic", {})
            meddic = MEDDICData(
                metrics=meddic_raw.get("metrics"),
                economic_buyer=meddic_raw.get("economicBuyer"),
                decision_criteria=meddic_raw.get("decisionCriteria"),
                decision_process=meddic_raw.get("decisionProcess"),
                identify_pain=meddic_raw.get("pain") or meddic_raw.get("identifyPain"),
                champion=meddic_raw.get("champion"),
            )

            psych_raw = data.get("psychology", {})
            psychology = BuyerPsychology(
                hesitations=psych_raw.get("hesitations", []),
                trust_score=psych_raw.get("trustScore"),
                engagement_level=psych_raw.get("engagementLevel"),
                buying_signals=psych_raw.get("buyingSignals", []),
            )

            output = BuyerOutput(
                identified_needs=data.get("identifiedNeeds", []),
                pain_points=data.get("painPoints", []),
                meddic=meddic,
                psychology=psychology,
                raw_data=data,
            )

            return SkillResult.ok(
                data=output,
                report=response.report,
                metadata={"model": response.model_name, "refined": True},
            )

        except Exception as e:
            return SkillResult.fail(error=str(e))
