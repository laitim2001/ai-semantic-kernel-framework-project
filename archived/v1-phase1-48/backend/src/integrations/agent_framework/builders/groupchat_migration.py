"""
GroupChatManager Migration Layer - Sprint 16

提供 Phase 2 GroupChatManager API 到 Agent Framework GroupChatBuilder 的遷移層。
保持向後兼容性，同時允許漸進式遷移到新的 API。

模組功能:
    1. GroupChatManagerAdapter - Phase 2 API 兼容適配器
    2. Legacy 數據類型轉換
    3. 狀態映射函數
    4. 工廠函數

遷移路徑:
    Phase 2 (GroupChatManager) → 遷移層 → Phase 3 (GroupChatBuilderAdapter)

API 兼容性:
    - GroupChatManager.start_chat() → GroupChatBuilderAdapter.run()
    - GroupChatManager.add_participant() → GroupChatBuilderAdapter.add_participant()
    - GroupChatManager.select_next_speaker() → 內部選擇邏輯

使用範例:
    # 使用遷移層保持舊 API
    adapter = GroupChatManagerAdapter(
        chat_id="team-discussion",
        participants=[participant1, participant2],
        selection_method=SpeakerSelectionMethodLegacy.ROUND_ROBIN,
    )
    result = await adapter.start_chat("Write a report")

    # 或者使用工廠函數遷移
    adapter = migrate_groupchat_manager(old_manager)

Author: IPA Platform Team
Sprint: 16 - GroupChatBuilder 重構
Created: 2025-12-05
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union, Awaitable
import logging
import asyncio
import time

from .groupchat import (
    GroupChatBuilderAdapter,
    GroupChatParticipant,
    GroupChatMessage,
    GroupChatState,
    GroupChatResult,
    GroupChatStatus,
    GroupChatTurn,
    SpeakerSelectionMethod,
    MessageRole,
    SpeakerSelectorFn,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Legacy Enumerations (Phase 2 API)
# =============================================================================


class SpeakerSelectionMethodLegacy(str, Enum):
    """
    Phase 2 發言者選擇方法枚舉（Legacy）。

    用於向後兼容 Phase 2 GroupChatManager API。

    Values:
        AUTO: 自動選擇（使用 LLM）
        ROUND_ROBIN: 輪流發言
        RANDOM: 隨機選擇
        MANUAL: 手動指定
        PRIORITY: 優先級選擇
        WEIGHTED: 加權選擇
    """
    AUTO = "auto"
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    MANUAL = "manual"
    PRIORITY = "priority"
    WEIGHTED = "weighted"


class GroupChatStateLegacy(str, Enum):
    """
    Phase 2 群組對話狀態枚舉（Legacy）。

    Values:
        IDLE: 空閒
        ACTIVE: 活躍
        SELECTING: 選擇發言者中
        SPEAKING: 發言中
        TERMINATED: 已終止
        ERROR: 錯誤
    """
    IDLE = "idle"
    ACTIVE = "active"
    SELECTING = "selecting"
    SPEAKING = "speaking"
    TERMINATED = "terminated"
    ERROR = "error"


# =============================================================================
# Legacy Data Classes (Phase 2 API)
# =============================================================================


@dataclass
class GroupParticipantLegacy:
    """
    Phase 2 群組參與者（Legacy）。

    Attributes:
        id: 參與者 ID
        name: 顯示名稱
        agent: Agent 實例
        role: 角色描述
        priority: 優先級（用於 PRIORITY 模式）
        weight: 權重（用於 WEIGHTED 模式）
        metadata: 附加元數據
    """
    id: str
    name: str
    agent: Any = None
    role: str = ""
    priority: int = 0
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式。"""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "priority": self.priority,
            "weight": self.weight,
            "metadata": self.metadata,
        }


