# =============================================================================
# Unit Tests for HandoffBuilderAdapter
# =============================================================================
# Sprint 15: HandoffBuilder 重構 - S15-5 測試
# Phase 3 Feature: P3-F2 (Agent Handoff 重構)
#
# 測試內容:
#   - HandoffMode 枚舉
#   - HandoffStatus 枚舉
#   - HandoffRoute 數據類
#   - HandoffParticipant 數據類
#   - UserInputRequest 數據類
#   - HandoffExecutionResult 數據類
#   - HandoffBuilderAdapter 類
#   - 工廠函數
# =============================================================================

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.integrations.agent_framework.builders.handoff import (
    HandoffBuilderAdapter,
    HandoffExecutionResult,
    HandoffMode,
    HandoffParticipant,
    HandoffRoute,
    HandoffStatus,
    UserInputRequest,
    create_autonomous_handoff,
    create_handoff_adapter,
    create_human_in_loop_handoff,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_executor():
    """創建模擬執行器."""
    return {"type": "mock_executor", "model": "gpt-4"}


@pytest.fixture
def sample_participants(mock_executor):
    """創建示例參與者."""
    return {
        "coordinator": mock_executor,
        "refund_agent": mock_executor,
        "shipping_agent": mock_executor,
    }


@pytest.fixture
def basic_adapter(sample_participants):
    """創建基本適配器."""
    return HandoffBuilderAdapter(
        id="test-workflow",
        participants=sample_participants,
        coordinator_id="coordinator",
        mode=HandoffMode.HUMAN_IN_LOOP,
    )


# =============================================================================
# Test HandoffMode Enum
# =============================================================================


class TestHandoffMode:
    """HandoffMode 枚舉測試."""

    def test_human_in_loop_value(self):
        """測試 HUMAN_IN_LOOP 值."""
        assert HandoffMode.HUMAN_IN_LOOP.value == "human_in_loop"

    def test_autonomous_value(self):
        """測試 AUTONOMOUS 值."""
        assert HandoffMode.AUTONOMOUS.value == "autonomous"

    def test_enum_membership(self):
        """測試枚舉成員."""
        assert HandoffMode.HUMAN_IN_LOOP in HandoffMode
        assert HandoffMode.AUTONOMOUS in HandoffMode
        assert len(HandoffMode) == 2

    def test_string_conversion(self):
        """測試字符串轉換."""
        assert str(HandoffMode.HUMAN_IN_LOOP) == "HandoffMode.HUMAN_IN_LOOP"
        assert HandoffMode("human_in_loop") == HandoffMode.HUMAN_IN_LOOP


# =============================================================================
# Test HandoffStatus Enum
# =============================================================================


class TestHandoffStatus:
    """HandoffStatus 枚舉測試."""

    def test_all_status_values(self):
        """測試所有狀態值."""
        expected = {
            "pending", "running", "waiting_input",
            "completed", "failed", "cancelled"
        }
        actual = {s.value for s in HandoffStatus}
        assert actual == expected

    def test_status_count(self):
        """測試狀態數量."""
        assert len(HandoffStatus) == 6

    def test_pending_status(self):
        """測試 PENDING 狀態."""
        assert HandoffStatus.PENDING.value == "pending"

    def test_completed_status(self):
        """測試 COMPLETED 狀態."""
        assert HandoffStatus.COMPLETED.value == "completed"


# =============================================================================
# Test HandoffRoute Data Class
# =============================================================================


class TestHandoffRoute:
    """HandoffRoute 數據類測試."""

    def test_basic_creation(self):
        """測試基本創建."""
        route = HandoffRoute(
            source_id="coordinator",
            target_ids=["agent1", "agent2"],
        )
        assert route.source_id == "coordinator"
        assert route.target_ids == ["agent1", "agent2"]
        assert route.description is None
        assert route.priority == 0
        assert route.metadata == {}

    def test_full_creation(self):
        """測試完整創建."""
        route = HandoffRoute(
            source_id="coordinator",
            target_ids=["agent1"],
            description="Route to specialist",
            priority=10,
            metadata={"category": "support"},
        )
        assert route.description == "Route to specialist"
        assert route.priority == 10
        assert route.metadata["category"] == "support"

    def test_target_ids_modification(self):
        """測試目標列表修改."""
        route = HandoffRoute(source_id="a", target_ids=["b"])
        route.target_ids.append("c")
        assert len(route.target_ids) == 2


# =============================================================================
# Test HandoffParticipant Data Class
# =============================================================================


class TestHandoffParticipant:
    """HandoffParticipant 數據類測試."""

    def test_basic_creation(self):
        """測試基本創建."""
        participant = HandoffParticipant(
            id="agent-1",
            name="Support Agent",
        )
        assert participant.id == "agent-1"
        assert participant.name == "Support Agent"
        assert participant.description is None
        assert participant.is_coordinator is False
        assert participant.executor is None
        assert participant.capabilities == []

    def test_coordinator_flag(self):
        """測試協調者標誌."""
        participant = HandoffParticipant(
            id="coord",
            name="Coordinator",
            is_coordinator=True,
        )
        assert participant.is_coordinator is True

    def test_capabilities_list(self):
        """測試能力列表."""
        participant = HandoffParticipant(
            id="agent",
            name="Agent",
            capabilities=["refund", "shipping", "general"],
        )
        assert len(participant.capabilities) == 3
        assert "refund" in participant.capabilities


# =============================================================================
# Test UserInputRequest Data Class
# =============================================================================


class TestUserInputRequest:
    """UserInputRequest 數據類測試."""

    def test_default_creation(self):
        """測試默認創建."""
        request = UserInputRequest()
        assert request.request_id is not None
        assert isinstance(request.request_id, UUID)
        assert request.conversation == []
        assert request.awaiting_agent_id == ""
        assert request.prompt == "Please provide your input."
        assert request.created_at is not None

    def test_custom_values(self):
        """測試自定義值."""
        request = UserInputRequest(
            conversation=[{"role": "user", "content": "Hello"}],
            awaiting_agent_id="agent-1",
            prompt="Please confirm",
        )
        assert len(request.conversation) == 1
        assert request.awaiting_agent_id == "agent-1"
        assert request.prompt == "Please confirm"


# =============================================================================
# Test HandoffExecutionResult Data Class
# =============================================================================


class TestHandoffExecutionResult:
    """HandoffExecutionResult 數據類測試."""

    def test_basic_creation(self):
        """測試基本創建."""
        execution_id = uuid4()
        result = HandoffExecutionResult(
            execution_id=execution_id,
            status=HandoffStatus.COMPLETED,
            conversation=[{"role": "user", "content": "test"}],
        )
        assert result.execution_id == execution_id
        assert result.status == HandoffStatus.COMPLETED
        assert len(result.conversation) == 1
        assert result.handoff_count == 0
        assert result.error is None

    def test_failed_result(self):
        """測試失敗結果."""
        result = HandoffExecutionResult(
            execution_id=uuid4(),
            status=HandoffStatus.FAILED,
            conversation=[],
            error="Connection timeout",
        )
        assert result.status == HandoffStatus.FAILED
        assert result.error == "Connection timeout"

    def test_duration_calculation(self):
        """測試持續時間."""
        result = HandoffExecutionResult(
            execution_id=uuid4(),
            status=HandoffStatus.COMPLETED,
            conversation=[],
            duration_ms=1500,
        )
        assert result.duration_ms == 1500


# =============================================================================
# Test HandoffBuilderAdapter Initialization
# =============================================================================


class TestHandoffBuilderAdapterInit:
    """HandoffBuilderAdapter 初始化測試."""

    def test_minimal_init(self):
        """測試最小初始化."""
        adapter = HandoffBuilderAdapter(id="test")
        assert adapter.id == "test"
        assert adapter.mode == HandoffMode.HUMAN_IN_LOOP
        assert adapter.coordinator_id is None
        assert len(adapter.participants) == 0

    def test_full_init(self, sample_participants):
        """測試完整初始化."""
        adapter = HandoffBuilderAdapter(
            id="full-test",
            participants=sample_participants,
            coordinator_id="coordinator",
            mode=HandoffMode.AUTONOMOUS,
            autonomous_turn_limit=100,
            enable_return_to_previous=True,
            request_prompt="Custom prompt",
        )
        assert adapter.id == "full-test"
        assert adapter.mode == HandoffMode.AUTONOMOUS
        assert adapter.coordinator_id == "coordinator"
        assert len(adapter.participants) == 3
        assert adapter._autonomous_turn_limit == 100
        assert adapter._enable_return_to_previous is True
        assert adapter._request_prompt == "Custom prompt"

    def test_participants_registration(self, mock_executor):
        """測試參與者自動註冊."""
        adapter = HandoffBuilderAdapter(
            id="test",
            participants={"a": mock_executor, "b": mock_executor},
        )
        assert "a" in adapter.participants
        assert "b" in adapter.participants


# =============================================================================
# Test HandoffBuilderAdapter Participant Management
# =============================================================================


class TestHandoffBuilderAdapterParticipants:
    """HandoffBuilderAdapter 參與者管理測試."""

    def test_add_participant(self, mock_executor):
        """測試添加參與者."""
        adapter = HandoffBuilderAdapter(id="test")
        adapter.add_participant(
            "agent-1",
            mock_executor,
            name="Agent One",
            description="Test agent",
            capabilities=["support"],
        )

        assert "agent-1" in adapter.participants
        participant = adapter.participants["agent-1"]
        assert participant.name == "Agent One"
        assert participant.description == "Test agent"
        assert "support" in participant.capabilities

    def test_add_coordinator_participant(self, mock_executor):
        """測試添加協調者參與者."""
        adapter = HandoffBuilderAdapter(id="test")
        adapter.add_participant(
            "coord",
            mock_executor,
            is_coordinator=True,
        )

        assert adapter.coordinator_id == "coord"
        assert adapter.participants["coord"].is_coordinator is True

    def test_set_coordinator(self, sample_participants):
        """測試設置協調者."""
        adapter = HandoffBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        adapter.set_coordinator("refund_agent")

        assert adapter.coordinator_id == "refund_agent"
        assert adapter.participants["refund_agent"].is_coordinator is True

    def test_set_coordinator_invalid(self):
        """測試設置無效協調者."""
        adapter = HandoffBuilderAdapter(id="test")

        with pytest.raises(ValueError, match="not in participants"):
            adapter.set_coordinator("nonexistent")

    def test_chain_calls(self, mock_executor):
        """測試鏈式調用."""
        adapter = HandoffBuilderAdapter(id="test")
        result = (
            adapter
            .add_participant("a", mock_executor)
            .add_participant("b", mock_executor)
            .set_coordinator("a")
        )

        assert result is adapter
        assert len(adapter.participants) == 2


# =============================================================================
# Test HandoffBuilderAdapter Handoff Routes
# =============================================================================


class TestHandoffBuilderAdapterRoutes:
    """HandoffBuilderAdapter 路由管理測試."""

    def test_add_handoff_single_target(self, basic_adapter):
        """測試添加單一目標路由."""
        basic_adapter.add_handoff("coordinator", "refund_agent")

        routes = basic_adapter.handoff_routes
        assert "coordinator" in routes
        assert "refund_agent" in routes["coordinator"].target_ids

    def test_add_handoff_multiple_targets(self, basic_adapter):
        """測試添加多個目標路由."""
        basic_adapter.add_handoff(
            "coordinator",
            ["refund_agent", "shipping_agent"],
        )

        route = basic_adapter.handoff_routes["coordinator"]
        assert len(route.target_ids) == 2

    def test_add_handoff_merge_targets(self, basic_adapter):
        """測試合併路由目標."""
        basic_adapter.add_handoff("coordinator", "refund_agent")
        basic_adapter.add_handoff("coordinator", "shipping_agent")

        route = basic_adapter.handoff_routes["coordinator"]
        assert len(route.target_ids) == 2

    def test_add_handoff_invalid_source(self, basic_adapter):
        """測試無效來源."""
        with pytest.raises(ValueError, match="Source .* is not in participants"):
            basic_adapter.add_handoff("nonexistent", "refund_agent")

    def test_add_handoff_invalid_target(self, basic_adapter):
        """測試無效目標."""
        with pytest.raises(ValueError, match="Target .* is not in participants"):
            basic_adapter.add_handoff("coordinator", "nonexistent")

    def test_add_handoff_with_metadata(self, basic_adapter):
        """測試帶元數據的路由."""
        basic_adapter.add_handoff(
            "coordinator",
            "refund_agent",
            description="Refund routing",
            priority=5,
            metadata={"category": "financial"},
        )

        route = basic_adapter.handoff_routes["coordinator"]
        assert route.description == "Refund routing"
        assert route.priority == 5
        assert route.metadata["category"] == "financial"


# =============================================================================
# Test HandoffBuilderAdapter Configuration
# =============================================================================


class TestHandoffBuilderAdapterConfig:
    """HandoffBuilderAdapter 配置測試."""

    def test_with_mode(self, basic_adapter):
        """測試設置模式."""
        result = basic_adapter.with_mode(
            HandoffMode.AUTONOMOUS,
            autonomous_turn_limit=100,
        )

        assert result is basic_adapter
        assert basic_adapter.mode == HandoffMode.AUTONOMOUS
        assert basic_adapter._autonomous_turn_limit == 100

    def test_with_termination_condition(self, basic_adapter):
        """測試設置終止條件."""
        def condition(conv: List[Dict]) -> bool:
            return len(conv) > 10

        basic_adapter.with_termination_condition(condition)
        assert basic_adapter._termination_condition is condition

    def test_enable_return_to_previous(self, basic_adapter):
        """測試啟用返回上一個."""
        basic_adapter.enable_return_to_previous(True)
        assert basic_adapter._enable_return_to_previous is True

        basic_adapter.enable_return_to_previous(False)
        assert basic_adapter._enable_return_to_previous is False

    def test_with_request_prompt(self, basic_adapter):
        """測試設置請求提示."""
        basic_adapter.with_request_prompt("Custom prompt message")
        assert basic_adapter._request_prompt == "Custom prompt message"


# =============================================================================
# Test HandoffBuilderAdapter Event Handlers
# =============================================================================


class TestHandoffBuilderAdapterEvents:
    """HandoffBuilderAdapter 事件處理測試."""

    def test_on_handoff_handler(self, basic_adapter):
        """測試 handoff 事件處理器."""
        handler = MagicMock()
        result = basic_adapter.on_handoff(handler)

        assert result is basic_adapter
        assert handler in basic_adapter._on_handoff

    def test_on_user_input_request_handler(self, basic_adapter):
        """測試用戶輸入請求事件處理器."""
        handler = MagicMock()
        basic_adapter.on_user_input_request(handler)

        assert handler in basic_adapter._on_user_input_request

    def test_on_completion_handler(self, basic_adapter):
        """測試完成事件處理器."""
        handler = MagicMock()
        basic_adapter.on_completion(handler)

        assert handler in basic_adapter._on_completion


# =============================================================================
# Test HandoffBuilderAdapter Build
# =============================================================================


class TestHandoffBuilderAdapterBuild:
    """HandoffBuilderAdapter 構建測試."""

    def test_build_success(self, basic_adapter):
        """測試成功構建."""
        workflow = basic_adapter.build()

        assert workflow is not None
        assert workflow["id"] == "test-workflow"
        assert workflow["coordinator_id"] == "coordinator"
        assert workflow["built"] is True

    def test_build_no_participants(self):
        """測試無參與者構建失敗."""
        adapter = HandoffBuilderAdapter(id="test")

        with pytest.raises(ValueError, match="No participants"):
            adapter.build()

    def test_build_no_coordinator(self, mock_executor):
        """測試無協調者構建失敗."""
        adapter = HandoffBuilderAdapter(
            id="test",
            participants={"a": mock_executor},
        )

        with pytest.raises(ValueError, match="No coordinator"):
            adapter.build()


# =============================================================================
# Test HandoffBuilderAdapter Run
# =============================================================================


class TestHandoffBuilderAdapterRun:
    """HandoffBuilderAdapter 執行測試."""

    @pytest.mark.asyncio
    async def test_run_string_input(self, basic_adapter):
        """測試字符串輸入執行."""
        result = await basic_adapter.run("Hello, I need help")

        assert result is not None
        assert result.status == HandoffStatus.COMPLETED
        assert result.execution_id is not None
        assert len(result.conversation) > 0

    @pytest.mark.asyncio
    async def test_run_dict_input(self, basic_adapter):
        """測試字典輸入執行."""
        result = await basic_adapter.run({
            "role": "user",
            "content": "Test message",
        })

        assert result.status == HandoffStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_run_list_input(self, basic_adapter):
        """測試列表輸入執行."""
        result = await basic_adapter.run([
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "Response"},
        ])

        assert result.status == HandoffStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_run_auto_build(self, basic_adapter):
        """測試自動構建."""
        assert basic_adapter._built is False
        await basic_adapter.run("Test")
        assert basic_adapter._built is True

    @pytest.mark.asyncio
    async def test_run_autonomous_mode(self, sample_participants):
        """測試自主模式執行."""
        adapter = HandoffBuilderAdapter(
            id="autonomous-test",
            participants=sample_participants,
            coordinator_id="coordinator",
            mode=HandoffMode.AUTONOMOUS,
            autonomous_turn_limit=5,
        )

        result = await adapter.run("Test input")
        assert result.status == HandoffStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_run_with_termination_condition(self, sample_participants):
        """測試帶終止條件執行."""
        def terminate_immediately(conv: List[Dict]) -> bool:
            return True

        adapter = HandoffBuilderAdapter(
            id="term-test",
            participants=sample_participants,
            coordinator_id="coordinator",
            termination_condition=terminate_immediately,
        )

        result = await adapter.run("Test")
        assert result.status == HandoffStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_run_tracks_participating_agents(self, basic_adapter):
        """測試追蹤參與 Agent."""
        result = await basic_adapter.run("Test")

        assert "coordinator" in result.participating_agents

    @pytest.mark.asyncio
    async def test_run_calculates_duration(self, basic_adapter):
        """測試計算持續時間."""
        result = await basic_adapter.run("Test")

        assert result.duration_ms is not None
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_run_completion_handler_called(self, basic_adapter):
        """測試完成處理器被調用."""
        handler = AsyncMock()
        basic_adapter.on_completion(handler)

        await basic_adapter.run("Test")

        handler.assert_called_once()


