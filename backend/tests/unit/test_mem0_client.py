# =============================================================================
# IPA Platform - mem0 Client Unit Tests
# =============================================================================
# Sprint 90: S90-3 - mem0_client.py 單元測試 (5 pts)
#
# Comprehensive unit tests for the Mem0Client class.
# Uses mocking to isolate external API calls (OpenAI, Anthropic, Qdrant).
# =============================================================================

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from src.integrations.memory.mem0_client import Mem0Client
from src.integrations.memory.types import (
    MemoryConfig,
    MemoryLayer,
    MemoryMetadata,
    MemoryRecord,
    MemorySearchQuery,
    MemorySearchResult,
    MemoryType,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def memory_config():
    """Create a test memory configuration."""
    return MemoryConfig(
        qdrant_path="/tmp/test_qdrant",
        qdrant_collection="test_memories",
        embedding_model="text-embedding-3-small",
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-20250514",
        working_memory_ttl=1800,
        session_memory_ttl=604800,
        enabled=True,
    )


@pytest.fixture
def mock_mem0_memory():
    """Create a mock mem0 Memory instance."""
    mock = MagicMock()
    mock.add = MagicMock(return_value={"id": "mem_123"})
    mock.search = MagicMock(return_value=[])
    mock.get_all = MagicMock(return_value=[])
    mock.get = MagicMock(return_value=None)
    mock.update = MagicMock(return_value=True)
    mock.delete = MagicMock(return_value=True)
    mock.delete_all = MagicMock(return_value=True)
    mock.history = MagicMock(return_value=[])
    return mock


@pytest.fixture
def mem0_client(memory_config):
    """Create a Mem0Client instance for testing."""
    return Mem0Client(config=memory_config)


# =============================================================================
# Initialization Tests
# =============================================================================


class TestMem0ClientInitialization:
    """Tests for Mem0Client initialization."""

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        client = Mem0Client()
        assert client.config is not None
        assert client._memory is None
        assert client._initialized is False

    def test_init_with_custom_config(self, memory_config):
        """Test initialization with custom configuration."""
        client = Mem0Client(config=memory_config)
        assert client.config == memory_config
        assert client.config.qdrant_path == "/tmp/test_qdrant"
        assert client.config.qdrant_collection == "test_memories"

    @pytest.mark.asyncio
    async def test_initialize_success(self, mem0_client, mock_mem0_memory):
        """Test successful initialization."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.return_value = mock_mem0_memory

            await mem0_client.initialize()

            assert mem0_client._initialized is True
            assert mem0_client._memory is not None
            MockMemory.from_config.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, mem0_client, mock_mem0_memory):
        """Test that initialize is idempotent."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.return_value = mock_mem0_memory

            await mem0_client.initialize()
            await mem0_client.initialize()  # Second call should be no-op

            # Should only be called once
            assert MockMemory.from_config.call_count == 1

    @pytest.mark.asyncio
    async def test_initialize_import_error(self, mem0_client):
        """Test initialization when mem0 is not installed."""
        import sys

        # Temporarily remove mem0 from sys.modules to simulate not installed
        mem0_module = sys.modules.get("mem0")
        try:
            sys.modules["mem0"] = None  # This makes import fail
            with pytest.raises((ImportError, TypeError)):
                await mem0_client.initialize()
        finally:
            # Restore the module
            if mem0_module is not None:
                sys.modules["mem0"] = mem0_module
            elif "mem0" in sys.modules:
                del sys.modules["mem0"]

    @pytest.mark.asyncio
    async def test_initialize_config_error(self, mem0_client):
        """Test initialization with invalid configuration."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.side_effect = Exception("Invalid config")

            with pytest.raises(Exception) as exc_info:
                await mem0_client.initialize()

            assert "Invalid config" in str(exc_info.value)

    def test_ensure_initialized_not_initialized(self, mem0_client):
        """Test that operations fail when not initialized."""
        with pytest.raises(RuntimeError) as exc_info:
            mem0_client._ensure_initialized()

        assert "not initialized" in str(exc_info.value).lower()


# =============================================================================
# Add Memory Tests
# =============================================================================


class TestMem0ClientAddMemory:
    """Tests for add_memory operation."""

    @pytest.mark.asyncio
    async def test_add_memory_success(self, mem0_client, mock_mem0_memory):
        """Test successful memory addition."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.return_value = mock_mem0_memory
            mock_mem0_memory.add.return_value = {"id": "mem_456"}

            await mem0_client.initialize()
            result = await mem0_client.add_memory(
                content="User prefers dark mode",
                user_id="user_123",
                memory_type=MemoryType.USER_PREFERENCE,
            )

            assert isinstance(result, MemoryRecord)
            assert result.id == "mem_456"
            assert result.user_id == "user_123"
            assert result.content == "User prefers dark mode"
            assert result.memory_type == MemoryType.USER_PREFERENCE
            assert result.layer == MemoryLayer.LONG_TERM

    @pytest.mark.asyncio
    async def test_add_memory_with_metadata(self, mem0_client, mock_mem0_memory):
        """Test memory addition with metadata."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.return_value = mock_mem0_memory
            mock_mem0_memory.add.return_value = {"id": "mem_789"}

            await mem0_client.initialize()

            metadata = MemoryMetadata(
                source="chat",
                session_id="session_123",
                importance=0.8,
                tags=["preference", "ui"],
            )

            result = await mem0_client.add_memory(
                content="User prefers light theme",
                user_id="user_123",
                memory_type=MemoryType.USER_PREFERENCE,
                metadata=metadata,
            )

            assert result.metadata.source == "chat"
            assert result.metadata.session_id == "session_123"
            assert result.metadata.importance == 0.8

            # Verify metadata was passed to mem0
            call_kwargs = mock_mem0_memory.add.call_args[1]
            assert "metadata" in call_kwargs
            assert call_kwargs["metadata"]["source"] == "chat"

    @pytest.mark.asyncio
    async def test_add_memory_not_initialized(self, mem0_client):
        """Test that add_memory fails when not initialized."""
        with pytest.raises(RuntimeError):
            await mem0_client.add_memory(
                content="test",
                user_id="user_123",
            )

    @pytest.mark.asyncio
    async def test_add_memory_error(self, mem0_client, mock_mem0_memory):
        """Test error handling in add_memory."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.return_value = mock_mem0_memory
            mock_mem0_memory.add.side_effect = Exception("Storage error")

            await mem0_client.initialize()

            with pytest.raises(Exception) as exc_info:
                await mem0_client.add_memory(
                    content="test",
                    user_id="user_123",
                )

            assert "Storage error" in str(exc_info.value)


# =============================================================================
# Search Memory Tests
# =============================================================================


class TestMem0ClientSearchMemory:
    """Tests for search_memory operation."""

    @pytest.mark.asyncio
    async def test_search_memory_success(self, mem0_client, mock_mem0_memory):
        """Test successful memory search."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.return_value = mock_mem0_memory
            mock_mem0_memory.search.return_value = [
                {
                    "id": "mem_001",
                    "memory": "User prefers dark mode",
                    "score": 0.95,
                    "metadata": {
                        "memory_type": "user_preference",
                        "source": "chat",
                    },
                },
                {
                    "id": "mem_002",
                    "memory": "User likes minimal UI",
                    "score": 0.85,
                    "metadata": {
                        "memory_type": "user_preference",
                        "source": "chat",
                    },
                },
            ]

            await mem0_client.initialize()

            query = MemorySearchQuery(
                query="user preferences",
                user_id="user_123",
                limit=10,
            )
            results = await mem0_client.search_memory(query)

            assert len(results) == 2
            assert all(isinstance(r, MemorySearchResult) for r in results)
            assert results[0].score == 0.95
            assert results[1].score == 0.85

    @pytest.mark.asyncio
    async def test_search_memory_empty_results(self, mem0_client, mock_mem0_memory):
        """Test search with no results."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.return_value = mock_mem0_memory
            mock_mem0_memory.search.return_value = []

            await mem0_client.initialize()

            query = MemorySearchQuery(
                query="nonexistent query",
                user_id="user_123",
            )
            results = await mem0_client.search_memory(query)

            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_memory_not_initialized(self, mem0_client):
        """Test that search fails when not initialized."""
        query = MemorySearchQuery(query="test", user_id="user_123")
        with pytest.raises(RuntimeError):
            await mem0_client.search_memory(query)


# =============================================================================
# Get All Memories Tests
# =============================================================================


class TestMem0ClientGetAll:
    """Tests for get_all operation."""

    @pytest.mark.asyncio
    async def test_get_all_success(self, mem0_client, mock_mem0_memory):
        """Test getting all memories for a user."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.return_value = mock_mem0_memory
            mock_mem0_memory.get_all.return_value = [
                {
                    "id": "mem_001",
                    "memory": "Memory 1",
                    "metadata": {
                        "memory_type": "conversation",
                        "created_at": datetime.utcnow().isoformat(),
                    },
                },
                {
                    "id": "mem_002",
                    "memory": "Memory 2",
                    "metadata": {
                        "memory_type": "user_preference",
                        "created_at": datetime.utcnow().isoformat(),
                    },
                },
            ]

            await mem0_client.initialize()
            results = await mem0_client.get_all(user_id="user_123")

            assert len(results) == 2
            assert all(isinstance(r, MemoryRecord) for r in results)

    @pytest.mark.asyncio
    async def test_get_all_with_type_filter(self, mem0_client, mock_mem0_memory):
        """Test getting memories filtered by type."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.return_value = mock_mem0_memory
            mock_mem0_memory.get_all.return_value = [
                {
                    "id": "mem_001",
                    "memory": "Memory 1",
                    "metadata": {
                        "memory_type": "conversation",
                        "created_at": datetime.utcnow().isoformat(),
                    },
                },
                {
                    "id": "mem_002",
                    "memory": "Memory 2",
                    "metadata": {
                        "memory_type": "user_preference",
                        "created_at": datetime.utcnow().isoformat(),
                    },
                },
            ]

            await mem0_client.initialize()
            results = await mem0_client.get_all(
                user_id="user_123",
                memory_types=[MemoryType.USER_PREFERENCE],
            )

            assert len(results) == 1
            assert results[0].memory_type == MemoryType.USER_PREFERENCE

    @pytest.mark.asyncio
    async def test_get_all_empty(self, mem0_client, mock_mem0_memory):
        """Test getting memories when none exist."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.return_value = mock_mem0_memory
            mock_mem0_memory.get_all.return_value = []

            await mem0_client.initialize()
            results = await mem0_client.get_all(user_id="user_123")

            assert len(results) == 0


# =============================================================================
# Get Memory Tests
# =============================================================================


class TestMem0ClientGetMemory:
    """Tests for get_memory operation."""

    @pytest.mark.asyncio
    async def test_get_memory_success(self, mem0_client, mock_mem0_memory):
        """Test getting a specific memory by ID."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.return_value = mock_mem0_memory
            mock_mem0_memory.get.return_value = {
                "id": "mem_123",
                "user_id": "user_123",
                "memory": "Test memory content",
                "metadata": {
                    "memory_type": "conversation",
                    "source": "chat",
                },
            }

            await mem0_client.initialize()
            result = await mem0_client.get_memory("mem_123")

            assert result is not None
            assert isinstance(result, MemoryRecord)
            assert result.id == "mem_123"
            assert result.content == "Test memory content"

    @pytest.mark.asyncio
    async def test_get_memory_not_found(self, mem0_client, mock_mem0_memory):
        """Test getting a non-existent memory."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.return_value = mock_mem0_memory
            mock_mem0_memory.get.return_value = None

            await mem0_client.initialize()
            result = await mem0_client.get_memory("nonexistent_id")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_memory_error(self, mem0_client, mock_mem0_memory):
        """Test error handling in get_memory."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.return_value = mock_mem0_memory
            mock_mem0_memory.get.side_effect = Exception("Storage error")

            await mem0_client.initialize()
            result = await mem0_client.get_memory("mem_123")

            # Should return None on error
            assert result is None


# =============================================================================
# Update Memory Tests
# =============================================================================


class TestMem0ClientUpdateMemory:
    """Tests for update_memory operation."""

    @pytest.mark.asyncio
    async def test_update_memory_success(self, mem0_client, mock_mem0_memory):
        """Test successful memory update."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.return_value = mock_mem0_memory
            mock_mem0_memory.update.return_value = True
            mock_mem0_memory.get.return_value = {
                "id": "mem_123",
                "user_id": "user_123",
                "memory": "Updated content",
                "metadata": {"memory_type": "conversation"},
            }

            await mem0_client.initialize()
            result = await mem0_client.update_memory(
                memory_id="mem_123",
                content="Updated content",
            )

            assert result is not None
            assert result.content == "Updated content"
            mock_mem0_memory.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_memory_not_found(self, mem0_client, mock_mem0_memory):
        """Test updating a non-existent memory."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.return_value = mock_mem0_memory
            mock_mem0_memory.update.return_value = False

            await mem0_client.initialize()
            result = await mem0_client.update_memory(
                memory_id="nonexistent",
                content="New content",
            )

            assert result is None


# =============================================================================
# Delete Memory Tests
# =============================================================================


class TestMem0ClientDeleteMemory:
    """Tests for delete_memory operation."""

    @pytest.mark.asyncio
    async def test_delete_memory_success(self, mem0_client, mock_mem0_memory):
        """Test successful memory deletion."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.return_value = mock_mem0_memory

            await mem0_client.initialize()
            result = await mem0_client.delete_memory("mem_123")

            assert result is True
            mock_mem0_memory.delete.assert_called_once_with(memory_id="mem_123")

    @pytest.mark.asyncio
    async def test_delete_memory_error(self, mem0_client, mock_mem0_memory):
        """Test error handling in delete_memory."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.return_value = mock_mem0_memory
            mock_mem0_memory.delete.side_effect = Exception("Delete error")

            await mem0_client.initialize()
            result = await mem0_client.delete_memory("mem_123")

            assert result is False


# =============================================================================
# Delete All Tests
# =============================================================================


class TestMem0ClientDeleteAll:
    """Tests for delete_all operation."""

    @pytest.mark.asyncio
    async def test_delete_all_success(self, mem0_client, mock_mem0_memory):
        """Test successful deletion of all user memories."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.return_value = mock_mem0_memory

            await mem0_client.initialize()
            result = await mem0_client.delete_all("user_123")

            assert result is True
            mock_mem0_memory.delete_all.assert_called_once_with(user_id="user_123")

    @pytest.mark.asyncio
    async def test_delete_all_error(self, mem0_client, mock_mem0_memory):
        """Test error handling in delete_all."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.return_value = mock_mem0_memory
            mock_mem0_memory.delete_all.side_effect = Exception("Delete error")

            await mem0_client.initialize()
            result = await mem0_client.delete_all("user_123")

            assert result is False


# =============================================================================
# Get History Tests
# =============================================================================


class TestMem0ClientGetHistory:
    """Tests for get_history operation."""

    @pytest.mark.asyncio
    async def test_get_history_success(self, mem0_client, mock_mem0_memory):
        """Test getting memory history."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.return_value = mock_mem0_memory
            mock_mem0_memory.history.return_value = [
                {"version": 1, "content": "Original", "timestamp": "2024-01-01T00:00:00"},
                {"version": 2, "content": "Updated", "timestamp": "2024-01-02T00:00:00"},
            ]

            await mem0_client.initialize()
            result = await mem0_client.get_history("mem_123")

            assert len(result) == 2
            assert result[0]["version"] == 1
            assert result[1]["version"] == 2

    @pytest.mark.asyncio
    async def test_get_history_empty(self, mem0_client, mock_mem0_memory):
        """Test getting history for a memory without history."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.return_value = mock_mem0_memory
            mock_mem0_memory.history.return_value = []

            await mem0_client.initialize()
            result = await mem0_client.get_history("mem_123")

            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_history_error(self, mem0_client, mock_mem0_memory):
        """Test error handling in get_history."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.return_value = mock_mem0_memory
            mock_mem0_memory.history.side_effect = Exception("History error")

            await mem0_client.initialize()
            result = await mem0_client.get_history("mem_123")

            assert len(result) == 0


# =============================================================================
# Close Tests
# =============================================================================


class TestMem0ClientClose:
    """Tests for close operation."""

    @pytest.mark.asyncio
    async def test_close(self, mem0_client, mock_mem0_memory):
        """Test closing the client."""
        with patch("mem0.Memory") as MockMemory:
            MockMemory.from_config.return_value = mock_mem0_memory

            await mem0_client.initialize()
            assert mem0_client._initialized is True

            await mem0_client.close()

            assert mem0_client._initialized is False
            assert mem0_client._memory is None

    @pytest.mark.asyncio
    async def test_close_not_initialized(self, mem0_client):
        """Test closing when not initialized."""
        # Should not raise an error
        await mem0_client.close()
        assert mem0_client._initialized is False


# =============================================================================
# Configuration Tests
# =============================================================================


class TestMemoryConfig:
    """Tests for MemoryConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = MemoryConfig()
        assert config.qdrant_collection == "ipa_memories"
        assert config.embedding_model == "text-embedding-3-small"
        assert config.llm_provider == "anthropic"

    def test_config_from_env(self):
        """Test configuration from environment variables."""
        import os

        # Set environment variables
        os.environ["QDRANT_PATH"] = "/custom/path"
        os.environ["QDRANT_COLLECTION"] = "custom_collection"
        os.environ["MEM0_ENABLED"] = "false"

        try:
            config = MemoryConfig()
            assert config.qdrant_path == "/custom/path"
            assert config.qdrant_collection == "custom_collection"
            assert config.enabled is False
        finally:
            # Clean up environment variables
            del os.environ["QDRANT_PATH"]
            del os.environ["QDRANT_COLLECTION"]
            del os.environ["MEM0_ENABLED"]

    def test_config_to_dict(self):
        """Test configuration serialization."""
        config = MemoryConfig(
            qdrant_path="/test/path",
            qdrant_collection="test_collection",
        )
        result = config.to_dict()

        assert isinstance(result, dict)
        assert result["qdrant_path"] == "/test/path"
        assert result["qdrant_collection"] == "test_collection"
        assert "enabled" in result
