"""
Data cleanup service.

Cleans up stale pending tasks and orphaned data.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter


class CleanupAction(str, Enum):
    """Types of cleanup actions."""
    MARK_FAILED = "mark_failed"
    DELETE = "delete"
    ARCHIVE = "archive"


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""
    case_id: str
    action: CleanupAction
    reason: str
    success: bool
    error_message: Optional[str] = None


@dataclass
class CleanupBatchResult:
    """Result of a batch cleanup operation."""
    action_type: str
    total_found: int
    total_processed: int
    successful: int
    failed: int
    results: List[CleanupResult] = field(default_factory=list)


class DataCleanupService:
    """Cleans up stale and orphaned data."""

    COLLECTION = "cases"

    def __init__(self, db: Optional[firestore.Client] = None):
        self.db = db or firestore.Client()

    async def cleanup_stale_pending(
        self,
        hours_threshold: int = 24,
        dry_run: bool = False,
    ) -> int:
        """
        Clean up tasks stuck in pending status for too long.

        Args:
            hours_threshold: Mark as failed if pending longer than this
            dry_run: If True, only report what would be cleaned up

        Returns:
            Number of tasks cleaned up
        """
        result = await self._cleanup_stale_status(
            status_field="status",
            status_value="pending",
            hours_threshold=hours_threshold,
            action=CleanupAction.MARK_FAILED,
            dry_run=dry_run,
        )
        return result.successful

    async def cleanup_stale_transcriptions(
        self,
        hours_threshold: int = 12,
        dry_run: bool = False,
    ) -> int:
        """
        Clean up transcriptions stuck in processing status.

        Args:
            hours_threshold: Mark as failed if processing longer than this
            dry_run: If True, only report what would be cleaned up

        Returns:
            Number of transcriptions cleaned up
        """
        result = await self._cleanup_stale_status(
            status_field="transcriptionStatus",
            status_value="processing",
            hours_threshold=hours_threshold,
            action=CleanupAction.MARK_FAILED,
            dry_run=dry_run,
        )
        return result.successful

    async def cleanup_stale_analyses(
        self,
        hours_threshold: int = 6,
        dry_run: bool = False,
    ) -> int:
        """
        Clean up analyses stuck in processing status.

        Args:
            hours_threshold: Mark as failed if processing longer than this
            dry_run: If True, only report what would be cleaned up

        Returns:
            Number of analyses cleaned up
        """
        result = await self._cleanup_stale_status(
            status_field="analysisStatus",
            status_value="processing",
            hours_threshold=hours_threshold,
            action=CleanupAction.MARK_FAILED,
            dry_run=dry_run,
        )
        return result.successful

    async def cleanup_orphaned_files(
        self,
        days_threshold: int = 30,
        dry_run: bool = False,
    ) -> CleanupBatchResult:
        """
        Clean up cases without associated audio files.

        Args:
            days_threshold: Only check cases older than this
            dry_run: If True, only report what would be cleaned up

        Returns:
            CleanupBatchResult with details
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_threshold)

        # Query for cases without audio URL
        query = (
            self.db.collection(self.COLLECTION)
            .where(filter=FieldFilter("createdAt", "<=", cutoff))
        )

        result = CleanupBatchResult(
            action_type="orphaned_files",
            total_found=0,
            total_processed=0,
            successful=0,
            failed=0,
        )

        for doc in query.stream():
            data = doc.to_dict()
            audio_url = data.get("audioUrl") or data.get("audio_url")

            if not audio_url:
                result.total_found += 1

                if not dry_run:
                    try:
                        # Archive or delete orphaned cases
                        self._archive_case(doc.id, data)
                        result.total_processed += 1
                        result.successful += 1
                        result.results.append(CleanupResult(
                            case_id=doc.id,
                            action=CleanupAction.ARCHIVE,
                            reason="No audio file associated",
                            success=True,
                        ))
                    except Exception as e:
                        result.failed += 1
                        result.results.append(CleanupResult(
                            case_id=doc.id,
                            action=CleanupAction.ARCHIVE,
                            reason="No audio file associated",
                            success=False,
                            error_message=str(e),
                        ))

        return result

    async def run_full_cleanup(
        self,
        dry_run: bool = True,
    ) -> Dict[str, CleanupBatchResult]:
        """
        Run all cleanup operations.

        Args:
            dry_run: If True, only report what would be cleaned up

        Returns:
            Dict with results for each cleanup type
        """
        results = {}

        # Cleanup stale pending
        stale_pending = await self._cleanup_stale_status(
            status_field="status",
            status_value="pending",
            hours_threshold=24,
            action=CleanupAction.MARK_FAILED,
            dry_run=dry_run,
        )
        results["stale_pending"] = stale_pending

        # Cleanup stale transcriptions
        stale_transcriptions = await self._cleanup_stale_status(
            status_field="transcriptionStatus",
            status_value="processing",
            hours_threshold=12,
            action=CleanupAction.MARK_FAILED,
            dry_run=dry_run,
        )
        results["stale_transcriptions"] = stale_transcriptions

        # Cleanup stale analyses
        stale_analyses = await self._cleanup_stale_status(
            status_field="analysisStatus",
            status_value="processing",
            hours_threshold=6,
            action=CleanupAction.MARK_FAILED,
            dry_run=dry_run,
        )
        results["stale_analyses"] = stale_analyses

        return results

    async def get_cleanup_candidates(
        self,
        status_field: str,
        status_value: str,
        hours_threshold: int,
    ) -> List[Dict[str, Any]]:
        """
        Get list of items that would be cleaned up.

        Args:
            status_field: Field to check status on
            status_value: Status value to look for
            hours_threshold: Age threshold in hours

        Returns:
            List of case documents that would be cleaned up
        """
        return self._query_stale_tasks(
            status_field=status_field,
            status_value=status_value,
            hours_threshold=hours_threshold,
        )

    async def _cleanup_stale_status(
        self,
        status_field: str,
        status_value: str,
        hours_threshold: int,
        action: CleanupAction,
        dry_run: bool,
    ) -> CleanupBatchResult:
        """Internal method to clean up tasks with stale status."""
        stale_cases = self._query_stale_tasks(
            status_field=status_field,
            status_value=status_value,
            hours_threshold=hours_threshold,
        )

        result = CleanupBatchResult(
            action_type=f"{status_field}_{status_value}",
            total_found=len(stale_cases),
            total_processed=0,
            successful=0,
            failed=0,
        )

        if dry_run:
            # Just return the count for dry run
            for case in stale_cases:
                result.results.append(CleanupResult(
                    case_id=case.get("caseId"),
                    action=action,
                    reason=f"Stale {status_field}={status_value} for >{hours_threshold}h",
                    success=True,
                ))
            return result

        for case in stale_cases:
            case_id = case.get("caseId")
            result.total_processed += 1

            try:
                if action == CleanupAction.MARK_FAILED:
                    self._mark_as_failed(case_id, status_field, hours_threshold)
                elif action == CleanupAction.DELETE:
                    self._delete_case(case_id)
                elif action == CleanupAction.ARCHIVE:
                    self._archive_case(case_id, case)

                result.successful += 1
                result.results.append(CleanupResult(
                    case_id=case_id,
                    action=action,
                    reason=f"Stale {status_field}={status_value} for >{hours_threshold}h",
                    success=True,
                ))
            except Exception as e:
                result.failed += 1
                result.results.append(CleanupResult(
                    case_id=case_id,
                    action=action,
                    reason=f"Stale {status_field}={status_value} for >{hours_threshold}h",
                    success=False,
                    error_message=str(e),
                ))

        return result

    def _query_stale_tasks(
        self,
        status_field: str,
        status_value: str,
        hours_threshold: int,
    ) -> List[Dict[str, Any]]:
        """Query for tasks that have been in a status too long."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_threshold)

        query = (
            self.db.collection(self.COLLECTION)
            .where(filter=FieldFilter(status_field, "==", status_value))
            .where(filter=FieldFilter("createdAt", "<=", cutoff))
        )

        cases = []
        for doc in query.stream():
            data = doc.to_dict()
            data["caseId"] = doc.id
            cases.append(data)

        return cases

    def _mark_as_failed(self, case_id: str, status_field: str, hours_stale: int):
        """Mark a case status as failed due to timeout."""
        self.db.collection(self.COLLECTION).document(case_id).update({
            status_field: "failed",
            f"{status_field}Error": f"Timed out after {hours_stale} hours in processing",
            f"{status_field}FailedAt": datetime.now(timezone.utc),
            "cleanupReason": "stale_timeout",
        })

    def _delete_case(self, case_id: str):
        """Delete a case document."""
        self.db.collection(self.COLLECTION).document(case_id).delete()

    def _archive_case(self, case_id: str, data: Dict[str, Any]):
        """Archive a case to a separate collection."""
        archive_data = {
            **data,
            "archivedAt": datetime.now(timezone.utc),
            "originalCaseId": case_id,
        }

        # Write to archive collection
        self.db.collection("cases_archive").add(archive_data)

        # Delete from main collection
        self.db.collection(self.COLLECTION).document(case_id).delete()
