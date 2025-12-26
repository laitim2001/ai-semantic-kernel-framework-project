"""Unit tests for MCP servers.

Sprint 50: S50-1 - MCP Server 基礎 (10 pts)
Tests for MCPServer, MCPStdioServer, and MCPHTTPServer.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.claude_sdk.mcp.base import MCPServer
from src.integrations.claude_sdk.mcp.exceptions import (
    MCPConnectionError,
    MCPDisconnectedError,
    MCPTimeoutError,
    MCPToolNotFoundError,
)
from src.integrations.claude_sdk.mcp.http import MCPHTTPServer, create_http_server
from src.integrations.claude_sdk.mcp.stdio import MCPStdioServer, create_stdio_server
from src.integrations.claude_sdk.mcp.types import (
    MCPMessage,
    MCPServerConfig,
    MCPServerState,
    MCPToolDefinition,
    MCPTransportType,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def stdio_config():
    """Create stdio server config."""
    return MCPServerConfig(
        name="test-stdio",
        transport=MCPTransportType.STDIO,
        command="echo",
        args=["test"],
    )


@pytest.fixture
def http_config():
    """Create HTTP server config."""
    return MCPServerConfig(
        name="test-http",
        transport=MCPTransportType.HTTP,
        url="https://mcp.example.com/rpc",
        headers={"Authorization": "Bearer token"},
        timeout=10.0,
    )


# ============================================================================
# MCPServerConfig Factory Tests
# ============================================================================


class TestCreateStdioServer:
    """Tests for create_stdio_server factory function."""

    def test_create_basic(self):
        """Test creating basic stdio server."""
        server = create_stdio_server(
            name="test",
            command="node",
        )

        assert isinstance(server, MCPStdioServer)
        assert server.name == "test"
        assert server.config.command == "node"

    def test_create_with_args(self):
        """Test creating with arguments."""
        server = create_stdio_server(
            name="test",
            command="npx",
            args=["-y", "@anthropic/mcp-filesystem"],
        )

        assert server.config.args == ["-y", "@anthropic/mcp-filesystem"]

    def test_create_with_env(self):
        """Test creating with environment."""
        server = create_stdio_server(
            name="test",
            command="node",
            env={"NODE_ENV": "production"},
        )

        assert server.config.env == {"NODE_ENV": "production"}

    def test_create_with_cwd(self):
        """Test creating with working directory."""
        server = create_stdio_server(
            name="test",
            command="node",
            cwd="/home/user/project",
        )

        assert server.config.cwd == "/home/user/project"


class TestCreateHTTPServer:
    """Tests for create_http_server factory function."""

    def test_create_basic(self):
        """Test creating basic HTTP server."""
        server = create_http_server(
            name="test",
            url="https://example.com/rpc",
        )

        assert isinstance(server, MCPHTTPServer)
        assert server.name == "test"
        assert server.config.url == "https://example.com/rpc"

    def test_create_with_headers(self):
        """Test creating with headers."""
        server = create_http_server(
            name="test",
            url="https://example.com/rpc",
            headers={"X-API-Key": "secret"},
        )

        assert server.config.headers == {"X-API-Key": "secret"}

    def test_create_with_timeout(self):
        """Test creating with custom timeout."""
        server = create_http_server(
            name="test",
            url="https://example.com/rpc",
            timeout=60.0,
        )

        assert server.config.timeout == 60.0


# ============================================================================
# MCPServer Base Tests
# ============================================================================


class TestMCPServerBase:
    """Tests for MCPServer base class functionality."""

    def test_initial_state(self, stdio_config):
        """Test initial server state."""
        server = MCPStdioServer(stdio_config)

        assert server.state == MCPServerState.DISCONNECTED
        assert server.is_connected is False
        assert server.tools == []
        assert server.name == "test-stdio"

    def test_get_tool_not_found(self, stdio_config):
        """Test getting non-existent tool."""
        server = MCPStdioServer(stdio_config)

        tool = server.get_tool("nonexistent")
        assert tool is None

    def test_has_tool_false(self, stdio_config):
        """Test has_tool returns False for non-existent tool."""
        server = MCPStdioServer(stdio_config)

        assert server.has_tool("nonexistent") is False

    def test_repr(self, stdio_config):
        """Test string representation."""
        server = MCPStdioServer(stdio_config)
        repr_str = repr(server)

        assert "MCPStdioServer" in repr_str
        assert "test-stdio" in repr_str
        assert "disconnected" in repr_str


# ============================================================================
# MCPStdioServer Tests
# ============================================================================


class TestMCPStdioServer:
    """Tests for MCPStdioServer."""

    def test_init(self, stdio_config):
        """Test initialization."""
        server = MCPStdioServer(stdio_config)

        assert server.config == stdio_config
        assert server._process is None
        assert server._read_task is None

    def test_pid_when_not_running(self, stdio_config):
        """Test PID is None when not running."""
        server = MCPStdioServer(stdio_config)

        assert server.pid is None

    @pytest.mark.asyncio
    async def test_connect_without_command(self):
        """Test connect fails without command."""
        config = MCPServerConfig(name="test")
        server = MCPStdioServer(config)

        with pytest.raises(MCPConnectionError, match="No command"):
            await server.connect()

    @pytest.mark.asyncio
    async def test_connect_command_not_found(self, stdio_config):
        """Test connect fails with invalid command."""
        stdio_config.command = "nonexistent_command_xyz"
        server = MCPStdioServer(stdio_config)

        with pytest.raises(MCPConnectionError, match="not found"):
            await server.connect()

    @pytest.mark.asyncio
    async def test_list_tools_when_disconnected(self, stdio_config):
        """Test list_tools fails when disconnected."""
        server = MCPStdioServer(stdio_config)

        with pytest.raises(MCPDisconnectedError):
            await server.list_tools()

    @pytest.mark.asyncio
    async def test_execute_tool_when_disconnected(self, stdio_config):
        """Test execute_tool fails when disconnected."""
        server = MCPStdioServer(stdio_config)

        with pytest.raises(MCPDisconnectedError):
            await server.execute_tool("test_tool", {"arg": "value"})

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self, stdio_config):
        """Test disconnect when already disconnected."""
        server = MCPStdioServer(stdio_config)

        # Should not raise
        await server.disconnect()
        assert server.state == MCPServerState.DISCONNECTED


class TestMCPStdioServerWithMock:
    """Tests for MCPStdioServer with mocked subprocess."""

    @pytest.mark.asyncio
    async def test_connect_success(self, stdio_config):
        """Test successful connection with mock process."""
        server = MCPStdioServer(stdio_config)

        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdout = MagicMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        mock_process.stderr = MagicMock()

        with patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=mock_process),
        ):
            # Mock the initialize and discover methods to avoid actual calls
            server._initialize = AsyncMock()
            server._discover_tools = AsyncMock()

            await server.connect()

            assert server.state == MCPServerState.CONNECTED
            assert server.pid == 12345

    @pytest.mark.asyncio
    async def test_disconnect_terminates_process(self, stdio_config):
        """Test disconnect terminates process."""
        server = MCPStdioServer(stdio_config)

        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()

        server._process = mock_process
        server._state = MCPServerState.CONNECTED
        server._read_task = asyncio.create_task(asyncio.sleep(100))

        await server.disconnect()

        assert server.state == MCPServerState.DISCONNECTED
        assert server._process is None
        mock_process.terminate.assert_called_once()


# ============================================================================
# MCPHTTPServer Tests
# ============================================================================


class TestMCPHTTPServer:
    """Tests for MCPHTTPServer."""

    def test_init(self, http_config):
        """Test initialization."""
        server = MCPHTTPServer(http_config)

        assert server.config == http_config
        assert server._session is None
        assert server.url == "https://mcp.example.com/rpc"

    @pytest.mark.asyncio
    async def test_connect_without_url(self):
        """Test connect fails without URL."""
        config = MCPServerConfig(
            name="test",
            transport=MCPTransportType.HTTP,
        )
        server = MCPHTTPServer(config)

        with pytest.raises(MCPConnectionError, match="No URL"):
            await server.connect()

    @pytest.mark.asyncio
    async def test_connect_without_aiohttp(self, http_config):
        """Test connect fails without aiohttp."""
        server = MCPHTTPServer(http_config)

        with patch(
            "src.integrations.claude_sdk.mcp.http.AIOHTTP_AVAILABLE",
            False,
        ):
            with pytest.raises(MCPConnectionError, match="aiohttp"):
                await server.connect()

    @pytest.mark.asyncio
    async def test_list_tools_when_disconnected(self, http_config):
        """Test list_tools fails when disconnected."""
        server = MCPHTTPServer(http_config)

        with pytest.raises(MCPDisconnectedError):
            await server.list_tools()

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self, http_config):
        """Test disconnect when already disconnected."""
        server = MCPHTTPServer(http_config)

        await server.disconnect()
        assert server.state == MCPServerState.DISCONNECTED


class TestMCPHTTPServerWithMock:
    """Tests for MCPHTTPServer with mocked HTTP client."""

    @pytest.mark.asyncio
    @patch("src.integrations.claude_sdk.mcp.http.AIOHTTP_AVAILABLE", True)
    async def test_connect_success(self, http_config):
        """Test successful HTTP connection."""
        server = MCPHTTPServer(http_config)

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200

        mock_get_context = MagicMock()
        mock_get_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_context.__aexit__ = AsyncMock(return_value=None)

        mock_session.get = MagicMock(return_value=mock_get_context)
        mock_session.close = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            # Mock initialize and discover
            server._initialize = AsyncMock()
            server._discover_tools = AsyncMock()

            await server.connect()

            assert server.state == MCPServerState.CONNECTED

    @pytest.mark.asyncio
    @patch("src.integrations.claude_sdk.mcp.http.AIOHTTP_AVAILABLE", True)
    async def test_send_request_success(self, http_config):
        """Test successful HTTP request."""
        server = MCPHTTPServer(http_config)

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"jsonrpc": "2.0", "result": {"tools": []}, "id": 1}
        )

        mock_post_context = MagicMock()
        mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_context.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_post_context)

        server._session = mock_session
        server._state = MCPServerState.CONNECTED

        result = await server.send_request("tools/list")

        assert result == {"tools": []}


# ============================================================================
# MCPServer Tool Operations Tests
# ============================================================================


class TestMCPServerToolOperations:
    """Tests for tool operations."""

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, stdio_config):
        """Test execute_tool fails for unknown tool."""
        server = MCPStdioServer(stdio_config)
        server._state = MCPServerState.CONNECTED

        with pytest.raises(MCPToolNotFoundError, match="unknown_tool"):
            await server.execute_tool("unknown_tool", {})

    @pytest.mark.asyncio
    async def test_execute_tool_timeout(self, stdio_config):
        """Test execute_tool timeout."""
        server = MCPStdioServer(stdio_config)
        server._state = MCPServerState.CONNECTED
        server._tools["slow_tool"] = MCPToolDefinition(
            name="slow_tool",
            description="Slow tool",
        )

        async def slow_execution(name, args):
            await asyncio.sleep(10)
            return "done"

        server._execute_tool = slow_execution

        with pytest.raises(MCPTimeoutError):
            await server.execute_tool("slow_tool", {}, timeout=0.1)

    def test_tools_property(self, stdio_config):
        """Test tools property returns list."""
        server = MCPStdioServer(stdio_config)
        server._tools = {
            "tool1": MCPToolDefinition(name="tool1", description="Tool 1"),
            "tool2": MCPToolDefinition(name="tool2", description="Tool 2"),
        }

        tools = server.tools
        assert len(tools) == 2
        assert all(isinstance(t, MCPToolDefinition) for t in tools)

    def test_get_tool_exists(self, stdio_config):
        """Test getting existing tool."""
        server = MCPStdioServer(stdio_config)
        tool_def = MCPToolDefinition(name="test_tool", description="Test")
        server._tools["test_tool"] = tool_def

        tool = server.get_tool("test_tool")
        assert tool == tool_def

    def test_has_tool_true(self, stdio_config):
        """Test has_tool returns True for existing tool."""
        server = MCPStdioServer(stdio_config)
        server._tools["test_tool"] = MCPToolDefinition(
            name="test_tool",
            description="Test",
        )

        assert server.has_tool("test_tool") is True


# ============================================================================
# MCPMessage Handling Tests
# ============================================================================


class TestMCPMessageHandling:
    """Tests for message handling."""

    def test_handle_response_with_pending_request(self, stdio_config):
        """Test handling response with pending request."""
        server = MCPStdioServer(stdio_config)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            future = loop.create_future()
            server._pending_requests[1] = future

            message = MCPMessage.response(result={"data": "value"}, id=1)
            server._handle_response(message)

            assert future.done()
            assert future.result() == message
        finally:
            loop.close()

    def test_handle_response_without_pending_request(self, stdio_config):
        """Test handling response without pending request."""
        server = MCPStdioServer(stdio_config)

        # Should not raise
        message = MCPMessage.response(result={"data": "value"}, id=999)
        server._handle_response(message)

    def test_handle_response_without_id(self, stdio_config):
        """Test handling response without ID."""
        server = MCPStdioServer(stdio_config)

        # Should not raise
        message = MCPMessage(result={"data": "value"})
        server._handle_response(message)

    def test_next_message_id(self, stdio_config):
        """Test message ID increments."""
        server = MCPStdioServer(stdio_config)

        id1 = server._next_message_id()
        id2 = server._next_message_id()
        id3 = server._next_message_id()

        assert id2 == id1 + 1
        assert id3 == id2 + 1


# ============================================================================
# Integration Tests
# ============================================================================


class TestMCPIntegration:
    """Integration tests for MCP module."""

    def test_import_all(self):
        """Test importing all components."""
        from src.integrations.claude_sdk.mcp import (
            MCPError,
            MCPHTTPServer,
            MCPMessage,
            MCPServer,
            MCPServerConfig,
            MCPServerState,
            MCPStdioServer,
            MCPToolDefinition,
            MCPToolResult,
            MCPTransportType,
            create_http_server,
            create_stdio_server,
        )

        # All imports should work
        assert MCPServer is not None
        assert MCPStdioServer is not None
        assert MCPHTTPServer is not None

    def test_create_servers_different_configs(self):
        """Test creating multiple servers with different configs."""
        stdio_server = create_stdio_server(
            name="local",
            command="node",
            args=["server.js"],
        )

        http_server = create_http_server(
            name="remote",
            url="https://api.example.com",
        )

        assert stdio_server.name != http_server.name
        assert stdio_server.config.transport == MCPTransportType.STDIO
        assert http_server.config.transport == MCPTransportType.HTTP
