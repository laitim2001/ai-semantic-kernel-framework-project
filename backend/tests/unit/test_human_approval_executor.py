# =============================================================================
# IPA Platform - Human Approval Executor Tests
# =============================================================================
# Phase 5: MVP Core Official API Migration
# Sprint 28, Story S28-1: HumanApprovalExecutor (10 pts)
#
# Test coverage for:
#   - HumanApprovalExecutor class
#   - ApprovalRequest/Response models
#   - EscalationPolicy class
#   - NotificationConfig class
#   - Factory functions
# =============================================================================

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from src.integrations.agent_framework.core.approval import (
    HumanApprovalExecutor,
    ApprovalRequest,
    ApprovalResponse,
    ApprovalStatus,
    ApprovalState,
    RiskLevel,
    EscalationPolicy,
    NotificationConfig,
    create_approval_executor,
    create_approval_request,
    create_approval_response,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_request():
    """Create a sample approval request."""
    return ApprovalRequest(
        action="deploy_to_production",
        risk_level=RiskLevel.HIGH,
        details="Deploy version 2.0.0 to production environment",
        context={"version": "2.0.0", "environment": "production"},
        requester="ci-pipeline",
        workflow_id="workflow-123",
        execution_id="exec-456",
    )


@pytest.fixture
def sample_response():
    """Create a sample approval response."""
    return ApprovalResponse(
        approved=True,
        reason="Risk acceptable after review",
        approver="admin@company.com",
        conditions=["Monitor logs for 24 hours"],
        notes="Approved after team discussion",
    )


@pytest.fixture
def escalation_policy():
    """Create a sample escalation policy."""
    return EscalationPolicy(
        timeout_minutes=30,
        escalate_to=["manager@company.com", "admin@company.com"],
        auto_reject=True,
        max_escalations=2,
    )


@pytest.fixture
def notification_config():
    """Create a sample notification config."""
    return NotificationConfig(
        enabled=True,
        channels=["email", "slack"],
        recipients=["approvers@company.com"],
        reminder_interval_minutes=30,
        max_reminders=2,
    )


@pytest.fixture
def approval_executor(escalation_policy, notification_config):
    """Create a sample approval executor."""
    return HumanApprovalExecutor(
        name="test-approval",
        escalation_policy=escalation_policy,
        notification_config=notification_config,
    )


# =============================================================================
# Test ApprovalRequest Model
# =============================================================================

class TestApprovalRequest:
    """Tests for ApprovalRequest Pydantic model."""

    def test_create_basic_request(self):
        """Test creating a basic approval request."""
        request = ApprovalRequest(
            action="test_action",
            details="Test details",
        )
        assert request.action == "test_action"
        assert request.details == "Test details"
        assert request.risk_level == RiskLevel.MEDIUM
        assert request.requester == "system"
        assert request.request_id is not None
        assert request.created_at is not None

    def test_create_full_request(self, sample_request):
        """Test creating a full approval request."""
        assert sample_request.action == "deploy_to_production"
        assert sample_request.risk_level == RiskLevel.HIGH
        assert sample_request.details == "Deploy version 2.0.0 to production environment"
        assert sample_request.context == {"version": "2.0.0", "environment": "production"}
        assert sample_request.requester == "ci-pipeline"
        assert sample_request.workflow_id == "workflow-123"
        assert sample_request.execution_id == "exec-456"

    def test_request_id_auto_generated(self):
        """Test that request_id is auto-generated."""
        request1 = ApprovalRequest(action="test", details="test")
        request2 = ApprovalRequest(action="test", details="test")
        assert request1.request_id != request2.request_id

    def test_risk_level_as_string(self):
        """Test risk level can be provided as string."""
        request = ApprovalRequest(
            action="test",
            details="test",
            risk_level="high",
        )
        assert request.risk_level == "high"

    def test_expires_at_default_none(self):
        """Test expires_at defaults to None."""
        request = ApprovalRequest(action="test", details="test")
        assert request.expires_at is None


# =============================================================================
# Test ApprovalResponse Model
# =============================================================================

class TestApprovalResponse:
    """Tests for ApprovalResponse Pydantic model."""

    def test_create_basic_response(self):
        """Test creating a basic approval response."""
        response = ApprovalResponse(
            approved=True,
            reason="Approved",
            approver="admin@company.com",
        )
        assert response.approved is True
        assert response.reason == "Approved"
        assert response.approver == "admin@company.com"
        assert response.conditions == []
        assert response.notes is None

    def test_create_rejection_response(self):
        """Test creating a rejection response."""
        response = ApprovalResponse(
            approved=False,
            reason="Too risky",
            approver="security@company.com",
            notes="Requires additional security review",
        )
        assert response.approved is False
        assert response.reason == "Too risky"
        assert response.notes == "Requires additional security review"

    def test_create_conditional_approval(self, sample_response):
        """Test creating a conditional approval."""
        assert sample_response.approved is True
        assert len(sample_response.conditions) == 1
        assert "Monitor logs" in sample_response.conditions[0]

    def test_response_id_auto_generated(self):
        """Test that response_id is auto-generated."""
        response1 = ApprovalResponse(approved=True, reason="ok", approver="a")
        response2 = ApprovalResponse(approved=True, reason="ok", approver="a")
        assert response1.response_id != response2.response_id


# =============================================================================
# Test EscalationPolicy
# =============================================================================

class TestEscalationPolicy:
    """Tests for EscalationPolicy dataclass."""

    def test_default_policy(self):
        """Test default escalation policy."""
        policy = EscalationPolicy()
        assert policy.timeout_minutes == 60
        assert policy.escalate_to == []
        assert policy.auto_approve is False
        assert policy.auto_reject is False
        assert policy.max_escalations == 2

    def test_custom_policy(self, escalation_policy):
        """Test custom escalation policy."""
        assert escalation_policy.timeout_minutes == 30
        assert len(escalation_policy.escalate_to) == 2
        assert escalation_policy.auto_reject is True
        assert escalation_policy.auto_approve is False

    def test_invalid_both_auto_actions(self):
        """Test that both auto_approve and auto_reject raises error."""
        with pytest.raises(ValueError, match="Cannot both auto_approve and auto_reject"):
            EscalationPolicy(auto_approve=True, auto_reject=True)

    def test_get_expiry_time(self, escalation_policy):
        """Test calculating expiry time."""
        now = datetime.utcnow()
        expiry = escalation_policy.get_expiry_time(now)
        expected = now + timedelta(minutes=30)
        # Allow 1 second tolerance
        assert abs((expiry - expected).total_seconds()) < 1

    def test_should_escalate_with_recipients(self, escalation_policy):
        """Test should_escalate with recipients configured."""
        assert escalation_policy.should_escalate(0) is True
        assert escalation_policy.should_escalate(1) is True
        assert escalation_policy.should_escalate(2) is False

    def test_should_escalate_without_recipients(self):
        """Test should_escalate without recipients."""
        policy = EscalationPolicy(escalate_to=[])
        assert policy.should_escalate(0) is False


# =============================================================================
# Test NotificationConfig
# =============================================================================

class TestNotificationConfig:
    """Tests for NotificationConfig."""

    def test_default_config(self):
        """Test default notification config."""
        config = NotificationConfig()
        assert config.enabled is True
        assert config.channels == ["email"]
        assert config.recipients == []
        assert config.reminder_interval_minutes == 60
        assert config.max_reminders == 3

    def test_custom_config(self, notification_config):
        """Test custom notification config."""
        assert notification_config.enabled is True
        assert notification_config.channels == ["email", "slack"]
        assert len(notification_config.recipients) == 1
        assert notification_config.reminder_interval_minutes == 30


# =============================================================================
# Test ApprovalState
# =============================================================================

class TestApprovalState:
    """Tests for ApprovalState dataclass."""

    def test_create_state(self, sample_request):
        """Test creating approval state."""
        state = ApprovalState(request=sample_request)
        assert state.status == ApprovalStatus.PENDING
        assert state.response is None
        assert state.escalation_level == 0
        assert state.reminders_sent == 0
        assert state.history == []

    def test_add_history_entry(self, sample_request):
        """Test adding history entry."""
        state = ApprovalState(request=sample_request)
        state.add_history_entry("created", {"reason": "test"})

        assert len(state.history) == 1
        assert state.history[0]["action"] == "created"
        assert state.history[0]["details"]["reason"] == "test"
        assert "timestamp" in state.history[0]


# =============================================================================
# Test HumanApprovalExecutor
# =============================================================================

class TestHumanApprovalExecutor:
    """Tests for HumanApprovalExecutor class."""

    def test_create_executor(self, approval_executor):
        """Test creating approval executor."""
        assert approval_executor.name == "test-approval"
        assert approval_executor.pending_count == 0
        assert approval_executor.escalation_policy.timeout_minutes == 30
        assert approval_executor.notification_config.enabled is True

    def test_create_executor_with_defaults(self):
        """Test creating executor with defaults."""
        executor = HumanApprovalExecutor()
        assert executor.name == "human-approval"
        assert executor.escalation_policy.timeout_minutes == 60
        assert executor.notification_config.enabled is True

    @pytest.mark.asyncio
    async def test_on_request_created(self, approval_executor, sample_request):
        """Test request creation callback."""
        context = MagicMock()

        await approval_executor.on_request_created(sample_request, context)

        assert approval_executor.pending_count == 1
        state = approval_executor.get_request_state(sample_request.request_id)
        assert state is not None
        assert state.status == ApprovalStatus.PENDING
        assert sample_request.expires_at is not None

    @pytest.mark.asyncio
    async def test_on_request_created_with_callback(self, sample_request):
        """Test request creation with custom callback."""
        callback = AsyncMock()
        executor = HumanApprovalExecutor(on_request_created=callback)
        context = MagicMock()

        await executor.on_request_created(sample_request, context)

        callback.assert_called_once_with(sample_request, context)

    @pytest.mark.asyncio
    async def test_on_response_received(
        self, approval_executor, sample_request, sample_response
    ):
        """Test response received callback."""
        context = MagicMock()

        # First create the request
        await approval_executor.on_request_created(sample_request, context)
        assert approval_executor.pending_count == 1

        # Then respond
        await approval_executor.on_response_received(
            sample_request, sample_response, context
        )

        assert approval_executor.pending_count == 0
        state = approval_executor.get_request_state(sample_request.request_id)
        assert state is not None
        assert state.status == ApprovalStatus.APPROVED
        assert state.response == sample_response

    @pytest.mark.asyncio
    async def test_on_response_rejection(self, approval_executor, sample_request):
        """Test rejection response."""
        context = MagicMock()
        rejection = ApprovalResponse(
            approved=False,
            reason="Denied",
            approver="admin@company.com",
        )

        await approval_executor.on_request_created(sample_request, context)
        await approval_executor.on_response_received(
            sample_request, rejection, context
        )

        state = approval_executor.get_request_state(sample_request.request_id)
        assert state.status == ApprovalStatus.REJECTED

    @pytest.mark.asyncio
    async def test_on_response_with_callback(self, sample_request, sample_response):
        """Test response received with custom callback."""
        callback = AsyncMock()
        executor = HumanApprovalExecutor(on_response_received=callback)
        context = MagicMock()

        await executor.on_request_created(sample_request, context)
        await executor.on_response_received(sample_request, sample_response, context)

        callback.assert_called_once_with(sample_request, sample_response, context)

    @pytest.mark.asyncio
    async def test_check_timeout_not_expired(
        self, approval_executor, sample_request
    ):
        """Test timeout check when not expired."""
        context = MagicMock()
        await approval_executor.on_request_created(sample_request, context)

        # Request was just created, shouldn't be expired
        result = await approval_executor.check_timeout(sample_request.request_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_check_timeout_auto_reject(self, sample_request):
        """Test timeout with auto-reject."""
        policy = EscalationPolicy(
            timeout_minutes=0,  # Immediate timeout
            auto_reject=True,
        )
        executor = HumanApprovalExecutor(escalation_policy=policy)
        context = MagicMock()

        await executor.on_request_created(sample_request, context)

        # Force expiry
        state = executor._pending_requests[sample_request.request_id]
        state.request.expires_at = datetime.utcnow() - timedelta(minutes=1)

        result = await executor.check_timeout(sample_request.request_id)

        assert result is not None
        assert result.approved is False
        assert "Auto-rejected" in result.reason

    @pytest.mark.asyncio
    async def test_check_timeout_auto_approve(self, sample_request):
        """Test timeout with auto-approve."""
        policy = EscalationPolicy(
            timeout_minutes=0,
            auto_approve=True,
        )
        executor = HumanApprovalExecutor(escalation_policy=policy)
        context = MagicMock()

        await executor.on_request_created(sample_request, context)

        # Force expiry
        state = executor._pending_requests[sample_request.request_id]
        state.request.expires_at = datetime.utcnow() - timedelta(minutes=1)

        result = await executor.check_timeout(sample_request.request_id)

        assert result is not None
        assert result.approved is True
        assert "Auto-approved" in result.reason

    @pytest.mark.asyncio
    async def test_check_timeout_escalation(self, sample_request):
        """Test timeout triggers escalation."""
        policy = EscalationPolicy(
            timeout_minutes=0,
            escalate_to=["manager@company.com"],
        )
        executor = HumanApprovalExecutor(escalation_policy=policy)
        context = MagicMock()

        await executor.on_request_created(sample_request, context)

        # Force expiry
        state = executor._pending_requests[sample_request.request_id]
        state.request.expires_at = datetime.utcnow() - timedelta(minutes=1)

        result = await executor.check_timeout(sample_request.request_id)

        # Should escalate, not auto-respond
        assert result is None
        state = executor._pending_requests[sample_request.request_id]
        assert state.status == ApprovalStatus.ESCALATED
        assert state.escalation_level == 1

    @pytest.mark.asyncio
    async def test_cancel_request(self, approval_executor, sample_request):
        """Test cancelling a request."""
        context = MagicMock()
        await approval_executor.on_request_created(sample_request, context)

        result = approval_executor.cancel_request(
            sample_request.request_id, "Test cancellation"
        )

        assert result is True
        assert approval_executor.pending_count == 0
        state = approval_executor.get_request_state(sample_request.request_id)
        assert state.status == ApprovalStatus.CANCELLED

    def test_cancel_nonexistent_request(self, approval_executor):
        """Test cancelling a nonexistent request."""
        result = approval_executor.cancel_request("nonexistent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_pending_requests(self, approval_executor):
        """Test getting pending requests."""
        context = MagicMock()

        request1 = ApprovalRequest(action="action1", details="details1")
        request2 = ApprovalRequest(action="action2", details="details2")

        await approval_executor.on_request_created(request1, context)
        await approval_executor.on_request_created(request2, context)

        pending = approval_executor.get_pending_requests()
        assert len(pending) == 2

    @pytest.mark.asyncio
    async def test_get_completed_requests(
        self, approval_executor, sample_request, sample_response
    ):
        """Test getting completed requests."""
        context = MagicMock()

        await approval_executor.on_request_created(sample_request, context)
        await approval_executor.on_response_received(
            sample_request, sample_response, context
        )

        completed = approval_executor.get_completed_requests()
        assert len(completed) == 1
        assert completed[0].status == ApprovalStatus.APPROVED

    def test_executor_repr(self, approval_executor):
        """Test executor string representation."""
        repr_str = repr(approval_executor)
        assert "HumanApprovalExecutor" in repr_str
        assert "test-approval" in repr_str


# =============================================================================
# Test Factory Functions
# =============================================================================

class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_approval_executor(self):
        """Test create_approval_executor factory."""
        executor = create_approval_executor(
            name="factory-executor",
            timeout_minutes=45,
            escalate_to=["admin@test.com"],
            auto_reject=True,
            notification_enabled=True,
            notification_channels=["email", "webhook"],
        )

        assert executor.name == "factory-executor"
        assert executor.escalation_policy.timeout_minutes == 45
        assert executor.escalation_policy.auto_reject is True
        assert executor.notification_config.enabled is True
        assert "webhook" in executor.notification_config.channels

    def test_create_approval_request(self):
        """Test create_approval_request factory."""
        request = create_approval_request(
            action="test_action",
            details="Test details",
            risk_level=RiskLevel.HIGH,
            context={"key": "value"},
            requester="user@test.com",
            workflow_id="wf-123",
            execution_id="ex-456",
        )

        assert request.action == "test_action"
        assert request.risk_level == RiskLevel.HIGH
        assert request.context == {"key": "value"}
        assert request.workflow_id == "wf-123"

    def test_create_approval_response(self):
        """Test create_approval_response factory."""
        response = create_approval_response(
            approved=True,
            reason="Looks good",
            approver="reviewer@test.com",
            conditions=["Condition 1", "Condition 2"],
            notes="Additional note",
        )

        assert response.approved is True
        assert response.reason == "Looks good"
        assert len(response.conditions) == 2
        assert response.notes == "Additional note"


# =============================================================================
# Test Integration Scenarios
# =============================================================================

class TestIntegrationScenarios:
    """Integration tests for complete approval workflows."""

    @pytest.mark.asyncio
    async def test_full_approval_flow(self):
        """Test complete approval flow from request to response."""
        # Setup
        request_callback = AsyncMock()
        response_callback = AsyncMock()

        executor = HumanApprovalExecutor(
            name="integration-test",
            on_request_created=request_callback,
            on_response_received=response_callback,
        )

        request = ApprovalRequest(
            action="deploy",
            details="Deploy to staging",
            risk_level=RiskLevel.LOW,
        )
        response = ApprovalResponse(
            approved=True,
            reason="Approved",
            approver="tester@test.com",
        )
        context = MagicMock()

        # Execute
        await executor.on_request_created(request, context)
        assert executor.pending_count == 1
        request_callback.assert_called_once()

        await executor.on_response_received(request, response, context)
        assert executor.pending_count == 0
        response_callback.assert_called_once()

        # Verify final state
        state = executor.get_request_state(request.request_id)
        assert state.status == ApprovalStatus.APPROVED
        assert len(state.history) >= 2

    @pytest.mark.asyncio
    async def test_multi_level_escalation(self):
        """Test multi-level escalation flow."""
        policy = EscalationPolicy(
            timeout_minutes=0,
            escalate_to=["level1@test.com", "level2@test.com"],
            max_escalations=2,
            auto_reject=True,
        )
        escalation_callback = AsyncMock()

        executor = HumanApprovalExecutor(
            escalation_policy=policy,
            on_escalation=escalation_callback,
        )

        request = ApprovalRequest(action="test", details="test")
        context = MagicMock()

        await executor.on_request_created(request, context)

        # Force expiry and check - should escalate to level 1
        state = executor._pending_requests[request.request_id]
        state.request.expires_at = datetime.utcnow() - timedelta(minutes=1)

        await executor.check_timeout(request.request_id)
        assert state.escalation_level == 1
        assert state.status == ApprovalStatus.ESCALATED

        # Force expiry again - should escalate to level 2
        state.request.expires_at = datetime.utcnow() - timedelta(minutes=1)
        await executor.check_timeout(request.request_id)
        assert state.escalation_level == 2

        # Force expiry again - should auto-reject (max escalations reached)
        state.request.expires_at = datetime.utcnow() - timedelta(minutes=1)
        result = await executor.check_timeout(request.request_id)

        assert result is not None
        assert result.approved is False
        assert executor.pending_count == 0
