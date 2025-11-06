# MCP Integration - Task List for Executing LLM

**Status**: Phase 1 Complete ✅ | Phase 2 Ready to Start 🔧

**Primary Reference**: Read `IMPLEMENTATION_GUIDE.md` in this directory first.

---

## 🎯 Current Task: Phase 2 - Tool Infrastructure Setup

### Task 2.1: Create Tool Directory Structure

**Action**: Execute these bash commands

```bash
cd /workspaces/sales-ai-automation-V2

mkdir -p tools/firestore
mkdir -p tools/gcs
mkdir -p tools/bigquery
mkdir -p tools/slack
mkdir -p tools/compute

touch tools/__init__.py
touch tools/firestore/__init__.py
touch tools/gcs/__init__.py
touch tools/bigquery/__init__.py
touch tools/slack/__init__.py
touch tools/compute/__init__.py
```

**Verification**: Check all directories exist

```bash
ls -la tools/
ls -la tools/firestore/
```

**Expected Output**:
```
tools/
  __init__.py
  firestore/
    __init__.py
  gcs/
    __init__.py
  ...
```

---

### Task 2.2: Implement First Tool - firestore.query

**Action**: Create file `tools/firestore/query.py`

**Template Source**: Copy complete template from `IMPLEMENTATION_GUIDE.md` Step 2.2

**Key Requirements**:
1. ✅ Include docstring with `# derived from Anthropic official doc (2025)`
2. ✅ Support 3 context modes: minimal, full, aggregate
3. ✅ Implement 5-stage filtering logic:
   - Stage 1: Query execution (in environment)
   - Stage 2: Field filtering (in environment)
   - Stage 3: Result truncation (in environment)
   - Stage 4: Return to model
4. ✅ Return dict with keys: `results`, `total_count`, `returned_count`, `truncated`, `context_mode`

**Verification**: Test import

```bash
cd /workspaces/sales-ai-automation-V2
python -c "from tools.firestore.query import query; print('Import successful')"
```

**Expected**: No errors (Firestore connection error is OK at this stage)

---

### Task 2.3: Mark Phase 2 Complete

**Checklist**:
- [ ] All directories created with `__init__.py`
- [ ] `tools/firestore/query.py` created
- [ ] Import test passes
- [ ] Code includes proper docstrings and comments

**Report Back to User**:
```
✅ Phase 2 完成

已建立：
- tools/ 目錄結構（5 個子目錄）
- tools/firestore/query.py（支援 minimal/full/aggregate 模式）

驗證結果：
- Import 測試通過
- 準備進入 Phase 3（Agent 8 整合）

是否繼續執行 Phase 3？
```

---

## 🎯 Next Task: Phase 3 - MCP Adapter Integration

**Do NOT start until Phase 2 is verified complete.**

### Task 3.1: Read Current Agent 8 Handler

**Action**: Read file to understand existing structure

```bash
Read: src/slack_app/handlers/agent8_handler.py
```

**Look for**:
- Existing `handle_user_query()` method
- How user queries are currently processed
- Where to insert MCP integration code

---

### Task 3.2: Add MCP Import and Initialization

**Action**: Edit `src/slack_app/handlers/agent8_handler.py`

**Add to imports** (top of file):
```python
from mcp_adapter import MCPAdapter
```

**Add to `__init__()` method**:
```python
def __init__(self):
    # ... existing initialization ...
    self.mcp = None  # MCP adapter (initialized per session)
```

---

### Task 3.3: Update handle_user_query() Method

**Action**: Modify existing method to integrate MCP

**Reference**: Complete code in `IMPLEMENTATION_GUIDE.md` Step 3.1

**Key additions**:
1. Initialize MCP adapter per session
2. Check if query needs tools (`_needs_tools()`)
3. If yes:
   - Discover tools (`discover_tools()`)
   - Select tool (`_select_tool()`)
   - Load definition (`load_tool()`)
   - Construct params (`_construct_tool_params()`)
   - Execute tool (`execute_tool()`)
   - Generate answer with data
