"""
Agent 2 - Buyer Perspective (Customer & Product).

Extracts customer insights, needs, pain points, and MEDDIC evaluation.

Migration note: From analysis-service/src/agents/agent2_buyer.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable

from .base import GeminiJSONAgent, render_transcript

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "agent2-buyer.md"


class BuyerAgent(GeminiJSONAgent):
    """Agent 2 - Buyer Perspective (Customer & Product)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(prompt_path=PROMPT_PATH, **kwargs)

    # pylint: disable=arguments-differ
    def build_prompt(  # type: ignore[override]
        self,
        *,
        transcript_segments: Iterable[Dict[str, Any]],
        context_insights: Dict[str, Any],
    ) -> str:
        transcript_block = render_transcript(transcript_segments)
        context_block = json.dumps(context_insights, ensure_ascii=False, indent=2)

        return (
            self.prompt_template
            + f"\n\n=== Context (Agent 1) ===\n{context_block}"
            + f"\n\n=== Transcript ===\n{transcript_block}"
        )

    def analyze(
        self,
        *,
        transcript_segments: Iterable[Dict[str, Any]],
        context_insights: Dict[str, Any],
    ):
        """Returns GeminiResponse with both data and report."""
        return self.invoke(
            transcript_segments=transcript_segments,
            context_insights=context_insights,
        )
