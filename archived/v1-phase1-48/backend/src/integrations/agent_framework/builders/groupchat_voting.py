"""
GroupChatVotingAdapter - Sprint 20 (S20-4)

GroupChatBuilderAdapter 的投票擴展，提供投票增強的發言者選擇功能。

模組功能:
    1. GroupChatVotingAdapter - 投票增強的群組對話適配器
    2. VotingMethod - 投票方法枚舉
    3. VotingConfig - 投票配置
    4. create_voting_chat() - 工廠函數

Sprint 20 整合: 從 domain/orchestration/groupchat/voting.py 遷移核心邏輯。
保留 VotingManager 的主要功能並整合到適配器架構中。

使用範例:
    # 使用多數投票選擇發言者
    adapter = GroupChatVotingAdapter(
        id="voting-chat",
        participants=[agent1, agent2, agent3],
        voting_method=VotingMethod.MAJORITY,
    )

    # 使用一致通過
    adapter = create_voting_chat(
        id="unanimous-chat",
        participants=[...],
        voting_method=VotingMethod.UNANIMOUS,
    )

Author: IPA Platform Team
Sprint: 20 - S20-4 投票系統擴展
Created: 2025-12-06
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
)
from uuid import uuid4
import logging

from .groupchat import (
    GroupChatBuilderAdapter,
    GroupChatParticipant,
    GroupChatMessage,
    GroupChatResult,
    GroupChatStatus,
    SpeakerSelectionMethod,
    MessageRole,
    SpeakerSelectorFn,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Enumerations
# =============================================================================


class VotingMethod(str, Enum):
    """
    投票方法枚舉。

    Sprint 20 整合: 從 domain 層遷移並簡化

    Values:
        MAJORITY: 多數投票（超過 50% 的參與者同意）
        UNANIMOUS: 一致通過（所有參與者同意）
        RANKED: 排序投票（Borda 計數）
        WEIGHTED: 加權投票（根據參與者權重）
        APPROVAL: 贊成票計數（選擇票數最高的）
    """
    MAJORITY = "majority"
    UNANIMOUS = "unanimous"
    RANKED = "ranked"
    WEIGHTED = "weighted"
    APPROVAL = "approval"


class VotingStatus(str, Enum):
    """
    投票狀態枚舉。
    """
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class VotingConfig:
    """
    投票配置。

    Attributes:
        method: 投票方法
        threshold: 通過門檻（0-1，MAJORITY 模式使用）
        require_all: 是否需要所有人投票
        timeout_seconds: 投票超時（秒）
        allow_abstain: 是否允許棄權
    """
    method: VotingMethod = VotingMethod.MAJORITY
    threshold: float = 0.5
    require_all: bool = False
    timeout_seconds: Optional[float] = None
    allow_abstain: bool = True


@dataclass
class Vote:
    """
    單次投票記錄。

    Attributes:
        voter_name: 投票者名稱
        choice: 選擇（候選人名稱或排序列表）
        weight: 投票權重
        reason: 投票理由
    """
    voter_name: str
    choice: Any
    weight: float = 1.0
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "voter_name": self.voter_name,
            "choice": self.choice,
            "weight": self.weight,
            "reason": self.reason,
        }


@dataclass
class VotingResult:
    """
    投票結果。

    Attributes:
        winner: 勝出者名稱
        status: 投票狀態
        votes: 投票記錄
        tallies: 計票結果
        participation_rate: 參與率
    """
    winner: Optional[str] = None
    status: VotingStatus = VotingStatus.PENDING
    votes: List[Vote] = field(default_factory=list)
    tallies: Dict[str, float] = field(default_factory=dict)
    participation_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "winner": self.winner,
            "status": self.status.value,
            "votes": [v.to_dict() for v in self.votes],
            "tallies": self.tallies,
            "participation_rate": self.participation_rate,
        }


# =============================================================================
# Voting Selector Factories
# =============================================================================


def create_voting_selector(
    participants: Dict[str, GroupChatParticipant],
    voting_config: VotingConfig,
) -> SpeakerSelectorFn:
    """
    創建投票選擇器。

    根據投票配置選擇適當的投票方法。

    Args:
        participants: 參與者字典
        voting_config: 投票配置

    Returns:
        投票選擇函數
    """
    if voting_config.method == VotingMethod.MAJORITY:
        return create_majority_selector(participants, voting_config.threshold)
    elif voting_config.method == VotingMethod.UNANIMOUS:
        return create_unanimous_selector(participants)
    elif voting_config.method == VotingMethod.RANKED:
        return create_ranked_selector(participants)
    elif voting_config.method == VotingMethod.WEIGHTED:
        return create_weighted_selector(participants)
    elif voting_config.method == VotingMethod.APPROVAL:
        return create_approval_selector(participants)
    else:
        raise ValueError(f"Unknown voting method: {voting_config.method}")


def create_majority_selector(
    participants: Dict[str, GroupChatParticipant],
    threshold: float = 0.5,
) -> SpeakerSelectorFn:
    """
    創建多數投票選擇器。

    選擇獲得超過 threshold 比例投票的候選人。

    Args:
        participants: 參與者字典
        threshold: 通過門檻

    Returns:
        多數投票選擇函數
    """
    def selector(state: Dict[str, Any]) -> Optional[str]:
        if not participants:
            return None

        # 從對話歷史中提取投票意向
        conversation = state.get("conversation", [])
        candidates = list(participants.keys())

        # 統計投票
        votes: Dict[str, int] = {name: 0 for name in candidates}
        total_votes = 0

        for msg in conversation:
            content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            author = msg.get("author_name") if isinstance(msg, dict) else getattr(msg, "author_name", None)

            # 檢查消息中是否包含對候選人的支持
            for candidate in candidates:
                if candidate != author:  # 不能投給自己
                    if candidate.lower() in content.lower():
                        votes[candidate] += 1
                        total_votes += 1
                        break

        if total_votes == 0:
            return list(participants.keys())[0]

        # 找出獲得最多票的候選人
        max_votes = max(votes.values())
        winners = [name for name, count in votes.items() if count == max_votes]

        # 檢查是否達到門檻
        if max_votes / total_votes >= threshold:
            return winners[0]

        # 未達門檻，返回第一個參與者
        return list(participants.keys())[0]

    return selector


def create_unanimous_selector(
    participants: Dict[str, GroupChatParticipant],
) -> SpeakerSelectorFn:
    """
    創建一致通過選擇器。

    只有當所有參與者都同意時才選擇。

    Args:
        participants: 參與者字典

    Returns:
        一致通過選擇函數
    """
    def selector(state: Dict[str, Any]) -> Optional[str]:
        if not participants:
            return None

        conversation = state.get("conversation", [])
        candidates = list(participants.keys())

        # 統計每個候選人的支持者
        support: Dict[str, Set[str]] = {name: set() for name in candidates}

        for msg in conversation:
            content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            author = msg.get("author_name") if isinstance(msg, dict) else getattr(msg, "author_name", None)

            if not author:
                continue

            for candidate in candidates:
                if candidate != author and candidate.lower() in content.lower():
                    support[candidate].add(author)
                    break

        # 檢查是否有候選人獲得所有人支持
        all_voters = set(participants.keys())
        for candidate, supporters in support.items():
            # 扣除候選人自己（不能投給自己）
            required_voters = all_voters - {candidate}
            if supporters >= required_voters:
                return candidate

        # 無一致通過，返回第一個參與者
        return list(participants.keys())[0]

    return selector


def create_ranked_selector(
    participants: Dict[str, GroupChatParticipant],
) -> SpeakerSelectorFn:
    """
    創建排序投票選擇器（Borda 計數）。

    根據排序計算分數，分數最高者勝出。

    Args:
        participants: 參與者字典

    Returns:
        排序投票選擇函數
    """
    def selector(state: Dict[str, Any]) -> Optional[str]:
        if not participants:
            return None

        candidates = list(participants.keys())
        n_candidates = len(candidates)

        # 初始化分數
        scores: Dict[str, float] = {name: 0.0 for name in candidates}

        # 從對話歷史中分析優先順序
        conversation = state.get("conversation", [])

        for msg in conversation:
            content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            author = msg.get("author_name") if isinstance(msg, dict) else getattr(msg, "author_name", None)

            if not author:
                continue

            # 根據提及順序分配分數
            mentioned = []
            content_lower = content.lower()
            for candidate in candidates:
                if candidate != author and candidate.lower() in content_lower:
                    idx = content_lower.find(candidate.lower())
                    mentioned.append((candidate, idx))

            # 按出現順序排序
            mentioned.sort(key=lambda x: x[1])

            # Borda 計數：越早提及越多分
            for rank, (candidate, _) in enumerate(mentioned):
                points = n_candidates - rank
                scores[candidate] += points

        # 返回分數最高的候選人
        if any(scores.values()):
            return max(scores.items(), key=lambda x: x[1])[0]

        return list(participants.keys())[0]

    return selector


def create_weighted_selector(
    participants: Dict[str, GroupChatParticipant],
) -> SpeakerSelectorFn:
    """
    創建加權投票選擇器。

    根據參與者的權重（metadata.weight）計算投票結果。

    Args:
        participants: 參與者字典

    Returns:
        加權投票選擇函數
    """
    def selector(state: Dict[str, Any]) -> Optional[str]:
        if not participants:
            return None

        candidates = list(participants.keys())

        # 初始化加權分數
        weighted_votes: Dict[str, float] = {name: 0.0 for name in candidates}

        conversation = state.get("conversation", [])

        for msg in conversation:
            content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            author = msg.get("author_name") if isinstance(msg, dict) else getattr(msg, "author_name", None)

            if not author or author not in participants:
                continue

            # 獲取投票者的權重
            voter_weight = participants[author].metadata.get("weight", 1.0)

            # 檢查投票
            for candidate in candidates:
                if candidate != author and candidate.lower() in content.lower():
                    weighted_votes[candidate] += voter_weight
                    break

        # 返回加權票數最高的候選人
        if any(weighted_votes.values()):
            return max(weighted_votes.items(), key=lambda x: x[1])[0]

        return list(participants.keys())[0]

    return selector


def create_approval_selector(
    participants: Dict[str, GroupChatParticipant],
) -> SpeakerSelectorFn:
    """
    創建贊成票選擇器。

    計算每個候選人獲得的贊成票數，最高者勝出。

    Args:
        participants: 參與者字典

    Returns:
        贊成票選擇函數
    """
    def selector(state: Dict[str, Any]) -> Optional[str]:
        if not participants:
            return None

        candidates = list(participants.keys())

        # 統計贊成票
        approvals: Dict[str, int] = {name: 0 for name in candidates}

        conversation = state.get("conversation", [])

        # 贊成關鍵字
        approval_keywords = ["agree", "support", "approve", "yes", "同意", "贊成", "支持"]

        for msg in conversation:
            content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            author = msg.get("author_name") if isinstance(msg, dict) else getattr(msg, "author_name", None)

            if not author:
                continue

            content_lower = content.lower()

            # 檢查是否有贊成表示
            has_approval = any(kw in content_lower for kw in approval_keywords)
            if not has_approval:
                continue

            # 檢查贊成哪個候選人
            for candidate in candidates:
                if candidate != author and candidate.lower() in content_lower:
                    approvals[candidate] += 1
                    break

        # 返回贊成票最多的候選人
        if any(approvals.values()):
            return max(approvals.items(), key=lambda x: x[1])[0]

        return list(participants.keys())[0]

    return selector


# =============================================================================
# GroupChatVotingAdapter
# =============================================================================


class GroupChatVotingAdapter(GroupChatBuilderAdapter):
    """
    投票增強的群組對話適配器。

    擴展 GroupChatBuilderAdapter，添加投票功能來選擇發言者。

    Sprint 20 整合: 從 domain/orchestration/groupchat/voting.py 遷移

    特性:
        - 支持多種投票方法（MAJORITY, UNANIMOUS, RANKED, WEIGHTED, APPROVAL）
        - 投票結果追蹤
        - 與基礎適配器功能兼容

    Example:
        adapter = GroupChatVotingAdapter(
            id="voting-chat",
            participants=[agent1, agent2, agent3],
            voting_method=VotingMethod.MAJORITY,
            voting_threshold=0.6,
        )
        result = await adapter.run("Discuss the best approach")
    """

    def __init__(
        self,
        id: str,
        participants: List[GroupChatParticipant],
        voting_method: VotingMethod = VotingMethod.MAJORITY,
        voting_threshold: float = 0.5,
        voting_config: Optional[VotingConfig] = None,
        max_rounds: Optional[int] = None,
        **kwargs,
    ):
        """
        初始化 GroupChatVotingAdapter。

        Args:
            id: 適配器唯一識別符
            participants: 參與者列表
            voting_method: 投票方法
            voting_threshold: 投票通過門檻
            voting_config: 完整投票配置（覆蓋 method 和 threshold）
            max_rounds: 最大輪數限制
            **kwargs: 傳遞給基類的其他參數
        """
        # 先創建投票配置
        if voting_config:
            self._voting_config = voting_config
        else:
            self._voting_config = VotingConfig(
                method=voting_method,
                threshold=voting_threshold,
            )

        # 創建參與者字典（需要在調用基類之前）
        _participant_dict = {p.name: p for p in participants}

        # 創建投票選擇器
        voting_selector = create_voting_selector(
            _participant_dict,
            self._voting_config,
        )

        # 使用 CUSTOM 選擇方法，傳遞投票選擇器
        super().__init__(
            id=id,
            participants=participants,
            selection_method=SpeakerSelectionMethod.CUSTOM,
            custom_selector=voting_selector,
            max_rounds=max_rounds,
            **kwargs,
        )

        # 投票記錄
        self._voting_results: List[VotingResult] = []

        self._logger.info(
            f"GroupChatVotingAdapter initialized: {id} "
            f"(method={self._voting_config.method.value})"
        )

    @property
    def voting_config(self) -> VotingConfig:
        """獲取投票配置。"""
        return self._voting_config

    @property
    def voting_results(self) -> List[VotingResult]:
        """獲取投票結果歷史。"""
        return self._voting_results.copy()

    def with_voting(
        self,
        method: Optional[VotingMethod] = None,
        threshold: Optional[float] = None,
    ) -> "GroupChatVotingAdapter":
        """
        更新投票配置。

        Args:
            method: 新的投票方法
            threshold: 新的通過門檻

        Returns:
            self，支持鏈式調用
        """
        if method:
            self._voting_config.method = method
        if threshold is not None:
            self._voting_config.threshold = threshold

        # 重新創建選擇器
        self._custom_selector = create_voting_selector(
            self._participants,
            self._voting_config,
        )

        self._logger.info(
            f"Voting config updated: method={self._voting_config.method.value}, "
            f"threshold={self._voting_config.threshold}"
        )

        return self

    def clear_voting_history(self) -> None:
        """清除投票歷史。"""
        self._voting_results.clear()
        self._logger.debug("Voting history cleared")


# =============================================================================
# Factory Functions
# =============================================================================


def create_voting_chat(
    id: str,
    participants: List[GroupChatParticipant],
    voting_method: VotingMethod = VotingMethod.MAJORITY,
    voting_threshold: float = 0.5,
    max_rounds: Optional[int] = 10,
    **kwargs,
) -> GroupChatVotingAdapter:
    """
    創建投票群組對話適配器的便捷工廠函數。

    Args:
        id: 適配器 ID
        participants: 參與者列表
        voting_method: 投票方法
        voting_threshold: 投票通過門檻
        max_rounds: 最大輪數
        **kwargs: 其他配置參數

    Returns:
        配置好的 GroupChatVotingAdapter 實例
    """
    return GroupChatVotingAdapter(
        id=id,
        participants=participants,
        voting_method=voting_method,
        voting_threshold=voting_threshold,
        max_rounds=max_rounds,
        **kwargs,
    )


def create_majority_voting_chat(
    id: str,
    participants: List[GroupChatParticipant],
    threshold: float = 0.5,
    max_rounds: Optional[int] = 10,
    **kwargs,
) -> GroupChatVotingAdapter:
    """
    創建多數投票群組對話適配器。

    Args:
        id: 適配器 ID
        participants: 參與者列表
        threshold: 通過門檻（0-1）
        max_rounds: 最大輪數
        **kwargs: 其他配置參數

    Returns:
        配置好的 GroupChatVotingAdapter 實例
    """
    return GroupChatVotingAdapter(
        id=id,
        participants=participants,
        voting_method=VotingMethod.MAJORITY,
        voting_threshold=threshold,
        max_rounds=max_rounds,
        **kwargs,
    )


def create_unanimous_voting_chat(
    id: str,
    participants: List[GroupChatParticipant],
    max_rounds: Optional[int] = 15,
    **kwargs,
) -> GroupChatVotingAdapter:
    """
    創建一致通過群組對話適配器。

    Args:
        id: 適配器 ID
        participants: 參與者列表
        max_rounds: 最大輪數
        **kwargs: 其他配置參數

    Returns:
        配置好的 GroupChatVotingAdapter 實例
    """
    return GroupChatVotingAdapter(
        id=id,
        participants=participants,
        voting_method=VotingMethod.UNANIMOUS,
        voting_threshold=1.0,
        max_rounds=max_rounds,
        **kwargs,
    )


def create_ranked_voting_chat(
    id: str,
    participants: List[GroupChatParticipant],
    max_rounds: Optional[int] = 10,
    **kwargs,
) -> GroupChatVotingAdapter:
    """
    創建排序投票群組對話適配器。

    Args:
        id: 適配器 ID
        participants: 參與者列表
        max_rounds: 最大輪數
        **kwargs: 其他配置參數

    Returns:
        配置好的 GroupChatVotingAdapter 實例
    """
    return GroupChatVotingAdapter(
        id=id,
        participants=participants,
        voting_method=VotingMethod.RANKED,
        max_rounds=max_rounds,
        **kwargs,
    )
