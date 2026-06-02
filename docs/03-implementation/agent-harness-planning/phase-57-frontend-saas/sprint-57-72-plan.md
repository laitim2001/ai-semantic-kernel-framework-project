# Sprint 57.72 Plan — A-5c Inspector UI: Subagent Tree tab (chat-v2 Inspector, Tree tab only)

**Purpose**: Advance `A-5c` (diagnostic Inspector UI, Area-A item 5c) by filling the **one Inspector tab that can be honestly populated from events already on the SSE wire today** — the chat-v2 Inspector **Tree** tab (Subagent Tree). The `subagent_spawned` / `subagent_completed` events are already serialized + wired into the chatStore `subagents` slice (Sprint 57.12), but the chat-v2 Inspector's Tree tab is still a `ComingSoonInspectorTab` placeholder. This sprint builds `InspectorTree.tsx` — a verbatim mockup re-point of `page-chat.jsx:489-531` (`.subagent-tree` root→fork→children + the Mode/Depth/Concurrency/Tokens summary rows) reading the existing `subagents` slice — replacing the placeholder. **Scope is the Tree tab ONLY** (user-confirmed): the other two unfilled tabs need deferred backend producers — **Trace** needs `SpanStarted`/`SpanEnded` over SSE (A-4 span tree goes to OTel only; the SSE form is the deferred A-4/A-5 sliver) and **Memory** needs `memory_accessed` (never yielded in `loop.py`; the A-1 sliver) — filling either with fake data = AP-4 Potemkin, so both stay `ComingSoon`. Pure frontend, no backend change. This is a **feature-continuation sprint** (a verbatim mockup re-point of one tab, mirroring the already-shipped `InspectorTurn.tsx` sibling) → **no design note**; the frontend Mockup-Fidelity Hard Constraint applies (`docs/rules-on-demand/frontend-mockup-fidelity.md`).
**Category / Scope**: Frontend (chat-v2 Inspector — mockup `page-chat.jsx` Tree tab) consuming Cat 11 subagent events; Phase 57.72
**Created**: 2026-06-03
**Status**: Draft — code execution gated on Day-0 GO (Step 2.5). Ground-truth already gathered via a Day-0 researcher pass (see §0).
**Source**: A-5 deep-analysis `claudedocs/5-status/cat-events-to-sse-analysis-20260531.md` (§8 A-5c DoD: "each diagnostic event has a frontend Inspector consumer") + A+B+C capstone `integration-gap-capstone-abc-20260601.md` (A-5c priority #5, downstream of A-1/A-2/A-4) + **Day-0 ground-truth researcher pass (2026-06-03)** + user AskUserQuestion decision 2026-06-03 (**scope = Tree tab only**; Trace/Memory deferred to their producers)

> **Modification History**
> - 2026-06-03: Initial creation — A-5c Inspector Subagent Tree tab (Tree only; Trace/Memory deferred to producers); frontend feature-continuation (no design note)

---

## 0. Background

A-5 is the 4-stage event-visibility pipeline (defined → yielded → serialized → rendered). A-5a (Sprint 57.66) serialized the diagnostic events to SSE; A-5b (Sprint 57.67) added the schema codegen + CI parity gate. **A-5c is the remaining frontend consumer half**: render the diagnostic / subagent events in the chat-v2 Inspector. The chat-v2 Inspector is a 4-tab panel (mockup `page-chat.jsx:371-390`: **Turn / Trace / Memory / Tree**); the **Turn** tab is already fully wired (`InspectorTurn.tsx`, Sprint 57.21/57.30), the other three are `ComingSoonInspectorTab` placeholders.

### Day-0 ground-truth (researcher pass, main `0f76e592`)

- **D1 — Tab availability vs live producers**: of the 3 unfilled tabs, only **Tree** can be honestly filled from events on the wire today. **Trace** needs `SpanStarted`/`SpanEnded` over SSE (A-4 shipped the loop span tree to OTel only — the SSE form is the deferred A-4/A-5 sliver); **Memory** needs `memory_accessed` (the contract exists but `loop.py` never yields it — the A-1 sliver). Filling either now = fake data (AP-4). → user-confirmed **Tree tab only**; Trace/Memory stay `ComingSoon`.
- **D2 — The data model already exists**: `chatStore.ts:514/571` — `subagent_spawned` / `subagent_completed` already update an `s.subagents` slice of `SubagentNode` (`{ subagentId, parentId, mode, status: "running"|"completed", summary, tokensUsed, spawnedAt }`, Sprint 57.12). No new event/store work — the Tree tab just reads this slice.
- **D3 — Mockup Tree structure** (`page-chat.jsx:489-531`): header "Subagent tree · live"; `.subagent-tree` with a root `.subagent-row` (icon + name + "root" + status Badge), an `.indent` fork row, a nested `.indent` of child `.subagent-row`s (icon + name + turns + task + status Badge dot); a `.thin-rule`; then a `.col` of 4 `.spread` rows — Mode (Badge) / Depth (mono) / Concurrency (mono "3/5") / Tokens subtree (mono). All classes are already in the byte-identical `styles-mockup.css`.
- **D4 — Mirror pattern exists**: `InspectorTurn.tsx` is the wired sibling — reads `useChatStore((s) => s.turns)`, renders verbatim mockup classes (`.col`/`.spread`/`.thin-rule`/`.mono`/`.subtle`/`.row`/`.badge`), has an empty state (`data-testid` + "No active turn"), uses an `eslint-disable no-restricted-syntax` block with a mockup-line-ref comment for the verbatim inline styles, maps lucide icons to the mockup `Icon name=…`. `InspectorTree` mirrors this exactly.
- **D5 — Data gaps (render what exists, placeholder the rest)**: `SubagentNode` has no per-child `turns` and no concurrency **max** (the mockup's "3 / 5" — the 5 is a config not in the data). Per the `InspectorTurn` "—" convention, render the available fields (name / status / mode / tokens / tree nesting / depth / running-count) and omit-or-placeholder the rest (turns, concurrency max) — do NOT fabricate.
- **D6 — Mockup-fidelity infra**: `styles-mockup.css` is byte-identical to `reference/design-mockups/styles.css` (diff empty); the `.subagent-tree`/`.subagent-row`/`.indent` classes already exist → **no CSS change**. The CI gate is `frontend/scripts/check-mockup-fidelity.mjs` (`npm run check:mockup-fidelity`), `HEX_OKLCH_BASELINE = 50` — the new component must use `var(--*)` tokens (no hardcoded hex/oklch) so the baseline does not move (Sprint 57.69 D-DAY2-1 lesson: a frontend sprint MUST run `check:mockup-fidelity`, not just lint/build/test).

**Net** (frontend-only): a new `InspectorTree.tsx` (verbatim re-point of mockup `page-chat.jsx:489-531`) that builds a tree from the flat `s.subagents` slice (via `parentId` nesting) + the Mode/Depth/Concurrency/Tokens summary, with an empty state; `ChatInspector.tsx` swaps the Tree `ComingSoonInspectorTab` for it. Trace + Memory stay `ComingSoon` (deferred to their backend producers). No backend / event / CSS change.

---

## 1. Sprint Goal

Fill the chat-v2 Inspector **Tree** tab from the existing `subagents` slice. Build `InspectorTree.tsx` as a verbatim mockup re-point of `page-chat.jsx:489-531` — render the `.subagent-tree` (root → fork → children, nested by `parentId`) with per-node name / status Badge / mode, plus the `.thin-rule` + Mode / Depth / Concurrency / Tokens-subtree summary `.spread` rows, computing depth + token-subtree-sum + running-count from the slice and rendering "—" (or omitting) the fields the slice does not carry (per-child turns, concurrency max). Add an empty state ("no subagents spawned this session") mirroring `InspectorTurn`. Replace the Tree `ComingSoonInspectorTab` in `ChatInspector.tsx`. Verify against the mockup via the Mockup-Fidelity DoD (CSS diff empty, computed-style spot-check, `check:mockup-fidelity` baseline unchanged). **Scope = Tree tab ONLY** — Trace (needs SpanStarted/SpanEnded over SSE) + Memory (needs `memory_accessed`) stay `ComingSoon` (§9). Pure frontend; no backend / event / CSS change.

---

## 2. User Stories

- **US-1 (Tree tab component)** — As an operator watching a run that spawns subagents, I want the Inspector Tree tab to show the live subagent tree (root → children, names, status) so I can see what was spawned and its state. → `InspectorTree.tsx` (NEW) reading `s.subagents`, verbatim mockup `.subagent-tree`.
- **US-2 (summary rows + derived aggregates)** — As an operator, I want the Mode / Depth / Concurrency / Tokens-subtree summary so I can see the fork shape + cost at a glance. → compute depth (max `parentId` nesting), running-count, token-subtree-sum from the slice; render available fields, "—"/omit the unavailable ones (turns, concurrency max — D5).
- **US-3 (empty state + wire-in)** — As an operator on a run with no subagents, I want a clear "no subagents spawned this session" empty state (not a blank tab); and the Tree tab must replace the `ComingSoon` placeholder. → empty state mirroring `InspectorTurn`; `ChatInspector.tsx` swaps the Tree placeholder for `InspectorTree`.
- **US-4 (mockup-fidelity + validation)** — As a reviewer, I want the Tree tab to follow the Mockup-Fidelity Hard Constraint (verbatim mockup classes, `var(--*)` colors, no new CSS, `check:mockup-fidelity` baseline unchanged) and a Vitest spec proving the tree renders from a seeded `subagents` slice + the empty state.

---

## 3. Technical Specifications

### 3.0 Architecture (frontend-only)

```
  chatStore  s.subagents: SubagentNode[]  (Sprint 57.12; updated by subagent_spawned/completed)
             { subagentId, parentId, mode, status, summary, tokensUsed, spawnedAt }
                          │  useChatStore((s) => s.subagents)
                          ▼
  InspectorTree.tsx (NEW — verbatim re-point of page-chat.jsx:489-531)
    - buildTree(subagents): flat → nested by parentId (root = parentId ∉ subagent ids)
    - render .subagent-tree (root .subagent-row + .indent children .subagent-row)
        per node: icon (lucide) + name (var(--primary)/--info) + status Badge
    - .thin-rule
    - .col summary: Mode (Badge) / Depth (mono) / Concurrency (mono, running-count) / Tokens-subtree (mono, Σ tokensUsed)
    - empty state when s.subagents is empty ("no subagents spawned this session")
                          │
                          ▼
  ChatInspector.tsx — Tree tab: <ComingSoonInspectorTab> → <InspectorTree/>
```

Trace + Memory tabs unchanged (`ComingSoonInspectorTab`, deferred to their producers). No backend, no new SSE event, no CSS, no `styles-mockup.css` change.

### 3.1 InspectorTree component (US-1/US-2/US-3) — `InspectorTree.tsx` (NEW)
- Mirror `InspectorTurn.tsx`: file header with mockup line-refs + Related; `eslint-disable no-restricted-syntax` block with a mockup-line-ref comment for the verbatim inline styles (colors via `var(--primary)`/`var(--thinking)`/`var(--info)`/`var(--fg-muted)`/`var(--fg-subtle)` — **no hardcoded hex/oklch**); lucide icons mapped to the mockup `Icon name="chat"/"fork"/"chevron_right"` (e.g. `MessageSquare` / `GitFork` / `ChevronRight`).
- `buildTree(subagents)`: group by `parentId`; roots = nodes whose `parentId` is not another subagent's `subagentId` (i.e. the dispatching session). Render root rows + nested `.indent` children. (A flat single-level render is acceptable if all spawns share one parent — match the mockup's root→fork→children depth-2 shape; deeper nesting recurses.)
- Per node row (`.subagent-row`): icon + name (`subagentId`, color by depth/role) + status Badge (running → `tone="warning"`/`info`, completed → `tone="success" dot`) + mode/summary as the subtle `.grow` task text where the mockup shows it.
- Summary `.spread` rows: **Mode** = the dominant `mode` (Badge); **Depth** = max nesting depth (mono); **Concurrency** = running-count (mono — render just the count, NOT a fabricated "/max" since max is not in the data, D5); **Tokens (subtree)** = `Σ tokensUsed` (mono, `toLocaleString()`; "—" if all null).
- Empty state (`data-testid="inspector-tree-empty"`): "no subagents spawned this session" mirroring `InspectorTurn`'s empty-state shape.

### 3.2 Wire-in (US-3) — `ChatInspector.tsx` (EDIT)
- Replace the Tree tab's `<ComingSoonInspectorTab .../>` with `<InspectorTree/>`. Keep the `AD-ChatV2-Inspector-{Trace,Memory}-Phase2` placeholders for the other two tabs (update the Tree-related AD note to "shipped Sprint 57.72").

### 3.3 Mockup-fidelity DoD (US-4) — `frontend-mockup-fidelity.md`
- `diff reference/design-mockups/styles.css frontend/src/styles-mockup.css` → empty (no CSS change this sprint; classes already exist).
- Verbatim mockup classes only (`.subagent-tree`/`.subagent-row`/`.indent`/`.spread`/`.thin-rule`/`.col`/`.mono`/`.subtle`/`.grow`/`.badge`); colors via `var(--*)`; no shadcn primitive as a style layer; no hardcoded hex/oklch (grep guard).
- `npm run check:mockup-fidelity` → baseline unchanged (`HEX_OKLCH_BASELINE = 50`) — **MUST run** (Sprint 57.69 D-DAY2-1 lesson; not just lint/build/test).
- computed-style spot-check of `.subagent-row` / `.spread` / `.badge` vs the mockup (Tree tab visible after seeding a subagent in the store / Storybook-style render).

### 3.4 Lint / validation
- `npm run lint` (NO `--silent` — Sprint 57.40 lesson) + `npm run build` + `npm run test` (Vitest) + `npm run check:mockup-fidelity`. tsc 0.
- **Vitest** (`InspectorTree.test.tsx` NEW, or extend `ChatInspector.test.tsx`): seed `s.subagents` with a root + 2 children → assert the tree renders names + status + the Mode/Depth/Concurrency/Tokens summary; assert the empty state when `s.subagents` is `[]`; assert the Tree tab no longer renders the ComingSoon placeholder.
- No backend test change (no backend touch). pytest untouched.

---

## 4. File Change List

| File | Change |
|------|--------|
| `frontend/src/features/chat_v2/components/inspector/InspectorTree.tsx` | **NEW** — verbatim re-point of mockup `page-chat.jsx:489-531`; reads `s.subagents`; tree + summary + empty state (US-1/US-2/US-3) |
| `frontend/src/features/chat_v2/components/inspector/ChatInspector.tsx` | **EDIT** — Tree tab `ComingSoonInspectorTab` → `InspectorTree`; update Tree AD note (US-3) |
| `frontend/src/features/chat_v2/components/inspector/InspectorTree.test.tsx` (or extend `ChatInspector.test.tsx`) | **NEW/extend** — tree render + summary + empty state + placeholder-gone (US-4) |

**No backend change. No new SSE event / wire-type / codegen. No CSS / `styles-mockup.css` change** (the `.subagent-tree` classes already exist, byte-identical). **No new dependency.** Trace + Memory tabs untouched (`ComingSoon`, deferred to producers).

---

## 5. Acceptance Criteria

- The chat-v2 Inspector **Tree** tab renders the live subagent tree from `s.subagents`: root → children nested by `parentId`, per-node name + status Badge + mode; a `.thin-rule`; and the Mode / Depth / Concurrency (running-count) / Tokens-subtree summary `.spread` rows. Fields not in the slice (per-child turns, concurrency max) are "—"/omitted — NOT fabricated.
- An empty `s.subagents` shows a clear empty state ("no subagents spawned this session"); the Tree tab no longer renders `ComingSoonInspectorTab`.
- **Mockup-fidelity**: `diff styles.css styles-mockup.css` empty; verbatim mockup classes + `var(--*)` colors; no hardcoded hex/oklch (grep guard); `npm run check:mockup-fidelity` baseline unchanged (50).
- `npm run lint` (no `--silent`) + `npm run build` + tsc 0; Vitest green (tree + empty state + placeholder-gone). Trace + Memory stay `ComingSoon`.
- No backend change (pytest / mypy / V2 lints untouched).

---

## 6. Deliverables

- [ ] `InspectorTree.tsx` (tree + summary + empty state, verbatim mockup) (US-1/US-2/US-3)
- [ ] `ChatInspector.tsx` Tree tab wire-in (US-3)
- [ ] Vitest (tree render + summary + empty state + placeholder-gone) (US-4)
- [ ] Mockup-fidelity DoD pass (CSS diff empty + `check:mockup-fidelity` 50 + computed-style spot-check) (US-4)
- [ ] CHANGE-040 + progress.md + retrospective.md

---

## 7. Workload Calibration

Scope class: **`frontend-mockup-direct-port` (0.55)** — a verbatim mockup re-point of one Inspector tab, mirroring the already-shipped `InspectorTurn.tsx` sibling, reading an existing store slice (no new event/store/CSS). Smaller than a full-page port. **Agent-delegated: yes** (single `code-implementer` for the component + test + mockup-fidelity verify; parent re-verify reads the component for verbatim-class fidelity + the tree-build logic + runs `check:mockup-fidelity`). `agent_factor` **`mechanical-greenfield-design-decisions` 0.65** (genuine design: flat→tree build from `parentId`, depth/token-subtree/running-count aggregates, the D5 render-vs-placeholder decision, empty state; on top of heavy pattern-mirror of `InspectorTurn`).

> Bottom-up est ~7 hr → class-calibrated commit ~3.9 hr (mult 0.55) → agent-adjusted commit ~2.5 hr (agent_factor 0.65).

Caveat (carried 57.63-57.71): agent-delegated sprints have no clean wall-clock (`AD-Calibration-AgentDelegated-WallClock-Measure`; would be **10th consecutive**). `frontend-mockup-direct-port` 0.55 is an existing class (3-sprint mean ~0.85, bimodal); this is a small structural port (not a token-sweep) so the upper mode is expected. Record caveated.

---

## 8. Dependencies & Risks

| Risk | Mitigation |
|------|------------|
| **Tree tab mostly empty in practice** (demo path may not spawn subagents) | The empty state is a first-class deliverable (US-3); the Vitest seeds `s.subagents` directly to prove the populated render. Value is realized when a run spawns subagents (A-3a is wired) |
| **Data gaps** (no per-child turns, no concurrency max) | Render available fields, "—"/omit the rest (D5 + `InspectorTurn` "—" convention); do NOT fabricate (AP-4) |
| **Mockup-fidelity drift** (the 10-sprint drift root cause) | Verbatim mockup classes only; `var(--*)` colors; no new CSS; CSS diff empty; **`check:mockup-fidelity` MUST run** (57.69 D-DAY2-1: a frontend sprint that skips this gate fails CI) |
| **Hardcoded color regression** (baseline bump) | Colors via `var(--primary)`/`var(--info)`/etc.; grep guard for hex/oklch; baseline stays 50 |
| **flat→tree build correctness** (parentId nesting / cycles) | roots = `parentId` ∉ subagent ids; guard against a node being its own ancestor; Vitest covers root + nested children |
| **eslint `no-restricted-syntax`** on verbatim inline styles | Mirror `InspectorTurn`'s `eslint-disable no-restricted-syntax` block + mockup-line-ref comment; lint runs WITHOUT `--silent` (57.40 lesson) |

---

## 9. Out of Scope (this sprint; carryover)

- **Inspector Trace tab** — needs `SpanStarted` / `SpanEnded` over SSE (A-4 shipped the loop span tree to OTel only; the SSE form is the deferred A-4/A-5 sliver) + high-volume event backpressure. Stays `ComingSoon` (`AD-ChatV2-Inspector-Trace-Phase2`).
- **Inspector Memory tab** — needs `memory_accessed` (contract exists, never yielded in `loop.py`; the A-1 sliver). Stays `ComingSoon` (`AD-ChatV2-Inspector-Memory-Phase2`).
- **Diagnostic-event surfacing** (`prompt_built` / `context_compacted` / `state_checkpointed` / `tripwire_triggered` / `guardrail_triggered`) — on the SSE wire (rawEvents-only) but with no mockup-faithful Inspector home; surfacing them needs either the Trace tab (span SSE) or a new alert component not in the Inspector mockup. Deferred.
- **Per-child turns + concurrency max** — not in the `SubagentNode` slice; would need richer subagent telemetry (a backend producer change). Deferred.
- **Other Area-A**: A-6 (frontend real-data wiring), the FE `/subagents` page wiring (57.70 carryover). Two high-priority capstone key chains remain untouched: C-11 (real-LLM enablement) + the billing-correctness bundle (B-7/B-8/C-15).
