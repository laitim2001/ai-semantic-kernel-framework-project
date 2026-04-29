# Sprint 50.1 Progress

**Sprint**：50.1 — Loop Core（Cat 1 + Cat 6）
**Branch**：`feature/phase-50-sprint-1-loop-core`
**Started**：2026-04-29
**Plan**：[`../../../agent-harness-planning/phase-50-loop-core/sprint-50-1-plan.md`](../../../agent-harness-planning/phase-50-loop-core/sprint-50-1-plan.md)
**Story Points**：28 (planned)

---

## Day-by-Day estimate vs actual

| Day | Plan | Actual | Ratio | Notes |
|-----|------|--------|-------|-------|
| Day 0 — Branch + prerequisites + commit docs | 30 min | ~15 min | 50% | pytest invocation `python -m pytest` (cwd in sys.path) — env nuance |
| Day 1 — Output Parser + classifier + StopReason mapping | 6h | ~50 min | 14% | 49.1 stub already had `ParsedOutput`; refactor to `.types` + add `metadata`. MockChatClient already had sequence (49.4). Aligned with 49.x V2 plan保守 ratio |
| Day 2 — AgentLoop while-true main loop + 4 terminators | 6h | ~70 min | 19% | 49.1 ABC sig is `(session_id, user_input, trace_context)` — 50.1 ctor-injects ChatClient/OutputParser/ToolExecutor/system_prompt instead of `run()` params. ToolExecutor + ToolRegistry already split in 49.1. Cancellation `asyncio.current_task().cancelling()` only valid Python 3.11+ |
| Day 3 | 6h | — | — | pending |
| Day 3 | 6h | — | — | pending |
| Day 4 | 6h | — | — | pending |
| Day 5 | 4h | — | — | pending |

---

## Daily highlights

### Day 0 (2026-04-29)
- Branch `feature/phase-50-sprint-1-loop-core` from 49.4 closeout HEAD `3d385bc`
- Prerequisites green: pytest 150 PASS / mypy 124 files clean / 4 V2 lints OK
  - Note: 49.4 progress claimed 143 PASS; actual is 150 (closeout count drift)
  - Note: pytest must be invoked as `python -m pytest` (cwd in sys.path) — bare `pytest` CLI fails on `from tests.conftest import ...`
- Day 0 commit: `74dd2e4 docs(sprint-50-1): plan + checklist + Phase 50 README`

### Day 1 (2026-04-29)
- `output_parser/types.py` — extracted `ParsedOutput` from `_abc.py` (Cat boundary: ABC files own only ABC); added `metadata: dict` field for Cat 11 handoff future ext; added `OutputType` enum
- `output_parser/parser.py` — `OutputParserImpl` with `Tracer` injection (NoOpTracer fallback); pure ChatResponse → ParsedOutput transform; native tool_calls only, no regex
- `output_parser/classifier.py` — `classify_output()` 3-way dispatch; `HANDOFF_TOOL_NAME = "handoff"` reserved per 17.md §3.1
- `_abc.py` refactored — imports `ParsedOutput` from `.types`; Modification History updated
- `__init__.py` — full export incl `OutputParserImpl` / `classify_output` / `OutputType` / `HANDOFF_TOOL_NAME`
- 21 new unit tests (parser × 5, classifier × 3, stop_reason × 13)
- Tracer signature gotcha: `start_span` is **async context manager** + requires `category: SpanCategory` kwarg; first impl used sync `with` + missing category → caught immediately
- Day 1 commit: `068d2fd feat(output-parser, sprint-50-1): OutputParser + classifier + StopReason mapping (Day 1)`

