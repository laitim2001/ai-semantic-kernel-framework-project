"""Unit tests for MCP types.

Sprint 50: S50-1 - MCP Server 基礎 (10 pts)
Tests for MCP type definitions.
"""

import pytest

from src.integrations.claude_sdk.mcp.types import (
    MCPErrorCode,
    MCPMessage,
    MCPServerConfig,
    MCPServerState,
    MCPToolDefinition,
    MCPToolResult,
    MCPTransportType,
)


# ============================================================================
# MCPServerState Tests
# ============================================================================


class TestMCPServerState:
    """Tests for MCPServerState enum."""

    def test_states_exist(self):
        """Test all states are defined."""
        assert MCPServerState.DISCONNECTED.value == "disconnected"
        assert MCPServerState.CONNECTING.value == "connecting"
        assert MCPServerState.CONNECTED.value == "connected"
        assert MCPServerState.ERROR.value == "error"


# ============================================================================
# MCPTransportType Tests
# ============================================================================


class TestMCPTransportType:
    """Tests for MCPTransportType enum."""

    def test_transports_exist(self):
        """Test all transports are defined."""
        assert MCPTransportType.STDIO.value == "stdio"
        assert MCPTransportType.HTTP.value == "http"
        assert MCPTransportType.WEBSOCKET.value == "websocket"


# ============================================================================
# MCPToolDefinition Tests
# ============================================================================


class TestMCPToolDefinition:
    """Tests for MCPToolDefinition dataclass."""

    def test_create_tool_definition(self):
        """Test creating tool definition."""
        tool = MCPToolDefinition(
            name="read_file",
            description="Read file content",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            server_name="filesystem",
        )

        assert tool.name == "read_file"
        assert tool.description == "Read file content"
        assert "path" in tool.input_schema["properties"]
        assert tool.server_name == "filesystem"

    def test_to_dict(self):
        """Test converting to dictionary."""
        tool = MCPToolDefinition(
            name="test_tool",
            description="Test description",
            input_schema={"type": "object"},
        )

        d = tool.to_dict()
        assert d["name"] == "test_tool"
        assert d["description"] == "Test description"
        assert d["input_schema"] == {"type": "object"}
        assert d["server_name"] is None

    def test_to_claude_format(self):
        """Test converting to Claude API format."""
        tool = MCPToolDefinition(
            name="my_tool",
            description="My tool",
            input_schema={"type": "object"},
            server_name="server1",  # Should not appear in Claude format
        )

        claude_format = tool.to_claude_format()
        assert claude_format["name"] == "my_tool"
        assert claude_format["description"] == "My tool"
        assert "server_name" not in claude_format


# ============================================================================
# MCPToolResult Tests
# ============================================================================


class TestMCPToolResult:
    """Tests for MCPToolResult dataclass."""

    def test_create_success_result(self):
        """Test creating success result."""
        result = MCPToolResult(
            success=True,
            content="File content here",
            tool_name="read_file",
            execution_time_ms=15.5,
        )

        assert result.success is True
        assert result.content == "File content here"
        assert result.error is None
        assert result.tool_name == "read_file"
        assert result.execution_time_ms == 15.5

    def test_create_error_result(self):
        """Test creating error result."""
        result = MCPToolResult(
            success=False,
            error="File not found",
            tool_name="read_file",
        )

        assert result.success is False
        assert result.error == "File not found"
        assert result.content is None

    def test_to_dict_success(self):
        """Test converting success result to dict."""
        result = MCPToolResult(
            success=True,
            content={"data": "value"},
            tool_name="my_tool",
            execution_time_ms=10.0,
        )

        d = result.to_dict()
        assert d["success"] is True
        assert d["content"] == {"data": "value"}
        assert d["tool_name"] == "my_tool"
        assert d["execution_time_ms"] == 10.0
        assert "error" not in d

    def test_to_dict_error(self):
        """Test converting error result to dict."""
        result = MCPToolResult(
            success=False,
            error="Something went wrong",
        )

        d = result.to_dict()
        assert d["success"] is False
        assert d["error"] == "Something went wrong"


# ============================================================================
# MCPServerConfig Tests
# ============================================================================


