# Quick Start Guide for AI Assistants

**Purpose**: Enable any AI assistant to quickly understand project context and continue development.

**Reading Time**: 5 minutes

---

## 🚀 Start Here (Essential Reading Order)

### 1️⃣ 如何啟動 AI 開發 (How to Start an AI Task)

當您準備好開始一項新任務時，請使用一個簡單、高層次的指令來啟動 AI。您不需要記住所有流程細節。

**建議指令：**

> **「請遵循標準作業流程，開始執行下一個開發任務。」**

或更簡單的：

> **「請開始下一個開發任務。」**

收到此指令後，AI 將會自動執行「工作前啟動檢查清單」：

1. 與遠端同步，確保程式碼與文件為最新。
2. 閱讀 `DEVELOPMENT_LOG.md`，分析 `Outstanding Work Tracker`。
3. 從待辦事項中選擇一個任務。
4. **執行開發前置評估（見本檔案「開發前置檢查清單」段落）** ⭐ **新增**
   - 檢查是否需要建置 MCP Server
   - 評估是否使用 Subagent
   - 選擇最經濟的開發方式
5. 向您**提案**要執行的任務、使用方法、預期成本並請求**確認**。
6. 在您同意後，開始執行。

這個標準化指令確保了開發流程的一致性與可預測性，同時優化 Token 使用成本。

---

## ✅ 開發前置檢查清單 (Pre-Development Assessment)（已整併於本指南）

> **強制執行**：任何新功能、新服務、bug 修復開始前，必須先完成此檢查
> **目標**：確保選擇最經濟、最高效的開發方式（MCP > Subagent > 直接工具）

---

## 🚨 STOP - 在開始寫程式碼前

### 第一步：任務分析（5 分鐘思考時間）

回答以下 4 個問題：

```
┌──────────────────────────────────────────────────────────┐
│ 1. 這個任務需要呼叫哪些外部服務/API？                      │
│    □ Google Cloud (GCS, Firestore, Cloud Run, Logging...)│
│    □ Slack API                                            │
│    □ Gemini/Vertex AI API                                 │
│    □ 其他：_______________                                │
│                                                           │
│ 2. 這個任務需要讀取/搜尋多少檔案？                        │
│    □ 1-3 個已知檔案 → 直接工具                           │
│    □ 3-10 個檔案或不確定位置 → Subagent (Explore)         │
│    □ 10+ 個檔案或全專案搜尋 → Subagent (general)          │
│                                                           │
│ 3. 這個任務需要多輪試錯嗎？                               │
│    □ 否（需求明確） → 直接工具                            │
│    □ 是（測試參數、模型、配置） → Subagent               │
│                                                           │
│ 4. 這個任務會重複執行嗎？                                 │
│    □ 一次性任務 → 直接工具                                │
│    □ 可能重複（批次操作、定期查詢） → MCP Server          │
└──────────────────────────────────────────────────────────┘
```

---

## 📋 決策流程圖

