"""
GroupChatBuilder Adapter - Sprint 16/20

將 Agent Framework GroupChatBuilder API 封裝為 IPA 平台適配器。
支持多種發言者選擇方法和群組對話編排。

模組功能:
    1. GroupChatBuilderAdapter - GroupChatBuilder 適配器
    2. SpeakerSelectionMethod - 發言者選擇方法枚舉 (7 種策略)
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
    | SpeakerSelectionMethod.PRIORITY | set_select_speakers_func() |
    | SpeakerSelectionMethod.EXPERTISE | set_select_speakers_func() |

使用範例:
    adapter = GroupChatBuilderAdapter(
        id="team-discussion",
        participants=[researcher, writer, reviewer],
        selection_method=SpeakerSelectionMethod.ROUND_ROBIN,
        max_rounds=10,
    )
    result = await adapter.run("Write a blog post about AI")

    # Sprint 20: 使用優先級選擇
    adapter = GroupChatBuilderAdapter(
        id="priority-chat",
        participants=[senior_dev, junior_dev],
        selection_method=SpeakerSelectionMethod.PRIORITY,
    )

    # Sprint 20: 使用專業能力匹配
    adapter = GroupChatBuilderAdapter(
        id="expertise-chat",
        participants=[researcher, coder, tester],
        selection_method=SpeakerSelectionMethod.EXPERTISE,
    )

Author: IPA Platform Team
Sprint: 16 - GroupChatBuilder 重構
Sprint: 20 - S20-2 整合 SpeakerSelector (PRIORITY, EXPERTISE)
Created: 2025-12-05
Updated: 2025-12-06
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

# =============================================================================
# 官方 Agent Framework API 導入 (Sprint 19 整合)
# =============================================================================
from agent_framework import (
    GroupChatBuilder,
    GroupChatDirective,
    ManagerSelectionResponse,
)

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
        PRIORITY: 按優先級選擇（Sprint 20 整合）
        EXPERTISE: 按專業能力匹配選擇（Sprint 20 整合）
    """
    AUTO = "auto"
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    MANUAL = "manual"
    CUSTOM = "custom"
    PRIORITY = "priority"
    EXPERTISE = "expertise"


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
# Sprint 20: Termination Condition Factories (S20-3)
# =============================================================================


class TerminationType(str, Enum):
    """
    終止條件類型枚舉。

    Sprint 20 整合: 從 domain/orchestration/groupchat/termination.py 遷移

    Values:
        MAX_ROUNDS: 達到最大輪次
        MAX_MESSAGES: 達到最大訊息數
        TIMEOUT: 超時
        KEYWORD: 關鍵字觸發
        CONSENSUS: 達成共識
        CUSTOM: 自定義條件
        NO_PROGRESS: 無進展（相同回應重複）
    """
    MAX_ROUNDS = "max_rounds"
    MAX_MESSAGES = "max_messages"
    TIMEOUT = "timeout"
    KEYWORD = "keyword"
    CONSENSUS = "consensus"
    CUSTOM = "custom"
    NO_PROGRESS = "no_progress"


# 預設終止關鍵字（從 domain 層遷移）
DEFAULT_TERMINATION_KEYWORDS = [
    "TERMINATE",
    "DONE",
    "END CONVERSATION",
    "TASK COMPLETE",
    "完成",
    "結束",
]


def create_max_rounds_termination(
    max_rounds: int,
) -> TerminationConditionFn:
    """
    創建最大輪數終止條件。

    Sprint 20 整合: 從 domain 層遷移

    Args:
        max_rounds: 最大輪數

    Returns:
        終止條件函數
    """
    def condition(messages: List[GroupChatMessage]) -> bool:
        # 計算輪數（排除 user 消息）
        agent_messages = [m for m in messages if m.role != MessageRole.USER]
        return len(agent_messages) >= max_rounds

    return condition


