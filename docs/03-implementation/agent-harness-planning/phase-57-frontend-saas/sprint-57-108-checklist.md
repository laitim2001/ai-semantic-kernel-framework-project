# Sprint 57.108 — Checklist (UX slice: chat-v2 HITL card real tool/reason + Inspector turn metadata wire — additive `approval_requested` + `llm_response` fields, codegen regen, FE store captures → tool-escalate drive-through)

[Plan](./sprint-57-108-plan.md)

---

## Day 0 — Plan-vs-Repo Verify + Branch ✅

### 0.1 Three-prong Day-0 verify (against `main` HEAD `a42ed717`) — DONE, catalogued in progress.md D1-D8
- [x] **Prong 1 — path verify**: EDIT files Glob-1 (`events.py` / `loop.py` / `event_wire_schema.py` / `sse.py` / `chatStore.ts` / `types.ts` / `HITLTurn.tsx` (actual: `components/turns/`) / `ApprovalCard.tsx` / `InspectorTurn.tsx` / generated artifacts ×2 / codegen script); test suites pinned (`ChatInspector.test.tsx` / `approval-card.spec.ts` / loop escalate unit suites / `test_event_wire_schema_parity.py`); NO new files expected (Glob-0 check n/a)
- [x] **Prong 2 — content verify** (D1 tokensIn already wired via llm_request → overwrite not accumulate; D2 TURN span explicit; D3 no turn_end → durationMs via TURN span_ended fold-in; D6 :1833 reason in scope; D7 constructors keyword-only ×8; D8 relay excludes ApprovalRequested): ALL plan §0 STALE anchors — verification site :1833 reason-in-scope · grep ALL `ApprovalRequested(` constructors (src + tests + resume replay 57.99 + subagent relay `_TAO_CHILD_EVENT_TYPES`) · `llm_response` serializer body (where `cached_input_tokens` is read) · FE `turn_start` handler shape (:382-398) + `stop_reason`/`durationMs` already-wired? (`turn_end`/`loop_end` handlers) · span event payload shape (name/kind — turn-root identifiable?) · `llm_response` multiplicity per AgentTurn · HITLTurn.tsx tool/rationale render lines (D5 — ZERO component edits needed; store-driven) · `events.json` committed envelope shape (codegen-shape drift class)
- [x] **Prong 2.5 — FE tree audit**: HITLTurn / ApprovalCard / InspectorTurn child-import depth-2 grep (shadcn residue / inline-style escapes) — clean (no structural change this sprint; HITLTurn header documents styles-mockup.css classes)
- [x] **Prong 3 — schema verify**: N/A (no DB / no migration) — recorded explicitly
- [x] **Catalog drift** findings in progress.md Day 0 (D1-D8 + implications; plan §8 cross-ref)
- [x] **Go/no-go**: GO — findings SHRINK scope (HITLTurn no-edit; tokens.in done; explicit span match)

### 0.2 Branch
- [x] `git checkout -b feature/sprint-57-108-chatv2-hitl-inspector-wire` (from `main` `a42ed717`)

---

## Day 1 — Backend: additive event fields + wire + serializer + codegen (US-1 + US-3 backend)

### 1.1 `ApprovalRequested` +2 fields + 5-site emission (US-1)
- [ ] **`_contracts/events.py`**: `ApprovalRequested` += `tool_name: str | None = None` + `reason: str = ""` (defaulted; frozen dataclass; MHist 1-line)
- [ ] **`loop.py`**: 5 yield sites pass `reason=` from in-scope local; tool site (:1048) additionally `tool_name=tc.name`; verification site per Day-0 finding (worst case `reason=""`)
  - DoD: grep `yield ApprovalRequested` → 5 sites all carry reason ✓; loop.py diff limited to yield sites ✓
- [ ] **Wire + serializer**: `event_wire_schema.py` approval_requested += `{tool_name: "string | null", reason: "string"}`; `sse.py` approval serializer reads both
- [ ] **Unit tests CONVERT**: loop escalate-shape suites assert new fields (tool site = tc.name; others None) — 0 deletions; parity test fields extended, count stays 24

