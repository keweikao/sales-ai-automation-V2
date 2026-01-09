"""
Analytics Service for Firestore aggregations.
"""

from datetime import datetime, timedelta
from typing import Optional


from deps.firestore import FirestoreService


class AnalyticsService(FirestoreService):
    """Service for analytics-related Firestore operations."""

    CASES_COLLECTION = "cases"
    WEEKLY_REPORTS_COLLECTION = "weekly_reports"

    def get_dashboard_stats(self) -> dict:
        """
        Get dashboard statistics.

        Returns aggregated stats for:
        - Total conversations
        - Completed today
        - Pending analysis
        - Average MEDDIC score
        - Top performers
        """
        cases_ref = self.db.collection(self.CASES_COLLECTION)

        # Get all cases for aggregation
        all_cases = list(cases_ref.stream())
        total = len(all_cases)

        # Today's date at midnight
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        completed_today = 0
        pending = 0
        meddic_scores = []
        rep_stats: dict[str, dict] = {}

        for doc in all_cases:
            data = doc.to_dict()
            status = data.get("status", "")

            # Count by status
            if status == "completed":
                completed_at = data.get("completedAt")
                if completed_at:
                    if isinstance(completed_at, datetime) and completed_at >= today:
                        completed_today += 1
            elif status in ("pending", "processing", "transcribing", "analyzing"):
                pending += 1

            # Extract MEDDIC score from analysis
            analysis = data.get("analysis", {})
            agents = analysis.get("agents", {})
            agent2 = agents.get("agent2", {})
            agent2_data = agent2.get("data", {})

            if score := agent2_data.get("meddic_score"):
                meddic_scores.append(score)

            # Aggregate by rep
            rep_id = data.get("uploadedBy") or data.get("salesRepId")
            rep_name = data.get("uploadedByName") or data.get("salesRepName", "Unknown")

            if rep_id:
                if rep_id not in rep_stats:
                    rep_stats[rep_id] = {
                        "id": rep_id,
                        "name": rep_name,
                        "count": 0,
                        "scores": [],
                    }
                rep_stats[rep_id]["count"] += 1
                if score:
                    rep_stats[rep_id]["scores"].append(score)

        # Calculate averages
        avg_meddic = sum(meddic_scores) / len(meddic_scores) if meddic_scores else 0

        # Get top performers
        top_performers = []
        for rep_id, stats in rep_stats.items():
            avg_score = (
                sum(stats["scores"]) / len(stats["scores"])
                if stats["scores"]
                else 0
            )
            top_performers.append({
                "id": rep_id,
                "name": stats["name"],
                "conversationCount": stats["count"],
                "avgMeddicScore": round(avg_score, 1),
            })

        # Sort by average score descending
        top_performers.sort(key=lambda x: x["avgMeddicScore"], reverse=True)

        # Determine trend (simplified)
        trend = "stable"
        if len(meddic_scores) >= 10:
            recent = meddic_scores[-5:]
            older = meddic_scores[-10:-5]
            recent_avg = sum(recent) / len(recent)
            older_avg = sum(older) / len(older)
            if recent_avg > older_avg + 5:
                trend = "up"
            elif recent_avg < older_avg - 5:
                trend = "down"

        return {
            "totalConversations": total,
            "completedToday": completed_today,
            "pendingAnalysis": pending,
            "avgMeddicScore": round(avg_meddic, 1),
            "conversionRate": 0.0,  # Would need conversion tracking
            "topPerformers": top_performers[:5],
            "recentTrend": trend,
        }

    def get_weekly_report(
        self,
        week_start: Optional[datetime] = None,
    ) -> Optional[dict]:
        """
        Get weekly report summary.

        Args:
            week_start: Start of the week to fetch. Defaults to last week.
        """
        if week_start is None:
            today = datetime.now()
            # Go back to last Monday
            week_start = today - timedelta(days=today.weekday() + 7)

        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

        # Try to find existing report
        reports_ref = self.db.collection(self.WEEKLY_REPORTS_COLLECTION)
        query = reports_ref.where("periodStart", ">=", week_start).where(
            "periodStart", "<=", week_end
        ).limit(1)

        for doc in query.stream():
            data = doc.to_dict()
            data["id"] = doc.id
            return data

        # Generate report from cases if not found
        return self._generate_weekly_report(week_start, week_end)

    def _generate_weekly_report(
        self,
        week_start: datetime,
        week_end: datetime,
    ) -> dict:
        """Generate weekly report from cases data."""
        cases_ref = self.db.collection(self.CASES_COLLECTION)

        # Query cases in date range
        query = cases_ref.where("createdAt", ">=", week_start).where(
            "createdAt", "<=", week_end
        )

        total = 0
        analyzed = 0
        scores = []
        by_rep: dict[str, dict] = {}

        for doc in query.stream():
            data = doc.to_dict()
            total += 1

            if data.get("status") == "completed":
                analyzed += 1

            # Extract score
            analysis = data.get("analysis", {})
            agent2 = analysis.get("agents", {}).get("agent2", {})
            if score := agent2.get("data", {}).get("meddic_score"):
                scores.append(score)

            # Aggregate by rep
            rep_id = data.get("uploadedBy") or data.get("salesRepId")
            rep_name = data.get("uploadedByName") or data.get("salesRepName", "Unknown")

            if rep_id:
                if rep_id not in by_rep:
                    by_rep[rep_id] = {
                        "repId": rep_id,
                        "repName": rep_name,
                        "conversationCount": 0,
                        "avgScore": 0,
                        "scores": [],
                    }
                by_rep[rep_id]["conversationCount"] += 1
                if score:
                    by_rep[rep_id]["scores"].append(score)

        # Calculate rep averages
        rep_summaries = []
        for rep_id, stats in by_rep.items():
            avg = sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0
            rep_summaries.append({
                "repId": rep_id,
                "repName": stats["repName"],
                "conversationCount": stats["conversationCount"],
                "avgScore": round(avg, 1),
            })

        return {
            "periodStart": week_start,
            "periodEnd": week_end,
            "totalConversations": total,
            "totalAnalyzed": analyzed,
            "avgMeddicScore": round(sum(scores) / len(scores), 1) if scores else 0,
            "byRep": rep_summaries,
            "insights": [],
            "generatedAt": datetime.utcnow(),
        }

    def get_trends(self, period: str = "7d") -> dict:
        """
        Get trends data for the specified period.

        Args:
            period: Time period (7d, 30d, 90d)
        """
        days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 7)
        start_date = datetime.now() - timedelta(days=days)

        cases_ref = self.db.collection(self.CASES_COLLECTION)
        query = cases_ref.where("createdAt", ">=", start_date)

        # Aggregate by day
        daily_data: dict[str, dict] = {}

        for doc in query.stream():
            data = doc.to_dict()
            created_at = data.get("createdAt")

            if isinstance(created_at, datetime):
                day_key = created_at.strftime("%Y-%m-%d")
            else:
                continue

            if day_key not in daily_data:
                daily_data[day_key] = {
                    "date": day_key,
                    "conversationCount": 0,
                    "avgMeddicScore": 0,
                    "scores": [],
                }

            daily_data[day_key]["conversationCount"] += 1

            # Extract score
            analysis = data.get("analysis", {})
            agent2 = analysis.get("agents", {}).get("agent2", {})
            if score := agent2.get("data", {}).get("meddic_score"):
                daily_data[day_key]["scores"].append(score)

        # Calculate daily averages and format
        trend_data = []
        for day_key in sorted(daily_data.keys()):
            day = daily_data[day_key]
            avg = sum(day["scores"]) / len(day["scores"]) if day["scores"] else 0
            trend_data.append({
                "date": day_key,
                "conversationCount": day["conversationCount"],
                "avgMeddicScore": round(avg, 1),
            })

        # Determine overall trend
        overall_trend = "stable"
        if len(trend_data) >= 2:
            first_half = trend_data[: len(trend_data) // 2]
            second_half = trend_data[len(trend_data) // 2 :]

            first_avg = (
                sum(d["avgMeddicScore"] for d in first_half) / len(first_half)
                if first_half
                else 0
            )
            second_avg = (
                sum(d["avgMeddicScore"] for d in second_half) / len(second_half)
                if second_half
                else 0
            )

            if second_avg > first_avg + 3:
                overall_trend = "up"
            elif second_avg < first_avg - 3:
                overall_trend = "down"

        return {
            "period": period,
            "data": trend_data,
            "overallTrend": overall_trend,
        }

    def get_rep_stats(self, rep_id: str) -> Optional[dict]:
        """Get statistics for a specific sales rep."""
        cases_ref = self.db.collection(self.CASES_COLLECTION)

        # Query by rep ID (check both field names)
        query1 = cases_ref.where("uploadedBy", "==", rep_id)
        query2 = cases_ref.where("salesRepId", "==", rep_id)

        cases = list(query1.stream()) + list(query2.stream())

        if not cases:
            return None

        # Deduplicate by doc ID
        seen_ids = set()
        unique_cases = []
        for doc in cases:
            if doc.id not in seen_ids:
                seen_ids.add(doc.id)
                unique_cases.append(doc)

        scores = []
        rep_name = "Unknown"

        for doc in unique_cases:
            data = doc.to_dict()

            # Get rep name
            if name := data.get("uploadedByName") or data.get("salesRepName"):
                rep_name = name

            # Extract score
            analysis = data.get("analysis", {})
            agent2 = analysis.get("agents", {}).get("agent2", {})
            if score := agent2.get("data", {}).get("meddic_score"):
                scores.append(score)

        avg_score = sum(scores) / len(scores) if scores else 0

        # Determine trend
        trend = "stable"
        if len(scores) >= 4:
            recent = scores[-2:]
            older = scores[-4:-2]
            recent_avg = sum(recent) / len(recent)
            older_avg = sum(older) / len(older)
            if recent_avg > older_avg + 5:
                trend = "up"
            elif recent_avg < older_avg - 5:
                trend = "down"

        return {
            "id": rep_id,
            "name": rep_name,
            "conversationCount": len(unique_cases),
            "avgMeddicScore": round(avg_score, 1),
            "trend": trend,
        }
