"""
Agent 8 Slack 命令處理器

處理 /ask-agent8 命令，提供業務主管智能問答功能
"""

import os
import logging
import json
import time
from typing import Dict, Any, List

from google.cloud import firestore, tasks_v2

try:
    from slack_sdk import WebClient
except ModuleNotFoundError:  # pragma: no cover
    WebClient = Any

from ..mcp_adapter import MCPAdapter

logger = logging.getLogger(__name__)

# --- Environment Config ---
ANALYSIS_SERVICE_URL = os.environ.get("ANALYSIS_SERVICE_URL")
AGENT8_TASK_QUEUE = os.environ.get("AGENT8_TASK_QUEUE", "agent8-tasks")
TASK_LOCATION = os.environ.get("TASK_LOCATION", "asia-east1")
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
TASK_SERVICE_ACCOUNT = os.environ.get("TASK_SERVICE_ACCOUNT")

class Agent8Handler:
    def __init__(self, client: WebClient, db_client: firestore.Client, logger_instance):
        self.client = client
        self.db_client = db_client
        self.logger = logger_instance
        self.mcp = None  # MCP adapter (initialized per session)

    def check_manager_permission(self, user_id: str) -> bool:
        """Checks if a user has manager permissions in Firestore."""
        if not self.db_client:
            self.logger.error("Firestore client is not available for permission check.")
            return False
        try:
            user_doc = self.db_client.collection("users").document(user_id).get()
            if user_doc.exists and user_doc.to_dict().get("role") in ["manager", "admin"]:
                self.logger.info(f"Permission check PASSED for user {user_id}")
                return True
        except Exception as e:
            self.logger.error(f"Error checking permission for {user_id}: {e}", exc_info=True)
        
        self.logger.warning(f"Permission check FAILED for user {user_id}")
        return False

    def enqueue_agent8_task(self, payload: Dict[str, Any]):
        """Creates a Cloud Task to trigger the analysis service asynchronously."""
        tasks_client = tasks_v2.CloudTasksClient()
        parent = tasks_client.queue_path(GCP_PROJECT_ID, TASK_LOCATION, AGENT8_TASK_QUEUE)

        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": f"{ANALYSIS_SERVICE_URL}/ask-agent8",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(payload).encode(),
            }
        }

        if TASK_SERVICE_ACCOUNT:
            task["http_request"]["oidc_token"] = {
                "service_account_email": TASK_SERVICE_ACCOUNT
            }

        try:
            response = tasks_client.create_task(parent=parent, task=task)
            self.logger.info(f"Created Cloud Task: {response.name}")
            return response
        except Exception as e:
            self.logger.error(f"Error creating Cloud Task: {e}", exc_info=True)
            raise

    def handle_command(self, ack, command: Dict[str, Any]):
        """Handles the /ask-agent8 command by creating a Cloud Task with detailed timing."""
        start_time = time.time()
        self.logger.info("Agent 8 handler started.")

        ack()
        ack_time = time.time()
        self.logger.info(f"--- TIMING: ack() sent in {(ack_time - start_time) * 1000:.2f} ms ---")

        user_id = command.get("user_id")
        question = command.get("text", "").strip()
        channel_id = command.get("channel_id")
        session_id = f"{user_id}-{channel_id}-{time.time()}"

        try:
            # 1. Permission Check
            perm_start_time = time.time()
            has_permission = self.check_manager_permission(user_id)
            perm_end_time = time.time()
            self.logger.info(f"--- TIMING: Permission check took {(perm_end_time - perm_start_time) * 1000:.2f} ms ---")

            if not has_permission:
                self.client.chat_postEphemeral(channel=channel_id, user=user_id, text="❌ 您沒有使用此命令的權限。")
                return

            if not question:
                self.client.chat_postEphemeral(channel=channel_id, user=user_id, text="📝 請輸入問題。")
                return

            # 2. Post "thinking" message
            thinking_start_time = time.time()
            self.client.chat_postEphemeral(
                channel=channel_id, user=user_id, text=f"🤔 收到問題，正在為您分析...\n> {question}"
            )
            thinking_end_time = time.time()
            self.logger.info(f"--- TIMING: chat_postEphemeral took {(thinking_end_time - thinking_start_time) * 1000:.2f} ms ---")

            # 3. Handle user query with MCP
            answer = self.handle_user_query(question, session_id, user_id)
            self.client.chat_postEphemeral(channel=channel_id, user=user_id, text=answer)


        except Exception as e:
            self.logger.error(f"An unexpected error occurred in ask-agent8 handler: {e}", exc_info=True)
            try:
                self.client.chat_postEphemeral(channel=channel_id, user=user_id, text=f"❌ 處理您的問題時發生未預期的錯誤。")
            except Exception as slack_err:
                self.logger.error(f"Unable to send error message to Slack: {slack_err}")
        finally:
            end_time = time.time()
            self.logger.info(f"--- TIMING: Total handler execution time: {(end_time - start_time) * 1000:.2f} ms ---")

    def handle_user_query(self, user_query: str, session_id: str, user_id: str):
        """
        Handle user query with MCP tool support.
        """
        # Initialize MCP adapter for this session
        if self.mcp is None or self.mcp.session_id != session_id:
            self.mcp = MCPAdapter(
                session_id=session_id,
                tools_dir="tools",
                enable_pii_protection=True
            )

        # Infer if query requires data access
        needs_tools = self._needs_tools(user_query)

        if needs_tools:
            # Progressive tool discovery
            category = self._infer_tool_category(user_query)
            tools = self.mcp.discover_tools(category=category, detail_level="names")

            # Tool selection (can use LLM to select best tool)
            selected_tool = self._select_tool(tools, user_query)

            # Load tool definition
            tool_def = self.mcp.load_tool(selected_tool)

            # Construct parameters (can use LLM to extract from query)
            params = self._construct_tool_params(user_query, tool_def)

            # Execute tool with context optimization
            result = self.mcp.execute_tool(selected_tool, params, timeout=30)

            # Generate response based on tool result
            if result["status"] == "success":
                answer = self._generate_answer_with_data(user_query, result["result"])
            else:
                answer = f"抱歉，查詢資料時發生錯誤：{result.get('error', 'Unknown error')}"

            return answer
        else:
            # Direct LLM response (existing logic)
            return self._direct_gemini_response(user_query)

    def _direct_gemini_response(self, user_query: str) -> str:
        """Directly call Gemini for a response."""
        # This is a placeholder for the original logic of enqueuing a task
        # In a real scenario, you might call a different service or a direct LLM here.
        self.logger.info("Query does not require tools. Enqueuing a standard task.")
        task_payload = {
            "question": user_query,
            "user_id": "system", # Should be the actual user_id
            "slack_context": {}
        }
        self.enqueue_agent8_task(task_payload)
        return "您的問題已提交處理，請稍後。"

    def _needs_tools(self, query: str) -> bool:
        """Check if query requires data access tools."""
        # Simple keyword matching (can be enhanced with LLM classification)
        data_keywords = ["案件", "資料", "統計", "健康度", "客戶", "業務員", "團隊"]
        return any(kw in query for kw in data_keywords)

    def _infer_tool_category(self, query: str) -> str:
        """Infer required tool category from query."""
        if any(kw in query for kw in ["案件", "客戶", "業務員", "健康度"]):
            return "firestore"
        elif any(kw in query for kw in ["檔案", "上傳", "下載"]):
            return "gcs"
        elif any(kw in query for kw in ["SQL", "分析", "報表"]):
            return "bigquery"
        else:
            return "firestore"  # Default

    def _select_tool(self, tools: List[str], query: str) -> str:
        """Select most appropriate tool."""
        # Simple selection (can be enhanced with LLM reasoning)
        if "統計" in query or "平均" in query or "趨勢" in query:
            # Prefer aggregate tools
            for tool in tools:
                if "aggregate" in tool:
                    return tool

        # Default to first query tool
        for tool in tools:
            if "query" in tool:
                return tool

        return tools[0] if tools else "firestore.query"

    def _construct_tool_params(self, query: str, tool_def: dict) -> dict:
        """Construct tool parameters from query."""
        # TODO: Use LLM to extract entities and construct params
        # For now, return basic structure

        params = {
            "collection": "cases",  # Extract from query
            "filters": [],  # Extract from query
            "limit": 100,
            "context_mode": "minimal"  # Use minimal by default for token optimization
        }

        # Extract rep name if mentioned
        import re
        name_match = re.search(r"([\u4e00-\u9fff]{2,4})", query)
        if name_match:
            rep_name = name_match.group(1)
            params["filters"].append({
                "field": "rep_name",
                "op": "==",
                "value": rep_name
            })

        # Check if aggregate mode needed
        if any(kw in query for kw in ["平均", "統計", "趨勢", "分布"]):
            params["context_mode"] = "aggregate"

        return params

    def _generate_answer_with_data(self, query: str, data: Any) -> str:
        """Generate natural language answer based on query and data."""
        # TODO: Use Gemini to generate response
        # For now, return simple formatted response

        if isinstance(data, dict) and "results" in data:
            results = data["results"]
            if isinstance(results, list):
                return f"查詢結果：共找到 {len(results)} 筆資料\n{results[:3]}"  # Show first 3
            else:
                return f"統計結果：\n{results}"
        else:
            return str(data)

def handle_ask_agent8_command(
    ack, command: Dict[str, Any], client: WebClient, logger_instance, db_client: firestore.Client
):
    handler = Agent8Handler(client, db_client, logger_instance)
    handler.handle_command(ack, command)
