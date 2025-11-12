import json
import sys
from pathlib import Path

import pytest

CURRENT_DIR = Path(__file__).resolve().parent
MODULE_ROOT = CURRENT_DIR.parents[1] / "analysis-service" / "src"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from agents.agent6_sales_coach import SalesCoachAgent
from agents.base import GeminiResponse, GeminiClientError


def _load_agent_outputs() -> dict:
    fixture_path = (
        Path(__file__).resolve().parent / "samples" / "sample_agent_inputs.json"
    )
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    return payload["agentOutputs"]


def test_sales_coach_build_prompt_includes_context():
    agent = SalesCoachAgent(model_name="gemini-mock")
    prompt = agent.build_prompt(
        agent_outputs=_load_agent_outputs(),
        transcript_text="業務：你好\n張總：哈囉",
        case_metadata={"caseId": "CASE-XYZ", "customer": {"company": "Test"}},
    )
    assert "CASE-XYZ" in prompt
    assert "agentOutputs" in prompt
    assert "業務：" in prompt


def test_sales_coach_analyze_requires_transcript():
    agent = SalesCoachAgent(model_name="gemini-mock")
    with pytest.raises(ValueError):
        agent.analyze(agent_outputs={})


def test_sales_coach_analyze_parses_response(monkeypatch):
    agent = SalesCoachAgent(model_name="gemini-mock")

    def fake_invoke(self, **kwargs):  # pylint: disable=unused-argument
        return GeminiResponse(
            data={
                "structured": {"dealHealth": {"score": 80, "sentiment": "positive", "reasoning": "ok"}},
                "rawOutput": "## 30秒快速掃描\n- 測試",
            },
            raw_text="{}",
            prompt="PROMPT",
            model_name="gemini-mock",
        )

    monkeypatch.setattr(SalesCoachAgent, "invoke", fake_invoke)

    result = agent.analyze(
        agent_outputs=_load_agent_outputs(),
        transcript_text="示例逐字稿",
        case_metadata={"caseId": "CASE-XYZ"},
    )

    assert result["structured"]["dealHealth"]["score"] == 80
    assert result["rawOutput"].startswith("## 30秒")


def test_sales_coach_analyze_validates_required_keys(monkeypatch):
    agent = SalesCoachAgent(model_name="gemini-mock")

    def fake_invoke(self, **kwargs):  # pylint: disable=unused-argument
        return GeminiResponse(
            data={"structured": {}},
            raw_text="{}",
            prompt="PROMPT",
            model_name="gemini-mock",
        )

    monkeypatch.setattr(SalesCoachAgent, "invoke", fake_invoke)

    with pytest.raises(GeminiClientError):
        agent.analyze(agent_outputs={}, transcript_text="text")
