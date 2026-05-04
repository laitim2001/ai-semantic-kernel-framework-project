# Sprint 53.7 — Progress Log

**Plan**: [`../../../agent-harness-planning/phase-53-7-audit-cleanup-cat9-quickwins/sprint-53-7-plan.md`](../../../agent-harness-planning/phase-53-7-audit-cleanup-cat9-quickwins/sprint-53-7-plan.md)
**Checklist**: [`../../../agent-harness-planning/phase-53-7-audit-cleanup-cat9-quickwins/sprint-53-7-checklist.md`](../../../agent-harness-planning/phase-53-7-audit-cleanup-cat9-quickwins/sprint-53-7-checklist.md)
**Branch**: `feature/sprint-53-7-audit-cleanup-cat9-quickwins`
**Start date**: 2026-05-04

---

## Day 0 — Setup + Carryover Verify + Calibration Pre-Read (2026-05-04)

### Time

- Estimated: 1.5-2 hr
- Actual: ~0.5 hr
- Banked: ~1-1.5 hr (cause: 53.6 retro just-read; fresh context; no need to re-derive carryover sources)

### 0.1 Branch + plan + checklist commit ✅

- Pre-branch state: main clean (only `phase-53-7-*` untracked dir)
- Branch created: `feature/sprint-53-7-audit-cleanup-cat9-quickwins`
- Commit: `5a2464fd` — `docs(plan, sprint-53-7): plan + checklist for audit cleanup + Cat 9 quick wins (9 AD bundle)`
- Push: branch tracking `origin/feature/sprint-53-7-audit-cleanup-cat9-quickwins` ✅
- 2 files / 896 insertions

### 0.2 Carryover source verify ✅

All 9 AD trace to source retrospectives confirmed open:

| AD | Source retro | Line ref | Status |
|----|--------------|---------|--------|
| AD-Lint-1 | 53.6 retro | Q4 line 64 + Q6 line 100 | ✅ open, target 53.7 |
| AD-Test-1 | 53.6 retro | Q4 line 66 + Q6 line 101 | ✅ open, target 53.7 |
| AD-Sprint-Plan-1 | 53.6 retro | Q6 line 102 | ✅ open, target plan template update |
| AD-CI-4 | 53.2.5 retro | line 79 | ✅ open, target plan template / sprint-workflow.md |
| AD-Hitl-8 | 53.4 retro | Q6 line 106 | ✅ open, target audit cycle |
| AI-22 | 52.6 retro line 205 + 53.2.5 line 80 | ✅ open, target 53.x or 54.x bundle |
| AD-Cat9-7 | 53.3 retro | Q6 line 80 | ✅ open, target Phase 54.x (advancing) |
| AD-Cat9-8 | 53.3 retro | Q6 line 81 | ✅ open, target Phase 53.4 (overdue) |
| AD-Cat9-9 | 53.3 retro | Q6 line 82 | ✅ open, target Phase 53.4 / future |

### 0.3 Calibration multiplier pre-read ✅

53.6 retro Q2 explicitly states:
> "Same ~50% over-estimate pattern as Sprint 53.4 + 53.5. Under-estimate consistent: ~7-14 hr banked across 3 sprints. Calibration follow-up: starting Sprint 53.7+, default new sprint estimates to 50-60% of bottom-up sum."

53.7 plan §Workload applies multiplier 0.55 (mid-band):
- Bottom-up est: ~17 hr
- Calibrated commit: ~9 hr (0.55 × 17)
- Day 4 retrospective Q2 必驗 actual / committed ratio；若 delta > 30% 則 AD-Sprint-Plan-1 round 2

### 0.4 SSE serializer scope check ✅

- Loop event yields: 10 (`grep "yield .*Event\(\|yield .*Triggered\(" backend/src/agent_harness/orchestrator_loop/loop.py | wc -l`)
- SSE isinstance branches: 12 (`grep -c "isinstance(event," backend/src/api/v1/chat/sse.py`)
- 12 > 10 → coverage with margin; 53.7 USs not introducing new LoopEvent ✅

### 0.5 Pre-flight verify ✅

- pytest collect: **1089 tests collected** (matches main HEAD `f4a1425f` baseline 1085 passed + 4 skipped = 1089 = 53.6 closeout)
- 6 V2 lint baseline timings (pre-Day 1 wrapper):

