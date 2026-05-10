---
File: docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-12-checklist.md
Purpose: Sprint 57.12 execution checklist — Agent Harness UI Suite (LoopVisualizer + MemoryViewer + SubagentTree) + Cat 11 SSE backend + Cat 3 NEW REST + AD-AdminTenant-Patch-Flake audit cycle.
Category: Frontend / Backend / Cat 1 + Cat 3 + Cat 11 / Audit cycle / Multi-domain
Scope: Phase 57 / Sprint 57.12

Created: 2026-05-10 (drafted post-plan approval)
Last Modified: 2026-05-10
Status: Draft (pending Day 0 commit)

Modification History (newest-first):
    - 2026-05-10: Initial creation (Sprint 57.12 — mirrors 57.11 5-day pattern)

Related:
    - sprint-57-12-plan.md (sibling plan — 10-section authority for this checklist)
    - sprint-57-11-checklist.md (structural template per sprint-workflow.md §Step 2)
---

# Sprint 57.12 — Checklist (Day 0-4)

> Branch: `feature/sprint-57-12-agent-harness-ui-suite`
> Calibration: `large multi-domain` 0.55 5th application
> Bottom-up ~25 hr → committed ~14 hr

---

## Day 0 — Setup + Branch + Pre-flight + 三-prong + Calibration

### 0.1 Branch creation
- [ ] **Create branch `feature/sprint-57-12-agent-harness-ui-suite` from main `0a46b86e`**
  - Verify clean working tree (`git status --short` = empty or `?? test-results/`)
  - DoD: `git branch --show-current` returns expected name
  - Verify command: `git rev-parse main && git log feature/sprint-57-12-agent-harness-ui-suite --oneline`

### 0.2 Pre-flight baseline capture (post Sprint 57.11)
- [ ] **Capture pytest baseline (1635 / 4 skipped)**
  - DoD: pytest count documented in progress.md Day 0 entry
  - Verify command: `cd backend && python -m pytest --collect-only -q 2>&1 | tail -3`
- [ ] **Capture Vitest baseline (119)**
  - DoD: Vitest count documented
  - Verify command: `cd frontend && npm test -- --run 2>&1 | tail -10`
- [ ] **Capture Playwright baseline (31)**
  - DoD: Playwright count documented
  - Verify command: `cd frontend && npx playwright test --list 2>&1 | tail -5`
- [ ] **Capture mypy baseline (strict 0/300)**
  - DoD: mypy 0 errors confirmed
  - Verify command: `cd backend && python -m mypy --strict src/ 2>&1 | tail -3`
- [ ] **Capture 9 V2 lints baseline (9/9 green)**
  - DoD: all 9 lints pass
  - Verify command: `cd backend && python scripts/lint/run_all.py`
- [ ] **Capture LLM SDK leak (0)**
  - DoD: `agent_harness/` no `import openai/anthropic`
  - Verify command: `cd backend && python -m pytest tests/lint/test_no_sdk_in_harness.py`

### 0.3 Day 0 三-prong verify (per AD-Plan-1+3+4 promoted rules)
- [ ] **Prong 1 Path Verify** — verify file paths in plan §File Change List
  - 24 NEW paths exist as 0 results (Glob): `backend/src/api/v1/memory.py` / `backend/src/api/v1/_schemas/memory.py` / `frontend/src/features/agent_harness/types.ts` / `frontend/src/features/agent_harness/services/memoryService.ts` / 3 hooks / 2 badges / 4 components / 2 pages / 8+ test files / 4 e2e specs
  - 11 MODIFIED paths exist as 1 result (Glob): `backend/src/agent_harness/subagent/tools.py` / `fork_executor.py` / `_metrics.py` / `chat/handler.py` / `api/v1/__init__.py` / `tests/integration/api/conftest.py` / `chat_v2/store/chatStore.ts` / `chat_v2/types.ts` / `ChatLayout.tsx` / `routes.config.ts` / `.claude/rules/testing.md`
  - DoD: D-PRE-N table in progress.md cataloguing path findings (0 RED expected per Day 0 探勘)
