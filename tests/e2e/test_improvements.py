"""
驗證高風險改善的測試

測試我們實作的三個主要改善：
1. 檔案驗證
2. 通知 fallback 機制
3. Agent 執行順序
"""

import pytest
from unittest.mock import MagicMock, patch
from slack_sdk.errors import SlackApiError


@pytest.mark.p0
class TestFileValidation:
    """檔案驗證測試"""

    def test_valid_audio_file_passes(self):
        """測試有效的音檔通過驗證"""
        from src.slack_app.utils.file_validator import validate_audio_file

        valid_file = {
            "id": "F123",
            "name": "meeting.m4a",
            "filetype": "m4a",
            "mimetype": "audio/mp4",
            "size": 5 * 1024 * 1024,  # 5 MB
            "shares": {"private": {"C123": [{}]}},
        }

        # 應該不拋出異常
        success, error = validate_audio_file(valid_file)
        assert success is True
        assert error is None

    def test_unsupported_filetype_rejected(self):
        """測試不支援的檔案類型被拒絕"""
        from src.slack_app.utils.file_validator import validate_audio_file, FileValidationError

        invalid_file = {
            "id": "F123",
            "name": "document.pdf",
            "filetype": "pdf",
            "mimetype": "application/pdf",
            "size": 1024,
            "shares": {"private": {"C123": [{}]}},
        }

        with pytest.raises(FileValidationError) as exc:
            validate_audio_file(invalid_file)

        assert "不支援" in exc.value.user_friendly_message
        assert "pdf" in exc.value.user_friendly_message.lower()

    def test_oversized_file_rejected(self):
        """測試過大檔案被拒絕"""
        from src.slack_app.utils.file_validator import validate_audio_file, FileValidationError

        oversized_file = {
            "id": "F123",
            "name": "large.m4a",
            "filetype": "m4a",
            "mimetype": "audio/mp4",
            "size": 150 * 1024 * 1024,  # 150 MB
            "shares": {"private": {"C123": [{}]}},
        }

        with pytest.raises(FileValidationError) as exc:
            validate_audio_file(oversized_file)

        assert "過大" in exc.value.user_friendly_message

    def test_empty_file_rejected(self):
        """測試空檔案被拒絕"""
        from src.slack_app.utils.file_validator import validate_audio_file, FileValidationError

        empty_file = {
            "id": "F123",
            "name": "empty.m4a",
            "filetype": "m4a",
            "mimetype": "audio/mp4",
            "size": 0,
            "shares": {"private": {"C123": [{}]}},
        }

        with pytest.raises(FileValidationError) as exc:
            validate_audio_file(empty_file)

        assert "0" in exc.value.user_friendly_message

    def test_mime_type_mismatch_rejected(self):
        """測試 MIME type 不符被拒絕"""
        from src.slack_app.utils.file_validator import validate_audio_file, FileValidationError

        mismatched_file = {
            "id": "F123",
            "name": "fake.m4a",
            "filetype": "m4a",
            "mimetype": "application/octet-stream",  # 不正確的 MIME type
            "size": 1024,
            "shares": {"private": {"C123": [{}]}},
        }

        with pytest.raises(FileValidationError) as exc:
            validate_audio_file(mismatched_file)

        # 應該提示格式異常
        message = exc.value.user_friendly_message
        assert "格式" in message or "mime" in message.lower()


