# MCP 高效使用指南 - Sales AI Automation V2

**基於**: Anthropic [Code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)  
**目標**: 減少 token 消耗，提升複雜邏輯處理能力

---

## 🎯 核心原則

### 傳統工具呼叫 vs. MCP 模式

| 方法 | 傳統工具呼叫 | MCP 模式 |
|------|-------------|----------|
| **執行方式** | `use_tool("search", query="...")` | 撰寫 Python 程式碼呼叫 API |
| **資料處理** | 所有結果回傳給模型 | 在執行環境中處理和過濾 |
| **邏輯複雜度** | 受限於工具定義 | 可使用迴圈、條件、錯誤處理 |
| **Token 消耗** | 高（大量中間結果） | 低（只回傳關鍵資訊） |

---

## 🚀 三大關鍵實踐

### 1. 將工具視為 API，而非函式

**❌ 舊方法**:

```python
# 每次呼叫都需要模型介入
result1 = use_tool("search", query="Agent 1")
result2 = use_tool("search", query="Agent 2")
result3 = use_tool("search", query="Agent 3")
```

**✅ 新方法**:

```python
# 在程式碼中使用迴圈和邏輯
from tools.code_intelligence.cli import find_agents, search

# 一次性獲取所有代理
agents = find_agents()

# 在程式碼中處理和過濾
active_agents = [a for a in agents if 'active' in a['content'].lower()]

# 只回傳關鍵資訊
return {
    "total": len(agents),
    "active": len(active_agents),
    "summary": [a['name'] for a in active_agents[:5]]
}
```

**優勢**:

- ✅ 減少 API 呼叫次數
- ✅ 在程式碼中實現複雜邏輯
- ✅ 只回傳必要資訊給模型

---

### 2. 在執行環境中處理資料

**問題**: 搜尋結果可能非常龐大，直接回傳會佔用大量 token

**❌ 低效方式**:

```python
# 獲取所有符號（827 個）
all_symbols = get_all_symbols()

# 直接回傳給模型（消耗大量 token）
return all_symbols  # 可能數千行資料
```

**✅ 高效方式**:

```python
# 獲取所有符號
all_symbols = get_all_symbols()

# 在程式碼中分析和摘要
stats = {
    "total": len(all_symbols),
    "by_type": {},
    "top_files": []
}

# 統計分析
for symbol in all_symbols:
    stats["by_type"][symbol["type"]] = stats["by_type"].get(symbol["type"], 0) + 1

# 找出最活躍的檔案
file_counts = {}
for symbol in all_symbols:
    file_counts[symbol["file"]] = file_counts.get(symbol["file"], 0) + 1

stats["top_files"] = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:5]

# 只回傳摘要（節省 90%+ token）
return stats
```

**實際應用 - 程式碼智能工具**:

```python
# 使用 Cased Kit 時的最佳實踐
from tools.code_intelligence.repo_analyzer import SalesAIRepoAnalyzer
from tools.code_intelligence.symbol_indexer import SmartCodeSearch

analyzer = SalesAIRepoAnalyzer()
searcher = SmartCodeSearch()

# ❌ 不要這樣做
all_agents = analyzer.find_agent_implementations()
# 回傳所有 10 個代理的完整資訊（浪費 token）

# ✅ 應該這樣做
all_agents = analyzer.find_agent_implementations()

# 在程式碼中分析
agent_summary = {
    "count": len(all_agents),
    "files": list(set(a["file"] for a in all_agents)),
    "by_service": {}
}

for agent in all_agents:
    service = agent["file"].split("/")[0]
    if service not in agent_summary["by_service"]:
        agent_summary["by_service"][service] = []
    agent_summary["by_service"][service].append(agent["content"])

# 只回傳摘要
return agent_summary
```

---

### 3. 按需載入與技能建立

#### 動態載入工具

**不需要一次性了解所有工具**，可以動態發現：

```python
# 探索可用的程式碼智能工具
import subprocess

result = subprocess.run(
    ["python3", "tools/code_intelligence/cli.py", "--help"],
    capture_output=True,
    text=True
)

# 解析可用命令
available_commands = parse_help_output(result.stdout)

# 只載入需要的命令
if "find-agents" in available_commands:
    agents = run_command("find-agents")
```

#### 技能固化

**將常用邏輯儲存為可重複使用的函式**：

