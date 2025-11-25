# Cased Kit 程式碼智能工具使用指南

## 概述

本工具包整合了 [Cased Kit](https://github.com/cased/kit)，為 Sales AI Automation V2 專案提供強大的程式碼智能功能。

## 功能特色

- 🔍 **程式碼搜尋**: 快速找到函數、類別和符號
- 📊 **依賴分析**: 分析服務間的依賴關係
- 🤖 **AI 代理查找**: 自動找出所有 AI 代理實作
- 📝 **符號索引**: 建立可搜尋的程式碼索引
- 🔌 **API 端點提取**: 提取所有 API 端點定義

## 安裝

### 1. 安裝依賴

```bash
cd /Users/stephen/Desktop/sales-ai-automation-V2
pip install -r tools/code_intelligence/requirements.txt
```

### 2. 驗證安裝

```bash
python tools/code_intelligence/cli.py --help
```

## 使用方法

### CLI 命令

#### 1. 建立符號索引

首次使用前，需要建立符號索引：

```bash
python tools/code_intelligence/cli.py build-index
```

強制重建索引：

```bash
python tools/code_intelligence/cli.py build-index --force
```

#### 2. 搜尋程式碼

搜尋包含特定關鍵字的符號：

```bash
# 搜尋 "Agent"
python tools/code_intelligence/cli.py search "Agent"

# 限制結果數量
python tools/code_intelligence/cli.py search "transcribe" --limit 5
```

#### 3. 找出所有 AI 代理

```bash
python tools/code_intelligence/cli.py find-agents
```

輸出範例：

```
🔍 搜尋 AI 代理...

找到 7 個代理:

  📍 analysis-service/src/agents/agent1_participant.py:15
     class Agent1ParticipantAnalyzer:

  📍 analysis-service/src/agents/agent2_sentiment.py:12
     class Agent2SentimentAnalyzer:
  
  ...
```

#### 4. 提取 API 端點

```bash
python tools/code_intelligence/cli.py extract-endpoints
```

#### 5. 分析服務依賴

```bash
# 輸出到終端
python tools/code_intelligence/cli.py analyze-deps

# 儲存到檔案
python tools/code_intelligence/cli.py analyze-deps --output deps.json
```

#### 6. 查看索引統計

```bash
python tools/code_intelligence/cli.py index-stats
```

輸出範例：

```
📊 索引統計資訊:

總符號數: 1234

類型分布:
  function: 856
  class: 234
  method: 144

索引檔案: .kit-mcp/cache/symbol_index.json
```

### Python API

#### 使用專案分析器

```python
from tools.code_intelligence.repo_analyzer import SalesAIRepoAnalyzer

# 建立分析器
analyzer = SalesAIRepoAnalyzer()

# 找出所有 AI 代理
agents = analyzer.find_agent_implementations()
for agent in agents:
    print(f"{agent['file']}:{agent['line']} - {agent['content']}")

# 提取 API 端點
endpoints = analyzer.extract_api_endpoints()

# 分析依賴關係
deps = analyzer.analyze_service_dependencies()
```

#### 使用符號索引器

```python
from tools.code_intelligence.symbol_indexer import SmartCodeSearch

# 建立搜尋器
searcher = SmartCodeSearch()

# 建立索引
result = searcher.build_index()

# 搜尋符號
results = searcher.search("Agent", limit=10)
for r in results:
    print(f"{r['name']} ({r['type']}) - {r['file']}:{r['line_start']}")

# 按類型搜尋
classes = searcher.search_by_type("class")

# 獲取統計資訊
stats = searcher.get_stats()
print(f"總符號數: {stats['total_symbols']}")
```

## Kit-Dev MCP 整合

### 什麼是 MCP？

Model Context Protocol (MCP) 是一個協定，讓 AI 助手能夠存取外部工具和資料來源。Kit-Dev MCP 提供程式碼智能功能給 AI 助手。

### 安裝 Kit-Dev MCP

```bash
# 使用 uv 安裝
uv tool install kit-dev-mcp
```

### 配置 Gemini CLI

MCP 配置檔案已建立在 `.kit-mcp/config.json`。

如果你的 Gemini CLI 支援 MCP，可以這樣使用：

```bash
# 啟動 Gemini CLI 並載入 MCP
gemini --mcp-config .kit-mcp/config.json

# 在 Gemini CLI 中詢問：
# "請分析 analysis-service 的依賴關係"
# "找出所有使用 Agent1 的地方"
```

### 替代方案（如果 Gemini CLI 不支援 MCP）

直接使用 Python API：

```python
from tools.code_intelligence.repo_analyzer import SalesAIRepoAnalyzer

analyzer = SalesAIRepoAnalyzer()

# 你的 AI 助手可以呼叫這些方法
result = analyzer.analyze_service_dependencies()
```

## 常見使用場景

### 場景 1: 理解新代理的實作

```bash
# 1. 找出所有代理
python tools/code_intelligence/cli.py find-agents

# 2. 搜尋特定代理的使用
python tools/code_intelligence/cli.py search "Agent6"

# 3. 使用 Python API 獲取詳細資訊
python -c "
from tools.code_intelligence.repo_analyzer import SalesAIRepoAnalyzer
analyzer = SalesAIRepoAnalyzer()
usages = analyzer.find_symbol_usages('Agent6')
for u in usages:
    print(f'{u[\"file\"]}:{u[\"line\"]}')
"
```

### 場景 2: 分析服務依賴

```bash
# 生成依賴報告
python tools/code_intelligence/cli.py analyze-deps --output tmp/deps.json

# 檢視報告
cat tmp/deps.json | jq .
```

### 場景 3: 快速導航程式碼

```bash
# 建立索引
python tools/code_intelligence/cli.py build-index

# 搜尋轉錄相關的程式碼
python tools/code_intelligence/cli.py search "transcribe"

# 搜尋 Firestore 相關的程式碼
python tools/code_intelligence/cli.py search "firestore"
```

## 整合到開發工作流程

### 在 Makefile 中使用

已在 `Makefile` 中新增以下目標：

```bash
# 建立程式碼索引
make build-code-index

# 測試程式碼智能工具
make test-code-intelligence
```

### 在 CI/CD 中使用

可以在 GitHub Actions 中自動更新程式碼索引：

```yaml
- name: Build code index
  run: |
    pip install -r tools/code_intelligence/requirements.txt
    python tools/code_intelligence/cli.py build-index
```

## 快取管理

符號索引儲存在 `.kit-mcp/cache/symbol_index.json`。

清除快取：

```bash
rm -rf .kit-mcp/cache
```

重建索引：

```bash
python tools/code_intelligence/cli.py build-index --force
```

## 疑難排解

### 問題: ImportError: No module named 'kit'

**解決方案**: 安裝 kit-ai 套件

```bash
pip install kit-ai
```

### 問題: 索引建立失敗

**解決方案**: 檢查專案路徑是否正確

```python
from tools.code_intelligence.symbol_indexer import SmartCodeSearch

# 確認路徑
searcher = SmartCodeSearch(repo_path="/Users/stephen/Desktop/sales-ai-automation-V2")
```

### 問題: MCP 整合不工作

**解決方案**: 確認 Gemini CLI 版本是否支援 MCP

```bash
gemini --version

# 如果不支援，使用 Python API 替代方案
```

## 效能考量

- **首次索引建立**: 可能需要 1-2 分鐘（取決於專案大小）
- **增量更新**: 未來版本將支援增量更新
- **記憶體使用**: 索引檔案約 1-5 MB

## 下一步

- 探索 [Cased Kit 文檔](https://kit.cased.com)
- 查看 [實施計劃](../../.gemini/antigravity/brain/42fa48d5-4d70-41d7-bfe4-33c192e8f95d/implementation_plan.md)
- 閱讀 [優化分析報告](../../.gemini/antigravity/brain/42fa48d5-4d70-41d7-bfe4-33c192e8f95d/cased_kit_optimization_analysis.md)

## 支援

如有問題，請參考：

- 專案 README: `/Users/stephen/Desktop/sales-ai-automation-V2/README.md`
- 開發指南: `/Users/stephen/Desktop/sales-ai-automation-V2/DEVELOPMENT_GUIDELINES.md`
