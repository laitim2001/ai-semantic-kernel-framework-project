# =============================================================================
# IPA Platform - PlanningAdapter
# =============================================================================
# Sprint 24: S24-2 PlanningAdapter (10 points)
#
# 動態規劃適配器，整合官方 MagenticBuilder 與 Phase 2 擴展功能。
#
# 架構:
#   PlanningAdapter
#   ├── _magentic_builder: MagenticBuilder    # 官方 API - 規劃核心
#   ├── _task_decomposer: TaskDecomposer      # Phase 2 擴展 - 任務分解
#   ├── _decision_engine: DecisionEngine      # Phase 2 擴展 - 決策引擎
#   └── Methods: with_task_decomposition(), with_decision_engine(), build(), run()
#
# 使用範例:
#   adapter = PlanningAdapter("my-planner")
#   adapter.with_task_decomposition(DecompositionStrategy.HYBRID)
#   adapter.with_decision_engine(rules=[...])
#   result = await adapter.run("Create a user authentication system")
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, Union
from uuid import UUID, uuid4
import asyncio
import logging

# 官方 Agent Framework API
from agent_framework import MagenticBuilder, Workflow

# Phase 2 擴展功能 (內部使用，對外通過 PlanningAdapter 暴露)
from src.domain.orchestration.planning.task_decomposer import (
    TaskDecomposer,
    DecompositionStrategy as DomainDecompositionStrategy,
    DecompositionResult,
    SubTask,
    TaskStatus,
    TaskPriority,
)
from src.domain.orchestration.planning.decision_engine import (
    AutonomousDecisionEngine,
    DecisionType,
    DecisionConfidence,
    DecisionRule as DomainDecisionRule,
)
from src.domain.orchestration.planning.trial_error import (
    TrialAndErrorEngine,
    TrialStatus,
)
from src.domain.orchestration.planning.dynamic_planner import (
    DynamicPlanner,
    ExecutionPlan,
    PlanStatus as DomainPlanStatus,
)

# 本地異常
from ..exceptions import AdapterError, ExecutionError, ValidationError

logger = logging.getLogger(__name__)


# =============================================================================
# 枚舉定義
# =============================================================================

class DecompositionStrategy(str, Enum):
    """任務分解策略枚舉。

    映射到 Phase 2 的 DecompositionStrategy。
    """
    SEQUENTIAL = "sequential"      # 順序分解
    HIERARCHICAL = "hierarchical"  # 階層分解
    PARALLEL = "parallel"          # 並行分解
    HYBRID = "hybrid"              # 混合分解 (默認)


class PlanningMode(str, Enum):
    """規劃模式枚舉。"""
    SIMPLE = "simple"              # 簡單規劃，無擴展
    DECOMPOSED = "decomposed"      # 帶任務分解
    DECISION_DRIVEN = "decision"   # 決策驅動
    ADAPTIVE = "adaptive"          # 自適應 (帶試錯學習)
    FULL = "full"                  # 完整模式 (所有擴展)


class PlanStatus(str, Enum):
    """規劃狀態枚舉。"""
    CREATED = "created"
    PLANNING = "planning"
    READY = "ready"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


# =============================================================================
# 數據類定義
# =============================================================================

@dataclass
class DecisionRule:
    """決策規則配置。

    用於配置決策引擎的規則。

    Attributes:
        name: 規則名稱
        condition: 條件函數
        action: 滿足條件時的動作
        priority: 規則優先級
        description: 規則描述
    """
    name: str
    condition: Callable[[str, List[str]], bool]
    action: str
    priority: int = 0
    description: str = ""


@dataclass
class PlanningConfig:
    """規劃配置。

    Attributes:
        max_subtasks: 最大子任務數
        max_depth: 最大分解深度
        timeout_seconds: 超時時間（秒）
        require_approval: 是否需要人工審批
        enable_learning: 是否啟用學習
    """
    max_subtasks: int = 20
    max_depth: int = 3
    timeout_seconds: float = 300.0
    require_approval: bool = False
    enable_learning: bool = False


