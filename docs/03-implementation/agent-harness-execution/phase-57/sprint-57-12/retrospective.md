---
File: docs/03-implementation/agent-harness-execution/phase-57/sprint-57-12/retrospective.md
Purpose: Sprint 57.12 retrospective — Agent Harness UI Suite (LoopVisualizer + MemoryViewer + SubagentTree) + Cat 11 SSE emission + Cat 3 REST read facade + AD-AdminTenant-Patch-Flake fix closeout (Phase 57+ Frontend SaaS 8/N).
Category: Frontend / Backend / Cat 11 + Cat 3 + Cat 1 ship + audit cycle
Scope: Phase 57 / Sprint 57.12

Created: 2026-05-10 (Sprint 57.12 Day 4 closeout)

Modification History (newest-first):
    - 2026-05-10: Initial creation (Sprint 57.12 Day 4 closeout)

Related:
    - sprint-57-12-plan.md
    - sprint-57-12-checklist.md
    - progress.md
---

# Sprint 57.12 Retrospective — Agent Harness UI Suite + Cat 11 SSE + Cat 3 REST + AD-AdminTenant-Patch-Flake

## Q1: What went well?

1. **三-prong verify ROI (12 drift findings Day 0-3)**: D-PRE (4 from plan drafting) + D1-001..008 + D2-001..003 + D3-001 all resolved during implementation with **0 scope creep**. Highest-value catches: D1-001 (Cat 11 emit at `DefaultSubagentDispatcher.spawn` single bottleneck — plan's "4 tool handlers" don't exist; reality = 2 tool factories + 4 mode classes) / D1-007 (MemoryStore ABC has no `list_*` methods → chose Option B Direct ORM access to preserve "0 NEW ABC/migrations" claim) / D1-008 (5-layer ORM non-uniform schemas → discriminated `MemoryEntryItem`; role+session return 501) / D2-001 (3 existing placeholder feature dirs reused instead of 1 new `agent_harness/`).

2. **Pattern reuse from 57.11 verification ship accelerated frontend ~40%**: chat-v2 inline panel + standalone admin page + auth gate + 2-tab nested Routes + `features/X/` folder structure all directly mirrored from VerificationPanel / verification page. Vitest coverage scaffolding ~30-40% faster than greenfield Sprint 57.7 IAM rate.

3. **CONVENTION.md §7 SSE 3-edit checklist applied surgically (US-6)**: SubagentSpawned/Completed routed via types.ts type union + KNOWN_LOOP_EVENT_TYPES set + chatStore.mergeEvent cases — no separate AD spike, no silent-drop bug (closes AD-Cat11-SSEEvents 54.2 carryover, frontend half). Backend half (US-1) emits from the dispatcher's `spawn` bottleneck via best-effort `_emit_safely` (exception isolated from tool path).

4. **AD-AdminTenant-Patch-Flake root-caused deeper than "test pollution" (US-7)**: actual cause = admin PATCH route `await db.commit()` persists test rows past `db_session` rollback → `uq_tenants_code` collision; FK CASCADE to `audit_log` hits WORM trigger `audit_log_no_update_delete` → naive `DELETE FROM tenants` fails. Fix = single-transaction WORM-trigger-toggle (same idiom 57.10 D-PRE-DAY4-1 used). `test_admin_tenant_patch.py` 9/9 × 3 consecutive runs (was 3/9 on polluted DB). Pattern documented in `testing.md` §Committed-Row Cleanup Pattern.

5. **Cat 11 + Cat 3 + Cat 1 demarcation clean**: SSE emission lives in Cat 11 dispatcher (not Cat 12 observer); REST read facade is a NEW `api/v1/memory.py` (Cat 3 read path, no Cat 3 ABC change); LoopVisualizer consumes Cat 1 `rawEvents` (no new LoopEvent types). 0 NEW contracts / ABC / LoopEvents / migrations — 17.md single-source preserved.

## Q2: Calibration — Sprint 57.12 ratio + 5-data-point `large multi-domain` mean update

**Sprint 57.12 calibration class**: `large multi-domain` 0.55 (5th data point validation)

**Bottom-up estimate**: ~25 hr
**Calibrated commit**: 25 × 0.55 = ~13.75 hr (~14 hr)
**Actual spent**: ~9.5-11.5 hr conversation total (Day 0 ~30 min + Day 1 ~3-4 hr + Day 2 ~2.5-3 hr + Day 3 ~1.5-2 hr + Day 4 ~2-2.5 hr incl. ~30 min unplanned lint fixup)

**Sprint 57.12 ratio**: actual / committed = ~10.5 / 14 = **~0.75**

