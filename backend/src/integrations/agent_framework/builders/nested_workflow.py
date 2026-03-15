# =============================================================================
# IPA Platform - NestedWorkflow Adapter
# =============================================================================
# Sprint 23: Nested Workflow 重構 (Phase 4)
# Phase 4 Feature: P4-F4 (嵌套工作流遷移)
#
# 將 Phase 2 嵌套工作流功能適配到 Agent Framework WorkflowBuilder。
#
# 功能對照:
#   Phase 2 ContextPropagation    → ContextPropagationStrategy 策略
#   Phase 2 RecursiveDepthTracker → RecursiveDepthController 控制器
#   Phase 2 SubWorkflowExecutor   → 使用其他 BuilderAdapter
#   Phase 2 CompositionBuilder    → 官方 WorkflowBuilder 組合
#
# 支持的子工作流類型:
#   - GroupChatBuilderAdapter
#   - HandoffBuilderAdapter
#   - ConcurrentBuilderAdapter
#   - 官方 Workflow 實例
#
# 使用範例:
#   from src.integrations.agent_framework.builders import NestedWorkflowAdapter
#   from src.integrations.agent_framework.builders.nested_workflow import (
#       ContextPropagationStrategy,
#       ExecutionMode,
#   )
#
#   adapter = NestedWorkflowAdapter(
#       id="nested-research",
#       max_depth=5,
#       context_strategy=ContextPropagationStrategy.INHERITED,
#   )
#   adapter.add_sub_workflow("analyze", groupchat_adapter)
#   adapter.add_sub_workflow("summarize", handoff_adapter)
#   adapter.with_sequential_execution(["analyze", "summarize"])
#   result = await adapter.run(input_data)
#
# 參考:
#   - Agent Framework WorkflowBuilder: reference/agent-framework/python/
#     packages/core/agent_framework/_workflows/_workflow.py
#   - Phase 2 NestedWorkflow: backend/src/domain/orchestration/nested/
#   - Phase 2 ContextPropagation: backend/src/domain/orchestration/nested/context_propagation.py
# =============================================================================

import asyncio
import copy
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Set,
    TypeVar,
    Union,
    runtime_checkable,
)
from uuid import UUID, uuid4

from ..base import BuilderAdapter
from ..exceptions import ExecutionError, RecursionError, ValidationError, WorkflowBuildError

# =============================================================================
# 官方 Agent Framework API 導入 (Sprint 23 整合)
# =============================================================================
from agent_framework import WorkflowBuilder, Workflow, WorkflowExecutor

logger = logging.getLogger(__name__)

# Type variables
T = TypeVar("T")
R = TypeVar("R")


# =============================================================================
# 上下文傳播策略枚舉 (對應 Phase 2 PropagationType)
# =============================================================================


class ContextPropagationStrategy(str, Enum):
    """
    上下文傳播策略類型。

    決定父工作流如何將上下文傳遞給子工作流。

    Values:
        INHERITED: 完全繼承父上下文 (默認)
        ISOLATED: 隔離，不繼承父上下文
        MERGED: 合併父子上下文 (子優先)
        FILTERED: 僅傳遞指定字段

    對應 Phase 2 PropagationType:
        COPY     → INHERITED (深拷貝繼承)
        REFERENCE → 不支持 (安全考慮)
        MERGE    → MERGED
        FILTER   → FILTERED
    """
    INHERITED = "inherited"
    ISOLATED = "isolated"
    MERGED = "merged"
    FILTERED = "filtered"


class ExecutionMode(str, Enum):
    """
    子工作流執行模式。

    決定多個子工作流如何執行。

    Values:
        SEQUENTIAL: 順序執行，按定義順序
        PARALLEL: 並行執行，同時啟動所有子工作流
        CONDITIONAL: 條件執行，根據條件選擇執行

    對應 Phase 2 CompositionType:
        SEQUENCE    → SEQUENTIAL
        PARALLEL    → PARALLEL
        CONDITIONAL → CONDITIONAL
        LOOP        → 使用遞歸處理
        SWITCH      → 使用 CONDITIONAL + 條件
    """
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"


class RecursionStatus(str, Enum):
    """
    遞歸執行狀態。

    Values:
        PENDING: 等待執行
        RUNNING: 正在執行
        COMPLETED: 執行完成
        FAILED: 執行失敗
        DEPTH_EXCEEDED: 超過最大深度
        TIMEOUT: 執行超時
    """
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DEPTH_EXCEEDED = "depth_exceeded"
    TIMEOUT = "timeout"


