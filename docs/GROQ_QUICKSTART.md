# Groq Whisper 快速開始指南

> 5 分鐘內完成 Groq Whisper 整合與部署

---

## 🚀 快速部署 (3 步驟)

### Step 1: 設定 Groq API Key

```bash
# 1. 取得 Groq API Key
# 前往 https://console.groq.com/ 註冊並建立 API Key

# 2. 加入 Secret Manager
echo -n "YOUR_GROQ_API_KEY" | gcloud secrets create GROQ_API_KEY \
  --data-file=- \
  --project=sales-ai-automation-v2

# 3. 授權 Service Account
gcloud secrets add-iam-policy-binding GROQ_API_KEY \
  --member="serviceAccount:497329205771-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=sales-ai-automation-v2
```

### Step 2: 部署 Transcription Service

```bash
# 使用預配置的 Cloud Build
gcloud builds submit \
  --config cloudbuild.transcription-groq.yaml \
  --project=sales-ai-automation-v2
```

### Step 3: 測試

```bash
# 測試轉錄端點
curl -X POST https://transcription-service-497329205771.asia-east1.run.app/transcribe \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "TEST_001",
    "audio_uri": "gs://YOUR_BUCKET/test.mp3"
  }'
```

---

## 📊 預期結果

### 效能指標
- ⚡ **速度**: 228x realtime (~10 秒處理 37.5 分鐘音檔)
- 💰 **成本**: ~$7.50/月 (300 檔)
- 🎯 **準確度**: 95%+ (繁體中文)
- 💾 **記憶體**: 2Gi (vs Gemini 4Gi, Faster-Whisper 8Gi)

### 轉錄輸出範例

```json
{
  "success": true,
  "full_text": "您好我是 iCHEF 的業務代表...",
  "segments": [],
  "speakers": [],
  "audio_info": {
    "duration": 2250.5,
    "processing_time": 9.8,
    "num_chunks": 4,
    "model": "whisper-large-v3-turbo"
  }
}
```

**注意**: `segments` 和 `speakers` 為空，Agent 會從 `full_text` 推斷說話者。

---

## 🔍 驗證部署

### 1. 檢查 Cloud Run 服務

```bash
gcloud run services describe transcription-service \
  --region=asia-east1 \
  --project=sales-ai-automation-v2
```

預期輸出：
```
Environment Variables:
  TRANSCRIPTION_ENGINE: groq_whisper
  TRANSCRIPTION_LANGUAGE: zh
  ...
Secrets:
  GROQ_API_KEY: projects/.../secrets/GROQ_API_KEY/versions/latest
```

### 2. 檢查日誌

```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=transcription-service" \
  --limit 50 \
  --project=sales-ai-automation-v2
```

預期看到：
```
GroqWhisperPipeline initialized with model: whisper-large-v3-turbo
```

### 3. 測試完整流程

使用 Slack 發起 Demo：
1. 上傳音檔到 Slack
2. 填寫 Demo 表單
3. 等待轉錄完成 (應 < 30 秒)
4. 查看分析結果

---

## 🐛 常見問題

### Q1: 部署失敗 - "GROQ_API_KEY not found"

**A**: Secret Manager 設定問題

```bash
# 確認 secret 存在
gcloud secrets describe GROQ_API_KEY --project=sales-ai-automation-v2

# 確認權限
gcloud secrets get-iam-policy GROQ_API_KEY --project=sales-ai-automation-v2
```

### Q2: 轉錄速度慢

**A**: 檢查音檔大小和格式

```bash
# 查看音檔資訊
gsutil ls -l gs://YOUR_BUCKET/audio.mp3

# Groq 限制單一檔案 < 25MB
# 如果超過，pipeline 會自動分段
```

### Q3: Agent 分析結果不準確

**A**: 檢查轉錄文字品質

1. 查看 Firestore 中的 `transcript.full_text`
2. 確認文字清晰且完整
3. 如果音檔品質差，考慮使用 `whisper-large-v3` (較慢但更準確)

---

## 📈 監控與優化

### 成本監控

```bash
# 查看 Groq API 使用量
# 前往 https://console.groq.com/usage

# 預期月成本
# 300 檔 × 37.5 min × $0.04/60 min = $7.50
```

### 效能優化

**如果速度不夠快**:
- 檢查 Cloud Run concurrency 設定 (建議 5)
- 增加 max-instances (建議 10)

**如果成本過高**:
- 檢查是否有重複轉錄
- 確認音檔不會過長 (> 60 分鐘建議分段)

---

## 🔄 切換引擎

### 從 Gemini 切換到 Groq

```bash
gcloud builds submit --config cloudbuild.transcription-groq.yaml
```

### 回滾到 Gemini

```bash
gcloud builds submit --config cloudbuild.transcription.yaml
```

### 動態切換 (不重新部署)

```bash
# 切換到 Groq
gcloud run services update transcription-service \
  --set-env-vars=TRANSCRIPTION_ENGINE=groq_whisper \
  --region=asia-east1

# 切換到 Gemini
gcloud run services update transcription-service \
  --set-env-vars=TRANSCRIPTION_ENGINE=gemini \
  --region=asia-east1
```

---

## 📚 下一步

- 📖 [完整整合文檔](GROQ_WHISPER_INTEGRATION.md)
- 🔧 [故障排除指南](GROQ_WHISPER_INTEGRATION.md#-故障排除)
- 🎯 [Agent Prompts 優化](../analysis-service/src/agents/prompts/README.md)

---

**需要幫助？** 查看完整文檔或聯繫維護團隊。

**最後更新**: 2026-01-07
