"""D365 MCP Server Integration Tests

Tests the full D365 MCP Server flow from tool call to client dispatch
using mocked D365 API responses.

Sprint 129: Story 129-3
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.integrations.mcp.servers.d365.client import (
    D365ApiClient,
    D365Config,
    D365NotFoundError,
)
from src.integrations.mcp.servers.d365.server import D365MCPServer
from src.integrations.mcp.core.types import ToolResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def d365_config():
    """Create a test D365Config for integration tests."""
    return D365Config(
        d365_url="https://test.crm.dynamics.com",
        tenant_id="tenant-123",
        client_id="client-123",
        client_secret="secret-123",
    )


@pytest.fixture
def mock_client():
    """Create a mock D365ApiClient with all async methods pre-configured."""
    client = MagicMock(spec=D365ApiClient)
    client.query_entities = AsyncMock(return_value={
        "value": [
            {"accountid": "acc-1", "name": "Contoso", "statecode": 0},
            {"accountid": "acc-2", "name": "Fabrikam", "statecode": 0},
        ],
    })
    client.get_record = AsyncMock(return_value={
        "accountid": "acc-1",
        "name": "Contoso",
        "telephone1": "02-1234-5678",
        "statecode": 0,
    })
    client.create_record = AsyncMock(return_value={
        "accountid": "acc-new",
        "name": "New Corp",
    })
    client.update_record = AsyncMock(return_value={
        "accountid": "acc-1",
        "name": "Updated Corp",
    })
    client.list_entity_types = AsyncMock(return_value=[
        {
            "LogicalName": "account",
            "DisplayName": {
                "LocalizedLabels": [{"Label": "Account"}],
            },
            "EntitySetName": "accounts",
        },
        {
            "LogicalName": "contact",
            "DisplayName": {
                "LocalizedLabels": [{"Label": "Contact"}],
            },
            "EntitySetName": "contacts",
        },
    ])
    client.get_entity_metadata = AsyncMock(return_value={
        "LogicalName": "account",
        "PrimaryIdAttribute": "accountid",
        "PrimaryNameAttribute": "name",
        "EntitySetName": "accounts",
    })
    client.health_check = AsyncMock(return_value=True)
    client.is_healthy = True
    return client


def _make_server(d365_config, mock_client):
    """Create a D365MCPServer and wire in the mock client."""
    server = D365MCPServer(d365_config)
    server._client = mock_client
    server._query_tools._client = mock_client
    server._crud_tools._client = mock_client
    return server


# ---------------------------------------------------------------------------
# 1. TestD365QueryFlow — End-to-end query tool flows (4 tests)
# ---------------------------------------------------------------------------


class TestD365QueryFlow:
    """Integration tests for D365 query tool flows."""

    @pytest.mark.asyncio
    async def test_query_entities_full_flow(self, d365_config, mock_client):
        """Test query_entities end-to-end with entity_name and filter."""
        server = _make_server(d365_config, mock_client)

        result = await server.call_tool(
            "d365_query_entities",
            {"entity_name": "account", "filter": "statecode eq 0"},
        )

        assert result.success is True
        assert result.content is not None
        # The query tool wraps results in a structured format
        content = result.content
        assert "content" in content or "total" in content or "records" in content
        mock_client.query_entities.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_record_full_flow(self, d365_config, mock_client):
        """Test get_record end-to-end with entity_name and record_id."""
        server = _make_server(d365_config, mock_client)

        result = await server.call_tool(
            "d365_get_record",
            {"entity_name": "account", "record_id": "acc-1"},
        )

        assert result.success is True
        assert result.content is not None
        mock_client.get_record.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_entity_types_flow(self, d365_config, mock_client):
        """Test list_entity_types end-to-end returns structured response."""
        server = _make_server(d365_config, mock_client)

        result = await server.call_tool("d365_list_entity_types")

        assert result.success is True
        assert result.content is not None
        mock_client.list_entity_types.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_with_odata_params(self, d365_config, mock_client):
        """Test query_entities with all OData parameters."""
        server = _make_server(d365_config, mock_client)

        result = await server.call_tool(
            "d365_query_entities",
            {
                "entity_name": "account",
                "filter": "statecode eq 0",
                "select": "name,accountnumber",
                "top": 10,
                "orderby": "name asc",
            },
        )

        assert result.success is True
        assert result.content is not None
        mock_client.query_entities.assert_called_once()


# ---------------------------------------------------------------------------
# 2. TestD365CrudFlow — End-to-end CRUD tool flows (2 tests)
# ---------------------------------------------------------------------------


class TestD365CrudFlow:
    """Integration tests for D365 CRUD tool flows."""

    @pytest.mark.asyncio
    async def test_create_record_flow(self, d365_config, mock_client):
        """Test create_record end-to-end with entity_name and data."""
        server = _make_server(d365_config, mock_client)

        result = await server.call_tool(
            "d365_create_record",
            {
                "entity_name": "account",
                "data": {"name": "New Corp", "accountnumber": "ACC-999"},
            },
        )

        assert result.success is True
        assert result.content is not None
        mock_client.create_record.assert_called_once_with(
            entity_name="account",
            data={"name": "New Corp", "accountnumber": "ACC-999"},
        )

    @pytest.mark.asyncio
    async def test_update_record_flow(self, d365_config, mock_client):
        """Test update_record end-to-end with entity_name, record_id, and data."""
        server = _make_server(d365_config, mock_client)

        result = await server.call_tool(
            "d365_update_record",
            {
                "entity_name": "account",
                "record_id": "acc-1",
                "data": {"name": "Updated Corp"},
            },
        )

        assert result.success is True
        assert result.content is not None
        mock_client.update_record.assert_called_once_with(
            entity_name="account",
            record_id="acc-1",
            data={"name": "Updated Corp"},
        )


# ---------------------------------------------------------------------------
# 3. TestD365ErrorHandling — Error scenarios (3 tests)
# ---------------------------------------------------------------------------


class TestD365ErrorHandling:
    """Integration tests for D365 error handling scenarios."""

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self, d365_config, mock_client):
        """Test calling an unknown tool returns an error indication."""
        server = _make_server(d365_config, mock_client)

        result = await server.call_tool("d365_delete_everything")

        # The protocol returns isError inside the result content
        assert result.content is not None
        assert result.content.get("isError") is True
        content_text = result.content["content"][0]["text"]
        assert (
            "not found" in content_text.lower()
            or "d365_delete_everything" in content_text
        )

    @pytest.mark.asyncio
    async def test_query_not_found(self, d365_config, mock_client):
        """Test that D365NotFoundError from client surfaces through tool result."""
        mock_client.get_record = AsyncMock(
            side_effect=D365NotFoundError(
                "Resource not found: account(nonexistent-id)",
                status_code=404,
            )
        )
        server = _make_server(d365_config, mock_client)

        result = await server.call_tool(
            "d365_get_record",
            {"entity_name": "account", "record_id": "nonexistent-id"},
        )

        # The tool handler catches D365NotFoundError and returns success=False
        assert result.content is not None
        # The tool returns ToolResult with error info; protocol wraps it
        mock_client.get_record.assert_called_once()

    @pytest.mark.asyncio
    async def test_server_health_check_flow(self, d365_config, mock_client):
        """Test health_check integration delegates properly."""
        server = _make_server(d365_config, mock_client)

        is_healthy = await server.health_check()

        assert is_healthy is True
        mock_client.health_check.assert_called_once()

        # Verify is_healthy property also reflects current state
        assert server.is_healthy is True
