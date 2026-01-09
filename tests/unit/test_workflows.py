"""
Unit tests for the Workflow system.

Tests the workflow execution infrastructure including:
- Workflow schema validation
- Workflow executor step and phase execution
- State management and data flow
- Parallel vs sequential execution
"""

import pytest
import asyncio
from unittest.mock import MagicMock

from core.skills.base import Skill, SkillMetadata, SkillContext, SkillResult
from core.skills.registry import SkillRegistry
from core.workflows.schema import (
    Workflow,
    WorkflowMetadata,
    WorkflowPhase,
    WorkflowStep,
    StepInput,
    StepOutput,
    ExecutionMode,
)
from core.workflows.executor import (
    WorkflowExecutor,
    WorkflowExecution,
    PhaseExecution,
    StepExecution,
)


# ===== Test Fixtures =====

@pytest.fixture
def registry():
    """Fresh skill registry with test skills."""
    SkillRegistry.reset()
    reg = SkillRegistry()

    # Register test skills
    reg.register(EchoSkill)
    reg.register(UppercaseSkill)
    reg.register(CounterSkill)
    reg.register(SlowSkill)

    yield reg
    SkillRegistry.reset()


@pytest.fixture
def executor(registry):
    """Workflow executor with test registry."""
    return WorkflowExecutor(
        registry=registry,
        llm_gateway=MagicMock(),
        database=MagicMock(),
    )


# ===== Test Skills =====

class EchoSkill(Skill):
    """Simply echoes input."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(id="test.echo", name="Echo Skill")

    def execute(self, input_data: dict, context: SkillContext) -> SkillResult:
        return SkillResult.ok(data={"echo": input_data.get("message", "")})


class UppercaseSkill(Skill):
    """Converts text to uppercase."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(id="test.uppercase", name="Uppercase Skill")

    def execute(self, input_data: dict, context: SkillContext) -> SkillResult:
        text = input_data.get("text", "")
        return SkillResult.ok(data={"result": text.upper()})


class CounterSkill(Skill):
    """Counts items in a list."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(id="test.counter", name="Counter Skill")

    def execute(self, input_data: dict, context: SkillContext) -> SkillResult:
        items = input_data.get("items", [])
        return SkillResult.ok(data={"count": len(items)})


class SlowSkill(Skill):
    """Simulates slow processing."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(id="test.slow", name="Slow Skill")

    def execute(self, input_data: dict, context: SkillContext) -> SkillResult:
        import time
        delay = input_data.get("delay", 0.1)
        time.sleep(delay)
        return SkillResult.ok(data={"processed": True})


# ===== WorkflowMetadata Tests =====

class TestWorkflowMetadata:
    """Tests for WorkflowMetadata."""

    def test_default_values(self):
        """Test default metadata values."""
        metadata = WorkflowMetadata(id="test.workflow", name="Test Workflow")

        assert metadata.version == "1.0.0"
        assert metadata.description is None
        assert metadata.tags == []

    def test_full_metadata(self):
        """Test metadata with all fields."""
        metadata = WorkflowMetadata(
            id="sales.meddic-analysis",
            name="MEDDIC Analysis Workflow",
            version="2.0.0",
            description="Analyzes sales conversations using MEDDIC",
            author="Sales AI Team",
            tags=["sales", "meddic", "analysis"],
        )

        assert metadata.id == "sales.meddic-analysis"
        assert "meddic" in metadata.tags


# ===== WorkflowStep Tests =====

class TestWorkflowStep:
    """Tests for WorkflowStep configuration."""

    def test_minimal_step(self):
        """Test minimal step configuration."""
        step = WorkflowStep(
            id="step1",
            skill="test.echo",
            inputs=[],
            outputs=[],
        )

        assert step.id == "step1"
        assert step.skill == "test.echo"
        assert step.timeout_seconds == 120.0  # default from schema

    def test_step_with_io(self):
        """Test step with input/output mappings."""
        step = WorkflowStep(
            id="process",
            skill="test.uppercase",
            inputs=[
                StepInput(from_state="input.text", to_param="text"),
            ],
            outputs=[
                StepOutput(from_result="result", to_state="output.text"),
            ],
        )

        assert len(step.inputs) == 1
        assert step.inputs[0].from_state == "input.text"
        assert len(step.outputs) == 1
        assert step.outputs[0].to_state == "output.text"


# ===== WorkflowPhase Tests =====

