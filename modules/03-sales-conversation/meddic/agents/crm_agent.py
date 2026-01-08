"""
Agent 6: CRM Extractor - Salesforce 欄位擷取.

從對話逐字稿和前置 Agent 分析結果中，提取 Salesforce CRM 所需的結構化欄位。
支援即時更新 Salesforce Opportunity 的 StageName 和其他自訂欄位。

Migration note: From analysis-service/src/agents/agent6_crm_extractor.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .base import GeminiJSONAgent, render_transcript

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "agent6-crm-extractor.md"


class CRMExtractorAgent(GeminiJSONAgent):
    """Agent 6 - CRM Extractor (Salesforce 欄位擷取)."""

    # Valid Salesforce StageName values
    VALID_STAGES = [
        "Prospecting",
        "Qualification",
        "Needs Analysis",
        "Value Proposition",
        "Proposal",
        "Negotiation",
        "Closed Won",
        "Closed Lost",
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(prompt_path=PROMPT_PATH, **kwargs)

    def build_prompt(
        self,
        *,
        transcript_segments: Iterable[Dict[str, Any]],
        context_insights: Optional[Dict[str, Any]] = None,
        buyer_insights: Optional[Dict[str, Any]] = None,
        seller_insights: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build the extraction prompt with transcript and previous agent results.

        Args:
            transcript_segments: The conversation transcript
            context_insights: Agent 1 output (optional)
            buyer_insights: Agent 2 output (optional)
            seller_insights: Agent 3 output (optional)
        """
        transcript_block = render_transcript(transcript_segments)

        # Build context from previous agents
        context_parts = []

        if context_insights:
            context_parts.append(
                f"=== Agent 1 (Context) ===\n"
                f"{json.dumps(context_insights, ensure_ascii=False, indent=2)}"
            )

        if buyer_insights:
            context_parts.append(
                f"=== Agent 2 (Buyer) ===\n"
                f"{json.dumps(buyer_insights, ensure_ascii=False, indent=2)}"
            )

        if seller_insights:
            context_parts.append(
                f"=== Agent 3 (Seller) ===\n"
                f"{json.dumps(seller_insights, ensure_ascii=False, indent=2)}"
            )

        context_block = "\n\n".join(context_parts) if context_parts else "(無前置分析)"

        return (
            self.prompt_template
            + f"\n\n=== 前置 Agent 分析結果 ===\n{context_block}"
            + f"\n\n=== Transcript ===\n{transcript_block}"
        )

    def extract(
        self,
        *,
        transcript_segments: Iterable[Dict[str, Any]],
        context_insights: Optional[Dict[str, Any]] = None,
        buyer_insights: Optional[Dict[str, Any]] = None,
        seller_insights: Optional[Dict[str, Any]] = None,
    ):
        """
        Extract CRM fields from transcript.

        Returns GeminiResponse with both data and report.
        """
        return self.invoke(
            transcript_segments=transcript_segments,
            context_insights=context_insights,
            buyer_insights=buyer_insights,
            seller_insights=seller_insights,
        )

    def validate_stage(self, stage_name: str) -> bool:
        """Validate that the stage_name is a valid Salesforce picklist value."""
        return stage_name in self.VALID_STAGES

    def get_salesforce_update_payload(self, extraction_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert extraction result to Salesforce update payload.

        Args:
            extraction_result: The JSON data from extract()

        Returns:
            Dict ready to be sent to Salesforce API
        """
        payload = {}

        # StageName (primary field)
        stage_name = extraction_result.get("stage_name")
        if stage_name and self.validate_stage(stage_name):
            payload["StageName"] = stage_name

        # Additional fields can be mapped here
        # Example: Custom fields like Budget__c, Next_Steps__c

        if extraction_result.get("budget", {}).get("range"):
            payload["Budget__c"] = extraction_result["budget"]["range"]

        if extraction_result.get("next_steps"):
            next_steps = extraction_result["next_steps"]
            if isinstance(next_steps, list):
                payload["Next_Steps__c"] = "; ".join(next_steps)
            else:
                payload["Next_Steps__c"] = str(next_steps)

        return payload
