from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .base import GeminiJSONAgent, render_transcript

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "agent1-context.md"


class ContextAgent(GeminiJSONAgent):
    """Agent 1 - Context & Structure (The Scene)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(prompt_path=PROMPT_PATH, **kwargs)

    # pylint: disable=arguments-differ
    def build_prompt(  # type: ignore[override]
        self,
        *,
        transcript_segments: Iterable[Dict[str, Any]],
    ) -> str:
        transcript_block = render_transcript(transcript_segments)
        
        return self.prompt_template.replace(
            "{{TRANSCRIPT}}", transcript_block
        ) + f"\n\n=== Transcript ===\n{transcript_block}"

    def analyze(
        self,
        *,
        transcript_segments: Iterable[Dict[str, Any]],
    ):
        """Returns GeminiResponse with both data and report."""
        return self.invoke(
            transcript_segments=transcript_segments,
        )
