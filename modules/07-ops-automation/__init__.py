"""
07-Ops-Automation Module

Operational automation and monitoring.

Features:
- Error notification with Slack integration
- System health monitoring
- Automated remediation (retry and cleanup)
- Ops Agent for intelligent analysis
- Health history and statistics tracking
- Proactive daily reporting (morning/evening)

Status: COMPLETE
"""

from .monitoring.error_notifier import (
    ErrorNotifier,
    ErrorSeverity,
    ErrorCategory,
    ErrorRecord,
)
from .health_check import HealthChecker, ServiceStatus
from .remediation import AutoRetryService, DataCleanupService
from .history import (
    HealthHistoryService,
    HealthHistoryRecord,
    StatsCollector,
    ProcessingStats,
)
from .agent import OpsOrchestrator, OpsRunResult
from .reporting import OpsReporter

__all__ = [
    # Error notification
    "ErrorNotifier",
    "ErrorSeverity",
    "ErrorCategory",
    "ErrorRecord",
    # Health check
    "HealthChecker",
    "ServiceStatus",
    # Remediation
    "AutoRetryService",
    "DataCleanupService",
    # History
    "HealthHistoryService",
    "HealthHistoryRecord",
    "StatsCollector",
    "ProcessingStats",
    # Agent
    "OpsOrchestrator",
    "OpsRunResult",
    # Reporting
    "OpsReporter",
]

# Optional: OpsAgent (requires google-generativeai)
try:
    from .agent import OpsAgent, OpsAnalysisResult

    __all__.extend(["OpsAgent", "OpsAnalysisResult"])
except ImportError:
    pass
