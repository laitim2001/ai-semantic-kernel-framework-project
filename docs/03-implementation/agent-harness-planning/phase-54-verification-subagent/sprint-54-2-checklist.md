# Sprint 54.2 — Cat 11 Subagent Orchestration + AD-Cat10-Obs-1 — Checklist

**Plan**: [sprint-54-2-plan.md](sprint-54-2-plan.md)
**Branch**: `feature/sprint-54-2-cat11-subagent`
**Day count**: 5 (Day 0-4) | **Bottom-up est**: ~22.5 hr | **Calibrated commit**: ~12-13 hr (multiplier 0.55 per AD-Sprint-Plan-1; **3rd application** after 53.7 ratio 1.01 + 54.1 ratio 0.69)

> **格式遵守**：每 Day 同 54.1 結構（progress.md update + sanity + commit + verify CI）。每 task 3-6 sub-bullets（case / DoD / Verify command）。Per AD-Lint-2 (53.7) — 不寫 per-day calibrated hour targets；只寫 sprint-aggregate calibration verify in retro。

---

## Day 0 — Setup + Day-0 探勘 + Pre-flight Verify

### 0.1 Branch + plan + checklist commit
- [x] **Verify on main + clean** ✅ HEAD `c5a64c62`
- [x] **Create branch + push plan/checklist** ✅ commit `60a5050b` (2 files / 1041 insertions)

### 0.2 Day-0 探勘 — 9 Drift Findings catalogued (D1-D9)
- [x] **Verify 49.1 stubs exist + signatures** ✅ partial drift
  - 🚨 **D1** (architecture): SubagentDispatcher ABC has UNIFIED `dispatch(*, mode, ...)` method (not 4 separate). DefaultSubagentDispatcher implements single dispatch() routing internally.
  - 🚨 **D7** (contract): SubagentHandle + AgentSpec MISSING from `_contracts/subagent.py` → US-1/3 will add
  - 🚨 **D9** (data): SubagentBudget frozen=True (use dataclasses.replace if mutation needed)
  - ✅ SubagentMode / SubagentBudget / SubagentResult exist
- [x] **Grep AgentLoop tool dispatch path** ✅
  - ✅ **D8**: tool_executor.execute(tc) single-line dispatch at loop.py:1018; ToolExecutor auto-routes by tool_name. handoff still needs `_pending_handoff` flag check after turn → loop.py change
- [x] **Grep SSE serializer for SubagentSpawned / SubagentCompleted** ✅
  - 🚨 **D3**: 0 matches in `api/v1/chat/sse.py` → US-4 add 2 isinstance branches (SAME location as 54.1 D1 finding — `api/v1/chat/sse.py` not `orchestrator_loop/sse.py`)
- [x] **Verify SubagentResultReducer location** ✅
  - 🚨 **D4**: at `state_mgmt/decision_reducers.py:96` (NOT `state_mgmt/reducer.py` as plan said). Pattern is **build_patch** (returns dict for DefaultReducer.merge), not Reducer subclass
  - ✅ **D2**: SubagentSpawned + SubagentCompleted events EXIST at `_contracts/events.py:274,281` (49.1 stub; optional fields)
- [x] **Verify 4 verifier classes + Tracer ABC for AD-Cat10-Obs-1** ✅
  - ✅ **D5**: Tracer ABC at `agent_harness/observability/_abc.py:32` (49.4 stub) — use this for AD-Cat10-Obs-1
  - 🚨 **D6**: Second Tracer Protocol at `prompt_builder/builder.py:102` (informational duplicate; NOT same class). Cat 10 uses observability Tracer ABC. Day 4 retro flag for AD-Naming
- [x] **Grep existing Mailbox-related code** ✅
  - Only 3 references (subagent/_abc.py + README + _contracts/subagent.py docs); no implementation. Clean slate for US-3 ✅

