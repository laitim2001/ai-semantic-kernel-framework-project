"""
File: backend/src/platform_layer/governance/hitl/notifier.py
Purpose: HITLNotifier ABC — best-effort notification channel for pending approvals.
Category: Platform / Governance / HITL
Scope: Phase 53 / Sprint 53.4 US-6

Description:
    Notifiers are invoked by HITLManager.request_approval() AFTER the request
    is persisted. Failures must NOT block the HITL flow — caller wraps in
    try/except.

    Production deployments wire `TeamsWebhookNotifier` (default). Tests use
    `NoopNotifier` or a list-collector fake.

Created: 2026-05-03 (Sprint 53.4 Day 3)

Modification History:
    - 2026-05-03: Initial creation (Sprint 53.4 Day 3 US-6)

Related:
    - platform_layer/governance/hitl/manager.py
    - 17-cross-category-interfaces.md §5 (HITL centralization)
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from agent_harness._contracts.hitl import ApprovalRequest


class HITLNotifier(ABC):
    """ABC for HITL pending-request notification channels."""

    @abstractmethod
    async def notify(self, req: ApprovalRequest) -> None:
        """Best-effort notification; failures do not block HITL flow."""
        ...


class NoopNotifier(HITLNotifier):
    """No-op notifier (default for tests; production should wire a real one)."""

    async def notify(self, req: ApprovalRequest) -> None:
        return None
