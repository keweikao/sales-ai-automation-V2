"""
Unit tests for the Skills system.

Tests the core skill infrastructure including:
- Skill base class and metadata
- Skill registry registration and discovery
- Skill execution and result handling
"""

import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass
from typing import Optional

from core.skills.base import (
    Skill,
    SkillMetadata,
    SkillCategory,
    SkillContext,
    SkillResult,
)
from core.skills.registry import (
    SkillRegistry,
    SkillNotFoundError,
    skill,
)


# ===== Test Fixtures =====

@pytest.fixture
def registry():
    """Fresh skill registry for each test."""
    reg = SkillRegistry()
    yield reg
    SkillRegistry.reset()


@pytest.fixture
def sample_context():
    """Sample execution context."""
    return SkillContext(
        execution_id="test-exec-001",
        case_id="test-case-001",
        llm_gateway=MagicMock(),
        database=MagicMock(),
    )


@dataclass
class SampleInput:
    """Sample input for test skill."""
    text: str
    multiplier: int = 1


@dataclass
class SampleOutput:
    """Sample output for test skill."""
    result: str
    length: int


class MockSkill(Skill[SampleInput, SampleOutput]):
    """Mock skill for testing."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="test.mock-skill",
            name="Mock Skill",
            version="1.0.0",
            description="A mock skill for testing",
            category=SkillCategory.ANALYSIS,
        )

    def execute(
        self, input_data: SampleInput, context: SkillContext
    ) -> SkillResult[SampleOutput]:
        result = input_data.text * input_data.multiplier
        return SkillResult.ok(
            SampleOutput(result=result, length=len(result))
        )


class FailingSkill(Skill[SampleInput, SampleOutput]):
    """Skill that always fails."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="test.failing-skill",
            name="Failing Skill",
        )

    def execute(
        self, input_data: SampleInput, context: SkillContext
    ) -> SkillResult[SampleOutput]:
        raise ValueError("Intentional failure for testing")


