# =============================================================================
# IPA Platform - Storage Backend Tests
# =============================================================================
# Sprint 119: InMemory Storage Migration
#
# Tests for:
# - InMemoryStorageBackend (full coverage)
# - RedisStorageBackend (mocked Redis)
# - StorageBackend Protocol compliance
# =============================================================================

import asyncio
import time
from datetime import datetime
from enum import Enum
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.infrastructure.storage.memory_backend import InMemoryStorageBackend
from src.infrastructure.storage.protocol import StorageBackend
from src.infrastructure.storage.redis_backend import (
    RedisStorageBackend,
    StorageEncoder,
    _decode_hook,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def memory_backend():
    """Create a fresh InMemoryStorageBackend."""
    return InMemoryStorageBackend(prefix="test")


@pytest.fixture
def memory_backend_with_ttl():
    """Create InMemoryStorageBackend with default TTL."""
    return InMemoryStorageBackend(prefix="ttl_test", default_ttl=5)


@pytest.fixture
def mock_redis():
    """Create a mock async Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.setex = AsyncMock()
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=0)
    redis.sadd = AsyncMock(return_value=1)
    redis.srem = AsyncMock(return_value=1)
    redis.smembers = AsyncMock(return_value=set())
    redis.ttl = AsyncMock(return_value=-1)
    redis.expire = AsyncMock(return_value=True)
    redis.scan_iter = MagicMock(return_value=AsyncIterator([]))
    return redis


@pytest.fixture
def redis_backend(mock_redis):
    """Create RedisStorageBackend with mocked Redis."""
    return RedisStorageBackend(redis_client=mock_redis, prefix="test")


class AsyncIterator:
    """Helper to create async iterators from lists."""

    def __init__(self, items):
        self.items = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.items)
        except StopIteration:
            raise StopAsyncIteration


# =============================================================================
# Protocol Compliance Tests
# =============================================================================


class TestStorageBackendProtocol:
    """Test that implementations conform to StorageBackend Protocol."""

    def test_inmemory_is_storage_backend(self):
        """InMemoryStorageBackend implements StorageBackend protocol."""
        backend = InMemoryStorageBackend(prefix="p")
        assert isinstance(backend, StorageBackend)

    def test_redis_is_storage_backend(self):
        """RedisStorageBackend implements StorageBackend protocol."""
        mock = AsyncMock()
        backend = RedisStorageBackend(redis_client=mock, prefix="p")
        assert isinstance(backend, StorageBackend)


# =============================================================================
# InMemoryStorageBackend Tests
# =============================================================================


class TestInMemoryStorageBackendBasic:
    """Basic CRUD operations for InMemoryStorageBackend."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_key_returns_none(self, memory_backend):
        result = await memory_backend.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get(self, memory_backend):
        await memory_backend.set("key1", {"name": "test", "value": 42})
        result = await memory_backend.get("key1")
        assert result == {"name": "test", "value": 42}

    @pytest.mark.asyncio
    async def test_set_overwrites_existing(self, memory_backend):
        await memory_backend.set("key1", "value1")
        await memory_backend.set("key1", "value2")
        result = await memory_backend.get("key1")
        assert result == "value2"

    @pytest.mark.asyncio
    async def test_delete_existing_key(self, memory_backend):
        await memory_backend.set("key1", "value1")
        result = await memory_backend.delete("key1")
        assert result is True
        assert await memory_backend.get("key1") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self, memory_backend):
        result = await memory_backend.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_true(self, memory_backend):
        await memory_backend.set("key1", "value1")
        assert await memory_backend.exists("key1") is True

    @pytest.mark.asyncio
    async def test_exists_false(self, memory_backend):
        assert await memory_backend.exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_prefix_property(self, memory_backend):
        assert memory_backend.prefix == "test"


class TestInMemoryStorageBackendTTL:
    """TTL-related tests for InMemoryStorageBackend."""

    @pytest.mark.asyncio
    async def test_set_with_ttl_expires(self):
        backend = InMemoryStorageBackend(prefix="ttl")
        await backend.set("key1", "value1", ttl=1)

        # Should exist immediately
        assert await backend.get("key1") == "value1"

        # Wait for expiry
        await asyncio.sleep(1.1)
        assert await backend.get("key1") is None

    @pytest.mark.asyncio
    async def test_default_ttl(self, memory_backend_with_ttl):
        await memory_backend_with_ttl.set("key1", "value1")
        # Key should exist immediately
        assert await memory_backend_with_ttl.exists("key1") is True

    @pytest.mark.asyncio
    async def test_explicit_ttl_overrides_default(self, memory_backend_with_ttl):
        await memory_backend_with_ttl.set("key1", "value1", ttl=1)
        assert await memory_backend_with_ttl.get("key1") == "value1"
        await asyncio.sleep(1.1)
        assert await memory_backend_with_ttl.get("key1") is None

    @pytest.mark.asyncio
    async def test_exists_returns_false_for_expired(self):
        backend = InMemoryStorageBackend(prefix="ttl")
        await backend.set("key1", "value1", ttl=1)
        await asyncio.sleep(1.1)
        assert await backend.exists("key1") is False


