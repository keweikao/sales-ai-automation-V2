import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

# Stub Slack dependencies if not installed
SLACK_APP_DIR = Path(__file__).resolve().parents[1]
if str(SLACK_APP_DIR) not in sys.path:
    sys.path.insert(0, str(SLACK_APP_DIR))

if "slack_bolt" not in sys.modules:
    slack_bolt = types.ModuleType("slack_bolt")

    class DummyApp:
        def __init__(self, *args, **kwargs):
            pass

        def command(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

        def event(self, *args, **kwargs):
            return self.command(*args, **kwargs)

        def action(self, *args, **kwargs):
            return self.command(*args, **kwargs)

        def view(self, *args, **kwargs):
            return self.command(*args, **kwargs)

    adapter_module = types.ModuleType("slack_bolt.adapter")
    flask_module = types.ModuleType("slack_bolt.adapter.flask")

    class DummyHandler:
        def __init__(self, app):
            self.app = app

        def handle(self, request):
            return {}

    flask_module.SlackRequestHandler = DummyHandler
    adapter_module.flask = flask_module
    slack_bolt.App = DummyApp
    slack_bolt.adapter = adapter_module

    sys.modules["slack_bolt"] = slack_bolt
    sys.modules["slack_bolt.adapter"] = adapter_module
    sys.modules["slack_bolt.adapter.flask"] = flask_module

if "slack_sdk" not in sys.modules:
    slack_sdk = types.ModuleType("slack_sdk")

    class DummyWebClient:
        def __init__(self, *args, **kwargs):
            pass

        def chat_postMessage(self, **kwargs):
            return {"ok": True}

        def chat_postEphemeral(self, **kwargs):
            return {"ok": True}

        def files_info(self, **kwargs):
            return {"file": {}}

        def users_info(self, user):
            return {"user": {"profile": {"email": "user@example.com", "real_name": "Tester"}}}

        def conversations_open(self, users):
            return {"channel": {"id": "DOPEN"}}

    errors_module = types.ModuleType("slack_sdk.errors")

    class DummySlackApiError(Exception):
        def __init__(self, response):
            self.response = response

    slack_sdk.WebClient = DummyWebClient
    errors_module.SlackApiError = DummySlackApiError
    slack_sdk.errors = errors_module
    sys.modules["slack_sdk"] = slack_sdk
    sys.modules["slack_sdk.errors"] = errors_module

from slack_app import main as slack_main
from slack_app.notifications.summary_delivery import DeliveryResult


class FakeAck:
    def __init__(self):
        self.calls = []

    def __call__(self, payload=None):
        self.calls.append(payload)


class FakeLogger:
    def __getattr__(self, name):
        def _log(*args, **kwargs):
            return None

        return _log


class FakeSlackClient:
    def __init__(self):
        self.messages = []

    def chat_postMessage(self, **kwargs):
        self.messages.append(kwargs)
        return {"ok": True}


class FakeDeliveryService:
    def __init__(self):
        self.calls = []

    def send_summary(self, case_id, initiated_by, phone_number=None):
        self.calls.append((case_id, initiated_by, phone_number))
        return DeliveryResult(
            status="sent",
            summary_url="https://sho.rt/abc123",
            phone=phone_number,
        )


def _build_view(phone="+886912345678", channel="D123", thread="111.222"):
    return {
        "private_metadata": json.dumps(
            {"case_id": "CASE123", "channel_id": channel, "thread_ts": thread}
        ),
        "state": {
            "values": {
                "phone_block": {
                    "phone_input": {"value": phone},
                }
            }
        },
    }


def test_confirm_send_enqueues_cloud_task(monkeypatch):
    from slack_app import main as slack_main
    ack = FakeAck()
    logger = FakeLogger()
    fake_slack = FakeSlackClient()
    slack_main.slack_client = fake_slack
    slack_main.summary_delivery_service = FakeDeliveryService()

    monkeypatch.setattr(slack_main, "_enqueue_summary_delivery_task", lambda *args, **kwargs: True)

    slack_main.handle_confirm_send_summary_modal(
        ack,
        {"user": {"id": "U123"}},
        _build_view(),
        logger,
    )

    assert ack.calls == [None]
    assert fake_slack.messages, "Should post progress update when enqueued"
    assert "📤" in fake_slack.messages[0]["text"]


def test_confirm_send_direct_fallback(monkeypatch):
    from slack_app import main as slack_main
    ack = FakeAck()
    logger = FakeLogger()
    captured = {}

    def fake_enqueue(*args, **kwargs):
        return False

    def fake_notify(case_id, result, channel_id, thread_ts, initiated_by=None):
        captured["case_id"] = case_id
        captured["result"] = result
        captured["channel_id"] = channel_id
        captured["thread_ts"] = thread_ts
        captured["initiated_by"] = initiated_by

    monkeypatch.setattr(slack_main, "_enqueue_summary_delivery_task", fake_enqueue)
    monkeypatch.setattr(slack_main, "_notify_summary_delivery_result", fake_notify)
    slack_main.slack_client = FakeSlackClient()
    slack_main.summary_delivery_service = FakeDeliveryService()

    view = _build_view(channel=None, thread=None)

    slack_main.handle_confirm_send_summary_modal(
        ack,
        {"user": {"id": "U777"}},
        view,
        logger,
    )

    assert captured["case_id"] == "CASE123"
    assert captured["result"].status == "sent"
    assert captured["channel_id"] is None
    assert captured["initiated_by"] == "U777"
