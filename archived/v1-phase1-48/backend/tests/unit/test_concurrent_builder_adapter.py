# =============================================================================
# Unit Tests for ConcurrentBuilderAdapter
# =============================================================================
# Sprint 14: ConcurrentBuilder 重構
# Phase 3 Feature: P3-F1 (並行執行重構)
#
# 測試範圍:
#   - ConcurrentBuilderAdapter 初始化和配置
#   - 四種執行模式 (ALL, ANY, MAJORITY, FIRST_SUCCESS)
#   - 執行器添加和驗證
#   - 超時處理
#   - 錯誤處理
#   - 結果聚合
# =============================================================================

import asyncio
import pytest
from datetime import datetime
from typing import Any

from src.integrations.agent_framework.builders.concurrent import (
    ConcurrentBuilderAdapter,
    ConcurrentMode,
    ConcurrentTaskConfig,
    TaskResult,
    ConcurrentExecutionResult,
    AllModeAggregator,
    AnyModeAggregator,
    MajorityModeAggregator,
    FirstSuccessAggregator,
    get_aggregator_for_mode,
    create_all_concurrent,
    create_any_concurrent,
    create_majority_concurrent,
    create_first_success_concurrent,
)
from src.integrations.agent_framework.exceptions import (
    ExecutionError,
    ValidationError,
    WorkflowBuildError,
)


# =============================================================================
# 測試輔助函數和 Mock 執行器
# =============================================================================


async def success_executor(input_data: Any) -> dict:
    """成功的執行器 mock。"""
    await asyncio.sleep(0.01)
    return {"status": "success", "input": input_data}


async def failure_executor(input_data: Any) -> dict:
    """失敗的執行器 mock。"""
    await asyncio.sleep(0.01)
    raise ValueError("Intentional failure")


async def slow_executor(input_data: Any) -> dict:
    """慢速執行器 mock (用於超時測試)。"""
    await asyncio.sleep(10)
    return {"status": "slow"}


async def variable_delay_executor(delay: float):
    """可變延遲執行器工廠。"""
    async def executor(input_data: Any) -> dict:
        await asyncio.sleep(delay)
        return {"status": "success", "delay": delay}
    return executor


class MockExecutor:
    """Mock 執行器類，實現 ExecutorProtocol。"""

    def __init__(self, executor_id: str, return_value: Any = None, should_fail: bool = False):
        self._id = executor_id
        self._return_value = return_value or {"result": "ok"}
        self._should_fail = should_fail
        self.call_count = 0

    @property
    def id(self) -> str:
        return self._id

    async def handle(self, input_data: Any, ctx: Any) -> Any:
        self.call_count += 1
        await asyncio.sleep(0.01)
        if self._should_fail:
            raise RuntimeError(f"Mock executor {self._id} failed")
        return self._return_value


# =============================================================================
# ConcurrentMode 測試
# =============================================================================


class TestConcurrentMode:
    """ConcurrentMode 枚舉測試。"""

    def test_mode_values(self):
        """測試模式值。"""
        assert ConcurrentMode.ALL.value == "all"
        assert ConcurrentMode.ANY.value == "any"
        assert ConcurrentMode.MAJORITY.value == "majority"
        assert ConcurrentMode.FIRST_SUCCESS.value == "first_success"

    def test_mode_from_string(self):
        """測試從字符串創建模式。"""
        assert ConcurrentMode("all") == ConcurrentMode.ALL
        assert ConcurrentMode("any") == ConcurrentMode.ANY
        assert ConcurrentMode("majority") == ConcurrentMode.MAJORITY
        assert ConcurrentMode("first_success") == ConcurrentMode.FIRST_SUCCESS


# =============================================================================
# TaskResult 測試
# =============================================================================