```
收到開發任務
    ↓
┌────────────────────────────┐
│ 步驟 1: 檢查現有 MCP Server │ ← 【強制執行】
└────────────────────────────┘
    ↓
執行指令: ls ~/.claude/mcp_config.json
    ↓
    ├─ 存在 → 檢查已配置的 servers
    │          cat ~/.claude/mcp_config.json | jq '.mcpServers | keys'
    │
    └─ 不存在 → 建立空白配置
               mkdir -p ~/.claude && echo '{"mcpServers":{}}' > ~/.claude/mcp_config.json

    ↓
┌────────────────────────────┐
│ 步驟 2: 評估是否需要新 MCP  │ ← 【成本決策點】
└────────────────────────────┘
    ↓
    問自己：
    1. 這個 API 會呼叫超過 3 次嗎？
    2. 這個 API 回傳的資料量大嗎（>1000 行）？
    3. 是否需要快取結果？

    ↓
    任一答案是 YES → 需要建置 MCP Server
    ↓
┌──────────────────────────────────┐
│ 步驟 3: 建置 MCP Server (15 分鐘) │
└──────────────────────────────────┘
    ↓
    選擇建置方式：

    ┌─────────────────────────────────────────┐
    │ 方式 A: 使用現成的 MCP Server (優先)     │
    │ - Anthropic 官方: @modelcontextprotocol  │
    │ - 社群套件: awesome-mcp-servers          │
    │ 安裝指令:                                │
    │   npm install -g @modelcontextprotocol/server-gcloud │
    └─────────────────────────────────────────┘

    ┌─────────────────────────────────────────┐
    │ 方式 B: 自行包裝（無現成 server 時）     │
    │ - 建立 tools/{service_name}/             │
    │ - 實作 Python function                   │
    │ - 使用 MCP SDK 包裝                       │
    │ 參考: tools/firestore/query.py           │
    └─────────────────────────────────────────┘

    ↓
    更新 ~/.claude/mcp_config.json
    ↓
    測試 MCP tool 是否可用（執行範例呼叫）
    ↓
┌────────────────────────────┐
│ 步驟 4: 評估是否需要 Subagent │
└────────────────────────────┘
    ↓
    問自己：
    1. 需要探索大型檔案/未知結構嗎？
    2. 需要多輪試錯嗎？
    3. 預期會產生大量中間輸出嗎？

    ↓
    任一答案是 YES → 使用 Subagent
    ↓
    選擇 Subagent 類型：
    - subagent_type="Explore" → 程式碼探索
    - subagent_type="general-purpose" → 試錯、測試
    - model="haiku" → 降低 Subagent 內部成本

    ↓
┌────────────────────────────┐
│ 步驟 5: 開始實際開發        │
└────────────────────────────┘
    ↓
    優先順序：
    1. 使用 MCP tools（如果步驟 3 已建置）
    2. 使用 Subagent（如果步驟 4 判斷需要）
    3. 使用直接工具（Read/Edit/Bash）
```

---

## 🛠️ MCP Server 建置 SOP

### 場景 1: Google Cloud 操作

**需求識別**：
- 需要呼叫 `gcloud` 命令 3 次以上
- 需要讀取 Cloud Logging、查詢 Firestore、管理 Cloud Run

**建置步驟**：

```bash
# 1. 安裝官方 MCP server（如果有）
npm install -g @modelcontextprotocol/server-gcloud

# 2. 配置 MCP config
cat >> ~/.claude/mcp_config.json <<'EOF'
{
  "mcpServers": {
    "gcloud": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-gcloud"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/service-account.json",
        "GCP_PROJECT": "sales-ai-automation-v2",
        "GCP_LOCATION": "asia-east1"
      }
    }
  }
}
EOF

# 3. 重啟 Claude Code 或重新載入配置

# 4. 測試是否可用
# 在下次對話中應該會看到 mcp__gcloud 工具可用
```

**成本效益**：
- 建置時間：10 分鐘
- Token 節省：85%（每次呼叫從 ~5000 tokens → ~750 tokens）
- 適用任務：日誌查詢、服務部署、資源管理

---

### 場景 2: 自定義 API（無現成 MCP Server）

**需求識別**：
- 需要呼叫內部 API 或第三方 API
- 預期會重複呼叫 5 次以上
- API 回傳資料需要過濾/摘要

**建置步驟**：

