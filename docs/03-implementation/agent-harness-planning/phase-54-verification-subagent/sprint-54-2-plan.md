# Sprint 54.2 — Cat 11 Subagent Orchestration + AD-Cat10-Obs-1

> **Sprint Type**: V2 main progress sprint (Phase 54 closure — final 範疇 sprint before Phase 55 business domain)
> **Owner Categories**: Cat 11 (Subagent Orchestration, primary) / Cat 12 (Observability — AD-Cat10-Obs-1 verifier tracer + metrics) / Cat 1 (AgentLoop integration for handoff) / Cat 2 (task_spawn / handoff tools registration) / Cat 7 (SubagentResultReducer wiring; reuse 53.4 stub)
> **Phase**: 54 (Verification + Subagent — 2 sprints; this is 2/2)
> **Workload**: 5 days (Day 0-4); bottom-up est ~22.5 hr → calibrated commit **~12-13 hr** (multiplier 0.55 per AD-Sprint-Plan-1; **3rd application** after 53.7 ratio 1.01 + 54.1 ratio 0.69 → 2-sprint window mean ~0.85 still inside [0.85, 1.20] band; keep 0.55 default)
> **Branch**: `feature/sprint-54-2-cat11-subagent`
> **Plan Authority**: This document (per CLAUDE.md §Sprint Execution Workflow)
> **Roadmap Source**: 06-phase-roadmap.md §Sprint 54.2 + 01-eleven-categories-spec.md §範疇 11 + 17-cross-category-interfaces.md §1.1 / §2.1 / §3.1 / §4.1
> **Carryover absorbed (sub-scope)**: AD-Cat10-Obs-1 (Cat 12 observability for Cat 10 verifiers — 1 tracer span pattern + 3 metrics)

---

## Sprint Goal

Bring 範疇 11 (Subagent Orchestration) from **stub (Level 0)** to **Level 4 (主流量強制)** by:
- **US-1**: Implement `DefaultSubagentDispatcher` (production class implementing `SubagentDispatcher` ABC) with budget enforcement (`SubagentBudget` token / duration / concurrency caps) + summary cap enforcement (≤ `summary_token_cap`)
- **US-2**: Implement Fork mode + AsTool mode (parent context copy / agents-as-tool wrapping; both stateless / no mailbox)
- **US-3**: Implement Teammate mode + `MailboxStore` (in-memory pub/sub; per-session mailbox; Cat 7 reducer-friendly)
- **US-4**: Implement Handoff mode + AgentLoop wiring (parent yields control; child loop continues with appended context)
- **US-5**: Register `task_spawn` + `handoff` tools per 17.md §3.1 in Cat 2 ToolRegistry + sub-scope AD-Cat10-Obs-1 (verifier tracer span + 3 metrics) + Day 4 retrospective + closeout

Sprint 結束後：(a) 4 種 subagent 模式全部 production-ready；(b) `SubagentBudget` 強制 — token / duration / concurrency 任一超限即 abort；(c) `SubagentResult.summary` 強制 ≤ `summary_token_cap`（caller-defined，default 2000）；(d) `task_spawn` + `handoff` 兩 LLM-callable tool 註冊主流量；(e) AD-Cat10-Obs-1 closure — 4 verifier 類型（Rules / LLMJudge / 兩 wrapper）皆有 tracer span + 3 metrics；(f) **V2 進度 19/22 → 20/22 (91%)** — 主進度推進；剩 Phase 55 業務 domain + canary 1 sprint。

**主流量驗收標準**：
- `pytest backend/tests/integration/agent_harness/subagent/test_main_flow_subagent.py` 跑 e2e: AgentLoop → LLM emits tool_call("task_spawn") → DefaultSubagentDispatcher.fork() → child loop runs 1 turn → SubagentResult returned → parent loop appends summary → continues
- SSE event stream 包含 `subagent_spawned` + `subagent_completed` payload（serialize_loop_event 對 2 個 event 都有 isinstance branch；如 49.1 stub 未含則本 sprint 加）
- `DefaultSubagentDispatcher.fork()` p95 < 500ms 啟動延遲（不含 child LLM call 時間）
- Budget enforcement test: token cap 觸發 → child 立即 cancel + 回傳 `SubagentResult(status="budget_exceeded")`
- `SubagentResult.summary` 強制 ≤ `summary_token_cap`：超過自動截斷（不 swallow exception，紀錄 warning）
- `task_spawn` tool callable via mock LLM tool_call → handler returns SubagentResult JSON
- `handoff` tool callable → AgentLoop 標 `_pending_handoff` flag → 父 loop yield `LoopCompleted(status="handoff")`
- AD-Cat10-Obs-1 closure: `verifier.verify()` 每次呼叫產生 tracer span (`verifier.{name}`) + 3 metrics 記錄；驗 tracer / metrics emitter mock 接到 events
- Worktree 模式 ❌ 不對應（per V2 server-side decision；01-spec.md §範疇 11）— ABC 不含 worktree method

---

## Background

### V2 進度

