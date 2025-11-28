# Transcription Service Tests

- 範圍：分段/VAD/說話人分離、平行處理、品質檢查與持久化流程。
- 執行：`PYTHONPATH=src/transcription pytest src/transcription/tests`。
- 依賴：部分測試需模型/音訊樣本，Large 音檔在 `.gitignore` 下；請確認必要的環境變數或 mocks 已設定。***
