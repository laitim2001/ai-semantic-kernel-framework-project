# =============================================================================
# IPA Platform - Approval Gateway Unit Tests
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Human-in-the-Loop
#
# Tests for the approval gateway executor including:
#   - HumanApprovalRequest data structure
#   - ApprovalResponse data structure
#   - ApprovalGateway executor logic
#   - Approval workflow scenarios
# =============================================================================

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.domain.workflows.executors.approval import (
    ApprovalAction,
    ApprovalGateway,
    ApprovalResponse,
    HumanApprovalRequest,
)
from src.domain.checkpoints import CheckpointStatus


# =============================================================================
# ApprovalAction Tests
# =============================================================================


class TestApprovalAction:
    """Tests for ApprovalAction enum."""

    def test_action_values(self):
        """Test all action enum values."""
        assert ApprovalAction.APPROVE.value == "approve"
        assert ApprovalAction.REJECT.value == "reject"
        assert ApprovalAction.MODIFY.value == "modify"
        assert ApprovalAction.RETRY.value == "retry"

    def test_action_from_string(self):
        """Test creating action from string."""
        assert ApprovalAction("approve") == ApprovalAction.APPROVE
        assert ApprovalAction("reject") == ApprovalAction.REJECT
        assert ApprovalAction("modify") == ApprovalAction.MODIFY
        assert ApprovalAction("retry") == ApprovalAction.RETRY


# =============================================================================
# HumanApprovalRequest Tests
# =============================================================================


class TestHumanApprovalRequest:
    """Tests for HumanApprovalRequest dataclass."""

    def test_initialization(self):
        """Test basic initialization."""
        execution_id = uuid4()
        request = HumanApprovalRequest(
            execution_id=execution_id,
            node_id="approval-gate",
        )

        assert request.execution_id == execution_id
        assert request.node_id == "approval-gate"
        assert request.prompt == ""
        assert request.content == ""
        assert request.iteration == 1

    def test_initialization_with_content(self):
        """Test initialization with content."""
        request = HumanApprovalRequest(
            execution_id=uuid4(),
            node_id="review",
            agent_id=uuid4(),
            prompt="Write a summary",
            content="Here is the summary...",
            context={"user_id": "123"},
            iteration=2,
        )

        assert request.prompt == "Write a summary"
        assert request.content == "Here is the summary..."
        assert request.context == {"user_id": "123"}
        assert request.iteration == 2

    def test_to_dict(self):
        """Test serialization to dictionary."""
        execution_id = uuid4()
        agent_id = uuid4()

        request = HumanApprovalRequest(
            execution_id=execution_id,
            node_id="test",
            agent_id=agent_id,
            content="Test content",
        )

        result = request.to_dict()

        assert result["execution_id"] == str(execution_id)
        assert result["node_id"] == "test"
        assert result["agent_id"] == str(agent_id)
        assert result["content"] == "Test content"

    def test_to_checkpoint_payload(self):
        """Test conversion to checkpoint payload format."""
        request = HumanApprovalRequest(
            execution_id=uuid4(),
            node_id="review",
            content="Review this content",
            iteration=1,
        )

        payload = request.to_checkpoint_payload()

        assert payload["type"] == "human_approval"
        assert payload["content"] == "Review this content"
        assert payload["iteration"] == 1


# =============================================================================
# ApprovalResponse Tests
# =============================================================================


