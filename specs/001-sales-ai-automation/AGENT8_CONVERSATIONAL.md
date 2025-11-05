# Agent 8 對話式交互設計

**文檔目的**：設計業務主管與 Agent 8 的對話式交互功能，讓主管可以用自然語言詢問團隊數據。

**語言要求**：Agent 8 必須使用繁體中文（台灣用語習慣）與主管互動。

**最後更新**：2025-11-04

---

## 🎯 设计目标

### 核心价值
✅ **主动探索**：主管可以主动询问关心的问题，不只是被动接收固定报告
✅ **自然语言**：用日常对话方式提问，无需学习查询语法
✅ **即时洞察**：随时获取最新数据，不必等待定时报告
✅ **深度下钻**：从整体到个体，从趋势到细节，自由探索

### 使用场景示例

**场景 1：快速概览**
```
主管: 今天團隊表現如何？
Agent: 今天共完成 8 件案件，平均健康度 75 分。王小明表現優異（3 件，健康度 82），
       但陳美玲的 #202501-IC003 需要關注（健康度 45）。
```

**场景 2：个人业务深挖**
```
主管: 王小明這週的案件詳細情況？
Agent: 王小明本週完成 5 件案件：
       - 平均健康度 82（團隊第一）
       - 客戶信任度平均 85
       - 主要優勢：擅長需求挖掘，客戶關係建立良好
       - 需改進：結案速度偏慢，平均 5 天（團隊平均 3 天）

       最高優先級案件：#202501-IC008（健康度 90，預算已確認）
```

**场景 3：趋势分析**
```
主管: 本週 vs 上週，團隊健康度趨勢如何？
Agent: 本週平均健康度 75 分，較上週 72 分提升 4%（↑）
       主要原因：
       1. 王小明成功轉化 2 件競品案件
       2. 團隊整體預算溝通改善

       但需注意：李大華本週健康度下降 10% (68→61)，建議關注。
```

**场景 4：竞品情报**
```
主管: Eats365 最近被提到幾次？客戶怎麼評價？
Agent: 本週 Eats365 被提及 7 次（佔競品提及 40%）
       客戶評價：
       - 優點：價格便宜（5 次提及）
       - 缺點：功能不足（4 次）、客服差（2 次）

       我們的優勢：庫存管理、成本控管功能更強
       建議話術：強調長期 ROI，避免價格戰
```

**场景 5：产品需求洞察**
```
主管: 掃碼點餐功能的客戶需求度如何？
Agent: 本週「掃碼點餐」被討論 12 次：
       - 高意願：5 件（42%）
       - 中意願：4 件（33%）
       - 低意願：3 件（25%）

       主要障礙：
       1. 客群年齡（5 次）：「客人都是老人家不會用」
       2. 預算限制（3 次）

       建議：提供「混合模式」（人工+掃碼），降低顧慮
```

---

## 🏗️ 系统架构

### 整合到现有系统

**重要**：对话式 Agent 8 **复用现有的 `slack-service`**，不需要新的 Slack App 或 Cloud Run 服务！

### 整体流程

```
主管在 Slack 输入问题
      ↓
现有 slack-service (Cloud Run)
      ↓
   ┌──────────────────────────────────┐
   │ /ask-agent8 Command Handler      │
   │ （新增到现有 slack-service）      │
   └────────┬─────────────────────────┘
            ↓
   ┌─────────────────────────┐
   │ 1. 问题理解（Gemini）    │
   │    - 识别问题类型        │
   │    - 提取查询参数        │
   └────────┬────────────────┘
            ↓
   ┌─────────────────────────┐
   │ 2. 数据查询（Firestore）│
   │    - 动态构建查询        │
   │    - 获取相关案件        │
   └────────┬────────────────┘
            ↓
   ┌─────────────────────────┐
   │ 3. 数据分析（Gemini）   │
   │    - Agent 8 分析数据   │
   │    - 生成回答           │
   └────────┬────────────────┘
            ↓
      Slack 回复主管
```

### 现有 slack-service 的扩展

