# =============================================================================
# Unit Tests for ConcurrentExecutor Migration Layer
# =============================================================================
# Sprint 14: ConcurrentBuilder 重構
# Phase 3 Feature: P3-F1 (並行執行重構)
#
# 測試範圍:
#   - ConcurrentExecutorAdapter 兼容 Phase 2 API
#   - ConcurrentTask, ConcurrentResult 數據結構遷移
#   - BranchStatus, ParallelBranch 狀態管理
#   - migrate_concurrent_executor 輔助函數
#   - 工廠函數 create_all_executor, create_any_executor 等
# =============================================================================

import asyncio
import pytest
from datetime import datetime, timezone
from typing import Any

from src.integrations.agent_framework.builders.concurrent_migration import (
    ConcurrentMode,
    ConcurrentTask,
    ConcurrentResult,
    BranchStatus,
    ParallelBranch,
    ConcurrentExecutorAdapter,
    create_all_executor,
    create_any_executor,
    create_majority_executor,
    create_first_success_executor,
    migrate_concurrent_executor,
)


# =============================================================================
# 測試輔助函數
# =============================================================================


async def success_task_executor(task: ConcurrentTask) -> dict:
    """成功的任務執行器 mock。"""
    await asyncio.sleep(0.01)
    return {"status": "success", "task_id": task.id, "input": task.input_data}


async def failure_task_executor(task: ConcurrentTask) -> dict:
    """失敗的任務執行器 mock。"""
    await asyncio.sleep(0.01)
    raise ValueError(f"Task {task.id} failed intentionally")


async def variable_executor(task: ConcurrentTask) -> dict:
    """可變行為的執行器 - 根據任務 ID 決定成功或失敗。"""
    await asyncio.sleep(0.01)
    if "fail" in task.id:
        raise ValueError(f"Task {task.id} failed")
    return {"status": "success", "task_id": task.id}


# =============================================================================
# ConcurrentMode 測試
# =============================================================================


class TestConcurrentMode:
    """ConcurrentMode 枚舉測試。"""

    def test_mode_values(self):
        """測試模式值與 Phase 2 兼容。"""
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
# ConcurrentTask 測試
# =============================================================================


class TestConcurrentTask:
    """ConcurrentTask 數據類測試。"""

    def test_basic_creation(self):
        """測試基本創建。"""
        task = ConcurrentTask(
            id="task-1",
            executor_id="exec-1",
            input_data={"key": "value"},
        )

        assert task.id == "task-1"
        assert task.executor_id == "exec-1"
        assert task.input_data == {"key": "value"}
        assert task.timeout is None
        assert task.priority == 0

    def test_with_all_fields(self):
        """測試所有字段。"""
        task = ConcurrentTask(
            id="task-2",
            executor_id="exec-2",
            input_data={"data": 123},
            timeout=30,
            priority=5,
            metadata={"tag": "test"},
        )

        assert task.id == "task-2"
        assert task.timeout == 30
        assert task.priority == 5
        assert task.metadata == {"tag": "test"}

    def test_to_dict(self):
        """測試字典轉換。"""
        task = ConcurrentTask(
            id="task-3",
            executor_id="exec-3",
            input_data={"value": 100},
            priority=1,
        )

        data = task.to_dict()
        assert data["id"] == "task-3"
        assert data["executor_id"] == "exec-3"
        assert data["input_data"] == {"value": 100}
        assert data["priority"] == 1


# =============================================================================
# ConcurrentResult 測試
# =============================================================================


class TestConcurrentResult:
    """ConcurrentResult 數據類測試。"""

    def test_successful_result(self):
        """測試成功結果。"""
        result = ConcurrentResult(
            task_id="task-1",
            success=True,
            result={"output": "data"},
            execution_time_ms=150,
        )

        assert result.task_id == "task-1"
        assert result.success is True
        assert result.result == {"output": "data"}
        assert result.error is None
        assert result.execution_time_ms == 150

    def test_failed_result(self):
        """測試失敗結果。"""
        result = ConcurrentResult(
            task_id="task-2",
            success=False,
            error="Something went wrong",
            execution_time_ms=50,
        )

        assert result.task_id == "task-2"
        assert result.success is False
        assert result.result is None
        assert result.error == "Something went wrong"

    def test_to_dict(self):
        """測試字典轉換 (Phase 2 兼容格式)。"""
        now = datetime.now(timezone.utc)
        result = ConcurrentResult(
            task_id="task-3",
            success=True,
            result={"value": 42},
            execution_time_ms=200,
            started_at=now,
            completed_at=now,
        )

        data = result.to_dict()
        assert data["task_id"] == "task-3"
        assert data["success"] is True
        assert data["result"] == {"value": 42}
        assert data["execution_time_ms"] == 200


