# =============================================================================
# IPA Platform - GroupChat Manager
# =============================================================================
# Sprint 9: S9-1 GroupChatManager (8 points)
#
# Core group chat management for multi-Agent conversations.
# Supports multiple speaker selection methods and termination conditions.
# =============================================================================

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class SpeakerSelectionMethod(str, Enum):
    """Methods for selecting the next speaker in a group chat.

    發言者選擇方法:
    - AUTO: LLM 自動選擇最適合的發言者
    - ROUND_ROBIN: 按順序輪流發言
    - RANDOM: 隨機選擇發言者
    - MANUAL: 由用戶手動指定
    - PRIORITY: 按優先級選擇
    - EXPERTISE: 按專業能力匹配選擇
    """
    AUTO = "auto"
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    MANUAL = "manual"
    PRIORITY = "priority"
    EXPERTISE = "expertise"


class MessageType(str, Enum):
    """Types of messages in a group chat.

    訊息類型:
    - USER: 用戶發送的訊息
    - AGENT: Agent 發送的訊息
    - SYSTEM: 系統訊息（如加入/離開通知）
    - FUNCTION_CALL: 函數調用請求
    - FUNCTION_RESULT: 函數調用結果
    """
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
    FUNCTION_CALL = "function_call"
    FUNCTION_RESULT = "function_result"


class GroupChatStatus(str, Enum):
    """Status of a group chat session.

    群組聊天狀態:
    - CREATED: 已創建，等待開始
    - ACTIVE: 進行中
    - PAUSED: 暫停
    - TERMINATED: 已終止
    - COMPLETED: 已完成
    """
    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATED = "terminated"
    COMPLETED = "completed"


@dataclass
class GroupMessage:
    """Represents a message in a group chat.

    群組訊息數據類，包含發送者、內容、類型等信息。

    Attributes:
        id: 訊息唯一標識符
        group_id: 所屬群組 ID
        sender_id: 發送者 ID
        sender_name: 發送者名稱
        content: 訊息內容
        message_type: 訊息類型
        timestamp: 發送時間
        metadata: 額外元數據
        reply_to: 回覆的訊息 ID（可選）
    """
    id: str
    group_id: str
    sender_id: str
    sender_name: str
    content: str
    message_type: MessageType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    reply_to: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format."""
        return {
            "id": self.id,
            "group_id": self.group_id,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "content": self.content,
            "message_type": self.message_type.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "reply_to": self.reply_to,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GroupMessage":
        """Create message from dictionary."""
        return cls(
            id=data["id"],
            group_id=data["group_id"],
            sender_id=data["sender_id"],
            sender_name=data["sender_name"],
            content=data["content"],
            message_type=MessageType(data["message_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]) if isinstance(data["timestamp"], str) else data["timestamp"],
            metadata=data.get("metadata", {}),
            reply_to=data.get("reply_to"),
        )


@dataclass
class GroupChatConfig:
    """Configuration for a group chat session.

    群組聊天配置，定義對話的各項參數。

    Attributes:
        max_rounds: 最大對話輪次（預設 10）
        max_messages_per_round: 每輪最大訊息數（預設 5）
        speaker_selection_method: 發言者選擇方法
        allow_repeat_speaker: 是否允許連續發言
        termination_conditions: 終止條件配置
        timeout_seconds: 對話超時時間（秒）
        enable_voting: 是否啟用投票功能
        consensus_threshold: 共識閾值（0-1）
    """
    max_rounds: int = 10
    max_messages_per_round: int = 5
    speaker_selection_method: SpeakerSelectionMethod = SpeakerSelectionMethod.AUTO
    allow_repeat_speaker: bool = False
    termination_conditions: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300  # 5 minutes default
    enable_voting: bool = False
    consensus_threshold: float = 0.7

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary format."""
        return {
            "max_rounds": self.max_rounds,
            "max_messages_per_round": self.max_messages_per_round,
            "speaker_selection_method": self.speaker_selection_method.value,
            "allow_repeat_speaker": self.allow_repeat_speaker,
            "termination_conditions": self.termination_conditions,
            "timeout_seconds": self.timeout_seconds,
            "enable_voting": self.enable_voting,
            "consensus_threshold": self.consensus_threshold,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GroupChatConfig":
        """Create config from dictionary."""
        return cls(
            max_rounds=data.get("max_rounds", 10),
            max_messages_per_round=data.get("max_messages_per_round", 5),
            speaker_selection_method=SpeakerSelectionMethod(data.get("speaker_selection_method", "auto")),
            allow_repeat_speaker=data.get("allow_repeat_speaker", False),
            termination_conditions=data.get("termination_conditions", {}),
            timeout_seconds=data.get("timeout_seconds", 300),
            enable_voting=data.get("enable_voting", False),
            consensus_threshold=data.get("consensus_threshold", 0.7),
        )


@dataclass
class AgentInfo:
    """Information about an agent participating in group chat.

    參與群組聊天的 Agent 資訊。

    Attributes:
        agent_id: Agent 唯一標識符
        name: Agent 名稱
        description: Agent 描述
        capabilities: Agent 能力列表
        priority: 發言優先級（數值越小優先級越高）
        is_active: 是否處於活躍狀態
    """
    agent_id: str
    name: str
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    priority: int = 0
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert agent info to dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "priority": self.priority,
            "is_active": self.is_active,
        }


