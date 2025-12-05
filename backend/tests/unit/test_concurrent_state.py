# =============================================================================
# IPA Platform - Concurrent State Management Unit Tests
# =============================================================================
# Sprint 7: Concurrent Execution Engine (Phase 2)
#
# Tests for concurrent state management including:
#   - BranchStatus enumeration
#   - ParallelBranch state tracking
#   - ConcurrentExecutionState aggregation
#   - ConcurrentStateManager operations
# =============================================================================

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.domain.workflows.executors.concurrent_state import (
    BranchStatus,
    ParallelBranch,
    ConcurrentExecutionState,
    ConcurrentStateManager,
    get_state_manager,
    reset_state_manager,
)


# =============================================================================
# BranchStatus Tests
# =============================================================================


class TestBranchStatus:
    """Tests for BranchStatus enum."""

    def test_status_values(self):
        """Test all status enum values."""
        assert BranchStatus.PENDING.value == "pending"
        assert BranchStatus.RUNNING.value == "running"
        assert BranchStatus.COMPLETED.value == "completed"
        assert BranchStatus.FAILED.value == "failed"
        assert BranchStatus.CANCELLED.value == "cancelled"
        assert BranchStatus.TIMEOUT.value == "timeout"

    def test_status_from_string(self):
        """Test creating status from string."""
        assert BranchStatus("pending") == BranchStatus.PENDING
        assert BranchStatus("running") == BranchStatus.RUNNING
        assert BranchStatus("completed") == BranchStatus.COMPLETED


# =============================================================================
# ParallelBranch Tests
# =============================================================================


