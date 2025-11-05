from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .base import GeminiJSONAgent, render_transcript


PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "agent1-participant.md"


def _format_speaker_stats(stats: Optional[Dict[str, Any]]) -> str:
    if not stats:
        return "（未提供說話者發言占比）"

    lines = []
    for speaker, value in stats.items():
        if isinstance(value, dict):
            percentage = value.get("percentage") or value.get("ratio")
        else:
            percentage = value
        try:
            percentage = float(percentage)
            lines.append(f"- {speaker}: {percentage:.1f}%")
        except (TypeError, ValueError):
            lines.append(f"- {speaker}: {percentage}")
    return "\n".join(lines)


class ParticipantProfileAgent(GeminiJSONAgent):
    """Agent 1 - Participant Profile Analyzer."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(prompt_path=PROMPT_PATH, **kwargs)

    # pylint: disable=arguments-differ
    def build_prompt(  # type: ignore[override]
        self,
        *,
        transcript_segments: Iterable[Dict[str, Any]],
        speaker_statistics: Optional[Dict[str, Any]] = None,
        conversation_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        transcript_block = render_transcript(transcript_segments) or "（無對話內容）"
        stats_block = _format_speaker_stats(speaker_statistics)

        metadata_json = ""
        if conversation_metadata:
            metadata_json = json.dumps(
                conversation_metadata, ensure_ascii=False, indent=2
            )

        sections = [
            self.prompt_template.strip(),
            "\n\n=== 說話者發言占比 ===\n",
            stats_block,
            "\n\n=== 對話逐字稿 ===\n",
            transcript_block,
        ]

        if metadata_json:
            sections.extend(
                [
                    "\n\n=== 補充對話背景 ===\n",
                    metadata_json,
                ]
            )

        return "".join(sections).strip()

    def analyze(
        self,
        *,
        transcript_segments: Iterable[Dict[str, Any]],
        speaker_statistics: Optional[Dict[str, Any]] = None,
        conversation_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute Agent 1 and return the structured JSON payload.
        """
        response = self.invoke(
            transcript_segments=transcript_segments,
            speaker_statistics=speaker_statistics,
            conversation_metadata=conversation_metadata,
        )
        return response.data
