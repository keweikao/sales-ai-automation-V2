"""
Repository pattern implementations for data access.

Repositories provide a clean abstraction over Firestore operations.
"""

from .conversation_repository import ConversationRepository
from .lead_repository import LeadRepository

__all__ = ["ConversationRepository", "LeadRepository"]
