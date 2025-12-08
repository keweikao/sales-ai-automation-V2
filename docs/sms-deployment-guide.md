# SMS 會議記錄功能部署指南

## 📋 部署前準備

### 1. 註冊互動資通 EVERY8D 帳號

1. 前往 [互動資通 EVERY8D](https://www.every8d.com/)
2. 註冊企業帳號
3. 申請 API 使用權限
4. 儲值點數（建議先儲值 NT$ 1,000 測試）
5. 取得 API 帳號和密碼

### 2. 準備環境變數

```bash
# 互動資通 EVERY8D
EVERY8D_USERNAME=your_username
EVERY8D_PASSWORD=your_password

# SMS 服務
SMS_SERVICE_URL=https://sms-service-xxx.run.app
SMS_INTERNAL_TOKEN=your_random_token_here

# 網頁服務
SUMMARY_BASE_URL=https://web-service-497329205771.asia-east1.run.app
```

---

## 🚀 部署步驟

### 步驟 1: 部署 SMS 服務到 Cloud Run

> **⚠️ 重要**: 建議使用 **Secret Manager** 儲存敏感資訊（帳號密碼）
>
> 詳細步驟請參考: [`sms-deployment-secrets.md`](sms-deployment-secrets.md)

#### 方法 A: 使用 Secret Manager（推薦）✅

```bash
# 1. 建立 secrets
echo -n "your_username" | gcloud secrets create every8d-username --data-file=- --replication-policy="automatic"
echo -n "your_password" | gcloud secrets create every8d-password --data-file=- --replication-policy="automatic"
echo -n "$(openssl rand -hex 32)" | gcloud secrets create sms-internal-token --data-file=- --replication-policy="automatic"

# 2. 授予權限
PROJECT_NUMBER=$(gcloud projects describe sales-ai-automation-v2 --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for secret in every8d-username every8d-password sms-internal-token; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"
done

# 3. 建立並部署
cd /Users/stephen/Desktop/sales-ai-automation-V2/sms-service
gcloud builds submit --tag gcr.io/sales-ai-automation-v2/sms-service

gcloud run deploy sms-service \
  --image gcr.io/sales-ai-automation-v2/sms-service \
  --platform managed \
  --region asia-east1 \
  --allow-unauthenticated \
  --set-env-vars "GCP_PROJECT_ID=sales-ai-automation-v2" \
  --set-env-vars "SUMMARY_BASE_URL=https://web-service-497329205771.asia-east1.run.app" \
  --set-secrets "EVERY8D_USERNAME=every8d-username:latest" \
  --set-secrets "EVERY8D_PASSWORD=every8d-password:latest" \
  --set-secrets "SMS_INTERNAL_TOKEN=sms-internal-token:latest" \
  --memory 512Mi \
  --timeout 60s
```

#### 方法 B: 使用環境變數（不推薦，僅供測試）⚠️

```bash
cd /Users/stephen/Desktop/sales-ai-automation-V2/sms-service

# 建立 Docker 映像
gcloud builds submit --tag gcr.io/sales-ai-automation-v2/sms-service

# 部署到 Cloud Run
gcloud run deploy sms-service \
  --image gcr.io/sales-ai-automation-v2/sms-service \
  --platform managed \
  --region asia-east1 \
  --allow-unauthenticated \
  --set-env-vars "GCP_PROJECT_ID=sales-ai-automation-v2" \
  --set-env-vars "EVERY8D_USERNAME=$EVERY8D_USERNAME" \
  --set-env-vars "EVERY8D_PASSWORD=$EVERY8D_PASSWORD" \
  --set-env-vars "SUMMARY_BASE_URL=$SUMMARY_BASE_URL" \
  --set-env-vars "SMS_INTERNAL_TOKEN=$SMS_INTERNAL_TOKEN" \
  --memory 512Mi \
  --timeout 60s
```

### 步驟 2: 更新 Slack App 環境變數

```bash
# 取得 SMS 服務 URL
SMS_SERVICE_URL=$(gcloud run services describe sms-service \
  --region asia-east1 \
  --format 'value(status.url)')

# 更新 Slack App
gcloud run services update slack-app \
  --region asia-east1 \
  --set-env-vars "SMS_SERVICE_URL=$SMS_SERVICE_URL" \
  --set-env-vars "SMS_INTERNAL_TOKEN=$SMS_INTERNAL_TOKEN"
```

### 步驟 3: 重新部署 Slack App

```bash
cd /Users/stephen/Desktop/sales-ai-automation-V2

# 重新部署 Slack App（包含新的按鈕處理器）
gcloud run deploy slack-app \
  --source ./src/slack_app \
  --region asia-east1 \
  --platform managed
```

---

## 🧪 測試

### 本地測試 SMS 服務

```bash
# 設定環境變數
export EVERY8D_USERNAME=your_username
export EVERY8D_PASSWORD=your_password
export GCP_PROJECT_ID=sales-ai-automation-v2

# 啟動本地服務
cd sms-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python src/main.py

# 在另一個終端測試
python test_sms_service.py \
  --case-id 202512-IC001 \
  --phone 0912345678 \
  --name "測試客戶"
```

### 端到端測試

1. **上傳音檔到 Slack**
   - 在 Slack DM 上傳音檔
   - 填寫客戶資訊（電話現在是必填）

2. **等待分析完成**
   - Agent 1-4 會依序執行
   - Agent 4 會顯示會議記錄 + 按鈕

3. **測試編輯功能**
   - 點擊「📝 編輯」按鈕
   - 修改會議記錄內容
   - 儲存

4. **測試發送功能**
   - 點擊「📤 發送給客戶」按鈕
   - 確認發送
   - 檢查客戶是否收到簡訊
   - 點擊簡訊中的連結，確認網頁正常顯示

---

## ✅ 驗收清單

### 功能驗證

- [ ] Slack 上傳時電話為必填
- [ ] Agent 4 完成後顯示編輯和發送按鈕
- [ ] 編輯功能正常運作
- [ ] 點擊發送後客戶收到簡訊
- [ ] 簡訊包含正確的網頁連結
- [ ] 網頁顯示完整會議記錄
- [ ] Firestore 正確記錄發送狀態

### 錯誤處理

- [ ] 無效電話號碼會顯示錯誤
- [ ] 重複發送會顯示警告
- [ ] SMS 發送失敗有適當錯誤訊息
- [ ] 餘額不足時有明確提示

### 監控

- [ ] Cloud Logging 記錄 SMS 發送
- [ ] Firestore delivery 欄位正確更新
- [ ] 可以追蹤 SMS 成本

---

## 📊 監控與維護

### 查看 SMS 發送記錄

```bash
# 查看 SMS 服務日誌
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=sms-service" \
  --limit 50 \
  --format json

# 查看 Firestore 發送狀態
# 在 Firebase Console 查看 cases/{caseId}/delivery
```

### 監控成本

```bash
# 在 GCP Billing 中設定預算警報
# 建議設定: NT$ 500/月
```

---

## 🔧 故障排除

### 問題 1: SMS 發送失敗

**檢查項目**:

1. EVERY8D 帳號密碼是否正確
2. 帳號餘額是否充足
3. 手機號碼格式是否正確 (09xxxxxxxx)

**解決方法**:

```bash
# 檢查環境變數
gcloud run services describe sms-service --region asia-east1 --format yaml | grep env

# 查看錯誤日誌
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=sms-service AND severity>=ERROR" --limit 10
```

### 問題 2: 按鈕無反應

**檢查項目**:

1. Slack App 是否已重新部署
2. summary_sender 是否正確初始化
3. SMS_SERVICE_URL 是否設定

**解決方法**:

```bash
# 查看 Slack App 日誌
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=slack-app AND textPayload:summary_sender" --limit 10
```

### 問題 3: 網頁無法訪問

**檢查項目**:

1. web-service 是否正常運行
2. Firestore customerSummary 是否存在
3. URL 格式是否正確

---

## 📝 相關文件

- [互動資通 EVERY8D API 文件](https://www.every8d.com/api)
- [實作計畫](implementation_plan.md)
- [任務清單](task.md)

---

## 💡 後續優化建議

1. **短網址服務**: 使用 bit.ly 或 Google URL Shortener 縮短連結
2. **發送時間控制**: 避免在非營業時間發送簡訊
3. **範本管理**: 允許自訂簡訊內容範本
4. **發送記錄**: 建立 SMS 發送歷史查詢介面
5. **成本追蹤**: 建立 SMS 成本儀表板
