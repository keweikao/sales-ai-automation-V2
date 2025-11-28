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

from agents.agent3_needs import ProductNeedsAgent
from .conftest import build_dummy_factory


def test_agent3_product_needs_analyze(sample_segments):
    dummy_payload = json.dumps(
        {
            "explicitNeeds": [],
            "implicitNeeds": [],
            "recommendedProducts": [],
            "budget": {
                "mentioned": False,
                "value": "未提及",
                "flexibility": "unknown",
                "paymentPreference": "未提及",
                "budgetReason": "",
            },
            "decisionTimeline": {
                "urgency": "unknown",
                "expectedDecisionDate": "未提及",
                "drivers": [],
                "timelineReason": "",
            },
            "priceAnchors": [],
            "priceSensitivity": {
                "level": "low",
                "evidence": [],
                "sensitivityReason": "",
            },
            "productQuestions": [],
        }
    )
    recorded_prompts = []
    agent = ProductNeedsAgent(
        model_factory=build_dummy_factory(dummy_payload, recorded_prompts)
    )

    result = agent.analyze(
        transcript_segments=sample_segments,
        participant_insights={"participants": [{"speakerId": "Speaker 2", "role": "老闆"}]},
        sentiment_insights={"overall": "neutral"},
        conversation_metadata={"caseId": "CASE-003"},
    )

    assert "budget" in result
    assert recorded_prompts, "Prompt should be captured for inspection"
    prompt = recorded_prompts[0]
    assert "情緒與態度" in prompt
    assert "CASE-003" in prompt
