# =============================================================================
# IPA Platform - AG-UI Approval Routes Tests
# =============================================================================
# Sprint 59: AG-UI Basic Features
# S59-3: Human-in-the-Loop
#
# Unit tests for AG-UI approval API endpoints.
# Tests approval workflow: list pending, get, approve, reject, cancel, stats.
#
# Dependencies:
#   - pytest (testing framework)
#   - pytest-asyncio (async test support)
#   - FastAPI TestClient (API testing)
#   - unittest.mock (mocking)
# =============================================================================

from datetime import datetime, timedelta
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1.ag_ui.routes import router
from src.api.v1.ag_ui.schemas import (
    ApprovalStatusEnum,
    RiskLevelEnum,
)
from src.integrations.ag_ui.features.human_in_loop import (
    ApprovalRequest,
    ApprovalStatus,
    ApprovalStorage,
    HITLHandler,
    get_approval_storage,
    get_hitl_handler,
)
from src.integrations.hybrid.risk import RiskLevel


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_storage():
    """Create a mock ApprovalStorage."""
    storage = MagicMock(spec=ApprovalStorage)
    # Set up async methods
    storage.get_pending = AsyncMock(return_value=[])
    storage.get = AsyncMock(return_value=None)
    storage.cancel = AsyncMock(return_value=True)
    storage.get_stats = MagicMock(return_value={
        "total": 0,
        "pending": 0,
        "approved": 0,
        "rejected": 0,
        "timeout": 0,
        "cancelled": 0,
    })
    return storage


@pytest.fixture
def mock_hitl():
    """Create a mock HITLHandler."""
    handler = MagicMock(spec=HITLHandler)
    handler.handle_approval_response = AsyncMock(return_value=(True, None))
    return handler


@pytest.fixture
def app(mock_storage, mock_hitl):
    """Create FastAPI app with AG-UI router and mocked dependencies."""
    test_app = FastAPI()
    # Router already has prefix="/ag-ui", so we only add "/api/v1"
    test_app.include_router(router, prefix="/api/v1")

    # Override dependencies with mocks
    test_app.dependency_overrides[get_approval_storage] = lambda: mock_storage
    test_app.dependency_overrides[get_hitl_handler] = lambda: mock_hitl

    return test_app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_approval_request():
    """Create a sample ApprovalRequest object with proper enum types."""
    return ApprovalRequest(
        approval_id="approval-test-123",
        tool_call_id="tc-456",
        tool_name="Bash",
        arguments={"command": "ls -la"},
        risk_level=RiskLevel.HIGH,
        risk_score=0.75,
        reasoning="Shell command with potential risk",
        run_id="run-789",
        session_id="session-abc",
        status=ApprovalStatus.PENDING,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(seconds=300),
        resolved_at=None,
        user_comment=None,
    )


@pytest.fixture
def sample_approved_request(sample_approval_request):
    """Create a sample approved request."""
    return ApprovalRequest(
        approval_id=sample_approval_request.approval_id,
        tool_call_id=sample_approval_request.tool_call_id,
        tool_name=sample_approval_request.tool_name,
        arguments=sample_approval_request.arguments,
        risk_level=sample_approval_request.risk_level,
        risk_score=sample_approval_request.risk_score,
        reasoning=sample_approval_request.reasoning,
        run_id=sample_approval_request.run_id,
        session_id=sample_approval_request.session_id,
        status=ApprovalStatus.APPROVED,
        created_at=sample_approval_request.created_at,
        expires_at=sample_approval_request.expires_at,
        resolved_at=datetime.utcnow(),
        user_comment="Looks safe to execute",
    )


