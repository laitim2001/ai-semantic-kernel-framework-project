"""
Tests for Session Agent Bridge - Sprint 46 S46-1

測試 SessionAgentBridge 的功能:
- 初始化
- 訊息處理
- 工具審批整合
- 錯誤處理
"""

import pytest
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from src.domain.sessions.bridge import (
    SessionAgentBridge,
    BridgeConfig,
    ProcessingContext,
    BridgeError,
    SessionNotFoundError,
    SessionNotActiveError,
    AgentNotFoundError,
    MaxIterationsExceededError,
    PendingApprovalError,
    SessionServiceProtocol,
    AgentRepositoryProtocol,
    create_session_agent_bridge,
)
from src.domain.sessions.models import (
    Session,
    SessionStatus,
    SessionConfig,
    Message,
    MessageRole,
    Attachment,
)
from src.domain.sessions.events import (
    ExecutionEvent,
    ExecutionEventType,
    ExecutionEventFactory,
)
from src.domain.sessions.executor import (
    AgentExecutor,
    AgentConfig,
    ExecutionConfig,
)
from src.domain.sessions.tool_handler import (
    ToolCallHandler,
    ParsedToolCall,
    ToolExecutionResult,
    ToolSource,
)
from src.domain.sessions.approval import (
    ToolApprovalManager,
    ToolApprovalRequest,
    ApprovalStatus,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_session():
    """創建 mock Session"""
    session = MagicMock(spec=Session)
    session.id = "session-123"
    session.user_id = "user-456"
    session.agent_id = "agent-789"
    session.status = SessionStatus.ACTIVE
    session.config = SessionConfig()
    session.messages = []
    session.to_llm_messages.return_value = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]
    return session


@pytest.fixture
def mock_session_service(mock_session):
    """創建 mock SessionService"""
    service = AsyncMock()
    service.get_session = AsyncMock(return_value=mock_session)
    service.send_message = AsyncMock(return_value=Message(
        role=MessageRole.USER,
        content="Hello",
    ))
    service.add_assistant_message = AsyncMock(return_value=Message(
        role=MessageRole.ASSISTANT,
        content="Hi there!",
    ))
    service.get_messages = AsyncMock(return_value=[])
    service.get_conversation_for_llm = AsyncMock(return_value=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"},
    ])
    return service


@pytest.fixture
def mock_agent():
    """創建 mock Agent"""
    agent = MagicMock()
    agent.id = "agent-789"
    agent.name = "Test Agent"
    agent.instructions = "You are a helpful assistant."
    agent.tools = []
    agent.model_config_data = {"temperature": 0.7}
    agent.max_iterations = 10
    return agent


@pytest.fixture
def mock_agent_repository(mock_agent):
    """創建 mock AgentRepository"""
    repo = AsyncMock()
    repo.get = AsyncMock(return_value=mock_agent)
    return repo


@pytest.fixture
def mock_agent_executor():
    """創建 mock AgentExecutor"""
    executor = MagicMock(spec=AgentExecutor)

    async def mock_execute(*args, **kwargs):
        yield ExecutionEventFactory.started(
            session_id=kwargs.get("session_id", ""),
            execution_id="exec-123",
        )
        yield ExecutionEventFactory.content_delta(
            session_id=kwargs.get("session_id", ""),
            execution_id="exec-123",
            delta="Hello",
        )
        yield ExecutionEventFactory.content_delta(
            session_id=kwargs.get("session_id", ""),
            execution_id="exec-123",
            delta=" there!",
        )
        yield ExecutionEventFactory.done(
            session_id=kwargs.get("session_id", ""),
            execution_id="exec-123",
            finish_reason="stop",
        )

    executor.execute = mock_execute
    return executor


@pytest.fixture
def mock_tool_handler():
    """創建 mock ToolCallHandler"""
    handler = MagicMock(spec=ToolCallHandler)
    handler.config = MagicMock()
    handler.config.require_approval_tools = set()

    handler.execute_tool = AsyncMock(return_value=ToolExecutionResult(
        tool_call_id="tc-123",
        name="test_tool",
        success=True,
        result={"output": "Tool executed successfully"},
        source=ToolSource.LOCAL,
    ))

    handler.results_to_messages = MagicMock(return_value=[
        {"role": "tool", "tool_call_id": "tc-123", "content": "Tool result"}
    ])

    return handler


