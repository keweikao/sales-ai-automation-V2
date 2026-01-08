"""
Daily reminder job.

Sends daily reminders to sales reps about pending follow-ups.
"""

from datetime import datetime
from typing import Optional


async def send_daily_reminder(
    date: Optional[datetime] = None,
) -> dict:
    """
    Send daily follow-up reminders to sales reps.

    Args:
        date: Date to check for follow-ups (defaults to today)

    Returns:
        Summary of reminders sent
    """
    if date is None:
        date = datetime.now()

    # TODO: Implement reminder logic
    # 1. Query conversations with pending follow-ups due today
    # 2. Group by sales rep
    # 3. Send personalized reminders via Slack DM

    result = {
        "date": date.isoformat(),
        "reminders_sent": 0,
        "reps_notified": [],
    }

    return result
