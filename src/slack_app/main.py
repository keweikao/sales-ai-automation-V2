"""
Slack App for Sales AI Automation - HTTP Mode (Cloud Run)
處理音檔上傳、客戶資料收集、並觸發 AI 分析流程
支持 Agent 8 業務主管智能問答
"""
import json
import logging
import os
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple

from flask import Flask, request
from google.cloud import firestore
from google.cloud import tasks_v2
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from utils.case_management import (
    allocate_case_id,
    build_initial_case_document,
    build_processed_file_document,
)
from utils.file_pipeline import (
    download_slack_file,
    convert_audio,
    enqueue_transcription_task,
    upload_to_gcs,
)

from notifications.summary_delivery import DeliveryResult, SummaryDeliveryService
from interactions.summary_editor import SummaryEditor
from interactions.summary_sender import SummarySender

# 設定 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化 Firestore（若未設定專案 ID 則嘗試使用預設設定）
project_id = os.environ.get("GCP_PROJECT_ID")
db = None
try:
    if project_id:
        db = firestore.Client(project=project_id)
    else:
        db = firestore.Client()
        logger.warning("GCP_PROJECT_ID 未設定，改用預設專案：%s", db.project)
except Exception as firestore_error:
    logger.error("初始化 Firestore 失敗：%s", firestore_error)
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
PROGRESS_SHARED_TOKEN = os.getenv("SLACK_PROGRESS_TOKEN") or os.getenv("TRANSCRIPTION_PROGRESS_TOKEN")
SUMMARY_DELIVERY_QUEUE = os.getenv("SUMMARY_DELIVERY_QUEUE")
SUMMARY_DELIVERY_LOCATION = os.getenv("SUMMARY_DELIVERY_LOCATION", "asia-east1")
SUMMARY_DELIVERY_HANDLER_URL = os.getenv("SUMMARY_DELIVERY_HANDLER_URL")
SUMMARY_INTERNAL_TOKEN = os.getenv("SUMMARY_INTERNAL_TOKEN") or PROGRESS_SHARED_TOKEN
SUMMARY_BASE_URL = os.getenv("SUMMARY_BASE_URL")
SHORT_URL_BASE = os.getenv("SHORT_URL_BASE")

slack_client: Optional[WebClient] = WebClient(token=SLACK_BOT_TOKEN) if SLACK_BOT_TOKEN else None
summary_editor: Optional[SummaryEditor] = None
summary_sender: Optional[SummarySender] = None
summary_delivery_service: Optional[SummaryDeliveryService] = None
if slack_client and db:

    try:
        summary_editor = SummaryEditor(slack_client, db)
        logger.info("Summary editor initialized successfully")
    except Exception as notifier_error:  # pylint: disable=broad-except
        logger.error("Failed to initialize summary editor: %s", notifier_error, exc_info=True)

    try:
        summary_sender = SummarySender(slack_client, db)
        logger.info("Summary sender initialized successfully")
    except Exception as notifier_error:  # pylint: disable=broad-except
        logger.error("Failed to initialize summary editor: %s", notifier_error, exc_info=True)

    try:
        summary_delivery_service = SummaryDeliveryService(
            db_client=db,
            summary_base_url=SUMMARY_BASE_URL,
            short_url_base=SHORT_URL_BASE,
        )
        logger.info("Summary delivery service initialized successfully")
    except Exception as notifier_error:  # pylint: disable=broad-except
        logger.error("Failed to initialize summary delivery service: %s", notifier_error, exc_info=True)

# ============================================
# Command Handlers
# ============================================



# ============================================
# Event Handlers
# ============================================

@firestore.transactional
def check_and_create_notified_record(transaction, file_ref, file_id, file_name, user_id):
    """
    Atomically checks if a file record exists and creates it if it doesn't.
    Returns the existing document if found, otherwise None.
    """
    snapshot = file_ref.get(transaction=transaction)
    if snapshot.exists:
        return snapshot.to_dict()
    
    new_doc = {
        "fileId": file_id,
        "fileName": file_name,
        "userId": user_id,
        "status": "notified",
        "notifiedAt": firestore.SERVER_TIMESTAMP,
    }
    transaction.set(file_ref, new_doc)
    return None


@app.event("file_shared")
def handle_file_shared(client, event, logger):
    """
    處理音檔上傳事件（僅處理 DM），使用 Transaction 防止重複處理。
    """
    try:
        if not db:
            logger.error("Firestore 尚未初始化，無法處理 file_shared 事件")
            client.chat_postMessage(
                channel=event.get("user_id"),
                text="⚠️ 系統尚未連線到 Firestore，暫時無法處理音檔。請通知開發團隊。"
            )
            return

        file_id = event.get("file_id")
        user_id = event.get("user_id")

        if not file_id or not user_id:
            logger.warning(f"Missing file_id or user_id in event: {event}")
            return

        # 取得檔案基本資訊
        file_info_response = client.files_info(file=file_id)
        file_info = file_info_response.get("file", {})
        file_name = file_info.get("name", "Unknown")
        
        # 使用 Transaction 檢查並建立初始紀錄
        file_ref = db.collection("processed_files").document(file_id)
        transaction = db.transaction()
        existing_doc = check_and_create_notified_record(transaction, file_ref, file_id, file_name, user_id)

        if existing_doc:
            logger.info(f"Duplicate file_shared event for file_id: {file_id}. Ignoring.")
            return
        else:
            # 如果 existing_doc 是 None，表示新紀錄已成功建立，可以繼續後續流程
            logger.info(f"New file {file_id} record created atomically.")

        # 檔案驗證
        from utils.file_validator import validate_audio_file, FileValidationError
        try:
            validate_audio_file(file_info)
        except FileValidationError as e:
            # 發送使用者友善的錯誤訊息
            client.chat_postMessage(
                channel=user_id,
                text=e.user_friendly_message
            )
            logger.warning(f"File validation failed for {file_id}: {e.message}")
            return
        except Exception as e:
            # 未預期的錯誤
            client.chat_postMessage(
                channel=user_id,
                text="⚠️ 檔案驗證時發生錯誤，請稍後再試或聯絡技術支援。"
            )
            logger.error(f"Unexpected error during file validation for {file_id}: {e}", exc_info=True)
            return

        client.chat_postMessage(
            channel=user_id,
            thread_ts=event.get("ts"), # Add this line to make it a thread reply
            text=f"📎 收到音檔：*{file_name}*\n請點擊下方按鈕補充客戶資訊以開始分析。",
            blocks=[
                {"type": "section", "text": {"type": "mrkdwn", "text": f"📎 收到音檔：*{file_name}*\n\n請點擊下方按鈕補充客戶資訊以開始分析。"}},
                {"type": "actions", "block_id": "audio_actions", "elements": [{"type": "button", "text": {"type": "plain_text", "text": "🎯 分析此錄音"}, "style": "primary", "action_id": "analyze_audio_button", "value": file_id}]}
            ]
        )
        logger.info(f"Audio file detected: {file_id} ({file_name}) from user {user_id}, prompt sent.")

    except SlackApiError as e:
        logger.error(f"Slack API error in handle_file_shared: {e.response['error']}")
    except Exception as e:
        logger.error(f"Unexpected error in handle_file_shared: {e}", exc_info=True)


