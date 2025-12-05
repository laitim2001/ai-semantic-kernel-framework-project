# =============================================================================
# ConcurrentExecutor Migration Layer
# =============================================================================
# Sprint 14: ConcurrentBuilder 重構
# Phase 3 Feature: P3-F1 (並行執行重構)
#
# 此模組提供從 Phase 2 ConcurrentExecutor 到 Agent Framework
# ConcurrentBuilderAdapter 的遷移層，確保向後兼容。
#
# 遷移策略:
#   - 保留原始 API 簽名
#   - 內部使用 ConcurrentBuilderAdapter
#   - 自動轉換數據結構
#
# 使用範例:
#   # 原有代碼
#   from domain.workflows.executors.concurrent import (
#       ConcurrentExecutor, ConcurrentTask, ConcurrentMode
#   )
#
#   # 遷移後
#   from integrations.agent_framework.builders.concurrent_migration import (
#       ConcurrentExecutorAdapter, ConcurrentTask, ConcurrentMode
#   )
#
#   # API 完全兼容
#   executor = ConcurrentExecutorAdapter(
#       id="parallel-tasks",
#       tasks=[task1, task2],
#       mode=ConcurrentMode.ALL,
#   )
#   result = await executor.execute(task_executor_fn)
# =============================================================================

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import UUID

from .concurrent import (
    ConcurrentBuilderAdapter,
    ConcurrentMode as AdapterConcurrentMode,
    ConcurrentTaskConfig,
    TaskResult,
    ConcurrentExecutionResult,
)

logger = logging.getLogger(__name__)


# =============================================================================
# 兼容層 - 維持 Phase 2 API
# =============================================================================


class ConcurrentMode(str, Enum):
    """
    Concurrent execution mode types (Phase 2 兼容).

    此枚舉與 Phase 2 完全兼容，內部映射到 AdapterConcurrentMode。

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

    def to_adapter_mode(self) -> AdapterConcurrentMode:
        """Convert to adapter ConcurrentMode."""
        return AdapterConcurrentMode(self.value)


@dataclass
class ConcurrentTask:
    """
    Definition of a concurrent task to execute (Phase 2 兼容).

    與 Phase 2 ConcurrentTask 完全兼容，可自動轉換為 ConcurrentTaskConfig。

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
            input_data={"document": "Q3 Report"},
            timeout=60,
        )
    """

    id: str
    executor_id: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    timeout: Optional[int] = None
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_task_config(self) -> ConcurrentTaskConfig:
        """Convert to ConcurrentTaskConfig for adapter."""
        return ConcurrentTaskConfig(
            id=self.id,
            timeout_seconds=float(self.timeout) if self.timeout else None,
            metadata={
                "executor_id": self.executor_id,
                "priority": self.priority,
                **self.metadata,
            },
        )

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
    Result from a concurrent task execution (Phase 2 兼容).

    與 Phase 2 ConcurrentResult 完全兼容。

    Attributes:
        task_id: ID of the task that produced this result
        success: Whether the task completed successfully
        result: Task result data (if successful)
        error: Error message (if failed)
        duration_ms: Task execution duration in milliseconds
        started_at: When the task started
        completed_at: When the task completed
    """

    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @classmethod
    def from_task_result(cls, task_result: TaskResult) -> "ConcurrentResult":
        """Create from adapter TaskResult."""
        return cls(
            task_id=task_result.task_id,
            success=task_result.success,
            result=task_result.result,
            error=task_result.error,
            duration_ms=int(task_result.duration_ms),
            started_at=task_result.started_at,
            completed_at=task_result.completed_at,
        )

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


# =============================================================================
# 狀態管理 - BranchStatus 和 ParallelBranch
# =============================================================================


