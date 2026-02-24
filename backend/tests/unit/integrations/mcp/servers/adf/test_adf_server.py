"""Tests for AdfMCPServer.

Sprint 125: Azure Data Factory MCP Server

Tests cover:
    - Server initialization and tool registration
    - Tool count and naming conventions
    - Permission levels
    - Health check delegation
    - Pipeline tools via server (list, get, run, cancel)
    - Monitoring tools via server (get run, list runs, datasets, triggers)
    - MCP format compliance
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.mcp.servers.adf.client import AdfApiClient, AdfConfig
from src.integrations.mcp.servers.adf.server import AdfMCPServer
from src.integrations.mcp.servers.adf.tools.pipeline import PipelineTools
from src.integrations.mcp.servers.adf.tools.monitoring import MonitoringTools


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
    """Create a mock AdfApiClient with all async methods."""
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
    client.run_pipeline = AsyncMock(return_value={
        "runId": "run-abc-123",
    })
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
            {
                "runId": "run-2",
                "pipelineName": "pipeline-load",
                "status": "Failed",
                "runStart": "2026-02-24T11:00:00Z",
                "runEnd": "2026-02-24T11:02:00Z",
                "invokedBy": {"name": "manual"},
                "message": "Timeout error",
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


# ---------------------------------------------------------------------------
# 1. TestAdfMCPServer — Server initialization (5 tests)
# ---------------------------------------------------------------------------


class TestAdfMCPServer:
    """Tests for AdfMCPServer initialization and core properties."""

    def test_initialization(self, adf_server, adf_config):
        """Test server initializes with config, client, and registered tools."""
        assert adf_server._config is adf_config
        assert isinstance(adf_server._client, AdfApiClient)
        assert isinstance(adf_server._pipeline_tools, PipelineTools)
        assert isinstance(adf_server._monitoring_tools, MonitoringTools)

        # Tools should be registered during init
        tools = adf_server.get_tools()
        assert len(tools) > 0

    def test_get_tools_returns_8_tools(self, adf_server):
        """Test exactly 8 tools are registered."""
        tools = adf_server.get_tools()
        assert len(tools) == 8

    def test_get_tool_names_adf_prefix(self, adf_server):
        """Test all tool names start with 'adf_' prefix."""
        names = adf_server.get_tool_names()
        assert len(names) == 8

        for name in names:
            assert name.startswith("adf_"), f"Tool '{name}' missing 'adf_' prefix"

        expected = [
            "adf_list_pipelines",
            "adf_get_pipeline",
            "adf_run_pipeline",
            "adf_cancel_pipeline_run",
            "adf_get_pipeline_run",
            "adf_list_pipeline_runs",
            "adf_list_datasets",
            "adf_list_triggers",
        ]
        assert sorted(names) == sorted(expected)

    def test_permission_levels_defined(self, adf_server):
        """Test permission levels are defined for pipeline and monitoring tools."""
        pipeline_perms = PipelineTools.PERMISSION_LEVELS
        monitoring_perms = MonitoringTools.PERMISSION_LEVELS

        # Pipeline tools: read (1), execute (2), admin (3)
        assert pipeline_perms["adf_list_pipelines"] == 1
        assert pipeline_perms["adf_get_pipeline"] == 1
        assert pipeline_perms["adf_run_pipeline"] == 2
        assert pipeline_perms["adf_cancel_pipeline_run"] == 3

        # Monitoring tools: all read (1)
        assert monitoring_perms["adf_get_pipeline_run"] == 1
        assert monitoring_perms["adf_list_pipeline_runs"] == 1
        assert monitoring_perms["adf_list_datasets"] == 1
        assert monitoring_perms["adf_list_triggers"] == 1

    @pytest.mark.asyncio
    async def test_health_check(self, adf_server):
        """Test health_check delegates to client."""
        adf_server._client.health_check = AsyncMock(return_value=True)

        result = await adf_server.health_check()

        assert result is True
        adf_server._client.health_check.assert_called_once()


# ---------------------------------------------------------------------------
# 2. TestPipelineToolsViaServer — Pipeline tools (5 tests)
# ---------------------------------------------------------------------------


class TestPipelineToolsViaServer:
    """Tests for pipeline tools called through the server's tool instances."""

    @pytest.mark.asyncio
    async def test_list_pipelines(self, mock_client):
        """Test adf_list_pipelines returns summarized pipeline list."""
        tools = PipelineTools(mock_client)

        result = await tools.adf_list_pipelines()

        assert result.success is True
        assert result.content["count"] == 1

        pipeline = result.content["pipelines"][0]
        assert pipeline["name"] == "pipeline-etl"
        assert pipeline["description"] == "ETL pipeline"
        assert pipeline["activityCount"] == 2
        assert pipeline["parameterCount"] == 1
        assert "env" in pipeline["parameters"]

        mock_client.list_pipelines.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pipeline(self, mock_client):
        """Test adf_get_pipeline returns detailed pipeline info."""
        tools = PipelineTools(mock_client)

        result = await tools.adf_get_pipeline(pipeline_name="pipeline-etl")

        assert result.success is True
        assert result.content["name"] == "pipeline-etl"
        assert result.content["description"] == "ETL pipeline"
        assert result.content["activityCount"] == 1
        assert "env" in result.content["parameters"]
        assert result.content["folder"] == "production"
        assert result.content["annotations"] == ["critical"]

        mock_client.get_pipeline.assert_called_once_with("pipeline-etl")

    @pytest.mark.asyncio
    async def test_get_pipeline_missing_name(self, mock_client):
        """Test adf_get_pipeline with empty name returns error."""
        tools = PipelineTools(mock_client)

        result = await tools.adf_get_pipeline(pipeline_name="")

        assert result.success is False
        assert result.error == "pipeline_name is required"
        assert result.content is None

        # Client should NOT be called when name is empty
        mock_client.get_pipeline.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_pipeline(self, mock_client):
        """Test adf_run_pipeline triggers execution and returns run ID."""
        tools = PipelineTools(mock_client)

        result = await tools.adf_run_pipeline(
            pipeline_name="pipeline-etl",
            parameters={"env": "prod"},
        )

        assert result.success is True
        assert result.content["runId"] == "run-abc-123"
        assert result.content["pipelineName"] == "pipeline-etl"
        assert result.content["status"] == "Accepted"

        mock_client.run_pipeline.assert_called_once_with(
            pipeline_name="pipeline-etl",
            parameters={"env": "prod"},
        )

    @pytest.mark.asyncio
    async def test_cancel_pipeline_run(self, mock_client):
        """Test adf_cancel_pipeline_run requests cancellation."""
        tools = PipelineTools(mock_client)

        result = await tools.adf_cancel_pipeline_run(run_id="run-abc-123")

        assert result.success is True
        assert result.content["runId"] == "run-abc-123"
        assert result.content["status"] == "Cancelling"

        mock_client.cancel_pipeline_run.assert_called_once_with("run-abc-123")