class TestParallelBranch:
    """Tests for ParallelBranch dataclass."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        branch = ParallelBranch(
            id="branch-1",
            executor_id="agent-001",
        )

        assert branch.id == "branch-1"
        assert branch.executor_id == "agent-001"
        assert branch.status == BranchStatus.PENDING
        assert branch.started_at is None
        assert branch.completed_at is None

    def test_mark_started(self):
        """Test marking branch as started."""
        branch = ParallelBranch(id="b1", executor_id="a1")
        branch.mark_started()

        assert branch.status == BranchStatus.RUNNING
        assert branch.started_at is not None

    def test_mark_completed(self):
        """Test marking branch as completed."""
        branch = ParallelBranch(id="b1", executor_id="a1")
        branch.mark_started()
        branch.mark_completed(result={"output": "data"})

        assert branch.status == BranchStatus.COMPLETED
        assert branch.completed_at is not None
        assert branch.result == {"output": "data"}

    def test_mark_failed(self):
        """Test marking branch as failed."""
        branch = ParallelBranch(id="b1", executor_id="a1")
        branch.mark_started()
        branch.mark_failed(error="Connection error")

        assert branch.status == BranchStatus.FAILED
        assert branch.error == "Connection error"

    def test_mark_cancelled(self):
        """Test marking branch as cancelled."""
        branch = ParallelBranch(id="b1", executor_id="a1")
        branch.mark_started()
        branch.mark_cancelled()

        assert branch.status == BranchStatus.CANCELLED

    def test_mark_timeout(self):
        """Test marking branch as timed out."""
        branch = ParallelBranch(id="b1", executor_id="a1")
        branch.mark_timeout()

        assert branch.status == BranchStatus.TIMEOUT
        assert "timed out" in branch.error.lower()

    def test_is_terminal(self):
        """Test terminal state detection."""
        branch = ParallelBranch(id="b1", executor_id="a1")

        assert not branch.is_terminal

        branch.mark_completed(result=None)
        assert branch.is_terminal

    def test_is_successful(self):
        """Test success detection."""
        branch = ParallelBranch(id="b1", executor_id="a1")

        assert not branch.is_successful

        branch.mark_completed(result="ok")
        assert branch.is_successful

    def test_duration_ms(self):
        """Test duration calculation."""
        branch = ParallelBranch(id="b1", executor_id="a1")

        assert branch.duration_ms is None

        branch.started_at = datetime.utcnow()
        branch.completed_at = branch.started_at + timedelta(milliseconds=1500)

        assert branch.duration_ms == 1500

    def test_to_dict(self):
        """Test serialization to dictionary."""
        branch = ParallelBranch(
            id="branch-1",
            executor_id="agent-1",
            metadata={"key": "value"},
        )
        branch.mark_started()
        branch.mark_completed(result={"data": "output"})

        data = branch.to_dict()

        assert data["id"] == "branch-1"
        assert data["executor_id"] == "agent-1"
        assert data["status"] == "completed"
        assert data["result"] == {"data": "output"}
        assert data["metadata"]["key"] == "value"


# =============================================================================
# ConcurrentExecutionState Tests
# =============================================================================


class TestConcurrentExecutionState:
    """Tests for ConcurrentExecutionState dataclass."""

    def test_initialization(self):
        """Test basic initialization."""
        exec_id = uuid4()
        state = ConcurrentExecutionState(
            execution_id=exec_id,
            parent_node_id="parallel-1",
        )

        assert state.execution_id == exec_id
        assert state.parent_node_id == "parallel-1"
        assert len(state.branches) == 0
        assert not state.is_completed

    def test_add_branch(self):
        """Test adding branches."""
        state = ConcurrentExecutionState(
            execution_id=uuid4(),
            parent_node_id="parallel-1",
        )

        branch1 = ParallelBranch(id="b1", executor_id="a1")
        branch2 = ParallelBranch(id="b2", executor_id="a2")

        state.add_branch(branch1)
        state.add_branch(branch2)

        assert state.total_branches == 2
        assert state.get_branch("b1") == branch1
        assert state.get_branch("b2") == branch2

    def test_get_branch_not_found(self):
        """Test getting non-existent branch."""
        state = ConcurrentExecutionState(
            execution_id=uuid4(),
            parent_node_id="parallel-1",
        )

        assert state.get_branch("nonexistent") is None

    def test_update_branch_status(self):
        """Test updating branch status."""
        state = ConcurrentExecutionState(
            execution_id=uuid4(),
            parent_node_id="parallel-1",
        )
        state.add_branch(ParallelBranch(id="b1", executor_id="a1"))

        result = state.update_branch_status(
            branch_id="b1",
            status=BranchStatus.COMPLETED,
            result={"output": "data"},
        )

        assert result is True
        assert state.get_branch("b1").status == BranchStatus.COMPLETED

    def test_update_branch_not_found(self):
        """Test updating non-existent branch."""
        state = ConcurrentExecutionState(
            execution_id=uuid4(),
            parent_node_id="parallel-1",
        )

        result = state.update_branch_status("nonexistent", BranchStatus.RUNNING)
        assert result is False

    def test_is_completed(self):
        """Test completion detection."""
        state = ConcurrentExecutionState(
            execution_id=uuid4(),
            parent_node_id="parallel-1",
        )
        state.add_branch(ParallelBranch(id="b1", executor_id="a1"))
        state.add_branch(ParallelBranch(id="b2", executor_id="a2"))

        assert not state.is_completed

        state.update_branch_status("b1", BranchStatus.COMPLETED)
        assert not state.is_completed

        state.update_branch_status("b2", BranchStatus.FAILED)
        assert state.is_completed

    def test_counts(self):
        """Test branch count properties."""
        state = ConcurrentExecutionState(
            execution_id=uuid4(),
            parent_node_id="parallel-1",
        )
        state.add_branch(ParallelBranch(id="b1", executor_id="a1"))
        state.add_branch(ParallelBranch(id="b2", executor_id="a2"))
        state.add_branch(ParallelBranch(id="b3", executor_id="a3"))

        assert state.pending_count == 3
        assert state.running_count == 0
        assert state.completed_count == 0

        state.update_branch_status("b1", BranchStatus.RUNNING)
        assert state.running_count == 1
        assert state.pending_count == 2

        state.update_branch_status("b1", BranchStatus.COMPLETED, result="ok")
        assert state.completed_count == 1

        state.update_branch_status("b2", BranchStatus.FAILED, error="err")
        assert state.failed_count == 1

    def test_get_successful_results(self):
        """Test getting successful results."""
        state = ConcurrentExecutionState(
            execution_id=uuid4(),
            parent_node_id="parallel-1",
        )
        state.add_branch(ParallelBranch(id="b1", executor_id="a1"))
        state.add_branch(ParallelBranch(id="b2", executor_id="a2"))

        state.update_branch_status("b1", BranchStatus.COMPLETED, result="result1")
        state.update_branch_status("b2", BranchStatus.FAILED, error="error")

        results = state.get_successful_results()
        assert len(results) == 1
        assert results["b1"] == "result1"

    def test_get_failed_branches(self):
        """Test getting failed branches."""
        state = ConcurrentExecutionState(
            execution_id=uuid4(),
            parent_node_id="parallel-1",
        )
        state.add_branch(ParallelBranch(id="b1", executor_id="a1"))
        state.add_branch(ParallelBranch(id="b2", executor_id="a2"))
        state.add_branch(ParallelBranch(id="b3", executor_id="a3"))

        state.update_branch_status("b1", BranchStatus.COMPLETED, result="ok")
        state.update_branch_status("b2", BranchStatus.FAILED, error="err")
        state.update_branch_status("b3", BranchStatus.TIMEOUT)

        failed = state.get_failed_branches()
        assert len(failed) == 2

    def test_get_active_branches(self):
        """Test getting active branches."""
        state = ConcurrentExecutionState(
            execution_id=uuid4(),
            parent_node_id="parallel-1",
        )
        state.add_branch(ParallelBranch(id="b1", executor_id="a1"))
        state.add_branch(ParallelBranch(id="b2", executor_id="a2"))

        assert len(state.get_active_branches()) == 0

        state.update_branch_status("b1", BranchStatus.RUNNING)
        active = state.get_active_branches()
        assert len(active) == 1
        assert active[0].id == "b1"

    def test_progress_percentage(self):
        """Test progress calculation."""
        state = ConcurrentExecutionState(
            execution_id=uuid4(),
            parent_node_id="parallel-1",
        )
        state.add_branch(ParallelBranch(id="b1", executor_id="a1"))
        state.add_branch(ParallelBranch(id="b2", executor_id="a2"))
        state.add_branch(ParallelBranch(id="b3", executor_id="a3"))
        state.add_branch(ParallelBranch(id="b4", executor_id="a4"))

        assert state.progress_percentage == 0.0

        state.update_branch_status("b1", BranchStatus.COMPLETED)
        assert state.progress_percentage == 25.0

        state.update_branch_status("b2", BranchStatus.COMPLETED)
        assert state.progress_percentage == 50.0

    def test_to_dict(self):
        """Test serialization to dictionary."""
        state = ConcurrentExecutionState(
            execution_id=uuid4(),
            parent_node_id="parallel-1",
            mode="all",
        )
        state.add_branch(ParallelBranch(id="b1", executor_id="a1"))

        data = state.to_dict()

        assert "execution_id" in data
        assert data["parent_node_id"] == "parallel-1"
        assert data["mode"] == "all"
        assert len(data["branches"]) == 1


# =============================================================================
# ConcurrentStateManager Tests
# =============================================================================


class TestConcurrentStateManager:
    """Tests for ConcurrentStateManager class."""

    @pytest.fixture
    def manager(self):
        """Create fresh manager for each test."""
        reset_state_manager()
        return ConcurrentStateManager()

    def test_create_state(self, manager):
        """Test creating execution state."""
        exec_id = uuid4()
        state = manager.create_state(
            execution_id=exec_id,
            parent_node_id="parallel-1",
            branch_configs=[
                {"id": "b1", "executor_id": "a1"},
                {"id": "b2", "executor_id": "a2"},
            ],
            mode="all",
        )

        assert state.execution_id == exec_id
        assert state.total_branches == 2

    def test_get_state(self, manager):
        """Test getting execution state."""
        exec_id = uuid4()
        manager.create_state(
            execution_id=exec_id,
            parent_node_id="p1",
            branch_configs=[{"id": "b1", "executor_id": "a1"}],
        )

        state = manager.get_state(exec_id)
        assert state is not None
        assert state.execution_id == exec_id

    def test_get_state_not_found(self, manager):
        """Test getting non-existent state."""
        assert manager.get_state(uuid4()) is None

    def test_update_branch(self, manager):
        """Test updating branch via manager."""
        exec_id = uuid4()
        manager.create_state(
            execution_id=exec_id,
            parent_node_id="p1",
            branch_configs=[{"id": "b1", "executor_id": "a1"}],
        )

        result = manager.update_branch(
            execution_id=exec_id,
            branch_id="b1",
            status=BranchStatus.COMPLETED,
            result="success",
        )

        assert result is True
        state = manager.get_state(exec_id)
        assert state.get_branch("b1").status == BranchStatus.COMPLETED

    def test_start_branch(self, manager):
        """Test starting branch."""
        exec_id = uuid4()
        manager.create_state(
            execution_id=exec_id,
            parent_node_id="p1",
            branch_configs=[{"id": "b1", "executor_id": "a1"}],
        )

        assert manager.start_branch(exec_id, "b1") is True
        assert manager.get_state(exec_id).get_branch("b1").status == BranchStatus.RUNNING

    def test_complete_branch(self, manager):
        """Test completing branch."""
        exec_id = uuid4()
        manager.create_state(
            execution_id=exec_id,
            parent_node_id="p1",
            branch_configs=[{"id": "b1", "executor_id": "a1"}],
        )

        assert manager.complete_branch(exec_id, "b1", result="data") is True
        assert manager.get_state(exec_id).get_branch("b1").status == BranchStatus.COMPLETED

    def test_fail_branch(self, manager):
        """Test failing branch."""
        exec_id = uuid4()
        manager.create_state(
            execution_id=exec_id,
            parent_node_id="p1",
            branch_configs=[{"id": "b1", "executor_id": "a1"}],
        )

        assert manager.fail_branch(exec_id, "b1", error="error msg") is True
        branch = manager.get_state(exec_id).get_branch("b1")
        assert branch.status == BranchStatus.FAILED
        assert branch.error == "error msg"

    def test_cancel_all_branches(self, manager):
        """Test cancelling all running branches."""
        exec_id = uuid4()
        manager.create_state(
            execution_id=exec_id,
            parent_node_id="p1",
            branch_configs=[
                {"id": "b1", "executor_id": "a1"},
                {"id": "b2", "executor_id": "a2"},
            ],
        )

        manager.start_branch(exec_id, "b1")
        manager.start_branch(exec_id, "b2")

        cancelled = manager.cancel_all_branches(exec_id)
        assert cancelled == 2

    def test_cleanup(self, manager):
        """Test cleanup."""
        exec_id = uuid4()
        manager.create_state(
            execution_id=exec_id,
            parent_node_id="p1",
            branch_configs=[{"id": "b1", "executor_id": "a1"}],
        )

        assert manager.cleanup(exec_id) is True
        assert manager.get_state(exec_id) is None

    def test_cleanup_not_found(self, manager):
        """Test cleanup of non-existent state."""
        assert manager.cleanup(uuid4()) is False

    def test_get_all_active(self, manager):
        """Test getting all active states."""
        exec1 = uuid4()
        exec2 = uuid4()

        manager.create_state(exec1, "p1", [{"id": "b1", "executor_id": "a1"}])
        manager.create_state(exec2, "p2", [{"id": "b1", "executor_id": "a1"}])

        # Complete one
        manager.complete_branch(exec1, "b1", result="done")

        active = manager.get_all_active()
        assert len(active) == 1
        assert active[0].execution_id == exec2

    def test_get_statistics(self, manager):
        """Test getting statistics."""
        exec1 = uuid4()
        exec2 = uuid4()

        manager.create_state(exec1, "p1", [
            {"id": "b1", "executor_id": "a1"},
            {"id": "b2", "executor_id": "a2"},
        ])
        manager.create_state(exec2, "p2", [{"id": "b1", "executor_id": "a1"}])

        manager.start_branch(exec1, "b1")

        stats = manager.get_statistics()

        assert stats["total_executions"] == 2
        assert stats["active_executions"] == 2
        assert stats["total_branches"] == 3
        assert stats["running_branches"] == 1


# =============================================================================
# Singleton Tests
# =============================================================================


class TestSingleton:
    """Tests for singleton pattern."""

    def test_get_state_manager_singleton(self):
        """Test that get_state_manager returns singleton."""
        reset_state_manager()
        manager1 = get_state_manager()
        manager2 = get_state_manager()
        assert manager1 is manager2

    def test_reset_state_manager(self):
        """Test reset creates new instance."""
        manager1 = get_state_manager()
        reset_state_manager()
        manager2 = get_state_manager()
        assert manager1 is not manager2
