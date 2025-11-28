# Agent 7 簡訊發送功能 - 任務清單

**建立日期**：2025-11-12
**總工期**：4 天
**優先級**：Medium

> **參考文件**：`AGENT7_SMS_DELIVERY_PLAN.md` - 完整實作規劃

---

## 📊 進度總覽

| 階段 | 任務數 | 完成數 | 進度 | 預估時間 |
|-----|-------|-------|------|---------|
| Phase 1: Slack 互動 | 3 | 0 | 0% | 0.5 天 |
| Phase 2: 網頁服務 | 4 | 0 | 0% | 1 天 |
| Phase 3: 簡訊服務 | 4 | 0 | 0% | 1 天 |
| Phase 4: Cloud Tasks | 3 | 0 | 0% | 0.5 天 |
| Phase 5: 測試部署 | 4 | 0 | 0% | 1 天 |
| **總計** | **18** | **0** | **0%** | **4 天** |

---

## Phase 1: Slack 互動處理（0.5 天）

### Task 1.1: 更新 agent7_notifier.py

**檔案**：`src/slack_app/notifications/agent7_notifier.py`
**預估時間**：0.5 小時
**優先級**：Low
**依賴**：無

**詳細步驟**：

1. 開啟檔案 `src/slack_app/notifications/agent7_notifier.py`
2. 找到 Line 173-180（「確認送出」按鈕的警告訊息）
3. 修改內容為：

   ```python

   blocks.append({
       "type": "context",
       "elements": [{
           "type": "mrkdwn",
           "text": "⚠️ 點擊「確認送出」後，系統將：\n1️⃣ 生成客戶摘要網頁\n2️⃣ 發送簡訊（含短網址）至客戶手機"
       }]
   })

   ```

4. 儲存檔案

**驗收標準**：

- [ ] 檔案修改完成
- [ ] Slack 訊息顯示新的警告文字
- [ ] 按鈕功能不受影響

**測試指令**：

```bash
# 重新部署 slack-app
gcloud builds submit --config deploy/slack/cloudbuild.slack.yaml

```

---

### Task 1.2: 建立 summary_sender.py

**檔案**：`src/slack_app/handlers/summary_sender.py`（新檔案）
**預估時間**：2 小時
**優先級**：High
**依賴**：無

**詳細步驟**：

1. 建立新檔案 `src/slack_app/handlers/summary_sender.py`

2. 實作以下函數（依序）：

   **a. handle_confirm_send_summary()**

   ```python

   def handle_confirm_send_summary(ack, body, client: WebClient, db: firestore.Client):
       """處理「確認送出」按鈕點擊"""
       # 1. ack() 立即回應
       # 2. 從 action value 解析 case_id
       # 3. 從 Firestore 讀取案件資料
       # 4. 驗證客戶電話
       # 5. 如果電話為空或「待補」→ 開啟輸入 Modal
       # 6. 否則 → 開啟確認 Modal
   ```

   **b. build_send_confirmation_modal()**

   ```python

   def build_send_confirmation_modal(
       case_id: str,
       customer_name: str,
       customer_phone: str,
       summary_preview: str
   ) -> dict:
       """建立確認送出 Modal"""
       # 返回 Slack Modal JSON 結構
       # - 顯示客戶姓名、電話
       # - 顯示摘要預覽（前 200 字）
       # - 顯示簡訊內容預覽
       # - 提供「確認送出」和「取消」按鈕
   ```

   **c. build_phone_input_modal()**

   ```python

   def build_phone_input_modal(case_id: str, customer_name: str) -> dict:
       """建立電話輸入 Modal"""
       # 返回 Slack Modal JSON 結構
       # - 電話輸入欄位（placeholder: +886912345678）
       # - 格式說明
       # - 提交按鈕
   ```

   **d. handle_send_summary_confirmed()**

   ```python

   def handle_send_summary_confirmed(ack, body, view, client: WebClient, db: firestore.Client):
       """處理確認送出 Modal 提交"""
       # 1. ack() 立即回應
       # 2. 從 view metadata 取得 case_id
       # 3. 更新 Firestore 狀態
       # 4. 建立 Cloud Tasks（呼叫 MCP）
       # 5. 發送 Slack 確認訊息
   ```

