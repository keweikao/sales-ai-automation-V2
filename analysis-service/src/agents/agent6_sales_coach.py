from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .base import (
    GeminiJSONAgent,
    GeminiClientError,
    render_transcript,
)

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "agent6-coach.md"


def _json_serializer(obj: Any) -> Any:
    """Serialize datetime-like objects for json.dumps."""
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


def _ensure_agent_outputs(agent_outputs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return agent outputs with only serializable entries."""
    if not agent_outputs:
        return {}
    return {key: value for key, value in agent_outputs.items() if value is not None}


class SalesCoachAgent(GeminiJSONAgent):
    """Agent 6 - Sales Coach Synthesizer."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(prompt_path=PROMPT_PATH, **kwargs)

    # pylint: disable=arguments-differ
    def build_prompt(  # type: ignore[override]
        self,
        *,
        agent_outputs: Optional[Dict[str, Any]] = None,
        transcript_segments: Optional[Iterable[Dict[str, Any]]] = None,
        transcript_text: Optional[str] = None,
        case_metadata: Optional[Dict[str, Any]] = None,
        conversation_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        transcript_block = ""
        if transcript_text:
            transcript_block = transcript_text.strip()
        elif transcript_segments:
            transcript_block = render_transcript(transcript_segments)

        if not transcript_block:
            transcript_block = "（無對話內容）"

        context_payload = {
            "caseMetadata": case_metadata or {},
            "conversationMetadata": conversation_metadata or {},
            "agentOutputs": _ensure_agent_outputs(agent_outputs),
        }

        context_block = json.dumps(
            context_payload,
            ensure_ascii=False,
            indent=2,
            default=_json_serializer,
        )

        sections = [
            self.prompt_template.strip(),
            "\n\n=== Case Context (JSON) ===\n",
            context_block,
            "\n\n=== Transcript ===\n",
            transcript_block,
        ]

        return "".join(sections).strip()

    def analyze(
        self,
        *,
        agent_outputs: Optional[Dict[str, Any]] = None,
        transcript_segments: Optional[Iterable[Dict[str, Any]]] = None,
        transcript_text: Optional[str] = None,
        case_metadata: Optional[Dict[str, Any]] = None,
        conversation_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run prompt and return structured + rawOutput payload."""
        if not transcript_text and not transcript_segments:
            raise ValueError("SalesCoachAgent 需要提供 transcript_text 或 transcript_segments。")

        response = self.invoke(
            agent_outputs=agent_outputs,
            transcript_segments=transcript_segments,
            transcript_text=transcript_text,
            case_metadata=case_metadata,
            conversation_metadata=conversation_metadata,
        )

        payload = response.data
        if "structured" not in payload or "rawOutput" not in payload:
            raise GeminiClientError("Agent 6 回應缺少 structured/rawOutput 欄位。")
        return payload
