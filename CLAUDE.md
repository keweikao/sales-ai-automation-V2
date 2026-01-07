# Sales AI Automation V2 - Claude Code 開發指南

> 此文件會在每次 Claude Code 啟動時自動載入。

## 專案概述

這是一個 **Sales AI Automation** 系統，透過多個 AI Agent 分析銷售對話，提供即時教練建議。

## 快速上手

### 首次使用
```
/context    # 載入完整專案上下文
```

### 常用指令
| 指令 | 用途 |
|------|------|
| `/context` | 載入專案架構和開發指南 |
| `/mcp` | 查看 MCP 工具配置和整合狀態 |
| `/implement <任務>` | 根據 spec 實施功能 |

## 關鍵文件位置

| 類型 | 路徑 |
|------|------|
| 專案上下文 | `.conductor/PROJECT_CONTEXT.md` |
| 開發指南 | `DEVELOPMENT_GUIDELINES.md` |
| MCP 整合 | `specs/001-sales-ai-automation/integration-mcp/` |
| Agent 設計 | `analysis-service/src/agents/` |

## Agent 架構

```
Agent 1: Context Analyzer     - 上下文分析
Agent 2: Buyer Perspective    - 買家視角分析
Agent 3: Seller/Coach         - 銷售教練建議
Agent 4: Summary Generator    - 摘要生成
Agent 5: Sales Coach          - 即時教練
Agent 6: CRM Extractor        - CRM 欄位提取
Agent 8: Conversational       - Slack 對話介面
Agent 9: MCP Integration      - 工具整合層 (開發中)
```

## 開發規範

- **回應語言**：繁體中文
- **Commit 格式**：`feat:`, `fix:`, `docs:`, `refactor:`
- **代碼註解**：英文
- **測試要求**：新功能需有對應測試

## MCP 整合狀態

目前進度：**Phase 1 已完成**

下一步：執行 Phase 2 (Tool Infrastructure Setup)
- 建立 `tools/` 目錄結構
- 實作第一個工具 `firestore.query`

詳見：`specs/001-sales-ai-automation/integration-mcp/IMPLEMENTATION_GUIDE.md`

## Subagent 使用建議

在開發過程中，可使用以下 subagent 提高效率：

| Subagent | 用途 | 使用時機 |
|----------|------|----------|
| `Explore` | 探索代碼庫 | 需要了解架構、找文件時 |
| `Plan` | 設計實施計劃 | 複雜功能實作前 |
| `claude-code-guide` | Claude Code 使用指南 | 需要了解 Claude Code 功能時 |

---

*提示：使用 `/context` 可獲得更詳細的專案資訊*
