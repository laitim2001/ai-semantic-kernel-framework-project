"""
Search Service

Full-text search service for session messages.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import re
import logging

from ..models import Message, MessageRole

logger = logging.getLogger(__name__)


class SearchScope(str, Enum):
    """搜索範圍"""
    ALL = "all"           # 所有 Sessions
    SESSION = "session"   # 單一 Session
    RECENT = "recent"     # 最近的記錄


class SearchSortBy(str, Enum):
    """排序方式"""
    RELEVANCE = "relevance"  # 相關性
    DATE_DESC = "date_desc"  # 最新優先
    DATE_ASC = "date_asc"    # 最舊優先


@dataclass
class SearchQuery:
    """搜索查詢"""
    query: str
    scope: SearchScope = SearchScope.SESSION
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    role: Optional[MessageRole] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    sort_by: SearchSortBy = SearchSortBy.RELEVANCE
    limit: int = 20
    offset: int = 0
    highlight: bool = True
    highlight_tag: str = "mark"  # HTML 標籤


@dataclass
class SearchResult:
    """搜索結果"""
    message: Message
    session_id: str
    score: float = 0.0
    highlights: List[str] = field(default_factory=list)
    context_before: Optional[str] = None
    context_after: Optional[str] = None


@dataclass
class SearchResponse:
    """搜索回應"""
    results: List[SearchResult] = field(default_factory=list)
    total: int = 0
    query: str = ""
    took_ms: int = 0
    suggestions: List[str] = field(default_factory=list)


class SearchService:
    """搜索服務

    提供訊息的全文搜索功能。

    功能:
    - 全文搜索
    - 關鍵字高亮
    - 搜索建議
    - 多欄位搜索
    - 結果排序
    """

    def __init__(
        self,
        repository: Optional[Any] = None,
        search_engine: Optional[Any] = None,
        cache: Optional[Any] = None
    ):
        """
        初始化搜索服務

        Args:
            repository: 資料庫存儲實例
            search_engine: 搜索引擎實例 (如 Elasticsearch)
            cache: 快取服務實例
        """
        self._repository = repository
        self._search_engine = search_engine
        self._cache = cache

    async def search(self, query: SearchQuery) -> SearchResponse:
        """
        執行搜索

        Args:
            query: 搜索查詢

        Returns:
            SearchResponse: 搜索結果
        """
        start_time = datetime.now()

        try:
            # 預處理查詢
            processed_query = self._preprocess_query(query.query)
            if not processed_query:
                return SearchResponse(query=query.query)

            # 使用搜索引擎或資料庫搜索
            if self._search_engine:
                results, total = await self._search_with_engine(query, processed_query)
            else:
                results, total = await self._search_with_database(query, processed_query)

            # 計算耗時
            took_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # 生成搜索建議
            suggestions = await self._get_suggestions(query.query) if total == 0 else []

            return SearchResponse(
                results=results,
                total=total,
                query=query.query,
                took_ms=took_ms,
                suggestions=suggestions
            )

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return SearchResponse(query=query.query)

    async def search_in_session(
        self,
        session_id: str,
        query: str,
        limit: int = 20
    ) -> SearchResponse:
        """
        在單一 Session 中搜索

        Args:
            session_id: Session ID
            query: 搜索關鍵字
            limit: 返回數量限制

        Returns:
            SearchResponse: 搜索結果
        """
        search_query = SearchQuery(
            query=query,
            scope=SearchScope.SESSION,
            session_id=session_id,
            limit=limit
        )
        return await self.search(search_query)

    async def search_user_messages(
        self,
        user_id: str,
        query: str,
        limit: int = 50
    ) -> SearchResponse:
        """
        搜索用戶的所有訊息

        Args:
            user_id: 用戶 ID
            query: 搜索關鍵字
            limit: 返回數量限制

        Returns:
            SearchResponse: 搜索結果
        """
        search_query = SearchQuery(
            query=query,
            scope=SearchScope.ALL,
            user_id=user_id,
            limit=limit
        )
        return await self.search(search_query)

    async def _search_with_engine(
        self,
        query: SearchQuery,
        processed_query: str
    ) -> tuple[List[SearchResult], int]:
        """使用搜索引擎搜索"""
        try:
            # 構建搜索請求
            search_request = {
                "query": {
                    "bool": {
                        "must": [
                            {"multi_match": {
                                "query": processed_query,
                                "fields": ["content^2", "metadata.*"],
                                "type": "best_fields"
                            }}
                        ],
                        "filter": self._build_filters(query)
                    }
                },
                "highlight": {
                    "fields": {"content": {}},
                    "pre_tags": [f"<{query.highlight_tag}>"],
                    "post_tags": [f"</{query.highlight_tag}>"]
                } if query.highlight else {},
                "from": query.offset,
                "size": query.limit,
                "sort": self._build_sort(query.sort_by)
            }

            # 執行搜索
            response = await self._search_engine.search(
                index="messages",
                body=search_request
            )

            # 解析結果
            results = []
            for hit in response.get("hits", {}).get("hits", []):
                source = hit["_source"]
                highlights = hit.get("highlight", {}).get("content", [])

                message = self._parse_message(source)
                result = SearchResult(
                    message=message,
                    session_id=source.get("session_id", ""),
                    score=hit.get("_score", 0),
                    highlights=highlights
                )
                results.append(result)

            total = response.get("hits", {}).get("total", {})
            if isinstance(total, dict):
                total = total.get("value", 0)

            return results, total

        except Exception as e:
            logger.error(f"Search engine query failed: {e}")
            return [], 0

    async def _search_with_database(
        self,
        query: SearchQuery,
        processed_query: str
    ) -> tuple[List[SearchResult], int]:
        """使用資料庫搜索 (降級方案)"""
        try:
            if not self._repository:
                return [], 0

            # 構建搜索條件
            search_params = {
                "query": processed_query,
                "session_id": query.session_id,
                "user_id": query.user_id,
                "role": query.role,
                "start_date": query.start_date,
                "end_date": query.end_date,
                "limit": query.limit,
                "offset": query.offset
            }

            # 執行搜索
            messages, total = await self._repository.search_messages(**search_params)

            # 轉換為搜索結果
            results = []
            for msg in messages:
                # 計算簡單的相關性分數
                score = self._calculate_simple_score(msg.content, processed_query)

                # 生成高亮
                highlights = []
                if query.highlight:
                    highlights = self._generate_highlights(
                        msg.content,
                        processed_query,
                        query.highlight_tag
                    )

                result = SearchResult(
                    message=msg,
                    session_id=getattr(msg, 'session_id', ''),
                    score=score,
                    highlights=highlights
                )
                results.append(result)

            # 按相關性排序
            if query.sort_by == SearchSortBy.RELEVANCE:
                results.sort(key=lambda r: r.score, reverse=True)

            return results, total

        except Exception as e:
            logger.error(f"Database search failed: {e}")
            return [], 0

    def _preprocess_query(self, query: str) -> str:
        """預處理搜索查詢"""
        if not query:
            return ""

        # 移除多餘空白
        query = " ".join(query.split())

        # 移除特殊字符 (保留中文和基本標點)
        query = re.sub(r'[^\w\s\u4e00-\u9fff\u3400-\u4dbf]', ' ', query)

        return query.strip()

    def _build_filters(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """構建搜索過濾器"""
        filters = []

        if query.session_id:
            filters.append({"term": {"session_id": query.session_id}})

        if query.user_id:
            filters.append({"term": {"user_id": query.user_id}})

        if query.role:
            filters.append({"term": {"role": query.role.value}})

        if query.start_date or query.end_date:
            date_range = {}
            if query.start_date:
                date_range["gte"] = query.start_date.isoformat()
            if query.end_date:
                date_range["lte"] = query.end_date.isoformat()
            filters.append({"range": {"created_at": date_range}})

        return filters

    def _build_sort(self, sort_by: SearchSortBy) -> List[Dict[str, Any]]:
        """構建排序規則"""
        if sort_by == SearchSortBy.RELEVANCE:
            return [{"_score": "desc"}]
        elif sort_by == SearchSortBy.DATE_DESC:
            return [{"created_at": "desc"}]
        elif sort_by == SearchSortBy.DATE_ASC:
            return [{"created_at": "asc"}]
        return [{"_score": "desc"}]

    def _calculate_simple_score(self, content: str, query: str) -> float:
        """計算簡單的相關性分數"""
        if not content or not query:
            return 0.0

        content_lower = content.lower()
        query_lower = query.lower()

        # 精確匹配加分
        exact_matches = content_lower.count(query_lower)
        if exact_matches > 0:
            return 1.0 + (exact_matches * 0.1)

        # 單詞匹配
        query_words = query_lower.split()
        match_count = 0
        for word in query_words:
            if word in content_lower:
                match_count += 1

        if query_words:
            return match_count / len(query_words)

        return 0.0

    def _generate_highlights(
        self,
        content: str,
        query: str,
        tag: str
    ) -> List[str]:
        """生成高亮片段"""
        if not content or not query:
            return []

        highlights = []
        query_words = query.lower().split()

        # 找到匹配位置並生成片段
        content_lower = content.lower()
        for word in query_words:
            pos = 0
            while True:
                pos = content_lower.find(word, pos)
                if pos == -1:
                    break

                # 提取片段 (前後各 50 個字符)
                start = max(0, pos - 50)
                end = min(len(content), pos + len(word) + 50)
                snippet = content[start:end]

                # 高亮關鍵字
                highlighted = re.sub(
                    re.escape(word),
                    f"<{tag}>{word}</{tag}>",
                    snippet,
                    flags=re.IGNORECASE
                )

                if highlighted not in highlights:
                    highlights.append(highlighted)

                pos += len(word)

        return highlights[:3]  # 最多返回 3 個片段

    def _parse_message(self, source: Dict[str, Any]) -> Message:
        """從搜索結果解析訊息"""
        return Message(
            id=source.get("id", ""),
            role=MessageRole(source.get("role", "user")),
            content=source.get("content", ""),
            created_at=datetime.fromisoformat(source["created_at"])
                if source.get("created_at") else None
        )

    async def _get_suggestions(self, query: str) -> List[str]:
        """獲取搜索建議"""
        try:
            if not query or len(query) < 2:
                return []

            # 使用快取的熱門搜索
            if self._cache:
                suggestions = await self._cache.get("search:suggestions")
                if suggestions:
                    # 過濾相關的建議
                    return [
                        s for s in suggestions
                        if query.lower() in s.lower()
                    ][:5]

            return []

        except Exception as e:
            logger.error(f"Failed to get suggestions: {e}")
            return []

    async def index_message(self, message: Message, session_id: str) -> bool:
        """
        索引訊息 (用於搜索引擎)

        Args:
            message: 訊息對象
            session_id: Session ID

        Returns:
            bool: 是否索引成功
        """
        try:
            if not self._search_engine:
                return True  # 無搜索引擎時跳過

            document = {
                "id": message.id,
                "session_id": session_id,
                "role": message.role.value if hasattr(message.role, 'value') else message.role,
                "content": message.content,
                "created_at": message.created_at.isoformat() if message.created_at else None,
                "metadata": getattr(message, 'metadata', {})
            }

            await self._search_engine.index(
                index="messages",
                id=message.id,
                body=document
            )

            return True

        except Exception as e:
            logger.error(f"Failed to index message: {e}")
            return False

    async def remove_from_index(self, message_id: str) -> bool:
        """
        從索引中移除訊息

        Args:
            message_id: 訊息 ID

        Returns:
            bool: 是否移除成功
        """
        try:
            if not self._search_engine:
                return True

            await self._search_engine.delete(
                index="messages",
                id=message_id
            )
            return True

        except Exception as e:
            logger.error(f"Failed to remove message from index: {e}")
            return False

    async def reindex_session(self, session_id: str) -> int:
        """
        重新索引 Session 的所有訊息

        Args:
            session_id: Session ID

        Returns:
            int: 索引的訊息數量
        """
        try:
            if not self._repository or not self._search_engine:
                return 0

            # 獲取所有訊息
            messages = await self._repository.get_all_messages(session_id)

            # 批量索引
            indexed = 0
            for message in messages:
                if await self.index_message(message, session_id):
                    indexed += 1

            logger.info(f"Reindexed {indexed} messages for session {session_id}")
            return indexed

        except Exception as e:
            logger.error(f"Failed to reindex session: {e}")
            return 0