# ---------------------------------------------------------------------------
# 3. TestMonitoringToolsViaServer — Monitoring tools (4 tests)
# ---------------------------------------------------------------------------


class TestMonitoringToolsViaServer:
    """Tests for monitoring tools called through the server's tool instances."""

    @pytest.mark.asyncio
    async def test_get_pipeline_run(self, mock_client):
        """Test adf_get_pipeline_run returns run details with duration."""
        tools = MonitoringTools(mock_client)

        result = await tools.adf_get_pipeline_run(run_id="run-abc-123")

        assert result.success is True
        assert result.content["runId"] == "run-abc-123"
        assert result.content["pipelineName"] == "pipeline-etl"
        assert result.content["status"] == "Succeeded"
        assert result.content["runStart"] == "2026-02-24T10:00:00Z"
        assert result.content["runEnd"] == "2026-02-24T10:05:00Z"
        assert result.content["durationMs"] == 300000  # 5 minutes in ms
        assert result.content["parameters"] == {"env": "prod"}
        assert result.content["isLatest"] is True

        mock_client.get_pipeline_run.assert_called_once_with("run-abc-123")

    @pytest.mark.asyncio
    async def test_list_pipeline_runs(self, mock_client):
        """Test adf_list_pipeline_runs returns run history summary."""
        tools = MonitoringTools(mock_client)

        result = await tools.adf_list_pipeline_runs(
            last_updated_after="2026-02-24T00:00:00Z",
            last_updated_before="2026-02-25T00:00:00Z",
        )

        assert result.success is True
        assert result.content["count"] == 2

        runs = result.content["runs"]
        assert runs[0]["runId"] == "run-1"
        assert runs[0]["pipelineName"] == "pipeline-etl"
        assert runs[0]["status"] == "Succeeded"
        assert runs[1]["runId"] == "run-2"
        assert runs[1]["status"] == "Failed"

        mock_client.list_pipeline_runs.assert_called_once_with(
            last_updated_after="2026-02-24T00:00:00Z",
            last_updated_before="2026-02-25T00:00:00Z",
        )

    @pytest.mark.asyncio
    async def test_list_datasets(self, mock_client):
        """Test adf_list_datasets returns dataset summary."""
        tools = MonitoringTools(mock_client)

        result = await tools.adf_list_datasets()

        assert result.success is True
        assert result.content["count"] == 1

        dataset = result.content["datasets"][0]
        assert dataset["name"] == "ds-source"
        assert dataset["type"] == "AzureSqlTable"
        assert dataset["linkedService"] == "ls-sql"
        assert dataset["folder"] == "raw"
        assert len(dataset["schema"]) == 2
        assert dataset["schema"][0]["name"] == "id"

        mock_client.list_datasets.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_triggers(self, mock_client):
        """Test adf_list_triggers returns trigger summary with schedule info."""
        tools = MonitoringTools(mock_client)

        result = await tools.adf_list_triggers()

        assert result.success is True
        assert result.content["count"] == 1

        trigger = result.content["triggers"][0]
        assert trigger["name"] == "trigger-daily"
        assert trigger["type"] == "ScheduleTrigger"
        assert trigger["runtimeState"] == "Started"
        assert trigger["schedule"]["frequency"] == "Day"
        assert trigger["schedule"]["interval"] == 1
        assert "pipeline-etl" in trigger["pipelines"]

        mock_client.list_triggers.assert_called_once()


