# CHANGE-038: Real Per-Tenant Agent-Spec Catalog (DB-backed) + Admin CRUD API (backend slice)

**Date**: 2026-06-02
**Sprint**: 57.70
**Scope**: Cat 11 (Subagent AgentSpec registry + HANDOFF persona resolution) + platform-layer catalog + DB (Alembic 0023, per-tenant RLS table, Group 9) + API (admin CRUD)

## What Changed

Replaced the hardcoded 3-entry persona stand-in (`persona_registry.py`, Sprint 57.68) with a real DB-backed per-tenant agent-spec catalog — the persistent backing for Cat 11 HANDOFF persona resolution (and, in 57.71, the `/subagents` Subagent Registry page). Backend-only this slice (FE → 57.71).

1. **Table** — `agent_catalog` (`infrastructure/db/models/agent_catalog.py`, `Base + TenantScopedMixin`, 09-schema Group 9): `key/name/model/system_prompt/allowed_modes(JSONB)/status` + `meta_data` JSONB (physical `"metadata"`; budget+tools) + `is_active`; `UNIQUE(tenant_id, key)`. Alembic `0023_agent_catalog` (create + RLS 2 policies + FORCE, mirror 0019) + a data-migration seeding the 3 defaults per existing tenant (7599 rows = 2533 tenants × 3).
2. **Repository** — `AgentCatalogRepository` (async, tenant-scoped CRUD).
3. **Resolver** — `persona_registry.py`: `PERSONA_REGISTRY` → `DEFAULT_AGENTS`; async `resolve_persona(db, tenant_id, key)` = DB active row → `DEFAULT_AGENTS` → `None` (DB-error fail-safe to defaults); sync `resolve_default_persona`. Rewired into `HandoffService.boot_handoff` (None→reject) + `handler.resolve_session_persona` (None→DEMO) — the contract is preserved (an empty catalog still resolves the 3 defaults).
4. **Admin CRUD API** — `api/v1/admin/agents.py`: `GET/POST /admin/tenants/{tenant_id}/agents` + `PUT/DELETE /{agent_id}`; `require_admin_platform_role` (writes) + `require_tenant_match_or_platform_admin` (read); Pydantic; `append_audit`; 409 on dup key; 404 tenant-scoped. Distinct from the `/subagents` invocations STUB (untouched — `AD-Subagent-RealList-Phase58`).

## Why

`18-handoff-design.md §5` listed "real agent/persona catalog" as A-3b carryover. A Day-0 reality drift found the "agent catalog" = the existing Subagent Registry of AgentSpec definitions (mockup `page-agents.jsx` + 09-schema Group 9 + a read-only fixture `/subagents` page); the user re-confirmed scope as **backend registry + CRUD API this sprint, FE wiring → 57.71**.

## Verification

- Backend: full `pytest tests/unit tests/integration` → **2049 passed / 4 skipped / 0 failed**; `mypy src/` 0/329; `run_all.py` 10/10 (`check_rls_policies` + `check_llm_sdk_leak` green); black 603 unchanged. New: repo (9, DB-backed) + resolver (DB-hit/miss/unknown/inactive/error) + `test_admin_agent_catalog_api.py` (15: CRUD + 409 + 403 + 401 + 3 cross-tenant) + integration handoff-from-DB (+2 override/fallback) + updated 57.68/69 tests for the async signature. Migration verified up/down vs live Postgres.
- Multi-tenant: RLS (2 policies + FORCE) + repo tenant-filter; tenant A's agents invisible to B (asserted).

## Impact

- Backend: additive (new table/repo/API; resolver sync→async — 2 consumers rewired, both already async). No FE change. No new wire-type / codegen. No `agent_harness/**` edit (resolver in platform-layer). The `/subagents` invocations STUB untouched.
- Deferred (plan §9): FE `/subagents` wiring (57.71); allowed_modes/budget/tools loop-enforcement; default chat persona from catalog; provisioning-step seeding; tenant self-service.

## Related

- `sprint-57-70-plan.md` / `-checklist.md` / `agent-harness-execution/phase-57/sprint-57-70/{progress,retrospective}.md`
- `09-db-schema-design.md §Group 9` (agent_catalog documented)
- Predecessor: CHANGE-037 (57.69); the catalog replaces the 57.68 persona stand-in
