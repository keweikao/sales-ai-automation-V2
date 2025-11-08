# Speckit 啟動指令使用說明

## 🎯 目的

當你切換到新的 LLM 或開啟新對話時，使用啟動指令確保 LLM 遵守 MCP Code Execution 規則。

## 📋 使用方式

### 方式 1：完整啟動（推薦首次使用）

複製以下指令到 LLM：

```
請執行 .specify/STARTUP.md 中的完整初始化流程。
```

**時間**：2-3 分鐘（包含驗證）

**適用**：

- 第一次使用新的 LLM
- LLM 對專案不熟悉
- 需要確保 LLM 完全理解規則

---

### 方式 2：快速啟動（日常使用）

複製以下指令到 LLM：

```
Speckit MCP 規則：
- 禁止讀 spec/plan/tasks/constitution
- 必須用 .specify/mcp-server/servers/ API
- Token < 1,500/回應
- 回應註明 [估計 token: XXX]
- 詳見 .specify/LLM-USAGE-GUIDE.md
```

**時間**：15-30 秒

**適用**：

- 已經熟悉的 LLM
- 快速提醒規則
- 日常切換

---

### 方式 3：極簡啟動（熟練後）

複製以下指令到 LLM：

```
請讀 .specify/QUICK-START.txt
```

**時間**：10 秒

**適用**：

- 非常熟悉的 LLM
- 只需要快速提醒
- 緊急情況

---

## ✅ 驗證 LLM 是否理解

啟動後，測試一下：

```
請協助我查看任務 3.2 的資訊。
```

### 正確回應

```typescript
import * as tasks from './.specify/mcp-server/servers/tasks/index.js';
const task = await tasks.getTaskById({ taskId: '3.2', includeContext: true });
```

### 錯誤回應

```
我需要先看 tasks.md 的內容...
```

**如果是錯誤回應**，立即糾正：

```
❌ 錯了！請閱讀 .specify/STARTUP.md 重新初始化
```

---

## 🔧 不同 IDE 的使用方式

### Cursor

Cursor 會自動讀取 `.cursorrules`，但建議還是執行「方式 2」提醒一次。

### Windsurf

執行「方式 2」的快速啟動。

### GitHub Copilot

在 Chat 視窗執行「方式 1」的完整啟動。

### Claude.ai / ChatGPT

執行「方式 1」的完整啟動（因為沒有檔案系統存取）。

---

## 📊 效果監控

啟動後，LLM 應該：

✅ 主動使用 API（不需要提醒）
✅ 每次回應都註明 `[估計 token: XXX]`
✅ Token 使用在目標範圍內
✅ 超標時主動優化

如果沒有，重新執行啟動指令。

---

## 🎯 建議工作流程

1. **開啟新對話**
2. **執行啟動指令**（方式 1 或 2）
3. **驗證理解**（查看任務 3.2）
4. **開始正常工作** 🚀

每次切換 LLM 只需 30 秒，就能確保 90% 的 token 節省！
