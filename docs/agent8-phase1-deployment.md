# Agent 8 Phase 1 MVP 部署指南

**最後更新**：2025-11-04
**狀態**：✅ 代碼整合完成，準備部署

---

## 📦 完成的工作

### ✅ 代碼整合（已完成）

1. **Agent 8 核心模塊**
   - ✅ `src/slack_app/agents/question_parser.py` - 問題解析
   - ✅ `src/slack_app/agents/data_fetcher.py` - 數據查詢
   - ✅ `src/slack_app/agents/conversation_manager.py` - 對話管理
   - ✅ `src/slack_app/agents/conversational_agent8.py` - Agent 8 核心

2. **Slack 整合**
   - ✅ `src/slack_app/handlers/agent8_handler.py` - 命令處理器
   - ✅ `src/slack_app/main.py` - 註冊 `/ask-agent8` 命令

3. **文檔**
   - ✅ `docs/agent8-user-guide.md` - 用戶使用指南
   - ✅ `docs/agent8-permission-management.md` - 權限管理文檔
   - ✅ 本文檔 - 部署指南

4. **測試**
   - ✅ `src/slack_app/tests/test_agent8_integration.py` - 單元測試

5. **依賴管理**
   - ✅ `src/slack_app/requirements.txt` - 更新依賴（新增 google-generativeai, pydantic）

---

## 🚀 部署步驟

### 前置準備

**所需資源**：
- ✅ GCP 項目：`sales-ai-automation-v2`
- ✅ Firestore 資料庫（已存在）
- ✅ Cloud Run 服務：`slack-service`（已存在）
- ⚠️ Gemini API Key（需設定）
- ⚠️ 主管權限清單（需建立）

---

### Step 1: 設定環境變數

> 📘 參考：[Credential & Secret Management Guide](credential-management.md) — 取得 `GEMINI_API_KEY`、Slack Tokens 等所有憑證的 Secret Manager 設定方式。

在 Cloud Run 中添加環境變數：

```bash
# 設定 Gemini API Key
gcloud run services update slack-service \
  --region=asia-east1 \
  --update-env-vars GEMINI_API_KEY=<your-gemini-api-key>
```

**驗證現有環境變數**：

```bash
gcloud run services describe slack-service \
  --region=asia-east1 \
  --format="value(spec.template.spec.containers[0].env)"
```

**必須的環境變數**：
- ✅ `GCP_PROJECT_ID`
- ✅ `SLACK_BOT_TOKEN`
- ✅ `SLACK_SIGNING_SECRET`
- ⚠️ `GEMINI_API_KEY`（新增）

---

### Step 2: 建立主管權限清單

**方法 1：使用 Firestore Console（推薦首次設定）**