# =============================================================================
# BranchStatus 測試
# =============================================================================


class TestBranchStatus:
    """BranchStatus 枚舉測試。"""

    def test_status_values(self):
        """測試狀態值。"""
        assert BranchStatus.PENDING.value == "pending"
        assert BranchStatus.RUNNING.value == "running"
        assert BranchStatus.COMPLETED.value == "completed"
        assert BranchStatus.FAILED.value == "failed"
        assert BranchStatus.CANCELLED.value == "cancelled"
        assert BranchStatus.TIMED_OUT.value == "timed_out"

    def test_terminal_statuses(self):
        """測試終態狀態。"""
        terminal = [BranchStatus.COMPLETED, BranchStatus.FAILED,
                    BranchStatus.CANCELLED, BranchStatus.TIMED_OUT]
        non_terminal = [BranchStatus.PENDING, BranchStatus.RUNNING]

        for status in terminal:
            assert status.is_terminal is True

        for status in non_terminal:
            assert status.is_terminal is False


# =============================================================================
# ParallelBranch 測試
# =============================================================================


class TestParallelBranch:
    """ParallelBranch 數據類測試。"""

    def test_basic_creation(self):
        """測試基本創建。"""
        branch = ParallelBranch(
            id="branch-1",
            executor_id="exec-1",
        )

        assert branch.id == "branch-1"
        assert branch.executor_id == "exec-1"
        assert branch.status == BranchStatus.PENDING
        assert branch.is_terminal is False

    def test_terminal_property(self):
        """測試終態屬性。"""
        branch = ParallelBranch(id="b1", executor_id="e1")
        assert branch.is_terminal is False

        branch.status = BranchStatus.COMPLETED
        assert branch.is_terminal is True

        branch.status = BranchStatus.FAILED
        assert branch.is_terminal is True

    def test_duration_ms(self):
        """測試持續時間計算。"""
        now = datetime.now(timezone.utc)
        branch = ParallelBranch(
            id="b1",
            executor_id="e1",
            started_at=now,
        )

        # 沒有完成時間時不返回持續時間
        assert branch.duration_ms is None

        # 設置完成時間
        from datetime import timedelta
        branch.completed_at = now + timedelta(milliseconds=500)

        assert branch.duration_ms is not None
        assert branch.duration_ms >= 500

    def test_to_dict(self):
        """測試字典轉換。"""
        branch = ParallelBranch(
            id="branch-1",
            executor_id="exec-1",
            status=BranchStatus.COMPLETED,
            result={"data": "value"},
        )

        data = branch.to_dict()
        assert data["id"] == "branch-1"
        assert data["executor_id"] == "exec-1"
        assert data["status"] == "completed"
        assert data["result"] == {"data": "value"}


# =============================================================================
# ConcurrentExecutorAdapter 初始化測試
# =============================================================================


class TestConcurrentExecutorAdapterInit:
    """ConcurrentExecutorAdapter 初始化測試。"""

    def test_basic_initialization(self):
        """測試基本初始化。"""
        tasks = [
            ConcurrentTask(id="t1", executor_id="e1", input_data={}),
            ConcurrentTask(id="t2", executor_id="e2", input_data={}),
        ]

        adapter = ConcurrentExecutorAdapter(
            id="test-executor",
            tasks=tasks,
        )

        assert adapter.id == "test-executor"
        assert len(adapter._tasks) == 2
        assert adapter._mode == ConcurrentMode.ALL

    def test_with_all_options(self):
        """測試所有選項。"""
        tasks = [ConcurrentTask(id="t1", executor_id="e1", input_data={})]

        adapter = ConcurrentExecutorAdapter(
            id="test-executor",
            tasks=tasks,
            mode=ConcurrentMode.MAJORITY,
            max_concurrency=5,
            timeout=60,
        )

        assert adapter._mode == ConcurrentMode.MAJORITY
        assert adapter._max_concurrency == 5
        assert adapter._timeout == 60

    def test_empty_tasks_allowed(self):
        """測試允許空任務列表。"""
        adapter = ConcurrentExecutorAdapter(
            id="empty-executor",
            tasks=[],
        )

        assert len(adapter._tasks) == 0


# =============================================================================
# ConcurrentExecutorAdapter 執行測試
# =============================================================================


