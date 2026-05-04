"""
File: backend/tests/unit/platform_layer/governance/hitl/test_db_hitl_policy_store.py
Purpose: AD-Hitl-7 closure — DBHITLPolicyStore unit tests.
Category: Tests / Platform / Governance / HITL
Scope: Sprint 55.3 Day 3

Description:
    Unit-level tests for DBHITLPolicyStore. Uses the shared db_session fixture
    + monkeypatch session.commit → flush so the outer rollback unwinds writes
    (mirrors test_manager.py pattern from Sprint 53.4).

Created: 2026-05-04 (Sprint 55.3)
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from agent_harness._contracts.hitl import HITLPolicy, RiskLevel
from infrastructure.db.models.governance import HitlPolicyRow
from platform_layer.governance.hitl.policy_store import DBHITLPolicyStore
from tests.conftest import seed_tenant

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def store_setup(db_session: AsyncSession, monkeypatch):
    """Seed 2 tenants + build DBHITLPolicyStore using the test session.

    Returns (store, tenant_a, tenant_b).
    """
    tenant_a = await seed_tenant(db_session, code="POL_A")
    tenant_b = await seed_tenant(db_session, code="POL_B")

    # Match test_manager.py pattern: route commits through flush so outer rollback unwinds.
    async def _flush_only() -> None:
        await db_session.flush()

    monkeypatch.setattr(db_session, "commit", _flush_only)

    @asynccontextmanager
    async def factory():
        yield db_session

    store = DBHITLPolicyStore(session_factory=factory)
    return store, tenant_a, tenant_b


async def test_get_returns_none_when_no_row(store_setup) -> None:
    """Empty hitl_policies table → get(tenant_id) returns None."""
    store, tenant_a, _ = store_setup
    policy = await store.get(tenant_a.id)
    assert policy is None


async def test_get_returns_policy_when_row_exists(store_setup, db_session) -> None:
    """Insert sample row → get returns matching HITLPolicy."""
    store, tenant_a, _ = store_setup

    db_session.add(
        HitlPolicyRow(
            tenant_id=tenant_a.id,
            auto_approve_max_risk="MEDIUM",
            require_approval_min_risk="HIGH",
            reviewer_groups_by_risk={"HIGH": ["sec_team", "compliance"]},
            sla_seconds_by_risk={"HIGH": 3600, "CRITICAL": 1800},
        )
    )
    await db_session.flush()

    policy = await store.get(tenant_a.id)
    assert policy is not None
    assert isinstance(policy, HITLPolicy)
    assert policy.tenant_id == tenant_a.id
    assert policy.auto_approve_max_risk == RiskLevel.MEDIUM
    assert policy.require_approval_min_risk == RiskLevel.HIGH
    assert policy.reviewer_groups_by_risk == {RiskLevel.HIGH: ["sec_team", "compliance"]}
    assert policy.sla_seconds_by_risk == {RiskLevel.HIGH: 3600, RiskLevel.CRITICAL: 1800}


async def test_get_differentiates_per_tenant(store_setup, db_session) -> None:
    """2 tenants with distinct policies → get returns each tenant's policy."""
    store, tenant_a, tenant_b = store_setup

    db_session.add(
        HitlPolicyRow(
            tenant_id=tenant_a.id,
            auto_approve_max_risk="LOW",
            require_approval_min_risk="MEDIUM",
        )
    )
    db_session.add(
        HitlPolicyRow(
            tenant_id=tenant_b.id,
            auto_approve_max_risk="MEDIUM",
            require_approval_min_risk="HIGH",
        )
    )
    await db_session.flush()

    pol_a = await store.get(tenant_a.id)
    pol_b = await store.get(tenant_b.id)
    assert pol_a is not None and pol_b is not None
    assert pol_a.auto_approve_max_risk == RiskLevel.LOW
    assert pol_b.auto_approve_max_risk == RiskLevel.MEDIUM
    assert pol_a.require_approval_min_risk == RiskLevel.MEDIUM
    assert pol_b.require_approval_min_risk == RiskLevel.HIGH


async def test_hydrate_empty_jsonb_dicts(store_setup, db_session) -> None:
    """Empty JSONB defaults → empty dict[RiskLevel, ...] (no KeyError)."""
    store, tenant_a, _ = store_setup

    db_session.add(
        HitlPolicyRow(
            tenant_id=tenant_a.id,
            auto_approve_max_risk="LOW",
            require_approval_min_risk="MEDIUM",
            # leave reviewer_groups_by_risk + sla_seconds_by_risk to default '{}'
        )
    )
    await db_session.flush()

    policy = await store.get(tenant_a.id)
    assert policy is not None
    assert policy.reviewer_groups_by_risk == {}
    assert policy.sla_seconds_by_risk == {}


async def test_hydrate_skips_unknown_risk_keys(store_setup, db_session) -> None:
    """JSONB dict with unknown RiskLevel keys → silently skipped (resilient)."""
    store, tenant_a, _ = store_setup

    db_session.add(
        HitlPolicyRow(
            tenant_id=tenant_a.id,
            auto_approve_max_risk="LOW",
            require_approval_min_risk="MEDIUM",
            reviewer_groups_by_risk={"HIGH": ["sec"], "BOGUS_LEVEL": ["x"]},
        )
    )
    await db_session.flush()

    policy = await store.get(tenant_a.id)
    assert policy is not None
    # Only known RiskLevel keys hydrated
    assert policy.reviewer_groups_by_risk == {RiskLevel.HIGH: ["sec"]}
