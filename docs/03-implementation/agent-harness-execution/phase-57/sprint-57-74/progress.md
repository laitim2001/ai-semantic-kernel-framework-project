# Sprint 57.74 Progress — admin-tenants stats aggregate endpoint

**Plan**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-74-plan.md`
**Checklist**: `...sprint-57-74-checklist.md`
**Branch**: `feature/sprint-57-74-admin-tenants-stats` (from `main` `12324e50`)

---

## Day 0 — 2026-06-03 — Plan-vs-Repo Verify + Decisions

### Decisions (user-locked, 3× AskUserQuestion)
- **Scope** = stats strip + per-row Agents/Runs·24h columns (full `AD-AdminTenants-Stats-Aggregate-Endpoint` closure).
- **Runs·24h** = sessions started in last 24h (`sessions.started_at >= now()-24h`).
- **Un-backable** (Anomalies stat + per-stat trend deltas) = honest gap (placeholder + `BackendGapBanner`, no fabrication).
- NEW `GET /admin/tenants/stats` endpoint (not extend lean `list_tenants`).
- **Agent-delegated: yes** — Track A backend + Track B frontend (sequential code-implementer) + parent re-verify (Before-Commit item 7).

### Prong 1 (path) — GREEN, no drift
All confirmed via Glob: `backend/src/api/v1/admin/tenants.py` + `cost_summary.py`/`sla_reports.py`/`agents.py`; ORMs `agent_catalog.py`/`sessions.py`/`identity.py`; `frontend/src/features/admin-tenants/{services/adminTenantsService,hooks/useAdminTenants,types,_fixtures,components/{TenantsStatsStrip,TenantsTable,AdminTenantsView}}` — all exist. Service file IS `adminTenantsService.ts` (plan assumption confirmed). `frontend/tests/e2e/admin-tenants.spec.ts` (57.73) exists to extend.

### Prong 2 (content) — researcher pass (see plan §0 D1-D8)
- agent_catalog: `is_active` (`:104`) / `tenant_id` / `idx_agent_catalog_tenant` (`:118`) — use `is_active` for "deployed".
- sessions: `started_at` (`:114`) / `tenant_id`; session root NOT partitioned (`:72`).
- `list_tenants` (`:227-230`) deps `require_admin_platform_role` (no tenant filter → cross-tenant aggregate OK); `TenantListResponse` (`:218`); no agents/runs24 fields.
- frontend: `TenantsTable:124-125` agents/runs24 = `GAP_PLACEHOLDER`; `TenantsStatsStrip` consumes `STATS_FIXTURE` (`_fixtures.ts:36`, 4 stats `{label,value,delta,deltaDir}` incl Anomalies).

### Prong 2.5 (child-tree) — researcher: shadcn-residue grep = 0 in `features/admin-tenants` (57.73 just stabilized); backend agent re-greps before edit.

### Prong 3 (schema) — N/A (read aggregate over existing tables; no migration/ORM change).

### Drift findings
- **D-DAY0-1 (path-order, MUST honor)**: `admin/tenants.py` router prefix `/admin/tenants`; `GET ""` list at `:227`, a `GET` at `:315` (likely `/{tenant_id}` detail) + `PATCH /{tenant_id}` at `:515`. → the new `GET /stats` **must be registered after `:227` and BEFORE the `/{tenant_id}` GET (`:315`)** or `/stats` gets captured as `tenant_id="stats"`. Backend agent instructed accordingly.
- **D-DAY0-2 (favourable)**: `cost_summary.py` + `sla_reports.py` are sibling admin aggregate endpoints in the same router package → clean precedent to mirror for deps + inline Pydantic.
- No unfavourable scope drift; plan §0 D3 already noted region/seats present (from 57.46/47).

### go/no-go = **GO** (Day 1 backend). No scope change; D-DAY0-1 is an implementation-placement constraint, not a scope shift.
