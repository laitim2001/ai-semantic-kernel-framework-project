# Sprint 57.102 Progress — TEAMMATE real multi-turn child loop + child MessageInbox (wired) + send_to_parent tool (B2a)

**Plan**: [`../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-102-plan.md`](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-102-plan.md)
**Checklist**: [`../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-102-checklist.md`](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-102-checklist.md)
**Branch**: `feature/sprint-57-102-teammate-multiturn` (from `main` `abee7bd3`)

---

## Day 0 — Plan-vs-Repo Verify (three-prong, against HEAD `abee7bd3`)

Day-0 recon (Explore agent + personal re-read of fork/teammate/dispatcher/tools/mailbox/_contracts + handler factory block + make_default_executor + ToolRegistry/ToolExecutor + the FORK test stubs). All proposal anchors re-verified against `abee7bd3`. **go/no-go = GO** (slice = plan §4 file list; backend-mostly).

### Prong 1 (path) — CONFIRMED
- `subagent/modes/fork.py:89-194` (ForkExecutor pattern to mirror; `_TAO_CHILD_EVENT_TYPES :80-86` = TurnStarted/LLMResponded/ToolCall{Requested,Executed,Failed}) · `subagent/modes/teammate.py:56-156` (current single-shot — `__init__(chat_client, mailbox, enforcer)`; `execute` 1×`chat()` + best-effort `mailbox.send(recipient="parent")`) · `dispatcher.py:105-144` ctor (`_fork`/`_teammate`/`_handoff`/`_as_tool_wrapper`) + `:208-227` routing + `:265-294` wait_for · `tools.py:51-125` task_spawn (`wait_for :116` BLOCKS) + `:128-185` handoff · `mailbox.py:46-99` (send/receive; NO drain) · `_contracts/subagent.py:95-101` (`ChildLoopFactory = Callable[[SubagentBudget], "AgentLoop"]`) · `_contracts/inbox.py` (`MessageInbox.drain`) · `loop.py:2026-2056` (B1 drain seam — reused unchanged) · `injection_registry.py` (`InjectionRegistry`/`QueueMessageInbox`) · `handler.py:322-368` (`_make_child_loop` + `make_default_executor` + `make_chat_subagent_dispatcher`) · `_category_factories.py:199-235` (`make_chat_subagent_dispatcher(chat_client, *, child_loop_factory=None, event_emitter=None)`).

### Prong 2 (content) — CONFIRMED + refinements
- **Await-completion BLOCKS** (D-DAY0-3): `dispatcher.spawn` → `asyncio.create_task(_track_and_emit())` (`:262`); `wait_for` → `await task` (`:284`); `task_spawn` handler → `await dispatcher.wait_for(subagent_id)` (`tools.py:116`). So the parent turn is suspended until the teammate finishes → "parent reasons mid-child-run + injects" needs non-blocking spawn (proposal §2.5 deferred). → **B2a/B2b split** (this sprint = B2a; the live inject-to-teammate producer = B2b).
- **Mailbox per-request → external writer needs InjectionRegistry, not mailbox** (D-DAY0-2): `MailboxStore` is per-request (`mailbox.py` AD-Test-1) → the separate inject HTTP request can't reach it → the child inbox's external-writer backing is the module-level B1 `InjectionRegistry` keyed by `subagent_id` (B2b). The mailbox stays the child→parent channel (`send_to_parent`). Corrects the proposal's "child inbox = mailbox channel" label.
- **`make_default_executor` registration mechanism** (D-DAY0-4 — wiring refinement, cleaner than plan §3.5): `ToolRegistry.register(spec)` takes ONLY a spec; handlers live in the executor's `_handlers` dict captured at construction (`ToolExecutorImpl(registry, handlers, tracer)`). The subagent `task_spawn` tool is registered via the opt-in `subagent_dispatcher` branch (`_register_all.py:262-279`): `registry.register(spec)` + `handlers[name] = _adapt_subagent_handler(handler)`. → register `send_to_parent` the SAME way: **add a `teammate_mailbox: MailboxStore | None = None` opt-in param to `make_default_executor`** (mirrors the `subagent_dispatcher` branch; reuse `_adapt_subagent_handler`); the teammate child executor = `make_default_executor(subagent_dispatcher=None, teammate_mailbox=mailbox, parent_session_id=session_id)`. This adds `business_domain/_register_all.py` to the file change list (the plan §3.5 anticipated "Day-1 verify the exact make_default_executor signature" — this is that finding).
- **The shared `MailboxStore` seam** (D-DAY0-4 cont.): the dispatcher creates `_mailbox` internally today (`mailbox or MailboxStore()`). For `send_to_parent` (in the teammate child) and the teammate executor's `mailbox.drain` to share ONE per-request instance, the handler creates ONE `MailboxStore` and passes it to BOTH `make_chat_subagent_dispatcher(mailbox=…)` (add the param) AND `make_default_executor(teammate_mailbox=…)`.
- **Test stubs** (D-DAY0-5): `_child_loop_helpers.make_child_loop_factory(chat, ...)` returns a 1-arg `ChildLoopFactory`. The teammate factory is 2-arg `(budget, inbox)` → add `make_teammate_child_loop_factory(chat, ...)` to `_child_loop_helpers.py` (passes `message_inbox=inbox` to `AgentLoopImpl`). `test_fork.py` is the conversion template for `test_teammate.py` (4 single-shot tests → child-loop equivalents).