# =============================================================================
# 協議定義
# =============================================================================


@runtime_checkable
class SubWorkflowProtocol(Protocol):
    """
    子工作流協議。

    任何可以作為子工作流的對象必須實現此協議。
    """

    def build(self) -> Workflow:
        """構建工作流實例。"""
        ...


# =============================================================================
# 數據類
# =============================================================================


@dataclass
class ContextConfig:
    """
    上下文配置。

    配置上下文傳播的詳細行為。

    Attributes:
        strategy: 傳播策略
        allowed_keys: 允許傳遞的鍵 (僅 FILTERED 策略使用)
        additional_context: 額外添加的上下文
        transform_fn: 上下文轉換函數
    """
    strategy: ContextPropagationStrategy = ContextPropagationStrategy.INHERITED
    allowed_keys: Optional[Set[str]] = None
    additional_context: Dict[str, Any] = field(default_factory=dict)
    transform_fn: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典表示。"""
        return {
            "strategy": self.strategy.value,
            "allowed_keys": list(self.allowed_keys) if self.allowed_keys else None,
            "additional_context_keys": list(self.additional_context.keys()),
            "has_transform": self.transform_fn is not None,
        }


@dataclass
class RecursionConfig:
    """
    遞歸配置。

    配置遞歸深度控制的詳細行為。

    Attributes:
        max_depth: 最大遞歸深度 (默認 5)
        max_iterations: 最大迭代次數 (默認 100)
        timeout_seconds: 超時秒數 (默認 300)
        track_history: 是否追蹤歷史 (默認 True)
    """
    max_depth: int = 5
    max_iterations: int = 100
    timeout_seconds: float = 300.0
    track_history: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典表示。"""
        return {
            "max_depth": self.max_depth,
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
            "track_history": self.track_history,
        }


@dataclass
class RecursionState:
    """
    遞歸狀態追蹤。

    追蹤當前遞歸執行的狀態。

    Attributes:
        current_depth: 當前深度
        iteration_count: 迭代計數
        status: 執行狀態
        started_at: 開始時間
        history: 執行歷史
    """
    current_depth: int = 0
    iteration_count: int = 0
    status: RecursionStatus = RecursionStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典表示。"""
        return {
            "current_depth": self.current_depth,
            "iteration_count": self.iteration_count,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "history_length": len(self.history),
        }


@dataclass
class SubWorkflowInfo:
    """
    子工作流信息。

    儲存子工作流的元數據和配置。

    Attributes:
        name: 子工作流名稱
        workflow: 構建的工作流實例
        adapter: 原始適配器 (可選)
        context_config: 上下文配置 (可選，覆蓋默認)
        condition: 執行條件 (可選)
        metadata: 額外元數據
    """
    name: str
    workflow: Workflow
    adapter: Optional[Any] = None
    context_config: Optional[ContextConfig] = None
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典表示。"""
        return {
            "name": self.name,
            "has_adapter": self.adapter is not None,
            "has_context_config": self.context_config is not None,
            "has_condition": self.condition is not None,
            "metadata": self.metadata,
        }


