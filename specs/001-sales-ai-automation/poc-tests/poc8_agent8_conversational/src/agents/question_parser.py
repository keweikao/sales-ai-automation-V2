"""
問題解析模塊 - 使用 Gemini 解析自然語言問題並提取查詢參數

支持 6 大類問題：
1. team_overview - 團隊整體表現
2. sales_rep_performance - 個人業務績效
3. case_details - 案件詳細分析
4. competitor_intelligence - 競品情報
5. product_demand - 產品需求洞察
6. trend_comparison - 趨勢對比
"""

import os
import json
from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel
import google.generativeai as genai


class QuestionType(str, Enum):
    """問題類型"""
    TEAM_OVERVIEW = "team_overview"
    SALES_REP_PERFORMANCE = "sales_rep_performance"
    CASE_DETAILS = "case_details"
    COMPETITOR_INTELLIGENCE = "competitor_intelligence"
    PRODUCT_DEMAND = "product_demand"
    TREND_COMPARISON = "trend_comparison"


class QuestionParams(BaseModel):
    """解析後的問題參數"""
    type: QuestionType
    timeRange: Optional[str] = None  # "today", "this_week", "this_month", "recent"
    salesRepName: Optional[str] = None
    salesRepId: Optional[str] = None
    caseId: Optional[str] = None
    customerName: Optional[str] = None
    competitorName: Optional[str] = None
    feature: Optional[str] = None
    metric: Optional[str] = None
    healthScoreMin: Optional[int] = None
    healthScoreMax: Optional[int] = None
    salesStage: Optional[str] = None
    compareRange: Optional[list] = None
    sort: Optional[str] = None
    filter: Optional[str] = None
    focus: Optional[str] = None


