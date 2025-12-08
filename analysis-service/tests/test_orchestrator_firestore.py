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


def test_persist_agent3_results_writes_seller_data():
    fake_db = FakeFirestore()
    orchestrator = MultiAgentOrchestrator(db_client=fake_db)
    result = AgentResult(
        agent_id="agent3",
        success=True,
        data={
            "salesCoach": {
                "strengths": ["Clear value prop"],
                "improvements": ["Ask more questions"]
            }
        },
        duration=12.5,
        retry_count=1,
    )

    orchestrator._persist_agent3_results("CASE-AGT3", result)

    assert fake_db.doc_ref.set_calls, "Expected Firestore set to be invoked"
    payload = fake_db.doc_ref.set_calls[0]["data"]["analysis"]
    
    agent3_meta = payload["agents"]["agent3"]
    assert agent3_meta["status"] == "success"
    assert agent3_meta["retryCount"] == 1
    assert agent3_meta["data"]["salesCoach"]["strengths"][0] == "Clear value prop"


def test_persist_agent4_results_writes_summary_data():
    fake_db = FakeFirestore()
    orchestrator = MultiAgentOrchestrator(db_client=fake_db)
    result = AgentResult(
        agent_id="agent4",
        success=True,
        data={
            "subject": "Meeting Summary",
            "summary": "Discussed pricing.",
            "actionItems": ["Send quote"]
        },
        duration=8.2,
        retry_count=0,
    )

    orchestrator._persist_agent4_results("CASE-AGT4", result)

    assert fake_db.doc_ref.set_calls, "Expected Firestore set to be invoked"
    payload = fake_db.doc_ref.set_calls[0]["data"]["analysis"]

    # Check top-level customerSummary
    summary = payload["customerSummary"]
    assert summary["subject"] == "Meeting Summary"
    assert summary["summary"] == "Discussed pricing."

    # Check agent metadata
    agent4_meta = payload["agents"]["agent4"]
    assert agent4_meta["status"] == "success"
    assert agent4_meta["data"]["subject"] == "Meeting Summary"