# ---------------------------------------------------------------------------
# 4. TestMCPFormatCompliance — MCP schema compliance (2 tests)
# ---------------------------------------------------------------------------


class TestMCPFormatCompliance:
    """Tests for MCP protocol format compliance of tool schemas."""

    def test_tool_schemas_mcp_compliant(self, adf_server):
        """Test all tool schemas produce valid MCP format with required fields."""
        tools = adf_server.get_tools()

        for tool in tools:
            mcp_format = tool.to_mcp_format()

            # Required MCP fields
            assert "name" in mcp_format, f"Tool missing 'name'"
            assert "description" in mcp_format, f"Tool {tool.name} missing 'description'"
            assert "inputSchema" in mcp_format, f"Tool {tool.name} missing 'inputSchema'"

            # inputSchema must be a JSON Schema object
            schema = mcp_format["inputSchema"]
            assert schema["type"] == "object", (
                f"Tool {tool.name} inputSchema type must be 'object', got '{schema['type']}'"
            )
            assert "properties" in schema, (
                f"Tool {tool.name} inputSchema missing 'properties'"
            )

            # Description should be meaningful (not empty)
            assert len(mcp_format["description"]) > 10, (
                f"Tool {tool.name} has too short description"
            )

    def test_tool_names_follow_convention(self, adf_server):
        """Test all tool names follow the 'adf_' prefix convention."""
        tools = adf_server.get_tools()

        for tool in tools:
            assert tool.name.startswith("adf_"), (
                f"Tool name '{tool.name}' does not start with 'adf_' prefix"
            )

            # Names should be snake_case
            assert tool.name == tool.name.lower(), (
                f"Tool name '{tool.name}' is not lowercase snake_case"
            )

            # Names should not have consecutive underscores
            assert "__" not in tool.name, (
                f"Tool name '{tool.name}' has consecutive underscores"
            )
