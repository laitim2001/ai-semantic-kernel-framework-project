"""Claude SDK built-in tools.

This module provides Claude SDK built-in tools for file operations,
command execution, and web interactions.

Sprint 49 Implementation:
- S49-1: File Tools (Read, Write, Edit, MultiEdit, Glob, Grep) ✓
- S49-2: Command Tools (Bash, Task) ✓
- S49-4: Web Tools (WebFetch, WebSearch) ✓
"""

from .base import Tool, ToolResult
from .file_tools import Read, Write, Edit, MultiEdit, Glob, Grep
from .command_tools import Bash, Task
from .web_tools import WebSearch, WebFetch
from .registry import (
    register_tool,
    get_tool_instance,
    get_available_tools,
    get_tool_definitions,
    execute_tool,
)

__all__ = [
    # Base classes
    "Tool",
    "ToolResult",
    # File tools
    "Read",
    "Write",
    "Edit",
    "MultiEdit",
    "Glob",
    "Grep",
    # Command tools
    "Bash",
    "Task",
    # Web tools
    "WebSearch",
    "WebFetch",
    # Registry functions
    "register_tool",
    "get_tool_instance",
    "get_available_tools",
    "get_tool_definitions",
    "execute_tool",
]
