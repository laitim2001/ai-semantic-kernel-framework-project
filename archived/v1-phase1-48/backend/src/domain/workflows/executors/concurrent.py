# =============================================================================
# IPA Platform - Concurrent Executor
# =============================================================================
# Sprint 7: Concurrent Execution Engine
# Phase 2 Feature: P2-F1 (Concurrent Execution)
#
# Concurrent executor for parallel agent execution with multiple modes:
#   - ALL: Wait for all tasks to complete
#   - ANY: Return when any task completes
#   - MAJORITY: Return when majority completes
#   - FIRST_SUCCESS: Return on first successful task
#
# Provides:
#   - ConcurrentMode: Execution mode enumeration
#   - ConcurrentTask: Task definition for concurrent execution
#   - ConcurrentResult: Result from concurrent task execution
#   - ConcurrentExecutor: Main executor for parallel tasks
# =============================================================================

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class ConcurrentMode(str, Enum):
    """
    Concurrent execution mode types.

    Determines how the executor handles multiple parallel tasks.

    Values:
        ALL: Wait for all tasks to complete before returning
        ANY: Return immediately when any single task completes
        MAJORITY: Return when more than half of tasks complete
        FIRST_SUCCESS: Return when first task succeeds (ignores failures)
    """

    ALL = "all"
    ANY = "any"
    MAJORITY = "majority"
    FIRST_SUCCESS = "first_success"


