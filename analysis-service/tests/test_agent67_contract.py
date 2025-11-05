import json
from pathlib import Path

import pytest


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "agent67"

AGENT6_FIXTURES = [
    "agent6_structured.json",
    "agent6_structured_negative.json",
    "agent6_structured_insufficient.json",
]

AGENT7_FIXTURES = [
    "agent7_summary.json",
    "agent7_summary_negative.json",
    "agent7_summary_insufficient.json",
]

SUMMARY_KEYWORDS = {
    "agent7_summary.json": ["掃碼點餐", "月費", "參訪"],
    "agent7_summary_negative.json": ["成本", "試用", "顧問"],
    "agent7_summary_insufficient.json": ["初次", "問卷", "探索"],
}


def load_json(name: str):
    with (FIXTURE_DIR / name).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def require_keys(data: dict, keys):
    for key in keys:
        assert key in data, f"Missing required key: {key}"


@pytest.mark.parametrize("fixture_name", AGENT6_FIXTURES)
def test_agent6_structured_schema(fixture_name):
    payload = load_json(fixture_name)
    structured = payload["structured"]

    require_keys(
        structured,
        [
            "keyDecisionMaker",
            "dealHealth",
            "recommendedBundle",
            "competitivePositioning",
            "salesStage",
            "maximumRisk",
            "nextActions",
            "talkTracks",
            "repFeedback",
        ],
    )

    kdm = structured["keyDecisionMaker"]
    require_keys(kdm, ["name", "role", "primaryConcerns"])
    assert isinstance(kdm["primaryConcerns"], list) and kdm["primaryConcerns"], "primaryConcerns must be non-empty list"

    deal = structured["dealHealth"]
    require_keys(deal, ["score", "sentiment", "reasoning"])
    assert isinstance(deal["score"], int) and 0 <= deal["score"] <= 100
    assert deal["sentiment"] in {"positive", "neutral", "negative"}

    bundle = structured["recommendedBundle"]
    require_keys(
        bundle,
        ["products", "pricingStrategy", "pricingDirection", "referencePoint", "totalEstimate", "pricingNotes"],
    )
    assert isinstance(bundle["products"], list) and bundle["products"], "products must be non-empty list"
    assert bundle["pricingDirection"] in {"below_baseline", "match_baseline", "above_baseline"}

    total_estimate = bundle["totalEstimate"]
    require_keys(total_estimate, ["currency", "min", "max", "notes"])
    assert isinstance(total_estimate["min"], int) and isinstance(total_estimate["max"], int)
    assert total_estimate["min"] <= total_estimate["max"], "totalEstimate min must be <= max"

    pricing_notes = bundle["pricingNotes"]
    assert isinstance(pricing_notes, list) and pricing_notes, "pricingNotes must not be empty"
    for note in pricing_notes:
        require_keys(note, ["type", "detail", "evidence"])
        assert note["type"] in {"software", "hardware"}

    assert structured["salesStage"] in {"立即報價型", "需要證明型", "教育培養型", "時機未到型"}

    max_risk = structured["maximumRisk"]
    require_keys(max_risk, ["risk", "mitigation"])

    next_actions = structured["nextActions"]
    assert isinstance(next_actions, list) and len(next_actions) == 3, "nextActions must contain exactly 3 entries"
    priorities = {action.get("priority") for action in next_actions}
    assert priorities == {1, 2, 3}, "nextActions priorities must be 1, 2, 3"
    for action in next_actions:
        require_keys(action, ["action", "deadline", "priority"])
        assert action["action"], "action description must not be empty"

    talk_tracks = structured["talkTracks"]
    assert isinstance(talk_tracks, list) and len(talk_tracks) >= 2, "talkTracks must contain at least two entries"
    for track in talk_tracks:
        require_keys(track, ["situation", "response"])

    feedback = structured["repFeedback"]
    require_keys(feedback, ["strengths", "improvements"])
    assert len(feedback["strengths"]) >= 2
    assert len(feedback["improvements"]) >= 2

    # rawOutput sanity check
    assert "rawOutput" in payload
    assert payload["rawOutput"].startswith("## 30秒快速掃描")


@pytest.mark.parametrize("fixture_name", AGENT7_FIXTURES)
def test_agent7_summary_schema_and_markdown(fixture_name):
    payload = load_json(fixture_name)
    require_keys(payload, ["customerSummary", "markdown"])

    summary = payload["customerSummary"]
    require_keys(summary, ["summary", "keyDecisions", "nextSteps", "upcomingMilestone", "contacts"])

    assert isinstance(summary["keyDecisions"], list) and len(summary["keyDecisions"]) >= 2
    for decision in summary["keyDecisions"]:
        require_keys(decision, ["title", "speakerId", "timestamp", "quote"])

    next_steps = summary["nextSteps"]
    require_keys(next_steps, ["customer", "ichef"])
    assert next_steps["customer"], "customer next steps must not be empty"
    assert next_steps["ichef"], "ichef next steps must not be empty"
    for owner_list in (next_steps["customer"], next_steps["ichef"]):
        for item in owner_list:
            require_keys(item, ["description", "owner", "dueDate"])
            assert item["description"]
            assert item["owner"]

    milestone = summary["upcomingMilestone"]
    require_keys(milestone, ["status", "date", "note"])
    assert milestone["status"] in {"scheduled", "proposed", "pending"}

    contacts = summary["contacts"]
    for party in ["customer", "ichef"]:
        require_keys(contacts[party], ["name", "role", "email", "phone"])

    markdown = payload["markdown"]
    required_sections = ["## 摘要", "## 重點決議", "## 待跟進事項", "## 下一步", "## 聯絡窗口"]
    for section in required_sections:
        assert section in markdown, f"Markdown missing section: {section}"

    # Ensure markdown references key decisions
    for decision in summary["keyDecisions"]:
        quote = decision["quote"]
        assert quote[:10] in markdown, "Markdown should include decision quotes for traceability"

    # Ensure summary highlights appear in markdown bullets
    key_phrases = SUMMARY_KEYWORDS[fixture_name]
    for phrase in key_phrases:
        assert phrase in markdown, f"Markdown should mention core summary phrase: {phrase}"
