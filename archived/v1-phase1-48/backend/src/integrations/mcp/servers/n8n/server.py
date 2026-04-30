"""n8n MCP Server.

Main server implementation for n8n workflow management via MCP protocol.

Provides 6 MCP tools across 2 tool categories:
    - WorkflowTools: list_workflows, get_workflow, activate_workflow
    - ExecutionTools: execute_workflow, get_execution, list_executions

Usage:
    # Run as MCP Server (stdio mode)
    python -m src.integrations.mcp.servers.n8n

    # Environment variables
    N8N_BASE_URL=http://localhost:5678
    N8N_API_KEY=xxx

    # Programmatic usage
    >>> config = N8nConfig.from_env()
    >>> server = N8nMCPServer(config)
    >>> tools = server.get_tools()
    >>> result = await server.call_tool("n8n_list_workflows")
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional

from ...core.protocol import MCPProtocol
from ...core.types import MCPRequest, MCPResponse, ToolSchema, ToolResult
from ...security.permission_checker import MCPPermissionChecker
from .client import N8nApiClient, N8nConfig
from .tools.workflow import WorkflowTools
from .tools.execution import ExecutionTools

logger = logging.getLogger(__name__)


class N8nMCPServer:
    """n8n MCP Server.

    Provides n8n workflow management and execution capabilities
    through the MCP protocol.

    Features:
        - Workflow listing, inspection, and activation
        - Workflow execution triggering
        - Execution history and status monitoring
        - Permission-based access control
        - Health checking and connection management

    Tools (6 total):
        - n8n_list_workflows: List all workflows
        - n8n_get_workflow: Get workflow details
        - n8n_activate_workflow: Activate/deactivate a workflow
        - n8n_execute_workflow: Trigger workflow execution
        - n8n_get_execution: Get execution status
        - n8n_list_executions: List execution history

    Example:
        >>> config = N8nConfig(base_url="http://localhost:5678", api_key="xxx")
        >>> server = N8nMCPServer(config)
        >>> tools = server.get_tools()
        >>> result = await server.call_tool("n8n_list_workflows")
        >>> print(result.content)

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
    SERVER_NAME = "n8n-mcp"
    SERVER_VERSION = "1.0.0"
    SERVER_DESCRIPTION = "n8n workflow automation MCP server"

    def __init__(self, config: N8nConfig):
        """Initialize the n8n MCP Server.

        Args:
            config: n8n connection configuration
        """
        self._config = config
        self._protocol = MCPProtocol()
        self._client = N8nApiClient(config)
        self._running = False

        # Initialize tool classes
        self._workflow_tools = WorkflowTools(self._client)
        self._execution_tools = ExecutionTools(self._client)

        # Register all tools
        self._register_all_tools()

        # Initialize permission checker
        self._permission_checker = MCPPermissionChecker()
        self._protocol.set_permission_checker(self._permission_checker, "n8n")

        logger.info(
            f"N8nMCPServer initialized: {self.SERVER_NAME} v{self.SERVER_VERSION} "
            f"(n8n: {config.base_url})"
        )

    def _register_all_tools(self) -> None:
        """Register all n8n tools with the protocol handler."""
        tool_classes = [
            (self._workflow_tools, WorkflowTools),
            (self._execution_tools, ExecutionTools),
        ]

        for tools_instance, tools_class in tool_classes:
            for schema in tools_class.get_schemas():
                handler = getattr(tools_instance, schema.name)
                self._protocol.register_tool(schema.name, handler, schema)
                logger.debug(f"Registered tool: {schema.name}")

            # Register permission levels from each tools class
            if hasattr(tools_class, "PERMISSION_LEVELS"):
                for tool_name, level in tools_class.PERMISSION_LEVELS.items():
                    self._protocol.set_tool_permission_level(tool_name, level)

        logger.info(f"Registered {len(self._protocol.list_tools())} n8n tools")

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
        """Check n8n connectivity.

        Returns:
            True if n8n is reachable
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
        logger.info("Starting n8n MCP Server in stdio mode")

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
        logger.info("n8n MCP Server stopped")

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

    async def cleanup(self) -> None:
        """Clean up resources."""
        await self._client.close()
        logger.info("Cleanup completed")

    async def __aenter__(self) -> "N8nMCPServer":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.cleanup()


def create_server_from_env() -> N8nMCPServer:
    """Create server from environment variables.

    Returns:
        Configured N8nMCPServer instance

    Raises:
        ValueError: If required environment variables are not set
    """
    config = N8nConfig.from_env()
    return N8nMCPServer(config)


def main() -> None:
    """Main entry point for the n8n MCP Server."""
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
        asyncio.run(server.cleanup())


if __name__ == "__main__":
    main()
