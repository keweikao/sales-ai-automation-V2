"""
Context Analysis Skill.

Wraps Agent 1 (Context & Structure) as a Skill.
Analyzes meeting background, participants, and conversation structure.
"""

from dataclasses import dataclass
from typing import Any, Optional

from core.skills import (
    Skill,
    SkillCategory,
    SkillContext,
    SkillMetadata,
    SkillResult,
)


@dataclass
class ContextInput:
    """Input for Context Analysis Skill."""
    transcript_segments: list[dict[str, Any]]
    demo_meta: Optional[dict[str, Any]] = None


@dataclass
class ContextOutput:
    """Output from Context Analysis Skill."""
    meeting_type: Optional[str] = None
    participants: list[dict[str, Any]] = None
    topics_discussed: list[str] = None
    meeting_stage: Optional[str] = None
    key_moments: list[dict[str, Any]] = None
    raw_data: dict[str, Any] = None

    def __post_init__(self):
        if self.participants is None:
            self.participants = []
        if self.topics_discussed is None:
            self.topics_discussed = []
        if self.key_moments is None:
            self.key_moments = []
        if self.raw_data is None:
            self.raw_data = {}


class ContextAnalysisSkill(Skill[ContextInput, ContextOutput]):
    """
    Skill that analyzes conversation context and structure.

    Wraps the existing ContextAgent (Agent 1) from the MEDDIC system.
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="meddic.context-analysis",
            name="Context Analysis",
            version="1.0.0",
            description="Analyzes meeting background, participants, and conversation structure",
            category=SkillCategory.ANALYSIS,
            tags=["meddic", "sales", "context"],
            requires_llm=True,
            estimated_duration_seconds=15.0,
        )

    def execute(
        self,
        input_data: ContextInput,
        context: SkillContext,
    ) -> SkillResult[ContextOutput]:
        """Execute context analysis using the underlying agent."""
        try:
            # Import the underlying agent
            from ..meddic.agents import ContextAgent

            # Create agent instance
            agent = ContextAgent()

            # Execute analysis
            response = agent.analyze(
                transcript_segments=input_data.transcript_segments,
                demo_meta=input_data.demo_meta,
            )

            # Map to output structure
            data = response.data or {}
            output = ContextOutput(
                meeting_type=data.get("meetingType"),
                participants=data.get("participants", []),
                topics_discussed=data.get("topicsDiscussed", []),
                meeting_stage=data.get("meetingStage"),
                key_moments=data.get("keyMoments", []),
                raw_data=data,
            )

            return SkillResult.ok(
                data=output,
                report=response.report,
                metadata={"model": response.model_name},
            )

        except Exception as e:
            return SkillResult.fail(error=str(e))

    def validate_input(self, input_data: ContextInput) -> Optional[str]:
        """Validate input data."""
        if not input_data.transcript_segments:
            return "transcript_segments is required and cannot be empty"
        return None
