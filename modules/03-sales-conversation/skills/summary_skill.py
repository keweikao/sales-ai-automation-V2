"""
Summary Generation Skill.

Wraps Agent 4 (Summary) as a Skill.
Generates customer-facing summaries from analysis results.
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
class SummaryInput:
    """Input for Summary Generation Skill."""
    transcript_segments: list[dict[str, Any]]
    context_insights: Optional[dict[str, Any]] = None
    customer_name: Optional[str] = None
    sales_rep_name: Optional[str] = None


@dataclass
class SummaryOutput:
    """Output from Summary Generation Skill."""
    summary: Optional[str] = None
    key_points: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    follow_up_topics: list[str] = field(default_factory=list)
    customer_message: Optional[str] = None  # Ready to send to customer
    raw_data: dict[str, Any] = field(default_factory=dict)


class SummaryGenerationSkill(Skill[SummaryInput, SummaryOutput]):
    """
    Skill that generates customer-facing summaries.

    Wraps the existing SummaryAgent (Agent 4) from the MEDDIC system.
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="meddic.summary-generation",
            name="Summary Generation",
            version="1.0.0",
            description="Generates customer-facing summaries from analysis results",
            category=SkillCategory.GENERATION,
            tags=["meddic", "sales", "summary", "customer"],
            requires_llm=True,
            estimated_duration_seconds=15.0,
        )

    def execute(
        self,
        input_data: SummaryInput,
        context: SkillContext,
    ) -> SkillResult[SummaryOutput]:
        """Execute summary generation using the underlying agent."""
        try:
            # Import the underlying agent
            from ..meddic.agents import SummaryAgent

            # Create agent instance
            agent = SummaryAgent()

            # Execute analysis
            response = agent.analyze(
                transcript_segments=input_data.transcript_segments,
                context_insights=input_data.context_insights or {},
            )

            # Map to output structure
            data = response.data or {}

            # Replace placeholders if names provided
            if input_data.customer_name or input_data.sales_rep_name:
                data = self._replace_placeholders(
                    data,
                    input_data.customer_name or "客戶",
                    input_data.sales_rep_name or "業務",
                )

            output = SummaryOutput(
                summary=data.get("summary"),
                key_points=data.get("keyPoints", []),
                action_items=data.get("actionItems", []),
                follow_up_topics=data.get("followUpTopics", []),
                customer_message=data.get("customerMessage"),
                raw_data=data,
            )

            return SkillResult.ok(
                data=output,
                report=response.report,
                metadata={"model": response.model_name},
            )

        except Exception as e:
            return SkillResult.fail(error=str(e))

    def validate_input(self, input_data: SummaryInput) -> Optional[str]:
        """Validate input data."""
        if not input_data.transcript_segments:
            return "transcript_segments is required and cannot be empty"
        return None

    def _replace_placeholders(
        self,
        data: dict[str, Any],
        customer_name: str,
        sales_rep_name: str,
    ) -> dict[str, Any]:
        """Replace placeholder text with actual names."""
        import copy
        import re

        result = copy.deepcopy(data)

        replacements = {
            r'\[店名\]': customer_name,
            r'\[客戶名稱\]': customer_name,
            r'\[客戶姓名\]': customer_name,
            r'\[業務名稱\]': sales_rep_name,
            r'\[業務姓名\]': sales_rep_name,
        }

        def replace_in_string(text: str) -> str:
            if not isinstance(text, str):
                return text
            for pattern, replacement in replacements.items():
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            return text

        def replace_recursive(obj):
            if isinstance(obj, str):
                return replace_in_string(obj)
            elif isinstance(obj, dict):
                return {k: replace_recursive(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_recursive(item) for item in obj]
            return obj

        return replace_recursive(result)
