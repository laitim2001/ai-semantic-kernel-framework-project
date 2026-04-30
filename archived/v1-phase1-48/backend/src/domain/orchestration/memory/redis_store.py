# =============================================================================
# IPA Platform - Redis Conversation Memory Store
# =============================================================================
# Sprint 9: S9-4 ConversationMemoryStore (8 points)
#
# Redis-based implementation of conversation memory storage.
# Optimized for fast read/write with TTL support.
# =============================================================================

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Protocol
from uuid import UUID

from src.domain.orchestration.memory.base import ConversationMemoryStore
from src.domain.orchestration.memory.models import (
    ConversationSession,
    ConversationTurn,
    MessageRecord,
    SessionStatus,
)

logger = logging.getLogger(__name__)


class RedisClientProtocol(Protocol):
    """Protocol for Redis client interface.

    Redis 客戶端協議，支持同步和異步實現。
    """

    async def rpush(self, key: str, value: str) -> int: ...
    async def lrange(self, key: str, start: int, end: int) -> List[bytes]: ...
    async def llen(self, key: str) -> int: ...
    async def delete(self, *keys: str) -> int: ...
    async def expire(self, key: str, seconds: int) -> bool: ...
    async def hset(self, key: str, mapping: Dict[str, Any]) -> int: ...
    async def hgetall(self, key: str) -> Dict[bytes, bytes]: ...
    async def keys(self, pattern: str) -> List[bytes]: ...
    async def exists(self, key: str) -> int: ...
    async def scan(self, cursor: int, match: str, count: int) -> tuple: ...


