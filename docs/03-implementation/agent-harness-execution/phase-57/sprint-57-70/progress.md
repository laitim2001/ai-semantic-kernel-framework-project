# Sprint 57.70 Progress — Real Per-Tenant Agent-Spec Catalog + Admin CRUD API (backend slice; FE → 57.71)

**Plan**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-70-plan.md`
**Checklist**: `.../sprint-57-70-checklist.md`
**Branch**: `feature/sprint-57-70-agent-catalog` (from main `3090e8b7`)

---

## Day 0 — 2026-06-02 — Plan-vs-Repo Verify + Reframe + Branch

### Scope selection (AskUserQuestion 2026-06-02)
- After 57.69 closed, the user picked the A-3b carryover item **real per-tenant agent catalog** for 57.70, then **+ Admin CRUD API + FE page** for scope.

### Three-prong Day-0 verify — drift D1-D7 (3 researcher rounds; reframed the plan)

The original plan (committed `ba3e7086`) assumed a NEW generic `agent_catalog` table + a NEW "Manage-Agents" FE page. Day-0 found the real shape:

- **D1** — the "agent catalog" IS the existing **Subagent Registry of AgentSpec definitions** (mockup `page-agents.jsx:311-438` `SubagentsRegistry`, faithful 57.38 port; fields role/model/system_prompt/allowed_modes/status + 4 detail tabs AgentSpec/Budget/Tools/Stats); 09-schema **Group 9 Subagent** is the home; `AgentSpec` (`_contracts/subagent.py:74-86`) is the in-code shape.
- **D2** — the `/subagents` FE page ALREADY EXISTS (`SubagentsPage.tsx` + `features/subagents/*`), a faithful mockup port (57.20+) but **read-only fixture** (4 detail tabs `defaultValue`/`readOnly`, zero CRUD). → making it real = moderate-to-large FE → **deferred to 57.71**.
- **D3** — the existing `GET /api/v1/subagents` is a **STUB about INVOCATIONS** (`subagents.py:67,95-121`; empty + `not_implemented_reason`; `SubagentItem` = invocation shape), a DIFFERENT concept from AgentSpec definitions (`AD-Subagent-RealList-Phase58`). → the definitions CRUD is a NEW endpoint; the invocations STUB is untouched.
- **D4** — NO registry table (33-table scan); next migration `0023`. → CREATE `agent_catalog` (per-tenant + RLS).
- **D5** — `resolve_persona` sync + global; 2 consumers (`service.py:131` boot_handoff resolves before txn / `handler.py:405` resolve_session_persona, both async). → make async + tenant-scoped; preserve None=reject / DEMO-fallback.
- **D6** — per-tenant must be added (existing surface global; tenant param `noqa`-unused). → table tenant_id + RLS + repo filter.
- **D7** — conventions confirmed (TenantScopedMixin / RLS 2-policy+FORCE `0019` / repo `session_repository` / admin CRUD `admin/tenants.py` / no real seed mechanism → 0023 data-migration + hardcoded fallback).

### go/no-go = **GO (plan REVISED + user re-confirmed)**
- >20% drift (FE-target + field-set + invocations-vs-definitions). Per the Day-0 rule, plan REVISED (not silently — §0 documents the drift; original framing preserved in MHist) + re-confirmed with user via AskUserQuestion → **backend registry + CRUD API this sprint; FE → 57.71**. Plan + checklist rewritten to the refined scope.

### Decisions
- catalog = AgentSpec registry (Group 9, fields per mockup); table `agent_catalog` (per-tenant, RLS); resolver = DB→DEFAULT_AGENTS→None (empty still works, no lazy-write); seed = 0023 data-migration + hardcoded fallback; CRUD = admin (`/admin/.../agents`, distinct from invocations STUB); default chat persona stays DEMO; budget/tools/modes STORED not enforced (§9); **FE → 57.71**.
- **Agent-delegated: yes** — Stage-1a backend (table + migration + repo + resolver rewire + seed); Stage-1b (admin CRUD API + integration). Parent independently re-verifies each stage (57.64+ discipline).

---

## Day 1 — 2026-06-02 — Stage-1a backend (agent-delegated + parent re-verify)

`code-implementer` agent built the catalog foundation; parent independently re-verified (read diffs + ran gates).

- **Changes**: `agent_catalog.py` (NEW, `AgentCatalog(Base, TenantScopedMixin)`, Group 9, meta_data→physical "metadata", UNIQUE(tenant_id,key)); `0023_agent_catalog` (create + RLS 2-policy+FORCE mirror 0019 + data-seed 3 defaults per existing tenant); `agent_catalog_repository.py` (async, tenant-scoped CRUD); `persona_registry.py` (`PERSONA_REGISTRY`→`DEFAULT_AGENTS` + async `resolve_persona(db, tenant_id, key)` DB→defaults→None with DB-error fail-safe + sync `resolve_default_persona`); `service.py`/`handler.py` await rewire; `09-db-schema-design §Group 9` documented.
- **Tests**: repo (9, DB-backed) + resolver (DB-hit/miss/unknown/inactive/error) + updated 57.68/69 tests for the async signature + integration (+2 override/fallback).
- **Parent re-verify (independent, read all contract-critical files)**: resolver correct (DB→DEFAULT_AGENTS→None + fail-safe); service/handler rewire preserves None=reject / DEMO-fallback; ORM alias + UNIQUE correct; migration RLS 2-policy+FORCE + seed `"metadata"`-quoted correct. `mypy src/` 0/328; 54 targeted pass; `run_all.py` 10/10; migration up/down vs live Postgres (7599 rows). Commit `8395e8b6`.

## Day 2 — 2026-06-02 — Stage-1b admin CRUD API (agent-delegated + parent re-verify)

`code-implementer` agent built the admin CRUD; parent independently re-verified.

- **Changes**: `api/v1/admin/agents.py` (NEW, separate router prefix `/admin/tenants`; GET list [`require_tenant_match_or_platform_admin`] + POST [201] + PUT + DELETE [204], writes `require_admin_platform_role`; Pydantic Create(extra=forbid)/Update(partial)/Response; 409 IntegrityError+rollback; 404 tenant-scoped; `append_audit` + commit); registered in `main.py`; conftest `AGENT_PUT_%` cleanup sweep. `/subagents` invocations STUB untouched.
- **Tests**: `test_admin_agent_catalog_api.py` (15: CRUD + 409 + 403 no-admin + 401 + 3 cross-tenant + audit).
- **Parent re-verify (independent)**: router mirrors admin/tenants.py; auth split (read tenant-match / write platform-admin) sensible; 409/404/audit correct; distinct from invocations STUB. `mypy src/` 0/329; admin test 15 pass.

## Day 3 — 2026-06-02 — Full sweep + edge (decisive re-verify)

- **Full backend sweep**: `pytest tests/unit tests/integration` → **2049 passed / 4 skipped / 0 failed** in 95s (= 57.69 baseline 2015 + Stage-1a/1b new + resolver-signature updates; no regression).
- **Edge** (covered): empty catalog → defaults; inactive → fallback; cross-tenant reject; unknown key → None reject; DB-error → fallback; override (tenant row beats default).
- **Decisive totals**: pytest 2049; mypy src 0/329; run_all 10/10; black 603 unchanged + isort/flake8 0; Alembic 0023 up/down (Stage-1a); Vitest unchanged (no FE).
- No drift beyond Day-0 D1-D7 (reframe). Commit `190a4946`.

## Day 4 — 2026-06-02 — Closeout

- CHANGE-038; `09-db-schema-design §Group 9` (Day 1); retrospective.md (Q1-Q7, no design note — feature-continuation); calibration-log §3.
- Final verify: black 603 unchanged + isort/flake8 0 + mypy 0/329 + run_all 10/10 (AD-Final-Commit-Black-Check).
- MEMORY.md pointer + subfile + CLAUDE.md lean. Carryover (plan §9): FE `/subagents` wiring → 57.71; allowed_modes/budget/tools loop-enforcement; AD-Subagent-RealList-Phase58; default chat persona from catalog; provisioning seed; tenant self-service.
