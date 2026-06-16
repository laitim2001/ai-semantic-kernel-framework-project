# CHANGE-098: chat-v2 Inspector Turn tab `model` row

**Date**: 2026-06-17
**Sprint**: 57.131
**Scope**: Frontend / chat_v2 (範疇 12 Observability surface; FE-only — no backend/wire/codegen/migration)

## Problem

The chat-v2 Inspector "Turn" tab showed 9 per-turn metadata KV rows (stop_reason / duration / tokens.in/out/thinking / cost / active_skill / trace_id / span_id) but NOT the LLM **model** that ran the turn. The model name was already store-captured (`chatStore.currentModel` from each `llm_request.model`, drives the ChatHeader badge — CHANGE-054) but only as a single session-latest value, not stamped per-turn, so the Inspector (which renders the most-recent `AgentTurn`'s metadata) had nothing per-turn to show. An operator inspecting a turn could not see which model produced it — significant in a multi-model session (e.g. cheap-tier compaction + strong-tier answer, the 57.97/57.109 model-policy work).

This closes the **`model` row leg** of `AD-ChatV2-Inspector-Turn-Metadata-Wire` (57.120 carryover; the Inspector-panel active_skill leg shipped 57.120, the user-turn chip leg shipped 57.116). The token-sweep leg (🟢) + the cost-in-stream carve-out remain separate, still-open legs.

## Root Cause

The `llm_request` `mergeEvent` case set `currentModel` (session-level) + the active turn's `tokensIn`, but never stamped a per-turn `model` onto the `AgentTurn`, and `AgentTurn` had no `model` field. `turn_start` (which builds the `AgentTurn`) fires BEFORE the turn's `llm_request`, so the model isn't known at turn-construction time — it must be captured at `llm_request`.

## Solution

Pure-frontend, mirroring the 57.120 `active_skill` row recipe:

- **`types.ts`**: `AgentTurn += model: string | null` (required `T | null`, matching the sibling Inspector-metadata convention; null until the turn's first `llm_request`).
- **`chatStore.ts`**: `turn_start` `newAgentTurn` += `model: null`; the EXISTING `llm_request` case's `updateLastAgentTurn` updater += `model: ev.data.model` (captured at the correct moment, alongside `tokensIn`; a multi-call turn keeps the latest, like `tokensIn`/`currentModel`). Description case-list + MHist.
- **`InspectorTurn.tsx`**: one more `<KV k="model" v={lastAgent.model ?? "—"} mono />` row, after `cost`, before `active_skill`. Reuses the `KV` helper + `.mono` → **0 new CSS class / `styles-mockup.css` edit / `oklch(`/`#hex` literal** (`HEX_OKLCH_BASELINE` 51 unchanged, mockup byte-identical).
- **NO backend / wire / codegen / migration** — `llm_request.model` already exists on the wire (generated `LLMRequestEvent.data.model: string`); wire stays 25; `loopEvents.generated.ts` untouched.

**Day-0 drift caught** (D-agentturn-literal-sites): the required `model` field forced `model: null` into 2 test factories the plan's File Change List missed (`chatStore.activeSkill.test.ts` + `TurnList.test.tsx` `agentTurn()`); tsc (`npm run build`) confirmed all 4 `AgentTurn` literals carry the field.

## Verification

- **Gates**: FE build clean (tsc — all 4 AgentTurn literals carry `model`) · chat_v2 Vitest 199 · full Vitest **911** (baseline 908 → +3: 1 new `mergeEvent` test + 2 new `ChatInspector` tests; the `turn_start` model-null assertion went into an existing test) · lint clean · mockup **51** byte-identical. Backend gates UNCHANGED (zero backend files in `git diff --stat`).
- **Tests added**: `chatStore.mergeEvent.test.ts` — `llm_request stamps the per-turn model` (null until first `llm_request` → `"claude-haiku-4-5"`) + `turn_start … null metadata` += `model` null assertion. `ChatInspector.test.tsx` — model row renders the value / model "—" → 2 dashes; `makeAgentTurn` default += `model`.
- **Drive-through PASS** (real UI + real backend + real Azure, jamie@acme.com/acme-prod): sent a real message → Inspector Turn tab `model` row = **`gpt-5.2`** (after `cost`, before `active_skill`), not "—", matching the ChatHeader badge (gpt-5.2 appears 3× in the page body). Screenshot `.playwright-mcp/drivethrough-57131-inspector-model-row-PASS.jpeg`. End-to-end: the render requires the store per-turn capture + the `AgentTurn.model` field + the new KV row all live. (NOT gate-only.)

## Impact

- Frontend-only; `chat_v2` Inspector surface. Zero backend / wire / DB impact.
- Completes the per-turn model attribution metadata; the Inspector Turn tab now pairs `model` with `trace_id` / `tokens` / `cost` for per-turn debugging.
- `AD-ChatV2-Inspector-Turn-Metadata-Wire` `model` row leg CLOSED; token-sweep + cost-in-stream legs remain open.

## Related

- Sprint 57.120 (`active_skill` row leg — the precedent recipe) · 57.116 (user-turn chip leg) · CHANGE-054 (`currentModel` capture).
- Plan: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-131-plan.md`
- (Sprint-adjacent process work: REFACTOR-008 froze the sprint plan/checklist template — separate from this feature.)
