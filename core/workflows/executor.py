"""
Workflow Executor for running workflow definitions.

Executes workflows by:
1. Loading the workflow definition
2. Resolving skill references from the registry
3. Executing phases and steps according to the workflow
4. Managing state transitions and error handling
"""

from __future__ import annotations

import asyncio
import copy
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..skills import SkillRegistry, SkillContext, SkillResult, SkillNotFoundError
from .schema import (
    Workflow,
    WorkflowPhase,
    WorkflowStep,
    WorkflowState,
    ExecutionMode,
)

logger = logging.getLogger(__name__)


@dataclass
class StepExecution:
    """Result of a single step execution."""
    step_id: str
    skill_id: str
    success: bool
    result: Optional[SkillResult] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    refinement_count: int = 0


@dataclass
class PhaseExecution:
    """Result of a phase execution."""
    phase_id: str
    success: bool
    steps: list[StepExecution] = field(default_factory=list)
    duration_seconds: float = 0.0


@dataclass
class WorkflowExecution:
    """Complete workflow execution result."""
    workflow_id: str
    execution_id: str
    success: bool
    phases: list[PhaseExecution] = field(default_factory=list)
    final_state: WorkflowState = field(default_factory=dict)
    total_duration_seconds: float = 0.0
    error: Optional[str] = None


