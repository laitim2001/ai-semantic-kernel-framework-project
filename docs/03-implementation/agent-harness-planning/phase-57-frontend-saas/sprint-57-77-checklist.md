# Sprint 57.77 — Checklist (Memory ops-history frontend: useMemoryOps hook + RecentOps/TimeTravel wire + remove fixtures)

**Plan**: `sprint-57-77-plan.md`
**Branch**: `feature/sprint-57-77-memory-ops-history-frontend` (from `main` `2947010a`)
**Closes**: `AD-Memory-OpsHistory-Backend` (frontend half; backend = Sprint 57.76)

---

## Day 0 — Plan-vs-Repo Verify + Branch + Decisions

### 0.1 Day-0 verify (2 researcher passes, main `2947010a`)
- [x] **Prong 1 (path)** — confirm: `features/memory/hooks/useMemoryMatrix.ts`, `services/memoryService.ts`, `types.ts`, `components/{RecentMemoryOpsCard,TimeTravelScrubber,MemoryView}.tsx`, `_fixtures.ts`, `backend/src/api/v1/memory.py` (`/ops` :527-571).
- [x] **Prong 2 (content)** — D-DAY0-1..7 in plan §0 (mockup line drift; op WRITE/EVICT + scope user/tenant; wire shape authoritative; all infra net-new; greenfield tests; file-top eslint-disable; scrub no real consumer today).
- [x] **Prong 2.5 (child tree)** — RecentMemoryOpsCard + TimeTravelScrubber: shadcn residue 0, hex/oklch 0, inline-style under file-top disable.
- [x] **go/no-go** — GO; no >20% drift (all touch-points net-new wiring, components already mockup-ported).

### 0.2 Branch + decisions
- [x] **Branch created** `feature/sprint-57-77-memory-ops-history-frontend`
- [x] **Decisions locked**: Full wire (AskUserQuestion) — RecentOps real + TimeTravel marks from real ops + scrub really filters RecentOps; honest ops-browsing (no state reconstruction); remove 2 stale banners + 3 fixtures; agent-delegated Track A frontend + parent re-verify.
- [x] **Day-0 commit** plan + checklist + progress.md Day 0

---

## Day 1 — Data layer (US-3/US-1)

### 1.1 API types
- [ ] **`MemoryOpItem` + `MemoryOpsResponse`** in `types.ts` (mirror wire verbatim, beside MemoryMatrixResponse)
  - fields: op/scope/key/time_scale/value_snapshot/actor/created_at_ms; response ops[] + next_cursor
  - DoD: tsc clean; MHist updated

### 1.2 fetchOps service
- [ ] **`memoryService.fetchOps(limit=50, before?, signal?)`** after `fetchMatrix` (:131)
  - `URLSearchParams` (limit always; before only if provided — NOT offset-based `_buildPageParams`); `GET ${API_BASE}/ops?...`; `_handleResponse<MemoryOpsResponse>`
  - DoD: MHist on memoryService.ts header

### 1.3 useMemoryOps hook
- [ ] **NEW `hooks/useMemoryOps.ts`** mirror `useMemoryMatrix.ts` verbatim
  - `MEMORY_OPS_QUERY_KEY = ["memory","ops"]`; `queryFn: ({signal}) => memoryService.fetchOps(50, undefined, signal)`; `staleTime: 30_000`
  - DoD: file header + MHist; tsc clean

---

## Day 2 — Component wire (US-1/US-2)

### 2.1 RecentMemoryOpsCard wire
- [ ] **consume `useMemoryOps()`** + add prop `{ cursor?: number | null }`
  - filter `ops` to `created_at_ms ≤ cursor` (null → all)
  - render 6-col table: op→Op badge, scope→Scope, key→Key, value_snapshot→Value (240px ellipsis), actor→By, created_at_ms→When (`HH:MM:SS` helper); null → `—`
  - mockup-native loading/error/empty states (NOT shadcn skeletons)
  - **remove** `RECENT_MEMORY_OPS` import + gap banner (:100)
  - DoD: mockup classes verbatim; MHist

