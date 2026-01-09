"""
Agent 1 - Context & Structure (The Scanner).

Analyzes meeting background, participants, and overall conversation structure.

Migration note: From analysis-service/src/agents/agent1_context.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .base import GeminiJSONAgent, render_transcript

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "agent1-context.md"


class ContextAgent(GeminiJSONAgent):
    """Agent 1 - Context & Structure (The Scanner)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(prompt_path=PROMPT_PATH, **kwargs)

    # pylint: disable=arguments-differ
    def build_prompt(  # type: ignore[override]
        self,
        *,
        transcript_segments: Iterable[Dict[str, Any]],
        demo_meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        transcript_block = render_transcript(transcript_segments)

        # Build demo_meta section if available
        demo_meta_section = ""
        if demo_meta:
            demo_meta_section = f"""
=== Demo Meta (業務填寫的客觀資訊) ===
店型 (storeType): {demo_meta.get('storeType', '未提供')}
營運型態 (serviceType): {demo_meta.get('serviceType', '未提供')}
老闆本人在場 (decisionMakerOnsite): {demo_meta.get('decisionMakerOnsite', '未提供')}
現有 POS 系統 (currentPos): {demo_meta.get('currentPos', '未提供')}
"""

        return (
            self.prompt_template
            + f"\n\n{demo_meta_section}"
            + f"\n\n=== Transcript ===\n{transcript_block}"
        )

    def analyze(
        self,
        *,
        transcript_segments: Iterable[Dict[str, Any]],
        demo_meta: Optional[Dict[str, Any]] = None,
    ):
        """Returns GeminiResponse with both data and report."""
        return self.invoke(
            transcript_segments=transcript_segments,
            demo_meta=demo_meta,
        )
