# Slack Service 實作任務清單

**專案**: Sales AI Automation V2.0
**Sprint**: Sprint 5-6 (Week 9-12)
**文件版本**: 1.0
**最後更新**: 2025-10-31
**相關文件**: [slack-workflow.md](./slack-workflow.md), [plan.md](./plan.md)

---

## 概述

本文件定義 Slack Service 的完整實作任務，遵循憲法的開發流程（Specification → Planning → Tasks → Implementation）。

### 總預估工作量

- **總時程**: 4 週（Sprint 5-6）
- **總工作量**: ~60-80 小時
- **優先級**: P0（核心功能）

### 依賴關係

- ✅ Firestore 已部署
- ✅ Agent 6/7 已完成
- ✅ Cloud Tasks 已設定
- ⚠️ 需要：Slack App 建立與設定
- ⚠️ 需要：SMS 服務商（Twilio）帳號

---

## Sprint 5: 核心功能（Week 9-10）

### Task 5.1: Slack App 設定與基礎建設

**優先級**: P0
**預估時間**: 4 小時
**負責人**: DevOps + Backend

**子任務**:

1. 在 Slack workspace 建立新 App "Sales AI Bot"
2. 設定 OAuth 權限（files:read, chat:write, im:write, im:history, users:read）
3. 設定 Event Subscriptions（file_shared, app_home_opened）
4. 將 Bot Token 和 Signing Secret 儲存到 Secret Manager
5. 安裝 Bot 到 workspace 並測試基本連線

**驗收標準**:

- [ ] Slack App 已建立並安裝
- [ ] Bot 可接收 file_shared 事件
- [ ] Secret Manager 中已儲存憑證
- [ ] 本地開發環境可連接 Slack API

**技術細節**:

```bash
# 建立 secrets
gcloud secrets create slack-bot-token --data-file=-
gcloud secrets create slack-signing-secret --data-file=-

# 測試連線
curl -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  https://slack.com/api/auth.test
```

---

### Task 5.2: 音檔上傳偵測與按鈕顯示

**優先級**: P0
**預估時間**: 8 小時
**依賴**: Task 5.1

**子任務**:

1. 實作 `file_shared` 事件處理器
2. 檢查檔案類型（僅處理音檔）
3. 檢查上傳位置（僅處理 DM）
4. 查詢 `processed_files` 檢查是否已處理
5. 發送 Block Kit 訊息含「分析此錄音」按鈕

**檔案位置**:

- `services/slack-service/src/events/file_upload_handler.py`
- `services/slack-service/src/models/slack_events.py`

**驗收標準**:

- [ ] 業務在 DM 上傳音檔時，Bot 立即回覆
- [ ] Channel 上傳音檔時，Bot 不回覆
- [ ] 非音檔（圖片、文件）時，Bot 不回覆
- [ ] 已處理的音檔顯示「已處理」訊息
- [ ] 單元測試覆蓋率 >80%

**測試案例**:

```python
# test_file_upload_handler.py
@pytest.mark.asyncio
async def test_audio_file_in_dm():
    """測試 DM 中上傳音檔"""
    # Given: 音檔上傳事件
    # When: 處理事件
    # Then: Bot 發送分析按鈕

@pytest.mark.asyncio
async def test_audio_file_in_channel():
    """測試 Channel 中上傳音檔（應忽略）"""
    # Given: Channel 音檔上傳事件
    # When: 處理事件
    # Then: Bot 不發送任何訊息

@pytest.mark.asyncio
async def test_non_audio_file():
    """測試非音檔（應忽略）"""
    # Given: 圖片上傳事件
    # When: 處理事件
    # Then: Bot 不發送任何訊息
```

---

### Task 5.3: Modal 開啟與資料收集

**優先級**: P0
**預估時間**: 6 小時
**依賴**: Task 5.2

**子任務**:

1. 實作「分析此錄音」按鈕點擊處理器
2. 開啟 Modal 含表單欄位（店名、客戶編號、手機、備註）
3. 實作欄位驗證（手機格式）
4. 處理 Modal 取消（無操作）

**檔案位置**:

- `services/slack-service/src/interactions/analysis_button_handler.py`

**驗收標準**:

- [ ] 點擊按鈕後 Modal 立即開啟（<1秒）
- [ ] Modal 包含所有必填欄位
- [ ] 手機格式驗證正確（09xx-xxx-xxx）
- [ ] 取消 Modal 後可重新開啟
- [ ] 已處理的檔案點擊按鈕顯示 ephemeral 提示

**技術細節**:

