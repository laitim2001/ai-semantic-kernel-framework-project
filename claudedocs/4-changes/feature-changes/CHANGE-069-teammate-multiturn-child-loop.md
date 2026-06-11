# CHANGE-069: TEAMMATE real multi-turn child loop + send_to_parent + B1 inbox wiring (B2a)

**Date**: 2026-06-11
**Sprint**: 57.102
**Scope**: Cat 11 (Subagent Orchestration) × Cat 1 (the teammate child loop carries the B1 `MessageInbox`) × Cat 12 (reuses the 57.96 `SubagentChildEvent` relay — no new wire event)
**Status**: ✅ Completed
**Source**: harness-deepening proposal §2.3 (B2) → Option A → B2a/B2b split (the chat-user inject-to-teammate UI producer is B2b)

## Problem / Motivation

TEAMMATE (Cat 11 mode 2) was a Sprint 54.2 "D15 simplification": a single-shot `ChatClient.chat()` call plus a best-effort `mailbox.send()` to the parent that **nobody read** (an AP-4-adjacent reader-less demo). It could not investigate or iterate like a real peer. The harness-deepening proposal's "one primitive, two payoffs" insight: the same B1 `MessageInbox` primitive (Sprint 57.101) that powers chat live-injection should back a long-lived collaborating child. Day-0 confirmed the proposal's own deferred constraint — the dispatcher awaits the child to completion (`dispatcher.py:262` + `tools.py:116` block the parent turn) — so "the parent reasons mid-child-run and injects" needs a non-blocking/detached teammate (deferred). The honest, blocking-contract-preserving v1 (**B2a**) makes TEAMMATE a real multi-turn child + wires the inbox; the live UI producer for that inbox (**B2b**) adds an inject-to-teammate endpoint + FE.

## Solution

Mirror the proven 57.94 FORK `ChildLoopFactory` child-loop pattern; reuse the 57.96 relay + the B1 inbox. Backend-only (15 files), `loop.py` UNCHANGED, no new wire event, no DB, no frontend:

- **`TeammateExecutor` rewrite** (`subagent/modes/teammate.py`): single-shot → real child `AgentLoop` via a new `TeammateChildLoopFactory`; same fail-closed envelope as FORK (`teammate_child_loop_factory is None` → `SubagentResult(success=False, error="teammate_child_loop_factory_unavailable")`; timeout / empty / child_loop_error; never raises). Forwards the child's per-turn TAO subset (`_TAO_CHILD_EVENT_TYPES`) via `SubagentChildEvent`. After the child completes, drains the parent mailbox for `send_to_parent` reports and **folds them into the `SubagentResult.summary`** so the parent integrates them via the existing `task_spawn` channel (await-completion: the reports surface when the teammate finishes).
- **`make_send_to_parent_tool`** (`subagent/tools.py`): the teammate child's `send_to_parent {message}` tool → `mailbox.send(recipient="parent")` → `{delivered}`. Registered ONLY on the teammate child executor.
- **`MailboxStore.drain`** (`subagent/mailbox.py`): non-blocking batch read (`.get` not `_queue_for` → no side-effect queue creation) for the report fold.
- **`TeammateChildLoopFactory`** (`_contracts/subagent.py`): `Callable[[SubagentBudget, "MessageInbox|None"], "AgentLoop"]` — a SEPARATE alias (the teammate child also takes an inbox) so FORK's `ChildLoopFactory` + every FORK call site stay byte-identical.
- **Dispatcher + factory wiring** (`subagent/dispatcher.py` + `_category_factories.py` + `handler.py`): the dispatcher builds `_teammate` with `teammate_child_loop_factory` + `inbox_factory` (+ `event_emitter=self._emit_safely`). The handler builds `_make_teammate_child_loop(budget, inbox)` (recursion-safe subset via `make_default_executor(subagent_dispatcher=None)` + `send_to_parent` via the NEW `teammate_mailbox` opt-in + `message_inbox=inbox`) and `inbox_factory(sid) = QueueMessageInbox(InjectionRegistry, tenant, sid)`. ONE shared per-request `MailboxStore` is threaded to both the dispatcher (the executor's drain) and the `send_to_parent` tool. **agent_harness stays LLM/layer-neutral** — only the `MessageInbox` ABC + an `inbox_factory` callable cross the layer (the api-layer `InjectionRegistry` is never imported by `subagent/`).
- **The B1 inbox is wired + unit-proven**; in production it is inert until B2b registers the queue + adds the inject endpoint (drain of an unregistered key = `[]` = no-op). NOT claimed drive-through in B2a.

## Verification

- **Gate**: mypy `src` 0/355 · flake8 `src tests` clean · `run_all` 10/10 (`check_ap1` + `check_llm_sdk_leak` + `check_cross_category_import` + `check_event_schema_sync` green; event count UNCHANGED) · full pytest **2333 passed + 4 skipped** (+13, 0 deletions).
- **Unit**: `test_teammate.py` (7, converted from 4 single-shot — multi-turn drive / fail-closed / report-fold / dispatcher-no-factory) · `test_send_to_parent_tool.py` (3) · `test_mailbox.py` (+4 drain) · `test_teammate_inbox.py` (3 — incl. the child loop draining a pre-seeded `InjectionRegistry` queue via the B1 seam).
- **Drive-through (real UI jamie@acme.com/acme-prod + real Azure gpt-5.2, clean restart PID 29576)**: parent `task_spawn {"mode":"teammate"}` → the teammate ran a **real 3-turn child loop** (turn 0 `mock_patrol_check_servers` → turn 1 `send_to_parent {"delivered":true}` → turn 2 final answer, all relayed to the Inspector Tree via 57.96) → the report folded into the summary → the parent's final answer integrated "**Teammate report (key finding):** 3/6 checkout servers in WARNING…" + `verification_passed 0.99`. Screenshot `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-102/artifacts/dt57102-teammate-tree.png`.

## Impact

- Cat 11 mode 2 (TEAMMATE) graduates from single-shot to a real multi-turn collaborating child — the proposal's third subagent simplification closed.
- `loop.py` / `modes/fork.py` / `modes/as_tool.py` / `router.py` / `injection_registry.py` / `events.py` / DB / frontend diff = 0.
- **Carryover → B2b**: the chat-user inject-to-teammate endpoint (`POST /chat/{id}/subagents/{subagent_id}/inject`) + the `InjectionRegistry` spawn-time registration + the FE inject-to-teammate control + render + that inbox's drive-through. Also the inline `SubagentForkBlock` mislabel ("Fork"/0t for a teammate spawn — a pre-existing 57.95/96 FE carryover surfaced by this drive-through; the Tree is correct) should be made mode-aware in B2b.
- Commits: `facffce4` (Day-0) · `6706bdd0` (impl + tests) · closeout.