```
src/slack_app/
├── main.py                    # 现有主程序
├── events/
│   ├── file_upload_handler.py      # 现有：音频上传
│   └── dm_message_handler.py       # 现有：DM 消息处理
├── commands/
│   ├── upload_handler.py           # 现有：/录音分析 命令
│   └── ask_agent8_handler.py       # 🆕 新增：/ask-agent8 命令
├── interactions/
│   ├── analysis_button_handler.py  # 现有：分析按钮
│   ├── modal_handler.py            # 现有：Modal 提交
│   └── summary_actions_handler.py  # 现有：摘要相关按钮
└── agents/                          # 🆕 新增目录
    ├── question_parser.py           # 问题理解
    ├── data_fetcher.py              # 数据查询
    ├── conversation_manager.py      # 对话管理
    └── conversational_agent8.py     # Agent 8 客户端
```

**关键点**：
- ✅ 复用现有 Slack Bot Token
- ✅ 复用现有 Slack App 配置
- ✅ 只需添加新的 Command Handler
- ✅ 数据查询逻辑作为内部模块

---

## 💬 Slack 交互设计

### 触发方式

#### 方式 1：Slash Command（推荐）

```
/ask-agent8 今天團隊表現如何？
```

**优点**：
- 明确的触发方式
- 不会与其他对话混淆
- 可以在任何 Channel 使用

#### 方式 2：与 Bot DM（更自然）

```
主管直接在 Bot DM 中输入问题，Bot 自动识别并回答
```

**优点**：
- 更自然的对话体验
- 像与助理对话

**实现方式**：
```python
@app.event("message")
async def handle_dm_message(event, client):
    """处理主管在 DM 中的提问"""

    # 仅处理 DM
    channel_type = event.get("channel_type")
    if channel_type != "im":
        return

    # 检查是否为主管
    user_id = event["user"]
    if not is_manager(user_id):
        await client.chat_postMessage(
            channel=event["channel"],
            text="此功能僅限主管使用。如需查看個人案件分析，請使用 /my-cases"
        )
        return

    # 提取问题
    question = event["text"]

    # 调用对话式 Agent 8
    await process_manager_question(user_id, question, event["channel"], client)
```

### 对话界面示例

**用户体验流程**：

```
👤 主管: /ask-agent8 今天團隊表現如何？

🤖 Bot: [思考中...] ⏳

🤖 Bot:
📊 今日團隊表現報告

✅ 完成案件：8 件
📈 平均健康度：75 分
⏱️ 平均處理時間：42 分鐘

🏆 表現優異
• 王小明：3 件，平均健康度 82

⚠️ 需要關注
• 陳美玲：#202501-IC003（健康度 45）
  風險：預算限制，客戶猶豫
  建議：主管介入，提供彈性方案

[📊 查看完整報告] [💬 繼續提問]

---

👤 主管: 王小明本週的詳細情況？

🤖 Bot: [查詢中...] ⏳

🤖 Bot:
👤 王小明本週表現分析

📊 量化指標
• 案件數：5 件（團隊第一）
• 平均健康度：82 分
• 完成率：100%
• 客戶信任度：85

💪 主要優勢
• 需求挖掘深入，平均每案識別 3.2 個需求
• 客戶關係建立良好，信任度高於團隊平均 12%
• 決策者識別準確率 100%

📈 改進建議
• 結案速度偏慢（平均 5 天 vs 團隊 3 天）
• 建議：加強跟進節奏，使用標準化報價模板

🎯 優先案件
#202501-IC008 - 幸福餐廳
• 健康度：90 分
• 狀態：預算已確認，等待簽約
• 建議行動：本週內完成簽約

[查看所有案件] [比較其他業務]
```

---

## 🧠 对话式 Agent 8 Prompt 设计

### Prompt 结构

