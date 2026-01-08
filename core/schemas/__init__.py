"""
Core schemas for Sales AI Automation V2.1

Pydantic models defining data contracts across modules.
"""

from .lead import Lead, LeadSource, LeadStatus
from .conversation import Conversation, Transcript, Speaker
from .analysis_result import AnalysisResult, MEDDICScore, CoachingInsight
from .events import Event, EventType

__all__ = [
    # Lead
    "Lead",
    "LeadSource",
    "LeadStatus",
    # Conversation
    "Conversation",
    "Transcript",
    "Speaker",
    # Analysis
    "AnalysisResult",
    "MEDDICScore",
    "CoachingInsight",
    # Events
    "Event",
    "EventType",
]
