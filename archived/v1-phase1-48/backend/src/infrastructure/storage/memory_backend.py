"""
InMemory Storage Backend — Sprint 119

Thread-safe in-memory storage for testing and fallback.
Implements the same StorageBackend protocol as RedisStorageBackend.
"""

import asyncio
import fnmatch
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class InMemoryStorageBackend:
    """
    In-memory storage backend with TTL support.

    Thread-safe via asyncio.Lock. Suitable for:
    - Unit testing (no Redis dependency)
    - Development fallback when Redis is unavailable
    - Single-worker deployments

    Warning:
        Data is NOT persistent across restarts.
        NOT safe for multi-worker (multi-process) deployments.

    Args:
        prefix: Key prefix for namespace isolation.
        default_ttl: Default TTL in seconds (None = no expiration).
    """

    def __init__(
        self,
        prefix: str = "",
        default_ttl: Optional[int] = None,
    ):
        self._prefix = prefix
        self._default_ttl = default_ttl
        self._data: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}  # key -> expiry timestamp
        self._sets: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()

    @property
    def prefix(self) -> str:
        """Return the key prefix."""
        return self._prefix

    def _make_key(self, key: str) -> str:
        """Build a full key with prefix."""
        if self._prefix:
            return f"{self._prefix}:{key}"
        return key

    def _strip_prefix(self, full_key: str) -> str:
        """Remove prefix from a full key."""
        if self._prefix and full_key.startswith(f"{self._prefix}:"):
            return full_key[len(self._prefix) + 1:]
        return full_key

    def _is_expired(self, full_key: str) -> bool:
        """Check if a key has expired."""
        if full_key in self._expiry:
            if time.monotonic() >= self._expiry[full_key]:
                return True
        return False

    def _cleanup_expired(self, full_key: str) -> None:
        """Remove an expired key."""
        self._data.pop(full_key, None)
        self._expiry.pop(full_key, None)

    async def get(self, key: str) -> Optional[Any]:
        """Get a value by key."""
        full_key = self._make_key(key)
        async with self._lock:
            if self._is_expired(full_key):
                self._cleanup_expired(full_key)
                return None
            return self._data.get(full_key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value with optional TTL."""
        full_key = self._make_key(key)
        effective_ttl = ttl if ttl is not None else self._default_ttl

        async with self._lock:
            self._data[full_key] = value
            if effective_ttl is not None:
                self._expiry[full_key] = time.monotonic() + effective_ttl
            elif full_key in self._expiry:
                del self._expiry[full_key]

    async def delete(self, key: str) -> bool:
        """Delete a key. Returns True if key existed."""
        full_key = self._make_key(key)
        async with self._lock:
            existed = full_key in self._data
            self._data.pop(full_key, None)
            self._expiry.pop(full_key, None)
            return existed

    async def exists(self, key: str) -> bool:
        """Check if a key exists (and is not expired)."""
        full_key = self._make_key(key)
        async with self._lock:
            if self._is_expired(full_key):
                self._cleanup_expired(full_key)
                return False
            return full_key in self._data

    async def list_keys(self, pattern: str = "*") -> List[str]:
        """List keys matching a glob pattern (after prefix)."""
        full_pattern = self._make_key(pattern)
        async with self._lock:
            # Clean expired first
            expired_keys = [k for k in self._data if self._is_expired(k)]
            for k in expired_keys:
                self._cleanup_expired(k)

            matching = [
                self._strip_prefix(k)
                for k in self._data
                if fnmatch.fnmatch(k, full_pattern)
            ]
        return matching

    async def set_add(self, key: str, *members: str) -> int:
        """Add members to a set."""
        full_key = self._make_key(key)
        async with self._lock:
            if full_key not in self._sets:
                self._sets[full_key] = set()
            before = len(self._sets[full_key])
            self._sets[full_key].update(members)
            return len(self._sets[full_key]) - before

    async def set_remove(self, key: str, *members: str) -> int:
        """Remove members from a set."""
        full_key = self._make_key(key)
        async with self._lock:
            if full_key not in self._sets:
                return 0
            before = len(self._sets[full_key])
            self._sets[full_key] -= set(members)
            return before - len(self._sets[full_key])

    async def set_members(self, key: str) -> set:
        """Get all members of a set."""
        full_key = self._make_key(key)
        async with self._lock:
            return set(self._sets.get(full_key, set()))

    async def clear_all(self) -> int:
        """Delete all keys with this prefix."""
        prefix_match = f"{self._prefix}:" if self._prefix else ""
        async with self._lock:
            if not prefix_match:
                count = len(self._data) + len(self._sets)
                self._data.clear()
                self._expiry.clear()
                self._sets.clear()
                return count

            keys_to_remove = [
                k for k in self._data if k.startswith(prefix_match)
            ]
            sets_to_remove = [
                k for k in self._sets if k.startswith(prefix_match)
            ]
            for k in keys_to_remove:
                self._data.pop(k, None)
                self._expiry.pop(k, None)
            for k in sets_to_remove:
                self._sets.pop(k, None)

            count = len(keys_to_remove) + len(sets_to_remove)
            logger.debug(f"Cleared {count} in-memory keys with prefix '{self._prefix}'")
            return count
