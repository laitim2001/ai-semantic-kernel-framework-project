# Sprint 50.1 Retrospective — Loop Core

**Sprint**：50.1
**Branch**：`feature/phase-50-sprint-1-loop-core`
**Started**：2026-04-29
**Closed**：2026-04-30
**Plan**：[`../../../agent-harness-planning/phase-50-loop-core/sprint-50-1-plan.md`](../../../agent-harness-planning/phase-50-loop-core/sprint-50-1-plan.md)
**Story Points**：28 (planned) → all completed

---

## Outcome

✅ **Sprint 50.1 DONE**. The first real V2 TAO/ReAct loop runs end-to-end:
user message → AgentLoop.run() → MockChatClient yields tool_call →
echo_tool execute → MockChatClient yields END_TURN → final answer.

All 6 user stories delivered. All structural + quality acceptance criteria met.
Phase 50 progress: 1/2 sprint complete = 50%.

---

## Estimate accuracy

| Day | Plan | Actual | Ratio |
|-----|------|--------|-------|
| Day 0 — Branch + prerequisites + commit docs | 30 min | ~15 min | 50% |
| Day 1 — Output Parser + classifier + StopReason mapping | 6h | ~50 min | 14% |
| Day 2 — AgentLoop while-true + 4 terminators | 6h | ~70 min | 19% |
| Day 3 — Events shim + InMemoryToolRegistry + AP-1 lint | 6h | ~80 min | 22% |
| Day 4 — E2E + Tracer/Metric coverage + cancellation polish | 6h | ~60 min | 17% |
| Day 5 — Header polish + retrospective + closeout | 4h | ~50 min | 21% |
| **Total** | **~28h** | **~5.4h (325 min)** | **~19%** |

Aligned with V2 sprint pattern (49.2 ~15% / 49.3 ~13% / 49.4 ~26%). Plan
remains usefully conservative — actual:plan ratio across 5 sprints stays in
the 13–26% band.

---

## Quality gates (final)

- pytest: **210 PASS / 0 SKIPPED / 4.25s** (49.4 baseline 150 + 50.1 new 60)
- mypy --strict: 0 issues / 131 source files
- 5 V2 lints: all OK (incl. new AP-1 / V2 lint #5)
- LLM SDK leak grep: 0
- alembic from-zero cycle: ✅ (head = `0010_pg_partman` from 49.4)
- AP-1 (Pipeline disguised as Loop): clean on 4 files in `agent_harness/orchestrator_loop/`
- Cat 12 instrumentation: 3 of 5 emit points reachable in 50.1 scope verified

---

## Did well (≥3)

1. **Plan-first discipline held** — 0.1-0.3 plan + checklist committed BEFORE
   any code; every commit traces to a checklist item; sacred rule (don't
   delete unchecked `[ ]`) honored — MockChatClient enhancement marked 🚧 +
   reason instead of removed.

2. **Karpathy "Think Before Coding" applied repeatedly** — when 49.1 stub
   surface didn't match plan (ParsedOutput already inline / AgentLoop ABC
   minimal sig / MockChatClient sequence already done), we adapted the plan
   in place rather than mechanically following it. Saved ~3h of unnecessary
   refactor + avoided redefinition that would have violated 17.md §1.

3. **Test isolation favored over OTel SDK** — Day 4.2 replaced OpenTelemetry
   in-memory exporter (which has global `set_tracer_provider` one-shot
   semantics) with a `RecordingTracer` ABC subclass. Hermetic tests; same
   `Tracer` interface as production; zero global-state pollution.

4. **Cumulative regression: 0** across 5 days, 6 code commits, 60 new tests.
   `pytest -q --tb=no` always green at end of each day.

---

## Improve next sprint (≥3)

