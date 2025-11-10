# Token 優化開發指引

> **目標**：透過 MCP、Subagent、直接工具的策略性使用，降低 70-85% 的 Token 消耗

---

## 📊 Token 消耗基準

### 當前模式（100% 直接工具）

| 操作類型 | Token 消耗 | 範例 |
|---------|-----------|------|
| 讀取大型檔案 | ~2000 tokens/次 | Read orchestrator.py (254行) |
| 手動 API 測試 | ~5000 tokens/輪 | 15次 gcloud + curl 測試 |
| 試錯式修改 | ~3000 tokens/次 | 6次 model name 調整 |
| 重複操作 | ~1000 tokens/次 | 重複讀取 base.py 3次 |

**總消耗估計**：~150,000 tokens（一個完整任務）

### 優化後模式（MCP + Subagent + 直接工具）

| 操作類型 | Token 消耗 | 節省比例 | 方法 |
|---------|-----------|---------|------|
| 讀取大型檔案 | ~600 tokens/次 | **70%** | Subagent 摘要回傳 |
| 批次 API 測試 | ~750 tokens/輪 | **85%** | MCP Server 直接執行 |
| 隔離試錯 | ~1200 tokens/次 | **60%** | Subagent 獨立 context |
| 快取重複查詢 | ~50 tokens/次 | **95%** | MCP tool 結果快取 |

**總消耗估計**：~22,500 tokens（一個完整任務）

---

## 🎯 決策矩陣

### 1️⃣ 直接工具（Read/Edit/Bash）

**使用條件**：
- ✅ 已知確切檔案路徑
- ✅ 單次操作不超過 3 步
- ✅ 不需要重複執行
- ✅ 檔案小於 100 行

**範例**：
```bash
# ✅ 適合：讀取小型 config 檔案
Read(/path/to/config.yaml)

# ✅ 適合：修改已知位置
Edit(file_path="/app/main.py", old_string="port=8080", new_string="port=9000")

# ❌ 不適合：搜尋未知錯誤
Bash("gcloud logging read") # 會產生大量 log，消耗過多 tokens
```

**Token 消耗**：基準值（1000-2000 tokens/操作）

---

### 2️⃣ MCP Server（透過 MCP 協議呼叫外部服務）

**使用條件**：
- ✅ 需要重複呼叫同一 API
- ✅ 批次操作（列表、查詢、刪除）
- ✅ 有現成 MCP server 可用
- ✅ 結果可快取

**優先使用場景**：

#### A. Google Cloud 操作
```python
# ❌ 直接呼叫（高 token 消耗）
Bash("gcloud logging read 'resource.type=cloud_run_revision' --limit=50")
# → 回傳 2000 行 log，消耗 ~8000 tokens

# ✅ 使用 MCP Server（低消耗）
mcp__gcloud_logging.read(
    filter='resource.type=cloud_run_revision AND severity>=ERROR',
    limit=10,
    format='summary'  # 只回傳摘要
)
# → 回傳 10 條錯誤摘要，消耗 ~500 tokens
```

#### B. Firestore 批次查詢
```python
# ❌ 直接呼叫（需要完整 SDK context）
Bash("python3 -c 'from google.cloud import firestore; db=firestore.Client(); ...'")
# → Python script + output，消耗 ~3000 tokens

# ✅ 使用 MCP Server
mcp__firestore.query(
    collection='cases',
    where=[('status', '==', 'failed')],
    limit=5,
    fields=['caseId', 'createdAt', 'error']  # 只取需要的欄位
)
# → 結構化 JSON，消耗 ~300 tokens
```

#### C. Slack 通知
```python
# ❌ 直接呼叫（需要完整 curl 命令 + response）
Bash('curl -X POST https://slack.com/api/chat.postMessage ...')
# → 完整 API response，消耗 ~1000 tokens

# ✅ 使用 MCP Server
mcp__slack.send_message(
    channel='C12345',
    text='分析完成',
    thread_ts='1234567890.123456'
)
# → 只回傳 success/failure，消耗 ~50 tokens
```

**Token 節省**：85%（批次操作）、95%（快取查詢）

**設定方式**：
1. 安裝 MCP server：`npm install -g @modelcontextprotocol/server-gcloud`
2. 配置 `~/.claude/mcp_config.json`：
```json
{
  "mcpServers": {
    "gcloud": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-gcloud"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/service-account.json"
      }
    },
    "firestore": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-firestore"],
      "env": {
        "GCP_PROJECT": "sales-ai-automation-v2"
      }
    },
    "slack": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-slack"],
      "env": {
        "SLACK_BOT_TOKEN": "${SLACK_BOT_TOKEN}"
      }
    }
  }
}
```

