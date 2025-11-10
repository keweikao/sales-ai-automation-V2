from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .base import GeminiJSONAgent, render_transcript

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "agent5-questionnaire.md"


def json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _format_questionnaire(questionnaire: Optional[List[Dict[str, Any]]]) -> str:
    if not questionnaire:
        return "（未提供問卷題目）"
    payload = [
        {"question": q.get("question"), "options": q.get("options")}
        for q in questionnaire
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _serialize_optional_context(
    label: str,
    payload: Optional[Dict[str, Any]],
) -> str:
    if not payload:
        return f"（未提供{label}）"
    return json.dumps(payload, ensure_ascii=False, indent=2, default=json_serializer)


class QuestionnaireAgent(GeminiJSONAgent):
    """Agent 5 - Questionnaire Agent."""

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
        questionnaire: Optional[List[Dict[str, Any]]] = None,
        conversation_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        transcript_block = render_transcript(transcript_segments) or "（無對話內容）"
        questionnaire_block = _format_questionnaire(questionnaire)
        participant_block = _serialize_optional_context("參與者洞察", participant_insights)
        sentiment_block = _serialize_optional_context("情緒洞察", sentiment_insights)
        needs_block = _serialize_optional_context("產品需求彙整", product_needs)

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
            "\n\n=== 參與者洞察（Agent 1） ===\n",
            participant_block,
            "\n\n=== 情緒洞察（Agent 2，可選） ===\n",
            sentiment_block,
            "\n\n=== 產品需求彙整（Agent 3，可選） ===\n",
            needs_block,
            "\n\n=== 問卷題目（若有） ===\n",
            questionnaire_block,
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
        questionnaire: Optional[List[Dict[str, Any]]] = None,
        conversation_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        response = self.invoke(
            transcript_segments=transcript_segments,
            participant_insights=participant_insights,
            sentiment_insights=sentiment_insights,
            product_needs=product_needs,
            questionnaire=questionnaire,
            conversation_metadata=conversation_metadata,
        )
        return response.data
