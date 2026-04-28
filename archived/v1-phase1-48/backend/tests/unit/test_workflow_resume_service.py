# =============================================================================
# IPA Platform - Workflow Resume Service Unit Tests
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Human-in-the-Loop
#
# Tests for the workflow resume service including:
#   - ResumeStatus enum
#   - ResumeResult dataclass
#   - WorkflowResumeService logic
#   - Resume workflow scenarios
# =============================================================================

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.domain.workflows.resume_service import (
    ResumeResult,
    ResumeStatus,
    WorkflowResumeService,
)
from src.domain.checkpoints import CheckpointStatus
from src.domain.executions import ExecutionStatus


# =============================================================================
# ResumeStatus Tests
# =============================================================================


class TestResumeStatus:
    """Tests for ResumeStatus enum."""

    def test_status_values(self):
        """Test all status enum values."""
        assert ResumeStatus.SUCCESS.value == "success"
        assert ResumeStatus.NOT_FOUND.value == "not_found"
        assert ResumeStatus.INVALID_STATE.value == "invalid_state"
        assert ResumeStatus.CHECKPOINT_PENDING.value == "checkpoint_pending"
        assert ResumeStatus.CHECKPOINT_REJECTED.value == "checkpoint_rejected"
        assert ResumeStatus.CHECKPOINT_EXPIRED.value == "checkpoint_expired"
        assert ResumeStatus.ERROR.value == "error"

    def test_status_from_string(self):
        """Test creating status from string."""
        assert ResumeStatus("success") == ResumeStatus.SUCCESS
        assert ResumeStatus("not_found") == ResumeStatus.NOT_FOUND


# =============================================================================
# ResumeResult Tests
# =============================================================================


class TestResumeResult:
    """Tests for ResumeResult dataclass."""

    def test_initialization(self):
        """Test basic initialization."""
        execution_id = uuid4()
        result = ResumeResult(
            status=ResumeStatus.SUCCESS,
            execution_id=execution_id,
            message="Resumed successfully",
        )

        assert result.status == ResumeStatus.SUCCESS
        assert result.execution_id == execution_id
        assert result.message == "Resumed successfully"

    def test_initialization_with_checkpoint(self):
        """Test initialization with checkpoint data."""
        execution_id = uuid4()
        checkpoint_id = uuid4()
        now = datetime.utcnow()

        result = ResumeResult(
            status=ResumeStatus.SUCCESS,
            execution_id=execution_id,
            checkpoint_id=checkpoint_id,
            message="Resumed",
            resumed_at=now,
            next_node_id="next-step",
            restored_state={"key": "value"},
        )

        assert result.checkpoint_id == checkpoint_id
        assert result.resumed_at == now
        assert result.next_node_id == "next-step"
        assert result.restored_state == {"key": "value"}

    def test_to_dict(self):
        """Test serialization to dictionary."""
        execution_id = uuid4()
        checkpoint_id = uuid4()
        now = datetime.utcnow()

        result = ResumeResult(
            status=ResumeStatus.SUCCESS,
            execution_id=execution_id,
            checkpoint_id=checkpoint_id,
            message="Done",
            resumed_at=now,
        )

        data = result.to_dict()

        assert data["status"] == "success"
        assert data["execution_id"] == str(execution_id)
        assert data["checkpoint_id"] == str(checkpoint_id)
        assert data["message"] == "Done"


# =============================================================================
# WorkflowResumeService Tests
# =============================================================================


