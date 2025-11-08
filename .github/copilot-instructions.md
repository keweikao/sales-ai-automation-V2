# Speckit 專案 - GitHub Copilot 指示

## 專案特性

本專案採用 **Anthropic MCP Code Execution** 模式優化 token 使用。

## 核心規則

1. **禁止直接讀取文件**
   - 不要讀取 `.specify/memory/constitution.md`
   - 不要讀取 `.specify/specs/*/spec.md`
   - 不要讀取 `.specify/specs/*/plan.md`
   - 不要讀取 `.specify/specs/*/tasks.md`

2. **必須使用 API**
   - 使用 `.specify/mcp-server/servers/` 下的 TypeScript API
   - 或使用 `.specify/llm` CLI 工具

3. **參考文件**
   - 完整指南：`.specify/LLM-USAGE-GUIDE.md`

## 常見任務範例

### 取得任務資訊

```typescript
import * as tasks from './.specify/mcp-server/servers/tasks/index.js';
const task = await tasks.getTaskById({ taskId: '3.2', includeContext: true });
```

### 查看 Constitution

```typescript
import * as constitution from './.specify/mcp-server/servers/constitution/index.js';
const summary = await constitution.getConstitutionSummary();
```

### 搜尋資訊

```typescript
const result = await constitution.searchConstitution({ query: 'code quality' });
```

## Token 目標

- 單次互動: < 1,500 tokens
- 完整任務實作: < 2,000 tokens

如果超過，重新檢查是否直接讀取了文件。