# =============================================================================
# Test Factory Functions
# =============================================================================


class TestFactoryFunctions:
    """工廠函數測試."""

    def test_create_handoff_adapter(self, sample_participants):
        """測試 create_handoff_adapter."""
        adapter = create_handoff_adapter(
            id="factory-test",
            participants=sample_participants,
            coordinator_id="coordinator",
        )

        assert adapter.id == "factory-test"
        assert adapter.coordinator_id == "coordinator"
        # 應該自動創建從 coordinator 到其他參與者的路由
        assert "coordinator" in adapter.handoff_routes

    def test_create_autonomous_handoff(self, sample_participants):
        """測試 create_autonomous_handoff."""
        adapter = create_autonomous_handoff(
            id="auto-test",
            participants=sample_participants,
            coordinator_id="coordinator",
            turn_limit=100,
        )

        assert adapter.mode == HandoffMode.AUTONOMOUS
        assert adapter._autonomous_turn_limit == 100

    def test_create_human_in_loop_handoff(self, sample_participants):
        """測試 create_human_in_loop_handoff."""
        adapter = create_human_in_loop_handoff(
            id="hitl-test",
            participants=sample_participants,
            coordinator_id="coordinator",
            request_prompt="Custom prompt",
        )

        assert adapter.mode == HandoffMode.HUMAN_IN_LOOP
        assert adapter._request_prompt == "Custom prompt"


