"""Tests for D365MCPServer — Sprint 129, Story 129-3.

Tests cover:
    - Server initialization (name, version, tool registration)
    - Tool count and exact tool name verification
    - Tool call dispatch for 4 representative tools (query + crud)
    - Unknown tool error handling
    - Health check delegation to client
    - is_healthy property reflection

Total: 9 tests across 3 test classes.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.mcp.servers.d365.client import D365ApiClient, D365Config
from src.integrations.mcp.servers.d365.server import D365MCPServer
from src.integrations.mcp.core.types import ToolResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def d365_config():
    """Create a test D365Config."""
    return D365Config(
        d365_url="https://test.crm.dynamics.com",
        tenant_id="tenant-123",
        client_id="client-123",
        client_secret="secret-123",
    )


@pytest.fixture
def d365_server(d365_config):
    """Create a test D365MCPServer."""
    return D365MCPServer(d365_config)


@pytest.fixture
def mock_client():
    """Create a mock D365ApiClient with all async methods pre-configured."""
    client = MagicMock(spec=D365ApiClient)
    client.query_entities = AsyncMock(return_value={
        "value": [{"accountid": "acc-1", "name": "Contoso"}],
    })
    client.get_record = AsyncMock(return_value={
        "accountid": "acc-1",
        "name": "Contoso",
        "telephone1": "02-1234-5678",
    })
    client.create_record = AsyncMock(return_value={
        "accountid": "acc-new",
        "name": "New Corp",
    })
    client.update_record = AsyncMock(return_value={
        "accountid": "acc-1",
        "name": "Updated Corp",
    })
    client.list_entity_types = AsyncMock(return_value=[
        {
            "LogicalName": "account",
            "DisplayName": {
                "LocalizedLabels": [{"Label": "Account"}],
            },
            "EntitySetName": "accounts",
        },
    ])
    client.get_entity_metadata = AsyncMock(return_value={
        "LogicalName": "account",
        "PrimaryIdAttribute": "accountid",
    })
    client.health_check = AsyncMock(return_value=True)
    client.is_healthy = True
    return client


def _make_server_with_mock_client(d365_config, mock_client):
    """Create a D365MCPServer and replace its internal client with the mock."""
    server = D365MCPServer(d365_config)
    # Replace client on server and both tool instances
    server._client = mock_client
    server._query_tools._client = mock_client
    server._crud_tools._client = mock_client
    return server


# ---------------------------------------------------------------------------
# 1. TestD365MCPServerInit — Server initialization (3 tests)
# ---------------------------------------------------------------------------


class TestD365MCPServerInit:
    """Tests for D365MCPServer initialization and metadata."""

    def test_server_init(self, d365_server):
        """Test server has correct SERVER_NAME and SERVER_VERSION constants."""
        assert d365_server.SERVER_NAME == "d365-mcp"
        assert d365_server.SERVER_VERSION == "1.0.0"
        assert isinstance(d365_server._client, D365ApiClient)

    def test_server_tools_registered(self, d365_server):
        """Test exactly 6 tools are registered (4 query + 2 crud)."""
        tools = d365_server.get_tools()
        assert len(tools) == 6

    def test_server_tool_names(self, d365_server):
        """Test the exact set of registered tool names matches expected tools."""
        names = set(d365_server.get_tool_names())
        expected = {
            "d365_query_entities",
            "d365_get_record",
            "d365_list_entity_types",
            "d365_get_entity_metadata",
            "d365_create_record",
            "d365_update_record",
        }
        assert names == expected


# ---------------------------------------------------------------------------
# 2. TestD365MCPServerToolCalls — Tool dispatch (4 tests)
# ---------------------------------------------------------------------------


class TestD365MCPServerToolCalls:
    """Tests for calling tools through D365MCPServer.call_tool()."""

    @pytest.mark.asyncio
    async def test_call_query_entities(self, d365_config, mock_client):
        """Test calling d365_query_entities returns successful ToolResult."""
        server = _make_server_with_mock_client(d365_config, mock_client)

        result = await server.call_tool(
            "d365_query_entities", {"entity_name": "account", "filter": "statecode eq 0"}
        )

        assert result.success is True
        assert result.content is not None
        mock_client.query_entities.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_get_record(self, d365_config, mock_client):
        """Test calling d365_get_record with entity_name and record_id."""
        server = _make_server_with_mock_client(d365_config, mock_client)

        result = await server.call_tool(
            "d365_get_record", {"entity_name": "account", "record_id": "acc-1"}
        )

        assert result.success is True
        assert result.content is not None
        mock_client.get_record.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_create_record(self, d365_config, mock_client):
        """Test calling d365_create_record with entity_name and data."""
        server = _make_server_with_mock_client(d365_config, mock_client)

        result = await server.call_tool(
            "d365_create_record",
            {"entity_name": "account", "data": {"name": "New Corp"}},
        )

        assert result.success is True
        assert result.content is not None
        mock_client.create_record.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self, d365_config, mock_client):
        """Test calling a non-existent tool returns an error indication.

        Note: The MCP protocol handler returns tool-not-found as a result with
        isError=True (not as a JSON-RPC error). The server's call_tool wraps this
        as ToolResult(success=True, content={isError: True, ...}).
        """
        server = _make_server_with_mock_client(d365_config, mock_client)

        result = await server.call_tool("d365_nonexistent_tool")

        # The protocol returns isError inside the result content
        assert result.content is not None
        assert result.content.get("isError") is True
        content_text = result.content["content"][0]["text"]
        assert "not found" in content_text.lower() or "d365_nonexistent_tool" in content_text


# ---------------------------------------------------------------------------
# 3. TestD365MCPServerHealth — Health check (2 tests)
# ---------------------------------------------------------------------------


class TestD365MCPServerHealth:
    """Tests for D365MCPServer health check and is_healthy property."""

    @pytest.mark.asyncio
    async def test_health_check_delegates(self, d365_config, mock_client):
        """Test health_check delegates to the underlying D365ApiClient."""
        server = _make_server_with_mock_client(d365_config, mock_client)

        result = await server.health_check()

        assert result is True
        mock_client.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_healthy_reflects_client(self, d365_config, mock_client):
        """Test is_healthy property reflects the client's is_healthy status."""
        server = _make_server_with_mock_client(d365_config, mock_client)

        assert server.is_healthy is True

        # Simulate unhealthy client
        mock_client.is_healthy = False
        assert server.is_healthy is False
