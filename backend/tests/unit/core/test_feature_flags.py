"""FeatureFlagsService tests (Sprint 56.1 Day 3 / US-4)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.feature_flags import (
    DEFAULT_FLAGS,
    FeatureFlagNotFoundError,
    FeatureFlagsService,
)
from infrastructure.db.models.audit import AuditLog
from infrastructure.db.models.feature_flag import FeatureFlag
from tests.conftest import seed_tenant


@pytest.mark.asyncio
async def test_feature_flag_default_lookup(db_session: AsyncSession) -> None:
    """Flag without any tenant override → returns default_enabled."""
    db_session.add(FeatureFlag(name="thinking_enabled", default_enabled=True, tenant_overrides={}))
    await db_session.flush()

    svc = FeatureFlagsService(db_session)
    tenant_id = uuid4()
    assert await svc.is_enabled("thinking_enabled", tenant_id=tenant_id) is True


@pytest.mark.asyncio
async def test_feature_flag_tenant_override_takes_precedence(
    db_session: AsyncSession,
) -> None:
    """tenant_overrides[tenant_id] beats default_enabled for that tenant."""
    tenant_id = uuid4()
    db_session.add(
        FeatureFlag(
            name="thinking_enabled",
            default_enabled=True,
            tenant_overrides={str(tenant_id): False},
        )
    )
    await db_session.flush()

    svc = FeatureFlagsService(db_session)
    assert await svc.is_enabled("thinking_enabled", tenant_id=tenant_id) is False
    # Other tenants still see default.
    other_tenant = uuid4()
    assert await svc.is_enabled("thinking_enabled", tenant_id=other_tenant) is True


@pytest.mark.asyncio
async def test_feature_flag_set_override_writes_audit(db_session: AsyncSession) -> None:
    """set_tenant_override emits an audit_log row via append_audit chain."""
    tenant = await seed_tenant(db_session, code="ff-aud")
    db_session.add(FeatureFlag(name="pii_masking", default_enabled=True, tenant_overrides={}))
    await db_session.flush()

    svc = FeatureFlagsService(db_session)
    actor = uuid4()
    await svc.set_tenant_override(
        "pii_masking", tenant_id=tenant.id, enabled=False, actor_user_id=actor
    )

    audit_rows = (
        (
            await db_session.execute(
                select(AuditLog).where(AuditLog.operation == "feature_flag_override_set")
            )
        )
        .scalars()
        .all()
    )
    assert len(audit_rows) == 1
    row = audit_rows[0]
    assert row.tenant_id == tenant.id
    assert row.user_id == actor
    assert row.resource_type == "feature_flag"
    assert row.resource_id == "pii_masking"
    assert row.operation_data["new_value"] is False


@pytest.mark.asyncio
async def test_feature_flag_cache_invalidate_on_set(db_session: AsyncSession) -> None:
    """is_enabled cache must invalidate after set_tenant_override."""
    tenant = await seed_tenant(db_session, code="ff-cache")
    db_session.add(
        FeatureFlag(name="verification_enabled", default_enabled=True, tenant_overrides={})
    )
    await db_session.flush()

    svc = FeatureFlagsService(db_session)
    # Prime cache.
    assert await svc.is_enabled("verification_enabled", tenant_id=tenant.id) is True

    await svc.set_tenant_override(
        "verification_enabled",
        tenant_id=tenant.id,
        enabled=False,
        actor_user_id=None,
    )

    # Re-query should see the new override (cache invalidated).
    assert await svc.is_enabled("verification_enabled", tenant_id=tenant.id) is False


@pytest.mark.asyncio
async def test_feature_flag_seed_defaults_idempotent(db_session: AsyncSession) -> None:
    """seed_defaults inserts missing flags first run; second run is a no-op."""
    svc = FeatureFlagsService(db_session)
    inserted_first = await svc.seed_defaults()
    assert inserted_first == len(DEFAULT_FLAGS)

    inserted_second = await svc.seed_defaults()
    assert inserted_second == 0

    # All defaults present.
    rows = (
        (
            await db_session.execute(
                select(FeatureFlag).where(FeatureFlag.name.in_(list(DEFAULT_FLAGS.keys())))
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == len(DEFAULT_FLAGS)


@pytest.mark.asyncio
async def test_feature_flag_unknown_flag_raises(db_session: AsyncSession) -> None:
    """Unknown flag returns FeatureFlagNotFoundError, not silent False."""
    svc = FeatureFlagsService(db_session)
    with pytest.raises(FeatureFlagNotFoundError):
        await svc.is_enabled("not_a_real_flag", tenant_id=uuid4())
