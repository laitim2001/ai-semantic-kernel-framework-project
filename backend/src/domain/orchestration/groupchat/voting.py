# =============================================================================
# IPA Platform - Voting Manager
# =============================================================================
# Sprint 9: S9-5 VotingManager (5 points)
#
# Manages voting sessions and consensus building in group chats.
# Supports multiple voting types and result calculation.
# =============================================================================

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class VoteType(str, Enum):
    """Type of voting mechanism.

    投票類型:
    - APPROVE_REJECT: 贊成/反對
    - MULTIPLE_CHOICE: 多選一
    - RANKING: 排序
    - WEIGHTED: 加權投票
    - SCORE: 評分投票
    """
    APPROVE_REJECT = "approve_reject"
    MULTIPLE_CHOICE = "multiple_choice"
    RANKING = "ranking"
    WEIGHTED = "weighted"
    SCORE = "score"


class VoteResult(str, Enum):
    """Result of a voting session.

    投票結果:
    - PASSED: 通過
    - REJECTED: 否決
    - TIE: 平局
    - NO_QUORUM: 未達法定人數
    - PENDING: 進行中
    - CANCELLED: 已取消
    """
    PASSED = "passed"
    REJECTED = "rejected"
    TIE = "tie"
    NO_QUORUM = "no_quorum"
    PENDING = "pending"
    CANCELLED = "cancelled"


class VotingSessionStatus(str, Enum):
    """Status of a voting session.

    投票會話狀態。
    """
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass
class Vote:
    """A single vote cast by a voter.

    單次投票記錄。

    Attributes:
        vote_id: 投票唯一標識符
        voter_id: 投票者 ID
        voter_name: 投票者名稱
        choice: 選擇（根據投票類型不同）
        weight: 投票權重
        timestamp: 投票時間
        reason: 投票理由
        metadata: 額外元數據
    """
    vote_id: UUID = field(default_factory=uuid4)
    voter_id: str = ""
    voter_name: str = ""
    choice: Any = None
    weight: float = 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "vote_id": str(self.vote_id),
            "voter_id": self.voter_id,
            "voter_name": self.voter_name,
            "choice": self.choice,
            "weight": self.weight,
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason,
            "metadata": self.metadata,
        }


@dataclass
class VotingSession:
    """A voting session within a group.

    投票會話。

    Attributes:
        session_id: 會話唯一標識符
        group_id: 所屬群組 ID
        topic: 投票主題
        description: 投票描述
        vote_type: 投票類型
        options: 選項列表
        votes: 投票記錄（voter_id -> Vote）
        status: 會話狀態
        created_at: 創建時間
        deadline: 截止時間
        required_quorum: 法定人數比例
        pass_threshold: 通過門檻
        result: 投票結果
        result_details: 結果詳情
        eligible_voters: 有資格投票的人員 ID
        created_by: 創建者 ID
        metadata: 額外元數據
    """
    session_id: UUID = field(default_factory=uuid4)
    group_id: Optional[UUID] = None
    topic: str = ""
    description: str = ""
    vote_type: VoteType = VoteType.APPROVE_REJECT
    options: List[str] = field(default_factory=list)
    votes: Dict[str, Vote] = field(default_factory=dict)
    status: VotingSessionStatus = VotingSessionStatus.OPEN
    created_at: datetime = field(default_factory=datetime.utcnow)
    deadline: Optional[datetime] = None
    required_quorum: float = 0.5
    pass_threshold: float = 0.5
    result: VoteResult = VoteResult.PENDING
    result_details: Dict[str, Any] = field(default_factory=dict)
    eligible_voters: Set[str] = field(default_factory=set)
    created_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        if self.deadline:
            return datetime.utcnow() > self.deadline
        return False

    @property
    def is_open(self) -> bool:
        """Check if the session is open for voting."""
        return self.status == VotingSessionStatus.OPEN and not self.is_expired

    @property
    def vote_count(self) -> int:
        """Get the number of votes cast."""
        return len(self.votes)

    @property
    def participation_rate(self) -> float:
        """Calculate the participation rate."""
        if not self.eligible_voters:
            return 0.0
        return len(self.votes) / len(self.eligible_voters)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "session_id": str(self.session_id),
            "group_id": str(self.group_id) if self.group_id else None,
            "topic": self.topic,
            "description": self.description,
            "vote_type": self.vote_type.value,
            "options": self.options,
            "votes": {k: v.to_dict() for k, v in self.votes.items()},
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "required_quorum": self.required_quorum,
            "pass_threshold": self.pass_threshold,
            "result": self.result.value,
            "result_details": self.result_details,
            "vote_count": self.vote_count,
            "participation_rate": self.participation_rate,
            "eligible_voters": list(self.eligible_voters),
            "created_by": self.created_by,
            "metadata": self.metadata,
        }


