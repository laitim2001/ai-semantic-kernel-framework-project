# Re-Verification of Corrected Flows Files (50 pts)

> **Date**: 2026-03-31
> **Method**: Post-correction re-verification — read corrected files, cross-check each correction against source code
> **Scope**: flows-01-to-05.md (25 pts) + flows-06-to-08.md (25 pts)

---

## flows-01-to-05.md (25 pts)

### P1-P5: Wave 12 Corrections Applied Check

**P1**: max_sessions=100 ✅
- Doc (line 114): "LRU cache with `OrderedDict`, max 100 sessions (default)"
- Source: `session_factory.py:41` `max_sessions: int = 100` — Correct.

**P2**: navigate-only onSuccess ✅
- Doc (line 331): "navigate('/agents') only (no cache invalidation)"
- Source: `CreateAgentPage.tsx:169-171` — `onSuccess: () => { navigate('/agents'); }` — no `invalidateQueries`. Correct.

**P3**: WorkflowDefinitionAdapter line ref ✅
- Doc (line 383): "workflow.py:113+ (imports at line 37)"
- Source: `workflow.py:113` `class WorkflowDefinitionAdapter` confirmed. Correct.

**P4**: MULTI approval note ✅
- Doc (line 489): "ApprovalType.MULTI enum is defined in controller.py for quorum-based approval, but is not implemented in the current pipeline flow — only single-approver requests are created."
- Source: `controller.py:47-59` has MULTI enum but `request_approval()` only creates single. Correct.

**P5**: ResultSynthesiser removed from Flow 5 ✅
- Doc (line 722-723): "Aggregation is concatenation with role headers (no ResultSynthesiser in current code)."
- Doc (line 763): "Result Synthesis | N/A | Concatenation with role headers (no ResultSynthesiser in current code)"
- Doc (line 773): "Result Synthesis | REAL — concatenation with role headers"
- Source: `execution.py:317-325` confirms concatenation only. No ResultSynthesiser usage. Correct.

### P6-P10: Surrounding Content Still Accurate

**P6**: _execute_swarm line range ✅
- Doc (line 669): "execution.py:223-360+"
- Source: `_execute_swarm` starts line 223, main try block ends ~358, with fallback extending to ~392. "223-360+" is accurate. Correct.

**P7**: Step B5 result aggregation line ref ✅
- Doc (line 718): "execution.py:317+"
- Source: `execution.py:317` "Build combined content" section confirmed. Correct.

**P8**: RoutingHandler line range ✅
- Doc (line 171): "routing.py:135-226"
- Source: `_handle_direct_routing` at routing.py:135 confirmed. Correct.

**P9**: Bootstrap assembly line range ✅
- Doc (line 123): "bootstrap.py:39-101"
- Source: `bootstrap.py` `build()` starts at 39, handler wiring through ~101. Correct.

**P10**: SessionFactory line range ✅
- Doc (line 110): "session_factory.py:52-71"
- Source: `get_or_create` at line 52 confirmed. Correct.

### P11-P15: Flow 1-2 Mermaid Diagram Participants

**P11**: Flow 1 Mermaid participants ✅
- Doc lists: User, Frontend (SSE), API Gateway, 3-Tier Router, Mediator, LLM Service, MCP Tools
- All are accurate abstractions of actual code components. Correct.

**P12**: Flow 1 Mermaid message flow ✅
- POST /orchestrator/chat/stream → Route intent → Execute pipeline → Generate response → SSE events → TEXT_DELTA stream
- Matches mediator.execute() pipeline. Correct.

**P13**: Flow 4 Mermaid participants ✅
- Doc lists: User, Frontend, API Gateway, Risk Assessor, HITL Controller, Teams Notification
- All exist as actual classes. Correct.

**P14**: Flow 2 has no Mermaid diagram ✅
- Flow 2 (CRUD) has no sequence diagram. Appropriate — it's a simple CRUD flow. No issue.

**P15**: Flow 1 Mermaid optional "Tool Calls" block ✅
- Shows `opt Tool Calls` block with MCP tools. Matches AgentHandler function calling loop (max 5 iterations). Correct.