4. If no: Use existing direct LLM response

---

### Task 3.4: Add Helper Methods

**Action**: Add these methods to Agent8Handler class

Methods to add:
- `_needs_tools(query: str) -> bool`
- `_infer_tool_category(query: str) -> str`
- `_select_tool(tools: List[str], query: str) -> str`
- `_construct_tool_params(query: str, tool_def: dict) -> dict`
- `_generate_answer_with_data(query: str, data: Any) -> str`

**Reference**: Complete implementations in `IMPLEMENTATION_GUIDE.md` Step 3.1

---

### Task 3.5: Verify Agent 8 Integration

**Action**: Test import and basic functionality

```bash
cd /workspaces/sales-ai-automation-V2
python -c "
from src.slack_app.handlers.agent8_handler import Agent8Handler
handler = Agent8Handler()
print('Agent 8 handler initialization successful')
print(f'MCP adapter available: {handler.mcp is not None or hasattr(handler, \"mcp\")}')
"
```

**Expected**: No import errors

---

### Task 3.6: Mark Phase 3 Complete

**Checklist**:
- [ ] MCP import added
- [ ] MCP initialization in `__init__()`
- [ ] `handle_user_query()` updated with MCP logic
- [ ] All 5 helper methods added
- [ ] Import test passes

**Report Back to User**:
```
✅ Phase 3 完成

已更新：
- src/slack_app/handlers/agent8_handler.py
  - MCP adapter 整合
  - 5 個輔助方法
  - 工具執行流程

驗證結果：
- Import 測試通過
- Agent 8 handler 可正常初始化
- 準備進入 Phase 4（測試驗證）

是否繼續執行 Phase 4 測試？
```

---

## 🎯 Next Task: Phase 4 - Testing & Validation

**Do NOT start until Phase 3 is verified complete.**

### Task 4.1: Create Unit Test File

**Action**: Create `tests/unit/test_mcp_adapter.py`

**Template**: Copy from `IMPLEMENTATION_GUIDE.md` Step 4.1

**Tests to include**:
1. `TestPIIAnonymizer` - email, phone, nested data anonymization
2. `TestToolRegistry` - tool discovery, definition loading
3. `TestMCPAdapter` - initialization, session stats

---

### Task 4.2: Run Unit Tests

**Action**: Execute pytest

```bash
cd /workspaces/sales-ai-automation-V2
pytest tests/unit/test_mcp_adapter.py -v
```

**Expected**: All tests pass (or skip if tools not yet created)

---

### Task 4.3: Create Integration Test File (Optional)

**Action**: Create `tests/integration/test_mcp_firestore_integration.py`

**Note**: This requires Firestore to be configured. Skip if not available.

**Template**: Copy from `IMPLEMENTATION_GUIDE.md` Step 4.2

---

### Task 4.4: Manual E2E Test

**Action**: Test Agent 8 with MCP via Slack

**Test Query**: "王小明這週的案件健康度如何？"

**Expected Flow**:
1. Agent 8 receives query
2. Detects tools needed → category = "firestore"
3. Discovers tools → finds "firestore.query"
4. Loads definition
5. Constructs params (filters by rep_name)
6. Executes tool with context_mode="minimal"
7. Returns filtered data (PII anonymized)
8. Generates natural language response

**Verification**: Check Slack response includes data summary

---

### Task 4.5: Mark Phase 4 Complete

**Checklist**:
- [ ] Unit tests created and pass
- [ ] Integration tests created (or documented as skipped)
- [ ] Manual E2E test successful (or documented issue)

**Report Back to User**:
```
✅ Phase 4 完成

測試結果：
- Unit tests: X/Y 通過
- Integration tests: [需要 Firestore] / 已略過
- E2E test: [成功] / [需要手動驗證]

已知問題：
- [列出任何發現的問題]

是否繼續執行 Phase 5（監控優化）？
或是否需要先處理測試中發現的問題？
```

---

## 🎯 Next Task: Phase 5 - Monitoring & Optimization

