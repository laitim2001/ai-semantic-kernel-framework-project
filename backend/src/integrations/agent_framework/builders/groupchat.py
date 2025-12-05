"""
GroupChatBuilder Adapter - Sprint 16

將 Agent Framework GroupChatBuilder API 封裝為 IPA 平台適配器。
支持多種發言者選擇方法和群組對話編排。

模組功能:
    1. GroupChatBuilderAdapter - GroupChatBuilder 適配器
    2. SpeakerSelectionMethod - 發言者選擇方法枚舉
    3. GroupChatParticipant - 參與者配置
    4. GroupChatState - 群組對話狀態
    5. GroupChatMessage - 群組消息
    6. GroupChatResult - 執行結果

API 映射:
    | IPA API | Agent Framework API |
    |---------|---------------------|
    | SpeakerSelectionMethod.AUTO | set_manager() |
    | SpeakerSelectionMethod.ROUND_ROBIN | set_select_speakers_func() |
    | SpeakerSelectionMethod.RANDOM | set_select_speakers_func() |
    | SpeakerSelectionMethod.MANUAL | set_select_speakers_func() |

使用範例:
    adapter = GroupChatBuilderAdapter(
        id="team-discussion",
        participants=[researcher, writer, reviewer],
        selection_method=SpeakerSelectionMethod.ROUND_ROBIN,
        max_rounds=10,
    )
    result = await adapter.run("Write a blog post about AI")

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

from ..base import BuilderAdapter
from ..exceptions import WorkflowBuildError, AdapterError

logger = logging.getLogger(__name__)


# =============================================================================
# Enumerations
# =============================================================================


class SpeakerSelectionMethod(str, Enum):
    """
    發言者選擇方法枚舉。

    定義群組對話中選擇下一位發言者的策略。

    Values:
        AUTO: 使用 LLM Agent 自動選擇（映射到 set_manager()）
        ROUND_ROBIN: 輪流發言（映射到 set_select_speakers_func()）
        RANDOM: 隨機選擇（映射到 set_select_speakers_func()）
        MANUAL: 手動指定（映射到 set_select_speakers_func()）
        CUSTOM: 自定義選擇函數（映射到 set_select_speakers_func()）
    """
    AUTO = "auto"
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    MANUAL = "manual"
    CUSTOM = "custom"


class GroupChatStatus(str, Enum):
    """
    群組對話狀態枚舉。

    Values:
        IDLE: 空閒，等待啟動
        RUNNING: 運行中
        WAITING: 等待發言者響應
        PAUSED: 暫停
        COMPLETED: 已完成
        FAILED: 失敗
        CANCELLED: 已取消
    """
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageRole(str, Enum):
    """
    消息角色枚舉。

    Values:
        USER: 用戶消息
        ASSISTANT: 助手/Agent 消息
        SYSTEM: 系統消息
        MANAGER: 管理者消息
    """
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    MANAGER = "manager"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class GroupChatParticipant:
    """
    群組對話參與者配置。

    Attributes:
        name: 參與者名稱（唯一識別符）
        description: 參與者描述（用於 LLM 選擇）
        agent: Agent 實例或 Executor 實例
        capabilities: 參與者能力列表
        metadata: 附加元數據
    """
    name: str
    description: str = ""
    agent: Any = None  # AgentProtocol | Executor
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.name:
            raise ValueError("Participant name cannot be empty")
        if not self.description and self.agent:
            # 嘗試從 agent 獲取描述
            self.description = getattr(self.agent, "description", "") or \
                              getattr(self.agent, "name", self.name)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式。"""
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "metadata": self.metadata,
        }


