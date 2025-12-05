# =============================================================================
# IPA Platform - Handoff Controller Unit Tests
# =============================================================================
# Sprint 8: Agent Handoff & Collaboration (Phase 2)
#
# Tests for the handoff controller including:
#   - HandoffPolicy enumeration
#   - HandoffStatus enumeration
#   - HandoffContext data structure
#   - HandoffRequest data structure
#   - HandoffResult data structure
#   - HandoffController handoff execution
#   - Context transfer validation
# =============================================================================

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

from src.domain.orchestration.handoff.controller import (
    HandoffController,
    HandoffContext,
    HandoffPolicy,
    HandoffRequest,
    HandoffResult,
    HandoffState,
    HandoffStatus,
)


# =============================================================================
# HandoffStatus Tests
# =============================================================================


class TestHandoffStatus:
    """Tests for HandoffStatus enum."""

    def test_status_values(self):
        """Test all status enum values."""
        assert HandoffStatus.INITIATED.value == "initiated"
        assert HandoffStatus.VALIDATING.value == "validating"
        assert HandoffStatus.TRANSFERRING.value == "transferring"
        assert HandoffStatus.COMPLETED.value == "completed"
        assert HandoffStatus.FAILED.value == "failed"
        assert HandoffStatus.CANCELLED.value == "cancelled"
        assert HandoffStatus.ROLLED_BACK.value == "rolled_back"

    def test_status_from_string(self):
        """Test creating status from string."""
        assert HandoffStatus("initiated") == HandoffStatus.INITIATED
        assert HandoffStatus("completed") == HandoffStatus.COMPLETED
        assert HandoffStatus("failed") == HandoffStatus.FAILED


# =============================================================================
# HandoffPolicy Tests
# =============================================================================


class TestHandoffPolicy:
    """Tests for HandoffPolicy enum."""

    def test_policy_values(self):
        """Test all policy enum values."""
        assert HandoffPolicy.IMMEDIATE.value == "immediate"
        assert HandoffPolicy.GRACEFUL.value == "graceful"
        assert HandoffPolicy.CONDITIONAL.value == "conditional"

    def test_policy_from_string(self):
        """Test creating policy from string."""
        assert HandoffPolicy("immediate") == HandoffPolicy.IMMEDIATE
        assert HandoffPolicy("graceful") == HandoffPolicy.GRACEFUL
        assert HandoffPolicy("conditional") == HandoffPolicy.CONDITIONAL


# =============================================================================
# HandoffContext Tests
# =============================================================================


class TestHandoffContext:
    """Tests for HandoffContext dataclass."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        context = HandoffContext(
            task_id="task-001",
            task_state={"status": "in_progress"},
        )

        assert context.task_id == "task-001"
        assert context.task_state == {"status": "in_progress"}
        assert context.conversation_history == []
        assert context.metadata == {}
        assert context.priority == 0
        assert context.timeout == 300

    def test_initialization_with_all_fields(self):
        """Test initialization with all fields."""
        history = [{"role": "user", "content": "Hello"}]
        metadata = {"source": "api"}

        context = HandoffContext(
            task_id="task-002",
            task_state={"step": 3},
            conversation_history=history,
            metadata=metadata,
            priority=5,
            timeout=600,
        )

        assert context.task_id == "task-002"
        assert context.conversation_history == history
        assert context.metadata == metadata
        assert context.priority == 5
        assert context.timeout == 600


# =============================================================================
# HandoffRequest Tests
# =============================================================================


class TestHandoffRequest:
    """Tests for HandoffRequest dataclass."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        source_id = uuid4()
        target_id = uuid4()
        context = HandoffContext(task_id="task-1", task_state={})

        request = HandoffRequest(
            source_agent_id=source_id,
            target_agent_id=target_id,
            context=context,
        )

        assert request.source_agent_id == source_id
        assert request.target_agent_id == target_id
        assert request.context == context
        assert request.policy == HandoffPolicy.GRACEFUL
        assert request.reason == ""
        assert isinstance(request.id, UUID)
        assert isinstance(request.created_at, datetime)

    def test_initialization_with_policy(self):
        """Test initialization with specific policy."""
        request = HandoffRequest(
            source_agent_id=uuid4(),
            target_agent_id=uuid4(),
            context=HandoffContext(task_id="task-2", task_state={}),
            policy=HandoffPolicy.IMMEDIATE,
            reason="Urgent transfer required",
        )

        assert request.policy == HandoffPolicy.IMMEDIATE
        assert request.reason == "Urgent transfer required"