```markdown
# Agent 8: 業務主管對話助理

## 角色定義
你是 iCHEF 業務主管的智能助理，專門回答關於團隊銷售數據的問題。

## 對話原則
1. **簡潔明瞭**：優先提供核心洞察，避免冗長數據堆砌
2. **可操作**：每個回答都應包含具體建議
3. **上下文感知**：記住對話歷史，提供連貫回答
4. **主動引導**：在回答後提供相關問題建議

## 你能回答的問題類型

### 1️⃣ 團隊整體表現
- "今天/本週/本月團隊表現如何？"
- "團隊平均健康度趨勢？"
- "目前有哪些高風險案件？"

### 2️⃣ 個人業務績效
- "[業務名稱] 的表現如何？"
- "誰是本週表現最好的業務？"
- "[業務名稱] 需要改進什麼？"

### 3️⃣ 案件細節
- "#[案件編號] 的詳細分析？"
- "健康度 <60 的案件有哪些？"
- "哪些案件需要主管介入？"

### 4️⃣ 競品情報
- "[競品名稱] 最近被提到幾次？"
- "客戶對 [競品] 的評價？"
- "我們 vs [競品] 的優勢？"

### 5️⃣ 產品需求
- "[功能名稱] 的需求度如何？"
- "客戶最常提到哪些功能？"
- "最常見的障礙因素是什麼？"

### 6️⃣ 趨勢對比
- "本週 vs 上週的健康度變化？"
- "[業務] 的健康度趨勢？"
- "團隊處理時間有改善嗎？"

## 輸入數據格式

你會收到以下數據：

```json
{
  "question": "今天團隊表現如何？",
  "conversationHistory": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "timeRange": {
    "start": "2025-11-03 00:00",
    "end": "2025-11-03 23:59"
  },
  "relevantCases": [
    // Agent 1-6 的完整分析數據
  ],
  "teamStats": {
    "totalCases": 8,
    "avgHealthScore": 75,
    "completionRate": 0.875
  }
}
```

## 輸出格式

以繁體中文 Markdown 格式輸出，結構如下：

```markdown
[簡短總結一句話]

## [主要發現標題]
• 重點 1
• 重點 2

## [需要關注的事項]（如有）
• 風險 1：[描述] → 建議：[具體行動]

## [建議行動]（如有）
1. [具體、可執行的行動]

---
💡 **相關問題**：
• [建議的後續問題 1]
• [建議的後續問題 2]
```

## 回答範例

### 問題：「今天團隊表現如何？」

```markdown
今日團隊共完成 8 件案件，平均健康度 75 分，表現良好 ✅

## 🏆 表現優異
• **王小明**：3 件，平均健康度 82（客戶信任度高，需求挖掘深入）
• **李大華**：2 件，平均健康度 78

## ⚠️ 需要關注
• **陳美玲 - #202501-IC003**（健康度 45）
  - 風險：客戶預算敏感，決策者態度猶豫
  - 建議：**主管介入**，提供彈性付款方案

## 📊 團隊洞察
• 共同挑戰：60% 案件提及預算限制
• 成功模式：強調庫存管理功能的案件健康度高 15%

---
💡 **你可能還想知道**：
• 王小明本週的詳細表現？
• #202501-IC003 的完整分析？
• 如何應對預算限制挑戰？
```

### 問題：「王小明本週的表現？」

```markdown
王小明本週表現優異，5 件案件平均健康度 82 分（團隊第一）🥇

## 📊 量化指標
• 案件數：5 件
• 平均健康度：82 分
• 客戶信任度：85（高於團隊平均 12%）
• 完成率：100%

## 💪 主要優勢
• **需求挖掘**：平均每案識別 3.2 個需求（團隊平均 2.1）
• **客戶關係**：信任度建立快速，首次會議即達 80+
• **決策者識別**：100% 準確率

## 📈 改進建議
• **結案速度**：平均 5 天（團隊平均 3 天）
  → 建議：使用標準化報價模板，加快流程

## 🎯 優先案件
**#202501-IC008 - 幸福餐廳**（健康度 90）
• 狀態：預算已確認，等待簽約
• 建議：本週內完成簽約，避免競品介入

---
💡 **相關問題**：
• #202501-IC008 的詳細分析？
• 如何幫助王小明提升結案速度？
• 本週其他業務的排名？
```

## 注意事項

1. **數據為空時**：
   - 如果查詢時間範圍內無案件，明確告知
   - 提供替代查詢建議

2. **問題不清楚時**：
   - 禮貌詢問澄清
   - 提供常見問題範例

3. **權限控制**：
   - 僅回答主管有權限查看的數據
   - 保護業務個人隱私細節

4. **保持對話連貫**：
   - 使用 conversationHistory 理解上下文
   - 允許代詞（如「他」、「這個案件」）
```

---

## 🔧 技术实现

### 1. 问题理解与参数提取