def create_max_messages_termination(
    max_messages: int,
) -> TerminationConditionFn:
    """
    創建最大訊息數終止條件。

    Sprint 20 整合: 從 domain 層遷移

    Args:
        max_messages: 最大訊息數

    Returns:
        終止條件函數
    """
    def condition(messages: List[GroupChatMessage]) -> bool:
        return len(messages) >= max_messages

    return condition


def create_keyword_termination(
    keywords: Optional[List[str]] = None,
    case_sensitive: bool = False,
    check_last_n: int = 1,
) -> TerminationConditionFn:
    """
    創建關鍵字終止條件。

    Sprint 20 整合: 從 domain 層遷移

    Args:
        keywords: 終止關鍵字列表
        case_sensitive: 是否區分大小寫
        check_last_n: 檢查最後 N 條訊息

    Returns:
        終止條件函數
    """
    _keywords = keywords or DEFAULT_TERMINATION_KEYWORDS

    def condition(messages: List[GroupChatMessage]) -> bool:
        if not messages:
            return False

        messages_to_check = messages[-check_last_n:]

        for message in messages_to_check:
            content = message.content
            if not case_sensitive:
                content = content.lower()

            for keyword in _keywords:
                check_keyword = keyword if case_sensitive else keyword.lower()
                if check_keyword in content:
                    logger.debug(f"Termination keyword '{keyword}' found in message")
                    return True

        return False

    return condition


def create_timeout_termination(
    timeout_seconds: float,
    start_time: Optional[float] = None,
) -> TerminationConditionFn:
    """
    創建超時終止條件。

    Sprint 20 整合: 從 domain 層遷移

    Args:
        timeout_seconds: 超時秒數
        start_time: 開始時間戳（None 則使用第一條訊息時間）

    Returns:
        終止條件函數
    """
    import time

    _start_time = start_time or time.time()

    def condition(messages: List[GroupChatMessage]) -> bool:
        elapsed = time.time() - _start_time
        if elapsed > timeout_seconds:
            logger.debug(f"Timeout reached: {elapsed:.1f}s > {timeout_seconds}s")
            return True
        return False

    return condition


def create_consensus_termination(
    agreement_keyword: str = "agree",
    threshold: float = 0.8,
    check_last_n: int = 5,
) -> TerminationConditionFn:
    """
    創建共識終止條件。

    當超過指定比例的參與者在最近的訊息中表達同意時終止。

    Sprint 20 整合: 從 domain 層遷移

    Args:
        agreement_keyword: 同意關鍵字
        threshold: 達成共識的閾值（0-1）
        check_last_n: 檢查最後 N 條訊息

    Returns:
        終止條件函數
    """
    def condition(messages: List[GroupChatMessage]) -> bool:
        if not messages:
            return False

        # 獲取最後 N 條 Agent 訊息
        agent_messages = [
            m for m in messages[-check_last_n:]
            if m.role == MessageRole.ASSISTANT
        ]

        if not agent_messages:
            return False

        # 計算同意數
        agreement_count = sum(
            1 for m in agent_messages
            if agreement_keyword.lower() in m.content.lower()
        )

        # 獲取唯一參與者數
        unique_speakers = set(m.author_name for m in agent_messages if m.author_name)
        if not unique_speakers:
            return False

        agreement_ratio = agreement_count / len(unique_speakers)

        if agreement_ratio >= threshold:
            logger.debug(
                f"Consensus reached: {agreement_ratio:.1%} >= {threshold:.1%}"
            )
            return True

        return False

    return condition


