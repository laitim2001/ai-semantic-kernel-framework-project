"""
File: backend/tests/integration/platform_layer/governance/hitl/test_per_tenant_policy.py
Purpose: AD-Hitl-7 closure — DefaultHITLManager + DBHITLPolicyStore integration.
Category: Tests / Platform / Governance / HITL
Scope: Sprint 55.3 Day 3

Description:
    Integration tests verifying:
    - 2 tenants with distinct DB policies → manager.get_policy differentiates
    - tenant with no row → falls back to default_policy supplied at construction
    - tenant with no row + no default_policy → hardcoded LOW/MEDIUM fallback

    Mirrors test_manager.py fixture pattern (db_session + commit→flush
    monkeypatch + factory async ctx mgr).

Created: 2026-05-04 (Sprint 55.3)
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from agent_harness._contracts.hitl import HITLPolicy, RiskLevel
from infrastructure.db.models.governance import HitlPolicyRow
from platform_layer.governance.hitl.manager import DefaultHITLManager
from platform_layer.governance.hitl.policy_store import DBHITLPolicyStore
from tests.conftest import seed_tenant

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def manager_setup(db_session: AsyncSession, monkeypatch):
    """Build DefaultHITLManager wired to DBHITLPolicyStore using the test session.

    Returns (manager_with_store, manager_with_default, manager_no_overrides,
             tenant_a, tenant_b, tenant_c).

    - manager_with_store: full wire (policy_store + default_policy fallback)
    - manager_with_default: no policy_store, only default_policy
    - manager_no_overrides: neither policy_store nor default_policy → hardcoded fallback
    """
    tenant_a = await seed_tenant(db_session, code="HITL_PT_A")
    tenant_b = await seed_tenant(db_session, code="HITL_PT_B")
    tenant_c = await seed_tenant(db_session, code="HITL_PT_C")

    async def _flush_only() -> None:
        await db_session.flush()

    monkeypatch.setattr(db_session, "commit", _flush_only)

    @asynccontextmanager
    async def factory():
        yield db_session

    store = DBHITLPolicyStore(session_factory=factory)

    # Default fallback policy (used when DB has no row).
    default_pol = HITLPolicy(
        tenant_id=tenant_a.id,  # placeholder; consumer's tenant_id is what matters
        auto_approve_max_risk=RiskLevel.MEDIUM,
        require_approval_min_risk=RiskLevel.HIGH,
        reviewer_groups_by_risk={RiskLevel.HIGH: ["fallback_reviewers"]},
        sla_seconds_by_risk={},
    )

    manager_with_store = DefaultHITLManager(
        session_factory=factory,
        default_policy=default_pol,
        policy_store=store,
        wait_poll_interval_s=0.05,
    )
    manager_with_default = DefaultHITLManager(
        session_factory=factory,
        default_policy=default_pol,
        wait_poll_interval_s=0.05,
    )
    manager_no_overrides = DefaultHITLManager(
        session_factory=factory,
        wait_poll_interval_s=0.05,
    )
    return (
        manager_with_store,
        manager_with_default,
        manager_no_overrides,
        tenant_a,
        tenant_b,
        tenant_c,
    )


async def test_per_tenant_db_policy_differentiates(manager_setup, db_session) -> None:
    """2 tenants with distinct DB rows → manager.get_policy returns each."""
    manager_with_store, _, _, tenant_a, tenant_b, _ = manager_setup

    db_session.add(
        HitlPolicyRow(
            tenant_id=tenant_a.id,
            auto_approve_max_risk="LOW",
            require_approval_min_risk="MEDIUM",
            reviewer_groups_by_risk={"MEDIUM": ["team_a"]},
        )
    )
    db_session.add(
        HitlPolicyRow(
            tenant_id=tenant_b.id,
            auto_approve_max_risk="HIGH",
            require_approval_min_risk="CRITICAL",
            reviewer_groups_by_risk={"CRITICAL": ["team_b_critical"]},
        )
    )
    await db_session.flush()

    pol_a = await manager_with_store.get_policy(tenant_a.id)
    pol_b = await manager_with_store.get_policy(tenant_b.id)

    assert pol_a.auto_approve_max_risk == RiskLevel.LOW
    assert pol_a.require_approval_min_risk == RiskLevel.MEDIUM
    assert pol_a.reviewer_groups_by_risk == {RiskLevel.MEDIUM: ["team_a"]}
    assert pol_b.auto_approve_max_risk == RiskLevel.HIGH
    assert pol_b.require_approval_min_risk == RiskLevel.CRITICAL
    assert pol_b.reviewer_groups_by_risk == {RiskLevel.CRITICAL: ["team_b_critical"]}


async def test_no_db_row_falls_back_to_default_policy(manager_setup) -> None:
    """tenant_c has no DB row → falls back to default_policy."""
    manager_with_store, _, _, _, _, tenant_c = manager_setup
    pol = await manager_with_store.get_policy(tenant_c.id)
    # Falls to default_policy (MEDIUM / HIGH per fixture)
    assert pol.auto_approve_max_risk == RiskLevel.MEDIUM
    assert pol.require_approval_min_risk == RiskLevel.HIGH
    assert pol.reviewer_groups_by_risk == {RiskLevel.HIGH: ["fallback_reviewers"]}


async def test_no_policy_store_uses_default_policy(manager_setup) -> None:
    """Manager wired without policy_store → uses default_policy directly."""
    _, manager_with_default, _, tenant_a, _, _ = manager_setup
    pol = await manager_with_default.get_policy(tenant_a.id)
    assert pol.auto_approve_max_risk == RiskLevel.MEDIUM
    assert pol.require_approval_min_risk == RiskLevel.HIGH


async def test_no_overrides_falls_back_to_hardcoded(manager_setup) -> None:
    """No policy_store + no default_policy → hardcoded LOW/MEDIUM minimal."""
    _, _, manager_no_overrides, tenant_a, _, _ = manager_setup
    pol = await manager_no_overrides.get_policy(tenant_a.id)
    assert pol.tenant_id == tenant_a.id
    assert pol.auto_approve_max_risk == RiskLevel.LOW
    assert pol.require_approval_min_risk == RiskLevel.MEDIUM
    assert pol.reviewer_groups_by_risk == {}
    assert pol.sla_seconds_by_risk == {}
