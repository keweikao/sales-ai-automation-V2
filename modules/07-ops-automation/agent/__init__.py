"""
Ops Agent module.

Provides:
- OpsOrchestrator: Coordinates all ops automation services
- OpsAgent: LLM-based intelligent analysis (optional)
"""

from .orchestrator import OpsOrchestrator, OpsRunResult

__all__ = [
    "OpsOrchestrator",
    "OpsRunResult",
]

# OpsAgent is imported conditionally to avoid requiring Gemini SDK
try:
    from .ops_agent import OpsAgent, OpsAnalysisResult

    __all__.extend(["OpsAgent", "OpsAnalysisResult"])
except ImportError:
    pass
