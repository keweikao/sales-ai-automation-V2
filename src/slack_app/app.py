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
    
    try:
        # Open a modal to collect metadata
        client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "callback_id": "upload_audio_modal",
                "private_metadata": file_id, # Pass the file_id to the modal
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
    
    # Retrieve the file_id from private_metadata
    file_id = view["private_metadata"]
    
    # Retrieve submitted values
    submitted_values = view["state"]["values"]
    customer_id = submitted_values["customer_id_block"]["customer_id_input"]["value"]
    store_name = submitted_values["store_name_block"]["store_name_input"]["value"]

    logger.info(f"Modal submitted by user {user_id}")
    logger.info(f"  - File ID: {file_id}")
    logger.info(f"  - Customer ID: {customer_id}")
    logger.info(f"  - Store Name: {store_name}")

    # TODO: Add logic to start the backend processing with this information
    # For now, send a confirmation message to the user in a DM
    try:
        client.chat_postMessage(
            channel=user_id, # Send as a DM to the user
            text=f"感謝！我們已收到您檔案的詳細資訊，將很快開始處理。\n- 檔案 ID: `{file_id}`\n- 客戶編號: `{customer_id}`\n- 店名: `{store_name}`"
        )
        # Optionally, update the original message in the channel to show it's processed
        # client.chat_update(
        #     channel=body["container"]["channel_id"],
        #     ts=body["container"]["message_ts"],
        #     text=f"檔案 {file_id} 的資訊已收到，正在處理中。",
        #     blocks=[] # Clear blocks if desired
        # )
    except SlackApiError as e:
        logger.error(f"Failed to send confirmation message to user {user_id}: {e.response['error']}")
    except Exception as e:
        logger.error(f"Unexpected error in handle_modal_submission: {e}")


# --- Main Execution ---
if __name__ == "__main__":
    logging.info("Starting Slack App in Socket Mode...")
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()
