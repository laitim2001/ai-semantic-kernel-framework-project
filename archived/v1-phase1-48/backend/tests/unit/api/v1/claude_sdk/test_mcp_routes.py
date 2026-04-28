"""Tests for Claude SDK MCP API routes.

Sprint 51: S51-3 MCP API Routes Unit Tests
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.v1.claude_sdk.mcp_routes import (
    router,
    MCPTransport,
    MCPServerStatus,
)


# Create test app
app = FastAPI()
app.include_router(router, prefix="/api/v1/claude-sdk")


class TestMCPRoutes:
    """Tests for Claude SDK MCP API routes."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_mcp_manager(self):
        """Create a mock MCP manager."""
        mock = MagicMock()
        mock.servers = {}
        mock.tools = {}
        return mock


class TestListServersEndpoint(TestMCPRoutes):
    """Tests for GET /mcp/servers endpoint."""

    def test_list_servers_empty(self, client, mock_mcp_manager):
        """Test listing servers when none are connected."""
        mock_mcp_manager.list_servers.return_value = []

        with patch(
            "src.api.v1.claude_sdk.mcp_routes.get_mcp_manager",
            return_value=mock_mcp_manager,
        ):
            response = client.get("/api/v1/claude-sdk/mcp/servers")
            assert response.status_code == 200
            data = response.json()
            assert data["servers"] == []
            assert data["total"] == 0
            assert data["connected"] == 0

    def test_list_servers_success(self, client, mock_mcp_manager):
        """Test listing connected servers."""
        mock_server_info = MagicMock()
        mock_server_info.name = "test-server"
        mock_server_info.state = "connected"
        mock_server_info.tools_count = 5
        mock_server_info.error = None

        mock_server = MagicMock()
        mock_server._config = None

        mock_mcp_manager.list_servers.return_value = [mock_server_info]
        mock_mcp_manager.get_server.return_value = mock_server

        with patch(
            "src.api.v1.claude_sdk.mcp_routes.get_mcp_manager",
            return_value=mock_mcp_manager,
        ):
            response = client.get("/api/v1/claude-sdk/mcp/servers")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["connected"] == 1
            assert data["servers"][0]["name"] == "test-server"
            assert data["servers"][0]["status"] == "connected"

    def test_list_servers_filter_by_status(self, client, mock_mcp_manager):
        """Test filtering servers by status."""
        mock_server_info = MagicMock()
        mock_server_info.name = "connected-server"
        mock_server_info.state = "connected"
        mock_server_info.tools_count = 3
        mock_server_info.error = None

        mock_server = MagicMock()
        mock_server._config = None

        mock_mcp_manager.list_servers.return_value = [mock_server_info]
        mock_mcp_manager.get_server.return_value = mock_server

        with patch(
            "src.api.v1.claude_sdk.mcp_routes.get_mcp_manager",
            return_value=mock_mcp_manager,
        ):
            response = client.get(
                "/api/v1/claude-sdk/mcp/servers?status=connected"
            )
            assert response.status_code == 200
            data = response.json()
            assert all(s["status"] == "connected" for s in data["servers"])