# =============================================================================
# HandoffResult Tests
# =============================================================================


class TestHandoffResult:
    """Tests for HandoffResult dataclass."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        request_id = uuid4()
        source_id = uuid4()
        target_id = uuid4()

        result = HandoffResult(
            request_id=request_id,
            status=HandoffStatus.COMPLETED,
            source_agent_id=source_id,
            target_agent_id=target_id,
        )

        assert result.request_id == request_id
        assert result.status == HandoffStatus.COMPLETED
        assert result.source_agent_id == source_id
        assert result.target_agent_id == target_id
        assert result.completed_at is None
        assert result.error is None
        assert result.rollback_performed is False

    def test_failed_result(self):
        """Test failed result with error."""
        result = HandoffResult(
            request_id=uuid4(),
            status=HandoffStatus.FAILED,
            source_agent_id=uuid4(),
            target_agent_id=uuid4(),
            error="Target agent not available",
            rollback_performed=True,
        )

        assert result.status == HandoffStatus.FAILED
        assert result.error == "Target agent not available"
        assert result.rollback_performed is True


# =============================================================================
# HandoffState Tests
# =============================================================================


class TestHandoffState:
    """Tests for HandoffState dataclass."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        handoff_id = uuid4()
        source_id = uuid4()
        target_id = uuid4()

        state = HandoffState(
            handoff_id=handoff_id,
            source_agent_id=source_id,
            target_agent_id=target_id,
            status=HandoffStatus.INITIATED,
        )

        assert state.handoff_id == handoff_id
        assert state.source_agent_id == source_id
        assert state.target_agent_id == target_id
        assert state.status == HandoffStatus.INITIATED
        assert state.context is None
        assert isinstance(state.started_at, datetime)


# =============================================================================
# HandoffController Tests
# =============================================================================


