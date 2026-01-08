"""
Analysis agents for MEDDIC evaluation.

Agents:
- ContextAgent: Meeting background analysis
- BuyerAgent: Customer insight extraction
- SellerAgent: Sales coaching
- SummaryAgent: Summary generation
- CoachAgent: Real-time sales coaching alerts
- CRMExtractorAgent: CRM data extraction

Migration note: From analysis-service/src/agents/
"""

from .base import (
    GeminiJSONAgent,
    GeminiResponse,
    GeminiClientError,
    render_transcript,
    format_timestamp,
    parse_dual_mode_output,
    extract_json_from_response,
)
from .context_agent import ContextAgent
from .buyer_agent import BuyerAgent
from .seller_agent import SellerAgent
from .summary_agent import SummaryAgent
from .coach_agent import CoachAgent, CoachAlert, ManagerAlert
from .crm_agent import CRMExtractorAgent

__all__ = [
    # Base classes and utilities
    "GeminiJSONAgent",
    "GeminiResponse",
    "GeminiClientError",
    "render_transcript",
    "format_timestamp",
    "parse_dual_mode_output",
    "extract_json_from_response",
    # Agents
    "ContextAgent",
    "BuyerAgent",
    "SellerAgent",
    "SummaryAgent",
    "CoachAgent",
    "CoachAlert",
    "ManagerAlert",
    "CRMExtractorAgent",
]
