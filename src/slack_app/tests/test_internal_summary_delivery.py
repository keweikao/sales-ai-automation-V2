import json
from types import SimpleNamespace

import pytest

from slack_app import main as slack_main
from slack_app.notifications.summary_delivery import DeliveryResult


class DummyDeliveryService:
    def __init__(self):
        self.calls = []

    def send_summary(self, case_id, initiated_by, phone_number=None):
        self.calls.append((case_id, initiated_by, phone_number))
        return DeliveryResult(
            status="sent",
            summary_url="https://sho.rt/demo123",
            phone=phone_number,
        )


@pytest.fixture(autouse=True)
def setup_service(monkeypatch):
    fake_service = DummyDeliveryService()
    monkeypatch.setattr(slack_main, "summary_delivery_service", fake_service)
    monkeypatch.setattr(
        slack_main, "_notify_summary_delivery_result", lambda *args, **kwargs: None
    )
    return fake_service


def test_internal_summary_delivery_endpoint(monkeypatch, setup_service):
    from slack_app import main as slack_main
    slack_main.SUMMARY_INTERNAL_TOKEN = "shared-token"
    with slack_main.flask_app.test_client() as client:
        response = client.post(
            "/internal/summary-delivery",
            data=json.dumps(
                {
                    "caseId": "CASE999",
                    "phone": "+886900000000",
                    "initiatedBy": "U12345",
                    "channelId": "D123",
                    "threadTs": "111.222",
                }
            ),
            headers={"Content-Type": "application/json", "X-Progress-Token": "shared-token"},
        )

    assert response.status_code == 200
    assert setup_service.calls == [("CASE999", "U12345", "+886900000000")]