class TestTaskResult:
    """TaskResult 數據類測試。"""

    def test_successful_result(self):
        """測試成功結果。"""
        result = TaskResult(
            task_id="task-1",
            success=True,
            result={"data": "value"},
            duration_ms=100,
        )

        assert result.task_id == "task-1"
        assert result.success is True
        assert result.result == {"data": "value"}
        assert result.error is None
        assert result.duration_ms == 100

    def test_failed_result(self):
        """測試失敗結果。"""
        result = TaskResult(
            task_id="task-2",
            success=False,
            error="Something went wrong",
            duration_ms=50,
        )

        assert result.task_id == "task-2"
        assert result.success is False
        assert result.result is None
        assert result.error == "Something went wrong"

    def test_to_dict(self):
        """測試字典轉換。"""
        now = datetime.utcnow()
        result = TaskResult(
            task_id="task-3",
            success=True,
            result={"key": "value"},
            duration_ms=200,
            started_at=now,
            completed_at=now,
        )

        data = result.to_dict()
        assert data["task_id"] == "task-3"
        assert data["success"] is True
        assert data["result"] == {"key": "value"}
        assert data["duration_ms"] == 200
        assert data["started_at"] is not None


# =============================================================================
# ConcurrentExecutionResult 測試
# =============================================================================


class TestConcurrentExecutionResult:
    """ConcurrentExecutionResult 測試。"""

    def test_execution_result_properties(self):
        """測試執行結果屬性。"""
        results = [
            TaskResult(task_id="t1", success=True, result={"a": 1}),
            TaskResult(task_id="t2", success=True, result={"b": 2}),
            TaskResult(task_id="t3", success=False, error="Failed"),
        ]

        execution_result = ConcurrentExecutionResult(
            mode=ConcurrentMode.ALL,
            total_tasks=3,
            completed_count=2,
            failed_count=1,
            task_results=results,
            duration_ms=500,
        )

        assert execution_result.success is True
        assert execution_result.results == {"t1": {"a": 1}, "t2": {"b": 2}}
        assert execution_result.errors == {"t3": "Failed"}

    def test_to_dict_compatibility(self):
        """測試 Phase 2 API 兼容的字典格式。"""
        results = [
            TaskResult(task_id="t1", success=True, result="ok"),
        ]

        execution_result = ConcurrentExecutionResult(
            mode=ConcurrentMode.ALL,
            total_tasks=1,
            completed_count=1,
            failed_count=0,
            task_results=results,
            duration_ms=100,
        )

        data = execution_result.to_dict()
        assert data["mode"] == "all"
        assert data["total_tasks"] == 1
        assert data["completed_tasks"] == 1
        assert data["failed_tasks"] == 0
        assert data["duration_ms"] == 100


# =============================================================================
# Aggregators 測試
# =============================================================================