class TestInMemoryStorageBackendListKeys:
    """list_keys tests for InMemoryStorageBackend."""

    @pytest.mark.asyncio
    async def test_list_keys_all(self, memory_backend):
        await memory_backend.set("a", 1)
        await memory_backend.set("b", 2)
        await memory_backend.set("c", 3)
        keys = await memory_backend.list_keys()
        assert sorted(keys) == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_list_keys_pattern(self, memory_backend):
        await memory_backend.set("user:1", "alice")
        await memory_backend.set("user:2", "bob")
        await memory_backend.set("session:1", "s1")
        keys = await memory_backend.list_keys("user:*")
        assert sorted(keys) == ["user:1", "user:2"]

    @pytest.mark.asyncio
    async def test_list_keys_excludes_expired(self):
        backend = InMemoryStorageBackend(prefix="ttl")
        await backend.set("live", "value1")
        await backend.set("expired", "value2", ttl=1)
        await asyncio.sleep(1.1)
        keys = await backend.list_keys()
        assert keys == ["live"]


class TestInMemoryStorageBackendSets:
    """Set operation tests for InMemoryStorageBackend."""

    @pytest.mark.asyncio
    async def test_set_add(self, memory_backend):
        count = await memory_backend.set_add("myset", "a", "b", "c")
        assert count == 3

    @pytest.mark.asyncio
    async def test_set_add_deduplicates(self, memory_backend):
        await memory_backend.set_add("myset", "a", "b")
        count = await memory_backend.set_add("myset", "b", "c")
        assert count == 1  # Only "c" is new

    @pytest.mark.asyncio
    async def test_set_remove(self, memory_backend):
        await memory_backend.set_add("myset", "a", "b", "c")
        count = await memory_backend.set_remove("myset", "a")
        assert count == 1

    @pytest.mark.asyncio
    async def test_set_remove_nonexistent(self, memory_backend):
        count = await memory_backend.set_remove("myset", "a")
        assert count == 0

    @pytest.mark.asyncio
    async def test_set_members(self, memory_backend):
        await memory_backend.set_add("myset", "a", "b", "c")
        members = await memory_backend.set_members("myset")
        assert members == {"a", "b", "c"}

    @pytest.mark.asyncio
    async def test_set_members_empty(self, memory_backend):
        members = await memory_backend.set_members("myset")
        assert members == set()


class TestInMemoryStorageBackendClearAll:
    """clear_all tests for InMemoryStorageBackend."""

    @pytest.mark.asyncio
    async def test_clear_all_with_prefix(self, memory_backend):
        await memory_backend.set("a", 1)
        await memory_backend.set("b", 2)
        await memory_backend.set_add("myset", "x")
        count = await memory_backend.clear_all()
        assert count >= 2

    @pytest.mark.asyncio
    async def test_clear_all_no_prefix(self):
        backend = InMemoryStorageBackend(prefix="")
        await backend.set("a", 1)
        await backend.set("b", 2)
        count = await backend.clear_all()
        assert count >= 2


# =============================================================================
# RedisStorageBackend Tests (Mocked)
# =============================================================================


