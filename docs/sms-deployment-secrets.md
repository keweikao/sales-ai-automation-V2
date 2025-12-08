# SMS 服務部署 - 使用 Secret Manager

## 🔐 使用 Secret Manager 儲存敏感資訊（推薦）

### 步驟 1: 建立 Secrets

```bash
# 啟用 Secret Manager API
gcloud services enable secretmanager.googleapis.com

# 建立 EVERY8D 帳號 secret
echo -n "your_username" | gcloud secrets create every8d-username \
  --data-file=- \
  --replication-policy="automatic"

# 建立 EVERY8D 密碼 secret
echo -n "your_password" | gcloud secrets create every8d-password \
  --data-file=- \
  --replication-policy="automatic"

# 建立 SMS 內部 token secret
echo -n "$(openssl rand -hex 32)" | gcloud secrets create sms-internal-token \
  --data-file=- \
  --replication-policy="automatic"
```

### 步驟 2: 授予 Cloud Run 存取權限

```bash
# 取得 Cloud Run 服務帳號
PROJECT_NUMBER=$(gcloud projects describe sales-ai-automation-v2 --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# 授予 Secret Manager 存取權限
gcloud secrets add-iam-policy-binding every8d-username \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding every8d-password \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding sms-internal-token \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```

### 步驟 3: 部署 SMS 服務（使用 Secret Manager）

```bash
cd /Users/stephen/Desktop/sales-ai-automation-V2/sms-service

# 建立 Docker 映像
gcloud builds submit --tag gcr.io/sales-ai-automation-v2/sms-service

# 部署到 Cloud Run（使用 secrets）
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

### 步驟 4: 更新 Slack App（使用 Secret Manager）

```bash
# 取得 SMS 服務 URL
SMS_SERVICE_URL=$(gcloud run services describe sms-service \
  --region asia-east1 \
  --format 'value(status.url)')

# 更新 Slack App
gcloud run services update slack-app \
  --region asia-east1 \
  --set-env-vars "SMS_SERVICE_URL=$SMS_SERVICE_URL" \
  --set-secrets "SMS_INTERNAL_TOKEN=sms-internal-token:latest"
```

---

## 🔄 更新 Secret 值

```bash
# 更新 EVERY8D 密碼
echo -n "new_password" | gcloud secrets versions add every8d-password \
  --data-file=-

# Cloud Run 會自動使用最新版本（:latest）
# 如果需要立即生效，重新部署服務
gcloud run services update sms-service --region asia-east1
```

---

## 📋 查看 Secret 狀態

```bash
# 列出所有 secrets
gcloud secrets list

# 查看特定 secret 的版本
gcloud secrets versions list every8d-password

# 查看 secret 的 IAM 權限
gcloud secrets get-iam-policy every8d-password
```

---

## ⚠️ 安全最佳實踐

### ✅ 推薦做法（使用 Secret Manager）
- 敏感資訊儲存在 Secret Manager
- 自動版本控制
- 細粒度的存取控制
- 審計日誌記錄

### ❌ 不推薦做法（直接使用環境變數）
```bash
# 不要這樣做！
gcloud run deploy sms-service \
  --set-env-vars "EVERY8D_PASSWORD=my_password"  # ❌ 密碼會出現在日誌中
```

---

## 🔍 驗證 Secret 配置

```bash
# 查看 Cloud Run 服務配置
gcloud run services describe sms-service \
  --region asia-east1 \
  --format yaml | grep -A 5 secrets

# 應該看到類似輸出：
# secrets:
# - name: EVERY8D_USERNAME
#   valueFrom:
#     secretKeyRef:
#       key: latest
#       name: every8d-username
```

---

## 💰 成本說明

Secret Manager 定價：
- **前 6 個 secrets**: 免費
- **每個額外 secret**: $0.06/月
- **每 10,000 次存取**: $0.03

對於我們的使用情況（3 個 secrets），**完全免費**！

---

## 🔗 相關文件

- [Secret Manager 文件](https://cloud.google.com/secret-manager/docs)
- [Cloud Run Secrets 整合](https://cloud.google.com/run/docs/configuring/secrets)
