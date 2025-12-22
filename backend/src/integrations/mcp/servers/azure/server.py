"""Azure MCP Server.

Main server implementation for Azure resource management via MCP protocol.

Usage:
    # Run as MCP Server (stdio mode)
    python -m src.integrations.mcp.servers.azure

    # Environment variables
    AZURE_SUBSCRIPTION_ID=xxx
    AZURE_TENANT_ID=xxx (optional)
    AZURE_CLIENT_ID=xxx (optional)
    AZURE_CLIENT_SECRET=xxx (optional)
"""

import asyncio
import sys
import json
import logging
from typing import Any, Callable, Dict, List, Optional

from ...core.protocol import MCPProtocol
from ...core.types import MCPRequest, MCPResponse, ToolSchema, ToolResult
from .client import AzureClientManager, AzureConfig
from .tools.vm import VMTools
from .tools.resource import ResourceTools
from .tools.monitor import MonitorTools
from .tools.network import NetworkTools
from .tools.storage import StorageTools

logger = logging.getLogger(__name__)


class AzureMCPServer:
    """Azure MCP Server.

    Provides Azure resource management and monitoring capabilities
    through the MCP protocol.

    Features:
        - VM management (list, start, stop, restart, run commands)
        - Resource discovery (resource groups, resources)
        - Monitoring (metrics, alerts)
        - Network resources (VNets, NSGs, public IPs)
        - Storage management (storage accounts, containers)

    Example:
        >>> config = AzureConfig.from_env()
        >>> server = AzureMCPServer(config)
        >>> await server.run()

    Protocol:
        The server communicates via JSON-RPC 2.0 over stdio.
        Supports standard MCP methods:
        - initialize
        - tools/list
        - tools/call
        - resources/list
        - resources/read
    """

    # Server metadata
    SERVER_NAME = "azure-mcp"
    SERVER_VERSION = "1.0.0"
    SERVER_DESCRIPTION = "Azure resource management MCP server"

    def __init__(self, config: AzureConfig):
        """Initialize the Azure MCP Server.

        Args:
            config: Azure configuration
        """
        self._config = config
        self._protocol = MCPProtocol()
        self._client_manager = AzureClientManager(config)
        self._running = False

        # Initialize tool classes
        self._vm_tools = VMTools(self._client_manager)
        self._resource_tools = ResourceTools(self._client_manager)
        self._monitor_tools = MonitorTools(self._client_manager)
        self._network_tools = NetworkTools(self._client_manager)
        self._storage_tools = StorageTools(self._client_manager)

        # Register all tools
        self._register_all_tools()

        logger.info(
            f"AzureMCPServer initialized: {self.SERVER_NAME} v{self.SERVER_VERSION}"
        )

    def _register_all_tools(self) -> None:
        """Register all Azure tools with the protocol handler."""
        tool_classes = [
            (self._vm_tools, VMTools),
            (self._resource_tools, ResourceTools),
            (self._monitor_tools, MonitorTools),
            (self._network_tools, NetworkTools),
            (self._storage_tools, StorageTools),
        ]

        for tools_instance, tools_class in tool_classes:
            for schema in tools_class.get_schemas():
                handler = getattr(tools_instance, schema.name)
                self._protocol.register_tool(schema.name, handler, schema)
                logger.debug(f"Registered tool: {schema.name}")

        logger.info(f"Registered {len(self._protocol.list_tools())} tools")

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

    async def run(self) -> None:
        """Run the server in stdio mode.

        Reads JSON-RPC requests from stdin and writes responses to stdout.
        """
        self._running = True
        logger.info("Starting Azure MCP Server in stdio mode")

        while self._running:
            try:
                # Read line from stdin
                line = sys.stdin.readline()
                if not line:
                    logger.info("stdin closed, shutting down")
                    break

                line = line.strip()
                if not line:
                    continue

                # Parse request
                try:
                    request_data = json.loads(line)
                except json.JSONDecodeError as e:
                    error_response = self._create_error_response(
                        None, -32700, f"Parse error: {e}"
                    )
                    self._write_response(error_response)
                    continue

                # Create MCPRequest
                request = MCPRequest(
                    jsonrpc=request_data.get("jsonrpc", "2.0"),
                    id=request_data.get("id"),
                    method=request_data.get("method", ""),
                    params=request_data.get("params"),
                )

                # Handle request
                response = await self._protocol.handle_request(request)

                # Write response
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
        logger.info("Azure MCP Server stopped")

    def _write_response(self, response: MCPResponse) -> None:
        """Write response to stdout.

        Args:
            response: MCP response to write
        """
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
        """Create an error response.

        Args:
            request_id: Original request ID
            code: Error code
            message: Error message

        Returns:
            Error response
        """
        return MCPResponse(
            jsonrpc="2.0",
            id=request_id,
            error={
                "code": code,
                "message": message,
            },
        )

    def stop(self) -> None:
        """Stop the server."""
        self._running = False
        logger.info("Stop requested")

    def cleanup(self) -> None:
        """Clean up resources."""
        self._client_manager.close()
        logger.info("Cleanup completed")

    async def __aenter__(self) -> "AzureMCPServer":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        self.cleanup()

    def __enter__(self) -> "AzureMCPServer":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.cleanup()


def create_server_from_env() -> AzureMCPServer:
    """Create server from environment variables.

    Returns:
        Configured AzureMCPServer instance

    Raises:
        ValueError: If required environment variables are not set
    """
    config = AzureConfig.from_env()
    return AzureMCPServer(config)


def main() -> None:
    """Main entry point for the Azure MCP Server."""
    import os

    # Configure logging
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,  # Log to stderr to keep stdout clean for MCP protocol
    )

    # Create and run server
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
        server.cleanup()


if __name__ == "__main__":
    main()