### Prong 3 (schema/wire) — N/A CONFIRMED
- NO DB/migration/ORM (mailbox + child loop ephemeral). NO new wire event TYPE — the teammate reuses `SubagentChildEvent` (57.96 relay forwards `ToolCall*` → `send_to_parent` is visible in the Inspector Tree for free) + `SubagentSpawned/Completed`. `len(WIRE_SCHEMA)` UNCHANGED; `check_event_schema_sync` stays green with NO regen. NO FE expected (Day-2 confirm via drive-through).

### Drift catalogue (Day-0)
- **D-DAY0-1** (path, resolved): proposal `teammate.py`/`fork.py`/`as_tool.py`/`handoff.py` live under `subagent/modes/`, not root (initial non-recursive Glob missed `modes/`). File names correct. No scope impact.
- **D-DAY0-2** (content, proposal correction): "child inbox = mailbox channel" wrong for an external writer (mailbox per-request) → backing = `InjectionRegistry` keyed by `subagent_id` (B1 reuse). B2b.
- **D-DAY0-3** (content, the load-bearing one): await-completion confirmed (`dispatcher.py:262`/`:284` + `tools.py:116`) → split B2a (this) / B2b (inject-to-teammate). Detached/live parent→child stays deferred (proposal §2.5).
- **D-DAY0-4** (wiring refinement): `send_to_parent` registered via a NEW `make_default_executor(teammate_mailbox=…)` opt-in param (mirror `subagent_dispatcher`; reuse `_adapt_subagent_handler`) + ONE shared per-request `MailboxStore` threaded to both the dispatcher and the tool. Adds `business_domain/_register_all.py` + `make_chat_subagent_dispatcher(mailbox=…)` to the change set. Cleaner than the plan §3.5 "register in the handler" sketch.
- **D-DAY0-5** (test helper): add `make_teammate_child_loop_factory` (2-arg, with inbox) to `_child_loop_helpers.py`; convert `test_teammate.py` per the `test_fork.py` template (drop the auto-final-mailbox-send assertion → the final answer is `SubagentResult.summary` like FORK; the mailbox now carries explicit `send_to_parent` reports folded into the summary).

### Decisions
- Design-note: NO (composition continuation of design note 20 + B1) → CHANGE-069 + 17.md + light edit design note 20.
- Behavior change: drop the teammate's auto-final-`mailbox.send` (the D15 reader-less demo) → final answer via `SubagentResult.summary` (FORK parity); the mailbox carries only explicit `send_to_parent` reports (drained + folded into summary by the executor). Documented in CHANGE-069.

