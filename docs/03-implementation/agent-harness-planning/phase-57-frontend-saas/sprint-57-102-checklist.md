# Sprint 57.102 — Checklist (TEAMMATE real multi-turn child loop + child MessageInbox wired + send_to_parent tool — B2a: TEAMMATE stops being single-shot, becomes a real collaborating child that reuses the B1 inbox; the chat-user inject-to-teammate UI producer is B2b)

**Plan**: [`sprint-57-102-plan.md`](./sprint-57-102-plan.md)
**Created**: 2026-06-11
**Status**: ✅ Completed 2026-06-11 — all gates green + drive-through PASS (real UI + real Azure gpt-5.2). PR pending push authorization.

> Rule: only `[ ]` → `[x]`; never delete unchecked items; defer with `🚧 + reason`.
> **Composition spike** (REUSES the 57.94 FORK child-loop pattern + the 57.96 SubagentChildEvent relay + the B1 MessageInbox) → **NO design note** (continuation of design note 20). Record = CHANGE-069 + **update 17.md** (`send_to_parent` tool + `TeammateChildLoopFactory` + TEAMMATE-now-multi-turn) + light edit design note 20 §Open Invariants. Gate = full backend pytest green (NET delta) + **drive-through PASS** (real UI → parent spawns teammate → teammate runs multi-turn + send_to_parent mid-loop → parent integrates). Load-bearing: TEAMMATE mirrors FORK's fail-closed envelope; the child-inbox seam is layer-neutral (agent_harness sees only the `MessageInbox` ABC + an `inbox_factory` callable); send_to_parent has a REAL reader (mailbox.drain → fold into summary) — not a Potemkin. Out: B2b inject-to-teammate endpoint + FE + that inbox's drive-through; detached teammate; depth>1; per-tenant policy (C3). **NO new wire event / codegen / DB / FE expected.**

---

## Day 0 — Plan-vs-Repo Verify + Branch