```python
# conversational-agent8-service/src/question_parser.py

import google.generativeai as genai
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

class QuestionParser:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

    async def parse_question(self, question: str) -> Dict[str, Any]:
        """
        解析主管的问题，提取查询参数
        """

        prompt = f"""
你是問題分析專家。請分析以下主管問題，提取查詢參數。

問題：「{question}」

請以 JSON 格式輸出：
{{
  "questionType": "team_overview | personal_performance | case_detail | competitor_intel | product_demand | trend_comparison",
  "timeRange": "today | this_week | this_month | last_week | last_month",
  "specificPerson": "業務名稱（如有）",
  "specificCase": "案件編號（如有）",
  "specificCompetitor": "競品名稱（如有）",
  "specificFeature": "功能名稱（如有）",
  "filters": {{
    "minHealthScore": null,
    "maxHealthScore": null,
    "status": null
  }}
}}

範例：
- 「今天團隊表現如何？」 → questionType: team_overview, timeRange: today
- 「王小明本週的案件？」 → questionType: personal_performance, timeRange: this_week, specificPerson: 王小明
- 「健康度 <60 的案件？」 → questionType: case_detail, filters: {{maxHealthScore: 60}}
"""

        response = self.model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )

        return json.loads(response.text)
```

### 2. 动态数据查询

```python
# conversational-agent8-service/src/data_fetcher.py

from google.cloud import firestore
from datetime import datetime, timedelta
from typing import Dict, List, Any

class DataFetcher:
    def __init__(self):
        self.db = firestore.Client()

    async def fetch_relevant_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据问题参数动态查询 Firestore
        """

        # 构建时间范围
        time_range = self._build_time_range(params["timeRange"])

        # 构建查询
        query = self.db.collection('cases')
        query = query.where('createdAt', '>=', time_range["start"])
        query = query.where('createdAt', '<=', time_range["end"])

        # 应用过滤器
        if params.get("specificPerson"):
            query = query.where('salesRepName', '==', params["specificPerson"])

        if params["filters"].get("maxHealthScore"):
            query = query.where(
                'analysis.structured.dealHealth.score',
                '<=',
                params["filters"]["maxHealthScore"]
            )

        # 执行查询
        cases = []
        async for doc in query.stream():
            case_data = doc.to_dict()
            case_data['caseId'] = doc.id

            # 提取 Agent 1-6 数据
            cases.append(self._extract_agent_data(case_data))

        # 计算团队统计
        team_stats = self._calculate_team_stats(cases)

        return {
            "timeRange": time_range,
            "relevantCases": cases,
            "teamStats": team_stats,
            "totalCases": len(cases)
        }

    def _build_time_range(self, time_range_str: str) -> Dict[str, datetime]:
        """构建时间范围"""
        now = datetime.now()

        if time_range_str == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif time_range_str == "this_week":
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif time_range_str == "this_month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        # ... 其他时间范围

        return {"start": start, "end": end}

    def _calculate_team_stats(self, cases: List[Dict]) -> Dict[str, Any]:
        """计算团队统计"""
        if not cases:
            return {}

        health_scores = [
            case['agent6Analysis']['healthScore']
            for case in cases
            if case.get('agent6Analysis', {}).get('healthScore')
        ]

        return {
            "totalCases": len(cases),
            "avgHealthScore": sum(health_scores) / len(health_scores) if health_scores else 0,
            "completionRate": len([c for c in cases if c['status'] == 'completed']) / len(cases)
        }
```

### 3. 对话管理

```python
# conversational-agent8-service/src/conversation_manager.py

from google.cloud import firestore
from typing import List, Dict, Any

class ConversationManager:
    def __init__(self):
        self.db = firestore.Client()

    async def get_conversation_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """获取对话历史"""

        conv_ref = self.db.collection('conversations').document(user_id)
        conv = await conv_ref.get()

        if not conv.exists:
            return []

        history = conv.to_dict().get('history', [])
        return history[-limit:]  # 最近 10 条

    async def save_conversation(
        self,
        user_id: str,
        question: str,
        answer: str
    ):
        """保存对话记录"""

        conv_ref = self.db.collection('conversations').document(user_id)

        await conv_ref.set({
            'history': firestore.ArrayUnion([
                {
                    'role': 'user',
                    'content': question,
                    'timestamp': firestore.SERVER_TIMESTAMP
                },
                {
                    'role': 'assistant',
                    'content': answer,
                    'timestamp': firestore.SERVER_TIMESTAMP
                }
            ])
        }, merge=True)
```

### 4. 主流程集成（添加到现有 slack-service）