3. 加入必要的 imports：

   ```python

   from slack_sdk import WebClient
   from google.cloud import firestore
   import logging
   import subprocess
   import json

   ```

**驗收標準**：

- [ ] 所有函數實作完成
- [ ] 程式碼無語法錯誤
- [ ] 加入適當的錯誤處理
- [ ] 加入 logging

**測試方法**：

- 單元測試（可選）
- 整合測試（在 Task 1.3 完成後）

---

### Task 1.3: 整合到 Slack App main.py

**檔案**：`src/slack_app/main.py`
**預估時間**：0.5 小時
**優先級**：High
**依賴**：Task 1.2

**詳細步驟**：

1. 在 `src/slack_app/main.py` 頂部加入 import：

   ```python

   from handlers.summary_sender import (
       handle_confirm_send_summary,
       handle_send_summary_confirmed
   )

   ```

2. 註冊 action handler（在現有 handlers 後面）：

   ```python

   @app.action("confirm_send_summary")
   def confirm_send_action(ack, body, client):
       handle_confirm_send_summary(ack, body, client, db)

   ```

3. 註冊 view submission handler：

   ```python

   @app.view("send_summary_confirmed")
   def send_confirmed_view(ack, body, view, client):
       handle_send_summary_confirmed(ack, body, view, client, db)

   ```

4. 如果需要處理電話輸入 Modal：

   ```python

   @app.view("phone_input_modal")
   def phone_input_view(ack, body, view, client):
       handle_phone_input_submission(ack, body, view, client, db)

   ```

5. 測試 Slack App 啟動：

   ```bash

   python src/slack_app/main.py

   ```

**驗收標準**：

- [ ] Import 無錯誤
- [ ] Handlers 正確註冊
- [ ] Slack App 啟動無錯誤
- [ ] 日誌顯示 handlers 載入成功

**測試指令**：

```bash
# 本地測試
python src/slack_app/main.py

# 部署測試
gcloud builds submit --config deploy/slack/cloudbuild.slack.yaml

```

---

## Phase 2: 網頁生成服務（1 天）

### Task 2.1: 建立服務目錄結構

**路徑**：`summary-webpage-service/`
**預估時間**：0.5 小時
**優先級**：High
**依賴**：無

**詳細步驟**：

1. 建立目錄結構：

   ```bash

   mkdir -p summary-webpage-service/{templates,static/{css,img}}
   cd summary-webpage-service

   ```

2. 建立 `requirements.txt`：

   ```txt

   fastapi==0.104.1
   uvicorn[standard]==0.24.0
   jinja2==3.1.2
   google-cloud-firestore==2.13.1
   python-multipart==0.0.6

   ```

3. 建立 `Dockerfile`：

   ```dockerfile

   FROM python:3.11-slim

   WORKDIR /app

   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   COPY . .

   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

   ```

4. 建立 `cloudbuild.yaml`（參考 `AGENT7_SMS_DELIVERY_PLAN.md` 中的範本）

5. 建立 `.dockerignore`：

   ```

   __pycache__
   *.pyc
   *.pyo
   *.pyd
   .git
   tests/

   ```

**驗收標準**：

- [ ] 目錄結構正確
- [ ] 所有設定檔就位
- [ ] Docker 可以建置（本地測試）

**測試指令**：

```bash
# 測試 Docker 建置
docker build -t summary-webpage-service:test .

```

---

### Task 2.2: 實作 main.py（FastAPI 應用）

**檔案**：`summary-webpage-service/main.py`
**預估時間**：3 小時
**優先級**：High
**依賴**：Task 2.1

