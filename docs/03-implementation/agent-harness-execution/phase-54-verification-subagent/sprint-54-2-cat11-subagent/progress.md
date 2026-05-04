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

## Day 1 (2026-05-04) — US-1 BudgetEnforcer + Dispatcher Skeleton ✅

### 1.1 / 1.2 / 1.3 Source files created (4)

- ✅ `agent_harness/subagent/exceptions.py` — `BudgetExceededError` + `SubagentLaunchError` (47 lines)
- ✅ `agent_harness/subagent/budget.py` — `BudgetEnforcer` (5 methods: check_concurrent / check_tokens / check_duration / check_depth / truncate_summary) (95 lines)
- ✅ `agent_harness/subagent/dispatcher.py` — `DefaultSubagentDispatcher` skeleton (3 ABC methods + `as_tool_factory()`; all raise NotImplementedError pending US-2/3/4) (152 lines)

### 1.4 `__init__.py` re-exports

- ✅ Added `DefaultSubagentDispatcher` / `BudgetEnforcer` / `BudgetExceededError` / `SubagentLaunchError` to public API

### Drift findings during Day 1 (D10 — D11)

| ID | Type | Issue | Fix |
|----|------|-------|----|
| **D10** | architecture (revises D1) | ABC reads `spawn / wait_for / handoff` (3 methods, fire-and-forget pattern) — **NOT** unified `dispatch()` as Day 0 D1 thought. spawn() returns UUID; wait_for(subagent_id) returns SubagentResult; handoff() returns new session_id directly. AS_TOOL stays out-of-band via separate `as_tool_factory()` method (Option A confirmed) | DefaultSubagentDispatcher implements actual ABC: spawn() + wait_for() + handoff() + as_tool_factory(). spawn(AS_TOOL/HANDOFF) raises SubagentLaunchError to surface misuse. |
| **D11** | data | Plan §Technical Spec said `max_concurrent_subagents` and `summary_token_cap` budget fields. Actual `SubagentBudget` (49.1 stub) has `max_concurrent` (no `_subagents` suffix) + `max_subagent_depth` (NEW; recursive guard) + NO `summary_token_cap` (convention is "≤ 500 tokens" docstring on SubagentResult.summary) | BudgetEnforcer: rename to `check_concurrent` (matches actual field); add 5th method `check_depth` for max_subagent_depth recursive guard; `truncate_summary(text, cap_words=500)` takes caller-provided cap (not from budget). No 17.md change needed. |

### 1.5 / 1.6 Tests (15 cases — +5 bonus)

- ✅ `tests/unit/agent_harness/subagent/test_budget.py` — **11 cases** (plan said 8; +3 bonus: empty truncation edge + depth pass + depth exceeds)
  - check_concurrent pass / exceeds (2)
  - check_tokens pass / exceeds (2)
  - check_duration pass / exceeds (2)
  - truncate_summary under_cap / over_cap / empty (3)
  - check_depth pass / exceeds (2)
- ✅ `tests/unit/agent_harness/subagent/test_dispatcher_init.py` — **4 cases** (plan said 2; +2 bonus: AS_TOOL + HANDOFF spawn() launch error coverage)
  - test_dispatcher_inherits_subagent_dispatcher_abc
  - test_spawn_as_tool_mode_raises_launch_error
  - test_spawn_handoff_mode_raises_launch_error
  - test_spawn_fork_mode_skeleton_raises_not_implemented

### 1.7 Day 1 sanity checks ✅

