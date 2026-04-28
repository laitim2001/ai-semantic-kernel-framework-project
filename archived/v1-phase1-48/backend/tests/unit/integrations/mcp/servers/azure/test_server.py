"""Tests for Azure MCP Server.

Tests AzureMCPServer class and main entry point.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import json

import pytest

from src.integrations.mcp.servers.azure.server import (
    AzureMCPServer,
    create_server_from_env,
)
from src.integrations.mcp.servers.azure.client import AzureConfig


class TestAzureMCPServer:
    """Tests for AzureMCPServer."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return AzureConfig(subscription_id="test-subscription")

    @pytest.fixture
    def server(self, config):
        """Create test server."""
        with patch("src.integrations.mcp.servers.azure.server.AzureClientManager"):
            return AzureMCPServer(config)

    def test_server_initialization(self, server):
        """Test server initializes correctly."""
        assert server.SERVER_NAME == "azure-mcp"
        assert server.SERVER_VERSION == "1.0.0"
        assert server._running is False

    def test_server_registers_all_tools(self, server):
        """Test that server registers all 23 tools."""
        tools = server.get_tools()
        # Should have 23 tools total (7 VM + 4 Resource + 3 Monitor + 5 Network + 4 Storage)
        assert len(tools) == 23

    def test_get_tool_names(self, server):
        """Test get_tool_names returns correct names."""
        names = server.get_tool_names()

        # Check some expected tool names
        assert "list_vms" in names
        assert "get_vm" in names
        assert "list_resource_groups" in names
        assert "get_metrics" in names
        assert "list_vnets" in names
        assert "list_storage_accounts" in names

    def test_vm_tools_registered(self, server):
        """Test that VM tools are registered."""
        names = server.get_tool_names()
        vm_tools = [
            "list_vms", "get_vm", "get_vm_status",
            "start_vm", "stop_vm", "restart_vm", "run_command"
        ]
        for tool in vm_tools:
            assert tool in names

    def test_resource_tools_registered(self, server):
        """Test that resource tools are registered."""
        names = server.get_tool_names()
        resource_tools = [
            "list_resource_groups", "get_resource_group",
            "list_resources", "search_resources"
        ]
        for tool in resource_tools:
            assert tool in names

    def test_monitor_tools_registered(self, server):
        """Test that monitor tools are registered."""
        names = server.get_tool_names()
        monitor_tools = ["get_metrics", "list_alerts", "get_metric_definitions"]
        for tool in monitor_tools:
            assert tool in names

    def test_network_tools_registered(self, server):
        """Test that network tools are registered."""
        names = server.get_tool_names()
        network_tools = [
            "list_vnets", "get_vnet", "list_nsgs",
            "get_nsg_rules", "list_public_ips"
        ]
        for tool in network_tools:
            assert tool in names

    def test_storage_tools_registered(self, server):
        """Test that storage tools are registered."""
        names = server.get_tool_names()
        storage_tools = [
            "list_storage_accounts", "get_storage_account",
            "list_containers", "get_storage_usage"
        ]
        for tool in storage_tools:
            assert tool in names

    @pytest.mark.asyncio
    async def test_call_tool_success(self, server):
        """Test successful tool call."""
        # Mock the protocol handler
        mock_response = MagicMock()
        mock_response.error = None
        mock_response.result = {"vms": []}
        server._protocol.handle_request = AsyncMock(return_value=mock_response)

        result = await server.call_tool("list_vms", {})

        assert result.success is True
        assert result.content == {"vms": []}

    @pytest.mark.asyncio
    async def test_call_tool_with_error(self, server):
        """Test tool call with error response."""
        mock_response = MagicMock()
        mock_response.error = {"message": "Tool failed"}
        mock_response.result = None
        server._protocol.handle_request = AsyncMock(return_value=mock_response)

        result = await server.call_tool("list_vms", {})

        assert result.success is False
        assert "Tool failed" in result.error

    def test_stop_sets_running_false(self, server):
        """Test stop method sets running flag to false."""
        server._running = True
        server.stop()
        assert server._running is False

    def test_cleanup_closes_client_manager(self, server):
        """Test cleanup closes client manager."""
        server.cleanup()
        server._client_manager.close.assert_called_once()

    def test_context_manager_support(self, config):
        """Test context manager support."""
        with patch("src.integrations.mcp.servers.azure.server.AzureClientManager"):
            with AzureMCPServer(config) as server:
                assert isinstance(server, AzureMCPServer)
            # Verify cleanup was called (close on client manager)
            server._client_manager.close.assert_called()

    @pytest.mark.asyncio
    async def test_async_context_manager_support(self, config):
        """Test async context manager support."""
        with patch("src.integrations.mcp.servers.azure.server.AzureClientManager"):
            async with AzureMCPServer(config) as server:
                assert isinstance(server, AzureMCPServer)
            server._client_manager.close.assert_called()


class TestCreateServerFromEnv:
    """Tests for create_server_from_env factory function."""

    def test_creates_server_from_env(self):
        """Test server creation from environment variables."""
        with patch.dict("os.environ", {
            "AZURE_SUBSCRIPTION_ID": "test-sub-id",
        }):
            with patch("src.integrations.mcp.servers.azure.server.AzureClientManager"):
                server = create_server_from_env()
                assert isinstance(server, AzureMCPServer)

    def test_raises_error_without_subscription(self):
        """Test that missing subscription ID raises error."""
        import os
        with patch.dict("os.environ", {}, clear=True):
            os.environ.pop("AZURE_SUBSCRIPTION_ID", None)
            with pytest.raises(ValueError):
                create_server_from_env()


class TestServerProtocol:
    """Tests for server protocol handling."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return AzureConfig(subscription_id="test-subscription")

    @pytest.fixture
    def server(self, config):
        """Create test server."""
        with patch("src.integrations.mcp.servers.azure.server.AzureClientManager"):
            return AzureMCPServer(config)

    def test_error_response_creation(self, server):
        """Test error response creation."""
        response = server._create_error_response(
            request_id=1,
            code=-32600,
            message="Invalid Request"
        )

        assert response.jsonrpc == "2.0"
        assert response.id == 1
        assert response.error["code"] == -32600
        assert response.error["message"] == "Invalid Request"

    def test_write_response_format(self, server, capsys):
        """Test response write format."""
        from src.integrations.mcp.core.types import MCPResponse

        response = MCPResponse(
            jsonrpc="2.0",
            id=1,
            result={"success": True}
        )

        server._write_response(response)

        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())

        assert output["jsonrpc"] == "2.0"
        assert output["id"] == 1
        assert output["result"] == {"success": True}