---

### 3️⃣ Subagent（Task tool）

**使用條件**：
- ✅ 需要探索大型檔案或目錄
- ✅ 多輪試錯（測試不同參數）
- ✅ 需要隔離 context（避免污染主對話）
- ✅ 需要搜尋不確定的內容

**優先使用場景**：

#### A. 程式碼探索
```python
# ❌ 直接搜尋（佔用主對話 context）
Grep(pattern="class.*Agent", path="analysis-service/src")
# → 回傳 20 個檔案的 class 定義，消耗 ~5000 tokens
Read("analysis-service/src/agents/agent1.py")
Read("analysis-service/src/agents/agent2.py")
# → 每次讀取 ~2000 tokens，累積在主對話中

# ✅ 使用 Subagent
Task(
    subagent_type="Explore",
    prompt="找出 analysis-service 中所有 Agent 類別的實作，回傳每個 Agent 的：
    1. 類別名稱
    2. 使用的 model name
    3. 主要功能（一句話）",
    description="探索 Agent 架構",
    model="haiku"  # 使用便宜模型
)
# → 只回傳摘要，消耗 ~800 tokens（Subagent 的 context 不累積到主對話）
```

#### B. 錯誤診斷（多輪試錯）
```python
# ❌ 直接診斷（每次嘗試都佔用主對話）
Bash("gcloud logging read 'severity>=ERROR' --limit=100")
# → 100 條 log，消耗 ~4000 tokens
Read("analysis-service/src/main.py")
# → +2000 tokens
Read("analysis-service/src/orchestrator.py")
# → +2500 tokens
# 總計：8500 tokens 累積在主對話

# ✅ 使用 Subagent
Task(
    subagent_type="general-purpose",
    prompt="診斷 analysis-service 為何出現 503 錯誤：
    1. 讀取 Cloud Run logs 找出錯誤訊息
    2. 檢查相關程式碼
    3. 回傳：錯誤原因 + 修復建議（不要貼完整程式碼）",
    description="診斷 503 錯誤",
    model="haiku"
)
# → 只回傳診斷結果，消耗 ~1000 tokens（Subagent 內部的探索不佔主對話）
```

#### C. 模型測試
```python
# ❌ 直接測試（每次失敗都累積 context）
Bash("python3 test_model.py --model=gemini-pro")  # 失敗
# → +1000 tokens
Bash("python3 test_model.py --model=gemini-1.5-flash")  # 失敗
# → +1000 tokens
Bash("python3 test_model.py --model=gemini-flash-latest")  # 成功
# → +1000 tokens
# 總計：3000 tokens

# ✅ 使用 Subagent
Task(
    subagent_type="general-purpose",
    prompt="測試以下模型哪個可用：
    - gemini-pro
    - gemini-1.5-flash
    - gemini-flash-latest
    - gemini-2.5-flash

    每個模型執行 test_model.py，回傳第一個成功的模型名稱即可",
    description="測試可用模型",
    model="haiku"
)
# → 只回傳成功的模型名稱，消耗 ~400 tokens
```

**Token 節省**：70%（程式碼探索）、60%（試錯隔離）

**使用技巧**：
1. 明確指定回傳格式（避免 Subagent 回傳過多內容）
2. 使用 `model="haiku"` 參數來降低 Subagent 內部消耗
3. 要求 Subagent 只回傳摘要，不要貼完整程式碼

---

## 📝 實戰案例：202511-IC004 重分析

### 原始方法（直接工具）

```
1. Bash: gcloud logging read（查看錯誤）
   → 回傳 50 條 log，消耗 2000 tokens

2. Read: analysis-service/src/main.py
   → 讀取 478 行，消耗 2500 tokens

3. Read: analysis-service/src/orchestrator.py
   → 讀取 254 行，消耗 2000 tokens

4. Read: analysis-service/src/agents/base.py
   → 讀取 254 行，消耗 2000 tokens

5. Bash: curl https://generativelanguage.googleapis.com/v1beta/models
   → 測試 API，消耗 1000 tokens

6. Read: analysis-service/src/agents/base.py（重複讀取）
   → 消耗 2000 tokens

7-12. Edit + Bash 測試（試錯 6 次）
   → 每次消耗 ~3000 tokens = 18000 tokens

13-15. Bash: gcloud builds submit + 查看 log（3 次）
   → 每次消耗 ~2000 tokens = 6000 tokens

16. Bash: trigger_analysis.py
   → 消耗 1500 tokens

總計：~39,000 tokens（主對話）
```

### 優化方法（MCP + Subagent + 直接工具）

