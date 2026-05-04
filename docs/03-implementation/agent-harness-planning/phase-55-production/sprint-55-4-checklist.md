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

## Day 1 — AD-Cat8-1 + AD-Cat8-3

### AD-Cat8-1 — RedisBudgetStore + fakeredis Integration Test

- [ ] **Read existing `tests/integration/agent_harness/error_handling/test_redis_budget_store.py`** (149 lines)
- [ ] **Verify fakeredis vs real Redis usage**
  - If real Redis → migrate to fakeredis
  - If fakeredis already → identify coverage gaps
- [ ] **Add coverage gaps**
  - consume_budget reduces remaining
  - restore_budget undoes consumption
  - get_remaining returns current
  - Concurrent access (2 simultaneous consume → no double-count)
  - TTL expiry behavior
- [ ] **Coverage target**: ≥80% line coverage on `_redis_store.py`
  - DoD: `pytest --cov=src/agent_harness/error_handling/_redis_store.py` ≥ 80%
- [ ] **Commit AD-Cat8-1**
  - Commit: `test(error-handling, sprint-55-4): close AD-Cat8-1 (RedisBudgetStore + fakeredis)`

### AD-Cat8-3 — Soft-Failure Path Preserve Original Exception Type

- [ ] **Read `agent_harness/error_handling/terminator.py`** — find synthesize call site
- [ ] **Decide Option A vs B**
  - A: `raise OriginalExceptionType(str(e)) from e`
  - B: `SoftFailureError(original=e)` wrapping with __cause__
  - Document decision in progress.md Day 1 entry
- [ ] **Refactor terminator.py** per decision
- [ ] **Add 3 type-preservation tests** to `test_terminator.py`
  - NetworkTimeoutError preserved
  - ValueError preserved
  - Generic Exception preserved
- [ ] **Run tests**: `pytest tests/unit/agent_harness/error_handling/test_terminator.py`
- [ ] **Commit AD-Cat8-3**
  - Commit: `fix(error-handling, sprint-55-4): close AD-Cat8-3 (preserve Exception type)`

### Day 1 Wrap

- [ ] **Update progress.md Day 1 entry**
  - Cover: 2 commits + Option A/B decision + new drift findings (if any)
- [ ] **Lint chain**: black ✓ / isort ✓ / flake8 ✓ / mypy --strict ✓ / 7 V2 lints ✓

---

## Day 2 — AD-Cat8-2 RetryPolicyMatrix Wire to AgentLoop

- [ ] **Read `agent_harness/error_handling/retry.py`** — confirm RetryPolicyMatrix interface
- [ ] **Read `agent_harness/orchestrator_loop/agent_loop.py`** — find current error-path code
- [ ] **Identify wire-point**
  - LLM call retry-eligible failures
  - Tool call retry-eligible failures
- [ ] **Implement wire**
  - AgentLoop accepts `retry_policy: RetryPolicyMatrix | None = None` constructor param
  - On retry-eligible exception → consult policy → backoff via asyncio.sleep
  - Max retries enforced;exceeded → error path continues
- [ ] **Write `tests/integration/agent_harness/orchestrator_loop/test_agent_loop_retry_integration.py`** (new)
  - Test 1: Transient error → retry success
  - Test 2: 5xx error → 3-retry backoff
  - Test 3: Non-retry-eligible → immediate fail
- [ ] **Run all error_handling + orchestrator_loop tests**
  - DoD: existing tests + 3 new integration tests all green
- [ ] **Update progress.md Day 2 entry**
- [ ] **Commit AD-Cat8-2**
  - Commit: `feat(orchestrator-loop, error-handling, sprint-55-4): close AD-Cat8-2 (retry wire)`

---

## Day 3 — AD-Cat9-5 + AD-Cat9-6

### AD-Cat9-5 — ToolGuardrail max-calls-per-session Counter

- [ ] **Read `tool_guardrail.py:120-150`** — understand current counter logic
- [ ] **Read `capability_matrix.py`** — verify `max_calls_per_session` field exists or needs adding
- [ ] **Decide storage: in-memory vs Redis**
  - In-memory acceptable for single-instance
  - Redis for multi-instance future
  - Document decision in progress.md Day 3
- [ ] **Implement session counter**
  - Replace TODO at L129 with impl
  - On `check(tool_name, trace_context)`: read max-calls, increment counter, BLOCK if over
- [ ] **Add 4 tests to `test_tool_guardrail.py`**
  - Under-cap → ALLOW
  - At-cap → ALLOW (last call)
  - Over-cap → BLOCK with reason
  - Different sessions independent (tenant isolation)
- [ ] **Verify**: `grep "TODO(53.4)" backend/src/agent_harness/guardrails/tool/tool_guardrail.py` returns 0
- [ ] **Commit AD-Cat9-5**
  - Commit: `feat(guardrails, sprint-55-4): close AD-Cat9-5 (session call-counter)`

### AD-Cat9-6 — WORMAuditLog Real-DB Integration Tests

- [ ] **Read `worm_log.py`** + existing `test_worm_log.py` (195 lines unit)
- [ ] **Write `tests/integration/agent_harness/guardrails/test_worm_log_db_integration.py`** (new)
  - Test 1: Insert sequence → hash chain links correctly
  - Test 2: UPDATE attempt → DB trigger blocks (per 0005 migration)
  - Test 3: DELETE attempt → DB trigger blocks
  - Test 4: verify_chain on 100+ rows → no break
  - Test 5: Two concurrent inserts → both succeed, chain extends
  - Optional Test 6: pagination 1000+ rows
- [ ] **Use db_session fixture** + monkey-patch commit→flush per testing.md
- [ ] **Run tests**: `pytest tests/integration/agent_harness/guardrails/test_worm_log_db_integration.py`
- [ ] **Commit AD-Cat9-6**
  - Commit: `test(guardrails, sprint-55-4): close AD-Cat9-6 (WORM real-DB integration)`

### Day 3 Wrap

- [ ] **Update progress.md Day 3 entry** — 2 commits + storage decision + drift findings
- [ ] **Lint chain**: 7 V2 lints + mypy strict + flake8 all green

---

## Day 4 — Retrospective + Closeout

- [ ] **Verify all 5 ADs closed** (acceptance criteria)
  - AD-Cat8-1: RedisBudgetStore ≥80% coverage
  - AD-Cat8-2: AgentLoop retry_policy wired + 3 tests green
  - AD-Cat8-3: ErrorTerminator preserves type + 3 tests green
  - AD-Cat9-5: tool_guardrail.py:129 TODO replaced + 4 tests green
  - AD-Cat9-6: 4-6 real-DB integration tests green
- [ ] **Run full pytest baseline**
  - Target: 1434 → ≥1447 (+13 minimum)
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
| AD-Cat8-1 | ⏳ pending | 3-4 | — |
| AD-Cat8-2 | ⏳ pending | 3 | — |
| AD-Cat8-3 | ⏳ pending | 3 | — |
| AD-Cat9-5 | ⏳ pending | 4 | — |
| AD-Cat9-6 | ⏳ pending | 4-6 | — |
| **Total** | **0/5 closed** | **0/+13** | — |

---

**Status**: Day 0 — Plan + Checklist + progress.md drafting (this commit pending). Pending user approval before Day 1 code starts.