class TestAggregators:
    """聚合器測試。"""

    @pytest.mark.asyncio
    async def test_all_mode_aggregator(self):
        """測試 ALL 模式聚合器。"""
        aggregator = AllModeAggregator()
        results = [
            TaskResult(task_id="t1", success=True, result="r1", duration_ms=100),
            TaskResult(task_id="t2", success=True, result="r2", duration_ms=150),
            TaskResult(task_id="t3", success=False, error="error", duration_ms=50),
        ]

        execution_result = await aggregator.aggregate(results, 3)

        assert execution_result.mode == ConcurrentMode.ALL
        assert execution_result.total_tasks == 3
        assert execution_result.completed_count == 2
        assert execution_result.failed_count == 1
        assert execution_result.duration_ms == 300  # Sum of all durations

    @pytest.mark.asyncio
    async def test_any_mode_aggregator(self):
        """測試 ANY 模式聚合器。"""
        aggregator = AnyModeAggregator()
        results = [
            TaskResult(task_id="t1", success=True, result="r1", duration_ms=100),
        ]

        execution_result = await aggregator.aggregate(results, 3)

        assert execution_result.mode == ConcurrentMode.ANY
        assert execution_result.completed_count == 1
        assert execution_result.metadata.get("early_termination") is True

    @pytest.mark.asyncio
    async def test_majority_mode_aggregator(self):
        """測試 MAJORITY 模式聚合器。"""
        aggregator = MajorityModeAggregator()
        results = [
            TaskResult(task_id="t1", success=True, result="r1", duration_ms=100),
            TaskResult(task_id="t2", success=True, result="r2", duration_ms=100),
        ]

        execution_result = await aggregator.aggregate(results, 3)

        assert execution_result.mode == ConcurrentMode.MAJORITY
        assert execution_result.metadata.get("majority_threshold") == 2
        assert execution_result.metadata.get("reached_majority") is True

    @pytest.mark.asyncio
    async def test_first_success_aggregator(self):
        """測試 FIRST_SUCCESS 模式聚合器。"""
        aggregator = FirstSuccessAggregator()
        results = [
            TaskResult(task_id="t1", success=False, error="fail", duration_ms=50),
            TaskResult(task_id="t2", success=True, result="r2", duration_ms=100),
        ]

        execution_result = await aggregator.aggregate(results, 3)

        assert execution_result.mode == ConcurrentMode.FIRST_SUCCESS
        assert execution_result.metadata.get("first_success_found") is True
        assert execution_result.metadata.get("failures_before_success") == 1

    def test_get_aggregator_for_mode(self):
        """測試根據模式獲取聚合器。"""
        assert isinstance(get_aggregator_for_mode(ConcurrentMode.ALL), AllModeAggregator)
        assert isinstance(get_aggregator_for_mode(ConcurrentMode.ANY), AnyModeAggregator)
        assert isinstance(get_aggregator_for_mode(ConcurrentMode.MAJORITY), MajorityModeAggregator)
        assert isinstance(get_aggregator_for_mode(ConcurrentMode.FIRST_SUCCESS), FirstSuccessAggregator)


# =============================================================================
# ConcurrentBuilderAdapter 初始化測試
# =============================================================================


class TestConcurrentBuilderAdapterInit:
    """ConcurrentBuilderAdapter 初始化測試。"""

    def test_default_initialization(self):
        """測試預設初始化。"""
        adapter = ConcurrentBuilderAdapter(id="test-adapter")

        assert adapter.id == "test-adapter"
        assert adapter.mode == ConcurrentMode.ALL
        assert adapter.task_count == 0

    def test_custom_initialization(self):
        """測試自定義初始化。"""
        adapter = ConcurrentBuilderAdapter(
            id="custom-adapter",
            mode=ConcurrentMode.MAJORITY,
            max_concurrency=5,
            timeout_seconds=60.0,
        )

        assert adapter.id == "custom-adapter"
        assert adapter.mode == ConcurrentMode.MAJORITY
        assert adapter._max_concurrency == 5
        assert adapter._timeout_seconds == 60.0

    def test_max_concurrency_bounds(self):
        """測試並發數邊界。"""
        # 下限
        adapter_low = ConcurrentBuilderAdapter(id="low", max_concurrency=0)
        assert adapter_low._max_concurrency == 1

        # 上限
        adapter_high = ConcurrentBuilderAdapter(id="high", max_concurrency=200)
        assert adapter_high._max_concurrency == 100

    def test_timeout_bounds(self):
        """測試超時邊界。"""
        # 下限
        adapter_low = ConcurrentBuilderAdapter(id="low", timeout_seconds=0)
        assert adapter_low._timeout_seconds == 1.0

        # 上限
        adapter_high = ConcurrentBuilderAdapter(id="high", timeout_seconds=5000)
        assert adapter_high._timeout_seconds == 3600.0


# =============================================================================
# ConcurrentBuilderAdapter 配置測試
# =============================================================================


