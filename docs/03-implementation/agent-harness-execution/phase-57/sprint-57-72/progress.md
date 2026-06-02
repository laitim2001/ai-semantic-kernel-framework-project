# Sprint 57.72 Progress — A-5c Inspector UI: Subagent Tree tab (Tree tab only)

**Plan**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-72-plan.md`
**Checklist**: `.../sprint-57-72-checklist.md`
**Branch**: `feature/sprint-57-72-inspector-tree` (from main `0f76e592`)

---

## Day 0 — 2026-06-03 — Plan-vs-Repo Verify + Reframe + Branch

### Scope selection (AskUserQuestion 2026-06-03)
- After A-4 (57.71) shipped, the user picked **A-5c Inspector UI** as the next sprint (57.72). Day-0 ground-truth surfaced that of the 3 unfilled chat-v2 Inspector tabs (Turn already wired), only **Tree** can be honestly filled from events on the wire today — **Trace** needs `SpanStarted`/`SpanEnded` over SSE (A-4 span tree → OTel only, SSE form deferred) and **Memory** needs `memory_accessed` (never yielded; A-1 sliver). User AskUserQuestion chose **Tree tab only** (over also unblocking Memory's or Trace's backend producer); Trace/Memory stay `ComingSoon`.

### Three-prong Day-0 verify — drift D1-D6 (researcher ground-truth, main `0f76e592`)

- **D1** — Tab-vs-producer availability: only **Tree** fillable today (Trace ← SpanStarted/SpanEnded SSE deferred; Memory ← `memory_accessed` never yielded). Filling Trace/Memory now = fake data (AP-4) → deferred.
- **D2** — Data model already exists: `chatStore.ts:514/571` — `subagent_spawned`/`subagent_completed` already update `s.subagents` (`SubagentNode`: subagentId/parentId/mode/status/summary/tokensUsed/spawnedAt, Sprint 57.12). No new event/store work.
- **D3** — Mockup Tree (`page-chat.jsx:489-531`): header + `.subagent-tree` (root→fork→children) + `.thin-rule` + 4 `.spread` (Mode/Depth/Concurrency/Tokens). Classes already in byte-identical `styles-mockup.css`.
- **D4** — Mirror pattern: `InspectorTurn.tsx` (selector + verbatim classes + empty state + `eslint-disable no-restricted-syntax` + lucide icons). `InspectorTree` mirrors it.
- **D5** — Data gaps: `SubagentNode` has no per-child `turns` + no concurrency **max** (mockup "3 / 5"). Render available fields; "—"/omit the rest (InspectorTurn "—" convention); do NOT fabricate (AP-4).
- **D6** — Mockup-fidelity infra: `styles-mockup.css` byte-identical (diff empty); `.subagent-tree` classes exist → no CSS change; `check:mockup-fidelity` `HEX_OKLCH_BASELINE = 50` MUST stay (57.69 D-DAY2-1: a frontend sprint MUST run the gate, not just lint/build/test).

### go/no-go = **GO (Tree tab only, user-confirmed)**
- <20% drift (scope confirmed Tree-only; data model + mockup classes + mirror pattern all present). Plan + checklist drafted to the confirmed scope.

### Decisions
- Scope = Tree tab only; Trace/Memory deferred to their backend producers; render available `SubagentNode` fields, "—"/omit per-child turns + concurrency max (D5, no fabrication); verbatim mockup classes + `var(--*)` colors (no new CSS, no baseline bump); mirror `InspectorTurn`.
- **Agent-delegated: yes** — single `code-implementer` (component + test + mockup-fidelity verify); parent independently re-verifies (verbatim-class fidelity + tree-build logic + empty state + runs `check:mockup-fidelity`).
