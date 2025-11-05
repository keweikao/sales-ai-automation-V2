"""
Slack App for Sales AI Automation - HTTP Mode (Cloud Run)
處理音檔上傳、客戶資料收集、並觸發 AI 分析流程
支持 Agent 8 業務主管智能問答
"""
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from flask import Flask, request
from google.cloud import firestore
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_sdk.errors import SlackApiError

from utils.case_management import (
    allocate_case_id,
    build_initial_case_document,
    build_processed_file_document,
)
from utils.file_pipeline import (
    download_slack_file,
    enqueue_transcription_task,
    upload_to_gcs,
)

# 設定 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化 Firestore
project_id = os.environ.get("GCP_PROJECT_ID")
if project_id:
    db = firestore.Client(project=project_id)
else:
    logger.warning("GCP_PROJECT_ID 未設定，Firestore 功能將無法使用")
    db = None

# 初始化 Slack App (HTTP Mode)
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    process_before_response=True  # 重要：Cloud Run 需要快速回應
)

# 初始化 Flask app
flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

# 環境設定
AUDIO_BUCKET = os.getenv("SLACK_AUDIO_BUCKET") or os.getenv("GCS_AUDIO_BUCKET")
TASK_QUEUE = os.getenv("TRANSCRIPTION_TASK_QUEUE")
TASK_LOCATION = os.getenv("TRANSCRIPTION_TASK_LOCATION", "asia-east1")
TASK_HANDLER_URL = os.getenv("TRANSCRIPTION_TASK_HANDLER_URL")
TASK_SERVICE_ACCOUNT = os.getenv("TRANSCRIPTION_TASK_SERVICE_ACCOUNT")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

# ============================================
# Command Handlers
# ============================================

@app.command("/ask-agent8")
def ask_agent8_command(ack, command, client):
    """處理 /ask-agent8 命令"""
    from handlers.agent8_handler import handle_ask_agent8_command
    handle_ask_agent8_command(ack, command, client, logger, db)


# ============================================
# Event Handlers
# ============================================

@app.event("file_shared")
def handle_file_shared(client, event, logger):
    """
    處理音檔上傳事件（僅處理 DM）
    """
    try:
        file_id = event.get("file_id")
        user_id = event.get("user_id")

        if not file_id or not user_id:
            logger.warning(f"Missing file_id or user_id in event: {event}")
            return

        # 取得檔案資訊
        file_info_response = client.files_info(file=file_id)
        file_info = file_info_response.get("file", {})
        file_name = file_info.get("name", "Unknown")
        file_type = file_info.get("filetype", "")
        shares = file_info.get("shares", {})

        # 只處理 DM（private shares）
        if not shares.get("private"):
            logger.info(f"Ignoring file {file_id} - not shared in DM")
            return

        # 檢查是否為音檔
        supported_audio_types = ["m4a", "mp3", "wav", "flac", "ogg", "aac"]
        if file_type.lower() not in supported_audio_types:
            client.chat_postMessage(
                channel=user_id,
                text=f"⚠️ 檔案類型不支援。請上傳音檔（支援格式：{', '.join(supported_audio_types)}）"
            )
            logger.info(f"Ignored non-audio file: {file_id} (type: {file_type})")
            return

        # 發送帶有按鈕的訊息
        client.chat_postMessage(
            channel=user_id,
            text=f"📎 收到音檔：*{file_name}*\n請點擊下方按鈕補充客戶資訊以開始分析。",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"📎 收到音檔：*{file_name}*\n\n請點擊下方按鈕補充客戶資訊以開始分析。"
                    }
                },
                {
                    "type": "actions",
                    "block_id": "audio_actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "🎯 分析此錄音"},
                            "style": "primary",
                            "action_id": "analyze_audio_button",
                            "value": file_id
                        }
                    ]
                }
            ]
        )
        logger.info(f"Audio file detected: {file_id} ({file_name}) from user {user_id}")

    except SlackApiError as e:
        logger.error(f"Slack API error in handle_file_shared: {e.response['error']}")
    except Exception as e:
        logger.error(f"Unexpected error in handle_file_shared: {e}", exc_info=True)


