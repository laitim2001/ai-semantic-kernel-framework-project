"""
History Manager

Main entry point for conversation history operations.
"""

from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import logging

from ..models import Message, MessageRole, Session

logger = logging.getLogger(__name__)


@dataclass
class HistoryFilter:
    """歷史記錄過濾器"""
    role: Optional[MessageRole] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    has_attachments: Optional[bool] = None
    has_tool_calls: Optional[bool] = None
    search_query: Optional[str] = None


@dataclass
class HistoryPage:
    """分頁結果"""
    messages: List[Message] = field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    has_more: bool = False


class HistoryManager:
    """對話歷史管理器

    管理 Session 的對話歷史記錄。

    功能:
    - 歷史記錄查詢
    - 分頁瀏覽
    - 過濾搜索
    - 匯出歷史
    - 清理歷史
    """

    def __init__(
        self,
        repository: Optional[Any] = None,
        cache: Optional[Any] = None,
        max_history_days: int = 90
    ):
        """
        初始化歷史管理器

        Args:
            repository: 資料庫存儲實例
            cache: 快取服務實例
            max_history_days: 歷史保留天數
        """
        self._repository = repository
        self._cache = cache
        self._max_history_days = max_history_days

    async def get_history(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0,
        filter: Optional[HistoryFilter] = None,
        order: str = "asc"
    ) -> HistoryPage:
        """
        獲取對話歷史

        Args:
            session_id: Session ID
            limit: 返回數量限制
            offset: 跳過數量
            filter: 過濾條件
            order: 排序 (asc/desc)

        Returns:
            HistoryPage: 分頁結果
        """
        try:
            # 嘗試從快取獲取
            cache_key = self._build_cache_key(session_id, limit, offset, filter, order)
            if self._cache:
                cached = await self._cache.get(cache_key)
                if cached:
                    return cached

            # 從資料庫查詢
            if self._repository:
                messages, total = await self._repository.get_messages(
                    session_id=session_id,
                    limit=limit,
                    offset=offset,
                    filter=self._convert_filter(filter),
                    order=order
                )
            else:
                # 模擬空結果
                messages = []
                total = 0

            result = HistoryPage(
                messages=messages,
                total=total,
                page=(offset // limit) + 1 if limit > 0 else 1,
                page_size=limit,
                has_more=offset + len(messages) < total
            )

            # 快取結果
            if self._cache:
                await self._cache.set(cache_key, result, ttl=60)

            return result

        except Exception as e:
            logger.error(f"Failed to get history for session {session_id}: {e}")
            return HistoryPage()

    async def get_recent_messages(
        self,
        session_id: str,
        count: int = 10
    ) -> List[Message]:
        """
        獲取最近的訊息

        Args:
            session_id: Session ID
            count: 返回數量

        Returns:
            List[Message]: 最近的訊息列表
        """
        result = await self.get_history(
            session_id=session_id,
            limit=count,
            order="desc"
        )
        # 反轉為時間順序
        return list(reversed(result.messages))

    async def get_message_context(
        self,
        session_id: str,
        message_id: str,
        before: int = 5,
        after: int = 5
    ) -> Dict[str, Any]:
        """
        獲取訊息上下文

        Args:
            session_id: Session ID
            message_id: 目標訊息 ID
            before: 前面的訊息數量
            after: 後面的訊息數量

        Returns:
            Dict: 包含前後訊息的上下文
        """
        try:
            if self._repository:
                # 獲取目標訊息的位置
                position = await self._repository.get_message_position(
                    session_id=session_id,
                    message_id=message_id
                )

                if position is None:
                    return {"target": None, "before": [], "after": []}

                # 獲取前面的訊息
                before_result = await self.get_history(
                    session_id=session_id,
                    limit=before,
                    offset=max(0, position - before),
                    order="asc"
                )

                # 獲取後面的訊息
                after_result = await self.get_history(
                    session_id=session_id,
                    limit=after + 1,  # +1 包含目標訊息
                    offset=position,
                    order="asc"
                )

                target = after_result.messages[0] if after_result.messages else None
                after_messages = after_result.messages[1:] if len(after_result.messages) > 1 else []

                return {
                    "target": target,
                    "before": before_result.messages,
                    "after": after_messages
                }

            return {"target": None, "before": [], "after": []}

        except Exception as e:
            logger.error(f"Failed to get message context: {e}")
            return {"target": None, "before": [], "after": []}

    async def get_conversation_turns(
        self,
        session_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        獲取對話輪次 (user-assistant 配對)

        Args:
            session_id: Session ID
            limit: 返回的輪次數量

        Returns:
            List[Dict]: 對話輪次列表
        """
        try:
            result = await self.get_history(
                session_id=session_id,
                limit=limit * 2,  # 每輪 2 條訊息
                order="asc"
            )

            turns = []
            current_turn = {"user": None, "assistant": None}

            for message in result.messages:
                if message.role == MessageRole.USER:
                    # 如果當前輪次已有 user，先保存
                    if current_turn["user"] is not None:
                        turns.append(current_turn)
                        current_turn = {"user": None, "assistant": None}
                    current_turn["user"] = message
                elif message.role == MessageRole.ASSISTANT:
                    current_turn["assistant"] = message
                    # 一輪完成，保存並開始新輪
                    if current_turn["user"] is not None:
                        turns.append(current_turn)
                        current_turn = {"user": None, "assistant": None}

            # 保存最後一個不完整的輪次
            if current_turn["user"] is not None:
                turns.append(current_turn)

            return turns[:limit]

        except Exception as e:
            logger.error(f"Failed to get conversation turns: {e}")
            return []

    async def export_history(
        self,
        session_id: str,
        format: str = "json",
        include_metadata: bool = True
    ) -> Union[str, Dict[str, Any]]:
        """
        匯出對話歷史

        Args:
            session_id: Session ID
            format: 匯出格式 (json/markdown/text)
            include_metadata: 是否包含元數據

        Returns:
            匯出的內容
        """
        try:
            # 獲取所有歷史
            all_messages = []
            offset = 0
            batch_size = 100

            while True:
                result = await self.get_history(
                    session_id=session_id,
                    limit=batch_size,
                    offset=offset,
                    order="asc"
                )
                all_messages.extend(result.messages)
                offset += batch_size
                if not result.has_more:
                    break

            # 根據格式匯出
            if format == "json":
                return self._export_json(all_messages, include_metadata)
            elif format == "markdown":
                return self._export_markdown(all_messages, include_metadata)
            elif format == "text":
                return self._export_text(all_messages)
            else:
                return self._export_json(all_messages, include_metadata)

        except Exception as e:
            logger.error(f"Failed to export history: {e}")
            return {"error": str(e)}

    def _export_json(
        self,
        messages: List[Message],
        include_metadata: bool
    ) -> Dict[str, Any]:
        """匯出為 JSON 格式"""
        return {
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role.value if hasattr(msg.role, 'value') else msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                    **({"metadata": msg.metadata} if include_metadata and hasattr(msg, 'metadata') else {})
                }
                for msg in messages
            ],
            "count": len(messages),
            "exported_at": datetime.now().isoformat()
        }

    def _export_markdown(
        self,
        messages: List[Message],
        include_metadata: bool
    ) -> str:
        """匯出為 Markdown 格式"""
        lines = ["# 對話歷史\n"]

        if include_metadata:
            lines.append(f"匯出時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            lines.append(f"訊息數量: {len(messages)}\n")
            lines.append("---\n")

        for msg in messages:
            role_emoji = "👤" if msg.role == MessageRole.USER else "🤖"
            role_name = "User" if msg.role == MessageRole.USER else "Assistant"
            timestamp = msg.created_at.strftime('%H:%M:%S') if msg.created_at else ""

            lines.append(f"### {role_emoji} {role_name} ({timestamp})\n")
            lines.append(f"{msg.content}\n")
            lines.append("")

        return "\n".join(lines)

    def _export_text(self, messages: List[Message]) -> str:
        """匯出為純文字格式"""
        lines = []
        for msg in messages:
            role = "User" if msg.role == MessageRole.USER else "Assistant"
            lines.append(f"[{role}]: {msg.content}")
            lines.append("")
        return "\n".join(lines)

    async def clear_history(
        self,
        session_id: str,
        before: Optional[datetime] = None,
        keep_recent: int = 0
    ) -> int:
        """
        清理歷史記錄

        Args:
            session_id: Session ID
            before: 清理此時間之前的記錄
            keep_recent: 保留最近的 N 條記錄

        Returns:
            int: 清理的記錄數量
        """
        try:
            if self._repository:
                deleted_count = await self._repository.delete_messages(
                    session_id=session_id,
                    before=before,
                    keep_recent=keep_recent
                )

                # 清除相關快取
                if self._cache:
                    await self._cache.delete_pattern(f"history:{session_id}:*")

                logger.info(f"Cleared {deleted_count} messages from session {session_id}")
                return deleted_count

            return 0

        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
            return 0

    async def cleanup_old_history(self) -> Dict[str, int]:
        """
        清理過期歷史 (定期任務)

        Returns:
            Dict: 清理統計
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=self._max_history_days)

            if self._repository:
                stats = await self._repository.cleanup_old_messages(before=cutoff_date)
                logger.info(f"Cleaned up old history: {stats}")
                return stats

            return {"deleted_sessions": 0, "deleted_messages": 0}

        except Exception as e:
            logger.error(f"Failed to cleanup old history: {e}")
            return {"error": str(e)}

    def _build_cache_key(
        self,
        session_id: str,
        limit: int,
        offset: int,
        filter: Optional[HistoryFilter],
        order: str
    ) -> str:
        """構建快取鍵"""
        filter_str = ""
        if filter:
            filter_str = f":f{hash(str(filter))}"
        return f"history:{session_id}:{limit}:{offset}:{order}{filter_str}"

    def _convert_filter(self, filter: Optional[HistoryFilter]) -> Optional[Dict[str, Any]]:
        """轉換過濾器為字典"""
        if not filter:
            return None

        result = {}
        if filter.role:
            result["role"] = filter.role
        if filter.start_time:
            result["start_time"] = filter.start_time
        if filter.end_time:
            result["end_time"] = filter.end_time
        if filter.has_attachments is not None:
            result["has_attachments"] = filter.has_attachments
        if filter.has_tool_calls is not None:
            result["has_tool_calls"] = filter.has_tool_calls
        if filter.search_query:
            result["search_query"] = filter.search_query

        return result if result else None
