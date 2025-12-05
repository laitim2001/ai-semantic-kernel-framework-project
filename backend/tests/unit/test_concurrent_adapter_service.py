# =============================================================================
# Unit Tests for Concurrent API Adapter Service
# =============================================================================
# Sprint 14: ConcurrentBuilder 重構
# Phase 3 Feature: P3-F1 (並行執行重構)
#
# 測試範圍:
#   - ConcurrentAPIService 初始化
#   - ExecuteRequest, ExecuteResponse DTOs
#   - 使用 adapter 執行
#   - 使用 legacy 執行
#   - 執行記錄管理
#   - 統計數據
# =============================================================================

import asyncio
import pytest
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.api.v1.concurrent.adapter_service import (
    ExecuteRequest,
    ExecuteResponse,
    BranchInfo,
    ConcurrentAPIService,
    get_concurrent_api_service,
    reset_concurrent_api_service,
)


# =============================================================================
# 測試輔助函數
# =============================================================================


@pytest.fixture
def api_service():
    """創建測試用 API 服務。"""
    reset_concurrent_api_service()
    return ConcurrentAPIService()


@pytest.fixture
def sample_request():
    """創建示例請求。"""
    return ExecuteRequest(
        workflow_id=uuid4(),
        mode="all",
        timeout_seconds=60,
        max_concurrency=5,
        tasks=[
            {"id": "task-1", "executor_id": "exec-1", "input_data": {"value": 1}},
            {"id": "task-2", "executor_id": "exec-2", "input_data": {"value": 2}},
        ],
        input_data={"context": "test"},
    )


# =============================================================================
# ExecuteRequest 測試
# =============================================================================


class TestExecuteRequest:
    """ExecuteRequest DTO 測試。"""

    def test_default_values(self):
        """測試預設值。"""
        request = ExecuteRequest()

        assert request.workflow_id is None
        assert request.mode == "all"
        assert request.timeout_seconds == 300
        assert request.max_concurrency == 10
        assert request.tasks == []
        assert request.input_data is None

    def test_custom_values(self):
        """測試自定義值。"""
        wf_id = uuid4()
        request = ExecuteRequest(
            workflow_id=wf_id,
            mode="majority",
            timeout_seconds=120,
            max_concurrency=20,
            tasks=[{"id": "t1"}],
            input_data={"key": "value"},
            fan_out_strategy="broadcast",
            fan_in_strategy="collect_all",
            metadata={"tag": "test"},
        )

        assert request.workflow_id == wf_id
        assert request.mode == "majority"
        assert request.timeout_seconds == 120
        assert request.max_concurrency == 20
        assert len(request.tasks) == 1
        assert request.fan_out_strategy == "broadcast"
        assert request.fan_in_strategy == "collect_all"


# =============================================================================
# ExecuteResponse 測試
# =============================================================================


class TestExecuteResponse:
    """ExecuteResponse DTO 測試。"""

    def test_successful_response(self):
        """測試成功響應。"""
        exec_id = uuid4()
        response = ExecuteResponse(
            execution_id=exec_id,
            status="completed",
            mode="all",
            total_tasks=3,
            completed_tasks=3,
            failed_tasks=0,
            results={"t1": "r1", "t2": "r2", "t3": "r3"},
            errors={},
            duration_ms=500,
            branches=[],
        )

        assert response.execution_id == exec_id
        assert response.status == "completed"
        assert response.total_tasks == 3
        assert response.completed_tasks == 3
        assert response.failed_tasks == 0
        assert response.duration_ms == 500

    def test_partial_failure_response(self):
        """測試部分失敗響應。"""
        response = ExecuteResponse(
            execution_id=uuid4(),
            status="completed",
            mode="all",
            total_tasks=3,
            completed_tasks=2,
            failed_tasks=1,
            results={"t1": "r1", "t2": "r2"},
            errors={"t3": "Error occurred"},
            duration_ms=300,
            branches=[],
        )

        assert response.completed_tasks == 2
        assert response.failed_tasks == 1
        assert "t3" in response.errors


# =============================================================================
# BranchInfo 測試
# =============================================================================