@app.action("analyze_audio_button")
def handle_analyze_button(ack, body, client, logger):
    """
    處理「分析此錄音」按鈕點擊，開啟 Modal 收集客戶資料
    """
    ack()  # 立即確認

    try:
        file_id = body["actions"][0]["value"]
        trigger_id = body["trigger_id"]

        channel_id = (
            body.get("channel", {}).get("id")
            or body.get("container", {}).get("channel_id")
            or body.get("user", {}).get("id")
        )
        message_ts = body.get("message", {}).get("ts") or body.get("container", {}).get("message_ts")
        thread_ts = body.get("message", {}).get("thread_ts")

        private_metadata = json.dumps(
            {
                "file_id": file_id,
                "channel_id": channel_id,
                "message_ts": message_ts,
                "thread_ts": thread_ts,
                "user_id": body.get("user", {}).get("id"),
            }
        )

        # 開啟 Modal
        client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "callback_id": "customer_info_modal",
                "private_metadata": private_metadata,
                "title": {"type": "plain_text", "text": "客戶資訊"},
                "submit": {"type": "plain_text", "text": "開始分析"},
                "close": {"type": "plain_text", "text": "取消"},
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "customer_id_block",
                        "label": {"type": "plain_text", "text": "客戶編號"},
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "customer_id_input",
                            "placeholder": {"type": "plain_text", "text": "例如：CUST-12345"}
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "customer_name_block",
                        "label": {"type": "plain_text", "text": "客戶名稱"},
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "customer_name_input",
                            "placeholder": {"type": "plain_text", "text": "例如：王小明餐廳"}
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "customer_phone_block",
                        "label": {"type": "plain_text", "text": "客戶電話"},
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "customer_phone_input",
                            "placeholder": {"type": "plain_text", "text": "例如：0912345678"}
                        },
                        "optional": True
                    },
                    {
                        "type": "input",
                        "block_id": "notes_block",
                        "label": {"type": "plain_text", "text": "備註（可選）"},
                        "optional": True,
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "notes_input",
                            "multiline": True,
                            "placeholder": {"type": "plain_text", "text": "對話關鍵重點、特殊需求等"}
                        }
                    }
                ]
            }
        )
        logger.info(f"Modal opened for file: {file_id}")

    except SlackApiError as e:
        logger.error(f"Error opening modal: {e.response['error']}")
    except Exception as e:
        logger.error(f"Unexpected error in handle_analyze_button: {e}", exc_info=True)


