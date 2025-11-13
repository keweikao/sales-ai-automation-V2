# Transcription Service 記憶體優化實施記錄

**日期**: 2025-11-12
**實施者**: Claude Code
**問題**: transcription-service 潛在的記憶體不足風險

## 問題分析

### 發現的問題

1. **配置不一致**:
   - Cloud Build 定義: 8Gi
   - 實際運行版本: 6Gi（手動調整導致）

2. **記憶體峰值風險**:
   - Whisper medium 模型: ~1.5Gi
   - Pyannote diarization: ~2-3Gi
   - 音檔處理緩衝: ~0.5-1Gi
   - **總計峰值**: 4-5.5Gi（在 6Gi 下很緊繃）

3. **並行處理風險**:
   - Cloud Tasks: `maxConcurrentDispatches=5`
   - Pipeline 內部: `MAX_WORKERS=3`
   - 理論上可同時處理 15 個音檔片段

## 實施的解決方案

### 方案 1: 配置調整（立即生效）✅

**執行時間**: 2025-11-12 01:30

1. **更新 Cloud Run 記憶體配置**:

```bash

gcloud run services update transcription-service \

  --region=asia-east1 \

  --memory=8Gi \

  --update-env-vars=MAX_WORKERS=2

```

- 新 revision: `transcription-service-00026-voc`
  - Memory: 6Gi → 8Gi ✓
  - MAX_WORKERS: 3 → 2 ✓

2. **降低 Cloud Tasks 並行度**:

```bash

gcloud tasks queues update transcription-queue \

  --location=asia-east1 \

  --max-concurrent-dispatches=3

```

- 並行度: 5 → 3 ✓
  - 理論最大並行: 15 → 6 個音檔片段

3. **成本影響**:
   - 增加: ~$1.2/月（8Gi vs 6Gi）
   - 可接受範圍內

### 方案 2: 程式碼優化（部署中）🔄

**修改檔案**: `src/transcription/pipeline.py`

**變更內容**:

1. **新增記憶體監控**:

```python

def _log_memory_usage(self, context: str = ""):

    """記錄記憶體使用情況"""

    import psutil

    memory = psutil.virtual_memory()

    process = psutil.Process()

    process_memory = process.memory_info().rss / 1024 / 1024 / 1024  # GB

    logger.info(

        f"Memory usage [{context}]: "

        f"System={memory.percent:.1f}%, "

        f"Process={process_memory:.2f}GB"

    )

```

2. **Diarization 模型 Lazy Loading**（已存在，加強監控）:

```python



def _get_diarizer(self):



    """Lazily instantiate the diarizer to reduce peak memory usage."""



    if not self.enable_diarization:



        return None







    if self.diarizer is None and not self.diarization_error:



        logger.info("Loading diarization model...")



        self._log_memory_usage("Before diarization model load")



        # ... 載入模型 ...



        self._log_memory_usage("After diarization model load")



```

3. **新增記憶體釋放機制**:

```python







def _cleanup_diarizer(self):







    """釋放 diarizer 記憶體"""







    if self.diarizer is not None:







        logger.info("Releasing diarization model from memory...")







        self._log_memory_usage("Before diarizer cleanup")















        del self.diarizer







        self.diarizer = None















        import gc







        gc.collect()















        self._log_memory_usage("After diarizer cleanup")







```

4. **在 process_audio 中自動清理**:

```python















# 套用說話者區分















diarizer = self._get_diarizer()















if merged_result["success"] and diarizer:















    # ... diarization 處理 ...































    # 立即釋放 diarizer 記憶體















    self._cleanup_diarizer()















```

**預期效果**:

- Diarization 完成後立即釋放 2-3Gi 記憶體
- 峰值記憶體使用降低約 40%
- 可在日誌中追蹤每個階段的記憶體使用

## 部署狀態

### Cloud Run 服務配置

**當前活躍版本**: `transcription-service-00026-voc`

| 配置項目 | 調整前 | 調整後 | 狀態 |
|---------|--------|--------|------|
| Memory | 6Gi | 8Gi | ✅ 已生效 |
| CPU | 2 cores | 2 cores | - |
| MAX_WORKERS | 3 | 2 | ✅ 已生效 |
| Concurrency | 1 | 1 | - |
| Timeout | 3600s | 3600s | - |

### Cloud Tasks 配置

**Queue**: `transcription-queue`

| 配置項目 | 調整前 | 調整後 | 狀態 |
|---------|--------|--------|------|
| maxConcurrentDispatches | 5 | 3 | ✅ 已生效 |
| maxDispatchesPerSecond | 2 | 2 | - |

### 程式碼部署

