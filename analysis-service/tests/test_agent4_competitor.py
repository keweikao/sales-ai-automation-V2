from __future__ import annotations

import json
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
MODULE_ROOT = CURRENT_DIR.parents[1] / "analysis-service" / "src"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from agents.agent4_competitor import CompetitorIntelligenceAgent
from conftest import build_dummy_factory


def test_agent4_competitor_analyze(sample_segments):
    dummy_payload = json.dumps(
        {
            "competitors": [
                {
                    "name": "Eats365",
                    "mentionCount": 2,
                    "contexts": ["提到 Eats365 價格較低"],
                    "customerOpinion": {
                        "pros": ["價格便宜"],
                        "cons": ["功能不足"],
                        "satisfactionScore": 55,
                        "satisfactionReason": "雖然便宜但功能不足",
                    },
                    "relationshipStatus": "evaluating",
                    "ourAdvantages": ["功能完整"],
                    "winningStrategy": "強調整合與在地支援",
                    "winningStrategyReason": "客戶需要穩定操作與支援",
                    "conversionProbability": 70,
                    "conversionReason": "若能提供現場導入支援就會選擇",
                }
            ]
        }
    )
    recorded_prompts = []
    agent = CompetitorIntelligenceAgent(
        model_factory=build_dummy_factory(dummy_payload, recorded_prompts)
    )

    result = agent.analyze(
        transcript_segments=sample_segments,
        participant_insights={"participants": [{"speakerId": "Speaker 2", "role": "老闆"}]},
        sentiment_insights={"overall": "neutral"},
        conversation_metadata={"caseId": "CASE-004"},
    )

    assert result["competitors"][0]["name"] == "Eats365"
    prompt = recorded_prompts[0]
    assert "Eats365" not in prompt  # should rely on transcript only
    assert "參與者資訊" in prompt
    assert "CASE-004" in prompt
