"""
InMemory Backend — Sprint 110

Development/testing storage backend with TTL support.
Uses dict + expiry timestamps, protected by asyncio.Lock.

Warning:
    Data is NOT persistent across restarts.
    NOT safe for multi-worker (multi-process) deployments.
"""

import asyncio
import fnmatch
import logging
import time
from datetime import timedelta
from typing import Any, Dict, List, Optional

from src.infrastructure.storage.backends.base import StorageBackendABC

logger = logging.getLogger(__name__)


class InMemoryBackend(StorageBackendABC):
    """
    In-memory storage backend with TTL support.

    Suitable for:
    - Unit testing (no external dependencies)
    - Development fallback when Redis/PostgreSQL unavailable
    - Single-worker deployments

    Args:
        prefix: Key prefix for namespace isolation.
        default_ttl: Default TTL for all keys. None means no expiration.
    """

    def __init__(
        self,
        prefix: str = "",
        default_ttl: Optional[timedelta] = None,
    ):
        self._prefix = prefix
        self._default_ttl = default_ttl
        self._data: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}  # key -> monotonic expiry time
        self._lock = asyncio.Lock()

    def _make_key(self, key: str) -> str:
        """Build a full key with prefix."""
        if self._prefix:
            return f"{self._prefix}:{key}"
        return key

    def _strip_prefix(self, full_key: str) -> str:
        """Remove prefix from a full key."""
        if self._prefix and full_key.startswith(f"{self._prefix}:"):
            return full_key[len(self._prefix) + 1 :]
        return full_key

    def _is_expired(self, full_key: str) -> bool:
        """Check if a key has expired."""
        if full_key in self._expiry:
            return time.monotonic() >= self._expiry[full_key]
        return False

    def _cleanup_expired(self, full_key: str) -> None:
        """Remove an expired key's data and expiry record."""
        self._data.pop(full_key, None)
        self._expiry.pop(full_key, None)

    def _resolve_ttl(self, ttl: Optional[timedelta]) -> Optional[float]:
        """Resolve TTL to seconds, using default if not specified."""
        effective = ttl if ttl is not None else self._default_ttl
        if effective is None:
            return None
        return effective.total_seconds()

    async def get(self, key: str) -> Optional[Any]:
        """Get a value by key. Returns None if expired or missing."""
        full_key = self._make_key(key)
        async with self._lock:
            if self._is_expired(full_key):
                self._cleanup_expired(full_key)
                return None
            return self._data.get(full_key)

    async def set(
        self, key: str, value: Any, ttl: Optional[timedelta] = None
    ) -> None:
        """Set a value with optional TTL."""
        full_key = self._make_key(key)
        ttl_seconds = self._resolve_ttl(ttl)

        async with self._lock:
            self._data[full_key] = value
            if ttl_seconds is not None:
                self._expiry[full_key] = time.monotonic() + ttl_seconds
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
        """Check if a key exists and is not expired."""
        full_key = self._make_key(key)
        async with self._lock:
            if self._is_expired(full_key):
                self._cleanup_expired(full_key)
                return False
            return full_key in self._data

    async def keys(self, pattern: str = "*") -> List[str]:
        """List keys matching a glob pattern (prefix-stripped)."""
        full_pattern = self._make_key(pattern)
        async with self._lock:
            # Clean expired keys first
            expired = [k for k in self._data if self._is_expired(k)]
            for k in expired:
                self._cleanup_expired(k)

            return [
                self._strip_prefix(k)
                for k in self._data
                if fnmatch.fnmatch(k, full_pattern)
            ]

    async def clear(self) -> None:
        """Delete all keys with this prefix."""
        async with self._lock:
            if not self._prefix:
                count = len(self._data)
                self._data.clear()
                self._expiry.clear()
                logger.debug(f"InMemoryBackend: cleared {count} keys (no prefix)")
                return

            prefix_match = f"{self._prefix}:"
            to_remove = [k for k in self._data if k.startswith(prefix_match)]
            for k in to_remove:
                self._data.pop(k, None)
                self._expiry.pop(k, None)
            logger.debug(
                f"InMemoryBackend[{self._prefix}]: cleared {len(to_remove)} keys"
            )

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Optimized batch get — single lock acquisition."""
        result: Dict[str, Any] = {}
        async with self._lock:
            for key in keys:
                full_key = self._make_key(key)
                if self._is_expired(full_key):
                    self._cleanup_expired(full_key)
                    continue
                if full_key in self._data:
                    result[key] = self._data[full_key]
        return result

    async def set_many(
        self, items: Dict[str, Any], ttl: Optional[timedelta] = None
    ) -> None:
        """Optimized batch set — single lock acquisition."""
        ttl_seconds = self._resolve_ttl(ttl)
        async with self._lock:
            for key, value in items.items():
                full_key = self._make_key(key)
                self._data[full_key] = value
                if ttl_seconds is not None:
                    self._expiry[full_key] = time.monotonic() + ttl_seconds
                elif full_key in self._expiry:
                    del self._expiry[full_key]

    async def count(self) -> int:
        """Count non-expired keys with this prefix."""
        async with self._lock:
            # Clean expired first
            expired = [k for k in self._data if self._is_expired(k)]
            for k in expired:
                self._cleanup_expired(k)

            if not self._prefix:
                return len(self._data)

            prefix_match = f"{self._prefix}:"
            return sum(1 for k in self._data if k.startswith(prefix_match))
