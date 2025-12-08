# 轉錄服務成本分析報告

## 📊 使用情境
- **音檔數量**: 每月 300 個
- **音檔長度**: 每個 40-60 分鐘（平均 50 分鐘）
- **總轉錄時長**: 300 × 50 = **15,000 分鐘/月**
- **即時性需求**: ❌ 不需要即時轉錄（可接受 24 小時內完成）

---

## 💰 成本比較總覽

| 方案 | 每分鐘成本 | 月成本 (15,000 分鐘) | 年成本 | 推薦度 |
|------|-----------|---------------------|--------|--------|
| **Google STT Batch API** | $0.003 | **$45** | **$540** | ⭐⭐⭐⭐⭐ |
| OpenAI Whisper API | $0.006 | $90 | $1,080 | ⭐⭐⭐ |
| Gemini 1.5 Flash | $0.12 | $1,800 | $21,600 | ⭐ |
| Gemini 2.5 Flash (估算) | ~$0.15-0.20 | $2,250-3,000 | $27,000-36,000 | ⭐ |

---

## 🏆 最佳方案：Google Speech-to-Text Batch API

### 為什麼選擇 STT Batch API？

#### 1. **成本最低** 💵
- **每分鐘 $0.003**（OpenAI Whisper 的一半）
- **月成本僅 $45**（vs Whisper 的 $90）
- **年省 $540**（vs Whisper）

#### 2. **專為批次處理設計** ⚡
- 24 小時內交付結果
- 完美符合您的非即時需求
- 自動處理大量音檔

#### 3. **功能完整** ✅
- 支援繁體中文（台灣）
- Speaker Diarization（說話者分離）
- 高準確度
- 自動標點符號

#### 4. **穩定可靠** 🛡️
- Google Cloud 企業級 SLA
- 99.9% 可用性保證
- 成熟的 API

---

## 📋 詳細成本分析

### 方案 1: Google Speech-to-Text Batch API（推薦）

**定價結構**:
- **Dynamic Batch Recognition**: $0.003/分鐘
- 24 小時內交付
- 比標準 API 便宜 75%

**月成本計算**:
```
15,000 分鐘 × $0.003 = $45/月
```

**年成本**: $540

**優點**:
- ✅ 成本最低
- ✅ 專為批次處理優化
- ✅ 支援 Speaker Diarization
- ✅ 繁體中文支援優秀
- ✅ 企業級穩定性

**缺點**:
- ⚠️ 需要 24 小時處理時間（但您不需要即時）

---

### 方案 2: OpenAI Whisper API

**定價**:
- **$0.006/分鐘**

**月成本計算**:
```
15,000 分鐘 × $0.006 = $90/月
```

**年成本**: $1,080

**優點**:
- ✅ 準確度高
- ✅ 支援多語言
- ✅ 簡單易用
- ✅ 可選 Speaker Diarization（GPT-4o Transcribe）

**缺點**:
- ❌ 成本是 Google STT Batch 的 2 倍
- ❌ 25 MB 檔案大小限制
- ⚠️ 繁體中文準確度可能不如 Google STT

---

### 方案 3: Gemini 1.5 Flash

**定價**:
- **$0.12/分鐘** 音訊輸入

**月成本計算**:
```
15,000 分鐘 × $0.12 = $1,800/月
```

**年成本**: $21,600

**優點**:
- ✅ 可以同時做轉錄和分析
- ✅ 支援多模態

**缺點**:
- ❌ 成本極高（是 STT Batch 的 40 倍）
- ❌ 不適合純轉錄任務
- ❌ 主要用於音訊理解，不是轉錄

---

### 方案 4: Gemini 2.5 Flash

**定價** (估算):
- **音訊輸入**: ~$1.00-3.00/百萬 tokens
- 假設 1 分鐘音訊 ≈ 10,000 tokens
- **估算**: ~$0.15-0.20/分鐘

**月成本計算** (保守估計):
```
15,000 分鐘 × $0.15 = $2,250/月
```

**年成本**: $27,000

**優點**:
- ✅ 最新模型
- ✅ 可能有更好的理解能力

