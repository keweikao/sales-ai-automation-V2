# Agent 9: MCP Tool Integration Layer

**文檔目的**：設計 Agent 9 作為 MCP 工具整合層，為其他 agents 提供高效、安全的工具調用能力。

**Source**: Derived from Anthropic official doc (2025) - <https://www.anthropic.com/engineering/code-execution-with-mcp>

**最後更新**：2025-11-06

---

## 🎯 設計目標

### 核心價值

✅ **Token 優化**：透過 progressive disclosure 和 context filtering，實現 95%+ token 節省
✅ **安全隔離**：沙箱執行工具代碼，保護系統穩定性和資料安全
✅ **按需加載**：工具定義僅在需要時加載，避免 context 污染
✅ **PII 保護**：自動偵測並匿名化敏感資料（email、phone、身份證字號）

### Agent 9 在系統中的定位

Agent 9 **不直接面對用戶**，而是作為**底層基礎設施**，為其他 agents 提供工具調用服務：

```
用戶 (Slack)
    ↓
Agent 8 (對話式 AI) ← 需要查詢 Firestore
    ↓
Agent 9 (MCP Integration) ← 按需加載 firestore_query 工具
    ↓
Firestore / GCS / BigQuery
```

**與現有 agents 的關係**：

- **Agent 1-7**（分析型 agents）：可能不需要 Agent 9（直接查詢 Firestore）
- **Agent 8**（對話式 AI）：**主要受益者** - 需要動態工具調用（查詢資料、發送通知、執行計算）
- **未來 agents**：任何需要外部工具的 agent 都可透過 Agent 9

---

## 🏗️ 系統架構

### 組件設計

```
┌─────────────────────────────────────────────────────┐
│              Agent 9: MCP Integration               │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1. Tool Registry (工具註冊表)                      │
│     - 文件樹結構管理工具定義                         │
│     - tools/firestore/query.py                      │
│     - tools/gcs/upload.py                           │
│     - tools/slack/send_message.py                   │
│                                                     │
│  2. Discovery Engine (探索引擎)                     │
│     - 關鍵字/類別匹配                                │
│     - 模糊搜尋 (fuzzy match)                        │
│     - 工具摘要生成（<50 tokens per tool）          │
│                                                     │
│  3. Execution Sandbox (執行沙箱)                    │
│     - Python multiprocessing 隔離                   │
│     - 超時控制 (30s 預設)                           │
│     - 記憶體限制 (512MB 預設)                       │
│     - 檔案系統/網路存取限制                         │
│                                                     │
│  4. Context Optimizer (上下文優化器)                │
│     - 資料過濾 (在執行環境完成)                     │
│     - PII 自動匿名化                                │
│     - 結果摘要生成                                  │
│                                                     │
│  5. Cache Manager (快取管理器)                      │
│     - 工具定義快取 (session 生命週期)              │
│     - PII token 映射快取                            │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 📋 功能設計

### 1. Progressive Tool Discovery (漸進式工具探索)

#### 設計原則 (derived from Anthropic official doc 2025)

- 工具定義**僅在需要時加載**，而非初始化時全部加載
- Agent 透過探索文件樹發現可用工具
- 支援三種詳細程度：
  1. **名稱列表** (10 tokens/tool)：`["firestore_query", "firestore_list"]`
  2. **含描述** (30 tokens/tool)：`{"name": "firestore_query", "desc": "Query Firestore by filters"}`
  3. **完整 schema** (200+ tokens/tool)：完整參數定義、範例

#### 使用情境

**情境 1：Agent 8 需要查詢案件資料**

```python
# Agent 8 內部邏輯
user_query = "王小明這週的案件健康度如何？"

# Step 1: Agent 8 判斷需要工具
需要工具類型：資料查詢

# Step 2: 透過 Agent 9 探索工具
Agent9.discover_tools(category="firestore", detail_level="names")
→ 返回：["firestore_query", "firestore_aggregate", "firestore_list_collections"]

# Step 3: Agent 8 選擇工具
selected_tool = "firestore_query"

# Step 4: 加載完整定義
Agent9.load_tool_definition("firestore_query")
→ 返回：完整 schema（參數、範例、限制）