@dataclass
class GroupMessageLegacy:
    """
    Phase 2 群組消息（Legacy）。

    Attributes:
        content: 消息內容
        sender_id: 發送者 ID
        sender_name: 發送者名稱
        message_type: 消息類型
        timestamp: 時間戳
        metadata: 附加元數據
    """
    content: str
    sender_id: str
    sender_name: str
    message_type: str = "chat"
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式。"""
        return {
            "content": self.content,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "message_type": self.message_type,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class GroupChatContextLegacy:
    """
    Phase 2 群組對話上下文（Legacy）。

    Attributes:
        chat_id: 對話 ID
        topic: 對話主題
        participants: 參與者列表
        messages: 消息歷史
        current_speaker: 當前發言者
        round_number: 輪數
        metadata: 附加元數據
    """
    chat_id: str
    topic: str = ""
    participants: List[GroupParticipantLegacy] = field(default_factory=list)
    messages: List[GroupMessageLegacy] = field(default_factory=list)
    current_speaker: Optional[str] = None
    round_number: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式。"""
        return {
            "chat_id": self.chat_id,
            "topic": self.topic,
            "participants": [p.to_dict() for p in self.participants],
            "messages": [m.to_dict() for m in self.messages],
            "current_speaker": self.current_speaker,
            "round_number": self.round_number,
            "metadata": self.metadata,
        }


