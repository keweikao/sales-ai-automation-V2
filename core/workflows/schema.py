"""
Workflow Schema definitions.

Defines the structure for declarative workflow configurations.
Workflows describe the execution flow of skills for a specific use case.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ExecutionMode(str, Enum):
    """How steps should be executed."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


class ConditionOperator(str, Enum):
    """Operators for conditional execution."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


@dataclass
class Condition:
    """
    Condition for conditional step execution.

    Example:
        Condition(
            field="state.competitors_detected",
            operator=ConditionOperator.EQUALS,
            value=True
        )
    """
    field: str
    operator: ConditionOperator
    value: Any = None

    def evaluate(self, context: dict[str, Any]) -> bool:
        """Evaluate the condition against a context."""
        # Navigate nested fields (e.g., "state.buyer_data.score")
        current = context
        for part in self.field.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            else:
                current = getattr(current, part, None)
            if current is None:
                break

        if self.operator == ConditionOperator.EXISTS:
            return current is not None
        if self.operator == ConditionOperator.NOT_EXISTS:
            return current is None
        if self.operator == ConditionOperator.EQUALS:
            return current == self.value
        if self.operator == ConditionOperator.NOT_EQUALS:
            return current != self.value
        if self.operator == ConditionOperator.CONTAINS:
            return self.value in current if current else False
        if self.operator == ConditionOperator.GREATER_THAN:
            return current > self.value if current is not None else False
        if self.operator == ConditionOperator.LESS_THAN:
            return current < self.value if current is not None else False

        return False


@dataclass
class RetryConfig:
    """Configuration for step retry behavior."""
    max_attempts: int = 3
    backoff_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    retryable_errors: list[str] = field(default_factory=lambda: [
        "timeout", "rate_limit", "503", "429"
    ])


@dataclass
class QualityCheck:
    """
    Quality check configuration for a step output.

    Enables self-correction/refinement if quality check fails.
    """
    enabled: bool = False
    max_refinements: int = 2
    rules: list[dict[str, Any]] = field(default_factory=list)
    # Rules example: [{"field": "identifiedNeeds", "min_length": 2}]


@dataclass
class StepInput:
    """
    Defines input mapping for a step.

    Maps workflow state fields to skill input parameters.
    """
    from_state: str  # Path in workflow state
    to_param: str    # Parameter name for the skill
    required: bool = True
    default: Any = None


@dataclass
class StepOutput:
    """
    Defines output mapping for a step.

    Maps skill output to workflow state fields.
    """
    from_result: str  # Path in skill result
    to_state: str     # Path in workflow state


@dataclass
class WorkflowStep:
    """
    A single step in a workflow.

    Each step invokes a skill with specific inputs/outputs and optional conditions.
    """
    id: str
    skill: str  # Skill identifier (e.g., "meddic.context-agent")
    name: Optional[str] = None
    description: Optional[str] = None

    # Input/Output mapping
    inputs: list[StepInput] = field(default_factory=list)
    outputs: list[StepOutput] = field(default_factory=list)

    # Execution control
    condition: Optional[Condition] = None
    retry: Optional[RetryConfig] = None
    timeout_seconds: float = 120.0

    # Quality assurance
    quality_check: Optional[QualityCheck] = None

    # Dependencies (step IDs that must complete before this step)
    depends_on: list[str] = field(default_factory=list)


@dataclass
class WorkflowPhase:
    """
    A phase groups multiple steps with a shared execution mode.

    Phases execute sequentially, but steps within a phase can run in parallel.
    """
    id: str
    name: str
    description: Optional[str] = None
    mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    steps: list[WorkflowStep] = field(default_factory=list)


@dataclass
class WorkflowTrigger:
    """Defines when a workflow should be triggered."""
    event: str  # e.g., "transcript.created", "case.status_changed"
    conditions: list[Condition] = field(default_factory=list)


@dataclass
class WorkflowMetadata:
    """Metadata for a workflow definition."""
    id: str
    name: str
    version: str = "1.0.0"
    description: Optional[str] = None
    author: Optional[str] = None
    tags: list[str] = field(default_factory=list)


@dataclass
class Workflow:
    """
    Complete workflow definition.

    A workflow orchestrates multiple skills through phases and steps.
    """
    metadata: WorkflowMetadata
    triggers: list[WorkflowTrigger] = field(default_factory=list)
    phases: list[WorkflowPhase] = field(default_factory=list)

    # Initial state template
    initial_state: dict[str, Any] = field(default_factory=dict)

    # Global configurations
    timeout_seconds: float = 600.0
    retry: Optional[RetryConfig] = None

    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """Find a step by ID across all phases."""
        for phase in self.phases:
            for step in phase.steps:
                if step.id == step_id:
                    return step
        return None

    def get_phase(self, phase_id: str) -> Optional[WorkflowPhase]:
        """Find a phase by ID."""
        for phase in self.phases:
            if phase.id == phase_id:
                return phase
        return None


# Type alias for workflow state
WorkflowState = dict[str, Any]