class TestHandoffController:
    """Tests for HandoffController class."""

    @pytest.fixture
    def mock_agent_service(self):
        """Create mock agent service."""
        service = AsyncMock()
        service.get_agent = AsyncMock(return_value={"id": "agent-1", "name": "Test Agent"})
        service.get_agent_status = AsyncMock(return_value="idle")
        service.pause_agent = AsyncMock()
        service.activate_agent = AsyncMock()
        service.release_agent = AsyncMock()
        service.mark_handoff_pending = AsyncMock()
        service.restore_agent = AsyncMock()
        service.inject_context = AsyncMock()
        return service

    @pytest.fixture
    def mock_audit_logger(self):
        """Create mock audit logger."""
        logger = AsyncMock()
        logger.log = AsyncMock()
        return logger

    @pytest.fixture
    def controller(self, mock_agent_service, mock_audit_logger):
        """Create controller with mocks."""
        return HandoffController(
            agent_service=mock_agent_service,
            audit_logger=mock_audit_logger,
        )

    @pytest.fixture
    def sample_context(self):
        """Create sample handoff context."""
        return HandoffContext(
            task_id="task-001",
            task_state={"step": 1, "data": {"key": "value"}},
            conversation_history=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ],
        )

    # -------------------------------------------------------------------------
    # Initialization Tests
    # -------------------------------------------------------------------------

    def test_controller_initialization(self):
        """Test controller initialization."""
        controller = HandoffController()

        assert controller.active_handoffs == {}
        assert controller.handoff_states == {}

    def test_controller_with_services(self, mock_agent_service, mock_audit_logger):
        """Test controller initialization with services."""
        controller = HandoffController(
            agent_service=mock_agent_service,
            audit_logger=mock_audit_logger,
        )

        assert controller._agent_service == mock_agent_service
        assert controller._audit == mock_audit_logger

    # -------------------------------------------------------------------------
    # Initiate Handoff Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_initiate_handoff_success(self, controller, sample_context):
        """Test successful handoff initiation."""
        source_id = uuid4()
        target_id = uuid4()

        request = await controller.initiate_handoff(
            source_agent_id=source_id,
            target_agent_id=target_id,
            context=sample_context,
            policy=HandoffPolicy.GRACEFUL,
            reason="Test handoff",
        )

        assert request.source_agent_id == source_id
        assert request.target_agent_id == target_id
        assert request.context == sample_context
        assert request.policy == HandoffPolicy.GRACEFUL
        assert request.reason == "Test handoff"
        assert request.id in controller.active_handoffs

    @pytest.mark.asyncio
    async def test_initiate_handoff_validates_source(self, controller, sample_context):
        """Test that initiation validates source agent."""
        with pytest.raises(ValueError, match="Both source_agent_id and target_agent_id"):
            await controller.initiate_handoff(
                source_agent_id=None,
                target_agent_id=uuid4(),
                context=sample_context,
            )

    @pytest.mark.asyncio
    async def test_initiate_handoff_validates_target(self, controller, sample_context):
        """Test that initiation validates target agent."""
        with pytest.raises(ValueError, match="Both source_agent_id and target_agent_id"):
            await controller.initiate_handoff(
                source_agent_id=uuid4(),
                target_agent_id=None,
                context=sample_context,
            )

    @pytest.mark.asyncio
    async def test_initiate_handoff_prevents_self_handoff(self, controller, sample_context):
        """Test that self-handoff is prevented."""
        same_id = uuid4()

        with pytest.raises(ValueError, match="cannot be the same"):
            await controller.initiate_handoff(
                source_agent_id=same_id,
                target_agent_id=same_id,
                context=sample_context,
            )

    @pytest.mark.asyncio
    async def test_initiate_handoff_creates_state(self, controller, sample_context):
        """Test that initiation creates handoff state."""
        source_id = uuid4()
        target_id = uuid4()

        request = await controller.initiate_handoff(
            source_agent_id=source_id,
            target_agent_id=target_id,
            context=sample_context,
        )

        state = controller.handoff_states.get(request.id)
        assert state is not None
        assert state.status == HandoffStatus.INITIATED
        assert state.source_agent_id == source_id
        assert state.target_agent_id == target_id

    @pytest.mark.asyncio
    async def test_initiate_handoff_logs_audit(self, controller, sample_context, mock_audit_logger):
        """Test that initiation logs audit event."""
        await controller.initiate_handoff(
            source_agent_id=uuid4(),
            target_agent_id=uuid4(),
            context=sample_context,
        )

        mock_audit_logger.log.assert_called_once()
        call_kwargs = mock_audit_logger.log.call_args[1]
        assert call_kwargs["action"] == "handoff.initiated"

    # -------------------------------------------------------------------------
    # Execute Handoff Tests - Immediate Policy
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_execute_immediate_handoff(self, controller, sample_context, mock_agent_service):
        """Test immediate handoff execution."""
        source_id = uuid4()
        target_id = uuid4()

        request = await controller.initiate_handoff(
            source_agent_id=source_id,
            target_agent_id=target_id,
            context=sample_context,
            policy=HandoffPolicy.IMMEDIATE,
        )

        result = await controller.execute_handoff(request)

        assert result.status == HandoffStatus.COMPLETED
        assert result.request_id == request.id
        assert result.source_agent_id == source_id
        assert result.target_agent_id == target_id
        assert result.completed_at is not None
        assert result.duration_ms is not None

    @pytest.mark.asyncio
    async def test_immediate_handoff_pauses_source(self, controller, sample_context, mock_agent_service):
        """Test that immediate handoff pauses source agent."""
        source_id = uuid4()
        target_id = uuid4()

        request = await controller.initiate_handoff(
            source_agent_id=source_id,
            target_agent_id=target_id,
            context=sample_context,
            policy=HandoffPolicy.IMMEDIATE,
        )

        await controller.execute_handoff(request)

        mock_agent_service.pause_agent.assert_called_with(source_id)

    @pytest.mark.asyncio
    async def test_immediate_handoff_activates_target(self, controller, sample_context, mock_agent_service):
        """Test that immediate handoff activates target agent."""
        source_id = uuid4()
        target_id = uuid4()

        request = await controller.initiate_handoff(
            source_agent_id=source_id,
            target_agent_id=target_id,
            context=sample_context,
            policy=HandoffPolicy.IMMEDIATE,
        )

        await controller.execute_handoff(request)

        mock_agent_service.activate_agent.assert_called()

    # -------------------------------------------------------------------------
    # Execute Handoff Tests - Graceful Policy
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_execute_graceful_handoff(self, controller, sample_context, mock_agent_service):
        """Test graceful handoff execution."""
        source_id = uuid4()
        target_id = uuid4()

        request = await controller.initiate_handoff(
            source_agent_id=source_id,
            target_agent_id=target_id,
            context=sample_context,
            policy=HandoffPolicy.GRACEFUL,
        )

        result = await controller.execute_handoff(request)

        assert result.status == HandoffStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_graceful_handoff_marks_pending(self, controller, sample_context, mock_agent_service):
        """Test that graceful handoff marks source as pending."""
        source_id = uuid4()
        target_id = uuid4()

        request = await controller.initiate_handoff(
            source_agent_id=source_id,
            target_agent_id=target_id,
            context=sample_context,
            policy=HandoffPolicy.GRACEFUL,
        )

        await controller.execute_handoff(request)

        mock_agent_service.mark_handoff_pending.assert_called_with(source_id)

    # -------------------------------------------------------------------------
    # Execute Handoff Tests - Conditional Policy
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_execute_conditional_handoff_success(self, controller, sample_context):
        """Test conditional handoff with conditions met."""
        source_id = uuid4()
        target_id = uuid4()

        request = await controller.initiate_handoff(
            source_agent_id=source_id,
            target_agent_id=target_id,
            context=sample_context,
            policy=HandoffPolicy.CONDITIONAL,
            conditions={"confidence": "> 0.8"},
        )

        result = await controller.execute_handoff(request)

        # Currently always succeeds as condition evaluation returns True
        assert result.status == HandoffStatus.COMPLETED

    # -------------------------------------------------------------------------
    # Context Transfer Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_context_transfer_includes_task_data(self, controller, sample_context, mock_agent_service):
        """Test that context transfer includes task data."""
        source_id = uuid4()
        target_id = uuid4()

        request = await controller.initiate_handoff(
            source_agent_id=source_id,
            target_agent_id=target_id,
            context=sample_context,
            policy=HandoffPolicy.IMMEDIATE,
        )

        result = await controller.execute_handoff(request)

        # Check inject_context was called
        mock_agent_service.inject_context.assert_called()
        call_args = mock_agent_service.inject_context.call_args[0]
        assert call_args[0] == target_id

    @pytest.mark.asyncio
    async def test_result_includes_transferred_context(self, controller, sample_context):
        """Test that result includes transferred context summary."""
        request = await controller.initiate_handoff(
            source_agent_id=uuid4(),
            target_agent_id=uuid4(),
            context=sample_context,
            policy=HandoffPolicy.IMMEDIATE,
        )

        result = await controller.execute_handoff(request)

        assert "task_id" in result.transferred_context
        assert result.transferred_context["task_id"] == "task-001"

    # -------------------------------------------------------------------------
    # Failure and Rollback Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_execute_handoff_failure_triggers_rollback(
        self, mock_agent_service, mock_audit_logger, sample_context
    ):
        """Test that execution failure triggers rollback."""
        mock_agent_service.get_agent = AsyncMock(side_effect=Exception("Agent not found"))

        controller = HandoffController(
            agent_service=mock_agent_service,
            audit_logger=mock_audit_logger,
        )

        request = await controller.initiate_handoff(
            source_agent_id=uuid4(),
            target_agent_id=uuid4(),
            context=sample_context,
        )

        result = await controller.execute_handoff(request)

        assert result.status == HandoffStatus.FAILED
        assert result.error == "Agent not found"
        assert result.rollback_performed is True

    @pytest.mark.asyncio
    async def test_rollback_restores_source_agent(
        self, mock_agent_service, mock_audit_logger, sample_context
    ):
        """Test that rollback restores source agent."""
        source_id = uuid4()
        mock_agent_service.get_agent = AsyncMock(side_effect=Exception("Error"))

        controller = HandoffController(
            agent_service=mock_agent_service,
            audit_logger=mock_audit_logger,
        )

        request = await controller.initiate_handoff(
            source_agent_id=source_id,
            target_agent_id=uuid4(),
            context=sample_context,
        )

        await controller.execute_handoff(request)

        mock_agent_service.restore_agent.assert_called_with(source_id)

    # -------------------------------------------------------------------------
    # Cancel Handoff Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_cancel_handoff_success(self, controller, sample_context):
        """Test successful handoff cancellation."""
        request = await controller.initiate_handoff(
            source_agent_id=uuid4(),
            target_agent_id=uuid4(),
            context=sample_context,
        )

        result = await controller.cancel_handoff(request.id)

        assert result is True
        assert request.id not in controller.active_handoffs

    @pytest.mark.asyncio
    async def test_cancel_handoff_not_found(self, controller):
        """Test cancellation of non-existent handoff."""
        result = await controller.cancel_handoff(uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_updates_state(self, controller, sample_context):
        """Test that cancellation updates handoff state."""
        request = await controller.initiate_handoff(
            source_agent_id=uuid4(),
            target_agent_id=uuid4(),
            context=sample_context,
        )

        await controller.cancel_handoff(request.id)

        # State should be cancelled (but cleaned up)
        assert request.id not in controller.active_handoffs

    # -------------------------------------------------------------------------
    # Get Status Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_handoff_status_exists(self, controller, sample_context):
        """Test getting status of existing handoff."""
        request = await controller.initiate_handoff(
            source_agent_id=uuid4(),
            target_agent_id=uuid4(),
            context=sample_context,
        )

        status = await controller.get_handoff_status(request.id)

        assert status is not None
        assert status.handoff_id == request.id
        assert status.status == HandoffStatus.INITIATED

    @pytest.mark.asyncio
    async def test_get_handoff_status_not_found(self, controller):
        """Test getting status of non-existent handoff."""
        status = await controller.get_handoff_status(uuid4())

        assert status is None

    # -------------------------------------------------------------------------
    # Event Handler Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_completion_handler_called(self, controller, sample_context):
        """Test that completion handler is called."""
        handler = MagicMock()
        controller.register_completion_handler(handler)

        request = await controller.initiate_handoff(
            source_agent_id=uuid4(),
            target_agent_id=uuid4(),
            context=sample_context,
            policy=HandoffPolicy.IMMEDIATE,
        )

        await controller.execute_handoff(request)

        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_failure_handler_called(
        self, mock_agent_service, mock_audit_logger, sample_context
    ):
        """Test that failure handler is called on error."""
        mock_agent_service.get_agent = AsyncMock(side_effect=Exception("Error"))

        controller = HandoffController(
            agent_service=mock_agent_service,
            audit_logger=mock_audit_logger,
        )

        handler = MagicMock()
        controller.register_failure_handler(handler)

        request = await controller.initiate_handoff(
            source_agent_id=uuid4(),
            target_agent_id=uuid4(),
            context=sample_context,
        )

        await controller.execute_handoff(request)

        handler.assert_called_once()

    # -------------------------------------------------------------------------
    # Edge Cases
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_handoff_without_agent_service(self, sample_context):
        """Test handoff works without agent service."""
        controller = HandoffController()

        request = await controller.initiate_handoff(
            source_agent_id=uuid4(),
            target_agent_id=uuid4(),
            context=sample_context,
            policy=HandoffPolicy.IMMEDIATE,
        )

        result = await controller.execute_handoff(request)

        assert result.status == HandoffStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_handoff_cleanup_after_execution(self, controller, sample_context):
        """Test that handoff is cleaned up after execution."""
        request = await controller.initiate_handoff(
            source_agent_id=uuid4(),
            target_agent_id=uuid4(),
            context=sample_context,
        )

        await controller.execute_handoff(request)

        assert request.id not in controller.active_handoffs

    @pytest.mark.asyncio
    async def test_multiple_concurrent_handoffs(self, controller, sample_context):
        """Test multiple concurrent handoffs."""
        requests = []
        for _ in range(3):
            request = await controller.initiate_handoff(
                source_agent_id=uuid4(),
                target_agent_id=uuid4(),
                context=sample_context,
            )
            requests.append(request)

        assert len(controller.active_handoffs) == 3

        # Execute all
        results = await asyncio.gather(
            *[controller.execute_handoff(r) for r in requests]
        )

        assert all(r.status == HandoffStatus.COMPLETED for r in results)
        assert len(controller.active_handoffs) == 0
