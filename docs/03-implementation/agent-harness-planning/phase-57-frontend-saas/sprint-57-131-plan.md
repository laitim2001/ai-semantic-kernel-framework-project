# Sprint 57.131 Plan — chat-v2 Inspector Turn tab `model` row

**Summary**: Surface the per-turn LLM model in the chat-v2 Inspector "Turn" tab — one more `model` KV row alongside `trace_id` / `tokens`. Closes the **`model` row leg** of `AD-ChatV2-Inspector-Turn-Metadata-Wire` (57.120 carryover): the model name is already store-captured (`chatStore.currentModel` from `llm_request.model`, drives the ChatHeader badge) but only session-latest, not stamped per-turn, so the Inspector can't show it. **Pure-frontend thin slice** (mirrors the 57.120 `active_skill` row): `AgentTurn += model: string \| null`, capture `ev.data.model` onto the active turn in the EXISTING `llm_request` `mergeEvent` case (alongside `tokensIn`), render one `<KV k="model" …/>` row. **NO backend / wire / codegen / migration** (the `llm_request` event already carries `model` — wire stays 25); **NO new CSS class / mockup authoring / `oklch(`/`#hex` literal** (reuses the `KV` helper — `styles-mockup.css` byte-identical, `HEX_OKLCH_BASELINE` 51 unchanged). **Drive-through MANDATORY** — send a message, open Inspector → Turn tab, confirm the `model` row shows the ACTUAL model (matching the ChatHeader badge), not "—". CHANGE-098; FE surfacing fix (NOT a spike), so NO design note. (Format: this plan is the first to mirror the FROZEN canonical template `claudedocs/templates/sprint-plan-template.md` — REFACTOR-008.)