### 1.2 `llm_response` token pair (US-3 backend)
- [ ] **Wire + serializer**: `event_wire_schema.py` llm_response += `{input_tokens: "number", output_tokens: "number"}`; `sse.py` llm_response serializer reads `event.input_tokens`/`event.output_tokens` (dataclass already carries them — no events.py change)
- [ ] **Codegen regen**: `python scripts/codegen/generate_event_schemas.py` → commit `events.json` + `loopEvents.generated.ts` in the SAME commit
  - DoD: `check_event_schema_sync` green ✓; run_all 10/10 (count 24 UNCHANGED) ✓; mypy strict 0 ✓; black/isort/flake8 0 ✓; full backend pytest 0 del ✓

---

## Day 2 — FE: store captures + renders + Vitest (US-2 + US-3 FE)

### 2.1 HITL card real tool/reason (US-2)
- [ ] **chatStore.ts** `approval_requested` case: `tool: ev.data.tool_name ?? "—"` + `rationale: ev.data.reason || "—"` (drop the :546 hardcode); `approvals[id]` += `toolName`/`reason`; `types.ts` ApprovalEntry +2
- [ ] **HITLTurn.tsx + ApprovalCard.tsx**: render real values per Day-0 render-line findings (store-driven — minimal component diff expected)
- [ ] **Vitest ADD**: approval card/HITLTurn unit cases (real tool renders; non-tool kind → "—" fallback); store capture tests

### 2.2 Inspector metadata captures (US-3 FE)
- [ ] **trace_id**: `turn_start` handler `traceId: ev.data.trace_id ?? null` (drop the :394 hardcode)
- [ ] **span_id**: `span_started` handler links the turn-root span (explicit match per Day-0, fallback first-span-of-turn) to active `AgentTurn.spanId`
- [ ] **tokens**: `llm_response` handler accumulates `tokensIn`/`tokensOut` from `ev.data` (+= semantics; 2-call double-count unit test)
- [ ] **Vitest CONVERT + ADD**: `ChatInspector.test.tsx` placeholder test narrows to cost/thinking ONLY + real-value cases; store unit tests ×3 captures
  - DoD: FE lint 0 (non-silent) ✓ · build ✓ · Vitest green (828+ baseline, 0 del) ✓ · mockup-fidelity 51 unchanged ✓

---

## Day 3 — Full gates + drive-through (US-4) + CHANGE-075

### 3.1 Full gate sweep
- [ ] mypy strict 0 · black/isort/flake8 0 · run_all 10/10 (count 24) · full pytest 0 del · FE 4 gates · wire schema diff = additive-only · loop.py diff = yield sites only

### 3.2 Drive-through (US-4 — real UI + real backend + real Azure; clean no-reload restart per Risk Class E)
- [ ] **HITL card reality**: escalate-phrase / risky-tool ask (57.106 lever) → kind="tool" pause → card shows REAL tool name + reason (not "—") → approve → run continues
- [ ] **Non-tool fallback**: input-phrase escalate → card tool falls back "—", reason real
- [ ] **Inspector reality**: live run → turn pane `trace_id`/`span_id`/`tokens.in`/`tokens.out` real values; `cost`/`tokens.thinking` honest "—"
- [ ] Screenshots (`artifacts/dt57108-*.png`) + observed-vs-intended in progress.md
  - DoD: ALL legs PASS ✓; any policy/test tenant state restored

### 3.3 CHANGE-075
- [ ] `claudedocs/4-changes/feature-changes/CHANGE-075-chatv2-hitl-card-inspector-metadata-wire.md` (1-page; spike design note NOT required — feature continuation, not a new-domain spike)

---

## Day 4 — Closeout

### 4.1 Closeout
- [ ] retrospective.md Q1-Q7 + calibration (`frontend-feature-with-event-wire-addition` 0.55 2nd data point; agent-delegated: no) + progress.md final
- [ ] Navigators: CLAUDE.md Current-Sprint row + Last-Updated; MEMORY.md quality pointer + memory subfile; next-phase-candidates (closes `AD-ChatV2-HITL-Card-Tool-Name` + `AD-ChatV2-Inspector-Turn-Metadata-Wire`; cost carve-out documented); sprint-workflow matrix row (2nd data point)
- [ ] PR (push + open on user authorization)
