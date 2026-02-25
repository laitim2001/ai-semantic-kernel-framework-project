"""Dynamics 365 MCP Server.

Provides MCP integration with Dynamics 365 for entity CRUD operations,
OData queries, and metadata discovery through 6 MCP tools.

Tools (6 total):
    - d365_query_entities: Query entity records with OData filtering
    - d365_get_record: Get a single entity record by ID
    - d365_list_entity_types: List all customizable entity types
    - d365_get_entity_metadata: Get metadata for a specific entity type
    - d365_create_record: Create a new entity record
    - d365_update_record: Update an existing entity record

Usage:
    # Run as MCP Server (stdio mode)
    python -m src.integrations.mcp.servers.d365

    # Environment variables (all required)
    D365_URL=https://org.crm.dynamics.com
    D365_TENANT_ID=xxx
    D365_CLIENT_ID=xxx
    D365_CLIENT_SECRET=xxx

    # Programmatic usage
    >>> config = D365Config.from_env()
    >>> server = D365MCPServer(config)
    >>> tools = server.get_tools()
    >>> result = await server.call_tool("d365_query_entities", {"entity_name": "account"})

Sprint 129: Story 129-2
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional

from ...core.protocol import MCPProtocol
from ...core.types import MCPRequest, MCPResponse, ToolSchema, ToolResult
from ...security.permission_checker import MCPPermissionChecker
from .client import D365ApiClient, D365Config
from .tools.query import QueryTools
from .tools.crud import CrudTools

logger = logging.getLogger(__name__)


class D365MCPServer:
    """Dynamics 365 MCP Server.

    Provides D365 entity management and metadata discovery capabilities
    through the MCP protocol.

    Features:
        - Entity querying with OData v4 filter support
        - Record CRUD operations (create, read, update)
        - Entity type listing and metadata discovery
        - Permission-based access control
        - Service Principal authentication with token caching

    Tools (6 total):
        - d365_query_entities: Query entity records with OData filtering
        - d365_get_record: Get a single entity record by ID
        - d365_list_entity_types: List all customizable entity types
        - d365_get_entity_metadata: Get metadata for a specific entity type
        - d365_create_record: Create a new entity record
        - d365_update_record: Update an existing entity record

    Example:
        >>> config = D365Config.from_env()
        >>> server = D365MCPServer(config)
        >>> tools = server.get_tools()
        >>> result = await server.call_tool("d365_query_entities", {"entity_name": "account"})
        >>> print(result.content)
    """

    SERVER_NAME = "d365-mcp"
    SERVER_VERSION = "1.0.0"
    SERVER_DESCRIPTION = (
        "Dynamics 365 MCP Server — Entity CRUD, OData queries, and metadata discovery"
    )

    def __init__(self, config: D365Config):
        """Initialize the D365 MCP Server.

        Args:
            config: D365 connection configuration
        """
        self._config = config
        self._protocol = MCPProtocol()
        self._client = D365ApiClient(config)
        self._running = False

        # Initialize tool classes
        self._query_tools = QueryTools(self._client)
        self._crud_tools = CrudTools(self._client)

        # Register all tools
        self._register_all_tools()

        # Initialize permission checker
        self._permission_checker = MCPPermissionChecker()
        self._protocol.set_permission_checker(self._permission_checker, "d365")

        logger.info(
            f"D365MCPServer initialized: {self.SERVER_NAME} v{self.SERVER_VERSION} "
            f"(url: {config.d365_url})"
        )

    def _register_all_tools(self) -> None:
        """Register all D365 tools with the protocol handler."""
        tool_classes = [
            (self._query_tools, QueryTools),
            (self._crud_tools, CrudTools),
        ]

        for tools_instance, tools_class in tool_classes:
            for schema in tools_class.get_schemas():
                handler = getattr(tools_instance, schema.name)
                self._protocol.register_tool(schema.name, handler, schema)
                logger.debug(f"Registered tool: {schema.name}")

            # Register permission levels
            if hasattr(tools_class, "PERMISSION_LEVELS"):
                for tool_name, level in tools_class.PERMISSION_LEVELS.items():
                    self._protocol.set_tool_permission_level(tool_name, level)

        logger.info(f"Registered {len(self._protocol.list_tools())} D365 tools")

    def get_tools(self) -> List[ToolSchema]:
        """Get all registered tool schemas.

        Returns:
            List of tool schemas
        """
        return self._protocol.list_tools()

    def get_tool_names(self) -> List[str]:
        """Get names of all registered tools.

        Returns:
            List of tool names
        """
        return [t.name for t in self._protocol.list_tools()]

    async def call_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        """Call a tool directly.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        request = MCPRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={
                "name": tool_name,
                "arguments": arguments or {},
            },
        )

        response = await self._protocol.handle_request(request)

        if response.error:
            return ToolResult(
                success=False,
                content=None,
                error=response.error.get("message", "Unknown error"),
            )

        return ToolResult(
            success=True,
            content=response.result,
        )

    async def health_check(self) -> bool:
        """Check D365 connectivity.

        Returns:
            True if D365 is reachable
        """
        return await self._client.health_check()

    @property
    def is_healthy(self) -> bool:
        """Get the last known health status."""
        return self._client.is_healthy

    async def run(self) -> None:
        """Run the server in stdio mode.

        Reads JSON-RPC requests from stdin and writes responses to stdout.
        """
        self._running = True
        logger.info("Starting D365 MCP Server in stdio mode")

        while self._running:
            try:
                line = sys.stdin.readline()
                if not line:
                    logger.info("stdin closed, shutting down")
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    request_data = json.loads(line)
                except json.JSONDecodeError as e:
                    error_response = self._create_error_response(
                        None, -32700, f"Parse error: {e}"
                    )
                    self._write_response(error_response)
                    continue

                request = MCPRequest(
                    jsonrpc=request_data.get("jsonrpc", "2.0"),
                    id=request_data.get("id"),
                    method=request_data.get("method", ""),
                    params=request_data.get("params"),
                )

                response = await self._protocol.handle_request(request)
                self._write_response(response)

            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, shutting down")
                break
            except Exception as e:
                logger.error(f"Error processing request: {e}")
                error_response = self._create_error_response(
                    None, -32603, f"Internal error: {e}"
                )
                self._write_response(error_response)

        self._running = False
        logger.info("D365 MCP Server stopped")

    def _write_response(self, response: MCPResponse) -> None:
        """Write response to stdout."""
        response_data: Dict[str, Any] = {
            "jsonrpc": response.jsonrpc,
            "id": response.id,
        }
        if response.result is not None:
            response_data["result"] = response.result
        if response.error is not None:
            response_data["error"] = response.error

        print(json.dumps(response_data), flush=True)

    def _create_error_response(
        self,
        request_id: Optional[Any],
        code: int,
        message: str,
    ) -> MCPResponse:
        """Create an error response."""
        return MCPResponse(
            jsonrpc="2.0",
            id=request_id,
            error={"code": code, "message": message},
        )

    def stop(self) -> None:
        """Stop the server."""
        self._running = False
        logger.info("Stop requested")

    async def cleanup(self) -> None:
        """Clean up resources."""
        await self._client.close()
        logger.info("Cleanup completed")

    async def __aenter__(self) -> "D365MCPServer":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.cleanup()


def create_server_from_env() -> D365MCPServer:
    """Create server from environment variables.

    Returns:
        Configured D365MCPServer instance

    Raises:
        ValueError: If required environment variables are not set
    """
    config = D365Config.from_env()
    return D365MCPServer(config)


def main() -> None:
    """Main entry point for the D365 MCP Server."""
    import os

    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    try:
        server = create_server_from_env()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    try:
        asyncio.run(server.run())
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
    finally:
        asyncio.run(server.cleanup())


if __name__ == "__main__":
    main()
