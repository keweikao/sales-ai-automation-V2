"""
Notification Service

Multi-channel notification system with template support.

Channels:
- Slack: Interactive messages with buttons
- SMS: Text messages via Twilio
- Email: (Future) Email notifications

Usage:
    from infrastructure.services.notification import NotificationService

    service = NotificationService()
    await service.send(
        channel="slack",
        recipient="sales-team",
        template="analysis_complete",
        data={"case_id": "123", "score": 85}
    )
"""

from .service import NotificationService

__all__ = ["NotificationService"]