- [ ] **Prong 2 Content Verify** — grep plan §Technical Spec assertions
  - SubagentSpawned/Completed defined at events.py:301,308 ✅ confirmed (from plan-time探勘)
  - MemoryStore.list_recent / list_by_scope / list_by_time methods exist ✅ verify via grep
  - ForkExecutor.run_with_session signature ✅ verify
  - require_admin_role helper at platform_layer/auth/ ✅ verify
  - DoD: drift findings catalogued (expect 0-2 YELLOW given plan-time探勘 already done)
- [ ] **Prong 3 Schema Verify** — applies (US-7 touches tenants table; no NEW table)
  - tenants.code uniqueness constraint `uq_tenants_code` ✅ verify via grep migrations
  - DoD: schema findings cataloged

### 0.4 Calibration baseline confirmation
- [ ] **Document calibration class + multiplier in progress.md Day 0**
  - Class: `large multi-domain` 0.55 mid-band 5th application
  - 4-data-point window: 56.1=1.00 + 56.3=1.04 + 57.2=0.77 + 57.11=0.47; mean 0.82
  - KEEP 0.55 baseline per `When to adjust` 3-sprint rule
  - Bottom-up ~25 hr → committed ~14 hr

### 0.5 User decision points cleared (pre-confirmed via plan §Open questions)
- [ ] User-confirmed Q1 branch name = `feature/sprint-57-12-agent-harness-ui-suite`
- [ ] User-confirmed Q2 calibration = `large multi-domain` 0.55
- [ ] User-confirmed Q3 STRETCH e2e = allow defer to AD-Subagent-RealShip-E2E
- [ ] User-confirmed plan scope (Option A bundle: All 3 UI + Cat 11 backend + audit cycle 1 sprint)

### 0.6 Day 0 commit
- [ ] **Commit Day 0 baseline + plan + checklist**
  - Files: sprint-57-12-plan.md / sprint-57-12-checklist.md / progress.md (Day 0 entry)
  - Message: `chore(sprint-57-12, Day 0): plan + checklist + 三-prong baseline`
  - DoD: 1 commit on feature branch

---

## Day 1 — US-1 + US-2 Backend (Cat 11 SSE + Cat 3 REST)

### 1.1 US-1: Cat 11 ForkExecutor.event_emitter param
- [ ] **Add `event_emitter: Callable[[LoopEvent], Awaitable[None]] | None = None` to ForkExecutor.run_with_*** methods**
  - Files: `backend/src/agent_harness/subagent/fork_executor.py`
  - DoD: signature additive (param defaults None for backward-compat); existing callers compile
  - Verify: `python -m mypy --strict src/agent_harness/subagent/fork_executor.py`

### 1.2 US-1: 4 tool handlers emit Spawned + Completed
- [ ] **Wrap 4 handlers `spawn_subagent` / `delegate` / `multi_agent_query` / `direct_query` to emit events**
  - Files: `backend/src/agent_harness/subagent/tools.py`
  - Best-effort emit (try/except + log warning; no propagation to tool path)
  - Metadata: session_id / parent_id / subagent_role / prompt_summary[:200] / tenant_id (TraceContext)
  - SubagentCompleted adds: success / tokens_used / elapsed_ms / error_class
  - DoD: each handler emit pair (Spawned then Completed) verified via unit test
  - Verify: `python -m mypy --strict src/agent_harness/subagent/tools.py`

### 1.3 US-1: Chat router serialize_loop_event for 2 NEW event types
- [ ] **Update `serialize_loop_event` mapper for SubagentSpawned + SubagentCompleted**
  - Files: `backend/src/api/v1/chat/handler.py`
  - DoD: SSE frame test for both event types pass
  - Verify: grep `serialize_loop_event` in handler.py and confirm 22-event coverage

### 1.4 US-1: 8 unit + integration tests
- [ ] **NEW `tests/unit/agent_harness/subagent/test_subagent_sse_emission.py` ≥ 6 unit tests**
  - Cases: Spawned + Completed emitted; emitter=None no-op; emitter raises does not break tool; metadata fields populated; parent_id correct; tenant_id propagation
  - Verify: `pytest tests/unit/agent_harness/subagent/test_subagent_sse_emission.py -v`
