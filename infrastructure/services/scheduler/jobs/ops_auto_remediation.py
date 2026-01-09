"""
Ops Auto Remediation Job.

Automatically retries failed tasks and cleans up stale data.
"""

import asyncio
import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _load_remediation_modules():
    """Dynamically load remediation modules (handles hyphenated directory name)."""
    project_root = Path(__file__).parent.parent.parent.parent.parent
    module_path = project_root / "modules" / "07-ops-automation" / "remediation"

    # Load auto_retry
    auto_retry_path = module_path / "auto_retry.py"
    spec = importlib.util.spec_from_file_location("ops_auto_retry", auto_retry_path)
    auto_retry_module = importlib.util.module_from_spec(spec)
    sys.modules["ops_auto_retry"] = auto_retry_module
    spec.loader.exec_module(auto_retry_module)

    # Load cleanup
    cleanup_path = module_path / "cleanup.py"
    spec = importlib.util.spec_from_file_location("ops_cleanup", cleanup_path)
    cleanup_module = importlib.util.module_from_spec(spec)
    sys.modules["ops_cleanup"] = cleanup_module
    spec.loader.exec_module(cleanup_module)

    return auto_retry_module.AutoRetryService, cleanup_module.DataCleanupService


async def run(
    retry_transcriptions: bool = True,
    retry_analyses: bool = True,
    cleanup_stale: bool = True,
    notify_on_success: bool = False,
    notify_on_failure: bool = True,
    alert_channel: Optional[str] = None,
    alert_channel_id: Optional[str] = None,
) -> dict:
    """
    Run auto remediation job.

    Args:
        retry_transcriptions: Retry failed transcription tasks
        retry_analyses: Retry failed analysis tasks
        cleanup_stale: Clean up stale pending/processing tasks
        notify_on_success: Send notification on successful remediation
        notify_on_failure: Send notification on failed remediation
        alert_channel: Slack channel name for notifications
        alert_channel_id: Slack channel ID (preferred)

    Returns:
        Job execution result
    """
    # Dynamically load modules (handles hyphenated directory name)
    AutoRetryService, DataCleanupService = _load_remediation_modules()
    from infrastructure.services.notification.service import NotificationService
    from google.cloud import firestore

    channel_id = alert_channel_id or os.getenv("OPS_ALERT_CHANNEL_ID", "C0A7C2HUXRR")

    logger.info("Starting auto remediation...")

    result = {
        "status": "success",
        "retry": None,
        "cleanup": None,
        "total_fixed": 0,
    }

    db = firestore.Client()

    # Auto-retry
    if retry_transcriptions or retry_analyses:
        try:
            auto_retry = AutoRetryService(db=db)
            retry_result = await auto_retry.retry_all_failed()

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

            result["total_fixed"] += (
                retry_result["transcription"].successful
                + retry_result["analysis"].successful
            )

            logger.info(
                f"Auto-retry complete: "
                f"{retry_result['transcription'].successful} transcriptions, "
                f"{retry_result['analysis'].successful} analyses"
            )

        except Exception as e:
            logger.error(f"Auto-retry failed: {e}", exc_info=True)
            result["retry"] = {"error": str(e)}

            if notify_on_failure:
                try:
                    notification_service = NotificationService()
                    await notification_service.send_slack_message(
                        channel=channel_id,
                        text=f"🔴 自動重試執行失敗: {str(e)}",
                    )
                except Exception:
                    pass

    # Cleanup
    if cleanup_stale:
        try:
            cleanup_service = DataCleanupService(db=db)
            cleanup_result = await cleanup_service.run_full_cleanup(dry_run=False)

            result["cleanup"] = {
                category: {
                    "found": batch.total_found,
                    "processed": batch.total_processed,
                    "successful": batch.successful,
                }
                for category, batch in cleanup_result.items()
            }

            total_cleaned = sum(
                batch.successful for batch in cleanup_result.values()
            )
            result["total_fixed"] += total_cleaned

            logger.info(f"Cleanup complete: {total_cleaned} items cleaned")

        except Exception as e:
            logger.error(f"Cleanup failed: {e}", exc_info=True)
            result["cleanup"] = {"error": str(e)}

            if notify_on_failure:
                try:
                    notification_service = NotificationService()
                    await notification_service.send_slack_message(
                        channel=channel_id,
                        text=f"🔴 資料清理執行失敗: {str(e)}",
                    )
                except Exception:
                    pass

    # Send success notification if requested and something was fixed
    if notify_on_success and result["total_fixed"] > 0:
        try:
            notification_service = NotificationService()

            retry_info = result.get("retry", {})
            cleanup_info = result.get("cleanup", {})

            message_parts = ["🔄 *自動修復完成*"]

            if retry_info and not retry_info.get("error"):
                trans = retry_info.get("transcription", {})
                analysis = retry_info.get("analysis", {})
                message_parts.append(
                    f"• 重試成功: {trans.get('successful', 0)} 件轉錄, "
                    f"{analysis.get('successful', 0)} 件分析"
                )

            if cleanup_info and not cleanup_info.get("error"):
                total_cleaned = sum(
                    cat.get("successful", 0)
                    for cat in cleanup_info.values()
                    if isinstance(cat, dict) and not cat.get("error")
                )
                message_parts.append(f"• 清理: {total_cleaned} 件過期任務")

            await notification_service.send_slack_message(
                channel=channel_id,
                text="\n".join(message_parts),
            )
        except Exception:
            pass

    logger.info(f"Auto remediation complete: {result['total_fixed']} total fixes")
    return result


def run_sync(
    retry_transcriptions: bool = True,
    retry_analyses: bool = True,
    cleanup_stale: bool = True,
    notify_on_success: bool = False,
    notify_on_failure: bool = True,
    alert_channel: Optional[str] = None,
    alert_channel_id: Optional[str] = None,
) -> dict:
    """Synchronous wrapper."""
    return asyncio.run(
        run(
            retry_transcriptions=retry_transcriptions,
            retry_analyses=retry_analyses,
            cleanup_stale=cleanup_stale,
            notify_on_success=notify_on_success,
            notify_on_failure=notify_on_failure,
            alert_channel=alert_channel,
            alert_channel_id=alert_channel_id,
        )
    )


if __name__ == "__main__":
    result = run_sync(notify_on_success=True)
    print(f"Result: {result}")
