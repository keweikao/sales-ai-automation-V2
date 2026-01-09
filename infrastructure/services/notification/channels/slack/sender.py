"""
Slack message sender.

Handles sending messages to Slack channels and users.
"""

from typing import Optional
from slack_sdk.web.async_client import AsyncWebClient


class SlackSender:
    """
    Sends messages to Slack.

    Supports:
    - Channel messages
    - Direct messages
    - Thread replies
    - Interactive blocks
    """

    def __init__(self, bot_token: str):
        self.client = AsyncWebClient(token=bot_token)

    async def send_message(
        self,
        channel: str,
        text: str,
        blocks: Optional[list[dict]] = None,
        thread_ts: Optional[str] = None,
        unfurl_links: bool = False,
    ) -> dict:
        """
        Send a message to a Slack channel.

        Args:
            channel: Channel ID or name
            text: Fallback text
            blocks: Block Kit blocks
            thread_ts: Thread timestamp for replies
            unfurl_links: Whether to unfurl links

        Returns:
            Slack API response
        """
        response = await self.client.chat_postMessage(
            channel=channel,
            text=text,
            blocks=blocks,
            thread_ts=thread_ts,
            unfurl_links=unfurl_links,
        )
        return response.data

    async def send_dm(
        self,
        user_id: str,
        text: str,
        blocks: Optional[list[dict]] = None,
    ) -> dict:
        """
        Send a direct message to a user.

        Args:
            user_id: Slack user ID
            text: Message text
            blocks: Block Kit blocks

        Returns:
            Slack API response
        """
        # Open DM channel first
        response = await self.client.conversations_open(users=[user_id])
        channel_id = response["channel"]["id"]

        return await self.send_message(channel_id, text, blocks)

    async def update_message(
        self,
        channel: str,
        ts: str,
        text: str,
        blocks: Optional[list[dict]] = None,
    ) -> dict:
        """Update an existing message."""
        response = await self.client.chat_update(
            channel=channel,
            ts=ts,
            text=text,
            blocks=blocks,
        )
        return response.data

    def build_analysis_blocks(
        self,
        case_id: str,
        summary: str,
        meddic_score: int,
        insights: list[str],
    ) -> list[dict]:
        """
        Build Block Kit blocks for analysis notification.

        Args:
            case_id: Case identifier
            summary: Analysis summary
            meddic_score: MEDDIC score (0-100)
            insights: List of key insights

        Returns:
            List of Block Kit blocks
        """
        # Score color
        if meddic_score >= 70:
            score_emoji = "🟢"
        elif meddic_score >= 40:
            score_emoji = "🟡"
        else:
            score_emoji = "🔴"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 分析完成: {case_id}",
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{score_emoji} *MEDDIC 分數: {meddic_score}/100*"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": summary
                }
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*關鍵洞察:*\n" + "\n".join(f"• {i}" for i in insights[:5])
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "查看詳情"},
                        "action_id": "view_analysis",
                        "value": case_id,
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "發送摘要"},
                        "action_id": "send_summary",
                        "value": case_id,
                        "style": "primary",
                    },
                ]
            }
        ]

        return blocks