@pytest.fixture
def sample_rejected_request(sample_approval_request):
    """Create a sample rejected request."""
    return ApprovalRequest(
        approval_id=sample_approval_request.approval_id,
        tool_call_id=sample_approval_request.tool_call_id,
        tool_name=sample_approval_request.tool_name,
        arguments=sample_approval_request.arguments,
        risk_level=sample_approval_request.risk_level,
        risk_score=sample_approval_request.risk_score,
        reasoning=sample_approval_request.reasoning,
        run_id=sample_approval_request.run_id,
        session_id=sample_approval_request.session_id,
        status=ApprovalStatus.REJECTED,
        created_at=sample_approval_request.created_at,
        expires_at=sample_approval_request.expires_at,
        resolved_at=datetime.utcnow(),
        user_comment="Not safe",
    )


@pytest.fixture
def sample_cancelled_request(sample_approval_request):
    """Create a sample cancelled request."""
    return ApprovalRequest(
        approval_id=sample_approval_request.approval_id,
        tool_call_id=sample_approval_request.tool_call_id,
        tool_name=sample_approval_request.tool_name,
        arguments=sample_approval_request.arguments,
        risk_level=sample_approval_request.risk_level,
        risk_score=sample_approval_request.risk_score,
        reasoning=sample_approval_request.reasoning,
        run_id=sample_approval_request.run_id,
        session_id=sample_approval_request.session_id,
        status=ApprovalStatus.CANCELLED,
        created_at=sample_approval_request.created_at,
        expires_at=sample_approval_request.expires_at,
        resolved_at=datetime.utcnow(),
        user_comment=None,
    )


# =============================================================================
# Test: GET /approvals/pending
# =============================================================================


class TestListPendingApprovals:
    """Tests for GET /approvals/pending endpoint."""

    def test_list_pending_empty(self, client, mock_storage):
        """Test listing pending approvals when none exist."""
        mock_storage.get_pending = AsyncMock(return_value=[])

        response = client.get("/api/v1/ag-ui/approvals/pending")

        assert response.status_code == 200
        data = response.json()
        assert data["pending"] == []
        assert data["total"] == 0

    def test_list_pending_with_approvals(self, client, mock_storage, sample_approval_request):
        """Test listing pending approvals when some exist."""
        mock_storage.get_pending = AsyncMock(return_value=[sample_approval_request])

        response = client.get("/api/v1/ag-ui/approvals/pending")

        assert response.status_code == 200
        data = response.json()
        assert len(data["pending"]) == 1
        assert data["total"] == 1
        assert data["pending"][0]["approval_id"] == "approval-test-123"

    def test_list_pending_with_session_filter(self, client, mock_storage, sample_approval_request):
        """Test listing pending approvals filtered by session ID."""
        mock_storage.get_pending = AsyncMock(return_value=[sample_approval_request])

        response = client.get(
            "/api/v1/ag-ui/approvals/pending?session_id=session-abc"
        )

        assert response.status_code == 200
        mock_storage.get_pending.assert_called_once_with(
            session_id="session-abc", run_id=None
        )

    def test_list_pending_with_run_filter(self, client, mock_storage, sample_approval_request):
        """Test listing pending approvals filtered by run ID."""
        mock_storage.get_pending = AsyncMock(return_value=[sample_approval_request])

        response = client.get(
            "/api/v1/ag-ui/approvals/pending?run_id=run-789"
        )

        assert response.status_code == 200
        mock_storage.get_pending.assert_called_once_with(
            session_id=None, run_id="run-789"
        )

    def test_list_pending_with_both_filters(self, client, mock_storage, sample_approval_request):
        """Test listing pending approvals filtered by session and run ID."""
        mock_storage.get_pending = AsyncMock(return_value=[sample_approval_request])

        response = client.get(
            "/api/v1/ag-ui/approvals/pending?session_id=session-abc&run_id=run-789"
        )

        assert response.status_code == 200
        mock_storage.get_pending.assert_called_once_with(
            session_id="session-abc", run_id="run-789"
        )


# =============================================================================
# Test: GET /approvals/{approval_id}
# =============================================================================


