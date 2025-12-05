# =============================================================================
# IPA Platform - In-Memory Conversation Memory Store
# =============================================================================
# Sprint 9: S9-4 ConversationMemoryStore (8 points)
#
# In-memory implementation of conversation memory storage.
# Suitable for testing and development environments.
# =============================================================================

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.domain.orchestration.memory.base import ConversationMemoryStore
from src.domain.orchestration.memory.models import (
    ConversationSession,
    ConversationTurn,
    MessageRecord,
    SessionStatus,
)

logger = logging.getLogger(__name__)


class InMemoryConversationMemoryStore(ConversationMemoryStore):
    """In-memory implementation of conversation memory storage.

    記憶體實現的對話記憶存儲。

    適用於測試和開發環境，不支持持久化。

    Example:
        ```python
        store = InMemoryConversationMemoryStore()

        # 保存會話
        session = ConversationSession(user_id="user-1")
        await store.save_session(session)

        # 保存輪次
        turn = ConversationTurn(
            user_input="Hello",
            agent_response="Hi there!"
        )
        await store.save_turn(session.session_id, turn)

        # 加載會話
        loaded = await store.load_session(session.session_id)
        ```
    """

    def __init__(self):
        """Initialize the in-memory store."""
        self._sessions: Dict[UUID, ConversationSession] = {}
        self._turns: Dict[UUID, List[ConversationTurn]] = defaultdict(list)
        self._messages: Dict[UUID, List[MessageRecord]] = defaultdict(list)

        logger.debug("InMemoryConversationMemoryStore initialized")

    # =========================================================================
    # Message Operations
    # =========================================================================

    async def add_message(self, message: MessageRecord) -> None:
        """Add a message to the store."""
        if message.group_id:
            self._messages[message.group_id].append(message)
            logger.debug(f"Added message {message.message_id} to group {message.group_id}")

    async def get_messages(
        self,
        group_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[MessageRecord]:
        """Get messages for a group."""
        messages = self._messages.get(group_id, [])
        return messages[offset:offset + limit]

    async def get_message_count(self, group_id: UUID) -> int:
        """Get the total message count for a group."""
        return len(self._messages.get(group_id, []))

    async def delete_messages(self, group_id: UUID) -> int:
        """Delete all messages for a group."""
        count = len(self._messages.get(group_id, []))
        if group_id in self._messages:
            del self._messages[group_id]
        return count

    # =========================================================================
    # Session Operations
    # =========================================================================

    async def save_session(self, session: ConversationSession) -> None:
        """Save a conversation session."""
        session.updated_at = datetime.utcnow()
        self._sessions[session.session_id] = session
        logger.debug(f"Saved session {session.session_id}")

    async def load_session(self, session_id: UUID) -> Optional[ConversationSession]:
        """Load a conversation session."""
        session = self._sessions.get(session_id)
        if session:
            # Load turns into session
            session.turns = self._turns.get(session_id, []).copy()
        return session

    async def delete_session(self, session_id: UUID) -> bool:
        """Delete a conversation session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            if session_id in self._turns:
                del self._turns[session_id]
            logger.debug(f"Deleted session {session_id}")
            return True
        return False

    async def list_sessions(
        self,
        user_id: Optional[str] = None,
        status: Optional[SessionStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ConversationSession]:
        """List conversation sessions."""
        sessions = list(self._sessions.values())

        # Apply filters
        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]
        if status:
            sessions = [s for s in sessions if s.status == status]

        # Sort by updated_at descending
        sessions.sort(key=lambda s: s.updated_at, reverse=True)

        # Apply pagination
        return sessions[offset:offset + limit]

    async def update_session_status(
        self,
        session_id: UUID,
        status: SessionStatus,
    ) -> bool:
        """Update the status of a session."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        session.status = status
        session.updated_at = datetime.utcnow()
        return True

    # =========================================================================
    # Turn Operations
    # =========================================================================

    async def save_turn(
        self,
        session_id: UUID,
        turn: ConversationTurn,
    ) -> None:
        """Save a conversation turn."""
        # Set turn number if not set
        if turn.turn_number == 0:
            turn.turn_number = len(self._turns[session_id]) + 1

        self._turns[session_id].append(turn)

        # Update session
        if session_id in self._sessions:
            self._sessions[session_id].updated_at = datetime.utcnow()

        logger.debug(f"Saved turn {turn.turn_number} for session {session_id}")

    async def get_turns(
        self,
        session_id: UUID,
        limit: Optional[int] = None,
    ) -> List[ConversationTurn]:
        """Get turns for a session."""
        turns = self._turns.get(session_id, [])
        if limit:
            return turns[-limit:]
        return turns.copy()

    async def get_turn(
        self,
        session_id: UUID,
        turn_number: int,
    ) -> Optional[ConversationTurn]:
        """Get a specific turn by number."""
        turns = self._turns.get(session_id, [])
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
        """Search conversations by content."""
        results = []
        query_lower = query.lower()

        # Determine which sessions to search
        search_sessions = session_ids or list(self._sessions.keys())

        for session_id in search_sessions:
            turns = self._turns.get(session_id, [])

            for turn in turns:
                # Search in user input and agent response
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
        """Get a summary of a session."""
        session = await self.load_session(session_id)
        if not session:
            return {}

        return session.get_summary()

    async def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics for the memory store."""
        total_sessions = len(self._sessions)
        total_turns = sum(len(turns) for turns in self._turns.values())
        total_messages = sum(len(msgs) for msgs in self._messages.values())

        status_counts: Dict[str, int] = {}
        for session in self._sessions.values():
            status_name = session.status.value
            status_counts[status_name] = status_counts.get(status_name, 0) + 1

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
        now = datetime.utcnow()
        expired_ids = []

        for session_id, session in self._sessions.items():
            if session.is_expired:
                expired_ids.append(session_id)

        for session_id in expired_ids:
            await self.delete_session(session_id)
            logger.debug(f"Cleaned up expired session {session_id}")

        return len(expired_ids)

    async def archive_session(self, session_id: UUID) -> bool:
        """Archive a session."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        session.status = SessionStatus.ARCHIVED
        session.updated_at = datetime.utcnow()
        logger.debug(f"Archived session {session_id}")
        return True

    # =========================================================================
    # Additional In-Memory Methods
    # =========================================================================

    def clear(self) -> None:
        """Clear all data from the store.

        清除所有數據。
        """
        self._sessions.clear()
        self._turns.clear()
        self._messages.clear()
        logger.debug("Cleared all data from in-memory store")

    def get_session_count(self) -> int:
        """Get the total number of sessions.

        獲取會話總數。
        """
        return len(self._sessions)

    def get_total_turn_count(self) -> int:
        """Get the total number of turns across all sessions.

        獲取所有會話的輪次總數。
        """
        return sum(len(turns) for turns in self._turns.values())
