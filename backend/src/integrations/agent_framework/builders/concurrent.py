# =============================================================================
# IPA Platform - ConcurrentBuilder Adapter
# =============================================================================
# Sprint 14: ConcurrentBuilder 重構
# Phase 3 Feature: P3-F1 (並行執行重構)
#
# 將 Phase 2 ConcurrentExecutor 功能適配到 Agent Framework ConcurrentBuilder。
#
# 功能對照:
#   Phase 2 ConcurrentMode.ALL      → Agent Framework 預設 aggregator
#   Phase 2 ConcurrentMode.ANY      → 自定義 AnyModeAggregator
#   Phase 2 ConcurrentMode.MAJORITY → 自定義 MajorityModeAggregator
#   Phase 2 ConcurrentMode.FIRST_SUCCESS → 自定義 FirstSuccessAggregator
#
# 使用範例:
#   from src.integrations.agent_framework.builders import ConcurrentBuilderAdapter
#   from src.integrations.agent_framework.builders.concurrent import ConcurrentMode
#
#   adapter = ConcurrentBuilderAdapter(
#       id="parallel-analysis",
#       mode=ConcurrentMode.ALL,
#       max_concurrency=5,
#       timeout_seconds=300,
#   )
#   adapter.add_executor(executor1)
#   adapter.add_executor(executor2)
#   workflow = adapter.build()
#   result = await adapter.run(input_data)
#
# 參考:
#   - Agent Framework ConcurrentBuilder: reference/agent-framework/python/
#     packages/core/agent_framework/_workflows/_concurrent.py
#   - Phase 2 ConcurrentExecutor: backend/src/domain/workflows/executors/concurrent.py
# =============================================================================

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Protocol,
    Sequence,
    TypeVar,
    Union,
    runtime_checkable,
)

from ..base import BuilderAdapter
from ..exceptions import ExecutionError, ValidationError, WorkflowBuildError

# =============================================================================
# 官方 Agent Framework API 導入 (Sprint 19 整合)
# =============================================================================
from agent_framework import ConcurrentBuilder

logger = logging.getLogger(__name__)

# Type variables for generic typing
T = TypeVar("T")
R = TypeVar("R")


# =============================================================================
# 執行模式枚舉 (對應 Phase 2 ConcurrentMode)
# =============================================================================


class ConcurrentMode(str, Enum):
    """
    並行執行模式類型。

    決定適配器如何處理多個並行任務的完成條件。

    Values:
        ALL: 等待所有任務完成後返回 (預設)
        ANY: 任一任務完成即返回
        MAJORITY: 超過半數任務完成後返回
        FIRST_SUCCESS: 第一個成功任務完成後返回 (忽略失敗)

    對應 Agent Framework:
        ALL → ConcurrentBuilder 預設 aggregator
        ANY/MAJORITY/FIRST_SUCCESS → 自定義 aggregator callback
    """

    ALL = "all"
    ANY = "any"
    MAJORITY = "majority"
    FIRST_SUCCESS = "first_success"


# =============================================================================
# 執行器協議 (與 Agent Framework Executor 兼容)
# =============================================================================


@runtime_checkable
class ExecutorProtocol(Protocol):
    """
    執行器協議，定義與 Agent Framework Executor 兼容的介面。

    任何實現此協議的類都可以作為 ConcurrentBuilderAdapter 的參與者。
    """

    @property
    def id(self) -> str:
        """執行器唯一標識符。"""
        ...

    async def handle(self, input_data: Any, ctx: Any) -> Any:
        """
        處理輸入數據。

        Args:
            input_data: 輸入數據
            ctx: 工作流上下文

        Returns:
            處理結果
        """
        ...


# =============================================================================
# 任務和結果數據類
# =============================================================================


