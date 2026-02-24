"""ServiceNow MCP Server — 6 core tools for Incident and RITM operations.

Registers ServiceNow tools with the MCP protocol handler, enabling
AI agents to create/read/update incidents, create/read RITMs,
and attach files via standardized MCP tool calls.

Sprint 117 — ServiceNow MCP Server
"""

import json
import logging
from typing import Any, Dict, List, Optional

from .core.protocol import MCPProtocol
from .core.types import (
    MCPRequest,
    ToolInputType,
    ToolParameter,
    ToolResult,
    ToolSchema,
)
from .servicenow_client import (
    ServiceNowAuthError,
    ServiceNowClient,
    ServiceNowError,
    ServiceNowNotFoundError,
    ServiceNowPermissionError,
    ServiceNowServerError,
)
from .servicenow_config import ServiceNowConfig

logger = logging.getLogger(__name__)


class ServiceNowMCPServer:
    """MCP Server for ServiceNow operations.

    Provides 6 core tools for interacting with ServiceNow via the MCP protocol:
      1. create_incident — Create a new Incident
      2. update_incident — Update an existing Incident
      3. get_incident — Query an Incident by number or sys_id
      4. create_ritm — Create a Requested Item (RITM)
      5. get_ritm_status — Query RITM status
      6. add_attachment — Add a file attachment to any record

    Example:
        >>> config = ServiceNowConfig.from_env()
        >>> client = ServiceNowClient(config)
        >>> server = ServiceNowMCPServer(client)
        >>> tools = server.get_tools()
        >>> result = await server.call_tool("get_incident", {"number": "INC0010001"})
    """

    SERVER_NAME = "servicenow-mcp"
    SERVER_VERSION = "1.0.0"

    # Permission levels for each tool (0=NONE, 1=READ, 2=EXECUTE, 3=ADMIN)
    PERMISSION_LEVELS: Dict[str, int] = {
        "create_incident": 2,
        "update_incident": 2,
        "get_incident": 1,
        "create_ritm": 2,
        "get_ritm_status": 1,
        "add_attachment": 2,
    }

    def __init__(self, client: ServiceNowClient) -> None:
        self._client = client
        self._protocol = MCPProtocol()
        self._running = False
        self._register_all_tools()

    # =========================================================================
    # Tool Schema Definitions
    # =========================================================================

    @staticmethod
    def get_tool_schemas() -> List[ToolSchema]:
        """Return all tool schemas for registration."""
        return [
            # ---- create_incident ----
            ToolSchema(
                name="create_incident",
                description=(
                    "Create a new ServiceNow incident. Use this when a user reports "
                    "an issue that needs tracking, such as system outages, service "
                    "degradation, or access problems."
                ),
                parameters=[
                    ToolParameter(
                        name="short_description",
                        type=ToolInputType.STRING,
                        description="Brief summary of the incident (max 160 chars)",
                        required=True,
                    ),
                    ToolParameter(
                        name="description",
                        type=ToolInputType.STRING,
                        description="Detailed incident description including impact and symptoms",
                        required=True,
                    ),
                    ToolParameter(
                        name="category",
                        type=ToolInputType.STRING,
                        description="Incident category",
                        required=False,
                        default="inquiry",
                        enum=[
                            "inquiry",
                            "software",
                            "hardware",
                            "network",
                            "database",
                        ],
                    ),
                    ToolParameter(
                        name="urgency",
                        type=ToolInputType.STRING,
                        description="Urgency level: 1=High, 2=Medium, 3=Low",
                        required=False,
                        default="3",
                        enum=["1", "2", "3"],
                    ),
                    ToolParameter(
                        name="assignment_group",
                        type=ToolInputType.STRING,
                        description="sys_id of the assignment group",
                        required=False,
                    ),
                    ToolParameter(
                        name="caller_id",
                        type=ToolInputType.STRING,
                        description="sys_id of the caller/reporter",
                        required=False,
                    ),
                ],
            ),
            # ---- update_incident ----
            ToolSchema(
                name="update_incident",
                description=(
                    "Update an existing ServiceNow incident. Use this to change "
                    "the state, add comments, reassign, or update any incident field."
                ),
                parameters=[
                    ToolParameter(
                        name="sys_id",
                        type=ToolInputType.STRING,
                        description="The sys_id of the incident to update",
                        required=True,
                    ),
                    ToolParameter(
                        name="state",
                        type=ToolInputType.STRING,
                        description="Incident state: 1=New, 2=InProgress, 3=OnHold, 6=Resolved, 7=Closed",
                        required=False,
                        enum=["1", "2", "3", "6", "7"],
                    ),
                    ToolParameter(
                        name="assignment_group",
                        type=ToolInputType.STRING,
                        description="sys_id of the new assignment group",
                        required=False,
                    ),
                    ToolParameter(
                        name="work_notes",
                        type=ToolInputType.STRING,
                        description="Work notes to add (internal)",
                        required=False,
                    ),
                    ToolParameter(
                        name="comments",
                        type=ToolInputType.STRING,
                        description="Additional comments (visible to caller)",
                        required=False,
                    ),
                    ToolParameter(
                        name="close_code",
                        type=ToolInputType.STRING,
                        description="Close code when resolving",
                        required=False,
                    ),
                    ToolParameter(
                        name="close_notes",
                        type=ToolInputType.STRING,
                        description="Resolution notes when resolving",
                        required=False,
                    ),
                ],
            ),
            # ---- get_incident ----
            ToolSchema(
                name="get_incident",
                description=(
                    "Look up a ServiceNow incident by number or sys_id. "
                    "Returns the full incident record with current state, "
                    "assignment, and timeline."
                ),
                parameters=[
                    ToolParameter(
                        name="number",
                        type=ToolInputType.STRING,
                        description="Incident number (e.g., INC0010001)",
                        required=False,
                    ),
                    ToolParameter(
                        name="sys_id",
                        type=ToolInputType.STRING,
                        description="Incident sys_id",
                        required=False,
                    ),
                ],
            ),
            # ---- create_ritm ----
            ToolSchema(
                name="create_ritm",
                description=(
                    "Create a ServiceNow Requested Item (RITM) from a catalog item. "
                    "Use this for service requests like AD account creation, "
                    "software installation, or access provisioning."
                ),
                parameters=[
                    ToolParameter(
                        name="cat_item",
                        type=ToolInputType.STRING,
                        description="Catalog item sys_id",
                        required=True,
                    ),
                    ToolParameter(
                        name="variables",
                        type=ToolInputType.OBJECT,
                        description="Catalog item variable values as key-value pairs",
                        required=True,
                    ),
                    ToolParameter(
                        name="requested_for",
                        type=ToolInputType.STRING,
                        description="sys_id of the person the item is requested for",
                        required=True,
                    ),
                    ToolParameter(
                        name="short_description",
                        type=ToolInputType.STRING,
                        description="Brief description of the request",
                        required=True,
                    ),
                ],
            ),
            # ---- get_ritm_status ----
            ToolSchema(
                name="get_ritm_status",
                description=(
                    "Check the status of a ServiceNow Requested Item (RITM). "
                    "Returns the current approval state, fulfillment status, "
                    "and associated task details."
                ),
                parameters=[
                    ToolParameter(
                        name="number",
                        type=ToolInputType.STRING,
                        description="RITM number (e.g., RITM0010001)",
                        required=False,
                    ),
                    ToolParameter(
                        name="sys_id",
                        type=ToolInputType.STRING,
                        description="RITM sys_id",
                        required=False,
                    ),
                ],
            ),
            # ---- add_attachment ----
            ToolSchema(
                name="add_attachment",
                description=(
                    "Attach a file to a ServiceNow record (incident, RITM, etc.). "
                    "Use this to attach log files, screenshots, or configuration "
                    "files to existing records."
                ),
                parameters=[
                    ToolParameter(
                        name="table",
                        type=ToolInputType.STRING,
                        description="Table name (e.g., incident, sc_req_item)",
                        required=True,
                        enum=["incident", "sc_req_item", "change_request", "problem"],
                    ),
                    ToolParameter(
                        name="sys_id",
                        type=ToolInputType.STRING,
                        description="Record sys_id to attach the file to",
                        required=True,
                    ),
                    ToolParameter(
                        name="file_name",
                        type=ToolInputType.STRING,
                        description="Name for the attached file",
                        required=True,
                    ),
                    ToolParameter(
                        name="content",
                        type=ToolInputType.STRING,
                        description="File content (text or base64-encoded binary)",
                        required=True,
                    ),
                    ToolParameter(
                        name="content_type",
                        type=ToolInputType.STRING,
                        description="MIME type of the file",
                        required=False,
                        default="text/plain",
                    ),
                ],
            ),
        ]

    # =========================================================================
    # Tool Registration
    # =========================================================================

    def _register_all_tools(self) -> None:
        """Register all 6 tools with the MCP protocol handler."""
        handler_map = {
            "create_incident": self._handle_create_incident,
            "update_incident": self._handle_update_incident,
            "get_incident": self._handle_get_incident,
            "create_ritm": self._handle_create_ritm,
            "get_ritm_status": self._handle_get_ritm_status,
            "add_attachment": self._handle_add_attachment,
        }

        for schema in self.get_tool_schemas():
            handler = handler_map[schema.name]
            self._protocol.register_tool(schema.name, handler, schema)

        for tool_name, level in self.PERMISSION_LEVELS.items():
            self._protocol.set_tool_permission_level(tool_name, level)

        logger.info(
            "ServiceNow MCP Server registered %d tools",
            len(handler_map),
        )

    # =========================================================================
    # Tool Handlers
    # =========================================================================

    async def _handle_create_incident(self, **kwargs: Any) -> ToolResult:
        """Handle create_incident tool call."""
        try:
            result = await self._client.create_incident(
                short_description=kwargs["short_description"],
                description=kwargs["description"],
                category=kwargs.get("category", "inquiry"),
                urgency=kwargs.get("urgency", "3"),
                assignment_group=kwargs.get("assignment_group"),
                caller_id=kwargs.get("caller_id"),
            )
            return ToolResult(
                success=True,
                content=result,
                metadata={"tool": "create_incident", "table": "incident"},
            )
        except ServiceNowError as e:
            return self._error_result("create_incident", e)

    async def _handle_update_incident(self, **kwargs: Any) -> ToolResult:
        """Handle update_incident tool call."""
        try:
            sys_id = kwargs["sys_id"]
            updates: Dict[str, Any] = {}
            for field in [
                "state",
                "assignment_group",
                "work_notes",
                "comments",
                "close_code",
                "close_notes",
            ]:
                if field in kwargs and kwargs[field] is not None:
                    updates[field] = kwargs[field]

            if not updates:
                return ToolResult(
                    success=False,
                    content=None,
                    error="No update fields provided",
                    metadata={"tool": "update_incident"},
                )

            result = await self._client.update_incident(sys_id, updates)
            return ToolResult(
                success=True,
                content=result,
                metadata={
                    "tool": "update_incident",
                    "sys_id": sys_id,
                    "updated_fields": list(updates.keys()),
                },
            )
        except ServiceNowError as e:
            return self._error_result("update_incident", e)

    async def _handle_get_incident(self, **kwargs: Any) -> ToolResult:
        """Handle get_incident tool call."""
        try:
            number = kwargs.get("number")
            sys_id = kwargs.get("sys_id")

            if not number and not sys_id:
                return ToolResult(
                    success=False,
                    content=None,
                    error="Either 'number' or 'sys_id' must be provided",
                    metadata={"tool": "get_incident"},
                )

            result = await self._client.get_incident(number=number, sys_id=sys_id)
            if result is None:
                return ToolResult(
                    success=True,
                    content=None,
                    error="Incident not found",
                    metadata={
                        "tool": "get_incident",
                        "query": number or sys_id,
                    },
                )
            return ToolResult(
                success=True,
                content=result,
                metadata={"tool": "get_incident"},
            )
        except ServiceNowError as e:
            return self._error_result("get_incident", e)

    async def _handle_create_ritm(self, **kwargs: Any) -> ToolResult:
        """Handle create_ritm tool call."""
        try:
            variables = kwargs.get("variables", {})
            if isinstance(variables, str):
                variables = json.loads(variables)

            result = await self._client.create_ritm(
                cat_item=kwargs["cat_item"],
                variables=variables,
                requested_for=kwargs["requested_for"],
                short_description=kwargs["short_description"],
            )
            return ToolResult(
                success=True,
                content=result,
                metadata={"tool": "create_ritm", "table": "sc_req_item"},
            )
        except (ServiceNowError, json.JSONDecodeError) as e:
            return self._error_result("create_ritm", e)

    async def _handle_get_ritm_status(self, **kwargs: Any) -> ToolResult:
        """Handle get_ritm_status tool call."""
        try:
            number = kwargs.get("number")
            sys_id = kwargs.get("sys_id")

            if not number and not sys_id:
                return ToolResult(
                    success=False,
                    content=None,
                    error="Either 'number' or 'sys_id' must be provided",
                    metadata={"tool": "get_ritm_status"},
                )

            result = await self._client.get_ritm_status(number=number, sys_id=sys_id)
            if result is None:
                return ToolResult(
                    success=True,
                    content=None,
                    error="RITM not found",
                    metadata={
                        "tool": "get_ritm_status",
                        "query": number or sys_id,
                    },
                )
            return ToolResult(
                success=True,
                content=result,
                metadata={"tool": "get_ritm_status"},
            )
        except ServiceNowError as e:
            return self._error_result("get_ritm_status", e)

    async def _handle_add_attachment(self, **kwargs: Any) -> ToolResult:
        """Handle add_attachment tool call."""
        try:
            content_str = kwargs["content"]
            content_bytes = content_str.encode("utf-8")

            result = await self._client.add_attachment(
                table=kwargs["table"],
                sys_id=kwargs["sys_id"],
                file_name=kwargs["file_name"],
                content=content_bytes,
                content_type=kwargs.get("content_type", "text/plain"),
            )
            return ToolResult(
                success=True,
                content=result,
                metadata={
                    "tool": "add_attachment",
                    "table": kwargs["table"],
                    "file_name": kwargs["file_name"],
                    "size_bytes": len(content_bytes),
                },
            )
        except ServiceNowError as e:
            return self._error_result("add_attachment", e)

    # =========================================================================
    # Public Interface
    # =========================================================================

    def get_tools(self) -> List[ToolSchema]:
        """Return list of registered tool schemas."""
        return self._protocol.list_tools()

    def get_tool_names(self) -> List[str]:
        """Return list of registered tool names."""
        return [t.name for t in self._protocol.list_tools()]

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> ToolResult:
        """Execute a tool by name with given arguments.

        Args:
            tool_name: Name of the tool to call.
            arguments: Tool input parameters.

        Returns:
            ToolResult with success status and content.
        """
        request = MCPRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={"name": tool_name, "arguments": arguments},
        )
        response = await self._protocol.handle_request(request)

        if response.error:
            return ToolResult(
                success=False,
                content=None,
                error=response.error.get("message", "Unknown error"),
                metadata={"tool": tool_name},
            )

        result_data = response.result or {}
        content_list = result_data.get("content", [])
        if content_list:
            first = content_list[0]
            if isinstance(first, dict) and "text" in first:
                try:
                    parsed = json.loads(first["text"])
                    return ToolResult(
                        success=parsed.get("success", True),
                        content=parsed.get("content"),
                        error=parsed.get("error"),
                        metadata=parsed.get("metadata", {"tool": tool_name}),
                    )
                except (json.JSONDecodeError, TypeError):
                    return ToolResult(
                        success=True,
                        content=first["text"],
                        metadata={"tool": tool_name},
                    )

        return ToolResult(
            success=True,
            content=result_data,
            metadata={"tool": tool_name},
        )

    # =========================================================================
    # Context Manager
    # =========================================================================

    async def __aenter__(self) -> "ServiceNowMCPServer":
        await self._client.__aenter__()
        self._running = True
        return self

    async def __aexit__(self, *args: Any) -> None:
        self._running = False
        await self._client.__aexit__(*args)

    def __enter__(self) -> "ServiceNowMCPServer":
        self._running = True
        return self

    def __exit__(self, *args: Any) -> None:
        self._running = False

    # =========================================================================
    # Helpers
    # =========================================================================

    @staticmethod
    def _error_result(tool_name: str, error: Exception) -> ToolResult:
        """Create a standardized error ToolResult."""
        error_type = type(error).__name__
        status_code = getattr(error, "status_code", None)
        metadata: Dict[str, Any] = {"tool": tool_name, "error_type": error_type}
        if status_code:
            metadata["status_code"] = status_code

        return ToolResult(
            success=False,
            content=None,
            error=str(error),
            metadata=metadata,
        )
