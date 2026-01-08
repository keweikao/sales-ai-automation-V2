"""
Slack Block Kit formatter for weekly upload reports.

Formats report data into Slack-compatible message blocks.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


class UploadReportSlackFormatter:
    """格式化週報表為 Slack Block Kit 格式。"""

    def format_report(
        self,
        data: Dict[str, Any],
        report_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        將報表資料格式化為 Slack message。

        Args:
            data: Report data dictionary
            report_url: Optional URL to full report page

        Returns:
            {
                'text': str,       # Fallback text
                'blocks': List     # Block Kit blocks
            }
        """
        blocks = []

        # Header
        blocks.append(self._build_header(data))
        blocks.append({"type": "divider"})

        # Summary Section
        blocks.append(self._build_summary(data))
        blocks.append({"type": "divider"})

        # Per-Rep Breakdown
        blocks.extend(self._build_rep_breakdown(data))

        # Focus Customers Section (if available)
        focus_customers = data.get("focus_customers", [])
        if focus_customers:
            blocks.extend(self._build_focus_customers_section(focus_customers, report_url))

        # Report Link (if provided)
        if report_url:
            blocks.append({"type": "divider"})
            blocks.append(self._build_report_link(report_url))

        # Footer
        blocks.append(self._build_footer(data))

        return {
            "text": f"📊 音檔上傳週報 - MTD 共 {data['mtd_total_uploads']} 筆",
            "blocks": blocks,
        }

    def _build_header(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """建立報表標題。"""
        mtd_start = self._parse_datetime(data["mtd_start"])
        return {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📊 音檔上傳週報 ({mtd_start.strftime('%Y/%m')})",
                "emoji": True,
            },
        }

    def _build_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """建立摘要區塊。"""
        week_start = self._parse_datetime(data["week_start"])
        week_end = self._parse_datetime(data["week_end"])

        return {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*📅 MTD 上傳總數:*\n`{data['mtd_total_uploads']}` 筆",
                },
                {
                    "type": "mrkdwn",
                    "text": (
                        f"*📆 本週上傳 ({week_start.strftime('%m/%d')}-"
                        f"{week_end.strftime('%m/%d')}):*\n"
                        f"`{data['weekly_total_uploads']}` 筆"
                    ),
                },
            ],
        }

    def _build_rep_breakdown(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """建立各業務統計區塊。"""
        blocks: List[Dict[str, Any]] = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*👥 各業務上傳統計*"},
            }
        ]

        # 建立業務排行
        rep_lines = []
        for i, rep in enumerate(data["by_rep"], 1):
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            else:
                medal = f"{i}."

            rep_lines.append(
                f"{medal} *{rep['rep_name']}*: "
                f"MTD `{rep['mtd_upload_count']}` / "
                f"本週 `{rep['weekly_upload_count']}`"
            )

        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "\n".join(rep_lines) if rep_lines else "_暫無資料_",
                },
            }
        )

        return blocks

    def _build_report_link(self, report_url: str) -> Dict[str, Any]:
        """建立完整報表連結區塊。"""
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*📋 MTD 客戶上傳明細*\n<{report_url}|📄 點擊查看完整報表>",
            },
        }

    def _build_footer(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """建立頁尾。"""
        generated = self._parse_datetime(data["generated_at"])

        return {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        f"🤖 自動產生於 {generated.strftime('%Y-%m-%d %H:%M')} "
                        f"| Sales AI Automation"
                    ),
                }
            ],
        }

    def _build_focus_customers_section(
        self,
        focus_customers: List[Dict[str, Any]],
        report_url: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """建立關注客戶區塊（Slack 摘要版）。"""
        blocks: List[Dict[str, Any]] = [
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*🎯 本週關注客戶*"},
            },
        ]

        # 顯示前 3 名
        for i, customer in enumerate(focus_customers[:3], 1):
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            else:
                medal = "🥉"

            # 取得客戶資訊
            customer_name = customer.get("customer_name", "未命名")
            rep_name = customer.get("rep_name", "未知業務")
            meddic_score = customer.get("meddic_score", 0)
            urgency_level = customer.get("urgency_level", "未知")
            executive_summary = customer.get("executive_summary", "")

            # 截斷摘要
            summary_preview = executive_summary[:80] if executive_summary else "無摘要"
            if len(executive_summary) > 80:
                summary_preview += "..."

            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"{medal} *{customer_name}* ({rep_name})\n"
                            f"MEDDIC: `{meddic_score}` | 急迫性: {urgency_level}\n"
                            f"_{summary_preview}_"
                        ),
                    },
                }
            )

        # 完整報表連結（如果有更多客戶）
        if len(focus_customers) > 3 and report_url:
            remaining = len(focus_customers) - 3
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"還有 {remaining} 位關注客戶，<{report_url}#focus|點擊查看完整報表>",
                        }
                    ],
                }
            )

        return blocks

    def _parse_datetime(self, value: Any) -> datetime:
        """解析 datetime 值。"""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            # 處理 ISO format
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        raise ValueError(f"Cannot parse datetime from {type(value)}: {value}")