```python
# 手機驗證
phone_pattern = r'^09\d{2}-?\d{3}-?\d{3}$'
if not re.match(phone_pattern, cleaned_phone):
    return errors
```

---

### Task 5.4: Transaction 鎖定與 Case 建立

**優先級**: P0
**預估時間**: 10 小時
**依賴**: Task 5.3

**子任務**:

1. 實作 Modal 提交處理器
2. 使用 Firestore Transaction 檢查並鎖定 `processed_files`
3. 建立 `cases` document
4. 更新 `processed_files` 加入 caseId
5. 更新 Slack 按鈕為「已開始分析」狀態
6. 下載音檔到 GCS
7. 觸發 Cloud Tasks 轉錄任務

**檔案位置**:

- `services/slack-service/src/interactions/modal_handler.py`
- `services/slack-service/src/utils/firestore_client.py`
- `services/slack-service/src/utils/audio_downloader.py`

**驗收標準**:

- [ ] Transaction 防止並發提交（測試：兩個用戶同時提交）
- [ ] Case 成功建立到 Firestore
- [ ] 音檔成功下載到 GCS（驗證 md5 hash）
- [ ] Cloud Tasks 任務成功加入佇列
- [ ] Slack 按鈕更新為禁用狀態
- [ ] 錯誤時回滾 Transaction 並解鎖

**測試案例**:

```python
@pytest.mark.asyncio
async def test_concurrent_submission():
    """測試並發提交（只有一個成功）"""
    # Given: 同一個 file_id
    # When: 兩個用戶同時提交 Modal
    # Then: 只有一個成功，另一個收到錯誤
```

---

### Task 5.5: 處理錯誤與重試通知

**優先級**: P0
**預估時間**: 6 小時
**依賴**: Task 5.4

**子任務**:

1. 監聽 Transcription/Analysis 服務的錯誤事件
2. 在 Slack thread 中發送錯誤通知
3. 根據重試次數顯示不同訊息
4. 更新按鈕狀態為「處理失敗」（重試用盡時）
5. 實作「查看錯誤詳情」Modal

**檔案位置**:

- `services/slack-service/src/notifications/error_notifier.py`

**驗收標準**:

- [ ] 轉錄失敗時，業務收到通知（1-3 次重試）
- [ ] 重試用盡時，按鈕變為紅色「處理失敗」
- [ ] 點擊錯誤按鈕可查看詳細錯誤訊息
- [ ] 錯誤訊息包含：失敗階段、重試次數、錯誤訊息

**通知範例**:

```
⚠️ 處理時發生錯誤，系統正在自動重試（第 1 次）...
案件編號：202501-IC001 | 錯誤階段：transcription
```

---

## Sprint 5 總結

**完成項目**:

- ✅ Slack App 設定
- ✅ 音檔上傳偵測
- ✅ Modal 資料收集
- ✅ Transaction 鎖定
- ✅ 錯誤通知

**產出**:

- `services/slack-service/` 基礎框架
- 音檔上傳到處理的完整流程
- 單元測試套件

---

## Sprint 6: 摘要編輯與發送（Week 11-12）

### Task 6.1: Agent 6 結果顯示

**優先級**: P1
**預估時間**: 4 小時
**依賴**: Sprint 5 完成

**子任務**:

1. 監聽 Agent 6 完成事件
2. 格式化 Agent 6 結果為 Block Kit 卡片
3. 在 DM thread 中發送銷售分析卡片

**檔案位置**:

- `services/slack-service/src/notifications/agent6_notifier.py`
- `services/slack-service/src/templates/agent6_card.json`

**驗收標準**:

- [ ] Agent 6 完成後立即發送通知（<5秒）
- [ ] 卡片包含：銷售階段、成交健康度、關鍵決策者、下一步行動
- [ ] 格式清晰易讀（繁體中文）

---

### Task 6.2: Agent 7 摘要預覽與按鈕

**優先級**: P0
**預估時間**: 6 小時
**依賴**: Task 6.1

**子任務**:

1. 監聽 Agent 7 完成事件
2. 顯示摘要預覽（前 500 字元）
3. 提供三個按鈕：編輯、預覽、確認送出

**檔案位置**:

- `services/slack-service/src/notifications/agent7_notifier.py`

**驗收標準**:

- [ ] Agent 7 完成後立即發送摘要（<5秒）
- [ ] 預覽顯示前 500 字元 + "..."
- [ ] 三個按鈕正常運作
- [ ] 訊息格式符合設計稿

---

### Task 6.3: 摘要編輯功能

