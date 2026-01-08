# Sales AI Automation V2 - Project Context

> 🤖 此文檔由 `.conductor/generate_context.py` 自動生成
> 最後更新：2026-01-08 13:33

## 專案概述

**Sales AI Automation** 是 iCHEF 銷售團隊的自動化銷售通話分析系統。
業務人員透過 Slack 上傳通話錄音，系統自動轉錄並使用多 Agent 架構分析通話內容，
最後產生客戶摘要報告。

- **程式碼行數**：~33,192 行 Python
- **服務數量**：5 個 Cloud Run 服務

## 技術架構

```
┌─────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Slack App  │───▶│ Transcription    │───▶│ Analysis Service │
│  (上傳入口)  │    │ Service (轉錄)    │    │ (多Agent分析)     │
└─────────────┘    └──────────────────┘    └──────────────────┘
                                                    │
                   ┌──────────────────┐             ▼
                   │  Web Service     │◀───  Firestore (資料庫)
                   │  (客戶摘要頁面)   │
                   └──────────────────┘
```

## 多 Agent 架構

| Agent | 檔案 | Prompt | 說明 |
|-------|------|--------|------|

## 執行流程 (orchestrator.py)

1. **Phase 1**：Agent 1 + Agent 2 並行執行
2. **Phase 2**：Agent 2 品質檢查迴圈（最多 2 次 refinement）
3. **Phase 3**：競爭對手偵測（條件式）
4. **Phase 4**：Agent 3（綜合前置 Agent 資料）
5. **Phase 5**：Agent 4（產生客戶摘要）

## 資料結構 (Firestore)

```typescript
cases/{caseId} = {
  caseId, customerName, status,
  transcription: { text, segments[] },
  analysis: {
    agents: { agent1, agent2, agent3, agent4 },
    customerSummary: { markdown }
  },
  notification: { slackChannelId, slackThreadTs }
}
```

## 技術棧

| 類別 | 技術 |
|-----|------|
| 語言 | Python 3.10+ |
| 框架 | Flask, Slack Bolt |
| AI | Gemini 2.5 Flash/Pro |
| 資料庫 | Google Firestore |
| 部署 | Google Cloud Run |

## 關鍵檔案

- `modules/03-sales-conversation/transcript_analyzer/orchestrator.py`
- `api-gateway/main.py`
- `web-service/src/main.py`
- `api-gateway/requirements.txt`
- `tools/code_intelligence/requirements.txt`
- `web-service/requirements.txt`
- `web-service/Dockerfile`

## 編碼規範

- 回應語言：**繁體中文**
- Commit 格式：`feat:`, `fix:`, `docs:`
- Agent Prompt 使用 Markdown 格式

---

*執行 `python .conductor/generate_context.py` 重新生成此文檔*
