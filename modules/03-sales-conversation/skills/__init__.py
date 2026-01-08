"""
Sales Conversation Skills.

Wraps the existing MEDDIC agents as Skills for the new workflow system.
"""

from .context_skill import ContextAnalysisSkill
from .buyer_skill import BuyerAnalysisSkill
from .seller_skill import SellerCoachingSkill
from .summary_skill import SummaryGenerationSkill
from .crm_skill import CRMExtractionSkill
from .coach_skill import CoachEvaluationSkill

__all__ = [
    "ContextAnalysisSkill",
    "BuyerAnalysisSkill",
    "SellerCoachingSkill",
    "SummaryGenerationSkill",
    "CRMExtractionSkill",
    "CoachEvaluationSkill",
]


def register_all():
    """Register all sales conversation skills with the registry."""
    from core.skills import SkillRegistry

    registry = SkillRegistry.get_instance()
    registry.register(ContextAnalysisSkill)
    registry.register(BuyerAnalysisSkill)
    registry.register(SellerCoachingSkill)
    registry.register(SummaryGenerationSkill)
    registry.register(CRMExtractionSkill)
    registry.register(CoachEvaluationSkill)
