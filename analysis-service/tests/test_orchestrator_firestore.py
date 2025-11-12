from __future__ import annotations

from typing import Any, Dict, List
from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parents[1]
MODULE_ROOT = REPO_ROOT / "analysis-service"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from src.orchestrator import AgentResult, MultiAgentOrchestrator


class FakeDocumentRef:
    """Minimal Firestore document stub."""

    def __init__(self) -> None:
        self.set_calls: List[Dict[str, Any]] = []

    def set(self, data: Dict[str, Any], merge: bool = False) -> None:  # pylint: disable=unused-argument
        self.set_calls.append({"data": data, "merge": merge})


class FakeCollectionRef:
    """Minimal Firestore collection stub."""

    def __init__(self, doc_ref: FakeDocumentRef) -> None:
        self.doc_ref = doc_ref
        self.last_case_id: str | None = None

    def document(self, case_id: str) -> FakeDocumentRef:
        self.last_case_id = case_id
        return self.doc_ref


class FakeFirestore:
    """Minimal Firestore client stub exposing only collection().document()."""

    def __init__(self) -> None:
        self.doc_ref = FakeDocumentRef()
        self.collection_name: str | None = None

    def collection(self, name: str) -> FakeCollectionRef:
        self.collection_name = name
        return FakeCollectionRef(self.doc_ref)


def test_persist_agent6_results_writes_structured_and_metadata():
    fake_db = FakeFirestore()
    orchestrator = MultiAgentOrchestrator(db_client=fake_db)
    result = AgentResult(
        agent_id="agent6",
        success=True,
        data={
            "structured": {"salesStage": "需要證明型", "dealHealth": {"score": 82}},
            "rawOutput": "## 30秒快速掃描",
        },
        duration=12.5,
        retry_count=1,
    )

    orchestrator._persist_agent6_results("CASE-AGT6", result)

    assert fake_db.doc_ref.set_calls, "Expected Firestore set to be invoked"
    payload = fake_db.doc_ref.set_calls[0]["data"]["analysis"]
    assert payload["structured"]["salesStage"] == "需要證明型"
    assert payload["rawOutput"] == "## 30秒快速掃描"
    agent6_meta = payload["agents"]["agent6"]
    assert agent6_meta["status"] == "success"
    assert agent6_meta["retryCount"] == 1
    assert agent6_meta["data"]["structured"]["dealHealth"]["score"] == 82


def test_persist_agent7_results_shapes_customer_summary():
    fake_db = FakeFirestore()
    orchestrator = MultiAgentOrchestrator(db_client=fake_db)
    result = AgentResult(
        agent_id="agent7",
        success=True,
        data={
            "customerSummary": {
                "summary": "張總確認導入掃碼點餐。",
                "keyDecisions": [{"title": "導入掃碼", "speakerId": "Speaker 2"}],
            },
            "markdown": "## 摘要\n- 張總確認導入掃碼點餐。",
        },
        duration=8.2,
        retry_count=0,
    )

    orchestrator._persist_agent7_results("CASE-AGT7", result)

    assert fake_db.doc_ref.set_calls, "Expected Firestore set to be invoked"
    payload = fake_db.doc_ref.set_calls[0]["data"]["analysis"]

    summary = payload["customerSummary"]
    assert summary["summary"] == "張總確認導入掃碼點餐。"
    assert summary["markdown"].startswith("## 摘要")
    assert summary["originalMarkdown"].startswith("## 摘要")
    assert summary["isEdited"] is False
    assert summary["editCount"] == 0

    agent7_meta = payload["agents"]["agent7"]
    assert agent7_meta["status"] == "success"
    assert agent7_meta["data"]["customerSummary"]["keyDecisions"][0]["title"] == "導入掃碼"
