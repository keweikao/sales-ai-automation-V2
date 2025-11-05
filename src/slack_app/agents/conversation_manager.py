"""
對話管理模組 - 使用 Firestore 管理對話歷史和上下文

功能：
1. 儲存對話歷史到 Firestore
2. 提取上下文資訊
3. 支持對話切換和重新查詢
4. 處理代詞指代
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from google.cloud import firestore

logger = logging.getLogger(__name__)


class ConversationManager:
    """對話管理器（使用 Firestore）"""

    def __init__(self, db_client: Optional[firestore.Client] = None, project_id: Optional[str] = None):
        """
        初始化對話管理器

        Args:
            db_client: Firestore Client（可選）
            project_id: GCP 項目 ID
        """
        if db_client:
            self.db = db_client
        else:
            project_id = project_id or os.getenv("GCP_PROJECT_ID")
            if not project_id:
                raise ValueError("GCP_PROJECT_ID 未設定")
            self.db = firestore.Client(project=project_id)

        self.collection_name = "agent8_conversations"

    def save_conversation(
        self,
        user_id: str,
        question: str,
        answer: str,
        params: Dict[str, Any],
        total_cases: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        儲存一輪對話到 Firestore

        Args:
            user_id: 用戶 ID
            question: 用戶問題
            answer: Agent 回答
            params: 問題參數
            total_cases: 查詢到的案件數
            metadata: 其他元數據
        """
        try:
            conversation_turn = {
                "userId": user_id,
                "timestamp": datetime.utcnow(),
                "question": question,
                "answer": answer,
                "params": params,
                "totalCases": total_cases,
                "metadata": metadata or {}
            }

            # 新增到 Firestore
            self.db.collection(self.collection_name).add(conversation_turn)

            logger.info(f"儲存對話：user={user_id}, type={params.get('type')}")

        except Exception as e:
            logger.error(f"儲存對話失敗：{e}", exc_info=True)

    def get_conversation_history(
        self,
        user_id: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        獲取對話歷史

        Args:
            user_id: 用戶 ID
            limit: 返回最近 N 輪對話（None = 全部）

        Returns:
            對話歷史列表
        """
        try:
            query = self.db.collection(self.collection_name)\
                .where("userId", "==", user_id)\
                .order_by("timestamp", direction=firestore.Query.DESCENDING)

            if limit:
                query = query.limit(limit)

            docs = query.stream()
            history = []

            for doc in docs:
                data = doc.to_dict()
                history.append(data)

            # 反轉順序（最舊的在前）
            history.reverse()

            return history

        except Exception as e:
            logger.error(f"獲取對話歷史失敗：{e}", exc_info=True)
            return []

    def get_context(
        self,
        user_id: str,
        current_question: str
    ) -> Dict[str, Any]:
        """
        提取當前問題的上下文

        Args:
            user_id: 用戶 ID
            current_question: 當前問題

        Returns:
            上下文資訊
        """
        history = self.get_conversation_history(user_id, limit=3)

        if not history:
            return {
                "hasContext": False,
                "previousQuestions": [],
                "referencedEntities": {}
            }

        # 提取最近提到的實體
        referenced_entities = self._extract_entities_from_history(history)

        # 檢查當前問題是否包含代詞
        has_pronouns = self._contains_pronouns(current_question)

        return {
            "hasContext": True,
            "previousQuestions": [h["question"] for h in history],
            "referencedEntities": referenced_entities,
            "hasPronouns": has_pronouns,
            "lastQuestionType": history[-1]["params"].get("type") if history else None
        }

    def _extract_entities_from_history(self, history: List[Dict]) -> Dict[str, Any]:
        """
        從歷史中提取實體（業務名字、案件 ID、客戶名字等）

        Args:
            history: 對話歷史

        Returns:
            提取的實體
        """
        entities = {
            "salesRepNames": [],
            "caseIds": [],
            "customerNames": [],
            "competitorNames": [],
            "features": []
        }

        for turn in history:
            params = turn.get("params", {})

            # 業務名字
            if params.get("salesRepName"):
                entities["salesRepNames"].append(params["salesRepName"])

            # 案件 ID
            if params.get("caseId"):
                entities["caseIds"].append(params["caseId"])

            # 客戶名字
            if params.get("customerName"):
                entities["customerNames"].append(params["customerName"])

            # 競品名字
            if params.get("competitorName"):
                entities["competitorNames"].append(params["competitorName"])

            # 功能名稱
            if params.get("feature"):
                entities["features"].append(params["feature"])

        # 去重並保留最近的
        for key in entities:
            entities[key] = list(dict.fromkeys(reversed(entities[key])))[:3]

        return entities

    def _contains_pronouns(self, question: str) -> bool:
        """
        檢查問題是否包含代詞

        Args:
            question: 問題文字

        Returns:
            是否包含代詞
        """
        pronouns = ["他", "她", "它", "這個", "那個", "這件", "那件", "這些", "那些"]
        return any(pronoun in question for pronoun in pronouns)

    def is_topic_switch(
        self,
        user_id: str,
        current_question_type: str,
        current_params: Dict[str, Any]
    ) -> bool:
        """
        判斷是否切換了話題

        Args:
            user_id: 用戶 ID
            current_question_type: 當前問題類型
            current_params: 當前問題參數

        Returns:
            是否切換話題
        """
        history = self.get_conversation_history(user_id, limit=1)

        if not history:
            return False

        last_turn = history[-1]
        last_type = last_turn["params"].get("type")

        # 問題類型改變
        if last_type != current_question_type:
            return True

        # 關鍵參數改變（例如從王小明切換到陳美玲）
        key_params = ["salesRepName", "caseId", "customerName", "competitorName"]
        for param in key_params:
            last_value = last_turn["params"].get(param)
            current_value = current_params.get(param)

            if last_value and current_value and last_value != current_value:
                return True

        return False

    def clear_conversation(self, user_id: str) -> None:
        """
        清除對話歷史

        Args:
            user_id: 用戶 ID
        """
        try:
            docs = self.db.collection(self.collection_name)\
                .where("userId", "==", user_id)\
                .stream()

            batch = self.db.batch()
            count = 0

            for doc in docs:
                batch.delete(doc.reference)
                count += 1

            if count > 0:
                batch.commit()
                logger.info(f"清除對話歷史：user={user_id}, count={count}")

        except Exception as e:
            logger.error(f"清除對話歷史失敗：{e}", exc_info=True)

    def get_summary(self, user_id: str) -> str:
        """
        獲取對話摘要

        Args:
            user_id: 用戶 ID

        Returns:
            對話摘要文字
        """
        history = self.get_conversation_history(user_id)

        if not history:
            return "尚無對話歷史"

        total_turns = len(history)
        total_cases_queried = sum(h.get("totalCases", 0) for h in history)

        summary = f"對話摘要：\n"
        summary += f"- 總共 {total_turns} 輪對話\n"
        summary += f"- 查詢了 {total_cases_queried} 個案件\n"
        summary += f"\n最近 3 個問題：\n"

        for i, turn in enumerate(history[-3:], 1):
            summary += f"{i}. {turn['question']}\n"

        return summary
