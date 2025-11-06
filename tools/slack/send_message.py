"""
Tool: slack_send_message
Category: slack
Version: 1.0.0
Description: Send a message to a Slack channel.

# derived from Slack official doc (2025)
"""

import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from typing import Dict, Any

def send_message(channel: str, text: str) -> Dict[str, Any]:
    """
    Sends a message to a Slack channel.

    Args:
        channel: The Slack channel to send the message to.
        text: The text of the message.

    Returns:
        A dictionary with the status of the message.
    """

    try:
        client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
        response = client.chat_postMessage(channel=channel, text=text)
        return {
            "status": "success",
            "ts": response["ts"],
        }
    except SlackApiError as e:
        return {
            "status": "error",
            "error": e.response["error"],
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }
