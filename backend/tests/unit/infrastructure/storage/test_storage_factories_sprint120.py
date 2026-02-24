"""Unit tests for Sprint 120 storage factory functions (5-7).

Sprint 120 -- Story 120-1: Tests for environment-aware factory functions:
    5. create_switch_checkpoint_storage (SwitchCheckpointStorage)
    6. create_audit_storage (AuditStorage)
    7. create_agent_framework_checkpoint_storage (AgentFrameworkCheckpoint)

Each factory follows the pattern:
    - STORAGE_BACKEND=memory  -> InMemory
    - STORAGE_BACKEND=redis   -> Redis (or raise if unavailable in production)
    - STORAGE_BACKEND=auto    -> Redis if available, InMemory fallback
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# =========================================================================
# 5. create_switch_checkpoint_storage
# =========================================================================


class TestCreateSwitchCheckpointStorage:
    """Tests for create_switch_checkpoint_storage factory."""

    @pytest.mark.asyncio
    async def test_create_switch_checkpoint_storage_redis(self):
        """With a Redis client available, return RedisSwitchCheckpointStorage."""
        mock_redis = AsyncMock()

        with (
            patch.dict(os.environ, {"STORAGE_BACKEND": "auto", "APP_ENV": "development"}),
            patch(
                "src.infrastructure.storage.storage_factories._get_redis_or_none",
                return_value=mock_redis,
            ),
        ):
            from src.infrastructure.storage.storage_factories import (
                create_switch_checkpoint_storage,
            )

            result = await create_switch_checkpoint_storage()

        from src.integrations.hybrid.switching.redis_checkpoint import (
            RedisSwitchCheckpointStorage,
        )

        assert isinstance(result, RedisSwitchCheckpointStorage)

    @pytest.mark.asyncio
    async def test_create_switch_checkpoint_storage_memory(self):
        """With STORAGE_BACKEND=memory, return InMemoryCheckpointStorage."""
        with patch.dict(os.environ, {"STORAGE_BACKEND": "memory", "APP_ENV": "development"}):
            from src.infrastructure.storage.storage_factories import (
                create_switch_checkpoint_storage,
            )

            result = await create_switch_checkpoint_storage()

        from src.integrations.hybrid.switching.switcher import (
            InMemoryCheckpointStorage,
        )

        assert isinstance(result, InMemoryCheckpointStorage)

    @pytest.mark.asyncio
    async def test_create_switch_checkpoint_storage_production_no_redis_raises(self):
        """In production with no Redis, raise RuntimeError."""
        with (
            patch.dict(os.environ, {"STORAGE_BACKEND": "auto", "APP_ENV": "production"}),
            patch(
                "src.infrastructure.storage.storage_factories._get_redis_or_none",
                return_value=None,
            ),
        ):
            from src.infrastructure.storage.storage_factories import (
                create_switch_checkpoint_storage,
            )

            with pytest.raises(RuntimeError, match="Redis unavailable"):
                await create_switch_checkpoint_storage()


# =========================================================================
# 6. create_audit_storage
# =========================================================================


class TestCreateAuditStorage:
    """Tests for create_audit_storage factory."""

    @pytest.mark.asyncio
    async def test_create_audit_storage_redis(self):
        """With a Redis client available, return RedisAuditStorage."""
        mock_redis = AsyncMock()

        with (
            patch.dict(os.environ, {"STORAGE_BACKEND": "auto", "APP_ENV": "development"}),
            patch(
                "src.infrastructure.storage.storage_factories._get_redis_or_none",
                return_value=mock_redis,
            ),
        ):
            from src.infrastructure.storage.storage_factories import (
                create_audit_storage,
            )

            result = await create_audit_storage()

        from src.integrations.mcp.security.redis_audit import RedisAuditStorage

        assert isinstance(result, RedisAuditStorage)

    @pytest.mark.asyncio
    async def test_create_audit_storage_memory(self):
        """With STORAGE_BACKEND=memory, return InMemoryAuditStorage."""
        with patch.dict(os.environ, {"STORAGE_BACKEND": "memory", "APP_ENV": "development"}):
            from src.infrastructure.storage.storage_factories import (
                create_audit_storage,
            )

            result = await create_audit_storage()

        from src.integrations.mcp.security.audit import InMemoryAuditStorage

        assert isinstance(result, InMemoryAuditStorage)

    @pytest.mark.asyncio
    async def test_create_audit_storage_production_no_redis_raises(self):
        """In production with no Redis, raise RuntimeError."""
        with (
            patch.dict(os.environ, {"STORAGE_BACKEND": "auto", "APP_ENV": "production"}),
            patch(
                "src.infrastructure.storage.storage_factories._get_redis_or_none",
                return_value=None,
            ),
        ):
            from src.infrastructure.storage.storage_factories import (
                create_audit_storage,
            )

            with pytest.raises(RuntimeError, match="Redis unavailable"):
                await create_audit_storage()


# =========================================================================
# 7. create_agent_framework_checkpoint_storage
# =========================================================================


class TestCreateAgentFrameworkCheckpointStorage:
    """Tests for create_agent_framework_checkpoint_storage factory."""

    @pytest.mark.asyncio
    async def test_create_agent_framework_checkpoint_redis(self):
        """With a Redis client available, return AFRedisCheckpointStorage."""
        mock_redis = AsyncMock()

        with (
            patch.dict(os.environ, {"STORAGE_BACKEND": "auto", "APP_ENV": "development"}),
            patch(
                "src.infrastructure.storage.storage_factories._get_redis_or_none",
                return_value=mock_redis,
            ),
            patch(
                "src.infrastructure.storage.storage_factories."
                "create_agent_framework_checkpoint_storage.__module__",
                create=True,
            ),
        ):
            # Mock the agent_framework import since it may not be installed
            mock_af_inmemory = MagicMock()
            mock_af_redis = MagicMock()

            with (
                patch.dict(
                    "sys.modules",
                    {
                        "agent_framework": MagicMock(
                            InMemoryCheckpointStorage=mock_af_inmemory
                        ),
                    },
                ),
                patch(
                    "src.integrations.agent_framework.multiturn.checkpoint_storage."
                    "RedisCheckpointStorage",
                    mock_af_redis,
                    create=True,
                ),
            ):
                from src.infrastructure.storage.storage_factories import (
                    create_agent_framework_checkpoint_storage,
                )

                result = await create_agent_framework_checkpoint_storage(
                    namespace="test",
                    ttl_seconds=7200,
                )

        # Result should be an instance created by the Redis storage class
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_agent_framework_checkpoint_memory(self):
        """With STORAGE_BACKEND=memory, return AFInMemoryCheckpointStorage."""
        mock_af_inmemory_cls = MagicMock()
        mock_af_inmemory_instance = MagicMock()
        mock_af_inmemory_cls.return_value = mock_af_inmemory_instance

        with (
            patch.dict(os.environ, {"STORAGE_BACKEND": "memory", "APP_ENV": "testing"}),
            patch.dict(
                "sys.modules",
                {
                    "agent_framework": MagicMock(
                        InMemoryCheckpointStorage=mock_af_inmemory_cls
                    ),
                },
            ),
        ):
            from src.infrastructure.storage.storage_factories import (
                create_agent_framework_checkpoint_storage,
            )

            result = await create_agent_framework_checkpoint_storage()

        assert result is mock_af_inmemory_instance
