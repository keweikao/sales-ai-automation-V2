"""
E2E 測試配置和共用 fixtures

提供測試所需的 mock 物件、測試資料和輔助函數。
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from typing import Dict, Any


# ===== Pytest Configuration =====

def pytest_configure(config):
    """註冊自定義 markers"""
    config.addinivalue_line(
        "markers", "p0: P0 priority tests (must pass)"
    )
    config.addinivalue_line(
        "markers", "p1: P1 priority tests (important but not blocking)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests with real services"
    )


# ===== Test Data Fixtures =====

@pytest.fixture
def sample_case_id():
    """提供測試用的 case ID"""
    return f"202511-IC001-TEST-{datetime.now().strftime('%H%M%S')}"


@pytest.fixture
def sample_file_id():
    """提供測試用的 file ID"""
    return "F123456789TEST"


@pytest.fixture
def sample_user_id():
    """提供測試用的 user ID"""
    return "U123456789"


@pytest.fixture
def sample_channel_id():
    """提供測試用的 channel ID"""
    return "C123456789"


@pytest.fixture
def sample_customer_data():
    """提供測試用的客戶資料"""
    return {
        "customerId": "CU12345",
        "storeName": "測試餐廳",
        "customerName": "王小明",
        "phone": "0912345678",
        "notes": "VIP 客戶",
    }


@pytest.fixture
def sample_file_info(sample_file_id):
    """提供測試用的 Slack file_info"""
    return {
        "id": sample_file_id,
        "name": "test_meeting.m4a",
        "title": "測試會議錄音",
        "filetype": "m4a",
        "mimetype": "audio/mp4",
        "size": 1024 * 1024,  # 1 MB
        "user": "U123456789",
        "created": 1700000000,
        "shares": {
            "private": {
                "C123456789": [
                    {
                        "ts": "1700000000.123456",
                        "reply_users": [],
                        "reply_count": 0,
                    }
                ]
            }
        },
        "url_private": "https://files.slack.com/test",
        "url_private_download": "https://files.slack.com/test/download",
    }


@pytest.fixture
def sample_transcript():
    """提供測試用的轉錄結果"""
    return {
        "success": True,
        "full_text": "這是測試會議的轉錄內容。業務：您好，請問有什麼需要協助的嗎？客戶：我想了解 POS 系統的功能。",
        "segments": [
            {
                "speaker": "speaker_0",
                "text": "您好，請問有什麼需要協助的嗎？",
                "start": 0.0,
                "end": 3.5,
            },
            {
                "speaker": "speaker_1",
                "text": "我想了解 POS 系統的功能。",
                "start": 4.0,
                "end": 7.2,
            },
        ],
        "speakers": [
            {
                "speaker_id": "speaker_0",
                "total_time": 15.5,
                "segment_count": 5,
            },
            {
                "speaker_id": "speaker_1",
                "total_time": 12.3,
                "segment_count": 4,
            },
        ],
        "audio_info": {
            "duration": 30.0,
            "format": "m4a",
            "sample_rate": 44100,
        },
    }


@pytest.fixture
def sample_agent_results():
    """提供測試用的 Agent 執行結果"""
    return {
        "agent1": {
            "success": True,
            "data": {
                "participants": [
                    {
                        "role": "sales_rep",
                        "confidence": 0.9,
                        "characteristics": ["professional", "helpful"],
                    },
                    {
                        "role": "customer",
                        "confidence": 0.85,
                        "characteristics": ["interested", "inquiring"],
                    },
                ],
            },
        },
        "agent2": {
            "success": True,
            "data": {
                "overall_sentiment": "positive",
                "purchase_intent": "high",
                "sentiment_score": 0.75,
            },
        },
        "agent3": {
            "success": True,
            "data": {
                "needs": [
                    {
                        "category": "POS 功能",
                        "priority": "high",
                        "details": "了解基本 POS 功能",
                    }
                ],
            },
        },
        "agent4": {
            "success": True,
            "data": {
                "email_subject": "會議摘要",
                "email_body": "感謝您今天的時間討論 POS 系統...",
                "action_items": {
                    "sales": ["安排產品示範"],
                    "customer": ["準備需求清單"],
                },
            },
        },
    }


# ===== Mock Fixtures =====

@pytest.fixture
def mock_slack_client():
    """Mock Slack WebClient"""
    mock_client = MagicMock()

    # Mock files.info
    mock_client.files_info.return_value = {
        "ok": True,
        "file": {
            "id": "F123456789",
            "name": "test.m4a",
            "filetype": "m4a",
            "mimetype": "audio/mp4",
            "size": 1024 * 1024,
            "shares": {"private": {"C123": [{}]}},
        },
    }

    # Mock chat.postMessage
    mock_client.chat_postMessage.return_value = {
        "ok": True,
        "ts": "1700000000.123456",
        "channel": "C123456789",
    }

    # Mock views.open
    mock_client.views_open.return_value = {"ok": True}

    # Mock views.update
    mock_client.views_update.return_value = {"ok": True}

    return mock_client


@pytest.fixture
def mock_firestore_db():
    """Mock Firestore database"""
    from tests.e2e.mocks.firestore_mock import MockFirestore
    return MockFirestore()


@pytest.fixture
def mock_gemini_api(sample_transcript):
    """Mock Gemini API"""
    with patch("google.generativeai.upload_file") as mock_upload:
        with patch("google.generativeai.GenerativeModel") as mock_model:
            # Mock file upload
            mock_file = MagicMock()
            mock_file.name = "uploaded_audio"
            mock_upload.return_value = mock_file

            # Mock generate_content
            mock_response = MagicMock()
            mock_response.text = str(sample_transcript)
            mock_model.return_value.generate_content.return_value = mock_response

            yield {
                "upload_file": mock_upload,
                "model": mock_model,
                "file": mock_file,
                "response": mock_response,
            }


@pytest.fixture
def mock_cloud_tasks():
    """Mock Cloud Tasks client"""
    with patch("google.cloud.tasks_v2.CloudTasksClient") as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.create_task.return_value = MagicMock(name="test-task")
        mock_instance.queue_path.return_value = "projects/test/locations/test/queues/test"
        yield mock_instance


@pytest.fixture
def mock_gcs():
    """Mock Google Cloud Storage"""
    with patch("google.cloud.storage.Client") as mock_client:
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.public_url = "https://storage.googleapis.com/test"

        mock_bucket.blob.return_value = mock_blob
        mock_client.return_value.bucket.return_value = mock_bucket

        yield {
            "client": mock_client,
            "bucket": mock_bucket,
            "blob": mock_blob,
        }


# ===== Helper Functions =====

@pytest.fixture
def wait_for_async():
    """等待非同步操作完成的輔助函數"""
    import time

    def _wait(condition_func, timeout=5.0, interval=0.1):
        """
        等待條件函數返回 True

        Args:
            condition_func: 返回布林值的函數
            timeout: 超時時間（秒）
            interval: 檢查間隔（秒）

        Returns:
            bool: 條件是否在超時前滿足
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if condition_func():
                return True
            time.sleep(interval)
        return False

    return _wait