@app.event("message")
def handle_message_events(body, logger):
    """
    Handles message events. Specifically ignores message events with a
    'file_share' subtype to prevent duplicate processing, as these are
    also handled by the 'file_shared' event.
    """
    subtype = body.get("event", {}).get("subtype")
    if subtype == "file_share":
        file_id = body.get("event", {}).get("files", [{}])[0].get("id")
        logger.info(f"Ignoring message event with subtype 'file_share' for file_id: {file_id} to prevent duplicate handling.")
        return
    
    # Log other unhandled message subtypes for debugging, if any
    logger.warning(f"Unhandled message event with subtype: {subtype}")


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
                    # === 基本資訊區塊 ===
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": "📋 基本資訊", "emoji": True}
                    },
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
                        "label": {"type": "plain_text", "text": "店名"},
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
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "customer_email_block",
                        "label": {"type": "plain_text", "text": "客戶 Email"},
                        "optional": True,
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "customer_email_input",
                            "placeholder": {"type": "plain_text", "text": "例如：customer@example.com"}
                        }
                    },
                    # === Demo Meta 區塊 ===
                    {
                        "type": "divider"
                    },
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": "📊 Demo 資訊", "emoji": True}
                    },
                    {
                        "type": "input",
                        "block_id": "store_type_block",
                        "label": {"type": "plain_text", "text": "店型"},
                        "element": {
                            "type": "static_select",
                            "action_id": "store_type_input",
                            "placeholder": {"type": "plain_text", "text": "請選擇店型"},
                            "options": [
                                {"text": {"type": "plain_text", "text": "☕ 咖啡廳"}, "value": "cafe"},
                                {"text": {"type": "plain_text", "text": "🧋 飲料店"}, "value": "beverage"},
                                {"text": {"type": "plain_text", "text": "🍲 火鍋"}, "value": "hotpot"},
                                {"text": {"type": "plain_text", "text": "🥩 燒肉/燒烤"}, "value": "bbq"},
                                {"text": {"type": "plain_text", "text": "🍜 小吃/麵食"}, "value": "snack"},
                                {"text": {"type": "plain_text", "text": "🍽️ 餐廳"}, "value": "restaurant"},
                                {"text": {"type": "plain_text", "text": "🍸 餐酒館/酒吧"}, "value": "bar"},
                                {"text": {"type": "plain_text", "text": "🍔 速食/外帶"}, "value": "fastfood"},
                                {"text": {"type": "plain_text", "text": "📦 其他"}, "value": "other"},
                            ]
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "service_type_block",
                        "label": {"type": "plain_text", "text": "營運型態"},
                        "element": {
                            "type": "static_select",
                            "action_id": "service_type_input",
                            "placeholder": {"type": "plain_text", "text": "請選擇營運型態"},
                            "options": [
                                {"text": {"type": "plain_text", "text": "🪑 純內用"}, "value": "dine_in_only"},
                                {"text": {"type": "plain_text", "text": "🥡 純外帶"}, "value": "takeout_only"},
                                {"text": {"type": "plain_text", "text": "🍽️ 主內用、外帶輔"}, "value": "dine_in_main"},
                                {"text": {"type": "plain_text", "text": "📦 主外帶、內用輔"}, "value": "takeout_main"},
                            ]
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "decision_maker_block",
                        "label": {"type": "plain_text", "text": "老闆本人在場？"},
                        "element": {
                            "type": "static_select",
                            "action_id": "decision_maker_input",
                            "placeholder": {"type": "plain_text", "text": "請選擇"},
                            "options": [
                                {"text": {"type": "plain_text", "text": "✅ 是，老闆本人"}, "value": "yes"},
                                {"text": {"type": "plain_text", "text": "❌ 否，是員工/店長"}, "value": "no"},
                            ]
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "current_pos_block",
                        "label": {"type": "plain_text", "text": "現有 POS 系統"},
                        "element": {
                            "type": "static_select",
                            "action_id": "current_pos_input",
                            "placeholder": {"type": "plain_text", "text": "請選擇"},
                            "options": [
                                {"text": {"type": "plain_text", "text": "🆕 無 (新開店)"}, "value": "none"},
                                {"text": {"type": "plain_text", "text": "🔄 iCHEF 舊用戶"}, "value": "ichef_old"},
                                {"text": {"type": "plain_text", "text": "肚肚"}, "value": "dudu"},
                                {"text": {"type": "plain_text", "text": "EZTABLE"}, "value": "eztable"},
                                {"text": {"type": "plain_text", "text": "其他 POS 品牌"}, "value": "other_pos"},
                                {"text": {"type": "plain_text", "text": "🧮 傳統收銀機"}, "value": "traditional"},
                                {"text": {"type": "plain_text", "text": "📝 手寫單/無系統"}, "value": "manual"},
                            ]
                        }
                    },
                    # === 備註區塊 ===
                    {
                        "type": "divider"
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
    
    customer_email = ""
    if "customer_email_block" in values and "customer_email_input" in values["customer_email_block"]:
        customer_email = values["customer_email_block"]["customer_email_input"].get("value", "") or ""
        customer_email = customer_email.strip()
    
    notes = ""
    if "notes_block" in values and "notes_input" in values["notes_block"]:
        notes = values["notes_block"]["notes_input"].get("value", "") or ""

    # === Demo Meta 欄位 ===
    store_type = ""
    if "store_type_block" in values and "store_type_input" in values["store_type_block"]:
        selected = values["store_type_block"]["store_type_input"].get("selected_option")
        store_type = selected.get("value", "") if selected else ""
    
    service_type = ""
    if "service_type_block" in values and "service_type_input" in values["service_type_block"]:
        selected = values["service_type_block"]["service_type_input"].get("selected_option")
        service_type = selected.get("value", "") if selected else ""
    
    decision_maker_onsite = None
    if "decision_maker_block" in values and "decision_maker_input" in values["decision_maker_block"]:
        selected = values["decision_maker_block"]["decision_maker_input"].get("selected_option")
        if selected:
            decision_maker_onsite = selected.get("value", "") == "yes"
    
    current_pos = ""
    if "current_pos_block" in values and "current_pos_input" in values["current_pos_block"]:
        selected = values["current_pos_block"]["current_pos_input"].get("selected_option")
        current_pos = selected.get("value", "") if selected else ""
    
    # Build demo_meta object
    demo_meta = {
        "store_type": store_type,
        "service_type": service_type,
        "decision_maker_onsite": decision_maker_onsite,
        "current_pos": current_pos,
    }

    logger.info(
        "Modal submitted: file_id=%s customer_id=%s user=%s channel=%s",
        file_id,
        customer_id,
        user_id,
        channel_id,
    )

    # 驗證手機（必填） - 在 ack() 之前驗證
    if not customer_phone_raw or not customer_phone_raw.strip():
        ack(response_action="errors", errors={
            "customer_phone_block": "客戶電話為必填欄位，請輸入手機號碼。"
        })
        return
    
    clean_phone = re.sub(r"[^\d]", "", customer_phone_raw)
    if not re.fullmatch(r"09\d{8}", clean_phone):
        ack(response_action="errors", errors={
            "customer_phone_block": "請輸入正確的台灣手機格式（例如：0912345678）。"
        })
        return

    # 檢查基本設定 - 在 ack() 之前檢查
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

    # 立即確認以避免 Slack 3 秒超時
    ack()

    # 嘗試立即更新原訊息，讓使用者看到「錄音檔上傳中」狀態並避免重複點擊
    initial_file_info: Optional[dict] = None
    if channel_id and message_ts:
        try:
            file_info_response = client.files_info(file=file_id)
            initial_file_info = file_info_response.get("file", {})
        except SlackApiError as fetch_error:
            logger.warning("Failed to fetch file info for status update: %s", fetch_error.response.get("error", fetch_error))

        status_filename = (initial_file_info or {}).get("name") or f"檔案 {file_id}"
        try:
            client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text=f"⏳ {status_filename} 錄音檔上傳中…",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"📎 *{status_filename}*\n⏳ 錄音檔上傳中，請稍候…",
                        },
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "⚠️ 上傳期間請勿重複送出，以避免建立重複案件。",
                            }
                        ],
                    },
                ],
            )
        except SlackApiError as update_error:
            logger.warning("Failed to update Slack message to uploading state: %s", update_error.response.get("error", update_error))

    # 將後續處理放到後台線程，避免被 Slack Bolt 中斷
    def process_in_background(file_info_payload: Optional[dict] = initial_file_info):
        try:
            _process_modal_submission(
                file_id=file_id,
                customer_id=customer_id,
                customer_name=customer_name,
                customer_phone_raw=customer_phone_raw,
                clean_phone=clean_phone,
                customer_email=customer_email,
                notes=notes,
                user_id=user_id,
                channel_id=channel_id,
                message_ts=message_ts,
                thread_ts=thread_ts,
                file_info=file_info_payload,
                demo_meta=demo_meta,
                client=client,
                logger=logger,
            )
        except Exception as e:
            logger.error(f"Background processing failed: {e}", exc_info=True)

    # 啟動後台線程
    thread = threading.Thread(target=process_in_background, daemon=False)
    thread.start()