class TestConnectServerEndpoint(TestMCPRoutes):
    """Tests for POST /mcp/servers/connect endpoint."""

    def test_connect_stdio_server(self, client, mock_mcp_manager):
        """Test connecting to a stdio server."""
        mock_mcp_manager.get_server.return_value = None
        mock_mcp_manager.add_server = MagicMock()
        mock_mcp_manager.connect_server = AsyncMock(return_value=True)
        mock_mcp_manager.discover_tools = AsyncMock()
        mock_mcp_manager.tools = {}

        with patch(
            "src.api.v1.claude_sdk.mcp_routes.get_mcp_manager",
            return_value=mock_mcp_manager,
        ), patch(
            "src.api.v1.claude_sdk.mcp_routes.MCPStdioServer",
        ):
            response = client.post(
                "/api/v1/claude-sdk/mcp/servers/connect",
                json={
                    "name": "test-stdio",
                    "transport": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem"],
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "test-stdio"
            assert data["status"] == "connected"

    def test_connect_http_server(self, client, mock_mcp_manager):
        """Test connecting to an HTTP server."""
        mock_mcp_manager.get_server.return_value = None
        mock_mcp_manager.add_server = MagicMock()
        mock_mcp_manager.connect_server = AsyncMock(return_value=True)
        mock_mcp_manager.discover_tools = AsyncMock()
        mock_mcp_manager.tools = {}

        with patch(
            "src.api.v1.claude_sdk.mcp_routes.get_mcp_manager",
            return_value=mock_mcp_manager,
        ), patch(
            "src.api.v1.claude_sdk.mcp_routes.MCPHTTPServer",
        ):
            response = client.post(
                "/api/v1/claude-sdk/mcp/servers/connect",
                json={
                    "name": "test-http",
                    "transport": "http",
                    "url": "http://localhost:8080/mcp",
                },
            )
            assert response.status_code == 200

    def test_connect_stdio_missing_command(self, client, mock_mcp_manager):
        """Test connecting to stdio server without command."""
        with patch(
            "src.api.v1.claude_sdk.mcp_routes.get_mcp_manager",
            return_value=mock_mcp_manager,
        ):
            response = client.post(
                "/api/v1/claude-sdk/mcp/servers/connect",
                json={"name": "test", "transport": "stdio"},
            )
            assert response.status_code == 400
            assert "command" in response.json()["detail"].lower()

    def test_connect_http_missing_url(self, client, mock_mcp_manager):
        """Test connecting to HTTP server without URL."""
        with patch(
            "src.api.v1.claude_sdk.mcp_routes.get_mcp_manager",
            return_value=mock_mcp_manager,
        ):
            response = client.post(
                "/api/v1/claude-sdk/mcp/servers/connect",
                json={"name": "test", "transport": "http"},
            )
            assert response.status_code == 400
            assert "url" in response.json()["detail"].lower()


class TestDisconnectServerEndpoint(TestMCPRoutes):
    """Tests for POST /mcp/servers/{id}/disconnect endpoint."""

    def test_disconnect_server_success(self, client, mock_mcp_manager):
        """Test disconnecting a connected server."""
        mock_server = MagicMock()
        mock_mcp_manager.get_server.return_value = mock_server
        mock_mcp_manager.disconnect_server = AsyncMock(return_value=True)

        with patch(
            "src.api.v1.claude_sdk.mcp_routes.get_mcp_manager",
            return_value=mock_mcp_manager,
        ):
            response = client.post(
                "/api/v1/claude-sdk/mcp/servers/test-server/disconnect"
            )
            assert response.status_code == 204

    def test_disconnect_server_not_found(self, client, mock_mcp_manager):
        """Test disconnecting a non-existent server."""
        mock_mcp_manager.get_server.return_value = None

        with patch(
            "src.api.v1.claude_sdk.mcp_routes.get_mcp_manager",
            return_value=mock_mcp_manager,
        ):
            response = client.post(
                "/api/v1/claude-sdk/mcp/servers/nonexistent/disconnect"
            )
            assert response.status_code == 404


class TestServerHealthEndpoint(TestMCPRoutes):
    """Tests for GET /mcp/servers/{id}/health endpoint."""

    def test_health_check_healthy(self, client, mock_mcp_manager):
        """Test health check for a healthy server."""
        mock_server = MagicMock()
        mock_mcp_manager.get_server.return_value = mock_server

        mock_health_result = MagicMock()
        mock_health_result.name = "test-server"
        mock_health_result.healthy = True
        mock_health_result.latency_ms = 15.5
        mock_health_result.error = None

        mock_mcp_manager.health_check = AsyncMock(
            return_value={"test-server": mock_health_result}
        )

        with patch(
            "src.api.v1.claude_sdk.mcp_routes.get_mcp_manager",
            return_value=mock_mcp_manager,
        ):
            response = client.get(
                "/api/v1/claude-sdk/mcp/servers/test-server/health"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["healthy"] is True
            assert data["latency_ms"] == 15.5

    def test_health_check_unhealthy(self, client, mock_mcp_manager):
        """Test health check for an unhealthy server."""
        mock_server = MagicMock()
        mock_mcp_manager.get_server.return_value = mock_server

        mock_health_result = MagicMock()
        mock_health_result.name = "test-server"
        mock_health_result.healthy = False
        mock_health_result.latency_ms = None
        mock_health_result.error = "Connection timeout"

        mock_mcp_manager.health_check = AsyncMock(
            return_value={"test-server": mock_health_result}
        )

        with patch(
            "src.api.v1.claude_sdk.mcp_routes.get_mcp_manager",
            return_value=mock_mcp_manager,
        ):
            response = client.get(
                "/api/v1/claude-sdk/mcp/servers/test-server/health"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["healthy"] is False
            assert "timeout" in data["error"].lower()

    def test_health_check_server_not_found(self, client, mock_mcp_manager):
        """Test health check for a non-existent server."""
        mock_mcp_manager.get_server.return_value = None

        with patch(
            "src.api.v1.claude_sdk.mcp_routes.get_mcp_manager",
            return_value=mock_mcp_manager,
        ):
            response = client.get(
                "/api/v1/claude-sdk/mcp/servers/nonexistent/health"
            )
            assert response.status_code == 404


class TestListToolsEndpoint(TestMCPRoutes):
    """Tests for GET /mcp/tools endpoint."""

    def test_list_tools_empty(self, client, mock_mcp_manager):
        """Test listing tools when none are available."""
        mock_mcp_manager.tools = {}

        with patch(
            "src.api.v1.claude_sdk.mcp_routes.get_mcp_manager",
            return_value=mock_mcp_manager,
        ):
            response = client.get("/api/v1/claude-sdk/mcp/tools")
            assert response.status_code == 200
            data = response.json()
            assert data["tools"] == []
            assert data["total"] == 0

    def test_list_tools_success(self, client, mock_mcp_manager):
        """Test listing available MCP tools."""
        mock_tool_def = MagicMock()
        mock_tool_def.name = "read_file"
        mock_tool_def.description = "Read a file"
        mock_tool_def.input_schema = {"type": "object"}

        mock_mcp_manager.tools = {"server1:read_file": mock_tool_def}

        with patch(
            "src.api.v1.claude_sdk.mcp_routes.get_mcp_manager",
            return_value=mock_mcp_manager,
        ):
            response = client.get("/api/v1/claude-sdk/mcp/tools")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["tools"][0]["name"] == "read_file"
            assert data["tools"][0]["server_name"] == "server1"

    def test_list_tools_filter_by_server(self, client, mock_mcp_manager):
        """Test filtering tools by server ID."""
        mock_tool1 = MagicMock()
        mock_tool1.name = "tool1"
        mock_tool1.description = "Tool 1"
        mock_tool1.input_schema = {}

        mock_tool2 = MagicMock()
        mock_tool2.name = "tool2"
        mock_tool2.description = "Tool 2"
        mock_tool2.input_schema = {}

        mock_mcp_manager.tools = {
            "server1:tool1": mock_tool1,
            "server2:tool2": mock_tool2,
        }

        with patch(
            "src.api.v1.claude_sdk.mcp_routes.get_mcp_manager",
            return_value=mock_mcp_manager,
        ):
            response = client.get("/api/v1/claude-sdk/mcp/tools?server_id=server1")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["tools"][0]["server_name"] == "server1"


class TestExecuteToolEndpoint(TestMCPRoutes):
    """Tests for POST /mcp/tools/execute endpoint."""

    def test_execute_tool_success(self, client, mock_mcp_manager):
        """Test executing an MCP tool successfully."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.content = {"data": "result"}
        mock_result.error = None
        mock_result.execution_time_ms = 25.5

        mock_mcp_manager.execute_tool = AsyncMock(return_value=mock_result)
        mock_mcp_manager.find_tool_server.return_value = "server1"

        with patch(
            "src.api.v1.claude_sdk.mcp_routes.get_mcp_manager",
            return_value=mock_mcp_manager,
        ):
            response = client.post(
                "/api/v1/claude-sdk/mcp/tools/execute",
                json={
                    "tool_ref": "server1:read_file",
                    "arguments": {"path": "/test.txt"},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["tool_name"] == "read_file"
            assert data["server_name"] == "server1"

    def test_execute_tool_without_server_prefix(self, client, mock_mcp_manager):
        """Test executing a tool without server prefix."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.content = "done"
        mock_result.error = None
        mock_result.execution_time_ms = 10.0

        mock_mcp_manager.find_tool_server.return_value = "auto-server"
        mock_mcp_manager.execute_tool = AsyncMock(return_value=mock_result)

        with patch(
            "src.api.v1.claude_sdk.mcp_routes.get_mcp_manager",
            return_value=mock_mcp_manager,
        ):
            response = client.post(
                "/api/v1/claude-sdk/mcp/tools/execute",
                json={"tool_ref": "read_file", "arguments": {}},
            )
            assert response.status_code == 200

    def test_execute_tool_not_found(self, client, mock_mcp_manager):
        """Test executing a non-existent tool."""
        mock_mcp_manager.find_tool_server.return_value = None

        with patch(
            "src.api.v1.claude_sdk.mcp_routes.get_mcp_manager",
            return_value=mock_mcp_manager,
        ):
            response = client.post(
                "/api/v1/claude-sdk/mcp/tools/execute",
                json={"tool_ref": "nonexistent", "arguments": {}},
            )
            assert response.status_code == 404

    def test_execute_tool_error(self, client, mock_mcp_manager):
        """Test tool execution error handling."""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.content = None
        mock_result.error = "Execution failed"
        mock_result.execution_time_ms = 5.0

        mock_mcp_manager.execute_tool = AsyncMock(return_value=mock_result)
        mock_mcp_manager.find_tool_server.return_value = "server1"

        with patch(
            "src.api.v1.claude_sdk.mcp_routes.get_mcp_manager",
            return_value=mock_mcp_manager,
        ):
            response = client.post(
                "/api/v1/claude-sdk/mcp/tools/execute",
                json={"tool_ref": "server1:failing_tool", "arguments": {}},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert data["error"] is not None


class TestMCPEnums:
    """Tests for MCP-related enums."""

    def test_transport_enum_values(self):
        """Test MCPTransport enum values."""
        assert MCPTransport.STDIO == "stdio"
        assert MCPTransport.HTTP == "http"
        assert MCPTransport.WEBSOCKET == "websocket"

    def test_server_status_enum_values(self):
        """Test MCPServerStatus enum values."""
        assert MCPServerStatus.CONNECTED == "connected"
        assert MCPServerStatus.DISCONNECTED == "disconnected"
        assert MCPServerStatus.CONNECTING == "connecting"
        assert MCPServerStatus.ERROR == "error"
