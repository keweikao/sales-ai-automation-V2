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

from agents.agent2_sentiment import SentimentAttitudeAgent
from conftest import build_dummy_factory


def test_agent2_sentiment_analyze(sample_segments):
    dummy_payload = json.dumps(
        {
            "overall": "positive",
            "overallConfidence": 80,
            "trustLevel": 70,
            "engagementLevel": 65,
            "techAdoptionLevel": 55,
            "emotionCurve": [],
            "buyingSignals": [],
            "objectionSignals": [],
        }
    )
    recorded_prompts = []
    agent = SentimentAttitudeAgent(
        model_factory=build_dummy_factory(dummy_payload, recorded_prompts)
    )

    result = agent.analyze(
        transcript_segments=sample_segments,
        participant_insights={
            "participants": [
                {"speakerId": "Speaker 1", "role": "業務"},
                {"speakerId": "Speaker 2", "role": "老闆"},
            ]
        },
        conversation_metadata={"caseId": "CASE-002"},
    )

    assert result["overall"] == "positive"
    assert recorded_prompts, "Model invocation should record prompt content"
    prompt = recorded_prompts[0]
    assert "Speaker 2" in prompt
    assert "參與者角色" in prompt
    assert "CASE-002" in prompt
