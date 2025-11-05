# Slack App 配置檢查清單（給 Admin）

> **目的**：協助 Slack Workspace Admin 快速配置 `/ask-agent8` 命令，啟用 Agent 8 業務主管智能助理功能。

---

## ✅ 前置條件

在開始配置前，請確認：

- [ ] 您有 Slack Workspace 的 Admin 權限
- [ ] Cloud Run 服務 `slack-app` 已部署並運行
- [ ] 服務 URL: `https://slack-app-497329205771.asia-east1.run.app`

---

## 🔧 配置步驟（約 5 分鐘）

### 步驟 1：進入 Slack App 管理頁面

1. 開啟 [Slack API Apps](https://api.slack.com/apps)
2. 登入您的 Slack Workspace
3. 找到並點擊專案使用的 Slack App（應該已經建立）

### 步驟 2：添加 Slash Command

1. 在左側選單中，點擊 **「Slash Commands」**
2. 點擊 **「Create New Command」** 按鈕
3. 填寫以下資訊：

   | 欄位 | 值 |
   |------|-----|
   | **Command** | `/ask-agent8` |
   | **Request URL** | `https://slack-app-497329205771.asia-east1.run.app/slack/events` |
   | **Short Description** | 詢問團隊數據和業務分析 |
   | **Usage Hint** | 今天團隊表現如何？ |

4. 點擊 **「Save」** 按鈕

### 步驟 3：確認權限範圍（Scopes）

確認 App 已有以下 Bot Token Scopes（應該已配置）：

- [x] `chat:write` - 發送訊息
- [x] `commands` - 接收 slash commands
- [x] `users:read` - 讀取用戶資訊
- [x] `channels:read` - 讀取頻道資訊

如果有新增 scopes，需要重新安裝 App（下一步）。

### 步驟 4：重新安裝 App（如需要）

**僅在新增權限時需要此步驟**：

1. 在左側選單中，點擊 **「Install App」**
2. 點擊 **「Reinstall to Workspace」** 按鈕
3. 授權 App 使用新權限

### 步驟 5：驗證配置

在 Slack 中測試新命令：

```text
/ask-agent8
```

**預期結果**：

- ✅ 如果您有主管權限：收到「請在命令後輸入問題」的提示
- ✅ 如果您沒有主管權限：收到「沒有使用 Agent 8 的權限」訊息

---

## 🧪 測試命令範例

配置完成後，可以用以下命令測試（需要有主管權限）：

```text
/ask-agent8 今天團隊表現如何？
/ask-agent8 王小明本週表現如何？
/ask-agent8 健康度低於 50 的案件有哪些？
```

---

## ⚠️ 常見問題

### Q1: 輸入命令後沒有反應？

**可能原因**：

- Request URL 設定錯誤
- Cloud Run 服務未運行

**解決方式**：

1. 檢查 Request URL 是否正確：`https://slack-app-497329205771.asia-east1.run.app/slack/events`
2. 確認 Cloud Run 服務狀態：

   ```bash
   gcloud run services describe slack-app --region=asia-east1
   ```

### Q2: 收到 "dispatch_failed" 錯誤？

**可能原因**：Cloud Run 服務無法訪問或未啟動

**解決方式**：

1. 檢查 Cloud Run 服務日誌：

   ```bash
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=slack-app" --limit=50 --format=json
   ```

2. 確認服務健康檢查：

   ```bash
   curl https://slack-app-497329205771.asia-east1.run.app/health
   ```

### Q3: 命令已配置，但用戶說看不到？

**可能原因**：用戶的 Slack App 尚未更新

**解決方式**：

- 要求用戶重新載入 Slack（Ctrl+R 或 Cmd+R）
- 要求用戶登出再登入 Slack

---

## 📞 需要協助？

如果遇到技術問題，請聯絡：

- **開發團隊**：提供 Cloud Run 服務日誌
- **系統管理員**：檢查 Firestore 權限設定

---

## ✅ 配置完成確認清單

完成後，請確認：

- [ ] `/ask-agent8` 命令已建立並儲存
- [ ] Request URL 正確設定為 `https://slack-app-497329205771.asia-east1.run.app/slack/events`
- [ ] 已測試命令並確認可正常運作
- [ ] 已通知相關主管可以開始使用 Agent 8

---

**配置日期**: _______________
**配置人員**: _______________
**驗證狀態**: ⬜ 成功 ⬜ 失敗（原因：_______________）
