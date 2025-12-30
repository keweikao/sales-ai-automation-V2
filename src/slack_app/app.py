import os
import logging
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError

# --- Initialization ---
load_dotenv()
logging.basicConfig(level=logging.INFO)

# Initialize the Slack App
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# --- File Shared Event Handler ---
@app.event("file_shared")
def handle_file_shared(client, event, logger):
    """
    This listener is triggered when a file is shared in a channel the bot is in.
    It posts a message with a button to collect metadata for the file.
    """
    file_id = event["file_id"]
    channel_id = event.get("channel_id")
    user_id = event.get("user_id")
    event_ts = event.get("event_ts")
    
    try:
        if not channel_id or not event_ts:
            logger.warning(f"file_shared event missing channel or event_ts: {event}")
            return

        # Get file info to check the file type
        file_info = client.files_info(file=file_id).get("file")
        file_type = file_info.get("filetype")
        file_name = file_info.get("name")
        
        # Define supported audio types
        supported_audio_types = ["m4a", "mp3", "wav", "flac"]

        if file_type in supported_audio_types:
            logger.info(f"Audio file shared: {file_id} ({file_name}) by user: {user_id}. Posting interactive message.")
            
            # Add a reaction to the file message to acknowledge receipt
            client.reactions_add(
                channel=channel_id,
                timestamp=event_ts, # Timestamp of the file_shared event message
                name="eyes" # Or any other suitable emoji
            )

            # Post a message with a button in a thread to the file_shared message
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=event_ts, # Reply in a thread to the file_shared message
                text=f"我偵測到一個音檔: *{file_name}*。請點擊下方按鈕補充客戶資訊以開始分析。",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"我偵測到一個音檔: *{file_name}*。請點擊下方按鈕補充客戶資訊以開始分析。"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "新增檔案細節"},
                                "style": "primary",
                                "action_id": "add_file_details_button",
                                "value": file_id # Pass the file_id through the button's value
                            }
                        ]
                    }
                ]
            )
        else:
            logger.info(f"Ignoring non-audio file: {file_id} of type {file_type}")

    except SlackApiError as e:
        logger.error(f"Error handling file_shared event: {e.response['error']}")
    except Exception as e:
        logger.error(f"Unexpected error in handle_file_shared: {e}")


# --- Button Click Handler ---
@app.action("add_file_details_button")
def handle_add_file_details_button(ack, body, client, logger):
    """
    This listener is triggered when the '新增檔案細節' button is clicked.
    It opens a modal to collect metadata.
    """
    ack() # Acknowledge the button click
    
    file_id = body["actions"][0]["value"] # Get file_id from the button's value
    trigger_id = body["trigger_id"] # Get trigger_id from the payload
    channel_id = body["channel"]["id"]
    # The thread_ts is in the message context
    thread_ts = body["message"]["thread_ts"]
    
    try:
        # Open a modal to collect metadata
        client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "callback_id": "upload_audio_modal",
                # Pass file_id, channel_id, and thread_ts to the modal
                "private_metadata": f"{file_id}|{channel_id}|{thread_ts}",
                "title": {"type": "plain_text", "text": "Audio File Details"},
                "submit": {"type": "plain_text", "text": "Submit"},
                "close": {"type": "plain_text", "text": "Cancel"},
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "customer_id_block",
                        "label": {"type": "plain_text", "text": "Customer ID"},
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "customer_id_input",
                            "placeholder": {"type": "plain_text", "text": "e.g., 123456-789012"}
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "store_name_block",
                        "label": {"type": "plain_text", "text": "Store Name"},
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "store_name_input"
                        }
                    }
                ]
            }
        )
        logger.info(f"Modal opened for file: {file_id}")

    except SlackApiError as e:
        logger.error(f"Error opening modal: {e.response['error']}")
    except Exception as e:
        logger.error(f"Unexpected error in handle_add_file_details_button: {e}")


