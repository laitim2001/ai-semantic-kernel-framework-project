"""
PostgreSQL Storage Backend — Sprint 110

Persistent key-value storage backed by PostgreSQL via asyncpg.
Uses a generic kv_store table with JSONB values and optional TTL.

Features:
- JSONB value storage with full PostgreSQL indexing support
- Namespace isolation via composite primary key (namespace, key)
- TTL via expires_at column with lazy cleanup on read
- Connection pool via asyncpg
- Graceful degradation to InMemoryBackend on connection failure

Table Schema:
    CREATE TABLE IF NOT EXISTS kv_store (
        namespace VARCHAR(100) NOT NULL,
        key VARCHAR(500) NOT NULL,
        value JSONB NOT NULL,
        expires_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        PRIMARY KEY (namespace, key)
    );
"""

import json
import logging
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.infrastructure.storage.backends.base import StorageBackendABC

logger = logging.getLogger(__name__)


class _PgJsonEncoder(json.JSONEncoder):
    """JSON encoder for PostgreSQL JSONB storage."""

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


def _pg_decode_hook(obj: dict) -> Any:
    """JSON decoder for PostgreSQL JSONB values."""
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


# SQL statements
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS kv_store (
    namespace VARCHAR(100) NOT NULL,
    key VARCHAR(500) NOT NULL,
    value JSONB NOT NULL,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (namespace, key)
);
"""

_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_kv_store_expires
    ON kv_store(expires_at)
    WHERE expires_at IS NOT NULL;
"""

_UPSERT_SQL = """
INSERT INTO kv_store (namespace, key, value, expires_at, created_at, updated_at)
VALUES ($1, $2, $3::jsonb, $4, NOW(), NOW())
ON CONFLICT (namespace, key) DO UPDATE SET
    value = EXCLUDED.value,
    expires_at = EXCLUDED.expires_at,
    updated_at = NOW();
"""

_GET_SQL = """
SELECT value, expires_at FROM kv_store
WHERE namespace = $1 AND key = $2;
"""

_DELETE_SQL = """
DELETE FROM kv_store WHERE namespace = $1 AND key = $2
RETURNING key;
"""

_EXISTS_SQL = """
SELECT 1 FROM kv_store
WHERE namespace = $1 AND key = $2
AND (expires_at IS NULL OR expires_at > NOW());
"""

_KEYS_SQL = """
SELECT key FROM kv_store
WHERE namespace = $1
AND (expires_at IS NULL OR expires_at > NOW())
AND key LIKE $2;
"""

_CLEAR_SQL = """
DELETE FROM kv_store WHERE namespace = $1;
"""

_COUNT_SQL = """
SELECT COUNT(*) FROM kv_store
WHERE namespace = $1
AND (expires_at IS NULL OR expires_at > NOW());
"""

_CLEANUP_EXPIRED_SQL = """
DELETE FROM kv_store
WHERE expires_at IS NOT NULL AND expires_at <= NOW();
"""

_BATCH_GET_SQL = """
SELECT key, value FROM kv_store
WHERE namespace = $1 AND key = ANY($2::varchar[])
AND (expires_at IS NULL OR expires_at > NOW());
"""


