"""
Ops Health Check Job.

Runs periodic health checks and sends alerts if issues are detected.
"""

import asyncio
import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _load_ops_modules():
    """Dynamically load ops-automation module (handles hyphenated directory name)."""
    project_root = Path(__file__).parent.parent.parent.parent.parent
    module_path = project_root / "modules" / "07-ops-automation"

    # Load orchestrator
    orchestrator_path = module_path / "agent" / "orchestrator.py"
    spec = importlib.util.spec_from_file_location("ops_orchestrator", orchestrator_path)
    orchestrator_module = importlib.util.module_from_spec(spec)
    sys.modules["ops_orchestrator"] = orchestrator_module
    spec.loader.exec_module(orchestrator_module)

    # Load reporter
    reporter_path = module_path / "reporting" / "ops_reporter.py"
    spec = importlib.util.spec_from_file_location("ops_reporter", reporter_path)
    reporter_module = importlib.util.module_from_spec(spec)
    sys.modules["ops_reporter"] = reporter_module
    spec.loader.exec_module(reporter_module)

    return orchestrator_module.OpsOrchestrator, reporter_module.OpsReporter


async def run(
    send_alert_on_issue: bool = True,
    alert_channel: Optional[str] = None,
    alert_channel_id: Optional[str] = None,
    save_to_history: bool = True,
) -> dict:
    """
    Run ops health check job.

    Args:
        send_alert_on_issue: Send Slack alert if issues detected
        alert_channel: Slack channel name for alerts
        alert_channel_id: Slack channel ID (preferred)
        save_to_history: Save result to health history

    Returns:
        Job execution result
    """
    # Dynamically load modules (handles hyphenated directory name)
    OpsOrchestrator, OpsReporter = _load_ops_modules()
    from infrastructure.services.notification.service import NotificationService

    channel_id = alert_channel_id or os.getenv("OPS_ALERT_CHANNEL_ID", "C0A7C2HUXRR")
    channel = alert_channel or os.getenv("OPS_ALERT_CHANNEL", "#sales-reports")

    logger.info("Starting ops health check...")

    try:
        # Create orchestrator (no analysis for quick health check)
        orchestrator = OpsOrchestrator(
            enable_analysis=False,
            enable_auto_remediation=False,  # Don't remediate during health check
            save_to_history=save_to_history,
        )

        # Run health check only (not full cycle)
        health_report = await orchestrator.run_health_check()
        overall_status = health_report.get("overall_status", "unknown")

        logger.info(f"Health check complete: {overall_status}")

        # Send alert if unhealthy or degraded
        should_alert = (
            send_alert_on_issue
            and overall_status in ["unhealthy", "degraded", "critical"]
        )

        if should_alert:
            reporter = OpsReporter()
            notification_service = NotificationService()

            # Build alert message
            summary = health_report.get("summary", "Unknown issue detected")
            services = health_report.get("services", {})

            # Find problematic services
            problem_services = {
                name: info
                for name, info in services.items()
                if info.get("status") in ["unhealthy", "degraded"]
            }

            blocks = reporter.build_alert_blocks(
                issue=summary,
                severity=overall_status,
                details={
                    "問題服務": ", ".join(problem_services.keys()) or "None",
                    "檢查時間": health_report.get("checked_at", "Unknown"),
                },
            )

            await notification_service.send_slack_message(
                channel=channel_id,
                text=f"🔴 系統健康告警: {overall_status.upper()}",
                blocks=blocks,
            )

            logger.warning(f"Health alert sent: {overall_status}")

        return {
            "status": "success",
            "overall_status": overall_status,
            "alert_sent": should_alert,
            "services": {
                name: info.get("status")
                for name, info in health_report.get("services", {}).items()
            },
            "summary": health_report.get("summary"),
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)

        # Send error alert
        if send_alert_on_issue:
            try:
                notification_service = NotificationService()
                await notification_service.send_slack_message(
                    channel=channel_id,
                    text=f"🔴 健康檢查執行失敗: {str(e)}",
                )
            except Exception:
                pass

        return {
            "status": "error",
            "error": str(e),
        }


def run_sync(
    send_alert_on_issue: bool = True,
    alert_channel: Optional[str] = None,
    alert_channel_id: Optional[str] = None,
    save_to_history: bool = True,
) -> dict:
    """Synchronous wrapper."""
    return asyncio.run(
        run(
            send_alert_on_issue=send_alert_on_issue,
            alert_channel=alert_channel,
            alert_channel_id=alert_channel_id,
            save_to_history=save_to_history,
        )
    )


if __name__ == "__main__":
    result = run_sync()
    print(f"Result: {result}")