class TestWorkflowResumeService:
    """Tests for WorkflowResumeService class."""

    @pytest.fixture
    def mock_checkpoint_service(self):
        """Create mock checkpoint service."""
        return AsyncMock()

    @pytest.fixture
    def mock_execution_repo(self):
        """Create mock execution repository."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_checkpoint_service, mock_execution_repo):
        """Create resume service with mocks."""
        return WorkflowResumeService(
            checkpoint_service=mock_checkpoint_service,
            execution_repository=mock_execution_repo,
        )

    @pytest.mark.asyncio
    async def test_resume_from_checkpoint_success(
        self, service, mock_checkpoint_service, mock_execution_repo
    ):
        """Test successful resume from checkpoint."""
        execution_id = uuid4()
        checkpoint_id = uuid4()

        # Mock execution in paused state
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.PAUSED.value
        mock_execution_repo.get.return_value = mock_execution
        mock_execution_repo.resume.return_value = mock_execution

        # Mock approved checkpoint
        mock_checkpoint = MagicMock()
        mock_checkpoint.execution_id = execution_id
        mock_checkpoint.status = CheckpointStatus.APPROVED
        mock_checkpoint.node_id = "approval-gate"
        mock_checkpoint.payload = {"type": "human_approval", "content": "test"}
        mock_checkpoint.response = {"action": "proceed"}
        mock_checkpoint_service.get_checkpoint.return_value = mock_checkpoint

        result = await service.resume_from_checkpoint(execution_id, checkpoint_id)

        assert result.status == ResumeStatus.SUCCESS
        assert result.execution_id == execution_id
        assert result.checkpoint_id == checkpoint_id
        assert result.next_node_id == "approval-gate"
        mock_execution_repo.resume.assert_called_once_with(execution_id)

    @pytest.mark.asyncio
    async def test_resume_execution_not_found(
        self, service, mock_execution_repo
    ):
        """Test resume when execution not found."""
        mock_execution_repo.get.return_value = None

        result = await service.resume_from_checkpoint(uuid4(), uuid4())

        assert result.status == ResumeStatus.NOT_FOUND
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_resume_execution_not_paused(
        self, service, mock_execution_repo
    ):
        """Test resume when execution is not paused."""
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.RUNNING.value
        mock_execution_repo.get.return_value = mock_execution

        result = await service.resume_from_checkpoint(uuid4(), uuid4())

        assert result.status == ResumeStatus.INVALID_STATE
        assert "not paused" in result.message.lower()

    @pytest.mark.asyncio
    async def test_resume_checkpoint_not_found(
        self, service, mock_checkpoint_service, mock_execution_repo
    ):
        """Test resume when checkpoint not found."""
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.PAUSED.value
        mock_execution_repo.get.return_value = mock_execution

        mock_checkpoint_service.get_checkpoint.return_value = None

        result = await service.resume_from_checkpoint(uuid4(), uuid4())

        assert result.status == ResumeStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_resume_checkpoint_wrong_execution(
        self, service, mock_checkpoint_service, mock_execution_repo
    ):
        """Test resume when checkpoint belongs to different execution."""
        execution_id = uuid4()
        other_execution_id = uuid4()

        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.PAUSED.value
        mock_execution_repo.get.return_value = mock_execution

        mock_checkpoint = MagicMock()
        mock_checkpoint.execution_id = other_execution_id
        mock_checkpoint_service.get_checkpoint.return_value = mock_checkpoint

        result = await service.resume_from_checkpoint(execution_id, uuid4())

        assert result.status == ResumeStatus.INVALID_STATE
        assert "does not belong" in result.message.lower()

    @pytest.mark.asyncio
    async def test_resume_checkpoint_pending(
        self, service, mock_checkpoint_service, mock_execution_repo
    ):
        """Test resume when checkpoint is still pending."""
        execution_id = uuid4()

        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.PAUSED.value
        mock_execution_repo.get.return_value = mock_execution

        mock_checkpoint = MagicMock()
        mock_checkpoint.execution_id = execution_id
        mock_checkpoint.status = CheckpointStatus.PENDING
        mock_checkpoint_service.get_checkpoint.return_value = mock_checkpoint

        result = await service.resume_from_checkpoint(execution_id, uuid4())

        assert result.status == ResumeStatus.CHECKPOINT_PENDING

    @pytest.mark.asyncio
    async def test_resume_checkpoint_rejected(
        self, service, mock_checkpoint_service, mock_execution_repo
    ):
        """Test resume when checkpoint was rejected."""
        execution_id = uuid4()

        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.PAUSED.value
        mock_execution_repo.get.return_value = mock_execution

        mock_checkpoint = MagicMock()
        mock_checkpoint.execution_id = execution_id
        mock_checkpoint.status = CheckpointStatus.REJECTED
        mock_checkpoint_service.get_checkpoint.return_value = mock_checkpoint

        result = await service.resume_from_checkpoint(execution_id, uuid4())

        assert result.status == ResumeStatus.CHECKPOINT_REJECTED

    @pytest.mark.asyncio
    async def test_resume_checkpoint_expired(
        self, service, mock_checkpoint_service, mock_execution_repo
    ):
        """Test resume when checkpoint has expired."""
        execution_id = uuid4()

        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.PAUSED.value
        mock_execution_repo.get.return_value = mock_execution

        mock_checkpoint = MagicMock()
        mock_checkpoint.execution_id = execution_id
        mock_checkpoint.status = CheckpointStatus.EXPIRED
        mock_checkpoint_service.get_checkpoint.return_value = mock_checkpoint

        result = await service.resume_from_checkpoint(execution_id, uuid4())

        assert result.status == ResumeStatus.CHECKPOINT_EXPIRED

    @pytest.mark.asyncio
    async def test_resume_with_approval_success(
        self, service, mock_checkpoint_service, mock_execution_repo
    ):
        """Test resume with approval (approve and resume in one step)."""
        execution_id = uuid4()
        checkpoint_id = uuid4()
        user_id = uuid4()

        # Mock pending checkpoint
        pending_checkpoint = MagicMock()
        pending_checkpoint.id = checkpoint_id
        mock_checkpoint_service.get_pending_approvals.return_value = [pending_checkpoint]

        # Mock approval
        approved_checkpoint = MagicMock()
        approved_checkpoint.id = checkpoint_id
        mock_checkpoint_service.approve_checkpoint.return_value = approved_checkpoint

        # Mock execution
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.PAUSED.value
        mock_execution_repo.get.return_value = mock_execution
        mock_execution_repo.resume.return_value = mock_execution

        # Mock checkpoint for resume
        resume_checkpoint = MagicMock()
        resume_checkpoint.execution_id = execution_id
        resume_checkpoint.status = CheckpointStatus.APPROVED
        resume_checkpoint.node_id = "gate"
        resume_checkpoint.payload = {}
        mock_checkpoint_service.get_checkpoint.return_value = resume_checkpoint

        result = await service.resume_with_approval(
            execution_id=execution_id,
            user_id=user_id,
        )

        assert result.status == ResumeStatus.SUCCESS
        mock_checkpoint_service.approve_checkpoint.assert_called_once()

    @pytest.mark.asyncio
    async def test_resume_with_approval_no_pending(
        self, service, mock_checkpoint_service
    ):
        """Test resume with approval when no pending checkpoint."""
        mock_checkpoint_service.get_pending_approvals.return_value = []

        result = await service.resume_with_approval(
            execution_id=uuid4(),
            user_id=uuid4(),
        )

        assert result.status == ResumeStatus.NOT_FOUND
        assert "No pending checkpoint" in result.message

    @pytest.mark.asyncio
    async def test_get_resume_status_can_resume(
        self, service, mock_checkpoint_service, mock_execution_repo
    ):
        """Test getting resume status when resume is possible."""
        execution_id = uuid4()

        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.PAUSED.value
        mock_execution_repo.get.return_value = mock_execution

        # Pending checkpoints
        mock_checkpoint_service.get_pending_approvals.return_value = []

        # Approved checkpoints
        approved_checkpoint = MagicMock()
        approved_checkpoint.status = CheckpointStatus.APPROVED
        mock_checkpoint_service.get_checkpoints_by_execution.return_value = [
            approved_checkpoint
        ]

        status = await service.get_resume_status(execution_id)

        assert status["can_resume"] is True
        assert status["approved_count"] == 1

    @pytest.mark.asyncio
    async def test_get_resume_status_awaiting_approval(
        self, service, mock_checkpoint_service, mock_execution_repo
    ):
        """Test getting resume status when awaiting approval."""
        execution_id = uuid4()

        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.PAUSED.value
        mock_execution_repo.get.return_value = mock_execution

        pending_checkpoint = MagicMock()
        pending_checkpoint.id = uuid4()
        pending_checkpoint.node_id = "gate"
        pending_checkpoint.created_at = datetime.utcnow()
        pending_checkpoint.status = CheckpointStatus.PENDING
        mock_checkpoint_service.get_pending_approvals.return_value = [pending_checkpoint]
        mock_checkpoint_service.get_checkpoints_by_execution.return_value = [
            pending_checkpoint
        ]

        status = await service.get_resume_status(execution_id)

        assert status["can_resume"] is False
        assert status["pending_count"] == 1

    @pytest.mark.asyncio
    async def test_get_resume_status_not_paused(
        self, service, mock_execution_repo
    ):
        """Test getting resume status when execution not paused."""
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.RUNNING.value
        mock_execution_repo.get.return_value = mock_execution

        status = await service.get_resume_status(uuid4())

        assert status["can_resume"] is False

    @pytest.mark.asyncio
    async def test_cancel_paused_execution_success(
        self, service, mock_execution_repo
    ):
        """Test cancelling a paused execution."""
        execution_id = uuid4()

        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.PAUSED.value
        mock_execution_repo.get.return_value = mock_execution
        mock_execution_repo.cancel.return_value = MagicMock()

        result = await service.cancel_paused_execution(
            execution_id=execution_id,
            reason="User cancelled",
        )

        assert result is True
        mock_execution_repo.cancel.assert_called_once_with(execution_id)

    @pytest.mark.asyncio
    async def test_cancel_paused_execution_not_paused(
        self, service, mock_execution_repo
    ):
        """Test cancelling when execution is not paused."""
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.RUNNING.value
        mock_execution_repo.get.return_value = mock_execution

        result = await service.cancel_paused_execution(uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_paused_execution_not_found(
        self, service, mock_execution_repo
    ):
        """Test cancelling when execution not found."""
        mock_execution_repo.get.return_value = None

        result = await service.cancel_paused_execution(uuid4())

        assert result is False


# =============================================================================
# Integration Workflow Tests
# =============================================================================


class TestResumeWorkflowIntegration:
    """Tests for complete resume workflow scenarios."""

    @pytest.fixture
    def mock_checkpoint_service(self):
        """Create mock checkpoint service."""
        return AsyncMock()

    @pytest.fixture
    def mock_execution_repo(self):
        """Create mock execution repository."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_checkpoint_service, mock_execution_repo):
        """Create resume service."""
        return WorkflowResumeService(
            mock_checkpoint_service, mock_execution_repo
        )

    @pytest.mark.asyncio
    async def test_full_pause_approve_resume_workflow(
        self, service, mock_checkpoint_service, mock_execution_repo
    ):
        """Test complete workflow: pause → await approval → approve → resume."""
        execution_id = uuid4()
        checkpoint_id = uuid4()
        user_id = uuid4()

        # Step 1: Execution is paused (externally)
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.PAUSED.value
        mock_execution_repo.get.return_value = mock_execution

        # Step 2: Check status - waiting for approval
        pending_cp = MagicMock()
        pending_cp.id = checkpoint_id
        pending_cp.node_id = "approval-gate"
        pending_cp.created_at = datetime.utcnow()
        pending_cp.status = CheckpointStatus.PENDING

        mock_checkpoint_service.get_pending_approvals.return_value = [pending_cp]
        mock_checkpoint_service.get_checkpoints_by_execution.return_value = [pending_cp]

        status = await service.get_resume_status(execution_id)
        assert status["can_resume"] is False
        assert status["pending_count"] == 1

        # Step 3: Approve (via checkpoint API - simulated)
        # Now the checkpoint is approved
        approved_cp = MagicMock()
        approved_cp.id = checkpoint_id
        approved_cp.execution_id = execution_id
        approved_cp.status = CheckpointStatus.APPROVED
        approved_cp.node_id = "approval-gate"
        approved_cp.payload = {"type": "human_approval"}
        approved_cp.response = {}

        mock_checkpoint_service.get_checkpoint.return_value = approved_cp
        mock_execution_repo.resume.return_value = mock_execution

        # Step 4: Resume
        result = await service.resume_from_checkpoint(execution_id, checkpoint_id)

        assert result.status == ResumeStatus.SUCCESS
        assert result.next_node_id == "approval-gate"
        mock_execution_repo.resume.assert_called_once()
