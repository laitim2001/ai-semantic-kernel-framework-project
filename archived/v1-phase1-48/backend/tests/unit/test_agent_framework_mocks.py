"""
Unit Tests for Agent Framework Mocks

測試 Mock 實現的正確性。

測試範圍:
    - MockExecutor
    - MockWorkflowContext
    - MockCheckpointStorage
    - MockWorkflow
    - 輔助函數
"""

import pytest
import asyncio
from datetime import datetime

from tests.mocks.agent_framework_mocks import (
    MockExecutor,
    MockWorkflowContext,
    MockCheckpointStorage,
    MockWorkflow,
    MockWorkflowRunResult,
    create_test_executor,
    create_test_workflow,
    create_test_checkpoint,
    assert_workflow_result,
)


class TestMockExecutor:
    """MockExecutor 測試類。"""

    @pytest.fixture
    def context(self):
        """創建測試上下文。"""
        return MockWorkflowContext()

    @pytest.mark.asyncio
    async def test_basic_handle(self, context):
        """測試基本處理。"""
        executor = MockExecutor(id="test", return_value={"result": "ok"})

        await executor.handle({"input": "data"}, context)

        assert executor.call_count == 1
        assert executor.last_input == {"input": "data"}
        assert executor.last_result == {"result": "ok"}
        assert {"result": "ok"} in context.outputs

    @pytest.mark.asyncio
    async def test_multiple_calls(self, context):
        """測試多次調用。"""
        executor = MockExecutor(id="test", return_value="ok")

        await executor.handle("call1", context)
        await executor.handle("call2", context)
        await executor.handle("call3", context)

        assert executor.call_count == 3
        assert len(executor.call_history) == 3
        assert executor.call_history[0].input_data == "call1"
        assert executor.call_history[2].input_data == "call3"

    @pytest.mark.asyncio
    async def test_delay(self, context):
        """測試延遲處理。"""
        executor = MockExecutor(id="test", delay_seconds=0.1)

        start = datetime.now()
        await executor.handle("data", context)
        elapsed = (datetime.now() - start).total_seconds()

        assert elapsed >= 0.1

    @pytest.mark.asyncio
    async def test_raise_error(self, context):
        """測試錯誤拋出。"""
        error = ValueError("Test error")
        executor = MockExecutor(id="test", raise_error=error)

        with pytest.raises(ValueError, match="Test error"):
            await executor.handle("data", context)

        assert executor.call_count == 1
        assert executor.call_history[0].error is error

    @pytest.mark.asyncio
    async def test_custom_handler(self, context):
        """測試自定義處理函數。"""
        async def custom_handler(data, ctx):
            return {"processed": data.upper()}

        executor = MockExecutor(id="test", handler_func=custom_handler)

        await executor.handle("hello", context)

        assert executor.last_result == {"processed": "HELLO"}

    def test_reset(self):
        """測試重置。"""
        executor = MockExecutor(id="test")
        executor._call_count = 5
        executor._call_history = [1, 2, 3]

        executor.reset()

        assert executor.call_count == 0
        assert executor.call_history == []

    def test_configure(self):
        """測試重新配置。"""
        executor = MockExecutor(id="test", return_value="old")

        executor.configure(return_value="new", delay_seconds=0.5)

        assert executor._return_value == "new"
        assert executor._delay == 0.5


