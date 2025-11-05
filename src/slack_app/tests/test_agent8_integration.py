"""
Agent 8 整合測試

測試 Agent 8 的核心功能
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock


class TestAgent8Integration:
    """Agent 8 整合測試"""

    def test_import_modules(self):
        """測試模塊導入"""
        from agents.question_parser import QuestionParser, QuestionParams, QuestionType
        from agents.data_fetcher import DataFetcher
        from agents.conversation_manager import ConversationManager
        from agents.conversational_agent8 import ConversationalAgent8

        assert QuestionParser is not None
        assert QuestionParams is not None
        assert QuestionType is not None
        assert DataFetcher is not None
        assert ConversationManager is not None
        assert ConversationalAgent8 is not None

    def test_question_types(self):
        """測試問題類型枚舉"""
        from agents.question_parser import QuestionType

        assert QuestionType.TEAM_OVERVIEW == "team_overview"
        assert QuestionType.SALES_REP_PERFORMANCE == "sales_rep_performance"
        assert QuestionType.CASE_DETAILS == "case_details"
        assert QuestionType.COMPETITOR_INTELLIGENCE == "competitor_intelligence"
        assert QuestionType.PRODUCT_DEMAND == "product_demand"
        assert QuestionType.TREND_COMPARISON == "trend_comparison"

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("agents.question_parser.genai.configure")
    @patch("agents.question_parser.genai.GenerativeModel")
    def test_question_parser_init(self, mock_model, mock_configure):
        """測試問題解析器初始化"""
        from agents.question_parser import QuestionParser

        parser = QuestionParser()

        # 驗證 API key 設置
        mock_configure.assert_called_once_with(api_key="test-key")
        mock_model.assert_called_once_with('gemini-2.0-flash-exp')

    def test_data_fetcher_init_with_client(self):
        """測試數據查詢器初始化（提供 client）"""
        from agents.data_fetcher import DataFetcher

        mock_db = Mock()
        fetcher = DataFetcher(db_client=mock_db)

        assert fetcher.db == mock_db

    def test_conversation_manager_init_with_client(self):
        """測試對話管理器初始化（提供 client）"""
        from agents.conversation_manager import ConversationManager

        mock_db = Mock()
        manager = ConversationManager(db_client=mock_db)

        assert manager.db == mock_db

    def test_check_manager_permission_authorized(self):
        """測試權限檢查 - 有權限"""
        from handlers.agent8_handler import check_manager_permission

        # Mock Firestore client
        mock_db = Mock()
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"role": "manager", "name": "王大明"}

        mock_collection = Mock()
        mock_collection.document.return_value.get.return_value = mock_doc
        mock_db.collection.return_value = mock_collection

        # 測試
        result = check_manager_permission("U12345678", mock_db)

        assert result is True
        mock_db.collection.assert_called_once_with("users")
        mock_collection.document.assert_called_once_with("U12345678")

    def test_check_manager_permission_unauthorized(self):
        """測試權限檢查 - 無權限"""
        from handlers.agent8_handler import check_manager_permission

        # Mock Firestore client
        mock_db = Mock()
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"role": "user", "name": "一般用戶"}

        mock_collection = Mock()
        mock_collection.document.return_value.get.return_value = mock_doc
        mock_db.collection.return_value = mock_collection

        # 測試
        result = check_manager_permission("U87654321", mock_db)

        assert result is False

    def test_check_manager_permission_user_not_exists(self):
        """測試權限檢查 - 用戶不存在"""
        from handlers.agent8_handler import check_manager_permission

        # Mock Firestore client
        mock_db = Mock()
        mock_doc = Mock()
        mock_doc.exists = False

        mock_collection = Mock()
        mock_collection.document.return_value.get.return_value = mock_doc
        mock_db.collection.return_value = mock_collection

        # 測試
        result = check_manager_permission("U99999999", mock_db)

        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
