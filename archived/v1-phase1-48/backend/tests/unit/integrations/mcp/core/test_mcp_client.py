"""Tests for MCP Client.

Sprint 130: MCP Core module unit tests.

Tests MCPClient and ServerConfig from src.integrations.mcp.core.client,
using InMemoryTransport + MCPProtocol to simulate a real MCP server
without subprocess overhead.
"""

import pytest

from src.integrations.mcp.core.client import MCPClient, ServerConfig
from src.integrations.mcp.core.protocol import MCPProtocol
from src.integrations.mcp.core.transport import InMemoryTransport
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
def vm_schema():
    """Create a ToolSchema for the list_vms tool."""
    return ToolSchema(
        name="list_vms",
        description="List virtual machines in a resource group",
        parameters=[
            ToolParameter(
                name="resource_group",
                type=ToolInputType.STRING,
                description="Azure resource group name",
                required=True,
            ),
        ],
        returns="List of VM objects with name, status, and size",
    )


@pytest.fixture
def server_protocol(vm_schema):
    """Create an MCPProtocol that acts as a mock MCP server with one tool."""
    protocol = MCPProtocol()

    async def list_vms_handler(**kwargs):
        rg = kwargs.get("resource_group", "unknown")
        return ToolResult(success=True, content=f"vm-1, vm-2 in {rg}")

    protocol.register_tool("list_vms", list_vms_handler, vm_schema)
    return protocol


@pytest.fixture
def server_transport(server_protocol):
    """Create an InMemoryTransport backed by the server protocol."""
    return InMemoryTransport(protocol=server_protocol)


@pytest.fixture
def server_config():
    """Create a minimal ServerConfig for testing."""
    return ServerConfig(
        name="test-server",
        command="python",
        args=["-m", "mcp_servers.test"],
    )


@pytest.fixture
async def connected_client(server_config, server_transport):
    """Create an MCPClient with a connected test server."""
    client = MCPClient()
    await client.connect(server_config, transport=server_transport)
    yield client
    await client.close()


# ---------------------------------------------------------------------------
# Tests: ServerConfig Validation
# ---------------------------------------------------------------------------

def test_server_config_validation():
    """ServerConfig requires name and command; missing either should raise ValueError."""
    with pytest.raises(ValueError, match="Server name is required"):
        ServerConfig(name="", command="python")

    with pytest.raises(ValueError, match="Server command is required"):
        ServerConfig(name="test", command="")


def test_server_config_defaults():
    """ServerConfig should have sensible defaults for transport and timeout."""
    config = ServerConfig(name="test-server", command="python")

    assert config.transport == "stdio"
    assert config.timeout == 30.0
    assert config.args == []
    assert config.env == {}
    assert config.cwd is None


# ---------------------------------------------------------------------------
# Tests: Connect / Disconnect
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_client_connect_with_transport(server_config, server_transport):
    """Connecting with a custom InMemoryTransport should succeed."""
    client = MCPClient()

    result = await client.connect(server_config, transport=server_transport)

    assert result is True
    assert client.is_connected("test-server") is True
    assert "test-server" in client.connected_servers

    await client.close()


@pytest.mark.asyncio
async def test_client_connect_already_connected(server_config, server_transport):
    """Connecting to an already-connected server should return True without error."""
    client = MCPClient()
    await client.connect(server_config, transport=server_transport)

    # Second connect should short-circuit and return True
    result = await client.connect(server_config, transport=server_transport)

    assert result is True
    assert len(client.connected_servers) == 1

    await client.close()


@pytest.mark.asyncio
async def test_client_disconnect(server_config, server_transport):
    """Disconnecting should remove the server from connected_servers."""
    client = MCPClient()
    await client.connect(server_config, transport=server_transport)
    assert client.is_connected("test-server") is True

    result = await client.disconnect("test-server")

    assert result is True
    assert client.is_connected("test-server") is False
    assert "test-server" not in client.connected_servers


@pytest.mark.asyncio
async def test_client_disconnect_not_found():
    """Disconnecting a server that was never connected should return True (idempotent)."""
    client = MCPClient()

    result = await client.disconnect("nonexistent-server")

    assert result is True


# ---------------------------------------------------------------------------
# Tests: List Tools
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_client_list_tools(connected_client):
    """list_tools should return tools for the connected server."""
    tools = await connected_client.list_tools()

    assert "test-server" in tools
    server_tools = tools["test-server"]
    assert len(server_tools) == 1
    assert server_tools[0].name == "list_vms"
    assert server_tools[0].description == "List virtual machines in a resource group"


