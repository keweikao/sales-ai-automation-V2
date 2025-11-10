
"""
Agent 8 核心模塊 - 對話式業務主管助理

整合問題解析、數據查詢和回答生成，提供自然語言的業務洞察
使用優化的 Prompt v2
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

try:
    import vertexai
    from vertexai.generative_models import GenerationConfig, GenerativeModel
except ImportError:
    vertexai = None
    GenerativeModel = None
    GenerationConfig = None

from .question_parser import QuestionParser, QuestionParams, QuestionType
from .data_fetcher import DataFetcher, QueryResult
from .conversation_manager import ConversationManager

logger = logging.getLogger(__name__)


class ConversationalAgent8:
    """對話式 Agent 8（支持多輪對話和話題切換）"""

    def __init__(
        self,
        db_client: Optional = None,
        model_name: str = "gemini-1.0-pro"
    ):
        """
        初始化 Agent 8

        Args:
            db_client: Firestore Client（可選）
            model_name: Gemini 模型名稱
        """
        if vertexai is None or GenerativeModel is None:
            raise ValueError(
                "google-cloud-aiplatform 套件未安裝，無法呼叫 Gemini 模型。"
            )

        # Initialize Vertex AI SDK to use Application Default Credentials
        GCP_PROJECT = os.environ.get("GCP_PROJECT", "sales-ai-automation-v2")
        GCP_LOCATION = os.environ.get("GCP_LOCATION", "asia-east1")
        try:
            vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)
        except Exception as e:
            raise ValueError(f"Vertex AI 初始化失敗: {e}") from e

        # 初始化問題解析器和數據查詢器
        self.parser = QuestionParser(model_name=model_name)
        self.fetcher = DataFetcher(db_client=db_client)
        self.conversation_manager = ConversationManager(db_client=db_client)

        # 初始化 Gemini 模型用於生成回答（使用 Vertex AI SDK）
        self.model = GenerativeModel(model_name)

        # 載入 System Prompt v2
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """
        載入 System Prompt v2

        Returns:
            System Prompt 內容
        """
        prompt_path = Path(__file__).parent.parent / "prompts" / "agent8_system_prompt_v2.md"

        if prompt_path.exists():
            return prompt_path.read_text(encoding='utf-8')
        else:
            logger.warning(f"Prompt file not found at {prompt_path}, using fallback.")
            # 內嵌簡化版 Prompt v2
            return '''你是 iCHEF 業務主管的專屬智能助理 Agent 8。

## 核心特質

- **必須使用繁體中文**（台灣用語習慣）
- 使用台灣業務領域常用詞彙：「案件」、「業務」、「主管」、「客戶」
- 專業但親切，正面鼓勵為主
- 具體量化，避免模糊描述
- 建議要有「誰」、「做什麼」、「何時」

## 回答結構（必須遵守）

**簡短總結**（1-2 句話，直接回答問題核心）

📊 **關鍵數據**
• 數據點 1（必須量化）
• 數據點 2
• 數據點 3

💡 **洞察發現**
• 洞察 1（解釋「為什麼」，找出模式）
• 洞察 2（發現趨勢或異常）

✅ **建議行動**
• 建議 1：具體行動 + 負責人 + 時間
• 建議 2：具體行動 + 負責人 + 時間

## 禁止事項

❌ 不要：
- 使用簡體中文或大陸用語
- 過度讚美或過度批評
- 給出模糊建議
- 重複問題

✅ 要做：
- 使用繁體中文（台灣用語）
- 量化數據 + 質性洞察
- 具體、可執行的建議
- 友善、專業的語氣
'''

    def _build_answer_prompt(
        self,
        question: str,
        params: QuestionParams,
        query_result: QueryResult,
        conversation_history: Optional[List[Dict]] = None,
        context: Optional[Dict[str, Any]] = None,
        is_topic_switch: bool = False
    ) -> str:
        """
        建立生成回答的 Prompt

        Args:
            question: 用戶問題
            params: 解析後的參數
            query_result: 查詢結果
            conversation_history: 對話歷史
            context: 上下文資訊
            is_topic_switch: 是否切換話題

        Returns:
            完整的 Prompt
        """
        # 準備數據摘要
        cases_summary = self._prepare_cases_summary(query_result["relevantCases"])
        team_stats = query_result.get("teamStats", {})

        # 準備對話歷史
        history_context = ""
        if conversation_history:
            history_context = "\n\n## 對話歷史\n\n"
            for msg in conversation_history[-2:]:  # 最近 2 輪
                history_context += f"用戶: {msg.get('question', '')}\n"
                history_context += f"你: {msg.get('answer', '')[:200]}...\n\n"

        # 話題切換提示
        topic_switch_note = ""
        if is_topic_switch:
            topic_switch_note = "\n\n**注意**：用戶切換了話題，這是一個新的問題方向。請重新聚焦新問題並回答。\n"

        prompt = f'''{self.system_prompt}

## 當前任務

問題類型：**{params.type.value}**

### 團隊統計
```json
{json.dumps(team_stats, ensure_ascii=False, indent=2)}
```

### 相關案件
{cases_summary}

## 用戶問題

{question}
{history_context}
{topic_switch_note}

## 回答要求

1. **直接回答問題**（不要重複問題）
2. **提供關鍵數據**（量化指標）
3. **給出洞察**（發現模式和趨勢）
4. **提出建議**（具體、可執行的行動項）

現在請用繁體中文回答：
'''
        return prompt

    def _prepare_cases_summary(self, cases: List[Dict]) -> str:
        """
        準備案件摘要

        Args:
            cases: 案件列表

        Returns:
            案件摘要文字
        """
        if not cases:
            return "無相關案件"

        if len(cases) <= 5:
            # 少於 5 個案件，列出所有詳情
            summary = f"共 {len(cases)} 個案件：\n\n"
            for case in cases:
                health_score = case.get("analysis", {}).get("structured", {}).get("healthScore", 0)
                summary += f"- **{case['caseId']}** ({case['customerName']})\n"
                summary += f"  - 業務：{case['salesRepName']}\n"
                summary += f"  - 健康度：{health_score} 分\n"
                summary += f"  - 階段：{case.get('analysis', {}).get('structured', {}).get('salesStage', '未知')}\n"

                # 風險
                risk = case.get("analysis", {}).get("structured", {}).get("maximumRisk", {})
                if risk and risk.get("risk"):
                    summary += f"  - 風險：{risk['risk']}\n"

                summary += "\n"
        else:
            # 多於 5 個案件，提供統計和前 3 個案例
            summary = f"共 {len(cases)} 個案件，以下是統計和代表案例：\n\n"

            # 統計
            health_scores = [
                c.get("analysis", {}).get("structured", {}).get("healthScore", 0)
                for c in cases
            ]
            avg_health = sum(health_scores) / len(health_scores) if health_scores else 0
            summary += f"**統計**：\n"
            summary += f"- 平均健康度：{avg_health:.1f} 分\n"
            summary += f"- 健康度分布：{min(health_scores)}-{max(health_scores)} 分\n\n"

            # 前 3 個案例
            summary += f"**代表案例**：\n\n"
            for case in cases[:3]:
                health_score = case.get("analysis", {}).get("structured", {}).get("healthScore", 0)
                summary += f"- **{case['caseId']}** ({case['salesRepName']} / {case['customerName']})\n"
                summary += f"  - 健康度：{health_score} 分\n\n"

        return summary

    def generate_answer(
        self,
        question: str,
        user_id: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        生成回答（完整流程，支持多輪對話和話題切換）

        Args:
            question: 用戶問題
            user_id: 用戶 ID（Slack User ID）
            conversation_history: 對話歷史（可選，如果不提供則自動從管理器獲取）

        Returns:
            包含 answer 和中間結果的 Dict
        """
        try:
            # 1. 獲取對話歷史（如果沒有提供）
            if conversation_history is None:
                conversation_history = self.conversation_manager.get_conversation_history(
                    user_id, limit=5
                )

            # 2. 獲取上下文資訊
            context = self.conversation_manager.get_context(user_id, question)

            # 3. 解析問題
            params = self.parser.parse_question_sync(question, conversation_history)

            # 4. 檢查是否切換話題
            is_topic_switch = self.conversation_manager.is_topic_switch(
                user_id,
                params.type.value,
                params.model_dump(exclude_none=True)
            )

            # 5. 查詢數據
            query_result = self.fetcher.fetch_relevant_data(params)

            # 6. 生成回答
            answer = self._generate_answer_text(
                question,
                params,
                query_result,
                conversation_history,
                context,
                is_topic_switch
            )

            # 7. 儲存對話
            self.conversation_manager.save_conversation(
                user_id=user_id,
                question=question,
                answer=answer,
                params=params.model_dump(exclude_none=True),
                total_cases=query_result["totalCases"],
                metadata={
                    "isTopicSwitch": is_topic_switch,
                    "hasPronouns": context.get("hasPronouns", False)
                }
            )

            logger.info(f"Agent 8 回答成功：user={user_id}, type={params.type.value}, cases={query_result['totalCases']}")

            return {
                "question": question,
                "answer": answer,
                "params": params.model_dump(exclude_none=True),
                "totalCases": query_result["totalCases"],
                "teamStats": query_result.get("teamStats", {}),
                "context": context,
                "isTopicSwitch": is_topic_switch,
                "success": True
            }

        except Exception as e:
            logger.error(f"Agent 8 處理問題失敗：{e}", exc_info=True)
            return {
                "question": question,
                "answer": f"抱歉，處理問題時發生錯誤。請稍後再試或聯絡系統管理員。",
                "success": False,
                "error": str(e)
            }

    def _generate_answer_text(
        self,
        question: str,
        params: QuestionParams,
        query_result: QueryResult,
        conversation_history: Optional[List[Dict]] = None,
        context: Optional[Dict[str, Any]] = None,
        is_topic_switch: bool = False
    ) -> str:
        """
        使用 Gemini 生成回答文字

        Args:
            question: 用戶問題
            params: 解析後的參數
            query_result: 查詢結果
            conversation_history: 對話歷史
            context: 上下文資訊
            is_topic_switch: 是否切換話題

        Returns:
            回答文字
        """
        prompt = self._build_answer_prompt(
            question,
            params,
            query_result,
            conversation_history,
            context,
            is_topic_switch
        )

        response = self.model.generate_content(
            prompt,
            generation_config=GenerationConfig(
                temperature=0.7,  # 適中的溫度，保持回答自然但穩定
                max_output_tokens=1024,
            )
        )

        return response.text.strip()

