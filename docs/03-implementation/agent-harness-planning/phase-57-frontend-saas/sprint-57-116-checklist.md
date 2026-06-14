# Sprint 57.116 — Checklist (Skills Force-Load Inspector Affordance: a server-confirmed `active_skill` additive field on the `loop_start` SSE event (sse.py default `None` + event_wire_schema field + router `_stream_loop_events` augment + codegen regen, count 24, `loop.py`/`events.py` untouched) + a chat-v2 `UserTurn.activeSkill` store stamp (truthy guard) + a `.route-pill` "⚡ {skill}" chip — the first Skills-epic UX affordance, closes `AD-Skills-Inspector-Affordance`; Inspector-panel row / per-read_skill chip / dedicated skill event deferred)

[Plan](./sprint-57-116-plan.md)

---

## Day 0 — Plan-vs-Repo Verify (三-prong; no Prong-3 schema — no new table) + Branch

### 0.1 Three-prong Day-0 verify (against `main` HEAD `fc385a87`) — catalogued in progress.md ✅
- [x] **Prong 1 — path verify**: NEW absent (Glob-0) — `test_loop_start_active_skill.py` / `chatStore.activeSkill.test.ts` / `UserTurn.skillChip.test.tsx` confirmed 0; EDIT present confirmed; CHANGE 083 free; FE tests → `frontend/tests/unit/chat_v2/` (basenames unique)
- [x] **Prong 2 — content verify** (drift findings → progress.md):
  - [x] **D-sse-loopstarted** 🟢: serializer `:138-143` → add `"active_skill": None`; **CONFIRMED conformance test EXISTS** (`test_event_wire_schema_parity.py`) → the default `None` is REQUIRED
  - [x] **D-wire-schema** 🟢: `WIRE_SCHEMA["loop_start"]` `:87-90` → add field; the 24 count is the dict-KEY count → unchanged
  - [x] **D-router-augment (CRITICAL)** 🟢: `forced_skill` `:279` / call `:413` / def `:570` / serialize `:641`; **DRIFT: `LoopStarted` NOT imported in router.py** → add the import
  - [x] **D-resume-mirror** 🟢: `_stream_resume_events` `:1080` — NOT touched (resume `loop_start` stays `null`)
  - [x] **D-fe-store** 🟢: `chatStore` `case "loop_start"` `:363` returns a new state preserving turns → stamp the last `role==="user"` turn when `active_skill` truthy
  - [x] **D-fe-userturn** 🟢: `UserTurn.tsx` `.turn-head` + the `injected` `.route-pill` (`:53-57`) to mirror; `types.ts` `UserTurn` `:128-136`
  - [x] **D-route-pill** 🟢: `.route-pill` (`styles-mockup.css:1101`) — design tokens only (no colour literal); reuse
  - [x] **D-codegen** 🟢: `scripts/codegen/generate_event_schemas.py`; `run_all` codegen `--check` diffs until regen
- [x] **Prong 3 — N/A** (no new table / migration / ORM this sprint)
- [x] **Catalog drift** findings in progress.md Day 0 (1 real: `LoopStarted` import absent; 1 constraint: parity test → serializer default `None` mandatory)
- [x] **Go/no-go**: 🟢 GO — design confirmed, no scope shift > 20%

### 0.2 Branch ✅
- [x] `git checkout -b feature/sprint-57-116-skills-inspector-affordance` (from `main` `fc385a87`)

---

## Day 1 — Backend: `active_skill` on `loop_start` (serializer default + wire schema + router augment) + codegen + tests (US-1)

### 1.1 Serializer default + wire schema (US-1 backend half) ✅
- [x] **`api/v1/chat/sse.py`** (EDIT): `LoopStarted` serializer `data` += `"active_skill": None` (default; router overrides); WHY comment + MHist
- [x] **`api/v1/chat/event_wire_schema.py`** (EDIT): `WIRE_SCHEMA["loop_start"]` += `"active_skill": "string | null"`; MHist
- [x] **`tests/unit/api/v1/chat/test_loop_start_active_skill.py`** (NEW ×4): serializer default `None` (with/without session) · `WIRE_SCHEMA["loop_start"]` has `active_skill` · 24 wire-type count unchanged
  - DoD: ✅ 71/71 pass (incl. the `test_event_wire_schema_parity.py` guard green); mypy 0; count 24

