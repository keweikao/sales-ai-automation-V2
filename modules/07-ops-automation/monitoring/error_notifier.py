"""
Error notification system.

Sends alerts when errors occur in the system.
Integrates with NotificationService for Slack delivery.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from enum import Enum
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from infrastructure.services.notification.service import NotificationService

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ErrorCategory(str, Enum):
    """Categories of errors to monitor."""
    TRANSCRIPTION_FAILED = "transcription_failed"
    ANALYSIS_FAILED = "analysis_failed"
    NOTIFICATION_FAILED = "notification_failed"
    SALESFORCE_SYNC_FAILED = "salesforce_sync_failed"
    DATABASE_ERROR = "database_error"
    LLM_ERROR = "llm_error"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class ErrorRecord:
    """Record of an error event."""
    message: str
    severity: ErrorSeverity
    category: Optional[ErrorCategory] = None
    conversation_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    notified: bool = False


class ErrorNotifier:
    """
    Sends error notifications to ops team.

    Provides immediate alerts for critical issues
    and batched notifications for lower-priority errors.
    Integrates with NotificationService for actual delivery.
    """

    # Default alert channel
    DEFAULT_CHANNEL = "#sales-ai-alerts"

    # Buffer flush interval (seconds)
    BUFFER_FLUSH_INTERVAL = 900  # 15 minutes

    def __init__(
        self,
        slack_channel: str = DEFAULT_CHANNEL,
        notification_service: Optional["NotificationService"] = None,
        buffer_size: int = 100,
    ):
        """
        Initialize the error notifier.

        Args:
            slack_channel: Slack channel for alerts
            notification_service: NotificationService instance for sending
            buffer_size: Maximum errors to buffer before auto-flush
        """
        self.slack_channel = slack_channel
        self.notification_service = notification_service
        self._error_buffer: List[ErrorRecord] = []
        self._buffer_size = buffer_size
        self._last_flush = datetime.now(timezone.utc)

    def set_notification_service(self, service: "NotificationService"):
        """
        Set the notification service for sending alerts.

        Args:
            service: NotificationService instance
        """
        self.notification_service = service

    async def notify(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: Optional[ErrorCategory] = None,
        conversation_id: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send an error notification.

        Args:
            message: Error message
            severity: Error severity level
            category: Error category for filtering
            conversation_id: Related conversation if applicable
            error_details: Additional error context

        Returns:
            True if notification was sent/buffered successfully
        """
        error_record = ErrorRecord(
            message=message,
            severity=severity,
            category=category,
            conversation_id=conversation_id,
            details=error_details or {},
        )

        # Critical errors get immediate notification
        if severity == ErrorSeverity.CRITICAL:
            return await self._send_immediate(error_record)

        # Other errors get buffered
        self._buffer_error(error_record)

        # Auto-flush if buffer is full
        if len(self._error_buffer) >= self._buffer_size:
            await self.flush_buffer()

        return True

    async def notify_critical(
        self,
        message: str,
        category: Optional[ErrorCategory] = None,
        conversation_id: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Convenience method for critical errors."""
        return await self.notify(
            message=message,
            severity=ErrorSeverity.CRITICAL,
            category=category,
            conversation_id=conversation_id,
            error_details=error_details,
        )

    async def notify_transcription_failed(
        self,
        conversation_id: str,
        error_message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Notify about a transcription failure."""
        return await self.notify(
            message=f"Transcription failed: {error_message}",
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.TRANSCRIPTION_FAILED,
            conversation_id=conversation_id,
            error_details=details,
        )

    async def notify_analysis_failed(
        self,
        conversation_id: str,
        error_message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Notify about an analysis failure."""
        return await self.notify(
            message=f"Analysis failed: {error_message}",
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.ANALYSIS_FAILED,
            conversation_id=conversation_id,
            error_details=details,
        )

    async def _send_immediate(self, error: ErrorRecord) -> bool:
        """Send immediate notification for critical errors."""
        blocks = self._build_error_blocks(error)

        # Log locally regardless of notification service status
        logger.critical(f"[{error.category}] {error.message}", extra={
            "conversation_id": error.conversation_id,
            "details": error.details,
        })

        # Send via notification service if available
        if self.notification_service:
            try:
                await self.notification_service.send_slack_message(
                    channel=self.slack_channel,
                    text=f"[{error.severity.value.upper()}] {error.message}",
                    blocks=blocks,
                )
                error.notified = True
                return True
            except Exception as e:
                logger.error(f"Failed to send error notification: {e}")
                return False
        else:
            logger.warning("No notification service configured, alert not sent to Slack")
            return False

    def _buffer_error(self, error: ErrorRecord):
        """Add error to buffer for batched sending."""
        self._error_buffer.append(error)

    async def flush_buffer(self) -> int:
        """
        Send all buffered errors as a summary.

        Returns:
            Number of errors flushed
        """
        if not self._error_buffer:
            return 0

        error_count = len(self._error_buffer)

        # Group by category
        by_category: Dict[str, List[ErrorRecord]] = {}
        for error in self._error_buffer:
            cat = error.category.value if error.category else "unknown"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(error)

        # Build summary blocks
        blocks = self._build_summary_blocks(by_category, error_count)

        # Log summary
        logger.warning(f"Flushing {error_count} buffered errors")

        # Send via notification service
        if self.notification_service:
            try:
                await self.notification_service.send_slack_message(
                    channel=self.slack_channel,
                    text=f"Error summary: {error_count} errors in the last period",
                    blocks=blocks,
                )
            except Exception as e:
                logger.error(f"Failed to send error summary: {e}")

        # Clear buffer
        self._error_buffer = []
        self._last_flush = datetime.now(timezone.utc)

        return error_count

    def get_buffer_stats(self) -> Dict[str, Any]:
        """Get statistics about the error buffer."""
        by_severity = {}
        by_category = {}

        for error in self._error_buffer:
            sev = error.severity.value
            by_severity[sev] = by_severity.get(sev, 0) + 1

            cat = error.category.value if error.category else "unknown"
            by_category[cat] = by_category.get(cat, 0) + 1

        return {
            "total": len(self._error_buffer),
            "by_severity": by_severity,
            "by_category": by_category,
            "last_flush": self._last_flush.isoformat(),
        }

    def _build_error_blocks(self, error: ErrorRecord) -> List[Dict[str, Any]]:
        """Build Slack blocks for error message."""
        severity_emoji = {
            "critical": "🚨",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
        }

        emoji = severity_emoji.get(error.severity.value, "❓")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {error.severity.value.upper()}: System Alert",
                    "emoji": True,
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Message:*\n{error.message}",
                }
            },
        ]

        # Add category if present
        if error.category:
            blocks.append({
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Category:*\n{error.category.value}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Time:*\n{error.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC",
                    },
                ]
            })

        # Add conversation ID if present
        if error.conversation_id:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Case ID: `{error.conversation_id}`",
                    }
                ]
            })

        # Add error details if present
        if error.details:
            detail_text = "\n".join([f"• {k}: {v}" for k, v in error.details.items()])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Details:*\n```{detail_text}```",
                }
            })

        return blocks

    def _build_summary_blocks(
        self,
        by_category: Dict[str, List[ErrorRecord]],
        total_count: int
    ) -> List[Dict[str, Any]]:
        """Build Slack blocks for error summary."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 Error Summary: {total_count} errors",
                    "emoji": True,
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Errors collected over the last {self.BUFFER_FLUSH_INTERVAL // 60} minutes:",
                }
            },
            {"type": "divider"},
        ]

        # Add category breakdown
        category_lines = []
        for cat, errors in sorted(by_category.items(), key=lambda x: -len(x[1])):
            severity_counts = {}
            for e in errors:
                sev = e.severity.value
                severity_counts[sev] = severity_counts.get(sev, 0) + 1

            severity_str = ", ".join([f"{k}: {v}" for k, v in severity_counts.items()])
            category_lines.append(f"• *{cat}*: {len(errors)} ({severity_str})")

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*By Category:*\n" + "\n".join(category_lines),
            }
        })

        # Add sample errors (first 3)
        sample_errors = []
        for errors in by_category.values():
            sample_errors.extend(errors[:1])  # Take 1 from each category

        if sample_errors:
            blocks.append({"type": "divider"})
            sample_text = "\n".join([
                f"• `{e.conversation_id or 'N/A'}`: {e.message[:80]}..."
                if len(e.message) > 80 else f"• `{e.conversation_id or 'N/A'}`: {e.message}"
                for e in sample_errors[:3]
            ])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Sample Errors:*\n{sample_text}",
                }
            })

        # Footer with timestamp
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Summary generated at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
                }
            ]
        })

        return blocks