**詳細步驟**：

1. 建立基礎 FastAPI 應用：

   ```python

   from fastapi import FastAPI, HTTPException, Request
   from fastapi.responses import HTMLResponse
   from fastapi.templating import Jinja2Templates
   from fastapi.staticfiles import StaticFiles
   from google.cloud import firestore
   import secrets
   import logging

   app = FastAPI(title="Summary Webpage Service")
   templates = Jinja2Templates(directory="templates")
   app.mount("/static", StaticFiles(directory="static"), name="static")

   db = firestore.Client()
   logger = logging.getLogger(__name__)

   ```

2. 實作端點：

   **a. GET /health**

   ```python

   @app.get("/health")
   async def health_check():
       return {"status": "healthy", "service": "summary-webpage-service"}

   ```

   **b. GET /summary/{case_id}/{access_token}**

   ```python

   @app.get("/summary/{case_id}/{access_token}", response_class=HTMLResponse)
   async def get_summary(case_id: str, access_token: str, request: Request):
       # 1. 從 Firestore 讀取案件
       # 2. 驗證 access_token
       # 3. 取得 customerSummary 資料
       # 4. 更新訪問統計
       # 5. 渲染 HTML 模板
       # 6. 返回 HTML
   ```

   **c. POST /generate/{case_id}**

   ```python

   @app.post("/generate/{case_id}")
   async def generate_summary_page(case_id: str):
       # 1. 生成 access_token（32 字元）
       # 2. 生成 short_code（7 字元）
       # 3. 建立完整 URL
       # 4. 建立短網址
       # 5. 更新 Firestore（案件 + shortUrls collection）
       # 6. 返回 JSON
   ```

3. 實作輔助函數：

   **a. generate_access_token()**

   ```python

   def generate_access_token(length: int = 32) -> str:
       return secrets.token_urlsafe(length)

   ```

   **b. generate_short_code()**

   ```python

   def generate_short_code(length: int = 7) -> str:
       import string
       alphabet = string.ascii_letters + string.digits
       return ''.join(secrets.choice(alphabet) for _ in range(length))

   ```

   **c. check_short_code_collision()**

   ```python

   def check_short_code_collision(code: str, db: firestore.Client) -> bool:
       doc = db.collection('shortUrls').document(code).get()
       return doc.exists

   ```

4. 加入錯誤處理：

   - 404：案件不存在
   - 403：Access token 錯誤
   - 500：內部錯誤

**驗收標準**：

- [ ] 所有端點實作完成
- [ ] 錯誤處理完善
- [ ] Firestore 讀寫正確
- [ ] Logging 完整

**測試指令**：

```bash
# 本地啟動
uvicorn main:app --reload --port 8080

# 測試端點
curl http://localhost:8080/health

```

---

### Task 2.3: 設計 HTML 模板

**檔案**：`summary-webpage-service/templates/summary_template.html`
**預估時間**：2 小時
**優先級**：Medium
**依賴**：Task 2.2

**詳細步驟**：

1. 建立基礎 HTML 結構（參考 `AGENT7_SMS_DELIVERY_PLAN.md` 中的範本）

2. 加入 Jinja2 模板語法：

   - 使用 `{{ variable }}` 顯示變數
   - 使用 `{% for %}` 迴圈渲染列表
   - 使用 `{% if %}` 條件顯示

3. 確保包含以下區塊：

   - Header（Logo、標題、日期）
   - Summary（摘要）
   - Key Decisions（重點決議）
   - Next Steps（下一步）
   - Contacts（聯絡窗口）
   - Footer（生成時間）

4. 加入 RWD meta tags：

   ```html

   <meta name="viewport" content="width=device-width, initial-scale=1.0">

   ```

**驗收標準**：

- [ ] HTML 結構完整
- [ ] Jinja2 語法正確
- [ ] 測試資料可正確渲染
- [ ] 無 HTML 驗證錯誤

