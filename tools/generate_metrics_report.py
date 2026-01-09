#!/usr/bin/env python3
"""
Generate service value metrics report.

Usage:
    # This week's report
    python tools/generate_metrics_report.py

    # Last week's report
    python tools/generate_metrics_report.py --week -1

    # This month's report
    python tools/generate_metrics_report.py --month

    # Specific month
    python tools/generate_metrics_report.py --month --year 2026 --month-num 1

    # Custom date range
    python tools/generate_metrics_report.py --start 2026-01-01 --end 2026-01-15

    # Output formats
    python tools/generate_metrics_report.py --format json
    python tools/generate_metrics_report.py --format markdown --output report.md
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

# Import from 06-analytics module (has hyphen in name)
import importlib.util  # noqa: E402
metrics_reporter_path = project_root / "modules" / "06-analytics" / "metrics" / "reporter.py"
spec = importlib.util.spec_from_file_location("reporter", metrics_reporter_path)
reporter_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reporter_module)
MetricsReporter = reporter_module.MetricsReporter


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate service value metrics report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Period selection
    period_group = parser.add_mutually_exclusive_group()
    period_group.add_argument(
        "--week",
        type=int,
        default=0,
        help="Generate weekly report. 0=this week, -1=last week, etc. (default: 0)",
    )
    period_group.add_argument(
        "--month",
        action="store_true",
        help="Generate monthly report",
    )
    period_group.add_argument(
        "--start",
        type=str,
        help="Start date for custom range (YYYY-MM-DD)",
    )

    # Month options
    parser.add_argument(
        "--year",
        type=int,
        help="Year for monthly report (default: current year)",
    )
    parser.add_argument(
        "--month-num",
        type=int,
        help="Month number for monthly report (default: current month)",
    )

    # Custom range end
    parser.add_argument(
        "--end",
        type=str,
        help="End date for custom range (YYYY-MM-DD)",
    )

    # Output options
    parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path (default: stdout)",
    )

    # Baseline configuration
    parser.add_argument(
        "--manual-minutes",
        type=float,
        default=45.0,
        help="Baseline manual analysis time per case in minutes (default: 45)",
    )

    # GCP project
    parser.add_argument(
        "--project",
        type=str,
        default="sales-ai-automation-v2",
        help="GCP project ID",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    # Initialize reporter
    reporter = MetricsReporter(project_id=args.project)

    # Generate report based on period selection
    if args.start:
        # Custom date range
        start_date = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if args.end:
            end_date = datetime.strptime(args.end, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
        else:
            end_date = datetime.now(timezone.utc)

        report = reporter.generate_period_report(
            start_date,
            end_date,
            manual_minutes_per_case=args.manual_minutes,
        )
    elif args.month:
        # Monthly report
        report = reporter.generate_monthly_report(
            year=args.year,
            month=args.month_num,
        )
    else:
        # Weekly report (default)
        report = reporter.generate_weekly_report(weeks_ago=abs(args.week))

    # Format output
    if args.format == "json":
        output = reporter.format_report_json(report)
    elif args.format == "markdown":
        output = reporter.format_report_markdown(report)
    else:
        output = reporter.format_report_text(report)

    # Write output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Report saved to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