# Step 5: 執行工具
result = Agent9.execute_tool(
    tool_name="firestore_query",
    params={
        "collection": "cases",
        "filters": [
            {"field": "rep_name", "op": "==", "value": "王小明"},
            {"field": "created_date", "op": ">=", "value": "2025-11-01"}
        ],
        "limit": 100
    }
)
# 原始結果：100 筆案件，~50k tokens
# Agent 9 自動過濾：僅返回 case_id, health_score, customer_name
# 最終結果：~2k tokens (節省 96%)
```

**Token 優化效果**：

- **傳統方法**（預載所有工具）：50 個工具 × 200 tokens = 10,000 tokens
- **Progressive Disclosure**：僅載入 1 個工具 = 200 tokens
- **節省**：98% (10k → 200 tokens)

---

### 2. In-Environment Data Filtering (環境內資料過濾)

#### 設計原則 (derived from Anthropic official doc 2025)

- 查詢結果在**執行環境內過濾**，而非傳給 model 後過濾
- 實現 Anthropic 案例：150k tokens → 2k tokens (98.7% 節省)
- 支援欄位篩選、條件過濾、聚合計算

#### 實作範例

```python
# tools/firestore/query.py

def firestore_query(collection: str, filters: list, context_mode: str = "minimal"):
    """
    Query Firestore with automatic context optimization.

    Args:
        collection: Collection name
        filters: List of filter conditions
        context_mode: "full" | "minimal" | "aggregate"
                     - full: 返回所有欄位 (適用於少量資料)
                     - minimal: 僅返回關鍵欄位 (預設)
                     - aggregate: 返回聚合統計

    Returns:
        Filtered, PII-protected results

    # derived from Anthropic official doc (2025)
    # Context optimization: 在執行環境完成過濾，避免原始資料進入 model context
    """

    # Step 1: 執行查詢 (在執行環境)
    raw_results = firestore_client.collection(collection).where(...).get()
    # 假設返回 5000 筆，每筆 50 欄位 → ~500k tokens

    # Step 2: 欄位篩選 (在執行環境)
    if context_mode == "minimal":
        filtered_results = [
            {
                "case_id": doc["case_id"],
                "health_score": doc["health_score"],
                "customer_name": doc["customer_name"],
                "rep_name": doc["rep_name"]
            }
            for doc in raw_results
        ]
        # 5000 筆 × 4 欄位 → ~20k tokens

    # Step 3: PII 匿名化 (在執行環境)
    pii_protected_results = anonymize_pii(filtered_results)
    # customer_name "張三" → [NAME_1]
    # phone "0912-345-678" → [PHONE_1]

    # Step 4: 額外過濾（如有需要）
    if len(pii_protected_results) > 50:
        # 僅返回前 50 筆最相關的
        pii_protected_results = pii_protected_results[:50]
        # ~2k tokens

    # Step 5: 返回給 model
    return {
        "results": pii_protected_results,
        "total_count": len(raw_results),
        "returned_count": len(pii_protected_results),
        "truncated": len(raw_results) > len(pii_protected_results)
    }
```

**Token 優化對比**：

| 階段 | Token 數量 | 說明 |
|------|-----------|------|
| 原始查詢結果 | 500,000 | 5000 筆 × 50 欄位 |
| 欄位篩選後 | 20,000 | 5000 筆 × 4 關鍵欄位 |
| PII 匿名化後 | 18,000 | 名字/電話縮短為 token |
| Top 50 截斷後 | 2,000 | 僅返回最相關 50 筆 |
| **節省比例** | **99.6%** | 500k → 2k |

---

### 3. PII Auto-Detection & Tokenization (PII 自動偵測與匿名化)

#### 設計原則 (derived from Anthropic official doc 2025)

- 敏感資料在進入 model context **之前**轉換為 tokens
- 原始值儲存在 secure session storage，4 小時自動過期
- Model 僅看到 `[EMAIL_1]`, `[PHONE_2]` 等 tokens

#### 支援的 PII 類型

```python
PII_PATTERNS = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone_tw": r"\b09\d{2}-?\d{3}-?\d{3}\b",  # 台灣手機
    "phone_intl": r"\+\d{1,3}-?\d{1,4}-?\d{1,4}-?\d{1,9}\b",
    "id_number_tw": r"\b[A-Z]\d{9}\b",  # 台灣身份證
    "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"
}

