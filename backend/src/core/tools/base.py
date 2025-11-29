"""
Base Tool interface and execution result

All tools must implement the ITool interface for consistent execution.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, field


@dataclass
class ToolExecutionResult:
    """
    Tool 執行結果

    封裝 Tool 執行的結果,包含成功狀態、輸出資料、錯誤訊息等
    """

    success: bool
    output: Any
    error_message: Optional[str] = None
    execution_time_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "success": self.success,
            "output": self.output,
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata,
        }


class ITool(ABC):
    """
    Tool 基礎接口

    所有 Tool 必須實現此接口,提供一致的執行介面
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Tool 名稱 (唯一識別符)

        Returns:
            Tool 的唯一名稱
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Tool 描述

        Returns:
            Tool 功能的詳細描述
        """
        pass

    @property
    @abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        """
        Tool 參數 schema (JSON Schema format)

        Returns:
            參數的 JSON Schema 定義
        """
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolExecutionResult:
        """
        執行 Tool

        Args:
            **kwargs: Tool 執行所需的參數

        Returns:
            ToolExecutionResult 包含執行結果

        Raises:
            ValueError: 參數驗證失敗
            Exception: Tool 執行失敗
        """
        pass

    def validate_parameters(self, params: Dict[str, Any]) -> None:
        """
        驗證參數是否符合 schema

        Args:
            params: 要驗證的參數

        Raises:
            ValueError: 參數驗證失敗
        """
        # 基本驗證 - 子類可以 override 進行更嚴格的驗證
        schema = self.parameters_schema
        required_params = schema.get("required", [])

        for param in required_params:
            if param not in params:
                raise ValueError(f"Missing required parameter: {param}")

    def get_metadata(self) -> Dict[str, Any]:
        """
        取得 Tool 元資料

        Returns:
            包含 Tool 名稱、描述、參數 schema 的字典
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters_schema": self.parameters_schema,
        }
