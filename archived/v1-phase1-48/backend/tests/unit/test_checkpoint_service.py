# =============================================================================
# IPA Platform - Checkpoint Service Unit Tests
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Human-in-the-Loop
#
# Tests for the checkpoint service and related components including:
#   - CheckpointStatus enum
#   - CheckpointData dataclass
#   - CheckpointService business logic
#   - Approval and rejection workflows
#   - Expiration handling
# =============================================================================

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.domain.checkpoints import (
    CheckpointService,
    CheckpointStatus,
    CheckpointData,
)


# =============================================================================
# CheckpointStatus Tests
# =============================================================================


class TestCheckpointStatus:
    """Tests for CheckpointStatus enum."""

    def test_status_values(self):
        """Test all status enum values."""
        assert CheckpointStatus.PENDING.value == "pending"
        assert CheckpointStatus.APPROVED.value == "approved"
        assert CheckpointStatus.REJECTED.value == "rejected"
        assert CheckpointStatus.EXPIRED.value == "expired"

    def test_status_from_string(self):
        """Test creating status from string."""
        assert CheckpointStatus("pending") == CheckpointStatus.PENDING
        assert CheckpointStatus("approved") == CheckpointStatus.APPROVED
        assert CheckpointStatus("rejected") == CheckpointStatus.REJECTED
        assert CheckpointStatus("expired") == CheckpointStatus.EXPIRED

    def test_invalid_status_raises(self):
        """Test that invalid status string raises ValueError."""
        with pytest.raises(ValueError):
            CheckpointStatus("invalid")

    def test_status_is_string_enum(self):
        """Test that status enum inherits from str."""
        assert isinstance(CheckpointStatus.PENDING, str)
        assert CheckpointStatus.PENDING == "pending"


# =============================================================================
# CheckpointData Tests
# =============================================================================


class TestCheckpointData:
    """Tests for CheckpointData dataclass."""

    def test_initialization(self):
        """Test CheckpointData initialization."""
        checkpoint_id = uuid4()
        execution_id = uuid4()

        data = CheckpointData(
            id=checkpoint_id,
            execution_id=execution_id,
            node_id="approval-gate",
            status=CheckpointStatus.PENDING,
        )

        assert data.id == checkpoint_id
        assert data.execution_id == execution_id
        assert data.node_id == "approval-gate"
        assert data.status == CheckpointStatus.PENDING
        assert data.payload == {}
        assert data.response is None

    def test_initialization_with_payload(self):
        """Test CheckpointData with payload."""
        data = CheckpointData(
            id=uuid4(),
            execution_id=uuid4(),
            node_id="review-node",
            status=CheckpointStatus.PENDING,
            payload={"draft": "Review this content", "iteration": 1},
        )

        assert data.payload == {"draft": "Review this content", "iteration": 1}

    def test_from_model(self):
        """Test creating CheckpointData from model."""
        checkpoint_id = uuid4()
        execution_id = uuid4()
        now = datetime.utcnow()

        mock_model = MagicMock()
        mock_model.id = checkpoint_id
        mock_model.execution_id = execution_id
        mock_model.node_id = "test-node"
        mock_model.status = "pending"
        mock_model.payload = {"key": "value"}
        mock_model.response = None
        mock_model.responded_by = None
        mock_model.responded_at = None
        mock_model.expires_at = now + timedelta(hours=24)
        mock_model.created_at = now
        mock_model.notes = "Test notes"

        data = CheckpointData.from_model(mock_model)

        assert data.id == checkpoint_id
        assert data.execution_id == execution_id
        assert data.node_id == "test-node"
        assert data.status == CheckpointStatus.PENDING
        assert data.payload == {"key": "value"}
        assert data.notes == "Test notes"

    def test_from_model_invalid_status(self):
        """Test from_model defaults to PENDING for invalid status."""
        mock_model = MagicMock()
        mock_model.id = uuid4()
        mock_model.execution_id = uuid4()
        mock_model.node_id = "test-node"
        mock_model.status = "invalid_status"
        mock_model.payload = {}
        mock_model.response = None
        mock_model.responded_by = None
        mock_model.responded_at = None
        mock_model.expires_at = None
        mock_model.created_at = None
        mock_model.notes = None

        data = CheckpointData.from_model(mock_model)

        assert data.status == CheckpointStatus.PENDING

    def test_to_dict(self):
        """Test CheckpointData serialization."""
        checkpoint_id = uuid4()
        execution_id = uuid4()
        user_id = uuid4()
        now = datetime.utcnow()

        data = CheckpointData(
            id=checkpoint_id,
            execution_id=execution_id,
            node_id="approval-gate",
            status=CheckpointStatus.APPROVED,
            payload={"content": "test"},
            response={"action": "proceed"},
            responded_by=user_id,
            responded_at=now,
            expires_at=now + timedelta(hours=24),
            created_at=now,
            notes="Approved by manager",
        )

        result = data.to_dict()

        assert result["id"] == str(checkpoint_id)
        assert result["execution_id"] == str(execution_id)
        assert result["node_id"] == "approval-gate"
        assert result["status"] == "approved"
        assert result["payload"] == {"content": "test"}
        assert result["response"] == {"action": "proceed"}
        assert result["responded_by"] == str(user_id)
        assert result["notes"] == "Approved by manager"

    def test_to_dict_with_none_values(self):
        """Test to_dict handles None values correctly."""
        data = CheckpointData(
            id=uuid4(),
            execution_id=uuid4(),
            node_id="test",
            status=CheckpointStatus.PENDING,
        )

        result = data.to_dict()

        assert result["response"] is None
        assert result["responded_by"] is None
        assert result["responded_at"] is None
        assert result["expires_at"] is None
        assert result["created_at"] is None