class TestRedisStorageBackendBasic:
    """Basic CRUD operations for RedisStorageBackend (mocked Redis)."""

    @pytest.mark.asyncio
    async def test_get_returns_deserialized_value(self, redis_backend, mock_redis):
        mock_redis.get.return_value = '{"name": "test"}'
        result = await redis_backend.get("key1")
        assert result == {"name": "test"}
        mock_redis.get.assert_called_once_with("test:key1")

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing_key(self, redis_backend, mock_redis):
        mock_redis.get.return_value = None
        result = await redis_backend.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_without_ttl(self, redis_backend, mock_redis):
        await redis_backend.set("key1", {"name": "test"})
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "test:key1"

    @pytest.mark.asyncio
    async def test_set_with_explicit_ttl(self, redis_backend, mock_redis):
        await redis_backend.set("key1", "value", ttl=60)
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "test:key1"
        assert call_args[0][1] == 60

    @pytest.mark.asyncio
    async def test_set_with_default_ttl(self, mock_redis):
        backend = RedisStorageBackend(redis_client=mock_redis, prefix="t", default_ttl=300)
        await backend.set("key1", "value")
        mock_redis.setex.assert_called_once()
        assert mock_redis.setex.call_args[0][1] == 300

    @pytest.mark.asyncio
    async def test_delete_existing_key(self, redis_backend, mock_redis):
        mock_redis.delete.return_value = 1
        result = await redis_backend.delete("key1")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self, redis_backend, mock_redis):
        mock_redis.delete.return_value = 0
        result = await redis_backend.delete("key1")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_true(self, redis_backend, mock_redis):
        mock_redis.exists.return_value = 1
        assert await redis_backend.exists("key1") is True

    @pytest.mark.asyncio
    async def test_exists_false(self, redis_backend, mock_redis):
        mock_redis.exists.return_value = 0
        assert await redis_backend.exists("key1") is False

    @pytest.mark.asyncio
    async def test_prefix_property(self, redis_backend):
        assert redis_backend.prefix == "test"


class TestRedisStorageBackendErrorHandling:
    """Error handling tests for RedisStorageBackend."""

    @pytest.mark.asyncio
    async def test_get_handles_redis_error(self, redis_backend, mock_redis):
        import redis.asyncio as aioredis

        mock_redis.get.side_effect = aioredis.RedisError("Connection lost")
        result = await redis_backend.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_propagates_redis_error(self, redis_backend, mock_redis):
        import redis.asyncio as aioredis

        mock_redis.set.side_effect = aioredis.RedisError("Connection lost")
        with pytest.raises(aioredis.RedisError):
            await redis_backend.set("key1", "value")

    @pytest.mark.asyncio
    async def test_delete_handles_redis_error(self, redis_backend, mock_redis):
        import redis.asyncio as aioredis

        mock_redis.delete.side_effect = aioredis.RedisError("Connection lost")
        result = await redis_backend.delete("key1")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_handles_redis_error(self, redis_backend, mock_redis):
        import redis.asyncio as aioredis

        mock_redis.exists.side_effect = aioredis.RedisError("Connection lost")
        result = await redis_backend.exists("key1")
        assert result is False


class TestRedisStorageBackendSets:
    """Set operation tests for RedisStorageBackend."""

    @pytest.mark.asyncio
    async def test_set_add(self, redis_backend, mock_redis):
        mock_redis.sadd.return_value = 2
        count = await redis_backend.set_add("myset", "a", "b")
        assert count == 2
        mock_redis.sadd.assert_called_once_with("test:myset", "a", "b")

    @pytest.mark.asyncio
    async def test_set_remove(self, redis_backend, mock_redis):
        mock_redis.srem.return_value = 1
        count = await redis_backend.set_remove("myset", "a")
        assert count == 1

    @pytest.mark.asyncio
    async def test_set_members(self, redis_backend, mock_redis):
        mock_redis.smembers.return_value = {"a", "b", "c"}
        members = await redis_backend.set_members("myset")
        assert members == {"a", "b", "c"}


# =============================================================================
# JSON Serialization Tests
# =============================================================================


class TestStorageEncoder:
    """Test custom JSON encoder/decoder for storage."""

    def test_encode_datetime(self):
        import json

        dt = datetime(2026, 2, 24, 12, 0, 0)
        encoded = json.dumps({"ts": dt}, cls=StorageEncoder)
        decoded = json.loads(encoded, object_hook=_decode_hook)
        assert decoded["ts"] == dt

    def test_encode_uuid(self):
        import json

        uid = uuid4()
        encoded = json.dumps({"id": uid}, cls=StorageEncoder)
        decoded = json.loads(encoded, object_hook=_decode_hook)
        assert decoded["id"] == uid

    def test_encode_enum(self):
        import json

        class Color(Enum):
            RED = "red"
            BLUE = "blue"

        encoded = json.dumps({"color": Color.RED}, cls=StorageEncoder)
        decoded = json.loads(encoded, object_hook=_decode_hook)
        # Enum deserializes to raw value
        assert decoded["color"] == "red"

    def test_encode_set(self):
        import json

        encoded = json.dumps({"items": {1, 2, 3}}, cls=StorageEncoder)
        decoded = json.loads(encoded, object_hook=_decode_hook)
        assert decoded["items"] == {1, 2, 3}

    def test_decode_hook_passthrough(self):
        """Non-typed dicts pass through unchanged."""
        result = _decode_hook({"key": "value"})
        assert result == {"key": "value"}