class TestGetApproval:
    """Tests for GET /approvals/{approval_id} endpoint."""

    def test_get_approval_success(self, client, mock_storage, sample_approval_request):
        """Test getting an existing approval request."""
        mock_storage.get = AsyncMock(return_value=sample_approval_request)

        response = client.get("/api/v1/ag-ui/approvals/approval-test-123")

        assert response.status_code == 200
        data = response.json()
        assert data["approval_id"] == "approval-test-123"
        assert data["tool_name"] == "Bash"
        assert data["status"] == "pending"

    def test_get_approval_not_found(self, client, mock_storage):
        """Test getting a non-existent approval request."""
        mock_storage.get = AsyncMock(return_value=None)

        response = client.get("/api/v1/ag-ui/approvals/non-existent-id")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]["message"].lower()


# =============================================================================
# Test: POST /approvals/{approval_id}/approve
# =============================================================================


class TestApproveToolCall:
    """Tests for POST /approvals/{approval_id}/approve endpoint."""

    def test_approve_success(self, client, mock_hitl, sample_approved_request):
        """Test approving a pending tool call."""
        mock_hitl.handle_approval_response = AsyncMock(
            return_value=(True, sample_approved_request)
        )

        response = client.post(
            "/api/v1/ag-ui/approvals/approval-test-123/approve",
            json={"comment": "Approved by admin"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "approved"
        assert "approved successfully" in data["message"].lower()

    def test_approve_without_comment(self, client, mock_hitl, sample_approved_request):
        """Test approving without a comment."""
        mock_hitl.handle_approval_response = AsyncMock(
            return_value=(True, sample_approved_request)
        )

        response = client.post(
            "/api/v1/ag-ui/approvals/approval-test-123/approve",
            json={}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_approve_not_found(self, client, mock_hitl):
        """Test approving a non-existent request."""
        mock_hitl.handle_approval_response = AsyncMock(
            return_value=(False, None)
        )

        response = client.post(
            "/api/v1/ag-ui/approvals/non-existent-id/approve",
            json={}
        )

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]["message"].lower()

    def test_approve_already_resolved(self, client, mock_hitl, sample_approved_request):
        """Test approving an already resolved request."""
        # Return False (failure) with the already-resolved request
        mock_hitl.handle_approval_response = AsyncMock(
            return_value=(False, sample_approved_request)
        )

        response = client.post(
            "/api/v1/ag-ui/approvals/approval-test-123/approve",
            json={}
        )

        assert response.status_code == 400
        data = response.json()
        assert "already resolved" in data["detail"]["message"].lower() or "expired" in data["detail"]["message"].lower()


# =============================================================================
# Test: POST /approvals/{approval_id}/reject
# =============================================================================


class TestRejectToolCall:
    """Tests for POST /approvals/{approval_id}/reject endpoint."""

    def test_reject_success(self, client, mock_hitl, sample_rejected_request):
        """Test rejecting a pending tool call."""
        mock_hitl.handle_approval_response = AsyncMock(
            return_value=(True, sample_rejected_request)
        )

        response = client.post(
            "/api/v1/ag-ui/approvals/approval-test-123/reject",
            json={"comment": "Too risky"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "rejected"
        assert "rejected" in data["message"].lower()

    def test_reject_without_comment(self, client, mock_hitl, sample_rejected_request):
        """Test rejecting without a comment."""
        mock_hitl.handle_approval_response = AsyncMock(
            return_value=(True, sample_rejected_request)
        )

        response = client.post(
            "/api/v1/ag-ui/approvals/approval-test-123/reject",
            json={}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_reject_not_found(self, client, mock_hitl):
        """Test rejecting a non-existent request."""
        mock_hitl.handle_approval_response = AsyncMock(
            return_value=(False, None)
        )

        response = client.post(
            "/api/v1/ag-ui/approvals/non-existent-id/reject",
            json={}
        )

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]["message"].lower()

    def test_reject_already_resolved(self, client, mock_hitl, sample_rejected_request):
        """Test rejecting an already resolved request."""
        mock_hitl.handle_approval_response = AsyncMock(
            return_value=(False, sample_rejected_request)
        )

        response = client.post(
            "/api/v1/ag-ui/approvals/approval-test-123/reject",
            json={}
        )

        assert response.status_code == 400
        data = response.json()
        assert "already resolved" in data["detail"]["message"].lower() or "expired" in data["detail"]["message"].lower()


# =============================================================================
# Test: POST /approvals/{approval_id}/cancel
# =============================================================================


class TestCancelApproval:
    """Tests for POST /approvals/{approval_id}/cancel endpoint."""

    def test_cancel_success(self, client, mock_storage, sample_cancelled_request):
        """Test cancelling a pending approval request."""
        mock_storage.cancel = AsyncMock(return_value=True)
        mock_storage.get = AsyncMock(return_value=sample_cancelled_request)

        response = client.post(
            "/api/v1/ag-ui/approvals/approval-test-123/cancel"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "cancelled"

    def test_cancel_not_found(self, client, mock_storage):
        """Test cancelling a non-existent request."""
        mock_storage.cancel = AsyncMock(return_value=False)
        mock_storage.get = AsyncMock(return_value=None)

        response = client.post(
            "/api/v1/ag-ui/approvals/non-existent-id/cancel"
        )

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]["message"].lower()

    def test_cancel_already_resolved(self, client, mock_storage, sample_approved_request):
        """Test cancelling an already resolved request."""
        mock_storage.cancel = AsyncMock(return_value=False)
        mock_storage.get = AsyncMock(return_value=sample_approved_request)

        response = client.post(
            "/api/v1/ag-ui/approvals/approval-test-123/cancel"
        )

        assert response.status_code == 400
        data = response.json()
        assert "already resolved" in data["detail"]["message"].lower()


# =============================================================================
# Test: GET /approvals/stats
# =============================================================================


class TestGetApprovalStats:
    """Tests for GET /approvals/stats endpoint."""

    def test_get_stats_empty(self, client, mock_storage):
        """Test getting stats when no approvals exist."""
        mock_storage.get_stats = MagicMock(return_value={
            "total": 0,
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "timeout": 0,
            "cancelled": 0,
        })

        response = client.get("/api/v1/ag-ui/approvals/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["pending"] == 0
        assert data["approved"] == 0
        assert data["rejected"] == 0
        assert data["timeout"] == 0
        assert data["cancelled"] == 0

    def test_get_stats_with_data(self, client, mock_storage):
        """Test getting stats when approvals exist."""
        mock_storage.get_stats = MagicMock(return_value={
            "total": 10,
            "pending": 2,
            "approved": 5,
            "rejected": 2,
            "timeout": 1,
            "cancelled": 0,
        })

        response = client.get("/api/v1/ag-ui/approvals/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert data["pending"] == 2
        assert data["approved"] == 5
        assert data["rejected"] == 2
        assert data["timeout"] == 1
        assert data["cancelled"] == 0


# =============================================================================
# Test: Response Schema Validation
# =============================================================================


class TestResponseSchemas:
    """Tests for verifying response schema compliance."""

    def test_pending_approvals_response_schema(self, client, mock_storage, sample_approval_request):
        """Test that pending approvals response matches expected schema."""
        mock_storage.get_pending = AsyncMock(return_value=[sample_approval_request])

        response = client.get("/api/v1/ag-ui/approvals/pending")

        assert response.status_code == 200
        data = response.json()

        # Verify top-level schema
        assert "pending" in data
        assert "total" in data
        assert isinstance(data["pending"], list)
        assert isinstance(data["total"], int)

        # Verify approval item schema
        if len(data["pending"]) > 0:
            approval = data["pending"][0]
            assert "approval_id" in approval
            assert "tool_call_id" in approval
            assert "tool_name" in approval
            assert "risk_level" in approval
            assert "risk_score" in approval
            assert "status" in approval
            assert "created_at" in approval
            assert "expires_at" in approval

    def test_approval_action_response_schema(self, client, mock_hitl, sample_approved_request):
        """Test that approval action response matches expected schema."""
        mock_hitl.handle_approval_response = AsyncMock(
            return_value=(True, sample_approved_request)
        )

        response = client.post(
            "/api/v1/ag-ui/approvals/approval-test-123/approve",
            json={}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify schema fields
        assert "success" in data
        assert "approval_id" in data
        assert "status" in data
        assert "message" in data
        assert isinstance(data["success"], bool)
        assert isinstance(data["status"], str)
        assert isinstance(data["message"], str)

    def test_stats_response_schema(self, client, mock_storage):
        """Test that stats response matches expected schema."""
        mock_storage.get_stats = MagicMock(return_value={
            "total": 5,
            "pending": 1,
            "approved": 2,
            "rejected": 1,
            "timeout": 1,
            "cancelled": 0,
        })

        response = client.get("/api/v1/ag-ui/approvals/stats")

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields
        required_fields = ["total", "pending", "approved", "rejected", "timeout", "cancelled"]
        for field in required_fields:
            assert field in data
            assert isinstance(data[field], int)


# =============================================================================
# Test: Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_invalid_approval_id_format(self, client, mock_storage):
        """Test handling of malformed approval IDs."""
        mock_storage.get = AsyncMock(return_value=None)

        # Test with empty string - should return 404
        response = client.get("/api/v1/ag-ui/approvals/")

        # Empty path would either be 404 or redirect to list
        # Actual behavior depends on routing
        assert response.status_code in [307, 404, 405]

    def test_concurrent_approval_attempts(self, client, mock_hitl, sample_approved_request):
        """Test behavior when approval is already processed."""
        # Second attempt fails
        mock_hitl.handle_approval_response = AsyncMock(
            return_value=(False, sample_approved_request)
        )

        response = client.post(
            "/api/v1/ag-ui/approvals/approval-test-123/approve",
            json={}
        )

        # Should return bad request (already resolved)
        assert response.status_code == 400

    def test_long_comment_in_approval(self, client, mock_hitl, sample_approved_request):
        """Test handling of long comments in approval action."""
        mock_hitl.handle_approval_response = AsyncMock(
            return_value=(True, sample_approved_request)
        )

        long_comment = "A" * 500  # Max length comment
        response = client.post(
            "/api/v1/ag-ui/approvals/approval-test-123/approve",
            json={"comment": long_comment}
        )

        # Should accept max length comment
        assert response.status_code == 200

    def test_empty_pending_list_with_filters(self, client, mock_storage):
        """Test empty pending list when filters match nothing."""
        mock_storage.get_pending = AsyncMock(return_value=[])

        response = client.get(
            "/api/v1/ag-ui/approvals/pending?session_id=nonexistent"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pending"] == []
        assert data["total"] == 0


# =============================================================================
# Test: Status Value Mapping
# =============================================================================


class TestStatusValueMapping:
    """Tests for status value mapping in responses."""

    def test_pending_status_lowercase_in_response(self, client, mock_storage, sample_approval_request):
        """Test that status values are lowercase in API responses."""
        mock_storage.get = AsyncMock(return_value=sample_approval_request)

        response = client.get("/api/v1/ag-ui/approvals/approval-test-123")

        assert response.status_code == 200
        data = response.json()
        # Status should be lowercase in response
        assert data["status"] == "pending"

    def test_risk_level_lowercase_in_response(self, client, mock_storage, sample_approval_request):
        """Test that risk level values are lowercase in API responses."""
        mock_storage.get = AsyncMock(return_value=sample_approval_request)

        response = client.get("/api/v1/ag-ui/approvals/approval-test-123")

        assert response.status_code == 200
        data = response.json()
        # Risk level should be lowercase in response
        assert data["risk_level"] == "high"
