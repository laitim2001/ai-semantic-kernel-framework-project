# =============================================================================
# IPA Platform - Agent Tools Module
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Tools module providing extensible tool framework for AI agents.
# Includes base classes, built-in tools, and tool registry.
#
# Components:
#   - base.py: ToolResult, ToolError, BaseTool, FunctionTool, @tool decorator
#   - builtin.py: HttpTool, DateTimeTool, get_weather, search_knowledge_base
#   - registry.py: ToolRegistry, get_tool_registry singleton
#
# Usage:
#   from src.domain.agents.tools import get_tool_registry, HttpTool
#
#   # Get tool from global registry
#   registry = get_tool_registry()
#   http_tool = registry.get("http_request")
#
#   # Or instantiate directly
#   tool = HttpTool()
#   result = await tool(method="GET", url="https://api.example.com")
# =============================================================================

from src.domain.agents.tools.base import (
    BaseTool,
    FunctionTool,
    ToolError,
    ToolResult,
    tool,
)
from src.domain.agents.tools.builtin import (
    DateTimeTool,
    HttpTool,
    calculate,
    get_weather,
    search_knowledge_base,
)
from src.domain.agents.tools.registry import (
    ToolRegistry,
    get_tool_registry,
    reset_tool_registry,
)

__all__ = [
    # Base
    "ToolResult",
    "ToolError",
    "BaseTool",
    "FunctionTool",
    "tool",
    # Built-in
    "HttpTool",
    "DateTimeTool",
    "get_weather",
    "search_knowledge_base",
    "calculate",
    # Registry
    "ToolRegistry",
    "get_tool_registry",
    "reset_tool_registry",
]
