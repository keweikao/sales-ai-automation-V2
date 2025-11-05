"""
Agent 8 Slack 命令處理器

處理 /ask-agent8 命令，提供業務主管智能問答功能
"""

import os
import logging
from typing import Dict, Any

from google.cloud import firestore

try:
    from slack_sdk.errors import SlackApiError
except ModuleNotFoundError:  # pragma: no cover - for test env without slack_sdk
    class SlackApiError(Exception):  # type: ignore
        def __init__(self, error: str = "slack_sdk_missing"):
            self.response = {"error": error}
            super().__init__(error)

try:
    from slack_sdk import WebClient
except ModuleNotFoundError:  # pragma: no cover - allow tests without slack_sdk installed
    WebClient = Any  # type: ignore
from agents.conversational_agent8 import ConversationalAgent8

logger = logging.getLogger(__name__)

# 全局 Agent 8 實例（單例模式）
_agent8_instance = None


def get_agent8_instance() -> ConversationalAgent8:
    """
    獲取 Agent 8 單例

    Returns:
        ConversationalAgent8 實例
    """
    global _agent8_instance
    if _agent8_instance is None:
        _agent8_instance = ConversationalAgent8()
    return _agent8_instance


def check_manager_permission(user_id: str, db_client: firestore.Client) -> bool:
    """
    檢查用戶是否有主管權限

    Args:
        user_id: Slack User ID
        db_client: Firestore Client

    Returns:
        是否有權限
    """
    try:
        # 查詢 Firestore 中的主管名單
        user_doc = db_client.collection("users").document(user_id).get()

        if not user_doc.exists:
            logger.warning(f"用戶不存在：{user_id}")
            return False

        user_data = user_doc.to_dict()
        role = user_data.get("role", "")

        # 允許 manager 和 admin 角色
        is_authorized = role in ["manager", "admin"]

        logger.info(f"權限檢查：user={user_id}, role={role}, authorized={is_authorized}")

        return is_authorized

    except Exception as e:
        logger.error(f"檢查權限失敗：{e}", exc_info=True)
        return False


def handle_ask_agent8_command(
    ack,
    command: Dict[str, Any],
    client: WebClient,
    logger_instance,
    db_client: firestore.Client
):
    """
    處理 /ask-agent8 命令

    Args:
        ack: Slack 確認函數
        command: Slack 命令數據
        client: Slack Web Client
        logger_instance: Logger 實例
        db_client: Firestore Client
    """
    # 立即確認命令（3 秒內必須回應）
    ack()

    user_id = command.get("user_id")
    question = command.get("text", "").strip()
    channel_id = command.get("channel_id")

    logger.info(f"收到 /ask-agent8 命令：user={user_id}, question={question}")

    try:
        # 1. 檢查權限
        if not check_manager_permission(user_id, db_client):
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text="❌ 抱歉，您沒有使用 Agent 8 的權限。\n\n"
                     "Agent 8 目前僅開放給業務主管使用。\n"
                     "如需權限，請聯絡系統管理員。"
            )
            logger.warning(f"用戶無權限：{user_id}")
            return

        # 2. 檢查問題是否為空
        if not question:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text="📝 請在命令後輸入問題，例如：\n\n"
                     "`/ask-agent8 今天團隊表現如何？`\n\n"
                     "**問題範例**：\n"
                     "• 今天團隊表現如何？\n"
                     "• 王小明本週表現如何？\n"
                     "• 健康度低於 50 的案件有哪些？\n"
                     "• Eats365 最近被提到幾次？"
            )
            return

        # 3. 發送「思考中」訊息
        thinking_msg = client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=f"🤔 正在分析您的問題...\n\n> {question}"
        )

        # 4. 使用 Agent 8 生成回答
        agent8 = get_agent8_instance()
        result = agent8.generate_answer(question, user_id)

        # 5. 回傳結果
        if result["success"]:
            # 準備回答訊息
            answer_text = f"💬 **問題**：{question}\n\n"
            answer_text += f"🤖 **Agent 8 回答**：\n\n{result['answer']}\n\n"
            answer_text += f"---\n"
            answer_text += f"📊 查詢了 {result['totalCases']} 個案件"

            # 如果是話題切換，加上提示
            if result.get("isTopicSwitch"):
                answer_text += " | 🔄 檢測到話題切換"

            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=answer_text
            )

            logger.info(f"Agent 8 回答成功：user={user_id}, cases={result['totalCases']}")

        else:
            # 錯誤訊息
            error_text = f"❌ 處理問題時發生錯誤：\n\n{result.get('error', '未知錯誤')}\n\n"
            error_text += "請稍後再試或聯絡系統管理員。"

            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=error_text
            )

            logger.error(f"Agent 8 處理失敗：user={user_id}, error={result.get('error')}")

    except SlackApiError as e:
        logger.error(f"Slack API 錯誤：{e.response['error']}", exc_info=True)
    except Exception as e:
        logger.error(f"處理命令時發生錯誤：{e}", exc_info=True)

        # 發送錯誤訊息給用戶
        try:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=f"❌ 系統錯誤，請稍後再試。\n\n錯誤訊息：{str(e)}"
            )
        except:
            pass