**測試方法**：

- 使用測試資料渲染模板
- 在瀏覽器中檢視

---

### Task 2.4: 設計 CSS 樣式

**檔案**：`summary-webpage-service/static/css/styles.css`
**預估時間**：2.5 小時
**優先級**：Medium
**依賴**：Task 2.3

**詳細步驟**：

1. 設計基礎樣式：

   ```css

   /* 字型 */
   @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap');

   body {
       font-family: 'Noto Sans TC', sans-serif;
       line-height: 1.6;
       color: #333;
       max-width: 800px;
       margin: 0 auto;
       padding: 20px;
   }

   ```

2. 設計區塊樣式：

   - Header（品牌色、大標題）
   - Section（卡片式設計、陰影）
   - List（清晰的項目符號）
   - Footer（置底、小字）

3. 加入 RWD：

   ```css

   @media (max-width: 768px) {
       /* 手機版樣式 */
   }

   @media print {
       /* 列印版樣式 */
   }

   ```

4. 使用 iCHEF 品牌色：

   - 主色：`#FF6B35`
   - 輔助色：`#004E89`
   - 背景色：`#F7F7F7`

**驗收標準**：

- [ ] 桌面版顯示美觀
- [ ] 手機版顯示友好
- [ ] 列印版面正確
- [ ] 配色協調專業

**測試方法**：

- Chrome DevTools 測試各種螢幕尺寸
- 實際手機測試
- 列印預覽

---

## Phase 3: 簡訊發送服務（1 天）

### Task 3.1: 建立服務目錄結構

**路徑**：`sms-service/`
**預估時間**：0.5 小時
**優先級**：High
**依賴**：無

**詳細步驟**：

1. 建立目錄結構：

   ```bash

   mkdir -p sms-service/providers
   cd sms-service

   ```

2. 建立 `requirements.txt`：

   ```txt

   fastapi==0.104.1
   uvicorn[standard]==0.24.0
   google-cloud-firestore==2.13.1
   twilio==8.10.0
   python-multipart==0.0.6

   ```

3. 建立 `Dockerfile`（同 Task 2.1）

4. 建立 `cloudbuild.yaml`

5. 建立 `providers/__init__.py`（空檔案）

**驗收標準**：

- [ ] 目錄結構正確
- [ ] 設定檔就位

---

### Task 3.2: 實作 Twilio Provider

**檔案**：

- `sms-service/providers/base.py`
- `sms-service/providers/twilio_provider.py`

**預估時間**：1.5 小時
**優先級**：High
**依賴**：Task 3.1

**詳細步驟**：

1. 建立 `providers/base.py`：

   ```python

   from abc import ABC, abstractmethod
   from dataclasses import dataclass
   from typing import Optional

   @dataclass
   class SMSResult:
       success: bool
       message_id: Optional[str] = None
       error: Optional[str] = None

   class SMSProvider(ABC):
       @abstractmethod
       def send_sms(self, to: str, message: str) -> SMSResult:
           pass

   ```

2. 建立 `providers/twilio_provider.py`：

   ```python

   from twilio.rest import Client
   from .base import SMSProvider, SMSResult

   class TwilioProvider(SMSProvider):
       def __init__(self, account_sid, auth_token, from_number, webhook_url):
           self.client = Client(account_sid, auth_token)
           self.from_number = from_number
           self.webhook_url = webhook_url

       def send_sms(self, to: str, message: str) -> SMSResult:
           try:
               msg = self.client.messages.create(
                   body=message,
                   from_=self.from_number,
                   to=to,
                   status_callback=self.webhook_url
               )
               return SMSResult(success=True, message_id=msg.sid)
           except Exception as e:
               return SMSResult(success=False, error=str(e))

   ```

**驗收標準**：

