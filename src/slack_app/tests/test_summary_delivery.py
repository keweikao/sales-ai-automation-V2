import os
from types import SimpleNamespace
from typing import Any, Dict

import pytest

from slack_app.notifications.summary_delivery import SummaryDeliveryService


class FakeDocRef:
    def __init__(self, data):
        self.data = data
        self.updates = []

    def get(self):
        return SimpleNamespace(exists=self.data is not None, to_dict=lambda: self.data)

    def update(self, payload):
        self.updates.append(payload)


class FakeCollection:
    def __init__(self, doc):
        self.doc = doc

    def document(self, case_id):
        return self.doc


class FakeShortDocRef:
    def __init__(self, store, code):
        self.store = store
        self.code = code

    def get(self):
        data = self.store.get(self.code)
        return SimpleNamespace(exists=data is not None, to_dict=lambda: data)

    def set(self, payload):
        self.store[self.code] = payload


class FakeShortCollection:
    def __init__(self, store):
        self.store = store

    def document(self, code):
        return FakeShortDocRef(self.store, code)


class FakeDB:
    def __init__(self, data):
        self.doc = FakeDocRef(data)
        self.short_urls: Dict[str, Dict[str, Any]] = {}

    def collection(self, name):
        if name == "cases":
            return FakeCollection(self.doc)
        if name == "shortUrls":
            return FakeShortCollection(self.short_urls)
        raise AssertionError(f"Unexpected collection {name}")


@pytest.fixture(autouse=True)
def clear_twilio_env(monkeypatch):
    for key in [
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_PHONE_NUMBER",
        "SHORT_URL_BASE",
        "SUMMARY_BASE_URL",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_summary_delivery_skipped_without_twilio():
    case_data = {
        "salesRepName": "測試顧問",
        "customerPhone": "+886912345678",
        "delivery": {},
    }
    fake_db = FakeDB(case_data)
    service = SummaryDeliveryService(fake_db, summary_base_url="https://example.com")

    result = service.send_summary("CASE123", initiated_by="U123")

    assert result.status == "skipped"
    assert result.summary_url.startswith("https://example.com")
    assert "/s/" in result.summary_url
    assert fake_db.doc.updates, "Firestore update should be recorded"
    update_payload = fake_db.doc.updates[-1]
    assert update_payload["delivery.customerPhone"] == "+886912345678"
    assert update_payload["delivery.smsStatus"] == "skipped"
    assert update_payload["delivery.confirmedBy"] == "U123"
    assert fake_db.short_urls, "short url documents should be created"
    assert update_payload["delivery.summaryPageUrl"].endswith("/summary/CASE123")


def test_summary_delivery_invalid_phone():
    case_data = {
        "salesRepName": "測試顧問",
        "customerPhone": "+886912345678",
        "delivery": {},
    }
    fake_db = FakeDB(case_data)
    service = SummaryDeliveryService(fake_db, summary_base_url="https://example.com")

    with pytest.raises(ValueError):
        service.send_summary("CASE123", initiated_by="U123", phone_number="abc")


def test_summary_delivery_short_url_creation():
    case_data = {
        "salesRepName": "測試顧問",
        "customerPhone": "+886912345678",
        "delivery": {},
    }
    fake_db = FakeDB(case_data)
    service = SummaryDeliveryService(
        fake_db,
        summary_base_url="https://example.com",
        short_url_base="https://sho.rt"
    )

    result = service.send_summary("CASE123", initiated_by="U123")

    assert result.summary_url.startswith("https://sho.rt/")
    assert fake_db.short_urls, "shortUrls collection should be populated"
