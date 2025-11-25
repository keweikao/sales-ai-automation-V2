# AI 助理快速上手指南 (v2.1)

**目標**：讓任何 AI 助理在 2 分鐘內掌握專案核心工作流程。

---

## 🎯 三大核心原則 (Top 3 Core Principles)

**所有操作前，請務必遵守以下原則：**

1. **語言第一：LLM 回覆嚴格遵守以繁體中文回應。**
2. **工具優先序：永遠先評估，後執行。**
    - **優先級**：`MCP Server` > `Subagent (Claude only)` > `直接工具 (Bash/Read/Grep)`。
    - **MCP 高效原則**：
      - 將工具視為 **API**，在程式碼中使用迴圈、條件、錯誤處理
      - 在執行環境中處理資料，**只回傳摘要**（減少 80% token）
      - 按需載入工具，建立可重複使用的技能
      - 詳見：`docs/MCP_BEST_PRACTICES.md`
    - **禁止行為**：在未經評估前，直接使用 `gcloud`、`Read`、`Grep` 等工具。花 2 分鐘評估，可節省 80% 以上的 Token 成本。

3. **部署唯一規則：永遠使用 `/deploy` 命令。**
    - **禁止行為**：直接使用 `git commit` 或 `git push`。
    - `/deploy` 會自動執行程式碼品質檢查，確保儲存庫的乾淨與穩定。

---

## 🚀 標準開發流程 (Standard Workflow)

當使用者要求「開始下一個開發任務」時，請遵循以下步驟：

1. **自動初始化程式碼智能工具**：

    ```bash
    python3 tools/code_intelligence/auto_init.py
    ```

    - 此步驟會自動檢查並建立程式碼索引（首次執行約需 30 秒）
    - 後續執行會跳過已存在的索引
    - **所有 AI 模型都應在開始工作前執行此步驟**

2. **同步狀態**：閱讀 `DEVELOPMENT_LOG.md`，了解最新的工作進度與待辦事項。

3. **評估與決策 (強制)**：根據任務需求，回答以下問題以決定最高效的工具：
    - **會重複呼叫 API 或指令 (>= 3次) 嗎？** → **是**：建置或使用 `MCP Server`。
    - **需要探索未知程式碼或多輪試錯嗎？** → **是**：使用 `Subagent` (僅限 Claude)。
    - **操作單一且目標明確嗎？** → **是**：使用 `直接工具`。

4. **提案與確認**：向使用者簡要報告您計畫採用的方法（MCP/Subagent/直接工具）、預期成果，並請求確認。

5. **執行開發**：獲得同意後，開始執行任務。

---

## 🛠️ 工具選擇速查表 (Tool Selection Cheat Sheet)

| 任務類型 | 推薦方法 | AI 支援 |
| :--- | :--- | :--- |
| **重複性 API/CLI 操作** (如 `gcloud`, `kubectl`) | **MCP Server** | ✅ 所有模型 |
| **程式碼探索、多輪試錯** (不確定路徑/參數) | **Subagent** | ⚠️ 僅限 Claude |
| **單一、明確的檔案操作或指令** | **直接工具** | ✅ 所有模型 |

> **非 Claude 模型須知**：您無法使用 `Subagent`。當需要探索或試錯時，請優先考慮建置 `MCP Server`，或向使用者說明功能限制。

---

## 🧠 程式碼智能工具 (Code Intelligence Tools)

**自動可用**：所有 AI 模型在執行 `auto_init.py` 後即可使用以下工具。

### 常用命令

```bash
# 找出所有 AI 代理
python3 tools/code_intelligence/cli.py find-agents

# 搜尋程式碼符號
python3 tools/code_intelligence/cli.py search "關鍵字"

# 查看索引統計
python3 tools/code_intelligence/cli.py index-stats

# 提取 API 端點
python3 tools/code_intelligence/cli.py extract-endpoints
```

### 使用時機

- 🔍 **需要找出特定代理或類別時**：使用 `find-agents` 或 `search`
- 📊 **需要了解專案結構時**：使用 `index-stats`
- 🔌 **需要找出 API 端點時**：使用 `extract-endpoints`

詳細使用方法請參考：`docs/CODE_INTELLIGENCE_GUIDE.md`

---

## 📚 關鍵文件參考 (Key Documents)

- **開發日誌 (必讀)**: `DEVELOPMENT_LOG.md` - 了解所有歷史決策與進度。
- **系統原則**: `memory/constitution.md` - 了解成本、效能、品質的核心要求。
- **功能規格**: `specs/001-sales-ai-automation/spec.md` - 查閱使用者故事與功能細節。
- **架構計畫**: `specs/001-sales-ai-automation/plan.md` - 了解技術架構與成本分析。
- **程式碼智能指南**: `docs/CODE_INTELLIGENCE_GUIDE.md` - 程式碼智能工具完整使用指南。
- **MCP 最佳實踐**: `docs/MCP_BEST_PRACTICES.md` - MCP 高效使用指南（減少 80% token 消耗）。

---

*上次更新: 2025-11-25*