### Day 2 (2026-04-30)
- `orchestrator_loop/termination.py` — 4 pure terminators + `TerminationReason` 7-enum + `TripwireTerminator` ABC stub for Cat 9
- `orchestrator_loop/loop.py` — `AgentLoopImpl(AgentLoop)` while-true; ctor-injects all 4 collaborators (ChatClient / OutputParser / ToolExecutor / ToolRegistry) + system_prompt + max_turns + token_budget; per-49.1-ABC sig `run(session_id, user_input, trace_context)`; 3-way dispatch (FINAL / HANDOFF / TOOL_USE); tool result `Message(role="tool", tool_call_id=tc.id)` feedback mandatory; `asyncio.CancelledError` boundary at chat() and execute(); `Tracer.start_span(category=ORCHESTRATOR)` wraps run()
- `orchestrator_loop/__init__.py` — full export incl AgentLoopImpl + termination
- `resume()` left as stub yielding `LoopCompleted(error)` until Phase 53.1 Checkpointer
- 17 new unit tests (termination × 10 + loop × 7); validates AP-1 cure, tool-message feedback, cancellation safety, HANDOFF stub
- Day 2 commit: `6f32d9a feat(orchestrator-loop, sprint-50-1): AgentLoop while-true main loop + 4 terminators (Day 2)`

---

## Surprises / fixes recorded

1. **`pytest` CLI vs `python -m pytest`** (Day 0) — bare `pytest` doesn't add cwd to `sys.path`, breaks `from tests.conftest import ...`. Use `python -m pytest`. (49.4 progress.md silently uses module form; should add to testing.md.)
2. **`Tracer.start_span` is async + requires `category`** (Day 1.1) — sig is `AbstractAsyncContextManager` + `category: SpanCategory` kwarg required. First parser impl used sync `with` and only passed `name` — caught by reading `_abc.py`.
3. **`ParsedOutput` already inline in `_abc.py` from 49.1** (Day 1.1) — plan called for new dataclass; instead refactored existing into `.types` + added `metadata` field. Avoided duplicate definition (17.md single-source).
4. **MockChatClient sequence already done in 49.4** (Day 1.3) — `responses: list[ChatResponse]` + `pop(0)` IS the sequence behavior. Day 1.3 task 2 obviated.
5. **49.1 AgentLoop ABC sig is minimal** (Day 2.2) — `run(session_id, user_input, trace_context)` only. 50.1 plan called for `(messages, tools, system_prompt, max_turns, ...)` as run() params; instead made these CTOR-configured to keep ABC stable. Phase 53.1+ may revisit if per-run override needed.
6. **`ToolRegistry` + `ToolExecutor` are separate ABCs in 49.1** (Day 2.2) — plan called them collectively "tool_registry"; Loop now injects both (registry for `list()` to populate ChatRequest.tools, executor for `execute()` per tool_call). Cleaner than collapsing.
7. **`asyncio.current_task().cancelling()` is Python 3.11+** (Day 2.1) — env is 3.12.10 so OK. `should_terminate_by_cancellation()` returns True only inside `except CancelledError:` handler before re-raise.
8. **`datetime.utcnow()` deprecation warnings** (Day 2 tests) — 49.1 events.py uses `field(default_factory=datetime.utcnow)`. 28 warnings emitted but not failing. CARRY: switch to `lambda: datetime.now(UTC)` in a future trivial-fix sprint.

---

## Cumulative branch state

```
feature/phase-50-sprint-1-loop-core
├── 74dd2e4 docs(sprint-50-1): plan + checklist + Phase 50 README
├── 068d2fd feat(output-parser, sprint-50-1): OutputParser + classifier + StopReason mapping (Day 1)
├── c72ef85 docs(sprint-50-1): Day 1 progress + checklist [x] update (Day 1)
└── 6f32d9a feat(orchestrator-loop, sprint-50-1): AgentLoop while-true main loop + 4 terminators (Day 2)
```

4 commits. Branch is ~40 commits ahead of `main` (carries Phase 49 baseline).

---

## Quality gates (current = end of Day 2)

- pytest: **188 / 0 SKIPPED / 4.26s** (49.4 baseline 150 + Day 1 21 + Day 2 17)
- mypy --strict: 0 issues / **129 source files** (49.4 124 + 50.1 +5: types / parser / classifier / termination / loop)
- 4 V2 lints: all OK (duplicate-dataclass 57 classes / cross-category-import / sync-callback / LLM SDK leak)
- LLM SDK leak grep on agent_harness/ + business_domain/ + platform_layer/ + runtime/ + api/: **0**
- alembic from-zero cycle: ✅ (head = `0010_pg_partman` from 49.4)
