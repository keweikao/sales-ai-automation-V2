# CRM Service

Salesforce 整合微服務，負責：

1. 定期從 Salesforce 同步 Opportunity 資料
2. 分析完成後即時更新 Salesforce StageName
3. 回填 Agent 6 擷取的結構化欄位

## 環境變數

| 變數名稱 | 說明 |
|---------|------|
| `SF_CLIENT_ID` | Salesforce Connected App Client ID |
| `SF_CLIENT_SECRET` | Salesforce Connected App Client Secret |
| `SF_USERNAME` | Salesforce 使用者名稱 |
| `SF_PASSWORD` | Salesforce 密碼 |
| `SF_SECURITY_TOKEN` | Salesforce Security Token |
| `SF_DOMAIN` | Salesforce 網域 (預設: login) |
| `GCP_PROJECT_ID` | GCP 專案 ID |
| `SLACK_WEBHOOK_URL` | (選填) 錯誤通知 Slack Webhook |

## 本地開發

```bash
cd crm-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

## 部署

```bash
gcloud builds submit --config=cloudbuild.crm-service.yaml
```
