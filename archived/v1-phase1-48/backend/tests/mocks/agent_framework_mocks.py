"""
Agent Framework Mock Implementations

提供 Agent Framework 組件的 Mock 實現，用於測試。

設計原則:
    1. 完全模擬 Agent Framework 行為
    2. 可配置返回值、延遲和錯誤
    3. 提供調用歷史記錄
    4. 支持 pytest fixtures

Mock 類:
    - MockExecutor: 模擬 Executor
    - MockWorkflowContext: 模擬 WorkflowContext
    - MockCheckpointStorage: 模擬 CheckpointStorage
    - MockWorkflow: 模擬 Workflow
    - MockWorkflowRunResult: 模擬 WorkflowRunResult

使用範例:
    # 使用 Mock Executor
    executor = MockExecutor(
        id="test-executor",
        return_value={"result": "success"},
        delay_seconds=0.1,
    )
    await executor.handle(input_data, context)
    assert executor.call_count == 1

    # 使用 Mock Checkpoint Storage
    storage = MockCheckpointStorage()
    await storage.save_checkpoint(checkpoint)
    loaded = await storage.load_checkpoint(checkpoint_id)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock
import asyncio
import uuid
import pytest


@dataclass
class CallRecord:
    """記錄函數調用的數據類。"""
    input_data: Any
    timestamp: datetime
    result: Optional[Any] = None
    error: Optional[Exception] = None


class MockExecutor:
    """
    Mock Executor 用於測試。

    模擬 Agent Framework Executor 的行為，支持:
    - 可配置返回值
    - 可配置延遲
    - 可配置錯誤
    - 調用歷史記錄

    Attributes:
        id: 執行器 ID
        _return_value: 配置的返回值
        _delay: 配置的延遲（秒）
        _error: 配置的錯誤
        _call_count: 調用計數
        _call_history: 調用歷史

    Example:
        executor = MockExecutor(
            id="processor",
            return_value={"status": "ok"},
            delay_seconds=0.5,
        )

        result = await executor.handle({"input": "test"}, mock_context)
        assert executor.call_count == 1
        assert executor.last_input == {"input": "test"}
    """

    def __init__(
        self,
        id: str,
        return_value: Any = None,
        delay_seconds: float = 0,
        raise_error: Optional[Exception] = None,
        handler_func: Optional[Callable] = None,
    ):
        """
        初始化 Mock Executor。

        Args:
            id: 執行器 ID
            return_value: 處理後返回的值
            delay_seconds: 處理延遲（秒）
            raise_error: 要拋出的異常
            handler_func: 自定義處理函數
        """
        self.id = id
        self._return_value = return_value
        self._delay = delay_seconds
        self._error = raise_error
        self._handler_func = handler_func
        self._call_count = 0
        self._call_history: List[CallRecord] = []

    async def handle(self, input_data: Any, ctx: "MockWorkflowContext") -> Any:
        """
        處理輸入數據。

        模擬 @handler 裝飾的方法行為。

        Args:
            input_data: 輸入數據
            ctx: 工作流上下文

        Returns:
            配置的返回值

        Raises:
            配置的錯誤（如果有）
        """
        self._call_count += 1
        record = CallRecord(
            input_data=input_data,
            timestamp=datetime.now(timezone.utc),
        )

        try:
            # 模擬處理延遲
            if self._delay > 0:
                await asyncio.sleep(self._delay)

            # 檢查是否應該拋出錯誤
            if self._error:
                raise self._error

            # 使用自定義處理函數或默認返回值
            if self._handler_func:
                result = await self._handler_func(input_data, ctx)
            else:
                result = self._return_value if self._return_value is not None else input_data

            record.result = result

            # 輸出結果到上下文
            await ctx.yield_output(result)

            return result

        except Exception as e:
            record.error = e
            raise

        finally:
            self._call_history.append(record)

    @property
    def call_count(self) -> int:
        """獲取調用次數。"""
        return self._call_count

    @property
    def call_history(self) -> List[CallRecord]:
        """獲取調用歷史。"""
        return self._call_history

    @property
    def last_input(self) -> Optional[Any]:
        """獲取最後一次調用的輸入。"""
        if self._call_history:
            return self._call_history[-1].input_data
        return None

    @property
    def last_result(self) -> Optional[Any]:
        """獲取最後一次調用的結果。"""
        if self._call_history:
            return self._call_history[-1].result
        return None

    def reset(self) -> None:
        """重置調用統計。"""
        self._call_count = 0
        self._call_history = []

    def configure(
        self,
        return_value: Any = None,
        delay_seconds: float = None,
        raise_error: Optional[Exception] = None,
    ) -> "MockExecutor":
        """
        重新配置 Mock。

        Args:
            return_value: 新的返回值
            delay_seconds: 新的延遲
            raise_error: 新的錯誤

        Returns:
            self，支持鏈式調用
        """
        if return_value is not None:
            self._return_value = return_value
        if delay_seconds is not None:
            self._delay = delay_seconds
        if raise_error is not None:
            self._error = raise_error
        return self


class MockWorkflowContext:
    """
    Mock WorkflowContext 用於測試。

    模擬 Agent Framework WorkflowContext 的行為。

    Attributes:
        outputs: 輸出列表
        messages: 發送的消息列表
        state: 狀態字典

    Example:
        ctx = MockWorkflowContext()
        await ctx.yield_output({"result": "ok"})
        await ctx.send_message("Hello", target_id="other-executor")

        assert ctx.outputs == [{"result": "ok"}]
        assert len(ctx.messages) == 1
    """

    def __init__(self, initial_state: Optional[Dict[str, Any]] = None):
        """
        初始化 Mock Context。

        Args:
            initial_state: 初始狀態字典
        """
        self.outputs: List[Any] = []
        self.messages: List[Dict[str, Any]] = []
        self.state: Dict[str, Any] = initial_state or {}
        self._request_info_events: List[Any] = []

    async def yield_output(self, output: Any) -> None:
        """
        輸出結果。

        Args:
            output: 要輸出的數據
        """
        self.outputs.append(output)

    async def send_message(
        self,
        message: Any,
        target_id: Optional[str] = None,
    ) -> None:
        """
        發送消息到其他執行器。

        Args:
            message: 消息內容
            target_id: 目標執行器 ID
        """
        self.messages.append({
            "message": message,
            "target_id": target_id,
            "timestamp": datetime.now(timezone.utc),
        })

    async def set_state(self, key: str, value: Any) -> None:
        """
        設置狀態值。

        Args:
            key: 狀態鍵
            value: 狀態值
        """
        self.state[key] = value

    async def get_state(self, key: str, default: Any = None) -> Any:
        """
        獲取狀態值。

        Args:
            key: 狀態鍵
            default: 默認值

        Returns:
            狀態值
        """
        return self.state.get(key, default)

    def clear(self) -> None:
        """清空所有記錄。"""
        self.outputs = []
        self.messages = []
        self.state = {}
        self._request_info_events = []


class MockCheckpointStorage:
    """
    Mock CheckpointStorage 用於測試。

    內存實現的檢查點存儲，符合 Agent Framework CheckpointStorage 協議。

    Example:
        storage = MockCheckpointStorage()
        checkpoint = create_test_checkpoint(workflow_id="test-wf")

        await storage.save_checkpoint(checkpoint)
        loaded = await storage.load_checkpoint(checkpoint.checkpoint_id)
        assert loaded is not None
    """

    def __init__(self):
        """初始化內存存儲。"""
        self._checkpoints: Dict[str, Any] = {}
        self._save_count = 0
        self._load_count = 0

    async def save_checkpoint(self, checkpoint: Any) -> str:
        """保存檢查點。"""
        self._save_count += 1
        checkpoint_id = checkpoint.checkpoint_id
        self._checkpoints[checkpoint_id] = checkpoint
        return checkpoint_id

    async def load_checkpoint(self, checkpoint_id: str) -> Optional[Any]:
        """載入檢查點。"""
        self._load_count += 1
        return self._checkpoints.get(checkpoint_id)

    async def list_checkpoint_ids(self, workflow_id: Optional[str] = None) -> List[str]:
        """列出檢查點 ID。"""
        if workflow_id is None:
            return list(self._checkpoints.keys())
        return [
            cp.checkpoint_id
            for cp in self._checkpoints.values()
            if cp.workflow_id == workflow_id
        ]

    async def list_checkpoints(self, workflow_id: Optional[str] = None) -> List[Any]:
        """列出檢查點。"""
        if workflow_id is None:
            return list(self._checkpoints.values())
        return [
            cp for cp in self._checkpoints.values()
            if cp.workflow_id == workflow_id
        ]

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """刪除檢查點。"""
        if checkpoint_id in self._checkpoints:
            del self._checkpoints[checkpoint_id]
            return True
        return False

    def clear(self) -> None:
        """清空所有檢查點。"""
        self._checkpoints = {}
        self._save_count = 0
        self._load_count = 0

    @property
    def save_count(self) -> int:
        """獲取保存次數。"""
        return self._save_count

    @property
    def load_count(self) -> int:
        """獲取載入次數。"""
        return self._load_count

    @property
    def checkpoint_count(self) -> int:
        """獲取檢查點數量。"""
        return len(self._checkpoints)


@dataclass
class MockWorkflowRunResult:
    """
    Mock WorkflowRunResult 用於測試。

    模擬 Agent Framework WorkflowRunResult 的結構。
    """
    outputs: List[Any] = field(default_factory=list)
    events: List[Any] = field(default_factory=list)
    final_state: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[Exception] = None

    def get_outputs(self) -> List[Any]:
        """獲取所有輸出。"""
        return self.outputs


class MockWorkflow:
    """
    Mock Workflow 用於測試。

    模擬 Agent Framework Workflow 的行為。

    Example:
        workflow = MockWorkflow(
            id="test-workflow",
            return_result=MockWorkflowRunResult(outputs=[{"result": "ok"}]),
        )

        result = await workflow.run({"input": "test"})
        assert result.outputs == [{"result": "ok"}]
    """

    def __init__(
        self,
        id: str,
        name: str = "Test Workflow",
        return_result: Optional[MockWorkflowRunResult] = None,
        raise_error: Optional[Exception] = None,
    ):
        """
        初始化 Mock Workflow。

        Args:
            id: 工作流 ID
            name: 工作流名稱
            return_result: 配置的返回結果
            raise_error: 配置的錯誤
        """
        self.id = id
        self.name = name
        self._return_result = return_result or MockWorkflowRunResult()
        self._error = raise_error
        self._run_count = 0

    async def run(self, input_data: Any) -> MockWorkflowRunResult:
        """
        執行工作流。

        Args:
            input_data: 輸入數據

        Returns:
            MockWorkflowRunResult

        Raises:
            配置的錯誤（如果有）
        """
        self._run_count += 1

        if self._error:
            raise self._error

        return self._return_result

    async def run_stream(self, input_data: Any):
        """
        串流執行工作流。

        Args:
            input_data: 輸入數據

        Yields:
            工作流事件
        """
        self._run_count += 1

        if self._error:
            raise self._error

        for event in self._return_result.events:
            yield event

    @property
    def run_count(self) -> int:
        """獲取執行次數。"""
        return self._run_count


# ============================================================
# Helper Functions
# ============================================================

def create_test_executor(
    id: str = "test-executor",
    return_value: Any = None,
    delay_seconds: float = 0,
    raise_error: Optional[Exception] = None,
) -> MockExecutor:
    """
    創建測試用的 Mock Executor。

    Args:
        id: 執行器 ID
        return_value: 返回值
        delay_seconds: 延遲
        raise_error: 錯誤

    Returns:
        MockExecutor 實例
    """
    return MockExecutor(
        id=id,
        return_value=return_value or {"status": "ok"},
        delay_seconds=delay_seconds,
        raise_error=raise_error,
    )


def create_test_workflow(
    id: str = "test-workflow",
    name: str = "Test Workflow",
    outputs: Optional[List[Any]] = None,
    raise_error: Optional[Exception] = None,
) -> MockWorkflow:
    """
    創建測試用的 Mock Workflow。

    Args:
        id: 工作流 ID
        name: 工作流名稱
        outputs: 輸出列表
        raise_error: 錯誤

    Returns:
        MockWorkflow 實例
    """
    result = MockWorkflowRunResult(outputs=outputs or [{"result": "success"}])
    return MockWorkflow(
        id=id,
        name=name,
        return_result=result,
        raise_error=raise_error,
    )


@dataclass
class MockCheckpoint:
    """測試用的檢查點數據類。"""
    checkpoint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    messages: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    shared_state: Dict[str, Any] = field(default_factory=dict)
    pending_request_info_events: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    iteration_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "workflow_id": self.workflow_id,
            "timestamp": self.timestamp,
            "messages": self.messages,
            "shared_state": self.shared_state,
            "pending_request_info_events": self.pending_request_info_events,
            "iteration_count": self.iteration_count,
            "metadata": self.metadata,
            "version": self.version,
        }


def create_test_checkpoint(
    checkpoint_id: Optional[str] = None,
    workflow_id: str = "test-workflow",
    iteration_count: int = 0,
    metadata: Optional[Dict[str, Any]] = None,
) -> MockCheckpoint:
    """
    創建測試用的檢查點。

    Args:
        checkpoint_id: 檢查點 ID（可選，自動生成）
        workflow_id: 工作流 ID
        iteration_count: 迭代計數
        metadata: 元數據

    Returns:
        MockCheckpoint 實例
    """
    return MockCheckpoint(
        checkpoint_id=checkpoint_id or str(uuid.uuid4()),
        workflow_id=workflow_id,
        iteration_count=iteration_count,
        metadata=metadata or {},
    )


def assert_workflow_result(
    result: Union[MockWorkflowRunResult, Any],
    expected_outputs: Optional[List[Any]] = None,
    expected_success: bool = True,
) -> None:
    """
    斷言工作流結果。

    Args:
        result: 工作流結果
        expected_outputs: 期望的輸出列表
        expected_success: 期望的成功狀態

    Raises:
        AssertionError: 斷言失敗時
    """
    if hasattr(result, 'success'):
        assert result.success == expected_success, (
            f"Expected success={expected_success}, got {result.success}"
        )

    if expected_outputs is not None:
        outputs = result.get_outputs() if hasattr(result, 'get_outputs') else result.outputs
        assert outputs == expected_outputs, (
            f"Expected outputs={expected_outputs}, got {outputs}"
        )


# ============================================================
# Pytest Fixtures
# ============================================================

@pytest.fixture
def mock_executor():
    """
    創建 Mock Executor 的 fixture。

    用法:
        def test_something(mock_executor):
            executor = mock_executor(id="my-exec", return_value={"ok": True})
            # ...
    """
    def _create(
        id: str = "test-executor",
        return_value: Any = None,
        delay_seconds: float = 0,
        raise_error: Optional[Exception] = None,
    ) -> MockExecutor:
        return create_test_executor(
            id=id,
            return_value=return_value,
            delay_seconds=delay_seconds,
            raise_error=raise_error,
        )
    return _create


@pytest.fixture
def mock_context():
    """
    創建 Mock WorkflowContext 的 fixture。

    用法:
        def test_something(mock_context):
            ctx = mock_context
            await ctx.yield_output({"result": "ok"})
            assert len(ctx.outputs) == 1
    """
    return MockWorkflowContext()


@pytest.fixture
def mock_checkpoint_storage():
    """
    創建 Mock CheckpointStorage 的 fixture。

    用法:
        def test_something(mock_checkpoint_storage):
            storage = mock_checkpoint_storage
            await storage.save_checkpoint(checkpoint)
            # ...
    """
    return MockCheckpointStorage()


@pytest.fixture
def mock_workflow():
    """
    創建 Mock Workflow 的 fixture。

    用法:
        def test_something(mock_workflow):
            wf = mock_workflow(id="my-wf", outputs=[{"done": True}])
            result = await wf.run(input_data)
            # ...
    """
    def _create(
        id: str = "test-workflow",
        name: str = "Test Workflow",
        outputs: Optional[List[Any]] = None,
        raise_error: Optional[Exception] = None,
    ) -> MockWorkflow:
        return create_test_workflow(
            id=id,
            name=name,
            outputs=outputs,
            raise_error=raise_error,
        )
    return _create