@pytest.fixture
def mock_approval_manager():
    """創建 mock ToolApprovalManager"""
    manager = AsyncMock(spec=ToolApprovalManager)

    manager.create_approval_request = AsyncMock(return_value=ToolApprovalRequest(
        id="approval-123",
        session_id="session-123",
        execution_id="exec-123",
        tool_call={"id": "tc-123", "name": "test_tool", "arguments": {}},
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow(),
    ))

    manager.get_pending_approvals = AsyncMock(return_value=[])
    manager.resolve_approval = AsyncMock()
    manager.cancel_approval = AsyncMock(return_value=True)

    return manager


@pytest.fixture
def bridge_config():
    """創建測試用 BridgeConfig"""
    return BridgeConfig(
        max_tool_iterations=5,
        stream_by_default=True,
        save_tool_results=True,
        approval_timeout=60,
        enable_approval=True,
    )


@pytest.fixture
def bridge(
    mock_session_service,
    mock_agent_executor,
    mock_agent_repository,
    mock_tool_handler,
    mock_approval_manager,
    bridge_config,
):
    """創建完整配置的 SessionAgentBridge"""
    return SessionAgentBridge(
        session_service=mock_session_service,
        agent_executor=mock_agent_executor,
        agent_repository=mock_agent_repository,
        tool_handler=mock_tool_handler,
        approval_manager=mock_approval_manager,
        config=bridge_config,
    )


# =============================================================================
# Test Classes
# =============================================================================


class TestBridgeConfig:
    """BridgeConfig 測試"""

    def test_default_values(self):
        """測試預設值"""
        config = BridgeConfig()

        assert config.max_tool_iterations == 10
        assert config.stream_by_default is True
        assert config.save_tool_results is True
        assert config.approval_timeout == 300
        assert config.enable_approval is True

    def test_custom_values(self):
        """測試自訂值"""
        config = BridgeConfig(
            max_tool_iterations=5,
            stream_by_default=False,
            save_tool_results=False,
            approval_timeout=60,
            enable_approval=False,
        )

        assert config.max_tool_iterations == 5
        assert config.stream_by_default is False
        assert config.save_tool_results is False
        assert config.approval_timeout == 60
        assert config.enable_approval is False


class TestProcessingContext:
    """ProcessingContext 測試"""

    def test_initialization(self):
        """測試初始化"""
        context = ProcessingContext(
            session_id="session-123",
            execution_id="exec-456",
        )

        assert context.session_id == "session-123"
        assert context.execution_id == "exec-456"
        assert context.iteration == 0
        assert context.content_parts == []
        assert context.tool_calls == []
        assert context.tool_results == []
        assert context.pending_approvals == []
        assert context.completed is False
        assert context.error is None

    def test_mutable_fields(self):
        """測試可變欄位"""
        context = ProcessingContext(
            session_id="session-123",
            execution_id="exec-456",
        )

        context.iteration = 1
        context.content_parts.append("Hello")
        context.completed = True

        assert context.iteration == 1
        assert context.content_parts == ["Hello"]
        assert context.completed is True


class TestSessionAgentBridgeInit:
    """SessionAgentBridge 初始化測試"""

    def test_basic_init(
        self,
        mock_session_service,
        mock_agent_executor,
        mock_agent_repository,
    ):
        """測試基本初始化"""
        bridge = SessionAgentBridge(
            session_service=mock_session_service,
            agent_executor=mock_agent_executor,
            agent_repository=mock_agent_repository,
        )

        assert bridge._session_service is mock_session_service
        assert bridge._agent_executor is mock_agent_executor
        assert bridge._agent_repository is mock_agent_repository
        assert bridge._tool_handler is None
        assert bridge._approval_manager is None
        assert bridge._config is not None

    def test_full_init(self, bridge):
        """測試完整初始化"""
        assert bridge._session_service is not None
        assert bridge._agent_executor is not None
        assert bridge._agent_repository is not None
        assert bridge._tool_handler is not None
        assert bridge._approval_manager is not None
        assert bridge._config is not None

    def test_custom_config(
        self,
        mock_session_service,
        mock_agent_executor,
        mock_agent_repository,
    ):
        """測試自訂配置"""
        config = BridgeConfig(max_tool_iterations=3)

        bridge = SessionAgentBridge(
            session_service=mock_session_service,
            agent_executor=mock_agent_executor,
            agent_repository=mock_agent_repository,
            config=config,
        )

        assert bridge._config.max_tool_iterations == 3