- [ ] Base class 定義正確
- [ ] Twilio provider 實作完整
- [ ] 錯誤處理完善

**測試方法**：

- 單元測試（mock Twilio API）

---

### Task 3.3: 實作 FastAPI 端點

**檔案**：`sms-service/main.py`
**預估時間**：2 小時
**優先級**：High
**依賴**：Task 3.2

**詳細步驟**：

1. 建立基礎應用：

   ```python

   from fastapi import FastAPI, Request
   from google.cloud import firestore
   from providers.twilio_provider import TwilioProvider
   import os

   app = FastAPI(title="SMS Service")
   db = firestore.Client()

   sms_provider = TwilioProvider(
       account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
       auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
       from_number=os.getenv("TWILIO_FROM_NUMBER"),
       webhook_url=os.getenv("TWILIO_WEBHOOK_URL")
   )

   ```

2. 實作端點：

   **a. GET /health**

   **b. POST /send**

   ```python

   @app.post("/send")
   async def send_sms(request: Request):
       # 1. 從 request body 取得 case_id
       # 2. 從 Firestore 讀取案件資料
       # 3. 組合簡訊內容（使用模板）
       # 4. 呼叫 sms_provider.send_sms()
       # 5. 更新 Firestore 狀態
       # 6. 返回結果
   ```

   **c. POST /webhook/delivery-status**

   ```python

   @app.post("/webhook/delivery-status")
   async def webhook_delivery_status(request: Request):
       # 1. 解析 Twilio webhook payload
       # 2. 驗證簽名（可選但推薦）
       # 3. 根據 message_id 找到案件
       # 4. 更新投遞狀態
       # 5. （可選）發送 Slack 通知
   ```

3. 定義簡訊模板：

   ```python

   SMS_TEMPLATE = """【iCHEF】您好 {customer_name}，

   感謝今日與 {sales_rep_name} 的會議討論。

   會議摘要已準備好，請點擊以下連結查看：
   {short_url}

   如有任何問題，歡迎隨時聯繫。

   iCHEF 團隊 敬上"""

   ```

**驗收標準**：

- [ ] 所有端點實作完成
- [ ] 簡訊發送成功
- [ ] Webhook 處理正確
- [ ] Firestore 狀態更新

---

### Task 3.4: 設定 Secrets 與環境變數

**預估時間**：1 小時
**優先級**：High
**依賴**：Twilio 帳號申請

**詳細步驟**：

1. 申請 Twilio 帳號（如尚未申請）
   - 前往 <https://www.twilio.com/try-twilio>
   - 取得 Account SID、Auth Token、Phone Number

2. 建立 GCP Secrets：

   ```bash
   # 設定環境變數
   export TWILIO_ACCOUNT_SID="ACxxxx..."
   export TWILIO_AUTH_TOKEN="xxxx..."
   export TWILIO_FROM_NUMBER="+1234567890"

   # 建立 secrets
   echo -n "$TWILIO_ACCOUNT_SID" | gcloud secrets create twilio-account-sid --data-file=-
   echo -n "$TWILIO_AUTH_TOKEN" | gcloud secrets create twilio-auth-token --data-file=-
   echo -n "$TWILIO_FROM_NUMBER" | gcloud secrets create twilio-from-number --data-file=-

   ```

3. 設定 Service Account 權限：

   ```bash
   # 授予 Secret Manager 存取權限
   gcloud secrets add-iam-policy-binding twilio-account-sid \
     --member="serviceAccount:497329205771-compute@developer.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"

   # 重複上述指令給其他 secrets
   ```

4. 更新 `cloudbuild.yaml`：

   ```yaml

   - '--set-secrets=TWILIO_ACCOUNT_SID=twilio-account-sid:latest,TWILIO_AUTH_TOKEN=twilio-auth-token:latest,TWILIO_FROM_NUMBER=twilio-from-number:latest'

   ```

**驗收標準**：

