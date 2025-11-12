from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

CURRENT_DIR = Path(__file__).resolve().parent
MODULE_ROOT = CURRENT_DIR.parents[1] / "analysis-service" / "src"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from agents.agent7_customer_summary import CustomerSummaryAgent
from conftest import build_dummy_factory


@pytest.fixture
def agent7_dummy_payload():
    """Provides a dummy JSON payload for Agent 7."""
    return json.dumps(
        {
            "customerSummary": {
                "summary": "這次會議主要是討論 POS 系統的升級方案。",
                "keyDecisions": [
                    {
                        "title": "決定升級",
                        "speakerId": "Speaker 1",
                        "timestamp": "00:10:25",
                        "quote": "我們決定就用這套方案了。",
                    }
                ],
                "nextSteps": {
                    "customer": [{"description": "提供硬體規格", "owner": "張總", "dueDate": "2025-11-10"}],
                    "ichef": [{"description": "提供報價單", "owner": "iCHEF業務", "dueDate": "2025-11-08"}],
                },
                "upcomingMilestone": {"status": "scheduled", "date": "2025-11-15", "note": "簽約"},
                "contacts": {
                    "customer": {"name": "張總", "role": "老闆", "email": None, "phone": None},
                    "ichef": {"name": "iCHEF業務", "role": "銷售顧問", "email": None, "phone": None},
                },
            },
            "markdown": "## 摘要...",
        }
    )


def test_agent7_customer_summary_analyze(sample_segments, agent7_dummy_payload):
    """
    Tests the analyze method of CustomerSummaryAgent to ensure it builds the correct
    prompt and parses the response, without dependency on other agents.
    """
    recorded_prompts = []
    agent = CustomerSummaryAgent(
        model_factory=build_dummy_factory(agent7_dummy_payload, recorded_prompts)
    )

    result = agent.analyze(
        transcript_segments=sample_segments,
        case_metadata={"caseId": "CASE-007", "customer": {"storeName": "測試餐廳"}},
        conversation_metadata={"topic": "POS升級"},
    )

    # 1. Check if the output is parsed correctly
    assert "customerSummary" in result
    assert "markdown" in result
    assert result["customerSummary"]["summary"] == "這次會議主要是討論 POS 系統的升級方案。"

    # 2. Check if the prompt was built correctly
    assert recorded_prompts, "Model invocation should have recorded the prompt content"
    prompt = recorded_prompts[0]

    # 3. Verify prompt contains only the necessary information
    assert "CASE-007" in prompt
    assert "測試餐廳" in prompt
    assert "POS升級" in prompt
    assert "大家好，感謝今天參與。" in prompt  # from sample_segments

    # 4. Verify prompt does NOT contain other agent outputs
    assert "agentOutputs" not in prompt
    assert "agent1_participant" not in prompt
    assert "agent6_sales_coach" not in prompt
