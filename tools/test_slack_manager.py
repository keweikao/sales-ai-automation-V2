import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Try to load .env manually if dotenv is available, otherwise rely on shell env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def test_manager_message():
    token = os.environ.get("SLACK_BOT_TOKEN")
    channel = os.environ.get("MANAGER_CHANNEL_ID", "C0A4F762FE0")

    if not token:
        print("⚠ SLACK_BOT_TOKEN not found in env. Attempting to fetch from Secret Manager...")
        try: 
            import subprocess
            result = subprocess.run(
                ["gcloud", "secrets", "versions", "access", "latest", "--secret=slack-bot-token", "--project=sales-ai-automation-v2"],
                capture_output=True, text=True, check=True
            )
            token = result.stdout.strip()
            print("✅ Successfully fetched token from Secret Manager.")
        except Exception as e:
            print(f"❌ Failed to fetch token from Secret Manager: {e}")
            print("Please export SLACK_BOT_TOKEN='xoxb-...' before running this script.")
            return

    print(f"Attempting to send message to Manager Channel: {channel}...")
    
    client = WebClient(token=token)

    try:
        response = client.chat_postMessage(
            channel=channel,
            text="🔔 *System Verification*\n這是來自 Sales AI Automation 的測試訊息。\n確認 Agent 5 主管通知頻道連線正常。 :white_check_mark:"
        )
        print(f"✅ Success! Message sent to {channel}. Timestamp: {response['ts']}")
    except SlackApiError as e:
        print(f"❌ Error sending message: {e.response['error']}")

if __name__ == "__main__":
    test_manager_message()
