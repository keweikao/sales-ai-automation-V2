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

from agents.agent5_questionnaire import QuestionnaireAgent
from .conftest import build_dummy_factory


def test_agent5_questionnaire_analyze(sample_segments):
    dummy_payload = json.dumps(
        {
            "discoveryQuestionnaires": [
                {
                    "topic": "掃碼點餐",
                    "featureCategory": "點餐與訂單管理",
                    "currentStatus": "未使用",
                    "statusReason": "目前仍靠紙本點餐",
                    "motivationSummary": "想減少尖峰時段人力壓力",
                    "hasNeed": True,
                    "hasNeedReason": "尖峰時段多次抱怨人手不足",
                    "needReasons": [],
                    "noNeedReasons": [],
                    "perceivedValue": {
                        "score": 70,
                        "aspects": [],
                        "valueReason": ""
                    },
                    "implementationWillingness": "medium",
                    "willingnessReason": "希望先參考案例",
                    "barriers": [],
                    "timeline": {
                        "consideration": "3 個月內",
                        "urgency": "medium",
                        "timelineReason": ""
                    },
                    "coverageAssessment": {
                        "positiveEvidence": 50,
                        "negativeEvidence": 20,
                        "verdict": "positive_dominant",
                        "comment": "正向證據較多"
                    },
                    "completenessScore": 65,
                    "completenessReason": "主要欄位皆有提及",
                    "additionalContext": "待安排演示",
                    "quotes": ["尖峰時段人手不足"]
                }
            ]
        }
    )
    recorded_prompts = []
    agent = DiscoveryQuestionnaireAgent(
        model_factory=build_dummy_factory(dummy_payload, recorded_prompts)
    )

    result = agent.analyze(
        transcript_segments=sample_segments,
        participant_insights={"participants": [{"speakerId": "Speaker 2", "role": "老闆"}]},
        sentiment_insights={"overall": "positive"},
        product_needs={"explicitNeeds": []},
        conversation_metadata={"caseId": "CASE-005"},
    )

    assert result["discoveryQuestionnaires"][0]["topic"] == "掃碼點餐"
    prompt = recorded_prompts[0]
    assert "產品需求彙整" in prompt
    assert "CASE-005" in prompt
