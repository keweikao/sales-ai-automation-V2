"""
Agent 8 核心模塊 - 對話式業務主管助理

整合問題解析、數據查詢和回答生成，提供自然語言的業務洞察
"""

import os
import json
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from .question_parser import QuestionParser, QuestionParams, QuestionType
from .data_fetcher import DataFetcher, QueryResult
from .conversation_manager import ConversationManager


class ConversationalAgent8:
    """對話式 Agent 8（支持多輪對話和話題切換）"""

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        test_mode: bool = False,
        storage_path: Optional[str] = None
    ):
        """
        初始化 Agent 8

        Args:
            gemini_api_key: Gemini API Key
            test_mode: 是否使用測試模式
            storage_path: 對話歷史儲存路徑
        """
        # 初始化問題解析器和數據查詢器
        self.parser = QuestionParser(gemini_api_key)
        self.fetcher = DataFetcher(test_mode=test_mode)
        self.conversation_manager = ConversationManager(storage_path)

        # 初始化 Gemini 模型用於生成回答
        api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY 未設定")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

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
            history_context = "\n\n對話歷史：\n"
            for msg in conversation_history[-2:]:  # 最近 2 輪
                history_context += f"用戶: {msg.get('question', '')}\n"
                history_context += f"你: {msg.get('answer', '')[:200]}...\n"

        # 話題切換提示
        topic_switch_note = ""
        if is_topic_switch:
            topic_switch_note = "\n\n**注意**：用戶切換了話題，這是一個新的問題方向。請重新搜集資訊並回答。\n"

        prompt = f"""你是 iCHEF 業務主管的智能助理 Agent 8，負責分析團隊銷售數據並提供可操作的管理建議。

## 你的特點

- **使用繁體中文**（台灣用語習慣）
- 專業但易懂（避免過度技術術語）
- 聚焦於「可操作的建議」而非僅描述數據
- 正面鼓勵為主，改進建議用建設性語言
- 使用台灣業務領域常用詞彙（如：「案件」、「業務」、「主管」等）

## 問題類型

問題類型是：**{params.type.value}**

不同類型的回答風格：
- **team_overview**: 提供團隊整體概況，突出亮點和風險
- **sales_rep_performance**: 分析個人表現，給出具體優劣勢和建議
- **case_details**: 深入分析案件，提供下一步行動
- **competitor_intelligence**: 整理競品情報，提供應對策略
- **product_demand**: 分析功能需求，建議產品策略
- **trend_comparison**: 對比趨勢，找出變化原因

## 數據

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

## 你的任務

1. **直接回答問題**（不要重複問題）
2. **提供關鍵數據**（量化指標）
3. **給出洞察**（發現模式和趨勢）
4. **提出建議**（具體、可執行的行動項）

## 回答格式

使用以下格式（根據問題類型調整）：

**簡短總結**（1-2 句話）

📊 **關鍵數據**
• 數據點 1
• 數據點 2

💡 **洞察**
• 洞察 1
• 洞察 2

✅ **建議**
• 建議 1
• 建議 2

**注意事項**：
- 如果案件數 < 3，提醒「數據量較少，分析僅供參考」
- 如果沒有相關數據，明確告知並建議其他查詢方向
- 數字保留 1 位小數
- 使用友善、專業的語氣

現在請回答：
"""
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
        user_id: str = "default_user",
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        生成回答（完整流程，支持多輪對話和話題切換）

        Args:
            question: 用戶問題
            user_id: 用戶 ID（用於管理對話歷史）
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
            return {
                "question": question,
                "answer": f"抱歉，處理問題時發生錯誤：{str(e)}",
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
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,  # 適中的溫度，保持回答自然但穩定
                max_output_tokens=1024,
            )
        )

        return response.text.strip()


# 單例模式
_agent_instance: Optional[ConversationalAgent8] = None


def get_agent8(test_mode: bool = False) -> ConversationalAgent8:
    """
    獲取 Agent 8 單例

    Args:
        test_mode: 是否使用測試模式

    Returns:
        ConversationalAgent8 實例
    """
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = ConversationalAgent8(test_mode=test_mode)
    return _agent_instance


if __name__ == "__main__":
    # 測試用
    import sys

    # 設置測試模式
    os.environ["TEST_MODE"] = "true"

    agent = ConversationalAgent8(test_mode=True)

    test_questions = [
        "今天團隊表現如何？",
        "王小明本週表現如何？",
        "健康度低於 50 的案件有哪些？",
        "Eats365 最近被提到幾次？",
        "掃碼點餐功能的需求如何？"
    ]

    print("=" * 60)
    print("Agent 8 對話式交互測試")
    print("=" * 60)

    conversation_history = []

    for i, q in enumerate(test_questions, 1):
        print(f"\n[問題 {i}] {q}")
        print("-" * 60)

        result = agent.generate_answer(q, conversation_history)

        if result["success"]:
            print(f"\n{result['answer']}")
            print(f"\n[數據] 查詢到 {result['totalCases']} 個案件")

            # 保存到對話歷史
            conversation_history.append({
                "question": q,
                "answer": result["answer"]
            })
        else:
            print(f"\n錯誤：{result['error']}")

        print("\n" + "=" * 60)

        # 只測試前 3 個問題
        if i >= 3:
            break