### 2.2 TimeTravelScrubber marks from ops
- [ ] **consume `useMemoryOps()`** + derive marks from real `created_at_ms`
  - domain `[minMs,maxMs]`; mark position normalized; empty ops → no marks + subtle hint
  - keep mockup props `{cursor,onCursor,playing,onPlay}` + scrubber/play UI verbatim (:600-656)
  - **remove** `MEMORY_OPS_TIMELINE` + `TIME_TRAVEL_MARKS` imports + gap banner (:162)
  - DoD: mockup classes verbatim; MHist

### 2.3 MemoryView wiring
- [ ] **cursor init `null`** (latest/all) + playback `setInterval` advances cursor over `[minMs,maxMs]` (pause/reset at end)
  - pass `cursor` → RecentMemoryOpsCard; `{cursor,onCursor,playing,onPlay}` → TimeTravelScrubber
  - no mount-order/layout change
  - DoD: MHist; scrub filters RecentOps (real effect, AP-4 clean)

---

## Day 3 — Tests + fixture removal (US-5/US-4)

### 3.1 Remove fixtures
- [ ] **grep-confirm 0 imports** of `RECENT_MEMORY_OPS`/`MEMORY_OPS_TIMELINE`/`TIME_TRAVEL_MARKS` → remove from `_fixtures.ts` + orphan types (`RecentMemoryOp`/`TimeTravelMark`/`MemoryOpTimelinePoint`)
  - Command: `grep -rn "RECENT_MEMORY_OPS\|MEMORY_OPS_TIMELINE\|TIME_TRAVEL_MARKS" frontend/src`

### 3.2 Vitest
- [ ] **`memoryService.test.ts` extend** — fetchOps: `?limit=50`, `?limit=&before=`, parses response, error detail
- [ ] **NEW `hooks/useMemoryOps.test.tsx`** — query key + signal forwarding
- [ ] **NEW `components/RecentMemoryOpsCard.test.tsx`** — real rows; null→`—`; cursor drops newer ops; loading/error/empty
- [ ] **NEW `components/TimeTravelScrubber.test.tsx`** — marks from ops; empty→no marks; onCursor on scrub

### 3.3 e2e
- [ ] **NEW `tests/e2e/memory/memory-ops.spec.ts`** — mock `GET /memory/ops`; assert rows + scrub filter; mock 403 → error render

### 3.4 Parent re-verify (Before-Commit item 7)
- [ ] **read all agent-changed code** + run ALL gates (incl. `check:mockup-fidelity`); don't trust agent report; pin English state copy

---

## Day 4 — Sweep + Closeout

### 4.1 Full sweep (parent re-verify, Before-Commit item 7)
- [ ] **Frontend gates** — `npm run lint` (NO `--silent`) 0 + `npm run build` (tsc 0) + `npm run test` (Vitest all green) + `npm run check:mockup-fidelity` (CSS byte-identical + HEX_OKLCH_BASELINE unchanged) + `npx playwright test memory-ops`
- [ ] **Read all agent-changed code** — wire correct, cursor filter real (not Potemkin), banners + fixtures removed, no orphan import, mockup classes verbatim, English state copy

### 4.2 Closeout docs
- [ ] **CHANGE-045** in `claudedocs/4-changes/feature-changes/`
- [ ] **progress.md** Day 0-4 + **retrospective.md** Q1-Q7
- [ ] **Checklist** all `[x]` (no deletion of unchecked)
- [ ] **Calibration** record (medium-frontend 0.65 + agent_factor 0.65; CAVEAT consecutive agent-delegated)
- [ ] **AD status**: `AD-Memory-OpsHistory-Backend` **fully closed** (backend 57.76 + frontend 57.77); next-phase-candidates.md
- [ ] **MEMORY subfile + pointer** + **CLAUDE.md lean**
- [ ] **Design note?** — NO (feature-continuation: data-wiring of shipped endpoint into mockup-ported components; no new contract / no 17.md change)

### 4.3 Ship
- [ ] **Commit mapping** Day-0 / data-layer / component-wire / tests+fixtures / closeout
- [ ] **Push + PR** (user-gated — explicit authorization required)
