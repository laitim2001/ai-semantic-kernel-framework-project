# Sprint 57.131 Progress — chat-v2 Inspector Turn tab `model` row

**Slice**: closes the `model` row leg of `AD-ChatV2-Inspector-Turn-Metadata-Wire` (57.120 carryover).
**Branch**: `feature/sprint-57-131-chatv2-inspector-model-row` (from `main` `eef15c5e`).
**Plan**: [sprint-57-131-plan.md](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-131-plan.md) · **Checklist**: [sprint-57-131-checklist.md](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-131-checklist.md)

---

## Day 0 — Plan-vs-Repo Verify (三-prong) — YYYY-MM-DD (2026-06-16)

### Prong 1 — Path verify ✅
- All 5 planned edit targets exist: `types.ts` / `chatStore.ts` / `InspectorTurn.tsx` / `chatStore.mergeEvent.test.ts` / `ChatInspector.test.tsx`.
- `CHANGE-098-chatv2-inspector-model-row.md` free (Glob: no files).

### Prong 2 — Content verify (drift findings)

| ID | Finding | Implication |
|----|---------|-------------|
| **D-llm-request-model-field** ✅ | Generated `LLMRequestEvent.data.model: string` (REQUIRED, `loopEvents.generated.ts:31`); `chatStore.ts:547 currentModel: ev.data.model` (no `?? null`) confirms. | `ev.data.model` is `string`; the per-turn `AgentTurn.model` is `string \| null` only because it's null BEFORE the turn's first `llm_request`. Capture mirrors `tokensIn` in the same `llm_request` updater (`:548-551`). |
| **D-agentturn-literal-sites** ⚠️ DRIFT | `grep "role: \"agent\""` → 5 files. **4 are AgentTurn LITERALS** needing the required `model:` field; `types.ts` is the type def (discriminant, not a literal); `mergeEvent.test.ts` has NONE (event-driven). | **Plan File Change List missed 2 test files.** Literal sites: (1) `chatStore.ts` turn_start `newAgentTurn` → `model: null`; (2) `ChatInspector.test.tsx` `makeAgentTurn` → `model: "azure/gpt-5.2"`; (3) **`chatStore.activeSkill.test.ts` `agentTurn()` factory (`:25-38`)** → `model: null` (NEW — not in plan); (4) **`TurnList.test.tsx` `agentTurn()` factory (`:37-50`)** → `model: null` (NEW — not in plan). Both adds are trivial 1-line factory edits. This is exactly the plan §8 "required `model` field tsc ripple" risk — caught at Day-0 as designed. |
| **D-turn-start-init** ✅ | `turn_start` `newAgentTurn` literal (`chatStore.ts:504-518`) lists `tokensIn: null` … `activeSkill: triggerSkill`. | Add `model: null` next to `tokensIn: null`. |
| **D-kv-row-placement** ✅ | `InspectorTurn.tsx` KV order: …`cost` (`:180`) / `active_skill` (`:184`) / `trace_id` (`:185`) / `span_id` (`:186`); `KV({k, v, mono})` helper (`:64-71`). | New row goes after `cost`, before `active_skill`; `mono` (technical id, like `trace_id`). |
| **D-render-test-impact** ✅ | `ChatInspector.test.tsx`: `active_skill '—' length 1` (`:132`) requires the default populated turn to have only ONE "—" (active_skill); `>= 7` dash test (`:114`). | `makeAgentTurn` default `model: "azure/gpt-5.2"` (non-null) → model row shows a value, NOT "—" → length-1 stays correct. The `>= 7` override adds `model: null` → 8 dashes (still `>= 7`). |
| **D-mergeEvent-llm-request-fixture** ⏳ | `chatStore.mergeEvent.test.ts` drives the reducer with event fixtures (no AgentTurn literal). | Day 2: locate the existing `llm_request`/`turn_start` fixture to mirror for the model-capture + turn_start-null assertions. |
| **D-mockup-fidelity-zero-delta** ✅ | The 57.120 `active_skill` row (`InspectorTurn.tsx:184`) reuses `KV` + tokens — 0 new CSS. | New `model` row reuses `KV` + `.mono` → `diff styles-mockup.css` empty; `HEX_OKLCH_BASELINE` 51 unchanged. |
| **D-drive-through-trigger** ✅ | Trivial — a normal chat message produces an `llm_request` with a `model`. | Day 3: send a normal message; the model row must match the ChatHeader badge (`currentModel`). |

### Prong 3 — Schema verify
- N/A (no DB table / migration / ORM — FE-only).

### Baselines (to re-assert at Day 2 gate)
- pytest 2727+5skip · wire 25 (UNCHANGED — no backend touch) · Vitest 908 · mockup 51 · mypy 0/372 · run_all 10/10.

### Go/no-go
- FE-only surfacing fix. Scope shift = +2 trivial test-factory `model:` edits (D-agentturn-literal-sites). ~+2% → **proceed**. Updated File Change List in retro/CHANGE to include `chatStore.activeSkill.test.ts` + `TurnList.test.tsx`.

