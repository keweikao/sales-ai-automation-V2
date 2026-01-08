"""分析相關 API 路由"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from google.cloud import firestore

from deps.firestore import get_db
from schemas.analytics import (
    AnalyticsTrends,
    DashboardStats,
    PerformerStats,
    WeeklyReportSummary,
)
from services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/analytics/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    db: firestore.Client = Depends(get_db),
):
    """
    取得儀表板統計數據

    返回：
    - 總對話數
    - 今日完成數
    - 平均 MEDDIC 分數
    - 轉換率
    - 表現最佳業務員
    """
    try:
        service = AnalyticsService(db)
        stats = service.get_dashboard_stats()

        return DashboardStats(
            totalConversations=stats["totalConversations"],
            completedToday=stats["completedToday"],
            pendingAnalysis=stats["pendingAnalysis"],
            avgMeddicScore=stats["avgMeddicScore"],
            conversionRate=stats["conversionRate"],
            topPerformers=stats["topPerformers"],
            recentTrend=stats["recentTrend"],
            lastUpdated=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Failed to get dashboard stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get dashboard stats: {str(e)}"
        )


@router.get("/analytics/weekly-report", response_model=WeeklyReportSummary)
async def get_weekly_report(
    week_start: Optional[datetime] = Query(None, description="週開始日期"),
    db: firestore.Client = Depends(get_db),
):
    """
    取得週報摘要

    如果未指定日期，返回上一週的報告。
    """
    try:
        service = AnalyticsService(db)
        report = service.get_weekly_report(week_start)

        if not report:
            # Return empty report structure
            if week_start is None:
                today = datetime.now()
                week_start = today - timedelta(days=today.weekday() + 7)
            week_end = week_start + timedelta(days=6)

            return WeeklyReportSummary(
                periodStart=week_start,
                periodEnd=week_end,
                totalConversations=0,
                totalAnalyzed=0,
                avgMeddicScore=0.0,
                byRep=[],
                insights=[],
                generatedAt=datetime.utcnow(),
            )

        return WeeklyReportSummary(
            periodStart=report["periodStart"],
            periodEnd=report["periodEnd"],
            totalConversations=report["totalConversations"],
            totalAnalyzed=report["totalAnalyzed"],
            avgMeddicScore=report["avgMeddicScore"],
            byRep=report["byRep"],
            insights=report.get("insights", []),
            generatedAt=report.get("generatedAt", datetime.utcnow()),
        )

    except Exception as e:
        logger.error(f"Failed to get weekly report: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get weekly report: {str(e)}"
        )


@router.get("/analytics/trends", response_model=AnalyticsTrends)
async def get_trends(
    period: str = Query("7d", description="期間: 7d, 30d, 90d"),
    db: firestore.Client = Depends(get_db),
):
    """
    取得分析趨勢

    返回指定期間內的對話數量和 MEDDIC 分數趨勢。
    """
    try:
        if period not in ("7d", "30d", "90d"):
            raise HTTPException(
                status_code=400,
                detail="Invalid period. Must be one of: 7d, 30d, 90d",
            )

        service = AnalyticsService(db)
        trends = service.get_trends(period)

        return AnalyticsTrends(
            period=trends["period"],
            data=trends["data"],
            overallTrend=trends["overallTrend"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trends: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get trends: {str(e)}"
        )


@router.get("/analytics/rep/{rep_id}", response_model=PerformerStats)
async def get_rep_stats(
    rep_id: str,
    db: firestore.Client = Depends(get_db),
):
    """
    取得特定業務員的統計數據
    """
    try:
        service = AnalyticsService(db)
        stats = service.get_rep_stats(rep_id)

        if not stats:
            raise HTTPException(
                status_code=404, detail=f"Rep not found: {rep_id}"
            )

        return PerformerStats(
            id=stats["id"],
            name=stats["name"],
            conversationCount=stats["conversationCount"],
            avgMeddicScore=stats["avgMeddicScore"],
            trend=stats["trend"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get rep stats for {rep_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get rep stats: {str(e)}"
        )
