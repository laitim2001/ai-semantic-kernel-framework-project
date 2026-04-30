"""
Storage Backend ABC — Sprint 110

Abstract base class for all storage backends.
Extends the existing StorageBackend Protocol (protocol.py) with a concrete ABC
that provides type-safe abstract methods and a consistent interface.

This ABC is used by the new backends (InMemoryBackend, RedisBackend, PostgresBackend).
The existing protocol.py and its implementations remain unchanged.
"""

from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any, Dict, List, Optional


class StorageBackendABC(ABC):
    """
    Abstract storage backend for key-value operations with optional TTL.

    All new storage backends (Sprint 110+) should inherit from this ABC.
    Existing backends (Sprint 119) implement the Protocol in protocol.py.

    Key differences from the Sprint 119 Protocol:
    - TTL accepts timedelta (more Pythonic) in addition to int seconds
    - keys() method (renamed from list_keys for clarity)
    - clear() method (renamed from clear_all for clarity)
    - No set operations (set_add/set_remove/set_members) — those remain
      in the Sprint 119 Protocol for Redis-specific use cases
    """

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value by key.

        Args:
            key: Storage key.

        Returns:
            Deserialized value, or None if key does not exist or is expired.
        """
        ...

    @abstractmethod
    async def set(
        self, key: str, value: Any, ttl: Optional[timedelta] = None
    ) -> None:
        """
        Set a value with optional TTL.

        Args:
            key: Storage key.
            value: Value to store (must be JSON-serializable).
            ttl: Time-to-live. None means no expiration.
        """
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete a key.

        Args:
            key: Storage key.

        Returns:
            True if the key existed and was deleted, False otherwise.
        """
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists (and is not expired).

        Args:
            key: Storage key.

        Returns:
            True if key exists and is not expired.
        """
        ...

    @abstractmethod
    async def keys(self, pattern: str = "*") -> List[str]:
        """
        List keys matching a glob-style pattern.

        Args:
            pattern: Glob pattern (e.g., "session:*").

        Returns:
            List of matching keys.
        """
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Delete all keys managed by this backend instance."""
        ...

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple values by keys.

        Default implementation calls get() for each key.
        Subclasses may override for batch optimization.

        Args:
            keys: List of storage keys.

        Returns:
            Dict mapping key to value (missing keys omitted).
        """
        result: Dict[str, Any] = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value
        return result

    async def set_many(
        self, items: Dict[str, Any], ttl: Optional[timedelta] = None
    ) -> None:
        """
        Set multiple key-value pairs.

        Default implementation calls set() for each pair.
        Subclasses may override for batch optimization.

        Args:
            items: Dict of key-value pairs to store.
            ttl: Optional TTL applied to all items.
        """
        for key, value in items.items():
            await self.set(key, value, ttl=ttl)

    async def count(self) -> int:
        """
        Count keys managed by this backend instance.

        Default implementation uses keys("*").
        Subclasses may override for efficiency.

        Returns:
            Number of keys.
        """
        all_keys = await self.keys("*")
        return len(all_keys)
