# =============================================================================
# Concurrent API Adapter Service
# =============================================================================
# Sprint 14: ConcurrentBuilder 重構
# Phase 3 Feature: P3-F1 (並行執行重構)
#
# 此模組提供 API 層與新的 ConcurrentBuilderAdapter 之間的適配服務。
# 主要功能:
#   - 將 API 請求轉換為 Adapter 調用
#   - 維持向後兼容的 API schema
#   - 整合狀態管理
#   - 提供遷移路徑
#
# 使用方式:
#   - 直接在 routes.py 中注入 ConcurrentAPIService
#   - 通過 use_adapter 參數控制使用新舊實現
# =============================================================================

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

from src.integrations.agent_framework.builders import (
    ConcurrentBuilderAdapter,
    ConcurrentMode as AdapterMode,
    ConcurrentExecutionResult,
    ConcurrentExecutorAdapter,
    ConcurrentTask,
    BranchStatus,
    ParallelBranch,
    FanOutRouter,
    FanOutConfig,
    FanOutStrategy,
    FanInAggregator,
    FanInConfig,
    FanInStrategy,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Data Transfer Objects
# =============================================================================


@dataclass
class ExecuteRequest:
    """並行執行請求 DTO。"""

    workflow_id: Optional[UUID] = None
    mode: str = "all"
    timeout_seconds: int = 300
    max_concurrency: int = 10
    tasks: List[Dict[str, Any]] = field(default_factory=list)
    input_data: Optional[Dict[str, Any]] = None
    fan_out_strategy: str = "broadcast"
    fan_in_strategy: str = "collect_all"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecuteResponse:
    """並行執行響應 DTO。"""

    execution_id: UUID
    status: str
    mode: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    results: Dict[str, Any]
    errors: Dict[str, Any]
    duration_ms: int
    branches: List[Dict[str, Any]]
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BranchInfo:
    """分支信息 DTO。"""

    branch_id: str
    executor_id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    result: Any = None
    error: Optional[str] = None


# =============================================================================
# Concurrent API Service
# =============================================================================


class ConcurrentAPIService:
    """
    並行執行 API 服務。

    提供與 ConcurrentBuilderAdapter 整合的 API 服務，
    同時支持 Phase 2 ConcurrentExecutor 的向後兼容。

    Features:
        - 支持新舊兩種執行器
        - 統一的 API 介面
        - 狀態追蹤和管理
        - 遷移路徑支持

    Example:
        service = ConcurrentAPIService()

        # 使用新的 Adapter
        response = await service.execute(
            request=ExecuteRequest(
                mode="all",
                tasks=[...],
                timeout_seconds=60,
            ),
            use_adapter=True,
        )
    """

    def __init__(self):
        """Initialize service."""
        self._executions: Dict[UUID, Dict[str, Any]] = {}
        self._task_executors: Dict[str, Callable] = {}
        logger.info("ConcurrentAPIService initialized")

    def register_task_executor(
        self,
        executor_id: str,
        executor: Callable,
    ) -> None:
        """
        註冊任務執行器。

        Args:
            executor_id: 執行器 ID
            executor: 異步執行函數
        """
        self._task_executors[executor_id] = executor
        logger.debug(f"Registered task executor: {executor_id}")

    async def execute(
        self,
        request: ExecuteRequest,
        use_adapter: bool = True,
    ) -> ExecuteResponse:
        """
        執行並行任務。

        Args:
            request: 執行請求
            use_adapter: 是否使用新的 Adapter (True) 或 Phase 2 實現 (False)

        Returns:
            執eResponse 包含執行結果
        """
        execution_id = uuid4()
        started_at = datetime.now(timezone.utc)

        logger.info(
            f"Starting concurrent execution {execution_id}, "
            f"mode={request.mode}, use_adapter={use_adapter}"
        )

        try:
            if use_adapter:
                result = await self._execute_with_adapter(
                    execution_id, request, started_at
                )
            else:
                result = await self._execute_with_legacy(
                    execution_id, request, started_at
                )

            # Store execution for later retrieval
            self._executions[execution_id] = {
                "request": request,
                "response": result,
                "use_adapter": use_adapter,
            }

            return result

        except Exception as e:
            logger.error(f"Concurrent execution {execution_id} failed: {e}")
            completed_at = datetime.now(timezone.utc)
            duration_ms = int(
                (completed_at - started_at).total_seconds() * 1000
            )

            return ExecuteResponse(
                execution_id=execution_id,
                status="failed",
                mode=request.mode,
                total_tasks=len(request.tasks),
                completed_tasks=0,
                failed_tasks=len(request.tasks),
                results={},
                errors={"execution": str(e)},
                duration_ms=duration_ms,
                branches=[],
                started_at=started_at,
                completed_at=completed_at,
            )

    async def _execute_with_adapter(
        self,
        execution_id: UUID,
        request: ExecuteRequest,
        started_at: datetime,
    ) -> ExecuteResponse:
        """
        使用新的 ConcurrentBuilderAdapter 執行。
        """
        # Convert mode
        mode_map = {
            "all": AdapterMode.ALL,
            "any": AdapterMode.ANY,
            "majority": AdapterMode.MAJORITY,
            "first_success": AdapterMode.FIRST_SUCCESS,
        }
        mode = mode_map.get(request.mode.lower(), AdapterMode.ALL)

        # Create adapter
        adapter = ConcurrentBuilderAdapter(
            id=str(execution_id),
            mode=mode,
            max_concurrency=request.max_concurrency,
            timeout_seconds=float(request.timeout_seconds),
        )

        # Add executors for each task
        branches: List[Dict[str, Any]] = []
        for i, task_config in enumerate(request.tasks):
            task_id = task_config.get("id", f"task-{i}")
            executor_id = task_config.get("executor_id", f"executor-{i}")

            # Get or create task executor
            if executor_id in self._task_executors:
                executor = self._task_executors[executor_id]
            else:
                # Create a default executor
                executor = self._create_default_executor(task_config)

            adapter.add_executor(
                executor,
                task_id=task_id,
                timeout_seconds=task_config.get("timeout"),
                metadata=task_config.get("metadata", {}),
            )

            branches.append({
                "branch_id": task_id,
                "executor_id": executor_id,
                "status": "pending",
            })

        # Execute
        input_data = request.input_data or {}
        result = await adapter.run(input_data)

        completed_at = datetime.now(timezone.utc)

        # Convert result to response format
        return ExecuteResponse(
            execution_id=execution_id,
            status="completed" if result.completed_count > 0 else "failed",
            mode=request.mode,
            total_tasks=result.total_tasks,
            completed_tasks=result.completed_count,
            failed_tasks=result.failed_count,
            results={
                tr.task_id: tr.result
                for tr in result.task_results
                if tr.success
            },
            errors={
                tr.task_id: tr.error
                for tr in result.task_results
                if not tr.success and tr.error
            },
            duration_ms=result.duration_ms,
            branches=self._convert_task_results_to_branches(result),
            started_at=started_at,
            completed_at=completed_at,
        )

    async def _execute_with_legacy(
        self,
        execution_id: UUID,
        request: ExecuteRequest,
        started_at: datetime,
    ) -> ExecuteResponse:
        """
        使用 Phase 2 ConcurrentExecutorAdapter (遷移層) 執行。
        """
        from src.integrations.agent_framework.builders.concurrent_migration import (
            ConcurrentMode,
            ConcurrentTask,
            ConcurrentExecutorAdapter,
        )

        # Convert mode
        mode_map = {
            "all": ConcurrentMode.ALL,
            "any": ConcurrentMode.ANY,
            "majority": ConcurrentMode.MAJORITY,
            "first_success": ConcurrentMode.FIRST_SUCCESS,
        }
        mode = mode_map.get(request.mode.lower(), ConcurrentMode.ALL)

        # Create tasks
        tasks = []
        for i, task_config in enumerate(request.tasks):
            task_id = task_config.get("id", f"task-{i}")
            executor_id = task_config.get("executor_id", f"executor-{i}")

            task = ConcurrentTask(
                id=task_id,
                executor_id=executor_id,
                input_data=task_config.get("input_data", {}),
                timeout=task_config.get("timeout"),
                priority=task_config.get("priority", 0),
                metadata=task_config.get("metadata", {}),
            )
            tasks.append(task)

        # Create executor
        executor = ConcurrentExecutorAdapter(
            id=str(execution_id),
            tasks=tasks,
            mode=mode,
            max_concurrency=request.max_concurrency,
            timeout=request.timeout_seconds,
        )

        # Define task executor function
        async def task_executor(task: ConcurrentTask) -> Any:
            if task.executor_id in self._task_executors:
                return await self._task_executors[task.executor_id](task)
            else:
                # Default: return input data as result
                return {"task_id": task.id, "input": task.input_data}

        # Execute
        result = await executor.execute(task_executor)

        completed_at = datetime.now(timezone.utc)

        # Convert branches
        branches = [
            {
                "branch_id": branch.id,
                "executor_id": branch.executor_id,
                "status": branch.status.value,
                "started_at": branch.started_at.isoformat() if branch.started_at else None,
                "completed_at": branch.completed_at.isoformat() if branch.completed_at else None,
                "duration_ms": branch.duration_ms,
                "result": branch.result,
                "error": branch.error,
            }
            for branch in executor.get_all_branches()
        ]

        return ExecuteResponse(
            execution_id=execution_id,
            status="completed" if result["completed_tasks"] > 0 else "failed",
            mode=request.mode,
            total_tasks=result["total_tasks"],
            completed_tasks=result["completed_tasks"],
            failed_tasks=result["failed_tasks"],
            results=result.get("results", {}),
            errors=result.get("errors", {}),
            duration_ms=result["duration_ms"],
            branches=branches,
            started_at=started_at,
            completed_at=completed_at,
        )

    def _create_default_executor(
        self,
        task_config: Dict[str, Any],
    ) -> Callable:
        """創建默認執行器。"""

        async def default_executor(input_data: Any) -> Dict[str, Any]:
            """默認執行器 - 返回輸入數據。"""
            return {
                "status": "completed",
                "task_id": task_config.get("id"),
                "input": input_data,
            }

        return default_executor

    def _convert_task_results_to_branches(
        self,
        result: ConcurrentExecutionResult,
    ) -> List[Dict[str, Any]]:
        """將 TaskResult 列表轉換為分支信息。"""
        return [
            {
                "branch_id": tr.task_id,
                "executor_id": tr.task_id,  # 在 adapter 中沒有分開
                "status": "completed" if tr.success else "failed",
                "started_at": tr.started_at.isoformat() if tr.started_at else None,
                "completed_at": tr.completed_at.isoformat() if tr.completed_at else None,
                "duration_ms": int(tr.duration_ms) if tr.duration_ms else None,
                "result": tr.result,
                "error": tr.error,
            }
            for tr in result.task_results
        ]

    def get_execution(self, execution_id: UUID) -> Optional[Dict[str, Any]]:
        """
        獲取執行記錄。

        Args:
            execution_id: 執行 ID

        Returns:
            執行記錄或 None
        """
        return self._executions.get(execution_id)

    def list_executions(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        列出所有執行記錄。

        Args:
            limit: 返回數量限制
            offset: 偏移量

        Returns:
            執行記錄列表
        """
        executions = list(self._executions.items())
        return [
            {"execution_id": eid, **data}
            for eid, data in executions[offset : offset + limit]
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """
        獲取執行統計。

        Returns:
            統計數據字典
        """
        total = len(self._executions)
        adapter_count = sum(
            1 for e in self._executions.values() if e.get("use_adapter")
        )
        legacy_count = total - adapter_count

        completed = sum(
            1
            for e in self._executions.values()
            if e.get("response") and e["response"].status == "completed"
        )

        return {
            "total_executions": total,
            "adapter_executions": adapter_count,
            "legacy_executions": legacy_count,
            "completed_executions": completed,
            "failed_executions": total - completed,
            "registered_executors": len(self._task_executors),
        }


# =============================================================================
# Singleton Instance
# =============================================================================

_service_instance: Optional[ConcurrentAPIService] = None


def get_concurrent_api_service() -> ConcurrentAPIService:
    """
    獲取 ConcurrentAPIService 單例。

    Returns:
        ConcurrentAPIService 實例
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = ConcurrentAPIService()
    return _service_instance


def reset_concurrent_api_service() -> None:
    """重置服務實例（用於測試）。"""
    global _service_instance
    _service_instance = None


__all__ = [
    "ExecuteRequest",
    "ExecuteResponse",
    "BranchInfo",
    "ConcurrentAPIService",
    "get_concurrent_api_service",
    "reset_concurrent_api_service",
]