**缺點**:
- ❌ 成本極高（是 STT Batch 的 50 倍）
- ❌ 仍在 Preview 階段
- ❌ 不適合純轉錄任務
- ⚠️ 定價可能變動

---

## 🎯 成本節省建議

### 使用 Google STT Batch API 的節省

| 對比方案 | 月節省 | 年節省 |
|---------|--------|--------|
| vs OpenAI Whisper | $45 | $540 |
| vs Gemini 1.5 Flash | $1,755 | $21,060 |
| vs Gemini 2.5 Flash | $2,205 | $26,460 |

---

## 🔧 實作狀態檢查

根據您的程式碼，我發現：

### 目前支援的轉錄引擎

**1. Faster-Whisper (本地)**
- 檔案: `src/transcription/pipeline.py`
- 環境變數: `TRANSCRIPTION_ENGINE=whisper`
- 成本: 僅 Cloud Run 運算成本
- 問題: 需要 GPU，Cloud Run 成本高

**2. Gemini API**
- 檔案: `src/transcription/pipeline.py`
- 環境變數: `TRANSCRIPTION_ENGINE=gemini`
- 成本: 高（見上述分析）

**3. Batch Service (部分實作)**
- 檔案: `src/transcription/batch_service.py`
- 狀態: ⚠️ 程式碼存在但未完全整合

---

## 📝 建議實作計畫

### 階段 1: 整合 Google STT Batch API

**需要做的事**:
1. 完成 `batch_service.py` 的實作
2. 新增環境變數 `TRANSCRIPTION_ENGINE=stt_batch`
3. 實作批次提交邏輯
4. 實作結果輪詢機制

**預估工作量**: 4-6 小時

### 階段 2: 測試與驗證

**測試項目**:
1. 上傳音檔到 GCS
2. 提交 Batch 轉錄請求
3. 輪詢結果（24 小時內）
4. 驗證準確度
5. 驗證 Speaker Diarization

**預估工作量**: 2-3 小時

### 階段 3: 部署與監控

**部署步驟**:
1. 更新環境變數
2. 部署到 Cloud Run
3. 設定監控和告警
4. 記錄成本

**預估工作量**: 1-2 小時

---

## 💡 額外優化建議

### 1. 使用 GCS 生命週期管理
- 自動刪除 30 天前的音檔
- 節省儲存成本

### 2. 批次提交優化
- 累積 10-20 個音檔後一次提交
- 減少 API 調用次數

### 3. 錯誤重試機制
- 自動重試失敗的轉錄
- 記錄失敗原因

---

## 📊 成本預測（使用 STT Batch API）

### 月成本明細

| 項目 | 成本 |
|------|------|
| STT Batch API (15,000 分鐘) | $45.00 |
| GCS 儲存 (300 個音檔 × 50 MB) | ~$0.38 |
| Cloud Run (轉錄服務) | ~$5.00 |
| Firestore (讀寫) | ~$2.00 |
| **總計** | **~$52.38/月** |

### 年成本預測

```
$52.38 × 12 = $628.56/年
```

---

## ✅ 結論與建議

### 最佳方案：Google Speech-to-Text Batch API

**理由**:
1. **成本最低**: 每月僅 $45（vs Whisper $90）
2. **完美符合需求**: 24 小時交付，您不需要即時
3. **功能完整**: Speaker Diarization、繁體中文支援
4. **穩定可靠**: Google Cloud 企業級服務

### 立即行動

1. ✅ 確認使用 Google STT Batch API
2. ⏭️ 完成 `batch_service.py` 實作
3. ⏭️ 測試並驗證準確度
4. ⏭️ 部署到生產環境

### 預期效益

- **年省 $540**（vs OpenAI Whisper）
- **年省 $21,060**（vs Gemini 1.5 Flash）
- **處理時間**: 24 小時內（完全可接受）
- **準確度**: 企業級（Google STT）

---

## 🔗 相關文件

- [Google STT Batch API 文件](https://cloud.google.com/speech-to-text/docs/batch-recognize)
- [Google STT 定價](https://cloud.google.com/speech-to-text/pricing)
- [OpenAI Whisper API 文件](https://platform.openai.com/docs/guides/speech-to-text)