```
1. MCP: mcp__gcloud_logging.read(severity=ERROR, limit=5)
   → 只回傳 5 條關鍵錯誤，消耗 300 tokens

2. Subagent (Explore): "分析 analysis-service 的模型初始化流程"
   → Subagent 內部讀取 3 個檔案，只回傳摘要，消耗 800 tokens

3. Subagent (general-purpose): "測試哪些 Gemini 模型可用"
   → Subagent 內部執行 5 次 curl，只回傳成功的模型，消耗 500 tokens

4. Edit: analysis-service/src/agents/base.py（直接修改）
   → 消耗 2000 tokens

5. MCP: mcp__gcloud_build.submit(dockerfile_path=..., tag=...)
   → 只回傳 build ID + status，消耗 200 tokens

6. MCP: mcp__gcloud_run.deploy(service=..., image=...)
   → 只回傳 deployment URL，消耗 150 tokens

7. MCP: mcp__firestore.query(collection='cases', where=[...])
   → 只回傳 case 資料，消耗 200 tokens

8. Bash: python3 trigger_analysis.py（簡單執行）
   → 消耗 1000 tokens

總計：~5,150 tokens（主對話）+ ~10,000 tokens（Subagent 內部，不累積）
     = 實際主對話消耗 5,150 tokens
```

**節省比例**：87%（39,000 → 5,150 tokens）

---

## 🚀 立即實施步驟

### Step 1: 安裝必要 MCP Servers

```bash
# Google Cloud MCP Server
npm install -g @modelcontextprotocol/server-gcloud

# Firestore MCP Server（如果有）
npm install -g @modelcontextprotocol/server-firestore

# Slack MCP Server
npm install -g @modelcontextprotocol/server-slack
```

### Step 2: 配置 MCP Config

編輯 `~/.claude/mcp_config.json`：

```json
{
  "mcpServers": {
    "gcloud": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-gcloud"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "/Users/stephen/.config/gcloud/application_default_credentials.json",
        "GCP_PROJECT": "sales-ai-automation-v2"
      }
    },
    "slack": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-slack"],
      "env": {
        "SLACK_BOT_TOKEN": "${SLACK_BOT_TOKEN}"
      }
    }
  }
}
```

### Step 3: 建立開發習慣 Checklist

在開始每個任務前，問自己：

```
┌─────────────────────────────────────────┐
│ Token 優化 Checklist                    │
├─────────────────────────────────────────┤
│ □ 是否需要查詢 GCP 資源？               │
│   → YES: 使用 mcp__gcloud               │
│                                         │
│ □ 是否需要讀取大型檔案？                │
│   → YES: 使用 Subagent (Explore)        │
│                                         │
│ □ 是否需要多輪測試？                    │
│   → YES: 使用 Subagent (general)        │
│                                         │
│ □ 是否需要批次操作 Firestore？          │
│   → YES: 使用 mcp__firestore            │
│                                         │
│ □ 是否是單次簡單修改？                  │
│   → YES: 直接使用 Read/Edit/Bash        │
└─────────────────────────────────────────┘
```

---

## 📈 預期效果

| 項目 | 優化前 | 優化後 | 改善 |
|-----|--------|--------|------|
| 平均任務 Token 消耗 | ~40,000 | ~6,000 | **85%↓** |
| 重複查詢消耗 | ~1,000/次 | ~50/次 | **95%↓** |
| 程式碼探索消耗 | ~8,000 | ~1,200 | **85%↓** |
| 試錯過程消耗 | ~15,000 | ~2,000 | **87%↓** |
| 每月成本（假設 30 任務） | $120 | $18 | **$102↓** |

---

## ⚠️ 注意事項

1. **MCP Server 可用性**
   - 並非所有 GCP API 都有對應 MCP server
   - 如果沒有現成 MCP server，可以考慮自己實作或使用直接工具

2. **Subagent 適用範圍**
   - Subagent 適合「探索」和「試錯」
   - 不適合「精確修改」（Edit 仍需直接工具）

3. **Context 管理**
   - Subagent 的 context 不會累積到主對話
   - 但 Subagent 自己的執行也會消耗 tokens（只是不佔主對話）
   - 因此要控制 Subagent 的回傳內容長度

4. **成本計算**
   - 主對話 tokens（累積 context）> Subagent tokens（獨立 context）
   - 優先減少主對話的 token 累積

---

## 📚 延伸閱讀

- [MCP 官方文件](https://modelcontextprotocol.io/)
- [Claude Code Subagent 使用指南](https://docs.anthropic.com/claude-code)
- [Token 優化最佳實踐](https://docs.anthropic.com/best-practices/token-optimization)
