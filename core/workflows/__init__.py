"""
Workflow system for declarative orchestration.

Provides a way to define analysis pipelines as data (YAML/Markdown)
rather than code, enabling easier customization and A/B testing.
"""

from .schema import (
    Workflow,
    WorkflowMetadata,
    WorkflowPhase,
    WorkflowStep,
    WorkflowTrigger,
    WorkflowState,
    ExecutionMode,
    Condition,
    ConditionOperator,
    RetryConfig,
    QualityCheck,
    StepInput,
    StepOutput,
)
from .loader import (
    WorkflowLoader,
    WorkflowLoadError,
    load_workflow,
)
from .executor import (
    WorkflowExecutor,
    WorkflowExecution,
    PhaseExecution,
    StepExecution,
)

__all__ = [
    # Schema
    "Workflow",
    "WorkflowMetadata",
    "WorkflowPhase",
    "WorkflowStep",
    "WorkflowTrigger",
    "WorkflowState",
    "ExecutionMode",
    "Condition",
    "ConditionOperator",
    "RetryConfig",
    "QualityCheck",
    "StepInput",
    "StepOutput",
    # Loader
    "WorkflowLoader",
    "WorkflowLoadError",
    "load_workflow",
    # Executor
    "WorkflowExecutor",
    "WorkflowExecution",
    "PhaseExecution",
    "StepExecution",
]
