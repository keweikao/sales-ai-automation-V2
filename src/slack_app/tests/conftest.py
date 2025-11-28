import os
import pytest
from unittest.mock import MagicMock

os.environ["SLACK_BOT_TOKEN"] = "test"

@pytest.fixture(autouse=True)
def mock_slack_app(monkeypatch):
    mock_app = MagicMock()
    monkeypatch.setattr("slack_bolt.App", lambda *args, **kwargs: mock_app)
