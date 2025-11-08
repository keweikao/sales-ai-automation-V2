# Speckit MCP 專案初始化

你現在進入一個使用 **MCP Code Execution** 模式的 Speckit 專案。

## 第一步：讀取指南

請立即閱讀 `.specify/LLM-USAGE-GUIDE.md` 並確認你理解：

1. MCP Code Execution 的核心概念
2. 禁止事項和必須事項
3. API 使用方式

## 強制規則

### ❌ 絕對禁止（違反將被立即糾正）

1. **禁止直接讀取以下文件**：
   - `.specify/memory/constitution.md`
   - `.specify/specs/*/spec.md`
   - `.specify/specs/*/plan.md`
   - `.specify/specs/*/tasks.md`

2. **禁止使用以下方式**：
   - `fs.readFileSync()`
   - `fs.readFile()`
   - `fs.promises.readFile()`
   - 任何直接讀取上述文件的方式

3. **禁止要求使用者**：
   - 「請提供 spec.md 的內容」
   - 「請把 tasks.md 貼給我」
   - 任何要求完整文件內容的請求

### ✅ 必須使用

**只能透過以下兩種方式存取資訊：**

#### 方式 1：TypeScript API

```typescript
// Constitution
import * as constitution from './.specify/mcp-server/servers/constitution/index.js';
const summary = await constitution.getConstitutionSummary();
const search = await constitution.searchConstitution({ query: 'code quality' });

// Tasks
import * as tasks from './.specify/mcp-server/servers/tasks/index.js';
const task = await tasks.getTaskById({ taskId: '3.2', includeContext: true });
const nextTask = await tasks.getNextTask();
const allTasks = await tasks.getAllTasks();
```

#### 方式 2：CLI 工具

```bash
# Constitution
./.specify/llm constitution-summary
./.specify/llm constitution-search --query "code quality"

# Tasks
./.specify/llm task --id 3.2 --context
./.specify/llm next-task
./.specify/llm all-tasks
```

## Token 使用目標

你的每個回應必須控制在以下範圍內：

| 階段/操作 | Token 目標 | 說明 |
|----------|-----------|------|
| Constitution 階段 | < 500 tokens | 只載入摘要，不載入完整文件 |
| Specify 階段 | < 800 tokens | 只載入相關需求 |
| Plan 階段 | < 1,000 tokens | 只載入技術細節 |
| Implement 單一任務 | < 1,500 tokens | 包含任務資訊 + 相關上下文 |
| 完整 Implement 流程 | < 2,000 tokens | 包含相依檢查 + 實作 |

**重要**：在每次回應中，你必須：

1. 估計你使用的 token 數量
2. 如果超過目標，主動優化並重新生成回應
3. 在回應末尾註明：`[估計 token: XXX]`

## 常見情境快速參考

### 情境 1：使用者說「查看專案原則」

```typescript
import * as constitution from './.specify/mcp-server/servers/constitution/index.js';
const summary = await constitution.getConstitutionSummary();
console.log(summary.summary);
// 使用約 300 tokens
```

### 情境 2：使用者說「實作任務 3.2」

```typescript
import * as tasks from './.specify/mcp-server/servers/tasks/index.js';

const task = await tasks.getTaskById({
  taskId: '3.2',
  includeContext: true
});

console.log(`任務: ${task.title}`);
console.log(`描述: ${task.description}`);
console.log(`相關需求:`, task.relatedSpecSections);
console.log(`技術細節:`, task.relatedPlanSections);
console.log(`驗收標準:`, task.acceptanceCriteria);
console.log(`要修改的檔案:`, task.files);

// 現在開始實作...
// 使用約 1,200 tokens
```

### 情境 3：使用者說「搜尋關於資料庫的資訊」

```typescript
import * as constitution from './.specify/mcp-server/servers/constitution/index.js';

const result = await constitution.searchConstitution({
  query: '資料庫',
  maxResults: 3
});

console.log('找到以下相關章節:');
result.sections.forEach(section => {
  console.log(`\n## ${section.title}`);
  console.log(section.content);
});
// 使用約 600 tokens
```

### 情境 4：使用者說「下一個任務是什麼」

```typescript
import * as tasks from './.specify/mcp-server/servers/tasks/index.js';

const nextTask = await tasks.getNextTask();
console.log(`下一個任務: ${nextTask.id} - ${nextTask.title}`);
// 使用約 200 tokens
```

## 回應前自我檢查清單

**在你生成任何回應之前，務必完成以下檢查：**

- [ ] ✅ 我使用了 MCP API 或 CLI 工具
- [ ] ❌ 我沒有直接讀取 spec/plan/tasks/constitution 文件
- [ ] ❌ 我沒有使用 fs.readFile* 讀取上述文件
- [ ] ❌ 我沒有要求使用者提供完整文件內容
- [ ] 📊 我的回應 token 使用量在目標範圍內
- [ ] 🔍 我在回應末尾註明了估計的 token 數量

**如果任何一項檢查失敗，立即修正後再回應。**

## 驗證你的理解

現在請回答以下問題，證明你理解了規則：

1. 如果使用者要求「查看任務 3.2 的資訊」，你會使用什麼方式？
2. 如果你發現自己的回應超過 token 目標，你應該怎麼做？
3. 列出 3 個絕對禁止的操作。

完成驗證後，告訴我你已準備好開始工作。