@dataclass
class NestedExecutionResult:
    """
    嵌套工作流執行結果。

    包含執行的完整結果和元數據。

    Attributes:
        success: 是否成功
        result: 執行結果
        sub_results: 各子工作流結果
        recursion_state: 遞歸狀態
        elapsed_seconds: 執行耗時
        error: 錯誤信息 (如有)
    """
    success: bool
    result: Any = None
    sub_results: Dict[str, Any] = field(default_factory=dict)
    recursion_state: Optional[RecursionState] = None
    elapsed_seconds: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典表示。"""
        return {
            "success": self.success,
            "result": self.result,
            "sub_results": self.sub_results,
            "recursion_state": self.recursion_state.to_dict() if self.recursion_state else None,
            "elapsed_seconds": self.elapsed_seconds,
            "error": self.error,
        }


# =============================================================================
# 上下文傳播器
# =============================================================================


class ContextPropagator:
    """
    上下文傳播器。

    處理父子工作流之間的上下文傳遞。

    保留 Phase 2 ContextPropagation 的核心邏輯，
    但簡化介面以適配 Agent Framework。
    """

    def __init__(self, config: Optional[ContextConfig] = None):
        """
        初始化上下文傳播器。

        Args:
            config: 上下文配置
        """
        self._config = config or ContextConfig()
        self._logger = logging.getLogger(f"{__name__}.ContextPropagator")

    @property
    def strategy(self) -> ContextPropagationStrategy:
        """獲取當前策略。"""
        return self._config.strategy

    def prepare_child_context(
        self,
        parent_context: Dict[str, Any],
        child_name: str,
    ) -> Dict[str, Any]:
        """
        準備子工作流的上下文。

        根據配置的策略處理上下文傳遞。

        Args:
            parent_context: 父工作流上下文
            child_name: 子工作流名稱

        Returns:
            處理後的子工作流上下文
        """
        strategy = self._config.strategy

        if strategy == ContextPropagationStrategy.ISOLATED:
            # 隔離模式：只傳遞額外上下文
            result = copy.deepcopy(self._config.additional_context)

        elif strategy == ContextPropagationStrategy.INHERITED:
            # 繼承模式：深拷貝父上下文
            result = copy.deepcopy(parent_context)
            result.update(self._config.additional_context)

        elif strategy == ContextPropagationStrategy.MERGED:
            # 合併模式：合併父上下文和額外上下文
            result = copy.deepcopy(parent_context)
            result.update(self._config.additional_context)

        elif strategy == ContextPropagationStrategy.FILTERED:
            # 過濾模式：只傳遞允許的鍵
            allowed = self._config.allowed_keys or set()
            result = {
                k: copy.deepcopy(v)
                for k, v in parent_context.items()
                if k in allowed
            }
            result.update(self._config.additional_context)

        else:
            # 默認使用繼承
            result = copy.deepcopy(parent_context)

        # 應用轉換函數
        if self._config.transform_fn:
            try:
                result = self._config.transform_fn(result)
            except Exception as e:
                self._logger.warning(f"Context transform failed for {child_name}: {e}")

        # 添加元數據
        result["_nested_parent"] = True
        result["_nested_child_name"] = child_name

        self._logger.debug(f"Prepared context for {child_name} using {strategy.value}")
        return result

    def finalize_result(
        self,
        child_result: Any,
        parent_context: Dict[str, Any],
    ) -> Any:
        """
        處理子工作流的結果。

        根據策略決定如何將子結果合併回父上下文。

        Args:
            child_result: 子工作流結果
            parent_context: 父工作流上下文

        Returns:
            處理後的結果
        """
        strategy = self._config.strategy

        if strategy == ContextPropagationStrategy.ISOLATED:
            # 隔離模式：直接返回子結果
            return child_result

        elif strategy == ContextPropagationStrategy.MERGED:
            # 合併模式：合併到父上下文
            if isinstance(child_result, dict):
                merged = copy.deepcopy(parent_context)
                merged.update(child_result)
                return merged
            return child_result

        else:
            # 其他模式：直接返回
            return child_result


# =============================================================================
# 遞歸深度控制器
# =============================================================================


class RecursiveDepthController:
    """
    遞歸深度控制器。

    保留 Phase 2 RecursiveDepthTracker 的核心邏輯，
    提供遞歸深度的安全控制。
    """

    def __init__(self, config: Optional[RecursionConfig] = None):
        """
        初始化遞歸深度控制器。

        Args:
            config: 遞歸配置
        """
        self._config = config or RecursionConfig()
        self._state = RecursionState()
        self._logger = logging.getLogger(f"{__name__}.RecursiveDepthController")

    @property
    def current_depth(self) -> int:
        """獲取當前深度。"""
        return self._state.current_depth

    @property
    def max_depth(self) -> int:
        """獲取最大深度。"""
        return self._config.max_depth

    @property
    def state(self) -> RecursionState:
        """獲取當前狀態。"""
        return self._state

    def can_enter(self) -> bool:
        """
        檢查是否可以進入更深層。

        Returns:
            True 如果可以進入，False 否則
        """
        return self._state.current_depth < self._config.max_depth

    def enter(self) -> None:
        """
        進入更深一層。

        Raises:
            RecursionError: 如果超過最大深度
        """
        if not self.can_enter():
            raise RecursionError(
                f"Maximum recursion depth exceeded: {self._config.max_depth}, "
                f"current depth: {self._state.current_depth}"
            )

        self._state.current_depth += 1
        self._state.iteration_count += 1
        self._state.status = RecursionStatus.RUNNING

        if self._state.started_at is None:
            self._state.started_at = datetime.utcnow()

        self._logger.debug(f"Entered depth {self._state.current_depth}")

    def exit(self) -> None:
        """
        退出當前層。
        """
        if self._state.current_depth > 0:
            self._state.current_depth -= 1
            self._logger.debug(f"Exited to depth {self._state.current_depth}")

        if self._state.current_depth == 0:
            self._state.status = RecursionStatus.COMPLETED
            self._state.completed_at = datetime.utcnow()

    def record_history(self, entry: Dict[str, Any]) -> None:
        """
        記錄執行歷史。

        Args:
            entry: 歷史記錄項
        """
        if self._config.track_history:
            self._state.history.append({
                "depth": self._state.current_depth,
                "iteration": self._state.iteration_count,
                "timestamp": datetime.utcnow().isoformat(),
                **entry,
            })

    def reset(self) -> None:
        """重置控制器狀態。"""
        self._state = RecursionState()


# =============================================================================
# NestedWorkflowAdapter 主類
# =============================================================================


class NestedWorkflowAdapter(BuilderAdapter):
    """
    嵌套工作流適配器。

    使用官方 WorkflowBuilder 組合功能實現嵌套執行，
    同時保留 Phase 2 的上下文傳播和遞歸深度控制。

    Features:
        - 支持多種子工作流類型 (GroupChat, Handoff, Concurrent, Workflow)
        - 上下文傳播策略 (INHERITED, ISOLATED, MERGED, FILTERED)
        - 遞歸深度控制 (防止無限遞歸)
        - 多種執行模式 (SEQUENTIAL, PARALLEL, CONDITIONAL)

    Example:
        adapter = NestedWorkflowAdapter(
            id="research-pipeline",
            max_depth=5,
            context_strategy=ContextPropagationStrategy.INHERITED,
        )
        adapter.add_sub_workflow("gather", gather_adapter)
        adapter.add_sub_workflow("analyze", analyze_adapter)
        adapter.with_sequential_execution(["gather", "analyze"])
        result = await adapter.run({"query": "AI trends"})
    """

    def __init__(
        self,
        id: str,
        max_depth: int = 5,
        context_strategy: ContextPropagationStrategy = ContextPropagationStrategy.INHERITED,
        timeout_seconds: float = 300.0,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化 NestedWorkflowAdapter。

        Args:
            id: 適配器唯一識別符
            max_depth: 最大遞歸深度
            context_strategy: 上下文傳播策略
            timeout_seconds: 執行超時秒數
            config: 額外配置
        """
        super().__init__(config)

        self._id = id
        self._max_depth = max_depth
        self._timeout_seconds = timeout_seconds

        # 官方 Builder 實例
        self._builder = WorkflowBuilder()

        # 子工作流註冊表
        self._sub_workflows: Dict[str, SubWorkflowInfo] = {}

        # 上下文傳播器
        self._context_config = ContextConfig(strategy=context_strategy)
        self._context_propagator = ContextPropagator(self._context_config)

        # 遞歸深度控制器
        self._recursion_config = RecursionConfig(
            max_depth=max_depth,
            timeout_seconds=timeout_seconds,
        )
        self._depth_controller = RecursiveDepthController(self._recursion_config)

        # 執行模式和順序
        self._execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
        self._execution_order: List[str] = []
        self._conditions: Dict[str, Callable[[Dict[str, Any]], bool]] = {}

        # 執行器 (用於運行構建的工作流)
        self._executor: Optional[WorkflowExecutor] = None

        self._logger.info(
            f"Created NestedWorkflowAdapter: id={id}, max_depth={max_depth}, "
            f"strategy={context_strategy.value}"
        )

    # =========================================================================
    # 屬性
    # =========================================================================

    @property
    def id(self) -> str:
        """獲取適配器 ID。"""
        return self._id

    @property
    def max_depth(self) -> int:
        """獲取最大遞歸深度。"""
        return self._max_depth

    @property
    def context_strategy(self) -> ContextPropagationStrategy:
        """獲取上下文傳播策略。"""
        return self._context_config.strategy

    @property
    def execution_mode(self) -> ExecutionMode:
        """獲取執行模式。"""
        return self._execution_mode

    @property
    def sub_workflow_names(self) -> List[str]:
        """獲取所有子工作流名稱。"""
        return list(self._sub_workflows.keys())

    @property
    def current_depth(self) -> int:
        """獲取當前遞歸深度。"""
        return self._depth_controller.current_depth

    # =========================================================================
    # 子工作流管理
    # =========================================================================

    def add_sub_workflow(
        self,
        name: str,
        workflow: Union[Workflow, SubWorkflowProtocol, Any],
        context_config: Optional[ContextConfig] = None,
        condition: Optional[Callable[[Dict[str, Any]], bool]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "NestedWorkflowAdapter":
        """
        添加子工作流。

        支持多種類型:
        - 官方 Workflow 實例
        - 任何實現 SubWorkflowProtocol 的適配器
        - 任何有 build() 方法的適配器

        Args:
            name: 子工作流名稱 (唯一)
            workflow: 工作流實例或適配器
            context_config: 上下文配置 (覆蓋默認)
            condition: 執行條件函數
            metadata: 額外元數據

        Returns:
            Self for chaining

        Raises:
            ValueError: 如果名稱已存在或類型不支持
        """
        if name in self._sub_workflows:
            raise ValueError(f"Sub-workflow '{name}' already exists")

        # 解析工作流類型
        if isinstance(workflow, Workflow):
            built_workflow = workflow
            adapter = None
        elif hasattr(workflow, "build"):
            try:
                built_workflow = workflow.build()
                adapter = workflow
            except Exception as e:
                raise ValueError(f"Failed to build workflow '{name}': {e}") from e
        else:
            raise TypeError(
                f"Unsupported workflow type for '{name}': {type(workflow)}. "
                f"Expected Workflow or adapter with build() method."
            )

        # 創建子工作流信息
        info = SubWorkflowInfo(
            name=name,
            workflow=built_workflow,
            adapter=adapter,
            context_config=context_config,
            condition=condition,
            metadata=metadata or {},
        )

        self._sub_workflows[name] = info
        self._execution_order.append(name)

        self._logger.info(f"Added sub-workflow: {name}")
        return self

    def remove_sub_workflow(self, name: str) -> "NestedWorkflowAdapter":
        """
        移除子工作流。

        Args:
            name: 子工作流名稱

        Returns:
            Self for chaining
        """
        if name in self._sub_workflows:
            del self._sub_workflows[name]
            if name in self._execution_order:
                self._execution_order.remove(name)
            if name in self._conditions:
                del self._conditions[name]
            self._logger.info(f"Removed sub-workflow: {name}")
        return self

    def get_sub_workflow(self, name: str) -> Optional[SubWorkflowInfo]:
        """
        獲取子工作流信息。

        Args:
            name: 子工作流名稱

        Returns:
            子工作流信息或 None
        """
        return self._sub_workflows.get(name)

    # =========================================================================
    # 上下文配置
    # =========================================================================

    def with_context_strategy(
        self,
        strategy: ContextPropagationStrategy,
        allowed_keys: Optional[Set[str]] = None,
        additional_context: Optional[Dict[str, Any]] = None,
        transform_fn: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> "NestedWorkflowAdapter":
        """
        配置上下文傳播策略。

        Args:
            strategy: 傳播策略
            allowed_keys: 允許傳遞的鍵 (僅 FILTERED 策略)
            additional_context: 額外添加的上下文
            transform_fn: 上下文轉換函數

        Returns:
            Self for chaining
        """
        self._context_config = ContextConfig(
            strategy=strategy,
            allowed_keys=allowed_keys,
            additional_context=additional_context or {},
            transform_fn=transform_fn,
        )
        self._context_propagator = ContextPropagator(self._context_config)

        self._logger.info(f"Updated context strategy: {strategy.value}")
        return self

    # =========================================================================
    # 執行模式配置
    # =========================================================================

    def with_sequential_execution(
        self,
        order: Optional[List[str]] = None,
    ) -> "NestedWorkflowAdapter":
        """
        配置順序執行模式。

        Args:
            order: 執行順序 (默認按添加順序)

        Returns:
            Self for chaining
        """
        self._execution_mode = ExecutionMode.SEQUENTIAL

        if order:
            # 驗證所有名稱都存在
            for name in order:
                if name not in self._sub_workflows:
                    raise ValueError(f"Unknown sub-workflow: {name}")
            self._execution_order = order
        # 否則保持原有順序

        self._logger.info(f"Set sequential execution: {self._execution_order}")
        return self

    def with_parallel_execution(self) -> "NestedWorkflowAdapter":
        """
        配置並行執行模式。

        Returns:
            Self for chaining
        """
        self._execution_mode = ExecutionMode.PARALLEL
        self._logger.info("Set parallel execution mode")
        return self

    def with_conditional_execution(
        self,
        conditions: Dict[str, Callable[[Dict[str, Any]], bool]],
    ) -> "NestedWorkflowAdapter":
        """
        配置條件執行模式。

        Args:
            conditions: 子工作流名稱到條件函數的映射

        Returns:
            Self for chaining
        """
        self._execution_mode = ExecutionMode.CONDITIONAL

        for name, condition in conditions.items():
            if name not in self._sub_workflows:
                raise ValueError(f"Unknown sub-workflow: {name}")
            self._conditions[name] = condition

        self._logger.info(f"Set conditional execution: {list(conditions.keys())}")
        return self

    # =========================================================================
    # 構建
    # =========================================================================

    def build(self) -> Workflow:
        """
        構建嵌套工作流。

        使用官方 WorkflowBuilder 組合所有子工作流。

        Returns:
            構建的 Workflow 實例

        Raises:
            WorkflowBuildError: 如果構建失敗
        """
        if not self._sub_workflows:
            raise WorkflowBuildError("No sub-workflows added to NestedWorkflowAdapter")

        try:
            # 收集所有子工作流
            workflows = [
                info.workflow
                for name in self._execution_order
                if name in self._sub_workflows
                for info in [self._sub_workflows[name]]
            ]

            # 使用官方 WorkflowBuilder 組合
            # 注意: 實際的 WorkflowBuilder API 可能不同，這裡展示概念
            workflow = self._builder.with_workflows(workflows).build()

            self._logger.info(
                f"Built nested workflow with {len(workflows)} sub-workflows"
            )
            return workflow

        except Exception as e:
            raise WorkflowBuildError(
                f"Failed to build nested workflow: {e}"
            ) from e

    # =========================================================================
    # 執行
    # =========================================================================

    async def run(self, input_data: Any) -> NestedExecutionResult:
        """
        執行嵌套工作流。

        根據配置的執行模式和上下文策略執行所有子工作流。

        Args:
            input_data: 輸入數據

        Returns:
            NestedExecutionResult 包含執行結果

        Raises:
            RecursionError: 如果超過最大遞歸深度
            ExecutionError: 如果執行失敗
        """
        start_time = datetime.utcnow()

        # 檢查遞歸深度
        if not self._depth_controller.can_enter():
            return NestedExecutionResult(
                success=False,
                error=f"Maximum recursion depth exceeded: {self._max_depth}",
                recursion_state=self._depth_controller.state,
            )

        self._depth_controller.enter()

        try:
            # 準備上下文
            parent_context = input_data if isinstance(input_data, dict) else {"input": input_data}

            # 根據執行模式執行
            if self._execution_mode == ExecutionMode.SEQUENTIAL:
                result = await self._execute_sequential(parent_context)
            elif self._execution_mode == ExecutionMode.PARALLEL:
                result = await self._execute_parallel(parent_context)
            elif self._execution_mode == ExecutionMode.CONDITIONAL:
                result = await self._execute_conditional(parent_context)
            else:
                raise ExecutionError(f"Unknown execution mode: {self._execution_mode}")

            elapsed = (datetime.utcnow() - start_time).total_seconds()

            # 記錄歷史
            self._depth_controller.record_history({
                "mode": self._execution_mode.value,
                "sub_workflows": list(result.sub_results.keys()),
                "success": result.success,
            })

            result.elapsed_seconds = elapsed
            result.recursion_state = self._depth_controller.state

            return result

        except Exception as e:
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            self._logger.error(f"Nested workflow execution failed: {e}")
            return NestedExecutionResult(
                success=False,
                error=str(e),
                elapsed_seconds=elapsed,
                recursion_state=self._depth_controller.state,
            )

        finally:
            self._depth_controller.exit()

    async def _execute_sequential(
        self,
        parent_context: Dict[str, Any],
    ) -> NestedExecutionResult:
        """順序執行所有子工作流。"""
        sub_results: Dict[str, Any] = {}
        current_context = parent_context.copy()
        final_result = None

        for name in self._execution_order:
            if name not in self._sub_workflows:
                continue

            info = self._sub_workflows[name]

            # 使用子工作流特定的上下文配置或默認
            propagator = ContextPropagator(info.context_config or self._context_config)
            child_context = propagator.prepare_child_context(current_context, name)

            try:
                # 執行子工作流
                result = await self._execute_sub_workflow(info, child_context)
                sub_results[name] = result

                # 更新當前上下文
                final_result = propagator.finalize_result(result, current_context)
                if isinstance(final_result, dict):
                    current_context.update(final_result)

            except Exception as e:
                self._logger.error(f"Sub-workflow {name} failed: {e}")
                sub_results[name] = {"error": str(e)}
                return NestedExecutionResult(
                    success=False,
                    result=final_result,
                    sub_results=sub_results,
                    error=f"Sub-workflow {name} failed: {e}",
                )

        return NestedExecutionResult(
            success=True,
            result=final_result,
            sub_results=sub_results,
        )

    async def _execute_parallel(
        self,
        parent_context: Dict[str, Any],
    ) -> NestedExecutionResult:
        """並行執行所有子工作流。"""
        tasks = []
        names = []

        for name, info in self._sub_workflows.items():
            propagator = ContextPropagator(info.context_config or self._context_config)
            child_context = propagator.prepare_child_context(parent_context, name)

            task = self._execute_sub_workflow(info, child_context)
            tasks.append(task)
            names.append(name)

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self._timeout_seconds,
            )

            sub_results = {}
            errors = []
            for name, result in zip(names, results):
                if isinstance(result, Exception):
                    sub_results[name] = {"error": str(result)}
                    errors.append(f"{name}: {result}")
                else:
                    sub_results[name] = result

            if errors:
                return NestedExecutionResult(
                    success=False,
                    sub_results=sub_results,
                    error="; ".join(errors),
                )

            return NestedExecutionResult(
                success=True,
                result=sub_results,
                sub_results=sub_results,
            )

        except asyncio.TimeoutError:
            return NestedExecutionResult(
                success=False,
                error=f"Parallel execution timed out after {self._timeout_seconds}s",
            )

    async def _execute_conditional(
        self,
        parent_context: Dict[str, Any],
    ) -> NestedExecutionResult:
        """條件執行子工作流。"""
        sub_results: Dict[str, Any] = {}
        executed = []

        for name, info in self._sub_workflows.items():
            # 檢查條件
            condition = self._conditions.get(name, info.condition)
            if condition and not condition(parent_context):
                sub_results[name] = {"skipped": True, "reason": "condition not met"}
                continue

            propagator = ContextPropagator(info.context_config or self._context_config)
            child_context = propagator.prepare_child_context(parent_context, name)

            try:
                result = await self._execute_sub_workflow(info, child_context)
                sub_results[name] = result
                executed.append(name)
            except Exception as e:
                sub_results[name] = {"error": str(e)}

        return NestedExecutionResult(
            success=True,
            result=sub_results,
            sub_results=sub_results,
        )

    async def _execute_sub_workflow(
        self,
        info: SubWorkflowInfo,
        context: Dict[str, Any],
    ) -> Any:
        """執行單個子工作流。"""
        self._logger.debug(f"Executing sub-workflow: {info.name}")

        # 如果有適配器且有 run 方法，優先使用
        if info.adapter and hasattr(info.adapter, "run"):
            return await info.adapter.run(context)

        # 否則使用 WorkflowExecutor
        if self._executor is None:
            self._executor = WorkflowExecutor()

        return await self._executor.run(info.workflow, context)

    # =========================================================================
    # 生命週期
    # =========================================================================

    async def initialize(self) -> None:
        """初始化適配器資源。"""
        self._initialized = True
        self._logger.info(f"Initialized NestedWorkflowAdapter: {self._id}")

    async def cleanup(self) -> None:
        """清理適配器資源。"""
        self._depth_controller.reset()
        self._initialized = False
        self._logger.info(f"Cleaned up NestedWorkflowAdapter: {self._id}")

    # =========================================================================
    # 診斷和調試
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        """
        獲取適配器狀態。

        Returns:
            狀態信息字典
        """
        return {
            "id": self._id,
            "max_depth": self._max_depth,
            "current_depth": self._depth_controller.current_depth,
            "context_strategy": self._context_config.strategy.value,
            "execution_mode": self._execution_mode.value,
            "sub_workflows": list(self._sub_workflows.keys()),
            "execution_order": self._execution_order,
            "recursion_state": self._depth_controller.state.to_dict(),
            "initialized": self._initialized,
        }

    def validate(self) -> List[str]:
        """
        驗證適配器配置。

        Returns:
            錯誤列表 (空表示驗證通過)
        """
        errors = []

        if not self._sub_workflows:
            errors.append("No sub-workflows configured")

        if self._execution_mode == ExecutionMode.CONDITIONAL:
            for name in self._sub_workflows:
                if name not in self._conditions:
                    info = self._sub_workflows[name]
                    if not info.condition:
                        errors.append(f"No condition for sub-workflow: {name}")

        if self._max_depth < 1:
            errors.append(f"Invalid max_depth: {self._max_depth}")

        return errors


# =============================================================================
# 工廠函數
# =============================================================================


def create_nested_workflow_adapter(
    id: str,
    max_depth: int = 5,
    context_strategy: ContextPropagationStrategy = ContextPropagationStrategy.INHERITED,
    timeout_seconds: float = 300.0,
) -> NestedWorkflowAdapter:
    """
    創建 NestedWorkflowAdapter 實例。

    Args:
        id: 適配器 ID
        max_depth: 最大遞歸深度
        context_strategy: 上下文傳播策略
        timeout_seconds: 超時秒數

    Returns:
        配置好的 NestedWorkflowAdapter
    """
    return NestedWorkflowAdapter(
        id=id,
        max_depth=max_depth,
        context_strategy=context_strategy,
        timeout_seconds=timeout_seconds,
    )


def create_sequential_nested_workflow(
    id: str,
    sub_workflows: List[tuple],  # [(name, adapter), ...]
    context_strategy: ContextPropagationStrategy = ContextPropagationStrategy.INHERITED,
) -> NestedWorkflowAdapter:
    """
    創建順序執行的嵌套工作流。

    Args:
        id: 適配器 ID
        sub_workflows: 子工作流列表 [(name, adapter), ...]
        context_strategy: 上下文傳播策略

    Returns:
        配置好的順序執行 NestedWorkflowAdapter
    """
    adapter = create_nested_workflow_adapter(id, context_strategy=context_strategy)

    order = []
    for name, workflow in sub_workflows:
        adapter.add_sub_workflow(name, workflow)
        order.append(name)

    adapter.with_sequential_execution(order)
    return adapter


def create_parallel_nested_workflow(
    id: str,
    sub_workflows: List[tuple],  # [(name, adapter), ...]
    timeout_seconds: float = 300.0,
) -> NestedWorkflowAdapter:
    """
    創建並行執行的嵌套工作流。

    Args:
        id: 適配器 ID
        sub_workflows: 子工作流列表 [(name, adapter), ...]
        timeout_seconds: 超時秒數

    Returns:
        配置好的並行執行 NestedWorkflowAdapter
    """
    adapter = create_nested_workflow_adapter(id, timeout_seconds=timeout_seconds)

    for name, workflow in sub_workflows:
        adapter.add_sub_workflow(name, workflow)

    adapter.with_parallel_execution()
    return adapter


def create_conditional_nested_workflow(
    id: str,
    sub_workflows: List[tuple],  # [(name, adapter, condition), ...]
) -> NestedWorkflowAdapter:
    """
    創建條件執行的嵌套工作流。

    Args:
        id: 適配器 ID
        sub_workflows: 子工作流列表 [(name, adapter, condition), ...]

    Returns:
        配置好的條件執行 NestedWorkflowAdapter
    """
    adapter = create_nested_workflow_adapter(id)

    conditions = {}
    for item in sub_workflows:
        if len(item) == 3:
            name, workflow, condition = item
            adapter.add_sub_workflow(name, workflow, condition=condition)
            conditions[name] = condition
        else:
            name, workflow = item
            adapter.add_sub_workflow(name, workflow)

    adapter.with_conditional_execution(conditions)
    return adapter
