"""
Notification Service implementation.

Provides unified interface for sending notifications across channels.
"""

import os
import logging
from typing import Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    """Supported notification channels."""
    SLACK = "slack"
    SMS = "sms"
    EMAIL = "email"


class NotificationService:
    """
    Unified notification service.

    Handles template rendering and channel routing.
    """

    def __init__(self):
        self._slack_sender = None
        self._templates = {}

    def _get_slack_sender(self):
        """Lazy initialization of Slack sender."""
        if self._slack_sender is None:
            from .channels.slack.sender import SlackSender

            bot_token = os.getenv("SLACK_BOT_TOKEN")
            if not bot_token:
                raise ValueError("SLACK_BOT_TOKEN environment variable is required")
            self._slack_sender = SlackSender(bot_token=bot_token)
        return self._slack_sender

    async def send(
        self,
        channel: str,
        recipient: str,
        template: str,
        data: dict[str, Any],
        priority: str = "normal",
    ) -> dict:
        """
        Send a notification.

        Args:
            channel: Notification channel (slack, sms, email)
            recipient: Recipient identifier (user ID, phone, email, or role)
            template: Template name to use
            data: Data to render in template
            priority: Message priority (high, normal, low)

        Returns:
            Dict with send status and message ID
        """
        # Resolve recipient from directory if it's a role
        resolved_recipient = await self._resolve_recipient(recipient, channel)

        # Load and render template
        rendered = await self._render_template(template, channel, data)

        # Send via appropriate channel
        if channel == NotificationChannel.SLACK or channel == "slack":
            return await self._send_slack(resolved_recipient, rendered, priority)
        elif channel == NotificationChannel.SMS or channel == "sms":
            return await self._send_sms(resolved_recipient, rendered)
        else:
            raise ValueError(f"Unsupported channel: {channel}")

    async def send_slack_message(
        self,
        channel: str,
        text: str,
        blocks: Optional[list[dict]] = None,
        thread_ts: Optional[str] = None,
    ) -> dict:
        """
        Send a direct Slack message (no template).

        Args:
            channel: Slack channel ID or name
            text: Message text
            blocks: Optional Block Kit blocks
            thread_ts: Thread timestamp for replies

        Returns:
            Slack API response
        """
        sender = self._get_slack_sender()
        return await sender.send_message(
            channel=channel,
            text=text,
            blocks=blocks,
            thread_ts=thread_ts,
        )

    async def send_slack_dm(
        self,
        user_id: str,
        text: str,
        blocks: Optional[list[dict]] = None,
    ) -> dict:
        """
        Send a direct message to a Slack user.

        Args:
            user_id: Slack user ID
            text: Message text
            blocks: Optional Block Kit blocks

        Returns:
            Slack API response
        """
        sender = self._get_slack_sender()
        return await sender.send_dm(user_id=user_id, text=text, blocks=blocks)

    async def send_analysis_notification(
        self,
        channel: str,
        case_id: str,
        summary: str,
        meddic_score: int,
        insights: list[str],
    ) -> dict:
        """
        Send analysis completion notification.

        Args:
            channel: Slack channel ID
            case_id: Case identifier
            summary: Analysis summary
            meddic_score: MEDDIC score (0-100)
            insights: List of key insights

        Returns:
            Slack API response
        """
        sender = self._get_slack_sender()
        blocks = sender.build_analysis_blocks(
            case_id=case_id,
            summary=summary,
            meddic_score=meddic_score,
            insights=insights,
        )
        return await sender.send_message(
            channel=channel,
            text=f"分析完成: {case_id}",
            blocks=blocks,
        )

    async def send_to_role(
        self,
        role: str,
        template: str,
        data: dict[str, Any],
        channels: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        Send notification to all users with a specific role.

        Args:
            role: Role name (e.g., "sales_manager", "rep")
            template: Template name
            data: Template data
            channels: Channels to use (defaults to all configured for role)

        Returns:
            List of send results
        """
        # Load role configuration from directory
        recipients = await self._get_role_recipients(role)

        results = []
        for recipient in recipients:
            for channel in channels or ["slack"]:
                try:
                    result = await self.send(
                        channel=channel,
                        recipient=recipient,
                        template=template,
                        data=data,
                    )
                    results.append({"recipient": recipient, "status": "sent", **result})
                except Exception as e:
                    logger.error(f"Failed to send to {recipient}: {e}")
                    results.append({"recipient": recipient, "status": "failed", "error": str(e)})

        return results

    async def _get_role_recipients(self, role: str) -> list[str]:
        """Get recipients for a role from directory."""
        # TODO: Load from recipients/directory.yaml
        # For now, return empty list - roles should be configured
        logger.warning(f"Role-based recipients not configured. Role: {role}")
        return []

    async def _resolve_recipient(self, recipient: str, channel: str) -> str:
        """Resolve recipient from directory or return as-is."""
        # If it looks like a Slack user ID or channel ID, return as-is
        if recipient.startswith("U") or recipient.startswith("C") or recipient.startswith("#"):
            return recipient

        # TODO: Load from recipients/directory.yaml for named recipients
        return recipient

    async def _render_template(
        self,
        template: str,
        channel: str,
        data: dict[str, Any]
    ) -> dict:
        """Load and render notification template."""
        # TODO: Load from templates/{events,roles}/
        # For now, return basic structure with data interpolation
        text = data.get("text", f"Notification: {template}")

        if "case_id" in data:
            text = f"[{data['case_id']}] {text}"

        return {
            "text": text,
            "blocks": data.get("blocks"),
            "data": data,
        }

    async def _send_slack(
        self,
        recipient: str,
        content: dict,
        priority: str
    ) -> dict:
        """Send via Slack channel."""
        sender = self._get_slack_sender()

        # Check if recipient is a user ID (DM) or channel
        if recipient.startswith("U"):
            return await sender.send_dm(
                user_id=recipient,
                text=content["text"],
                blocks=content.get("blocks"),
            )
        else:
            return await sender.send_message(
                channel=recipient,
                text=content["text"],
                blocks=content.get("blocks"),
            )

    async def _send_sms(self, recipient: str, content: dict) -> dict:
        """Send via SMS."""
        # TODO: Implement SMS via Twilio
        # For now, log and return success (SMS is lower priority)
        logger.warning(f"SMS not implemented. Would send to {recipient}: {content['text']}")
        return {
            "status": "skipped",
            "message": "SMS not yet implemented",
            "recipient": recipient,
        }