class BranchStatus(str, Enum):
    """
    Status of a parallel execution branch.

    Tracks the lifecycle of each branch in a parallel execution.

    Values:
        PENDING: Branch created but not yet started
        RUNNING: Branch currently executing
        COMPLETED: Branch finished successfully
        FAILED: Branch encountered an error
        CANCELLED: Branch was cancelled (timeout or parent cancellation)
        TIMEOUT: Branch exceeded timeout limit
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class ParallelBranch:
    """
    State of a single parallel execution branch.

    Tracks execution status, timing, and results for one branch
    in a parallel workflow execution.

    Attributes:
        id: Unique branch identifier
        executor_id: ID of the executor/agent running this branch
        status: Current branch status
        started_at: When execution started
        completed_at: When execution ended
        result: Execution result data (if completed)
        error: Error message (if failed)
        metadata: Additional branch metadata
    """

    id: str
    executor_id: str
    status: BranchStatus = BranchStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def mark_started(self) -> None:
        """Mark branch as started."""
        self.status = BranchStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)

    def mark_completed(self, result: Any) -> None:
        """Mark branch as completed with result."""
        self.status = BranchStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.result = result

    def mark_failed(self, error: str) -> None:
        """Mark branch as failed with error."""
        self.status = BranchStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error = error

    def mark_cancelled(self) -> None:
        """Mark branch as cancelled."""
        self.status = BranchStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc)

    def mark_timeout(self) -> None:
        """Mark branch as timed out."""
        self.status = BranchStatus.TIMEOUT
        self.completed_at = datetime.now(timezone.utc)
        self.error = "Branch execution timed out"

    @property
    def is_terminal(self) -> bool:
        """Check if branch is in a terminal state."""
        return self.status in {
            BranchStatus.COMPLETED,
            BranchStatus.FAILED,
            BranchStatus.CANCELLED,
            BranchStatus.TIMEOUT,
        }

    @property
    def is_successful(self) -> bool:
        """Check if branch completed successfully."""
        return self.status == BranchStatus.COMPLETED

    @property
    def duration_ms(self) -> Optional[int]:
        """Get execution duration in milliseconds."""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds() * 1000)
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert branch to dictionary for serialization."""
        return {
            "id": self.id,
            "executor_id": self.executor_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


# =============================================================================
# ConcurrentExecutorAdapter - 主要遷移適配器
# =============================================================================


class ConcurrentExecutorAdapter:
    """
    Adapter that provides Phase 2 ConcurrentExecutor API using ConcurrentBuilderAdapter.

    此類提供與 Phase 2 ConcurrentExecutor 完全兼容的 API，
    但內部使用 ConcurrentBuilderAdapter 執行。

    Features:
        - Multiple execution modes (ALL, ANY, MAJORITY, FIRST_SUCCESS)
        - Semaphore-based concurrency control
        - Per-task and global timeout handling
        - Result aggregation and error tracking
        - State management with BranchStatus tracking

    Lifecycle:
        1. __init__() - Configure executor with tasks and mode
        2. execute() - Run all tasks according to mode
        3. get_results() - Retrieve execution results

    Example:
        # 與 Phase 2 完全兼容的用法
        tasks = [
            ConcurrentTask(id="task1", executor_id="agent1"),
            ConcurrentTask(id="task2", executor_id="agent2"),
        ]

        executor = ConcurrentExecutorAdapter(
            id="parallel-analysis",
            tasks=tasks,
            mode=ConcurrentMode.ALL,
            max_concurrency=5,
            timeout=300,
        )

        results = await executor.execute(task_executor_fn)

    Migration Notes:
        - 直接替換 ConcurrentExecutor 為 ConcurrentExecutorAdapter
        - API 簽名完全相同
        - 返回格式完全相同
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
        Initialize ConcurrentExecutorAdapter.

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
        self._branches: Dict[str, ParallelBranch] = {}
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None

        # Initialize branches for state tracking
        for task in tasks:
            self._branches[task.id] = ParallelBranch(
                id=task.id,
                executor_id=task.executor_id,
                metadata=task.metadata,
            )

        # Create the underlying adapter
        self._adapter = ConcurrentBuilderAdapter(
            id=id,
            mode=mode.to_adapter_mode(),
            max_concurrency=self._max_concurrency,
            timeout_seconds=float(self._timeout),
        )

        logger.info(
            f"ConcurrentExecutorAdapter initialized: id={id}, tasks={len(tasks)}, "
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
        self._started_at = datetime.now(timezone.utc)
        logger.info(f"Starting concurrent execution: {self._id}, mode={self._mode.value}")

        # Create wrapper executors for each task
        task_executors: Dict[str, Callable] = {}
        for task in self._tasks:
            # Mark branch as started
            self._branches[task.id].mark_started()

            # Create a wrapper that captures the task context
            async def create_task_wrapper(t: ConcurrentTask):
                async def wrapper(input_data: Any) -> Any:
                    # Pass both the task and input to the original executor
                    return await task_executor(t)
                return wrapper

            wrapper = await create_task_wrapper(task)
            self._adapter.add_executor(wrapper, task_id=task.id)
            task_executors[task.id] = wrapper

        # Run through adapter
        adapter_result = await self._adapter.run(None)

        # Convert results back to Phase 2 format
        self._completed_at = datetime.now(timezone.utc)
        total_duration = int(
            (self._completed_at - self._started_at).total_seconds() * 1000
        )

        # Process task results and update branches
        results_dict: Dict[str, Any] = {}
        errors_dict: Dict[str, str] = {}

        for task_result in adapter_result.task_results:
            concurrent_result = ConcurrentResult.from_task_result(task_result)
            self._results[task_result.task_id] = concurrent_result

            # Update branch status
            branch = self._branches.get(task_result.task_id)
            if branch:
                if task_result.success:
                    branch.mark_completed(task_result.result)
                    results_dict[task_result.task_id] = task_result.result
                else:
                    if "timeout" in (task_result.error or "").lower():
                        branch.mark_timeout()
                    else:
                        branch.mark_failed(task_result.error or "Unknown error")
                    errors_dict[task_result.task_id] = task_result.error or "Unknown error"

        logger.info(
            f"Concurrent execution completed: {self._id}, "
            f"total={len(self._tasks)}, completed={adapter_result.completed_count}, "
            f"failed={adapter_result.failed_count}, duration={total_duration}ms"
        )

        # Return Phase 2 compatible format
        return {
            "mode": self._mode.value,
            "total_tasks": len(self._tasks),
            "completed_tasks": adapter_result.completed_count,
            "failed_tasks": adapter_result.failed_count,
            "results": results_dict,
            "errors": errors_dict,
            "duration_ms": total_duration,
        }

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

    def get_branch(self, branch_id: str) -> Optional[ParallelBranch]:
        """Get branch state by ID."""
        return self._branches.get(branch_id)

    def get_all_branches(self) -> List[ParallelBranch]:
        """Get all branch states."""
        return list(self._branches.values())

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
            "branches": {
                branch_id: branch.to_dict()
                for branch_id, branch in self._branches.items()
            },
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "completed_at": self._completed_at.isoformat() if self._completed_at else None,
        }


# =============================================================================
# Convenience Factory Functions
# =============================================================================


def create_all_executor(
    id: str,
    tasks: List[ConcurrentTask],
    **kwargs,
) -> ConcurrentExecutorAdapter:
    """Create executor in ALL mode."""
    return ConcurrentExecutorAdapter(id=id, tasks=tasks, mode=ConcurrentMode.ALL, **kwargs)


def create_any_executor(
    id: str,
    tasks: List[ConcurrentTask],
    **kwargs,
) -> ConcurrentExecutorAdapter:
    """Create executor in ANY mode."""
    return ConcurrentExecutorAdapter(id=id, tasks=tasks, mode=ConcurrentMode.ANY, **kwargs)


def create_majority_executor(
    id: str,
    tasks: List[ConcurrentTask],
    **kwargs,
) -> ConcurrentExecutorAdapter:
    """Create executor in MAJORITY mode."""
    return ConcurrentExecutorAdapter(id=id, tasks=tasks, mode=ConcurrentMode.MAJORITY, **kwargs)


def create_first_success_executor(
    id: str,
    tasks: List[ConcurrentTask],
    **kwargs,
) -> ConcurrentExecutorAdapter:
    """Create executor in FIRST_SUCCESS mode."""
    return ConcurrentExecutorAdapter(
        id=id, tasks=tasks, mode=ConcurrentMode.FIRST_SUCCESS, **kwargs
    )


# =============================================================================
# Migration Helpers
# =============================================================================


def migrate_concurrent_executor(
    old_executor_config: Dict[str, Any],
) -> ConcurrentExecutorAdapter:
    """
    Migrate existing ConcurrentExecutor configuration to adapter.

    Args:
        old_executor_config: Configuration dictionary from Phase 2 executor

    Returns:
        Configured ConcurrentExecutorAdapter

    Example:
        old_config = {
            "id": "parallel-1",
            "tasks": [...],
            "mode": "all",
            "max_concurrency": 10,
            "timeout": 300,
        }
        new_executor = migrate_concurrent_executor(old_config)
    """
    tasks = [
        ConcurrentTask(
            id=t["id"],
            executor_id=t["executor_id"],
            input_data=t.get("input_data", {}),
            timeout=t.get("timeout"),
            priority=t.get("priority", 0),
            metadata=t.get("metadata", {}),
        )
        for t in old_executor_config.get("tasks", [])
    ]

    return ConcurrentExecutorAdapter(
        id=old_executor_config["id"],
        tasks=tasks,
        mode=ConcurrentMode(old_executor_config.get("mode", "all")),
        max_concurrency=old_executor_config.get("max_concurrency", 10),
        timeout=old_executor_config.get("timeout", 300),
    )


__all__ = [
    # Core classes
    "ConcurrentMode",
    "ConcurrentTask",
    "ConcurrentResult",
    "ConcurrentExecutorAdapter",
    # State management
    "BranchStatus",
    "ParallelBranch",
    # Factory functions
    "create_all_executor",
    "create_any_executor",
    "create_majority_executor",
    "create_first_success_executor",
    # Migration helpers
    "migrate_concurrent_executor",
]
