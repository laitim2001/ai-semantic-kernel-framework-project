"""
Tool Factory for dynamic tool registration and execution

Provides centralized tool management with registration, discovery, and execution tracking.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

from .base import ITool, ToolExecutionResult

logger = logging.getLogger(__name__)


class ToolFactory:
    """
    Tool Factory 類別

    管理所有 Tool 的註冊、發現和執行
    支援動態註冊新 Tool,並追蹤執行歷史
    """

    def __init__(self):
        self._tools: Dict[str, ITool] = {}
        self._execution_history: List[Dict] = []

    def register(self, tool: ITool) -> None:
        """
        註冊 Tool

        Args:
            tool: 要註冊的 Tool 實例

        Raises:
            ValueError: Tool 名稱已存在
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")

        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name} - {tool.description}")

    def unregister(self, tool_name: str) -> None:
        """
        取消註冊 Tool

        Args:
            tool_name: Tool 名稱

        Raises:
            ValueError: Tool 不存在
        """
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' is not registered")

        del self._tools[tool_name]
        logger.info(f"Unregistered tool: {tool_name}")

    def get_tool(self, tool_name: str) -> ITool:
        """
        取得指定的 Tool

        Args:
            tool_name: Tool 名稱

        Returns:
            Tool 實例

        Raises:
            ValueError: Tool 不存在
        """
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not found")

        return self._tools[tool_name]

    def has_tool(self, tool_name: str) -> bool:
        """
        檢查 Tool 是否存在

        Args:
            tool_name: Tool 名稱

        Returns:
            True 如果 Tool 存在
        """
        return tool_name in self._tools

    def list_tools(self) -> List[Dict]:
        """
        列出所有已註冊的 Tool

        Returns:
            Tool 元資料列表
        """
        return [tool.get_metadata() for tool in self._tools.values()]

    async def execute_tool(
        self, tool_name: str, track_execution: bool = True, **kwargs
    ) -> ToolExecutionResult:
        """
        執行指定的 Tool

        Args:
            tool_name: Tool 名稱
            track_execution: 是否追蹤執行歷史
            **kwargs: Tool 執行參數

        Returns:
            ToolExecutionResult 包含執行結果

        Raises:
            ValueError: Tool 不存在或參數驗證失敗
            Exception: Tool 執行失敗
        """
        tool = self.get_tool(tool_name)

        # 驗證參數
        tool.validate_parameters(kwargs)

        # 執行 Tool
        start_time = datetime.now(timezone.utc)

        try:
            result = await tool.execute(**kwargs)

            if track_execution:
                self._track_execution(
                    tool_name=tool_name,
                    parameters=kwargs,
                    result=result,
                    start_time=start_time,
                )

            logger.info(
                f"Tool '{tool_name}' executed successfully in {result.execution_time_ms}ms"
            )

            return result

        except Exception as e:
            execution_time_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )

            error_result = ToolExecutionResult(
                success=False,
                output=None,
                error_message=str(e),
                execution_time_ms=execution_time_ms,
            )

            if track_execution:
                self._track_execution(
                    tool_name=tool_name,
                    parameters=kwargs,
                    result=error_result,
                    start_time=start_time,
                )

            logger.error(f"Tool '{tool_name}' execution failed: {e}")

            # Re-raise exception for caller to handle
            raise

    def _track_execution(
        self,
        tool_name: str,
        parameters: Dict,
        result: ToolExecutionResult,
        start_time: datetime,
    ) -> None:
        """
        追蹤 Tool 執行歷史

        Args:
            tool_name: Tool 名稱
            parameters: 執行參數
            result: 執行結果
            start_time: 開始時間
        """
        execution_record = {
            "tool_name": tool_name,
            "parameters": parameters,
            "success": result.success,
            "execution_time_ms": result.execution_time_ms,
            "error_message": result.error_message,
            "timestamp": start_time.isoformat(),
        }

        self._execution_history.append(execution_record)

        # Keep only last 1000 executions in memory
        if len(self._execution_history) > 1000:
            self._execution_history = self._execution_history[-1000:]

    def get_execution_history(
        self, tool_name: Optional[str] = None, limit: int = 100
    ) -> List[Dict]:
        """
        取得執行歷史

        Args:
            tool_name: 可選,過濾特定 Tool 的歷史
            limit: 返回的最大記錄數

        Returns:
            執行歷史記錄列表
        """
        history = self._execution_history

        if tool_name:
            history = [h for h in history if h["tool_name"] == tool_name]

        # Return latest records first
        return list(reversed(history[-limit:]))

    def get_tool_statistics(self, tool_name: Optional[str] = None) -> Dict:
        """
        取得 Tool 執行統計

        Args:
            tool_name: 可選,特定 Tool 的統計

        Returns:
            統計資料 (總執行次數、成功次數、失敗次數、平均執行時間)
        """
        history = self._execution_history

        if tool_name:
            history = [h for h in history if h["tool_name"] == tool_name]

        if not history:
            return {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "average_execution_time_ms": 0,
            }

        successful = [h for h in history if h["success"]]
        failed = [h for h in history if not h["success"]]

        total_time = sum(h["execution_time_ms"] for h in history)
        avg_time = total_time / len(history) if history else 0

        return {
            "total_executions": len(history),
            "successful_executions": len(successful),
            "failed_executions": len(failed),
            "average_execution_time_ms": round(avg_time, 2),
            "success_rate": (
                round(len(successful) / len(history) * 100, 2) if history else 0
            ),
        }


# Global Tool Factory instance
_tool_factory_instance: Optional[ToolFactory] = None


def get_tool_factory() -> ToolFactory:
    """
    取得全局 Tool Factory 實例 (Singleton pattern)

    Returns:
        ToolFactory 實例
    """
    global _tool_factory_instance

    if _tool_factory_instance is None:
        _tool_factory_instance = ToolFactory()
        logger.info("Created global ToolFactory instance")

    return _tool_factory_instance
