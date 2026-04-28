"""Tool registry for Claude SDK."""

from typing import Dict, List, Any, Optional, Type

from .base import Tool, ToolResult

# Tool registry mapping names to tool classes
_TOOL_REGISTRY: Dict[str, Type[Tool]] = {}

# Singleton instances of tools
_TOOL_INSTANCES: Dict[str, Tool] = {}


def register_tool(tool_class: Type[Tool]) -> Type[Tool]:
    """
    Register a tool class.

    Args:
        tool_class: Tool class to register

    Returns:
        The tool class (for decorator usage)
    """
    _TOOL_REGISTRY[tool_class.name] = tool_class
    return tool_class


def get_tool_instance(name: str, **kwargs) -> Optional[Tool]:
    """
    Get or create a tool instance.

    Args:
        name: Tool name
        **kwargs: Tool initialization arguments

    Returns:
        Tool instance or None if not found
    """
    if name not in _TOOL_REGISTRY:
        return None

    # Create new instance if kwargs provided or not cached
    if kwargs or name not in _TOOL_INSTANCES:
        _TOOL_INSTANCES[name] = _TOOL_REGISTRY[name](**kwargs)

    return _TOOL_INSTANCES[name]


def get_available_tools() -> List[str]:
    """
    Get list of available tool names.

    Returns:
        List of registered tool names
    """
    return list(_TOOL_REGISTRY.keys())


def get_tool_definitions(
    tools: List[str],
    mcp_servers: Optional[List[Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Get tool definitions for Claude API.

    Args:
        tools: List of tool names to include
        mcp_servers: Optional MCP servers to include tools from

    Returns:
        List of tool definition dictionaries for Claude API
    """
    definitions = []

    for tool_name in tools:
        tool = get_tool_instance(tool_name)
        if tool:
            definitions.append(tool.get_definition())

    # TODO: Add MCP server tools when implemented
    if mcp_servers:
        pass  # Will be implemented with MCP integration

    return definitions


async def execute_tool(
    tool_name: str,
    args: Dict[str, Any],
    working_directory: Optional[str] = None,
    mcp_servers: Optional[List[Any]] = None,
) -> str:
    """
    Execute a tool by name.

    Args:
        tool_name: Name of the tool to execute
        args: Tool arguments
        working_directory: Working directory for file operations
        mcp_servers: Optional MCP servers

    Returns:
        Tool execution result as string
    """
    tool = get_tool_instance(tool_name)

    if not tool:
        return f"Error: Tool '{tool_name}' not found"

    # Handle working directory for file tools
    if working_directory and "path" in args:
        import os

        if not os.path.isabs(args["path"]):
            args["path"] = os.path.join(working_directory, args["path"])

    try:
        result = await tool.execute(**args)
        if result.success:
            return result.content
        else:
            return f"Error: {result.error}"
    except Exception as e:
        return f"Error executing {tool_name}: {str(e)}"


def _register_builtin_tools():
    """Register all built-in tools."""
    from .file_tools import Read, Write, Edit, MultiEdit, Glob, Grep
    from .command_tools import Bash, Task
    from .web_tools import WebSearch, WebFetch

    # Register file tools
    register_tool(Read)
    register_tool(Write)
    register_tool(Edit)
    register_tool(MultiEdit)
    register_tool(Glob)
    register_tool(Grep)

    # Register command tools (S49-2)
    register_tool(Bash)
    register_tool(Task)

    # Register web tools (S49-4)
    register_tool(WebSearch)
    register_tool(WebFetch)


# Register built-in tools on module import
_register_builtin_tools()
