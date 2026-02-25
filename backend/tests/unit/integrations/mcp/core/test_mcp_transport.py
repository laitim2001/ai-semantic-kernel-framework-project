"""Tests for MCP Transport Layer.

Sprint 130: MCP Core module unit tests.

Tests BaseTransport, InMemoryTransport, and StdioTransport from
src.integrations.mcp.core.transport, covering connection lifecycle,
error hierarchy, and request/response routing through InMemoryTransport.
"""

import pytest

from src.integrations.mcp.core.protocol import MCPProtocol
from src.integrations.mcp.core.transport import (
    BaseTransport,
    ConnectionError,
    InMemoryTransport,
    StdioTransport,
    TimeoutError,
    TransportError,
)
from src.integrations.mcp.core.types import (
    ToolInputType,
    ToolParameter,
    ToolResult,
    ToolSchema,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tool_schema():
    """Create a sample ToolSchema for testing."""
    return ToolSchema(
        name="test",
        description="A test tool",
        parameters=[
            ToolParameter(
                name="input",
                type=ToolInputType.STRING,
                description="Test input",
                required=True,
            ),
        ],
    )


@pytest.fixture
def protocol_with_tool(tool_schema):
    """Create an MCPProtocol with a registered test tool."""
    protocol = MCPProtocol()

    async def handler(**kwargs):
        return ToolResult(success=True, content="ok")

    protocol.register_tool("test", handler, tool_schema)
    return protocol


@pytest.fixture
def in_memory_transport(protocol_with_tool):
    """Create an InMemoryTransport backed by a real protocol."""
    return InMemoryTransport(protocol=protocol_with_tool)


# ---------------------------------------------------------------------------
# Tests: Error Hierarchy
# ---------------------------------------------------------------------------

def test_transport_error_hierarchy():
    """TransportError is base; ConnectionError and TimeoutError are subclasses."""
    assert issubclass(ConnectionError, TransportError)
    assert issubclass(TimeoutError, TransportError)

    # Instances should also be instances of the base
    conn_err = ConnectionError("connection failed")
    timeout_err = TimeoutError("timed out")
    assert isinstance(conn_err, TransportError)
    assert isinstance(timeout_err, TransportError)

    # They should also be catchable as Exception
    assert isinstance(conn_err, Exception)
    assert isinstance(timeout_err, Exception)


# ---------------------------------------------------------------------------
# Tests: InMemoryTransport Lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_in_memory_transport_start_stop(in_memory_transport):
    """Starting sets connected=True; stopping sets connected=False."""
    assert in_memory_transport.is_connected() is False

    await in_memory_transport.start()
    assert in_memory_transport.is_connected() is True

    await in_memory_transport.stop()
    assert in_memory_transport.is_connected() is False


@pytest.mark.asyncio
async def test_in_memory_transport_is_connected(in_memory_transport):
    """is_connected should accurately reflect start/stop state transitions."""
    assert in_memory_transport.is_connected() is False

    await in_memory_transport.start()
    assert in_memory_transport.is_connected() is True

    await in_memory_transport.stop()
    assert in_memory_transport.is_connected() is False

    # Can be started again
    await in_memory_transport.start()
    assert in_memory_transport.is_connected() is True


# ---------------------------------------------------------------------------
# Tests: InMemoryTransport Send
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_in_memory_transport_send(in_memory_transport, protocol_with_tool):
    """Sending a request through InMemoryTransport should route to the protocol."""
    await in_memory_transport.start()

    request = protocol_with_tool.create_request("tools/list", {})
    response = await in_memory_transport.send(request)

    assert response.is_success
    tools = response.result["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == "test"


@pytest.mark.asyncio
async def test_in_memory_transport_not_connected():
    """Sending when not connected should raise ConnectionError."""
    transport = InMemoryTransport(protocol=MCPProtocol())
    # Do NOT call start()

    request = MCPProtocol().create_request("ping", {})

    with pytest.raises(ConnectionError):
        await transport.send(request)


@pytest.mark.asyncio
async def test_in_memory_transport_no_protocol():
    """Sending with no protocol configured should raise ConnectionError."""
    transport = InMemoryTransport(protocol=None)
    await transport.start()

    request = MCPProtocol().create_request("ping", {})

    with pytest.raises(ConnectionError):
        await transport.send(request)


@pytest.mark.asyncio
async def test_in_memory_transport_set_protocol():
    """set_protocol should replace the protocol handler after construction."""
    transport = InMemoryTransport(protocol=None)

    new_protocol = MCPProtocol()

    new_tool_schema = ToolSchema(
        name="new_tool",
        description="A replacement tool",
        parameters=[
            ToolParameter(
                name="input",
                type=ToolInputType.STRING,
                description="Test input",
                required=True,
            ),
        ],
    )

    async def handler(**kwargs):
        return ToolResult(success=True, content="from new protocol")

    new_protocol.register_tool("new_tool", handler, new_tool_schema)
    transport.set_protocol(new_protocol)

    await transport.start()

    request = new_protocol.create_request("tools/list", {})
    response = await transport.send(request)

    assert response.is_success
    tools = response.result["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == "new_tool"


# ---------------------------------------------------------------------------
# Tests: StdioTransport
# ---------------------------------------------------------------------------

def test_stdio_transport_init():
    """StdioTransport should store constructor arguments correctly."""
    transport = StdioTransport(
        command="python",
        args=["-m", "mcp_servers.test"],
        env={"KEY": "VALUE"},
        timeout=60.0,
        cwd="/tmp",
    )

    assert transport._command == "python"
    assert transport._args == ["-m", "mcp_servers.test"]
    assert transport._env == {"KEY": "VALUE"}
    assert transport._timeout == 60.0
    assert transport._cwd == "/tmp"


def test_stdio_transport_not_connected_by_default():
    """StdioTransport should not be connected before start() is called."""
    transport = StdioTransport(command="echo", args=["hello"])

    assert transport.is_connected() is False
