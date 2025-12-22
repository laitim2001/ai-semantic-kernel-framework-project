"""MCP Protocol Handler.

This module implements the MCP JSON-RPC 2.0 protocol handler,
providing core request/response processing capabilities.

Supported Methods:
    - initialize: Initialize connection and negotiate capabilities
    - tools/list: List available tools
    - tools/call: Execute a tool
    - resources/list: List available resources
    - resources/read: Read a resource
    - prompts/list: List available prompts
    - prompts/get: Get a prompt template
    - ping: Health check

Reference:
    - MCP Specification: https://modelcontextprotocol.io/
"""

from typing import Any, Callable, Dict, List, Optional, Awaitable
import logging

from .types import MCPRequest, MCPResponse, ToolSchema, ToolResult, MCPErrorCode

logger = logging.getLogger(__name__)


# Type alias for tool handlers
ToolHandler = Callable[..., Awaitable[ToolResult]]


class MCPProtocol:
    """MCP Protocol Handler.

    Implements the MCP JSON-RPC 2.0 protocol for tool registration,
    discovery, and execution.

    Attributes:
        MCP_VERSION: The MCP protocol version supported

    Example:
        >>> protocol = MCPProtocol()
        >>> protocol.register_tool(
        ...     name="list_vms",
        ...     handler=list_vms_handler,
        ...     schema=vm_list_schema,
        ... )
        >>> request = MCPRequest(method="tools/list")
        >>> response = await protocol.handle_request(request)
    """

    MCP_VERSION = "2024-11-05"
    SERVER_NAME = "ipa-platform-mcp"
    SERVER_VERSION = "1.0.0"

    def __init__(self):
        """Initialize MCP Protocol handler."""
        self._tools: Dict[str, ToolHandler] = {}
        self._tool_schemas: Dict[str, ToolSchema] = {}
        self._resources: Dict[str, Any] = {}
        self._prompts: Dict[str, Any] = {}
        self._initialized = False
        self._request_id = 0
        self._client_info: Optional[Dict[str, Any]] = None

    def register_tool(
        self,
        name: str,
        handler: ToolHandler,
        schema: ToolSchema,
    ) -> None:
        """Register a tool with the protocol handler.

        Args:
            name: Unique tool name
            handler: Async function to execute the tool
            schema: Tool schema definition
        """
        if name in self._tools:
            logger.warning(f"Overwriting existing tool: {name}")

        self._tools[name] = handler
        self._tool_schemas[name] = schema
        logger.info(f"Registered MCP tool: {name}")

    def unregister_tool(self, name: str) -> bool:
        """Unregister a tool.

        Args:
            name: Tool name to unregister

        Returns:
            True if tool was unregistered, False if not found
        """
        if name in self._tools:
            del self._tools[name]
            del self._tool_schemas[name]
            logger.info(f"Unregistered MCP tool: {name}")
            return True
        return False

    def get_tool_schema(self, name: str) -> Optional[ToolSchema]:
        """Get a tool's schema.

        Args:
            name: Tool name

        Returns:
            Tool schema or None if not found
        """
        return self._tool_schemas.get(name)

    @property
    def registered_tools(self) -> List[str]:
        """Get list of registered tool names."""
        return list(self._tools.keys())

    @property
    def is_initialized(self) -> bool:
        """Check if protocol is initialized."""
        return self._initialized

    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle an MCP request.

        Routes the request to the appropriate handler based on the method.

        Args:
            request: MCP request to handle

        Returns:
            MCP response
        """
        method = request.method
        params = request.params

        logger.debug(f"Handling MCP request: {method}")

        try:
            if method == "initialize":
                result = await self._handle_initialize(params)
            elif method == "initialized":
                result = await self._handle_initialized(params)
            elif method == "tools/list":
                result = await self._handle_tools_list(params)
            elif method == "tools/call":
                result = await self._handle_tools_call(params)
            elif method == "resources/list":
                result = await self._handle_resources_list(params)
            elif method == "resources/read":
                result = await self._handle_resources_read(params)
            elif method == "prompts/list":
                result = await self._handle_prompts_list(params)
            elif method == "prompts/get":
                result = await self._handle_prompts_get(params)
            elif method == "ping":
                result = {}
            else:
                return MCPResponse.create_error(
                    request_id=request.id,
                    code=MCPErrorCode.METHOD_NOT_FOUND,
                    message=f"Method not found: {method}",
                )

            return MCPResponse(id=request.id, result=result)

        except Exception as e:
            logger.error(f"MCP request error: {e}", exc_info=True)
            return MCPResponse.create_error(
                request_id=request.id,
                code=MCPErrorCode.INTERNAL_ERROR,
                message=str(e),
            )

    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request.

        Args:
            params: Initialize parameters including client info

        Returns:
            Server capabilities and info
        """
        self._client_info = params.get("clientInfo")
        client_version = params.get("protocolVersion", "unknown")

        logger.info(
            f"MCP Initialize - Client: {self._client_info}, "
            f"Protocol: {client_version}"
        )

        self._initialized = True

        return {
            "protocolVersion": self.MCP_VERSION,
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"subscribe": False, "listChanged": False},
                "prompts": {"listChanged": False},
                "logging": {},
            },
            "serverInfo": {
                "name": self.SERVER_NAME,
                "version": self.SERVER_VERSION,
            },
        }

    async def _handle_initialized(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialized notification (no response needed for notifications)."""
        logger.info("MCP connection initialized")
        return {}

    async def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request.

        Args:
            params: Optional cursor for pagination

        Returns:
            List of available tools
        """
        cursor = params.get("cursor") if params else None

        tools = []
        for name, schema in self._tool_schemas.items():
            tools.append(schema.to_mcp_format())

        result: Dict[str, Any] = {"tools": tools}

        # Add pagination cursor if needed (for large tool lists)
        if cursor:
            result["nextCursor"] = None  # No pagination for now

        return result

    async def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request.

        Args:
            params: Tool name and arguments

        Returns:
            Tool execution result
        """
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            return {
                "isError": True,
                "content": [{"type": "text", "text": "Tool name is required"}],
            }

        if tool_name not in self._tools:
            return {
                "isError": True,
                "content": [
                    {"type": "text", "text": f"Tool not found: {tool_name}"}
                ],
            }

        handler = self._tools[tool_name]

        try:
            result = await handler(**arguments)

            if isinstance(result, ToolResult):
                return result.to_mcp_format()
            else:
                # Wrap raw result in ToolResult
                return ToolResult(success=True, content=result).to_mcp_format()

        except TypeError as e:
            # Argument mismatch
            logger.error(f"Tool argument error: {tool_name}: {e}")
            return {
                "isError": True,
                "content": [
                    {"type": "text", "text": f"Invalid arguments: {e}"}
                ],
            }
        except Exception as e:
            logger.error(f"Tool execution error: {tool_name}: {e}", exc_info=True)
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Execution error: {e}"}],
            }

    async def _handle_resources_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/list request."""
        return {"resources": list(self._resources.values())}

    async def _handle_resources_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request."""
        uri = params.get("uri")
        if not uri or uri not in self._resources:
            return {
                "contents": [],
            }
        return {"contents": [self._resources[uri]]}

    async def _handle_prompts_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/list request."""
        return {"prompts": list(self._prompts.values())}

    async def _handle_prompts_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/get request."""
        name = params.get("name")
        if not name or name not in self._prompts:
            return {"messages": []}
        return {"messages": self._prompts[name].get("messages", [])}

    def create_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> MCPRequest:
        """Create a new MCP request.

        Args:
            method: Method name
            params: Method parameters

        Returns:
            MCP request object
        """
        self._request_id += 1
        return MCPRequest(
            id=self._request_id,
            method=method,
            params=params or {},
        )

    def create_notification(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> MCPRequest:
        """Create a notification (request without id).

        Args:
            method: Method name
            params: Method parameters

        Returns:
            MCP notification (request with empty id)
        """
        return MCPRequest(
            id="",  # Empty id for notifications
            method=method,
            params=params or {},
        )