def create_no_progress_termination(
    min_repeats: int = 3,
    check_last_n: int = 5,
) -> TerminationConditionFn:
    """
    創建無進展終止條件。

    當最近的訊息內容重複時終止。

    Sprint 20 整合: 從 domain 層遷移

    Args:
        min_repeats: 最小重複次數
        check_last_n: 檢查最後 N 條訊息

    Returns:
        終止條件函數
    """
    def condition(messages: List[GroupChatMessage]) -> bool:
        if len(messages) < min_repeats:
            return False

        # 獲取最後 N 條 Agent 訊息
        agent_messages = [
            m for m in messages[-check_last_n:]
            if m.role == MessageRole.ASSISTANT
        ]

        if len(agent_messages) < min_repeats:
            return False

        # 簡單檢查：內容完全相同
        contents = [m.content.strip().lower() for m in agent_messages]
        unique_contents = set(contents)

        if len(unique_contents) == 1 and len(contents) >= min_repeats:
            logger.debug(f"No progress detected: {min_repeats} similar messages")
            return True

        return False

    return condition


def create_combined_termination(
    *conditions: TerminationConditionFn,
    mode: str = "any",
) -> TerminationConditionFn:
    """
    創建組合終止條件。

    Sprint 20 新增

    Args:
        *conditions: 終止條件函數列表
        mode: "any" 任一滿足則終止, "all" 全部滿足才終止

    Returns:
        組合終止條件函數
    """
    def condition(messages: List[GroupChatMessage]) -> bool:
        if mode == "any":
            return any(cond(messages) for cond in conditions)
        elif mode == "all":
            return all(cond(messages) for cond in conditions)
        else:
            raise ValueError(f"Unknown mode: {mode}")

    return condition


# =============================================================================
# Sprint 20: Priority and Expertise Selectors (S20-2)
# =============================================================================


def create_priority_selector(
    participants: Dict[str, "GroupChatParticipant"],
) -> SpeakerSelectorFn:
    """
    創建優先級選擇器。

    根據參與者的優先級（metadata 中的 priority 字段）選擇。
    優先級數值越小，優先級越高。

    Sprint 20 整合: 從 domain/orchestration/groupchat/speaker_selector.py 遷移

    Args:
        participants: 參與者字典 {name: GroupChatParticipant}

    Returns:
        優先級選擇函數

    Example:
        participants = {
            "senior": GroupChatParticipant(
                name="senior", metadata={"priority": 1}
            ),
            "junior": GroupChatParticipant(
                name="junior", metadata={"priority": 2}
            ),
        }
        selector = create_priority_selector(participants)
    """
    def selector(state: Dict[str, Any]) -> Optional[str]:
        if not participants:
            return None

        history = state.get("history", [])
        last_speaker = None
        if history:
            last_turn = history[-1]
            if isinstance(last_turn, dict):
                last_speaker = last_turn.get("speaker")
            else:
                last_speaker = getattr(last_turn, "speaker", None)

        # 構建優先級列表
        priority_list = []
        for name, participant in participants.items():
            # 跳過上一位發言者（避免連續發言）
            if name == last_speaker:
                continue
            priority = participant.metadata.get("priority", 100)
            priority_list.append((name, priority))

        # 如果所有人都被過濾掉，則包含所有人
        if not priority_list:
            priority_list = [
                (name, p.metadata.get("priority", 100))
                for name, p in participants.items()
            ]

        # 按優先級排序（數值小的優先）
        priority_list.sort(key=lambda x: x[1])

        return priority_list[0][0] if priority_list else None

    return selector


def create_expertise_selector(
    participants: Dict[str, "GroupChatParticipant"],
    synonym_map: Optional[Dict[str, List[str]]] = None,
    min_score_threshold: float = 0.1,
) -> SpeakerSelectorFn:
    """
    創建專業能力匹配選擇器。

    根據訊息內容匹配最相關的專業 Agent。
    使用關鍵字匹配和同義詞擴展。

    Sprint 20 整合: 從 domain/orchestration/groupchat/speaker_selector.py 遷移
    保留 ExpertiseMatcher 的核心邏輯（同義詞表、匹配算法）。

    Args:
        participants: 參與者字典 {name: GroupChatParticipant}
        synonym_map: 自定義同義詞映射（可選）
        min_score_threshold: 最小匹配分數閾值

    Returns:
        專業能力匹配選擇函數

    Example:
        participants = {
            "coder": GroupChatParticipant(
                name="coder",
                capabilities=["coding", "debugging"]
            ),
            "tester": GroupChatParticipant(
                name="tester",
                capabilities=["testing", "qa"]
            ),
        }
        selector = create_expertise_selector(participants)
    """
    import re

    # 預定義的能力同義詞表（從 domain 層遷移）
    CAPABILITY_SYNONYMS = {
        "coding": ["programming", "development", "code", "implement", "build"],
        "debugging": ["debug", "fix", "troubleshoot", "investigate", "diagnose"],
        "testing": ["test", "qa", "quality", "verify", "validate"],
        "planning": ["plan", "schedule", "organize", "coordinate", "project"],
        "review": ["review", "feedback", "assess", "evaluate", "check"],
        "design": ["design", "architect", "structure", "blueprint", "model"],
        "documentation": ["document", "doc", "write", "describe", "explain"],
        "analysis": ["analyze", "analyse", "research", "study", "investigate"],
        "security": ["secure", "security", "protect", "auth", "permission"],
        "performance": ["optimize", "performance", "speed", "efficiency", "tune"],
    }

    # 合併自定義同義詞
    synonyms = {**CAPABILITY_SYNONYMS, **(synonym_map or {})}

    def calculate_relevance(
        capabilities: List[str],
        content_lower: str,
        content_words: set,
    ) -> tuple:
        """計算能力與內容的相關性分數。"""
        if not capabilities:
            return 0.0, []

        matched = []
        total_score = 0.0

        for cap in capabilities:
            cap_lower = cap.lower()
            cap_score = 0.0

            # 直接匹配（最高權重）
            if cap_lower in content_lower:
                cap_score = 1.0
                matched.append(cap)
            else:
                # 同義詞匹配
                cap_synonyms = synonyms.get(cap_lower, [cap_lower])
                for syn in cap_synonyms:
                    if syn in content_lower or syn in content_words:
                        cap_score = 0.7  # 同義詞匹配權重較低
                        matched.append(cap)
                        break

            total_score += cap_score

        # 正規化分數
        normalized_score = total_score / len(capabilities) if capabilities else 0
        return min(1.0, normalized_score), matched

    def selector(state: Dict[str, Any]) -> Optional[str]:
        if not participants:
            return None

        # 獲取最後一條訊息
        conversation = state.get("conversation", [])
        if not conversation:
            # 無訊息上下文，返回第一個參與者
            return list(participants.keys())[0]

        last_message = conversation[-1]
        if isinstance(last_message, dict):
            content = last_message.get("content", "")
        else:
            content = getattr(last_message, "content", "")

        if not content:
            return list(participants.keys())[0]

        content_lower = content.lower()
        content_words = set(re.findall(r'\w+', content_lower))

        # 計算每個參與者的匹配分數
        scores = []
        for name, participant in participants.items():
            score, matched = calculate_relevance(
                participant.capabilities,
                content_lower,
                content_words,
            )
            scores.append((name, score, matched))

        # 按分數排序
        scores.sort(key=lambda x: x[1], reverse=True)

        # 返回最高分（超過閾值）的參與者
        if scores and scores[0][1] >= min_score_threshold:
            logger.debug(
                f"Expertise match: {scores[0][0]} "
                f"(score: {scores[0][1]:.2f}, matched: {scores[0][2]})"
            )
            return scores[0][0]

        # 分數不足，返回第一個參與者
        return list(participants.keys())[0]

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

        # Sprint 19: 使用官方 GroupChatBuilder API
        self._builder = GroupChatBuilder()

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

        Sprint 20 更新: 添加 PRIORITY 和 EXPERTISE 選擇方法支持。

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
        # Sprint 20: 新增 PRIORITY 和 EXPERTISE 選擇方法
        elif self._selection_method == SpeakerSelectionMethod.PRIORITY:
            return create_priority_selector(self._participants)
        elif self._selection_method == SpeakerSelectionMethod.EXPERTISE:
            return create_expertise_selector(self._participants)
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

        使用官方 Agent Framework GroupChatBuilder API 構建工作流。

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

            # Sprint 19: 使用官方 GroupChatBuilder API 構建工作流
            # 將 IPA 平台參與者轉換為官方 API 格式
            participants = [p.agent for p in self._participants.values() if p.agent]

            try:
                # 調用官方 GroupChatBuilder.participants().build()
                workflow = (
                    self._builder
                    .participants(participants)
                    .build()
                )
                self._workflow = workflow
                self._built = True
                self._logger.info(f"Official GroupChatBuilder workflow created: {self._id}")
                return workflow
            except Exception as e:
                # 如果官方 API 失敗，記錄警告並回退到 Mock 實現
                self._logger.warning(
                    f"Official GroupChatBuilder.build() failed: {e}. "
                    f"Falling back to IPA platform implementation."
                )

            # 回退: 創建 mock workflow
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
            self._logger.info(f"GroupChat workflow built (fallback): {self._id}")
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


