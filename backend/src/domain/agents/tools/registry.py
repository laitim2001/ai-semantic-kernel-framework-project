# =============================================================================
# IPA Platform - Tool Registry
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Tool Registry for managing and discovering tools available to agents.
# Provides:
#   - ToolRegistry: Central registry for tool management
#   - get_tool_registry(): Singleton accessor
#
# Usage:
#   registry = get_tool_registry()
#   registry.register(MyTool())
#   tool = registry.get("my_tool")
#   all_tools = registry.get_all()
# =============================================================================

import logging
from typing import Any, Callable, Dict, List, Optional, Type, Union

from src.domain.agents.tools.base import BaseTool, FunctionTool, ToolError

logger = logging.getLogger(__name__)

# Singleton instance
_registry_instance: Optional["ToolRegistry"] = None


class ToolRegistry:
    """
    Central registry for managing tools available to agents.

    The registry maintains a collection of tools that can be:
    - Registered dynamically at runtime
    - Retrieved by name for agent use
    - Listed for capability discovery

    Example:
        registry = ToolRegistry()
        registry.register(HttpTool())
        registry.register(DateTimeTool())

        # Get specific tool
        http_tool = registry.get("http_request")

        # List all tools
        all_tools = registry.get_all()

        # Get tools as functions for agent framework
        functions = registry.get_functions()
    """

    def __init__(self):
        """Initialize empty tool registry."""
        self._tools: Dict[str, BaseTool] = {}
        self._tool_classes: Dict[str, Type[BaseTool]] = {}
        logger.debug("ToolRegistry initialized")

    def register(
        self,
        tool: Union[BaseTool, Callable],
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """
        Register a tool with the registry.

        Args:
            tool: Tool instance, tool class, or callable function
            name: Optional override name (uses tool.name if not provided)
            description: Optional override description

        Raises:
            ValueError: If tool with same name already registered
            TypeError: If tool is not a valid type

        Example:
            # Register tool instance
            registry.register(HttpTool())

            # Register with custom name
            registry.register(HttpTool(), name="custom_http")

            # Register a function
            async def my_func(x: int) -> str:
                return str(x * 2)
            registry.register(my_func, name="doubler", description="Double a number")
        """
        # Handle different input types
        if isinstance(tool, BaseTool):
            # Already a tool instance
            tool_instance = tool
        elif callable(tool):
            # Wrap callable in FunctionTool
            if not name:
                name = getattr(tool, "__name__", "unnamed_tool")
            if not description:
                description = getattr(tool, "__doc__", "") or "No description"
            tool_instance = FunctionTool(
                func=tool,
                name=name,
                description=description,
            )
        else:
            raise TypeError(
                f"Expected BaseTool instance or callable, got {type(tool).__name__}"
            )

        # Use override name if provided
        tool_name = name or tool_instance.name

        # Check for duplicates
        if tool_name in self._tools:
            raise ValueError(f"Tool '{tool_name}' is already registered")

        # Store the tool
        self._tools[tool_name] = tool_instance
        logger.info(f"Registered tool: {tool_name}")

    def register_class(self, tool_class: Type[BaseTool]) -> None:
        """
        Register a tool class for lazy instantiation.

        The tool will be instantiated on first access via get().

        Args:
            tool_class: Tool class (not instance)

        Example:
            registry.register_class(HttpTool)
            # Tool is instantiated when first accessed
            tool = registry.get("http_request")
        """
        if not isinstance(tool_class, type) or not issubclass(tool_class, BaseTool):
            raise TypeError(f"Expected BaseTool subclass, got {tool_class}")

        # Get name from class
        temp_instance = tool_class()
        tool_name = temp_instance.name
        self._tools[tool_name] = temp_instance
        self._tool_classes[tool_name] = tool_class
        logger.info(f"Registered tool class: {tool_name}")

    def unregister(self, name: str) -> bool:
        """
        Remove a tool from the registry.

        Args:
            name: Tool name to remove

        Returns:
            True if tool was removed, False if not found
        """
        if name in self._tools:
            del self._tools[name]
            if name in self._tool_classes:
                del self._tool_classes[name]
            logger.info(f"Unregistered tool: {name}")
            return True
        return False

    def get(self, name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance or None if not found

        Example:
            tool = registry.get("http_request")
            if tool:
                result = await tool(method="GET", url="https://api.example.com")
        """
        return self._tools.get(name)

    def get_required(self, name: str) -> BaseTool:
        """
        Get a tool by name, raising error if not found.

        Args:
            name: Tool name

        Returns:
            Tool instance

        Raises:
            ToolError: If tool not found
        """
        tool = self.get(name)
        if tool is None:
            raise ToolError(
                message=f"Tool '{name}' not found in registry",
                tool_name=name,
            )
        return tool

    def get_all(self) -> Dict[str, BaseTool]:
        """
        Get all registered tools.

        Returns:
            Dictionary of tool name -> tool instance
        """
        return dict(self._tools)

    def get_names(self) -> List[str]:
        """
        Get names of all registered tools.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def get_functions(self) -> List[Callable]:
        """
        Get all tools as callable functions for Agent Framework.

        Returns:
            List of callable functions suitable for agent tool lists
        """
        return [tool.as_function() for tool in self._tools.values()]

    def get_schemas(self) -> Dict[str, Dict[str, Any]]:
        """
        Get JSON schemas for all tools.

        Returns:
            Dictionary of tool name -> parameter schema
        """
        return {name: tool.get_schema() for name, tool in self._tools.items()}

    def has(self, name: str) -> bool:
        """
        Check if a tool is registered.

        Args:
            name: Tool name

        Returns:
            True if tool exists
        """
        return name in self._tools

    def count(self) -> int:
        """
        Get number of registered tools.

        Returns:
            Tool count
        """
        return len(self._tools)

    def clear(self) -> None:
        """Remove all registered tools."""
        self._tools.clear()
        self._tool_classes.clear()
        logger.info("Registry cleared")

    def load_builtins(self) -> None:
        """
        Load all built-in tools into the registry.

        This registers the standard tools provided by the platform:
        - HttpTool: HTTP requests
        - DateTimeTool: Date/time operations
        - get_weather: Weather data (mock)
        - search_knowledge_base: Knowledge search (mock)
        - calculate: Basic math operations
        """
        # Import here to avoid circular imports
        from src.domain.agents.tools.builtin import (
            DateTimeTool,
            HttpTool,
            calculate,
            get_weather,
            search_knowledge_base,
        )

        # Register class-based tools
        self.register(HttpTool())
        self.register(DateTimeTool())

        # Register function-based tools (already wrapped by @tool decorator)
        self.register(get_weather)
        self.register(search_knowledge_base)
        self.register(calculate)

        logger.info(f"Loaded {self.count()} built-in tools")

    def get_tool_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a tool.

        Args:
            name: Tool name

        Returns:
            Dictionary with tool metadata or None if not found
        """
        tool = self.get(name)
        if tool is None:
            return None

        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.get_schema(),
            "class": tool.__class__.__name__,
        }

    def get_all_info(self) -> List[Dict[str, Any]]:
        """
        Get detailed information about all registered tools.

        Returns:
            List of tool information dictionaries
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.get_schema(),
                "class": tool.__class__.__name__,
            }
            for tool in self._tools.values()
        ]

    def __contains__(self, name: str) -> bool:
        """Support 'in' operator for checking tool existence."""
        return self.has(name)

    def __len__(self) -> int:
        """Support len() for getting tool count."""
        return self.count()

    def __repr__(self) -> str:
        """String representation of registry."""
        return f"<ToolRegistry(tools={list(self._tools.keys())})>"


def get_tool_registry() -> ToolRegistry:
    """
    Get the global tool registry singleton.

    Creates the registry and loads built-in tools on first call.

    Returns:
        ToolRegistry singleton instance

    Example:
        registry = get_tool_registry()
        tool = registry.get("http_request")
    """
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ToolRegistry()
        _registry_instance.load_builtins()
        logger.info("Global tool registry initialized with built-in tools")
    return _registry_instance


def reset_tool_registry() -> None:
    """
    Reset the global tool registry.

    Primarily used for testing to ensure clean state.
    """
    global _registry_instance
    if _registry_instance is not None:
        _registry_instance.clear()
    _registry_instance = None
    logger.debug("Global tool registry reset")
