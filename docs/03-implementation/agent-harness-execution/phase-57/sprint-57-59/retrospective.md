# Sprint 57.59 — Retrospective

**Sprint**: 57.59 — RateLimits Potemkin Migration (C1 two-table split; Phase 58.x deeper extensions 2/5)
**Closed**: 2026-05-28
**Branch**: `feature/sprint-57-59-rate-limits-potemkin-migration`
**Commits**: `560a7697` (Day 0) + `195072ef` (Day 1, 17 files +1898/-76) + Day 2 closeout (pending)
**Class**: `mixed-multidomain-bundle` 0.65 (SCOPE 3rd data point) / agent_factor `mixed-multidomain-bundle-mechanical` 0.65 (tier-3 **2nd validation**)
**Agent-delegated**: yes (2 sequential code-implementer agents; 24th + 25th consecutive chain)

---

## Q1 — What went well

1. **AP-4 Potemkin fully closed**: the `rate_limits` table (dormant since Phase 49 V2 baseline) is now genuinely written (`pg_insert.on_conflict_do_update` write-through) + queried (recovery + usage GET). The V1-lesson anti-pattern that Sprint 57.58 Day 0 surfaced is resolved one sprint later — clean rolling-planning follow-on.
2. **Two-table split shipped cleanly**: NEW `rate_limit_configs` (durable config) + activated `rate_limits` (usage instances) + data migration (`meta_data` → config rows, additive) + 4 endpoint re-points (GET/PUT/usage/middleware) — all in one sprint, **API shapes UNCHANGED so frontend was untouched** (0 frontend files; Vitest 675 unaffected).
3. **Day 0 Schema-Verify Prong paid off**: caught 3 NOTABLE refinements before code (window_end column / RLS double-policy / inline-parse-not-import) → agents had accurate spec; 0 mid-Day-1 schema surprises on those.
4. **`check_rls_policies` lint green on the new table** (20 RLS tables, +1) — multi-tenant discipline held; both `tenant_isolation` (USING) + `tenant_insert` (WITH CHECK) policies added per 0009 pattern.
5. **Agents caught + fixed 2 real bugs honestly**: D-DAY1-1 (tenants JSONB physical column is `metadata`, ORM `meta_data` is an alias — live migration failure caught it) + D-DAY1-3 (asyncpg `SET LOCAL` bind-param fails → `set_config` per correction_loop precedent). No faked tests.
6. **LLM-neutrality preserved** through a runtime re-point that touched Cat 2: `check_llm_sdk_leak` green; the `RateLimitGate` Protocol seam stayed import-free.
7. pytest 1819 → **1840** (+21; plan target +15); migration up/down/up clean.

## Q2 — What didn't go well + calibration

1. **Plan §4.1/4.5 missed the `window_end` column** — the usage table has BOTH `window_start` + `window_end` (NOT NULL); plan only modeled window_start. Caught Day 0 Prong 3 (D-DAY0-G) so no code impact, but the plan was drafted from the Sprint 57.58 Day 0 memory of the table (which only noted window_start). Lesson: when planning to activate a known table, read its FULL schema at plan-draft time, not just the columns recalled from a prior sprint.
2. **Plan assumed `parse_rate_limit_item` importable in the migration** — it's in a Redis-importing module; Day 0 D-DAY0-N flagged inline-instead. Minor; resolved before code.
3. **`meta_data` physical-column-name alias** (`metadata`) not anticipated in plan — surfaced as a live migration failure (D-DAY1-1). The agent fixed it, but Day 0 Prong 3 D-DAY0-O ("how to read meta_data JSONB in raw SQL") should have read the ORM `mapped_column` definition to catch the alias. Future Schema-Verify on raw-SQL-touching migrations: confirm physical column names (not ORM attr names).

### Calibration

- **Bottom-up** ~18 hr → **class-calibrated** ~11.7 hr (mult 0.65 `mixed-multidomain-bundle`) → **agent-adjusted** ~7.6 hr (agent_factor 0.65 `mixed-multidomain-bundle-mechanical`)
- **Actual** ≈ **2.6 hr** (Day 0 ~1.1 + Day 1 ~0.83 + Day 2 ~0.67)
- **ratio actual/bottom-up** = 0.14 (bottom-up ~7× generous)
- **ratio actual/class-committed** = 0.22 (confound: agent speedup; resolved at sub-class layer → KEEP `mixed-multidomain-bundle` 0.65 SCOPE class)
- **ratio actual/agent-adjusted** = **~0.34 BELOW [0.85, 1.20] band by 0.51** = `mixed-multidomain-bundle-mechanical` 0.65 tier-3 **2nd validation**
- **DECISION — ROLLBACK RULE MET**: Sprint 57.58 (~0.49) + Sprint 57.59 (~0.34) = **2 consecutive < 0.7** → per §Active block rollback rule ("2 sprints with ratio < 0.7 → tighten to 0.45") → **tighten `mixed-multidomain-bundle-mechanical` 0.65 → 0.45 effective Sprint 57.60+**. Note: even at 0.45 the equivalent ratio would be ~0.49 (still below band) — the agent speedup for mechanical multi-track DB sprints (~7× vs bottom-up) consistently outruns the sub-class haircut; if Sprint 57.60+ at 0.45 still < 0.7, escalate to 0.30 OR fold into `mechanical-pattern-reuse-heavy` 0.30. Flag Sprint 57.60+ for 1st validation under 0.45.
- Root cause: heavy mechanical pattern reuse (Alembic 0006/0009 templates + Sprint 57.56/57.57 store/endpoint patterns + Sprint 57.58 counter/parse reuse) → agents executed 2 substantial DB+service tracks in ~26 min wall-clock.

