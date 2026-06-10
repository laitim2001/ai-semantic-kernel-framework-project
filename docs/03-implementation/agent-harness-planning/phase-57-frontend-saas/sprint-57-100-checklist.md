# Sprint 57.100 — Checklist (chat-v2 verification-reject UI — the A2 follow-up: surface the pause `kind` on the `approval_requested` wire so chat-v2 HITL can REJECT-with-a-coaching-note → resume the verification ESCALATE pause for one human-coached turn)

**Plan**: [`sprint-57-100-plan.md`](./sprint-57-100-plan.md)
**Created**: 2026-06-10
**Status**: Draft — Day-0 verify in progress

> Rule: only `[ ]` → `[x]`; never delete unchecked items; defer with `🚧 + reason`.
> **Feature-continuation** (completes the 57.99 A2 leg's reviewer UI — reuses the shipped `resume()` `kind="verification"` + `ApprovalDecision.reason` + the inline `VerificationBlock`) → **NO new design note** (`sprint-workflow.md §Step 5.5`, the 57.91-93/99 precedent). Record = CHANGE-067 + **update 17.md** (the `approval_requested` wire gains `kind`) + **25.md §4** (the A2 reviewer UI → SHIPPED). Gate = full backend pytest + frontend Vitest green (NET delta) + **drive-through PASS** (the REJECT half — a forced-fail judge → escalate pause → coaching note → Reject → the loop re-answers with the coaching). Load-bearing decision: add `kind` to the `approval_requested` wire (additive field, NOT a new event type) — the event-ordering inference alternative is a rejected Potemkin heuristic. Out: rich verification card (the `VerificationBlock` already shows the reason), per-tenant policy (C3), multi-round coaching, the `ApprovalCard.tsx` fallback, 4-action UX.

---

## Day 0 — Plan-vs-Repo Verify + Branch

### 0.1 Three-prong Day-0 verify
- [x] **Prong 1 (path)**: re-confirmed all anchors on `a890bb15` — `sse.py :229-238` (request_id+risk_level only) · `events.py ApprovalRequested :399-403` (no kind) · `loop.py` 5 yield sites `:814`/`:1030`/`:1433`/`:1596`/`:1812` + 5 `_emit_deferred_pause` `:825`/`:1061`/`:1444`/`:1608`/`:1824` · `event_wire_schema.py :119-122` · codegen + parity tests + lint · `governanceService.decide :71-83` (reason arg ✅) · `useLoopEventStream.resume :98-120` · `HITLTurn.tsx :106-141` (approve-only resume; meta `:186-191`) · `types.ts :146-158` · `chatStore.ts :453-487` + `verification_failed VerificationBlock :608-633`. (progress.md Day-0 Prong 1)
- [x] **Prong 2 (content)**: confirmed — emit-site `kind` literals from `pending_approval["kind"]` (`:821` input / `:1052` tool / `:1440` between_turns / `:1603` output / `:1819` verification); `_emit_deferred_pause` has NO `kind=` param (kind lives in `pending_approval`) → set `kind=` at the YIELD site; `sse.py` reads `event.<field>` (so `event.kind` works); schema vocab `"string"` matches; codegen nested `{type,data}` → `ApprovalRequestedEvent.data` gains `kind`; `chatStore` narrows on `ev.type` → `ev.data.kind` typed post-regen; `decide(reason?)` + `resume()` need no change. (progress.md Day-0 Prong 2)
- [x] **Prong 2.5 (frontend tree)**: confirmed — `HITLTurn.tsx` canonical (not `ApprovalCard.tsx`); e2e contracts additive-safe; the note textarea has NO mockup source → mockup `.hitl-card`/input vocab + `var(--*)` (no new HEX/oklch); **D-DAY0-2**: tests EXIST (`HITLTurn.resume.test.tsx` + `chatStore.mergeEvent.test.ts` + `eventSchema.generated.test.ts`) → EXTEND, do not create. (progress.md Day-0 Prong 2.5)
- [x] **Prong 3 (schema)**: N/A confirmed — no DB/migration/ORM; the wire change is a FIELD on the EXISTING `approval_requested` type → NO event-count bump (22 stays 22); `check_event_schema_sync` stays green after regen. No new table/column/event-type/DTO.
- [x] **Baseline capture**: `main a890bb15` — mypy `src` **0/353** ✅ · pytest collect `-m "not real_llm"` **2303** ✅ · run_all **10/10** ✅ · frontend Vitest + `check:mockup-fidelity` HEX_OKLCH baseline (background run, recorded in progress.md)
- [x] **Design-note decision**: feature-continuation → NO new design note (the 57.91-93/99 precedent); plan to UPDATE 17.md (the `approval_requested` wire +kind) + 25.md §4 (the A2 reviewer UI → SHIPPED). Confirmed in progress.md.
- [x] **Forced-fail drive-through setup**: reuse the 57.99 env approach (`CHAT_VERIFICATION_MODE=enabled` + `CHAT_VERIFICATION_ESCALATE_ON_MAX=true` + strict `CHAT_VERIFICATION_JUDGE_TEMPLATE` + neutral "no tools, just re-answer" prompt — the 57.99 D-DAY3-2 lesson); cheap deployment (57.97) set
- [x] Catalogue Day-0/Day-1 drift in progress.md; **go/no-go = GO** (slice = `kind` wire field + codegen regen + verification-gated frontend reject-with-note; D-DAY0-1 = a literal-ordering correction, no scope shift; D-DAY0-2 = scope shrinks, extend not create; D-DAY0-3 = held answer/reason already rendered)

### 0.2 Branch
- [x] Branch `feature/sprint-57-100-chatv2-verification-reject-ui` from `main` (`a890bb15`)
- [ ] plan + checklist + progress committed (Day-0 commit)

---

## Day 1 — The `kind` wire field + codegen (US-1)

### 1.1 The event + emit sites
- [ ] **`_contracts/events.py`** — `ApprovalRequested` +`kind: str = ""` (frozen dataclass field, optional default); MHist
  - DoD: `mypy src` 0; all 5 emit sites + any test constructors still build
- [ ] **`loop.py` 5 emit sites** — pass `kind=` at `:814`(`"tool"`)/`:1030`(`"input"`)/`:1433`(`"between_turns"`)/`:1596`(`"output"`)/`:1812`(`"verification"`); MHist
  - DoD: each site's `kind=` literal == its `pending_approval["kind"]` (Prong 2 confirmed); `mypy src` 0

### 1.2 The wire + schema + codegen
- [ ] **`api/v1/chat/sse.py`** — the `approval_requested` serializer (`:229-238`) +`"kind": event.kind`; MHist
- [ ] **`api/v1/chat/event_wire_schema.py`** — the `"approval_requested"` entry (`:119-122`) +`"kind": "string"`; MHist
- [ ] **codegen regen** — `python scripts/codegen/generate_event_schemas.py` → `frontend/src/features/chat_v2/generated/loopEvents.generated.ts` regenerates
  - DoD: `git diff` the generated `.ts` → the ONLY change is the `approval_requested` `kind` field (no spurious reformat / unrelated drift); event count unchanged (22)
- [ ] **backend lint/type** — `mypy src` 0; `python scripts/lint/check_event_schema_sync.py` green; the backend parity test `test_event_wire_schema_parity.py` green (regenerated)

---

## Day 2 — The frontend capture + REJECT-with-note (US-2/US-3/US-4/US-5)

### 2.1 Capture `kind` (US-2)
- [ ] **`chat_v2/types.ts`** — `HITLTurn` +`kind: string` (after `tool`); MHist
- [ ] **`chat_v2/store/chatStore.ts`** — the `approval_requested` case (`:453-487`) sets `kind: ev.data.kind ?? ""` on the `HITLTurn`; MHist
  - DoD: a unit feeds `approval_requested` `kind:"verification"` → pushed `HITLTurn.kind==="verification"`; no kind → `""`

### 2.2 REJECT-with-coaching-note, verification-gated (US-3/US-4)
- [ ] **`HITLTurn.tsx` state + gating** — `rejectNote`/`showNoteInput` state; `isVerification = turn.kind === "verification"`; `submitDecision(decision, note?)` passes `note` to `decide` + resumes when `awaiting_approval && (approved || (rejected && isVerification))`; MHist
- [ ] **Reject button behavior** — `isVerification && !showNoteInput` → Reject reveals the note input (`setShowNoteInput(true)`); `!isVerification` → Reject submits `"rejected"` immediately (today's behavior); a "Reject with note" confirm button (only when `showNoteInput`) submits `"rejected"` + `rejectNote`
  - DoD: a verification turn — Reject reveals the textarea; confirm → `decide(id,"rejected",note)` + `resume()`. A tool turn — Reject submits immediately, NO textarea, NO resume (byte-identical)
- [ ] **The note textarea** — design-system-consistent (mockup `.hitl-card`/input vocab + `var(--*)` tokens, NO invented colors); `aria-label="Coaching note"`; optional (placeholder "(optional)…")
  - DoD: `npm run check:mockup-fidelity` HEX_OKLCH baseline unchanged

### 2.3 Kind-aware render (US-5)
- [ ] **The meta row** (`:186-191`) — `isVerification` → render `kind: verification` (mono, `var(--tool)` tone) instead of `tool: {turn.tool}`; otherwise unchanged; MHist
  - DoD: a verification turn's card reads `kind: verification`; a tool turn reads `tool: {turn.tool}`

---

## Day 3 — Tests + full regression + drive-through (US-6) + CHANGE-067

### 3.1 Tests (US-1..US-5)
- [ ] **backend sse-kind test** — `ApprovalRequested(kind="verification")` → the wire `data` carries `"kind":"verification"`; the escalate pause emits `kind="verification"` (extend the 57.99 escalate test or a new small test)
- [ ] **backend parity** — `test_event_wire_schema_parity.py` green (regenerated `approval_requested` +kind)
- [ ] **frontend parity** — `eventSchema.generated.test.ts` green (regenerated)
- [ ] **frontend chatStore unit** — `approval_requested` `kind:"verification"` → `HITLTurn.kind==="verification"`; no kind → `""`
- [ ] **frontend HITLTurn unit** (NEW if absent) — a verification turn: Reject reveals the textarea; confirm → `decide` called `(id,"rejected",note)` + `resume` called; meta reads `kind: verification`. A tool turn: Reject → `decide(id,"rejected")` (no note) + `resume` NOT called; no textarea
- [ ] **existing e2e contracts** — `approval-card.spec.ts` (approval_id / HIGH / Decision / data-testids) still pass (additive change)

### 3.2 Full gate sweep
- [ ] **Full backend pytest green (NET delta documented)** — NO test deleted; baseline collect → delta
- [ ] **mypy 0 + run_all 10/10 + format chain** — `mypy src` 0; run_all **10/10** (`check_event_schema_sync` green; LLM SDK leak 0); black/isort/flake8 **FULL `src/ tests/` scope** clean — run INDEPENDENTLY (no `&&`; the 57.98 CI-black lesson)
- [ ] **Frontend gate** — `npm run lint` (WITHOUT `--silent` — the 57.40 lesson) + `npm run build` + `npm run check:mockup-fidelity` (baseline unchanged) + `npm run test` (Vitest) green

### 3.3 Drive-through (US-6 — the REJECT half)
- [ ] **Clean backend restart (Risk Class E)** — kill the stale uvicorn reloader + `multiprocessing.spawn` worker (`Get-CimInstance Win32_Process` PID/PPID/StartTime + `Stop-Process -Force`); verify :8000 free + the FRESH PID is the sole owner; do NOT touch node :3007 / claude-code node; start a fresh process with the forced-fail judge env (`CHAT_VERIFICATION_MODE=enabled` + `CHAT_VERIFICATION_ESCALATE_ON_MAX=true` + the strict `CHAT_VERIFICATION_JUDGE_TEMPLATE`); restore the normal `--reload` backend after
- [ ] **Drove a verification fail → escalate → REJECT-with-note → re-answer** — real UI (jamie@acme.com/acme-prod) + real backend + real Azure + a real LLM judge (forced-fail): a failing answer → escalate pause (the card shows `kind: verification` + the inline `VerificationBlock` reason) → type a coaching note → Reject → the loop re-answers with the reviewer's coaching in context (one bounded turn). Screenshot(s) + observed-vs-intended in progress.md
  - NOTE (honest gap): the forced-fail is a real LLM judge instructed to fail (deterministic) — clearly labelled DEMO; the reject-with-note mechanism is unit-proven. NOT claimed "gate-only". Use a neutral "no tools, just re-answer" prompt (the 57.99 D-DAY3-2 lesson)

### 3.4 CHANGE-067 + 17.md + 25.md §4
- [ ] `claudedocs/4-changes/feature-changes/CHANGE-067-chatv2-verification-reject-ui.md` written
- [ ] **`17-cross-category-interfaces.md`** — the `approval_requested` wire gains `kind` (tool/input/between_turns/output/verification); the chat-v2 HITL card branches REJECT on `kind==="verification"` (resume-with-note) vs terminate (others); MHist
- [ ] **`25-verification-in-loop-design.md` §4** — the A2 reviewer-facing UI (the chat-v2 verification-reject path) → SHIPPED (with file:line); MHist

---

## Day 4 — Closeout (feature-continuation — NO design note)

### 4.1 Closeout
- [ ] Full validation (parent re-verified): backend pytest (NET delta, zero deletion) / mypy `src` 0/353 / run_all 10/10 / **black FULL `src tests` clean** / frontend Vitest (delta) + lint(no `--silent`) + build + check:mockup-fidelity (baseline unchanged) / `resume()`+`hitl.py`-DTO+`governanceService`+DB+`ApprovalCard.tsx`+`ModelProfile` diff = **0** / **drive-through PASS** (the REJECT half — escalate → coaching note → Reject → re-answer; artifacts)
- [ ] progress.md (Day 0-3) + retrospective.md (Q1-Q7)
- [ ] Calibration: `frontend-feature-with-event-wire-addition` 0.55 (NEW class, 1st data point) + `agent_factor` 1.0 (parent-direct); recorded `calibration-log.md §3` + `sprint-workflow.md §Scope-class matrix` row; carryover → next-phase-candidates.md
- [ ] MEMORY.md pointer + `project_phase57_100_*.md` subfile + CLAUDE.md lean (Current Sprint row + Last Updated) + CHANGE-067 + 17.md + 25.md §4
- [ ] commit (Day 0-N) + push + PR (user-authorized)