@dataclass
class GroupChatMessage:
    """
    群組對話消息。

    Attributes:
        role: 消息角色
        content: 消息內容
        author_name: 作者名稱（發言者）
        timestamp: 時間戳
        metadata: 附加元數據
    """
    role: MessageRole
    content: str
    author_name: Optional[str] = None
    timestamp: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.timestamp is None:
            import time
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式。"""
        return {
            "role": self.role.value,
            "content": self.content,
            "author_name": self.author_name,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GroupChatMessage":
        """從字典創建實例。"""
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            author_name=data.get("author_name"),
            timestamp=data.get("timestamp"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class GroupChatTurn:
    """
    群組對話輪次記錄。

    Attributes:
        speaker: 發言者名稱
        role: 發言者角色（user/agent/manager）
        message: 消息內容
        turn_index: 輪次索引
    """
    speaker: str
    role: str
    message: GroupChatMessage
    turn_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式。"""
        return {
            "speaker": self.speaker,
            "role": self.role,
            "message": self.message.to_dict(),
            "turn_index": self.turn_index,
        }


@dataclass
class GroupChatState:
    """
    群組對話狀態快照。

    對應 Agent Framework 的 GroupChatStateSnapshot。

    Attributes:
        task: 原始任務消息
        participants: 參與者名稱到描述的映射
        conversation: 完整對話歷史
        history: 輪次記錄（包含發言者歸屬）
        pending_agent: 當前等待響應的 Agent
        round_index: 已完成的選擇輪數
    """
    task: GroupChatMessage
    participants: Dict[str, str]  # name -> description
    conversation: List[GroupChatMessage] = field(default_factory=list)
    history: List[GroupChatTurn] = field(default_factory=list)
    pending_agent: Optional[str] = None
    round_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式（用於傳遞給選擇函數）。"""
        return {
            "task": self.task.to_dict(),
            "participants": dict(self.participants),
            "conversation": [msg.to_dict() for msg in self.conversation],
            "history": [turn.to_dict() for turn in self.history],
            "pending_agent": self.pending_agent,
            "round_index": self.round_index,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GroupChatState":
        """從字典創建實例。"""
        return cls(
            task=GroupChatMessage.from_dict(data["task"]),
            participants=data["participants"],
            conversation=[
                GroupChatMessage.from_dict(msg) for msg in data.get("conversation", [])
            ],
            history=[],  # 簡化重建
            pending_agent=data.get("pending_agent"),
            round_index=data.get("round_index", 0),
        )


@dataclass
class SpeakerSelectionResult:
    """
    發言者選擇結果。

    對應 Agent Framework 的 ManagerSelectionResponse。

    Attributes:
        selected_participant: 選中的參與者名稱（None 表示結束）
        instruction: 給選中參與者的指示
        finish: 是否結束對話
        final_message: 結束時的最終消息
        metadata: 附加元數據
    """
    selected_participant: Optional[str] = None
    instruction: Optional[str] = None
    finish: bool = False
    final_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式。"""
        return {
            "selected_participant": self.selected_participant,
            "instruction": self.instruction,
            "finish": self.finish,
            "final_message": self.final_message,
            "metadata": self.metadata,
        }