# --- Modal Submission Handler ---
@app.view("upload_audio_modal")
def handle_modal_submission(ack, body, client, view, logger):
    """
    This handler is triggered when the metadata modal is submitted.
    It retrieves the file_id from private_metadata and submitted values.
    """
    ack() # Acknowledge the view submission

    user_id = body["user"]["id"]
    
    # Retrieve the file_id, channel_id, and thread_ts from private_metadata
    private_metadata = view["private_metadata"]
    try:
        file_id, channel_id, thread_ts = private_metadata.split("|")
    except ValueError:
        logger.error(f"Invalid private_metadata format: {private_metadata}")
        # Optionally, send an error message to the user
        return
    
    # Retrieve submitted values
    submitted_values = view["state"]["values"]
    customer_id = submitted_values["customer_id_block"]["customer_id_input"]["value"]
    store_name = submitted_values["store_name_block"]["store_name_input"]["value"]

    logger.info(f"Modal submitted by user {user_id}")
    logger.info(f"  - File ID: {file_id}")
    logger.info(f"  - Customer ID: {customer_id}")
    logger.info(f"  - Store Name: {store_name}")
    logger.info(f"  - Target Channel: {channel_id}")
    logger.info(f"  - Target Thread: {thread_ts}")

    # TODO: Add logic to start the backend processing with this information
    # For now, send a confirmation message to the original thread
    try:
        # Create the confirmation message using the example format
        confirmation_text = (
            f":white_check_mark: 案件已建立並開始轉錄與分析\n"
            f":file_folder: 案件編號：`{file_id}`\n" # Using file_id as a placeholder for case_id
            f":bust_in_silhouette: 客戶編號：`{customer_id}`\n"
            f":convenience_store: 客戶名稱：{store_name}\n"
            f":telephone_receiver: 客戶電話：未提供\n"
            f":memo: 備註：無\n"
            f":dart: 我們會在分析完成後自動通知您。"
        )

        client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=confirmation_text
        )
        # Optionally, update the original message in the channel to show it's processed
        # client.chat_update(
        #     channel=body["container"]["channel_id"],
        #     ts=body["container"]["message_ts"],
        #     text=f"檔案 {file_id} 的資訊已收到，正在處理中。",
        #     blocks=[] # Clear blocks if desired
        # )
    except SlackApiError as e:
        logger.error(f"Failed to send confirmation message to thread {thread_ts}: {e.response['error']}")
    except Exception as e:
        logger.error(f"Unexpected error in handle_modal_submission: {e}")


