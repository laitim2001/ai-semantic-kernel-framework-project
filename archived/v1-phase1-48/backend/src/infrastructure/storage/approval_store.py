"""
Approval State Store — Sprint 110

Persistent HITL (Human-in-the-Loop) approval storage backed by PostgreSQL.
Replaces InMemory approval dicts (AG-UI, Orchestration HITL, etc.)

Features:
- Structured ApprovalRecord with status tracking
- Query by status, user, time range
- Resolve (approve/reject/expire) with approver tracking
- Defaults to PostgreSQL for data durability (approvals must persist)
- Graceful degradation to InMemory in development

Usage:
    store = await ApprovalStore.create(backend_type="postgres")
    record = ApprovalRecord(
        approval_id="appr_001",
        request_type="workflow_execution",
        requester_id="user_123",
        metadata={"workflow_id": "wf_456"},
    )
    await store.submit(record)
    await store.resolve("appr_001", ApprovalStatus.APPROVED, approver_id="admin_1")
    pending = await store.get_pending(user_id="admin_1")
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from src.infrastructure.storage.backends.base import StorageBackendABC
from src.infrastructure.storage.backends.factory import StorageFactory

logger = logging.getLogger(__name__)


class ApprovalStatus(str, Enum):
    """Approval request status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class ApprovalRecord:
    """
    Structured approval request record.

    Attributes:
        approval_id: Unique approval identifier (auto-generated if not provided).
        request_type: Type of approval (e.g., "workflow_execution", "agent_action").
        status: Current approval status.
        requester_id: ID of the user/agent requesting approval.
        approver_id: ID of the user who resolved the approval (None if pending).
        created_at: When the approval was submitted.
        resolved_at: When the approval was resolved (None if pending).
        expires_at: When the approval expires (None means no expiry).
        metadata: Additional context for the approval request.
    """

    approval_id: str = field(default_factory=lambda: f"appr_{uuid.uuid4().hex[:12]}")
    request_type: str = ""
    status: ApprovalStatus = ApprovalStatus.PENDING
    requester_id: str = ""
    approver_id: Optional[str] = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for storage."""
        return {
            "approval_id": self.approval_id,
            "request_type": self.request_type,
            "status": self.status.value,
            "requester_id": self.requester_id,
            "approver_id": self.approver_id,
            "created_at": self.created_at.isoformat(),
            "resolved_at": (
                self.resolved_at.isoformat() if self.resolved_at else None
            ),
            "expires_at": (
                self.expires_at.isoformat() if self.expires_at else None
            ),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApprovalRecord":
        """Deserialize from dict."""
        return cls(
            approval_id=data.get("approval_id", ""),
            request_type=data.get("request_type", ""),
            status=ApprovalStatus(data.get("status", "pending")),
            requester_id=data.get("requester_id", ""),
            approver_id=data.get("approver_id"),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if data.get("created_at")
                else datetime.now(timezone.utc)
            ),
            resolved_at=(
                datetime.fromisoformat(data["resolved_at"])
                if data.get("resolved_at")
                else None
            ),
            expires_at=(
                datetime.fromisoformat(data["expires_at"])
                if data.get("expires_at")
                else None
            ),
            metadata=data.get("metadata", {}),
        )


class ApprovalStore:
    """
    Persistent approval state storage.

    Replaces InMemory approval dicts used across AG-UI, Orchestration HITL,
    and other approval workflows.

    Defaults to PostgreSQL backend for data durability — approval records
    must survive service restarts.

    Args:
        backend: StorageBackendABC instance.
    """

    def __init__(self, backend: StorageBackendABC):
        self._backend = backend

    @classmethod
    async def create(
        cls,
        backend_type: str = "auto",
        **kwargs,
    ) -> "ApprovalStore":
        """
        Factory method to create an ApprovalStore.

        Defaults to PostgreSQL for data persistence.
        Falls back to Redis or InMemory in development.

        Args:
            backend_type: "memory", "redis", "postgres", or "auto".
                         Auto prefers "postgres" for approval durability.
            **kwargs: Additional backend configuration.

        Returns:
            Configured ApprovalStore instance.
        """
        # For auto, prefer postgres since approvals must be durable
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
            name="approvals",
            backend_type=effective_type,
            namespace="approvals",
            **kwargs,
        )
        logger.info(
            f"ApprovalStore created with {type(backend).__name__}"
        )
        return cls(backend=backend)

    async def submit(self, record: ApprovalRecord) -> ApprovalRecord:
        """
        Submit a new approval request.

        Args:
            record: ApprovalRecord to submit.

        Returns:
            The submitted record (with generated ID if not provided).
        """
        record.status = ApprovalStatus.PENDING
        record.created_at = datetime.now(timezone.utc)

        # Calculate TTL if expires_at is set
        ttl = None
        if record.expires_at:
            remaining = record.expires_at - datetime.now(timezone.utc)
            if remaining.total_seconds() > 0:
                ttl = remaining
            else:
                record.status = ApprovalStatus.EXPIRED

        await self._backend.set(
            record.approval_id, record.to_dict(), ttl=ttl
        )

        # Also index by status for efficient queries
        await self._backend.set(
            f"idx:status:{record.status.value}:{record.approval_id}",
            record.approval_id,
            ttl=ttl,
        )

        logger.info(
            f"ApprovalStore: submitted {record.approval_id} "
            f"(type={record.request_type}, requester={record.requester_id})"
        )
        return record

    async def get(self, approval_id: str) -> Optional[ApprovalRecord]:
        """
        Get an approval record by ID.

        Automatically expires records past their expires_at.

        Args:
            approval_id: Unique approval identifier.

        Returns:
            ApprovalRecord, or None if not found.
        """
        data = await self._backend.get(approval_id)
        if data is None:
            return None

        record = ApprovalRecord.from_dict(data)

        # Check expiry
        if (
            record.status == ApprovalStatus.PENDING
            and record.expires_at
            and datetime.now(timezone.utc) >= record.expires_at
        ):
            record.status = ApprovalStatus.EXPIRED
            record.resolved_at = datetime.now(timezone.utc)
            await self._backend.set(approval_id, record.to_dict())
            # Clean up status index
            await self._backend.delete(
                f"idx:status:pending:{approval_id}"
            )
            await self._backend.set(
                f"idx:status:expired:{approval_id}",
                approval_id,
            )

        return record

    async def resolve(
        self,
        approval_id: str,
        status: ApprovalStatus,
        approver_id: str,
        metadata_updates: Optional[Dict[str, Any]] = None,
    ) -> Optional[ApprovalRecord]:
        """
        Resolve an approval request (approve/reject).

        Args:
            approval_id: Approval to resolve.
            status: New status (APPROVED or REJECTED).
            approver_id: ID of the user resolving the approval.
            metadata_updates: Additional metadata to merge.

        Returns:
            Updated ApprovalRecord, or None if not found.

        Raises:
            ValueError: If approval is not in PENDING status.
        """
        record = await self.get(approval_id)
        if record is None:
            logger.warning(
                f"ApprovalStore: approval {approval_id} not found"
            )
            return None

        if record.status != ApprovalStatus.PENDING:
            raise ValueError(
                f"Cannot resolve approval {approval_id}: "
                f"current status is {record.status.value}"
            )

        # Update record
        record.status = status
        record.approver_id = approver_id
        record.resolved_at = datetime.now(timezone.utc)

        if metadata_updates:
            record.metadata.update(metadata_updates)

        await self._backend.set(approval_id, record.to_dict())

        # Update status index
        await self._backend.delete(f"idx:status:pending:{approval_id}")
        await self._backend.set(
            f"idx:status:{status.value}:{approval_id}",
            approval_id,
        )

        logger.info(
            f"ApprovalStore: resolved {approval_id} -> {status.value} "
            f"by {approver_id}"
        )
        return record

    async def get_pending(
        self,
        user_id: Optional[str] = None,
        request_type: Optional[str] = None,
    ) -> List[ApprovalRecord]:
        """
        Get pending approval requests.

        Args:
            user_id: Filter by requester ID (optional).
            request_type: Filter by request type (optional).

        Returns:
            List of pending ApprovalRecords.
        """
        # Find pending approval keys
        pending_keys = await self._backend.keys("idx:status:pending:*")
        if not pending_keys:
            return []

        # Fetch actual approval IDs from index
        approval_ids = []
        for idx_key in pending_keys:
            aid = await self._backend.get(idx_key)
            if aid:
                approval_ids.append(aid)

        # Fetch records
        results: List[ApprovalRecord] = []
        for aid in approval_ids:
            record = await self.get(aid)
            if record is None or record.status != ApprovalStatus.PENDING:
                continue

            # Apply filters
            if user_id and record.requester_id != user_id:
                continue
            if request_type and record.request_type != request_type:
                continue

            results.append(record)

        return results

    async def get_history(
        self,
        limit: int = 50,
        status_filter: Optional[ApprovalStatus] = None,
        requester_id: Optional[str] = None,
    ) -> List[ApprovalRecord]:
        """
        Get approval history (all statuses).

        Args:
            limit: Maximum records to return.
            status_filter: Filter by status (optional).
            requester_id: Filter by requester (optional).

        Returns:
            List of ApprovalRecords, newest first.
        """
        # Get all approval keys (non-index keys)
        all_keys = await self._backend.keys("appr_*")

        records: List[ApprovalRecord] = []
        for key in all_keys:
            if len(records) >= limit:
                break

            data = await self._backend.get(key)
            if data is None:
                continue

            record = ApprovalRecord.from_dict(data)

            # Apply filters
            if status_filter and record.status != status_filter:
                continue
            if requester_id and record.requester_id != requester_id:
                continue

            records.append(record)

        # Sort by created_at descending
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records[:limit]

    async def cancel(self, approval_id: str) -> Optional[ApprovalRecord]:
        """
        Cancel a pending approval.

        Args:
            approval_id: Approval to cancel.

        Returns:
            Updated ApprovalRecord, or None if not found.
        """
        record = await self.get(approval_id)
        if record is None:
            return None

        if record.status != ApprovalStatus.PENDING:
            raise ValueError(
                f"Cannot cancel approval {approval_id}: "
                f"current status is {record.status.value}"
            )

        record.status = ApprovalStatus.CANCELLED
        record.resolved_at = datetime.now(timezone.utc)

        await self._backend.set(approval_id, record.to_dict())
        await self._backend.delete(f"idx:status:pending:{approval_id}")
        await self._backend.set(
            f"idx:status:cancelled:{approval_id}",
            approval_id,
        )

        logger.info(f"ApprovalStore: cancelled {approval_id}")
        return record

    async def count_pending(self) -> int:
        """Count pending approvals."""
        pending_keys = await self._backend.keys("idx:status:pending:*")
        return len(pending_keys)

    async def clear(self) -> None:
        """Delete all approval records. Use with caution."""
        await self._backend.clear()
        logger.warning("ApprovalStore: all records cleared")