class ValidatingSkill(Skill[SampleInput, SampleOutput]):
    """Skill with input validation."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="test.validating-skill",
            name="Validating Skill",
        )

    def validate_input(self, input_data: SampleInput) -> Optional[str]:
        if not input_data.text:
            return "Text cannot be empty"
        if input_data.multiplier < 1:
            return "Multiplier must be at least 1"
        return None

    def execute(
        self, input_data: SampleInput, context: SkillContext
    ) -> SkillResult[SampleOutput]:
        result = input_data.text * input_data.multiplier
        return SkillResult.ok(
            SampleOutput(result=result, length=len(result))
        )


# ===== SkillResult Tests =====

class TestSkillResult:
    """Tests for SkillResult dataclass."""

    def test_ok_result(self):
        """Test creating a successful result."""
        result = SkillResult.ok(data={"key": "value"}, duration=1.5)

        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
        assert result.duration_seconds == 1.5

    def test_fail_result(self):
        """Test creating a failed result."""
        result = SkillResult.fail(error="Something went wrong", duration=0.5)

        assert result.success is False
        assert result.data is None
        assert result.error == "Something went wrong"
        assert result.duration_seconds == 0.5

    def test_ok_with_metadata(self):
        """Test successful result with metadata."""
        result = SkillResult.ok(
            data="output",
            duration=1.0,
            report="Detailed report",
            metadata={"tokens": 100}
        )

        assert result.success is True
        assert result.report == "Detailed report"
        assert result.metadata == {"tokens": 100}


# ===== SkillMetadata Tests =====

class TestSkillMetadata:
    """Tests for SkillMetadata."""

    def test_default_values(self):
        """Test default metadata values."""
        metadata = SkillMetadata(id="test.skill", name="Test Skill")

        assert metadata.version == "1.0.0"
        assert metadata.category == SkillCategory.ANALYSIS
        assert metadata.tags == []
        assert metadata.requires_llm is False

    def test_full_metadata(self):
        """Test metadata with all fields."""
        metadata = SkillMetadata(
            id="my-plugin.my-skill",
            name="My Skill",
            version="2.0.0",
            description="Does something useful",
            category=SkillCategory.GENERATION,
            author="Test Author",
            tags=["llm", "generation"],
            requires_llm=True,
            estimated_duration_seconds=30.0,
        )

        assert metadata.id == "my-plugin.my-skill"
        assert metadata.category == SkillCategory.GENERATION
        assert metadata.requires_llm is True


# ===== Skill Base Class Tests =====

class TestSkillExecution:
    """Tests for skill execution."""

    def test_successful_execution(self, sample_context):
        """Test successful skill execution."""
        skill = MockSkill()
        input_data = SampleInput(text="hello", multiplier=3)

        result = skill(input_data, sample_context)

        assert result.success is True
        assert result.data.result == "hellohellohello"
        assert result.data.length == 15
        assert result.duration_seconds > 0

    def test_execution_failure_returns_fail_result(self, sample_context):
        """Test that exceptions are caught and returned as failures."""
        skill = FailingSkill()
        input_data = SampleInput(text="test")

        result = skill(input_data, sample_context)

        assert result.success is False
        assert "Intentional failure" in result.error
        assert result.duration_seconds > 0

    def test_input_validation_failure(self, sample_context):
        """Test input validation before execution."""
        skill = ValidatingSkill()

        # Empty text
        result1 = skill(SampleInput(text="", multiplier=1), sample_context)
        assert result1.success is False
        assert "Text cannot be empty" in result1.error

        # Invalid multiplier
        result2 = skill(SampleInput(text="test", multiplier=0), sample_context)
        assert result2.success is False
        assert "Multiplier must be at least 1" in result2.error

    def test_valid_input_passes_validation(self, sample_context):
        """Test that valid input passes validation."""
        skill = ValidatingSkill()
        input_data = SampleInput(text="hello", multiplier=2)

        result = skill(input_data, sample_context)

        assert result.success is True
        assert result.data.result == "hellohello"


# ===== SkillRegistry Tests =====

class TestSkillRegistry:
    """Tests for SkillRegistry."""

    def test_register_skill_class(self, registry):
        """Test registering a skill class."""
        registry.register(MockSkill)

        assert "test.mock-skill" in registry
        assert len(registry) == 1

    def test_register_with_custom_id(self, registry):
        """Test registering with a custom ID."""
        registry.register(MockSkill, skill_id="custom.skill-id")

        assert "custom.skill-id" in registry
        assert "test.mock-skill" not in registry

    def test_get_skill_instance(self, registry):
        """Test getting a skill instance."""
        registry.register(MockSkill)

        skill = registry.get("test.mock-skill")

        assert isinstance(skill, MockSkill)
        assert skill.metadata.id == "test.mock-skill"

    def test_get_unknown_skill_raises_error(self, registry):
        """Test getting an unknown skill raises error."""
        with pytest.raises(SkillNotFoundError):
            registry.get("unknown.skill")

    def test_skill_instance_caching(self, registry):
        """Test that skill instances are cached."""
        registry.register(MockSkill)

        skill1 = registry.get("test.mock-skill")
        skill2 = registry.get("test.mock-skill")

        assert skill1 is skill2  # Same instance

    def test_list_skills(self, registry):
        """Test listing all registered skills."""
        registry.register(MockSkill)
        registry.register(FailingSkill)

        skills = registry.list_skills()

        assert len(skills) == 2
        assert "test.mock-skill" in skills
        assert "test.failing-skill" in skills

    def test_list_skills_by_category(self, registry):
        """Test listing skills filtered by category."""
        registry.register(MockSkill)  # ANALYSIS category

        analysis_skills = registry.list_skills(SkillCategory.ANALYSIS)
        generation_skills = registry.list_skills(SkillCategory.GENERATION)

        assert "test.mock-skill" in analysis_skills
        assert "test.mock-skill" not in generation_skills

    def test_unregister_skill(self, registry):
        """Test unregistering a skill."""
        registry.register(MockSkill)
        assert "test.mock-skill" in registry

        result = registry.unregister("test.mock-skill")

        assert result is True
        assert "test.mock-skill" not in registry

    def test_unregister_unknown_skill(self, registry):
        """Test unregistering an unknown skill returns False."""
        result = registry.unregister("unknown.skill")
        assert result is False

    def test_has_skill(self, registry):
        """Test checking if a skill exists."""
        registry.register(MockSkill)

        assert registry.has("test.mock-skill") is True
        assert registry.has("unknown.skill") is False

    def test_get_metadata(self, registry):
        """Test getting skill metadata without instantiation."""
        registry.register(MockSkill)

        metadata = registry.get_metadata("test.mock-skill")

        assert metadata is not None
        assert metadata.id == "test.mock-skill"
        assert metadata.name == "Mock Skill"

    def test_clear_cache(self, registry):
        """Test clearing the instance cache."""
        registry.register(MockSkill)
        skill1 = registry.get("test.mock-skill")

        registry.clear_cache()
        skill2 = registry.get("test.mock-skill")

        assert skill1 is not skill2  # Different instances

    def test_singleton_pattern(self):
        """Test singleton pattern for global registry."""
        SkillRegistry.reset()

        reg1 = SkillRegistry.get_instance()
        reg2 = SkillRegistry.get_instance()

        assert reg1 is reg2

        SkillRegistry.reset()


# ===== Skill Decorator Tests =====

class TestSkillDecorator:
    """Tests for @skill decorator."""

    def test_skill_decorator_registers_class(self):
        """Test that @skill decorator registers the class."""
        SkillRegistry.reset()

        @skill("decorator.test-skill")
        class DecoratedSkill(Skill):
            @property
            def metadata(self) -> SkillMetadata:
                return SkillMetadata(
                    id="decorator.test-skill",
                    name="Decorated Skill",
                )

            def execute(self, input_data, context) -> SkillResult:
                return SkillResult.ok(data="decorated")

        registry = SkillRegistry.get_instance()
        assert "decorator.test-skill" in registry

        SkillRegistry.reset()


# ===== SkillContext Tests =====

class TestSkillContext:
    """Tests for SkillContext."""

    def test_context_with_resources(self):
        """Test context with injected resources."""
        mock_llm = MagicMock()
        mock_db = MagicMock()

        context = SkillContext(
            execution_id="exec-001",
            case_id="case-001",
            llm_gateway=mock_llm,
            database=mock_db,
        )

        assert context.llm_gateway is mock_llm
        assert context.database is mock_db

    def test_context_with_workflow_state(self):
        """Test context with workflow state."""
        context = SkillContext(
            execution_id="exec-001",
            workflow_state={
                "transcript": "Hello world",
                "analysis": {"score": 85},
            }
        )

        assert context.workflow_state["transcript"] == "Hello world"
        assert context.workflow_state["analysis"]["score"] == 85

    def test_context_default_values(self):
        """Test context default values."""
        context = SkillContext(execution_id="exec-001")

        assert context.case_id is None
        assert context.llm_gateway is None
        assert context.config == {}
        assert context.workflow_state == {}