class PostgresBackend(StorageBackendABC):
    """
    PostgreSQL-based persistent key-value storage.

    Uses asyncpg connection pool for async database operations.
    Data is stored in a generic kv_store table with JSONB values.

    Args:
        dsn: PostgreSQL connection string (e.g., "postgresql://user:pass@host:5432/db").
        namespace: Namespace for key isolation (part of composite PK).
        default_ttl: Default TTL for all keys. None means no expiration.
        pool_min_size: Minimum connection pool size.
        pool_max_size: Maximum connection pool size.
    """

    def __init__(
        self,
        dsn: str,
        namespace: str = "default",
        default_ttl: Optional[timedelta] = None,
        pool_min_size: int = 2,
        pool_max_size: int = 10,
    ):
        self._dsn = dsn
        self._namespace = namespace
        self._default_ttl = default_ttl
        self._pool_min_size = pool_min_size
        self._pool_max_size = pool_max_size
        self._pool = None  # asyncpg.Pool, initialized lazily
        self._initialized = False

    async def _ensure_pool(self):
        """Ensure connection pool is created and table exists."""
        if self._pool is not None and self._initialized:
            return

        try:
            import asyncpg

            if self._pool is None:
                self._pool = await asyncpg.create_pool(
                    dsn=self._dsn,
                    min_size=self._pool_min_size,
                    max_size=self._pool_max_size,
                    command_timeout=30,
                )
                logger.info(
                    f"PostgresBackend[{self._namespace}]: connection pool created "
                    f"(min={self._pool_min_size}, max={self._pool_max_size})"
                )

            if not self._initialized:
                async with self._pool.acquire() as conn:
                    await conn.execute(_CREATE_TABLE_SQL)
                    await conn.execute(_CREATE_INDEX_SQL)
                self._initialized = True
                logger.info(
                    f"PostgresBackend[{self._namespace}]: kv_store table ensured"
                )

        except Exception as e:
            logger.error(
                f"PostgresBackend[{self._namespace}]: failed to initialize: {e}"
            )
            raise

    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string for JSONB storage."""
        return json.dumps(value, cls=_PgJsonEncoder, ensure_ascii=False)

    def _deserialize(self, raw: Any) -> Optional[Any]:
        """Deserialize JSONB value from PostgreSQL."""
        if raw is None:
            return None
        try:
            # asyncpg returns JSONB as already-parsed Python objects
            if isinstance(raw, str):
                return json.loads(raw, object_hook=_pg_decode_hook)
            # If asyncpg already parsed the JSON, apply decode hook manually
            return self._apply_decode_hook(raw)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(
                f"PostgresBackend[{self._namespace}]: failed to deserialize: {e}"
            )
            return raw

    def _apply_decode_hook(self, obj: Any) -> Any:
        """Recursively apply decode hook to already-parsed JSON objects."""
        if isinstance(obj, dict):
            # Apply hook to nested dicts first
            processed = {k: self._apply_decode_hook(v) for k, v in obj.items()}
            return _pg_decode_hook(processed)
        if isinstance(obj, list):
            return [self._apply_decode_hook(item) for item in obj]
        return obj

    def _resolve_expires_at(
        self, ttl: Optional[timedelta]
    ) -> Optional[datetime]:
        """Calculate expires_at timestamp from TTL."""
        effective = ttl if ttl is not None else self._default_ttl
        if effective is None:
            return None
        return datetime.now(timezone.utc) + effective

    @staticmethod
    def _glob_to_sql_like(pattern: str) -> str:
        """Convert glob pattern to SQL LIKE pattern."""
        # Escape SQL LIKE special characters first
        result = pattern.replace("%", "\\%").replace("_", "\\_")
        # Convert glob patterns
        result = result.replace("*", "%").replace("?", "_")
        return result

    async def get(self, key: str) -> Optional[Any]:
        """Get a value by key. Returns None if expired or missing."""
        await self._ensure_pool()
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(_GET_SQL, self._namespace, key)
                if row is None:
                    return None

                # Check expiry (lazy cleanup)
                expires_at = row["expires_at"]
                if expires_at is not None:
                    # Ensure timezone-aware comparison
                    now = datetime.now(timezone.utc)
                    exp = expires_at if expires_at.tzinfo else expires_at.replace(
                        tzinfo=timezone.utc
                    )
                    if exp <= now:
                        # Expired — delete and return None
                        await conn.execute(
                            _DELETE_SQL, self._namespace, key
                        )
                        return None

                return self._deserialize(row["value"])
        except Exception as e:
            logger.error(
                f"PostgresBackend[{self._namespace}] GET error for '{key}': {e}"
            )
            return None

    async def set(
        self, key: str, value: Any, ttl: Optional[timedelta] = None
    ) -> None:
        """Set a value with optional TTL (upsert)."""
        await self._ensure_pool()
        expires_at = self._resolve_expires_at(ttl)
        serialized = self._serialize(value)

        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    _UPSERT_SQL, self._namespace, key, serialized, expires_at
                )
        except Exception as e:
            logger.error(
                f"PostgresBackend[{self._namespace}] SET error for '{key}': {e}"
            )
            raise

    async def delete(self, key: str) -> bool:
        """Delete a key. Returns True if key existed."""
        await self._ensure_pool()
        try:
            async with self._pool.acquire() as conn:
                result = await conn.fetchrow(
                    _DELETE_SQL, self._namespace, key
                )
                return result is not None
        except Exception as e:
            logger.error(
                f"PostgresBackend[{self._namespace}] DELETE error for '{key}': {e}"
            )
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists and is not expired."""
        await self._ensure_pool()
        try:
            async with self._pool.acquire() as conn:
                result = await conn.fetchrow(
                    _EXISTS_SQL, self._namespace, key
                )
                return result is not None
        except Exception as e:
            logger.error(
                f"PostgresBackend[{self._namespace}] EXISTS error for '{key}': {e}"
            )
            return False

    async def keys(self, pattern: str = "*") -> List[str]:
        """List keys matching a glob pattern (non-expired only)."""
        await self._ensure_pool()
        like_pattern = self._glob_to_sql_like(pattern)
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    _KEYS_SQL, self._namespace, like_pattern
                )
                return [row["key"] for row in rows]
        except Exception as e:
            logger.error(
                f"PostgresBackend[{self._namespace}] KEYS error "
                f"for pattern '{pattern}': {e}"
            )
            return []

    async def clear(self) -> None:
        """Delete all keys in this namespace."""
        await self._ensure_pool()
        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(_CLEAR_SQL, self._namespace)
                logger.info(
                    f"PostgresBackend[{self._namespace}]: cleared ({result})"
                )
        except Exception as e:
            logger.error(
                f"PostgresBackend[{self._namespace}] CLEAR error: {e}"
            )

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Batch get using SQL ANY() for efficiency."""
        if not keys:
            return {}

        await self._ensure_pool()
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    _BATCH_GET_SQL, self._namespace, keys
                )
                return {
                    row["key"]: self._deserialize(row["value"])
                    for row in rows
                }
        except Exception as e:
            logger.error(
                f"PostgresBackend[{self._namespace}] batch GET error: {e}"
            )
            return {}

    async def count(self) -> int:
        """Count non-expired keys in this namespace."""
        await self._ensure_pool()
        try:
            async with self._pool.acquire() as conn:
                result = await conn.fetchval(_COUNT_SQL, self._namespace)
                return result or 0
        except Exception as e:
            logger.error(
                f"PostgresBackend[{self._namespace}] COUNT error: {e}"
            )
            return 0

    async def cleanup_expired(self) -> int:
        """
        Delete all expired keys across all namespaces.

        This is a maintenance operation that should be called periodically
        (e.g., every 5 minutes via a background task).

        Returns:
            Number of expired keys deleted.
        """
        await self._ensure_pool()
        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(_CLEANUP_EXPIRED_SQL)
                # Parse "DELETE N" result
                count = int(result.split()[-1]) if result else 0
                if count > 0:
                    logger.info(
                        f"PostgresBackend: cleaned up {count} expired keys"
                    )
                return count
        except Exception as e:
            logger.error(f"PostgresBackend cleanup_expired error: {e}")
            return 0

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            self._initialized = False
            logger.info(
                f"PostgresBackend[{self._namespace}]: connection pool closed"
            )
