"""
Bookmark Service

Service for managing message bookmarks.
Based on D44-3 decision: Independent Bookmark table storage.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field
import uuid
import logging

from ..models import Message

logger = logging.getLogger(__name__)


@dataclass
class Bookmark:
    """書籤資料模型"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    session_id: str = ""
    message_id: str = ""
    name: str = ""
    description: Optional[str] = None
    color: Optional[str] = None  # 標記顏色
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    # 關聯的訊息 (懶加載)
    message: Optional[Message] = None


@dataclass
class BookmarkFilter:
    """書籤過濾器"""
    session_id: Optional[str] = None
    tags: Optional[List[str]] = None
    search_query: Optional[str] = None
    color: Optional[str] = None


class BookmarkService:
    """書籤服務

    管理用戶的訊息書籤。

    功能:
    - 創建/刪除書籤
    - 更新書籤信息
    - 按條件查詢書籤
    - 書籤分類 (標籤/顏色)
    - 書籤匯出
    """

    # 預設顏色
    DEFAULT_COLORS = [
        "#f44336",  # Red
        "#ff9800",  # Orange
        "#ffeb3b",  # Yellow
        "#4caf50",  # Green
        "#2196f3",  # Blue
        "#9c27b0",  # Purple
    ]

    def __init__(
        self,
        repository: Optional[Any] = None,
        cache: Optional[Any] = None
    ):
        """
        初始化書籤服務

        Args:
            repository: 資料庫存儲實例
            cache: 快取服務實例
        """
        self._repository = repository
        self._cache = cache

    async def create_bookmark(
        self,
        user_id: str,
        session_id: str,
        message_id: str,
        name: str,
        description: Optional[str] = None,
        color: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Bookmark:
        """
        創建書籤

        Args:
            user_id: 用戶 ID
            session_id: Session ID
            message_id: 訊息 ID
            name: 書籤名稱
            description: 描述
            color: 標記顏色
            tags: 標籤列表

        Returns:
            Bookmark: 創建的書籤

        Raises:
            ValueError: 如果書籤已存在
        """
        try:
            # 檢查是否已存在
            existing = await self.get_bookmark_by_message(user_id, message_id)
            if existing:
                raise ValueError(f"Bookmark already exists for message {message_id}")

            # 創建書籤
            bookmark = Bookmark(
                user_id=user_id,
                session_id=session_id,
                message_id=message_id,
                name=name,
                description=description,
                color=color or self.DEFAULT_COLORS[0],
                tags=tags or []
            )

            # 保存到資料庫
            if self._repository:
                await self._repository.create_bookmark(bookmark)

            # 清除用戶書籤快取
            await self._invalidate_user_cache(user_id)

            logger.info(f"Created bookmark: {bookmark.id} for message {message_id}")
            return bookmark

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to create bookmark: {e}")
            raise

    async def get_bookmark(self, bookmark_id: str) -> Optional[Bookmark]:
        """
        獲取書籤

        Args:
            bookmark_id: 書籤 ID

        Returns:
            Bookmark or None
        """
        try:
            if self._repository:
                return await self._repository.get_bookmark(bookmark_id)
            return None
        except Exception as e:
            logger.error(f"Failed to get bookmark {bookmark_id}: {e}")
            return None

    async def get_bookmark_by_message(
        self,
        user_id: str,
        message_id: str
    ) -> Optional[Bookmark]:
        """
        根據訊息 ID 獲取書籤

        Args:
            user_id: 用戶 ID
            message_id: 訊息 ID

        Returns:
            Bookmark or None
        """
        try:
            if self._repository:
                return await self._repository.get_bookmark_by_message(
                    user_id=user_id,
                    message_id=message_id
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get bookmark by message: {e}")
            return None

    async def get_user_bookmarks(
        self,
        user_id: str,
        filter: Optional[BookmarkFilter] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Bookmark]:
        """
        獲取用戶的所有書籤

        Args:
            user_id: 用戶 ID
            filter: 過濾條件
            limit: 返回數量限制
            offset: 跳過數量

        Returns:
            List[Bookmark]: 書籤列表
        """
        try:
            # 嘗試從快取獲取
            cache_key = f"bookmarks:{user_id}:{limit}:{offset}"
            if self._cache and not filter:
                cached = await self._cache.get(cache_key)
                if cached:
                    return cached

            if self._repository:
                bookmarks = await self._repository.get_user_bookmarks(
                    user_id=user_id,
                    filter=self._convert_filter(filter),
                    limit=limit,
                    offset=offset
                )
            else:
                bookmarks = []

            # 快取結果
            if self._cache and not filter:
                await self._cache.set(cache_key, bookmarks, ttl=300)

            return bookmarks

        except Exception as e:
            logger.error(f"Failed to get user bookmarks: {e}")
            return []

    async def get_session_bookmarks(
        self,
        user_id: str,
        session_id: str
    ) -> List[Bookmark]:
        """
        獲取 Session 的所有書籤

        Args:
            user_id: 用戶 ID
            session_id: Session ID

        Returns:
            List[Bookmark]: 書籤列表
        """
        filter = BookmarkFilter(session_id=session_id)
        return await self.get_user_bookmarks(user_id, filter=filter)

    async def update_bookmark(
        self,
        bookmark_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[Bookmark]:
        """
        更新書籤

        Args:
            bookmark_id: 書籤 ID
            user_id: 用戶 ID (驗證權限)
            name: 新名稱
            description: 新描述
            color: 新顏色
            tags: 新標籤

        Returns:
            Bookmark: 更新後的書籤
        """
        try:
            # 獲取現有書籤
            bookmark = await self.get_bookmark(bookmark_id)
            if not bookmark:
                return None

            # 驗證權限
            if bookmark.user_id != user_id:
                raise PermissionError("Not authorized to update this bookmark")

            # 更新欄位
            if name is not None:
                bookmark.name = name
            if description is not None:
                bookmark.description = description
            if color is not None:
                bookmark.color = color
            if tags is not None:
                bookmark.tags = tags
            bookmark.updated_at = datetime.now()

            # 保存更新
            if self._repository:
                await self._repository.update_bookmark(bookmark)

            # 清除快取
            await self._invalidate_user_cache(user_id)

            logger.info(f"Updated bookmark: {bookmark_id}")
            return bookmark

        except PermissionError:
            raise
        except Exception as e:
            logger.error(f"Failed to update bookmark: {e}")
            return None

    async def delete_bookmark(
        self,
        bookmark_id: str,
        user_id: str
    ) -> bool:
        """
        刪除書籤

        Args:
            bookmark_id: 書籤 ID
            user_id: 用戶 ID (驗證權限)

        Returns:
            bool: 是否刪除成功
        """
        try:
            # 獲取現有書籤
            bookmark = await self.get_bookmark(bookmark_id)
            if not bookmark:
                return False

            # 驗證權限
            if bookmark.user_id != user_id:
                raise PermissionError("Not authorized to delete this bookmark")

            # 刪除
            if self._repository:
                await self._repository.delete_bookmark(bookmark_id)

            # 清除快取
            await self._invalidate_user_cache(user_id)

            logger.info(f"Deleted bookmark: {bookmark_id}")
            return True

        except PermissionError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete bookmark: {e}")
            return False

    async def add_tags(
        self,
        bookmark_id: str,
        user_id: str,
        tags: List[str]
    ) -> Optional[Bookmark]:
        """
        添加標籤到書籤

        Args:
            bookmark_id: 書籤 ID
            user_id: 用戶 ID
            tags: 要添加的標籤

        Returns:
            Bookmark: 更新後的書籤
        """
        bookmark = await self.get_bookmark(bookmark_id)
        if not bookmark or bookmark.user_id != user_id:
            return None

        # 合併標籤 (去重)
        existing_tags = set(bookmark.tags)
        existing_tags.update(tags)
        new_tags = list(existing_tags)

        return await self.update_bookmark(bookmark_id, user_id, tags=new_tags)

    async def remove_tags(
        self,
        bookmark_id: str,
        user_id: str,
        tags: List[str]
    ) -> Optional[Bookmark]:
        """
        從書籤移除標籤

        Args:
            bookmark_id: 書籤 ID
            user_id: 用戶 ID
            tags: 要移除的標籤

        Returns:
            Bookmark: 更新後的書籤
        """
        bookmark = await self.get_bookmark(bookmark_id)
        if not bookmark or bookmark.user_id != user_id:
            return None

        # 移除標籤
        tags_to_remove = set(tags)
        new_tags = [t for t in bookmark.tags if t not in tags_to_remove]

        return await self.update_bookmark(bookmark_id, user_id, tags=new_tags)

    async def get_user_tags(self, user_id: str) -> List[str]:
        """
        獲取用戶使用的所有標籤

        Args:
            user_id: 用戶 ID

        Returns:
            List[str]: 標籤列表
        """
        try:
            if self._repository:
                return await self._repository.get_user_bookmark_tags(user_id)
            return []
        except Exception as e:
            logger.error(f"Failed to get user tags: {e}")
            return []

    async def export_bookmarks(
        self,
        user_id: str,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        匯出書籤

        Args:
            user_id: 用戶 ID
            format: 匯出格式

        Returns:
            Dict: 匯出的資料
        """
        try:
            bookmarks = await self.get_user_bookmarks(user_id, limit=1000)

            return {
                "bookmarks": [
                    {
                        "id": b.id,
                        "session_id": b.session_id,
                        "message_id": b.message_id,
                        "name": b.name,
                        "description": b.description,
                        "color": b.color,
                        "tags": b.tags,
                        "created_at": b.created_at.isoformat() if b.created_at else None
                    }
                    for b in bookmarks
                ],
                "count": len(bookmarks),
                "exported_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to export bookmarks: {e}")
            return {"error": str(e)}

    async def _invalidate_user_cache(self, user_id: str) -> None:
        """清除用戶書籤快取"""
        if self._cache:
            await self._cache.delete_pattern(f"bookmarks:{user_id}:*")

    def _convert_filter(self, filter: Optional[BookmarkFilter]) -> Optional[Dict[str, Any]]:
        """轉換過濾器為字典"""
        if not filter:
            return None

        result = {}
        if filter.session_id:
            result["session_id"] = filter.session_id
        if filter.tags:
            result["tags"] = filter.tags
        if filter.search_query:
            result["search_query"] = filter.search_query
        if filter.color:
            result["color"] = filter.color

        return result if result else None
