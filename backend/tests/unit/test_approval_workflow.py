# =============================================================================
# IPA Platform - Approval Workflow Integration Tests
# =============================================================================
# Phase 5: MVP Core Official API Migration
# Sprint 28, Story S28-5: Unit Tests (3 pts)
#
# Test coverage for:
#   - WorkflowApprovalAdapter
#   - ApprovalWorkflowManager
#   - ApprovalWorkflowState
#   - Factory functions
# =============================================================================

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.agent_framework.core.approval import (
    HumanApprovalExecutor,
    ApprovalRequest,
    ApprovalResponse,
    ApprovalStatus,
    RiskLevel,
    EscalationPolicy,
    create_approval_executor,
)

from src.integrations.agent_framework.core.approval_workflow import (
    WorkflowApprovalAdapter,
    ApprovalWorkflowManager,
    ApprovalWorkflowState,
    create_workflow_approval_adapter,
    create_approval_workflow_manager,
    quick_respond,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def approval_executor():
    """Create a test approval executor."""
    return create_approval_executor(
        name="test-approval",
        timeout_minutes=30,
    )


@pytest.fixture
def sample_request():
    """Create a sample approval request."""
    return ApprovalRequest(
        action="deploy_to_production",
        risk_level=RiskLevel.HIGH,
        details="Deploy version 2.0.0 to production",
        context={"version": "2.0.0"},
    )


@pytest.fixture
def sample_response():
    """Create a sample approval response."""
    return ApprovalResponse(
        approved=True,
        reason="Approved after review",
        approver="admin@company.com",
    )


@pytest.fixture
def workflow_adapter(approval_executor):
    """Create a workflow approval adapter with executor."""
    adapter = WorkflowApprovalAdapter()
    adapter.register_executor("test-approval", approval_executor)
    return adapter


@pytest.fixture
def workflow_manager():
    """Create an approval workflow manager."""
    return ApprovalWorkflowManager()


# =============================================================================
# Test ApprovalWorkflowState
# =============================================================================

class TestApprovalWorkflowState:
    """Tests for ApprovalWorkflowState dataclass."""

    def test_create_state(self):
        """Test creating workflow state."""
        state = ApprovalWorkflowState(workflow_id="wf-123")
        assert state.workflow_id == "wf-123"
        assert state.status == "pending"
        assert state.pending_approvals == {}
        assert state.completed_approvals == {}

    def test_has_pending_approval(self, sample_request):
        """Test checking for pending approval."""
        from src.integrations.agent_framework.core.approval import ApprovalState

        state = ApprovalWorkflowState(workflow_id="wf-123")
        assert state.has_pending_approval("test") is False

        # Add pending approval
        approval_state = ApprovalState(request=sample_request)
        state.pending_approvals["test"] = approval_state
        assert state.has_pending_approval("test") is True

    def test_get_pending_approval(self, sample_request):
        """Test getting pending approval."""
        from src.integrations.agent_framework.core.approval import ApprovalState

        state = ApprovalWorkflowState(workflow_id="wf-123")
        assert state.get_pending_approval("test") is None

        approval_state = ApprovalState(request=sample_request)
        state.pending_approvals["test"] = approval_state
        result = state.get_pending_approval("test")
        assert result is not None
        assert result.request.action == "deploy_to_production"

    def test_mark_approval_complete(self, sample_request, sample_response):
        """Test marking approval as complete."""
        from src.integrations.agent_framework.core.approval import ApprovalState

        state = ApprovalWorkflowState(workflow_id="wf-123")
        approval_state = ApprovalState(request=sample_request)
        state.pending_approvals["test"] = approval_state

        state.mark_approval_complete("test", sample_response)

        assert "test" not in state.pending_approvals
        assert "test" in state.completed_approvals
        assert state.completed_approvals["test"] == sample_response


# =============================================================================
# Test WorkflowApprovalAdapter
# =============================================================================

class TestWorkflowApprovalAdapter:
    """Tests for WorkflowApprovalAdapter class."""

    def test_create_adapter(self):
        """Test creating adapter."""
        adapter = WorkflowApprovalAdapter()
        assert adapter._executors == {}
        assert adapter._workflow_states == {}

    def test_register_executor(self, approval_executor):
        """Test registering executor."""
        adapter = WorkflowApprovalAdapter()
        adapter.register_executor("test", approval_executor)
        assert "test" in adapter._executors
        assert adapter.get_executor("test") == approval_executor

    def test_unregister_executor(self, approval_executor):
        """Test unregistering executor."""
        adapter = WorkflowApprovalAdapter()
        adapter.register_executor("test", approval_executor)

        result = adapter.unregister_executor("test")
        assert result is True
        assert "test" not in adapter._executors

        # Try unregistering non-existent
        result = adapter.unregister_executor("nonexistent")
        assert result is False

    def test_get_executor(self, workflow_adapter, approval_executor):
        """Test getting executor."""
        assert workflow_adapter.get_executor("test-approval") == approval_executor
        assert workflow_adapter.get_executor("nonexistent") is None

    def test_register_response_handler(self, workflow_adapter):
        """Test registering response handler."""
        handler = AsyncMock()
        workflow_adapter.register_response_handler("test-approval", handler)
        assert "test-approval" in workflow_adapter._response_handlers

    @pytest.mark.asyncio
    async def test_respond_executor_not_found(self, workflow_adapter, sample_response):
        """Test respond with executor not found."""
        mock_workflow = MagicMock()

        with pytest.raises(ValueError, match="not registered"):
            await workflow_adapter.respond(
                workflow=mock_workflow,
                executor_name="nonexistent",
                response=sample_response,
            )

    @pytest.mark.asyncio
    async def test_respond_no_pending_request(
        self, workflow_adapter, sample_response
    ):
        """Test respond with no pending request."""
        mock_workflow = MagicMock()

        with pytest.raises(ValueError, match="No pending requests"):
            await workflow_adapter.respond(
                workflow=mock_workflow,
                executor_name="test-approval",
                response=sample_response,
            )

    @pytest.mark.asyncio
    async def test_respond_success(
        self, workflow_adapter, sample_request, sample_response
    ):
        """Test successful respond."""
        mock_workflow = MagicMock()
        executor = workflow_adapter.get_executor("test-approval")

        # Create pending request
        await executor.on_request_created(sample_request, None)
        assert executor.pending_count == 1

        # Respond
        result = await workflow_adapter.respond(
            workflow=mock_workflow,
            executor_name="test-approval",
            response=sample_response,
        )

        assert result is True
        assert executor.pending_count == 0

    @pytest.mark.asyncio
    async def test_respond_with_handler(
        self, workflow_adapter, sample_request, sample_response
    ):
        """Test respond triggers handler."""
        mock_workflow = MagicMock()
        handler = AsyncMock()
        workflow_adapter.register_response_handler("test-approval", handler)

        executor = workflow_adapter.get_executor("test-approval")
        await executor.on_request_created(sample_request, None)

        await workflow_adapter.respond(
            workflow=mock_workflow,
            executor_name="test-approval",
            response=sample_response,
        )

        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_respond_by_request_id(
        self, workflow_adapter, sample_request, sample_response
    ):
        """Test respond by request ID."""
        executor = workflow_adapter.get_executor("test-approval")
        await executor.on_request_created(sample_request, None)

        result = await workflow_adapter.respond_by_request_id(
            request_id=sample_request.request_id,
            response=sample_response,
        )

        assert result is True
        assert executor.pending_count == 0

    @pytest.mark.asyncio
    async def test_respond_by_request_id_not_found(
        self, workflow_adapter, sample_response
    ):
        """Test respond by request ID not found."""
        with pytest.raises(ValueError, match="not found"):
            await workflow_adapter.respond_by_request_id(
                request_id="nonexistent-id",
                response=sample_response,
            )

    @pytest.mark.asyncio
    async def test_get_all_pending_requests(
        self, workflow_adapter, sample_request
    ):
        """Test getting all pending requests."""
        executor = workflow_adapter.get_executor("test-approval")
        await executor.on_request_created(sample_request, None)

        pending = workflow_adapter.get_all_pending_requests()

        assert len(pending) == 1
        assert pending[0]["executor_name"] == "test-approval"
        assert pending[0]["action"] == "deploy_to_production"
        assert pending[0]["status"] == "pending"


# =============================================================================
# Test ApprovalWorkflowManager
# =============================================================================

class TestApprovalWorkflowManager:
    """Tests for ApprovalWorkflowManager class."""

    def test_create_manager(self):
        """Test creating manager."""
        manager = ApprovalWorkflowManager()
        assert manager.adapter is not None

    def test_register_approval_executor(self, workflow_manager):
        """Test registering approval executor."""
        executor = workflow_manager.register_approval_executor("test")
        assert executor is not None
        assert executor.name == "test"
        assert workflow_manager.get_approval_executor("test") == executor

    def test_register_existing_executor(self, workflow_manager, approval_executor):
        """Test registering existing executor."""
        result = workflow_manager.register_approval_executor(
            "custom", executor=approval_executor
        )
        assert result == approval_executor

    def test_register_with_policy(self, workflow_manager):
        """Test registering with escalation policy."""
        policy = EscalationPolicy(timeout_minutes=45)
        executor = workflow_manager.register_approval_executor(
            "policy-test", escalation_policy=policy
        )
        assert executor is not None

    @pytest.mark.asyncio
    async def test_respond_to_approval(self, workflow_manager, sample_response):
        """Test responding to approval."""
        executor = workflow_manager.register_approval_executor("test")

        request = ApprovalRequest(action="test", details="test details")
        await executor.on_request_created(request, None)

        result = await workflow_manager.respond_to_approval(
            executor_name="test",
            response=sample_response,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_respond_by_request_id(self, workflow_manager, sample_response):
        """Test responding by request ID."""
        executor = workflow_manager.register_approval_executor("test")

        request = ApprovalRequest(action="test", details="test details")
        await executor.on_request_created(request, None)

        result = await workflow_manager.respond_by_request_id(
            request_id=request.request_id,
            response=sample_response,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_get_pending_approvals(self, workflow_manager):
        """Test getting pending approvals."""
        executor = workflow_manager.register_approval_executor("test1")
        executor2 = workflow_manager.register_approval_executor("test2")

        request1 = ApprovalRequest(action="action1", details="details1")
        request2 = ApprovalRequest(action="action2", details="details2")

        await executor.on_request_created(request1, None)
        await executor2.on_request_created(request2, None)

        # Get all pending
        all_pending = workflow_manager.get_pending_approvals()
        assert len(all_pending) == 2

        # Filter by executor
        filtered = workflow_manager.get_pending_approvals(executor_name="test1")
        assert len(filtered) == 1
        assert filtered[0]["action"] == "action1"

    def test_create_approval_request(self, workflow_manager):
        """Test creating approval request."""
        request = workflow_manager.create_approval_request(
            action="deploy",
            details="Deploy to production",
            risk_level=RiskLevel.HIGH,
            context={"env": "prod"},
        )

        assert request.action == "deploy"
        assert request.risk_level == RiskLevel.HIGH
        assert request.context == {"env": "prod"}

    def test_create_approval_response(self, workflow_manager):
        """Test creating approval response."""
        response = workflow_manager.create_approval_response(
            approved=True,
            reason="Looks good",
            approver="admin@test.com",
            conditions=["Monitor for 24h"],
        )

        assert response.approved is True
        assert response.reason == "Looks good"
        assert len(response.conditions) == 1


# =============================================================================
# Test Factory Functions
# =============================================================================

class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_workflow_approval_adapter(self):
        """Test create_workflow_approval_adapter factory."""
        adapter = create_workflow_approval_adapter()
        assert isinstance(adapter, WorkflowApprovalAdapter)

    def test_create_approval_workflow_manager(self):
        """Test create_approval_workflow_manager factory."""
        manager = create_approval_workflow_manager()
        assert isinstance(manager, ApprovalWorkflowManager)


# =============================================================================
# Test Quick Respond Helper
# =============================================================================

class TestQuickRespond:
    """Tests for quick_respond helper function."""

    @pytest.mark.asyncio
    async def test_quick_respond_approved(self):
        """Test quick_respond with approval."""
        manager = create_approval_workflow_manager()
        executor = manager.register_approval_executor("quick-test")

        request = ApprovalRequest(action="test", details="test")
        await executor.on_request_created(request, None)

        result = await quick_respond(
            manager=manager,
            executor_name="quick-test",
            approved=True,
            approver="tester@test.com",
            reason="Quick approval",
        )

        assert result is True
        assert executor.pending_count == 0

    @pytest.mark.asyncio
    async def test_quick_respond_rejected(self):
        """Test quick_respond with rejection."""
        manager = create_approval_workflow_manager()
        executor = manager.register_approval_executor("quick-test")

        request = ApprovalRequest(action="test", details="test")
        await executor.on_request_created(request, None)

        result = await quick_respond(
            manager=manager,
            executor_name="quick-test",
            approved=False,
            approver="tester@test.com",
        )

        assert result is True

        # Check the response was a rejection
        completed = executor.get_completed_requests()
        assert len(completed) == 1
        assert completed[0].status == ApprovalStatus.REJECTED


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegrationScenarios:
    """Integration tests for approval workflow scenarios."""

    @pytest.mark.asyncio
    async def test_full_approval_workflow(self):
        """Test complete approval workflow from request to response."""
        # Setup
        manager = create_approval_workflow_manager()
        executor = manager.register_approval_executor(
            "deploy-gate",
            escalation_policy=EscalationPolicy(timeout_minutes=60),
        )

        # Create approval request
        request = manager.create_approval_request(
            action="deploy",
            details="Deploy version 2.0 to production",
            risk_level=RiskLevel.HIGH,
            context={"version": "2.0", "environment": "production"},
        )

        # Submit request
        await executor.on_request_created(request, None)

        # Verify pending
        pending = manager.get_pending_approvals()
        assert len(pending) == 1
        assert pending[0]["action"] == "deploy"

        # Respond
        response = manager.create_approval_response(
            approved=True,
            reason="Approved by security team",
            approver="security@company.com",
            conditions=["Enable feature flags", "Monitor for 2 hours"],
        )

        result = await manager.respond_to_approval(
            executor_name="deploy-gate",
            response=response,
        )

        assert result is True

        # Verify completed
        pending_after = manager.get_pending_approvals()
        assert len(pending_after) == 0

        completed = executor.get_completed_requests()
        assert len(completed) == 1
        assert completed[0].status == ApprovalStatus.APPROVED

    @pytest.mark.asyncio
    async def test_multi_executor_workflow(self):
        """Test workflow with multiple approval executors."""
        manager = create_approval_workflow_manager()

        # Register multiple executors
        security_executor = manager.register_approval_executor("security-review")
        manager_executor = manager.register_approval_executor("manager-approval")

        # Create requests for each
        security_request = ApprovalRequest(
            action="security_review", details="Review for security concerns"
        )
        manager_request = ApprovalRequest(
            action="manager_approval", details="Manager sign-off required"
        )

        await security_executor.on_request_created(security_request, None)
        await manager_executor.on_request_created(manager_request, None)

        # Verify both pending
        pending = manager.get_pending_approvals()
        assert len(pending) == 2

        # Approve security
        await manager.respond_to_approval(
            "security-review",
            ApprovalResponse(
                approved=True, reason="No security issues", approver="sec@test.com"
            ),
        )

        pending = manager.get_pending_approvals()
        assert len(pending) == 1

        # Approve manager
        await manager.respond_to_approval(
            "manager-approval",
            ApprovalResponse(
                approved=True, reason="Budget approved", approver="mgr@test.com"
            ),
        )

        pending = manager.get_pending_approvals()
        assert len(pending) == 0
