"""ADF Pipeline Management Tools.

Provides MCP tools for listing, inspecting, running, and cancelling
Azure Data Factory pipelines.

Tools:
    - adf_list_pipelines: List all pipelines
    - adf_get_pipeline: Get pipeline details
    - adf_run_pipeline: Trigger a pipeline run
    - adf_cancel_pipeline_run: Cancel a running pipeline
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


class PipelineTools:
    """Pipeline management tools for ADF MCP Server.

    Provides CRUD and execution operations for ADF pipelines
    through the MCP protocol.

    Permission Levels:
        - Level 1 (READ): list_pipelines, get_pipeline
        - Level 2 (EXECUTE): run_pipeline
        - Level 3 (ADMIN): cancel_pipeline_run

    Example:
        >>> client = AdfApiClient(config)
        >>> tools = PipelineTools(client)
        >>> result = await tools.adf_list_pipelines()
        >>> print(result.content)
    """

    PERMISSION_LEVELS = {
        "adf_list_pipelines": 1,
        "adf_get_pipeline": 1,
        "adf_run_pipeline": 2,
        "adf_cancel_pipeline_run": 3,
    }

    def __init__(self, client: AdfApiClient):
        """Initialize pipeline tools.

        Args:
            client: AdfApiClient instance
        """
        self._client = client

    @staticmethod
    def get_schemas() -> List[ToolSchema]:
        """Get all pipeline tool schemas.

        Returns:
            List of ToolSchema definitions for MCP protocol
        """
        return [
            ToolSchema(
                name="adf_list_pipelines",
                description=(
                    "List all Azure Data Factory pipelines. Returns pipeline names, "
                    "types, descriptions, and activity counts."
                ),
                parameters=[],
                returns="List of pipelines with name, description, and activity summary",
            ),
            ToolSchema(
                name="adf_get_pipeline",
                description=(
                    "Get detailed information about a specific ADF pipeline, "
                    "including its activities, parameters, and configurations."
                ),
                parameters=[
                    ToolParameter(
                        name="pipeline_name",
                        type=ToolInputType.STRING,
                        description="The ADF pipeline name.",
                        required=True,
                    ),
                ],
                returns="Pipeline definition with activities, parameters, and settings",
            ),
            ToolSchema(
                name="adf_run_pipeline",
                description=(
                    "Trigger execution of an ADF pipeline with optional parameters. "
                    "Returns a run ID for tracking the execution."
                ),
                parameters=[
                    ToolParameter(
                        name="pipeline_name",
                        type=ToolInputType.STRING,
                        description="The ADF pipeline name to execute.",
                        required=True,
                    ),
                    ToolParameter(
                        name="parameters",
                        type=ToolInputType.OBJECT,
                        description=(
                            "Pipeline parameters as key-value pairs. "
                            "These override default parameter values."
                        ),
                        required=False,
                    ),
                ],
                returns="Pipeline run ID and status for execution tracking",
            ),
            ToolSchema(
                name="adf_cancel_pipeline_run",
                description=(
                    "Cancel a running ADF pipeline execution. "
                    "The pipeline must be in InProgress or Queued state."
                ),
                parameters=[
                    ToolParameter(
                        name="run_id",
                        type=ToolInputType.STRING,
                        description="The pipeline run ID to cancel.",
                        required=True,
                    ),
                ],
                returns="Cancellation confirmation with run details",
            ),
        ]

    async def adf_list_pipelines(self, **kwargs: Any) -> ToolResult:
        """List all ADF pipelines.

        Returns:
            ToolResult with list of pipelines
        """
        try:
            result = await self._client.list_pipelines()
            pipelines = result.get("value", [])

            summary = []
            for pl in pipelines:
                properties = pl.get("properties", {})
                activities = properties.get("activities", [])
                parameters = properties.get("parameters", {})

                summary.append({
                    "name": pl.get("name"),
                    "description": properties.get("description", ""),
                    "activityCount": len(activities),
                    "parameterCount": len(parameters),
                    "activities": [
                        {
                            "name": a.get("name"),
                            "type": a.get("type"),
                        }
                        for a in activities[:10]  # Limit activity detail
                    ],
                    "parameters": list(parameters.keys()),
                })

            return ToolResult(
                success=True,
                content={
                    "pipelines": summary,
                    "count": len(summary),
                },
            )

        except AdfApiError as e:
            logger.error(f"Failed to list pipelines: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Failed to list pipelines: {e}",
            )

    async def adf_get_pipeline(
        self,
        pipeline_name: str,
        **kwargs: Any,
    ) -> ToolResult:
        """Get detailed pipeline information.

        Args:
            pipeline_name: ADF pipeline name

        Returns:
            ToolResult with pipeline details
        """
        if not pipeline_name:
            return ToolResult(
                success=False,
                content=None,
                error="pipeline_name is required",
            )

        try:
            pipeline = await self._client.get_pipeline(pipeline_name)
            properties = pipeline.get("properties", {})
            activities = properties.get("activities", [])
            parameters = properties.get("parameters", {})

            # Build parameter details
            param_details = {}
            for pname, pconfig in parameters.items():
                param_details[pname] = {
                    "type": pconfig.get("type", "unknown"),
                    "defaultValue": pconfig.get("defaultValue"),
                }

            # Build activity details
            activity_details = []
            for activity in activities:
                detail = {
                    "name": activity.get("name"),
                    "type": activity.get("type"),
                    "description": activity.get("description", ""),
                }
                # Include dependency info
                depends_on = activity.get("dependsOn", [])
                if depends_on:
                    detail["dependsOn"] = [
                        {
                            "activity": d.get("activity"),
                            "conditions": d.get("dependencyConditions", []),
                        }
                        for d in depends_on
                    ]
                activity_details.append(detail)

            return ToolResult(
                success=True,
                content={
                    "name": pipeline.get("name"),
                    "description": properties.get("description", ""),
                    "activities": activity_details,
                    "activityCount": len(activities),
                    "parameters": param_details,
                    "folder": properties.get("folder", {}).get("name", ""),
                    "annotations": properties.get("annotations", []),
                },
            )

        except AdfNotFoundError:
            return ToolResult(
                success=False,
                content=None,
                error=f"Pipeline not found: {pipeline_name}",
            )
        except AdfApiError as e:
            logger.error(f"Failed to get pipeline {pipeline_name}: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Failed to get pipeline: {e}",
            )

    async def adf_run_pipeline(
        self,
        pipeline_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Trigger a pipeline run.

        Args:
            pipeline_name: ADF pipeline name
            parameters: Optional pipeline parameters

        Returns:
            ToolResult with run ID
        """
        if not pipeline_name:
            return ToolResult(
                success=False,
                content=None,
                error="pipeline_name is required",
            )

        try:
            logger.info(
                f"Running ADF pipeline {pipeline_name} "
                f"with params: {list(parameters.keys()) if parameters else 'none'}"
            )

            result = await self._client.run_pipeline(
                pipeline_name=pipeline_name,
                parameters=parameters,
            )

            run_id = result.get("runId", "unknown")

            return ToolResult(
                success=True,
                content={
                    "runId": run_id,
                    "pipelineName": pipeline_name,
                    "status": "Accepted",
                    "message": (
                        f"Pipeline '{pipeline_name}' run triggered successfully "
                        f"(run: {run_id})"
                    ),
                },
                metadata={
                    "pipeline_name": pipeline_name,
                    "run_id": run_id,
                },
            )

        except AdfNotFoundError:
            return ToolResult(
                success=False,
                content=None,
                error=f"Pipeline not found: {pipeline_name}",
            )
        except AdfApiError as e:
            logger.error(f"Failed to run pipeline {pipeline_name}: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Failed to run pipeline: {e}",
            )

    async def adf_cancel_pipeline_run(
        self,
        run_id: str,
        **kwargs: Any,
    ) -> ToolResult:
        """Cancel a pipeline run.

        Args:
            run_id: Pipeline run ID

        Returns:
            ToolResult with cancellation status
        """
        if not run_id:
            return ToolResult(
                success=False,
                content=None,
                error="run_id is required",
            )

        try:
            logger.info(f"Cancelling ADF pipeline run {run_id}")

            await self._client.cancel_pipeline_run(run_id)

            return ToolResult(
                success=True,
                content={
                    "runId": run_id,
                    "status": "Cancelling",
                    "message": f"Pipeline run '{run_id}' cancellation requested",
                },
            )

        except AdfNotFoundError:
            return ToolResult(
                success=False,
                content=None,
                error=f"Pipeline run not found: {run_id}",
            )
        except AdfApiError as e:
            logger.error(f"Failed to cancel pipeline run {run_id}: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Failed to cancel pipeline run: {e}",
            )