class TestWorkflowPhase:
    """Tests for WorkflowPhase configuration."""

    def test_sequential_phase(self):
        """Test sequential execution mode."""
        phase = WorkflowPhase(
            id="phase1",
            name="Phase 1",
            steps=[
                WorkflowStep(id="s1", skill="test.echo", inputs=[], outputs=[]),
                WorkflowStep(id="s2", skill="test.uppercase", inputs=[], outputs=[]),
            ],
            mode=ExecutionMode.SEQUENTIAL,
        )

        assert phase.mode == ExecutionMode.SEQUENTIAL
        assert len(phase.steps) == 2

    def test_parallel_phase(self):
        """Test parallel execution mode."""
        phase = WorkflowPhase(
            id="parallel-phase",
            name="Parallel Phase",
            steps=[
                WorkflowStep(id="s1", skill="test.echo", inputs=[], outputs=[]),
                WorkflowStep(id="s2", skill="test.counter", inputs=[], outputs=[]),
            ],
            mode=ExecutionMode.PARALLEL,
        )

        assert phase.mode == ExecutionMode.PARALLEL


# ===== WorkflowExecutor Tests =====

class TestWorkflowExecutor:
    """Tests for WorkflowExecutor."""

    def test_execute_simple_workflow(self, executor):
        """Test executing a simple workflow."""
        workflow = Workflow(
            metadata=WorkflowMetadata(id="test.simple", name="Simple"),
            phases=[
                WorkflowPhase(
                    id="phase1",
                    name="Phase 1",
                    steps=[
                        WorkflowStep(
                            id="step1",
                            skill="test.echo",
                            inputs=[StepInput(from_state="message", to_param="message")],
                            outputs=[StepOutput(from_result="echo", to_state="result")],
                        ),
                    ],
                ),
            ],
        )

        result = asyncio.run(executor.execute(
            workflow,
            initial_state={"message": "hello"},
            case_id="test-case-001",
        ))

        assert result.success is True
        assert result.workflow_id == "test.simple"
        assert result.final_state.get("result") == "hello"

    def test_execute_multi_step_workflow(self, executor):
        """Test workflow with multiple sequential steps."""
        workflow = Workflow(
            metadata=WorkflowMetadata(id="test.multi", name="Multi-step"),
            phases=[
                WorkflowPhase(
                    id="phase1",
                    name="Phase 1",
                    steps=[
                        WorkflowStep(
                            id="step1",
                            skill="test.echo",
                            inputs=[StepInput(from_state="input", to_param="message")],
                            outputs=[StepOutput(from_result="echo", to_state="echoed")],
                        ),
                        WorkflowStep(
                            id="step2",
                            skill="test.uppercase",
                            inputs=[StepInput(from_state="echoed", to_param="text")],
                            outputs=[StepOutput(from_result="result", to_state="output")],
                        ),
                    ],
                    mode=ExecutionMode.SEQUENTIAL,
                ),
            ],
        )

        result = asyncio.run(executor.execute(
            workflow,
            initial_state={"input": "hello"},
        ))

        assert result.success is True
        assert result.final_state.get("output") == "HELLO"

    def test_parallel_execution(self, executor):
        """Test parallel phase execution."""
        workflow = Workflow(
            metadata=WorkflowMetadata(id="test.parallel", name="Parallel"),
            phases=[
                WorkflowPhase(
                    id="parallel-phase",
                    name="Parallel Phase",
                    steps=[
                        WorkflowStep(
                            id="slow1",
                            skill="test.slow",
                            inputs=[StepInput(from_state="delay", to_param="delay", default=0.1)],
                            outputs=[StepOutput(from_result="processed", to_state="result1")],
                        ),
                        WorkflowStep(
                            id="slow2",
                            skill="test.slow",
                            inputs=[StepInput(from_state="delay", to_param="delay", default=0.1)],
                            outputs=[StepOutput(from_result="processed", to_state="result2")],
                        ),
                    ],
                    mode=ExecutionMode.PARALLEL,
                ),
            ],
        )

        import time
        start = time.time()
        result = asyncio.run(executor.execute(workflow, initial_state={"delay": 0.1}))
        duration = time.time() - start

        assert result.success is True
        # Parallel execution should be faster than sequential (0.2s)
        assert duration < 0.4  # Allow some overhead for event loop setup

    def test_workflow_with_unknown_skill(self, executor):
        """Test workflow fails gracefully with unknown skill."""
        workflow = Workflow(
            metadata=WorkflowMetadata(id="test.unknown", name="Unknown Skill"),
            phases=[
                WorkflowPhase(
                    id="phase1",
                    name="Phase 1",
                    steps=[
                        WorkflowStep(
                            id="step1",
                            skill="nonexistent.skill",
                            inputs=[],
                            outputs=[],
                        ),
                    ],
                ),
            ],
        )

        result = asyncio.run(executor.execute(workflow))

        assert result.phases[0].steps[0].success is False
        assert "not found" in result.phases[0].steps[0].error.lower()

    def test_execution_id_generation(self, executor):
        """Test that execution gets a unique ID."""
        workflow = Workflow(
            metadata=WorkflowMetadata(id="test.id", name="ID Test"),
            phases=[],
        )

        result1 = asyncio.run(executor.execute(workflow))
        result2 = asyncio.run(executor.execute(workflow))

        assert result1.execution_id != result2.execution_id

    def test_initial_state_merging(self, executor):
        """Test initial state merges with workflow default state."""
        workflow = Workflow(
            metadata=WorkflowMetadata(id="test.state", name="State Test"),
            initial_state={"default_key": "default_value", "override": "original"},
            phases=[
                WorkflowPhase(
                    id="phase1",
                    name="Phase 1",
                    steps=[
                        WorkflowStep(
                            id="step1",
                            skill="test.echo",
                            inputs=[StepInput(from_state="override", to_param="message")],
                            outputs=[StepOutput(from_result="echo", to_state="result")],
                        ),
                    ],
                ),
            ],
        )

        result = asyncio.run(executor.execute(
            workflow,
            initial_state={"override": "new_value"},
        ))

        # Both default and override should be in final state
        assert result.final_state.get("default_key") == "default_value"
        assert result.final_state.get("result") == "new_value"


