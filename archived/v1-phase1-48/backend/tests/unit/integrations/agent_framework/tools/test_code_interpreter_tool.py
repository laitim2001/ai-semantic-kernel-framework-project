"""
Tests for CodeInterpreterTool

Sprint 38: Agent 整合與擴展
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.integrations.agent_framework.tools.code_interpreter_tool import (
    CodeInterpreterTool,
)
from src.integrations.agent_framework.tools.base import ToolResult, ToolStatus


# =============================================================================
# CodeInterpreterTool Tests
# =============================================================================

class TestCodeInterpreterTool:
    """CodeInterpreterTool 測試。"""

    def test_tool_attributes(self):
        """測試工具屬性。"""
        tool = CodeInterpreterTool()

        assert tool.name == "code_interpreter"
        assert tool.description is not None
        assert "execute" in tool.SUPPORTED_ACTIONS
        assert "analyze" in tool.SUPPORTED_ACTIONS
        assert "visualize" in tool.SUPPORTED_ACTIONS

    def test_tool_with_custom_adapter(self):
        """測試使用自定義 adapter。"""
        mock_adapter = MagicMock()
        tool = CodeInterpreterTool(adapter=mock_adapter)

        assert tool._adapter is mock_adapter

    def test_schema_property(self):
        """測試 schema 屬性。"""
        tool = CodeInterpreterTool()
        schema = tool.schema  # 使用 schema 屬性

        assert schema.name == "code_interpreter"
        assert len(schema.parameters) > 0

        # Check action parameter exists
        action_param = next(
            (p for p in schema.parameters if p.name == "action"), None
        )
        assert action_param is not None
        assert action_param.required is True

    @pytest.mark.asyncio
    async def test_run_invalid_action(self):
        """測試執行無效操作。"""
        tool = CodeInterpreterTool()

        result = await tool.run(action="invalid_action")

        assert result.success is False
        assert result.status == ToolStatus.ERROR
        assert "Unknown action" in result.error  # 錯誤訊息為 "Unknown action"

    @pytest.mark.asyncio
    async def test_execute_code_action(self):
        """測試執行代碼操作。"""
        # Create mock adapter
        mock_adapter = MagicMock()

        # Create mock execution result
        mock_exec_result = MagicMock()
        mock_exec_result.success = True
        mock_exec_result.output = "Result: 4"
        mock_exec_result.execution_time = 1.5
        mock_exec_result.files = []
        mock_exec_result.error = None

        mock_adapter.execute.return_value = mock_exec_result

        tool = CodeInterpreterTool(adapter=mock_adapter)

        result = await tool.run(action="execute", code="print(2+2)")

        assert result.success is True
        assert result.output == "Result: 4"
        assert result.metadata["execution_time"] == 1.5
        mock_adapter.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_code_missing_code(self):
        """測試執行代碼缺少 code 參數。"""
        tool = CodeInterpreterTool()

        result = await tool.run(action="execute")

        assert result.success is False
        assert "code" in result.error.lower()

    @pytest.mark.asyncio
    async def test_analyze_task_action(self):
        """測試分析任務操作。"""
        mock_adapter = MagicMock()

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "Analysis complete"
        mock_result.execution_time = 2.0
        mock_result.files = []
        mock_result.error = None

        mock_adapter.analyze_task.return_value = mock_result

        tool = CodeInterpreterTool(adapter=mock_adapter)

        result = await tool.run(
            action="analyze",
            task="Analyze this data",
            context={"data": [1, 2, 3]}
        )

        assert result.success is True
        assert result.output == "Analysis complete"
        mock_adapter.analyze_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_missing_task(self):
        """測試分析缺少 task 參數。"""
        tool = CodeInterpreterTool()

        result = await tool.run(action="analyze")

        assert result.success is False
        assert "task" in result.error.lower()

    @pytest.mark.asyncio
    async def test_visualize_action(self):
        """測試生成可視化操作。"""
        mock_adapter = MagicMock()

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "Chart generated"
        mock_result.execution_time = 3.0
        mock_result.files = [{"type": "image", "file_id": "file-123"}]
        mock_result.error = None

        mock_adapter.execute.return_value = mock_result

        tool = CodeInterpreterTool(adapter=mock_adapter)

        result = await tool.run(
            action="visualize",
            data={"A": 10, "B": 20},
            chart_type="bar",
        )

        assert result.success is True
        assert "chart_type" in result.metadata
        mock_adapter.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_visualize_missing_data(self):
        """測試可視化缺少 data 參數。"""
        tool = CodeInterpreterTool()

        result = await tool.run(action="visualize")

        assert result.success is False
        assert "data" in result.error.lower()

    @pytest.mark.asyncio
    async def test_visualize_invalid_chart_type(self):
        """測試可視化使用無效圖表類型。"""
        tool = CodeInterpreterTool()

        result = await tool.run(
            action="visualize",
            data={"A": 1},
            chart_type="invalid_chart"
        )

        assert result.success is False
        assert "chart type" in result.error.lower()

    @pytest.mark.asyncio
    async def test_generate_chart_code(self):
        """測試生成圖表代碼。"""
        tool = CodeInterpreterTool()

        code = tool._generate_chart_code(
            data={"A": 10, "B": 20},
            chart_type="bar",
            title="Test Chart",
        )

        assert "matplotlib" in code
        assert "bar" in code
        assert "Test Chart" in code

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """測試清理資源。"""
        mock_adapter = MagicMock()
        tool = CodeInterpreterTool(adapter=mock_adapter)
        tool._owns_adapter = True  # 設置擁有 adapter

        await tool.cleanup()

        mock_adapter.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """測試異步上下文管理器。"""
        mock_adapter = MagicMock()
        tool = CodeInterpreterTool(adapter=mock_adapter)
        tool._owns_adapter = True

        async with tool:
            pass

        mock_adapter.cleanup.assert_called_once()


class TestCodeInterpreterToolChartTypes:
    """測試支援的圖表類型。"""

    @pytest.mark.parametrize("chart_type", [
        "bar", "line", "pie", "scatter", "hist", "box"
    ])
    def test_supported_chart_types(self, chart_type):
        """測試所有支援的圖表類型。"""
        tool = CodeInterpreterTool()

        assert chart_type in tool.SUPPORTED_CHART_TYPES

    def test_generate_bar_chart_code(self):
        """測試生成柱狀圖代碼。"""
        tool = CodeInterpreterTool()
        code = tool._generate_chart_code(
            data={"A": 1, "B": 2},
            chart_type="bar"
        )

        assert "bar" in code.lower()
        assert "plt" in code

    def test_generate_pie_chart_code(self):
        """測試生成圓餅圖代碼。"""
        tool = CodeInterpreterTool()
        code = tool._generate_chart_code(
            data={"A": 1, "B": 2},
            chart_type="pie"
        )

        assert "pie" in code.lower()
