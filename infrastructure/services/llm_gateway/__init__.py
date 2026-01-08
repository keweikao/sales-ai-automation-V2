"""
LLM Gateway Service

Provides unified access to LLM providers with:
- Model routing based on task type
- Token usage tracking
- Rate limiting
- Cost monitoring

Usage:
    from infrastructure.services.llm_gateway import LLMGateway

    gateway = LLMGateway()
    response = await gateway.generate(
        prompt="Analyze this conversation...",
        task_type="meddic_analysis"
    )
"""

from .service import LLMGateway

__all__ = ["LLMGateway"]