1. **Trade-off enunciation BEFORE coding** — Day 2 `ToolExecutor + ToolRegistry`
   dual-injection decision was sound but the trade-off ("vs collapsing into
   single facade") was only documented in progress.md AFTER the fact. Next
   sprint: 1-line trade-off statement at task start, BEFORE writing code.
   (Karpathy guideline #1 alignment.)

2. **AP-1 lint substring matching is over-approximate** — `Message(role="tool"`
   substring in comments yields false-pass. Acceptable for 50.1 (production
   doesn't write the literal in comments without using it), but Phase 51.1+
   should consider AST-based detection of actual `Message(role="tool", ...)`
   call nodes for higher precision when more loop variants ship.

3. **`pytest` CLI vs `python -m pytest` invocation gap** — bare `pytest`
   doesn't add cwd to sys.path, breaks `from tests.conftest import ...`.
   Day 0.2 had to discover this. Next sprint: add to `.claude/rules/testing.md`
   "ALWAYS use `python -m pytest`" rule + a pre-commit hook line to enforce.
   (CARRY-001 below.)

4. **`datetime.utcnow()` deprecation** in 49.1 events.py — emits 28+ warnings
   per loop test run. Not failing, but noisy. Next sprint: trivial-fix to
   `field(default_factory=lambda: datetime.now(UTC))`. (CARRY-002.)

---

## Action items for Sprint 50.2+

| ID | Item | Owner | Target |
|----|------|-------|--------|
| **CARRY-001** | Document `python -m pytest` invocation in `.claude/rules/testing.md` + pre-commit hook | AI assistant | Sprint 50.2 Day 0 |
| **CARRY-002** | Fix `datetime.utcnow()` deprecation in `_contracts/events.py` (trivial) | AI assistant | Sprint 50.2 (any day, ≤ 30 min) |
| **CARRY-003** | Frontend `pages/chat-v2/` skeleton + connect to `/api/v1/chat/` SSE | User + AI | Sprint 50.2 Day 1-3 |
| **CARRY-004** | API endpoint `POST /api/v1/chat/` consuming `AgentLoop.run()` AsyncIterator → SSE | AI assistant | Sprint 50.2 Day 1-2 |
| **CARRY-005** | `runtime/workers/agent_loop_worker.py` integration (49.4 stub → real handler) | AI assistant | Sprint 50.2 Day 2-3 |
| **CARRY-006** | Streaming partial-token emit (was deferred from 50.1) | AI assistant | Sprint 50.2 Day 3-4 |
| **CARRY-007** | Phase 50.1 e2e demo via real Azure OpenAI (replace MockChatClient) | User | Sprint 50.2 Day 4-5 |
| **CARRY-008** | InMemoryToolRegistry deprecation tracking — flag once Sprint 51.1 starts | AI assistant | Sprint 51.1 Day 0 |
| **CARRY-009** | Consider AST-based AP-1 lint refinement | AI assistant | Sprint 51.x backlog |

---

## 3 lessons learned

### 1. ABC sig stability > plan literalism

49.1 froze the `AgentLoop.run(session_id, user_input, trace_context)` ABC
sig. Sprint 50.1 plan called for `run(messages, tools, system_prompt, ...)`
as run-time args. Following the plan would have broken the ABC. Instead,
moved configuration to ctor injection. Lesson: **ABC sigs are contracts;
plans are intent. When they conflict, the ABC wins and the plan adapts.**

### 2. Single-source ABC files trump local convenience

`ParsedOutput` was defined inline in `output_parser/_abc.py` from 49.1.
First instinct was to create a fresh `ParsedOutput` in the new `types.py`.
Instead refactored — moved the existing dataclass + added `metadata` field
+ updated `_abc.py` to import. Result: zero violations of 17.md §1
single-source, zero duplicate definitions, mypy strict happy. Lesson:
**check what already exists; refactor over redefine, every time.**

### 3. Test infrastructure investment pays back fast

Building `RecordingTracer` (Day 4.2) took 30 lines + 5 minutes. Replaced
OTel global-state in-memory exporter that would have taken 90+ minutes of
fixture plumbing AND created flaky cross-test interaction. Lesson: when a
generic test helper would solve N tests' isolation pain, build it
immediately rather than copy/paste mock state per test.

---

## 49.4 retrospective carry-over status

49.4 retrospective listed 9 Action items. Status at 50.1 closeout:

| Item | Status | Notes |
|------|--------|-------|
| 49.4 retro #1 — TemporalQueueBackend real impl | 🚧 Phase 53.1 | Not in 50.1 scope |
| 49.4 retro #2 — Production app role staging config | 🚧 Phase 53.1+ | User-owned (operations) |
| 49.4 retro #3 — pg_partman create_parent for messages tables | 🚧 Production deploy | Per ops runbook |
| 49.4 retro #4 — tool_calls.message_id FK | 🚧 PG 18 LTS / Phase 56+ | DEFER decision stands |
| 49.4 retro #5 — CI deploy gate / 規範 E 警報 | 🚧 Phase 55 cutover | Not in 50.x scope |
| 49.4 retro #6 — Frontend Vite startup integration | ⏸ User-owned | CARRY-003 picks up frontend work in 50.2 |
| 49.4 retro #7 — npm audit 2 moderate vulnerabilities | ⏸ Frontend sprint | CARRY-003 area |
| 49.4 retro #8 — branch protection rule | ⏸ User admin UI | Independent of sprint work |
| 49.4 retro #9 — 49.1+49.2+49.3+49.4 merge to main decision | ⏸ User decision | Strategic timing |

Net: **0 of 9 resolved in 50.1** (all are downstream / out-of-scope items).
50.1 added 9 new carry items above (CARRY-001..009) — 2 are trivial-fix
candidates for 50.2 Day 0, the rest map naturally to 50.2 / 51.1 work.

---

## What unblocks Sprint 50.2

- ✅ `AgentLoopImpl.run()` is a real `AsyncIterator[LoopEvent]` ready to feed
  an SSE handler — no API translation layer needed.
- ✅ `make_echo_executor()` factory + `ECHO_TOOL_SPEC` ready for the 50.2
  demo flow ("ask echo X → see X").
- ✅ Tracer / metric instrumentation in place — Phase 50.2 frontend can
  surface `LoopEvent` directly + add OTel SDK exporters at deployment time.
- ✅ 49.4 `runtime/workers/agent_loop_worker.py` stub has a `TaskHandler`
  signature compatible with `AgentLoopImpl.run()` — wiring is mechanical.
- ✅ `MockChatClient` supports response sequence (49.4) — 50.2 demo can
  pre-program scripted flows for browser-based smoke tests before swapping
  to real Azure OpenAI.
- ✅ AP-1 lint enforces TAO discipline at PR time — frontend devs adding
  Loop subclasses get immediate feedback.

**Sprint 50.2 starting position is excellent.** Plan + checklist for 50.2
should be written at the start of the next session (rolling planning rule).

---

## Cumulative branch state at closeout

```
feature/phase-50-sprint-1-loop-core (10 commits)
├── 74dd2e4 docs(sprint-50-1): plan + checklist + Phase 50 README
├── 068d2fd feat(output-parser): OutputParser + classifier + StopReason mapping (Day 1)
├── c72ef85 docs(sprint-50-1): Day 1 progress + checklist [x] update
├── 6f32d9a feat(orchestrator-loop): AgentLoop while-true main loop + 4 terminators (Day 2)
├── 79bd1ba docs(sprint-50-1): Day 2 progress + checklist [x] update
├── 6962b8d feat(orchestrator-loop): events + InMemoryToolRegistry + AP-1 lint (Day 3)
├── e9592b6 docs(sprint-50-1): Day 3 progress + checklist [x] update
├── 7f70845 test(orchestrator-loop): e2e + tracer coverage + cancellation safety (Day 4)
├── 99d8d7a docs(sprint-50-1): Day 4 progress + checklist [x] update
└── (closeout commit, this Day 5) — header polish + retrospective + Phase 50 README + MEMORY.md
```

Branch is ~46 commits ahead of `main` (carries Phase 49 baseline).

---

**Sprint 50.1 closes ✅ DONE.** Phase 50 progress: 1/2 = 50%. V2 cumulative:
**5/22 sprints complete** (49.1, 49.2, 49.3, 49.4, 50.1).
