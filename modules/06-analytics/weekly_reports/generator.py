"""
Weekly report generator.

Creates weekly performance summaries for the sales team.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from google.cloud import firestore

# 台灣時區 (UTC+8)
TW_TZ = timezone(timedelta(hours=8))


@dataclass
class RepStats:
    """Statistics for a single sales rep."""
    rep_id: str
    name: str
    conversation_count: int
    analyzed_count: int
    avg_meddic_score: float
    trend: str  # 'up', 'down', 'stable'
    strengths: List[str] = field(default_factory=list)
    improvement_areas: List[str] = field(default_factory=list)


@dataclass
class WeeklyReportData:
    """Data structure for weekly report."""
    period_start: datetime
    period_end: datetime
    total_conversations: int
    total_analyzed: int
    avg_meddic_score: float
    by_rep: List[RepStats]
    top_insights: List[str]
    coaching_highlights: List[str]
    generated_at: datetime = field(default_factory=lambda: datetime.now(TW_TZ))


class WeeklyReportGenerator:
    """Generates weekly performance reports with MEDDIC analysis."""

    COLLECTION = "cases"

    def __init__(self, db: Optional[firestore.Client] = None):
        self.db = db or firestore.Client()

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
        # Calculate date range (Taiwan time)
        if week_start is None:
            today = datetime.now(TW_TZ)
            # Go back to last Monday
            days_since_monday = today.weekday()
            if days_since_monday == 0:  # If today is Monday, use last week
                days_since_monday = 7
            week_start = (today - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif week_start.tzinfo is None:
            week_start = week_start.replace(tzinfo=TW_TZ)

        week_end = (week_start + timedelta(days=6)).replace(
            hour=23, minute=59, second=59, microsecond=999999
        )

        # Convert to UTC for Firestore query
        week_start_utc = week_start.astimezone(timezone.utc)
        week_end_utc = week_end.astimezone(timezone.utc)

        # Query conversations from the period
        cases = self._query_cases(week_start_utc, week_end_utc)

        # Aggregate metrics
        rep_stats = self._aggregate_by_rep(cases)

        # Calculate totals
        total_conversations = len(cases)
        total_analyzed = sum(1 for c in cases if c.get("status") == "completed")

        # Calculate average MEDDIC score
        meddic_scores = []
        for case in cases:
            score = self._extract_meddic_score(case)
            if score is not None:
                meddic_scores.append(score)
        avg_meddic = sum(meddic_scores) / len(meddic_scores) if meddic_scores else 0.0

        # Generate insights
        top_insights = self._generate_insights(cases, rep_stats)
        coaching_highlights = self._generate_coaching_highlights(cases)

        return WeeklyReportData(
            period_start=week_start,
            period_end=week_end,
            total_conversations=total_conversations,
            total_analyzed=total_analyzed,
            avg_meddic_score=avg_meddic,
            by_rep=rep_stats,
            top_insights=top_insights,
            coaching_highlights=coaching_highlights,
        )

    def _query_cases(self, start_utc: datetime, end_utc: datetime) -> List[Dict[str, Any]]:
        """Query cases from Firestore within date range."""
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = (
            self.db.collection(self.COLLECTION)
            .where(filter=FieldFilter("createdAt", ">=", start_utc))
            .where(filter=FieldFilter("createdAt", "<=", end_utc))
            .order_by("createdAt", direction=firestore.Query.DESCENDING)
        )

        docs = query.stream()
        cases = []
        for doc in docs:
            data = doc.to_dict()
            data["caseId"] = doc.id
            cases.append(data)

        return cases

    def _extract_meddic_score(self, case: Dict[str, Any]) -> Optional[float]:
        """Extract MEDDIC score from case analysis."""
        analysis = case.get("analysis", {})
        if not analysis:
            return None

        # Try different paths for MEDDIC score
        meddic = analysis.get("meddic", {})
        if isinstance(meddic, dict):
            score = meddic.get("total_score") or meddic.get("totalScore")
            if score is not None:
                return float(score)

        # Fallback to direct meddicScore field
        score = analysis.get("meddicScore") or analysis.get("meddic_score")
        if score is not None:
            return float(score)

        return None

    def _aggregate_by_rep(self, cases: List[Dict[str, Any]]) -> List[RepStats]:
        """Aggregate case statistics by sales rep."""
        rep_data: Dict[str, Dict[str, Any]] = {}

        for case in cases:
            rep_name = (
                case.get("uploadedByName")
                or case.get("salesRepName")
                or "未知業務"
            )
            rep_id = case.get("salesRepId") or case.get("uploadedBy") or rep_name

            if rep_name not in rep_data:
                rep_data[rep_name] = {
                    "rep_id": rep_id,
                    "name": rep_name,
                    "cases": [],
                    "meddic_scores": [],
                    "coaching_insights": [],
                }

            rep_data[rep_name]["cases"].append(case)

            score = self._extract_meddic_score(case)
            if score is not None:
                rep_data[rep_name]["meddic_scores"].append(score)

            # Collect coaching insights
            analysis = case.get("analysis", {})
            coaching = analysis.get("sellerCoaching", {}) or analysis.get("seller_coaching", {})
            if coaching:
                insights = coaching.get("insights", [])
                rep_data[rep_name]["coaching_insights"].extend(insights)

        # Build RepStats list
        results = []
        for rep_name, data in rep_data.items():
            scores = data["meddic_scores"]
            avg_score = sum(scores) / len(scores) if scores else 0.0

            # Determine trend (placeholder - would need historical data)
            trend = "stable"
            if avg_score >= 70:
                trend = "up"
            elif avg_score < 50:
                trend = "down"

            # Extract strengths and improvement areas from coaching insights
            strengths = []
            improvements = []
            for insight in data["coaching_insights"]:
                if isinstance(insight, dict):
                    category = insight.get("category", "")
                    content = insight.get("content", "")
                    if category == "strength" and content:
                        strengths.append(content)
                    elif category == "improvement" and content:
                        improvements.append(content)

            results.append(RepStats(
                rep_id=data["rep_id"],
                name=data["name"],
                conversation_count=len(data["cases"]),
                analyzed_count=sum(1 for c in data["cases"] if c.get("status") == "completed"),
                avg_meddic_score=avg_score,
                trend=trend,
                strengths=strengths[:3],  # Top 3
                improvement_areas=improvements[:3],  # Top 3
            ))

        # Sort by conversation count descending
        results.sort(key=lambda x: x.conversation_count, reverse=True)
        return results

    def _generate_insights(
        self, cases: List[Dict[str, Any]], rep_stats: List[RepStats]
    ) -> List[str]:
        """Generate top insights from the week's data."""
        insights = []

        if not cases:
            return ["本週無對話記錄"]

        # Total conversations insight
        total = len(cases)
        analyzed = sum(1 for c in cases if c.get("status") == "completed")
        insights.append(f"本週共有 {total} 通對話，已分析 {analyzed} 通")

        # Top performer insight
        if rep_stats:
            top_rep = rep_stats[0]
            if top_rep.avg_meddic_score >= 70:
                insights.append(
                    f"{top_rep.name} 表現優異，平均 MEDDIC 分數達 {top_rep.avg_meddic_score:.0f} 分"
                )

        # Average score trend
        scores = [self._extract_meddic_score(c) for c in cases]
        valid_scores = [s for s in scores if s is not None]
        if valid_scores:
            avg = sum(valid_scores) / len(valid_scores)
            if avg >= 70:
                insights.append(f"團隊平均 MEDDIC 分數 {avg:.0f} 分，表現良好")
            elif avg < 50:
                insights.append(f"團隊平均 MEDDIC 分數 {avg:.0f} 分，建議加強訓練")

        # Completion rate
        if total > 0:
            completion_rate = (analyzed / total) * 100
            if completion_rate < 80:
                insights.append(f"分析完成率 {completion_rate:.0f}%，部分對話尚待分析")

        return insights[:5]  # Return top 5 insights

    def _generate_coaching_highlights(self, cases: List[Dict[str, Any]]) -> List[str]:
        """Extract coaching highlights from analyzed cases."""
        highlights = []

        for case in cases:
            analysis = case.get("analysis", {})
            if not analysis:
                continue

            coaching = analysis.get("sellerCoaching", {}) or analysis.get("seller_coaching", {})
            if not coaching:
                continue

            # Get recommended strategy
            strategy = coaching.get("recommendedStrategy") or coaching.get("recommended_strategy")
            if strategy and len(strategy) > 20:
                highlights.append(strategy)

            # Get action insights
            insights = coaching.get("insights", [])
            for insight in insights:
                if isinstance(insight, dict):
                    if insight.get("category") == "action" and insight.get("priority") == "high":
                        content = insight.get("content", "")
                        if content:
                            highlights.append(content)

        # Deduplicate and return top highlights
        unique_highlights = list(dict.fromkeys(highlights))
        return unique_highlights[:5]

    def format_slack_message(self, report: WeeklyReportData) -> dict:
        """Format report as Slack message blocks."""
        # Score color
        score_emoji = "🟢" if report.avg_meddic_score >= 70 else "🟡" if report.avg_meddic_score >= 40 else "🔴"

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
                        "text": f"*平均 MEDDIC:* {score_emoji} {report.avg_meddic_score:.1f}/100"
                    },
                ]
            },
            {"type": "divider"},
        ]

        # Add per-rep breakdown
        if report.by_rep:
            medals = ["🥇", "🥈", "🥉"]
            rep_lines = []
            for i, rep in enumerate(report.by_rep[:5]):
                medal = medals[i] if i < 3 else "•"
                trend_emoji = "📈" if rep.trend == "up" else "📉" if rep.trend == "down" else "➡️"
                rep_lines.append(
                    f"{medal} *{rep.name}*: {rep.conversation_count} 對話, "
                    f"平均 {rep.avg_meddic_score:.0f} 分 {trend_emoji}"
                )

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📋 業務表現排名:*\n" + "\n".join(rep_lines)
                }
            })

        # Add insights
        if report.top_insights:
            blocks.append({"type": "divider"})
            insights_text = "\n".join([f"• {insight}" for insight in report.top_insights])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*💡 本週洞察:*\n{insights_text}"
                }
            })

        # Add coaching highlights
        if report.coaching_highlights:
            blocks.append({"type": "divider"})
            highlights_text = "\n".join([f"• {h}" for h in report.coaching_highlights[:3]])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🎯 重點指導建議:*\n{highlights_text}"
                }
            })

        # Footer
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"📅 報表產生時間: {report.generated_at.strftime('%Y-%m-%d %H:%M')} (台灣時間)"
                }
            ]
        })

        return {"blocks": blocks}