def _process_modal_submission(
    file_id: str,
    customer_id: str,
    customer_name: str,
    customer_phone_raw: str,
    clean_phone: str,
    customer_email: str,
    notes: str,
    user_id: str,
    channel_id: str,
    message_ts: str,
    thread_ts: str,
    file_info: Optional[dict],
    demo_meta: dict,
    client,
    logger,
):
    """後台處理 Modal 提交的實際邏輯"""
    import sys
    logger.info("=== Background thread started for file %s ===", file_id)
    sys.stdout.flush()  # Force flush to ensure logs are written

    # 取得 Slack 檔案與使用者資訊
    try:
        if not file_info:
            logger.info("Fetching file info from Slack for file %s", file_id)
            sys.stdout.flush()
            file_info_response = client.files_info(file=file_id)
            file_info = file_info_response.get("file", {})
    except SlackApiError as e:
        logger.error("Failed to fetch Slack file info: %s", e.response["error"])
        try:
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=f"❌ 無法取得音檔資訊，請稍後再試。\n錯誤：{e.response['error']}"
            )
        except Exception as notify_error:
            logger.error(f"Failed to send error notification: {notify_error}")
        return

    try:
        user_info = client.users_info(user=user_id).get("user", {})
    except SlackApiError as e:
        logger.error("Failed to fetch Slack user info: %s", e.response["error"])
        try:
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=f"❌ 無法取得使用者資訊，請稍後再試。\n錯誤：{e.response['error']}"
            )
        except Exception as notify_error:
            logger.error(f"Failed to send error notification: {notify_error}")
        return

    sales_rep_email = user_info.get("profile", {}).get("email", "")
    sales_rep_name = user_info.get("profile", {}).get("real_name") or user_info.get("profile", {}).get("display_name") or ""
    sales_rep_display_name = user_info.get("profile", {}).get("display_name") or sales_rep_name

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
        "slack_display_name": sales_rep_display_name,
        "unit": firestore_unit,
    }

    customer = {
        "id": customer_id,
        "name": customer_name,
        "phone": clean_phone,
        "email": customer_email,
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

    @firestore.transactional
    def run_transaction(transaction: firestore.Transaction):
        snapshot = processed_ref.get(transaction=transaction)
        
        existing_processed_data = snapshot.to_dict() if snapshot.exists else {}
        existing_case_id = (existing_processed_data or {}).get("caseId")

        # Treat placeholder values (e.g. "未知") as missing so we don't block processing
        # for records created before the case ID was assigned.
        if isinstance(existing_case_id, str):
            if existing_case_id.strip().lower() in {"", "未知", "unknown", "not_set"}:
                existing_case_id = None

        if existing_case_id:
            # Document exists and already has a real caseId, so it's fully processed.
            return {
                "can_process": False,
                "existing": existing_processed_data,
            }
        
        if not snapshot.exists:
            # This should not happen. The initial 'notified' record should exist.
            # If it doesn't, it's an inconsistency.
            logger.error(f"Processed file record {file_id} not found during modal submission transaction. This indicates an inconsistency.")
            raise ValueError(f"Processed file record {file_id} not found.")

        # If we reach here, the processed_files document exists but does not have a caseId.
        # Allocate a new case ID and create the case document.
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
            demo_meta=demo_meta,
        )
        transaction.set(case_ref, case_doc) # Create the case document

        # Update the existing processed_files document with the new caseId and status.
        # Merge with existing data to preserve fields from handle_file_shared.
        updated_processed_data = {
            **existing_processed_data, # Preserve existing fields
            "caseId": case_id,
            "status": "processing", # Set status to processing
            "updatedAt": firestore.SERVER_TIMESTAMP,
            "locked": True,
            "lockedAt": firestore.SERVER_TIMESTAMP,
            "processedBy": sales_rep.get("slack_id", ""),
            "channelId": channel_id,
            "messageTs": message_ts,
            "threadTs": thread_ts or message_ts,
            "fileName": file_info.get("name", ""), # Redundant but safe
            "fileSize": file_info.get("size"), # Redundant but safe
            "customerName": customer.get("name", ""),
            "customerId": customer.get("id", ""),
            "customerPhone": customer.get("phone", "") or "",
            "submittedAt": firestore.SERVER_TIMESTAMP,
        }
        transaction.set(processed_ref, updated_processed_data) # Update the existing document

        return {
            "can_process": True,
            "case_id": case_id,
        }

    try:
        txn_result = run_transaction(db.transaction())
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Firestore transaction failed: %s", e, exc_info=True)
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=f"❌ 系統忙碌中，請稍後再試。\n錯誤：{str(e)[:200]}"
        )
        return

    if not txn_result.get("can_process"):
        existing = txn_result.get("existing", {})
        existing_case_id = existing.get("caseId", "未知")
        status = existing.get("status", "processing")
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=f"⚠️ 此音檔已在案件 `{existing_case_id}` ({status}) 中處理。"
        )
        return

    case_id = txn_result["case_id"]
    case_ref = db.collection("cases").document(case_id)

    logger.info("Case %s created for file %s by user %s", case_id, file_id, user_id)
    sys.stdout.flush()

    gcs_path = None
    local_path: Optional[str] = None

    try:
        logger.info("Downloading file from Slack: %s", file_metadata["name"])
        sys.stdout.flush()
        temp_path = download_slack_file(file_metadata, SLACK_BOT_TOKEN)
        local_path = str(temp_path)
        logger.info("File downloaded to: %s", local_path)
        sys.stdout.flush()

        # Convert audio to 16k MP3
        try:
            converted_path = convert_audio(Path(local_path))
            local_path = str(converted_path)
            logger.info("Audio converted to: %s", local_path)
        except Exception as conv_error:
            logger.error("Audio conversion failed: %s", conv_error)
            # Fallback to original file if conversion fails? 
            # Or fail hard? User wants conversion to fix error, so maybe fail hard or log warning.
            # Let's log warning and try original, but likely it will fail transcription again.
            # Actually, let's proceed with converted path if successful.
            pass

        safe_name = re.sub(r'\s+', '_', file_metadata["name"])
        # Update extension in destination blob if converted
        if local_path.endswith(".mp3"):
             safe_name = Path(safe_name).with_suffix(".mp3").name

        destination_blob = f"slack/{case_id}/{safe_name}"
        logger.info("Uploading to GCS: %s", destination_blob)
        sys.stdout.flush()
        gcs_path = upload_to_gcs(Path(local_path), AUDIO_BUCKET, destination_blob)
        logger.info("File uploaded to GCS: %s", gcs_path)
        sys.stdout.flush()

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

        logger.info("Enqueuing transcription task for case %s", case_id)
        logger.info("Task details: queue=%s, location=%s, handler_url=%s", TASK_QUEUE, TASK_LOCATION, TASK_HANDLER_URL)
        sys.stdout.flush()

        try:
            task_response = enqueue_transcription_task(
                case_id=case_id,
                gcs_path=gcs_path,
                queue=TASK_QUEUE,
                location=TASK_LOCATION,
                project=project_id,
                handler_url=TASK_HANDLER_URL,
                service_account_email=TASK_SERVICE_ACCOUNT,
                file_id=file_id,
            )
            logger.info("Transcription task enqueued successfully: %s", task_response.name)
            sys.stdout.flush()

            processed_ref.update({
                "taskEnqueuedAt": firestore.SERVER_TIMESTAMP,
                "taskName": task_response.name,
            })
        except Exception as task_error:
            logger.error("Failed to enqueue transcription task: %s", task_error, exc_info=True)
            sys.stdout.flush()
            # Update case with error but don't fail the entire process
            case_ref.update({
                "taskEnqueueError": str(task_error),
                "updatedAt": firestore.SERVER_TIMESTAMP,
            })
            # Re-raise to be caught by outer exception handler
            raise

        confirmation_text = (
            f"✅ *案件已建立並開始轉錄與分析*\n\n"
            f"📁 案件編號：`{case_id}`\n"
            f"👤 客戶編號：`{customer_id}`\n"
            f"🏪 客戶名稱：{customer_name}\n"
            f"📞 客戶電話：{clean_phone or '未提供'}\n"
            f"📝 備註：{notes or '無'}\n\n"
            f"🎯 我們會在分析完成後自動通知您。"
        )

        logger.info("Sending confirmation message to channel %s, thread %s", channel_id, thread_ts)
        sys.stdout.flush()
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=confirmation_text,
        )
        logger.info("Confirmation message sent successfully")
        sys.stdout.flush()

        if channel_id and message_ts:
            try:
                client.chat_update(
                    channel=channel_id,
                    ts=message_ts,
                    text=f"案件編號：`{case_id}` 📁 音檔已完成上傳，等待 Batch 傳送轉錄...",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"案件編號：`{case_id}` 📁 音檔已完成上傳，等待 Batch 傳送轉錄...",
                            },
                        },
                    ],
                )
            except SlackApiError as update_error:
                logger.warning("Failed to update Slack message: %s", update_error.response["error"])

    except Exception as e:  # pylint: disable=broad-except
        logger.error("Failed to process Slack submission: %s", e, exc_info=True)

        try:
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

            client.chat_postMessage(
                channel=channel_id,
                text=f"❌ 系統處理音檔時發生錯誤，請稍後再試或聯絡技術支援。\n錯誤詳情：{str(e)[:200]}",
            )
        except Exception as notify_error:
            logger.error("Unable to notify user about failure: %s", notify_error, exc_info=True)

    finally:
        if local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
            except OSError:
                logger.warning("Failed to remove temp file: %s", local_path)