**優先級**: P0
**預估時間**: 8 小時
**依賴**: Task 6.2

**子任務**:

1. 實作「編輯摘要」按鈕處理器
2. 開啟 Modal 含 Markdown 編輯器（max 3000 字元）
3. 實作儲存功能（更新 Firestore）
4. 更新預覽訊息並標記「已編輯」
5. 記錄編輯歷史

**檔案位置**:

- `services/slack-service/src/interactions/summary_editor.py`

**驗收標準**:

- [ ] 編輯 Modal 顯示當前 Markdown 內容
- [ ] 儲存後 Firestore 成功更新
- [ ] 預覽訊息更新並顯示「已編輯」標記
- [ ] 可重複編輯
- [ ] 編輯歷史記錄到 `editHistory`

**技術細節**:

```python
# 更新 Firestore
await db.collection("cases").document(case_id).update({
    "analysis.customerSummary.markdown": new_content,
    "analysis.customerSummary.lastEditedAt": firestore.SERVER_TIMESTAMP,
    "analysis.customerSummary.editedBy": user_id
})
```

---

### Task 6.4: 完整預覽功能

**優先級**: P2
**預估時間**: 2 小時
**依賴**: Task 6.2

**子任務**:

1. 實作「完整預覽」按鈕處理器
2. 開啟 Modal 顯示完整 Markdown（唯讀）

**驗收標準**:

- [ ] 完整預覽顯示所有內容（無字數限制）
- [ ] 格式正確（Markdown 渲染）
- [ ] 唯讀模式（無編輯按鈕）

---

### Task 6.5: 摘要網頁生成

**優先級**: P0
**預估時間**: 10 小時
**依賴**: Task 6.2

**子任務**:

1. 建立 `web-service` Cloud Run 服務
2. 實作 Markdown → HTML 轉換
3. 套用 iCHEF branding 模板
4. 實作 `/summary/{caseId}` endpoint
5. 記錄客戶查看次數

**檔案位置**:

- `services/web-service/src/main.py`
- `services/web-service/src/summary_renderer.py`
- `services/web-service/templates/customer_summary.html`

**驗收標準**:

- [ ] 網頁正確顯示摘要內容
- [ ] 套用 iCHEF logo 與 branding
- [ ] 響應式設計（手機 + 桌面）
- [ ] LINE 聯絡按鈕連結正確
- [ ] 記錄查看次數到 Firestore

**技術細節**:

```python
# Markdown → HTML
import markdown
html = markdown.markdown(
    markdown_content,
    extensions=['tables', 'fenced_code', 'nl2br']
)
```

---

### Task 6.6: SMS 發送整合

**優先級**: P0
**預估時間**: 8 小時
**依賴**: Task 6.5

**子任務**:

1. 申請 Twilio 帳號並設定
2. 將 Twilio 憑證儲存到 Secret Manager
3. 建立 `notification-service` Cloud Run 服務
4. 實作 SMS 發送功能
5. 處理發送失敗並記錄錯誤

**檔案位置**:

- `services/notification-service/src/sms_sender.py`

**驗收標準**:

- [ ] SMS 成功發送到客戶手機
- [ ] 訊息包含：問候語、網頁連結、業務聯絡資訊
- [ ] 訊息使用繁體中文
- [ ] 發送失敗時記錄錯誤並通知業務
- [ ] 記錄發送狀態到 Firestore

**SMS 範本**:

```
您好，我是 iCHEF 的 {業務姓名}。

感謝您今天與我們的會議！我已為您整理好會議摘要：
{summary_url}

若有任何問題，歡迎隨時與我聯繫 📞

iCHEF 資廚管理顧問
```

---

### Task 6.7: 確認送出流程

**優先級**: P0
**預估時間**: 6 小時
**依賴**: Task 6.5, Task 6.6

**子任務**:

1. 實作「確認送出」按鈕處理器（含確認對話框）
2. 更新 Firestore status 為 "approved"
3. 觸發網頁生成
4. 觸發 SMS 發送
5. 在 Slack 回報成功訊息

**檔案位置**:

- `services/slack-service/src/workflows/customer_delivery.py`

**驗收標準**:

- [ ] 點擊「確認送出」後顯示確認對話框
- [ ] 確認後觸發網頁生成 + SMS 發送
- [ ] 成功後在 thread 回報：SMS 狀態、網頁連結
- [ ] 失敗時顯示錯誤並保留重試選項

---

## Sprint 6 總結

**完成項目**:

- ✅ Agent 6/7 結果顯示
- ✅ 摘要編輯功能
- ✅ 客戶網頁生成
- ✅ SMS 發送整合
- ✅ 完整工作流程

**產出**:

- 完整的 Slack 互動流程
- 客戶摘要網頁服務
- SMS 通知服務
- E2E 測試套件

---

## 測試策略

### 單元測試

**覆蓋率目標**: >80%

**關鍵測試**:

- `test_file_upload_handler.py`: 音檔偵測邏輯
- `test_modal_handler.py`: Transaction 鎖定邏輯
- `test_summary_editor.py`: 編輯功能
- `test_sms_sender.py`: SMS 發送（使用 mock）

### 整合測試

**測試案例**:

1. 完整流程：上傳 → 處理 → 編輯 → 送出
2. 並發處理：兩個用戶同時處理同一音檔
3. 錯誤處理：轉錄失敗、SMS 失敗

### E2E 測試

**工具**: pytest + Slack Bolt testing utilities

**測試案例**:

```python
@pytest.mark.e2e
async def test_complete_workflow():
    """測試完整工作流程"""
    # 1. 模擬上傳音檔
    # 2. 驗證 Bot 回覆
    # 3. 模擬點擊按鈕填寫 Modal
    # 4. 等待處理完成（mock）
    # 5. 驗證 Agent 6/7 通知
    # 6. 模擬編輯摘要
    # 7. 模擬確認送出
    # 8. 驗證網頁生成與 SMS 發送
```

---

## 部署檢查清單

### Sprint 5 部署

- [ ] Slack App 已設定並安裝
- [ ] Secret Manager 憑證已建立
- [ ] `slack-service` 部署到 Cloud Run
- [ ] Event Subscriptions Request URL 已設定
- [ ] Firestore `processed_files` collection 已建立
- [ ] 索引已建立（slackFileId, caseId, status）

### Sprint 6 部署

- [ ] Twilio 帳號已申請並充值
- [ ] Twilio 憑證已儲存到 Secret Manager
- [ ] `web-service` 部署到 Cloud Run
- [ ] `notification-service` 部署到 Cloud Run
- [ ] Custom domain `sales.ichefpos.com` 已設定
- [ ] SSL 憑證已配置

---

## 風險與緩解

### 風險 1: Slack API 限制

**風險**: Slack API 有 rate limit（每分鐘 60 個請求）

**緩解**:

- 實作 exponential backoff 重試
- 使用 Slack Bolt 內建的 rate limit 處理
- 監控 API 使用量

### 風險 2: SMS 成本

**風險**: SMS 發送失敗導致重複扣款

**緩解**:

- 記錄 smsSid 防止重複發送
- 實作 idempotency key
- 設定每日發送上限告警

### 風險 3: Transaction 並發問題

**風險**: 高並發時 Firestore Transaction 可能衝突

**緩解**:

- 使用 exponential backoff 重試
- 限制每個用戶的並發請求數
- 監控 Transaction 失敗率

---

## 成本預估

### 額外成本（相對於原計劃）

| 服務 | 月用量 | 單價 | 月成本 |
|------|--------|------|--------|
| **Cloud Run (web-service)** | 250 請求 × 0.5s | $0.00002400/vCPU-sec | $0.003 |
| **Cloud Run (notification-service)** | 250 請求 × 1s | $0.00002400/vCPU-sec | $0.006 |
| **SMS (Twilio)** | 250 則 × NT$2.5 | NT$2.5/則 | NT$625 (~$20) |
| **Slack API** | 免費 | $0 | $0 |
| **總計** | | | **~$20/月** |

**總成本**: $46.74 (原計劃) + $20 (Slack 相關) = **$66.74/月**

⚠️ **超出預算**: 原目標 $45/月，需調整或向用戶確認

**優化選項**:

1. 使用三竹資訊（NT$1.5/則）→ 節省 $5/月
2. 客戶自選 Email/SMS → 節省 50% SMS 成本

---

## 總結

**完成後交付**:

- ✅ 完整的 Slack DM 互動流程
- ✅ 防重複處理機制（Transaction 鎖定）
- ✅ 摘要編輯功能
- ✅ 客戶網頁（iCHEF branding）
- ✅ SMS 自動發送
- ✅ 錯誤處理與自動重試
- ✅ 完整測試套件（單元 + 整合 + E2E）

**文件**:

- ✅ slack-workflow.md（技術設計）
- ✅ slack-implementation-tasks.md（本文件）
- ✅ plan.md（更新）
- ✅ Firestore 資料結構定義

**下一步**: 開始 Sprint 5 實作 🚀