- [ ] **NEW `tests/integration/agent_harness/test_subagent_sse_e2e.py` ≥ 2 real-LLM integration tests**
  - Cases: 2-turn chat triggers spawn_subagent → SSE contains Spawned then Completed; SubagentCompleted has actual token count
  - Marked `@pytest.mark.real_llm` (bypassed unless `--real-llm` flag)
  - Verify: `pytest tests/integration/agent_harness/test_subagent_sse_e2e.py -v --real-llm` (manual run)

### 1.5 US-2: Cat 3 NEW `/api/v1/memory` router
- [ ] **NEW `backend/src/api/v1/memory.py` with 3 endpoints**
  - `GET /recent?limit=50&offset=0&layer={layer}`
  - `GET /scope/{layer}/{scope_id}?limit=50&offset=0`
  - `GET /by-time/{layer}/{time_scale}?limit=50&offset=0`
  - All endpoints: `Depends(get_current_tenant)` + `Depends(require_admin_role("memory:read"))` + `Depends(get_memory_store)`
  - DoD: endpoints registered; auth chain enforced
  - Verify: `python -m mypy --strict src/api/v1/memory.py`

### 1.6 US-2: NEW Pydantic schemas
- [ ] **NEW `backend/src/api/v1/_schemas/memory.py`**
  - `MemoryEntryResponse` / `PaginatedMemoryResponse` / `MemoryLayer` enum / `MemoryTimeScale` enum
  - DoD: schemas validate against MemoryStore ABC return types
  - Verify: `python -m mypy --strict src/api/v1/_schemas/memory.py`

### 1.7 US-2: Register router in v1 __init__.py
- [ ] **Modify `backend/src/api/v1/__init__.py` to register memory router**
  - DoD: `from .memory import router as memory_router` + `include_router`
  - Verify: `pytest tests/integration/api/test_memory_recent.py::test_recent_200_path` (one minimal smoke)

### 1.8 US-2: 11 backend tests (4 integration files + 1 unit schema)
- [ ] **NEW `tests/unit/api/test_memory_schema.py` ≥ 3 tests**
  - Cases: MemoryEntryResponse serializes correctly; MemoryLayer enum reject invalid; MemoryTimeScale enum reject invalid
- [ ] **NEW `tests/integration/api/test_memory_recent.py` ≥ 4 tests**
  - Cases: 200 with paginated items; 401 no auth; 403 non-admin; cross-tenant denied
- [ ] **NEW `tests/integration/api/test_memory_scope.py` ≥ 3 tests**
  - Cases: 200 with layer + scope_id; 404 unknown scope_id; layer enum reject
- [ ] **NEW `tests/integration/api/test_memory_by_time.py` ≥ 3 tests**
  - Cases: 200 by time_scale; time_scale enum reject; layer enum reject
  - Verify: `pytest tests/integration/api/test_memory_*.py -v`

### 1.9 Day 1 wrap
- [ ] **Day 1 progress entry** — backend pytest delta + 9 V2 lints 9/9 + mypy 0
- [ ] **Day 1 commit**: `feat(sprint-57-12, Day 1): US-1 Cat 11 SSE emission + US-2 Cat 3 REST read facade`

---

## Day 2 — US-3 Frontend Infra + US-4 LoopVisualizer + US-5 MemoryViewer Page Wrap

### 2.1 US-3: types.ts
- [ ] **NEW `frontend/src/features/agent_harness/types.ts`**
  - Types: `MemoryEntry` / `MemoryLayer` / `MemoryTimeScale` / `SubagentSpawnedEvent` / `SubagentCompletedEvent`
  - DoD: tsc strict 0
  - Verify: `cd frontend && npx tsc --noEmit`

### 2.2 US-3: memoryService.ts
- [ ] **NEW `frontend/src/features/agent_harness/services/memoryService.ts`**
  - 3 fetcher functions per CONVENTION.md §6 fetchWithAuth pattern
  - DoD: fetchWithAuth from authService.ts (single-source)
  - Verify: grep `import.*fetchWithAuth` in memoryService.ts

