# Analysis Service Tests

- 範圍：orchestrator、各 Agent（1-4）邏輯與 Firestore/Slack 通知流程。
- 執行：`PYTHONPATH=analysis-service/src pytest analysis-service/tests`（或 `make test-analysis`）。
- 資料：fixtures/samples 位於本目錄下，`tests/samples` 用於輸入樣本。