```bash
# 1. 建立 tool 目錄結構
mkdir -p tools/my_service
touch tools/my_service/__init__.py

# 2. 實作 Python function
cat > tools/my_service/query.py <<'EOF'
"""
MCP Tool: My Service Query

Provides filtered access to MyService API with automatic data summarization.
"""
import os
import requests
from typing import Dict, Any, List, Optional

def query_my_service(
    endpoint: str,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 10,
    fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Query MyService API with filtering and field selection.

    Args:
        endpoint: API endpoint path (e.g., "/api/cases")
        filters: Filter criteria (e.g., {"status": "active"})
        limit: Maximum number of results
        fields: Fields to return (reduces token usage)

    Returns:
        Filtered and summarized results
    """
    api_base = os.environ.get("MY_SERVICE_API_BASE")
    api_key = os.environ.get("MY_SERVICE_API_KEY")

    # Call API
    response = requests.get(
        f"{api_base}{endpoint}",
        headers={"Authorization": f"Bearer {api_key}"},
        params=filters or {}
    )
    response.raise_for_status()

    # Filter results
    results = response.json()

    # Apply limit
    if isinstance(results, list):
        results = results[:limit]

    # Filter fields (token optimization)
    if fields:
        results = [
            {k: item[k] for k in fields if k in item}
            for item in results
        ]

    return {
        "count": len(results),
        "data": results,
        "truncated": len(response.json()) > limit
    }

# MCP Tool Definition
TOOL_DEFINITION = {
    "name": "my_service_query",
    "description": "Query MyService API with automatic filtering and summarization",
    "inputSchema": {
        "type": "object",
        "properties": {
            "endpoint": {"type": "string", "description": "API endpoint path"},
            "filters": {"type": "object", "description": "Filter criteria"},
            "limit": {"type": "integer", "default": 10},
            "fields": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["endpoint"]
    }
}
EOF

# 3. 建立 MCP server wrapper
cat > tools/my_service/mcp_server.py <<'EOF'
"""MCP Server for MyService"""
import sys
import json
from typing import Any
from query import query_my_service, TOOL_DEFINITION

def handle_tool_call(tool_name: str, arguments: dict) -> Any:
    if tool_name == "my_service_query":
        return query_my_service(**arguments)
    else:
        raise ValueError(f"Unknown tool: {tool_name}")

if __name__ == "__main__":
    # Simple MCP protocol handler
    for line in sys.stdin:
        request = json.loads(line)

        if request["method"] == "tools/list":
            response = {"tools": [TOOL_DEFINITION]}
        elif request["method"] == "tools/call":
            tool_name = request["params"]["name"]
            arguments = request["params"]["arguments"]
            response = handle_tool_call(tool_name, arguments)

        print(json.dumps(response))
        sys.stdout.flush()
EOF

# 4. 配置到 MCP config
cat >> ~/.claude/mcp_config.json <<'EOF'
{
  "mcpServers": {
    "my_service": {
      "command": "python3",
      "args": ["/path/to/tools/my_service/mcp_server.py"],
      "env": {
        "MY_SERVICE_API_BASE": "https://api.example.com",
        "MY_SERVICE_API_KEY": "${MY_SERVICE_API_KEY}"
      }
    }
  }
}
EOF

# 5. 測試
python3 tools/my_service/mcp_server.py
# 輸入: {"method": "tools/list"}
# 應回傳: {"tools": [{"name": "my_service_query", ...}]}
```

**成本效益**：
- 建置時間：15-20 分鐘
- Token 節省：90%（過濾 + 欄位選擇）
- 適用任務：內部 API、第三方整合

---

## 🤖 Subagent 使用 SOP

### 場景 3: 程式碼探索（不知道檔案在哪）

**識別條件**：
- 需要搜尋 "所有實作 X 的檔案"
- 需要理解 "系統架構"
- 不確定要讀哪些檔案

**使用範例**：

```python
# ❌ 錯誤做法（佔用主對話 context）
Glob(pattern="**/*.py")  # → 回傳 500 個檔案
Grep(pattern="class.*Agent")  # → 50 個結果
Read("file1.py")  # → 2000 tokens
Read("file2.py")  # → 2000 tokens
# 總計：~8000 tokens 累積在主對話

# ✅ 正確做法（使用 Subagent）
Task(
    subagent_type="Explore",
    description="探索 Agent 架構",
    prompt="""
    找出專案中所有 Agent 類別的實作。

    回傳格式（只要摘要，不要完整程式碼）：
    - 檔案路徑
    - 類別名稱
    - 主要功能（一句話）
    - 使用的 LLM 模型

    範例輸出：
    1. analysis-service/src/agents/agent1_participant.py
       - ParticipantProfileAgent
       - 識別通話參與者
       - Model: gemini-2.5-flash
    """,
    model="haiku"  # 使用便宜模型
)
# → 只回傳摘要，消耗 ~800 tokens
```

---

### 場景 4: 多輪試錯（測試參數、模型）

**識別條件**：
- 需要測試多個參數組合
- 不確定哪個配置會成功
- 預期會失敗 3 次以上

**使用範例**：

```python
# ❌ 錯誤做法（每次失敗都累積 context）
Bash("python test.py --model=gemini-pro")  # 失敗 → +1000 tokens
Bash("python test.py --model=gemini-1.5-flash")  # 失敗 → +1000 tokens
Bash("python test.py --model=gemini-flash-latest")  # 成功 → +1000 tokens
# 總計：3000 tokens（3 次失敗都在主對話）

# ✅ 正確做法（使用 Subagent 隔離試錯）
Task(
    subagent_type="general-purpose",
    description="測試可用的 Gemini 模型",
    prompt="""
    測試以下 Gemini 模型哪些可用：
    - gemini-pro
    - gemini-1.5-flash
    - gemini-flash-latest
    - gemini-2.5-flash
    - gemini-2.5-pro

    每個模型執行 test.py，記錄成功/失敗。

    只回傳：
    - 第一個成功的模型名稱
    - 失敗模型的錯誤類型（404/403/500）

    不要回傳完整錯誤訊息或程式碼。
    """,
    model="haiku"
)
# → 只回傳成功的模型名稱，消耗 ~500 tokens
# → Subagent 內部的試錯過程不累積到主對話
```

