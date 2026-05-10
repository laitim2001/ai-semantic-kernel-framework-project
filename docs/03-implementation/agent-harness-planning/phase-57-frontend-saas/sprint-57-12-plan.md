---
File: docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-12-plan.md
Purpose: Sprint 57.12 plan — Agent Harness UI Suite (LoopVisualizer + MemoryViewer + SubagentTree) bundled with Cat 11 backend SSE emission (closes AD-Cat11-SSEEvents 54.2 carryover), Cat 3 NEW REST `/api/v1/memory` read facade, and AD-AdminTenant-Patch-Flake audit cycle. Phase 57+ Frontend SaaS 8/N.
Category: Frontend / Backend / Cat 1 + Cat 3 + Cat 11 + Audit cycle / Multi-domain
Scope: Phase 57 / Sprint 57.12

Description:
    Phase 57+ SaaS Frontend 8/N expansion. Sprint 57.11 closed Verification
    Real Ship + AD-Frontend-SSE-Silent-Drop-Fix bundle (PR #125 main
    `923e808b`; closeout PR #126 main `0a46b86e`). Sprint 57.12 picks up
    Phase 57.12+ candidate (a) Agent Harness UI suite combined with (c)
    AD-AdminTenant-Patch-Flake audit cycle per user 2026-05-10 Option A
    bundle decision.

    The suite covers all 3 missing internal-debug UIs from `16-frontend-design.md`
    that were deferred since Sprint 49.1 placeholder ("Coming in Phase 51+
    — Loop / Memory / Subagent visualization."):
    - **LoopVisualizer**: TAO/ReAct state machine tree consuming the 22-type
      LoopEvent stream emitted by Cat 1 AgentLoop (50.2 SSE serializer);
      mounts chat-v2 inline (compact panel) + standalone `/loop-debug` page
      (AppShellV2 + auth gate full-screen layout) — same component, two contexts.
    - **MemoryViewer**: Standalone `/memory` page (AppShellV2 + auth gate
      + 2-tab Routes `/memory/recent` recent access list +
      `/memory/by-scope` 5-scope × 3-time-scale browser) consuming NEW
      `/api/v1/memory` read facade over Cat 3 5-layer stores (no NEW table —
      direct read of existing memory_system/tenant/role/user/session ORM).
    - **SubagentTree**: chat-v2 inline panel consuming NEW Cat 11 SSE
      `SubagentSpawned`/`SubagentCompleted` events (closes AD-Cat11-SSEEvents
      from Sprint 54.2 retrospective); parent→child tree links derived from
      `parent_session_id` in event metadata.

    Backend pre-requisites are bundled to avoid AP-4 Potemkin Features
    (UI mounted with no data source):
    - Cat 11 backend (US-1): ForkExecutor + 4 subagent tool handlers
      (`spawn_subagent` / `delegate` / `multi_agent_query` / `direct_query`)
      emit `SubagentSpawned` + `SubagentCompleted` events through the
      LoopState event channel — closes AD-Cat11-SSEEvents permanently.
    - Cat 3 backend (US-2): NEW `/api/v1/memory` REST endpoints
      `GET /recent` (cross-scope recent access list paginated) +
      `GET /scope/{scope}/{scope_id}` (scope-specific browser) +
      `GET /by-time/{layer}/{time_scale}` (time-scale filter) — NO write
      endpoints (read facade only); Cat 3 ABC `MemoryStore.list_*()` extended
      where missing.
    - Audit cycle (US-7): AD-AdminTenant-Patch-Flake fix per 53.7 §Risk
      Class C SAVEPOINT pattern — `tests/integration/api/conftest.py` autouse
      fixture cleanup of test-DB rows by tenant_code prefix to eliminate
      `UniqueViolationError uq_tenants_code` flake (3/9 tests fail post-57.11
      pollution from `BOTH_FIELDS` / `BEFORE_PATCH` / etc. unique codes).

    Closes:
    - 16-frontend-design.md §Internal Debug UIs priority slot 3/3 (loop
      Sprint 51 placeholder + memory Sprint 51 placeholder + subagent
      Sprint 54 placeholder all promote to real ship)
    - AD-Cat11-SSEEvents (logged Sprint 54.2 retrospective; emission from
      ForkExecutor + tool handlers — backend code change required)
    - AD-Cat11-Multiturn (logged Sprint 54.2 retrospective; **partial close**
      for SSE event metadata fields needed by SubagentTree, NOT the full
      multiturn loop pulling from mailbox each iteration — that remains
      Phase 58+ deferred)
    - AD-Cat11-ParentCtx (logged Sprint 54.2 retrospective; **partial close**
      via `parent_session_id` propagation in `SubagentSpawned.parent_id`
      metadata, NOT the full Cat 7 checkpoint load inheritance)
    - AD-AdminTenant-Patch-Flake (logged Sprint 57.11 retrospective; recurring
      57.8+57.9+57.10+57.11 dev-DB pollution pattern)

Created: 2026-05-10 (drafted Day 0 fresh against main `0a46b86e` after
    user 2026-05-10 Option A bundle decision; Day 0 三-prong: 4 D-PRE-N
    findings catalogued — 0 RED requiring abort + 1 RED scope-confirming
    + 2 YELLOW scope-confirming + 1 GREEN already-ready)
Last Modified: 2026-05-10
Status: ✅ COMPLETE (Day 4 closeout — 8/8 USs; ratio ~0.75; PR pending merge)

Modification History (newest-first):
    - 2026-05-10: Sprint 57.12 Day 4 closeout — 8/8 USs shipped; pytest 1635→1654 / Vitest 119→168 / Playwright 31→37; ratio ~0.75 (large multi-domain 5th); closes AD-Cat11-SSEEvents + AD-AdminTenant-Patch-Flake
    - 2026-05-10: Initial creation (Sprint 57.12 drafting; user 2026-05-10
      confirmed Option A bundle: All 3 UI + audit cycle + Cat 11 backend
      bundle; LoopVisualizer mount = inline + standalone; MemoryViewer = read
      facade no NEW table; SubagentTree = chat-v2 inline only)

Related:
    - 16-frontend-design.md §Internal Debug UIs (Loop / Memory / Subagent)
    - sprint-57-11-plan.md (structural template per sprint-workflow.md §Step 1
      — most recent completed sprint; mirror 10 sections + 5 days)
    - frontend/CONVENTION.md (NEW Sprint 57.10; §1 Page Architecture for
      standalone /memory + /loop-debug pages; §7 SSE Event 3-edit checklist
      for SubagentSpawned/SubagentCompleted + LoopVisualizer event types)
    - frontend/STYLE.md (NEW Sprint 57.10; §3 Risk Badge Palette for memory
      scope badges; §4 Tree typography for SubagentTree + LoopVisualizer)
    - .claude/rules/frontend-react.md (Tailwind / shadcn / Zustand / TanStack
      Query rules + Sprint 57.10 cross-ref)
    - .claude/rules/backend-python.md (FastAPI router / async / type hints)
    - .claude/rules/multi-tenant-data.md (NEW /api/v1/memory tenant_id rule;
      Cat 3 layer tables already RLS-enforced)
    - .claude/rules/testing.md (53.7 §Risk Class C SAVEPOINT pattern for
      US-7 audit cycle fix)
    - 17-cross-category-interfaces.md §4 LoopEvent (22 events single-source
      — already includes SubagentSpawned L301 / SubagentCompleted L308 /
      MemoryAccessed L170 / Thinking L111 — NO new contracts this sprint)
    - 17-cross-category-interfaces.md §Cat 3 (MemoryStore ABC); §Cat 11
      (Subagent ABC) — both used as-is, NO new ABC methods
    - AD-Cat11-SSEEvents (logged 54.2; closes via US-1)
    - AD-Cat11-Multiturn (logged 54.2; partial close via US-1 metadata)
    - AD-Cat11-ParentCtx (logged 54.2; partial close via US-1 parent_id)
    - AD-AdminTenant-Patch-Flake (logged 57.11; closes via US-7)
---

# Sprint 57.12 — Agent Harness UI Suite + Cat 11 SSE + Cat 3 REST + Admin Tenant Audit Cycle (Frontend 8/N)

## Sprint Goal

Promote the 3 internal-debug UIs from Sprint 49.1 placeholder ("Coming in
Phase 51+ — Loop / Memory / Subagent visualization.") to production-grade
real-ship — combining **LoopVisualizer** (chat-v2 inline panel + standalone
`/loop-debug` AppShellV2 page consuming Cat 1 AgentLoop SSE 22-event stream
end-to-end), **MemoryViewer** (standalone `/memory` AppShellV2 page + 2-tab
Routes consuming NEW `/api/v1/memory` read facade over Cat 3 5-layer stores
without NEW persistence table), and **SubagentTree** (chat-v2 inline panel
consuming NEW Cat 11 `SubagentSpawned`+`SubagentCompleted` SSE events with
`parent_session_id` derived tree links). Backend prerequisites bundled:
**Cat 11 SSE event emission** (closes AD-Cat11-SSEEvents 54.2 carryover) +
**Cat 3 NEW REST endpoints** (`GET /recent` + `GET /scope/{scope}/{scope_id}`
+ `GET /by-time/{layer}/{time_scale}`) + **AD-AdminTenant-Patch-Flake fix**
(autouse cleanup fixture per 53.7 §Risk Class C SAVEPOINT pattern).

Closes 16.md §Internal Debug UIs priority slot 3/3 + AD-Cat11-SSEEvents +
AD-Cat11-Multiturn (partial — metadata only) + AD-Cat11-ParentCtx (partial
— parent_id only) + AD-AdminTenant-Patch-Flake.

---

## Background

### Why agent harness UIs now (Phase 57.12 candidate (a) Option A bundle)

Sprint 57.11 closeout retrospective Q5 enumerated 5 candidates for Phase
57.12+; user 2026-05-10 selected **Option A bundle (a)+(c) complement**:

1. **Pattern reuse compound ROI** — Sprint 57.7 (IAM + AppShellV2 precursor) +
   Sprint 57.8 (AppShellV2 + auth gate ship) + Sprint 57.9 (governance +
   TanStack pattern) + Sprint 57.10 (CONVENTION.md + STYLE.md codify) +
   Sprint 57.11 (Verification real ship + chat-v2 inline panel pattern)
   built infrastructure that this sprint inherits FREE. Per Sprint 57.11
   Day 4 evidence: pattern reuse acceleration sustained ~50% velocity vs
   greenfield. Three internal-debug UIs share the chat-v2 inline panel
   pattern (verification panel template) and standalone `/foo` AppShellV2
   wrap pattern (verification + governance + admin-tenants templates).
2. **Backend gaps must close to avoid Potemkin Features (AP-4)** — UI without
   data source is V2 紀律 1st-order violation. Day 0 探勘 confirmed:
   - Cat 11 SubagentSpawned/Completed events **structurally defined** in
     `_contracts/events.py:301,308` (17.md §4 single-source compliant) but
     `subagent/tools.py:19-20` docstring says "if SSE event emission is
     required, that's a separate concern handled by..." → **0 emission
     today**. AD-Cat11-SSEEvents (54.2 carryover) must close via US-1.
   - Cat 3 Memory has 5 layer ABC + repo (11 files in
     `agent_harness/memory/`) but `backend/src/api/**/memory*.py` does NOT
     exist → **0 frontend-accessible REST endpoint**. NEW `/api/v1/memory`
     read facade (US-2) is mandatory.
3. **Calibration class continuity** — Sprint 57.11 was 4th `large
   multi-domain` 0.55 data point (ratio 0.47); 4-data-point mean **0.82**
   at lower edge of [0.85, 1.20] band. Sprint 57.12 is genuine multi-domain
   (Cat 11 backend + Cat 3 backend + 3 frontend pages + audit cycle) → 5th
   data point with same 0.55 multiplier per `When to adjust` 3-sprint rule
   (KEEP baseline; if continued under 0.7 → propose 0.55→0.40 lift).
4. **AD-AdminTenant-Patch-Flake recurring pattern closure** — 4 consecutive
   sprints (57.8+57.9+57.10+57.11) hit dev-DB pollution requiring
   manual remediation (docker exec + WORM trigger toggle in 57.10 + manual
   row delete in 57.11). Per Sprint 53.7 §Risk Class C and `.claude/rules/
   testing.md`, autouse SAVEPOINT cleanup is the V2 idiom — bundle with the
   feature ship since same backend test infra is touched.

### Internal-debug UIs are admin-only (auth gate + RBAC)

Per 16-frontend-design.md §Internal Debug UIs section + Sprint 57.7 IAM
foundation:
- LoopVisualizer standalone `/loop-debug` requires admin role (`debug:read`)
- MemoryViewer `/memory` requires admin role (`memory:read`)
- SubagentTree chat-v2 inline is visible to ALL chat-v2 users (no extra
  gate; same as VerificationPanel) — but the underlying SSE events are
  already authenticated through chat-v2 SSE stream tenant_id

### Single-source contracts preserved (17.md §4 LoopEvent)

Day 0 探勘 D-PRE-1 verified `_contracts/events.py` already includes 22
LoopEvent subclasses including SubagentSpawned (L301) + SubagentCompleted
(L308) + MemoryAccessed (L170) + Thinking (L111) + ContextCompacted (L180)
+ etc. **NO new LoopEvent types** added this sprint; only emission
side-effects in `subagent/`. 17.md §4 NEW contracts count = **0**.

For NEW REST endpoints (Cat 3), 17.md §3 (Cat 3 Memory) ABC `MemoryStore`
already declares `list_recent()` / `list_by_scope()` / `list_by_time()`
(used by retrieval engine internally); `/api/v1/memory` REST facade simply
exposes these as HTTP — NO new ABC methods. 17.md NEW ABC count = **0**.

### Why no NEW persistence table (per AP-6 YAGNI)

User decision rejected `memory_access_log` audit table (Option B in scope
question). Rationale: Cat 3 already persists memory entries in 5-layer
tables; `/api/v1/memory` is a read facade not an audit log. If compliance
audit needs access trail later, add then (AP-6 — don't build for hypothetical
future). 17.md §0 NEW Alembic migrations count = **0** (vs Sprint 57.11 = 1
for verification_log).

---

## User Stories

### US-1: Cat 11 backend — emit SubagentSpawned + SubagentCompleted SSE events (closes AD-Cat11-SSEEvents)

**As a** chat-v2 user observing a multi-agent workflow,
**I want to** see real-time SSE events when subagents are spawned and
completed by the orchestrator,
**so that** the SubagentTree UI (US-6) and any future agent observability
tooling has authentic data.

**Acceptance criteria**:
1. `agent_harness/subagent/tools.py` — 4 tool handlers
   (`spawn_subagent_handler` / `delegate_handler` / `multi_agent_query_handler`
   / `direct_query_handler`) emit `SubagentSpawned` event when child session
   created and `SubagentCompleted` event when child session ends (success or
   error).
2. `agent_harness/subagent/fork_executor.py` — `ForkExecutor.run_with_*`
   methods inject events into the parent loop's event channel through a
   new `event_emitter: Callable[[LoopEvent], Awaitable[None]] | None = None`
   parameter (None = no-op for unit-test backwards compat).
3. Event metadata fields:
   - `SubagentSpawned`: `session_id`, `parent_id` (parent session_id),
     `subagent_role` (from tool spec), `prompt_summary` (first 200 chars),
     `tenant_id` (from TraceContext per 57.11 D-PRE-4 pattern).
   - `SubagentCompleted`: `session_id`, `parent_id`, `success: bool`,
     `tokens_used`, `elapsed_ms`, `error_class: str | None`, `tenant_id`.
4. Chat router `_stream_loop_events` recognizes 2 NEW event types via
   `serialize_loop_event()` mapper — frontend-side `KNOWN_LOOP_EVENT_TYPES`
   set updated (per CONVENTION.md §7 3-edit pattern).
5. ≥ 6 unit tests + 2 integration tests:
   - Unit: ForkExecutor emits Spawned then Completed; emitter=None no-op;
     emitter raises does not break tool execution; metadata fields present;
     parent_id correctly populated; tenant_id propagation.
   - Integration: Real-LLM 2-turn chat triggers spawn_subagent → SSE stream
     contains SubagentSpawned then SubagentCompleted; SubagentCompleted
     receives subagent's actual token count.

**File touchpoints**:
- `backend/src/agent_harness/subagent/tools.py` (M)
- `backend/src/agent_harness/subagent/fork_executor.py` (M)
- `backend/src/agent_harness/orchestrator_loop/_metrics.py` (M — already
  references SubagentSpawned per Day 0 D-PRE-1; verify wire-up correct)
- `backend/src/api/v1/chat/handler.py` (M — serialize_loop_event mapper)
- `backend/tests/unit/agent_harness/subagent/test_subagent_sse_emission.py`
  (NEW)
- `backend/tests/integration/agent_harness/test_subagent_sse_e2e.py` (NEW —
  marked `@pytest.mark.real_llm`; bypassed unless `--real-llm` flag)

---

### US-2: Cat 3 backend — NEW `/api/v1/memory` REST read facade (3 endpoints)

**As an** admin investigating memory layer state,
**I want to** browse memory entries by scope (system/tenant/role/user/session)
and time scale (永久 / 季 / 天) through a REST API,
**so that** the MemoryViewer UI (US-5) has a stable contract independent of
internal Cat 3 ABC evolution.

**Acceptance criteria**:
1. NEW file `backend/src/api/v1/memory.py` with 3 endpoints:
   - `GET /api/v1/memory/recent?limit=50&offset=0&layer={layer}` — recent
     access list across all 5 layers (or filtered to specific layer);
     paginated; sorted by `last_accessed_at DESC`.
   - `GET /api/v1/memory/scope/{layer}/{scope_id}?limit=50&offset=0` —
     scope-specific entries (e.g. `/scope/user/abc-123` lists user
     memory). `layer` enum {system, tenant, role, user, session}.
   - `GET /api/v1/memory/by-time/{layer}/{time_scale}?limit=50&offset=0` —
     time-scale filter; `time_scale` enum {permanent, quarterly, daily}
     mapping to expires_at NULL / NOW()+90d / NOW()+1d boundary.
2. All endpoints require auth (`Depends(get_current_tenant)`) and admin role
   (`Depends(require_admin_role("memory:read"))`); auto-scope to
   `current_tenant_id` (multi-tenant rule).
3. Response shape: `MemoryEntryResponse { id, layer, scope_id, key, value,
   created_at_ms, last_accessed_at_ms, expires_at_ms, access_count,
   tenant_id }` — NEW Pydantic model in `api/v1/_schemas/memory.py`.
4. Cat 3 ABC `MemoryStore` already declares `list_recent` / `list_by_scope`
   / `list_by_time` (verified Day 0 D-PRE-3 探勘) → router wires through
   `Depends(get_memory_store)`; NO new ABC methods.
5. Multi-tenant rule: `tenant_id` filter enforced in repo layer (RLS already
   active per Sprint 56.1); 1 multi-tenant integration test confirms cross-
   tenant access denied.
6. ≥ 7 unit tests + 4 integration tests:
   - Unit: 3 endpoints each test 200 / 401 / 403 / 404 paths;
     pagination boundary (offset > total, limit=0 reject); layer enum
     validation reject invalid; time_scale enum validation reject invalid.
   - Integration: real-DB read across all 5 layers; cross-tenant denied;
     RBAC denied for non-admin role; pagination correctness.

**File touchpoints**:
- `backend/src/api/v1/memory.py` (NEW)
- `backend/src/api/v1/_schemas/memory.py` (NEW Pydantic schemas)
- `backend/src/api/v1/__init__.py` (M — register new router)
- `backend/tests/integration/api/test_memory_recent.py` (NEW)
- `backend/tests/integration/api/test_memory_scope.py` (NEW)
- `backend/tests/integration/api/test_memory_by_time.py` (NEW)
- `backend/tests/unit/api/test_memory_schema.py` (NEW)

---

### US-3: Frontend infra — agent_harness types + services + hooks + shared components

**As a** frontend developer mounting LoopVisualizer / MemoryViewer / SubagentTree,
**I want** centralized types + services + hooks + 2 shared badge components,
**so that** all 3 UIs share the same data contracts and visual vocabulary
per CONVENTION.md §1-§7.

**Acceptance criteria**:
1. NEW `frontend/src/features/agent_harness/types.ts` — TypeScript types
   matching backend schemas:
   - `MemoryEntry { id, layer, scope_id, key, value, created_at_ms,
     last_accessed_at_ms, expires_at_ms, access_count, tenant_id }`
   - `MemoryLayer = "system" | "tenant" | "role" | "user" | "session"`
   - `MemoryTimeScale = "permanent" | "quarterly" | "daily"`
   - `SubagentSpawnedEvent { type: "subagent_spawned"; data: { session_id,
     parent_id, subagent_role, prompt_summary, tenant_id } }`
   - `SubagentCompletedEvent { type: "subagent_completed"; data: {
     session_id, parent_id, success, tokens_used, elapsed_ms, error_class,
     tenant_id } }`
2. NEW `frontend/src/features/agent_harness/services/memoryService.ts`
   with 3 fetcher functions per CONVENTION.md §6 fetchWithAuth pattern.
3. NEW TanStack hooks per CONVENTION.md §5 single-source `*_QUERY_KEY_BASE`:
   - `useMemoryRecent(filter)` → `MEMORY_RECENT_QUERY_KEY_BASE`
   - `useMemoryByScope(layer, scope_id)` → `MEMORY_SCOPE_QUERY_KEY_BASE`
   - `useMemoryByTime(layer, time_scale)` → `MEMORY_BY_TIME_QUERY_KEY_BASE`
4. 2 shared components:
   - `MemoryScopeBadge` — 5-color variant per layer matching STYLE.md §3
     palette (system=indigo / tenant=blue / role=teal / user=green /
     session=amber).
   - `SubagentStatusBadge` — 3-state variant (running=blue / success=green
     / error=red) for SubagentTree status pills.
5. Both badges have `data-testid="*-badge-{type}"` per CONVENTION.md §8.
6. ≥ 8 Vitest tests:
   - 3 memoryService URL building + 4xx/5xx error surface
   - 3 hook tests (useMemoryRecent / useMemoryByScope / useMemoryByTime —
     queryKey shape + fetcher invocation)
   - 2 badge component tests (5-variant + 3-variant)

**File touchpoints**:
- `frontend/src/features/agent_harness/types.ts` (NEW)
- `frontend/src/features/agent_harness/services/memoryService.ts` (NEW)
- `frontend/src/features/agent_harness/hooks/useMemoryRecent.ts` (NEW)
- `frontend/src/features/agent_harness/hooks/useMemoryByScope.ts` (NEW)
- `frontend/src/features/agent_harness/hooks/useMemoryByTime.ts` (NEW)
- `frontend/src/features/agent_harness/components/MemoryScopeBadge.tsx`
  (NEW)
- `frontend/src/features/agent_harness/components/SubagentStatusBadge.tsx`
  (NEW)
- `frontend/tests/unit/agent_harness/*` (NEW; ≥ 8 tests)

---

### US-4: LoopVisualizer — chat-v2 inline panel + standalone `/loop-debug` page

**As an** admin debugging an agent loop in production,
**I want to** visualize the TAO state machine end-to-end (turn-by-turn
LLM thinking + tool calls + verification + memory access + state checkpoints),
**so that** I can identify bottleneck turns / failed verifications /
context compaction events without parsing raw SSE log files.

**Acceptance criteria**:
1. NEW `frontend/src/features/agent_harness/components/LoopVisualizer.tsx`
   — same component mounted in 2 contexts:
   - `<LoopVisualizer mode="inline" />` — chat-v2 ChatLayout side panel
     (compact tree view; auto-collapse old turns; max-height with scroll).
   - `<LoopVisualizer mode="standalone" />` — `/loop-debug` page full-screen
     layout (expanded all turns; total elapsed/tokens summary at top).
2. Consumes `useChatStore` `rawEvents` array (same source as chat-v2 SSE);
   filters/groups events into per-turn nested structure:
   ```
   Turn 0
     ├── PromptBuilt (cache_breakpoints, total_tokens)
     ├── LLMRequested (model, tools)
     ├── Thinking (200 chars summary)
     ├── LLMResponded (stop_reason, output_tokens)
     ├── ToolCallRequested (tool_name)
     ├── ToolCallExecuted / ToolCallFailed
     ├── MemoryAccessed (layer, scope_id)
     ├── VerificationPassed / VerificationFailed
     └── StateCheckpointed (snapshot_id)
   ```
3. NEW route `/loop-debug` (admin-gated; AppShellV2 wrap; reads
   `?session_id=X` query param → loads chat-v2 chatStore for that session
   if running, else shows "session not found / not currently running" panel).
4. Visual encoding (per STYLE.md §3 Risk Badge Palette + §4 Tree typography):
   - Successful events: muted gray border
   - Failed events (ToolCallFailed / VerificationFailed / GuardrailTriggered
     / TripwireTriggered): red border + icon
   - Compaction / retry: amber border (warn-ish)
5. ≥ 5 Vitest tests:
   - inline mode renders all 22 LoopEvent types
   - standalone mode renders summary header (turns count + total tokens)
   - failed event styling
   - turn grouping correctness
   - empty state ("No events yet")

**File touchpoints**:
- `frontend/src/features/agent_harness/components/LoopVisualizer.tsx` (NEW)
- `frontend/src/pages/loop-debug/index.tsx` (NEW page wrap)
- `frontend/src/features/chat_v2/components/ChatLayout.tsx` (M — mount
  inline LoopVisualizer side panel)
- `frontend/tests/unit/agent_harness/LoopVisualizer.test.tsx` (NEW)
- `frontend/tests/e2e/loop-debug-standalone.spec.ts` (NEW; 1 e2e)
- `frontend/tests/e2e/chat-v2-loop-inline.spec.ts` (NEW; 1 e2e)

---

### US-5: MemoryViewer — standalone `/memory` page with 2-tab Routes

**As an** admin investigating tenant memory state,
**I want to** browse memory entries by recent access, by scope, and by time
scale through a paginated UI,
**so that** I can audit memory contents without backend shell access.

**Acceptance criteria**:
1. NEW `/memory` route (admin-gated `memory:read`; AppShellV2 wrap; nested
   Routes per CONVENTION.md §3):
   - `/memory/recent` (default) — recent access list across all 5 layers;
     layer filter dropdown (or "all"); pagination 50/page.
   - `/memory/by-scope` — 5-layer card view; click layer card → drill into
     scope_id list → detail panel showing entries for that scope.
2. NEW `frontend/src/features/agent_harness/components/MemoryRecentList.tsx`
   — table/list view consuming `useMemoryRecent`; columns: layer (badge),
   scope_id, key, value (truncated 80 chars + tooltip full), last_accessed,
   expires_at (if non-null).
3. NEW
   `frontend/src/features/agent_harness/components/MemoryByScopeBrowser.tsx`
   — 5-card grid (one per layer) + scope_id list per card + drill-in detail
   panel.
4. NEW page `frontend/src/pages/memory/index.tsx` per CONVENTION.md §1
   page-level AppShellV2 wrap pattern (mirror `/verification` from 57.11).
5. Empty states + error retry per STYLE.md §6 (retryClicked StrictMode-safe).
6. ≥ 6 Vitest tests:
   - MemoryRecentList renders all 5 layer badges
   - MemoryRecentList pagination (next/prev disabled at boundaries)
   - MemoryByScopeBrowser renders 5 cards
   - MemoryByScopeBrowser drill-in expands detail panel
   - Empty state
   - Error state with retry

**File touchpoints**:
- `frontend/src/pages/memory/index.tsx` (NEW)
- `frontend/src/features/agent_harness/components/MemoryRecentList.tsx`
  (NEW)
- `frontend/src/features/agent_harness/components/MemoryByScopeBrowser.tsx`
  (NEW)
- `frontend/src/features/agent_harness/types.ts` (M — extend if needed)
- `frontend/tests/unit/agent_harness/MemoryRecentList.test.tsx` (NEW)
- `frontend/tests/unit/agent_harness/MemoryByScopeBrowser.test.tsx` (NEW)
- `frontend/tests/e2e/memory-page.spec.ts` (NEW; 1 e2e)

---

### US-6: SubagentTree — chat-v2 inline panel consuming Cat 11 SSE

**As a** chat-v2 user running a multi-agent workflow,
**I want to** see a live tree of spawned subagents with their status (running
/ success / error) + tokens / elapsed,
**so that** I can understand what the orchestrator is delegating without
parsing raw events.

**Acceptance criteria**:
1. NEW
   `frontend/src/features/agent_harness/components/SubagentTree.tsx`
   — chat-v2 inline panel (same pattern as VerificationPanel + LoopVisualizer
   inline).
2. Consumes `useChatStore` `subagents` slice — NEW state slice + reducers:
   - `appendSubagent(event: SubagentSpawnedEvent)` — adds new node
   - `updateSubagent(event: SubagentCompletedEvent)` — sets terminal status
   - `clearSubagents()` — reset on new session
   - `chatStore.mergeEvent` updated for `subagent_spawned` /
     `subagent_completed` cases per CONVENTION.md §7 3-edit checklist
     (types alias + KNOWN_LOOP_EVENT_TYPES set + mergeEvent reducer).
3. Tree visual: parent→child links derived from `parent_id`; root nodes are
   chat session itself (parent_id = chat session_id); each node shows:
   - Subagent role badge (per StatusBadge from US-3)
   - prompt_summary (first 60 chars + tooltip)
   - On completion: tokens_used + elapsed_ms + error_class (if failed)
   - Status: running (spinner) / success (green check) / error (red X)
4. ≥ 5 Vitest tests:
   - appendSubagent reducer
   - updateSubagent reducer (running → success transition)
   - updateSubagent reducer (running → error transition)
   - mergeEvent dispatches subagent_spawned/_completed correctly
   - Tree renders parent→child links with depth ≥ 2 (subagent spawning
     subagent)

**File touchpoints**:
- `frontend/src/features/agent_harness/components/SubagentTree.tsx` (NEW)
- `frontend/src/features/chat_v2/store/chatStore.ts` (M — subagents slice +
  reducers + mergeEvent SSE branch)
- `frontend/src/features/chat_v2/types.ts` (M — KNOWN_LOOP_EVENT_TYPES
  add subagent_spawned + subagent_completed)
- `frontend/src/features/chat_v2/components/ChatLayout.tsx` (M — mount
  inline SubagentTree side panel)
- `frontend/tests/unit/agent_harness/SubagentTree.test.tsx` (NEW)
- `frontend/tests/unit/agent_harness/chatStore.subagents.test.ts` (NEW)
- `frontend/tests/e2e/chat-v2-subagent-inline.spec.ts` (NEW; 1 e2e via
  page.route() mock per `feedback_e2e_network_mocking_pattern`)

---

### US-7: AD-AdminTenant-Patch-Flake fix (audit cycle)

**As a** developer running `pytest tests/integration/api/`,
**I want** test_admin_tenant_patch.py to pass deterministically across runs,
**so that** local test pollution from prior runs does not cause
`UniqueViolationError uq_tenants_code` flake (3/9 currently fail).

**Acceptance criteria**:
1. NEW or M `tests/integration/api/conftest.py` autouse fixture scoped to
   admin_tenant test files:
   - Yields control to test
   - On teardown, deletes `tenants` rows where `code LIKE 'TEST_%' OR
     code IN (<known test codes>)` per 53.7 §Risk Class C SAVEPOINT pattern.
2. Alternative or complementary: per-test unique tenant_code (UUID-suffix)
   — but autouse cleanup is preferred for predictable test IDs.
3. Re-run `pytest tests/integration/api/test_admin_tenant_patch.py` in 3
   consecutive sessions (with `pytest --reuse-db` mock); 9/9 pass each run.
4. Pattern documented in `.claude/rules/testing.md` §Module-level Singleton
   Reset Pattern (extend existing pattern catalog).

**File touchpoints**:
- `backend/tests/integration/api/conftest.py` (M — add autouse fixture or
  scoped `_cleanup_test_tenants` helper)
- `.claude/rules/testing.md` (M — extend §Risk Class C examples)

---

### US-8: Routing wire-up + 4-5 Playwright e2e + Closeout

**As an** AI assistant managing Sprint 57.12 closeout,
**I want** routes wired + e2e regression coverage + retrospective + memory
snapshot + doc syncs (4 standard items per 57.7+57.8+57.9+57.10+57.11
pattern),
**so that** Sprint 57.12 is mergeable to main with full audit trail.

**Acceptance criteria**:
1. `frontend/src/routes.config.ts` — register `/memory` (lazy import,
   admin-gated) + `/loop-debug` (lazy import, admin-gated); 11→13 entries.
2. 4 Playwright e2e (per 57.11 §3.5 + §4.2 pattern):
   - `loop-debug-standalone.spec.ts` (US-4 standalone page + auth gate)
   - `chat-v2-loop-inline.spec.ts` (US-4 chat-v2 inline)
   - `memory-page.spec.ts` (US-5 standalone /memory + 2-tab)
   - `chat-v2-subagent-inline.spec.ts` (US-6 chat-v2 inline + SSE mock per
     `feedback_e2e_network_mocking_pattern`)
3. **STRETCH** — 1 SSE-injection real-flow e2e: chat-v2 sends prompt that
   spawns subagent → SubagentTree renders 1-depth tree. Mark deferred to
   AD-Subagent-RealShip-E2E if Playwright SSE mock proves brittle (per
   Sprint 57.11 STRETCH deferral pattern → AD-Verification-RealShip-E2E).
4. chat-v2 8/8 Playwright regression sentinel pass (mirror 57.11 §4.3).
5. Full validation sweep all green (mirror 57.11 §4.4):
   - pytest 1635 → 1655+ (target +20: ≥17 backend tests)
   - mypy strict 0/300+ (NEW source files: 2 backend + 7+ frontend)
   - 9 V2 lints 9/9 green (no new lint added; check_rls_policies passes —
     NO new tables this sprint)
   - Vitest 119 → 145+ (target +26: ≥26 frontend tests)
   - Playwright 31 → 35+ (target +4: 4 NEW + 1 STRETCH if achieved)
   - Vite build (note: bundle main may grow per AD-Bundle-Size-285kB
     carryover; track ratio not absolute kB)
   - LLM SDK leak 0
6. retrospective.md Q1-Q7 (Q7 N/A SKIP per 57.8+57.9+57.10+57.11 precedent
   — feature ship NOT spike).
7. memory snapshot `project_phase57_12_agent_harness_ui_suite.md`
   (this file's frontmatter sets the description hint).
8. 4 doc syncs (3/4 done in sprint; SITUATION + CLAUDE.md DEFERRED to
   post-merge closeout PR per 57.7+57.8+57.9+57.10+57.11 pattern):
   - `sprint-workflow.md` calibration matrix +1 row data point (5th
     `large multi-domain` 0.55 application)
   - this plan header MHist Last Modified + closeout entry
   - `16-frontend-design.md` V2 Ship Timeline 7/N → 8/N + 3 internal-debug
     UIs promoted to shipped
   - `claudedocs/6-ai-assistant/prompts/SITUATION-V2-SESSION-START.md` — AFTER PR merge

**File touchpoints**:
- `frontend/src/routes.config.ts` (M)
- `frontend/tests/e2e/*.spec.ts` (4 NEW + STRETCH)
- `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-12/progress.md` (NEW)
- `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-12/retrospective.md` (NEW)
- `claudedocs/.../project_phase57_12_agent_harness_ui_suite.md` (NEW;
  memory snapshot)
- 4 doc syncs above

---

## Technical Specifications

### Cat 11 SSE event emission design (US-1)

**Where to emit**:
1. `subagent/tools.py` — 4 tool handlers wrap their existing
   `forkExecutor.run_*` call:
   ```python
   async def spawn_subagent_handler(args, ctx, event_emitter=None):
       child_session_id = uuid4()
       if event_emitter:
           await event_emitter(SubagentSpawned(
               session_id=str(child_session_id),
               parent_id=ctx.parent_session_id,
               subagent_role=args.role,
               prompt_summary=args.prompt[:200],
               tenant_id=ctx.trace_context.tenant_id,
               # ... LoopEvent base fields
           ))
       try:
           result = await ctx.fork_executor.run_with_session(...)
           if event_emitter:
               await event_emitter(SubagentCompleted(
                   session_id=str(child_session_id),
                   parent_id=ctx.parent_session_id,
                   success=True,
                   tokens_used=result.tokens_used,
                   elapsed_ms=elapsed,
                   error_class=None,
                   tenant_id=ctx.trace_context.tenant_id,
               ))
           return result
       except Exception as e:
           if event_emitter:
               await event_emitter(SubagentCompleted(
                   ...
                   success=False,
                   error_class=type(e).__name__,
               ))
           raise
   ```
2. `event_emitter` is wired by chat router `_stream_loop_events` ∈ same
   pattern as 57.11 verification correction_loop.write_hook (best-effort;
   exception in emitter NOT propagated; logged as warning).
3. `ForkExecutor.run_with_*` accepts optional `event_emitter` param;
   propagated through tool ctx for child loop's own emissions to nest into
   the same parent stream (recursive subagent spawning).

### Cat 3 REST design (US-2)

**Authentication chain**:
```python
@router.get("/recent", response_model=PaginatedMemoryResponse)
async def list_recent(
    layer: MemoryLayer | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_tenant: UUID = Depends(get_current_tenant),
    _admin: None = Depends(require_admin_role("memory:read")),
    memory_store: MemoryStore = Depends(get_memory_store),
) -> PaginatedMemoryResponse:
    entries = await memory_store.list_recent(
        tenant_id=current_tenant, layer=layer, limit=limit, offset=offset,
    )
    return PaginatedMemoryResponse(
        items=[_to_response(e) for e in entries],
        ...
    )
```

**Response shape**:
```python
class MemoryEntryResponse(BaseModel):
    id: UUID
    layer: MemoryLayer
    scope_id: str
    key: str
    value: str  # JSON-serialized via str() at API boundary
    created_at_ms: int
    last_accessed_at_ms: int | None
    expires_at_ms: int | None
    access_count: int
    tenant_id: UUID
```

**RLS rule**: 5-layer tables already RLS-enforced per Sprint 56.1 (8th V2
lint check_rls_policies green); REST layer does NOT bypass (no `text("SET
LOCAL")` overrides).

### Frontend infra (US-3)

Per CONVENTION.md §1-§7 + STYLE.md §3-§6:
- `*_QUERY_KEY_BASE` exports from hook files (single-source per 57.10 §5)
- `fetchWithAuth` from `services/authService.ts` (no parallel imports)
- ChatStore `mergeEvent` 3-edit pattern for SubagentSpawned/Completed
- StrictMode-safe retry buttons via `retryClicked` flag (57.10 §6)

### LoopVisualizer dual-mount (US-4)

Same `<LoopVisualizer />` component takes `mode` prop:
- `mode="inline"` → compact tree, 400px max-height, scroll, last 5 turns
  expanded by default
- `mode="standalone"` → full screen, summary header, all turns expanded

Both modes consume `useChatStore.rawEvents` — chat-v2 inline gets live
stream from current session; `/loop-debug?session_id=X` standalone reads
chatStore for that session ID (404 if no live session for that ID — keeps
scope simple per AP-6 YAGNI).

### Calibration class

**`large multi-domain` 0.55 mid-band 5th application**:
- Bottom-up est: ~24 hr (US-1 ~4 + US-2 ~3.5 + US-3 ~2.5 + US-4 ~4.5 +
  US-5 ~3.5 + US-6 ~2.5 + US-7 ~1.5 + US-8 ~2.5)
- Calibrated commit: ~13 hr (24 × 0.55)
- 5-data-point window post-application: 56.1=1.00 + 56.3=1.04 + 57.2=0.77
  + 57.11=0.47 + 57.12=TBD; current 4-data-point mean **0.82** (lower edge
  of band)
- KEEP 0.55 baseline this sprint per `When to adjust` 3-sprint rule (4 data
  points still under 0.7 evaluation threshold; if 5th point continues
  under 0.7 → propose 0.55 → 0.40 lift in 57.13 retro)

---

## File Change List

### NEW Backend (US-1 + US-2 + US-7)

| File | Purpose |
|------|---------|
| `backend/src/api/v1/memory.py` | NEW Cat 3 REST router (US-2) |
| `backend/src/api/v1/_schemas/memory.py` | NEW Pydantic schemas (US-2) |
| `backend/tests/unit/agent_harness/subagent/test_subagent_sse_emission.py` | US-1 unit tests |
| `backend/tests/integration/agent_harness/test_subagent_sse_e2e.py` | US-1 real-LLM integration |
| `backend/tests/integration/api/test_memory_recent.py` | US-2 |
| `backend/tests/integration/api/test_memory_scope.py` | US-2 |
| `backend/tests/integration/api/test_memory_by_time.py` | US-2 |
| `backend/tests/unit/api/test_memory_schema.py` | US-2 |

### MODIFIED Backend (US-1 + US-2 + US-7)

| File | Change |
|------|--------|
| `backend/src/agent_harness/subagent/tools.py` | US-1 emit Spawned/Completed in 4 handlers |
| `backend/src/agent_harness/subagent/fork_executor.py` | US-1 accept event_emitter param |
| `backend/src/api/v1/chat/handler.py` | US-1 serialize_loop_event for 2 NEW event types |
| `backend/src/api/v1/__init__.py` | US-2 register memory router |
| `backend/tests/integration/api/conftest.py` | US-7 autouse cleanup fixture |
| `.claude/rules/testing.md` | US-7 extend Risk Class C examples |

### NEW Frontend (US-3 + US-4 + US-5 + US-6)

| File | Purpose |
|------|---------|
| `frontend/src/features/agent_harness/types.ts` | US-3 single-source types |
| `frontend/src/features/agent_harness/services/memoryService.ts` | US-3 API client |
| `frontend/src/features/agent_harness/hooks/useMemoryRecent.ts` | US-3 |
| `frontend/src/features/agent_harness/hooks/useMemoryByScope.ts` | US-3 |
| `frontend/src/features/agent_harness/hooks/useMemoryByTime.ts` | US-3 |
| `frontend/src/features/agent_harness/components/MemoryScopeBadge.tsx` | US-3 |
| `frontend/src/features/agent_harness/components/SubagentStatusBadge.tsx` | US-3 |
| `frontend/src/features/agent_harness/components/LoopVisualizer.tsx` | US-4 dual-mount |
| `frontend/src/features/agent_harness/components/MemoryRecentList.tsx` | US-5 |
| `frontend/src/features/agent_harness/components/MemoryByScopeBrowser.tsx` | US-5 |
| `frontend/src/features/agent_harness/components/SubagentTree.tsx` | US-6 |
| `frontend/src/pages/loop-debug/index.tsx` | US-4 standalone page |
| `frontend/src/pages/memory/index.tsx` | US-5 standalone page |
| `frontend/tests/unit/agent_harness/*.test.tsx` (×8+) | US-3-6 unit tests |
| `frontend/tests/e2e/loop-debug-standalone.spec.ts` | US-4 e2e |
| `frontend/tests/e2e/chat-v2-loop-inline.spec.ts` | US-4 e2e |
| `frontend/tests/e2e/memory-page.spec.ts` | US-5 e2e |
| `frontend/tests/e2e/chat-v2-subagent-inline.spec.ts` | US-6 e2e |

### MODIFIED Frontend (US-4 + US-6 + US-8)

| File | Change |
|------|--------|
| `frontend/src/features/chat_v2/store/chatStore.ts` | US-6 subagents slice + mergeEvent SSE branch |
| `frontend/src/features/chat_v2/types.ts` | US-6 KNOWN_LOOP_EVENT_TYPES extend |
| `frontend/src/features/chat_v2/components/ChatLayout.tsx` | US-4+US-6 mount inline panels |
| `frontend/src/routes.config.ts` | US-8 register /memory + /loop-debug |

### NEW Sprint artifacts (US-8)

| File | Purpose |
|------|---------|
| `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-12/progress.md` | Daily progress |
| `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-12/retrospective.md` | Q1-Q7 closeout |
| `claudedocs/.../project_phase57_12_agent_harness_ui_suite.md` | Memory snapshot |

### Doc syncs (US-8 — 3 in sprint + 1 post-merge)

| File | Sync |
|------|------|
| `.claude/rules/sprint-workflow.md` | +1 row 5th `large multi-domain` 0.55 data point |
| `docs/03-implementation/agent-harness-planning/16-frontend-design.md` | V2 Ship Timeline 7/N → 8/N + 3 internal-debug UIs promoted |
| `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-12-plan.md` | this header MHist closeout |
| `claudedocs/6-ai-assistant/prompts/SITUATION-V2-SESSION-START.md` | DEFERRED post-merge closeout PR |

**Counts**: 24 NEW + 11 MODIFIED = 35 file touchpoints (vs 57.11 ~31 — slightly larger per multi-domain scope expansion)

---

## Acceptance Criteria

### Functional (per US 1-7)
- US-1 ✅: Cat 11 SSE Spawned + Completed events emit from 4 tool handlers; ForkExecutor propagates emitter; chat router serializes; ≥ 8 backend tests pass.
- US-2 ✅: 3 NEW REST endpoints accept auth + RBAC + tenant scope; cross-tenant denied; ≥ 11 backend tests pass.
- US-3 ✅: Frontend infra (types + services + hooks + 2 badges) compiled; ≥ 8 Vitest tests pass.
- US-4 ✅: LoopVisualizer mounts inline + standalone; renders 22 LoopEvent types grouped per turn; ≥ 5 Vitest tests + 2 Playwright e2e pass.
- US-5 ✅: `/memory` standalone page + 2-tab Routes; reads 5-layer entries; pagination + filter; ≥ 6 Vitest + 1 Playwright e2e pass.
- US-6 ✅: SubagentTree consumes Cat 11 SSE events; parent→child tree links; ≥ 5 Vitest + 1 Playwright e2e pass.
- US-7 ✅: `pytest tests/integration/api/test_admin_tenant_patch.py` 9/9 pass deterministically across 3 consecutive runs.

### Non-functional
- pytest +17 minimum (1635 → 1652+); strict 0/300+ source files.
- 9 V2 lints 9/9 green; LLM SDK leak 0 (no `import openai/anthropic` in `agent_harness/`).
- mypy strict 0 errors on Linux + Windows (Sprint 52.6 cross-platform pattern).
- Vitest +26 minimum (119 → 145+).
- Playwright +4 minimum (31 → 35+).
- chat-v2 8/8 regression sentinel.
- Vite build succeed (bundle ratio change documented in retrospective if main >285 kB ceiling per AD-Bundle-Size-285kB carryover).
- ESLint silent.

### Sprint workflow discipline
- ✅ Day 0 三-prong already done (4 D-PRE-N catalogued in plan §Background)
- ✅ Plan + Checklist drafted before code
- ✅ MHist 1-line max per `.claude/rules/file-header-convention.md`
- ✅ NO new ABC + NO new LoopEvent + NO new Alembic migration (per 17.md single-source preserved)
- ✅ rolling planning紀律(no 57.13 plan pre-write)

### V2 紀律 9 項 self-check (each commit + PR)
1. ✅ Server-Side First — Cat 3 REST tenant_id + RLS; Cat 11 emission tenant_id propagation
2. ✅ LLM Provider Neutrality — agent_harness no SDK import (verified via 9th V2 lint check_no_sdk_in_harness)
3. ✅ CC Reference 不照搬 — internal debug UIs server-side rendered (NOT CC-style local file system)
4. ✅ 17.md Single-source — 0 NEW contracts, ABC, LoopEvents, migrations
5. ✅ 11+1 範疇 — Cat 11 (subagent) + Cat 3 (memory) + Cat 1 (loop visualization) clearly demarcated
6. ✅ AP-1/2/3/4/6/9 — no Pipeline pretending Loop, no orphan, no scattering, no Potemkin (data-source verified), no premature abstraction, verification still active
7. ✅ Sprint workflow — Day 0 → Plan → Checklist → Code → Update → Progress doc → Retrospective
8. ✅ File header MHist — 1-line max
9. ✅ Multi-tenant — tenant_id NN + RLS + fetchWithAuth + RBAC

---

## Deliverables (checklist mapping)

- [ ] Day 0 setup + 三-prong + branch + calibration
- [ ] US-1 Cat 11 SSE event emission (8+ backend tests)
- [ ] US-2 Cat 3 NEW `/api/v1/memory` REST (11+ backend tests)
- [ ] US-3 Frontend infra (types + services + 3 hooks + 2 badges) (8+ Vitest)
- [ ] US-4 LoopVisualizer chat-v2 inline + standalone `/loop-debug` (5+ Vitest + 2 Playwright)
- [ ] US-5 MemoryViewer standalone `/memory` 2-tab (6+ Vitest + 1 Playwright)
- [ ] US-6 SubagentTree chat-v2 inline (5+ Vitest + 1 Playwright)
- [ ] US-7 AD-AdminTenant-Patch-Flake fix (audit cycle; 9/9 pass × 3 runs)
- [ ] US-8 routes.config wire + 4 Playwright e2e + chat-v2 8/8 regression + retrospective Q1-Q7 + memory snapshot + 4 doc syncs
- [ ] PR opened with V2 紀律 9 項 self-check + Day 4 closeout user decision points

---

## Dependencies & Risks

### External dependencies (no scope creep risk)
- 17.md §4 LoopEvent definitions (single-source; `_contracts/events.py:301,308` for SubagentSpawned/Completed already exist) — **NO change**
- 17.md §3 Cat 3 MemoryStore ABC `list_recent`/`list_by_scope`/`list_by_time` (Sprint 51.2) — **used as-is**
- 17.md §11 Cat 11 ForkExecutor + Subagent ABC (Sprint 54.2) — **emission added without ABC change**
- Sprint 57.7 IAM / require_admin_role + JWT — **used as-is**
- Sprint 57.10 CONVENTION.md §7 SSE 3-edit + STYLE.md §3 palette — **used as-is**
- Sprint 57.11 verification_log + REST pattern — **mirror for memory REST shape**

### Risk matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| US-1 emitter wiring breaks ToolCallExecuted contract | Low | High | Best-effort emit (try/except + log warning); no propagation to tool path |
| US-2 RLS bypass in memory_store layer | Low | Critical | RLS already at DB layer per 56.1 8th lint; REST does NOT SET LOCAL override; cross-tenant integration test mandatory |
| US-4 LoopVisualizer perf — 22 events × N turns × tooltip render | Medium | Medium | Compact mode auto-collapse old turns; standalone fully expanded only on user toggle |
| US-5 5-layer card view UX confusion | Low | Low | 2-tab Routes (recent + by-scope) per CONVENTION.md page architecture; MemoryScopeBadge color-coded per STYLE.md §3 |
| US-6 SubagentTree depth-N rendering — recursion stack overflow | Low | Medium | Cap depth at 5 in component (defensive); deeper subagent spawning logs warning + truncates display |
| US-7 conftest.py autouse fixture breaks unrelated tests | Medium | Low | Scope cleanup to specific test files via fixture parametrization; verify pytest 1635 baseline maintained |
| Bundle main grows past 285 kB ceiling per AD-Bundle-Size-285kB | High | Low | Track ratio not absolute; carryover AD already logged Sprint 57.11 — ship with size note in retrospective; defer optimization Phase 57.13+ |
| Cat 11 SSE backend test real-LLM flake | Medium | Low | Mark `@pytest.mark.real_llm`; bypassed by default; opt-in via `--real-llm` flag |
| Day 0 三-prong missed Cat 11 ForkExecutor signature break | Low | Critical | Day 0 D-PRE-2 confirmed only docstring marker + 0 emission; signature additive `event_emitter: Callable | None = None` backward-compat |

### Roll-back plan
- US-1 backend revert: `git revert` 4 tool handler edits + ForkExecutor; emitter param defaults to None preserves compat
- US-2 backend revert: drop `/api/v1/memory` router registration; no schema change
- Frontend US-3-6 revert: drop `frontend/src/features/agent_harness/` directory + 2 page directories + routes.config entries; no chat-v2 chatStore breakage if subagents slice + mergeEvent revert clean
- US-7 revert: remove conftest.py fixture; tests revert to flaky state (pre-57.12 baseline)

---

## Workload (calibrated)

### Bottom-up estimate by US

| US | Bottom-up | Notes |
|----|-----------|-------|
| US-0 (Day 0 setup) | 0.5 hr | branch + 三-prong commit + calibration baseline |
| US-1 Cat 11 SSE | 4.0 hr | 4 handler edits + ForkExecutor + chat router serializer + 8 tests |
| US-2 Cat 3 REST | 3.5 hr | 3 endpoints + Pydantic schemas + 11 tests |
| US-3 Frontend infra | 2.5 hr | types + service + 3 hooks + 2 badges + 8 Vitest |
| US-4 LoopVisualizer | 4.5 hr | dual-mount component + standalone page wrap + 5 Vitest + 2 Playwright |
| US-5 MemoryViewer | 3.5 hr | 2-tab page + 2 components + 6 Vitest + 1 Playwright |
| US-6 SubagentTree | 2.5 hr | 1 component + chatStore slice + 5 Vitest + 1 Playwright |
| US-7 audit cycle | 1.5 hr | conftest fixture + testing.md doc + 3-run verify |
| US-8 closeout | 2.5 hr | routes wire + e2e regression + retro Q1-Q7 + memory + 3 doc syncs |
| **Bottom-up total** | **~25 hr** | |

### Calibrated commitment

> Bottom-up est ~25 hr → calibrated commit **~14 hr** (multiplier 0.55)

- **Scope class**: `large multi-domain` 0.55 mid-band (5th application)
- **Multiplier rationale**: Per AD-Sprint-Plan-4 scope-class matrix; 4-data-point window post-57.11 mean **0.82** (lower edge of [0.85, 1.20] band); KEEP 0.55 baseline per `When to adjust` 3-sprint rule
- **Day 4 retrospective Q2 must verify**: actual_total / committed (~14 hr) → if `> 1.20` consider scope class re-evaluation

### Day-level allocation (Day 0-4)

| Day | Focus | USs | Est commit |
|-----|-------|-----|----------|
| Day 0 | Setup + 三-prong + branch | US-0 | 0.5 hr |
| Day 1 | Backend (Cat 11 SSE + Cat 3 REST) | US-1 + US-2 | 4-5 hr |
| Day 2 | Frontend infra + LoopVisualizer + MemoryViewer page wrap | US-3 + US-4 + US-5 (partial) | 3.5-4.5 hr |
| Day 3 | MemoryViewer complete + SubagentTree + audit cycle | US-5 (rest) + US-6 + US-7 | 3-4 hr |
| Day 4 | Routing + e2e + closeout | US-8 | 2-3 hr |

### Pre-commit verification (per ✅ exit criteria)
- ✅ pytest 1635 → 1652+ (target +17 = 8 US-1 + 11 US-2 + ε US-7 verification)
- ✅ Vitest 119 → 145+ (target +26 = 8 US-3 + 5 US-4 + 6 US-5 + 5 US-6 + buffer)
- ✅ Playwright 31 → 35+ (target +4)
- ✅ 9 V2 lints 9/9; mypy strict 0; ESLint silent; LLM SDK leak 0

---

## Open questions for user (pending plan approval)

> All 3 scope-shaping questions resolved 2026-05-10 via AskUserQuestion. No
> open questions block plan approval. Below items are **confirmation-only**:

### Q1 — Branch naming convention
Proposed: `feature/sprint-57-12-agent-harness-ui-suite`
(mirrors 57.11 `feature/sprint-57-11-verification-real-ship` + 57.10
`feature/sprint-57-10-verification-real-ship` even after pivot — keep
descriptive scope name).

**User to confirm before Day 0 commit**.

### Q2 — Calibration class confirmation
Proposed: `large multi-domain` 0.55 (5th application; 4-data-point mean
0.82 lower edge of band; KEEP baseline per `When to adjust` 3-sprint rule).

Alternative considered: `mixed` 0.60 (only if sprint perceived as smaller
scope) — rejected because Cat 11 backend + Cat 3 backend + 3 frontend +
audit cycle clearly multi-domain.

**User to confirm**.

### Q3 — STRETCH e2e SSE-injection
Proposed: 1 stretch e2e for SubagentTree chat-v2 real-flow
(prompt → spawn_subagent → 1-depth tree). Mark deferred to
AD-Subagent-RealShip-E2E if Playwright SSE mock proves brittle (mirror
57.11 STRETCH deferral pattern → AD-Verification-RealShip-E2E).

**User to confirm STRETCH expectation** (allow defer or require ship?).

### Q4 — Final go/no-go decision
After Q1-Q3 confirmed, AI proceeds to draft `sprint-57-12-checklist.md`
mirroring 57.11 5-day pattern (~430 lines, ~36 sub-tasks across 5 days).
Day 0 commit creates branch + writes plan + checklist + initial baselines.