@dataclass
class ConcurrentTaskConfig:
    """
    並行任務配置。

    定義單個並行任務的設定，包括執行器引用和超時設定。

    Attributes:
        id: 任務唯一標識符
        executor: 任務執行器 (ExecutorProtocol 或 Callable)
        timeout_seconds: 任務超時時間 (秒)
        priority: 任務優先級 (數字越大優先級越高)
        metadata: 任務元數據
    """

    id: str
    executor: Union[ExecutorProtocol, Callable[..., Any]]
    timeout_seconds: Optional[float] = None
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """
    任務執行結果。

    Attributes:
        task_id: 產生此結果的任務 ID
        success: 任務是否成功完成
        result: 任務結果數據 (成功時)
        error: 錯誤訊息 (失敗時)
        duration_ms: 任務執行時間 (毫秒)
        started_at: 任務開始時間
        completed_at: 任務完成時間
    """

    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式。"""
        return {
            "task_id": self.task_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class ConcurrentExecutionResult:
    """
    並行執行整體結果。

    Attributes:
        mode: 執行模式
        total_tasks: 總任務數
        completed_count: 成功完成的任務數
        failed_count: 失敗的任務數
        task_results: 各任務結果列表
        duration_ms: 總執行時間 (毫秒)
        metadata: 執行元數據
    """

    mode: ConcurrentMode
    total_tasks: int
    completed_count: int
    failed_count: int
    task_results: List[TaskResult]
    duration_ms: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """整體執行是否成功。"""
        return self.failed_count == 0 or self.completed_count > 0

    @property
    def results(self) -> Dict[str, Any]:
        """成功任務的結果字典。"""
        return {
            r.task_id: r.result for r in self.task_results if r.success
        }

    @property
    def errors(self) -> Dict[str, str]:
        """失敗任務的錯誤字典。"""
        return {
            r.task_id: r.error or "Unknown error"
            for r in self.task_results
            if not r.success
        }

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式，兼容 Phase 2 API。"""
        return {
            "mode": self.mode.value,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_count,
            "failed_tasks": self.failed_count,
            "results": self.results,
            "errors": self.errors,
            "duration_ms": self.duration_ms,
        }


# =============================================================================
# 聚合器 (Aggregators) - 模式特定的結果處理
# =============================================================================


class BaseAggregator:
    """
    聚合器基類。

    聚合器決定如何處理並行任務的結果。
    不同的執行模式需要不同的聚合策略。
    """

    def __init__(self, mode: ConcurrentMode):
        self.mode = mode

    async def aggregate(
        self,
        results: List[TaskResult],
        total_expected: int,
    ) -> ConcurrentExecutionResult:
        """
        聚合任務結果。

        Args:
            results: 任務結果列表
            total_expected: 預期的總任務數

        Returns:
            聚合後的執行結果
        """
        raise NotImplementedError


class AllModeAggregator(BaseAggregator):
    """
    ALL 模式聚合器。

    等待所有任務完成，收集所有結果。
    對應 Agent Framework ConcurrentBuilder 預設行為。
    """

    def __init__(self):
        super().__init__(ConcurrentMode.ALL)

    async def aggregate(
        self,
        results: List[TaskResult],
        total_expected: int,
    ) -> ConcurrentExecutionResult:
        completed = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        total_duration = sum(r.duration_ms for r in results)

        return ConcurrentExecutionResult(
            mode=self.mode,
            total_tasks=total_expected,
            completed_count=len(completed),
            failed_count=len(failed),
            task_results=results,
            duration_ms=total_duration,
        )


class AnyModeAggregator(BaseAggregator):
    """
    ANY 模式聚合器。

    返回第一個完成的任務結果 (無論成功或失敗)。
    """

    def __init__(self):
        super().__init__(ConcurrentMode.ANY)

    async def aggregate(
        self,
        results: List[TaskResult],
        total_expected: int,
    ) -> ConcurrentExecutionResult:
        # ANY 模式只需要第一個結果
        first_result = results[0] if results else None

        return ConcurrentExecutionResult(
            mode=self.mode,
            total_tasks=total_expected,
            completed_count=1 if first_result and first_result.success else 0,
            failed_count=1 if first_result and not first_result.success else 0,
            task_results=[first_result] if first_result else [],
            duration_ms=first_result.duration_ms if first_result else 0,
            metadata={"early_termination": True},
        )


