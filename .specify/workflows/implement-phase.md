# Implement Phase Workflow

Complete workflow for the implementation phase of a Speckit project.

## Overview

The Implement phase is when you execute all planned tasks. This workflow maximizes efficiency through:
- Parallel task execution
- MCP API usage for minimal token consumption
- Specialized subagents for different aspects

## Prerequisites

- Constitution defined
- Spec completed and validated
- Plan created with implementation details
- Tasks broken down in tasks.md

## Workflow

### Step 1: Load Current Status (Main Agent)
```typescript
import * as tasks from './.specify/mcp-server/servers/tasks/index.js';

// Get all tasks
const allTasks = await tasks.getAllTasks();

// Identify pending tasks
const pendingTasks = allTasks.filter(t => 
  !t.status || t.status === 'pending'
);

console.log(`Total tasks: ${allTasks.length}`);
console.log(`Pending: ${pendingTasks.length}`);
console.log(`Completed: ${allTasks.length - pendingTasks.length}`);
```

### Step 2: Plan Execution Strategy (Subagent)
```
使用 speckit-planner 建立執行策略：

Input: 所有待處理的任務
Output: 批次執行計畫，識別可平行執行的任務組

請使用 MCP API，不要讀取檔案。
```

### Step 3: Execute Task Batches (Subagents)

#### Batch 1: Foundation Tasks
```
批次 1：基礎任務（平行執行）

Subagent 1 (speckit-implementer): Task 1.1 - Database Schema
Subagent 2 (speckit-implementer): Task 1.2 - Base Models
Subagent 3 (speckit-implementer): Task 1.3 - Configuration

每個 subagent:
- 用 MCP API 獲取任務資訊（includeContext: true）
- 實作功能
- 撰寫測試
- 執行測試
- 報告狀態
```

#### Batch 2: Core Logic Tasks
```
批次 2：核心邏輯（平行執行）

[等待批次 1 完成]

Subagent 1 (speckit-implementer): Task 2.1 - Auth Service
Subagent 2 (speckit-implementer): Task 2.2 - User Service
Subagent 3 (speckit-implementer): Task 2.3 - Data Service

[同樣的執行模式]
```

#### Batch 3: Integration Tasks
```
批次 3：整合任務（平行執行）

[等待批次 2 完成]

Subagent 1 (speckit-implementer): Task 3.1 - API Integration
Subagent 2 (speckit-implementer): Task 3.2 - UI Integration
Subagent 3 (speckit-documenter): Task 3.3 - Documentation

[同樣的執行模式]
```

### Step 4: Continuous Validation (Background)

While batches execute, run validation checks:

```
Subagent (speckit-tester): 持續測試
- 監控所有新實作的功能
- 執行單元測試
- 執行整合測試
- 報告測試失敗
```

### Step 5: Final Integration (Main Agent)
```
最後整合（主 Agent）

1. 驗證所有任務已完成
2. 執行完整測試套件
3. 檢查所有驗收標準
4. 執行端到端測試
5. 生成實作報告
```

## Commands

### Start Implementation Phase
```
開始實作階段

使用 implement-phase workflow 完成所有待處理任務。

要求：
- 使用 speckit-planner 建立執行計畫
- 使用 speckit-implementer 平行實作任務
- 使用 speckit-tester 持續驗證
- 每個 subagent 使用 MCP API
- 所有 subagent token < 3,500

請開始執行。
```

### Resume Implementation
```
繼續實作階段

當前狀態：批次 1 已完成，批次 2 進行中

請繼續使用 implement-phase workflow：
- 完成批次 2
- 執行批次 3
- 最後整合驗證

使用 MCP API。
```

### Check Progress
```
檢查實作進度

請使用 MCP API 報告：
- 已完成任務數量
- 進行中任務
- 待處理任務
- Token 使用統計
- 預估剩餘時間
```

## Expected Output

```
=== IMPLEMENT PHASE EXECUTION REPORT ===

## Planning
[speckit-planner] Execution strategy created
- Total tasks: 12
- Batches: 4
- Max parallelism: 3
[Token: 1,800]

## Batch 1: Foundation (3 tasks, parallel)
● Task(1.1) ⎿ Done [Token: 3,200, Time: 12min]
● Task(1.2) ⎿ Done [Token: 2,900, Time: 11min]
● Task(1.3) ⎿ Done [Token: 3,100, Time: 13min]
Batch complete: 13 minutes, 9,200 tokens

## Batch 2: Core Logic (3 tasks, parallel)
● Task(2.1) ⎿ Done [Token: 3,400, Time: 15min]
● Task(2.2) ⎿ Done [Token: 3,300, Time: 14min]
● Task(2.3) ⎿ Done [Token: 3,200, Time: 16min]
Batch complete: 16 minutes, 9,900 tokens

## Batch 3: Integration (3 tasks, parallel)
● Task(3.1) ⎿ Done [Token: 3,100, Time: 13min]
● Task(3.2) ⎿ Done [Token: 3,000, Time: 14min]
● Task(3.3) ⎿ Done [Token: 900, Time: 8min]
Batch complete: 14 minutes, 7,000 tokens

## Final Integration
✅ All 12 tasks completed
✅ 287 tests passing
✅ All acceptance criteria met
✅ No regressions detected

## Statistics
📊 Total tokens: 26,100 (avg 2,175 per task)
⏱️ Total time: 43 minutes
💰 vs Traditional: 156,000 tokens, 180 minutes
📈 Efficiency: 83% token saved, 76% time saved
```