| Lint | Args | Time |
|------|------|------|
| check_ap1_pipeline_disguise.py | `--root backend/src/agent_harness` | 0.054 s |
| check_promptbuilder_usage.py | `--root backend/src/agent_harness` | 0.126 s |
| check_cross_category_import.py | (auto) | 0.113 s |
| check_duplicate_dataclass.py | (auto) | 0.108 s |
| check_llm_sdk_leak.py | (auto) | 0.088 s |
| check_sync_callback.py | (auto) | 0.175 s |
| **Total** | | **0.66 s** |

Wrapper (Day 1 US-1.3) target: ≤ 1 s wallclock + per-script line summary.

### Drift Findings (Day 0)

| ID | Description | Action |
|----|-------------|--------|
| **D1** | `check_ap1_pipeline_disguise.py --root backend/src/agent_harness` reports "no orchestrator_loop dir found; skipping AP-1 check" — but `backend/src/agent_harness/orchestrator_loop/` clearly exists with `loop.py`, `events.py`, `_abc.py`. Path resolution is wrong (likely script joins `--root` with literal `orchestrator_loop` but mismatching cwd vs file location semantics). Result: AP-1 silently passes in CI without running real check (false-green). Pre-existing bug, not introduced by 53.7. | Day 1 US-1.3 wrapper work to investigate + fix path resolution as part of AD-Lint-1 (extends scope slightly). If complex, log as AD-Lint-1-followup and document in retrospective Q4. |

### Files touched (Day 0)

- New: `docs/03-implementation/agent-harness-planning/phase-53-7-audit-cleanup-cat9-quickwins/sprint-53-7-plan.md` (+523 lines)
- New: `docs/03-implementation/agent-harness-planning/phase-53-7-audit-cleanup-cat9-quickwins/sprint-53-7-checklist.md` (+373 lines)
- New: `docs/03-implementation/agent-harness-execution/phase-53-7-audit-cleanup-cat9-quickwins/sprint-53-7-audit-cleanup-cat9-quickwins/progress.md` (this file)

### Next — Day 1

US-1 Plan/Process Improvements (closes 4 AD):
- 1.1 AD-Sprint-Plan-1 — sprint-workflow.md calibration multiplier sub-section (Step 1)
- 1.2 AD-CI-4 — sprint-workflow.md §Common Risk Classes section (3 classes minimum)
- 1.3 AD-Lint-1 — `scripts/lint/run_all.py` wrapper + Pre-Push doc + investigate D1 path resolution bug
- 1.4 AD-Test-1 — `.claude/rules/testing.md` §Module-level Singleton Reset Pattern

Estimated 2.5-3 hr; calibrated target ~1.5-2 hr after Day 0 banking.

---

## Day 1 — US-1 Plan/Process Improvements (2026-05-04)

### Time

- Estimated: 2.5-3 hr (calibrated target ~1.5-2 hr post Day 0 banking)
- Actual: ~1.5 hr
- Banked: ~1-1.5 hr (cause: tooling fixes inline + reusing 53.6 patterns)

### 1.1 AD-Sprint-Plan-1 — Calibration multiplier sub-section ✅

- File: `.claude/rules/sprint-workflow.md`
- Added §Workload Calibration sub-section under Step 1
- Three-segment commitment form `bottom-up X hr → calibrated Y hr (multiplier Z)`
- Default multiplier 0.5-0.6 (mid-band 0.55) backed by 53.4-53.6 retrospective Q2 evidence
- When-to-adjust criteria + Day 4 retro Q2 verification rule

### 1.2 AD-CI-4 — §Common Risk Classes section ✅

- Added new H2 section between Step 5 and Change Record Conventions
- 3 risk classes: paths-filter (53.2.5 source) / mypy unused-ignore (52.6) / module singleton (53.6)
- Each entry: symptom + source + workaround + long-term fix + how-to-use guidance
- Catalog ready to grow as new classes emerge

### 1.3 AD-Lint-1 — run_all.py wrapper + 2 bonus bug fixes ✅

- New file: `scripts/lint/run_all.py` (129 lines after black format)
- LINTS list with correct per-script args:
  - check_ap1: `--root backend/src` (was wrong `backend/src/agent_harness` in 53.3-53.6 silently)
  - check_promptbuilder: explicit `--root backend/src/agent_harness` (defensive)
  - 4 others: auto-discover (no args)
