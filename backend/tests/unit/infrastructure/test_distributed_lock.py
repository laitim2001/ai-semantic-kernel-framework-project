# =============================================================================
# IPA Platform - Distributed Lock Tests
# =============================================================================
# Sprint 119: ContextSynchronizer Upgrade
#
# Tests for:
# - InMemoryLock
# - RedisDistributedLock (mocked Redis)
# - create_distributed_lock factory
# - DistributedLock Protocol compliance
# =============================================================================

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.distributed_lock.redis_lock import (
    DistributedLock,
    InMemoryLock,
    RedisDistributedLock,
    create_distributed_lock,
)


# =============================================================================
# Protocol Compliance Tests
# =============================================================================


class TestDistributedLockProtocol:
    """Test that implementations conform to DistributedLock Protocol."""

    def test_inmemory_lock_is_distributed_lock(self):
        lock = InMemoryLock(lock_name="test")
        assert isinstance(lock, DistributedLock)

    def test_redis_lock_is_distributed_lock(self):
        mock = AsyncMock()
        lock = RedisDistributedLock(redis_client=mock, lock_name="test")
        assert isinstance(lock, DistributedLock)


# =============================================================================
# InMemoryLock Tests
# =============================================================================


class TestInMemoryLock:
    """Tests for InMemoryLock."""

    def test_lock_name_property(self):
        lock = InMemoryLock(lock_name="my_lock")
        assert lock.lock_name == "my_lock"

    @pytest.mark.asyncio
    async def test_acquire_and_release(self):
        lock = InMemoryLock(lock_name="test")
        async with lock.acquire():
            # Lock should be held
            assert await lock.is_locked() is True
        # Lock should be released
        assert await lock.is_locked() is False

    @pytest.mark.asyncio
    async def test_mutual_exclusion(self):
        """Test that two concurrent acquires are serialized."""
        lock = InMemoryLock(lock_name="test")
        order = []

        async def task(name: str, delay: float):
            async with lock.acquire():
                order.append(f"{name}_start")
                await asyncio.sleep(delay)
                order.append(f"{name}_end")

        await asyncio.gather(task("A", 0.1), task("B", 0.1))

        # A and B should not interleave
        assert order[0].endswith("_start")
        assert order[1].endswith("_end")

    @pytest.mark.asyncio
    async def test_timeout_raises(self):
        """Test that timeout raises TimeoutError."""
        lock = InMemoryLock(lock_name="test", timeout=1)

        async with lock.acquire():
            # Try to acquire from another coroutine
            with pytest.raises(TimeoutError, match="Failed to acquire"):
                async with lock.acquire():
                    pass  # Should not reach here

    @pytest.mark.asyncio
    async def test_is_locked_false_initially(self):
        lock = InMemoryLock(lock_name="test")
        assert await lock.is_locked() is False


# =============================================================================
# RedisDistributedLock Tests (Mocked)
# =============================================================================


class TestRedisDistributedLock:
    """Tests for RedisDistributedLock with mocked Redis."""

    def test_lock_name_property(self):
        mock = AsyncMock()
        lock = RedisDistributedLock(redis_client=mock, lock_name="test")
        assert lock.lock_name == "test"

    @pytest.mark.asyncio
    async def test_acquire_success(self):
        mock_redis = AsyncMock()
        mock_lock = AsyncMock()
        mock_lock.acquire = AsyncMock(return_value=True)
        mock_lock.release = AsyncMock()
        mock_redis.lock = MagicMock(return_value=mock_lock)

        lock = RedisDistributedLock(redis_client=mock_redis, lock_name="test")
        async with lock.acquire():
            pass

        mock_lock.acquire.assert_called_once_with(blocking=True)
        mock_lock.release.assert_called_once()

    @pytest.mark.asyncio
    async def test_acquire_failure_raises_timeout(self):
        mock_redis = AsyncMock()
        mock_lock = AsyncMock()
        mock_lock.acquire = AsyncMock(return_value=False)
        mock_redis.lock = MagicMock(return_value=mock_lock)

        lock = RedisDistributedLock(
            redis_client=mock_redis, lock_name="test", blocking_timeout=1
        )

        with pytest.raises(TimeoutError, match="Failed to acquire"):
            async with lock.acquire():
                pass

    @pytest.mark.asyncio
    async def test_release_handles_lock_not_owned(self):
        from redis.exceptions import LockNotOwnedError

        mock_redis = AsyncMock()
        mock_lock = AsyncMock()
        mock_lock.acquire = AsyncMock(return_value=True)
        mock_lock.release = AsyncMock(side_effect=LockNotOwnedError("expired"))
        mock_redis.lock = MagicMock(return_value=mock_lock)

        lock = RedisDistributedLock(redis_client=mock_redis, lock_name="test")
        # Should not raise — just warns
        async with lock.acquire():
            pass

    @pytest.mark.asyncio
    async def test_is_locked_true(self):
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 1
        lock = RedisDistributedLock(redis_client=mock_redis, lock_name="test")
        assert await lock.is_locked() is True

    @pytest.mark.asyncio
    async def test_is_locked_false(self):
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 0
        lock = RedisDistributedLock(redis_client=mock_redis, lock_name="test")
        assert await lock.is_locked() is False


# =============================================================================
# Factory Tests
# =============================================================================


class TestCreateDistributedLock:
    """Tests for create_distributed_lock factory."""

    @pytest.mark.asyncio
    async def test_creates_inmemory_when_redis_unavailable(self):
        with patch(
            "src.infrastructure.redis_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=None,
        ):
            lock = await create_distributed_lock("test")
            assert isinstance(lock, InMemoryLock)
            assert lock.lock_name == "test"

    @pytest.mark.asyncio
    async def test_creates_redis_when_available(self):
        mock_client = AsyncMock()
        with patch(
            "src.infrastructure.redis_client.get_redis_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            lock = await create_distributed_lock("test")
            assert isinstance(lock, RedisDistributedLock)

    @pytest.mark.asyncio
    async def test_raises_in_production_when_redis_unavailable(self):
        with (
            patch(
                "src.infrastructure.redis_client.get_redis_client",
                new_callable=AsyncMock,
                side_effect=Exception("Connection refused"),
            ),
            patch.dict("os.environ", {"APP_ENV": "production"}),
        ):
            with pytest.raises(RuntimeError, match="Redis required"):
                await create_distributed_lock("test")

    @pytest.mark.asyncio
    async def test_fallback_in_development(self):
        with (
            patch(
                "src.infrastructure.redis_client.get_redis_client",
                new_callable=AsyncMock,
                side_effect=Exception("Connection refused"),
            ),
            patch.dict("os.environ", {"APP_ENV": "development"}),
        ):
            lock = await create_distributed_lock("test")
            assert isinstance(lock, InMemoryLock)
