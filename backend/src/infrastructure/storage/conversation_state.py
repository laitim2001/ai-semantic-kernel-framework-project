"""L1 Conversation State — Redis-backed session conversation storage.

Stores ephemeral conversation data with 24-hour TTL:
  - Session messages (user + assistant turns)
  - Routing decisions
  - Approval status
  - Active tool calls

This is the fastest-access layer of the three-layer checkpoint system.

Sprint 115 — Phase 37 E2E Assembly B.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.infrastructure.storage.backends.base import StorageBackendABC
from src.infrastructure.storage.backends.factory import StorageFactory

logger = logging.getLogger(__name__)

_DEFAULT_TTL = timedelta(hours=24)
_KEY_PREFIX = "conv:"


class ConversationMessage(BaseModel):
    """Single message in a conversation."""

    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationState(BaseModel):
    """Full conversation state for a session."""

    session_id: str
    messages: List[ConversationMessage] = Field(default_factory=list)
    routing_decision: Optional[Dict[str, Any]] = None
    approval_status: Optional[Dict[str, Any]] = None
    active_tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = 0

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Append a message to the conversation."""
        self.messages.append(ConversationMessage(
            role=role,
            content=content,
            metadata=metadata or {},
        ))
        self.message_count = len(self.messages)
        self.updated_at = datetime.utcnow()


class ConversationStateStore:
    """L1 Conversation State store with Redis TTL.

    Provides fast access to ephemeral conversation data.  Data expires
    after 24 hours unless explicitly refreshed.

    Args:
        backend: Storage backend (Redis preferred, memory fallback).
        ttl: Time-to-live for conversation data.
    """

    def __init__(
        self,
        backend: Optional[StorageBackendABC] = None,
        ttl: timedelta = _DEFAULT_TTL,
    ) -> None:
        self._backend = backend
        self._ttl = ttl

    async def _ensure_backend(self) -> StorageBackendABC:
        if self._backend is None:
            self._backend = await StorageFactory.create(
                name="conversation_state",
                backend_type="auto",
            )
            logger.info(
                "ConversationStateStore: backend=%s ttl=%s",
                type(self._backend).__name__, self._ttl,
            )
        return self._backend

    def _key(self, session_id: str) -> str:
        return f"{_KEY_PREFIX}{session_id}"

    async def save(self, state: ConversationState) -> None:
        """Save conversation state with TTL."""
        backend = await self._ensure_backend()
        state.updated_at = datetime.utcnow()
        await backend.set(
            self._key(state.session_id),
            state.model_dump(mode="json"),
            ttl=self._ttl,
        )

    async def load(self, session_id: str) -> Optional[ConversationState]:
        """Load conversation state for a session."""
        backend = await self._ensure_backend()
        data = await backend.get(self._key(session_id))
        if data is None:
            return None
        return ConversationState.model_validate(data)

    async def delete(self, session_id: str) -> None:
        """Remove conversation state."""
        backend = await self._ensure_backend()
        await backend.delete(self._key(session_id))

    async def exists(self, session_id: str) -> bool:
        """Check if conversation state exists."""
        backend = await self._ensure_backend()
        return await backend.exists(self._key(session_id))

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationState:
        """Add a message to a session's conversation.

        Creates a new ConversationState if none exists.
        """
        state = await self.load(session_id)
        if state is None:
            state = ConversationState(session_id=session_id)
        state.add_message(role, content, metadata)
        await self.save(state)
        return state

    async def set_routing_decision(
        self, session_id: str, decision: Dict[str, Any]
    ) -> None:
        """Update the routing decision for a session."""
        state = await self.load(session_id)
        if state is None:
            state = ConversationState(session_id=session_id)
        state.routing_decision = decision
        state.updated_at = datetime.utcnow()
        await self.save(state)

    async def list_active_sessions(self) -> List[str]:
        """List all active session IDs."""
        backend = await self._ensure_backend()
        try:
            keys = await backend.keys(pattern=f"{_KEY_PREFIX}*")
            return [k.replace(_KEY_PREFIX, "") for k in keys]
        except (AttributeError, NotImplementedError):
            return []