### 2.3 US-3: 3 TanStack hooks
- [ ] **NEW `useMemoryRecent.ts` + `useMemoryByScope.ts` + `useMemoryByTime.ts`**
  - `*_QUERY_KEY_BASE` exports per CONVENTION.md §5 single-source
  - DoD: each hook's queryKey shape verified via test

### 2.4 US-3: 2 shared badge components
- [ ] **NEW `MemoryScopeBadge.tsx` (5 variants per layer)**
  - Variants: system=indigo / tenant=blue / role=teal / user=green / session=amber per STYLE.md §3
  - `data-testid="memory-scope-badge-{layer}"`
- [ ] **NEW `SubagentStatusBadge.tsx` (3 variants)**
  - Variants: running=blue / success=green / error=red
  - `data-testid="subagent-status-badge-{status}"`

### 2.5 US-3: ≥ 8 Vitest tests
- [ ] **memoryService URL building + 4xx/5xx error tests** (3 tests)
- [ ] **3 hook tests (queryKey + fetcher invocation)**
- [ ] **2 badge component tests (5-variant + 3-variant)**
  - Verify: `cd frontend && npm test -- --run agent_harness`

### 2.6 US-4: LoopVisualizer dual-mount component
- [ ] **NEW `frontend/src/features/agent_harness/components/LoopVisualizer.tsx`**
  - `<LoopVisualizer mode="inline" />` + `<LoopVisualizer mode="standalone" />`
  - Consumes `useChatStore` `rawEvents`; groups into per-turn nested structure
  - Renders 22 LoopEvent types (Thinking / LLMRequested / LLMResponded / ToolCallRequested / ToolCallExecuted / ToolCallFailed / MemoryAccessed / ContextCompacted / PromptBuilt / VerificationPassed / VerificationFailed / GuardrailTriggered / TripwireTriggered / SubagentSpawned / SubagentCompleted / StateCheckpointed / ErrorRetried / SpanStarted / SpanEnded / MetricRecorded / TurnStarted / LoopStarted / LoopCompleted / LoopTerminated / ApprovalRequested / ApprovalReceived)
  - Visual encoding per STYLE.md §3 + §4 (red border failed / amber border warn / muted gray success)
  - DoD: tsc strict 0; storybook visual confirm
  - Verify: `cd frontend && npx tsc --noEmit`

### 2.7 US-4: standalone /loop-debug page wrap
- [ ] **NEW `frontend/src/pages/loop-debug/index.tsx`**
  - AppShellV2 + auth gate (`require_admin_role("debug:read")`)
  - Reads `?session_id=X` query param → loads chatStore for that session
  - Empty state "session not found / not currently running"
  - DoD: route renders + 401/403 redirects + empty state

### 2.8 US-5: standalone /memory page wrap (initial scaffold)
- [ ] **NEW `frontend/src/pages/memory/index.tsx`**
  - AppShellV2 + auth gate (`require_admin_role("memory:read")`)
  - 2-tab Routes per CONVENTION.md §3: `/memory/recent` (default) + `/memory/by-scope`
  - DoD: route renders both tabs (stubs OK at this point)

### 2.9 Day 2 wrap
- [ ] **Day 2 progress entry** — frontend Vitest delta + tsc strict 0
- [ ] **Day 2 commit**: `feat(sprint-57-12, Day 2): US-3 frontend infra + US-4 LoopVisualizer + US-5 page wrap`

---

## Day 3 — US-5 Complete + US-6 SubagentTree + US-7 Audit Cycle

### 3.1 US-5: MemoryRecentList component
- [ ] **NEW `MemoryRecentList.tsx`**
  - Consumes `useMemoryRecent`
  - Columns: layer (MemoryScopeBadge), scope_id, key, value (truncated 80 + tooltip), last_accessed, expires_at
  - Pagination 50/page (next/prev disabled at boundaries)
  - Empty state + error state with retryClicked StrictMode-safe
  - Verify: `npm test -- --run MemoryRecentList`

### 3.2 US-5: MemoryByScopeBrowser component
- [ ] **NEW `MemoryByScopeBrowser.tsx`**
  - 5-card grid (one per layer)
  - Click layer card → drill into scope_id list → detail panel for entries
  - Verify: `npm test -- --run MemoryByScopeBrowser`

### 3.3 US-5: ≥ 6 Vitest tests
- [ ] **MemoryRecentList renders 5 layer badges + pagination boundaries + empty + error retry** (4 tests)
- [ ] **MemoryByScopeBrowser renders 5 cards + drill-in expands detail** (2 tests)

### 3.4 US-6: chatStore subagents slice
- [ ] **Modify `frontend/src/features/chat_v2/store/chatStore.ts`**
  - NEW state field: `subagents: SubagentNode[]`
  - NEW reducers: `appendSubagent` / `updateSubagent` / `clearSubagents`
  - DoD: tsc strict 0; reducer tests pass

### 3.5 US-6: chatStore.mergeEvent SSE 3-edit (per CONVENTION.md §7)
- [ ] **Edit 1**: types.ts — `KNOWN_LOOP_EVENT_TYPES` add `subagent_spawned` + `subagent_completed`
- [ ] **Edit 2**: types.ts — `LoopEvent` type union extends with SubagentSpawnedEvent + SubagentCompletedEvent
- [ ] **Edit 3**: chatStore.ts mergeEvent reducer — case `subagent_spawned` → appendSubagent; case `subagent_completed` → updateSubagent
- [ ] **AD-Frontend-SSE-Silent-Drop-Fix sentinel test** — chatStore receiving subagent_spawned/_completed routes to subagents array (not silently dropped)

### 3.6 US-6: SubagentTree component
- [ ] **NEW `SubagentTree.tsx`**
  - Consumes `useChatStore` `subagents` slice
  - Tree visual: parent→child links from `parent_id`; depth cap 5 (defensive)
  - Each node: SubagentStatusBadge + prompt_summary (60 chars + tooltip) + tokens_used + elapsed_ms + error_class on error
  - Verify: `npm test -- --run SubagentTree`

### 3.7 US-6: ≥ 5 Vitest tests
- [ ] **appendSubagent + updateSubagent (running→success + running→error) + mergeEvent SSE branch + tree depth-N**

### 3.8 US-6 + US-4: Mount inline panels in chat-v2 ChatLayout
- [ ] **Modify `frontend/src/features/chat_v2/components/ChatLayout.tsx`**
  - Mount `<LoopVisualizer mode="inline" />` and `<SubagentTree />` in side panel area
  - DoD: chat-v2 page renders without regression (Vitest sentinel pass)

### 3.9 US-7: AD-AdminTenant-Patch-Flake fix
- [ ] **Modify or create `backend/tests/integration/api/conftest.py` autouse cleanup fixture**
  - Scope: admin_tenant test files
  - On teardown: delete tenants WHERE code LIKE 'TEST_%' OR code IN (<known test codes>)
  - Per 53.7 §Risk Class C SAVEPOINT pattern
  - DoD: 9/9 admin_tenant_patch tests pass × 3 consecutive runs
  - Verify: `pytest tests/integration/api/test_admin_tenant_patch.py` × 3 runs all pass

### 3.10 US-7: Document pattern in `.claude/rules/testing.md`
- [ ] **Extend Risk Class C examples in testing.md**
  - DoD: pattern reference points back to 53.7 origin

### 3.11 Day 3 wrap
- [ ] **Day 3 progress entry** — Vitest +20 cumulative + AD-AdminTenant-Patch-Flake closure verified × 3 runs
- [ ] **Day 3 commit**: `feat(sprint-57-12, Day 3): US-5 MemoryViewer complete + US-6 SubagentTree + US-7 audit cycle fix`

---

## Day 4 — US-8 Routing + e2e + Closeout

### 4.1 US-8: routes.config.ts wire
- [ ] **Modify `frontend/src/routes.config.ts` to register /memory + /loop-debug**
  - Both lazy import + admin-gated
  - 11 → 13 entries
  - DoD: `npm run build` + bundle main size noted (vs 295.14 kB ceiling per AD-Bundle-Size-285kB carryover)

