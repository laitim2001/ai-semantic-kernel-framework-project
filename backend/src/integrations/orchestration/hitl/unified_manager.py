"""
Unified HITL Approval Manager -- Sprint 111

Single source of truth for all approval workflows across the IPA Platform.

Consolidates 4-5 independent approval systems into one manager that:
1. Receives approval requests from any source (Orchestration, AG-UI, Claude SDK, MAF)
2. Stores state in persistent ApprovalStore (PostgreSQL)
3. Routes notifications (Teams, SSE, etc.)
4. Tracks lifecycle: PENDING -> APPROVED/REJECTED/EXPIRED/CANCELLED

Usage:
    from src.integrations.orchestration.hitl.unified_manager import (
        UnifiedApprovalManager, ApprovalRequest, ApprovalSource,
    )

    manager = UnifiedApprovalManager(approval_store=store)
    request = ApprovalRequest(
        source=ApprovalSource.ORCHESTRATION,
        title="Deploy to production",
        description="Release v2.1.0 to production cluster",
        requester_id="user_123",
    )
    request_id = await manager.submit_approval(request)
    result = await manager.resolve_approval(request_id, approved=True, approver_id="admin_1")
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

from src.infrastructure.storage.approval_store import (
    ApprovalRecord,
    ApprovalStatus,
    ApprovalStore,
)

logger = logging.getLogger(__name__)


class ApprovalSource(str, Enum):
    """Source system that originated the approval request."""

    ORCHESTRATION = "orchestration"  # Phase 28 HITLController
    AG_UI = "ag_ui"  # AG-UI SSE approval
    CLAUDE_SDK = "claude_sdk"  # Claude SDK ApprovalHook
    MAF_HANDOFF = "maf_handoff"  # MAF handoff_hitl
    ORCHESTRATOR_AGENT = "agent"  # Orchestrator Agent request_approval tool


class ApprovalPriority(str, Enum):
    """Priority level for approval requests."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


# Type alias for approval callbacks
ApprovalCallback = Callable[
    [str, bool, Optional[str]],
    Coroutine[Any, Any, None],
]


@dataclass
class ApprovalRequest:
    """
    Unified approval request data structure.

    Normalizes approval requests from all source systems into a single
    format for consistent processing and storage.

    Attributes:
        request_id: Unique identifier (auto-generated if not provided).
        source: Which system originated the request.
        priority: Urgency level affecting notification and timeout.
        title: Short summary of what needs approval.
        description: Detailed explanation for the approver.
        requester_id: ID of the user or agent requesting approval.
        session_id: Associated chat/dialog session (optional).
        risk_level: Risk assessment result (optional).
        tool_name: Tool call requiring approval (optional, for SDK/AG-UI).
        tool_args: Arguments for the tool call (optional).
        timeout_minutes: How long before the request expires.
        metadata: Additional context from the source system.
        created_at: When the request was created.
    """

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: ApprovalSource = ApprovalSource.ORCHESTRATION
    priority: ApprovalPriority = ApprovalPriority.NORMAL
    title: str = ""
    description: str = ""
    requester_id: Optional[str] = None
    session_id: Optional[str] = None
    risk_level: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    timeout_minutes: int = 30
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_approval_record(self) -> ApprovalRecord:
        """Convert to ApprovalRecord for persistent storage."""
        expires_at = self.created_at + timedelta(minutes=self.timeout_minutes)

        metadata = {
            **self.metadata,
            "source": self.source.value,
            "priority": self.priority.value,
            "title": self.title,
            "description": self.description,
        }
        if self.session_id:
            metadata["session_id"] = self.session_id
        if self.risk_level:
            metadata["risk_level"] = self.risk_level
        if self.tool_name:
            metadata["tool_name"] = self.tool_name
        if self.tool_args is not None:
            metadata["tool_args"] = self.tool_args

        return ApprovalRecord(
            approval_id=self.request_id,
            request_type=f"{self.source.value}_approval",
            status=ApprovalStatus.PENDING,
            requester_id=self.requester_id or "",
            created_at=self.created_at,
            expires_at=expires_at,
            metadata=metadata,
        )