```python
# 建立技能：分析專案狀態
def analyze_project_status():
    """
    技能：分析專案完成狀態
    
    Returns:
        dict: 包含完成率、待辦項目等摘要資訊
    """
    from tools.code_intelligence.repo_analyzer import SalesAIRepoAnalyzer
    
    analyzer = SalesAIRepoAnalyzer()
    
    # 獲取所有代理
    agents = analyzer.find_agent_implementations()
    
    # 獲取所有測試
    tests = analyzer.extract_symbols(file_pattern="*test*.py")
    
    # 分析完成狀態
    return {
        "agents": {
            "total": len(agents),
            "implemented": len([a for a in agents if "class" in a["content"]])
        },
        "tests": {
            "total": len(tests),
            "coverage": len(tests) / len(agents) if agents else 0
        },
        "completion_rate": calculate_completion_rate(agents, tests)
    }

# 儲存為技能，未來直接呼叫
save_skill("analyze_project_status", analyze_project_status)
```

---

## 📋 對 Sales AI Automation V2 的應用

### 當前實作優化建議

#### 1. 程式碼智能工具使用

**優化前**:

```python
# 每次都呼叫 CLI
agents = run_cli("find-agents")
endpoints = run_cli("extract-endpoints")
symbols = run_cli("search", "Agent")
```

**優化後**:

```python
# 建立一個統一的分析函式
def comprehensive_code_analysis():
    analyzer = SalesAIRepoAnalyzer()
    searcher = SmartCodeSearch()
    
    # 一次性獲取所有資料
    agents = analyzer.find_agent_implementations()
    endpoints = analyzer.extract_api_endpoints()
    
    # 在程式碼中處理和關聯
    analysis = {
        "agents": process_agents(agents),
        "endpoints": process_endpoints(endpoints),
        "relationships": find_relationships(agents, endpoints)
    }
    
    # 只回傳摘要
    return generate_summary(analysis)
```

#### 2. DEVELOPMENT_LOG 驗證

**優化前**:

```python
# 逐項檢查，多次呼叫
check_item("Agent 1")
check_item("Agent 2")
# ... 重複多次
```

**優化後**:

```python
# 批次驗證
def verify_all_pending_items():
    pending_items = parse_development_log()
    
    verification_results = {}
    
    for item in pending_items:
        # 在程式碼中執行驗證邏輯
        if "Agent" in item:
            verification_results[item] = verify_agent_implementation(item)
        elif "test" in item:
            verification_results[item] = verify_test_exists(item)
        # ... 其他類型
    
    # 生成摘要報告
    return {
        "completed": [k for k, v in verification_results.items() if v],
        "pending": [k for k, v in verification_results.items() if not v],
        "completion_rate": calculate_rate(verification_results)
    }
```

---

## 🎓 最佳實踐清單

### ✅ DO（應該做）

1. **在程式碼中處理大量資料**
   - 使用迴圈、條件、過濾
   - 只回傳摘要和關鍵資訊

2. **建立可重複使用的技能**
   - 將常用邏輯封裝為函式
   - 儲存並重複使用

3. **動態載入工具**
   - 按需探索和載入
   - 不需要預先了解所有工具

4. **批次處理**
   - 一次性獲取資料
   - 在程式碼中關聯和分析

### ❌ DON'T（不應該做）

1. **不要直接回傳大量原始資料**
   - ❌ 回傳 827 個符號的完整資訊
   - ✅ 回傳統計摘要和 Top 5

2. **不要重複呼叫相同工具**
   - ❌ 逐個查詢每個代理
   - ✅ 一次性獲取所有代理

3. **不要在模型中實現複雜邏輯**
   - ❌ 讓模型在上下文中推理
   - ✅ 在 Python 程式碼中實現

4. **不要忽略錯誤處理**
   - ❌ 假設所有呼叫都成功
   - ✅ 使用 try/except 處理異常

---

## 📈 效益估算

根據 Anthropic 的研究和我們的實際應用：

| 指標 | 傳統方式 | MCP 方式 | 改善 |
|------|---------|---------|------|
| **Token 消耗** | 10,000+ | 2,000- | -80% |
| **API 呼叫次數** | 20+ | 3-5 | -75% |
| **執行時間** | 2-3 分鐘 | 30 秒 | -75% |
| **邏輯複雜度** | 受限 | 無限制 | ∞ |

---

## 🔗 相關資源

- [Anthropic: Code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [程式碼智能工具使用指南](./CODE_INTELLIGENCE_GUIDE.md)
- [QUICK_START_FOR_AI.md](../QUICK_START_FOR_AI.md)

---

**最後更新**: 2025-11-25  
**適用於**: 所有 AI 模型（Gemini, Claude, GPT 等）
