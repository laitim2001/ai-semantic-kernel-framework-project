# Sprint 57.75 Progress — Inspector Trace + Memory tabs full-chain

**Plan**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-75-plan.md`
**Checklist**: `...sprint-57-75-checklist.md`
**Branch**: `feature/sprint-57-75-inspector-trace-memory` (from `main` `aaf0364c`)
**Closes**: `AD-ChatV2-Inspector-Trace-Phase2` + `AD-ChatV2-Inspector-Memory-Phase2` (program items #1+#2)

---

## Day 0 — 2026-06-03 — Plan-vs-Repo Verify + Decisions

### Decisions (user-locked, AskUserQuestion ×1 + program directive)
- **Scope** = Trace tab + Memory tab BOTH (full A-5 chain: emit → serialize → wire/codegen → frontend consumer).
- **Span granularity** = all 6 span types emit (LOOP/TURN/LLM_CALL/TOOL_EXEC/PROMPT_BUILD/COMPACTION) — most-faithful mockup waterfall.
- **Agent-delegated: yes** — Track A backend (events + loop emit + serialize + wire + codegen + tests) → Track B frontend (store slices + 2 components + ChatInspector + tests), sequential + parent re-verify (Before-Commit item 7).
- Program: "process all carryover except A-4 Tier 2"; this closes #1+#2.

### Day-0 verify (5 researcher passes + parent direct grep/read)
Front-loaded because the carryover ADs assumed both tabs blocked. Verification **changed the premise**:

- **D-DAY0-1 🔴 (refutes stale analysis)**: `cat3-memory-loop-injection-analysis-20260531.md` "production passes no PromptBuilder (memory cut wire)" is STALE. `handler.py:258` injects `make_chat_prompt_builder(..., memory_retrieval=...)` + `:292` `prompt_builder=prompt_builder`; MHist = Sprint 57.64-65 (A-1 fix). router `build_handler` → `mode=="real_llm"` → `build_real_llm_handler` injects → `loop.py:928` true-branch runs `build()` → memory touched. **Memory tab NOT a Potemkin on real_llm.** (2 researchers had cited the stale doc; parent grep on handler.py corrected it — exactly the "verify analysis premise at Day-0" discipline.)
- **D-DAY0-2**: `SpanStarted`/`SpanEnded` (events.py:378-389) + `MemoryAccessed` (events.py:200-203) exist but never emitted/serialized; fields short → SpanStarted +parent_span_id+span_type, MemoryAccessed +summary+time_scale. Extend not create.
- **D-DAY0-3 (Option C, zero blast)**: loop.py 6 span sites already `tracer.start_span(...) as <ctx>` (797/877/912/960/1021/1289); nesting explicit via `trace_context=` kwarg; emit at existing `as <ctx>` reading `.span_id`/`.parent_span_id`. Only loop.py + events.py change.
- **D-DAY0-4**: `get_tracer` defaults OTelTracer (platform_layer/observability/tracer.py:54-65, no env-gate); both OTel + NoOp `.start_span` yield populated TraceContext → emit valid even in tests.
- **D-DAY0-5**: echo_demo path no prompt_builder → Memory tab honest empty (conditional, not Potemkin).
- **D-DAY0-6**: codegen single-source `event_wire_schema.py` WIRE_SCHEMA (18) → `scripts/codegen/generate_event_schemas.py` → `generated/{events.json,loopEvents.generated.ts}`; parity test + `check_event_schema_sync` lint gate. +3 → 21.
- **D-DAY0-7**: `InspectorTree.tsx` (57.72) consumer template; `chatStore.ts` mergeEvent (:245) + rawEvents + derived slices; Trace/Memory each need a case + slice + component + ChatInspector swap.

### Prong status
- Prong 1 (path) GREEN — all files confirmed.
- Prong 2 (content) — D-DAY0-1..7 above.
- Prong 3 (schema) N/A — no DB/migration/ORM.
- Prong 2.5 (child-tree) N/A — new components are leaf; ChatInspector swap only.

### go/no-go = **GO** — Memory blocker refuted, Trace mechanism confirmed zero-blast. No >20% scope drift; both tabs feasible in one full-chain sprint.

---

## Day 1+2 — Backend emit chain (Track A, agent-delegated code-implementer)

Combined backend Track A (Trace + Memory share events.py/sse.py/wire/codegen → one agent for consistency). Agent wall-clock ~25 min; parent Day-0 research + full re-verify.

### Implemented
- **Event fields** (`_contracts/events.py`): `SpanStarted` +`parent_span_id`+`span_type`; `SpanEnded` +`span_type`; `MemoryAccessed` +`summary`+`time_scale`. All additive (defaults preserve existing ctors).
- **Trace emit** (`loop.py`, Option C): 6 span sites `as <ctx>` + `try: yield SpanStarted ... finally: yield SpanEnded` (R3 — every exit closes the span). LOOP SpanStarted moved AFTER `LoopStarted` so `loop_start` stays first public frame; LOOP SpanEnded trails LoopCompleted (span wraps whole loop).
- **Memory emit** (`builder.py` + `loop.py`): `build()` adds `layer_metadata["memory_accesses"]` = per-hint `{scope,time_scale,key=full_content_pointer,summary}` from the already-retrieved `memory_layers` (no extra search); loop yields one `MemoryAccessed(operation="read")` per hint after PromptBuilt. echo_demo (no builder) → 0 (honest empty).
- **serialize+wire+codegen**: `sse.py` +3 nested `{type,data:{...}}` branches; `event_wire_schema.py` 19→22; `generate_event_schemas.py` +3 interface map; regenerated `events.json` + `loopEvents.generated.ts`.

### Drift findings (agent-surfaced, parent-confirmed)
- **D1**: 57.71 added the 6 spans tracer-only; only LOOP/TURN bound `as` → agent added `as <ctx>` to the other 4 (COMPACTION/PROMPT_BUILD/LLM_CALL/TOOL_EXEC) + re-indented bodies (py_compile-verified). loop.py diff ~1393 lines = mostly re-indent.
- **D2**: WIRE_SCHEMA was already 19 (57.68 agent_handoff), not 18 → 19→22.
- **D3**: `MemoryHint` has no `key` field → used `full_content_pointer` as the natural id.
- 5 existing sequence-assertion tests updated to filter diagnostic events via a `_public()` helper (none weakened/deleted — parent read all 5 diffs; assertions intact, comments point to test_observability_coverage.py).

### Tests added
- `test_observability_coverage.py` +142: `test_emits_span_started_ended_with_nesting` (LOOP→TURN→{LLM_CALL,TOOL_EXEC} parent_span_id linkage + start/end pairing) + `test_max_turns_exit_still_emits_loop_span_ended` (R3) + `test_tool_error_turn_still_emits_tool_exec_span_ended` (R3).
- `test_loop_with_prompt_builder.py` +77: `test_loop_emits_memory_accessed_per_hint` (2 hits → 2 events, exact field values) + `test_loop_without_prompt_builder_emits_no_memory_accessed` (honest empty).
- `test_event_wire_schema_parity.py`: 19→22 (3 types moved UNWIRED→WIRED).

### Parent re-verify (Before-Commit item 7) — all gates green (parent-run, not trusting agent report)
- mypy `0/329`; pytest **2089 passed, 4 skipped, 0 failed**; `scripts/lint/run_all.py` **10/10** (incl. check_event_schema_sync codegen-sync + check_llm_sdk_leak + check_ap4_frontend_placeholder); black 607 / isort / flake8 clean.
- Read core emit code (events/builder/sse/wire/codegen) — additive, nested envelope consistent, no fabrication. Read all 5 modified existing tests — filter-only, no weakening. Read 5 new tests — non-shell, rigorous nesting/R3/honest-empty assertions.

---