class UnifiedApprovalManager:
    """
    Single entry point for all HITL approval workflows.

    Provides a unified interface that all approval sources (Orchestration,
    AG-UI, Claude SDK, MAF) delegate to. Manages the full approval lifecycle
    from submission through resolution/expiration.

    Supports two operating modes:
    - With ApprovalStore: Full persistent storage (PostgreSQL/Redis)
    - Without ApprovalStore: In-memory fallback for development/testing

    Args:
        approval_store: Optional ApprovalStore instance from Sprint 110.
                       If None, uses in-memory dict as fallback.
    """

    def __init__(self, approval_store: Optional[ApprovalStore] = None):
        self._store = approval_store
        self._pending: Dict[str, Dict[str, Any]] = {}  # in-memory fallback
        self._callbacks: Dict[str, ApprovalCallback] = {}
        self._use_store = approval_store is not None

        if self._use_store:
            logger.info("UnifiedApprovalManager: using persistent ApprovalStore")
        else:
            logger.warning(
                "UnifiedApprovalManager: no ApprovalStore provided, "
                "using in-memory fallback (data will not survive restarts)"
            )

    async def submit_approval(self, request: ApprovalRequest) -> str:
        """
        Submit a new approval request.

        Stores the request in the persistent store (or in-memory fallback)
        and returns the request_id for tracking.

        Args:
            request: ApprovalRequest with all relevant context.

        Returns:
            The request_id string for subsequent operations.
        """
        if self._use_store:
            record = request.to_approval_record()
            await self._store.submit(record)
        else:
            # In-memory fallback
            expires_at = request.created_at + timedelta(
                minutes=request.timeout_minutes
            )
            self._pending[request.request_id] = {
                "request_id": request.request_id,
                "source": request.source.value,
                "priority": request.priority.value,
                "title": request.title,
                "description": request.description,
                "requester_id": request.requester_id,
                "session_id": request.session_id,
                "risk_level": request.risk_level,
                "tool_name": request.tool_name,
                "tool_args": request.tool_args,
                "timeout_minutes": request.timeout_minutes,
                "metadata": request.metadata,
                "status": ApprovalStatus.PENDING.value,
                "created_at": request.created_at.isoformat(),
                "expires_at": expires_at.isoformat(),
                "approver_id": None,
                "resolved_at": None,
                "comment": "",
            }

        logger.info(
            f"UnifiedApprovalManager: submitted approval {request.request_id} "
            f"(source={request.source.value}, priority={request.priority.value}, "
            f"title={request.title!r})"
        )
        return request.request_id

    async def resolve_approval(
        self,
        request_id: str,
        approved: bool,
        approver_id: str,
        comment: str = "",
    ) -> Dict[str, Any]:
        """
        Resolve a pending approval (approve or reject).

        Updates the stored record, invokes any registered callback,
        and returns the resolution result.

        Args:
            request_id: The approval request to resolve.
            approved: True for approve, False for reject.
            approver_id: ID of the user resolving the approval.
            comment: Optional comment from the approver.

        Returns:
            Dict with resolution details including status, approver, timestamp.

        Raises:
            ValueError: If the approval is not found or not in PENDING status.
        """
        new_status = (
            ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        )
        resolved_at = datetime.now(timezone.utc)

        if self._use_store:
            record = await self._store.resolve(
                approval_id=request_id,
                status=new_status,
                approver_id=approver_id,
                metadata_updates={"comment": comment} if comment else None,
            )
            if record is None:
                raise ValueError(
                    f"Approval {request_id} not found in store"
                )
            result = record.to_dict()
        else:
            # In-memory fallback
            entry = self._pending.get(request_id)
            if entry is None:
                raise ValueError(
                    f"Approval {request_id} not found in memory"
                )
            if entry["status"] != ApprovalStatus.PENDING.value:
                raise ValueError(
                    f"Approval {request_id} is not pending "
                    f"(current: {entry['status']})"
                )

            entry["status"] = new_status.value
            entry["approver_id"] = approver_id
            entry["resolved_at"] = resolved_at.isoformat()
            entry["comment"] = comment
            result = dict(entry)

        logger.info(
            f"UnifiedApprovalManager: resolved {request_id} -> "
            f"{new_status.value} by {approver_id}"
        )

        # Invoke callback if registered
        callback = self._callbacks.pop(request_id, None)
        if callback is not None:
            try:
                await callback(request_id, approved, comment or None)
            except Exception as exc:
                logger.error(
                    f"UnifiedApprovalManager: callback error for "
                    f"{request_id}: {exc}",
                    exc_info=True,
                )

        return result

    async def get_pending(
        self,
        user_id: Optional[str] = None,
        source: Optional[ApprovalSource] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all pending approvals, optionally filtered.

        Args:
            user_id: Filter by requester ID.
            source: Filter by approval source system.

        Returns:
            List of pending approval dicts.
        """
        if self._use_store:
            records = await self._store.get_pending(user_id=user_id)
            results = [r.to_dict() for r in records]
            # Apply source filter (not natively supported by ApprovalStore)
            if source is not None:
                results = [
                    r
                    for r in results
                    if r.get("metadata", {}).get("source") == source.value
                ]
            return results
        else:
            # In-memory fallback
            now = datetime.now(timezone.utc)
            results: List[Dict[str, Any]] = []
            for entry in self._pending.values():
                if entry["status"] != ApprovalStatus.PENDING.value:
                    continue

                # Check expiry
                if entry.get("expires_at"):
                    expires = datetime.fromisoformat(entry["expires_at"])
                    if now >= expires:
                        entry["status"] = ApprovalStatus.EXPIRED.value
                        entry["resolved_at"] = now.isoformat()
                        continue

                # Apply filters
                if user_id and entry.get("requester_id") != user_id:
                    continue
                if source and entry.get("source") != source.value:
                    continue

                results.append(dict(entry))

            return results

    async def get_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of an approval request.

        Args:
            request_id: The approval request ID.

        Returns:
            Dict with approval details, or None if not found.
        """
        if self._use_store:
            record = await self._store.get(request_id)
            if record is None:
                return None
            return record.to_dict()
        else:
            entry = self._pending.get(request_id)
            if entry is None:
                return None

            # Check expiry for pending items
            if entry["status"] == ApprovalStatus.PENDING.value:
                if entry.get("expires_at"):
                    expires = datetime.fromisoformat(entry["expires_at"])
                    if datetime.now(timezone.utc) >= expires:
                        entry["status"] = ApprovalStatus.EXPIRED.value
                        entry["resolved_at"] = datetime.now(
                            timezone.utc
                        ).isoformat()

            return dict(entry)

    async def cancel_approval(
        self, request_id: str, reason: str = ""
    ) -> bool:
        """
        Cancel a pending approval.

        Args:
            request_id: The approval request to cancel.
            reason: Optional cancellation reason.

        Returns:
            True if successfully cancelled, False if not found.

        Raises:
            ValueError: If the approval is not in PENDING status.
        """
        if self._use_store:
            try:
                record = await self._store.cancel(request_id)
                if record is None:
                    return False
                if reason:
                    # Update metadata with reason via the backend
                    record.metadata["cancel_reason"] = reason
                    await self._store._backend.set(
                        request_id, record.to_dict()
                    )
                logger.info(
                    f"UnifiedApprovalManager: cancelled {request_id} "
                    f"(reason={reason!r})"
                )
                return True
            except ValueError:
                raise
        else:
            entry = self._pending.get(request_id)
            if entry is None:
                return False
            if entry["status"] != ApprovalStatus.PENDING.value:
                raise ValueError(
                    f"Cannot cancel approval {request_id}: "
                    f"current status is {entry['status']}"
                )
            entry["status"] = ApprovalStatus.CANCELLED.value
            entry["resolved_at"] = datetime.now(timezone.utc).isoformat()
            entry["comment"] = reason
            logger.info(
                f"UnifiedApprovalManager: cancelled {request_id} "
                f"(reason={reason!r})"
            )
            return True

    async def check_expired(self) -> List[str]:
        """
        Check and expire timed-out approvals.

        Scans all pending approvals and marks those past their
        expiry time as EXPIRED.

        Returns:
            List of approval IDs that were expired.
        """
        expired_ids: List[str] = []

        if self._use_store:
            pending_records = await self._store.get_pending()
            now = datetime.now(timezone.utc)
            for record in pending_records:
                if (
                    record.expires_at
                    and now >= record.expires_at
                    and record.status == ApprovalStatus.PENDING
                ):
                    # The store's get() method auto-expires, but we
                    # explicitly trigger it here for batch processing
                    await self._store.get(record.approval_id)
                    expired_ids.append(record.approval_id)
        else:
            now = datetime.now(timezone.utc)
            for request_id, entry in self._pending.items():
                if entry["status"] != ApprovalStatus.PENDING.value:
                    continue
                if entry.get("expires_at"):
                    expires = datetime.fromisoformat(entry["expires_at"])
                    if now >= expires:
                        entry["status"] = ApprovalStatus.EXPIRED.value
                        entry["resolved_at"] = now.isoformat()
                        expired_ids.append(request_id)

        if expired_ids:
            logger.info(
                f"UnifiedApprovalManager: expired {len(expired_ids)} "
                f"approvals: {expired_ids}"
            )

        return expired_ids

    def register_callback(
        self,
        request_id: str,
        callback: ApprovalCallback,
    ) -> None:
        """
        Register a callback for when an approval is resolved.

        The callback will be invoked with (request_id, approved, comment)
        when resolve_approval is called for this request.

        Args:
            request_id: The approval request to watch.
            callback: Async callable (request_id, approved, comment) -> None.
        """
        self._callbacks[request_id] = callback
        logger.debug(
            f"UnifiedApprovalManager: registered callback for {request_id}"
        )

    def unregister_callback(self, request_id: str) -> bool:
        """
        Remove a previously registered callback.

        Args:
            request_id: The approval request to stop watching.

        Returns:
            True if a callback was removed, False if none was registered.
        """
        removed = self._callbacks.pop(request_id, None)
        return removed is not None

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics for approval management.

        Returns:
            Dict with counts by status and source.
        """
        if self._use_store:
            pending_count = await self._store.count_pending()
            return {
                "pending_count": pending_count,
                "callback_count": len(self._callbacks),
                "storage_backend": "persistent",
            }
        else:
            status_counts: Dict[str, int] = {}
            source_counts: Dict[str, int] = {}
            for entry in self._pending.values():
                status = entry.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
                src = entry.get("source", "unknown")
                source_counts[src] = source_counts.get(src, 0) + 1

            return {
                "total": len(self._pending),
                "by_status": status_counts,
                "by_source": source_counts,
                "callback_count": len(self._callbacks),
                "storage_backend": "in_memory",
            }