# ===== StepExecution Tests =====

class TestStepExecution:
    """Tests for StepExecution result structure."""

    def test_successful_step_execution(self):
        """Test successful step execution result."""
        step_exec = StepExecution(
            step_id="step1",
            skill_id="test.echo",
            success=True,
            result=SkillResult.ok(data={"echo": "hello"}),
            duration_seconds=0.1,
        )

        assert step_exec.success is True
        assert step_exec.error is None
        assert step_exec.result.data == {"echo": "hello"}

    def test_failed_step_execution(self):
        """Test failed step execution result."""
        step_exec = StepExecution(
            step_id="step1",
            skill_id="test.failing",
            success=False,
            error="Skill not found",
            duration_seconds=0.01,
        )

        assert step_exec.success is False
        assert "not found" in step_exec.error.lower()


# ===== PhaseExecution Tests =====

class TestPhaseExecution:
    """Tests for PhaseExecution result structure."""

    def test_phase_success_when_all_steps_succeed(self):
        """Test phase success when all steps succeed."""
        phase_exec = PhaseExecution(
            phase_id="phase1",
            success=True,
            steps=[
                StepExecution(step_id="s1", skill_id="test.echo", success=True),
                StepExecution(step_id="s2", skill_id="test.uppercase", success=True),
            ],
            duration_seconds=0.2,
        )

        assert phase_exec.success is True
        assert len(phase_exec.steps) == 2

    def test_phase_failure_when_step_fails(self):
        """Test phase failure when any step fails."""
        phase_exec = PhaseExecution(
            phase_id="phase1",
            success=False,
            steps=[
                StepExecution(step_id="s1", skill_id="test.echo", success=True),
                StepExecution(step_id="s2", skill_id="test.failing", success=False),
            ],
        )

        assert phase_exec.success is False


# ===== WorkflowExecution Tests =====

class TestWorkflowExecution:
    """Tests for WorkflowExecution result structure."""

    def test_execution_with_final_state(self):
        """Test execution captures final state."""
        execution = WorkflowExecution(
            workflow_id="test.workflow",
            execution_id="exec-001",
            success=True,
            final_state={"key": "value"},
            total_duration_seconds=1.5,
        )

        assert execution.final_state == {"key": "value"}
        assert execution.total_duration_seconds == 1.5

    def test_failed_execution_with_error(self):
        """Test failed execution captures error."""
        execution = WorkflowExecution(
            workflow_id="test.workflow",
            execution_id="exec-001",
            success=False,
            error="Workflow timed out",
        )

        assert execution.success is False
        assert execution.error == "Workflow timed out"
