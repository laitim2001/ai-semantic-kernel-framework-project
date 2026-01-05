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


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def app():
    """Create FastAPI app with AG-UI router for testing."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1/ag-ui")
    return test_app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_approval_request():
    """Create a mock approval request object."""
    mock = MagicMock()
    mock.approval_id = "approval-test-123"
    mock.tool_call_id = "tc-456"
    mock.tool_name = "Bash"
    mock.arguments = {"command": "ls -la"}
    mock.risk_level = "HIGH"
    mock.risk_score = 0.75
    mock.reasoning = "Shell command with potential risk"
    mock.run_id = "run-789"
    mock.session_id = "session-abc"
    mock.status = "PENDING"
    mock.created_at = datetime.utcnow()
    mock.expires_at = datetime.utcnow() + timedelta(seconds=300)
    mock.resolved_at = None
    mock.user_comment = None
    return mock


@pytest.fixture
def mock_approved_request(mock_approval_request):
    """Create a mock approved request object."""
    mock = MagicMock()
    mock.approval_id = mock_approval_request.approval_id
    mock.tool_call_id = mock_approval_request.tool_call_id
    mock.tool_name = mock_approval_request.tool_name
    mock.arguments = mock_approval_request.arguments
    mock.risk_level = mock_approval_request.risk_level
    mock.risk_score = mock_approval_request.risk_score
    mock.reasoning = mock_approval_request.reasoning
    mock.run_id = mock_approval_request.run_id
    mock.session_id = mock_approval_request.session_id
    mock.status = "APPROVED"
    mock.created_at = mock_approval_request.created_at
    mock.expires_at = mock_approval_request.expires_at
    mock.resolved_at = datetime.utcnow()
    mock.user_comment = "Looks safe to execute"
    return mock


@pytest.fixture
def mock_rejected_request(mock_approval_request):
    """Create a mock rejected request object."""
    mock = MagicMock()
    mock.approval_id = mock_approval_request.approval_id
    mock.tool_call_id = mock_approval_request.tool_call_id
    mock.tool_name = mock_approval_request.tool_name
    mock.arguments = mock_approval_request.arguments
    mock.risk_level = mock_approval_request.risk_level
    mock.risk_score = mock_approval_request.risk_score
    mock.reasoning = mock_approval_request.reasoning
    mock.run_id = mock_approval_request.run_id
    mock.session_id = mock_approval_request.session_id
    mock.status = "REJECTED"
    mock.created_at = mock_approval_request.created_at
    mock.expires_at = mock_approval_request.expires_at
    mock.resolved_at = datetime.utcnow()
    mock.user_comment = "Not safe"
    return mock


# =============================================================================
# Test: GET /approvals/pending
# =============================================================================


class TestListPendingApprovals:
    """Tests for GET /approvals/pending endpoint."""

    def test_list_pending_empty(self, client):
        """Test listing pending approvals when none exist."""
        with patch(
            "src.api.v1.ag_ui.routes.get_approval_storage"
        ) as mock_get_storage:
            mock_storage = AsyncMock()
            mock_storage.get_pending = AsyncMock(return_value=[])
            mock_get_storage.return_value = mock_storage

            response = client.get("/api/v1/ag-ui/approvals/pending")

            assert response.status_code == 200
            data = response.json()
            assert data["pending"] == []
            assert data["total"] == 0

    def test_list_pending_with_approvals(self, client, mock_approval_request):
        """Test listing pending approvals when some exist."""
        with patch(
            "src.api.v1.ag_ui.routes.get_approval_storage"
        ) as mock_get_storage:
            mock_storage = AsyncMock()
            mock_storage.get_pending = AsyncMock(return_value=[mock_approval_request])
            mock_get_storage.return_value = mock_storage

            response = client.get("/api/v1/ag-ui/approvals/pending")

            assert response.status_code == 200
            data = response.json()
            assert len(data["pending"]) == 1
            assert data["total"] == 1
            assert data["pending"][0]["approval_id"] == "approval-test-123"

    def test_list_pending_with_session_filter(self, client, mock_approval_request):
        """Test listing pending approvals filtered by session ID."""
        with patch(
            "src.api.v1.ag_ui.routes.get_approval_storage"
        ) as mock_get_storage:
            mock_storage = AsyncMock()
            mock_storage.get_pending = AsyncMock(return_value=[mock_approval_request])
            mock_get_storage.return_value = mock_storage

            response = client.get(
                "/api/v1/ag-ui/approvals/pending?session_id=session-abc"
            )

            assert response.status_code == 200
            mock_storage.get_pending.assert_called_once_with(
                session_id="session-abc", run_id=None
            )

    def test_list_pending_with_run_filter(self, client, mock_approval_request):
        """Test listing pending approvals filtered by run ID."""
        with patch(
            "src.api.v1.ag_ui.routes.get_approval_storage"
        ) as mock_get_storage:
            mock_storage = AsyncMock()
            mock_storage.get_pending = AsyncMock(return_value=[mock_approval_request])
            mock_get_storage.return_value = mock_storage

            response = client.get(
                "/api/v1/ag-ui/approvals/pending?run_id=run-789"
            )

            assert response.status_code == 200
            mock_storage.get_pending.assert_called_once_with(
                session_id=None, run_id="run-789"
            )

    def test_list_pending_with_both_filters(self, client, mock_approval_request):
        """Test listing pending approvals filtered by session and run ID."""
        with patch(
            "src.api.v1.ag_ui.routes.get_approval_storage"
        ) as mock_get_storage:
            mock_storage = AsyncMock()
            mock_storage.get_pending = AsyncMock(return_value=[mock_approval_request])
            mock_get_storage.return_value = mock_storage

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

    def test_get_approval_success(self, client, mock_approval_request):
        """Test getting an existing approval request."""
        with patch(
            "src.api.v1.ag_ui.routes.get_approval_storage"
        ) as mock_get_storage:
            mock_storage = AsyncMock()
            mock_storage.get = AsyncMock(return_value=mock_approval_request)
            mock_get_storage.return_value = mock_storage

            response = client.get("/api/v1/ag-ui/approvals/approval-test-123")

            assert response.status_code == 200
            data = response.json()
            assert data["approval_id"] == "approval-test-123"
            assert data["tool_name"] == "Bash"
            assert data["status"] == "pending"

    def test_get_approval_not_found(self, client):
        """Test getting a non-existent approval request."""
        with patch(
            "src.api.v1.ag_ui.routes.get_approval_storage"
        ) as mock_get_storage:
            mock_storage = AsyncMock()
            mock_storage.get = AsyncMock(return_value=None)
            mock_get_storage.return_value = mock_storage

            response = client.get("/api/v1/ag-ui/approvals/non-existent-id")

            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"]["message"].lower()


# =============================================================================
# Test: POST /approvals/{approval_id}/approve
# =============================================================================


class TestApproveToolCall:
    """Tests for POST /approvals/{approval_id}/approve endpoint."""

    def test_approve_success(self, client, mock_approved_request):
        """Test approving a pending tool call."""
        with patch(
            "src.api.v1.ag_ui.routes.get_hitl_handler"
        ) as mock_get_hitl:
            mock_hitl = AsyncMock()
            mock_hitl.handle_approval_response = AsyncMock(
                return_value=(True, mock_approved_request)
            )
            mock_get_hitl.return_value = mock_hitl

            response = client.post(
                "/api/v1/ag-ui/approvals/approval-test-123/approve",
                json={"comment": "Approved by admin"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "approved"
            assert "approved successfully" in data["message"].lower()

    def test_approve_without_comment(self, client, mock_approved_request):
        """Test approving without a comment."""
        with patch(
            "src.api.v1.ag_ui.routes.get_hitl_handler"
        ) as mock_get_hitl:
            mock_hitl = AsyncMock()
            mock_hitl.handle_approval_response = AsyncMock(
                return_value=(True, mock_approved_request)
            )
            mock_get_hitl.return_value = mock_hitl

            response = client.post(
                "/api/v1/ag-ui/approvals/approval-test-123/approve",
                json={}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_approve_not_found(self, client):
        """Test approving a non-existent request."""
        with patch(
            "src.api.v1.ag_ui.routes.get_hitl_handler"
        ) as mock_get_hitl:
            mock_hitl = AsyncMock()
            mock_hitl.handle_approval_response = AsyncMock(
                return_value=(False, None)
            )
            mock_get_hitl.return_value = mock_hitl

            response = client.post(
                "/api/v1/ag-ui/approvals/non-existent-id/approve",
                json={}
            )

            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"]["message"].lower()

    def test_approve_already_resolved(self, client, mock_approved_request):
        """Test approving an already resolved request."""
        # Return False (failure) with the already-resolved request
        mock_approved_request.status = "APPROVED"

        with patch(
            "src.api.v1.ag_ui.routes.get_hitl_handler"
        ) as mock_get_hitl:
            mock_hitl = AsyncMock()
            mock_hitl.handle_approval_response = AsyncMock(
                return_value=(False, mock_approved_request)
            )
            mock_get_hitl.return_value = mock_hitl

            response = client.post(
                "/api/v1/ag-ui/approvals/approval-test-123/approve",
                json={}
            )

            assert response.status_code == 409
            data = response.json()
            assert "already resolved" in data["detail"]["message"].lower() or "expired" in data["detail"]["message"].lower()


# =============================================================================
# Test: POST /approvals/{approval_id}/reject
# =============================================================================


class TestRejectToolCall:
    """Tests for POST /approvals/{approval_id}/reject endpoint."""

    def test_reject_success(self, client, mock_rejected_request):
        """Test rejecting a pending tool call."""
        with patch(
            "src.api.v1.ag_ui.routes.get_hitl_handler"
        ) as mock_get_hitl:
            mock_hitl = AsyncMock()
            mock_hitl.handle_approval_response = AsyncMock(
                return_value=(True, mock_rejected_request)
            )
            mock_get_hitl.return_value = mock_hitl

            response = client.post(
                "/api/v1/ag-ui/approvals/approval-test-123/reject",
                json={"comment": "Too risky"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "rejected"
            assert "rejected" in data["message"].lower()

    def test_reject_without_comment(self, client, mock_rejected_request):
        """Test rejecting without a comment."""
        with patch(
            "src.api.v1.ag_ui.routes.get_hitl_handler"
        ) as mock_get_hitl:
            mock_hitl = AsyncMock()
            mock_hitl.handle_approval_response = AsyncMock(
                return_value=(True, mock_rejected_request)
            )
            mock_get_hitl.return_value = mock_hitl

            response = client.post(
                "/api/v1/ag-ui/approvals/approval-test-123/reject",
                json={}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_reject_not_found(self, client):
        """Test rejecting a non-existent request."""
        with patch(
            "src.api.v1.ag_ui.routes.get_hitl_handler"
        ) as mock_get_hitl:
            mock_hitl = AsyncMock()
            mock_hitl.handle_approval_response = AsyncMock(
                return_value=(False, None)
            )
            mock_get_hitl.return_value = mock_hitl

            response = client.post(
                "/api/v1/ag-ui/approvals/non-existent-id/reject",
                json={}
            )

            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"]["message"].lower()

    def test_reject_already_resolved(self, client, mock_rejected_request):
        """Test rejecting an already resolved request."""
        mock_rejected_request.status = "REJECTED"

        with patch(
            "src.api.v1.ag_ui.routes.get_hitl_handler"
        ) as mock_get_hitl:
            mock_hitl = AsyncMock()
            mock_hitl.handle_approval_response = AsyncMock(
                return_value=(False, mock_rejected_request)
            )
            mock_get_hitl.return_value = mock_hitl

            response = client.post(
                "/api/v1/ag-ui/approvals/approval-test-123/reject",
                json={}
            )

            assert response.status_code == 409
            data = response.json()
            assert "already resolved" in data["detail"]["message"].lower() or "expired" in data["detail"]["message"].lower()


# =============================================================================
# Test: POST /approvals/{approval_id}/cancel
# =============================================================================


class TestCancelApproval:
    """Tests for POST /approvals/{approval_id}/cancel endpoint."""

    def test_cancel_success(self, client, mock_approval_request):
        """Test cancelling a pending approval request."""
        mock_approval_request.status = "CANCELLED"

        with patch(
            "src.api.v1.ag_ui.routes.get_approval_storage"
        ) as mock_get_storage:
            mock_storage = AsyncMock()
            mock_storage.cancel = AsyncMock(return_value=True)
            mock_storage.get = AsyncMock(return_value=mock_approval_request)
            mock_get_storage.return_value = mock_storage

            response = client.post(
                "/api/v1/ag-ui/approvals/approval-test-123/cancel"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "cancelled"

    def test_cancel_not_found(self, client):
        """Test cancelling a non-existent request."""
        with patch(
            "src.api.v1.ag_ui.routes.get_approval_storage"
        ) as mock_get_storage:
            mock_storage = AsyncMock()
            mock_storage.cancel = AsyncMock(return_value=False)
            mock_storage.get = AsyncMock(return_value=None)
            mock_get_storage.return_value = mock_storage

            response = client.post(
                "/api/v1/ag-ui/approvals/non-existent-id/cancel"
            )

            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"]["message"].lower()

    def test_cancel_already_resolved(self, client, mock_approved_request):
        """Test cancelling an already resolved request."""
        with patch(
            "src.api.v1.ag_ui.routes.get_approval_storage"
        ) as mock_get_storage:
            mock_storage = AsyncMock()
            mock_storage.cancel = AsyncMock(return_value=False)
            mock_storage.get = AsyncMock(return_value=mock_approved_request)
            mock_get_storage.return_value = mock_storage

            response = client.post(
                "/api/v1/ag-ui/approvals/approval-test-123/cancel"
            )

            assert response.status_code == 409
            data = response.json()
            assert "already resolved" in data["detail"]["message"].lower()


# =============================================================================
# Test: GET /approvals/stats
# =============================================================================


class TestGetApprovalStats:
    """Tests for GET /approvals/stats endpoint."""

    def test_get_stats_empty(self, client):
        """Test getting stats when no approvals exist."""
        with patch(
            "src.api.v1.ag_ui.routes.get_approval_storage"
        ) as mock_get_storage:
            mock_storage = AsyncMock()
            mock_storage.get_stats = MagicMock(return_value={
                "total": 0,
                "pending": 0,
                "approved": 0,
                "rejected": 0,
                "timeout": 0,
                "cancelled": 0,
            })
            mock_get_storage.return_value = mock_storage

            response = client.get("/api/v1/ag-ui/approvals/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert data["pending"] == 0
            assert data["approved"] == 0
            assert data["rejected"] == 0
            assert data["timeout"] == 0
            assert data["cancelled"] == 0

    def test_get_stats_with_data(self, client):
        """Test getting stats when approvals exist."""
        with patch(
            "src.api.v1.ag_ui.routes.get_approval_storage"
        ) as mock_get_storage:
            mock_storage = AsyncMock()
            mock_storage.get_stats = MagicMock(return_value={
                "total": 10,
                "pending": 2,
                "approved": 5,
                "rejected": 2,
                "timeout": 1,
                "cancelled": 0,
            })
            mock_get_storage.return_value = mock_storage

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

    def test_pending_approvals_response_schema(self, client, mock_approval_request):
        """Test that pending approvals response matches expected schema."""
        with patch(
            "src.api.v1.ag_ui.routes.get_approval_storage"
        ) as mock_get_storage:
            mock_storage = AsyncMock()
            mock_storage.get_pending = AsyncMock(return_value=[mock_approval_request])
            mock_get_storage.return_value = mock_storage

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

    def test_approval_action_response_schema(self, client, mock_approved_request):
        """Test that approval action response matches expected schema."""
        with patch(
            "src.api.v1.ag_ui.routes.get_hitl_handler"
        ) as mock_get_hitl:
            mock_hitl = AsyncMock()
            mock_hitl.handle_approval_response = AsyncMock(
                return_value=(True, mock_approved_request)
            )
            mock_get_hitl.return_value = mock_hitl

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

    def test_stats_response_schema(self, client):
        """Test that stats response matches expected schema."""
        with patch(
            "src.api.v1.ag_ui.routes.get_approval_storage"
        ) as mock_get_storage:
            mock_storage = AsyncMock()
            mock_storage.get_stats = MagicMock(return_value={
                "total": 5,
                "pending": 1,
                "approved": 2,
                "rejected": 1,
                "timeout": 1,
                "cancelled": 0,
            })
            mock_get_storage.return_value = mock_storage

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

    def test_invalid_approval_id_format(self, client):
        """Test handling of malformed approval IDs."""
        with patch(
            "src.api.v1.ag_ui.routes.get_approval_storage"
        ) as mock_get_storage:
            mock_storage = AsyncMock()
            mock_storage.get = AsyncMock(return_value=None)
            mock_get_storage.return_value = mock_storage

            # Test with empty string - should return 404
            response = client.get("/api/v1/ag-ui/approvals/")

            # Empty path would either be 404 or redirect to list
            # Actual behavior depends on routing
            assert response.status_code in [307, 404, 405]

    def test_concurrent_approval_attempts(self, client, mock_approval_request):
        """Test behavior when approval is already processed."""
        # First request succeeds
        mock_approved_request = MagicMock()
        mock_approved_request.approval_id = mock_approval_request.approval_id
        mock_approved_request.status = "APPROVED"
        mock_approved_request.resolved_at = datetime.utcnow()

        with patch(
            "src.api.v1.ag_ui.routes.get_hitl_handler"
        ) as mock_get_hitl:
            mock_hitl = AsyncMock()
            # Second attempt fails
            mock_hitl.handle_approval_response = AsyncMock(
                return_value=(False, mock_approved_request)
            )
            mock_get_hitl.return_value = mock_hitl

            response = client.post(
                "/api/v1/ag-ui/approvals/approval-test-123/approve",
                json={}
            )

            # Should return conflict
            assert response.status_code == 409

    def test_long_comment_in_approval(self, client, mock_approved_request):
        """Test handling of long comments in approval action."""
        with patch(
            "src.api.v1.ag_ui.routes.get_hitl_handler"
        ) as mock_get_hitl:
            mock_hitl = AsyncMock()
            mock_hitl.handle_approval_response = AsyncMock(
                return_value=(True, mock_approved_request)
            )
            mock_get_hitl.return_value = mock_hitl

            long_comment = "A" * 500  # Max length comment
            response = client.post(
                "/api/v1/ag-ui/approvals/approval-test-123/approve",
                json={"comment": long_comment}
            )

            # Should accept max length comment
            assert response.status_code == 200

    def test_empty_pending_list_with_filters(self, client):
        """Test empty pending list when filters match nothing."""
        with patch(
            "src.api.v1.ag_ui.routes.get_approval_storage"
        ) as mock_get_storage:
            mock_storage = AsyncMock()
            mock_storage.get_pending = AsyncMock(return_value=[])
            mock_get_storage.return_value = mock_storage

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

    def test_pending_status_lowercase_in_response(self, client, mock_approval_request):
        """Test that status values are lowercase in API responses."""
        mock_approval_request.status = "PENDING"  # Internal representation

        with patch(
            "src.api.v1.ag_ui.routes.get_approval_storage"
        ) as mock_get_storage:
            mock_storage = AsyncMock()
            mock_storage.get = AsyncMock(return_value=mock_approval_request)
            mock_get_storage.return_value = mock_storage

            response = client.get("/api/v1/ag-ui/approvals/approval-test-123")

            assert response.status_code == 200
            data = response.json()
            # Status should be lowercase in response
            assert data["status"] == "pending"

    def test_risk_level_lowercase_in_response(self, client, mock_approval_request):
        """Test that risk level values are lowercase in API responses."""
        mock_approval_request.risk_level = "HIGH"  # Internal representation

        with patch(
            "src.api.v1.ag_ui.routes.get_approval_storage"
        ) as mock_get_storage:
            mock_storage = AsyncMock()
            mock_storage.get = AsyncMock(return_value=mock_approval_request)
            mock_get_storage.return_value = mock_storage

            response = client.get("/api/v1/ag-ui/approvals/approval-test-123")

            assert response.status_code == 200
            data = response.json()
            # Risk level should be lowercase in response
            assert data["risk_level"] == "high"