### 1.2 Router `_stream_loop_events` augment (US-1 router half) ✅
- [x] **`api/v1/chat/router.py`** (EDIT): imported `LoopStarted` (was absent); `_stream_loop_events(..., active_skill: str | None = None)`; passed `active_skill=forced_skill` at the `:413` call; injected at `:641` (`if active_skill and isinstance(event, LoopStarted): payload["data"]["active_skill"] = active_skill`); `_stream_resume_events` UNTOUCHED; WHY comment + MHist
- [x] **`tests/integration/api/test_chat_e2e.py`** (EDIT — NOT `test_chat_force_load_skill.py`; +3): **Day-1 DRY adjustment** — the SSE-level assertions reuse the echo-mode TestClient `_parse_sse` harness here (echo computes `forced_skill` the same router-level way as real_llm → no real Azure needed) rather than duplicating a TestClient app in the build_handler-level force-load file. confirmed (`code-review` → `loop_start.active_skill=="code-review"`) · null (no force_load) · null (unknown name → router drops it)
  - DoD: ✅ tests pass; the 主流量 router emits the confirmed skill on `loop_start`; `loop.py`/`events.py` UNTOUCHED

### 1.3 Codegen regen + backend gate sweep (US-1) ✅
- [x] **`python scripts/codegen/generate_event_schemas.py`** → regenerated `loopEvents.generated.ts` (`LoopStartEvent.data.active_skill: string | null`) + `events.json`; `KNOWN_LOOP_EVENT_TYPES` unchanged (24)
- [x] mypy `src` **0/370** · black/isort/flake8 0 · `python scripts/lint/run_all.py` **10/10** (count 24; codegen `--check` clean AFTER regen) · `loop.py`/`events.py`/`LoopStarted` dataclass/`read_skill`/`_stream_resume_events` UNTOUCHED · no migration
- [x] full pytest **2623 passed + 5 skip (+7, 0 del)** vs 2616
  - Verify: ✅ `cd backend && python -m mypy src` · `python scripts/codegen/generate_event_schemas.py` · `python scripts/lint/run_all.py` (repo root) · `python -m pytest -q`

---

## Day 2 — Frontend: `UserTurn.activeSkill` store stamp + the `.route-pill` chip + Vitest (US-2, US-3, US-4)

### 2.1 Store stamp (US-2) ✅
- [x] **`features/chat_v2/types.ts`** (EDIT): `UserTurn` += `activeSkill?: string` (after `injected?`)
- [x] **`features/chat_v2/store/chatStore.ts`** (EDIT): in `mergeEvent` `case "loop_start"`, precompute `lastUserIdx` (reduce, only when `ev.data.active_skill` truthy); the `turns` map stamps that turn's `activeSkill` (folded with the 57.88 agent-waiting clear, narrowing `t` per branch); a `null`/absent value → `turns` unchanged (truthy guard, resume-safe); WHY comment + MHist
- [x] **`tests/unit/chat_v2/chatStore.activeSkill.test.ts`** (NEW ×4): `active_skill` stamps the last user turn · `null` → no stamp · a later `null` doesn't clear an existing chip · the last USER turn is stamped (a trailing agent turn skipped)
  - DoD: ✅ Vitest pass; truthy guard + last-user-turn target verified

### 2.2 The chip (US-3) ✅
- [x] **`features/chat_v2/components/turns/UserTurn.tsx`** (EDIT): in `.turn-head` after the timestamp, a conditional `.route-pill` "⚡ {activeSkill}" chip (`data-testid="user-turn-skill-chip"`, `title="Skill: …"`) — mirrors the `injected` `.route-pill`; inline English; mockup token only (no colour literal)
- [x] **`tests/unit/chat_v2/UserTurn.skillChip.test.tsx`** (NEW ×2): chip renders "⚡ {skill}" when `activeSkill` set · absent when unset
  - DoD: ✅ `npm run build` clean; chip renders conditionally
- [x] **Build-time fix** (tsc -b stricter than Vitest transform): the generated `LoopStartEvent.data.active_skill` is REQUIRED → fixed `chatStore.ts` union narrowing (narrow `t` per branch, not a `let next`) + `features/orchestrator-loop/_fixtures/demoLoopEvents.ts:73` (add `active_skill: null`). Lesson: a REQUIRED codegen field breaks every existing event LITERAL → run `npm run build`, not just Vitest, after a wire field add.

