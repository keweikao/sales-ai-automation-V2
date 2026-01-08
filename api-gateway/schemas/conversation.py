"""對話相關 Schema"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class Conversation(BaseModel):
    """對話基本資訊"""
    id: str = Field(..., description="對話 ID")
    leadId: Optional[str] = Field(None, description="關聯的潛客 ID")
    salesRepName: Optional[str] = Field(None, description="業務員名稱")
    status: str = Field(..., description="狀態: pending, transcribing, analyzing, completed, failed")
    conversationType: Optional[str] = Field(None, description="對話類型: discovery, demo, negotiation, etc.")
    createdAt: datetime = Field(..., description="建立時間")
    completedAt: Optional[datetime] = Field(None, description="完成時間")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "case_20250108_001",
                "leadId": "lead_abc123",
                "salesRepName": "Alice Wang",
                "status": "completed",
                "conversationType": "demo",
                "createdAt": "2025-01-08T10:30:00Z",
                "completedAt": "2025-01-08T11:00:00Z",
            }
        }


class ConversationListResponse(BaseModel):
    """對話列表回應"""
    items: List[Conversation] = Field(..., description="對話列表")
    total: int = Field(..., description="總筆數")
    limit: int = Field(..., description="每頁筆數")
    offset: int = Field(0, description="分頁偏移")


class TranscriptSegment(BaseModel):
    """逐字稿片段"""
    speaker: Optional[str] = Field(None, description="發言者")
    text: str = Field(..., description="文字內容")
    start: Optional[float] = Field(None, description="開始時間 (秒)")
    end: Optional[float] = Field(None, description="結束時間 (秒)")


class Transcript(BaseModel):
    """逐字稿"""
    segments: List[TranscriptSegment] = Field(default_factory=list, description="逐字稿片段")
    fullText: Optional[str] = Field(None, description="完整文字")
    language: str = Field("zh-TW", description="語言")
    durationSeconds: Optional[float] = Field(None, description="時長 (秒)")


class MEDDICData(BaseModel):
    """MEDDIC 分析資料"""
    metrics: Optional[str] = Field(None, description="量化指標")
    economicBuyer: Optional[str] = Field(None, description="經濟決策者")
    decisionCriteria: Optional[str] = Field(None, description="決策標準")
    decisionProcess: Optional[str] = Field(None, description="決策流程")
    identifyPain: Optional[str] = Field(None, description="痛點")
    champion: Optional[str] = Field(None, description="支持者")


class BuyerData(BaseModel):
    """買家分析資料"""
    identifiedNeeds: List[str] = Field(default_factory=list, description="已識別需求")
    hesitations: List[str] = Field(default_factory=list, description="疑慮")
    painPoints: List[str] = Field(default_factory=list, description="痛點")
    trustScore: Optional[int] = Field(None, description="信任分數 0-100")
    meddic: Optional[MEDDICData] = Field(None, description="MEDDIC 分析")


class CoachingInsight(BaseModel):
    """銷售指導建議"""
    category: str = Field(..., description="類別: strength, improvement, action")
    content: str = Field(..., description="內容")
    priority: Optional[str] = Field(None, description="優先度: high, medium, low")


class SellerCoaching(BaseModel):
    """銷售指導資料"""
    progressScore: Optional[int] = Field(None, description="進度分數 0-100")
    recommendedStrategy: Optional[str] = Field(None, description="建議策略")
    insights: List[CoachingInsight] = Field(default_factory=list, description="洞察列表")
    nextSteps: List[str] = Field(default_factory=list, description="下一步行動")


class AnalysisResult(BaseModel):
    """分析結果"""
    contextData: Optional[Dict[str, Any]] = Field(None, description="對話背景資料")
    buyerData: Optional[BuyerData] = Field(None, description="買家分析")
    sellerCoaching: Optional[SellerCoaching] = Field(None, description="銷售指導")
    meddicScore: Optional[int] = Field(None, description="MEDDIC 總分 0-100")
    summary: Optional[str] = Field(None, description="摘要")
    customerSummary: Optional[str] = Field(None, description="客戶摘要 (可發送給客戶)")
    analyzedAt: Optional[datetime] = Field(None, description="分析時間")
    # Additional fields from Firestore analysis
    qualificationStatus: Optional[str] = Field(None, description="資格狀態")
    progressScore: Optional[int] = Field(None, description="推進分數 0-100")
    buyerSignals: List[str] = Field(default_factory=list, description="買家訊號")
    coachingNotes: List[str] = Field(default_factory=list, description="教練筆記")
    storeName: Optional[str] = Field(None, description="店家名稱")
    urgencyLevel: Optional[str] = Field(None, description="急迫度")
    rawAgents: Optional[Dict[str, Any]] = Field(None, description="原始 Agent 資料")


class ConversationDetail(Conversation):
    """對話詳情（包含逐字稿和分析）"""
    transcript: Optional[Transcript] = Field(None, description="逐字稿")
    analysis: Optional[AnalysisResult] = Field(None, description="分析結果")
    audioFileUri: Optional[str] = Field(None, description="音檔 GCS URI")
    audioDurationSeconds: Optional[float] = Field(None, description="音檔時長")
