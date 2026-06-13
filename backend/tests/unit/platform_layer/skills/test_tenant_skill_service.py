"""
File: backend/tests/unit/platform_layer/skills/test_tenant_skill_service.py
Purpose: TenantSkillService CRUD unit tests (Sprint 57.114 / US-2).
Category: Tests / Unit (platform_layer.skills — Skills System per-tenant catalog)
Created: 2026-06-13 (Sprint 57.114)

Covers the service against the real docker-compose Postgres (db_session, rolled
back at teardown): create/list/update/delete round-trip, name ordering, duplicate
(create + update name-clash) → DuplicateSkillError, update/delete miss →
SkillNotFoundError, and tenant-scoped list (service-level scoping). The raw RLS
isolation (cross-tenant 404) is covered at the HTTP layer in
tests/integration/api/test_admin_tenant_skills.py (per test_rbac.py convention —
unit tests assert app-level scoping, integration tests exercise RLS).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from platform_layer.skills.service import (
    DuplicateSkillError,
    SkillNotFoundError,
    TenantSkillService,
)
from tests.conftest import seed_tenant


async def test_create_list_update_delete_roundtrip(db_session: AsyncSession) -> None:
    svc = TenantSkillService()
    tenant = await seed_tenant(db_session, code="SK_CRUD")
    created = await svc.create(
        db_session,
        tenant_id=tenant.id,
        name="release-notes",
        description="Turn a changelog into a release note",
        instructions="Body here",
    )
    assert created.id is not None
    rows = await svc.list_skills(db_session, tenant_id=tenant.id)
    assert [r.name for r in rows] == ["release-notes"]

    updated = await svc.update(
        db_session, tenant_id=tenant.id, skill_id=created.id, description="New description"
    )
    assert updated.description == "New description"
    assert updated.name == "release-notes"  # unchanged

    await svc.delete(db_session, tenant_id=tenant.id, skill_id=created.id)
    assert await svc.list_skills(db_session, tenant_id=tenant.id) == []


async def test_list_is_name_ordered(db_session: AsyncSession) -> None:
    svc = TenantSkillService()
    tenant = await seed_tenant(db_session, code="SK_ORDER")
    await svc.create(
        db_session, tenant_id=tenant.id, name="zeta", description="d", instructions="i"
    )
    await svc.create(
        db_session, tenant_id=tenant.id, name="alpha", description="d", instructions="i"
    )
    rows = await svc.list_skills(db_session, tenant_id=tenant.id)
    assert [r.name for r in rows] == ["alpha", "zeta"]


async def test_create_duplicate_name_raises(db_session: AsyncSession) -> None:
    svc = TenantSkillService()
    tenant = await seed_tenant(db_session, code="SK_DUP")
    await svc.create(db_session, tenant_id=tenant.id, name="dup", description="d", instructions="i")
    with pytest.raises(DuplicateSkillError):
        await svc.create(
            db_session, tenant_id=tenant.id, name="dup", description="d2", instructions="i2"
        )


async def test_update_name_clash_raises(db_session: AsyncSession) -> None:
    svc = TenantSkillService()
    tenant = await seed_tenant(db_session, code="SK_CLASH")
    a = await svc.create(
        db_session, tenant_id=tenant.id, name="a", description="d", instructions="i"
    )
    await svc.create(db_session, tenant_id=tenant.id, name="b", description="d", instructions="i")
    with pytest.raises(DuplicateSkillError):
        await svc.update(db_session, tenant_id=tenant.id, skill_id=a.id, name="b")


async def test_update_missing_raises(db_session: AsyncSession) -> None:
    svc = TenantSkillService()
    tenant = await seed_tenant(db_session, code="SK_UPD_MISS")
    with pytest.raises(SkillNotFoundError):
        await svc.update(db_session, tenant_id=tenant.id, skill_id=uuid4(), name="x")


async def test_delete_missing_raises(db_session: AsyncSession) -> None:
    svc = TenantSkillService()
    tenant = await seed_tenant(db_session, code="SK_DEL_MISS")
    with pytest.raises(SkillNotFoundError):
        await svc.delete(db_session, tenant_id=tenant.id, skill_id=uuid4())


async def test_cross_tenant_scoping(db_session: AsyncSession) -> None:
    """list_skills is scoped by tenant_id (raw RLS denial is covered in integration)."""
    svc = TenantSkillService()
    tenant_a = await seed_tenant(db_session, code="SK_ISO_A")
    tenant_b = await seed_tenant(db_session, code="SK_ISO_B")
    await svc.create(
        db_session, tenant_id=tenant_a.id, name="a-secret", description="d", instructions="i"
    )
    assert await svc.list_skills(db_session, tenant_id=tenant_b.id) == []
    a_rows = await svc.list_skills(db_session, tenant_id=tenant_a.id)
    assert [r.name for r in a_rows] == ["a-secret"]
