"""Azure Data Factory MCP Server.

Main server implementation for ADF pipeline management via MCP protocol.

Provides 8 MCP tools across 2 tool categories:
    - PipelineTools: list_pipelines, get_pipeline, run_pipeline, cancel_pipeline_run
    - MonitoringTools: get_pipeline_run, list_pipeline_runs, list_datasets, list_triggers

Usage:
    # Run as MCP Server (stdio mode)
    python -m src.integrations.mcp.servers.adf

    # Environment variables (all required)
    ADF_SUBSCRIPTION_ID=xxx
    ADF_RESOURCE_GROUP=xxx
    ADF_FACTORY_NAME=xxx
    ADF_TENANT_ID=xxx
    ADF_CLIENT_ID=xxx
    ADF_CLIENT_SECRET=xxx

    # Programmatic usage
    >>> config = AdfConfig.from_env()
    >>> server = AdfMCPServer(config)
    >>> tools = server.get_tools()
    >>> result = await server.call_tool("adf_list_pipelines")
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional

from ...core.protocol import MCPProtocol
from ...core.types import MCPRequest, MCPResponse, ToolSchema, ToolResult
from ...security.permission_checker import MCPPermissionChecker
from .client import AdfApiClient, AdfConfig
from .tools.pipeline import PipelineTools
from .tools.monitoring import MonitoringTools

logger = logging.getLogger(__name__)


class AdfMCPServer:
    """Azure Data Factory MCP Server.

    Provides ADF pipeline management and monitoring capabilities
    through the MCP protocol.

    Features:
        - Pipeline listing, inspection, and execution
        - Pipeline run monitoring and cancellation
        - Dataset and trigger discovery
        - Permission-based access control
        - Service Principal authentication with token caching

    Tools (8 total):
        - adf_list_pipelines: List all pipelines
        - adf_get_pipeline: Get pipeline details
        - adf_run_pipeline: Trigger pipeline execution
        - adf_cancel_pipeline_run: Cancel a pipeline run
        - adf_get_pipeline_run: Get run status
        - adf_list_pipeline_runs: Query run history
        - adf_list_datasets: List datasets
        - adf_list_triggers: List triggers

    Example:
        >>> config = AdfConfig.from_env()
        >>> server = AdfMCPServer(config)
        >>> tools = server.get_tools()
        >>> result = await server.call_tool("adf_list_pipelines")
        >>> print(result.content)
    """

    SERVER_NAME = "adf-mcp"
    SERVER_VERSION = "1.0.0"
    SERVER_DESCRIPTION = "Azure Data Factory MCP server for ETL pipeline management"

    def __init__(self, config: AdfConfig):
        """Initialize the ADF MCP Server.

        Args:
            config: ADF connection configuration
        """
        self._config = config
        self._protocol = MCPProtocol()
        self._client = AdfApiClient(config)
        self._running = False

        # Initialize tool classes
        self._pipeline_tools = PipelineTools(self._client)
        self._monitoring_tools = MonitoringTools(self._client)

        # Register all tools
        self._register_all_tools()

        # Initialize permission checker
        self._permission_checker = MCPPermissionChecker()
        self._protocol.set_permission_checker(self._permission_checker, "adf")

        logger.info(
            f"AdfMCPServer initialized: {self.SERVER_NAME} v{self.SERVER_VERSION} "
            f"(factory: {config.factory_name})"
        )

    def _register_all_tools(self) -> None:
        """Register all ADF tools with the protocol handler."""
        tool_classes = [
            (self._pipeline_tools, PipelineTools),
            (self._monitoring_tools, MonitoringTools),
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

        logger.info(f"Registered {len(self._protocol.list_tools())} ADF tools")

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
        """Check ADF connectivity.

        Returns:
            True if ADF is reachable
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
        logger.info("Starting ADF MCP Server in stdio mode")

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
        logger.info("ADF MCP Server stopped")

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

    async def __aenter__(self) -> "AdfMCPServer":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.cleanup()


def create_server_from_env() -> AdfMCPServer:
    """Create server from environment variables.

    Returns:
        Configured AdfMCPServer instance

    Raises:
        ValueError: If required environment variables are not set
    """
    config = AdfConfig.from_env()
    return AdfMCPServer(config)


def main() -> None:
    """Main entry point for the ADF MCP Server."""
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