class TestConcurrentBuilderAdapterConfiguration:
    """ConcurrentBuilderAdapter 配置測試。"""

    def test_add_executor_with_callable(self):
        """測試添加可調用執行器。"""
        adapter = ConcurrentBuilderAdapter(id="test")
        adapter.add_executor(success_executor, task_id="task-1")

        assert adapter.task_count == 1

    def test_add_executor_with_protocol(self):
        """測試添加 ExecutorProtocol 執行器。"""
        adapter = ConcurrentBuilderAdapter(id="test")
        mock_exec = MockExecutor("mock-1")
        adapter.add_executor(mock_exec)

        assert adapter.task_count == 1

    def test_add_executor_auto_id(self):
        """測試自動生成任務 ID。"""
        adapter = ConcurrentBuilderAdapter(id="test")
        adapter.add_executor(success_executor)
        adapter.add_executor(success_executor)

        assert adapter.task_count == 2

    def test_add_executor_duplicate_id_error(self):
        """測試重複 ID 錯誤。"""
        adapter = ConcurrentBuilderAdapter(id="test")
        adapter.add_executor(success_executor, task_id="task-1")

        with pytest.raises(ValidationError, match="Duplicate task ID"):
            adapter.add_executor(success_executor, task_id="task-1")

    def test_add_executors_batch(self):
        """測試批量添加執行器。"""
        adapter = ConcurrentBuilderAdapter(id="test")
        adapter.add_executors([success_executor, success_executor, success_executor])

        assert adapter.task_count == 3

    def test_method_chaining(self):
        """測試方法鏈式調用。"""
        adapter = (
            ConcurrentBuilderAdapter(id="test")
            .with_mode(ConcurrentMode.ANY)
            .with_timeout(120.0)
            .with_max_concurrency(8)
            .add_executor(success_executor, task_id="t1")
            .add_executor(success_executor, task_id="t2")
        )

        assert adapter.mode == ConcurrentMode.ANY
        assert adapter._timeout_seconds == 120.0
        assert adapter._max_concurrency == 8
        assert adapter.task_count == 2

    def test_cannot_modify_after_build(self):
        """測試構建後不能修改配置。"""
        adapter = ConcurrentBuilderAdapter(id="test")
        adapter.add_executor(success_executor)
        adapter.build()

        with pytest.raises(ValidationError, match="Cannot add executor after build"):
            adapter.add_executor(success_executor)

        with pytest.raises(ValidationError, match="Cannot change mode after build"):
            adapter.with_mode(ConcurrentMode.ANY)


# =============================================================================
# ConcurrentBuilderAdapter Build 測試
# =============================================================================


class TestConcurrentBuilderAdapterBuild:
    """ConcurrentBuilderAdapter 構建測試。"""

    def test_build_success(self):
        """測試成功構建。"""
        adapter = ConcurrentBuilderAdapter(id="test")
        adapter.add_executor(success_executor)
        result = adapter.build()

        assert result is adapter
        assert adapter._built is True

    def test_build_no_tasks_error(self):
        """測試無任務構建錯誤。"""
        adapter = ConcurrentBuilderAdapter(id="test")

        with pytest.raises(WorkflowBuildError, match="No tasks configured"):
            adapter.build()

    def test_double_build_warning(self):
        """測試重複構建警告。"""
        adapter = ConcurrentBuilderAdapter(id="test")
        adapter.add_executor(success_executor)
        adapter.build()

        # 第二次構建應該返回 self，不報錯
        result = adapter.build()
        assert result is adapter

    def test_to_dict(self):
        """測試字典轉換。"""
        adapter = ConcurrentBuilderAdapter(id="test", mode=ConcurrentMode.ALL)
        adapter.add_executor(success_executor, task_id="task-1")

        data = adapter.to_dict()

        assert data["id"] == "test"
        assert data["mode"] == "all"
        assert data["task_count"] == 1
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["id"] == "task-1"


# =============================================================================
# ConcurrentBuilderAdapter 執行測試 - ALL 模式
# =============================================================================