## Q3 — What we learned (generalizable)

1. **Schema-Verify Prong 3 must read physical column names + full schema, not ORM attr names** (D-DAY1-1 `metadata` alias + D-DAY0-G window_end). When a migration touches raw SQL OR plans to activate a known table, read the ORM `mapped_column("physical_name", ...)` declarations + the full column list. Candidate codification: extend `sprint-workflow.md §Step 2.5 Prong 3` with a "physical-column-name + full-schema read" row (combine with `AD-Day0-Prong2-Nested-Shape-Read` from Sprint 57.58 — both are "read the body, not the name" lessons). → NEW `AD-Day0-Prong3-Physical-Column-Read`.
2. **Activating a dormant table is a clean way to close AP-4** (vs deleting) when the table's schema matches a real need — the two-table split made the Phase-49 design intent finally real. But it required reading the FULL original schema (window_end surprise).
3. **`mixed-multidomain-bundle-mechanical` agent_factor needs tightening to 0.45** (2 consecutive < 0.7) — the mechanical-multi-track-DB shape is among the fastest agent-delegated work observed (~7× bottom-up).

## Q4 — Audit Debt deferred

| ID | Status | Target |
|----|--------|--------|
| `AD-RateLimits-MetaData-Cleanup-Phase58` | NEW | After 1-2 sprints validating table path stable → remove `meta_data["rate_limits"]` read-fallback + transitional dual-write + clear stored JSONB; ~1-2 hr |
| `AD-Day0-Prong3-Physical-Column-Read` | NEW (Q3 Lesson 1) | Codify Prong 3 physical-column + full-schema read (combine with Sprint 57.58 `AD-Day0-Prong2-Nested-Shape-Read`); when 2 data points |
| `AD-AgentFactor-Tier-3-MixedBundle-Mechanical-Tighten-0.45-Validation-Sprint-57.60` | NEW | 1st validation under tightened 0.45 (if also < 0.7 → escalate 0.30 / fold into pattern-reuse-heavy) |
| `AD-RateLimits-SyntaxValidation-Phase58` | CARRYOVER | Easier post-split (typed `quota`/`window_type` columns); PUT-time validation |
| `AD-RateLimits-Alerting-Phase58` | CARRYOVER | SSE 80% threshold; pairs with usage table |
| `AD-RateLimits-DedicatedTable-Phase58` | CLOSED | Folded into this sprint (table activated) |
| `AD-Day0-Prong2-Nested-Shape-Read` | CONTINUES | Sprint 57.58 1st + 57.59 reinforces; codify with Prong3 lesson |
| `AD-medium-frontend-Baseline-Recalibration` / `AD-MediumBackend-AICadence-Recalibration` / `AD-Test-Cleanup-Pattern-Shared-Helper` | CONTINUES | Phase 58+ |

## Q5 — Next steps (carryover candidates only; rolling planning §6)

Candidate directions for Sprint 57.60 (user picks):
- **`AD-RateLimits-MetaData-Cleanup-Phase58`** (remove transitional dual-write + fallback — natural follow-on after table path validated; small)
- RateLimits Alerting (SSE 80% threshold) — pairs with usage table just activated
- RateLimits SyntaxValidation (now easier with typed config columns)
- Other Phase 58+ portfolio (Quotas LiveUsage / FeatureFlags / Identity persistence)
- Codify `AD-Day0-Prong3-Physical-Column-Read` + `AD-Day0-Prong2-Nested-Shape-Read` (audit/docs sprint)

## Q6 — Solo-dev policy validation

- `required_approving_review_count = 0`; PR for audit trail + CI gate
- `enforce_admins = true` active; 5 required CI checks
- No `--admin` bypass / `--no-verify` / force push

## Q7 — N/A SKIP

Schema migration / refactor, NOT a spike sprint → no design-note extract (per `sprint-workflow.md §Step 5.5`). 9th consecutive Q7-N/A feature/refactor ship (57.51-57.59).

---

## Summary metrics

| Metric | Value |
|--------|-------|
| Files | 17 changed (5 NEW backend + 10 EDIT + 2 sprint docs) |
| pytest | 1819 → 1840 (+21; plan target +15) |
| mypy --strict | 0 |
| 9 V2 lints | 9/9 (check_rls_policies 20 tables + check_llm_sdk_leak) |
| Frontend | 0 touched (Vitest 675 unaffected) |
| Migration | 0019; up/down/up clean |
| **AP-4** | **CLOSED** (`rate_limits` usage table activated) |
| Calibration | `mixed-multidomain-bundle-mechanical` 0.65 tier-3 2nd validation ~0.34 → 2 consec < 0.7 → tighten 0.45 |
| mockup-fidelity | DUAL CLEAN 22/22 PARITY 15 consec 57.45-57.59 |
| Phase 58.x portfolio | 2/5 RateLimits deeper extensions (RuntimeEnforcement + Potemkin-Migration) |
