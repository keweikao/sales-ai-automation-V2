"""
Weekly report job.

Generates and sends weekly performance reports to sales team.
"""

import logging
import importlib.util
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _load_weekly_report_generator():
    """Dynamically load WeeklyReportGenerator from 06-analytics module."""
    # Get the module path
    project_root = Path(__file__).parent.parent.parent.parent.parent
    module_path = project_root / "modules" / "06-analytics" / "weekly_reports" / "generator.py"

    if not module_path.exists():
        raise ImportError(f"Weekly report generator not found: {module_path}")

    # Load module dynamically
    spec = importlib.util.spec_from_file_location("weekly_reports_generator", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["weekly_reports_generator"] = module
    spec.loader.exec_module(module)

    return module.WeeklyReportGenerator, module.WeeklyReportData


async def generate_weekly_report(
    week_start: Optional[datetime] = None,
    send_notification: bool = True,
    notification_channel: Optional[str] = None,
) -> dict:
    """
    Generate weekly sales performance report.

    Args:
        week_start: Start of the week (defaults to last Monday)
        send_notification: Whether to send Slack notification
        notification_channel: Slack channel to send to (required if send_notification=True)

    Returns:
        Report data
    """
    # Calculate date range
    if week_start is None:
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday() + 7)

    week_end = week_start + timedelta(days=6)

    logger.info(f"Generating weekly report for {week_start.date()} - {week_end.date()}")

    try:
        # Load and use the generator
        WeeklyReportGenerator, _ = _load_weekly_report_generator()
        generator = WeeklyReportGenerator()
        report_data = await generator.generate(week_start=week_start)

        # Convert to dict format
        report = {
            "period": {
                "start": report_data.period_start.isoformat(),
                "end": report_data.period_end.isoformat(),
            },
            "summary": {
                "total_conversations": report_data.total_conversations,
                "total_analyzed": report_data.total_analyzed,
                "avg_meddic_score": report_data.avg_meddic_score,
            },
            "by_rep": report_data.by_rep,
            "insights": report_data.top_insights,
            "coaching_highlights": report_data.coaching_highlights,
            "generated_at": datetime.utcnow().isoformat(),
        }

        # Send notification if requested
        if send_notification and notification_channel:
            try:
                from infrastructure.services.notification.service import NotificationService

                notification_service = NotificationService()
                slack_message = generator.format_slack_message(report_data)

                await notification_service.send_slack_message(
                    channel=notification_channel,
                    text=f"週報: {week_start.strftime('%m/%d')} - {week_end.strftime('%m/%d')}",
                    blocks=slack_message.get("blocks"),
                )
                report["notification_sent"] = True
                logger.info(f"Weekly report notification sent to {notification_channel}")
            except Exception as e:
                logger.error(f"Failed to send weekly report notification: {e}")
                report["notification_sent"] = False
                report["notification_error"] = str(e)

        return report

    except Exception as e:
        logger.error(f"Failed to generate weekly report: {e}", exc_info=True)
        return {
            "error": str(e),
            "period": {
                "start": week_start.isoformat(),
                "end": week_end.isoformat(),
            },
            "generated_at": datetime.utcnow().isoformat(),
        }


async def run_weekly_report_job() -> dict:
    """
    Scheduled job entry point for weekly report.

    This is called by the scheduler service on a weekly basis.
    """
    import os

    # Get notification channel from environment
    notification_channel = os.getenv("WEEKLY_REPORT_CHANNEL", "#sales-reports")

    return await generate_weekly_report(
        send_notification=True,
        notification_channel=notification_channel,
    )
