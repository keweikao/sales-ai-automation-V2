"""
CRM Extraction Skill.

Wraps Agent 6 (CRM Extractor) as a Skill.
Extracts Salesforce-ready fields from analysis results.
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
class CRMInput:
    """Input for CRM Extraction Skill."""
    transcript_segments: list[dict[str, Any]]
    context_insights: Optional[dict[str, Any]] = None
    buyer_insights: Optional[dict[str, Any]] = None
    seller_insights: Optional[dict[str, Any]] = None


@dataclass
class CRMOutput:
    """Output from CRM Extraction Skill."""
    stage_name: Optional[str] = None  # Salesforce stage
    next_step: Optional[str] = None
    close_date: Optional[str] = None
    amount: Optional[float] = None
    probability: Optional[int] = None
    description: Optional[str] = None
    custom_fields: dict[str, Any] = field(default_factory=dict)
    raw_data: dict[str, Any] = field(default_factory=dict)


class CRMExtractionSkill(Skill[CRMInput, CRMOutput]):
    """
    Skill that extracts CRM-ready fields.

    Wraps the existing CRMExtractorAgent (Agent 6) from the MEDDIC system.
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="meddic.crm-extraction",
            name="CRM Extraction",
            version="1.0.0",
            description="Extracts Salesforce-ready fields from analysis results",
            category=SkillCategory.EXTRACTION,
            tags=["meddic", "sales", "crm", "salesforce"],
            requires_llm=True,
            estimated_duration_seconds=10.0,
        )

    def execute(
        self,
        input_data: CRMInput,
        context: SkillContext,
    ) -> SkillResult[CRMOutput]:
        """Execute CRM extraction using the underlying agent."""
        try:
            # Import the underlying agent
            from ..meddic.agents import CRMExtractorAgent

            # Create agent instance
            agent = CRMExtractorAgent()

            # Execute extraction
            response = agent.extract(
                transcript_segments=input_data.transcript_segments,
                context_insights=input_data.context_insights or {},
                buyer_insights=input_data.buyer_insights or {},
                seller_insights=input_data.seller_insights or {},
            )

            # Map to output structure
            data = response.data or {}

            output = CRMOutput(
                stage_name=data.get("stage_name") or data.get("stageName"),
                next_step=data.get("next_step") or data.get("nextStep"),
                close_date=data.get("close_date") or data.get("closeDate"),
                amount=data.get("amount"),
                probability=data.get("probability"),
                description=data.get("description"),
                custom_fields=data.get("customFields", {}),
                raw_data=data,
            )

            return SkillResult.ok(
                data=output,
                report=response.report,
                metadata={"model": response.model_name},
            )

        except Exception as e:
            return SkillResult.fail(error=str(e))

    def validate_input(self, input_data: CRMInput) -> Optional[str]:
        """Validate input data."""
        if not input_data.transcript_segments:
            return "transcript_segments is required and cannot be empty"
        return None
