"""
File: backend/src/platform_layer/governance/hitl/manager.py
Purpose: DefaultHITLManager — concrete HITLManager implementation backed by
         existing `approvals` table (Sprint 49.3 schema).
Category: Platform / Governance / HITL
Scope: Phase 53 / Sprint 53.4 US-2

Description:
    Day 1 scope: skeleton with NotImplementedError stubs + dependency injection
    structure. Day 2 will fill in real SQL / state-machine / multi-instance
    pickup logic.

    The existing `approvals` table from Sprint 49.3 (per 09-db-schema-design.md)
    already provides all needed columns:
        id, session_id, action_type, action_summary, action_payload,
        risk_level, risk_score, risk_reasoning, required_approver_role,
        approver_user_id, status, decision_reason, teams_notification_sent,
        teams_message_id, created_at, expires_at, decided_at

    Tenant isolation: via session_id → sessions.tenant_id chain.
    State machine: see state_machine.py (pending → approved/rejected/escalated/expired).

Key Components:
    - DefaultHITLManager: subclass of agent_harness.hitl.HITLManager (ABC)
    - Day 1 stubs raise NotImplementedError; Day 2 implements

Created: 2026-05-03 (Sprint 53.4 Day 1)
Last Modified: 2026-05-03

Modification History:
    - 2026-05-03: Initial skeleton (Sprint 53.4 Day 1) — Day 2 to implement

Related:
    - agent_harness/hitl/_abc.py (HITLManager ABC)
    - agent_harness/_contracts/hitl.py (Single-source types)
    - 17-cross-category-interfaces.md §5
    - 09-db-schema-design.md §approvals
    - sprint-53-4-plan.md §US-2
"""

from __future__ import annotations

from uuid import UUID

from agent_harness._contracts.hitl import (
    ApprovalDecision,
    ApprovalRequest,
    HITLPolicy,
)
from agent_harness._contracts.observability import TraceContext
from agent_harness.hitl._abc import HITLManager


class DefaultHITLManager(HITLManager):
    """Production HITL manager backed by `approvals` table.

    Day 1 status: skeleton with stub methods (Day 2 to implement).
    """

    def __init__(
        self,
        *,
        session_factory: object,  # async sessionmaker; precise type added Day 2
        notifier: object | None = None,  # HITLNotifier (Day 3)
        default_expiry_seconds: int = 14400,  # 4 hours
    ) -> None:
        self._session_factory = session_factory
        self._notifier = notifier
        self._default_expiry_seconds = default_expiry_seconds

    async def request_approval(
        self,
        req: ApprovalRequest,
        *,
        trace_context: TraceContext | None = None,
    ) -> UUID:
        """Persist new approval request; trigger notifier if configured.

        Day 2: implement INSERT into approvals + emit notifier.notify().
        """
        raise NotImplementedError("Sprint 53.4 Day 2: implement DB write + notifier hook")

    async def wait_for_decision(
        self,
        request_id: UUID,
        *,
        timeout_s: int,
        trace_context: TraceContext | None = None,
    ) -> ApprovalDecision:
        """Block until decision is available or timeout expires.

        Day 2: implement polling/notify loop with state-machine validation.
        """
        raise NotImplementedError("Sprint 53.4 Day 2: implement wait loop")

    async def get_pending(
        self,
        tenant_id: UUID,
        *,
        trace_context: TraceContext | None = None,
    ) -> list[ApprovalRequest]:
        """Return pending approvals for a tenant (multi-instance pickup uses
        SELECT ... FOR UPDATE SKIP LOCKED to coordinate).

        Day 2: implement query with tenant filter via session join.
        """
        raise NotImplementedError("Sprint 53.4 Day 2: implement pending query")

    async def decide(
        self,
        *,
        request_id: UUID,
        decision: ApprovalDecision,
        trace_context: TraceContext | None = None,
    ) -> None:
        """Apply decision; validate state transition; persist.

        Day 2: implement state-machine validation + UPDATE.
        """
        raise NotImplementedError("Sprint 53.4 Day 2: implement decide flow")

    async def get_policy(
        self,
        tenant_id: UUID,
        *,
        trace_context: TraceContext | None = None,
    ) -> HITLPolicy:
        """Return per-tenant HITLPolicy (loaded from config + DB overrides).

        Day 2: implement policy retrieval (default + per-tenant overlay).
        """
        raise NotImplementedError("Sprint 53.4 Day 2: implement policy retrieval")

    async def expire_overdue(
        self,
        *,
        trace_context: TraceContext | None = None,
    ) -> int:
        """Background scan: pending + expires_at < NOW() → expired.

        Returns count of records expired. Not in ABC; convenience method
        invoked by background worker (Day 2).
        """
        raise NotImplementedError("Sprint 53.4 Day 2: implement expiry sweep")