### 0.1 Three-prong Day-0 verify (re-confirm against HEAD `abee7bd3` before Day-1 code)
- [x] **Prong 1 (path)**: re-confirm all anchors — `modes/fork.py:89-194` (ForkExecutor pattern + `_TAO_CHILD_EVENT_TYPES :80-86`) · `modes/teammate.py:56-156` (current single-shot) · `dispatcher.py:105-144` ctor + `:208-227` routing + `:265-294` wait_for · `tools.py:51-125` task_spawn (`wait_for :116`) · `mailbox.py:46-99` (send/receive, no drain) · `_contracts/subagent.py:95-101` (`ChildLoopFactory`) · `_contracts/inbox.py` (`MessageInbox`) · `loop.py:2026-2056` (B1 drain seam — to be reused unchanged) · `injection_registry.py` (`InjectionRegistry`/`QueueMessageInbox`) · `handler.py:322-356` (`_make_child_loop`) · `_category_factories.py:199-235` (`make_chat_subagent_dispatcher`). (progress.md Day-0 Prong 1)
- [x] **Prong 2 (content)**: confirm — FORK's `_drive` await-completion (`asyncio.wait_for(_drive(), timeout)`); the dispatcher BLOCKS (`:262` create_task + `:284` await) + task_spawn BLOCKS (`tools.py:116`) → D-DAY0-3 await-completion (B2b split); the mailbox is per-request → external writer needs `InjectionRegistry` not mailbox (D-DAY0-2); `make_default_executor` builds the recursion-safe subset WITHOUT a subagent_dispatcher (so the teammate child can't spawn); where the dispatcher's `MailboxStore` instance is reachable for the `send_to_parent` tool (the seam §3.5/§8 — handler creates ONE mailbox, passes to both). (progress.md Day-0 Prong 2)
- [x] **Prong 3 (schema)**: N/A confirmed — NO DB/migration/ORM (mailbox + child loop ephemeral). NO new wire event TYPE — the teammate reuses `SubagentChildEvent` (57.96) + `SubagentSpawned/Completed`; `len(WIRE_SCHEMA)` UNCHANGED; `check_event_schema_sync` stays green with no regen. (progress.md Day-0 Prong 3)
- [x] **Baseline capture**: `main abee7bd3` — mypy `src` 0/N · pytest collect `-m "not real_llm"` count · run_all 10/10 · (no FE baseline needed unless a render tweak lands).
- [x] **Design-note decision**: composition continuation → NO new design note; plan to UPDATE 17.md (`send_to_parent` + `TeammateChildLoopFactory` + TEAMMATE multi-turn) + light edit design note 20. Confirmed in progress.md.
- [x] **Drive-through setup**: a prompt that reliably makes the parent spawn a TEAMMATE + elicits `send_to_parent` (the 57.101 forceful-prompt lesson); cheap deployment (57.97) set; clean-restart plan (Risk Class E) — noted in progress.md, executed Day 3.
- [x] Catalogue Day-0 drift in progress.md (D-DAY0-1 modes/ path / D-DAY0-2 mailbox-can't-bridge → InjectionRegistry backing / D-DAY0-3 await-completion → B2a/B2b split); **go/no-go = GO** (slice = §4 file list).

### 0.2 Branch
- [x] Branch `feature/sprint-57-102-teammate-multiturn` from `main` (`abee7bd3`)
- [x] plan + checklist + progress committed (Day-0 commit)

---

## Day 1 — `TeammateExecutor` rewrite + `send_to_parent` + `MailboxStore.drain` + `TeammateChildLoopFactory` (US-1/US-2/US-3)

### 1.1 The contract + tool + mailbox primitives
- [x] **`_contracts/subagent.py`** — +`TeammateChildLoopFactory = Callable[[SubagentBudget, "MessageInbox | None"], "AgentLoop"]` (`MessageInbox` under TYPE_CHECKING; FORK's `ChildLoopFactory` byte-identical); export via `_contracts/__init__.py`; MHist; `check_llm_sdk_leak` 0
- [x] **`subagent/mailbox.py`** — +`async def drain(session_id, recipient) -> list[Message]` (non-blocking get_nowait loop; `[]` if no queue); `receive()` kept; MHist
- [x] **`subagent/tools.py`** — +`make_send_to_parent_tool(*, mailbox, parent_session_id, role="teammate")` → `ToolSpec(name="send_to_parent", {message:str})` + handler → `mailbox.send(parent_session_id, sender=role, recipient="parent", content=msg)` → `{delivered:True}` / empty → `{delivered:False, error}`; export via `subagent/__init__.py`; MHist

### 1.2 The `TeammateExecutor` rewrite (mirror FORK)
- [x] **`subagent/modes/teammate.py`** — REWRITE: ctor `(*, teammate_child_loop_factory, mailbox, enforcer, event_emitter, inbox_factory)`; `execute(...)` fail-closed if no factory; `inbox = inbox_factory(subagent_id) if inbox_factory else None`; `_drive` mirrors FORK (`child = factory(budget, inbox)`; `async for ev in child.run(session_id=uuid4(), user_input=task)`: forward `_TAO_CHILD_EVENT_TYPES` via emitter; track `LLMResponded.content` + `LoopCompleted.total_tokens`); `asyncio.wait_for(_drive(), timeout=budget.max_duration_s)`; on success `reports = await mailbox.drain(parent_session_id, "parent")` + fold into summary + `truncate_summary` + `SubagentResult`; same fail-closed envelope (timeout/empty/child_loop_error; never raises); import `_TAO_CHILD_EVENT_TYPES` from `modes/fork.py` (avoid dup, AP-3); MHist; mypy `src` 0

---

## Day 2 — Dispatcher + handler wiring + inbox-factory + tests (US-4)

### 2.1 Dispatcher + factory wiring
- [x] **`subagent/dispatcher.py`** — `__init__` +`teammate_child_loop_factory` + `inbox_factory`; build `_teammate = TeammateExecutor(teammate_child_loop_factory=…, mailbox=self._mailbox, enforcer, event_emitter=self._emit_safely, inbox_factory=…)`; `chat_client` Day-1 decision (keep+note vestigial / prune if ≤2 files); MHist
- [x] **`_category_factories.py`** — `make_chat_subagent_dispatcher(chat_client, *, child_loop_factory=None, event_emitter=None, teammate_child_loop_factory=None, inbox_factory=None, mailbox=None)` → pass through to `DefaultSubagentDispatcher`; MHist
- [x] **`handler.py`** — `_make_teammate_child_loop(budget, inbox)` (recursion-safe subset via `make_default_executor` WITHOUT subagent_dispatcher + register `make_send_to_parent_tool(mailbox, parent_session_id=session_id, role="teammate")` + `AgentLoopImpl(..., message_inbox=inbox)`); `inbox_factory = lambda sid: QueueMessageInbox(get_default_injection_registry(), tenant_id, sid)` (None if no tenant); ONE shared `MailboxStore` passed to both `make_chat_subagent_dispatcher(mailbox=…)` + the send_to_parent tool; thread `teammate_child_loop_factory` + `inbox_factory`; MHist; mypy `src` 0

### 2.2 Tests (US-1..US-4)
- [x] **teammate executor (convert)** — the single-shot tests → real child-loop equivalents (Never-Delete → convert, 57.94 precedent): multi-turn drive + summary from last `LLMResponded` + TAO forwarded + fail-closed without a factory + report-fold into summary
- [x] **`test_send_to_parent_tool.py`** (NEW) — delivers to mailbox (`recipient="parent"`); empty message → `delivered:False`
- [x] **`test_mailbox.py`** (NEW/EDIT) — `drain` non-blocking + FIFO + `[]` empty; coexists with `receive`
- [x] **teammate-inbox-drain** (NEW) — a teammate child loop built with `QueueMessageInbox` over a REGISTERED test queue + a queued message → the child drains it at its next turn boundary (B1 seam) + the guardrail sees it; no inbox → no-op
- [x] **dispatcher** (EDIT) — TEAMMATE routes to the child loop; fail-closed without a teammate factory
- [x] **neutrality** — `check_llm_sdk_leak` 0; no `from api…` import in `subagent/` (layer boundary); `check_ap1`/`check_ap3` green

---

## Day 3 — Full regression + drive-through (US-5) + CHANGE-069 + 17.md

### 3.1 Full gate sweep
- [x] **Full backend pytest green (NET delta documented)** — `-m "not real_llm"`: baseline → +N (send_to_parent + mailbox.drain + teammate-inbox + converted teammate; 0 deletions). Infra check first (`docker compose ps` + `:5432`); never 2 full suites concurrently.
- [x] **mypy 0 + run_all 10/10 + format chain** — mypy `src` 0/N; run_all 10/10 (`check_event_schema_sync` count UNCHANGED + `check_ap1` + `check_ap3` + `check_llm_sdk_leak` green); black/isort/flake8 FULL `src tests` clean (independent)
- [x] **Frontend** — only if a render tweak landed: `npm run lint` (no `--silent`) + `build` + `check:mockup-fidelity` (baseline unchanged) + Vitest. Else: confirm NO FE change (the 57.96 relay renders the teammate turns + send_to_parent tool call) via the Day-3 drive-through.

### 3.2 Drive-through (US-5 — multi-turn teammate + send_to_parent picked up)
- [x] **Clean backend (Risk Class E)** — kill stale uvicorn reloader + `multiprocessing.spawn` worker (`Get-CimInstance Win32_Process` PID/PPID/StartTime + `Stop-Process -Force`); verify the FRESH PID is the SOLE :8000 owner; do NOT touch node :3007 (frontend) / claude-code node. Fresh process so the teammate factory + dispatcher wiring are startup-constructed.
- [x] **Drive-through PASS** — real UI + real backend + real Azure: a prompt that makes the parent spawn a TEAMMATE → the teammate runs ≥2 turns (Inspector Tree shows the child's per-turn loop + ≥1 tool call via the 57.96 relay) → the teammate calls `send_to_parent` mid-loop → the parent's final answer integrates the report. `artifacts/dt57102-*.png` + progress.md Day-3 (observed-vs-intended). The teammate child inbox is "wired + unit-proven" — explicitly NOT claimed drive-through (UI producer = B2b).

### 3.3 CHANGE-069 + 17.md + design note 20
- [x] `claudedocs/4-changes/feature-changes/CHANGE-069-teammate-multiturn-child-loop.md` written
- [x] **`17-cross-category-interfaces.md`** — register `send_to_parent` Cat 11 tool (§3.1) + `TeammateChildLoopFactory` (§2.1, sibling of `ChildLoopFactory`) + update TEAMMATE mode description (single-shot → real child loop with mailbox + inbox)
- [x] **design note 20** (`20-subagent-child-loop-design.md`) — §Open Invariants light edit: TEAMMATE now multi-turn (1-2 lines)

---

## Day 4 — Closeout (composition spike — no design note)

### 4.1 Closeout
- [x] Full validation (parent re-verified): backend pytest +N (0 deletion) / mypy `src` 0/N / run_all 10/10 (count unchanged) / black FULL `src tests` clean / `loop.py`+`modes/fork.py`+`modes/as_tool.py`+`router.py`+`injection_registry.py`+`events.py`+DB diff = 0 / **drive-through PASS** (teammate multi-turn + send_to_parent → parent integrates; artifacts dt57102-*.png)
- [x] progress.md (Day 0-3 + drive-through) + retrospective.md (Q1-Q7)
- [x] Calibration: `subagent-teammate-multiturn-spike` 0.55 (NEW class, 1st pt) + `agent_factor` 1.0 (parent-direct); recorded `sprint-workflow.md §Scope-class matrix` row; carryover (B2b inject-to-teammate) → next-phase-candidates.md
- [x] MEMORY.md pointer + `project_phase57_102_teammate_multiturn.md` subfile + CLAUDE.md lean (Current Sprint row + Last Updated) + CHANGE-069 + 17.md + design note 20 edit
- [x] commit (Day 0-N) + push + PR — user-authorized
