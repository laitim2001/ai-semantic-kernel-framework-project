"""
Agent 工具模組

提供 Agent Framework 可用的工具集合。

Sprint 38: Phase 8 - Agent 整合與擴展

Exports:
    - BaseTool: 工具基類
    - ToolResult: 工具執行結果
    - ToolSchema: 工具 Schema 定義
    - ToolParameter: 工具參數定義
    - ToolStatus: 工具執行狀態
    - ToolRegistry: 工具註冊表
    - get_tool_registry: 獲取全局工具註冊表
    - CodeInterpreterTool: Code Interpreter 工具
"""

# Base classes and utilities
from .base import (
    BaseTool,
    ToolResult,
    ToolSchema,
    ToolParameter,
    ToolStatus,
    ToolRegistry,
    get_tool_registry,
)

# Tool implementations
from .code_interpreter_tool import CodeInterpreterTool

__all__ = [
    # Base
    "BaseTool",
    "ToolResult",
    "ToolSchema",
    "ToolParameter",
    "ToolStatus",
    "ToolRegistry",
    "get_tool_registry",
    # Tools
    "CodeInterpreterTool",
]


def register_default_tools() -> None:
    """註冊預設工具到全局註冊表。

    Example:
        ```python
        from src.integrations.agent_framework.tools import register_default_tools

        register_default_tools()
        ```
    """
    registry = get_tool_registry()

    # 註冊 Code Interpreter 工具
    if "code_interpreter" not in registry:
        registry.register(CodeInterpreterTool())