```python
# src/slack_app/commands/ask_agent8_handler.py
# 🆕 新文件：添加到现有 slack-service

from slack_bolt.async_app import AsyncApp
from ..agents.question_parser import QuestionParser
from ..agents.data_fetcher import DataFetcher
from ..agents.conversation_manager import ConversationManager
from ..agents.conversational_agent8 import ConversationalAgent8Client
import logging

logger = logging.getLogger(__name__)

# 初始化（在 main.py 中初始化一次）
question_parser = QuestionParser()
data_fetcher = DataFetcher()
conversation_manager = ConversationManager()
agent8_client = ConversationalAgent8Client()

def register_ask_agent8_handler(app: AsyncApp):
    """注册 /ask-agent8 命令处理器"""

    @app.command("/ask-agent8")
    async def handle_ask_agent8(ack, command, client):
        """处理 /ask-agent8 命令"""
        await ack()

        user_id = command["user_id"]
        question = command["text"]

        # 检查权限
        if not await is_manager(user_id):
            await client.chat_postEphemeral(
                channel=command["channel_id"],
                user=user_id,
                text="❌ 此功能僅限主管使用"
            )
            return

        # 显示"思考中"
        thinking_msg = await client.chat_postMessage(
            channel=command["channel_id"],
            text="🤔 正在分析數據..."
        )

        try:
            # 1. 解析问题
            params = await question_parser.parse_question(question)

            # 2. 获取对话历史
            history = await conversation_manager.get_conversation_history(user_id)

            # 3. 查询数据
            data = await data_fetcher.fetch_relevant_data(params)

            # 4. 调用 Agent 8 生成回答
            answer = await agent8_client.generate_answer({
                "question": question,
                "conversationHistory": history,
                "relevantCases": data["relevantCases"],
                "teamStats": data["teamStats"],
                "timeRange": data["timeRange"]
            })

            # 5. 保存对话
            await conversation_manager.save_conversation(user_id, question, answer)

            # 6. 更新消息
            await client.chat_update(
                channel=command["channel_id"],
                ts=thinking_msg["ts"],
                text=answer,
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": answer
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "💬 繼續提問"},
                                "action_id": "continue_conversation"
                            }
                        ]
                    }
                ]
            )

        except Exception as e:
            logger.error(f"Error processing question: {e}", exc_info=True)
            await client.chat_update(
                channel=command["channel_id"],
                ts=thinking_msg["ts"],
                text=f"❌ 抱歉，處理時發生錯誤：{str(e)}"
            )


# src/slack_app/main.py
# 在现有 main.py 中添加注册

from commands.ask_agent8_handler import register_ask_agent8_handler

# ... 现有代码 ...

# 注册所有 handlers
register_ask_agent8_handler(app)  # 🆕 新增这一行
```

---

## 📊 示例对话流程

### 完整对话示例

```
👤 主管: /ask-agent8 今天團隊表現如何？

🤖 Bot: 🤔 正在分析數據...

🤖 Bot:
今日團隊共完成 8 件案件，平均健康度 75 分，表現良好 ✅

## 🏆 表現優異
• **王小明**：3 件，平均健康度 82
• **李大華**：2 件，平均健康度 78

## ⚠️ 需要關注
• **陳美玲 - #202501-IC003**（健康度 45）
  - 風險：預算限制，決策者猶豫
  - 建議：主管介入，提供彈性方案

---
💡 **相關問題**：
• 王小明本週的表現？
• #202501-IC003 的詳細分析？
• 如何應對預算限制？

[💬 繼續提問]

---

👤 主管: 王小明本週的表現？

🤖 Bot: 🤔 查詢中...

🤖 Bot:
王小明本週表現優異，5 件案件平均健康度 82 分 🥇

## 📊 量化指標
• 案件數：5 件（團隊第一）
• 平均健康度：82 分
• 客戶信任度：85
• 完成率：100%

## 💪 主要優勢
• 需求挖掘深入
• 客戶關係良好
• 決策者識別準確

## 📈 改進建議
• 結案速度偏慢（5天 vs 團隊3天）
  → 使用標準化報價模板

## 🎯 優先案件
#202501-IC008 - 幸福餐廳（健康度 90）
建議：本週內完成簽約

[💬 繼續提問]

---

👤 主管: #202501-IC003 的詳細分析？

🤖 Bot: 🤔 查詢中...

🤖 Bot:
案件 #202501-IC003 - 美味廚房 ⚠️ 需要關注

## 📊 基本資訊
• 業務：陳美玲
• 客戶：美味廚房（中式餐廳）
• 健康度：45 分（低風險）
• 創建時間：3 天前

## 👥 參與者分析（Agent 1）
• 決策者：老闆（決策權力 85）
• 影響者：店長（決策權力 60）
• 老闆關注：成本、ROI

## 💭 情緒分析（Agent 2）
• 整體情緒：neutral
• 信任度：58（偏低）
• 反對信號：「月費太貴」「擔心員工不會用」

## 💰 產品需求（Agent 3）
• 預算：$20K-$30K（低於推薦方案 $45K）
• 需求：POS 基礎版 + 庫存管理
• 時間線：within_month（較急迫）

## 🏆 競品情況（Agent 4）
• 正在評估：Eats365（價格低）
• 客戶評價：便宜但功能不足

## ⚠️ 最大風險
預算限制可能導致選擇競品

## 💡 建議行動（優先級：高）
1. **主管介入**：提供彈性付款方案（12期分期）
2. **ROI試算**：量化成本節省（庫存+人力）
3. **競品比較**：強調長期價值 vs Eats365

[🔔 通知陳美玲] [📞 安排會議] [💬 繼續提問]
```

