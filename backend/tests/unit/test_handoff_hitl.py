# =============================================================================
# Unit Tests for Handoff Human-in-the-Loop (HITL) Module
# =============================================================================
# Sprint 15: HandoffBuilder 重構 - S15-5 測試
# Phase 3 Feature: P3-F2 (Agent Handoff 重構)
#
# 測試內容:
#   - HITLSessionStatus 枚舉
#   - HITLInputType 枚舉
#   - HITLInputRequest 數據類
#   - HITLInputResponse 數據類
#   - HITLSession 數據類
#   - HITLCallback 協議
#   - DefaultHITLCallback 類
#   - HITLManager 類
#   - HITLCheckpointAdapter 類
#   - 工廠函數
# =============================================================================

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.integrations.agent_framework.builders.handoff_hitl import (
    DefaultHITLCallback,
    HITLCheckpointAdapter,
    HITLInputRequest,
    HITLInputResponse,
    HITLInputType,
    HITLManager,
    HITLSession,
    HITLSessionStatus,
    create_hitl_checkpoint_adapter,
    create_hitl_manager,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def hitl_manager():
    """創建 HITL 管理器."""
    return HITLManager()


@pytest.fixture
def mock_callback():
    """創建模擬回調."""
    callback = MagicMock()
    callback.on_input_requested = AsyncMock()
    callback.on_input_received = AsyncMock()
    callback.on_session_completed = AsyncMock()
    callback.on_session_timeout = AsyncMock()
    callback.on_session_escalated = AsyncMock()
    return callback


@pytest.fixture
def mock_checkpoint_service():
    """創建模擬 checkpoint 服務."""
    service = MagicMock()
    service.create_checkpoint = AsyncMock(return_value=MagicMock(id=uuid4()))
    service.complete_checkpoint = AsyncMock()
    return service


@pytest.fixture
def sample_conversation():
    """創建示例對話."""
    return [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help?"},
        {"role": "user", "content": "I need a refund"},
    ]


# =============================================================================
# Test HITLSessionStatus Enum
# =============================================================================


class TestHITLSessionStatus:
    """HITLSessionStatus 枚舉測試."""

    def test_all_status_values(self):
        """測試所有狀態值."""
        expected = {
            "active", "input_received", "processing",
            "completed", "timeout", "cancelled", "escalated"
        }
        actual = {s.value for s in HITLSessionStatus}
        assert actual == expected

    def test_status_count(self):
        """測試狀態數量."""
        assert len(HITLSessionStatus) == 7

    def test_active_status(self):
        """測試 ACTIVE 狀態."""
        assert HITLSessionStatus.ACTIVE.value == "active"

    def test_escalated_status(self):
        """測試 ESCALATED 狀態."""
        assert HITLSessionStatus.ESCALATED.value == "escalated"


# =============================================================================
# Test HITLInputType Enum
# =============================================================================


class TestHITLInputType:
    """HITLInputType 枚舉測試."""

    def test_all_input_types(self):
        """測試所有輸入類型."""
        expected = {"text", "choice", "confirmation", "file", "form"}
        actual = {t.value for t in HITLInputType}
        assert actual == expected

    def test_input_type_count(self):
        """測試輸入類型數量."""
        assert len(HITLInputType) == 5

    def test_text_type(self):
        """測試 TEXT 類型."""
        assert HITLInputType.TEXT.value == "text"

    def test_confirmation_type(self):
        """測試 CONFIRMATION 類型."""
        assert HITLInputType.CONFIRMATION.value == "confirmation"


# =============================================================================
# Test HITLInputRequest Data Class
# =============================================================================


class TestHITLInputRequest:
    """HITLInputRequest 數據類測試."""

    def test_default_creation(self):
        """測試默認創建."""
        request = HITLInputRequest()
        assert request.request_id is not None
        assert isinstance(request.request_id, UUID)
        assert request.session_id is None
        assert request.conversation == []
        assert request.awaiting_agent_id == ""
        assert request.prompt == "Please provide your input."
        assert request.input_type == HITLInputType.TEXT
        assert request.choices == []
        assert request.default_value is None
        assert request.timeout_seconds == 300
        assert request.created_at is not None

    def test_custom_creation(self, sample_conversation):
        """測試自定義創建."""
        session_id = uuid4()
        request = HITLInputRequest(
            session_id=session_id,
            conversation=sample_conversation,
            awaiting_agent_id="refund_agent",
            prompt="Please confirm the refund",
            input_type=HITLInputType.CONFIRMATION,
            timeout_seconds=600,
        )
        assert request.session_id == session_id
        assert len(request.conversation) == 3
        assert request.awaiting_agent_id == "refund_agent"
        assert request.input_type == HITLInputType.CONFIRMATION
        assert request.timeout_seconds == 600

    def test_choice_input_type(self):
        """測試選項輸入類型."""
        request = HITLInputRequest(
            input_type=HITLInputType.CHOICE,
            choices=["Option A", "Option B", "Option C"],
        )
        assert request.input_type == HITLInputType.CHOICE
        assert len(request.choices) == 3

    def test_expires_at_property(self):
        """測試過期時間計算."""
        request = HITLInputRequest(timeout_seconds=300)
        expected_expiry = request.created_at + timedelta(seconds=300)
        assert request.expires_at == expected_expiry

    def test_is_expired_property_not_expired(self):
        """測試未過期判斷."""
        request = HITLInputRequest(timeout_seconds=300)
        assert request.is_expired is False

    def test_is_expired_property_expired(self):
        """測試已過期判斷."""
        request = HITLInputRequest(timeout_seconds=0)
        # 創建一個已過期的請求
        request.created_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        assert request.is_expired is True


# =============================================================================
# Test HITLInputResponse Data Class
# =============================================================================


class TestHITLInputResponse:
    """HITLInputResponse 數據類測試."""

    def test_default_creation(self):
        """測試默認創建."""
        response = HITLInputResponse()
        assert response.response_id is not None
        assert isinstance(response.response_id, UUID)
        assert response.request_id is not None
        assert response.input_value is None
        assert response.input_type == HITLInputType.TEXT
        assert response.user_id is None
        assert response.responded_at is not None

    def test_custom_creation(self):
        """測試自定義創建."""
        request_id = uuid4()
        response = HITLInputResponse(
            request_id=request_id,
            input_value="Yes, proceed with refund",
            input_type=HITLInputType.CONFIRMATION,
            user_id="user-123",
            metadata={"ip_address": "192.168.1.1"},
        )
        assert response.request_id == request_id
        assert response.input_value == "Yes, proceed with refund"
        assert response.input_type == HITLInputType.CONFIRMATION
        assert response.user_id == "user-123"
        assert "ip_address" in response.metadata


# =============================================================================
# Test HITLSession Data Class
# =============================================================================


class TestHITLSession:
    """HITLSession 數據類測試."""

    def test_default_creation(self):
        """測試默認創建."""
        session = HITLSession()
        assert session.session_id is not None
        assert isinstance(session.session_id, UUID)
        assert session.handoff_execution_id is None
        assert session.status == HITLSessionStatus.ACTIVE
        assert session.current_request is None
        assert session.history == []
        assert session.created_at is not None
        assert session.updated_at is not None
        assert session.completed_at is None
        assert session.checkpoint_id is None

    def test_custom_creation(self):
        """測試自定義創建."""
        execution_id = uuid4()
        checkpoint_id = uuid4()
        session = HITLSession(
            handoff_execution_id=execution_id,
            checkpoint_id=checkpoint_id,
            metadata={"source": "api"},
        )
        assert session.handoff_execution_id == execution_id
        assert session.checkpoint_id == checkpoint_id
        assert session.metadata["source"] == "api"

    def test_add_request(self):
        """測試添加請求."""
        session = HITLSession()
        request = HITLInputRequest(
            prompt="Test prompt",
            input_type=HITLInputType.TEXT,
        )

        session.add_request(request)

        assert session.current_request == request
        assert len(session.history) == 1
        assert session.history[0]["type"] == "request"
        assert session.history[0]["prompt"] == "Test prompt"

    def test_add_response(self):
        """測試添加回應."""
        session = HITLSession()
        request = HITLInputRequest()
        session.add_request(request)

        response = HITLInputResponse(
            request_id=request.request_id,
            input_value="Test response",
        )
        session.add_response(response)

        assert session.current_request is None
        assert len(session.history) == 2
        assert session.history[1]["type"] == "response"


# =============================================================================
# Test DefaultHITLCallback
# =============================================================================


class TestDefaultHITLCallback:
    """DefaultHITLCallback 測試."""

    @pytest.mark.asyncio
    async def test_on_input_requested(self):
        """測試輸入請求回調."""
        callback = DefaultHITLCallback()
        session = HITLSession()
        request = HITLInputRequest()

        # 應該不拋出異常
        await callback.on_input_requested(session, request)

    @pytest.mark.asyncio
    async def test_on_input_received(self):
        """測試輸入接收回調."""
        callback = DefaultHITLCallback()
        session = HITLSession()
        response = HITLInputResponse()

        await callback.on_input_received(session, response)

    @pytest.mark.asyncio
    async def test_on_session_completed(self):
        """測試會話完成回調."""
        callback = DefaultHITLCallback()
        session = HITLSession()

        await callback.on_session_completed(session)

    @pytest.mark.asyncio
    async def test_on_session_timeout(self):
        """測試會話超時回調."""
        callback = DefaultHITLCallback()
        session = HITLSession()

        await callback.on_session_timeout(session)

    @pytest.mark.asyncio
    async def test_on_session_escalated(self):
        """測試會話升級回調."""
        callback = DefaultHITLCallback()
        session = HITLSession()

        await callback.on_session_escalated(session, "Test reason")


# =============================================================================
# Test HITLManager Initialization
# =============================================================================


class TestHITLManagerInit:
    """HITLManager 初始化測試."""

    def test_basic_init(self):
        """測試基本初始化."""
        manager = HITLManager()
        assert manager.active_sessions == {}
        assert manager._default_timeout == 300

    def test_init_with_callback(self, mock_callback):
        """測試帶回調初始化."""
        manager = HITLManager(callback=mock_callback)
        assert manager._callback == mock_callback

    def test_init_with_checkpoint_service(self, mock_checkpoint_service):
        """測試帶 checkpoint 服務初始化."""
        manager = HITLManager(checkpoint_service=mock_checkpoint_service)
        assert manager._checkpoint_service == mock_checkpoint_service

    def test_init_custom_timeout(self):
        """測試自定義超時."""
        manager = HITLManager(default_timeout=600)
        assert manager._default_timeout == 600


# =============================================================================
# Test HITLManager Session Management
# =============================================================================


class TestHITLManagerSessions:
    """HITLManager 會話管理測試."""

    @pytest.mark.asyncio
    async def test_create_session_basic(self, hitl_manager):
        """測試創建基本會話."""
        session = await hitl_manager.create_session()

        assert session is not None
        assert session.session_id in hitl_manager._sessions
        assert session.status == HITLSessionStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_create_session_with_execution_id(self, hitl_manager):
        """測試帶執行 ID 創建會話."""
        execution_id = uuid4()
        session = await hitl_manager.create_session(
            handoff_execution_id=execution_id,
        )

        assert session.handoff_execution_id == execution_id

    @pytest.mark.asyncio
    async def test_create_session_with_checkpoint(
        self, mock_checkpoint_service
    ):
        """測試帶 checkpoint 創建會話."""
        manager = HITLManager(checkpoint_service=mock_checkpoint_service)
        execution_id = uuid4()

        session = await manager.create_session(
            handoff_execution_id=execution_id,
            create_checkpoint=True,
        )

        mock_checkpoint_service.create_checkpoint.assert_called_once()
        assert session.checkpoint_id is not None

    @pytest.mark.asyncio
    async def test_create_session_with_metadata(self, hitl_manager):
        """測試帶元數據創建會話."""
        session = await hitl_manager.create_session(
            metadata={"source": "api", "priority": "high"},
        )

        assert session.metadata["source"] == "api"
        assert session.metadata["priority"] == "high"

    def test_get_session(self, hitl_manager):
        """測試獲取會話."""
        session = HITLSession()
        hitl_manager._sessions[session.session_id] = session

        result = hitl_manager.get_session(session.session_id)
        assert result == session

    def test_get_session_not_found(self, hitl_manager):
        """測試獲取不存在的會話."""
        fake_id = uuid4()
        result = hitl_manager.get_session(fake_id)
        assert result is None

    def test_active_sessions_property(self, hitl_manager):
        """測試活躍會話屬性."""
        active_session = HITLSession(status=HITLSessionStatus.ACTIVE)
        completed_session = HITLSession(status=HITLSessionStatus.COMPLETED)

        hitl_manager._sessions[active_session.session_id] = active_session
        hitl_manager._sessions[completed_session.session_id] = completed_session

        active = hitl_manager.active_sessions
        assert len(active) == 1
        assert active_session.session_id in active


# =============================================================================
# Test HITLManager Request Input
# =============================================================================


class TestHITLManagerRequestInput:
    """HITLManager request_input 測試."""

    @pytest.mark.asyncio
    async def test_request_input_basic(
        self, hitl_manager, sample_conversation
    ):
        """測試基本請求輸入."""
        session = await hitl_manager.create_session()

        request = await hitl_manager.request_input(
            session_id=session.session_id,
            prompt="Please confirm",
            awaiting_agent_id="refund_agent",
        )

        assert request is not None
        assert request.session_id == session.session_id
        assert request.prompt == "Please confirm"
        assert session.current_request == request

    @pytest.mark.asyncio
    async def test_request_input_with_choices(self, hitl_manager):
        """測試帶選項請求輸入."""
        session = await hitl_manager.create_session()

        request = await hitl_manager.request_input(
            session_id=session.session_id,
            prompt="Select option",
            input_type=HITLInputType.CHOICE,
            choices=["A", "B", "C"],
        )

        assert request.input_type == HITLInputType.CHOICE
        assert request.choices == ["A", "B", "C"]

    @pytest.mark.asyncio
    async def test_request_input_with_conversation(
        self, hitl_manager, sample_conversation
    ):
        """測試帶對話歷史請求輸入."""
        session = await hitl_manager.create_session()

        request = await hitl_manager.request_input(
            session_id=session.session_id,
            prompt="Continue?",
            conversation=sample_conversation,
        )

        assert len(request.conversation) == 3

    @pytest.mark.asyncio
    async def test_request_input_callback_called(
        self, mock_callback
    ):
        """測試請求輸入時回調被調用."""
        manager = HITLManager(callback=mock_callback)
        session = await manager.create_session()

        await manager.request_input(
            session_id=session.session_id,
            prompt="Test",
        )

        mock_callback.on_input_requested.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_input_session_not_found(self, hitl_manager):
        """測試請求輸入會話不存在."""
        fake_id = uuid4()

        with pytest.raises(ValueError, match="not found"):
            await hitl_manager.request_input(
                session_id=fake_id,
                prompt="Test",
            )

    @pytest.mark.asyncio
    async def test_request_input_session_not_active(self, hitl_manager):
        """測試請求輸入會話非活躍."""
        session = await hitl_manager.create_session()
        session.status = HITLSessionStatus.COMPLETED

        with pytest.raises(ValueError, match="not active"):
            await hitl_manager.request_input(
                session_id=session.session_id,
                prompt="Test",
            )


# =============================================================================
# Test HITLManager Submit Input
# =============================================================================


class TestHITLManagerSubmitInput:
    """HITLManager submit_input 測試."""

    @pytest.mark.asyncio
    async def test_submit_input_basic(self, hitl_manager):
        """測試基本提交輸入."""
        session = await hitl_manager.create_session()
        request = await hitl_manager.request_input(
            session_id=session.session_id,
            prompt="Test",
        )

        response = await hitl_manager.submit_input(
            request_id=request.request_id,
            input_value="User response",
        )

        assert response is not None
        assert response.request_id == request.request_id
        assert response.input_value == "User response"
        assert session.status == HITLSessionStatus.INPUT_RECEIVED

    @pytest.mark.asyncio
    async def test_submit_input_with_user_id(self, hitl_manager):
        """測試帶用戶 ID 提交輸入."""
        session = await hitl_manager.create_session()
        request = await hitl_manager.request_input(
            session_id=session.session_id,
            prompt="Test",
        )

        response = await hitl_manager.submit_input(
            request_id=request.request_id,
            input_value="Response",
            user_id="user-456",
        )

        assert response.user_id == "user-456"

    @pytest.mark.asyncio
    async def test_submit_input_callback_called(self, mock_callback):
        """測試提交輸入時回調被調用."""
        manager = HITLManager(callback=mock_callback)
        session = await manager.create_session()
        request = await manager.request_input(
            session_id=session.session_id,
            prompt="Test",
        )

        await manager.submit_input(
            request_id=request.request_id,
            input_value="Response",
        )

        mock_callback.on_input_received.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_input_request_not_found(self, hitl_manager):
        """測試提交輸入請求不存在."""
        fake_id = uuid4()

        with pytest.raises(ValueError, match="not found"):
            await hitl_manager.submit_input(
                request_id=fake_id,
                input_value="Response",
            )

    @pytest.mark.asyncio
    async def test_submit_input_wrong_request(self, hitl_manager):
        """測試提交輸入錯誤請求."""
        session = await hitl_manager.create_session()
        request = await hitl_manager.request_input(
            session_id=session.session_id,
            prompt="Test",
        )

        # 創建新請求
        request2 = await hitl_manager.request_input(
            session_id=session.session_id,
            prompt="Test 2",
        )

        # 嘗試提交舊請求
        with pytest.raises(ValueError, match="not the current request"):
            await hitl_manager.submit_input(
                request_id=request.request_id,
                input_value="Response",
            )


# =============================================================================
# Test HITLManager Wait For Input
# =============================================================================


class TestHITLManagerWaitForInput:
    """HITLManager wait_for_input 測試."""

    @pytest.mark.asyncio
    async def test_wait_for_input_success(self, hitl_manager):
        """測試等待輸入成功."""
        session = await hitl_manager.create_session()
        request = await hitl_manager.request_input(
            session_id=session.session_id,
            prompt="Test",
        )

        # 模擬在另一個任務中提交輸入
        async def submit_later():
            await asyncio.sleep(0.1)
            await hitl_manager.submit_input(
                request_id=request.request_id,
                input_value="Response",
            )

        task = asyncio.create_task(submit_later())

        response = await hitl_manager.wait_for_input(
            request_id=request.request_id,
            timeout=5.0,
        )

        await task
        assert response.input_value == "Response"

    @pytest.mark.asyncio
    async def test_wait_for_input_timeout(self, hitl_manager):
        """測試等待輸入超時."""
        session = await hitl_manager.create_session()
        request = await hitl_manager.request_input(
            session_id=session.session_id,
            prompt="Test",
        )

        with pytest.raises(TimeoutError):
            await hitl_manager.wait_for_input(
                request_id=request.request_id,
                timeout=0.1,
            )

    @pytest.mark.asyncio
    async def test_wait_for_input_request_not_found(self, hitl_manager):
        """測試等待不存在的請求."""
        fake_id = uuid4()

        with pytest.raises(ValueError, match="not found"):
            await hitl_manager.wait_for_input(
                request_id=fake_id,
                timeout=1.0,
            )


# =============================================================================
# Test HITLManager Session Lifecycle
# =============================================================================


class TestHITLManagerLifecycle:
    """HITLManager 會話生命週期測試."""

    @pytest.mark.asyncio
    async def test_complete_session(self, hitl_manager):
        """測試完成會話."""
        session = await hitl_manager.create_session()

        completed = await hitl_manager.complete_session(session.session_id)

        assert completed.status == HITLSessionStatus.COMPLETED
        assert completed.completed_at is not None

    @pytest.mark.asyncio
    async def test_complete_session_with_checkpoint(
        self, mock_checkpoint_service
    ):
        """測試完成帶 checkpoint 的會話."""
        manager = HITLManager(checkpoint_service=mock_checkpoint_service)
        session = await manager.create_session(create_checkpoint=True)

        await manager.complete_session(session.session_id)

        mock_checkpoint_service.complete_checkpoint.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_session_callback_called(self, mock_callback):
        """測試完成會話回調被調用."""
        manager = HITLManager(callback=mock_callback)
        session = await manager.create_session()

        await manager.complete_session(session.session_id)

        mock_callback.on_session_completed.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_session_not_found(self, hitl_manager):
        """測試完成不存在的會話."""
        fake_id = uuid4()

        with pytest.raises(ValueError, match="not found"):
            await hitl_manager.complete_session(fake_id)

    @pytest.mark.asyncio
    async def test_cancel_session(self, hitl_manager):
        """測試取消會話."""
        session = await hitl_manager.create_session()

        cancelled = await hitl_manager.cancel_session(
            session.session_id,
            reason="User request",
        )

        assert cancelled.status == HITLSessionStatus.CANCELLED
        assert cancelled.metadata["cancel_reason"] == "User request"

    @pytest.mark.asyncio
    async def test_cancel_session_with_pending_request(self, hitl_manager):
        """測試取消帶等待請求的會話."""
        session = await hitl_manager.create_session()
        request = await hitl_manager.request_input(
            session_id=session.session_id,
            prompt="Test",
        )

        await hitl_manager.cancel_session(session.session_id)

        # 確保等待的 Future 被取消
        assert request.request_id not in hitl_manager._waiting_futures

    @pytest.mark.asyncio
    async def test_escalate_session(self, hitl_manager):
        """測試升級會話."""
        session = await hitl_manager.create_session()

        escalated = await hitl_manager.escalate_session(
            session.session_id,
            reason="Complex issue",
            escalation_target="supervisor",
        )

        assert escalated.status == HITLSessionStatus.ESCALATED
        assert escalated.metadata["escalation_reason"] == "Complex issue"
        assert escalated.metadata["escalation_target"] == "supervisor"

    @pytest.mark.asyncio
    async def test_escalate_session_callback_called(self, mock_callback):
        """測試升級會話回調被調用."""
        manager = HITLManager(callback=mock_callback)
        session = await manager.create_session()

        await manager.escalate_session(session.session_id, reason="Test")

        mock_callback.on_session_escalated.assert_called_once()


# =============================================================================
# Test HITLManager Pending Requests
# =============================================================================


class TestHITLManagerPendingRequests:
    """HITLManager 等待請求測試."""

    @pytest.mark.asyncio
    async def test_get_pending_requests_empty(self, hitl_manager):
        """測試獲取空的等待請求列表."""
        requests = hitl_manager.get_pending_requests()
        assert requests == []

    @pytest.mark.asyncio
    async def test_get_pending_requests_with_requests(self, hitl_manager):
        """測試獲取等待請求列表."""
        session1 = await hitl_manager.create_session()
        session2 = await hitl_manager.create_session()

        await hitl_manager.request_input(
            session_id=session1.session_id,
            prompt="Request 1",
        )
        await hitl_manager.request_input(
            session_id=session2.session_id,
            prompt="Request 2",
        )

        requests = hitl_manager.get_pending_requests()
        assert len(requests) == 2


# =============================================================================
# Test HITLManager Start/Stop
# =============================================================================


class TestHITLManagerStartStop:
    """HITLManager 啟動/停止測試."""

    @pytest.mark.asyncio
    async def test_start(self, hitl_manager):
        """測試啟動管理器."""
        await hitl_manager.start()
        assert hitl_manager._timeout_task is not None
        await hitl_manager.stop()

    @pytest.mark.asyncio
    async def test_stop(self, hitl_manager):
        """測試停止管理器."""
        await hitl_manager.start()
        await hitl_manager.stop()
        assert hitl_manager._timeout_task is None

    @pytest.mark.asyncio
    async def test_multiple_starts(self, hitl_manager):
        """測試多次啟動."""
        await hitl_manager.start()
        task1 = hitl_manager._timeout_task

        await hitl_manager.start()
        task2 = hitl_manager._timeout_task

        # 不應該創建新任務
        assert task1 == task2
        await hitl_manager.stop()


# =============================================================================
# Test HITLCheckpointAdapter
# =============================================================================


class TestHITLCheckpointAdapter:
    """HITLCheckpointAdapter 測試."""

    @pytest.mark.asyncio
    async def test_create_hitl_checkpoint(self, mock_checkpoint_service):
        """測試創建 HITL checkpoint."""
        manager = HITLManager(checkpoint_service=mock_checkpoint_service)
        adapter = HITLCheckpointAdapter(
            hitl_manager=manager,
            checkpoint_service=mock_checkpoint_service,
        )

        execution_id = uuid4()
        handoff_context = {
            "task_id": "task-001",
            "conversation": [{"role": "user", "content": "Hello"}],
        }

        session = await adapter.create_hitl_checkpoint(
            execution_id=execution_id,
            handoff_context=handoff_context,
            prompt="Please confirm",
            awaiting_agent_id="agent-1",
        )

        assert session is not None
        assert session.handoff_execution_id == execution_id
        assert session.current_request is not None

    @pytest.mark.asyncio
    async def test_process_checkpoint_approval_approved(
        self, mock_checkpoint_service
    ):
        """測試處理 checkpoint 批准."""
        manager = HITLManager(checkpoint_service=mock_checkpoint_service)
        adapter = HITLCheckpointAdapter(
            hitl_manager=manager,
            checkpoint_service=mock_checkpoint_service,
        )

        # 創建 checkpoint
        session = await adapter.create_hitl_checkpoint(
            execution_id=uuid4(),
            handoff_context={},
            prompt="Confirm",
            awaiting_agent_id="agent",
        )

        # 批准
        response = await adapter.process_checkpoint_approval(
            checkpoint_id=session.checkpoint_id,
            approved=True,
            approver_id="admin",
            comments="Looks good",
        )

        assert response is not None
        assert "approved" in response.input_value
        assert response.metadata["approved"] is True

    @pytest.mark.asyncio
    async def test_process_checkpoint_approval_rejected(
        self, mock_checkpoint_service
    ):
        """測試處理 checkpoint 拒絕."""
        manager = HITLManager(checkpoint_service=mock_checkpoint_service)
        adapter = HITLCheckpointAdapter(
            hitl_manager=manager,
            checkpoint_service=mock_checkpoint_service,
        )

        session = await adapter.create_hitl_checkpoint(
            execution_id=uuid4(),
            handoff_context={},
            prompt="Confirm",
            awaiting_agent_id="agent",
        )

        response = await adapter.process_checkpoint_approval(
            checkpoint_id=session.checkpoint_id,
            approved=False,
            approver_id="admin",
            comments="Need more info",
        )

        assert "rejected" in response.input_value
        assert response.metadata["approved"] is False

    @pytest.mark.asyncio
    async def test_process_checkpoint_not_found(
        self, mock_checkpoint_service
    ):
        """測試處理不存在的 checkpoint."""
        manager = HITLManager()
        adapter = HITLCheckpointAdapter(
            hitl_manager=manager,
            checkpoint_service=mock_checkpoint_service,
        )

        fake_id = uuid4()

        with pytest.raises(ValueError, match="No HITL session"):
            await adapter.process_checkpoint_approval(
                checkpoint_id=fake_id,
                approved=True,
                approver_id="admin",
            )


# =============================================================================
# Test Factory Functions
# =============================================================================


class TestFactoryFunctions:
    """工廠函數測試."""

    def test_create_hitl_manager_basic(self):
        """測試創建基本 HITL 管理器."""
        manager = create_hitl_manager()
        assert manager is not None
        assert isinstance(manager, HITLManager)

    def test_create_hitl_manager_with_options(
        self, mock_checkpoint_service, mock_callback
    ):
        """測試帶選項創建 HITL 管理器."""
        manager = create_hitl_manager(
            checkpoint_service=mock_checkpoint_service,
            callback=mock_callback,
            default_timeout=600,
        )

        assert manager._checkpoint_service == mock_checkpoint_service
        assert manager._callback == mock_callback
        assert manager._default_timeout == 600

    def test_create_hitl_checkpoint_adapter(self, mock_checkpoint_service):
        """測試創建 checkpoint 適配器."""
        manager = HITLManager()
        adapter = create_hitl_checkpoint_adapter(
            hitl_manager=manager,
            checkpoint_service=mock_checkpoint_service,
        )

        assert adapter is not None
        assert isinstance(adapter, HITLCheckpointAdapter)
        assert adapter._hitl_manager == manager


# =============================================================================
# Integration Tests
# =============================================================================


class TestHITLIntegration:
    """HITL 整合測試."""

    @pytest.mark.asyncio
    async def test_full_hitl_workflow(self, mock_callback):
        """測試完整 HITL 工作流."""
        manager = HITLManager(callback=mock_callback)

        # 1. 創建會話
        session = await manager.create_session(
            metadata={"workflow": "refund"},
        )
        assert session.status == HITLSessionStatus.ACTIVE

        # 2. 請求輸入
        request = await manager.request_input(
            session_id=session.session_id,
            prompt="Please confirm refund of $100",
            input_type=HITLInputType.CONFIRMATION,
            awaiting_agent_id="refund_agent",
        )
        assert session.current_request == request
        mock_callback.on_input_requested.assert_called_once()

        # 3. 提交輸入
        response = await manager.submit_input(
            request_id=request.request_id,
            input_value="approved",
            user_id="user-123",
        )
        assert session.status == HITLSessionStatus.INPUT_RECEIVED
        mock_callback.on_input_received.assert_called_once()

        # 4. 完成會話
        await manager.complete_session(session.session_id)
        assert session.status == HITLSessionStatus.COMPLETED
        mock_callback.on_session_completed.assert_called_once()

    @pytest.mark.asyncio
    async def test_hitl_timeout_workflow(self, mock_callback):
        """測試 HITL 超時工作流."""
        manager = HITLManager(callback=mock_callback, default_timeout=1)

        session = await manager.create_session()
        request = await manager.request_input(
            session_id=session.session_id,
            prompt="Quick response needed",
            timeout_seconds=0,
        )

        # 手動觸發超時處理
        request.created_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        await manager._handle_timeout(session)

        assert session.status == HITLSessionStatus.TIMEOUT
        mock_callback.on_session_timeout.assert_called_once()

    @pytest.mark.asyncio
    async def test_hitl_escalation_workflow(self, mock_callback):
        """測試 HITL 升級工作流."""
        manager = HITLManager(callback=mock_callback)

        session = await manager.create_session()
        await manager.request_input(
            session_id=session.session_id,
            prompt="Complex issue",
        )

        await manager.escalate_session(
            session.session_id,
            reason="Requires supervisor",
            escalation_target="supervisor@company.com",
        )

        assert session.status == HITLSessionStatus.ESCALATED
        mock_callback.on_session_escalated.assert_called_once()