def _resolve_notification_target(case_id: str, file_id: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Locate Slack channel/thread for a given case/file to post progress updates.
    Returns (channel_id, thread_ts, customer_name, user_id).

    Fallback strategy:
    1. Try original thread (channel_id + thread_ts)
    2. If thread unavailable, try channel without thread
    3. If channel unavailable, try user DM
    """
    if not db:
        return None, None, None, None

    channel_id = thread_ts = customer_name = user_id = None

    case_snapshot = db.collection("cases").document(case_id).get()
    if case_snapshot.exists:
        case_data = case_snapshot.to_dict() or {}
        customer_name = case_data.get("customerName")
        notification = case_data.get("notification") or {}
        channel_id = notification.get("slackChannelId")
        thread_ts = notification.get("slackThreadTs") or notification.get("messageTs")
        user_id = notification.get("slackUserId")  # For DM fallback

    if not channel_id and file_id:
        file_snapshot = db.collection("processed_files").document(file_id).get()
        if file_snapshot.exists:
            file_data = file_snapshot.to_dict() or {}
            channel_id = channel_id or file_data.get("channelId")
            thread_ts = thread_ts or file_data.get("threadTs") or file_data.get("messageTs")
            customer_name = customer_name or file_data.get("customerName")
            user_id = user_id or file_data.get("userId")

    return channel_id, thread_ts, customer_name, user_id


def _send_notification_with_fallback(
    case_id: str,
    notifier_func,
    fallback_prefix: str,
    **notifier_kwargs
) -> Tuple[bool, str]:
    """
    Send notification with fallback strategy.

    Fallback strategy:
    1. Try original thread
    2. If thread deleted/unavailable, try channel without thread
    3. If channel unavailable, try user DM

    Returns (success, reason)
    """
    from slack_sdk.errors import SlackApiError

    try:
        success = notifier_func(**notifier_kwargs)
        if success:
            return True, "sent_to_thread"
        return False, "send_failed"

    except SlackApiError as e:
        error_code = e.response.get("error", "")
        logger.warning(f"Slack API error for {case_id}: {error_code}")

        # Thread is deleted or invalid
        if error_code in ["thread_not_found", "message_not_found", "channel_not_found"]:
            logger.info(f"Thread not available for {case_id}, trying fallback strategies")

            # Fallback 1: Try channel without thread
            if "user_id" in notifier_kwargs or "channel_id" in notifier_kwargs:
                channel = notifier_kwargs.get("user_id") or notifier_kwargs.get("channel_id")
                fallback_kwargs = notifier_kwargs.copy()
                fallback_kwargs["thread_ts"] = None

                try:
                    success = notifier_func(**fallback_kwargs)
                    if success:
                        logger.info(f"{fallback_prefix} notification sent to channel (no thread) for {case_id}")
                        _log_notification_fallback(case_id, "channel_without_thread", error_code)
                        return True, "sent_to_channel"
                except Exception as fallback_error:
                    logger.warning(f"Fallback to channel failed: {fallback_error}")

            # Fallback 2: Try user DM
            _, _, _, user_id = _resolve_notification_target(case_id, None)
            if user_id and user_id != notifier_kwargs.get("user_id"):
                dm_kwargs = notifier_kwargs.copy()
                dm_kwargs["user_id"] = user_id
                dm_kwargs["channel_id"] = user_id
                dm_kwargs["thread_ts"] = None

                try:
                    success = notifier_func(**dm_kwargs)
                    if success:
                        logger.info(f"{fallback_prefix} notification sent to user DM for {case_id}")
                        _log_notification_fallback(case_id, "user_dm", error_code)
                        return True, "sent_to_dm"
                except Exception as dm_error:
                    logger.error(f"Fallback to DM failed: {dm_error}")

        return False, f"fallback_failed_{error_code}"

    except Exception as e:
        logger.error(f"Unexpected error sending notification for {case_id}: {e}", exc_info=True)
        return False, "unexpected_error"


def _log_notification_fallback(case_id: str, fallback_type: str, original_error: str):
    """
    Log notification fallback to Firestore for tracking.
    """
    if not db:
        return

    try:
        db.collection("cases").document(case_id).update({
            "notification.fallback": {
                "type": fallback_type,
                "originalError": original_error,
                "timestamp": firestore.SERVER_TIMESTAMP,
            }
        })
    except Exception as e:
        logger.warning(f"Failed to log notification fallback for {case_id}: {e}")



def _notify_summary_delivery_result(
    case_id: str,
    result,
    channel_id: Optional[str],
    thread_ts: Optional[str],
    initiated_by: Optional[str] = None,
) -> None:
    """Post a status update back to Slack after summary delivery."""
    if not channel_id:
        resolved_channel, resolved_thread, _ = _resolve_notification_target(case_id, None)
        channel_id = resolved_channel
        thread_ts = thread_ts or resolved_thread

    if not (slack_client and channel_id):
        return

    status_map = {
        "sent": "✅ 已成功發送摘要簡訊給客戶",
        "failed": "⚠️ 摘要簡訊發送失敗，請稍後再試或聯絡技術支援",
        "skipped": "ℹ️ 尚未設定簡訊服務，已產生摘要連結供手動分享",
    }
    status_line = status_map.get(result.status, "摘要發送狀態：未知")
    lines = [
        status_line,
        f"🔗 摘要連結：{result.summary_url}",
    ]
    if result.phone:
        lines.append(f"📱 目標電話：{result.phone}")
    if result.error:
        lines.append(f"🧪 系統訊息：{result.error}")
    if initiated_by:
        lines.append(f"👤 操作人：<@{initiated_by}>")

    slack_client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        text="\n".join(lines),
    )


def _enqueue_summary_delivery_task(
    case_id: str,
    phone: str,
    initiated_by: str,
    channel_id: Optional[str],
    thread_ts: Optional[str],
) -> bool:
    """Enqueue Cloud Task to process summary delivery asynchronously."""
    if not (SUMMARY_DELIVERY_QUEUE and SUMMARY_DELIVERY_HANDLER_URL and project_id):
        return False

    try:
        client = tasks_v2.CloudTasksClient()
        parent = client.queue_path(project_id, SUMMARY_DELIVERY_LOCATION, SUMMARY_DELIVERY_QUEUE)
        payload = json.dumps(
            {
                "caseId": case_id,
                "phone": phone,
                "initiatedBy": initiated_by,
                "channelId": channel_id,
                "threadTs": thread_ts,
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if SUMMARY_INTERNAL_TOKEN:
            headers["X-Progress-Token"] = SUMMARY_INTERNAL_TOKEN

        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": SUMMARY_DELIVERY_HANDLER_URL,
                "headers": headers,
                "body": payload,
            }
        }

        client.create_task(request={"parent": parent, "task": task})
        logger.info("Enqueued summary delivery task for %s", case_id)
        return True
    except Exception as exc:  # noqa: broad-except
        logger.error("Failed to enqueue summary delivery task: %s", exc)
        return False


def _extract_case_id(value: Optional[str], prefix: str) -> Optional[str]:
    """
    Extract case id from button value helper.
    """
    if not value:
        return None
    if value.startswith(prefix):
        return value[len(prefix):]
    return value


# ============================================
# Interactive Components (Agent 7)
# ============================================


@app.action("edit_summary")
def handle_edit_summary_action(ack, body, logger):  # type: ignore[override]
    """
    Handle the Agent 7 "Edit summary" button.
    """
    ack()
    if not summary_editor:
        logger.warning("Summary editor unavailable; cannot open edit modal.")
        return

    trigger_id = body.get("trigger_id")
    actions = body.get("actions") or []
    action_value = actions[0].get("value") if actions else None
    case_id = _extract_case_id(action_value, "edit_summary_")
    if not (trigger_id and case_id):
        logger.warning("Missing trigger or case id in edit_summary action: %s", body)
        return

    summary_editor.open_edit_modal(trigger_id, case_id)


@app.action("send_to_customer")
def handle_send_to_customer_action(ack, body, logger):  # type: ignore[override]
    """
    Handle the "Send to Customer" button for Agent 4.
    """
    ack()
    if not summary_sender:
        logger.warning("Summary sender unavailable; cannot send SMS.")
        return

    actions = body.get("actions") or []
    case_id = actions[0].get("value") if actions else None
    user_id = body.get("user", {}).get("id")
    channel_id = body.get("channel", {}).get("id")
    message_ts = body.get("message", {}).get("ts")
    
    if not case_id:
        logger.warning("Missing case_id in send_to_customer action: %s", body)
        return

    # Handle send to customer
    result = summary_sender.handle_send_to_customer(
        case_id=case_id,
        user_id=user_id,
        channel_id=channel_id,
        message_ts=message_ts
    )
    
    # Send ephemeral response
    if result.get("response_type") == "ephemeral":
        try:
            app.client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=result.get("text", "操作完成")
            )
        except Exception as e:
            logger.error(f"Failed to send ephemeral message: {e}")


@app.action("open_send_sms_modal")
def handle_open_sms_modal(ack, body, client, logger):
    """
    Opens a modal for sales rep to confirm phone number before sending SMS.
    """
    ack()
    
    actions = body.get("actions") or []
    case_id = actions[0].get("value") if actions else None
    trigger_id = body.get("trigger_id")
    channel_id = body.get("channel", {}).get("id", "")
    message_ts = body.get("message", {}).get("ts", "")
    
    if not case_id:
        logger.warning("Missing case_id in open_send_sms_modal action: %s", body)
        return
    
    # Fetch case data from Firestore to get customer phone
    customer_phone = ""
    customer_name = "客戶"
    if db:
        try:
            case_doc = db.collection("cases").document(case_id).get()
            if case_doc.exists:
                case_data = case_doc.to_dict()
                customer_phone = case_data.get("customerPhone", "")
                customer_name = case_data.get("customerName", "客戶")
        except Exception as e:
            logger.error(f"Error fetching case data: {e}")
    
    try:
        client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "callback_id": "send_sms_modal",
                "private_metadata": f"{case_id}|{channel_id}|{message_ts}",
                "title": {"type": "plain_text", "text": "發送會議摘要"},
                "submit": {"type": "plain_text", "text": "確認發送"},
                "close": {"type": "plain_text", "text": "取消"},
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f":bust_in_silhouette: *客戶名稱*: {customer_name}\n:clipboard: *案件編號*: `{case_id}`"
                        }
                    },
                    {"type": "divider"},
                    {
                        "type": "input",
                        "block_id": "phone_block",
                        "label": {"type": "plain_text", "text": "📱 客戶電話"},
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "phone_input",
                            "initial_value": customer_phone,
                            "placeholder": {"type": "plain_text", "text": "09xxxxxxxx"}
                        },
                        "hint": {"type": "plain_text", "text": "請確認電話號碼正確，或輸入新電話"}
                    },
                    {
                        "type": "input",
                        "block_id": "extra_phone_block",
                        "label": {"type": "plain_text", "text": "📱 額外電話 (選填)"},
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "extra_phone_input",
                            "placeholder": {"type": "plain_text", "text": "如需發送給多人，請輸入額外電話"}
                        },
                        "optional": True
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": ":information_source: 簡訊將包含會議摘要的短網址連結，客戶可點擊查看完整內容。"
                            }
                        ]
                    }
                ]
            }
        )
        logger.info(f"SMS modal opened for case: {case_id}")
    except Exception as e:
        logger.error(f"Error opening SMS modal: {e}")


@app.view("send_sms_modal")
def handle_sms_modal_submit(ack, body, client, view, logger):
    """
    Handles SMS modal submission - sends SMS to customer.
    """
    ack()
    
    user_id = body["user"]["id"]
    private_metadata = view["private_metadata"]
    
    try:
        case_id, channel_id, message_ts = private_metadata.split("|")
    except ValueError:
        logger.error(f"Invalid SMS modal private_metadata: {private_metadata}")
        return
    
    submitted_values = view["state"]["values"]
    phone = submitted_values["phone_block"]["phone_input"]["value"]
    extra_phone = submitted_values.get("extra_phone_block", {}).get("extra_phone_input", {}).get("value", "")
    
    logger.info(f"SMS modal submitted by {user_id} for case {case_id}, phone: {phone}, extra: {extra_phone}")
    
    # Get customer name from Firestore and update phone
    customer_name = "客戶"
    if db:
        try:
            case_doc = db.collection("cases").document(case_id).get()
            customer_name = case_doc.to_dict().get("customerName", "客戶") if case_doc.exists else "客戶"
            
            # Update phone in Firestore
            db.collection("cases").document(case_id).update({
                "customerPhone": phone,
                "updatedAt": firestore.SERVER_TIMESTAMP
            })
        except Exception as e:
            logger.error(f"Error updating Firestore: {e}")
    
    # Send SMS
    import requests
    sms_service_url = os.getenv("SMS_SERVICE_URL", "https://sms-service-497329205771.asia-east1.run.app")
    sms_internal_token = os.getenv("SMS_INTERNAL_TOKEN")
    
    phones_to_send = [phone]
    if extra_phone and extra_phone.strip():
        phones_to_send.append(extra_phone.strip())
    
    success_results = []
    failed_results = []
    
    for target_phone in phones_to_send:
        try:
            headers = {"Content-Type": "application/json"}
            if sms_internal_token:
                headers["Authorization"] = f"Bearer {sms_internal_token}"
            
            response = requests.post(
                f"{sms_service_url}/send-sms",
                json={
                    "caseId": case_id,
                    "customerPhone": target_phone,
                    "customerName": customer_name
                },
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                success_results.append(f"{target_phone} ✅")
                logger.info(f"SMS sent to {target_phone} for case {case_id}")
            else:
                error_data = response.json()
                failed_results.append(f"{target_phone} ❌ ({error_data.get('error', 'Unknown')})")
                logger.error(f"SMS failed for {target_phone}: {error_data}")
        except Exception as e:
            failed_results.append(f"{target_phone} ❌ ({str(e)})")
            logger.error(f"SMS error for {target_phone}: {e}")
    
    # Send result message
    try:
        if success_results and not failed_results:
            result_text = f"✅ 會議摘要已成功發送給 {customer_name}！\n\n📱 發送至: {', '.join(success_results)}"
        elif success_results and failed_results:
            result_text = f"⚠️ 部分發送成功\n\n成功: {', '.join(success_results)}\n失敗: {', '.join(failed_results)}"
        else:
            result_text = f"❌ 發送失敗\n\n{', '.join(failed_results)}"
        
        if channel_id:
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=message_ts if message_ts else None,
                text=result_text
            )
    except Exception as e:
        logger.error(f"Failed to post SMS result: {e}")


@app.action("open_send_email_modal")
def handle_open_email_modal(ack, body, client, logger):
    """
    Opens a modal for sales rep to confirm email before sending.
    """
    ack()
    
    actions = body.get("actions") or []
    case_id = actions[0].get("value") if actions else None
    trigger_id = body.get("trigger_id")
    channel_id = body.get("channel", {}).get("id", "")
    message_ts = body.get("message", {}).get("ts", "")
    
    if not case_id:
        logger.warning("Missing case_id in open_send_email_modal action: %s", body)
        return
    
    # Fetch case data from Firestore to get customer email
    customer_email = ""
    customer_name = "客戶"
    if db:
        try:
            case_doc = db.collection("cases").document(case_id).get()
            if case_doc.exists:
                case_data = case_doc.to_dict()
                customer_email = case_data.get("customerEmail", "")
                customer_name = case_data.get("customerName", "客戶")
        except Exception as e:
            logger.error(f"Error fetching case data: {e}")
    
    try:
        client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "callback_id": "send_email_modal",
                "private_metadata": f"{case_id}|{channel_id}|{message_ts}",
                "title": {"type": "plain_text", "text": "發送 Email"},
                "submit": {"type": "plain_text", "text": "確認發送"},
                "close": {"type": "plain_text", "text": "取消"},
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f":bust_in_silhouette: *客戶名稱*: {customer_name}\n:clipboard: *案件編號*: `{case_id}`"
                        }
                    },
                    {"type": "divider"},
                    {
                        "type": "input",
                        "block_id": "email_block",
                        "label": {"type": "plain_text", "text": "📧 客戶 Email"},
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "email_input",
                            "initial_value": customer_email,
                            "placeholder": {"type": "plain_text", "text": "customer@example.com"}
                        },
                        "hint": {"type": "plain_text", "text": "請確認 Email 地址正確"}
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": ":information_source: Email 將包含精美的 HTML 格式會議摘要連結。"
                            }
                        ]
                    }
                ]
            }
        )
        logger.info(f"Email modal opened for case: {case_id}")
    except Exception as e:
        logger.error(f"Error opening Email modal: {e}")


@app.view("send_email_modal")
def handle_email_modal_submit(ack, body, client, view, logger):
    """
    Handles Email modal submission - sends Email to customer.
    Uses background thread to prevent Slack timeout.
    """
    ack()
    
    user_id = body["user"]["id"]
    private_metadata = view["private_metadata"]
    
    try:
        case_id, channel_id, message_ts = private_metadata.split("|")
    except ValueError:
        logger.error(f"Invalid Email modal private_metadata: {private_metadata}")
        return
    
    submitted_values = view["state"]["values"]
    email = submitted_values["email_block"]["email_input"]["value"]
    
    logger.info(f"Email modal submitted by {user_id} for case {case_id}, email: {email}")
    
    # Run in background thread
    def send_email_async():
        # Get customer name from Firestore
        customer_name = "客戶"
        if db:
            try:
                case_doc = db.collection("cases").document(case_id).get()
                if case_doc.exists:
                    customer_name = case_doc.to_dict().get("customerName", "客戶")
                    # Update email in Firestore
                    db.collection("cases").document(case_id).update({
                        "customerEmail": email,
                        "updatedAt": firestore.SERVER_TIMESTAMP
                    })
            except Exception as e:
                logger.error(f"Error updating case: {e}")
        
        # Call Email service
        import requests
        sms_service_url = os.environ.get("SMS_SERVICE_URL", "https://sms-service-497329205771.asia-east1.run.app")
        sms_internal_token = os.environ.get("SMS_INTERNAL_TOKEN")
        
        headers = {"Content-Type": "application/json"}
        if sms_internal_token:
            headers["Authorization"] = f"Bearer {sms_internal_token}"
        
        payload = {
            "caseId": case_id,
            "customerEmail": email,
            "customerName": customer_name
        }
        
        try:
            response = requests.post(
                f"{sms_service_url}/send-email",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result_text = f"✅ Email 已發送至 `{email}`"
            else:
                error_data = response.json()
                result_text = f"❌ Email 發送失敗: {error_data.get('error', 'Unknown')}"
        except Exception as e:
            logger.error(f"Email request failed: {e}")
            result_text = f"❌ Email 發送失敗: {str(e)}"
        
        # Post result to channel
        try:
            if channel_id:
                client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=message_ts if message_ts else None,
                    text=result_text
                )
        except Exception as e:
            logger.error(f"Failed to post Email result: {e}")
    
    # Start background thread
    thread = threading.Thread(target=send_email_async, daemon=True)
    thread.start()


@app.action("preview_summary")
def handle_preview_summary_action(ack, body, logger):  # type: ignore[override]
    """
    Handle the Agent 7 "Preview" button.
    """
    ack()
    if not summary_editor:
        logger.warning("Summary editor unavailable; cannot open preview modal.")
        return

    trigger_id = body.get("trigger_id")
    actions = body.get("actions") or []
    action_value = actions[0].get("value") if actions else None
    case_id = _extract_case_id(action_value, "preview_summary_")
    if not (trigger_id and case_id):
        logger.warning("Missing trigger or case id in preview_summary action: %s", body)
        return

    summary_editor.open_preview_modal(trigger_id, case_id)


@app.action("confirm_send_summary")
def handle_confirm_send_summary_action(ack, body, client, logger):  # type: ignore[override]
    """
    Open confirmation modal before sending summary + SMS.
    """
    ack()
    if not (summary_delivery_service and db):
        logger.warning("Summary delivery service unavailable; cannot confirm send.")
        return

    actions = body.get("actions") or []
    action_value = actions[0].get("value") if actions else None
    case_id = _extract_case_id(action_value, "confirm_send_")
    if not case_id:
        logger.warning("Missing case id in confirm send action: %s", body)
        return

    case_doc = db.collection("cases").document(case_id).get()
    if not case_doc.exists:
        logger.warning("Case %s not found when confirming summary", case_id)
        return

    case_data = case_doc.to_dict() or {}
    phone = case_data.get("customerPhone", "")
    customer_name = case_data.get("customerName", "客戶")
    notification = case_data.get("notification") or {}
    channel_id = (body.get("channel") or {}).get("id") or notification.get("slackChannelId")
    thread_ts = notification.get("slackThreadTs")

    private_metadata = json.dumps({
        "case_id": case_id,
        "channel_id": channel_id,
        "thread_ts": thread_ts,
    })

    view = {
        "type": "modal",
        "callback_id": "confirm_send_summary_modal",
        "private_metadata": private_metadata,
        "title": {"type": "plain_text", "text": "確認送出"},
        "submit": {"type": "plain_text", "text": "確認送出"},
        "close": {"type": "plain_text", "text": "取消"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"請確認是否將「*{customer_name}*」的客戶摘要以簡訊發送給客戶。"
                }
            },
            {
                "type": "input",
                "block_id": "phone_block",
                "label": {"type": "plain_text", "text": "客戶電話 (含國碼)"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "phone_input",
                    "initial_value": phone,
                    "placeholder": {"type": "plain_text", "text": "+886912345678"},
                },
                "hint": {"type": "plain_text", "text": "手機格式：+國碼 + 電話號碼"},
                "optional": False,
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "送出後將更新 Firestore 並在此 Thread 通知結果。"
                    }
                ]
            }
        ],
    }
    try:
        client.views_open(trigger_id=body["trigger_id"], view=view)
    except SlackApiError as exc:  # type: ignore[name-defined]
        logger.error("Failed to open confirm modal: %s", exc.response.get("error"))


@app.view("edit_summary_modal")
def handle_edit_summary_submission(ack, body, view, logger):  # type: ignore[override]
    """
    Handle summary edit modal submissions.
    """
    if not summary_editor:
        ack({"response_action": "errors", "errors": {"summary_content_block": "系統尚未初始化"}})
        return

    user_id = (body.get("user") or {}).get("id")
    case_id = view.get("private_metadata")
    response = summary_editor.handle_modal_submission(view, user_id)
    ack(response)

    if response and response.get("response_action") == "errors":
        return


@app.view("confirm_send_summary_modal")
def handle_confirm_send_summary_modal(ack, body, view, logger):  # type: ignore[override]
    """
    Handle the confirmation modal submission for sending summaries.
    """
    if not summary_delivery_service:
        ack({"response_action": "errors", "errors": {"phone_block": "系統尚未初始化"}})
        return

    metadata = json.loads(view.get("private_metadata") or "{}")
    case_id = metadata.get("case_id")
    phone_value = view.get("state", {}).get("values", {}).get("phone_block", {}).get("phone_input", {}).get("value")
    if not phone_value:
        ack({"response_action": "errors", "errors": {"phone_block": "請輸入客戶電話"}})
        return

    user_id = (body.get("user") or {}).get("id", "unknown")

    channel_id = metadata.get("channel_id")
    thread_ts = metadata.get("thread_ts")

    ack()

    enqueued = _enqueue_summary_delivery_task(
        case_id=case_id,
        phone=phone_value,
        initiated_by=user_id,
        channel_id=channel_id,
        thread_ts=thread_ts,
    )

    if enqueued:
        if slack_client and channel_id:
            slack_client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text="📤 已建立摘要發送任務，完成後會在此通知結果。"
            )
        return

    try:
        result = summary_delivery_service.send_summary(
            case_id=case_id,
            initiated_by=user_id,
            phone_number=phone_value,
        )
    except ValueError as exc:
        _notify_summary_delivery_result(
            case_id,
            DeliveryResult(status="failed", summary_url="", phone=None, error=str(exc)),
            channel_id,
            thread_ts,
            initiated_by=user_id,
        )
        return
    except Exception as exc:  # noqa: broad-except
        logger.exception("Summary delivery failed for case %s", case_id)
        _notify_summary_delivery_result(
            case_id,
            DeliveryResult(status="failed", summary_url="", phone=phone_value, error="發送失敗"),
            channel_id,
            thread_ts,
            initiated_by=user_id,
        )
        return

    _notify_summary_delivery_result(case_id, result, channel_id, thread_ts, initiated_by=user_id)


# ============================================
# Interactive Components (Analysis Results)
# ============================================


@app.action("view_full_analysis")
def handle_view_full_analysis_action(ack, body, client, logger):  # type: ignore[override]
    """
    Handle the "查看完整分析" button from analysis completion notifications.
    """
    ack()
    logger.info("view_full_analysis button clicked: %s", body)

    # TODO: Implement view full analysis functionality
    # For now, just acknowledge the button click
    # In the future, this could open a modal with detailed analysis results

    actions = body.get("actions") or []
    action_value = actions[0].get("value") if actions else None
    case_id = _extract_case_id(action_value, "view_analysis_")

    if case_id:
        logger.info(f"User requested full analysis for case {case_id}")
        # Can send an ephemeral message or open a modal here
        client.chat_postEphemeral(
            channel=body["container"]["channel_id"],
            user=body["user"]["id"],
            text=f"完整分析功能開發中。案件 ID: {case_id}"
        )


@app.action("retry_analysis")
def handle_retry_analysis_action(ack, body, logger):  # type: ignore[override]
    """
    Handle the "重新分析" button for failed analyses.
    """
    ack()
    logger.info("retry_analysis button clicked: %s", body)

    actions = body.get("actions") or []
    action_value = actions[0].get("value") if actions else None
    case_id = _extract_case_id(action_value, "retry_analysis_")

    if case_id:
        logger.info(f"User requested retry for case {case_id}")
        # TODO: Trigger reanalysis for the case


# ============================================
# Flask Routes
# ============================================

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """
    處理 Slack Events API 請求（包含 URL verification）
    """
    return handler.handle(request)


@flask_app.route("/internal/transcription-progress", methods=["POST"])
def handle_transcription_progress():
    """
    Receives transcription progress webhooks (e.g., when audio transcription completes)
    and posts status updates back to Slack.
    """
    if PROGRESS_SHARED_TOKEN:
        provided_token = request.headers.get("X-Progress-Token")
        if provided_token != PROGRESS_SHARED_TOKEN:
            logger.warning("Rejected transcription progress webhook: invalid token")
            return {"error": "Unauthorized"}, 403

    if not slack_client:
        logger.warning("Slack client not initialized; skipping progress notification")
        return {"error": "Slack client unavailable"}, 503

    if not db:
        logger.warning("Firestore unavailable; cannot resolve notification targets")
        return {"error": "Firestore unavailable"}, 503

    payload = request.get_json(silent=True) or {}
    case_id = payload.get("caseId")
    file_id = payload.get("fileId")
    status = payload.get("status")

    if not case_id or status not in ["transcribed", "batch_submitted"]:
        logger.warning("Invalid transcription progress payload: %s", payload)
        return {"error": "Invalid payload"}, 400

    channel_id, thread_ts, customer_name, _ = _resolve_notification_target(case_id, file_id)
    if not channel_id:
        logger.warning("No Slack channel found for case %s (file: %s)", case_id, file_id)
        return {"status": "ignored", "reason": "channel_not_found"}, 200

    if status == "batch_submitted":
        progress_text = f"🚀 案件 `{case_id}` 已送往 STT 進行轉錄..."
        context_text = "狀態：已送出轉錄 🚀"
    elif status == "transcribed":
        progress_text = f"✅ 案件 `{case_id}` 完成轉錄，正在進行分析中..."
        context_text = "狀態：完成轉錄・分析中 🔄"
    else:
        progress_text = f"ℹ️ 案件 `{case_id}` 狀態更新：{status}"
        context_text = f"狀態：{status}"

    if customer_name:
        context_text = f"{context_text} · 客戶：{customer_name}"

    try:
        slack_client.chat_postMessage(
            channel=channel_id,
            text=progress_text,
            thread_ts=thread_ts,
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": progress_text},
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": context_text,
                        }
                    ],
                },
            ],
        )
        logger.info("Posted transcription progress update for case %s", case_id)
    except SlackApiError as exc:
        logger.error(
            "Failed to post transcription progress for case %s: %s",
            case_id,
            exc.response.get("error"),
        )
        return {"error": "Failed to post Slack message"}, 500

    return {"status": "ok"}, 200


@flask_app.route("/internal/summary-delivery", methods=["POST"])
def handle_summary_delivery_request():
    """
    Internal endpoint triggered via Cloud Tasks to send summary + SMS.
    """
    if SUMMARY_INTERNAL_TOKEN:
        provided_token = request.headers.get("X-Progress-Token")
        if provided_token != SUMMARY_INTERNAL_TOKEN:
            logger.warning("Rejected summary delivery webhook: invalid token")
            return {"error": "Unauthorized"}, 403

    if not summary_delivery_service:
        logger.warning("Summary delivery service unavailable; skipping request")
        return {"error": "service_unavailable"}, 503

    payload = request.get_json(silent=True) or {}
    case_id = payload.get("caseId")
    if not case_id:
        return {"error": "Missing caseId"}, 400

    phone = payload.get("phone")
    initiated_by = payload.get("initiatedBy", "system")
    channel_id = payload.get("channelId")
    thread_ts = payload.get("threadTs")

    try:
        result = summary_delivery_service.send_summary(
            case_id=case_id,
            initiated_by=initiated_by,
            phone_number=phone,
        )
    except Exception as exc:  # noqa: broad-except
        logger.exception("Summary delivery task failed for %s", case_id)
        _notify_summary_delivery_result(
            case_id,
            DeliveryResult(status="failed", summary_url="", phone=phone, error=str(exc)),
            channel_id,
            thread_ts,
            initiated_by=initiated_by,
        )
        return {"status": "error", "reason": str(exc)}, 500

    _notify_summary_delivery_result(case_id, result, channel_id, thread_ts, initiated_by=initiated_by)
    return {"status": "ok", "deliveryStatus": result.status}, 200


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