---

## 📈 数据价值

### 相比固定报告的优势

| 维度 | 固定报告 | 对话式 Agent 8 |
|------|---------|---------------|
| **灵活性** | 固定格式，无法自定义 | 随时提问任何关心的数据 |
| **时效性** | 每日/每周定时 | 即时查询最新数据 |
| **深度** | 固定深度 | 可以无限下钻 |
| **互动性** | 单向推送 | 双向对话 |
| **学习成本** | 需要学习报告结构 | 自然语言，无需学习 |
| **个性化** | 所有主管看相同报告 | 每位主管根据关注点提问 |

---

## 🚀 实施建议

### MVP 阶段（Phase 1）

✅ **必需功能**：
1. Slack `/ask-agent8` 命令
2. 支持 6 种基本问题类型：
   - 团队整体表现
   - 个人业务绩效
   - 案件详情
   - 竞品情报
   - 产品需求
   - 趋势对比
3. 简单的对话历史（最近 10 条）

### 进阶阶段（Phase 2）

🔄 **增强功能**：
1. 主动建议（"您可能还想知道..."）
2. 数据可视化（生成图表）
3. 多轮深度对话
4. 自定义查询保存（"我的常用查询"）
5. 定时提醒（"每天早上告诉我昨天的高风险案件"）

### 未来扩展（Phase 3）

🌟 **高级功能**：
1. 预测性分析（"下周可能需要关注哪些案件？"）
2. 异常检测（"有什么不寻常的情况吗？"）
3. 语音交互（Slack 语音消息）
4. 多语言支持
5. 与 CRM 系统集成

---

## 💰 成本估算

**重要**：因为复用现有 `slack-service`，只需要增加很少的成本！

| 项目 | 用量 | 成本/月 |
|------|------|---------|
| **Gemini API（问题解析）** | 主管提问 ~20 次/天 × 2K tokens | $0.10 |
| **Gemini API（回答生成）** | 主管提问 ~20 次/天 × 10K tokens | $0.50 |
| **Cloud Run（增量）** | 复用现有 slack-service，增量可忽略 | ~$0 |
| **Firestore 查询** | 20 次/天 × 30 天 × 50 reads | $0.02 |
| **总计** | | **~$0.62/月** |

✅ **几乎零额外成本**：复用现有基础设施
✅ **按需使用**：只有主管提问时才产生费用
✅ **远低于定时报告**：无需定时生成报告

---

## 🚀 部署步骤

### 1. Slack App 配置（只需添加新命令）

**在现有 Slack App 配置中添加**：

1. 进入 Slack App 管理页面：https://api.slack.com/apps
2. 选择现有的 Sales AI Bot
3. 进入 **Slash Commands** 页面
4. 点击 **Create New Command**：
   - Command: `/ask-agent8`
   - Request URL: `https://slack-service-[PROJECT_ID].run.app/slack/commands`（复用现有）
   - Short Description: `詢問團隊銷售數據`
   - Usage Hint: `今天團隊表現如何？`

5. 保存并重新安装 App 到 Workspace（如需要）

✅ **不需要新的 Bot Token**
✅ **不需要修改 OAuth 权限**
✅ **不需要新的服务**

---

### 2. 代码部署

