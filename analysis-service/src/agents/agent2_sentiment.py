from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .base import GeminiJSONAgent, render_transcript

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "agent2-sentiment.md"


def json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _format_participants(participant_insights: Optional[Dict[str, Any]]) -> str:
    if not participant_insights:
        return "（未提供參與者資訊）"
    participants = participant_insights.get("participants", [])
    payload = [
        {"name": p.get("name"), "role": p.get("role"), "company": p.get("company")}
        for p in participants
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2)


class SentimentAttitudeAgent(GeminiJSONAgent):
    """Agent 2 - Sentiment & Attitude Analyzer."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(prompt_path=PROMPT_PATH, **kwargs)

    # pylint: disable=arguments-differ
    def build_prompt(  # type: ignore[override]
        self,
        *,
        transcript_segments: Iterable[Dict[str, Any]],
        participant_insights: Optional[Dict[str, Any]] = None, # Changed from 'participants'
        conversation_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        transcript_block = render_transcript(transcript_segments) or "（無對話內容）"
        participant_block = _format_participants(participant_insights) # Use participant_insights

        metadata_json = ""
        if conversation_metadata:
            metadata_json = json.dumps(
                conversation_metadata,
                ensure_ascii=False,
                indent=2,
                default=json_serializer,
            )

        sections = [
            self.prompt_template.strip(),
            "\n\n=== 參與者資訊 ===\n",
            participant_block,
            "\n\n=== 對話逐字稿 ===\n",
            transcript_block,
        ]

        if metadata_json:
            sections.extend(
                [
                    "\n\n=== 補充背景 ===\n",
                    metadata_json,
                ]
            )

        return "".join(sections).strip()

    def analyze(
        self,
        *,
        transcript_segments: Iterable[Dict[str, Any]],
        participant_insights: Optional[Dict[str, Any]] = None,
        conversation_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        response = self.invoke(
            transcript_segments=transcript_segments,
            participant_insights=participant_insights, # Directly pass participant_insights
            conversation_metadata=conversation_metadata,
        )
        return response.data
