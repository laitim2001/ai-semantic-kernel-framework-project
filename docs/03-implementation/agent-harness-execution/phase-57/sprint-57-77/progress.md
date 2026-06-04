# Sprint 57.77 Progress — Memory ops-history frontend

**Plan**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-77-plan.md`
**Checklist**: `...sprint-57-77-checklist.md`
**Branch**: `feature/sprint-57-77-memory-ops-history-frontend` (from `main` `2947010a`)
**Closes**: `AD-Memory-OpsHistory-Backend` (frontend half; backend = Sprint 57.76)

---

## Day 0 — 2026-06-04 — Plan-vs-Repo Verify + Decisions

### Decisions (user-locked, AskUserQuestion ×1)
- **TimeTravel handling**: **Full wire** — RecentOps consumes real `GET /memory/ops`; TimeTravel marks derive from real `created_at_ms` (fixture removed); scrub cursor **really filters** RecentOps to `created_at_ms ≤ cursor`. Honest semantic = browse ops timeline, NOT point-in-time state reconstruction (deferred, retro 57.76 Q5). Keeps AP-4 clean (scrub has real effect, not Potemkin slider).
- **Split**: frontend-only (backend shipped 57.76). Agent-delegated: yes (Track A frontend code-implementer + parent re-verify).
- **FE type**: mirror backend wire verbatim (`MemoryOpItem` {op,scope,key,time_scale,value_snapshot,actor,created_at_ms}); remove fixture-era `RecentMemoryOp {op,scope,k,v,by,at}`; render maps key→Key/value_snapshot→Value/actor→By/created_at_ms→When.

### Day-0 verify (2 researcher passes + parent, main `2947010a`)
- **D-DAY0-1 (mockup line drift)**: retro `:556-579` → actual `:557-579` (RecentOps) + `:600-656` (scrubber). Plan §3 uses corrected refs.
- **D-DAY0-2 (op/scope value drift)**: `op` ∈ {WRITE,EVICT} (not READ/EXPIRE); `scope` ∈ {user,tenant} only (role/system raise, session in-memory → not recorded). Render uses real value set.
- **D-DAY0-3 (wire shape, authoritative)**: `MemoryOpItem` (`memory.py:153-166`) {op,scope,key,time_scale,value_snapshot,actor,created_at_ms}; `MemoryOpsResponse` (:169-171) {ops,next_cursor}; `before`/`next_cursor` = created_at_ms strict-older. FE type mirrors wire; fixture type removed.
- **D-DAY0-4 (net-new infra)**: no useMemoryOps/fetchOps/API-type. Mirror targets: `useMemoryMatrix.ts:31-39` + `fetchMatrix` (`memoryService.ts:123-131`).
- **D-DAY0-5 (greenfield tests)**: 0 component Vitest; `memoryService.test.ts` has no fetchMatrix test; no Playwright memory spec. New coverage greenfield.
- **D-DAY0-6 (inline-style)**: both targets use file-top `eslint-disable no-restricted-syntax`; new inline styles covered. Prong-2.5: shadcn residue 0, hex/oklch 0.
- **D-DAY0-7 (scrub no real consumer today)**: `MemoryView.tsx:73-90` owns cursor but MemoryMatrix ignores it → scrub visual-only. Full-wire fixes (cursor → RecentOps filter).

### Prong 1 (path) — GREEN
All confirmed: `hooks/useMemoryMatrix.ts`, `services/memoryService.ts` (fetchMatrix :123-131), `types.ts` (MemoryMatrixResponse :93-97), `components/{RecentMemoryOpsCard,TimeTravelScrubber,MemoryView}.tsx`, `_fixtures.ts` (3 ops fixtures), `api/v1/memory.py` (/ops :527-571, MemoryOpItem :153-166).

### Prong 2 (content) — researcher-confirmed
- RecentMemoryOpsCard fixture-based no-props + stale banner (:100); TimeTravelScrubber fixture marks + stale banner (:162); MemoryView owns cursor+playing+playback setInterval; useMemoryMatrix minimal TanStack; fetchMatrix simple GET; no offset for ops (`before` cursor).

### go/no-go = **GO** (Day 1 data layer). All touch-points are net-new wiring; components already mockup-ported; no >20% scope drift.

---
