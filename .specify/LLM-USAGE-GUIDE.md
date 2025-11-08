# Speckit LLM 使用指南

## 🎯 核心原則

你現在擁有一套 MCP Code APIs 來存取 Speckit 文件。

**永遠不要直接讀取完整的 markdown 文件**。改用提供的程式碼 API。

### 為什麼？

傳統方式每次載入完整文件會消耗大量 tokens：

- constitution.md: 2,340 tokens
- spec.md: 5,670 tokens
- plan.md + tasks.md: 4,000 tokens
- **總計**: 12,000+ tokens

新方式透過 API 只載入需要的部分：

- Constitution 摘要: 300 tokens (87% ↓)
- 單一任務資訊: 1,200 tokens (90% ↓)
- 搜尋結果: 600 tokens (89% ↓)

## 📊 Token 節省對比

| 操作 | 傳統方式 | MCP API 方式 | 節省 |
|-----|---------|-------------|------|
| 讀取 Constitution | 2,340 tokens | 300 tokens | 87% |
| 取得任務資訊 | 12,000 tokens | 1,200 tokens | 90% |
| 搜尋 Spec | 5,670 tokens | 600 tokens | 89% |
| 完整 Implement 流程 | 15,000 tokens | 2,000 tokens | 87% |

## 🚀 使用方式

### 情境一：開始新功能（Constitution 階段）

**❌ 錯誤做法：**

```
請讀取 .specify/memory/constitution.md 的完整內容，
我要了解專案的開發原則。
```

**✅ 正確做法：**

```typescript
import * as constitution from './.specify/mcp-server/servers/constitution/index.js';

const summary = await constitution.getConstitutionSummary();
console.log(summary.summary);

// 只用 300 tokens 而非 2,340 tokens！
```

### 情境二：實作任務（Implement 階段）

**❌ 錯誤做法：**

```
請讀取 spec.md、plan.md 和 tasks.md 的完整內容，
找出任務 3.2 的資訊，然後協助我實作。
```

**✅ 正確做法：**

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

// 只用 1,200 tokens 而非 12,000 tokens！
```

### 情境三：搜尋特定資訊

**❌ 錯誤做法：**

```
請讀取所有文件並搜尋關於「資料庫架構」的資訊
```

**✅ 正確做法：**

```typescript
import * as constitution from './.specify/mcp-server/servers/constitution/index.js';

const result = await constitution.searchConstitution({
  query: '資料庫架構',
  maxResults: 3,
});

console.log('找到以下相關章節:');
result.sections.forEach((section) => {
  console.log(`\n## ${section.title}`);
  console.log(section.content);
});
```

## 🛠️ 命令列工具快速參考

```
./.specify/llm constitution-summary
./.specify/llm task --id 3.2 --context
./.specify/llm next-task
./.specify/llm constitution-search --query "code quality"
./.specify/llm all-tasks
./.specify/llm all-tasks --phase "Phase 1"
./.specify/llm stats
```

## 💡 最佳實踐

### 1. 漸進式載入

```typescript
const summary = await constitution.getConstitutionSummary();
if (needMoreDetail) {
  const result = await constitution.searchConstitution({ query: '特定主題' });
}
```

### 2. 精確查詢

```typescript
const result = await constitution.searchConstitution({
  query: 'error handling',
  maxResults: 2,
});
```

### 3. 上下文控制

```typescript
const task = await tasks.getTaskById({ taskId: '3.2', includeContext: false });
const taskWithContext = await tasks.getTaskById({
  taskId: '3.2',
  includeContext: true,
});
```

## 📝 完整工作流程範例

```typescript
import * as tasks from './.specify/mcp-server/servers/tasks/index.js';
import * as files from './.specify/mcp-server/servers/files/index.js';

async function implementTask() {
  const task = await tasks.getTaskById({ taskId: '3.2', includeContext: true });
  const deps = await tasks.getDependencies({ taskId: '3.2' });
  console.log(task.title, task.description, deps);
}

implementTask();
```

## ⚠️ 注意事項

### 禁止事項

- ❌ 直接讀取 spec/plan/tasks/constitution
- ❌ 要求使用者提供完整文件

### 必做事項

- ✅ 使用 MCP API 或 CLI
- ✅ 控制 token 使用
- ✅ 只載入需要的內容

如需更多資訊，請擴充 API 而非讀取整份文件。

## 📊 監控 Token 使用

```
./.specify/llm stats
```

## 🎯 成功標準

- Constitution 階段: < 500 tokens
- Specify 階段: < 800 tokens
- Plan 階段: < 1,000 tokens
- Implement 階段: < 1,500 tokens

## 🚀 開始使用

記住：**寫程式碼來查詢資訊，而不是載入完整文件**。祝開發順利！
