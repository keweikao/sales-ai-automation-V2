from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List

class RetryableError(Exception):
    """Error that can be retried (e.g., network timeout, rate limit)."""
    pass


class NonRetryableError(Exception):
    """Error that should not be retried (e.g., invalid format, auth error)."""
    pass


class InsufficientDataError(Exception):
    """Not enough agents succeeded to proceed with synthesis."""
    pass


@dataclass
class AgentResult:
    """Result from a single agent execution."""
    agent_id: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None  # 'retryable' or 'non_retryable'
    duration: float = 0.0
    retry_count: int = 0
    raw_output: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None  # Additional metadata like reports


@dataclass
class AnalysisResult:
    """Complete analysis result from all agents."""
    case_id: str
    success: bool
    agent_results: Dict[str, AgentResult] = field(default_factory=dict)
    total_duration: float = 0.0
    error: Optional[str] = None
    coach_alert: Optional[Any] = None  # CoachAlert object from Agent 5
    manager_alert: Optional[Any] = None # ManagerAlert object from Agent 5

    def get_agent_data(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get structured data from a specific agent."""
        result = self.agent_results.get(agent_id)
        return result.data if result and result.success else None