# =============================================================================
# CheckpointService Tests
# =============================================================================


class TestCheckpointService:
    """Tests for CheckpointService class."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock checkpoint repository."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repository):
        """Create checkpoint service with mock repository."""
        return CheckpointService(mock_repository, default_timeout_hours=24)

    @pytest.mark.asyncio
    async def test_create_checkpoint(self, service, mock_repository):
        """Test creating a checkpoint."""
        execution_id = uuid4()
        checkpoint_id = uuid4()
        now = datetime.utcnow()

        mock_checkpoint = MagicMock()
        mock_checkpoint.id = checkpoint_id
        mock_checkpoint.execution_id = execution_id
        mock_checkpoint.node_id = "approval-gate"
        mock_checkpoint.status = "pending"
        mock_checkpoint.payload = {"draft": "Review this"}
        mock_checkpoint.response = None
        mock_checkpoint.responded_by = None
        mock_checkpoint.responded_at = None
        mock_checkpoint.expires_at = now + timedelta(hours=24)
        mock_checkpoint.created_at = now
        mock_checkpoint.notes = None

        mock_repository.create.return_value = mock_checkpoint

        result = await service.create_checkpoint(
            execution_id=execution_id,
            node_id="approval-gate",
            payload={"draft": "Review this"},
        )

        assert result.id == checkpoint_id
        assert result.execution_id == execution_id
        assert result.node_id == "approval-gate"
        assert result.status == CheckpointStatus.PENDING
        mock_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_checkpoint_with_custom_timeout(self, service, mock_repository):
        """Test creating checkpoint with custom timeout."""
        execution_id = uuid4()
        mock_checkpoint = MagicMock()
        mock_checkpoint.id = uuid4()
        mock_checkpoint.execution_id = execution_id
        mock_checkpoint.node_id = "test"
        mock_checkpoint.status = "pending"
        mock_checkpoint.payload = {}
        mock_checkpoint.response = None
        mock_checkpoint.responded_by = None
        mock_checkpoint.responded_at = None
        mock_checkpoint.expires_at = datetime.utcnow() + timedelta(hours=48)
        mock_checkpoint.created_at = datetime.utcnow()
        mock_checkpoint.notes = None

        mock_repository.create.return_value = mock_checkpoint

        await service.create_checkpoint(
            execution_id=execution_id,
            node_id="test",
            payload={},
            timeout_hours=48,
        )

        call_args = mock_repository.create.call_args
        # Check that expires_at is roughly 48 hours from now
        assert call_args.kwargs.get("expires_at") is not None

    @pytest.mark.asyncio
    async def test_get_checkpoint_found(self, service, mock_repository):
        """Test getting an existing checkpoint."""
        checkpoint_id = uuid4()
        execution_id = uuid4()

        mock_checkpoint = MagicMock()
        mock_checkpoint.id = checkpoint_id
        mock_checkpoint.execution_id = execution_id
        mock_checkpoint.node_id = "test"
        mock_checkpoint.status = "pending"
        mock_checkpoint.payload = {}
        mock_checkpoint.response = None
        mock_checkpoint.responded_by = None
        mock_checkpoint.responded_at = None
        mock_checkpoint.expires_at = None
        mock_checkpoint.created_at = None
        mock_checkpoint.notes = None

        mock_repository.get.return_value = mock_checkpoint

        result = await service.get_checkpoint(checkpoint_id)

        assert result is not None
        assert result.id == checkpoint_id
        mock_repository.get.assert_called_once_with(checkpoint_id)

    @pytest.mark.asyncio
    async def test_get_checkpoint_not_found(self, service, mock_repository):
        """Test getting non-existent checkpoint."""
        mock_repository.get.return_value = None

        result = await service.get_checkpoint(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_pending_approvals(self, service, mock_repository):
        """Test listing pending checkpoints."""
        checkpoint1 = MagicMock()
        checkpoint1.id = uuid4()
        checkpoint1.execution_id = uuid4()
        checkpoint1.node_id = "node1"
        checkpoint1.status = "pending"
        checkpoint1.payload = {}
        checkpoint1.response = None
        checkpoint1.responded_by = None
        checkpoint1.responded_at = None
        checkpoint1.expires_at = None
        checkpoint1.created_at = datetime.utcnow()
        checkpoint1.notes = None

        checkpoint2 = MagicMock()
        checkpoint2.id = uuid4()
        checkpoint2.execution_id = uuid4()
        checkpoint2.node_id = "node2"
        checkpoint2.status = "pending"
        checkpoint2.payload = {}
        checkpoint2.response = None
        checkpoint2.responded_by = None
        checkpoint2.responded_at = None
        checkpoint2.expires_at = None
        checkpoint2.created_at = datetime.utcnow()
        checkpoint2.notes = None

        mock_repository.get_pending.return_value = [checkpoint1, checkpoint2]

        result = await service.get_pending_approvals(limit=10)

        assert len(result) == 2
        assert all(cp.status == CheckpointStatus.PENDING for cp in result)
        mock_repository.get_pending.assert_called_once_with(limit=10, execution_id=None)

    @pytest.mark.asyncio
    async def test_approve_checkpoint_success(self, service, mock_repository):
        """Test approving a checkpoint."""
        checkpoint_id = uuid4()
        user_id = uuid4()
        now = datetime.utcnow()

        pending_checkpoint = MagicMock()
        pending_checkpoint.status = "pending"

        approved_checkpoint = MagicMock()
        approved_checkpoint.id = checkpoint_id
        approved_checkpoint.execution_id = uuid4()
        approved_checkpoint.node_id = "test"
        approved_checkpoint.status = "approved"
        approved_checkpoint.payload = {}
        approved_checkpoint.response = {"action": "proceed"}
        approved_checkpoint.responded_by = user_id
        approved_checkpoint.responded_at = now
        approved_checkpoint.expires_at = None
        approved_checkpoint.created_at = now
        approved_checkpoint.notes = None

        mock_repository.get.return_value = pending_checkpoint
        mock_repository.update_status.return_value = approved_checkpoint

        result = await service.approve_checkpoint(
            checkpoint_id=checkpoint_id,
            user_id=user_id,
            response={"action": "proceed"},
        )

        assert result is not None
        assert result.status == CheckpointStatus.APPROVED
        mock_repository.update_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_checkpoint_not_pending_raises(self, service, mock_repository):
        """Test that approving non-pending checkpoint raises error."""
        checkpoint_id = uuid4()

        mock_checkpoint = MagicMock()
        mock_checkpoint.status = "approved"  # Already approved

        mock_repository.get.return_value = mock_checkpoint

        with pytest.raises(ValueError) as exc:
            await service.approve_checkpoint(
                checkpoint_id=checkpoint_id,
                user_id=uuid4(),
            )

        assert "Only PENDING checkpoints can be approved" in str(exc.value)

    @pytest.mark.asyncio
    async def test_approve_checkpoint_not_found(self, service, mock_repository):
        """Test approving non-existent checkpoint."""
        mock_repository.get.return_value = None

        result = await service.approve_checkpoint(
            checkpoint_id=uuid4(),
            user_id=uuid4(),
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_reject_checkpoint_success(self, service, mock_repository):
        """Test rejecting a checkpoint."""
        checkpoint_id = uuid4()
        user_id = uuid4()
        now = datetime.utcnow()

        pending_checkpoint = MagicMock()
        pending_checkpoint.status = "pending"

        rejected_checkpoint = MagicMock()
        rejected_checkpoint.id = checkpoint_id
        rejected_checkpoint.execution_id = uuid4()
        rejected_checkpoint.node_id = "test"
        rejected_checkpoint.status = "rejected"
        rejected_checkpoint.payload = {}
        rejected_checkpoint.response = {"rejection_reason": "Not good enough"}
        rejected_checkpoint.responded_by = user_id
        rejected_checkpoint.responded_at = now
        rejected_checkpoint.expires_at = None
        rejected_checkpoint.created_at = now
        rejected_checkpoint.notes = None

        mock_repository.get.return_value = pending_checkpoint
        mock_repository.update_status.return_value = rejected_checkpoint

        result = await service.reject_checkpoint(
            checkpoint_id=checkpoint_id,
            user_id=user_id,
            reason="Not good enough",
        )

        assert result is not None
        assert result.status == CheckpointStatus.REJECTED
        mock_repository.update_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_reject_checkpoint_not_pending_raises(self, service, mock_repository):
        """Test that rejecting non-pending checkpoint raises error."""
        mock_checkpoint = MagicMock()
        mock_checkpoint.status = "expired"

        mock_repository.get.return_value = mock_checkpoint

        with pytest.raises(ValueError) as exc:
            await service.reject_checkpoint(
                checkpoint_id=uuid4(),
                user_id=uuid4(),
            )

        assert "Only PENDING checkpoints can be rejected" in str(exc.value)

    @pytest.mark.asyncio
    async def test_expire_old_checkpoints(self, service, mock_repository):
        """Test expiring old checkpoints."""
        mock_repository.expire_old.return_value = 5

        result = await service.expire_old_checkpoints()

        assert result == 5
        mock_repository.expire_old.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_checkpoints_by_execution(self, service, mock_repository):
        """Test getting checkpoints by execution."""
        execution_id = uuid4()

        checkpoint = MagicMock()
        checkpoint.id = uuid4()
        checkpoint.execution_id = execution_id
        checkpoint.node_id = "test"
        checkpoint.status = "pending"
        checkpoint.payload = {}
        checkpoint.response = None
        checkpoint.responded_by = None
        checkpoint.responded_at = None
        checkpoint.expires_at = None
        checkpoint.created_at = None
        checkpoint.notes = None

        mock_repository.get_by_execution.return_value = [checkpoint]

        result = await service.get_checkpoints_by_execution(execution_id)

        assert len(result) == 1
        assert result[0].execution_id == execution_id
        mock_repository.get_by_execution.assert_called_once_with(
            execution_id=execution_id,
            include_expired=False,
        )

    @pytest.mark.asyncio
    async def test_get_stats(self, service, mock_repository):
        """Test getting checkpoint statistics."""
        mock_repository.get_stats.return_value = {
            "pending": 5,
            "approved": 10,
            "rejected": 2,
            "expired": 1,
            "total": 18,
            "avg_response_seconds": 3600.0,
        }

        result = await service.get_stats()

        assert result["pending"] == 5
        assert result["approved"] == 10
        assert result["total"] == 18
        mock_repository.get_stats.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_delete_checkpoint(self, service, mock_repository):
        """Test deleting a checkpoint."""
        checkpoint_id = uuid4()
        mock_repository.delete.return_value = True

        result = await service.delete_checkpoint(checkpoint_id)

        assert result is True
        mock_repository.delete.assert_called_once_with(checkpoint_id)


# =============================================================================
# Full Workflow Tests
# =============================================================================


class TestCheckpointWorkflows:
    """Tests for complete checkpoint workflows."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repository):
        """Create service."""
        return CheckpointService(mock_repository)

    @pytest.mark.asyncio
    async def test_create_and_approve_workflow(self, service, mock_repository):
        """Test complete create → approve workflow."""
        execution_id = uuid4()
        checkpoint_id = uuid4()
        user_id = uuid4()
        now = datetime.utcnow()

        # Create checkpoint
        created_checkpoint = MagicMock()
        created_checkpoint.id = checkpoint_id
        created_checkpoint.execution_id = execution_id
        created_checkpoint.node_id = "approval"
        created_checkpoint.status = "pending"
        created_checkpoint.payload = {"draft": "Content for review"}
        created_checkpoint.response = None
        created_checkpoint.responded_by = None
        created_checkpoint.responded_at = None
        created_checkpoint.expires_at = now + timedelta(hours=24)
        created_checkpoint.created_at = now
        created_checkpoint.notes = None

        mock_repository.create.return_value = created_checkpoint

        created = await service.create_checkpoint(
            execution_id=execution_id,
            node_id="approval",
            payload={"draft": "Content for review"},
        )

        assert created.status == CheckpointStatus.PENDING

        # Approve checkpoint
        pending_for_approval = MagicMock()
        pending_for_approval.status = "pending"

        approved_checkpoint = MagicMock()
        approved_checkpoint.id = checkpoint_id
        approved_checkpoint.execution_id = execution_id
        approved_checkpoint.node_id = "approval"
        approved_checkpoint.status = "approved"
        approved_checkpoint.payload = {"draft": "Content for review"}
        approved_checkpoint.response = {"feedback": "Looks good!"}
        approved_checkpoint.responded_by = user_id
        approved_checkpoint.responded_at = now
        approved_checkpoint.expires_at = now + timedelta(hours=24)
        approved_checkpoint.created_at = now
        approved_checkpoint.notes = None

        mock_repository.get.return_value = pending_for_approval
        mock_repository.update_status.return_value = approved_checkpoint

        approved = await service.approve_checkpoint(
            checkpoint_id=checkpoint_id,
            user_id=user_id,
            feedback="Looks good!",
        )

        assert approved.status == CheckpointStatus.APPROVED
        assert approved.responded_by == user_id

    @pytest.mark.asyncio
    async def test_create_and_reject_workflow(self, service, mock_repository):
        """Test complete create → reject workflow."""
        execution_id = uuid4()
        checkpoint_id = uuid4()
        user_id = uuid4()
        now = datetime.utcnow()

        # Setup
        pending_checkpoint = MagicMock()
        pending_checkpoint.status = "pending"

        rejected_checkpoint = MagicMock()
        rejected_checkpoint.id = checkpoint_id
        rejected_checkpoint.execution_id = execution_id
        rejected_checkpoint.node_id = "review"
        rejected_checkpoint.status = "rejected"
        rejected_checkpoint.payload = {}
        rejected_checkpoint.response = {"rejection_reason": "Needs more work"}
        rejected_checkpoint.responded_by = user_id
        rejected_checkpoint.responded_at = now
        rejected_checkpoint.expires_at = None
        rejected_checkpoint.created_at = now
        rejected_checkpoint.notes = None

        mock_repository.get.return_value = pending_checkpoint
        mock_repository.update_status.return_value = rejected_checkpoint

        result = await service.reject_checkpoint(
            checkpoint_id=checkpoint_id,
            user_id=user_id,
            reason="Needs more work",
        )

        assert result.status == CheckpointStatus.REJECTED

    @pytest.mark.asyncio
    async def test_cannot_double_approve(self, service, mock_repository):
        """Test that approved checkpoint cannot be approved again."""
        already_approved = MagicMock()
        already_approved.status = "approved"

        mock_repository.get.return_value = already_approved

        with pytest.raises(ValueError):
            await service.approve_checkpoint(
                checkpoint_id=uuid4(),
                user_id=uuid4(),
            )

    @pytest.mark.asyncio
    async def test_cannot_reject_approved(self, service, mock_repository):
        """Test that approved checkpoint cannot be rejected."""
        already_approved = MagicMock()
        already_approved.status = "approved"

        mock_repository.get.return_value = already_approved

        with pytest.raises(ValueError):
            await service.reject_checkpoint(
                checkpoint_id=uuid4(),
                user_id=uuid4(),
            )