class TestConcurrentBuilderAdapterAllMode:
    """ALL 模式執行測試。"""

    @pytest.mark.asyncio
    async def test_all_success(self):
        """測試所有任務成功。"""
        adapter = ConcurrentBuilderAdapter(id="test", mode=ConcurrentMode.ALL)
        adapter.add_executor(success_executor, task_id="t1")
        adapter.add_executor(success_executor, task_id="t2")
        adapter.add_executor(success_executor, task_id="t3")

        result = await adapter.run({"input": "test"})

        assert result.mode == ConcurrentMode.ALL
        assert result.total_tasks == 3
        assert result.completed_count == 3
        assert result.failed_count == 0
        assert result.success is True

    @pytest.mark.asyncio
    async def test_partial_failure(self):
        """測試部分失敗。"""
        adapter = ConcurrentBuilderAdapter(id="test", mode=ConcurrentMode.ALL)
        adapter.add_executor(success_executor, task_id="t1")
        adapter.add_executor(failure_executor, task_id="t2")
        adapter.add_executor(success_executor, task_id="t3")

        result = await adapter.run({"input": "test"})

        assert result.total_tasks == 3
        assert result.completed_count == 2
        assert result.failed_count == 1
        assert "t2" in result.errors

    @pytest.mark.asyncio
    async def test_with_mock_executor(self):
        """測試使用 MockExecutor。"""
        mock1 = MockExecutor("exec-1", {"value": 1})
        mock2 = MockExecutor("exec-2", {"value": 2})

        adapter = ConcurrentBuilderAdapter(id="test", mode=ConcurrentMode.ALL)
        adapter.add_executor(mock1)
        adapter.add_executor(mock2)

        result = await adapter.run(None)

        assert result.completed_count == 2
        assert mock1.call_count == 1
        assert mock2.call_count == 1


# =============================================================================
# ConcurrentBuilderAdapter 執行測試 - ANY 模式
# =============================================================================


class TestConcurrentBuilderAdapterAnyMode:
    """ANY 模式執行測試。"""

    @pytest.mark.asyncio
    async def test_any_returns_first_complete(self):
        """測試返回第一個完成的任務。"""
        # 創建不同延遲的執行器
        async def fast_executor(input_data):
            await asyncio.sleep(0.01)
            return {"status": "fast"}

        async def slow_executor(input_data):
            await asyncio.sleep(0.5)
            return {"status": "slow"}

        adapter = ConcurrentBuilderAdapter(id="test", mode=ConcurrentMode.ANY)
        adapter.add_executor(slow_executor, task_id="slow")
        adapter.add_executor(fast_executor, task_id="fast")

        result = await adapter.run(None)

        # ANY 模式應該只返回一個結果
        assert len(result.task_results) == 1
        assert result.task_results[0].task_id == "fast"


# =============================================================================
# ConcurrentBuilderAdapter 執行測試 - MAJORITY 模式
# =============================================================================


class TestConcurrentBuilderAdapterMajorityMode:
    """MAJORITY 模式執行測試。"""

    @pytest.mark.asyncio
    async def test_majority_returns_after_threshold(self):
        """測試達到多數後返回。"""
        async def fast_executor(input_data):
            await asyncio.sleep(0.01)
            return {"status": "fast"}

        async def slow_executor(input_data):
            await asyncio.sleep(1.0)
            return {"status": "slow"}

        adapter = ConcurrentBuilderAdapter(id="test", mode=ConcurrentMode.MAJORITY)
        adapter.add_executor(fast_executor, task_id="fast1")
        adapter.add_executor(fast_executor, task_id="fast2")
        adapter.add_executor(slow_executor, task_id="slow")

        result = await adapter.run(None)

        # 3 個任務，多數 = 2
        # 應該在 2 個快任務完成後返回
        assert len(result.task_results) >= 2


# =============================================================================
# ConcurrentBuilderAdapter 執行測試 - FIRST_SUCCESS 模式
# =============================================================================