### 0.3 Calibration multiplier pre-read ✅
- [x] **Read 54.1 retrospective Q2** ✅ 0.55 ratio 0.69 (predicted 10.2 / actual 7); 2-sprint mean 0.85 border stable band
- [x] **Compute 54.2 bottom-up** ✅ ~22.5 hr × 0.55 = **commit 12-13 hr**

### 0.4 Pre-flight verify（main green baseline） ✅
- [x] **pytest collect baseline** ✅ **1309 tests collected** (= 1305 passed + 4 skipped + 4 from post-merge sync)
- [x] **6 V2 lints via run_all.py** ✅ **6/6 green in 0.62s** (check_ap1 0.04 / check_promptbuilder 0.12 / check_cross_category_import 0.11 / check_duplicate_dataclass 0.11 / check_llm_sdk_leak 0.07 / check_sync_callback 0.17)

### 0.5 Day 0 progress.md ✅
- [x] **Create `progress.md`** ✅ 125 insertions; 9 drifts D1-D9 + plan adjustments captured (D1-followup AS_TOOL design Option A vs B)
- [x] **Commit + push Day 0** ✅ commit `4861bb57`

---

## Day 1 — US-1 DefaultSubagentDispatcher + Budget Enforcement Foundation

### 1.1 New `agent_harness/subagent/exceptions.py` ✅
- [x] **Define BudgetExceededError + SubagentLaunchError** ✅ 47 lines

### 1.2 New `agent_harness/subagent/budget.py` ✅
- [x] **Implement BudgetEnforcer 5 methods** ✅ (D11 fix: added `check_depth` for max_subagent_depth recursive guard; renamed `max_concurrent_subagents` → `max_concurrent` to match actual frozen dataclass; truncate_summary takes `cap_words=500` not from budget)

### 1.3 New `agent_harness/subagent/dispatcher.py` ✅
- [x] **DefaultSubagentDispatcher skeleton** ✅ (D10 fix: 3 ABC methods `spawn / wait_for / handoff` not 4; AS_TOOL out-of-band via `as_tool_factory()` Option A; spawn(AS_TOOL/HANDOFF) raises SubagentLaunchError)

### 1.4 Update `agent_harness/subagent/__init__.py` ✅
- [x] **Re-export 4 new public classes** ✅ DefaultSubagentDispatcher / BudgetEnforcer / BudgetExceededError / SubagentLaunchError

### 1.5 / 1.6 Tests (15 cases — +5 bonus over plan's 10) ✅
- [x] **test_budget.py — 11 cases** ✅ (3 bonus: empty truncation edge + 2 depth coverage)
- [x] **test_dispatcher_init.py — 4 cases** ✅ (2 bonus: AS_TOOL + HANDOFF launch error coverage)
- Verify: `pytest tests/unit/agent_harness/subagent/ -v` → 15 passed