class WorkflowExecutor:
    """
    Executes workflow definitions using registered skills.

    Manages the full lifecycle of workflow execution including
    state management, parallel execution, and error handling.
    """

    def __init__(
        self,
        registry: Optional[SkillRegistry] = None,
        llm_gateway: Optional[Any] = None,
        database: Optional[Any] = None,
        notification_service: Optional[Any] = None,
    ):
        self.registry = registry or SkillRegistry.get_instance()
        self.llm_gateway = llm_gateway
        self.database = database
        self.notification_service = notification_service

    async def execute(
        self,
        workflow: Workflow,
        initial_state: Optional[WorkflowState] = None,
        case_id: Optional[str] = None,
    ) -> WorkflowExecution:
        """
        Execute a workflow.

        Args:
            workflow: The workflow definition to execute
            initial_state: Optional initial state (merged with workflow default)
            case_id: Optional case ID for context

        Returns:
            WorkflowExecution with results and final state
        """
        execution_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        logger.info(
            f"Starting workflow execution: {workflow.metadata.id} "
            f"(execution_id={execution_id}, case_id={case_id})"
        )

        # Initialize state
        state = copy.deepcopy(workflow.initial_state)
        if initial_state:
            state.update(initial_state)

        # Create execution context
        context = SkillContext(
            execution_id=execution_id,
            case_id=case_id,
            llm_gateway=self.llm_gateway,
            database=self.database,
            notification_service=self.notification_service,
            workflow_state=state,
        )

        # Execute phases
        phase_executions = []
        workflow_success = True
        workflow_error = None

        try:
            for phase in workflow.phases:
                phase_exec = await self._execute_phase(
                    phase, state, context
                )
                phase_executions.append(phase_exec)

                if not phase_exec.success:
                    workflow_success = False
                    # Continue to next phase or stop?
                    # For now, continue but mark as failed
                    logger.warning(
                        f"Phase {phase.id} failed, continuing with remaining phases"
                    )

        except asyncio.TimeoutError:
            workflow_success = False
            workflow_error = f"Workflow timed out after {workflow.timeout_seconds}s"
            logger.error(workflow_error)
        except Exception as e:
            workflow_success = False
            workflow_error = str(e)
            logger.error(f"Workflow execution failed: {e}", exc_info=True)

        total_duration = time.time() - start_time

        logger.info(
            f"Workflow execution complete: {workflow.metadata.id} "
            f"(success={workflow_success}, duration={total_duration:.2f}s)"
        )

        return WorkflowExecution(
            workflow_id=workflow.metadata.id,
            execution_id=execution_id,
            success=workflow_success,
            phases=phase_executions,
            final_state=state,
            total_duration_seconds=total_duration,
            error=workflow_error,
        )

    async def _execute_phase(
        self,
        phase: WorkflowPhase,
        state: WorkflowState,
        context: SkillContext,
    ) -> PhaseExecution:
        """Execute a single phase."""
        start_time = time.time()
        logger.info(f"Executing phase: {phase.id} ({phase.mode.value})")

        step_executions = []

        if phase.mode == ExecutionMode.PARALLEL:
            # Execute all steps in parallel
            tasks = [
                self._execute_step(step, state, context)
                for step in phase.steps
            ]
            step_executions = await asyncio.gather(*tasks)
        else:
            # Execute steps sequentially
            for step in phase.steps:
                step_exec = await self._execute_step(step, state, context)
                step_executions.append(step_exec)

                # Update context with new state
                context.workflow_state = state

        # Determine phase success
        phase_success = all(s.success for s in step_executions)

        return PhaseExecution(
            phase_id=phase.id,
            success=phase_success,
            steps=step_executions,
            duration_seconds=time.time() - start_time,
        )

    async def _execute_step(
        self,
        step: WorkflowStep,
        state: WorkflowState,
        context: SkillContext,
    ) -> StepExecution:
        """Execute a single step."""
        start_time = time.time()
        logger.debug(f"Executing step: {step.id} (skill={step.skill})")

        # Check condition
        if step.condition and not step.condition.evaluate({"state": state}):
            logger.debug(f"Step {step.id} skipped due to condition")
            return StepExecution(
                step_id=step.id,
                skill_id=step.skill,
                success=True,  # Skipped steps are considered successful
                duration_seconds=time.time() - start_time,
            )

        # Get skill
        try:
            skill = self.registry.get(step.skill)
        except SkillNotFoundError as e:
            logger.error(f"Skill not found for step {step.id}: {step.skill}")
            return StepExecution(
                step_id=step.id,
                skill_id=step.skill,
                success=False,
                error=str(e),
                duration_seconds=time.time() - start_time,
            )

        # Build input data from state
        input_data = self._build_input(step, state)

        # Execute with retry
        result = await self._execute_with_retry(
            skill, input_data, context, step
        )

        # Handle quality check and refinement
        refinement_count = 0
        if step.quality_check and step.quality_check.enabled and result.success:
            while refinement_count < step.quality_check.max_refinements:
                is_acceptable, feedback = self._check_quality(
                    result.data, step.quality_check.rules
                )
                if is_acceptable:
                    break

                logger.info(f"Step {step.id} quality check failed, refining...")
                # TODO: Implement refinement using skill.refine() if available
                refinement_count += 1

        # Update state with outputs
        if result.success and result.data:
            self._apply_outputs(step, result.data, state)

        return StepExecution(
            step_id=step.id,
            skill_id=step.skill,
            success=result.success,
            result=result,
            error=result.error,
            duration_seconds=time.time() - start_time,
            refinement_count=refinement_count,
        )

    async def _execute_with_retry(
        self,
        skill: Any,
        input_data: Any,
        context: SkillContext,
        step: WorkflowStep,
    ) -> SkillResult:
        """Execute skill with retry logic."""
        retry_config = step.retry
        max_attempts = retry_config.max_attempts if retry_config else 1

        last_result = None
        for attempt in range(max_attempts):
            try:
                # Run in executor to not block event loop
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: skill(input_data, context)
                    ),
                    timeout=step.timeout_seconds,
                )

                if result.success:
                    return result

                last_result = result

                # Check if error is retryable
                if retry_config and result.error:
                    is_retryable = any(
                        err in result.error.lower()
                        for err in retry_config.retryable_errors
                    )
                    if not is_retryable:
                        break

            except asyncio.TimeoutError:
                last_result = SkillResult.fail(
                    error=f"Step timed out after {step.timeout_seconds}s"
                )
            except Exception as e:
                last_result = SkillResult.fail(error=str(e))

            # Wait before retry
            if attempt < max_attempts - 1 and retry_config:
                wait_time = retry_config.backoff_seconds * (
                    retry_config.backoff_multiplier ** attempt
                )
                await asyncio.sleep(wait_time)

        return last_result or SkillResult.fail(error="Unknown error")

    def _build_input(
        self,
        step: WorkflowStep,
        state: WorkflowState,
    ) -> dict[str, Any]:
        """Build input data for a step from workflow state."""
        input_data = {}

        for inp in step.inputs:
            value = self._get_nested(state, inp.from_state)
            if value is None and inp.required and inp.default is None:
                logger.warning(
                    f"Required input {inp.from_state} not found in state "
                    f"for step {step.id}"
                )
            input_data[inp.to_param] = value if value is not None else inp.default

        return input_data

    def _apply_outputs(
        self,
        step: WorkflowStep,
        result_data: Any,
        state: WorkflowState,
    ) -> None:
        """Apply step outputs to workflow state."""
        for out in step.outputs:
            value = self._get_nested(
                result_data if isinstance(result_data, dict) else {"result": result_data},
                out.from_result
            )
            self._set_nested(state, out.to_state, value)

    def _get_nested(self, obj: dict, path: str) -> Any:
        """Get a nested value from a dict using dot notation."""
        current = obj
        for part in path.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None
        return current

    def _set_nested(self, obj: dict, path: str, value: Any) -> None:
        """Set a nested value in a dict using dot notation."""
        parts = path.split(".")
        current = obj
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    def _check_quality(
        self,
        data: Any,
        rules: list[dict[str, Any]],
    ) -> tuple[bool, str]:
        """
        Check data quality against rules.

        Returns:
            Tuple of (is_acceptable, feedback_message)
        """
        if not rules or not data:
            return True, ""

        issues = []
        for rule in rules:
            field = rule.get("field")
            value = self._get_nested(data, field) if field else None

            if "min_length" in rule:
                if not value or len(value) < rule["min_length"]:
                    issues.append(
                        f"Field '{field}' should have at least "
                        f"{rule['min_length']} items"
                    )

            if "required" in rule and rule["required"]:
                if not value:
                    issues.append(f"Field '{field}' is required but missing")

            if "min_value" in rule:
                if value is None or value < rule["min_value"]:
                    issues.append(
                        f"Field '{field}' should be at least {rule['min_value']}"
                    )

        if issues:
            return False, "\n".join(issues)
        return True, ""