# --- SMS Modal Handler ---
@app.action("open_send_sms_modal")
def handle_open_sms_modal(ack, body, client, logger):
    """
    Opens a modal for sales rep to confirm phone number before sending SMS.
    """
    ack()
    
    case_id = body["actions"][0]["value"]
    trigger_id = body["trigger_id"]
    channel_id = body.get("channel", {}).get("id", "")
    message_ts = body.get("message", {}).get("ts", "")
    
    # Fetch case data from Firestore to get customer phone
    try:
        from google.cloud import firestore
        db = firestore.Client(project=os.environ.get("GCP_PROJECT_ID", "sales-ai-automation-v2"))
        case_doc = db.collection("cases").document(case_id).get()
        
        if case_doc.exists:
            case_data = case_doc.to_dict()
            customer_phone = case_data.get("customerPhone", "")
            customer_name = case_data.get("customerName", "客戶")
        else:
            customer_phone = ""
            customer_name = "客戶"
    except Exception as e:
        logger.error(f"Error fetching case data: {e}")
        customer_phone = ""
        customer_name = "客戶"
    
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
    except SlackApiError as e:
        logger.error(f"Error opening SMS modal: {e.response['error']}")


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
    
    # Call SMS service
    import requests
    sms_service_url = os.environ.get("SMS_SERVICE_URL", "https://sms-service-497329205771.asia-east1.run.app")
    sms_internal_token = os.environ.get("SMS_INTERNAL_TOKEN")
    
    # Get customer name from Firestore
    try:
        from google.cloud import firestore
        db = firestore.Client(project=os.environ.get("GCP_PROJECT_ID", "sales-ai-automation-v2"))
        case_doc = db.collection("cases").document(case_id).get()
        customer_name = case_doc.to_dict().get("customerName", "客戶") if case_doc.exists else "客戶"
        
        # Update phone in Firestore
        db.collection("cases").document(case_id).update({
            "customerPhone": phone,
            "updatedAt": firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        logger.error(f"Error updating Firestore: {e}")
        customer_name = "客戶"
    
    # Send SMS
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
                result = response.json()
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
    except SlackApiError as e:
        logger.error(f"Failed to post SMS result: {e.response['error']}")


# --- Email Modal Handler ---
@app.action("open_send_email_modal")
def handle_open_email_modal(ack, body, client, logger):
    """
    Opens a modal for sales rep to confirm email before sending.
    """
    ack()
    
    case_id = body["actions"][0]["value"]
    trigger_id = body["trigger_id"]
    channel_id = body.get("channel", {}).get("id", "")
    message_ts = body.get("message", {}).get("ts", "")
    
    # Fetch case data from Firestore to get customer email
    try:
        from google.cloud import firestore
        db = firestore.Client(project=os.environ.get("GCP_PROJECT_ID", "sales-ai-automation-v2"))
        case_doc = db.collection("cases").document(case_id).get()
        
        if case_doc.exists:
            case_data = case_doc.to_dict()
            customer_email = case_data.get("customerEmail", "")
            customer_name = case_data.get("customerName", "客戶")
        else:
            customer_email = ""
            customer_name = "客戶"
    except Exception as e:
        logger.error(f"Error fetching case data: {e}")
        customer_email = ""
        customer_name = "客戶"
    
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
    except SlackApiError as e:
        logger.error(f"Error opening Email modal: {e.response['error']}")


@app.view("send_email_modal")
def handle_email_modal_submit(ack, body, client, view, logger):
    """
    Handles Email modal submission - sends Email to customer.
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
    
    # Call Email service
    sms_service_url = os.environ.get("SMS_SERVICE_URL", "https://sms-service-497329205771.asia-east1.run.app")
    sms_internal_token = os.environ.get("SMS_INTERNAL_TOKEN")
    
    # Fetch customer name
    customer_name = "客戶"
    try:
        from google.cloud import firestore
        db = firestore.Client(project=os.environ.get("GCP_PROJECT_ID", "sales-ai-automation-v2"))
        case_doc = db.collection("cases").document(case_id).get()
        if case_doc.exists:
            customer_name = case_doc.to_dict().get("customerName", "客戶")
    except Exception as e:
        logger.error(f"Error fetching customer name: {e}")
    
    # Send Email
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
            result_text = f":white_check_mark: Email 已發送至 `{email}`"
        else:
            error = response.json().get("error", "Unknown error")
            result_text = f":x: Email 發送失敗: {error}"
    except Exception as e:
        logger.error(f"Email request failed: {e}")
        result_text = f":x: Email 發送失敗: {str(e)}"
    
    # Post result to channel
    try:
        if channel_id:
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=message_ts if message_ts else None,
                text=result_text
            )
    except SlackApiError as e:
        logger.error(f"Failed to post Email result: {e.response['error']}")



# --- Coach Chat Handler ---
@app.event("message")
def handle_message(event, client, logger):
    """
    Handle replies in threads.
    Checks if the thread is a Coach Alert thread by calling Analysis Service.
    """
    # Ignore bot messages and non-message events
    if event.get("bot_id") or event.get("subtype") == "bot_message":
        return

    # Only process thread replies
    thread_ts = event.get("thread_ts")
    if not thread_ts:
        return

    channel_id = event.get("channel")
    user_message = event.get("text")
    
    logger.info(f"Received thread reply in {channel_id}, ts={thread_ts}")

    # Call Analysis Service to get Coach response
    # We call the service and if it returns a response, we post it.
    # If it returns "active: false" or 404, we ignore it.
    
    analysis_service_url = os.environ.get("ANALYSIS_SERVICE_URL", "https://analysis-service-497329205771.asia-east1.run.app")
    
    try:
        import requests
        response = requests.post(
            f"{analysis_service_url}/coach/chat",
            json={
                "threadId": thread_ts,
                "channelId": channel_id,
                "message": user_message
            },
            timeout=10 # Short timeout for chat
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success" and data.get("response"):
                # Coach has a response! Post it.
                coach_response = data.get("response")
                client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=thread_ts,
                    text=coach_response
                )
                logger.info(f"Posted Coach response to thread {thread_ts}")
            else:
                logger.debug(f"No coach response for thread {thread_ts}: {data}")
        else:
            logger.warning(f"Analysis Service returned {response.status_code}")

    except Exception as e:
        logger.error(f"Error calling Analysis Service for coach chat: {e}")


# --- Main Execution ---
if __name__ == "__main__":
    logging.info("Starting Slack App in Socket Mode...")
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()