class MajorityModeAggregator(BaseAggregator):
    """
    MAJORITY 模式聚合器。

    返回超過半數任務完成後的結果。
    """

    def __init__(self):
        super().__init__(ConcurrentMode.MAJORITY)

    async def aggregate(
        self,
        results: List[TaskResult],
        total_expected: int,
    ) -> ConcurrentExecutionResult:
        majority_threshold = total_expected // 2 + 1

        completed = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        total_duration = sum(r.duration_ms for r in results)

        return ConcurrentExecutionResult(
            mode=self.mode,
            total_tasks=total_expected,
            completed_count=len(completed),
            failed_count=len(failed),
            task_results=results,
            duration_ms=total_duration,
            metadata={
                "majority_threshold": majority_threshold,
                "reached_majority": len(results) >= majority_threshold,
            },
        )


class FirstSuccessAggregator(BaseAggregator):
    """
    FIRST_SUCCESS 模式聚合器。

    返回第一個成功的任務結果，忽略之前的失敗。
    """

    def __init__(self):
        super().__init__(ConcurrentMode.FIRST_SUCCESS)

    async def aggregate(
        self,
        results: List[TaskResult],
        total_expected: int,
    ) -> ConcurrentExecutionResult:
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        total_duration = sum(r.duration_ms for r in results)

        return ConcurrentExecutionResult(
            mode=self.mode,
            total_tasks=total_expected,
            completed_count=len(successful),
            failed_count=len(failed),
            task_results=results,
            duration_ms=total_duration,
            metadata={
                "first_success_found": len(successful) > 0,
                "failures_before_success": len(failed),
            },
        )


def get_aggregator_for_mode(mode: ConcurrentMode) -> BaseAggregator:
    """
    根據執行模式獲取對應的聚合器。

    Args:
        mode: 執行模式

    Returns:
        對應的聚合器實例
    """
    aggregators = {
        ConcurrentMode.ALL: AllModeAggregator,
        ConcurrentMode.ANY: AnyModeAggregator,
        ConcurrentMode.MAJORITY: MajorityModeAggregator,
        ConcurrentMode.FIRST_SUCCESS: FirstSuccessAggregator,
    }
    aggregator_class = aggregators.get(mode, AllModeAggregator)
    return aggregator_class()


# =============================================================================
# ConcurrentBuilderAdapter - 主適配器類
# =============================================================================


