"""Base classes for Claude SDK tools."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class ToolResult:
    """Result from tool execution."""

    content: str
    success: bool = True
    error: Optional[str] = None

    def __str__(self) -> str:
        if self.success:
            return self.content
        return f"Error: {self.error}"


class Tool(ABC):
    """
    Base class for all tools.

    Tools are the building blocks of agent capabilities.
    Each tool must implement execute() and get_schema().
    """

    name: str
    description: str

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given arguments.

        Args:
            **kwargs: Tool-specific arguments

        Returns:
            ToolResult with content and success status
        """
        pass

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        Get the tool's input schema.

        Returns:
            JSON Schema dictionary describing the tool's parameters
        """
        pass

    def get_definition(self) -> Dict[str, Any]:
        """
        Get the complete tool definition for Claude API.

        Returns:
            Tool definition dictionary
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.get_schema(),
        }
