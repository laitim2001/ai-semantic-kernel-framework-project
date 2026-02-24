"""
Storage Infrastructure — Sprint 119

Unified storage backend abstraction with Redis and InMemory implementations.
Provides environment-aware factory for automatic backend selection.

Usage:
    from src.infrastructure.storage import create_storage_backend, StorageBackend

    # Auto-select based on environment
    storage = await create_storage_backend(prefix="approval")

    # Explicit Redis
    storage = await create_storage_backend(prefix="session", backend="redis")
"""

from src.infrastructure.storage.factory import create_storage_backend
from src.infrastructure.storage.memory_backend import InMemoryStorageBackend
from src.infrastructure.storage.protocol import StorageBackend
from src.infrastructure.storage.redis_backend import RedisStorageBackend

__all__ = [
    "StorageBackend",
    "RedisStorageBackend",
    "InMemoryStorageBackend",
    "create_storage_backend",
]
