# Sprint 55.4 — Checklist

[Plan](./sprint-55-4-plan.md)

> **Note**: Per **AD-Lint-2** (Sprint 55.3), per-day "Estimated X hours" headers dropped from this template. Sprint-aggregate estimate in plan §Workload only. Day-level actuals → progress.md.
>
> Per **AD-Plan-2** (Sprint 55.3), every plan §File Change List entry was Day-0 path-verified (Glob-checked exists for edits / not-exist for creates). 7 paths verified ✓ in plan.

---

## Day 0 — Setup + Day-0 探勘 + Plan/Checklist Drafting

- [x] **Working tree clean verified on main `a7724261`**
  - DoD: `git status --short` returns empty
- [x] **Feature branch created**
  - Branch: `feature/sprint-55-4-audit-cycle-B-C`
- [x] **Day-0 探勘 grep (AD-Plan-1 + AD-Plan-2 self-applied)**
  - 4 grep + 5 Glob + 1 Bash wc
  - Drift findings catalogued: D1 (all 5 classes exist) / D2 (tool_guardrail.py:129 TODO marker) / D3 (test_redis_budget_store.py exists 149 lines)
- [x] **Read 55.3 plan template**
  - 13 sections / Day 0-4 confirmed
- [x] **Write `sprint-55-4-plan.md`**
  - 13 sections mirror 55.3
  - 5 ADs detailed
- [x] **Write `sprint-55-4-checklist.md`** (this file)
- [ ] **Write Day 0 `progress.md` entry**
  - Path: `docs/03-implementation/agent-harness-execution/phase-55/sprint-55-4/progress.md`
- [ ] **Commit Day 0** (plan + checklist + progress)
  - Commit: `chore(docs, sprint-55-4): Day 0 plan + checklist + progress`

---

## Day 1 — AD-Cat8-1 stamp + AD-Cat8-3 narrow Option C [revised per D4-D8 + Selection D]

### AD-Cat8-1 — Verification Stamp (no new test code per D4)

- [x] **Read existing `test_redis_budget_store.py`** (149 lines, 9 tests, fakeredis)
- [x] **Verify coverage** — `_redis_store.py` 16/16 stmts = **100% line coverage**;9/9 tests PASS in 0.52s
- [x] **D4 catalog** — AD-Cat8-1 实质 closed by 53.3 Day 4;Sprint 55.4 = verification stamp only
- [x] **Add 1-line stamp comment to test file header** (Sprint 55.4 verification stamp)

### AD-Cat8-3 — Narrow Option C (loop.py only;no schema change)

- [x] **Read `loop.py:1072` synthetic site + `_handle_tool_error:258-304`** — D5/D7/D8 confirmed
- [x] **Read `policy.py:140-176`** — `classify_by_string()` mechanism (53.3 US-9) confirmed
- [x] **Read `executor.py:204-223`** — `error_class = f"{type(exc).__module__}.{type(exc).__name__}"` confirmed
- [x] **Edit `_handle_tool_error()` signature** — add `error_class_str: str | None = None` param
- [x] **Edit `_handle_tool_error()` classify path** — when `error_class_str` provided, use `classify_by_string()` instead of `classify(error)`
- [x] **Edit caller at L1074** — pass `error_class_str=result.error_class`
- [x] **Update file header Modification History** (per AD-Lint-3 1-line MHist)
- [x] **Add `classify_by_string` default to ErrorPolicy ABC** (mypy strict required;non-breaking;default FATAL)
- [x] **Add 3 unit tests** to new `test_handle_tool_error.py`:
  - test_handle_tool_error_with_error_class_str_uses_classify_by_string ✓
  - test_handle_tool_error_without_error_class_str_uses_mro_classify (regression) ✓
  - test_handle_tool_error_unknown_class_str_returns_fatal ✓
- [x] **Run tests**: 3/3 PASS in 0.26s;941 passed full agent_harness regression
- [ ] **Commit AD-Cat8-1 + AD-Cat8-3 (combined)**
  - Commit: `fix(orchestrator-loop, error-handling, sprint-55-4): close AD-Cat8-1 stamp + AD-Cat8-3 narrow Option C`

### Day 1 Wrap

- [x] **Update progress.md Day 1 entry** — cover: D4-D8 drift catalog + Selection D rationale + AD-Cat8-2 deferred to 55.5 + Option C narrow scope
- [x] **Lint chain**: black ✓ / isort ✓ / flake8 ✓ / mypy --strict ✓ / 7 V2 lints ✓

---

## Day 2 — AD-Cat9-5 ToolGuardrail Session Counter (promoted per Selection D)

> **AD-Cat8-2 deferred to 55.5 per D6** — `loop.py:194/245` retry_policy 完全 dead state;wire-up 需 dedicated retry-with-backoff design sprint,不適合 audit cycle Group。

### AD-Cat9-5 — ToolGuardrail max-calls-per-session Counter

- [x] **Read `tool_guardrail.py:120-150`** — understand current counter logic (TODO at L129 confirmed in Stage 2.3)
- [x] **Read `capability_matrix.py`** — `max_calls_per_session: int = 0` field already exists ✓
- [x] **Decide storage: in-memory** (per Selection D 紀律;single-instance scope;Redis multi-instance tracked separately)
- [x] **Implement session counter**
  - Replace TODO at L129 with pre-increment + check impl
  - `__init__`: `self._call_counters: dict[tuple[str, str], int] = {}`
  - On check: when `rule.max_calls_per_session > 0` AND session_id present → pre-increment + check `new > max → BLOCK` else write back
  - Missing session_id → fail-open (documented; over-blocking unauthenticated harms availability)
