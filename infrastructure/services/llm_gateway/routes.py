"""
LLM Gateway API routes.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Optional

router = APIRouter(prefix="/llm", tags=["llm"])


class GenerateRequest(BaseModel):
    """Request for text generation."""
    prompt: str
    task_type: str = "default"
    conversation_id: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class GenerateResponse(BaseModel):
    """Response from generation."""
    text: str
    model: str
    tokens_used: int


@router.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """Generate text using LLM."""
    # TODO: Connect to LLMGateway
    return GenerateResponse(
        text="Gateway not yet connected",
        model="pending",
        tokens_used=0,
    )


@router.get("/usage")
async def get_usage(
    conversation_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Get token usage statistics."""
    # TODO: Implement usage reporting
    return {"message": "Usage reporting not yet implemented"}
