"""
Agent 工具基類

定義 Agent Framework 工具的基礎接口和抽象類。

Sprint 38: Phase 8 - Agent 整合與擴展
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ToolStatus(Enum):
    """工具執行狀態。"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class ToolResult:
    """工具執行結果。

    所有工具執行的統一返回格式。

    Attributes:
        success: 是否成功
        output: 輸出內容
        metadata: 額外的元數據
        status: 執行狀態
        error: 錯誤信息 (如果有)
        files: 生成的文件列表
    """
    success: bool
    output: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: ToolStatus = ToolStatus.SUCCESS
    error: Optional[str] = None
    files: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式。"""
        return {
            "success": self.success,
            "output": self.output,
            "metadata": self.metadata,
            "status": self.status.value,
            "error": self.error,
            "files": self.files,
        }

    @classmethod
    def success_result(
        cls,
        output: Any,
        metadata: Optional[Dict[str, Any]] = None,
        files: Optional[List[Dict[str, Any]]] = None,
    ) -> "ToolResult":
        """創建成功結果。"""
        return cls(
            success=True,
            output=output,
            metadata=metadata or {},
            status=ToolStatus.SUCCESS,
            files=files or [],
        )

    @classmethod
    def failure_result(
        cls,
        error: str,
        output: Any = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ToolResult":
        """創建失敗結果。"""
        return cls(
            success=False,
            output=output,
            metadata=metadata or {},
            status=ToolStatus.FAILURE,
            error=error,
        )

    @classmethod
    def error_result(
        cls,
        error: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ToolResult":
        """創建錯誤結果。"""
        return cls(
            success=False,
            output=None,
            metadata=metadata or {},
            status=ToolStatus.ERROR,
            error=error,
        )


@dataclass
class ToolParameter:
    """工具參數定義。

    Attributes:
        name: 參數名稱
        type: 參數類型
        description: 參數描述
        required: 是否必需
        default: 預設值
    """
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolSchema:
    """工具 Schema 定義。

    描述工具的完整接口規範。

    Attributes:
        name: 工具名稱
        description: 工具描述
        parameters: 參數列表
        returns: 返回值描述
    """
    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)
    returns: str = "ToolResult"

    def to_openai_function(self) -> Dict[str, Any]:
        """轉換為 OpenAI Function 格式。

        Returns:
            OpenAI Function 定義
        """
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description,
            }
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


class BaseTool(ABC):
    """Agent 工具基類。

    所有 Agent 工具必須繼承此類並實現 run 方法。

    Example:
        ```python
        class MyTool(BaseTool):
            name = "my_tool"
            description = "Does something useful"

            async def run(self, **kwargs) -> ToolResult:
                # 實現工具邏輯
                return ToolResult.success_result("Done!")
        ```
    """

    # 類屬性 - 子類必須覆蓋
    name: str = "base_tool"
    description: str = "Base tool implementation"

    def __init__(self):
        """初始化工具。"""
        self._initialized = False
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @property
    def schema(self) -> ToolSchema:
        """獲取工具 Schema。

        子類可以覆蓋此方法提供更詳細的 Schema。
        """
        return ToolSchema(
            name=self.name,
            description=self.description,
        )

    async def initialize(self) -> None:
        """初始化工具資源。

        子類可以覆蓋此方法進行資源初始化。
        """
        self._initialized = True
        self._logger.debug(f"Tool {self.name} initialized")

    @abstractmethod
    async def run(self, **kwargs: Any) -> ToolResult:
        """執行工具操作。

        Args:
            **kwargs: 工具參數

        Returns:
            ToolResult 包含執行結果
        """
        pass

    async def cleanup(self) -> None:
        """清理工具資源。

        子類可以覆蓋此方法進行資源清理。
        """
        self._initialized = False
        self._logger.debug(f"Tool {self.name} cleaned up")

    async def __aenter__(self) -> "BaseTool":
        """異步上下文管理器入口。"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """異步上下文管理器出口。"""
        await self.cleanup()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name})>"


class ToolRegistry:
    """工具註冊表。

    管理所有可用的 Agent 工具。

    Example:
        ```python
        registry = ToolRegistry()
        registry.register(MyTool())

        tool = registry.get("my_tool")
        result = await tool.run(param="value")
        ```
    """

    def __init__(self):
        """初始化註冊表。"""
        self._tools: Dict[str, BaseTool] = {}
        self._logger = logging.getLogger(f"{__name__}.ToolRegistry")

    def register(self, tool: BaseTool) -> None:
        """註冊工具。

        Args:
            tool: 要註冊的工具實例
        """
        if tool.name in self._tools:
            self._logger.warning(f"Tool {tool.name} already registered, overwriting")
        self._tools[tool.name] = tool
        self._logger.info(f"Registered tool: {tool.name}")

    def unregister(self, name: str) -> bool:
        """取消註冊工具。

        Args:
            name: 工具名稱

        Returns:
            是否成功取消註冊
        """
        if name in self._tools:
            del self._tools[name]
            self._logger.info(f"Unregistered tool: {name}")
            return True
        return False

    def get(self, name: str) -> Optional[BaseTool]:
        """獲取工具。

        Args:
            name: 工具名稱

        Returns:
            工具實例，如果不存在則返回 None
        """
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """列出所有已註冊的工具名稱。

        Returns:
            工具名稱列表
        """
        return list(self._tools.keys())

    def get_schemas(self) -> List[Dict[str, Any]]:
        """獲取所有工具的 OpenAI Function Schema。

        Returns:
            OpenAI Function 定義列表
        """
        return [tool.schema.to_openai_function() for tool in self._tools.values()]

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


# 全局工具註冊表實例
_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """獲取全局工具註冊表。

    Returns:
        全局 ToolRegistry 實例
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry
