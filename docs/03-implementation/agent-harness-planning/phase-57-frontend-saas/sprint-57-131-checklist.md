# Sprint 57.131 — Checklist (chat-v2 Inspector Turn tab `model` row)

> Full description: see the plan's **Summary**. Closes the `model` row leg of `AD-ChatV2-Inspector-Turn-Metadata-Wire`. CHANGE-098; FE-only surfacing fix; drive-through MANDATORY. (First checklist mirroring the FROZEN template `claudedocs/templates/sprint-checklist-template.md` — REFACTOR-008.)

[Plan](./sprint-57-131-plan.md)

---

## Day 0 — Plan-vs-Repo Verify (三-prong) + Branch

### 0.1 Three-prong Day-0 verify (against `main` HEAD `eef15c5e`)
- [x] **Prong 1 — path verify**: all 5 edit targets exist; `CHANGE-098` free ✅
- [x] **Prong 2 — content verify** (drift → progress.md):
  - [x] **D-agentturn-literal-sites** — `grep "role: \"agent\""` → 5 files; **4 AgentTurn LITERALS** need `model:`: turn_start (`chatStore.ts`) + `makeAgentTurn` (`ChatInspector.test.tsx`) + **`agentTurn()` (`chatStore.activeSkill.test.ts:25`)** + **`agentTurn()` (`TurnList.test.tsx:37`)**. ⚠️ DRIFT: plan File Change List missed the latter 2 test factories (+2 trivial edits; the §8 "tsc ripple" risk, caught Day-0) ✅
  - [x] **D-llm-request-model-field** — `LLMRequestEvent.data.model: string` REQUIRED (`loopEvents.generated.ts:31`); `currentModel: ev.data.model` no `?? null` → capture mirrors `tokensIn` ✅
  - [x] **D-turn-start-init** — `newAgentTurn` literal `:504-518` (`tokensIn: null` … `activeSkill`) → `model: null` slots next to `tokensIn` ✅
  - [x] **D-kv-row-placement** — order …`cost`(`:180`)/`active_skill`(`:184`)/`trace_id`/`span_id`; `KV({k,v,mono})` `:64-71` → new row after `cost`, mono ✅
  - [x] **D-render-test-impact** — `makeAgentTurn` default `model` non-null → model row shows value not "—" → `active_skill` length-1 stays; `>= 7` override +`model:null` → 8 dashes (passes) ✅
  - [x] **D-mergeEvent-llm-request-fixture** — `mergeEvent.test.ts` is event-driven (no AgentTurn literal); Day 2 locate the `llm_request`/`turn_start` fixture to mirror ✅
  - [x] **D-mockup-fidelity-zero-delta** — 57.120 active_skill row reuses `KV` + tokens; new model row reuses `KV` + `.mono` → 0 new CSS / 0 oklch ✅
  - [x] **D-drive-through-trigger** — trivial (a normal message → `llm_request` with model); Day 3 match the ChatHeader badge ✅
- [x] **Prong 3 — schema verify**: N/A (no DB table / migration / ORM) ✅
- [x] **D-baselines** — pytest 2727+5skip · wire 25 (UNCHANGED) · Vitest 908 · mockup 51 · mypy 0/372 · run_all 10/10 (re-assert at Day 2 gate) ✅
- [x] **Catalog drift** — progress.md Day-0 table (incl. the +2 test-factory drift) ✅
- [x] **Go/no-go** — FE-only surfacing; scope shift ~+2% (2 trivial test-factory `model:` edits) → proceed ✅

### 0.2 Branch
- [x] `git checkout -b feature/sprint-57-131-chatv2-inspector-model-row` (from `main` `eef15c5e`) ✅

---

## Day 1 — FE: type + store capture + Inspector row (US-1/2) ✅

### 1.1 `AgentTurn` type (US-1)
- [x] **`types.ts` (EDIT)**: `model: string | null` added after `costUsd` + WHY-comment + MHist ✅

### 1.2 Per-turn capture (US-1)
- [x] **`chatStore.ts` `turn_start` (EDIT)**: `model: null` in `newAgentTurn` literal ✅
- [x] **`chatStore.ts` `llm_request` (EDIT)**: `model: ev.data.model` added to the EXISTING `updateLastAgentTurn` updater (alongside `tokensIn`); Description case-list + MHist ✅ — build (tsc) clean
- [x] **Day-0 drift +2 factories** (D-agentturn-literal-sites): `chatStore.activeSkill.test.ts` + `TurnList.test.tsx` `agentTurn()` factories +`model: null` (required-field tsc ripple, caught Day-0) ✅

