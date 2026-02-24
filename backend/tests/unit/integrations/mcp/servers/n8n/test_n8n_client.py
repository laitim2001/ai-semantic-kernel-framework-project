"""Tests for N8nApiClient.

Sprint 124: n8n Integration — Mode 1 + Mode 2

Tests cover:
    - Configuration from environment variables
    - HTTP request handling with retry logic
    - Workflow CRUD operations
    - Execution operations
    - Error handling (auth, not found, rate limit, connection)
    - Health check
    - Client lifecycle
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.integrations.mcp.servers.n8n.client import (
    ExecutionStatus,
    N8nApiClient,
    N8nApiError,
    N8nAuthenticationError,
    N8nConfig,
    N8nConnectionError,
    N8nNotFoundError,
    N8nRateLimitError,
    WorkflowStatus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def n8n_config():
    """Create a test N8nConfig."""
    return N8nConfig(
        base_url="http://test-n8n:5678",
        api_key="test-api-key-12345",
        timeout=10,
        max_retries=2,
        retry_base_delay=0.01,  # Fast retries for testing
    )


@pytest.fixture
def n8n_client(n8n_config):
    """Create a test N8nApiClient."""
    return N8nApiClient(n8n_config)


@pytest.fixture
def mock_response():
    """Create a mock httpx.Response factory."""

    def _create(status_code=200, json_data=None, text="", headers=None):
        response = MagicMock(spec=httpx.Response)
        response.status_code = status_code
        response.text = text
        response.headers = headers or {}
        response.json.return_value = json_data or {}
        return response

    return _create


# ---------------------------------------------------------------------------
# N8nConfig Tests
# ---------------------------------------------------------------------------


class TestN8nConfig:
    """Tests for N8nConfig configuration."""

    def test_config_from_env_success(self, monkeypatch):
        """Test creating config from environment variables."""
        monkeypatch.setenv("N8N_BASE_URL", "http://prod-n8n:5678")
        monkeypatch.setenv("N8N_API_KEY", "prod-api-key")
        monkeypatch.setenv("N8N_TIMEOUT", "60")
        monkeypatch.setenv("N8N_MAX_RETRIES", "5")

        config = N8nConfig.from_env()

        assert config.base_url == "http://prod-n8n:5678"
        assert config.api_key == "prod-api-key"
        assert config.timeout == 60
        assert config.max_retries == 5

    def test_config_from_env_defaults(self, monkeypatch):
        """Test config defaults when only API key is provided."""
        monkeypatch.setenv("N8N_API_KEY", "test-key")
        monkeypatch.delenv("N8N_BASE_URL", raising=False)
        monkeypatch.delenv("N8N_TIMEOUT", raising=False)
        monkeypatch.delenv("N8N_MAX_RETRIES", raising=False)

        config = N8nConfig.from_env()

        assert config.base_url == "http://localhost:5678"
        assert config.timeout == 30
        assert config.max_retries == 3

    def test_config_from_env_missing_api_key(self, monkeypatch):
        """Test that missing API key raises ValueError."""
        monkeypatch.delenv("N8N_API_KEY", raising=False)

        with pytest.raises(ValueError, match="N8N_API_KEY"):
            N8nConfig.from_env()

    def test_config_strips_trailing_slash(self, monkeypatch):
        """Test that base_url trailing slash is stripped."""
        monkeypatch.setenv("N8N_API_KEY", "test")
        monkeypatch.setenv("N8N_BASE_URL", "http://n8n:5678/")

        config = N8nConfig.from_env()
        assert config.base_url == "http://n8n:5678"


# ---------------------------------------------------------------------------
# N8nApiClient — Workflow Operations
# ---------------------------------------------------------------------------


class TestN8nClientWorkflows:
    """Tests for N8nApiClient workflow operations."""

    @pytest.mark.asyncio
    async def test_list_workflows_success(self, n8n_client, mock_response):
        """Test listing workflows returns formatted data."""
        mock_resp = mock_response(
            json_data={
                "data": [
                    {
                        "id": "wf-1",
                        "name": "Password Reset",
                        "active": True,
                        "createdAt": "2026-01-01T00:00:00Z",
                        "updatedAt": "2026-01-15T00:00:00Z",
                        "tags": [{"name": "IT"}],
                    },
                    {
                        "id": "wf-2",
                        "name": "VM Provisioning",
                        "active": False,
                        "createdAt": "2026-01-10T00:00:00Z",
                        "updatedAt": "2026-01-20T00:00:00Z",
                        "tags": [],
                    },
                ],
                "nextCursor": "abc123",
            }
        )

        n8n_client._client.request = AsyncMock(return_value=mock_resp)

        result = await n8n_client.list_workflows(active=True, limit=10)

        assert len(result["data"]) == 2
        assert result["data"][0]["id"] == "wf-1"
        assert result["data"][0]["name"] == "Password Reset"
        assert result["nextCursor"] == "abc123"

    @pytest.mark.asyncio
    async def test_get_workflow_success(self, n8n_client, mock_response):
        """Test getting workflow details."""
        mock_resp = mock_response(
            json_data={
                "id": "wf-1",
                "name": "Password Reset",
                "active": True,
                "nodes": [
                    {"name": "Start", "type": "n8n-nodes-base.start"},
                    {"name": "HTTP Request", "type": "n8n-nodes-base.httpRequest"},
                ],
                "connections": {"Start": {"main": [[{"node": "HTTP Request"}]]}},
                "settings": {},
            }
        )

        n8n_client._client.request = AsyncMock(return_value=mock_resp)

        result = await n8n_client.get_workflow("wf-1")

        assert result["id"] == "wf-1"
        assert result["name"] == "Password Reset"
        assert len(result["nodes"]) == 2

    @pytest.mark.asyncio
    async def test_get_workflow_not_found(self, n8n_client, mock_response):
        """Test getting non-existent workflow raises N8nNotFoundError."""
        mock_resp = mock_response(status_code=404, text="Not found")

        n8n_client._client.request = AsyncMock(return_value=mock_resp)

        with pytest.raises(N8nNotFoundError):
            await n8n_client.get_workflow("nonexistent")

    @pytest.mark.asyncio
    async def test_activate_workflow_success(self, n8n_client, mock_response):
        """Test activating a workflow."""
        mock_resp = mock_response(
            json_data={
                "id": "wf-1",
                "name": "Password Reset",
                "active": True,
            }
        )

        n8n_client._client.request = AsyncMock(return_value=mock_resp)

        result = await n8n_client.activate_workflow("wf-1", True)

        assert result["active"] is True


# ---------------------------------------------------------------------------
# N8nApiClient — Execution Operations
# ---------------------------------------------------------------------------


class TestN8nClientExecutions:
    """Tests for N8nApiClient execution operations."""

    @pytest.mark.asyncio
    async def test_execute_workflow_success(self, n8n_client, mock_response):
        """Test executing a workflow returns execution result."""
        mock_resp = mock_response(
            json_data={
                "data": {
                    "executionId": "exec-456",
                    "status": "success",
                    "data": {"result": "password_reset_complete"},
                },
            }
        )

        n8n_client._client.request = AsyncMock(return_value=mock_resp)

        result = await n8n_client.execute_workflow(
            "wf-1", data={"user": "john", "action": "reset"}
        )

        assert result["data"]["executionId"] == "exec-456"
        assert result["data"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_execution_success(self, n8n_client, mock_response):
        """Test getting execution details."""
        mock_resp = mock_response(
            json_data={
                "id": "exec-456",
                "workflowId": "wf-1",
                "status": "success",
                "startedAt": "2026-02-24T10:00:00Z",
                "stoppedAt": "2026-02-24T10:00:05Z",
                "finished": True,
            }
        )

        n8n_client._client.request = AsyncMock(return_value=mock_resp)

        result = await n8n_client.get_execution("exec-456")

        assert result["id"] == "exec-456"
        assert result["status"] == "success"
        assert result["finished"] is True

    @pytest.mark.asyncio
    async def test_list_executions_with_filters(self, n8n_client, mock_response):
        """Test listing executions with filters."""
        mock_resp = mock_response(
            json_data={
                "data": [
                    {"id": "exec-1", "workflowId": "wf-1", "status": "error"},
                ],
                "nextCursor": None,
            }
        )

        n8n_client._client.request = AsyncMock(return_value=mock_resp)

        result = await n8n_client.list_executions(
            workflow_id="wf-1", status="error", limit=5
        )

        assert len(result["data"]) == 1
        assert result["data"][0]["status"] == "error"


# ---------------------------------------------------------------------------
# N8nApiClient — Error Handling
# ---------------------------------------------------------------------------


class TestN8nClientErrors:
    """Tests for N8nApiClient error handling."""

    @pytest.mark.asyncio
    async def test_authentication_error_401(self, n8n_client, mock_response):
        """Test 401 raises N8nAuthenticationError without retry."""
        mock_resp = mock_response(status_code=401, text="Unauthorized")

        n8n_client._client.request = AsyncMock(return_value=mock_resp)

        with pytest.raises(N8nAuthenticationError):
            await n8n_client.list_workflows()

        # Should NOT retry on auth errors
        assert n8n_client._client.request.call_count == 1

    @pytest.mark.asyncio
    async def test_authentication_error_403(self, n8n_client, mock_response):
        """Test 403 raises N8nAuthenticationError."""
        mock_resp = mock_response(status_code=403, text="Forbidden")

        n8n_client._client.request = AsyncMock(return_value=mock_resp)

        with pytest.raises(N8nAuthenticationError):
            await n8n_client.list_workflows()

    @pytest.mark.asyncio
    async def test_rate_limit_error_with_retry(self, n8n_client, mock_response):
        """Test 429 retries then raises N8nRateLimitError."""
        mock_resp_429 = mock_response(
            status_code=429,
            headers={"Retry-After": "0"},  # Instant retry for tests
        )

        n8n_client._client.request = AsyncMock(return_value=mock_resp_429)

        with pytest.raises(N8nRateLimitError):
            await n8n_client.list_workflows()

        # Should retry max_retries times
        assert n8n_client._client.request.call_count == n8n_client._config.max_retries

    @pytest.mark.asyncio
    async def test_connection_error_with_retry(self, n8n_client):
        """Test connection error retries then raises N8nConnectionError."""
        n8n_client._client.request = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with pytest.raises(N8nConnectionError, match="Failed to connect"):
            await n8n_client.list_workflows()

        assert n8n_client._client.request.call_count == n8n_client._config.max_retries

    @pytest.mark.asyncio
    async def test_timeout_error_with_retry(self, n8n_client):
        """Test timeout error retries then raises N8nConnectionError."""
        n8n_client._client.request = AsyncMock(
            side_effect=httpx.TimeoutException("Request timed out")
        )

        with pytest.raises(N8nConnectionError):
            await n8n_client.list_workflows()

    @pytest.mark.asyncio
    async def test_server_error_500(self, n8n_client, mock_response):
        """Test 500 server error raises N8nApiError."""
        mock_resp = mock_response(status_code=500, text="Internal Server Error")

        n8n_client._client.request = AsyncMock(return_value=mock_resp)

        with pytest.raises(N8nApiError, match="500"):
            await n8n_client.list_workflows()


# ---------------------------------------------------------------------------
# N8nApiClient — Health Check
# ---------------------------------------------------------------------------


class TestN8nClientHealth:
    """Tests for N8nApiClient health checking."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, n8n_client, mock_response):
        """Test successful health check."""
        mock_resp = mock_response(json_data={"data": []})

        n8n_client._client.request = AsyncMock(return_value=mock_resp)

        result = await n8n_client.health_check()

        assert result is True
        assert n8n_client.is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, n8n_client):
        """Test failed health check."""
        n8n_client._client.request = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        result = await n8n_client.health_check()

        assert result is False
        assert n8n_client.is_healthy is False


