"""Unit tests for MCP Manager.

Sprint 50: S50-2 - MCP Manager 與工具發現 (8 pts)
Tests for MCPManager class.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

import pytest

from src.integrations.claude_sdk.mcp.base import MCPServer
from src.integrations.claude_sdk.mcp.exceptions import (
    MCPDisconnectedError,
    MCPToolNotFoundError,
)
from src.integrations.claude_sdk.mcp.manager import (
    HealthCheckResult,
    MCPManager,
    ServerInfo,
    create_manager,
)
from src.integrations.claude_sdk.mcp.types import (
    MCPServerState,
    MCPToolDefinition,
    MCPToolResult,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_server():
    """Create a mock MCP server."""
    server = MagicMock(spec=MCPServer)
    server.name = "test-server"
    server.is_connected = False
    server.state = MCPServerState.DISCONNECTED

    async def mock_connect():
        server.is_connected = True
        server.state = MCPServerState.CONNECTED

    async def mock_disconnect():
        server.is_connected = False
        server.state = MCPServerState.DISCONNECTED

    server.connect = AsyncMock(side_effect=mock_connect)
    server.disconnect = AsyncMock(side_effect=mock_disconnect)
    server.list_tools = AsyncMock(return_value=[
        MCPToolDefinition(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object"},
            server_name="test-server",
        ),
    ])
    server.execute_tool = AsyncMock(return_value=MCPToolResult(
        success=True,
        content="Tool executed",
        tool_name="test_tool",
    ))

    return server


@pytest.fixture
def mock_server_2():
    """Create a second mock MCP server."""
    server = MagicMock(spec=MCPServer)
    server.name = "server-2"
    server.is_connected = False
    server.state = MCPServerState.DISCONNECTED

    async def mock_connect():
        server.is_connected = True
        server.state = MCPServerState.CONNECTED

    async def mock_disconnect():
        server.is_connected = False
        server.state = MCPServerState.DISCONNECTED

    server.connect = AsyncMock(side_effect=mock_connect)
    server.disconnect = AsyncMock(side_effect=mock_disconnect)
    server.list_tools = AsyncMock(return_value=[
        MCPToolDefinition(
            name="another_tool",
            description="Another tool",
            input_schema={"type": "object"},
            server_name="server-2",
        ),
        MCPToolDefinition(
            name="db_query",
            description="Query database",
            input_schema={"type": "object", "properties": {"sql": {"type": "string"}}},
            server_name="server-2",
        ),
    ])
    server.execute_tool = AsyncMock(return_value=MCPToolResult(
        success=True,
        content="Tool executed",
    ))

    return server


@pytest.fixture
def manager():
    """Create an MCPManager instance."""
    return MCPManager()


# ============================================================================
# MCPManager Initialization Tests
# ============================================================================


class TestMCPManagerInit:
    """Tests for MCPManager initialization."""

    def test_default_init(self):
        """Test default initialization."""
        manager = MCPManager()

        assert manager.server_count == 0
        assert manager.connected_count == 0
        assert manager.tool_count == 0

    def test_custom_init(self):
        """Test custom initialization."""
        manager = MCPManager(
            auto_discover=False,
            connection_timeout=60.0,
        )

        assert manager._auto_discover is False
        assert manager._connection_timeout == 60.0


# ============================================================================
# MCPManager Add/Remove Server Tests
# ============================================================================


class TestMCPManagerServerManagement:
    """Tests for server management."""

    def test_add_server(self, manager, mock_server):
        """Test adding a server."""
        manager.add_server(mock_server)

        assert manager.server_count == 1
        assert "test-server" in manager.servers
        assert manager.get_server("test-server") is mock_server

    def test_add_duplicate_server_raises(self, manager, mock_server):
        """Test adding duplicate server raises error."""
        manager.add_server(mock_server)

        with pytest.raises(ValueError, match="already exists"):
            manager.add_server(mock_server)

    def test_remove_server(self, manager, mock_server):
        """Test removing a server."""
        manager.add_server(mock_server)
        result = manager.remove_server("test-server")

        assert result is True
        assert manager.server_count == 0
        assert manager.get_server("test-server") is None

    def test_remove_nonexistent_server(self, manager):
        """Test removing non-existent server."""
        result = manager.remove_server("nonexistent")

        assert result is False

    def test_add_multiple_servers(self, manager, mock_server, mock_server_2):
        """Test adding multiple servers."""
        manager.add_server(mock_server)
        manager.add_server(mock_server_2)

        assert manager.server_count == 2
        assert "test-server" in manager.servers
        assert "server-2" in manager.servers


# ============================================================================
# MCPManager Connection Tests
# ============================================================================


class TestMCPManagerConnection:
    """Tests for server connection."""

    @pytest.mark.asyncio
    async def test_connect_server(self, manager, mock_server):
        """Test connecting a single server."""
        manager.add_server(mock_server)
        result = await manager.connect_server("test-server")

        assert result is True
        assert mock_server.connect.called
        assert mock_server.is_connected

    @pytest.mark.asyncio
    async def test_connect_nonexistent_server(self, manager):
        """Test connecting non-existent server."""
        result = await manager.connect_server("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_connect_all(self, manager, mock_server, mock_server_2):
        """Test connecting all servers."""
        manager.add_server(mock_server)
        manager.add_server(mock_server_2)

        results = await manager.connect_all()

        assert results["test-server"] is True
        assert results["server-2"] is True
        assert manager.connected_count == 2

    @pytest.mark.asyncio
    async def test_connect_all_partial_failure(self, manager, mock_server, mock_server_2):
        """Test partial connection failure."""
        mock_server_2.connect = AsyncMock(side_effect=Exception("Connection failed"))

        manager.add_server(mock_server)
        manager.add_server(mock_server_2)

        results = await manager.connect_all()

        assert results["test-server"] is True
        assert results["server-2"] is False

    @pytest.mark.asyncio
    async def test_disconnect_server(self, manager, mock_server):
        """Test disconnecting a server."""
        manager.add_server(mock_server)
        await manager.connect_server("test-server")

        result = await manager.disconnect_server("test-server")

        assert result is True
        assert mock_server.disconnect.called

    @pytest.mark.asyncio
    async def test_disconnect_all(self, manager, mock_server, mock_server_2):
        """Test disconnecting all servers."""
        manager.add_server(mock_server)
        manager.add_server(mock_server_2)
        await manager.connect_all()

        await manager.disconnect_all()

        assert mock_server.disconnect.called
        assert mock_server_2.disconnect.called


# ============================================================================
# MCPManager Tool Discovery Tests
# ============================================================================


class TestMCPManagerToolDiscovery:
    """Tests for tool discovery."""

    @pytest.mark.asyncio
    async def test_discover_tools(self, manager, mock_server):
        """Test discovering tools from a server."""
        manager.add_server(mock_server)
        await manager.connect_server("test-server")

        tools = await manager.discover_tools()

        assert len(tools) == 1
        assert tools[0].name == "test_tool"
        assert manager.tool_count == 1

    @pytest.mark.asyncio
    async def test_discover_tools_multiple_servers(
        self, manager, mock_server, mock_server_2
    ):
        """Test discovering tools from multiple servers."""
        manager.add_server(mock_server)
        manager.add_server(mock_server_2)
        await manager.connect_all()

        tools = await manager.discover_tools()

        assert len(tools) == 3  # 1 + 2 tools
        assert manager.tool_count == 3

    @pytest.mark.asyncio
    async def test_discover_tools_skips_disconnected(
        self, manager, mock_server, mock_server_2
    ):
        """Test that disconnected servers are skipped."""
        manager.add_server(mock_server)
        manager.add_server(mock_server_2)
        await manager.connect_server("test-server")  # Only connect first

        tools = await manager.discover_tools()

        assert len(tools) == 1  # Only from connected server

    def test_find_tool_server(self, manager, mock_server):
        """Test finding tool server."""
        manager.add_server(mock_server)
        manager._tool_to_server["test_tool"] = "test-server"

        result = manager.find_tool_server("test_tool")

        assert result == "test-server"

    def test_find_tool_server_not_found(self, manager):
        """Test finding non-existent tool server."""
        result = manager.find_tool_server("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_tool_by_qualified_name(self, manager, mock_server):
        """Test getting tool by qualified name."""
        manager.add_server(mock_server)
        await manager.connect_server("test-server")
        await manager.discover_tools()

        tool = manager.get_tool("test-server:test_tool")

        assert tool is not None
        assert tool.name == "test_tool"

    @pytest.mark.asyncio
    async def test_get_tool_by_name(self, manager, mock_server):
        """Test getting tool by simple name."""
        manager.add_server(mock_server)
        await manager.connect_server("test-server")
        await manager.discover_tools()

        tool = manager.get_tool("test_tool")

        assert tool is not None
        assert tool.name == "test_tool"


# ============================================================================
# MCPManager Tool Execution Tests
# ============================================================================


class TestMCPManagerToolExecution:
    """Tests for tool execution."""

    @pytest.mark.asyncio
    async def test_execute_tool_by_ref(self, manager, mock_server):
        """Test executing tool by reference."""
        manager.add_server(mock_server)
        await manager.connect_server("test-server")
        await manager.discover_tools()

        result = await manager.execute_tool(
            "test-server:test_tool",
            {"arg": "value"},
        )

        assert result.success is True
        mock_server.execute_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_tool_by_name(self, manager, mock_server):
        """Test executing tool by name."""
        manager.add_server(mock_server)
        await manager.connect_server("test-server")
        await manager.discover_tools()

        result = await manager.execute_tool(
            "test_tool",
            {"arg": "value"},
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, manager, mock_server):
        """Test executing non-existent tool."""
        manager.add_server(mock_server)
        await manager.connect_server("test-server")
        await manager.discover_tools()

        with pytest.raises(MCPToolNotFoundError):
            await manager.execute_tool("nonexistent_tool", {})

    @pytest.mark.asyncio
    async def test_execute_tool_server_disconnected(self, manager, mock_server):
        """Test executing tool on disconnected server."""
        manager.add_server(mock_server)
        await manager.connect_server("test-server")
        await manager.discover_tools()
        await manager.disconnect_server("test-server")

        with pytest.raises(MCPDisconnectedError):
            await manager.execute_tool("test-server:test_tool", {})


# ============================================================================
# MCPManager Health Check Tests
# ============================================================================


class TestMCPManagerHealthCheck:
    """Tests for health check."""

    @pytest.mark.asyncio
    async def test_health_check(self, manager, mock_server):
        """Test health check."""
        manager.add_server(mock_server)
        await manager.connect_server("test-server")

        results = await manager.health_check()

        assert "test-server" in results
        assert results["test-server"].healthy is True
        assert results["test-server"].latency_ms is not None

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self, manager, mock_server):
        """Test health check on disconnected server."""
        manager.add_server(mock_server)

        results = await manager.health_check()

        assert results["test-server"].healthy is False
        assert results["test-server"].error == "Not connected"

    @pytest.mark.asyncio
    async def test_health_check_failure(self, manager, mock_server):
        """Test health check with tool list failure."""
        manager.add_server(mock_server)
        await manager.connect_server("test-server")
        mock_server.list_tools = AsyncMock(side_effect=Exception("Health check failed"))

        results = await manager.health_check()

        assert results["test-server"].healthy is False
        assert "Health check failed" in results["test-server"].error

    @pytest.mark.asyncio
    async def test_reconnect_unhealthy(self, manager, mock_server):
        """Test reconnecting unhealthy servers."""
        manager.add_server(mock_server)
        # Server is disconnected (unhealthy)

        results = await manager.reconnect_unhealthy()

        assert results["test-server"] is True


# ============================================================================
# MCPManager List Servers Tests
# ============================================================================


class TestMCPManagerListServers:
    """Tests for listing servers."""

    @pytest.mark.asyncio
    async def test_list_servers(self, manager, mock_server, mock_server_2):
        """Test listing servers."""
        manager.add_server(mock_server)
        manager.add_server(mock_server_2)
        await manager.connect_server("test-server")

        servers = manager.list_servers()

        assert len(servers) == 2
        assert any(s.name == "test-server" and s.connected for s in servers)
        assert any(s.name == "server-2" and not s.connected for s in servers)


# ============================================================================
# MCPManager Context Manager Tests
# ============================================================================


class TestMCPManagerContextManager:
    """Tests for context manager."""

    @pytest.mark.asyncio
    async def test_context_manager(self, manager, mock_server):
        """Test context manager."""
        manager.add_server(mock_server)

        async with manager as m:
            assert m.connected_count == 1
            assert m.tool_count == 1

        assert mock_server.disconnect.called

    @pytest.mark.asyncio
    async def test_context_manager_no_auto_discover(self, mock_server):
        """Test context manager without auto discover."""
        manager = MCPManager(auto_discover=False)
        manager.add_server(mock_server)

        async with manager as m:
            assert m.connected_count == 1
            assert m.tool_count == 0  # No auto-discover


# ============================================================================
# Factory Function Tests
# ============================================================================


class TestCreateManager:
    """Tests for create_manager factory function."""

    def test_create_manager_default(self):
        """Test creating manager with defaults."""
        manager = create_manager()

        assert isinstance(manager, MCPManager)
        assert manager._auto_discover is True
        assert manager._connection_timeout == 30.0

    def test_create_manager_custom(self):
        """Test creating manager with custom settings."""
        manager = create_manager(
            auto_discover=False,
            connection_timeout=60.0,
        )

        assert manager._auto_discover is False
        assert manager._connection_timeout == 60.0
