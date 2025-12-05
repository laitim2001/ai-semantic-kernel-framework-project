# =============================================================================
# IPA Platform - Conversation Memory Store Base
# =============================================================================
# Sprint 9: S9-4 ConversationMemoryStore (8 points)
#
# Abstract base class for conversation memory storage implementations.
# =============================================================================

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.domain.orchestration.memory.models import (
    ConversationSession,
    ConversationTurn,
    MessageRecord,
    SessionStatus,
)


class ConversationMemoryStore(ABC):
    """Abstract base class for conversation memory storage.

    對話記憶存儲抽象基類。

    提供統一的接口用於:
    - 訊息存儲和檢索
    - 會話管理
    - 輪次存儲
    - 內容搜索
    - 會話統計

    實現類:
    - InMemoryConversationMemoryStore: 記憶體實現，用於測試
    - RedisConversationMemoryStore: Redis 實現，用於快速存取
    - PostgresConversationMemoryStore: PostgreSQL 實現，用於持久化
    """

    # =========================================================================
    # Message Operations
    # =========================================================================

    @abstractmethod
    async def add_message(self, message: MessageRecord) -> None:
        """Add a message to the store.

        添加訊息到存儲。

        Args:
            message: 訊息記錄
        """
        pass

    @abstractmethod
    async def get_messages(
        self,
        group_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[MessageRecord]:
        """Get messages for a group.

        獲取群組的訊息。

        Args:
            group_id: 群組 ID
            limit: 最大返回數量
            offset: 偏移量

        Returns:
            訊息記錄列表
        """
        pass

    @abstractmethod
    async def get_message_count(self, group_id: UUID) -> int:
        """Get the total message count for a group.

        獲取群組的訊息總數。

        Args:
            group_id: 群組 ID

        Returns:
            訊息數量
        """
        pass

    @abstractmethod
    async def delete_messages(self, group_id: UUID) -> int:
        """Delete all messages for a group.

        刪除群組的所有訊息。

        Args:
            group_id: 群組 ID

        Returns:
            刪除的訊息數量
        """
        pass

    # =========================================================================
    # Session Operations
    # =========================================================================

    @abstractmethod
    async def save_session(self, session: ConversationSession) -> None:
        """Save a conversation session.

        保存對話會話。

        Args:
            session: 會話對象
        """
        pass

    @abstractmethod
    async def load_session(self, session_id: UUID) -> Optional[ConversationSession]:
        """Load a conversation session.

        加載對話會話。

        Args:
            session_id: 會話 ID

        Returns:
            會話對象，如果不存在則返回 None
        """
        pass

    @abstractmethod
    async def delete_session(self, session_id: UUID) -> bool:
        """Delete a conversation session.

        刪除對話會話。

        Args:
            session_id: 會話 ID

        Returns:
            是否成功刪除
        """
        pass

    @abstractmethod
    async def list_sessions(
        self,
        user_id: Optional[str] = None,
        status: Optional[SessionStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ConversationSession]:
        """List conversation sessions.

        列出對話會話。

        Args:
            user_id: 過濾用戶 ID
            status: 過濾狀態
            limit: 最大返回數量
            offset: 偏移量

        Returns:
            會話列表
        """
        pass

    @abstractmethod
    async def update_session_status(
        self,
        session_id: UUID,
        status: SessionStatus,
    ) -> bool:
        """Update the status of a session.

        更新會話狀態。

        Args:
            session_id: 會話 ID
            status: 新狀態

        Returns:
            是否成功更新
        """
        pass

    # =========================================================================
    # Turn Operations
    # =========================================================================

    @abstractmethod
    async def save_turn(
        self,
        session_id: UUID,
        turn: ConversationTurn,
    ) -> None:
        """Save a conversation turn.

        保存對話輪次。

        Args:
            session_id: 會話 ID
            turn: 輪次對象
        """
        pass

    @abstractmethod
    async def get_turns(
        self,
        session_id: UUID,
        limit: Optional[int] = None,
    ) -> List[ConversationTurn]:
        """Get turns for a session.

        獲取會話的輪次。

        Args:
            session_id: 會話 ID
            limit: 最大返回數量

        Returns:
            輪次列表
        """
        pass

    @abstractmethod
    async def get_turn(
        self,
        session_id: UUID,
        turn_number: int,
    ) -> Optional[ConversationTurn]:
        """Get a specific turn by number.

        獲取特定編號的輪次。

        Args:
            session_id: 會話 ID
            turn_number: 輪次編號

        Returns:
            輪次對象，如果不存在則返回 None
        """
        pass

    # =========================================================================
    # Search Operations
    # =========================================================================

    @abstractmethod
    async def search_by_content(
        self,
        query: str,
        session_ids: Optional[List[UUID]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search conversations by content.

        按內容搜索對話。

        Args:
            query: 搜索查詢
            session_ids: 限制搜索的會話 ID 列表
            limit: 最大返回數量

        Returns:
            搜索結果列表
        """
        pass

    # =========================================================================
    # Statistics Operations
    # =========================================================================

    @abstractmethod
    async def get_session_summary(
        self,
        session_id: UUID,
    ) -> Dict[str, Any]:
        """Get a summary of a session.

        獲取會話摘要。

        Args:
            session_id: 會話 ID

        Returns:
            會話摘要字典
        """
        pass

    @abstractmethod
    async def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics for the memory store.

        獲取整體統計信息。

        Returns:
            統計信息字典
        """
        pass

    # =========================================================================
    # Cleanup Operations
    # =========================================================================

    @abstractmethod
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions.

        清理過期的會話。

        Returns:
            清理的會話數量
        """
        pass

    @abstractmethod
    async def archive_session(self, session_id: UUID) -> bool:
        """Archive a session.

        歸檔會話。

        Args:
            session_id: 會話 ID

        Returns:
            是否成功歸檔
        """
        pass

    # =========================================================================
    # Context Operations
    # =========================================================================

    async def update_session_context(
        self,
        session_id: UUID,
        context_updates: Dict[str, Any],
    ) -> bool:
        """Update the context of a session.

        更新會話上下文。

        Args:
            session_id: 會話 ID
            context_updates: 上下文更新

        Returns:
            是否成功更新
        """
        session = await self.load_session(session_id)
        if not session:
            return False

        session.context.update(context_updates)
        session.updated_at = datetime.utcnow()
        await self.save_session(session)
        return True

    async def get_session_context(
        self,
        session_id: UUID,
    ) -> Optional[Dict[str, Any]]:
        """Get the context of a session.

        獲取會話上下文。

        Args:
            session_id: 會話 ID

        Returns:
            會話上下文字典，如果會話不存在則返回 None
        """
        session = await self.load_session(session_id)
        return session.context if session else None

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def session_exists(self, session_id: UUID) -> bool:
        """Check if a session exists.

        檢查會話是否存在。

        Args:
            session_id: 會話 ID

        Returns:
            是否存在
        """
        session = await self.load_session(session_id)
        return session is not None

    async def get_latest_sessions(
        self,
        limit: int = 10,
    ) -> List[ConversationSession]:
        """Get the most recently updated sessions.

        獲取最近更新的會話。

        Args:
            limit: 最大返回數量

        Returns:
            會話列表
        """
        sessions = await self.list_sessions(limit=limit)
        return sorted(sessions, key=lambda s: s.updated_at, reverse=True)[:limit]
