# =============================================================================
# IPA Platform - Claude Session State Management
# =============================================================================
# Sprint 80: S80-4 - Claude Session 狀態增強 (5 pts)
#
# This module provides session state persistence and enhancement features:
#   - State persistence to PostgreSQL
#   - Cross-session context recovery
#   - Context compression strategies
#   - Session expiration and cleanup
#   - State sync to mem0
# =============================================================================

import hashlib
import json
import logging
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .types import Message


logger = logging.getLogger(__name__)


@dataclass
class SessionStateConfig:
    """Configuration for session state management."""

    # Persistence
    enable_persistence: bool = True
    compression_enabled: bool = True
    compression_threshold: int = 1000  # Compress if > N characters

    # Expiration
    session_ttl_hours: int = 24
    cleanup_batch_size: int = 100

    # Context compression
    max_context_tokens: int = 10000
    context_summarization_enabled: bool = True
    preserve_recent_messages: int = 10

    # mem0 sync
    enable_mem0_sync: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enable_persistence": self.enable_persistence,
            "compression_enabled": self.compression_enabled,
            "compression_threshold": self.compression_threshold,
            "session_ttl_hours": self.session_ttl_hours,
            "cleanup_batch_size": self.cleanup_batch_size,
            "max_context_tokens": self.max_context_tokens,
            "context_summarization_enabled": self.context_summarization_enabled,
            "preserve_recent_messages": self.preserve_recent_messages,
            "enable_mem0_sync": self.enable_mem0_sync,
        }


@dataclass
class SessionState:
    """Serializable session state."""

    session_id: str
    user_id: Optional[str] = None
    history: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    total_tokens: int = 0
    message_count: int = 0
    is_compressed: bool = False
    checksum: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "history": self.history,
            "context": self.context,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "total_tokens": self.total_tokens,
            "message_count": self.message_count,
            "is_compressed": self.is_compressed,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionState":
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            user_id=data.get("user_id"),
            history=data.get("history", []),
            context=data.get("context", {}),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"])
            if isinstance(data.get("created_at"), str)
            else data.get("created_at", datetime.utcnow()),
            updated_at=datetime.fromisoformat(data["updated_at"])
            if isinstance(data.get("updated_at"), str)
            else data.get("updated_at", datetime.utcnow()),
            expires_at=datetime.fromisoformat(data["expires_at"])
            if data.get("expires_at")
            else None,
            total_tokens=data.get("total_tokens", 0),
            message_count=data.get("message_count", 0),
            is_compressed=data.get("is_compressed", False),
            checksum=data.get("checksum"),
        )


# Default configuration
DEFAULT_SESSION_STATE_CONFIG = SessionStateConfig()


