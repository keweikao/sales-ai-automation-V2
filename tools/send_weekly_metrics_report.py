#!/usr/bin/env python3
"""
Send weekly metrics report to Slack.

This script generates a service value metrics report and sends it to Slack.
It's designed to run as a scheduled job (GitHub Actions or Cloud Scheduler).

Usage:
    python tools/send_weekly_metrics_report.py

Environment variables:
    SLACK_BOT_TOKEN: Slack bot token for sending messages
    TARGET_CHANNEL: Slack channel ID (default: C0A4F762FE0)
    GOOGLE_CLOUD_PROJECT: GCP project ID
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

# Dynamic import for hyphenated module path
import importlib.util  # noqa: E402


def load_module(name: str, relative_path: str):
    """Dynamically load a module from a path with hyphens."""
    full_path = project_root / relative_path
    spec = importlib.util.spec_from_file_location(name, full_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def format_metrics_slack_blocks(report) -> dict:
    """Format metrics report as Slack Block Kit message."""
    
    # Header
    period_display = f"{report.period_start[:10]} ~ {report.period_end[:10]}"
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📊 Sales AI 週報 - 服務價值報告",
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"報告期間: *{period_display}*"
                }
            ]
        },
        {"type": "divider"},
        
        # Key Metrics Section
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*🎯 本週成果*"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*轉錄語音時數*\n{report.total_audio_minutes / 60:.1f} 小時"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*完成對話分析*\n{report.completed_cases} 通"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*成功率*\n{report.success_rate_percent:.1f}%"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*平均處理時間*\n{report.avg_total_processing_seconds:.0f} 秒"
                }
            ]
        },
        {"type": "divider"},
        
        # Processing Efficiency
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*⏱️ 處理效率*"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*平均轉錄時間*\n{report.avg_transcription_seconds:.1f} 秒"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*平均分析時間*\n{report.avg_analysis_seconds:.1f} 秒"
                }
            ]
        },
        {"type": "divider"},
        
        # Cost Section
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*💰 成本*"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*本週總成本*\n${report.estimated_cost_usd:.2f} USD"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*每通成本*\n${report.cost_per_case_usd:.4f} USD"
                }
            ]
        },
        {"type": "divider"},
        
        # Engagement Section
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*👁️ 摘要使用情況*"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*總瀏覽次數*\n{report.total_summary_views}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*瀏覽率*\n{report.view_rate_percent:.1f}%"
                }
            ]
        },
    ]
    
    # Add top sales reps if available
    if report.by_sales_rep:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*👥 各業務使用情況 (Top 5)*"
            }
        })
        
        rep_text = "\n".join([
            f"• {rep['name']}: {rep['count']} 通 ({rep['completed']} 完成)"
            for rep in report.by_sales_rep[:5]
        ])
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": rep_text
            }
        })
    
    # Footer
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"_報告自動產生於 {report.generated_at[:19]}_"
            }
        ]
    })
    
    return {
        "text": f"📊 Sales AI 週報 ({period_display}) - {report.completed_cases} 通對話分析完成",
        "blocks": blocks
    }


async def main():
    """Generate and send weekly metrics report."""
    print("=" * 60)
    print("Weekly Metrics Report")
    print("=" * 60)
    
    # Get configuration
    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    if not slack_token:
        print("ERROR: SLACK_BOT_TOKEN not set")
        sys.exit(1)
    
    target_channel = os.environ.get("TARGET_CHANNEL", "C0A7C2HUXRR")
    print(f"Target Channel: {target_channel}")
    print(f"SLACK_BOT_TOKEN: {slack_token[:10]}...{slack_token[-4:]}")
    
    # Load metrics reporter
    print("\nLoading metrics reporter...")
    reporter_module = load_module(
        "metrics_reporter",
        "modules/06-analytics/metrics/reporter.py"
    )
    MetricsReporter = reporter_module.MetricsReporter
    
    # Import Slack sender
    from infrastructure.services.notification.channels.slack.sender import SlackSender
    
    print("Modules loaded successfully")
    
    # Generate report
    print("\nGenerating weekly metrics report...")
    reporter = MetricsReporter()
    report = reporter.generate_weekly_report(weeks_ago=0)  # Current week
    
    print(f"  Period: {report.period_start[:10]} ~ {report.period_end[:10]}")
    print(f"  Total Cases: {report.total_cases}")
    print(f"  Completed: {report.completed_cases}")
    print(f"  Success Rate: {report.success_rate_percent:.1f}%")
    print(f"  Audio Minutes: {report.total_audio_minutes:.1f}")
    print(f"  Est. Cost: ${report.estimated_cost_usd:.2f}")
    
    # Format Slack message
    print("\nFormatting Slack message...")
    message = format_metrics_slack_blocks(report)
    print(f"  Text: {message['text']}")
    print(f"  Blocks: {len(message['blocks'])}")
    
    # Send to Slack
    print(f"\nSending to Slack channel: {target_channel}")
    sender = SlackSender(bot_token=slack_token)
    response = await sender.send_message(
        channel=target_channel,
        text=message["text"],
        blocks=message["blocks"],
    )
    
    if response.get("ok"):
        print("\n✅ SUCCESS: Metrics report sent to Slack!")
        print(f"   Message TS: {response.get('ts')}")
        print(f"   Channel: {response.get('channel')}")
    else:
        print(f"\n❌ FAILED: {response.get('error')}")
        sys.exit(1)
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
