"""
GroupChat Orchestrator - Sprint 16 (S16-3 & S16-4)

提供 GroupChat 編排器和管理者選擇相關的實現。

模組功能:
    S16-3: GroupChatOrchestratorExecutor 整合
    S16-4: ManagerSelectionRequest/Response 整合

此模組封裝了 Agent Framework 的群組對話編排功能，
提供統一的介面供 IPA 平台使用。

組件:
    1. ManagerSelectionRequest - 發言者選擇請求
    2. ManagerSelectionResponse - 發言者選擇響應
    3. GroupChatDirective - 編排指令
    4. OrchestratorState - 編排器狀態
    5. GroupChatOrchestrator - 群組對話編排器

使用範例:
    # 創建選擇請求
    request = ManagerSelectionRequest(
        task=task_message,
        participants={"agent1": "Research agent", "agent2": "Writer agent"},
        conversation=[msg1, msg2],
        round_index=0,
    )

    # 創建選擇響應
    response = ManagerSelectionResponse(
        selected_participant="agent1",
        instruction="Please research the topic",
    )

    # 使用編排器
    orchestrator = GroupChatOrchestrator(
        manager=selector_fn,
        participants={"agent1": "...", "agent2": "..."},
    )
    await orchestrator.run(task_message)

Author: IPA Platform Team
Sprint: 16 - GroupChatBuilder 重構
Created: 2025-12-05
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Union,
)
from uuid import uuid4
import logging
import asyncio
import time

from .groupchat import (
    GroupChatMessage,
    GroupChatTurn,
    GroupChatStatus,
    MessageRole,
    GroupChatParticipant,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Manager Selection Types (S16-4)
# =============================================================================


@dataclass
class ManagerSelectionRequest:
    """
    發言者選擇請求。

    對應 Agent Framework 的 ManagerSelectionRequest。
    包含編排器傳遞給管理者的所有上下文信息。

    Attributes:
        task: 原始用戶任務消息
        participants: 參與者名稱到描述的映射
        conversation: 完整對話歷史
        round_index: 已完成的選擇輪數
        metadata: 可選的附加元數據
    """
    task: GroupChatMessage
    participants: Dict[str, str]  # name -> description
    conversation: List[GroupChatMessage]
    round_index: int
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式（用於序列化）。"""
        return {
            "task": self.task.to_dict(),
            "participants": dict(self.participants),
            "conversation": [msg.to_dict() for msg in self.conversation],
            "round_index": self.round_index,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ManagerSelectionRequest":
        """從字典創建實例。"""
        return cls(
            task=GroupChatMessage.from_dict(data["task"]),
            participants=data["participants"],
            conversation=[
                GroupChatMessage.from_dict(msg) for msg in data.get("conversation", [])
            ],
            round_index=data.get("round_index", 0),
            metadata=data.get("metadata"),
        )


@dataclass
class ManagerSelectionResponse:
    """
    發言者選擇響應。

    對應 Agent Framework 的 ManagerSelectionResponse。
    管理者返回此結構來通知編排器下一步操作。

    Attributes:
        selected_participant: 選中的參與者名稱（None 表示結束對話）
        instruction: 給選中參與者的可選指示
        finish: 是否應該結束對話
        final_message: 結束時的最終消息文本
    """
    selected_participant: Optional[str] = None
    instruction: Optional[str] = None
    finish: bool = False
    final_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式。"""
        return {
            "selected_participant": self.selected_participant,
            "instruction": self.instruction,
            "finish": self.finish,
            "final_message": self.final_message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ManagerSelectionResponse":
        """從字典創建實例。"""
        return cls(
            selected_participant=data.get("selected_participant"),
            instruction=data.get("instruction"),
            finish=data.get("finish", False),
            final_message=data.get("final_message"),
        )

    def get_final_message_as_chat_message(
        self,
        author_name: str = "manager",
    ) -> Optional[GroupChatMessage]:
        """
        將 final_message 轉換為 ChatMessage。

        Args:
            author_name: 作者名稱

        Returns:
            ChatMessage 或 None
        """
        if self.final_message:
            return GroupChatMessage(
                role=MessageRole.ASSISTANT,
                content=self.final_message,
                author_name=author_name,
            )
        return None


# =============================================================================
# Group Chat Directive (S16-3)
# =============================================================================


@dataclass
class GroupChatDirective:
    """
    群組對話編排指令。

    對應 Agent Framework 的 GroupChatDirective。
    由管理者實現返回，指示編排器的下一步操作。

    Attributes:
        agent_name: 要選擇的參與者名稱（finish=False 時必需）
        instruction: 給選中參與者的可選指示
        metadata: 可選的附加元數據
        finish: 是否結束對話
        final_message: 結束時的最終消息
    """
    agent_name: Optional[str] = None
    instruction: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    finish: bool = False
    final_message: Optional[GroupChatMessage] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式。"""
        return {
            "agent_name": self.agent_name,
            "instruction": self.instruction,
            "metadata": self.metadata,
            "finish": self.finish,
            "final_message": self.final_message.to_dict() if self.final_message else None,
        }

    @classmethod
    def from_selection_response(
        cls,
        response: ManagerSelectionResponse,
        manager_name: str = "manager",
    ) -> "GroupChatDirective":
        """
        從 ManagerSelectionResponse 創建指令。

        Args:
            response: 選擇響應
            manager_name: 管理者名稱

        Returns:
            對應的 GroupChatDirective
        """
        final_message = None
        if response.final_message:
            final_message = GroupChatMessage(
                role=MessageRole.ASSISTANT,
                content=response.final_message,
                author_name=manager_name,
            )

        return cls(
            agent_name=response.selected_participant,
            instruction=response.instruction,
            finish=response.finish,
            final_message=final_message,
        )


# =============================================================================
# Orchestrator State (S16-3)
# =============================================================================


class OrchestratorPhase(str, Enum):
    """
    編排器階段枚舉。

    Values:
        IDLE: 空閒，等待輸入
        INITIALIZING: 正在初始化
        SELECTING: 正在選擇下一位發言者
        ROUTING: 正在路由消息到參與者
        WAITING_RESPONSE: 等待參與者響應
        PROCESSING_RESPONSE: 處理參與者響應
        COMPLETING: 正在完成對話
        COMPLETED: 已完成
        ERROR: 錯誤狀態
    """
    IDLE = "idle"
    INITIALIZING = "initializing"
    SELECTING = "selecting"
    ROUTING = "routing"
    WAITING_RESPONSE = "waiting_response"
    PROCESSING_RESPONSE = "processing_response"
    COMPLETING = "completing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class OrchestratorState:
    """
    編排器狀態快照。

    用於追蹤編排器的當前狀態，支持 checkpoint 和恢復。

    Attributes:
        phase: 當前階段
        conversation: 對話歷史
        history: 輪次記錄
        round_index: 當前輪數
        pending_agent: 等待響應的 Agent
        task_message: 原始任務消息
        participants: 參與者映射
        manager_name: 管理者名稱
        start_time: 開始時間
        metadata: 附加元數據
    """
    phase: OrchestratorPhase = OrchestratorPhase.IDLE
    conversation: List[GroupChatMessage] = field(default_factory=list)
    history: List[GroupChatTurn] = field(default_factory=list)
    round_index: int = 0
    pending_agent: Optional[str] = None
    task_message: Optional[GroupChatMessage] = None
    participants: Dict[str, str] = field(default_factory=dict)
    manager_name: str = "manager"
    start_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式（用於 checkpoint）。"""
        return {
            "phase": self.phase.value,
            "conversation": [msg.to_dict() for msg in self.conversation],
            "history": [turn.to_dict() for turn in self.history],
            "round_index": self.round_index,
            "pending_agent": self.pending_agent,
            "task_message": self.task_message.to_dict() if self.task_message else None,
            "participants": self.participants,
            "manager_name": self.manager_name,
            "start_time": self.start_time,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrchestratorState":
        """從字典恢復實例。"""
        task_message = None
        if data.get("task_message"):
            task_message = GroupChatMessage.from_dict(data["task_message"])

        return cls(
            phase=OrchestratorPhase(data.get("phase", "idle")),
            conversation=[
                GroupChatMessage.from_dict(msg) for msg in data.get("conversation", [])
            ],
            history=[],  # 簡化重建
            round_index=data.get("round_index", 0),
            pending_agent=data.get("pending_agent"),
            task_message=task_message,
            participants=data.get("participants", {}),
            manager_name=data.get("manager_name", "manager"),
            start_time=data.get("start_time"),
            metadata=data.get("metadata", {}),
        )


# =============================================================================
# Type Aliases
# =============================================================================

# 管理者函數類型（返回 GroupChatDirective）
ManagerFn = Callable[
    [Mapping[str, Any]],  # state snapshot
    Union[GroupChatDirective, Awaitable[GroupChatDirective]]
]

# 簡單選擇函數類型（返回參與者名稱）
SimpleSelectorFn = Callable[
    [Mapping[str, Any]],  # state snapshot
    Union[str, None, Awaitable[Union[str, None]]]
]


# =============================================================================
# GroupChatOrchestrator (S16-3)
# =============================================================================


class GroupChatOrchestrator:
    """
    群組對話編排器。

    對應 Agent Framework 的 GroupChatOrchestratorExecutor。
    負責管理群組對話的執行流程：
    1. 接收初始輸入
    2. 查詢管理者選擇下一位發言者
    3. 路由消息到選中的參與者
    4. 收集響應並更新對話狀態
    5. 重複步驟 2-4 直到管理者指示結束

    核心職責:
        - 維護對話歷史和輪次記錄
        - 委託管理者進行發言者選擇
        - 路由消息到參與者
        - 執行輪數限制
        - 執行終止條件
        - 支持 checkpoint 持久化

    Example:
        # 使用簡單選擇函數
        def round_robin_selector(state: Mapping[str, Any]) -> str:
            participants = list(state["participants"].keys())
            return participants[state["round_index"] % len(participants)]

        orchestrator = GroupChatOrchestrator(
            manager=round_robin_selector,
            participants={"agent1": "Researcher", "agent2": "Writer"},
            max_rounds=10,
        )

        # 執行對話
        result = await orchestrator.run("Write an article about AI")
    """

    def __init__(
        self,
        manager: Union[ManagerFn, SimpleSelectorFn],
        participants: Dict[str, str],
        manager_name: str = "manager",
        max_rounds: Optional[int] = None,
        termination_condition: Optional[Callable[[List[GroupChatMessage]], bool]] = None,
        executor_id: Optional[str] = None,
    ):
        """
        初始化編排器。

        Args:
            manager: 管理者函數（選擇下一位發言者）
            participants: 參與者名稱到描述的映射
            manager_name: 管理者顯示名稱
            max_rounds: 最大輪數限制（None 表示無限制）
            termination_condition: 自定義終止條件
            executor_id: 編排器 ID（自動生成如果未提供）
        """
        self._id = executor_id or f"groupchat_orchestrator_{uuid4().hex[:8]}"
        self._manager = manager
        self._participants = dict(participants)
        self._manager_name = manager_name
        self._max_rounds = max_rounds
        self._termination_condition = termination_condition

        # 狀態
        self._state = OrchestratorState(
            participants=self._participants,
            manager_name=manager_name,
        )

        # 參與者回調（用於模擬 Agent 響應）
        self._participant_callbacks: Dict[str, Callable] = {}

        logger.debug(f"GroupChatOrchestrator created: {self._id}")

    @property
    def id(self) -> str:
        """獲取編排器 ID。"""
        return self._id

    @property
    def state(self) -> OrchestratorState:
        """獲取當前狀態。"""
        return self._state

    @property
    def participants(self) -> Dict[str, str]:
        """獲取參與者映射。"""
        return self._participants.copy()

    def register_participant_callback(
        self,
        name: str,
        callback: Callable[[GroupChatMessage, List[GroupChatMessage]], Awaitable[GroupChatMessage]],
    ) -> None:
        """
        註冊參與者回調。

        Args:
            name: 參與者名稱
            callback: 回調函數，接收任務和對話歷史，返回響應消息
        """
        if name not in self._participants:
            raise ValueError(f"Unknown participant: {name}")
        self._participant_callbacks[name] = callback
        logger.debug(f"Registered callback for participant: {name}")

    def _build_state_snapshot(self) -> Dict[str, Any]:
        """
        構建狀態快照。

        Returns:
            不可變的狀態映射（傳遞給管理者）
        """
        if self._state.task_message is None:
            raise RuntimeError("Orchestrator not initialized with task message")

        return {
            "task": self._state.task_message.to_dict(),
            "participants": dict(self._participants),
            "conversation": [msg.to_dict() for msg in self._state.conversation],
            "history": [turn.to_dict() for turn in self._state.history],
            "pending_agent": self._state.pending_agent,
            "round_index": self._state.round_index,
        }

    async def _query_manager(self) -> GroupChatDirective:
        """
        查詢管理者選擇下一位發言者。

        Returns:
            管理者指令
        """
        state_snapshot = self._build_state_snapshot()

        try:
            result = self._manager(state_snapshot)
            if asyncio.iscoroutine(result):
                result = await result

            # 處理不同返回類型
            if isinstance(result, GroupChatDirective):
                return result
            elif isinstance(result, str):
                # 簡單選擇函數返回參與者名稱
                return GroupChatDirective(agent_name=result)
            elif result is None:
                # None 表示結束
                return GroupChatDirective(
                    finish=True,
                    final_message=GroupChatMessage(
                        role=MessageRole.ASSISTANT,
                        content="Conversation completed.",
                        author_name=self._manager_name,
                    ),
                )
            else:
                raise TypeError(f"Unexpected manager result type: {type(result)}")

        except Exception as e:
            logger.error(f"Manager query failed: {e}")
            return GroupChatDirective(
                finish=True,
                final_message=GroupChatMessage(
                    role=MessageRole.ASSISTANT,
                    content=f"Conversation ended due to error: {e}",
                    author_name=self._manager_name,
                ),
            )

    async def _route_to_participant(
        self,
        participant_name: str,
        instruction: Optional[str] = None,
    ) -> GroupChatMessage:
        """
        路由消息到參與者並獲取響應。

        Args:
            participant_name: 參與者名稱
            instruction: 可選的指示

        Returns:
            參與者的響應消息
        """
        if participant_name not in self._participants:
            raise ValueError(f"Unknown participant: {participant_name}")

        self._state.phase = OrchestratorPhase.ROUTING
        self._state.pending_agent = participant_name

        # 構建上下文
        conversation = list(self._state.conversation)
        if instruction:
            manager_message = GroupChatMessage(
                role=MessageRole.MANAGER,
                content=instruction,
                author_name=self._manager_name,
            )
            conversation.append(manager_message)
            self._state.conversation.append(manager_message)
            self._state.history.append(GroupChatTurn(
                speaker=self._manager_name,
                role="manager",
                message=manager_message,
                turn_index=len(self._state.history),
            ))

        # 調用參與者回調
        self._state.phase = OrchestratorPhase.WAITING_RESPONSE

        if participant_name in self._participant_callbacks:
            callback = self._participant_callbacks[participant_name]
            response = await callback(self._state.task_message, conversation)
        else:
            # 默認響應（模擬）
            response = GroupChatMessage(
                role=MessageRole.ASSISTANT,
                content=f"[{participant_name}] Response to task.",
                author_name=participant_name,
            )

        # 處理響應
        self._state.phase = OrchestratorPhase.PROCESSING_RESPONSE
        self._state.conversation.append(response)
        self._state.history.append(GroupChatTurn(
            speaker=participant_name,
            role="agent",
            message=response,
            turn_index=len(self._state.history),
        ))
        self._state.pending_agent = None
        self._state.round_index += 1

        return response

    def _check_round_limit(self) -> bool:
        """
        檢查是否達到輪數限制。

        Returns:
            True 如果達到限制
        """
        if self._max_rounds is None:
            return False
        return self._state.round_index >= self._max_rounds

    async def _check_termination(self) -> bool:
        """
        檢查終止條件。

        Returns:
            True 如果應該終止
        """
        if self._termination_condition is None:
            return False

        result = self._termination_condition(self._state.conversation)
        if asyncio.iscoroutine(result):
            result = await result
        return bool(result)

    async def run(
        self,
        input_data: Union[str, GroupChatMessage],
    ) -> Dict[str, Any]:
        """
        執行群組對話。

        Args:
            input_data: 輸入任務

        Returns:
            執行結果字典
        """
        self._state.phase = OrchestratorPhase.INITIALIZING
        self._state.start_time = time.time()

        # 標準化輸入
        if isinstance(input_data, str):
            task_message = GroupChatMessage(
                role=MessageRole.USER,
                content=input_data,
            )
        else:
            task_message = input_data

        # 初始化狀態
        self._state.task_message = task_message
        self._state.conversation = [task_message]
        self._state.history = [GroupChatTurn(
            speaker="user",
            role="user",
            message=task_message,
            turn_index=0,
        )]
        self._state.round_index = 0

        participants_involved = []

        try:
            # 主對話循環
            while True:
                # 檢查終止條件
                if await self._check_termination():
                    logger.info("Termination condition met")
                    break

                # 檢查輪數限制
                if self._check_round_limit():
                    logger.info(f"Round limit reached: {self._max_rounds}")
                    break

                # 查詢管理者
                self._state.phase = OrchestratorPhase.SELECTING
                directive = await self._query_manager()

                # 處理指令
                if directive.finish:
                    if directive.final_message:
                        self._state.conversation.append(directive.final_message)
                    break

                if not directive.agent_name:
                    logger.warning("Directive missing agent_name, ending conversation")
                    break

                if directive.agent_name not in self._participants:
                    logger.warning(f"Unknown participant selected: {directive.agent_name}")
                    break

                # 路由到參與者
                await self._route_to_participant(
                    directive.agent_name,
                    directive.instruction,
                )

                if directive.agent_name not in participants_involved:
                    participants_involved.append(directive.agent_name)

            self._state.phase = OrchestratorPhase.COMPLETED

        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            self._state.phase = OrchestratorPhase.ERROR
            raise

        duration = time.time() - self._state.start_time

        return {
            "conversation": self._state.conversation,
            "final_message": self._state.conversation[-1] if self._state.conversation else None,
            "round_index": self._state.round_index,
            "participants_involved": participants_involved,
            "duration": duration,
            "phase": self._state.phase.value,
        }

    async def run_stream(
        self,
        input_data: Union[str, GroupChatMessage],
    ):
        """
        以串流模式執行群組對話。

        Args:
            input_data: 輸入任務

        Yields:
            對話事件
        """
        # 初始化
        self._state.phase = OrchestratorPhase.INITIALIZING
        yield {"type": "started", "data": {"id": self._id}}

        result = await self.run(input_data)

        # 串流輸出消息
        for msg in result.get("conversation", []):
            yield {
                "type": "message",
                "data": msg.to_dict() if hasattr(msg, "to_dict") else msg,
            }

        yield {"type": "completed", "data": result}

    # Checkpoint 支持
    async def save_checkpoint(self) -> Dict[str, Any]:
        """
        保存 checkpoint。

        Returns:
            狀態字典
        """
        return self._state.to_dict()

    async def restore_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        """
        恢復 checkpoint。

        Args:
            checkpoint: 狀態字典
        """
        self._state = OrchestratorState.from_dict(checkpoint)
        logger.info(f"Restored checkpoint for orchestrator: {self._id}")


# =============================================================================
# Factory Functions
# =============================================================================


def create_orchestrator(
    participants: Dict[str, str],
    manager: Optional[Union[ManagerFn, SimpleSelectorFn]] = None,
    selection_method: str = "round_robin",
    max_rounds: Optional[int] = 10,
    **kwargs,
) -> GroupChatOrchestrator:
    """
    創建群組對話編排器。

    Args:
        participants: 參與者名稱到描述的映射
        manager: 自定義管理者函數
        selection_method: 選擇方法（如果未提供 manager）
        max_rounds: 最大輪數
        **kwargs: 其他配置

    Returns:
        配置好的編排器實例
    """
    if manager is None:
        # 創建默認選擇函數
        participant_names = list(participants.keys())

        if selection_method == "round_robin":
            def manager(state: Mapping[str, Any]) -> Optional[str]:
                idx = state.get("round_index", 0)
                return participant_names[idx % len(participant_names)]
        elif selection_method == "random":
            import random
            def manager(state: Mapping[str, Any]) -> Optional[str]:
                return random.choice(participant_names)
        else:
            def manager(state: Mapping[str, Any]) -> Optional[str]:
                idx = state.get("round_index", 0)
                return participant_names[idx % len(participant_names)]

    return GroupChatOrchestrator(
        manager=manager,
        participants=participants,
        max_rounds=max_rounds,
        **kwargs,
    )


def create_manager_selection_request(
    task: GroupChatMessage,
    participants: Dict[str, str],
    conversation: List[GroupChatMessage],
    round_index: int = 0,
    metadata: Optional[Dict[str, Any]] = None,
) -> ManagerSelectionRequest:
    """
    創建發言者選擇請求。

    Args:
        task: 任務消息
        participants: 參與者映射
        conversation: 對話歷史
        round_index: 輪數
        metadata: 附加元數據

    Returns:
        選擇請求實例
    """
    return ManagerSelectionRequest(
        task=task,
        participants=participants,
        conversation=conversation,
        round_index=round_index,
        metadata=metadata,
    )


def create_manager_selection_response(
    selected_participant: Optional[str] = None,
    instruction: Optional[str] = None,
    finish: bool = False,
    final_message: Optional[str] = None,
) -> ManagerSelectionResponse:
    """
    創建發言者選擇響應。

    Args:
        selected_participant: 選中的參與者
        instruction: 指示
        finish: 是否結束
        final_message: 最終消息

    Returns:
        選擇響應實例
    """
    return ManagerSelectionResponse(
        selected_participant=selected_participant,
        instruction=instruction,
        finish=finish,
        final_message=final_message,
    )
