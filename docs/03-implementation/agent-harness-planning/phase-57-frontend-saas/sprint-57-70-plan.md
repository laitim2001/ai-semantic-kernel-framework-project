# Sprint 57.70 Plan — Real Per-Tenant Agent-Spec Catalog (DB-backed) + Admin CRUD API (backend slice; FE → 57.71)

**Purpose**: Replace the hardcoded 3-entry persona stand-in (`platform_layer/handoff/persona_registry.py`, Sprint 57.68) with a **real DB-backed per-tenant agent-spec catalog** — the persistent backing for the Cat 11 **Subagent Registry of AgentSpec definitions** (the `/subagents` page concept) AND for HANDOFF persona resolution. This slice is **backend-only** (user-confirmed after a Day-0 reality drift — see §0): a new `agent_catalog` table (per-tenant, RLS, Group 9), an `AgentCatalogRepository`, async tenant-scoped persona resolution (rewiring `resolve_persona`'s two consumers while PRESERVING the `None`=reject / DEMO-fallback contract), the 3 default agents materialized per tenant (data migration + hardcoded fallback so an empty catalog still works), and an **admin CRUD API** for the AgentSpec definitions (distinct from the existing `/subagents` invocations STUB). Wiring the existing read-only `/subagents` FE page to this catalog (replace the fixture, editable detail tabs, create/edit/delete) is the **next sprint 57.71**. This is a **feature-continuation sprint** (it composes established patterns — per-tenant table + RLS + repository + admin CRUD — NOT a new mechanism), so **no design note** is required (per `sprint-workflow.md §Step 5.5`).
**Category / Scope**: Cat 11 (Subagent AgentSpec registry + HANDOFF persona resolution) + platform-layer agent catalog (service + repository) + DB (Alembic `0023`, new per-tenant RLS table, 09-schema Group 9) + API (admin CRUD of AgentSpec definitions) + governance (audit on mutations); Phase 57.70
**Created**: 2026-06-02
**Status**: Draft — **revised at Day-0** after a >20% reality drift (the "agent catalog" = the existing Subagent Registry of AgentSpec definitions; the `/subagents` FE page already exists as a read-only mockup-ported fixture; the existing `/subagents` GET is a separate invocations STUB; per-tenant must be added). User re-confirmed scope: **backend registry + CRUD API this sprint, FE → 57.71** (§0/§9). Code execution gated on Day-0 GO.
**Source**: A-3b carryover (design note `18-handoff-design.md §5`: "real agent/persona catalog") + **three-round Day-0 reality audit (3 codebase-researchers, 2026-06-02)** (persona/agent concept + `resolve_persona` consumers; per-tenant table + RLS + seed + admin CRUD conventions; existing `/subagents` full-stack map) + user AskUserQuestion decisions 2026-06-02 (next sprint = real per-tenant agent catalog → scope = +API+FE → **re-confirmed backend registry + CRUD API only, FE → 57.71**)

> **Modification History**
> - 2026-06-02: Day-0 revision — reframed to "agent-spec catalog backing the Subagent Registry" + scoped backend-only (FE → 57.71) after the existing-`/subagents`-stack discovery; was "generic agent_catalog + FE Manage-Agents page" (the FE-target + field-set + invocations-vs-definitions drift folded into §0)
> - 2026-06-02: Initial creation — DB-backed per-tenant agent catalog + admin CRUD API + FE page; feature-continuation (no design note)

---

## 0. Background

Sprint 57.68 (A-3b slice 1) introduced a **minimal hardcoded 3-entry persona stand-in** (`persona_registry.py`: `PERSONA_REGISTRY: dict[str, str]` = researcher/reviewer/planner; `resolve_persona(target_agent) -> str | None`, sync, global) — flagged as a thin stand-in (`18-handoff-design.md §5`: "a DB-backed per-tenant catalog is future work"). The user chose to build that catalog.

### ⚠️ Day-0 reality drift (>20% — reframed the plan; user re-confirmed; folded per `sprint-workflow.md §Step 2.5`)

The original plan assumed a NEW generic `agent_catalog` table + a NEW "Manage-Agents" FE page. Three researcher rounds found the real shape:

- **D1 — the "agent catalog" IS the existing Subagent Registry of AgentSpec definitions.** The mockup `reference/design-mockups/page-agents.jsx:311-438` (`SubagentsRegistry` + `SubagentDetail`, a faithful Sprint-57.38 port) defines the catalog UI: AgentSpec rows = `role`(immutable id)/`model`/`system_prompt`/`allowed modes`(fork/as_tool/teammate/handoff)/`status`(live/staging) + 4 detail tabs (AgentSpec / Budget[max_tokens/duration/concurrent/depth] / Tools / Stats). 09-schema **Group 9 Subagent (範疇 11)** is the home. → the catalog table fields align to this AgentSpec shape; `AgentSpec` (`_contracts/subagent.py:74-86`: role/prompt/model/metadata) is the in-code shape.
- **D2 — the `/subagents` FE page ALREADY EXISTS, read-only fixture.** `frontend/src/pages/subagents/SubagentsPage.tsx` (+ `features/subagents/{types.ts, services/subagentsService.ts, hooks/useSubagents.ts}`) is a faithful mockup port (57.20+) rendering `SUBAGENT_LIST` fixture; all 4 detail tabs are `defaultValue`/`readOnly`, ZERO CRUD wired; `useSubagents()` is called but real items never render the table (fixture-primary). → making this page real (replace fixture + editable tabs + create/edit/delete) is **moderate-to-large FE** → deferred to **57.71** (user-confirmed).
- **D3 — the existing `/api/v1/subagents` GET is a STUB about INVOCATIONS, not definitions.** `backend/src/api/v1/subagents.py:67,95-121`: one `GET /api/v1/subagents` returning `items=[]` + `not_implemented_reason`; its `SubagentItem` shape is runtime invocations (`invocation_id`/`mode`/`status`/tokens/timestamps), a DIFFERENT concept from AgentSpec definitions (tracked separately as `AD-Subagent-RealList-Phase58`). → this sprint does NOT touch the invocations STUB; the AgentSpec-definitions CRUD is a NEW endpoint.
- **D4 — NO registry table exists** (33-table `__tablename__` scan; closest is `sessions` + 57.68's `meta_data["agent_role"]`). Alembic head `0022` → next **`0023`**. → CREATE `agent_catalog` (per-tenant + RLS).
- **D5 — `resolve_persona` is SYNC + global; two consumers** — `service.py:131` (`boot_handoff`, async, resolves BEFORE the txn; `None` → `HandoffError`) + `handler.py:405` (`resolve_session_persona`, async; `None` → `DEMO_SYSTEM_PROMPT`). → make resolution **async + tenant-scoped**; both call sites already async. **Preserve the `None`=reject / DEMO-fallback contract.**
- **D6 — per-tenant must be ADDED.** The existing `/subagents` surface is global (tenant param `Depends(get_current_tenant)` wired but `noqa`-unused). The user wants per-tenant + multi-tenant 鐵律 → table `tenant_id` + RLS + repo filter.
- **D7 — conventions confirmed** — `TenantScopedMixin` (`base.py:51-78`); RLS = 2 policies + FORCE (`0019` template; `check_rls_policies` lint); repo template `session_repository.py`; admin CRUD template `admin/tenants.py` (`require_admin_platform_role`, Pydantic, `append_audit`, sub-resource `/admin/tenants/{id}/X`); no real per-tenant seed mechanism (provisioning stubs) → seed via `0023` data migration + hardcoded fallback.

**Net** (backend-only this slice): `agent_catalog` table (per-tenant, RLS, `0023`, Group 9; fields per mockup AgentSpec) + `AgentCatalogRepository` + an async tenant-scoped resolver (DB catalog → hardcoded `DEFAULT_AGENTS` → `None`), rewired into `boot_handoff` + `resolve_session_persona`; a data migration materializes the 3 defaults per existing tenant; an admin CRUD API for the AgentSpec definitions (distinct from the invocations STUB). The HANDOFF flow resolves the target's `system_prompt` from the catalog. FE wiring of the existing `/subagents` page → **57.71**.

---

## 1. Sprint Goal

Stand up a real DB-backed per-tenant agent-spec catalog and wire it behind HANDOFF persona resolution + expose it for management: create the `agent_catalog` table (per-tenant, RLS, Alembic `0023`, Group 9; fields aligned to the mockup AgentSpec — key/name/model/system_prompt/allowed_modes/status + budget/tools in JSONB) + `AgentCatalogRepository`; replace the global sync `resolve_persona` with an async tenant-scoped resolver (DB catalog → hardcoded `DEFAULT_AGENTS` → `None`), rewiring `HandoffService.boot_handoff` (reject unknown) + `handler.resolve_session_persona` (DEMO fallback) while preserving their contracts; materialize the 3 default agents per existing tenant via a data migration; and expose an admin CRUD API for the AgentSpec definitions (`require_admin_platform_role`, Pydantic, `append_audit`; distinct from the existing `/subagents` invocations STUB). Prove it with backend tests (table/RLS/repo/seed/resolution/CRUD/multi-tenant) + the HANDOFF flow resolving the target persona from the DB. **Multi-tenant 鐵律: every catalog row + query is tenant-scoped; cross-tenant forbidden (RLS + repo filter).** The default (non-handoff) chat persona stays DEMO (§9). Wiring the existing `/subagents` FE page to this catalog → **57.71** (§9).

---

## 2. User Stories

- **US-1 (catalog table + migration)** — As the platform, I want an `agent_catalog` table (per-tenant, RLS) holding AgentSpec definitions (key/name/model/system_prompt/allowed_modes/status + budget/tools JSONB) so each tenant's agents are isolated + durable. → `infrastructure/db/models/agent_catalog.py` (NEW, `Base, TenantScopedMixin`, Group 9) + Alembic `0023`.
- **US-2 (repository + default seed)** — As the platform, I want an `AgentCatalogRepository` (async, tenant-scoped CRUD) + the 3 default agents materialized per existing tenant. → `AgentCatalogRepository`; `DEFAULT_AGENTS` (moved from `PERSONA_REGISTRY`); `0023` data migration seeds existing tenants.
- **US-3 (async tenant-scoped resolution)** — As the HANDOFF flow, I want persona resolution to read the tenant's catalog (override/extend) → hardcoded defaults → reject, so handoff targets are per-tenant configurable WITHOUT breaking the `None`=reject / DEMO-fallback contract. → async `resolve_persona(db, tenant_id, key)`; rewire `service.py:131` + `handler.py:405`.
- **US-4 (admin CRUD API)** — As a platform admin, I want CRUD endpoints for a tenant's AgentSpec definitions (list/create/update/delete) so the catalog is manageable (and the 57.71 FE has a real API). → `api/v1/admin/agents.py` (mirror `admin/tenants.py`); distinct from the `/subagents` invocations STUB (untouched).
- **US-5 (validation)** — As a reviewer, I want backend tests (table/RLS/repo/seed/resolution/CRUD/multi-tenant) + a HANDOFF integration test proving the target persona resolves from the DB catalog (override) and falls back to defaults (empty catalog), so the catalog is real (non-Potemkin) and the contract is preserved.

---

## 3. Technical Specifications

### 3.0 Architecture (backend-only)

```
        ┌──────────── agent_catalog (per-tenant, RLS, 0023, Group 9) ─────────────┐
        │ id · tenant_id · key · name · model · system_prompt · allowed_modes      │
        │ · status · meta_data JSONB (budget{max_tokens,duration,concurrent,depth} │
        │   + tools[]) · is_active · created/updated_at                            │
        └──────────────────────────────────────────────────────────────────────────┘
              ▲ CRUD (tenant-scoped, admin)            ▲ read (tenant-scoped)
   /admin/.../agents (NEW CRUD API) ──► AgentCatalogRepository ◄── async resolve_persona(db, tenant_id, key):
   (require_admin_platform_role,                                    1. DB catalog row (active) → system_prompt
    Pydantic, append_audit)                                         2. else DEFAULT_AGENTS[key] (hardcoded fallback)
   [distinct from /subagents invocations STUB — untouched]          3. else None (reject)
                                                                       ▲                      ▲
                                       HandoffService.boot_handoff ────┘   handler.resolve_session_persona ──┘
                                       (None → HandoffError, reject)       (None → DEMO_SYSTEM_PROMPT)

   FE /subagents page (read-only fixture today) → wire to this CRUD API + editable tabs → Sprint 57.71 (§9)
```

The resolver prefers the per-tenant DB row, falls back to the always-present hardcoded `DEFAULT_AGENTS`, then `None` — an empty / new-tenant catalog still resolves the 3 defaults (contract preserved, no lazy-write in any read path). The data migration materializes the defaults as editable rows for existing tenants (so the 57.71 FE shows + edits them). The budget/tools/allowed_modes fields are STORED (JSONB) but NOT yet enforced in the loop (§9). The default (non-handoff) chat persona stays DEMO (§9).

### 3.1 Catalog table + migration (US-1) — `agent_catalog.py` (NEW) + Alembic `0023`
- `AgentCatalog(Base, TenantScopedMixin)` (09-schema **Group 9 Subagent**): `id` UUID PK (`server_default gen_random_uuid()`), `tenant_id` (mixin), `key` String(64) (the role / immutable id, e.g. "researcher"), `name` String(128), `model` String(128) nullable, `system_prompt` Text, `allowed_modes` JSONB or String[] (subset of fork/as_tool/teammate/handoff), `status` String(32) default "live" (live/staging), `meta_data` JSONB (physical `"metadata"` alias; holds budget{max_tokens,duration,concurrent,depth} + tools[]), `is_active` Boolean default true, `created_at`/`updated_at`. `__table_args__`: `UniqueConstraint("tenant_id", "key", name="uq_agent_catalog_tenant_key")` + `Index("idx_agent_catalog_tenant", "tenant_id")`. (Day-1 confirms the domain-group file per `09-db-schema-design.md §Group 9`.)
- Alembic `0023_agent_catalog` (`down_revision="0022_session_handoff_linkage"`): create table + indexes + TWO RLS policies (`tenant_isolation_agent_catalog` USING + `tenant_insert_agent_catalog` WITH CHECK) + `FORCE ROW LEVEL SECURITY` (mirror `0019`); `downgrade` drops policies then table. Data-seed step loops existing tenants → INSERT the 3 defaults (raw SQL quotes `"metadata"` — alias). Verified up/down/re-up.

### 3.2 Repository + default seed (US-2) — `AgentCatalogRepository` + `DEFAULT_AGENTS`
- `AgentCatalogRepository(db: AsyncSession)` (mirror `SessionRepository`): async, `tenant_id` required kw-only, tenant filter in every WHERE, caller-owned flush. Methods: `list_by_tenant(tenant_id)`, `get_by_key(tenant_id, key)`, `create(...)`, `update(tenant_id, agent_id, ...)`, `delete(tenant_id, agent_id)`.
- `DEFAULT_AGENTS` (moved from `PERSONA_REGISTRY` — same 3 researcher/reviewer/planner prompts; `persona_registry.py` becomes the default-source + the async resolver). The `0023` data migration seeds existing tenants.

### 3.3 Async tenant-scoped resolution (US-3) — `resolve_persona` rewire
- NEW async `resolve_persona(db: AsyncSession, tenant_id: UUID, key: str) -> str | None`: (1) `AgentCatalogRepository(db).get_by_key(tenant_id, key)` → if active → `system_prompt`; (2) else `DEFAULT_AGENTS.get(key)`; (3) else `None`. Keep sync `resolve_default_persona(key) -> str | None` (hardcoded fallback, for tests / no-DB paths).
- Rewire `service.py:131` (`boot_handoff`): `await resolve_persona(db, tenant_id, target_agent)`; `None` → `HandoffError` (it resolves BEFORE the txn — Day-1 keeps that order; `db`/`tenant_id` are params).
- Rewire `handler.py:405` (`resolve_session_persona`, async): `await resolve_persona(db, tenant_id, str(agent_role))`; `None` → `DEMO_SYSTEM_PROMPT`. Day-1 re-reads both call sites + `handoff/__init__.py` re-export before the rewire.

### 3.4 Admin CRUD API (US-4) — `api/v1/admin/agents.py` (NEW)
- `APIRouter` mirroring `admin/tenants.py` — sub-resource of a tenant: `GET/POST /admin/tenants/{tenant_id}/agents` + `PUT/DELETE /admin/tenants/{tenant_id}/agents/{agent_id}` (Day-1 confirms the exact prefix vs a top-level `/admin/agents`). Pydantic `AgentCreateRequest`/`AgentUpdateRequest`/`AgentResponse` (fields per the AgentSpec shape). Guards: `Depends(require_admin_platform_role)` + `require_tenant_match_or_platform_admin`. `append_audit` on create/update/delete (`operation="agent_catalog.create"` etc.). `db.flush()`; tenant-scoped via the repo. **Distinct from `/api/v1/subagents`** (the invocations STUB — untouched).

### 3.5 Lint / neutrality / doc single-source
- `check_rls_policies` green (2-policy + FORCE). `check_llm_sdk_leak` 0 (catalog + repo + resolver provider-free; `agent_harness/**` untouched — resolver in `platform_layer`). All 10 V2 lints green; no codegen change; no FE change this slice.
- **Doc single-source**: 17.md unchanged (resolve_persona is a platform-layer concern, not a registered cross-category contract — Day-1 confirms). `09-db-schema-design.md §Group 9` += the `agent_catalog` table.

### 3.6 Validation (US-5)
- **Backend unit**: `AgentCatalogRepository` (CRUD + tenant filter + UniqueConstraint); `resolve_persona` (DB hit / DB miss→default / unknown→None / inactive→fallback); `DEFAULT_AGENTS` integrity. **Backend integration**: `0023` up/down; RLS enforced (cross-tenant SELECT blocked); the CRUD API (create/list/update/delete + `require_admin_platform_role` 403 + cross-tenant 404 + audit rows); the HANDOFF flow resolves the target from the DB catalog (override) AND from defaults (empty catalog) — extend `test_chat_handoff.py`. **Multi-tenant**: tenant A's agents invisible to tenant B. **Test isolation**: the new resolver DB read must not leak connections in TestClient suites (Risk Class C; 57.68 FIX-026 lesson).

---

## 4. File Change List

| File | Change |
|------|--------|
| `backend/src/infrastructure/db/models/agent_catalog.py` | **NEW** — `AgentCatalog` ORM (per-tenant, AgentSpec fields, JSONB meta_data) (US-1) |
| `backend/src/infrastructure/db/migrations/versions/0023_agent_catalog.py` | **NEW** — create table + RLS 2 policies + FORCE + indexes + data-seed existing tenants (US-1/US-2) |
| `backend/src/infrastructure/db/repositories/agent_catalog_repository.py` | **NEW** — `AgentCatalogRepository` (async, tenant-scoped CRUD) (US-2) |
| `backend/src/platform_layer/handoff/persona_registry.py` | **EDIT** — `PERSONA_REGISTRY`→`DEFAULT_AGENTS`; NEW async `resolve_persona(db, tenant_id, key)` (DB→default→None) + sync `resolve_default_persona`; `__all__` (US-2/US-3) |
| `backend/src/platform_layer/handoff/service.py` | **EDIT** (`:131`) — `await resolve_persona(db, tenant_id, target_agent)` (US-3) |
| `backend/src/platform_layer/handoff/__init__.py` | **EDIT** — re-export updates (US-3) |
| `backend/src/api/v1/chat/handler.py` | **EDIT** (`:405`) — `await resolve_persona(db, tenant_id, agent_role)` (US-3) |
| `backend/src/api/v1/admin/agents.py` | **NEW** — admin CRUD router for AgentSpec definitions (US-4) |
| `backend/src/api/main.py` (or admin router include) | **EDIT** — register the agents router (US-4) |
| `backend/tests/unit/...` + `backend/tests/integration/...` | **NEW/extend** — repo + resolver + migration + RLS + CRUD + multi-tenant + handoff-from-DB (US-5) |
| `backend/tests/integration/api/test_chat_handoff.py` | **EXTEND** — target resolves from DB catalog (override) + default fallback (US-5) |
| `docs/03-implementation/agent-harness-planning/09-db-schema-design.md` | **EDIT** §Group 9 — document the `agent_catalog` table |
| `claudedocs/4-changes/feature-changes/CHANGE-038-agent-catalog.md` | **NEW** — change record |

**No FE change** (the existing `/subagents` page wiring → 57.71). **No new wire-type / no codegen / no SSE change.** No `agent_harness/**` edit (resolver is platform-layer). **No touch to the `/subagents` invocations STUB** (different concern — `AD-Subagent-RealList-Phase58`).

---

## 5. Acceptance Criteria

- `agent_catalog` table exists (per-tenant, RLS 2 policies + FORCE, Group 9, AgentSpec fields); Alembic `0023` up/down/re-up clean; `check_rls_policies` green.
- `AgentCatalogRepository` is async + tenant-scoped (every query filters `tenant_id`); the 3 defaults are materialized per existing tenant by the `0023` data migration.
- Async `resolve_persona(db, tenant_id, key)` resolves DB catalog (override) → hardcoded `DEFAULT_AGENTS` → `None`; `boot_handoff` still rejects unknown targets; `resolve_session_persona` still falls back to DEMO; an EMPTY catalog still resolves the 3 defaults (contract preserved).
- Admin CRUD API: create/list/update/delete a tenant's AgentSpec definitions; `require_admin_platform_role` enforced (403 without); cross-tenant blocked (404/RLS); `append_audit` rows on mutations; the `/subagents` invocations STUB untouched.
- The HANDOFF flow resolves the target persona from the DB catalog (override proven) + from defaults (empty-catalog proven) — `test_chat_handoff.py` extended.
- All existing tests green; `mypy --strict src/` 0; 10/10 V2 lints (LLM SDK leak 0). **Multi-tenant**: tenant A's agents invisible to tenant B. No FE change (Vitest unchanged).

---

## 6. Deliverables

- [ ] `agent_catalog.py` ORM + Alembic `0023` (table + RLS + seed) (US-1/US-2)
- [ ] `AgentCatalogRepository` (US-2)
- [ ] `persona_registry.py` rewire (`DEFAULT_AGENTS` + async `resolve_persona`) + `service.py`/`handler.py` await rewire (US-3)
- [ ] `api/v1/admin/agents.py` CRUD router + registration (US-4)
- [ ] backend tests (repo/resolver/migration/RLS/CRUD/multi-tenant/handoff-from-DB) (US-5)
- [ ] `09-db-schema-design.md §Group 9` += agent_catalog; CHANGE-038 + progress.md + retrospective.md

---

## 7. Workload Calibration

Scope class: **`agent-catalog-backend` (0.55, NEW — pending validation)** — a backend multi-domain feature-continuation (new per-tenant RLS table + migration + repo + async resolver rewire + seed + admin CRUD API + tests), composing established patterns (no new mechanism; FE deferred). Mid-band 0.55 (vs the fuller 0.50 fullstack the original plan estimated — FE removed). **Agent-delegated: yes** (staged: Stage-1a backend — table + migration + repo + resolver rewire + seed; Stage-1b — admin CRUD API + integration; parent independent re-verify each). `agent_factor` **`mechanical-greenfield-design-decisions` 0.65** (genuine design: table schema aligned to AgentSpec, resolver fallback chain, CRUD shape; heavy pattern-mirroring of `admin/tenants.py` + `0019` + `session_repository`).

> Bottom-up est ~15 hr → class-calibrated commit ~8.2 hr (mult 0.55) → agent-adjusted commit ~5.4 hr (agent_factor 0.65).

Caveat (carried 57.63-57.69): agent-delegated sprints have no clean wall-clock (`AD-Calibration-AgentDelegated-WallClock-Measure`; would be 8th consecutive). The NEW `agent-catalog-backend` class is a single unvalidated point — record caveated. The FE-deferral (57.71) keeps this slice bounded; if the CRUD API proves larger (the AgentSpec field set + reconciling allowed_modes/budget JSONB shapes), defer the richer fields to FE-time + re-confirm.

---

## 8. Dependencies & Risks

| Risk | Mitigation |
|------|------------|
| **Misframing the catalog** (generic vs the real Subagent Registry) | Day-0 D1-D3 reframed it to the AgentSpec-definitions registry (mockup + 09 Group 9 + existing fixture page); fields align to the mockup AgentSpec; user re-confirmed |
| **Conflating definitions with the invocations STUB** | the AgentSpec-definitions CRUD is a NEW endpoint (`/admin/.../agents`); the `/subagents` invocations GET (`AD-Subagent-RealList-Phase58`) is untouched |
| **`resolve_persona` sync→async ripple** | only 2 consumers (`service.py:131` + `handler.py:405`), both already async; Day-1 re-reads both + `__init__` re-export (`AD-Day0-Codegen-Existing-Shape-Capture`) |
| **Contract break** (None=reject / DEMO-fallback) | DB→default→None chain preserves both; EMPTY catalog still resolves the 3 defaults; tests assert all three branches |
| **RLS lint** | mirror the `0019` 2-policy + FORCE pattern; `check_rls_policies` gates; next migration `0023` |
| **JSONB column alias** | `meta_data` → physical `"metadata"`; raw SQL in the migration quotes `"metadata"` (57.59/57.60 precedent) |
| **Seed coverage** (new tenants) | hardcoded `DEFAULT_AGENTS` fallback covers new/empty tenants (no lazy-write); data migration materializes editable rows for EXISTING tenants; provisioning-step seeding deferred (§9) |
| **Admin CRUD auth** | mirror `admin/tenants.py` (`require_admin_platform_role` + `require_tenant_match_or_platform_admin`); cross-tenant 403/404 tested |
| **Multi-tenant leakage** | RLS + repo tenant-filter (double defense); integration asserts tenant A's agents invisible to B |
| **Test isolation** (new source DB call) | the resolver now does a DB read; ensure TestClient suites overriding `get_db_session` don't leak conns (Risk Class C; 57.68 FIX-026 lesson) |

---

## 9. Out of Scope (this sprint; carryover)

- **FE: wire the existing `/subagents` page to the catalog** — replace the `SUBAGENT_LIST` fixture with the real CRUD API, make the 4 detail tabs (AgentSpec/Budget/Tools/Stats) editable, add create/edit/delete. **Sprint 57.71** (user-confirmed; the FE page is a faithful mockup port today but read-only).
- **Wiring allowed_modes / budget / tools into the loop** — the catalog STORES these (JSONB) but does NOT enforce them this slice (loop tool/budget/mode wiring is a separate concern); fields present, enforcement deferred.
- **The `/subagents` invocations real list** — `AD-Subagent-RealList-Phase58` (the existing GET STUB → real invocation observability); a different concept, untouched.
- **Default (non-handoff) chat persona from the catalog** — stays hardcoded `DEMO_SYSTEM_PROMPT` (Day-0 D7).
- **Provisioning-step seeding for new tenants** — covered by the hardcoded fallback this slice; a real `ProvisioningWorkflow` seed step is future work.
- **Tenant self-service management** — CRUD is platform-admin (`require_admin_platform_role`); tenant-admin self-service is future.
- **Other A-3b carryover** — user-visible transcript continuity (message-persistence subsystem), summarize-carry, target auto-first-turn, multi-hop chains + cycle guards, dedicated columns. Other Area-A: A-4 (loop tracer), A-5c (diagnostic Inspector UI), A-6.