**Status**: Approved-to-execute (user 2026-06-16: "繼續做 bucket C 的下一條" → AskUserQuestion picked **Inspector model row (57.120)**). Read-only recon mapped the store capture point + the Inspector render + the test fixtures with file:line anchors (the Day-0 三-prong head-start; re-verified in §checklist 0.1).
**Branch**: `feature/sprint-57-131-chatv2-inspector-model-row`
**Base**: `main` HEAD `eef15c5e` (post-#308 — the 57.130 PR-pending→MERGED status flip).
**Slice**: closes the **`model` row leg** of `AD-ChatV2-Inspector-Turn-Metadata-Wire` (carried from 57.120; the Inspector-PANEL active_skill leg shipped 57.120, the user-turn chip leg shipped 57.116). The token-sweep leg (🟢) + the cost-in-stream carve-out remain separate, still-open legs. A standalone FE surfacing fix (no arc).
**Scope decisions**: (a) **Capture `model` PER-TURN at `llm_request`, not `turn_start`** — `turn_start` fires BEFORE the turn's `llm_request` (the order is `turn_start` → `llm_request`), so the model for the turn isn't known at `turn_start`. Capture it in the EXISTING `llm_request` case (which already sets `currentModel` + the turn's `tokensIn`) — add `model: ev.data.model` to the same `updateLastAgentTurn` updater. `turn_start` initializes `model: null`. (b) **`model: string | null` REQUIRED on `AgentTurn`** (NOT optional) — matches the sibling Inspector-metadata convention (`traceId`/`spanId`/`tokensIn`/`tokensOut`/`costUsd` are all required `T | null`, null-until-the-source-event, "—" placeholder at render). The 57.120 `activeSkill?` is optional because a skill is force-loaded only conditionally (undefined = no skill, a distinct semantic); `model` is ALWAYS present once `llm_request` fires → the required `T | null` pattern is the right match. The required field surfaces every `AgentTurn` literal via tsc (turn_start + test fixtures) — Day-0 Prong-1 grep `role: "agent"` enumerates them so each gets `model:`. (c) **One `<KV>` row** — reuse the existing `KV` helper + `.mono` class (like `trace_id`); placed right after `cost` (groups with the LLM-call metrics) and before `active_skill`. NO new CSS class / `styles-mockup.css` edit / mockup authoring / `oklch(`/`#hex` literal. (d) **NO backend / wire / codegen** — `llm_request.model` already exists on the wire (`event_wire_schema.py`; `chatStore.ts:547 currentModel: ev.data.model` proves the generated `LLMRequestEvent.data.model` field). Wire stays 25; `loopEvents.generated.ts` UNTOUCHED. (e) User-facing surface change → a real UI + real backend + real LLM **drive-through is MANDATORY** (open the Inspector Turn tab, confirm the model row shows the real model). (f) Mirror the 57.120 `active_skill` row precedent for the render + the test shape.

---

## 0. Background

### The gap (the 57.120 carryover `AD-ChatV2-Inspector-Turn-Metadata-Wire` — `model` row leg)

The chat-v2 Inspector "Turn" tab (`InspectorTurn.tsx`) renders the most-recent `AgentTurn`'s metadata as a set of KV rows. After 57.120 it shows 9 rows: `stop_reason` / `duration` / `tokens.in` / `tokens.out` / `tokens.thinking` / `cost` / `active_skill` / `trace_id` / `span_id`. It does NOT show the **model** that produced the turn. The model name is captured in the store (`currentModel`, set from each `llm_request.model` — it drives the ChatHeader model badge, CHANGE-054), but `currentModel` is a single session-latest value, not stamped onto each `AgentTurn`. The Inspector renders per-turn metadata, so it has no per-turn model to show. A developer/operator inspecting a turn cannot see which model ran it from the Inspector — they must read the ChatHeader badge (session-latest only) and infer.

### Why it matters (the missing capability)

The Inspector Turn tab is the per-turn debugging surface — it pairs the model identity with the trace_id / tokens / cost so an operator can attribute cost + latency + behaviour to a specific model on a specific turn. In a multi-model session (e.g. a cheap-tier compaction call + a strong-tier answer, per the 57.97/57.109 model-policy work), the session-latest `currentModel` badge is insufficient — only a per-turn model row tells you which turn ran which model. Surfacing it completes the per-turn attribution metadata.

### Root cause (recon code read, file:line; ALL re-verified §checklist 0.1)

| Layer | Reality (on `main` HEAD `eef15c5e`) | Anchor |
|-------|-------------------------------------|--------|
| `model` IS captured at the store level | `case "llm_request": return {..., currentModel: ev.data.model, turns: updateLastAgentTurn(s.turns, t => ({...t, tokensIn: ev.data.tokens_in}))}` | `chatStore.ts:543-553` |
| …but NOT stamped per-turn | the `updateLastAgentTurn` updater sets `tokensIn` only — no `model` field on `AgentTurn` | `chatStore.ts:548-551` |
| `llm_request.model` is on the wire (a `string`) | `currentModel: ev.data.model` (no `?? null`) → the generated `LLMRequestEvent.data.model` is a required `string` | `chatStore.ts:547` + `event_wire_schema.py` (`llm_request` entry) |
| `turn_start` builds the `AgentTurn` (no `model` yet) | `newAgentTurn` literal: `tokensIn: null` … `activeSkill: triggerSkill` — fires BEFORE `llm_request` | `chatStore.ts:485-519` |
| The Inspector renders per-turn metadata KV rows | `InspectorTurn` picks the most-recent `AgentTurn`; 9 `<KV>` rows; `active_skill` is the 57.120 precedent | `InspectorTurn.tsx:120-186` |
| The `KV` helper (reused for the new row) | `function KV({k, v, mono}) → <div className="spread"><span className="subtle">{k}</span><span className={mono ? "mono tnum" : undefined}>{v}</span></div>` | `InspectorTurn.tsx:64-71` |
| `AgentTurn` type (add `model` here) | required `T \| null` metadata fields (`tokensIn` … `costUsd` / `traceId` / `spanId`) + optional `activeSkill?` (57.120) + optional `terminated?` (57.130) | `types.ts:158-182` |
| Render test fixture (needs `model`) | `makeAgentTurn()` returns a full `AgentTurn` literal (no `model`) → a required `model` field forces adding it here | `ChatInspector.test.tsx:39-67` |
| The "—" placeholder + active_skill-length-1 tests | `>= 7` dashes (line 114) + `active_skill` is the only "—" in the default populated turn → `toHaveLength(1)` (line 132) | `ChatInspector.test.tsx:97-133` |
| Wire registry (UNTOUCHED — no new event/field) | `WIRE_SCHEMA` 25 entries (57.130 `loop_terminated`); `llm_request.model` already present | `event_wire_schema.py` |

→ The fix is FE-only: (1) add `model: string | null` to `AgentTurn`, (2) capture `ev.data.model` onto the active turn in the EXISTING `llm_request` case (init `model: null` at `turn_start`), (3) render one more `<KV k="model" v={lastAgent.model ?? "—"} mono />` row in `InspectorTurn`, (4) update the test fixtures (`makeAgentTurn` default + the null-placeholder override) + add explicit model-row tests + a `mergeEvent` capture test.

### The design (FE-only: 1 type field + 1 store capture line + 1 turn_start init + 1 KV row + tests)

```
# FRONTEND — types.ts AgentTurn (add the required per-turn metadata field, next to costUsd)
model: string | null;   // the LLM model that ran this turn (from llm_request.model); null until the turn's first llm_request

# FRONTEND — chatStore.ts turn_start (init in the newAgentTurn literal)
model: null,

# FRONTEND — chatStore.ts llm_request (capture onto the active turn, alongside the existing tokensIn)
turns: updateLastAgentTurn(s.turns, (t) => ({ ...t, tokensIn: ev.data.tokens_in, model: ev.data.model })),

# FRONTEND — InspectorTurn.tsx (one more KV row, after `cost`, before `active_skill`)
<KV k="model" v={lastAgent.model ?? "—"} mono />
```

**Why minimal (no new CSS / wire)**: the model is already on the wire + already store-captured; the only gap is a per-turn stamp + a render row. Reusing the `KV` helper + `.mono` class keeps `styles-mockup.css` byte-identical (mockup 51 unchanged), adds zero `oklch(`/`#hex` literals (`HEX_OKLCH_BASELINE` 51 unchanged), and authors no new mockup element — exactly the 57.120 `active_skill` row recipe.

**Why per-turn capture at `llm_request` (not `turn_start`)**: `turn_start` pushes the new `AgentTurn` BEFORE the turn's `llm_request` fires, so the model isn't known yet at `turn_start`. The `llm_request` case already updates the same turn's `tokensIn` — adding `model: ev.data.model` to that same updater stamps the per-turn model at the correct moment, with zero new traversal. A multi-call turn (>1 `llm_request`) keeps the LATEST model (each call overwrites — consistent with `tokensIn` / `currentModel` semantics).

### Ground truth (recon head-start — code read on `main` HEAD `eef15c5e`; ALL re-verified §checklist 0.1)

- `frontend/src/features/chat_v2/store/chatStore.ts:543-553` — the `llm_request` case (add `model: ev.data.model` to the `updateLastAgentTurn` updater; `currentModel` already proves `ev.data.model` exists).
- `frontend/src/features/chat_v2/store/chatStore.ts:485-519` — the `turn_start` case (`newAgentTurn` literal — add `model: null`).
- `frontend/src/features/chat_v2/types.ts:158-182` — the `AgentTurn` type (add `model: string | null` near `costUsd`).
- `frontend/src/features/chat_v2/components/inspector/InspectorTurn.tsx:120-186` — `InspectorTurn` (add the `<KV k="model" .../>` row after `cost` line 180) + the `KV` helper (`:64-71`) + the 57.120 `active_skill` row (`:181-184`, the precedent).
- `frontend/tests/unit/chat_v2/components/inspector/ChatInspector.test.tsx:39-67` — `makeAgentTurn` (add `model:` to the default) + `:83-133` (the populated / "—" / active_skill-length tests to update) + add explicit model-row tests.
- `frontend/tests/unit/chat_v2/chatStore.mergeEvent.test.ts` — the merge-reducer harness (add: `llm_request` stamps the turn's `model`; `turn_start` inits `model: null`). Day-0 locate the existing `llm_request` fixture/case.
- `frontend/scripts/check-mockup-fidelity.mjs` — `HEX_OKLCH_BASELINE = 51` (must stay 51 — no new literal).
- Wire/backend UNTOUCHED: `event_wire_schema.py` 25 · `loopEvents.generated.ts` (codegen output) · `sse.py` · no migration.

**Baselines (57.130 closeout + #307/#308)**: full pytest **2727+5skip** · wire **25** (UNCHANGED this sprint) · Vitest **908** · mockup **51** · mypy `src` **0/372** · run_all **10/10**. Re-verify Day-0. (The intermittent `AD-Billing-Outbox-Drain-Test-Flake` Risk Class C billing flake — pre-existing, untouched — may surface once; re-run confirms. Backend gates UNCHANGED this sprint — FE-only — but re-run to confirm no incidental break.)

### STALE / drift findings (Day-0; full detail → progress.md — placeholder, filled in §checklist 0.1)

- **D-agentturn-literal-sites** — grep `role: "agent"` across `frontend/src` + `frontend/tests`: enumerate EVERY `AgentTurn` object literal (a required `model` field must be added to each, else tsc fails). Expected: `chatStore.ts` turn_start (`:504`) + `ChatInspector.test.tsx` `makeAgentTurn` (`:39`) + any in `chatStore.mergeEvent.test.ts` / `chatStore.activeSkill.test.ts` / `chatStore.historyReplay.test.ts` / `chatStore.pauseResume.test.ts`. Resolve the count BEFORE editing the type.
- **D-llm-request-model-field** — confirm the generated `LLMRequestEvent.data.model` is a required `string` (re-grep `currentModel: ev.data.model` + read the generated `LLMRequestEvent`); confirm the `llm_request` case's exact `updateLastAgentTurn` shape so the `model` add mirrors `tokensIn`.
- **D-turn-start-init** — confirm the `turn_start` `newAgentTurn` literal fields so the `model: null` init slots in cleanly (alongside `tokensIn: null`).
- **D-kv-row-placement** — confirm the `InspectorTurn` KV row order + the `KV` helper signature so the new row reuses it (mono for a technical identifier, like `trace_id`).
- **D-render-test-impact** — confirm the `ChatInspector.test.tsx` `active_skill '—' length 1` test (line 132) stays correct IFF `makeAgentTurn` default `model` is non-null (so model shows a value, not "—") + the `>= 7` dash test (line 114) tolerates the new nullable row (→ 8 when overridden null).
- **D-mergeEvent-llm-request-fixture** — locate the existing `llm_request` test in `chatStore.mergeEvent.test.ts` to mirror for the new model-capture assertion.
- **D-mockup-fidelity-zero-delta** — confirm the new KV row reuses `var(--*)` tokens + `.mono` with NO new CSS class / NO `styles-mockup.css` edit / NO new `oklch(`/`#hex` (HEX_OKLCH_BASELINE 51 stays).
- **D-drive-through-trigger** — the trigger is trivial (a normal chat message produces an `llm_request` with a model) — confirm the real model string the backend reports (e.g. the Azure deployment) so the drive-through assertion matches the ChatHeader badge.
- **D-baselines** — re-assert the 6 gate baselines (wire 25 UNCHANGED this sprint; FE-only).

## 1. Sprint Goal

Close the **`model` row leg** of `AD-ChatV2-Inspector-Turn-Metadata-Wire`: the chat-v2 Inspector "Turn" tab now shows a per-turn `model` KV row (the LLM model that ran the turn), alongside the existing `trace_id` / `tokens` / `cost` rows. Frontend-only — add a required `model: string | null` field to `AgentTurn`; capture `ev.data.model` onto the active turn in the EXISTING `llm_request` `mergeEvent` case (alongside `tokensIn`); initialize `model: null` in the `turn_start` `newAgentTurn` literal; render one more `<KV k="model" v={lastAgent.model ?? "—"} mono />` row in `InspectorTurn` (reusing the `KV` helper — NO new CSS class, NO mockup authoring, NO new `oklch(`/`#hex` literal). NO backend / wire / codegen / migration change (the `llm_request` event already carries `model`; wire stays 25; `loopEvents.generated.ts` untouched). Proven by FE Vitest cases (`mergeEvent` stamps the per-turn model + inits null at turn_start; `InspectorTurn` renders the model row populated + "—" when null) **and a MANDATORY real UI + real backend + real LLM drive-through** (send a message, open Inspector → Turn tab, confirm the model row shows the ACTUAL model that ran, matching the ChatHeader badge, instead of "—"). `styles-mockup.css` byte-identical (mockup 51 unchanged); `HEX_OKLCH_BASELINE` 51 unchanged. CHANGE-098; FE surfacing fix (NO design note).

## 2. User Stories

- **US-1** (type + per-turn capture): 作為 chat-v2 store，我希望 `AgentTurn` 新增 required `model: string | null` 欄位、`turn_start` 初始化 `model: null`、`llm_request` case 在既有的 `updateLastAgentTurn` updater 內 stamp `model: ev.data.model`（與 `tokensIn` 並列），以便每個 turn 記錄產生它的 LLM model（multi-call turn 取最新）。
- **US-2** (Inspector render): 作為 chat-v2 Inspector Turn tab，我希望在 `cost` row 之後、`active_skill` row 之前新增一個 `<KV k="model" v={lastAgent.model ?? "—"} mono />` row（復用既有 `KV` helper + `.mono`），以便操作者能在每個 turn 看到跑它的 model（null 時顯示「—」）。無新 CSS class / mockup 編輯 / oklch/#hex literal。
- **US-3** (tests — store): frontend `chatStore.mergeEvent.test.ts` — (a) `llm_request` 把 active turn 的 `model` 設為 `ev.data.model`；(b) `turn_start` 初始化 `model: null`（在第一個 `llm_request` 之前）。
- **US-4** (tests — render): frontend `ChatInspector.test.tsx` — `makeAgentTurn` default 加非-null `model`；(a) populated turn 顯示該 model 值；(b) `model: null` override 顯示「—」；既有 `active_skill '—' length 1` + `>= 7` dash 測試仍綠（更新 comment/count）。
- **US-5** (drive-through — MANDATORY): 真 UI + 真後端 + 真 Azure — 送一則訊息 → 開 Inspector → Turn tab → 確認 `model` row 顯示實際跑的 model（與 ChatHeader badge 一致），而非「—」；逐控件 AP-4 walk + 截圖 + 實際-vs-預期 → progress.md。
- **US-6** (closeout): CHANGE-098 + 收尾（retro + calibration + navigators + **CLOSE the `model` row leg of `AD-ChatV2-Inspector-Turn-Metadata-Wire`**）；FE surfacing fix → NO design note。

## 3. Technical Specifications

### 3.0 Architecture (frontend: 1 type field + 1 store capture + 1 turn_start init + 1 KV row + tests; NO backend / wire / codegen / CSS / migration)

```
# FRONTEND (EDIT)
frontend/src/features/chat_v2/types.ts                 (EDIT): AgentTurn += model: string | null
frontend/src/features/chat_v2/store/chatStore.ts       (EDIT): turn_start init model:null; llm_request capture model
frontend/src/features/chat_v2/components/inspector/InspectorTurn.tsx  (EDIT): + <KV k="model" .../> row
frontend/tests/unit/chat_v2/chatStore.mergeEvent.test.ts  (EDIT): model-capture + turn_start-init cases
frontend/tests/unit/chat_v2/components/inspector/ChatInspector.test.tsx  (EDIT): makeAgentTurn +model; model-row tests
# docs
claudedocs/4-changes/feature-changes/CHANGE-098-chatv2-inspector-model-row.md  (NEW)
# UNTOUCHED: event_wire_schema.py (llm_request.model already on wire; 25 unchanged) · loopEvents.generated.ts (codegen) ·
#            sse.py · router.py · styles-mockup.css (byte-identical) · reference/design-mockups/** · no migration · no new CSS class
```

### 3.1 `AgentTurn` type + per-turn capture (US-1) — `types.ts` + `chatStore.ts`

- `types.ts`: add `model: string | null;` to `AgentTurn` (place near `costUsd` / `traceId` — the LLM-call metadata group) + a WHY-comment ("the LLM model that ran this turn, from `llm_request.model`; null until the turn's first `llm_request`"). REQUIRED (not optional) — matches the sibling `T | null` metadata convention; tsc surfaces every `AgentTurn` literal (each gets `model:`).
- `chatStore.ts` `turn_start`: add `model: null` to the `newAgentTurn` literal (alongside `tokensIn: null`).
- `chatStore.ts` `llm_request`: add `model: ev.data.model` to the EXISTING `updateLastAgentTurn` updater (alongside `tokensIn: ev.data.tokens_in`). A multi-`llm_request` turn keeps the latest model (overwrite — same as `tokensIn` / `currentModel`).
- Add a 1-line MHist to both files.

### 3.2 Inspector model row (US-2) — `InspectorTurn.tsx`

- Add `<KV k="model" v={lastAgent.model ?? "—"} mono />` after the `cost` row (`:180`) and before the `active_skill` row (`:184`) — groups with the LLM-call metrics. Reuse the `KV` helper with `mono` (a technical identifier, like `trace_id`/`span_id`). A WHY-comment mirroring the 57.120 `active_skill` comment ("the LLM model that ran this turn, captured at `llm_request`; '—' until the first call; reuses the `KV` helper — no new mockup CSS").
- Update the file MHist (1-line).
- NO new CSS class / `styles-mockup.css` edit / `oklch(`/`#hex` literal.

### 3.3 Tests (US-3/4)

- **`chatStore.mergeEvent.test.ts`** (EDIT): mirror the existing `llm_request` test (Day-0 D-mergeEvent-llm-request-fixture locates it) — add: (a) after `turn_start` → `llm_request{model:"azure/gpt-5.2", tokens_in: N}`, the active `AgentTurn.model === "azure/gpt-5.2"` (and `currentModel` still set); (b) after `turn_start` alone (no `llm_request` yet), the active turn's `model === null`.
- **`ChatInspector.test.tsx`** (EDIT): `makeAgentTurn` default gets `model: "azure/gpt-5.2"` (non-null). (a) the "populated" test (`:83-95`) adds `expect(screen.getByText("azure/gpt-5.2")).toBeInTheDocument()`; (b) a NEW test: `makeAgentTurn({ model: null })` → the model row shows "—" (mirror the active_skill "—" test); (c) the "—" placeholder test (`:97-115`) override adds `model: null` → bump the comment to "8 fields nullable" (the `>= 7` assertion still passes); (d) the `active_skill '—' length 1` test (`:127-133`) stays correct because the default `model` is non-null (model shows a value, not "—") — verify, no change needed.

### 3.4 Drive-through (US-5) — real UI + real backend + real LLM (MANDATORY)

1. Clean restart only if needed (Risk Class E — this sprint is FE-only; the backend is UNCHANGED, so the running bg backend on :8000 is fine; rebuild/refresh the FE so Vite picks up the type + store + Inspector edits). Vite :3007 (node) NOT stopped.
2. Open `/chat-v2`, send a normal message (real Azure) so the loop runs a turn with a real `llm_request`.
3. **The fix**: open the Inspector → **Turn** tab; confirm the new `model` KV row shows the ACTUAL model string the backend reported (e.g. the Azure deployment / `gpt-5.2`), and that it MATCHES the ChatHeader model badge (`currentModel`). Before the message (no turn) → the Inspector empty state; mid/after a turn → the model row is populated (not "—").
4. Per-control AP-4 walk (the model row is real data, not a hardcoded label); screenshot (Inspector Turn tab showing the model row) + observed-vs-intended → progress.md. "drive-through PASS" only if the Inspector model row actually shows the real model (NOT gate-only).

### 3.5 What is explicitly NOT done

The **token-sweep leg** of `AD-ChatV2-Inspector-Turn-Metadata-Wire` (actual `input_tokens` vs the `tokens_in` estimate + `cached_input_tokens` + `cache_hit_rate`) — a separate still-open leg (🟢). The **cost-in-stream carve-out** (`AD-ChatV2-Inspector-Cost-InStream`) — cost stays an honest "—" by design (post-loop). Any **ChatHeader change** (the badge already shows `currentModel`). Any **backend / wire / codegen / migration** (the `llm_request.model` field already exists). A **session-level model history** view. The other bucket-C carryovers (`AD-ChatV2-Resume-Tool-RoundTrips` / `AD-ChatV2-HITL-Card-Tool-Name` (likely already closed by 57.108) / transcript retention).

### 3.6 Validation (US-1..US-6)

Gates: mypy `src` **0/372** (re-assert — backend UNCHANGED) · run_all **10/10** (wire **25** UNCHANGED) · full pytest **2727+5skip** (UNCHANGED — FE-only; re-run to confirm no incidental break) · Vitest **908 + the new `mergeEvent` + Inspector cases** · mockup **51 UNCHANGED** (`diff styles-mockup.css` empty; `check:mockup-fidelity` `HEX_OKLCH_BASELINE` 51) · `npm run lint && npm run build` (NO `--silent`) · `black`/`isort`/`flake8` clean (backend untouched; re-run quick) · LLM-SDK-leak clean. Plus the §3.4 drive-through.

## 4. File Change List

| # | File | Action |
|---|------|--------|
| 1 | `frontend/src/features/chat_v2/types.ts` | EDIT — `AgentTurn += model: string \| null` |
| 2 | `frontend/src/features/chat_v2/store/chatStore.ts` | EDIT — `turn_start` init `model: null`; `llm_request` capture `model: ev.data.model` |
| 3 | `frontend/src/features/chat_v2/components/inspector/InspectorTurn.tsx` | EDIT — add `<KV k="model" .../>` row (after `cost`, before `active_skill`) |
| 4 | `frontend/tests/unit/chat_v2/chatStore.mergeEvent.test.ts` | EDIT — model-capture + turn_start-init cases |
| 5 | `frontend/tests/unit/chat_v2/components/inspector/ChatInspector.test.tsx` | EDIT — `makeAgentTurn` +`model`; model-row populated + "—" tests; comment bumps |
| 6 | `claudedocs/4-changes/feature-changes/CHANGE-098-chatv2-inspector-model-row.md` | NEW — change record |
| — | `event_wire_schema.py` (`llm_request.model` already on wire) · `loopEvents.generated.ts` (codegen) · `sse.py` · `router.py` · `styles-mockup.css` · `reference/design-mockups/**` · migration · new CSS class | **UNTOUCHED** |

## 5. Acceptance Criteria

1. **Type + capture**: `AgentTurn` has `model: string | null`; `turn_start` inits it null; the `llm_request` `mergeEvent` case stamps `ev.data.model` onto the active turn (alongside `tokensIn`); a multi-call turn keeps the latest.
2. **Render**: `InspectorTurn` shows a `model` KV row (`lastAgent.model ?? "—"`, mono), placed after `cost` / before `active_skill`.
3. **No new wire/codegen**: `event_wire_schema.py` 25 entries UNCHANGED; `loopEvents.generated.ts` untouched; `check_event_schema_sync` green.
4. **Mockup fidelity**: `diff styles-mockup.css` empty; `HEX_OKLCH_BASELINE` 51 unchanged; mockup 51 unchanged; no new CSS class / `oklch(`/`#hex` literal.
5. **Tests**: `mergeEvent` model-capture + turn_start-null cases pass; `ChatInspector` model-row populated + "—" cases pass; the pre-existing `active_skill` / dash tests stay green.
6. Gates: mypy 0 · run_all 10/10 (**25** unchanged) · pytest 2727+5 (unchanged) · Vitest 908 + new cases · `npm run build` clean · lint clean · LLM-SDK-leak clean.
7. **Drive-through PASS (MANDATORY, real UI + backend + LLM)**: a real chat message → the Inspector Turn tab model row shows the ACTUAL model (matching the ChatHeader badge), not "—"; screenshot + observed-vs-intended in progress.md. (NOT gate-only.)
8. The **`model` row leg** of `AD-ChatV2-Inspector-Turn-Metadata-Wire` CLOSED; CHANGE-098; calibration recorded; navigators + next-phase-candidates updated.

## 6. Deliverables

- [ ] US-1 `AgentTurn += model` (`types.ts`) + `turn_start` init `model: null` + `llm_request` capture `model: ev.data.model` (`chatStore.ts`)
- [ ] US-2 `<KV k="model" .../>` row in `InspectorTurn` (after `cost`, before `active_skill`; reuse `KV`, no new CSS)
- [ ] US-3 `chatStore.mergeEvent` tests: `llm_request` stamps model; `turn_start` inits null
- [ ] US-4 `ChatInspector` tests: `makeAgentTurn` +`model`; model-row populated + "—"; pre-existing dash/active_skill tests stay green
- [ ] US-5 drive-through (real chat → Inspector Turn tab model row shows the real model, matches badge; screenshot; MANDATORY)
- [ ] US-6 CHANGE-098 + closeout (retro + calibration + navigators + CLOSE the `model` row leg)

## 7. Workload Calibration

- Scope class **`chatv2-inspector-existing-field-surface` 0.85** (the 57.120 class — surface an ALREADY-store-captured wire field in a NEW chat-v2 render location + a thin per-turn carry-forward; NO new wire field / codegen / backend / migration. This is the **2nd data point** for the class (57.120 was 1st, re-pointed 0.55→0.85 at ratio ~1.6). 57.131 is even thinner than 57.120: 57.120 carried `activeSkill` cross-turn (from the trigger user-turn at turn_start); 57.131 stamps `model` same-turn at `llm_request` (no cross-turn traversal) + has a TRIVIAL drive-through (a normal message produces an `llm_request`, vs 57.120's force-load setup). **Ceremony-floor note** (57.120/122/123/126/128/129): the code is ~6-8 lines but a full-ceremony parent-direct sprint WITH a mandatory drive-through does NOT drop to the 0.45-0.55 band — the fixed-cost ceremony (plan/checklist/Day-0/drive-through/CHANGE/retro/navigators) is NOT code-accelerated. 0.85 is the validated ceremony floor for this shape. Per the 57.120 rule: if this 2nd `*-existing-field-surface` lands < 0.7 at 0.85, lower again toward 0.65.)
- **Agent-delegated: no** (parent-direct — the per-turn capture TIMING (`llm_request` not `turn_start`), the required-vs-optional type decision + its tsc literal ripple, and the mockup-fidelity-safe render are small but correctness-/convention-critical and best hand-authored + self-verified). `agent_factor` 1.0 → 3-segment form.
- Bottom-up est ~3.3 hr (Day-0 三-prong (recon head-start, re-verify + enumerate AgentTurn literals) ~0.4 · type + store capture + turn_start init ~0.5 · InspectorTurn row ~0.3 · tests (mergeEvent + ChatInspector + fixture ripple) ~0.9 · drive-through (FE rebuild + send message + Inspector verify + screenshot) ~0.7 · CHANGE-098 + closeout ~0.5) → class-calibrated commit ~2.8 hr (mult 0.85). Day-4 retro Q2 verifies (`chatv2-inspector-existing-field-surface` 2nd data point; flag if it lands < 0.7 → re-point toward 0.65 per the 57.120 rule).

## 8. Dependencies & Risks

| Risk | Mitigation |
|------|------------|
| **Required `model` field tsc ripple** (every `AgentTurn` literal needs `model:`) | D-agentturn-literal-sites grep `role: "agent"` in src + tests BEFORE the type edit → enumerate every literal; add `model:` to each; `npm run build` (tsc) confirms none missed. |
| **Capture at the wrong moment** (stamping at `turn_start` → always null) | Capture in the `llm_request` case (the model is known there); the `mergeEvent` test asserts model is null after `turn_start` alone + set after `llm_request`. |
| **`active_skill '—' length 1` test breaks** (a new "—" row appears in the default populated turn) | `makeAgentTurn` default gets a NON-null `model` → the model row shows a value, not "—" → the active_skill length-1 assertion stays correct (D-render-test-impact confirms). |
| **Mockup-fidelity baseline bump** (a new literal via the row) | Reuse `var(--*)` + `.mono` (the 57.120 active_skill row precedent uses tokens, not literals); `diff styles-mockup.css` empty; `npm run check:mockup-fidelity` asserts `HEX_OKLCH_BASELINE` 51 (run it, don't eyeball). |
| **Risk Class E** — stale FE dev server serves pre-edit bundle during the drive-through | rebuild / hard-refresh Vite so it picks up the type + store + Inspector edits before trusting the UI (backend UNCHANGED — no backend restart needed). |
| **Pre-existing billing flake** (`AD-Billing-Outbox-Drain-Test-Flake`) may surface once | re-run confirms 2727+5 (do NOT skip the test); FE-only change is unrelated. |
| **`llm_request.model` assumed nullable** (it's actually a required `string`) | D-llm-request-model-field confirms `currentModel: ev.data.model` (no `?? null`) → `ev.data.model` is `string`; the per-turn field is `string | null` only because it's null BEFORE the first `llm_request`. |

## 9. Out of Scope (this sprint; → separate slices / ADs)

- **The token-sweep leg** of `AD-ChatV2-Inspector-Turn-Metadata-Wire` (actual `input_tokens` vs estimate + `cached_input_tokens` + `cache_hit_rate`) — separate still-open leg (🟢).
- **The cost-in-stream carve-out** (`AD-ChatV2-Inspector-Cost-InStream`) — cost stays an honest "—" (post-loop by design).
- **Any ChatHeader change** — the badge already shows `currentModel`.
- **Any backend / wire / codegen / migration** — `llm_request.model` already exists on the wire.
- **A session-level model-history view** — out of scope.
- **`AD-ChatV2-Resume-Tool-RoundTrips` / `AD-ChatV2-HITL-Card-Tool-Name` (likely already closed by 57.108) / transcript retention** — the other bucket-C carryovers (separate slices).
- **ANY new CSS class / mockup authoring / new backend primitive.**
