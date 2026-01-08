#!/usr/bin/env python3
"""
Test script for weekly upload report.

Run this via Cloud Build to test the Slack integration.

Usage:
  # Default channel (C0A4F762FE0)
  python tools/test_weekly_upload_report.py

  # Specify channel
  python tools/test_weekly_upload_report.py C08XXXXXXXX
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

# Dynamic imports for hyphenated directories
import importlib.util

# Default target channel
DEFAULT_CHANNEL = "C0A4F762FE0"

# Web service URL
WEB_SERVICE_URL = "https://summary-web-service-497329205771.asia-east1.run.app"


def load_module(name: str, relative_path: str):
    """Dynamically load a module from a path with hyphens."""
    full_path = project_root / relative_path
    spec = importlib.util.spec_from_file_location(name, full_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _serialize_for_firestore(data: dict) -> dict:
    """Serialize data for Firestore storage."""
    from datetime import datetime

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


async def main():
    """Run the weekly upload report test."""
    print("=" * 60)
    print("Weekly Upload Report Test")
    print("=" * 60)

    # Get target channel from args or environment
    target_channel = DEFAULT_CHANNEL
    if len(sys.argv) > 1:
        target_channel = sys.argv[1]
    elif os.environ.get("TARGET_CHANNEL"):
        target_channel = os.environ.get("TARGET_CHANNEL")

    print(f"Target Channel: {target_channel}")

    # Check environment
    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    if not slack_token:
        print("ERROR: SLACK_BOT_TOKEN not set")
        sys.exit(1)

    print(f"SLACK_BOT_TOKEN: {slack_token[:10]}...{slack_token[-4:]}")

    # Load modules
    print("\nLoading modules...")

    # Load focus customer modules first (dependencies)
    load_module(
        "focus_customer_models",
        "modules/06-analytics/weekly_reports/focus_customer_models.py",
    )
    load_module(
        "focus_customer_aggregator",
        "modules/06-analytics/weekly_reports/focus_customer_aggregator.py",
    )

    aggregator_module = load_module(
        "upload_data_aggregator",
        "modules/06-analytics/weekly_reports/upload_data_aggregator.py",
    )
    formatter_module = load_module(
        "upload_slack_formatter",
        "modules/06-analytics/weekly_reports/upload_slack_formatter.py",
    )

    UploadDataAggregator = aggregator_module.UploadDataAggregator
    UploadReportSlackFormatter = formatter_module.UploadReportSlackFormatter

    # Import Slack sender and Firestore
    from infrastructure.services.notification.channels.slack.sender import SlackSender
    from google.cloud import firestore
    from datetime import datetime

    print("Modules loaded successfully")

    # Generate report
    print("\nGenerating report data...")
    aggregator = UploadDataAggregator()
    report_data = aggregator.generate_report_data()

    print(f"  MTD Total: {report_data['mtd_total_uploads']}")
    print(f"  Weekly Total: {report_data['weekly_total_uploads']}")
    print(f"  Sales Reps: {len(report_data['by_rep'])}")
    focus_customers = report_data.get('focus_customers', [])
    print(f"  Focus Customers: {len(focus_customers)}")
    for fc in focus_customers[:3]:
        print(f"    - {fc['customer_name']} (MEDDIC: {fc['meddic_score']})")

    # Save report to Firestore
    print("\nSaving report to Firestore...")
    db = firestore.Client()
    doc_ref = db.collection("upload_reports").document()

    # Serialize datetime objects for Firestore
    save_data = _serialize_for_firestore(report_data)
    save_data["created_at"] = firestore.SERVER_TIMESTAMP
    doc_ref.set(save_data)

    report_id = doc_ref.id
    report_url = f"{WEB_SERVICE_URL}/report/upload/{report_id}"
    print(f"  Report ID: {report_id}")
    print(f"  Report URL: {report_url}")

    # Format message with report URL
    print("\nFormatting Slack message...")
    formatter = UploadReportSlackFormatter()
    message = formatter.format_report(report_data, report_url=report_url)

    print(f"  Text preview: {message['text'][:100]}...")
    print(f"  Blocks count: {len(message['blocks'])}")

    # Send to Slack
    print(f"\nSending to Slack channel: {target_channel}")

    sender = SlackSender(bot_token=slack_token)
    response = await sender.send_message(
        channel=target_channel,
        text=message["text"],
        blocks=message["blocks"],
    )

    print(f"  Response: {json.dumps(response, indent=2)}")

    if response.get("ok"):
        print("\n✅ SUCCESS: Report sent to Slack!")
        print(f"   Message TS: {response.get('ts')}")
        print(f"   Channel: {response.get('channel')}")
    else:
        print(f"\n❌ FAILED: {response.get('error')}")
        sys.exit(1)

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