- [ ] Secrets 建立成功
- [ ] Service Account 有權限存取
- [ ] Cloud Run 可讀取 secrets

**測試指令**：

```bash
# 驗證 secret 存在
gcloud secrets describe twilio-account-sid

# 測試存取（需要權限）
gcloud secrets versions access latest --secret="twilio-account-sid"

```

---

## Phase 4: Cloud Tasks 整合（0.5 天）

### Task 4.1: 建立 Cloud Tasks Queue

**預估時間**：0.5 小時
**優先級**：High
**依賴**：無

**詳細步驟**：

1. 建立 queue：

   ```bash

   gcloud tasks queues create summary-delivery-queue \
     --location=asia-east1 \
     --max-concurrent-dispatches=10 \
     --max-attempts=3 \
     --min-backoff=10s \
     --max-backoff=300s \
     --project=sales-ai-automation-v2

   ```

2. 驗證 queue 建立：

   ```bash

   gcloud tasks queues describe summary-delivery-queue \
     --location=asia-east1 \
     --project=sales-ai-automation-v2

   ```

**驗收標準**：

- [ ] Queue 建立成功
- [ ] 參數設定正確

---

### Task 4.2: 更新 MCP Server

**檔案**：`tools/cloud_tasks/mcp_server.py`
**預估時間**：2 小時
**優先級**：High
**依賴**：Task 4.1, Phase 2, Phase 3

**詳細步驟**：

1. 在 `mcp_server.py` 中新增函數（參考 `AGENT7_SMS_DELIVERY_PLAN.md`）：

   ```python

   def create_summary_delivery_tasks(
       case_id: str,
       project: str = "sales-ai-automation-v2",
       location: str = "asia-east1"
   ):
       # 實作內容...
   ```

2. 新增到 `TOOL_DEFINITIONS` 列表：

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

3. 實作任務建立邏輯：

   - Task 1: POST to summary-webpage-service
   - Task 2: POST to sms-service (延遲 10 秒)

**驗收標準**：

- [ ] 函數實作完成
- [ ] Tool definition 正確
- [ ] 測試呼叫成功

**測試指令**：

```bash

echo '{
  "method": "tools/call",
  "params": {
    "name": "create_summary_delivery_tasks",
    "arguments": {"case_id": "TEST-001"}
  }
}' | python3 tools/cloud_tasks/mcp_server.py

```

---

### Task 4.3: 整合到 Slack Handler

**檔案**：`src/slack_app/handlers/summary_sender.py`
**預估時間**：1.5 小時
**優先級**：High
**依賴**：Task 1.2, Task 4.2

**詳細步驟**：

1. 在 `handle_send_summary_confirmed()` 中加入 MCP 呼叫：

   ```python
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

   if result.returncode != 0:
       # 錯誤處理
       logger.error(f"Failed to create tasks: {result.stderr}")
       # 通知使用者
       return

   task_result = json.loads(result.stdout)

   ```

2. 更新 Slack 確認訊息，顯示任務資訊

**驗收標準**：

- [ ] MCP 呼叫成功
- [ ] Cloud Tasks 建立成功
- [ ] Slack 訊息顯示任務資訊
- [ ] 錯誤處理完善

---

## Phase 5: 測試與部署（1 天）

### Task 5.1: 單元測試

**路徑**：各服務的 `tests/` 目錄
**預估時間**：2 小時
**優先級**：Medium
**依賴**：Phase 2, Phase 3

**詳細步驟**：

1. 建立測試目錄結構：

   ```bash

   mkdir -p summary-webpage-service/tests
   mkdir -p sms-service/tests

   ```

2. 安裝測試依賴：

   ```bash

   pip install pytest pytest-asyncio pytest-cov

   ```

