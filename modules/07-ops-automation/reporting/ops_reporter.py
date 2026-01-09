"""
Ops Reporter - Generates Slack reports for ops status.

Creates formatted Slack Block Kit messages for:
- Morning/Evening health reports
- Alert notifications
- Weekly summaries
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..agent.orchestrator import OpsRunResult
from ..history import ProcessingStats


class OpsReporter:
    """
    Generates Slack reports for ops status.

    Supports:
    - Health status reports (morning/evening)
    - Alert notifications
    - Weekly summaries
    """

    # Status emoji mapping
    STATUS_EMOJI = {
        "healthy": "🟢",
        "degraded": "🟡",
        "unhealthy": "🔴",
        "unknown": "⚪",
        "critical": "🚨",
        "warning": "⚠️",
    }

    # Period type labels
    PERIOD_LABELS = {
        "morning": "早報",
        "evening": "晚報",
        "scheduled": "定期報告",
    }

    def build_health_report_blocks(
        self,
        run_result: OpsRunResult,
    ) -> List[Dict[str, Any]]:
        """Build Slack blocks for health report."""
        overall_status = run_result.overall_status
        status_emoji = self.STATUS_EMOJI.get(overall_status, "❓")
        period_label = self.PERIOD_LABELS.get(run_result.period_type, "報告")

        # Format date
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

        # AI Analysis section (if available)
        if run_result.analysis:
            analysis_blocks = self._build_analysis_section(run_result.analysis)
            blocks.extend(analysis_blocks)
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

        # Remediation results section
        if run_result.remediation_executed:
            remediation_blocks = self._build_remediation_section(run_result)
            blocks.extend(remediation_blocks)

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
        """Format period text for the report."""
        if run_result.period_start and run_result.period_end:
            start_str = run_result.period_start.strftime("%m/%d %H:%M")
            end_str = run_result.period_end.strftime("%m/%d %H:%M")
            hours = (run_result.period_end - run_result.period_start).total_seconds() / 3600
            return f"*報告區間:* {start_str} → {end_str} ({hours:.0f}h)"
        return ""

    def _build_stats_section(
        self,
        stats: ProcessingStats,
    ) -> List[Dict[str, Any]]:
        """Build processing stats section."""
        # Build table-like text
        lines = [
            "*📊 處理量統計*",
            "```",
            "┌─────────────────┬────────┬─────────┐",
            "│ 階段            │ 數量   │ vs 上週  │",
            "├─────────────────┼────────┼─────────┤",
        ]

        # Add rows
        rows = [
            ("Slack 上傳", stats.slack_uploads, stats.get_comparison("slack_uploads")),
            ("GCS 存放", stats.gcs_files, stats.get_comparison("gcs_files")),
            ("轉錄完成", stats.transcriptions_completed, stats.get_comparison("transcriptions_completed")),
            ("分析完成", stats.analyses_completed, stats.get_comparison("analyses_completed")),
        ]

        for label, count, comparison in rows:
            # Pad label to fixed width
            label_padded = label.ljust(15)
            count_str = str(count).ljust(6)
            comp_str = comparison.ljust(7)
            lines.append(f"│ {label_padded} │ {count_str} │ {comp_str} │")

        lines.append("└─────────────────┴────────┴─────────┘")
        lines.append("```")

        # Success rate
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

    def _build_service_section(
        self,
        health_report: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Build service status section."""
        services = health_report.get("services", {})

        lines = ["*🔧 服務狀態*"]
        for name, status_info in services.items():
            status = status_info.get("status", "unknown")
            emoji = self.STATUS_EMOJI.get(status, "❓")

            # Format latency
            latency = status_info.get("latency_ms")
            latency_str = f" ({latency:.0f}ms)" if latency else ""

            # Format success rate from details
            details = status_info.get("details", {})
            success_rate = details.get("success_rate")
            rate_str = f" - 成功率 {success_rate * 100:.1f}%" if success_rate is not None else ""

            lines.append(f"{emoji} {name}{latency_str}{rate_str}")

        return [{
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(lines),
            }
        }]

    def _build_analysis_section(
        self,
        analysis: Any,
    ) -> List[Dict[str, Any]]:
        """Build AI analysis section."""
        blocks = []

        # Summary
        summary = getattr(analysis, "summary", None) or analysis.get("summary", "")
        if summary:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🤖 AI 分析*\n{summary}",
                }
            })

        return blocks

    def _get_recommendations(
        self,
        run_result: OpsRunResult,
    ) -> List[str]:
        """Generate recommendations based on results."""
        recommendations = []

        # From processing stats
        if run_result.processing_stats:
            stats = run_result.processing_stats

            # Check for failed cases
            if stats.failed_case_ids:
                case_list = ", ".join(stats.failed_case_ids[:3])
                recommendations.append(f"檢查失敗的案件: {case_list}")

            # Check for stuck cases
            if stats.stuck_case_ids:
                case_list = ", ".join(stats.stuck_case_ids[:3])
                recommendations.append(f"追蹤卡住的案件: {case_list}")

            # Check success rate
            if stats.success_rate < 0.9 and stats.transcriptions_completed > 0:
                recommendations.append(
                    f"分析成功率偏低 ({stats.success_rate * 100:.1f}%)，建議檢查分析服務"
                )

        # From health report
        if run_result.health_report:
            services = run_result.health_report.get("services", {})
            for name, status_info in services.items():
                status = status_info.get("status", "")
                if status == "unhealthy":
                    recommendations.append(f"服務 {name} 狀態異常，需要檢查")
                elif status == "degraded":
                    latency = status_info.get("latency_ms", 0)
                    if latency > 1000:
                        recommendations.append(f"服務 {name} 延遲過高 ({latency:.0f}ms)")

        # From LLM analysis
        if run_result.analysis:
            analysis_recs = getattr(run_result.analysis, "recommendations", None)
            if analysis_recs:
                recommendations.extend(analysis_recs[:3])

        return recommendations

    def _build_remediation_section(
        self,
        run_result: OpsRunResult,
    ) -> List[Dict[str, Any]]:
        """Build remediation results section."""
        lines = ["*🔄 自動修復*"]

        # Retry results
        retry = run_result.retry_result or {}
        if not retry.get("error"):
            trans_retry = retry.get("transcription", {})
            analysis_retry = retry.get("analysis", {})
            lines.append(
                f"• 重試成功: {trans_retry.get('successful', 0)} 件轉錄, "
                f"{analysis_retry.get('successful', 0)} 件分析"
            )
        else:
            lines.append(f"• 重試: 執行失敗")

        # Cleanup results
        cleanup = run_result.cleanup_result or {}
        if not cleanup.get("error"):
            total_cleaned = sum(
                cat.get("successful", 0)
                for cat in cleanup.values()
                if isinstance(cat, dict) and not cat.get("error")
            )
            lines.append(f"• 清理: {total_cleaned} 件過期任務")
        else:
            lines.append(f"• 清理: 執行失敗")

        return [{
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(lines),
            }
        }]

    def build_alert_blocks(
        self,
        issue: str,
        severity: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Build Slack blocks for alert notification."""
        severity_emoji = self.STATUS_EMOJI.get(severity, "❓")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{severity_emoji} 運維告警: {severity.upper()}",
                    "emoji": True,
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*問題:*\n{issue}",
                }
            },
        ]

        if details:
            detail_lines = [f"• {k}: {v}" for k, v in details.items()]
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*詳細資訊:*\n```\n{chr(10).join(detail_lines)}\n```",
                }
            })

        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"時間: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
                }
            ]
        })

        return blocks

    def build_weekly_summary_blocks(
        self,
        weekly_summary: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Build Slack blocks for weekly summary."""
        uptime = weekly_summary.get("uptime_percent", 0)
        total_checks = weekly_summary.get("total_checks", 0)

        # Determine overall status emoji based on uptime
        if uptime >= 99:
            status_emoji = "🟢"
        elif uptime >= 95:
            status_emoji = "🟡"
        else:
            status_emoji = "🔴"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji} 週報摘要",
                    "emoji": True,
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*系統可用性:* {uptime:.1f}%\n"
                        f"*總檢查次數:* {total_checks}\n"
                        f"*健康:* {weekly_summary.get('healthy_count', 0)} | "
                        f"*降級:* {weekly_summary.get('degraded_count', 0)} | "
                        f"*異常:* {weekly_summary.get('unhealthy_count', 0)}"
                    ),
                }
            },
        ]

        # Processing totals
        totals = weekly_summary.get("processing_totals", {})
        if totals:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*本週處理量*\n"
                        f"• Slack 上傳: {totals.get('slack_uploads', 0)}\n"
                        f"• 轉錄完成: {totals.get('transcriptions_completed', 0)}\n"
                        f"• 分析完成: {totals.get('analyses_completed', 0)}"
                    ),
                }
            })

        return blocks

    def format_text_report(
        self,
        run_result: OpsRunResult,
    ) -> str:
        """
        Format a plain text report (for logging or fallback).

        Returns a formatted string representation of the report.
        """
        lines = []

        # Header
        period_label = self.PERIOD_LABELS.get(run_result.period_type, "報告")
        status_emoji = self.STATUS_EMOJI.get(run_result.overall_status, "❓")
        date_str = (run_result.completed_at or datetime.now(timezone.utc)).strftime("%Y/%m/%d")

        lines.append(f"{status_emoji} 系統健康報告 - {date_str} {period_label}")
        lines.append("━" * 30)
        lines.append(f"整體狀態: {run_result.overall_status.upper()}")

        # Period
        if run_result.period_start and run_result.period_end:
            start_str = run_result.period_start.strftime("%m/%d %H:%M")
            end_str = run_result.period_end.strftime("%m/%d %H:%M")
            hours = (run_result.period_end - run_result.period_start).total_seconds() / 3600
            lines.append(f"報告區間: {start_str} → {end_str} ({hours:.0f}h)")

        lines.append("")

        # Processing stats
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

        # Footer
        lines.append("━" * 30)
        lines.append(f"Run ID: {run_result.run_id} | 耗時: {run_result.duration_seconds:.1f}s")

        return "\n".join(lines)
