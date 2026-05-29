# Sprint 57.62 — Retrospective

**Sprint**: 57.62 — RateLimits Alerting (close `AD-RateLimits-Alerting-Phase58`)
**Closed**: 2026-05-29
**Class**: `medium-backend` 0.80 / agent-delegated yes (sequential Track A backend `rl-alerts-backend` 28th + Track B frontend `rl-alerts-frontend` 29th consecutive code-implementer) / agent-factor `mechanical-greenfield-design-decisions` 0.65 (4th validation — **back to backend+frontend pair shape**, vs 57.61 backend-only)
**Commits**: Day 0 `79282286` · Day 1 `95c65e09` · Day 2 (closeout) pending

---

## Q1 — What went well

- **Day 0 三-Prong reframed the whole sprint correctly before any code**: the carryover claim was "SSE infra ~80% from prior sprints; ~3-4 hr". Pre-plan Explore recon proved that false — the only SSE in the repo is the agent-loop `LoopEvent` stream; an admin SSE channel is greenfield (~8-12 hr). The AskUserQuestion at plan time → user locked **Option A persisted alert log** (~4-6 hr, polling-reuse) over a much larger SSE build. The sprint shipped the durable-alert value (capture-when-unwatched) without the SSE cost.
- **D-DAY0-G stateless-store simplification dropped a whole wiring edit before Day 1**: Prong 2 read the `_write_through` body and confirmed all 7 values (`session`/`tenant_id`/`resource`/`window_type`/`used`/`limit`/`window_start`) are in scope at the usage-upsert, inside an already-best-effort block. → the alert store is stateless + the session is already present → **NO ctor DI + NO `api/main.py` wiring** (the counter calls `maybe_record(session, …)` directly). Net scope −~0.2 hr; parallels 57.61's D-DAY0-J micro-simplification.
- **3 Day-0 factual corrections folded into the plan, not discovered mid-Day-1**: (1) migration-test path `tests/integration/db/` → `tests/integration/api/` (the repo has no `db/` test dir); (2) RLS SQL needs `current_setting('app.tenant_id', true)::uuid` (the `true` missing-ok arg) + `FORCE ROW LEVEL SECURITY` per the `0019` 2-policy precedent; (3) severity lowercase `warning`/`critical` + `CHECK` constraint mirroring `SLAViolation`. All three landed in `0021` correctly on the first agent pass.
- **Surgical, 0 regressions, all 13 Day-1.4 gates GREEN**: pytest 1887 → **1907** (+20: 12 store + 6 endpoint + 2 migration) / mypy `src --strict` 0/319 / 9/9 V2 lints (`check_rls_policies` 20 → **21** tables) / black·isort·flake8 clean / Vitest → **686** (+17) / tsc + build ✓ / ESLint exit 0 / **oklch delta 0** (baseline 48) / Alembic `0021` live down→up clean. The fail-open alert hook never touches the enforcement path (best-effort try/except rides the existing 57.59 usage-upsert write — no new DB roundtrip class).
- **Frontend reused existing severity styling cleanly**: the agent chose `.badge.warning` / `.badge.danger` CSS modifiers (which already reference `--warning`/`--danger` in `styles-mockup.css`) over inline color — 0 new oklch, existing Rate limits + Live usage cards bit-for-bit unchanged (scope-guard test).

## Q2 — What didn't go well

- **A stray orphaned `AA` unmerged remnant surfaced at the Day 1.4 sweep** (repo-health, OUT OF SCOPE): two ancient `sprint-52-2` docs (`progress.md` + `retrospective.md`) were in a both-added unmerged state with conflict markers in the working tree, with **no active merge/MERGE_HEAD** — a remnant from an earlier interrupted merge/stash in a prior session, NOT created by Track A/B. It cost ~15 min to diagnose + an AskUserQuestion gate before the Day 1 commit could proceed. Resolved cleanly (restore-from-HEAD; main/HEAD both hold the canonical clean blobs → no data loss). **Lesson** (`AD-RepoHealth-Orphaned-Unmerged-Sweep`): a parent should run `git status --short` looking for `AA`/`UU`/`DD` markers at sprint start (Day 0), not first discover them at the Day-1 commit gate — an orphaned conflict can block a path-scoped commit.
- **`AD-AgentDelegate-DevStack-Precheck` (57.61 lesson) was applied and paid off**: the parent pre-started `docker-compose.dev.yml` (Postgres + Redis Healthy) before delegating, so the backend agent's 20 integration tests ran in-agent rather than the parent absorbing a Docker-start step mid-sweep. (Listed here as the 57.61 "didn't go well" item that is now fixed.)

