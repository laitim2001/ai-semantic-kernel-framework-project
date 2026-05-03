"""
File: backend/src/platform_layer/governance/hitl/manager.py
Purpose: DefaultHITLManager — concrete HITLManager implementation backed by
         existing `approvals` table (Sprint 49.3 schema).
Category: Platform / Governance / HITL
Scope: Phase 53 / Sprint 53.4 US-2

Description:
    Implements 17.md §5 HITLManager ABC over the existing `approvals` table
    (per 09-db-schema-design.md L566-601 / Sprint 49.3 0008_governance.py).

    Tenant isolation: via session_id → sessions.tenant_id JOIN.
    State machine: see state_machine.py (pending → approved/rejected/escalated/expired).
    Multi-instance pickup: SELECT ... FOR UPDATE SKIP LOCKED.
    Wait: poll-based (interval); production deployments may upgrade to LISTEN/NOTIFY.

Key Components:
    - DefaultHITLManager: subclass of agent_harness.hitl.HITLManager (ABC)

Created: 2026-05-03 (Sprint 53.4 Day 1)
Last Modified: 2026-05-03

Modification History:
    - 2026-05-03: Day 2 — full implementation (Sprint 53.4 Day 2)
    - 2026-05-03: Initial skeleton (Sprint 53.4 Day 1) — Day 2 to implement

Related:
    - agent_harness/hitl/_abc.py (HITLManager ABC)
    - agent_harness/_contracts/hitl.py (Single-source types)
    - 17-cross-category-interfaces.md §5
    - 09-db-schema-design.md §approvals
    - sprint-53-4-plan.md §US-2
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable
from uuid import UUID, uuid4

from sqlalchemy import select, update

from agent_harness._contracts.hitl import (
    ApprovalDecision,
    ApprovalRequest,
    DecisionType,
    HITLPolicy,
    RiskLevel,
)
from agent_harness._contracts.observability import TraceContext
from agent_harness.hitl import HITLManager
from infrastructure.db.models.governance import Approval
from infrastructure.db.models.sessions import Session as SessionModel
from platform_layer.governance.hitl.state_machine import (
    ApprovalState,
    validate_transition,
)

# Type alias for the session factory accepted by DefaultHITLManager. We accept
# any callable returning an async-context-manager-yielding AsyncSession; tests
# pass a factory that wraps an AsyncSession created from the test engine.
SessionFactory = Callable[[], Any]


class DefaultHITLManager(HITLManager):
    """Production HITL manager backed by `approvals` table.

    Args:
        session_factory: callable returning an async context manager that yields
            an `AsyncSession`. Tests can pass a partial bound to the test engine.
        notifier: optional HITLNotifier (Day 3 / US-6); if provided, called
            best-effort after request_approval persistence succeeds.
        default_expiry_seconds: default approval TTL (4 hours per 17.md §5).
        default_policy: optional HITLPolicy returned by get_policy() when no
            tenant-specific policy is loaded; tests pass a minimal policy.
        wait_poll_interval_s: poll interval for wait_for_decision (default 1s).
    """

    def __init__(
        self,
        *,
        session_factory: SessionFactory,
        notifier: Callable[[ApprovalRequest], Awaitable[None]] | None = None,
        default_expiry_seconds: int = 14400,
        default_policy: HITLPolicy | None = None,
        wait_poll_interval_s: float = 1.0,
    ) -> None:
        self._session_factory = session_factory
        self._notifier = notifier
        self._default_expiry_seconds = default_expiry_seconds
        self._default_policy = default_policy
        self._wait_poll_interval_s = wait_poll_interval_s

    # ---------------- request_approval ----------------

    async def request_approval(
        self,
        req: ApprovalRequest,
        *,
        trace_context: TraceContext | None = None,
    ) -> UUID:
        """Persist new approval request; trigger notifier best-effort."""
        async with self._session_factory() as session:
            row = Approval(
                id=req.request_id,
                session_id=req.session_id,
                action_type=req.requester,
                action_summary=req.payload.get("summary", req.requester),
                action_payload=req.payload,
                risk_level=req.risk_level.value.lower(),
                status=ApprovalState.PENDING.value,
                created_at=datetime.now(timezone.utc),
                expires_at=req.sla_deadline,
            )
            session.add(row)
            await session.commit()

        if self._notifier is not None:
            try:
                await self._notifier(req)
            except Exception:  # noqa: BLE001 — best-effort notify; failure must not block
                pass
        return req.request_id

    # ---------------- decide ----------------

    async def decide(
        self,
        *,
        request_id: UUID,
        decision: ApprovalDecision,
        trace_context: TraceContext | None = None,
    ) -> None:
        """Apply decision; validate state machine transition; persist."""
        target_state = self._decision_to_state(decision.decision)
        async with self._session_factory() as session:
            row = await session.get(Approval, request_id)
            if row is None:
                raise LookupError(f"approval not found: {request_id}")

            current_state = ApprovalState(row.status)
            validate_transition(current_state, target_state)

            row.status = target_state.value
            row.decision_reason = decision.reason
            row.decided_at = decision.decided_at
            await session.commit()

    @staticmethod
    def _decision_to_state(decision_type: DecisionType) -> ApprovalState:
        return {
            DecisionType.APPROVED: ApprovalState.APPROVED,
            DecisionType.REJECTED: ApprovalState.REJECTED,
            DecisionType.ESCALATED: ApprovalState.ESCALATED,
        }[decision_type]

    # ---------------- get_pending (multi-instance safe) ----------------

    async def get_pending(
        self,
        tenant_id: UUID,
        *,
        trace_context: TraceContext | None = None,
    ) -> list[ApprovalRequest]:
        """Return pending approvals for a tenant via session JOIN.

        Uses SELECT ... FOR UPDATE SKIP LOCKED so multiple worker instances can
        each pick up a disjoint batch without conflicting.
        """
        async with self._session_factory() as session:
            stmt = (
                select(Approval, SessionModel.tenant_id)
                .join(SessionModel, Approval.session_id == SessionModel.id)
                .where(
                    SessionModel.tenant_id == tenant_id,
                    Approval.status == ApprovalState.PENDING.value,
                )
                .with_for_update(skip_locked=True)
            )
            rows = (await session.execute(stmt)).all()

            return [self._approval_row_to_request(row[0], row[1]) for row in rows]

    @staticmethod
    def _approval_row_to_request(row: Approval, tenant_id: UUID) -> ApprovalRequest:
        return ApprovalRequest(
            request_id=row.id,
            tenant_id=tenant_id,
            session_id=row.session_id,
            requester=row.action_type,
            risk_level=RiskLevel[str(row.risk_level).upper()],
            payload=dict(row.action_payload or {}),
            sla_deadline=row.expires_at or datetime.now(timezone.utc),
            context_snapshot={},  # not persisted in approvals table
        )

    # ---------------- wait_for_decision ----------------

    async def wait_for_decision(
        self,
        request_id: UUID,
        *,
        timeout_s: int,
        trace_context: TraceContext | None = None,
    ) -> ApprovalDecision:
        """Poll DB until decision available or timeout."""
        deadline = datetime.now(timezone.utc) + timedelta(seconds=timeout_s)
        while datetime.now(timezone.utc) < deadline:
            async with self._session_factory() as session:
                row = await session.get(Approval, request_id)
                if row is None:
                    raise LookupError(f"approval not found: {request_id}")
                if row.status != ApprovalState.PENDING.value:
                    return ApprovalDecision(
                        request_id=row.id,
                        decision=self._state_to_decision(ApprovalState(row.status)),
                        reviewer=str(row.approver_user_id or "system"),
                        decided_at=row.decided_at or datetime.now(timezone.utc),
                        reason=row.decision_reason,
                    )
            await asyncio.sleep(self._wait_poll_interval_s)
        raise TimeoutError(f"approval {request_id} not decided within {timeout_s}s")

    @staticmethod
    def _state_to_decision(state: ApprovalState) -> DecisionType:
        return {
            ApprovalState.APPROVED: DecisionType.APPROVED,
            ApprovalState.REJECTED: DecisionType.REJECTED,
            ApprovalState.ESCALATED: DecisionType.ESCALATED,
            ApprovalState.EXPIRED: DecisionType.REJECTED,  # fallback for expired
        }[state]

    # ---------------- get_policy ----------------

    async def get_policy(
        self,
        tenant_id: UUID,
        *,
        trace_context: TraceContext | None = None,
    ) -> HITLPolicy:
        """Return per-tenant HITL policy.

        Day 2 scope: returns default_policy supplied at construction time.
        Day 3+ may extend with DB-stored per-tenant overrides.
        """
        if self._default_policy is not None:
            return self._default_policy
        return HITLPolicy(
            tenant_id=tenant_id,
            auto_approve_max_risk=RiskLevel.LOW,
            require_approval_min_risk=RiskLevel.MEDIUM,
        )

    # ---------------- expire_overdue (background sweep) ----------------

    async def expire_overdue(
        self,
        *,
        trace_context: TraceContext | None = None,
    ) -> int:
        """Background scan: pending + expires_at < NOW() → expired.

        Returns count of records updated. Invoked by background worker.
        """
        async with self._session_factory() as session:
            now = datetime.now(timezone.utc)
            stmt = (
                update(Approval)
                .where(
                    Approval.status == ApprovalState.PENDING.value,
                    Approval.expires_at < now,
                )
                .values(status=ApprovalState.EXPIRED.value, decided_at=now)
            )
            result = await session.execute(stmt)
            await session.commit()
            return int(result.rowcount or 0)

    # ---------------- escalate (helper, not in ABC) ----------------

    async def escalate(
        self,
        *,
        request_id: UUID,
        new_role: str,
        reason: str | None = None,
        trace_context: TraceContext | None = None,
    ) -> UUID:
        """Mark current approval ESCALATED + create fresh PENDING for higher tier.

        Returns the new pending request_id.
        """
        # Step 1: terminate current request
        await self.decide(
            request_id=request_id,
            decision=ApprovalDecision(
                request_id=request_id,
                decision=DecisionType.ESCALATED,
                reviewer="system:escalate",
                decided_at=datetime.now(timezone.utc),
                reason=reason,
            ),
            trace_context=trace_context,
        )

        # Step 2: create new pending under higher role
        async with self._session_factory() as session:
            old = await session.get(Approval, request_id)
            if old is None:
                raise LookupError(f"approval not found for escalation: {request_id}")

            new_id = uuid4()
            new_row = Approval(
                id=new_id,
                session_id=old.session_id,
                action_type=old.action_type,
                action_summary=old.action_summary,
                action_payload=dict(old.action_payload or {}),
                risk_level=old.risk_level,
                status=ApprovalState.PENDING.value,
                required_approver_role=new_role,
                created_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc)
                + timedelta(seconds=self._default_expiry_seconds),
            )
            session.add(new_row)
            await session.commit()
            return new_id
