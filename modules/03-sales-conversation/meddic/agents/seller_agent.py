"""
Agent 3 - Seller Perspective (Sales & Strategy).

Evaluates sales performance and provides coaching recommendations.

Migration note: From analysis-service/src/agents/agent3_seller.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable

from .base import GeminiJSONAgent, render_transcript

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "agent3-seller.md"


class SellerAgent(GeminiJSONAgent):
    """Agent 3 - Seller Perspective (Sales & Strategy)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(prompt_path=PROMPT_PATH, **kwargs)

    # pylint: disable=arguments-differ
    def build_prompt(  # type: ignore[override]
        self,
        *,
        transcript_segments: Iterable[Dict[str, Any]],
        context_insights: Dict[str, Any],
        buyer_insights: Dict[str, Any],
    ) -> str:
        transcript_block = render_transcript(transcript_segments)
        context_block = json.dumps(context_insights, ensure_ascii=False, indent=2)
        buyer_block = json.dumps(buyer_insights, ensure_ascii=False, indent=2)

        return (
            self.prompt_template
            + f"\n\n=== Context (Agent 1) ===\n{context_block}"
            + f"\n\n=== Buyer Insights (Agent 2) ===\n{buyer_block}"
            + f"\n\n=== Transcript ===\n{transcript_block}"
        )

    def analyze(
        self,
        *,
        transcript_segments: Iterable[Dict[str, Any]],
        context_insights: Dict[str, Any],
        buyer_insights: Dict[str, Any],
    ):
        """Returns GeminiResponse with both data and report."""
        return self.invoke(
            transcript_segments=transcript_segments,
            context_insights=context_insights,
            buyer_insights=buyer_insights,
        )
