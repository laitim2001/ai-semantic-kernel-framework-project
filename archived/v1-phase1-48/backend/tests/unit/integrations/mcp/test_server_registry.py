"""Tests for MCP Server Registry.

Sprint 123, Story 123-3: MCP module unit tests.

Tests ServerRegistry from src.integrations.mcp.registry.server_registry,
covering server registration, unregistration, listing, status queries,
and status summary generation.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.mcp.registry.server_registry import (
    RegisteredServer,
    ServerRegistry,
    ServerStatus,
)


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCPClient for testing."""
    client = AsyncMock()
    client.connect = AsyncMock(return_value=True)
    client.disconnect = AsyncMock()
    client.list_tools = AsyncMock(return_value={})
    client.close = AsyncMock()
    return client


@pytest.fixture
def registry(mock_mcp_client):
    """Create a ServerRegistry with mocked MCPClient."""
    with patch(
        "src.integrations.mcp.registry.server_registry.MCPClient",
        return_value=mock_mcp_client,
    ):
        reg = ServerRegistry(max_retries=2, retry_delay=0.01)
    return reg


@pytest.fixture
def sample_server():
    """Create a sample RegisteredServer for testing."""
    return RegisteredServer(
        name="test-server",
        command="python",
        args=["-m", "mcp_servers.test"],
        enabled=True,
    )


@pytest.fixture
def sample_server_b():
    """Create a second sample RegisteredServer for testing."""
    return RegisteredServer(
        name="azure-mcp",
        command="python",
        args=["-m", "mcp_servers.azure"],
        enabled=True,
    )


class TestServerRegistryBasic:
    """Tests for basic server registration operations."""

    @pytest.mark.asyncio
    async def test_register_server(self, registry, sample_server):
        """Test registering a new server returns True."""
        result = await registry.register(sample_server)
        assert result is True
        assert "test-server" in registry.servers

    @pytest.mark.asyncio
    async def test_register_duplicate_server_returns_false(
        self, registry, sample_server
    ):
        """Test registering a duplicate server name returns False."""
        await registry.register(sample_server)
        result = await registry.register(sample_server)
        assert result is False

    @pytest.mark.asyncio
    async def test_unregister_server(self, registry, sample_server):
        """Test unregistering an existing server returns True."""
        await registry.register(sample_server)
        result = await registry.unregister("test-server")
        assert result is True
        assert "test-server" not in registry.servers

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_returns_false(self, registry):
        """Test unregistering a nonexistent server returns False."""
        result = await registry.unregister("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_servers(self, registry, sample_server, sample_server_b):
        """Test listing registered servers returns all names."""
        await registry.register(sample_server)
        await registry.register(sample_server_b)

        servers = registry.servers
        assert len(servers) == 2
        assert "test-server" in servers
        assert "azure-mcp" in servers

    @pytest.mark.asyncio
    async def test_get_status_unknown_server(self, registry):
        """Test getting status of an unregistered server returns None."""
        server = registry.get_server("nonexistent")
        assert server is None

    @pytest.mark.asyncio
    async def test_get_server_returns_registered(self, registry, sample_server):
        """Test getting a registered server returns the correct object."""
        await registry.register(sample_server)
        server = registry.get_server("test-server")
        assert server is not None
        assert server.name == "test-server"
        assert server.status == ServerStatus.REGISTERED

    @pytest.mark.asyncio
    async def test_servers_property_returns_copy(self, registry, sample_server):
        """Test that servers property returns a copy, not internal dict."""
        await registry.register(sample_server)
        servers_copy = registry.servers
        servers_copy["injected"] = MagicMock()

        # Internal state should not be affected
        assert "injected" not in registry.servers


class TestServerRegistryStatusSummary:
    """Tests for server status summary generation."""

    @pytest.mark.asyncio
    async def test_empty_registry(self, registry):
        """Test status summary for empty registry."""
        summary = registry.get_status_summary()
        assert summary["total_servers"] == 0
        assert summary["total_tools"] == 0
        assert summary["servers"] == []
        # All status counts should be 0
        for status in ServerStatus:
            assert summary["status_counts"][status.value] == 0

    @pytest.mark.asyncio
    async def test_summary_counts(self, registry, sample_server, sample_server_b):
        """Test status summary correctly counts servers by status."""
        await registry.register(sample_server)
        await registry.register(sample_server_b)

        summary = registry.get_status_summary()
        assert summary["total_servers"] == 2
        assert summary["status_counts"]["registered"] == 2
        assert summary["total_tools"] == 0
        assert len(summary["servers"]) == 2

        # Verify server detail structure
        names = [s["name"] for s in summary["servers"]]
        assert "test-server" in names
        assert "azure-mcp" in names

        # Verify each server detail has expected keys
        for detail in summary["servers"]:
            assert "name" in detail
            assert "status" in detail
            assert "enabled" in detail
            assert "tools_count" in detail
            assert "last_connected" in detail
            assert "last_error" in detail
            assert "retry_count" in detail

    @pytest.mark.asyncio
    async def test_summary_with_mixed_statuses(self, registry):
        """Test summary correctly counts multiple status types."""
        server_a = RegisteredServer(
            name="server-a", command="cmd", enabled=True,
        )
        server_b = RegisteredServer(
            name="server-b", command="cmd", enabled=True,
        )
        await registry.register(server_a)
        await registry.register(server_b)

        # Manually set one to error status
        registry._servers["server-b"].status = ServerStatus.ERROR
        registry._servers["server-b"].last_error = "Connection timeout"

        summary = registry.get_status_summary()
        assert summary["status_counts"]["registered"] == 1
        assert summary["status_counts"]["error"] == 1

        # Verify server-b shows error details
        server_b_detail = next(
            s for s in summary["servers"] if s["name"] == "server-b"
        )
        assert server_b_detail["status"] == "error"
        assert server_b_detail["last_error"] == "Connection timeout"

    @pytest.mark.asyncio
    async def test_connected_servers_property(self, registry):
        """Test connected_servers returns only connected server names."""
        server_a = RegisteredServer(
            name="connected-srv", command="cmd", enabled=True,
        )
        server_b = RegisteredServer(
            name="disconnected-srv", command="cmd", enabled=True,
        )
        await registry.register(server_a)
        await registry.register(server_b)

        # Manually mark one as connected
        registry._servers["connected-srv"].status = ServerStatus.CONNECTED

        connected = registry.connected_servers
        assert "connected-srv" in connected
        assert "disconnected-srv" not in connected