@pytest.mark.p0
class TestNotificationFallback:
    """通知 fallback 機制測試"""

    def test_fallback_to_channel_on_thread_not_found(self, mock_firestore_db):
        """測試 thread 不存在時 fallback 到 channel"""
        from src.slack_app.main import _send_notification_with_fallback

        # Mock notifier 第一次失敗（thread_not_found），第二次成功
        mock_notifier = MagicMock()
        mock_notifier.side_effect = [
            SlackApiError("thread_not_found", response={"error": "thread_not_found"}),
            True,  # Fallback 成功
        ]

        with patch("src.slack_app.main._resolve_notification_target") as mock_resolve:
            mock_resolve.return_value = ("C123", "1700000000.123", "客戶", "U123")

            success, reason = _send_notification_with_fallback(
                case_id="TEST-001",
                notifier_func=mock_notifier,
                fallback_prefix="Test",
                user_id="C123",
                channel_id="C123",
                thread_ts="1700000000.123",
            )

            # 應該 fallback 成功
            assert success is True
            assert "channel" in reason

            # 應該嘗試了兩次
            assert mock_notifier.call_count == 2

            # 第二次呼叫應該沒有 thread_ts
            second_call = mock_notifier.call_args_list[1]
            assert second_call[1].get("thread_ts") is None

    def test_fallback_to_dm_on_channel_not_found(self, mock_firestore_db):
        """測試 channel 不存在時 fallback 到 DM"""
        from src.slack_app.main import _send_notification_with_fallback

        # Mock notifier 前兩次失敗，第三次成功（DM）
        mock_notifier = MagicMock()
        mock_notifier.side_effect = [
            SlackApiError("channel_not_found", response={"error": "channel_not_found"}),
            SlackApiError("channel_not_found", response={"error": "channel_not_found"}),
            True,  # DM fallback 成功
        ]

        with patch("src.slack_app.main._resolve_notification_target") as mock_resolve:
            # 第一次返回 channel，第二次返回 user（DM）
            mock_resolve.return_value = ("C123", None, "客戶", "U123")

            success, reason = _send_notification_with_fallback(
                case_id="TEST-001",
                notifier_func=mock_notifier,
                fallback_prefix="Test",
                user_id="C123",
                channel_id="C123",
                thread_ts=None,
            )

            # 應該 fallback 到 DM 成功
            assert success is True
            assert "dm" in reason


@pytest.mark.p0
class TestAgentOrdering:
    """Agent 執行順序測試"""

    def test_agent7_runs_in_phase1(self):
        """測試 Agent 7 在 Phase 1 執行（與 Agent 1, 5 並行）"""
        # 讀取 orchestrator.py 檢查 Phase 1 配置
        with open("/workspaces/sales-ai-automation-V2/analysis-service/src/orchestrator.py", "r") as f:
            content = f.read()

        # 應該有 Phase 1 包含 agent1, agent5, agent7
        assert "Phase 1: Agents 1, 5, 7" in content
        assert "result_agent1, result_agent5, result_agent7 = await asyncio.gather" in content

    def test_agent6_runs_after_agent1_to_5(self):
        """測試 Agent 6 在 Agent 1-5 之後執行"""
        with open("/workspaces/sales-ai-automation-V2/analysis-service/src/orchestrator.py", "r") as f:
            content = f.read()

        # 應該有 Phase 5 執行 Agent 6
        assert "Phase 5: Agent 6 (Sales Coach)" in content

        # 應該檢查 Agent 1-5 的成功門檻
        assert 'r.agent_id in ["agent1", "agent2", "agent3", "agent4", "agent5"]' in content

    def test_notification_order_agent6_before_agent7(self):
        """測試通知順序：Agent 6 在 Agent 7 之前"""
        with open("/workspaces/sales-ai-automation-V2/analysis-service/src/main.py", "r") as f:
            lines = f.readlines()

        # 找到 Agent 6 和 Agent 7 通知的行號
        agent6_line = None
        agent7_line = None

        for i, line in enumerate(lines):
            if "trigger_agent6_notification" in line and "def " not in line:
                agent6_line = i
            if "trigger_agent7_notification" in line and "def " not in line:
                agent7_line = i

        # Agent 6 通知應該在 Agent 7 之前
        assert agent6_line is not None, "找不到 Agent 6 通知呼叫"
        assert agent7_line is not None, "找不到 Agent 7 通知呼叫"
        assert agent6_line < agent7_line, f"Agent 6 通知應該在 Agent 7 之前（行 {agent6_line} vs {agent7_line}）"


@pytest.mark.p0
def test_file_size_display():
    """測試檔案大小顯示格式"""
    from src.slack_app.utils.file_validator import get_file_size_display

    assert get_file_size_display(500) == "500 B"
    assert get_file_size_display(1536) == "1.5 KB"
    assert get_file_size_display(1024 * 1024 * 2.5) == "2.5 MB"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "p0"])
