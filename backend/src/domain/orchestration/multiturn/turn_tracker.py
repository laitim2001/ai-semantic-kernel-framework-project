# =============================================================================
# IPA Platform - Turn Tracker
# =============================================================================
# Sprint 9: S9-3 MultiTurnSessionManager (8 points)
#
# Tracks individual turns within a multi-turn conversation session.
# =============================================================================

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TurnStatus(str, Enum):
    """Status of a conversation turn.

    輪次狀態:
    - STARTED: 已開始
    - AWAITING_RESPONSE: 等待回應
    - COMPLETED: 已完成
    - FAILED: 失敗
    - CANCELLED: 已取消
    """
    STARTED = "started"
    AWAITING_RESPONSE = "awaiting_response"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TurnMessage:
    """A message within a turn.

    輪次中的訊息。

    Attributes:
        message_id: 訊息唯一標識符
        role: 發送者角色
        content: 訊息內容
        timestamp: 發送時間
        metadata: 額外元數據
    """
    message_id: str
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "message_id": self.message_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class Turn:
    """Represents a single turn in a multi-turn conversation.

    多輪對話中的單個輪次。

    Attributes:
        turn_id: 輪次唯一標識符
        session_id: 所屬會話 ID
        turn_number: 輪次編號
        status: 輪次狀態
        messages: 輪次中的訊息
        agent_id: 處理此輪次的 Agent ID
        started_at: 開始時間
        completed_at: 完成時間
        duration_ms: 持續時間（毫秒）
        metadata: 額外元數據
    """
    turn_id: str
    session_id: str
    turn_number: int
    status: TurnStatus = TurnStatus.STARTED
    messages: List[TurnMessage] = field(default_factory=list)
    agent_id: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "turn_number": self.turn_number,
            "status": self.status.value,
            "messages": [m.to_dict() for m in self.messages],
            "agent_id": self.agent_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TurnMessage:
        """Add a message to this turn."""
        message = TurnMessage(
            message_id=str(uuid.uuid4()),
            role=role,
            content=content,
            metadata=metadata or {},
        )
        self.messages.append(message)
        return message

    def complete(self) -> None:
        """Mark this turn as completed."""
        self.status = TurnStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.duration_ms = int(
            (self.completed_at - self.started_at).total_seconds() * 1000
        )

    def fail(self, reason: str = "") -> None:
        """Mark this turn as failed."""
        self.status = TurnStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.duration_ms = int(
            (self.completed_at - self.started_at).total_seconds() * 1000
        )
        self.metadata["failure_reason"] = reason

    def cancel(self) -> None:
        """Cancel this turn."""
        self.status = TurnStatus.CANCELLED
        self.completed_at = datetime.utcnow()