@dataclass
class ConcurrentTask:
    """
    Definition of a concurrent task to execute.

    Represents a single unit of work in a concurrent execution batch.
    Each task targets a specific executor (agent) with input data.

    Attributes:
        id: Unique identifier for this task within the batch
        executor_id: ID of the target executor/agent to run
        input_data: Input data to pass to the executor
        timeout: Task-specific timeout in seconds (optional)
        priority: Task priority (higher = more important)
        metadata: Additional task metadata

    Example:
        task = ConcurrentTask(
            id="analyze-financial",
            executor_id="financial-agent-001",
            input_data={"document": "Q3 Report", "type": "analysis"},
            timeout=60,
        )
    """

    id: str
    executor_id: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    timeout: Optional[int] = None
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for serialization."""
        return {
            "id": self.id,
            "executor_id": self.executor_id,
            "input_data": self.input_data,
            "timeout": self.timeout,
            "priority": self.priority,
            "metadata": self.metadata,
        }


@dataclass
class ConcurrentResult:
    """
    Result from a concurrent task execution.

    Contains the outcome of a single task in a concurrent batch,
    including success/failure status, result data, and timing.

    Attributes:
        task_id: ID of the task that produced this result
        success: Whether the task completed successfully
        result: Task result data (if successful)
        error: Error message (if failed)
        duration_ms: Task execution duration in milliseconds
        started_at: When the task started
        completed_at: When the task completed

    Example:
        result = ConcurrentResult(
            task_id="analyze-financial",
            success=True,
            result={"sentiment": "positive", "score": 0.85},
            duration_ms=1250,
        )
    """

    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class ConcurrentExecutor:
    """
    Concurrent executor for parallel task execution.

    Executes multiple tasks in parallel with different completion modes.
    Supports concurrency limiting, timeouts, and various merge strategies.

    Features:
        - Multiple execution modes (ALL, ANY, MAJORITY, FIRST_SUCCESS)
        - Semaphore-based concurrency control
        - Per-task and global timeout handling
        - Result aggregation and error tracking

    Lifecycle:
        1. __init__() - Configure executor with tasks and mode
        2. execute() - Run all tasks according to mode
        3. get_results() - Retrieve execution results

    Example:
        tasks = [
            ConcurrentTask(id="task1", executor_id="agent1"),
            ConcurrentTask(id="task2", executor_id="agent2"),
            ConcurrentTask(id="task3", executor_id="agent3"),
        ]

        executor = ConcurrentExecutor(
            id="parallel-analysis",
            tasks=tasks,
            mode=ConcurrentMode.ALL,
            max_concurrency=5,
            timeout=300,
        )

        results = await executor.execute(task_executor_fn)

    Args:
        id: Unique identifier for this executor instance
        tasks: List of tasks to execute concurrently
        mode: Execution mode determining completion behavior
        max_concurrency: Maximum number of concurrent tasks
        timeout: Global timeout for all tasks (seconds)
    """

    def __init__(
        self,
        id: str,
        tasks: List[ConcurrentTask],
        mode: ConcurrentMode = ConcurrentMode.ALL,
        max_concurrency: int = 10,
        timeout: int = 300,
    ):
        """
        Initialize ConcurrentExecutor.

        Args:
            id: Unique executor identifier
            tasks: Tasks to execute in parallel
            mode: Execution mode (ALL, ANY, MAJORITY, FIRST_SUCCESS)
            max_concurrency: Maximum parallel tasks (1-100)
            timeout: Global timeout in seconds (max 3600)
        """
        self._id = id
        self._tasks = tasks
        self._mode = mode
        self._max_concurrency = min(max(1, max_concurrency), 100)
        self._timeout = min(max(1, timeout), 3600)
        self._results: Dict[str, ConcurrentResult] = {}
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None

        logger.info(
            f"ConcurrentExecutor initialized: id={id}, tasks={len(tasks)}, "
            f"mode={mode.value}, max_concurrency={self._max_concurrency}"
        )

    @property
    def id(self) -> str:
        """Get executor ID."""
        return self._id

    @property
    def mode(self) -> ConcurrentMode:
        """Get execution mode."""
        return self._mode

    @property
    def tasks(self) -> List[ConcurrentTask]:
        """Get task list."""
        return self._tasks

    async def execute(
        self,
        task_executor: Callable[[ConcurrentTask], Any],
    ) -> Dict[str, Any]:
        """
        Execute all tasks according to the configured mode.

        Runs tasks in parallel with concurrency control and timeout handling.
        Results vary based on execution mode.

        Args:
            task_executor: Async function to execute each task
                Signature: async def executor(task: ConcurrentTask) -> Any

        Returns:
            Dictionary containing:
                - mode: Execution mode used
                - total_tasks: Number of tasks attempted
                - completed_tasks: Number successfully completed
                - failed_tasks: Number that failed
                - results: Dict of task_id -> result (successful only)
                - errors: Dict of task_id -> error (failed only)
                - duration_ms: Total execution duration

        Example:
            async def my_executor(task: ConcurrentTask) -> dict:
                return await agent_service.execute(task.executor_id, task.input_data)

            result = await concurrent_executor.execute(my_executor)
        """
        self._started_at = datetime.utcnow()
        logger.info(f"Starting concurrent execution: {self._id}, mode={self._mode.value}")

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self._max_concurrency)

        async def execute_single_task(task: ConcurrentTask) -> ConcurrentResult:
            """Execute a single task with semaphore and timeout control."""
            async with semaphore:
                task_start = datetime.utcnow()
                task_timeout = task.timeout or self._timeout

                try:
                    # Execute with timeout
                    result = await asyncio.wait_for(
                        task_executor(task),
                        timeout=task_timeout,
                    )

                    task_end = datetime.utcnow()
                    duration = int((task_end - task_start).total_seconds() * 1000)

                    logger.debug(f"Task {task.id} completed successfully in {duration}ms")

                    return ConcurrentResult(
                        task_id=task.id,
                        success=True,
                        result=result,
                        duration_ms=duration,
                        started_at=task_start,
                        completed_at=task_end,
                    )

                except asyncio.TimeoutError:
                    task_end = datetime.utcnow()
                    duration = int((task_end - task_start).total_seconds() * 1000)

                    logger.warning(f"Task {task.id} timeout after {task_timeout}s")

                    return ConcurrentResult(
                        task_id=task.id,
                        success=False,
                        error=f"Task timeout after {task_timeout} seconds",
                        duration_ms=duration,
                        started_at=task_start,
                        completed_at=task_end,
                    )

                except Exception as e:
                    task_end = datetime.utcnow()
                    duration = int((task_end - task_start).total_seconds() * 1000)

                    logger.error(f"Task {task.id} failed: {str(e)}")

                    return ConcurrentResult(
                        task_id=task.id,
                        success=False,
                        error=str(e),
                        duration_ms=duration,
                        started_at=task_start,
                        completed_at=task_end,
                    )

        # Execute based on mode
        if self._mode == ConcurrentMode.ALL:
            results = await self._execute_all(execute_single_task)
        elif self._mode == ConcurrentMode.ANY:
            results = await self._execute_any(execute_single_task)
        elif self._mode == ConcurrentMode.FIRST_SUCCESS:
            results = await self._execute_first_success(execute_single_task)
        elif self._mode == ConcurrentMode.MAJORITY:
            results = await self._execute_majority(execute_single_task)
        else:
            # Default to ALL mode
            results = await self._execute_all(execute_single_task)

        # Store results
        self._results = {r.task_id: r for r in results}
        self._completed_at = datetime.utcnow()

        total_duration = int(
            (self._completed_at - self._started_at).total_seconds() * 1000
        )

        logger.info(
            f"Concurrent execution completed: {self._id}, "
            f"total={len(self._tasks)}, completed={len([r for r in results if r.success])}, "
            f"failed={len([r for r in results if not r.success])}, duration={total_duration}ms"
        )

        # Build output
        return {
            "mode": self._mode.value,
            "total_tasks": len(self._tasks),
            "completed_tasks": len([r for r in results if r.success]),
            "failed_tasks": len([r for r in results if not r.success]),
            "results": {r.task_id: r.result for r in results if r.success},
            "errors": {r.task_id: r.error for r in results if not r.success},
            "duration_ms": total_duration,
        }

    async def _execute_all(
        self,
        execute_fn: Callable[[ConcurrentTask], ConcurrentResult],
    ) -> List[ConcurrentResult]:
        """
        Execute all tasks and wait for completion.

        All tasks run in parallel (limited by semaphore) and results
        are collected when all have completed.

        Args:
            execute_fn: Function to execute each task

        Returns:
            List of all task results
        """
        logger.debug(f"Executing ALL mode with {len(self._tasks)} tasks")
        coroutines = [execute_fn(task) for task in self._tasks]
        return await asyncio.gather(*coroutines)

    async def _execute_any(
        self,
        execute_fn: Callable[[ConcurrentTask], ConcurrentResult],
    ) -> List[ConcurrentResult]:
        """
        Execute tasks and return when any completes.

        Returns immediately when the first task completes (success or failure).
        Cancels remaining tasks.

        Args:
            execute_fn: Function to execute each task

        Returns:
            List containing the first completed result
        """
        logger.debug(f"Executing ANY mode with {len(self._tasks)} tasks")

        tasks = [asyncio.create_task(execute_fn(task)) for task in self._tasks]

        try:
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel pending tasks
            for task in pending:
                task.cancel()

            # Wait for cancellation to complete
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)

            return [task.result() for task in done]

        except Exception as e:
            logger.error(f"Error in ANY mode execution: {e}")
            # Cancel all tasks on error
            for task in tasks:
                task.cancel()
            raise

    async def _execute_first_success(
        self,
        execute_fn: Callable[[ConcurrentTask], ConcurrentResult],
    ) -> List[ConcurrentResult]:
        """
        Execute tasks and return when first succeeds.

        Continues executing until a successful result is found.
        Cancels remaining tasks after first success.

        Args:
            execute_fn: Function to execute each task

        Returns:
            List of results including first successful one
        """
        logger.debug(f"Executing FIRST_SUCCESS mode with {len(self._tasks)} tasks")

        tasks = [asyncio.create_task(execute_fn(task)) for task in self._tasks]
        results: List[ConcurrentResult] = []

        try:
            while tasks:
                done, pending = await asyncio.wait(
                    tasks,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for completed_task in done:
                    result = completed_task.result()
                    results.append(result)

                    if result.success:
                        # Found success, cancel remaining tasks
                        logger.debug(f"First success found: {result.task_id}")
                        for task in pending:
                            task.cancel()

                        if pending:
                            await asyncio.gather(*pending, return_exceptions=True)

                        return results

                tasks = list(pending)

            return results

        except Exception as e:
            logger.error(f"Error in FIRST_SUCCESS mode execution: {e}")
            for task in tasks:
                task.cancel()
            raise

    async def _execute_majority(
        self,
        execute_fn: Callable[[ConcurrentTask], ConcurrentResult],
    ) -> List[ConcurrentResult]:
        """
        Execute tasks and return when majority completes.

        Returns when more than half of tasks have completed.
        Cancels remaining tasks after majority threshold reached.

        Args:
            execute_fn: Function to execute each task

        Returns:
            List of results from majority of tasks
        """
        majority_count = len(self._tasks) // 2 + 1
        logger.debug(
            f"Executing MAJORITY mode with {len(self._tasks)} tasks, "
            f"need {majority_count} to complete"
        )

        tasks = [asyncio.create_task(execute_fn(task)) for task in self._tasks]
        results: List[ConcurrentResult] = []

        try:
            while len(results) < majority_count and tasks:
                done, pending = await asyncio.wait(
                    tasks,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for completed_task in done:
                    results.append(completed_task.result())

                tasks = list(pending)

            # Cancel remaining tasks
            for task in tasks:
                task.cancel()

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            return results

        except Exception as e:
            logger.error(f"Error in MAJORITY mode execution: {e}")
            for task in tasks:
                task.cancel()
            raise

    def get_results(self) -> Dict[str, ConcurrentResult]:
        """
        Get all execution results.

        Returns:
            Dictionary mapping task_id to ConcurrentResult
        """
        return self._results

    def get_successful_results(self) -> Dict[str, Any]:
        """
        Get only successful results.

        Returns:
            Dictionary mapping task_id to result data
        """
        return {
            task_id: result.result
            for task_id, result in self._results.items()
            if result.success
        }

    def get_failed_results(self) -> Dict[str, str]:
        """
        Get only failed results.

        Returns:
            Dictionary mapping task_id to error message
        """
        return {
            task_id: result.error or "Unknown error"
            for task_id, result in self._results.items()
            if not result.success
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert executor state to dictionary for serialization."""
        return {
            "id": self._id,
            "mode": self._mode.value,
            "tasks": [task.to_dict() for task in self._tasks],
            "max_concurrency": self._max_concurrency,
            "timeout": self._timeout,
            "results": {
                task_id: result.to_dict()
                for task_id, result in self._results.items()
            },
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "completed_at": self._completed_at.isoformat() if self._completed_at else None,
        }


# Convenience factory functions
def create_all_executor(
    id: str,
    tasks: List[ConcurrentTask],
    **kwargs,
) -> ConcurrentExecutor:
    """Create executor in ALL mode."""
    return ConcurrentExecutor(id=id, tasks=tasks, mode=ConcurrentMode.ALL, **kwargs)


def create_any_executor(
    id: str,
    tasks: List[ConcurrentTask],
    **kwargs,
) -> ConcurrentExecutor:
    """Create executor in ANY mode."""
    return ConcurrentExecutor(id=id, tasks=tasks, mode=ConcurrentMode.ANY, **kwargs)


def create_majority_executor(
    id: str,
    tasks: List[ConcurrentTask],
    **kwargs,
) -> ConcurrentExecutor:
    """Create executor in MAJORITY mode."""
    return ConcurrentExecutor(id=id, tasks=tasks, mode=ConcurrentMode.MAJORITY, **kwargs)


def create_first_success_executor(
    id: str,
    tasks: List[ConcurrentTask],
    **kwargs,
) -> ConcurrentExecutor:
    """Create executor in FIRST_SUCCESS mode."""
    return ConcurrentExecutor(
        id=id, tasks=tasks, mode=ConcurrentMode.FIRST_SUCCESS, **kwargs
    )
