"""
Tests for Agent Framework Tool Base Classes

Sprint 38: Agent 整合與擴展
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from dataclasses import asdict

from src.integrations.agent_framework.tools.base import (
    BaseTool,
    ToolResult,
    ToolSchema,
    ToolParameter,
    ToolStatus,
    ToolRegistry,
    get_tool_registry,
)


# =============================================================================
# ToolResult Tests
# =============================================================================

class TestToolResult:
    """ToolResult 數據類測試。"""

    def test_create_success_result(self):
        """測試創建成功結果。"""
        result = ToolResult(
            success=True,
            output="Hello World",
            metadata={"execution_time": 1.5},
        )

        assert result.success is True
        assert result.output == "Hello World"
        assert result.metadata == {"execution_time": 1.5}
        assert result.status == ToolStatus.SUCCESS
        assert result.error is None
        assert result.files == []

    def test_create_failure_result(self):
        """測試創建失敗結果。"""
        result = ToolResult(
            success=False,
            output="",
            error="Division by zero",
            status=ToolStatus.ERROR,
        )

        assert result.success is False
        assert result.error == "Division by zero"
        assert result.status == ToolStatus.ERROR

    def test_result_with_files(self):
        """測試帶文件的結果。"""
        result = ToolResult(
            success=True,
            output="Chart generated",
            files=[
                {"type": "image", "file_id": "file-123", "filename": "chart.png"}
            ],
        )

        assert len(result.files) == 1
        assert result.files[0]["type"] == "image"
        assert result.files[0]["file_id"] == "file-123"

    def test_result_status_enum(self):
        """測試狀態枚舉值。"""
        assert ToolStatus.SUCCESS.value == "success"
        assert ToolStatus.FAILURE.value == "failure"
        assert ToolStatus.ERROR.value == "error"
        assert ToolStatus.TIMEOUT.value == "timeout"
        assert ToolStatus.PARTIAL.value == "partial"


# =============================================================================
# ToolSchema Tests
# =============================================================================

class TestToolSchema:
    """ToolSchema 測試。"""

    def test_create_schema(self):
        """測試創建 schema。"""
        schema = ToolSchema(
            name="code_interpreter",
            description="Execute Python code",
            parameters=[
                ToolParameter(
                    name="code",
                    type="string",
                    description="Python code to execute",
                    required=True,
                )
            ],
        )

        assert schema.name == "code_interpreter"
        assert schema.description == "Execute Python code"
        assert len(schema.parameters) == 1
        assert schema.parameters[0].name == "code"
        assert schema.parameters[0].required is True

    def test_to_openai_function(self):
        """測試轉換為 OpenAI Function 格式。"""
        schema = ToolSchema(
            name="test_tool",
            description="A test tool",
            parameters=[
                ToolParameter(
                    name="input",
                    type="string",
                    description="Input value",
                    required=True,
                )
            ],
        )

        result = schema.to_openai_function()

        assert result["type"] == "function"
        assert result["function"]["name"] == "test_tool"
        assert result["function"]["description"] == "A test tool"
        assert "input" in result["function"]["parameters"]["properties"]
        assert "input" in result["function"]["parameters"]["required"]


# =============================================================================
# BaseTool Tests
# =============================================================================

class TestBaseTool:
    """BaseTool 抽象類測試。"""

    def test_cannot_instantiate_base_tool(self):
        """測試無法直接實例化 BaseTool。"""
        with pytest.raises(TypeError):
            BaseTool()

    def test_concrete_tool_implementation(self):
        """測試具體工具實現。"""

        class ConcreteTool(BaseTool):
            name = "concrete_tool"
            description = "A concrete tool"

            async def run(self, **kwargs):
                return ToolResult(
                    success=True,
                    output="OK",
                    metadata={},
                )

        tool = ConcreteTool()
        assert tool.name == "concrete_tool"
        assert tool.description == "A concrete tool"

    @pytest.mark.asyncio
    async def test_tool_run_method(self):
        """測試工具執行方法。"""

        class EchoTool(BaseTool):
            name = "echo"
            description = "Echo input"

            async def run(self, **kwargs):
                text = kwargs.get("text", "")
                return ToolResult(
                    success=True,
                    output=f"Echo: {text}",
                    metadata={"input_length": len(text)},
                )

        tool = EchoTool()
        result = await tool.run(text="Hello")

        assert result.success is True
        assert result.output == "Echo: Hello"
        assert result.metadata["input_length"] == 5

    def test_tool_schema_property(self):
        """測試獲取工具 schema 屬性。"""

        class TestTool(BaseTool):
            name = "test_tool"
            description = "Test tool description"

            async def run(self, **kwargs):
                return ToolResult(success=True, output="", metadata={})

        tool = TestTool()
        schema = tool.schema  # 使用 schema 屬性

        assert schema.name == "test_tool"
        assert schema.description == "Test tool description"


# =============================================================================
# ToolRegistry Tests
# =============================================================================

class TestToolRegistry:
    """ToolRegistry 測試。"""

    def test_register_tool(self):
        """測試註冊工具。"""

        class MyTool(BaseTool):
            name = "my_tool"
            description = "My tool"

            async def run(self, **kwargs):
                return ToolResult(success=True, output="", metadata={})

        registry = ToolRegistry()
        tool = MyTool()

        registry.register(tool)

        assert "my_tool" in registry
        assert registry.get("my_tool") is tool

    def test_register_duplicate_overwrites(self):
        """測試重複註冊會覆蓋之前的工具 (警告但不拋錯誤)。"""

        class MyTool1(BaseTool):
            name = "duplicate_tool"
            description = "First version"

            async def run(self, **kwargs):
                return ToolResult(success=True, output="v1", metadata={})

        class MyTool2(BaseTool):
            name = "duplicate_tool"
            description = "Second version"

            async def run(self, **kwargs):
                return ToolResult(success=True, output="v2", metadata={})

        registry = ToolRegistry()
        tool1 = MyTool1()
        tool2 = MyTool2()

        registry.register(tool1)
        registry.register(tool2)  # 應該覆蓋而非拋錯

        # 驗證取到的是第二個工具
        assert registry.get("duplicate_tool") is tool2
        assert registry.get("duplicate_tool").description == "Second version"

    def test_unregister_tool(self):
        """測試取消註冊工具。"""

        class MyTool(BaseTool):
            name = "to_remove"
            description = "To be removed"

            async def run(self, **kwargs):
                return ToolResult(success=True, output="", metadata={})

        registry = ToolRegistry()
        registry.register(MyTool())

        assert "to_remove" in registry
        registry.unregister("to_remove")
        assert "to_remove" not in registry

    def test_list_tools(self):
        """測試列出所有工具。"""

        class ToolA(BaseTool):
            name = "tool_a"
            description = "Tool A"

            async def run(self, **kwargs):
                return ToolResult(success=True, output="", metadata={})

        class ToolB(BaseTool):
            name = "tool_b"
            description = "Tool B"

            async def run(self, **kwargs):
                return ToolResult(success=True, output="", metadata={})

        registry = ToolRegistry()
        registry.register(ToolA())
        registry.register(ToolB())

        tools = registry.list_tools()

        assert len(tools) == 2
        assert "tool_a" in tools
        assert "tool_b" in tools

    def test_get_nonexistent_tool(self):
        """測試獲取不存在的工具。"""
        registry = ToolRegistry()

        assert registry.get("nonexistent") is None

    def test_contains_operator(self):
        """測試 in 操作符。"""

        class MyTool(BaseTool):
            name = "check_tool"
            description = "Check"

            async def run(self, **kwargs):
                return ToolResult(success=True, output="", metadata={})

        registry = ToolRegistry()
        registry.register(MyTool())

        assert "check_tool" in registry
        assert "missing_tool" not in registry


class TestGetToolRegistry:
    """測試 get_tool_registry 單例函數。"""

    def test_returns_registry_instance(self):
        """測試返回 ToolRegistry 實例。"""
        registry = get_tool_registry()
        assert isinstance(registry, ToolRegistry)

    def test_returns_same_instance(self):
        """測試返回相同實例 (單例模式)。"""
        registry1 = get_tool_registry()
        registry2 = get_tool_registry()

        assert registry1 is registry2
