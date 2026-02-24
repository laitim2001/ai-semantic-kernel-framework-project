"""Tests for N8nMCPServer.

Sprint 124: n8n Integration — Mode 1 + Mode 2

Tests cover:
    - Server initialization and tool registration
    - Tool schema listing
    - Direct tool calls via server
    - Server metadata
    - Health check delegation
    - Server lifecycle
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.mcp.servers.n8n.client import N8nApiClient, N8nConfig
from src.integrations.mcp.servers.n8n.server import N8nMCPServer, create_server_from_env
from src.integrations.mcp.servers.n8n.tools.workflow import WorkflowTools
from src.integrations.mcp.servers.n8n.tools.execution import ExecutionTools


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def n8n_config():
    """Create a test N8nConfig."""
    return N8nConfig(
        base_url="http://test-n8n:5678",
        api_key="test-api-key",
        timeout=10,
        max_retries=1,
    )


@pytest.fixture
def n8n_server(n8n_config):
    """Create a test N8nMCPServer."""
    return N8nMCPServer(n8n_config)


# ---------------------------------------------------------------------------
# Initialization Tests
# ---------------------------------------------------------------------------


class TestN8nServerInit:
    """Tests for N8nMCPServer initialization."""

    def test_server_metadata(self, n8n_server):
        """Test server metadata constants."""
        assert n8n_server.SERVER_NAME == "n8n-mcp"
        assert n8n_server.SERVER_VERSION == "1.0.0"
        assert "n8n" in n8n_server.SERVER_DESCRIPTION.lower()

    def test_server_registers_6_tools(self, n8n_server):
        """Test that exactly 6 tools are registered."""
        tools = n8n_server.get_tools()
        assert len(tools) == 6

    def test_server_tool_names(self, n8n_server):
        """Test registered tool names."""
        names = n8n_server.get_tool_names()
        expected = [
            "n8n_list_workflows",
            "n8n_get_workflow",
            "n8n_activate_workflow",
            "n8n_execute_workflow",
            "n8n_get_execution",
            "n8n_list_executions",
        ]
        assert sorted(names) == sorted(expected)

    def test_server_has_client(self, n8n_server):
        """Test server has an N8nApiClient."""
        assert isinstance(n8n_server._client, N8nApiClient)

    def test_server_has_tool_instances(self, n8n_server):
        """Test server has workflow and execution tool instances."""
        assert isinstance(n8n_server._workflow_tools, WorkflowTools)
        assert isinstance(n8n_server._execution_tools, ExecutionTools)


# ---------------------------------------------------------------------------
# Tool Schema Tests
# ---------------------------------------------------------------------------


class TestN8nServerToolSchemas:
    """Tests for MCP tool schema definitions."""

    def test_workflow_tools_have_descriptions(self, n8n_server):
        """Test all workflow tools have descriptions."""
        tools = n8n_server.get_tools()
        workflow_tools = [t for t in tools if "workflow" in t.name.lower()]

        for tool in workflow_tools:
            assert tool.description, f"Tool {tool.name} missing description"
            assert len(tool.description) > 20

    def test_execution_tools_have_descriptions(self, n8n_server):
        """Test all execution tools have descriptions."""
        tools = n8n_server.get_tools()
        exec_tools = [t for t in tools if "execution" in t.name.lower() or "execute" in t.name.lower()]

        for tool in exec_tools:
            assert tool.description, f"Tool {tool.name} missing description"

    def test_execute_workflow_has_required_params(self, n8n_server):
        """Test execute_workflow tool has workflow_id as required param."""
        tools = n8n_server.get_tools()
        execute_tool = next(t for t in tools if t.name == "n8n_execute_workflow")

        param_names = [p.name for p in execute_tool.parameters]
        assert "workflow_id" in param_names

        wf_param = next(p for p in execute_tool.parameters if p.name == "workflow_id")
        assert wf_param.required is True

    def test_list_workflows_has_optional_filters(self, n8n_server):
        """Test list_workflows has optional filter params."""
        tools = n8n_server.get_tools()
        list_tool = next(t for t in tools if t.name == "n8n_list_workflows")

        for param in list_tool.parameters:
            assert param.required is False


# ---------------------------------------------------------------------------
# Health Check Tests
# ---------------------------------------------------------------------------


class TestN8nServerHealth:
    """Tests for N8nMCPServer health checking."""

    @pytest.mark.asyncio
    async def test_health_check_delegates_to_client(self, n8n_server):
        """Test health_check delegates to N8nApiClient."""
        n8n_server._client.health_check = AsyncMock(return_value=True)

        result = await n8n_server.health_check()

        assert result is True
        n8n_server._client.health_check.assert_called_once()

    def test_is_healthy_delegates_to_client(self, n8n_server):
        """Test is_healthy property delegates to client."""
        n8n_server._client._healthy = True
        assert n8n_server.is_healthy is True

        n8n_server._client._healthy = False
        assert n8n_server.is_healthy is False


# ---------------------------------------------------------------------------
# Lifecycle Tests
# ---------------------------------------------------------------------------


class TestN8nServerLifecycle:
    """Tests for N8nMCPServer lifecycle management."""

    @pytest.mark.asyncio
    async def test_cleanup_closes_client(self, n8n_server):
        """Test cleanup closes the API client."""
        n8n_server._client.close = AsyncMock()

        await n8n_server.cleanup()

        n8n_server._client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_context_manager(self, n8n_config):
        """Test async context manager."""
        server = N8nMCPServer(n8n_config)
        server._client.close = AsyncMock()

        async with server as s:
            assert isinstance(s, N8nMCPServer)

        server._client.close.assert_called_once()

    def test_stop_sets_running_false(self, n8n_server):
        """Test stop method."""
        n8n_server._running = True
        n8n_server.stop()
        assert n8n_server._running is False


# ---------------------------------------------------------------------------
# Factory Tests
# ---------------------------------------------------------------------------


class TestN8nServerFactory:
    """Tests for server factory functions."""

    def test_create_server_from_env_success(self, monkeypatch):
        """Test creating server from environment variables."""
        monkeypatch.setenv("N8N_BASE_URL", "http://prod:5678")
        monkeypatch.setenv("N8N_API_KEY", "prod-key")

        server = create_server_from_env()

        assert isinstance(server, N8nMCPServer)
        assert server._config.base_url == "http://prod:5678"

    def test_create_server_from_env_missing_key(self, monkeypatch):
        """Test factory raises without API key."""
        monkeypatch.delenv("N8N_API_KEY", raising=False)

        with pytest.raises(ValueError, match="N8N_API_KEY"):
            create_server_from_env()