@pytest.fixture
def assert_firestore_document(mock_firestore_db):
    """斷言 Firestore 文件內容的輔助函數"""

    def _assert(collection: str, document_id: str, expected_fields: Dict[str, Any]):
        """
        斷言 Firestore 文件包含預期欄位

        Args:
            collection: 集合名稱
            document_id: 文件 ID
            expected_fields: 預期的欄位和值
        """
        doc = mock_firestore_db.collection(collection).document(document_id).get()
        assert doc.exists, f"Document {collection}/{document_id} does not exist"

        doc_data = doc.to_dict()
        for key, expected_value in expected_fields.items():
            assert key in doc_data, f"Field '{key}' not found in document"
            if expected_value is not None:
                assert doc_data[key] == expected_value, (
                    f"Field '{key}' mismatch: expected {expected_value}, got {doc_data[key]}"
                )

    return _assert


@pytest.fixture
def create_test_case(mock_firestore_db, sample_case_id, sample_customer_data):
    """創建測試 case 的輔助函數"""

    def _create(**overrides):
        """
        創建測試 case

        Args:
            **overrides: 覆蓋預設值的欄位

        Returns:
            str: Case ID
        """
        case_data = {
            "caseId": sample_case_id,
            "createdAt": datetime.now(),
            "status": "processing",
            **sample_customer_data,
            **overrides,
        }

        mock_firestore_db.collection("cases").document(sample_case_id).set(case_data)
        return sample_case_id

    return _create


# ===== Environment Setup =====

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """設定測試環境變數"""
    test_env = {
        "GOOGLE_CLOUD_PROJECT": "test-project",
        "FIRESTORE_EMULATOR_HOST": "localhost:8080",
        "TRANSCRIPTION_ENGINE": "gemini",
        "GEMINI_MODEL": "gemini-2.5-flash",
        "GEMINI_API_KEY": "test-api-key",
        "SLACK_BOT_TOKEN": "xoxb-test-token",
        "SLACK_SIGNING_SECRET": "test-secret",
        "TEST_MODE": "true",
    }

    for key, value in test_env.items():
        monkeypatch.setenv(key, value)

    yield

    # Cleanup if needed