class RedisConversationMemoryStore(ConversationMemoryStore):
    """Redis-based implementation of conversation memory storage.

    基於 Redis 的對話記憶存儲實現。

    使用 Redis 提供快速的讀寫性能和自動過期功能。

    Key Patterns:
    - Messages: {prefix}messages:{group_id}
    - Sessions: {prefix}session:{session_id}
    - Turns: {prefix}turns:{session_id}
    - Session Index: {prefix}sessions:user:{user_id}

    Example:
        ```python
        import redis.asyncio as redis

        redis_client = redis.Redis(host="localhost", port=6379)
        store = RedisConversationMemoryStore(redis_client)

        # 保存會話
        session = ConversationSession(user_id="user-1")
        await store.save_session(session)
        ```
    """

    def __init__(
        self,
        redis_client: Any,
        key_prefix: str = "conv_memory:",
        message_ttl_hours: int = 24,
        session_ttl_hours: int = 48,
    ):
        """Initialize the Redis store.

        Args:
            redis_client: Redis 客戶端
            key_prefix: 鍵前綴
            message_ttl_hours: 訊息 TTL（小時）
            session_ttl_hours: 會話 TTL（小時）
        """
        self.redis = redis_client
        self.prefix = key_prefix
        self.message_ttl = timedelta(hours=message_ttl_hours)
        self.session_ttl = timedelta(hours=session_ttl_hours)

        logger.debug(f"RedisConversationMemoryStore initialized with prefix '{key_prefix}'")

    # =========================================================================
    # Key Generation
    # =========================================================================

    def _message_key(self, group_id: UUID) -> str:
        """Generate key for messages."""
        return f"{self.prefix}messages:{group_id}"

    def _session_key(self, session_id: UUID) -> str:
        """Generate key for session."""
        return f"{self.prefix}session:{session_id}"

    def _turn_key(self, session_id: UUID) -> str:
        """Generate key for turns."""
        return f"{self.prefix}turns:{session_id}"

    def _user_sessions_key(self, user_id: str) -> str:
        """Generate key for user's session index."""
        return f"{self.prefix}sessions:user:{user_id}"

    # =========================================================================
    # Message Operations
    # =========================================================================

    async def add_message(self, message: MessageRecord) -> None:
        """Add a message to Redis."""
        if not message.group_id:
            logger.warning("Message has no group_id, skipping")
            return

        key = self._message_key(message.group_id)
        message_json = json.dumps(message.to_dict(), default=str)

        await self.redis.rpush(key, message_json)
        await self.redis.expire(key, int(self.message_ttl.total_seconds()))

        logger.debug(f"Added message {message.message_id} to group {message.group_id}")

    async def get_messages(
        self,
        group_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[MessageRecord]:
        """Get messages from Redis."""
        key = self._message_key(group_id)

        start = offset
        end = offset + limit - 1

        messages_raw = await self.redis.lrange(key, start, end)

        messages = []
        for msg_raw in messages_raw:
            msg_str = msg_raw.decode("utf-8") if isinstance(msg_raw, bytes) else msg_raw
            msg_data = json.loads(msg_str)
            messages.append(MessageRecord.from_dict(msg_data))

        return messages

    async def get_message_count(self, group_id: UUID) -> int:
        """Get message count from Redis."""
        key = self._message_key(group_id)
        return await self.redis.llen(key)

    async def delete_messages(self, group_id: UUID) -> int:
        """Delete all messages for a group."""
        key = self._message_key(group_id)
        count = await self.redis.llen(key)
        await self.redis.delete(key)
        return count

    # =========================================================================
    # Session Operations
    # =========================================================================

    async def save_session(self, session: ConversationSession) -> None:
        """Save session to Redis hash."""
        key = self._session_key(session.session_id)

        session_data = {
            "session_id": str(session.session_id),
            "user_id": session.user_id,
            "workflow_id": str(session.workflow_id) if session.workflow_id else "",
            "status": session.status.value,
            "context": json.dumps(session.context),
            "created_at": session.created_at.isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "expires_at": session.expires_at.isoformat() if session.expires_at else "",
            "metadata": json.dumps(session.metadata),
            "turn_count": str(len(session.turns)),
        }

        await self.redis.hset(key, mapping=session_data)
        await self.redis.expire(key, int(self.session_ttl.total_seconds()))

        # Add to user index
        if session.user_id:
            user_key = self._user_sessions_key(session.user_id)
            await self.redis.rpush(user_key, str(session.session_id))
            await self.redis.expire(user_key, int(self.session_ttl.total_seconds()))

        logger.debug(f"Saved session {session.session_id} to Redis")

    async def load_session(self, session_id: UUID) -> Optional[ConversationSession]:
        """Load session from Redis."""
        key = self._session_key(session_id)

        session_raw = await self.redis.hgetall(key)
        if not session_raw:
            return None

        # Decode bytes if necessary
        session_data = {}
        for k, v in session_raw.items():
            key_str = k.decode("utf-8") if isinstance(k, bytes) else k
            val_str = v.decode("utf-8") if isinstance(v, bytes) else v
            session_data[key_str] = val_str

        # Load turns
        turns = await self.get_turns(session_id)

        return ConversationSession(
            session_id=UUID(session_data["session_id"]),
            user_id=session_data.get("user_id", ""),
            workflow_id=UUID(session_data["workflow_id"]) if session_data.get("workflow_id") else None,
            status=SessionStatus(session_data["status"]),
            turns=turns,
            context=json.loads(session_data.get("context", "{}")),
            created_at=datetime.fromisoformat(session_data["created_at"]),
            updated_at=datetime.fromisoformat(session_data["updated_at"]),
            expires_at=datetime.fromisoformat(session_data["expires_at"]) if session_data.get("expires_at") else None,
            metadata=json.loads(session_data.get("metadata", "{}")),
        )

    async def delete_session(self, session_id: UUID) -> bool:
        """Delete session from Redis."""
        session_key = self._session_key(session_id)
        turn_key = self._turn_key(session_id)

        # Check if exists
        exists = await self.redis.exists(session_key)
        if not exists:
            return False

        await self.redis.delete(session_key, turn_key)
        logger.debug(f"Deleted session {session_id} from Redis")
        return True

    async def list_sessions(
        self,
        user_id: Optional[str] = None,
        status: Optional[SessionStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ConversationSession]:
        """List sessions from Redis."""
        sessions = []

        if user_id:
            # Get sessions for specific user
            user_key = self._user_sessions_key(user_id)
            session_ids_raw = await self.redis.lrange(user_key, 0, -1)

            for sid_raw in session_ids_raw:
                sid_str = sid_raw.decode("utf-8") if isinstance(sid_raw, bytes) else sid_raw
                try:
                    session = await self.load_session(UUID(sid_str))
                    if session:
                        if status is None or session.status == status:
                            sessions.append(session)
                except (ValueError, TypeError):
                    continue
        else:
            # Scan all sessions
            pattern = f"{self.prefix}session:*"
            cursor = 0
            scanned_keys = []

            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                scanned_keys.extend(keys)
                if cursor == 0:
                    break

            for key in scanned_keys:
                key_str = key.decode("utf-8") if isinstance(key, bytes) else key
                session_id_str = key_str.split(":")[-1]
                try:
                    session = await self.load_session(UUID(session_id_str))
                    if session:
                        if status is None or session.status == status:
                            sessions.append(session)
                except (ValueError, TypeError):
                    continue

        # Sort by updated_at
        sessions.sort(key=lambda s: s.updated_at, reverse=True)

        # Apply pagination
        return sessions[offset:offset + limit]

    async def update_session_status(
        self,
        session_id: UUID,
        status: SessionStatus,
    ) -> bool:
        """Update session status in Redis."""
        key = self._session_key(session_id)

        exists = await self.redis.exists(key)
        if not exists:
            return False

        await self.redis.hset(key, mapping={
            "status": status.value,
            "updated_at": datetime.utcnow().isoformat(),
        })
        return True

    # =========================================================================
    # Turn Operations
    # =========================================================================

    async def save_turn(
        self,
        session_id: UUID,
        turn: ConversationTurn,
    ) -> None:
        """Save turn to Redis list."""
        key = self._turn_key(session_id)

        # Set turn number if not set
        if turn.turn_number == 0:
            turn.turn_number = await self.redis.llen(key) + 1

        turn_json = json.dumps(turn.to_dict(), default=str)
        await self.redis.rpush(key, turn_json)
        await self.redis.expire(key, int(self.session_ttl.total_seconds()))

        # Update session
        await self.update_session_status(session_id, SessionStatus.ACTIVE)

        logger.debug(f"Saved turn {turn.turn_number} for session {session_id}")

    async def get_turns(
        self,
        session_id: UUID,
        limit: Optional[int] = None,
    ) -> List[ConversationTurn]:
        """Get turns from Redis."""
        key = self._turn_key(session_id)

        if limit:
            turns_raw = await self.redis.lrange(key, -limit, -1)
        else:
            turns_raw = await self.redis.lrange(key, 0, -1)

        turns = []
        for turn_raw in turns_raw:
            turn_str = turn_raw.decode("utf-8") if isinstance(turn_raw, bytes) else turn_raw
            turn_data = json.loads(turn_str)
            turns.append(ConversationTurn.from_dict(turn_data))

        return turns

    async def get_turn(
        self,
        session_id: UUID,
        turn_number: int,
    ) -> Optional[ConversationTurn]:
        """Get a specific turn by number."""
        turns = await self.get_turns(session_id)
        for turn in turns:
            if turn.turn_number == turn_number:
                return turn
        return None

    # =========================================================================
    # Search Operations
    # =========================================================================

    async def search_by_content(
        self,
        query: str,
        session_ids: Optional[List[UUID]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search by content (simple implementation).

        Note: This is a basic implementation. For production,
        consider using Redis Search or Elasticsearch.
        """
        results = []
        query_lower = query.lower()

        # Determine which sessions to search
        if not session_ids:
            sessions = await self.list_sessions()
            session_ids = [s.session_id for s in sessions]

        for session_id in session_ids:
            turns = await self.get_turns(session_id)

            for turn in turns:
                if (query_lower in turn.user_input.lower() or
                    query_lower in turn.agent_response.lower()):
                    results.append({
                        "session_id": str(session_id),
                        "turn_number": turn.turn_number,
                        "user_input": turn.user_input,
                        "agent_response": turn.agent_response,
                        "timestamp": turn.timestamp.isoformat(),
                    })

                    if len(results) >= limit:
                        return results

        return results

    # =========================================================================
    # Statistics Operations
    # =========================================================================

    async def get_session_summary(
        self,
        session_id: UUID,
    ) -> Dict[str, Any]:
        """Get session summary."""
        session = await self.load_session(session_id)
        if not session:
            return {}

        return session.get_summary()

    async def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics."""
        sessions = await self.list_sessions()
        total_turns = 0
        status_counts: Dict[str, int] = {}

        for session in sessions:
            total_turns += len(session.turns)
            status_name = session.status.value
            status_counts[status_name] = status_counts.get(status_name, 0) + 1

        # Count messages
        pattern = f"{self.prefix}messages:*"
        cursor = 0
        total_messages = 0

        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            for key in keys:
                total_messages += await self.redis.llen(key)
            if cursor == 0:
                break

        return {
            "total_sessions": len(sessions),
            "total_turns": total_turns,
            "total_messages": total_messages,
            "sessions_by_status": status_counts,
            "avg_turns_per_session": total_turns / len(sessions) if sessions else 0,
        }

    # =========================================================================
    # Cleanup Operations
    # =========================================================================

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        sessions = await self.list_sessions()
        count = 0

        for session in sessions:
            if session.is_expired:
                await self.delete_session(session.session_id)
                count += 1
                logger.debug(f"Cleaned up expired session {session.session_id}")

        return count

    async def archive_session(self, session_id: UUID) -> bool:
        """Archive a session."""
        return await self.update_session_status(session_id, SessionStatus.ARCHIVED)
