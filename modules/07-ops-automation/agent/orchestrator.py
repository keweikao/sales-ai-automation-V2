"""
Ops Orchestrator - Coordinates all ops automation services.

Runs health checks, collects statistics, executes remediation,
and optionally runs LLM analysis.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from google.cloud import firestore

from ..health_check import HealthChecker, ServiceStatus, SystemHealthReport
from ..monitoring.error_notifier import ErrorNotifier
from ..remediation import AutoRetryService, DataCleanupService
from ..history import HealthHistoryService, HealthHistoryRecord, StatsCollector, ProcessingStats

logger = logging.getLogger(__name__)


@dataclass
class OpsRunResult:
    """Result of a complete ops run."""

    run_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Health check results
    health_report: Optional[Dict[str, Any]] = None
    overall_status: str = "unknown"

    # Processing statistics
    processing_stats: Optional[ProcessingStats] = None

    # Error stats from buffer
    error_stats: Optional[Dict[str, Any]] = None

    # Remediation results
    retry_result: Optional[Dict[str, Any]] = None
    cleanup_result: Optional[Dict[str, Any]] = None
    remediation_executed: bool = False

    # LLM Analysis (optional)
    analysis: Optional[Any] = None  # OpsAnalysisResult if available

    # Metadata
    period_type: str = "scheduled"  # morning, evening, scheduled
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    notification_sent: bool = False
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "runId": self.run_id,
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
            "healthReport": self.health_report,
            "overallStatus": self.overall_status,
            "processingStats": (
                self.processing_stats.to_dict() if self.processing_stats else None
            ),
            "errorStats": self.error_stats,
            "retryResult": self.retry_result,
            "cleanupResult": self.cleanup_result,
            "remediationExecuted": self.remediation_executed,
            "periodType": self.period_type,
            "periodStart": self.period_start.isoformat() if self.period_start else None,
            "periodEnd": self.period_end.isoformat() if self.period_end else None,
            "notificationSent": self.notification_sent,
            "errors": self.errors,
        }

    @property
    def duration_seconds(self) -> float:
        """Get run duration in seconds."""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0


class OpsOrchestrator:
    """
    Orchestrates all ops automation components.

    Coordinates:
    - Health checks
    - Processing statistics collection
    - Error monitoring
    - Auto-retry
    - Data cleanup
    - LLM analysis (optional)
    - History recording
    """

    def __init__(
        self,
        health_checker: Optional[HealthChecker] = None,
        error_notifier: Optional[ErrorNotifier] = None,
        auto_retry: Optional[AutoRetryService] = None,
        cleanup_service: Optional[DataCleanupService] = None,
        stats_collector: Optional[StatsCollector] = None,
        history_service: Optional[HealthHistoryService] = None,
        db: Optional[firestore.Client] = None,
        enable_analysis: bool = False,
        enable_auto_remediation: bool = True,
        save_to_history: bool = True,
    ):
        self.db = db or firestore.Client()
        self.health_checker = health_checker or HealthChecker(db=self.db)
        self.error_notifier = error_notifier or ErrorNotifier()
        self.auto_retry = auto_retry or AutoRetryService(db=self.db)
        self.cleanup_service = cleanup_service or DataCleanupService(db=self.db)
        self.stats_collector = stats_collector or StatsCollector(db=self.db)
        self.history_service = history_service or HealthHistoryService(db=self.db)

        self.enable_analysis = enable_analysis
        self.enable_auto_remediation = enable_auto_remediation
        self.save_to_history = save_to_history

        # Lazy load OpsAgent if analysis is enabled
        self.ops_agent = None
        if enable_analysis:
            try:
                from .ops_agent import OpsAgent
                self.ops_agent = OpsAgent()
            except ImportError:
                logger.warning("OpsAgent not available, analysis disabled")

    async def run_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check."""
        try:
            report: SystemHealthReport = await self.health_checker.get_full_report()
            return {
                "overall_status": report.overall_status.value,
                "services": {
                    name: {
                        "status": result.status.value,
                        "latency_ms": result.latency_ms,
                        "error": result.error_message,
                        "details": result.details,
                    }
                    for name, result in report.services.items()
                },
                "summary": report.summary,
                "checked_at": report.checked_at.isoformat(),
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"error": str(e), "overall_status": "unknown"}

    async def run_auto_remediation(self) -> Dict[str, Any]:
        """Run auto-retry and cleanup."""
        result = {
            "retry": None,
            "cleanup": None,
        }

        if not self.enable_auto_remediation:
            return result

        # Auto-retry
        try:
            retry_result = await self.auto_retry.retry_all_failed()
            result["retry"] = {
                "transcription": {
                    "found": retry_result["transcription"].total_found,
                    "retried": retry_result["transcription"].total_retried,
                    "successful": retry_result["transcription"].successful,
                },
                "analysis": {
                    "found": retry_result["analysis"].total_found,
                    "retried": retry_result["analysis"].total_retried,
                    "successful": retry_result["analysis"].successful,
                },
            }
        except Exception as e:
            logger.error(f"Auto-retry failed: {e}")
            result["retry"] = {"error": str(e)}

        # Cleanup
        try:
            cleanup_result = await self.cleanup_service.run_full_cleanup(dry_run=False)
            result["cleanup"] = {
                category: {
                    "found": batch.total_found,
                    "processed": batch.total_processed,
                    "successful": batch.successful,
                }
                for category, batch in cleanup_result.items()
            }
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            result["cleanup"] = {"error": str(e)}

        return result

    def collect_processing_stats(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> ProcessingStats:
        """Collect processing statistics for a time period."""
        return self.stats_collector.collect_stats(
            start_time=start_time,
            end_time=end_time,
            include_comparison=True,
        )

    async def run_full_ops_cycle(
        self,
        period_type: str = "scheduled",
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> OpsRunResult:
        """
        Run a complete ops cycle.

        1. Health check
        2. Collect processing stats
        3. Collect error stats
        4. Auto-remediation (if enabled)
        5. LLM analysis (if enabled)
        6. Save to history (if enabled)

        Args:
            period_type: Type of report (morning, evening, scheduled)
            period_start: Start of the reporting period
            period_end: End of the reporting period

        Returns:
            OpsRunResult with comprehensive results
        """
        run_result = OpsRunResult(
            run_id=str(uuid.uuid4())[:8],
            started_at=datetime.now(timezone.utc),
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
        )

        # Default period to last 24 hours if not specified
        if period_end is None:
            period_end = datetime.now(timezone.utc)
        if period_start is None:
            period_start = period_end - timedelta(hours=24)

        run_result.period_start = period_start
        run_result.period_end = period_end

        # 1. Health check
        logger.info(f"[{run_result.run_id}] Running health check...")
        run_result.health_report = await self.run_health_check()
        run_result.overall_status = run_result.health_report.get(
            "overall_status", "unknown"
        )

        # 2. Collect processing stats
        logger.info(f"[{run_result.run_id}] Collecting processing stats...")
        try:
            run_result.processing_stats = self.collect_processing_stats(
                start_time=period_start,
                end_time=period_end,
            )
        except Exception as e:
            logger.error(f"Failed to collect processing stats: {e}")
            run_result.errors.append(f"Stats collection failed: {e}")

        # 3. Collect error stats
        logger.info(f"[{run_result.run_id}] Collecting error stats...")
        try:
            run_result.error_stats = self.error_notifier.get_buffer_stats()
        except Exception as e:
            logger.error(f"Failed to get error stats: {e}")
            run_result.errors.append(f"Error stats failed: {e}")

        # 4. Auto-remediation
        if self.enable_auto_remediation:
            logger.info(f"[{run_result.run_id}] Running auto-remediation...")
            remediation_result = await self.run_auto_remediation()
            run_result.retry_result = remediation_result.get("retry")
            run_result.cleanup_result = remediation_result.get("cleanup")
            run_result.remediation_executed = True

        # 5. LLM Analysis (optional)
        if self.enable_analysis and self.ops_agent:
            logger.info(f"[{run_result.run_id}] Running LLM analysis...")
            try:
                run_result.analysis = self.ops_agent.analyze(
                    health_report=run_result.health_report,
                    error_stats=run_result.error_stats,
                    retry_stats=run_result.retry_result,
                    cleanup_stats=run_result.cleanup_result,
                    processing_stats=(
                        run_result.processing_stats.to_dict()
                        if run_result.processing_stats
                        else None
                    ),
                )
            except Exception as e:
                logger.error(f"Ops analysis failed: {e}")
                run_result.errors.append(f"Analysis failed: {e}")

        run_result.completed_at = datetime.now(timezone.utc)

        # 6. Save to history
        if self.save_to_history:
            logger.info(f"[{run_result.run_id}] Saving to history...")
            try:
                history_record = HealthHistoryRecord(
                    record_id=run_result.run_id,
                    checked_at=run_result.completed_at,
                    overall_status=run_result.overall_status,
                    period_type=period_type,
                    services=run_result.health_report.get("services", {}),
                    processing_stats=run_result.processing_stats,
                    run_duration_seconds=run_result.duration_seconds,
                    remediation_executed=run_result.remediation_executed,
                    remediation_results={
                        "retry": run_result.retry_result,
                        "cleanup": run_result.cleanup_result,
                    },
                )
                self.history_service.save_record(history_record)
            except Exception as e:
                logger.error(f"Failed to save history: {e}")
                run_result.errors.append(f"History save failed: {e}")

        logger.info(
            f"[{run_result.run_id}] Ops cycle completed in {run_result.duration_seconds:.2f}s"
        )
        return run_result

    async def run_morning_report(self) -> OpsRunResult:
        """
        Run morning report (09:30 Taiwan time).

        Covers period: Previous day 18:30 -> Current day 09:30 (15 hours)
        """
        now = datetime.now(timezone.utc)

        # Calculate period for morning report
        # Taiwan is UTC+8, so 09:30 Taiwan = 01:30 UTC
        # Period: previous day 18:30 Taiwan (10:30 UTC) to today 09:30 Taiwan (01:30 UTC)

        # End time is now (approximately 09:30 Taiwan)
        period_end = now

        # Start time is previous day 18:30 Taiwan = 10:30 UTC
        # That's 15 hours before 01:30 UTC
        period_start = period_end - timedelta(hours=15)

        return await self.run_full_ops_cycle(
            period_type="morning",
            period_start=period_start,
            period_end=period_end,
        )

    async def run_evening_report(self) -> OpsRunResult:
        """
        Run evening report (18:30 Taiwan time).

        Covers period: Current day 09:30 -> Current day 18:30 (9 hours)
        """
        now = datetime.now(timezone.utc)

        # Calculate period for evening report
        # Taiwan is UTC+8, so 18:30 Taiwan = 10:30 UTC
        # Period: today 09:30 Taiwan (01:30 UTC) to today 18:30 Taiwan (10:30 UTC)

        # End time is now (approximately 18:30 Taiwan)
        period_end = now

        # Start time is today 09:30 Taiwan = 01:30 UTC
        # That's 9 hours before 10:30 UTC
        period_start = period_end - timedelta(hours=9)

        return await self.run_full_ops_cycle(
            period_type="evening",
            period_start=period_start,
            period_end=period_end,
        )

    def get_comparison_data(
        self,
        current_time: datetime,
        period_type: str,
    ) -> Optional[HealthHistoryRecord]:
        """
        Get comparison data from the same time last week.

        Args:
            current_time: Current report time
            period_type: Type of report (morning, evening)

        Returns:
            The comparison record from last week
        """
        return self.history_service.get_comparison_record(
            current_time=current_time,
            period_type=period_type,
            days_ago=7,
        )
