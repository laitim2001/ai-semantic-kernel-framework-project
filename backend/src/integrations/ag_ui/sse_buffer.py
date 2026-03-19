"""SSE Event Buffer — session-aware event buffering for reconnection.

Stores recent SSE events in Redis so that clients can reconnect
and replay missed events using Last-Event-ID.

Sprint 135 — Phase 39 E2E Assembly D.
"""

import json
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_TTL = timedelta(minutes=5)
MAX_BUFFER_SIZE = 100
KEY_PREFIX = "sse_buffer:"


class SSEEventBuffer:
    """Redis-backed SSE event buffer for reconnection support.

    Stores recent events per session so clients can replay missed
    events after a disconnection.

    Args:
        redis_backend: Storage backend with set/get/delete.
        ttl: Time-to-live for buffered events.
        max_size: Maximum events to retain per session.
    """

    def __init__(
        self,
        redis_backend: Any = None,
        ttl: timedelta = DEFAULT_TTL,
        max_size: int = MAX_BUFFER_SIZE,
    ) -> None:
        self._backend = redis_backend
        self._ttl = ttl
        self._max_size = max_size
        # In-memory fallback
        self._memory_buffer: Dict[str, List[Dict[str, Any]]] = {}

    async def buffer_event(
        self, session_id: str, event: Dict[str, Any]
    ) -> None:
        """Buffer an SSE event for potential replay."""
        key = f"{KEY_PREFIX}{session_id}"

        if self._backend:
            try:
                existing = await self._backend.get(key)
                events = existing if isinstance(existing, list) else []
                events.append(event)
                # Trim to max size
                if len(events) > self._max_size:
                    events = events[-self._max_size:]
                await self._backend.set(key, events, ttl=self._ttl)
                return
            except Exception as e:
                logger.warning("SSEBuffer: Redis write failed: %s", e)

        # In-memory fallback
        if session_id not in self._memory_buffer:
            self._memory_buffer[session_id] = []
        self._memory_buffer[session_id].append(event)
        if len(self._memory_buffer[session_id]) > self._max_size:
            self._memory_buffer[session_id] = self._memory_buffer[session_id][-self._max_size:]

    async def replay_from(
        self, session_id: str, last_event_id: int
    ) -> List[Dict[str, Any]]:
        """Replay events after a given event ID.

        Args:
            session_id: The session to replay.
            last_event_id: The last event ID the client received.

        Returns:
            List of events after last_event_id.
        """
        key = f"{KEY_PREFIX}{session_id}"
        events: List[Dict[str, Any]] = []

        if self._backend:
            try:
                stored = await self._backend.get(key)
                if isinstance(stored, list):
                    events = stored
            except Exception as e:
                logger.warning("SSEBuffer: Redis read failed: %s", e)

        if not events:
            events = self._memory_buffer.get(session_id, [])

        # Filter events after last_event_id
        return [e for e in events if e.get("id", 0) > last_event_id]

    async def cleanup(self, session_id: str) -> None:
        """Remove all buffered events for a session."""
        key = f"{KEY_PREFIX}{session_id}"
        if self._backend:
            try:
                await self._backend.delete(key)
            except Exception:
                pass
        self._memory_buffer.pop(session_id, None)