def anonymize_pii(data: dict | list) -> dict | list:
    """
    # derived from Anthropic official doc (2025)
    Auto-detect and tokenize PII in data structures.
    """
    session_id = get_current_session_id()
    pii_map = get_or_create_pii_map(session_id)

    for key, value in data.items():
        if isinstance(value, str):
            # 檢測 email
            if re.match(PII_PATTERNS["email"], value):
                token_id = f"[EMAIL_{len(pii_map['email']) + 1}]"
                pii_map["email"][token_id] = value
                data[key] = token_id

            # 檢測手機
            elif re.match(PII_PATTERNS["phone_tw"], value):
                token_id = f"[PHONE_{len(pii_map['phone']) + 1}]"
                pii_map["phone"][token_id] = value
                data[key] = token_id

            # ... 其他 PII 類型

    return data
```

#### 使用範例

```python
# 原始查詢結果
raw_data = {
    "customer_name": "張三",
    "email": "zhang.san@example.com",
    "phone": "0912-345-678",
    "case_id": "202501-IC001"
}

# 經過 anonymize_pii() 處理
anonymized_data = {
    "customer_name": "張三",  # 中文姓名暫不匿名化（可選）
    "email": "[EMAIL_1]",
    "phone": "[PHONE_1]",
    "case_id": "202501-IC001"
}

# PII 映射儲存在 session storage（Model 看不到）
pii_map[session_id] = {
    "email": {"[EMAIL_1]": "zhang.san@example.com"},
    "phone": {"[PHONE_1]": "0912-345-678"}
}
```

---

### 4. Secure Execution Sandbox (安全執行沙箱)

#### 設計原則 (derived from Anthropic official doc 2025)

- 工具代碼在隔離環境執行
- 超時、記憶體、檔案/網路限制
- 錯誤不影響主服務穩定性

#### 實作架構

```python
# src/slack_app/mcp_adapter.py

import multiprocessing
import signal
import psutil

class ToolExecutor:
    """
    # derived from Anthropic official doc (2025)
    Secure sandbox for tool execution with resource limits.
    """

    def execute_tool(self, tool_name: str, params: dict,
                     timeout: int = 30,
                     memory_limit_mb: int = 512) -> dict:
        """
        Execute tool in isolated process with resource limits.
        """
        # 建立隔離 process
        queue = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=self._run_tool,
            args=(tool_name, params, queue)
        )

        # 啟動執行
        process.start()

        # 設定記憶體限制
        p = psutil.Process(process.pid)
        p.rlimit(psutil.RLIMIT_AS, (memory_limit_mb * 1024 * 1024, -1))

        # 等待結果（含超時）
        try:
            result = queue.get(timeout=timeout)
            process.join(timeout=1)
            return result

        except queue.Empty:
            # 超時處理
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()  # 強制終止

            return {
                "status": "error",
                "error": f"Tool execution timeout after {timeout}s",
                "tool": tool_name
            }

        except Exception as e:
            process.terminate()
            return {
                "status": "error",
                "error": str(e),
                "tool": tool_name
            }

    def _run_tool(self, tool_name: str, params: dict, queue: multiprocessing.Queue):
        """
        在隔離 process 中執行工具
        """
        try:
            # 動態載入工具模組
            tool_module = importlib.import_module(f"tools.{tool_name}")
            tool_func = getattr(tool_module, tool_name)

            # 執行工具
            result = tool_func(**params)

            # 返回結果
            queue.put({
                "status": "success",
                "result": result
            })

        except Exception as e:
            queue.put({
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc()
            })
```

#### 安全邊界

| 資源類型 | 限制 | 超過時處理 |
|---------|------|-----------|
| CPU 時間 | 30s (預設) | SIGKILL 終止 process |
| 記憶體 | 512MB (預設) | MemoryError → 返回錯誤 |
| 檔案讀取 | 僅 `/tmp/` 可寫 | PermissionError |
| 網路存取 | 白名單制 (預設阻擋) | ConnectionError |
| 系統呼叫 | 禁止 `os.system()`, `subprocess` | RuntimeError |

---

## 🔗 與 Agent 8 整合

### Agent 8 呼叫 Agent 9 的流程

```python
# src/slack_app/handlers/agent8_handler.py

from mcp_adapter import MCPAdapter

