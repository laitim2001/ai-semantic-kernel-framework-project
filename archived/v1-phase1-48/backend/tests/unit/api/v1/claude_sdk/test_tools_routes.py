"""Tests for Claude SDK Tools API routes.

Sprint 51: S51-1 Tools API Routes Unit Tests
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.v1.claude_sdk.tools_routes import router


# Create test app
app = FastAPI()
app.include_router(router, prefix="/api/v1/claude-sdk")


class TestToolsRoutes:
    """Tests for Claude SDK Tools API routes."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_tool(self):
        """Create a mock tool instance."""
        mock = MagicMock()
        mock.name = "TestTool"
        mock.description = "A test tool"
        mock.get_schema.return_value = {
            "properties": {
                "input": {"type": "string", "description": "Input value"},
                "count": {"type": "integer", "description": "Count value"},
            },
            "required": ["input"],
        }
        return mock


class TestListToolsEndpoint(TestToolsRoutes):
    """Tests for GET /tools endpoint."""

    def test_list_tools_empty(self, client):
        """Test listing tools when none are registered."""
        with patch(
            "src.api.v1.claude_sdk.tools_routes.get_available_tools",
            return_value=[],
        ):
            response = client.get("/api/v1/claude-sdk/tools")
            assert response.status_code == 200
            data = response.json()
            assert data["tools"] == []
            assert data["total"] == 0

    def test_list_tools_success(self, client, mock_tool):
        """Test listing tools successfully."""
        with patch(
            "src.api.v1.claude_sdk.tools_routes.get_available_tools",
            return_value=["TestTool"],
        ), patch(
            "src.api.v1.claude_sdk.tools_routes.get_tool_instance",
            return_value=mock_tool,
        ):
            response = client.get("/api/v1/claude-sdk/tools")
            assert response.status_code == 200
            data = response.json()
            assert len(data["tools"]) == 1
            assert data["tools"][0]["name"] == "TestTool"
            assert data["total"] == 1

    def test_list_tools_filter_by_category(self, client, mock_tool):
        """Test filtering tools by category."""
        mock_tool.name = "Read"
        with patch(
            "src.api.v1.claude_sdk.tools_routes.get_available_tools",
            return_value=["Read"],
        ), patch(
            "src.api.v1.claude_sdk.tools_routes.get_tool_instance",
            return_value=mock_tool,
        ):
            response = client.get("/api/v1/claude-sdk/tools?category=file")
            assert response.status_code == 200
            data = response.json()
            assert len(data["tools"]) == 1
            assert data["tools"][0]["category"] == "file"


class TestGetToolEndpoint(TestToolsRoutes):
    """Tests for GET /tools/{name} endpoint."""

    def test_get_tool_success(self, client, mock_tool):
        """Test getting a specific tool."""
        with patch(
            "src.api.v1.claude_sdk.tools_routes.get_tool_instance",
            return_value=mock_tool,
        ):
            response = client.get("/api/v1/claude-sdk/tools/TestTool")
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "TestTool"
            assert data["description"] == "A test tool"
            assert len(data["parameters"]) == 2

    def test_get_tool_not_found(self, client):
        """Test getting a non-existent tool."""
        with patch(
            "src.api.v1.claude_sdk.tools_routes.get_tool_instance",
            return_value=None,
        ):
            response = client.get("/api/v1/claude-sdk/tools/NonExistent")
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


