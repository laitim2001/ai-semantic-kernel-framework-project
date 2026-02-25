"""
Unit Tests for ApprovalHandler and RedisApprovalStorage

Comprehensive tests covering approve/reject operations, input validation,
audit logging, request status, history retrieval, and Redis key generation.

Sprint 130: Phase 34 - ApprovalHandler Deep Testing
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from src.integrations.orchestration.hitl.approval_handler import (
    ApprovalHandler,
    ApprovalResult,
    RedisApprovalStorage,
)
from src.integrations.orchestration.hitl.controller import (
    ApprovalEvent,
    ApprovalRequest,
    ApprovalStatus,
    ApprovalType,
    InMemoryApprovalStorage,
)
from src.integrations.orchestration.intent_router.models import (
    ITIntentCategory,
    RiskLevel,
    RoutingDecision,
    WorkflowType,
)
from src.integrations.orchestration.risk_assessor.assessor import (
    RiskAssessment,
    RiskFactor,
)


# =============================================================================
# Helper Factories
# =============================================================================


def _make_routing_decision() -> RoutingDecision:
    """Create a standard routing decision for testing."""
    return RoutingDecision(
        intent_category=ITIntentCategory.INCIDENT,
        sub_intent="etl_failure",
        confidence=0.95,
        routing_layer="pattern",
        risk_level=RiskLevel.HIGH,
        workflow_type=WorkflowType.MAGENTIC,
    )


def _make_risk_assessment() -> RiskAssessment:
    """Create a standard risk assessment for testing."""
    return RiskAssessment(
        level=RiskLevel.HIGH,
        score=0.8,
        requires_approval=True,
        approval_type="single",
        factors=[
            RiskFactor(
                name="intent",
                description="High risk intent",
                weight=0.5,
                impact="increase",
            ),
        ],
        reasoning="High risk operation",
    )


def _make_pending_request(
    request_id: str = "test-123",
    approvers: list = None,
    expires_minutes: int = 30,
) -> ApprovalRequest:
    """Create a pending approval request for testing."""
    return ApprovalRequest(
        request_id=request_id,
        routing_decision=_make_routing_decision(),
        risk_assessment=_make_risk_assessment(),
        requester="user@example.com",
        expires_at=datetime.utcnow() + timedelta(minutes=expires_minutes),
        approvers=approvers or [],
    )


def _make_mock_redis() -> AsyncMock:
    """Create a mock Redis client with standard async methods."""
    redis = AsyncMock()
    redis.setex = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.sadd = AsyncMock()
    redis.srem = AsyncMock()
    redis.delete = AsyncMock()
    redis.smembers = AsyncMock(return_value=set())
    return redis


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def storage() -> InMemoryApprovalStorage:
    """Provide a fresh in-memory storage."""
    return InMemoryApprovalStorage()


@pytest.fixture
def audit_logger() -> MagicMock:
    """Provide a mock audit logger."""
    return MagicMock()


@pytest.fixture
def handler(storage, audit_logger) -> ApprovalHandler:
    """Provide an ApprovalHandler with in-memory storage and mock audit logger."""
    return ApprovalHandler(storage=storage, audit_logger=audit_logger)


# =============================================================================
# Test ApprovalResult
# =============================================================================


class TestApprovalResult:
    """Tests for ApprovalResult dataclass."""

    def test_to_dict_success(self):
        """Verify to_dict for a successful result with request."""
        request = _make_pending_request()
        result = ApprovalResult(
            success=True,
            request=request,
            message="Approved",
            error=None,
        )

        data = result.to_dict()

        assert data["success"] is True
        assert data["message"] == "Approved"
        assert data["error"] is None
        assert data["request"] is not None
        assert data["request"]["request_id"] == "test-123"

    def test_to_dict_failure_without_request(self):
        """Verify to_dict for a failure result without request."""
        result = ApprovalResult(
            success=False,
            request=None,
            message="",
            error="Not found",
        )

        data = result.to_dict()

        assert data["success"] is False
        assert data["request"] is None
        assert data["error"] == "Not found"


# =============================================================================
# Test ApprovalHandler.approve
# =============================================================================


class TestApprovalHandlerApprove:
    """Tests for ApprovalHandler.approve method."""

    @pytest.mark.asyncio
    async def test_approve_success(self, handler, storage, audit_logger):
        """Verify successful approval sets status, fields, and calls audit."""
        request = _make_pending_request()
        await storage.save(request)

        result = await handler.approve(
            request_id="test-123",
            approver="admin@example.com",
            comment="Looks good",
        )

        assert result.success is True
        assert result.request.status == ApprovalStatus.APPROVED
        assert result.request.approved_by == "admin@example.com"
        assert result.request.approved_at is not None
        assert result.request.comment == "Looks good"
        assert "test-123" in result.message

        audit_logger.assert_called_once()
        call_args = audit_logger.call_args
        assert call_args[0][0] == "approval_approved"
        assert call_args[0][1]["request_id"] == "test-123"
        assert call_args[0][1]["approver"] == "admin@example.com"

    @pytest.mark.asyncio
    async def test_approve_not_found(self, handler):
        """Verify approve returns failure for nonexistent request."""
        result = await handler.approve(
            request_id="nonexistent",
            approver="admin@example.com",
        )

        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_approve_not_pending(self, handler, storage):
        """Verify approve returns failure for non-PENDING request."""
        request = _make_pending_request()
        request.status = ApprovalStatus.REJECTED
        await storage.save(request)

        result = await handler.approve(
            request_id="test-123",
            approver="admin@example.com",
        )

        assert result.success is False
        assert "not pending" in result.error

    @pytest.mark.asyncio
    async def test_approve_expired(self, handler, storage):
        """Verify approve returns failure for expired request."""
        request = _make_pending_request(expires_minutes=-5)
        await storage.save(request)

        result = await handler.approve(
            request_id="test-123",
            approver="admin@example.com",
        )

        assert result.success is False
        assert "expired" in result.error.lower()

        stored = await storage.get("test-123")
        assert stored.status == ApprovalStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_approve_unauthorized_approver(self, handler, storage):
        """Verify approve rejects unauthorized approver."""
        request = _make_pending_request(
            approvers=["approved-admin@example.com"],
        )
        await storage.save(request)

        result = await handler.approve(
            request_id="test-123",
            approver="random-user@example.com",
        )

        assert result.success is False
        assert "not authorized" in result.error


# =============================================================================
# Test ApprovalHandler.reject
# =============================================================================


class TestApprovalHandlerReject:
    """Tests for ApprovalHandler.reject method."""

    @pytest.mark.asyncio
    async def test_reject_success(self, handler, storage, audit_logger):
        """Verify successful rejection sets status, fields, and calls audit."""
        request = _make_pending_request()
        await storage.save(request)

        result = await handler.reject(
            request_id="test-123",
            rejector="admin@example.com",
            reason="Too risky",
        )

        assert result.success is True
        assert result.request.status == ApprovalStatus.REJECTED
        assert result.request.rejected_by == "admin@example.com"
        assert result.request.rejected_at is not None
        assert result.request.comment == "Too risky"

        audit_logger.assert_called_once()
        call_args = audit_logger.call_args
        assert call_args[0][0] == "approval_rejected"
        assert call_args[0][1]["rejector"] == "admin@example.com"

    @pytest.mark.asyncio
    async def test_reject_not_found(self, handler):
        """Verify reject returns failure for nonexistent request."""
        result = await handler.reject(
            request_id="nonexistent",
            rejector="admin@example.com",
        )

        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_reject_not_pending(self, handler, storage):
        """Verify reject returns failure for non-PENDING request."""
        request = _make_pending_request()
        request.status = ApprovalStatus.APPROVED
        await storage.save(request)

        result = await handler.reject(
            request_id="test-123",
            rejector="admin@example.com",
        )

        assert result.success is False
        assert "not pending" in result.error

    @pytest.mark.asyncio
    async def test_reject_expired(self, handler, storage):
        """Verify reject returns failure for expired request."""
        request = _make_pending_request(expires_minutes=-5)
        await storage.save(request)

        result = await handler.reject(
            request_id="test-123",
            rejector="admin@example.com",
        )

        assert result.success is False
        assert "expired" in result.error.lower()


# =============================================================================
# Test ApprovalHandler.get_request_status
# =============================================================================


class TestApprovalHandlerGetStatus:
    """Tests for ApprovalHandler.get_request_status method."""

    @pytest.mark.asyncio
    async def test_get_request_status_found(self, handler, storage):
        """Verify status retrieval for existing request."""
        request = _make_pending_request()
        await storage.save(request)

        result = await handler.get_request_status("test-123")

        assert result.success is True
        assert result.request.status == ApprovalStatus.PENDING
        assert "pending" in result.message

    @pytest.mark.asyncio
    async def test_get_request_status_not_found(self, handler):
        """Verify status retrieval returns failure for missing request."""
        result = await handler.get_request_status("missing-id")

        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_get_request_status_auto_expires(self, handler, storage):
        """Verify status check auto-expires stale PENDING request."""
        request = _make_pending_request(expires_minutes=-5)
        await storage.save(request)

        result = await handler.get_request_status("test-123")

        assert result.success is True
        assert result.request.status == ApprovalStatus.EXPIRED


# =============================================================================
# Test ApprovalHandler.get_history
# =============================================================================


class TestApprovalHandlerGetHistory:
    """Tests for ApprovalHandler.get_history method."""

    @pytest.mark.asyncio
    async def test_get_history_found(self, handler, storage):
        """Verify history retrieval for existing request."""
        request = _make_pending_request()
        await storage.save(request)

        history = await handler.get_history("test-123")

        assert len(history) >= 1
        assert history[0].event_type == "created"

    @pytest.mark.asyncio
    async def test_get_history_not_found(self, handler):
        """Verify history returns empty list for missing request."""
        history = await handler.get_history("missing-id")

        assert history == []


# =============================================================================
# Test ApprovalHandler.list_pending_by_approver
# =============================================================================


class TestApprovalHandlerListPending:
    """Tests for ApprovalHandler.list_pending_by_approver method."""

    @pytest.mark.asyncio
    async def test_list_pending_by_approver(self, handler, storage):
        """Verify filtering pending by approver identity."""
        req_a = _make_pending_request(
            request_id="a1",
            approvers=["admin-a@example.com"],
        )
        req_b = _make_pending_request(
            request_id="b1",
            approvers=["admin-b@example.com"],
        )
        req_open = _make_pending_request(
            request_id="open1",
            approvers=[],
        )
        await storage.save(req_a)
        await storage.save(req_b)
        await storage.save(req_open)

        result = await handler.list_pending_by_approver("admin-a@example.com")

        request_ids = [r.request_id for r in result]
        assert "a1" in request_ids
        assert "open1" in request_ids
        assert "b1" not in request_ids


# =============================================================================
# Test Input Validation
# =============================================================================


class TestApprovalHandlerInputValidation:
    """Tests for input validation in approve/reject."""

    @pytest.mark.asyncio
    async def test_approve_empty_request_id(self, handler):
        """Verify approve fails with empty request_id."""
        result = await handler.approve(
            request_id="",
            approver="admin@example.com",
        )

        assert result.success is False
        assert "required" in result.error

    @pytest.mark.asyncio
    async def test_approve_empty_approver(self, handler):
        """Verify approve fails with empty approver."""
        result = await handler.approve(
            request_id="test-123",
            approver="",
        )

        assert result.success is False
        assert "required" in result.error

    @pytest.mark.asyncio
    async def test_reject_empty_request_id(self, handler):
        """Verify reject fails with empty request_id."""
        result = await handler.reject(
            request_id="",
            rejector="admin@example.com",
        )

        assert result.success is False
        assert "required" in result.error

    @pytest.mark.asyncio
    async def test_reject_empty_rejector(self, handler):
        """Verify reject fails with empty rejector."""
        result = await handler.reject(
            request_id="test-123",
            rejector="",
        )

        assert result.success is False
        assert "required" in result.error


# =============================================================================
# Test RedisApprovalStorage Key Generation
# =============================================================================


class TestRedisApprovalStorageKeys:
    """Tests for RedisApprovalStorage key generation methods."""

    def test_request_key_default_prefix(self):
        """Verify _request_key with default prefix."""
        redis_mock = _make_mock_redis()
        store = RedisApprovalStorage(redis_client=redis_mock)

        assert store._request_key("abc-123") == "approval:abc-123"

    def test_request_key_custom_prefix(self):
        """Verify _request_key with custom prefix."""
        redis_mock = _make_mock_redis()
        store = RedisApprovalStorage(redis_client=redis_mock, key_prefix="hitl")

        assert store._request_key("abc-123") == "hitl:abc-123"

    def test_history_key(self):
        """Verify _history_key format."""
        redis_mock = _make_mock_redis()
        store = RedisApprovalStorage(redis_client=redis_mock)

        assert store._history_key("abc-123") == "approval_history:abc-123"

    def test_pending_set_key(self):
        """Verify _pending_set_key format."""
        redis_mock = _make_mock_redis()
        store = RedisApprovalStorage(redis_client=redis_mock)

        assert store._pending_set_key() == "approval_pending"

    def test_pending_set_key_custom_prefix(self):
        """Verify _pending_set_key with custom prefix."""
        redis_mock = _make_mock_redis()
        store = RedisApprovalStorage(redis_client=redis_mock, key_prefix="myapp")

        assert store._pending_set_key() == "myapp_pending"