class TestSessionAgentBridgeProcessMessage:
    """SessionAgentBridge.process_message 測試"""

    @pytest.mark.asyncio
    async def test_basic_message_processing(self, bridge, mock_session_service):
        """測試基本訊息處理"""
        events = []

        async for event in bridge.process_message(
            session_id="session-123",
            content="Hello",
        ):
            events.append(event)

        assert len(events) > 0
        # 驗證有 started 事件
        assert any(e.event_type == ExecutionEventType.STARTED for e in events)
        # 驗證有 done 事件
        assert any(e.event_type == ExecutionEventType.DONE for e in events)

        # 驗證 session service 被調用
        mock_session_service.send_message.assert_called_once()
        mock_session_service.add_assistant_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_not_found(
        self,
        bridge,
        mock_session_service,
    ):
        """測試 Session 未找到"""
        mock_session_service.get_session = AsyncMock(return_value=None)

        with pytest.raises(SessionNotFoundError):
            async for _ in bridge.process_message(
                session_id="nonexistent",
                content="Hello",
            ):
                pass

    @pytest.mark.asyncio
    async def test_session_not_active(
        self,
        bridge,
        mock_session_service,
        mock_session,
    ):
        """測試 Session 非活躍"""
        mock_session.status = SessionStatus.ENDED
        mock_session_service.get_session = AsyncMock(return_value=mock_session)

        with pytest.raises(SessionNotActiveError):
            async for _ in bridge.process_message(
                session_id="session-123",
                content="Hello",
            ):
                pass

    @pytest.mark.asyncio
    async def test_agent_not_found(
        self,
        bridge,
        mock_agent_repository,
    ):
        """測試 Agent 未找到"""
        mock_agent_repository.get = AsyncMock(return_value=None)

        with pytest.raises(AgentNotFoundError):
            async for _ in bridge.process_message(
                session_id="session-123",
                content="Hello",
            ):
                pass

    @pytest.mark.asyncio
    async def test_with_attachments(self, bridge, mock_session_service):
        """測試帶附件的訊息"""
        attachments = [
            Attachment(
                filename="test.txt",
                content_type="text/plain",
                size=1024,
                storage_path="/uploads/test.txt",
            ),
        ]

        events = []
        async for event in bridge.process_message(
            session_id="session-123",
            content="Check this file",
            attachments=attachments,
        ):
            events.append(event)

        # 驗證附件被傳遞
        call_args = mock_session_service.send_message.call_args
        assert call_args.kwargs.get("attachments") == attachments

    @pytest.mark.asyncio
    async def test_stream_mode_explicit(self, bridge):
        """測試明確指定串流模式"""
        events = []

        async for event in bridge.process_message(
            session_id="session-123",
            content="Hello",
            stream=True,
        ):
            events.append(event)

        # 應該有 content delta 事件
        assert any(e.event_type == ExecutionEventType.CONTENT_DELTA for e in events)

    @pytest.mark.asyncio
    async def test_non_stream_mode(
        self,
        mock_session_service,
        mock_agent_repository,
        mock_tool_handler,
        bridge_config,
    ):
        """測試非串流模式"""
        # 創建返回完整內容的 executor
        executor = MagicMock(spec=AgentExecutor)

        async def mock_execute(*args, **kwargs):
            yield ExecutionEventFactory.started(
                session_id=kwargs.get("session_id", ""),
                execution_id="exec-123",
            )
            yield ExecutionEventFactory.content(
                session_id=kwargs.get("session_id", ""),
                execution_id="exec-123",
                content="Complete response",
            )
            yield ExecutionEventFactory.done(
                session_id=kwargs.get("session_id", ""),
                execution_id="exec-123",
                finish_reason="stop",
            )

        executor.execute = mock_execute

        bridge = SessionAgentBridge(
            session_service=mock_session_service,
            agent_executor=executor,
            agent_repository=mock_agent_repository,
            tool_handler=mock_tool_handler,
            config=bridge_config,
        )

        events = []
        async for event in bridge.process_message(
            session_id="session-123",
            content="Hello",
            stream=False,
        ):
            events.append(event)

        # 應該有 content 事件（非 delta）
        assert any(e.event_type == ExecutionEventType.CONTENT for e in events)