class TestApprovalResponse:
    """Tests for ApprovalResponse dataclass."""

    def test_initialization(self):
        """Test basic initialization."""
        user_id = uuid4()
        response = ApprovalResponse(
            action=ApprovalAction.APPROVE,
            user_id=user_id,
        )

        assert response.action == ApprovalAction.APPROVE
        assert response.user_id == user_id
        assert response.responded_at is not None

    def test_initialization_with_modifications(self):
        """Test initialization with modifications."""
        response = ApprovalResponse(
            action=ApprovalAction.MODIFY,
            user_id=uuid4(),
            modified_content="Modified content here",
            notes="Fixed some issues",
        )

        assert response.action == ApprovalAction.MODIFY
        assert response.modified_content == "Modified content here"
        assert response.notes == "Fixed some issues"

    def test_initialization_with_feedback(self):
        """Test initialization with retry feedback."""
        response = ApprovalResponse(
            action=ApprovalAction.RETRY,
            user_id=uuid4(),
            feedback="Please be more concise",
        )

        assert response.action == ApprovalAction.RETRY
        assert response.feedback == "Please be more concise"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        user_id = uuid4()
        now = datetime.utcnow()

        response = ApprovalResponse(
            action=ApprovalAction.APPROVE,
            user_id=user_id,
            notes="Looks good",
            responded_at=now,
        )

        result = response.to_dict()

        assert result["action"] == "approve"
        assert result["user_id"] == str(user_id)
        assert result["notes"] == "Looks good"


# =============================================================================
# ApprovalGateway Tests
# =============================================================================