@pytest.mark.asyncio
async def test_client_list_tools_filter_by_server(connected_client):
    """list_tools with server_name should return tools for that server only."""
    tools = await connected_client.list_tools(server_name="test-server")

    assert "test-server" in tools
    assert len(tools) == 1

    # Filtering by a non-connected server should return empty
    empty_tools = await connected_client.list_tools(server_name="nonexistent")
    assert empty_tools == {}


# ---------------------------------------------------------------------------
# Tests: Call Tool
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_client_call_tool_success(connected_client):
    """Calling a registered tool should return a successful ToolResult."""
    result = await connected_client.call_tool(
        server="test-server",
        tool="list_vms",
        arguments={"resource_group": "prod-rg"},
    )

    assert result.success is True
    assert "vm-1" in result.content
    assert "vm-2" in result.content
    assert "prod-rg" in result.content
    assert result.metadata["server"] == "test-server"
    assert result.metadata["tool"] == "list_vms"


@pytest.mark.asyncio
async def test_client_call_tool_not_connected():
    """Calling a tool on a server that is not connected should return an error."""
    client = MCPClient()

    result = await client.call_tool(
        server="disconnected-server",
        tool="list_vms",
        arguments={},
    )

    assert result.success is False
    assert "not connected" in result.error.lower()


@pytest.mark.asyncio
async def test_client_call_tool_not_found(connected_client):
    """Calling a tool that does not exist should return an error ToolResult."""
    result = await connected_client.call_tool(
        server="test-server",
        tool="nonexistent_tool",
        arguments={},
    )

    assert result.success is False
    assert "not found" in result.error.lower()


# ---------------------------------------------------------------------------
# Tests: Connection Status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_client_is_connected(server_config, server_transport):
    """is_connected should reflect connection state accurately."""
    client = MCPClient()

    assert client.is_connected("test-server") is False

    await client.connect(server_config, transport=server_transport)
    assert client.is_connected("test-server") is True

    await client.disconnect("test-server")
    assert client.is_connected("test-server") is False


@pytest.mark.asyncio
async def test_client_connected_servers_property(server_config, server_transport):
    """connected_servers should return a list of names of connected servers."""
    client = MCPClient()
    assert client.connected_servers == []

    await client.connect(server_config, transport=server_transport)
    assert client.connected_servers == ["test-server"]

    await client.disconnect("test-server")
    assert client.connected_servers == []


# ---------------------------------------------------------------------------
# Tests: Server Info
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_client_get_server_info(connected_client):
    """get_server_info should return server info dict after connection."""
    info = connected_client.get_server_info("test-server")

    assert info is not None
    assert "protocolVersion" in info
    assert "serverInfo" in info
    assert info["serverInfo"]["name"] == MCPProtocol.SERVER_NAME

    # Non-connected server should return None
    assert connected_client.get_server_info("nonexistent") is None


# ---------------------------------------------------------------------------
# Tests: Close All
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_client_close_all(server_transport, vm_schema):
    """close() should disconnect all servers."""
    client = MCPClient()

    config_a = ServerConfig(name="server-a", command="python")
    transport_a = InMemoryTransport(protocol=_make_server_protocol(vm_schema))
    await client.connect(config_a, transport=transport_a)

    config_b = ServerConfig(name="server-b", command="python")
    transport_b = InMemoryTransport(protocol=_make_server_protocol(vm_schema))
    await client.connect(config_b, transport=transport_b)

    assert len(client.connected_servers) == 2

    await client.close()

    assert len(client.connected_servers) == 0
    assert client.is_connected("server-a") is False
    assert client.is_connected("server-b") is False


# ---------------------------------------------------------------------------
# Tests: Async Context Manager
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_client_async_context_manager(server_config, server_transport):
    """MCPClient should support async with for automatic cleanup."""
    async with MCPClient() as client:
        await client.connect(server_config, transport=server_transport)
        assert client.is_connected("test-server") is True

    # After exiting the context manager, all servers should be disconnected.
    # We verify by checking the transport was stopped.
    assert server_transport.is_connected() is False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_server_protocol(schema: ToolSchema) -> MCPProtocol:
    """Create a minimal MCPProtocol with a single tool for multi-server tests."""
    protocol = MCPProtocol()

    async def handler(**kwargs):
        return ToolResult(success=True, content="ok")

    protocol.register_tool(schema.name, handler, schema)
    return protocol