- Output: per-script line `[OK ] script_name elapsed` + final aggregated `6/6 green`
- Sprint 53.7 D1 hunting uncovered **2 bonus bugs**:
  - **check_promptbuilder_usage.py**: `_default_root()` used `parents[1]` (= `<repo>/scripts/`) → produced non-existent path `<repo>/scripts/backend/src/agent_harness/` → silent fail when invoked without --root. Fixed to `parents[2]` (= repo root). Pre-53.7 callers escaped this by always passing explicit --root; run_all.py exposed it.
  - **check_ap1_pipeline_disguise.py**: returned 0 with "OK: no orchestrator_loop dir; skipping" when target_dir missing → mis-invocation produced false-greens. Changed to exit 2 with hint message.
- Both fixes have Modification History entries; both verified via re-run of run_all.py: 6/6 green in 0.77s
- Updated `.claude/rules/sprint-workflow.md` §Before Commit §Lint to reference `python scripts/lint/run_all.py`

### 1.4 AD-Test-1 — testing.md §Module-level Singleton Reset Pattern ✅

- File: `.claude/rules/testing.md`
- Inserted between §Mocking Guidelines and §Coverage Requirements
- Sections: When needed / When to apply / Required pattern (autouse fixture template) / Scope rules / Known singletons catalog / Anti-patterns / Long-term direction
- Catalog seeded with `service_factory.reset_service_factory()` (53.6 source)
- Catalog row format ready for additions as new singletons emerge
- Modification History updated

### 1.5 Day 1 sanity ✅

- mypy --strict on 3 touched .py files: Success no issues
- black: 2 files reformatted (run_all.py + check_ap1) → re-checked clean
- flake8 + isort: clean on touched files
- run_all.py self-test: **6/6 green in 0.77s**, exit 0
- Backend full pytest: **1085 passed / 4 skipped** (matches main HEAD baseline)

### Drift Findings (Day 1)

| ID | Description | Action |
|----|-------------|--------|
| **D2** | check_promptbuilder_usage.py `_default_root()` `parents[1]` bug — would fail when invoked without --root from project root | Fixed inline (Modification History added) |
| **D3** | check_ap1_pipeline_disguise.py "OK: skipping" silent-pass when target_dir missing — mis-invocation false-green | Fixed inline (exit 2 + hint message) |

Both D2 + D3 are sub-fixes inside AD-Lint-1 closure and don't need separate carryover AD entries (folded into the wrapper PR scope).

### Files touched (Day 1)

- New: `scripts/lint/run_all.py`
- Modified: `scripts/lint/check_ap1_pipeline_disguise.py` (silent-skip fix)
- Modified: `scripts/lint/check_promptbuilder_usage.py` (parents bug fix)
- Modified: `.claude/rules/sprint-workflow.md` (1.1 + 1.2 + Pre-Push update)
- Modified: `.claude/rules/testing.md` (1.4)

### Next — Day 2

Group B infra cleanup (closes AD-Hitl-8 + AI-22 + Playwright required_check):
- 2.1 US-2 — Alembic migration `add_escalated_to_status_check` + integration test
- 2.2 US-3 — Branch protection PATCH 5 required + verify
- 2.3 US-3 — AI-22 enforce_admins chaos test (dummy red PR + admin merge attempt)

Estimated 1.5-2 hr; calibrated target ~1 hr after Day 0+1 banking.

---

## Day 2 — US-2 DB Constraint + US-3 Branch Protection + AI-22 Chaos Test (2026-05-04)

### Time

- Estimated: 1.5-2 hr (calibrated target ~1 hr post Day 0+1 banking)
- Actual: ~2 hr (D5 regression + D6 mypy fix iteration cost ~30 min)
- Banked: ~0 hr (used buffer for D5 + D6 fixes)

### 2.1 US-2 — AD-Hitl-8 DB CHECK constraint ✅