@app.view("customer_info_modal")
def handle_modal_submission(ack, body, client, view, logger):
    """
    處理 Modal 提交，建立 Firestore case 並觸發分析流程。
    """
    if db is None:
        ack(response_action="errors", errors={
            "customer_name_block": "系統尚未啟用 Firestore，請聯絡管理員。"
        })
        return

    try:
        metadata = json.loads(view.get("private_metadata") or "{}")
    except json.JSONDecodeError:
        metadata = {}

    user_id = body["user"]["id"]
    file_id = metadata.get("file_id") or view.get("private_metadata")
    channel_id = metadata.get("channel_id") or user_id
    message_ts = metadata.get("message_ts")
    thread_ts = metadata.get("thread_ts") or message_ts

    values = view["state"]["values"]
    customer_id = values["customer_id_block"]["customer_id_input"]["value"].strip()
    customer_name = values["customer_name_block"]["customer_name_input"]["value"].strip()
    customer_phone_raw = ""
    if "customer_phone_block" in values and "customer_phone_input" in values["customer_phone_block"]:
        customer_phone_raw = values["customer_phone_block"]["customer_phone_input"].get("value", "") or ""
    notes = ""
    if "notes_block" in values and "notes_input" in values["notes_block"]:
        notes = values["notes_block"]["notes_input"].get("value", "") or ""

    logger.info(
        "Modal submitted: file_id=%s customer_id=%s user=%s channel=%s",
        file_id,
        customer_id,
        user_id,
        channel_id,
    )

    # 檢查基本設定
    missing_config = []
    if not SLACK_BOT_TOKEN:
        missing_config.append("SLACK_BOT_TOKEN")
    if not AUDIO_BUCKET:
        missing_config.append("SLACK_AUDIO_BUCKET")
    if not TASK_QUEUE:
        missing_config.append("TRANSCRIPTION_TASK_QUEUE")
    if not TASK_HANDLER_URL:
        missing_config.append("TRANSCRIPTION_TASK_HANDLER_URL")

    if missing_config:
        ack(response_action="errors", errors={
            "customer_name_block": f"系統設定缺少：{', '.join(missing_config)}。請聯絡管理員。"
        })
        return

    # 驗證手機（若有提供）
    clean_phone = re.sub(r"[^\d]", "", customer_phone_raw)
    if customer_phone_raw and not re.fullmatch(r"09\d{8}", clean_phone):
        ack(response_action="errors", errors={
            "customer_phone_block": "請輸入正確的台灣手機格式（例如：0912345678）。"
        })
        return

    # 取得 Slack 檔案與使用者資訊
    try:
        file_info_response = client.files_info(file=file_id)
        file_info = file_info_response.get("file", {})
    except SlackApiError as e:
        logger.error("Failed to fetch Slack file info: %s", e.response["error"])
        ack(response_action="errors", errors={
            "customer_name_block": "無法取得音檔資訊，請稍後再試。"
        })
        return

    try:
        user_info = client.users_info(user=user_id).get("user", {})
    except SlackApiError as e:
        logger.error("Failed to fetch Slack user info: %s", e.response["error"])
        ack(response_action="errors", errors={
            "customer_name_block": "無法取得使用者資訊，請稍後再試。"
        })
        return

    sales_rep_email = user_info.get("profile", {}).get("email", "")
    sales_rep_name = user_info.get("profile", {}).get("real_name") or user_info.get("profile", {}).get("display_name") or ""

    firestore_unit = "IC"
    firestore_user_doc = None
    if sales_rep_email:
        firestore_user_doc = db.collection("users").document(sales_rep_email).get()
        if firestore_user_doc.exists:
            firestore_unit = firestore_user_doc.to_dict().get("unit", "IC") or "IC"
    sales_rep = {
        "slack_id": user_id,
        "email": sales_rep_email,
        "name": sales_rep_name,
        "unit": firestore_unit,
    }

    customer = {
        "id": customer_id,
        "name": customer_name,
        "phone": clean_phone,
    }

    file_metadata = {
        "id": file_id,
        "name": file_info.get("name", f"{file_id}.m4a"),
        "size": file_info.get("size"),
        "type": file_info.get("filetype"),
        "duration": (file_info.get("duration_ms") or 0) / 1000,
        "mimetype": file_info.get("mimetype"),
        "url_private": file_info.get("url_private"),
        "url_private_download": file_info.get("url_private_download"),
    }

    processed_ref = db.collection("processed_files").document(file_id)

    def run_transaction(transaction: firestore.Transaction):
        snapshot = processed_ref.get(transaction=transaction)
        if snapshot.exists:
            return {
                "can_process": False,
                "existing": snapshot.to_dict(),
            }

        case_id, counter_doc = allocate_case_id(db, transaction, sales_rep.get("unit", "IC"))
        case_ref = db.collection("cases").document(case_id)

        case_doc = build_initial_case_document(
            case_id=case_id,
            customer=customer,
            sales_rep=sales_rep,
            file_info=file_metadata,
            channel_id=channel_id,
            message_ts=message_ts,
            thread_ts=thread_ts,
            notes=notes,
        )

        processed_doc = build_processed_file_document(
            case_id=case_id,
            file_info=file_metadata,
            customer=customer,
            sales_rep=sales_rep,
            channel_id=channel_id,
            message_ts=message_ts,
            thread_ts=thread_ts,
        )

        transaction.set(case_ref, case_doc)
        transaction.set(processed_ref, processed_doc)

        return {
            "can_process": True,
            "case_id": case_id,
        }

    try:
        transaction = db.transaction()
        txn_result = run_transaction(transaction)
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Firestore transaction failed: %s", e, exc_info=True)
        ack(response_action="errors", errors={
            "customer_name_block": "系統忙碌中，請稍後再試。"
        })
        return

    if not txn_result.get("can_process"):
        existing = txn_result.get("existing", {})
        existing_case_id = existing.get("caseId", "未知")
        status = existing.get("status", "processing")
        ack(response_action="errors", errors={
            "customer_id_block": f"此音檔已在案件 {existing_case_id} ({status}) 中處理。"
        })
        return

    case_id = txn_result["case_id"]
    case_ref = db.collection("cases").document(case_id)

    # 交易成功後立即回覆 Slack，避免逾時
    ack()

    logger.info("Case %s created for file %s by user %s", case_id, file_id, user_id)

    gcs_path = None
    local_path: Optional[str] = None

    try:
        temp_path = download_slack_file(file_metadata, SLACK_BOT_TOKEN)
        local_path = str(temp_path)

        safe_name = file_metadata["name"].replace(" ", "_")
        destination_blob = f"slack/{case_id}/{safe_name}"
        gcs_path = upload_to_gcs(temp_path, AUDIO_BUCKET, destination_blob)

        delete_at = datetime.now(timezone.utc) + timedelta(days=7)
        case_ref.update({
            "audio.gcsPath": gcs_path,
            "audio.originalUrl": file_metadata.get("url_private"),
            "audio.deleteAt": delete_at,
            "status": "transcribing",
            "updatedAt": firestore.SERVER_TIMESTAMP,
            "customerPhone": clean_phone,
            "notes": notes or "",
        })

        processed_ref.update({
            "status": "queued",
            "gcsPath": gcs_path,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })

        enqueue_transcription_task(
            case_id=case_id,
            gcs_path=gcs_path,
            queue=TASK_QUEUE,
            location=TASK_LOCATION,
            project=project_id,
            handler_url=TASK_HANDLER_URL,
            service_account_email=TASK_SERVICE_ACCOUNT,
        )

        processed_ref.update({
            "taskEnqueuedAt": firestore.SERVER_TIMESTAMP,
        })

        confirmation_text = (
            f"✅ *案件已建立並開始分析*\n\n"
            f"📁 案件編號：`{case_id}`\n"
            f"🏪 客戶名稱：{customer_name}\n"
            f"📞 客戶電話：{clean_phone or '未提供'}\n"
            f"📝 備註：{notes or '無'}\n\n"
            f"🎯 我們會在分析完成後自動通知您。"
        )

        client.chat_postMessage(
            channel=channel_id,
            text=confirmation_text,
        )

        if channel_id and message_ts:
            try:
                client.chat_update(
                    channel=channel_id,
                    ts=message_ts,
                    text=f"🎧 *{file_metadata['name']}* 已開始分析，案件 `{case_id}`。",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"🎧 *{file_metadata['name']}* 已開始分析。\n案件編號：`{case_id}`",
                            },
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": "⏱️ 轉錄約需 5-10 分鐘，完成後會通知您。",
                                }
                            ],
                        },
                    ],
                )
            except SlackApiError as update_error:
                logger.warning("Failed to update Slack message: %s", update_error.response["error"])

    except Exception as e:  # pylint: disable=broad-except
        logger.error("Failed to process Slack submission: %s", e, exc_info=True)

        processed_ref.update({
            "status": "failed",
            "error": str(e),
            "locked": False,
            "failedAt": firestore.SERVER_TIMESTAMP,
        })

        case_ref.update({
            "status": "failed",
            "error": str(e),
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })

        try:
            client.chat_postMessage(
                channel=channel_id,
                text="❌ 系統處理音檔時發生錯誤，請稍後再試或聯絡技術支援。",
            )
        except SlackApiError as notify_error:
            logger.error("Unable to notify user about failure: %s", notify_error.response["error"])

    finally:
        if local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
            except OSError:
                logger.warning("Failed to remove temp file: %s", local_path)


# ============================================
# Flask Routes
# ============================================

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """
    處理 Slack Events API 請求（包含 URL verification）
    """
    return handler.handle(request)


@flask_app.route("/slack/interactions", methods=["POST"])
def slack_interactions():
    """
    處理 Slack 互動事件（按鈕點擊、Modal 提交）
    """
    return handler.handle(request)


@flask_app.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint for Cloud Run
    """
    return {"status": "healthy", "service": "slack-app"}, 200


@flask_app.route("/", methods=["GET"])
def index():
    """
    Root endpoint
    """
    return {"message": "Sales AI Slack App is running"}, 200


# ============================================
# Application Entry Point
# ============================================

if __name__ == "__main__":
    # 本地開發用
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting Slack App (HTTP Mode) on port {port}...")
    flask_app.run(host="0.0.0.0", port=port, debug=False)
