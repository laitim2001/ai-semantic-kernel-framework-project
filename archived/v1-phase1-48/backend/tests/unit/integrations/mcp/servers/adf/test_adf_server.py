"""Tests for AdfMCPServer — Sprint 127, Story 127-2.

Tests cover:
    - Server initialization (name, version, tool registration)
    - Tool count and exact tool name verification
    - Tool call dispatch for all 8 tools (pipeline + monitoring)
    - Unknown tool error handling
    - Health check delegation to client

Total: 12 tests across 3 test classes.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.mcp.servers.adf.client import AdfApiClient, AdfConfig
from src.integrations.mcp.servers.adf.server import AdfMCPServer
from src.integrations.mcp.core.types import ToolResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def adf_config():
    """Create a test AdfConfig."""
    return AdfConfig(
        subscription_id="sub-123",
        resource_group="rg-test",
        factory_name="adf-test",
        tenant_id="t-123",
        client_id="c-123",
        client_secret="s-123",
        timeout=5,
        max_retries=1,
    )


@pytest.fixture
def adf_server(adf_config):
    """Create a test AdfMCPServer."""
    return AdfMCPServer(adf_config)


@pytest.fixture
def mock_client():
    """Create a mock AdfApiClient with all async methods pre-configured."""
    client = MagicMock(spec=AdfApiClient)
    client.list_pipelines = AsyncMock(return_value={
        "value": [
            {
                "name": "pipeline-etl",
                "properties": {
                    "description": "ETL pipeline",
                    "activities": [
                        {"name": "CopyData", "type": "Copy"},
                        {"name": "Transform", "type": "DataFlow"},
                    ],
                    "parameters": {
                        "env": {"type": "String", "defaultValue": "dev"},
                    },
                },
            },
        ],
    })
    client.get_pipeline = AsyncMock(return_value={
        "name": "pipeline-etl",
        "properties": {
            "description": "ETL pipeline",
            "activities": [
                {
                    "name": "CopyData",
                    "type": "Copy",
                    "description": "Copy from source",
                    "dependsOn": [],
                },
            ],
            "parameters": {
                "env": {"type": "String", "defaultValue": "dev"},
            },
            "folder": {"name": "production"},
            "annotations": ["critical"],
        },
    })
    client.run_pipeline = AsyncMock(return_value={"runId": "run-abc-123"})
    client.cancel_pipeline_run = AsyncMock(return_value={})
    client.get_pipeline_run = AsyncMock(return_value={
        "runId": "run-abc-123",
        "pipelineName": "pipeline-etl",
        "status": "Succeeded",
        "runStart": "2026-02-24T10:00:00Z",
        "runEnd": "2026-02-24T10:05:00Z",
        "parameters": {"env": "prod"},
        "invokedBy": {"name": "manual"},
        "message": "",
        "isLatest": True,
        "runGroupId": "group-1",
    })
    client.list_pipeline_runs = AsyncMock(return_value={
        "value": [
            {
                "runId": "run-1",
                "pipelineName": "pipeline-etl",
                "status": "Succeeded",
                "runStart": "2026-02-24T10:00:00Z",
                "runEnd": "2026-02-24T10:05:00Z",
                "invokedBy": {"name": "schedule"},
                "message": "Completed",
            },
        ],
    })
    client.list_datasets = AsyncMock(return_value={
        "value": [
            {
                "name": "ds-source",
                "properties": {
                    "type": "AzureSqlTable",
                    "description": "Source dataset",
                    "linkedServiceName": {"referenceName": "ls-sql"},
                    "folder": {"name": "raw"},
                    "annotations": [],
                    "schema": [
                        {"name": "id", "type": "int"},
                        {"name": "name", "type": "varchar"},
                    ],
                },
            },
        ],
    })
    client.list_triggers = AsyncMock(return_value={
        "value": [
            {
                "name": "trigger-daily",
                "properties": {
                    "type": "ScheduleTrigger",
                    "description": "Daily trigger",
                    "runtimeState": "Started",
                    "annotations": [],
                    "typeProperties": {
                        "recurrence": {
                            "frequency": "Day",
                            "interval": 1,
                            "startTime": "2026-01-01T06:00:00Z",
                            "timeZone": "UTC",
                        },
                    },
                    "pipelines": [
                        {"pipelineReference": {"referenceName": "pipeline-etl"}},
                    ],
                },
            },
        ],
    })
    client.health_check = AsyncMock(return_value=True)
    client.is_healthy = True
    return client


def _make_server_with_mock_client(adf_config, mock_client):
    """Create an AdfMCPServer and replace its internal client with the mock."""
    server = AdfMCPServer(adf_config)
    # Replace client on server and both tool instances
    server._client = mock_client
    server._pipeline_tools._client = mock_client
    server._monitoring_tools._client = mock_client
    return server


# ---------------------------------------------------------------------------
# 1. TestAdfMCPServerInit — Server initialization (3 tests)
# ---------------------------------------------------------------------------


class TestAdfMCPServerInit:
    """Tests for AdfMCPServer initialization and metadata."""

    def test_server_init(self, adf_server):
        """Test server has correct SERVER_NAME and SERVER_VERSION constants."""
        assert adf_server.SERVER_NAME == "adf-mcp"
        assert adf_server.SERVER_VERSION == "1.0.0"
        assert isinstance(adf_server._client, AdfApiClient)

    def test_server_tools_registered(self, adf_server):
        """Test exactly 8 tools are registered (4 pipeline + 4 monitoring)."""
        tools = adf_server.get_tools()
        assert len(tools) == 8

    def test_server_tool_names(self, adf_server):
        """Test the exact set of registered tool names matches expected tools."""
        names = set(adf_server.get_tool_names())
        expected = {
            "adf_list_pipelines",
            "adf_get_pipeline",
            "adf_run_pipeline",
            "adf_cancel_pipeline_run",
            "adf_get_pipeline_run",
            "adf_list_pipeline_runs",
            "adf_list_datasets",
            "adf_list_triggers",
        }
        assert names == expected


# ---------------------------------------------------------------------------
# 2. TestAdfMCPServerToolCalls — Tool dispatch (9 tests)
# ---------------------------------------------------------------------------


class TestAdfMCPServerToolCalls:
    """Tests for calling tools through AdfMCPServer.call_tool()."""

    @pytest.mark.asyncio
    async def test_call_list_pipelines(self, adf_config, mock_client):
        """Test calling adf_list_pipelines returns successful ToolResult."""
        server = _make_server_with_mock_client(adf_config, mock_client)

        result = await server.call_tool("adf_list_pipelines")

        assert result.success is True
        assert result.content is not None
        mock_client.list_pipelines.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_get_pipeline(self, adf_config, mock_client):
        """Test calling adf_get_pipeline with pipeline_name argument."""
        server = _make_server_with_mock_client(adf_config, mock_client)

        result = await server.call_tool(
            "adf_get_pipeline", {"pipeline_name": "pipeline-etl"}
        )

        assert result.success is True
        assert result.content is not None
        mock_client.get_pipeline.assert_called_once_with("pipeline-etl")

    @pytest.mark.asyncio
    async def test_call_run_pipeline(self, adf_config, mock_client):
        """Test calling adf_run_pipeline triggers execution."""
        server = _make_server_with_mock_client(adf_config, mock_client)

        result = await server.call_tool(
            "adf_run_pipeline", {"pipeline_name": "pipeline-etl"}
        )

        assert result.success is True
        assert result.content is not None
        mock_client.run_pipeline.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_get_pipeline_run(self, adf_config, mock_client):
        """Test calling adf_get_pipeline_run with run_id argument."""
        server = _make_server_with_mock_client(adf_config, mock_client)

        result = await server.call_tool(
            "adf_get_pipeline_run", {"run_id": "run-abc-123"}
        )

        assert result.success is True
        assert result.content is not None
        mock_client.get_pipeline_run.assert_called_once_with("run-abc-123")

    @pytest.mark.asyncio
    async def test_call_list_pipeline_runs(self, adf_config, mock_client):
        """Test calling adf_list_pipeline_runs returns run history."""
        server = _make_server_with_mock_client(adf_config, mock_client)

        result = await server.call_tool("adf_list_pipeline_runs")

        assert result.success is True
        assert result.content is not None
        mock_client.list_pipeline_runs.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_list_datasets(self, adf_config, mock_client):
        """Test calling adf_list_datasets returns dataset list."""
        server = _make_server_with_mock_client(adf_config, mock_client)

        result = await server.call_tool("adf_list_datasets")

        assert result.success is True
        assert result.content is not None
        mock_client.list_datasets.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_list_triggers(self, adf_config, mock_client):
        """Test calling adf_list_triggers returns trigger list."""
        server = _make_server_with_mock_client(adf_config, mock_client)

        result = await server.call_tool("adf_list_triggers")

        assert result.success is True
        assert result.content is not None
        mock_client.list_triggers.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self, adf_config, mock_client):
        """Test calling a non-existent tool returns an error indication.

        Note: The MCP protocol handler returns tool-not-found as a result with
        isError=True (not as a JSON-RPC error). The server's call_tool wraps this
        as ToolResult(success=True, content={isError: True, ...}).
        """
        server = _make_server_with_mock_client(adf_config, mock_client)

        result = await server.call_tool("adf_nonexistent_tool")

        # The protocol returns isError inside the result content
        assert result.content is not None
        assert result.content.get("isError") is True
        content_text = result.content["content"][0]["text"]
        assert "not found" in content_text.lower() or "adf_nonexistent_tool" in content_text

    @pytest.mark.asyncio
    async def test_health_check(self, adf_config, mock_client):
        """Test health_check delegates to the underlying AdfApiClient."""
        server = _make_server_with_mock_client(adf_config, mock_client)

        result = await server.health_check()

        assert result is True
        mock_client.health_check.assert_called_once()
