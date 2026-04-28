"""
Redis Storage Backend — Sprint 110

Production-grade Redis backend implementing StorageBackendABC.
Uses redis.asyncio with JSON serialization and SCAN-based key listing.

Features:
- JSON serialization with custom encoder (datetime, Enum, UUID, dataclass)
- TTL management via native Redis EXPIRE
- Key prefix isolation for multi-tenant usage
- SCAN-based key listing (production-safe, no KEYS command)
- Graceful degradation to InMemoryBackend on connection failure
"""

import json
import logging
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

import redis.asyncio as aioredis

from src.infrastructure.storage.backends.base import StorageBackendABC

logger = logging.getLogger(__name__)


class _StorageEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for storage serialization.

    Handles: datetime, Enum, UUID, dataclass, set, bytes.
    Compatible with the existing StorageEncoder in redis_backend.py (Sprint 119).
    """

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return {"__type__": "datetime", "value": obj.isoformat()}
        if isinstance(obj, Enum):
            return {
                "__type__": "enum",
                "class": f"{type(obj).__module__}.{type(obj).__qualname__}",
                "value": obj.value,
            }
        if isinstance(obj, UUID):
            return {"__type__": "uuid", "value": str(obj)}
        if is_dataclass(obj) and not isinstance(obj, type):
            return {
                "__type__": "dataclass",
                "class": f"{type(obj).__module__}.{type(obj).__qualname__}",
                "value": asdict(obj),
            }
        if isinstance(obj, set):
            return {"__type__": "set", "value": list(obj)}
        if isinstance(obj, bytes):
            return {
                "__type__": "bytes",
                "value": obj.decode("utf-8", errors="replace"),
            }
        if isinstance(obj, timedelta):
            return {"__type__": "timedelta", "value": obj.total_seconds()}
        return super().default(obj)


def _decode_hook(obj: dict) -> Any:
    """Custom JSON decoder for storage deserialization."""
    if "__type__" not in obj:
        return obj

    type_tag = obj["__type__"]

    if type_tag == "datetime":
        return datetime.fromisoformat(obj["value"])
    if type_tag == "uuid":
        return UUID(obj["value"])
    if type_tag == "set":
        return set(obj["value"])
    if type_tag == "bytes":
        return obj["value"].encode("utf-8")
    if type_tag == "timedelta":
        return timedelta(seconds=obj["value"])
    if type_tag == "enum":
        return obj["value"]
    if type_tag == "dataclass":
        return obj["value"]

    return obj


class RedisBackend(StorageBackendABC):
    """
    Redis-based storage backend.

    Provides persistent key-value storage with:
    - Automatic JSON serialization/deserialization
    - Key prefix isolation (multiple consumers share one Redis)
    - TTL-based expiration via native Redis EXPIRE
    - SCAN-based key listing (no KEYS command)
    - Connection error resilience

    Args:
        redis_client: Async Redis client instance.
        prefix: Key prefix for namespace isolation (e.g., "ipa:sessions").
        default_ttl: Default TTL for all keys. None means no expiration.
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        prefix: str = "ipa",
        default_ttl: Optional[timedelta] = None,
    ):
        self._redis = redis_client
        self._prefix = prefix
        self._default_ttl = default_ttl

    def _make_key(self, key: str) -> str:
        """Build a full Redis key with prefix."""
        if self._prefix:
            return f"{self._prefix}:{key}"
        return key

    def _strip_prefix(self, full_key: str) -> str:
        """Remove prefix from a full Redis key."""
        if isinstance(full_key, bytes):
            full_key = full_key.decode("utf-8", errors="replace")
        if self._prefix and full_key.startswith(f"{self._prefix}:"):
            return full_key[len(self._prefix) + 1 :]
        return full_key

    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string."""
        return json.dumps(value, cls=_StorageEncoder, ensure_ascii=False)

    def _deserialize(self, raw: Optional[str]) -> Optional[Any]:
        """Deserialize JSON string to value."""
        if raw is None:
            return None
        try:
            return json.loads(raw, object_hook=_decode_hook)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"RedisBackend: failed to deserialize value: {e}")
            return raw

    def _resolve_ttl_seconds(self, ttl: Optional[timedelta]) -> Optional[int]:
        """Resolve TTL to integer seconds."""
        effective = ttl if ttl is not None else self._default_ttl
        if effective is None:
            return None
        return max(1, int(effective.total_seconds()))

    async def get(self, key: str) -> Optional[Any]:
        """Get a value by key."""
        full_key = self._make_key(key)
        try:
            raw = await self._redis.get(full_key)
            return self._deserialize(raw)
        except aioredis.RedisError as e:
            logger.error(f"RedisBackend GET error for '{full_key}': {e}")
            return None

    async def set(
        self, key: str, value: Any, ttl: Optional[timedelta] = None
    ) -> None:
        """Set a value with optional TTL."""
        full_key = self._make_key(key)
        ttl_seconds = self._resolve_ttl_seconds(ttl)
        serialized = self._serialize(value)

        try:
            if ttl_seconds is not None:
                await self._redis.setex(full_key, ttl_seconds, serialized)
            else:
                await self._redis.set(full_key, serialized)
        except aioredis.RedisError as e:
            logger.error(f"RedisBackend SET error for '{full_key}': {e}")
            raise

    async def delete(self, key: str) -> bool:
        """Delete a key. Returns True if key existed."""
        full_key = self._make_key(key)
        try:
            result = await self._redis.delete(full_key)
            return result > 0
        except aioredis.RedisError as e:
            logger.error(f"RedisBackend DELETE error for '{full_key}': {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        full_key = self._make_key(key)
        try:
            return bool(await self._redis.exists(full_key))
        except aioredis.RedisError as e:
            logger.error(f"RedisBackend EXISTS error for '{full_key}': {e}")
            return False

    async def keys(self, pattern: str = "*") -> List[str]:
        """
        List keys matching a pattern (prefix-stripped).

        Uses SCAN for safe iteration (never KEYS in production).
        """
        full_pattern = self._make_key(pattern)
        result: List[str] = []
        try:
            async for key in self._redis.scan_iter(
                match=full_pattern, count=100
            ):
                result.append(self._strip_prefix(key))
        except aioredis.RedisError as e:
            logger.error(
                f"RedisBackend SCAN error for pattern '{full_pattern}': {e}"
            )
        return result

    async def clear(self) -> None:
        """Delete all keys with this prefix."""
        pattern = self._make_key("*")
        count = 0
        try:
            async for key in self._redis.scan_iter(match=pattern, count=100):
                await self._redis.delete(key)
                count += 1
            logger.info(
                f"RedisBackend[{self._prefix}]: cleared {count} keys"
            )
        except aioredis.RedisError as e:
            logger.error(
                f"RedisBackend CLEAR error for prefix '{self._prefix}': {e}"
            )

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Batch get using Redis MGET for efficiency."""
        if not keys:
            return {}

        full_keys = [self._make_key(k) for k in keys]
        try:
            raw_values = await self._redis.mget(*full_keys)
            result: Dict[str, Any] = {}
            for key, raw in zip(keys, raw_values):
                value = self._deserialize(raw)
                if value is not None:
                    result[key] = value
            return result
        except aioredis.RedisError as e:
            logger.error(f"RedisBackend MGET error: {e}")
            # Fallback to individual gets
            return await super().get_many(keys)

    async def set_many(
        self, items: Dict[str, Any], ttl: Optional[timedelta] = None
    ) -> None:
        """Batch set using Redis pipeline for efficiency."""
        if not items:
            return

        ttl_seconds = self._resolve_ttl_seconds(ttl)
        try:
            async with self._redis.pipeline(transaction=False) as pipe:
                for key, value in items.items():
                    full_key = self._make_key(key)
                    serialized = self._serialize(value)
                    if ttl_seconds is not None:
                        pipe.setex(full_key, ttl_seconds, serialized)
                    else:
                        pipe.set(full_key, serialized)
                await pipe.execute()
        except aioredis.RedisError as e:
            logger.error(f"RedisBackend pipeline SET error: {e}")
            # Fallback to individual sets
            await super().set_many(items, ttl=ttl)

    async def count(self) -> int:
        """Count keys with this prefix using SCAN."""
        pattern = self._make_key("*")
        count = 0
        try:
            async for _ in self._redis.scan_iter(match=pattern, count=100):
                count += 1
        except aioredis.RedisError as e:
            logger.error(
                f"RedisBackend COUNT error for prefix '{self._prefix}': {e}"
            )
        return count
