# =============================================================================
# IPA Platform - Sub-Workflow Executor
# =============================================================================
# Sprint 11: S11-2 SubWorkflowExecutor
#
# Handles sub-workflow execution with multiple modes:
# - Synchronous execution (blocking)
# - Asynchronous execution (non-blocking)
# - Fire-and-forget execution
# - Callback-based execution
# =============================================================================

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, Awaitable, List, Protocol
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class SubWorkflowExecutionMode(str, Enum):
    """
    子工作流執行模式

    Execution modes for sub-workflows:
    - SYNC: Synchronous, waits for completion
    - ASYNC: Asynchronous, returns immediately
    - FIRE_AND_FORGET: No tracking, fire and forget
    - CALLBACK: Executes callback on completion
    """
    SYNC = "sync"
    ASYNC = "async"
    FIRE_AND_FORGET = "fire_and_forget"
    CALLBACK = "callback"


# =============================================================================
# Protocols
# =============================================================================


class WorkflowEngineProtocol(Protocol):
    """Protocol for workflow engine dependency."""

    async def execute(
        self,
        workflow_id: UUID,
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a workflow."""
        ...


class CheckpointServiceProtocol(Protocol):
    """Protocol for checkpoint service dependency."""

    async def save_checkpoint(
        self,
        execution_id: UUID,
        state: Dict[str, Any]
    ) -> None:
        """Save execution checkpoint."""
        ...


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class SubExecutionState:
    """
    子執行狀態

    Tracks the state of a sub-workflow execution including
    status, result, error, and callback information.
    """
    execution_id: UUID
    sub_workflow_id: UUID
    mode: SubWorkflowExecutionMode
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "execution_id": str(self.execution_id),
            "sub_workflow_id": str(self.sub_workflow_id),
            "mode": self.mode.value,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
        }


# =============================================================================
# Sub-Workflow Executor
# =============================================================================


class SubWorkflowExecutor:
    """
    子工作流執行器

    Executes sub-workflows with support for multiple execution modes,
    parallel and sequential execution, status tracking, and cancellation.
    """

    def __init__(
        self,
        workflow_engine: Optional[WorkflowEngineProtocol] = None,
        checkpoint_service: Optional[CheckpointServiceProtocol] = None,
        max_concurrent: int = 10,
        default_timeout: float = 600.0
    ):
        """
        Initialize SubWorkflowExecutor.

        Args:
            workflow_engine: Engine for workflow execution
            checkpoint_service: Service for checkpointing
            max_concurrent: Maximum concurrent executions
            default_timeout: Default timeout in seconds
        """
        self.workflow_engine = workflow_engine
        self.checkpoint_service = checkpoint_service
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout

        # Execution state tracking
        self._executions: Dict[UUID, SubExecutionState] = {}

        # Async tasks for tracking
        self._async_tasks: Dict[UUID, asyncio.Task] = {}

        # Semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(max_concurrent)

    # =========================================================================
    # Main Execution Methods
    # =========================================================================

    async def execute(
        self,
        sub_workflow_id: UUID,
        inputs: Dict[str, Any],
        mode: SubWorkflowExecutionMode = SubWorkflowExecutionMode.SYNC,
        callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        執行子工作流

        Execute a sub-workflow with specified mode.

        Args:
            sub_workflow_id: Sub-workflow ID to execute
            inputs: Input parameters
            mode: Execution mode
            callback: Completion callback (for CALLBACK mode)
            timeout: Execution timeout in seconds
            metadata: Additional metadata

        Returns:
            Execution result (SYNC) or execution info (ASYNC/FIRE_AND_FORGET/CALLBACK)
        """
        execution_id = uuid4()
        timeout = timeout or self.default_timeout

        state = SubExecutionState(
            execution_id=execution_id,
            sub_workflow_id=sub_workflow_id,
            mode=mode,
            callback=callback,
            metadata=metadata or {},
        )
        self._executions[execution_id] = state

        logger.info(f"Starting sub-workflow execution {execution_id} in {mode.value} mode")

        if mode == SubWorkflowExecutionMode.SYNC:
            return await self._execute_sync(state, inputs, timeout)

        elif mode == SubWorkflowExecutionMode.ASYNC:
            task = asyncio.create_task(
                self._execute_async(state, inputs, timeout)
            )
            self._async_tasks[execution_id] = task
            return {
                "execution_id": str(execution_id),
                "status": "started",
                "mode": mode.value,
            }

        elif mode == SubWorkflowExecutionMode.FIRE_AND_FORGET:
            asyncio.create_task(self._execute_fire_forget(state, inputs, timeout))
            return {
                "execution_id": str(execution_id),
                "status": "dispatched",
                "mode": mode.value,
            }

        elif mode == SubWorkflowExecutionMode.CALLBACK:
            if not callback:
                raise ValueError("Callback mode requires a callback function")
            task = asyncio.create_task(
                self._execute_with_callback(state, inputs, timeout)
            )
            self._async_tasks[execution_id] = task
            return {
                "execution_id": str(execution_id),
                "status": "started",
                "mode": mode.value,
            }

        else:
            raise ValueError(f"Unknown execution mode: {mode}")

    async def _execute_sync(
        self,
        state: SubExecutionState,
        inputs: Dict[str, Any],
        timeout: float
    ) -> Dict[str, Any]:
        """
        同步執行

        Execute sub-workflow synchronously, waiting for completion.
        """
        async with self._semaphore:
            state.status = "running"
            state.started_at = datetime.utcnow()

            try:
                if self.workflow_engine:
                    result = await asyncio.wait_for(
                        self.workflow_engine.execute(
                            workflow_id=state.sub_workflow_id,
                            inputs=inputs
                        ),
                        timeout=timeout
                    )
                else:
                    # Mock execution without engine
                    await asyncio.sleep(0.1)  # Simulate work
                    result = {
                        "status": "completed",
                        "workflow_id": str(state.sub_workflow_id),
                        "inputs": inputs,
                        "mock": True,
                    }

                state.status = "completed"
                state.result = result
                state.completed_at = datetime.utcnow()

                logger.info(f"Sub-workflow {state.execution_id} completed successfully")
                return result

            except asyncio.TimeoutError:
                state.status = "timeout"
                state.error = f"Execution timed out after {timeout}s"
                state.completed_at = datetime.utcnow()
                raise

            except Exception as e:
                state.status = "failed"
                state.error = str(e)
                state.completed_at = datetime.utcnow()
                logger.error(f"Sub-workflow {state.execution_id} failed: {e}")
                raise

    async def _execute_async(
        self,
        state: SubExecutionState,
        inputs: Dict[str, Any],
        timeout: float
    ) -> None:
        """
        異步執行

        Execute sub-workflow asynchronously without blocking.
        """
        try:
            await self._execute_sync(state, inputs, timeout)
        except Exception as e:
            logger.error(f"Async execution {state.execution_id} error: {e}")

    async def _execute_fire_forget(
        self,
        state: SubExecutionState,
        inputs: Dict[str, Any],
        timeout: float
    ) -> None:
        """
        發射即忘執行

        Execute and don't track result (fire and forget).
        """
        try:
            await self._execute_sync(state, inputs, timeout)
        except Exception as e:
            # Log but don't propagate
            logger.warning(f"Fire-and-forget execution {state.execution_id} error: {e}")

    async def _execute_with_callback(
        self,
        state: SubExecutionState,
        inputs: Dict[str, Any],
        timeout: float
    ) -> None:
        """
        帶回調的執行

        Execute and invoke callback on completion or error.
        """
        try:
            result = await self._execute_sync(state, inputs, timeout)
            if state.callback:
                await state.callback(result)
        except Exception as e:
            if state.callback:
                await state.callback({"error": str(e), "status": "failed"})

    # =========================================================================
    # Batch Execution
    # =========================================================================

    async def execute_parallel(
        self,
        sub_workflows: List[Dict[str, Any]],
        timeout: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        並行執行多個子工作流

        Execute multiple sub-workflows in parallel.

        Args:
            sub_workflows: List of sub-workflow configs
                [{"id": UUID, "inputs": {...}}, ...]
            timeout: Timeout for each execution

        Returns:
            List of execution results
        """
        timeout = timeout or self.default_timeout
        tasks = []

        for sw in sub_workflows:
            state = SubExecutionState(
                execution_id=uuid4(),
                sub_workflow_id=sw["id"] if isinstance(sw["id"], UUID) else UUID(str(sw["id"])),
                mode=SubWorkflowExecutionMode.SYNC,
            )
            self._executions[state.execution_id] = state

            task = self._execute_sync(state, sw.get("inputs", {}), timeout)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [
            result if not isinstance(result, Exception)
            else {"error": str(result), "status": "failed"}
            for result in results
        ]

    async def execute_sequential(
        self,
        sub_workflows: List[Dict[str, Any]],
        pass_outputs: bool = True,
        stop_on_error: bool = True,
        timeout: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        順序執行多個子工作流

        Execute multiple sub-workflows sequentially.

        Args:
            sub_workflows: List of sub-workflow configs
            pass_outputs: Pass previous output to next input
            stop_on_error: Stop execution on error
            timeout: Timeout for each execution

        Returns:
            List of execution results
        """
        timeout = timeout or self.default_timeout
        results: List[Dict[str, Any]] = []
        previous_output: Dict[str, Any] = {}

        for sw in sub_workflows:
            inputs = sw.get("inputs", {})
            if pass_outputs:
                inputs = {**previous_output, **inputs}

            state = SubExecutionState(
                execution_id=uuid4(),
                sub_workflow_id=sw["id"] if isinstance(sw["id"], UUID) else UUID(str(sw["id"])),
                mode=SubWorkflowExecutionMode.SYNC,
            )
            self._executions[state.execution_id] = state

            try:
                result = await self._execute_sync(state, inputs, timeout)
                results.append(result)
                previous_output = result
            except Exception as e:
                results.append({"error": str(e), "status": "failed"})
                if stop_on_error:
                    break

        return results

    # =========================================================================
    # Status and Management
    # =========================================================================

    async def get_execution_status(
        self,
        execution_id: UUID
    ) -> Dict[str, Any]:
        """
        獲取執行狀態

        Get the status of an execution.

        Args:
            execution_id: Execution ID

        Returns:
            Execution status information
        """
        state = self._executions.get(execution_id)
        if not state:
            return {"error": "Execution not found", "execution_id": str(execution_id)}

        return state.to_dict()

    async def wait_for_completion(
        self,
        execution_id: UUID,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        等待執行完成

        Wait for an async execution to complete.

        Args:
            execution_id: Execution ID
            timeout: Wait timeout

        Returns:
            Execution result or status
        """
        task = self._async_tasks.get(execution_id)
        if not task:
            state = self._executions.get(execution_id)
            if state and state.status in ["completed", "failed", "timeout"]:
                return state.to_dict()
            return {"error": "Execution not found or not async"}

        try:
            await asyncio.wait_for(task, timeout=timeout)
        except asyncio.TimeoutError:
            return {"error": "Wait timeout", "status": "running"}

        return await self.get_execution_status(execution_id)

    async def cancel_execution(
        self,
        execution_id: UUID
    ) -> bool:
        """
        取消執行

        Cancel an execution.

        Args:
            execution_id: Execution ID

        Returns:
            True if cancelled successfully
        """
        task = self._async_tasks.get(execution_id)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

            state = self._executions.get(execution_id)
            if state:
                state.status = "cancelled"
                state.completed_at = datetime.utcnow()

            del self._async_tasks[execution_id]
            logger.info(f"Cancelled execution {execution_id}")
            return True

        return False

    def get_active_executions(self) -> List[Dict[str, Any]]:
        """
        獲取活躍執行列表

        Get list of all active (running) executions.
        """
        return [
            state.to_dict()
            for state in self._executions.values()
            if state.status == "running"
        ]

    def get_all_executions(
        self,
        status_filter: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        獲取所有執行

        Get all executions with optional filtering.

        Args:
            status_filter: Filter by status
            limit: Maximum number to return

        Returns:
            List of execution states
        """
        executions = list(self._executions.values())

        if status_filter:
            executions = [e for e in executions if e.status == status_filter]

        # Sort by started_at descending
        executions.sort(
            key=lambda e: e.started_at or datetime.min,
            reverse=True
        )

        return [e.to_dict() for e in executions[:limit]]

    def clear_completed(
        self,
        older_than_seconds: int = 3600
    ) -> int:
        """
        清理已完成的執行

        Clear completed executions older than threshold.

        Args:
            older_than_seconds: Age threshold

        Returns:
            Number of executions cleared
        """
        now = datetime.utcnow()
        to_remove = []

        for exec_id, state in self._executions.items():
            if state.status in ["completed", "failed", "cancelled", "timeout"]:
                if state.completed_at:
                    age = (now - state.completed_at).total_seconds()
                    if age > older_than_seconds:
                        to_remove.append(exec_id)

        for exec_id in to_remove:
            del self._executions[exec_id]
            self._async_tasks.pop(exec_id, None)

        return len(to_remove)

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """
        獲取統計信息

        Get executor statistics.
        """
        total = len(self._executions)
        by_status = {}
        by_mode = {}
        total_duration = 0.0
        completed_count = 0

        for state in self._executions.values():
            # By status
            by_status[state.status] = by_status.get(state.status, 0) + 1

            # By mode
            mode_val = state.mode.value
            by_mode[mode_val] = by_mode.get(mode_val, 0) + 1

            # Duration calculation
            if state.completed_at and state.started_at:
                duration = (state.completed_at - state.started_at).total_seconds()
                total_duration += duration
                completed_count += 1

        avg_duration = total_duration / completed_count if completed_count > 0 else 0

        return {
            "total_executions": total,
            "active_tasks": len(self._async_tasks),
            "by_status": by_status,
            "by_mode": by_mode,
            "average_duration_seconds": round(avg_duration, 2),
            "max_concurrent": self.max_concurrent,
            "default_timeout": self.default_timeout,
        }