**Do NOT start until Phase 4 issues are resolved.**

### Task 5.1: Create Token Tracker Module

**Action**: Create `src/slack_app/monitoring/token_tracker.py`

**Template**: Copy from `IMPLEMENTATION_GUIDE.md` Step 5.1

---

### Task 5.2: Integrate Token Tracker with MCP Adapter

**Action**: Update `mcp_adapter.py` to use TokenUsageTracker

**Changes**:
1. Import TokenUsageTracker
2. Initialize in `__init__()`
3. Call `measure_optimization()` in `execute_tool()`
4. Add metrics to result dict

---

### Task 5.3: Verify Token Optimization

**Action**: Execute test query and check metrics

```python
mcp = MCPAdapter(session_id="test-token-001")
result = mcp.execute_tool("firestore.query", {
    "collection": "cases",
    "filters": [{"field": "created_date", "op": ">=", "value": "2025-01-01"}],
    "limit": 100,
    "context_mode": "minimal"
})

print(result.get("token_optimization"))
# Expected: reduction_pct > 90
```

---

### Task 5.4: Mark Phase 5 Complete

**Checklist**:
- [ ] TokenUsageTracker implemented
- [ ] Integrated with MCP adapter
- [ ] Test shows >90% token reduction for minimal mode
- [ ] Test shows >95% token reduction for aggregate mode

**Report Back to User**:
```
✅ Phase 5 完成

Token 優化結果：
- Minimal mode: X% 節省（目標 90%+）
- Aggregate mode: Y% 節省（目標 95%+）
- 總體效果：[達標] / [需調整]

全部 5 個 Phase 已完成！

下一步建議：
1. 部署到測試環境
2. 擴充更多工具（GCS、BigQuery、Slack）
3. 建立監控儀表板
```

---

## 📋 Quick Reference

### File Locations

```
/workspaces/sales-ai-automation-V2/
├── specs/001-sales-ai-automation/
│   ├── integration-mcp/
│   │   ├── spec.md                          # 規格文件
│   │   ├── IMPLEMENTATION_GUIDE.md          # 實施指南（主要參考）
│   │   └── TASK_LIST_FOR_LLM.md            # 本文件
│   └── AGENT9_MCP_INTEGRATION.md           # Agent 9 設計
├── src/slack_app/
│   ├── mcp_adapter.py                       # MCP 核心模組
│   ├── handlers/
│   │   └── agent8_handler.py                # 需要修改
│   └── monitoring/
│       └── token_tracker.py                 # Phase 5 新增
├── tools/
│   └── firestore/
│       └── query.py                         # Phase 2 新增
├── templates/prompts/
│   ├── mcp-tool-discovery.md                # 工具探索指南
│   └── mcp-context-optimization.md          # Context 優化指南
└── tests/
    ├── unit/
    │   └── test_mcp_adapter.py              # Phase 4 新增
    └── integration/
        └── test_mcp_firestore_integration.py # Phase 4 新增
```

### Important Commands

```bash
# Check current status
ls -la tools/
ls -la src/slack_app/mcp_adapter.py

# Test imports
python -c "from tools.firestore.query import query; print('OK')"
python -c "from src.slack_app.mcp_adapter import MCPAdapter; print('OK')"

# Run tests
pytest tests/unit/test_mcp_adapter.py -v
pytest tests/integration/ -v -m integration

# Test MCP adapter
cd src/slack_app
python mcp_adapter.py
```

---

## 🚨 Important Reminders

1. **Do NOT skip phases** - Each phase builds on the previous
2. **Verify after each task** - Run verification commands
3. **Report issues immediately** - Don't proceed if tests fail
4. **Include proper attribution** - All code must have `# derived from Anthropic official doc (2025)` where applicable
5. **Ask before deviating** - If something seems wrong, ask user first

---

**Start Here**: Begin with Phase 2, Task 2.1
**Questions**: Ask user if anything is unclear
**Updates**: Report progress after each phase completion
