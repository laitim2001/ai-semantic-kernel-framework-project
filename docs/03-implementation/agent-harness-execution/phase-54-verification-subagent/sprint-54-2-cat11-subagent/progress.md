# Sprint 54.2 Progress — Cat 11 Subagent + AD-Cat10-Obs-1

**Plan**: [sprint-54-2-plan.md](../../../agent-harness-planning/phase-54-verification-subagent/sprint-54-2-plan.md)
**Checklist**: [sprint-54-2-checklist.md](../../../agent-harness-planning/phase-54-verification-subagent/sprint-54-2-checklist.md)
**Branch**: `feature/sprint-54-2-cat11-subagent`
**Sprint Goal**: Cat 11 (Subagent Orchestration) Level 0 → Level 4 + AD-Cat10-Obs-1 closure → V2 19/22 → 20/22 (91%)

---

## Day 0 (2026-05-04) — Setup + 探勘 + Pre-flight

### 0.1 Branch + Plan/Checklist Commit ✅

- ✅ Verified clean main (HEAD `c5a64c62` post-54.1 closeout merge)
- ✅ Created branch `feature/sprint-54-2-cat11-subagent` (tracks origin)
- ✅ Plan + checklist commit `60a5050b` (2 files / 1041 insertions)
- ✅ Pushed to origin

### 0.2 Day-0 探勘 — 9 Drift Findings

Per AD-Plan-1 (53.7 lesson): grep §Technical Spec assertions vs actual repo state.

| ID | Type | Issue | Fix Plan |
|----|------|-------|----------|
| **D1** | architecture | `SubagentDispatcher` ABC has UNIFIED `dispatch(*, mode: SubagentMode, ...) -> SubagentResult` method — **NOT 4 separate methods** (fork / spawn_teammate / handoff_to / as_tool) as plan §Technical Spec assumed | DefaultSubagentDispatcher implements single `dispatch()` that internally routes to mode executors based on `mode` parameter. ABC unchanged (preserves 17.md single-source). Convenience methods can be added on DefaultSubagentDispatcher (not ABC) if useful internally, but `dispatch()` is the canonical entry point. |
| **D2** | events ✅ | `SubagentSpawned` + `SubagentCompleted` events ALREADY exist at `_contracts/events.py:274,281` (49.1 stub). Fields: `subagent_id`, `mode`, `parent_session_id`, `summary`, `tokens_used` (all optional with defaults). | Confirmed (good); just emit them in US-4 dispatch path. No event class changes needed. |
| **D3** | SSE | SSE serializer at `backend/src/api/v1/chat/sse.py` has **0 isinstance branches** for SubagentSpawned / SubagentCompleted. Per `feedback_sse_serializer_scope_check.md`: production AgentLoop will raise NotImplementedError if events emitted without serializer support. | US-4 must add 2 isinstance branches at `api/v1/chat/sse.py` (NOT `orchestrator_loop/sse.py` — same location as 54.1 D1 finding). |
| **D4** | location | `SubagentResultReducer` lives at `state_mgmt/decision_reducers.py:96` — **NOT `state_mgmt/reducer.py`** as plan said. Pattern is **patch-builder** (`build_patch(result) → dict for DefaultReducer.merge()`), not Reducer subclass. (Per 53.4 retro v2-lints dup error fix.) | US-4 wires AgentLoop to call `SubagentResultReducer.build_patch(result)` then feed patch into `DefaultReducer.merge()`. Plan §File Change List path correction. |
| **D5** | observability ✅ | `Tracer` ABC exists at `agent_harness/observability/_abc.py:32` (49.4 stub). `TraceContext` + `MetricEvent` at `_contracts/observability.py:60,78`. | Use Tracer ABC for AD-Cat10-Obs-1. Inject `Tracer | None = None` into 4 verifier classes; default `NullTracer` if needed. |
| **D6** | naming | Second `Tracer` Protocol class at `prompt_builder/builder.py:102` (informational duplicate; different from observability Tracer ABC). | Cat 10 verifiers import from `agent_harness.observability` (the ABC), not from prompt_builder. No code change needed but Day 4 retro should flag for AD-Naming carryover. |
| **D7** | contract | `SubagentHandle` + `AgentSpec` NOT in `_contracts/subagent.py` (only `SubagentMode` / `SubagentBudget` / `SubagentResult` exist). | US-3 (Teammate) needs SubagentHandle; US-2/3/4 need AgentSpec. Add both to `_contracts/subagent.py` per 17.md §1.1 single-source rule. Update 17.md if signatures don't match existing language in spec. |
| **D8** | architecture ✅ | AgentLoop tool dispatch via `self._tool_executor.execute(tc)` (single line at `loop.py:1018`); ToolExecutor auto-routes by tool_name. **No need to add per-tool branches in loop.py.** | task_spawn / handoff register as Cat 2 tools (factory functions in `subagent/tools.py`); ToolExecutor dispatches automatically. EXCEPT handoff needs flag check after turn → AgentLoop change still needed for `_pending_handoff` → yield `LoopCompleted(status="handoff")` path. |
| **D9** | data | `SubagentBudget` is `frozen=True` dataclass (`_contracts/subagent.py:47`). | Plan must not mutate; if budget needs adjustment per child create new instance via `dataclasses.replace()`. |

### 0.3 Calibration Multiplier Pre-read ✅

