# =============================================================================
# IPA Platform - Deadlock Detection and Timeout Handling
# =============================================================================
# Sprint 7: Concurrent Execution Engine
# Phase 2 Feature: P2-F1 (Concurrent Execution)
#
# Deadlock detection and timeout handling for parallel execution:
#   - WaitingTask: Task waiting for dependencies
#   - DeadlockDetector: Cycle detection in wait-for graph
#   - TimeoutHandler: Task and execution timeout management
#   - DeadlockResolutionStrategy: Strategy for resolving deadlocks
#
# Uses Wait-for Graph with DFS cycle detection algorithm.
# =============================================================================

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID

logger = logging.getLogger(__name__)


class DeadlockResolutionStrategy(str, Enum):
    """
    Strategy for resolving detected deadlocks.

    Values:
        CANCEL_YOUNGEST: Cancel the most recently started task in the cycle
        CANCEL_OLDEST: Cancel the longest running task in the cycle
        CANCEL_ALL: Cancel all tasks in the deadlock cycle
        CANCEL_LOWEST_PRIORITY: Cancel the task with lowest priority
        NOTIFY_ONLY: Only notify, don't automatically cancel
    """

    CANCEL_YOUNGEST = "cancel_youngest"
    CANCEL_OLDEST = "cancel_oldest"
    CANCEL_ALL = "cancel_all"
    CANCEL_LOWEST_PRIORITY = "cancel_lowest_priority"
    NOTIFY_ONLY = "notify_only"