**`large multi-domain` 5-data-point evidence**:
- Sprint 56.1 = 1.00
- Sprint 56.3 = 1.04
- Sprint 57.2 = 0.77
- Sprint 57.11 = 0.47
- Sprint 57.12 = ~0.75 (NEW)
- **5-data-point mean = (1.00 + 1.04 + 0.77 + 0.47 + 0.75) / 5 = 0.81** (vs 4-data-point mean 0.82 — stable at lower edge)
- Mean 0.81 is below the [0.85, 1.20] band lower bound by 0.04 — within tolerance per `When to adjust` 3-sprint moving evidence rule (single-sprint outliers ignored)

**Multiplier action**: **KEEP 0.55 baseline** this iteration. `When to adjust` lower-trigger ("3+ consecutive sprints with actual/committed < 0.7") is NOT met: 57.2 = 0.77 (≥ 0.7), 57.11 = 0.47 (< 0.7), 57.12 = 0.75 (≥ 0.7) — only 1 of last 3 under 0.7. If next 1-2 sprints continue under 0.7 → propose 0.55 → 0.40 lift (AD-Sprint-Plan-6 already proposes splitting `mixed`; a parallel `large multi-domain` split is the natural next step if drift persists).

**Why ratio in 0.7-0.8 band this sprint (vs 57.11's 0.47)**:
- US-5 components pulled forward from Day 3 to Day 2 (front-loaded) — net throughput similar, but Day 3 was light, so the per-day estimates over-counted
- Day 1 had genuine new backend work (Cat 11 emission + NEW api/v1/memory.py with per-layer ORM helpers for mypy) — not pure pattern-reuse like 57.11
- ~30 min unplanned Day 4 lint fixup (Day 1/Day 3 commits had skipped black/flake8) added to actual
- Pattern-reuse savings (frontend) + genuine-new-work cost (backend) roughly netted to a "mid-band" 0.75 — the most representative `large multi-domain` data point of the 5 (0.55 was the original calibration; 0.75 actual is within reach of it accounting for the lint-fixup overhead)

## Q3: What didn't go well? (friction / cascade lessons)

1. **Day 1/Day 3 commits skipped `black` + `flake8`** (caught Day 4 §4.4 full sweep): 4 files needed black reformat + 3 E501 violations + 1 E402 (`SubagentEventEmitter` type alias placed before module imports in `dispatcher.py`). ~30 min Day 4 fixup. **Root cause**: Day 1/Day 3 pre-commit only ran `mypy` + 9 V2 lints, not the per-file format chain. **Cascade lesson** (re-confirms `feedback_pre_push_lint_must_run_flake8.md` + `feedback_v2_lints_must_run_locally.md`): every commit's pre-push must be `black . && isort . && flake8 . && mypy . && python scripts/lint/run_all.py` — the format chain catches what mypy/V2-lints don't. No FIX doc (lint-only, no behavioral change) — folded into Day 4 commit.

2. **AD-Bundle-Size-285kB-Carryover continues**: main `index-*.js` 295.14 → **296.58 kB** (+1.44 kB). Adding 2 lazy-loaded page chunks (`/loop-debug` + `/memory`) + 2 lucide icons (Brain, Workflow) to the routes config bumped main slightly. Per the 57.11 VerifierTypeBadge precedent, any component shared between chat-v2 inline panels (LoopVisualizer, SubagentTree, SubagentStatusBadge) AND their standalone pages gets hoisted to main. Mitigation deferred to a dedicated optimization sprint (acceptable — over by ~12 kB only vs the informal 285 kB target, no functional issue).

3. **`scripts/lint/run_all.py` is at project root, not `backend/`** (minor friction Day 4): muscle memory ran `cd backend && python scripts/lint/run_all.py` first (fails — path doesn't exist there); the wrapper + 9 `check_*.py` live at repo-root `scripts/lint/`. Already documented correctly in `.claude/rules/sprint-workflow.md` Pre-Push checklist; just a session-start re-orientation cost.

4. **Backend test count reconciliation noise**: progress.md Day 1-3 entries quoted "pytest 1658"; Day 4 full sweep shows "1654 passed + 4 skipped" = 1658 total collected. The 4 skips are pre-existing real-LLM-marked tests; "1658" was the collected count, "1654" is passed. Reconciled in Day 4 progress entry — no actual regression.

## Q4: Carryover ADs (new + carry-forward decisions)

| AD ID | Status | Description |
|-------|--------|-------------|
| **AD-Cat11-SSEEvents** | ✅ CLOSED via this sprint | Full close — US-1 backend emission (`DefaultSubagentDispatcher._emit_safely` from `spawn` bottleneck) + US-6 frontend (CONVENTION.md §7 3-edit: types.ts union + KNOWN set + chatStore mergeEvent cases). 54.2 carryover resolved. |
| **AD-AdminTenant-Patch-Flake** | ✅ CLOSED via this sprint | US-7 — `_clear_committed_test_tenants()` autouse fixture w/ WORM-trigger-toggle; `test_admin_tenant_patch.py` 9/9 × 3 runs; root cause (PATCH commit + FK CASCADE + WORM trigger) documented in `testing.md` §Committed-Row Cleanup Pattern. |
| **AD-Cat11-Multiturn** | 🟡 PARTIAL — metadata only | US-1 emits SubagentSpawned with `mode` metadata; full multi-turn loop pulling from mailbox NOT shipped → Phase 58+ (AD-Cat11-Multiturn-Full). |
| **AD-Cat11-ParentCtx** | 🟡 PARTIAL — parent_id only | US-1 emits `parent_session_id`; full Cat 7 checkpoint inheritance (parent state → child) NOT shipped → Phase 58+ (AD-Cat11-ParentCtx-Full). |
| **AD-Subagent-RealShip-E2E** | 🆕 NEW Phase 58+ | Plan §4.2 STRETCH (real-backend `spawn_subagent` flow firing live SubagentSpawned over a real SSE connection) deferred — Playwright SSE mock at network layer is the established pattern (verification / governance / approval all deferred their real-flow variants). chat-v2-subagent-inline.spec.ts covers the mocked-SSE path. |
| **AD-Memory-ABC-ListMethods** | 🆕 NEW Phase 58+ | `MemoryStore` ABC has no `list_*` / pagination methods; `api/v1/memory.py` reads via Direct ORM access (Option B, D1-007) to keep "0 NEW ABC" claim. Phase 58+: add `list_recent(layer, scope_id, limit, offset)` to the ABC if more read consumers appear. |
| **AD-Memory-Role-Session-Phase58** | 🆕 NEW Phase 58+ | `api/v1/memory.py` returns 501 for `layer=role` and `layer=session` (their ORM tables have non-uniform schemas — no `updated_at`, role has no `tenant_id`, etc., D1-008). Phase 58+: model the discriminated columns + wire the 2 remaining layers. |
| **AD-Cat11-Handoff-Events-Phase58+** | 🆕 NEW Phase 58+ | HANDOFF mode goes through `handoff()` (synchronous, returns new session_id), NOT `spawn()` — so it does NOT currently emit SubagentSpawned/Completed. Phase 58+: emit a `subagent_handoff` event from `HandoffExecutor` if the UI needs to show handoff transitions. |
| **AD-Cat11-Completed-ErrorFields** | 🆕 NEW Phase 58+ | `SubagentCompleted` SSE event has `summary` + `tokens_used` but no error/failure fields; a failed subagent currently completes with whatever summary the executor produced. Phase 58+: add `success: bool` + `error: str | null` to the event + an `error` status variant to `SubagentStatusBadge`. |
| **AD-Bundle-Size-285kB-Carryover** | 🟡 CONTINUED | main 296.58 kB (+1.44 vs 57.11). Shared inline-panel components (LoopVisualizer / SubagentTree / SubagentStatusBadge used by both chat-v2 and standalone pages) hoist to main. Defer to optimization sprint (extract shared chunk OR dynamically import inline panels in chat-v2). |

### Q4.1: Closeout user decision points (surface in PR description)

1. **Bundle size**: main +1.44 kB (295.14 → 296.58 kB). Over the informal 285 kB target by ~12 kB. Acceptable for this sprint? Or schedule the AD-Bundle-Size optimization sprint next?
2. **STRETCH deferred**: real-backend subagent spawn e2e → AD-Subagent-RealShip-E2E Phase 58+. OK with mocked-SSE coverage for now?
3. **Calibration**: `large multi-domain` 5-point mean = 0.81 (lower edge of [0.85, 1.20]). KEEP 0.55 this iteration; if 57.13 continues drifting, AD-Sprint-Plan-N candidate to split `large multi-domain` into greenfield-heavy vs reuse-heavy (parallel to the AD-Sprint-Plan-6 `mixed` split proposal).

## Q5: Phase 57.13+ direction — candidates per rolling planning 紀律

**(Do NOT commit Phase 57.13 plan/checklist; await user explicit selection)**

1. **AD-Bundle-Size optimization sprint** (~3-5 hr): extract shared inline-panel components (LoopVisualizer / SubagentTree / SubagentStatusBadge / VerifierTypeBadge) to a dedicated lazy chunk OR dynamically import the inline panels in chat-v2; target main back below ~250 kB.
2. **Cat 11 deepening** (~8-12 hr): close AD-Cat11-Multiturn-Full + AD-Cat11-ParentCtx-Full + AD-Cat11-Handoff-Events — full multi-turn mailbox loop + Cat 7 parent-state inheritance + handoff event emission.
3. **Memory read facade completion** (~5-7 hr): close AD-Memory-Role-Session-Phase58 + AD-Memory-ABC-ListMethods — model role/session discriminated schemas, add `list_*` to MemoryStore ABC, wire the 2 remaining layers.
4. **Tier 1 IaC + DR drill** (~15-20 hr): per `enterprise-saas-gap-analysis-20260508.md` §6 Adjusted Roadmap (Phase 58 Tier 1 entry).
5. **SOC 2 + SBOM Tier 1 entry** (~12-15 hr): per gap analysis §1.7 + §1.10.

## Q6: V2 紀律 9 項 self-check

1. ☑️ **Server-Side First** — Cat 3 `api/v1/memory.py` reads are tenant_id-scoped + RLS at storage layer; Cat 11 emission carries tenant_id via `TraceContext`; frontend is pure presentation.
2. ☑️ **LLM Provider Neutrality** — `agent_harness/**` 0 SDK imports (`check_llm_sdk_leak.py` OK + `test_llm_sdk_leak.py` pass); Cat 11 emission + Cat 3 read facade do not touch openai/anthropic.
3. ☑️ **CC Reference 不照搬** — debug UIs (LoopVisualizer / MemoryViewer / SubagentTree) are server-rendered React reading server-streamed events, NOT CC-style local-fs introspection.
4. ☑️ **17.md Single-source** — 0 NEW contracts / ABC / LoopEvents / migrations. Cat 3 ABC unchanged (Direct ORM read, D1-007). Cat 11 SubagentSpawned/Completed already in 17.md §LoopEvent registry. NEW frontend query-key consts (`MEMORY_*_QUERY_KEY_BASE`) are feature-local, not cross-category contracts.
5. ☑️ **11+1 範疇** — Cat 11 (dispatcher emission) + Cat 3 (memory read facade) + Cat 1 (LoopVisualizer consumes rawEvents) + Cat 12 (events are observability surface); clean demarcation, no cross-category hash.
6. ☑️ **04 anti-patterns** — AP-1 no Pipeline-as-Loop / AP-2 no orphan (routes wired, pages reachable) / AP-3 no scattering (3 existing feature dirs, not a new mega-dir) / AP-4 no Potemkin (e2e + Vitest cover real render+merge) / AP-6 YAGNI (no auth refactor, no historical persistence layer, role/session deferred not stubbed-empty) / AP-9 verification preserved.
7. ☑️ **Sprint workflow** — Phase README → plan → checklist → Day 0 三-prong → code → progress → retro; no step skipped.
8. ☑️ **File header convention** — all new files have header + Category + MHist 1-line max per 55.3+ rule; Day 4 trimmed 3 over-budget MHist/Purpose lines.
9. ☑️ **Multi-tenant rule** — `api/v1/memory.py` queries scoped by JWT tenant_id; tenant-layer scope_id mismatch → 404 (not 403, no info leak); RLS at storage; `fetchWithAuth` on the frontend service.

## Q7: Spike sprint design note? (N/A SKIP)

**N/A SKIP** — feature-ship pattern (4th consecutive sprint after 57.8 + 57.9 + 57.10 + 57.11). Per `sprint-workflow.md` §Step 5.5, the spike-extract design note is for spike sprints only (new-domain exploration). Sprint 57.12 ships UI for already-specified Cat 1 / Cat 3 / Cat 11 — `01-eleven-categories-spec.md` + `16-frontend-design.md` already catalog the relevant contracts; no new design spec extraction needed.

(Pattern-promotion candidate: 5 consecutive feature-ship N/A SKIP sprints (57.8-57.12) — strong evidence for folding a "feature-ship vs spike" differential rule into `sprint-workflow.md` §Step 5.5 so the N/A determination is explicit, not ad-hoc. Defer to a rules-maintenance commit.)

---

**Sprint 57.12 status**: ✅ COMPLETE (Day 4 closeout — PR open + closeout sync pending)
**Branch**: `feature/sprint-57-12-agent-harness-ui-suite` (5 commits ahead of origin/main pre-PR: Day 0 `4ea0dc61` / Day 1 `9a1e69f6` / Day 2 `baab74f3` / Day 3 `469daf5c` / Day 4 — this commit)
**Deliverables**: 8 USs (US-1 Cat 11 SSE + US-2 Cat 3 REST + US-3 frontend infra + US-4 LoopVisualizer + US-5 MemoryViewer + US-6 SubagentTree + US-7 audit cycle + US-8 routing + e2e + closeout)
**Test deltas**: pytest 1635 → 1654 (+19) / Vitest 119 → 168 (+49) / Playwright 31 → 37 (+6)