### 1.7 Day 1 sanity checks ✅
- [x] **mypy --strict** ✅ 0 errors / 5 source files
- [x] **black** ✅ 3 files auto-formatted then clean
- [x] **isort** ✅ clean
- [x] **flake8** ✅ clean
- [x] **6 V2 lints via run_all.py** ✅ 6/6 green in 0.77s
- [x] **Backend full pytest** ✅ **1320 passed / 4 skipped / 0 fail** (= 1305 baseline + 15 new)
- [x] **LLM SDK leak in subagent/** ✅ 0 (grep confirm)

### 1.8 Day 1 commit + push + progress.md
- [ ] **Stage + commit + push** (next)
- [x] **Update progress.md with Day 1 actuals + drift fixes (D10 + D11)** ✅

---

## Day 2 — US-2 Fork Mode + AsTool Mode

### 2.1 New `agent_harness/subagent/modes/__init__.py` (empty package init)
- [ ] **Create modes/ subpackage**
  - DoD: `from agent_harness.subagent.modes import ForkExecutor, AsToolWrapper, TeammateExecutor, HandoffExecutor` will work after Days 2-4

### 2.2 New `agent_harness/subagent/modes/fork.py` — ForkExecutor
- [ ] **Implement ForkExecutor**
  - `__init__(enforcer: BudgetEnforcer, chat_client_factory)`
  - `async execute(parent_ctx, task, budget, trace_context) -> SubagentResult`
  - Flow: deepcopy parent.messages → append task as user msg → build child LoopState (new session_id; inherit tenant_id) → run child AgentLoop with budget guards → on completion truncate summary to budget.summary_token_cap → return SubagentResult
  - Budget guards: pre-call `check_concurrent`; mid-loop `check_tokens` per turn; post-loop `check_duration`
  - File header per file-header-convention
  - DoD: matches plan §US-2 acceptance flow

### 2.3 New `agent_harness/subagent/modes/as_tool.py` — AsToolWrapper
- [ ] **Implement AsToolWrapper**
  - `__init__(fork_executor: ForkExecutor)`
  - `wrap(agent_spec: AgentSpec) -> ToolSpec` returns ToolSpec with name=f"agent_{agent_spec.role}", input_schema={"task": str}, handler closure that calls fork_executor.execute() with agent_spec's bounded budget
  - File header per file-header-convention
  - DoD: returned ToolSpec passes 17.md §1 ToolSpec validation

### 2.4 Modify `agent_harness/subagent/dispatcher.py` — wire fork() and as_tool()
- [ ] **Replace 2 `NotImplementedError` with delegation**
  - `fork()` delegates to `self._fork.execute(...)`
  - `as_tool()` delegates to `self._as_tool.wrap(...)`
  - DoD: 2 methods working; spawn_teammate / handoff_to still NotImplementedError (US-3/4)

### 2.5 New `tests/unit/agent_harness/subagent/test_fork.py` — 5 cases
- [ ] **Implement 5 unit tests using mock ChatClient**
  - test_fork_copies_parent_messages_no_mutation (assert id mismatch)
  - test_fork_returns_subagent_result_with_summary
  - test_fork_summary_truncated_to_cap (set cap=10 words; provide long output)
  - test_fork_budget_token_exceeded_returns_status
  - test_fork_propagates_tenant_id_to_child
  - Verify: 5 passed

### 2.6 New `tests/unit/agent_harness/subagent/test_as_tool.py` — 3 cases
- [ ] **Implement 3 unit tests**
  - test_as_tool_returns_toolspec_with_correct_schema
  - test_as_tool_handler_calls_fork_executor (mock fork_executor)
  - test_as_tool_handler_returns_result_summary (e2e via mock)
  - Verify: 3 passed

### 2.7 Day 2 sanity checks
- [ ] **mypy --strict on touched files** → 0 errors
- [ ] **black + isort + flake8** → clean
- [ ] **6 V2 lints** → 6/6 green
- [ ] **LLM SDK leak check** → 0 in subagent/
- [ ] **Backend full pytest** → ~1323 passed (1315 + 8 new) / 0 fail

### 2.8 Day 2 commit + push + progress.md
- [ ] **Stage + commit + push**
  - Commit message: `feat(subagent, sprint-54-2): US-2 Fork + AsTool modes + 8 unit tests`
- [ ] **Update progress.md with Day 2 actuals + drift fixes**

---

## Day 3 — US-3 Teammate Mode + Mailbox

### 3.1 New `agent_harness/subagent/mailbox.py` — MailboxStore
- [ ] **Implement MailboxStore**
  - `__init__()` creates `_queues: dict[UUID, dict[str, asyncio.Queue[Message]]]`
  - `async send(session_id, sender, recipient, content)` puts Message in queue
  - `async receive(session_id, recipient, timeout_s=5.0) -> Message | None` `asyncio.wait_for(q.get())` with TimeoutError → None
  - `clear(session_id)` removes session entry
  - **Per-request DI** — NOT module-level singleton (per AD-Test-1 53.6 lesson; per-instance no autouse fixture needed)
  - File header per file-header-convention
  - DoD: matches plan §Technical Spec skeleton

### 3.2 New `agent_harness/subagent/modes/teammate.py` — TeammateExecutor
- [ ] **Implement TeammateExecutor**
  - `__init__(enforcer, mailbox, chat_client_factory)`
  - `async spawn(role, agent_spec, budget, trace_context) -> SubagentHandle`
  - Flow: pre-call `enforcer.check_concurrent`; create child loop in `asyncio.create_task` with budget guard wrapper; return SubagentHandle (subagent_id + future)
  - Cancellation: try/finally → on outer task cancel, ensure child task.cancel() + await task (per Risk row 2)
  - File header per file-header-convention
  - DoD: matches plan §US-3 acceptance

### 3.3 Modify `agent_harness/subagent/dispatcher.py` — wire spawn_teammate()
- [ ] **Replace `NotImplementedError`**
  - `spawn_teammate()` delegates to `self._teammate.spawn(...)`

### 3.4 New `tests/unit/agent_harness/subagent/test_mailbox.py` — 5 cases
- [ ] **Implement 5 unit tests**
  - test_mailbox_send_receive_round_trip
  - test_mailbox_per_session_isolation
  - test_mailbox_per_recipient_isolation
  - test_mailbox_receive_timeout_returns_none
  - test_mailbox_clear_drops_session_queues
  - Verify: 5 passed

### 3.5 New `tests/unit/agent_harness/subagent/test_teammate.py` — 3 cases
- [ ] **Implement 3 unit tests**
  - test_teammate_spawn_returns_handle
  - test_teammate_child_can_send_to_parent_via_mailbox
  - test_teammate_budget_exceeded_cancels_child_task
  - Verify: 3 passed

### 3.6 Day 3 sanity checks
- [ ] **mypy --strict on touched files** → 0 errors
- [ ] **black + isort + flake8** → clean
- [ ] **6 V2 lints** → 6/6 green
- [ ] **Backend full pytest** → ~1331 passed (1323 + 8 new) / 0 fail

### 3.7 Day 3 commit + push + progress.md
- [ ] **Stage + commit + push**
  - Commit message: `feat(subagent, sprint-54-2): US-3 Teammate mode + Mailbox + 8 unit tests`
- [ ] **Update progress.md with Day 3 actuals**

---

## Day 4 — US-4 Handoff Mode + AgentLoop Wiring + US-5 Tools + AD-Cat10-Obs-1 + Retrospective + PR

### 4.1 US-4 — New `agent_harness/subagent/modes/handoff.py` — HandoffExecutor
- [ ] **Implement HandoffExecutor**
  - `__init__(enforcer, chat_client_factory)`
  - `async execute(parent_state, target_agent, handoff_context, budget) -> SubagentResult`
  - Flow: parent state.messages append [handoff context] → build child loop with target_agent prompt + parent.messages → run child loop → return SubagentResult(mode=HANDOFF)
  - File header per file-header-convention
  - DoD: matches plan §US-4 acceptance

### 4.2 US-4 — Modify `agent_harness/subagent/dispatcher.py` — wire handoff_to()
- [ ] **Replace last `NotImplementedError`**
  - `handoff_to()` delegates to `self._handoff.execute(...)`
  - DoD: all 4 mode methods working

### 4.3 US-4 — Modify `agent_harness/orchestrator_loop/loop.py` — task_spawn / handoff dispatch + 2 events
- [ ] **Add `subagent_dispatcher: SubagentDispatcher | None = None` to AgentLoop init**
  - Backward compat: existing callers default None → no behavior change
- [ ] **Tool dispatch path: handle `tool_call.name == "task_spawn"`**
  - Call dispatcher.fork() → emit `SubagentSpawned(subagent_id, mode)` → await result → emit `SubagentCompleted(subagent_id, status, summary)` → append SubagentResult.summary as user message via SubagentResultReducer (53.4 stub)
- [ ] **Tool dispatch path: handle `tool_call.name == "handoff"`**
  - Set `state._pending_handoff = HandoffSpec(target=..., context=...)` → after current turn yield `LoopCompleted(status="handoff", handoff_target=...)` instead of normal completion
  - DoD: existing AgentLoop tests still pass (backward compat verify)

### 4.4 US-4 — Modify `backend/src/api/v1/chat/sse.py` — add 2 isinstance branches (per Day 0 探勘 findings)
- [ ] **Per `feedback_sse_serializer_scope_check.md` 教訓**
  - Add isinstance branch for SubagentSpawned → JSON payload with subagent_id + mode
  - Add isinstance branch for SubagentCompleted → JSON payload with subagent_id + status + summary
  - Verify: `grep "SubagentSpawned\|SubagentCompleted" backend/src/api/v1/chat/sse.py` → 2 matches
  - DoD: SSE event 可正確序列化；chat router e2e 不 raise NotImplementedError

### 4.5 US-4 — New tests
- [ ] **`tests/unit/agent_harness/subagent/test_handoff.py` — 3 cases**
  - test_handoff_appends_context_to_child_messages
  - test_handoff_returns_subagent_result_with_handoff_mode
  - test_handoff_budget_token_exceeded_returns_budget_exceeded_status
- [ ] **`tests/integration/agent_harness/subagent/test_loop_subagent_integration.py` — 4 cases**
  - test_loop_emits_subagent_spawned_on_task_spawn_tool_call
  - test_loop_appends_subagent_summary_after_completion
  - test_loop_handoff_yields_loop_completed_with_handoff_status
  - test_loop_concurrent_subagents_respect_budget_max_concurrent
  - Verify: 7 tests passed

### 4.6 US-5 — New `agent_harness/subagent/tools.py`
- [ ] **Implement make_task_spawn_tool factory**
  - `make_task_spawn_tool(dispatcher) -> tuple[ToolSpec, handler]`
  - input_schema: task / budget (optional dict) / mode (Literal["fork", "as_tool"])
  - handler dispatches to dispatcher.fork() or dispatcher.as_tool()
- [ ] **Implement make_handoff_tool factory**
  - `make_handoff_tool(dispatcher) -> tuple[ToolSpec, handler]`
  - input_schema: target_role / handoff_context
  - handler sets `state._pending_handoff` flag

### 4.7 US-5 — Wire 2 tools into AgentLoop init
- [ ] **Auto-register when dispatcher provided**
  - When `subagent_dispatcher is not None and tool_registry is not None`: register both tools
  - DoD: LLM 可 tool_call "task_spawn" / "handoff"

### 4.8 US-5 — AD-Cat10-Obs-1 closure: 4 verifier classes wire tracer + metrics
- [ ] **Modify rules_based.py / llm_judge.py / cat9_fallback.py / cat9_mutator.py**
  - Each verifier `__init__` accepts `tracer: Tracer | None = None` + `metrics: MetricsEmitter | None = None` (with NullTracer / NullMetricsEmitter defaults)
  - Each `verify()` wraps body in `with self._tracer.start_span(f"verifier.{name}", trace_context):`
  - Each `verify()` records 3 metrics:
    - `verification_pass_rate` (gauge with verifier_type + tenant_id labels)
    - `verification_duration_seconds` (histogram with verifier_type label)
    - `verification_correction_attempts` only in correction_loop wrapper (already does; verify still works)
  - DoD: AD-Cat10-Obs-1 closure (54.1 retro Q4 deferred item)

### 4.9 US-5 — New tests
- [ ] **`tests/integration/agent_harness/subagent/test_subagent_tools.py` — 3 cases**
  - test_task_spawn_tool_callable_returns_subagent_result
  - test_handoff_tool_callable_sets_pending_handoff_flag
  - test_task_spawn_tool_with_budget_exceeded_returns_status
- [ ] **`tests/unit/agent_harness/verification/test_observability.py` — 4 cases (closes AD-Cat10-Obs-1)**
  - test_rules_based_verify_emits_tracer_span (mock tracer)
  - test_llm_judge_verify_emits_3_metrics
  - test_cat9_fallback_wrapper_emits_span_for_inner_judge
  - test_verifier_metric_labels_include_tenant_id
  - Verify: 7 tests passed

### 4.10 Sprint final verification
- [ ] **AD-Cat10-Obs-1 closure grep evidence**
  - `grep "self._tracer.start_span" backend/src/agent_harness/verification/` → ≥ 4 matches (one per verifier)
  - `pytest backend/tests/unit/agent_harness/verification/test_observability.py -v` → 4 passed
- [ ] **Cat 11 Level 4 evidence**
  - `python -c "from agent_harness.subagent import DefaultSubagentDispatcher, BudgetEnforcer, MailboxStore; from agent_harness.subagent.modes import ForkExecutor, TeammateExecutor, HandoffExecutor, AsToolWrapper; print('Cat 11 Level 4 imports OK')"`
  - 主流量 e2e tests (test_loop_subagent_integration.py + test_subagent_tools.py) all 7 passing
- [ ] **Full sweep**
  - pytest 全綠 (~1342 expected = 1305 baseline + ~37 new)
  - mypy --strict on all touched files (0 errors)
  - black + isort + flake8 + run_all.py green
  - LLM SDK leak: 0 (especially `subagent/`)
  - Frontend Playwright e2e 11 specs green (regression sanity)
  - Cat 11 coverage ≥ 80% (per code-quality.md)

### 4.11 Day 4 retrospective.md
- [ ] **Create retrospective.md**
  - Path: `docs/03-implementation/agent-harness-execution/phase-54-verification-subagent/sprint-54-2-cat11-subagent/retrospective.md`
- [ ] **Answer 6 mandatory questions per 54.1 template**
  - Q1 Goal achieved + Cat 11 Level 4 evidence + AD-Cat10-Obs-1 closed grep
  - Q2 Estimated vs actual + **calibration multiplier 0.55 第 3 次驗證** (committed 12-13 hr; actual / committed ratio; 3-sprint window mean = (1.01 + 0.69 + ratio_54.2) / 3; if mean stays in [0.85, 1.20] → multiplier 0.55 confirmed stable; else lower to 0.45)
  - Q3 What went well (≥ 3)
  - Q4 What can improve (≥ 3 + follow-up actions)
  - Q5 V2 9-discipline self-check (per item ✅/⚠️ — especially AP-3 範疇歸屬 + AP-6 worktree 不偷加)
  - Q6 New AD logged (Phase 55 candidates; e.g., teammate mailbox 持久化 / handoff vs HITL pause priority / token-not-word truncation refinement)

### 4.12 PR open + closeout
- [ ] **Final commit + push**
  - Commit message: `docs(closeout, sprint-54-2): retrospective + Day 4 progress + final marks`
- [ ] **Open PR**
  - Title: `Sprint 54.2: Cat 11 Subagent (Level 4) + AD-Cat10-Obs-1 — V2 19→20/22 (91%)`
  - Body: Summary + plan link + checklist link + 5 USs status + AD-Cat10-Obs-1 closed + Anti-pattern checklist (especially AP-3 + AP-6) + verification evidence
  - Command: `gh pr create --title "..." --body "..."`
- [ ] **Wait for 5 active CI checks**
  - Backend CI (PG16) / V2 Lint / E2E Tests / Frontend CI / Playwright E2E
  - Per AD-CI-5 paths-filter workaround: if Frontend E2E SKIPPED on backend-only PR, touch `playwright-e2e.yml` header
- [ ] **Normal merge after green** (solo-dev policy: review_count=0)
  - Command: `gh pr merge <num> --merge --delete-branch`
- [ ] **Verify main HEAD has merge commit**

### 4.13 Cleanup + memory update
- [ ] **Pull main + verify**
- [ ] **Delete local feature branch**: `git branch -d feature/sprint-54-2-cat11-subagent`
- [ ] **Verify main 5 active CI green post-merge**
- [ ] **Memory update**
  - Create: `memory/project_phase54_2_cat11_subagent.md`
  - Add to MEMORY.md index
  - Mark V2 progress: **19/22 → 20/22 (91%)**; Cat 11 Level 4; AD-Cat10-Obs-1 closed
- [ ] **Working tree clean check**: `git status --short`

### 4.14 Update SITUATION-V2-SESSION-START.md
- [ ] **Update §8 Open Items**
  - Move AD-Cat10-Obs-1 to Closed
  - Add new AD from 54.2 retrospective Q6 (if any)
  - Add Phase 55 candidate scope (business domain + canary)
- [ ] **Update §9 milestones**
  - Add Sprint 54.2 row with merge SHA + Cat 11 Level 4 + AD-Cat10-Obs-1 closed
  - Update header summary: V2 20/22 (91%)
- [ ] **Update §10 必做 if needed**
  - If calibration multiplier needs 3rd-round adjust based on Q2 verify

---

## Verification Summary（Day 4 final 必填）

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | All 5 USs delivered (Cat 11 Level 4 + AD-Cat10-Obs-1 closed) | [ ] | PR #__ merged |
| 2 | Cat 11 reaches Level 4 (主流量強制) | [ ] | test_loop_subagent_integration.py 4/4 + test_subagent_tools.py 3/3 green |
| 3 | AD-Cat10-Obs-1 closed (4 verifiers tracer + 3 metrics) | [ ] | grep + test_observability.py 4/4 green |
| 4 | DefaultSubagentDispatcher production (4 modes + budget) | [ ] | dispatcher.py imports + 7 mode tests green |
| 5 | BudgetEnforcer 3 cap types + summary truncation | [ ] | test_budget.py 8/8 green |
| 6 | Fork mode no parent-context pollution | [ ] | test_fork.py 5/5 green |
| 7 | AsTool mode wraps to ToolSpec | [ ] | test_as_tool.py 3/3 green |
| 8 | Teammate Mailbox per-session isolation | [ ] | test_mailbox.py 5/5 green |
| 9 | Teammate cancellation cascade clean | [ ] | test_teammate.py 3/3 green |
| 10 | Handoff yields LoopCompleted(status="handoff") | [ ] | test_handoff.py 3/3 green |
| 11 | task_spawn / handoff tools LLM-callable | [ ] | test_subagent_tools.py 3/3 green |
| 12 | SSE serializer covers SubagentSpawned / SubagentCompleted | [ ] | grep sse.py 2 matches |
| 13 | pytest ~1342 / 0 fail | [ ] | command output |
| 14 | mypy --strict clean on touched files | [ ] | command output |
| 15 | run_all.py green (6 V2 lints) | [ ] | wrapper output |
| 16 | LLM SDK leak: 0 (especially `subagent/`) | [ ] | grep |
| 17 | Cat 11 coverage ≥ 80% | [ ] | pytest --cov |
| 18 | Frontend Playwright e2e 11 specs green | [ ] | CI |
| 19 | Anti-pattern checklist 11 points (especially AP-3 + AP-6) | [ ] | retrospective |
| 20 | retrospective.md filled (6 questions + calibration verify 第 3 次 + 3-sprint window mean) | [ ] | file exists |
| 21 | Memory updated (project_phase54_2 + index) | [ ] | files |
| 22 | SITUATION-V2-SESSION-START.md updated (§8 §9) | [ ] | file |
| 23 | Branches deleted (local + remote) | [ ] | git branch -a |
| 24 | V2 progress: **19/22 → 20/22 (91%)** | [ ] | memory + SITUATION-V2 §9 |
| 25 | AD-Cat10-Obs-1 closed in retrospective Q6 with evidence | [ ] | retrospective |
| 26 | Worktree mode NOT implemented (AP-6 verified clean) | [ ] | grep + retro confirms YAGNI |