class QuestionParser:
    """問題解析器"""

    def __init__(self, gemini_api_key: Optional[str] = None):
        """
        初始化問題解析器

        Args:
            gemini_api_key: Gemini API Key，如果不提供則從環境變數讀取
        """
        api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY 未設定")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

    def _build_parsing_prompt(self, question: str, conversation_history: Optional[list] = None) -> str:
        """
        建立問題解析的 Prompt

        Args:
            question: 用戶問題
            conversation_history: 對話歷史

        Returns:
            完整的 Prompt
        """
        history_context = ""
        if conversation_history:
            history_context = "\n\n對話歷史：\n"
            for msg in conversation_history[-3:]:  # 只取最近 3 輪
                history_context += f"用戶: {msg.get('question', '')}\n"
                history_context += f"AI: {msg.get('answer', '')[:100]}...\n"

        prompt = f"""你是 Agent 8 的問題解析助手，負責分析業務主管的問題並提取查詢參數。

## 問題類型定義

1. **team_overview** - 團隊整體表現
   - 例如：「今天團隊表現如何？」「本週完成幾件案件？」「有哪些案件需要關注？」

2. **sales_rep_performance** - 個人業務績效
   - 例如：「王小明本週表現如何？」「誰的健康度最低？」「陳美玲有什麼問題？」

3. **case_details** - 案件詳細分析
   - 例如：「#202501-IC003 的情況如何？」「健康度低於 50 的案件有哪些？」

4. **competitor_intelligence** - 競品情報
   - 例如：「Eats365 最近被提到幾次？」「客戶對競品的評價如何？」

5. **product_demand** - 產品需求洞察
   - 例如：「掃碼點餐功能的需求如何？」「最熱門的功能是什麼？」

6. **trend_comparison** - 趨勢對比
   - 例如：「本週 vs 上週，健康度有什麼變化？」「王小明本月跟上月比較如何？」

## 時間範圍對應

- 「今天」→ "today"
- 「本週」、「這週」→ "this_week"
- 「上週」→ "last_week"
- 「本月」→ "this_month"
- 「上月」→ "last_month"
- 「最近」→ "recent"

## 任務

分析以下問題，識別問題類型並提取所有相關參數。{history_context}

**用戶問題**：{question}

請以 JSON 格式輸出，schema 如下：

```json
{{
  "type": "問題類型",
  "timeRange": "時間範圍或 null",
  "salesRepName": "業務名字或 null",
  "caseId": "案件 ID 或 null",
  "customerName": "客戶名字或 null",
  "competitorName": "競品名字或 null",
  "feature": "功能名稱或 null",
  "metric": "指標類型或 null",
  "healthScoreMin": 健康度最小值或 null,
  "healthScoreMax": 健康度最大值或 null,
  "salesStage": "銷售階段或 null",
  "compareRange": ["時間1", "時間2"] 或 null,
  "sort": "排序方式或 null",
  "filter": "篩選條件或 null",
  "focus": "焦點方向或 null"
}}
```

**重要**：
1. 必須輸出有效的 JSON
2. 只輸出 JSON，不要有其他文字
3. 如果問題使用代詞（「他」、「這個」、「那個」），請根據對話歷史推斷指代對象
4. 時間範圍預設為 "recent" 如果沒有明確指定
"""
        return prompt

    async def parse_question(
        self,
        question: str,
        conversation_history: Optional[list] = None
    ) -> QuestionParams:
        """
        解析用戶問題

        Args:
            question: 用戶問題
            conversation_history: 對話歷史（用於理解代詞和上下文）

        Returns:
            QuestionParams: 解析後的參數

        Raises:
            ValueError: 如果解析失敗
        """
        try:
            prompt = self._build_parsing_prompt(question, conversation_history)

            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,  # 低溫度確保穩定輸出
                )
            )

            # 提取 JSON
            response_text = response.text.strip()

            # 移除可能的 markdown code fence
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            # 解析 JSON
            parsed_data = json.loads(response_text)

            # 驗證並創建 QuestionParams
            params = QuestionParams(**parsed_data)

            return params

        except json.JSONDecodeError as e:
            raise ValueError(f"Gemini 回應不是有效的 JSON: {response_text}") from e
        except Exception as e:
            raise ValueError(f"問題解析失敗: {str(e)}") from e

    def parse_question_sync(
        self,
        question: str,
        conversation_history: Optional[list] = None
    ) -> QuestionParams:
        """
        解析用戶問題（同步版本）

        Args:
            question: 用戶問題
            conversation_history: 對話歷史

        Returns:
            QuestionParams: 解析後的參數
        """
        try:
            prompt = self._build_parsing_prompt(question, conversation_history)

            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                )
            )

            response_text = response.text.strip()

            # 移除 markdown code fence
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            parsed_data = json.loads(response_text)
            params = QuestionParams(**parsed_data)

            return params

        except json.JSONDecodeError as e:
            raise ValueError(f"Gemini 回應不是有效的 JSON: {response_text}") from e
        except Exception as e:
            raise ValueError(f"問題解析失敗: {str(e)}") from e


# 單例模式，避免重複初始化
_parser_instance: Optional[QuestionParser] = None


def get_question_parser() -> QuestionParser:
    """
    獲取 QuestionParser 單例

    Returns:
        QuestionParser 實例
    """
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = QuestionParser()
    return _parser_instance


if __name__ == "__main__":
    # 測試用
    import asyncio

    async def test():
        parser = QuestionParser()

        test_questions = [
            "今天團隊表現如何？",
            "王小明本週表現如何？",
            "#202501-IC003 的情況如何？",
            "Eats365 最近被提到幾次？",
            "掃碼點餐功能的需求如何？",
            "本週 vs 上週，健康度有什麼變化？"
        ]

        for q in test_questions:
            print(f"\n問題: {q}")
            try:
                params = parser.parse_question_sync(q)
                print(f"類型: {params.type}")
                print(f"參數: {params.model_dump(exclude_none=True)}")
            except Exception as e:
                print(f"錯誤: {e}")

    asyncio.run(test())
