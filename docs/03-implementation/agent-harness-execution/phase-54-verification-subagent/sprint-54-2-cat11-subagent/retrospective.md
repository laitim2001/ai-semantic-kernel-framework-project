# Sprint 54.2 — Cat 11 Subagent + AD-Cat10-Obs-1 — Retrospective

**Sprint**: 54.2 (Phase 54 closure — final 範疇 sprint before Phase 55)
**Goal**: Cat 11 (Subagent Orchestration) Level 0 → Level 4 + AD-Cat10-Obs-1 closure
**Result**: ✅ V2 19/22 → 20/22 (91%) main progress advance
**Branch**: `feature/sprint-54-2-cat11-subagent`
**Date completed**: 2026-05-04

---

## Q1 — Sprint Goal Achieved?

**Yes — all 5 USs delivered with main-flow validation.**

### Cat 11 Level 4 evidence

```bash
$ python -c "from agent_harness.subagent import (
    DefaultSubagentDispatcher, BudgetEnforcer, MailboxStore,
    ForkExecutor, AsToolWrapper, TeammateExecutor, HandoffExecutor,
    make_task_spawn_tool, make_handoff_tool)
print('Cat 11 Level 4 imports OK')"
Cat 11 Level 4 imports OK

$ pytest tests/unit/agent_harness/subagent/ -q
46 passed in 0.20s   # = 11 budget + 4 dispatcher_init + 5 fork + 4 as_tool + 5 mailbox + 4 teammate + 3 handoff + 7 tools + 3 dispatcher round-trips
```

### AD-Cat10-Obs-1 closure evidence

```bash
$ pytest tests/unit/agent_harness/verification/test_observability.py -q
4 passed in 0.05s   # 4 verifier classes emit verifier.{name} spans under SpanCategory.VERIFICATION
```

### 5 USs status

| US | Deliverable | Tests | Status |
|----|------------|-------|--------|
| US-1 | BudgetEnforcer + DefaultSubagentDispatcher skeleton | 11 budget + 4 dispatcher_init | ✅ |
| US-2 | Fork + AsTool modes + AgentSpec | 5 fork + 4 as_tool | ✅ |
| US-3 | Teammate + Mailbox | 5 mailbox + 4 teammate | ✅ |
| US-4 | Handoff + dispatcher.handoff wired | 3 handoff | ✅ |
| US-5 | task_spawn / handoff tools + AD-Cat10-Obs-1 | 7 tools + 4 obs | ✅ |

### Worktree mode AP-6 verification

`grep -rn "worktree" backend/src/agent_harness/subagent/ → 0 matches` ✅ (V2 spec §範疇 11 explicitly omits worktree mode; AP-6 Hybrid Bridge Debt clean — no speculative implementation).

---

## Q2 — Estimated vs Actual + Calibration Multiplier 3rd Verification

### Hours

| Day | Bottom-up | Calibrated commit (×0.55) | Actual | Ratio |
|-----|-----------|---------------------------|--------|-------|
| Day 0 (探勘 + setup) | 1.5 | 0.8 | ~1.0 | 1.25 |
| Day 1 (US-1) | 3.5 | 1.9 | ~1.0 | 0.53 |
| Day 2 (US-2) | 4.0 | 2.2 | ~1.5 | 0.68 |
| Day 3 (US-3) | 5.0 | 2.75 | ~1.5 | 0.55 |
| Day 4 (US-4 + US-5 + closeout) | 8.5 | 4.7 | ~3.0 | 0.64 |
| **Total** | **22.5** | **12.4** | **~8.0** | **0.65** |

### Calibration Multiplier 3-Sprint Window

| Sprint | Predicted (committed) | Actual | Ratio |
|--------|----------------------|--------|-------|
| 53.7 (audit cycle) | 7.4 | 7.5 | 1.01 |
| 54.1 (Cat 10 Verification) | 10.2 | 7.0 | 0.69 |
| 54.2 (Cat 11 Subagent) | 12.4 | 8.0 | 0.65 |
| **3-sprint mean** | | | **0.78** |

**Verdict**: 3-sprint mean **0.78 is BELOW the stable [0.85, 1.20] band**. Per AD-Sprint-Plan-1 rule (53.7+ §Workload Calibration): "3+ consecutive sprints with `actual / committed < 0.7` → lower multiplier (e.g. 0.55 → 0.40)".

54.1 + 54.2 are 2 consecutive sub-0.7 ratios; 53.7 was 1.01. Strict reading says NOT 3 consecutive yet → keep 0.55. But the trend is clearly downward (1.01 → 0.69 → 0.65). Recommend a **conservative adjustment**:

- **Action**: lower multiplier to **0.50** for Phase 55 (mid-band between strict 0.55 and recommended 0.45)
- **Re-evaluate after**: 1 more sprint at 0.50; if ratio stays < 0.85, drop to 0.45
- **Track as**: AD-Sprint-Plan-2 (multiplier downward drift; revisit after 1 Phase 55 sprint)

---

## Q3 — What Went Well (≥ 3)

1. **Day 0 探勘 paid off (3rd time confirming pattern)**: 9 drifts catalogued in Day 0 (D1-D9) prevented misalignment. D1 (ABC has 3 unified methods, not 4) and D7 (SubagentHandle missing) would have caused mid-sprint refactor if discovered later.

2. **Skeleton-first scaffolding accelerated implementation**: US-1 ships dispatcher with NotImplementedError raises; US-2/3/4 fill in mode executors progressively. Each Day's tests build on prior Days' patterns. This pattern is now SOP — recommend formalizing in next checklist template.

3. **D8 simplification preserved 17.md single-source**: AgentLoop is NOT modified; subagent integration via tool_registry is cleaner and respects the Cat 1 owner. Phase 55+ may add SubagentSpawned/Completed event emission via hook, but the basic LLM-callable surface works without touching loop.py.

4. **Banked buffer effectively absorbed Day 4 drift cluster**: D18-D22 (5 drifts in Day 4 alone) were absorbed by Day 1+2+3 banked +2.95 hr. Total sprint completed 4.4 hr under commit.

---

## Q4 — What Can Improve (≥ 3 + Follow-up Action)

1. **Calibration multiplier 0.55 systematically over-budgets** (3-sprint trend ratio 0.78). Action: **drop to 0.50** for Phase 55 sprint 1 (re-evaluate after 1 sprint). Track as **AD-Sprint-Plan-2**.

2. **Tracer / MetricsEmitter ABC ergonomics**: The `_obs.py` helper pattern (verification_span async ctx mgr) is good but should be promoted to a shared utility. Repeating it for Cat 11 (subagent dispatch spans), Cat 8 (error handling spans), etc. = boilerplate. Action: **extract to `agent_harness/observability/helpers.py`** in Phase 55. Track as **AD-Cat12-Helpers-1**.

3. **Module docstring accumulation creates flake8 E501**: 4× E501 hit in Day 4 (D21) all from "Modification History" entries getting too verbose. Action: **shorten Modification History format** (`YYYY-MM-DD: scope (Sprint XX.Y)` 1 line max). Document in `.claude/rules/file-header-convention.md`. Track as **AD-Lint-3**.

4. **AS_TOOL mode / dispatch ABC mismatch surfaced late** (Day 0 D1-followup): Plan §US-2 designed for unified `dispatch()`; actual ABC has `spawn / wait_for / handoff` only. Day 0 探勘 caught this BEFORE coding — but the plan §Technical Spec dispatcher.py skeleton was misleading. Action: **Day-0 探勘 must verify ABC method signatures BEFORE plan §Technical Spec section is finalized** — i.e., grep ABC during plan drafting, not just before code starts. Update sprint-workflow.md §Step 1 to include this check.

---

## Q5 — V2 9-Discipline Self-Check

| # | Discipline | Status | Note |
|---|-----------|--------|------|
| 1 | Server-Side First | ✅ | All Cat 11 source files server-side; in-memory mailbox; no local file IO |
| 2 | LLM Provider Neutrality | ✅ | 0 SDK imports in subagent/ + verification/ (lint passed); ChatClient ABC throughout |
| 3 | CC Reference 不照搬 | ✅ | CC peer-pane (file-based) → V2 in-memory queues; CC worktree NOT implemented (per V2 spec); CC concept preserved, V2 implementation rewritten |
| 4 | 17.md Single-source | ✅ | Added AgentSpec (D7 partial closure; deferred SubagentHandle to Phase 55+); existing SubagentBudget/Mode/Result/SubagentDispatcher unchanged |
| 5 | 11+1 範疇歸屬 | ✅ | All Cat 11 code in `agent_harness/subagent/`; AD-Cat10-Obs-1 modifies 4 verifier classes within `agent_harness/verification/` (Cat 10 owner) — Cat 12 cross-cutting via Tracer ABC import |
| 6 | 04 anti-patterns | ✅ | AP-3 / AP-4 / AP-6 (worktree NOT implemented) / AP-8 (D14 + D17 ALLOWLIST justified) all clean |
| 7 | Sprint workflow | ✅ | Plan → checklist → Day 0 探勘 → Day 1/2/3/4 with progress.md updates each day; retrospective with 6 mandatory questions |
| 8 | File header convention | ✅ | All 8 new source + 4 new test files have File / Purpose / Category / Scope / Modification History |
| 9 | Multi-tenant rule | ✅ | Per-request DI dispatcher (no module singleton); mailbox per-session_id (cross-session isolation tested); tenant_id propagates via parent_session_id |

