"""n8n Workflow Management Tools.

Provides MCP tools for listing, inspecting, and managing n8n workflows.

Tools:
    - list_workflows: List all n8n workflows with optional filtering
    - get_workflow: Get detailed workflow information
    - activate_workflow: Activate or deactivate a workflow
"""

from typing import Any, Dict, List, Optional
import json
import logging

from ....core.types import (
    ToolSchema,
    ToolParameter,
    ToolInputType,
    ToolResult,
)
from ..client import N8nApiClient, N8nApiError, N8nNotFoundError

logger = logging.getLogger(__name__)


class WorkflowTools:
    """Workflow management tools for n8n MCP Server.

    Provides read and management operations for n8n workflows
    through the MCP protocol.

    Permission Levels:
        - Level 1 (READ): list_workflows, get_workflow
        - Level 3 (ADMIN): activate_workflow

    Example:
        >>> client = N8nApiClient(config)
        >>> tools = WorkflowTools(client)
        >>> result = await tools.list_workflows()
        >>> print(result.content)
    """

    PERMISSION_LEVELS = {
        "n8n_list_workflows": 1,
        "n8n_get_workflow": 1,
        "n8n_activate_workflow": 3,
    }

    def __init__(self, client: N8nApiClient):
        """Initialize workflow tools.

        Args:
            client: N8nApiClient instance
        """
        self._client = client

    @staticmethod
    def get_schemas() -> List[ToolSchema]:
        """Get all workflow tool schemas.

        Returns:
            List of ToolSchema definitions for MCP protocol
        """
        return [
            ToolSchema(
                name="n8n_list_workflows",
                description=(
                    "List all n8n workflows. Optionally filter by active status "
                    "or tags. Returns workflow ID, name, active status, and timestamps."
                ),
                parameters=[
                    ToolParameter(
                        name="active",
                        type=ToolInputType.BOOLEAN,
                        description="Filter by active status (true/false). Omit to list all.",
                        required=False,
                    ),
                    ToolParameter(
                        name="tags",
                        type=ToolInputType.STRING,
                        description="Filter by tag name.",
                        required=False,
                    ),
                    ToolParameter(
                        name="limit",
                        type=ToolInputType.INTEGER,
                        description="Maximum number of workflows to return (default: 50).",
                        required=False,
                        default=50,
                    ),
                ],
                returns="List of workflows with id, name, active, createdAt, updatedAt",
            ),
            ToolSchema(
                name="n8n_get_workflow",
                description=(
                    "Get detailed information about a specific n8n workflow, "
                    "including its nodes, connections, and settings."
                ),
                parameters=[
                    ToolParameter(
                        name="workflow_id",
                        type=ToolInputType.STRING,
                        description="The n8n workflow ID.",
                        required=True,
                    ),
                ],
                returns="Workflow object with nodes, connections, settings, and metadata",
            ),
            ToolSchema(
                name="n8n_activate_workflow",
                description=(
                    "Activate or deactivate an n8n workflow. Active workflows "
                    "can be triggered by external events (webhooks, schedules)."
                ),
                parameters=[
                    ToolParameter(
                        name="workflow_id",
                        type=ToolInputType.STRING,
                        description="The n8n workflow ID.",
                        required=True,
                    ),
                    ToolParameter(
                        name="active",
                        type=ToolInputType.BOOLEAN,
                        description="Set to true to activate, false to deactivate.",
                        required=True,
                    ),
                ],
                returns="Updated workflow object with new active status",
            ),
        ]

    async def n8n_list_workflows(
        self,
        active: Optional[bool] = None,
        tags: Optional[str] = None,
        limit: int = 50,
        **kwargs: Any,
    ) -> ToolResult:
        """List all n8n workflows.

        Args:
            active: Filter by active status
            tags: Filter by tag name
            limit: Maximum results (default: 50)

        Returns:
            ToolResult with list of workflows
        """
        try:
            result = await self._client.list_workflows(
                active=active,
                tags=tags,
                limit=limit,
            )

            workflows = result.get("data", [])
            summary = []
            for wf in workflows:
                summary.append({
                    "id": wf.get("id"),
                    "name": wf.get("name"),
                    "active": wf.get("active"),
                    "createdAt": wf.get("createdAt"),
                    "updatedAt": wf.get("updatedAt"),
                    "tags": [t.get("name") for t in wf.get("tags", [])],
                })

            return ToolResult(
                success=True,
                content={
                    "workflows": summary,
                    "count": len(summary),
                    "nextCursor": result.get("nextCursor"),
                },
            )

        except N8nApiError as e:
            logger.error(f"Failed to list workflows: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Failed to list workflows: {e}",
            )

    async def n8n_get_workflow(
        self,
        workflow_id: str,
        **kwargs: Any,
    ) -> ToolResult:
        """Get detailed workflow information.

        Args:
            workflow_id: n8n workflow ID

        Returns:
            ToolResult with workflow details
        """
        if not workflow_id:
            return ToolResult(
                success=False,
                content=None,
                error="workflow_id is required",
            )

        try:
            workflow = await self._client.get_workflow(workflow_id)

            # Extract node summary for readability
            nodes = workflow.get("nodes", [])
            node_summary = [
                {
                    "name": n.get("name"),
                    "type": n.get("type"),
                    "position": n.get("position"),
                }
                for n in nodes
            ]

            return ToolResult(
                success=True,
                content={
                    "id": workflow.get("id"),
                    "name": workflow.get("name"),
                    "active": workflow.get("active"),
                    "nodes": node_summary,
                    "nodeCount": len(nodes),
                    "connections": workflow.get("connections", {}),
                    "settings": workflow.get("settings", {}),
                    "createdAt": workflow.get("createdAt"),
                    "updatedAt": workflow.get("updatedAt"),
                    "tags": [t.get("name") for t in workflow.get("tags", [])],
                },
            )

        except N8nNotFoundError:
            return ToolResult(
                success=False,
                content=None,
                error=f"Workflow not found: {workflow_id}",
            )
        except N8nApiError as e:
            logger.error(f"Failed to get workflow {workflow_id}: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Failed to get workflow: {e}",
            )

    async def n8n_activate_workflow(
        self,
        workflow_id: str,
        active: bool,
        **kwargs: Any,
    ) -> ToolResult:
        """Activate or deactivate a workflow.

        Args:
            workflow_id: n8n workflow ID
            active: True to activate, False to deactivate

        Returns:
            ToolResult with updated workflow status
        """
        if not workflow_id:
            return ToolResult(
                success=False,
                content=None,
                error="workflow_id is required",
            )

        try:
            result = await self._client.activate_workflow(workflow_id, active)

            action = "activated" if active else "deactivated"
            return ToolResult(
                success=True,
                content={
                    "id": result.get("id"),
                    "name": result.get("name"),
                    "active": result.get("active"),
                    "message": f"Workflow '{result.get('name')}' {action} successfully",
                },
            )

        except N8nNotFoundError:
            return ToolResult(
                success=False,
                content=None,
                error=f"Workflow not found: {workflow_id}",
            )
        except N8nApiError as e:
            logger.error(f"Failed to activate workflow {workflow_id}: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Failed to activate workflow: {e}",
            )
