"""
Base Skill interface and utilities.

Skills are the atomic units of functionality that can be composed
into workflows. Each skill has a well-defined interface with
typed inputs and outputs.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, Optional, TypeVar

logger = logging.getLogger(__name__)


class SkillCategory(str, Enum):
    """Categories of skills for organization and discovery."""
    ANALYSIS = "analysis"       # Analyze data (e.g., transcript analysis)
    EXTRACTION = "extraction"   # Extract structured data
    GENERATION = "generation"   # Generate content (e.g., summaries)
    TRANSFORMATION = "transformation"  # Transform data formats
    INTEGRATION = "integration" # External system integration
    NOTIFICATION = "notification"  # Send notifications
    VALIDATION = "validation"   # Validate data quality


@dataclass
class SkillMetadata:
    """Metadata describing a skill."""
    id: str  # Unique identifier (e.g., "meddic.context-agent")
    name: str  # Human-readable name
    version: str = "1.0.0"
    description: Optional[str] = None
    category: SkillCategory = SkillCategory.ANALYSIS
    author: Optional[str] = None
    tags: list[str] = field(default_factory=list)

    # Schema information
    input_schema: Optional[dict[str, Any]] = None
    output_schema: Optional[dict[str, Any]] = None

    # Resource requirements
    requires_llm: bool = False
    requires_database: bool = False
    estimated_duration_seconds: float = 10.0


@dataclass
class SkillContext:
    """
    Runtime context provided to skills during execution.

    Contains shared resources and configuration.
    """
    # Unique execution ID for tracing
    execution_id: str

    # Case/conversation being processed
    case_id: Optional[str] = None

    # Shared resources (injected by plugin manager)
    llm_gateway: Optional[Any] = None
    database: Optional[Any] = None
    notification_service: Optional[Any] = None

    # Configuration
    config: dict[str, Any] = field(default_factory=dict)

    # State from previous steps (read-only)
    workflow_state: dict[str, Any] = field(default_factory=dict)


# Generic type for skill input/output
TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


@dataclass
class SkillResult(Generic[TOutput]):
    """
    Result from skill execution.

    Provides a uniform structure for all skill outputs.
    """
    success: bool
    data: Optional[TOutput] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0

    # Optional human-readable report
    report: Optional[str] = None

    # Metadata for debugging/tracing
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, data: TOutput, duration: float = 0.0, **kwargs) -> "SkillResult[TOutput]":
        """Create a successful result."""
        return cls(success=True, data=data, duration_seconds=duration, **kwargs)

    @classmethod
    def fail(cls, error: str, duration: float = 0.0, **kwargs) -> "SkillResult[TOutput]":
        """Create a failed result."""
        return cls(success=False, error=error, duration_seconds=duration, **kwargs)


class Skill(ABC, Generic[TInput, TOutput]):
    """
    Abstract base class for all skills.

    Skills are stateless, reusable units of functionality.
    They receive typed input and produce typed output.
    """

    @property
    @abstractmethod
    def metadata(self) -> SkillMetadata:
        """Return skill metadata."""
        ...

    @abstractmethod
    def execute(self, input_data: TInput, context: SkillContext) -> SkillResult[TOutput]:
        """
        Execute the skill.

        Args:
            input_data: Typed input for the skill
            context: Runtime context with shared resources

        Returns:
            SkillResult with success/failure and output data
        """
        ...

    def validate_input(self, input_data: TInput) -> Optional[str]:
        """
        Validate input data before execution.

        Override to add custom validation.

        Returns:
            Error message if invalid, None if valid
        """
        return None

    def __call__(self, input_data: TInput, context: SkillContext) -> SkillResult[TOutput]:
        """Execute the skill with timing and error handling."""
        start = time.time()

        # Validate input
        validation_error = self.validate_input(input_data)
        if validation_error:
            return SkillResult.fail(
                error=f"Input validation failed: {validation_error}",
                duration=time.time() - start
            )

        try:
            result = self.execute(input_data, context)
            result.duration_seconds = time.time() - start
            return result
        except Exception as e:
            logger.error(f"Skill {self.metadata.id} failed: {e}", exc_info=True)
            return SkillResult.fail(
                error=str(e),
                duration=time.time() - start
            )


class LLMSkill(Skill[TInput, TOutput]):
    """
    Base class for skills that use LLM for processing.

    Provides common utilities for prompt-based skills.
    """

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash",
        temperature: float = 0.2,
    ):
        self.model_name = model_name
        self.temperature = temperature

    def get_llm(self, context: SkillContext) -> Any:
        """Get LLM gateway from context."""
        if context.llm_gateway is None:
            raise RuntimeError("LLM gateway not available in context")
        return context.llm_gateway

    @abstractmethod
    def build_prompt(self, input_data: TInput) -> str:
        """Build the prompt for the LLM."""
        ...

    def parse_response(self, response: str) -> TOutput:
        """
        Parse the LLM response into typed output.

        Override for custom parsing logic.
        """
        # Default: return raw response (subclasses should override)
        return response  # type: ignore


class CompositeSkill(Skill[TInput, TOutput]):
    """
    A skill that composes multiple sub-skills.

    Useful for creating higher-level skills from primitives.
    """

    def __init__(self, skills: list[Skill]):
        self._skills = skills

    @property
    def skills(self) -> list[Skill]:
        """Get the list of sub-skills."""
        return self._skills
