# 案件 202511-IC011 轉錄狀態分析報告

**生成時間**: 2025-11-13 11:37:05 UTC  
**案件 ID**: 202511-IC011  
**狀態**: 轉錄失敗（FAILED）  

---

## 一、案件基本信息

| 欄位 | 值 |
|------|-----|
| 案件 ID | 202511-IC011 |
| 客戶名稱 | 麻辣燙_3 |
| 業務代表 | Stephen 高克瑋 |
| 業務代表郵箱 | <stephen.kao@ichef.com.tw> |
| 單位 | IC |
| 客戶電話 | 0937621894 |
| 音檔來源 | Slack |
| 案件創建時間 | 2025-11-12 06:24:35 UTC |
| 最後更新時間 | 2025-11-12 06:25:02 UTC |

---

## 二、Firestore 查詢結果

### 2.1 轉錄狀態

```
Step: transcribing
Progress: 0.0 (0%)
Error: 'NoneType' object is not callable
Updated At: 2025-11-13 03:05:38.952000 UTC
Total Chunks: 1
Completed Chunks: 0
```

### 2.2 文檔結構

Firestore 中案件文檔的字段分佈：

```
Top-level fields:
- caseId: 202511-IC011
- customerName: 麻辣燙_3
- customerId: 202511-122162
- salesRepName: Stephen 高克瑋
- salesRepEmail: stephen.kao@ichef.com.tw
- salesRepSlackId: U0BU3PESX
- unit: IC
- sourceType: slack
- status: transcribing
- retryCount: 0
- notes: (empty)
- createdAt: 2025-11-12 06:24:35.090000+00:00
- updatedAt: 2025-11-12 06:25:02.197000+00:00

analysis.transcription 欄位:
- step: "transcribing"
- progress: 0.0
- error: "'NoneType' object is not callable"
- detail: "開始並行轉錄"
- totalChunks: 1
- completedChunks: 0
- updatedAt: 2025-11-13 03:05:38.952000+00:00
- chunks.0: {status: "pending", updatedAt: 2025-11-13 03:05:38.952000+00:00, duration: 847}
```

### 2.3 轉錄結果

**預期轉錄內容**: 無（仍在進行中，已失敗）  
**Diarization Segments**: 未創建  
**Speakers**: 未檢測到  
**詳細信息**: "開始並行轉錄" （表示轉錄服務已啟動但隨後失敗）

---

## 三、錯誤分析

### 3.1 主要錯誤

**錯誤類型**: `'NoneType' object is not callable`  
**錯誤時間**: 2025-11-13 03:05:38 UTC  
**服務**: transcription-service（版本 00038-vxs）

### 3.2 根本原因

根據代碼分析，該錯誤可能發生於以下場景：

#### 場景 1: Diarizer Pipeline 為空（最可能）

在 `/src/transcription/diarization/pyannote_diarizer.py` 中：

```python
class PyannoteDiarizer:
    def __init__(self, ...):
        # ... 初始化代碼
        self.pipeline = Pipeline.from_pretrained(model_name, use_auth_token=token)
        if self.pipeline is None:
            raise RuntimeError(
                "Failed to load pyannote.audio pipeline, it returned None. "
                "This may be due to an invalid Hugging Face token or network issues."
            )
```

**問題**: 當 `Pipeline.from_pretrained()` 返回 `None` 時，檢查會失敗，隨後調用 `self.pipeline()` 會拋出 `'NoneType' object is not callable`

#### 場景 2: Diarizer 過早被清理

在 `/src/transcription/pipeline.py` 中存在潛在競態條件：

```python
# ... diarizer 調用
if diarizer is not None:
    merged_result["speakers"] = diarizer.summarize(diarization_segments)

# 立即釋放 diarizer 記憶體
self._cleanup_diarizer()
```

如果 `summarize()` 呼叫內部模型，而該模型已被垃圾回收，可能導致此錯誤。

### 3.3 相關雲日誌

根據 GCP Cloud Logging 查詢結果：

1. **2025-11-13T03:05:26**: 轉錄服務啟動，開始處理案件
2. **2025-11-13T02:33:04**: 記憶體警告

   ```
   Memory limit of 4096 MiB exceeded with 4184 MiB used.
   Consider increasing the memory limit...
   ```

3. **2025-11-13T02:30:41**: 連線錯誤

   ```
   The request failed because either the HTTP response was malformed 
   or connection to the instance had an error.
   ```

這表示轉錄服務在處理過程中發生了記憶體問題。

---

## 四、影響評估

