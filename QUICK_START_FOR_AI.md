# Quick Start for AI

> 此文件專為 AI 語言模型設計，幫助快速了解專案上下文。

## 必讀文件 (依優先順序)

| 優先 | 文件 | 說明 |
|------|------|------|
| 1 | [PROJECT_CONTEXT.md](.conductor/PROJECT_CONTEXT.md) | 專案概述、架構圖、技術棧 |
| 2 | [AI_ARCHITECTURE_ANALYSIS.md](AI_ARCHITECTURE_ANALYSIS.md) | 多 Agent 架構詳細分析 |
| 3 | [DEVELOPMENT_GUIDELINES.md](DEVELOPMENT_GUIDELINES.md) | 強制性開發規範 |

## 多 Agent 架構

本專案核心為多 Agent 銷售對話分析系統：

| Agent | 角色 | Prompt 位置 |
|-------|------|-------------|
| Agent 1 | Context Analyzer (會議背景分析師) | `modules/03-sales-conversation/meddic/agents/prompts/agent1-context.md` |
| Agent 2 | Buyer Analyzer (客戶洞察分析師) | `modules/03-sales-conversation/meddic/agents/prompts/agent2-buyer.md` |
| Agent 3 | Seller Coach (業務教練) | `modules/03-sales-conversation/meddic/agents/prompts/agent3-seller.md` |
| Agent 4 | Summary Generator (跟進摘要專家) | `modules/03-sales-conversation/meddic/agents/prompts/agent4-summary.md` |
| Agent 6 | CRM Extractor (Salesforce 欄位擷取) | `modules/03-sales-conversation/meddic/agents/prompts/agent6-crm-extractor.md` |

**Agent 程式碼**：`modules/03-sales-conversation/meddic/agents/`
**Orchestrator**：`modules/03-sales-conversation/transcript_analyzer/orchestrator.py`

## 編碼規範

- 回應語言：**繁體中文**
- Commit 格式：`feat:`, `fix:`, `docs:`, `refactor:`
- Agent Prompt 使用 Markdown 格式

## 開發記錄要求

每次開發 session 結束前，**必須** 更新 `DEVELOPMENT_LOG.md`。
詳見 [DEVELOPMENT_GUIDELINES.md](DEVELOPMENT_GUIDELINES.md)

---

*最後更新：2026-01-08*
