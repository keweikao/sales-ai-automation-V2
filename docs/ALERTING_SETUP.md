# Cloud Monitoring 告警設定指南

## 設定步驟

### 1. 建立通知管道 (Email)

1. 前往 [Cloud Console > Monitoring > Alerting](https://console.cloud.google.com/monitoring/alerting?project=sales-ai-automation-v2)
2. 點擊 **Edit Notification Channels**
3. 在 **Email** 區塊點擊 **Add New**
4. 輸入 email 地址，例如：`admin@company.com`
5. 點擊 **Save**

可以新增多個 email 地址，每個都會收到告警。

---

### 2. 建立告警政策

#### 方法 A: 透過 Console UI

1. 前往 [Alerting > Create Policy](https://console.cloud.google.com/monitoring/alerting/policies/create?project=sales-ai-automation-v2)
2. 設定條件：
   - Metric: `Cloud Run Revision > Request Count`
   - Filter: `service_name = analysis-service`, `response_code_class = 5xx`
   - Condition: `> 5 per minute`
3. 選擇通知管道 (剛才建立的 email)
4. 命名並儲存

#### 方法 B: 透過 gcloud CLI (推薦)

```bash
# 設定通知管道
gcloud alpha monitoring channels create \
  --display-name="Admin Email" \
  --type=email \
  --channel-labels=email_address=your@email.com \
  --project=sales-ai-automation-v2

# 取得 channel ID
gcloud alpha monitoring channels list --project=sales-ai-automation-v2
```

---

### 3. 建議的告警政策

| 告警名稱 | 條件 | 嚴重度 |
|----------|------|--------|
| 高錯誤率 | 5xx 錯誤 > 5/min | Critical |
| 服務延遲 | Latency P95 > 30s | Warning |
| 服務當機 | 請求數 = 0 持續 5min | Critical |

---

## 快速設定腳本

執行以下指令來建立基本告警：

```bash
# 建立 email 通知管道 (替換 your@email.com)
gcloud alpha monitoring channels create \
  --display-name="Admin Email" \
  --type=email \
  --channel-labels=email_address=YOUR_EMAIL@example.com \
  --project=sales-ai-automation-v2
```

---

## 管理通知人員

### 新增人員
1. Console > Monitoring > Alerting > Edit Notification Channels
2. Email 區塊 > Add New
3. 輸入新的 email 地址

### 移除人員
1. 在同一頁面找到要移除的 email
2. 點擊刪除圖示

---

## 替代方案：程式碼管理

如果需要從程式碼管理通知人員，可以使用 Firestore 存放 email 列表：

```python
# Firestore 結構
# /settings/alerts
{
  "email_recipients": [
    "admin@company.com",
    "manager@company.com"
  ]
}
```

需要這個方案的話請告知。
