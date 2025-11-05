# Slack Workflow 詳細設計文件

**專案**: Sales AI Automation V2.0
**文件版本**: 1.0
**最後更新**: 2025-10-31
**相關文件**: [plan.md](./plan.md), [spec.md](./spec.md)

## 目錄

- [概述](#概述)
- [架構決策](#架構決策)
- [層次 1: 音檔上傳與處理](#層次-1-音檔上傳與處理)
- [層次 2: 摘要審核與編輯](#層次-2-摘要審核與編輯)
- [層次 3: 客戶網頁與通知](#層次-3-客戶網頁與通知)
- [Firestore 資料結構](#firestore-資料結構)
- [錯誤處理與重試](#錯誤處理與重試)
- [測試策略](#測試策略)
- [部署需求](#部署需求)

---

## 概述

### 設計原則

本工作流程遵循以下憲法原則：

1. **隱私保護**：所有互動僅透過 DM，不使用 Channel（避免客戶資料外洩）
2. **成本優化**：使用 Cloud Tasks 自動重試，減少人工介入成本
3. **用戶體驗**：清晰的視覺反饋，防止重複操作
4. **繁體中文優先**：所有用戶面向訊息使用繁體中文（憲法 Principle VI）

### 完整流程概覽

```text
業務與 Bot DM
  ↓
上傳音檔 → Bot 偵測 → 顯示分析按鈕
  ↓
點擊按鈕 → 填寫 Modal → 提交鎖定
  ↓
Cloud 處理 30-40 分鐘（自動重試）
  ↓
Agent 6 銷售分析 → Agent 7 客戶摘要
  ↓
業務審核編輯 → 確認送出
  ↓
生成網頁 + SMS 發送給客戶
```

---

## 架構決策

### 為何選擇 DM 而非 Channel？

| 考量 | DM | Channel |
|------|-----|---------|
| 隱私保護 | ✅ 只有業務看得到客戶資料 | ❌ 所有成員都能看到 |
| 用戶體驗 | ✅ 像個人助理，清爽 | ⚠️ 訊息混亂 |
| 通知精準度 | ✅ 只通知相關業務 | ❌ 干擾其他成員 |
| 技術複雜度 | ✅ 簡單，無需權限管理 | ⚠️ 需要管理 Channel 權限 |
| 符合 GDPR/個資法 | ✅ 符合 | ⚠️ 可能違反 |

**決策**：僅支援 DM，不實作 Channel 功能。

### 主管監控方式

主管查看所有案件的方式（暫不實作，後續 Phase）：

- Firestore Console 直接查詢
- Google Sheets 每日同步（原計劃已有）
- 獨立管理後台（Web，Phase 3）

---

## 層次 1: 音檔上傳與處理

### 1.1 用戶體驗流程

```text
業務操作：
1. 在 Slack 左側找到「Sales AI Bot」並開啟 DM
2. 拖放音檔（m4a/mp3/wav）到對話中
3. Bot 自動回覆「已偵測到音檔」+ [🎤 分析此錄音] 按鈕
4. 點擊按鈕，開啟 Modal 填寫資料
5. 提交 Modal
6. 等待 30-40 分鐘
7. Bot 在同一 thread 回覆分析結果
```

### 1.2 技術實作

#### A. Slack App 權限設定

```yaml
OAuth & Permissions:
  Bot Token Scopes:
    - files:read           # 讀取檔案資訊
    - chat:write           # 發送訊息
    - im:history           # 讀取 DM 歷史
    - im:write             # 在 DM 中發送訊息
    - users:read           # 讀取用戶資訊
    - users:read.email     # 讀取用戶 email

Event Subscriptions:
  Events:
    - file_shared          # 檔案上傳事件
    - app_home_opened      # 用戶打開與 Bot 的對話（用於歡迎訊息）
  Request URL:
    https://slack-service-[PROJECT_ID].run.app/slack/events
```

#### B. 偵測音檔上傳

```python
# services/slack-service/src/events/file_upload_handler.py

from slack_bolt.async_app import AsyncApp
from google.cloud import firestore
import logging

app = AsyncApp()
logger = logging.getLogger(__name__)

@app.event("file_shared")
async def handle_file_upload(event, client):
    """處理音檔上傳事件（僅 DM）"""

    file_id = event["file_id"]
    user_id = event["user_id"]

    logger.info(f"File shared event: file_id={file_id}, user_id={user_id}")

    # 取得檔案資訊
    try:
        file_info = await client.files_info(file=file_id)
        file = file_info["file"]
    except Exception as e:
        logger.error(f"Failed to get file info: {e}")
        return

    # 檢查是否為音檔
    allowed_mimetypes = [
        "audio/m4a",
        "audio/mp3",
        "audio/wav",
        "audio/mpeg",
        "audio/x-m4a"
    ]

    if file.get("mimetype") not in allowed_mimetypes:
        logger.debug(f"Ignoring non-audio file: {file.get('mimetype')}")
        return

    # ====== 關鍵：僅處理 DM（private shares）======
    shares = file.get("shares", {})

    if not shares.get("private"):
        logger.debug("Ignoring file not shared in DM")
        return

    # 取得 DM channel_id 和 message_ts
    dm_channel_id = list(shares["private"].keys())[0]
    message_ts = shares["private"][dm_channel_id][0]["ts"]

    logger.info(f"Audio file detected in DM: channel={dm_channel_id}, ts={message_ts}")

    # 檢查是否已處理
    db = firestore.AsyncClient()
    processed_file_ref = db.collection("processed_files").document(file_id)
    processed_file = await processed_file_ref.get()

    if processed_file.exists:
        logger.info(f"File {file_id} already processed")
        await send_already_processed_message(
            client, dm_channel_id, message_ts, file, processed_file
        )
        return

    # 顯示「分析此錄音」按鈕
    await send_analysis_button(client, dm_channel_id, message_ts, file, user_id)


async def send_analysis_button(client, channel_id, message_ts, file, user_id):
    """發送「分析此錄音」按鈕"""

    file_id = file["id"]
    file_name = file["name"]
    file_size_mb = file["size"] / 1024 / 1024
    duration_min = file.get("duration_ms", 0) // 1000 // 60

    response = await client.chat_postMessage(
        channel=channel_id,
        thread_ts=message_ts,
        text=f"✅ 已偵測到音檔：{file_name}",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"✅ *已偵測到音檔*\n\n*檔案*：{file_name}\n*大小*：{file_size_mb:.1f} MB\n*時長*：{duration_min} 分鐘"
                }
            },
            {
                "type": "actions",
                "block_id": f"analyze_actions_{file_id}",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🎤 分析此錄音"},
                        "action_id": "start_analysis",
                        "value": file_id,
                        "style": "primary"
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "💡 點擊按鈕填寫客戶資料後開始分析"
                    }
                ]
            }
        ]
    )

    logger.info(f"Analysis button sent: message_ts={response['ts']}")
```

#### C. 處理按鈕點擊

```python
# services/slack-service/src/interactions/analysis_button_handler.py

import json

@app.action("start_analysis")
async def handle_start_analysis(ack, body, client):
    """處理「分析此錄音」按鈕點擊"""

    # 立即回應 Slack（必須在 3 秒內）
    await ack()

    file_id = body["actions"][0]["value"]
    user_id = body["user"]["id"]

    logger.info(f"Analysis button clicked: file_id={file_id}, user_id={user_id}")

    # 檢查檔案是否已處理（無鎖定，僅檢查）
    db = firestore.AsyncClient()
    processed_file = await db.collection("processed_files").document(file_id).get()

    if processed_file.exists:
        data = processed_file.to_dict()
        case_id = data.get("caseId")
        status = data.get("status")

        status_messages = {
            "processing": f"⏳ 此音檔正在處理中（案件編號：{case_id}）",
            "completed": f"✅ 此音檔已完成分析（案件編號：{case_id}）",
            "failed": f"❌ 此音檔處理失敗（案件編號：{case_id}），系統正在自動重試"
        }

        await client.chat_postEphemeral(
            channel=body["container"]["channel_id"],
            user=user_id,
            thread_ts=body["message"]["thread_ts"],
            text=status_messages.get(status, "此音檔已被處理")
        )
        return

    # 開啟 Modal 收集資訊
    await open_metadata_modal(client, body, file_id)


async def open_metadata_modal(client, body, file_id):
    """開啟 Modal 收集客戶資訊"""

    # 取得檔案資訊
    file_info = await client.files_info(file=file_id)
    file = file_info["file"]

    await client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "recording_metadata_modal",
            "private_metadata": json.dumps({
                "file_id": file_id,
                "channel_id": body["container"]["channel_id"],
                "message_ts": body["message"]["thread_ts"],
                "bot_message_ts": body["container"]["message_ts"]
            }),
            "title": {"type": "plain_text", "text": "🎤 分析此錄音"},
            "submit": {"type": "plain_text", "text": "開始分析"},
            "close": {"type": "plain_text", "text": "取消"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*檔案*：{file['name']}\n*大小*：{file['size'] / 1024 / 1024:.1f} MB"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "input",
                    "block_id": "customer_name",
                    "label": {"type": "plain_text", "text": "店名"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "customer_name_input",
                        "placeholder": {"type": "plain_text", "text": "例：小確幸咖啡"}
                    }
                },
                {
                    "type": "input",
                    "block_id": "customer_id",
                    "label": {"type": "plain_text", "text": "客戶編號"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "customer_id_input",
                        "placeholder": {"type": "plain_text", "text": "例：C12345"}
                    }
                },
                {
                    "type": "input",
                    "block_id": "customer_phone",
                    "label": {"type": "plain_text", "text": "客戶手機"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "customer_phone_input",
                        "placeholder": {"type": "plain_text", "text": "例：0912-345-678"}
                    },
                    "hint": {
                        "type": "plain_text",
                        "text": "用於發送客戶摘要 SMS"
                    }
                },
                {
                    "type": "input",
                    "block_id": "notes",
                    "optional": True,
                    "label": {"type": "plain_text", "text": "備註（可選）"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "notes_input",
                        "multiline": True,
                        "placeholder": {"type": "plain_text", "text": "例：首次會議、需要特別注意..."}
                    }
                }
            ]
        }
    )

    logger.info(f"Modal opened for file {file_id}")
```

### 1.3 防重複機制

#### Transaction 鎖定邏輯

```python
# services/slack-service/src/interactions/modal_handler.py

from google.cloud.firestore_v1 import transactional

@app.view("recording_metadata_modal")
async def handle_metadata_submission(ack, body, client, view):
    """處理 Modal 提交（鎖定點）"""

    # 解析 metadata
    metadata = json.loads(view["private_metadata"])
    file_id = metadata["file_id"]
    channel_id = metadata["channel_id"]
    message_ts = metadata["message_ts"]
    bot_message_ts = metadata["bot_message_ts"]

    # 取得表單資料
    values = view["state"]["values"]
    customer_name = values["customer_name"]["customer_name_input"]["value"]
    customer_id = values["customer_id"]["customer_id_input"]["value"]
    customer_phone = values["customer_phone"]["customer_phone_input"]["value"]
    notes = values["notes"]["notes_input"].get("value", "")

    # 驗證手機格式
    import re
    phone_pattern = r'^09\d{2}-?\d{3}-?\d{3}$'
    cleaned_phone = customer_phone.replace("-", "").replace(" ", "")

    if not re.match(phone_pattern, cleaned_phone):
        await ack(response_action="errors", errors={
            "customer_phone": "請輸入正確的台灣手機格式（例：0912-345-678）"
        })
        return

    # ====== Firestore Transaction 鎖定 ======
    db = firestore.AsyncClient()
    file_ref = db.collection("processed_files").document(file_id)

    try:
        @transactional
        async def check_and_lock(transaction, ref):
            snapshot = await ref.get(transaction=transaction)

            if snapshot.exists:
                # 已鎖定
                existing = snapshot.to_dict()
                return False, existing.get("caseId"), existing.get("status")

            # 立即鎖定
            transaction.set(ref, {
                "slackFileId": file_id,
                "status": "processing",
                "locked": True,
                "lockedAt": firestore.SERVER_TIMESTAMP,
                "processedBy": body["user"]["id"],
                "channelId": channel_id,
                "messageTs": message_ts,
                "threadTs": bot_message_ts,
                "customerName": customer_name,
                "customerId": customer_id,
                "customerPhone": cleaned_phone,
                "fileName": (await client.files_info(file=file_id))["file"]["name"],
            })

            return True, None, None

        transaction = db.transaction()
        can_process, existing_case_id, existing_status = await check_and_lock(
            transaction, file_ref
        )

        if not can_process:
            status_text = {
                "processing": "正在處理中",
                "completed": "已完成分析",
                "failed": "處理失敗（系統重試中）"
            }.get(existing_status, "已被處理")

            await ack(response_action="errors", errors={
                "customer_name": f"此音檔{status_text}（案件編號：{existing_case_id}），無法重複提交"
            })
            return

    except Exception as e:
        logger.error(f"Transaction failed: {e}")
        await ack(response_action="errors", errors={
            "customer_name": "系統錯誤，請稍後再試"
        })
        return

    # Transaction 成功，確認 Modal
    await ack()

    logger.info(f"File {file_id} locked successfully")

    # 建立 case 並觸發處理流程
    # （詳細實作見下一節）
```

---

## 層次 2: 摘要審核與編輯

### 2.1 用戶體驗流程

```text
Agent 7 完成後：
1. Bot 在 thread 回覆摘要預覽（前 500 字）
2. 顯示三個按鈕：
   - [✏️ 編輯摘要]
   - [👁️ 完整預覽]
   - [✅ 確認送出]
3. 業務可重複編輯，每次儲存後更新預覽
4. 確認無誤後點擊「確認送出」
```

### 2.2 編輯功能實作

```python
# services/slack-service/src/interactions/summary_editor.py

@app.action("edit_summary")
async def handle_edit_summary(ack, body, client):
    """處理「編輯摘要」按鈕"""

    await ack()

    case_id = body["actions"][0]["value"]

    # 從 Firestore 取得摘要
    db = firestore.AsyncClient()
    case = await db.collection("cases").document(case_id).get()
    customer_summary = case.get("analysis.customerSummary")
    markdown_content = customer_summary.get("markdown", "")

    # 開啟編輯 Modal
    await client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "edit_summary_modal",
            "private_metadata": json.dumps({
                "case_id": case_id,
                "bot_message_ts": body["container"]["message_ts"],
                "channel_id": body["container"]["channel_id"],
                "thread_ts": body["message"]["thread_ts"]
            }),
            "title": {"type": "plain_text", "text": "編輯客戶摘要"},
            "submit": {"type": "plain_text", "text": "儲存"},
            "close": {"type": "plain_text", "text": "取消"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*店名*：{case.get('customerName')}\n*案件編號*：{case_id}"
                    }
                },
                {
                    "type": "input",
                    "block_id": "summary_content",
                    "label": {"type": "plain_text", "text": "摘要內容（Markdown 格式）"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "summary_input",
                        "multiline": True,
                        "initial_value": markdown_content,
                        "max_length": 3000
                    },
                    "hint": {
                        "type": "plain_text",
                        "text": "支援 Markdown 格式：標題 (##)、列表 (-)、粗體 (**)"
                    }
                }
            ]
        }
    )


@app.view("edit_summary_modal")
async def handle_save_summary(ack, body, client, view):
    """處理摘要儲存"""

    await ack()

    metadata = json.loads(view["private_metadata"])
    case_id = metadata["case_id"]
    bot_message_ts = metadata["bot_message_ts"]
    channel_id = metadata["channel_id"]
    thread_ts = metadata["thread_ts"]

    new_content = view["state"]["values"]["summary_content"]["summary_input"]["value"]

    # 更新 Firestore
    db = firestore.AsyncClient()
    await db.collection("cases").document(case_id).update({
        "analysis.customerSummary.markdown": new_content,
        "analysis.customerSummary.lastEditedAt": firestore.SERVER_TIMESTAMP,
        "analysis.customerSummary.editedBy": body["user"]["id"]
    })

    logger.info(f"Summary edited: case_id={case_id}")

    # 更新原訊息，標記「已編輯」
    # （詳細實作略）

    # 在 thread 中回覆確認
    await client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        text=f"✅ 摘要已更新 by <@{body['user']['id']}>"
    )
```

---

## 層次 3: 客戶網頁與通知

### 3.1 網頁生成

```python
# services/web-service/src/summary_renderer.py

import markdown
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

class SummaryRenderer:
    def __init__(self):
        self.env = Environment(loader=FileSystemLoader('templates'))

    async def render_summary_html(self, case_id: str) -> str:
        """生成客戶摘要 HTML"""

        db = firestore.AsyncClient()
        case = await db.collection("cases").document(case_id).get()

        customer_summary = case.get("analysis.customerSummary")
        markdown_content = customer_summary.get("markdown", "")

        # Markdown 轉 HTML
        summary_html = markdown.markdown(
            markdown_content,
            extensions=['tables', 'fenced_code', 'nl2br']
        )

        # 取得業務資訊
        sales_rep_email = case.get("salesRepEmail")
        sales_rep = await db.collection("users").document(sales_rep_email).get()
        line_id = sales_rep.get("lineId", "")
        line_url = f"https://line.me/ti/p/{line_id}" if line_id else "#"

        # 渲染模板
        template = self.env.get_template('customer_summary.html')
        html = template.render(
            customer_name=case.get("customerName"),
            meeting_date=case.get("createdAt").strftime("%Y年%m月%d日"),
            sales_rep_name=case.get("salesRepName"),
            summary_html=summary_html,
            line_url=line_url,
            current_year=datetime.now().year
        )

        return html
```

### 3.2 SMS 發送

```python
# services/notification-service/src/sms_sender.py

from twilio.rest import Client
import os

class SMSSender:
    def __init__(self):
        self.client = Client(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN")
        )
        self.from_number = os.getenv("TWILIO_PHONE_NUMBER")

    async def send_summary_link(self, case_id: str) -> dict:
        """發送摘要連結給客戶"""

        db = firestore.AsyncClient()
        case = await db.collection("cases").document(case_id).get()

        customer_phone = case.get("customerPhone")
        sales_rep_name = case.get("salesRepName")
        summary_url = f"https://sales.ichefpos.com/summary/{case_id}"

        # SMS 訊息內容（繁體中文）
        message = f"""您好，我是 iCHEF 的 {sales_rep_name}。

感謝您今天與我們的會議！我已為您整理好會議摘要：
{summary_url}

若有任何問題，歡迎隨時與我聯繫 📞

iCHEF 資廚管理顧問"""

        try:
            result = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=customer_phone
            )

            # 更新 Firestore
            await db.collection("cases").document(case_id).update({
                "delivery.smsStatus": "sent",
                "delivery.smsSid": result.sid,
                "delivery.sentAt": firestore.SERVER_TIMESTAMP,
                "delivery.customerPhone": customer_phone,
                "delivery.summaryUrl": summary_url
            })

            logger.info(f"SMS sent: sid={result.sid}, case_id={case_id}")

            return {
                "status": "success",
                "sid": result.sid,
                "to": customer_phone
            }

        except Exception as e:
            logger.error(f"SMS failed: {e}")

            await db.collection("cases").document(case_id).update({
                "delivery.smsStatus": "failed",
                "delivery.smsError": str(e),
                "delivery.failedAt": firestore.SERVER_TIMESTAMP
            })

            raise e
```

---

## Firestore 資料結構

### Collection: `processed_files`

```typescript
// Document ID: slack_file_id
{
  slackFileId: string,              // Slack file ID（主鍵）
  status: "processing" | "completed" | "failed",
  locked: boolean,                  // 防止並發
  lockedAt: Timestamp,

  // 關聯資訊
  caseId: string,                   // 對應的 case ID
  channelId: string,                // DM channel ID
  messageTs: string,                // 音檔訊息的 timestamp
  threadTs: string,                 // Bot 回覆訊息的 timestamp

  // 檔案資訊
  fileName: string,
  fileSize: number,

  // 客戶資訊
  customerName: string,
  customerId: string,
  customerPhone: string,

  // 處理者
  processedBy: string,              // 業務的 Slack ID

  // 時間戳
  processedAt: Timestamp,
  completedAt: Timestamp,
}
```

### Collection: `cases` 更新

```typescript
{
  // ... 原有欄位

  // 客戶資訊（新增）
  customerId: string,
  customerPhone: string,

  // Slack 通知（更新）
  notification: {
    slackChannelId: string,         // DM channel ID（就是 user_id）
    slackThreadTs: string,           // Thread timestamp
    slackFileId: string,             // Slack file ID
    agent6MessageTs: string,         // Agent 6 分析卡片的 message_ts
    agent7MessageTs: string,         // Agent 7 摘要預覽的 message_ts
    agent6SentAt: Timestamp,
    agent7SentAt: Timestamp,
  },

  // Agent 7 客戶摘要（新增）
  analysis: {
    // ... 其他 agents

    customerSummary: {
      markdown: string,              // 當前版本
      originalMarkdown: string,      // AI 原始版本
      summary: string,               // 簡短摘要
      lastEditedAt: Timestamp,
      editedBy: string,              // Slack ID
      editHistory: [                 // 可選
        {
          markdown: string,
          editedAt: Timestamp,
          editedBy: string,
        }
      ]
    }
  },

  // 客戶摘要發送（新增）
  delivery: {
    smsStatus: "pending" | "sent" | "failed",
    smsSid: string,
    customerPhone: string,
    sentAt: Timestamp,
    failedAt: Timestamp,
    smsError: string,
    summaryUrl: string,
    shortUrl: string,                // 可選
    viewCount: number,               // 客戶查看次數
    lastViewedAt: Timestamp,
  }
}
```

---

## 錯誤處理與重試

### Cloud Tasks Retry Policy

```python
# services/orchestration-service/src/queue_manager.py

from google.cloud import tasks_v2
from google.protobuf import duration_pb2

class QueueManager:
    def enqueue_transcription_task(self, case_id: str, gcs_path: str):
        """加入轉錄任務（含重試策略）"""

        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": f"https://transcription-service.run.app/transcribe",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"caseId": case_id, "gcsPath": gcs_path}).encode()
            },
            "retry_config": {
                "max_attempts": 5,                      # 最多 5 次
                "max_retry_duration": duration_pb2.Duration(seconds=7200),  # 2 小時
                "min_backoff": duration_pb2.Duration(seconds=60),   # 60 秒
                "max_backoff": duration_pb2.Duration(seconds=600),  # 10 分鐘
                "max_doublings": 3                       # 指數退避
            }
        }

        # 發送任務
        # ...
```

### Slack 錯誤通知

```python
async def notify_slack_processing_error(case_id: str, stage: str, error: str):
    """通知 Slack 處理錯誤（保持鎖定）"""

    db = firestore.AsyncClient()
    case = await db.collection("cases").document(case_id).get()

    channel_id = case.get("notification.slackChannelId")
    thread_ts = case.get("notification.slackThreadTs")
    retry_count = case.get("retryCount", 0)

    if retry_count < 3:
        message = f"⚠️ 處理時發生錯誤，系統正在自動重試（第 {retry_count} 次）..."
    else:
        message = f"❌ 處理失敗（已重試 {retry_count} 次），請聯繫技術支援"

    await slack_client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        text=message
    )
```

---

## 測試策略

### 單元測試

```python
# services/slack-service/tests/test_file_upload_handler.py

import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_handle_file_upload_audio_file():
    """測試音檔上傳處理"""

    # Mock event
    event = {
        "file_id": "F12345",
        "user_id": "U67890"
    }

    # Mock client
    client = AsyncMock()
    client.files_info.return_value = {
        "file": {
            "id": "F12345",
            "name": "test.m4a",
            "mimetype": "audio/m4a",
            "size": 1024000,
            "shares": {
                "private": {
                    "D12345": [{"ts": "1234567890.123456"}]
                }
            }
        }
    }

    # 執行
    with patch('firestore.AsyncClient') as mock_db:
        mock_db.return_value.collection.return_value.document.return_value.get.return_value.exists = False

        await handle_file_upload(event, client)

    # 驗證
    client.chat_postMessage.assert_called_once()
    assert "已偵測到音檔" in client.chat_postMessage.call_args[1]["text"]


@pytest.mark.asyncio
async def test_handle_file_upload_non_audio():
    """測試非音檔不處理"""

    event = {"file_id": "F12345", "user_id": "U67890"}
    client = AsyncMock()
    client.files_info.return_value = {
        "file": {"mimetype": "image/png"}
    }

    await handle_file_upload(event, client)

    # 不應發送訊息
    client.chat_postMessage.assert_not_called()
```

### E2E 測試

```python
# tests/e2e/test_slack_workflow.py

@pytest.mark.e2e
async def test_complete_workflow():
    """測試完整工作流程：上傳 → 分析 → 編輯 → 送出"""

    # 1. 模擬上傳音檔
    # 2. 驗證 Bot 回覆按鈕
    # 3. 模擬點擊按鈕
    # 4. 模擬填寫 Modal
    # 5. 等待處理完成
    # 6. 驗證 Agent 6/7 結果
    # 7. 模擬編輯摘要
    # 8. 模擬確認送出
    # 9. 驗證 SMS 發送

    # （詳細實作略）
```

---

## 部署需求

### Slack App 設定

1. 建立 Slack App：<https://api.slack.com/apps>
2. 設定 OAuth 權限（如前述）
3. 設定 Event Subscriptions Request URL
4. 安裝到 Workspace
5. 將 Bot Token 和 Signing Secret 儲存到 Secret Manager

### GCP Secret Manager

```bash
# 儲存 Slack 憑證
gcloud secrets create slack-bot-token --data-file=- <<< "xoxb-..."
gcloud secrets create slack-signing-secret --data-file=- <<< "..."

# 儲存 Twilio 憑證
gcloud secrets create twilio-account-sid --data-file=- <<< "AC..."
gcloud secrets create twilio-auth-token --data-file=- <<< "..."
gcloud secrets create twilio-phone-number --data-file=- <<< "+886..."
```

### Cloud Run 部署

```yaml
# services/slack-service/service.yaml

apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: slack-service
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "0"
        autoscaling.knative.dev/maxScale: "3"
    spec:
      containers:
      - image: gcr.io/PROJECT_ID/slack-service:latest
        env:
        - name: SLACK_BOT_TOKEN
          valueFrom:
            secretKeyRef:
              name: slack-bot-token
              key: latest
        - name: SLACK_SIGNING_SECRET
          valueFrom:
            secretKeyRef:
              name: slack-signing-secret
              key: latest
        resources:
          limits:
            cpu: "1"
            memory: "512Mi"
```

---

## 總結

本文件定義了 Slack Workflow 的完整技術實作細節，涵蓋：

✅ 三層架構：上傳 → 審核 → 發送
✅ DM-only 設計（隱私保護）
✅ 防重複機制（Transaction 鎖定）
✅ 錯誤處理（自動重試）
✅ 測試策略（單元 + E2E）
✅ 部署需求（Slack App + GCP）

**下一步**：參考 `tasks.md` 開始實作各個功能模組。