3. 撰寫測試：

   **summary-webpage-service/tests/test_main.py**：

   - `test_health_check()`
   - `test_generate_access_token()`
   - `test_generate_short_code()`
   - `test_get_summary_with_valid_token()`
   - `test_get_summary_with_invalid_token()`

   **sms-service/tests/test_providers.py**：

   - `test_twilio_provider_success()` (mock)
   - `test_twilio_provider_error()` (mock)

   **sms-service/tests/test_main.py**：

   - `test_health_check()`
   - `test_send_sms()` (mock Firestore & Twilio)

4. 執行測試：

   ```bash

   pytest --cov=. tests/

   ```

**驗收標準**：

- [ ] 測試覆蓋率 > 70%
- [ ] 所有測試通過
- [ ] 無警告訊息

---

### Task 5.2: 整合測試

**預估時間**：3 小時
**優先級**：High
**依賴**：所有 Phase 1-4

**測試場景**：

**場景 1: 正常流程**

1. 準備測試環境：

   - [ ] 建立測試案件（含 Agent 7 摘要）
   - [ ] 設定測試手機號碼

2. 執行流程：

   - [ ] 在 Slack 點擊「確認送出」
   - [ ] 驗證 Modal 顯示
   - [ ] 提交 Modal
   - [ ] 等待 Cloud Tasks 執行
   - [ ] 檢查簡訊是否收到
   - [ ] 點擊短網址
   - [ ] 驗證網頁顯示

3. 驗證資料：

   - [ ] Firestore `customerSummaryDelivery` 狀態正確
   - [ ] `shortUrls` collection 有記錄
   - [ ] `webPageAnalytics` 有訪問記錄

**場景 2: 錯誤處理**

- [ ] 客戶電話為空 → 顯示輸入 Modal
- [ ] 電話格式錯誤 → 顯示錯誤
- [ ] Twilio API 失敗 → 記錄錯誤、重試
- [ ] Access token 錯誤 → 返回 403

**驗收標準**：

- [ ] 所有場景測試通過
- [ ] 錯誤處理符合預期
- [ ] 日誌記錄完整

---

### Task 5.3: 部署到 Production

**預估時間**：2 小時
**優先級**：High
**依賴**：Task 5.1, Task 5.2

**部署清單**：

1. **部署 summary-webpage-service**：

   ```bash

   cd summary-webpage-service
   gcloud builds submit --config cloudbuild.yaml

   ```

   - [ ] 建置成功
   - [ ] 部署成功
   - [ ] 健康檢查通過

2. **部署 sms-service**：

   ```bash

   cd sms-service
   gcloud builds submit --config cloudbuild.yaml

   ```

   - [ ] 建置成功
   - [ ] 部署成功
   - [ ] 健康檢查通過
   - [ ] Secrets 可存取

3. **部署 slack-app（更新版）**：

   ```bash

   gcloud builds submit --config deploy/slack/cloudbuild.slack.yaml

   ```

   - [ ] 建置成功
   - [ ] 部署成功
   - [ ] 新 handlers 載入成功

4. **驗證服務 URLs**：

   ```bash

   gcloud run services list --platform managed --region asia-east1

   ```

   - [ ] summary-webpage-service URL 正確
   - [ ] sms-service URL 正確
   - [ ] slack-app URL 正確

5. **更新 MCP Server 中的 URLs**（如果 hardcoded）

**驗收標準**：

- [ ] 所有服務部署成功
- [ ] 服務間可正常通訊
- [ ] IAM 權限正確

---

### Task 5.4: Production 驗證

**預估時間**：1 小時
**優先級**：High
**依賴**：Task 5.3

**驗證步驟**：

1. **建立真實測試案件**：

   - [ ] 上傳真實音檔
   - [ ] 等待 Agent 1-7 完成
   - [ ] 確認 Slack 通知顯示

2. **執行完整流程**：

   - [ ] 點擊「確認送出」
   - [ ] 填寫真實手機號碼（自己的）
   - [ ] 確認提交
   - [ ] 檢查 Cloud Tasks 執行狀態
   - [ ] 等待簡訊（應在 15 秒內收到）

