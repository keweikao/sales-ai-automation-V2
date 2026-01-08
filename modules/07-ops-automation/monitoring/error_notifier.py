"""
Error notification system.

Sends alerts when errors occur in the system.
"""

from datetime import datetime
from typing import Optional
from enum import Enum


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"


class ErrorCategory(str, Enum):
    """Categories of errors to monitor."""
    TRANSCRIPTION_FAILED = "transcription_failed"
    ANALYSIS_FAILED = "analysis_failed"
    NOTIFICATION_FAILED = "notification_failed"
    SALESFORCE_SYNC_FAILED = "salesforce_sync_failed"


class ErrorNotifier:
    """
    Sends error notifications to ops team.

    Provides immediate alerts for critical issues
    and batched notifications for lower-priority errors.
    """

    def __init__(
        self,
        slack_channel: str = "#sales-ai-alerts",
        notification_service=None,
    ):
        self.slack_channel = slack_channel
        self.notification_service = notification_service
        self._error_buffer: list[dict] = []

    async def notify(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: Optional[ErrorCategory] = None,
        conversation_id: Optional[str] = None,
        error_details: Optional[dict] = None,
    ):
        """
        Send an error notification.

        Args:
            message: Error message
            severity: Error severity level
            category: Error category for filtering
            conversation_id: Related conversation if applicable
            error_details: Additional error context
        """
        error_record = {
            "message": message,
            "severity": severity.value,
            "category": category.value if category else None,
            "conversation_id": conversation_id,
            "details": error_details,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if severity == ErrorSeverity.CRITICAL:
            await self._send_immediate(error_record)
        else:
            self._buffer_error(error_record)

    async def _send_immediate(self, error: dict):
        """Send immediate notification for critical errors."""
        # Build Slack message
        blocks = self._build_error_blocks(error)

        # TODO: Send via notification service
        # For now, print for debugging
        print(f"[CRITICAL ERROR] {error['message']}")

        if self.notification_service:
            await self.notification_service.send(
                channel="slack",
                recipient=self.slack_channel,
                template="error_alert",
                data=error,
            )

    def _buffer_error(self, error: dict):
        """Add error to buffer for batched sending."""
        self._error_buffer.append(error)

    async def flush_buffer(self):
        """Send all buffered errors."""
        if not self._error_buffer:
            return

        # Group by category
        by_category = {}
        for error in self._error_buffer:
            cat = error.get("category", "unknown")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(error)

        # Send summary
        summary = f"過去 15 分鐘發生 {len(self._error_buffer)} 個錯誤:\n"
        for cat, errors in by_category.items():
            summary += f"• {cat}: {len(errors)} 個\n"

        print(f"[ERROR SUMMARY] {summary}")

        self._error_buffer = []

    def _build_error_blocks(self, error: dict) -> list[dict]:
        """Build Slack blocks for error message."""
        severity_emoji = {
            "critical": "🚨",
            "error": "❌",
            "warning": "⚠️",
        }

        emoji = severity_emoji.get(error["severity"], "❓")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {error['severity'].upper()}: {error['message'][:50]}",
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": error["message"],
                }
            },
        ]

        if error.get("conversation_id"):
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Case: `{error['conversation_id']}`",
                    }
                ]
            })

        return blocks
