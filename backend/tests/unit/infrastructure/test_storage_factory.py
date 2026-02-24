# =============================================================================
# IPA Platform - Storage Factory Tests
# =============================================================================
# Sprint 119: InMemory Storage Migration
#
# Tests for:
# - create_storage_backend() factory
# - Environment-aware backend selection
# =============================================================================

from unittest.mock import AsyncMock, patch

import pytest

from src.infrastructure.storage.factory import create_storage_backend
from src.infrastructure.storage.memory_backend import InMemoryStorageBackend
from src.infrastructure.storage.redis_backend import RedisStorageBackend


class TestCreateStorageBackendExplicitMemory:
    """Test explicit memory backend selection."""

    @pytest.mark.asyncio
    async def test_explicit_memory_returns_inmemory(self):
        result = await create_storage_backend(prefix="test", backend="memory")
        assert isinstance(result, InMemoryStorageBackend)
        assert result.prefix == "test"

    @pytest.mark.asyncio
    async def test_explicit_memory_with_default_ttl(self):
        result = await create_storage_backend(
            prefix="test", backend="memory", default_ttl=300
        )
        assert isinstance(result, InMemoryStorageBackend)


class TestCreateStorageBackendAutoMode:
    """Test auto mode backend selection."""

    @pytest.mark.asyncio
    async def test_auto_with_redis_available(self):
        mock_client = AsyncMock()
        with patch(
            "src.infrastructure.storage.factory._try_create_redis_backend",
            new_callable=AsyncMock,
        ) as mock_try:
            mock_backend = RedisStorageBackend(redis_client=mock_client, prefix="test")
            mock_try.return_value = mock_backend
            result = await create_storage_backend(prefix="test")
            assert isinstance(result, RedisStorageBackend)

    @pytest.mark.asyncio
    async def test_auto_with_redis_unavailable_in_dev(self):
        with (
            patch(
                "src.infrastructure.storage.factory._try_create_redis_backend",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.dict("os.environ", {"STORAGE_BACKEND": "auto", "APP_ENV": "development"}),
        ):
            result = await create_storage_backend(prefix="test")
            assert isinstance(result, InMemoryStorageBackend)

    @pytest.mark.asyncio
    async def test_auto_with_redis_unavailable_in_testing(self):
        with (
            patch(
                "src.infrastructure.storage.factory._try_create_redis_backend",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.dict("os.environ", {"STORAGE_BACKEND": "auto", "APP_ENV": "testing"}),
        ):
            result = await create_storage_backend(prefix="test")
            assert isinstance(result, InMemoryStorageBackend)

    @pytest.mark.asyncio
    async def test_auto_with_redis_unavailable_in_production_raises(self):
        with (
            patch(
                "src.infrastructure.storage.factory._try_create_redis_backend",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.dict("os.environ", {"STORAGE_BACKEND": "auto", "APP_ENV": "production"}),
        ):
            with pytest.raises(RuntimeError, match="Redis unavailable"):
                await create_storage_backend(prefix="test")


class TestCreateStorageBackendExplicitRedis:
    """Test explicit redis backend selection."""

    @pytest.mark.asyncio
    async def test_explicit_redis_raises_when_unavailable(self):
        with (
            patch(
                "src.infrastructure.storage.factory._try_create_redis_backend",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.dict("os.environ", {"APP_ENV": "development"}),
        ):
            with pytest.raises(RuntimeError, match="Redis unavailable"):
                await create_storage_backend(prefix="test", backend="redis")

    @pytest.mark.asyncio
    async def test_explicit_redis_success(self):
        mock_client = AsyncMock()
        mock_backend = RedisStorageBackend(redis_client=mock_client, prefix="test")
        with patch(
            "src.infrastructure.storage.factory._try_create_redis_backend",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            result = await create_storage_backend(prefix="test", backend="redis")
            assert isinstance(result, RedisStorageBackend)


class TestCreateStorageBackendInvalidInput:
    """Test invalid backend type."""

    @pytest.mark.asyncio
    async def test_invalid_backend_raises(self):
        with patch.dict("os.environ", {"STORAGE_BACKEND": "postgres"}):
            with pytest.raises(ValueError, match="Unknown storage backend"):
                await create_storage_backend(prefix="test", backend="postgres")


class TestCreateStorageBackendEnvVar:
    """Test STORAGE_BACKEND environment variable."""

    @pytest.mark.asyncio
    async def test_env_var_memory(self):
        with patch.dict("os.environ", {"STORAGE_BACKEND": "memory"}):
            result = await create_storage_backend(prefix="test")
            assert isinstance(result, InMemoryStorageBackend)
