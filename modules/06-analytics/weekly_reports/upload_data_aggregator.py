"""
Upload data aggregator for weekly reports.

Queries Firestore and aggregates upload statistics by sales rep.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from google.cloud import firestore

# 台灣時區 (UTC+8)
TW_TZ = timezone(timedelta(hours=8))


def get_time_ranges(report_date: Optional[datetime] = None) -> Dict[str, Tuple[datetime, datetime]]:
    """
    計算 MTD 和 Weekly 時間範圍。

    Firestore 中的 createdAt 以 UTC 儲存，因此：
    - 計算時需要以 UTC+8 為基準
    - 查詢 Firestore 時轉換為 UTC

    Args:
        report_date: 報表基準日期（預設為當前台灣時間）

    Returns:
        {
            'mtd': (start_utc, end_utc),
            'weekly': (start_utc, end_utc),
            'mtd_local': (start_tw, end_tw),
            'weekly_local': (start_tw, end_tw),
        }
    """
    if report_date is None:
        report_date = datetime.now(TW_TZ)
    elif report_date.tzinfo is None:
        # 假設輸入為台灣時間
        report_date = report_date.replace(tzinfo=TW_TZ)

    # MTD: 當月 1 號 00:00 ~ 報表日 23:59:59 (台灣時間)
    mtd_start_tw = report_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    mtd_end_tw = report_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Weekly: 本週一 00:00 ~ 本週日 23:59:59 (台灣時間)
    days_since_monday = report_date.weekday()
    week_start_tw = (report_date - timedelta(days=days_since_monday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_end_tw = (week_start_tw + timedelta(days=6)).replace(
        hour=23, minute=59, second=59, microsecond=999999
    )

    # 轉換為 UTC 用於 Firestore 查詢
    mtd_start_utc = mtd_start_tw.astimezone(timezone.utc)
    mtd_end_utc = mtd_end_tw.astimezone(timezone.utc)
    week_start_utc = week_start_tw.astimezone(timezone.utc)
    week_end_utc = week_end_tw.astimezone(timezone.utc)

    return {
        "mtd": (mtd_start_utc, mtd_end_utc),
        "weekly": (week_start_utc, week_end_utc),
        "mtd_local": (mtd_start_tw, mtd_end_tw),
        "weekly_local": (week_start_tw, week_end_tw),
    }


class UploadDataAggregator:
    """聚合音檔上傳資料。"""

    COLLECTION = "cases"

    def __init__(self, db: Optional[firestore.Client] = None):
        self.db = db or firestore.Client()

    def get_mtd_cases(self, mtd_start: datetime, mtd_end: datetime) -> List[Dict[str, Any]]:
        """
        查詢 MTD 期間的所有 cases。

        Args:
            mtd_start: MTD 開始時間 (UTC)
            mtd_end: MTD 結束時間 (UTC)

        Returns:
            List of case documents
        """
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = (
            self.db.collection(self.COLLECTION)
            .where(filter=FieldFilter("createdAt", ">=", mtd_start))
            .where(filter=FieldFilter("createdAt", "<=", mtd_end))
            .order_by("createdAt", direction=firestore.Query.DESCENDING)
        )

        docs = query.stream()
        cases = []
        for doc in docs:
            data = doc.to_dict()
            data["caseId"] = doc.id
            cases.append(data)

        return cases

    def aggregate_by_rep(
        self,
        cases: List[Dict[str, Any]],
        week_start: datetime,
        week_end: datetime,
    ) -> List[Dict[str, Any]]:
        """
        依業務聚合資料。

        Args:
            cases: MTD 期間的 case 列表
            week_start: 本週開始時間 (UTC)
            week_end: 本週結束時間 (UTC)

        Returns:
            List of rep stats dictionaries
        """
        rep_data: Dict[str, Dict[str, Any]] = {}

        for case in cases:
            # 取得業務名稱（優先 uploadedByName）
            rep_name = (
                case.get("uploadedByName") or case.get("salesRepName") or "未知業務"
            )

            if rep_name not in rep_data:
                rep_data[rep_name] = {
                    "rep_name": rep_name,
                    "mtd_cases": [],
                    "weekly_cases": [],
                    "customer_details": [],
                }

            created_at = case.get("createdAt")
            if not created_at:
                continue

            # 處理 Firestore datetime (已含時區資訊 UTC)
            if hasattr(created_at, "tzinfo") and created_at.tzinfo is not None:
                # 已經是 timezone-aware datetime
                created_at_utc = created_at
            elif hasattr(created_at, "seconds"):
                # Firestore Timestamp 物件
                created_at_utc = datetime.fromtimestamp(
                    created_at.seconds, tz=timezone.utc
                )
            else:
                # 假設為 UTC
                created_at_utc = created_at.replace(tzinfo=timezone.utc)

            # 轉換為台灣時間用於顯示
            created_at_tw = created_at_utc.astimezone(TW_TZ)

            # MTD 計算（所有查詢結果都在 MTD 範圍內）
            rep_data[rep_name]["mtd_cases"].append(case)

            # 客戶明細
            customer_id = case.get("customerId", "")
            if customer_id:
                rep_data[rep_name]["customer_details"].append(
                    {
                        "customer_id": customer_id,
                        "customer_name": case.get("customerName", "未命名"),
                        "case_id": case.get("caseId"),
                        "created_at": created_at_tw,  # 使用台灣時間
                    }
                )

            # Weekly 計算（比較 UTC 時間）
            if week_start <= created_at_utc <= week_end:
                rep_data[rep_name]["weekly_cases"].append(case)

        # 轉換並排序結果
        results = []
        for rep_name, data in rep_data.items():
            results.append(
                {
                    "rep_name": rep_name,
                    "mtd_upload_count": len(data["mtd_cases"]),
                    "weekly_upload_count": len(data["weekly_cases"]),
                    "customer_details": sorted(
                        data["customer_details"],
                        key=lambda x: x["created_at"],
                        reverse=True,
                    ),
                }
            )

        # 依 MTD 上傳數降序排序
        results.sort(key=lambda x: x["mtd_upload_count"], reverse=True)

        return results

    def generate_report_data(
        self,
        report_date: Optional[datetime] = None,
        include_focus_customers: bool = True,
        focus_top_n: int = 10,
    ) -> Dict[str, Any]:
        """
        生成完整報表資料。

        Args:
            report_date: 報表基準日期
            include_focus_customers: 是否包含關注客戶
            focus_top_n: 關注客戶數量

        Returns:
            Report data dictionary
        """
        ranges = get_time_ranges(report_date)
        mtd_range = ranges["mtd"]
        weekly_range = ranges["weekly"]
        mtd_local = ranges["mtd_local"]
        weekly_local = ranges["weekly_local"]

        # 查詢 MTD cases
        cases = self.get_mtd_cases(mtd_range[0], mtd_range[1])

        # 聚合資料
        by_rep = self.aggregate_by_rep(cases, weekly_range[0], weekly_range[1])

        # 計算總數
        mtd_total = sum(r["mtd_upload_count"] for r in by_rep)
        weekly_total = sum(r["weekly_upload_count"] for r in by_rep)

        result = {
            "report_date": (report_date or datetime.now(TW_TZ)).isoformat(),
            "mtd_start": mtd_local[0].isoformat(),
            "mtd_end": mtd_local[1].isoformat(),
            "week_start": weekly_local[0].isoformat(),
            "week_end": weekly_local[1].isoformat(),
            "mtd_total_uploads": mtd_total,
            "weekly_total_uploads": weekly_total,
            "by_rep": by_rep,
            "generated_at": datetime.now(TW_TZ).isoformat(),
        }

        # 提取關注客戶
        if include_focus_customers:
            try:
                from .focus_customer_aggregator import FocusCustomerAggregator
            except ImportError:
                # Fallback for dynamic module loading (e.g., test scripts)
                from focus_customer_aggregator import FocusCustomerAggregator

            focus_aggregator = FocusCustomerAggregator()
            focus_customers = focus_aggregator.get_focus_customers(
                cases, top_n=focus_top_n
            )
            result["focus_customers"] = [fc.to_dict() for fc in focus_customers]

        return result