class TestConcurrentExecutorAdapterExecution:
    """ConcurrentExecutorAdapter 執行測試。"""

    @pytest.mark.asyncio
    async def test_execute_all_success(self):
        """測試 ALL 模式全部成功。"""
        tasks = [
            ConcurrentTask(id="t1", executor_id="e1", input_data={"value": 1}),
            ConcurrentTask(id="t2", executor_id="e2", input_data={"value": 2}),
            ConcurrentTask(id="t3", executor_id="e3", input_data={"value": 3}),
        ]

        adapter = ConcurrentExecutorAdapter(
            id="test",
            tasks=tasks,
            mode=ConcurrentMode.ALL,
        )

        result = await adapter.execute(success_task_executor)

        assert result["total_tasks"] == 3
        assert result["completed_tasks"] == 3
        assert result["failed_tasks"] == 0
        assert len(result["results"]) == 3

    @pytest.mark.asyncio
    async def test_execute_partial_failure(self):
        """測試部分失敗。"""
        tasks = [
            ConcurrentTask(id="success-1", executor_id="e1", input_data={}),
            ConcurrentTask(id="fail-1", executor_id="e2", input_data={}),
            ConcurrentTask(id="success-2", executor_id="e3", input_data={}),
        ]

        adapter = ConcurrentExecutorAdapter(
            id="test",
            tasks=tasks,
            mode=ConcurrentMode.ALL,
        )

        result = await adapter.execute(variable_executor)

        assert result["total_tasks"] == 3
        assert result["completed_tasks"] == 2
        assert result["failed_tasks"] == 1
        assert "fail-1" in result["errors"]

    @pytest.mark.asyncio
    async def test_execute_any_mode(self):
        """測試 ANY 模式。"""
        tasks = [
            ConcurrentTask(id="t1", executor_id="e1", input_data={}),
            ConcurrentTask(id="t2", executor_id="e2", input_data={}),
        ]

        adapter = ConcurrentExecutorAdapter(
            id="test",
            tasks=tasks,
            mode=ConcurrentMode.ANY,
        )

        result = await adapter.execute(success_task_executor)

        # ANY 模式至少應該有一個結果
        assert result["completed_tasks"] >= 1

    @pytest.mark.asyncio
    async def test_execute_majority_mode(self):
        """測試 MAJORITY 模式。"""
        tasks = [
            ConcurrentTask(id="t1", executor_id="e1", input_data={}),
            ConcurrentTask(id="t2", executor_id="e2", input_data={}),
            ConcurrentTask(id="t3", executor_id="e3", input_data={}),
        ]

        adapter = ConcurrentExecutorAdapter(
            id="test",
            tasks=tasks,
            mode=ConcurrentMode.MAJORITY,
        )

        result = await adapter.execute(success_task_executor)

        # MAJORITY 模式應該有多數完成
        assert result["completed_tasks"] >= 2

    @pytest.mark.asyncio
    async def test_execute_first_success_mode(self):
        """測試 FIRST_SUCCESS 模式。"""
        tasks = [
            ConcurrentTask(id="fail-1", executor_id="e1", input_data={}),
            ConcurrentTask(id="success-1", executor_id="e2", input_data={}),
            ConcurrentTask(id="fail-2", executor_id="e3", input_data={}),
        ]

        adapter = ConcurrentExecutorAdapter(
            id="test",
            tasks=tasks,
            mode=ConcurrentMode.FIRST_SUCCESS,
        )

        result = await adapter.execute(variable_executor)

        # 應該找到至少一個成功
        assert result["completed_tasks"] >= 1


# =============================================================================
# ConcurrentExecutorAdapter 狀態管理測試
# =============================================================================


class TestConcurrentExecutorAdapterState:
    """ConcurrentExecutorAdapter 狀態管理測試。"""

    @pytest.mark.asyncio
    async def test_get_all_branches(self):
        """測試獲取所有分支。"""
        tasks = [
            ConcurrentTask(id="t1", executor_id="e1", input_data={}),
            ConcurrentTask(id="t2", executor_id="e2", input_data={}),
        ]

        adapter = ConcurrentExecutorAdapter(
            id="test",
            tasks=tasks,
        )

        await adapter.execute(success_task_executor)

        branches = adapter.get_all_branches()
        assert len(branches) == 2

        # 驗證分支狀態
        for branch in branches:
            assert branch.status in [BranchStatus.COMPLETED, BranchStatus.FAILED]

    @pytest.mark.asyncio
    async def test_get_branch_by_id(self):
        """測試根據 ID 獲取分支。"""
        tasks = [
            ConcurrentTask(id="target-task", executor_id="e1", input_data={}),
        ]

        adapter = ConcurrentExecutorAdapter(
            id="test",
            tasks=tasks,
        )

        await adapter.execute(success_task_executor)

        branch = adapter.get_branch("target-task")
        assert branch is not None
        assert branch.id == "target-task"

    def test_get_nonexistent_branch(self):
        """測試獲取不存在的分支。"""
        adapter = ConcurrentExecutorAdapter(
            id="test",
            tasks=[],
        )

        branch = adapter.get_branch("nonexistent")
        assert branch is None


