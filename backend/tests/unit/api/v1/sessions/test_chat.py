"""
Unit tests for Session Chat API (S46-3)

Tests:
- Chat endpoints (sync/stream)
- Approval endpoints
- Cancel endpoint
- Error handling

Uses FastAPI dependency_overrides for proper mock injection.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from typing import AsyncGenerator, List

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from src.api.v1.sessions.chat import (
    router,
    get_session_bridge,
    ChatRequest,
    ChatResponse,
    ApprovalRequest,
    ApprovalResponse,
    PendingApprovalsResponse,
    PendingApprovalItem,
    CancelResponse,
)
from src.domain.sessions.events import (
    ExecutionEvent,
    ExecutionEventType,
    ExecutionEventFactory,
    ToolCallInfo,
    ToolResultInfo,
)
from src.domain.sessions.approval import ToolApprovalRequest, ApprovalStatus
from src.domain.sessions.bridge import (
    SessionNotFoundError,
    SessionNotActiveError,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_bridge():
    """Create mock SessionAgentBridge"""
    bridge = MagicMock()
    bridge.process_message = AsyncMock()
    bridge.handle_tool_approval = AsyncMock()
    bridge.get_pending_approvals = AsyncMock(return_value=[])
    bridge.cancel_pending_approvals = AsyncMock(return_value=0)
    return bridge


@pytest.fixture
def app(mock_bridge) -> FastAPI:
    """Create test FastAPI application with dependency override"""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/sessions")

    # Override dependency to return mock bridge
    async def override_get_session_bridge():
        return mock_bridge

    app.dependency_overrides[get_session_bridge] = override_get_session_bridge

    yield app

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def test_client(app: FastAPI) -> TestClient:
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_events() -> List[ExecutionEvent]:
    """Create mock execution events using factory methods"""
    return [
        ExecutionEventFactory.started(
            session_id="test-session",
            execution_id="exec-123",
        ),
        ExecutionEventFactory.content(
            session_id="test-session",
            execution_id="exec-123",
            content="Hello! ",
        ),
        ExecutionEventFactory.content(
            session_id="test-session",
            execution_id="exec-123",
            content="How can I help?",
        ),
        ExecutionEventFactory.done(
            session_id="test-session",
            execution_id="exec-123",
            finish_reason="stop",
            message_id="msg-123",  # via metadata
        ),
    ]


@pytest.fixture
def mock_approval_request() -> ToolApprovalRequest:
    """Create mock approval request with correct field structure"""
    now = datetime.utcnow()
    return ToolApprovalRequest(
        id="approval-123",  # Use 'id' not 'approval_id'
        session_id="test-session",
        execution_id="exec-123",
        tool_call={  # Dict, not individual fields
            "id": "tool-call-123",
            "name": "file_write",
            "arguments": {"path": "/tmp/test.txt", "content": "test"},
        },
        created_at=now,
        expires_at=now + timedelta(minutes=5),
        status=ApprovalStatus.PENDING,
    )


# =============================================================================
# Chat Endpoint Tests
# =============================================================================

class TestChatEndpoint:
    """Test chat endpoint"""

    def test_chat_success(
        self, test_client: TestClient, mock_bridge, mock_events
    ):
        """Test successful chat request"""
        async def mock_process_message(*args, **kwargs):
            for event in mock_events:
                yield event

        mock_bridge.process_message = mock_process_message

        response = test_client.post(
            "/api/v1/sessions/test-session/chat",
            json={"content": "Hello", "stream": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session"
        assert "Hello!" in data["content"]
        assert "How can I help?" in data["content"]

    def test_chat_stream_redirect(self, test_client: TestClient, mock_bridge):
        """Test chat with stream=True returns error"""
        response = test_client.post(
            "/api/v1/sessions/test-session/chat",
            json={"content": "Hello", "stream": True},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "STREAM_NOT_SUPPORTED"

    def test_chat_session_not_found(self, test_client: TestClient, mock_bridge):
        """Test chat with non-existent session"""
        async def mock_process_message(*args, **kwargs):
            raise SessionNotFoundError("Session not found")
            yield  # Make it a generator

        mock_bridge.process_message = mock_process_message

        response = test_client.post(
            "/api/v1/sessions/nonexistent/chat",
            json={"content": "Hello", "stream": False},
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"] == "SESSION_NOT_FOUND"

    def test_chat_session_not_active(self, test_client: TestClient, mock_bridge):
        """Test chat with inactive session"""
        async def mock_process_message(*args, **kwargs):
            raise SessionNotActiveError("Session not active")
            yield

        mock_bridge.process_message = mock_process_message

        response = test_client.post(
            "/api/v1/sessions/test-session/chat",
            json={"content": "Hello", "stream": False},
        )

        assert response.status_code == 410
        data = response.json()
        assert data["detail"]["error"] == "SESSION_NOT_ACTIVE"

    def test_chat_with_execution_error(self, test_client: TestClient, mock_bridge):
        """Test chat handling execution error"""
        error_events = [
            ExecutionEventFactory.error(
                session_id="test-session",
                execution_id="exec-123",
                error_message="Tool execution failed",
                error_code="TOOL_ERROR",
            )
        ]

        async def mock_process_message(*args, **kwargs):
            for event in error_events:
                yield event

        mock_bridge.process_message = mock_process_message

        response = test_client.post(
            "/api/v1/sessions/test-session/chat",
            json={"content": "Hello", "stream": False},
        )

        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["error"] == "EXECUTION_ERROR"

    def test_chat_with_tool_calls(self, test_client: TestClient, mock_bridge):
        """Test chat returning tool calls"""
        events_with_tool = [
            ExecutionEventFactory.tool_call(
                session_id="test-session",
                execution_id="exec-123",
                tool_call_id="tc-123",
                tool_name="calculator",
                arguments={"expression": "2+2"},
            ),
            ExecutionEventFactory.tool_result(
                session_id="test-session",
                execution_id="exec-123",
                tool_call_id="tc-123",
                tool_name="calculator",
                result={"result": 4},
            ),
            ExecutionEventFactory.content(
                session_id="test-session",
                execution_id="exec-123",
                content="The result is 4",
            ),
            ExecutionEventFactory.done(
                session_id="test-session",
                execution_id="exec-123",
            ),
        ]

        async def mock_process_message(*args, **kwargs):
            for event in events_with_tool:
                yield event

        mock_bridge.process_message = mock_process_message

        response = test_client.post(
            "/api/v1/sessions/test-session/chat",
            json={"content": "Calculate 2+2", "stream": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["tool_calls"]) == 1
        assert data["tool_calls"][0]["name"] == "calculator"

    def test_chat_with_pending_approvals(self, test_client: TestClient, mock_bridge):
        """Test chat returning pending approvals"""
        events_with_approval = [
            ExecutionEventFactory.approval_required(
                session_id="test-session",
                execution_id="exec-123",
                approval_request_id="approval-123",
                tool_call_id="tc-123",
                tool_name="file_write",
                arguments={"path": "/tmp/test.txt"},
            ),
        ]

        async def mock_process_message(*args, **kwargs):
            for event in events_with_approval:
                yield event

        mock_bridge.process_message = mock_process_message

        response = test_client.post(
            "/api/v1/sessions/test-session/chat",
            json={"content": "Write file", "stream": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["pending_approvals"]) == 1
        assert data["pending_approvals"][0]["approval_request_id"] == "approval-123"


# =============================================================================
# Streaming Chat Tests
# =============================================================================

class TestChatStreamEndpoint:
    """Test streaming chat endpoint"""

    def test_stream_returns_sse(
        self, test_client: TestClient, mock_bridge, mock_events
    ):
        """Test streaming returns SSE format"""
        async def mock_process_message(*args, **kwargs):
            for event in mock_events:
                yield event

        mock_bridge.process_message = mock_process_message

        response = test_client.post(
            "/api/v1/sessions/test-session/chat/stream",
            json={"content": "Hello"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Check SSE format
        content = response.text
        assert "event:" in content
        assert "data:" in content


# =============================================================================
# Approval Endpoint Tests
# =============================================================================

class TestApprovalEndpoints:
    """Test approval endpoints"""

    def test_get_pending_approvals_empty(self, test_client: TestClient, mock_bridge):
        """Test getting empty pending approvals"""
        mock_bridge.get_pending_approvals = AsyncMock(return_value=[])

        response = test_client.get("/api/v1/sessions/test-session/approvals")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session"
        assert data["approvals"] == []
        assert data["total"] == 0

    def test_get_pending_approvals_with_items(
        self, test_client: TestClient, mock_bridge, mock_approval_request
    ):
        """Test getting pending approvals with items"""
        mock_bridge.get_pending_approvals = AsyncMock(return_value=[mock_approval_request])

        response = test_client.get("/api/v1/sessions/test-session/approvals")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        # Uses ToolApprovalRequest.id mapped to approval_id in response
        assert data["approvals"][0]["approval_id"] == "approval-123"
        # Uses ToolApprovalRequest.tool_name property
        assert data["approvals"][0]["tool_name"] == "file_write"

    def test_handle_approval_approve(self, test_client: TestClient, mock_bridge):
        """Test approving a request"""
        approval_events = [
            ExecutionEventFactory.approval_response(
                session_id="test-session",
                execution_id="exec-123",
                approval_request_id="approval-123",
                approved=True,
                feedback="Approved by user",
            ),
            ExecutionEventFactory.tool_result(
                session_id="test-session",
                execution_id="exec-123",
                tool_call_id="tc-123",
                tool_name="file_write",
                result={"success": True},
            ),
        ]

        async def mock_handle_approval(*args, **kwargs):
            for event in approval_events:
                yield event

        mock_bridge.handle_tool_approval = mock_handle_approval

        response = test_client.post(
            "/api/v1/sessions/test-session/approvals/approval-123",
            json={"approved": True, "feedback": "Looks good"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["approval_id"] == "approval-123"
        assert data["approved"] is True
        assert data["status"] == "approved"

    def test_handle_approval_reject(self, test_client: TestClient, mock_bridge):
        """Test rejecting a request"""
        rejection_events = [
            ExecutionEventFactory.approval_response(
                session_id="test-session",
                execution_id="exec-123",
                approval_request_id="approval-123",
                approved=False,
                feedback="Too risky",
            ),
        ]

        async def mock_handle_approval(*args, **kwargs):
            for event in rejection_events:
                yield event

        mock_bridge.handle_tool_approval = mock_handle_approval

        response = test_client.post(
            "/api/v1/sessions/test-session/approvals/approval-123",
            json={"approved": False, "feedback": "Too risky"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["approved"] is False
        assert data["status"] == "rejected"
        assert data["feedback"] == "Too risky"

    def test_handle_approval_not_found(self, test_client: TestClient, mock_bridge):
        """Test handling non-existent approval"""
        from src.domain.sessions.approval import ApprovalNotFoundError

        async def mock_handle_approval(*args, **kwargs):
            raise ApprovalNotFoundError("Approval not found")
            yield

        mock_bridge.handle_tool_approval = mock_handle_approval

        response = test_client.post(
            "/api/v1/sessions/test-session/approvals/nonexistent",
            json={"approved": True},
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"] == "APPROVAL_NOT_FOUND"


# =============================================================================
# Cancel Endpoint Tests
# =============================================================================

class TestCancelEndpoint:
    """Test cancel endpoint"""

    def test_cancel_approvals_success(self, test_client: TestClient, mock_bridge):
        """Test canceling approvals successfully"""
        mock_bridge.cancel_pending_approvals = AsyncMock(return_value=3)

        response = test_client.delete(
            "/api/v1/sessions/test-session/approvals?reason=user_cancelled"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session"
        assert data["cancelled_count"] == 3
        assert data["reason"] == "user_cancelled"

    def test_cancel_approvals_none_pending(self, test_client: TestClient, mock_bridge):
        """Test canceling when no approvals pending"""
        mock_bridge.cancel_pending_approvals = AsyncMock(return_value=0)

        response = test_client.delete("/api/v1/sessions/test-session/approvals")

        assert response.status_code == 200
        data = response.json()
        assert data["cancelled_count"] == 0


# =============================================================================
# Status Endpoint Tests
# =============================================================================

class TestStatusEndpoint:
    """Test status endpoint"""

    def test_get_chat_status(self, test_client: TestClient, mock_bridge):
        """Test getting chat status"""
        mock_bridge.get_pending_approvals = AsyncMock(return_value=[])

        response = test_client.get("/api/v1/sessions/test-session/chat/status")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session"
        assert "pending_approvals_count" in data
        assert "timestamp" in data

    def test_get_chat_status_session_not_found(
        self, test_client: TestClient, mock_bridge
    ):
        """Test getting status for non-existent session"""
        mock_bridge.get_pending_approvals = AsyncMock(
            side_effect=SessionNotFoundError("Session not found")
        )

        response = test_client.get("/api/v1/sessions/nonexistent/chat/status")

        assert response.status_code == 404


# =============================================================================
# Request Validation Tests
# =============================================================================

class TestRequestValidation:
    """Test request validation"""

    def test_chat_empty_content(self, test_client: TestClient, mock_bridge):
        """Test chat with empty content"""
        response = test_client.post(
            "/api/v1/sessions/test-session/chat",
            json={"content": "", "stream": False},
        )

        assert response.status_code == 422  # Validation error

    def test_chat_content_too_long(self, test_client: TestClient, mock_bridge):
        """Test chat with content too long"""
        response = test_client.post(
            "/api/v1/sessions/test-session/chat",
            json={"content": "x" * 100001, "stream": False},
        )

        assert response.status_code == 422  # Validation error

    def test_approval_missing_required_field(self, test_client: TestClient, mock_bridge):
        """Test approval without required approved field"""
        response = test_client.post(
            "/api/v1/sessions/test-session/approvals/approval-123",
            json={},  # Missing 'approved' field
        )

        assert response.status_code == 422
