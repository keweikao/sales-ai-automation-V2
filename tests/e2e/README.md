# 端到端（E2E）測試框架

此目錄包含完整的端到端測試，用於驗證整個「Slack 上傳音檔 → Gemini 轉錄 → Agent 1-7 分析 → 結果回傳 Slack」工作流程。

## 測試優先級

### P0（必須通過）
- ✅ 完整工作流程測試
- ✅ Slack 檔案上傳處理
- ✅ Gemini 轉錄流程
- ✅ Agent 1-7 執行順序
- ✅ 通知發送與 fallback

### P1（重要但非阻塞）
- ✅ Slack 事件處理
- ✅ 錯誤恢復機制
- ✅ Modal 互動流程
- ⚠️ 負載測試

## 目錄結構

```
tests/e2e/
├── README.md                    # 本檔案
├── conftest.py                  # Pytest 配置和共用 fixtures
├── mocks/                       # Mock 物件和工具
│   ├── __init__.py
│   ├── slack_mock.py           # Mock Slack API
│   ├── firestore_mock.py       # Mock Firestore
│   ├── gemini_mock.py          # Mock Gemini API
│   └── cloud_tasks_mock.py     # Mock Cloud Tasks
├── fixtures/                    # 測試資料
│   ├── audio_files/            # 測試音檔
│   ├── transcripts/            # 預期轉錄結果
│   └── agent_outputs/          # 預期 Agent 輸出
├── test_full_workflow.py        # P0: 完整工作流程測試
├── test_slack_events.py         # P1: Slack 事件測試
├── test_error_recovery.py       # P1: 錯誤恢復測試
└── test_notification_fallback.py # P1: 通知 fallback 測試
```

## 執行測試

### 執行所有 E2E 測試
```bash
pytest tests/e2e/ -v
```

### 執行 P0 測試
```bash
pytest tests/e2e/test_full_workflow.py -v -m p0
```

### 執行 P1 測試
```bash
pytest tests/e2e/ -v -m p1
```

### 執行特定測試
```bash
pytest tests/e2e/test_full_workflow.py::test_upload_to_notification -v
```

## Mock 策略

### 外部服務 Mock
- **Slack API**: 使用 `unittest.mock` 模擬所有 Slack API 呼叫
- **Firestore**: 使用內存模擬或 Firestore Emulator
- **Gemini API**: 使用預錄的轉錄結果
- **Cloud Tasks**: 使用同步執行模擬非同步任務

### 真實服務（可選）
可通過環境變數切換使用真實服務進行整合測試：
- `E2E_USE_REAL_FIRESTORE=true`: 使用真實 Firestore
- `E2E_USE_REAL_SLACK=true`: 使用真實 Slack（需 test workspace）
- `E2E_USE_REAL_GEMINI=true`: 使用真實 Gemini API

## 測試資料

### 音檔測試資料
位於 `fixtures/audio_files/`:
- `sample_meeting_30s.m4a` - 短會議錄音（30 秒）
- `sample_meeting_2min.mp3` - 中等會議錄音（2 分鐘）
- `sample_invalid.txt` - 無效檔案類型
- `sample_oversized.mp3` - 超過大小限制的檔案

### 預期輸出
位於 `fixtures/agent_outputs/`:
- 每個測試場景的預期 Agent 1-7 輸出
- 用於驗證 Agent 執行結果的正確性

## 斷言策略

### 關鍵斷言點
1. **Slack 上傳階段**
   - Firestore 防重複記錄建立
   - Modal 正確顯示
   - 檔案驗證通過

2. **轉錄階段**
   - Cloud Task 成功建立
   - Gemini API 正確呼叫
   - 轉錄結果正確儲存到 Firestore

3. **分析階段**
   - Agent 1-7 按正確順序執行
   - Agent 6 依賴 Agent 1-5 結果
   - 結果正確持久化

4. **通知階段**
   - Agent 6 通知先於 Agent 7
   - 通知發送到正確的 thread
   - Fallback 機制正確觸發

## 效能指標

### 預期執行時間
- 單一測試: < 5 秒（使用 mock）
- 完整測試套件: < 30 秒
- 整合測試（真實服務）: < 5 分鐘

### 測試覆蓋率目標
- P0 功能: 100% 覆蓋
- P1 功能: 80% 覆蓋
- 錯誤路徑: 70% 覆蓋

## CI/CD 整合

E2E 測試應在以下情況執行：
- Pull Request 創建時（P0 測試）
- Merge 到 main 前（P0 + P1 測試）
- 定期排程（每日，包含整合測試）

## 疑難排解

### 測試失敗常見原因
1. Mock 狀態未正確重置
2. 非同步操作未正確等待
3. Firestore 測試資料衝突
4. 環境變數未設定

### Debug 模式
```bash
pytest tests/e2e/ -v -s --log-cli-level=DEBUG
```

## 貢獻指南

新增測試時請遵循：
1. 使用描述性的測試名稱
2. 添加適當的 pytest mark（@pytest.mark.p0 或 @pytest.mark.p1）
3. 確保測試可獨立執行
4. 清理測試後狀態
5. 更新本 README