class TestMCPServerConfig:
    """Tests for MCPServerConfig dataclass."""

    def test_create_stdio_config(self):
        """Test creating stdio config."""
        config = MCPServerConfig(
            name="filesystem",
            transport=MCPTransportType.STDIO,
            command="npx",
            args=["-y", "@anthropic/mcp-filesystem"],
            env={"HOME": "/home/user"},
            cwd="/tmp",
        )

        assert config.name == "filesystem"
        assert config.transport == MCPTransportType.STDIO
        assert config.command == "npx"
        assert config.args == ["-y", "@anthropic/mcp-filesystem"]
        assert config.env == {"HOME": "/home/user"}
        assert config.cwd == "/tmp"

    def test_create_http_config(self):
        """Test creating HTTP config."""
        config = MCPServerConfig(
            name="remote",
            transport=MCPTransportType.HTTP,
            url="https://mcp.example.com/rpc",
            headers={"Authorization": "Bearer token"},
            timeout=60.0,
        )

        assert config.name == "remote"
        assert config.transport == MCPTransportType.HTTP
        assert config.url == "https://mcp.example.com/rpc"
        assert config.headers == {"Authorization": "Bearer token"}
        assert config.timeout == 60.0

    def test_default_values(self):
        """Test default config values."""
        config = MCPServerConfig(name="test")

        assert config.transport == MCPTransportType.STDIO
        assert config.args == []
        assert config.env == {}
        assert config.headers == {}
        assert config.timeout == 30.0
        assert config.enabled is True
        assert config.auto_connect is True
        assert config.retry_attempts == 3
        assert config.retry_delay == 1.0

    def test_validate_stdio_config(self):
        """Test validation for stdio config."""
        config = MCPServerConfig(
            name="test",
            transport=MCPTransportType.STDIO,
            command="npx",
        )
        config.validate()  # Should not raise

    def test_validate_stdio_missing_command(self):
        """Test validation fails without command."""
        config = MCPServerConfig(
            name="test",
            transport=MCPTransportType.STDIO,
        )
        with pytest.raises(ValueError, match="Command is required"):
            config.validate()

    def test_validate_http_config(self):
        """Test validation for HTTP config."""
        config = MCPServerConfig(
            name="test",
            transport=MCPTransportType.HTTP,
            url="https://example.com",
        )
        config.validate()  # Should not raise

    def test_validate_http_missing_url(self):
        """Test validation fails without URL."""
        config = MCPServerConfig(
            name="test",
            transport=MCPTransportType.HTTP,
        )
        with pytest.raises(ValueError, match="URL is required"):
            config.validate()

    def test_validate_missing_name(self):
        """Test validation fails without name."""
        config = MCPServerConfig(name="")
        with pytest.raises(ValueError, match="name is required"):
            config.validate()

    def test_to_dict(self):
        """Test converting config to dict."""
        config = MCPServerConfig(
            name="test",
            command="cmd",
            args=["arg1"],
        )

        d = config.to_dict()
        assert d["name"] == "test"
        assert d["transport"] == "stdio"
        assert d["command"] == "cmd"
        assert d["args"] == ["arg1"]

    def test_from_dict(self):
        """Test creating config from dict."""
        data = {
            "name": "test",
            "transport": "http",
            "url": "https://example.com",
            "headers": {"X-Key": "value"},
            "timeout": 45.0,
        }

        config = MCPServerConfig.from_dict(data)
        assert config.name == "test"
        assert config.transport == MCPTransportType.HTTP
        assert config.url == "https://example.com"
        assert config.headers == {"X-Key": "value"}
        assert config.timeout == 45.0


# ============================================================================
# MCPMessage Tests
# ============================================================================


class TestMCPMessage:
    """Tests for MCPMessage dataclass."""

    def test_create_request(self):
        """Test creating request message."""
        msg = MCPMessage.request(
            method="tools/list",
            params={"filter": "enabled"},
            id=1,
        )

        assert msg.jsonrpc == "2.0"
        assert msg.method == "tools/list"
        assert msg.params == {"filter": "enabled"}
        assert msg.id == 1
        assert msg.result is None
        assert msg.error is None

    def test_create_response(self):
        """Test creating response message."""
        msg = MCPMessage.response(
            result={"tools": []},
            id=1,
        )

        assert msg.jsonrpc == "2.0"
        assert msg.result == {"tools": []}
        assert msg.id == 1
        assert msg.method is None

    def test_create_error_response(self):
        """Test creating error response message."""
        msg = MCPMessage.error_response(
            code=-32601,
            message="Method not found",
            id=1,
            data={"method": "unknown"},
        )

        assert msg.error["code"] == -32601
        assert msg.error["message"] == "Method not found"
        assert msg.error["data"] == {"method": "unknown"}
        assert msg.id == 1

    def test_to_dict_request(self):
        """Test converting request to dict."""
        msg = MCPMessage.request(
            method="tools/call",
            params={"name": "read_file"},
            id=5,
        )

        d = msg.to_dict()
        assert d["jsonrpc"] == "2.0"
        assert d["method"] == "tools/call"
        assert d["params"] == {"name": "read_file"}
        assert d["id"] == 5
        assert "result" not in d
        assert "error" not in d

    def test_to_dict_response(self):
        """Test converting response to dict."""
        msg = MCPMessage.response(
            result="success",
            id=5,
        )

        d = msg.to_dict()
        assert d["result"] == "success"
        assert d["id"] == 5
        assert "method" not in d

    def test_from_dict(self):
        """Test creating message from dict."""
        data = {
            "jsonrpc": "2.0",
            "id": 10,
            "result": {"data": "value"},
        }

        msg = MCPMessage.from_dict(data)
        assert msg.jsonrpc == "2.0"
        assert msg.id == 10
        assert msg.result == {"data": "value"}


# ============================================================================
# MCPErrorCode Tests
# ============================================================================


class TestMCPErrorCode:
    """Tests for MCPErrorCode constants."""

    def test_standard_error_codes(self):
        """Test standard JSON-RPC error codes."""
        assert MCPErrorCode.PARSE_ERROR == -32700
        assert MCPErrorCode.INVALID_REQUEST == -32600
        assert MCPErrorCode.METHOD_NOT_FOUND == -32601
        assert MCPErrorCode.INVALID_PARAMS == -32602
        assert MCPErrorCode.INTERNAL_ERROR == -32603

    def test_mcp_specific_codes(self):
        """Test MCP-specific error codes."""
        assert MCPErrorCode.SERVER_NOT_CONNECTED == -32000
        assert MCPErrorCode.TOOL_NOT_FOUND == -32001
        assert MCPErrorCode.TOOL_EXECUTION_ERROR == -32002
        assert MCPErrorCode.TIMEOUT_ERROR == -32003
        assert MCPErrorCode.CONNECTION_ERROR == -32004