class TestExecuteToolEndpoint(TestToolsRoutes):
    """Tests for POST /tools/execute endpoint."""

    def test_execute_tool_success(self, client, mock_tool):
        """Test executing a tool successfully."""
        with patch(
            "src.api.v1.claude_sdk.tools_routes.get_tool_instance",
            return_value=mock_tool,
        ), patch(
            "src.api.v1.claude_sdk.tools_routes.execute_tool",
            new_callable=AsyncMock,
            return_value="Execution result",
        ):
            response = client.post(
                "/api/v1/claude-sdk/tools/execute",
                json={"tool_name": "TestTool", "arguments": {"input": "test"}},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["content"] == "Execution result"

    def test_execute_tool_not_found(self, client):
        """Test executing a non-existent tool."""
        with patch(
            "src.api.v1.claude_sdk.tools_routes.get_tool_instance",
            return_value=None,
        ):
            response = client.post(
                "/api/v1/claude-sdk/tools/execute",
                json={"tool_name": "NonExistent", "arguments": {}},
            )
            assert response.status_code == 404

    def test_execute_tool_requires_approval(self, client, mock_tool):
        """Test tool that requires approval."""
        mock_tool.name = "Write"
        with patch(
            "src.api.v1.claude_sdk.tools_routes.get_tool_instance",
            return_value=mock_tool,
        ):
            response = client.post(
                "/api/v1/claude-sdk/tools/execute",
                json={
                    "tool_name": "Write",
                    "arguments": {},
                    "require_approval": True,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "approval" in data["error"].lower()

    def test_execute_tool_error_handling(self, client, mock_tool):
        """Test tool execution error handling."""
        with patch(
            "src.api.v1.claude_sdk.tools_routes.get_tool_instance",
            return_value=mock_tool,
        ), patch(
            "src.api.v1.claude_sdk.tools_routes.execute_tool",
            new_callable=AsyncMock,
            return_value="Error: Something went wrong",
        ):
            response = client.post(
                "/api/v1/claude-sdk/tools/execute",
                json={"tool_name": "TestTool", "arguments": {}},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "Error:" in data["error"]


class TestValidateToolEndpoint(TestToolsRoutes):
    """Tests for POST /tools/validate endpoint."""

    def test_validate_tool_success(self, client, mock_tool):
        """Test validating valid tool parameters."""
        with patch(
            "src.api.v1.claude_sdk.tools_routes.get_tool_instance",
            return_value=mock_tool,
        ):
            response = client.post(
                "/api/v1/claude-sdk/tools/validate",
                json={
                    "tool_name": "TestTool",
                    "arguments": {"input": "test", "count": 5},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["errors"] == []

    def test_validate_tool_missing_required(self, client, mock_tool):
        """Test validating with missing required parameter."""
        with patch(
            "src.api.v1.claude_sdk.tools_routes.get_tool_instance",
            return_value=mock_tool,
        ):
            response = client.post(
                "/api/v1/claude-sdk/tools/validate",
                json={"tool_name": "TestTool", "arguments": {"count": 5}},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert len(data["errors"]) > 0
            assert any("input" in e["parameter"] for e in data["errors"])

    def test_validate_tool_unknown_parameter(self, client, mock_tool):
        """Test validating with unknown parameter."""
        with patch(
            "src.api.v1.claude_sdk.tools_routes.get_tool_instance",
            return_value=mock_tool,
        ):
            response = client.post(
                "/api/v1/claude-sdk/tools/validate",
                json={
                    "tool_name": "TestTool",
                    "arguments": {"input": "test", "unknown_param": "value"},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert any("unknown" in e["parameter"].lower() for e in data["errors"])

    def test_validate_tool_wrong_type(self, client, mock_tool):
        """Test validating with wrong parameter type."""
        with patch(
            "src.api.v1.claude_sdk.tools_routes.get_tool_instance",
            return_value=mock_tool,
        ):
            response = client.post(
                "/api/v1/claude-sdk/tools/validate",
                json={
                    "tool_name": "TestTool",
                    "arguments": {"input": "test", "count": "not_an_integer"},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert any("count" in e["parameter"] for e in data["errors"])

    def test_validate_tool_not_found(self, client):
        """Test validating non-existent tool."""
        with patch(
            "src.api.v1.claude_sdk.tools_routes.get_tool_instance",
            return_value=None,
        ):
            response = client.post(
                "/api/v1/claude-sdk/tools/validate",
                json={"tool_name": "NonExistent", "arguments": {}},
            )
            assert response.status_code == 404


class TestToolCategoryMapping:
    """Tests for tool category mapping helper."""

    def test_file_tools(self):
        """Test file tool categorization."""
        from src.api.v1.claude_sdk.tools_routes import _get_tool_category

        assert _get_tool_category("Read") == "file"
        assert _get_tool_category("Write") == "file"
        assert _get_tool_category("Edit") == "file"
        assert _get_tool_category("MultiEdit") == "file"
        assert _get_tool_category("Glob") == "file"

    def test_command_tools(self):
        """Test command tool categorization."""
        from src.api.v1.claude_sdk.tools_routes import _get_tool_category

        assert _get_tool_category("Bash") == "command"
        assert _get_tool_category("Grep") == "command"

    def test_agent_tools(self):
        """Test agent tool categorization."""
        from src.api.v1.claude_sdk.tools_routes import _get_tool_category

        assert _get_tool_category("Task") == "agent"

    def test_web_tools(self):
        """Test web tool categorization."""
        from src.api.v1.claude_sdk.tools_routes import _get_tool_category

        assert _get_tool_category("WebSearch") == "web"
        assert _get_tool_category("WebFetch") == "web"

    def test_other_tools(self):
        """Test other tool categorization."""
        from src.api.v1.claude_sdk.tools_routes import _get_tool_category

        assert _get_tool_category("UnknownTool") == "other"


class TestToolApprovalRequirement:
    """Tests for tool approval requirement helper."""

    def test_approval_required_tools(self):
        """Test tools that require approval."""
        from src.api.v1.claude_sdk.tools_routes import _tool_requires_approval

        assert _tool_requires_approval("Write") is True
        assert _tool_requires_approval("Edit") is True
        assert _tool_requires_approval("MultiEdit") is True
        assert _tool_requires_approval("Bash") is True

    def test_no_approval_required_tools(self):
        """Test tools that don't require approval."""
        from src.api.v1.claude_sdk.tools_routes import _tool_requires_approval

        assert _tool_requires_approval("Read") is False
        assert _tool_requires_approval("Glob") is False
        assert _tool_requires_approval("Grep") is False
        assert _tool_requires_approval("WebSearch") is False
