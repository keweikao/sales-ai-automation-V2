# Speckit Subagent 使用指南

完整指南，教你如何在 Speckit 專案中使用 Subagents。

## 🎯 快速開始

### 最簡單的用法

```
實作任務 3.2，使用 speckit-implementer subagent

要求：
- 使用 MCP API 取得任務資訊
- Token < 3,500
- 報告 token 使用量
```

### 平行實作多個任務

```
使用 3 個 speckit-implementer subagents 平行實作任務 1.1, 1.2, 1.3

每個 subagent 必須：
- 使用 MCP API
- Token < 3,500
- 互相不干擾（不同檔案）
```

## 🤖 可用的 Subagents

### 1. speckit-implementer
**用途**：實作任務
**Token 預算**：< 3,500 per task
**使用時機**：
- 實作功能
- 修改程式碼
- 寫單元測試

**範例**：
```
使用 speckit-implementer 實作任務 2.1
```

### 2. speckit-planner
**用途**：規劃執行策略
**Token 預算**：< 2,000
**使用時機**：
- 分析任務相依性
- 建立執行計畫
- 估計工作量

**範例**：
```
使用 speckit-planner 分析任務 1.1 到 1.5，建議執行策略
```

### 3. speckit-researcher
**用途**：研究需求和技術
**Token 預算**：< 1,500
**使用時機**：
- 調查需求細節
- 查詢技術決策
- 驗證對齊性

**範例**：
```
使用 speckit-researcher 研究「認證系統的安全性需求」
```

### 4. speckit-tester
**用途**：撰寫和執行測試
**Token 預算**：< 2,500
**使用時機**：
- 寫測試（TDD）
- 執行測試
- 驗證覆蓋率

**範例**：
```
使用 speckit-tester 為任務 2.1 撰寫測試
```

### 5. speckit-documenter
**用途**：更新文件
**Token 預算**：< 1,000
**使用時機**：
- 更新 API 文件
- 撰寫使用指南
- 更新技術文件

**範例**：
```
使用 speckit-documenter 為任務 2.1 更新文件
```

### 6. speckit-debugger
**用途**：分析日誌與錯誤
**Token 預算**：< 2,000
**使用時機**：
- 分析大型 log 檔案
- 找出錯誤的根本原因
- 建議解決方案

**範例**：
```
使用 speckit-debugger 分析 tmp/error.log 的錯誤
```

## 📋 預定義工作流程

### Workflow 1: parallel-tasks
**用途**：平行實作多個獨立任務

```
使用 parallel-tasks workflow 實作任務 1.1, 1.2, 1.3
```

### Workflow 2: feature-development
**用途**：完整功能開發（從規劃到文件）

```
使用 feature-development workflow 開發「使用者認證」功能
任務：2.1, 2.2, 2.3
```

### Workflow 3: implement-phase
**用途**：完整實作階段執行

```
使用 implement-phase workflow 執行所有待處理任務
```

## 💡 最佳實踐

### 1. 總是使用 MCP API 或檔案路徑
```
❌ 錯誤：
const content = fs.readFileSync('spec.md')

✅ 正確 (MCP):
import * as tasks from './.specify/mcp-server/servers/tasks/index.js';
const task = await tasks.getTaskById({ taskId: '3.2', includeContext: true });

✅ 正確 (檔案):
// 當處理大型、非結構化數據時
const logContent = await read_file({ absolute_path: '/path/to/your/log.txt' });
```

### 2. 控制 Token 預算
```
每個 subagent 完成時應報告：

[Subagent: speckit-implementer]
[Task: 3.2]
[Token Usage: 3,200]
[Status: completed]
```

### 3. 明確任務邊界
```
✅ 好的任務分配：
Subagent 1: 修改 /src/auth/*.ts
Subagent 2: 修改 /src/user/*.ts  
Subagent 3: 修改 /src/api/*.ts

❌ 壞的任務分配：
Subagent 1: 實作認證（檔案範圍不明確）
Subagent 2: 實作使用者功能（檔案範圍不明確）
→ 可能產生檔案衝突
```

### 4. 依序執行有相依性的任務
```
✅ 正確順序：
批次 1 (平行): Task 1.1, 1.2, 1.3 (無相依)
[等待批次 1 完成]
批次 2 (平行): Task 2.1, 2.2 (依賴批次 1)

❌ 錯誤做法：
一次平行執行所有任務（忽略相依性）
→ Task 2.1 會失敗（缺少 Task 1.1 的輸出）
```

