# Sprint 57.125 Retrospective — chat-v2 session history replay (arc slice 1/2: backend SSE transcript persistence + replay endpoint)

**Closed**: 2026-06-16 · **Branch**: `feature/sprint-57-125-chatv2-session-transcript-persistence` · **Base**: `main` `486db0ed`

## Q1 — What shipped?

Backend foundation for chat-v2 historical-session replay (arc slice 1/2):
- **Writer** (`router.py` `_persist_main_event` in `_stream_loop_events`): persists the EXACT serialized main-session SSE payload to `message_events` (mirrors the 57.107 sidechain observer — best-effort SAVEPOINT, `MAIN_TRANSCRIPT_OBSERVER` env-gate default-on, monotonic `main_seq`, keyed by the MAIN `session_id`). NO migration (table + partitions exist).
- **Reader** (`sessions.py` `GET /{id}/events`): ordered replay; cross-tenant/unknown/event-less → 200 + `[]` (not 404).
- Test isolation (`tests/integration/api/conftest.py`) + stale-ref cleanup (`next-phase-candidates.md:495` + `sessions.py` docstring).
- CHANGE-092 + design note 37 (spike-extract). Closes `AD-ChatV2-Session-History-Replay-Phase58` backend half + `AD-ChatV2-SessionList-Backend` (resolved-by-57.107).

## Q2 — Estimate accuracy (calibration)

- **Scope class**: `chatv2-transcript-persistence-spike` **0.60** (NEW). Backend SSE-stream persistence observer mirroring the proven `_persist_subagent_transcript` + a sibling read endpoint mirroring `get_state_snapshot`; reuses an existing table/partitions/serializer, NO migration. Closest: `subagent-sse-relay-wiring` 0.55 + the read-endpoint half → 0.60.
- **Agent-delegated: no** (parent-direct; the writer placement + best-effort/env-gate semantics + the empty-vs-404 reader decision are precise and hand-authored). `agent_factor` 1.0 → 3-segment form.
- Bottom-up ~8.75 hr → class-calibrated commit ~5.25 hr (mult 0.60). **Actual ≈ commit** (ratio ~1.0, IN band): the Day-0 re-scope added discovery time but SAVED building the wrong thing (the AD's literal scope was already done); implementation was a clean mirror-of-proven-pattern; all gates + the live probe passed first-try. **1st data point → KEEP 0.60**, flag the next such sprint for the 3-sprint window.

## Q3 — What went well?

- **Day-0 三-prong caught the re-scope** (the highest-value moment): two Explore sweeps + direct reads showed `AD-ChatV2-SessionList-Backend`'s literal scope was already shipped by 57.107; the real gap is history-replay. AskUserQuestion settled Option B (full SSE persist) over the lossy Option A. Without Day-0, the sprint would have rebuilt an existing endpoint.
- **Mirror-a-proven-pattern** de-risked the writer: `_persist_subagent_transcript` (57.107) gave the exact best-effort/env-gate/serialize shape → the writer was a small symmetric addition.
- **The elegance held**: persist the already-computed `payload` → the persisted stream is byte-identical to the live stream (live probe: `streamed == persisted` TRUE) → 57.126 replays through the unchanged reducer for pixel-identical turns.
- All gates green first-try (mypy 0/370, run_all 10/10, full pytest 2711+5, +8 new); live probe passed first-try.

## Q4 — What to improve / lessons

- **Stale carryover descriptions**: the AD one-liner (`next-phase-candidates.md:495`) was ~10 days stale (predated 57.107). Lesson reinforced — Day-0 Prong-1/2 must verify the AD's CLAIM against repo reality, not just its file paths. (Corrected this sprint.)
- **Test path drift** (minor): the planned `tests/integration/api/v1/chat/` was a fresh empty subtree (no conftest chain) → moved the writer test to `tests/integration/api/` beside the sibling observer test. Lesson: co-locate a new test with its closest proven sibling rather than inventing a deeper path.
- **Day-0 baseline numbers drift** (D1): the plan assumed Alembic head `0028`; reality `0030` (0029 MFA + 0030 skills). No impact (no migration), but a reminder to `ls migrations/versions | tail` at Day-0 rather than trust memory.

## Q5 — Anti-pattern self-check

- **AP-2** (no orphan / Potemkin): the writer is real persistence, the reader returns real rows — proven by integration tests + a live probe (NOT a stub). Stale-ref corrected. ✅
- **AP-4** (Potemkin): backend-only foundation honestly labelled "gate + probe, NOT a UI drive-through" (the UI lands 57.126); no dead control / fake data introduced. `check_ap4` green. ✅
- **AP-3** (scattering): writer in the chat router (Cat 12 persistence at the api layer, like the sidechain observer); reader in `sessions.py` (sibling of `get_state_snapshot`). ✅
- **AP-6** (YAGNI): reused the existing table/serializer; no speculative abstraction; deferred volume-filter + retention. ✅
- **AP-1 / AP-7 / AP-8** N/A (no loop / context / prompt change). v2 lints 10/10. ✅

## Q6 — Carryover

- **`AD-ChatV2-Session-History-Replay-Phase58` frontend half** (Sprint 57.126, NOT pre-written) — click historical session → fetch `/events` → replay through `mergeEvent` → render historical turns + route the continuation. The replay contract is fixed in design note 37 §4.
- **`AD-ChatV2-Transcript-Volume-Filter`** (🟢, NEW) — optionally drop high-frequency span events from the persisted stream if volume becomes a concern; fidelity-first deferred.
- **`AD-ChatV2-Transcript-Retention`** (🟢, NEW) — a `message_events` TTL / archival policy (Phase 58+).
- Inherited from 57.124: `AD-ExecutionContext-ExplicitApproval-Tidy` + other C-class / chrome Potemkin + operator-portal audit backlog.

## Q7 — Gate summary

mypy `src` **0/370** · flake8 clean · run_all **10/10** (wire 24) · full pytest **2711 passed / 5 skipped** (+8) · Vitest 892 / mockup 51 UNCHANGED (no FE) · Alembic head `0030` (no migration) · live probe PASS (16/16 streamed==persisted).

## Design Note Extract (spike sprint — §5.5)

**File**: `docs/03-implementation/agent-harness-planning/37-chatv2-session-transcript-persistence.md`
**Verified ratio (estimated)**: ~95%
**8-Point Quality Gate**: [x] 1 header [x] 2 file:line [x] 3 decision matrix [x] 4 verification command [x] 5 test fixture [x] 6 open-invariant fence [x] 7 rollback [x] 8 17.md cross-ref (no new contract — reuses Cat 12 + serializer)
**Reviewer pass**: self-review
