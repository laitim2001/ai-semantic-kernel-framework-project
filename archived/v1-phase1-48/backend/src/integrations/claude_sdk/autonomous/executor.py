# =============================================================================
# IPA Platform - Plan Executor
# =============================================================================
# Sprint 79: S79-1 - Claude 自主規劃引擎 (13 pts)
#
# This module provides plan execution capabilities, including:
# - Step-by-step plan execution
# - Tool invocation and workflow orchestration
# - Failure handling and rollback
# - Progress tracking and event emission
# =============================================================================

import asyncio
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from .types import (
    AutonomousPlan,
    PlanStatus,
    PlanStep,
    StepStatus,
)

logger = logging.getLogger(__name__)


# Event types for execution progress
class ExecutionEventType:
    """Types of execution events."""

    PLAN_STARTED = "plan_started"
    STEP_STARTED = "step_started"
    STEP_PROGRESS = "step_progress"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    PLAN_COMPLETED = "plan_completed"
    PLAN_FAILED = "plan_failed"
    APPROVAL_REQUIRED = "approval_required"


class ExecutionEvent:
    """Event emitted during plan execution."""

    def __init__(
        self,
        event_type: str,
        plan_id: str,
        step_number: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        self.event_type = event_type
        self.plan_id = plan_id
        self.step_number = step_number
        self.data = data or {}
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for SSE streaming."""
        return {
            "event": self.event_type,
            "plan_id": self.plan_id,
            "step_number": self.step_number,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


# Type alias for tool executor functions
ToolExecutor = Callable[[str, Dict[str, Any]], Any]


class PlanExecutor:
    """
    Executes autonomous plans step by step.

    Handles tool invocation, failure recovery, and progress tracking.
    Supports streaming execution events for real-time UI updates.

    Example:
        executor = PlanExecutor(tool_executors)
        async for event in executor.execute_stream(plan):
            print(f"Step {event.step_number}: {event.event_type}")
    """

    def __init__(
        self,
        tool_executors: Optional[Dict[str, ToolExecutor]] = None,
        max_retries: int = 2,
        step_timeout: int = 300,
    ):
        """
        Initialize the PlanExecutor.

        Args:
            tool_executors: Map of tool names to executor functions
            max_retries: Maximum retries per step
            step_timeout: Timeout per step in seconds
        """
        self._tool_executors = tool_executors or {}
        self._max_retries = max_retries
        self._step_timeout = step_timeout
        self._approval_callbacks: Dict[str, Callable] = {}

    def register_tool(self, tool_name: str, executor: ToolExecutor):
        """Register a tool executor function."""
        self._tool_executors[tool_name] = executor

    def register_approval_callback(
        self, plan_id: str, callback: Callable[[int], bool]
    ):
        """Register a callback for approval requests."""
        self._approval_callbacks[plan_id] = callback

    async def execute(self, plan: AutonomousPlan) -> AutonomousPlan:
        """
        Execute a plan and return the updated plan.

        This is a blocking execution that waits for completion.

        Args:
            plan: The plan to execute

        Returns:
            Updated plan with execution results
        """
        async for _ in self.execute_stream(plan):
            pass  # Consume all events
        return plan

    async def execute_stream(
        self, plan: AutonomousPlan
    ) -> AsyncGenerator[ExecutionEvent, None]:
        """
        Execute a plan with streaming progress events.

        Args:
            plan: The plan to execute

        Yields:
            ExecutionEvent for each execution milestone
        """
        logger.info(f"Starting execution of plan {plan.id}")

        # Update plan status
        plan.status = PlanStatus.EXECUTING
        plan.started_at = datetime.utcnow()

        yield ExecutionEvent(
            ExecutionEventType.PLAN_STARTED,
            plan.id,
            data={"total_steps": len(plan.steps)},
        )

        try:
            # Execute each step
            for step in plan.steps:
                async for event in self._execute_step(plan, step):
                    yield event

                # Check if step failed and stop if critical
                if step.status == StepStatus.FAILED:
                    if not step.fallback_action:
                        logger.error(f"Step {step.step_number} failed without fallback")
                        raise Exception(f"Step {step.step_number} failed: {step.error}")

            # All steps completed
            plan.status = PlanStatus.VERIFYING
            plan.completed_at = datetime.utcnow()

            yield ExecutionEvent(
                ExecutionEventType.PLAN_COMPLETED,
                plan.id,
                data={
                    "duration_seconds": (
                        plan.completed_at - plan.started_at
                    ).total_seconds(),
                    "steps_completed": len(
                        [s for s in plan.steps if s.status == StepStatus.COMPLETED]
                    ),
                },
            )

        except Exception as e:
            logger.error(f"Plan execution failed: {e}")
            plan.status = PlanStatus.FAILED
            plan.error = str(e)
            plan.updated_at = datetime.utcnow()

            yield ExecutionEvent(
                ExecutionEventType.PLAN_FAILED,
                plan.id,
                data={"error": str(e)},
            )

    async def _execute_step(
        self, plan: AutonomousPlan, step: PlanStep
    ) -> AsyncGenerator[ExecutionEvent, None]:
        """Execute a single plan step."""
        logger.info(f"Executing step {step.step_number}: {step.action}")

        step.status = StepStatus.IN_PROGRESS
        step.started_at = datetime.utcnow()

        yield ExecutionEvent(
            ExecutionEventType.STEP_STARTED,
            plan.id,
            step.step_number,
            data={
                "action": step.action,
                "tool": step.tool_or_workflow,
            },
        )

        # Check if approval is required
        if step.requires_approval:
            approved = await self._request_approval(plan.id, step)
            if not approved:
                step.status = StepStatus.SKIPPED
                step.result = "Skipped - approval denied"
                yield ExecutionEvent(
                    ExecutionEventType.STEP_COMPLETED,
                    plan.id,
                    step.step_number,
                    data={"status": "skipped", "reason": "approval_denied"},
                )
                return

        # Execute with retries
        retries = 0
        last_error = None

        while retries <= self._max_retries:
            try:
                result = await self._invoke_tool(
                    step.tool_or_workflow,
                    step.parameters,
                )
                step.status = StepStatus.COMPLETED
                step.result = str(result)
                step.completed_at = datetime.utcnow()

                yield ExecutionEvent(
                    ExecutionEventType.STEP_COMPLETED,
                    plan.id,
                    step.step_number,
                    data={
                        "status": "completed",
                        "result": step.result[:500],  # Truncate for event
                        "duration_seconds": (
                            step.completed_at - step.started_at
                        ).total_seconds(),
                    },
                )
                return

            except Exception as e:
                last_error = e
                retries += 1
                logger.warning(
                    f"Step {step.step_number} failed (attempt {retries}): {e}"
                )

                if retries <= self._max_retries:
                    yield ExecutionEvent(
                        ExecutionEventType.STEP_PROGRESS,
                        plan.id,
                        step.step_number,
                        data={
                            "status": "retrying",
                            "attempt": retries,
                            "error": str(e),
                        },
                    )
                    await asyncio.sleep(2 ** retries)  # Exponential backoff

        # All retries exhausted
        step.status = StepStatus.FAILED
        step.error = str(last_error)
        step.completed_at = datetime.utcnow()

        # Try fallback if available
        if step.fallback_action:
            logger.info(f"Attempting fallback for step {step.step_number}")
            try:
                result = await self._execute_fallback(step)
                step.result = f"Fallback executed: {result}"
                step.status = StepStatus.COMPLETED

                yield ExecutionEvent(
                    ExecutionEventType.STEP_COMPLETED,
                    plan.id,
                    step.step_number,
                    data={
                        "status": "completed_with_fallback",
                        "result": step.result[:500],
                    },
                )
                return
            except Exception as e:
                logger.error(f"Fallback also failed: {e}")
                step.error = f"Primary: {last_error}, Fallback: {e}"

        yield ExecutionEvent(
            ExecutionEventType.STEP_FAILED,
            plan.id,
            step.step_number,
            data={"error": step.error},
        )

    async def _invoke_tool(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> Any:
        """Invoke a tool executor."""
        executor = self._tool_executors.get(tool_name)

        if executor is None:
            # Check for manual/placeholder tools
            if tool_name == "manual":
                return "Manual step - requires human action"

            raise ValueError(f"No executor registered for tool: {tool_name}")

        # Execute with timeout
        try:
            if asyncio.iscoroutinefunction(executor):
                result = await asyncio.wait_for(
                    executor(tool_name, parameters),
                    timeout=self._step_timeout,
                )
            else:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: executor(tool_name, parameters)
                )
            return result

        except asyncio.TimeoutError:
            raise TimeoutError(f"Tool {tool_name} timed out after {self._step_timeout}s")

    async def _execute_fallback(self, step: PlanStep) -> str:
        """Execute a fallback action."""
        if not step.fallback_action:
            raise ValueError("No fallback action defined")

        # Parse fallback action (format: "tool_name:action" or just description)
        if ":" in step.fallback_action:
            tool_name, action = step.fallback_action.split(":", 1)
            return await self._invoke_tool(tool_name, {"action": action})
        else:
            # Treat as manual fallback
            return f"Manual fallback required: {step.fallback_action}"

    async def _request_approval(self, plan_id: str, step: PlanStep) -> bool:
        """Request approval for a step."""
        callback = self._approval_callbacks.get(plan_id)

        if callback:
            return callback(step.step_number)

        # Default: auto-approve after logging
        logger.warning(
            f"Step {step.step_number} requires approval but no callback registered. "
            "Auto-approving."
        )
        return True

    async def cancel_execution(self, plan: AutonomousPlan) -> bool:
        """Cancel an executing plan."""
        if plan.status != PlanStatus.EXECUTING:
            return False

        plan.status = PlanStatus.CANCELLED
        plan.updated_at = datetime.utcnow()

        # Mark remaining steps as skipped
        for step in plan.steps:
            if step.status == StepStatus.PENDING:
                step.status = StepStatus.SKIPPED

        return True

    def get_execution_progress(self, plan: AutonomousPlan) -> Dict[str, Any]:
        """Get current execution progress."""
        total = len(plan.steps)
        completed = len([s for s in plan.steps if s.status == StepStatus.COMPLETED])
        failed = len([s for s in plan.steps if s.status == StepStatus.FAILED])
        in_progress = len([s for s in plan.steps if s.status == StepStatus.IN_PROGRESS])

        return {
            "total_steps": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": total - completed - failed - in_progress,
            "progress_percent": (completed / total * 100) if total > 0 else 0,
            "status": plan.status.value,
        }
