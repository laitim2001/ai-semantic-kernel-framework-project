"""
Session Recovery Manager (S47-2)

Provides session state recovery and checkpoint management:
- SessionCheckpoint: Checkpoint data model
- SessionRecoveryManager: Checkpoint save/restore operations
- WebSocket reconnection handling
"""

from typing import Optional, Dict, Any, List, Protocol
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import logging

from src.domain.sessions.events import ExecutionEvent, ExecutionEventType, ExecutionEventFactory

logger = logging.getLogger(__name__)


class CheckpointType(str, Enum):
    """Checkpoint types"""
    EXECUTION_START = "execution_start"
    TOOL_CALL = "tool_call"
    APPROVAL_PENDING = "approval_pending"
    CONTENT_PARTIAL = "content_partial"
    EXECUTION_COMPLETE = "execution_complete"


@dataclass
class SessionCheckpoint:
    """Session checkpoint data"""
    session_id: str
    checkpoint_type: CheckpointType
    execution_id: Optional[str] = None
    state: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "session_id": self.session_id,
            "checkpoint_type": self.checkpoint_type.value,
            "execution_id": self.execution_id,
            "state": self.state,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionCheckpoint":
        """Create from dictionary"""
        return cls(
            session_id=data["session_id"],
            checkpoint_type=CheckpointType(data["checkpoint_type"]),
            execution_id=data.get("execution_id"),
            state=data.get("state", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            metadata=data.get("metadata", {}),
        )

    @property
    def is_expired(self) -> bool:
        """Check if checkpoint is expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class CacheProtocol(Protocol):
    """Protocol for cache operations"""

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        ...

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        ...

    async def delete(self, key: str) -> None:
        """Delete value from cache"""
        ...

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        ...


class SessionRecoveryManager:
    """Session recovery and checkpoint manager"""

    # Cache key prefixes
    CHECKPOINT_PREFIX = "session_checkpoint"
    EVENT_BUFFER_PREFIX = "session_events"
    RECONNECT_PREFIX = "session_reconnect"

    def __init__(
        self,
        cache: CacheProtocol,
        checkpoint_ttl: int = 3600,  # 1 hour
        event_buffer_ttl: int = 300,  # 5 minutes
        max_buffered_events: int = 100,
    ):
        self._cache = cache
        self._checkpoint_ttl = checkpoint_ttl
        self._event_buffer_ttl = event_buffer_ttl
        self._max_buffered_events = max_buffered_events

    def _checkpoint_key(self, session_id: str) -> str:
        """Generate checkpoint cache key"""
        return f"{self.CHECKPOINT_PREFIX}:{session_id}"

    def _event_buffer_key(self, session_id: str) -> str:
        """Generate event buffer cache key"""
        return f"{self.EVENT_BUFFER_PREFIX}:{session_id}"

    def _reconnect_key(self, session_id: str) -> str:
        """Generate reconnect info cache key"""
        return f"{self.RECONNECT_PREFIX}:{session_id}"

    # =========================================================================
    # Checkpoint Operations
    # =========================================================================

    async def save_checkpoint(
        self,
        session_id: str,
        checkpoint_type: CheckpointType,
        state: Dict[str, Any],
        execution_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> SessionCheckpoint:
        """Save session checkpoint"""
        checkpoint = SessionCheckpoint(
            session_id=session_id,
            checkpoint_type=checkpoint_type,
            execution_id=execution_id,
            state=state,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(seconds=ttl or self._checkpoint_ttl),
            metadata=metadata or {},
        )

        await self._cache.set(
            self._checkpoint_key(session_id),
            checkpoint.to_dict(),
            ttl=ttl or self._checkpoint_ttl,
        )

        logger.debug(
            f"Saved checkpoint for session {session_id}",
            extra={"checkpoint_type": checkpoint_type.value, "execution_id": execution_id},
        )

        return checkpoint

    async def get_checkpoint(
        self,
        session_id: str,
    ) -> Optional[SessionCheckpoint]:
        """Get session checkpoint"""
        data = await self._cache.get(self._checkpoint_key(session_id))
        if data is None:
            return None

        checkpoint = SessionCheckpoint.from_dict(data)
        if checkpoint.is_expired:
            await self.delete_checkpoint(session_id)
            return None

        return checkpoint

    async def delete_checkpoint(self, session_id: str) -> None:
        """Delete session checkpoint"""
        await self._cache.delete(self._checkpoint_key(session_id))
        logger.debug(f"Deleted checkpoint for session {session_id}")

    async def restore_from_checkpoint(
        self,
        session_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Restore session state from checkpoint"""
        checkpoint = await self.get_checkpoint(session_id)
        if checkpoint is None:
            return None

        logger.info(
            f"Restoring session {session_id} from checkpoint",
            extra={
                "checkpoint_type": checkpoint.checkpoint_type.value,
                "execution_id": checkpoint.execution_id,
            },
        )

        return checkpoint.state

    # =========================================================================
    # Event Buffer Operations
    # =========================================================================

    async def buffer_event(
        self,
        session_id: str,
        event: ExecutionEvent,
    ) -> None:
        """Buffer execution event for reconnection"""
        key = self._event_buffer_key(session_id)

        # Get existing buffer
        buffer = await self._cache.get(key) or []

        # Add event (limit buffer size)
        buffer.append(event.to_dict())
        if len(buffer) > self._max_buffered_events:
            buffer = buffer[-self._max_buffered_events:]

        await self._cache.set(key, buffer, ttl=self._event_buffer_ttl)

    async def get_buffered_events(
        self,
        session_id: str,
        since_event_id: Optional[str] = None,
    ) -> List[ExecutionEvent]:
        """Get buffered events for reconnection"""
        key = self._event_buffer_key(session_id)
        buffer = await self._cache.get(key) or []

        events = [ExecutionEvent.from_dict(e) for e in buffer]

        # Filter events after the specified event_id
        if since_event_id:
            found = False
            filtered = []
            for event in events:
                if found:
                    filtered.append(event)
                elif event.id == since_event_id:
                    found = True
            events = filtered

        return events

    async def clear_event_buffer(self, session_id: str) -> None:
        """Clear event buffer"""
        await self._cache.delete(self._event_buffer_key(session_id))

    # =========================================================================
    # WebSocket Reconnection
    # =========================================================================

    async def handle_websocket_reconnect(
        self,
        session_id: str,
        last_event_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle WebSocket reconnection"""
        result = {
            "status": "reconnected",
            "session_id": session_id,
            "checkpoint": None,
            "missed_events": [],
            "pending_state": None,
        }

        # Check for checkpoint
        checkpoint = await self.get_checkpoint(session_id)
        if checkpoint:
            result["checkpoint"] = checkpoint.to_dict()
            result["pending_state"] = checkpoint.state

            logger.info(
                f"Reconnected with pending checkpoint: {checkpoint.checkpoint_type.value}",
                extra={"session_id": session_id, "execution_id": checkpoint.execution_id},
            )

        # Get missed events
        missed_events = await self.get_buffered_events(session_id, last_event_id)
        result["missed_events"] = [e.to_dict() for e in missed_events]

        if missed_events:
            logger.info(
                f"Returning {len(missed_events)} missed events on reconnect",
                extra={"session_id": session_id},
            )

        return result

    async def save_reconnect_info(
        self,
        session_id: str,
        connection_id: str,
        client_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Save reconnection info for a session"""
        await self._cache.set(
            self._reconnect_key(session_id),
            {
                "connection_id": connection_id,
                "connected_at": datetime.utcnow().isoformat(),
                "client_info": client_info or {},
            },
            ttl=self._event_buffer_ttl,
        )

    async def get_reconnect_info(
        self,
        session_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get reconnection info for a session"""
        return await self._cache.get(self._reconnect_key(session_id))

    async def clear_reconnect_info(self, session_id: str) -> None:
        """Clear reconnection info"""
        await self._cache.delete(self._reconnect_key(session_id))

    # =========================================================================
    # Recovery Events
    # =========================================================================

    def create_reconnect_event(
        self,
        session_id: str,
        execution_id: str,
        pending_state: Optional[Dict[str, Any]] = None,
        missed_event_count: int = 0,
    ) -> ExecutionEvent:
        """Create reconnection event"""
        return ExecutionEvent(
            event_type=ExecutionEventType.CONTENT,
            session_id=session_id,
            execution_id=execution_id,
            content="reconnected",
            metadata={
                "type": "reconnected",
                "pending_state": pending_state,
                "missed_event_count": missed_event_count,
            },
        )

    def create_recovery_event(
        self,
        session_id: str,
        execution_id: str,
        checkpoint_type: CheckpointType,
        message: str,
    ) -> ExecutionEvent:
        """Create recovery status event"""
        return ExecutionEvent(
            event_type=ExecutionEventType.CONTENT,
            session_id=session_id,
            execution_id=execution_id,
            content=message,
            metadata={
                "type": "recovery",
                "checkpoint_type": checkpoint_type.value,
                "message": message,
            },
        )


def create_recovery_manager(
    cache: CacheProtocol,
    checkpoint_ttl: int = 3600,
    event_buffer_ttl: int = 300,
    max_buffered_events: int = 100,
) -> SessionRecoveryManager:
    """Factory function for SessionRecoveryManager"""
    return SessionRecoveryManager(
        cache=cache,
        checkpoint_ttl=checkpoint_ttl,
        event_buffer_ttl=event_buffer_ttl,
        max_buffered_events=max_buffered_events,
    )
