"""
GroupChat Orchestrator Tests - Sprint 16 (S16-6)

測試 groupchat_orchestrator.py 模組的所有組件。

測試覆蓋:
    - ManagerSelectionRequest
    - ManagerSelectionResponse
    - GroupChatDirective
    - OrchestratorState
    - OrchestratorPhase
    - GroupChatOrchestrator
    - 工廠函數

Author: IPA Platform Team
Sprint: 16 - GroupChatBuilder 重構
Created: 2025-12-05
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any, List, Optional

# Import modules under test
from src.integrations.agent_framework.builders.groupchat_orchestrator import (
    # Data classes
    ManagerSelectionRequest,
    ManagerSelectionResponse,
    GroupChatDirective,
    OrchestratorState,
    # Enums
    OrchestratorPhase,
    # Main class
    GroupChatOrchestrator,
    # Factory functions
    create_orchestrator,
    create_manager_selection_request,
    create_manager_selection_response,
)

from src.integrations.agent_framework.builders.groupchat import (
    GroupChatMessage,
    MessageRole,
)


# =============================================================================
# ManagerSelectionRequest Tests
# =============================================================================


class TestManagerSelectionRequest:
    """測試 ManagerSelectionRequest 數據類。"""

    def test_creation(self):
        """測試創建。"""
        task = GroupChatMessage(
            role=MessageRole.USER,
            content="Task",
        )
        request = ManagerSelectionRequest(
            task=task,
            participants={"agent1": "Agent 1", "agent2": "Agent 2"},
            conversation=[task],
            round_index=0,
        )
        assert request.round_index == 0
        assert len(request.participants) == 2

    def test_to_dict(self):
        """測試轉換為字典。"""
        task = GroupChatMessage(
            role=MessageRole.USER,
            content="Task",
        )
        request = ManagerSelectionRequest(
            task=task,
            participants={"agent1": "Agent 1"},
            conversation=[task],
            round_index=3,
        )
        data = request.to_dict()
        assert data["round_index"] == 3
        assert "agent1" in data["participants"]

    def test_from_dict(self):
        """測試從字典創建。"""
        data = {
            "task": {
                "role": "user",
                "content": "Task",
            },
            "participants": {"agent1": "Agent 1"},
            "conversation": [],
            "round_index": 5,
        }
        request = ManagerSelectionRequest.from_dict(data)
        assert request.round_index == 5


# =============================================================================
# ManagerSelectionResponse Tests
# =============================================================================


class TestManagerSelectionResponse:
    """測試 ManagerSelectionResponse 數據類。"""

    def test_selection(self):
        """測試選擇響應。"""
        response = ManagerSelectionResponse(
            selected_participant="agent1",
            instruction="Please respond",
        )
        assert response.selected_participant == "agent1"
        assert response.finish is False

    def test_finish(self):
        """測試結束響應。"""
        response = ManagerSelectionResponse(
            finish=True,
            final_message="Conversation ended",
        )
        assert response.selected_participant is None
        assert response.finish is True
        assert response.final_message == "Conversation ended"

    def test_to_dict(self):
        """測試轉換為字典。"""
        response = ManagerSelectionResponse(
            selected_participant="agent1",
        )
        data = response.to_dict()
        assert data["selected_participant"] == "agent1"

    def test_from_dict(self):
        """測試從字典創建。"""
        data = {
            "selected_participant": "agent2",
            "finish": False,
        }
        response = ManagerSelectionResponse.from_dict(data)
        assert response.selected_participant == "agent2"

    def test_get_final_message_as_chat_message(self):
        """測試獲取最終消息為 ChatMessage。"""
        response = ManagerSelectionResponse(
            finish=True,
            final_message="Done",
        )
        msg = response.get_final_message_as_chat_message("manager")
        assert msg is not None
        assert msg.content == "Done"
        assert msg.author_name == "manager"

    def test_get_final_message_none(self):
        """測試無最終消息時返回 None。"""
        response = ManagerSelectionResponse(
            selected_participant="agent1",
        )
        msg = response.get_final_message_as_chat_message()
        assert msg is None


# =============================================================================
# GroupChatDirective Tests
# =============================================================================


class TestGroupChatDirective:
    """測試 GroupChatDirective 數據類。"""

    def test_selection_directive(self):
        """測試選擇指令。"""
        directive = GroupChatDirective(
            agent_name="agent1",
            instruction="Please research",
        )
        assert directive.agent_name == "agent1"
        assert directive.finish is False

    def test_finish_directive(self):
        """測試結束指令。"""
        final_msg = GroupChatMessage(
            role=MessageRole.ASSISTANT,
            content="Done",
        )
        directive = GroupChatDirective(
            finish=True,
            final_message=final_msg,
        )
        assert directive.finish is True
        assert directive.final_message.content == "Done"

    def test_to_dict(self):
        """測試轉換為字典。"""
        directive = GroupChatDirective(
            agent_name="agent1",
            metadata={"key": "value"},
        )
        data = directive.to_dict()
        assert data["agent_name"] == "agent1"
        assert data["metadata"]["key"] == "value"

    def test_from_selection_response(self):
        """測試從 ManagerSelectionResponse 創建。"""
        response = ManagerSelectionResponse(
            selected_participant="agent1",
            instruction="Do this",
        )
        directive = GroupChatDirective.from_selection_response(response)
        assert directive.agent_name == "agent1"
        assert directive.instruction == "Do this"

    def test_from_selection_response_finish(self):
        """測試從結束響應創建。"""
        response = ManagerSelectionResponse(
            finish=True,
            final_message="Completed",
        )
        directive = GroupChatDirective.from_selection_response(response, "manager")
        assert directive.finish is True
        assert directive.final_message.content == "Completed"


# =============================================================================
# OrchestratorState Tests
# =============================================================================


class TestOrchestratorPhase:
    """測試 OrchestratorPhase 枚舉。"""

    def test_enum_values(self):
        """測試枚舉值。"""
        assert OrchestratorPhase.IDLE == "idle"
        assert OrchestratorPhase.INITIALIZING == "initializing"
        assert OrchestratorPhase.SELECTING == "selecting"
        assert OrchestratorPhase.ROUTING == "routing"
        assert OrchestratorPhase.WAITING_RESPONSE == "waiting_response"
        assert OrchestratorPhase.PROCESSING_RESPONSE == "processing_response"
        assert OrchestratorPhase.COMPLETING == "completing"
        assert OrchestratorPhase.COMPLETED == "completed"
        assert OrchestratorPhase.ERROR == "error"


class TestOrchestratorState:
    """測試 OrchestratorState 數據類。"""

    def test_default_creation(self):
        """測試默認創建。"""
        state = OrchestratorState()
        assert state.phase == OrchestratorPhase.IDLE
        assert state.round_index == 0
        assert state.conversation == []

    def test_full_creation(self):
        """測試完整創建。"""
        task = GroupChatMessage(
            role=MessageRole.USER,
            content="Task",
        )
        state = OrchestratorState(
            phase=OrchestratorPhase.RUNNING if hasattr(OrchestratorPhase, 'RUNNING') else OrchestratorPhase.SELECTING,
            conversation=[task],
            round_index=5,
            pending_agent="agent1",
            task_message=task,
            participants={"agent1": "Agent 1"},
        )
        assert state.round_index == 5
        assert state.pending_agent == "agent1"

    def test_to_dict(self):
        """測試轉換為字典。"""
        state = OrchestratorState(
            phase=OrchestratorPhase.SELECTING,
            round_index=3,
        )
        data = state.to_dict()
        assert data["phase"] == "selecting"
        assert data["round_index"] == 3

    def test_from_dict(self):
        """測試從字典創建。"""
        data = {
            "phase": "completed",
            "round_index": 10,
            "pending_agent": None,
            "conversation": [],
        }
        state = OrchestratorState.from_dict(data)
        assert state.phase == OrchestratorPhase.COMPLETED
        assert state.round_index == 10


# =============================================================================
# GroupChatOrchestrator Tests
# =============================================================================


class TestGroupChatOrchestrator:
    """測試 GroupChatOrchestrator 類。"""

    @pytest.fixture
    def sample_participants(self):
        """創建示例參與者。"""
        return {
            "researcher": "Research agent",
            "writer": "Writing agent",
        }

    @pytest.fixture
    def round_robin_manager(self):
        """創建輪流選擇管理者。"""
        def manager(state):
            participants = list(state.get("participants", {}).keys())
            if not participants:
                return None
            idx = state.get("round_index", 0)
            return participants[idx % len(participants)]
        return manager

    def test_creation(self, sample_participants, round_robin_manager):
        """測試創建。"""
        orchestrator = GroupChatOrchestrator(
            manager=round_robin_manager,
            participants=sample_participants,
        )
        assert orchestrator.id is not None
        assert len(orchestrator.participants) == 2

    def test_creation_with_options(self, sample_participants, round_robin_manager):
        """測試帶選項創建。"""
        orchestrator = GroupChatOrchestrator(
            manager=round_robin_manager,
            participants=sample_participants,
            manager_name="coordinator",
            max_rounds=5,
            executor_id="custom-id",
        )
        assert orchestrator.id == "custom-id"
        assert orchestrator._max_rounds == 5

    def test_register_participant_callback(self, sample_participants, round_robin_manager):
        """測試註冊參與者回調。"""
        orchestrator = GroupChatOrchestrator(
            manager=round_robin_manager,
            participants=sample_participants,
        )

        async def callback(task, conversation):
            return GroupChatMessage(
                role=MessageRole.ASSISTANT,
                content="Response",
                author_name="researcher",
            )

        orchestrator.register_participant_callback("researcher", callback)
        assert "researcher" in orchestrator._participant_callbacks

    def test_register_unknown_participant_raises_error(self, sample_participants, round_robin_manager):
        """測試註冊未知參與者拋出錯誤。"""
        orchestrator = GroupChatOrchestrator(
            manager=round_robin_manager,
            participants=sample_participants,
        )

        async def callback(task, conversation):
            pass

        with pytest.raises(ValueError, match="Unknown participant"):
            orchestrator.register_participant_callback("unknown", callback)

    @pytest.mark.asyncio
    async def test_run_basic(self, sample_participants, round_robin_manager):
        """測試基本執行。"""
        orchestrator = GroupChatOrchestrator(
            manager=round_robin_manager,
            participants=sample_participants,
            max_rounds=2,
        )

        result = await orchestrator.run("Test task")

        assert "conversation" in result
        assert "round_index" in result
        assert result["phase"] == "completed"

    @pytest.mark.asyncio
    async def test_run_with_message_input(self, sample_participants, round_robin_manager):
        """測試使用消息輸入執行。"""
        orchestrator = GroupChatOrchestrator(
            manager=round_robin_manager,
            participants=sample_participants,
            max_rounds=2,
        )

        task_message = GroupChatMessage(
            role=MessageRole.USER,
            content="Task message",
        )
        result = await orchestrator.run(task_message)

        assert len(result["conversation"]) > 0

    @pytest.mark.asyncio
    async def test_run_with_termination_condition(self, sample_participants, round_robin_manager):
        """測試帶終止條件執行。"""
        def termination_condition(conversation):
            return len(conversation) >= 3

        orchestrator = GroupChatOrchestrator(
            manager=round_robin_manager,
            participants=sample_participants,
            termination_condition=termination_condition,
        )

        result = await orchestrator.run("Test")

        # 應該在 3 條消息後終止
        assert result["phase"] == "completed"

    @pytest.mark.asyncio
    async def test_run_with_custom_callback(self, sample_participants, round_robin_manager):
        """測試帶自定義回調執行。"""
        orchestrator = GroupChatOrchestrator(
            manager=round_robin_manager,
            participants=sample_participants,
            max_rounds=1,
        )

        callback_called = False

        async def custom_callback(task, conversation):
            nonlocal callback_called
            callback_called = True
            return GroupChatMessage(
                role=MessageRole.ASSISTANT,
                content="Custom response",
                author_name="researcher",
            )

        orchestrator.register_participant_callback("researcher", custom_callback)

        await orchestrator.run("Test")

        assert callback_called

    @pytest.mark.asyncio
    async def test_run_stream(self, sample_participants, round_robin_manager):
        """測試串流執行。"""
        orchestrator = GroupChatOrchestrator(
            manager=round_robin_manager,
            participants=sample_participants,
            max_rounds=2,
        )

        events = []
        async for event in orchestrator.run_stream("Test"):
            events.append(event)

        # 應該有 started, message(s), completed 事件
        assert any(e["type"] == "started" for e in events)
        assert any(e["type"] == "completed" for e in events)

    @pytest.mark.asyncio
    async def test_checkpoint_save_restore(self, sample_participants, round_robin_manager):
        """測試 checkpoint 保存和恢復。"""
        orchestrator = GroupChatOrchestrator(
            manager=round_robin_manager,
            participants=sample_participants,
            max_rounds=5,
        )

        # 執行一些操作
        await orchestrator.run("Test")

        # 保存 checkpoint
        checkpoint = await orchestrator.save_checkpoint()

        # 創建新的 orchestrator 並恢復
        new_orchestrator = GroupChatOrchestrator(
            manager=round_robin_manager,
            participants=sample_participants,
        )
        await new_orchestrator.restore_checkpoint(checkpoint)

        # 驗證狀態被恢復
        assert new_orchestrator.state.phase == orchestrator.state.phase

    @pytest.mark.asyncio
    async def test_manager_returns_directive(self, sample_participants):
        """測試管理者返回 GroupChatDirective。"""
        def directive_manager(state):
            return GroupChatDirective(
                agent_name="researcher",
                instruction="Do research",
            )

        orchestrator = GroupChatOrchestrator(
            manager=directive_manager,
            participants=sample_participants,
            max_rounds=1,
        )

        result = await orchestrator.run("Test")
        assert result is not None

    @pytest.mark.asyncio
    async def test_manager_returns_finish(self, sample_participants):
        """測試管理者返回結束指令。"""
        def finish_manager(state):
            return GroupChatDirective(
                finish=True,
                final_message=GroupChatMessage(
                    role=MessageRole.ASSISTANT,
                    content="Finished immediately",
                ),
            )

        orchestrator = GroupChatOrchestrator(
            manager=finish_manager,
            participants=sample_participants,
        )

        result = await orchestrator.run("Test")
        assert result["phase"] == "completed"
        # 對話應該很短（只有初始消息和結束消息）
        assert len(result["conversation"]) <= 3


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestOrchestratorFactoryFunctions:
    """測試編排器工廠函數。"""

    def test_create_orchestrator_default(self):
        """測試 create_orchestrator 默認選項。"""
        participants = {"agent1": "Agent 1", "agent2": "Agent 2"}
        orchestrator = create_orchestrator(
            participants=participants,
        )
        assert orchestrator is not None
        assert len(orchestrator.participants) == 2

    def test_create_orchestrator_with_manager(self):
        """測試 create_orchestrator 帶自定義管理者。"""
        def custom_manager(state):
            return "agent1"

        participants = {"agent1": "Agent 1"}
        orchestrator = create_orchestrator(
            participants=participants,
            manager=custom_manager,
        )
        assert orchestrator._manager == custom_manager

    def test_create_orchestrator_round_robin(self):
        """測試 create_orchestrator 輪流模式。"""
        participants = {"a": "A", "b": "B"}
        orchestrator = create_orchestrator(
            participants=participants,
            selection_method="round_robin",
        )
        # 驗證默認管理者使用輪流選擇
        result = orchestrator._manager({"round_index": 0, "participants": participants})
        assert result in ["a", "b"]

    def test_create_orchestrator_random(self):
        """測試 create_orchestrator 隨機模式。"""
        participants = {"a": "A", "b": "B"}
        orchestrator = create_orchestrator(
            participants=participants,
            selection_method="random",
        )
        result = orchestrator._manager({})
        assert result in ["a", "b"]

    def test_create_manager_selection_request(self):
        """測試 create_manager_selection_request。"""
        task = GroupChatMessage(
            role=MessageRole.USER,
            content="Task",
        )
        request = create_manager_selection_request(
            task=task,
            participants={"a": "A"},
            conversation=[task],
            round_index=5,
        )
        assert request.round_index == 5

    def test_create_manager_selection_response(self):
        """測試 create_manager_selection_response。"""
        response = create_manager_selection_response(
            selected_participant="agent1",
            instruction="Do this",
        )
        assert response.selected_participant == "agent1"
        assert response.instruction == "Do this"

    def test_create_manager_selection_response_finish(self):
        """測試 create_manager_selection_response 結束。"""
        response = create_manager_selection_response(
            finish=True,
            final_message="Done",
        )
        assert response.finish is True
        assert response.final_message == "Done"


# =============================================================================
# Integration Tests
# =============================================================================


class TestOrchestratorIntegration:
    """編排器整合測試。"""

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self):
        """測試完整對話流程。"""
        participants = {
            "researcher": "Research agent",
            "writer": "Writing agent",
            "reviewer": "Review agent",
        }

        def round_robin(state):
            names = list(state.get("participants", {}).keys())
            idx = state.get("round_index", 0)
            if idx >= 3:  # 每個人說一次就結束
                return None
            return names[idx % len(names)]

        orchestrator = GroupChatOrchestrator(
            manager=round_robin,
            participants=participants,
        )

        # 註冊回調
        for name in participants:
            async def make_callback(n):
                async def callback(task, conversation):
                    return GroupChatMessage(
                        role=MessageRole.ASSISTANT,
                        content=f"Response from {n}",
                        author_name=n,
                    )
                return callback

            orchestrator.register_participant_callback(
                name,
                await make_callback(name),
            )

        result = await orchestrator.run("Write an article")

        assert result["phase"] == "completed"
        assert result["round_index"] <= 3

    @pytest.mark.asyncio
    async def test_async_manager(self):
        """測試異步管理者。"""
        participants = {"agent1": "Agent 1"}

        async def async_manager(state):
            await asyncio.sleep(0.01)  # 模擬異步操作
            if state.get("round_index", 0) >= 1:
                return None
            return "agent1"

        orchestrator = GroupChatOrchestrator(
            manager=async_manager,
            participants=participants,
        )

        result = await orchestrator.run("Test")
        assert result is not None
