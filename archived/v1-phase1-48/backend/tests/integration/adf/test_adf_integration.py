"""Integration tests for ADF MCP Server.

Sprint 125: Azure Data Factory MCP Server

End-to-end tests that exercise the full tool execution path:
    Server → Tool class → (mocked) AdfApiClient → ToolResult

These tests instantiate a real AdfMCPServer but mock the underlying
HTTP client so no actual Azure calls are made.

Tests cover:
    - Pipeline E2E: list, run, missing params
    - Monitoring E2E: get run, list datasets, list triggers
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
    """Create a real AdfMCPServer with mocked client internals."""
    server = AdfMCPServer(adf_config)
    return server


def _build_mock_client() -> MagicMock:
    """Build a fully mocked AdfApiClient with realistic responses."""
    client = MagicMock(spec=AdfApiClient)

    client.list_pipelines = AsyncMock(return_value={
        "value": [
            {
                "name": "etl-daily",
                "properties": {
                    "description": "Daily ETL job",
                    "activities": [
                        {"name": "Extract", "type": "Copy"},
                        {"name": "Transform", "type": "DataFlow"},
                        {"name": "Load", "type": "Copy"},
                    ],
                    "parameters": {
                        "sourceDB": {"type": "String", "defaultValue": "prod"},
                        "targetDB": {"type": "String", "defaultValue": "warehouse"},
                    },
                },
            },
            {
                "name": "report-gen",
                "properties": {
                    "description": "Generate weekly reports",
                    "activities": [
                        {"name": "RunNotebook", "type": "DatabricksNotebook"},
                    ],
                    "parameters": {},
                },
            },
        ],
    })

    client.get_pipeline = AsyncMock(return_value={
        "name": "etl-daily",
        "properties": {
            "description": "Daily ETL job",
            "activities": [
                {
                    "name": "Extract",
                    "type": "Copy",
                    "description": "Extract from source",
                    "dependsOn": [],
                },
                {
                    "name": "Transform",
                    "type": "DataFlow",
                    "description": "Apply transformations",
                    "dependsOn": [
                        {
                            "activity": "Extract",
                            "dependencyConditions": ["Succeeded"],
                        },
                    ],
                },
            ],
            "parameters": {
                "sourceDB": {"type": "String", "defaultValue": "prod"},
            },
            "folder": {"name": "production"},
            "annotations": ["critical", "daily"],
        },
    })

    client.run_pipeline = AsyncMock(return_value={
        "runId": "int-run-001",
    })

    client.cancel_pipeline_run = AsyncMock(return_value={})

    client.get_pipeline_run = AsyncMock(return_value={
        "runId": "int-run-001",
        "pipelineName": "etl-daily",
        "status": "InProgress",
        "runStart": "2026-02-24T08:00:00Z",
        "runEnd": None,
        "parameters": {"sourceDB": "prod"},
        "invokedBy": {"name": "integration-test"},
        "message": "",
        "isLatest": True,
        "runGroupId": "grp-001",
    })

    client.list_pipeline_runs = AsyncMock(return_value={
        "value": [
            {
                "runId": "int-run-001",
                "pipelineName": "etl-daily",
                "status": "InProgress",
                "runStart": "2026-02-24T08:00:00Z",
                "runEnd": None,
                "invokedBy": {"name": "integration-test"},
                "message": "Running",
            },
        ],
    })

    client.list_datasets = AsyncMock(return_value={
        "value": [
            {
                "name": "ds-sql-source",
                "properties": {
                    "type": "AzureSqlTable",
                    "description": "Source SQL table",
                    "linkedServiceName": {"referenceName": "ls-sql-prod"},
                    "folder": {"name": "raw"},
                    "annotations": ["source"],
                    "schema": [
                        {"name": "id", "type": "int"},
                        {"name": "created_at", "type": "datetime"},
                    ],
                    "typeProperties": {},
                },
            },
            {
                "name": "ds-blob-sink",
                "properties": {
                    "type": "AzureBlobStorage",
                    "description": "Sink blob storage",
                    "linkedServiceName": {"referenceName": "ls-blob-warehouse"},
                    "folder": {"name": "processed"},
                    "annotations": [],
                    "schema": [],
                    "typeProperties": {},
                },
            },
        ],
    })

    client.list_triggers = AsyncMock(return_value={
        "value": [
            {
                "name": "schedule-6am",
                "properties": {
                    "type": "ScheduleTrigger",
                    "description": "Daily 6 AM trigger",
                    "runtimeState": "Started",
                    "annotations": [],
                    "typeProperties": {
                        "recurrence": {
                            "frequency": "Day",
                            "interval": 1,
                            "startTime": "2026-01-01T06:00:00Z",
                            "timeZone": "Asia/Taipei",
                        },
                    },
                    "pipelines": [
                        {"pipelineReference": {"referenceName": "etl-daily"}},
                    ],
                },
            },
            {
                "name": "blob-event",
                "properties": {
                    "type": "BlobEventsTrigger",
                    "description": "Blob arrival trigger",
                    "runtimeState": "Stopped",
                    "annotations": [],
                    "typeProperties": {
                        "blobPathBeginsWith": "/raw/incoming/",
                        "blobPathEndsWith": ".csv",
                    },
                    "pipelines": [
                        {"pipelineReference": {"referenceName": "report-gen"}},
                    ],
                },
            },
        ],
    })

    client.health_check = AsyncMock(return_value=True)
    client.is_healthy = True

    return client


# ---------------------------------------------------------------------------
# 1. TestAdfPipelineE2E (3 tests)
# ---------------------------------------------------------------------------


class TestAdfPipelineE2E:
    """End-to-end tests for pipeline tools through the full server stack."""

    @pytest.mark.asyncio
    async def test_list_pipelines_through_tools(self, adf_server):
        """Test listing pipelines through PipelineTools with mocked client."""
        mock_client = _build_mock_client()
        adf_server._pipeline_tools._client = mock_client

        result = await adf_server._pipeline_tools.adf_list_pipelines()

        assert result.success is True
        assert result.content["count"] == 2

        pipelines = result.content["pipelines"]
        names = [p["name"] for p in pipelines]
        assert "etl-daily" in names
        assert "report-gen" in names

        # Verify etl-daily has correct activity and parameter counts
        etl = next(p for p in pipelines if p["name"] == "etl-daily")
        assert etl["activityCount"] == 3
        assert etl["parameterCount"] == 2
        assert "sourceDB" in etl["parameters"]
        assert "targetDB" in etl["parameters"]

        # Verify report-gen
        report = next(p for p in pipelines if p["name"] == "report-gen")
        assert report["activityCount"] == 1
        assert report["parameterCount"] == 0

        mock_client.list_pipelines.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_pipeline_through_tools(self, adf_server):
        """Test running a pipeline through PipelineTools with mocked client."""
        mock_client = _build_mock_client()
        adf_server._pipeline_tools._client = mock_client

        result = await adf_server._pipeline_tools.adf_run_pipeline(
            pipeline_name="etl-daily",
            parameters={"sourceDB": "staging"},
        )

        assert result.success is True
        assert result.content["runId"] == "int-run-001"
        assert result.content["pipelineName"] == "etl-daily"
        assert result.content["status"] == "Accepted"
        assert "int-run-001" in result.content["message"]

        # Metadata should track the run
        assert result.metadata["pipeline_name"] == "etl-daily"
        assert result.metadata["run_id"] == "int-run-001"

        mock_client.run_pipeline.assert_called_once_with(
            pipeline_name="etl-daily",
            parameters={"sourceDB": "staging"},
        )

    @pytest.mark.asyncio
    async def test_tool_handles_missing_params(self, adf_server):
        """Test tools gracefully handle missing required parameters."""
        mock_client = _build_mock_client()
        adf_server._pipeline_tools._client = mock_client

        # Empty pipeline_name for get
        result_get = await adf_server._pipeline_tools.adf_get_pipeline(pipeline_name="")
        assert result_get.success is False
        assert "pipeline_name is required" in result_get.error

        # Empty pipeline_name for run
        result_run = await adf_server._pipeline_tools.adf_run_pipeline(pipeline_name="")
        assert result_run.success is False
        assert "pipeline_name is required" in result_run.error

        # Empty run_id for cancel
        result_cancel = await adf_server._pipeline_tools.adf_cancel_pipeline_run(run_id="")
        assert result_cancel.success is False
        assert "run_id is required" in result_cancel.error

        # None of the client methods should have been called
        mock_client.get_pipeline.assert_not_called()
        mock_client.run_pipeline.assert_not_called()
        mock_client.cancel_pipeline_run.assert_not_called()


# ---------------------------------------------------------------------------
# 2. TestAdfMonitoringE2E (3 tests)
# ---------------------------------------------------------------------------


class TestAdfMonitoringE2E:
    """End-to-end tests for monitoring tools through the full server stack."""

    @pytest.mark.asyncio
    async def test_get_pipeline_run_through_tools(self, adf_server):
        """Test getting a pipeline run through MonitoringTools with mocked client."""
        mock_client = _build_mock_client()
        adf_server._monitoring_tools._client = mock_client

        result = await adf_server._monitoring_tools.adf_get_pipeline_run(
            run_id="int-run-001",
        )

        assert result.success is True
        content = result.content
        assert content["runId"] == "int-run-001"
        assert content["pipelineName"] == "etl-daily"
        assert content["status"] == "InProgress"
        assert content["runStart"] == "2026-02-24T08:00:00Z"
        assert content["runEnd"] is None
        # Duration should be None since runEnd is None
        assert content["durationMs"] is None
        assert content["parameters"] == {"sourceDB": "prod"}
        assert content["invokedBy"] == {"name": "integration-test"}
        assert content["isLatest"] is True

        mock_client.get_pipeline_run.assert_called_once_with("int-run-001")

    @pytest.mark.asyncio
    async def test_list_datasets_through_tools(self, adf_server):
        """Test listing datasets through MonitoringTools with mocked client."""
        mock_client = _build_mock_client()
        adf_server._monitoring_tools._client = mock_client

        result = await adf_server._monitoring_tools.adf_list_datasets()

        assert result.success is True
        assert result.content["count"] == 2

        datasets = result.content["datasets"]
        names = [d["name"] for d in datasets]
        assert "ds-sql-source" in names
        assert "ds-blob-sink" in names

        # Verify ds-sql-source details
        sql_ds = next(d for d in datasets if d["name"] == "ds-sql-source")
        assert sql_ds["type"] == "AzureSqlTable"
        assert sql_ds["linkedService"] == "ls-sql-prod"
        assert sql_ds["folder"] == "raw"
        assert len(sql_ds["schema"]) == 2
        assert sql_ds["schema"][0]["name"] == "id"
        assert sql_ds["schema"][1]["name"] == "created_at"

        # Verify ds-blob-sink
        blob_ds = next(d for d in datasets if d["name"] == "ds-blob-sink")
        assert blob_ds["type"] == "AzureBlobStorage"
        assert blob_ds["linkedService"] == "ls-blob-warehouse"
        assert blob_ds["folder"] == "processed"
        assert len(blob_ds["schema"]) == 0

        mock_client.list_datasets.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_triggers_through_tools(self, adf_server):
        """Test listing triggers through MonitoringTools with mocked client."""
        mock_client = _build_mock_client()
        adf_server._monitoring_tools._client = mock_client

        result = await adf_server._monitoring_tools.adf_list_triggers()

        assert result.success is True
        assert result.content["count"] == 2

        triggers = result.content["triggers"]
        names = [t["name"] for t in triggers]
        assert "schedule-6am" in names
        assert "blob-event" in names

        # Verify schedule trigger has schedule info
        schedule_trigger = next(t for t in triggers if t["name"] == "schedule-6am")
        assert schedule_trigger["type"] == "ScheduleTrigger"
        assert schedule_trigger["runtimeState"] == "Started"
        assert schedule_trigger["schedule"]["frequency"] == "Day"
        assert schedule_trigger["schedule"]["interval"] == 1
        assert schedule_trigger["schedule"]["timeZone"] == "Asia/Taipei"
        assert "etl-daily" in schedule_trigger["pipelines"]

        # Verify blob event trigger has blob filter info
        blob_trigger = next(t for t in triggers if t["name"] == "blob-event")
        assert blob_trigger["type"] == "BlobEventsTrigger"
        assert blob_trigger["runtimeState"] == "Stopped"
        assert blob_trigger["blobFilter"]["pathBeginsWith"] == "/raw/incoming/"
        assert blob_trigger["blobFilter"]["pathEndsWith"] == ".csv"
        assert "report-gen" in blob_trigger["pipelines"]

        mock_client.list_triggers.assert_called_once()