### P16-P20: Flow 3-4 Barrier/Gap Descriptions

**P16**: Flow 3 stats always zero ✅
- Doc (line 452): "stats always returns 0 for llm_calls/tokens/cost (line 451-455) — metrics not propagated from node executors"
- Source: `routes.py:450-455` hardcodes zeroes. Correct.

**P17**: Flow 3 AGENT nodes require LLM ✅
- Doc (line 451): "AGENT node execution requires Azure OpenAI config"
- Accurate — AGENT-type nodes need an LLM service. Correct.

**P18**: Flow 4 InMemoryApprovalStorage barrier ✅
- Doc (line 488): "InMemoryApprovalStorage loses data on server restart. No Redis/DB persistence."
- Source: `controller.py` uses InMemoryApprovalStorage. Correct.

**P19**: Flow 4 three disconnected approval systems ✅
- Doc (line 460): "3 separate approval systems" — System A (Phase 28), System B (Phase 42), System C (Phase 4)
- All three confirmed to exist independently. Correct.

**P20**: Flow 4 timeout fails open ✅
- Doc (line 527): "If timeout: logs warning, pipeline continues (fails open)"
- Source: `mediator.py:399-401` catches TimeoutError, logs warning, continues. Correct.

### P21-P25: Flow 5 Swarm Descriptions

**P21**: Phase 29 demo path vs Phase 43 real path ✅
- Doc (lines 604-606): Two paths clearly described — demo via `/swarm/demo/start`, real via orchestrator pipeline.
- Source confirms both paths exist. Correct.

**P22**: TaskDecomposer.decompose() description ✅
- Doc (line 651-653): `TaskDecomposition { original_task, mode, sub_tasks: List[DecomposedTask], reasoning }`
- Source: `task_decomposer.py:70-75` matches. Correct.

**P23**: Semaphore(3) for parallel workers ✅
- Doc (line 673): "asyncio.Semaphore(3) for max 3 concurrent workers"
- Source: `execution.py:288` `semaphore = asyncio.Semaphore(max_concurrent)` where `max_concurrent = 3`. Correct.

**P24**: SwarmWorkerExecutor per-worker LLM loop ✅
- Doc (lines 689-707): Describes independent LLM function calling loop per worker with max 5 iterations.
- Source: `worker_executor.py` confirmed. Correct.

**P25**: Phase 29 vs Phase 43 SSE protocol mismatch ✅
- Doc (line 775): "Phase 29 event format (AG-UI CustomEvent) vs Phase 43 format (Pipeline SSE) are different protocols"
- Phase 29 uses SwarmEventEmitter (AG-UI), Phase 43 uses PipelineEventEmitter (Pipeline SSE). Correct.

---

## flows-06-to-08.md (25 pts)

### P26-P30: Wave 13 Corrections Applied Check

**P26**: SSE 13 types (not 14) ✅
- Doc (line 171): "SSE Event Type Registry (13 Types)"
- Source: `sse_events.py:39-54` has exactly 13 enum members (PIPELINE_START through PIPELINE_ERROR). Correct.

**P27**: Bootstrap clarification (routes.py vs SessionFactory) ✅
- Doc (lines 50-51): Step 0d clearly says "_get_bootstrap() lazy-initialises ... used only for health check and tool registry; **NOT** used to create per-session mediators"
- Step 0e says "Routes call _get_session_factory().get_or_create(session_id) ... factory creates per-session mediator via _create_orchestrator() ... which instantiates a **separate** OrchestratorBootstrap per session"
- Source: `routes.py:33-48` `_get_bootstrap()` for health/registry only; `routes.py:65-81` `_get_session_factory()` uses bootstrap only for LLM service extraction; `session_factory.py:95` `_create_orchestrator()` creates separate bootstrap. Correct.

**P28**: dispatch_to_claude NOT registered note ✅
- Doc (line 218): "dispatch_to_claude exists as handle_dispatch_to_claude() (line 282) but is **NOT registered** in register_all()"
- Source: `dispatch_handlers.py:282` method exists; `dispatch_handlers.py:456-469` register_all() maps 8 tools without dispatch_to_claude. Correct.