class TestApprovalGateway:
    """Tests for ApprovalGateway class."""

    @pytest.fixture
    def mock_checkpoint_service(self):
        """Create mock checkpoint service."""
        service = AsyncMock()
        return service

    @pytest.fixture
    def gateway(self, mock_checkpoint_service):
        """Create approval gateway with mock service."""
        return ApprovalGateway(
            checkpoint_service=mock_checkpoint_service,
            timeout_hours=24,
            max_iterations=3,
        )

    @pytest.mark.asyncio
    async def test_on_agent_response_creates_checkpoint(
        self, gateway, mock_checkpoint_service
    ):
        """Test that on_agent_response creates a checkpoint."""
        execution_id = uuid4()
        checkpoint_id = uuid4()

        mock_checkpoint = MagicMock()
        mock_checkpoint.id = checkpoint_id
        mock_checkpoint_service.create_checkpoint.return_value = mock_checkpoint

        request = HumanApprovalRequest(
            execution_id=execution_id,
            node_id="review-gate",
            content="Review this output",
        )

        result = await gateway.on_agent_response(request)

        assert result == checkpoint_id
        mock_checkpoint_service.create_checkpoint.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_agent_response_max_iterations_exceeded(
        self, gateway, mock_checkpoint_service
    ):
        """Test that exceeding max iterations raises error."""
        request = HumanApprovalRequest(
            execution_id=uuid4(),
            node_id="review",
            iteration=4,  # Exceeds max of 3
        )

        with pytest.raises(ValueError) as exc:
            await gateway.on_agent_response(request)

        assert "Maximum approval iterations" in str(exc.value)

    @pytest.mark.asyncio
    async def test_on_human_feedback_approve(
        self, gateway, mock_checkpoint_service
    ):
        """Test approval feedback processing."""
        checkpoint_id = uuid4()
        user_id = uuid4()

        # Store pending request
        request = HumanApprovalRequest(
            execution_id=uuid4(),
            node_id="review",
            content="Original content",
        )
        gateway._pending_requests[checkpoint_id] = request

        mock_checkpoint_service.approve_checkpoint.return_value = MagicMock()

        response = ApprovalResponse(
            action=ApprovalAction.APPROVE,
            user_id=user_id,
        )

        result = await gateway.on_human_feedback(checkpoint_id, response)

        assert result["action"] == "continue"
        assert result["content"] == "Original content"
        mock_checkpoint_service.approve_checkpoint.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_human_feedback_reject(
        self, gateway, mock_checkpoint_service
    ):
        """Test rejection feedback processing."""
        checkpoint_id = uuid4()
        user_id = uuid4()

        gateway._pending_requests[checkpoint_id] = HumanApprovalRequest(
            execution_id=uuid4(),
            node_id="review",
            content="Content",
        )

        mock_checkpoint_service.reject_checkpoint.return_value = MagicMock()

        response = ApprovalResponse(
            action=ApprovalAction.REJECT,
            user_id=user_id,
            notes="Not acceptable",
        )

        result = await gateway.on_human_feedback(checkpoint_id, response)

        assert result["action"] == "stop"
        assert result["reason"] == "Not acceptable"
        mock_checkpoint_service.reject_checkpoint.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_human_feedback_modify(
        self, gateway, mock_checkpoint_service
    ):
        """Test modification feedback processing."""
        checkpoint_id = uuid4()
        user_id = uuid4()

        gateway._pending_requests[checkpoint_id] = HumanApprovalRequest(
            execution_id=uuid4(),
            node_id="review",
            content="Original content",
        )

        mock_checkpoint_service.approve_checkpoint.return_value = MagicMock()

        response = ApprovalResponse(
            action=ApprovalAction.MODIFY,
            user_id=user_id,
            modified_content="Modified content",
        )

        result = await gateway.on_human_feedback(checkpoint_id, response)

        assert result["action"] == "continue"
        assert result["content"] == "Modified content"

    @pytest.mark.asyncio
    async def test_on_human_feedback_retry(
        self, gateway, mock_checkpoint_service
    ):
        """Test retry feedback processing."""
        checkpoint_id = uuid4()
        user_id = uuid4()

        gateway._pending_requests[checkpoint_id] = HumanApprovalRequest(
            execution_id=uuid4(),
            node_id="review",
            content="Content",
            iteration=1,
        )

        mock_checkpoint_service.reject_checkpoint.return_value = MagicMock()

        response = ApprovalResponse(
            action=ApprovalAction.RETRY,
            user_id=user_id,
            feedback="Please be more concise",
        )

        result = await gateway.on_human_feedback(checkpoint_id, response)

        assert result["action"] == "retry"
        assert result["feedback"] == "Please be more concise"
        assert result["iteration"] == 2

    @pytest.mark.asyncio
    async def test_on_checkpoint_save(self, gateway, mock_checkpoint_service):
        """Test saving workflow state checkpoint."""
        execution_id = uuid4()
        checkpoint_id = uuid4()

        mock_checkpoint = MagicMock()
        mock_checkpoint.id = checkpoint_id
        mock_checkpoint_service.create_checkpoint.return_value = mock_checkpoint

        result = await gateway.on_checkpoint_save(
            execution_id=execution_id,
            node_id="state-save",
            state={"current_step": 5},
        )

        assert result == checkpoint_id
        call_args = mock_checkpoint_service.create_checkpoint.call_args
        assert call_args.kwargs["payload"]["type"] == "state_checkpoint"

    @pytest.mark.asyncio
    async def test_on_checkpoint_restore_approved(
        self, gateway, mock_checkpoint_service
    ):
        """Test restoring state from approved checkpoint."""
        checkpoint_id = uuid4()

        mock_checkpoint = MagicMock()
        mock_checkpoint.status = CheckpointStatus.APPROVED
        mock_checkpoint.payload = {
            "type": "state_checkpoint",
            "state": {"current_step": 5},
        }
        mock_checkpoint_service.get_checkpoint.return_value = mock_checkpoint

        result = await gateway.on_checkpoint_restore(checkpoint_id)

        assert result == {"current_step": 5}

    @pytest.mark.asyncio
    async def test_on_checkpoint_restore_not_approved(
        self, gateway, mock_checkpoint_service
    ):
        """Test restore returns None for non-approved checkpoint."""
        mock_checkpoint = MagicMock()
        mock_checkpoint.status = CheckpointStatus.PENDING
        mock_checkpoint_service.get_checkpoint.return_value = mock_checkpoint

        result = await gateway.on_checkpoint_restore(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_on_checkpoint_restore_not_found(
        self, gateway, mock_checkpoint_service
    ):
        """Test restore returns None when checkpoint not found."""
        mock_checkpoint_service.get_checkpoint.return_value = None

        result = await gateway.on_checkpoint_restore(uuid4())

        assert result is None

    def test_clear_pending_request(self, gateway):
        """Test clearing pending request from memory."""
        checkpoint_id = uuid4()
        gateway._pending_requests[checkpoint_id] = HumanApprovalRequest(
            execution_id=uuid4(),
            node_id="test",
        )

        gateway.clear_pending_request(checkpoint_id)

        assert checkpoint_id not in gateway._pending_requests


# =============================================================================
# Workflow Scenario Tests
# =============================================================================


class TestApprovalWorkflowScenarios:
    """Tests for complete approval workflow scenarios."""

    @pytest.fixture
    def mock_checkpoint_service(self):
        """Create mock checkpoint service."""
        return AsyncMock()

    @pytest.fixture
    def gateway(self, mock_checkpoint_service):
        """Create approval gateway."""
        return ApprovalGateway(mock_checkpoint_service)

    @pytest.mark.asyncio
    async def test_full_approval_workflow(
        self, gateway, mock_checkpoint_service
    ):
        """Test complete approval workflow: create → approve → continue."""
        execution_id = uuid4()
        checkpoint_id = uuid4()
        user_id = uuid4()

        # Step 1: Agent produces output
        mock_checkpoint = MagicMock()
        mock_checkpoint.id = checkpoint_id
        mock_checkpoint_service.create_checkpoint.return_value = mock_checkpoint

        request = HumanApprovalRequest(
            execution_id=execution_id,
            node_id="review-gate",
            content="Agent's draft response",
        )

        created_id = await gateway.on_agent_response(request)
        assert created_id == checkpoint_id

        # Step 2: Human approves
        mock_checkpoint_service.approve_checkpoint.return_value = MagicMock()

        response = ApprovalResponse(
            action=ApprovalAction.APPROVE,
            user_id=user_id,
        )

        result = await gateway.on_human_feedback(checkpoint_id, response)
        assert result["action"] == "continue"

    @pytest.mark.asyncio
    async def test_rejection_workflow(
        self, gateway, mock_checkpoint_service
    ):
        """Test rejection workflow: create → reject → stop."""
        checkpoint_id = uuid4()

        # Setup
        mock_checkpoint = MagicMock()
        mock_checkpoint.id = checkpoint_id
        mock_checkpoint_service.create_checkpoint.return_value = mock_checkpoint
        mock_checkpoint_service.reject_checkpoint.return_value = MagicMock()

        request = HumanApprovalRequest(
            execution_id=uuid4(),
            node_id="review-gate",
            content="Agent's output",
        )

        await gateway.on_agent_response(request)

        # Reject
        response = ApprovalResponse(
            action=ApprovalAction.REJECT,
            user_id=uuid4(),
            notes="Quality issues",
        )

        result = await gateway.on_human_feedback(checkpoint_id, response)
        assert result["action"] == "stop"

    @pytest.mark.asyncio
    async def test_retry_workflow(
        self, gateway, mock_checkpoint_service
    ):
        """Test retry workflow with multiple iterations."""
        checkpoint_id = uuid4()

        mock_checkpoint = MagicMock()
        mock_checkpoint.id = checkpoint_id
        mock_checkpoint_service.create_checkpoint.return_value = mock_checkpoint
        mock_checkpoint_service.reject_checkpoint.return_value = MagicMock()
        mock_checkpoint_service.approve_checkpoint.return_value = MagicMock()

        # Iteration 1
        request = HumanApprovalRequest(
            execution_id=uuid4(),
            node_id="review",
            content="First attempt",
            iteration=1,
        )
        await gateway.on_agent_response(request)

        # Request retry
        retry_response = ApprovalResponse(
            action=ApprovalAction.RETRY,
            user_id=uuid4(),
            feedback="Be more detailed",
        )
        result = await gateway.on_human_feedback(checkpoint_id, retry_response)

        assert result["action"] == "retry"
        assert result["iteration"] == 2

        # Iteration 2 - create new checkpoint
        gateway._pending_requests[checkpoint_id] = HumanApprovalRequest(
            execution_id=uuid4(),
            node_id="review",
            content="Second attempt",
            iteration=2,
        )

        # Approve iteration 2
        approve_response = ApprovalResponse(
            action=ApprovalAction.APPROVE,
            user_id=uuid4(),
        )
        result = await gateway.on_human_feedback(checkpoint_id, approve_response)

        assert result["action"] == "continue"