class TestMockWorkflowContext:
    """MockWorkflowContext 測試類。"""

    @pytest.mark.asyncio
    async def test_yield_output(self):
        """測試輸出。"""
        ctx = MockWorkflowContext()

        await ctx.yield_output({"result": 1})
        await ctx.yield_output({"result": 2})

        assert ctx.outputs == [{"result": 1}, {"result": 2}]

    @pytest.mark.asyncio
    async def test_send_message(self):
        """測試發送消息。"""
        ctx = MockWorkflowContext()

        await ctx.send_message("Hello", target_id="exec1")
        await ctx.send_message("World")

        assert len(ctx.messages) == 2
        assert ctx.messages[0]["message"] == "Hello"
        assert ctx.messages[0]["target_id"] == "exec1"
        assert ctx.messages[1]["target_id"] is None

    @pytest.mark.asyncio
    async def test_state_management(self):
        """測試狀態管理。"""
        ctx = MockWorkflowContext()

        await ctx.set_state("key1", "value1")
        await ctx.set_state("key2", 42)

        assert await ctx.get_state("key1") == "value1"
        assert await ctx.get_state("key2") == 42
        assert await ctx.get_state("missing") is None
        assert await ctx.get_state("missing", "default") == "default"

    def test_initial_state(self):
        """測試初始狀態。"""
        ctx = MockWorkflowContext(initial_state={"preset": "value"})

        assert ctx.state == {"preset": "value"}

    def test_clear(self):
        """測試清空。"""
        ctx = MockWorkflowContext()
        ctx.outputs = [1, 2, 3]
        ctx.messages = [{"msg": "test"}]
        ctx.state = {"key": "value"}

        ctx.clear()

        assert ctx.outputs == []
        assert ctx.messages == []
        assert ctx.state == {}


class TestMockCheckpointStorage:
    """MockCheckpointStorage 測試類。"""

    @pytest.fixture
    def storage(self):
        """創建測試存儲。"""
        return MockCheckpointStorage()

    @pytest.fixture
    def checkpoint(self):
        """創建測試檢查點。"""
        return create_test_checkpoint(
            checkpoint_id="cp-1",
            workflow_id="wf-1",
        )

    @pytest.mark.asyncio
    async def test_save_checkpoint(self, storage, checkpoint):
        """測試保存檢查點。"""
        cp_id = await storage.save_checkpoint(checkpoint)

        assert cp_id == "cp-1"
        assert storage.save_count == 1
        assert storage.checkpoint_count == 1

    @pytest.mark.asyncio
    async def test_load_checkpoint(self, storage, checkpoint):
        """測試載入檢查點。"""
        await storage.save_checkpoint(checkpoint)

        loaded = await storage.load_checkpoint("cp-1")

        assert loaded is checkpoint
        assert storage.load_count == 1

    @pytest.mark.asyncio
    async def test_load_nonexistent(self, storage):
        """測試載入不存在的檢查點。"""
        loaded = await storage.load_checkpoint("nonexistent")

        assert loaded is None

    @pytest.mark.asyncio
    async def test_list_checkpoint_ids(self, storage):
        """測試列出檢查點 ID。"""
        cp1 = create_test_checkpoint(checkpoint_id="cp-1", workflow_id="wf-1")
        cp2 = create_test_checkpoint(checkpoint_id="cp-2", workflow_id="wf-1")
        cp3 = create_test_checkpoint(checkpoint_id="cp-3", workflow_id="wf-2")

        await storage.save_checkpoint(cp1)
        await storage.save_checkpoint(cp2)
        await storage.save_checkpoint(cp3)

        # 列出所有
        all_ids = await storage.list_checkpoint_ids()
        assert len(all_ids) == 3

        # 按工作流過濾
        wf1_ids = await storage.list_checkpoint_ids("wf-1")
        assert len(wf1_ids) == 2
        assert "cp-1" in wf1_ids
        assert "cp-2" in wf1_ids

    @pytest.mark.asyncio
    async def test_delete_checkpoint(self, storage, checkpoint):
        """測試刪除檢查點。"""
        await storage.save_checkpoint(checkpoint)

        deleted = await storage.delete_checkpoint("cp-1")

        assert deleted
        assert storage.checkpoint_count == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, storage):
        """測試刪除不存在的檢查點。"""
        deleted = await storage.delete_checkpoint("nonexistent")

        assert not deleted

    def test_clear(self, storage):
        """測試清空存儲。"""
        storage._checkpoints = {"cp-1": "data"}
        storage._save_count = 5
        storage._load_count = 3

        storage.clear()

        assert storage.checkpoint_count == 0
        assert storage.save_count == 0
        assert storage.load_count == 0


