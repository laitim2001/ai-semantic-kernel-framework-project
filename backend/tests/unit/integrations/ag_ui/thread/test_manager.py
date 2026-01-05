# =============================================================================
# IPA Platform - AG-UI Thread Manager Unit Tests
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-3: Thread Manager
#
# Unit tests for AG-UI ThreadManager.
# =============================================================================

from datetime import datetime

import pytest

from src.integrations.ag_ui.thread.manager import ThreadManager
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


class TestThreadManager:
    """Tests for ThreadManager class."""

    @pytest.fixture
    def manager(self):
        """Create ThreadManager with in-memory backends."""
        cache = ThreadCache(InMemoryCache())
        repository = InMemoryThreadRepository()
        return ThreadManager(cache=cache, repository=repository)

    @pytest.fixture
    def sample_message(self):
        """Create a sample message."""
        return AGUIMessage(
            message_id="msg-1",
            role=MessageRole.USER,
            content="Hello, assistant!",
        )

    # =============================================================================
    # Thread Creation Tests
    # =============================================================================

    @pytest.mark.asyncio
    async def test_get_or_create_new_thread(self, manager):
        """Test creating a new thread when no ID provided."""
        thread = await manager.get_or_create()

        assert thread is not None
        assert thread.thread_id.startswith("thread-")
        assert thread.status == ThreadStatus.ACTIVE
        assert thread.run_count == 0
        assert thread.messages == []

    @pytest.mark.asyncio
    async def test_get_or_create_new_thread_with_metadata(self, manager):
        """Test creating a new thread with metadata."""
        metadata = {"source": "test", "user_id": "user-123"}
        thread = await manager.get_or_create(metadata=metadata)

        assert thread.metadata["source"] == "test"
        assert thread.metadata["user_id"] == "user-123"

    @pytest.mark.asyncio
    async def test_get_or_create_existing_thread(self, manager):
        """Test retrieving an existing thread."""
        # Create a thread first
        thread1 = await manager.get_or_create()
        thread_id = thread1.thread_id

        # Retrieve it
        thread2 = await manager.get_or_create(thread_id)

        assert thread2.thread_id == thread_id

    @pytest.mark.asyncio
    async def test_get_or_create_nonexistent_creates_new(self, manager):
        """Test that requesting nonexistent thread creates a new one."""
        thread = await manager.get_or_create("nonexistent-thread-id")

        # Should create a new thread since the ID doesn't exist
        assert thread is not None
        assert thread.thread_id.startswith("thread-")

    # =============================================================================
    # Thread Retrieval Tests
    # =============================================================================

    @pytest.mark.asyncio
    async def test_get_existing_thread(self, manager):
        """Test getting an existing thread."""
        # Create a thread
        created = await manager.get_or_create()

        # Get it
        thread = await manager.get(created.thread_id)

        assert thread is not None
        assert thread.thread_id == created.thread_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_thread(self, manager):
        """Test getting a nonexistent thread returns None."""
        thread = await manager.get("nonexistent")
        assert thread is None

    @pytest.mark.asyncio
    async def test_get_uses_cache(self, manager):
        """Test that get() uses cache for subsequent calls."""
        thread = await manager.get_or_create()
        thread_id = thread.thread_id

        # First get populates cache
        result1 = await manager.get(thread_id)
        # Second get should use cache
        result2 = await manager.get(thread_id)

        assert result1 is not None
        assert result2 is not None
        assert result1.thread_id == result2.thread_id

    # =============================================================================
    # Message Operations Tests
    # =============================================================================

    @pytest.mark.asyncio
    async def test_append_messages(self, manager, sample_message):
        """Test appending messages to a thread."""
        thread = await manager.get_or_create()

        updated = await manager.append_messages(thread.thread_id, [sample_message])

        assert len(updated.messages) == 1
        assert updated.messages[0].content == "Hello, assistant!"

    @pytest.mark.asyncio
    async def test_append_multiple_messages(self, manager):
        """Test appending multiple messages."""
        thread = await manager.get_or_create()

        messages = [
            AGUIMessage(message_id="msg-1", role=MessageRole.USER, content="Hi"),
            AGUIMessage(message_id="msg-2", role=MessageRole.ASSISTANT, content="Hello!"),
            AGUIMessage(message_id="msg-3", role=MessageRole.USER, content="How are you?"),
        ]
        updated = await manager.append_messages(thread.thread_id, messages)

        assert len(updated.messages) == 3
        assert updated.messages[0].role == MessageRole.USER
        assert updated.messages[1].role == MessageRole.ASSISTANT

    @pytest.mark.asyncio
    async def test_append_message_convenience(self, manager):
        """Test append_message convenience method."""
        thread = await manager.get_or_create()

        updated = await manager.append_message(
            thread_id=thread.thread_id,
            role=MessageRole.USER,
            content="Test message",
            metadata={"importance": "high"},
        )

        assert len(updated.messages) == 1
        assert updated.messages[0].content == "Test message"
        assert updated.messages[0].metadata["importance"] == "high"

    @pytest.mark.asyncio
    async def test_append_message_generates_id(self, manager):
        """Test that append_message generates message ID if not provided."""
        thread = await manager.get_or_create()

        updated = await manager.append_message(
            thread_id=thread.thread_id,
            role=MessageRole.USER,
            content="No ID provided",
        )

        assert updated.messages[0].message_id.startswith("msg-")

    @pytest.mark.asyncio
    async def test_get_messages(self, manager):
        """Test getting messages from a thread."""
        thread = await manager.get_or_create()
        messages = [
            AGUIMessage(message_id=f"msg-{i}", role=MessageRole.USER, content=f"Msg {i}")
            for i in range(5)
        ]
        await manager.append_messages(thread.thread_id, messages)

        result = await manager.get_messages(thread.thread_id)
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_get_messages_with_limit(self, manager):
        """Test getting messages with limit."""
        thread = await manager.get_or_create()
        messages = [
            AGUIMessage(message_id=f"msg-{i}", role=MessageRole.USER, content=f"Msg {i}")
            for i in range(5)
        ]
        await manager.append_messages(thread.thread_id, messages)

        result = await manager.get_messages(thread.thread_id, limit=3)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_get_messages_with_offset(self, manager):
        """Test getting messages with offset."""
        thread = await manager.get_or_create()
        messages = [
            AGUIMessage(message_id=f"msg-{i}", role=MessageRole.USER, content=f"Msg {i}")
            for i in range(5)
        ]
        await manager.append_messages(thread.thread_id, messages)

        result = await manager.get_messages(thread.thread_id, offset=2, limit=2)
        assert len(result) == 2
        assert result[0].message_id == "msg-2"

    @pytest.mark.asyncio
    async def test_clear_messages(self, manager):
        """Test clearing all messages from a thread."""
        thread = await manager.get_or_create()
        await manager.append_message(
            thread.thread_id, MessageRole.USER, "Test"
        )

        updated = await manager.clear_messages(thread.thread_id)
        assert len(updated.messages) == 0

    # =============================================================================
    # State Operations Tests
    # =============================================================================

    @pytest.mark.asyncio
    async def test_update_state(self, manager):
        """Test updating thread state."""
        thread = await manager.get_or_create()

        updated = await manager.update_state(
            thread.thread_id,
            {"key1": "value1", "key2": 42},
        )

        assert updated.state["key1"] == "value1"
        assert updated.state["key2"] == 42

    @pytest.mark.asyncio
    async def test_update_state_merges(self, manager):
        """Test that update_state merges with existing state."""
        thread = await manager.get_or_create()
        await manager.update_state(thread.thread_id, {"existing": "value"})

        updated = await manager.update_state(thread.thread_id, {"new": "data"})

        assert updated.state["existing"] == "value"
        assert updated.state["new"] == "data"

    @pytest.mark.asyncio
    async def test_set_state_replaces(self, manager):
        """Test that set_state replaces entire state."""
        thread = await manager.get_or_create()
        await manager.update_state(thread.thread_id, {"old": "data"})

        updated = await manager.set_state(thread.thread_id, {"new": "state"})

        assert "old" not in updated.state
        assert updated.state["new"] == "state"

    @pytest.mark.asyncio
    async def test_get_state(self, manager):
        """Test getting thread state."""
        thread = await manager.get_or_create()
        await manager.update_state(thread.thread_id, {"key": "value"})

        state = await manager.get_state(thread.thread_id)
        assert state["key"] == "value"

    @pytest.mark.asyncio
    async def test_get_state_nonexistent_raises(self, manager):
        """Test getting state for nonexistent thread raises."""
        with pytest.raises(ValueError, match="not found"):
            await manager.get_state("nonexistent")

    # =============================================================================
    # Run Count Tests
    # =============================================================================

    @pytest.mark.asyncio
    async def test_increment_run_count(self, manager):
        """Test incrementing run count."""
        thread = await manager.get_or_create()
        assert thread.run_count == 0

        count = await manager.increment_run_count(thread.thread_id)
        assert count == 1

        count = await manager.increment_run_count(thread.thread_id)
        assert count == 2

    @pytest.mark.asyncio
    async def test_increment_run_count_persists(self, manager):
        """Test that run count persists."""
        thread = await manager.get_or_create()
        await manager.increment_run_count(thread.thread_id)
        await manager.increment_run_count(thread.thread_id)

        retrieved = await manager.get(thread.thread_id)
        assert retrieved.run_count == 2

    # =============================================================================
    # Archive and Delete Tests
    # =============================================================================

    @pytest.mark.asyncio
    async def test_archive_thread(self, manager):
        """Test archiving a thread."""
        thread = await manager.get_or_create()
        assert thread.status == ThreadStatus.ACTIVE

        archived = await manager.archive(thread.thread_id)
        assert archived.status == ThreadStatus.ARCHIVED
        assert not archived.is_active

    @pytest.mark.asyncio
    async def test_archive_nonexistent_raises(self, manager):
        """Test archiving nonexistent thread raises."""
        with pytest.raises(ValueError, match="not found"):
            await manager.archive("nonexistent")

    @pytest.mark.asyncio
    async def test_delete_thread(self, manager):
        """Test deleting a thread."""
        thread = await manager.get_or_create()

        deleted = await manager.delete(thread.thread_id)
        assert deleted is True

        # Verify it's gone
        result = await manager.get(thread.thread_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, manager):
        """Test deleting nonexistent thread returns False."""
        deleted = await manager.delete("nonexistent")
        assert deleted is False

    # =============================================================================
    # List Operations Tests
    # =============================================================================

    @pytest.mark.asyncio
    async def test_list_active(self, manager):
        """Test listing active threads."""
        # Create some active threads
        for _ in range(3):
            await manager.get_or_create()

        # Archive one
        threads = await manager.list_active()
        if threads:
            await manager.archive(threads[0].thread_id)

        # List active should show fewer
        active = await manager.list_active()
        assert len(active) == 2

    @pytest.mark.asyncio
    async def test_list_active_pagination(self, manager):
        """Test listing active threads with pagination."""
        for _ in range(5):
            await manager.get_or_create()

        result = await manager.list_active(limit=2, offset=1)
        assert len(result) == 2

    # =============================================================================
    # Write-Through Pattern Tests
    # =============================================================================

    @pytest.mark.asyncio
    async def test_write_through_saves_to_both(self, manager):
        """Test that writes go to both cache and repository."""
        thread = await manager.get_or_create()

        # Check cache has it
        cached = await manager.cache.get(thread.thread_id)
        assert cached is not None

        # Check repository has it
        stored = await manager.repository.get_by_id(thread.thread_id)
        assert stored is not None

    @pytest.mark.asyncio
    async def test_cache_populated_on_repo_read(self, manager):
        """Test that cache is populated when reading from repository."""
        # Create thread
        thread = await manager.get_or_create()
        thread_id = thread.thread_id

        # Clear cache manually
        await manager.cache.delete(thread_id)

        # Get should populate cache from repo
        result = await manager.get(thread_id)
        assert result is not None

        # Cache should now have it
        cached = await manager.cache.get(thread_id)
        assert cached is not None

    # =============================================================================
    # Error Handling Tests
    # =============================================================================

    @pytest.mark.asyncio
    async def test_update_state_nonexistent_raises(self, manager):
        """Test updating state for nonexistent thread raises."""
        with pytest.raises(ValueError, match="not found"):
            await manager.update_state("nonexistent", {"key": "value"})

    @pytest.mark.asyncio
    async def test_set_state_nonexistent_raises(self, manager):
        """Test setting state for nonexistent thread raises."""
        with pytest.raises(ValueError, match="not found"):
            await manager.set_state("nonexistent", {"key": "value"})

    @pytest.mark.asyncio
    async def test_increment_run_count_nonexistent_raises(self, manager):
        """Test incrementing run count for nonexistent thread raises."""
        with pytest.raises(ValueError, match="not found"):
            await manager.increment_run_count("nonexistent")

    @pytest.mark.asyncio
    async def test_get_messages_nonexistent_raises(self, manager):
        """Test getting messages for nonexistent thread raises."""
        with pytest.raises(ValueError, match="not found"):
            await manager.get_messages("nonexistent")

    @pytest.mark.asyncio
    async def test_clear_messages_nonexistent_raises(self, manager):
        """Test clearing messages for nonexistent thread raises."""
        with pytest.raises(ValueError, match="not found"):
            await manager.clear_messages("nonexistent")


