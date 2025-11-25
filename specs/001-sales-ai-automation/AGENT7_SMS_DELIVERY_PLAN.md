# Agent 7 簡訊發送功能 - 實作規劃

**建立日期**：2025-11-12
**狀態**：規劃階段
**預估工期**：4 天
**預估成本**：~$14.4/月（250 案件）

---

## 📋 目錄

1. [功能概述](#功能概述)
2. [系統架構](#系統架構)
3. [技術選型](#技術選型)
4. [資料結構設計](#資料結構設計)
5. [實作階段](#實作階段)
6. [部署清單](#部署清單)
7. [驗收標準](#驗收標準)
8. [成本分析](#成本分析)

---

## 功能概述

### 目標

當業務確認 Agent 7 生成的客戶摘要後，系統自動：

1. **生成美觀的網頁版摘要**（託管在 Cloud Run）
2. **產生短網址**（自建短網址服務）
3. **透過簡訊發送短網址**給客戶
4. **追蹤簡訊發送狀態**（投遞成功/失敗）

### 使用者流程

```

業務 (Slack)
  ↓
點擊「✅ 確認送出」按鈕
  ↓
系統顯示確認 Modal（客戶電話、摘要預覽、簡訊內容）
  ↓
業務確認送出
  ↓
系統自動：
  1. 生成網頁（5 秒內）
  2. 建立短網址
  3. 發送簡訊（10 秒內）
  ↓
客戶收到簡訊
  ↓
點擊短網址查看摘要網頁

```

---

## 系統架構

### 整體架構圖

```

┌─────────────────────────────────────────────────────────────┐
│                         Slack App                            │
│  - agent7_notifier.py (發送預覽訊息)                         │
│  - summary_sender.py (處理確認送出)                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      Cloud Tasks Queue                       │
│  - summary-delivery-queue                                    │
│    Task 1: 生成網頁                                          │
│    Task 2: 發送簡訊 (延遲 10 秒)                             │
└─────────────────────────────────────────────────────────────┘
                    ↓                    ↓
        ┌───────────────────┐    ┌───────────────────┐
        │  Summary Webpage  │    │   SMS Service     │
        │  Service          │    │   - Twilio API    │
        │  - Cloud Run      │    │   - Cloud Run     │
        │  - Jinja2 模板    │    │   - Webhook       │
        └───────────────────┘    └───────────────────┘
                    ↓                    ↓
        ┌───────────────────┐    ┌───────────────────┐
        │  Short URL        │    │  Customer Phone   │
        │  Redirect Service │    │  (簡訊)           │
        │  - Cloud Run      │    └───────────────────┘
        └───────────────────┘
                    ↓
        ┌───────────────────┐
        │  Customer Browser │
        │  (查看摘要網頁)   │
        └───────────────────┘

```

### 服務列表

| 服務名稱 | 類型 | 職責 | 端點 |
|---------|------|------|------|
| **slack-app** | Cloud Run (現有) | Slack 互動處理 | `/slack/events` |
| **summary-webpage-service** | Cloud Run (新增) | 生成客戶摘要網頁 | `GET /summary/{case_id}/{token}`<br>`POST /generate/{case_id}` |
| **sms-service** | Cloud Run (新增) | 發送簡訊 | `POST /send`<br>`POST /webhook/delivery-status` |
| **short-url-service** | Cloud Run (新增) | 短網址重定向 | `GET /{short_code}` |

---

## 技術選型

### 1. 網頁託管方案

**選型：Cloud Run + Jinja2 動態生成**

| 方案 | 優點 | 缺點 | 選擇 |
|-----|------|------|------|
| Cloud Run + 動態生成 | 即時更新、可客製化、與現有架構一致 | 成本稍高 | ✅ **推薦** |
| Cloud Storage + 靜態 HTML | 成本低、簡單 | 需預先生成、不易更新 | ❌ |
| Firebase Hosting | 免費額度高 | 需額外管理 | ❌ |

### 2. 簡訊服務商

**選型：互動資通簡訊API21**

| 服務商 | 優點 | 缺點 | 費用/則 | 選擇 |
|-------|------|------|--------|------|
| **互動資通簡訊API21** | 台灣在地、API 規格明確、支援多種簡訊類型 | 需自行實作 HTTP 請求、無現成 SDK | 待確認 | ✅ **優先** |
| **Twilio** | 國際支援、Python SDK 完善、Webhook 通知 | 費用較高、非台灣在地服務 | ~$0.05 | ❌ 備選 |
| **三竹資訊** | 台灣在地、客服支援 | 主要針對台灣 | ~$0.03 | ❌ 備選 |
| AWS SNS | 與 AWS 整合 | 跨雲端管理複雜 | ~$0.04 | ❌ |

### 3. 短網址方案

**選型：自建短網址服務（Cloud Run）**

| 方案 | 優點 | 缺點 | 選擇 |
|-----|------|------|------|
| **自建 (Cloud Run)** | 完全控制、無外部依賴、與架構一致 | 需額外維護 | ✅ **推薦** |
| Firebase Dynamic Links | Google 官方、免費 | 2025/08/25 停止服務 | ❌ |
| Bitly API | 成熟穩定、分析豐富 | 付費、外部依賴 | ❌ |

**短網址格式**：`https://ichef.page/{short_code}` → 重定向至完整網址

---

## 資料結構設計

### Firestore Schema 更新

#### 1. Cases Collection 新增欄位

```javascript

cases/{caseId}
{
  // === 現有欄位（省略）===

  // === 新增：客戶摘要發送相關 ===
  "customerSummaryDelivery": {
    "status": "pending" | "generating_webpage" | "webpage_ready" | "sms_sent" | "delivered" | "failed",
    "customerPhone": "+886912345678",  // 確認的客戶電話
    "webPageUrl": "https://summary-webpage-service/.../...",  // 完整網址
    "shortUrl": "https://ichef.page/abc123",  // 短網址
    "accessToken": "random_secure_token_32_chars",  // 網頁存取 token
    "smsBatchId": "every8d_batch_id",  // 簡訊服務商批次 ID
    "smsSentAt": Timestamp,
    "smsDeliveredAt": Timestamp,
    "deliveryStatus": "sent" | "delivered" | "failed" | "bounced",
    "deliveryError": "錯誤訊息（如果失敗）",
    "confirmedBy": "U0BU3PESX",  // 確認送出的 Slack 使用者 ID
    "confirmedAt": Timestamp
  },

  // === 新增：追蹤網頁訪問 ===
  "webPageAnalytics": {
    "viewCount": 3,
    "lastViewedAt": Timestamp,
    "uniqueVisitors": ["ip_hash_1", "ip_hash_2"]  // 隱私考量：使用 hash
  }
}

```

#### 2. 新增 Collection：shortUrls

```javascript

shortUrls/{shortCode}
{
  "shortCode": "abc123",  // 6-8 字元隨機碼
  "targetUrl": "https://summary-webpage-service/summary/202511-IC008/token123",
  "caseId": "202511-IC008",
  "createdAt": Timestamp,
  "expiresAt": Timestamp,  // 30 天後過期（可選）
  "clickCount": 5,
  "lastClickedAt": Timestamp
}

```

---

## 實作階段

### Phase 1: Slack 互動處理（0.5 天）

#### Task 1.1: 更新 agent7_notifier.py

**檔案**：`src/slack_app/notifications/agent7_notifier.py`

**修改位置**：Line 173-180

**修改內容**：

```python
# 更新「確認送出」按鈕的警告訊息
blocks.append({
    "type": "context",
    "elements": [{
        "type": "mrkdwn",
        "text": "⚠️ 點擊「確認送出」後，系統將：\n1️⃣ 生成客戶摘要網頁\n2️⃣ 發送簡訊（含短網址）至客戶手機"
    }]
})

```

**驗收**：

- [ ] Slack 訊息顯示更新後的警告文字
- [ ] 按鈕功能正常（點擊後觸發 action）

#### Task 1.2: 建立 summary_sender.py

**檔案**：`src/slack_app/handlers/summary_sender.py`（新檔案）

**功能模組**：

1. **handle_confirm_send_summary()**
   - 接收「確認送出」按鈕點擊
   - 從 Firestore 讀取案件資料
   - 驗證客戶電話號碼
   - 開啟確認 Modal

2. **build_send_confirmation_modal()**
   - 建立確認 Modal UI
   - 顯示：客戶姓名、電話、摘要預覽、簡訊內容預覽
   - 提供「確認送出」和「取消」按鈕

3. **build_phone_input_modal()**
   - 當客戶電話為空或「待補」時顯示
   - 提供電話輸入欄位
   - 格式驗證（台灣手機號碼）

4. **handle_send_summary_confirmed()**
   - 處理 Modal 提交
   - 更新 Firestore 狀態
   - 建立 Cloud Tasks（呼叫 MCP）
   - 發送 Slack 確認訊息

**依賴**：

- Slack SDK
- Firestore Client
- MCP Cloud Tasks 工具

**驗收**：

- [ ] 點擊「確認送出」按鈕後顯示 Modal
- [ ] Modal 正確顯示客戶資料
- [ ] 電話號碼驗證正常
- [ ] Modal 提交後建立 Cloud Tasks
- [ ] Firestore 狀態更新正確

#### Task 1.3: 整合到 Slack App main.py

**檔案**：`src/slack_app/main.py`

**修改內容**：

```python

from handlers.summary_sender import (
    handle_confirm_send_summary,
    handle_send_summary_confirmed
)

# 註冊 action handler
@app.action("confirm_send_summary")
def confirm_send_action(ack, body, client):
    handle_confirm_send_summary(ack, body, client, db)

# 註冊 view submission handler
@app.view("send_summary_confirmed")
def send_confirmed_view(ack, body, view, client):
    handle_send_summary_confirmed(ack, body, view, client, db)

```

**驗收**：

- [ ] Slack App 啟動無錯誤
- [ ] Action handler 正確註冊
- [ ] 端到端測試通過

---

### Phase 2: 網頁生成服務（1 天）

#### Task 2.1: 建立服務目錄結構

**路徑**：`summary-webpage-service/`

**目錄結構**：

```

summary-webpage-service/
├── Dockerfile
├── requirements.txt
├── main.py
├── templates/
│   └── summary_template.html
├── static/
│   ├── css/
│   │   └── styles.css
│   └── img/
│       └── ichef_logo.png
└── cloudbuild.yaml

```

**檔案內容**：

**requirements.txt**：

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
jinja2==3.1.2
google-cloud-firestore==2.13.1
python-multipart==0.0.6

```

**Dockerfile**：

```dockerfile

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

```

**cloudbuild.yaml**：

```yaml

steps:

  - name: 'gcr.io/cloud-builders/docker'
    args:

      - 'build'
      - '-t'
      - 'asia-east1-docker.pkg.dev/sales-ai-automation-v2/sales-ai-automation-v2/summary-webpage-service:latest'
      - '.'

  - name: 'gcr.io/cloud-builders/docker'
    args:

      - 'push'
      - 'asia-east1-docker.pkg.dev/sales-ai-automation-v2/sales-ai-automation-v2/summary-webpage-service:latest'

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:

      - 'run'
      - 'deploy'
      - 'summary-webpage-service'
      - '--image=asia-east1-docker.pkg.dev/sales-ai-automation-v2/sales-ai-automation-v2/summary-webpage-service:latest'
      - '--region=asia-east1'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--set-env-vars=GCP_PROJECT_ID=sales-ai-automation-v2'

images:

  - 'asia-east1-docker.pkg.dev/sales-ai-automation-v2/sales-ai-automation-v2/summary-webpage-service:latest'

timeout: 1200s

```

**驗收**：

- [ ] 目錄結構建立完成
- [ ] 所有設定檔案就位

#### Task 2.2: 實作 main.py（FastAPI 應用）

**檔案**：`summary-webpage-service/main.py`

**端點列表**：

1. **GET /summary/{case_id}/{access_token}**
   - 驗證 access token
   - 從 Firestore 讀取案件資料
   - 渲染 HTML 模板
   - 更新訪問記錄
   - 返回 HTML 頁面

2. **POST /generate/{case_id}**
   - 生成 access token (32 字元)
   - 建立短網址
   - 更新 Firestore（webPageUrl, shortUrl, accessToken）
   - 返回 JSON（urls）

3. **GET /health**
   - 健康檢查端點

**關鍵函數**：

- `generate_access_token()` - 使用 `secrets.token_urlsafe(32)`
- `generate_short_code()` - 6-8 字元隨機碼（避免碰撞）
- `update_view_analytics()` - 更新訪問統計

**驗收**：

- [ ] 所有端點回應正常
- [ ] Access token 驗證有效
- [ ] Firestore 讀寫正確
- [ ] 錯誤處理完善（404, 403）

#### Task 2.3: 設計 HTML 模板

**檔案**：`summary-webpage-service/templates/summary_template.html`

**設計要求**：

- RWD 響應式設計（支援手機、平板、桌面）
- 清晰的視覺層次
- 專業的配色（iCHEF 品牌色）
- 可列印友好

**模板結構**：

```html

<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>會議摘要 - {{ store_name }}</title>
    <link rel="stylesheet" href="/static/css/styles.css">
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header>
            <img src="/static/img/ichef_logo.png" alt="iCHEF Logo">
            <h1>{{ store_name }} - 會議摘要</h1>
            <p class="date">{{ generated_at|format_date }}</p>
        </header>

        <!-- Summary Section -->
        <section class="summary">
            <h2>📝 摘要</h2>
            <p>{{ summary }}</p>
        </section>

        <!-- Key Decisions -->
        <section class="decisions">
            <h2>✅ 重點決議</h2>
            <ul>
            {% for decision in key_decisions %}
                <li>
                    <strong>{{ decision.title }}</strong>
                    <p class="quote">"{{ decision.quote }}"</p>
                    <p class="meta">— {{ decision.speakerId }} ({{ decision.timestamp }})</p>
                </li>
            {% endfor %}
            </ul>
        </section>

        <!-- Next Steps -->
        <section class="next-steps">
            <h2>🎯 下一步</h2>

            <h3>客戶待辦</h3>
            <ul>
            {% for step in next_steps.customer %}
                <li>
                    {{ step.description }}
                    <span class="owner">負責人：{{ step.owner }}</span>
                    <span class="due">期限：{{ step.dueDate }}</span>
                </li>
            {% endfor %}
            </ul>

            <h3>iCHEF 待辦</h3>
            <ul>
            {% for step in next_steps.ichef %}
                <li>
                    {{ step.description }}
                    <span class="owner">負責人：{{ step.owner }}</span>
                    <span class="due">期限：{{ step.dueDate }}</span>
                </li>
            {% endfor %}
            </ul>
        </section>

        <!-- Contacts -->
        <section class="contacts">
            <h2>📞 聯絡窗口</h2>
            <div class="contact-cards">
                <div class="card customer">
                    <h3>客戶方</h3>
                    <p><strong>{{ contacts.customer.name }}</strong></p>
                    <p>{{ contacts.customer.role }}</p>
                    {% if contacts.customer.phone %}
                    <p>📱 {{ contacts.customer.phone }}</p>
                    {% endif %}
                </div>
                <div class="card ichef">
                    <h3>iCHEF 方</h3>
                    <p><strong>{{ contacts.ichef.name }}</strong></p>
                    <p>{{ contacts.ichef.role }}</p>
                    <p>📧 {{ contacts.ichef.email }}</p>
                </div>
            </div>
        </section>

        <!-- Footer -->
        <footer>
            <p>由 iCHEF 銷售 AI 系統自動生成</p>
            <p>生成時間：{{ generated_at|format_datetime }}</p>
        </footer>
    </div>
</body>
</html>

```

**驗收**：

- [ ] 在手機上顯示正常
- [ ] 在平板上顯示正常
- [ ] 在桌面上顯示正常
- [ ] 列印版面友好
- [ ] 所有資料正確渲染

#### Task 2.4: 設計 CSS 樣式

**檔案**：`summary-webpage-service/static/css/styles.css`

**設計重點**：

- 使用 iCHEF 品牌色（橘色 #FF6B35）
- 清晰的字型（Noto Sans TC）
- 適當的留白和間距
- 卡片式設計

**驗收**：

- [ ] 視覺設計專業
- [ ] 配色協調
- [ ] 字體大小適中
- [ ] 列印樣式優化

---

### Phase 3: 簡訊發送服務（1 天）

#### Task 3.1: 建立服務目錄結構

**路徑**：`sms-service/`

**目錄結構**：

```

sms-service/
├── Dockerfile
├── requirements.txt
├── main.py
├── providers/
│   ├── __init__.py
│   ├── base.py
│   └── every8d_provider.py  # 互動資通簡訊API21
└── cloudbuild.yaml

```

**requirements.txt**：

```

fastapi==0.104.1
uvicorn[standard]==0.24.0
google-cloud-firestore==2.13.1
requests>=2.31.0 # For EVERY8D API calls
python-multipart==0.0.6

```

**驗收**：

- [ ] 目錄結構建立完成

#### Task 3.2: 實作 EVERY8D Provider

**檔案**：`sms-service/providers/base.py`

```python

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class SMSResult:
    success: bool
    batch_id: Optional[str] = None
    error: Optional[str] = None
    raw_response: Optional[str] = None

class SMSProvider(ABC):
    @abstractmethod
    def send_sms(self, to: str, message: str) -> SMSResult:
        """發送簡訊"""
        pass

```

**檔案**：`sms-service/providers/every8d_provider.py`

```python

import requests
import json
import logging
from .base import SMSProvider, SMSResult

logger = logging.getLogger(__name__)

class Every8dProvider(SMSProvider):
    def __init__(self, site_url: str, uid: str, pwd: str):
        self.site_url = site_url.rstrip('/')
        self.uid = uid
        self.pwd = pwd
        self.token = None # Token will be acquired on demand

    def _get_token(self) -> Optional[str]:
        """取得 EVERY8D 連線憑證"""
        url = f"{self.site_url}/API21/HTTP/ConnectionHandler.ashx"
        headers = {"Content-Type": "application/json"}
        payload = {
            "HandlerType": 3,
            "VerifyType": 1,
            "UID": self.uid,
            "PWD": self.pwd
        }
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
            response.raise_for_status()
            result = response.json()
            if result.get("Result"):
                self.token = result.get("Msg")
                logger.info("Successfully acquired EVERY8D token.")
                return self.token
            else:
                logger.error("Failed to acquire EVERY8D token: %s", result.get("Msg"))
                return None
        except requests.exceptions.RequestException as e:
            logger.error("Request error acquiring EVERY8D token: %s", e)
            return None
        except json.JSONDecodeError:
            logger.error("JSON decode error from EVERY8D token response: %s", response.text)
            return None

    def send_sms(self, to: str, message: str) -> SMSResult:
        """
        使用 EVERY8D API 發送一般簡訊 (SendSMS.ashx)。
        目前僅支援單一收件人。
        """
        if not self.token:
            self._get_token()
        if not self.token:
            return SMSResult(success=False, error="Failed to get EVERY8D token.", raw_response="No token")

        url = f"{self.site_url}/API21/HTTP/SendSMS.ashx"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        payload = {
            "UID": self.uid,
            "PWD": self.pwd, # PWD is also required for SendSMS.ashx
            "MSG": message,
            "DEST": to,
            "SB": "iCHEF會議摘要", # Subject for internal tracking
            "RETRYTIME": 1440, # 24 hours validity
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
            response.raise_for_status()
            result_str = response.text # EVERY8D returns plain text for success/failure
            
            # Parse the plain text response
            # Success example: "9610040.00,2,2,0,c496f706-9b0f-4ff8-9644-9503edbb7064"
            # Failure example: "-99,發生不明錯誤"
            parts = result_str.split(',')
            if len(parts) > 4 and parts[0].replace('.', '', 1).isdigit(): # Check if it looks like a success response
                batch_id = parts[4].strip()
                logger.info("EVERY8D SMS sent successfully to %s, Batch ID: %s", to, batch_id)
                return SMSResult(success=True, batch_id=batch_id, raw_response=result_str)
            else:
                error_msg = result_str
                logger.error("EVERY8D SMS failed to %s: %s", to, error_msg)
                return SMSResult(success=False, error=error_msg, raw_response=result_str)

        except requests.exceptions.RequestException as e:
            logger.error("Request error sending EVERY8D SMS to %s: %s", to, e)
            return SMSResult(success=False, error=str(e), raw_response=str(e))
        except Exception as e:
            logger.error("Unexpected error sending EVERY8D SMS to %s: %s", to, e)
            return SMSResult(success=False, error=str(e), raw_response=str(e))

```

**驗收**：

- [ ] EVERY8D API 整合成功
- [ ] Token 獲取機制正常
- [ ] 發送簡訊功能正常
- [ ] 錯誤處理完善，並返回 EVERY8D 的批次 ID

#### Task 3.3: 實作 FastAPI 端點

**檔案**：`sms-service/main.py`

**端點列表**：

1. **POST /send**
   - 從 request body 讀取 case_id
   - 從 Firestore 讀取案件資料
   - 組合簡訊內容
   - 呼叫 EVERY8D API 發送
   - 更新 Firestore 狀態
   - 返回發送結果

2. **GET /health**
   - 健康檢查

**簡訊內容模板**：

```python

SMS_TEMPLATE = """【iCHEF】您好 {customer_name}，

感謝今日與 {sales_rep_name} 的會議討論。

會議摘要已準備好，請點擊以下連結查看：
{short_url}

如有任何問題，歡迎隨時聯繫。

iCHEF 團隊 敬上"""

```

**驗收**：

- [ ] 簡訊發送成功
- [ ] Firestore 狀態更新正確
- [ ] 投遞狀態追蹤正確 (透過 EVERY8D API 查詢)

#### Task 3.4: 環境變數與 Secret 設定

**Secret Manager 設定**：

```bash
# 建立 EVERY8D secrets
gcloud secrets create every8d-site-url --data-file=- <<< "https://api.e8d.tw"
gcloud secrets create every8d-uid --data-file=- <<< "YOUR_EVERY8D_UID"
gcloud secrets create every8d-pwd --data-file=- <<< "YOUR_EVERY8D_PWD"

```

**cloudbuild.yaml 設定**：

```yaml

- '--set-secrets=EVERY8D_SITE_URL=every8d-site-url:latest,EVERY8D_UID=every8d-uid:latest,EVERY8D_PWD=every8d-pwd:latest'

```

**驗收**：

- [ ] Secrets 建立成功
- [ ] Cloud Run 可讀取 secrets
- [ ] 敏感資訊不外洩

---

### Phase 4: Cloud Tasks 整合（0.5 天）

#### Task 4.1: 建立 Cloud Tasks Queue

**指令**：

```bash

gcloud tasks queues create summary-delivery-queue \
  --location=asia-east1 \
  --max-concurrent-dispatches=10 \
  --max-attempts=3 \
  --min-backoff=10s \
  --max-backoff=300s

```

**驗收**：

- [ ] Queue 建立成功
- [ ] 參數設定正確

#### Task 4.2: 更新 MCP Server

**檔案**：`tools/cloud_tasks/mcp_server.py`

**新增函數**：

```python

def create_summary_delivery_tasks(
    case_id: str,
    project: str = "sales-ai-automation-v2",
    location: str = "asia-east1"
):
    """
    建立客戶摘要發送任務鏈

    Task 1: 生成網頁
    Task 2: 發送簡訊（延遲 10 秒）
    """
    client = tasks_v2.CloudTasksClient()
    queue_path = client.queue_path(project, location, "summary-delivery-queue")

    # Task 1: 生成網頁
    webpage_task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": f"https://summary-webpage-service-{hash}.asia-east1.run.app/generate/{case_id}",
            "oidc_token": {
                "service_account_email": f"{project_number}-compute@developer.gserviceaccount.com"
            }
        }
    }

    webpage_response = client.create_task(parent=queue_path, task=webpage_task)

    # Task 2: 發送簡訊
    import time
    sms_task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": f"https://sms-service-{hash}.asia-east1.run.app/send",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"case_id": case_id}).encode(),
            "oidc_token": {
                "service_account_email": f"{project_number}-compute@developer.gserviceaccount.com"
            }
        },
        "schedule_time": {"seconds": int(time.time()) + 10}
    }

    sms_response = client.create_task(parent=queue_path, task=sms_task)

    return {
        "webpage_task_name": webpage_response.name,
        "sms_task_name": sms_response.name
    }

```

**MCP Tool Definition**：

```python

TOOL_DEFINITIONS.append({
    "name": "create_summary_delivery_tasks",
    "description": "建立客戶摘要發送任務鏈（生成網頁 + 發送簡訊）",
    "inputSchema": {
        "type": "object",
        "properties": {
            "case_id": {"type": "string", "description": "案件 ID"},
            "project": {"type": "string", "default": "sales-ai-automation-v2"},
            "location": {"type": "string", "default": "asia-east1"}
        },
        "required": ["case_id"]
    }
})

```

**驗收**：

- [ ] MCP 工具註冊成功
- [ ] 測試呼叫正常
- [ ] Cloud Tasks 建立成功

#### Task 4.3: 整合到 Slack Handler

**檔案**：`src/slack_app/handlers/summary_sender.py`

**修改 handle_send_summary_confirmed()**：

```python

def handle_send_summary_confirmed(ack, body, view, client, db):
    # ... 前面的程式碼 ...

    # 建立 Cloud Tasks
    import subprocess
    import json

    mcp_request = {
        "method": "tools/call",
        "params": {
            "name": "create_summary_delivery_tasks",
            "arguments": {"case_id": case_id}
        }
    }

    result = subprocess.run(
        ["python3", "tools/cloud_tasks/mcp_server.py"],
        input=json.dumps(mcp_request),
        capture_output=True,
        text=True
    )

    task_result = json.loads(result.stdout)

    # 發送確認訊息
    client.chat_postMessage(
        channel=body["user"]["id"],
        text=f"✅ 客戶摘要發送流程已啟動（案件：{case_id}）\n\n" +
             f"📄 網頁生成任務：{task_result['webpage_task_name']}\n" +
             f"📱 簡訊發送任務：{task_result['sms_task_name']}"
    )

```

**驗收**：

- [ ] Modal 提交後建立 Cloud Tasks
- [ ] Slack 訊息顯示任務資訊
- [ ] 端到端流程正常

---

### Phase 5: 測試與部署（1 天）

#### Task 5.1: 單元測試

**測試檔案**：

- `summary-webpage-service/tests/test_main.py`
- `sms-service/tests/test_providers.py`
- `sms-service/tests/test_main.py`

**測試覆蓋**：

- [ ] HTML 模板渲染測試
- [ ] Access token 驗證測試
- [ ] 簡訊發送測試（mock Twilio）
- [ ] Firestore 讀寫測試
- [ ] 錯誤處理測試

#### Task 5.2: 整合測試

**測試場景**：

1. **正常流程測試**
   - [ ] 點擊「確認送出」→ 顯示 Modal
   - [ ] Modal 提交 → 建立 Cloud Tasks
   - [ ] Cloud Task 1 執行 → 生成網頁和短網址
   - [ ] Cloud Task 2 執行 → 發送簡訊
   - [ ] 客戶點擊短網址 → 查看摘要網頁
   - [ ] Webhook 回調 → 更新投遞狀態

2. **錯誤處理測試**
   - [ ] 客戶電話為空 → 顯示輸入 Modal
   - [ ] 客戶電話格式錯誤 → 顯示錯誤訊息
   - [ ] Firestore 讀取失敗 → 錯誤處理
   - [ ] Twilio API 失敗 → 記錄錯誤、重試
   - [ ] Access token 錯誤 → 返回 403

3. **邊界測試**
   - [ ] 摘要內容過長 → 正確截斷或換頁
   - [ ] 簡訊內容超過限制 → 正確處理
   - [ ] 並發訪問網頁 → 效能正常
   - [ ] 過期的短網址 → 顯示提示訊息

#### Task 5.3: 部署到 Production

**部署清單**：

1. **部署 summary-webpage-service**

   ```bash

   cd summary-webpage-service
   gcloud builds submit --config cloudbuild.yaml

   ```

2. **部署 sms-service**

   ```bash

   cd sms-service
   gcloud builds submit --config cloudbuild.yaml

   ```

3. **部署 slack-app（更新版）**

   ```bash

   gcloud builds submit --config cloudbuild.slack.yaml

   ```

4. **更新 MCP config**

   ```bash
   # 測試 MCP 工具
   echo '{"method": "tools/call", "params": {"name": "create_summary_delivery_tasks", "arguments": {"case_id": "TEST-001"}}}' | python3 tools/cloud_tasks/mcp_server.py

   ```

5. **驗證服務 URL**

   ```bash
   # 檢查所有服務是否正常運行
   gcloud run services list --platform managed --region asia-east1

   ```

**驗收**：

- [ ] 所有服務部署成功
- [ ] 健康檢查通過
- [ ] 服務間可正常通訊
- [ ] IAM 權限設定正確

#### Task 5.4: Production 驗證

**驗證步驟**：

1. **建立測試案件**
   - [ ] 上傳測試音檔
   - [ ] 完成 Agent 1-7 分析
   - [ ] 確認 customerSummary 存在

2. **測試簡訊發送流程**
   - [ ] 點擊「確認送出」按鈕
   - [ ] 確認 Modal 顯示
   - [ ] 輸入測試手機號碼
   - [ ] 提交並等待簡訊

3. **驗證網頁**
   - [ ] 收到簡訊
   - [ ] 點擊短網址
   - [ ] 網頁正確顯示
   - [ ] 手機版顯示正常

4. **檢查 Firestore**
   - [ ] `customerSummaryDelivery.status` = "delivered"
   - [ ] `webPageUrl` 正確
   - [ ] `shortUrl` 正確
   - [ ] `smsMessageId` 存在

5. **監控日誌**

   ```bash
   # 檢查 summary-webpage-service 日誌
   gcloud logging read 'resource.type="cloud_run_revision" resource.labels.service_name="summary-webpage-service"' --limit 50

   # 檢查 sms-service 日誌
   gcloud logging read 'resource.type="cloud_run_revision" resource.labels.service_name="sms-service"' --limit 50

   ```

**驗收**：

- [ ] 端到端流程完整通過
- [ ] 無錯誤日誌
- [ ] 效能符合預期（生成 < 5s, 發送 < 10s）

---

## 部署清單

### 環境準備

- [ ] EVERY8D 帳號申請與設定
- [ ] 取得 EVERY8D Site URL, UID, PWD
- [ ] 建立 GCP Secret Manager secrets
- [ ] 準備短網址 domain（或使用現有 domain）

### GCP 資源建立

- [ ] 建立 Cloud Tasks Queue: `summary-delivery-queue`
- [ ] 設定 Service Account 權限
- [ ] 建立 Artifact Registry（如未存在）

### 服務部署順序

1. [ ] `summary-webpage-service` - 網頁生成服務
2. [ ] `sms-service` - 簡訊發送服務
3. [ ] `slack-app` - 更新 Slack 應用（含新 handlers）
4. [ ] 更新 MCP Server 工具定義

### 設定驗證

- [ ] 所有服務的 URL 正確設定
- [ ] IAM 權限設定完成
- [ ] Secret Manager 可正常存取
- [ ] Cloud Tasks 可正常建立與執行

---

## 驗收標準

### 功能驗收

#### Slack 互動

- [ ] 點擊「✅ 確認送出」按鈕後顯示確認 Modal
- [ ] Modal 正確顯示客戶電話、摘要預覽、簡訊內容
- [ ] 客戶電話為空時，顯示輸入 Modal
- [ ] 電話號碼格式驗證正常
- [ ] Modal 提交後顯示確認訊息

#### 網頁生成

- [ ] 網頁生成時間 < 5 秒
- [ ] 網頁內容完整（摘要、決議、下一步、聯絡人）
- [ ] 網頁 RWD 響應式設計正常（手機、平板、桌面）
- [ ] Access token 驗證有效
- [ ] 短網址生成成功
- [ ] 短網址重定向正確

#### 簡訊發送

- [ ] 簡訊發送時間 < 10 秒（從 Modal 提交算起）
- [ ] 簡訊內容包含短網址
- [ ] 簡訊成功發送至客戶手機
- [ ] 投遞狀態追蹤正常（webhook 回調）

#### 資料記錄

- [ ] Firestore `customerSummaryDelivery` 所有欄位正確記錄
- [ ] `webPageAnalytics` 訪問統計正常
- [ ] `shortUrls` collection 資料正確
- [ ] Slack 通知訊息顯示完整資訊

### 非功能驗收

#### 效能

- [ ] 網頁生成時間 < 5 秒
- [ ] 簡訊發送時間 < 10 秒
- [ ] 網頁訪問速度 < 2 秒
- [ ] 短網址重定向速度 < 500ms
- [ ] 支援 100+ 並發訪問

#### 穩定性

- [ ] 錯誤處理完善（電話錯誤、API 失敗等）
- [ ] 重試機制正常（Cloud Tasks 重試）
- [ ] 降級處理（簡訊失敗時的備案）
- [ ] 日誌記錄完整

#### 安全性

- [ ] Access token 長度 32 字元以上
- [ ] Access token 無法預測
- [ ] 短網址無法枚舉
- [ ] Secrets 管理正確（不外洩）

#### 使用者體驗

- [ ] Slack 訊息清晰易懂
- [ ] Modal 介面友好
- [ ] 網頁設計專業美觀
- [ ] 手機瀏覽體驗良好
- [ ] 錯誤訊息清楚

---

## 成本分析

### 月費用估算（基於 250 案件/月）

| 服務項目 | 單價 | 用量 | 月費用 |
|---------|------|------|--------|
| **Cloud Run - summary-webpage-service** | | | |
| └ CPU 時間 | $0.00002400/vCPU-秒 | 250 次生成 × 2s | $0.01 |
| └ 記憶體 | $0.00000250/GiB-秒 | 250 次 × 0.5GiB × 2s | $0.001 |
| └ 請求數 | $0.40/百萬次 | 1,000 次（含訪問） | $0.0004 |
| **Cloud Run - sms-service** | | | |
| └ CPU 時間 | $0.00002400/vCPU-秒 | 250 次 × 1s | $0.006 |
| └ 記憶體 | $0.00000250/GiB-秒 | 250 次 × 0.5GiB × 1s | $0.0003 |
| └ 請求數 | $0.40/百萬次 | 500 次（含 webhook） | $0.0002 |
| **Firestore** | | | |
| └ 文件寫入 | $0.18/十萬次 | 1,500 次 | $0.003 |
| └ 文件讀取 | $0.06/十萬次 | 1,500 次 | $0.001 |
| └ 儲存 | $0.18/GiB | 0.1 GiB | $0.018 |
| **Cloud Tasks** | | | |
| └ 任務執行 | 免費（前 100 萬次） | 500 次 | $0 |
| **Cloud Storage（如使用）** | | | |
| └ 儲存 | $0.020/GiB | 0.5 GiB | $0.01 |
| **EVERY8D 簡訊費用** | | | |
| └ 簡訊發送 | 待確認 | 250 則 | **待確認** |
| **其他** | | | |
| └ 網路流量 | $0.12/GiB | 1 GiB | $0.12 |
| **總計** | | | **待確認** |

### 成本優化建議

1. **簡訊費用優化**（最大成本項）
   - 評估 EVERY8D 簡訊費用，若有更高性價比的方案可考慮
   - 實作簡訊批次發送（如適用）
   - 提供 Email 替代選項（成本極低）

2. **Cloud Run 優化**
   - 設定最小實例為 0（節省閒置成本）
   - 優化 CPU 和記憶體配置
   - 使用 Cloud Run gen2（更高效）

3. **Firestore 優化**
   - 批次讀寫操作
   - 使用 cache 減少重複讀取
   - 定期清理過期資料

### 成本擴展分析

| 月案件數 | EVERY8D 簡訊費 | GCP 服務費 | 總費用 |
|---------|--------------|-----------|--------|
| 100 | 待確認 | $0.70 | **待確認** |
| 250 | 待確認 | $1.75 | **待確認** |
| 500 | 待確認 | $3.50 | **待確認** |
| 1000 | 待確認 | $7.00 | **待確認** |

**關鍵發現**：簡訊費用佔總成本 85-90%，優化重點應放在簡訊服務商選擇。

---

## 附錄

### A. 簡訊內容範本

```

【iCHEF】您好 {{ customer_name }}，

感謝今日與 {{ sales_rep_name }} 的會議討論。

會議摘要已準備好，請點擊以下連結查看：
{{ short_url }}

如有任何問題，歡迎隨時聯繫。

iCHEF 團隊 敬上

```

**字數統計**：

- 固定文字：約 50 個中文字
- 變數長度：

  - customer_name: 2-4 字
  - sales_rep_name: 2-4 字
  - short_url: 25 字元
- **總計**：約 65-70 個中文字（符合 70 字簡訊限制）

### B. 短網址生成邏輯

```python

import secrets
import string

def generate_short_code(length: int = 7) -> str:
    """
    生成短網址碼

    使用 Base62 編碼（a-z, A-Z, 0-9）
    7 個字元 = 62^7 = 3.5 兆種組合（碰撞機率極低）
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def check_collision(short_code: str, db: firestore.Client) -> bool:
    """檢查短網址是否已存在"""
    doc = db.collection('shortUrls').document(short_code).get()
    return doc.exists

def generate_unique_short_code(db: firestore.Client, max_attempts: int = 5) -> str:
    """生成唯一的短網址碼"""
    for _ in range(max_attempts):
        code = generate_short_code()
        if not check_collision(code, db):
            return code
    raise Exception("無法生成唯一短網址碼")

```

### D. 錯誤代碼定義

| 錯誤代碼 | 說明 | 處理方式 |
|---------|------|---------|
| `SMS_001` | 客戶電話為空 | 顯示輸入 Modal |
| `SMS_002` | 電話格式錯誤 | 顯示格式提示 |
| `SMS_003` | Firestore 讀取失敗 | 重試 3 次，失敗後通知業務 |
| `SMS_004` | 網頁生成失敗 | 記錄錯誤，通知業務 |
| `SMS_005` | 短網址生成失敗 | 使用完整 URL 作為 fallback |
| `SMS_006` | Twilio API 失敗 | 重試 3 次，記錄錯誤 |
| `SMS_007` | 簡訊投遞失敗 | 通知業務，建議改用 Email |

---

**文件版本**：1.0
**最後更新**：2025-11-12
**維護者**：Sales AI Team
