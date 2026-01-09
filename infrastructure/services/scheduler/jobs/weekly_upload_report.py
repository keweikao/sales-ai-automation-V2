"""
Weekly upload report job.

Generates and sends weekly audio upload statistics to Slack.
"""

import importlib.util
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from google.cloud import firestore

# Handle module path with hyphens by using dynamic import
_project_root = Path(__file__).resolve().parents[4]


def _load_module(name: str, relative_path: str):
    """Dynamically load a module from a path with hyphens."""
    full_path = _project_root / relative_path
    spec = importlib.util.spec_from_file_location(name, full_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Load modules with hyphenated paths
_aggregator_module = _load_module(
    "upload_data_aggregator",
    "modules/06-analytics/weekly_reports/upload_data_aggregator.py",
)
_formatter_module = _load_module(
    "upload_slack_formatter",
    "modules/06-analytics/weekly_reports/upload_slack_formatter.py",
)

UploadDataAggregator = _aggregator_module.UploadDataAggregator
UploadReportSlackFormatter = _formatter_module.UploadReportSlackFormatter

from infrastructure.services.notification.channels.slack.sender import SlackSender  # noqa: E402

logger = logging.getLogger(__name__)

# 目標 Slack 頻道
TARGET_CHANNEL = "C0A4F762FE0"

# Web service URL for reports
WEB_SERVICE_URL = os.environ.get(
    "WEB_SERVICE_URL", "https://sales-web-service-497329205771.asia-east1.run.app"
)


async def send_weekly_upload_report(
    report_date: Optional[datetime] = None,
    channel: str = TARGET_CHANNEL,
    dry_run: bool = False,
) -> dict:
    """
    生成並發送每週音檔上傳報表。

    Args:
        report_date: 報表基準日期 (預設為當天)
        channel: Slack 頻道 ID
        dry_run: 若為 True，只生成報表不發送

    Returns:
        執行結果 dictionary
    """
    logger.info("Starting weekly upload report generation...")

    try:
        # 1. 聚合資料
        aggregator = UploadDataAggregator()
        report_data = aggregator.generate_report_data(report_date)

        logger.info(
            f"Report generated: MTD={report_data['mtd_total_uploads']}, "
            f"Weekly={report_data['weekly_total_uploads']}, "
            f"Reps={len(report_data['by_rep'])}"
        )

        # 2. 儲存報表到 Firestore 並取得 URL
        report_url = None
        if not dry_run:
            report_id = _save_report_to_firestore(report_data)
            report_url = f"{WEB_SERVICE_URL}/report/upload/{report_id}"
            logger.info(f"Report saved with ID: {report_id}")

        # 3. 格式化為 Slack 訊息
        formatter = UploadReportSlackFormatter()
        message = formatter.format_report(report_data, report_url=report_url)

        # 4. 發送到 Slack
        if dry_run:
            logger.info("Dry run mode - skipping Slack send")
            return {
                "status": "dry_run",
                "report_data": report_data,
                "message": message,
            }

        slack_token = os.environ.get("SLACK_BOT_TOKEN")
        if not slack_token:
            raise ValueError("SLACK_BOT_TOKEN not configured")

        sender = SlackSender(bot_token=slack_token)
        response = await sender.send_message(
            channel=channel,
            text=message["text"],
            blocks=message["blocks"],
        )

        logger.info(f"Report sent to Slack channel {channel}")

        return {
            "status": "success",
            "channel": channel,
            "message_ts": response.get("ts"),
            "report_url": report_url,
            "report_data": report_data,
        }

    except Exception as e:
        logger.exception(f"Failed to send weekly upload report: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


def _save_report_to_firestore(report_data: dict) -> str:
    """
    儲存報表資料到 Firestore。

    Args:
        report_data: Report data dictionary

    Returns:
        Document ID
    """
    db = firestore.Client()
    doc_ref = db.collection("upload_reports").document()

    # 準備儲存的資料（需要序列化 datetime）
    save_data = _serialize_for_firestore(report_data)
    save_data["created_at"] = firestore.SERVER_TIMESTAMP

    doc_ref.set(save_data)
    return doc_ref.id


def _serialize_for_firestore(data: dict) -> dict:
    """
    序列化資料以便儲存到 Firestore。

    將 datetime 物件轉換為 ISO 字串。
    """
    result = {}
    for key, value in data.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            result[key] = _serialize_for_firestore(value)
        elif isinstance(value, list):
            result[key] = [
                _serialize_for_firestore(item) if isinstance(item, dict) else
                item.isoformat() if isinstance(item, datetime) else item
                for item in value
            ]
        else:
            result[key] = value
    return result