class TestSessionAgentBridgeToolExecution:
    """SessionAgentBridge 工具執行測試"""

    @pytest.mark.asyncio
    async def test_tool_execution_no_approval(
        self,
        mock_session_service,
        mock_agent_repository,
        mock_tool_handler,
        bridge_config,
    ):
        """測試無需審批的工具執行"""
        # 創建返回工具調用的 executor
        executor = MagicMock(spec=AgentExecutor)
        call_count = [0]

        async def mock_execute(*args, **kwargs):
            call_count[0] += 1
            yield ExecutionEventFactory.started(
                session_id=kwargs.get("session_id", ""),
                execution_id="exec-123",
            )

            if call_count[0] == 1:
                # 第一次調用：返回工具調用
                yield ExecutionEventFactory.tool_call(
                    session_id=kwargs.get("session_id", ""),
                    execution_id="exec-123",
                    tool_call_id="tc-123",
                    tool_name="test_tool",
                    arguments={"input": "test"},
                )
                yield ExecutionEventFactory.done(
                    session_id=kwargs.get("session_id", ""),
                    execution_id="exec-123",
                    finish_reason="tool_calls",
                )
            else:
                # 第二次調用：返回最終回應
                yield ExecutionEventFactory.content(
                    session_id=kwargs.get("session_id", ""),
                    execution_id="exec-123",
                    content="Tool result processed",
                )
                yield ExecutionEventFactory.done(
                    session_id=kwargs.get("session_id", ""),
                    execution_id="exec-123",
                    finish_reason="stop",
                )

        executor.execute = mock_execute

        bridge = SessionAgentBridge(
            session_service=mock_session_service,
            agent_executor=executor,
            agent_repository=mock_agent_repository,
            tool_handler=mock_tool_handler,
            config=bridge_config,
        )

        events = []
        async for event in bridge.process_message(
            session_id="session-123",
            content="Use the test tool",
        ):
            events.append(event)

        # 驗證工具被執行
        mock_tool_handler.execute_tool.assert_called()

        # 驗證有工具結果事件
        assert any(e.event_type == ExecutionEventType.TOOL_RESULT for e in events)


