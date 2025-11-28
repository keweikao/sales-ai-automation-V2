# Tests Overview

統一測試分層，快速找到對應套件：

- `tests/`（根目錄） — 共用單元/整合測試；`e2e/` 保存端到端流程（詳見 `tests/e2e/README.md`）。
- `analysis-service/tests/` — Orchestrator/分析服務測試。
- `src/slack_app/tests/` — Slack App 測試。
- `src/transcription/tests/` — 轉錄/分段/平行處理/品質檢查測試。
- `test-data/` — 測試音訊與支援資料（大型檔案依 `.gitignore` 管理）。

建議新增測試時遵循以上分層，並在對應資料夾內新增 README 說明測試範圍與執行方式。***
