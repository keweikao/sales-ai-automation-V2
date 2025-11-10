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


# --- Main Execution ---
if __name__ == "__main__":
    logging.info("Starting Slack App in Socket Mode...")
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()