**P29**: _write_to_longterm misleading name documented ✅
- Doc (line 309): "Misleading name: calls add() with MemType.CONVERSATION and no explicit importance, so default importance=0.0 applies → layer selection routes to **WORKING** layer, not long-term"
- Source: `memory_manager.py:387-406` calls `self._memory.add(content=..., memory_type=MemType.CONVERSATION)` without importance arg; `unified_memory.py:130-171` routes CONVERSATION + importance<0.5 to WORKING. Correct.

**P30**: ConversationStateStore.save() signature mismatch documented ✅
- Doc (line 321): "save(state: ConversationState) accepts a single ConversationState object ... not keyword args. Mediator at lines 714-719 passes keyword args — signature mismatch"
- Source: `conversation_state.py:96` `async def save(self, state: ConversationState) -> None`; `mediator.py:714-719` calls `save(session_id=..., messages=..., ...)` with kwargs. Mismatch confirmed. Correct.

### P31-P35: PipelineRequest/Response Field Lists

**P31**: PipelineRequest fields ✅
- Doc (line 49): "content, source, mode, user_id, session_id, metadata, timestamp" (Step 0a/0c)
- Source: `pipeline.py:25-34` has: content, source, mode, user_id, session_id, metadata, timestamp. **All 7 fields listed.** Correct.

**P32**: PipelineResponse fields ✅
- Doc (line 160): Lists "content, intent_category, confidence, risk_level, routing_layer, execution_mode, suggested_mode, framework_used, session_id, is_complete, **task_id**, tool_calls, processing_time_ms"
- Source: `pipeline.py:37-52` has all 13 fields including task_id. Correct.

**P33**: Mode mapping values ✅
- Doc (lines 56-59): chat→CHAT_MODE, workflow→WORKFLOW_MODE, swarm→SWARM_MODE, hybrid→HYBRID_MODE
- Source: `routes.py:304-310` confirmed. Correct.

**P34**: PipelineRequest Pydantic model location ✅
- Doc (line 49): "integrations/contracts/pipeline.py:25-34"
- Source: `pipeline.py:25` class starts. Correct.

**P35**: PipelineResponse includes task_id ⚠️ Minor note
- Doc (line 160) includes task_id in the field list — this was flagged as missing in earlier verification (P9 in flows-06-08 report). Now it IS listed. Correct fix applied.

### P36-P40: Memory Architecture Description

**P36**: Layer 1 Working Memory ✅
- Doc (line 289): "Layer 1: Working Memory (Redis, TTL 30 min)"
- Source: `unified_memory.py:248-249` Redis SETEX with working_memory_ttl. Correct.

**P37**: Layer 2 Session Memory "Redis (PostgreSQL planned)" ✅
- Doc (line 290): "Layer 2: Session Memory (Redis (PostgreSQL planned), TTL 7 days)"
- Source: `unified_memory.py:273` comment "In production, this would use PostgreSQL", uses Redis SETEX. Correct description.

**P38**: Layer 3 Long-term Memory ✅
- Doc (line 291): "Layer 3: Long-term Memory (mem0 + Qdrant, permanent)"
- Source: `unified_memory.py:227-233` calls `self._mem0_client.add_memory()`. Correct.

**P39**: ConversationStateStore separate from 3-layer ✅
- Doc (line 293): "ConversationStateStore (Redis, TTL 24h) -- separate from 3-layer memory"
- Source: `conversation_state.py` is in `infrastructure/storage/`, separate from `integrations/memory/unified_memory.py`. Correct.

**P40**: Session Memory barrier ✅
- Doc (line 397): "Session Memory is Redis | Session memory uses Redis with longer TTL instead of PostgreSQL"
- Source: `unified_memory.py:271-280` confirmed Redis only with PostgreSQL comment. Correct.

### P41-P45: Cross-Flow Integration Map

**P41**: Flow 6 Step 1 reads Flow 8 Part B ✅
- Doc (line 408): "Step 1 ─── reads ──── Flow 8 Part B (Memory Retrieval)"
- Source: ContextHandler calls retrieve_relevant_memories(). Correct.