class SessionStateManager:
    """
    Manages session state persistence and recovery.

    Provides:
    - PostgreSQL persistence for session state
    - Context compression for large histories
    - Automatic session expiration
    - Cross-session recovery
    - mem0 synchronization
    """

    def __init__(
        self,
        config: Optional[SessionStateConfig] = None,
        checkpoint_service: Optional[Any] = None,
        memory_manager: Optional[Any] = None,
    ):
        """
        Initialize session state manager.

        Args:
            config: State management configuration.
            checkpoint_service: Checkpoint service for persistence.
            memory_manager: UnifiedMemoryManager for mem0 sync.
        """
        self.config = config or DEFAULT_SESSION_STATE_CONFIG
        self._checkpoint_service = checkpoint_service
        self._memory_manager = memory_manager

        # In-memory cache
        self._state_cache: Dict[str, SessionState] = {}

        self._initialized = False

    async def initialize(
        self,
        checkpoint_service: Optional[Any] = None,
        memory_manager: Optional[Any] = None,
    ) -> None:
        """
        Initialize with required services.

        Args:
            checkpoint_service: Checkpoint service for persistence.
            memory_manager: UnifiedMemoryManager for mem0 sync.
        """
        if checkpoint_service:
            self._checkpoint_service = checkpoint_service
        if memory_manager:
            self._memory_manager = memory_manager

        self._initialized = True
        logger.info("SessionStateManager initialized")

    def _ensure_initialized(self) -> None:
        """Ensure manager is initialized."""
        if not self._initialized:
            raise RuntimeError(
                "SessionStateManager not initialized. Call initialize() first."
            )

    async def save_state(
        self,
        session_id: str,
        history: List[Message],
        context: Dict[str, Any],
        user_id: Optional[str] = None,
        total_tokens: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionState:
        """
        Save session state.

        Args:
            session_id: Session identifier.
            history: Conversation history.
            context: Session context variables.
            user_id: User identifier.
            total_tokens: Total tokens used.
            metadata: Additional metadata.

        Returns:
            Saved SessionState.
        """
        self._ensure_initialized()

        # Convert history to serializable format
        history_data = [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "tool_calls": [tc.__dict__ for tc in (msg.tool_calls or [])],
            }
            for msg in history
        ]

        # Create state object
        state = SessionState(
            session_id=session_id,
            user_id=user_id,
            history=history_data,
            context=context,
            metadata=metadata or {},
            updated_at=datetime.utcnow(),
            expires_at=datetime.utcnow()
            + timedelta(hours=self.config.session_ttl_hours),
            total_tokens=total_tokens,
            message_count=len(history),
        )

        # Compress if needed
        if self.config.compression_enabled:
            state = self._compress_state(state)

        # Calculate checksum
        state.checksum = self._calculate_checksum(state)

        # Save to cache
        self._state_cache[session_id] = state

        # Persist to checkpoint service
        if self.config.enable_persistence and self._checkpoint_service:
            try:
                await self._persist_state(state)
            except Exception as e:
                logger.warning(f"Failed to persist session state: {e}")

        # Sync to mem0
        if self.config.enable_mem0_sync and self._memory_manager:
            try:
                await self._sync_to_mem0(state)
            except Exception as e:
                logger.warning(f"Failed to sync state to mem0: {e}")

        logger.debug(f"Saved session state: {session_id}")
        return state

    async def restore_state(
        self,
        session_id: str,
    ) -> Optional[SessionState]:
        """
        Restore session state.

        Args:
            session_id: Session identifier.

        Returns:
            Restored SessionState or None if not found.
        """
        self._ensure_initialized()

        # Check cache first
        if session_id in self._state_cache:
            state = self._state_cache[session_id]

            # Check expiration
            if state.expires_at and datetime.utcnow() > state.expires_at:
                logger.debug(f"Session {session_id} has expired")
                await self.delete_state(session_id)
                return None

            return state

        # Try to load from checkpoint service
        if self.config.enable_persistence and self._checkpoint_service:
            try:
                state = await self._load_state(session_id)
                if state:
                    # Verify checksum
                    if not self._verify_checksum(state):
                        logger.warning(
                            f"Session {session_id} checksum mismatch, data may be corrupted"
                        )

                    # Check expiration
                    if state.expires_at and datetime.utcnow() > state.expires_at:
                        logger.debug(f"Session {session_id} has expired")
                        await self.delete_state(session_id)
                        return None

                    # Decompress if needed
                    if state.is_compressed:
                        state = self._decompress_state(state)

                    # Cache it
                    self._state_cache[session_id] = state
                    return state

            except Exception as e:
                logger.warning(f"Failed to load session state: {e}")

        return None

    async def delete_state(self, session_id: str) -> bool:
        """
        Delete session state.

        Args:
            session_id: Session identifier.

        Returns:
            True if deleted, False if not found.
        """
        self._ensure_initialized()

        # Remove from cache
        deleted = session_id in self._state_cache
        self._state_cache.pop(session_id, None)

        # Delete from checkpoint service
        if self.config.enable_persistence and self._checkpoint_service:
            try:
                await self._delete_persisted_state(session_id)
            except Exception as e:
                logger.warning(f"Failed to delete persisted state: {e}")

        return deleted

    def compress_context(
        self,
        history: List[Message],
        context: Dict[str, Any],
        current_prompt: str,
    ) -> tuple[List[Message], Dict[str, Any], Optional[str]]:
        """
        Compress context to fit within token limits.

        Args:
            history: Full conversation history.
            context: Current context variables.
            current_prompt: The new prompt being added.

        Returns:
            Tuple of (compressed_history, compressed_context, summary).
        """
        # Estimate current tokens (rough approximation: 4 chars = 1 token)
        total_chars = sum(len(m.content) for m in history) + len(str(context))
        estimated_tokens = total_chars // 4

        if estimated_tokens <= self.config.max_context_tokens:
            return history, context, None

        logger.debug(
            f"Compressing context: {estimated_tokens} tokens > {self.config.max_context_tokens}"
        )

        # Strategy 1: Keep only recent messages
        compressed_history = history[-self.config.preserve_recent_messages :]

        # Strategy 2: Summarize older context
        summary = None
        if self.config.context_summarization_enabled and len(history) > self.config.preserve_recent_messages:
            older_messages = history[: -self.config.preserve_recent_messages]
            summary = self._generate_summary(older_messages)

        # Strategy 3: Remove large context items
        compressed_context = {}
        for key, value in context.items():
            value_str = str(value)
            if len(value_str) < 500:  # Keep small items
                compressed_context[key] = value
            else:
                compressed_context[key] = f"[Compressed: {len(value_str)} chars]"

        return compressed_history, compressed_context, summary

    def _generate_summary(self, messages: List[Message]) -> str:
        """Generate a summary of messages."""
        # Simple summary - in production, could use Claude to generate
        user_msgs = [m for m in messages if m.role == "user"]
        assistant_msgs = [m for m in messages if m.role == "assistant"]

        summary_parts = []
        if user_msgs:
            topics = [m.content[:100] for m in user_msgs[:3]]
            summary_parts.append(f"討論主題: {'; '.join(topics)}")

        if assistant_msgs:
            summary_parts.append(f"共 {len(assistant_msgs)} 次回應")

        return " | ".join(summary_parts) if summary_parts else ""

    def _compress_state(self, state: SessionState) -> SessionState:
        """Compress state data if needed."""
        history_str = json.dumps(state.history, ensure_ascii=False)

        if len(history_str) < self.config.compression_threshold:
            return state

        try:
            compressed = zlib.compress(history_str.encode("utf-8"))
            # Store as base64 for JSON compatibility
            import base64

            state.history = [{"_compressed": base64.b64encode(compressed).decode("ascii")}]
            state.is_compressed = True

            logger.debug(
                f"Compressed history: {len(history_str)} -> {len(compressed)} bytes"
            )
        except Exception as e:
            logger.warning(f"Failed to compress state: {e}")

        return state

    def _decompress_state(self, state: SessionState) -> SessionState:
        """Decompress state data."""
        if not state.is_compressed:
            return state

        try:
            if state.history and "_compressed" in state.history[0]:
                import base64

                compressed = base64.b64decode(state.history[0]["_compressed"])
                history_str = zlib.decompress(compressed).decode("utf-8")
                state.history = json.loads(history_str)
                state.is_compressed = False

                logger.debug("Decompressed history")
        except Exception as e:
            logger.warning(f"Failed to decompress state: {e}")

        return state

    def _calculate_checksum(self, state: SessionState) -> str:
        """Calculate checksum for state integrity."""
        data = json.dumps(
            {
                "session_id": state.session_id,
                "history": state.history,
                "context": state.context,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]

    def _verify_checksum(self, state: SessionState) -> bool:
        """Verify state checksum."""
        if not state.checksum:
            return True

        calculated = self._calculate_checksum(state)
        return calculated == state.checksum

    async def _persist_state(self, state: SessionState) -> None:
        """Persist state to checkpoint service."""
        if not self._checkpoint_service:
            return

        # Use checkpoint service's save method
        await self._checkpoint_service.save_checkpoint(
            checkpoint_id=f"session_state:{state.session_id}",
            state=state.to_dict(),
            ttl_seconds=self.config.session_ttl_hours * 3600,
        )

    async def _load_state(self, session_id: str) -> Optional[SessionState]:
        """Load state from checkpoint service."""
        if not self._checkpoint_service:
            return None

        data = await self._checkpoint_service.load_checkpoint(
            checkpoint_id=f"session_state:{session_id}"
        )

        if data:
            return SessionState.from_dict(data)

        return None

    async def _delete_persisted_state(self, session_id: str) -> None:
        """Delete persisted state."""
        if not self._checkpoint_service:
            return

        await self._checkpoint_service.delete_checkpoint(
            checkpoint_id=f"session_state:{session_id}"
        )

    async def _sync_to_mem0(self, state: SessionState) -> None:
        """Sync state to mem0 for long-term memory."""
        if not self._memory_manager:
            return

        # Create a memory entry from session state
        memory_content = f"Session {state.session_id}: {state.message_count} messages, {state.total_tokens} tokens"

        if state.context:
            context_summary = ", ".join(
                f"{k}={str(v)[:50]}" for k, v in list(state.context.items())[:5]
            )
            memory_content += f". Context: {context_summary}"

        await self._memory_manager.add_memory(
            content=memory_content,
            user_id=state.user_id,
            metadata={
                "type": "session_state",
                "session_id": state.session_id,
                "message_count": state.message_count,
                "total_tokens": state.total_tokens,
            },
        )

    async def cleanup_expired_sessions(self) -> int:
        """
        Cleanup expired sessions.

        Returns:
            Number of sessions cleaned up.
        """
        self._ensure_initialized()

        cleaned = 0
        now = datetime.utcnow()

        # Clean from cache
        expired_ids = [
            sid
            for sid, state in self._state_cache.items()
            if state.expires_at and now > state.expires_at
        ]

        for sid in expired_ids:
            await self.delete_state(sid)
            cleaned += 1

        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} expired sessions")

        return cleaned

    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        active_sessions = len(self._state_cache)
        total_messages = sum(s.message_count for s in self._state_cache.values())
        total_tokens = sum(s.total_tokens for s in self._state_cache.values())

        return {
            "active_sessions": active_sessions,
            "total_messages": total_messages,
            "total_tokens": total_tokens,
            "config": self.config.to_dict(),
        }