# =============================================================================
# Test Private Methods
# =============================================================================


class TestPrivateMethods:
    """私有方法測試."""

    def test_normalize_input_string(self, basic_adapter):
        """測試字符串輸入規範化."""
        result = basic_adapter._normalize_input("Hello")

        assert result == [{"role": "user", "content": "Hello"}]

    def test_normalize_input_dict(self, basic_adapter):
        """測試字典輸入規範化."""
        input_dict = {"role": "user", "content": "Test"}
        result = basic_adapter._normalize_input(input_dict)

        assert result == [input_dict]

    def test_normalize_input_list(self, basic_adapter):
        """測試列表輸入規範化."""
        input_list = [
            {"role": "user", "content": "A"},
            {"role": "assistant", "content": "B"},
        ]
        result = basic_adapter._normalize_input(input_list)

        assert result == input_list

    @pytest.mark.asyncio
    async def test_simulate_agent_response(self, basic_adapter):
        """測試模擬 Agent 回應."""
        basic_adapter.build()

        response = await basic_adapter._simulate_agent_response(
            "coordinator",
            [{"role": "user", "content": "Test"}],
        )

        assert response is not None
        assert "content" in response

    @pytest.mark.asyncio
    async def test_handle_handoff(self, basic_adapter):
        """測試處理 handoff."""
        basic_adapter._participating_agents = ["coordinator"]

        await basic_adapter._handle_handoff("coordinator", "refund_agent")

        assert basic_adapter._handoff_count == 1
        assert basic_adapter._current_agent_id == "refund_agent"
        assert "refund_agent" in basic_adapter._participating_agents


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """整合測試."""

    @pytest.mark.asyncio
    async def test_full_workflow(self, sample_participants):
        """測試完整工作流."""
        adapter = HandoffBuilderAdapter(
            id="integration-test",
            participants=sample_participants,
            coordinator_id="coordinator",
            mode=HandoffMode.AUTONOMOUS,
            autonomous_turn_limit=3,
        )

        # 添加路由
        adapter.add_handoff("coordinator", ["refund_agent", "shipping_agent"])

        # 添加事件處理器
        handoffs_recorded = []
        adapter.on_handoff(lambda s, t: handoffs_recorded.append((s, t)))

        # 執行
        result = await adapter.run("I need help with refund_agent")

        # 驗證
        assert result.status == HandoffStatus.COMPLETED
        assert result.final_agent_id is not None

    @pytest.mark.asyncio
    async def test_error_handling(self, sample_participants):
        """測試錯誤處理."""
        adapter = HandoffBuilderAdapter(
            id="error-test",
            participants=sample_participants,
            coordinator_id="coordinator",
        )

        # 模擬錯誤
        async def failing_handler(result):
            raise Exception("Test error")

        adapter.on_completion(failing_handler)

        # 執行應該完成 (錯誤被捕獲)
        result = await adapter.run("Test")
        assert result.status == HandoffStatus.COMPLETED
