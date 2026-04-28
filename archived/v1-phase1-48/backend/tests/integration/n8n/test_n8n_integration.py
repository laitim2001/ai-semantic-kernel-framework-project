"""Integration Tests for n8n MCP Server + Webhook API.

Sprint 124: n8n Integration — Mode 1 + Mode 2

Tests cover:
    - End-to-end MCP Server → Tool execution flow
    - Webhook API → Processing pipeline flow
    - MCP tool schema validation (MCP format compliance)
    - Server + Client integration
    - Full webhook lifecycle
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.integrations.mcp.servers.n8n.client import N8nApiClient, N8nConfig
from src.integrations.mcp.servers.n8n.server import N8nMCPServer
from src.integrations.mcp.servers.n8n.tools.workflow import WorkflowTools
from src.integrations.mcp.servers.n8n.tools.execution import ExecutionTools
from src.api.v1.n8n.routes import router


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def n8n_config():
    """Create test configuration."""
    return N8nConfig(
        base_url="http://test-n8n:5678",
        api_key="test-key",
        timeout=5,
        max_retries=1,
    )


@pytest.fixture
def mock_n8n_client(n8n_config):
    """Create a mock N8nApiClient with pre-configured responses."""
    client = N8nApiClient(n8n_config)

    # Mock the internal httpx client
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.headers = {}
    client._client.request = AsyncMock(return_value=mock_response)

    return client


@pytest.fixture
def test_client():
    """Create test client for webhook API."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


# ---------------------------------------------------------------------------
# E2E: MCP Server Tool Execution
# ---------------------------------------------------------------------------


class TestMCPServerE2E:
    """End-to-end tests for MCP Server tool execution."""

    @pytest.mark.asyncio
    async def test_list_workflows_through_tools(self, n8n_config):
        """Test listing workflows through WorkflowTools."""
        client = N8nApiClient(n8n_config)

        # Mock HTTP response
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.headers = {}
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": "wf-1",
                    "name": "Test Workflow",
                    "active": True,
                    "createdAt": "2026-01-01T00:00:00Z",
                    "updatedAt": "2026-01-01T00:00:00Z",
                    "tags": [{"name": "test"}],
                },
            ],
            "nextCursor": None,
        }
        client._client.request = AsyncMock(return_value=mock_resp)

        tools = WorkflowTools(client)
        result = await tools.n8n_list_workflows()

        assert result.success is True
        assert result.content["count"] == 1
        assert result.content["workflows"][0]["id"] == "wf-1"
        assert result.content["workflows"][0]["tags"] == ["test"]

        await client.close()

    @pytest.mark.asyncio
    async def test_execute_workflow_through_tools(self, n8n_config):
        """Test executing a workflow through ExecutionTools."""
        client = N8nApiClient(n8n_config)

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.headers = {}
        mock_resp.json.return_value = {
            "data": {
                "executionId": "exec-789",
                "status": "success",
                "data": {"output": "completed"},
            },
        }
        client._client.request = AsyncMock(return_value=mock_resp)

        tools = ExecutionTools(client)
        result = await tools.n8n_execute_workflow(
            workflow_id="wf-1",
            input_data={"action": "test"},
        )

        assert result.success is True
        assert result.content["executionId"] == "exec-789"
        assert result.content["status"] == "success"
        assert result.metadata["workflow_id"] == "wf-1"

        await client.close()

    @pytest.mark.asyncio
    async def test_tool_handles_missing_workflow_id(self, n8n_config):
        """Test tools handle missing required parameters."""
        client = N8nApiClient(n8n_config)

        tools = WorkflowTools(client)
        result = await tools.n8n_get_workflow(workflow_id="")

        assert result.success is False
        assert "required" in result.error.lower()

        await client.close()


# ---------------------------------------------------------------------------
# E2E: Webhook Lifecycle
# ---------------------------------------------------------------------------


class TestWebhookE2E:
    """End-to-end tests for webhook processing lifecycle."""

    def test_full_webhook_lifecycle(self, test_client):
        """Test complete webhook lifecycle: receive → process → respond."""
        # Step 1: Send webhook
        payload = {
            "workflow_id": "wf-prod-001",
            "execution_id": "exec-prod-001",
            "action": "analyze",
            "data": {
                "incident_id": "INC-2026-001",
                "severity": "high",
                "description": "Database connection pool exhausted",
            },
            "metadata": {"environment": "production"},
        }

        response = test_client.post("/api/v1/n8n/webhook", json=payload)

        # Step 2: Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["request_id"]  # UUID generated
        assert data["action"] == "analyze"
        assert data["result"]["action"] == "analyze"
        assert data["timestamp"]  # Timestamp present

    def test_multiple_actions_in_sequence(self, test_client):
        """Test processing multiple webhook actions in sequence."""
        actions = ["analyze", "classify", "execute", "query", "notify"]

        for action in actions:
            payload = {
                "workflow_id": f"wf-{action}",
                "execution_id": f"exec-{action}",
                "action": action,
                "data": {"test": True},
            }

            response = test_client.post("/api/v1/n8n/webhook", json=payload)
            assert response.status_code == 200
            assert response.json()["success"] is True
            assert response.json()["action"] == action


# ---------------------------------------------------------------------------
# MCP Format Compliance
# ---------------------------------------------------------------------------


class TestMCPFormatCompliance:
    """Tests for MCP protocol format compliance."""

    def test_tool_schemas_are_mcp_compliant(self, n8n_config):
        """Test that tool schemas produce valid MCP format."""
        server = N8nMCPServer(n8n_config)

        for tool in server.get_tools():
            mcp_format = tool.to_mcp_format()

            # Required MCP fields
            assert "name" in mcp_format
            assert "description" in mcp_format
            assert "inputSchema" in mcp_format
            assert mcp_format["inputSchema"]["type"] == "object"
            assert "properties" in mcp_format["inputSchema"]

    def test_tool_names_follow_convention(self, n8n_config):
        """Test tool names follow n8n_ prefix convention."""
        server = N8nMCPServer(n8n_config)

        for name in server.get_tool_names():
            assert name.startswith("n8n_"), f"Tool {name} should start with n8n_"

    def test_permission_levels_defined_for_all_tools(self, n8n_config):
        """Test all tools have permission levels defined."""
        all_permissions = {}
        all_permissions.update(WorkflowTools.PERMISSION_LEVELS)
        all_permissions.update(ExecutionTools.PERMISSION_LEVELS)

        server = N8nMCPServer(n8n_config)

        for name in server.get_tool_names():
            assert name in all_permissions, f"Tool {name} missing permission level"
            assert 1 <= all_permissions[name] <= 3
