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

from agents.agent1_participant import ParticipantProfileAgent
from .conftest import build_dummy_factory


def test_agent1_participant_analyze(sample_segments):
    dummy_payload = json.dumps(
        {
            "participants": [
                {
                    "speakerId": "Speaker 1",
                    "role": "老闆/決策者",
                    "roleConfidence": 90,
                    "roleReason": "主導導入時程。",
                    "personalityType": "driver",
                    "decisionPower": 95,
                    "influenceLevel": "primary",
                    "concerns": [{"concern": "流程效率", "keyPhrases": ["點餐太慢"]}],
                    "interests": ["提升效率"],
                }
            ]
        }
    )
    recorded_prompts = []
    agent = ParticipantProfileAgent(
        model_factory=build_dummy_factory(dummy_payload, recorded_prompts)
    )

    result = agent.analyze(
        transcript_segments=sample_segments,
        speaker_statistics={"Speaker 1": 60.0, "Speaker 2": 40.0},
        conversation_metadata={"caseId": "CASE-001"},
    )

    assert result["participants"][0]["speakerId"] == "Speaker 1"
    assert recorded_prompts, "Model invocation should record prompt content"
    prompt = recorded_prompts[0]
    assert "Speaker 1" in prompt
    assert "發言占比" in prompt
    assert "CASE-001" in prompt