---

## Q6 — New Audit Debt + Phase 55 Candidate Scope

### New AD logged from 54.2

| ID | Type | Description | Target |
|----|------|------------|--------|
| **AD-Sprint-Plan-2** | Process | Calibration multiplier 0.55 systematically over-budgets (3-sprint mean 0.78). Lower to 0.50 for Phase 55; re-evaluate after 1 sprint. | Next plan template |
| **AD-Cat12-Helpers-1** | Code quality | Extract `verification_span` pattern to `observability/helpers.py` for cross-Cat reuse | Phase 55 |
| **AD-Lint-3** | Process | Shorten Modification History entries to 1 line max format to avoid recurring E501 | `.claude/rules/file-header-convention.md` update |
| **AD-Cat11-Multiturn** | Feature | Phase 55+: TeammateExecutor multi-turn loop pulling from mailbox each iteration; SubagentHandle for long-lived child query | Phase 55 |
| **AD-Cat11-SSEEvents** | Observability | SubagentSpawned/Completed event emission from tool handlers; SSE serializer 2 isinstance branches (Day 0 D3 deferred per D18) | Phase 55 frontend |
| **AD-Cat11-ParentCtx** | Feature | ForkExecutor parent context inheritance via Cat 7 checkpoint load (Day 2 D12 deferred) | Phase 55 |
| **AD-Cat10-Obs-Cat9Wrappers** | Code quality | Cat 9 fallback / mutator wrappers separate observability span (currently rely on inner judge per D19); revisit if double-instrumentation actually needed | Phase 55+ audit cycle |

### Phase 55 candidate scope (V2 final main-progress sprints)

V2 progress now **20/22 (91%)**. Remaining 2 sprints estimated for Phase 55:

- **Sprint 55.1 (Phase 55 kickoff)**: Business domain layer (5 domains: patrol / correlation / rootcause / audit / incident) — **24 mock tools per 08b-business-tools-spec.md**; integrate with Cat 2 ToolRegistry; demonstrate end-to-end domain workflow via subagent
- **Sprint 55.2 (V2 closure)**: Canary deployment + production readiness — Phase 55 tools wire to real enterprise APIs; SaaS Stage 0 cutover prep

After Phase 55 completion (Sprint 55.2), V2 reaches **22/22 (100%)** — V2 done; SaaS Stage 1 begins in Phase 56.

---

## Sprint 54.2 Final Stats

| Metric | Value |
|--------|-------|
| Sprint duration | 1 day (compressed; Day 0-4 same session) |
| Source files new | 8 (exceptions / budget / dispatcher / mailbox / fork / as_tool / teammate / handoff / tools + _obs helper) |
| Source files modified | 4 (subagent/__init__.py + modes/__init__.py + _contracts/subagent.py + _contracts/__init__.py) + 4 verification (rules_based / llm_judge for AD-Cat10-Obs-1) |
| Test files new | 6 (test_budget / test_dispatcher_init / test_fork / test_as_tool / test_mailbox / test_teammate / test_handoff / test_subagent_tools / test_observability) |
| Tests added | **46** (= 11 budget + 4 dispatcher_init + 5 fork + 4 as_tool + 5 mailbox + 4 teammate + 3 handoff + 7 tools + 4 obs - 2 obsolete removed) |
| pytest total | **1351 passed / 4 skipped** (= 1305 baseline + 46) |
| mypy --strict | 0 errors / 24 source files |
| 6 V2 lints | 6/6 green (after D14 + D17 + D22 fixes) |
| LLM SDK leak | 0 (lint check passed) |
| Cat 11 source LOC | ~700 |
| AD-Cat10-Obs-1 source LOC | ~50 (helper + 4 verifier edits) |
| Drifts catalogued | **22** (D1-D22 across Day 0-4) |
| AD closed | 1 (AD-Cat10-Obs-1) |
| AD logged for follow-up | 7 (AD-Sprint-Plan-2 / AD-Cat12-Helpers-1 / AD-Lint-3 / AD-Cat11-Multiturn / AD-Cat11-SSEEvents / AD-Cat11-ParentCtx / AD-Cat10-Obs-Cat9Wrappers) |
| Calibration ratio | 0.65 (committed 12.4 hr / actual 8 hr) |
| Cat 11 level | Level 0 (49.1 stub) → **Level 4** (主流量強制 infrastructure ready) |
| V2 progress | 19/22 (86%) → **20/22 (91%)** ↑ |

---

**Sprint complete. V2 final 2 sprints (Phase 55) target 22/22 (100%).**
