"""
Transcript analyzer - orchestrates conversation analysis.

Provides multi-agent orchestration for sales conversation analysis
using MEDDIC framework.

Migration note: Logic from analysis-service/src/orchestrator.py
"""

from .orchestrator import (
    MultiAgentOrchestrator,
    AnalysisResult,
    AgentResult,
    AnalysisState,
    RetryableError,
    NonRetryableError,
    InsufficientDataError,
)

__all__ = [
    "MultiAgentOrchestrator",
    "AnalysisResult",
    "AgentResult",
    "AnalysisState",
    "RetryableError",
    "NonRetryableError",
    "InsufficientDataError",
]