@dataclass
class GroupChatResultLegacy:
    """
    Phase 2 群組對話結果（Legacy）。

    Attributes:
        success: 是否成功
        state: 結束狀態
        messages: 完整消息歷史
        summary: 對話摘要
        total_rounds: 總輪數
        participants_count: 參與人數
        duration: 執行時長
        metadata: 附加元數據
    """
    success: bool
    state: GroupChatStateLegacy
    messages: List[GroupMessageLegacy] = field(default_factory=list)
    summary: str = ""
    total_rounds: int = 0
    participants_count: int = 0
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式。"""
        return {
            "success": self.success,
            "state": self.state.value,
            "messages": [m.to_dict() for m in self.messages],
            "summary": self.summary,
            "total_rounds": self.total_rounds,
            "participants_count": self.participants_count,
            "duration": self.duration,
            "metadata": self.metadata,
        }


# =============================================================================
# Conversion Functions
# =============================================================================


def convert_selection_method_to_new(
    legacy_method: SpeakerSelectionMethodLegacy,
) -> SpeakerSelectionMethod:
    """
    將 Legacy 選擇方法轉換為新格式。

    Args:
        legacy_method: Phase 2 選擇方法

    Returns:
        Phase 3 選擇方法
    """
    mapping = {
        SpeakerSelectionMethodLegacy.AUTO: SpeakerSelectionMethod.AUTO,
        SpeakerSelectionMethodLegacy.ROUND_ROBIN: SpeakerSelectionMethod.ROUND_ROBIN,
        SpeakerSelectionMethodLegacy.RANDOM: SpeakerSelectionMethod.RANDOM,
        SpeakerSelectionMethodLegacy.MANUAL: SpeakerSelectionMethod.MANUAL,
        SpeakerSelectionMethodLegacy.PRIORITY: SpeakerSelectionMethod.CUSTOM,
        SpeakerSelectionMethodLegacy.WEIGHTED: SpeakerSelectionMethod.CUSTOM,
    }
    return mapping.get(legacy_method, SpeakerSelectionMethod.ROUND_ROBIN)


def convert_selection_method_from_new(
    new_method: SpeakerSelectionMethod,
) -> SpeakerSelectionMethodLegacy:
    """
    將新選擇方法轉換為 Legacy 格式。

    Args:
        new_method: Phase 3 選擇方法

    Returns:
        Phase 2 選擇方法
    """
    mapping = {
        SpeakerSelectionMethod.AUTO: SpeakerSelectionMethodLegacy.AUTO,
        SpeakerSelectionMethod.ROUND_ROBIN: SpeakerSelectionMethodLegacy.ROUND_ROBIN,
        SpeakerSelectionMethod.RANDOM: SpeakerSelectionMethodLegacy.RANDOM,
        SpeakerSelectionMethod.MANUAL: SpeakerSelectionMethodLegacy.MANUAL,
        SpeakerSelectionMethod.CUSTOM: SpeakerSelectionMethodLegacy.MANUAL,
    }
    return mapping.get(new_method, SpeakerSelectionMethodLegacy.ROUND_ROBIN)


def convert_state_to_legacy(
    new_status: GroupChatStatus,
) -> GroupChatStateLegacy:
    """
    將新狀態轉換為 Legacy 格式。

    Args:
        new_status: Phase 3 狀態

    Returns:
        Phase 2 狀態
    """
    mapping = {
        GroupChatStatus.IDLE: GroupChatStateLegacy.IDLE,
        GroupChatStatus.RUNNING: GroupChatStateLegacy.ACTIVE,
        GroupChatStatus.WAITING: GroupChatStateLegacy.SELECTING,
        GroupChatStatus.PAUSED: GroupChatStateLegacy.IDLE,
        GroupChatStatus.COMPLETED: GroupChatStateLegacy.TERMINATED,
        GroupChatStatus.FAILED: GroupChatStateLegacy.ERROR,
        GroupChatStatus.CANCELLED: GroupChatStateLegacy.TERMINATED,
    }
    return mapping.get(new_status, GroupChatStateLegacy.IDLE)


def convert_state_from_legacy(
    legacy_state: GroupChatStateLegacy,
) -> GroupChatStatus:
    """
    將 Legacy 狀態轉換為新格式。

    Args:
        legacy_state: Phase 2 狀態

    Returns:
        Phase 3 狀態
    """
    mapping = {
        GroupChatStateLegacy.IDLE: GroupChatStatus.IDLE,
        GroupChatStateLegacy.ACTIVE: GroupChatStatus.RUNNING,
        GroupChatStateLegacy.SELECTING: GroupChatStatus.WAITING,
        GroupChatStateLegacy.SPEAKING: GroupChatStatus.RUNNING,
        GroupChatStateLegacy.TERMINATED: GroupChatStatus.COMPLETED,
        GroupChatStateLegacy.ERROR: GroupChatStatus.FAILED,
    }
    return mapping.get(legacy_state, GroupChatStatus.IDLE)


def convert_participant_to_new(
    legacy_participant: GroupParticipantLegacy,
) -> GroupChatParticipant:
    """
    將 Legacy 參與者轉換為新格式。

    Args:
        legacy_participant: Phase 2 參與者

    Returns:
        Phase 3 參與者
    """
    return GroupChatParticipant(
        name=legacy_participant.name,
        description=legacy_participant.role or legacy_participant.name,
        agent=legacy_participant.agent,
        capabilities=[],
        metadata={
            "legacy_id": legacy_participant.id,
            "priority": legacy_participant.priority,
            "weight": legacy_participant.weight,
            **legacy_participant.metadata,
        },
    )


def convert_participant_from_new(
    new_participant: GroupChatParticipant,
) -> GroupParticipantLegacy:
    """
    將新參與者轉換為 Legacy 格式。

    Args:
        new_participant: Phase 3 參與者

    Returns:
        Phase 2 參與者
    """
    metadata = new_participant.metadata.copy()
    legacy_id = metadata.pop("legacy_id", new_participant.name)
    priority = metadata.pop("priority", 0)
    weight = metadata.pop("weight", 1.0)

    return GroupParticipantLegacy(
        id=legacy_id,
        name=new_participant.name,
        agent=new_participant.agent,
        role=new_participant.description,
        priority=priority,
        weight=weight,
        metadata=metadata,
    )


def convert_message_to_new(
    legacy_message: GroupMessageLegacy,
) -> GroupChatMessage:
    """
    將 Legacy 消息轉換為新格式。

    Args:
        legacy_message: Phase 2 消息

    Returns:
        Phase 3 消息
    """
    # 推斷角色
    role = MessageRole.ASSISTANT
    if legacy_message.message_type == "user":
        role = MessageRole.USER
    elif legacy_message.message_type == "system":
        role = MessageRole.SYSTEM
    elif legacy_message.message_type == "manager":
        role = MessageRole.MANAGER

    return GroupChatMessage(
        role=role,
        content=legacy_message.content,
        author_name=legacy_message.sender_name,
        timestamp=legacy_message.timestamp,
        metadata={
            "legacy_sender_id": legacy_message.sender_id,
            "legacy_message_type": legacy_message.message_type,
            **legacy_message.metadata,
        },
    )


def convert_message_from_new(
    new_message: GroupChatMessage,
) -> GroupMessageLegacy:
    """
    將新消息轉換為 Legacy 格式。

    Args:
        new_message: Phase 3 消息

    Returns:
        Phase 2 消息
    """
    # 推斷消息類型
    message_type = "chat"
    if new_message.role == MessageRole.USER:
        message_type = "user"
    elif new_message.role == MessageRole.SYSTEM:
        message_type = "system"
    elif new_message.role == MessageRole.MANAGER:
        message_type = "manager"

    metadata = new_message.metadata.copy()
    sender_id = metadata.pop("legacy_sender_id", new_message.author_name or "unknown")

    return GroupMessageLegacy(
        content=new_message.content,
        sender_id=sender_id,
        sender_name=new_message.author_name or "unknown",
        message_type=message_type,
        timestamp=new_message.timestamp or time.time(),
        metadata=metadata,
    )


def convert_result_to_legacy(
    new_result: GroupChatResult,
) -> GroupChatResultLegacy:
    """
    將新結果轉換為 Legacy 格式。

    Args:
        new_result: Phase 3 結果

    Returns:
        Phase 2 結果
    """
    legacy_state = convert_state_to_legacy(new_result.status)
    success = new_result.status == GroupChatStatus.COMPLETED

    legacy_messages = [
        convert_message_from_new(msg) for msg in new_result.conversation
    ]

    summary = ""
    if new_result.final_message:
        summary = new_result.final_message.content

    return GroupChatResultLegacy(
        success=success,
        state=legacy_state,
        messages=legacy_messages,
        summary=summary,
        total_rounds=new_result.total_rounds,
        participants_count=len(new_result.participants_involved),
        duration=new_result.duration,
        metadata=new_result.metadata,
    )


# =============================================================================
# GroupChatManagerAdapter (Phase 2 API Compatible)
# =============================================================================


class GroupChatManagerAdapter:
    """
    Phase 2 GroupChatManager API 兼容適配器。

    提供與 Phase 2 GroupChatManager 相同的 API，
    內部使用 GroupChatBuilderAdapter 實現。

    這個適配器讓現有代碼可以無縫遷移到新的架構，
    同時保持所有原有功能正常工作。

    Example:
        # Phase 2 風格的使用方式
        adapter = GroupChatManagerAdapter(
            chat_id="team-discussion",
            participants=[participant1, participant2],
            selection_method=SpeakerSelectionMethodLegacy.ROUND_ROBIN,
            max_rounds=10,
        )

        # 添加參與者
        adapter.add_participant(new_participant)

        # 開始對話
        result = await adapter.start_chat("Write a report")

        # 獲取消息歷史
        messages = adapter.get_messages()
    """

    def __init__(
        self,
        chat_id: str,
        participants: Optional[List[GroupParticipantLegacy]] = None,
        selection_method: SpeakerSelectionMethodLegacy = SpeakerSelectionMethodLegacy.ROUND_ROBIN,
        manager_agent: Any = None,
        max_rounds: Optional[int] = None,
        termination_callback: Optional[Callable[[List[GroupMessageLegacy]], bool]] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化 GroupChatManagerAdapter。

        Args:
            chat_id: 對話 ID
            participants: 參與者列表（Legacy 格式）
            selection_method: 選擇方法（Legacy）
            manager_agent: 管理者 Agent（AUTO 模式）
            max_rounds: 最大輪數
            termination_callback: 終止回調（Legacy 格式）
            config: 額外配置
        """
        self._chat_id = chat_id
        self._selection_method = selection_method
        self._manager_agent = manager_agent
        self._max_rounds = max_rounds
        self._config = config or {}

        # 轉換參與者
        self._legacy_participants: Dict[str, GroupParticipantLegacy] = {}
        new_participants = []
        if participants:
            for p in participants:
                self._legacy_participants[p.id] = p
                new_participants.append(convert_participant_to_new(p))

        # 轉換終止條件
        termination_condition = None
        if termination_callback:
            def wrapped_condition(messages: List[GroupChatMessage]) -> bool:
                legacy_messages = [convert_message_from_new(m) for m in messages]
                return termination_callback(legacy_messages)
            termination_condition = wrapped_condition

        # 創建內部適配器
        self._adapter = GroupChatBuilderAdapter(
            id=chat_id,
            participants=new_participants if new_participants else [
                GroupChatParticipant(name="default", description="Default participant")
            ],
            selection_method=convert_selection_method_to_new(selection_method),
            manager_agent=manager_agent,
            max_rounds=max_rounds,
            termination_condition=termination_condition,
            config=config,
        )

        # 狀態追蹤
        self._state = GroupChatStateLegacy.IDLE
        self._context: Optional[GroupChatContextLegacy] = None
        self._events: List[Dict[str, Any]] = []

        logger.info(
            f"GroupChatManagerAdapter created: {chat_id}, "
            f"method={selection_method.value}, participants={len(new_participants)}"
        )

    @property
    def chat_id(self) -> str:
        """獲取對話 ID。"""
        return self._chat_id

    @property
    def state(self) -> GroupChatStateLegacy:
        """獲取當前狀態（Legacy）。"""
        return self._state

    @property
    def context(self) -> Optional[GroupChatContextLegacy]:
        """獲取當前上下文（Legacy）。"""
        return self._context

    def add_participant(self, participant: GroupParticipantLegacy) -> None:
        """
        添加參與者。

        Args:
            participant: 參與者（Legacy 格式）

        Raises:
            ValueError: 如果 ID 已存在
        """
        if participant.id in self._legacy_participants:
            raise ValueError(f"Participant '{participant.id}' already exists")

        self._legacy_participants[participant.id] = participant
        new_participant = convert_participant_to_new(participant)
        self._adapter.add_participant(new_participant)

        logger.info(f"Added participant: {participant.id}")

    def remove_participant(self, participant_id: str) -> bool:
        """
        移除參與者。

        Args:
            participant_id: 參與者 ID

        Returns:
            是否成功移除
        """
        if participant_id not in self._legacy_participants:
            return False

        participant = self._legacy_participants.pop(participant_id)
        self._adapter.remove_participant(participant.name)

        logger.info(f"Removed participant: {participant_id}")
        return True

    def get_participant(self, participant_id: str) -> Optional[GroupParticipantLegacy]:
        """
        獲取參與者。

        Args:
            participant_id: 參與者 ID

        Returns:
            參與者實例或 None
        """
        return self._legacy_participants.get(participant_id)

    def get_participants(self) -> List[GroupParticipantLegacy]:
        """獲取所有參與者。"""
        return list(self._legacy_participants.values())

    def set_selection_method(
        self,
        method: SpeakerSelectionMethodLegacy,
    ) -> None:
        """
        設置選擇方法。

        Args:
            method: 選擇方法（Legacy）
        """
        self._selection_method = method
        new_method = convert_selection_method_to_new(method)
        self._adapter.set_selection_method(new_method)

        logger.info(f"Selection method set to: {method.value}")

    def set_max_rounds(self, max_rounds: Optional[int]) -> None:
        """
        設置最大輪數。

        Args:
            max_rounds: 最大輪數
        """
        self._max_rounds = max_rounds
        self._adapter.set_max_rounds(max_rounds)

    async def start_chat(
        self,
        topic: str,
        initial_message: Optional[str] = None,
    ) -> GroupChatResultLegacy:
        """
        開始群組對話。

        Args:
            topic: 對話主題
            initial_message: 初始消息（默認使用 topic）

        Returns:
            對話結果（Legacy 格式）
        """
        self._state = GroupChatStateLegacy.ACTIVE

        # 初始化上下文
        self._context = GroupChatContextLegacy(
            chat_id=self._chat_id,
            topic=topic,
            participants=list(self._legacy_participants.values()),
        )

        # 執行對話
        input_message = initial_message or topic
        result = await self._adapter.run(input_message)

        # 轉換結果
        legacy_result = convert_result_to_legacy(result)

        # 更新狀態
        self._state = legacy_result.state
        self._context.messages = legacy_result.messages
        self._context.round_number = legacy_result.total_rounds

        return legacy_result

    async def send_message(
        self,
        content: str,
        sender_id: str,
    ) -> GroupMessageLegacy:
        """
        發送消息到對話。

        Args:
            content: 消息內容
            sender_id: 發送者 ID

        Returns:
            發送的消息（Legacy 格式）
        """
        sender = self._legacy_participants.get(sender_id)
        sender_name = sender.name if sender else sender_id

        message = GroupMessageLegacy(
            content=content,
            sender_id=sender_id,
            sender_name=sender_name,
        )

        if self._context:
            self._context.messages.append(message)

        return message

    def get_messages(self) -> List[GroupMessageLegacy]:
        """獲取所有消息。"""
        if self._context:
            return self._context.messages.copy()
        return []

    def get_current_speaker(self) -> Optional[str]:
        """獲取當前發言者 ID。"""
        if self._context:
            return self._context.current_speaker
        return None

    def get_round_number(self) -> int:
        """獲取當前輪數。"""
        if self._context:
            return self._context.round_number
        return 0

    async def terminate(self) -> bool:
        """
        終止對話。

        Returns:
            是否成功終止
        """
        self._state = GroupChatStateLegacy.TERMINATED
        return True

    def reset(self) -> None:
        """重置管理器狀態。"""
        self._state = GroupChatStateLegacy.IDLE
        self._context = None
        self._events.clear()
        self._adapter.reset()

    def on_event(self, event_type: str, callback: Callable) -> None:
        """
        註冊事件回調。

        Args:
            event_type: 事件類型
            callback: 回調函數
        """
        # 事件系統（簡化實現）
        self._events.append({
            "type": event_type,
            "callback": callback,
        })


