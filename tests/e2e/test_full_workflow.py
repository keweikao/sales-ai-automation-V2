"""
P0: 完整工作流程端到端測試

測試從 Slack 音檔上傳到最終通知發送的完整流程。
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, call
from datetime import datetime


@pytest.mark.p0
class TestFullWorkflow:
    """完整工作流程測試套件"""

    def test_upload_to_notification_happy_path(
        self,
        mock_slack_client,
        mock_firestore_db,
        mock_gemini_api,
        mock_cloud_tasks,
        mock_gcs,
        sample_file_info,
        sample_customer_data,
        sample_transcript,
        sample_agent_results,
        wait_for_async,
    ):
        """
        測試完整的快樂路徑：
        1. Slack 上傳音檔
        2. 驗證檔案並顯示 Modal
        3. 提交客戶資訊
        4. Gemini 轉錄
        5. Agent 1-7 分析
        6. Agent 6, 7 通知發送
        """
        # ===== Phase 1: Slack 音檔上傳 =====
        with patch("src.slack_app.main.db", mock_firestore_db):
            with patch("src.slack_app.main.client", mock_slack_client):
                from src.slack_app.main import handle_file_shared

                event = {
                    "file_id": sample_file_info["id"],
                    "user_id": "U123456789",
                    "ts": "1700000000.123456",
                }

                # 執行檔案上傳處理
                handle_file_shared(
                    client=mock_slack_client,
                    event=event,
                    logger=MagicMock(),
                )

                # 斷言：防重複記錄已建立
                doc = mock_firestore_db.collection("processed_files").document(
                    sample_file_info["id"]
                ).get()
                assert doc.exists
                assert doc.to_dict()["status"] == "notified"

                # 斷言：顯示「分析此錄音」按鈕
                mock_slack_client.chat_postMessage.assert_called_once()
                call_kwargs = mock_slack_client.chat_postMessage.call_args[1]
                assert "blocks" in call_kwargs
                assert any("analyze_audio_button" in str(block) for block in call_kwargs["blocks"])

        # ===== Phase 2: Modal 提交客戶資訊 =====
        with patch("src.slack_app.main.db", mock_firestore_db):
            with patch("src.slack_app.main.client", mock_slack_client):
                from src.slack_app.main import handle_modal_submission

                # 模擬 Modal 提交
                body = {
                    "view": {
                        "state": {
                            "values": {
                                "customer_id_block": {
                                    "customer_id_input": {"value": sample_customer_data["customerId"]}
                                },
                                "store_name_block": {
                                    "store_name_input": {"value": sample_customer_data["storeName"]}
                                },
                                "customer_name_block": {
                                    "customer_name_input": {"value": sample_customer_data["customerName"]}
                                },
                                "phone_block": {
                                    "phone_input": {"value": sample_customer_data["phone"]}
                                },
                                "notes_block": {
                                    "notes_input": {"value": sample_customer_data.get("notes", "")}
                                },
                            }
                        },
                        "private_metadata": sample_file_info["id"],
                    },
                    "user": {"id": "U123456789"},
                }

                # 執行 Modal 提交
                handle_modal_submission(ack=MagicMock(), body=body, client=mock_slack_client, logger=MagicMock())

                # 等待後台處理完成（使用 wait_for_async）
                def case_created():
                    docs = mock_firestore_db.collection("cases").stream()
                    return len(docs) > 0

                assert wait_for_async(case_created, timeout=2.0), "Case not created in time"

                # 斷言：Case 已建立
                cases = mock_firestore_db.collection("cases").stream()
                assert len(cases) == 1
                case_data = cases[0].to_dict()
                assert case_data["customerName"] == sample_customer_data["customerName"]
                assert case_data["phone"] == sample_customer_data["phone"]

                # 斷言：Cloud Task 已建立（觸發轉錄）
                mock_cloud_tasks.create_task.assert_called()

        # ===== Phase 3: Gemini 轉錄 =====
        with patch("src.transcription.main.db", mock_firestore_db):
            with patch("src.transcription.gemini_pipeline.genai", mock_gemini_api):
                from src.transcription.main import transcribe_audio

                case_id = cases[0].id

                # 模擬轉錄請求
                with patch("src.transcription.main.get_pipeline") as mock_get_pipeline:
                    mock_pipeline = MagicMock()
                    mock_pipeline.transcribe.return_value = sample_transcript
                    mock_get_pipeline.return_value = mock_pipeline

                    # 執行轉錄
                    response = transcribe_audio(
                        case_id=case_id,
                        gcs_uri=f"gs://test-bucket/{case_id}/audio.m4a",
                        file_id=sample_file_info["id"],
                    )

                    assert response["status"] == "success"

                # 斷言：轉錄結果已儲存
                case_doc = mock_firestore_db.collection("cases").document(case_id).get()
                assert case_doc.exists
                case_data = case_doc.to_dict()
                assert "transcript" in case_data
                assert case_data["transcript"]["success"] is True

                # 斷言：觸發 Analysis Service
                assert mock_cloud_tasks.create_task.call_count >= 2  # 轉錄 + 分析

        # ===== Phase 4: Agent 1-7 分析 =====
        with patch("analysis_service.src.main.db", mock_firestore_db):
            from analysis_service.src.main import analyze

            # Mock Orchestrator 執行
            with patch("analysis_service.src.main.orchestrator") as mock_orchestrator:
                from analysis_service.src.orchestrator import AnalysisResult, AgentResult

                # 構造 Agent 結果
                agent_results_obj = {
                    agent_id: AgentResult(
                        agent_id=agent_id,
                        success=result["success"],
                        data=result["data"],
                        duration=0.5,
                        error=None,
                    )
                    for agent_id, result in sample_agent_results.items()
                }

                mock_orchestrator.run_sequential_analysis.return_value = AnalysisResult(
                    case_id=case_id,
                    success=True,
                    agent_results=agent_results_obj,
                    total_duration=5.0,
                    error=None,
                )

                # 執行分析
                response = analyze(case_id=case_id)

                assert response["status"] == "success"
                assert response["successCount"] == 7

                # 斷言：Agent 6 結果已儲存
                case_doc = mock_firestore_db.collection("cases").document(case_id).get()
                analysis_data = case_doc.to_dict().get("analysis", {})
                assert "agents" in analysis_data
                assert "agent6" in analysis_data["agents"]
                assert analysis_data["agents"]["agent6"]["success"] is True

                # 斷言：Agent 7 結果已儲存
                assert "customerSummary" in analysis_data
                assert analysis_data["customerSummary"]["markdown"]

        # ===== Phase 5: 通知發送 =====
        with patch("src.slack_app.main.db", mock_firestore_db):
            with patch("src.slack_app.main.agent6_notifier") as mock_agent6_notifier:
                with patch("src.slack_app.main.agent7_notifier") as mock_agent7_notifier:
                    from src.slack_app.main import trigger_agent6_notification, trigger_agent7_notification

                    mock_agent6_notifier.send_agent6_notification.return_value = True
                    mock_agent7_notifier.send_agent7_preview.return_value = True

                    # 觸發通知
                    trigger_agent6_notification(case_id)
                    trigger_agent7_notification(case_id)

                    # 斷言：Agent 6 通知先發送
                    assert mock_agent6_notifier.send_agent6_notification.called
                    # 斷言：Agent 7 通知後發送
                    assert mock_agent7_notifier.send_agent7_preview.called

                    # 斷言：通知發送到正確的 thread
                    agent6_call = mock_agent6_notifier.send_agent6_notification.call_args
                    assert agent6_call[1]["case_id"] == case_id

                    agent7_call = mock_agent7_notifier.send_agent7_preview.call_args
                    assert agent7_call[1]["case_id"] == case_id

    @pytest.mark.p0
    def test_file_validation_rejects_invalid_files(
        self,
        mock_slack_client,
        mock_firestore_db,
    ):
        """測試檔案驗證拒絕無效檔案"""
        from src.slack_app.utils.file_validator import validate_audio_file, FileValidationError

        # 測試：檔案類型不支援
        invalid_file = {
            "id": "F_INVALID",
            "name": "document.pdf",
            "filetype": "pdf",
            "mimetype": "application/pdf",
            "size": 1024,
            "shares": {"private": {"C123": [{}]}},
        }

        with pytest.raises(FileValidationError) as exc_info:
            validate_audio_file(invalid_file)

        assert "不支援" in exc_info.value.user_friendly_message

        # 測試：檔案過大
        oversized_file = {
            "id": "F_LARGE",
            "name": "meeting.m4a",
            "filetype": "m4a",
            "mimetype": "audio/mp4",
            "size": 200 * 1024 * 1024,  # 200 MB
            "shares": {"private": {"C123": [{}]}},
        }

        with pytest.raises(FileValidationError) as exc_info:
            validate_audio_file(oversized_file)

        assert "過大" in exc_info.value.user_friendly_message

        # 測試：檔案大小為 0
        empty_file = {
            "id": "F_EMPTY",
            "name": "empty.m4a",
            "filetype": "m4a",
            "mimetype": "audio/mp4",
            "size": 0,
            "shares": {"private": {"C123": [{}]}},
        }

        with pytest.raises(FileValidationError) as exc_info:
            validate_audio_file(empty_file)

        assert "0" in exc_info.value.user_friendly_message

    @pytest.mark.p0
    def test_agent_execution_order(
        self,
        mock_firestore_db,
        sample_transcript,
    ):
        """測試 Agent 執行順序正確"""
        from analysis_service.src.orchestrator import Orchestrator

        orchestrator = Orchestrator(db=mock_firestore_db)

        # Mock Agent 執行
        execution_order = []

        async def mock_agent_wrapper(case_id, agent_id, agent_func, *args, **kwargs):
            execution_order.append(agent_id)
            from analysis_service.src.orchestrator import AgentResult
            return AgentResult(
                agent_id=agent_id,
                success=True,
                data={"test": "data"},
                duration=0.1,
                error=None,
            )

        with patch.object(orchestrator, "_run_agent_wrapper", side_effect=mock_agent_wrapper):
            # 執行分析
            asyncio.run(
                orchestrator.run_sequential_analysis(
                    case_id="TEST-001",
                    transcript_segments=sample_transcript["segments"],
                    speaker_statistics=sample_transcript.get("speakers"),
                    conversation_metadata={},
                )
            )

            # 斷言：執行順序
            # Phase 1: agent1, agent5, agent7 並行（順序不定）
            assert set(execution_order[:3]) == {"agent1", "agent5", "agent7"}

            # Phase 2: agent2
            assert execution_order[3] == "agent2"

            # Phase 3: agent3, agent4 並行
            assert set(execution_order[4:6]) == {"agent3", "agent4"}

            # Phase 5: agent6
            assert execution_order[6] == "agent6"

    @pytest.mark.p0
    def test_notification_fallback_on_thread_deleted(
        self,
        mock_slack_client,
        mock_firestore_db,
        sample_case_id,
    ):
        """測試 thread 被刪除時的 fallback 機制"""
        from slack_sdk.errors import SlackApiError
        from src.slack_app.main import _send_notification_with_fallback

        # 設定：thread 已被刪除
        mock_notifier = MagicMock()
        error_response = {"error": "thread_not_found"}
        mock_notifier.side_effect = [
            SlackApiError("thread_not_found", response=error_response),  # 第一次失敗
            True,  # Fallback 成功
        ]

        # 執行通知
        success, reason = _send_notification_with_fallback(
            case_id=sample_case_id,
            notifier_func=mock_notifier,
            fallback_prefix="Test",
            user_id="U123",
            thread_ts="1700000000.123",
        )

        # 斷言：Fallback 成功
        assert success is True
        assert reason == "sent_to_channel"

        # 斷言：嘗試了 fallback
        assert mock_notifier.call_count == 2

        # 第一次：有 thread_ts
        first_call = mock_notifier.call_args_list[0]
        assert first_call[1]["thread_ts"] == "1700000000.123"

        # 第二次：無 thread_ts（fallback）
        second_call = mock_notifier.call_args_list[1]
        assert second_call[1].get("thread_ts") is None


@pytest.mark.p0
def test_duplicate_file_prevention(
    mock_slack_client,
    mock_firestore_db,
    sample_file_info,
):
    """測試防止重複處理同一檔案"""
    from src.slack_app.main import handle_file_shared

    event = {
        "file_id": sample_file_info["id"],
        "user_id": "U123456789",
        "ts": "1700000000.123456",
    }

    with patch("src.slack_app.main.db", mock_firestore_db):
        # 第一次處理
        handle_file_shared(
            client=mock_slack_client,
            event=event,
            logger=MagicMock(),
        )

        # 斷言：訊息已發送
        assert mock_slack_client.chat_postMessage.call_count == 1

        # 重置 mock
        mock_slack_client.reset_mock()

        # 第二次處理（重複）
        handle_file_shared(
            client=mock_slack_client,
            event=event,
            logger=MagicMock(),
        )

        # 斷言：訊息未再次發送
        assert mock_slack_client.chat_postMessage.call_count == 0
