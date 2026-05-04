"""
File: backend/src/platform_layer/governance/service_factory.py
Purpose: Centralized factory for governance services (HITL / Risk / Audit) — single
    construction site, lazy singletons for stateless services, per-request builder for
    stateful ones.
Category: 12 Cross-Cutting Governance / platform_layer
Scope: Phase 53 / Sprint 53.6 US-5 (closes AD-Hitl-4-followup)

Description:
    Sprint 53.4 + 53.5 left service construction scattered: governance/router.py
    built `DefaultHITLManager(...)` per-request via `_build_manager()`; api/v1/audit.py
    constructed `AuditQuery(...)` per-endpoint inline; chat/handler.py never wired
    `hitl_manager` at all (AD-Front-2 gap → production crash on Cat 9 detection).

    ServiceFactory consolidates these construction sites. Three patterns
    based on each service's lifetime semantics:

    - HITLManager: stateless wrapper over session_factory + notifier; safe to
      cache as process-level singleton. Notifier resolution (Teams webhook
      vs Noop) happens once at first access via load_notifier_from_config.
    - RiskPolicy: stateless YAML loader; cache as singleton.
    - AuditQuery: takes a request-bound session for list() OR uses session_factory
      for verify_chain(). Cannot cache — exposed as `build_audit_query(session=...)`.

    Tenant routing is HANDLED INTERNALLY by each service (HITLNotifier per-tenant
    override map; RiskPolicy.evaluate(tool_name, args, tenant_id)) — the factory
    itself stays tenant-agnostic. This avoids per-tenant cache complexity.

Key Components:
    - ServiceFactory: main class with `get_hitl_manager()` / `get_risk_policy()` /
      `build_audit_query(session?)`.
    - get_service_factory(): module-level lazy singleton accessor (process-scoped).
      FastAPI routers use this directly OR via Depends(get_service_factory).

Created: 2026-05-04 (Sprint 53.6 Day 4)

Modification History (newest-first):
    - 2026-05-04: Initial creation (Sprint 53.6 US-5) — closes AD-Hitl-4-followup.

Related:
    - .hitl.manager (DefaultHITLManager construction)
    - .hitl.notifier (load_notifier_from_config — Sprint 53.5 US-4 loader)
    - .audit.query (AuditQuery — Sprint 53.5 US-5 + US-6)
    - .risk.policy (DefaultRiskPolicy — Sprint 53.4 US-1)
    - api/v1/chat/handler.py (consumer — closes AD-Front-2 production wiring)
    - api/v1/governance/router.py (consumer — drops _build_manager)
    - api/v1/audit.py (consumer — drops inline AuditQuery construction)
"""

from __future__ import annotations

import logging
import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from agent_harness._contracts.hitl import ApprovalRequest
from agent_harness.hitl import HITLManager

from .audit.query import AuditQuery
from .hitl.manager import DefaultHITLManager
from .hitl.notifier import HITLNotifier, NoopNotifier, load_notifier_from_config
from .risk.policy import DefaultRiskPolicy, RiskPolicy

logger = logging.getLogger(__name__)

# Type aliases mirroring DefaultHITLManager signature for clarity.
SessionFactoryT = Callable[[], Any]
NotifierCallable = Callable[[ApprovalRequest], Awaitable[None]]