# ---------------------------------------------------------------------------
# N8nApiClient — Lifecycle
# ---------------------------------------------------------------------------


class TestN8nClientLifecycle:
    """Tests for N8nApiClient lifecycle management."""

    @pytest.mark.asyncio
    async def test_close_client(self, n8n_client):
        """Test closing the client."""
        n8n_client._client.aclose = AsyncMock()

        await n8n_client.close()

        n8n_client._client.aclose.assert_called_once()
        assert n8n_client.is_healthy is False

    @pytest.mark.asyncio
    async def test_context_manager(self, n8n_config):
        """Test async context manager."""
        async with N8nApiClient(n8n_config) as client:
            assert isinstance(client, N8nApiClient)
        # After exit, client should be closed

    def test_initial_state(self, n8n_client):
        """Test initial client state."""
        assert n8n_client.is_healthy is False
        assert n8n_client._config.base_url == "http://test-n8n:5678"


# ---------------------------------------------------------------------------
# Enum Tests
# ---------------------------------------------------------------------------


class TestEnums:
    """Tests for n8n enum types."""

    def test_workflow_status_values(self):
        """Test WorkflowStatus enum values."""
        assert WorkflowStatus.ACTIVE == "active"
        assert WorkflowStatus.INACTIVE == "inactive"

    def test_execution_status_values(self):
        """Test ExecutionStatus enum values."""
        assert ExecutionStatus.SUCCESS == "success"
        assert ExecutionStatus.ERROR == "error"
        assert ExecutionStatus.RUNNING == "running"
        assert ExecutionStatus.WAITING == "waiting"
        assert ExecutionStatus.NEW == "new"