class TestThreadManagerConcurrency:
    """Tests for ThreadManager concurrent operations."""

    @pytest.fixture
    def manager(self):
        """Create ThreadManager with in-memory backends."""
        cache = ThreadCache(InMemoryCache())
        repository = InMemoryThreadRepository()
        return ThreadManager(cache=cache, repository=repository)

    @pytest.mark.asyncio
    async def test_multiple_runs_same_thread(self, manager):
        """Test multiple runs on the same thread."""
        thread = await manager.get_or_create()
        thread_id = thread.thread_id

        # Simulate multiple runs
        for i in range(3):
            await manager.increment_run_count(thread_id)
            await manager.append_message(
                thread_id,
                MessageRole.USER,
                f"Run {i + 1} message",
            )

        final = await manager.get(thread_id)
        assert final.run_count == 3
        assert len(final.messages) == 3

    @pytest.mark.asyncio
    async def test_state_isolation(self, manager):
        """Test that different threads have isolated state."""
        thread1 = await manager.get_or_create()
        thread2 = await manager.get_or_create()

        await manager.update_state(thread1.thread_id, {"thread": 1})
        await manager.update_state(thread2.thread_id, {"thread": 2})

        state1 = await manager.get_state(thread1.thread_id)
        state2 = await manager.get_state(thread2.thread_id)

        assert state1["thread"] == 1
        assert state2["thread"] == 2