### 1.3 Inspector model row (US-2)
- [x] **`InspectorTurn.tsx` (EDIT)**: `<KV k="model" v={lastAgent.model ?? "—"} mono />` after `cost`, before `active_skill` + WHY-comment + MHist ✅

### 1.4 FE gate (partial)
- [x] `npm run build` clean (tsc — all 4 AgentTurn literals carry `model`); `npm run lint` clean; `check:mockup-fidelity` 51 byte-identical ✅

---

## Day 2 — FE tests (US-3/4) ✅

### 2.1 `mergeEvent` tests (US-3)
- [x] **`chatStore.mergeEvent.test.ts` (EDIT)**: (a) NEW `llm_request stamps the per-turn model` (null until first `llm_request` → `"claude-haiku-4-5"` after); (b) `turn_start ... null metadata` test +`expect(t.model).toBeNull()`; MHist ✅

### 2.2 Inspector render tests (US-4)
- [x] **`ChatInspector.test.tsx` (EDIT)**: `makeAgentTurn` default `model: "azure/gpt-5.2"`; populated test asserts the value; +2 NEW tests (model row set / model "—" → 2 dashes); "—" override +`model: null` + comment "8 fields nullable"; `active_skill '—' length 1` stays green; MHist ✅

### 2.3 Full gate
- [x] FE: build clean · chat_v2 Vitest 199 · full Vitest **911** (+3 new) · lint clean · mockup **51** byte-identical ✅
- [x] backend gates: **UNCHANGED — zero backend files in diff** (`git diff --stat`: only `frontend/` + `.claude/rules/sprint-workflow.md` + `CLAUDE.md`); backend exercised live in the Day-3 drive-through ✅
  - NOTE: actual +3 new tests (not +4 — the turn_start model-null assertion went into an EXISTING test, not a new one)

---

## Day 3 — Drive-through (US-5) — real UI + real backend + real LLM — **PASS** ✅

### 3.1 FE rebuild (Risk Class E — FE-only, backend UNCHANGED)
- [x] Vite :3007 HMR picked up the edits; backend bg :8000 UNCHANGED (no restart); jamie@acme.com/acme-prod, `/chat-v2`, mode `real_llm` ✅

### 3.2 Drive-through (MANDATORY — NOT gate-only) — **PASS** (real Azure gpt-5.2)
- [x] Sent "What is the capital of France? Answer in one word." → real turn (`end_turn`, tokens.in 2,435 / out 5) ✅
- [x] **THE fix (real UI)**: Inspector → Turn tab `model` row = **`gpt-5.2`** (after `cost`, before `active_skill`), NOT "—"; matches the ChatHeader badge (gpt-5.2 appears 3× in body) ✅
- [x] AP-4 walk: model row is REAL live data (not hardcoded/fixture), renders, matches badge; end-to-end (store capture + type field + KV row all live) ✅
- [x] Screenshot `.playwright-mcp/drivethrough-57131-inspector-model-row-PASS.jpeg` + observed-vs-intended → progress.md Day 3 ✅

---

## Day 4 — CHANGE-098 + closeout ✅

### 4.1 CHANGE-098
- [x] **`CHANGE-098-chatv2-inspector-model-row.md`** (gap + FE surfacing fix + drive-through PASS + AD leg closed) ✅

### 4.2 Closeout
- [x] retrospective.md Q1-Q7 + calibration (`chatv2-inspector-existing-field-surface` 0.85, **2nd data point** ratio ~0.82-0.93 IN band → KEEP 0.85) + progress.md final ✅
- [x] Final gate sweep: FE build clean · full Vitest **911** (+3) · lint clean · mockup **51** byte-identical; backend gates UNCHANGED (zero backend diff — `git diff --stat`; backend exercised live in drive-through) ✅
- [x] Navigators: CLAUDE.md Current-Sprint (PR-pending) + Last-Updated · MEMORY.md pointer + subfile · next-phase-candidates (CLOSE the `model` row leg + note HITL-Card stale-closed-by-57.108) · sprint-workflow matrix `chatv2-inspector-existing-field-surface` 2nd data point ✅
- [x] **REFACTOR-008** (interleaved per user observation): froze `claudedocs/templates/sprint-{plan,checklist}-template.md` + re-anchored the format 鐵律 (sprint-workflow.md + CLAUDE.md) relative→absolute + REFACTOR-008 record + normalized 57.131 plan/checklist ✅
- [x] Anti-pattern self-check (retro Q5): AP-2/3/4/6/8/11 → 0 violations (REMOVES an AP-4 missing-metadata gap); FE lint clean, backend lints UNCHANGED ✅
- [ ] **Commit** → ⏳ PR push + open → CI → merge: PENDING USER CONFIRMATION (push is outward-facing per Developer Preferences) → post-merge status flip after gh-verified MERGED