# =============================================================================
# Priority and Weighted Selectors (for Legacy compatibility)
# =============================================================================


def create_priority_selector(
    participants: List[GroupParticipantLegacy],
) -> SpeakerSelectorFn:
    """
    創建優先級選擇器。

    按優先級從高到低選擇，優先級相同時輪流。

    Args:
        participants: 參與者列表（Legacy 格式）

    Returns:
        選擇函數
    """
    # 按優先級排序
    sorted_participants = sorted(
        participants,
        key=lambda p: p.priority,
        reverse=True,
    )
    names = [p.name for p in sorted_participants]

    def selector(state: Dict[str, Any]) -> Optional[str]:
        history = state.get("history", [])
        round_index = state.get("round_index", 0)

        if not names:
            return None

        # 按優先級順序選擇
        index = round_index % len(names)
        return names[index]

    return selector


def create_weighted_selector(
    participants: List[GroupParticipantLegacy],
    seed: Optional[int] = None,
) -> SpeakerSelectorFn:
    """
    創建加權選擇器。

    根據權重隨機選擇發言者。

    Args:
        participants: 參與者列表（Legacy 格式）
        seed: 隨機種子

    Returns:
        選擇函數
    """
    import random
    rng = random.Random(seed)

    names = [p.name for p in participants]
    weights = [p.weight for p in participants]

    def selector(state: Dict[str, Any]) -> Optional[str]:
        if not names:
            return None

        # 加權隨機選擇
        selected = rng.choices(names, weights=weights, k=1)
        return selected[0] if selected else None

    return selector


