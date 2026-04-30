"""D365 Query Tools for MCP Server.

Provides tools for querying and discovering Dynamics 365 entities
through the OData v4 Web API.

Tools:
    - d365_query_entities: Query entity records with OData filtering
    - d365_get_record: Get a single entity record by ID
    - d365_list_entity_types: List all customizable entity types
    - d365_get_entity_metadata: Get metadata for a specific entity type

Sprint 129: Story 129-2
"""

import logging
from typing import Any, Dict, List, Optional

from ....core.types import (
    ToolInputType,
    ToolParameter,
    ToolResult,
    ToolSchema,
)
from ..client import D365ApiClient, D365NotFoundError, ODataQueryBuilder

logger = logging.getLogger(__name__)


class QueryTools:
    """Query tools for D365 MCP Server.

    Provides entity querying and metadata discovery capabilities
    through the MCP protocol using the Dynamics 365 OData v4 Web API.

    Permission Levels:
        - Level 1 (READ): All query tools

    Example:
        >>> client = D365ApiClient(config)
        >>> tools = QueryTools(client)
        >>> result = await tools.d365_query_entities(entity_name="account")
        >>> print(result.content)
    """

    PERMISSION_LEVELS = {
        "d365_query_entities": 1,
        "d365_get_record": 1,
        "d365_list_entity_types": 1,
        "d365_get_entity_metadata": 1,
    }

    def __init__(self, client: D365ApiClient):
        """Initialize query tools.

        Args:
            client: D365ApiClient instance
        """
        self._client = client

    @staticmethod
    def get_schemas() -> List[ToolSchema]:
        """Get all query tool schemas.

        Returns:
            List of ToolSchema definitions for MCP protocol
        """
        return [
            ToolSchema(
                name="d365_query_entities",
                description=(
                    "Query Dynamics 365 entity records with OData v4 filtering. "
                    "Supports $filter, $select, $top, and $orderby query options."
                ),
                parameters=[
                    ToolParameter(
                        name="entity_name",
                        type=ToolInputType.STRING,
                        description=(
                            "Logical entity name (e.g. 'account', 'contact', "
                            "'incident', 'msdyn_workorder')."
                        ),
                        required=True,
                    ),
                    ToolParameter(
                        name="filter",
                        type=ToolInputType.STRING,
                        description=(
                            "OData $filter expression. "
                            "Example: \"statecode eq 0 and name ne null\""
                        ),
                        required=False,
                    ),
                    ToolParameter(
                        name="select",
                        type=ToolInputType.STRING,
                        description=(
                            "Comma-separated list of fields to return. "
                            "Example: \"name,accountnumber,statecode\""
                        ),
                        required=False,
                    ),
                    ToolParameter(
                        name="top",
                        type=ToolInputType.INTEGER,
                        description=(
                            "Maximum number of records to return. "
                            "Example: 10"
                        ),
                        required=False,
                    ),
                    ToolParameter(
                        name="orderby",
                        type=ToolInputType.STRING,
                        description=(
                            "Field and direction for sorting. "
                            "Example: \"name asc\" or \"createdon desc\""
                        ),
                        required=False,
                    ),
                ],
                returns="Query results with total count, records, and pagination indicator",
            ),
            ToolSchema(
                name="d365_get_record",
                description=(
                    "Get a single Dynamics 365 entity record by its GUID. "
                    "Optionally select specific fields to return."
                ),
                parameters=[
                    ToolParameter(
                        name="entity_name",
                        type=ToolInputType.STRING,
                        description=(
                            "Logical entity name (e.g. 'account', 'contact')."
                        ),
                        required=True,
                    ),
                    ToolParameter(
                        name="record_id",
                        type=ToolInputType.STRING,
                        description="The GUID of the record to retrieve.",
                        required=True,
                    ),
                    ToolParameter(
                        name="select",
                        type=ToolInputType.STRING,
                        description=(
                            "Comma-separated list of fields to return. "
                            "Example: \"name,emailaddress1\""
                        ),
                        required=False,
                    ),
                ],
                returns="Entity record dictionary with requested fields",
            ),
            ToolSchema(
                name="d365_list_entity_types",
                description=(
                    "List all customizable entity types in Dynamics 365. "
                    "Returns logical names, display names, and entity set names."
                ),
                parameters=[],
                returns="List of entity types with logical name, display name, and entity set name",
            ),
            ToolSchema(
                name="d365_get_entity_metadata",
                description=(
                    "Get metadata for a specific Dynamics 365 entity type, "
                    "including primary key attribute, primary name attribute, "
                    "and entity set name."
                ),
                parameters=[
                    ToolParameter(
                        name="entity_name",
                        type=ToolInputType.STRING,
                        description=(
                            "Logical entity name (e.g. 'account', 'contact')."
                        ),
                        required=True,
                    ),
                ],
                returns="Entity metadata with logical name, display name, and attribute info",
            ),
        ]

    async def d365_query_entities(
        self,
        entity_name: str,
        filter: Optional[str] = None,
        select: Optional[str] = None,
        top: Optional[int] = None,
        orderby: Optional[str] = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Query D365 entity records with OData filtering.

        Args:
            entity_name: Logical entity name
            filter: OData $filter expression
            select: Comma-separated fields to return
            top: Maximum number of records
            orderby: Sort field and direction (e.g. "name asc")

        Returns:
            ToolResult with query results
        """
        if not entity_name:
            return ToolResult(
                success=False,
                content=None,
                error="entity_name is required",
            )

        try:
            query = ODataQueryBuilder()

            if filter:
                query.filter(filter)

            if select:
                fields = [f.strip() for f in select.split(",")]
                query.select(*fields)

            if top is not None:
                query.top(top)

            if orderby:
                parts = orderby.strip().split()
                field_name = parts[0]
                desc = len(parts) > 1 and parts[1].lower() == "desc"
                query.orderby(field_name, desc=desc)

            result = await self._client.query_entities(entity_name, query)
            records = result.get("value", [])
            next_link = result.get("@odata.nextLink")

            return ToolResult(
                success=True,
                content={
                    "total": len(records),
                    "records": records,
                    "has_more": next_link is not None,
                },
            )

        except D365NotFoundError:
            return ToolResult(
                success=False,
                content=None,
                error=f"Entity type not found: {entity_name}",
            )
        except Exception as e:
            logger.error(f"Failed to query entities '{entity_name}': {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Failed to query entities: {e}",
            )

    async def d365_get_record(
        self,
        entity_name: str,
        record_id: str,
        select: Optional[str] = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Get a single D365 entity record by ID.

        Args:
            entity_name: Logical entity name
            record_id: GUID of the record
            select: Comma-separated fields to return

        Returns:
            ToolResult with the record
        """
        if not entity_name:
            return ToolResult(
                success=False,
                content=None,
                error="entity_name is required",
            )

        if not record_id:
            return ToolResult(
                success=False,
                content=None,
                error="record_id is required",
            )

        try:
            select_fields = None
            if select:
                select_fields = [f.strip() for f in select.split(",")]

            record = await self._client.get_record(
                entity_name=entity_name,
                record_id=record_id,
                select=select_fields,
            )

            return ToolResult(
                success=True,
                content=record,
            )

        except D365NotFoundError:
            return ToolResult(
                success=False,
                content=None,
                error=f"Record not found: {entity_name}({record_id})",
            )
        except Exception as e:
            logger.error(
                f"Failed to get record {entity_name}({record_id}): {e}"
            )
            return ToolResult(
                success=False,
                content=None,
                error=f"Failed to get record: {e}",
            )

    async def d365_list_entity_types(self, **kwargs: Any) -> ToolResult:
        """List all customizable D365 entity types.

        Returns:
            ToolResult with list of entity types
        """
        try:
            entity_types = await self._client.list_entity_types()

            summary = []
            for entity in entity_types:
                display_name_obj = entity.get("DisplayName", {})
                localized = display_name_obj.get("LocalizedLabels", [])
                display_name = (
                    localized[0].get("Label", "") if localized else ""
                )

                summary.append({
                    "logical_name": entity.get("LogicalName", ""),
                    "display_name": display_name,
                    "entity_set_name": entity.get("EntitySetName", ""),
                })

            return ToolResult(
                success=True,
                content={
                    "total": len(summary),
                    "entity_types": summary,
                },
            )

        except Exception as e:
            logger.error(f"Failed to list entity types: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Failed to list entity types: {e}",
            )

    async def d365_get_entity_metadata(
        self,
        entity_name: str,
        **kwargs: Any,
    ) -> ToolResult:
        """Get metadata for a specific D365 entity type.

        Args:
            entity_name: Logical entity name

        Returns:
            ToolResult with entity metadata
        """
        if not entity_name:
            return ToolResult(
                success=False,
                content=None,
                error="entity_name is required",
            )

        try:
            metadata = await self._client.get_entity_metadata(entity_name)

            return ToolResult(
                success=True,
                content=metadata,
            )

        except D365NotFoundError:
            return ToolResult(
                success=False,
                content=None,
                error=f"Entity type not found: {entity_name}",
            )
        except Exception as e:
            logger.error(
                f"Failed to get entity metadata for '{entity_name}': {e}"
            )
            return ToolResult(
                success=False,
                content=None,
                error=f"Failed to get entity metadata: {e}",
            )
