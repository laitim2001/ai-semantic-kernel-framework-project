"""
Tag Service

Service for managing session tags.
"""

from typing import Optional, Dict, Any, List, Set
from datetime import datetime
from dataclasses import dataclass, field
import uuid
import logging

logger = logging.getLogger(__name__)


@dataclass
class Tag:
    """標籤資料模型"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    color: Optional[str] = None
    description: Optional[str] = None
    user_id: str = ""
    usage_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SessionTag:
    """Session 標籤關聯"""
    session_id: str
    tag_id: str
    added_at: datetime = field(default_factory=datetime.now)
    added_by: Optional[str] = None


class TagService:
    """標籤服務

    管理 Session 的標籤系統。

    功能:
    - 創建/刪除標籤
    - 為 Session 添加/移除標籤
    - 按標籤查詢 Sessions
    - 標籤統計
    - 標籤建議
    """

    # 系統預設標籤
    SYSTEM_TAGS = [
        {"name": "important", "color": "#f44336", "description": "重要對話"},
        {"name": "work", "color": "#2196f3", "description": "工作相關"},
        {"name": "personal", "color": "#4caf50", "description": "個人事務"},
        {"name": "project", "color": "#ff9800", "description": "專案討論"},
        {"name": "learning", "color": "#9c27b0", "description": "學習筆記"},
        {"name": "archived", "color": "#9e9e9e", "description": "已歸檔"},
    ]

    def __init__(
        self,
        repository: Optional[Any] = None,
        cache: Optional[Any] = None
    ):
        """
        初始化標籤服務

        Args:
            repository: 資料庫存儲實例
            cache: 快取服務實例
        """
        self._repository = repository
        self._cache = cache

    async def create_tag(
        self,
        user_id: str,
        name: str,
        color: Optional[str] = None,
        description: Optional[str] = None
    ) -> Tag:
        """
        創建標籤

        Args:
            user_id: 用戶 ID
            name: 標籤名稱
            color: 標籤顏色
            description: 標籤描述

        Returns:
            Tag: 創建的標籤

        Raises:
            ValueError: 如果標籤已存在
        """
        try:
            # 正規化標籤名稱
            normalized_name = self._normalize_tag_name(name)
            if not normalized_name:
                raise ValueError("Tag name cannot be empty")

            # 檢查是否已存在
            existing = await self.get_tag_by_name(user_id, normalized_name)
            if existing:
                raise ValueError(f"Tag '{normalized_name}' already exists")

            # 創建標籤
            tag = Tag(
                name=normalized_name,
                color=color or self._generate_color(normalized_name),
                description=description,
                user_id=user_id
            )

            # 保存到資料庫
            if self._repository:
                await self._repository.create_tag(tag)

            # 清除快取
            await self._invalidate_cache(user_id)

            logger.info(f"Created tag: {tag.name} for user {user_id}")
            return tag

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to create tag: {e}")
            raise

    async def get_tag(self, tag_id: str) -> Optional[Tag]:
        """獲取標籤"""
        try:
            if self._repository:
                return await self._repository.get_tag(tag_id)
            return None
        except Exception as e:
            logger.error(f"Failed to get tag: {e}")
            return None

    async def get_tag_by_name(self, user_id: str, name: str) -> Optional[Tag]:
        """根據名稱獲取標籤"""
        try:
            normalized_name = self._normalize_tag_name(name)
            if self._repository:
                return await self._repository.get_tag_by_name(user_id, normalized_name)
            return None
        except Exception as e:
            logger.error(f"Failed to get tag by name: {e}")
            return None

    async def get_user_tags(
        self,
        user_id: str,
        include_system: bool = True
    ) -> List[Tag]:
        """
        獲取用戶的所有標籤

        Args:
            user_id: 用戶 ID
            include_system: 是否包含系統標籤

        Returns:
            List[Tag]: 標籤列表
        """
        try:
            # 嘗試從快取獲取
            cache_key = f"tags:{user_id}"
            if self._cache:
                cached = await self._cache.get(cache_key)
                if cached:
                    return cached

            tags = []

            # 獲取系統標籤
            if include_system:
                for st in self.SYSTEM_TAGS:
                    tags.append(Tag(
                        id=f"system_{st['name']}",
                        name=st["name"],
                        color=st["color"],
                        description=st["description"],
                        user_id="system"
                    ))

            # 獲取用戶標籤
            if self._repository:
                user_tags = await self._repository.get_user_tags(user_id)
                tags.extend(user_tags)

            # 快取結果
            if self._cache:
                await self._cache.set(cache_key, tags, ttl=300)

            return tags

        except Exception as e:
            logger.error(f"Failed to get user tags: {e}")
            return []

    async def update_tag(
        self,
        tag_id: str,
        user_id: str,
        name: Optional[str] = None,
        color: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[Tag]:
        """更新標籤"""
        try:
            tag = await self.get_tag(tag_id)
            if not tag or tag.user_id != user_id:
                return None

            if name is not None:
                tag.name = self._normalize_tag_name(name)
            if color is not None:
                tag.color = color
            if description is not None:
                tag.description = description

            if self._repository:
                await self._repository.update_tag(tag)

            await self._invalidate_cache(user_id)
            return tag

        except Exception as e:
            logger.error(f"Failed to update tag: {e}")
            return None

    async def delete_tag(self, tag_id: str, user_id: str) -> bool:
        """刪除標籤"""
        try:
            tag = await self.get_tag(tag_id)
            if not tag or tag.user_id != user_id:
                return False

            if self._repository:
                await self._repository.delete_tag(tag_id)

            await self._invalidate_cache(user_id)
            return True

        except Exception as e:
            logger.error(f"Failed to delete tag: {e}")
            return False

    async def add_tag_to_session(
        self,
        session_id: str,
        tag_id: str,
        user_id: str
    ) -> bool:
        """
        為 Session 添加標籤

        Args:
            session_id: Session ID
            tag_id: 標籤 ID
            user_id: 用戶 ID

        Returns:
            bool: 是否添加成功
        """
        try:
            # 檢查標籤是否存在
            tag = await self.get_tag(tag_id)
            if not tag:
                return False

            # 檢查是否已添加
            session_tags = await self.get_session_tags(session_id)
            if any(t.id == tag_id for t in session_tags):
                return True  # 已存在

            # 添加關聯
            if self._repository:
                await self._repository.add_session_tag(SessionTag(
                    session_id=session_id,
                    tag_id=tag_id,
                    added_by=user_id
                ))

                # 更新使用計數
                tag.usage_count += 1
                await self._repository.update_tag(tag)

            # 清除快取
            await self._invalidate_session_cache(session_id)

            return True

        except Exception as e:
            logger.error(f"Failed to add tag to session: {e}")
            return False

    async def remove_tag_from_session(
        self,
        session_id: str,
        tag_id: str,
        user_id: str
    ) -> bool:
        """從 Session 移除標籤"""
        try:
            if self._repository:
                await self._repository.remove_session_tag(session_id, tag_id)

                # 更新使用計數
                tag = await self.get_tag(tag_id)
                if tag and tag.usage_count > 0:
                    tag.usage_count -= 1
                    await self._repository.update_tag(tag)

            await self._invalidate_session_cache(session_id)
            return True

        except Exception as e:
            logger.error(f"Failed to remove tag from session: {e}")
            return False

    async def get_session_tags(self, session_id: str) -> List[Tag]:
        """獲取 Session 的所有標籤"""
        try:
            cache_key = f"session_tags:{session_id}"
            if self._cache:
                cached = await self._cache.get(cache_key)
                if cached:
                    return cached

            if self._repository:
                tags = await self._repository.get_session_tags(session_id)
            else:
                tags = []

            if self._cache:
                await self._cache.set(cache_key, tags, ttl=300)

            return tags

        except Exception as e:
            logger.error(f"Failed to get session tags: {e}")
            return []

    async def get_sessions_by_tag(
        self,
        tag_id: str,
        user_id: str,
        limit: int = 50
    ) -> List[str]:
        """根據標籤獲取 Session 列表"""
        try:
            if self._repository:
                return await self._repository.get_sessions_by_tag(
                    tag_id=tag_id,
                    user_id=user_id,
                    limit=limit
                )
            return []
        except Exception as e:
            logger.error(f"Failed to get sessions by tag: {e}")
            return []

    async def get_popular_tags(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Tag]:
        """獲取最常用的標籤"""
        try:
            tags = await self.get_user_tags(user_id)
            # 按使用次數排序
            sorted_tags = sorted(tags, key=lambda t: t.usage_count, reverse=True)
            return sorted_tags[:limit]
        except Exception as e:
            logger.error(f"Failed to get popular tags: {e}")
            return []

    async def suggest_tags(
        self,
        user_id: str,
        content: str,
        limit: int = 5
    ) -> List[Tag]:
        """
        根據內容建議標籤

        Args:
            user_id: 用戶 ID
            content: 對話內容
            limit: 返回數量

        Returns:
            List[Tag]: 建議的標籤
        """
        try:
            # 獲取用戶所有標籤
            all_tags = await self.get_user_tags(user_id)

            # 簡單的關鍵字匹配
            suggestions = []
            content_lower = content.lower()

            for tag in all_tags:
                if tag.name.lower() in content_lower:
                    suggestions.append(tag)
                elif tag.description and any(
                    word in content_lower
                    for word in tag.description.lower().split()
                ):
                    suggestions.append(tag)

            # 如果沒有匹配，返回最常用的
            if not suggestions:
                suggestions = await self.get_popular_tags(user_id, limit)

            return suggestions[:limit]

        except Exception as e:
            logger.error(f"Failed to suggest tags: {e}")
            return []

    def _normalize_tag_name(self, name: str) -> str:
        """正規化標籤名稱"""
        return name.strip().lower().replace(" ", "-")

    def _generate_color(self, name: str) -> str:
        """根據名稱生成顏色"""
        colors = [
            "#f44336", "#e91e63", "#9c27b0", "#673ab7",
            "#3f51b5", "#2196f3", "#03a9f4", "#00bcd4",
            "#009688", "#4caf50", "#8bc34a", "#cddc39",
            "#ffeb3b", "#ffc107", "#ff9800", "#ff5722"
        ]
        # 使用名稱的 hash 選擇顏色
        index = hash(name) % len(colors)
        return colors[index]

    async def _invalidate_cache(self, user_id: str) -> None:
        """清除用戶標籤快取"""
        if self._cache:
            await self._cache.delete(f"tags:{user_id}")

    async def _invalidate_session_cache(self, session_id: str) -> None:
        """清除 Session 標籤快取"""
        if self._cache:
            await self._cache.delete(f"session_tags:{session_id}")
