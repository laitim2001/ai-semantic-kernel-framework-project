"""
Agent Framework Integration - Workflow Adapter

提供 WorkflowBuilder 的適配器，簡化工作流的創建和管理。
此適配器包裝 Agent Framework 的 WorkflowBuilder，提供更簡潔的 API。

設計原則:
    1. 簡化 API: 提供比原生 Builder 更直覺的介面
    2. 類型安全: 使用 dataclass 和類型提示
    3. 向後相容: 保持與現有系統的介面一致性
    4. 可擴展性: 支持自定義擴展

使用範例:
    from src.integrations.agent_framework.workflow import (
        WorkflowAdapter,
        WorkflowConfig,
    )

    # 創建配置
    config = WorkflowConfig(
        id="my-workflow",
        name="My Workflow",
        description="A sample workflow",
        max_iterations=100,
    )

    # 創建適配器
    adapter = WorkflowAdapter(config)

    # 添加執行器
    adapter.add_executor(my_executor)
    adapter.add_executor(my_other_executor)

    # 添加邊
    adapter.add_edge("executor1", "executor2")

    # 設置起始執行器
    adapter.set_start_executor("executor1")

    # 構建並運行
    result = await adapter.run(input_data)

Agent Framework API 對應:
    - WorkflowAdapter → WorkflowBuilder
    - WorkflowConfig → WorkflowBuilder 構造函數參數
    - add_edge() → WorkflowBuilder.add_edge()
    - add_fan_out_edges() → WorkflowBuilder.add_fan_out_edges()
    - add_fan_in_edges() → WorkflowBuilder.add_fan_in_edges()
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Union
import logging

from .base import BuilderAdapter
from .exceptions import WorkflowBuildError, ExecutionError

logger = logging.getLogger(__name__)


@dataclass
class WorkflowConfig:
    """
    工作流配置類。

    定義創建工作流所需的所有配置參數。

    Attributes:
        id: 工作流的唯一標識符
        name: 工作流的人類可讀名稱
        description: 工作流的描述
        max_iterations: 最大迭代次數（防止無限循環），默認 100
        enable_checkpointing: 是否啟用檢查點功能
        checkpoint_storage: 檢查點存儲實例（如果啟用）

    Example:
        config = WorkflowConfig(
            id="data-processing-workflow",
            name="Data Processing Pipeline",
            description="Process and transform data",
            max_iterations=50,
            enable_checkpointing=True,
        )
    """

    id: str
    name: str
    description: str = ""
    max_iterations: int = 100
    enable_checkpointing: bool = False
    checkpoint_storage: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """驗證配置。"""
        if not self.id:
            raise ValueError("Workflow ID cannot be empty")
        if not self.name:
            raise ValueError("Workflow name cannot be empty")
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")
        if self.enable_checkpointing and not self.checkpoint_storage:
            logger.warning(
                "Checkpointing enabled but no checkpoint_storage provided. "
                "Checkpoints will not be saved."
            )


@dataclass
class EdgeConfig:
    """
    邊配置類。

    定義工作流中執行器之間邊的配置。

    Attributes:
        source_id: 源執行器 ID
        target_id: 目標執行器 ID
        condition: 可選的條件函數，決定是否遍歷此邊
    """

    source_id: str
    target_id: str
    condition: Optional[Callable[[Any], bool]] = None


class WorkflowAdapter(BuilderAdapter):
    """
    WorkflowBuilder 適配器。

    包裝 Agent Framework 的 WorkflowBuilder，提供：
    - 簡化的 API 來創建和管理工作流
    - 類型安全的配置
    - 統一的錯誤處理
    - 可選的檢查點支持

    此適配器作為 IPA Platform 與 Agent Framework 之間的橋樑，
    隔離底層 API 的變更。

    Attributes:
        _config: 工作流配置
        _executors: 執行器字典 (id -> executor)
        _executor_factories: 執行器工廠字典 (name -> factory)
        _edges: 邊列表
        _start_executor_id: 起始執行器 ID

    Example:
        # 基本使用
        adapter = WorkflowAdapter(config)
        adapter.register_executor(lambda: MyExecutor(id="exec1"), "exec1")
        adapter.set_start_executor("exec1")
        workflow = adapter.build()

        # 使用上下文管理器
        async with WorkflowAdapter(config) as adapter:
            adapter.register_executor(lambda: MyExecutor(id="exec1"), "exec1")
            result = await adapter.run(input_data)
    """

    def __init__(self, config: WorkflowConfig):
        """
        初始化 WorkflowAdapter。

        Args:
            config: 工作流配置實例

        Raises:
            ValueError: 配置無效時
        """
        super().__init__(config={
            "id": config.id,
            "name": config.name,
            "description": config.description,
            "max_iterations": config.max_iterations,
            "enable_checkpointing": config.enable_checkpointing,
        })
        self._config = config
        self._executors: Dict[str, Any] = {}
        self._executor_factories: Dict[str, Callable] = {}
        self._edges: List[EdgeConfig] = []
        self._fan_out_edges: List[Dict[str, Any]] = []
        self._fan_in_edges: List[Dict[str, Any]] = []
        self._switch_case_edges: List[Dict[str, Any]] = []
        self._start_executor_id: Optional[str] = None
        self._logger = logging.getLogger(f"{__name__}.{config.id}")

    @property
    def workflow_id(self) -> str:
        """獲取工作流 ID。"""
        return self._config.id

    @property
    def workflow_name(self) -> str:
        """獲取工作流名稱。"""
        return self._config.name

    def register_executor(
        self,
        factory: Callable[[], Any],
        name: str,
    ) -> "WorkflowAdapter":
        """
        註冊執行器工廠函數。

        使用工廠函數進行延遲初始化，確保每次構建工作流時
        都創建新的執行器實例。

        Args:
            factory: 返回 Executor 實例的工廠函數
            name: 執行器的註冊名稱

        Returns:
            self，支持鏈式調用

        Raises:
            ValueError: 名稱已存在時

        Example:
            adapter.register_executor(
                lambda: MyExecutor(id="processor"),
                "processor"
            )
        """
        if name in self._executor_factories:
            raise ValueError(f"Executor factory '{name}' already registered")

        self._executor_factories[name] = factory
        self._logger.debug(f"Registered executor factory: {name}")
        return self

    def add_executor(self, executor: Any) -> "WorkflowAdapter":
        """
        直接添加執行器實例。

        注意：推薦使用 register_executor() 進行延遲初始化。
        直接添加的執行器會在所有工作流實例間共享。

        Args:
            executor: Executor 實例

        Returns:
            self，支持鏈式調用

        Raises:
            ValueError: 執行器 ID 已存在時
        """
        executor_id = executor.id
        if executor_id in self._executors:
            raise ValueError(f"Executor with ID '{executor_id}' already added")

        self._executors[executor_id] = executor
        self._logger.debug(f"Added executor: {executor_id}")
        return self

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        condition: Optional[Callable[[Any], bool]] = None,
    ) -> "WorkflowAdapter":
        """
        添加執行器之間的邊。

        Args:
            source_id: 源執行器的 ID 或註冊名稱
            target_id: 目標執行器的 ID 或註冊名稱
            condition: 可選的條件函數

        Returns:
            self，支持鏈式調用

        Example:
            # 無條件邊
            adapter.add_edge("processor1", "processor2")

            # 條件邊
            adapter.add_edge(
                "validator",
                "error_handler",
                condition=lambda msg: msg.get("has_error", False)
            )
        """
        self._edges.append(EdgeConfig(
            source_id=source_id,
            target_id=target_id,
            condition=condition,
        ))
        self._logger.debug(f"Added edge: {source_id} -> {target_id}")
        return self

    def add_fan_out_edges(
        self,
        source_id: str,
        target_ids: Sequence[str],
    ) -> "WorkflowAdapter":
        """
        添加扇出邊（一對多）。

        源執行器的輸出會廣播到所有目標執行器。

        Args:
            source_id: 源執行器的 ID 或註冊名稱
            target_ids: 目標執行器的 ID 或註冊名稱列表

        Returns:
            self，支持鏈式調用

        Example:
            # 將數據廣播到多個處理器
            adapter.add_fan_out_edges(
                "data_source",
                ["processor_a", "processor_b", "processor_c"]
            )
        """
        self._fan_out_edges.append({
            "source_id": source_id,
            "target_ids": list(target_ids),
        })
        self._logger.debug(
            f"Added fan-out edges: {source_id} -> {target_ids}"
        )
        return self

    def add_fan_in_edges(
        self,
        source_ids: Sequence[str],
        target_id: str,
    ) -> "WorkflowAdapter":
        """
        添加扇入邊（多對一）。

        多個源執行器的輸出會聚合後發送到目標執行器。
        目標執行器會收到所有源的輸出列表。

        Args:
            source_ids: 源執行器的 ID 或註冊名稱列表
            target_id: 目標執行器的 ID 或註冊名稱

        Returns:
            self，支持鏈式調用

        Example:
            # 聚合多個處理器的結果
            adapter.add_fan_in_edges(
                ["processor_a", "processor_b", "processor_c"],
                "aggregator"
            )
        """
        self._fan_in_edges.append({
            "source_ids": list(source_ids),
            "target_id": target_id,
        })
        self._logger.debug(
            f"Added fan-in edges: {source_ids} -> {target_id}"
        )
        return self

    def add_chain(self, executor_names: Sequence[str]) -> "WorkflowAdapter":
        """
        添加執行器鏈。

        依序連接多個執行器，形成處理管線。

        Args:
            executor_names: 執行器名稱列表（按順序）

        Returns:
            self，支持鏈式調用

        Raises:
            ValueError: 執行器數量少於 2 時

        Example:
            adapter.add_chain(["input", "process", "validate", "output"])
        """
        if len(executor_names) < 2:
            raise ValueError("Chain requires at least 2 executors")

        for i in range(len(executor_names) - 1):
            self.add_edge(executor_names[i], executor_names[i + 1])

        self._logger.debug(f"Added chain: {' -> '.join(executor_names)}")
        return self

    def set_start_executor(self, executor_id: str) -> "WorkflowAdapter":
        """
        設置起始執行器。

        Args:
            executor_id: 起始執行器的 ID 或註冊名稱

        Returns:
            self，支持鏈式調用

        Example:
            adapter.set_start_executor("input_handler")
        """
        if self._start_executor_id is not None:
            self._logger.warning(
                f"Overwriting start executor: {self._start_executor_id} -> {executor_id}"
            )
        self._start_executor_id = executor_id
        self._logger.debug(f"Set start executor: {executor_id}")
        return self

    def build(self):
        """
        構建工作流。

        創建 WorkflowBuilder，配置所有執行器和邊，
        然後構建最終的 Workflow 實例。

        Returns:
            構建完成的 Workflow 實例

        Raises:
            WorkflowBuildError: 構建失敗時（配置無效、驗證失敗等）

        Note:
            此方法會導入 agent_framework 模組。
            如果 agent_framework 不可用，會拋出 ImportError。
        """
        try:
            # 延遲導入以避免循環依賴
            from agent_framework import WorkflowBuilder

            self._logger.info(f"Building workflow: {self._config.id}")

            # 驗證起始執行器
            if not self._start_executor_id:
                raise WorkflowBuildError(
                    "Start executor not set",
                    workflow_id=self._config.id,
                )

            # 創建 builder
            builder = WorkflowBuilder(
                max_iterations=self._config.max_iterations,
                name=self._config.name,
                description=self._config.description,
            )

            # 註冊執行器工廠
            for name, factory in self._executor_factories.items():
                builder.register_executor(factory, name=name)

            # 添加直接的執行器（不推薦，但支持）
            # 注意：agent_framework 的 add_executor 已被棄用
            # 這裡我們通過工廠包裝來處理
            for executor_id, executor in self._executors.items():
                # 創建一個返回現有實例的工廠（不推薦）
                def make_factory(exec_instance):
                    return lambda: exec_instance
                builder.register_executor(make_factory(executor), name=executor_id)

            # 添加邊
            for edge in self._edges:
                builder.add_edge(
                    edge.source_id,
                    edge.target_id,
                    condition=edge.condition,
                )

            # 添加扇出邊
            for fan_out in self._fan_out_edges:
                builder.add_fan_out_edges(
                    fan_out["source_id"],
                    fan_out["target_ids"],
                )

            # 添加扇入邊
            for fan_in in self._fan_in_edges:
                builder.add_fan_in_edges(
                    fan_in["source_ids"],
                    fan_in["target_id"],
                )

            # 設置起始執行器
            builder.set_start_executor(self._start_executor_id)

            # 配置檢查點
            if self._config.enable_checkpointing and self._config.checkpoint_storage:
                builder.with_checkpointing(self._config.checkpoint_storage)

            # 構建工作流
            self._workflow = builder.build()
            self._builder = builder
            self._built = True

            self._logger.info(f"Workflow built successfully: {self._config.id}")
            return self._workflow

        except ImportError as e:
            raise WorkflowBuildError(
                f"Agent Framework not available: {e}",
                workflow_id=self._config.id,
                original_error=e,
            )
        except Exception as e:
            raise WorkflowBuildError(
                f"Failed to build workflow: {e}",
                workflow_id=self._config.id,
                original_error=e,
            )

    async def run(self, input_data: Any) -> Any:
        """
        執行工作流。

        如果工作流尚未構建，會先調用 build()。

        Args:
            input_data: 工作流輸入數據

        Returns:
            WorkflowRunResult 實例

        Raises:
            WorkflowBuildError: 構建失敗時
            ExecutionError: 執行失敗時
        """
        await self.ensure_initialized()

        if not self._workflow:
            self.build()

        try:
            self._logger.info(f"Running workflow: {self._config.id}")
            result = await self._workflow.run(input_data)
            self._logger.info(f"Workflow completed: {self._config.id}")
            return result
        except Exception as e:
            raise ExecutionError(
                f"Workflow execution failed: {e}",
                workflow_id=self._config.id,
                original_error=e,
            )

    async def run_stream(self, input_data: Any):
        """
        以串流模式執行工作流。

        Args:
            input_data: 工作流輸入數據

        Yields:
            工作流事件

        Raises:
            WorkflowBuildError: 構建失敗時
            ExecutionError: 執行失敗時
        """
        await self.ensure_initialized()

        if not self._workflow:
            self.build()

        try:
            self._logger.info(f"Running workflow (stream): {self._config.id}")
            async for event in self._workflow.run_stream(input_data):
                yield event
            self._logger.info(f"Workflow stream completed: {self._config.id}")
        except Exception as e:
            raise ExecutionError(
                f"Workflow stream execution failed: {e}",
                workflow_id=self._config.id,
                original_error=e,
            )

    def get_executor_ids(self) -> List[str]:
        """獲取所有已註冊的執行器 ID。"""
        return list(self._executor_factories.keys()) + list(self._executors.keys())

    def get_edge_count(self) -> int:
        """獲取邊的總數。"""
        return (
            len(self._edges) +
            sum(len(fo["target_ids"]) for fo in self._fan_out_edges) +
            sum(len(fi["source_ids"]) for fi in self._fan_in_edges)
        )

    def __repr__(self) -> str:
        return (
            f"WorkflowAdapter("
            f"id={self._config.id!r}, "
            f"name={self._config.name!r}, "
            f"executors={len(self.get_executor_ids())}, "
            f"edges={self.get_edge_count()}, "
            f"built={self._built})"
        )
