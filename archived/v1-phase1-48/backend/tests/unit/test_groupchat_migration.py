"""
GroupChatManager Migration Layer Tests - Sprint 16 (S16-6)

測試 groupchat_migration.py 模組的所有組件。

測試覆蓋:
    - Legacy 枚舉
    - Legacy 數據類
    - 轉換函數
    - GroupChatManagerAdapter 類
    - 工廠函數

Author: IPA Platform Team
Sprint: 16 - GroupChatBuilder 重構
Created: 2025-12-05
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any, List

# Import modules under test
from src.integrations.agent_framework.builders.groupchat_migration import (
    # Legacy enums
    SpeakerSelectionMethodLegacy,
    GroupChatStateLegacy,
    # Legacy data classes
    GroupParticipantLegacy,
    GroupMessageLegacy,
    GroupChatContextLegacy,
    GroupChatResultLegacy,
    # Conversion functions
    convert_selection_method_to_new,
    convert_selection_method_from_new,
    convert_state_to_legacy,
    convert_state_from_legacy,
    convert_participant_to_new,
    convert_participant_from_new,
    convert_message_to_new,
    convert_message_from_new,
    convert_result_to_legacy,
    # Adapter
    GroupChatManagerAdapter,
    # Selectors
    create_priority_selector,
    create_weighted_selector,
    # Factory functions
    migrate_groupchat_manager,
    create_groupchat_manager_adapter,
    create_priority_chat_manager,
    create_weighted_chat_manager,
)

from src.integrations.agent_framework.builders.groupchat import (
    SpeakerSelectionMethod,
    GroupChatStatus,
    GroupChatParticipant,
    GroupChatMessage,
    GroupChatResult,
    MessageRole,
)


# =============================================================================
# Legacy Enum Tests
# =============================================================================


class TestSpeakerSelectionMethodLegacy:
    """測試 SpeakerSelectionMethodLegacy 枚舉。"""

    def test_enum_values(self):
        """測試枚舉值。"""
        assert SpeakerSelectionMethodLegacy.AUTO == "auto"
        assert SpeakerSelectionMethodLegacy.ROUND_ROBIN == "round_robin"
        assert SpeakerSelectionMethodLegacy.RANDOM == "random"
        assert SpeakerSelectionMethodLegacy.MANUAL == "manual"
        assert SpeakerSelectionMethodLegacy.PRIORITY == "priority"
        assert SpeakerSelectionMethodLegacy.WEIGHTED == "weighted"


class TestGroupChatStateLegacy:
    """測試 GroupChatStateLegacy 枚舉。"""

    def test_enum_values(self):
        """測試枚舉值。"""
        assert GroupChatStateLegacy.IDLE == "idle"
        assert GroupChatStateLegacy.ACTIVE == "active"
        assert GroupChatStateLegacy.SELECTING == "selecting"
        assert GroupChatStateLegacy.SPEAKING == "speaking"
        assert GroupChatStateLegacy.TERMINATED == "terminated"
        assert GroupChatStateLegacy.ERROR == "error"


# =============================================================================
# Legacy Data Class Tests
# =============================================================================


class TestGroupParticipantLegacy:
    """測試 GroupParticipantLegacy 數據類。"""

    def test_basic_creation(self):
        """測試基本創建。"""
        participant = GroupParticipantLegacy(
            id="p1",
            name="Agent 1",
        )
        assert participant.id == "p1"
        assert participant.name == "Agent 1"
        assert participant.priority == 0
        assert participant.weight == 1.0

    def test_full_creation(self):
        """測試完整創建。"""
        participant = GroupParticipantLegacy(
            id="p1",
            name="Agent 1",
            agent=MagicMock(),
            role="researcher",
            priority=5,
            weight=2.0,
            metadata={"key": "value"},
        )
        assert participant.role == "researcher"
        assert participant.priority == 5
        assert participant.weight == 2.0

    def test_to_dict(self):
        """測試轉換為字典。"""
        participant = GroupParticipantLegacy(id="p1", name="Agent 1")
        data = participant.to_dict()
        assert data["id"] == "p1"
        assert data["name"] == "Agent 1"


class TestGroupMessageLegacy:
    """測試 GroupMessageLegacy 數據類。"""

    def test_basic_creation(self):
        """測試基本創建。"""
        msg = GroupMessageLegacy(
            content="Hello",
            sender_id="s1",
            sender_name="Sender 1",
        )
        assert msg.content == "Hello"
        assert msg.sender_id == "s1"
        assert msg.message_type == "chat"

    def test_to_dict(self):
        """測試轉換為字典。"""
        msg = GroupMessageLegacy(
            content="Test",
            sender_id="s1",
            sender_name="Sender",
        )
        data = msg.to_dict()
        assert data["content"] == "Test"


class TestGroupChatContextLegacy:
    """測試 GroupChatContextLegacy 數據類。"""

    def test_creation(self):
        """測試創建。"""
        context = GroupChatContextLegacy(
            chat_id="chat1",
            topic="Discussion",
        )
        assert context.chat_id == "chat1"
        assert context.topic == "Discussion"
        assert context.round_number == 0

    def test_to_dict(self):
        """測試轉換為字典。"""
        context = GroupChatContextLegacy(chat_id="chat1")
        data = context.to_dict()
        assert data["chat_id"] == "chat1"


class TestGroupChatResultLegacy:
    """測試 GroupChatResultLegacy 數據類。"""

    def test_creation(self):
        """測試創建。"""
        result = GroupChatResultLegacy(
            success=True,
            state=GroupChatStateLegacy.TERMINATED,
            total_rounds=5,
        )
        assert result.success is True
        assert result.state == GroupChatStateLegacy.TERMINATED
        assert result.total_rounds == 5

    def test_to_dict(self):
        """測試轉換為字典。"""
        result = GroupChatResultLegacy(
            success=True,
            state=GroupChatStateLegacy.TERMINATED,
        )
        data = result.to_dict()
        assert data["success"] is True
        assert data["state"] == "terminated"


# =============================================================================
# Conversion Function Tests
# =============================================================================


class TestConversionFunctions:
    """測試轉換函數。"""

    def test_convert_selection_method_to_new(self):
        """測試選擇方法轉換（Legacy -> New）。"""
        assert convert_selection_method_to_new(
            SpeakerSelectionMethodLegacy.AUTO
        ) == SpeakerSelectionMethod.AUTO

        assert convert_selection_method_to_new(
            SpeakerSelectionMethodLegacy.ROUND_ROBIN
        ) == SpeakerSelectionMethod.ROUND_ROBIN

        assert convert_selection_method_to_new(
            SpeakerSelectionMethodLegacy.RANDOM
        ) == SpeakerSelectionMethod.RANDOM

        # PRIORITY 和 WEIGHTED 映射到 CUSTOM
        assert convert_selection_method_to_new(
            SpeakerSelectionMethodLegacy.PRIORITY
        ) == SpeakerSelectionMethod.CUSTOM

        assert convert_selection_method_to_new(
            SpeakerSelectionMethodLegacy.WEIGHTED
        ) == SpeakerSelectionMethod.CUSTOM

    def test_convert_selection_method_from_new(self):
        """測試選擇方法轉換（New -> Legacy）。"""
        assert convert_selection_method_from_new(
            SpeakerSelectionMethod.AUTO
        ) == SpeakerSelectionMethodLegacy.AUTO

        assert convert_selection_method_from_new(
            SpeakerSelectionMethod.ROUND_ROBIN
        ) == SpeakerSelectionMethodLegacy.ROUND_ROBIN

    def test_convert_state_to_legacy(self):
        """測試狀態轉換（New -> Legacy）。"""
        assert convert_state_to_legacy(
            GroupChatStatus.IDLE
        ) == GroupChatStateLegacy.IDLE

        assert convert_state_to_legacy(
            GroupChatStatus.RUNNING
        ) == GroupChatStateLegacy.ACTIVE

        assert convert_state_to_legacy(
            GroupChatStatus.COMPLETED
        ) == GroupChatStateLegacy.TERMINATED

        assert convert_state_to_legacy(
            GroupChatStatus.FAILED
        ) == GroupChatStateLegacy.ERROR

    def test_convert_state_from_legacy(self):
        """測試狀態轉換（Legacy -> New）。"""
        assert convert_state_from_legacy(
            GroupChatStateLegacy.IDLE
        ) == GroupChatStatus.IDLE

        assert convert_state_from_legacy(
            GroupChatStateLegacy.ACTIVE
        ) == GroupChatStatus.RUNNING

        assert convert_state_from_legacy(
            GroupChatStateLegacy.TERMINATED
        ) == GroupChatStatus.COMPLETED

    def test_convert_participant_to_new(self):
        """測試參與者轉換（Legacy -> New）。"""
        legacy = GroupParticipantLegacy(
            id="p1",
            name="Agent 1",
            role="researcher",
            priority=5,
        )
        new = convert_participant_to_new(legacy)

        assert new.name == "Agent 1"
        assert new.description == "researcher"
        assert new.metadata["priority"] == 5

    def test_convert_participant_from_new(self):
        """測試參與者轉換（New -> Legacy）。"""
        new = GroupChatParticipant(
            name="Agent 1",
            description="Researcher",
            metadata={"legacy_id": "p1", "priority": 3},
        )
        legacy = convert_participant_from_new(new)

        assert legacy.id == "p1"
        assert legacy.name == "Agent 1"
        assert legacy.role == "Researcher"
        assert legacy.priority == 3

    def test_convert_message_to_new(self):
        """測試消息轉換（Legacy -> New）。"""
        legacy = GroupMessageLegacy(
            content="Hello",
            sender_id="s1",
            sender_name="Sender",
            message_type="user",
        )
        new = convert_message_to_new(legacy)

        assert new.content == "Hello"
        assert new.role == MessageRole.USER
        assert new.author_name == "Sender"

    def test_convert_message_from_new(self):
        """測試消息轉換（New -> Legacy）。"""
        new = GroupChatMessage(
            role=MessageRole.ASSISTANT,
            content="Response",
            author_name="Agent",
        )
        legacy = convert_message_from_new(new)

        assert legacy.content == "Response"
        assert legacy.sender_name == "Agent"
        assert legacy.message_type == "chat"

    def test_convert_result_to_legacy(self):
        """測試結果轉換。"""
        new_result = GroupChatResult(
            status=GroupChatStatus.COMPLETED,
            conversation=[
                GroupChatMessage(role=MessageRole.USER, content="Hi"),
            ],
            total_rounds=3,
            duration=10.5,
        )
        legacy = convert_result_to_legacy(new_result)

        assert legacy.success is True
        assert legacy.state == GroupChatStateLegacy.TERMINATED
        assert legacy.total_rounds == 3


# =============================================================================
# Selector Tests
# =============================================================================


class TestLegacySelectors:
    """測試 Legacy 選擇器。"""

    def test_priority_selector(self):
        """測試優先級選擇器。"""
        participants = [
            GroupParticipantLegacy(id="p1", name="Agent 1", priority=1),
            GroupParticipantLegacy(id="p2", name="Agent 2", priority=10),
            GroupParticipantLegacy(id="p3", name="Agent 3", priority=5),
        ]
        selector = create_priority_selector(participants)

        # 應該按優先級排序：Agent 2 (10), Agent 3 (5), Agent 1 (1)
        result0 = selector({"round_index": 0})
        assert result0 == "Agent 2"

    def test_weighted_selector(self):
        """測試加權選擇器。"""
        participants = [
            GroupParticipantLegacy(id="p1", name="Agent 1", weight=1.0),
            GroupParticipantLegacy(id="p2", name="Agent 2", weight=2.0),
        ]
        selector = create_weighted_selector(participants, seed=42)

        # 使用種子應該得到一致的結果
        result = selector({})
        assert result in ["Agent 1", "Agent 2"]


# =============================================================================
# GroupChatManagerAdapter Tests
# =============================================================================


class TestGroupChatManagerAdapter:
    """測試 GroupChatManagerAdapter 類。"""

    @pytest.fixture
    def sample_participants(self):
        """創建示例參與者。"""
        return [
            GroupParticipantLegacy(id="p1", name="Agent 1", role="researcher"),
            GroupParticipantLegacy(id="p2", name="Agent 2", role="writer"),
        ]

    def test_creation(self, sample_participants):
        """測試創建適配器。"""
        adapter = GroupChatManagerAdapter(
            chat_id="test-chat",
            participants=sample_participants,
        )
        assert adapter.chat_id == "test-chat"
        assert adapter.state == GroupChatStateLegacy.IDLE

    def test_add_participant(self, sample_participants):
        """測試添加參與者。"""
        adapter = GroupChatManagerAdapter(
            chat_id="test",
            participants=sample_participants,
        )
        new_participant = GroupParticipantLegacy(
            id="p3",
            name="Agent 3",
        )
        adapter.add_participant(new_participant)
        assert len(adapter.get_participants()) == 3

    def test_add_duplicate_participant_raises_error(self, sample_participants):
        """測試添加重複參與者拋出錯誤。"""
        adapter = GroupChatManagerAdapter(
            chat_id="test",
            participants=sample_participants,
        )
        duplicate = GroupParticipantLegacy(id="p1", name="Duplicate")
        with pytest.raises(ValueError, match="already exists"):
            adapter.add_participant(duplicate)

    def test_remove_participant(self, sample_participants):
        """測試移除參與者。"""
        adapter = GroupChatManagerAdapter(
            chat_id="test",
            participants=sample_participants,
        )
        result = adapter.remove_participant("p1")
        assert result is True
        assert len(adapter.get_participants()) == 1

    def test_get_participant(self, sample_participants):
        """測試獲取參與者。"""
        adapter = GroupChatManagerAdapter(
            chat_id="test",
            participants=sample_participants,
        )
        p = adapter.get_participant("p1")
        assert p is not None
        assert p.name == "Agent 1"

    def test_set_selection_method(self, sample_participants):
        """測試設置選擇方法。"""
        adapter = GroupChatManagerAdapter(
            chat_id="test",
            participants=sample_participants,
        )
        adapter.set_selection_method(SpeakerSelectionMethodLegacy.RANDOM)
        assert adapter._selection_method == SpeakerSelectionMethodLegacy.RANDOM

    @pytest.mark.asyncio
    async def test_start_chat(self, sample_participants):
        """測試開始對話。"""
        adapter = GroupChatManagerAdapter(
            chat_id="test",
            participants=sample_participants,
            max_rounds=2,
        )
        result = await adapter.start_chat("Test topic")

        assert result.success is True
        assert len(result.messages) > 0

    @pytest.mark.asyncio
    async def test_send_message(self, sample_participants):
        """測試發送消息。"""
        adapter = GroupChatManagerAdapter(
            chat_id="test",
            participants=sample_participants,
        )
        # 先開始對話
        await adapter.start_chat("Test")

        msg = await adapter.send_message("Hello", "p1")
        assert msg.content == "Hello"
        assert msg.sender_id == "p1"

    def test_get_messages(self, sample_participants):
        """測試獲取消息。"""
        adapter = GroupChatManagerAdapter(
            chat_id="test",
            participants=sample_participants,
        )
        messages = adapter.get_messages()
        assert isinstance(messages, list)

    @pytest.mark.asyncio
    async def test_terminate(self, sample_participants):
        """測試終止對話。"""
        adapter = GroupChatManagerAdapter(
            chat_id="test",
            participants=sample_participants,
        )
        result = await adapter.terminate()
        assert result is True
        assert adapter.state == GroupChatStateLegacy.TERMINATED

    def test_reset(self, sample_participants):
        """測試重置。"""
        adapter = GroupChatManagerAdapter(
            chat_id="test",
            participants=sample_participants,
        )
        adapter._state = GroupChatStateLegacy.ACTIVE
        adapter.reset()
        assert adapter.state == GroupChatStateLegacy.IDLE


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestMigrationFactoryFunctions:
    """測試遷移工廠函數。"""

    def test_create_groupchat_manager_adapter(self):
        """測試 create_groupchat_manager_adapter。"""
        participants = [
            GroupParticipantLegacy(id="p1", name="Agent 1"),
        ]
        adapter = create_groupchat_manager_adapter(
            chat_id="test",
            participants=participants,
        )
        assert adapter.chat_id == "test"

    def test_create_priority_chat_manager(self):
        """測試 create_priority_chat_manager。"""
        participants = [
            GroupParticipantLegacy(id="p1", name="Agent 1", priority=5),
            GroupParticipantLegacy(id="p2", name="Agent 2", priority=10),
        ]
        adapter = create_priority_chat_manager(
            chat_id="test",
            participants=participants,
        )
        assert adapter._selection_method == SpeakerSelectionMethodLegacy.PRIORITY

    def test_create_weighted_chat_manager(self):
        """測試 create_weighted_chat_manager。"""
        participants = [
            GroupParticipantLegacy(id="p1", name="Agent 1", weight=1.0),
            GroupParticipantLegacy(id="p2", name="Agent 2", weight=2.0),
        ]
        adapter = create_weighted_chat_manager(
            chat_id="test",
            participants=participants,
        )
        assert adapter._selection_method == SpeakerSelectionMethodLegacy.WEIGHTED

    def test_migrate_groupchat_manager(self):
        """測試 migrate_groupchat_manager。"""
        # 創建模擬的 legacy manager
        mock_manager = MagicMock()
        mock_manager.chat_id = "legacy-chat"
        mock_manager.selection_method = SpeakerSelectionMethodLegacy.ROUND_ROBIN
        mock_manager.max_rounds = 10
        mock_manager.participants = {
            "p1": GroupParticipantLegacy(id="p1", name="Agent 1"),
        }
        mock_manager.state = GroupChatStateLegacy.ACTIVE

        adapter = migrate_groupchat_manager(mock_manager)

        assert adapter.chat_id == "legacy-chat"
        assert adapter.state == GroupChatStateLegacy.ACTIVE
