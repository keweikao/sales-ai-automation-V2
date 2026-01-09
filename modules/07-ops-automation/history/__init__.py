"""
Health history and statistics collection module.

Provides:
- HealthHistoryService: Store and retrieve health check history
- StatsCollector: Collect processing statistics from Firestore
"""

from .health_history import HealthHistoryService, HealthHistoryRecord
from .stats_collector import StatsCollector, ProcessingStats

__all__ = [
    "HealthHistoryService",
    "HealthHistoryRecord",
    "StatsCollector",
    "ProcessingStats",
]
