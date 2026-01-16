"""
Unit Tests for HITL Module

Tests for HITLController, ApprovalHandler, and NotificationService.

Sprint 97: Phase 28 - HITL Testing
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.orchestration.hitl import (
    ApprovalEvent,
    ApprovalHandler,
    ApprovalRequest,
    ApprovalResult,
    ApprovalStatus,
    ApprovalType,
    HITLController,
    InMemoryApprovalStorage,
    MockNotificationService,
    TeamsCardBuilder,
    TeamsMessageCard,
    TeamsNotificationService,
    create_hitl_controller,
    create_mock_hitl_controller,
)
from src.integrations.orchestration.intent_router.models import (
    CompletenessInfo,
    ITIntentCategory,
    RiskLevel,
    RoutingDecision,
)
from src.integrations.orchestration.risk_assessor.assessor import (
    RiskAssessment,
    RiskFactor,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_routing_decision() -> RoutingDecision:
    """Create a mock routing decision."""
    return RoutingDecision(
        intent_category=ITIntentCategory.INCIDENT,
        sub_intent="etl_failure",
        confidence=0.9,
        routing_layer="llm",
        completeness=CompletenessInfo(
            is_complete=True,
            completeness_score=0.8,
            missing_fields=[],
        ),
    )


@pytest.fixture
def mock_risk_assessment() -> RiskAssessment:
    """Create a mock risk assessment requiring approval."""
    return RiskAssessment(
        level=RiskLevel.HIGH,
        score=0.75,
        requires_approval=True,
        approval_type="single",
        factors=[
            RiskFactor(
                name="intent_category",
                description="Incident handling",
                weight=0.8,
                value="incident",
                impact="increase",
            ),
        ],
        reasoning="High risk due to incident category",
    )


@pytest.fixture
def mock_risk_assessment_no_approval() -> RiskAssessment:
    """Create a mock risk assessment not requiring approval."""
    return RiskAssessment(
        level=RiskLevel.LOW,
        score=0.25,
        requires_approval=False,
        approval_type="none",
        factors=[],
        reasoning="Low risk query",
    )


@pytest.fixture
def hitl_controller() -> tuple[HITLController, InMemoryApprovalStorage, MockNotificationService]:
    """Create HITL controller with mock dependencies."""
    return create_mock_hitl_controller()


# =============================================================================
# Test ApprovalStatus and ApprovalType Enums
# =============================================================================


class TestApprovalEnums:
    """Tests for ApprovalStatus and ApprovalType enums."""

    def test_approval_status_values(self):
        """Test ApprovalStatus enum values."""
        assert ApprovalStatus.PENDING.value == "pending"
        assert ApprovalStatus.APPROVED.value == "approved"
        assert ApprovalStatus.REJECTED.value == "rejected"
        assert ApprovalStatus.EXPIRED.value == "expired"
        assert ApprovalStatus.CANCELLED.value == "cancelled"

    def test_approval_type_values(self):
        """Test ApprovalType enum values."""
        assert ApprovalType.NONE.value == "none"
        assert ApprovalType.SINGLE.value == "single"
        assert ApprovalType.MULTI.value == "multi"


# =============================================================================
# Test ApprovalRequest
# =============================================================================


class TestApprovalRequest:
    """Tests for ApprovalRequest dataclass."""

    def test_creation(self, mock_routing_decision, mock_risk_assessment):
        """Test creating an ApprovalRequest."""
        request = ApprovalRequest(
            request_id="test-123",
            routing_decision=mock_routing_decision,
            risk_assessment=mock_risk_assessment,
            requester="user@example.com",
        )

        assert request.request_id == "test-123"
        assert request.status == ApprovalStatus.PENDING
        assert request.requester == "user@example.com"
        assert len(request.history) == 1  # Creation event
        assert request.history[0].event_type == "created"

    def test_is_expired_false(self, mock_routing_decision, mock_risk_assessment):
        """Test is_expired returns False for valid request."""
        request = ApprovalRequest(
            request_id="test-123",
            routing_decision=mock_routing_decision,
            risk_assessment=mock_risk_assessment,
            requester="user@example.com",
            expires_at=datetime.utcnow() + timedelta(minutes=30),
        )

        assert request.is_expired() is False

    def test_is_expired_true(self, mock_routing_decision, mock_risk_assessment):
        """Test is_expired returns True for expired request."""
        request = ApprovalRequest(
            request_id="test-123",
            routing_decision=mock_routing_decision,
            risk_assessment=mock_risk_assessment,
            requester="user@example.com",
            expires_at=datetime.utcnow() - timedelta(minutes=1),
        )

        assert request.is_expired() is True

    def test_is_terminal(self, mock_routing_decision, mock_risk_assessment):
        """Test is_terminal for different statuses."""
        request = ApprovalRequest(
            request_id="test-123",
            routing_decision=mock_routing_decision,
            risk_assessment=mock_risk_assessment,
            requester="user@example.com",
        )

        assert request.is_terminal() is False

        request.status = ApprovalStatus.APPROVED
        assert request.is_terminal() is True

        request.status = ApprovalStatus.REJECTED
        assert request.is_terminal() is True

    def test_to_dict(self, mock_routing_decision, mock_risk_assessment):
        """Test serialization to dictionary."""
        request = ApprovalRequest(
            request_id="test-123",
            routing_decision=mock_routing_decision,
            risk_assessment=mock_risk_assessment,
            requester="user@example.com",
        )

        data = request.to_dict()

        assert data["request_id"] == "test-123"
        assert data["requester"] == "user@example.com"
        assert data["status"] == "pending"
        assert "routing_decision" in data
        assert "risk_assessment" in data


# =============================================================================
# Test HITLController
# =============================================================================


class TestHITLController:
    """Tests for HITLController."""

    @pytest.mark.asyncio
    async def test_request_approval(
        self,
        hitl_controller,
        mock_routing_decision,
        mock_risk_assessment,
    ):
        """Test creating an approval request."""
        controller, storage, notification = hitl_controller

        request = await controller.request_approval(
            routing_decision=mock_routing_decision,
            risk_assessment=mock_risk_assessment,
            requester="user@example.com",
        )

        assert request.request_id is not None
        assert request.status == ApprovalStatus.PENDING
        assert request.requester == "user@example.com"

        # Verify storage
        stored = await storage.get(request.request_id)
        assert stored is not None
        assert stored.request_id == request.request_id

        # Verify notification sent
        assert len(notification.sent_requests) == 1

    @pytest.mark.asyncio
    async def test_request_approval_rejects_non_required(
        self,
        hitl_controller,
        mock_routing_decision,
        mock_risk_assessment_no_approval,
    ):
        """Test that approval is rejected when not required."""
        controller, _, _ = hitl_controller

        with pytest.raises(ValueError, match="does not require approval"):
            await controller.request_approval(
                routing_decision=mock_routing_decision,
                risk_assessment=mock_risk_assessment_no_approval,
                requester="user@example.com",
            )

    @pytest.mark.asyncio
    async def test_check_status(
        self,
        hitl_controller,
        mock_routing_decision,
        mock_risk_assessment,
    ):
        """Test checking approval status."""
        controller, _, _ = hitl_controller

        request = await controller.request_approval(
            routing_decision=mock_routing_decision,
            risk_assessment=mock_risk_assessment,
            requester="user@example.com",
        )

        status = await controller.check_status(request.request_id)
        assert status == ApprovalStatus.PENDING

    @pytest.mark.asyncio
    async def test_check_status_auto_expires(
        self,
        hitl_controller,
        mock_routing_decision,
        mock_risk_assessment,
    ):
        """Test that check_status auto-expires old requests."""
        controller, storage, _ = hitl_controller

        request = await controller.request_approval(
            routing_decision=mock_routing_decision,
            risk_assessment=mock_risk_assessment,
            requester="user@example.com",
            timeout_minutes=0,  # Immediate expiry
        )

        # Force expiry
        request.expires_at = datetime.utcnow() - timedelta(minutes=1)
        await storage.update(request)

        status = await controller.check_status(request.request_id)
        assert status == ApprovalStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_process_approval_approve(
        self,
        hitl_controller,
        mock_routing_decision,
        mock_risk_assessment,
    ):
        """Test approving a request."""
        controller, _, notification = hitl_controller

        request = await controller.request_approval(
            routing_decision=mock_routing_decision,
            risk_assessment=mock_risk_assessment,
            requester="user@example.com",
        )

        updated = await controller.process_approval(
            request_id=request.request_id,
            approved=True,
            approver="admin@example.com",
            comment="Approved for production",
        )

        assert updated.status == ApprovalStatus.APPROVED
        assert updated.approved_by == "admin@example.com"
        assert updated.comment == "Approved for production"

        # Verify result notification
        assert len(notification.sent_results) == 1
        assert notification.sent_results[0][1] is True  # approved=True

    @pytest.mark.asyncio
    async def test_process_approval_reject(
        self,
        hitl_controller,
        mock_routing_decision,
        mock_risk_assessment,
    ):
        """Test rejecting a request."""
        controller, _, _ = hitl_controller

        request = await controller.request_approval(
            routing_decision=mock_routing_decision,
            risk_assessment=mock_risk_assessment,
            requester="user@example.com",
        )

        updated = await controller.process_approval(
            request_id=request.request_id,
            approved=False,
            approver="admin@example.com",
            comment="Not appropriate at this time",
        )

        assert updated.status == ApprovalStatus.REJECTED
        assert updated.rejected_by == "admin@example.com"

    @pytest.mark.asyncio
    async def test_cancel_approval(
        self,
        hitl_controller,
        mock_routing_decision,
        mock_risk_assessment,
    ):
        """Test cancelling an approval request."""
        controller, _, _ = hitl_controller

        request = await controller.request_approval(
            routing_decision=mock_routing_decision,
            risk_assessment=mock_risk_assessment,
            requester="user@example.com",
        )

        updated = await controller.cancel_approval(
            request_id=request.request_id,
            canceller="user@example.com",
            reason="No longer needed",
        )

        assert updated.status == ApprovalStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_list_pending_requests(
        self,
        hitl_controller,
        mock_routing_decision,
        mock_risk_assessment,
    ):
        """Test listing pending requests."""
        controller, _, _ = hitl_controller

        # Create multiple requests
        await controller.request_approval(
            routing_decision=mock_routing_decision,
            risk_assessment=mock_risk_assessment,
            requester="user1@example.com",
        )
        await controller.request_approval(
            routing_decision=mock_routing_decision,
            risk_assessment=mock_risk_assessment,
            requester="user2@example.com",
        )

        pending = await controller.list_pending_requests()
        assert len(pending) == 2

    @pytest.mark.asyncio
    async def test_callbacks_on_approved(
        self,
        hitl_controller,
        mock_routing_decision,
        mock_risk_assessment,
    ):
        """Test that callbacks are triggered on approval."""
        controller, _, _ = hitl_controller

        callback_called = []

        def on_approved(request):
            callback_called.append(request.request_id)

        controller.on_approved(on_approved)

        request = await controller.request_approval(
            routing_decision=mock_routing_decision,
            risk_assessment=mock_risk_assessment,
            requester="user@example.com",
        )

        await controller.process_approval(
            request_id=request.request_id,
            approved=True,
            approver="admin@example.com",
        )

        assert request.request_id in callback_called


# =============================================================================
# Test ApprovalHandler
# =============================================================================


class TestApprovalHandler:
    """Tests for ApprovalHandler."""

    @pytest.fixture
    def handler(self):
        """Create ApprovalHandler with in-memory storage."""
        storage = InMemoryApprovalStorage()
        return ApprovalHandler(storage=storage), storage

    @pytest.mark.asyncio
    async def test_approve(
        self,
        handler,
        mock_routing_decision,
        mock_risk_assessment,
    ):
        """Test approve operation."""
        approval_handler, storage = handler

        # Create a pending request
        request = ApprovalRequest(
            request_id="test-123",
            routing_decision=mock_routing_decision,
            risk_assessment=mock_risk_assessment,
            requester="user@example.com",
            expires_at=datetime.utcnow() + timedelta(minutes=30),
        )
        await storage.save(request)

        result = await approval_handler.approve(
            request_id="test-123",
            approver="admin@example.com",
            comment="Approved",
        )

        assert result.success is True
        assert result.request.status == ApprovalStatus.APPROVED

    @pytest.mark.asyncio
    async def test_reject(
        self,
        handler,
        mock_routing_decision,
        mock_risk_assessment,
    ):
        """Test reject operation."""
        approval_handler, storage = handler

        request = ApprovalRequest(
            request_id="test-123",
            routing_decision=mock_routing_decision,
            risk_assessment=mock_risk_assessment,
            requester="user@example.com",
            expires_at=datetime.utcnow() + timedelta(minutes=30),
        )
        await storage.save(request)

        result = await approval_handler.reject(
            request_id="test-123",
            rejector="admin@example.com",
            reason="Not approved",
        )

        assert result.success is True
        assert result.request.status == ApprovalStatus.REJECTED

    @pytest.mark.asyncio
    async def test_approve_not_found(self, handler):
        """Test approve when request not found."""
        approval_handler, _ = handler

        result = await approval_handler.approve(
            request_id="nonexistent",
            approver="admin@example.com",
        )

        assert result.success is False
        assert "not found" in result.error


# =============================================================================
# Test TeamsCardBuilder
# =============================================================================


class TestTeamsCardBuilder:
    """Tests for TeamsCardBuilder."""

    def test_basic_card(self):
        """Test building a basic card."""
        card = (
            TeamsCardBuilder()
            .with_title("Test Title")
            .with_summary("Test Summary")
            .build()
        )

        assert card.title == "Test Title"
        assert card.summary == "Test Summary"

    def test_with_theme_color(self):
        """Test setting theme color."""
        card = (
            TeamsCardBuilder()
            .with_title("Test")
            .with_theme_color("FF0000")
            .build()
        )

        assert card.theme_color == "FF0000"

    def test_with_risk_level_color(self):
        """Test setting color based on risk level."""
        card = (
            TeamsCardBuilder()
            .with_title("Test")
            .with_risk_level_color(RiskLevel.HIGH)
            .build()
        )

        assert card.theme_color == "FF0000"  # Red for high risk

    def test_add_section_and_facts(self):
        """Test adding sections with facts."""
        card = (
            TeamsCardBuilder()
            .with_title("Test")
            .add_section("Details")
            .add_fact("Key1", "Value1")
            .add_fact("Key2", "Value2")
            .build()
        )

        assert len(card.sections) == 1
        assert len(card.sections[0]["facts"]) == 2

    def test_add_action_buttons(self):
        """Test adding action buttons."""
        card = (
            TeamsCardBuilder()
            .with_title("Test")
            .add_approve_button("https://api.example.com/approve")
            .add_reject_button("https://api.example.com/reject")
            .build()
        )

        assert len(card.potential_actions) == 2

    def test_to_dict(self):
        """Test serialization to MessageCard format."""
        card = (
            TeamsCardBuilder()
            .with_title("Test")
            .with_summary("Summary")
            .build()
        )

        data = card.to_dict()

        assert data["@type"] == "MessageCard"
        assert data["@context"] == "http://schema.org/extensions"
        assert data["title"] == "Test"
        assert data["summary"] == "Summary"


# =============================================================================
# Test InMemoryApprovalStorage
# =============================================================================


class TestInMemoryApprovalStorage:
    """Tests for InMemoryApprovalStorage."""

    @pytest.fixture
    def storage(self):
        """Create InMemoryApprovalStorage."""
        return InMemoryApprovalStorage()

    @pytest.mark.asyncio
    async def test_save_and_get(
        self,
        storage,
        mock_routing_decision,
        mock_risk_assessment,
    ):
        """Test saving and retrieving a request."""
        request = ApprovalRequest(
            request_id="test-123",
            routing_decision=mock_routing_decision,
            risk_assessment=mock_risk_assessment,
            requester="user@example.com",
        )

        await storage.save(request)
        retrieved = await storage.get("test-123")

        assert retrieved is not None
        assert retrieved.request_id == "test-123"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, storage):
        """Test getting a nonexistent request."""
        retrieved = await storage.get("nonexistent")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete(
        self,
        storage,
        mock_routing_decision,
        mock_risk_assessment,
    ):
        """Test deleting a request."""
        request = ApprovalRequest(
            request_id="test-123",
            routing_decision=mock_routing_decision,
            risk_assessment=mock_risk_assessment,
            requester="user@example.com",
        )

        await storage.save(request)
        await storage.delete("test-123")
        retrieved = await storage.get("test-123")

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_pending(
        self,
        storage,
        mock_routing_decision,
        mock_risk_assessment,
    ):
        """Test listing pending requests."""
        # Add pending request
        pending = ApprovalRequest(
            request_id="pending-1",
            routing_decision=mock_routing_decision,
            risk_assessment=mock_risk_assessment,
            requester="user@example.com",
        )
        await storage.save(pending)

        # Add approved request
        approved = ApprovalRequest(
            request_id="approved-1",
            routing_decision=mock_routing_decision,
            risk_assessment=mock_risk_assessment,
            requester="user@example.com",
            status=ApprovalStatus.APPROVED,
        )
        await storage.save(approved)

        pending_list = await storage.list_pending()

        assert len(pending_list) == 1
        assert pending_list[0].request_id == "pending-1"


# =============================================================================
# Test Factory Functions
# =============================================================================


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_hitl_controller(self):
        """Test create_hitl_controller factory."""
        controller = create_hitl_controller()
        assert isinstance(controller, HITLController)

    def test_create_mock_hitl_controller(self):
        """Test create_mock_hitl_controller factory."""
        controller, storage, notification = create_mock_hitl_controller()

        assert isinstance(controller, HITLController)
        assert isinstance(storage, InMemoryApprovalStorage)
        assert isinstance(notification, MockNotificationService)