# =============================================================================
# Sprint 20: Priority and Expertise Factory Functions
# =============================================================================


def create_priority_chat(
    id: str,
    participants: List[GroupChatParticipant],
    max_rounds: Optional[int] = 10,
    **kwargs,
) -> GroupChatBuilderAdapter:
    """
    創建優先級選擇的群組對話適配器。

    Sprint 20 新增: 從 domain 層遷移的優先級選擇功能。

    根據參與者的優先級（metadata.priority）選擇發言者。
    優先級數值越小，優先級越高。

    Args:
        id: 適配器 ID
        participants: 參與者列表（需設置 metadata.priority）
        max_rounds: 最大輪數
        **kwargs: 其他配置參數

    Returns:
        配置好的 GroupChatBuilderAdapter 實例

    Example:
        adapter = create_priority_chat(
            id="priority-discussion",
            participants=[
                GroupChatParticipant(
                    name="senior",
                    description="Senior Developer",
                    metadata={"priority": 1},
                ),
                GroupChatParticipant(
                    name="junior",
                    description="Junior Developer",
                    metadata={"priority": 2},
                ),
            ],
        )
    """
    return GroupChatBuilderAdapter(
        id=id,
        participants=participants,
        selection_method=SpeakerSelectionMethod.PRIORITY,
        max_rounds=max_rounds,
        **kwargs,
    )


def create_expertise_chat(
    id: str,
    participants: List[GroupChatParticipant],
    max_rounds: Optional[int] = 15,
    **kwargs,
) -> GroupChatBuilderAdapter:
    """
    創建專業能力匹配的群組對話適配器。

    Sprint 20 新增: 從 domain 層遷移的專業能力匹配功能。

    根據訊息內容匹配最相關的專業 Agent。
    使用關鍵字匹配和同義詞擴展。

    Args:
        id: 適配器 ID
        participants: 參與者列表（需設置 capabilities）
        max_rounds: 最大輪數
        **kwargs: 其他配置參數

    Returns:
        配置好的 GroupChatBuilderAdapter 實例

    Example:
        adapter = create_expertise_chat(
            id="expertise-discussion",
            participants=[
                GroupChatParticipant(
                    name="coder",
                    description="Software Developer",
                    capabilities=["coding", "debugging"],
                ),
                GroupChatParticipant(
                    name="tester",
                    description="QA Engineer",
                    capabilities=["testing", "qa"],
                ),
                GroupChatParticipant(
                    name="designer",
                    description="UX Designer",
                    capabilities=["design", "analysis"],
                ),
            ],
        )
    """
    return GroupChatBuilderAdapter(
        id=id,
        participants=participants,
        selection_method=SpeakerSelectionMethod.EXPERTISE,
        max_rounds=max_rounds,
        **kwargs,
    )