class TestConcurrentBuilderAdapterFirstSuccessMode:
    """FIRST_SUCCESS 模式執行測試。"""

    @pytest.mark.asyncio
    async def test_first_success_skips_failures(self):
        """測試跳過失敗找到第一個成功。"""
        async def quick_fail(input_data):
            await asyncio.sleep(0.01)
            raise ValueError("Quick fail")

        async def delayed_success(input_data):
            await asyncio.sleep(0.05)
            return {"status": "success"}

        adapter = ConcurrentBuilderAdapter(id="test", mode=ConcurrentMode.FIRST_SUCCESS)
        adapter.add_executor(quick_fail, task_id="fail1")
        adapter.add_executor(delayed_success, task_id="success")
        adapter.add_executor(quick_fail, task_id="fail2")

        result = await adapter.run(None)

        # 應該找到 success 任務
        successful_tasks = [r for r in result.task_results if r.success]
        assert len(successful_tasks) == 1
        assert successful_tasks[0].task_id == "success"


# =============================================================================
# ConcurrentBuilderAdapter 超時測試
# =============================================================================


class TestConcurrentBuilderAdapterTimeout:
    """超時處理測試。"""

    @pytest.mark.asyncio
    async def test_task_timeout(self):
        """測試任務超時。"""
        adapter = ConcurrentBuilderAdapter(
            id="test",
            mode=ConcurrentMode.ALL,
            timeout_seconds=0.1,
        )
        adapter.add_executor(slow_executor, task_id="slow")

        result = await adapter.run(None)

        assert result.failed_count == 1
        assert "timeout" in result.errors.get("slow", "").lower()

    @pytest.mark.asyncio
    async def test_task_specific_timeout(self):
        """測試任務特定超時。"""
        adapter = ConcurrentBuilderAdapter(
            id="test",
            mode=ConcurrentMode.ALL,
            timeout_seconds=10.0,  # 全局超時較長
        )
        adapter.add_executor(
            slow_executor,
            task_id="slow",
            timeout_seconds=0.1,  # 任務超時較短
        )

        result = await adapter.run(None)

        assert result.failed_count == 1
        assert "timeout" in result.errors.get("slow", "").lower()


# =============================================================================
# 便捷工廠函數測試
# =============================================================================


class TestFactoryFunctions:
    """便捷工廠函數測試。"""

    def test_create_all_concurrent(self):
        """測試創建 ALL 模式適配器。"""
        adapter = create_all_concurrent("test", [success_executor, success_executor])

        assert adapter.mode == ConcurrentMode.ALL
        assert adapter.task_count == 2

    def test_create_any_concurrent(self):
        """測試創建 ANY 模式適配器。"""
        adapter = create_any_concurrent("test")

        assert adapter.mode == ConcurrentMode.ANY

    def test_create_majority_concurrent(self):
        """測試創建 MAJORITY 模式適配器。"""
        adapter = create_majority_concurrent("test")

        assert adapter.mode == ConcurrentMode.MAJORITY

    def test_create_first_success_concurrent(self):
        """測試創建 FIRST_SUCCESS 模式適配器。"""
        adapter = create_first_success_concurrent("test")

        assert adapter.mode == ConcurrentMode.FIRST_SUCCESS


# =============================================================================
# 生命週期測試
# =============================================================================


class TestLifecycle:
    """生命週期測試。"""

    @pytest.mark.asyncio
    async def test_initialize(self):
        """測試初始化。"""
        adapter = ConcurrentBuilderAdapter(id="test")
        await adapter.initialize()

        assert adapter._initialized is True

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """測試清理。"""
        adapter = ConcurrentBuilderAdapter(id="test")
        adapter.add_executor(success_executor)
        adapter.build()

        await adapter.cleanup()

        assert adapter.task_count == 0
        assert adapter._built is False

    @pytest.mark.asyncio
    async def test_auto_build_on_run(self):
        """測試執行時自動構建。"""
        adapter = ConcurrentBuilderAdapter(id="test")
        adapter.add_executor(success_executor)

        # 不調用 build()，直接 run()
        result = await adapter.run(None)

        assert adapter._built is True
        assert result.completed_count == 1
