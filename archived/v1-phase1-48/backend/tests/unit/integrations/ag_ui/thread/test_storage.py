# =============================================================================
# IPA Platform - AG-UI Thread Storage Unit Tests
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-3: Thread Manager
#
# Unit tests for AG-UI Thread storage backends.
# =============================================================================

from datetime import datetime

import pytest

from src.integrations.ag_ui.thread.models import (
    AGUIMessage,
    AGUIThread,
    MessageRole,
    ThreadStatus,
)
from src.integrations.ag_ui.thread.storage import (
    InMemoryCache,
    InMemoryThreadRepository,
    ThreadCache,
)


class TestInMemoryCache:
    """Tests for InMemoryCache implementation."""

    @pytest.fixture
    def cache(self):
        """Create fresh cache for each test."""
        return InMemoryCache()

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache):
        """Test setting and getting values."""
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, cache):
        """Test getting nonexistent key."""
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, cache):
        """Test setting with TTL."""
        await cache.set("key1", "value1", ttl=3600)
        result = await cache.get("key1")
        assert result == "value1"
        # Note: In-memory cache doesn't actually expire

    @pytest.mark.asyncio
    async def test_delete(self, cache):
        """Test deleting a key."""
        await cache.set("key1", "value1")
        assert await cache.exists("key1")

        result = await cache.delete("key1")
        assert result is True
        assert not await cache.exists("key1")

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, cache):
        """Test deleting nonexistent key."""
        result = await cache.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists(self, cache):
        """Test checking key existence."""
        assert not await cache.exists("key1")
        await cache.set("key1", "value1")
        assert await cache.exists("key1")

    @pytest.mark.asyncio
    async def test_clear(self, cache):
        """Test clearing all cache entries."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.clear()

        assert not await cache.exists("key1")
        assert not await cache.exists("key2")


class TestThreadCache:
    """Tests for ThreadCache implementation."""

    @pytest.fixture
    def cache(self):
        """Create thread cache with in-memory backend."""
        return ThreadCache(InMemoryCache())

    @pytest.fixture
    def sample_thread(self):
        """Create a sample thread for testing."""
        return AGUIThread(
            thread_id="thread-123",
            messages=[
                AGUIMessage(message_id="msg-1", role=MessageRole.USER, content="Hi"),
            ],
            state={"key": "value"},
            metadata={"source": "test"},
        )

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache, sample_thread):
        """Test caching and retrieving a thread."""
        await cache.set(sample_thread)
        result = await cache.get(sample_thread.thread_id)

        assert result is not None
        assert result.thread_id == sample_thread.thread_id
        assert len(result.messages) == 1
        assert result.state["key"] == "value"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, cache):
        """Test getting nonexistent thread."""
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, cache, sample_thread):
        """Test deleting a thread from cache."""
        await cache.set(sample_thread)
        assert await cache.exists(sample_thread.thread_id)

        result = await cache.delete(sample_thread.thread_id)
        assert result is True
        assert not await cache.exists(sample_thread.thread_id)

    @pytest.mark.asyncio
    async def test_exists(self, cache, sample_thread):
        """Test checking thread existence."""
        assert not await cache.exists(sample_thread.thread_id)
        await cache.set(sample_thread)
        assert await cache.exists(sample_thread.thread_id)

    @pytest.mark.asyncio
    async def test_custom_ttl(self, cache, sample_thread):
        """Test setting custom TTL."""
        await cache.set(sample_thread, ttl=3600)
        result = await cache.get(sample_thread.thread_id)
        assert result is not None

    @pytest.mark.asyncio
    async def test_key_prefix(self, sample_thread):
        """Test custom key prefix."""
        inner_cache = InMemoryCache()
        cache = ThreadCache(inner_cache, key_prefix="custom_prefix")

        await cache.set(sample_thread)

        # Check internal key format
        expected_key = f"custom_prefix:{sample_thread.thread_id}"
        assert await inner_cache.exists(expected_key)

    @pytest.mark.asyncio
    async def test_refresh_ttl(self, cache, sample_thread):
        """Test refreshing TTL for cached thread."""
        await cache.set(sample_thread)

        result = await cache.refresh_ttl(sample_thread.thread_id, ttl=7200)
        assert result is True

        # Thread should still be accessible
        thread = await cache.get(sample_thread.thread_id)
        assert thread is not None

    @pytest.mark.asyncio
    async def test_refresh_ttl_nonexistent(self, cache):
        """Test refreshing TTL for nonexistent thread."""
        result = await cache.refresh_ttl("nonexistent")
        assert result is False


class TestInMemoryThreadRepository:
    """Tests for InMemoryThreadRepository implementation."""

    @pytest.fixture
    def repository(self):
        """Create fresh repository for each test."""
        return InMemoryThreadRepository()

    @pytest.fixture
    def sample_thread(self):
        """Create a sample thread for testing."""
        return AGUIThread(
            thread_id="thread-123",
            messages=[
                AGUIMessage(message_id="msg-1", role=MessageRole.USER, content="Hi"),
            ],
            state={"key": "value"},
        )

    @pytest.mark.asyncio
    async def test_save_and_get(self, repository, sample_thread):
        """Test saving and retrieving a thread."""
        await repository.save(sample_thread)
        result = await repository.get_by_id(sample_thread.thread_id)

        assert result is not None
        assert result.thread_id == sample_thread.thread_id
        assert len(result.messages) == 1

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, repository):
        """Test getting nonexistent thread."""
        result = await repository.get_by_id("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, repository, sample_thread):
        """Test deleting a thread."""
        await repository.save(sample_thread)
        result = await repository.delete(sample_thread.thread_id)

        assert result is True
        assert await repository.get_by_id(sample_thread.thread_id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, repository):
        """Test deleting nonexistent thread."""
        result = await repository.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_by_status(self, repository):
        """Test listing threads by status."""
        # Create threads with different statuses
        active_thread = AGUIThread(thread_id="active-1", status=ThreadStatus.ACTIVE)
        archived_thread = AGUIThread(thread_id="archived-1", status=ThreadStatus.ARCHIVED)

        await repository.save(active_thread)
        await repository.save(archived_thread)

        active_list = await repository.list_by_status("active")
        assert len(active_list) == 1
        assert active_list[0].thread_id == "active-1"

        archived_list = await repository.list_by_status("archived")
        assert len(archived_list) == 1
        assert archived_list[0].thread_id == "archived-1"

    @pytest.mark.asyncio
    async def test_list_by_status_with_pagination(self, repository):
        """Test listing threads with pagination."""
        # Create multiple active threads
        for i in range(5):
            thread = AGUIThread(thread_id=f"thread-{i}", status=ThreadStatus.ACTIVE)
            await repository.save(thread)

        result = await repository.list_by_status("active", limit=2, offset=1)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_all(self, repository):
        """Test listing all threads."""
        for i in range(3):
            thread = AGUIThread(thread_id=f"thread-{i}")
            await repository.save(thread)

        result = await repository.list_all()
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_list_all_with_pagination(self, repository):
        """Test listing all threads with pagination."""
        for i in range(5):
            thread = AGUIThread(thread_id=f"thread-{i}")
            await repository.save(thread)

        result = await repository.list_all(limit=2, offset=1)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_count(self, repository):
        """Test counting threads."""
        assert await repository.count() == 0

        for i in range(3):
            thread = AGUIThread(thread_id=f"thread-{i}")
            await repository.save(thread)

        assert await repository.count() == 3

    @pytest.mark.asyncio
    async def test_clear(self, repository):
        """Test clearing all threads."""
        for i in range(3):
            thread = AGUIThread(thread_id=f"thread-{i}")
            await repository.save(thread)

        await repository.clear()
        assert await repository.count() == 0

    @pytest.mark.asyncio
    async def test_update_existing_thread(self, repository, sample_thread):
        """Test updating an existing thread."""
        await repository.save(sample_thread)

        # Modify and save again
        sample_thread.state["new_key"] = "new_value"
        sample_thread.messages.append(
            AGUIMessage(message_id="msg-2", role=MessageRole.ASSISTANT, content="Hello!")
        )
        await repository.save(sample_thread)

        result = await repository.get_by_id(sample_thread.thread_id)
        assert result.state["new_key"] == "new_value"
        assert len(result.messages) == 2