class TestSessionAgentBridgeApproval:
    """SessionAgentBridge 審批流程測試"""

    @pytest.mark.asyncio
    async def test_handle_tool_approval_approved(
        self,
        bridge,
        mock_approval_manager,
        mock_tool_handler,
    ):
        """測試批准工具調用"""
        approval = ToolApprovalRequest(
            id="approval-123",
            session_id="session-123",
            execution_id="exec-123",
            tool_call={"id": "tc-123", "name": "test_tool", "arguments": {}},
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow(),
            status=ApprovalStatus.APPROVED,
        )
        mock_approval_manager.resolve_approval = AsyncMock(return_value=approval)

        events = []
        async for event in bridge.handle_tool_approval(
            session_id="session-123",
            approval_id="approval-123",
            approved=True,
            feedback="Approved",
            approver_id="user-456",
        ):
            events.append(event)

        # 驗證審批被處理
        mock_approval_manager.resolve_approval.assert_called_once()

        # 驗證有審批回應事件
        assert any(
            e.event_type == ExecutionEventType.APPROVAL_RESPONSE for e in events
        )

    @pytest.mark.asyncio
    async def test_handle_tool_approval_rejected(
        self,
        bridge,
        mock_approval_manager,
    ):
        """測試拒絕工具調用"""
        approval = ToolApprovalRequest(
            id="approval-123",
            session_id="session-123",
            execution_id="exec-123",
            tool_call={"id": "tc-123", "name": "test_tool", "arguments": {}},
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow(),
            status=ApprovalStatus.REJECTED,
        )
        mock_approval_manager.resolve_approval = AsyncMock(return_value=approval)

        events = []
        async for event in bridge.handle_tool_approval(
            session_id="session-123",
            approval_id="approval-123",
            approved=False,
            feedback="Not allowed",
            approver_id="user-456",
        ):
            events.append(event)

        # 驗證審批回應
        approval_responses = [
            e for e in events
            if e.event_type == ExecutionEventType.APPROVAL_RESPONSE
        ]
        assert len(approval_responses) == 1

    @pytest.mark.asyncio
    async def test_handle_approval_no_manager(
        self,
        mock_session_service,
        mock_agent_executor,
        mock_agent_repository,
    ):
        """測試沒有審批管理器時的處理"""
        bridge = SessionAgentBridge(
            session_service=mock_session_service,
            agent_executor=mock_agent_executor,
            agent_repository=mock_agent_repository,
            approval_manager=None,
        )

        events = []
        async for event in bridge.handle_tool_approval(
            session_id="session-123",
            approval_id="approval-123",
            approved=True,
        ):
            events.append(event)

        # 應該返回錯誤事件
        assert any(e.event_type == ExecutionEventType.ERROR for e in events)

    @pytest.mark.asyncio
    async def test_get_pending_approvals(self, bridge, mock_approval_manager):
        """測試獲取待處理審批"""
        pending = [
            ToolApprovalRequest(
                id="approval-1",
                session_id="session-123",
                execution_id="exec-1",
                tool_call={"id": "tc-1", "name": "tool1", "arguments": {}},
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow(),
            ),
            ToolApprovalRequest(
                id="approval-2",
                session_id="session-123",
                execution_id="exec-2",
                tool_call={"id": "tc-2", "name": "tool2", "arguments": {}},
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow(),
            ),
        ]
        mock_approval_manager.get_pending_approvals = AsyncMock(return_value=pending)

        result = await bridge.get_pending_approvals("session-123")

        assert len(result) == 2
        mock_approval_manager.get_pending_approvals.assert_called_once_with(
            "session-123"
        )

    @pytest.mark.asyncio
    async def test_get_pending_approvals_no_manager(
        self,
        mock_session_service,
        mock_agent_executor,
        mock_agent_repository,
    ):
        """測試沒有審批管理器時獲取待處理審批"""
        bridge = SessionAgentBridge(
            session_service=mock_session_service,
            agent_executor=mock_agent_executor,
            agent_repository=mock_agent_repository,
            approval_manager=None,
        )

        result = await bridge.get_pending_approvals("session-123")

        assert result == []

    @pytest.mark.asyncio
    async def test_cancel_pending_approvals(self, bridge, mock_approval_manager):
        """測試取消待處理審批"""
        pending = [
            ToolApprovalRequest(
                id="approval-1",
                session_id="session-123",
                execution_id="exec-1",
                tool_call={"id": "tc-1", "name": "tool1", "arguments": {}},
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow(),
            ),
        ]
        mock_approval_manager.get_pending_approvals = AsyncMock(return_value=pending)
        mock_approval_manager.cancel_approval = AsyncMock(return_value=True)

        cancelled = await bridge.cancel_pending_approvals(
            session_id="session-123",
            reason="User cancelled",
        )

        assert cancelled == 1
        mock_approval_manager.cancel_approval.assert_called_once()


class TestSessionAgentBridgeErrors:
    """SessionAgentBridge 錯誤處理測試"""

    @pytest.mark.asyncio
    async def test_error_event_on_exception(
        self,
        mock_session_service,
        mock_agent_repository,
        bridge_config,
    ):
        """測試異常時返回錯誤事件"""
        executor = MagicMock(spec=AgentExecutor)

        async def mock_execute(*args, **kwargs):
            yield ExecutionEventFactory.started(
                session_id=kwargs.get("session_id", ""),
                execution_id="exec-123",
            )
            raise RuntimeError("Unexpected error")

        executor.execute = mock_execute

        bridge = SessionAgentBridge(
            session_service=mock_session_service,
            agent_executor=executor,
            agent_repository=mock_agent_repository,
            config=bridge_config,
        )

        events = []
        async for event in bridge.process_message(
            session_id="session-123",
            content="Hello",
        ):
            events.append(event)

        # 應該有錯誤事件
        assert any(e.event_type == ExecutionEventType.ERROR for e in events)


