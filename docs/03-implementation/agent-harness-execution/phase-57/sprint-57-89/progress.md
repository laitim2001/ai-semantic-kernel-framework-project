# Sprint 57.89 Progress — run() Re-entrancy Refactor Slice 1 (pure extraction)

**Plan**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-89-plan.md`
**Branch**: `feature/sprint-57-89-run-loop-reentrancy` (from `main` `e2948810`)
**Analysis**: `claudedocs/1-planning/run-loop-reentrancy-refactor-analysis-20260608.md`

---

## Day 0 — 2026-06-08 — Plan-vs-Repo Verify + Branch

### Branch
- `feature/sprint-57-89-run-loop-reentrancy` created from main.

### Three-prong verify (GO)

**Prong 1 (path)** — confirmed against the analysis note's ground-truth read:
- `run()` @`loop.py:960`; entire body wrapped in `async with self._tracer.start_span(name="agent_loop.run", LOOP) as root_ctx:` (1002) → `_root_ctx_t0 = monotonic()` (1008) → `try:` (1009) → `yield LoopStarted` (1014) + `yield SpanStarted(LOOP)` (1015) → `async for ev in self._cat9_input_check(...)` (1030, return on LoopCompleted) → **`while True:` (1035)** … `turn_count += 1` (1830) → `finally: yield SpanEnded(LOOP)` (1832-1839).
- The per-turn body has its OWN `async with` TURN span + `try/finally: yield SpanEnded(TURN)` (…1821-1828) inside the while.
- `resume()` @1841 / `_resume_continuation` @1992 — **NOT touched this sprint**.

**Prong 2 (content — accumulator enumeration; the US-2 no-field-loss contract)** — per-run mutables initialized in run()'s preamble + threaded through the while body:
- `messages: list[Message]` (969) — system+user seed; appended assistant/tool messages through the body; passed to `_emit_state_checkpoint` (1811-1818) + PromptBuilder.
- `turn_count` (974) — checked `should_terminate_by_turns` (1037); incremented (1830); stamped `total_turns` on every `LoopCompleted`.
- `tokens_used` (975) — checked `should_terminate_by_tokens` (1045); incremented post-LLM; stamped `total_tokens`.
- `metrics_acc = LoopMetricsAccumulator()` (980) — Sprint 57.2 per-run accumulator (token split / provider attribution / 57.65 cache / etc.); stamped onto `LoopCompleted` fields.
- span carriers: `root_ctx` (1007) + `_root_ctx_t0` (1008).
- **Preservation guarantee**: the extraction is a VERBATIM move of the while block (1035-1831) into `_run_turns`, uniformly dedented by 8 spaces. Every update + every `LoopCompleted` stamp moves intact → no field loss by construction. `check_event_schema_sync` + the existing token/cache tests are the post-move guard.
- Note: `verification_*` fields (57.82) are stamped by the OUTER correction-loop wrapper AFTER `LoopCompleted`, NOT by run() itself → not in run()'s extraction scope (untouched).

**Prong 3 (schema)** — N/A: no DB / migration / ORM change this sprint.

### Baseline capture (to prove "unchanged" at the gate)
- Pre-sprint baseline = main `e2948810`: pytest **2229 passed / 4 skipped**, mypy **0 / 346**, run_all **10/10** (from Sprint 57.88 closeout, same HEAD). Will re-confirm exact numbers in Day-1 before editing.

### Drift findings
- **D-DAY0-1 (design refinement, documented — NOT silent; AP-2)** — plan §3.1 proposed a `LoopState` carrier for `_run_turns`. Day-0 read shows the **raw-locals signature** (`session_id, messages, turn_count, tokens_used, metrics_acc, ctx, root_ctx`) is the lower-risk pure extraction (introducing a new state object mid-extraction could itself shift behavior) AND is still reusable by resume() in Slice 2 (resume unpacks its `LoopState` → these args). → adopt raw-locals; plan §3.1's LoopState framing was aspirational. Recorded here per the "no silent plan rewrite" rule.
- **D-DAY0-2 (span ownership)** — the LOOP `async with` + `try/finally: SpanEnded(LOOP)` STAYS in run() (per plan §3.3); `_run_turns` receives `root_ctx` as a param so the per-turn TURN spans still nest under it. A `return` inside `_run_turns` ends the generator → run()'s `async for` completes → run()'s `finally` fires SpanEnded(LOOP) → behavior-identical (the LOOP SpanEnded still emits on every exit path).
- **D-DAY0-3 (boundary)** — extraction block = the `while True:` (1035) through `turn_count += 1` + comment (1830-1831), i.e. up to (not including) the try's `finally:` at 12-space indent (1832). Uniform dedent by 8 (while `True:` 16→8).

### go/no-go = **GO** (scope unchanged; raw-locals signature adopted per D-DAY0-1; verbatim-move strategy locks zero-behavior-change)

### Next: Day 1 — extract `_run_turns` (programmatic verbatim move + dedent, like Sprint 57.71's 472-line re-indent) → run() delegates → full regression gate (pytest UNCHANGED).