## Q3 — What we learned (generalizable)

1. **A carryover's effort estimate is a hypothesis, not a fact — re-verify the substrate at Day 0.** "SSE infra ~80%" was an unexamined assumption carried across two sprints; one Explore recon collapsed it. Day-0 Prong-2 content verify of the *claimed* prerequisite (not just the new code) is what surfaced it before the plan committed to the wrong shape.
2. **Detection belongs at the enforcement write-through, not the read/GET poll.** The core design reason Option A persists alerts: a breach that crosses 80% while no admin is watching the live-usage card must still be captured. Hooking `maybe_record` into `RedisRateLimitCounter._write_through` (the point where usage is already upserted) captures every window; a GET-time detection would miss unwatched windows. Idempotent peak/escalate upsert (`on_conflict_do_update` GREATEST + warning→critical) makes the hook safe to fire on every increment.
3. **An additive backend-feature card preserves mockup DUAL CLEAN as long as it reuses existing tokens.** The "Recent alerts" card is not in the mockup (it's a backend-feature surface), yet parity holds because it consumes existing `--warning`/`--danger`/`.card`/`.badge` tokens → HEX_OKLCH baseline 48 unchanged → `check-mockup-fidelity` oklch-delta 0. Same pattern as 57.57 (edit mode) + 57.58 (Live usage card). 18 consecutive DUAL CLEAN.

## Q4 — Calibration

**Bottom-up ~6.75 hr → class-calibrated ~5.4 hr (`medium-backend` 0.80) → agent-adjusted ~3.5 hr (`agent_factor` 0.65 `mechanical-greenfield-design-decisions`).**

Actual ≈ **2.7 hr** (Day 0 plan+checklist+三-Prong 16 checks+drift catalog+branch+commit ~0.8 hr + Day 1 Track A agent + Track B agent wall-clock ~0.45 hr + parent Day-1.4 authoritative sweep + AA detour ~0.25 hr + doc updates + commit ~0.85 hr + Day 2 closeout ~0.6 hr).

- **ratio actual/agent-adjusted ≈ 2.7 / 3.5 ≈ 0.77 — BELOW band [0.85, 1.20] by 0.08**
- ratio actual/class-committed ≈ 2.7 / 5.4 ≈ **0.50** (BELOW band — confound: agent speedup; resolved at the agent_factor sub-class layer per discipline. Note the internal consistency: actual/class-committed ≈ `agent_factor` × actual/agent-adjusted = 0.65 × 0.77 ≈ 0.50 ✓ → the combined class×agent_factor model is coherent)
- ratio actual/bottom-up ≈ 2.7 / 6.75 ≈ 0.40 (bottom-up ~2.5× generous — consistent with agent-delegated work)

**`medium-backend` 0.80 — 13th data point**: actual/class-committed ~0.50. Last-3 (57.60≈0.33 + 57.61≈0.48 + 57.62≈0.50) = **3-consecutive < 0.7** — the class-layer lower-trigger *technically* fires, BUT all three are agent-delegated and the confound is resolved at the agent_factor sub-class layer (the unconfounded signal is actual/agent-adjusted ~0.77, near band). → **KEEP `medium-backend` 0.80**. The class baseline is calibrated for human-pace; a class-baseline recalibration requires *human-factor* (non-agent) data points, which is exactly what `AD-MediumBackend-AICadence-Recalibration` continues to await (Phase 58+). No human-factor medium-backend sprint has occurred since the agent-delegation streak began.

**`mechanical-greenfield-design-decisions` 0.65 — 4th validation, BACK TO PAIR SHAPE**: ratio actual/agent-adjusted ≈ **0.77 BELOW band by 0.08**. Pair-shape sub-sequence is now 57.56=1.02 + 57.57=1.15 + 57.62≈0.77 → **3-point mean ≈ 0.98 IN band middle**. Within the pair shape, this is the 1st BELOW reading against 2 IN-band points (NOT 2-consecutive-below) → **KEEP 0.65, single-data-point caution** per the rollback rule.

**R6/R7 reassessment — the "backend-only is the outlier" hypothesis WEAKENS**: 57.61 (backend-only) landed 0.74 BELOW; 57.62 (pair shape) landed ~0.77 BELOW → **2 consecutive `-design-decisions` sprints below band regardless of shape**. R6 framed backend-only as the fast outlier; but a pair-shape sprint also undershot. The more likely root: **agent-delegation generally over-delivers vs the 0.65 on `-design-decisions` work**, with shape a secondary (not primary) factor. The AA detour (~0.25 hr unplanned overhead) actually nudged 57.62's ratio UP toward band — absent it, actual ≈ 2.45 hr → ratio ~0.70 (further below). So the agent over-delivery is real, not a measurement artifact.

**Updated carryover** `AD-AgentFactor-DesignDecisions-Below-Band-Watch` (broadens the 57.61 `-BackendOnly-Variant-Watch`): the watch is now **cross-shape** — if the NEXT `-design-decisions` sprint (either shape) lands < 0.85, that is the 3rd consecutive cross-shape below-band reading → propose tighten `agent_factor` 0.65 → 0.55. The pair-shape sub-sequence mean (0.98) still being IN band is the only thing holding 0.65; one more below-band reading flips it. Defer the tighten until that 3rd point per single-data-point-per-shape discipline.

## Q5 — Next steps (rolling — carryover candidates only, no specific future-sprint tasks)

- `AD-RateLimits-Alerting-Webhook` (NEW) — push 80%/100% breaches to a tenant-configured webhook / Slack (the persisted log is the substrate; webhook is the notify layer); ~3-4 hr
- `AD-RateLimits-Alerting-Ack-Mute` (NEW) — admin ack / mute / resolve on an alert row (add `resolved_at` like `SLAViolation`) + filter resolved from the Recent alerts card; ~2 hr
- `AD-Quotas-Alerting-Template` (NEW) — the Sprint 57.62 pattern (write-through detection → idempotent alert upsert → GET → polling card) is reusable for Quotas usage alerts (the Quotas usage card already exists from 57.56); ~3 hr
- `AD-RepoHealth-Orphaned-Unmerged-Sweep` (NEW — Q2 lesson) — add a Day-0 `git status --short` scan for `AA`/`UU`/`DD` markers to the 三-Prong (catch orphaned conflicts at sprint start, not the Day-1 commit gate); ~0.5 hr to codify
- `AD-AgentFactor-DesignDecisions-Below-Band-Watch` (broadened from 57.61 — Q4) — cross-shape: 3rd consecutive `-design-decisions` below band → tighten 0.65 → 0.55
- 57.61 hygiene carryovers CONTINUE: `AD-RateLimits-DuplicateResource-Validation` (~1 hr) · `AD-RateLimits-SyntaxValidation-ClientSide-Polish` (~2 hr) · `AD-RateLimits-Parser-Extract-Shared-Predicate` (~2-3 hr)
- `AD-AgentFactor-Tier-3-MixedBundle-Mechanical-Tighten-0.45-Validation` (DEFERS again — 57.62 was single-domain, not a multi-track bundle) · `AD-MediumBackend-AICadence-Recalibration` (CONTINUES — needs human-factor data) · `AD-Mypy-WholeDir-Conftest-Collision` (CONTINUES — Phase 58+; CI runs `mypy src/` unaffected)
- `AD-AgentDelegate-DevStack-Precheck` (CLOSED this sprint — applied at Day 0; parent pre-started Postgres+Redis before delegating)

## Q6 — Phase 58.x RateLimits arc completeness (sprint-specific topic)

The RateLimits subsystem now **enforces** (57.58 middleware + Cat 2 gate), **persists usage** (57.59 two-table split), **single-sources config** (57.60 meta_data cleanup), **fail-loud-validates writes** (57.61 PUT 422), and **alerts on breach** (57.62 this — durable 80% log + GET + admin surface, captured even when unwatched). The arc:

- **57.57** WRITE-side ship — PUT endpoint + composite-replace
- **57.58** RuntimeEnforcement — middleware + Cat 2 gate + Redis counter
- **57.59** Potemkin Migration — two-table split (config + usage; AP-4 closed)
- **57.60** MetaData Cleanup — config single-source, 0 transitional fallback
- **57.61** SyntaxValidation — PUT-time 422 closes the silent-drop gap
- **57.62** Alerting (this) — durable 80%-threshold alert log + GET + QuotasTab surface

Remaining RateLimits items (Webhook / Ack-Mute / DuplicateResource / ClientSide-Polish / Parser-Extract / Quotas-Alerting-Template) are feature additions + code-hygiene, not architectural debt. The storage layer (57.59-60) + write validation (57.61) + alert capture (57.62) are clean.

## Q7 — Design Note Extract (spike sprint only) — **N/A SKIP**

Sprint 57.62 is a feature-ship sprint (durable alerting on an established subsystem), NOT a spike into a new domain. No design note required (11th consecutive Q7 N/A SKIP across the RateLimits + Tenant-settings ship/refactor sprints).