- [x] **Add 4 tests to `test_tool_guardrail.py`**
  - test_max_calls_under_cap_passes ✓
  - test_max_calls_at_cap_passes (3/3 last allowed) ✓
  - test_max_calls_over_cap_blocks (4th of 3 max → BLOCK + HIGH risk) ✓
  - test_max_calls_per_session_isolation (cross-session independent) ✓
- [x] **Verify**: `grep "TODO(53.4)" backend/src/agent_harness/guardrails/tool/tool_guardrail.py` → 0 hits ✓
- [ ] **Commit AD-Cat9-5**
  - Commit: `feat(guardrails, sprint-55-4): close AD-Cat9-5 (session call-counter)`

### AD-Cat9-6 — WORMAuditLog Real-DB Integration Tests

- [x] **Read `worm_log.py`** (188 lines) + `chain_verifier.py` + Migration 0005
- [x] **Write `test_worm_log_db_integration.py`** (5 tests) ✓
  - Test 1: Hash chain links across 3 appends ✓
  - Test 2: UPDATE attempt → trigger blocks (DBAPIError) ✓
  - Test 3: DELETE attempt → trigger blocks (with SAVEPOINT for post-fail SELECT) ✓
  - Test 4: verify_chain on 100 rows → valid=True ✓
  - Test 5: Two sequential appends → chain extends (concurrent rephrased per D10) ✓
- [x] **Use db_session fixture + monkey-patch commit→flush + close→no-op** ✓
- [x] **Run tests**: 5/5 PASS in 0.52s;950 passed full regression
- [ ] **Commit AD-Cat9-6**
  - Commit: `test(guardrails, sprint-55-4): close AD-Cat9-6 (WORM real-DB integration)`

### Day 3 Wrap

- [x] **Update progress.md Day 3 entry** — 1 commit + drift findings D9/D10
- [x] **Lint chain**: 7 V2 lints + mypy strict + flake8 all green

---

## Day 4 — Retrospective + Closeout

- [ ] **Verify all 4 ADs closed** (acceptance criteria;AD-Cat8-2 deferred to 55.5 per D6 Selection D)
  - AD-Cat8-1: 100% line coverage stamp (verified 9 tests, 16/16 stmts) ✓
  - AD-Cat8-3 (narrow Option C): _handle_tool_error error_class_str + classify_by_string + 3 tests green
  - AD-Cat9-5: tool_guardrail.py:129 TODO replaced + 4 tests green
  - AD-Cat9-6: 4-6 real-DB integration tests green
- [ ] **Run full pytest baseline**
  - Target: 1434 → ≥1445 (+11 minimum;was ≥+13 with AD-Cat8-2 included)
- [ ] **Run full lint chain**
  - black + isort + flake8 + mypy --strict + 7 V2 lints
- [ ] **LLM SDK leak check** — 0
- [ ] **Compute calibration ratio** (AD-Sprint-Plan-4 1st application)
  - Sum actual hours Day 0-4
  - Ratio = actual / committed
  - Document in retro Q2
- [ ] **Catalog final drift findings** (D1-Dn)
- [ ] **Write `retrospective.md`** (6 必答 Q1-Q6)
  - Q1 What went well
  - Q2 What didn't go well + ratio + scope-class verification
  - Q3 Generalizable lessons
  - Q4 Audit Debt deferred (carryover candidates for 55.5+)
  - Q5 Next steps (rolling planning — 55.5 candidate scope only)
  - Q6 AD-Sprint-Plan-4 medium-backend class first validation + recommendations
- [ ] **Update `claudedocs/6-ai-assistant/prompts/SITUATION-V2-SESSION-START.md`**
  - §8 close 5 ADs
  - Add new ADs (if any)
  - §9 milestones row +Sprint 55.4 (V2 22/22 unchanged — audit cycle)
  - Footer Last Updated + Update history +1 row
- [ ] **Update memory**
  - `memory/project_phase55_4_audit_cycle_2.md` — new
  - `memory/MEMORY.md` — index +1 line
- [ ] **Commit Day 4**
  - Commit: `docs(retro, sprint-55-4): retrospective + 5 AD closure summary`
- [ ] **Push branch**
- [ ] **Open PR**
  - Title: `Sprint 55.4: Audit Cycle Mini-Sprint #2 — close 5 ADs (Groups B + C)`
- [ ] **Watch CI green** — apply paths-filter workaround for Frontend E2E if needed (per AD-CI-5)
- [ ] **Merge PR** — solo-dev policy, review_count=0
- [ ] **Closeout PR for SHA fill-in** if needed
- [ ] **Final verify on main** — clean

---

## Tracker

| AD | Status | Tests Added | Commit |
|----|--------|-------------|--------|
| AD-Cat8-1 | ⏳ stamp pending | 0 (already 100% via 53.3) | — |
| AD-Cat8-2 | 🚧 deferred to 55.5 (D6) | — | — |
| AD-Cat8-3 (narrow Option C) | ⏳ Day 1 in progress | 3 | — |
| AD-Cat9-5 | ⏳ Day 2 pending | 4 | — |
| AD-Cat9-6 | ⏳ Day 3 pending | 4-6 | — |
| **Total** | **0/4 closed** (1 deferred) | **0/+11** | — |

---

**Status**: Day 0 — Plan + Checklist + progress.md drafting (this commit pending). Pending user approval before Day 1 code starts.