- 53.7 ratio: **1.01** (predicted 7.4 hr / actual 7.5 hr)
- 54.1 ratio: **0.69** (predicted 10.2 hr / actual 7 hr)
- 2-sprint window mean: **0.85** (border of stable [0.85, 1.20] band)
- Per 54.1 retro Q2 recommendation: keep 0.55 default for 1-2 more sprints

**54.2 Bottom-up estimate**:
| US | Bottom-up |
|----|-----------|
| US-1 (BudgetEnforcer + Dispatcher skeleton) | ~3.5 hr |
| US-2 (Fork + AsTool) | ~4 hr |
| US-3 (Teammate + Mailbox) | ~5 hr |
| US-4 (Handoff + AgentLoop wiring) | ~3.5 hr |
| US-5 (tools + AD-Cat10-Obs-1) | ~3.5 hr |
| Day 0/4 overhead | ~3 hr |
| **Total** | **~22.5 hr** |

**Calibrated commit (×0.55)**: ~12.4 hr → **commit 12-13 hr** (matches plan §Workload).

### 0.4 Pre-flight Verify ✅

- ✅ pytest collect baseline: **1309 tests** (1305 passed + 4 skipped on main; +4 from 54.1 baseline due to post-merge sync)
- ✅ 6 V2 lints via `run_all.py`: **6/6 green in 0.62s**
  - check_ap1: 0.04s / check_promptbuilder: 0.12s / check_cross_category_import: 0.11s
  - check_duplicate_dataclass: 0.11s / check_llm_sdk_leak: 0.07s / check_sync_callback: 0.17s

### 0.5 Time Banking Status

- 54.1 banked: +3 hr buffer (committed 10.2, actual 7)
- 54.2 commit: 12-13 hr; effective buffer 12-13 + 3 = 15-16 hr
- This buffer absorbs higher complexity (4 modes + mailbox + handoff signal coordination)

### 0.6 Plan Adjustments Captured (Day 1 Pre-Work)

Based on 9 drift findings, plan §Technical Spec dispatcher.py skeleton needs adjustment:

```python
# CORRECTED dispatcher.py skeleton (per D1)
class DefaultSubagentDispatcher(SubagentDispatcher):
    def __init__(self, *, mailbox: MailboxStore, chat_client_factory=None):
        self._enforcer = BudgetEnforcer()
        self._fork = ForkExecutor(self._enforcer, chat_client_factory)
        self._teammate = TeammateExecutor(self._enforcer, mailbox, chat_client_factory)
        self._handoff = HandoffExecutor(self._enforcer, chat_client_factory)
        self._as_tool_wrapper = AsToolWrapper(self._fork)

    async def dispatch(self, *, mode: SubagentMode, parent_ctx, task=None,
                       agent_spec=None, target_agent=None, handoff_context=None,
                       budget: SubagentBudget | None = None,
                       trace_context: TraceContext) -> SubagentResult:
        budget = budget or SubagentBudget()  # default per _contracts
        if mode == SubagentMode.FORK:
            return await self._fork.execute(parent_ctx, task, budget, trace_context)
        elif mode == SubagentMode.TEAMMATE:
            handle = await self._teammate.spawn(agent_spec.role, agent_spec, budget, trace_context)
            return await handle.completion_future  # SubagentHandle holds future
        elif mode == SubagentMode.HANDOFF:
            return await self._handoff.execute(parent_ctx, target_agent, handoff_context, budget)
        elif mode == SubagentMode.AS_TOOL:
            return self._as_tool_wrapper.wrap(agent_spec)  # returns ToolSpec, NOT SubagentResult
            # Note: AS_TOOL diverges from SubagentResult contract — this is a known design inconsistency
            # Alternative: AS_TOOL is NOT dispatched directly; only via dispatcher.as_tool_factory()
        else:
            raise ValueError(f"Unknown mode: {mode}")
```

**Note D1-followup**: `AS_TOOL` mode doesn't fit `dispatch() -> SubagentResult` since it returns a wrapped ToolSpec. Two design options for Day 1:
- **Option A**: Add separate `as_tool_factory(agent_spec) -> ToolSpec` method on DefaultSubagentDispatcher (not in ABC); `dispatch(mode=AS_TOOL)` raises ValueError
- **Option B**: Wrap ToolSpec inside SubagentResult.metadata field; consumer extracts

Recommend **Option A** (cleaner separation of concerns); decide at Day 1 start.

### 0.7 Day 0 Outcome ✅

| Item | Status |
|------|--------|
| Branch + plan/checklist pushed | ✅ commit `60a5050b` |
| 9 drifts catalogued | ✅ D1-D9 |
| Pre-flight green | ✅ 1309 tests + 6/6 V2 lints |
| Calibration pre-read | ✅ 0.55 × 22.5 = 12-13 hr commit |
| Day 0 progress.md | ✅ this file |

### Next: Day 1 (US-1 BudgetEnforcer + Dispatcher Skeleton)

- Decide D1-followup Option A vs B (recommend A)
- Add `SubagentHandle` + `AgentSpec` to `_contracts/subagent.py` (D7)
- Implement `subagent/exceptions.py` + `subagent/budget.py` + `subagent/dispatcher.py` (skeleton)
- 8 unit tests for budget + 2 for dispatcher init
- Sanity: mypy / lint / pytest 1319 expected
- Day 1 commit + push + progress update
