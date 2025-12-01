# =============================================================================
# IPA Platform - Tool Base Classes
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Base classes and abstractions for AI Agent tools.
# Provides:
#   - ToolResult: Standard result format for tool execution
#   - ToolError: Exception class for tool failures
#   - BaseTool: Abstract base class for class-based tools
#   - FunctionTool: Wrapper for function-based tools
#
# Usage:
#   # Class-based tool
#   class MyTool(BaseTool):
#       name = "my_tool"
#       description = "Does something useful"
#
#       async def execute(self, **kwargs) -> ToolResult:
#           return ToolResult(success=True, data={"result": "done"})
#
#   # Function-based tool
#   @tool(name="greet", description="Greet a user")
#   async def greet(name: str) -> str:
#       return f"Hello, {name}!"
# =============================================================================

import asyncio
import functools
import inspect
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type, Union

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ToolResult:
    """
    Standard result format for tool execution.

    Attributes:
        success: Whether the tool execution succeeded
        data: Result data (any type depending on tool)
        error: Error message if execution failed
        metadata: Additional metadata about the execution

    Example:
        result = ToolResult(
            success=True,
            data={"temperature": 72, "conditions": "sunny"},
        )
    """

    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """String representation for agent consumption."""
        if self.success:
            if isinstance(self.data, dict):
                return str(self.data)
            return str(self.data) if self.data is not None else "Success"
        return f"Error: {self.error}"


class ToolError(Exception):
    """
    Exception raised when tool execution fails.

    Attributes:
        message: Error description
        tool_name: Name of the tool that failed
        original_error: Original exception if any

    Example:
        raise ToolError(
            message="API request failed",
            tool_name="http_tool",
            original_error=e,
        )
    """

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        self.message = message
        self.tool_name = tool_name
        self.original_error = original_error
        super().__init__(message)

    def to_result(self) -> ToolResult:
        """Convert error to ToolResult."""
        return ToolResult(
            success=False,
            error=self.message,
            metadata={
                "tool_name": self.tool_name,
                "original_error": str(self.original_error) if self.original_error else None,
            },
        )


# =============================================================================
# Base Tool Class
# =============================================================================


class BaseTool(ABC):
    """
    Abstract base class for AI Agent tools.

    Subclasses must define:
        - name: Unique tool identifier
        - description: Tool description for agent context
        - execute(): Async method that performs the tool action

    Attributes:
        name: Tool identifier used by agents
        description: Description shown to agents
        parameters: Parameter schema for validation

    Example:
        class WeatherTool(BaseTool):
            name = "get_weather"
            description = "Get current weather for a location"

            async def execute(self, location: str) -> ToolResult:
                # Fetch weather data...
                return ToolResult(success=True, data=weather_data)
    """

    # Subclasses must define these
    name: str = ""
    description: str = ""

    # Optional parameter schema (JSON Schema format)
    parameters: Dict[str, Any] = {}

    def __init__(self):
        """Initialize the tool."""
        if not self.name:
            raise ValueError(f"{self.__class__.__name__} must define 'name'")
        if not self.description:
            raise ValueError(f"{self.__class__.__name__} must define 'description'")

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            ToolResult with success status and data/error

        Raises:
            ToolError: If execution fails
        """
        pass

    async def __call__(self, **kwargs) -> ToolResult:
        """
        Call the tool (wrapper around execute with error handling).

        Args:
            **kwargs: Tool parameters

        Returns:
            ToolResult (never raises, errors captured in result)
        """
        try:
            return await self.execute(**kwargs)
        except ToolError as e:
            logger.error(f"Tool {self.name} failed: {e.message}")
            return e.to_result()
        except Exception as e:
            logger.error(f"Tool {self.name} unexpected error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"tool_name": self.name},
            )

    def as_function(self) -> Callable:
        """
        Convert tool to a callable function for Agent Framework.

        Returns:
            Async function that can be passed to agent executor.

        Example:
            tool = HttpTool()
            func = tool.as_function()
            # func can now be passed to agent tools list
        """

        async def tool_function(**kwargs) -> str:
            result = await self(**kwargs)
            return str(result)

        # Add metadata for agent framework
        tool_function.__name__ = self.name
        tool_function.__doc__ = self.description

        return tool_function

    def get_schema(self) -> Dict[str, Any]:
        """
        Get JSON Schema for tool parameters.

        Returns:
            JSON Schema dictionary describing parameters
        """
        if self.parameters:
            return self.parameters

        # Auto-generate from execute signature
        sig = inspect.signature(self.execute)
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "kwargs"):
                continue

            param_info: Dict[str, Any] = {"type": "string"}  # Default type

            # Try to infer type from annotation
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_info["type"] = "integer"
                elif param.annotation == float:
                    param_info["type"] = "number"
                elif param.annotation == bool:
                    param_info["type"] = "boolean"
                elif param.annotation == list or param.annotation == List:
                    param_info["type"] = "array"
                elif param.annotation == dict or param.annotation == Dict:
                    param_info["type"] = "object"

            properties[param_name] = param_info

            # Check if required (no default value)
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}')>"


# =============================================================================
# Function Tool Wrapper
# =============================================================================


class FunctionTool(BaseTool):
    """
    Wrapper to convert a regular function into a BaseTool.

    Allows using simple functions as tools without creating a class.

    Example:
        async def my_func(x: int) -> str:
            return f"Result: {x * 2}"

        tool = FunctionTool(
            func=my_func,
            name="double",
            description="Double a number",
        )
    """

    def __init__(
        self,
        func: Callable,
        name: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize FunctionTool.

        Args:
            func: The function to wrap (async or sync)
            name: Tool name
            description: Tool description
            parameters: Optional parameter schema
        """
        self._func = func
        self.name = name
        self.description = description
        self.parameters = parameters or {}
        super().__init__()

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the wrapped function."""
        try:
            # Handle both sync and async functions
            if asyncio.iscoroutinefunction(self._func):
                result = await self._func(**kwargs)
            else:
                result = self._func(**kwargs)

            # Wrap result in ToolResult if not already
            if isinstance(result, ToolResult):
                return result

            return ToolResult(success=True, data=result)

        except Exception as e:
            raise ToolError(
                message=str(e),
                tool_name=self.name,
                original_error=e,
            )


# =============================================================================
# Decorator
# =============================================================================


def tool(
    name: str,
    description: str,
    parameters: Optional[Dict[str, Any]] = None,
) -> Callable:
    """
    Decorator to convert a function into a tool.

    Args:
        name: Tool name
        description: Tool description
        parameters: Optional parameter schema

    Returns:
        Decorator function

    Example:
        @tool(name="greet", description="Greet a user by name")
        async def greet(name: str) -> str:
            return f"Hello, {name}!"
    """

    def decorator(func: Callable) -> FunctionTool:
        return FunctionTool(
            func=func,
            name=name,
            description=description,
            parameters=parameters,
        )

    return decorator