# =============================================================================
# Factory Functions
# =============================================================================


def migrate_groupchat_manager(
    legacy_manager: Any,
    preserve_state: bool = True,
) -> GroupChatManagerAdapter:
    """
    將 Phase 2 GroupChatManager 遷移到適配器。

    Args:
        legacy_manager: Phase 2 GroupChatManager 實例
        preserve_state: 是否保留狀態

    Returns:
        遷移後的適配器
    """
    # 提取配置
    chat_id = getattr(legacy_manager, "chat_id", "migrated-chat")
    selection_method = getattr(
        legacy_manager,
        "selection_method",
        SpeakerSelectionMethodLegacy.ROUND_ROBIN,
    )
    max_rounds = getattr(legacy_manager, "max_rounds", None)

    # 提取參與者
    participants = []
    legacy_participants = getattr(legacy_manager, "participants", {})
    for pid, p in legacy_participants.items():
        if isinstance(p, GroupParticipantLegacy):
            participants.append(p)
        else:
            participants.append(GroupParticipantLegacy(
                id=pid,
                name=getattr(p, "name", pid),
                agent=getattr(p, "agent", None),
                role=getattr(p, "role", ""),
            ))

    # 創建適配器
    adapter = GroupChatManagerAdapter(
        chat_id=chat_id,
        participants=participants,
        selection_method=selection_method,
        max_rounds=max_rounds,
    )

    # 保留狀態
    if preserve_state:
        legacy_state = getattr(legacy_manager, "state", None)
        if legacy_state:
            adapter._state = legacy_state

        legacy_context = getattr(legacy_manager, "context", None)
        if legacy_context:
            adapter._context = legacy_context

    logger.info(f"Migrated GroupChatManager: {chat_id}")
    return adapter