### 4.2 US-8: 4 Playwright e2e specs
- [ ] **NEW `loop-debug-standalone.spec.ts` ≥ 1 test**
  - Cases: page renders + auth gate redirect for non-admin
- [ ] **NEW `chat-v2-loop-inline.spec.ts` ≥ 1 test**
  - Cases: chat-v2 page mounts LoopVisualizer in side panel
- [ ] **NEW `memory-page.spec.ts` ≥ 1 test**
  - Cases: /memory page mounts + 2-tab navigation + auth gate
- [ ] **NEW `chat-v2-subagent-inline.spec.ts` ≥ 1 test**
  - Cases: chat-v2 mounts SubagentTree (page.route() mock SSE per `feedback_e2e_network_mocking_pattern`)
- [ ] **STRETCH (allow defer)** — 1 SSE-injection real-flow chat-v2 spawn_subagent e2e
  - If brittle → log AD-Subagent-RealShip-E2E carryover

### 4.3 US-8: chat-v2 8/8 regression sentinel
- [ ] **Run chat-v2 e2e suite all 8/8 pass**
  - Verify: `cd frontend && npx playwright test chat-v2`

### 4.4 Full validation sweep
- [ ] **pytest 1635 → 1652+ (target +17)**
  - Verify: `cd backend && python -m pytest`
- [ ] **mypy strict 0 (Linux + Windows)**
  - Verify: `cd backend && python -m mypy --strict src/`
- [ ] **9 V2 lints 9/9 green**
  - Verify: `cd backend && python scripts/lint/run_all.py`
- [ ] **Vitest 119 → 145+ (target +26)**
  - Verify: `cd frontend && npm test -- --run`
- [ ] **Playwright 31 → 35+ (target +4)**
  - Verify: `cd frontend && npx playwright test`
- [ ] **Vite build succeed; main bundle size noted**
  - Verify: `cd frontend && npm run build`
- [ ] **ESLint silent**
  - Verify: `cd frontend && npm run lint`
- [ ] **LLM SDK leak 0**
  - Verify: `cd backend && python -m pytest tests/lint/test_no_sdk_in_harness.py`

### 4.5 Retrospective.md (Q1-Q7)
- [ ] **NEW `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-12/retrospective.md`**
  - Q1 What went well
  - Q2 Time tracking — actual / committed (~14 hr) ratio
  - Q3 What surprised us (D-PRE delta)
  - Q4 Open items / carry-forward (NEW carryover ADs)
  - Q4.1 Closeout user decision points
  - Q5 Next-sprint candidates (rolling planning — list candidates only, NO 57.13 plan pre-write)
  - Q6 Calibration verification (5th `large multi-domain` 0.55 application result)
  - Q7 Design note Day 4 closeout extract — **N/A SKIP** per 57.8+57.9+57.10+57.11 pattern (feature ship NOT spike)

### 4.6 Memory snapshot
- [ ] **NEW `claudedocs/.../memory/project_phase57_12_agent_harness_ui_suite.md`**
  - Mirror 57.11 / 57.10 memory snapshot pattern
  - Include: 8 USs delivered + test deltas + AD closures + carryover ADs + calibration result
- [ ] **Update MEMORY.md index with new entry**

### 4.7 Doc syncs (3/4 in sprint; SITUATION + CLAUDE.md DEFERRED to post-merge closeout PR)
- [ ] **`.claude/rules/sprint-workflow.md` — calibration matrix +1 row 5th `large multi-domain` 0.55 data point**
- [ ] **This plan + checklist header MHist closeout entry**
- [ ] **`docs/03-implementation/agent-harness-planning/16-frontend-design.md` — V2 Ship Timeline 7/N → 8/N + 3 internal-debug UIs promoted to shipped**
- [ ] DEFERRED post-merge: `claudedocs/6-ai-assistant/prompts/SITUATION-V2-SESSION-START.md` Header Last Updated + Previous milestone +Sprint 57.12 row + § 8 carryover updates

