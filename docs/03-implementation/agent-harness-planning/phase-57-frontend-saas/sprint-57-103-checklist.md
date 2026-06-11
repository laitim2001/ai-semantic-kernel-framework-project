# Sprint 57.103 — Checklist (chat-user inject-to-teammate: live MessageInbox producer + injected child turn on the Tree + inline block mode-awareness — B2b: the live UI producer the B2a teammate inbox was wired "until B2b" for)

[Plan](./sprint-57-103-plan.md)

**Status**: Completed — US-1/2/3 backend + US-5 shipped & driven; **US-4 inject control + US-6 live inject 🚧 DEFERRED to proposal §2.5** (drive-through Day 3 found the FE never observes a teammate as "running" under the buffered SSE relay + await-completion → the control can never render; removed per Option A, no dead control)
**Branch**: `feature/sprint-57-103-inject-to-teammate`

---

## Day 0 — Plan-vs-Repo Verify + Branch

### 0.1 Three-prong Day-0 verify (re-confirm against HEAD `0209c672` before Day-1 code)
- [x] **Prong 1 — path verify**: Glob-confirm every File Change List path exists/absent as expected (router.py / teammate.py / fork.py / dispatcher.py / _category_factories.py / handler.py / _contracts/subagent.py; FE chatService.ts / InspectorTree.tsx / chatStore.ts / subagent/types.ts / chat_v2/types.ts / SubagentForkBlock.tsx; test files)
- [x] **Prong 2 — content verify** (the load-bearing greps):
  - `injection_registry.py:73-82` `put()` returns False on no-queue (NOT auto-create) — re-confirm
  - B1 parent `register()` call line + the router SSE `unregister` finally line (pin both for the lifecycle mirror)
  - `_TAO_CHILD_EVENT_TYPES` (`fork.py:80-86`) — confirm `MessageInjected` absent + the tuple membership
  - `teammate.py:137` inbox build site + `:162` the blocking `wait_for` (confirm the `async with` insertion point)
  - `handler.py:388-395` `_make_teammate_inbox` (confirm the rename target + the tenant-None guard)
  - `dispatcher.py` teammate branch + the `inbox_factory` thread param name
  - `chatStore.ts` `subagent_child` reducer + `ChildTurnEvent.kind` set (`subagent/types.ts:65-76`)
  - `SubagentForkBlock.tsx:63` "Fork · concurrent" + `:88` "{a.turns}t" + `SubagentEntry` (`types.ts:64-70`) field set
- [x] **Prong 3 — schema verify**: N/A (no DB / migration / ORM / new wire schema this sprint) — record "N/A: no schema change"
- [x] **Catalog drift** in progress.md Day 0 (`D{N}` + finding + implication; do NOT silently rewrite plan §3 — add to §8 Risks)
- [x] **Go/no-go**: scope shift ≤20% → continue; 20-50% → re-confirm §5/§7; >50% → abort + redraft

### 0.2 Branch
- [x] `git checkout -b feature/sprint-57-103-inject-to-teammate` (done; HEAD `0209c672`)

---

## Day 1 — Backend: endpoint + `inbox_scope` lifecycle + relay (US-1/US-2/US-3 backend)

### 1.1 The `inbox_scope` contract + executor bracket (US-2)
- [x] **`TeammateInboxScope` contract** (`_contracts/subagent.py` + `__init__.py` export)
  - `Callable[[UUID], "AbstractAsyncContextManager[MessageInbox | None]]"`; TYPE_CHECKING-safe import
  - DoD: mypy green; `check_cross_category_import` green (no api import into agent_harness)
- [x] **`TeammateExecutor` `inbox_factory` → `inbox_scope`** (`teammate.py`)
  - `__init__` param rename + type; `execute()` brackets the child drive in `async with self._inbox_scope(subagent_id) as inbox:` (None scope → inbox None, byte-identical no-op path)
  - fail-closed returns stay inside the `async with`; mailbox-report drain + success return after it closes
  - DoD: mypy green; the no-scope path is byte-identical to the no-inbox path

### 1.2 Handler + dispatcher wiring (US-2)
- [x] **`_teammate_inbox_scope` async-CM** (`handler.py`)
  - `@asynccontextmanager`: `await registry.register(tenant, sid)` → `yield QueueMessageInbox(registry, tenant, sid)` → `await registry.unregister(tenant, sid)`; tenant-None guard preserved
  - thread `inbox_scope=` through `make_chat_subagent_dispatcher`
- [x] **Thread `inbox_scope`** (`_category_factories.py` + `dispatcher.py` rename of the `inbox_factory` param)
  - DoD: mypy green; the dispatcher passes `inbox_scope` to `TeammateExecutor`

### 1.3 The inject-to-teammate endpoint (US-1)
- [x] **`POST /{session_id}/subagents/{subagent_id}/inject`** (`router.py`)
  - parent gate via `get_default_registry().get(tenant, session_id)` → 404; `status != "running"` → 409
  - `put(tenant, subagent_id, Message(...))`; `put()==False` → 409; return `{"status":"queued"}` (202)
  - reuse `InjectRequestBody`; empty message → 422 (Field min_length)
  - DoD: mypy green; route registered (no new DTO)

### 1.4 Relay `MessageInjected` to the Tree (US-3 backend)
- [x] **Add `MessageInjected` to `_TAO_CHILD_EVENT_TYPES`** (`fork.py`)
  - DoD: a child `MessageInjected` produces a `SubagentChildEvent` (emitter assertion); `check_event_schema_sync` count UNCHANGED (no new type)

---

## Day 2 — Frontend: inject control + injected-turn render + inline mode-awareness + tests (US-3 FE/US-4/US-5)