---

## 📊 決策矩陣速查表

| 任務類型 | 呼叫次數 | 資料量 | 試錯 | 推薦方法 | Token 節省 | 建置時間 |
|---------|---------|--------|------|---------|-----------|---------|
| GCP API 呼叫 | 3+ | 大 | 否 | **MCP** | 85% | 10 分鐘 |
| Firestore 批次查詢 | 5+ | 大 | 否 | **MCP** | 90% | 10 分鐘 |
| Slack 通知 | 任意 | 小 | 否 | **MCP** | 95% | 5 分鐘 |
| 程式碼探索 | 1 | 大 | 是 | **Subagent** | 70% | 0 分鐘 |
| 參數測試 | 1 | 中 | 是 | **Subagent** | 60% | 0 分鐘 |
| 錯誤診斷 | 1 | 大 | 是 | **Subagent** | 75% | 0 分鐘 |
| 單檔案修改 | 1 | 小 | 否 | **直接工具** | 0% | 0 分鐘 |
| 簡單命令 | 1 | 小 | 否 | **直接工具** | 0% | 0 分鐘 |

---

## ✅ 開發前檢查清單（複製使用）

每次開始任務前，複製以下 checklist 到對話中：

```markdown
## 開發前評估

### 任務：[任務描述]

### 檢查項目
- [ ] **步驟 1**: 檢查現有 MCP servers
  - 已配置: [列出]
  - 缺少: [列出]

- [ ] **步驟 2**: 評估是否需要新 MCP
  - API 呼叫次數: [次數]
  - 是否需要建置: [是/否]
  - 建置方式: [現成套件/自行實作/不需要]

- [ ] **步驟 3**: 評估是否需要 Subagent
  - 探索未知檔案: [是/否]
  - 多輪試錯: [是/否]
  - Subagent 類型: [Explore/general-purpose/不需要]

- [ ] **步驟 4**: 確認開發方式
  - 主要方法: [MCP/Subagent/直接工具]
  - 預期 Token 消耗: [估計值]
  - 預期節省: [%]

### 建置計畫（如需要）
- [ ] 安裝 MCP server: `[command]`
- [ ] 配置 mcp_config.json
- [ ] 測試 MCP tool
- [ ] 開始實際開發
```

---

## 🔄 實際案例：202511-IC004 重分析（應該怎麼做）

### 錯誤做法（實際執行）

```
1. 直接 Bash: gcloud logging read
2. 直接 Read: 3 個大型檔案
3. 直接 Bash: curl 測試 API 6 次
4. 直接 Edit + Bash build 3 次
→ 總計 ~39,000 tokens
```

### 正確做法（應該執行）

```
【開發前評估 - 5 分鐘】
1. 檢查 MCP: 無 gcloud server → 需要建置
2. 評估 Subagent:
   - 需要探索 3 個檔案找出模型配置 → 使用 Explore
   - 需要測試 5 個模型哪個可用 → 使用 general-purpose

【建置 MCP - 10 分鐘】
3. npm install -g @modelcontextprotocol/server-gcloud
4. 配置 ~/.claude/mcp_config.json
5. 測試 mcp__gcloud.logging_read

【實際開發 - 20 分鐘】
6. mcp__gcloud.logging_read(severity=ERROR, limit=5)  # 300 tokens
7. Task(Explore, "找出 analysis-service 的模型初始化")  # 800 tokens
8. Task(general, "測試可用的 Gemini 模型")  # 500 tokens
9. Edit: 修改 base.py  # 2000 tokens
10. mcp__gcloud.build_submit(...)  # 200 tokens
11. mcp__gcloud.run_deploy(...)  # 150 tokens

→ 總計 ~5,150 tokens（節省 87%）
→ 總時間：35 分鐘（前置 15 分鐘 + 開發 20 分鐘）
→ 長期效益：gcloud MCP server 可重複使用，之後任務節省更多
```