### 4.8 PR open + closeout sync
- [ ] **Push branch + open PR with V2 紀律 9 項 self-check + retrospective Q4.1 user decision points**
- [ ] **Verify all 5 active CI checks green** (Backend E2E / E2E Test Summary / Frontend E2E chromium / Lint+Type+Test PG16 / v2-lints)
- [ ] **Squash merge after CI green** (per solo-dev policy review_count=0)

### 4.9 Day 4 closeout user decision points
- [ ] **Surface to user in PR description / closeout sync**:
  - Bundle size change vs 285 kB ceiling per AD-Bundle-Size-285kB
  - Any STRETCH e2e deferred → AD-Subagent-RealShip-E2E carryover
  - Calibration ratio (actual / committed) — propose 0.55→0.40 lift if 5th data point continues under 0.7

---

## 重要備註

### Rolling planning 紀律自檢(每 day 結束 + Day 4 closeout 必檢)
- ☑ 沒預寫 57.13 sprint plan(Phase 57.13+ candidates 只列候選名)
- ☑ 沒跳過 plan/checklist 直接 code(Day 0 plan + checklist 完整;Day 1 起 code)
- ☑ 沒刪除未勾選 [ ] 項(用 [x] 完成 / 🚧 阻塞 / [DEFERRED] 延後標記)
- ☑ 沒在 retrospective 寫具體未來 sprint task(Q5 只列候選)

### V2 紀律 9 項自檢(每 commit + 每 PR — per plan §Acceptance Criteria)
1. ✅ Server-Side First — Cat 3 REST tenant_id + RLS;Cat 11 emission tenant_id propagation
2. ✅ LLM Provider Neutrality — agent_harness 0 SDK import(check_no_sdk_in_harness lint)
3. ✅ CC Reference 不照搬 — internal debug UIs server-side rendered(NOT CC-style local fs)
4. ✅ 17.md Single-source — 0 NEW contracts / ABC / LoopEvents / migrations
5. ✅ 11+1 範疇 — Cat 11 + Cat 3 + Cat 1 demarcation 清楚
6. ✅ AP-1/2/3/4/6/9 — no Pipeline pretending Loop / no orphan / no scattering / no Potemkin / no premature abstraction / verification still active
7. ✅ Sprint workflow — Day 0 → Plan → Checklist → Code → Update → Progress doc → Retrospective
8. ✅ File header MHist — 1-line max per `.claude/rules/file-header-convention.md`
9. ✅ Multi-tenant — tenant_id NN + RLS + fetchWithAuth + RBAC

### Sprint 57.7 D19 + 57.8 D13 + 57.9 D-PRE-16 + 57.10 D-PRE-13 + 57.11 D-PRE-2 cascade lessons 強制執行
- ✅ CONVENTION.md §7 SSE 3-edit checklist applied to SubagentSpawned/Completed (US-6)
- ✅ retryClicked StrictMode-safe pattern in MemoryRecentList error retry (US-5)
- ✅ Page-level h1 in /memory + /loop-debug standalone pages
- ✅ seedAuthJwt beforeEach in 4 NEW e2e specs (auth-gated routes)
- ✅ chatStore.subagents slice avoids silent drop (sentinel test in US-6 §3.5)

### Open Items / Carry-forward(填入 retrospective Q4 + Q4.1)
- AD-Subagent-RealShip-E2E (if STRETCH deferred per Q3 user decision)
- AD-Bundle-Size-285kB-Carryover (continued from 57.11; main may grow further with 4 NEW lazy chunks)
- AD-Cat11-Multiturn-Full (54.2 carryover; partial close via metadata in US-1; full multiturn loop pulling from mailbox NOT shipped)
- AD-Cat11-ParentCtx-Full (54.2 carryover; partial close via parent_id in US-1; full Cat 7 checkpoint inheritance NOT shipped)
- (Future) AD-Memory-AccessLog-Persist if compliance audit requires access trail

### Sprint workflow §Step 5 expansion candidate
- 5th `large multi-domain` 0.55 data point — track Day 4 retrospective Q6 ratio; if continued under 0.7 propose lift
- 8-Point Quality Gate N/A this sprint (feature ship not spike)