### 5. 監控進度
```
每完成一個批次，檢查狀態：

請報告當前實作進度：
- 已完成任務
- 進行中任務
- 遇到的問題
- Token 使用統計
```

## 🎯 常見場景

### 場景 1：實作單一任務
```
實作任務 3.2

使用 speckit-implementer：
- 用 MCP API 取得任務資訊（includeContext: true）
- 實作功能
- 撰寫測試
- 執行測試
- 報告 token 使用量
```

### 場景 2：平行實作 3 個任務
```
平行實作任務 1.1, 1.2, 1.3

使用 3 個 speckit-implementer subagents：
- 每個處理一個任務
- 使用 MCP API
- Token < 3,500 per task
- 平行執行
```

### 場景 3：完整功能開發
```
開發「使用者註冊」功能

使用 feature-development workflow：
- Stage 1: Research (speckit-researcher)
- Stage 2: Planning (speckit-planner)
- Stage 3: TDD (speckit-tester)
- Stage 4: Implementation (speckit-implementer)
- Stage 5: Documentation (speckit-documenter)

所有 subagents 使用 MCP API。
```

### 場景 4：分析 Log 檔案
```
分析 tmp/error.log 的錯誤

1. 將錯誤訊息儲存到 tmp/error.log
2. 使用 speckit-debugger subagent：
   - 讀取檔案內容
   - 分析根本原因
   - 提出解決方案
   - 報告分析結果
```

### 場景 5：繼續未完成的工作
```
繼續實作

當前狀態：批次 1 已完成，批次 2 進行中

使用 MCP API 檢查狀態：
- 列出所有待處理任務
- 識別下一批次
- 平行執行

使用 speckit-implementer subagents。
```

## 📊 效能監控

### 檢查 Token 使用
```
請報告所有 subagent 的 token 使用：

預期輸出：
Subagent 1 (speckit-implementer): 3,200 tokens
Subagent 2 (speckit-implementer): 2,900 tokens
Subagent 3 (speckit-implementer): 3,400 tokens
Total: 9,500 tokens
Average: 3,167 tokens per task
```

### 比較效能
```
請比較使用 subagents 前後的效能：

傳統方式：
- 時間：45 minutes
- Tokens：45,000

使用 Subagents + MCP：
- 時間：15 minutes (67% ↓)
- Tokens：9,500 (79% ↓)

總提升：5倍效率
```

## 🔧 故障排除

### 問題 1：Subagent 超過 token 預算
```
解決方案：
1. 確認 subagent 使用了 MCP API（不是讀取檔案）
2. 檢查是否載入了不必要的上下文
3. 減少任務範圍
```

### 問題 2：Subagents 互相衝突
```
解決方案：
1. 確認任務修改不同的檔案
2. 明確定義每個 subagent 的檔案範圍
3. 使用 speckit-planner 分析相依性
```

### 問題 3：Subagent 沒有使用 MCP API
```
解決方案：
1. 在指令中明確要求「使用 MCP API」
2. 提供程式碼範例
3. 糾正錯誤行為：
   
   ❌ 你做錯了！不要讀取 spec.md
   ✅ 使用 MCP API：
   import * as spec from './.specify/mcp-server/servers/spec/index.js';
```

## 🎓 進階技巧

### 技巧 1：Resume Subagent
```
長時間任務可以跨 session 繼續：

# 第一次
使用 code-analyzer subagent 分析認證模組
[返回 agentId: "abc123"]

# 之後
Resume subagent abc123 並分析授權邏輯
```

### 技巧 2：自訂 Subagent
```
建立專門的 subagent：

檔案：.specify/agents/my-custom-agent.md

---
name: my-custom-agent
description: My specialized agent
tools: Bash, Read, Write
model: sonnet
---

[自訂規則和工作流程]
```

### 技巧 3：嵌套工作流程
```
大型專案可以嵌套工作流程：

主工作流程：implement-phase
  ├── 批次 1：使用 parallel-tasks workflow
  ├── 批次 2：使用 feature-development workflow
  └── 批次 3：使用 parallel-tasks workflow
```

## 🎉 總結

使用 Subagents 的好處：
- ⚡ 速度：平行執行節省 60-70% 時間
- 💰 成本：結合 MCP API 節省 80-90% tokens
- 🎯 品質：專門化 subagents 提供更好的結果
- 📊 可擴展：處理大型專案更容易

開始使用：
1. 選擇一個工作流程
2. 明確指定使用 MCP API
3. 設定 token 預算
4. 監控進度和效能

祝你開發順利！🚀
```