**P42**: Flow 6 Step 5 calls Flow 7 ✅
- Doc (line 409): "Step 5 ─── calls ──── Flow 7 (if tool_call = dispatch_workflow/dispatch_swarm)"
- Source: AgentHandler tool loop -> OrchestratorToolRegistry -> DispatchHandlers. Correct.

**P43**: Flow 6 Step 8 writes Flow 8 Part A ✅
- Doc (line 411): "Step 8 ─── writes ──── Flow 8 Part A (Memory Write)"
- Source: `mediator.py:512-538` memory write. Correct.

**P44**: Flow 7 task lifecycle ✅
- Doc (lines 413-417): create → queue → execute → update
- Source: dispatch_handlers → ARQ → task_functions → _update_task_status. Correct.

**P45**: Flow 8 three-layer pattern ✅
- Doc (lines 419-422): Part A writes, Part B reads, Part C indexes RAG
- Source confirmed all three subsystems. Correct.

### P46-P50: Readiness Ratings

**P46**: Flow 6 Pipeline readiness 70% ✅
- Doc (line 429): "70% -- works for chat mode; workflow/swarm dispatch needs real executors"
- Assessment is reasonable. Chat mode E2E confirmed; ExecutionHandler stubs for MAF/Claude. Correct.

**P47**: Flow 7 Async Dispatch readiness 30% ✅
- Doc (line 430): "30% -- infrastructure exists but actual execution not connected"
- task_functions.py:53 has TODO for actual MAF execution. Correct assessment.

**P48**: Flow 8 Memory readiness 45% ✅
- Doc (line 431): "45% -- works when all external services available; fragile dependency chain; per-message writes go to working memory, not long-term despite method name"
- This was adjusted down from 50% per verification recommendation (40-45%). Now at 45%. Reasonable.

**P49**: Barrier table completeness ✅
- Doc (lines 193-203): 6 barriers listed for Flow 6, all verified against source. Correct.

**P50**: Flow 8 barrier table ✅
- Doc (lines 389-400): 8 barriers for Flow 8. mem0 init, Qdrant, EmbeddingService, Redis, Session Memory Redis-only, no auto-summarisation, LLM for summarisation, RAG Qdrant. All confirmed. Correct.

---

## Summary

| Section | Points | ✅ | ⚠️ | ❌ |
|---------|--------|----|----|-----|
| flows-01-to-05 P1-P5 (Wave 12 corrections) | 5 | 5 | 0 | 0 |
| flows-01-to-05 P6-P10 (surrounding content) | 5 | 5 | 0 | 0 |
| flows-01-to-05 P11-P15 (Mermaid diagrams) | 5 | 5 | 0 | 0 |
| flows-01-to-05 P16-P20 (barrier/gap) | 5 | 5 | 0 | 0 |
| flows-01-to-05 P21-P25 (swarm) | 5 | 5 | 0 | 0 |
| flows-06-to-08 P26-P30 (Wave 13 corrections) | 5 | 5 | 0 | 0 |
| flows-06-to-08 P31-P35 (Request/Response) | 5 | 4 | 1 | 0 |
| flows-06-to-08 P36-P40 (Memory arch) | 5 | 5 | 0 | 0 |
| flows-06-to-08 P41-P45 (Cross-flow map) | 5 | 5 | 0 | 0 |
| flows-06-to-08 P46-P50 (Readiness) | 5 | 5 | 0 | 0 |
| **Total** | **50** | **49** | **1** | **0** |

**Accuracy**: 49/50 = **98.0%** (49 ✅ + 1 ⚠️ + 0 ❌)

## New Errors Introduced by Corrections

**None found.** All Wave 12 and Wave 13 corrections were applied correctly and did not introduce any new inaccuracies.

The single ⚠️ (P35) is a minor observation that the task_id field inclusion is now correct — it was previously flagged as missing and is now properly listed. This is a positive fix, not a new error.

## Verdict

The corrected flows-01-to-05.md and flows-06-to-08.md files are now **highly accurate** at 98% verification rate. No corrections introduced new errors. The documents are production-quality for V9.
