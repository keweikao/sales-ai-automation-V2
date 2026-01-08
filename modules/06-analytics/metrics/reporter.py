"""
Metrics reporter for generating service value reports.

Queries Firestore and generates reports for different time periods.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from google.cloud import firestore

logger = logging.getLogger(__name__)


@dataclass
class PeriodReport:
    """Report data for a specific time period."""

    # Period info
    period_start: str
    period_end: str
    generated_at: str

    # Volume metrics
    total_cases: int = 0
    completed_cases: int = 0
    failed_cases: int = 0
    in_progress_cases: int = 0

    # Success rate
    success_rate_percent: float = 0.0

    # Processing time (seconds)
    avg_transcription_seconds: float = 0.0
    avg_analysis_seconds: float = 0.0
    avg_total_processing_seconds: float = 0.0
    min_total_processing_seconds: float = 0.0
    max_total_processing_seconds: float = 0.0

    # Audio stats
    total_audio_minutes: float = 0.0
    avg_audio_minutes: float = 0.0

    # Engagement
    total_summary_views: int = 0
    cases_with_views: int = 0
    view_rate_percent: float = 0.0

    # Time saved calculation
    manual_minutes_per_case: float = 45.0  # Baseline: 45 min manual analysis
    ai_review_minutes_per_case: float = 5.0  # Time to review AI output
    estimated_time_saved_hours: float = 0.0
    estimated_fte_equivalent: float = 0.0

    # Cost estimate (USD)
    estimated_cost_usd: float = 0.0
    cost_per_case_usd: float = 0.0

    # By sales rep breakdown
    by_sales_rep: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.by_sales_rep is None:
            self.by_sales_rep = []


class MetricsReporter:
    """
    Generates metrics reports from Firestore data.
    """

    # Cost estimates per 1M tokens (USD)
    GROQ_WHISPER_COST_PER_HOUR = 0.111  # $0.111 per audio hour
    GEMINI_FLASH_COST_PER_1M_INPUT = 0.075
    GEMINI_FLASH_COST_PER_1M_OUTPUT = 0.30

    # Average tokens per case (estimated)
    AVG_INPUT_TOKENS_PER_CASE = 15000
    AVG_OUTPUT_TOKENS_PER_CASE = 5000

    def __init__(self, db: Optional[firestore.Client] = None, project_id: str = None):
        self.db = db or firestore.Client(project=project_id)

    def generate_period_report(
        self,
        start_date: datetime,
        end_date: datetime,
        manual_minutes_per_case: float = 45.0,
    ) -> PeriodReport:
        """
        Generate a report for a specific time period.

        Args:
            start_date: Start of the period (inclusive)
            end_date: End of the period (inclusive)
            manual_minutes_per_case: Baseline manual analysis time

        Returns:
            PeriodReport with aggregated metrics
        """
        # Ensure timezone aware
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        # Query cases in the period
        cases_ref = self.db.collection("cases")
        query = (
            cases_ref
            .where("createdAt", ">=", start_date)
            .where("createdAt", "<=", end_date)
        )

        cases = list(query.stream())
        logger.info(f"Found {len(cases)} cases between {start_date} and {end_date}")

        # Initialize report
        report = PeriodReport(
            period_start=start_date.isoformat(),
            period_end=end_date.isoformat(),
            generated_at=datetime.now(timezone.utc).isoformat(),
            manual_minutes_per_case=manual_minutes_per_case,
        )

        if not cases:
            return report

        # Aggregate metrics
        transcription_times = []
        analysis_times = []
        total_times = []
        audio_durations = []
        by_rep = {}

        for case_doc in cases:
            data = case_doc.to_dict() or {}
            report.total_cases += 1

            status = data.get("status", "unknown")
            if status == "completed" or status == "analyzed":
                report.completed_cases += 1
            elif status == "failed" or status == "error":
                report.failed_cases += 1
            else:
                report.in_progress_cases += 1

            # Metrics data
            metrics = data.get("metrics", {})
            durations = metrics.get("durations", {})
            audio = metrics.get("audio", {})
            delivery = data.get("delivery", {})

            # Processing times
            if durations.get("transcriptionSeconds"):
                transcription_times.append(durations["transcriptionSeconds"])
            if durations.get("analysisSeconds"):
                analysis_times.append(durations["analysisSeconds"])
            if durations.get("totalProcessingSeconds"):
                total_times.append(durations["totalProcessingSeconds"])

            # Audio duration
            if audio.get("durationSeconds"):
                audio_durations.append(audio["durationSeconds"])

            # Engagement
            view_count = delivery.get("viewCount", 0)
            if view_count > 0:
                report.total_summary_views += view_count
                report.cases_with_views += 1

            # By sales rep
            rep_name = data.get("salesRepName") or data.get("uploadedByName") or "Unknown"
            if rep_name not in by_rep:
                by_rep[rep_name] = {"name": rep_name, "count": 0, "completed": 0}
            by_rep[rep_name]["count"] += 1
            if status in ("completed", "analyzed"):
                by_rep[rep_name]["completed"] += 1

        # Calculate averages
        if report.completed_cases > 0:
            report.success_rate_percent = (report.completed_cases / report.total_cases) * 100

        if transcription_times:
            report.avg_transcription_seconds = sum(transcription_times) / len(transcription_times)

        if analysis_times:
            report.avg_analysis_seconds = sum(analysis_times) / len(analysis_times)

        if total_times:
            report.avg_total_processing_seconds = sum(total_times) / len(total_times)
            report.min_total_processing_seconds = min(total_times)
            report.max_total_processing_seconds = max(total_times)

        if audio_durations:
            report.total_audio_minutes = sum(audio_durations) / 60
            report.avg_audio_minutes = report.total_audio_minutes / len(audio_durations)

        if report.total_cases > 0:
            report.view_rate_percent = (report.cases_with_views / report.total_cases) * 100

        # Time saved calculation
        if report.completed_cases > 0:
            # Manual: 45 min per case
            manual_total = report.completed_cases * manual_minutes_per_case

            # AI: processing time + review time
            ai_total = report.completed_cases * (
                report.avg_total_processing_seconds / 60 + report.ai_review_minutes_per_case
            )

            saved_minutes = manual_total - ai_total
            report.estimated_time_saved_hours = saved_minutes / 60
            report.estimated_fte_equivalent = report.estimated_time_saved_hours / 160  # 160 hr/month

        # Cost calculation
        if report.completed_cases > 0:
            # Transcription cost (Groq Whisper)
            transcription_cost = (report.total_audio_minutes / 60) * self.GROQ_WHISPER_COST_PER_HOUR

            # Analysis cost (Gemini Flash)
            input_cost = (report.completed_cases * self.AVG_INPUT_TOKENS_PER_CASE / 1_000_000) * self.GEMINI_FLASH_COST_PER_1M_INPUT
            output_cost = (report.completed_cases * self.AVG_OUTPUT_TOKENS_PER_CASE / 1_000_000) * self.GEMINI_FLASH_COST_PER_1M_OUTPUT

            report.estimated_cost_usd = transcription_cost + input_cost + output_cost
            report.cost_per_case_usd = report.estimated_cost_usd / report.completed_cases

        # By sales rep
        report.by_sales_rep = sorted(by_rep.values(), key=lambda x: x["count"], reverse=True)

        return report

    def generate_weekly_report(self, weeks_ago: int = 0) -> PeriodReport:
        """Generate report for a specific week."""
        today = datetime.now(timezone.utc)
        # Get Monday of the target week
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)
        target_monday = this_monday - timedelta(weeks=weeks_ago)

        start_date = target_monday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)

        return self.generate_period_report(start_date, end_date)

    def generate_monthly_report(self, year: int = None, month: int = None) -> PeriodReport:
        """Generate report for a specific month."""
        today = datetime.now(timezone.utc)
        if year is None:
            year = today.year
        if month is None:
            month = today.month

        start_date = datetime(year, month, 1, tzinfo=timezone.utc)

        # Get last day of month
        if month == 12:
            end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
        else:
            end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)

        return self.generate_period_report(start_date, end_date)

    def format_report_text(self, report: PeriodReport) -> str:
        """Format report as human-readable text."""
        lines = [
            "=" * 60,
            "Sales AI Automation - 服務價值報告",
            "=" * 60,
            f"報告期間: {report.period_start[:10]} ~ {report.period_end[:10]}",
            f"產生時間: {report.generated_at[:19]}",
            "",
            "📊 處理量",
            "-" * 40,
            f"  總案件數:     {report.total_cases}",
            f"  已完成:       {report.completed_cases}",
            f"  失敗:         {report.failed_cases}",
            f"  處理中:       {report.in_progress_cases}",
            f"  成功率:       {report.success_rate_percent:.1f}%",
            "",
            "⏱️ 處理效率",
            "-" * 40,
            f"  平均轉錄時間:   {report.avg_transcription_seconds:.1f} 秒",
            f"  平均分析時間:   {report.avg_analysis_seconds:.1f} 秒",
            f"  平均總處理時間: {report.avg_total_processing_seconds:.1f} 秒",
            "",
            "🎵 音檔統計",
            "-" * 40,
            f"  總音檔長度:   {report.total_audio_minutes:.1f} 分鐘",
            f"  平均音檔長度: {report.avg_audio_minutes:.1f} 分鐘",
            "",
            "👁️ 使用情況",
            "-" * 40,
            f"  摘要總瀏覽次數: {report.total_summary_views}",
            f"  有被瀏覽的案件: {report.cases_with_views}",
            f"  瀏覽率:         {report.view_rate_percent:.1f}%",
            "",
            "💡 節省時間估算",
            "-" * 40,
            f"  基準假設: 人工分析每通電話 {report.manual_minutes_per_case:.0f} 分鐘",
            f"  AI 處理 + 主管審閱: {report.avg_total_processing_seconds/60 + report.ai_review_minutes_per_case:.1f} 分鐘/通",
            f"  估計節省時間: {report.estimated_time_saved_hours:.1f} 小時",
            f"  相當於 FTE:   {report.estimated_fte_equivalent:.2f} 人",
            "",
            "💰 成本估算",
            "-" * 40,
            f"  總成本:     ${report.estimated_cost_usd:.2f} USD",
            f"  每通成本:   ${report.cost_per_case_usd:.4f} USD",
            "",
        ]

        if report.by_sales_rep:
            lines.extend([
                "👥 各業務使用情況",
                "-" * 40,
            ])
            for rep in report.by_sales_rep[:10]:  # Top 10
                lines.append(f"  {rep['name']}: {rep['count']} 通 ({rep['completed']} 完成)")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

    def format_report_json(self, report: PeriodReport) -> str:
        """Format report as JSON."""
        return json.dumps(asdict(report), indent=2, ensure_ascii=False)

    def format_report_markdown(self, report: PeriodReport) -> str:
        """Format report as Markdown for easy sharing."""
        return f"""# Sales AI Automation 服務價值報告