@dataclass
class GroupChatResult:
    """
    群組對話執行結果。

    Attributes:
        status: 結束狀態
        conversation: 完整對話歷史
        final_message: 最終消息
        total_rounds: 總輪數
        participants_involved: 參與的 Agent 列表
        duration: 執行時長（秒）
        metadata: 附加元數據
    """
    status: GroupChatStatus
    conversation: List[GroupChatMessage]
    final_message: Optional[GroupChatMessage] = None
    total_rounds: int = 0
    participants_involved: List[str] = field(default_factory=list)
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式。"""
        return {
            "status": self.status.value,
            "conversation": [msg.to_dict() for msg in self.conversation],
            "final_message": self.final_message.to_dict() if self.final_message else None,
            "total_rounds": self.total_rounds,
            "participants_involved": self.participants_involved,
            "duration": self.duration,
            "metadata": self.metadata,
        }


# =============================================================================
# Type Aliases
# =============================================================================

# 發言者選擇函數類型
SpeakerSelectorFn = Callable[
    [Dict[str, Any]],  # GroupChatStateSnapshot as dict
    Union[str, None, Awaitable[Union[str, None]]]
]

# 終止條件函數類型
TerminationConditionFn = Callable[
    [List[GroupChatMessage]],
    Union[bool, Awaitable[bool]]
]


# =============================================================================
# Built-in Speaker Selectors
# =============================================================================


def create_round_robin_selector(
    participant_names: List[str],
) -> SpeakerSelectorFn:
    """
    創建輪流選擇器。

    Args:
        participant_names: 參與者名稱列表

    Returns:
        輪流選擇函數
    """
    def selector(state: Dict[str, Any]) -> Optional[str]:
        history = state.get("history", [])
        round_index = state.get("round_index", 0)

        if not participant_names:
            return None

        # 輪流選擇
        index = round_index % len(participant_names)
        return participant_names[index]

    return selector


def create_random_selector(
    participant_names: List[str],
    seed: Optional[int] = None,
) -> SpeakerSelectorFn:
    """
    創建隨機選擇器。

    Args:
        participant_names: 參與者名稱列表
        seed: 隨機種子（用於可重現性）

    Returns:
        隨機選擇函數
    """
    import random
    rng = random.Random(seed)

    def selector(state: Dict[str, Any]) -> Optional[str]:
        if not participant_names:
            return None
        return rng.choice(participant_names)

    return selector


def create_last_speaker_different_selector(
    participant_names: List[str],
) -> SpeakerSelectorFn:
    """
    創建避免連續發言的選擇器。

    確保下一位發言者與上一位不同。

    Args:
        participant_names: 參與者名稱列表

    Returns:
        選擇函數
    """
    import random

    def selector(state: Dict[str, Any]) -> Optional[str]:
        if not participant_names:
            return None

        history = state.get("history", [])
        last_speaker = None
        if history:
            last_turn = history[-1]
            if isinstance(last_turn, dict):
                last_speaker = last_turn.get("speaker")
            else:
                last_speaker = getattr(last_turn, "speaker", None)

        # 過濾掉上一位發言者
        candidates = [p for p in participant_names if p != last_speaker]
        if not candidates:
            candidates = participant_names

        return random.choice(candidates)

    return selector


# =============================================================================
# GroupChatBuilderAdapter
# =============================================================================


class GroupChatBuilderAdapter(BuilderAdapter):
    """
    Agent Framework GroupChatBuilder 適配器。

    將 Agent Framework 的 GroupChatBuilder API 封裝為統一的適配器接口，
    支持多種發言者選擇方法和靈活的群組對話編排。

    特性:
        - 支持多種發言者選擇方法（AUTO、ROUND_ROBIN、RANDOM、MANUAL、CUSTOM）
        - 支持最大輪數限制
        - 支持自定義終止條件
        - 支持 Checkpoint 持久化
        - 事件系統支持

    API 映射:
        | IPA API | Agent Framework API |
        |---------|---------------------|
        | selection_method=AUTO | builder.set_manager(agent) |
        | selection_method=ROUND_ROBIN | builder.set_select_speakers_func(fn) |
        | max_rounds | builder.with_max_rounds(n) |
        | termination_condition | builder.with_termination_condition(fn) |
        | checkpoint_storage | builder.with_checkpointing(storage) |

    Example:
        # 使用輪流發言
        adapter = GroupChatBuilderAdapter(
            id="team-chat",
            participants=[
                GroupChatParticipant(name="researcher", agent=researcher_agent),
                GroupChatParticipant(name="writer", agent=writer_agent),
            ],
            selection_method=SpeakerSelectionMethod.ROUND_ROBIN,
            max_rounds=10,
        )
        result = await adapter.run("Write an article about AI")

        # 使用 LLM 自動選擇
        adapter = GroupChatBuilderAdapter(
            id="auto-chat",
            participants=[...],
            selection_method=SpeakerSelectionMethod.AUTO,
            manager_agent=coordinator_agent,
        )
    """

    def __init__(
        self,
        id: str,
        participants: List[GroupChatParticipant],
        selection_method: SpeakerSelectionMethod = SpeakerSelectionMethod.ROUND_ROBIN,
        manager_agent: Any = None,
        manager_name: str = "manager",
        custom_selector: Optional[SpeakerSelectorFn] = None,
        max_rounds: Optional[int] = None,
        termination_condition: Optional[TerminationConditionFn] = None,
        checkpoint_storage: Any = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化 GroupChatBuilderAdapter。

        Args:
            id: 適配器唯一識別符
            participants: 參與者列表
            selection_method: 發言者選擇方法
            manager_agent: 管理者 Agent（AUTO 模式必需）
            manager_name: 管理者顯示名稱
            custom_selector: 自定義選擇函數（CUSTOM 模式必需）
            max_rounds: 最大輪數限制
            termination_condition: 自定義終止條件
            checkpoint_storage: Checkpoint 存儲
            config: 額外配置

        Raises:
            ValueError: 參數無效時
        """
        super().__init__(config)

        # 驗證參數
        if not id:
            raise ValueError("Adapter ID cannot be empty")
        if not participants:
            raise ValueError("At least one participant is required")
        if selection_method == SpeakerSelectionMethod.AUTO and not manager_agent:
            raise ValueError("Manager agent is required for AUTO selection method")
        if selection_method == SpeakerSelectionMethod.CUSTOM and not custom_selector:
            raise ValueError("Custom selector is required for CUSTOM selection method")

        self._id = id
        self._participants = {p.name: p for p in participants}
        self._selection_method = selection_method
        self._manager_agent = manager_agent
        self._manager_name = manager_name
        self._custom_selector = custom_selector
        self._max_rounds = max_rounds
        self._termination_condition = termination_condition
        self._checkpoint_storage = checkpoint_storage

        # 運行時狀態
        self._status = GroupChatStatus.IDLE
        self._state: Optional[GroupChatState] = None
        self._events: List[Dict[str, Any]] = []

    @property
    def id(self) -> str:
        """獲取適配器 ID。"""
        return self._id

    @property
    def participants(self) -> Dict[str, GroupChatParticipant]:
        """獲取參與者映射。"""
        return self._participants.copy()

    @property
    def selection_method(self) -> SpeakerSelectionMethod:
        """獲取選擇方法。"""
        return self._selection_method

    @property
    def status(self) -> GroupChatStatus:
        """獲取當前狀態。"""
        return self._status

    @property
    def state(self) -> Optional[GroupChatState]:
        """獲取當前對話狀態。"""
        return self._state

    def add_participant(self, participant: GroupChatParticipant) -> None:
        """
        添加參與者。

        Args:
            participant: 參與者配置

        Raises:
            ValueError: 如果名稱已存在
        """
        if participant.name in self._participants:
            raise ValueError(f"Participant '{participant.name}' already exists")
        self._participants[participant.name] = participant
        self._logger.info(f"Added participant: {participant.name}")

    def remove_participant(self, name: str) -> bool:
        """
        移除參與者。

        Args:
            name: 參與者名稱

        Returns:
            是否成功移除
        """
        if name in self._participants:
            del self._participants[name]
            self._logger.info(f"Removed participant: {name}")
            return True
        return False

    def set_selection_method(
        self,
        method: SpeakerSelectionMethod,
        custom_selector: Optional[SpeakerSelectorFn] = None,
    ) -> None:
        """
        設置發言者選擇方法。

        Args:
            method: 選擇方法
            custom_selector: 自定義選擇函數（CUSTOM 模式必需）

        Raises:
            ValueError: 參數無效時
        """
        if method == SpeakerSelectionMethod.CUSTOM and not custom_selector:
            raise ValueError("Custom selector is required for CUSTOM method")
        self._selection_method = method
        if custom_selector:
            self._custom_selector = custom_selector
        self._logger.info(f"Selection method set to: {method.value}")

    def set_manager_agent(self, agent: Any, name: str = "manager") -> None:
        """
        設置管理者 Agent。

        Args:
            agent: 管理者 Agent 實例
            name: 管理者顯示名稱
        """
        self._manager_agent = agent
        self._manager_name = name
        self._logger.info(f"Manager agent set: {name}")

    def set_max_rounds(self, max_rounds: Optional[int]) -> None:
        """
        設置最大輪數。

        Args:
            max_rounds: 最大輪數（None 表示無限制）
        """
        self._max_rounds = max_rounds
        self._logger.info(f"Max rounds set to: {max_rounds}")

    def set_termination_condition(
        self,
        condition: TerminationConditionFn,
    ) -> None:
        """
        設置終止條件。

        Args:
            condition: 終止條件函數
        """
        self._termination_condition = condition
        self._logger.info("Termination condition set")

    def _get_speaker_selector(self) -> SpeakerSelectorFn:
        """
        獲取發言者選擇函數。

        Returns:
            選擇函數

        Raises:
            ValueError: 配置無效時
        """
        participant_names = list(self._participants.keys())

        if self._selection_method == SpeakerSelectionMethod.ROUND_ROBIN:
            return create_round_robin_selector(participant_names)
        elif self._selection_method == SpeakerSelectionMethod.RANDOM:
            return create_random_selector(participant_names)
        elif self._selection_method == SpeakerSelectionMethod.MANUAL:
            return create_last_speaker_different_selector(participant_names)
        elif self._selection_method == SpeakerSelectionMethod.CUSTOM:
            if not self._custom_selector:
                raise ValueError("Custom selector not configured")
            return self._custom_selector
        elif self._selection_method == SpeakerSelectionMethod.AUTO:
            # AUTO 模式使用 manager agent，這裡返回佔位函數
            async def auto_selector(state: Dict[str, Any]) -> Optional[str]:
                raise RuntimeError(
                    "AUTO selector should not be called directly. "
                    "Use set_manager() in Agent Framework."
                )
            return auto_selector
        else:
            raise ValueError(f"Unknown selection method: {self._selection_method}")

    def _wrap_selector_for_agent_framework(
        self,
        selector: SpeakerSelectorFn,
    ) -> Callable:
        """
        包裝選擇器以適配 Agent Framework API。

        Agent Framework 的 set_select_speakers_func 期望返回 GroupChatDirective。

        Args:
            selector: 原始選擇函數

        Returns:
            包裝後的函數
        """
        manager_name = self._manager_name
        max_rounds = self._max_rounds

        async def wrapped_selector(state_snapshot: Mapping[str, Any]):
            # 檢查輪數限制
            round_index = state_snapshot.get("round_index", 0)
            if max_rounds is not None and round_index >= max_rounds:
                # 返回結束指令
                return _create_finish_directive(
                    manager_name=manager_name,
                    reason="max_rounds_reached",
                )

            # 調用原始選擇器
            try:
                result = selector(dict(state_snapshot))
                if asyncio.iscoroutine(result):
                    result = await result

                if result is None:
                    # 選擇器返回 None 表示結束
                    return _create_finish_directive(
                        manager_name=manager_name,
                        reason="selector_finished",
                    )

                # 返回選擇指令
                return _create_selection_directive(
                    agent_name=result,
                )
            except Exception as e:
                logger.error(f"Selector error: {e}")
                return _create_finish_directive(
                    manager_name=manager_name,
                    reason=f"selector_error: {e}",
                )

        return wrapped_selector

    def build(self):
        """
        構建 GroupChat Workflow。

        Returns:
            構建完成的 Workflow 實例

        Raises:
            WorkflowBuildError: 構建失敗時
        """
        try:
            self._logger.info(f"Building GroupChat workflow: {self._id}")

            # 構建參與者描述映射
            participant_descriptions = {
                name: p.description for name, p in self._participants.items()
            }

            # 創建 mock workflow（實際環境會使用 Agent Framework）
            workflow = _MockGroupChatWorkflow(
                id=self._id,
                participants=self._participants,
                selection_method=self._selection_method,
                selector=self._get_speaker_selector(),
                manager_agent=self._manager_agent,
                manager_name=self._manager_name,
                max_rounds=self._max_rounds,
                termination_condition=self._termination_condition,
                checkpoint_storage=self._checkpoint_storage,
            )

            self._workflow = workflow
            self._built = True
            self._logger.info(f"GroupChat workflow built: {self._id}")
            return workflow

        except Exception as e:
            self._logger.error(f"Failed to build GroupChat workflow: {e}")
            raise WorkflowBuildError(f"Failed to build GroupChat workflow: {e}") from e

    async def run(self, input_data: Any) -> GroupChatResult:
        """
        執行群組對話。

        Args:
            input_data: 輸入任務（字符串或 GroupChatMessage）

        Returns:
            執行結果
        """
        import time
        start_time = time.time()

        await self.ensure_initialized()

        if not self._workflow:
            self.build()

        self._status = GroupChatStatus.RUNNING

        try:
            # 標準化輸入
            if isinstance(input_data, str):
                task_message = GroupChatMessage(
                    role=MessageRole.USER,
                    content=input_data,
                )
            elif isinstance(input_data, GroupChatMessage):
                task_message = input_data
            else:
                task_message = GroupChatMessage(
                    role=MessageRole.USER,
                    content=str(input_data),
                )

            # 初始化狀態
            self._state = GroupChatState(
                task=task_message,
                participants={
                    name: p.description for name, p in self._participants.items()
                },
                conversation=[task_message],
                history=[
                    GroupChatTurn(
                        speaker="user",
                        role="user",
                        message=task_message,
                        turn_index=0,
                    )
                ],
            )

            # 執行對話循環
            result = await self._workflow.run(task_message)

            self._status = GroupChatStatus.COMPLETED
            duration = time.time() - start_time

            return GroupChatResult(
                status=self._status,
                conversation=result.get("conversation", [task_message]),
                final_message=result.get("final_message"),
                total_rounds=result.get("round_index", 0),
                participants_involved=result.get("participants_involved", []),
                duration=duration,
            )

        except Exception as e:
            self._status = GroupChatStatus.FAILED
            self._logger.error(f"GroupChat execution failed: {e}")
            duration = time.time() - start_time

            return GroupChatResult(
                status=self._status,
                conversation=self._state.conversation if self._state else [],
                total_rounds=self._state.round_index if self._state else 0,
                duration=duration,
                metadata={"error": str(e)},
            )

    async def run_stream(self, input_data: Any):
        """
        以串流模式執行群組對話。

        Args:
            input_data: 輸入任務

        Yields:
            對話事件
        """
        await self.ensure_initialized()

        if not self._workflow:
            self.build()

        self._status = GroupChatStatus.RUNNING

        try:
            async for event in self._workflow.run_stream(input_data):
                self._events.append(event)
                yield event

            self._status = GroupChatStatus.COMPLETED

        except Exception as e:
            self._status = GroupChatStatus.FAILED
            self._logger.error(f"GroupChat stream execution failed: {e}")
            raise

    def get_events(self) -> List[Dict[str, Any]]:
        """獲取已記錄的事件。"""
        return self._events.copy()

    def clear_events(self) -> None:
        """清除已記錄的事件。"""
        self._events.clear()

    async def initialize(self) -> None:
        """初始化適配器。"""
        self._logger.debug(f"Initializing GroupChatBuilderAdapter: {self._id}")
        self._status = GroupChatStatus.IDLE
        self._initialized = True

    async def cleanup(self) -> None:
        """清理適配器資源。"""
        self._logger.debug(f"Cleaning up GroupChatBuilderAdapter: {self._id}")
        self._status = GroupChatStatus.IDLE
        self._state = None
        self._events.clear()
        await super().cleanup()


