"""
對話管理模組 - 管理對話歷史和上下文

功能：
1. 儲存對話歷史
2. 提取上下文資訊
3. 支持對話切換和重新查詢
4. 處理代詞指代
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path


class ConversationManager:
    """對話管理器"""

    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化對話管理器

        Args:
            storage_path: 對話歷史儲存路徑（可選）
        """
        self.conversations: Dict[str, List[Dict]] = {}  # user_id -> conversation history
        self.storage_path = storage_path

        if storage_path:
            self.storage_dir = Path(storage_path)
            self.storage_dir.mkdir(parents=True, exist_ok=True)

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
        儲存一輪對話

        Args:
            user_id: 用戶 ID
            question: 用戶問題
            answer: Agent 回答
            params: 問題參數
            total_cases: 查詢到的案件數
            metadata: 其他元數據
        """
        if user_id not in self.conversations:
            self.conversations[user_id] = []

        conversation_turn = {
            "timestamp": datetime.utcnow().isoformat(),
            "question": question,
            "answer": answer,
            "params": params,
            "totalCases": total_cases,
            "metadata": metadata or {}
        }

        self.conversations[user_id].append(conversation_turn)

        # 如果設置了儲存路徑，儲存到文件
        if self.storage_path:
            self._save_to_file(user_id)

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
        history = self.conversations.get(user_id, [])

        if limit:
            return history[-limit:]

        return history

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
        if user_id in self.conversations:
            del self.conversations[user_id]

        # 刪除儲存的文件
        if self.storage_path:
            file_path = self.storage_dir / f"{user_id}.json"
            if file_path.exists():
                file_path.unlink()

    def _save_to_file(self, user_id: str) -> None:
        """
        儲存對話歷史到文件

        Args:
            user_id: 用戶 ID
        """
        file_path = self.storage_dir / f"{user_id}.json"

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(
                self.conversations[user_id],
                f,
                ensure_ascii=False,
                indent=2
            )

    def _load_from_file(self, user_id: str) -> None:
        """
        從文件載入對話歷史

        Args:
            user_id: 用戶 ID
        """
        file_path = self.storage_dir / f"{user_id}.json"

        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                self.conversations[user_id] = json.load(f)

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


# 單例模式
_manager_instance: Optional[ConversationManager] = None


def get_conversation_manager(storage_path: Optional[str] = None) -> ConversationManager:
    """
    獲取 ConversationManager 單例

    Args:
        storage_path: 儲存路徑

    Returns:
        ConversationManager 實例
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ConversationManager(storage_path)
    return _manager_instance


if __name__ == "__main__":
    # 測試用
    manager = ConversationManager()

    # 測試儲存對話
    manager.save_conversation(
        user_id="test_user",
        question="今天團隊表現如何？",
        answer="團隊表現良好...",
        params={"type": "team_overview", "timeRange": "today"},
        total_cases=30
    )

    manager.save_conversation(
        user_id="test_user",
        question="王小明的情況呢？",
        answer="王小明表現優異...",
        params={"type": "sales_rep_performance", "salesRepName": "王小明"},
        total_cases=7
    )

    # 獲取上下文
    context = manager.get_context("test_user", "他最好的案件是哪個？")
    print("上下文：")
    print(json.dumps(context, ensure_ascii=False, indent=2))

    # 檢查是否切換話題
    is_switch = manager.is_topic_switch(
        "test_user",
        "sales_rep_performance",
        {"salesRepName": "陳美玲"}
    )
    print(f"\n是否切換話題：{is_switch}")

    # 獲取摘要
    summary = manager.get_summary("test_user")
    print(f"\n{summary}")