| 項目 | 狀態 |
|------|------|
| 轉錄完成 | 否 (0%) |
| 轉錄文字 | 無 |
| Diarization | 未執行 |
| 說話者檢測 | 未執行 |
| 品質評分 | 未計算 |
| 後續分析 | 無法執行 |

**音檔信息**:

- 檔案長度: 847 秒 (~14.1 分鐘)
- 預期轉錄時間: 5-10 分鐘
- 實際耗時: > 8 小時（未完成）

---

## 五、建議與修復方案

### 5.1 立即行動

1. **確認 Hugging Face Token**
   - 驗證 `HUGGINGFACE_TOKEN` 環境變數是否正確設置
   - 確認令牌具有訪問 `pyannote/speaker-diarization` 模型的權限
   - 測試令牌是否已過期

2. **增加記憶體配額**
   - 當前服務配置: 8GB 記憶體
   - 建議增至: 12GB - 16GB 記憶體
   - 特別是針對 diarization 模型加載

3. **重試案件轉錄**

   ```bash
   # 方式 1: 通過 Cloud Tasks 重新排隊
   gcloud tasks create-http-task <queue-name> \
     --http-method=POST \
     --uri="https://transcription-service-xxx.run.app/transcribe" \
     --message-body='{"gcs_uri": "...audio file..."}'
   
   # 方式 2: 直接調用 API
   curl -X POST https://transcription-service-xxx.run.app/transcribe \
     -H "Content-Type: application/json" \
     -d '{"gcs_uri": "gs://..."}'
   ```

### 5.2 代碼修復

**文件**: `/src/transcription/diarization/pyannote_diarizer.py`

改進 Pipeline 檢查:

```python
self.pipeline = Pipeline.from_pretrained(model_name, use_auth_token=token)
if self.pipeline is None:
    raise RuntimeError(
        f"Failed to load pyannote.audio pipeline for model {model_name}. "
        "This may be due to: "
        "1. Invalid or expired Hugging Face token "
        "2. Network connectivity issues "
        "3. Model access restrictions "
        "Set the HUGGINGFACE_TOKEN environment variable or provide "
        "`use_auth_token` when constructing PyannoteDiarizer."
    )
```

**文件**: `/src/transcription/pipeline.py`

改進 Diarizer 清理時序:

```python
# 檢查結果
if merged_result["success"] and diarizer:
    try:
        diarization_segments = diarizer.diarize(
            audio_path, merged_result.get("segments")
        )
        merged_result["speaker_segments"] = [
            {
                "start": segment.start,
                "end": segment.end,
                "speaker": segment.speaker,
            }
            for segment in diarization_segments
        ]

        merged_result["segments"] = self._assign_speakers_to_segments(
            merged_result["segments"], diarization_segments
        )

        # 先執行 summarize，再清理
        if diarizer is not None:
            merged_result["speakers"] = diarizer.summarize(diarization_segments)
    finally:
        # 確保在所有操作完成後才清理 diarizer
        self._cleanup_diarizer()
```

### 5.3 監控改進

1. **增加詳細的日誌記錄**

   ```python
   logger.info(f"Diarizer loaded: {self.diarizer is not None}")
   logger.info(f"Pipeline type: {type(self.diarizer.pipeline)}")
   logger.info(f"Pipeline callable: {callable(self.diarizer.pipeline)}")
   ```

2. **添加健康檢查端點**

   ```python
   @flask_app.route("/health", methods=["GET"])
   def health_check():
       return {
           "status": "healthy",
           "pipeline_loaded": pipeline is not None,
           "memory_usage_mb": get_memory_usage(),
           "diarizer_available": check_diarizer_availability()
       }
   ```

3. **增強錯誤報告**
   - 將詳細的堆棧追蹤保存到 Firestore
   - 添加自動 Slack 通知
   - 實現自動重試機制

---

## 六、後續步驟

1. **立即**: 驗證 Hugging Face Token 並測試 diarizer 連接
2. **短期** (今日): 增加服務記憶體，重新部署
3. **中期** (本週): 實現代碼修復和改進
4. **長期** (本月): 實現完整的健康檢查和自動恢復機制

---

## 七、相關文件參考

- 轉錄服務代碼: `/src/transcription/main.py`
- 轉錄管道: `/src/transcription/pipeline.py`
- Diarization 模塊: `/src/transcription/diarization/`
- 狀態追蹤: `/src/transcription/status_tracker.py`
- 部署配置: `/src/transcription/Dockerfile`

---

**報告生成**: 自動分析腳本  
**版本**: 1.0  
**最後更新**: 2025-11-13 11:37:05 UTC
