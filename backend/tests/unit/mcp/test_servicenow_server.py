"""Unit tests for ServiceNow MCP Server — Sprint 117.

Tests MCP tool registration, handler execution, schema correctness,
and tool list export for the ServiceNow MCP Server.

38 tests covering:
- Server initialization (4 tests)
- Tool registration (5 tests)
- Tool schema correctness (6 tests)
- create_incident handler (4 tests)
- update_incident handler (4 tests)
- get_incident handler (4 tests)
- create_ritm handler (3 tests)
- get_ritm_status handler (3 tests)
- add_attachment handler (3 tests)
- Context manager (2 tests)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.mcp.servicenow_client import (
    ServiceNowAuthError,
    ServiceNowClient,
    ServiceNowError,
    ServiceNowNotFoundError,
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
    """Test configuration."""
    return ServiceNowConfig(
        instance_url="https://test.service-now.com",
        username="admin",
        password="secret",
        auth_method=AuthMethod.BASIC,
    )


@pytest.fixture
def mock_client() -> AsyncMock:
    """Mock ServiceNowClient."""
    client = AsyncMock(spec=ServiceNowClient)
    client._config = ServiceNowConfig(
        instance_url="https://test.service-now.com",
        username="admin",
        password="secret",
    )
    return client


@pytest.fixture
def server(mock_client: AsyncMock) -> ServiceNowMCPServer:
    """ServiceNow MCP Server with mocked client."""
    return ServiceNowMCPServer(mock_client)


# =============================================================================
# Server Initialization
# =============================================================================


class TestServerInitialization:
    """Tests for ServiceNowMCPServer initialization."""

    def test_server_name(self, server: ServiceNowMCPServer) -> None:
        """Server has correct name."""
        assert server.SERVER_NAME == "servicenow-mcp"

    def test_server_version(self, server: ServiceNowMCPServer) -> None:
        """Server has correct version."""
        assert server.SERVER_VERSION == "1.0.0"

    def test_running_flag_initially_false(
        self, server: ServiceNowMCPServer
    ) -> None:
        """Server is not running initially."""
        assert server._running is False

    def test_protocol_initialized(self, server: ServiceNowMCPServer) -> None:
        """MCP protocol handler is initialized."""
        assert server._protocol is not None


# =============================================================================
# Tool Registration
# =============================================================================


class TestToolRegistration:
    """Tests for tool registration in MCP protocol."""

    def test_registers_six_tools(self, server: ServiceNowMCPServer) -> None:
        """Exactly 6 tools are registered."""
        tools = server.get_tools()
        assert len(tools) == 6

    def test_all_tool_names(self, server: ServiceNowMCPServer) -> None:
        """All 6 expected tool names are registered."""
        names = server.get_tool_names()
        expected = {
            "create_incident",
            "update_incident",
            "get_incident",
            "create_ritm",
            "get_ritm_status",
            "add_attachment",
        }
        assert set(names) == expected

    def test_static_schemas_match_registered(
        self, server: ServiceNowMCPServer
    ) -> None:
        """Static get_tool_schemas() matches registered tools."""
        static_schemas = ServiceNowMCPServer.get_tool_schemas()
        registered_tools = server.get_tools()
        static_names = {s.name for s in static_schemas}
        registered_names = {t.name for t in registered_tools}
        assert static_names == registered_names

    def test_permission_levels_set(self, server: ServiceNowMCPServer) -> None:
        """Permission levels are defined for all tools."""
        for name in server.get_tool_names():
            assert name in server.PERMISSION_LEVELS

    def test_read_tools_have_lower_permission(
        self, server: ServiceNowMCPServer
    ) -> None:
        """Read-only tools (get_*) have permission level 1."""
        assert server.PERMISSION_LEVELS["get_incident"] == 1
        assert server.PERMISSION_LEVELS["get_ritm_status"] == 1


# =============================================================================
# Tool Schema Correctness
# =============================================================================


class TestToolSchemas:
    """Tests for tool schema definitions."""

    def test_create_incident_required_params(
        self, server: ServiceNowMCPServer
    ) -> None:
        """create_incident has correct required parameters."""
        schemas = {s.name: s for s in server.get_tools()}
        schema = schemas["create_incident"]
        required_names = [p.name for p in schema.parameters if p.required]
        assert "short_description" in required_names
        assert "description" in required_names

    def test_create_incident_optional_params(
        self, server: ServiceNowMCPServer
    ) -> None:
        """create_incident has optional category, urgency, etc."""
        schemas = {s.name: s for s in server.get_tools()}
        schema = schemas["create_incident"]
        optional_names = [p.name for p in schema.parameters if not p.required]
        assert "category" in optional_names
        assert "urgency" in optional_names

    def test_update_incident_sys_id_required(
        self, server: ServiceNowMCPServer
    ) -> None:
        """update_incident requires sys_id."""
        schemas = {s.name: s for s in server.get_tools()}
        schema = schemas["update_incident"]
        required_names = [p.name for p in schema.parameters if p.required]
        assert "sys_id" in required_names

    def test_get_incident_both_optional(
        self, server: ServiceNowMCPServer
    ) -> None:
        """get_incident has number and sys_id both optional."""
        schemas = {s.name: s for s in server.get_tools()}
        schema = schemas["get_incident"]
        required_names = [p.name for p in schema.parameters if p.required]
        assert len(required_names) == 0

    def test_create_ritm_required_params(
        self, server: ServiceNowMCPServer
    ) -> None:
        """create_ritm has all 4 required params."""
        schemas = {s.name: s for s in server.get_tools()}
        schema = schemas["create_ritm"]
        required_names = [p.name for p in schema.parameters if p.required]
        assert set(required_names) == {
            "cat_item",
            "variables",
            "requested_for",
            "short_description",
        }

    def test_add_attachment_table_enum(
        self, server: ServiceNowMCPServer
    ) -> None:
        """add_attachment table parameter has enum values."""
        schemas = {s.name: s for s in server.get_tools()}
        schema = schemas["add_attachment"]
        table_param = next(p for p in schema.parameters if p.name == "table")
        assert "incident" in table_param.enum
        assert "sc_req_item" in table_param.enum


# =============================================================================
# create_incident Handler
# =============================================================================


class TestCreateIncidentHandler:
    """Tests for create_incident tool handler."""

    @pytest.mark.asyncio
    async def test_success(
        self, server: ServiceNowMCPServer, mock_client: AsyncMock
    ) -> None:
        """Successful creation returns ToolResult with content."""
        mock_client.create_incident.return_value = {
            "sys_id": "inc-001",
            "number": "INC0010001",
        }

        result = await server._handle_create_incident(
            short_description="Server down",
            description="Web server not responding",
        )

        assert result.success is True
        assert result.content["number"] == "INC0010001"
        assert result.metadata["tool"] == "create_incident"

    @pytest.mark.asyncio
    async def test_with_optional_params(
        self, server: ServiceNowMCPServer, mock_client: AsyncMock
    ) -> None:
        """Optional parameters passed through."""
        mock_client.create_incident.return_value = {"sys_id": "inc-001"}

        await server._handle_create_incident(
            short_description="Test",
            description="Test",
            category="software",
            urgency="1",
            assignment_group="grp-001",
            caller_id="user-001",
        )

        mock_client.create_incident.assert_called_once_with(
            short_description="Test",
            description="Test",
            category="software",
            urgency="1",
            assignment_group="grp-001",
            caller_id="user-001",
        )

    @pytest.mark.asyncio
    async def test_auth_error_returns_failure(
        self, server: ServiceNowMCPServer, mock_client: AsyncMock
    ) -> None:
        """Auth error returns ToolResult with error."""
        mock_client.create_incident.side_effect = ServiceNowAuthError(
            "Invalid credentials", status_code=401
        )

        result = await server._handle_create_incident(
            short_description="Test",
            description="Test",
        )

        assert result.success is False
        assert "Invalid credentials" in result.error
        assert result.metadata["status_code"] == 401

    @pytest.mark.asyncio
    async def test_generic_error_returns_failure(
        self, server: ServiceNowMCPServer, mock_client: AsyncMock
    ) -> None:
        """Generic ServiceNowError returns ToolResult with error."""
        mock_client.create_incident.side_effect = ServiceNowError("Network error")

        result = await server._handle_create_incident(
            short_description="Test",
            description="Test",
        )

        assert result.success is False
        assert "Network error" in result.error


# =============================================================================
# update_incident Handler
# =============================================================================


class TestUpdateIncidentHandler:
    """Tests for update_incident tool handler."""

    @pytest.mark.asyncio
    async def test_success(
        self, server: ServiceNowMCPServer, mock_client: AsyncMock
    ) -> None:
        """Successful update returns ToolResult."""
        mock_client.update_incident.return_value = {
            "sys_id": "inc-001",
            "state": "2",
        }

        result = await server._handle_update_incident(
            sys_id="inc-001",
            state="2",
            work_notes="Investigating",
        )

        assert result.success is True
        assert "state" in result.metadata["updated_fields"]
        assert "work_notes" in result.metadata["updated_fields"]

    @pytest.mark.asyncio
    async def test_no_updates_returns_error(
        self, server: ServiceNowMCPServer
    ) -> None:
        """No update fields provided returns error."""
        result = await server._handle_update_incident(sys_id="inc-001")

        assert result.success is False
        assert "No update fields" in result.error

    @pytest.mark.asyncio
    async def test_filters_none_values(
        self, server: ServiceNowMCPServer, mock_client: AsyncMock
    ) -> None:
        """None values are filtered from updates."""
        mock_client.update_incident.return_value = {"sys_id": "inc-001"}

        await server._handle_update_incident(
            sys_id="inc-001",
            state="2",
            comments=None,
        )

        call_args = mock_client.update_incident.call_args
        updates = call_args[0][1]
        assert "comments" not in updates
        assert "state" in updates

    @pytest.mark.asyncio
    async def test_not_found_error(
        self, server: ServiceNowMCPServer, mock_client: AsyncMock
    ) -> None:
        """Not found error returns ToolResult with error."""
        mock_client.update_incident.side_effect = ServiceNowNotFoundError(
            "Record not found", status_code=404
        )

        result = await server._handle_update_incident(
            sys_id="nonexistent",
            state="2",
        )

        assert result.success is False
        assert result.metadata["status_code"] == 404


# =============================================================================
# get_incident Handler
# =============================================================================


class TestGetIncidentHandler:
    """Tests for get_incident tool handler."""

    @pytest.mark.asyncio
    async def test_found_by_number(
        self, server: ServiceNowMCPServer, mock_client: AsyncMock
    ) -> None:
        """Found incident returns ToolResult with content."""
        mock_client.get_incident.return_value = {
            "sys_id": "inc-001",
            "number": "INC0010001",
        }

        result = await server._handle_get_incident(number="INC0010001")

        assert result.success is True
        assert result.content["number"] == "INC0010001"

    @pytest.mark.asyncio
    async def test_not_found(
        self, server: ServiceNowMCPServer, mock_client: AsyncMock
    ) -> None:
        """Not found returns ToolResult with None content."""
        mock_client.get_incident.return_value = None

        result = await server._handle_get_incident(number="INC9999999")

        assert result.success is True
        assert result.content is None
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_missing_identifiers(
        self, server: ServiceNowMCPServer
    ) -> None:
        """Neither number nor sys_id returns error."""
        result = await server._handle_get_incident()

        assert result.success is False
        assert "number" in result.error and "sys_id" in result.error

    @pytest.mark.asyncio
    async def test_api_error(
        self, server: ServiceNowMCPServer, mock_client: AsyncMock
    ) -> None:
        """API error returns ToolResult with error."""
        mock_client.get_incident.side_effect = ServiceNowError("API timeout")

        result = await server._handle_get_incident(number="INC0010001")

        assert result.success is False
        assert "API timeout" in result.error


# =============================================================================
# create_ritm Handler
# =============================================================================


class TestCreateRITMHandler:
    """Tests for create_ritm tool handler."""

    @pytest.mark.asyncio
    async def test_success(
        self, server: ServiceNowMCPServer, mock_client: AsyncMock
    ) -> None:
        """Successful RITM creation."""
        mock_client.create_ritm.return_value = {
            "sys_id": "ritm-001",
            "number": "RITM0010001",
        }

        result = await server._handle_create_ritm(
            cat_item="cat-001",
            variables={"target_user": "john"},
            requested_for="user-001",
            short_description="AD Account",
        )

        assert result.success is True
        assert result.content["number"] == "RITM0010001"

    @pytest.mark.asyncio
    async def test_variables_as_json_string(
        self, server: ServiceNowMCPServer, mock_client: AsyncMock
    ) -> None:
        """Variables passed as JSON string are parsed."""
        mock_client.create_ritm.return_value = {"sys_id": "ritm-001"}

        await server._handle_create_ritm(
            cat_item="cat-001",
            variables='{"target_user": "john"}',
            requested_for="user-001",
            short_description="Test",
        )

        call_args = mock_client.create_ritm.call_args
        assert call_args.kwargs["variables"] == {"target_user": "john"}

    @pytest.mark.asyncio
    async def test_error_handling(
        self, server: ServiceNowMCPServer, mock_client: AsyncMock
    ) -> None:
        """Error returns ToolResult with error."""
        mock_client.create_ritm.side_effect = ServiceNowError("Failed")

        result = await server._handle_create_ritm(
            cat_item="cat-001",
            variables={},
            requested_for="user-001",
            short_description="Test",
        )

        assert result.success is False


# =============================================================================
# get_ritm_status Handler
# =============================================================================


class TestGetRITMStatusHandler:
    """Tests for get_ritm_status tool handler."""

    @pytest.mark.asyncio
    async def test_found(
        self, server: ServiceNowMCPServer, mock_client: AsyncMock
    ) -> None:
        """Found RITM returns ToolResult with content."""
        mock_client.get_ritm_status.return_value = {
            "sys_id": "ritm-001",
            "stage": "fulfillment",
        }

        result = await server._handle_get_ritm_status(number="RITM0010001")

        assert result.success is True
        assert result.content["stage"] == "fulfillment"

    @pytest.mark.asyncio
    async def test_not_found(
        self, server: ServiceNowMCPServer, mock_client: AsyncMock
    ) -> None:
        """Not found RITM returns None content."""
        mock_client.get_ritm_status.return_value = None

        result = await server._handle_get_ritm_status(number="RITM9999999")

        assert result.success is True
        assert result.content is None

    @pytest.mark.asyncio
    async def test_missing_identifiers(
        self, server: ServiceNowMCPServer
    ) -> None:
        """Missing identifiers returns error."""
        result = await server._handle_get_ritm_status()

        assert result.success is False


# =============================================================================
# add_attachment Handler
# =============================================================================


class TestAddAttachmentHandler:
    """Tests for add_attachment tool handler."""

    @pytest.mark.asyncio
    async def test_success(
        self, server: ServiceNowMCPServer, mock_client: AsyncMock
    ) -> None:
        """Successful attachment upload."""
        mock_client.add_attachment.return_value = {
            "sys_id": "att-001",
            "file_name": "log.txt",
        }

        result = await server._handle_add_attachment(
            table="incident",
            sys_id="inc-001",
            file_name="log.txt",
            content="Error log content here",
        )

        assert result.success is True
        assert result.metadata["file_name"] == "log.txt"
        assert result.metadata["size_bytes"] > 0

    @pytest.mark.asyncio
    async def test_content_encoded_to_bytes(
        self, server: ServiceNowMCPServer, mock_client: AsyncMock
    ) -> None:
        """String content is encoded to bytes."""
        mock_client.add_attachment.return_value = {"sys_id": "att-001"}

        await server._handle_add_attachment(
            table="incident",
            sys_id="inc-001",
            file_name="test.txt",
            content="Hello world",
        )

        call_args = mock_client.add_attachment.call_args
        assert isinstance(call_args.kwargs["content"], bytes)

    @pytest.mark.asyncio
    async def test_error_handling(
        self, server: ServiceNowMCPServer, mock_client: AsyncMock
    ) -> None:
        """Error returns ToolResult with error."""
        mock_client.add_attachment.side_effect = ServiceNowError("Upload failed")

        result = await server._handle_add_attachment(
            table="incident",
            sys_id="inc-001",
            file_name="test.txt",
            content="content",
        )

        assert result.success is False
        assert "Upload failed" in result.error


# =============================================================================
# Context Manager
# =============================================================================


class TestContextManager:
    """Tests for context manager support."""

    def test_sync_context_manager(
        self, mock_client: AsyncMock
    ) -> None:
        """Sync context manager sets running flag."""
        server = ServiceNowMCPServer(mock_client)
        with server:
            assert server._running is True
        assert server._running is False

    @pytest.mark.asyncio
    async def test_async_context_manager(
        self, mock_client: AsyncMock
    ) -> None:
        """Async context manager manages client lifecycle."""
        server = ServiceNowMCPServer(mock_client)
        async with server:
            assert server._running is True
        assert server._running is False
        mock_client.__aexit__.assert_called()