@dataclass
class GroupChatState:
    """State of a group chat session.

    群組聊天狀態，追蹤對話的當前狀態。

    Attributes:
        group_id: 群組唯一標識符
        name: 群組名稱
        status: 當前狀態
        agents: 參與的 Agent 列表
        messages: 訊息歷史
        current_round: 當前輪次
        current_speaker_id: 當前發言者 ID
        config: 群組配置
        created_at: 創建時間
        started_at: 開始時間
        ended_at: 結束時間
        metadata: 額外元數據
    """
    group_id: str
    name: str
    status: GroupChatStatus = GroupChatStatus.CREATED
    agents: List[AgentInfo] = field(default_factory=list)
    messages: List[GroupMessage] = field(default_factory=list)
    current_round: int = 0
    current_speaker_id: Optional[str] = None
    config: GroupChatConfig = field(default_factory=GroupChatConfig)
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary format."""
        return {
            "group_id": self.group_id,
            "name": self.name,
            "status": self.status.value,
            "agents": [a.to_dict() for a in self.agents],
            "messages": [m.to_dict() for m in self.messages],
            "current_round": self.current_round,
            "current_speaker_id": self.current_speaker_id,
            "config": self.config.to_dict(),
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "metadata": self.metadata,
        }

    @property
    def agent_ids(self) -> List[str]:
        """Get list of agent IDs."""
        return [a.agent_id for a in self.agents]

    @property
    def active_agents(self) -> List[AgentInfo]:
        """Get list of active agents."""
        return [a for a in self.agents if a.is_active]

    @property
    def message_count(self) -> int:
        """Get total message count."""
        return len(self.messages)

    @property
    def round_message_count(self) -> int:
        """Get message count for current round."""
        return sum(
            1 for m in self.messages
            if m.metadata.get("round") == self.current_round
        )


class GroupChatManager:
    """Manages multi-Agent group chat conversations.

    群組聊天管理器，負責管理多 Agent 對話的生命週期、
    發言者選擇、訊息處理和終止判斷。

    主要功能:
    - 創建和管理群組聊天
    - 控制對話輪次
    - 選擇發言者
    - 處理訊息
    - 判斷終止條件

    Example:
        ```python
        manager = GroupChatManager()

        # 創建群組
        state = await manager.create_group_chat(
            name="Planning Session",
            agents=[agent1, agent2],
            config=GroupChatConfig(max_rounds=5)
        )

        # 開始對話
        await manager.start_conversation(state.group_id, initial_message="Let's plan the project")
        ```
    """

    def __init__(
        self,
        speaker_selector: Optional[Callable] = None,
        termination_checker: Optional[Callable] = None,
        llm_client: Optional[Any] = None,
    ):
        """Initialize the GroupChatManager.

        Args:
            speaker_selector: 自定義發言者選擇器
            termination_checker: 自定義終止檢查器
            llm_client: LLM 客戶端（用於 AUTO 模式）
        """
        self._groups: Dict[str, GroupChatState] = {}
        self._speaker_selector = speaker_selector
        self._termination_checker = termination_checker
        self._llm_client = llm_client
        self._message_handlers: List[Callable] = []
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

        logger.info("GroupChatManager initialized")

    # =========================================================================
    # Group Management
    # =========================================================================

    async def create_group_chat(
        self,
        name: str,
        agents: List[AgentInfo],
        config: Optional[GroupChatConfig] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GroupChatState:
        """Create a new group chat.

        創建新的群組聊天。

        Args:
            name: 群組名稱
            agents: 參與的 Agent 列表
            config: 群組配置（可選）
            metadata: 額外元數據（可選）

        Returns:
            GroupChatState: 新創建的群組狀態

        Raises:
            ValueError: 如果 Agent 列表為空或配置無效
        """
        if not agents:
            raise ValueError("At least one agent is required to create a group chat")

        group_id = str(uuid.uuid4())

        state = GroupChatState(
            group_id=group_id,
            name=name,
            status=GroupChatStatus.CREATED,
            agents=agents,
            config=config or GroupChatConfig(),
            metadata=metadata or {},
        )

        self._groups[group_id] = state
        self._locks[group_id] = asyncio.Lock()

        logger.info(f"Created group chat: {group_id} ({name}) with {len(agents)} agents")
        await self._emit_event("group_created", state)

        return state

    async def get_group_chat(self, group_id: str) -> Optional[GroupChatState]:
        """Get group chat state by ID.

        Args:
            group_id: 群組 ID

        Returns:
            群組狀態，如果不存在則返回 None
        """
        return self._groups.get(group_id)

    async def delete_group_chat(self, group_id: str) -> bool:
        """Delete a group chat.

        Args:
            group_id: 群組 ID

        Returns:
            是否成功刪除
        """
        if group_id in self._groups:
            state = self._groups.pop(group_id)
            self._locks.pop(group_id, None)
            logger.info(f"Deleted group chat: {group_id}")
            await self._emit_event("group_deleted", state)
            return True
        return False

    async def list_group_chats(
        self,
        status: Optional[GroupChatStatus] = None,
    ) -> List[GroupChatState]:
        """List all group chats with optional status filter.

        Args:
            status: 狀態過濾（可選）

        Returns:
            群組列表
        """
        groups = list(self._groups.values())
        if status:
            groups = [g for g in groups if g.status == status]
        return groups

    # =========================================================================
    # Agent Management
    # =========================================================================

    async def add_agent(
        self,
        group_id: str,
        agent: AgentInfo,
    ) -> bool:
        """Add an agent to a group chat.

        Args:
            group_id: 群組 ID
            agent: Agent 資訊

        Returns:
            是否成功添加
        """
        state = await self.get_group_chat(group_id)
        if not state:
            return False

        if agent.agent_id in state.agent_ids:
            logger.warning(f"Agent {agent.agent_id} already in group {group_id}")
            return False

        async with self._locks[group_id]:
            state.agents.append(agent)

            # Add system message
            await self._add_system_message(
                state,
                f"{agent.name} joined the conversation"
            )

        logger.info(f"Agent {agent.agent_id} added to group {group_id}")
        await self._emit_event("agent_added", {"group_id": group_id, "agent": agent})
        return True

    async def remove_agent(
        self,
        group_id: str,
        agent_id: str,
    ) -> bool:
        """Remove an agent from a group chat.

        Args:
            group_id: 群組 ID
            agent_id: Agent ID

        Returns:
            是否成功移除
        """
        state = await self.get_group_chat(group_id)
        if not state:
            return False

        async with self._locks[group_id]:
            agent = next((a for a in state.agents if a.agent_id == agent_id), None)
            if not agent:
                return False

            state.agents = [a for a in state.agents if a.agent_id != agent_id]

            # Add system message
            await self._add_system_message(
                state,
                f"{agent.name} left the conversation"
            )

        logger.info(f"Agent {agent_id} removed from group {group_id}")
        await self._emit_event("agent_removed", {"group_id": group_id, "agent_id": agent_id})
        return True

    # =========================================================================
    # Conversation Control
    # =========================================================================

    async def start_conversation(
        self,
        group_id: str,
        initial_message: Optional[str] = None,
        sender_id: Optional[str] = None,
        sender_name: str = "User",
    ) -> GroupChatState:
        """Start a group chat conversation.

        開始群組對話。

        Args:
            group_id: 群組 ID
            initial_message: 初始訊息（可選）
            sender_id: 發送者 ID（可選）
            sender_name: 發送者名稱

        Returns:
            更新後的群組狀態

        Raises:
            ValueError: 如果群組不存在或狀態無效
        """
        state = await self.get_group_chat(group_id)
        if not state:
            raise ValueError(f"Group chat {group_id} not found")

        if state.status not in [GroupChatStatus.CREATED, GroupChatStatus.PAUSED]:
            raise ValueError(f"Cannot start conversation in status: {state.status.value}")

        async with self._locks[group_id]:
            state.status = GroupChatStatus.ACTIVE
            state.started_at = datetime.utcnow()
            state.current_round = 1

            # Add initial message if provided
            if initial_message:
                message = GroupMessage(
                    id=str(uuid.uuid4()),
                    group_id=group_id,
                    sender_id=sender_id or "user",
                    sender_name=sender_name,
                    content=initial_message,
                    message_type=MessageType.USER,
                    metadata={"round": 1},
                )
                state.messages.append(message)

        logger.info(f"Started conversation for group {group_id}")
        await self._emit_event("conversation_started", state)

        return state

    async def execute_round(
        self,
        group_id: str,
        get_agent_response: Callable[[str, str, List[GroupMessage]], str],
    ) -> Optional[GroupMessage]:
        """Execute one round of conversation.

        執行一輪對話。

        Args:
            group_id: 群組 ID
            get_agent_response: 獲取 Agent 回應的回調函數

        Returns:
            新的訊息，如果對話終止則返回 None
        """
        state = await self.get_group_chat(group_id)
        if not state or state.status != GroupChatStatus.ACTIVE:
            return None

        async with self._locks[group_id]:
            # Check termination
            if await self._should_terminate(state):
                state.status = GroupChatStatus.COMPLETED
                state.ended_at = datetime.utcnow()
                await self._emit_event("conversation_completed", state)
                return None

            # Select next speaker
            next_speaker = await self._select_next_speaker(state)
            if not next_speaker:
                logger.warning(f"No available speaker for group {group_id}")
                return None

            state.current_speaker_id = next_speaker.agent_id

            # Build context for agent
            context = await self._build_context_for_agent(state, next_speaker)

            # Get agent response
            response_content = await asyncio.get_event_loop().run_in_executor(
                None,
                get_agent_response,
                next_speaker.agent_id,
                context,
                state.messages[-10:],  # Last 10 messages for context
            )

            # Create response message
            message = GroupMessage(
                id=str(uuid.uuid4()),
                group_id=group_id,
                sender_id=next_speaker.agent_id,
                sender_name=next_speaker.name,
                content=response_content,
                message_type=MessageType.AGENT,
                metadata={"round": state.current_round},
            )
            state.messages.append(message)

            # Check if round should end
            if state.round_message_count >= state.config.max_messages_per_round:
                state.current_round += 1
                await self._emit_event("round_completed", {
                    "group_id": group_id,
                    "round": state.current_round - 1,
                })

        await self._emit_event("message_added", message)
        return message

    async def add_message(
        self,
        group_id: str,
        content: str,
        sender_id: str,
        sender_name: str,
        message_type: MessageType = MessageType.USER,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[GroupMessage]:
        """Add a message to the group chat.

        添加訊息到群組聊天。

        Args:
            group_id: 群組 ID
            content: 訊息內容
            sender_id: 發送者 ID
            sender_name: 發送者名稱
            message_type: 訊息類型
            reply_to: 回覆的訊息 ID
            metadata: 額外元數據

        Returns:
            創建的訊息，如果群組不存在則返回 None
        """
        state = await self.get_group_chat(group_id)
        if not state:
            return None

        async with self._locks[group_id]:
            message = GroupMessage(
                id=str(uuid.uuid4()),
                group_id=group_id,
                sender_id=sender_id,
                sender_name=sender_name,
                content=content,
                message_type=message_type,
                reply_to=reply_to,
                metadata={
                    **(metadata or {}),
                    "round": state.current_round,
                },
            )
            state.messages.append(message)

        await self._emit_event("message_added", message)

        # Notify message handlers
        for handler in self._message_handlers:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Message handler error: {e}")

        return message

    async def pause_conversation(self, group_id: str) -> bool:
        """Pause the conversation.

        暫停對話。

        Args:
            group_id: 群組 ID

        Returns:
            是否成功暫停
        """
        state = await self.get_group_chat(group_id)
        if not state or state.status != GroupChatStatus.ACTIVE:
            return False

        async with self._locks[group_id]:
            state.status = GroupChatStatus.PAUSED

        logger.info(f"Paused conversation for group {group_id}")
        await self._emit_event("conversation_paused", state)
        return True

    async def resume_conversation(self, group_id: str) -> bool:
        """Resume a paused conversation.

        恢復暫停的對話。

        Args:
            group_id: 群組 ID

        Returns:
            是否成功恢復
        """
        state = await self.get_group_chat(group_id)
        if not state or state.status != GroupChatStatus.PAUSED:
            return False

        async with self._locks[group_id]:
            state.status = GroupChatStatus.ACTIVE

        logger.info(f"Resumed conversation for group {group_id}")
        await self._emit_event("conversation_resumed", state)
        return True

    async def terminate_conversation(
        self,
        group_id: str,
        reason: str = "Manual termination",
    ) -> bool:
        """Terminate the conversation.

        終止對話。

        Args:
            group_id: 群組 ID
            reason: 終止原因

        Returns:
            是否成功終止
        """
        state = await self.get_group_chat(group_id)
        if not state or state.status in [GroupChatStatus.TERMINATED, GroupChatStatus.COMPLETED]:
            return False

        async with self._locks[group_id]:
            state.status = GroupChatStatus.TERMINATED
            state.ended_at = datetime.utcnow()
            state.metadata["termination_reason"] = reason

            # Add system message
            await self._add_system_message(state, f"Conversation terminated: {reason}")

        logger.info(f"Terminated conversation for group {group_id}: {reason}")
        await self._emit_event("conversation_terminated", state)
        return True

    # =========================================================================
    # Transcript and Summary
    # =========================================================================

    async def get_transcript(
        self,
        group_id: str,
        include_system: bool = False,
    ) -> List[GroupMessage]:
        """Get the conversation transcript.

        獲取對話記錄。

        Args:
            group_id: 群組 ID
            include_system: 是否包含系統訊息

        Returns:
            訊息列表
        """
        state = await self.get_group_chat(group_id)
        if not state:
            return []

        messages = state.messages
        if not include_system:
            messages = [m for m in messages if m.message_type != MessageType.SYSTEM]

        return messages

    async def get_summary(
        self,
        group_id: str,
        summarizer: Optional[Callable[[List[GroupMessage]], str]] = None,
    ) -> Optional[str]:
        """Get a summary of the conversation.

        獲取對話摘要。

        Args:
            group_id: 群組 ID
            summarizer: 自定義摘要器（可選）

        Returns:
            對話摘要
        """
        state = await self.get_group_chat(group_id)
        if not state:
            return None

        if summarizer:
            return summarizer(state.messages)

        # Simple default summary
        return self._generate_simple_summary(state)

    # =========================================================================
    # Event Handling
    # =========================================================================

    def on_message(self, handler: Callable) -> None:
        """Register a message handler.

        Args:
            handler: 訊息處理函數
        """
        self._message_handlers.append(handler)

    def on_event(self, event_type: str, handler: Callable) -> None:
        """Register an event handler.

        Args:
            event_type: 事件類型
            handler: 事件處理函數
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    async def _emit_event(self, event_type: str, data: Any) -> None:
        """Emit an event to registered handlers."""
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Event handler error for {event_type}: {e}")

    # =========================================================================
    # Private Methods
    # =========================================================================

    async def _select_next_speaker(
        self,
        state: GroupChatState,
    ) -> Optional[AgentInfo]:
        """Select the next speaker based on the configured method.

        根據配置的方法選擇下一個發言者。
        """
        if self._speaker_selector:
            return await self._speaker_selector(state)

        active_agents = state.active_agents
        if not active_agents:
            return None

        method = state.config.speaker_selection_method
        last_speaker_id = state.current_speaker_id

        # Filter out last speaker if repeat not allowed
        if not state.config.allow_repeat_speaker and last_speaker_id:
            candidates = [a for a in active_agents if a.agent_id != last_speaker_id]
            if not candidates:
                candidates = active_agents  # Fallback if only one agent
        else:
            candidates = active_agents

        if method == SpeakerSelectionMethod.ROUND_ROBIN:
            return self._select_round_robin(state, candidates)
        elif method == SpeakerSelectionMethod.RANDOM:
            import random
            return random.choice(candidates)
        elif method == SpeakerSelectionMethod.PRIORITY:
            return min(candidates, key=lambda a: a.priority)
        elif method == SpeakerSelectionMethod.EXPERTISE:
            return await self._select_by_expertise(state, candidates)
        else:  # AUTO or default
            return await self._select_auto(state, candidates)

    def _select_round_robin(
        self,
        state: GroupChatState,
        candidates: List[AgentInfo],
    ) -> Optional[AgentInfo]:
        """Select speaker using round-robin.

        Uses the full agent list to maintain proper round-robin order,
        even when some agents are filtered from candidates.
        """
        if not candidates:
            return None

        if not state.current_speaker_id:
            return candidates[0]

        # Use the full agent list to determine order, not just candidates
        all_agents = state.agents
        candidate_ids = {a.agent_id for a in candidates}

        # Find current speaker's position in the full agent list
        try:
            current_idx = next(
                i for i, a in enumerate(all_agents)
                if a.agent_id == state.current_speaker_id
            )
        except StopIteration:
            # Current speaker not found, start from beginning
            return candidates[0]

        # Look for the next available candidate in round-robin order
        for offset in range(1, len(all_agents) + 1):
            next_idx = (current_idx + offset) % len(all_agents)
            next_agent = all_agents[next_idx]
            if next_agent.agent_id in candidate_ids:
                return next(a for a in candidates if a.agent_id == next_agent.agent_id)

        # Fallback to first candidate
        return candidates[0]

    async def _select_by_expertise(
        self,
        state: GroupChatState,
        candidates: List[AgentInfo],
    ) -> Optional[AgentInfo]:
        """Select speaker based on expertise matching."""
        if not candidates:
            return None

        # Get last message content for context
        last_message = state.messages[-1] if state.messages else None
        if not last_message:
            return candidates[0]

        # Simple keyword matching (can be enhanced with LLM)
        content_lower = last_message.content.lower()

        best_match = candidates[0]
        best_score = 0

        for agent in candidates:
            score = sum(
                1 for cap in agent.capabilities
                if cap.lower() in content_lower
            )
            if score > best_score:
                best_score = score
                best_match = agent

        return best_match

    async def _select_auto(
        self,
        state: GroupChatState,
        candidates: List[AgentInfo],
    ) -> Optional[AgentInfo]:
        """Select speaker using LLM-based selection."""
        if not candidates:
            return None

        # If no LLM client, fallback to round-robin
        if not self._llm_client:
            return self._select_round_robin(state, candidates)

        # Build selection prompt
        prompt = self._build_selection_prompt(state, candidates)

        try:
            response = await self._llm_client.complete(prompt)
            selected_id = self._parse_selection_response(response, candidates)
            return next(
                (a for a in candidates if a.agent_id == selected_id),
                candidates[0],
            )
        except Exception as e:
            logger.error(f"LLM selection failed: {e}")
            return self._select_round_robin(state, candidates)

    def _build_selection_prompt(
        self,
        state: GroupChatState,
        candidates: List[AgentInfo],
    ) -> str:
        """Build prompt for LLM speaker selection."""
        agents_desc = "\n".join([
            f"- {a.name} (ID: {a.agent_id}): {a.description}"
            for a in candidates
        ])

        recent_messages = "\n".join([
            f"{m.sender_name}: {m.content[:100]}..."
            if len(m.content) > 100 else f"{m.sender_name}: {m.content}"
            for m in state.messages[-5:]
        ])

        return f"""Based on the conversation context, select the most appropriate agent to speak next.

Available agents:
{agents_desc}

Recent conversation:
{recent_messages}

Respond with only the agent ID of the selected agent."""

    def _parse_selection_response(
        self,
        response: str,
        candidates: List[AgentInfo],
    ) -> str:
        """Parse LLM response to extract agent ID."""
        response = response.strip()

        # Check if response is a valid agent ID
        for agent in candidates:
            if agent.agent_id in response:
                return agent.agent_id
            if agent.name.lower() in response.lower():
                return agent.agent_id

        # Default to first candidate
        return candidates[0].agent_id if candidates else ""

    async def _build_context_for_agent(
        self,
        state: GroupChatState,
        agent: AgentInfo,
    ) -> str:
        """Build conversation context for an agent."""
        recent_messages = state.messages[-10:]

        context_parts = [
            f"You are {agent.name}. {agent.description}",
            f"\nGroup chat: {state.name}",
            f"Current round: {state.current_round}",
            f"\nRecent conversation:",
        ]

        for msg in recent_messages:
            context_parts.append(f"{msg.sender_name}: {msg.content}")

        context_parts.append("\nPlease provide your response:")

        return "\n".join(context_parts)

    async def _should_terminate(self, state: GroupChatState) -> bool:
        """Check if conversation should terminate."""
        if self._termination_checker:
            return await self._termination_checker(state)

        # Max rounds check
        if state.current_round > state.config.max_rounds:
            logger.info(f"Terminating group {state.group_id}: max rounds reached")
            return True

        # Timeout check
        if state.started_at:
            elapsed = (datetime.utcnow() - state.started_at).total_seconds()
            if elapsed > state.config.timeout_seconds:
                logger.info(f"Terminating group {state.group_id}: timeout")
                return True

        # Custom termination conditions
        conditions = state.config.termination_conditions

        # Keyword termination
        if "keywords" in conditions:
            last_message = state.messages[-1] if state.messages else None
            if last_message:
                for keyword in conditions["keywords"]:
                    if keyword.lower() in last_message.content.lower():
                        logger.info(f"Terminating group {state.group_id}: keyword '{keyword}' found")
                        return True

        return False

    async def _add_system_message(
        self,
        state: GroupChatState,
        content: str,
    ) -> GroupMessage:
        """Add a system message to the group."""
        message = GroupMessage(
            id=str(uuid.uuid4()),
            group_id=state.group_id,
            sender_id="system",
            sender_name="System",
            content=content,
            message_type=MessageType.SYSTEM,
            metadata={"round": state.current_round},
        )
        state.messages.append(message)
        return message

    def _generate_simple_summary(self, state: GroupChatState) -> str:
        """Generate a simple summary of the conversation."""
        total_messages = len(state.messages)
        agent_messages = [m for m in state.messages if m.message_type == MessageType.AGENT]
        user_messages = [m for m in state.messages if m.message_type == MessageType.USER]

        speakers = set(m.sender_name for m in state.messages if m.message_type != MessageType.SYSTEM)

        summary_parts = [
            f"Conversation Summary for '{state.name}'",
            f"- Status: {state.status.value}",
            f"- Duration: {state.current_round} rounds",
            f"- Total messages: {total_messages}",
            f"- Agent messages: {len(agent_messages)}",
            f"- User messages: {len(user_messages)}",
            f"- Participants: {', '.join(speakers)}",
        ]

        return "\n".join(summary_parts)
