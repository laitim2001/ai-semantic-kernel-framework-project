"""
Agent Swarm State Tracker

This module provides the SwarmTracker class for managing the state of
multi-agent swarm executions. It supports thread-safe operations and
optional Redis persistence.
"""

import threading
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .models import (
    AgentSwarmStatus,
    SwarmMode,
    SwarmStatus,
    ThinkingContent,
    ToolCallInfo,
    ToolCallStatus,
    WorkerExecution,
    WorkerMessage,
    WorkerStatus,
    WorkerType,
)


class SwarmNotFoundError(Exception):
    """Raised when a swarm is not found."""
    pass


class WorkerNotFoundError(Exception):
    """Raised when a worker is not found."""
    pass


class ToolCallNotFoundError(Exception):
    """Raised when a tool call is not found."""
    pass


class SwarmTracker:
    """Agent Swarm state tracker.

    Manages the lifecycle and state of multi-agent swarm executions.
    Provides thread-safe operations for creating, updating, and querying
    swarm and worker states.

    Attributes:
        use_redis: Whether to use Redis for persistence.

    Example:
        tracker = SwarmTracker()

        # Create a swarm
        swarm = tracker.create_swarm("swarm-1", SwarmMode.PARALLEL)

        # Start workers
        tracker.start_worker("swarm-1", "w1", "Research", WorkerType.RESEARCH, "Gatherer")
        tracker.start_worker("swarm-1", "w2", "Writer", WorkerType.WRITER, "Content Creator")

        # Update progress
        tracker.update_worker_progress("swarm-1", "w1", 50)

        # Complete
        tracker.complete_worker("swarm-1", "w1")
        tracker.complete_swarm("swarm-1")
    """

    def __init__(
        self,
        use_redis: bool = False,
        redis_client: Optional[Any] = None,
        on_swarm_update: Optional[Callable[[AgentSwarmStatus], None]] = None,
        on_worker_update: Optional[Callable[[str, WorkerExecution], None]] = None,
    ):
        """Initialize the SwarmTracker.

        Args:
            use_redis: Whether to use Redis for persistence.
            redis_client: Optional Redis client instance.
            on_swarm_update: Callback when swarm state changes.
            on_worker_update: Callback when worker state changes.
        """
        self._swarms: Dict[str, AgentSwarmStatus] = {}
        self._lock = threading.RLock()
        self._use_redis = use_redis
        self._redis_client = redis_client
        self._on_swarm_update = on_swarm_update
        self._on_worker_update = on_worker_update

        if use_redis and redis_client is None:
            raise ValueError("Redis client required when use_redis=True")

    def _notify_swarm_update(self, swarm: AgentSwarmStatus) -> None:
        """Notify listeners of swarm state change."""
        if self._on_swarm_update:
            try:
                self._on_swarm_update(swarm)
            except Exception:
                pass  # Don't let callback errors affect tracker

    def _notify_worker_update(self, swarm_id: str, worker: WorkerExecution) -> None:
        """Notify listeners of worker state change."""
        if self._on_worker_update:
            try:
                self._on_worker_update(swarm_id, worker)
            except Exception:
                pass  # Don't let callback errors affect tracker

    def _save_to_redis(self, swarm: AgentSwarmStatus) -> None:
        """Save swarm state to Redis."""
        if self._use_redis and self._redis_client:
            key = f"swarm:{swarm.swarm_id}"
            self._redis_client.set(key, swarm.to_json())

    def _load_from_redis(self, swarm_id: str) -> Optional[AgentSwarmStatus]:
        """Load swarm state from Redis."""
        if self._use_redis and self._redis_client:
            key = f"swarm:{swarm_id}"
            data = self._redis_client.get(key)
            if data:
                return AgentSwarmStatus.from_json(data)
        return None

    def create_swarm(
        self,
        swarm_id: str,
        mode: SwarmMode,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentSwarmStatus:
        """Create a new swarm.

        Args:
            swarm_id: Unique identifier for the swarm.
            mode: Execution mode (sequential, parallel, hierarchical).
            metadata: Optional additional metadata.

        Returns:
            The created AgentSwarmStatus.
        """
        with self._lock:
            swarm = AgentSwarmStatus(
                swarm_id=swarm_id,
                mode=mode,
                status=SwarmStatus.INITIALIZING,
                overall_progress=0,
                workers=[],
                total_tool_calls=0,
                completed_tool_calls=0,
                started_at=datetime.now(),
                metadata=metadata or {},
            )
            self._swarms[swarm_id] = swarm
            self._save_to_redis(swarm)
            self._notify_swarm_update(swarm)
            return swarm

    def get_swarm(self, swarm_id: str) -> Optional[AgentSwarmStatus]:
        """Get swarm status by ID.

        Args:
            swarm_id: The swarm identifier.

        Returns:
            The AgentSwarmStatus if found, None otherwise.
        """
        with self._lock:
            swarm = self._swarms.get(swarm_id)
            if swarm is None and self._use_redis:
                swarm = self._load_from_redis(swarm_id)
                if swarm:
                    self._swarms[swarm_id] = swarm
            return swarm

    def _get_swarm_or_raise(self, swarm_id: str) -> AgentSwarmStatus:
        """Get swarm or raise error if not found."""
        swarm = self.get_swarm(swarm_id)
        if swarm is None:
            raise SwarmNotFoundError(f"Swarm not found: {swarm_id}")
        return swarm

    def _get_worker_or_raise(
        self, swarm: AgentSwarmStatus, worker_id: str
    ) -> WorkerExecution:
        """Get worker from swarm or raise error if not found."""
        worker = swarm.get_worker_by_id(worker_id)
        if worker is None:
            raise WorkerNotFoundError(f"Worker not found: {worker_id}")
        return worker

    def complete_swarm(
        self,
        swarm_id: str,
        status: SwarmStatus = SwarmStatus.COMPLETED,
    ) -> AgentSwarmStatus:
        """Mark a swarm as completed.

        Args:
            swarm_id: The swarm identifier.
            status: Final status (COMPLETED or FAILED).

        Returns:
            The updated AgentSwarmStatus.

        Raises:
            SwarmNotFoundError: If swarm not found.
        """
        with self._lock:
            swarm = self._get_swarm_or_raise(swarm_id)
            swarm.status = status
            swarm.completed_at = datetime.now()
            swarm.overall_progress = 100 if status == SwarmStatus.COMPLETED else swarm.overall_progress
            self._save_to_redis(swarm)
            self._notify_swarm_update(swarm)
            return swarm

    def update_swarm_status(
        self,
        swarm_id: str,
        status: SwarmStatus,
    ) -> AgentSwarmStatus:
        """Update swarm status.

        Args:
            swarm_id: The swarm identifier.
            status: New status.

        Returns:
            The updated AgentSwarmStatus.
        """
        with self._lock:
            swarm = self._get_swarm_or_raise(swarm_id)
            swarm.status = status
            self._save_to_redis(swarm)
            self._notify_swarm_update(swarm)
            return swarm

    def start_worker(
        self,
        swarm_id: str,
        worker_id: str,
        worker_name: str,
        worker_type: WorkerType,
        role: str,
        current_task: Optional[str] = None,
    ) -> WorkerExecution:
        """Start a new worker in the swarm.

        Args:
            swarm_id: The swarm identifier.
            worker_id: Unique identifier for the worker.
            worker_name: Display name of the worker.
            worker_type: Type of the worker.
            role: Role description.
            current_task: Optional initial task description.

        Returns:
            The created WorkerExecution.

        Raises:
            SwarmNotFoundError: If swarm not found.
        """
        with self._lock:
            swarm = self._get_swarm_or_raise(swarm_id)

            # Update swarm status to running if initializing
            if swarm.status == SwarmStatus.INITIALIZING:
                swarm.status = SwarmStatus.RUNNING

            worker = WorkerExecution(
                worker_id=worker_id,
                worker_name=worker_name,
                worker_type=worker_type,
                role=role,
                status=WorkerStatus.RUNNING,
                progress=0,
                current_task=current_task,
                started_at=datetime.now(),
            )
            swarm.workers.append(worker)
            self._save_to_redis(swarm)
            self._notify_worker_update(swarm_id, worker)
            self._notify_swarm_update(swarm)
            return worker

    def update_worker_progress(
        self,
        swarm_id: str,
        worker_id: str,
        progress: int,
        current_task: Optional[str] = None,
    ) -> WorkerExecution:
        """Update worker progress.

        Args:
            swarm_id: The swarm identifier.
            worker_id: The worker identifier.
            progress: Progress percentage (0-100).
            current_task: Optional updated task description.

        Returns:
            The updated WorkerExecution.

        Raises:
            SwarmNotFoundError: If swarm not found.
            WorkerNotFoundError: If worker not found.
        """
        with self._lock:
            swarm = self._get_swarm_or_raise(swarm_id)
            worker = self._get_worker_or_raise(swarm, worker_id)

            worker.progress = max(0, min(100, progress))
            if current_task is not None:
                worker.current_task = current_task

            # Recalculate overall progress
            swarm.overall_progress = self._calculate_progress(swarm)
            self._save_to_redis(swarm)
            self._notify_worker_update(swarm_id, worker)
            return worker

    def update_worker_status(
        self,
        swarm_id: str,
        worker_id: str,
        status: WorkerStatus,
    ) -> WorkerExecution:
        """Update worker status.

        Args:
            swarm_id: The swarm identifier.
            worker_id: The worker identifier.
            status: New status.

        Returns:
            The updated WorkerExecution.
        """
        with self._lock:
            swarm = self._get_swarm_or_raise(swarm_id)
            worker = self._get_worker_or_raise(swarm, worker_id)

            worker.status = status
            self._save_to_redis(swarm)
            self._notify_worker_update(swarm_id, worker)
            return worker

    def add_worker_thinking(
        self,
        swarm_id: str,
        worker_id: str,
        content: str,
        token_count: Optional[int] = None,
    ) -> ThinkingContent:
        """Add extended thinking content to a worker.

        Args:
            swarm_id: The swarm identifier.
            worker_id: The worker identifier.
            content: The thinking content.
            token_count: Optional token count.

        Returns:
            The created ThinkingContent.

        Raises:
            SwarmNotFoundError: If swarm not found.
            WorkerNotFoundError: If worker not found.
        """
        with self._lock:
            swarm = self._get_swarm_or_raise(swarm_id)
            worker = self._get_worker_or_raise(swarm, worker_id)

            # Update worker status to thinking
            worker.status = WorkerStatus.THINKING

            thinking = ThinkingContent(
                content=content,
                timestamp=datetime.now(),
                token_count=token_count,
            )
            worker.thinking_contents.append(thinking)
            self._save_to_redis(swarm)
            self._notify_worker_update(swarm_id, worker)
            return thinking

    def add_worker_tool_call(
        self,
        swarm_id: str,
        worker_id: str,
        tool_id: str,
        tool_name: str,
        is_mcp: bool,
        input_params: Dict[str, Any],
    ) -> ToolCallInfo:
        """Add a tool call to a worker.

        Args:
            swarm_id: The swarm identifier.
            worker_id: The worker identifier.
            tool_id: Unique identifier for this tool call.
            tool_name: Name of the tool.
            is_mcp: Whether this is an MCP tool.
            input_params: Tool input parameters.

        Returns:
            The created ToolCallInfo.

        Raises:
            SwarmNotFoundError: If swarm not found.
            WorkerNotFoundError: If worker not found.
        """
        with self._lock:
            swarm = self._get_swarm_or_raise(swarm_id)
            worker = self._get_worker_or_raise(swarm, worker_id)

            # Update worker status
            worker.status = WorkerStatus.TOOL_CALLING

            tool_call = ToolCallInfo(
                tool_id=tool_id,
                tool_name=tool_name,
                is_mcp=is_mcp,
                input_params=input_params,
                status=ToolCallStatus.RUNNING.value,
                started_at=datetime.now(),
            )
            worker.tool_calls.append(tool_call)
            swarm.total_tool_calls += 1
            self._save_to_redis(swarm)
            self._notify_worker_update(swarm_id, worker)
            return tool_call

    def update_tool_call_result(
        self,
        swarm_id: str,
        worker_id: str,
        tool_id: str,
        result: Any = None,
        error: Optional[str] = None,
    ) -> ToolCallInfo:
        """Update tool call with result or error.

        Args:
            swarm_id: The swarm identifier.
            worker_id: The worker identifier.
            tool_id: The tool call identifier.
            result: Tool execution result.
            error: Error message if failed.

        Returns:
            The updated ToolCallInfo.

        Raises:
            SwarmNotFoundError: If swarm not found.
            WorkerNotFoundError: If worker not found.
            ToolCallNotFoundError: If tool call not found.
        """
        with self._lock:
            swarm = self._get_swarm_or_raise(swarm_id)
            worker = self._get_worker_or_raise(swarm, worker_id)

            # Find tool call
            tool_call = None
            for tc in worker.tool_calls:
                if tc.tool_id == tool_id:
                    tool_call = tc
                    break

            if tool_call is None:
                raise ToolCallNotFoundError(f"Tool call not found: {tool_id}")

            tool_call.completed_at = datetime.now()
            if tool_call.started_at:
                tool_call.duration_ms = int(
                    (tool_call.completed_at - tool_call.started_at).total_seconds() * 1000
                )

            if error:
                tool_call.status = ToolCallStatus.FAILED.value
                tool_call.error = error
            else:
                tool_call.status = ToolCallStatus.COMPLETED.value
                tool_call.result = result
                swarm.completed_tool_calls += 1

            # Reset worker status to running
            worker.status = WorkerStatus.RUNNING
            self._save_to_redis(swarm)
            self._notify_worker_update(swarm_id, worker)
            return tool_call

    def add_worker_message(
        self,
        swarm_id: str,
        worker_id: str,
        role: str,
        content: str,
    ) -> WorkerMessage:
        """Add a message to worker's conversation history.

        Args:
            swarm_id: The swarm identifier.
            worker_id: The worker identifier.
            role: Message role (user, assistant).
            content: Message content.

        Returns:
            The created WorkerMessage.

        Raises:
            SwarmNotFoundError: If swarm not found.
            WorkerNotFoundError: If worker not found.
        """
        with self._lock:
            swarm = self._get_swarm_or_raise(swarm_id)
            worker = self._get_worker_or_raise(swarm, worker_id)

            message = WorkerMessage(
                role=role,
                content=content,
                timestamp=datetime.now(),
            )
            worker.messages.append(message)
            self._save_to_redis(swarm)
            self._notify_worker_update(swarm_id, worker)
            return message

    def complete_worker(
        self,
        swarm_id: str,
        worker_id: str,
        status: WorkerStatus = WorkerStatus.COMPLETED,
        error: Optional[str] = None,
    ) -> WorkerExecution:
        """Mark a worker as completed.

        Args:
            swarm_id: The swarm identifier.
            worker_id: The worker identifier.
            status: Final status (COMPLETED or FAILED).
            error: Error message if failed.

        Returns:
            The updated WorkerExecution.

        Raises:
            SwarmNotFoundError: If swarm not found.
            WorkerNotFoundError: If worker not found.
        """
        with self._lock:
            swarm = self._get_swarm_or_raise(swarm_id)
            worker = self._get_worker_or_raise(swarm, worker_id)

            worker.status = status
            worker.completed_at = datetime.now()
            if status == WorkerStatus.COMPLETED:
                worker.progress = 100
            if error:
                worker.error = error

            # Recalculate overall progress
            swarm.overall_progress = self._calculate_progress(swarm)
            self._save_to_redis(swarm)
            self._notify_worker_update(swarm_id, worker)
            self._notify_swarm_update(swarm)
            return worker

    def get_worker(
        self,
        swarm_id: str,
        worker_id: str,
    ) -> Optional[WorkerExecution]:
        """Get a specific worker from a swarm.

        Args:
            swarm_id: The swarm identifier.
            worker_id: The worker identifier.

        Returns:
            The WorkerExecution if found, None otherwise.
        """
        with self._lock:
            swarm = self.get_swarm(swarm_id)
            if swarm is None:
                return None
            return swarm.get_worker_by_id(worker_id)

    def get_all_workers(self, swarm_id: str) -> List[WorkerExecution]:
        """Get all workers in a swarm.

        Args:
            swarm_id: The swarm identifier.

        Returns:
            List of WorkerExecution objects.
        """
        with self._lock:
            swarm = self.get_swarm(swarm_id)
            if swarm is None:
                return []
            return swarm.workers

    def calculate_overall_progress(self, swarm_id: str) -> int:
        """Calculate and return the overall swarm progress.

        Args:
            swarm_id: The swarm identifier.

        Returns:
            Progress percentage (0-100).
        """
        with self._lock:
            swarm = self.get_swarm(swarm_id)
            if swarm is None:
                return 0
            return self._calculate_progress(swarm)

    def _calculate_progress(self, swarm: AgentSwarmStatus) -> int:
        """Calculate progress for a swarm.

        Progress is calculated as the average of all worker progresses.
        """
        if not swarm.workers:
            return 0

        total_progress = sum(w.progress for w in swarm.workers)
        return total_progress // len(swarm.workers)

    def delete_swarm(self, swarm_id: str) -> bool:
        """Delete a swarm from the tracker.

        Args:
            swarm_id: The swarm identifier.

        Returns:
            True if deleted, False if not found.
        """
        with self._lock:
            if swarm_id in self._swarms:
                del self._swarms[swarm_id]
                if self._use_redis and self._redis_client:
                    self._redis_client.delete(f"swarm:{swarm_id}")
                return True
            return False

    def list_swarms(self) -> List[AgentSwarmStatus]:
        """List all tracked swarms.

        Returns:
            List of AgentSwarmStatus objects.
        """
        with self._lock:
            return list(self._swarms.values())

    def list_active_swarms(self) -> List[AgentSwarmStatus]:
        """List all active (non-completed) swarms.

        Returns:
            List of active AgentSwarmStatus objects.
        """
        with self._lock:
            return [
                s for s in self._swarms.values()
                if s.status in {SwarmStatus.INITIALIZING, SwarmStatus.RUNNING, SwarmStatus.PAUSED}
            ]


# Singleton instance for global access
_default_tracker: Optional[SwarmTracker] = None


def get_swarm_tracker() -> SwarmTracker:
    """Get the default SwarmTracker singleton.

    Returns:
        The global SwarmTracker instance.
    """
    global _default_tracker
    if _default_tracker is None:
        _default_tracker = SwarmTracker()
    return _default_tracker


def set_swarm_tracker(tracker: SwarmTracker) -> None:
    """Set the default SwarmTracker singleton.

    Args:
        tracker: The SwarmTracker instance to use globally.
    """
    global _default_tracker
    _default_tracker = tracker
