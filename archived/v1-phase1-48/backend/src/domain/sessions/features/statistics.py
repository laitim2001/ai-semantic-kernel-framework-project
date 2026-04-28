"""
Statistics Service

Service for session statistics with lazy calculation and caching.
Based on D44-4 decision: Lazy calculation + cache.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import logging

from ..models import MessageRole

logger = logging.getLogger(__name__)


@dataclass
class MessageStatistics:
    """訊息統計"""
    total_count: int = 0
    user_count: int = 0
    assistant_count: int = 0
    system_count: int = 0
    with_attachments: int = 0
    with_tool_calls: int = 0
    avg_length: float = 0.0
    total_tokens: int = 0


@dataclass
class SessionStatistics:
    """Session 統計資料"""
    session_id: str = ""
    # 訊息統計
    messages: MessageStatistics = field(default_factory=MessageStatistics)
    # 時間統計
    created_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    duration_minutes: int = 0
    # 附件統計
    attachment_count: int = 0
    attachment_size_bytes: int = 0
    # 對話統計
    conversation_turns: int = 0
    avg_response_time_ms: int = 0
    # 書籤統計
    bookmark_count: int = 0
    # 標籤
    tags: List[str] = field(default_factory=list)
    # 快取狀態
    calculated_at: datetime = field(default_factory=datetime.now)
    is_stale: bool = False


@dataclass
class UserStatistics:
    """用戶統計資料"""
    user_id: str = ""
    total_sessions: int = 0
    total_messages: int = 0
    total_tokens: int = 0
    total_attachments: int = 0
    active_sessions: int = 0
    avg_session_duration_minutes: float = 0.0
    most_used_tags: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    last_active_at: Optional[datetime] = None


class StatisticsService:
    """統計服務

    提供 Session 統計功能，使用延遲計算和快取策略。

    功能:
    - Session 統計計算
    - 用戶統計計算
    - 快取管理
    - 統計匯出
    """

    # 快取 TTL (秒)
    CACHE_TTL = 300  # 5 分鐘

    # 過期閾值
    STALE_THRESHOLD = 600  # 10 分鐘

    def __init__(
        self,
        repository: Optional[Any] = None,
        cache: Optional[Any] = None
    ):
        """
        初始化統計服務

        Args:
            repository: 資料庫存儲實例
            cache: 快取服務實例
        """
        self._repository = repository
        self._cache = cache

    async def get_statistics(
        self,
        session_id: str,
        force_refresh: bool = False
    ) -> SessionStatistics:
        """
        獲取 Session 統計

        使用延遲計算策略：
        1. 先檢查快取
        2. 快取有效則返回
        3. 否則計算並快取

        Args:
            session_id: Session ID
            force_refresh: 強制重新計算

        Returns:
            SessionStatistics: 統計結果
        """
        cache_key = f"stats:{session_id}"

        try:
            # 如果不強制刷新，嘗試從快取獲取
            if not force_refresh and self._cache:
                cached = await self._cache.get(cache_key)
                if cached:
                    # 檢查是否過期
                    if self._is_stale(cached):
                        cached.is_stale = True
                    return cached

            # 計算統計
            stats = await self._calculate_session_statistics(session_id)

            # 快取結果
            if self._cache:
                await self._cache.set(cache_key, stats, ttl=self.CACHE_TTL)

            logger.debug(f"Calculated statistics for session {session_id}")
            return stats

        except Exception as e:
            logger.error(f"Failed to get statistics for session {session_id}: {e}")
            return SessionStatistics(session_id=session_id)

    async def get_user_statistics(
        self,
        user_id: str,
        force_refresh: bool = False
    ) -> UserStatistics:
        """
        獲取用戶統計

        Args:
            user_id: 用戶 ID
            force_refresh: 強制重新計算

        Returns:
            UserStatistics: 統計結果
        """
        cache_key = f"user_stats:{user_id}"

        try:
            if not force_refresh and self._cache:
                cached = await self._cache.get(cache_key)
                if cached:
                    return cached

            stats = await self._calculate_user_statistics(user_id)

            if self._cache:
                await self._cache.set(cache_key, stats, ttl=self.CACHE_TTL)

            return stats

        except Exception as e:
            logger.error(f"Failed to get user statistics: {e}")
            return UserStatistics(user_id=user_id)

    async def refresh_statistics(self, session_id: str) -> SessionStatistics:
        """強制刷新統計"""
        return await self.get_statistics(session_id, force_refresh=True)

    async def invalidate_statistics(self, session_id: str) -> None:
        """使統計快取失效"""
        if self._cache:
            await self._cache.delete(f"stats:{session_id}")

    async def invalidate_user_statistics(self, user_id: str) -> None:
        """使用戶統計快取失效"""
        if self._cache:
            await self._cache.delete(f"user_stats:{user_id}")

    async def _calculate_session_statistics(
        self,
        session_id: str
    ) -> SessionStatistics:
        """計算 Session 統計"""
        stats = SessionStatistics(session_id=session_id)

        if not self._repository:
            return stats

        try:
            # 獲取 Session 基本信息
            session = await self._repository.get_session(session_id)
            if session:
                stats.created_at = session.created_at

            # 獲取訊息統計
            messages = await self._repository.get_all_messages(session_id)

            if messages:
                msg_stats = MessageStatistics()
                msg_stats.total_count = len(messages)

                total_length = 0
                prev_timestamp = None
                response_times = []

                for msg in messages:
                    # 計算角色分佈
                    if msg.role == MessageRole.USER:
                        msg_stats.user_count += 1
                    elif msg.role == MessageRole.ASSISTANT:
                        msg_stats.assistant_count += 1
                        # 計算響應時間
                        if prev_timestamp:
                            response_time = (msg.created_at - prev_timestamp).total_seconds() * 1000
                            response_times.append(response_time)
                    elif msg.role == MessageRole.SYSTEM:
                        msg_stats.system_count += 1

                    # 內容長度
                    total_length += len(msg.content) if msg.content else 0

                    # 附件
                    if hasattr(msg, 'attachments') and msg.attachments:
                        msg_stats.with_attachments += 1

                    # 工具調用
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        msg_stats.with_tool_calls += 1

                    # Token 統計
                    if hasattr(msg, 'metadata') and msg.metadata:
                        msg_stats.total_tokens += msg.metadata.get('tokens', 0)

                    prev_timestamp = msg.created_at

                # 計算平均值
                if msg_stats.total_count > 0:
                    msg_stats.avg_length = total_length / msg_stats.total_count

                stats.messages = msg_stats
                stats.last_message_at = messages[-1].created_at if messages else None

                # 計算持續時間
                if stats.created_at and stats.last_message_at:
                    duration = stats.last_message_at - stats.created_at
                    stats.duration_minutes = int(duration.total_seconds() / 60)

                # 計算對話輪次
                stats.conversation_turns = min(msg_stats.user_count, msg_stats.assistant_count)

                # 計算平均響應時間
                if response_times:
                    stats.avg_response_time_ms = int(sum(response_times) / len(response_times))

            # 獲取附件統計
            attachments = await self._repository.get_session_attachments(session_id)
            if attachments:
                stats.attachment_count = len(attachments)
                stats.attachment_size_bytes = sum(
                    a.size for a in attachments if hasattr(a, 'size')
                )

            # 獲取書籤統計
            bookmark_count = await self._repository.count_session_bookmarks(session_id)
            stats.bookmark_count = bookmark_count

            # 獲取標籤
            tags = await self._repository.get_session_tags(session_id)
            stats.tags = [t.name for t in tags] if tags else []

            stats.calculated_at = datetime.now()
            return stats

        except Exception as e:
            logger.error(f"Failed to calculate session statistics: {e}")
            return stats

    async def _calculate_user_statistics(
        self,
        user_id: str
    ) -> UserStatistics:
        """計算用戶統計"""
        stats = UserStatistics(user_id=user_id)

        if not self._repository:
            return stats

        try:
            # 獲取用戶 Sessions
            sessions = await self._repository.get_user_sessions(user_id)

            if sessions:
                stats.total_sessions = len(sessions)
                stats.created_at = min(s.created_at for s in sessions if s.created_at)

                active_count = 0
                total_duration = 0
                total_messages = 0
                total_tokens = 0
                total_attachments = 0

                for session in sessions:
                    # 檢查活躍狀態
                    if session.status == "active":
                        active_count += 1

                    # 累計統計
                    session_stats = await self.get_statistics(session.id)
                    total_messages += session_stats.messages.total_count
                    total_tokens += session_stats.messages.total_tokens
                    total_attachments += session_stats.attachment_count
                    total_duration += session_stats.duration_minutes

                    if session_stats.last_message_at:
                        if not stats.last_active_at or session_stats.last_message_at > stats.last_active_at:
                            stats.last_active_at = session_stats.last_message_at

                stats.active_sessions = active_count
                stats.total_messages = total_messages
                stats.total_tokens = total_tokens
                stats.total_attachments = total_attachments

                if stats.total_sessions > 0:
                    stats.avg_session_duration_minutes = total_duration / stats.total_sessions

            # 獲取最常用標籤
            tags = await self._repository.get_user_popular_tags(user_id, limit=5)
            stats.most_used_tags = [t.name for t in tags] if tags else []

            return stats

        except Exception as e:
            logger.error(f"Failed to calculate user statistics: {e}")
            return stats

    def _is_stale(self, stats: SessionStatistics) -> bool:
        """檢查統計是否過期"""
        if not stats.calculated_at:
            return True

        age = (datetime.now() - stats.calculated_at).total_seconds()
        return age > self.STALE_THRESHOLD

    async def get_statistics_summary(
        self,
        session_ids: List[str]
    ) -> Dict[str, SessionStatistics]:
        """
        批量獲取統計摘要

        Args:
            session_ids: Session ID 列表

        Returns:
            Dict: Session ID -> 統計結果
        """
        results = {}
        for session_id in session_ids:
            results[session_id] = await self.get_statistics(session_id)
        return results

    async def export_statistics(
        self,
        session_id: str,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        匯出統計資料

        Args:
            session_id: Session ID
            format: 匯出格式

        Returns:
            Dict: 統計資料
        """
        stats = await self.get_statistics(session_id, force_refresh=True)

        return {
            "session_id": stats.session_id,
            "messages": {
                "total": stats.messages.total_count,
                "user": stats.messages.user_count,
                "assistant": stats.messages.assistant_count,
                "system": stats.messages.system_count,
                "with_attachments": stats.messages.with_attachments,
                "with_tool_calls": stats.messages.with_tool_calls,
                "avg_length": round(stats.messages.avg_length, 2),
                "total_tokens": stats.messages.total_tokens
            },
            "timeline": {
                "created_at": stats.created_at.isoformat() if stats.created_at else None,
                "last_message_at": stats.last_message_at.isoformat() if stats.last_message_at else None,
                "duration_minutes": stats.duration_minutes
            },
            "attachments": {
                "count": stats.attachment_count,
                "size_bytes": stats.attachment_size_bytes
            },
            "conversation": {
                "turns": stats.conversation_turns,
                "avg_response_time_ms": stats.avg_response_time_ms
            },
            "bookmarks": stats.bookmark_count,
            "tags": stats.tags,
            "calculated_at": stats.calculated_at.isoformat()
        }
