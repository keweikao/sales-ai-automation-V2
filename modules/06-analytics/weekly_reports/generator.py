"""
Weekly report generator.

Creates weekly performance summaries for the sales team.
"""

from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass

from core.database import ConversationRepository


@dataclass
class WeeklyReportData:
    """Data structure for weekly report."""
    period_start: datetime
    period_end: datetime
    total_conversations: int
    total_analyzed: int
    avg_meddic_score: float
    by_rep: list[dict]
    top_insights: list[str]
    coaching_highlights: list[str]


class WeeklyReportGenerator:
    """Generates weekly performance reports."""

    def __init__(self, conversation_repo: Optional[ConversationRepository] = None):
        self.conversation_repo = conversation_repo or ConversationRepository()

    async def generate(
        self,
        week_start: Optional[datetime] = None,
    ) -> WeeklyReportData:
        """
        Generate weekly report.

        Args:
            week_start: Start of reporting week (defaults to last Monday)

        Returns:
            WeeklyReportData with report contents
        """
        # Calculate date range
        if week_start is None:
            today = datetime.now()
            week_start = today - timedelta(days=today.weekday() + 7)

        week_end = week_start + timedelta(days=6, hours=23, minutes=59)

        # TODO: Query conversations from the period
        # TODO: Aggregate metrics
        # TODO: Generate insights

        return WeeklyReportData(
            period_start=week_start,
            period_end=week_end,
            total_conversations=0,
            total_analyzed=0,
            avg_meddic_score=0.0,
            by_rep=[],
            top_insights=[],
            coaching_highlights=[],
        )

    def format_slack_message(self, report: WeeklyReportData) -> dict:
        """Format report as Slack message blocks."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 週報: {report.period_start.strftime('%m/%d')} - {report.period_end.strftime('%m/%d')}",
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*對話數量:* {report.total_conversations}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*已分析:* {report.total_analyzed}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*平均 MEDDIC:* {report.avg_meddic_score:.1f}/100"
                    },
                ]
            },
            {"type": "divider"},
        ]

        # Add per-rep breakdown
        if report.by_rep:
            rep_text = "\n".join([
                f"• {r['name']}: {r['count']} 對話, 平均 {r['avg_score']:.0f} 分"
                for r in report.by_rep
            ])
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*各業務表現:*\n{rep_text}"}
            })

        return {"blocks": blocks}
