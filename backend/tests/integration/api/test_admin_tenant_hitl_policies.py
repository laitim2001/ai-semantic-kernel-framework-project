"""
File: backend/tests/integration/api/test_admin_tenant_hitl_policies.py
Purpose: Integration tests — GET /admin/tenants/{tenant_id}/hitl-policies (Sprint 57.48 Track A).
Category: Tests / Integration / API (Phase 58+ Backend Schema Extension wave)
Scope: Sprint 57.48 Day 1 Track A (closes AD-TenantSettings-HITLPolicies-Backend)

Description:
    Verifies the GET /admin/tenants/{tenant_id}/hitl-policies endpoint:
    - 401 when no JWT context
    - 404 when tenant not found
    - 200 empty list when no per-tenant HITL policy row exists (fallback path)
    - 200 with projected items when a per-tenant HitlPolicyRow exists
    - Response shape: items + total + limit + offset; items carry
      risk/policy/sla_seconds/reviewers
    - Multi-tenant isolation: tenant B's policy does NOT leak into tenant A's
      response
    - Pagination (limit + offset)

Created: 2026-05-26 (Sprint 57.48 Day 1)

Modification History (newest-first):
    - 2026-05-26: Sprint 57.54 — add 12 PUT tests (Track A — upsert + 422 + iso + idemp)
    - 2026-05-26: Initial creation (Sprint 57.48 Day 1 Track A — HITLPolicies admin GET)
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, Request, Response
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.admin.tenants import router as admin_tenants_router
from infrastructure.db.models.governance import HitlPolicyRow
from infrastructure.db.models.identity import Tenant, TenantPlan, TenantState
from infrastructure.db.session import get_db_session
from platform_layer.identity.auth import require_admin_platform_role

pytestmark = pytest.mark.asyncio


def _build_app(db_session: AsyncSession | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(admin_tenants_router, prefix="/api/v1")

    @app.middleware("http")
    async def _populate_test_state(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        user_header = request.headers.get("X-Test-User")
        roles_header = request.headers.get("X-Test-Roles")
        tenant_header = request.headers.get("X-Test-Tenant")
        request.state.user_id = UUID(user_header) if user_header else None
        request.state.roles = json.loads(roles_header) if roles_header else None
        request.state.tenant_id = UUID(tenant_header) if tenant_header else None
        return await call_next(request)

    if db_session is not None:

        async def _override_session() -> AsyncIterator[AsyncSession]:
            yield db_session

        async def _override_admin() -> UUID:
            return UUID("00000000-0000-0000-0000-000000000001")

        app.dependency_overrides[get_db_session] = _override_session
        app.dependency_overrides[require_admin_platform_role] = _override_admin

    return app


async def _seed_tenant(session: AsyncSession, *, code: str) -> Tenant:
    t = Tenant(
        code=code,
        display_name=f"Tenant {code}",
        state=TenantState.ACTIVE,
        plan=TenantPlan.ENTERPRISE,
    )
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t


async def _seed_hitl_policy(
    session: AsyncSession,
    *,
    tenant: Tenant,
    auto_approve_max_risk: str = "LOW",
    require_approval_min_risk: str = "MEDIUM",
    reviewer_groups_by_risk: dict[str, list[str]] | None = None,
    sla_seconds_by_risk: dict[str, int] | None = None,
) -> HitlPolicyRow:
    row = HitlPolicyRow(
        tenant_id=tenant.id,
        auto_approve_max_risk=auto_approve_max_risk,
        require_approval_min_risk=require_approval_min_risk,
        reviewer_groups_by_risk=reviewer_groups_by_risk or {"HIGH": ["@platform-l2"]},
        sla_seconds_by_risk=sla_seconds_by_risk or {"HIGH": 900, "MEDIUM": 3600},
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def test_list_hitl_policies_401_without_auth() -> None:
    app = _build_app()
    tenant_id = uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/admin/tenants/{tenant_id}/hitl-policies")
    assert resp.status_code == 401


async def test_list_hitl_policies_404_when_tenant_not_found(db_session: AsyncSession) -> None:
    app = _build_app(db_session=db_session)
    missing_id = uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/admin/tenants/{missing_id}/hitl-policies")
    assert resp.status_code == 404


async def test_list_hitl_policies_empty_when_no_row(db_session: AsyncSession) -> None:
    """Tenant with no per-tenant HitlPolicyRow → empty list (frontend falls back to fixture)."""
    tenant = await _seed_tenant(db_session, code="HITL_EMPTY_T1")
    app = _build_app(db_session=db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/admin/tenants/{tenant.id}/hitl-policies")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


async def test_list_hitl_policies_happy_path_projects_4_risks(db_session: AsyncSession) -> None:
    """Per-tenant HitlPolicyRow exists → 4 items (one per RiskLevel)."""
    tenant = await _seed_tenant(db_session, code="HITL_HAPPY_T1")
    await _seed_hitl_policy(db_session, tenant=tenant)

    app = _build_app(db_session=db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/admin/tenants/{tenant.id}/hitl-policies")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 4
    assert len(body["items"]) == 4
    risks = {item["risk"] for item in body["items"]}
    assert risks == {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


async def test_list_hitl_policies_response_shape(db_session: AsyncSession) -> None:
    """Each item exposes risk + policy + sla_seconds + reviewers."""
    tenant = await _seed_tenant(db_session, code="HITL_SHAPE_T1")
    await _seed_hitl_policy(db_session, tenant=tenant)

    app = _build_app(db_session=db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/admin/tenants/{tenant.id}/hitl-policies")
    assert resp.status_code == 200, resp.text
    item = resp.json()["items"][0]
    expected = {"risk", "policy", "sla_seconds", "reviewers"}
    assert expected.issubset(set(item.keys()))


async def test_list_hitl_policies_tenant_isolation(db_session: AsyncSession) -> None:
    """Tenant A's policy must NOT appear in tenant B's response."""
    tenant_a = await _seed_tenant(db_session, code="HITL_ISO_A")
    tenant_b = await _seed_tenant(db_session, code="HITL_ISO_B")
    await _seed_hitl_policy(
        db_session,
        tenant=tenant_a,
        reviewer_groups_by_risk={"HIGH": ["@team-A"]},
    )
    # tenant_b has NO row → empty projection

    app = _build_app(db_session=db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp_a = await ac.get(f"/api/v1/admin/tenants/{tenant_a.id}/hitl-policies")
        resp_b = await ac.get(f"/api/v1/admin/tenants/{tenant_b.id}/hitl-policies")

    assert resp_a.status_code == 200 and resp_b.status_code == 200
    body_a = resp_a.json()
    body_b = resp_b.json()
    assert body_a["total"] == 4
    assert body_b["total"] == 0
    # tenant_a's reviewers contain "@team-A" for HIGH risk; tenant_b empty
    a_high = next(item for item in body_a["items"] if item["risk"] == "HIGH")
    assert "@team-A" in a_high["reviewers"]


async def test_list_hitl_policies_pagination(db_session: AsyncSession) -> None:
    """limit=2 + offset=2 returns the second slice of the 4-row projection."""
    tenant = await _seed_tenant(db_session, code="HITL_PAGE_T1")
    await _seed_hitl_policy(db_session, tenant=tenant)

    app = _build_app(db_session=db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        page1 = await ac.get(f"/api/v1/admin/tenants/{tenant.id}/hitl-policies?limit=2&offset=0")
        page2 = await ac.get(f"/api/v1/admin/tenants/{tenant.id}/hitl-policies?limit=2&offset=2")
    assert page1.status_code == 200 and page2.status_code == 200
    body1 = page1.json()
    body2 = page2.json()
    assert body1["total"] == 4 and body2["total"] == 4
    assert len(body1["items"]) == 2
    assert len(body2["items"]) == 2
    risks1 = {item["risk"] for item in body1["items"]}
    risks2 = {item["risk"] for item in body2["items"]}
    assert risks1.isdisjoint(risks2)


# =====================================================================
# Sprint 57.54 Track A — PUT /{tenant_id}/hitl-policies upsert tests
# =====================================================================
# IMPORTANT: PUT tests call DBHITLPolicyStore.put() which commits via the
# shared test session. To avoid "duplicate key" cross-test leakage on the
# unique tenants.code, each PUT test seeds its tenant with a uuid4-suffixed
# code (mirrors Sprint 57.51-53 §Committed-Row Cleanup pattern at file scope).


def _unique_code(prefix: str) -> str:
    """Return a unique tenant code suffix to survive committed-row leakage."""
    return f"{prefix}_{uuid4().hex[:8]}"


def _valid_put_payload(
    *,
    auto_approve_max_risk: str = "LOW",
    require_approval_min_risk: str = "MEDIUM",
    reviewer_groups_by_risk: dict[str, list[str]] | None = None,
    sla_seconds_by_risk: dict[str, int] | None = None,
) -> dict[str, object]:
    return {
        "auto_approve_max_risk": auto_approve_max_risk,
        "require_approval_min_risk": require_approval_min_risk,
        "reviewer_groups_by_risk": (
            reviewer_groups_by_risk
            if reviewer_groups_by_risk is not None
            else {"HIGH": ["@platform-l2"]}
        ),
        "sla_seconds_by_risk": (
            sla_seconds_by_risk
            if sla_seconds_by_risk is not None
            else {"HIGH": 900, "MEDIUM": 3600}
        ),
    }


async def test_put_requires_admin_role() -> None:
    """No JWT context → 401 from require_admin_platform_role."""
    app = _build_app()
    tenant_id = uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.put(
            f"/api/v1/admin/tenants/{tenant_id}/hitl-policies",
            json=_valid_put_payload(),
        )
    assert resp.status_code in (401, 403)


async def test_put_tenant_not_found(db_session: AsyncSession) -> None:
    """Nonexistent tenant_id → 404 via _load_tenant_or_404."""
    app = _build_app(db_session=db_session)
    missing_id = uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.put(
            f"/api/v1/admin/tenants/{missing_id}/hitl-policies",
            json=_valid_put_payload(),
        )
    assert resp.status_code == 404


async def test_put_creates_new_row(db_session: AsyncSession) -> None:
    """No prior HitlPolicyRow → PUT creates row; response has saved+items."""
    tenant = await _seed_tenant(db_session, code=_unique_code("HITL_PUT_CREATE"))
    app = _build_app(db_session=db_session)
    payload = _valid_put_payload(
        auto_approve_max_risk="LOW",
        require_approval_min_risk="HIGH",
        reviewer_groups_by_risk={"HIGH": ["@team-create"]},
        sla_seconds_by_risk={"HIGH": 1800},
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.put(f"/api/v1/admin/tenants/{tenant.id}/hitl-policies", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["saved_policy"]["auto_approve_max_risk"] == "LOW"
    assert body["saved_policy"]["require_approval_min_risk"] == "HIGH"
    assert len(body["items"]) == 4
    # Verify persistence via direct ORM query
    row = (
        await db_session.execute(select(HitlPolicyRow).where(HitlPolicyRow.tenant_id == tenant.id))
    ).scalar_one()
    assert row.auto_approve_max_risk == "LOW"
    assert row.require_approval_min_risk == "HIGH"
    assert row.reviewer_groups_by_risk == {"HIGH": ["@team-create"]}


async def test_put_updates_existing_row(db_session: AsyncSession) -> None:
    """Pre-seeded HitlPolicyRow → PUT updates content (upsert ON CONFLICT path)."""
    tenant = await _seed_tenant(db_session, code=_unique_code("HITL_PUT_UPDATE"))
    await _seed_hitl_policy(
        db_session,
        tenant=tenant,
        auto_approve_max_risk="LOW",
        require_approval_min_risk="MEDIUM",
        reviewer_groups_by_risk={"HIGH": ["@old-team"]},
        sla_seconds_by_risk={"HIGH": 900},
    )
    app = _build_app(db_session=db_session)
    payload = _valid_put_payload(
        auto_approve_max_risk="MEDIUM",
        require_approval_min_risk="CRITICAL",
        reviewer_groups_by_risk={"CRITICAL": ["@new-team"]},
        sla_seconds_by_risk={"CRITICAL": 60},
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.put(f"/api/v1/admin/tenants/{tenant.id}/hitl-policies", json=payload)
    assert resp.status_code == 200, resp.text
    # Verify update via direct ORM query
    row = (
        await db_session.execute(select(HitlPolicyRow).where(HitlPolicyRow.tenant_id == tenant.id))
    ).scalar_one()
    assert row.auto_approve_max_risk == "MEDIUM"
    assert row.require_approval_min_risk == "CRITICAL"
    assert row.reviewer_groups_by_risk == {"CRITICAL": ["@new-team"]}
    assert row.sla_seconds_by_risk == {"CRITICAL": 60}


async def test_put_response_projects_items_matching_get(db_session: AsyncSession) -> None:
    """PUT then GET return identical projected items."""
    tenant = await _seed_tenant(db_session, code=_unique_code("HITL_PUT_PROJECT"))
    app = _build_app(db_session=db_session)
    payload = _valid_put_payload(
        auto_approve_max_risk="LOW",
        require_approval_min_risk="HIGH",
        reviewer_groups_by_risk={"HIGH": ["@team-proj"]},
        sla_seconds_by_risk={"HIGH": 1200, "MEDIUM": 600},
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        put_resp = await ac.put(f"/api/v1/admin/tenants/{tenant.id}/hitl-policies", json=payload)
        get_resp = await ac.get(f"/api/v1/admin/tenants/{tenant.id}/hitl-policies")
    assert put_resp.status_code == 200, put_resp.text
    assert get_resp.status_code == 200, get_resp.text
    put_items = put_resp.json()["items"]
    get_items = get_resp.json()["items"]
    assert put_items == get_items


async def test_put_invalid_risk_level_auto_approve(db_session: AsyncSession) -> None:
    """auto_approve_max_risk='INVALID' → 422 via field_validator."""
    tenant = await _seed_tenant(db_session, code=_unique_code("HITL_PUT_BAD_AUTO"))
    app = _build_app(db_session=db_session)
    payload = _valid_put_payload(auto_approve_max_risk="INVALID")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.put(f"/api/v1/admin/tenants/{tenant.id}/hitl-policies", json=payload)
    assert resp.status_code == 422


async def test_put_invalid_risk_level_require_approval(db_session: AsyncSession) -> None:
    """require_approval_min_risk='BADLEVEL' → 422 via field_validator."""
    tenant = await _seed_tenant(db_session, code=_unique_code("HITL_PUT_BAD_REQ"))
    app = _build_app(db_session=db_session)
    payload = _valid_put_payload(require_approval_min_risk="BADLEVEL")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.put(f"/api/v1/admin/tenants/{tenant.id}/hitl-policies", json=payload)
    assert resp.status_code == 422


async def test_put_extra_field_rejected(db_session: AsyncSession) -> None:
    """Unknown field in payload → 422 via extra='forbid'."""
    tenant = await _seed_tenant(db_session, code=_unique_code("HITL_PUT_EXTRA"))
    app = _build_app(db_session=db_session)
    payload = _valid_put_payload()
    payload["unknown_field"] = "leak"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.put(f"/api/v1/admin/tenants/{tenant.id}/hitl-policies", json=payload)
    assert resp.status_code == 422


async def test_put_multi_tenant_isolation(db_session: AsyncSession) -> None:
    """PUT to tenant_b MUST NOT mutate tenant_a's row (multi-tenant rule)."""
    tenant_a = await _seed_tenant(db_session, code=_unique_code("HITL_PUT_ISO_A"))
    tenant_b = await _seed_tenant(db_session, code=_unique_code("HITL_PUT_ISO_B"))
    await _seed_hitl_policy(
        db_session,
        tenant=tenant_a,
        auto_approve_max_risk="LOW",
        require_approval_min_risk="MEDIUM",
        reviewer_groups_by_risk={"HIGH": ["@tenant-a-team"]},
        sla_seconds_by_risk={"HIGH": 500},
    )
    app = _build_app(db_session=db_session)
    payload_b = _valid_put_payload(
        auto_approve_max_risk="MEDIUM",
        require_approval_min_risk="CRITICAL",
        reviewer_groups_by_risk={"CRITICAL": ["@tenant-b-team"]},
        sla_seconds_by_risk={"CRITICAL": 60},
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp_b = await ac.put(f"/api/v1/admin/tenants/{tenant_b.id}/hitl-policies", json=payload_b)
    assert resp_b.status_code == 200, resp_b.text
    row_a = (
        await db_session.execute(
            select(HitlPolicyRow).where(HitlPolicyRow.tenant_id == tenant_a.id)
        )
    ).scalar_one()
    # tenant_a unchanged
    assert row_a.auto_approve_max_risk == "LOW"
    assert row_a.require_approval_min_risk == "MEDIUM"
    assert row_a.reviewer_groups_by_risk == {"HIGH": ["@tenant-a-team"]}
    # tenant_b has its own new row
    row_b = (
        await db_session.execute(
            select(HitlPolicyRow).where(HitlPolicyRow.tenant_id == tenant_b.id)
        )
    ).scalar_one()
    assert row_b.auto_approve_max_risk == "MEDIUM"
    assert row_b.reviewer_groups_by_risk == {"CRITICAL": ["@tenant-b-team"]}


async def test_put_idempotent_same_payload_twice(db_session: AsyncSession) -> None:
    """PUT same payload twice → both succeed; items projection identical."""
    tenant = await _seed_tenant(db_session, code=_unique_code("HITL_PUT_IDEMP"))
    app = _build_app(db_session=db_session)
    payload = _valid_put_payload(
        auto_approve_max_risk="LOW",
        require_approval_min_risk="HIGH",
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        first = await ac.put(f"/api/v1/admin/tenants/{tenant.id}/hitl-policies", json=payload)
        second = await ac.put(f"/api/v1/admin/tenants/{tenant.id}/hitl-policies", json=payload)
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    # Items projection is deterministic on (saved_policy)
    assert first.json()["items"] == second.json()["items"]
    assert first.json()["saved_policy"] == second.json()["saved_policy"]


async def test_put_persists_to_db_via_subsequent_get(db_session: AsyncSession) -> None:
    """After PUT, GET on same tenant returns the projected items from the saved row."""
    tenant = await _seed_tenant(db_session, code=_unique_code("HITL_PUT_PERSIST"))
    app = _build_app(db_session=db_session)
    payload = _valid_put_payload(
        auto_approve_max_risk="MEDIUM",
        require_approval_min_risk="HIGH",
        reviewer_groups_by_risk={"HIGH": ["@persist-team"]},
        sla_seconds_by_risk={"HIGH": 450},
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        put_resp = await ac.put(f"/api/v1/admin/tenants/{tenant.id}/hitl-policies", json=payload)
        get_resp = await ac.get(f"/api/v1/admin/tenants/{tenant.id}/hitl-policies")
    assert put_resp.status_code == 200, put_resp.text
    assert get_resp.status_code == 200, get_resp.text
    body = get_resp.json()
    assert body["total"] == 4
    high = next(item for item in body["items"] if item["risk"] == "HIGH")
    assert "@persist-team" in high["reviewers"]
    assert high["sla_seconds"] == 450


async def test_put_empty_reviewer_groups_and_sla(db_session: AsyncSession) -> None:
    """Empty dicts for reviewer_groups/sla → accepted; defaults work."""
    tenant = await _seed_tenant(db_session, code=_unique_code("HITL_PUT_EMPTY"))
    app = _build_app(db_session=db_session)
    payload = _valid_put_payload(
        reviewer_groups_by_risk={},
        sla_seconds_by_risk={},
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.put(f"/api/v1/admin/tenants/{tenant.id}/hitl-policies", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["saved_policy"]["reviewer_groups_by_risk"] == {}
    assert body["saved_policy"]["sla_seconds_by_risk"] == {}
    # All 4 items present with empty reviewers / None sla
    assert len(body["items"]) == 4
    for item in body["items"]:
        assert item["reviewers"] == ""
        assert item["sla_seconds"] is None
