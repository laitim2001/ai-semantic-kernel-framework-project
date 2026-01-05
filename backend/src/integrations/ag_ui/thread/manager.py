# =============================================================================
# IPA Platform - AG-UI Thread Manager
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-3: Thread Manager
#
# Thread Manager for AG-UI conversation threads.
# Manages thread lifecycle, message storage, and state persistence.
#
# Architecture:
#   - Write-Through pattern: Writes go to both cache and repository
#   - Cache-First reads: Check cache before repository
#   - Automatic thread creation when thread_id is None
#
# Dependencies:
#   - ThreadCache (storage.py)
#   - ThreadRepository (storage.py)
# =============================================================================

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import AGUIMessage, AGUIThread, MessageRole, ThreadStatus
from .storage import ThreadCache, ThreadRepository

logger = logging.getLogger(__name__)


class ThreadManager:
    """
    Thread Manager for AG-UI conversations.

    Manages the lifecycle of conversation threads including creation,
    retrieval, message storage, and state management. Uses Write-Through
    caching pattern for performance with durability.

    Attributes:
        cache: ThreadCache for fast reads
        repository: ThreadRepository for persistence
        default_ttl: Default cache TTL in seconds
    """

    def __init__(
        self,
        cache: ThreadCache,
        repository: ThreadRepository,
        default_ttl: int = 7200,  # 2 hours
    ):
        """
        Initialize ThreadManager.

        Args:
            cache: ThreadCache instance for caching
            repository: ThreadRepository instance for persistence
            default_ttl: Default TTL for cached threads
        """
        self.cache = cache
        self.repository = repository
        self.default_ttl = default_ttl

    async def get_or_create(
        self,
        thread_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AGUIThread:
        """
        Get existing thread or create a new one.

        If thread_id is provided, attempts to retrieve the existing thread.
        If not found or thread_id is None, creates a new thread.

        Args:
            thread_id: Optional thread ID to retrieve
            metadata: Optional metadata for new thread

        Returns:
            AGUIThread - existing or newly created

        Example:
            >>> thread = await manager.get_or_create()  # Create new
            >>> thread = await manager.get_or_create("thread-123")  # Get existing
        """
        if thread_id:
            # Try cache first
            thread = await self.cache.get(thread_id)
            if thread:
                logger.debug(f"Retrieved thread {thread_id} from cache")
                return thread

            # Try repository
            thread = await self.repository.get_by_id(thread_id)
            if thread:
                logger.debug(f"Retrieved thread {thread_id} from repository")
                # Populate cache for future reads
                await self.cache.set(thread, ttl=self.default_ttl)
                return thread

            logger.warning(f"Thread {thread_id} not found, creating new")

        # Create new thread
        return await self._create_thread(metadata=metadata)

    async def get(self, thread_id: str) -> Optional[AGUIThread]:
        """
        Get thread by ID.

        Cache-first retrieval: checks cache, then repository.

        Args:
            thread_id: Thread ID to retrieve

        Returns:
            AGUIThread if found, None otherwise
        """
        # Try cache first
        thread = await self.cache.get(thread_id)
        if thread:
            return thread

        # Try repository
        thread = await self.repository.get_by_id(thread_id)
        if thread:
            # Populate cache
            await self.cache.set(thread, ttl=self.default_ttl)
            return thread

        return None

    async def append_messages(
        self,
        thread_id: str,
        messages: List[AGUIMessage],
    ) -> AGUIThread:
        """
        Append messages to a thread.

        Retrieves the thread, adds messages, and persists changes
        using Write-Through pattern.

        Args:
            thread_id: Thread ID to append to
            messages: List of messages to append

        Returns:
            Updated AGUIThread

        Raises:
            ValueError: If thread not found
        """
        thread = await self.get_or_create(thread_id)

        for message in messages:
            thread.add_message(message)

        await self._save(thread)
        logger.debug(f"Appended {len(messages)} messages to thread {thread_id}")
        return thread

    async def append_message(
        self,
        thread_id: str,
        role: MessageRole,
        content: str,
        message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_call_id: Optional[str] = None,
    ) -> AGUIThread:
        """
        Append a single message to a thread.

        Convenience method for adding one message.

        Args:
            thread_id: Thread ID to append to
            role: Message role
            content: Message content
            message_id: Optional message ID (auto-generated if not provided)
            metadata: Optional message metadata
            tool_calls: Optional tool calls
            tool_call_id: Optional tool call ID for tool responses

        Returns:
            Updated AGUIThread
        """
        message = AGUIMessage(
            message_id=message_id or f"msg-{uuid.uuid4().hex[:8]}",
            role=role,
            content=content,
            metadata=metadata or {},
            tool_calls=tool_calls or [],
            tool_call_id=tool_call_id,
        )
        return await self.append_messages(thread_id, [message])

    async def update_state(
        self,
        thread_id: str,
        state_updates: Dict[str, Any],
    ) -> AGUIThread:
        """
        Update thread state.

        Merges new state values with existing state and persists.

        Args:
            thread_id: Thread ID to update
            state_updates: State key-value pairs to update

        Returns:
            Updated AGUIThread

        Raises:
            ValueError: If thread not found
        """
        thread = await self.get(thread_id)
        if not thread:
            raise ValueError(f"Thread {thread_id} not found")

        thread.update_state(state_updates)
        await self._save(thread)
        logger.debug(f"Updated state for thread {thread_id}")
        return thread

    async def set_state(
        self,
        thread_id: str,
        state: Dict[str, Any],
    ) -> AGUIThread:
        """
        Replace thread state entirely.

        Args:
            thread_id: Thread ID to update
            state: New state to set

        Returns:
            Updated AGUIThread

        Raises:
            ValueError: If thread not found
        """
        thread = await self.get(thread_id)
        if not thread:
            raise ValueError(f"Thread {thread_id} not found")

        thread.state = state
        thread.updated_at = datetime.utcnow()
        await self._save(thread)
        logger.debug(f"Set state for thread {thread_id}")
        return thread

    async def increment_run_count(
        self,
        thread_id: str,
    ) -> int:
        """
        Increment and return the run count for a thread.

        Called when a new run starts in the thread.

        Args:
            thread_id: Thread ID to increment

        Returns:
            New run count

        Raises:
            ValueError: If thread not found
        """
        thread = await self.get(thread_id)
        if not thread:
            raise ValueError(f"Thread {thread_id} not found")

        new_count = thread.increment_run_count()
        await self._save(thread)
        logger.debug(f"Incremented run count for thread {thread_id} to {new_count}")
        return new_count

    async def archive(self, thread_id: str) -> AGUIThread:
        """
        Archive a thread.

        Sets thread status to ARCHIVED.

        Args:
            thread_id: Thread ID to archive

        Returns:
            Updated AGUIThread

        Raises:
            ValueError: If thread not found
        """
        thread = await self.get(thread_id)
        if not thread:
            raise ValueError(f"Thread {thread_id} not found")

        thread.archive()
        await self._save(thread)
        logger.info(f"Archived thread {thread_id}")
        return thread

    async def delete(self, thread_id: str) -> bool:
        """
        Delete a thread.

        Removes from both cache and repository.

        Args:
            thread_id: Thread ID to delete

        Returns:
            True if deleted, False if not found
        """
        # Delete from cache
        await self.cache.delete(thread_id)

        # Delete from repository
        deleted = await self.repository.delete(thread_id)

        if deleted:
            logger.info(f"Deleted thread {thread_id}")
        else:
            logger.warning(f"Thread {thread_id} not found for deletion")

        return deleted

    async def list_active(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AGUIThread]:
        """
        List active threads.

        Args:
            limit: Maximum threads to return
            offset: Number of threads to skip

        Returns:
            List of active threads
        """
        return await self.repository.list_by_status(
            status=ThreadStatus.ACTIVE.value,
            limit=limit,
            offset=offset,
        )

    async def _create_thread(
        self,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AGUIThread:
        """
        Create a new thread.

        Args:
            metadata: Optional initial metadata

        Returns:
            New AGUIThread
        """
        thread_id = f"thread-{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow()

        thread = AGUIThread(
            thread_id=thread_id,
            created_at=now,
            updated_at=now,
            messages=[],
            state={},
            metadata=metadata or {},
            status=ThreadStatus.ACTIVE,
            run_count=0,
        )

        await self._save(thread)
        logger.info(f"Created new thread {thread_id}")
        return thread

    async def _save(self, thread: AGUIThread) -> None:
        """
        Save thread using Write-Through pattern.

        Writes to both cache and repository for durability.

        Args:
            thread: Thread to save
        """
        # Update timestamp
        thread.updated_at = datetime.utcnow()

        # Write-Through: save to both cache and repository
        await self.cache.set(thread, ttl=self.default_ttl)
        await self.repository.save(thread)

        logger.debug(f"Saved thread {thread.thread_id} (Write-Through)")

    async def get_messages(
        self,
        thread_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[AGUIMessage]:
        """
        Get messages from a thread.

        Args:
            thread_id: Thread ID
            limit: Maximum messages to return (None = all)
            offset: Number of messages to skip

        Returns:
            List of messages

        Raises:
            ValueError: If thread not found
        """
        thread = await self.get(thread_id)
        if not thread:
            raise ValueError(f"Thread {thread_id} not found")

        messages = thread.messages[offset:]
        if limit is not None:
            messages = messages[:limit]

        return messages

    async def get_state(self, thread_id: str) -> Dict[str, Any]:
        """
        Get thread state.

        Args:
            thread_id: Thread ID

        Returns:
            Thread state dictionary

        Raises:
            ValueError: If thread not found
        """
        thread = await self.get(thread_id)
        if not thread:
            raise ValueError(f"Thread {thread_id} not found")

        return thread.state

    async def clear_messages(self, thread_id: str) -> AGUIThread:
        """
        Clear all messages from a thread.

        Args:
            thread_id: Thread ID

        Returns:
            Updated AGUIThread

        Raises:
            ValueError: If thread not found
        """
        thread = await self.get(thread_id)
        if not thread:
            raise ValueError(f"Thread {thread_id} not found")

        thread.messages = []
        thread.updated_at = datetime.utcnow()
        await self._save(thread)
        logger.debug(f"Cleared messages for thread {thread_id}")
        return thread
