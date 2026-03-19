"""MCP Tool Bridge — dynamic MCP tool discovery and registration.

Scans the MCP ServerRegistry for available tools and registers them
into the OrchestratorToolRegistry so the Orchestrator Agent can
dynamically discover and invoke MCP tools.

Sprint 134 — Phase 39 E2E Assembly D.
"""

import logging
from typing import Any, Dict, List, Optional

from src.integrations.hybrid.orchestrator.tools import (
    OrchestratorToolRegistry,
    ToolDefinition,
    ToolType,
)

logger = logging.getLogger(__name__)


class MCPToolBridge:
    """Bridges MCP ServerRegistry tools into OrchestratorToolRegistry.

    Discovers available tools from registered MCP servers and creates
    corresponding ToolDefinition entries with lazy-loading handlers.

    Args:
        tool_registry: The OrchestratorToolRegistry to register tools into.
    """

    def __init__(self, tool_registry: OrchestratorToolRegistry) -> None:
        self._tool_registry = tool_registry
        self._registered_tools: Dict[str, str] = {}  # tool_name -> server_name
        self._mcp_client: Any = None

    def discover_and_register(self) -> int:
        """Discover MCP tools and register them into the orchestrator.

        Returns:
            Number of tools successfully registered.
        """
        servers = self._get_available_servers()
        if not servers:
            return 0

        registered = 0
        for server_name, server_info in servers.items():
            tools = server_info.get("tools", [])
            for tool_info in tools:
                tool_name = f"mcp_{server_name}_{tool_info.get('name', 'unknown')}"
                if tool_name in self._registered_tools:
                    continue

                tool_def = ToolDefinition(
                    name=tool_name,
                    description=tool_info.get("description", f"MCP tool from {server_name}"),
                    tool_type=ToolType.SYNC,
                    parameters=tool_info.get("parameters", {}),
                    required_role="operator",
                )
                self._tool_registry._tools[tool_name] = tool_def

                # Register lazy handler
                handler = self._create_lazy_handler(server_name, tool_info.get("name", ""))
                self._tool_registry.register_handler(tool_name, handler)
                self._registered_tools[tool_name] = server_name
                registered += 1

        logger.info("MCPToolBridge: registered %d tools from %d servers", registered, len(servers))
        return registered

    def _get_available_servers(self) -> Dict[str, Any]:
        """Query MCP ServerRegistry for available servers and their tools."""
        try:
            from src.integrations.mcp.registry.server_registry import ServerRegistry
            registry = ServerRegistry()
            # Get registered servers and their tool schemas
            servers: Dict[str, Any] = {}
            for server_name in getattr(registry, "_servers", {}).keys():
                server = registry._servers[server_name]
                tools = []
                if hasattr(server, "get_tools"):
                    tools = server.get_tools()
                elif hasattr(server, "tools"):
                    tools = server.tools
                servers[server_name] = {
                    "tools": [
                        {
                            "name": getattr(t, "name", str(t)),
                            "description": getattr(t, "description", ""),
                            "parameters": getattr(t, "parameters", {}),
                        }
                        for t in (tools if isinstance(tools, list) else [])
                    ]
                }
            return servers
        except ImportError:
            logger.info("MCPToolBridge: ServerRegistry not available")
            return {}
        except Exception as e:
            logger.warning("MCPToolBridge: server discovery failed: %s", e)
            return {}

    def _create_lazy_handler(self, server_name: str, tool_name: str):
        """Create a lazy-loading handler for an MCP tool.

        The actual MCP connection is only established when the tool
        is first invoked.
        """
        async def _handler(**kwargs: Any) -> Dict[str, Any]:
            try:
                client = self._get_or_create_client()
                if client is None:
                    return {"error": f"MCP client not available for {server_name}"}

                result = await client.call_tool(
                    server_name=server_name,
                    tool_name=tool_name,
                    arguments=kwargs,
                )
                return {"result": result, "server": server_name, "tool": tool_name}
            except Exception as e:
                logger.error("MCP tool call failed: %s/%s: %s", server_name, tool_name, e)
                return {"error": str(e), "server": server_name, "tool": tool_name}

        return _handler

    def _get_or_create_client(self) -> Any:
        """Lazy-load the MCP client."""
        if self._mcp_client is not None:
            return self._mcp_client
        try:
            from src.integrations.mcp.core.client import MCPClient
            self._mcp_client = MCPClient()
            logger.info("MCPToolBridge: MCP client created (lazy)")
            return self._mcp_client
        except ImportError:
            logger.warning("MCPToolBridge: MCPClient not available")
            return None
        except Exception as e:
            logger.warning("MCPToolBridge: client creation failed: %s", e)
            return None

    @property
    def registered_count(self) -> int:
        """Number of MCP tools registered."""
        return len(self._registered_tools)

    @property
    def registered_tools(self) -> Dict[str, str]:
        """Map of registered tool names to their server names."""
        return dict(self._registered_tools)
