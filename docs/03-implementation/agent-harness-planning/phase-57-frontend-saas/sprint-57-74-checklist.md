# Sprint 57.74 — Checklist (admin-tenants stats aggregate endpoint + per-row agents/runs24 + stats-strip wiring)

**Plan**: [`sprint-57-74-plan.md`](./sprint-57-74-plan.md)
**Created**: 2026-06-03
**Status**: Draft (commit/push/PR user-gated)

> Rule: only `[ ]` → `[x]`; never delete unchecked items; defer with `🚧 + reason`.
> Backend+frontend feature-continuation (endpoint mirrors Sprint-57.73 `/memory/matrix` + `cost_summary` deps; frontend is pure wiring) → **no design note**. Mockup-Fidelity Hard Constraint applies (`docs/rules-on-demand/frontend-mockup-fidelity.md`). Scope: fleet `/admin/tenants/stats` + strip (3 real stats) + table agents/runs24 columns; Anomalies + trend deltas honest-gapped (no fabrication). Closes `AD-AdminTenants-Stats-Aggregate-Endpoint`.

---

## Day 0 — Plan-vs-Repo Verify + Branch + Decisions

### 0.1 Day-0 verify (researcher ground-truth pass, main `12324e50`)
- [x] **Prong 1 (path)**: `backend/src/api/v1/admin/tenants.py` (list endpoint + add `/stats`); `backend/src/infrastructure/db/models/{agent_catalog,sessions,identity}.py` (AgentCatalog / Session / Tenant ORMs); `backend/src/platform_layer/identity/auth.py` (`require_admin_platform_role`); `frontend/src/features/admin-tenants/{services/adminTenantsService,hooks/useAdminTenants,types,_fixtures,components/{TenantsStatsStrip,TenantsTable,AdminTenantsView}}.tsx`; precedent `backend/src/api/v1/memory.py` (`/matrix`) + `admin/cost_summary.py`; mockup `reference/design-mockups/page-admin.jsx`; `frontend/tests/e2e/admin-tenants.spec.ts` (57.73 e2e to extend); `check-mockup-fidelity.mjs`
- [x] **Prong 2 (content)**: D1 `agent_catalog` `is_active`/`tenant_id` + idx (`:104`/`:118`); D2 `sessions` `started_at`/`tenant_id`, NOT partitioned (`:72`/`:114`); D3 `list_tenants` deps `require_admin_platform_role` (`:227-230`), `TenantListResponse` (`:218`), NO agents/runs24 fields; D4 NEW `/stats` endpoint decision (don't pollute lean list); D5 frontend shapes (`TenantsTable:124-125` GAP_PLACEHOLDER, `TenantsStatsStrip` STATS_FIXTURE `{label,value,delta,deltaDir}` ×4 incl Anomalies); D6 stat mapping (3 real + Anomalies/deltas gap); D7 precedent `/memory/matrix` + deps; D8 shadcn-residue grep=0, mockup-native states
- [x] **Prong 2.5 (child-tree)**: admin-tenants page child components (TenantsStatsStrip / TenantsTable / AdminTenantsView) — confirm no shadcn-utility residue (grep `bg-card|text-foreground|bg-muted|border-border`) + inline `style={{` has `eslint-disable` header (57.73 just stabilized these → expect clean)
- [x] **Prong 3 (schema)**: N/A — no DB / migration / ORM change (`/stats` is a read aggregate over existing `tenants`/`agent_catalog`/`sessions`)
- [x] **Path-order check** (D-DAY0-1 — register `/stats` after `:227` list, BEFORE `/{tenant_id}` GET `:315`): grep `admin/tenants.py` for a `GET /{tenant_id}` that could shadow `/stats` (static segment should be safe; verify + register explicitly)
- [x] **Mockup-fidelity**: `styles-mockup.css` byte-identical (diff empty); data-only wiring → no CSS change; `HEX_OKLCH_BASELINE = 50` must stay; strip loading/error MUST be mockup-native (NOT shadcn skeleton)
- [x] **Doc-location**: CHANGE-042; mockup canonical = `page-admin.jsx`; `/stats` follows `/memory/matrix` facade precedent (router + FE service single-source, not 17.md)
- [x] Catalogue drift in progress.md Day-0 (D-DAY0-1 path-order + D-DAY0-2 sibling precedent); **go/no-go for Day 1 = GO** (no scope shift)

### 0.2 Branch + decisions
- [x] Branch `feature/sprint-57-74-admin-tenants-stats` from `main` (`12324e50`)
- [ ] plan + checklist commit; Day-0 progress commit
- [x] Decisions (user-locked 2026-06-03): scope = strip + per-row columns; **Runs·24h = sessions started in last 24h** (`started_at`); un-backable Anomalies + trend deltas = **honest gap** (placeholder + BackendGapBanner, no fabrication); NEW `/stats` endpoint (not extend list); **Agent-delegated: yes** (Track A backend + Track B frontend sequential code-implementer + parent re-verify per Before-Commit item 7)

---

## Day 1 — Backend `/admin/tenants/stats` endpoint + tests (US-1/US-2/US-6)

### 1.1 Endpoint + models (US-1/US-2)
- [ ] `admin/tenants.py` — new `GET /admin/tenants/stats`, deps `[require_admin_platform_role]` + `get_db_session` (plain, fleet-wide; NOT `get_db_session_with_tenant`); registered without `/{tenant_id}` shadowing
- [ ] Pydantic (inline, mirror `/memory/matrix`): `FleetStats{active_tenants,total_seats,agents_deployed}` + `PerTenantStat{tenant_id,agents,runs24}` + `TenantsStatsResponse{fleet,per_tenant,gapped}`
- [ ] Aggregate: `active_tenants`=count(Tenant state=ACTIVE); `total_seats`=coalesce(sum(seats),0); `agents_deployed`=count(AgentCatalog is_active); per-tenant agents=GROUP BY tenant_id WHERE is_active; per-tenant runs24=GROUP BY tenant_id WHERE `started_at >= now(utc)-24h` (tz-aware bound param, NOT DB string); merge maps (union; missing side→0); `gapped=["anomalies","deltas"]`

### 1.2 Backend tests (US-6)
- [ ] `test_admin_tenants_stats.py` — fleet counts correct (seed active/suspended tenants, seats, active+inactive agents); per_tenant map (agents from agent_catalog, runs24 from sessions in window, session outside 24h excluded); non-platform-admin → 403; empty fleet → zeros + empty per_tenant + gapped present
- [ ] Risk Class C: ensure admin-tenants suite `get_db_session` override covers the new endpoint (just-codified `AD-Source-DB-Call-Test-Isolation`)
- [ ] `mypy src/ --strict` 0; `python scripts/lint/run_all.py` (V2 lints incl `check_llm_sdk_leak`) green

---

## Day 2 — Frontend hook/service/types + stats-strip wiring (US-5/US-3)

### 2.1 Hook + service + types (US-5)
- [ ] `services/adminTenantsService.ts` — `fetchStats(signal)` → `GET /api/v1/admin/tenants/stats` (mirror `listTenants`)
- [ ] `types.ts` — `FleetStats`/`PerTenantStat`/`TenantsStatsResponse` (`tenant_id` string)
- [ ] `hooks/useAdminTenantsStats.ts` (NEW) — `useQuery` key `["admin-tenants","stats"]`, mirror `useAdminTenants.ts:34-41`

### 2.2 Stats strip wiring + honest gaps (US-3)
- [ ] `TenantsStatsStrip.tsx` — take `fleet`(+loading/error) prop, drop `STATS_FIXTURE` import; real Active tenants / Total seats / Agents deployed (formatted)
- [ ] `Anomalies` stat → subtle placeholder (`var(--fg-subtle)` "—", NOT fabricated); every `delta`/trend arrow → omit/subtle placeholder (no historical source); keep verbatim mockup card classes
- [ ] `BackendGapBanner` naming the gapped bits (Anomalies + trend deltas); mockup-native loading/error states
- [ ] `_fixtures.ts` — remove orphan `STATS_FIXTURE` (move to test if a Vitest needs it)

---

## Day 3 — Table columns + View wiring + Vitest + e2e (US-4/US-7)

### 3.1 Table columns + View (US-4)
- [ ] `TenantsTable.tsx` — accept `statsByTenant?: Record<string,{agents,runs24}>` prop; fill `Agents` + `Runs · 24h` cells (`:124-125`) from the map (real counts; subtle "—" only for absent/0 tenant per mockup spot-check); identity columns + states from 57.73 UNCHANGED
- [ ] Reword/relocate gap banner: drop now-backed agents/runs24 from the table banner (strip owns Anomalies/deltas banner) — single honest banner per gap, no double-banner
- [ ] `AdminTenantsView.tsx` — mount `useAdminTenantsStats()`; pass `data.fleet`(+loading/error) to strip + build `statsByTenant` from `data.per_tenant` → pass to table; keep 57.73 `useAdminTenants()` list wiring intact

### 3.2 Vitest + Playwright (US-7)
- [ ] Vitest: `useAdminTenantsStats` (mocked fetch → fleet/per_tenant/gapped); `TenantsStatsStrip` (seeded fleet → 3 real + Anomalies/delta gap markers + banner); `TenantsTable` (statsByTenant → real agents/runs24, "—" absent; 57.73 rows/states unchanged)
- [ ] Playwright: extend `admin-tenants.spec.ts` — mock `**/api/v1/admin/tenants/stats` (happy: strip real values + table columns filled; error: 500 → mockup-native states)

---

## Day 4 — Mockup-fidelity sweep + Closeout

### 4.1 Mockup-fidelity + full sweep (US-7)
- [ ] **CSS diff**: `diff styles.css styles-mockup.css` → empty (parent-verified)
- [ ] **grep guard**: no hardcoded hex/oklch in edited components + new hook (all `var(--*)`)
- [ ] **`check:mockup-fidelity`**: baseline unchanged (50=50, byte-identical) — parent-run (Before-Commit item 7)
- [ ] **computed-style**: stats-strip card + table agents/runs24 cell vs `page-admin.jsx`; no shadcn-token residue introduced
- [ ] `npm run lint` (no `--silent`) EXIT 0 + `npm run build` tsc 0 + Vitest green — parent-run
- [ ] Backend `pytest` (stats + 403 + window) green; mypy 0; V2 lints green — parent-run
- [ ] Parent re-verify (Before-Commit item 7): 4-query aggregate correctness + per-tenant merge + 403 gate + honest gaps (no fabricated stat/arrow) + English copy convention (no 繁中 state strings — 57.73 lesson)

### 4.2 Closeout docs
- [ ] CHANGE-042 created; no 17.md/02.md/01.md change (facade precedent; pure read aggregate)
- [ ] progress.md (Day 0-4) + retrospective.md (Q1-Q7) — NO design note (feature-continuation)
- [ ] Calibration: `mixed-multidomain-bundle` 0.65 + `agent_factor` `mixed-multidomain-bundle-mechanical` 0.45 (CAVEATED — 12th consecutive no-clean-wall-clock; if <0.7 → escalate per 57.59 note / 0.30 or fold pattern-reuse-heavy); recorded `calibration-log.md §3`
- [ ] MEMORY.md pointer + `project_phase57_74_*.md` subfile + CLAUDE.md lean (Current Sprint row + footer)
- [ ] Carryover recorded (plan §9 + retrospective §Q5): `AD-AdminTenants-Anomalies-Stat-Backend` + `AD-AdminTenants-Stats-Trend-Deltas` (NEW, if pursued) + page-scoped per-tenant stats; remaining program: A-5c Trace/Memory tabs (`AD-ChatV2-Inspector-{Trace,Memory}-Phase2`), `AD-Memory-OpsHistory-Backend`, FE `/subagents` (`AD-Subagent-RealList-Phase58`)
- [ ] Mark `AD-AdminTenants-Stats-Aggregate-Endpoint` CLOSED in next-phase-candidates

### 4.3 Ship
- [ ] Final verify (parent-run): CSS diff empty + build tsc 0 + Vitest green + `check:mockup-fidelity` 50 + lint (no `--silent`) EXIT 0 + backend pytest/mypy/V2-lints green + grep 0 hardcoded color
- [ ] commit (Day 0-4) + push + PR — **user-authorized** (push/PR gated on user approval)
