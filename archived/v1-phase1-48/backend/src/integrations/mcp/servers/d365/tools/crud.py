"""D365 CRUD Tools for MCP Server.

Provides tools for creating and updating Dynamics 365 entity records
through the OData v4 Web API.

Tools:
    - d365_create_record: Create a new entity record
    - d365_update_record: Update an existing entity record

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
from ..client import D365ApiClient, D365NotFoundError, D365ValidationError

logger = logging.getLogger(__name__)


class CrudTools:
    """CRUD tools for D365 MCP Server.

    Provides entity record creation and update capabilities
    through the MCP protocol using the Dynamics 365 OData v4 Web API.

    Permission Levels:
        - Level 2 (EXECUTE): create_record, update_record

    Example:
        >>> client = D365ApiClient(config)
        >>> tools = CrudTools(client)
        >>> result = await tools.d365_create_record(
        ...     entity_name="account",
        ...     data={"name": "Contoso Ltd"},
        ... )
        >>> print(result.content)
    """

    PERMISSION_LEVELS = {
        "d365_create_record": 2,
        "d365_update_record": 2,
    }

    def __init__(self, client: D365ApiClient):
        """Initialize CRUD tools.

        Args:
            client: D365ApiClient instance
        """
        self._client = client

    @staticmethod
    def get_schemas() -> List[ToolSchema]:
        """Get all CRUD tool schemas.

        Returns:
            List of ToolSchema definitions for MCP protocol
        """
        return [
            ToolSchema(
                name="d365_create_record",
                description=(
                    "Create a new Dynamics 365 entity record. "
                    "Provide the entity name and a data object with field values."
                ),
                parameters=[
                    ToolParameter(
                        name="entity_name",
                        type=ToolInputType.STRING,
                        description=(
                            "Logical entity name (e.g. 'account', 'contact', "
                            "'incident')."
                        ),
                        required=True,
                    ),
                    ToolParameter(
                        name="data",
                        type=ToolInputType.OBJECT,
                        description=(
                            "Record field values as key-value pairs. "
                            "Example: {\"name\": \"Contoso Ltd\", "
                            "\"accountnumber\": \"ACC-001\"}"
                        ),
                        required=True,
                    ),
                ],
                returns="Created record ID, entity name, and confirmation message",
            ),
            ToolSchema(
                name="d365_update_record",
                description=(
                    "Update an existing Dynamics 365 entity record. "
                    "Only the specified fields will be modified (partial update)."
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
                        description="The GUID of the record to update.",
                        required=True,
                    ),
                    ToolParameter(
                        name="data",
                        type=ToolInputType.OBJECT,
                        description=(
                            "Fields to update as key-value pairs. "
                            "Example: {\"name\": \"Updated Name\", "
                            "\"statecode\": 1}"
                        ),
                        required=True,
                    ),
                ],
                returns="Updated record ID, entity name, and confirmation message",
            ),
        ]

    async def d365_create_record(
        self,
        entity_name: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Create a new D365 entity record.

        Args:
            entity_name: Logical entity name
            data: Record field values

        Returns:
            ToolResult with created record info
        """
        if not entity_name:
            return ToolResult(
                success=False,
                content=None,
                error="entity_name is required",
            )

        if not data:
            return ToolResult(
                success=False,
                content=None,
                error="data is required and must not be empty",
            )

        try:
            logger.info(
                "Creating D365 record in entity '%s' with fields: %s",
                entity_name,
                list(data.keys()),
            )

            result = await self._client.create_record(
                entity_name=entity_name,
                data=data,
            )

            # Extract record ID from response
            record_id = result.get("id", "unknown")
            # Some responses include the primary ID attribute directly
            if record_id == "unknown":
                # Try common ID patterns
                for key in result:
                    if key.endswith("id") and isinstance(result[key], str):
                        record_id = result[key]
                        break

            return ToolResult(
                success=True,
                content={
                    "record_id": record_id,
                    "entity_name": entity_name,
                    "message": "Record created successfully",
                },
                metadata={
                    "entity_name": entity_name,
                    "record_id": record_id,
                },
            )

        except D365ValidationError as e:
            return ToolResult(
                success=False,
                content=None,
                error=f"Validation error creating record: {e}",
            )
        except Exception as e:
            logger.error(
                f"Failed to create record in '{entity_name}': {e}"
            )
            return ToolResult(
                success=False,
                content=None,
                error=f"Failed to create record: {e}",
            )

    async def d365_update_record(
        self,
        entity_name: str,
        record_id: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Update an existing D365 entity record.

        Args:
            entity_name: Logical entity name
            record_id: GUID of the record to update
            data: Fields to update

        Returns:
            ToolResult with update confirmation
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

        if not data:
            return ToolResult(
                success=False,
                content=None,
                error="data is required and must not be empty",
            )

        try:
            logger.info(
                "Updating D365 record '%s' in entity '%s' with fields: %s",
                record_id,
                entity_name,
                list(data.keys()),
            )

            await self._client.update_record(
                entity_name=entity_name,
                record_id=record_id,
                data=data,
            )

            return ToolResult(
                success=True,
                content={
                    "record_id": record_id,
                    "entity_name": entity_name,
                    "message": "Record updated successfully",
                },
                metadata={
                    "entity_name": entity_name,
                    "record_id": record_id,
                },
            )

        except D365NotFoundError:
            return ToolResult(
                success=False,
                content=None,
                error=f"Record not found: {entity_name}({record_id})",
            )
        except D365ValidationError as e:
            return ToolResult(
                success=False,
                content=None,
                error=f"Validation error updating record: {e}",
            )
        except Exception as e:
            logger.error(
                f"Failed to update record {entity_name}({record_id}): {e}"
            )
            return ToolResult(
                success=False,
                content=None,
                error=f"Failed to update record: {e}",
            )
