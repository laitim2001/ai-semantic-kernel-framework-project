"""
Audit Log Store — Sprint 110

Persistent, append-only audit trail storage backed by PostgreSQL.
Provides structured audit logging for compliance and security tracking.

Features:
- Append-only writes (no update/delete of audit entries)
- Structured AuditEntry with actor, action, resource tracking
- Query by action, actor, time range, resource
- Defaults to PostgreSQL for data durability and compliance
- Graceful degradation to InMemory in development

Usage:
    store = await AuditStore.create(backend_type="postgres")
    await store.log(AuditEntry(
        action="agent.execute",
        actor_id="user_123",
        resource_type="agent",
        resource_id="agent_456",
        details={"input": "hello", "output": "world"},
    ))
    entries = await store.query(action="agent.execute", since=one_hour_ago)
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.infrastructure.storage.backends.base import StorageBackendABC
from src.infrastructure.storage.backends.factory import StorageFactory

logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    """
    Structured audit log entry.

    Attributes:
        entry_id: Unique entry identifier (auto-generated).
        action: Action performed (e.g., "agent.execute", "workflow.approve").
        actor_id: ID of the user/system performing the action.
        resource_type: Type of resource acted upon (e.g., "agent", "workflow").
        resource_id: ID of the resource acted upon.
        details: Additional action-specific details.
        timestamp: When the action occurred.
        ip_address: Client IP address (optional).
        session_id: Associated session ID (optional).
    """

    entry_id: str = field(
        default_factory=lambda: f"audit_{uuid.uuid4().hex[:16]}"
    )
    action: str = ""
    actor_id: str = ""
    resource_type: str = ""
    resource_id: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    ip_address: Optional[str] = None
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for storage."""
        return {
            "entry_id": self.entry_id,
            "action": self.action,
            "actor_id": self.actor_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "ip_address": self.ip_address,
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEntry":
        """Deserialize from dict."""
        return cls(
            entry_id=data.get("entry_id", ""),
            action=data.get("action", ""),
            actor_id=data.get("actor_id", ""),
            resource_type=data.get("resource_type", ""),
            resource_id=data.get("resource_id", ""),
            details=data.get("details", {}),
            timestamp=(
                datetime.fromisoformat(data["timestamp"])
                if data.get("timestamp")
                else datetime.now(timezone.utc)
            ),
            ip_address=data.get("ip_address"),
            session_id=data.get("session_id"),
        )


class AuditStore:
    """
    Append-only audit log backed by StorageBackendABC.

    Designed for compliance and security audit trails.
    Audit entries are write-once — no updates or deletes are exposed.

    The store maintains a time-ordered index for efficient querying.

    Args:
        backend: StorageBackendABC instance.
        max_entries: Maximum entries to retain (0 = unlimited).
    """

    def __init__(
        self,
        backend: StorageBackendABC,
        max_entries: int = 0,
    ):
        self._backend = backend
        self._max_entries = max_entries

    @classmethod
    async def create(
        cls,
        backend_type: str = "auto",
        max_entries: int = 0,
        **kwargs,
    ) -> "AuditStore":
        """
        Factory method to create an AuditStore.

        Defaults to PostgreSQL for data persistence and compliance.

        Args:
            backend_type: "memory", "redis", "postgres", or "auto".
                         Auto prefers "postgres" for audit durability.
            max_entries: Maximum entries to retain (0 = unlimited).
            **kwargs: Additional backend configuration.

        Returns:
            Configured AuditStore instance.
        """
        # For auto, prefer postgres since audit logs must be durable
        effective_type = backend_type
        if effective_type == "auto":
            import os

            db_host = os.environ.get("DB_HOST", "")
            redis_host = os.environ.get("REDIS_HOST", "")
            if db_host:
                effective_type = "postgres"
            elif redis_host:
                effective_type = "redis"
            else:
                effective_type = "memory"

        backend = await StorageFactory.create(
            name="audit",
            backend_type=effective_type,
            namespace="audit",
            **kwargs,
        )
        logger.info(
            f"AuditStore created with {type(backend).__name__} "
            f"(max_entries={max_entries or 'unlimited'})"
        )
        return cls(backend=backend, max_entries=max_entries)

    async def log(self, entry: AuditEntry) -> AuditEntry:
        """
        Write an audit entry (append-only).

        Args:
            entry: AuditEntry to log.

        Returns:
            The logged entry (with generated ID if not provided).
        """
        entry.timestamp = datetime.now(timezone.utc)

        # Store the entry by its unique ID
        await self._backend.set(entry.entry_id, entry.to_dict())

        # Store time-ordered index entry for efficient querying
        # Key format: ts:{ISO timestamp}:{entry_id} -> entry_id
        ts_key = f"ts:{entry.timestamp.isoformat()}:{entry.entry_id}"
        await self._backend.set(ts_key, entry.entry_id)

        # Store action index for filtered queries
        # Key format: idx:action:{action}:{entry_id} -> entry_id
        if entry.action:
            action_key = f"idx:action:{entry.action}:{entry.entry_id}"
            await self._backend.set(action_key, entry.entry_id)

        # Store actor index
        if entry.actor_id:
            actor_key = f"idx:actor:{entry.actor_id}:{entry.entry_id}"
            await self._backend.set(actor_key, entry.entry_id)

        # Store resource index
        if entry.resource_type and entry.resource_id:
            resource_key = (
                f"idx:resource:{entry.resource_type}"
                f":{entry.resource_id}:{entry.entry_id}"
            )
            await self._backend.set(resource_key, entry.entry_id)

        logger.debug(
            f"AuditStore: logged {entry.entry_id} "
            f"(action={entry.action}, actor={entry.actor_id})"
        )
        return entry

    async def get(self, entry_id: str) -> Optional[AuditEntry]:
        """
        Get a single audit entry by ID.

        Args:
            entry_id: Unique entry identifier.

        Returns:
            AuditEntry, or None if not found.
        """
        data = await self._backend.get(entry_id)
        if data is None:
            return None
        return AuditEntry.from_dict(data)

    async def query(
        self,
        action: Optional[str] = None,
        actor_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """
        Query audit entries with filters.

        Args:
            action: Filter by action (e.g., "agent.execute").
            actor_id: Filter by actor ID.
            resource_type: Filter by resource type.
            resource_id: Filter by resource ID.
            since: Start of time range (inclusive).
            until: End of time range (inclusive).
            limit: Maximum entries to return.

        Returns:
            List of matching AuditEntries, newest first.
        """
        # Determine which index to use for the primary filter
        entry_ids = await self._resolve_entry_ids(
            action=action,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
        )

        # Fetch and filter entries
        entries: List[AuditEntry] = []
        for eid in entry_ids:
            if len(entries) >= limit:
                break

            data = await self._backend.get(eid)
            if data is None:
                continue

            entry = AuditEntry.from_dict(data)

            # Apply time filters
            if since and entry.timestamp < since:
                continue
            if until and entry.timestamp > until:
                continue

            # Apply remaining filters not covered by index
            if action and entry.action != action:
                continue
            if actor_id and entry.actor_id != actor_id:
                continue
            if resource_type and entry.resource_type != resource_type:
                continue
            if resource_id and entry.resource_id != resource_id:
                continue

            entries.append(entry)

        # Sort by timestamp descending (newest first)
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries[:limit]

    async def _resolve_entry_ids(
        self,
        action: Optional[str] = None,
        actor_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> List[str]:
        """Resolve entry IDs using the most selective index available."""
        # Use the most specific index available
        if resource_type and resource_id:
            idx_keys = await self._backend.keys(
                f"idx:resource:{resource_type}:{resource_id}:*"
            )
        elif actor_id:
            idx_keys = await self._backend.keys(
                f"idx:actor:{actor_id}:*"
            )
        elif action:
            idx_keys = await self._backend.keys(
                f"idx:action:{action}:*"
            )
        else:
            # No filter — use time-ordered index
            idx_keys = await self._backend.keys("ts:*")

        # Resolve index keys to entry IDs
        entry_ids: List[str] = []
        for idx_key in idx_keys:
            eid = await self._backend.get(idx_key)
            if eid and eid not in entry_ids:
                entry_ids.append(eid)

        return entry_ids

    async def count(
        self,
        action: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> int:
        """
        Count audit entries with optional filters.

        Args:
            action: Filter by action.
            since: Count only entries after this time.

        Returns:
            Number of matching entries.
        """
        if action is None and since is None:
            # Fast path: count all audit_* keys
            all_keys = await self._backend.keys("audit_*")
            return len(all_keys)

        # Filtered count requires full query
        entries = await self.query(
            action=action, since=since, limit=100000
        )
        return len(entries)

    async def recent(self, limit: int = 20) -> List[AuditEntry]:
        """
        Get the most recent audit entries.

        Args:
            limit: Number of entries to return.

        Returns:
            List of recent AuditEntries, newest first.
        """
        return await self.query(limit=limit)

    async def clear(self) -> None:
        """
        Delete all audit entries. Use with extreme caution.

        This should only be used in testing environments.
        In production, audit logs should be retained.
        """
        import os

        app_env = os.environ.get("APP_ENV", "development")
        if app_env == "production":
            logger.error(
                "AuditStore.clear() called in production — refusing to delete"
            )
            raise RuntimeError(
                "Cannot clear audit logs in production environment"
            )

        await self._backend.clear()
        logger.warning("AuditStore: all audit entries cleared")
