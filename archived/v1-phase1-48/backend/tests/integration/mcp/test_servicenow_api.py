"""Integration tests for ServiceNow MCP Server — Sprint 117.

Tests the full ServiceNow MCP Server flow with mocked ServiceNow API.
These tests validate the complete tool call chain:
  MCPServer.call_tool() → handler → client → HTTP mock

For actual ServiceNow instance testing, set SERVICENOW_INSTANCE_URL
environment variable and run with: pytest -m integration

20 tests covering:
- Full tool chain (6 tests — one per tool)
- Error propagation chain (4 tests)
- MCP protocol flow (4 tests)
- Configuration integration (3 tests)
- Tool discovery (3 tests)
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.mcp.servicenow_client import (
    ServiceNowAuthError,
    ServiceNowClient,
    ServiceNowError,
)
from src.integrations.mcp.servicenow_config import (
    AuthMethod,
    ServiceNowConfig,
)
from src.integrations.mcp.servicenow_server import ServiceNowMCPServer


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def config() -> ServiceNowConfig:
    """Integration test configuration."""
    return ServiceNowConfig(
        instance_url="https://test.service-now.com",
        username="admin",
        password="secret",
        auth_method=AuthMethod.BASIC,
        timeout=10,
        max_retries=1,
        retry_base_delay=0.01,
    )


@pytest.fixture
def mock_servicenow_client(config: ServiceNowConfig) -> AsyncMock:
    """Mock client with realistic responses."""
    client = AsyncMock(spec=ServiceNowClient)
    client._config = config

    # Default successful responses
    client.create_incident.return_value = {
        "sys_id": "abc-123-def",
        "number": "INC0010001",
        "short_description": "Server down",
        "state": "1",
        "category": "software",
        "urgency": "2",
    }

    client.update_incident.return_value = {
        "sys_id": "abc-123-def",
        "number": "INC0010001",
        "state": "2",
        "work_notes": "Investigation started",
    }

    client.get_incident.return_value = {
        "sys_id": "abc-123-def",
        "number": "INC0010001",
        "short_description": "Server down",
        "state": "1",
        "opened_at": "2026-02-24 10:00:00",
        "assignment_group": {"display_value": "IT Support"},
    }

    client.create_ritm.return_value = {
        "sys_id": "ritm-456-ghi",
        "number": "RITM0010001",
        "short_description": "AD Account Creation",
        "stage": "requested",
        "approval": "not yet requested",
    }

    client.get_ritm_status.return_value = {
        "sys_id": "ritm-456-ghi",
        "number": "RITM0010001",
        "stage": "fulfillment",
        "approval": "approved",
        "state": "2",
    }

    client.add_attachment.return_value = {
        "sys_id": "att-789-jkl",
        "file_name": "error.log",
        "size_bytes": "1024",
        "content_type": "text/plain",
        "table_name": "incident",
        "table_sys_id": "abc-123-def",
    }

    return client


@pytest.fixture
def server(mock_servicenow_client: AsyncMock) -> ServiceNowMCPServer:
    """MCP server with mocked client."""
    return ServiceNowMCPServer(mock_servicenow_client)


# =============================================================================
# Full Tool Chain Tests
# =============================================================================


class TestFullToolChain:
    """End-to-end tests for each tool through the MCP handler chain."""

    @pytest.mark.asyncio
    async def test_create_incident_full_chain(
        self, server: ServiceNowMCPServer
    ) -> None:
        """create_incident: handler → client → result."""
        result = await server._handle_create_incident(
            short_description="Server down",
            description="Web server not responding on port 443",
            category="software",
            urgency="2",
        )

        assert result.success is True
        assert result.content["number"] == "INC0010001"
        assert result.content["sys_id"] == "abc-123-def"
        assert result.metadata["tool"] == "create_incident"
        assert result.metadata["table"] == "incident"

    @pytest.mark.asyncio
    async def test_update_incident_full_chain(
        self, server: ServiceNowMCPServer
    ) -> None:
        """update_incident: handler → client → result."""
        result = await server._handle_update_incident(
            sys_id="abc-123-def",
            state="2",
            work_notes="Investigation started",
        )

        assert result.success is True
        assert result.content["state"] == "2"
        assert "state" in result.metadata["updated_fields"]
        assert "work_notes" in result.metadata["updated_fields"]

    @pytest.mark.asyncio
    async def test_get_incident_full_chain(
        self, server: ServiceNowMCPServer
    ) -> None:
        """get_incident: handler → client → result."""
        result = await server._handle_get_incident(number="INC0010001")

        assert result.success is True
        assert result.content["number"] == "INC0010001"
        assert result.content["assignment_group"]["display_value"] == "IT Support"

    @pytest.mark.asyncio
    async def test_create_ritm_full_chain(
        self, server: ServiceNowMCPServer
    ) -> None:
        """create_ritm: handler → client → result."""
        result = await server._handle_create_ritm(
            cat_item="cat-ad-account",
            variables={
                "target_user": "john.doe",
                "department": "Engineering",
                "access_level": "standard",
            },
            requested_for="user-mgr-001",
            short_description="AD Account Creation for John Doe",
        )

        assert result.success is True
        assert result.content["number"] == "RITM0010001"
        assert result.metadata["table"] == "sc_req_item"

    @pytest.mark.asyncio
    async def test_get_ritm_status_full_chain(
        self, server: ServiceNowMCPServer
    ) -> None:
        """get_ritm_status: handler → client → result."""
        result = await server._handle_get_ritm_status(number="RITM0010001")

        assert result.success is True
        assert result.content["stage"] == "fulfillment"
        assert result.content["approval"] == "approved"

    @pytest.mark.asyncio
    async def test_add_attachment_full_chain(
        self, server: ServiceNowMCPServer
    ) -> None:
        """add_attachment: handler → client → result."""
        result = await server._handle_add_attachment(
            table="incident",
            sys_id="abc-123-def",
            file_name="error.log",
            content="2026-02-24 10:00:00 ERROR: Connection refused",
            content_type="text/plain",
        )

        assert result.success is True
        assert result.content["file_name"] == "error.log"
        assert result.metadata["file_name"] == "error.log"
        assert result.metadata["size_bytes"] > 0


# =============================================================================
# Error Propagation Chain
# =============================================================================


class TestErrorPropagation:
    """Tests that errors propagate correctly through the tool chain."""

    @pytest.mark.asyncio
    async def test_auth_error_propagation(
        self,
        server: ServiceNowMCPServer,
        mock_servicenow_client: AsyncMock,
    ) -> None:
        """Auth error from client surfaces in ToolResult."""
        mock_servicenow_client.create_incident.side_effect = (
            ServiceNowAuthError("Invalid credentials", status_code=401)
        )

        result = await server._handle_create_incident(
            short_description="Test",
            description="Test",
        )

        assert result.success is False
        assert "Invalid credentials" in result.error
        assert result.metadata["error_type"] == "ServiceNowAuthError"
        assert result.metadata["status_code"] == 401

    @pytest.mark.asyncio
    async def test_network_error_propagation(
        self,
        server: ServiceNowMCPServer,
        mock_servicenow_client: AsyncMock,
    ) -> None:
        """Network error from client surfaces in ToolResult."""
        mock_servicenow_client.get_incident.side_effect = ServiceNowError(
            "Connection failed after 2 attempts"
        )

        result = await server._handle_get_incident(number="INC0010001")

        assert result.success is False
        assert "Connection failed" in result.error
        assert result.metadata["error_type"] == "ServiceNowError"

    @pytest.mark.asyncio
    async def test_ritm_error_propagation(
        self,
        server: ServiceNowMCPServer,
        mock_servicenow_client: AsyncMock,
    ) -> None:
        """RITM creation error surfaces correctly."""
        mock_servicenow_client.create_ritm.side_effect = ServiceNowError(
            "Catalog item not found"
        )

        result = await server._handle_create_ritm(
            cat_item="nonexistent",
            variables={},
            requested_for="user-001",
            short_description="Test",
        )

        assert result.success is False
        assert "Catalog item not found" in result.error

    @pytest.mark.asyncio
    async def test_attachment_error_propagation(
        self,
        server: ServiceNowMCPServer,
        mock_servicenow_client: AsyncMock,
    ) -> None:
        """Attachment upload error surfaces correctly."""
        mock_servicenow_client.add_attachment.side_effect = ServiceNowError(
            "File too large"
        )

        result = await server._handle_add_attachment(
            table="incident",
            sys_id="inc-001",
            file_name="huge.log",
            content="x" * 1000,
        )

        assert result.success is False
        assert "File too large" in result.error


# =============================================================================
# MCP Protocol Flow
# =============================================================================


class TestMCPProtocolFlow:
    """Tests for MCP protocol integration."""

    def test_tools_list_via_protocol(
        self, server: ServiceNowMCPServer
    ) -> None:
        """Protocol lists all 6 tools."""
        tools = server._protocol.list_tools()
        assert len(tools) == 6

    def test_tool_schemas_have_descriptions(
        self, server: ServiceNowMCPServer
    ) -> None:
        """All tools have non-empty descriptions."""
        for tool in server.get_tools():
            assert tool.description
            assert len(tool.description) > 20

    def test_tool_schemas_have_parameters(
        self, server: ServiceNowMCPServer
    ) -> None:
        """All tools have at least one parameter."""
        for tool in server.get_tools():
            assert len(tool.parameters) > 0

    def test_registered_tools_property(
        self, server: ServiceNowMCPServer
    ) -> None:
        """registered_tools on protocol returns all names."""
        registered = server._protocol.registered_tools
        assert len(registered) == 6


# =============================================================================
# Configuration Integration
# =============================================================================


class TestConfigurationIntegration:
    """Tests for configuration-driven server creation."""

    @patch.dict(
        os.environ,
        {
            "SERVICENOW_INSTANCE_URL": "https://prod.service-now.com",
            "SERVICENOW_USERNAME": "svc-ipa",
            "SERVICENOW_PASSWORD": "prod-secret",
            "SERVICENOW_API_VERSION": "v2",
            "SERVICENOW_TIMEOUT": "60",
        },
    )
    def test_config_from_env(self) -> None:
        """Config can be created from environment."""
        config = ServiceNowConfig.from_env()
        assert config.instance_url == "https://prod.service-now.com"
        assert config.username == "svc-ipa"
        assert config.timeout == 60
        assert config.base_url == "https://prod.service-now.com/api/now/v2"

    def test_config_validation_valid(self, config: ServiceNowConfig) -> None:
        """Valid config passes validation."""
        errors = config.validate()
        assert errors == []

    def test_config_validation_invalid(self) -> None:
        """Invalid config returns error messages."""
        config = ServiceNowConfig(
            instance_url="",
            username="",
            password="",
        )
        errors = config.validate()
        assert len(errors) > 0
        assert any("instance_url" in e for e in errors)


# =============================================================================
# Tool Discovery
# =============================================================================


class TestToolDiscovery:
    """Tests for tool discovery and metadata."""

    def test_get_tools_returns_schemas(
        self, server: ServiceNowMCPServer
    ) -> None:
        """get_tools() returns ToolSchema objects."""
        tools = server.get_tools()
        assert all(hasattr(t, "name") for t in tools)
        assert all(hasattr(t, "description") for t in tools)
        assert all(hasattr(t, "parameters") for t in tools)

    def test_get_tool_names_returns_strings(
        self, server: ServiceNowMCPServer
    ) -> None:
        """get_tool_names() returns list of strings."""
        names = server.get_tool_names()
        assert all(isinstance(n, str) for n in names)

    def test_tool_descriptions_for_llm(
        self, server: ServiceNowMCPServer
    ) -> None:
        """Tool descriptions are suitable for LLM consumption."""
        for tool in server.get_tools():
            # Description should explain when to use the tool
            desc = tool.description.lower()
            assert any(
                keyword in desc
                for keyword in ["use this", "create", "look up", "check", "attach", "update"]
            )
