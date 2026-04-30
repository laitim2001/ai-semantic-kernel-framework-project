# =============================================================================
# IPA Platform - AG-UI Thread Models
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-3: Thread Manager
#
# Data models for AG-UI Thread (conversation thread) management.
# Threads track conversation state, messages, and metadata.
#
# Dependencies:
#   - pydantic (BaseModel, Field)
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ThreadStatus(str, Enum):
    """Thread 狀態枚舉"""

    ACTIVE = "active"  # 活躍中
    IDLE = "idle"  # 閒置
    ARCHIVED = "archived"  # 已歸檔
    DELETED = "deleted"  # 已刪除


class MessageRole(str, Enum):
    """訊息角色枚舉"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class AGUIMessage:
    """
    AG-UI Message (對話訊息)

    Represents a single message in a conversation thread.

    Attributes:
        message_id: Unique identifier for the message
        role: Message role (user, assistant, system, tool)
        content: Message text content
        created_at: When the message was created
        metadata: Additional message metadata
        tool_calls: Tool calls associated with this message
        tool_call_id: For tool response messages, the ID of the tool call
    """

    message_id: str
    role: MessageRole
    content: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_call_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "message_id": self.message_id,
            "role": self.role.value if isinstance(self.role, MessageRole) else self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "tool_calls": self.tool_calls,
            "tool_call_id": self.tool_call_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AGUIMessage":
        """Create from dictionary."""
        role = data.get("role", "user")
        if isinstance(role, str):
            role = MessageRole(role)

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.utcnow()

        return cls(
            message_id=data["message_id"],
            role=role,
            content=data.get("content", ""),
            created_at=created_at,
            metadata=data.get("metadata", {}),
            tool_calls=data.get("tool_calls", []),
            tool_call_id=data.get("tool_call_id"),
        )


@dataclass
class AGUIThread:
    """
    AG-UI Thread (對話線程)

    Represents a conversation thread that can contain multiple runs.
    Threads persist conversation state and history across multiple
    interactions.

    Attributes:
        thread_id: Unique identifier for the thread
        created_at: When the thread was created
        updated_at: When the thread was last updated
        messages: List of messages in the thread
        state: Shared state accessible to the agent
        metadata: Additional thread metadata
        status: Current thread status
        run_count: Number of runs executed in this thread
    """

    thread_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    messages: List[AGUIMessage] = field(default_factory=list)
    state: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: ThreadStatus = ThreadStatus.ACTIVE
    run_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "thread_id": self.thread_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [msg.to_dict() for msg in self.messages],
            "state": self.state,
            "metadata": self.metadata,
            "status": self.status.value if isinstance(self.status, ThreadStatus) else self.status,
            "run_count": self.run_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AGUIThread":
        """Create from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.utcnow()

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.utcnow()

        status = data.get("status", "active")
        if isinstance(status, str):
            status = ThreadStatus(status)

        messages = [
            AGUIMessage.from_dict(msg) if isinstance(msg, dict) else msg
            for msg in data.get("messages", [])
        ]

        return cls(
            thread_id=data["thread_id"],
            created_at=created_at,
            updated_at=updated_at,
            messages=messages,
            state=data.get("state", {}),
            metadata=data.get("metadata", {}),
            status=status,
            run_count=data.get("run_count", 0),
        )

    def add_message(self, message: AGUIMessage) -> None:
        """Add a message to the thread."""
        self.messages.append(message)
        self.updated_at = datetime.utcnow()

    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update thread state with new values."""
        self.state.update(updates)
        self.updated_at = datetime.utcnow()

    def increment_run_count(self) -> int:
        """Increment and return the new run count."""
        self.run_count += 1
        self.updated_at = datetime.utcnow()
        return self.run_count

    def archive(self) -> None:
        """Archive the thread."""
        self.status = ThreadStatus.ARCHIVED
        self.updated_at = datetime.utcnow()

    @property
    def is_active(self) -> bool:
        """Check if the thread is active."""
        return self.status == ThreadStatus.ACTIVE

    @property
    def message_count(self) -> int:
        """Get the number of messages in the thread."""
        return len(self.messages)


# Pydantic schemas for API serialization


class AGUIMessageSchema(BaseModel):
    """Pydantic schema for AGUIMessage API responses."""

    message_id: str = Field(..., description="訊息唯一 ID")
    role: str = Field(..., description="訊息角色 (user/assistant/system/tool)")
    content: str = Field(..., description="訊息內容")
    created_at: datetime = Field(..., description="建立時間")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="訊息元資料")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="工具調用")
    tool_call_id: Optional[str] = Field(None, description="工具調用 ID")

    model_config = {"from_attributes": True}

    @classmethod
    def from_dataclass(cls, message: AGUIMessage) -> "AGUIMessageSchema":
        """Create from AGUIMessage dataclass."""
        return cls(
            message_id=message.message_id,
            role=message.role.value if isinstance(message.role, MessageRole) else message.role,
            content=message.content,
            created_at=message.created_at,
            metadata=message.metadata,
            tool_calls=message.tool_calls,
            tool_call_id=message.tool_call_id,
        )


class AGUIThreadSchema(BaseModel):
    """Pydantic schema for AGUIThread API responses."""

    thread_id: str = Field(..., description="線程唯一 ID")
    created_at: datetime = Field(..., description="建立時間")
    updated_at: datetime = Field(..., description="更新時間")
    messages: List[AGUIMessageSchema] = Field(default_factory=list, description="訊息列表")
    state: Dict[str, Any] = Field(default_factory=dict, description="線程狀態")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="線程元資料")
    status: str = Field(..., description="線程狀態 (active/idle/archived/deleted)")
    run_count: int = Field(default=0, description="執行次數")

    model_config = {"from_attributes": True}

    @classmethod
    def from_dataclass(cls, thread: AGUIThread) -> "AGUIThreadSchema":
        """Create from AGUIThread dataclass."""
        return cls(
            thread_id=thread.thread_id,
            created_at=thread.created_at,
            updated_at=thread.updated_at,
            messages=[AGUIMessageSchema.from_dataclass(msg) for msg in thread.messages],
            state=thread.state,
            metadata=thread.metadata,
            status=thread.status.value if isinstance(thread.status, ThreadStatus) else thread.status,
            run_count=thread.run_count,
        )