@dataclass
class WaitingTask:
    """
    A task waiting for other tasks to complete.

    Used to build the wait-for graph for deadlock detection.

    Attributes:
        task_id: Unique task identifier
        waiting_for: Set of task IDs this task is waiting for
        started_at: When the task started waiting
        timeout: Timeout in seconds for this wait
        priority: Task priority (higher = more important)
        metadata: Additional task information

    Example:
        task = WaitingTask(
            task_id="task-A",
            waiting_for={"task-B", "task-C"},
            started_at=datetime.utcnow(),
            timeout=60,
        )
    """

    task_id: str
    waiting_for: Set[str]
    started_at: datetime = field(default_factory=datetime.utcnow)
    timeout: int = 300  # Default 5 minutes
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time since task started waiting."""
        return (datetime.utcnow() - self.started_at).total_seconds()

    @property
    def is_timed_out(self) -> bool:
        """Check if task has exceeded timeout."""
        return self.elapsed_seconds > self.timeout

    @property
    def remaining_seconds(self) -> float:
        """Get remaining time before timeout."""
        return max(0, self.timeout - self.elapsed_seconds)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "waiting_for": list(self.waiting_for),
            "started_at": self.started_at.isoformat(),
            "timeout": self.timeout,
            "priority": self.priority,
            "elapsed_seconds": self.elapsed_seconds,
            "is_timed_out": self.is_timed_out,
            "metadata": self.metadata,
        }


@dataclass
class DeadlockInfo:
    """
    Information about a detected deadlock.

    Attributes:
        cycle: List of task IDs forming the cycle
        detected_at: When the deadlock was detected
        resolved: Whether the deadlock has been resolved
        resolution_action: Action taken to resolve
        cancelled_task: Task that was cancelled (if any)
    """

    cycle: List[str]
    detected_at: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolution_action: Optional[str] = None
    cancelled_task: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cycle": self.cycle,
            "detected_at": self.detected_at.isoformat(),
            "resolved": self.resolved,
            "resolution_action": self.resolution_action,
            "cancelled_task": self.cancelled_task,
        }


class DeadlockDetector:
    """
    Deadlock detector using Wait-for Graph analysis.

    Detects circular dependencies in task waiting relationships.
    Uses Depth-First Search (DFS) to find cycles in the wait-for graph.

    Features:
        - Register/unregister waiting tasks
        - Detect deadlock cycles using DFS
        - Identify timed out tasks
        - Continuous monitoring mode
        - Multiple resolution strategies

    Algorithm:
        1. Build wait-for graph from registered tasks
        2. Perform DFS traversal looking for back edges
        3. Back edge indicates a cycle (deadlock)
        4. Return the cycle path for resolution

    Example:
        detector = DeadlockDetector(check_interval=5)

        # Register waiting tasks
        detector.register_waiting("A", {"B"})
        detector.register_waiting("B", {"C"})
        detector.register_waiting("C", {"A"})  # Creates cycle!

        # Detect deadlock
        cycle = detector.detect_deadlock()
        # cycle = ["A", "B", "C"]

        # Start continuous monitoring
        await detector.start_monitoring(
            on_deadlock=handle_deadlock,
            on_timeout=handle_timeout,
        )
    """

    def __init__(
        self,
        check_interval: int = 5,
        resolution_strategy: DeadlockResolutionStrategy = DeadlockResolutionStrategy.CANCEL_YOUNGEST,
    ):
        """
        Initialize DeadlockDetector.

        Args:
            check_interval: Seconds between automatic checks
            resolution_strategy: Default strategy for resolving deadlocks
        """
        self._waiting_tasks: Dict[str, WaitingTask] = {}
        self._check_interval = check_interval
        self._resolution_strategy = resolution_strategy
        self._running = False
        self._deadlock_history: List[DeadlockInfo] = []

        logger.info(
            f"DeadlockDetector initialized: check_interval={check_interval}, "
            f"strategy={resolution_strategy.value}"
        )

    def register_waiting(
        self,
        task_id: str,
        waiting_for: Set[str],
        timeout: int = 300,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Register a task as waiting for other tasks.

        Args:
            task_id: Unique task identifier
            waiting_for: Set of task IDs this task depends on
            timeout: Timeout in seconds
            priority: Task priority (higher = more important)
            metadata: Additional task information
        """
        self._waiting_tasks[task_id] = WaitingTask(
            task_id=task_id,
            waiting_for=waiting_for,
            timeout=timeout,
            priority=priority,
            metadata=metadata or {},
        )

        logger.debug(
            f"Registered waiting task: {task_id} -> {waiting_for}, timeout={timeout}s"
        )

    def unregister(self, task_id: str) -> bool:
        """
        Unregister a task from waiting.

        Args:
            task_id: Task identifier to unregister

        Returns:
            True if task was found and removed
        """
        if task_id in self._waiting_tasks:
            del self._waiting_tasks[task_id]
            logger.debug(f"Unregistered task: {task_id}")
            return True
        return False

    def update_waiting_for(self, task_id: str, waiting_for: Set[str]) -> bool:
        """
        Update the dependencies of a waiting task.

        Args:
            task_id: Task identifier
            waiting_for: New set of dependencies

        Returns:
            True if task was found and updated
        """
        if task_id in self._waiting_tasks:
            self._waiting_tasks[task_id].waiting_for = waiting_for
            return True
        return False

    def remove_dependency(self, task_id: str, dependency_id: str) -> bool:
        """
        Remove a single dependency from a waiting task.

        Called when a dependency completes.

        Args:
            task_id: Task identifier
            dependency_id: Dependency that completed

        Returns:
            True if dependency was removed
        """
        if task_id in self._waiting_tasks:
            self._waiting_tasks[task_id].waiting_for.discard(dependency_id)

            # If no more dependencies, unregister
            if not self._waiting_tasks[task_id].waiting_for:
                self.unregister(task_id)
                return True
            return True
        return False

    def detect_deadlock(self) -> Optional[List[str]]:
        """
        Detect deadlock cycles in the wait-for graph.

        Uses DFS to find cycles. A cycle indicates a deadlock where
        tasks are waiting for each other in a circular dependency.

        Returns:
            List of task IDs forming the cycle, or None if no deadlock

        Algorithm:
            1. Build adjacency list from waiting tasks
            2. DFS traversal tracking visited and recursion stack
            3. Back edge (node already in rec stack) = cycle found
            4. Reconstruct cycle path from back edge
        """
        # Build wait-for graph
        graph: Dict[str, Set[str]] = {
            task_id: task.waiting_for.copy()
            for task_id, task in self._waiting_tasks.items()
        }

        if not graph:
            return None

        # DFS for cycle detection
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        parent: Dict[str, Optional[str]] = {}

        def dfs(node: str, path: List[str]) -> Optional[List[str]]:
            """DFS traversal looking for cycles."""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, set()):
                if neighbor not in visited:
                    parent[neighbor] = node
                    cycle = dfs(neighbor, path)
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Found cycle - reconstruct path
                    cycle_start_idx = path.index(neighbor)
                    return path[cycle_start_idx:]

            path.pop()
            rec_stack.remove(node)
            return None

        # Check all nodes (handles disconnected components)
        for node in graph:
            if node not in visited:
                cycle = dfs(node, [])
                if cycle:
                    logger.warning(f"Deadlock detected: {' -> '.join(cycle)}")
                    return cycle

        return None

    def get_timed_out_tasks(self) -> List[WaitingTask]:
        """
        Get all tasks that have exceeded their timeout.

        Returns:
            List of timed out WaitingTask objects
        """
        return [
            task for task in self._waiting_tasks.values()
            if task.is_timed_out
        ]

    def get_tasks_near_timeout(self, threshold_seconds: float = 30) -> List[WaitingTask]:
        """
        Get tasks within threshold of timeout.

        Args:
            threshold_seconds: Time threshold before timeout

        Returns:
            List of tasks near timeout
        """
        return [
            task for task in self._waiting_tasks.values()
            if 0 < task.remaining_seconds <= threshold_seconds
        ]

    async def start_monitoring(
        self,
        on_deadlock: Optional[Callable[[List[str]], Any]] = None,
        on_timeout: Optional[Callable[[WaitingTask], Any]] = None,
        on_near_timeout: Optional[Callable[[WaitingTask], Any]] = None,
    ) -> None:
        """
        Start continuous monitoring for deadlocks and timeouts.

        Args:
            on_deadlock: Async callback for deadlock detection
            on_timeout: Async callback for task timeout
            on_near_timeout: Async callback for near-timeout warning
        """
        self._running = True
        logger.info(f"Starting deadlock monitoring (interval={self._check_interval}s)")

        while self._running:
            try:
                # Check for deadlocks
                cycle = self.detect_deadlock()
                if cycle:
                    deadlock_info = DeadlockInfo(cycle=cycle)
                    self._deadlock_history.append(deadlock_info)

                    if on_deadlock:
                        await on_deadlock(cycle)

                    # Auto-resolve if not notify-only
                    if self._resolution_strategy != DeadlockResolutionStrategy.NOTIFY_ONLY:
                        await self._resolve_deadlock(cycle, deadlock_info)

                # Check for timeouts
                for task in self.get_timed_out_tasks():
                    if on_timeout:
                        await on_timeout(task)
                    self.unregister(task.task_id)

                # Check for near-timeouts
                if on_near_timeout:
                    for task in self.get_tasks_near_timeout():
                        await on_near_timeout(task)

            except Exception as e:
                logger.error(f"Error in deadlock monitoring: {e}")

            await asyncio.sleep(self._check_interval)

    def stop_monitoring(self) -> None:
        """Stop continuous monitoring."""
        self._running = False
        logger.info("Stopped deadlock monitoring")

    async def _resolve_deadlock(
        self,
        cycle: List[str],
        deadlock_info: DeadlockInfo,
    ) -> Optional[str]:
        """
        Resolve a deadlock according to configured strategy.

        Args:
            cycle: List of task IDs in the deadlock
            deadlock_info: DeadlockInfo object to update

        Returns:
            ID of cancelled task, or None
        """
        if not cycle:
            return None

        cancelled_task: Optional[str] = None

        if self._resolution_strategy == DeadlockResolutionStrategy.CANCEL_YOUNGEST:
            # Cancel most recently started task
            youngest = max(
                (self._waiting_tasks.get(tid) for tid in cycle if tid in self._waiting_tasks),
                key=lambda t: t.started_at if t else datetime.min,
                default=None,
            )
            if youngest:
                cancelled_task = youngest.task_id

        elif self._resolution_strategy == DeadlockResolutionStrategy.CANCEL_OLDEST:
            # Cancel longest running task
            oldest = min(
                (self._waiting_tasks.get(tid) for tid in cycle if tid in self._waiting_tasks),
                key=lambda t: t.started_at if t else datetime.max,
                default=None,
            )
            if oldest:
                cancelled_task = oldest.task_id

        elif self._resolution_strategy == DeadlockResolutionStrategy.CANCEL_LOWEST_PRIORITY:
            # Cancel lowest priority task
            lowest = min(
                (self._waiting_tasks.get(tid) for tid in cycle if tid in self._waiting_tasks),
                key=lambda t: t.priority if t else float('inf'),
                default=None,
            )
            if lowest:
                cancelled_task = lowest.task_id

        elif self._resolution_strategy == DeadlockResolutionStrategy.CANCEL_ALL:
            # Cancel all tasks in cycle
            for task_id in cycle:
                self.unregister(task_id)
            cancelled_task = ",".join(cycle)

        # Unregister cancelled task
        if cancelled_task and cancelled_task not in ",":
            self.unregister(cancelled_task)

        # Update deadlock info
        deadlock_info.resolved = True
        deadlock_info.resolution_action = self._resolution_strategy.value
        deadlock_info.cancelled_task = cancelled_task

        logger.info(f"Resolved deadlock: cancelled={cancelled_task}")
        return cancelled_task

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get detector statistics.

        Returns:
            Dictionary with detector statistics
        """
        return {
            "waiting_tasks": len(self._waiting_tasks),
            "timed_out_tasks": len(self.get_timed_out_tasks()),
            "deadlocks_detected": len(self._deadlock_history),
            "deadlocks_resolved": len([d for d in self._deadlock_history if d.resolved]),
            "is_monitoring": self._running,
        }

    def get_deadlock_history(self) -> List[DeadlockInfo]:
        """Get history of detected deadlocks."""
        return self._deadlock_history.copy()

    def clear_history(self) -> None:
        """Clear deadlock history."""
        self._deadlock_history.clear()

    def get_all_waiting_tasks(self) -> Dict[str, WaitingTask]:
        """Get all currently waiting tasks."""
        return self._waiting_tasks.copy()


class TimeoutHandler:
    """
    Handler for task and execution timeouts.

    Provides utilities for handling timeout scenarios in parallel execution,
    including cleanup, notification, and recovery.

    Example:
        handler = TimeoutHandler()

        result = await handler.handle_task_timeout(
            execution_id=uuid4(),
            task_id="slow-task",
            cleanup_fn=my_cleanup,
        )
    """

    @staticmethod
    async def handle_task_timeout(
        execution_id: UUID,
        task_id: str,
        cleanup_fn: Optional[Callable[[str], Any]] = None,
        notify_fn: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> Dict[str, Any]:
        """
        Handle a task timeout.

        Args:
            execution_id: Execution UUID
            task_id: Task that timed out
            cleanup_fn: Async function to clean up task resources
            notify_fn: Async function to send notifications

        Returns:
            Dictionary with timeout handling result
        """
        logger.warning(f"Handling task timeout: {task_id} in execution {execution_id}")

        result = {
            "execution_id": str(execution_id),
            "task_id": task_id,
            "status": "timeout",
            "handled_at": datetime.utcnow().isoformat(),
        }

        # Run cleanup
        if cleanup_fn:
            try:
                await cleanup_fn(task_id)
                result["cleanup_status"] = "success"
            except Exception as e:
                logger.error(f"Cleanup failed for task {task_id}: {e}")
                result["cleanup_status"] = "failed"
                result["cleanup_error"] = str(e)

        # Send notification
        if notify_fn:
            try:
                await notify_fn({
                    "type": "task_timeout",
                    "execution_id": str(execution_id),
                    "task_id": task_id,
                    "timestamp": datetime.utcnow().isoformat(),
                })
                result["notification_sent"] = True
            except Exception as e:
                logger.error(f"Notification failed for task {task_id}: {e}")
                result["notification_sent"] = False

        return result

    @staticmethod
    async def handle_execution_timeout(
        execution_id: UUID,
        cancel_fn: Optional[Callable[[], Any]] = None,
        cleanup_fn: Optional[Callable[[], Any]] = None,
    ) -> Dict[str, Any]:
        """
        Handle an entire execution timeout.

        Args:
            execution_id: Execution UUID
            cancel_fn: Async function to cancel running tasks
            cleanup_fn: Async function to clean up execution resources

        Returns:
            Dictionary with timeout handling result
        """
        logger.warning(f"Handling execution timeout: {execution_id}")

        result = {
            "execution_id": str(execution_id),
            "status": "execution_timeout",
            "handled_at": datetime.utcnow().isoformat(),
        }

        # Cancel running tasks
        if cancel_fn:
            try:
                await cancel_fn()
                result["tasks_cancelled"] = True
            except Exception as e:
                logger.error(f"Task cancellation failed: {e}")
                result["tasks_cancelled"] = False
                result["cancel_error"] = str(e)

        # Cleanup resources
        if cleanup_fn:
            try:
                await cleanup_fn()
                result["cleanup_status"] = "success"
            except Exception as e:
                logger.error(f"Execution cleanup failed: {e}")
                result["cleanup_status"] = "failed"
                result["cleanup_error"] = str(e)

        return result

    @staticmethod
    async def handle_deadlock(
        execution_id: UUID,
        cycle: List[str],
        resolution_strategy: DeadlockResolutionStrategy = DeadlockResolutionStrategy.CANCEL_YOUNGEST,
        cancel_fn: Optional[Callable[[str], Any]] = None,
    ) -> Dict[str, Any]:
        """
        Handle a detected deadlock.

        Args:
            execution_id: Execution UUID
            cycle: List of task IDs in the deadlock cycle
            resolution_strategy: Strategy for resolving
            cancel_fn: Async function to cancel a specific task

        Returns:
            Dictionary with deadlock handling result
        """
        logger.warning(
            f"Handling deadlock in execution {execution_id}: {' -> '.join(cycle)}"
        )

        result = {
            "execution_id": str(execution_id),
            "deadlock_detected": True,
            "cycle": cycle,
            "strategy": resolution_strategy.value,
            "handled_at": datetime.utcnow().isoformat(),
        }

        task_to_cancel: Optional[str] = None

        if resolution_strategy == DeadlockResolutionStrategy.CANCEL_YOUNGEST:
            task_to_cancel = cycle[-1] if cycle else None
        elif resolution_strategy == DeadlockResolutionStrategy.CANCEL_OLDEST:
            task_to_cancel = cycle[0] if cycle else None
        elif resolution_strategy == DeadlockResolutionStrategy.CANCEL_ALL:
            task_to_cancel = None  # Cancel all
        elif resolution_strategy == DeadlockResolutionStrategy.CANCEL_LOWEST_PRIORITY:
            task_to_cancel = cycle[-1] if cycle else None  # Default to youngest

        result["cancelled_task"] = task_to_cancel

        # Execute cancellation
        if cancel_fn:
            try:
                if resolution_strategy == DeadlockResolutionStrategy.CANCEL_ALL:
                    for task_id in cycle:
                        await cancel_fn(task_id)
                    result["tasks_cancelled"] = cycle
                elif task_to_cancel:
                    await cancel_fn(task_to_cancel)
                    result["cancel_status"] = "success"
            except Exception as e:
                logger.error(f"Deadlock resolution failed: {e}")
                result["cancel_status"] = "failed"
                result["cancel_error"] = str(e)

        return result


# Global detector instance
_detector: Optional[DeadlockDetector] = None


def get_deadlock_detector() -> DeadlockDetector:
    """Get global DeadlockDetector instance."""
    global _detector
    if _detector is None:
        _detector = DeadlockDetector()
    return _detector


def reset_deadlock_detector() -> None:
    """Reset global detector (for testing)."""
    global _detector
    if _detector:
        _detector.stop_monitoring()
    _detector = None
