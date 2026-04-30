# =============================================================================
# IPA Platform - Concurrent Execution State Management
# =============================================================================
# Sprint 7: Concurrent Execution Engine
# Phase 2 Feature: P2-F1 (Concurrent Execution)
#
# State management for parallel workflow execution:
#   - BranchStatus: Status enumeration for parallel branches
#   - ParallelBranch: Individual branch state tracking
#   - ConcurrentExecutionState: Complete execution state
#   - ConcurrentStateManager: State management singleton
#
# Provides visibility into parallel execution progress and enables
# checkpoint/restore operations for fault tolerance.
# =============================================================================

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


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

    Example:
        branch = ParallelBranch(
            id="financial-analysis",
            executor_id="financial-agent-001",
            status=BranchStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
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
        self.started_at = datetime.utcnow()

    def mark_completed(self, result: Any) -> None:
        """Mark branch as completed with result."""
        self.status = BranchStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.result = result

    def mark_failed(self, error: str) -> None:
        """Mark branch as failed with error."""
        self.status = BranchStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error = error

    def mark_cancelled(self) -> None:
        """Mark branch as cancelled."""
        self.status = BranchStatus.CANCELLED
        self.completed_at = datetime.utcnow()

    def mark_timeout(self) -> None:
        """Mark branch as timed out."""
        self.status = BranchStatus.TIMEOUT
        self.completed_at = datetime.utcnow()
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


@dataclass
class ConcurrentExecutionState:
    """
    Complete state of a concurrent execution.

    Aggregates all parallel branches for a single execution instance,
    providing visibility into overall progress and individual branch states.

    Attributes:
        execution_id: UUID of the parent workflow execution
        parent_node_id: ID of the gateway/executor node managing this state
        branches: Dictionary of branch_id -> ParallelBranch
        created_at: When the concurrent execution was created
        completed_at: When all branches finished (or cancelled)
        mode: Execution mode (ALL, ANY, MAJORITY, FIRST_SUCCESS)
        metadata: Additional execution metadata

    Example:
        state = ConcurrentExecutionState(
            execution_id=UUID("..."),
            parent_node_id="parallel-gateway-1",
        )
        state.add_branch(ParallelBranch(id="branch1", executor_id="agent1"))
        state.add_branch(ParallelBranch(id="branch2", executor_id="agent2"))
    """

    execution_id: UUID
    parent_node_id: str
    branches: Dict[str, ParallelBranch] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    mode: str = "all"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_branch(self, branch: ParallelBranch) -> None:
        """
        Add a branch to this execution.

        Args:
            branch: ParallelBranch to add
        """
        self.branches[branch.id] = branch
        logger.debug(
            f"Added branch {branch.id} to execution {self.execution_id}, "
            f"total branches: {len(self.branches)}"
        )

    def get_branch(self, branch_id: str) -> Optional[ParallelBranch]:
        """
        Get a branch by ID.

        Args:
            branch_id: Branch identifier

        Returns:
            ParallelBranch or None if not found
        """
        return self.branches.get(branch_id)

    def update_branch_status(
        self,
        branch_id: str,
        status: BranchStatus,
        result: Any = None,
        error: Optional[str] = None,
    ) -> bool:
        """
        Update a branch's status.

        Args:
            branch_id: Branch identifier
            status: New status
            result: Result data (for COMPLETED)
            error: Error message (for FAILED)

        Returns:
            True if branch was updated, False if not found
        """
        branch = self.branches.get(branch_id)
        if not branch:
            logger.warning(f"Branch {branch_id} not found in execution {self.execution_id}")
            return False

        branch.status = status

        if status == BranchStatus.RUNNING:
            branch.started_at = datetime.utcnow()
        elif status in {BranchStatus.COMPLETED, BranchStatus.FAILED,
                       BranchStatus.CANCELLED, BranchStatus.TIMEOUT}:
            branch.completed_at = datetime.utcnow()
            branch.result = result
            branch.error = error

        logger.debug(
            f"Updated branch {branch_id} status to {status.value} "
            f"in execution {self.execution_id}"
        )

        # Check if all branches are terminal
        if self.is_completed:
            self.completed_at = datetime.utcnow()

        return True

    @property
    def is_completed(self) -> bool:
        """Check if all branches are in terminal state."""
        if not self.branches:
            return False  # No branches means not completed yet
        return all(branch.is_terminal for branch in self.branches.values())

    @property
    def total_branches(self) -> int:
        """Get total number of branches."""
        return len(self.branches)

    @property
    def pending_count(self) -> int:
        """Get count of pending branches."""
        return len([b for b in self.branches.values() if b.status == BranchStatus.PENDING])

    @property
    def running_count(self) -> int:
        """Get count of running branches."""
        return len([b for b in self.branches.values() if b.status == BranchStatus.RUNNING])

    @property
    def completed_count(self) -> int:
        """Get count of completed branches."""
        return len([b for b in self.branches.values() if b.status == BranchStatus.COMPLETED])

    @property
    def failed_count(self) -> int:
        """Get count of failed branches (including timeout/cancelled)."""
        failed_statuses = {BranchStatus.FAILED, BranchStatus.CANCELLED, BranchStatus.TIMEOUT}
        return len([b for b in self.branches.values() if b.status in failed_statuses])

    def get_successful_results(self) -> Dict[str, Any]:
        """
        Get results from all successful branches.

        Returns:
            Dictionary mapping branch_id to result data
        """
        return {
            branch_id: branch.result
            for branch_id, branch in self.branches.items()
            if branch.is_successful
        }

    def get_failed_branches(self) -> List[ParallelBranch]:
        """
        Get all failed branches.

        Returns:
            List of failed ParallelBranch objects
        """
        failed_statuses = {BranchStatus.FAILED, BranchStatus.TIMEOUT}
        return [
            branch for branch in self.branches.values()
            if branch.status in failed_statuses
        ]

    def get_active_branches(self) -> List[ParallelBranch]:
        """
        Get all currently active (running) branches.

        Returns:
            List of running ParallelBranch objects
        """
        return [
            branch for branch in self.branches.values()
            if branch.status == BranchStatus.RUNNING
        ]

    @property
    def progress_percentage(self) -> float:
        """Calculate completion progress as percentage."""
        if not self.branches:
            return 0.0
        terminal_count = len([b for b in self.branches.values() if b.is_terminal])
        return (terminal_count / len(self.branches)) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return {
            "execution_id": str(self.execution_id),
            "parent_node_id": self.parent_node_id,
            "branches": {
                branch_id: branch.to_dict()
                for branch_id, branch in self.branches.items()
            },
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "mode": self.mode,
            "is_completed": self.is_completed,
            "progress_percentage": self.progress_percentage,
            "total_branches": self.total_branches,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            "metadata": self.metadata,
        }


class ConcurrentStateManager:
    """
    Manager for concurrent execution states.

    Provides CRUD operations for tracking multiple concurrent executions.
    Acts as an in-memory store with serialization support for persistence.

    Features:
        - Create and track concurrent execution states
        - Update branch statuses within executions
        - Query execution progress and results
        - Cleanup completed executions

    Example:
        manager = ConcurrentStateManager()

        # Create state for new execution
        state = manager.create_state(
            execution_id=UUID("..."),
            parent_node_id="parallel-gateway-1",
            branch_configs=[
                {"id": "b1", "executor_id": "agent1"},
                {"id": "b2", "executor_id": "agent2"},
            ],
        )

        # Update branch status
        manager.update_branch(
            execution_id=state.execution_id,
            branch_id="b1",
            status=BranchStatus.COMPLETED,
            result={"output": "data"},
        )

        # Get final results
        results = manager.get_state(execution_id).get_successful_results()
    """

    def __init__(self):
        """Initialize the state manager."""
        self._states: Dict[UUID, ConcurrentExecutionState] = {}
        logger.info("ConcurrentStateManager initialized")

    def create_state(
        self,
        execution_id: UUID,
        parent_node_id: str,
        branch_configs: List[Dict[str, Any]],
        mode: str = "all",
    ) -> ConcurrentExecutionState:
        """
        Create a new concurrent execution state.

        Args:
            execution_id: UUID of the parent execution
            parent_node_id: ID of the gateway/executor managing this state
            branch_configs: List of branch configurations with 'id' and 'executor_id'
            mode: Execution mode string

        Returns:
            Created ConcurrentExecutionState

        Example:
            state = manager.create_state(
                execution_id=uuid4(),
                parent_node_id="parallel-1",
                branch_configs=[
                    {"id": "b1", "executor_id": "agent1", "timeout": 60},
                    {"id": "b2", "executor_id": "agent2"},
                ],
                mode="all",
            )
        """
        state = ConcurrentExecutionState(
            execution_id=execution_id,
            parent_node_id=parent_node_id,
            mode=mode,
        )

        for config in branch_configs:
            branch = ParallelBranch(
                id=config["id"],
                executor_id=config["executor_id"],
                metadata=config.get("metadata", {}),
            )
            state.add_branch(branch)

        self._states[execution_id] = state

        logger.info(
            f"Created concurrent state for execution {execution_id} "
            f"with {len(branch_configs)} branches"
        )

        return state

    def get_state(self, execution_id: UUID) -> Optional[ConcurrentExecutionState]:
        """
        Get concurrent execution state by ID.

        Args:
            execution_id: UUID of the execution

        Returns:
            ConcurrentExecutionState or None if not found
        """
        return self._states.get(execution_id)

    def update_branch(
        self,
        execution_id: UUID,
        branch_id: str,
        status: BranchStatus,
        result: Any = None,
        error: Optional[str] = None,
    ) -> bool:
        """
        Update a branch's status in an execution.

        Args:
            execution_id: UUID of the execution
            branch_id: Branch identifier
            status: New status
            result: Result data (for COMPLETED)
            error: Error message (for FAILED)

        Returns:
            True if updated, False if execution/branch not found
        """
        state = self._states.get(execution_id)
        if not state:
            logger.warning(f"Execution {execution_id} not found for branch update")
            return False

        return state.update_branch_status(branch_id, status, result, error)

    def start_branch(
        self,
        execution_id: UUID,
        branch_id: str,
    ) -> bool:
        """Mark a branch as started."""
        return self.update_branch(execution_id, branch_id, BranchStatus.RUNNING)

    def complete_branch(
        self,
        execution_id: UUID,
        branch_id: str,
        result: Any,
    ) -> bool:
        """Mark a branch as completed with result."""
        return self.update_branch(
            execution_id, branch_id, BranchStatus.COMPLETED, result=result
        )

    def fail_branch(
        self,
        execution_id: UUID,
        branch_id: str,
        error: str,
    ) -> bool:
        """Mark a branch as failed with error."""
        return self.update_branch(
            execution_id, branch_id, BranchStatus.FAILED, error=error
        )

    def cancel_branch(
        self,
        execution_id: UUID,
        branch_id: str,
    ) -> bool:
        """Mark a branch as cancelled."""
        return self.update_branch(execution_id, branch_id, BranchStatus.CANCELLED)

    def timeout_branch(
        self,
        execution_id: UUID,
        branch_id: str,
    ) -> bool:
        """Mark a branch as timed out."""
        return self.update_branch(execution_id, branch_id, BranchStatus.TIMEOUT)

    def cancel_all_branches(self, execution_id: UUID) -> int:
        """
        Cancel all running branches in an execution.

        Args:
            execution_id: UUID of the execution

        Returns:
            Number of branches cancelled
        """
        state = self._states.get(execution_id)
        if not state:
            return 0

        cancelled = 0
        for branch in state.get_active_branches():
            if self.cancel_branch(execution_id, branch.id):
                cancelled += 1

        logger.info(f"Cancelled {cancelled} branches in execution {execution_id}")
        return cancelled

    def cleanup(self, execution_id: UUID) -> bool:
        """
        Remove execution state from memory.

        Args:
            execution_id: UUID of the execution to remove

        Returns:
            True if removed, False if not found
        """
        if execution_id in self._states:
            del self._states[execution_id]
            logger.debug(f"Cleaned up state for execution {execution_id}")
            return True
        return False

    def cleanup_completed(self, max_age_minutes: int = 60) -> int:
        """
        Remove completed execution states older than max_age.

        Args:
            max_age_minutes: Maximum age in minutes for completed states

        Returns:
            Number of states cleaned up
        """
        now = datetime.utcnow()
        to_remove = []

        for exec_id, state in self._states.items():
            if state.is_completed and state.completed_at:
                age_minutes = (now - state.completed_at).total_seconds() / 60
                if age_minutes > max_age_minutes:
                    to_remove.append(exec_id)

        for exec_id in to_remove:
            del self._states[exec_id]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} completed execution states")

        return len(to_remove)

    def get_all_active(self) -> List[ConcurrentExecutionState]:
        """
        Get all active (not completed) execution states.

        Returns:
            List of active ConcurrentExecutionState objects
        """
        return [state for state in self._states.values() if not state.is_completed]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get manager statistics.

        Returns:
            Dictionary with statistics about tracked executions
        """
        total = len(self._states)
        active = len([s for s in self._states.values() if not s.is_completed])
        completed = total - active

        total_branches = sum(s.total_branches for s in self._states.values())
        running_branches = sum(s.running_count for s in self._states.values())

        return {
            "total_executions": total,
            "active_executions": active,
            "completed_executions": completed,
            "total_branches": total_branches,
            "running_branches": running_branches,
        }


# Global singleton instance
_state_manager: Optional[ConcurrentStateManager] = None


def get_state_manager() -> ConcurrentStateManager:
    """
    Get the global ConcurrentStateManager instance.

    Returns:
        ConcurrentStateManager singleton
    """
    global _state_manager
    if _state_manager is None:
        _state_manager = ConcurrentStateManager()
    return _state_manager


def reset_state_manager() -> None:
    """Reset the global state manager (for testing)."""
    global _state_manager
    _state_manager = None