class TestCreateSessionAgentBridge:
    """create_session_agent_bridge 工廠函數測試"""

    def test_basic_creation(
        self,
        mock_session_service,
        mock_agent_executor,
        mock_agent_repository,
    ):
        """測試基本創建"""
        bridge = create_session_agent_bridge(
            session_service=mock_session_service,
            agent_executor=mock_agent_executor,
            agent_repository=mock_agent_repository,
        )

        assert isinstance(bridge, SessionAgentBridge)

    def test_full_creation(
        self,
        mock_session_service,
        mock_agent_executor,
        mock_agent_repository,
        mock_tool_handler,
        mock_approval_manager,
        bridge_config,
    ):
        """測試完整創建"""
        bridge = create_session_agent_bridge(
            session_service=mock_session_service,
            agent_executor=mock_agent_executor,
            agent_repository=mock_agent_repository,
            tool_handler=mock_tool_handler,
            approval_manager=mock_approval_manager,
            config=bridge_config,
        )

        assert isinstance(bridge, SessionAgentBridge)
        assert bridge._tool_handler is mock_tool_handler
        assert bridge._approval_manager is mock_approval_manager
        assert bridge._config is bridge_config


class TestBridgeIntegration:
    """SessionAgentBridge 整合測試"""

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, bridge, mock_session_service):
        """測試完整對話流程"""
        # 第一輪對話
        events1 = []
        async for event in bridge.process_message(
            session_id="session-123",
            content="Hello",
        ):
            events1.append(event)

        assert len(events1) > 0
        assert any(e.event_type == ExecutionEventType.DONE for e in events1)

        # 重置 mock 調用記錄
        mock_session_service.send_message.reset_mock()
        mock_session_service.add_assistant_message.reset_mock()

        # 第二輪對話
        events2 = []
        async for event in bridge.process_message(
            session_id="session-123",
            content="How are you?",
        ):
            events2.append(event)

        assert len(events2) > 0

        # 驗證兩輪都調用了服務
        mock_session_service.send_message.assert_called()
        mock_session_service.add_assistant_message.assert_called()

    @pytest.mark.asyncio
    async def test_content_aggregation(self, bridge, mock_session_service):
        """測試內容聚合"""
        events = []
        async for event in bridge.process_message(
            session_id="session-123",
            content="Hello",
        ):
            events.append(event)

        # 獲取 add_assistant_message 調用參數
        call_args = mock_session_service.add_assistant_message.call_args
        content = call_args.kwargs.get("content", "")

        # 驗證內容被正確聚合
        assert "Hello" in content and "there!" in content


class TestBridgeEdgeCases:
    """SessionAgentBridge 邊緣情況測試"""

    @pytest.mark.asyncio
    async def test_empty_content(self, bridge, mock_session_service):
        """測試空內容"""
        events = []
        async for event in bridge.process_message(
            session_id="session-123",
            content="",
        ):
            events.append(event)

        # 即使內容為空也應該處理
        mock_session_service.send_message.assert_called()

    @pytest.mark.asyncio
    async def test_execution_config_override(self, bridge):
        """測試執行配置覆蓋"""
        custom_config = ExecutionConfig(
            stream=False,
            max_tokens=2048,
            temperature=0.5,
        )

        events = []
        async for event in bridge.process_message(
            session_id="session-123",
            content="Hello",
            execution_config=custom_config,
        ):
            events.append(event)

        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_suspended_session(
        self,
        bridge,
        mock_session_service,
        mock_session,
    ):
        """測試暫停的 Session"""
        mock_session.status = SessionStatus.SUSPENDED
        mock_session_service.get_session = AsyncMock(return_value=mock_session)

        with pytest.raises(SessionNotActiveError):
            async for _ in bridge.process_message(
                session_id="session-123",
                content="Hello",
            ):
                pass
