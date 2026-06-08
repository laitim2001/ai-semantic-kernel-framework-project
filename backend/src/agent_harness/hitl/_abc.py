"""
File: backend/src/agent_harness/hitl/_abc.py
Purpose: HITL Centralization ABCs — HITLManager + HITLPolicyStore.
Category: §HITL Centralization (per 17.md §5)
Scope: Phase 49 / Sprint 49.1 (HITLManager); Sprint 55.3 (HITLPolicyStore — AD-Hitl-7)

Description:
    HITL was scattered across categories 2 / 7 / 8 / 9 in V1. V2
    centralizes all HITL via HITLManager. Categories 2 (tools) and 9
    (guardrails) call request_approval(); category 7 (state) stores
    pending_approval_ids in DurableState; category 8 (errors) treats
    HITL as recoverable wait.

    HITLPolicyStore (Sprint 55.3 / AD-Hitl-7) is a separate abstraction
    for per-tenant HITLPolicy retrieval; DefaultHITLManager.get_policy()
    delegates to it when supplied (DB-backed) or falls back to default.

Owner: 01-eleven-categories-spec.md §HITL Centralization
Single-source: 17.md §5

Modification History:
    - 2026-06-08: Sprint 57.88 US-3 — add non-blocking get_decision() to HITLManager
    - 2026-05-04: Sprint 55.3 — add HITLPolicyStore ABC (closes AD-Hitl-7)
    - 2026-04-29: Initial creation (Sprint 49.1)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from agent_harness._contracts import (
    ApprovalDecision,
    ApprovalRequest,
    HITLPolicy,
    TraceContext,
)


class HITLPolicyStore(ABC):
    """Per-tenant HITLPolicy retrieval ABC. Sprint 55.3 / AD-Hitl-7.

    Implementations (DBHITLPolicyStore, future: file-backed / in-memory)
    return the policy for a tenant or None if no override row exists.
    DefaultHITLManager wraps the result with default-policy fallback.
    """

    @abstractmethod
    async def get(self, tenant_id: UUID) -> HITLPolicy | None:
        """Return per-tenant policy; None if no override exists."""
        ...


class HITLManager(ABC):
    """Central HITL coordinator. Single source of HITL behavior."""

    @abstractmethod
    async def request_approval(
        self,
        req: ApprovalRequest,
        *,
        trace_context: TraceContext | None = None,
    ) -> UUID:
        """Submit approval request. Returns request_id."""
        ...

    @abstractmethod
    async def wait_for_decision(
        self,
        request_id: UUID,
        *,
        timeout_s: int,
        trace_context: TraceContext | None = None,
    ) -> ApprovalDecision: ...

    @abstractmethod
    async def get_decision(
        self,
        request_id: UUID,
        *,
        trace_context: TraceContext | None = None,
    ) -> ApprovalDecision | None:
        """Non-blocking single read of a recorded decision (Sprint 57.88 US-3).

        Unlike ``wait_for_decision`` (which polls until decided or times out),
        this returns immediately: ``None`` if the request is still PENDING (or
        not found), else the ``ApprovalDecision``. Used by ``AgentLoop.resume()``
        to check a deferred approval that the human already decided hours/days
        earlier — no blocking, the connection was released at pause time.
        """
        ...

    @abstractmethod
    async def get_pending(
        self,
        tenant_id: UUID,
        *,
        trace_context: TraceContext | None = None,
    ) -> list[ApprovalRequest]: ...

    @abstractmethod
    async def decide(
        self,
        *,
        request_id: UUID,
        decision: ApprovalDecision,
        trace_context: TraceContext | None = None,
    ) -> None: ...

    @abstractmethod
    async def get_policy(
        self,
        tenant_id: UUID,
        *,
        trace_context: TraceContext | None = None,
    ) -> HITLPolicy: ...
