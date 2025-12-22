"""
Code Interpreter 工具

供 Agent 使用的 Code Interpreter 工具封裝。

Sprint 38: Phase 8 - Agent 整合與擴展
"""

from typing import Any, Dict, List, Optional
import json
import logging

from .base import BaseTool, ToolResult, ToolSchema, ToolParameter, ToolStatus
from ..builders.code_interpreter import CodeInterpreterAdapter, CodeInterpreterConfig

logger = logging.getLogger(__name__)


class CodeInterpreterTool(BaseTool):
    """Code Interpreter 工具 - 供 Agent 使用。

    將 CodeInterpreterAdapter 封裝為 Agent 可調用的工具。
    遵循 Agent Framework 的 Tool 規範。

    Supported Actions:
        - execute: 執行 Python 代碼
        - analyze: 分析任務/問題
        - visualize: 生成可視化圖表

    Example:
        ```python
        tool = CodeInterpreterTool()
        await tool.initialize()

        # Agent 調用執行代碼
        result = await tool.run(
            action="execute",
            code="import pandas as pd; print(pd.__version__)"
        )

        # Agent 調用分析任務
        result = await tool.run(
            action="analyze",
            task="Calculate the average of [1, 2, 3, 4, 5]"
        )

        # Agent 調用生成圖表
        result = await tool.run(
            action="visualize",
            data={"A": 10, "B": 20, "C": 30},
            chart_type="bar"
        )

        await tool.cleanup()
        ```
    """

    name: str = "code_interpreter"
    description: str = (
        "Execute Python code, analyze data, and generate visualizations. "
        "Supports actions: execute (run Python code), analyze (AI-driven analysis), "
        "visualize (generate charts from data)."
    )

    # 支援的操作類型
    SUPPORTED_ACTIONS = ["execute", "analyze", "visualize"]

    # 支援的圖表類型
    SUPPORTED_CHART_TYPES = ["bar", "line", "pie", "scatter", "hist", "box"]

    def __init__(
        self,
        adapter: Optional[CodeInterpreterAdapter] = None,
        config: Optional[CodeInterpreterConfig] = None,
    ):
        """初始化工具。

        Args:
            adapter: 可選的 CodeInterpreterAdapter 實例
            config: 可選的配置
        """
        super().__init__()
        self._config = config or CodeInterpreterConfig()
        self._adapter = adapter
        self._owns_adapter = adapter is None  # 是否需要自己管理 adapter

    @property
    def schema(self) -> ToolSchema:
        """獲取工具 Schema。"""
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="Action to perform: execute, analyze, or visualize",
                    required=True,
                ),
                ToolParameter(
                    name="code",
                    type="string",
                    description="Python code to execute (for 'execute' action)",
                    required=False,
                ),
                ToolParameter(
                    name="task",
                    type="string",
                    description="Task description for analysis (for 'analyze' action)",
                    required=False,
                ),
                ToolParameter(
                    name="data",
                    type="object",
                    description="Data for visualization (for 'visualize' action)",
                    required=False,
                ),
                ToolParameter(
                    name="chart_type",
                    type="string",
                    description="Chart type: bar, line, pie, scatter, hist, box",
                    required=False,
                    default="bar",
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Execution timeout in seconds",
                    required=False,
                    default=60,
                ),
            ],
            returns="ToolResult with execution output and generated files",
        )

    async def initialize(self) -> None:
        """初始化工具資源。"""
        if self._adapter is None:
            self._adapter = CodeInterpreterAdapter(config=self._config)
            self._owns_adapter = True
        await super().initialize()
        self._logger.info("CodeInterpreterTool initialized")

    async def run(self, **kwargs: Any) -> ToolResult:
        """執行工具操作。

        Args:
            action: 操作類型 (execute, analyze, visualize)
            **kwargs: 操作參數

        Returns:
            ToolResult 包含執行結果
        """
        action = kwargs.get("action")

        if not action:
            return ToolResult.error_result(
                "Missing required parameter: action",
                metadata={"available_actions": self.SUPPORTED_ACTIONS},
            )

        if action not in self.SUPPORTED_ACTIONS:
            return ToolResult.error_result(
                f"Unknown action: {action}",
                metadata={"available_actions": self.SUPPORTED_ACTIONS},
            )

        # 確保 adapter 已初始化
        if self._adapter is None:
            await self.initialize()

        try:
            if action == "execute":
                return await self._execute_code(**kwargs)
            elif action == "analyze":
                return await self._analyze_task(**kwargs)
            elif action == "visualize":
                return await self._generate_visualization(**kwargs)
            else:
                return ToolResult.error_result(f"Unhandled action: {action}")
        except Exception as e:
            self._logger.error(f"Tool execution failed: {e}", exc_info=True)
            return ToolResult.error_result(
                str(e),
                metadata={"action": action, "exception_type": type(e).__name__},
            )

    async def _execute_code(
        self,
        code: Optional[str] = None,
        timeout: int = 60,
        **kwargs,
    ) -> ToolResult:
        """執行 Python 代碼。

        Args:
            code: 要執行的 Python 代碼
            timeout: 超時時間 (秒)

        Returns:
            ToolResult 包含執行結果
        """
        if not code:
            return ToolResult.error_result(
                "Missing required parameter: code",
                metadata={"action": "execute"},
            )

        self._logger.info(f"Executing code: {code[:100]}...")

        result = self._adapter.execute(code=code, timeout=timeout)

        return ToolResult(
            success=result.success,
            output=result.output,
            metadata={
                "action": "execute",
                "execution_time": result.execution_time,
                "code_length": len(code),
            },
            status=ToolStatus.SUCCESS if result.success else ToolStatus.FAILURE,
            error=result.error,
            files=result.files,
        )

    async def _analyze_task(
        self,
        task: Optional[str] = None,
        context: Optional[str] = None,
        file_id: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        """分析任務。

        Args:
            task: 任務描述
            context: 額外上下文
            file_id: 可選的文件 ID

        Returns:
            ToolResult 包含分析結果
        """
        if not task:
            return ToolResult.error_result(
                "Missing required parameter: task",
                metadata={"action": "analyze"},
            )

        # 如果有 file_id，添加到任務描述中
        full_task = task
        if file_id:
            full_task = f"Analyze the file with ID {file_id}. {task}"

        self._logger.info(f"Analyzing task: {task[:100]}...")

        result = self._adapter.analyze_task(task=full_task, context=context)

        return ToolResult(
            success=result.success,
            output=result.output,
            metadata={
                "action": "analyze",
                "execution_time": result.execution_time,
                "file_id": file_id,
            },
            status=ToolStatus.SUCCESS if result.success else ToolStatus.FAILURE,
            error=result.error,
            files=result.files,
        )

    async def _generate_visualization(
        self,
        data: Optional[Dict[str, Any]] = None,
        chart_type: str = "bar",
        title: Optional[str] = None,
        x_label: Optional[str] = None,
        y_label: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        """生成可視化圖表。

        Args:
            data: 圖表數據
            chart_type: 圖表類型
            title: 圖表標題
            x_label: X 軸標籤
            y_label: Y 軸標籤

        Returns:
            ToolResult 包含生成的圖表信息
        """
        if not data:
            return ToolResult.error_result(
                "Missing required parameter: data",
                metadata={"action": "visualize"},
            )

        if chart_type not in self.SUPPORTED_CHART_TYPES:
            return ToolResult.error_result(
                f"Unsupported chart type: {chart_type}",
                metadata={
                    "action": "visualize",
                    "supported_types": self.SUPPORTED_CHART_TYPES,
                },
            )

        self._logger.info(f"Generating {chart_type} chart...")

        code = self._generate_chart_code(
            data=data,
            chart_type=chart_type,
            title=title,
            x_label=x_label,
            y_label=y_label,
        )

        result = self._adapter.execute(code=code)

        return ToolResult(
            success=result.success,
            output=result.output,
            metadata={
                "action": "visualize",
                "chart_type": chart_type,
                "execution_time": result.execution_time,
            },
            status=ToolStatus.SUCCESS if result.success else ToolStatus.FAILURE,
            error=result.error,
            files=result.files,
        )

    def _generate_chart_code(
        self,
        data: Dict[str, Any],
        chart_type: str,
        title: Optional[str] = None,
        x_label: Optional[str] = None,
        y_label: Optional[str] = None,
    ) -> str:
        """生成圖表代碼。

        Args:
            data: 圖表數據
            chart_type: 圖表類型
            title: 圖表標題
            x_label: X 軸標籤
            y_label: Y 軸標籤

        Returns:
            Python 代碼字符串
        """
        data_json = json.dumps(data)
        title = title or "Generated Chart"
        x_label = x_label or ""
        y_label = y_label or ""

        # 根據圖表類型生成相應的繪圖代碼
        if chart_type == "pie":
            plot_code = f"""
plt.pie(list(data.values()), labels=list(data.keys()), autopct='%1.1f%%')
"""
        elif chart_type == "scatter":
            plot_code = f"""
x_vals = list(range(len(data)))
plt.scatter(x_vals, list(data.values()))
plt.xticks(x_vals, list(data.keys()))
"""
        elif chart_type == "hist":
            plot_code = """
plt.hist(list(data.values()), bins='auto', edgecolor='black')
"""
        elif chart_type == "box":
            plot_code = """
plt.boxplot([list(data.values())], labels=['Data'])
"""
        elif chart_type == "line":
            plot_code = """
plt.plot(list(data.keys()), list(data.values()), marker='o')
"""
        else:  # bar
            plot_code = """
plt.bar(list(data.keys()), list(data.values()))
"""

        return f'''
import matplotlib
matplotlib.use('Agg')  # 非交互式後端
import matplotlib.pyplot as plt
import json

data = {data_json}

plt.figure(figsize=(10, 6))
{plot_code}
plt.title('{title}')
plt.xlabel('{x_label}')
plt.ylabel('{y_label}')
plt.tight_layout()
plt.savefig('chart.png', dpi=150)
plt.close()

print('Chart saved as chart.png')
'''

    async def cleanup(self) -> None:
        """清理工具資源。"""
        if self._owns_adapter and self._adapter is not None:
            self._adapter.cleanup()
            self._adapter = None
        await super().cleanup()
        self._logger.info("CodeInterpreterTool cleaned up")

    def __repr__(self) -> str:
        return f"<CodeInterpreterTool(initialized={self._initialized})>"
