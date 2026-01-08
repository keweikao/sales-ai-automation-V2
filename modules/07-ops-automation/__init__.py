"""
07-Ops-Automation Module

Operational automation and monitoring.

Features:
- Error notification with Slack integration
- System health monitoring
- Automated remediation (retry and cleanup)

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
]