class Agent8Handler:
    def __init__(self):
        self.mcp = MCPAdapter()  # Agent 9 介面

    async def handle_user_query(self, query: str):
        """
        處理用戶查詢（如：王小明這週案件健康度？）
        """

        # Step 1: 判斷是否需要工具
        if self._needs_data_query(query):

            # Step 2: 探索可用工具
            tools = self.mcp.discover_tools(
                category="firestore",
                detail_level="names"
            )
            # → ["firestore_query", "firestore_aggregate"]

            # Step 3: 選擇並載入工具定義
            tool_def = self.mcp.load_tool("firestore_query")

            # Step 4: 構造查詢參數
            params = self._build_query_params(query, tool_def)
            # → {"collection": "cases", "filters": [...], "context_mode": "minimal"}

            # Step 5: 執行工具（經過 Agent 9 優化）
            result = self.mcp.execute_tool("firestore_query", params)
            # 原始 5000 筆 → 自動過濾為 50 筆，PII 匿名化

            # Step 6: 基於結果生成回答
            answer = self._generate_answer(query, result)

            return answer
```

---

## 📊 效能指標

### Token 優化目標

| 情境 | 無 Agent 9 | 有 Agent 9 | 節省比例 |
|------|-----------|-----------|---------|
| 預載 50 個工具 | 10,000 tokens | 200 tokens | 98% |
| 查詢 5000 筆案件 | 500,000 tokens | 2,000 tokens | 99.6% |
| 查詢含 PII 資料 | 50,000 tokens | 3,000 tokens | 94% |

### 執行效能目標

- 工具探索：< 500ms
- 工具載入：< 200ms
- 工具執行：< 30s (含超時)
- 快取命中率：> 90% (同 session 重複呼叫)

---

## 🛡️ 安全與隱私

### 資料保護原則

1. **PII 不進入 Model Context**
   - Email、電話、身份證字號自動匿名化
   - 原始值儲存在 secure session storage
   - 4 小時自動過期

2. **工具代碼審查**
   - 所有工具上線前需 code review
   - 禁止直接執行用戶輸入的代碼
   - 使用白名單限制可呼叫的工具

3. **執行隔離**
   - 工具在獨立 process 執行
   - 記憶體/CPU/檔案/網路限制
   - 錯誤不影響主服務

4. **審計日誌**
   - 記錄所有工具呼叫（工具名、參數、結果狀態）
   - PII 不寫入 log（僅記錄 token）
   - 保留 30 天供審查

---

## 🔄 工具目錄結構

```
tools/
├── firestore/
│   ├── __init__.py
│   ├── query.py           # Firestore 查詢
│   ├── aggregate.py       # 聚合統計
│   └── list_collections.py
├── gcs/
│   ├── __init__.py
│   ├── upload.py          # 上傳檔案
│   └── download.py
├── bigquery/
│   ├── __init__.py
│   └── query.py           # BigQuery SQL
├── slack/
│   ├── __init__.py
│   ├── send_message.py    # 發送 Slack 訊息
│   └── upload_file.py
└── compute/
    ├── __init__.py
    ├── statistics.py      # 統計計算 (pandas)
    └── aggregation.py     # 資料聚合
```

每個工具檔案範例：

```python
# tools/firestore/query.py

"""
Tool: firestore_query
Category: firestore
Version: 1.0.0
Description: Query Firestore with automatic context optimization and PII protection

# derived from Anthropic official doc (2025)
"""

def firestore_query(
    collection: str,
    filters: list[dict],
    order_by: str = None,
    limit: int = 100,
    context_mode: str = "minimal"
) -> dict:
    """
    Query Firestore collection with filters.

    Args:
        collection: Collection name (e.g., "cases")
        filters: List of {"field": str, "op": str, "value": any}
        order_by: Field name for sorting (optional)
        limit: Max results to return
        context_mode: "full" | "minimal" | "aggregate"

    Returns:
        {"results": [...], "total_count": int, "truncated": bool}

    Example:
        result = firestore_query(
            collection="cases",
            filters=[
                {"field": "rep_name", "op": "==", "value": "王小明"},
                {"field": "health_score", "op": "<", "value": 60}
            ],
            limit=50,
            context_mode="minimal"
        )
    """
    # 實作邏輯...
```

---

## 📝 下一步

1. **實作 `mcp_adapter.py` 模組**
   - Tool discovery engine
   - Execution sandbox
   - Context optimizer
   - PII anonymizer

2. **建立範例工具**
   - `tools/firestore/query.py`
   - `tools/slack/send_message.py`
   - `tools/compute/statistics.py`

3. **整合 Agent 8**
   - 修改 Agent 8 handler 呼叫 Agent 9
   - 測試對話場景（"王小明這週案件？"）

4. **效能測試**
   - Token 優化比例
   - 執行效能
   - 快取命中率

5. **安全測試**
   - 超時處理
   - 記憶體限制
   - PII 洩漏檢查