# =============================================================================
# 工廠函數測試
# =============================================================================


class TestFactoryFunctions:
    """工廠函數測試。"""

    def test_create_all_executor(self):
        """測試創建 ALL 模式執行器。"""
        tasks = [ConcurrentTask(id="t1", executor_id="e1", input_data={})]
        executor = create_all_executor("test", tasks)

        assert executor._mode == ConcurrentMode.ALL

    def test_create_any_executor(self):
        """測試創建 ANY 模式執行器。"""
        tasks = [ConcurrentTask(id="t1", executor_id="e1", input_data={})]
        executor = create_any_executor("test", tasks)

        assert executor._mode == ConcurrentMode.ANY

    def test_create_majority_executor(self):
        """測試創建 MAJORITY 模式執行器。"""
        tasks = [ConcurrentTask(id="t1", executor_id="e1", input_data={})]
        executor = create_majority_executor("test", tasks)

        assert executor._mode == ConcurrentMode.MAJORITY

    def test_create_first_success_executor(self):
        """測試創建 FIRST_SUCCESS 模式執行器。"""
        tasks = [ConcurrentTask(id="t1", executor_id="e1", input_data={})]
        executor = create_first_success_executor("test", tasks)

        assert executor._mode == ConcurrentMode.FIRST_SUCCESS


# =============================================================================
# migrate_concurrent_executor 測試
# =============================================================================


class TestMigrateConcurrentExecutor:
    """遷移輔助函數測試。"""

    def test_migrate_basic(self):
        """測試基本遷移。"""
        tasks = [
            ConcurrentTask(id="t1", executor_id="e1", input_data={"v": 1}),
            ConcurrentTask(id="t2", executor_id="e2", input_data={"v": 2}),
        ]

        old_executor_config = {
            "id": "old-executor",
            "tasks": tasks,
            "mode": ConcurrentMode.ALL,
            "max_concurrency": 10,
            "timeout": 300,
        }

        adapter = migrate_concurrent_executor(**old_executor_config)

        assert adapter.id == "old-executor"
        assert len(adapter._tasks) == 2
        assert adapter._mode == ConcurrentMode.ALL

    def test_migrate_with_different_modes(self):
        """測試不同模式的遷移。"""
        tasks = [ConcurrentTask(id="t1", executor_id="e1", input_data={})]

        for mode in ConcurrentMode:
            adapter = migrate_concurrent_executor(
                id=f"test-{mode.value}",
                tasks=tasks,
                mode=mode,
            )
            assert adapter._mode == mode

    @pytest.mark.asyncio
    async def test_migrated_executor_works(self):
        """測試遷移後的執行器可正常工作。"""
        tasks = [
            ConcurrentTask(id="t1", executor_id="e1", input_data={}),
            ConcurrentTask(id="t2", executor_id="e2", input_data={}),
        ]

        adapter = migrate_concurrent_executor(
            id="migrated-executor",
            tasks=tasks,
            mode=ConcurrentMode.ALL,
        )

        result = await adapter.execute(success_task_executor)

        assert result["total_tasks"] == 2
        assert result["completed_tasks"] == 2


# =============================================================================
# Phase 2 API 兼容性測試
# =============================================================================


class TestPhase2Compatibility:
    """Phase 2 API 兼容性測試。"""

    @pytest.mark.asyncio
    async def test_result_format_compatible(self):
        """測試結果格式與 Phase 2 兼容。"""
        tasks = [
            ConcurrentTask(id="t1", executor_id="e1", input_data={}),
        ]

        adapter = ConcurrentExecutorAdapter(
            id="test",
            tasks=tasks,
        )

        result = await adapter.execute(success_task_executor)

        # 驗證 Phase 2 API 所需的字段
        assert "total_tasks" in result
        assert "completed_tasks" in result
        assert "failed_tasks" in result
        assert "results" in result
        assert "errors" in result
        assert "duration_ms" in result

    @pytest.mark.asyncio
    async def test_branch_info_compatible(self):
        """測試分支信息與 Phase 2 兼容。"""
        tasks = [
            ConcurrentTask(id="t1", executor_id="e1", input_data={}),
        ]

        adapter = ConcurrentExecutorAdapter(
            id="test",
            tasks=tasks,
        )

        await adapter.execute(success_task_executor)

        branches = adapter.get_all_branches()
        for branch in branches:
            data = branch.to_dict()

            # 驗證 Phase 2 所需字段
            assert "id" in data
            assert "executor_id" in data
            assert "status" in data
            assert "started_at" in data
            assert "completed_at" in data
