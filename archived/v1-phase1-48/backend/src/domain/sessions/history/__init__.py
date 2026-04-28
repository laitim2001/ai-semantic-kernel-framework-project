"""
Session History Module

Provides conversation history management functionality for Session mode.

Components:
- HistoryManager: Main entry point for history operations
- BookmarkService: Manage message bookmarks
- SearchService: Full-text search across messages

Usage:
    from src.domain.sessions.history import HistoryManager, BookmarkService

    # History Management
    history = HistoryManager(repository=repo)
    messages = await history.get_history(session_id, limit=50)

    # Bookmarks
    bookmarks = BookmarkService(repository=repo)
    await bookmarks.create_bookmark(user_id, session_id, message_id, name="Important")
"""

from .manager import HistoryManager
from .bookmarks import BookmarkService, Bookmark
from .search import SearchService, SearchResult, SearchQuery

__all__ = [
    # History Manager
    "HistoryManager",
    # Bookmarks
    "BookmarkService",
    "Bookmark",
    # Search
    "SearchService",
    "SearchResult",
    "SearchQuery",
]
