"""
GroupChatBuilderAdapter Unit Tests - Sprint 16 (S16-6)

測試 groupchat.py 模組的所有組件。

測試覆蓋:
    - SpeakerSelectionMethod 枚舉
    - GroupChatStatus 枚舉
    - MessageRole 枚舉
    - GroupChatParticipant 數據類
    - GroupChatMessage 數據類
    - GroupChatTurn 數據類
    - GroupChatState 數據類
    - SpeakerSelectionResult 數據類
    - GroupChatResult 數據類
    - Built-in selectors
    - GroupChatBuilderAdapter 類
    - Factory functions

Author: IPA Platform Team
Sprint: 16 - GroupChatBuilder 重構
Created: 2025-12-05
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List, Optional

# Import modules under test
from src.integrations.agent_framework.builders.groupchat import (
    # Enums
    SpeakerSelectionMethod,
    GroupChatStatus,
    MessageRole,
    # Data classes
    GroupChatParticipant,
    GroupChatMessage,
    GroupChatTurn,
    GroupChatState,
    SpeakerSelectionResult,
    GroupChatResult,
    # Selectors
    create_round_robin_selector,
    create_random_selector,
    create_last_speaker_different_selector,
    # Main class
    GroupChatBuilderAdapter,
    # Factory functions
    create_groupchat_adapter,
    create_round_robin_chat,
    create_auto_managed_chat,
    create_custom_selector_chat,
)


# =============================================================================
# Enum Tests
# =============================================================================


class TestSpeakerSelectionMethod:
    """測試 SpeakerSelectionMethod 枚舉。"""

    def test_enum_values(self):
        """測試枚舉值。"""
        assert SpeakerSelectionMethod.AUTO == "auto"
        assert SpeakerSelectionMethod.ROUND_ROBIN == "round_robin"
        assert SpeakerSelectionMethod.RANDOM == "random"
        assert SpeakerSelectionMethod.MANUAL == "manual"
        assert SpeakerSelectionMethod.CUSTOM == "custom"

    def test_enum_from_string(self):
        """測試從字符串創建枚舉。"""
        method = SpeakerSelectionMethod("round_robin")
        assert method == SpeakerSelectionMethod.ROUND_ROBIN

    def test_enum_str_representation(self):
        """測試字符串表示。"""
        assert str(SpeakerSelectionMethod.AUTO.value) == "auto"


class TestGroupChatStatus:
    """測試 GroupChatStatus 枚舉。"""

    def test_enum_values(self):
        """測試枚舉值。"""
        assert GroupChatStatus.IDLE == "idle"
        assert GroupChatStatus.RUNNING == "running"
        assert GroupChatStatus.WAITING == "waiting"
        assert GroupChatStatus.PAUSED == "paused"
        assert GroupChatStatus.COMPLETED == "completed"
        assert GroupChatStatus.FAILED == "failed"
        assert GroupChatStatus.CANCELLED == "cancelled"


class TestMessageRole:
    """測試 MessageRole 枚舉。"""

    def test_enum_values(self):
        """測試枚舉值。"""
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.SYSTEM == "system"
        assert MessageRole.MANAGER == "manager"


# =============================================================================
# Data Class Tests
# =============================================================================


class TestGroupChatParticipant:
    """測試 GroupChatParticipant 數據類。"""

    def test_basic_creation(self):
        """測試基本創建。"""
        participant = GroupChatParticipant(
            name="researcher",
            description="Research agent",
        )
        assert participant.name == "researcher"
        assert participant.description == "Research agent"
        assert participant.agent is None
        assert participant.capabilities == []
        assert participant.metadata == {}

    def test_full_creation(self):
        """測試完整創建。"""
        mock_agent = MagicMock()
        participant = GroupChatParticipant(
            name="writer",
            description="Writing agent",
            agent=mock_agent,
            capabilities=["writing", "editing"],
            metadata={"priority": 1},
        )
        assert participant.name == "writer"
        assert participant.agent == mock_agent
        assert "writing" in participant.capabilities
        assert participant.metadata["priority"] == 1

    def test_empty_name_raises_error(self):
        """測試空名稱拋出錯誤。"""
        with pytest.raises(ValueError, match="name cannot be empty"):
            GroupChatParticipant(name="")

    def test_to_dict(self):
        """測試轉換為字典。"""
        participant = GroupChatParticipant(
            name="test",
            description="Test agent",
            capabilities=["cap1"],
        )
        data = participant.to_dict()
        assert data["name"] == "test"
        assert data["description"] == "Test agent"
        assert data["capabilities"] == ["cap1"]


class TestGroupChatMessage:
    """測試 GroupChatMessage 數據類。"""

    def test_basic_creation(self):
        """測試基本創建。"""
        msg = GroupChatMessage(
            role=MessageRole.USER,
            content="Hello",
        )
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
        assert msg.author_name is None
        assert msg.timestamp is not None

    def test_full_creation(self):
        """測試完整創建。"""
        msg = GroupChatMessage(
            role=MessageRole.ASSISTANT,
            content="Response",
            author_name="agent1",
            timestamp=1234567890.0,
            metadata={"key": "value"},
        )
        assert msg.author_name == "agent1"
        assert msg.timestamp == 1234567890.0
        assert msg.metadata["key"] == "value"

    def test_to_dict(self):
        """測試轉換為字典。"""
        msg = GroupChatMessage(
            role=MessageRole.USER,
            content="Test",
            author_name="user",
        )
        data = msg.to_dict()
        assert data["role"] == "user"
        assert data["content"] == "Test"
        assert data["author_name"] == "user"

    def test_from_dict(self):
        """測試從字典創建。"""
        data = {
            "role": "assistant",
            "content": "Response",
            "author_name": "agent",
            "timestamp": 1234567890.0,
        }
        msg = GroupChatMessage.from_dict(data)
        assert msg.role == MessageRole.ASSISTANT
        assert msg.content == "Response"
        assert msg.author_name == "agent"


class TestGroupChatTurn:
    """測試 GroupChatTurn 數據類。"""

    def test_creation(self):
        """測試創建。"""
        msg = GroupChatMessage(
            role=MessageRole.ASSISTANT,
            content="Turn message",
        )
        turn = GroupChatTurn(
            speaker="agent1",
            role="agent",
            message=msg,
            turn_index=1,
        )
        assert turn.speaker == "agent1"
        assert turn.role == "agent"
        assert turn.turn_index == 1

    def test_to_dict(self):
        """測試轉換為字典。"""
        msg = GroupChatMessage(
            role=MessageRole.USER,
            content="Test",
        )
        turn = GroupChatTurn(
            speaker="user",
            role="user",
            message=msg,
            turn_index=0,
        )
        data = turn.to_dict()
        assert data["speaker"] == "user"
        assert data["turn_index"] == 0


class TestGroupChatState:
    """測試 GroupChatState 數據類。"""

    def test_creation(self):
        """測試創建。"""
        task = GroupChatMessage(
            role=MessageRole.USER,
            content="Task",
        )
        state = GroupChatState(
            task=task,
            participants={"agent1": "Agent 1", "agent2": "Agent 2"},
        )
        assert state.task == task
        assert len(state.participants) == 2
        assert state.round_index == 0

    def test_to_dict(self):
        """測試轉換為字典。"""
        task = GroupChatMessage(
            role=MessageRole.USER,
            content="Task",
        )
        state = GroupChatState(
            task=task,
            participants={"agent1": "Agent 1"},
            round_index=5,
        )
        data = state.to_dict()
        assert data["round_index"] == 5
        assert "agent1" in data["participants"]


class TestSpeakerSelectionResult:
    """測試 SpeakerSelectionResult 數據類。"""

    def test_selection(self):
        """測試選擇結果。"""
        result = SpeakerSelectionResult(
            selected_participant="agent1",
            instruction="Please respond",
        )
        assert result.selected_participant == "agent1"
        assert result.finish is False

    def test_finish(self):
        """測試結束結果。"""
        result = SpeakerSelectionResult(
            finish=True,
            final_message="Conversation ended",
        )
        assert result.selected_participant is None
        assert result.finish is True


class TestGroupChatResult:
    """測試 GroupChatResult 數據類。"""

    def test_creation(self):
        """測試創建。"""
        msg = GroupChatMessage(
            role=MessageRole.USER,
            content="Test",
        )
        result = GroupChatResult(
            status=GroupChatStatus.COMPLETED,
            conversation=[msg],
            total_rounds=3,
            participants_involved=["agent1", "agent2"],
            duration=10.5,
        )
        assert result.status == GroupChatStatus.COMPLETED
        assert len(result.conversation) == 1
        assert result.total_rounds == 3

    def test_to_dict(self):
        """測試轉換為字典。"""
        result = GroupChatResult(
            status=GroupChatStatus.COMPLETED,
            conversation=[],
            total_rounds=0,
        )
        data = result.to_dict()
        assert data["status"] == "completed"


# =============================================================================
# Built-in Selector Tests
# =============================================================================


class TestBuiltInSelectors:
    """測試內建選擇器。"""

    def test_round_robin_selector(self):
        """測試輪流選擇器。"""
        participants = ["agent1", "agent2", "agent3"]
        selector = create_round_robin_selector(participants)

        # 測試輪流選擇
        assert selector({"round_index": 0}) == "agent1"
        assert selector({"round_index": 1}) == "agent2"
        assert selector({"round_index": 2}) == "agent3"
        assert selector({"round_index": 3}) == "agent1"  # 循環

    def test_round_robin_empty_list(self):
        """測試空列表。"""
        selector = create_round_robin_selector([])
        assert selector({"round_index": 0}) is None

    def test_random_selector(self):
        """測試隨機選擇器。"""
        participants = ["agent1", "agent2", "agent3"]
        selector = create_random_selector(participants, seed=42)

        # 使用固定種子應該得到一致的結果
        result1 = selector({"round_index": 0})
        assert result1 in participants

    def test_random_selector_with_seed(self):
        """測試帶種子的隨機選擇器。"""
        participants = ["a", "b", "c"]
        selector1 = create_random_selector(participants, seed=123)
        selector2 = create_random_selector(participants, seed=123)

        # 相同種子應產生相同結果
        result1 = selector1({})
        result2 = selector2({})
        assert result1 == result2

    def test_last_speaker_different_selector(self):
        """測試避免連續發言的選擇器。"""
        participants = ["agent1", "agent2"]
        selector = create_last_speaker_different_selector(participants)

        # 如果上一位發言者是 agent1，下一位應該是 agent2
        state = {"history": [{"speaker": "agent1"}]}
        result = selector(state)
        assert result == "agent2"


# =============================================================================
# GroupChatBuilderAdapter Tests
# =============================================================================


class TestGroupChatBuilderAdapter:
    """測試 GroupChatBuilderAdapter 類。"""

    @pytest.fixture
    def sample_participants(self):
        """創建示例參與者。"""
        return [
            GroupChatParticipant(name="agent1", description="Agent 1"),
            GroupChatParticipant(name="agent2", description="Agent 2"),
        ]

    def test_creation(self, sample_participants):
        """測試創建適配器。"""
        adapter = GroupChatBuilderAdapter(
            id="test-chat",
            participants=sample_participants,
        )
        assert adapter.id == "test-chat"
        assert len(adapter.participants) == 2
        assert adapter.status == GroupChatStatus.IDLE

    def test_creation_with_config(self, sample_participants):
        """測試帶配置創建。"""
        adapter = GroupChatBuilderAdapter(
            id="test-chat",
            participants=sample_participants,
            selection_method=SpeakerSelectionMethod.RANDOM,
            max_rounds=10,
            config={"key": "value"},
        )
        assert adapter.selection_method == SpeakerSelectionMethod.RANDOM

    def test_empty_participants_raises_error(self):
        """測試空參與者列表拋出錯誤。"""
        with pytest.raises(ValueError, match="At least one participant"):
            GroupChatBuilderAdapter(id="test", participants=[])

    def test_empty_id_raises_error(self, sample_participants):
        """測試空 ID 拋出錯誤。"""
        with pytest.raises(ValueError, match="ID cannot be empty"):
            GroupChatBuilderAdapter(id="", participants=sample_participants)

    def test_auto_without_manager_raises_error(self, sample_participants):
        """測試 AUTO 模式無 manager 拋出錯誤。"""
        with pytest.raises(ValueError, match="Manager agent is required"):
            GroupChatBuilderAdapter(
                id="test",
                participants=sample_participants,
                selection_method=SpeakerSelectionMethod.AUTO,
            )

    def test_custom_without_selector_raises_error(self, sample_participants):
        """測試 CUSTOM 模式無 selector 拋出錯誤。"""
        with pytest.raises(ValueError, match="Custom selector is required"):
            GroupChatBuilderAdapter(
                id="test",
                participants=sample_participants,
                selection_method=SpeakerSelectionMethod.CUSTOM,
            )

    def test_add_participant(self, sample_participants):
        """測試添加參與者。"""
        adapter = GroupChatBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        new_participant = GroupChatParticipant(
            name="agent3",
            description="Agent 3",
        )
        adapter.add_participant(new_participant)
        assert len(adapter.participants) == 3

    def test_add_duplicate_participant_raises_error(self, sample_participants):
        """測試添加重複參與者拋出錯誤。"""
        adapter = GroupChatBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        duplicate = GroupChatParticipant(name="agent1", description="Duplicate")
        with pytest.raises(ValueError, match="already exists"):
            adapter.add_participant(duplicate)

    def test_remove_participant(self, sample_participants):
        """測試移除參與者。"""
        adapter = GroupChatBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        result = adapter.remove_participant("agent1")
        assert result is True
        assert len(adapter.participants) == 1

    def test_remove_nonexistent_participant(self, sample_participants):
        """測試移除不存在的參與者。"""
        adapter = GroupChatBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        result = adapter.remove_participant("nonexistent")
        assert result is False

    def test_set_selection_method(self, sample_participants):
        """測試設置選擇方法。"""
        adapter = GroupChatBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        adapter.set_selection_method(SpeakerSelectionMethod.RANDOM)
        assert adapter.selection_method == SpeakerSelectionMethod.RANDOM

    def test_set_max_rounds(self, sample_participants):
        """測試設置最大輪數。"""
        adapter = GroupChatBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        adapter.set_max_rounds(20)
        # Internal check
        assert adapter._max_rounds == 20

    @pytest.mark.asyncio
    async def test_initialize(self, sample_participants):
        """測試初始化。"""
        adapter = GroupChatBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        await adapter.initialize()
        assert adapter.is_initialized is True

    @pytest.mark.asyncio
    async def test_build(self, sample_participants):
        """測試構建。"""
        adapter = GroupChatBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        await adapter.initialize()
        workflow = adapter.build()
        assert workflow is not None
        assert adapter.is_built is True

    @pytest.mark.asyncio
    async def test_run(self, sample_participants):
        """測試執行。"""
        adapter = GroupChatBuilderAdapter(
            id="test",
            participants=sample_participants,
            max_rounds=3,
        )
        await adapter.initialize()
        result = await adapter.run("Test task")

        assert result.status == GroupChatStatus.COMPLETED
        assert len(result.conversation) > 0
        assert result.duration > 0

    @pytest.mark.asyncio
    async def test_run_with_message_input(self, sample_participants):
        """測試使用消息輸入執行。"""
        adapter = GroupChatBuilderAdapter(
            id="test",
            participants=sample_participants,
            max_rounds=2,
        )
        await adapter.initialize()

        task_message = GroupChatMessage(
            role=MessageRole.USER,
            content="Task message",
        )
        result = await adapter.run(task_message)

        assert result.status == GroupChatStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_cleanup(self, sample_participants):
        """測試清理。"""
        adapter = GroupChatBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        await adapter.initialize()
        adapter.build()
        await adapter.cleanup()

        assert adapter.is_initialized is False
        assert adapter.is_built is False

    def test_get_events(self, sample_participants):
        """測試獲取事件。"""
        adapter = GroupChatBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        events = adapter.get_events()
        assert isinstance(events, list)

    def test_clear_events(self, sample_participants):
        """測試清除事件。"""
        adapter = GroupChatBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        adapter._events.append({"type": "test"})
        adapter.clear_events()
        assert len(adapter.get_events()) == 0


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunctions:
    """測試工廠函數。"""

    @pytest.fixture
    def sample_participants(self):
        """創建示例參與者。"""
        return [
            GroupChatParticipant(name="agent1", description="Agent 1"),
            GroupChatParticipant(name="agent2", description="Agent 2"),
        ]

    def test_create_groupchat_adapter(self, sample_participants):
        """測試 create_groupchat_adapter。"""
        adapter = create_groupchat_adapter(
            id="test",
            participants=sample_participants,
        )
        assert adapter.id == "test"
        assert adapter.selection_method == SpeakerSelectionMethod.ROUND_ROBIN

    def test_create_round_robin_chat(self, sample_participants):
        """測試 create_round_robin_chat。"""
        adapter = create_round_robin_chat(
            id="test",
            participants=sample_participants,
            max_rounds=5,
        )
        assert adapter.selection_method == SpeakerSelectionMethod.ROUND_ROBIN
        assert adapter._max_rounds == 5

    def test_create_auto_managed_chat(self, sample_participants):
        """測試 create_auto_managed_chat。"""
        mock_manager = MagicMock()
        adapter = create_auto_managed_chat(
            id="test",
            participants=sample_participants,
            manager_agent=mock_manager,
        )
        assert adapter.selection_method == SpeakerSelectionMethod.AUTO
        assert adapter._manager_agent == mock_manager

    def test_create_custom_selector_chat(self, sample_participants):
        """測試 create_custom_selector_chat。"""
        def custom_selector(state):
            return "agent1"

        adapter = create_custom_selector_chat(
            id="test",
            participants=sample_participants,
            selector=custom_selector,
        )
        assert adapter.selection_method == SpeakerSelectionMethod.CUSTOM


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """整合測試。"""

    @pytest.fixture
    def sample_participants(self):
        """創建示例參與者。"""
        return [
            GroupChatParticipant(
                name="researcher",
                description="Research agent",
                capabilities=["research", "analysis"],
            ),
            GroupChatParticipant(
                name="writer",
                description="Writing agent",
                capabilities=["writing", "editing"],
            ),
            GroupChatParticipant(
                name="reviewer",
                description="Review agent",
                capabilities=["review", "feedback"],
            ),
        ]

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, sample_participants):
        """測試完整對話流程。"""
        adapter = GroupChatBuilderAdapter(
            id="full-test",
            participants=sample_participants,
            selection_method=SpeakerSelectionMethod.ROUND_ROBIN,
            max_rounds=3,
        )

        await adapter.initialize()
        assert adapter.is_initialized

        result = await adapter.run("Write an article about AI")

        assert result.status == GroupChatStatus.COMPLETED
        assert result.total_rounds >= 0
        assert len(result.participants_involved) > 0
        assert result.duration > 0

        await adapter.cleanup()
        assert not adapter.is_initialized

    @pytest.mark.asyncio
    async def test_context_manager(self, sample_participants):
        """測試上下文管理器。"""
        adapter = GroupChatBuilderAdapter(
            id="context-test",
            participants=sample_participants,
        )

        async with adapter:
            assert adapter.is_initialized
            result = await adapter.run("Test")
            assert result is not None

        assert not adapter.is_initialized

    @pytest.mark.asyncio
    async def test_state_tracking(self, sample_participants):
        """測試狀態追蹤。"""
        adapter = GroupChatBuilderAdapter(
            id="state-test",
            participants=sample_participants,
            max_rounds=2,
        )

        await adapter.initialize()
        assert adapter.status == GroupChatStatus.IDLE

        result = await adapter.run("Test task")

        # 執行後應該是 COMPLETED
        assert adapter.status == GroupChatStatus.COMPLETED

        # 狀態應該被追蹤
        assert adapter.state is not None