**Build ID**: 8ec5192a-e51a-4fb9-823c-b5d0d65718b6 ✅

| 項目 | 狀態 |
|------|------|
| pipeline.py 修改 | ✅ 完成 |
| Python 語法檢查 | ✅ 通過 |
| Cloud Build YAML 更新 | ✅ 完成（MAX_WORKERS=2） |
| Docker 建置 | ✅ 完成 |
| Cloud Run 部署 | ✅ 完成（revision-00030-jic） |
| 流量切換 | ✅ 100% 切換至新版本 |

## 預期成本影響

### 每月成本估算（假設 250 案件/月）

**調整前**:

- Memory: 6Gi × 2 instances × 8 hours/day × 30 days = $3.60/月
- CPU: 2 cores × 2 instances × 8 hours/day × 30 days = $3.84/月
- **總計**: ~$7.44/月

**調整後**:

- Memory: 8Gi × 2 instances × 8 hours/day × 30 days = $4.80/月
- CPU: 2 cores × 2 instances × 8 hours/day × 30 days = $3.84/月
- **總計**: ~$8.64/月

**增加**: $1.20/月（16% 增加）

### 性能影響

**吞吐量**:

- 調整前: 最多 5 個並行請求 × 3 workers = 15 並行片段
- 調整後: 最多 3 個並行請求 × 2 workers = 6 並行片段
- **降低**: 60%（但仍滿足當前需求，每天處理 10-20 個音檔綽綽有餘）

**處理時間**:

- 單檔案影響: 微小（workers 從 3→2，影響約 10-15%）
- 整體影響: 在低並行場景下幾乎無感

## 監控建議

### 立即設定（待執行）

1. **Cloud Monitoring 告警**:

```bash

# Memory 使用率 > 85%

gcloud monitoring policies create \

  --notification-channels=CHANNEL_ID \

  --display-name="Transcription Service High Memory" \

  --condition-display-name="Memory > 85%" \

  --condition-threshold-value=0.85 \

  --condition-threshold-duration=300s

```

2. **查看記憶體使用日誌**:

```bash



gcloud logging read 'resource.type="cloud_run_revision"



  resource.labels.service_name="transcription-service"



  textPayload=~"Memory usage"' \



  --limit=50 \



  --format="table(timestamp, textPayload)"



```

3. **監控 OOM 錯誤**:

```bash







gcloud logging read 'resource.type="cloud_run_revision"







  resource.labels.service_name="transcription-service"







  (severity>=ERROR OR textPayload=~"OOM" OR textPayload=~"MemoryError")' \







  --limit=50







```

### 長期監控指標

建議追蹤：

1. **Peak Memory Usage** - 每次轉錄的峰值記憶體
2. **Diarization Memory Delta** - 載入/釋放 diarization 模型前後的記憶體差異
3. **Processing Time** - 確保優化沒有顯著增加處理時間
4. **Error Rate** - 監控是否有新的錯誤類型

## 驗證計畫

### 短期驗證（1-2 天）

1. **上傳測試音檔**:
   - 短音檔（5 分鐘）
   - 中等音檔（20 分鐘）
   - 長音檔（45 分鐘）

2. **檢查日誌**:
   - 確認記憶體監控日誌正常輸出
   - 驗證 diarization 模型載入/釋放訊息
   - 檢查沒有 OOM 錯誤

3. **性能驗證**:
   - 處理時間沒有顯著增加（<20%）
   - 記憶體峰值保持在 6.5Gi 以下（8Gi 的 80%）

### 中期觀察（1-2 週）

1. **批量測試**:
   - 同時上傳 3-5 個音檔
   - 觀察並行處理效果
   - 驗證沒有積壓

2. **成本追蹤**:
   - 確認月成本增加在預期範圍內（$1-2）

3. **穩定性**:
   - 無 shutdown/OOM 事件
   - Error rate < 1%

## 回滾計畫

如果發現問題，可立即回滾：

```bash

# 方案 A: 回滾到之前的 revision

gcloud run services update-traffic transcription-service \

  --to-revisions=transcription-service-00013-d2j=100 \

  --region=asia-east1



# 方案 B: 調整參數

gcloud run services update transcription-service \

  --region=asia-east1 \

  --memory=6Gi \

  --update-env-vars=MAX_WORKERS=3



gcloud tasks queues update transcription-queue \

  --location=asia-east1 \

  --max-concurrent-dispatches=5

```

## 參考資料

- 原始調查報告: Subagent investigation (2025-11-12)
- Cloud Run 文件: <https://cloud.google.com/run/docs/configuring/memory-limits>
- 相關 Session: DEVELOPMENT_LOG.md Session 31+