1. 前往 [Firestore Console](https://console.cloud.google.com/firestore)
2. 選擇或創建 `users` Collection
3. 添加測試主管：

   **Document ID**: `U12345678`（您的 Slack User ID）

   **欄位**：
   ```
   userId: U12345678
   role: manager
   name: 測試主管
   email: manager@example.com
   department: 業務部
   createdAt: [時間戳記]
   updatedAt: [時間戳記]
   ```

**如何獲取 Slack User ID**：
1. 在 Slack 中點擊自己的頭像
2. 選擇「檢視個人檔案」→「更多」→「複製成員 ID」

**方法 2：使用 Python Script**

創建 `scripts/add_manager.py`（參考 `docs/agent8-permission-management.md`），然後執行：

```bash
python scripts/add_manager.py U12345678 測試主管 manager@example.com
```

---

### Step 3: 部署到 Cloud Run

#### 選項 A：使用現有 CI/CD

如果已設置 Cloud Build 自動部署：

```bash
# 提交代碼
git add .
git commit -m "Add Agent 8 integration"
git push origin main
```

#### 選項 B：手動部署

```bash
cd src/slack_app

# 構建容器
gcloud builds submit \
  --tag gcr.io/sales-ai-automation-v2/slack-service

# 部署到 Cloud Run
gcloud run deploy slack-service \
  --image gcr.io/sales-ai-automation-v2/slack-service \
  --region asia-east1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT_ID=sales-ai-automation-v2,GEMINI_API_KEY=<your-key>
```

---

### Step 4: 配置 Slack App

在 [Slack App 配置頁面](https://api.slack.com/apps) 添加新命令：

1. 進入您的 Slack App
2. 選擇「Slash Commands」
3. 點擊「Create New Command」
4. 填寫資訊：

   ```
   Command: /ask-agent8
   Request URL: https://slack-service-xxx.run.app/slack/events
   Short Description: 詢問團隊數據和業務分析
   Usage Hint: 今天團隊表現如何？
   ```

5. 點擊「Save」
6. 重新安裝 App 到 workspace（如果需要）

---

### Step 5: 測試功能

#### 5.1 權限測試

**測試有權限的用戶**：
```
/ask-agent8 今天團隊表現如何？
```

**預期結果**：
- ✅ 收到 Agent 8 的回答
- ✅ 回答使用繁體中文
- ✅ 包含數據、洞察、建議

**測試無權限的用戶**：
- 切換到沒有主管權限的用戶
- 執行 `/ask-agent8 測試`

**預期結果**：
- ✅ 收到「沒有權限」訊息

#### 5.2 功能測試

測試以下問題類型：

```
# 1. 團隊整體
/ask-agent8 本週團隊表現如何？

# 2. 個人績效
/ask-agent8 [業務名字] 本週表現如何？

# 3. 案件分析
/ask-agent8 健康度低於 50 的案件有哪些？

# 4. 多輪對話
/ask-agent8 王小明的情況詳細說明？
/ask-agent8 他最好的案件是哪個？
```

#### 5.3 檢查日誌

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=slack-service" \
  --limit 50 \
  --format json
```

**關鍵日誌**：
- ✅ `收到 /ask-agent8 命令`
- ✅ `權限檢查：user=xxx, authorized=true/false`
- ✅ `Agent 8 回答成功`

---

## 🔧 故障排除

### 問題 1：收到「GEMINI_API_KEY 未設定」錯誤

**解決方法**：
```bash
gcloud run services update slack-service \
  --region=asia-east1 \
  --update-env-vars GEMINI_API_KEY=<your-key>
```

### 問題 2：收到「沒有權限」訊息

**檢查步驟**：
1. 確認 Firestore `users` Collection 中有您的 Document
2. 確認 `role` 欄位為 `manager` 或 `admin`
3. 確認 Document ID 是您的 Slack User ID

**驗證腳本**：
```python
from google.cloud import firestore

db = firestore.Client()
user_id = "U12345678"  # 您的 Slack User ID

doc = db.collection("users").document(user_id).get()
if doc.exists:
    print(f"用戶資料：{doc.to_dict()}")
else:
    print(f"用戶 {user_id} 不存在")
```

### 問題 3：Agent 8 沒有回應

**檢查步驟**：
1. 檢查 Cloud Run 日誌
2. 確認 Slack Command 的 Request URL 正確
3. 確認 Cloud Run 服務健康

```bash
curl https://slack-service-xxx.run.app/health
```

### 問題 4：回答錯誤或不完整

**可能原因**：
- Firestore 中沒有案件數據
- 查詢條件過於嚴格

**檢查數據**：
```python
from google.cloud import firestore

db = firestore.Client()
docs = db.collection("opportunities").limit(5).stream()

count = sum(1 for _ in docs)
print(f"案件數量：{count}")
```

---

## 📊 監控與維護

### 設定告警

```bash
# 創建告警策略（Cloud Run 錯誤率 > 5%）
gcloud alpha monitoring policies create \
  --notification-channels=<channel-id> \
  --display-name="Agent 8 Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05 \
  --condition-threshold-duration=300s
```

### 查看使用統計

```bash
# 查看 Agent 8 使用次數
gcloud logging read "textPayload:\"收到 /ask-agent8 命令\"" \
  --limit 100 \
  --format="value(timestamp)" | wc -l
```

### 成本監控

**預估成本**（每月）：
- Gemini 2.0 Flash Exp: ~$0.11（每天 10 次查詢）
- Cloud Run: 包含在現有服務中
- Firestore: 讀取操作費用極低

---

## 📝 下一步（Phase 2）

### 功能增強（可選）

1. **定時報告**
   - 每日早晨自動發送團隊摘要
   - 每週一發送上週總結

2. **更多問題類型**
   - 客戶滿意度趨勢
   - 成交預測

3. **優化**
   - 快取常見查詢
   - 批量處理

### 用戶培訓

1. 發送用戶使用指南（`docs/agent8-user-guide.md`）
2. 舉辦線上培訓
3. 收集反饋並優化

---

## ✅ 檢查清單

**部署前**：
- [ ] Gemini API Key 已設定
- [ ] 至少添加 1 位主管到 Firestore
- [ ] Cloud Run 環境變數正確

**部署中**：
- [ ] 代碼成功部署到 Cloud Run
- [ ] Slack Command 已配置
- [ ] 健康檢查通過

**部署後**：
- [ ] 有權限用戶測試成功
- [ ] 無權限用戶收到正確提示
- [ ] 多輪對話功能正常
- [ ] 日誌記錄正常

---

## 📞 支援

如有問題，請參考：
- [用戶使用指南](./agent8-user-guide.md)
- [權限管理文檔](./agent8-permission-management.md)
- [POC 測試報告](../specs/001-sales-ai-automation/poc-tests/poc8_agent8_conversational/POC8_REPORT.md)

---

**Agent 8 Phase 1 MVP 準備就緒！** 🎉
