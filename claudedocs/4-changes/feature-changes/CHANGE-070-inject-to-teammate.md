# CHANGE-070: chat-user inject-to-teammate (B2b) — backend primitive + mode-aware inline block; live UI deferred to §2.5

**Date**: 2026-06-11
**Sprint**: 57.103 (B2b — harness-deepening Workflow B slice B2, second half)
**Scope**: 範疇 11 (Subagent Orchestration) × 範疇 1 (loop drain seam, reused) × 範疇 12 (event relay) × Frontend

## Problem

Sprint 57.102 (B2a) wired a `MessageInbox` on the TEAMMATE child loop but with **no live producer** — the inbox drained a never-registered queue, inert "until B2b". B2b is that producer: a chat user injects a message into a running teammate, the teammate drains it at its next turn boundary, and the injected turn surfaces on the Inspector Tree. It also closes the 57.102 🟢 carryover: the inline `SubagentForkBlock` mislabelled a teammate spawn as "Fork · concurrent" + showed an always-0 "0t".

## Root cause / design

Two separate HTTP requests bridged by the module `InjectionRegistry` (the B1 pattern, per-subagent):
- **US-1 endpoint** `POST /chat/{session_id}/subagents/{subagent_id}/inject` (`router.py`) — a B1 sibling: gates the parent session (active + owned, 404/409), then `put(tenant, subagent_id, msg)` (409 if the teammate has no live queue). Reuses `InjectRequestBody`.
- **US-2 lifecycle** — `InjectionRegistry.put()` does NOT auto-create a queue (Day-0 finding), so the teammate's queue must be registered ONLY while it runs. The B2a sync `inbox_factory` was reshaped to `TeammateInboxScope` (an async context manager): `make_teammate_inbox_scope(registry, tenant)` registers the queue on `__aenter__` + unregisters on `__aexit__` (success / timeout / exception); the `TeammateExecutor` brackets the child drive in `async with`. So `put()` tells a live teammate from a finished one (no Potemkin dead inbox). The CM lives in the api layer (`injection_registry.py`); the executor depends only on the `MessageInbox` ABC + the scope callable (LLM-neutral; `check_cross_category_import` green).
- **US-3 relay** — `MessageInjected` joins `fork.py::_TAO_CHILD_EVENT_TYPES`, so the child's injection-drain surfaces as a `SubagentChildEvent` (no new event type, no codegen, count unchanged). FE: `chatStore` `subagent_child` text projection += `inner.text`; `InspectorTree.childTurnLabel` + a `message_injected` case.
- **US-5 inline mode-awareness** — `SubagentEntry` += `mode` + `tokensUsed` (dropped the dead always-0 `turns`); `SubagentForkBlock` mode-aware label/icon ("Teammate · peer" / Users vs "Fork · concurrent" / GitFork) + real tokens. Mockup `.subagent-tree`/`.subagent-row`/`.badge` CSS vocabulary unchanged.

`loop.py` diff = 0 (the child reuses the B1 drain seam). No DB / migration.

## Drive-through finding → deferral (US-4 / US-6)

A real-UI + real-Azure drive-through found the inject control **can never render**: the Cat 11→12 SSE relay (Sprint 57.95, `router.py:232-239` + `:445-447`) buffers `SubagentSpawned`/`Child`/`Completed` in a router-owned list and drains it only when the parent loop yields its NEXT event — which happens AFTER the awaited `task_spawn`/teammate completes. The parent blocks in `wait_for` during the teammate run, so spawn+child+completed flush together post-completion → **the FE never observes a teammate as "running"** → the control's `status === "running"` gate is never satisfied. A live inject window needs the detached/streaming teammate (proposal §2.5).

**Decision (Option A)** — per the Drive-Through Acceptance rule (no dead control): removed the un-reachable inject control + `injectToSubagent` service + the `InspectorTree.inject` Vitest; KEPT the proven, reusable backend primitive (endpoint + lifecycle + relay) + US-5. The live inject UI is rebuilt on top of this primitive once §2.5 lands.

## Solution (files)

**Backend (kept)**: `_contracts/subagent.py` (+`TeammateInboxScope`) + `__init__.py`; `subagent/modes/teammate.py` (`inbox_scope` async-CM bracket); `subagent/modes/fork.py` (+`MessageInjected` in the relay tuple); `subagent/dispatcher.py` + `api/v1/chat/_category_factories.py` (`inbox_factory`→`inbox_scope` rename); `api/v1/chat/handler.py` (call `make_teammate_inbox_scope`); `api/v1/chat/injection_registry.py` (+`make_teammate_inbox_scope`); `api/v1/chat/router.py` (the new endpoint).
**Frontend (kept)**: `chat_v2/types.ts` (`SubagentEntry` +mode +tokensUsed); `chat_v2/store/chatStore.ts` (inner.text projection + mode/tokensUsed); `subagent/types.ts` (kind doc); `chat_v2/components/blocks/SubagentForkBlock.tsx` (mode-aware); `chat_v2/components/inspector/InspectorTree.tsx` (`message_injected` child-row render).
**Frontend (removed Day 3)**: the `TeammateInjectControl` + `injectToSubagent` + `InspectorTree.inject.test.tsx`.

## Verification

- Backend unit +9 (0 del): `test_router.py::TestInjectToSubagentEndpoint` (6: 202/404/404/409/409/422); `test_teammate_inbox.py` converted to `inbox_scope` + register/unregister/exception + the drain seam + the relay assertion (3→6).
- Frontend Vitest: `chatStore` `message_injected` projection + completed `tokensUsed`; `blocks` "Teammate · peer" + tokens.
- Gates: mypy `src` 0/355 · `run_all` 10/10 (event count unchanged) · full pytest 2342+4skip · FE build ✓ / lint exit 0 / Vitest 143 / mockup-fidelity 53 · `loop.py`+DB+wire-schema diff 0.
- **Drive-through (real Azure gpt-5.2)**: US-5 "Teammate · peer" + "4,013 tok" DRIVEN; parent integrated "Teammate subagent finding (checkout patrol)" + verification passed (backend flow end-to-end); inject control proven un-drivable (removed). `artifacts/dt57103-*.png`.

## Impact

- Backend-primitive complete + reusable: the inject endpoint + the teammate inbox lifecycle + the MessageInjected relay are proven and unchanged-ready for the §2.5 inject UI.
- US-5 fixes a real mislabel (a teammate is not a fork) end-to-end in the live UI.
- No live inject capability via UI yet — explicitly deferred (not faked). Commits: `7e873583` (backend) + `35c4e797` (FE) + `982520a7` (Option-A control removal).