class TestBranchInfo:
    """BranchInfo DTO 測試。"""

    def test_basic_creation(self):
        """測試基本創建。"""
        info = BranchInfo(
            branch_id="branch-1",
            executor_id="exec-1",
            status="completed",
        )

        assert info.branch_id == "branch-1"
        assert info.executor_id == "exec-1"
        assert info.status == "completed"

    def test_with_timing(self):
        """測試帶計時信息。"""
        now = datetime.now(timezone.utc)
        info = BranchInfo(
            branch_id="branch-1",
            executor_id="exec-1",
            status="completed",
            started_at=now,
            completed_at=now,
            duration_ms=150,
            result={"data": "value"},
        )

        assert info.started_at is not None
        assert info.completed_at is not None
        assert info.duration_ms == 150
        assert info.result == {"data": "value"}


# =============================================================================
# ConcurrentAPIService 初始化測試
# =============================================================================


class TestConcurrentAPIServiceInit:
    """ConcurrentAPIService 初始化測試。"""

    def test_basic_initialization(self, api_service):
        """測試基本初始化。"""
        assert api_service._executions == {}
        assert api_service._task_executors == {}

    def test_singleton_pattern(self):
        """測試單例模式。"""
        reset_concurrent_api_service()

        service1 = get_concurrent_api_service()
        service2 = get_concurrent_api_service()

        assert service1 is service2

    def test_reset_singleton(self):
        """測試重置單例。"""
        service1 = get_concurrent_api_service()
        reset_concurrent_api_service()
        service2 = get_concurrent_api_service()

        assert service1 is not service2


# =============================================================================
# ConcurrentAPIService 執行器註冊測試
# =============================================================================


class TestConcurrentAPIServiceExecutorRegistration:
    """執行器註冊測試。"""

    def test_register_executor(self, api_service):
        """測試註冊執行器。"""

        async def my_executor(input_data):
            return {"status": "done"}

        api_service.register_task_executor("my-exec", my_executor)

        assert "my-exec" in api_service._task_executors

    def test_register_multiple_executors(self, api_service):
        """測試註冊多個執行器。"""

        async def exec1(input_data):
            return {"exec": 1}

        async def exec2(input_data):
            return {"exec": 2}

        api_service.register_task_executor("exec-1", exec1)
        api_service.register_task_executor("exec-2", exec2)

        assert len(api_service._task_executors) == 2


# =============================================================================
# ConcurrentAPIService 執行測試 (使用 Adapter)
# =============================================================================


class TestConcurrentAPIServiceAdapterExecution:
    """使用 Adapter 執行測試。"""

    @pytest.mark.asyncio
    async def test_execute_with_adapter_empty_tasks(self, api_service):
        """測試 adapter 執行空任務。"""
        request = ExecuteRequest(
            mode="all",
            tasks=[],
            timeout_seconds=30,
        )

        response = await api_service.execute(request, use_adapter=True)

        assert response.execution_id is not None
        assert response.total_tasks == 0

    @pytest.mark.asyncio
    async def test_execute_with_adapter_with_tasks(self, api_service):
        """測試 adapter 執行帶任務。"""
        # 註冊執行器
        async def test_executor(input_data):
            await asyncio.sleep(0.01)
            return {"processed": True}

        api_service.register_task_executor("test-exec", test_executor)

        request = ExecuteRequest(
            mode="all",
            tasks=[
                {"id": "t1", "executor_id": "test-exec"},
                {"id": "t2", "executor_id": "test-exec"},
            ],
            timeout_seconds=30,
        )

        response = await api_service.execute(request, use_adapter=True)

        assert response.execution_id is not None
        assert response.total_tasks == 2

    @pytest.mark.asyncio
    async def test_execute_stores_execution(self, api_service):
        """測試執行結果被存儲。"""
        request = ExecuteRequest(mode="all", tasks=[])

        response = await api_service.execute(request, use_adapter=True)

        stored = api_service.get_execution(response.execution_id)
        assert stored is not None
        assert stored["use_adapter"] is True


# =============================================================================
# ConcurrentAPIService 執行測試 (使用 Legacy)
# =============================================================================


