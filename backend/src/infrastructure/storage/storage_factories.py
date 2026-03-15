"""
Domain-Specific Storage Factories — Sprint 119 + Sprint 120

Environment-aware factory functions for each storage consumer:
1. ApprovalStorage (HITL)
2. DialogSessionStorage (Guided Dialog)
3. AG-UI ThreadRepository + CacheProtocol
4. ConversationMemoryStore (Orchestration Memory)
5. SwitchCheckpointStorage (Mode Switcher) — Sprint 120
6. AuditStorage (MCP Audit) — Sprint 120
7. AgentFrameworkCheckpointStorage (MultiTurn) — Sprint 120

Each factory follows the pattern:
  - production: Redis required
  - development: Redis preferred, InMemory fallback with WARNING
  - testing: InMemory directly

Environment Variables:
  - STORAGE_BACKEND: "redis" | "memory" | "auto" (default: "auto")
  - APP_ENV: "development" | "staging" | "production"
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


async def _get_redis_or_none():
    """Get centralized Redis client, or None if unavailable."""
    try:
        from src.infrastructure.redis_client import get_redis_client
        return await get_redis_client()
    except Exception as e:
        logger.debug(f"Redis unavailable: {e}")
        return None


def _get_env_config() -> tuple:
    """Get storage backend and app environment configuration."""
    backend = os.environ.get("STORAGE_BACKEND", "auto")
    app_env = os.environ.get("APP_ENV", "development")
    return backend, app_env


def _should_use_memory(backend: str, app_env: str) -> bool:
    """Check if InMemory should be used directly."""
    return backend == "memory" or (backend == "auto" and app_env == "testing")


def _handle_redis_unavailable(backend: str, app_env: str, name: str) -> None:
    """Handle Redis unavailability based on environment."""
    if backend == "redis" or app_env == "production":
        raise RuntimeError(
            f"Redis unavailable for {name} in {app_env}. "
            f"Set REDIS_HOST or use STORAGE_BACKEND=memory."
        )
    logger.warning(
        f"{name}: Redis unavailable in {app_env}, "
        f"falling back to InMemory. Data will be lost on restart."
    )


# =============================================================================
# 1. ApprovalStorage Factory
# =============================================================================


async def create_approval_storage():
    """
    Create ApprovalStorage instance.

    Returns:
        ApprovalStorage (Redis or InMemory).
    """
    from src.integrations.orchestration.hitl.controller import (
        ApprovalStorage,
        InMemoryApprovalStorage,
    )

    backend, app_env = _get_env_config()

    if _should_use_memory(backend, app_env):
        logger.info("ApprovalStorage: using InMemory")
        return InMemoryApprovalStorage()

    redis_client = await _get_redis_or_none()
    if redis_client is not None:
        from src.integrations.orchestration.hitl.approval_handler import RedisApprovalStorage
        logger.info("ApprovalStorage: using Redis")
        return RedisApprovalStorage(redis_client=redis_client)

    _handle_redis_unavailable(backend, app_env, "ApprovalStorage")
    return InMemoryApprovalStorage()


# =============================================================================
# 2. DialogSessionStorage Factory
# =============================================================================


async def create_dialog_session_storage(ttl_seconds: int = 1800):
    """
    Create DialogSessionStorage instance.

    Args:
        ttl_seconds: Session TTL in seconds (default: 30 minutes).

    Returns:
        DialogSessionStorage (Redis or InMemory).
    """
    from src.integrations.orchestration.guided_dialog.context_manager import (
        InMemoryDialogSessionStorage,
        RedisDialogSessionStorage,
    )

    backend, app_env = _get_env_config()

    if _should_use_memory(backend, app_env):
        logger.info("DialogSessionStorage: using InMemory")
        return InMemoryDialogSessionStorage(ttl_seconds=ttl_seconds)

    redis_client = await _get_redis_or_none()
    if redis_client is not None:
        logger.info("DialogSessionStorage: using Redis")
        return RedisDialogSessionStorage(
            redis_client=redis_client,
            ttl_seconds=ttl_seconds,
        )

    _handle_redis_unavailable(backend, app_env, "DialogSessionStorage")
    return InMemoryDialogSessionStorage(ttl_seconds=ttl_seconds)


# =============================================================================
# 3. AG-UI Thread Storage Factory
# =============================================================================


async def create_thread_repository():
    """
    Create AG-UI ThreadRepository instance.

    Returns:
        ThreadRepository (Redis or InMemory).
    """
    from src.integrations.ag_ui.thread.storage import InMemoryThreadRepository

    backend, app_env = _get_env_config()

    if _should_use_memory(backend, app_env):
        logger.info("ThreadRepository: using InMemory")
        return InMemoryThreadRepository()

    redis_client = await _get_redis_or_none()
    if redis_client is not None:
        from src.integrations.ag_ui.thread.redis_storage import RedisThreadRepository
        logger.info("ThreadRepository: using Redis")
        return RedisThreadRepository(redis_client=redis_client)

    _handle_redis_unavailable(backend, app_env, "ThreadRepository")
    return InMemoryThreadRepository()


async def create_ag_ui_cache():
    """
    Create AG-UI CacheProtocol instance.

    Returns:
        CacheProtocol (Redis or InMemory).
    """
    from src.integrations.ag_ui.thread.storage import InMemoryCache

    backend, app_env = _get_env_config()

    if _should_use_memory(backend, app_env):
        logger.info("AG-UI Cache: using InMemory")
        return InMemoryCache()

    redis_client = await _get_redis_or_none()
    if redis_client is not None:
        from src.integrations.ag_ui.thread.redis_storage import RedisCacheBackend
        logger.info("AG-UI Cache: using Redis")
        return RedisCacheBackend(redis_client=redis_client)

    _handle_redis_unavailable(backend, app_env, "AG-UI Cache")
    return InMemoryCache()


# =============================================================================
# 4. ConversationMemoryStore Factory
# =============================================================================


async def create_conversation_memory_store():
    """
    Create ConversationMemoryStore instance.

    Returns:
        ConversationMemoryStore (Redis or InMemory).
    """
    from src.domain.orchestration.memory.in_memory import InMemoryConversationMemoryStore

    backend, app_env = _get_env_config()

    if _should_use_memory(backend, app_env):
        logger.info("ConversationMemoryStore: using InMemory")
        return InMemoryConversationMemoryStore()

    redis_client = await _get_redis_or_none()
    if redis_client is not None:
        from src.domain.orchestration.memory.redis_store import RedisConversationMemoryStore
        logger.info("ConversationMemoryStore: using Redis")
        return RedisConversationMemoryStore(redis_client=redis_client)

    _handle_redis_unavailable(backend, app_env, "ConversationMemoryStore")
    return InMemoryConversationMemoryStore()


# =============================================================================
# 5. SwitchCheckpointStorage Factory — Sprint 120
# =============================================================================


async def create_switch_checkpoint_storage():
    """
    Create CheckpointStorageProtocol instance for ModeSwitcher.

    Returns:
        CheckpointStorageProtocol (Redis or InMemory).
    """
    from src.integrations.hybrid.switching.switcher import InMemoryCheckpointStorage

    backend, app_env = _get_env_config()

    if _should_use_memory(backend, app_env):
        logger.info("SwitchCheckpointStorage: using InMemory")
        return InMemoryCheckpointStorage()

    redis_client = await _get_redis_or_none()
    if redis_client is not None:
        from src.integrations.hybrid.switching.redis_checkpoint import (
            RedisSwitchCheckpointStorage,
        )
        logger.info("SwitchCheckpointStorage: using Redis")
        return RedisSwitchCheckpointStorage(redis_client=redis_client)

    _handle_redis_unavailable(backend, app_env, "SwitchCheckpointStorage")
    return InMemoryCheckpointStorage()


# =============================================================================
# 6. AuditStorage Factory — Sprint 120
# =============================================================================


async def create_audit_storage(max_size: int = 10000):
    """
    Create AuditStorage instance for MCP audit logging.

    Args:
        max_size: Maximum number of events to retain (default: 10000).

    Returns:
        AuditStorage (Redis or InMemory).
    """
    from src.integrations.mcp.security.audit import InMemoryAuditStorage

    backend, app_env = _get_env_config()

    if _should_use_memory(backend, app_env):
        logger.info("AuditStorage: using InMemory")
        return InMemoryAuditStorage(max_size=max_size)

    redis_client = await _get_redis_or_none()
    if redis_client is not None:
        from src.integrations.mcp.security.redis_audit import RedisAuditStorage
        logger.info("AuditStorage: using Redis")
        return RedisAuditStorage(redis_client=redis_client, max_size=max_size)

    _handle_redis_unavailable(backend, app_env, "AuditStorage")
    return InMemoryAuditStorage(max_size=max_size)


# =============================================================================
# 7. AgentFrameworkCheckpointStorage Factory — Sprint 120
# =============================================================================


async def create_agent_framework_checkpoint_storage(
    namespace: str = "multiturn",
    ttl_seconds: int = 86400,
):
    """
    Create BaseCheckpointStorage instance for Agent Framework multi-turn.

    This wraps the existing RedisCheckpointStorage / InMemoryCheckpointStorage
    from agent_framework.multiturn with environment-aware selection.

    Args:
        namespace: Storage namespace for key isolation.
        ttl_seconds: TTL for checkpoint data in seconds.

    Returns:
        BaseCheckpointStorage (Redis or InMemory).
    """
    from agent_framework.workflows import InMemoryCheckpointStorage as AFInMemoryCheckpointStorage  # TODO: verify submodule path

    backend, app_env = _get_env_config()

    if _should_use_memory(backend, app_env):
        logger.info("AgentFrameworkCheckpointStorage: using InMemory")
        return AFInMemoryCheckpointStorage()

    redis_client = await _get_redis_or_none()
    if redis_client is not None:
        from src.integrations.agent_framework.multiturn.checkpoint_storage import (
            RedisCheckpointStorage as AFRedisCheckpointStorage,
        )
        logger.info("AgentFrameworkCheckpointStorage: using Redis")
        return AFRedisCheckpointStorage(
            redis_client=redis_client,
            namespace=namespace,
            ttl_seconds=ttl_seconds,
        )

    _handle_redis_unavailable(
        backend, app_env, "AgentFrameworkCheckpointStorage"
    )
    return AFInMemoryCheckpointStorage()