class TestMockWorkflow:
    """MockWorkflow 測試類。"""

    @pytest.mark.asyncio
    async def test_run(self):
        """測試執行。"""
        result = MockWorkflowRunResult(outputs=[{"done": True}])
        workflow = MockWorkflow(id="wf-1", return_result=result)

        run_result = await workflow.run({"input": "test"})

        assert run_result.outputs == [{"done": True}]
        assert workflow.run_count == 1

    @pytest.mark.asyncio
    async def test_run_with_error(self):
        """測試執行錯誤。"""
        error = RuntimeError("Workflow failed")
        workflow = MockWorkflow(id="wf-1", raise_error=error)

        with pytest.raises(RuntimeError, match="Workflow failed"):
            await workflow.run({"input": "test"})

    @pytest.mark.asyncio
    async def test_run_stream(self):
        """測試串流執行。"""
        result = MockWorkflowRunResult(
            outputs=[{"done": True}],
            events=[{"event": 1}, {"event": 2}],
        )
        workflow = MockWorkflow(id="wf-1", return_result=result)

        events = [e async for e in workflow.run_stream({"input": "test"})]

        assert len(events) == 2
        assert workflow.run_count == 1


class TestHelperFunctions:
    """輔助函數測試類。"""

    def test_create_test_executor(self):
        """測試創建測試執行器。"""
        executor = create_test_executor(
            id="my-exec",
            return_value={"custom": "value"},
            delay_seconds=0.2,
        )

        assert executor.id == "my-exec"
        assert executor._return_value == {"custom": "value"}
        assert executor._delay == 0.2

    def test_create_test_workflow(self):
        """測試創建測試工作流。"""
        workflow = create_test_workflow(
            id="my-wf",
            name="My Workflow",
            outputs=[{"output": "test"}],
        )

        assert workflow.id == "my-wf"
        assert workflow.name == "My Workflow"

    def test_create_test_checkpoint(self):
        """測試創建測試檢查點。"""
        checkpoint = create_test_checkpoint(
            workflow_id="wf-test",
            iteration_count=5,
            metadata={"custom": "data"},
        )

        assert checkpoint.workflow_id == "wf-test"
        assert checkpoint.iteration_count == 5
        assert checkpoint.metadata == {"custom": "data"}

    def test_assert_workflow_result_success(self):
        """測試斷言工作流結果（成功）。"""
        result = MockWorkflowRunResult(
            outputs=[{"status": "ok"}],
            success=True,
        )

        # 不應該拋出異常
        assert_workflow_result(result, expected_outputs=[{"status": "ok"}])

    def test_assert_workflow_result_failure(self):
        """測試斷言工作流結果（失敗）。"""
        result = MockWorkflowRunResult(
            outputs=[{"status": "ok"}],
            success=True,
        )

        with pytest.raises(AssertionError):
            assert_workflow_result(result, expected_outputs=[{"wrong": "value"}])


class TestPytestFixtures:
    """Pytest Fixtures 測試類。"""

    def test_mock_executor_fixture(self, mock_executor):
        """測試 mock_executor fixture。"""
        executor = mock_executor(id="test-exec", return_value={"ok": True})

        assert executor.id == "test-exec"
        assert executor._return_value == {"ok": True}

    def test_mock_context_fixture(self, mock_context):
        """測試 mock_context fixture。"""
        assert mock_context.outputs == []
        assert mock_context.messages == []

    def test_mock_checkpoint_storage_fixture(self, mock_checkpoint_storage):
        """測試 mock_checkpoint_storage fixture。"""
        assert mock_checkpoint_storage.checkpoint_count == 0

    def test_mock_workflow_fixture(self, mock_workflow):
        """測試 mock_workflow fixture。"""
        wf = mock_workflow(id="test-wf", outputs=[{"done": True}])

        assert wf.id == "test-wf"
