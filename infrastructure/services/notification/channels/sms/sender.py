"""
SMS sender using Twilio.

NOTE: Current implementation is in sms-service/src/main.py
This will be migrated here.
"""

from typing import Optional


class SMSSender:
    """
    Sends SMS messages via Twilio.

    Migration status: PENDING
    Current implementation: sms-service/src/main.py
    """

    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None,
    ):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number

    async def send(self, to: str, message: str) -> dict:
        """
        Send an SMS message.

        Args:
            to: Recipient phone number
            message: Message content

        Returns:
            Dict with send status
        """
        # TODO: Migrate from sms-service/src/main.py
        raise NotImplementedError(
            "SMS sender not yet migrated. "
            "Use sms-service directly during migration."
        )
