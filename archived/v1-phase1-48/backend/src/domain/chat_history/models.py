"""
Chat History Domain Models -- Sprint 111

Pydantic models for chat message persistence and frontend-backend sync.

These models define the contract between the frontend localStorage-based
chat and the backend persistent storage.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """
    A single chat message in a session.

    Attributes:
        id: Unique message identifier (typically UUID from frontend).
        session_id: The session this message belongs to.
        role: Message role ("user", "assistant", "system").
        content: The message text content.
        timestamp: When the message was created.
        metadata: Additional context (e.g., tool calls, model info).
    """

    id: str
    session_id: str
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime
    metadata: Dict = Field(default_factory=dict)


class ChatHistorySync(BaseModel):
    """
    Bulk sync payload from frontend to backend.

    The frontend periodically sends its localStorage messages to the
    backend for persistent storage via the sync endpoint.

    Attributes:
        session_id: The session to sync.
        messages: Full list of messages to store.
        last_sync_at: Timestamp of the previous sync (for delta detection).
    """

    session_id: str
    messages: List[ChatMessage]
    last_sync_at: Optional[datetime] = None


class ChatSyncResponse(BaseModel):
    """
    Response from the sync endpoint.

    Attributes:
        session_id: The synced session.
        synced_count: Number of messages stored.
        sync_at: Timestamp of this sync operation.
    """

    session_id: str
    synced_count: int
    sync_at: datetime
