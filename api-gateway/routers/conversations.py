"""對話相關 API 路由"""
import logging
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import datetime

from schemas.conversation import (
    Conversation,
    ConversationDetail,
    ConversationListResponse,
    AnalysisResult,
    Transcript,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def get_conversation_repository():
    """Get ConversationRepository instance."""
    try:
        from core.database.repositories.conversation_repository import ConversationRepository
        return ConversationRepository()
    except Exception as e:
        logger.warning(f"Failed to initialize repository: {e}")
        return None


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    status: Optional[str] = Query(None, description="篩選狀態 (pending, completed, failed)"),
    sales_rep: Optional[str] = Query(None, description="篩選業務員 ID"),
    start_date: Optional[datetime] = Query(None, description="開始日期"),
    end_date: Optional[datetime] = Query(None, description="結束日期"),
    limit: int = Query(50, ge=1, le=100, description="回傳數量限制"),
    offset: int = Query(0, ge=0, description="分頁偏移"),
):
    """
    列出對話記錄

    支援多種篩選條件：
    - status: 對話狀態
    - sales_rep: 業務員 ID
    - start_date/end_date: 日期範圍
    """
    repo = get_conversation_repository()

    if repo is None:
        # Return empty list if repository not available (local dev without GCP)
        return ConversationListResponse(items=[], total=0, limit=limit, offset=offset)

    try:
        if sales_rep:
            conversations = await repo.list_by_sales_rep(
                sales_rep_id=sales_rep,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
        elif status:
            conversations = await repo.list_by_status(status=status, limit=limit)
        else:
            conversations = await repo.list_by_status(status="completed", limit=limit)

        items = [
            Conversation(
                id=c.id,
                leadId=c.lead_id,
                salesRepName=c.sales_rep_name,
                status=c.status,
                conversationType=c.conversation_type.value if hasattr(c, 'conversation_type') and c.conversation_type else None,
                createdAt=c.created_at,
                completedAt=c.completed_at,
            )
            for c in conversations
        ]

        return ConversationListResponse(
            items=items,
            total=len(items),
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error(f"Failed to list conversations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list conversations: {str(e)}")


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str):
    """
    取得對話詳情

    包含：
    - 基本資訊
    - 逐字稿 (transcript)
    - 分析結果 (analysis)
    """
    repo = get_conversation_repository()

    if repo is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        conversation = await repo.get(conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_id}")

        result = ConversationDetail(
            id=conversation.id,
            leadId=conversation.lead_id,
            salesRepName=conversation.sales_rep_name,
            status=conversation.status,
            conversationType=conversation.conversation_type.value if hasattr(conversation, 'conversation_type') and conversation.conversation_type else None,
            createdAt=conversation.created_at,
            completedAt=conversation.completed_at,
        )

        if conversation.transcript:
            result.transcript = Transcript(
                segments=[
                    {
                        "speaker": seg.speaker_label,
                        "text": seg.text,
                        "start": seg.start_time,
                        "end": seg.end_time,
                    }
                    for seg in conversation.transcript.segments
                ],
                fullText=conversation.transcript.full_text,
                language=conversation.transcript.language,
                durationSeconds=conversation.transcript.duration_seconds,
            )

        result.analysis = AnalysisResult()

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation {conversation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {str(e)}")


@router.get("/conversations/{conversation_id}/analysis", response_model=AnalysisResult)
async def get_conversation_analysis(conversation_id: str):
    """
    取得對話分析結果

    返回 MEDDIC 分析、買家心理、銷售建議等。
    """
    try:
        from deps.firestore import get_firestore_client

        db = get_firestore_client()
        doc = db.collection("cases").document(conversation_id).get()

        if not doc.exists:
            raise HTTPException(
                status_code=404, detail=f"Conversation not found: {conversation_id}"
            )

        data = doc.to_dict()
        analysis = data.get("analysis", {})
        agents = analysis.get("agents", {})

        # Extract MEDDIC score from agent2 (Buyer Analysis)
        agent2_data = agents.get("agent2", {}).get("data", {})
        meddic_score = agent2_data.get("meddic_score", 0)

        # Extract summary from agent4 (Summary Generation)
        agent4_data = agents.get("agent4", {}).get("data", {})
        summary = agent4_data.get("executive_summary", "")

        # Extract buyer insights
        buyer_signals = agent2_data.get("buyer_signals", [])
        qualification_status = agent2_data.get("qualification_status", "")

        # Extract seller insights from agent3
        agent3_data = agents.get("agent3", {}).get("data", {})
        progress_score = agent3_data.get("progress_score", 0)
        coaching_notes = agent3_data.get("coaching_notes", [])

        # Extract context from agent1
        agent1_data = agents.get("agent1", {}).get("data", {})
        store_name = agent1_data.get("store_name", "")
        urgency_level = agent1_data.get("urgency_level", "")

        return AnalysisResult(
            meddicScore=meddic_score,
            summary=summary or "No summary available",
            qualificationStatus=qualification_status,
            progressScore=progress_score,
            buyerSignals=buyer_signals,
            coachingNotes=coaching_notes,
            storeName=store_name,
            urgencyLevel=urgency_level,
            rawAgents={
                "agent1": agents.get("agent1", {}),
                "agent2": agents.get("agent2", {}),
                "agent3": agents.get("agent3", {}),
                "agent4": agents.get("agent4", {}),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get analysis for {conversation_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to get analysis: {str(e)}"
        )