### Baseline capture (`main abee7bd3`, pre-code)
- mypy `src` **0/355** ✅ · pytest collect `-m "not real_llm"` **2324** ✅ (run_all + Vitest not re-run — no FE change expected; captured if a render tweak lands).

### Day-0 GO + branch
- Branch `feature/sprint-57-102-teammate-multiturn` from `main abee7bd3`; Day-0 commit `facffce4` (plan + checklist + progress).

---

## Day 1-2 — Implementation (committed `6706bdd0`)

All Day-0 wiring findings (D-DAY0-4 `make_default_executor(teammate_mailbox=)` + the shared `MailboxStore` seam + D-DAY0-5 test helper) applied exactly as catalogued. Backend-only, 15 files:

- **`_contracts/subagent.py`** — `TeammateChildLoopFactory = Callable[[SubagentBudget, "MessageInbox|None"], "AgentLoop"]` (separate alias; FORK's `ChildLoopFactory` byte-identical); exported.
- **`subagent/mailbox.py`** — `drain(session_id, recipient)` non-blocking (`.get` not `_queue_for` → no side-effect queue creation).
- **`subagent/tools.py`** — `make_send_to_parent_tool(mailbox, parent_session_id, role)` → `send_to_parent {message}` → `{delivered}`.
- **`subagent/modes/teammate.py`** — REWRITE: single-shot → real child loop (mirror `fork.py` `_drive` + `asyncio.wait_for` + fail-closed envelope + `_TAO_CHILD_EVENT_TYPES` relay); drains the parent mailbox + folds `send_to_parent` reports into the summary.
- **`subagent/dispatcher.py`** — ctor `+teammate_child_loop_factory + inbox_factory`; `_teammate` built with them + `event_emitter=self._emit_safely`; `chat_client` kept (vestigial, noted).
- **`business_domain/_register_all.py`** — `make_default_executor(+teammate_mailbox)` opt-in registers `send_to_parent` via `_adapt_subagent_handler` (mirror the subagent_dispatcher branch).
- **`_category_factories.py`** — `make_chat_subagent_dispatcher(+teammate_child_loop_factory + inbox_factory + mailbox)`.
- **`handler.py`** — `_make_teammate_child_loop(budget, inbox)` (recursion-safe subset + `send_to_parent` + `message_inbox`) + `inbox_factory` (`QueueMessageInbox` over `InjectionRegistry` keyed by `subagent_id`, None without tenant) + ONE shared `MailboxStore` threaded to both. **loop.py UNCHANGED.**

**Tests** (convert + new, the 57.94 precedent): `test_teammate.py` 4 single-shot → 7 child-loop (incl. fail-closed + report-fold + dispatcher-no-factory); `test_send_to_parent_tool.py` (3 new); `test_mailbox.py` (+4 drain); `test_teammate_inbox.py` (3 new — incl. **`test_teammate_child_loop_drains_queued_inbox_message`** proving the child loop consumes a pre-seeded `InjectionRegistry` queue via the B1 seam) + `_child_loop_helpers.make_teammate_child_loop_factory`.

### Day-1/2 drift
- **D-DAY0-4 confirmed cleaner than plan §3.5**: `ToolRegistry.register(spec)` takes only a spec; handlers live in the executor's `_handlers` dict captured at construction → register `send_to_parent` via a `make_default_executor(teammate_mailbox=)` opt-in (mirrors `subagent_dispatcher`), NOT post-construction registry mutation. Added `_register_all.py` to the change set (the plan §3.5 anticipated this as a Day-1 verify).
- No other drift. `chat_client` vestigial on the dispatcher: KEPT + noted (pruning cascades to all callers; not worth the churn).

### Gate (Day-2 close)
- mypy `src` **0/355** ✅ · flake8 `src tests` clean ✅ (6 MHist/docstring E501s shortened) · black reformatted `handler.py` (1 file) · isort clean.
- `run_all` **10/10** ✅ (`check_ap1` green = the teammate `_drive` is data-flow not a pipeline; `check_llm_sdk_leak` 0; `check_cross_category_import` green = agent_harness imports no api layer; `check_event_schema_sync` green = event count UNCHANGED — reuses `SubagentChildEvent`).
- subagent suite **73 passed** (was 60: 56 + 4 broken teammate → converted; +13 new).

---

## Day 3 — Full regression + drive-through

### 3.1-3.2 Full gate sweep
- Infra check first (57.101 lesson): `docker compose ps` → postgres healthy + `:5432` LISTENING; redis/rabbitmq/mock_services healthy. Single full-suite run (no concurrency).
- **Full backend pytest `-m "not real_llm"`: 2333 passed + 4 skipped** (baseline 2324 collected → **+13, 0 deletions**: teammate +3 / send_to_parent +3 / mailbox.drain +4 / teammate_inbox +3); 101s clean.
- mypy `src` 0/355 · run_all 10/10 · black/isort/flake8 FULL `src tests` clean.
- **Frontend: NO change** (confirmed `git diff` = 0 frontend files). The 57.96 `SubagentChildEvent` relay already renders the teammate's turns + the `send_to_parent` tool call — verified live in the drive-through (below). No Vitest/build needed.

### 3.3 Drive-through (US-5) — ✅ PASS (real UI jamie@acme.com/acme-prod + real Azure gpt-5.2)
- **Clean restart (Risk Class E)**: killed the stale 57.101 backend PID 2520 + its `multiprocessing.spawn` worker 10140 (started 11:09 AM, pre-B2a); verified `:8000` FREE; started a fresh B2a backend PID 29576 (`dev.py start backend`, sole `:8000` owner). Frontend node :3007 (PID 22000) untouched. Also cleared a stale mcp-chrome profile lock (7 orphan chrome procs) before Playwright could attach — unrelated to B2a.
- **Prompt**: "Use the task_spawn tool with mode='teammate' … have the teammate check the server health for the checkout service, and instruct it … to send you its key finding via the send_to_parent tool before finishing. Then give me a short summary that includes the teammate's report." (Nailed first try — no iteration needed.)
- **Observed vs intended (ALL match)**:
  - Parent turn 0 → `task_spawn {"mode":"teammate", "task":"Check server health … send your key finding … via the send_to_parent tool …"}` → `subagent_spawned mode=teammate`.
  - **The teammate ran a REAL 3-turn child loop** (NOT single-shot — the B2a core): turn 0 `mock_patrol_check_servers(scope=[checkout-web-01…])` → server health; turn 1 `send_to_parent({"message":"Checkout service health: 3/6 servers in WARNING…"})` → `{"delivered": true}`; turn 2 final answer.
  - All the child's per-turn TAO events relayed via `subagent_child` (57.96) — visible in the **Inspector Tree** (turn 0 → `mock_patrol_check_servers()` → turn 1 → `send_to_parent()` → turn 2) + the Loop visualizer.
  - The `task_spawn` result summary = `"[teammate reports]\n[from teammate] Checkout service health: 3/6 servers in WARNING…\n[final answer]\n…"` — the **report folded into the summary** (the B2a fold works).
  - The parent's final answer (turn 3) **integrated the teammate report**: "**Teammate report (key finding):** 3/6 checkout servers are in WARNING due to elevated CPU—especially the web tier. checkout-web-01 CPU 88.6%…" + in-loop `verification_passed score=0.99` (A1, 57.98).
  - Tree summary: "Subagents (1) · Done · teammate · 7376 tok"; Mode teammate / Depth 1 / Concurrency 0.
- Screenshot: `artifacts/dt57102-teammate-tree.png`. **NOT "gate-only" — driven live.**
- **Honest cosmetic note (NOT a B2a regression)**: the **inline** conversation `SubagentForkBlock` mislabels the spawn as "Fork · concurrent" + shows "0t" tokens — both PRE-EXISTING 57.95/96 FE carryovers (the inline block hardcodes "Fork" + a separate 0t turn-count display) surfaced again here; the authoritative **Tree** correctly shows "teammate" + 7376 tok. B2a is backend-only (no FE change) → carry to B2b (the FE slice): make the inline block mode-aware + fix the 0t display.

---