@dataclass
class PlanningResult:
    """規劃執行結果。

    Attributes:
        plan_id: 計劃 ID
        goal: 原始目標
        status: 執行狀態
        subtasks: 子任務列表
        results: 執行結果
        decisions: 決策記錄
        duration_ms: 執行時間（毫秒）
        metadata: 額外元數據
    """
    plan_id: str
    goal: str
    status: PlanStatus
    subtasks: List[Dict[str, Any]] = field(default_factory=list)
    results: List[Dict[str, Any]] = field(default_factory=list)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式。"""
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "status": self.status.value,
            "subtasks": self.subtasks,
            "results": self.results,
            "decisions": self.decisions,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


# =============================================================================
# PlanningAdapter 主類
# =============================================================================

class PlanningAdapter:
    """動態規劃適配器。

    整合官方 MagenticBuilder 與 Phase 2 擴展功能：
    - TaskDecomposer: 任務分解
    - DecisionEngine: 決策引擎
    - TrialAndErrorEngine: 試錯學習

    遵循 Phase 4 架構原則，使用官方 API 作為核心。

    Example:
        ```python
        # 基本使用
        adapter = PlanningAdapter("my-planner")
        result = await adapter.run("Build a REST API")

        # 帶任務分解
        adapter = PlanningAdapter("decomposed-planner")
        adapter.with_task_decomposition(DecompositionStrategy.HYBRID)
        result = await adapter.run("Create user authentication")

        # 完整模式
        adapter = PlanningAdapter("full-planner")
        adapter.with_task_decomposition(DecompositionStrategy.HYBRID)
        adapter.with_decision_engine(rules=[...])
        adapter.with_trial_error(max_retries=3)
        result = await adapter.run("Complex enterprise workflow")
        ```
    """

    def __init__(
        self,
        id: str,
        config: Optional[PlanningConfig] = None,
    ):
        """初始化規劃適配器。

        Args:
            id: 適配器唯一標識符
            config: 規劃配置
        """
        self._id = id
        self._config = config or PlanningConfig()

        # 官方 Builder 實例
        self._magentic_builder = MagenticBuilder()

        # Phase 2 擴展功能（可選）
        self._task_decomposer: Optional[TaskDecomposer] = None
        self._decision_engine: Optional[AutonomousDecisionEngine] = None
        self._trial_error_engine: Optional[TrialAndErrorEngine] = None
        self._dynamic_planner: Optional[DynamicPlanner] = None

        # 分解結果緩存 (用於 refine_decomposition)
        self._decomposition_cache: Dict[str, DecompositionResult] = {}

        # 規劃模式
        self._mode = PlanningMode.SIMPLE

        # 分解策略
        self._decomposition_strategy = DecompositionStrategy.HYBRID

        # 決策規則
        self._decision_rules: List[DecisionRule] = []

        # 執行回調
        self._task_callback: Optional[Callable[[SubTask], Any]] = None

        # 初始化標記
        self._initialized = False

        logger.info(f"PlanningAdapter '{id}' 創建成功")

    # =========================================================================
    # 屬性
    # =========================================================================

    @property
    def id(self) -> str:
        """獲取適配器 ID。"""
        return self._id

    @property
    def mode(self) -> PlanningMode:
        """獲取當前規劃模式。"""
        return self._mode

    @property
    def config(self) -> PlanningConfig:
        """獲取配置。"""
        return self._config

    # =========================================================================
    # Builder 模式方法
    # =========================================================================

    def with_task_decomposition(
        self,
        strategy: DecompositionStrategy = DecompositionStrategy.HYBRID,
        max_subtasks: Optional[int] = None,
        max_depth: Optional[int] = None,
    ) -> "PlanningAdapter":
        """啟用任務分解功能。

        Args:
            strategy: 分解策略
            max_subtasks: 最大子任務數
            max_depth: 最大分解深度

        Returns:
            self，支持鏈式調用
        """
        self._decomposition_strategy = strategy

        self._task_decomposer = TaskDecomposer(
            max_subtasks=max_subtasks or self._config.max_subtasks,
            max_depth=max_depth or self._config.max_depth,
        )

        # 更新模式
        if self._mode == PlanningMode.SIMPLE:
            self._mode = PlanningMode.DECOMPOSED
        elif self._mode == PlanningMode.DECISION_DRIVEN:
            self._mode = PlanningMode.FULL

        logger.info(f"PlanningAdapter '{self._id}' 啟用任務分解，策略: {strategy.value}")
        return self

    def with_decision_engine(
        self,
        rules: Optional[List[DecisionRule]] = None,
        risk_threshold: float = 0.7,
        auto_decision_confidence: float = 0.8,
    ) -> "PlanningAdapter":
        """啟用決策引擎。

        Args:
            rules: 決策規則列表
            risk_threshold: 風險閾值
            auto_decision_confidence: 自動決策信心閾值

        Returns:
            self，支持鏈式調用
        """
        self._decision_engine = AutonomousDecisionEngine(
            risk_threshold=risk_threshold,
            auto_decision_confidence=auto_decision_confidence,
        )

        # 添加規則
        if rules:
            self._decision_rules = rules
            for rule in rules:
                self._decision_engine.add_rule(
                    name=rule.name,
                    condition=rule.condition,
                    action=rule.action,
                    priority=rule.priority,
                    description=rule.description,
                )

        # 更新模式
        if self._mode == PlanningMode.SIMPLE:
            self._mode = PlanningMode.DECISION_DRIVEN
        elif self._mode == PlanningMode.DECOMPOSED:
            self._mode = PlanningMode.FULL

        logger.info(f"PlanningAdapter '{self._id}' 啟用決策引擎，規則數: {len(self._decision_rules)}")
        return self

    def with_trial_error(
        self,
        max_retries: int = 3,
        learning_threshold: int = 5,
    ) -> "PlanningAdapter":
        """啟用試錯學習引擎。

        Args:
            max_retries: 最大重試次數
            learning_threshold: 學習閾值

        Returns:
            self，支持鏈式調用
        """
        self._trial_error_engine = TrialAndErrorEngine(
            max_retries=max_retries,
            learning_threshold=learning_threshold,
            timeout_seconds=int(self._config.timeout_seconds),
        )

        self._mode = PlanningMode.ADAPTIVE

        logger.info(f"PlanningAdapter '{self._id}' 啟用試錯學習，最大重試: {max_retries}")
        return self

    def with_task_callback(
        self,
        callback: Callable[[SubTask], Any],
    ) -> "PlanningAdapter":
        """設置任務執行回調。

        Args:
            callback: 任務執行回調函數

        Returns:
            self，支持鏈式調用
        """
        self._task_callback = callback
        logger.info(f"PlanningAdapter '{self._id}' 設置任務回調")
        return self

    def with_dynamic_planner(self) -> "PlanningAdapter":
        """啟用動態規劃功能。

        創建 DynamicPlanner 實例，支持計劃創建、執行和管理。

        Returns:
            self，支持鏈式調用
        """
        # 確保有 TaskDecomposer
        if not self._task_decomposer:
            self._task_decomposer = TaskDecomposer(
                max_subtasks=self._config.max_subtasks,
                max_depth=self._config.max_depth,
            )

        self._dynamic_planner = DynamicPlanner(
            task_decomposer=self._task_decomposer
        )

        logger.info(f"PlanningAdapter '{self._id}' 啟用動態規劃")
        return self

    # =========================================================================
    # 核心方法
    # =========================================================================

    def build(self) -> Workflow:
        """構建工作流。

        使用官方 MagenticBuilder 構建工作流。

        Returns:
            構建的 Workflow 實例
        """
        logger.info(f"PlanningAdapter '{self._id}' 構建工作流")
        return self._magentic_builder.build()

    async def initialize(self) -> None:
        """初始化適配器。"""
        if self._initialized:
            return

        logger.info(f"PlanningAdapter '{self._id}' 初始化")
        self._initialized = True

    async def run(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> PlanningResult:
        """執行動態規劃。

        根據配置的模式執行規劃：
        - SIMPLE: 直接使用官方 API
        - DECOMPOSED: 任務分解後執行
        - DECISION_DRIVEN: 決策引擎驅動
        - ADAPTIVE: 帶試錯學習
        - FULL: 完整模式

        Args:
            goal: 規劃目標
            context: 上下文信息

        Returns:
            PlanningResult 執行結果
        """
        await self.initialize()

        plan_id = str(uuid4())
        start_time = datetime.utcnow()

        logger.info(f"PlanningAdapter '{self._id}' 開始執行，目標: {goal[:50]}...")

        try:
            result = await self._execute_planning(plan_id, goal, context)

            # 計算執行時間
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            result.duration_ms = duration_ms

            logger.info(
                f"PlanningAdapter '{self._id}' 執行完成，"
                f"狀態: {result.status.value}，時間: {duration_ms}ms"
            )

            return result

        except Exception as e:
            logger.error(f"PlanningAdapter '{self._id}' 執行失敗: {e}")

            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            return PlanningResult(
                plan_id=plan_id,
                goal=goal,
                status=PlanStatus.FAILED,
                duration_ms=duration_ms,
                metadata={"error": str(e)},
            )

    async def _execute_planning(
        self,
        plan_id: str,
        goal: str,
        context: Optional[Dict[str, Any]],
    ) -> PlanningResult:
        """內部執行規劃邏輯。"""

        # 1. 任務分解（如果啟用）
        subtasks: List[Dict[str, Any]] = []
        decomposition_result: Optional[DecompositionResult] = None

        if self._task_decomposer:
            # 映射策略
            domain_strategy = self._decomposition_strategy.value

            decomposition_result = await self._task_decomposer.decompose(
                task_description=goal,
                context=context,
                strategy=domain_strategy,
            )

            subtasks = [t.to_dict() for t in decomposition_result.subtasks]
            logger.info(f"任務分解完成，子任務數: {len(subtasks)}")

        # 2. 構建並執行工作流
        workflow = self.build()
        results: List[Dict[str, Any]] = []
        decisions: List[Dict[str, Any]] = []

        if decomposition_result and self._task_callback:
            # 有任務分解和回調，逐個執行子任務
            for phase_tasks in decomposition_result.execution_order:
                phase_results = await self._execute_phase(
                    decomposition_result,
                    phase_tasks,
                    decisions,
                )
                results.extend(phase_results)
        else:
            # 直接執行
            try:
                result = await self._execute_with_workflow(workflow, goal, context)
                results.append(result)
            except Exception as e:
                results.append({"status": "failed", "error": str(e)})

        # 3. 確定最終狀態
        failed_count = sum(1 for r in results if r.get("status") == "failed")
        total_count = len(results) or 1

        if failed_count == 0:
            status = PlanStatus.COMPLETED
        elif failed_count < total_count:
            status = PlanStatus.COMPLETED  # 部分成功也算完成
        else:
            status = PlanStatus.FAILED

        return PlanningResult(
            plan_id=plan_id,
            goal=goal,
            status=status,
            subtasks=subtasks,
            results=results,
            decisions=decisions,
            metadata={
                "mode": self._mode.value,
                "decomposition_strategy": self._decomposition_strategy.value if self._task_decomposer else None,
                "context": context,
            },
        )

    async def _execute_phase(
        self,
        decomposition: DecompositionResult,
        task_ids: List[UUID],
        decisions: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """執行一個階段的任務。"""
        task_index = {t.id: t for t in decomposition.subtasks}
        results = []

        async def execute_single_task(task_id: UUID) -> Dict[str, Any]:
            task = task_index.get(task_id)
            if not task:
                return {"task_id": str(task_id), "status": "not_found"}

            # 決策引擎（如果啟用）
            if self._decision_engine:
                decision = await self._decision_engine.make_decision(
                    situation=task.description,
                    options=["execute", "skip", "defer"],
                    context={"task_name": task.name, "priority": task.priority.value},
                )
                decisions.append(decision)

                if decision.get("action") == "skip":
                    return {
                        "task_id": str(task_id),
                        "task_name": task.name,
                        "status": "skipped",
                        "decision": decision,
                    }

            # 試錯引擎（如果啟用）
            if self._trial_error_engine and self._task_callback:
                result = await self._trial_error_engine.execute_with_retry(
                    task_id=task_id,
                    execution_fn=lambda **kwargs: self._task_callback(task),
                    initial_params={},
                    strategy="default",
                )
                return {
                    "task_id": str(task_id),
                    "task_name": task.name,
                    **result,
                }

            # 直接執行
            if self._task_callback:
                try:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        self._task_callback,
                        task,
                    )
                    return {
                        "task_id": str(task_id),
                        "task_name": task.name,
                        "status": "completed",
                        "result": result,
                    }
                except Exception as e:
                    return {
                        "task_id": str(task_id),
                        "task_name": task.name,
                        "status": "failed",
                        "error": str(e),
                    }

            # 無回調，標記為待處理
            return {
                "task_id": str(task_id),
                "task_name": task.name,
                "status": "pending",
            }

        # 並行執行階段內的任務
        tasks = [execute_single_task(tid) for tid in task_ids]
        results = await asyncio.gather(*tasks)

        return list(results)

    async def _execute_with_workflow(
        self,
        workflow: Workflow,
        goal: str,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """使用官方工作流執行。"""
        try:
            # 這裡調用官方 Workflow 的執行方法
            # 實際實現取決於官方 API
            result = await workflow.run(goal)
            return {
                "status": "completed",
                "result": result,
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
            }

    # =========================================================================
    # 輔助方法
    # =========================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """獲取統計信息。"""
        stats = {
            "adapter_id": self._id,
            "mode": self._mode.value,
            "decomposition_strategy": self._decomposition_strategy.value,
            "has_task_decomposer": self._task_decomposer is not None,
            "has_decision_engine": self._decision_engine is not None,
            "has_trial_error_engine": self._trial_error_engine is not None,
            "decision_rules_count": len(self._decision_rules),
        }

        # 添加試錯引擎統計
        if self._trial_error_engine:
            stats["trial_error_stats"] = self._trial_error_engine.get_statistics()

        return stats

    async def cleanup(self) -> None:
        """清理資源。"""
        logger.info(f"PlanningAdapter '{self._id}' 清理資源")
        self._initialized = False

    # =========================================================================
    # 任務分解包裝方法 (Sprint 31 遷移)
    # =========================================================================

    async def decompose_task(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        strategy: str = "hybrid",
    ) -> DecompositionResult:
        """分解任務為子任務。

        包裝 TaskDecomposer.decompose()，供 API 層使用。

        Args:
            task_description: 任務描述
            context: 上下文信息
            strategy: 分解策略

        Returns:
            DecompositionResult 分解結果
        """
        if not self._task_decomposer:
            self._task_decomposer = TaskDecomposer(
                max_subtasks=self._config.max_subtasks,
                max_depth=self._config.max_depth,
            )

        result = await self._task_decomposer.decompose(
            task_description=task_description,
            context=context,
            strategy=strategy,
        )

        # 緩存結果以支持 refine
        self._decomposition_cache[str(result.task_id)] = result

        return result

    async def refine_decomposition(
        self,
        task_id: str,
        feedback: str,
    ) -> DecompositionResult:
        """根據反饋精煉分解結果。

        包裝 TaskDecomposer.refine_decomposition()。

        Args:
            task_id: 任務 ID
            feedback: 反饋內容

        Returns:
            DecompositionResult 精煉後的結果

        Raises:
            ValidationError: 找不到原始分解結果
        """
        original = self._decomposition_cache.get(task_id)
        if not original:
            raise ValidationError(f"Decomposition not found: {task_id}")

        if not self._task_decomposer:
            raise ValidationError("TaskDecomposer not initialized")

        result = await self._task_decomposer.refine_decomposition(
            result=original,
            feedback=feedback,
        )

        # 更新緩存
        self._decomposition_cache[task_id] = result

        return result

    # =========================================================================
    # 動態規劃包裝方法 (Sprint 31 遷移)
    # =========================================================================

    async def create_plan(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        deadline: Optional[datetime] = None,
        strategy: str = "default",
    ) -> ExecutionPlan:
        """創建執行計劃。

        包裝 DynamicPlanner.create_plan()。

        Args:
            goal: 計劃目標
            context: 上下文信息
            deadline: 截止日期
            strategy: 規劃策略

        Returns:
            Plan 計劃實例
        """
        if not self._dynamic_planner:
            self.with_dynamic_planner()

        return await self._dynamic_planner.create_plan(
            goal=goal,
            context=context,
            deadline=deadline,
            strategy=strategy,
        )

    def get_plan_status(self, plan_id: UUID) -> Dict[str, Any]:
        """獲取計劃狀態。

        包裝 DynamicPlanner.get_plan_status()。

        Args:
            plan_id: 計劃 ID

        Returns:
            計劃狀態字典
        """
        if not self._dynamic_planner:
            return {"error": "DynamicPlanner not initialized"}

        return self._dynamic_planner.get_plan_status(plan_id)

    async def execute_plan(
        self,
        plan_id: UUID,
        execution_callback: Callable,
    ) -> None:
        """執行計劃。

        包裝 DynamicPlanner.execute_plan()。

        Args:
            plan_id: 計劃 ID
            execution_callback: 執行回調函數
        """
        if not self._dynamic_planner:
            self.with_dynamic_planner()

        await self._dynamic_planner.execute_plan(plan_id, execution_callback)

    async def pause_plan(self, plan_id: UUID) -> None:
        """暫停計劃執行。

        包裝 DynamicPlanner.pause_plan()。

        Args:
            plan_id: 計劃 ID
        """
        if not self._dynamic_planner:
            raise ValidationError("DynamicPlanner not initialized")

        await self._dynamic_planner.pause_plan(plan_id)

    async def approve_plan(self, plan_id: UUID, approver: str) -> None:
        """審批計劃。

        包裝 DynamicPlanner.approve_plan()。

        Args:
            plan_id: 計劃 ID
            approver: 審批者
        """
        if not self._dynamic_planner:
            raise ValidationError("DynamicPlanner not initialized")

        await self._dynamic_planner.approve_plan(plan_id, approver)

    async def approve_adjustment(
        self,
        plan_id: UUID,
        adjustment_id: UUID,
        approver: str,
    ) -> None:
        """審批計劃調整。

        包裝 DynamicPlanner.approve_adjustment()。

        Args:
            plan_id: 計劃 ID
            adjustment_id: 調整 ID
            approver: 審批者
        """
        if not self._dynamic_planner:
            raise ValidationError("DynamicPlanner not initialized")

        await self._dynamic_planner.approve_adjustment(plan_id, adjustment_id, approver)

    def list_plans(
        self,
        status: Optional[DomainPlanStatus] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """列出計劃。

        包裝 DynamicPlanner.list_plans()。

        Args:
            status: 過濾狀態
            limit: 限制數量

        Returns:
            計劃列表
        """
        if not self._dynamic_planner:
            return []

        return self._dynamic_planner.list_plans(status=status, limit=limit)

    def delete_plan(self, plan_id: UUID) -> bool:
        """刪除計劃。

        包裝 DynamicPlanner.delete_plan()。

        Args:
            plan_id: 計劃 ID

        Returns:
            是否成功刪除
        """
        if not self._dynamic_planner:
            return False

        return self._dynamic_planner.delete_plan(plan_id)

    # =========================================================================
    # 決策引擎包裝方法 (Sprint 31 遷移)
    # =========================================================================

    async def make_decision(
        self,
        situation: str,
        options: List[str],
        context: Optional[Dict[str, Any]] = None,
        decision_type: Optional[DecisionType] = None,
    ) -> Dict[str, Any]:
        """做出決策。

        包裝 AutonomousDecisionEngine.make_decision()。

        Args:
            situation: 情況描述
            options: 可選項列表
            context: 上下文信息
            decision_type: 決策類型

        Returns:
            決策結果字典
        """
        if not self._decision_engine:
            self.with_decision_engine()

        return await self._decision_engine.make_decision(
            situation=situation,
            options=options,
            context=context,
            decision_type=decision_type,
        )

    async def explain_decision(self, decision_id: UUID) -> str:
        """解釋決策。

        包裝 AutonomousDecisionEngine.explain_decision()。

        Args:
            decision_id: 決策 ID

        Returns:
            決策解釋
        """
        if not self._decision_engine:
            return "Decision engine not initialized"

        return await self._decision_engine.explain_decision(decision_id)

    async def approve_decision(self, decision_id: UUID, approver: str) -> bool:
        """審批決策。

        包裝 AutonomousDecisionEngine.approve_decision()。

        Args:
            decision_id: 決策 ID
            approver: 審批者

        Returns:
            是否成功
        """
        if not self._decision_engine:
            return False

        return await self._decision_engine.approve_decision(decision_id, approver)

    async def reject_decision(
        self,
        decision_id: UUID,
        approver: str,
        reason: str,
    ) -> bool:
        """拒絕決策。

        包裝 AutonomousDecisionEngine.reject_decision()。

        Args:
            decision_id: 決策 ID
            approver: 審批者
            reason: 拒絕原因

        Returns:
            是否成功
        """
        if not self._decision_engine:
            return False

        return await self._decision_engine.reject_decision(decision_id, approver, reason)

    def get_decision_history(
        self,
        decision_type: Optional[DecisionType] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """獲取決策歷史。

        包裝 AutonomousDecisionEngine.get_decision_history()。

        Args:
            decision_type: 決策類型過濾
            limit: 限制數量

        Returns:
            決策歷史列表
        """
        if not self._decision_engine:
            return []

        return self._decision_engine.get_decision_history(
            decision_type=decision_type,
            limit=limit,
        )

    def list_decision_rules(self) -> List[Dict[str, Any]]:
        """列出決策規則。

        包裝 AutonomousDecisionEngine.list_rules()。

        Returns:
            規則列表
        """
        if not self._decision_engine:
            return []

        return self._decision_engine.list_rules()

    # =========================================================================
    # 試錯學習包裝方法 (Sprint 31 遷移)
    # =========================================================================

    async def execute_trial(
        self,
        task_id: UUID,
        execution_fn: Callable,
        initial_params: Dict[str, Any],
        strategy: str = "default",
    ) -> Dict[str, Any]:
        """執行試錯。

        包裝 TrialAndErrorEngine.execute_with_retry()。

        Args:
            task_id: 任務 ID
            execution_fn: 執行函數
            initial_params: 初始參數
            strategy: 試錯策略

        Returns:
            試錯結果
        """
        if not self._trial_error_engine:
            self.with_trial_error()

        return await self._trial_error_engine.execute_with_retry(
            task_id=task_id,
            execution_fn=execution_fn,
            initial_params=initial_params,
            strategy=strategy,
        )

    async def learn_from_history(self) -> List[Any]:
        """從歷史學習。

        包裝 TrialAndErrorEngine.learn_from_history()。

        Returns:
            學習洞察列表
        """
        if not self._trial_error_engine:
            return []

        return await self._trial_error_engine.learn_from_history()

    def get_trial_recommendations(
        self,
        task_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """獲取試錯建議。

        包裝 TrialAndErrorEngine.get_recommendations()。

        Args:
            task_type: 任務類型過濾

        Returns:
            建議列表
        """
        if not self._trial_error_engine:
            return []

        return self._trial_error_engine.get_recommendations(task_type=task_type)

    def get_trial_statistics(self) -> Dict[str, Any]:
        """獲取試錯統計。

        包裝 TrialAndErrorEngine.get_statistics()。

        Returns:
            統計信息
        """
        if not self._trial_error_engine:
            return {}

        return self._trial_error_engine.get_statistics()

    def get_trial_history(
        self,
        task_id: Optional[UUID] = None,
        status: Optional[TrialStatus] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """獲取試錯歷史。

        包裝 TrialAndErrorEngine.get_trial_history()。

        Args:
            task_id: 任務 ID 過濾
            status: 狀態過濾
            limit: 限制數量

        Returns:
            試錯歷史列表
        """
        if not self._trial_error_engine:
            return []

        return self._trial_error_engine.get_trial_history(
            task_id=task_id,
            status=status,
            limit=limit,
        )

    def clear_trial_history(self, task_id: Optional[UUID] = None) -> None:
        """清除試錯歷史。

        包裝 TrialAndErrorEngine.clear_history()。

        Args:
            task_id: 任務 ID (可選，不提供則清除全部)
        """
        if self._trial_error_engine:
            self._trial_error_engine.clear_history(task_id=task_id)


# =============================================================================
# 類型重新導出 (供 API 層使用，避免直接導入 domain)
# =============================================================================

# 從 domain 重新導出，集中管理
__all__ = [
    # 主要類
    "PlanningAdapter",
    "PlanningConfig",
    "PlanningResult",
    "DecisionRule",
    # 枚舉
    "PlanningMode",
    "PlanStatus",
    "DecompositionStrategy",
    "DecisionType",
    "TrialStatus",
    # Domain 類型 (透過適配器重新導出)
    "DomainPlanStatus",
    "DecompositionResult",
    "SubTask",
    "TaskStatus",
    "TaskPriority",
    "ExecutionPlan",
    # 工廠函數
    "create_planning_adapter",
    "create_simple_planner",
    "create_decomposed_planner",
    "create_full_planner",
]


# =============================================================================
# 工廠函數
# =============================================================================

def create_planning_adapter(
    id: str,
    mode: PlanningMode = PlanningMode.SIMPLE,
    config: Optional[PlanningConfig] = None,
) -> PlanningAdapter:
    """創建規劃適配器的工廠函數。

    Args:
        id: 適配器 ID
        mode: 規劃模式
        config: 配置

    Returns:
        配置好的 PlanningAdapter 實例
    """
    adapter = PlanningAdapter(id=id, config=config)

    if mode in [PlanningMode.DECOMPOSED, PlanningMode.FULL]:
        adapter.with_task_decomposition()

    if mode in [PlanningMode.DECISION_DRIVEN, PlanningMode.FULL]:
        adapter.with_decision_engine()

    if mode == PlanningMode.ADAPTIVE:
        adapter.with_task_decomposition()
        adapter.with_trial_error()

    return adapter


def create_simple_planner(id: str) -> PlanningAdapter:
    """創建簡單規劃適配器。"""
    return create_planning_adapter(id=id, mode=PlanningMode.SIMPLE)


def create_decomposed_planner(
    id: str,
    strategy: DecompositionStrategy = DecompositionStrategy.HYBRID,
) -> PlanningAdapter:
    """創建帶任務分解的規劃適配器。"""
    return PlanningAdapter(id=id).with_task_decomposition(strategy=strategy)


def create_full_planner(
    id: str,
    config: Optional[PlanningConfig] = None,
) -> PlanningAdapter:
    """創建完整模式的規劃適配器。"""
    return create_planning_adapter(id=id, mode=PlanningMode.FULL, config=config)