- **19/22 sprints (86%)** completed (Phase 49-55 roadmap)
- 54.1 closed (Cat 10 Verification Loops Level 4 + AD-Cat9-1+2+3 closed via D8 wrapper pattern; calibration ratio 0.69)
- main HEAD: `c5a64c62` (Sprint 54.1 closeout PR #79)
- Cat 10 達 Level 4（主流量強制）；Cat 11 仍是 49.1 stub（Level 0：只有 SubagentBudget / SubagentResult / SubagentMode dataclasses + SubagentDispatcher ABC）；本 sprint 推進 Cat 11 從 Level 0 → Level 4，V2 主進度 **19/22 → 20/22 (91%)**

### 為什麼 54.2 是 Cat 11 而不是繼續 audit cycle

54.1 retrospective Q5/Q6 + SITUATION-V2-SESSION-START.md §8 列出 3 個候選 bundle scope。選 **Bundle A + 局部 B**（用戶 approve 2026-05-04）原因：

1. **主進度推進**：19/22 → 20/22 接近 V2 完成（91%）；Cat 11 是最後一個範疇 sprint
2. **Phase 55 (business domain) 依賴**：5 個業務領域工具（patrol / correlation / rootcause / audit / incident）的複雜分析任務需 subagent 拆分（patrol_diagnose 拆出 multiple parallel root cause subagents）；Phase 55 啟動前 Cat 11 必須 ready
3. **AD-Cat10-Obs-1 自然搭載**：54.1 D8 wrapper 已建 verifier 入口；本 sprint 加 Cat 12 觀測層成本低（共用 Tracer ABC + MetricRecorded event；54.1 retro Day 4 已 spec 出 3 metrics）；同 sprint ROI 高
4. **Cat 7 reducer 已備**：53.4 已加 SubagentResultReducer stub（_contracts/subagent.py + reducer.py）；本 sprint wire AgentLoop 即可
5. **Risk balance**：Cat 11 風險高（4 模式 + budget + mailbox + handoff），但 54.1 ratio 0.69 已 banked +3 hr 緩衝；calibration multiplier 0.55 第 3 次應用驗證 stable phase

### 既有結構（Day 0 探勘已 grep 確認 — 從 §0.2 預演）

```
backend/src/agent_harness/
├── _contracts/
│   ├── subagent.py                                          # ✅ SubagentMode (Enum: FORK/TEAMMATE/HANDOFF/AS_TOOL) / SubagentBudget / SubagentResult — 49.1 stub stable
│   └── events.py                                            # ✅ SubagentSpawned / SubagentCompleted events — Day 0 grep confirm 49.1 stub or extend
├── subagent/                                                # 🚧 Cat 11 stub (49.1; Level 0)
│   ├── __init__.py                                          # ✅ exports SubagentDispatcher ABC (5 lines)
│   ├── _abc.py                                              # ✅ SubagentDispatcher ABC (67 lines; fork / spawn_teammate / handoff_to / as_tool methods)
│   └── README.md                                            # ✅ design notes
├── orchestrator_loop/
│   └── loop.py                                              # 🚧 待加 task_spawn handler + handoff handler in tool dispatch path
├── state_mgmt/
│   └── reducer.py                                           # ✅ SubagentResultReducer (53.4 stub) — wire AgentLoop on subagent return
├── tools/
│   └── registry.py                                          # 🚧 待註冊 task_spawn + handoff tools per 17.md §3.1
└── verification/                                            # 54.1 base for AD-Cat10-Obs-1 sub-scope
    ├── rules_based.py                                       # ✅ tracer span TODO; AD-Cat10-Obs-1 wires
    ├── llm_judge.py                                         # ✅ tracer span TODO; AD-Cat10-Obs-1 wires
    ├── cat9_fallback.py                                     # ✅ tracer span TODO; AD-Cat10-Obs-1 wires
    └── cat9_mutator.py                                      # ✅ tracer span TODO; AD-Cat10-Obs-1 wires
```

### V2 紀律 9 項對齐確認

1. **Server-Side First** ✅ Subagent 全 server-side；Mailbox 是 in-memory per-session（無 worktree / 無 file-based mailbox per V2 §範疇 11 worktree decision）
2. **LLM Provider Neutrality** ✅ Subagent child loop 透過 ChatClient ABC（同主 loop）；DefaultSubagentDispatcher **不 import openai/anthropic**；CI lint 強制
3. **CC Reference 不照搬** ✅ CC `Worktree` 模式不對應（git-isolated branch 不適合 multi-tenant server）；CC `Teammate file-based mailbox` 改 in-memory state；CC 概念保留，實作完全重寫
4. **17.md Single-source** ✅ SubagentBudget / SubagentResult / SubagentMode / SubagentDispatcher ABC 全在 49.1 stub；本 sprint **不新增 type / ABC**；如需擴 Literal（e.g. AS_TOOL_PARALLEL）必須同步更新 17.md §1.1
5. **11+1 範疇歸屬** ✅ 全部 dispatcher 實作在 `agent_harness/subagent/`；mailbox 在 `subagent/mailbox.py`；4 模式在 `subagent/modes/{fork,teammate,handoff,as_tool}.py`（每模式獨立檔；AP-3 範疇歸屬合規）
6. **04 anti-patterns** ✅ AP-3 (Cross-Directory Scattering) — subagent infra 只在 `subagent/`；AP-4 (Potemkin) — 每 mode 必有 unit test 證明 fail path；AP-6 (Hybrid Bridge Debt) — Worktree 模式不實作（YAGNI；用戶從未需要）
7. **Sprint workflow** ✅ plan → checklist → Day 0 探勘 → code → progress → retro；本文件依 54.1 plan 結構鏡射（13 sections / Day 0-4）
8. **File header convention** ✅ 所有新建 .py / .md 含 Purpose / Category / Scope / Modification History
9. **Multi-tenant rule** ✅ Subagent 繼承父 LoopState 的 tenant_id；budget enforcement 在 dispatcher 層 enforce；mailbox per-session（不跨 tenant）；audit log entry 含 tenant_id

---

## User Stories

### US-1: DefaultSubagentDispatcher + Budget Enforcement Foundation (Cat 11 Level 1 → Level 2)

**As** a Cat 11 Subagent implementer
**I want** `DefaultSubagentDispatcher` 實作（subclass `SubagentDispatcher` ABC）+ token / duration / concurrency budget enforcement + `SubagentResult.summary` 強制截斷至 `summary_token_cap`
**So that** 主流量 AgentLoop 可透過 dispatcher spawn child agents；budget 強制保護租戶 token 不被失控 fork 燒爆；caller-defined summary cap 確保父 context 不被 child raw output 污染

**Acceptance**:
- 新建 `agent_harness/subagent/dispatcher.py`：`DefaultSubagentDispatcher(SubagentDispatcher)` skeleton (4 模式 method 暫 raise NotImplementedError；US-2/3/4 補完)
- 新建 `agent_harness/subagent/budget.py`：`BudgetEnforcer` class
  - `check_concurrent(active_count: int, budget: SubagentBudget)` → raise `BudgetExceededError` if active >= max_concurrent
  - `check_tokens(used: int, budget: SubagentBudget)` → raise if used > max_tokens
  - `check_duration(elapsed_s: float, budget: SubagentBudget)` → raise if elapsed > max_duration_s
  - `truncate_summary(text: str, cap: int) -> tuple[str, bool]` → returns `(truncated_text, was_truncated)` 用 tiktoken-style 截斷 token 不字元
- 新建 `agent_harness/subagent/exceptions.py`：`BudgetExceededError(Exception)` + `SubagentLaunchError(Exception)`
- 修改 `agent_harness/subagent/__init__.py`：re-exports `DefaultSubagentDispatcher` / `BudgetEnforcer` / `BudgetExceededError`
- 新建 `tests/unit/agent_harness/subagent/test_budget.py`：≥ 6 cases
  - test_check_concurrent_pass / test_check_concurrent_exceeds_raises
  - test_check_tokens_pass / test_check_tokens_exceeds_raises
  - test_check_duration_pass / test_check_duration_exceeds_raises
  - test_truncate_summary_under_cap_no_truncation / test_truncate_summary_over_cap_returns_truncated_flag
- 新建 `tests/unit/agent_harness/subagent/test_dispatcher_init.py`：≥ 2 cases
  - test_dispatcher_inherits_abc / test_dispatcher_methods_raise_not_implemented (will be filled by US-2/3/4)

**Files**:
- 新建: `backend/src/agent_harness/subagent/dispatcher.py`
- 新建: `backend/src/agent_harness/subagent/budget.py`
- 新建: `backend/src/agent_harness/subagent/exceptions.py`
- 修改: `backend/src/agent_harness/subagent/__init__.py`（re-exports）
- 新建: `backend/tests/unit/agent_harness/subagent/test_budget.py`
- 新建: `backend/tests/unit/agent_harness/subagent/test_dispatcher_init.py`

### US-2: Fork Mode + AsTool Mode (stateless modes)

**As** a Cat 11 Subagent implementer
**I want** Fork 模式（複製父 LoopState 的 messages 副本給子 agent；子任務探索；不污染父 context）+ AsTool 模式（包裝 agent_spec 為 ToolSpec 讓 LLM 當工具呼叫）
**So that** 兩 stateless 模式（無 mailbox 互動）先 working；US-3 Teammate 再加 mailbox 複雜度

**Acceptance**:
- 新建 `agent_harness/subagent/modes/__init__.py`：mode 子套件 init
- 新建 `agent_harness/subagent/modes/fork.py`：`ForkExecutor`
  - `async execute(parent_ctx: LoopContext, task: str, budget: SubagentBudget, trace_context: TraceContext) -> SubagentResult`
  - 流程：(1) deepcopy parent.messages；(2) append task as user message；(3) build child LoopState (new session_id; inherit tenant_id)；(4) run child AgentLoop with budget guards；(5) on completion: extract last assistant message + summarize via LLM if > summary_token_cap (call LLM-as-summarizer if needed) → return SubagentResult
- 新建 `agent_harness/subagent/modes/as_tool.py`：`AsToolWrapper`
  - `wrap(agent_spec: AgentSpec) -> ToolSpec`：returns ToolSpec with name="agent_{role}", input_schema={"task": str}, handler that internally calls ForkExecutor with bounded budget
  - AgentSpec dataclass at `_contracts/subagent.py` if 49.1 stub has it; else add (Day 0 grep confirm)
- 修改 `agent_harness/subagent/dispatcher.py`：`fork()` method delegates to `ForkExecutor`；`as_tool()` method delegates to `AsToolWrapper`
- 新建 `tests/unit/agent_harness/subagent/test_fork.py`：≥ 5 cases
  - test_fork_copies_parent_messages_no_mutation (assert id(parent_msgs) != id(child_msgs))
  - test_fork_returns_subagent_result_with_summary
  - test_fork_summary_truncated_to_cap
  - test_fork_budget_token_exceeded_returns_budget_exceeded_status
  - test_fork_propagates_tenant_id_to_child
- 新建 `tests/unit/agent_harness/subagent/test_as_tool.py`：≥ 3 cases
  - test_as_tool_returns_toolspec_with_correct_schema
  - test_as_tool_handler_calls_fork_executor
  - test_as_tool_handler_returns_result_summary

**Files**:
- 新建: `backend/src/agent_harness/subagent/modes/__init__.py`
- 新建: `backend/src/agent_harness/subagent/modes/fork.py`
- 新建: `backend/src/agent_harness/subagent/modes/as_tool.py`
- 修改: `backend/src/agent_harness/subagent/dispatcher.py`（fork / as_tool methods）
- 新建: `backend/tests/unit/agent_harness/subagent/test_fork.py`
- 新建: `backend/tests/unit/agent_harness/subagent/test_as_tool.py`

### US-3: Teammate Mode + In-Memory Mailbox

**As** a Cat 11 Subagent implementer
**I want** Teammate 模式（獨立 child agent 透過 mailbox pub/sub 與父通信；不複製父 context；in-memory store; per-session 隔離）
**So that** 多 agent 協作場景 working（e.g., research agent + writer agent 平行）；不需 file-based mailbox（V2 server-side）

**Acceptance**:
- 新建 `agent_harness/subagent/mailbox.py`：`MailboxStore` class
  - `async send(session_id: UUID, sender: str, recipient: str, content: str) -> None`
  - `async receive(session_id: UUID, recipient: str, timeout_s: float = 5.0) -> Message | None`
  - `clear(session_id: UUID)` — 清除 session 結束後 mailbox
  - In-memory `dict[UUID, dict[str, asyncio.Queue]]`：per-session, per-recipient queue
  - **Per-request DI** （per AD-Test-1 53.6 lesson）：MailboxStore 不 module-level singleton；AgentLoop 持有 instance
- 新建 `agent_harness/subagent/modes/teammate.py`：`TeammateExecutor`
  - `async spawn(role: str, agent_spec: AgentSpec, budget: SubagentBudget, mailbox: MailboxStore, trace_context: TraceContext) -> SubagentHandle`
  - 啟動 child loop in `asyncio.create_task`；返回 SubagentHandle (subagent_id + completion future)
  - SubagentHandle dataclass: 49.1 stub 是否有 — Day 0 grep confirm；缺則加到 `_contracts/subagent.py`
- 修改 `agent_harness/subagent/dispatcher.py`：`spawn_teammate()` method delegates to `TeammateExecutor`
- 新建 `tests/unit/agent_harness/subagent/test_mailbox.py`：≥ 5 cases
  - test_mailbox_send_receive_round_trip
  - test_mailbox_per_session_isolation (msg in session A invisible to session B)
  - test_mailbox_per_recipient_isolation
  - test_mailbox_receive_timeout_returns_none
  - test_mailbox_clear_drops_session_queues
- 新建 `tests/unit/agent_harness/subagent/test_teammate.py`：≥ 3 cases
  - test_teammate_spawn_returns_handle
  - test_teammate_child_can_send_to_parent_via_mailbox
  - test_teammate_budget_exceeded_cancels_child_task

**Files**:
- 新建: `backend/src/agent_harness/subagent/mailbox.py`
- 新建: `backend/src/agent_harness/subagent/modes/teammate.py`
- 修改: `backend/src/agent_harness/subagent/dispatcher.py`（spawn_teammate method）
- 修改 (potential): `backend/src/agent_harness/_contracts/subagent.py`（如缺 SubagentHandle dataclass）
- 新建: `backend/tests/unit/agent_harness/subagent/test_mailbox.py`
- 新建: `backend/tests/unit/agent_harness/subagent/test_teammate.py`

### US-4: Handoff Mode + AgentLoop Wiring

**As** a Cat 1 Orchestrator integrator
**I want** Handoff 模式（父 agent 完全交棒給 child；父 yield `LoopCompleted(status="handoff")`；child loop 接續 with appended handoff context）+ AgentLoop integration that detects `_pending_handoff` flag and emits handoff event
**So that** 主流量支援 AGI-style agent transition（specialist takes full control）；OpenAI agents-handoff pattern works server-side

**Acceptance**:
- 新建 `agent_harness/subagent/modes/handoff.py`：`HandoffExecutor`
  - `async execute(parent_state: LoopState, target_agent: AgentSpec, handoff_context: str, budget: SubagentBudget) -> SubagentResult`
  - 流程：(1) parent state.messages append [handoff context]；(2) build child loop with target_agent's prompt + parent.messages；(3) run child loop until completion；(4) return SubagentResult (mode=HANDOFF)
- 修改 `agent_harness/subagent/dispatcher.py`：`handoff_to()` method delegates to `HandoffExecutor`
- 修改 `agent_harness/orchestrator_loop/loop.py`：
  - Add `subagent_dispatcher: SubagentDispatcher | None = None` to `__init__`
  - In tool dispatch path：if tool_call.name == "task_spawn" → call dispatcher.fork() → emit `SubagentSpawned` + `SubagentCompleted` LoopEvents → append SubagentResult.summary as user message via `SubagentResultReducer` (53.4 stub already wired)
  - In tool dispatch path：if tool_call.name == "handoff" → set `state._pending_handoff = HandoffSpec(target=..., context=...)` → after current turn yield `LoopCompleted(status="handoff", handoff_target=...)` instead of normal completion
- 修改 `agent_harness/orchestrator_loop/sse.py`：add isinstance branches for `SubagentSpawned` / `SubagentCompleted` (per `feedback_sse_serializer_scope_check.md` — Day 0 grep confirm whether already exists)
- 新建 `tests/unit/agent_harness/subagent/test_handoff.py`：≥ 3 cases
  - test_handoff_appends_context_to_child_messages
  - test_handoff_returns_subagent_result_with_handoff_mode
  - test_handoff_budget_token_exceeded_returns_budget_exceeded_status
- 新建 `tests/integration/agent_harness/subagent/test_loop_subagent_integration.py`：≥ 4 cases
  - test_loop_emits_subagent_spawned_on_task_spawn_tool_call
  - test_loop_appends_subagent_summary_after_completion
  - test_loop_handoff_yields_loop_completed_with_handoff_status
  - test_loop_concurrent_subagents_respect_budget_max_concurrent

**Files**:
- 新建: `backend/src/agent_harness/subagent/modes/handoff.py`
- 修改: `backend/src/agent_harness/subagent/dispatcher.py`（handoff_to method）
- 修改: `backend/src/agent_harness/orchestrator_loop/loop.py`（dispatcher param + 2 tool dispatch paths + 2 LoopEvent emits）
- 修改: `backend/src/api/v1/chat/sse.py`（add 2 isinstance branches if missing per 49.1 stub status）
- 新建: `backend/tests/unit/agent_harness/subagent/test_handoff.py`
- 新建: `backend/tests/integration/agent_harness/subagent/test_loop_subagent_integration.py`

### US-5: task_spawn / handoff Tools + AD-Cat10-Obs-1 (verifier observability) + Day 4 Closeout

**As** an LLM consumer of the agent harness AND Cat 12 Observability owner
**I want** `task_spawn` + `handoff` tools 註冊到 Cat 2 ToolRegistry（per 17.md §3.1）讓 LLM 可 self-trigger subagent，加上 AD-Cat10-Obs-1 closure（4 verifier 類型加 tracer span + 3 metrics from 54.1 retro deferred）+ Day 4 retrospective + closeout
**So that** Cat 11 達 Level 4（主流量強制 + LLM 自呼叫 + 完整觀測）；Cat 10 verifier 觀測層補完；54.1 retro AD-Cat10-Obs-1 closed

**Acceptance**:
- 新建 `agent_harness/subagent/tools.py`：
  - `make_task_spawn_tool(dispatcher: SubagentDispatcher) -> tuple[ToolSpec, handler]`
    - input_schema = `{"task": str, "budget": Optional[dict], "mode": Literal["fork", "as_tool"] = "fork"}`
    - handler dispatches to `dispatcher.fork()` or `dispatcher.as_tool()` per mode
    - returns `{"subagent_id": str, "summary": str, "status": Literal["completed", "budget_exceeded", "failed"]}`
  - `make_handoff_tool(dispatcher: SubagentDispatcher) -> tuple[ToolSpec, handler]`
    - input_schema = `{"target_role": str, "handoff_context": str}`
    - handler sets `state._pending_handoff` flag (consumed by AgentLoop in next turn)
    - returns `{"handoff_initiated": True, "target_role": str}`
- 修改 `agent_harness/orchestrator_loop/loop.py`：在 init 註冊 2 tools 到 tool_registry (when subagent_dispatcher provided)
- **AD-Cat10-Obs-1 sub-scope** (per 54.1 retro Q4 deferred)：
  - 修改 4 verifier 檔案（rules_based.py / llm_judge.py / cat9_fallback.py / cat9_mutator.py）：在 `verify()` 內加 tracer span：`with self._tracer.start_span(f"verifier.{self.__class__.__name__}"):`
  - 新建 metric emitter:
    - `verification_pass_rate{verifier_type, tenant_id}` (gauge)
    - `verification_duration_seconds{verifier_type}` (histogram, p50/p95/p99 buckets)
    - `verification_correction_attempts{outcome}` (counter)
  - Tracer + Metrics 透過 `_contracts.observability.Tracer` ABC（49.1 stub）；如缺 production class 則用 NullTracer 注入
- 新建 `tests/integration/agent_harness/subagent/test_subagent_tools.py`：≥ 3 cases
  - test_task_spawn_tool_callable_returns_subagent_result
  - test_handoff_tool_callable_sets_pending_handoff_flag
  - test_task_spawn_tool_with_budget_exceeded_returns_status
- 新建 `tests/unit/agent_harness/verification/test_observability.py`：≥ 4 cases (closes AD-Cat10-Obs-1)
  - test_rules_based_verify_emits_tracer_span
  - test_llm_judge_verify_emits_3_metrics
  - test_cat9_fallback_wrapper_emits_span_for_inner_judge
  - test_verifier_metric_labels_include_tenant_id
- 新建 retrospective.md (Day 4) per 54.1 6-question template + calibration multiplier 第 3 次驗證
- 新建 progress.md daily entries (Day 0-4)

**Files**:
- 新建: `backend/src/agent_harness/subagent/tools.py`
- 修改: `backend/src/agent_harness/orchestrator_loop/loop.py`（register 2 tools at init）
- 修改 (4 files for AD-Cat10-Obs-1): `verification/rules_based.py` / `verification/llm_judge.py` / `verification/cat9_fallback.py` / `verification/cat9_mutator.py`
- 新建: `backend/tests/integration/agent_harness/subagent/test_subagent_tools.py`
- 新建: `backend/tests/unit/agent_harness/verification/test_observability.py`
- 新建: `docs/03-implementation/agent-harness-execution/phase-54-verification-subagent/sprint-54-2-cat11-subagent/progress.md`
- 新建: `docs/03-implementation/agent-harness-execution/phase-54-verification-subagent/sprint-54-2-cat11-subagent/retrospective.md`

---

## Technical Specifications

### File Skeleton — `agent_harness/subagent/dispatcher.py`

```python
"""
File: backend/src/agent_harness/subagent/dispatcher.py
Purpose: DefaultSubagentDispatcher production class; delegates to 4 mode executors with budget enforcement.
Category: 範疇 11 (Subagent Orchestration)
Scope: Sprint 54.2 US-1/2/3/4
"""
from __future__ import annotations
from agent_harness._contracts.subagent import (
    SubagentBudget, SubagentResult, SubagentMode, AgentSpec, SubagentHandle
)
from agent_harness._contracts import LoopContext, TraceContext
from agent_harness.subagent._abc import SubagentDispatcher
from agent_harness.subagent.budget import BudgetEnforcer
from agent_harness.subagent.modes.fork import ForkExecutor
from agent_harness.subagent.modes.teammate import TeammateExecutor
from agent_harness.subagent.modes.handoff import HandoffExecutor
from agent_harness.subagent.modes.as_tool import AsToolWrapper
from agent_harness.subagent.mailbox import MailboxStore

class DefaultSubagentDispatcher(SubagentDispatcher):
    def __init__(self, *, mailbox: MailboxStore, chat_client_factory=None):
        self._enforcer = BudgetEnforcer()
        self._fork = ForkExecutor(self._enforcer, chat_client_factory)
        self._teammate = TeammateExecutor(self._enforcer, mailbox, chat_client_factory)
        self._handoff = HandoffExecutor(self._enforcer, chat_client_factory)
        self._as_tool = AsToolWrapper(self._fork)

    async def fork(self, *, parent_ctx, task, budget, trace_context):
        return await self._fork.execute(parent_ctx, task, budget, trace_context)

    async def spawn_teammate(self, *, role, agent_spec, budget, trace_context):
        return await self._teammate.spawn(role, agent_spec, budget, trace_context)

    async def handoff_to(self, *, target_agent, handoff_context, parent_state, budget, trace_context):
        return await self._handoff.execute(parent_state, target_agent, handoff_context, budget)

    def as_tool(self, agent_spec):
        return self._as_tool.wrap(agent_spec)
```

### File Skeleton — `agent_harness/subagent/budget.py`

```python
"""
File: backend/src/agent_harness/subagent/budget.py
Purpose: Budget enforcement primitives; raise BudgetExceededError on cap breach.
Category: 範疇 11 (Subagent Orchestration)
Scope: Sprint 54.2 US-1
"""
from __future__ import annotations
from agent_harness._contracts.subagent import SubagentBudget
from agent_harness.subagent.exceptions import BudgetExceededError

class BudgetEnforcer:
    def check_concurrent(self, active_count: int, budget: SubagentBudget) -> None:
        if active_count >= budget.max_concurrent_subagents:
            raise BudgetExceededError(f"max_concurrent={budget.max_concurrent_subagents} reached")

    def check_tokens(self, used: int, budget: SubagentBudget) -> None:
        if used > budget.max_tokens:
            raise BudgetExceededError(f"token_used={used} > max_tokens={budget.max_tokens}")

    def check_duration(self, elapsed_s: float, budget: SubagentBudget) -> None:
        if elapsed_s > budget.max_duration_s:
            raise BudgetExceededError(f"elapsed={elapsed_s:.1f}s > max={budget.max_duration_s}s")

    def truncate_summary(self, text: str, cap: int) -> tuple[str, bool]:
        # Simple word-based truncation; production use tiktoken if needed
        words = text.split()
        if len(words) <= cap:
            return text, False
        return " ".join(words[:cap]) + " [...truncated]", True
```

### File Skeleton — `agent_harness/subagent/mailbox.py`

```python
"""
File: backend/src/agent_harness/subagent/mailbox.py
Purpose: In-memory per-session mailbox for Teammate-mode subagent communication.
Category: 範疇 11 (Subagent Orchestration)
Scope: Sprint 54.2 US-3
"""
from __future__ import annotations
import asyncio
from collections import defaultdict
from uuid import UUID
from agent_harness._contracts import Message

class MailboxStore:
    """Per-request DI; NOT module-level singleton (per AD-Test-1 53.6 lesson)."""

    def __init__(self) -> None:
        # session_id → recipient → asyncio.Queue[Message]
        self._queues: dict[UUID, dict[str, asyncio.Queue[Message]]] = defaultdict(dict)

    async def send(self, session_id: UUID, sender: str, recipient: str, content: str) -> None:
        q = self._queues[session_id].setdefault(recipient, asyncio.Queue())
        await q.put(Message(role="user", content=f"[from {sender}] {content}"))

    async def receive(self, session_id: UUID, recipient: str, timeout_s: float = 5.0) -> Message | None:
        q = self._queues[session_id].setdefault(recipient, asyncio.Queue())
        try:
            return await asyncio.wait_for(q.get(), timeout=timeout_s)
        except asyncio.TimeoutError:
            return None

    def clear(self, session_id: UUID) -> None:
        self._queues.pop(session_id, None)
```

### AD-Cat10-Obs-1 — Verifier observability snippet (US-5)

```python
# Modification to verification/rules_based.py (similar for llm_judge.py / cat9_fallback.py / cat9_mutator.py)

class RulesBasedVerifier(Verifier):
    def __init__(self, rules: list[Rule], name: str = "rules_based",
                 tracer: Tracer | None = None, metrics: MetricsEmitter | None = None):
        self._rules = rules
        self._name = name
        self._tracer = tracer or NullTracer()
        self._metrics = metrics or NullMetricsEmitter()

    async def verify(self, *, output, state, trace_context=None):
        start = time.monotonic()
        with self._tracer.start_span(f"verifier.{self._name}", trace_context):
            for rule in self._rules:
                ok, reason, suggestion = rule.check(output)
                if not ok:
                    duration = time.monotonic() - start
                    self._metrics.record_histogram("verification_duration_seconds",
                                                    duration, {"verifier_type": "rules_based"})
                    self._metrics.record_gauge("verification_pass_rate", 0.0,
                                               {"verifier_type": "rules_based",
                                                "tenant_id": str(state.tenant_id)})
                    return VerificationResult(passed=False, ...)
            duration = time.monotonic() - start
            self._metrics.record_histogram("verification_duration_seconds", duration, {...})
            self._metrics.record_gauge("verification_pass_rate", 1.0, {...})
            return VerificationResult(passed=True, ...)
```

### Pre-Push Lint Chain (unchanged from 54.1)

```bash
black backend/src --check && isort backend/src --check && flake8 backend/src && mypy backend/src --strict
python scripts/lint/run_all.py  # 6 V2 lints (per AD-Lint-1 closure 53.7)
cd frontend && npm run lint && npm run build  # if frontend touched (54.2 = backend-only)
```

---

## File Change List

### 新建（19+ 個）

**Cat 11 source** (10):
1. `backend/src/agent_harness/subagent/dispatcher.py`
2. `backend/src/agent_harness/subagent/budget.py`
3. `backend/src/agent_harness/subagent/exceptions.py`
4. `backend/src/agent_harness/subagent/mailbox.py`
5. `backend/src/agent_harness/subagent/tools.py`
6. `backend/src/agent_harness/subagent/modes/__init__.py`
7. `backend/src/agent_harness/subagent/modes/fork.py`
8. `backend/src/agent_harness/subagent/modes/teammate.py`
9. `backend/src/agent_harness/subagent/modes/handoff.py`
10. `backend/src/agent_harness/subagent/modes/as_tool.py`

**Tests** (11):
11. `backend/tests/unit/agent_harness/subagent/test_budget.py`
12. `backend/tests/unit/agent_harness/subagent/test_dispatcher_init.py`
13. `backend/tests/unit/agent_harness/subagent/test_fork.py`
14. `backend/tests/unit/agent_harness/subagent/test_as_tool.py`
15. `backend/tests/unit/agent_harness/subagent/test_mailbox.py`
16. `backend/tests/unit/agent_harness/subagent/test_teammate.py`
17. `backend/tests/unit/agent_harness/subagent/test_handoff.py`
18. `backend/tests/integration/agent_harness/subagent/test_loop_subagent_integration.py`
19. `backend/tests/integration/agent_harness/subagent/test_subagent_tools.py`
20. `backend/tests/unit/agent_harness/verification/test_observability.py`（AD-Cat10-Obs-1）

**Documentation** (2):
21. `docs/03-implementation/agent-harness-execution/phase-54-verification-subagent/sprint-54-2-cat11-subagent/progress.md`
22. `docs/03-implementation/agent-harness-execution/phase-54-verification-subagent/sprint-54-2-cat11-subagent/retrospective.md`

### 修改（6-7 個）

1. `backend/src/agent_harness/subagent/__init__.py`（re-exports 擴：DefaultSubagentDispatcher / BudgetEnforcer / MailboxStore / 4 mode executors）
2. `backend/src/agent_harness/orchestrator_loop/loop.py`（subagent_dispatcher param + 2 tool dispatch paths + 2 LoopEvent emits + register task_spawn/handoff tools at init）
3. `backend/src/api/v1/chat/sse.py`（add 2 isinstance branches for SubagentSpawned / SubagentCompleted — Day 0 grep confirm whether already exists）
4. `backend/src/agent_harness/verification/rules_based.py`（AD-Cat10-Obs-1: tracer span + metrics）
5. `backend/src/agent_harness/verification/llm_judge.py`（同上）
6. `backend/src/agent_harness/verification/cat9_fallback.py`（同上）
7. `backend/src/agent_harness/verification/cat9_mutator.py`（同上）
8. `backend/src/agent_harness/_contracts/subagent.py`（如缺 SubagentHandle / AgentSpec — Day 0 grep confirm）

### 修改（既有測試 — 視 Day 0 探勘需要）

- 既有 50.x AgentLoop tests：如 init 簽名變動破壞 → 升級 test 加 `subagent_dispatcher=None`
- 既有 54.1 verifier tests：如 init 簽名變動 → 升級 test 加 `tracer=None, metrics=None`

---

## Acceptance Criteria

### 主流量端到端驗收

- [ ] **US-1 BudgetEnforcer production**: 3 cap types（concurrent / tokens / duration）+ summary truncation；6 unit tests 全綠
- [ ] **US-2 Fork + AsTool modes**: Fork 不污染 parent messages；AsTool 返回有效 ToolSpec；budget exceeded 正確返回 status；8 unit tests 全綠
- [ ] **US-3 Teammate + Mailbox**: per-session mailbox isolation；timeout 行為正確；child cancellation 透過 budget；8 unit tests 全綠
- [ ] **US-4 Handoff + AgentLoop wiring**: AgentLoop 主流量 e2e — LLM emits task_spawn → SubagentSpawned event → SubagentCompleted event → SubagentResult.summary 注入 messages；handoff 正確 yield LoopCompleted(status="handoff")；7 tests 全綠
- [ ] **US-5 task_spawn / handoff tools + AD-Cat10-Obs-1**: 2 tools LLM-callable；4 verifier 全部 emit tracer span + 3 metrics；test_observability.py 4 cases 全綠

### 品質門檻

- [ ] pytest 全綠（baseline 1305 → 預期 ~1340+ passed，+35-40 from 54.2 new tests）
- [ ] mypy --strict 0 errors（所有 subagent/ + 改動 loop.py / sse.py / 4 verifier files）
- [ ] flake8 + black + isort green（pre-push 跑）
- [ ] 6 V2 lints green（透過 `run_all.py`）
- [ ] LLM SDK leak: 0（特別檢查 `subagent/modes/*.py` 不 import openai/anthropic）
- [ ] Cat 11 coverage ≥ 80%（per code-quality.md range owner target）
- [ ] 既有 Frontend e2e 11 specs 全綠（不應受 backend-only 改動影響）
- [ ] CI: 5 active checks green (Backend / V2 Lint / E2E / Frontend CI / Playwright E2E)

### 範疇對齐

- [ ] **Cat 11 reaches Level 4**: 主流量強制 + 4 modes production + 2 LLM-callable tools + budget enforcement + observability
- [ ] **AD-Cat10-Obs-1 closed**: 4 verifier types tracer span + 3 metrics; test_observability.py 4/4 green
- [ ] **17.md compliance**: SubagentBudget / SubagentResult / SubagentMode / SubagentDispatcher ABC 不變動 (single-source preserved); SubagentHandle / AgentSpec 如新增則同步更新 17.md §1.1

---

## Deliverables（見 checklist 詳細）

US-1 到 US-5 共 5 個 User Stories；checklist 拆分到 Day 0-4。

---

## Dependencies & Risks

### Dependencies

| Dependency | 來自 | 必須狀態 |
|------------|------|---------|
| 49.1 Cat 11 stub (SubagentDispatcher ABC + SubagentBudget/Result/Mode dataclasses) | 49.1 | ✅ verified by Day 0 探勘 (`_contracts/subagent.py` exists; `subagent/_abc.py` 67 lines) |
| 53.4 SubagentResultReducer (Cat 7 stub for parent context inject) | 53.4 | ✅ merged main; US-4 reuse |
| 54.1 4 verifier classes (target of AD-Cat10-Obs-1 modifications) | 54.1 | ✅ merged main `c0c2860a` |
| 50.1 Cat 6 OutputParser + Cat 1 AgentLoop run() AsyncIterator | 50.1 | ✅ merged main |
| 17.md §1.1 / §2.1 / §3.1 / §4.1 single-source contracts | planning | ✅ verified |
| ChatClient ABC (LLM Provider Neutrality) for child loops | 49.3+ | ✅ stable |
| 53.7 calibration multiplier 0.55 + sprint-workflow.md §Workload Calibration | 53.7 | ✅ merged main; 本 sprint plan §Workload 應用第 3 次 |

### Risks (per `sprint-workflow.md` §Common Risk Classes)

| Risk | Class | Mitigation |
|------|-------|-----------|
| Mailbox per-session state 在 TestClient 跨 event loop 可能 dead | C (Module singleton) | MailboxStore per-request DI（per AD-Test-1 53.6）；conftest.py autouse fixture 不需（因 per-instance 不 cache module-level） |
| Child loop launched in `asyncio.create_task` 在 budget timeout 時 cancellation cascade 可能 leak resource | logic | `try/finally` in TeammateExecutor.spawn → ensure task.cancel() + await task on timeout；test_teammate_budget_exceeded_cancels_child_task 鎖行為 |
| Fork mode `deepcopy(parent.messages)` 對大 context 性能差 | perf | Day 0 探勘量測；如 parent.messages > 50k tokens 改 shallow copy + COW message refs |
| `SubagentResult.summary` 強制截斷 < cap 但 LLM 給更長 → 用戶體驗 degradation | UX | Day 4 retro 收集 — 如真常觸發，後續 sprint 加 LLM-as-summarizer 預處理；本 sprint 用 word-based 截斷夠用 |
| Handoff mode 與 53.4 §HITL pause/resume 衝突 — 父 loop yield handoff vs ApprovalRequested 同 turn 雙信號 | logic | Day 1 探勘確認 LoopEvent stream order；handoff 必須在 verification 後（54.1 hook）；如有衝突優先 HITL |
| `feedback_sse_serializer_scope_check.md` 教訓：US-4 加 SubagentSpawned/Completed event emits 但 SSE serializer 漏 isinstance branch → chat router NotImplementedError | A (Day 0 探勘類) | Day 0 + Day 4 sanity check `grep "SubagentSpawned\|SubagentCompleted" backend/src/api/v1/chat/sse.py` |
| Paths-filter (per AD-CI-5)：54.2 是 backend-only 但可能還是要 touch playwright-e2e.yml header 才能滿足 required Frontend E2E check | A | sprint closeout PR 預計 touch playwright-e2e.yml header 一次（同 54.1 pattern） |
| AgentLoop 多 tool dispatch path（task_spawn / handoff / verify / hitl_*）耦合度增高 → 後續維護成本 | logic | tool dispatch 抽出 `_dispatch_tool_call()` helper（Day 4 重構 ROI 評估；如不重構納入 53.7-style banked AD） |
| `test_loop_subagent_integration.py` 初次跑可能因 mock LLM 簽名與 real ChatClient 偏差 fail | logic | 沿用 50.2 mock ChatClient pattern (test fixtures `_test_factories.py`); 同 54.1 D3 drift 借鑑 |
| AD-Cat10-Obs-1 改 4 verifier files：可能既有 54.1 verifier 測試破壞（init 簽名變） | logic | tracer / metrics 加 default `None` 參數 + NullTracer / NullMetricsEmitter；既有 test 不傳即 backward compat；Day 4 sanity check 全 verifier tests 仍綠 |

### 主流量驗證承諾

54.2 不允許「Cat 11 標 Level 4 但 dispatcher 在主流量為 opt-in / disabled」交付。`AgentLoop.run()` 主流量必須在 `subagent_dispatcher is not None` 時：(a) 註冊 task_spawn + handoff tools；(b) 在 tool dispatch path 處理 task_spawn → SubagentSpawned/Completed events emit；(c) 處理 handoff → yield LoopCompleted(status="handoff")。驗收測試從 chat router 入口（POST /chat）e2e 走完整流程。54.2 是 V2 主進度推進（19/22 → 20/22 = 91%）；交付即更新 SITUATION-V2-SESSION-START.md §9 milestones + 累計進度。

---

## Audit Carryover Section

### 從 53.x / 54.1 反激活（in scope；本 sprint 處理）

- ✅ **AD-Cat10-Obs-1** Cat 12 observability for verifiers (US-5 sub-scope: tracer span + 3 metrics + 4 verifier classes wired)

### Defer 至 Phase 55 / Audit cycle bundle（不在本 sprint scope）

- 🚧 **AD-Cat9-5** ToolGuardrail max-calls-per-session counter → Phase 55 / future audit cycle
- 🚧 **AD-Cat9-6** WORMAuditLog real-DB integration tests → Phase 55 / future audit cycle
- 🚧 **AD-Cat7-1** Full sole-mutator pattern → Phase 55 (與 Cat 11 SubagentResultReducer state 整合，但 grep-zero refactor 範圍跨 7 範疇；本 sprint 不處理)
- 🚧 **AD-Cat8-1/2/3** Cat 8 carryover → Phase 55 / future audit cycle
- 🚧 **AD-Hitl-7** Per-tenant HITLPolicy DB persistence → Phase 55
- 🚧 **AD-Cat10-Wire-1** chat router default-wire run_with_verification → Phase 55 frontend / 業務 sprint
- 🚧 **AD-Cat10-VisualVerifier** Playwright screenshot verifier → Phase 55+
- 🚧 **AD-Cat10-Frontend-Panel** verification UI → Phase 55 frontend
- 🚧 **AD-Cat9-1-WireDetectors** auto-wrap 4 detectors with LLMJudgeFallbackGuardrail → operator-driven (not a sprint)
- 🚧 **AD-Test-Module-Naming** prefix tests by category → next checklist template iteration
- 🚧 **AD-Plan-1** Day-0 plan-vs-repo verify rule → next plan template iteration (54.2 plan §Background 既有結構 應用此規則)
- 🚧 **AD-Lint-2** Drop per-day calibrated targets → next checklist template (54.2 checklist 已不寫)
- 🚧 **AD-CI-5** required_status_checks paths-filter long-term fix → independent infra track
- 🚧 **AD-CI-6** Deploy to Production chronic fail → independent infra track
- 🚧 **#31** V2 Dockerfile → independent infra track

### 54.2 新 Audit Debt（保留位置；retro 補充）

`AD-Cat11-*` / `AD-Subagent-*` 可能在 retrospective Q4 加入（e.g., teammate mailbox 持久化需求；handoff 與 HITL pause 雙信號優先級細節；budget enforcer 需更精確 token counter 不字元）。

---

## §10 Process 修補落地檢核

- [ ] Plan 文件起草前讀 54.1 plan + checklist 作 template (per `feedback_sprint_plan_use_prior_template.md`) ✅ done
- [ ] Plan §Background 既有結構 條目用 grep 驗證 (per AD-Plan-1 53.7 lesson) ✅ done in §0.2 預演
- [ ] Checklist 同樣以 54.1 為 template（Day 0-4，每 task 3-6 sub-bullets，含 DoD + Verify command；不寫 per-day calibrated targets per AD-Lint-2）
- [ ] Pre-push lint 完整跑 black + isort + flake8 + mypy + run_all.py（per AD-Lint-1 53.7 closure）
- [ ] Day 0 探勘 必 grep SubagentSpawned / SubagentCompleted 在 SSE serializer 出現位置（per `feedback_sse_serializer_scope_check.md`）
- [ ] Day 0 探勘 必 grep §Technical Spec assertions vs repo state（per AD-Plan-1 53.7 lesson）
- [ ] PR commit message 含 scope + sprint ID + Co-Authored-By
- [ ] Anti-pattern checklist 11 條 PR 前自檢（特別 AP-3 範疇歸屬；AP-4 Potemkin；AP-6 Hybrid Bridge — 確認 worktree 模式不偷加）
- [ ] CARRY items 清單可追溯到 54.1 retrospective Q4（AD-Cat10-Obs-1）
- [ ] V2 lint 6 scripts CI green（透過 run_all.py）
- [ ] Frontend lint + type check + build green（不應受 backend-only 改動影響）
- [ ] LLM SDK leak: 0（grep openai/anthropic in `subagent/`）
- [ ] Cat 11 coverage ≥ 80%

---

## Retrospective 必答（per W3-2 + 53.x + 54.1 教訓 + AD-Sprint-Plan-1 calibration verify）

Day 4 retrospective.md 必答 6 題：

1. **Sprint Goal achieved?**（Yes/No + Cat 11 達 Level 4 evidence + AD-Cat10-Obs-1 closed grep / test 證據）
2. **Estimated vs actual hours**（per US；總計；**+ calibration multiplier 0.55 第 3 次驗證**：actual / committed ratio；本 sprint 是 53.7 (1.01) + 54.1 (0.69) 後第 3 次應用 0.55；3-sprint window mean 算術 → 若 < 0.85 lower to 0.45；若仍 [0.85, 1.20] 內保持 0.55 stable phase）
3. **What went well**（≥ 3 items；含 banked buffer 來源）
4. **What can improve**（≥ 3 items + 對應的 follow-up action）
5. **V2 9-discipline self-check**（逐項 ✅/⚠️ 評估；特別 AP-3 範疇歸屬 + AP-6 worktree 模式不偷加）
6. **Audit Debt logged**（54.2 新發現的 issue + Phase 55 candidate scope 候選清單；本 sprint 結束後 V2 進度 20/22 — 接近完成；剩 Phase 55 業務 domain + canary）

---

## Sprint Closeout

- [ ] All 5 USs delivered with 主流量 verification（Cat 11 Level 4 + AD-Cat10-Obs-1 closed）
- [ ] PR open + 5 active CI checks → green
- [ ] Normal merge to main (solo-dev policy: review_count=0; no temp-relax needed)
- [ ] retrospective.md filled (6 questions; **含 calibration multiplier 第 3 次 accuracy verification + 3-sprint window mean**)
- [ ] Memory update (project_phase54_2_cat11_subagent.md + index)
- [ ] Branch deleted (local + remote)
- [ ] V2 progress: **19/22 → 20/22 (91%)**（主進度推進 — 不是 carryover bundle）
- [ ] Cat 11 reaches Level 4 (主流量強制)
- [ ] AD-Cat10-Obs-1 closed in retrospective Q6 with grep / test evidence
- [ ] SITUATION-V2-SESSION-START.md §8 (Open Items) + §9 (milestones) updated
- [ ] AP-6 (Hybrid Bridge Debt) 從 04-anti-patterns.md 角度標 verified clean (worktree 模式 ❌ not implemented per V2 spec)
