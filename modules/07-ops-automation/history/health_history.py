"""
Health history storage and retrieval.

Stores health check results and processing stats to Firestore
for historical analysis and weekly comparisons.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from .stats_collector import ProcessingStats


@dataclass
class HealthHistoryRecord:
    """A single health history record."""

    record_id: str
    checked_at: datetime
    overall_status: str  # healthy, degraded, unhealthy, unknown
    period_type: str  # morning, evening, scheduled

    # Service health status
    services: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Processing stats
    processing_stats: Optional[ProcessingStats] = None

    # Run metadata
    run_duration_seconds: float = 0.0
    remediation_executed: bool = False
    remediation_results: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firestore storage."""
        return {
            "recordId": self.record_id,
            "checkedAt": self.checked_at,
            "overallStatus": self.overall_status,
            "periodType": self.period_type,
            "services": self.services,
            "processingStats": (
                self.processing_stats.to_dict() if self.processing_stats else None
            ),
            "runDurationSeconds": self.run_duration_seconds,
            "remediationExecuted": self.remediation_executed,
            "remediationResults": self.remediation_results,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HealthHistoryRecord":
        """Create from Firestore document."""
        processing_stats = None
        if data.get("processingStats"):
            processing_stats = ProcessingStats.from_dict(data["processingStats"])

        return cls(
            record_id=data.get("recordId", ""),
            checked_at=data.get("checkedAt"),
            overall_status=data.get("overallStatus", "unknown"),
            period_type=data.get("periodType", "scheduled"),
            services=data.get("services", {}),
            processing_stats=processing_stats,
            run_duration_seconds=data.get("runDurationSeconds", 0.0),
            remediation_executed=data.get("remediationExecuted", False),
            remediation_results=data.get("remediationResults"),
        )


class HealthHistoryService:
    """
    Service for storing and retrieving health history.

    Uses Firestore collection 'ops_health_history' to store records.
    """

    COLLECTION_NAME = "ops_health_history"

    def __init__(self, db: Optional[firestore.Client] = None):
        self.db = db or firestore.Client()

    def save_record(self, record: HealthHistoryRecord) -> str:
        """
        Save a health history record to Firestore.

        Args:
            record: The health history record to save

        Returns:
            The document ID
        """
        doc_ref = self.db.collection(self.COLLECTION_NAME).document(record.record_id)
        doc_ref.set(record.to_dict())
        return record.record_id

    def get_record(self, record_id: str) -> Optional[HealthHistoryRecord]:
        """
        Get a specific health history record.

        Args:
            record_id: The record ID to retrieve

        Returns:
            The health history record or None if not found
        """
        doc_ref = self.db.collection(self.COLLECTION_NAME).document(record_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        return HealthHistoryRecord.from_dict(doc.to_dict())

    def get_recent_records(
        self,
        limit: int = 10,
        period_type: Optional[str] = None,
    ) -> List[HealthHistoryRecord]:
        """
        Get recent health history records.

        Args:
            limit: Maximum number of records to return
            period_type: Filter by period type (morning, evening, scheduled)

        Returns:
            List of health history records, newest first
        """
        query = self.db.collection(self.COLLECTION_NAME).order_by(
            "checkedAt", direction=firestore.Query.DESCENDING
        )

        if period_type:
            query = query.where(filter=FieldFilter("periodType", "==", period_type))

        query = query.limit(limit)

        records = []
        for doc in query.stream():
            records.append(HealthHistoryRecord.from_dict(doc.to_dict()))

        return records

    def get_records_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
        period_type: Optional[str] = None,
    ) -> List[HealthHistoryRecord]:
        """
        Get health history records in a time range.

        Args:
            start_time: Start of the range
            end_time: End of the range
            period_type: Filter by period type

        Returns:
            List of health history records
        """
        query = (
            self.db.collection(self.COLLECTION_NAME)
            .where(filter=FieldFilter("checkedAt", ">=", start_time))
            .where(filter=FieldFilter("checkedAt", "<=", end_time))
            .order_by("checkedAt", direction=firestore.Query.DESCENDING)
        )

        if period_type:
            query = query.where(filter=FieldFilter("periodType", "==", period_type))

        records = []
        for doc in query.stream():
            records.append(HealthHistoryRecord.from_dict(doc.to_dict()))

        return records

    def get_comparison_record(
        self,
        current_time: datetime,
        period_type: str,
        days_ago: int = 7,
    ) -> Optional[HealthHistoryRecord]:
        """
        Get the health record from the same time period N days ago.

        Useful for weekly comparisons.

        Args:
            current_time: The current report time
            period_type: The period type (morning, evening)
            days_ago: How many days back to look

        Returns:
            The comparison record or None if not found
        """
        # Look for a record from the same period type, N days ago
        target_time = current_time - timedelta(days=days_ago)
        window_start = target_time - timedelta(hours=1)
        window_end = target_time + timedelta(hours=1)

        records = self.get_records_in_range(
            start_time=window_start,
            end_time=window_end,
            period_type=period_type,
        )

        if records:
            return records[0]  # Return the closest match

        return None

    def get_weekly_summary(
        self,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get a summary of health over the past week.

        Args:
            end_time: End time for the week (defaults to now)

        Returns:
            Summary statistics for the week
        """
        if end_time is None:
            end_time = datetime.now(timezone.utc)

        start_time = end_time - timedelta(days=7)
        records = self.get_records_in_range(start_time, end_time)

        if not records:
            return {
                "total_checks": 0,
                "healthy_count": 0,
                "degraded_count": 0,
                "unhealthy_count": 0,
                "uptime_percent": 0.0,
            }

        healthy_count = sum(1 for r in records if r.overall_status == "healthy")
        degraded_count = sum(1 for r in records if r.overall_status == "degraded")
        unhealthy_count = sum(1 for r in records if r.overall_status == "unhealthy")
        total = len(records)

        # Calculate average processing stats
        total_slack_uploads = 0
        total_gcs_files = 0
        total_transcriptions = 0
        total_analyses = 0

        for record in records:
            if record.processing_stats:
                total_slack_uploads += record.processing_stats.slack_uploads
                total_gcs_files += record.processing_stats.gcs_files
                total_transcriptions += record.processing_stats.transcriptions_completed
                total_analyses += record.processing_stats.analyses_completed

        return {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
            "total_checks": total,
            "healthy_count": healthy_count,
            "degraded_count": degraded_count,
            "unhealthy_count": unhealthy_count,
            "uptime_percent": (healthy_count / total * 100) if total > 0 else 0.0,
            "processing_totals": {
                "slack_uploads": total_slack_uploads,
                "gcs_files": total_gcs_files,
                "transcriptions_completed": total_transcriptions,
                "analyses_completed": total_analyses,
            },
        }

    def cleanup_old_records(self, retention_days: int = 90) -> int:
        """
        Delete records older than the retention period.

        Args:
            retention_days: Number of days to retain records

        Returns:
            Number of records deleted
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

        query = self.db.collection(self.COLLECTION_NAME).where(
            filter=FieldFilter("checkedAt", "<", cutoff)
        )

        deleted_count = 0
        batch = self.db.batch()
        batch_size = 0

        for doc in query.stream():
            batch.delete(doc.reference)
            batch_size += 1
            deleted_count += 1

            # Commit in batches of 500
            if batch_size >= 500:
                batch.commit()
                batch = self.db.batch()
                batch_size = 0

        # Commit remaining
        if batch_size > 0:
            batch.commit()

        return deleted_count
