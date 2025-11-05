"""
Agent 8 - 對話式業務主管助理

提供自然語言問答界面，讓業務主管可以隨時查詢團隊數據和業務洞察
"""

from .question_parser import QuestionParser, QuestionParams, QuestionType
from .data_fetcher import DataFetcher, QueryResult
from .conversation_manager import ConversationManager
from .conversational_agent8 import ConversationalAgent8

__all__ = [
    "QuestionParser",
    "QuestionParams",
    "QuestionType",
    "DataFetcher",
    "QueryResult",
    "ConversationManager",
    "ConversationalAgent8"
]
