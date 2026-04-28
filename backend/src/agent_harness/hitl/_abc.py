"""
File: backend/src/agent_harness/hitl/_abc.py
Purpose: HITL Centralization ABC — HITLManager.
Category: §HITL Centralization (per 17.md §5)
Scope: Phase 49 / Sprint 49.1 (stub; impl in Phase 53.3)

Description:
    HITL was scattered across categories 2 / 7 / 8 / 9 in V1. V2
    centralizes all HITL via HITLManager. Categories 2 (tools) and 9
    (guardrails) call request_approval(); category 7 (state) stores
    pending_approval_ids in DurableState; category 8 (errors) treats
    HITL as recoverable wait.

Owner: 01-eleven-categories-spec.md §HITL Centralization
Single-source: 17.md §5

Created: 2026-04-29 (Sprint 49.1)
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
