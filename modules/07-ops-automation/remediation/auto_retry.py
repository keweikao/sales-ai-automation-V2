"""
Auto retry service.

Automatically retries failed transcription and analysis tasks.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter


class RetryableTaskType(str, Enum):
    """Types of tasks that can be retried."""
    TRANSCRIPTION = "transcription"
    ANALYSIS = "analysis"


@dataclass
class RetryResult:
    """Result of a retry operation."""
    task_type: RetryableTaskType
    case_id: str
    success: bool
    attempt: int
    error_message: Optional[str] = None
    retried_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RetryBatchResult:
    """Result of a batch retry operation."""
    task_type: RetryableTaskType
    total_found: int
    total_retried: int
    successful: int
    failed: int
    results: List[RetryResult] = field(default_factory=list)


class AutoRetryService:
    """Automatically retries failed tasks."""

    COLLECTION = "cases"
    MAX_RETRY_ATTEMPTS = 3

    def __init__(
        self,
        db: Optional[firestore.Client] = None,
        transcription_callback: Optional[Callable] = None,
        analysis_callback: Optional[Callable] = None,
    ):
        """
        Initialize the auto retry service.

        Args:
            db: Firestore client
            transcription_callback: Function to call to retry transcription
            analysis_callback: Function to call to retry analysis
        """
        self.db = db or firestore.Client()
        self.transcription_callback = transcription_callback
        self.analysis_callback = analysis_callback

    async def retry_failed_transcriptions(
        self,
        max_retries: int = 3,
        hours_lookback: int = 24,
    ) -> int:
        """
        Retry failed transcription tasks.

        Args:
            max_retries: Maximum number of retry attempts per task
            hours_lookback: Only retry tasks failed within this many hours

        Returns:
            Number of successfully retried tasks
        """
        result = await self._retry_failed_tasks(
            task_type=RetryableTaskType.TRANSCRIPTION,
            status_field="transcriptionStatus",
            retry_field="transcriptionRetries",
            callback=self.transcription_callback,
            max_retries=max_retries,
            hours_lookback=hours_lookback,
        )
        return result.successful

    async def retry_failed_analyses(
        self,
        max_retries: int = 3,
        hours_lookback: int = 24,
    ) -> int:
        """
        Retry failed analysis tasks.

        Args:
            max_retries: Maximum number of retry attempts per task
            hours_lookback: Only retry tasks failed within this many hours

        Returns:
            Number of successfully retried tasks
        """
        result = await self._retry_failed_tasks(
            task_type=RetryableTaskType.ANALYSIS,
            status_field="analysisStatus",
            retry_field="analysisRetries",
            callback=self.analysis_callback,
            max_retries=max_retries,
            hours_lookback=hours_lookback,
        )
        return result.successful

    async def retry_all_failed(
        self,
        max_retries: int = 3,
        hours_lookback: int = 24,
    ) -> Dict[str, RetryBatchResult]:
        """
        Retry all failed tasks (both transcription and analysis).

        Args:
            max_retries: Maximum retry attempts per task
            hours_lookback: Only retry tasks failed within this many hours

        Returns:
            Dict with results for each task type
        """
        transcription_result = await self._retry_failed_tasks(
            task_type=RetryableTaskType.TRANSCRIPTION,
            status_field="transcriptionStatus",
            retry_field="transcriptionRetries",
            callback=self.transcription_callback,
            max_retries=max_retries,
            hours_lookback=hours_lookback,
        )

        analysis_result = await self._retry_failed_tasks(
            task_type=RetryableTaskType.ANALYSIS,
            status_field="analysisStatus",
            retry_field="analysisRetries",
            callback=self.analysis_callback,
            max_retries=max_retries,
            hours_lookback=hours_lookback,
        )

        return {
            "transcription": transcription_result,
            "analysis": analysis_result,
        }

    async def get_retry_candidates(
        self,
        task_type: RetryableTaskType,
        max_retries: int = 3,
        hours_lookback: int = 24,
    ) -> List[Dict[str, Any]]:
        """
        Get list of failed tasks eligible for retry.

        Args:
            task_type: Type of task to find
            max_retries: Maximum retry attempts
            hours_lookback: Only include tasks failed within this many hours

        Returns:
            List of case documents eligible for retry
        """
        status_field = (
            "transcriptionStatus" if task_type == RetryableTaskType.TRANSCRIPTION
            else "analysisStatus"
        )
        retry_field = (
            "transcriptionRetries" if task_type == RetryableTaskType.TRANSCRIPTION
            else "analysisRetries"
        )

        return self._query_failed_tasks(
            status_field=status_field,
            retry_field=retry_field,
            max_retries=max_retries,
            hours_lookback=hours_lookback,
        )

    async def _retry_failed_tasks(
        self,
        task_type: RetryableTaskType,
        status_field: str,
        retry_field: str,
        callback: Optional[Callable],
        max_retries: int,
        hours_lookback: int,
    ) -> RetryBatchResult:
        """Internal method to retry failed tasks of a specific type."""
        # Find failed tasks
        failed_cases = self._query_failed_tasks(
            status_field=status_field,
            retry_field=retry_field,
            max_retries=max_retries,
            hours_lookback=hours_lookback,
        )

        result = RetryBatchResult(
            task_type=task_type,
            total_found=len(failed_cases),
            total_retried=0,
            successful=0,
            failed=0,
        )

        if not failed_cases:
            return result

        for case in failed_cases:
            case_id = case.get("caseId")
            current_retries = case.get(retry_field, 0)

            if current_retries >= max_retries:
                continue

            # Update retry count
            self._update_retry_count(case_id, retry_field, current_retries + 1)
            result.total_retried += 1

            # Execute retry callback if provided
            retry_success = False
            error_msg = None

            if callback:
                try:
                    await callback(case_id, case)
                    retry_success = True
                except Exception as e:
                    error_msg = str(e)
            else:
                # No callback, just mark as pending for external processor
                self._mark_for_retry(case_id, status_field)
                retry_success = True

            retry_result = RetryResult(
                task_type=task_type,
                case_id=case_id,
                success=retry_success,
                attempt=current_retries + 1,
                error_message=error_msg,
            )
            result.results.append(retry_result)

            if retry_success:
                result.successful += 1
            else:
                result.failed += 1

        return result

    def _query_failed_tasks(
        self,
        status_field: str,
        retry_field: str,
        max_retries: int,
        hours_lookback: int,
    ) -> List[Dict[str, Any]]:
        """Query for failed tasks eligible for retry."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_lookback)

        # Query for failed status
        query = (
            self.db.collection(self.COLLECTION)
            .where(filter=FieldFilter(status_field, "==", "failed"))
            .where(filter=FieldFilter("createdAt", ">=", cutoff))
        )

        cases = []
        for doc in query.stream():
            data = doc.to_dict()
            data["caseId"] = doc.id

            # Filter by retry count in memory (Firestore limitation)
            current_retries = data.get(retry_field, 0)
            if current_retries < max_retries:
                cases.append(data)

        return cases

    def _update_retry_count(self, case_id: str, retry_field: str, count: int):
        """Update the retry count for a case."""
        self.db.collection(self.COLLECTION).document(case_id).update({
            retry_field: count,
            f"{retry_field}LastAttempt": datetime.now(timezone.utc),
        })

    def _mark_for_retry(self, case_id: str, status_field: str):
        """Mark a case for retry by setting status to pending."""
        self.db.collection(self.COLLECTION).document(case_id).update({
            status_field: "pending",
            "retryRequestedAt": datetime.now(timezone.utc),
        })
