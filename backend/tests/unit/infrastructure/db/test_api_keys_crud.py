"""
File: backend/tests/unit/infrastructure/db/test_api_keys_crud.py
Purpose: api_keys + rate_limits CRUD + status transitions + uniqueness.
Category: Tests / Infrastructure / DB / API auth schema
Scope: Sprint 49.3 Day 2.6

Tests:
    1. test_api_key_create_active   — baseline: insert active key
    2. test_api_key_lookup_by_hash  — find by key_hash for auth path
    3. test_api_key_revoke          — flip status; revoked_at filled
    4. test_api_key_expire_lookup   — partial-active idx excludes expired
    5. test_rate_limit_create_unique — UNIQUE(tenant,resource,window,start)

Created: 2026-04-29 (Sprint 49.3 Day 2.6)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import ApiKey, RateLimit
from tests.conftest import seed_tenant, seed_user


@pytest.mark.asyncio
async def test_api_key_create_active(db_session: AsyncSession) -> None:
    """Baseline: tenant can mint an active API key."""
    t = await seed_tenant(db_session, code="API_NEW")
    u = await seed_user(db_session, t, email="key_owner@api.test")

    k = ApiKey(
        tenant_id=t.id,
        name="prod-integration-key",
        key_prefix="ipa_abcd",
        key_hash="$2b$12$placeholder.bcrypt.hash.value.0123456789abcdef",
        permissions=["read:sessions", "write:tools"],
        rate_limit_tier="standard",
        created_by=u.id,
    )
    db_session.add(k)
    await db_session.flush()
    assert k.id is not None
    assert k.status == "active"
    assert k.revoked_at is None
    assert k.permissions == ["read:sessions", "write:tools"]


@pytest.mark.asyncio
async def test_api_key_lookup_by_hash(db_session: AsyncSession) -> None:
    """Auth path: find by key_hash → return tenant_id + permissions."""
    t = await seed_tenant(db_session, code="API_LKP")
    h = "$2b$12$lookup.hash.example.value.0987654321fedcba9876"
    k = ApiKey(
        tenant_id=t.id,
        name="lookup-key",
        key_prefix="ipa_lkup",
        key_hash=h,
        permissions=["read:*"],
    )
    db_session.add(k)
    await db_session.flush()

    result = await db_session.execute(select(ApiKey).where(ApiKey.key_hash == h))
    found = result.scalar_one()
    assert found.tenant_id == t.id
    assert found.permissions == ["read:*"]


@pytest.mark.asyncio
async def test_api_key_revoke(db_session: AsyncSession) -> None:
    """Revoke: flip status + populate revoked_at; partial-active idx excludes."""
    t = await seed_tenant(db_session, code="API_RVK")
    k = ApiKey(
        tenant_id=t.id,
        name="to-revoke",
        key_prefix="ipa_rvkd",
        key_hash="$2b$12$revoke.hash.example.value.aaaaaaaaaaaaaaaa",
    )
    db_session.add(k)
    await db_session.flush()

    revoked_at = datetime.now(timezone.utc)
    k.status = "revoked"
    k.revoked_at = revoked_at
    await db_session.flush()

    # idx_api_keys_active is partial WHERE status='active' — revoked rows
    # are simply outside the index; query by status still works.
    result = await db_session.execute(
        select(ApiKey).where((ApiKey.tenant_id == t.id) & (ApiKey.status == "active"))
    )
    assert result.scalar_one_or_none() is None
    assert k.status == "revoked"
    assert k.revoked_at is not None


@pytest.mark.asyncio
async def test_api_key_expire_lookup(db_session: AsyncSession) -> None:
    """Expired key: status remains 'active' until revocation job; lookup
    by (status='active' AND expires_at > now) reflects effective usability."""
    t = await seed_tenant(db_session, code="API_EXP")
    past = datetime.now(timezone.utc) - timedelta(days=1)
    k = ApiKey(
        tenant_id=t.id,
        name="already-expired",
        key_prefix="ipa_expd",
        key_hash="$2b$12$expired.hash.example.value.bbbbbbbbbbbbbbb",
        expires_at=past,
    )
    db_session.add(k)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    result = await db_session.execute(
        select(ApiKey).where(
            (ApiKey.tenant_id == t.id)
            & (ApiKey.status == "active")
            & (ApiKey.expires_at > now)
        )
    )
    assert result.scalar_one_or_none() is None  # expired → effective denied


@pytest.mark.asyncio
async def test_rate_limit_create_unique(db_session: AsyncSession) -> None:
    """UNIQUE(tenant_id, resource_type, window_type, window_start) enforced."""
    t = await seed_tenant(db_session, code="RL_UNIQ")
    win_start = datetime.now(timezone.utc).replace(microsecond=0, second=0)
    win_end = win_start + timedelta(minutes=1)

    rl = RateLimit(
        tenant_id=t.id,
        resource_type="llm_tokens",
        window_type="minute",
        quota=10000,
        used=0,
        window_start=win_start,
        window_end=win_end,
    )
    db_session.add(rl)
    await db_session.flush()
    assert rl.id is not None

    # Same key → IntegrityError
    dup = RateLimit(
        tenant_id=t.id,
        resource_type="llm_tokens",
        window_type="minute",
        quota=10000,
        used=5,
        window_start=win_start,
        window_end=win_end,
    )
    db_session.add(dup)
    with pytest.raises(IntegrityError):
        await db_session.flush()
