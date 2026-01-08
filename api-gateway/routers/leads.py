"""潛客相關 API 路由"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from google.cloud import firestore

from deps.firestore import get_db
from schemas.lead import Lead
from services.lead_service import LeadService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/leads", response_model=List[Lead])
async def list_leads(
    status: Optional[str] = Query(None, description="篩選狀態"),
    limit: int = Query(50, ge=1, le=100, description="回傳數量限制"),
    db: firestore.Client = Depends(get_db),
):
    """
    列出潛客

    可選篩選條件：
    - status: new, contacted, qualified, converted
    """
    try:
        service = LeadService(db)
        leads = service.list_leads(status=status, limit=limit)
        return leads
    except Exception as e:
        logger.error(f"Failed to list leads: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list leads: {str(e)}")


@router.get("/leads/{lead_id}", response_model=Lead)
async def get_lead(
    lead_id: str,
    db: firestore.Client = Depends(get_db),
):
    """取得潛客詳情"""
    try:
        service = LeadService(db)
        lead = service.get_lead(lead_id)

        if not lead:
            raise HTTPException(status_code=404, detail=f"Lead not found: {lead_id}")

        return lead
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get lead {lead_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get lead: {str(e)}")