**報告期間**: {report.period_start[:10]} ~ {report.period_end[:10]}
**產生時間**: {report.generated_at[:19]}

---

## 📊 本期關鍵數字

| 指標 | 數值 |
|-----|------|
| 處理通話數 | **{report.completed_cases}** |
| 成功率 | **{report.success_rate_percent:.1f}%** |
| 平均處理時間 | **{report.avg_total_processing_seconds:.0f} 秒** |
| 節省時間 | **{report.estimated_time_saved_hours:.0f} 小時** |

---

## 💡 價值說明

**Before (人工分析)**:
- 每通電話需要 {report.manual_minutes_per_case:.0f} 分鐘（聽錄音 + 筆記 + 回饋）
- {report.completed_cases} 通 × {report.manual_minutes_per_case:.0f} 分鐘 = {report.completed_cases * report.manual_minutes_per_case / 60:.0f} 小時

**After (AI 自動化)**:
- AI 處理: {report.avg_total_processing_seconds:.0f} 秒
- 主管審閱: {report.ai_review_minutes_per_case:.0f} 分鐘
- {report.completed_cases} 通 × {(report.avg_total_processing_seconds/60 + report.ai_review_minutes_per_case):.1f} 分鐘 = {report.completed_cases * (report.avg_total_processing_seconds/60 + report.ai_review_minutes_per_case) / 60:.0f} 小時

**節省時間**: {report.estimated_time_saved_hours:.0f} 小時 ≈ **{report.estimated_fte_equivalent:.1f} FTE**

---

## 💰 成本效益

| 項目 | 金額 |
|-----|------|
| 本期總成本 | ${report.estimated_cost_usd:.2f} USD |
| 每通成本 | ${report.cost_per_case_usd:.4f} USD |

---

## 👥 各業務使用情況

| 業務 | 通話數 | 完成數 |
|-----|-------|-------|
""" + "\n".join([f"| {rep['name']} | {rep['count']} | {rep['completed']} |" for rep in report.by_sales_rep[:10]]) + """

---

## 📈 摘要瀏覽統計

- 總瀏覽次數: {report.total_summary_views}
- 有被瀏覽的案件: {report.cases_with_views}
- 瀏覽率: {report.view_rate_percent:.1f}%

---

*報告自動產生於 {report.generated_at[:19]}*
"""