- **Drift D4**: Plan assumed table `hitl_approvals` + DROP+ADD existing constraint. Actual: table is `approvals` + no prior CHECK existed → simpler ADD-only migration.
- **Drift D5 (CRITICAL)**: Initial 4-value enum `('pending','approved','rejected','escalated')` broke `test_expire_overdue_transitions_pending_to_expired` because HITL state machine includes `expired` (per Approval ORM docstring "pending → approved | rejected | expired"). **Fix**: extended constraint to 5 values; integration test parametrize updated; regression resolved.
- **Drift D6**: mypy --strict caught 5 missing-annotation errors in new test file. Fixed with `UUID` import + `_make_approval` arg type + `seeded_session` return type + per-test arg annotations.
- New: `backend/src/infrastructure/db/migrations/versions/0011_approvals_status_check.py`
  - Chain `0010_pg_partman → 0011_approvals_status_check`
  - upgrade(): `ADD CONSTRAINT approvals_status_check CHECK status IN 5 values`
  - downgrade(): `DROP CONSTRAINT IF EXISTS approvals_status_check`
- New: `backend/tests/integration/infrastructure/db/test_approval_status_constraint.py` (6 cases)
  - test_status_escalated_is_accepted
  - test_status_existing_values_still_accepted[pending|approved|rejected|expired] (parametrize ×4)
  - test_status_unknown_string_is_rejected (asserts IntegrityError + constraint name in error msg)
- alembic upgrade + downgrade -1 + upgrade head 三遍 clean
- Verify: pytest 6 passed in 0.38s
- Backend full pytest: **1091 passed / 4 skipped / 0 fail** (+6 from main 1085 baseline)

### 2.2 US-3 — Branch protection PATCH ✅

- **Drift D7**: Plan said "Playwright E2E" context. Actual: workflow `Playwright E2E` job `e2e` has display name `Frontend E2E (chromium headless)`. Required contexts use **job names** not workflow names.
- Pre-PATCH 4 contexts: Lint+Type+Test (PG16) / Backend E2E Tests / E2E Test Summary / v2-lints
- PATCH: `echo '{"strict":true,"contexts":[5 names]}' | gh api repos/.../required_status_checks -X PATCH --input -`
- Post-PATCH GET shows 5 contexts confirmed

### 2.3 US-3 — AI-22 enforce_admins chaos test ✅ PASSED

- Dummy red PR #75 (`chore/chaos-test-enforce-admins` from main HEAD f4a1425f)
- `backend/tests/unit/test_chaos_dummy_53_7.py` with `assert 1 == 2`
- Non-admin merge: blocked — "the base branch policy prohibits the merge"
- Admin merge (KEY TEST): blocked — "GraphQL: 5 of 5 required status checks have not succeeded: 3 expected. (mergePullRequest)"
- **Critical evidence**: enforce_admins=true actively rejects --admin bypass at GitHub API layer
- Cleanup: `gh pr close 75 --delete-branch` (PR + remote branch deleted)
- Documented: `chaos-test-enforce-admins.md` with verbatim error messages

### Drift Findings (Day 2)

| ID | Description | Action |
|----|-------------|--------|
| D4 | Plan assumed table=hitl_approvals + DROP+ADD; actual=approvals + no prior CHECK | Migration revised to ADD-only |
| D5 | Initial 4-value enum missed 'expired' → broke test_expire_overdue | Extended to 5 values; regression resolved |
| D6 | mypy --strict caught 5 missing annotations | Fixed with UUID + return-type + arg-type |
| D7 | Plan said "Playwright E2E" context; actual is "Frontend E2E (chromium headless)" | PATCH used correct job display name |

### Files touched (Day 2)

- New: `backend/src/infrastructure/db/migrations/versions/0011_approvals_status_check.py`
- New: `backend/tests/integration/infrastructure/db/test_approval_status_constraint.py`
- New: `docs/.../sprint-53-7-audit-cleanup-cat9-quickwins/chaos-test-enforce-admins.md`
- Admin op (not git-tracked): branch protection PATCH on main (5 required contexts)

### Next — Day 3

Group C Cat 9 hardening (closes AD-Cat9-7 + AD-Cat9-8 + AD-Cat9-9):
- 3.1 US-4 — AD-Cat9-8 jailbreak regex FP fix (negative-lookahead for meta-discussion)
- 3.2 US-4 — AD-Cat9-7 _audit_log_safe FATAL escalation (raise WORMAuditWriteError)
- 3.3 US-5 — AD-Cat9-9 PII red-team fixture 50→200 cases + SLO test

Estimated 3-4 hr; calibrated target ~2 hr.