3. **驗證簡訊與網頁**：

   - [ ] 簡訊內容正確
   - [ ] 短網址可點擊
   - [ ] 網頁顯示完整
   - [ ] 手機瀏覽正常

4. **檢查資料**：

   ```bash
   # 檢查 Firestore（需要自行實作查詢）
   # 檢查 Cloud Logging
   gcloud logging read 'resource.type="cloud_run_revision"
     (resource.labels.service_name="summary-webpage-service" OR
      resource.labels.service_name="sms-service")' \
     --limit 50 --freshness=10m

   ```

5. **監控告警**（可選）：

   - [ ] 設定 Cloud Monitoring 告警
   - [ ] 設定錯誤率告警

**驗收標準**：

- [ ] 端到端流程完全正常
- [ ] 無錯誤日誌
- [ ] 效能符合預期
- [ ] 使用者體驗良好

---

## 📋 檢查清單總覽

### 開發前準備

- [ ] 閱讀完整規劃文件（`AGENT7_SMS_DELIVERY_PLAN.md`）
- [ ] 申請 Twilio 帳號並取得憑證
- [ ] 確認 GCP 專案權限
- [ ] 準備短網址 domain（可選）

### Phase 1 完成標準

- [ ] `agent7_notifier.py` 更新完成
- [ ] `summary_sender.py` 實作完成（4 個函數）
- [ ] Slack App `main.py` 整合完成
- [ ] 本地測試通過
- [ ] 部署測試通過

### Phase 2 完成標準

- [ ] 服務目錄結構建立
- [ ] FastAPI 應用實作完成（3 個端點）
- [ ] HTML 模板設計完成
- [ ] CSS 樣式設計完成
- [ ] Docker 可建置
- [ ] 本地測試通過

### Phase 3 完成標準

- [ ] 服務目錄結構建立
- [ ] Twilio Provider 實作完成
- [ ] FastAPI 應用實作完成（3 個端點）
- [ ] Secrets 設定完成
- [ ] Docker 可建置
- [ ] 本地測試通過

### Phase 4 完成標準

- [ ] Cloud Tasks Queue 建立
- [ ] MCP Server 更新完成
- [ ] Slack Handler 整合完成
- [ ] MCP 測試通過

### Phase 5 完成標準

- [ ] 單元測試通過（覆蓋率 > 70%）
- [ ] 整合測試通過（所有場景）
- [ ] 所有服務部署成功
- [ ] Production 驗證通過
- [ ] 文件更新完成

---

## 🐛 已知問題與注意事項

1. **Twilio Webhook URL**
   - 需要在 Twilio Console 設定 webhook URL
   - URL 格式：`https://sms-service-{hash}.asia-east1.run.app/webhook/delivery-status`

2. **短網址 Domain**
   - 如使用自訂 domain（如 `ichef.page`），需要額外設定 DNS
   - 建議初期使用 Cloud Run 預設 URL

3. **簡訊字數限制**
   - 單則簡訊限制 70 個中文字
   - 目前模板約 65-70 字，需注意變數長度

4. **Access Token 長度**
   - 預設 32 字元，產生 URL 較長
   - 可考慮縮短為 16-24 字元（仍然安全）

5. **Firestore 寫入成本**
   - 每次發送會產生 3-4 次寫入
   - 大量使用時注意成本

---

## 📚 參考資源

- **規劃文件**：`AGENT7_SMS_DELIVERY_PLAN.md`
- **Twilio 文件**：<https://www.twilio.com/docs/sms>
- **FastAPI 文件**：<https://fastapi.tiangolo.com/>
- **Jinja2 文件**：<https://jinja.palletsprojects.com/>
- **Cloud Tasks 文件**：<https://cloud.google.com/tasks/docs>

---

**最後更新**：2025-11-12
**維護者**：Sales AI Team