### 2.3 FE gate sweep (US-4) ✅
- [x] `npm run lint` (NO `--silent`) 0 error (TSSatisfiesExpression = pre-existing plugin noise) · `npm run build` ✓ (tsc + vite) · `npm run test` Vitest **869 (+6 vs 863)** · `npm run check:mockup-fidelity` **51** holds (no CSS change; `.route-pill` reused)
  - Verify: ✅ `cd frontend && npm run lint && npm run build && npm run test && npm run check:mockup-fidelity`

---

## Day 3 — Drive-through (US-5) — real chat-v2 + fresh backend + real Azure LLM (Risk Class E clean restart)

### 3.1 Clean restart + probe ✅
- [x] Killed stale backend PID 26524 (57.115 code) via `Stop-Process`; port 8000 free + ZERO orphan uvicorn (`Win32_Process` sweep, no `--reload` workers); restarted from **repo-root** `PYTHONPATH=backend/src ... --env-file .env`; startup-log all-wired + complete (fresh 57.116 process). dev-login `acme-skills`/jamie 200; `GET /api/v1/chat/skills` → [code-review, summarize, release-notes] (persisted overlay). API pre-probe (curl-layer sanity): echo_demo `force_load_skill=release-notes` → loop_start `active_skill="release-notes"`; unknown → `null`

### 3.2 Drive-through 1 leg / 3 cases ✅ (real chat-v2 :3007 + real Azure gpt-5.2, mode=real_llm)
- [x] **Leg A (force-load → chip + determinism) PASS**: `/release-notes <task>` → Send → user turn shows **`⚡ release-notes`** chip (`data-testid` + `title="Skill: release-notes"`) + the `/token` STRIPPED + output follows `## Summary/## Highlights/## Upgrade steps` + Inspector `read_skill` **0×** (`toolBlockCount=0`, `mentionsReadSkill=false`) + verification 0.99. `artifacts/sprint-57-116-legA-userturn-skill-chip.png`
- [x] **Leg B (graceful unknown → no chip) PASS**: `/nonexistent reply with exactly: OK` → user turn shows the LITERAL token (not stripped) + **NO chip** (router dropped → `active_skill:null`) + agent "OK"; `totalChips` stays 1. `artifacts/sprint-57-116-legB-unknown-no-chip.png`
- [x] **Leg C (plain → no chip) PASS**: `What is 2 plus 2?` (no `/`) → **NO chip** + agent "4"; `totalChips` stays 1. `artifacts/sprint-57-116-legC-plain-no-chip.png`
- [x] Each control driven (real LLM, no fixture): the chip is SERVER-confirmed (Leg B — a `/nonexistent` token the FE sent yields no chip → not a client echo); bound to the CORRECT triggering turn (3 user turns, only Leg A chipped); Drive-Through-Acceptance + AP-4 guard satisfied
  - DoD: ✅ ALL 3 cases PASS + the chip is server-confirmed

---

## Day 4 — CHANGE-083 + closeout (NO design note — feature continuation)

### 4.1 CHANGE-083
- [ ] **`claudedocs/4-changes/feature-changes/CHANGE-083-skills-inspector-affordance.md`** (1-page, incl. the 3-case drive-through)
- [ ] (NO design note — feature continuation of the validated Skills epic + the 57.108 additive-wire-field pattern; sprint-workflow §5.5 → design note is spike-only)

### 4.2 Closeout
- [ ] retrospective.md Q1-Q7 + calibration (`frontend-feature-with-event-wire-addition` 0.55 **3rd data point** — ratio vs ~1.05 mean; parent-direct agent_factor 1.0) + progress.md final
- [ ] Navigators: CLAUDE.md Current-Sprint row + Last-Updated (minimal touch); MEMORY.md quality pointer + memory subfile `project_phase57_116_skills_inspector_affordance.md`; next-phase-candidates — `AD-Skills-Inspector-Affordance` CLOSED + 57.116 carryover block + remaining Skills ADs carried; sprint-workflow matrix `frontend-feature-with-event-wire-addition` 0.55 3rd-point update; 17.md — N/A (additive `loop_start` field, no new contract)
- [ ] **Anti-pattern self-check** (retro Q5/Q7): AP-4 (drive-through proves the chip is server-confirmed — Leg B no-chip on an invalid name) · AP-2 (force-load → router augment → loop_start → store → chip main flow) · AP-3 (wire field chat api / store+render chat_v2) · AP-6 (additive field, no speculative new event type)
- [ ] PR (push + open on user authorization)
