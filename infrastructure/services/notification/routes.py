"""
Notification Service API routes.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Optional

router = APIRouter(prefix="/notifications", tags=["notifications"])


class SendNotificationRequest(BaseModel):
    """Request to send a notification."""
    channel: str
    recipient: str
    template: str
    data: dict[str, Any]
    priority: str = "normal"


class NotificationResponse(BaseModel):
    """Response from notification send."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


@router.post("/send", response_model=NotificationResponse)
async def send_notification(request: SendNotificationRequest):
    """Send a notification via specified channel."""
    # TODO: Connect to NotificationService
    return NotificationResponse(
        success=False,
        error="Notification service migration in progress"
    )
