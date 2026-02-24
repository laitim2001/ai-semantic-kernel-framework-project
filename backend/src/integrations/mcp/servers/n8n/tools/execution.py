"""n8n Execution Management Tools.

Provides MCP tools for triggering and monitoring n8n workflow executions.

Tools:
    - execute_workflow: Trigger a workflow execution with input data
    - get_execution: Get execution status and results
    - list_executions: List execution history with filtering
"""

from typing import Any, Dict, List, Optional
import logging

from ....core.types import (
    ToolSchema,
    ToolParameter,
    ToolInputType,
    ToolResult,
)
from ..client import N8nApiClient, N8nApiError, N8nNotFoundError

logger = logging.getLogger(__name__)


class ExecutionTools:
    """Execution management tools for n8n MCP Server.

    Provides workflow execution triggering and monitoring capabilities
    through the MCP protocol.

    Permission Levels:
        - Level 1 (READ): get_execution, list_executions
        - Level 2 (EXECUTE): execute_workflow

    Example:
        >>> client = N8nApiClient(config)
        >>> tools = ExecutionTools(client)
        >>> result = await tools.n8n_execute_workflow(
        ...     workflow_id="wf-123",
        ...     input_data={"action": "reset_password", "user": "john"}
        ... )
    """

    PERMISSION_LEVELS = {
        "n8n_execute_workflow": 2,
        "n8n_get_execution": 1,
        "n8n_list_executions": 1,
    }

    def __init__(self, client: N8nApiClient):
        """Initialize execution tools.

        Args:
            client: N8nApiClient instance
        """
        self._client = client

    @staticmethod
    def get_schemas() -> List[ToolSchema]:
        """Get all execution tool schemas.

        Returns:
            List of ToolSchema definitions for MCP protocol
        """
        return [
            ToolSchema(
                name="n8n_execute_workflow",
                description=(
                    "Trigger execution of an n8n workflow with optional input data. "
                    "The workflow must be saved (but does not need to be active). "
                    "Returns the execution result or execution ID for async tracking."
                ),
                parameters=[
                    ToolParameter(
                        name="workflow_id",
                        type=ToolInputType.STRING,
                        description="The n8n workflow ID to execute.",
                        required=True,
                    ),
                    ToolParameter(
                        name="input_data",
                        type=ToolInputType.OBJECT,
                        description=(
                            "Input data to pass to the workflow. "
                            "This data will be available in the first node."
                        ),
                        required=False,
                    ),
                ],
                returns="Execution result with executionId, status, and output data",
            ),
            ToolSchema(
                name="n8n_get_execution",
                description=(
                    "Get detailed information about a specific workflow execution, "
                    "including its status, timing, input/output data, and any errors."
                ),
                parameters=[
                    ToolParameter(
                        name="execution_id",
                        type=ToolInputType.STRING,
                        description="The n8n execution ID.",
                        required=True,
                    ),
                ],
                returns="Execution object with status, startedAt, stoppedAt, data, and error info",
            ),
            ToolSchema(
                name="n8n_list_executions",
                description=(
                    "List workflow execution history with optional filtering "
                    "by workflow ID or execution status."
                ),
                parameters=[
                    ToolParameter(
                        name="workflow_id",
                        type=ToolInputType.STRING,
                        description="Filter by workflow ID.",
                        required=False,
                    ),
                    ToolParameter(
                        name="status",
                        type=ToolInputType.STRING,
                        description="Filter by status: success, error, waiting.",
                        required=False,
                        enum=["success", "error", "waiting"],
                    ),
                    ToolParameter(
                        name="limit",
                        type=ToolInputType.INTEGER,
                        description="Maximum number of executions to return (default: 20).",
                        required=False,
                        default=20,
                    ),
                ],
                returns="List of executions with id, workflowId, status, startedAt, stoppedAt",
            ),
        ]

    async def n8n_execute_workflow(
        self,
        workflow_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Trigger a workflow execution.

        Args:
            workflow_id: n8n workflow ID
            input_data: Optional input data for the workflow

        Returns:
            ToolResult with execution result
        """
        if not workflow_id:
            return ToolResult(
                success=False,
                content=None,
                error="workflow_id is required",
            )

        try:
            logger.info(
                f"Executing n8n workflow {workflow_id} "
                f"with data keys: {list(input_data.keys()) if input_data else 'none'}"
            )

            result = await self._client.execute_workflow(
                workflow_id=workflow_id,
                data=input_data,
            )

            # Extract execution details from response
            execution_data = result.get("data", result)
            execution_id = execution_data.get("executionId", "unknown")

            return ToolResult(
                success=True,
                content={
                    "executionId": execution_id,
                    "workflowId": workflow_id,
                    "status": execution_data.get("status", "completed"),
                    "data": execution_data.get("data"),
                    "message": f"Workflow {workflow_id} executed successfully (execution: {execution_id})",
                },
                metadata={
                    "workflow_id": workflow_id,
                    "execution_id": execution_id,
                },
            )

        except N8nNotFoundError:
            return ToolResult(
                success=False,
                content=None,
                error=f"Workflow not found: {workflow_id}",
            )
        except N8nApiError as e:
            logger.error(f"Failed to execute workflow {workflow_id}: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Failed to execute workflow: {e}",
            )

    async def n8n_get_execution(
        self,
        execution_id: str,
        **kwargs: Any,
    ) -> ToolResult:
        """Get execution details.

        Args:
            execution_id: n8n execution ID

        Returns:
            ToolResult with execution details
        """
        if not execution_id:
            return ToolResult(
                success=False,
                content=None,
                error="execution_id is required",
            )

        try:
            execution = await self._client.get_execution(execution_id)

            return ToolResult(
                success=True,
                content={
                    "id": execution.get("id"),
                    "workflowId": execution.get("workflowId"),
                    "status": execution.get("status"),
                    "startedAt": execution.get("startedAt"),
                    "stoppedAt": execution.get("stoppedAt"),
                    "finished": execution.get("finished"),
                    "mode": execution.get("mode"),
                    "data": execution.get("data"),
                    "workflowName": execution.get("workflowData", {}).get("name"),
                },
            )

        except N8nNotFoundError:
            return ToolResult(
                success=False,
                content=None,
                error=f"Execution not found: {execution_id}",
            )
        except N8nApiError as e:
            logger.error(f"Failed to get execution {execution_id}: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Failed to get execution: {e}",
            )

    async def n8n_list_executions(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        **kwargs: Any,
    ) -> ToolResult:
        """List execution history.

        Args:
            workflow_id: Filter by workflow ID
            status: Filter by execution status
            limit: Maximum results (default: 20)

        Returns:
            ToolResult with list of executions
        """
        try:
            result = await self._client.list_executions(
                workflow_id=workflow_id,
                status=status,
                limit=limit,
            )

            executions = result.get("data", [])
            summary = []
            for ex in executions:
                summary.append({
                    "id": ex.get("id"),
                    "workflowId": ex.get("workflowId"),
                    "status": ex.get("status"),
                    "startedAt": ex.get("startedAt"),
                    "stoppedAt": ex.get("stoppedAt"),
                    "finished": ex.get("finished"),
                    "mode": ex.get("mode"),
                })

            return ToolResult(
                success=True,
                content={
                    "executions": summary,
                    "count": len(summary),
                    "nextCursor": result.get("nextCursor"),
                },
            )

        except N8nApiError as e:
            logger.error(f"Failed to list executions: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Failed to list executions: {e}",
            )
