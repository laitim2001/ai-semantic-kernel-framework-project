"""
Session Cache

Redis-based caching for Session data to reduce database load.
Implements write-through caching strategy.
"""

from typing import Optional, List, Dict, Any
from dataclasses import asdict
import json
from datetime import datetime

from redis.asyncio import Redis

from src.domain.sessions.models import (
    Session,
    SessionStatus,
    SessionConfig,
    Message,
    MessageRole,
    Attachment,
    ToolCall,
)


class SessionCache:
    """Session Redis 快取

    快取策略:
    - Session 資料快取 1 小時
    - 活躍 Session 列表快取 5 分鐘
    - 訊息快取 30 分鐘
    """

    # 快取 TTL (秒)
    SESSION_TTL = 3600          # 1 小時
    MESSAGE_TTL = 1800          # 30 分鐘
    LIST_TTL = 300              # 5 分鐘

    # Key 前綴
    SESSION_PREFIX = "session:"
    MESSAGES_PREFIX = "session:messages:"
    USER_SESSIONS_PREFIX = "user:sessions:"

    def __init__(self, redis: Redis, default_ttl: int = 3600):
        """初始化快取

        Args:
            redis: Redis 客戶端
            default_ttl: 預設 TTL (秒)
        """
        self._redis = redis
        self._ttl = default_ttl

    # ===== Session 快取 =====

    async def get_session(self, session_id: str) -> Optional[Session]:
        """從快取獲取 Session

        Args:
            session_id: Session ID

        Returns:
            Session 或 None
        """
        key = f"{self.SESSION_PREFIX}{session_id}"
        data = await self._redis.get(key)
        if data is None:
            return None

        try:
            session_dict = json.loads(data)
            return Session.from_dict(session_dict)
        except (json.JSONDecodeError, KeyError):
            # 快取數據損壞，刪除並返回 None
            await self.delete_session(session_id)
            return None

    async def set_session(self, session: Session, ttl: Optional[int] = None) -> None:
        """設置 Session 快取

        Args:
            session: Session 物件
            ttl: 可選 TTL (秒)
        """
        key = f"{self.SESSION_PREFIX}{session.id}"
        data = json.dumps(session.to_dict(), default=str)
        await self._redis.setex(
            key,
            ttl or self.SESSION_TTL,
            data
        )

    async def delete_session(self, session_id: str) -> None:
        """刪除 Session 快取

        Args:
            session_id: Session ID
        """
        # 刪除 Session 和相關的訊息快取
        session_key = f"{self.SESSION_PREFIX}{session_id}"
        messages_key = f"{self.MESSAGES_PREFIX}{session_id}"

        await self._redis.delete(session_key, messages_key)

    async def extend_session(self, session_id: str, ttl: Optional[int] = None) -> bool:
        """延長 Session 快取過期時間

        Args:
            session_id: Session ID
            ttl: 新的 TTL (秒)

        Returns:
            是否成功延長
        """
        key = f"{self.SESSION_PREFIX}{session_id}"
        return await self._redis.expire(key, ttl or self.SESSION_TTL)

    async def update_session_status(
        self,
        session_id: str,
        status: SessionStatus,
    ) -> bool:
        """更新快取中的 Session 狀態

        Args:
            session_id: Session ID
            status: 新狀態

        Returns:
            是否成功更新
        """
        session = await self.get_session(session_id)
        if session is None:
            return False

        session.status = status
        session.updated_at = datetime.utcnow()
        await self.set_session(session)
        return True

    # ===== 訊息快取 =====

    async def get_messages(
        self,
        session_id: str,
        limit: int = 50,
    ) -> Optional[List[Message]]:
        """從快取獲取訊息

        Args:
            session_id: Session ID
            limit: 最大數量

        Returns:
            Message 列表或 None
        """
        key = f"{self.MESSAGES_PREFIX}{session_id}"
        data = await self._redis.lrange(key, -limit, -1)

        if not data:
            return None

        try:
            messages = []
            for item in data:
                msg_dict = json.loads(item)
                messages.append(Message.from_dict(msg_dict))
            return messages
        except (json.JSONDecodeError, KeyError):
            await self._redis.delete(key)
            return None

    async def append_message(self, session_id: str, message: Message) -> None:
        """添加訊息到快取

        Args:
            session_id: Session ID
            message: Message 物件
        """
        key = f"{self.MESSAGES_PREFIX}{session_id}"
        data = json.dumps(message.to_dict(), default=str)

        # 使用 pipeline 減少網路往返
        pipe = self._redis.pipeline()
        pipe.rpush(key, data)
        pipe.expire(key, self.MESSAGE_TTL)
        await pipe.execute()

    async def clear_messages(self, session_id: str) -> None:
        """清除訊息快取

        Args:
            session_id: Session ID
        """
        key = f"{self.MESSAGES_PREFIX}{session_id}"
        await self._redis.delete(key)

    # ===== 用戶 Session 列表快取 =====

    async def get_user_sessions(
        self,
        user_id: str,
        status: Optional[SessionStatus] = None,
    ) -> Optional[List[str]]:
        """從快取獲取用戶的 Session ID 列表

        Args:
            user_id: 用戶 ID
            status: 可選狀態過濾

        Returns:
            Session ID 列表或 None
        """
        key = self._user_sessions_key(user_id, status)
        data = await self._redis.lrange(key, 0, -1)

        if not data:
            return None

        return [item.decode() if isinstance(item, bytes) else item for item in data]

    async def set_user_sessions(
        self,
        user_id: str,
        session_ids: List[str],
        status: Optional[SessionStatus] = None,
    ) -> None:
        """設置用戶的 Session ID 列表快取

        Args:
            user_id: 用戶 ID
            session_ids: Session ID 列表
            status: 可選狀態過濾
        """
        key = self._user_sessions_key(user_id, status)

        pipe = self._redis.pipeline()
        pipe.delete(key)
        if session_ids:
            pipe.rpush(key, *session_ids)
        pipe.expire(key, self.LIST_TTL)
        await pipe.execute()

    async def invalidate_user_sessions(self, user_id: str) -> None:
        """使用戶的 Session 列表快取失效

        Args:
            user_id: 用戶 ID
        """
        # 刪除所有狀態的列表快取
        keys = [
            self._user_sessions_key(user_id, None),
            self._user_sessions_key(user_id, SessionStatus.CREATED),
            self._user_sessions_key(user_id, SessionStatus.ACTIVE),
            self._user_sessions_key(user_id, SessionStatus.SUSPENDED),
            self._user_sessions_key(user_id, SessionStatus.ENDED),
        ]
        await self._redis.delete(*keys)

    def _user_sessions_key(
        self,
        user_id: str,
        status: Optional[SessionStatus],
    ) -> str:
        """生成用戶 Session 列表的快取 key

        Args:
            user_id: 用戶 ID
            status: 可選狀態過濾

        Returns:
            快取 key
        """
        if status:
            return f"{self.USER_SESSIONS_PREFIX}{user_id}:{status.value}"
        return f"{self.USER_SESSIONS_PREFIX}{user_id}:all"

    # ===== 批量操作 =====

    async def get_sessions_batch(
        self,
        session_ids: List[str],
    ) -> Dict[str, Optional[Session]]:
        """批量獲取 Sessions

        Args:
            session_ids: Session ID 列表

        Returns:
            Session ID 到 Session 的映射
        """
        if not session_ids:
            return {}

        keys = [f"{self.SESSION_PREFIX}{sid}" for sid in session_ids]
        values = await self._redis.mget(keys)

        result = {}
        for sid, value in zip(session_ids, values):
            if value:
                try:
                    session_dict = json.loads(value)
                    result[sid] = Session.from_dict(session_dict)
                except (json.JSONDecodeError, KeyError):
                    result[sid] = None
            else:
                result[sid] = None

        return result

    async def set_sessions_batch(
        self,
        sessions: List[Session],
        ttl: Optional[int] = None,
    ) -> None:
        """批量設置 Sessions

        Args:
            sessions: Session 列表
            ttl: 可選 TTL (秒)
        """
        if not sessions:
            return

        pipe = self._redis.pipeline()
        for session in sessions:
            key = f"{self.SESSION_PREFIX}{session.id}"
            data = json.dumps(session.to_dict(), default=str)
            pipe.setex(key, ttl or self.SESSION_TTL, data)

        await pipe.execute()

    # ===== 統計和健康檢查 =====

    async def get_cache_stats(self) -> Dict[str, Any]:
        """獲取快取統計資訊

        Returns:
            統計資訊字典
        """
        info = await self._redis.info("memory")
        keys_count = await self._redis.dbsize()

        return {
            "used_memory": info.get("used_memory_human"),
            "total_keys": keys_count,
            "session_prefix": self.SESSION_PREFIX,
        }

    async def health_check(self) -> bool:
        """健康檢查

        Returns:
            是否健康
        """
        try:
            await self._redis.ping()
            return True
        except Exception:
            return False

    async def flush_all(self) -> None:
        """清除所有 Session 相關快取 (慎用)"""
        # 使用 SCAN 避免阻塞
        cursor = 0
        while True:
            cursor, keys = await self._redis.scan(
                cursor,
                match=f"{self.SESSION_PREFIX}*",
                count=100
            )
            if keys:
                await self._redis.delete(*keys)
            if cursor == 0:
                break

        # 清除用戶列表快取
        cursor = 0
        while True:
            cursor, keys = await self._redis.scan(
                cursor,
                match=f"{self.USER_SESSIONS_PREFIX}*",
                count=100
            )
            if keys:
                await self._redis.delete(*keys)
            if cursor == 0:
                break
