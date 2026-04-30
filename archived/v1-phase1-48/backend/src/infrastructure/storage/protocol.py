"""
Storage Backend Protocol — Sprint 119

Defines the unified interface for all storage backends.
Both Redis and InMemory implementations must conform to this protocol.
"""

from typing import Any, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    """
    Unified storage backend protocol.

    All storage implementations (Redis, InMemory, PostgreSQL) must
    provide these methods for interoperability.

    Key Prefix:
        Each backend instance has an isolated key prefix to prevent
        collisions between different storage consumers.
    """

    @property
    def prefix(self) -> str:
        """Return the key prefix for this storage backend."""
        ...

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value by key.

        Args:
            key: Storage key (will be prefixed internally).

        Returns:
            Deserialized value, or None if key does not exist.
        """
        ...

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value with optional TTL.

        Args:
            key: Storage key (will be prefixed internally).
            value: Value to store (must be JSON-serializable).
            ttl: Time-to-live in seconds. None means no expiration.
        """
        ...

    async def delete(self, key: str) -> bool:
        """
        Delete a key.

        Args:
            key: Storage key.

        Returns:
            True if the key existed and was deleted, False otherwise.
        """
        ...

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists.

        Args:
            key: Storage key.

        Returns:
            True if key exists.
        """
        ...

    async def list_keys(self, pattern: str = "*") -> List[str]:
        """
        List keys matching a pattern.

        Args:
            pattern: Glob-style pattern (e.g., "session:*").
                     Applied after the prefix.

        Returns:
            List of matching keys (without prefix).
        """
        ...

    async def set_add(self, key: str, *members: str) -> int:
        """
        Add members to a set.

        Args:
            key: Set key.
            members: Values to add.

        Returns:
            Number of new members added.
        """
        ...

    async def set_remove(self, key: str, *members: str) -> int:
        """
        Remove members from a set.

        Args:
            key: Set key.
            members: Values to remove.

        Returns:
            Number of members removed.
        """
        ...

    async def set_members(self, key: str) -> set:
        """
        Get all members of a set.

        Args:
            key: Set key.

        Returns:
            Set of member values.
        """
        ...

    async def clear_all(self) -> int:
        """
        Delete all keys with this backend's prefix.

        Returns:
            Number of keys deleted.

        Warning:
            Use with caution — this deletes ALL data for this prefix.
        """
        ...
