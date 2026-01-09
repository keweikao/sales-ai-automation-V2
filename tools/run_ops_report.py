#!/usr/bin/env python3
"""
Run Ops Report - Manual execution script.

Usage:
    python tools/run_ops_report.py morning
    python tools/run_ops_report.py evening
    python tools/run_ops_report.py scheduled
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import uuid

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# ===== Inline dataclasses to avoid import issues =====

@dataclass
class ProcessingStats:
    """Processing statistics for a time period."""
    slack_uploads: int = 0
    gcs_files: int = 0
    transcriptions_completed: int = 0
    analyses_completed: int = 0
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    # Comparison with previous period
    comparison: Dict[str, int] = field(default_factory=dict)

    # Failed/stuck case IDs for recommendations
    failed_case_ids: List[str] = field(default_factory=list)
    stuck_case_ids: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.transcriptions_completed == 0:
            return 1.0
        return self.analyses_completed / self.transcriptions_completed

    def get_comparison(self, field_name: str) -> str:
        """Get comparison string for a field."""
        diff = self.comparison.get(field_name, 0)
        if diff > 0:
            return f"+{diff} ↑"
        elif diff < 0:
            return f"{diff} ↓"
        else:
            return "-"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slackUploads": self.slack_uploads,
            "gcsFiles": self.gcs_files,
            "transcriptionsCompleted": self.transcriptions_completed,
            "analysesCompleted": self.analyses_completed,
            "periodStart": self.period_start.isoformat() if self.period_start else None,
            "periodEnd": self.period_end.isoformat() if self.period_end else None,
            "comparison": self.comparison,
            "failedCaseIds": self.failed_case_ids,
            "stuckCaseIds": self.stuck_case_ids,
            "successRate": self.success_rate,
        }


@dataclass
class OpsRunResult:
    """Result of an ops run."""
    run_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    health_report: Optional[Dict[str, Any]] = None
    overall_status: str = "unknown"
    processing_stats: Optional[ProcessingStats] = None
    error_stats: Optional[Dict[str, Any]] = None
    retry_result: Optional[Dict[str, Any]] = None
    cleanup_result: Optional[Dict[str, Any]] = None
    remediation_executed: bool = False
    analysis: Any = None
    period_type: str = "scheduled"
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    notification_sent: bool = False
    errors: List[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0


# ===== Inline OpsReporter =====

class OpsReporter:
    """Generates Slack reports for ops status."""

    STATUS_EMOJI = {
        "healthy": "🟢",
        "degraded": "🟡",
        "unhealthy": "🔴",
        "unknown": "⚪",
        "critical": "🚨",
        "warning": "⚠️",
    }

    PERIOD_LABELS = {
        "morning": "早報",
        "evening": "晚報",
        "scheduled": "定期報告",
    }

    def build_health_report_blocks(self, run_result: OpsRunResult) -> List[Dict[str, Any]]:
        """Build Slack blocks for health report."""
        overall_status = run_result.overall_status
        status_emoji = self.STATUS_EMOJI.get(overall_status, "❓")
        period_label = self.PERIOD_LABELS.get(run_result.period_type, "報告")

        report_date = run_result.completed_at or datetime.now(timezone.utc)
        date_str = report_date.strftime("%Y/%m/%d")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji} 系統健康報告 - {date_str} {period_label}",
                    "emoji": True,
                }
            },
        ]

        # Period info section
        period_text = self._format_period_text(run_result)
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*整體狀態:* {overall_status.upper()}\n{period_text}",
            }
        })

        blocks.append({"type": "divider"})

        # Processing stats section
        if run_result.processing_stats:
            stats_blocks = self._build_stats_section(run_result.processing_stats)
            blocks.extend(stats_blocks)
            blocks.append({"type": "divider"})

        # Service status section
        if run_result.health_report and run_result.health_report.get("services"):
            service_blocks = self._build_service_section(run_result.health_report)
            blocks.extend(service_blocks)
            blocks.append({"type": "divider"})

        # Recommendations section
        recommendations = self._get_recommendations(run_result)
        if recommendations:
            rec_text = "\n".join(f"• {rec}" for rec in recommendations[:5])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📝 建議事項*\n{rec_text}",
                }
            })
            blocks.append({"type": "divider"})

        # Footer
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Run ID: `{run_result.run_id}` | 耗時: {run_result.duration_seconds:.1f}s",
                }
            ]
        })

        return blocks

    def _format_period_text(self, run_result: OpsRunResult) -> str:
        if run_result.period_start and run_result.period_end:
            start_str = run_result.period_start.strftime("%m/%d %H:%M")
            end_str = run_result.period_end.strftime("%m/%d %H:%M")
            hours = (run_result.period_end - run_result.period_start).total_seconds() / 3600
            return f"*報告區間:* {start_str} → {end_str} ({hours:.0f}h)"
        return ""

    def _build_stats_section(self, stats: ProcessingStats) -> List[Dict[str, Any]]:
        lines = [
            "*📊 處理量統計*",
            "```",
            "┌─────────────────┬────────┬─────────┐",
            "│ 階段            │ 數量   │ vs 上週  │",
            "├─────────────────┼────────┼─────────┤",
        ]

        rows = [
            ("Slack 上傳", stats.slack_uploads, stats.get_comparison("slack_uploads")),
            ("GCS 存放", stats.gcs_files, stats.get_comparison("gcs_files")),
            ("轉錄完成", stats.transcriptions_completed, stats.get_comparison("transcriptions_completed")),
            ("分析完成", stats.analyses_completed, stats.get_comparison("analyses_completed")),
        ]

        for label, count, comparison in rows:
            label_padded = label.ljust(15)
            count_str = str(count).ljust(6)
            comp_str = comparison.ljust(7)
            lines.append(f"│ {label_padded} │ {count_str} │ {comp_str} │")

        lines.append("└─────────────────┴────────┴─────────┘")
        lines.append("```")

        success_rate_pct = stats.success_rate * 100
        if stats.transcriptions_completed > 0:
            lines.append(
                f"成功率: {success_rate_pct:.1f}% ({stats.analyses_completed}/{stats.transcriptions_completed})"
            )

        return [{
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(lines),
            }
        }]

    def _build_service_section(self, health_report: Dict[str, Any]) -> List[Dict[str, Any]]:
        services = health_report.get("services", {})

        lines = ["*🔧 服務狀態*"]
        for name, status_info in services.items():
            status = status_info.get("status", "unknown")
            emoji = self.STATUS_EMOJI.get(status, "❓")

            latency = status_info.get("latency_ms")
            latency_str = f" ({latency:.0f}ms)" if latency else ""

            details = status_info.get("details", {})
            success_rate = details.get("success_rate")
            rate_str = f" - 成功率 {success_rate * 100:.1f}%" if success_rate is not None else ""

            error = status_info.get("error")
            error_str = f" - {error}" if error else ""

            lines.append(f"{emoji} {name}{latency_str}{rate_str}{error_str}")

        return [{
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(lines),
            }
        }]

    def _get_recommendations(self, run_result: OpsRunResult) -> List[str]:
        recommendations = []

        if run_result.processing_stats:
            stats = run_result.processing_stats

            if stats.failed_case_ids:
                case_list = ", ".join(stats.failed_case_ids[:3])
                recommendations.append(f"檢查失敗的案件: {case_list}")

            if stats.stuck_case_ids:
                case_list = ", ".join(stats.stuck_case_ids[:3])
                recommendations.append(f"追蹤卡住的案件: {case_list}")

            if stats.success_rate < 0.9 and stats.transcriptions_completed > 0:
                recommendations.append(
                    f"分析成功率偏低 ({stats.success_rate * 100:.1f}%)，建議檢查分析服務"
                )

        if run_result.health_report:
            services = run_result.health_report.get("services", {})
            for name, status_info in services.items():
                status = status_info.get("status", "")
                if status == "unhealthy":
                    error = status_info.get("error", "")
                    recommendations.append(f"服務 {name} 狀態異常: {error}" if error else f"服務 {name} 狀態異常，需要檢查")
                elif status == "degraded":
                    latency = status_info.get("latency_ms", 0)
                    if latency > 1000:
                        recommendations.append(f"服務 {name} 延遲過高 ({latency:.0f}ms)")

        return recommendations

    def format_text_report(self, run_result: OpsRunResult) -> str:
        lines = []

        period_label = self.PERIOD_LABELS.get(run_result.period_type, "報告")
        status_emoji = self.STATUS_EMOJI.get(run_result.overall_status, "❓")
        date_str = (run_result.completed_at or datetime.now(timezone.utc)).strftime("%Y/%m/%d")

        lines.append(f"{status_emoji} 系統健康報告 - {date_str} {period_label}")
        lines.append("━" * 30)
        lines.append(f"整體狀態: {run_result.overall_status.upper()}")

        if run_result.period_start and run_result.period_end:
            start_str = run_result.period_start.strftime("%m/%d %H:%M")
            end_str = run_result.period_end.strftime("%m/%d %H:%M")
            hours = (run_result.period_end - run_result.period_start).total_seconds() / 3600
            lines.append(f"報告區間: {start_str} → {end_str} ({hours:.0f}h)")

        lines.append("")

        if run_result.processing_stats:
            stats = run_result.processing_stats
            lines.append("📊 處理量統計")
            lines.append(f"  Slack 上傳: {stats.slack_uploads} {stats.get_comparison('slack_uploads')}")
            lines.append(f"  GCS 存放: {stats.gcs_files} {stats.get_comparison('gcs_files')}")
            lines.append(f"  轉錄完成: {stats.transcriptions_completed} {stats.get_comparison('transcriptions_completed')}")
            lines.append(f"  分析完成: {stats.analyses_completed} {stats.get_comparison('analyses_completed')}")
            if stats.transcriptions_completed > 0:
                lines.append(f"  成功率: {stats.success_rate * 100:.1f}%")
            lines.append("")

        if run_result.health_report and run_result.health_report.get("services"):
            lines.append("🔧 服務狀態")
            for name, status_info in run_result.health_report["services"].items():
                status = status_info.get("status", "unknown")
                emoji = self.STATUS_EMOJI.get(status, "❓")
                latency = status_info.get("latency_ms")
                latency_str = f" ({latency:.0f}ms)" if latency else ""
                lines.append(f"  {emoji} {name}{latency_str}")
            lines.append("")

        lines.append("━" * 30)
        lines.append(f"Run ID: {run_result.run_id} | 耗時: {run_result.duration_seconds:.1f}s")

        return "\n".join(lines)


# ===== Stats Collector =====

class StatsCollector:
    """Collects processing statistics from Firestore."""

    def __init__(self, db):
        self.db = db

    def collect_stats(
        self,
        start_time: datetime,
        end_time: datetime,
        include_comparison: bool = True
    ) -> ProcessingStats:
        """Collect processing stats for the given time period."""
        from google.cloud.firestore_v1.base_query import FieldFilter

        # Query cases collection
        cases_ref = self.db.collection("cases")

        # Get all cases in the time range
        query = (
            cases_ref
            .where(filter=FieldFilter("createdAt", ">=", start_time))
            .where(filter=FieldFilter("createdAt", "<=", end_time))
        )

        slack_uploads = 0
        gcs_files = 0
        transcriptions_completed = 0
        analyses_completed = 0
        failed_case_ids = []
        stuck_case_ids = []

        for doc in query.stream():
            data = doc.to_dict()
            case_id = doc.id

            # Slack uploads: has uploadedBySlackName
            if data.get("uploadedBySlackName"):
                slack_uploads += 1

            # GCS files: has gcsUri
            if data.get("gcsUri"):
                gcs_files += 1

            # Transcriptions completed: status is completed or analyzed
            status = data.get("status", "")
            if status in ["completed", "analyzed"]:
                transcriptions_completed += 1

            # Analyses completed: check analysis.agents for all successful
            analysis = data.get("analysis", {})
            if analysis:
                agents = analysis.get("agents", {})
                if agents:
                    all_success = all(
                        agent_data.get("status") == "success"
                        for agent_data in agents.values()
                        if isinstance(agent_data, dict)
                    )
                    if all_success and agents:
                        analyses_completed += 1
                    elif not all_success:
                        # Some agent failed
                        failed_case_ids.append(case_id)

            # Check for stuck cases
            if status in ["pending", "processing"]:
                created_at = data.get("createdAt")
                if created_at:
                    # If stuck for more than 1 hour
                    if isinstance(created_at, datetime):
                        age = (datetime.now(timezone.utc) - created_at.replace(tzinfo=timezone.utc)).total_seconds()
                    else:
                        age = 0
                    if age > 3600:  # 1 hour
                        stuck_case_ids.append(case_id)

        # Build comparison data
        comparison = {}
        if include_comparison:
            # Get stats from 7 days ago
            period_duration = end_time - start_time
            prev_end = start_time - timedelta(days=7)
            prev_start = prev_end - period_duration

            prev_stats = self._collect_raw_stats(prev_start, prev_end)

            comparison = {
                "slack_uploads": slack_uploads - prev_stats.get("slack_uploads", 0),
                "gcs_files": gcs_files - prev_stats.get("gcs_files", 0),
                "transcriptions_completed": transcriptions_completed - prev_stats.get("transcriptions_completed", 0),
                "analyses_completed": analyses_completed - prev_stats.get("analyses_completed", 0),
            }

        return ProcessingStats(
            slack_uploads=slack_uploads,
            gcs_files=gcs_files,
            transcriptions_completed=transcriptions_completed,
            analyses_completed=analyses_completed,
            period_start=start_time,
            period_end=end_time,
            comparison=comparison,
            failed_case_ids=failed_case_ids[:10],  # Limit to 10
            stuck_case_ids=stuck_case_ids[:10],
        )

    def _collect_raw_stats(self, start_time: datetime, end_time: datetime) -> Dict[str, int]:
        """Collect raw stats without comparison."""
        from google.cloud.firestore_v1.base_query import FieldFilter

        cases_ref = self.db.collection("cases")
        query = (
            cases_ref
            .where(filter=FieldFilter("createdAt", ">=", start_time))
            .where(filter=FieldFilter("createdAt", "<=", end_time))
        )

        stats = {
            "slack_uploads": 0,
            "gcs_files": 0,
            "transcriptions_completed": 0,
            "analyses_completed": 0,
        }

        for doc in query.stream():
            data = doc.to_dict()

            if data.get("uploadedBySlackName"):
                stats["slack_uploads"] += 1

            if data.get("gcsUri"):
                stats["gcs_files"] += 1

            status = data.get("status", "")
            if status in ["completed", "analyzed"]:
                stats["transcriptions_completed"] += 1

            analysis = data.get("analysis", {})
            if analysis:
                agents = analysis.get("agents", {})
                if agents:
                    all_success = all(
                        agent_data.get("status") == "success"
                        for agent_data in agents.values()
                        if isinstance(agent_data, dict)
                    )
                    if all_success and agents:
                        stats["analyses_completed"] += 1

        return stats


# ===== Health Checker (simplified) =====

async def run_health_check(db) -> Dict[str, Any]:
    """Run simplified health check."""
    import importlib.util
    import httpx

    ops_module_path = project_root / "modules" / "07-ops-automation"

    # Try to load the full HealthChecker
    try:
        hc_checker_path = ops_module_path / "health_check" / "checker.py"
        spec = importlib.util.spec_from_file_location("hc_checker", hc_checker_path)
        hc_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hc_module)

        health_checker = hc_module.HealthChecker(db=db)
        health_report = await health_checker.get_full_report()

        return {
            "overall_status": health_report.overall_status.value,
            "services": {
                name: {
                    "status": result.status.value,
                    "latency_ms": result.latency_ms,
                    "error": result.error_message,
                    "details": result.details,
                }
                for name, result in health_report.services.items()
            },
            "summary": health_report.summary,
            "checked_at": health_report.checked_at.isoformat(),
        }
    except Exception as e:
        logger.warning(f"Failed to run full health check: {e}, using simplified check")

        # Fallback: simplified health check
        services = {}
        overall_status = "healthy"

        # Check Firestore
        try:
            start = datetime.now()
            list(db.collection("cases").limit(1).stream())
            latency = (datetime.now() - start).total_seconds() * 1000
            services["database"] = {
                "status": "healthy",
                "latency_ms": latency,
                "error": None,
                "details": {},
            }
        except Exception as e:
            services["database"] = {
                "status": "unhealthy",
                "latency_ms": None,
                "error": str(e),
                "details": {},
            }
            overall_status = "unhealthy"

        return {
            "overall_status": overall_status,
            "services": services,
            "summary": f"簡易檢查完成: {len(services)} 服務",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }


# ===== Main Report Function =====

async def run_ops_report(report_type: str = "scheduled") -> dict:
    """Run ops report and send to Slack."""
    from google.cloud import firestore
    from infrastructure.services.notification.service import NotificationService

    # Channel configuration
    channel_id = os.getenv("OPS_REPORT_CHANNEL_ID", "C0A7C2HUXRR")
    channel = os.getenv("OPS_REPORT_CHANNEL", "#sales-reports")

    logger.info(f"Starting {report_type} ops report...")

    # Calculate time period
    now = datetime.now(timezone.utc)
    if report_type == "morning":
        # Morning report: previous day 18:30 -> current day 09:30 (15 hours)
        period_end = now
        period_start = now - timedelta(hours=15)
    elif report_type == "evening":
        # Evening report: current day 09:30 -> current day 18:30 (9 hours)
        period_end = now
        period_start = now - timedelta(hours=9)
    else:
        # Default: last 24 hours
        period_end = now
        period_start = now - timedelta(hours=24)

    try:
        db = firestore.Client()

        # 1. Run health check
        logger.info("Running health check...")
        health_dict = await run_health_check(db)

        # 2. Collect processing stats
        logger.info("Collecting processing stats...")
        stats_collector = StatsCollector(db=db)
        processing_stats = stats_collector.collect_stats(
            start_time=period_start,
            end_time=period_end,
            include_comparison=True,
        )

        # 3. Build result object
        run_result = OpsRunResult(
            run_id=str(uuid.uuid4())[:8],
            started_at=now,
            completed_at=datetime.now(timezone.utc),
            health_report=health_dict,
            overall_status=health_dict["overall_status"],
            processing_stats=processing_stats,
            period_type=report_type,
            period_start=period_start,
            period_end=period_end,
        )

        # 4. Generate report
        logger.info("Generating report...")
        reporter = OpsReporter()
        blocks = reporter.build_health_report_blocks(run_result)
        text_report = reporter.format_text_report(run_result)

        logger.info(f"Generated report:\n{text_report}")

        # 5. Send to Slack
        logger.info(f"Sending to Slack channel: {channel}")
        notification_service = NotificationService()
        await notification_service.send_slack_message(
            channel=channel_id,
            text=f"系統健康報告 - {report_type}",
            blocks=blocks,
        )

        logger.info("Report sent successfully!")

        return {
            "status": "success",
            "run_id": run_result.run_id,
            "report_type": report_type,
            "channel": channel,
            "overall_status": run_result.overall_status,
            "processing_stats": {
                "slack_uploads": processing_stats.slack_uploads,
                "gcs_files": processing_stats.gcs_files,
                "transcriptions_completed": processing_stats.transcriptions_completed,
                "analyses_completed": processing_stats.analyses_completed,
            },
            "duration_seconds": run_result.duration_seconds,
        }

    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)

        # Try to send error notification
        try:
            notification_service = NotificationService()
            await notification_service.send_slack_message(
                channel=channel_id,
                text=f"🔴 Ops 報告生成失敗: {str(e)}",
            )
        except Exception:
            pass

        return {
            "status": "error",
            "report_type": report_type,
            "error": str(e),
        }


if __name__ == "__main__":
    report_type = sys.argv[1] if len(sys.argv) > 1 else "scheduled"
    result = asyncio.run(run_ops_report(report_type))
    print(f"\nResult: {result}")
