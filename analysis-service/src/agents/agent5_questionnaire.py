from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .base import GeminiJSONAgent, render_transcript

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "agent5-questionnaire.md"


def _serialize_context(label: str, payload: Optional[Dict[str, Any]]) -> str:
    if not payload:
        return f"（未提供{label}）"
    return json.dumps(payload, ensure_ascii=False, indent=2)


class DiscoveryQuestionnaireAgent(GeminiJSONAgent):
    """Agent 5 - Discovery Questionnaire Analyzer."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(prompt_path=PROMPT_PATH, **kwargs)

    # pylint: disable=arguments-differ
    def build_prompt(  # type: ignore[override]
        self,
        *,
        transcript_segments: Iterable[Dict[str, Any]],
        participant_insights: Optional[Dict[str, Any]] = None,
        sentiment_insights: Optional[Dict[str, Any]] = None,
        product_needs: Optional[Dict[str, Any]] = None,
        conversation_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        transcript_block = render_transcript(transcript_segments) or "（無對話內容）"
        participant_block = _serialize_context("參與者資訊", participant_insights)
        sentiment_block = _serialize_context("情緒與態度", sentiment_insights)
        needs_block = _serialize_context("產品需求（Agent 3）", product_needs)

        metadata_json = ""
        if conversation_metadata:
            metadata_json = json.dumps(
                conversation_metadata, ensure_ascii=False, indent=2
            )

        sections = [
            self.prompt_template.strip(),
            "\n\n=== 參與者資訊（Agent 1，可選） ===\n",
            participant_block,
            "\n\n=== 情緒洞察（Agent 2，可選） ===\n",
            sentiment_block,
            "\n\n=== 產品需求彙整（Agent 3，可選） ===\n",
            needs_block,
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
        sentiment_insights: Optional[Dict[str, Any]] = None,
        product_needs: Optional[Dict[str, Any]] = None,
        conversation_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        response = self.invoke(
            transcript_segments=transcript_segments,
            participant_insights=participant_insights,
            sentiment_insights=sentiment_insights,
            product_needs=product_needs,
            conversation_metadata=conversation_metadata,
        )
        return response.data
