"""
Ops Daily Report Job.

Generates and sends daily ops health reports to Slack.
Supports morning (09:30) and evening (18:30) reports.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _setup_ops_module_path():
    """
    Setup module path to allow importing from 07-ops-automation.

    Creates a symlink-like module alias so Python can import from
    the hyphenated directory name.
    """
    project_root = Path(__file__).parent.parent.parent.parent.parent

    # Add project root to path if not already
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Create module alias for the hyphenated directory
    ops_module_path = project_root / "modules" / "07-ops-automation"

    # Import via importlib.util to handle hyphenated name
    import importlib.util

    # Check if already loaded
    if "ops_automation" not in sys.modules:
        # Load the package __init__.py
        init_path = ops_module_path / "__init__.py"
        spec = importlib.util.spec_from_file_location(
            "ops_automation",
            init_path,
            submodule_search_locations=[str(ops_module_path)],
        )
        ops_module = importlib.util.module_from_spec(spec)
        sys.modules["ops_automation"] = ops_module

        # We need to load submodules manually for relative imports to work
        # Load health_check
        health_check_init = ops_module_path / "health_check" / "__init__.py"
        if health_check_init.exists():
            hc_spec = importlib.util.spec_from_file_location(
                "ops_automation.health_check",
                health_check_init,
                submodule_search_locations=[str(ops_module_path / "health_check")],
            )
            hc_module = importlib.util.module_from_spec(hc_spec)
            sys.modules["ops_automation.health_check"] = hc_module
            hc_spec.loader.exec_module(hc_module)

        # Load monitoring
        monitoring_init = ops_module_path / "monitoring" / "__init__.py"
        if monitoring_init.exists():
            mon_spec = importlib.util.spec_from_file_location(
                "ops_automation.monitoring",
                monitoring_init,
                submodule_search_locations=[str(ops_module_path / "monitoring")],
            )
            mon_module = importlib.util.module_from_spec(mon_spec)
            sys.modules["ops_automation.monitoring"] = mon_module
            mon_spec.loader.exec_module(mon_module)

        # Load remediation
        remediation_init = ops_module_path / "remediation" / "__init__.py"
        if remediation_init.exists():
            rem_spec = importlib.util.spec_from_file_location(
                "ops_automation.remediation",
                remediation_init,
                submodule_search_locations=[str(ops_module_path / "remediation")],
            )
            rem_module = importlib.util.module_from_spec(rem_spec)
            sys.modules["ops_automation.remediation"] = rem_module
            rem_spec.loader.exec_module(rem_module)

        # Load history
        history_init = ops_module_path / "history" / "__init__.py"
        if history_init.exists():
            hist_spec = importlib.util.spec_from_file_location(
                "ops_automation.history",
                history_init,
                submodule_search_locations=[str(ops_module_path / "history")],
            )
            hist_module = importlib.util.module_from_spec(hist_spec)
            sys.modules["ops_automation.history"] = hist_module
            hist_spec.loader.exec_module(hist_module)

        # Now exec the main module
        spec.loader.exec_module(ops_module)

    return sys.modules["ops_automation"]


async def run(
    report_type: str = "scheduled",
    slack_channel: Optional[str] = None,
    slack_channel_id: Optional[str] = None,
    include_insights: bool = True,
    include_recommendations: bool = True,
    include_weekly_comparison: bool = True,
) -> dict:
    """
    Run daily ops report job.

    Args:
        report_type: Type of report (morning, evening, scheduled)
        slack_channel: Slack channel name to send report to
        slack_channel_id: Slack channel ID (preferred over name)
        include_insights: Include AI insights in report
        include_recommendations: Include recommendations in report
        include_weekly_comparison: Include comparison with last week

    Returns:
        Job execution result
    """
    # Setup module path and import
    ops_module = _setup_ops_module_path()
    OpsOrchestrator = ops_module.OpsOrchestrator
    OpsReporter = ops_module.OpsReporter
    from infrastructure.services.notification.service import NotificationService

    # Default channel
    channel_id = slack_channel_id or os.getenv("OPS_REPORT_CHANNEL_ID", "C0A7C2HUXRR")
    channel = slack_channel or os.getenv("OPS_REPORT_CHANNEL", "#sales-reports")

    logger.info(f"Starting {report_type} ops report for channel: {channel}")

    try:
        # Create orchestrator
        orchestrator = OpsOrchestrator(
            enable_analysis=include_insights,
            enable_auto_remediation=True,
            save_to_history=True,
        )

        # Run appropriate report type
        if report_type == "morning":
            run_result = await orchestrator.run_morning_report()
        elif report_type == "evening":
            run_result = await orchestrator.run_evening_report()
        else:
            run_result = await orchestrator.run_full_ops_cycle(period_type=report_type)

        # Generate report blocks
        reporter = OpsReporter()
        blocks = reporter.build_health_report_blocks(run_result)

        # Also generate text version for logging
        text_report = reporter.format_text_report(run_result)
        logger.info(f"Generated report:\n{text_report}")

        # Send notification
        notification_service = NotificationService()
        await notification_service.send_slack_message(
            channel=channel_id,  # Use channel ID for reliability
            text=f"系統健康報告 - {run_result.period_type}",
            blocks=blocks,
        )

        run_result.notification_sent = True
        logger.info(f"{report_type} ops report sent to {channel}")

        return {
            "status": "success",
            "run_id": run_result.run_id,
            "report_type": report_type,
            "channel": channel,
            "overall_status": run_result.overall_status,
            "processing_stats": (
                {
                    "slack_uploads": run_result.processing_stats.slack_uploads,
                    "gcs_files": run_result.processing_stats.gcs_files,
                    "transcriptions_completed": run_result.processing_stats.transcriptions_completed,
                    "analyses_completed": run_result.processing_stats.analyses_completed,
                }
                if run_result.processing_stats
                else None
            ),
            "analysis_included": run_result.analysis is not None,
            "duration_seconds": run_result.duration_seconds,
        }

    except Exception as e:
        logger.error(f"{report_type} ops report failed: {e}", exc_info=True)

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


def run_sync(
    report_type: str = "scheduled",
    slack_channel: Optional[str] = None,
    slack_channel_id: Optional[str] = None,
    include_insights: bool = True,
    include_recommendations: bool = True,
    include_weekly_comparison: bool = True,
) -> dict:
    """Synchronous wrapper for the async run function."""
    return asyncio.run(
        run(
            report_type=report_type,
            slack_channel=slack_channel,
            slack_channel_id=slack_channel_id,
            include_insights=include_insights,
            include_recommendations=include_recommendations,
            include_weekly_comparison=include_weekly_comparison,
        )
    )


if __name__ == "__main__":
    # For manual testing
    import sys

    report_type = sys.argv[1] if len(sys.argv) > 1 else "scheduled"
    result = run_sync(report_type=report_type)
    print(f"Result: {result}")
