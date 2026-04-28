"""Tests for MCP Protocol Handler.

Sprint 130: MCP Core module unit tests.

Tests MCPProtocol from src.integrations.mcp.core.protocol,
covering tool registration, request handling, permission checking,
and request/notification creation.
"""

import pytest

from src.integrations.mcp.core.protocol import MCPProtocol
from src.integrations.mcp.core.types import (
    MCPErrorCode,
    MCPRequest,
    ToolInputType,
    ToolParameter,
    ToolResult,
    ToolSchema,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def protocol():
    """Create a fresh MCPProtocol instance."""
    return MCPProtocol()


@pytest.fixture
def tool_schema():
    """Create a sample ToolSchema for testing."""
    return ToolSchema(
        name="test_tool",
        description="A test tool",
        parameters=[
            ToolParameter(
                name="arg1",
                type=ToolInputType.STRING,
                description="Test arg",
                required=True,
            ),
        ],
    )


def _make_tool_handler(
    success: bool = True,
    content: str = "test result",
    error: str = None,
):
    """Create an async tool handler that returns a predetermined ToolResult."""

    async def handler(**kwargs):
        return ToolResult(success=success, content=content, error=error)

    return handler


# ---------------------------------------------------------------------------
# Tests: Tool Registration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_tool(protocol, tool_schema):
    """Registering a tool should make it appear in registered_tools."""
    handler = _make_tool_handler()
    protocol.register_tool("test_tool", handler, tool_schema)

    assert "test_tool" in protocol.registered_tools
    assert len(protocol.registered_tools) == 1


@pytest.mark.asyncio
async def test_unregister_tool(protocol, tool_schema):
    """Unregistering a tool should remove it from registered_tools."""
    handler = _make_tool_handler()
    protocol.register_tool("test_tool", handler, tool_schema)
    assert "test_tool" in protocol.registered_tools

    result = protocol.unregister_tool("test_tool")

    assert result is True
    assert "test_tool" not in protocol.registered_tools
    assert len(protocol.registered_tools) == 0


@pytest.mark.asyncio
async def test_unregister_nonexistent(protocol):
    """Unregistering a tool that does not exist should return False."""
    result = protocol.unregister_tool("nonexistent_tool")

    assert result is False


@pytest.mark.asyncio
async def test_get_tool_schema(protocol, tool_schema):
    """get_tool_schema should return the schema for a registered tool."""
    handler = _make_tool_handler()
    protocol.register_tool("test_tool", handler, tool_schema)

    retrieved = protocol.get_tool_schema("test_tool")

    assert retrieved is not None
    assert retrieved.name == "test_tool"
    assert retrieved.description == "A test tool"
    assert len(retrieved.parameters) == 1
    assert retrieved.parameters[0].name == "arg1"


@pytest.mark.asyncio
async def test_list_tools(protocol, tool_schema):
    """list_tools should return all registered schemas."""
    handler = _make_tool_handler()
    protocol.register_tool("test_tool", handler, tool_schema)

    second_schema = ToolSchema(
        name="second_tool",
        description="Another tool",
        parameters=[],
    )
    protocol.register_tool("second_tool", handler, second_schema)

    schemas = protocol.list_tools()

    assert len(schemas) == 2
    names = {s.name for s in schemas}
    assert names == {"test_tool", "second_tool"}


# ---------------------------------------------------------------------------
# Tests: Request Handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_initialize(protocol):
    """Handle 'initialize' should set initialized=True and return server info."""
    request = MCPRequest(
        id=1,
        method="initialize",
        params={
            "protocolVersion": "2024-11-05",
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    )

    response = await protocol.handle_request(request)

    assert response.is_success
    assert response.id == 1
    assert protocol.is_initialized is True

    result = response.result
    assert result["protocolVersion"] == MCPProtocol.MCP_VERSION
    assert "capabilities" in result
    assert "tools" in result["capabilities"]
    assert "serverInfo" in result
    assert result["serverInfo"]["name"] == MCPProtocol.SERVER_NAME


@pytest.mark.asyncio
async def test_handle_tools_list(protocol, tool_schema):
    """Handle 'tools/list' should return all registered tools in MCP format."""
    handler = _make_tool_handler()
    protocol.register_tool("test_tool", handler, tool_schema)

    request = MCPRequest(id=2, method="tools/list", params={})
    response = await protocol.handle_request(request)

    assert response.is_success
    assert response.id == 2

    tools = response.result["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == "test_tool"
    assert tools[0]["description"] == "A test tool"
    assert "inputSchema" in tools[0]


@pytest.mark.asyncio
async def test_handle_tools_call_success(protocol, tool_schema):
    """Handle 'tools/call' for a registered tool should return the tool result."""
    handler = _make_tool_handler(success=True, content="hello world")
    protocol.register_tool("test_tool", handler, tool_schema)

    request = MCPRequest(
        id=3,
        method="tools/call",
        params={"name": "test_tool", "arguments": {"arg1": "value1"}},
    )
    response = await protocol.handle_request(request)

    assert response.is_success
    result = response.result
    assert "content" in result
    assert result["content"][0]["type"] == "text"
    assert result["content"][0]["text"] == "hello world"
    assert result.get("isError") is None


@pytest.mark.asyncio
async def test_handle_tools_call_not_found(protocol):
    """Handle 'tools/call' for an unknown tool should return isError=True."""
    request = MCPRequest(
        id=4,
        method="tools/call",
        params={"name": "nonexistent_tool", "arguments": {}},
    )
    response = await protocol.handle_request(request)

    assert response.is_success  # JSON-RPC response itself is OK
    result = response.result
    assert result["isError"] is True
    assert "Tool not found" in result["content"][0]["text"]


@pytest.mark.asyncio
async def test_handle_tools_call_missing_name(protocol):
    """Handle 'tools/call' without a tool name should return isError=True."""
    request = MCPRequest(
        id=5,
        method="tools/call",
        params={"arguments": {}},
    )
    response = await protocol.handle_request(request)

    assert response.is_success
    result = response.result
    assert result["isError"] is True
    assert "required" in result["content"][0]["text"].lower()


@pytest.mark.asyncio
async def test_handle_method_not_found(protocol):
    """Handle an unrecognized method should return METHOD_NOT_FOUND error."""
    request = MCPRequest(
        id=6,
        method="unknown/method",
        params={},
    )
    response = await protocol.handle_request(request)

    assert response.is_success is False
    assert response.error_code == MCPErrorCode.METHOD_NOT_FOUND
    assert "Method not found" in response.error_message


@pytest.mark.asyncio
async def test_handle_ping(protocol):
    """Handle 'ping' should return an empty dict result."""
    request = MCPRequest(id=7, method="ping", params={})
    response = await protocol.handle_request(request)

    assert response.is_success
    assert response.result == {}


# ---------------------------------------------------------------------------
# Tests: Request / Notification Creation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_request_and_notification(protocol):
    """create_request should produce incrementing IDs; create_notification empty ID."""
    req1 = protocol.create_request("tools/list", {})
    req2 = protocol.create_request("tools/call", {"name": "t"})

    assert req1.id == 1
    assert req2.id == 2
    assert req1.method == "tools/list"
    assert req2.method == "tools/call"

    notification = protocol.create_notification("initialized", {})
    assert notification.id == ""
    assert notification.method == "initialized"


# ---------------------------------------------------------------------------
# Tests: Permission Checker
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_permission_checker_blocks(protocol, tool_schema):
    """When a permission checker raises PermissionError, tools/call should reflect it."""

    async def handler(**kwargs):
        return ToolResult(success=True, content="should not reach")

    protocol.register_tool("test_tool", handler, tool_schema)

    class StubPermissionChecker:
        """A stub permission checker that always denies access."""

        def check_tool_permission(self, server_name, tool_name, required_level, context):
            raise PermissionError(
                f"Access denied for tool '{tool_name}' on server '{server_name}'"
            )

    checker = StubPermissionChecker()
    protocol.set_permission_checker(checker, "test-server")
    protocol.set_tool_permission_level("test_tool", 3)

    request = MCPRequest(
        id=8,
        method="tools/call",
        params={"name": "test_tool", "arguments": {"arg1": "val"}},
    )
    response = await protocol.handle_request(request)

    assert response.is_success
    result = response.result
    assert result["isError"] is True
    assert "Access denied" in result["content"][0]["text"]
