# =============================================================================
# IPA Platform - Memory Storage Adapters
# =============================================================================
# Sprint 22: Memory System Migration (Phase 4)
#
# Implements official Agent Framework MemoryStorage interface with custom
# backend implementations (Redis, PostgreSQL).
#
# Usage:
#   from integrations.agent_framework.memory import (
#       RedisMemoryStorage,
#       PostgresMemoryStorage,
#       MemoryStorageProtocol,
#   )
#
#   # Create Redis storage
#   storage = RedisMemoryStorage(redis_client)
#   await storage.store("key", {"data": "value"})
#   result = await storage.retrieve("key")
#
#   # Create Postgres storage
#   storage = PostgresMemoryStorage(connection)
#   await storage.store("key", {"data": "value"})
#   result = await storage.retrieve("key")
#
# Reference:
#   - Official API: from agent_framework import Memory, MemoryStorage
#   - Phase 2: domain/orchestration/memory/redis_store.py
#   - Phase 2: domain/orchestration/memory/postgres_store.py
# =============================================================================

from .base import (
    MemoryStorageProtocol,
    MemoryRecord,
    MemorySearchResult,
    SearchOptions,
    MemoryError,
    MemoryNotFoundError,
    MemoryStorageError,
    MemoryValidationError,
)

from .redis_storage import (
    RedisMemoryStorage,
    create_redis_storage,
)

from .postgres_storage import (
    PostgresMemoryStorage,
    create_postgres_storage,
)

__all__ = [
    # Base types
    "MemoryStorageProtocol",
    "MemoryRecord",
    "MemorySearchResult",
    "SearchOptions",
    "MemoryError",
    "MemoryNotFoundError",
    "MemoryStorageError",
    "MemoryValidationError",
    # Redis storage
    "RedisMemoryStorage",
    "create_redis_storage",
    # Postgres storage
    "PostgresMemoryStorage",
    "create_postgres_storage",
]
