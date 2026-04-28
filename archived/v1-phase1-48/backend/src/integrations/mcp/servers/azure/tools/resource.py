"""Azure Resource Management Tools.

Provides MCP tools for resource group and resource management operations.

Tools:
    - list_resource_groups: List all resource groups
    - get_resource_group: Get resource group details
    - list_resources: List resources in a resource group
    - search_resources: Search resources by type or tag
"""

from typing import Any, Dict, List, Optional
import logging

from ....core.types import (
    ToolSchema,
    ToolParameter,
    ToolInputType,
    ToolResult,
)
from ..client import AzureClientManager

logger = logging.getLogger(__name__)


class ResourceTools:
    """Resource management tools for Azure MCP Server.

    Provides resource discovery and management capabilities.

    Permission Levels:
        - Level 1 (READ): All tools (read-only operations)

    Example:
        >>> manager = AzureClientManager(config)
        >>> tools = ResourceTools(manager)
        >>> result = await tools.list_resource_groups()
        >>> print(result.content)
    """

    # Permission levels for tools
    PERMISSION_LEVELS = {
        "list_resource_groups": 1,
        "get_resource_group": 1,
        "list_resources": 1,
        "search_resources": 1,
    }

    def __init__(self, client_manager: AzureClientManager):
        """Initialize Resource tools.

        Args:
            client_manager: Azure client manager instance
        """
        self._manager = client_manager

    @staticmethod
    def get_schemas() -> List[ToolSchema]:
        """Get all Resource tool schemas.

        Returns:
            List of ToolSchema definitions for MCP protocol
        """
        return [
            ToolSchema(
                name="list_resource_groups",
                description="List all resource groups in the subscription",
                parameters=[
                    ToolParameter(
                        name="tag_filter",
                        type=ToolInputType.OBJECT,
                        description="Optional tag filter (e.g., {\"environment\": \"production\"})",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="get_resource_group",
                description="Get details of a specific resource group",
                parameters=[
                    ToolParameter(
                        name="resource_group",
                        type=ToolInputType.STRING,
                        description="Resource group name",
                        required=True,
                    ),
                ],
            ),
            ToolSchema(
                name="list_resources",
                description="List all resources in a resource group",
                parameters=[
                    ToolParameter(
                        name="resource_group",
                        type=ToolInputType.STRING,
                        description="Resource group name",
                        required=True,
                    ),
                    ToolParameter(
                        name="resource_type",
                        type=ToolInputType.STRING,
                        description="Optional resource type filter (e.g., Microsoft.Compute/virtualMachines)",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="search_resources",
                description="Search for resources across the subscription",
                parameters=[
                    ToolParameter(
                        name="resource_type",
                        type=ToolInputType.STRING,
                        description="Resource type to search for",
                        required=False,
                    ),
                    ToolParameter(
                        name="tag_name",
                        type=ToolInputType.STRING,
                        description="Tag name to filter by",
                        required=False,
                    ),
                    ToolParameter(
                        name="tag_value",
                        type=ToolInputType.STRING,
                        description="Tag value to filter by",
                        required=False,
                    ),
                    ToolParameter(
                        name="name_contains",
                        type=ToolInputType.STRING,
                        description="Filter resources whose name contains this string",
                        required=False,
                    ),
                ],
            ),
        ]

    async def list_resource_groups(
        self,
        tag_filter: Optional[Dict[str, str]] = None,
    ) -> ToolResult:
        """List all resource groups.

        Args:
            tag_filter: Optional tag filter

        Returns:
            ToolResult with list of resource groups
        """
        try:
            resource = self._manager.resource
            rgs = resource.resource_groups.list()

            rg_list = []
            for rg in rgs:
                # Apply tag filter if specified
                if tag_filter:
                    if not rg.tags:
                        continue
                    match = all(
                        rg.tags.get(k) == v for k, v in tag_filter.items()
                    )
                    if not match:
                        continue

                rg_list.append({
                    "name": rg.name,
                    "location": rg.location,
                    "provisioning_state": rg.properties.provisioning_state if rg.properties else None,
                    "tags": rg.tags or {},
                    "id": rg.id,
                })

            logger.info(f"Found {len(rg_list)} resource groups")
            return ToolResult(
                success=True,
                content=rg_list,
                metadata={"count": len(rg_list)},
            )

        except Exception as e:
            logger.error(f"Failed to list resource groups: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )

    async def get_resource_group(
        self,
        resource_group: str,
    ) -> ToolResult:
        """Get resource group details.

        Args:
            resource_group: Resource group name

        Returns:
            ToolResult with resource group details
        """
        try:
            resource = self._manager.resource
            rg = resource.resource_groups.get(resource_group)

            logger.info(f"Retrieved resource group: {resource_group}")
            return ToolResult(
                success=True,
                content={
                    "name": rg.name,
                    "location": rg.location,
                    "provisioning_state": rg.properties.provisioning_state if rg.properties else None,
                    "tags": rg.tags or {},
                    "id": rg.id,
                    "managed_by": rg.managed_by,
                },
            )

        except Exception as e:
            logger.error(f"Failed to get resource group {resource_group}: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )

    async def list_resources(
        self,
        resource_group: str,
        resource_type: Optional[str] = None,
    ) -> ToolResult:
        """List resources in a resource group.

        Args:
            resource_group: Resource group name
            resource_type: Optional resource type filter

        Returns:
            ToolResult with list of resources
        """
        try:
            resource = self._manager.resource

            # Build filter
            filter_str = None
            if resource_type:
                filter_str = f"resourceType eq '{resource_type}'"

            resources = resource.resources.list_by_resource_group(
                resource_group,
                filter=filter_str,
            )

            resource_list = []
            for res in resources:
                resource_list.append({
                    "name": res.name,
                    "type": res.type,
                    "location": res.location,
                    "id": res.id,
                    "tags": res.tags or {},
                    "provisioning_state": res.provisioning_state,
                    "kind": res.kind,
                })

            logger.info(f"Found {len(resource_list)} resources in {resource_group}")
            return ToolResult(
                success=True,
                content=resource_list,
                metadata={
                    "count": len(resource_list),
                    "resource_group": resource_group,
                },
            )

        except Exception as e:
            logger.error(f"Failed to list resources in {resource_group}: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )

    async def search_resources(
        self,
        resource_type: Optional[str] = None,
        tag_name: Optional[str] = None,
        tag_value: Optional[str] = None,
        name_contains: Optional[str] = None,
    ) -> ToolResult:
        """Search for resources.

        Args:
            resource_type: Resource type to search for
            tag_name: Tag name to filter by
            tag_value: Tag value to filter by
            name_contains: Filter by name substring

        Returns:
            ToolResult with matching resources
        """
        try:
            resource = self._manager.resource

            # Build filter
            filters = []
            if resource_type:
                filters.append(f"resourceType eq '{resource_type}'")
            if tag_name and tag_value:
                filters.append(f"tagName eq '{tag_name}' and tagValue eq '{tag_value}'")
            elif tag_name:
                filters.append(f"tagName eq '{tag_name}'")

            filter_str = " and ".join(filters) if filters else None

            resources = resource.resources.list(filter=filter_str)

            resource_list = []
            for res in resources:
                # Apply name filter client-side
                if name_contains and name_contains.lower() not in res.name.lower():
                    continue

                resource_list.append({
                    "name": res.name,
                    "type": res.type,
                    "location": res.location,
                    "resource_group": self._extract_resource_group(res.id),
                    "id": res.id,
                    "tags": res.tags or {},
                })

            logger.info(f"Found {len(resource_list)} matching resources")
            return ToolResult(
                success=True,
                content=resource_list,
                metadata={"count": len(resource_list)},
            )

        except Exception as e:
            logger.error(f"Failed to search resources: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )

    def _extract_resource_group(self, resource_id: str) -> str:
        """Extract resource group name from resource ID.

        Args:
            resource_id: Azure resource ID

        Returns:
            Resource group name
        """
        try:
            parts = resource_id.split("/")
            idx = parts.index("resourceGroups")
            return parts[idx + 1]
        except (ValueError, IndexError):
            return "unknown"