class TestConcurrentAPIServiceLegacyExecution:
    """使用 Legacy 執行測試。"""

    @pytest.mark.asyncio
    async def test_execute_with_legacy_empty_tasks(self, api_service):
        """測試 legacy 執行空任務。"""
        request = ExecuteRequest(
            mode="all",
            tasks=[],
            timeout_seconds=30,
        )

        response = await api_service.execute(request, use_adapter=False)

        assert response.execution_id is not None
        assert response.total_tasks == 0

    @pytest.mark.asyncio
    async def test_execute_with_legacy_with_tasks(self, api_service):
        """測試 legacy 執行帶任務。"""
        request = ExecuteRequest(
            mode="all",
            tasks=[
                {"id": "t1", "executor_id": "e1", "input_data": {"v": 1}},
                {"id": "t2", "executor_id": "e2", "input_data": {"v": 2}},
            ],
            timeout_seconds=30,
        )

        response = await api_service.execute(request, use_adapter=False)

        assert response.execution_id is not None
        assert response.total_tasks == 2

    @pytest.mark.asyncio
    async def test_execute_legacy_stores_flag(self, api_service):
        """測試 legacy 執行存儲標記。"""
        request = ExecuteRequest(mode="all", tasks=[])

        response = await api_service.execute(request, use_adapter=False)

        stored = api_service.get_execution(response.execution_id)
        assert stored is not None
        assert stored["use_adapter"] is False


# =============================================================================
# ConcurrentAPIService 執行模式測試
# =============================================================================


class TestConcurrentAPIServiceModes:
    """執行模式測試。"""

    @pytest.mark.asyncio
    async def test_all_mode(self, api_service):
        """測試 ALL 模式。"""
        request = ExecuteRequest(mode="all", tasks=[])
        response = await api_service.execute(request)

        assert response.mode == "all"

    @pytest.mark.asyncio
    async def test_any_mode(self, api_service):
        """測試 ANY 模式。"""
        request = ExecuteRequest(mode="any", tasks=[])
        response = await api_service.execute(request)

        assert response.mode == "any"

    @pytest.mark.asyncio
    async def test_majority_mode(self, api_service):
        """測試 MAJORITY 模式。"""
        request = ExecuteRequest(mode="majority", tasks=[])
        response = await api_service.execute(request)

        assert response.mode == "majority"

    @pytest.mark.asyncio
    async def test_first_success_mode(self, api_service):
        """測試 FIRST_SUCCESS 模式。"""
        request = ExecuteRequest(mode="first_success", tasks=[])
        response = await api_service.execute(request)

        assert response.mode == "first_success"


# =============================================================================
# ConcurrentAPIService 記錄管理測試
# =============================================================================


class TestConcurrentAPIServiceRecords:
    """記錄管理測試。"""

    @pytest.mark.asyncio
    async def test_get_execution(self, api_service):
        """測試獲取執行記錄。"""
        request = ExecuteRequest(mode="all", tasks=[])
        response = await api_service.execute(request)

        execution = api_service.get_execution(response.execution_id)

        assert execution is not None
        assert "request" in execution
        assert "response" in execution

    def test_get_nonexistent_execution(self, api_service):
        """測試獲取不存在的執行記錄。"""
        execution = api_service.get_execution(uuid4())

        assert execution is None

    @pytest.mark.asyncio
    async def test_list_executions(self, api_service):
        """測試列出執行記錄。"""
        # 創建多個執行
        for _ in range(5):
            request = ExecuteRequest(mode="all", tasks=[])
            await api_service.execute(request)

        executions = api_service.list_executions(limit=10)

        assert len(executions) == 5

    @pytest.mark.asyncio
    async def test_list_executions_with_pagination(self, api_service):
        """測試分頁列出執行記錄。"""
        # 創建多個執行
        for _ in range(10):
            request = ExecuteRequest(mode="all", tasks=[])
            await api_service.execute(request)

        # 獲取前 5 個
        page1 = api_service.list_executions(limit=5, offset=0)
        assert len(page1) == 5

        # 獲取後 5 個
        page2 = api_service.list_executions(limit=5, offset=5)
        assert len(page2) == 5


# =============================================================================
# ConcurrentAPIService 統計測試
# =============================================================================


class TestConcurrentAPIServiceStatistics:
    """統計測試。"""

    def test_empty_statistics(self, api_service):
        """測試空統計。"""
        stats = api_service.get_statistics()

        assert stats["total_executions"] == 0
        assert stats["adapter_executions"] == 0
        assert stats["legacy_executions"] == 0

    @pytest.mark.asyncio
    async def test_statistics_after_executions(self, api_service):
        """測試執行後統計。"""
        # 使用 adapter 執行
        request1 = ExecuteRequest(mode="all", tasks=[])
        await api_service.execute(request1, use_adapter=True)

        # 使用 legacy 執行
        request2 = ExecuteRequest(mode="all", tasks=[])
        await api_service.execute(request2, use_adapter=False)

        stats = api_service.get_statistics()

        assert stats["total_executions"] == 2
        assert stats["adapter_executions"] == 1
        assert stats["legacy_executions"] == 1

    @pytest.mark.asyncio
    async def test_registered_executors_count(self, api_service):
        """測試註冊執行器計數。"""
        async def exec1(data):
            return {}

        async def exec2(data):
            return {}

        api_service.register_task_executor("e1", exec1)
        api_service.register_task_executor("e2", exec2)

        stats = api_service.get_statistics()

        assert stats["registered_executors"] == 2


