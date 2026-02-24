"""ADF Monitoring Tools.

Provides MCP tools for monitoring pipeline execution and querying
Azure Data Factory resources (datasets, triggers).

Tools:
    - adf_get_pipeline_run: Get details of a specific pipeline run
    - adf_list_pipeline_runs: Query pipeline run history
    - adf_list_datasets: List all datasets
    - adf_list_triggers: List all triggers
"""

import logging
from typing import Any, Dict, List, Optional

from ....core.types import (
    ToolSchema,
    ToolParameter,
    ToolInputType,
    ToolResult,
)
from ..client import AdfApiClient, AdfApiError, AdfNotFoundError

logger = logging.getLogger(__name__)


class MonitoringTools:
    """Monitoring tools for ADF MCP Server.

    Provides pipeline run monitoring and resource discovery capabilities
    through the MCP protocol.

    Permission Levels:
        - Level 1 (READ): All monitoring tools

    Example:
        >>> client = AdfApiClient(config)
        >>> tools = MonitoringTools(client)
        >>> result = await tools.adf_get_pipeline_run(run_id="abc-123")
    """

    PERMISSION_LEVELS = {
        "adf_get_pipeline_run": 1,
        "adf_list_pipeline_runs": 1,
        "adf_list_datasets": 1,
        "adf_list_triggers": 1,
    }

    def __init__(self, client: AdfApiClient):
        """Initialize monitoring tools.

        Args:
            client: AdfApiClient instance
        """
        self._client = client

    @staticmethod
    def get_schemas() -> List[ToolSchema]:
        """Get all monitoring tool schemas.

        Returns:
            List of ToolSchema definitions for MCP protocol
        """
        return [
            ToolSchema(
                name="adf_get_pipeline_run",
                description=(
                    "Get detailed information about a specific ADF pipeline run, "
                    "including status, timing, parameters, and error details."
                ),
                parameters=[
                    ToolParameter(
                        name="run_id",
                        type=ToolInputType.STRING,
                        description="The pipeline run ID.",
                        required=True,
                    ),
                ],
                returns="Pipeline run details with status, duration, and parameters",
            ),
            ToolSchema(
                name="adf_list_pipeline_runs",
                description=(
                    "Query pipeline run history with optional time range filtering. "
                    "Defaults to the last 24 hours."
                ),
                parameters=[
                    ToolParameter(
                        name="last_updated_after",
                        type=ToolInputType.STRING,
                        description=(
                            "Start of time range (ISO 8601). "
                            "Example: 2026-01-01T00:00:00Z"
                        ),
                        required=False,
                    ),
                    ToolParameter(
                        name="last_updated_before",
                        type=ToolInputType.STRING,
                        description=(
                            "End of time range (ISO 8601). "
                            "Example: 2026-01-02T00:00:00Z"
                        ),
                        required=False,
                    ),
                ],
                returns="List of pipeline runs with status, timing, and pipeline names",
            ),
            ToolSchema(
                name="adf_list_datasets",
                description=(
                    "List all datasets in the Azure Data Factory. "
                    "Returns dataset names, types, and linked service references."
                ),
                parameters=[],
                returns="List of datasets with name, type, and linked service",
            ),
            ToolSchema(
                name="adf_list_triggers",
                description=(
                    "List all triggers in the Azure Data Factory. "
                    "Returns trigger names, types, runtime state, and configurations."
                ),
                parameters=[],
                returns="List of triggers with name, type, state, and schedule info",
            ),
        ]

    async def adf_get_pipeline_run(
        self,
        run_id: str,
        **kwargs: Any,
    ) -> ToolResult:
        """Get pipeline run details.

        Args:
            run_id: Pipeline run ID

        Returns:
            ToolResult with run details
        """
        if not run_id:
            return ToolResult(
                success=False,
                content=None,
                error="run_id is required",
            )

        try:
            run = await self._client.get_pipeline_run(run_id)

            # Calculate duration if available
            duration_ms = None
            run_start = run.get("runStart")
            run_end = run.get("runEnd")
            if run_start and run_end:
                try:
                    from datetime import datetime
                    start = datetime.fromisoformat(run_start.replace("Z", "+00:00"))
                    end = datetime.fromisoformat(run_end.replace("Z", "+00:00"))
                    duration_ms = int((end - start).total_seconds() * 1000)
                except (ValueError, TypeError):
                    pass

            return ToolResult(
                success=True,
                content={
                    "runId": run.get("runId"),
                    "pipelineName": run.get("pipelineName"),
                    "status": run.get("status"),
                    "runStart": run_start,
                    "runEnd": run_end,
                    "durationMs": duration_ms,
                    "parameters": run.get("parameters", {}),
                    "invokedBy": run.get("invokedBy", {}),
                    "message": run.get("message", ""),
                    "isLatest": run.get("isLatest"),
                    "runGroupId": run.get("runGroupId"),
                },
            )

        except AdfNotFoundError:
            return ToolResult(
                success=False,
                content=None,
                error=f"Pipeline run not found: {run_id}",
            )
        except AdfApiError as e:
            logger.error(f"Failed to get pipeline run {run_id}: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Failed to get pipeline run: {e}",
            )

    async def adf_list_pipeline_runs(
        self,
        last_updated_after: Optional[str] = None,
        last_updated_before: Optional[str] = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Query pipeline run history.

        Args:
            last_updated_after: Start time (ISO 8601)
            last_updated_before: End time (ISO 8601)

        Returns:
            ToolResult with list of pipeline runs
        """
        try:
            result = await self._client.list_pipeline_runs(
                last_updated_after=last_updated_after,
                last_updated_before=last_updated_before,
            )

            runs = result.get("value", [])
            summary = []
            for run in runs:
                summary.append({
                    "runId": run.get("runId"),
                    "pipelineName": run.get("pipelineName"),
                    "status": run.get("status"),
                    "runStart": run.get("runStart"),
                    "runEnd": run.get("runEnd"),
                    "invokedBy": run.get("invokedBy", {}).get("name", ""),
                    "message": run.get("message", "")[:200],
                })

            return ToolResult(
                success=True,
                content={
                    "runs": summary,
                    "count": len(summary),
                },
            )

        except AdfApiError as e:
            logger.error(f"Failed to list pipeline runs: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Failed to list pipeline runs: {e}",
            )

    async def adf_list_datasets(self, **kwargs: Any) -> ToolResult:
        """List all datasets.

        Returns:
            ToolResult with list of datasets
        """
        try:
            result = await self._client.list_datasets()
            datasets = result.get("value", [])

            summary = []
            for ds in datasets:
                properties = ds.get("properties", {})
                type_properties = properties.get("typeProperties", {})
                linked_service = properties.get("linkedServiceName", {})

                summary.append({
                    "name": ds.get("name"),
                    "type": properties.get("type", "unknown"),
                    "description": properties.get("description", ""),
                    "linkedService": linked_service.get("referenceName", ""),
                    "folder": properties.get("folder", {}).get("name", ""),
                    "annotations": properties.get("annotations", []),
                    "schema": [
                        {"name": s.get("name"), "type": s.get("type")}
                        for s in properties.get("schema", [])[:10]
                    ],
                })

            return ToolResult(
                success=True,
                content={
                    "datasets": summary,
                    "count": len(summary),
                },
            )

        except AdfApiError as e:
            logger.error(f"Failed to list datasets: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Failed to list datasets: {e}",
            )

    async def adf_list_triggers(self, **kwargs: Any) -> ToolResult:
        """List all triggers.

        Returns:
            ToolResult with list of triggers
        """
        try:
            result = await self._client.list_triggers()
            triggers = result.get("value", [])

            summary = []
            for trigger in triggers:
                properties = trigger.get("properties", {})
                type_props = properties.get("typeProperties", {})

                trigger_info: Dict[str, Any] = {
                    "name": trigger.get("name"),
                    "type": properties.get("type", "unknown"),
                    "description": properties.get("description", ""),
                    "runtimeState": properties.get("runtimeState", "unknown"),
                    "annotations": properties.get("annotations", []),
                }

                # Extract schedule info for schedule triggers
                if properties.get("type") == "ScheduleTrigger":
                    recurrence = type_props.get("recurrence", {})
                    trigger_info["schedule"] = {
                        "frequency": recurrence.get("frequency"),
                        "interval": recurrence.get("interval"),
                        "startTime": recurrence.get("startTime"),
                        "timeZone": recurrence.get("timeZone"),
                    }

                # Extract event info for blob/event triggers
                if "blobPathBeginsWith" in type_props:
                    trigger_info["blobFilter"] = {
                        "pathBeginsWith": type_props.get("blobPathBeginsWith"),
                        "pathEndsWith": type_props.get("blobPathEndsWith"),
                    }

                # List pipelines this trigger activates
                pipelines = properties.get("pipelines", [])
                trigger_info["pipelines"] = [
                    p.get("pipelineReference", {}).get("referenceName", "")
                    for p in pipelines
                ]

                summary.append(trigger_info)

            return ToolResult(
                success=True,
                content={
                    "triggers": summary,
                    "count": len(summary),
                },
            )

        except AdfApiError as e:
            logger.error(f"Failed to list triggers: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Failed to list triggers: {e}",
            )
