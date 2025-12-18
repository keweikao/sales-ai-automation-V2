from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .base import GeminiJSONAgent, render_transcript

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "agent4-summary.md"


class SummaryAgent(GeminiJSONAgent):
    """Agent 4 - The Recap (Customer Summary).
    
    Only uses transcript for analysis, no dependency on other agents.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(prompt_path=PROMPT_PATH, **kwargs)

    # pylint: disable=arguments-differ
    def build_prompt(  # type: ignore[override]
        self,
        *,
        transcript_segments: Iterable[Dict[str, Any]],
        context_insights: Optional[Dict[str, Any]] = None,  # Made optional, not used
    ) -> str:
        transcript_block = render_transcript(transcript_segments)

        # Only use transcript, ignore context_insights
        return (
            self.prompt_template
            + f"\n\n=== Transcript ===\n{transcript_block}"
        )

    def analyze(
        self,
        *,
        transcript_segments: Iterable[Dict[str, Any]],
        context_insights: Optional[Dict[str, Any]] = None,  # Made optional
    ):
        """Returns GeminiResponse with both data and report.
        
        Only uses transcript_segments for analysis.
        """
        return self.invoke(
            transcript_segments=transcript_segments,
            context_insights=context_insights,  # Passed but not used in build_prompt
        )
