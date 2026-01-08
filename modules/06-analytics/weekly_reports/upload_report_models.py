"""
Upload report data models.

Defines data structures for weekly audio upload statistics reports.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class CustomerUploadDetail:
    """單筆客戶上傳記錄"""

    customer_id: str  # 客戶編號 (202601-000001)
    customer_name: str  # 客戶名稱
    case_id: str  # 案件 ID
    created_at: datetime  # 上傳時間 (UTC+8)


@dataclass
class SalesRepUploadStats:
    """單一業務的上傳統計"""

    rep_name: str
    mtd_upload_count: int
    weekly_upload_count: int
    customer_details: List[CustomerUploadDetail] = field(default_factory=list)


@dataclass
class WeeklyUploadReportData:
    """週報表完整資料"""

    report_date: datetime  # 報表基準日期 (UTC+8)
    mtd_start: datetime  # MTD 起始日 (UTC+8)
    mtd_end: datetime  # MTD 結束日 (UTC+8)
    week_start: datetime  # 本週起始日 (UTC+8)
    week_end: datetime  # 本週結束日 (UTC+8)
    mtd_total_uploads: int  # MTD 上傳總數
    weekly_total_uploads: int  # 本週上傳總數
    by_rep: List[SalesRepUploadStats] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)
    report_url: Optional[str] = None  # 完整報表網頁 URL