def create_groupchat_manager_adapter(
    chat_id: str,
    participants: Optional[List[GroupParticipantLegacy]] = None,
    selection_method: SpeakerSelectionMethodLegacy = SpeakerSelectionMethodLegacy.ROUND_ROBIN,
    **kwargs,
) -> GroupChatManagerAdapter:
    """
    創建 GroupChatManager 適配器的便捷工廠函數。

    Args:
        chat_id: 對話 ID
        participants: 參與者列表
        selection_method: 選擇方法
        **kwargs: 其他配置參數

    Returns:
        配置好的適配器實例
    """
    return GroupChatManagerAdapter(
        chat_id=chat_id,
        participants=participants,
        selection_method=selection_method,
        **kwargs,
    )


def create_priority_chat_manager(
    chat_id: str,
    participants: List[GroupParticipantLegacy],
    max_rounds: Optional[int] = 10,
) -> GroupChatManagerAdapter:
    """
    創建優先級選擇的群組對話管理器。

    Args:
        chat_id: 對話 ID
        participants: 參與者列表（包含優先級）
        max_rounds: 最大輪數

    Returns:
        配置好的適配器實例
    """
    return GroupChatManagerAdapter(
        chat_id=chat_id,
        participants=participants,
        selection_method=SpeakerSelectionMethodLegacy.PRIORITY,
        max_rounds=max_rounds,
    )


def create_weighted_chat_manager(
    chat_id: str,
    participants: List[GroupParticipantLegacy],
    max_rounds: Optional[int] = 10,
) -> GroupChatManagerAdapter:
    """
    創建加權選擇的群組對話管理器。

    Args:
        chat_id: 對話 ID
        participants: 參與者列表（包含權重）
        max_rounds: 最大輪數

    Returns:
        配置好的適配器實例
    """
    return GroupChatManagerAdapter(
        chat_id=chat_id,
        participants=participants,
        selection_method=SpeakerSelectionMethodLegacy.WEIGHTED,
        max_rounds=max_rounds,
    )
