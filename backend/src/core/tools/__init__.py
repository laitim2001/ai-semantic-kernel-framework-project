"""
Tools module for IPA Platform

Provides Tool Factory pattern for dynamic tool registration and execution.
"""
from .base import ITool, ToolExecutionResult
from .factory import ToolFactory, get_tool_factory
from .builtin.http_tool import HttpTool
from .builtin.database_tool import DatabaseTool
from .builtin.email_tool import EmailTool

__all__ = [
    "ITool",
    "ToolExecutionResult",
    "ToolFactory",
    "get_tool_factory",
    "HttpTool",
    "DatabaseTool",
    "EmailTool",
]
