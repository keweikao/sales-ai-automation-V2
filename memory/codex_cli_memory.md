# Codex CLI 專用 Memory

> 此檔專供 Codex CLI 在進入專案時快速讀取，補足我本身沒有持久化記憶的限制。

## 核心啟動文件

1. **`QUICK_START_FOR_AI.md`**  
   - 內含完整的開發前置檢查清單、MCP/Subagent SOP、Token 節省策略與自我檢查表。  
   - 任何任務開始前務必閱讀「✅ 開發前置檢查清單」段落，並按照自我檢查表逐項確認。  
   - Markdown 變更必須通過 `markdownlint-cli2`（自檢表已納入此要求）。

2. **`DEVELOPMENT_LOG.md`**  
   - 記錄所有 Session 的詳細脈絡、決策、剩餘待辦。  
   - 最新 Session（截至 2025-11-10 的 Session 21）包含：  
     - Checklist 整併、Agent 5 修補、Slack thread sync  
     - Diarization 部署準備（需建立 `huggingface-token` secret）  
     - markdownlint 強制要求  
   - 開始開發前務必閱讀最後一次 Session 的「Next Session Preparation」。

## 使用方式

- 啟動 Codex CLI 後，先閱讀本檔，再依序打開 Quick Start 及 Development Log。
- 若本檔需要更新（例如新增注意事項或手動記憶），請直接修改此檔並紀錄於 `DEVELOPMENT_LOG.md`。  