- ✅ **mypy --strict** — 0 errors in 5 source files (subagent/__init__.py / _abc.py / exceptions.py / budget.py / dispatcher.py)
- ✅ **black** — 3 files auto-formatted; recheck clean
- ✅ **isort** — clean
- ✅ **flake8** — clean
- ✅ **6 V2 lints (`run_all.py`)** — 6/6 green in 0.77s
- ✅ **LLM SDK leak in subagent/** — 0 (grep confirm)
- ✅ **Backend full pytest** — **1320 passed / 4 skipped / 0 fail** (= 1305 baseline + 15 new = 11 budget + 4 dispatcher_init)

### 1.8 V2 9-discipline self-check ✅

| # | Discipline | Status | Note |
|---|-----------|--------|------|
| 1 | Server-Side First | ✅ | All 4 Cat 11 source files server-side; no local file IO |
| 2 | LLM Provider Neutrality | ✅ | 0 SDK imports in subagent/ (lint pass) |
| 3 | CC Reference 不照搬 | ✅ | spawn/wait_for/handoff is V2 server-side pattern; CC has different async model |
| 4 | 17.md Single-source | ✅ | Used existing SubagentBudget/Mode/Result (no redefinition); SubagentHandle / AgentSpec deferred to US-2/3 (per Day 0 D7) |
| 5 | 11+1 範疇歸屬 | ✅ | All files in `agent_harness/subagent/` — Cat 11 owner directory |
| 6 | 04 anti-patterns | ✅ | AP-3 (no scattering), AP-4 (NotImplementedError IS placeholder but tests assert it raises — caught by US-2/3/4 acceptance), AP-6 (worktree NOT implemented per V2 spec; YAGNI) |
| 7 | Sprint workflow | ✅ | Plan → checklist → Day 0 探勘 → Day 1 code → progress |
| 8 | File header convention | ✅ | All 4 source + 2 test files have File / Purpose / Category / Scope / Created header |
| 9 | Multi-tenant rule | ✅ | parent_session_id passed through spawn(); future executors will propagate tenant_id |

### 1.9 Time spent

Day 1 actual: ~1 hr (plan estimate 3.5 hr × 0.55 calibrated → committed for ~2 hr). Faster than expected due to:
- Skeleton-first approach (no real mode executor logic this Day)
- Frozen-dataclass discovery (no defensive code needed)
- Test boilerplate copy-pasting from 54.1 patterns

Banked: +1 hr buffer added to Day 2/3/4 reserve.

## Day 2 (2026-05-04) — US-2 Fork + AsTool Modes ✅

### 2.1 / 2.2 / 2.3 New `subagent/modes/` package + 2 mode executors

- ✅ `subagent/modes/__init__.py` — re-export ForkExecutor + AsToolWrapper
- ✅ `subagent/modes/fork.py` (~130 lines) — ForkExecutor with single-shot ChatClient call + budget timeout/error fail-closed
- ✅ `subagent/modes/as_tool.py` (~115 lines) — AsToolWrapper.wrap(spec) → (ToolSpec, handler) tuple

### 2.4 Wire dispatcher (rewrite for FORK + as_tool_factory)

- ✅ `__init__(*, chat_client: ChatClient)` injection
- ✅ spawn(FORK) → asyncio.create_task wrapping fork_executor.execute() → store in `_in_flight[uuid]`
- ✅ spawn() concurrency check via `BudgetEnforcer.check_concurrent` → BudgetExceededError → SubagentLaunchError
- ✅ wait_for() → await stored task with optional timeout (asyncio.shield protect cancellation)
- ✅ as_tool_factory(spec: AgentSpec) → tuple delegation to AsToolWrapper
- ✅ TEAMMATE / HANDOFF still NotImplementedError (US-3 / US-4 fill)

### 2.5 D7 partial closure: AgentSpec added to `_contracts/subagent.py`

- ✅ Frozen dataclass: role + prompt + model + metadata
- ✅ Re-exported from `_contracts/__init__.py` (imports + __all__)
- 🚧 SubagentHandle still deferred — Teammate (US-3) decides if needed

### Drift findings during Day 2 (D12 — D14)

| ID | Type | Issue | Fix |
|----|------|-------|----|
| **D12** | architecture | Plan §US-2 said ForkExecutor "deepcopy parent.messages → run child AgentLoop with budget guards". But actual ABC `spawn(mode, task, parent_session_id, budget)` only passes parent_session_id (UUID), not parent_ctx. Loading parent state from session_id requires checkpoint/Cat 7 wiring not in scope for 54.2. | Day 2 simplification: ForkExecutor runs `task` as single-shot ChatClient call (user message only). No parent message inheritance. Phase 55+ may extend to multi-turn child loops with parent state load. Documented in fork.py module docstring. |
| **D13** | data | `TokenUsage` actual fields are `prompt_tokens` / `completion_tokens` / `cached_input_tokens` / `total_tokens`, NOT `input_tokens` / `output_tokens` as initially written | Use `response.usage.total_tokens` if > 0 else fall back to `prompt_tokens + completion_tokens` |
| **D14** | lint | AP-8 lint flagged `fork.py` (same issue as 54.1 D10 with llm_judge.py). ForkExecutor calls ChatClient.chat() directly without PromptBuilder routing | Add `agent_harness/subagent/modes/fork.py` to `check_promptbuilder_usage.py` ALLOWLIST_PATTERNS with utility-LLM caller justification (parent already routed through PromptBuilder before deciding to spawn). |

### 2.6 Tests (10 new — +2 bonus over plan's 8)

- ✅ `test_fork.py` — **5 cases**:
  - test_fork_returns_subagent_result_with_summary (happy path; 80 tokens)
  - test_fork_summary_truncated_to_cap (1000 → 501 words)
  - test_fork_chat_exception_returns_fail_closed (RuntimeError → error string)
  - test_fork_timeout_returns_timeout_error (max_duration_s=0)
  - test_dispatcher_spawn_fork_then_wait_for_round_trip (e2e via dispatcher)
- ✅ `test_as_tool.py` — **4 cases** (3 plan + 1 bonus: missing_task input):
  - test_as_tool_returns_toolspec_with_correct_schema
  - test_as_tool_handler_calls_fork_executor_returns_summary_dict
  - test_as_tool_handler_missing_task_returns_error (bonus; no LLM call)
  - test_dispatcher_as_tool_factory_returns_pair (e2e via dispatcher)
- ✅ `test_dispatcher_init.py` updated:
  - All 4 prior tests now pass MockChatClient
  - +1 bonus: test_handoff_method_skeleton_raises_not_implemented (US-4 placeholder coverage)

### 2.7 Day 2 sanity checks ✅

- ✅ **mypy --strict** — 0 errors / 8 source files
- ✅ **black** — 3 files auto-formatted; recheck clean
- ✅ **isort** — 1 fix on test_dispatcher_init.py; recheck clean
- ✅ **flake8** — clean
- ✅ **6 V2 lints** — initially 5/6 (D14 AP-8 flag); after ALLOWLIST add → 6/6 green in 0.63s
- ✅ **LLM SDK leak in subagent/** — 0 (grep confirm)
- ✅ **Backend full pytest** — **1330 passed / 4 skipped / 0 fail** (= 1320 baseline + 10 new = 5 fork + 4 as_tool + 1 dispatcher_init bonus)

### 2.8 V2 9-discipline self-check ✅

| # | Discipline | Status | Note |
|---|-----------|--------|------|
| 1 | Server-Side First | ✅ | All Cat 11 mode files server-side; ChatClient via injection |
| 2 | LLM Provider Neutrality | ✅ | 0 SDK imports in subagent/; check_llm_sdk_leak passed |
| 3 | CC Reference 不照搬 | ✅ | Single-shot ForkExecutor is V2 server-side simplification (D12); CC has different multi-turn pattern |
| 4 | 17.md Single-source | ✅ | AgentSpec added to _contracts/subagent.py (D7 partial); SubagentBudget/Mode/Result unchanged; ToolSpec from _contracts |
| 5 | 11+1 範疇歸屬 | ✅ | Fork + AsTool in `subagent/modes/` (Cat 11 owner) |
| 6 | 04 anti-patterns | ✅ | AP-3 (no scattering), AP-8 (D14 ALLOWLIST justified — utility-LLM caller, same as 54.1 D10 pattern) |
| 7 | Sprint workflow | ✅ | Plan → checklist → Day 0 → Day 1 → Day 2 → progress |
| 8 | File header convention | ✅ | All new files have File / Purpose / Category / Scope / Modification History |
| 9 | Multi-tenant rule | ✅ | Per-request DI dispatcher (no module singleton); parent_session_id propagates via spawn() |

### 2.9 Time spent

Day 2 actual: ~1.5 hr (plan estimate 4 hr × 0.55 calibrated → committed for ~2.2 hr). Faster than expected due to:
- Day 0 探勘 captured all major contract drifts (D1-D9) so writing was straightforward
- AsToolWrapper closure pattern reusable from 54.1 verifier handler patterns
- Test boilerplate copy-pasting from 54.1

Banked: +0.7 hr Day 2 + carrying forward Day 1 +1 hr → **+1.7 hr total banked** for Day 3-4 reserve.

## Day 3 (2026-05-04) — US-3 Teammate Mode + Mailbox ✅

### 3.1 / 3.2 New `subagent/mailbox.py` + `subagent/modes/teammate.py`

- ✅ `subagent/mailbox.py` (~80 lines) — `MailboxStore`: per-(session_id, recipient) asyncio.Queue; per-request DI (no module singleton)
  - `send(session_id, sender, recipient, content)` puts Message
  - `receive(session_id, recipient, timeout_s=5.0)` returns Message | None
  - `clear(session_id)` drops session queues
  - `session_count()` for diagnostics
- ✅ `subagent/modes/teammate.py` (~150 lines) — `TeammateExecutor`: single-shot LLM call (D15 simplification) with mailbox side effect (deliver summary to parent's "parent" recipient)

### 3.3 Wire dispatcher (TEAMMATE)

- ✅ `__init__(*, chat_client, mailbox: MailboxStore | None = None)` — optional mailbox injection (default fresh instance)
- ✅ spawn(TEAMMATE) → asyncio.create_task wrapping teammate_executor.execute() with role="teammate" default (per Day 3 D15: ABC has no role kwarg; Phase 55+ may extend)
- ✅ TEAMMATE branch replaces NotImplementedError; only HANDOFF still skeleton

### 3.4 D7 final closure

- 🚧 SubagentHandle NOT added — TeammateExecutor.execute returns SubagentResult (consistent with ForkExecutor; Phase 55+ may add Handle if multi-turn long-lived semantics needed). Plan §US-3 SubagentHandle deferred — design simpler without it.

### Drift findings during Day 3 (D15 — D17)

| ID | Type | Issue | Fix |
|----|------|-------|----|
| **D15** | architecture | Plan §US-3 said TeammateExecutor.spawn returns SubagentHandle (long-lived) and supports multi-turn child loop pulling from mailbox each iteration. ABC `dispatcher.spawn(mode, task, parent_session_id, budget) -> UUID` doesn't pass role; mailbox is per-session-per-recipient unbounded queue | Day 3 simplification: TeammateExecutor.execute is single-shot LLM call (same as ForkExecutor) with mailbox side effect — delivers summary to parent's "parent" recipient on completion. Demonstrates mailbox infrastructure works. Phase 55+ may extend to multi-turn loop. SubagentHandle deferred. |
| **D16** | flake8 | E501 line too long (105 chars) on dispatcher.py L5 (Scope description) after multiple sprint annotations accumulated | Shortened: "Sprint 54.2 US-1 → US-2 (FORK + AsTool) → US-3 (TEAMMATE); US-4 HANDOFF" |
| **D17** | lint | AP-8 lint flagged teammate.py (same pattern as D14 fork.py and 54.1 D10 llm_judge.py — utility-LLM caller, not main loop) | Added `agent_harness/subagent/modes/teammate.py` to check_promptbuilder_usage.py ALLOWLIST_PATTERNS with same justification |

### 3.5 / 3.6 Tests (8 new — per plan)

- ✅ `test_mailbox.py` — **5 cases**:
  - send/receive round-trip (sender annotation in content)
  - per-session isolation (session A msg invisible to B)
  - per-recipient isolation (msg to alice invisible to bob)
  - receive timeout returns None (not raises)
  - clear drops session queues
- ✅ `test_teammate.py` — **4 cases** (3 plan + 1 bonus: chat_exception variant):
  - test_teammate_returns_subagent_result_and_delivers_to_mailbox (happy path; both result + mailbox)
  - test_teammate_timeout_returns_timeout_error_no_mailbox_delivery (timeout fail-closed; no spam in mailbox)
  - test_dispatcher_spawn_teammate_then_wait_for_round_trip (e2e via dispatcher)
  - test_teammate_chat_exception_returns_fail_closed_no_mailbox_delivery (bonus; ChatClient raise variant)
- ✅ test_dispatcher_init.py: removed obsolete `test_spawn_teammate_skeleton_raises_not_implemented` (US-3 wired TEAMMATE; round-trip behavior covered in test_teammate.py)

### 3.7 Day 3 sanity checks ✅

- ✅ **mypy --strict** — 0 errors / 10 source files
- ✅ **black** — 1 file auto-formatted (teammate.py)
- ✅ **isort** — clean
- ✅ **flake8** — D16 fix → clean
- ✅ **6 V2 lints** — initially 5/6 (D17 AP-8 flag); after ALLOWLIST add → 6/6 green in 0.65s
- ✅ **LLM SDK leak in subagent/** — 0
- ✅ **Backend full pytest** — **1338 passed / 4 skipped / 0 fail** (= 1330 baseline + 8 new = 5 mailbox + 4 teammate − 1 obsolete dispatcher_init removed)

### 3.8 V2 9-discipline self-check ✅

| # | Discipline | Status | Note |
|---|-----------|--------|------|
| 1 | Server-Side First | ✅ | Mailbox in-memory only (no file IO; per-request DI) |
| 2 | LLM Provider Neutrality | ✅ | TeammateExecutor via ChatClient ABC; lint passed |
| 3 | CC Reference 不照搬 | ✅ | CC peer-pane is file-based mailbox; V2 in-memory asyncio queues (server-side) |
| 4 | 17.md Single-source | ✅ | Reused SubagentBudget/Mode/Result; no new dataclass added (SubagentHandle deferred) |
| 5 | 11+1 範疇歸屬 | ✅ | mailbox.py + modes/teammate.py both in `agent_harness/subagent/` (Cat 11 owner) |
| 6 | 04 anti-patterns | ✅ | AP-3 / AP-6 (worktree NOT implemented; verified clean) / AP-8 D17 ALLOWLIST justified |
| 7 | Sprint workflow | ✅ | Plan → checklist → Day 0/1/2/3 → progress update each day |
| 8 | File header convention | ✅ | All new files have File / Purpose / Category / Scope / Modification History |
| 9 | Multi-tenant rule | ✅ | Mailbox session-scoped (queue dict by session_id); cross-session isolation tested |

### 3.9 Time spent

Day 3 actual: ~1.5 hr (plan estimate 5 hr × 0.55 calibrated → committed for ~2.75 hr). Significantly faster than expected due to:
- D15 simplification (single-shot vs full multi-turn loop) saves ~2 hr complexity
- Mailbox in-memory pattern is straightforward dict-of-queues
- Test patterns reused from Day 1+2 (MockChatClient + dispatcher)

Banked Day 3: **+1.25 hr** + Day 1+2 banked +1.7 hr = **+2.95 hr cumulative banked** for Day 4 reserve.

### Next: Day 4 (US-4 Handoff + AgentLoop wiring + US-5 task_spawn/handoff tools + AD-Cat10-Obs-1 + Retrospective)

- Implement `subagent/modes/handoff.py` (HandoffExecutor)
- Wire `dispatcher.handoff()` to HandoffExecutor (returns new session_id UUID per ABC)
- AgentLoop integration: subagent_dispatcher param + tool dispatch path for task_spawn / handoff (currently dispatch via tool_executor; handoff needs `_pending_handoff` flag + LoopCompleted(status="handoff") path)
- SSE serializer: add SubagentSpawned + SubagentCompleted isinstance branches (D3 from Day 0)
- US-5 tools: `agent_harness/subagent/tools.py` with `make_task_spawn_tool` + `make_handoff_tool` factories
- US-5 AD-Cat10-Obs-1: 4 verifier classes (rules_based / llm_judge / cat9_fallback / cat9_mutator) tracer span + 3 metrics
- 7 tests handoff + integration + 3 tools + 4 observability = **~14 tests**
- Day 4 retrospective.md (6 questions + calibration multiplier 3rd verification)
- PR open + closeout + memory + SITUATION-V2 update

預計 ~5.5 hr。Banked +2.95 hr → effective ~8.5 hr。完整 sprint 收尾 + V2 19/22 → 20/22。
