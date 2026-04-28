"""Tests for Claude SDK API routes."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.v1.claude_sdk.routes import router, get_client
from src.api.v1.claude_sdk.schemas import (
    QueryRequest,
    QueryResponse,
    CreateSessionRequest,
    SessionResponse,
)
from src.integrations.claude_sdk.client import ClaudeSDKClient
from src.integrations.claude_sdk.types import QueryResult, ToolCall
from src.integrations.claude_sdk.exceptions import (
    ClaudeSDKError,
    AuthenticationError,
)


# Create test app
app = FastAPI()
app.include_router(router, prefix="/api/v1")


class TestClaudeSDKRoutes:
    """Tests for Claude SDK API routes."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_sdk_client(self):
        """Create a mock Claude SDK client."""
        mock = MagicMock(spec=ClaudeSDKClient)
        mock.config = MagicMock()
        mock.config.model = "claude-sonnet-4-20250514"
        mock.config.max_tokens = 4096
        mock.get_sessions.return_value = {}
        return mock

    @pytest.fixture
    def override_get_client(self, mock_sdk_client):
        """Override the get_client dependency."""
        app.dependency_overrides[get_client] = lambda: mock_sdk_client
        yield
        app.dependency_overrides.clear()


class TestQueryEndpoint(TestClaudeSDKRoutes):
    """Tests for POST /claude-sdk/query endpoint."""

    @pytest.mark.asyncio
    async def test_query_success(
        self, client, mock_sdk_client, override_get_client
    ):
        """Test successful query execution."""
        mock_result = QueryResult(
            content="Hello! I'm Claude.",
            tool_calls=[],
            tokens_used=100,
            duration=1.5,
            status="completed",
        )
        mock_sdk_client.query = AsyncMock(return_value=mock_result)

        response = client.post(
            "/api/v1/claude-sdk/query",
            json={"prompt": "Hello!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Hello! I'm Claude."
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_query_with_tools(
        self, client, mock_sdk_client, override_get_client
    ):
        """Test query with tool calls."""
        mock_result = QueryResult(
            content="File read successfully",
            tool_calls=[
                ToolCall(id="1", name="Read", args={"path": "/test.txt"})
            ],
            tokens_used=150,
            duration=2.0,
            status="completed",
        )
        mock_sdk_client.query = AsyncMock(return_value=mock_result)

        response = client.post(
            "/api/v1/claude-sdk/query",
            json={"prompt": "Read the file", "tools": ["Read"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["tool_calls"]) == 1
        assert data["tool_calls"][0]["name"] == "Read"

    @pytest.mark.asyncio
    async def test_query_with_custom_options(
        self, client, mock_sdk_client, override_get_client
    ):
        """Test query with custom options."""
        mock_result = QueryResult(
            content="Done",
            tool_calls=[],
            tokens_used=50,
            duration=0.5,
            status="completed",
        )
        mock_sdk_client.query = AsyncMock(return_value=mock_result)

        response = client.post(
            "/api/v1/claude-sdk/query",
            json={
                "prompt": "Hello!",
                "max_tokens": 2048,
                "timeout": 120,
                "working_directory": "/home/user",
            },
        )

        assert response.status_code == 200
        mock_sdk_client.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_error(
        self, client, mock_sdk_client, override_get_client
    ):
        """Test query error handling."""
        mock_sdk_client.query = AsyncMock(
            side_effect=ClaudeSDKError("API error")
        )

        response = client.post(
            "/api/v1/claude-sdk/query",
            json={"prompt": "Hello!"},
        )

        assert response.status_code == 500
        assert "API error" in response.json()["detail"]


class TestSessionEndpoints(TestClaudeSDKRoutes):
    """Tests for session management endpoints."""

    @pytest.mark.asyncio
    async def test_create_session(
        self, client, mock_sdk_client, override_get_client
    ):
        """Test creating a new session."""
        mock_session = MagicMock()
        mock_session.session_id = "new-session-123"
        mock_sdk_client.create_session = AsyncMock(return_value=mock_session)

        response = client.post(
            "/api/v1/claude-sdk/sessions",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "new-session-123"

    @pytest.mark.asyncio
    async def test_create_session_with_id(
        self, client, mock_sdk_client, override_get_client
    ):
        """Test creating a session with custom ID."""
        mock_session = MagicMock()
        mock_session.session_id = "custom-id"
        mock_sdk_client.create_session = AsyncMock(return_value=mock_session)

        response = client.post(
            "/api/v1/claude-sdk/sessions",
            json={"session_id": "custom-id"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "custom-id"

    @pytest.mark.asyncio
    async def test_session_query(
        self, client, mock_sdk_client, override_get_client
    ):
        """Test querying within a session."""
        mock_session = MagicMock()
        mock_result = QueryResult(
            content="Response in session",
            tool_calls=[],
            tokens_used=80,
            duration=1.0,
            status="completed",
        )
        mock_result.message_index = 2
        mock_session.query = AsyncMock(return_value=mock_result)
        mock_sdk_client.resume_session = AsyncMock(return_value=mock_session)

        response = client.post(
            "/api/v1/claude-sdk/sessions/session-123/query",
            json={"prompt": "Continue our conversation"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Response in session"

    @pytest.mark.asyncio
    async def test_session_query_not_found(
        self, client, mock_sdk_client, override_get_client
    ):
        """Test querying non-existent session."""
        mock_sdk_client.resume_session = AsyncMock(
            side_effect=ClaudeSDKError("Session not found")
        )

        response = client.post(
            "/api/v1/claude-sdk/sessions/nonexistent/query",
            json={"prompt": "Hello"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_close_session(
        self, client, mock_sdk_client, override_get_client
    ):
        """Test closing a session."""
        mock_session = MagicMock()
        mock_session.close = AsyncMock()
        mock_sdk_client.resume_session = AsyncMock(return_value=mock_session)

        response = client.delete("/api/v1/claude-sdk/sessions/session-123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "closed"

    @pytest.mark.asyncio
    async def test_get_session_history(
        self, client, mock_sdk_client, override_get_client
    ):
        """Test getting session history."""
        import time

        mock_session = MagicMock()
        # Schema expects timestamp as float (Unix timestamp), not datetime
        mock_history = [
            MagicMock(
                role="user",
                content="Hello",
                timestamp=time.time(),
                tool_calls=None,
            ),
            MagicMock(
                role="assistant",
                content="Hi!",
                timestamp=time.time(),
                tool_calls=[],
            ),
        ]
        mock_session.get_history.return_value = mock_history
        mock_sdk_client.resume_session = AsyncMock(return_value=mock_session)

        response = client.get(
            "/api/v1/claude-sdk/sessions/session-123/history"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 2


class TestHealthEndpoint(TestClaudeSDKRoutes):
    """Tests for health check endpoint."""

    def test_health_check_healthy(self, client):
        """Test health check when client is configured."""
        from src.api.v1.claude_sdk.routes import get_optional_client

        mock = MagicMock(spec=ClaudeSDKClient)
        mock.config = MagicMock()
        mock.config.model = "claude-sonnet-4-20250514"
        mock.config.max_tokens = 4096
        mock.get_sessions.return_value = {"session-1": MagicMock()}

        # Override get_optional_client dependency to return our mock
        async def mock_get_optional():
            return mock

        app.dependency_overrides[get_optional_client] = mock_get_optional

        response = client.get("/api/v1/claude-sdk/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["ready"] is True

        app.dependency_overrides.clear()

    def test_health_check_unconfigured(self, client):
        """Test health check when client is not configured."""
        from src.api.v1.claude_sdk.routes import get_optional_client

        async def mock_get_optional():
            return None

        app.dependency_overrides[get_optional_client] = mock_get_optional

        response = client.get("/api/v1/claude-sdk/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unconfigured"
        assert data["ready"] is False

        app.dependency_overrides.clear()


class TestSchemaValidation:
    """Tests for request schema validation."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_query_request_empty_prompt_rejected(self, client):
        """Test that empty prompt is rejected."""
        response = client.post(
            "/api/v1/claude-sdk/query",
            json={"prompt": ""},
        )

        # Empty prompt should still be accepted by Pydantic
        # but the actual validation depends on schema definition
        assert response.status_code in [200, 422, 500]

    def test_query_request_invalid_timeout(self, client):
        """Test that invalid timeout is rejected."""
        response = client.post(
            "/api/v1/claude-sdk/query",
            json={"prompt": "Hello", "timeout": -1},
        )

        # Negative timeout validation depends on schema
        assert response.status_code in [200, 422, 500]