class TurnTracker:
    """Tracks turns within a multi-turn conversation session.

    輪次追蹤器，管理會話中的所有輪次。

    主要功能:
    - 創建和追蹤輪次
    - 記錄輪次中的訊息
    - 計算輪次統計信息
    - 提供輪次歷史查詢

    Example:
        ```python
        tracker = TurnTracker(session_id="session-123")

        # 開始新輪次
        turn = tracker.start_turn()

        # 添加訊息
        turn.add_message("user", "Hello")
        turn.add_message("agent", "Hi there!")

        # 完成輪次
        tracker.end_turn(turn.turn_id)

        # 獲取統計
        stats = tracker.get_statistics()
        ```
    """

    def __init__(self, session_id: str):
        """Initialize the TurnTracker.

        Args:
            session_id: 所屬會話 ID
        """
        self._session_id = session_id
        self._turns: Dict[str, Turn] = {}
        self._turn_order: List[str] = []  # Maintains turn order
        self._current_turn_id: Optional[str] = None

        logger.debug(f"TurnTracker initialized for session {session_id}")

    @property
    def session_id(self) -> str:
        """Get the session ID."""
        return self._session_id

    @property
    def current_turn(self) -> Optional[Turn]:
        """Get the current active turn."""
        if self._current_turn_id:
            return self._turns.get(self._current_turn_id)
        return None

    @property
    def turn_count(self) -> int:
        """Get the total number of turns."""
        return len(self._turns)

    # =========================================================================
    # Turn Management
    # =========================================================================

    def start_turn(
        self,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Turn:
        """Start a new turn.

        開始新的輪次。

        Args:
            agent_id: 處理此輪次的 Agent ID
            metadata: 額外元數據

        Returns:
            新創建的輪次
        """
        turn_id = str(uuid.uuid4())
        turn_number = len(self._turns) + 1

        turn = Turn(
            turn_id=turn_id,
            session_id=self._session_id,
            turn_number=turn_number,
            status=TurnStatus.STARTED,
            agent_id=agent_id,
            metadata=metadata or {},
        )

        self._turns[turn_id] = turn
        self._turn_order.append(turn_id)
        self._current_turn_id = turn_id

        logger.debug(f"Started turn {turn_number} in session {self._session_id}")

        return turn

    def end_turn(
        self,
        turn_id: str,
        success: bool = True,
        failure_reason: str = "",
    ) -> Optional[Turn]:
        """End a turn.

        結束輪次。

        Args:
            turn_id: 輪次 ID
            success: 是否成功
            failure_reason: 失敗原因

        Returns:
            更新後的輪次
        """
        turn = self._turns.get(turn_id)
        if not turn:
            return None

        if success:
            turn.complete()
        else:
            turn.fail(failure_reason)

        if self._current_turn_id == turn_id:
            self._current_turn_id = None

        logger.debug(
            f"Ended turn {turn.turn_number} in session {self._session_id}: "
            f"{'success' if success else 'failed'}"
        )

        return turn

    def get_turn(self, turn_id: str) -> Optional[Turn]:
        """Get a turn by ID.

        Args:
            turn_id: 輪次 ID

        Returns:
            輪次
        """
        return self._turns.get(turn_id)

    def get_current_turn(self) -> Optional[Turn]:
        """Get the current active turn.

        Returns:
            當前輪次
        """
        return self.current_turn

    def get_turn_by_number(self, turn_number: int) -> Optional[Turn]:
        """Get a turn by number.

        Args:
            turn_number: 輪次編號

        Returns:
            輪次
        """
        for turn in self._turns.values():
            if turn.turn_number == turn_number:
                return turn
        return None

    def get_turn_history(
        self,
        limit: Optional[int] = None,
        include_failed: bool = True,
    ) -> List[Turn]:
        """Get turn history.

        獲取輪次歷史。

        Args:
            limit: 最大輪次數
            include_failed: 是否包含失敗的輪次

        Returns:
            輪次列表
        """
        turns = [self._turns[tid] for tid in self._turn_order]

        if not include_failed:
            turns = [t for t in turns if t.status != TurnStatus.FAILED]

        if limit:
            turns = turns[-limit:]

        return turns

    # =========================================================================
    # Message Management
    # =========================================================================

    def add_message_to_current(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[TurnMessage]:
        """Add a message to the current turn.

        添加訊息到當前輪次。

        Args:
            role: 發送者角色
            content: 訊息內容
            metadata: 額外元數據

        Returns:
            創建的訊息
        """
        turn = self.current_turn
        if not turn:
            logger.warning("No active turn to add message")
            return None

        return turn.add_message(role, content, metadata)

    def get_all_messages(
        self,
        limit: Optional[int] = None,
    ) -> List[TurnMessage]:
        """Get all messages across all turns.

        獲取所有輪次的訊息。

        Args:
            limit: 最大訊息數

        Returns:
            訊息列表
        """
        messages = []
        for turn_id in self._turn_order:
            turn = self._turns[turn_id]
            messages.extend(turn.messages)

        if limit:
            messages = messages[-limit:]

        return messages

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """Get turn statistics.

        獲取輪次統計信息。

        Returns:
            統計字典
        """
        turns = list(self._turns.values())

        completed = [t for t in turns if t.status == TurnStatus.COMPLETED]
        failed = [t for t in turns if t.status == TurnStatus.FAILED]

        durations = [t.duration_ms for t in completed if t.duration_ms is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0

        total_messages = sum(len(t.messages) for t in turns)

        return {
            "session_id": self._session_id,
            "total_turns": len(turns),
            "completed_turns": len(completed),
            "failed_turns": len(failed),
            "success_rate": len(completed) / len(turns) if turns else 0,
            "average_duration_ms": avg_duration,
            "total_messages": total_messages,
            "messages_per_turn": total_messages / len(turns) if turns else 0,
        }

    # =========================================================================
    # Cleanup
    # =========================================================================

    def clear(self) -> None:
        """Clear all turns."""
        self._turns.clear()
        self._turn_order.clear()
        self._current_turn_id = None
        logger.debug(f"Cleared all turns for session {self._session_id}")

    def cancel_current(self) -> Optional[Turn]:
        """Cancel the current turn.

        Returns:
            取消的輪次
        """
        if self._current_turn_id:
            turn = self._turns.get(self._current_turn_id)
            if turn:
                turn.cancel()
                self._current_turn_id = None
                return turn
        return None