### 0.2 Branch ✅
- `git checkout -b feature/sprint-57-131-chatv2-inspector-model-row` (from `main` `eef15c5e`).

---

## Day 1 — FE: type + store capture + Inspector row (US-1/2) — 2026-06-16/17

- **`types.ts`**: `AgentTurn += model: string | null` (after `costUsd`; WHY-comment + MHist). Required `T | null` — matches the Inspector-metadata convention.
- **`chatStore.ts`**: `turn_start` `newAgentTurn` += `model: null`; `llm_request` case += `model: ev.data.model` in the EXISTING `updateLastAgentTurn` updater (alongside `tokensIn`) — captures at the correct moment (turn_start fires before llm_request). Description case-list (`llm_request → … tokensIn + model`) + MHist.
- **`InspectorTurn.tsx`**: `<KV k="model" v={lastAgent.model ?? "—"} mono />` after `cost`, before `active_skill`. Reuses `KV` + `.mono` → 0 new CSS.
- **Day-0 drift resolved** (D-agentturn-literal-sites): the required `model` field forced `model: null` into 2 MORE test factories the plan missed — `chatStore.activeSkill.test.ts` `agentTurn()` + `TurnList.test.tsx` `agentTurn()`. tsc (`npm run build`) confirmed all 4 literals carry `model` (build clean).
- Gate (partial): build clean · lint clean · `check:mockup-fidelity` 51 byte-identical.

## Day 2 — FE tests (US-3/4) — 2026-06-17

- **`chatStore.mergeEvent.test.ts`**: +1 NEW test `llm_request stamps the per-turn model` (asserts `model` null until the first `llm_request`, then `"claude-haiku-4-5"` from the `llmRequest` fixture); the existing `turn_start ... null metadata` test += `expect(t.model).toBeNull()`. MHist.
- **`ChatInspector.test.tsx`**: `makeAgentTurn` default += `model: "azure/gpt-5.2"`; populated test += model-value assertion; +2 NEW tests (model row renders the value / model "—" → 2 dashes [model + active_skill]); "—" placeholder override += `model: null` (comment → "8 fields nullable"); `active_skill '—' length 1` stays green (default model non-null). MHist.
- **Gate**: FE build clean · chat_v2 Vitest 199 passed · full Vitest **911 passed** (baseline 908 → +3; the turn_start assertion went into an existing test, hence +3 not +4) · lint clean · mockup **51** byte-identical.
- **Backend gates UNCHANGED**: `git diff --stat` shows zero backend files (only `frontend/` + `.claude/rules/sprint-workflow.md` + `CLAUDE.md`). Backend will be exercised live in the Day-3 drive-through. (NOT a skip — zero-diff inference; faithful: did NOT run/claim 2727 pytest, the change cannot reach backend.)
- **Format meta-work** (REFACTOR-008, interleaved this sprint per user request): froze `claudedocs/templates/sprint-{plan,checklist}-template.md`, re-anchored the format 鐵律 (sprint-workflow.md + CLAUDE.md) from "mirror most-recent sprint" → "mirror frozen template", normalized 57.131 plan/checklist (short H1 + Summary). Zero code impact.

## Day 3 — Drive-through (US-5) — real UI + real backend + real LLM — **PASS** — 2026-06-17

- **Setup**: FE-only sprint → Vite :3007 (HMR picked up the edits) + the running backend bg on :8000 (UNCHANGED) + real Azure. Logged in jamie@acme.com / acme-prod; `/chat-v2`, mode `real_llm`. (No backend restart needed — Risk Class E N/A for FE-only.)
- **Trigger**: sent "What is the capital of France? Answer in one word." → a real turn ran (`stop_reason = end_turn`, tokens.in 2,435 / out 5).
- **THE fix (real UI, Inspector → Turn tab)** — read via `browser_evaluate` of the `inspector-turn` KV rows:
  ```
  stop_reason = end_turn
  duration    = —
  tokens.in   = 2,435
  tokens.out  = 5
  tokens.thinking = —
  cost        = —
  model       = gpt-5.2     ← THE FIX (new row, after cost / before active_skill)
  active_skill = —
  trace_id    = 2ee888ea38f541bc942419097f8de0bd
  span_id     = 43fecd5c0814eb85
  ```
- **Observed vs intended**: intended = a `model` row showing the ACTUAL model, matching the ChatHeader badge, not "—". Observed = `model = gpt-5.2` (real Azure), and `gpt-5.2` appears 3× in the page body (the ChatHeader `currentModel` badge + the new Inspector row + the session meta) → **consistent**. ✅
- **AP-4 walk**: the model row is REAL live data (`gpt-5.2` from the turn's `llm_request`), NOT a hardcoded label / fixture; it renders; it matches the badge. End-to-end proof — the render requires the store per-turn capture + the `AgentTurn.model` field + the new KV row all live. No Potemkin.
- **Screenshot**: `.playwright-mcp/drivethrough-57131-inspector-model-row-PASS.jpeg`.
- **Verdict**: **drive-through PASS** (NOT gate-only).

## Day 4 — CHANGE-098 + closeout

_(in progress)_