---

## 🎯 關鍵原則

1. **前置投資值得**
   - 花 15 分鐘建置 MCP → 節省 85% tokens
   - 每個任務節省 30,000+ tokens
   - MCP server 可重複使用（一次建置，永久受益）

2. **優先順序明確**
   - MCP > Subagent > 直接工具
   - 不是「能不能用」，是「應該用哪個」

3. **強制檢查**
   - 任何任務開始前必須先執行評估
   - 不允許直接跳到寫程式碼
   - 養成習慣後速度會更快

4. **持續優化**
   - 每次任務後回顧：是否選對方法？
   - 更新 MCP server 清單
   - 分享新建置的 tools

---

## 📚 延伸資源

- [MCP 官方文件](https://modelcontextprotocol.io/)
- [Anthropic MCP 工程案例](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [Awesome MCP Servers](https://github.com/modelcontextprotocol/servers)
- 專案內建 tools: `/tools/`
- Token 優化指引: `/TOKEN_OPTIMIZATION_GUIDE.md`

---

### 2️⃣ 檢查當前狀態 (Check Current Status)

- **Current Phase**: Phase 0 - POC Validation (Ready to Execute)
- **Last Session**: 2025-01-29 (Planning & Specification completed)
- **Next Steps**: Execute 6 POC tests (3-4 days with 3-person team)

### 3️⃣ 閱讀上下文檔案 (Read Context Files)

**Must Read** (in order):

1. `DEVELOPMENT_GUIDELINES.md` ⚠️ **MANDATORY** - Recording rules (READ FIRST!)
2. `QUICK_START_FOR_AI.md` → **本檔案內的「開發前置檢查清單」段落** - Token 優化開發流程（任務開始前必讀）
3. `docs/ai-collaboration-playbook.md` - 標準開發流程與交接規範
4. `DEVELOPMENT_LOG.md` - Full session history, decisions, and context
5. `memory/constitution.md` - System principles (cost, performance, Chinese optimization)
6. `docs/credential-management.md` - Secret/Token 存取方式（避免重複索取）
7. `specs/001-sales-ai-automation/spec.md` - 8 User Stories, 22 features, success criteria

**Optional** (if implementing):

8. `TOKEN_OPTIMIZATION_GUIDE.md` ⭐ **NEW** - MCP/Subagent 使用範例與成本分析
9. `specs/001-sales-ai-automation/plan.md` - Technical architecture, cost breakdown
10. `specs/001-sales-ai-automation/research.md` - 6 POC test plans

### 4️⃣ 理解關鍵決策 (Understand Key Decisions)

All critical decisions are FINAL ✅ (do not re-discuss):

| Topic | Decision | Documented In |
|-------|----------|--------------|
| Architecture | 6-agent multi-agent, Firestore primary, Slack-first | plan.md |
| Product Catalog | iCHEF website (22 features, 6 categories) | spec.md, DEVELOPMENT_LOG.md |
| Questionnaire | Prompt-based (not Firestore templates) | plan.md, research.md |
| Disaster Recovery | Wait for recovery (no multi-region) | plan.md |
| Cost Budget | <$45/month (actual: $46.74, acceptable) | plan.md |

---

## 📋 Current State Summary

### What's Done ✅

- [x] Complete feature specification (spec.md)
- [x] Technical implementation plan (plan.md)
- [x] POC validation plan with 6 detailed tests (research.md)
- [x] Test script structure and 3 example scripts
- [x] All user decisions confirmed and documented

### What's Next 🎯

**Immediate**: Execute Phase 0 POC validations

**6 POCs to validate** (3-4 days, 3-person team):

1. Faster-Whisper + Speaker Diarization (<5 min, >80% accuracy)
2. Multi-Agent Parallel Orchestration (<40s, <5% errors)
3. Gemini Structured Output Quality (>95% compliance)
4. Slack Block Kit Interactivity (<3s response)
5. Firestore Query Performance (<$5/month)
6. Questionnaire Extraction Accuracy (>75% accuracy)

---

## 🗂️ File Structure (What to Look At)

```text
sales-ai-automation-V2/
├── DEVELOPMENT_LOG.md           ⭐ FULL SESSION HISTORY - READ FIRST
├── QUICK_START_FOR_AI.md        ⭐ THIS FILE
├── README.md                    📘 Project overview
├── memory/
│   └── constitution.md          📜 Core principles (cost, performance, quality)
├── specs/001-sales-ai-automation/
│   ├── spec.md                  📋 8 User Stories, 22 features, success criteria
│   ├── plan.md                  🏗️ Architecture, microservices, cost breakdown
│   ├── research.md              🧪 6 POC test plans (NEXT TO EXECUTE)
│   └── poc-tests/
│       ├── README.md            📖 POC execution guide
│       ├── poc1_whisper/
│       │   └── test_whisper.py  🐍 Whisper performance test
│       ├── poc2_multi_agent/
│       │   └── test_parallel.py 🐍 Multi-agent orchestration test
│       └── poc6_questionnaire/
│           └── agent5_prompts/v1.md  💬 Questionnaire analyzer prompt
```text

---

## 💡 Common User Requests & How to Handle

### "Continue where we left off"

→ Read `DEVELOPMENT_LOG.md` Session 1 to understand full context
→ Current task: Prepare for POC execution (or execute if ready)

### "Can you explain the architecture?"

→ Read `specs/001-sales-ai-automation/plan.md`
→ Key: 4 Cloud Run services, 6 agents (1-5 parallel, 6 synthesis), Firestore primary

### "What are the 22 features for Agent 5?"

→ See `DEVELOPMENT_LOG.md` "22 iCHEF Features" section
→ Also in `spec.md` lines 943-976

### "Why did we choose X over Y?"

→ Check `DEVELOPMENT_LOG.md` "Key Discussions & Decisions"
→ All decisions have documented rationale

### "What's the budget/cost?"

→ $46.74/month for 250 files (see `plan.md` cost breakdown)
→ Slightly over $45 target but acceptable

### "How do I run the POC tests?"

→ Read `specs/001-sales-ai-automation/research.md`
→ Test scripts in `specs/001-sales-ai-automation/poc-tests/`
→ Agent 6/7 regression：`make test-agent67`（使用內建 mock fixtures，可離線執行；需要先 `pip install pytest`）

### "How do I set up MCP infrastructure?" ⭐ **NEW**

→ 執行：`./scripts/setup_mcp_infrastructure.sh`
→ 閱讀：本檔案「開發前置檢查清單」段落
→ 參考：`TOKEN_OPTIMIZATION_GUIDE.md`

---

## ⚠️ Important Notes

### DO NOT Re-Discuss These (Already Decided ✅)

- Multi-agent architecture (6 agents) - User confirmed
- Firestore as primary database - User confirmed
- Slack-first interface - User confirmed
- 22 iCHEF features for questionnaire - User confirmed
- Prompt-based questionnaire (not Firestore templates) - User confirmed

### DO Ask User About

- POC execution readiness (team availability, test data, API keys)
- New features or changes not in existing specs
- Clarification on ambiguous requirements (rare, most things are clear)

### Respect the Constitution

`memory/constitution.md` defines immutable principles:

- Cost optimization first (<$45/month target)
- Self-hosted Faster-Whisper (not OpenAI API)
- Event-driven architecture (not polling)
- Chinese language optimization

### Token Optimization First ⭐ **NEW**

Before starting **any** development task, complete this **5-minute assessment**:

#### Step 1: 檢查現有 MCP Servers

```bash
# 執行此指令檢查已配置的 MCP servers
cat ~/.claude/mcp_config.json | jq '.mcpServers | keys'

# 如果檔案不存在，建立空白配置
mkdir -p ~/.claude && echo '{"mcpServers":{}}' > ~/.claude/mcp_config.json
```

#### Step 2: 評估任務需求（回答以下問題）

```
┌──────────────────────────────────────────────────────────┐
│ 1. 這個任務需要呼叫哪些外部服務/API？                      │
│    □ Google Cloud (GCS, Firestore, Cloud Run, Logging...)│
│    □ Slack API                                            │
│    □ Gemini/Vertex AI API                                 │
│    □ 其他：_______________                                │
│                                                           │
│ 2. 這個任務需要讀取/搜尋多少檔案？                        │
│    □ 1-3 個已知檔案 → 直接工具                           │
│    □ 3-10 個檔案或不確定位置 → Subagent (Explore)         │
│    □ 10+ 個檔案或全專案搜尋 → Subagent (general)          │
│                                                           │
│ 3. 這個任務需要多輪試錯嗎？                               │
│    □ 否（需求明確） → 直接工具                            │
│    □ 是（測試參數、模型、配置） → Subagent               │
│                                                           │
│ 4. 這個任務會重複執行嗎？                                 │
│    □ 一次性任務 → 直接工具                                │
│    □ 可能重複（批次操作、定期查詢） → MCP Server          │
└──────────────────────────────────────────────────────────┘
```

#### Step 3: 決策矩陣（選擇開發方式）

| 任務類型 | 呼叫次數 | 資料量 | 試錯 | 推薦方法 | Token 節省 | 建置時間 |
|---------|---------|--------|------|---------|-----------|---------|
| GCP API 呼叫 | 3+ | 大 | 否 | **MCP** | 85% | 10 分鐘 |
| Firestore 批次查詢 | 5+ | 大 | 否 | **MCP** | 90% | 10 分鐘 |
| Slack 通知 | 任意 | 小 | 否 | **MCP** | 95% | 5 分鐘 |
| 程式碼探索 | 1 | 大 | 是 | **Subagent** | 70% | 0 分鐘 |
| 參數測試 | 1 | 中 | 是 | **Subagent** | 60% | 0 分鐘 |
| 錯誤診斷 | 1 | 大 | 是 | **Subagent** | 75% | 0 分鐘 |
| 單檔案修改 | 1 | 小 | 否 | **直接工具** | 0% | 0 分鐘 |
| 簡單命令 | 1 | 小 | 否 | **直接工具** | 0% | 0 分鐘 |

#### Step 4: 執行方案

**如果需要建置 MCP Server**：

```bash
# 快速建置常用 MCP servers（10-15 分鐘）
cd /path/to/sales-ai-automation-V2
./scripts/setup_mcp_infrastructure.sh

# 重啟 Claude Code 以載入新配置
```

**如果使用 Subagent**：

```python
# 範例 1: 程式碼探索
Task(
    subagent_type="Explore",
    description="探索 Agent 架構",
    prompt="找出專案中所有 Agent 類別，回傳：檔案路徑、類別名稱、主要功能（一句話）",
    model="haiku"  # 使用便宜模型降低成本
)

# 範例 2: 多輪試錯
Task(
    subagent_type="general-purpose",
    description="測試可用模型",
    prompt="測試以下 Gemini 模型哪個可用：gemini-pro, gemini-2.5-flash, gemini-flash-latest。只回傳第一個成功的模型名稱。",
    model="haiku"
)
```

**如果使用直接工具**：

```python
# 適用於：已知檔案、單次操作、不重複
Read("/path/to/known/file.py")
Edit(file_path="/path/to/file.py", old_string="...", new_string="...")
Bash("gcloud run services list")
```

#### Step 5: 成本效益對比

**實際案例：202511-IC004 重分析**

| 方法 | Token 消耗 | 時間 | 說明 |
|-----|-----------|------|------|
| ❌ 直接工具（實際） | ~39,000 tokens | 60 分鐘 | 15次 gcloud, 3次重複讀檔, 6次試錯 |
| ✅ MCP + Subagent（應該） | ~5,150 tokens | 35 分鐘 | 10分鐘建置 MCP + 25分鐘開發 |
| **節省** | **87%** | **42%** | 長期效益：MCP 可重複使用 |

---

### 完整開發流程示範

```markdown
## 任務：修復 analysis-service 503 錯誤

### 前置評估（5 分鐘）

#### 1. MCP Server 檢查
- [x] 已配置: 無
- [x] 需要建置: gcloud（用於日誌查詢和部署）

#### 2. 外部服務呼叫
- [x] Google Cloud API: 需要 → 預計 5-8 次
  - Cloud Logging: 查詢錯誤
  - Cloud Build: 觸發建置
  - Cloud Run: 部署服務

#### 3. 程式碼探索
- [x] 需要讀取: 3-10 個檔案（不確定錯誤位置）
- [x] 使用 Subagent (Explore)

#### 4. 試錯需求
- [x] 需要測試多個模型參數: 是
- [x] 使用 Subagent (general-purpose)

#### 5. 最終方案
- **主要方法**: MCP + Subagent
- **預期 Token**: ~5,000 tokens
- **預期節省**: 87%
- **前置時間**: 10 分鐘建置 MCP

---

### 執行計畫

```bash
# 1. 建置 MCP（10 分鐘）
./scripts/setup_mcp_infrastructure.sh

# 2. 重啟 Claude Code

# 3. 開始開發（25 分鐘）
```

### 開發步驟

1. ✅ 使用 `mcp__gcloud.logging_read(severity=ERROR, limit=5)` 查詢錯誤（300 tokens）
2. ✅ 使用 `Task(Explore, "找出模型初始化流程")` 探索檔案（800 tokens）
3. ✅ 使用 `Task(general, "測試可用模型")` 試錯（500 tokens）
4. ✅ 使用 `Edit` 修改程式碼（2000 tokens）
5. ✅ 使用 `mcp__gcloud.build_submit()` 建置（200 tokens）
6. ✅ 使用 `mcp__gcloud.run_deploy()` 部署（150 tokens）

**總計**: ~5,150 tokens（vs. 直接工具 ~39,000 tokens）
```

---

## 🔧 If User Wants to Execute POCs

### Prerequisites Checklist

Ask user to confirm:

- [ ] GCP project created with billing enabled
- [ ] Slack workspace with test app
- [ ] Gemini API key obtained
- [ ] Test audio files prepared (10 files, various lengths)
- [ ] Test transcripts prepared (30 files, various scenarios)
- [ ] 3-person team available for parallel execution

### Execution Steps

1. Review `specs/001-sales-ai-automation/research.md` for detailed procedures
2. Set up test environment (GCP, Slack, API keys)
3. Run POCs in parallel (Week 1 + Week 2 schedule in research.md)
4. Document results in `specs/001-sales-ai-automation/poc-tests/results/`
5. Make Go/No-Go decisions
6. Update `plan.md` with validated configurations
7. Add new session entry to `DEVELOPMENT_LOG.md`

---

## 📝 When Completing a Task

### Update DEVELOPMENT_LOG.md

1. Add new session entry using template at end of file
2. Document:
   - What was done
   - Key decisions made
   - Files created/modified
   - Technical highlights
   - Open questions
   - Next steps

### Format for Session Entry

```markdown
### Session 2: 2025-MM-DD (Title)

**Duration**: X hours
**AI Model**: [Your model name]
**User**: Stephen

#### Objectives Completed ✅
- [x] Task 1
- [x] Task 2

#### Files Created/Modified
- `path/to/file` (description)

#### Key Decisions
1. **Topic**: Decision and rationale

#### Next Session Preparation
- Action items for next AI assistant
```text

---

## 🎯 Quick Decision Tree

**User says**: "Continue development"
→ Read DEVELOPMENT_LOG.md → Current phase is POC Validation → Ask if ready to execute

**User says**: "Can you implement feature X?"
→ Check if feature is in spec.md → If yes, check if POCs are done → If no, remind that POC validation comes first

**User says**: "Why did we choose X?"
→ Check DEVELOPMENT_LOG.md "Key Discussions & Decisions" → Explain rationale

**User says**: "Change decision X to Y"
→ Explain current decision and rationale → If user insists, update spec.md/plan.md → Document in DEVELOPMENT_LOG.md

**User says**: "Start POC testing"
→ Check prerequisites → Guide through research.md procedures → Document results

---

## 📞 Emergency References

**If confused about project goals**:
→ Read `README.md` or `spec.md` "Summary" section

**If confused about technical decisions**:
→ Read `plan.md` "User Decisions" section

**If confused about what to do next**:
→ Read `DEVELOPMENT_LOG.md` "Next Session Preparation"

**If user mentions something unfamiliar**:
→ Search DEVELOPMENT_LOG.md for the term
→ Ask user to clarify (may be new information)

---

## ✅ Self-Check Before Starting

Before responding to user, verify:

- [ ] I have read DEVELOPMENT_GUIDELINES.md ⚠️ **MANDATORY**
- [ ] I have read DEVELOPMENT_LOG.md
- [ ] I understand current phase (Phase 0 - POC Validation)
- [ ] I know what was done in last session
- [ ] I know what the next steps are
- [ ] I will not re-discuss finalized decisions
- [ ] **I will record this session before ending** ⚠️ **MANDATORY**

---

#### Welcome to the project! You're now ready to continue development. 🚀

*Last Updated: 2025-01-29 by Claude Sonnet 4.5*