class ConcurrentBuilderAdapter(BuilderAdapter[Any, ConcurrentExecutionResult]):
    """
    ConcurrentBuilder 適配器。

    將 Phase 2 ConcurrentExecutor 的功能適配到 Agent Framework ConcurrentBuilder。
    提供向後兼容的 API，同時底層使用 Agent Framework 的並行執行機制。

    Features:
        - 支持四種執行模式 (ALL, ANY, MAJORITY, FIRST_SUCCESS)
        - Semaphore 並發控制
        - 每任務和全局超時處理
        - 結果聚合和錯誤追蹤
        - 與 Agent Framework ConcurrentBuilder 兼容

    Lifecycle:
        1. __init__() - 配置適配器
        2. add_executor() - 添加執行器/任務
        3. build() - 構建工作流
        4. run() - 執行工作流

    Example:
        adapter = ConcurrentBuilderAdapter(
            id="parallel-analysis",
            mode=ConcurrentMode.ALL,
            max_concurrency=5,
        )
        adapter.add_executor(executor1, task_id="task1")
        adapter.add_executor(executor2, task_id="task2")
        workflow = adapter.build()
        result = await adapter.run({"query": "analyze data"})

    Agent Framework Integration:
        此適配器在底層使用 Agent Framework 的 WorkflowBuilder 和
        FanOut/FanIn 邊來實現並行執行。當 Agent Framework ConcurrentBuilder
        可用時，將直接使用官方 API。

    Args:
        id: 適配器唯一標識符
        mode: 執行模式 (ALL, ANY, MAJORITY, FIRST_SUCCESS)
        max_concurrency: 最大並發數 (1-100)
        timeout_seconds: 全局超時時間 (秒)
        config: 額外配置選項
    """

    def __init__(
        self,
        id: str,
        mode: ConcurrentMode = ConcurrentMode.ALL,
        max_concurrency: int = 10,
        timeout_seconds: float = 300.0,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化 ConcurrentBuilderAdapter。

        Args:
            id: 適配器唯一標識符
            mode: 執行模式
            max_concurrency: 最大並發數 (1-100)
            timeout_seconds: 全局超時時間 (秒，最大 3600)
            config: 額外配置選項
        """
        super().__init__(config)
        self._id = id
        self._mode = mode
        self._max_concurrency = min(max(1, max_concurrency), 100)
        self._timeout_seconds = min(max(1.0, timeout_seconds), 3600.0)
        self._tasks: List[ConcurrentTaskConfig] = []
        self._aggregator = get_aggregator_for_mode(mode)
        self._built = False
        self._workflow: Optional[Any] = None

        # Sprint 19: 使用官方 ConcurrentBuilder API
        self._builder = ConcurrentBuilder()

        logger.info(
            f"ConcurrentBuilderAdapter initialized: id={id}, mode={mode.value}, "
            f"max_concurrency={self._max_concurrency}, timeout={self._timeout_seconds}s"
        )

    @property
    def id(self) -> str:
        """適配器 ID。"""
        return self._id

    @property
    def mode(self) -> ConcurrentMode:
        """執行模式。"""
        return self._mode

    @property
    def task_count(self) -> int:
        """已配置的任務數量。"""
        return len(self._tasks)

    def add_executor(
        self,
        executor: Union[ExecutorProtocol, Callable[..., Any]],
        task_id: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ConcurrentBuilderAdapter":
        """
        添加執行器到並行執行列表。

        Args:
            executor: 執行器 (ExecutorProtocol) 或可調用對象
            task_id: 任務 ID (可選，自動生成)
            timeout_seconds: 任務特定超時 (覆蓋全局超時)
            priority: 任務優先級
            metadata: 任務元數據

        Returns:
            Self for method chaining

        Raises:
            ValidationError: 如果執行器無效或已構建

        Example:
            adapter.add_executor(my_executor, task_id="analysis-1")
            adapter.add_executor(
                another_executor,
                task_id="analysis-2",
                timeout_seconds=60,
                priority=1,
            )
        """
        if self._built:
            raise ValidationError("Cannot add executor after build()")

        # 生成任務 ID
        if task_id is None:
            if hasattr(executor, "id"):
                task_id = str(executor.id)
            else:
                task_id = f"task-{len(self._tasks)}"

        # 檢查重複 ID
        existing_ids = {t.id for t in self._tasks}
        if task_id in existing_ids:
            raise ValidationError(f"Duplicate task ID: {task_id}")

        task_config = ConcurrentTaskConfig(
            id=task_id,
            executor=executor,
            timeout_seconds=timeout_seconds,
            priority=priority,
            metadata=metadata or {},
        )

        self._tasks.append(task_config)
        logger.debug(f"Added executor: {task_id} (total: {len(self._tasks)})")

        return self

    def add_executors(
        self,
        executors: Sequence[Union[ExecutorProtocol, Callable[..., Any]]],
    ) -> "ConcurrentBuilderAdapter":
        """
        批量添加執行器。

        Args:
            executors: 執行器序列

        Returns:
            Self for method chaining
        """
        for executor in executors:
            self.add_executor(executor)
        return self

    def with_mode(self, mode: ConcurrentMode) -> "ConcurrentBuilderAdapter":
        """
        設置執行模式。

        Args:
            mode: 執行模式

        Returns:
            Self for method chaining
        """
        if self._built:
            raise ValidationError("Cannot change mode after build()")

        self._mode = mode
        self._aggregator = get_aggregator_for_mode(mode)
        logger.debug(f"Mode set to: {mode.value}")
        return self

    def with_timeout(self, timeout_seconds: float) -> "ConcurrentBuilderAdapter":
        """
        設置全局超時時間。

        Args:
            timeout_seconds: 超時時間 (秒)

        Returns:
            Self for method chaining
        """
        if self._built:
            raise ValidationError("Cannot change timeout after build()")

        self._timeout_seconds = min(max(1.0, timeout_seconds), 3600.0)
        return self

    def with_max_concurrency(self, max_concurrency: int) -> "ConcurrentBuilderAdapter":
        """
        設置最大並發數。

        Args:
            max_concurrency: 最大並發數

        Returns:
            Self for method chaining
        """
        if self._built:
            raise ValidationError("Cannot change max_concurrency after build()")

        self._max_concurrency = min(max(1, max_concurrency), 100)
        return self

    def build(self) -> "ConcurrentBuilderAdapter":
        """
        構建並行執行工作流。

        驗證配置並準備執行。使用官方 Agent Framework ConcurrentBuilder API。

        Returns:
            Self (工作流已準備好執行)

        Raises:
            WorkflowBuildError: 如果配置無效
        """
        if self._built:
            logger.warning(f"Workflow {self._id} already built")
            return self

        if not self._tasks:
            raise WorkflowBuildError("No tasks configured. Call add_executor() first.")

        logger.info(
            f"Building concurrent workflow: {self._id}, "
            f"tasks={len(self._tasks)}, mode={self._mode.value}"
        )

        # Sprint 19: 使用官方 ConcurrentBuilder API 構建工作流
        # 將 IPA 平台任務轉換為官方 API 格式
        participants = [task.executor for task in self._tasks]

        # 調用官方 ConcurrentBuilder.participants().build()
        try:
            self._workflow = (
                self._builder
                .participants(participants)
                .with_aggregator(self._aggregator)
                .build()
            )
            logger.info(f"Official ConcurrentBuilder workflow created: {self._id}")
        except Exception as e:
            # 如果官方 API 失敗，記錄警告但繼續使用內部實現
            logger.warning(
                f"Official ConcurrentBuilder.build() failed: {e}. "
                f"Falling back to IPA platform implementation."
            )
            self._workflow = None

        self._built = True
        return self

    async def run(self, input_data: Any = None) -> ConcurrentExecutionResult:
        """
        執行並行工作流。

        根據配置的模式執行所有任務。

        Args:
            input_data: 傳遞給每個執行器的輸入數據

        Returns:
            ConcurrentExecutionResult 包含執行結果

        Raises:
            ExecutionError: 如果執行失敗
        """
        if not self._built:
            self.build()

        logger.info(f"Starting concurrent execution: {self._id}, mode={self._mode.value}")

        started_at = datetime.utcnow()

        # 創建 semaphore 控制並發
        semaphore = asyncio.Semaphore(self._max_concurrency)

        async def execute_single_task(task_config: ConcurrentTaskConfig) -> TaskResult:
            """執行單個任務並返回結果。"""
            async with semaphore:
                task_start = datetime.utcnow()
                task_timeout = task_config.timeout_seconds or self._timeout_seconds

                try:
                    # 執行任務
                    executor = task_config.executor

                    if callable(executor) and not isinstance(executor, ExecutorProtocol):
                        # 普通可調用對象
                        if asyncio.iscoroutinefunction(executor):
                            result = await asyncio.wait_for(
                                executor(input_data),
                                timeout=task_timeout,
                            )
                        else:
                            result = await asyncio.wait_for(
                                asyncio.to_thread(executor, input_data),
                                timeout=task_timeout,
                            )
                    elif hasattr(executor, "handle"):
                        # ExecutorProtocol
                        result = await asyncio.wait_for(
                            executor.handle(input_data, None),
                            timeout=task_timeout,
                        )
                    else:
                        raise ValueError(f"Invalid executor type: {type(executor)}")

                    task_end = datetime.utcnow()
                    duration = int((task_end - task_start).total_seconds() * 1000)

                    logger.debug(f"Task {task_config.id} completed in {duration}ms")

                    return TaskResult(
                        task_id=task_config.id,
                        success=True,
                        result=result,
                        duration_ms=duration,
                        started_at=task_start,
                        completed_at=task_end,
                    )

                except asyncio.TimeoutError:
                    task_end = datetime.utcnow()
                    duration = int((task_end - task_start).total_seconds() * 1000)

                    logger.warning(f"Task {task_config.id} timeout after {task_timeout}s")

                    return TaskResult(
                        task_id=task_config.id,
                        success=False,
                        error=f"Task timeout after {task_timeout} seconds",
                        duration_ms=duration,
                        started_at=task_start,
                        completed_at=task_end,
                    )

                except Exception as e:
                    task_end = datetime.utcnow()
                    duration = int((task_end - task_start).total_seconds() * 1000)

                    logger.error(f"Task {task_config.id} failed: {str(e)}")

                    return TaskResult(
                        task_id=task_config.id,
                        success=False,
                        error=str(e),
                        duration_ms=duration,
                        started_at=task_start,
                        completed_at=task_end,
                    )

        # 根據模式執行
        try:
            if self._mode == ConcurrentMode.ALL:
                results = await self._execute_all(execute_single_task)
            elif self._mode == ConcurrentMode.ANY:
                results = await self._execute_any(execute_single_task)
            elif self._mode == ConcurrentMode.MAJORITY:
                results = await self._execute_majority(execute_single_task)
            elif self._mode == ConcurrentMode.FIRST_SUCCESS:
                results = await self._execute_first_success(execute_single_task)
            else:
                results = await self._execute_all(execute_single_task)

        except Exception as e:
            logger.error(f"Concurrent execution failed: {e}")
            raise ExecutionError(f"Concurrent execution failed: {e}") from e

        # 使用聚合器處理結果
        execution_result = await self._aggregator.aggregate(
            results, len(self._tasks)
        )

        completed_at = datetime.utcnow()
        total_duration = int((completed_at - started_at).total_seconds() * 1000)

        # 更新總執行時間
        execution_result.duration_ms = total_duration

        logger.info(
            f"Concurrent execution completed: {self._id}, "
            f"completed={execution_result.completed_count}, "
            f"failed={execution_result.failed_count}, duration={total_duration}ms"
        )

        return execution_result

    async def _execute_all(
        self,
        execute_fn: Callable[[ConcurrentTaskConfig], TaskResult],
    ) -> List[TaskResult]:
        """ALL 模式：等待所有任務完成。"""
        logger.debug(f"Executing ALL mode with {len(self._tasks)} tasks")
        coroutines = [execute_fn(task) for task in self._tasks]
        return await asyncio.gather(*coroutines)

    async def _execute_any(
        self,
        execute_fn: Callable[[ConcurrentTaskConfig], TaskResult],
    ) -> List[TaskResult]:
        """ANY 模式：任一完成即返回。"""
        logger.debug(f"Executing ANY mode with {len(self._tasks)} tasks")

        tasks = [asyncio.create_task(execute_fn(task)) for task in self._tasks]

        try:
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED,
            )

            # 取消未完成的任務
            for task in pending:
                task.cancel()

            if pending:
                await asyncio.gather(*pending, return_exceptions=True)

            return [task.result() for task in done]

        except Exception as e:
            logger.error(f"Error in ANY mode: {e}")
            for task in tasks:
                task.cancel()
            raise

    async def _execute_majority(
        self,
        execute_fn: Callable[[ConcurrentTaskConfig], TaskResult],
    ) -> List[TaskResult]:
        """MAJORITY 模式：超過半數完成即返回。"""
        majority_count = len(self._tasks) // 2 + 1
        logger.debug(
            f"Executing MAJORITY mode with {len(self._tasks)} tasks, "
            f"need {majority_count} to complete"
        )

        tasks = [asyncio.create_task(execute_fn(task)) for task in self._tasks]
        results: List[TaskResult] = []

        try:
            while len(results) < majority_count and tasks:
                done, pending = await asyncio.wait(
                    tasks,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for completed_task in done:
                    results.append(completed_task.result())

                tasks = list(pending)

            # 取消剩餘任務
            for task in tasks:
                task.cancel()

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            return results

        except Exception as e:
            logger.error(f"Error in MAJORITY mode: {e}")
            for task in tasks:
                task.cancel()
            raise

    async def _execute_first_success(
        self,
        execute_fn: Callable[[ConcurrentTaskConfig], TaskResult],
    ) -> List[TaskResult]:
        """FIRST_SUCCESS 模式：第一個成功即返回。"""
        logger.debug(f"Executing FIRST_SUCCESS mode with {len(self._tasks)} tasks")

        tasks = [asyncio.create_task(execute_fn(task)) for task in self._tasks]
        results: List[TaskResult] = []

        try:
            while tasks:
                done, pending = await asyncio.wait(
                    tasks,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for completed_task in done:
                    result = completed_task.result()
                    results.append(result)

                    if result.success:
                        # 找到成功結果，取消剩餘任務
                        logger.debug(f"First success found: {result.task_id}")
                        for task in pending:
                            task.cancel()

                        if pending:
                            await asyncio.gather(*pending, return_exceptions=True)

                        return results

                tasks = list(pending)

            return results

        except Exception as e:
            logger.error(f"Error in FIRST_SUCCESS mode: {e}")
            for task in tasks:
                task.cancel()
            raise

    async def initialize(self) -> None:
        """初始化適配器 (BuilderAdapter 介面)。"""
        logger.debug(f"Initializing ConcurrentBuilderAdapter: {self._id}")
        self._initialized = True

    async def cleanup(self) -> None:
        """清理資源 (BuilderAdapter 介面)。"""
        logger.debug(f"Cleaning up ConcurrentBuilderAdapter: {self._id}")
        self._tasks.clear()
        self._built = False
        self._workflow = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式。"""
        return {
            "id": self._id,
            "mode": self._mode.value,
            "max_concurrency": self._max_concurrency,
            "timeout_seconds": self._timeout_seconds,
            "task_count": len(self._tasks),
            "tasks": [
                {
                    "id": t.id,
                    "timeout_seconds": t.timeout_seconds,
                    "priority": t.priority,
                    "metadata": t.metadata,
                }
                for t in self._tasks
            ],
            "built": self._built,
        }


# =============================================================================
# 便捷工廠函數
# =============================================================================


def create_all_concurrent(
    id: str,
    executors: Optional[Sequence[Union[ExecutorProtocol, Callable[..., Any]]]] = None,
    **kwargs,
) -> ConcurrentBuilderAdapter:
    """創建 ALL 模式的並行執行適配器。"""
    adapter = ConcurrentBuilderAdapter(id=id, mode=ConcurrentMode.ALL, **kwargs)
    if executors:
        adapter.add_executors(executors)
    return adapter


def create_any_concurrent(
    id: str,
    executors: Optional[Sequence[Union[ExecutorProtocol, Callable[..., Any]]]] = None,
    **kwargs,
) -> ConcurrentBuilderAdapter:
    """創建 ANY 模式的並行執行適配器。"""
    adapter = ConcurrentBuilderAdapter(id=id, mode=ConcurrentMode.ANY, **kwargs)
    if executors:
        adapter.add_executors(executors)
    return adapter


def create_majority_concurrent(
    id: str,
    executors: Optional[Sequence[Union[ExecutorProtocol, Callable[..., Any]]]] = None,
    **kwargs,
) -> ConcurrentBuilderAdapter:
    """創建 MAJORITY 模式的並行執行適配器。"""
    adapter = ConcurrentBuilderAdapter(id=id, mode=ConcurrentMode.MAJORITY, **kwargs)
    if executors:
        adapter.add_executors(executors)
    return adapter


def create_first_success_concurrent(
    id: str,
    executors: Optional[Sequence[Union[ExecutorProtocol, Callable[..., Any]]]] = None,
    **kwargs,
) -> ConcurrentBuilderAdapter:
    """創建 FIRST_SUCCESS 模式的並行執行適配器。"""
    adapter = ConcurrentBuilderAdapter(
        id=id, mode=ConcurrentMode.FIRST_SUCCESS, **kwargs
    )
    if executors:
        adapter.add_executors(executors)
    return adapter
