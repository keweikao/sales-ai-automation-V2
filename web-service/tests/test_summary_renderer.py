from types import SimpleNamespace
from pathlib import Path
import sys
import types

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

if "markdown" not in sys.modules:
    sys.modules["markdown"] = types.SimpleNamespace(  # type: ignore
        markdown=lambda text, extensions=None: text
    )

from summary_renderer import (  # type: ignore  # pylint: disable=wrong-import-position
    SummaryNotFoundError,
    SummaryRenderer,
    SummaryUnavailableError,
)


class DummyDoc:
    def __init__(self, data):
        self._data = data
        self.exists = data is not None

    def get(self, transaction=None):
        return self

    def to_dict(self):
        return self._data

    def update(self, payload):
        self.last_update = payload


class DummyCollection:
    def __init__(self, store):
        self.store = store

    def document(self, case_id):
        return DummyDoc(self.store.get(case_id))


class DummyDB:
    def __init__(self, store):
        self.store = store

    def collection(self, name):
        assert name == "cases"
        return DummyCollection(self.store)

    def transaction(self):
        return SimpleNamespace()


def test_build_context_success():
    case_data = {
        "customerName": "麻辣燙",
        "createdAt": "2025-11-12T06:24:35+00:00",
        "salesRepName": "Stephen",
        "analysis": {
            "customerSummary": {
                "summary": "短摘要",
                "markdown": "## 標題\n- 項目 1",
                "keyDecisions": [{"title": "導入掃碼", "quote": "盡快導入"}],
                "nextSteps": {
                    "customer": [{"description": "回覆報價", "owner": "Eileen"}],
                    "ichef": [{"description": "提供SOP", "owner": "iCHEF"}],
                },
                "contacts": {"customer": "Eileen"},
            }
        },
    }
    renderer = SummaryRenderer(db_client=DummyDB({"CASE123": case_data}))

    context = renderer.build_context("CASE123")

    assert context.customer_name == "麻辣燙"
    assert "項目" in context.summary_html
    assert context.key_decisions[0]["title"] == "導入掃碼"
    assert context.next_steps_customer


def test_build_context_missing_case():
    renderer = SummaryRenderer(db_client=DummyDB({}))
    with pytest.raises(SummaryNotFoundError):
        renderer.build_context("UNKNOWN")


def test_build_context_missing_summary():
    renderer = SummaryRenderer(db_client=DummyDB({"CASE1": {"analysis": {}}}))
    with pytest.raises(SummaryUnavailableError):
        renderer.build_context("CASE1")