```bash
# 1. 在现有 slack-service 中添加新文件
cd src/slack_app

# 2. 创建 agents 目录
mkdir -p agents

# 3. 添加新文件
# - commands/ask_agent8_handler.py
# - agents/question_parser.py
# - agents/data_fetcher.py
# - agents/conversation_manager.py
# - agents/conversational_agent8.py

# 4. 更新 main.py（添加注册）
# 在 main.py 中添加：
# from commands.ask_agent8_handler import register_ask_agent8_handler
# register_ask_agent8_handler(app)

# 5. 重新部署（复用现有部署流程）
gcloud run deploy slack-service \
  --source . \
  --region asia-east1 \
  --project sales-ai-automation-v2
```

✅ **复用现有 Dockerfile**
✅ **复用现有 Cloud Run 服务**
✅ **复用现有环境变量和 Secrets**

---

### 3. Firestore 索引（如需要）

如果查询需要复合索引，Firestore 会自动提示。通常需要：

```bash
# 为对话历史创建索引
gcloud firestore indexes composite create \
  --collection-group=conversations \
  --query-scope=COLLECTION \
  --field-config field-path=userId,order=ASCENDING \
  --field-config field-path=timestamp,order=DESCENDING
```

---

### 4. 权限配置

在 `src/slack_app/utils/permissions.py` 中添加主管列表：

```python
# 主管用户 ID 列表（Slack User ID）
MANAGER_USER_IDS = [
    "U12345ABC",  # 张主管
    "U67890XYZ",  # 李主管
    # ... 添加更多
]

async def is_manager(user_id: str) -> bool:
    """检查用户是否为主管"""
    return user_id in MANAGER_USER_IDS
```

或者从 Firestore 动态读取：

```python
async def is_manager(user_id: str) -> bool:
    """从 Firestore 检查用户权限"""
    db = firestore.AsyncClient()
    user_ref = db.collection('users').document(user_id)
    user = await user_ref.get()

    if not user.exists:
        return False

    user_data = user.to_dict()
    return user_data.get('role') == 'manager'
```

---

## 🧪 测试

### 本地测试

```bash
# 1. 启动本地 slack-service
cd src/slack_app
python -m uvicorn main:app --reload --port 3000

# 2. 使用 ngrok 暴露本地服务
ngrok http 3000

# 3. 更新 Slack App 的 Request URL 为 ngrok URL

# 4. 在 Slack 中测试
/ask-agent8 今天團隊表現如何？
```

### 单元测试

```python
# tests/test_ask_agent8.py

import pytest
from commands.ask_agent8_handler import question_parser

@pytest.mark.asyncio
async def test_question_parser():
    """测试问题解析"""
    result = await question_parser.parse_question("今天團隊表現如何？")

    assert result["questionType"] == "team_overview"
    assert result["timeRange"] == "today"
```

---

## 📚 相关文档

- [Agent 8 主管报告 Prompt](./agent8-manager-prompt.md)
- [Agent 8 实施计划](./agent8-implementation.md)
- [Agent 1-6 数据说明](./AGENT_DATA_FOR_MANAGERS.md)
- [Slack 工作流程](./slack-workflow.md)
- [现有 slack-service 架构](./plan.md#slack-service)

---

## ✅ 实施检查清单

### MVP 阶段（1-2 周）

- [ ] 在 Slack App 中添加 `/ask-agent8` 命令
- [ ] 创建 `agents/` 目录结构
- [ ] 实现 `question_parser.py`（问题理解）
- [ ] 实现 `data_fetcher.py`（数据查询）
- [ ] 实现 `conversation_manager.py`（对话管理）
- [ ] 实现 `conversational_agent8.py`（Agent 8 客户端）
- [ ] 在 `main.py` 中注册 handler
- [ ] 配置主管权限列表
- [ ] 本地测试
- [ ] 部署到 dev 环境
- [ ] 邀请主管测试
- [ ] 收集反馈并改进
- [ ] 部署到 production

### 可选增强（后续迭代）

- [ ] 添加数据可视化（图表生成）
- [ ] 添加主动建议（"你可能还想知道..."）
- [ ] 添加查询收藏功能
- [ ] 添加定时提醒功能
- [ ] 优化对话上下文理解

---

**文档维护**：此文档随实施进展更新

**下一步**：开始实施 MVP，让主管可以用自然语言提问！🚀
