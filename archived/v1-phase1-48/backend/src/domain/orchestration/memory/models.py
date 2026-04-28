# =============================================================================
# IPA Platform - Conversation Memory Models
# =============================================================================
# Sprint 9: S9-4 ConversationMemoryStore (8 points)
#
# Data models for conversation memory storage.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class SessionStatus(str, Enum):
    """Status of a conversation session.

    會話狀態:
    - ACTIVE: 活躍中
    - PAUSED: 已暫停
    - COMPLETED: 已完成
    - EXPIRED: 已過期
    - ARCHIVED: 已歸檔
    """
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    EXPIRED = "expired"
    ARCHIVED = "archived"


@dataclass
class MessageRecord:
    """A record of a message in conversation memory.

    訊息記錄。

    Attributes:
        message_id: 訊息唯一標識符
        group_id: 所屬群組 ID
        sender_id: 發送者 ID
        sender_name: 發送者名稱
        content: 訊息內容
        message_type: 訊息類型
        timestamp: 發送時間
        metadata: 額外元數據
        reply_to: 回覆的訊息 ID
    """
    message_id: UUID = field(default_factory=uuid4)
    group_id: Optional[UUID] = None
    sender_id: str = ""
    sender_name: str = ""
    content: str = ""
    message_type: str = "text"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    reply_to: Optional[UUID] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "message_id": str(self.message_id),
            "group_id": str(self.group_id) if self.group_id else None,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "content": self.content,
            "message_type": self.message_type,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "reply_to": str(self.reply_to) if self.reply_to else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageRecord":
        """Create from dictionary format."""
        return cls(
            message_id=UUID(data["message_id"]) if data.get("message_id") else uuid4(),
            group_id=UUID(data["group_id"]) if data.get("group_id") else None,
            sender_id=data.get("sender_id", ""),
            sender_name=data.get("sender_name", ""),
            content=data.get("content", ""),
            message_type=data.get("message_type", "text"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.utcnow(),
            metadata=data.get("metadata", {}),
            reply_to=UUID(data["reply_to"]) if data.get("reply_to") else None,
        )


@dataclass
class ConversationTurn:
    """A single turn in a conversation.

    對話輪次。

    Attributes:
        turn_id: 輪次唯一標識符
        turn_number: 輪次編號
        user_input: 用戶輸入
        agent_response: Agent 回應
        agent_id: 處理此輪次的 Agent ID
        timestamp: 時間戳
        processing_time_ms: 處理時間（毫秒）
        tokens_used: 使用的 token 數
        metadata: 額外元數據
    """
    turn_id: UUID = field(default_factory=uuid4)
    turn_number: int = 0
    user_input: str = ""
    agent_response: str = ""
    agent_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    processing_time_ms: int = 0
    tokens_used: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "turn_id": str(self.turn_id),
            "turn_number": self.turn_number,
            "user_input": self.user_input,
            "agent_response": self.agent_response,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp.isoformat(),
            "processing_time_ms": self.processing_time_ms,
            "tokens_used": self.tokens_used,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationTurn":
        """Create from dictionary format."""
        return cls(
            turn_id=UUID(data["turn_id"]) if data.get("turn_id") else uuid4(),
            turn_number=data.get("turn_number", 0),
            user_input=data.get("user_input", ""),
            agent_response=data.get("agent_response", ""),
            agent_id=data.get("agent_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.utcnow(),
            processing_time_ms=data.get("processing_time_ms", 0),
            tokens_used=data.get("tokens_used", 0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ConversationSession:
    """A conversation session containing multiple turns.

    對話會話，包含多個輪次。

    Attributes:
        session_id: 會話唯一標識符
        user_id: 用戶 ID
        workflow_id: 工作流 ID
        status: 會話狀態
        turns: 對話輪次列表
        context: 會話上下文
        created_at: 創建時間
        updated_at: 更新時間
        expires_at: 過期時間
        metadata: 額外元數據
    """
    session_id: UUID = field(default_factory=uuid4)
    user_id: str = ""
    workflow_id: Optional[UUID] = None
    status: SessionStatus = SessionStatus.ACTIVE
    turns: List[ConversationTurn] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def turn_count(self) -> int:
        """Get the number of turns in this session."""
        return len(self.turns)

    @property
    def is_expired(self) -> bool:
        """Check if the session is expired."""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False

    @property
    def duration_seconds(self) -> float:
        """Get the duration of the session in seconds."""
        return (self.updated_at - self.created_at).total_seconds()

    def add_turn(self, turn: ConversationTurn) -> None:
        """Add a turn to the session."""
        turn.turn_number = len(self.turns) + 1
        self.turns.append(turn)
        self.updated_at = datetime.utcnow()

    def get_last_turn(self) -> Optional[ConversationTurn]:
        """Get the last turn in the session."""
        return self.turns[-1] if self.turns else None

    def get_turn_by_number(self, turn_number: int) -> Optional[ConversationTurn]:
        """Get a turn by its number."""
        for turn in self.turns:
            if turn.turn_number == turn_number:
                return turn
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "session_id": str(self.session_id),
            "user_id": self.user_id,
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "status": self.status.value,
            "turns": [t.to_dict() for t in self.turns],
            "context": self.context,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata,
            "turn_count": self.turn_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationSession":
        """Create from dictionary format."""
        turns = [
            ConversationTurn.from_dict(t)
            for t in data.get("turns", [])
        ]
        return cls(
            session_id=UUID(data["session_id"]) if data.get("session_id") else uuid4(),
            user_id=data.get("user_id", ""),
            workflow_id=UUID(data["workflow_id"]) if data.get("workflow_id") else None,
            status=SessionStatus(data["status"]) if data.get("status") else SessionStatus.ACTIVE,
            turns=turns,
            context=data.get("context", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            metadata=data.get("metadata", {}),
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the session.

        獲取會話摘要。
        """
        total_user_tokens = sum(
            len(t.user_input.split()) for t in self.turns
        )
        total_agent_tokens = sum(
            len(t.agent_response.split()) for t in self.turns
        )
        total_tokens_used = sum(t.tokens_used for t in self.turns)
        avg_response_time = (
            sum(t.processing_time_ms for t in self.turns) / len(self.turns)
            if self.turns else 0
        )

        return {
            "session_id": str(self.session_id),
            "user_id": self.user_id,
            "status": self.status.value,
            "turn_count": self.turn_count,
            "total_user_words": total_user_tokens,
            "total_agent_words": total_agent_tokens,
            "total_tokens_used": total_tokens_used,
            "avg_response_time_ms": avg_response_time,
            "duration_seconds": self.duration_seconds,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
