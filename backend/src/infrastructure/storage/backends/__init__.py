"""
Storage Backends — Sprint 110

Unified storage backend abstraction for key-value + TTL storage.
Replaces scattered InMemory dicts across the codebase with pluggable backends.

Supports: InMemory (dev), Redis (session/cache), PostgreSQL (persistent).

Usage:
    from src.infrastructure.storage.backends import (
        StorageBackendABC,
        InMemoryBackend,
        RedisBackend,
        PostgresBackend,
        StorageFactory,
    )

    # Auto-detect from environment
    backend = await StorageFactory.create("dialog_sessions", backend_type="redis")

    # With explicit config
    backend = await StorageFactory.create("approvals", backend_type="postgres", namespace="approvals")
"""

from src.infrastructure.storage.backends.base import StorageBackendABC
from src.infrastructure.storage.backends.factory import StorageFactory
from src.infrastructure.storage.backends.memory import InMemoryBackend
from src.infrastructure.storage.backends.postgres_backend import PostgresBackend
from src.infrastructure.storage.backends.redis_backend import RedisBackend

__all__ = [
    "StorageBackendABC",
    "InMemoryBackend",
    "RedisBackend",
    "PostgresBackend",
    "StorageFactory",
]
