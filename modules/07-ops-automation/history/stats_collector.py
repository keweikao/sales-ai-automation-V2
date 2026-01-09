"""
Processing statistics collector.

Collects statistics about case processing from Firestore:
- Slack uploads
- GCS files
- Transcriptions completed
- Analyses completed
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter


@dataclass
class ProcessingStats:
    """Processing statistics for a time period."""

    period_start: datetime
    period_end: datetime

    # Counts
    slack_uploads: int = 0
    gcs_files: int = 0
    transcriptions_completed: int = 0
    analyses_completed: int = 0

    # Success rate
    success_rate: float = 0.0

    # Failed cases (for recommendations)
    failed_case_ids: List[str] = field(default_factory=list)
    stuck_case_ids: List[str] = field(default_factory=list)

    # Comparison with previous period
    prev_slack_uploads: Optional[int] = None
    prev_gcs_files: Optional[int] = None
    prev_transcriptions_completed: Optional[int] = None
    prev_analyses_completed: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "periodStart": self.period_start,
            "periodEnd": self.period_end,
            "slackUploads": self.slack_uploads,
            "gcsFiles": self.gcs_files,
            "transcriptionsCompleted": self.transcriptions_completed,
            "analysesCompleted": self.analyses_completed,
            "successRate": self.success_rate,
            "failedCaseIds": self.failed_case_ids,
            "stuckCaseIds": self.stuck_case_ids,
            "prevSlackUploads": self.prev_slack_uploads,
            "prevGcsFiles": self.prev_gcs_files,
            "prevTranscriptionsCompleted": self.prev_transcriptions_completed,
            "prevAnalysesCompleted": self.prev_analyses_completed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessingStats":
        """Create from dictionary."""
        return cls(
            period_start=data.get("periodStart"),
            period_end=data.get("periodEnd"),
            slack_uploads=data.get("slackUploads", 0),
            gcs_files=data.get("gcsFiles", 0),
            transcriptions_completed=data.get("transcriptionsCompleted", 0),
            analyses_completed=data.get("analysesCompleted", 0),
            success_rate=data.get("successRate", 0.0),
            failed_case_ids=data.get("failedCaseIds", []),
            stuck_case_ids=data.get("stuckCaseIds", []),
            prev_slack_uploads=data.get("prevSlackUploads"),
            prev_gcs_files=data.get("prevGcsFiles"),
            prev_transcriptions_completed=data.get("prevTranscriptionsCompleted"),
            prev_analyses_completed=data.get("prevAnalysesCompleted"),
        )

    def get_comparison(self, field: str) -> str:
        """Get comparison string for a field (e.g., '+3 ↑' or '-2 ↓')."""
        current = getattr(self, field, 0)
        prev = getattr(self, f"prev_{field}", None)

        if prev is None:
            return "-"

        diff = current - prev
        if diff > 0:
            return f"+{diff} ↑"
        elif diff < 0:
            return f"{diff} ↓"
        else:
            return "="


class StatsCollector:
    """Collects processing statistics from Firestore."""

    def __init__(self, db: Optional[firestore.Client] = None):
        self.db = db or firestore.Client()

    def collect_stats(
        self,
        start_time: datetime,
        end_time: datetime,
        include_comparison: bool = True,
    ) -> ProcessingStats:
        """
        Collect processing statistics for a time period.

        Args:
            start_time: Start of the period
            end_time: End of the period
            include_comparison: Whether to include comparison with previous week

        Returns:
            ProcessingStats with counts and optional comparison
        """
        stats = ProcessingStats(
            period_start=start_time,
            period_end=end_time,
        )

        # Query cases in the time period
        cases_ref = self.db.collection("cases")

        query = (
            cases_ref
            .where(filter=FieldFilter("createdAt", ">=", start_time))
            .where(filter=FieldFilter("createdAt", "<=", end_time))
        )

        cases = list(query.stream())

        for case_doc in cases:
            data = case_doc.to_dict() or {}
            case_id = case_doc.id

            # Count Slack uploads (has uploadedBySlackName)
            if data.get("uploadedBySlackName"):
                stats.slack_uploads += 1

            # Count GCS files (has gcsUri)
            if data.get("gcsUri"):
                stats.gcs_files += 1

            # Count transcriptions completed
            status = data.get("status", "")
            if status in ["completed", "analyzed", "analysis_completed"]:
                stats.transcriptions_completed += 1

            # Count analyses completed (all agents successful)
            if self._is_analysis_complete(data):
                stats.analyses_completed += 1
            elif status == "failed":
                stats.failed_case_ids.append(case_id)
            elif status in ["transcribing", "analyzing", "processing"]:
                # Check if stuck (created more than 2 hours ago)
                created_at = data.get("createdAt")
                if created_at:
                    if isinstance(created_at, datetime):
                        age_hours = (end_time - created_at).total_seconds() / 3600
                        if age_hours > 2:
                            stats.stuck_case_ids.append(case_id)

        # Calculate success rate
        if stats.transcriptions_completed > 0:
            stats.success_rate = (
                stats.analyses_completed / stats.transcriptions_completed
            )

        # Get comparison with previous week (same time period, 7 days ago)
        if include_comparison:
            from datetime import timedelta

            prev_start = start_time - timedelta(days=7)
            prev_end = end_time - timedelta(days=7)
            prev_stats = self.collect_stats(
                prev_start, prev_end, include_comparison=False
            )

            stats.prev_slack_uploads = prev_stats.slack_uploads
            stats.prev_gcs_files = prev_stats.gcs_files
            stats.prev_transcriptions_completed = prev_stats.transcriptions_completed
            stats.prev_analyses_completed = prev_stats.analyses_completed

        return stats

    def _is_analysis_complete(self, case_data: Dict[str, Any]) -> bool:
        """Check if all 4 agents have completed analysis."""
        analysis = case_data.get("analysis", {})
        agents = analysis.get("agents", {})

        for i in range(1, 5):
            agent_key = f"agent{i}"
            agent_data = agents.get(agent_key, {})
            if agent_data.get("status") != "success":
                return False
            if not agent_data.get("data"):
                return False

        return True

    def get_period_summary(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> Dict[str, Any]:
        """
        Get a summary of processing for a period.

        Returns a dictionary suitable for Slack reporting.
        """
        stats = self.collect_stats(start_time, end_time)

        return {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "hours": (end_time - start_time).total_seconds() / 3600,
            },
            "counts": {
                "slack_uploads": stats.slack_uploads,
                "gcs_files": stats.gcs_files,
                "transcriptions_completed": stats.transcriptions_completed,
                "analyses_completed": stats.analyses_completed,
            },
            "comparisons": {
                "slack_uploads": stats.get_comparison("slack_uploads"),
                "gcs_files": stats.get_comparison("gcs_files"),
                "transcriptions_completed": stats.get_comparison(
                    "transcriptions_completed"
                ),
                "analyses_completed": stats.get_comparison("analyses_completed"),
            },
            "success_rate": stats.success_rate,
            "issues": {
                "failed_count": len(stats.failed_case_ids),
                "stuck_count": len(stats.stuck_case_ids),
                "failed_case_ids": stats.failed_case_ids[:5],  # Limit to 5
                "stuck_case_ids": stats.stuck_case_ids[:5],  # Limit to 5
            },
        }
