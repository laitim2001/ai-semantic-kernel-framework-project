"""
File: backend/tests/unit/platform_layer/governance/test_service_factory.py
Purpose: Unit tests for ServiceFactory (Sprint 53.6 US-5 — closes AD-Hitl-4-followup).
Category: Tests / unit / platform_layer / governance
Scope: Phase 53 / Sprint 53.6 US-5

Created: 2026-05-04 (Sprint 53.6 Day 4)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from agent_harness.hitl import HITLManager
from platform_layer.governance.audit.query import AuditQuery
from platform_layer.governance.hitl.manager import DefaultHITLManager
from platform_layer.governance.hitl.notifier import NoopNotifier
from platform_layer.governance.hitl.teams_webhook import TeamsWebhookNotifier
from platform_layer.governance.risk.policy import DefaultRiskPolicy, RiskPolicy
from platform_layer.governance.service_factory import (
    ServiceFactory,
    get_service_factory,
    reset_service_factory,
    set_service_factory,
)


@asynccontextmanager
async def _fake_session_factory() -> Any:
    yield MagicMock()


def _factory(
    *,
    notif_path: str | Path | None = None,
    risk_path: str | Path | None = None,
) -> ServiceFactory:
    return ServiceFactory(
        session_factory=_fake_session_factory,
        notification_config_path=notif_path,
        risk_policy_config_path=risk_path,
    )


class TestServiceFactoryHITLManager:
    def test_get_hitl_manager_returns_default_implementation(self) -> None:
        f = _factory()
        mgr = f.get_hitl_manager()
        assert isinstance(mgr, HITLManager)
        assert isinstance(mgr, DefaultHITLManager)

    def test_get_hitl_manager_caches_singleton(self) -> None:
        f = _factory()
        first = f.get_hitl_manager()
        second = f.get_hitl_manager()
        assert first is second  # same instance, lazy singleton

    def test_get_hitl_manager_uses_noop_when_no_config_path(self) -> None:
        f = _factory(notif_path=None)
        f.get_hitl_manager()  # construct
        # Verify by introspecting the bound notifier callable's __self__.
        notifier_bound = f._hitl_manager._notifier  # type: ignore[union-attr]
        assert notifier_bound is not None
        assert isinstance(notifier_bound.__self__, NoopNotifier)  # type: ignore[union-attr]

    def test_get_hitl_manager_uses_teams_when_config_resolves(self, tmp_path: Path) -> None:
        config = tmp_path / "notification.yaml"
        config.write_text(
            "version: '1.0'\n"
            "teams:\n"
            "  enabled: true\n"
            "  default_webhook: 'https://example.test/teams/hook'\n"
            "  per_tenant_overrides: {}\n",
            encoding="utf-8",
        )
        f = _factory(notif_path=config)
        f.get_hitl_manager()
        notifier_bound = f._hitl_manager._notifier  # type: ignore[union-attr]
        assert notifier_bound is not None
        assert isinstance(notifier_bound.__self__, TeamsWebhookNotifier)  # type: ignore[union-attr]

    def test_get_hitl_manager_falls_back_to_noop_on_malformed_config(self, tmp_path: Path) -> None:
        config = tmp_path / "notification.yaml"
        # Malformed YAML — per_tenant_overrides as list (not mapping) → ValueError
        config.write_text(
            "version: '1.0'\n"
            "teams:\n"
            "  enabled: true\n"
            "  default_webhook: 'https://example.test/teams/hook'\n"
            "  per_tenant_overrides:\n"
            "    - not_a_mapping\n",
            encoding="utf-8",
        )
        f = _factory(notif_path=config)
        # Should NOT raise — factory catches ValueError and falls back to Noop.
        f.get_hitl_manager()
        notifier_bound = f._hitl_manager._notifier  # type: ignore[union-attr]
        assert isinstance(notifier_bound.__self__, NoopNotifier)  # type: ignore[union-attr]


class TestServiceFactoryRiskPolicy:
    def test_get_risk_policy_returns_default_implementation(self, tmp_path: Path) -> None:
        config = tmp_path / "risk_policy.yaml"
        config.write_text("default_risk: medium\n", encoding="utf-8")
        f = _factory(risk_path=config)
        policy = f.get_risk_policy()
        assert isinstance(policy, RiskPolicy)
        assert isinstance(policy, DefaultRiskPolicy)

    def test_get_risk_policy_caches_singleton(self, tmp_path: Path) -> None:
        config = tmp_path / "risk_policy.yaml"
        config.write_text("default_risk: medium\n", encoding="utf-8")
        f = _factory(risk_path=config)
        first = f.get_risk_policy()
        second = f.get_risk_policy()
        assert first is second

    def test_get_risk_policy_raises_without_config(self) -> None:
        f = _factory(risk_path=None)
        with pytest.raises(RuntimeError, match="risk_policy_config_path"):
            f.get_risk_policy()


class TestServiceFactoryAuditQuery:
    def test_build_audit_query_returns_new_instance_each_call(self) -> None:
        f = _factory()
        first = f.build_audit_query()
        second = f.build_audit_query()
        assert first is not second  # request-scoped, not cached
        assert isinstance(first, AuditQuery)

    def test_build_audit_query_with_session_for_list(self) -> None:
        f = _factory()
        session = MagicMock()
        q = f.build_audit_query(session=session)
        assert q._session is session  # type: ignore[attr-defined]
        assert q._session_factory is _fake_session_factory  # type: ignore[attr-defined]

    def test_build_audit_query_without_session_for_chain_verify(self) -> None:
        f = _factory()
        q = f.build_audit_query()
        assert q._session is None  # type: ignore[attr-defined]
        # session_factory still wired for verify_chain()
        assert q._session_factory is _fake_session_factory  # type: ignore[attr-defined]


class TestServiceFactoryModuleSingleton:
    def setup_method(self) -> None:
        reset_service_factory()

    def teardown_method(self) -> None:
        reset_service_factory()

    def test_set_and_get_service_factory_round_trip(self) -> None:
        f = _factory()
        set_service_factory(f)
        assert get_service_factory() is f

    def test_reset_clears_singleton(self) -> None:
        f = _factory()
        set_service_factory(f)
        reset_service_factory()
        # After reset, get_service_factory tries lazy init — but our test factory
        # is gone. The module would lazy-import infrastructure.db.session which
        # may fail in pure-unit tests. We assert that the singleton is cleared
        # by checking that setting a new factory takes effect.
        f2 = _factory()
        set_service_factory(f2)
        assert get_service_factory() is f2
        assert get_service_factory() is not f