class VotingManager:
    """Manages voting sessions and consensus building.

    投票管理器，管理群組中的投票和共識達成。

    主要功能:
    - 創建投票會話
    - 投票
    - 計算結果
    - 支持多種投票類型
    - 投票驗證

    Example:
        ```python
        manager = VotingManager()

        # 創建投票
        session = manager.create_session(
            group_id=group_id,
            topic="Should we proceed with Plan A?",
            vote_type=VoteType.APPROVE_REJECT,
            eligible_voters=["agent-1", "agent-2", "agent-3"],
        )

        # 投票
        manager.cast_vote(session.session_id, "agent-1", "Alice", "approve")
        manager.cast_vote(session.session_id, "agent-2", "Bob", "reject")
        manager.cast_vote(session.session_id, "agent-3", "Charlie", "approve")

        # 計算結果
        result = manager.calculate_result(session.session_id)
        ```
    """

    def __init__(self):
        """Initialize the VotingManager."""
        self._sessions: Dict[UUID, VotingSession] = {}
        self._result_callbacks: List[Callable[[VotingSession], None]] = []

        logger.debug("VotingManager initialized")

    # =========================================================================
    # Session Management
    # =========================================================================

    def create_session(
        self,
        group_id: Optional[UUID] = None,
        topic: str = "",
        description: str = "",
        vote_type: VoteType = VoteType.APPROVE_REJECT,
        options: Optional[List[str]] = None,
        deadline_minutes: Optional[int] = None,
        required_quorum: float = 0.5,
        pass_threshold: float = 0.5,
        eligible_voters: Optional[Set[str]] = None,
        created_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VotingSession:
        """Create a new voting session.

        創建投票會話。

        Args:
            group_id: 群組 ID
            topic: 投票主題
            description: 投票描述
            vote_type: 投票類型
            options: 選項列表（多選時需要）
            deadline_minutes: 截止時間（分鐘）
            required_quorum: 法定人數比例
            pass_threshold: 通過門檻
            eligible_voters: 有資格投票的人員
            created_by: 創建者 ID
            metadata: 額外元數據

        Returns:
            新創建的投票會話
        """
        # Set default options for approve/reject
        if vote_type == VoteType.APPROVE_REJECT:
            options = ["approve", "reject"]
        elif vote_type == VoteType.SCORE:
            options = options or ["1", "2", "3", "4", "5"]
        elif not options:
            raise ValueError("Options required for this vote type")

        # Calculate deadline
        deadline = None
        if deadline_minutes:
            deadline = datetime.utcnow() + timedelta(minutes=deadline_minutes)

        session = VotingSession(
            session_id=uuid4(),
            group_id=group_id,
            topic=topic,
            description=description,
            vote_type=vote_type,
            options=options,
            deadline=deadline,
            required_quorum=required_quorum,
            pass_threshold=pass_threshold,
            eligible_voters=eligible_voters or set(),
            created_by=created_by,
            metadata=metadata or {},
        )

        self._sessions[session.session_id] = session
        logger.debug(f"Created voting session {session.session_id}: {topic}")

        return session

    def get_session(self, session_id: UUID) -> Optional[VotingSession]:
        """Get a voting session by ID.

        Args:
            session_id: 會話 ID

        Returns:
            投票會話
        """
        return self._sessions.get(session_id)

    def list_sessions(
        self,
        group_id: Optional[UUID] = None,
        status: Optional[VotingSessionStatus] = None,
    ) -> List[VotingSession]:
        """List voting sessions.

        列出投票會話。

        Args:
            group_id: 過濾群組 ID
            status: 過濾狀態

        Returns:
            會話列表
        """
        sessions = list(self._sessions.values())

        if group_id:
            sessions = [s for s in sessions if s.group_id == group_id]
        if status:
            sessions = [s for s in sessions if s.status == status]

        return sessions

    def close_session(self, session_id: UUID) -> bool:
        """Close a voting session.

        關閉投票會話。

        Args:
            session_id: 會話 ID

        Returns:
            是否成功關閉
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        session.status = VotingSessionStatus.CLOSED
        logger.debug(f"Closed voting session {session_id}")
        return True

    def cancel_session(self, session_id: UUID, reason: str = "") -> bool:
        """Cancel a voting session.

        取消投票會話。

        Args:
            session_id: 會話 ID
            reason: 取消原因

        Returns:
            是否成功取消
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        session.status = VotingSessionStatus.CANCELLED
        session.result = VoteResult.CANCELLED
        session.result_details["cancel_reason"] = reason
        logger.debug(f"Cancelled voting session {session_id}: {reason}")
        return True

    def delete_session(self, session_id: UUID) -> bool:
        """Delete a voting session.

        刪除投票會話。

        Args:
            session_id: 會話 ID

        Returns:
            是否成功刪除
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.debug(f"Deleted voting session {session_id}")
            return True
        return False

    # =========================================================================
    # Voting Operations
    # =========================================================================

    def cast_vote(
        self,
        session_id: UUID,
        voter_id: str,
        voter_name: str,
        choice: Any,
        weight: float = 1.0,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Vote:
        """Cast a vote in a session.

        投票。

        Args:
            session_id: 會話 ID
            voter_id: 投票者 ID
            voter_name: 投票者名稱
            choice: 選擇
            weight: 投票權重
            reason: 投票理由
            metadata: 額外元數據

        Returns:
            投票記錄

        Raises:
            ValueError: 如果投票無效
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Voting session {session_id} not found")

        # Check if session is open
        if not session.is_open:
            if session.is_expired:
                raise ValueError("Voting deadline has passed")
            raise ValueError("Voting session is not open")

        # Check eligibility
        if session.eligible_voters and voter_id not in session.eligible_voters:
            raise ValueError(f"Voter {voter_id} is not eligible to vote")

        # Validate choice
        self._validate_choice(session, choice)

        # Create vote
        vote = Vote(
            vote_id=uuid4(),
            voter_id=voter_id,
            voter_name=voter_name,
            choice=choice,
            weight=weight,
            reason=reason,
            metadata=metadata or {},
        )

        session.votes[voter_id] = vote
        logger.debug(f"Vote cast in session {session_id} by {voter_id}: {choice}")

        return vote

    def change_vote(
        self,
        session_id: UUID,
        voter_id: str,
        new_choice: Any,
        reason: Optional[str] = None,
    ) -> Optional[Vote]:
        """Change an existing vote.

        更改投票。

        Args:
            session_id: 會話 ID
            voter_id: 投票者 ID
            new_choice: 新選擇
            reason: 更改理由

        Returns:
            更新後的投票
        """
        session = self._sessions.get(session_id)
        if not session or not session.is_open:
            return None

        if voter_id not in session.votes:
            return None

        self._validate_choice(session, new_choice)

        vote = session.votes[voter_id]
        old_choice = vote.choice
        vote.choice = new_choice
        vote.timestamp = datetime.utcnow()
        if reason:
            vote.reason = reason

        logger.debug(f"Vote changed in session {session_id} by {voter_id}: {old_choice} -> {new_choice}")
        return vote

    def withdraw_vote(self, session_id: UUID, voter_id: str) -> bool:
        """Withdraw a vote.

        撤回投票。

        Args:
            session_id: 會話 ID
            voter_id: 投票者 ID

        Returns:
            是否成功撤回
        """
        session = self._sessions.get(session_id)
        if not session or not session.is_open:
            return False

        if voter_id in session.votes:
            del session.votes[voter_id]
            logger.debug(f"Vote withdrawn in session {session_id} by {voter_id}")
            return True
        return False

    def get_vote(self, session_id: UUID, voter_id: str) -> Optional[Vote]:
        """Get a voter's vote.

        獲取投票。

        Args:
            session_id: 會話 ID
            voter_id: 投票者 ID

        Returns:
            投票記錄
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        return session.votes.get(voter_id)

    def has_voted(self, session_id: UUID, voter_id: str) -> bool:
        """Check if a voter has voted.

        檢查是否已投票。

        Args:
            session_id: 會話 ID
            voter_id: 投票者 ID

        Returns:
            是否已投票
        """
        session = self._sessions.get(session_id)
        if not session:
            return False
        return voter_id in session.votes

    def _validate_choice(self, session: VotingSession, choice: Any) -> None:
        """Validate a vote choice.

        驗證投票選擇。
        """
        if session.vote_type == VoteType.APPROVE_REJECT:
            if choice not in ["approve", "reject"]:
                raise ValueError("Choice must be 'approve' or 'reject'")

        elif session.vote_type == VoteType.MULTIPLE_CHOICE:
            if choice not in session.options:
                raise ValueError(f"Invalid choice: {choice}. Must be one of {session.options}")

        elif session.vote_type == VoteType.RANKING:
            if not isinstance(choice, list):
                raise ValueError("Ranking choice must be a list")
            if set(choice) != set(session.options):
                raise ValueError("Ranking must include all options exactly once")

        elif session.vote_type == VoteType.SCORE:
            try:
                score = int(choice)
                if str(score) not in session.options:
                    raise ValueError(f"Score must be one of {session.options}")
            except (ValueError, TypeError):
                raise ValueError(f"Score must be a valid integer from {session.options}")

        elif session.vote_type == VoteType.WEIGHTED:
            if not isinstance(choice, (int, float)) or choice < 0:
                raise ValueError("Weighted choice must be a non-negative number")

    # =========================================================================
    # Result Calculation
    # =========================================================================

    def calculate_result(
        self,
        session_id: UUID,
        total_eligible_voters: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Calculate the voting result.

        計算投票結果。

        Args:
            session_id: 會話 ID
            total_eligible_voters: 總有資格投票人數

        Returns:
            投票結果詳情
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Voting session {session_id} not found")

        # Use eligible voters count if not provided
        if total_eligible_voters is None:
            total_eligible_voters = len(session.eligible_voters) or len(session.votes)

        if total_eligible_voters == 0:
            session.result = VoteResult.NO_QUORUM
            session.result_details = {"error": "No eligible voters"}
            return session.result_details

        # Check quorum
        participation_rate = len(session.votes) / total_eligible_voters
        if participation_rate < session.required_quorum:
            session.result = VoteResult.NO_QUORUM
            session.result_details = {
                "result": VoteResult.NO_QUORUM.value,
                "participation_rate": participation_rate,
                "required_quorum": session.required_quorum,
                "votes_received": len(session.votes),
                "voters_needed": int(total_eligible_voters * session.required_quorum),
            }
            return session.result_details

        # Calculate based on vote type
        if session.vote_type == VoteType.APPROVE_REJECT:
            result = self._calculate_approve_reject(session)
        elif session.vote_type == VoteType.MULTIPLE_CHOICE:
            result = self._calculate_multiple_choice(session)
        elif session.vote_type == VoteType.RANKING:
            result = self._calculate_ranking(session)
        elif session.vote_type == VoteType.WEIGHTED:
            result = self._calculate_weighted(session)
        elif session.vote_type == VoteType.SCORE:
            result = self._calculate_score(session)
        else:
            result = {"error": "Unknown vote type"}

        session.result_details = result
        session.result_details["participation_rate"] = participation_rate
        session.result_details["total_votes"] = len(session.votes)

        # Trigger callbacks
        for callback in self._result_callbacks:
            try:
                callback(session)
            except Exception as e:
                logger.error(f"Result callback error: {e}")

        return session.result_details

    def _calculate_approve_reject(self, session: VotingSession) -> Dict[str, Any]:
        """Calculate approve/reject voting result."""
        approve_weight = 0.0
        reject_weight = 0.0

        for vote in session.votes.values():
            if vote.choice == "approve":
                approve_weight += vote.weight
            else:
                reject_weight += vote.weight

        total_weight = approve_weight + reject_weight
        approve_ratio = approve_weight / total_weight if total_weight > 0 else 0

        if approve_ratio > session.pass_threshold:
            session.result = VoteResult.PASSED
        elif approve_ratio == session.pass_threshold and approve_ratio == 0.5:
            session.result = VoteResult.TIE
        else:
            session.result = VoteResult.REJECTED

        return {
            "result": session.result.value,
            "approve_count": sum(1 for v in session.votes.values() if v.choice == "approve"),
            "reject_count": sum(1 for v in session.votes.values() if v.choice == "reject"),
            "approve_weight": approve_weight,
            "reject_weight": reject_weight,
            "approve_ratio": approve_ratio,
            "pass_threshold": session.pass_threshold,
        }

    def _calculate_multiple_choice(self, session: VotingSession) -> Dict[str, Any]:
        """Calculate multiple choice voting result."""
        choice_weights: Dict[str, float] = {opt: 0.0 for opt in session.options}
        choice_counts: Dict[str, int] = {opt: 0 for opt in session.options}

        for vote in session.votes.values():
            if vote.choice in choice_weights:
                choice_weights[vote.choice] += vote.weight
                choice_counts[vote.choice] += 1

        # Find winner
        max_weight = max(choice_weights.values()) if choice_weights else 0
        winners = [opt for opt, weight in choice_weights.items() if weight == max_weight]

        if len(winners) == 1:
            session.result = VoteResult.PASSED
            winner = winners[0]
        else:
            session.result = VoteResult.TIE
            winner = None

        return {
            "result": session.result.value,
            "winner": winner,
            "choice_counts": choice_counts,
            "choice_weights": choice_weights,
            "tie_options": winners if len(winners) > 1 else None,
        }

    def _calculate_ranking(self, session: VotingSession) -> Dict[str, Any]:
        """Calculate ranking voting result using Borda count."""
        n_options = len(session.options)
        scores: Dict[str, float] = {opt: 0.0 for opt in session.options}

        for vote in session.votes.values():
            if isinstance(vote.choice, list):
                for rank, option in enumerate(vote.choice):
                    # Borda count: higher rank = more points
                    points = (n_options - rank) * vote.weight
                    scores[option] += points

        # Sort by score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        winner = ranked[0][0] if ranked else None

        session.result = VoteResult.PASSED

        return {
            "result": session.result.value,
            "winner": winner,
            "final_ranking": [opt for opt, _ in ranked],
            "scores": scores,
        }

    def _calculate_weighted(self, session: VotingSession) -> Dict[str, Any]:
        """Calculate weighted voting result."""
        total_weight = 0.0
        weighted_sum = 0.0

        for vote in session.votes.values():
            if isinstance(vote.choice, (int, float)):
                weighted_sum += vote.choice * vote.weight
                total_weight += vote.weight

        average = weighted_sum / total_weight if total_weight > 0 else 0

        session.result = VoteResult.PASSED

        return {
            "result": session.result.value,
            "weighted_average": average,
            "total_weight": total_weight,
            "weighted_sum": weighted_sum,
        }

    def _calculate_score(self, session: VotingSession) -> Dict[str, Any]:
        """Calculate score voting result."""
        scores: List[float] = []

        for vote in session.votes.values():
            try:
                score = float(vote.choice) * vote.weight
                scores.append(score)
            except (ValueError, TypeError):
                continue

        average = sum(scores) / len(scores) if scores else 0

        session.result = VoteResult.PASSED

        return {
            "result": session.result.value,
            "average_score": average,
            "total_scores": len(scores),
            "min_score": min(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
        }

    # =========================================================================
    # Callbacks and Events
    # =========================================================================

    def on_result(self, callback: Callable[[VotingSession], None]) -> None:
        """Register a callback for when results are calculated.

        註冊結果計算回調。

        Args:
            callback: 回調函數
        """
        self._result_callbacks.append(callback)

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self, session_id: UUID) -> Dict[str, Any]:
        """Get voting session statistics.

        獲取投票統計。

        Args:
            session_id: 會話 ID

        Returns:
            統計字典
        """
        session = self._sessions.get(session_id)
        if not session:
            return {}

        vote_times = [v.timestamp for v in session.votes.values()]

        return {
            "session_id": str(session_id),
            "topic": session.topic,
            "vote_type": session.vote_type.value,
            "status": session.status.value,
            "result": session.result.value,
            "total_votes": len(session.votes),
            "eligible_voters": len(session.eligible_voters),
            "participation_rate": session.participation_rate,
            "first_vote": min(vote_times).isoformat() if vote_times else None,
            "last_vote": max(vote_times).isoformat() if vote_times else None,
            "has_deadline": session.deadline is not None,
            "is_expired": session.is_expired,
        }

    # =========================================================================
    # Cleanup
    # =========================================================================

    def cleanup_expired(self) -> int:
        """Clean up expired sessions.

        清理過期的會話。

        Returns:
            清理的數量
        """
        expired = [
            sid for sid, session in self._sessions.items()
            if session.is_expired and session.status == VotingSessionStatus.OPEN
        ]

        for sid in expired:
            self._sessions[sid].status = VotingSessionStatus.EXPIRED
            logger.debug(f"Expired voting session {sid}")

        return len(expired)

    def clear(self) -> None:
        """Clear all voting sessions."""
        self._sessions.clear()
        logger.debug("Cleared all voting sessions")