### 2.1 FE service + inject control + injected child row (US-4 + US-3 FE)
- [ ] **`injectToSubagent`** (`chatService.ts`) — 🚧 DEFERRED → §2.5 (built Day 2, REMOVED Day 3 per Option A: inject UI blocked by await-completion)
- [ ] **Inject control on running teammate node** (`InspectorTree.tsx`) — 🚧 DEFERRED → §2.5 (built + Vitest-proven Day 2, REMOVED Day 3: the FE never observes a teammate "running" under the buffered relay → control can never render)
- [x] **`message_injected` child row** (`InspectorTree.childTurnLabel` + `chatStore.ts` `subagent_child` text projection += `inner.text` + `subagent/types.ts` `kind` doc)
  - the relay render is correct + reachable once a live inject window exists (§2.5); the backend relay primitive is wired + unit-proven now

### 2.2 Inline block mode-awareness (US-5 — 🟢 carryover)
- [x] **`SubagentEntry` += `mode` + `tokensUsed`** (`chat_v2/types.ts`) + source them at the `subagent_spawned`/`subagent_completed` dual-emit (`chatStore.ts`) — dropped the dead always-0 `turns`
- [x] **Mode-aware label + real tokens** (`SubagentForkBlock.tsx`): `"teammate"` → "Teammate · peer" (icon Users); show `tokensUsed` — DRIVE-THROUGH PROVEN ("Teammate · peer" + "4,013 tok")

### 2.3 Tests (US-1..US-5)
- [x] **Backend** `test_router.py::TestInjectToSubagentEndpoint` (202 / 404 missing / 404 cross-tenant / 409 parent-not-running / 409 teammate-no-queue / 422 empty)
- [x] **Backend** `test_teammate_inbox.py` CONVERT to `inbox_scope` + ADD register-on-enter / unregister-on-exit / unregister-on-exception + the drain seam test (3 → 6)
- [x] **Backend** `test_teammate.py` + `_child_loop_helpers.py` — N/A: neither used the old `inbox_factory` ctor arg (Day-0 confirmed; no conversion needed)
- [x] **Backend** relay assertion (child `MessageInjected` → `SubagentChildEvent`)
- [x] **Frontend Vitest**: chatStore `message_injected` projection + completed `tokensUsed`; blocks "Teammate · peer" + tokens (the InspectorTree.inject gating tests were REMOVED Day 3 with the control → §2.5)

---

## Day 3 — Full regression + drive-through (US-6) + CHANGE-070 + 17.md

### 3.1 Full gate sweep
- [x] `black . && isort . && flake8 .` (src tests) clean
- [x] `mypy src` 0 errors (0/355)
- [x] `python scripts/lint/run_all.py` 10/10 (event count UNCHANGED; `check_llm_sdk_leak` 0; `check_cross_category_import` green; `check_ap1` green)
- [x] full `pytest -q` green — **2342 passed + 4 skipped (+9, 0 deletions)**
- [x] frontend `npm run lint` (exit 0, no `--silent`) + `npm run build` ✓ + Vitest 143 + `npm run check:mockup-fidelity` 53 unchanged
- [x] `git diff` confirms `loop.py` / DB / migration / generated wire schema diff = 0

### 3.2 Drive-through (US-6 — inject into a running multi-turn teammate)
- [x] Clean restart (Risk Class E): killed stale reloader 29576 + spawn-worker 38668; fresh no-reload backend PID 16496 sole :8000 owner; frontend node untouched
- [x] Real UI (real_llm) + real Azure gpt-5.2: spawned real multi-turn teammates (mock_patrol_check_servers patrols)
- [ ] Inject mid-run via the Tree node control — 🚧 IMPOSSIBLE under await-completion: the FE never observes a teammate "running" (buffered relay flushes spawn+child+completed together post-completion) → the control never renders → §2.5
- [ ] Observe the injected child turn reflected — 🚧 same blocker (no live inject possible); the `message_injected` relay render is unit-proven + reachable once §2.5 lands
- [x] Screenshots (`artifacts/dt57103-teammate-completed-no-running-window.png` = the finding; `artifacts/dt57103-shipped-teammate-label-tokens-parent-integrated.png` = what shipped) + observed-vs-intended in progress.md
- [x] Walk every control: US-5 "Teammate · peer" + "4,013 tok" DRIVEN; the inject control was REMOVED (no dead control per Drive-Through rule)

### 3.3 CHANGE-070 + 17.md + design note 20
- [x] `CHANGE-070-inject-to-teammate.md` (problem / design / verification / impact + the await-completion finding)
- [x] 17.md Cat 11: `TeammateInboxScope` contract + the inject-to-subagent endpoint + MessageInjected-in-relay note
- [x] design note 20 §5: B2b backend primitive shipped; the live inject UI deferred to §2.5 (await-completion finding)

---

## Day 4 — Closeout (composition continuation — no new design note)

### 4.1 Closeout
- [x] progress.md Day 0-3 + drive-through complete
- [x] retrospective.md Q1-Q7 (Q2 calibration; Q4 the await-completion planning-miss lesson; Q7 no-design-note rationale)
- [x] CLAUDE.md Current Sprint + Last Updated (lean, per §Sprint Closeout policy)
- [x] MEMORY.md pointer + `project_phase57_103_inject_to_teammate.md` subfile
- [x] next-phase-candidates.md: B2b backend primitive + US-5 done; **inject UI deferred to §2.5** (await-completion prerequisite)
- [x] sprint-workflow.md calibration row `subagent-inject-to-teammate 0.55` (1st data point)
- [x] all checklist items `[x]` or 🚧 (never deleted unchecked; US-4/6 marked 🚧 DEFERRED with reason)