class ServiceFactory:
    """Centralized governance service construction with lazy singletons.

    Args:
        session_factory: async-context-manager factory yielding AsyncSession.
            Shared across all governance services.
        notification_config_path: optional path to notification.yaml (Sprint 53.5
            US-4). When None, defaults to NoopNotifier — no Teams notifications.
        risk_policy_config_path: optional path to risk_policy.yaml (Sprint 53.4
            US-1). When None, get_risk_policy() raises if called.

    Caching:
        - HITLManager: lazy singleton (constructed at first get_hitl_manager()).
        - RiskPolicy: lazy singleton (constructed at first get_risk_policy()).
        - AuditQuery: NOT cached (request-scoped session binding).

    Notifier resolution:
        Notifier is resolved ONCE at HITLManager construction. The notifier
        instance internally routes per-tenant (load_notifier_from_config returns
        a TeamsWebhookNotifier with per-tenant override map embedded; routing
        happens inside .notify(req) based on req.tenant_id). The factory does
        NOT need a tenant arg.
    """

    def __init__(
        self,
        *,
        session_factory: SessionFactoryT,
        notification_config_path: str | Path | None = None,
        risk_policy_config_path: str | Path | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._notification_config_path = notification_config_path
        self._risk_policy_config_path = risk_policy_config_path
        self._hitl_manager: HITLManager | None = None
        self._risk_policy: RiskPolicy | None = None

    # --- HITL ---------------------------------------------------------------

    def get_hitl_manager(self) -> HITLManager:
        """Return process-singleton HITLManager. Constructs on first access."""
        if self._hitl_manager is None:
            notifier = self._resolve_notifier()
            self._hitl_manager = DefaultHITLManager(
                session_factory=self._session_factory,
                notifier=notifier.notify,  # bind method → matches Callable signature
            )
            logger.info(
                "ServiceFactory: HITLManager constructed with notifier=%s",
                type(notifier).__name__,
            )
        return self._hitl_manager

    def _resolve_notifier(self) -> HITLNotifier:
        """Load notifier from notification.yaml; fall back to NoopNotifier."""
        if self._notification_config_path is None:
            logger.info("ServiceFactory: no notification_config_path; using NoopNotifier")
            return NoopNotifier()
        try:
            return load_notifier_from_config(self._notification_config_path)
        except (FileNotFoundError, ValueError) as exc:
            # load_notifier_from_config raises ValueError on malformed YAML; we
            # treat that as configuration failure but still fall back to Noop
            # so the platform stays up. Operators see the warning in logs.
            logger.warning(
                "ServiceFactory: notifier config load failed (%s); using NoopNotifier",
                exc,
            )
            return NoopNotifier()

    # --- Risk ---------------------------------------------------------------

    def get_risk_policy(self) -> RiskPolicy:
        """Return process-singleton RiskPolicy. Requires risk_policy_config_path."""
        if self._risk_policy is None:
            if self._risk_policy_config_path is None:
                raise RuntimeError(
                    "ServiceFactory: get_risk_policy() called without "
                    "risk_policy_config_path; configure ServiceFactory with the "
                    "risk_policy.yaml path."
                )
            self._risk_policy = DefaultRiskPolicy(self._risk_policy_config_path)
            logger.info(
                "ServiceFactory: RiskPolicy constructed from %s",
                self._risk_policy_config_path,
            )
        return self._risk_policy

    # --- Audit --------------------------------------------------------------

    def build_audit_query(self, *, session: AsyncSession | None = None) -> AuditQuery:
        """Build a per-request AuditQuery.

        - For `list()`: pass `session` bound to the current tenant.
        - For `verify_chain()`: omit `session`; AuditQuery uses self._session_factory
          for fresh-session paginated chain walks.
        """
        return AuditQuery(session=session, session_factory=self._session_factory)


# ---------------------------------------------------------------------------
# Module-level singleton accessor (used by FastAPI Depends).
# ---------------------------------------------------------------------------

_factory: ServiceFactory | None = None


def get_service_factory() -> ServiceFactory:
    """FastAPI dependency / module-level accessor returning the process-singleton.

    Lazy-initialized on first call. Reads paths from env (Sprint 53.6 US-4
    config wiring):
        NOTIFICATION_CONFIG_PATH (default: backend/config/notification.yaml)
        RISK_POLICY_CONFIG_PATH  (default: backend/config/risk_policy.yaml)

    Tests can override via `set_service_factory(test_factory)` then
    `reset_service_factory()` in teardown.
    """
    global _factory
    if _factory is None:
        from infrastructure.db import get_session_factory

        notif_path = os.environ.get("NOTIFICATION_CONFIG_PATH", "config/notification.yaml")
        risk_path = os.environ.get("RISK_POLICY_CONFIG_PATH", "config/risk_policy.yaml")
        # Coerce empty-string env override to None so that explicitly clearing the
        # env var disables loading (unit tests rely on this).
        _factory = ServiceFactory(
            session_factory=get_session_factory(),
            notification_config_path=notif_path or None,
            risk_policy_config_path=risk_path or None,
        )
    return _factory


def set_service_factory(factory: ServiceFactory | None) -> None:
    """Test-only override; pair with reset_service_factory in teardown."""
    global _factory
    _factory = factory


def reset_service_factory() -> None:
    """Test teardown — clears the cached factory so the next call re-initializes."""
    global _factory
    _factory = None