# =============================================================================
# ConcurrentAPIService 錯誤處理測試
# =============================================================================


class TestConcurrentAPIServiceErrorHandling:
    """錯誤處理測試。"""

    @pytest.mark.asyncio
    async def test_execution_error_handling(self, api_service):
        """測試執行錯誤處理。"""
        # 使用會失敗的執行器
        async def failing_executor(input_data):
            raise ValueError("Intentional failure")

        api_service.register_task_executor("fail-exec", failing_executor)

        request = ExecuteRequest(
            mode="all",
            tasks=[{"id": "t1", "executor_id": "fail-exec"}],
        )

        response = await api_service.execute(request)

        # 應該有錯誤記錄
        assert response.execution_id is not None

    @pytest.mark.asyncio
    async def test_invalid_mode_handling(self, api_service):
        """測試無效模式處理。"""
        request = ExecuteRequest(
            mode="invalid_mode",  # 無效模式
            tasks=[],
        )

        response = await api_service.execute(request)

        # 應該回退到預設模式
        assert response.execution_id is not None


# =============================================================================
# 整合測試
# =============================================================================


class TestConcurrentAPIServiceIntegration:
    """整合測試。"""

    @pytest.mark.asyncio
    async def test_full_workflow_with_adapter(self, api_service):
        """測試完整 adapter 工作流程。"""
        # 1. 註冊執行器
        async def process_executor(input_data):
            await asyncio.sleep(0.01)
            return {"processed": input_data, "timestamp": datetime.now(timezone.utc).isoformat()}

        api_service.register_task_executor("process", process_executor)

        # 2. 創建請求
        request = ExecuteRequest(
            mode="all",
            tasks=[
                {"id": "task-1", "executor_id": "process", "input_data": {"item": "A"}},
                {"id": "task-2", "executor_id": "process", "input_data": {"item": "B"}},
            ],
            timeout_seconds=60,
            max_concurrency=5,
        )

        # 3. 執行
        response = await api_service.execute(request, use_adapter=True)

        # 4. 驗證響應
        assert response.status in ["completed", "failed"]
        assert response.total_tasks == 2

        # 5. 獲取存儲的執行
        stored = api_service.get_execution(response.execution_id)
        assert stored is not None

        # 6. 驗證統計
        stats = api_service.get_statistics()
        assert stats["total_executions"] >= 1

    @pytest.mark.asyncio
    async def test_full_workflow_with_legacy(self, api_service):
        """測試完整 legacy 工作流程。"""
        # 1. 創建請求
        request = ExecuteRequest(
            mode="all",
            tasks=[
                {"id": "task-1", "executor_id": "e1", "input_data": {"value": 1}},
                {"id": "task-2", "executor_id": "e2", "input_data": {"value": 2}},
            ],
            timeout_seconds=60,
        )

        # 2. 執行
        response = await api_service.execute(request, use_adapter=False)

        # 3. 驗證響應
        assert response.status in ["completed", "failed"]
        assert response.total_tasks == 2

        # 4. 獲取存儲的執行
        stored = api_service.get_execution(response.execution_id)
        assert stored["use_adapter"] is False

    @pytest.mark.asyncio
    async def test_mixed_adapter_and_legacy(self, api_service):
        """測試混合使用 adapter 和 legacy。"""
        request = ExecuteRequest(mode="all", tasks=[])

        # 使用 adapter
        resp1 = await api_service.execute(request, use_adapter=True)

        # 使用 legacy
        resp2 = await api_service.execute(request, use_adapter=False)

        # 再次使用 adapter
        resp3 = await api_service.execute(request, use_adapter=True)

        stats = api_service.get_statistics()

        assert stats["total_executions"] == 3
        assert stats["adapter_executions"] == 2
        assert stats["legacy_executions"] == 1
