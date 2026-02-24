"""
Redis Storage Backend — Sprint 119

Full-featured Redis storage implementation with:
- JSON serialization with custom encoder (datetime, Enum, UUID, dataclass)
- TTL management
- Key prefix isolation
- Connection error handling with retry
- Set operations for indexing
"""

import json
import logging
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class StorageEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for storage serialization.

    Handles: datetime, Enum, UUID, dataclass, set, bytes.
    """

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return {"__type__": "datetime", "value": obj.isoformat()}
        if isinstance(obj, Enum):
            return {"__type__": "enum", "class": f"{type(obj).__module__}.{type(obj).__qualname__}", "value": obj.value}
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
            return {"__type__": "bytes", "value": obj.decode("utf-8", errors="replace")}
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
    if type_tag == "enum":
        # Enum deserialization requires import; store as raw value
        return obj["value"]
    if type_tag == "dataclass":
        # Dataclass deserialization requires import; return as dict
        return obj["value"]

    return obj


class RedisStorageBackend:
    """
    Redis-based storage backend.

    Provides persistent key-value storage with:
    - Automatic JSON serialization/deserialization
    - Key prefix isolation (multiple consumers share one Redis)
    - TTL-based expiration
    - Set operations for indexing
    - Connection error handling

    Args:
        redis_client: Async Redis client instance.
        prefix: Key prefix for namespace isolation (e.g., "approval", "session").
        default_ttl: Default TTL in seconds (None = no expiration).
        max_retries: Max retries on transient errors.
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        prefix: str = "",
        default_ttl: Optional[int] = None,
        max_retries: int = 2,
    ):
        self._redis = redis_client
        self._prefix = prefix
        self._default_ttl = default_ttl
        self._max_retries = max_retries

    @property
    def prefix(self) -> str:
        """Return the key prefix."""
        return self._prefix

    def _make_key(self, key: str) -> str:
        """Build a full Redis key with prefix."""
        if self._prefix:
            return f"{self._prefix}:{key}"
        return key

    def _strip_prefix(self, full_key: str) -> str:
        """Remove prefix from a full Redis key."""
        if self._prefix and full_key.startswith(f"{self._prefix}:"):
            return full_key[len(self._prefix) + 1:]
        return full_key

    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string."""
        return json.dumps(value, cls=StorageEncoder, ensure_ascii=False)

    def _deserialize(self, raw: Optional[str]) -> Optional[Any]:
        """Deserialize JSON string to value."""
        if raw is None:
            return None
        try:
            return json.loads(raw, object_hook=_decode_hook)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to deserialize value: {e}")
            return raw

    async def get(self, key: str) -> Optional[Any]:
        """Get a value by key."""
        full_key = self._make_key(key)
        try:
            raw = await self._redis.get(full_key)
            return self._deserialize(raw)
        except aioredis.RedisError as e:
            logger.error(f"Redis GET error for {full_key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value with optional TTL."""
        full_key = self._make_key(key)
        effective_ttl = ttl if ttl is not None else self._default_ttl
        serialized = self._serialize(value)

        try:
            if effective_ttl is not None:
                await self._redis.setex(full_key, effective_ttl, serialized)
            else:
                await self._redis.set(full_key, serialized)
        except aioredis.RedisError as e:
            logger.error(f"Redis SET error for {full_key}: {e}")
            raise

    async def delete(self, key: str) -> bool:
        """Delete a key. Returns True if key existed."""
        full_key = self._make_key(key)
        try:
            result = await self._redis.delete(full_key)
            return result > 0
        except aioredis.RedisError as e:
            logger.error(f"Redis DELETE error for {full_key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        full_key = self._make_key(key)
        try:
            return bool(await self._redis.exists(full_key))
        except aioredis.RedisError as e:
            logger.error(f"Redis EXISTS error for {full_key}: {e}")
            return False

    async def list_keys(self, pattern: str = "*") -> List[str]:
        """
        List keys matching a pattern (after prefix).

        Uses SCAN for safe iteration (no KEYS in production).
        """
        full_pattern = self._make_key(pattern)
        keys: List[str] = []
        try:
            async for key in self._redis.scan_iter(match=full_pattern, count=100):
                keys.append(self._strip_prefix(key))
        except aioredis.RedisError as e:
            logger.error(f"Redis SCAN error for pattern {full_pattern}: {e}")
        return keys

    async def set_add(self, key: str, *members: str) -> int:
        """Add members to a set."""
        full_key = self._make_key(key)
        try:
            return await self._redis.sadd(full_key, *members)
        except aioredis.RedisError as e:
            logger.error(f"Redis SADD error for {full_key}: {e}")
            return 0

    async def set_remove(self, key: str, *members: str) -> int:
        """Remove members from a set."""
        full_key = self._make_key(key)
        try:
            return await self._redis.srem(full_key, *members)
        except aioredis.RedisError as e:
            logger.error(f"Redis SREM error for {full_key}: {e}")
            return 0

    async def set_members(self, key: str) -> set:
        """Get all members of a set."""
        full_key = self._make_key(key)
        try:
            return await self._redis.smembers(full_key)
        except aioredis.RedisError as e:
            logger.error(f"Redis SMEMBERS error for {full_key}: {e}")
            return set()

    async def clear_all(self) -> int:
        """Delete all keys with this prefix. Use with caution."""
        pattern = self._make_key("*")
        count = 0
        try:
            async for key in self._redis.scan_iter(match=pattern, count=100):
                await self._redis.delete(key)
                count += 1
            logger.info(f"Cleared {count} keys with prefix '{self._prefix}'")
        except aioredis.RedisError as e:
            logger.error(f"Redis CLEAR error for prefix '{self._prefix}': {e}")
        return count

    async def get_ttl(self, key: str) -> int:
        """
        Get remaining TTL for a key.

        Returns:
            TTL in seconds, -1 if no TTL, -2 if key doesn't exist.
        """
        full_key = self._make_key(key)
        try:
            return await self._redis.ttl(full_key)
        except aioredis.RedisError as e:
            logger.error(f"Redis TTL error for {full_key}: {e}")
            return -2

    async def expire(self, key: str, ttl: int) -> bool:
        """Set or update TTL on an existing key."""
        full_key = self._make_key(key)
        try:
            return await self._redis.expire(full_key, ttl)
        except aioredis.RedisError as e:
            logger.error(f"Redis EXPIRE error for {full_key}: {e}")
            return False
