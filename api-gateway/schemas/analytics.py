"""分析相關 Schema"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class PerformerStats(BaseModel):
    """業務表現統計"""
    id: str = Field(..., description="業務員 ID")
    name: str = Field(..., description="業務員名稱")
    conversationCount: int = Field(..., description="對話數量")
    avgMeddicScore: float = Field(..., description="平均 MEDDIC 分數")
    trend: Optional[str] = Field(None, description="趨勢: up, down, stable")


class DashboardStats(BaseModel):
    """儀表板統計數據"""
    totalConversations: int = Field(..., description="總對話數")
    completedToday: int = Field(..., description="今日完成數")
    pendingAnalysis: int = Field(0, description="待分析數")
    avgMeddicScore: float = Field(..., description="平均 MEDDIC 分數")
    conversionRate: float = Field(..., description="轉換率 (0-100)")
    topPerformers: List[PerformerStats] = Field(default_factory=list, description="表現最佳業務員")
    recentTrend: Optional[str] = Field(None, description="近期趨勢: improving, declining, stable")
    lastUpdated: datetime = Field(default_factory=datetime.utcnow, description="最後更新時間")

    class Config:
        json_schema_extra = {
            "example": {
                "totalConversations": 150,
                "completedToday": 12,
                "pendingAnalysis": 3,
                "avgMeddicScore": 65.5,
                "conversionRate": 23.4,
                "topPerformers": [
                    {"id": "rep_001", "name": "Alice Wang", "conversationCount": 45, "avgMeddicScore": 78.2, "trend": "up"},
                    {"id": "rep_002", "name": "Bob Chen", "conversationCount": 38, "avgMeddicScore": 72.1, "trend": "stable"},
                ],
                "recentTrend": "improving",
                "lastUpdated": "2025-01-08T12:00:00Z",
            }
        }


class WeeklyReportSummary(BaseModel):
    """週報摘要"""
    periodStart: datetime = Field(..., description="報告期間開始")
    periodEnd: datetime = Field(..., description="報告期間結束")
    totalConversations: int = Field(..., description="總對話數")
    totalAnalyzed: int = Field(..., description="已分析數")
    avgMeddicScore: float = Field(..., description="平均 MEDDIC 分數")
    byRep: List[PerformerStats] = Field(default_factory=list, description="各業務員統計")
    insights: List[str] = Field(default_factory=list, description="關鍵洞察")
    generatedAt: datetime = Field(default_factory=datetime.utcnow, description="產生時間")


class TrendData(BaseModel):
    """趨勢資料"""
    date: datetime = Field(..., description="日期")
    conversationCount: int = Field(..., description="對話數量")
    avgMeddicScore: float = Field(..., description="平均分數")


class AnalyticsTrends(BaseModel):
    """分析趨勢"""
    period: str = Field(..., description="期間: 7d, 30d, 90d")
    data: List[TrendData] = Field(..., description="趨勢資料")
    overallTrend: str = Field(..., description="整體趨勢: improving, declining, stable")