# =============================================================================
# Helper Functions
# =============================================================================


def _create_selection_directive(
    agent_name: str,
    instruction: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    創建選擇指令。

    對應 Agent Framework 的 GroupChatDirective。
    """
    return {
        "agent_name": agent_name,
        "instruction": instruction,
        "metadata": metadata,
        "finish": False,
        "final_message": None,
    }


def _create_finish_directive(
    manager_name: str,
    reason: str = "completed",
    final_message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    創建結束指令。

    對應 Agent Framework 的 GroupChatDirective(finish=True)。
    """
    return {
        "agent_name": None,
        "instruction": None,
        "metadata": {"reason": reason},
        "finish": True,
        "final_message": final_message or f"Conversation {reason}.",
    }


# =============================================================================
# Mock Workflow (for testing without Agent Framework)
# =============================================================================


class _MockGroupChatWorkflow:
    """
    Mock GroupChat Workflow 實現。

    用於測試和無 Agent Framework 環境。
    實際部署時應替換為真正的 Agent Framework Workflow。
    """

    def __init__(
        self,
        id: str,
        participants: Dict[str, GroupChatParticipant],
        selection_method: SpeakerSelectionMethod,
        selector: SpeakerSelectorFn,
        manager_agent: Any = None,
        manager_name: str = "manager",
        max_rounds: Optional[int] = None,
        termination_condition: Optional[TerminationConditionFn] = None,
        checkpoint_storage: Any = None,
    ):
        self._id = id
        self._participants = participants
        self._selection_method = selection_method
        self._selector = selector
        self._manager_agent = manager_agent
        self._manager_name = manager_name
        self._max_rounds = max_rounds
        self._termination_condition = termination_condition
        self._checkpoint_storage = checkpoint_storage

    async def run(self, task_message: GroupChatMessage) -> Dict[str, Any]:
        """執行對話。"""
        conversation = [task_message]
        history = []
        round_index = 0
        participants_involved = []

        state = {
            "task": task_message.to_dict(),
            "participants": {
                name: p.description for name, p in self._participants.items()
            },
            "conversation": [task_message.to_dict()],
            "history": [],
            "pending_agent": None,
            "round_index": 0,
        }

        while True:
            # 檢查輪數限制
            if self._max_rounds is not None and round_index >= self._max_rounds:
                logger.info(f"Max rounds reached: {self._max_rounds}")
                break

            # 檢查終止條件
            if self._termination_condition:
                should_terminate = self._termination_condition(conversation)
                if asyncio.iscoroutine(should_terminate):
                    should_terminate = await should_terminate
                if should_terminate:
                    logger.info("Termination condition met")
                    break

            # 選擇下一位發言者
            try:
                selected = self._selector(state)
                if asyncio.iscoroutine(selected):
                    selected = await selected
            except Exception as e:
                logger.error(f"Selector error: {e}")
                break

            if selected is None:
                logger.info("Selector returned None, ending conversation")
                break

            if selected not in self._participants:
                logger.warning(f"Selected unknown participant: {selected}")
                break

            # 模擬 Agent 響應
            participant = self._participants[selected]
            response_content = f"[{selected}] Response to: {task_message.content[:50]}..."

            response_message = GroupChatMessage(
                role=MessageRole.ASSISTANT,
                content=response_content,
                author_name=selected,
            )
            conversation.append(response_message)

            if selected not in participants_involved:
                participants_involved.append(selected)

            # 更新狀態
            round_index += 1
            state["conversation"].append(response_message.to_dict())
            state["round_index"] = round_index

            # 限制模擬輪數
            if round_index >= 3:
                break

        # 創建結束消息
        final_message = GroupChatMessage(
            role=MessageRole.ASSISTANT,
            content="Conversation completed.",
            author_name=self._manager_name,
        )
        conversation.append(final_message)

        return {
            "conversation": conversation,
            "final_message": final_message,
            "round_index": round_index,
            "participants_involved": participants_involved,
        }

    async def run_stream(self, task_message):
        """串流執行對話。"""
        result = await self.run(task_message)
        for msg in result.get("conversation", []):
            yield {
                "type": "message",
                "data": msg.to_dict() if hasattr(msg, "to_dict") else msg,
            }
        yield {
            "type": "completed",
            "data": result,
        }


# =============================================================================
# Factory Functions
# =============================================================================


def create_groupchat_adapter(
    id: str,
    participants: List[GroupChatParticipant],
    selection_method: SpeakerSelectionMethod = SpeakerSelectionMethod.ROUND_ROBIN,
    **kwargs,
) -> GroupChatBuilderAdapter:
    """
    創建 GroupChat 適配器的便捷工廠函數。

    Args:
        id: 適配器 ID
        participants: 參與者列表
        selection_method: 選擇方法
        **kwargs: 其他配置參數

    Returns:
        配置好的 GroupChatBuilderAdapter 實例
    """
    return GroupChatBuilderAdapter(
        id=id,
        participants=participants,
        selection_method=selection_method,
        **kwargs,
    )


def create_round_robin_chat(
    id: str,
    participants: List[GroupChatParticipant],
    max_rounds: Optional[int] = 10,
    **kwargs,
) -> GroupChatBuilderAdapter:
    """
    創建輪流發言的群組對話適配器。

    Args:
        id: 適配器 ID
        participants: 參與者列表
        max_rounds: 最大輪數
        **kwargs: 其他配置參數

    Returns:
        配置好的 GroupChatBuilderAdapter 實例
    """
    return GroupChatBuilderAdapter(
        id=id,
        participants=participants,
        selection_method=SpeakerSelectionMethod.ROUND_ROBIN,
        max_rounds=max_rounds,
        **kwargs,
    )


def create_auto_managed_chat(
    id: str,
    participants: List[GroupChatParticipant],
    manager_agent: Any,
    manager_name: str = "coordinator",
    max_rounds: Optional[int] = 15,
    **kwargs,
) -> GroupChatBuilderAdapter:
    """
    創建 LLM 自動管理的群組對話適配器。

    Args:
        id: 適配器 ID
        participants: 參與者列表
        manager_agent: 管理者 Agent
        manager_name: 管理者名稱
        max_rounds: 最大輪數
        **kwargs: 其他配置參數

    Returns:
        配置好的 GroupChatBuilderAdapter 實例
    """
    return GroupChatBuilderAdapter(
        id=id,
        participants=participants,
        selection_method=SpeakerSelectionMethod.AUTO,
        manager_agent=manager_agent,
        manager_name=manager_name,
        max_rounds=max_rounds,
        **kwargs,
    )


def create_custom_selector_chat(
    id: str,
    participants: List[GroupChatParticipant],
    selector: SpeakerSelectorFn,
    max_rounds: Optional[int] = None,
    **kwargs,
) -> GroupChatBuilderAdapter:
    """
    創建自定義選擇器的群組對話適配器。

    Args:
        id: 適配器 ID
        participants: 參與者列表
        selector: 自定義選擇函數
        max_rounds: 最大輪數
        **kwargs: 其他配置參數

    Returns:
        配置好的 GroupChatBuilderAdapter 實例
    """
    return GroupChatBuilderAdapter(
        id=id,
        participants=participants,
        selection_method=SpeakerSelectionMethod.CUSTOM,
        custom_selector=selector,
        max_rounds=max_rounds,
        **kwargs,
    )
