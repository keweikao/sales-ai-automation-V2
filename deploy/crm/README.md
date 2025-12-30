# CRM Service 部署指南

## 環境變數設定

### GCP Secret Manager 憑證

在部署前，請先在 GCP Secret Manager 建立以下 secrets：

```bash
# Salesforce 憑證
gcloud secrets create sf-client-id --data-file=-
gcloud secrets create sf-client-secret --data-file=-
gcloud secrets create sf-username --data-file=-
gcloud secrets create sf-password --data-file=-
gcloud secrets create sf-security-token --data-file=-
```

### Cloud Run 環境變數

| 變數名稱 | 說明 | 來源 |
|---------|------|------|
| `SF_CLIENT_ID` | Salesforce Connected App Client ID | Secret Manager |
| `SF_CLIENT_SECRET` | Salesforce Connected App Client Secret | Secret Manager |
| `SF_USERNAME` | Salesforce 使用者名稱 | Secret Manager |
| `SF_PASSWORD` | Salesforce 密碼 | Secret Manager |
| `SF_SECURITY_TOKEN` | Salesforce Security Token | Secret Manager |
| `SF_DOMAIN` | `login` (production) 或 `test` (sandbox) | 環境變數 |
| `GCP_PROJECT_ID` | GCP 專案 ID | 環境變數 |
| `SLACK_WEBHOOK_URL` | 錯誤通知 Slack Webhook | 環境變數 |

## 部署指令

```bash
# 從專案根目錄執行
gcloud builds submit --config=cloudbuild.crm-service.yaml
```

## Cloud Scheduler 設定

設定每日 8:00 PM 同步 Salesforce 機會：

```bash
gcloud scheduler jobs create http sync-salesforce-opportunities \
  --location=asia-east1 \
  --schedule="0 20 * * *" \
  --uri="https://crm-service-XXXXXX-de.a.run.app/sync-opportunities" \
  --http-method=POST \
  --oidc-service-account-email=YOUR_SERVICE_ACCOUNT@PROJECT.iam.gserviceaccount.com \
  --time-zone="Asia/Taipei"
```

## 測試 Endpoints

### 健康檢查
```bash
curl https://crm-service-XXXXXX-de.a.run.app/health
```

### 手動觸發同步
```bash
curl -X POST https://crm-service-XXXXXX-de.a.run.app/sync-opportunities
```

### 更新機會狀態
```bash
curl -X POST https://crm-service-XXXXXX-de.a.run.app/update-status \
  -H "Content-Type: application/json" \
  -d '{"customerId": "CU123", "stageName": "Meeting Completed"}'
```
