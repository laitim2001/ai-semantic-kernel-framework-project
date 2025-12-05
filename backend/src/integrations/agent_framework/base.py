"""
Agent Framework Integration - Base Classes

提供所有 Agent Framework 適配器的基礎類別。
這些抽象類定義了適配器的通用介面和生命週期管理。

設計原則:
    1. 隔離性: 隔離 Agent Framework API 變更的影響
    2. 一致性: 提供統一的適配器介面
    3. 可擴展性: 便於添加新的適配器類型
    4. 可測試性: 支持 mock 和單元測試

類別層次:
    BaseAdapter (抽象基類)
    └── BuilderAdapter (Builder 適配器基類)
        ├── ConcurrentBuilderAdapter
        ├── HandoffBuilderAdapter
        ├── GroupChatBuilderAdapter
        ├── MagenticBuilderAdapter
        └── WorkflowExecutorAdapter

使用範例:
    class MyAdapter(BuilderAdapter):
        def build(self) -> Workflow:
            # 實現構建邏輯
            pass

        async def initialize(self) -> None:
            # 初始化資源
            self._initialized = True

        async def cleanup(self) -> None:
            # 清理資源
            self._initialized = False
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Optional, TypeVar
import logging

from .exceptions import AdapterInitializationError, WorkflowBuildError

logger = logging.getLogger(__name__)

# Type variables for generic typing
T = TypeVar("T")  # Builder type
R = TypeVar("R")  # Result type


class BaseAdapter(ABC):
    """
    所有 Agent Framework 適配器的抽象基類。

    提供:
        - 配置管理
        - 生命週期管理 (initialize/cleanup)
        - 狀態追蹤
        - 日誌記錄

    Attributes:
        _config: 適配器配置字典
        _initialized: 初始化狀態標記
        _logger: 日誌記錄器

    Example:
        class MyAdapter(BaseAdapter):
            async def initialize(self) -> None:
                # 執行初始化
                self._initialized = True

            async def cleanup(self) -> None:
                # 執行清理
                self._initialized = False
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化適配器。

        Args:
            config: 可選的配置字典，包含適配器特定的設置
        """
        self._config = config or {}
        self._initialized = False
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def initialize(self) -> None:
        """
        初始化適配器資源。

        子類必須實現此方法來執行任何必要的初始化操作，
        例如建立連接、載入資源等。

        Raises:
            AdapterInitializationError: 初始化失敗時
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """
        清理適配器資源。

        子類必須實現此方法來釋放任何持有的資源，
        例如關閉連接、釋放內存等。
        """
        pass

    @property
    def is_initialized(self) -> bool:
        """檢查適配器是否已初始化。"""
        return self._initialized

    @property
    def config(self) -> Dict[str, Any]:
        """獲取適配器配置的只讀副本。"""
        return self._config.copy()

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        安全地獲取配置值。

        Args:
            key: 配置鍵名
            default: 默認值（如果鍵不存在）

        Returns:
            配置值或默認值
        """
        return self._config.get(key, default)

    async def ensure_initialized(self) -> None:
        """
        確保適配器已初始化。

        如果尚未初始化，則執行初始化。

        Raises:
            AdapterInitializationError: 初始化失敗時
        """
        if not self._initialized:
            try:
                await self.initialize()
            except Exception as e:
                raise AdapterInitializationError(
                    f"Failed to initialize {self.__class__.__name__}: {e}"
                ) from e

    async def __aenter__(self) -> "BaseAdapter":
        """異步上下文管理器入口。"""
        await self.ensure_initialized()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """異步上下文管理器出口。"""
        await self.cleanup()

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"initialized={self._initialized}, "
            f"config_keys={list(self._config.keys())})"
        )


class BuilderAdapter(BaseAdapter, Generic[T, R]):
    """
    Builder 類適配器的抽象基類。

    為 Agent Framework 的各種 Builder（如 ConcurrentBuilder、
    GroupChatBuilder 等）提供統一的適配介面。

    提供:
        - Builder 實例管理
        - Workflow 構建和執行
        - 事件處理

    Type Parameters:
        T: Agent Framework Builder 類型
        R: 執行結果類型

    Attributes:
        _builder: Agent Framework Builder 實例
        _workflow: 構建後的 Workflow 實例

    Example:
        class MyConcurrentAdapter(BuilderAdapter[ConcurrentBuilder, WorkflowRunResult]):
            def build(self) -> Workflow:
                self._builder = ConcurrentBuilder()
                # 配置 builder
                return self._builder.build()
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化 Builder 適配器。

        Args:
            config: 可選的配置字典
        """
        super().__init__(config)
        self._builder: Optional[T] = None
        self._workflow = None
        self._built = False

    @abstractmethod
    def build(self):
        """
        構建 Workflow。

        子類必須實現此方法來配置 Builder 並構建 Workflow。

        Returns:
            構建完成的 Workflow 實例

        Raises:
            WorkflowBuildError: 構建失敗時
        """
        pass

    async def run(self, input_data: Any) -> R:
        """
        執行工作流。

        如果 workflow 尚未構建，會先調用 build()。

        Args:
            input_data: 工作流輸入數據

        Returns:
            工作流執行結果

        Raises:
            WorkflowBuildError: 構建失敗時
            ExecutionError: 執行失敗時
        """
        await self.ensure_initialized()

        if not self._workflow:
            try:
                self._workflow = self.build()
                self._built = True
            except Exception as e:
                raise WorkflowBuildError(
                    f"Failed to build workflow: {e}"
                ) from e

        return await self._workflow.run(input_data)

    async def run_stream(self, input_data: Any):
        """
        以串流模式執行工作流。

        Args:
            input_data: 工作流輸入數據

        Yields:
            工作流事件

        Raises:
            WorkflowBuildError: 構建失敗時
        """
        await self.ensure_initialized()

        if not self._workflow:
            try:
                self._workflow = self.build()
                self._built = True
            except Exception as e:
                raise WorkflowBuildError(
                    f"Failed to build workflow: {e}"
                ) from e

        async for event in self._workflow.run_stream(input_data):
            yield event

    @property
    def is_built(self) -> bool:
        """檢查工作流是否已構建。"""
        return self._built

    @property
    def workflow(self):
        """獲取構建的工作流（如果存在）。"""
        return self._workflow

    async def initialize(self) -> None:
        """
        初始化 Builder 適配器。

        默認實現僅設置初始化標記。
        子類可以覆寫以執行額外的初始化操作。
        """
        self._logger.debug(f"Initializing {self.__class__.__name__}")
        self._initialized = True

    async def cleanup(self) -> None:
        """
        清理 Builder 適配器資源。

        重置 builder 和 workflow 實例。
        子類可以覆寫以執行額外的清理操作。
        """
        self._logger.debug(f"Cleaning up {self.__class__.__name__}")
        self._builder = None
        self._workflow = None
        self._built = False
        self._initialized = False

    def reset(self) -> None:
        """
        重置適配器狀態（同步版本）。

        清除 builder 和 workflow，但保持初始化狀態。
        用於需要重新構建工作流的場景。
        """
        self._builder = None
        self._workflow = None
        self._built = False

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"initialized={self._initialized}, "
            f"built={self._built}, "
            f"config_keys={list(self._config.keys())})"
        )
