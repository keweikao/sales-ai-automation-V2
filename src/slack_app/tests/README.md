# Slack App Tests

- 範圍：Slack Bolt handlers、內部通知與流程驗證（mock Firestore/Cloud Tasks）。
- 執行：`PYTHONPATH=src/slack_app pytest src/slack_app/tests`。
- 依賴：部分測試使用 e2e mocks/fixtures，請確保環境變數在測試設定檔中已提供或被 mock。***
