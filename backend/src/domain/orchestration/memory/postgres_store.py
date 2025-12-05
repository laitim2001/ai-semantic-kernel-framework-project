# =============================================================================
# IPA Platform - PostgreSQL Conversation Memory Store
# =============================================================================
# Sprint 9: S9-4 ConversationMemoryStore (8 points)
#
# PostgreSQL-based implementation of conversation memory storage.
# Suitable for production environments requiring persistence and complex queries.
# =============================================================================

from __future__ import annotations

import json
import logging
from datetime import datetime
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


class DatabaseSessionProtocol(Protocol):
    """Protocol for database session interface.

    資料庫會話協議。
    """

    async def execute(self, query: str, *args: Any) -> None: ...
    async def fetch_all(self, query: str, *args: Any) -> List[Any]: ...
    async def fetch_one(self, query: str, *args: Any) -> Optional[Any]: ...


class PostgresConversationMemoryStore(ConversationMemoryStore):
    """PostgreSQL-based implementation of conversation memory storage.

    基於 PostgreSQL 的對話記憶存儲實現。

    適用於需要持久化存儲、複雜查詢和事務支持的生產環境。

    Required Tables:
    - conversation_messages: 訊息表
    - conversation_sessions: 會話表
    - conversation_turns: 輪次表

    Example:
        ```python
        from sqlalchemy.ext.asyncio import AsyncSession

        async with AsyncSession(engine) as session:
            store = PostgresConversationMemoryStore(session)
            await store.save_session(conversation_session)
        ```
    """

    def __init__(self, db_session: Any):
        """Initialize the PostgreSQL store.

        Args:
            db_session: 資料庫會話
        """
        self.db = db_session
        logger.debug("PostgresConversationMemoryStore initialized")

    # =========================================================================
    # Message Operations
    # =========================================================================

    async def add_message(self, message: MessageRecord) -> None:
        """Add message to database."""
        query = """
            INSERT INTO conversation_messages
            (id, group_id, sender_id, sender_name, content, message_type,
             timestamp, metadata, reply_to)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """
        await self.db.execute(
            query,
            message.message_id,
            message.group_id,
            message.sender_id,
            message.sender_name,
            message.content,
            message.message_type,
            message.timestamp,
            json.dumps(message.metadata),
            message.reply_to,
        )
        logger.debug(f"Added message {message.message_id} to database")

    async def get_messages(
        self,
        group_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[MessageRecord]:
        """Get messages from database."""
        query = """
            SELECT id, group_id, sender_id, sender_name, content, message_type,
                   timestamp, metadata, reply_to
            FROM conversation_messages
            WHERE group_id = $1
            ORDER BY timestamp ASC
            LIMIT $2 OFFSET $3
        """
        rows = await self.db.fetch_all(query, group_id, limit, offset)

        messages = []
        for row in rows:
            messages.append(MessageRecord(
                message_id=row["id"],
                group_id=row["group_id"],
                sender_id=row["sender_id"],
                sender_name=row["sender_name"],
                content=row["content"],
                message_type=row["message_type"],
                timestamp=row["timestamp"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                reply_to=row["reply_to"],
            ))

        return messages

    async def get_message_count(self, group_id: UUID) -> int:
        """Get message count from database."""
        query = """
            SELECT COUNT(*) as count
            FROM conversation_messages
            WHERE group_id = $1
        """
        row = await self.db.fetch_one(query, group_id)
        return row["count"] if row else 0

    async def delete_messages(self, group_id: UUID) -> int:
        """Delete messages from database."""
        count = await self.get_message_count(group_id)
        query = "DELETE FROM conversation_messages WHERE group_id = $1"
        await self.db.execute(query, group_id)
        return count

    # =========================================================================
    # Session Operations
    # =========================================================================

    async def save_session(self, session: ConversationSession) -> None:
        """Save session to database with upsert."""
        query = """
            INSERT INTO conversation_sessions
            (session_id, user_id, workflow_id, status, context, created_at,
             updated_at, expires_at, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (session_id) DO UPDATE SET
                status = EXCLUDED.status,
                context = EXCLUDED.context,
                updated_at = EXCLUDED.updated_at,
                expires_at = EXCLUDED.expires_at,
                metadata = EXCLUDED.metadata
        """
        await self.db.execute(
            query,
            session.session_id,
            session.user_id,
            session.workflow_id,
            session.status.value,
            json.dumps(session.context),
            session.created_at,
            datetime.utcnow(),
            session.expires_at,
            json.dumps(session.metadata),
        )
        logger.debug(f"Saved session {session.session_id} to database")

    async def load_session(self, session_id: UUID) -> Optional[ConversationSession]:
        """Load session from database."""
        query = """
            SELECT session_id, user_id, workflow_id, status, context,
                   created_at, updated_at, expires_at, metadata
            FROM conversation_sessions
            WHERE session_id = $1
        """
        row = await self.db.fetch_one(query, session_id)

        if not row:
            return None

        # Load turns
        turns = await self.get_turns(session_id)

        return ConversationSession(
            session_id=row["session_id"],
            user_id=row["user_id"],
            workflow_id=row["workflow_id"],
            status=SessionStatus(row["status"]),
            turns=turns,
            context=json.loads(row["context"]) if row["context"] else {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            expires_at=row["expires_at"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    async def delete_session(self, session_id: UUID) -> bool:
        """Delete session from database."""
        # Delete turns first
        await self.db.execute(
            "DELETE FROM conversation_turns WHERE session_id = $1",
            session_id,
        )

        # Delete session
        query = "DELETE FROM conversation_sessions WHERE session_id = $1"
        await self.db.execute(query, session_id)

        logger.debug(f"Deleted session {session_id} from database")
        return True

    async def list_sessions(
        self,
        user_id: Optional[str] = None,
        status: Optional[SessionStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ConversationSession]:
        """List sessions from database."""
        conditions = []
        params = []
        param_count = 0

        if user_id:
            param_count += 1
            conditions.append(f"user_id = ${param_count}")
            params.append(user_id)

        if status:
            param_count += 1
            conditions.append(f"status = ${param_count}")
            params.append(status.value)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        param_count += 1
        limit_param = param_count
        param_count += 1
        offset_param = param_count

        query = f"""
            SELECT session_id, user_id, workflow_id, status, context,
                   created_at, updated_at, expires_at, metadata
            FROM conversation_sessions
            WHERE {where_clause}
            ORDER BY updated_at DESC
            LIMIT ${limit_param} OFFSET ${offset_param}
        """

        params.extend([limit, offset])
        rows = await self.db.fetch_all(query, *params)

        sessions = []
        for row in rows:
            # Load turns for each session
            turns = await self.get_turns(row["session_id"])

            sessions.append(ConversationSession(
                session_id=row["session_id"],
                user_id=row["user_id"],
                workflow_id=row["workflow_id"],
                status=SessionStatus(row["status"]),
                turns=turns,
                context=json.loads(row["context"]) if row["context"] else {},
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                expires_at=row["expires_at"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            ))

        return sessions

    async def update_session_status(
        self,
        session_id: UUID,
        status: SessionStatus,
    ) -> bool:
        """Update session status in database."""
        query = """
            UPDATE conversation_sessions
            SET status = $1, updated_at = $2
            WHERE session_id = $3
        """
        await self.db.execute(query, status.value, datetime.utcnow(), session_id)
        return True

    # =========================================================================
    # Turn Operations
    # =========================================================================

    async def save_turn(
        self,
        session_id: UUID,
        turn: ConversationTurn,
    ) -> None:
        """Save turn to database."""
        # Get turn number if not set
        if turn.turn_number == 0:
            count_query = """
                SELECT COUNT(*) as count
                FROM conversation_turns
                WHERE session_id = $1
            """
            row = await self.db.fetch_one(count_query, session_id)
            turn.turn_number = (row["count"] if row else 0) + 1

        query = """
            INSERT INTO conversation_turns
            (turn_id, session_id, turn_number, user_input, agent_response,
             agent_id, timestamp, processing_time_ms, tokens_used, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """
        await self.db.execute(
            query,
            turn.turn_id,
            session_id,
            turn.turn_number,
            turn.user_input,
            turn.agent_response,
            turn.agent_id,
            turn.timestamp,
            turn.processing_time_ms,
            turn.tokens_used,
            json.dumps(turn.metadata),
        )

        # Update session timestamp
        await self.db.execute(
            "UPDATE conversation_sessions SET updated_at = $1 WHERE session_id = $2",
            datetime.utcnow(),
            session_id,
        )

        logger.debug(f"Saved turn {turn.turn_number} for session {session_id}")

    async def get_turns(
        self,
        session_id: UUID,
        limit: Optional[int] = None,
    ) -> List[ConversationTurn]:
        """Get turns from database."""
        if limit:
            query = """
                SELECT turn_id, turn_number, user_input, agent_response,
                       agent_id, timestamp, processing_time_ms, tokens_used, metadata
                FROM conversation_turns
                WHERE session_id = $1
                ORDER BY turn_number DESC
                LIMIT $2
            """
            rows = await self.db.fetch_all(query, session_id, limit)
            rows = list(reversed(rows))  # Restore order
        else:
            query = """
                SELECT turn_id, turn_number, user_input, agent_response,
                       agent_id, timestamp, processing_time_ms, tokens_used, metadata
                FROM conversation_turns
                WHERE session_id = $1
                ORDER BY turn_number ASC
            """
            rows = await self.db.fetch_all(query, session_id)

        turns = []
        for row in rows:
            turns.append(ConversationTurn(
                turn_id=row["turn_id"],
                turn_number=row["turn_number"],
                user_input=row["user_input"],
                agent_response=row["agent_response"],
                agent_id=row["agent_id"],
                timestamp=row["timestamp"],
                processing_time_ms=row["processing_time_ms"],
                tokens_used=row["tokens_used"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            ))

        return turns

    async def get_turn(
        self,
        session_id: UUID,
        turn_number: int,
    ) -> Optional[ConversationTurn]:
        """Get specific turn from database."""
        query = """
            SELECT turn_id, turn_number, user_input, agent_response,
                   agent_id, timestamp, processing_time_ms, tokens_used, metadata
            FROM conversation_turns
            WHERE session_id = $1 AND turn_number = $2
        """
        row = await self.db.fetch_one(query, session_id, turn_number)

        if not row:
            return None

        return ConversationTurn(
            turn_id=row["turn_id"],
            turn_number=row["turn_number"],
            user_input=row["user_input"],
            agent_response=row["agent_response"],
            agent_id=row["agent_id"],
            timestamp=row["timestamp"],
            processing_time_ms=row["processing_time_ms"],
            tokens_used=row["tokens_used"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    # =========================================================================
    # Search Operations
    # =========================================================================

    async def search_by_content(
        self,
        query: str,
        session_ids: Optional[List[UUID]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search by content using full-text search."""
        conditions = ["(user_input ILIKE $1 OR agent_response ILIKE $1)"]
        params = [f"%{query}%"]
        param_count = 1

        if session_ids:
            placeholders = ", ".join(f"${i}" for i in range(2, len(session_ids) + 2))
            conditions.append(f"session_id IN ({placeholders})")
            params.extend([str(sid) for sid in session_ids])
            param_count += len(session_ids)

        where_clause = " AND ".join(conditions)
        param_count += 1

        search_query = f"""
            SELECT session_id, turn_number, user_input, agent_response, timestamp
            FROM conversation_turns
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ${param_count}
        """
        params.append(limit)

        rows = await self.db.fetch_all(search_query, *params)

        return [
            {
                "session_id": str(row["session_id"]),
                "turn_number": row["turn_number"],
                "user_input": row["user_input"],
                "agent_response": row["agent_response"],
                "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None,
            }
            for row in rows
        ]

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
        """Get overall statistics from database."""
        # Count sessions by status
        status_query = """
            SELECT status, COUNT(*) as count
            FROM conversation_sessions
            GROUP BY status
        """
        status_rows = await self.db.fetch_all(status_query)
        status_counts = {row["status"]: row["count"] for row in status_rows}

        # Total counts
        session_count_row = await self.db.fetch_one(
            "SELECT COUNT(*) as count FROM conversation_sessions"
        )
        turn_count_row = await self.db.fetch_one(
            "SELECT COUNT(*) as count FROM conversation_turns"
        )
        message_count_row = await self.db.fetch_one(
            "SELECT COUNT(*) as count FROM conversation_messages"
        )

        total_sessions = session_count_row["count"] if session_count_row else 0
        total_turns = turn_count_row["count"] if turn_count_row else 0
        total_messages = message_count_row["count"] if message_count_row else 0

        return {
            "total_sessions": total_sessions,
            "total_turns": total_turns,
            "total_messages": total_messages,
            "sessions_by_status": status_counts,
            "avg_turns_per_session": total_turns / total_sessions if total_sessions else 0,
        }

    # =========================================================================
    # Cleanup Operations
    # =========================================================================

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        query = """
            DELETE FROM conversation_sessions
            WHERE expires_at IS NOT NULL AND expires_at < $1
            RETURNING session_id
        """
        rows = await self.db.fetch_all(query, datetime.utcnow())

        # Delete associated turns
        for row in rows:
            await self.db.execute(
                "DELETE FROM conversation_turns WHERE session_id = $1",
                row["session_id"],
            )

        count = len(rows)
        if count > 0:
            logger.info(f"Cleaned up {count} expired sessions")

        return count

    async def archive_session(self, session_id: UUID) -> bool:
        """Archive a session."""
        return await self.update_session_status(session_id, SessionStatus.ARCHIVED)
