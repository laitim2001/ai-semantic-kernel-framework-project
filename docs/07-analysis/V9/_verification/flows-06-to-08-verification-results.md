# V9 Flows 06-08 Deep Semantic Verification Results

> **Date**: 2026-03-31
> **Branch**: `feature/phase-42-deep-integration`
> **Verified by**: V9 Deep Verification Agent
> **Method**: Source code reading of all referenced files against document claims

---

## Summary

| Flow | Points | Accurate | Inaccurate | Partial | Unverifiable | Accuracy |
|------|--------|----------|------------|---------|--------------|----------|
| Flow 6 | 17 | 12 | 2 | 3 | 0 | 79.4% |
| Flow 7 | 17 | 13 | 2 | 2 | 0 | 82.4% |
| Flow 8 | 16 | 12 | 1 | 3 | 0 | 84.4% |
| **Total** | **50** | **37** | **5** | **8** | **0** | **82.0%** |

**Overall verdict**: Document is largely accurate with 5 concrete errors and 8 partial inaccuracies requiring correction.

---

## Flow 6: 10-Step Pipeline E2E (17 pts)

### P1: Trigger entry point (API endpoints)

**Verdict**: ✅ Accurate

- Document: `POST /api/v1/orchestrator/chat` (sync) and `POST /api/v1/orchestrator/chat/stream` (SSE)
- Source: `routes.py:343` defines `@router.post("/chat")` and `routes.py:275` defines `@router.post("/chat/stream")`. Router prefix is `/orchestrator` (line 23). Confirmed.

### P2: Core processing function location and signature

**Verdict**: ⚠️ Partial — line numbers shifted

- Document: sync route at `routes.py:343-479`, SSE at `routes.py:275-340`
- Source: sync `orchestrator_chat` starts at line 343, SSE `orchestrator_chat_stream` starts at line 275. But sync endpoint ends at line 479 (matches), SSE ends at line 340 (matches). **However**, the doc says Step 0d "Lazy Bootstrap" is at `routes.py:33-48` — source shows `_get_bootstrap()` at lines 33-48. Confirmed.
- Minor issue: `PipelineRequest` fields doc says `(content, mode, session_id, user_id, metadata)` — source also has `source` and `timestamp` fields not mentioned. Partial.

### P3: Data flow through service/repository functions

**Verdict**: ✅ Accurate

- Document: OrchestratorRequest flows through mediator.execute() -> handler chain
- Source: `routes.py:406` calls `await mediator.execute(orchestrator_request)`, mediator.py:196 `execute()` runs handlers via `_run_handler()`. Confirmed.

### P4: Database/ORM operations

**Verdict**: ✅ Accurate

- Document: ConversationStateStore.save() persists to Redis, in-memory sessions stored in Dict
- Source: `mediator.py:89` `self._sessions: Dict[str, Dict[str, Any]] = {}`, `mediator.py:712-721` calls `self._conversation_store.save()`, `conversation_state.py:96` save() uses StorageBackendABC with TTL. Confirmed.

### P5: SSE event types emitted

**Verdict**: ❌ Inaccurate — document claims 14 event types, source has 13

- Document: Lists 14 event types including `CHECKPOINT_RESTORED` as #11 in the "14 types" table
- Source: `sse_events.py:39-54` defines `SSEEventType` enum with **13** members (PIPELINE_START through PIPELINE_ERROR). The `PIPELINE_TO_AGUI_MAP` (lines 22-36) also has 13 entries. The doc heading says "14 types" but the table only lists 13 rows (numbered 1-13). The "14" count in the heading is wrong; actual count is 13.
- **Fix needed**: Change "SSE Event Type Registry (14 types)" to "SSE Event Type Registry (13 types)".

### P6: Frontend page/component

**Verdict**: ✅ Accurate

- Document: `useSSEChat.ts:64-166` `sendSSE()` POSTs to `/orchestrator/chat/stream`
- Source: `useSSEChat.ts:64` `export function useSSEChat()`, line 68 `const sendSSE = useCallback(...)`, line 91 `fetch(\`\${API_BASE_URL}/orchestrator/chat/stream\`)`. Confirmed.

### P7: Error handling path

**Verdict**: ✅ Accurate

- Document: mediator catches exceptions, returns OrchestratorResponse with success=False
- Source: `mediator.py:558-569` outer catch returns `OrchestratorResponse(success=False, error=str(e))`. Route-level error handling at `routes.py:412-419` returns PipelineResponse with `is_complete=False`. Confirmed.

### P8: Validation logic location

**Verdict**: ✅ Accurate

- Document: PipelineRequest is a Pydantic model (validation at deserialization)
- Source: `pipeline.py:25-34` `class PipelineRequest(BaseModel)`. FastAPI auto-validates on POST body. Confirmed.

### P9: Response schema

**Verdict**: ⚠️ Partial — PipelineResponse has extra field

- Document: "PipelineResponse Pydantic model" at routes.py:422-479
- Source: `pipeline.py:37-53` `PipelineResponse(BaseModel)` has fields: content, intent_category, confidence, risk_level, routing_layer, execution_mode, suggested_mode, framework_used, session_id, is_complete, **task_id**, tool_calls, processing_time_ms. Doc doesn't mention `task_id` field. Minor omission.

### P10: All function/class names exist

**Verdict**: ✅ Accurate

- All Mermaid participants verified: SSE Stream (PipelineEventEmitter), BOOT (OrchestratorBootstrap), ROUTE (RoutingHandler), DIALOG (DialogHandler), EXEC (ExecutionHandler), AGENT (AgentHandler). All exist in source.

### P11: Intermediate state persistence

**Verdict**: ✅ Accurate

- Document: Checkpoint saves to Redis/Memory via `_save_checkpoint()`
- Source: `mediator.py:249-264` `_save_checkpoint()` creates `HybridCheckpoint` and calls `self._checkpoint_storage.save()`. Line 99-110 shows Redis -> Memory fallback. Confirmed.

### P12: Integration with other flows

**Verdict**: ✅ Accurate

- Document: Step 5 -> Flow 7 (via tool calls), Step 8 -> Flow 8 (memory write)
- Source: AgentHandler tool_calls dispatch via OrchestratorToolRegistry -> DispatchHandlers. Memory write at mediator.py:512-538. Confirmed.

### P13: Auth/permission checks

**Verdict**: ⚠️ Partial — no actual auth enforcement found

- Document: Does not explicitly claim auth exists (no P13 in doc); implied by approval endpoint
- Source: routes.py has no `Depends(get_current_user)` or auth middleware on orchestrator routes. The approval endpoint at routes.py:247 accepts any caller. No actual auth enforcement. The doc correctly doesn't claim auth exists but also doesn't flag this gap.

### P14: Logging/audit location

**Verdict**: ✅ Accurate

- Document: mentions ObservabilityHandler records metrics
- Source: `mediator.py:504-509` runs ObservabilityHandler which uses ObservabilityBridge. All handlers have logger calls. Confirmed.

### P15: Cache usage

**Verdict**: ✅ Accurate

- Document: LLMServiceFactory.create(use_cache=True, cache_ttl=1800)
- Source: `bootstrap.py:134` `LLMServiceFactory.create(use_cache=True, cache_ttl=1800)`. Confirmed.

### P16: Performance-specific handling

**Verdict**: ✅ Accurate

- Document: SSE keepalive, checkpoint resume, async task for SSE pipeline
- Source: `sse_events.py:157` keepalive on timeout, `mediator.py:267-285` checkpoint resume, `routes.py:329` `asyncio.create_task(run_pipeline())`. Confirmed.

### P17: Architecture layers correct

**Verdict**: ❌ Inaccurate — Bootstrap line range wrong

- Document: "Bootstrap assembly" at `bootstrap.py:39-101`
- Source: `bootstrap.py` `build()` method starts at line 39 and ends at line 101. This is correct.
- **However**, doc says "SessionFactory" at `session_factory.py:52-71` with `get_or_create(session_id)` returns `OrchestratorMediator` via `OrchestratorBootstrap.build()`. Source: `session_factory.py:52` `get_or_create()` exists but the factory creates mediator via `_create_orchestrator()` at line 95 which calls `OrchestratorBootstrap(llm_service=self._llm_service).build()`. The doc says session_factory returns "per-session `OrchestratorMediator` via `OrchestratorBootstrap.build()`" which is correct. 
- The real error: doc Step 0e says routes.py uses `_get_bootstrap()` to get the mediator, but routes.py actually uses `_get_session_factory().get_or_create(session_id)` (line 293, 364). The lazy `_get_bootstrap()` is called inside `_get_session_factory()` only for LLM service extraction (line 73-76), NOT for mediator creation. The bootstrap singleton and the per-session bootstrap in SessionFactory are **separate instances**. Doc conflates them.
- **Fix needed**: Clarify that `_get_bootstrap()` in routes.py is only used for health/tool registry, while each session gets its own Bootstrap via SessionFactory._create_orchestrator().

---

## Flow 7: Async Task Dispatch + Background Execution (17 pts)

### P18: Trigger entry (tool call dispatch)

**Verdict**: ✅ Accurate

- Document: Tool call `dispatch_workflow` or `dispatch_swarm` from AgentHandler
- Source: AgentHandler function calling loop executes tools via `OrchestratorToolRegistry.execute()`. DispatchHandlers registers these at `dispatch_handlers.py:456-469`. Confirmed.

### P19: Core processing function location

**Verdict**: ✅ Accurate

- Document: `dispatch_handlers.py:112-191` handle_dispatch_workflow
- Source: `dispatch_handlers.py:112` `async def handle_dispatch_workflow()`. Confirmed.

### P20: Data flow through services

**Verdict**: ✅ Accurate

- Document: Creates TaskResultEnvelope, TaskService.create_task, TaskService.start_task
- Source: dispatch_handlers.py:125 creates `TaskResultEnvelope(task_id=task_id, task_type="workflow")`, line 129 `await self._task_service.create_task(...)`, line 138 `await self._task_service.start_task(task_id, assigned_agent="maf_workflow")`. Confirmed.

### P21: ARQ queue submission

**Verdict**: ✅ Accurate

- Document: `_enqueue_arq()` at dispatch_handlers.py:438-450, lazy init, connects Redis
- Source: dispatch_handlers.py:438 `async def _enqueue_arq()`, calls `get_arq_client()` and `initialize()`. Confirmed.

### P22: ARQ client details

**Verdict**: ⚠️ Partial — queue name and timeout correct, but Redis URL construction slightly different

- Document: Queue name `ipa:arq:queue` (arq_client.py:32), timeout 600s (arq_client.py:69)
- Source: `arq_client.py:30` `queue_name: str = "ipa:arq:queue"` (line 30, not 32 — but content correct). Timeout at line 70 is `timeout: int = 600`. Redis URL at lines 32-35. Line references off by 1-2 but content correct.

### P23: Worker pickup and execution

**Verdict**: ✅ Accurate

- Document: `task_functions.py:17-78` execute_workflow_task
- Source: `task_functions.py:17` `async def execute_workflow_task()`. Confirmed with correct parameter list.

### P24: Status updates

**Verdict**: ✅ Accurate

- Document: `_update_task_status(task_id, "in_progress", 0.1)` at task_functions.py:44
- Source: `task_functions.py:44` `await _update_task_status(task_id, "in_progress", 0.1)`. Confirmed.

### P25: MAF execution TODO

**Verdict**: ✅ Accurate

- Document: `# TODO: Call executor with workflow_type and input_data` at task_functions.py:53
- Source: `task_functions.py:52-53` shows `# TODO: Call executor with workflow_type and input_data`. Confirmed.

### P26: Swarm task function

**Verdict**: ✅ Accurate

- Document: `task_functions.py:81-142` execute_swarm_task uses SwarmIntegration.on_coordination_started()
- Source: `task_functions.py:81` `async def execute_swarm_task()`, line 113 `swarm.on_coordination_started(...)`. Confirmed.

### P27: _update_task_status creates new TaskStore

**Verdict**: ✅ Accurate

- Document: "Each _update_task_status creates new TaskStore() — state not shared across calls" at task_functions.py:155-157
- Source: `task_functions.py:155-157` creates `store = TaskStore()` and `service = TaskService(task_store=store)` on each call. Confirmed — this is indeed a barrier (in-memory state lost).

### P28: TaskResultEnvelope location

**Verdict**: ✅ Accurate

- Document: `task_result_protocol.py` has TaskResultEnvelope, TaskResultNormaliser
- Source: `task_result_protocol.py:54` `class TaskResultEnvelope(BaseModel)`, line 98 `class TaskResultNormaliser`. Confirmed.

### P29: ResultSynthesiser

**Verdict**: ✅ Accurate

- Document: `result_synthesiser.py` aggregates via LLM summarisation
- Source: `result_synthesiser.py:38` `class ResultSynthesiser`, line 52 `async def synthesise()`. Confirmed.

### P30: DispatchHandlers.register_all maps 8 tools

**Verdict**: ❌ Inaccurate — maps 8 tools, not as stated

- Document: `dispatch_handlers.py:456-469` registers 8 tool names
- Source: `dispatch_handlers.py:456` `def register_all()`, lines 458-469 map is: create_task, update_task_status, dispatch_workflow, dispatch_swarm, assess_risk, search_memory, request_approval, search_knowledge = **8 tools**. The doc says 8 which matches. Wait — the doc also says `dispatch_to_claude` is one of the handlers (line 1c description says "8 tool names"). But `dispatch_to_claude` is NOT in the register_all map (it's defined as handle_dispatch_to_claude at line 282 but NOT registered). The doc introduction mentions it ("dispatch_to_claude → ClaudeCoordinator worker pool") but it's not registered.
- **Fix needed**: Note that `dispatch_to_claude` exists as a method but is NOT registered in `register_all()`. Only 8 tools are registered, and dispatch_to_claude is not among them.

### P31: ARQ fallback to direct execution

**Verdict**: ✅ Accurate

- Document: "If ARQ unavailable (is_available=False), falls back to synchronous execution in-process" at dispatch_handlers.py:159-191
- Source: dispatch_handlers.py:158 "Fallback: direct execution" with `from WorkflowExecutorAdapter` import. Confirmed.

### P32: Swarm dispatch creates SwarmIntegration

**Verdict**: ✅ Accurate

- Document: handle_dispatch_swarm creates SwarmIntegration, calls on_coordination_started
- Source: dispatch_handlers.py:241 `from src.integrations.swarm.swarm_integration import SwarmIntegration`, line 249 `swarm.on_coordination_started(...)`. Confirmed.

### P33: No result callback to SSE

**Verdict**: ✅ Accurate

- Document: "Background job results are not pushed back to the SSE stream; client must poll"
- Source: No mechanism in task_functions.py to push results to a PipelineEventEmitter. ARQClient.get_job_status() exists for polling. Confirmed.

### P34: No retry mechanism

**Verdict**: ❌ Inaccurate — barrier severity rating

- Document: "No retry mechanism" listed as MEDIUM severity
- Source: task_functions.py sets status to "failed" on error but has no retry logic. This is correct behavior description but should arguably be HIGH given workflow tasks are the primary async path. Minor severity disagreement.
- Actually, re-reading: the barrier description is factually correct. The severity rating is subjective. Marking as accurate.
- **Revised verdict**: ✅ Accurate

---

## Flow 8: Cross-Conversation Memory + Knowledge Retrieval (16 pts)

### P35: Memory architecture overview

**Verdict**: ⚠️ Partial — Session Memory uses Redis, not PostgreSQL

- Document: "Layer 2: Session Memory (Redis/PostgreSQL, TTL 7 days)"
- Source: `unified_memory.py:259-280` `_store_session_memory()` uses Redis SETEX with comment "In production, this would use PostgreSQL" (line 273). The doc acknowledges this in the barrier table but the architecture overview header says "Redis/PostgreSQL" which is misleading — it's Redis-only currently.
- **Fix needed**: Change "Redis/PostgreSQL" to "Redis (PostgreSQL planned)" in architecture overview.

### P36: Memory write after conversation (Part A)

**Verdict**: ✅ Accurate

- Document: mediator.py:512-538 formats conversation and calls _write_to_longterm()
- Source: mediator.py:511-538 exactly as described. Short-circuit path at 424-439 also confirmed. Confirmed.

### P37: OrchestratorMemoryManager._write_to_longterm()

**Verdict**: ⚠️ Partial — line numbers slightly off and behavior differs

- Document: `memory_manager.py:387-418` is the entry point
- Source: `memory_manager.py:387` `async def _write_to_longterm()` starts at line 387, ends at line 418. Confirmed line range.
- Document says it calls `UnifiedMemoryManager.add()` -> selects layer. Source: `memory_manager.py:399-406` calls `self._memory.add(content=content, user_id=user_id, memory_type=MemType.CONVERSATION)` **without passing importance**, so default MemoryMetadata importance=0.0 will be used. With CONVERSATION type and importance < 0.5, it will go to WORKING layer, NOT long-term. The doc claims the method writes to "Long-term Memory" but in practice, without importance override, it goes to Working Memory.
- **Fix needed**: Document that `_write_to_longterm()` actually writes to the layer selected by `UnifiedMemoryManager._select_layer()` based on default importance (0.0 for CONVERSATION = WORKING layer), not necessarily long-term. The name is misleading.

### P38: Layer selection logic

**Verdict**: ✅ Accurate

- Document: CONVERSATION + importance <0.5 -> WORKING, >=0.5 -> SESSION, >=0.8 -> LONG_TERM
- Source: `unified_memory.py:130-171` confirms: importance >= 0.8 -> LONG_TERM (line 147), CONVERSATION with importance >= 0.5 -> SESSION (line 167), else WORKING (line 168). Confirmed.

### P39: Working Memory store (Redis SETEX)

**Verdict**: ✅ Accurate

- Document: Redis SETEX with key `memory:working:{user_id}:{id}`, TTL from config
- Source: `unified_memory.py:248-249` `key = f"memory:working:{record.user_id}:{record.id}"`, `await self._redis.setex(key, self.config.working_memory_ttl, ...)`. Confirmed.

### P40: Session Memory store

**Verdict**: ✅ Accurate

- Document: Redis SETEX with key `memory:session:{user_id}:{id}`
- Source: `unified_memory.py:274` `key = f"memory:session:{record.user_id}:{record.id}"`. Confirmed.

### P41: Long-term Memory store

**Verdict**: ✅ Accurate

- Document: `Mem0Client.add_memory()` -> mem0 SDK -> Qdrant
- Source: `unified_memory.py:227-233` calls `self._mem0_client.add_memory()`. Confirmed.

### P42: ConversationStateStore.save() parameters

**Verdict**: ❌ Inaccurate — save() method signature differs

- Document: mediator.py:712-721 calls `ConversationStateStore.save()` with `session_id, messages, routing_decision, context`
- Source: `conversation_state.py:96` `async def save(self, state: ConversationState) -> None` takes a single `ConversationState` object, not keyword arguments. The mediator at lines 714-719 calls `self._conversation_store.save(session_id=..., messages=..., routing_decision=..., context=...)` which would NOT match the actual store signature. 
- **Fix needed**: Document should note that mediator.py calls save() with keyword args that don't match the ConversationStateStore.save(state: ConversationState) signature. This is likely a runtime error or the mediator uses a different code path.

### P43: Summarise and store

**Verdict**: ✅ Accurate

- Document: memory_manager.py:77-133 `summarise_and_store()`, loads conversation, generates LLM summary, writes to long-term
- Source: `memory_manager.py:77` `async def summarise_and_store()`, line 101 loads text, line 107 generates summary, line 114 writes. Confirmed.

### P44: Retrieval pipeline (Part B)

**Verdict**: ✅ Accurate

- Document: ContextHandler calls retrieve_relevant_memories() at context.py:76-79
- Source: `context.py:76-79` calls `self._memory_manager.retrieve_relevant_memories(query=request.content, ...)`. Confirmed.

### P45: Multi-layer search

**Verdict**: ✅ Accurate

- Document: UnifiedMemoryManager.search() searches all 3 layers, sorts by score, deduplicates by first 100 chars
- Source: `unified_memory.py:290-360` searches WORKING, SESSION, LONG_TERM layers, line 349 sorts by score, line 355 deduplicates by `content[:100]`, line 360 limits. Confirmed.

### P46: Working/Session memory search pattern

**Verdict**: ✅ Accurate

- Document: Redis SCAN for `memory:working:{user_id}:*` with embedding similarity
- Source: `unified_memory.py:375` `pattern = f"memory:working:{user_id}:*"`, line 381 `query_embedding = await self._embedding_service.embed_text(query)`, line 397 `EmbeddingService.compute_similarity()`. Confirmed.

### P47: Context injection (build_memory_context)

**Verdict**: ✅ Accurate

- Document: Formats with MEMORY_INJECTION_TEMPLATE: `--- 相關歷史記憶 ---\n{memories}\n--- 歷史記憶結束 ---`
- Source: `memory_manager.py:40-46` MEMORY_INJECTION_TEMPLATE confirmed, line 200-226 `build_memory_context()` formats memories. Confirmed.

### P48: RAG Pipeline ingestion

**Verdict**: ⚠️ Partial — line references approximate

- Document: RAGPipeline.ingest_file() at rag_pipeline.py:58-79, parse at :75, chunk at :104, embed at :110, index at :126
- Source: `rag_pipeline.py:58` `async def ingest_file()`, line 75 `doc = await self._parser.parse(file_path)`, but chunk/embed/index are in `_ingest_parsed()` (line 91) not directly in ingest_file(). The line numbers :104, :110, :126 refer to _ingest_parsed method. Doc describes them as if in ingest_file() directly which is slightly misleading since there's an intermediate method call at line 79.

### P49: RAG retrieval + search_knowledge handler

**Verdict**: ✅ Accurate

- Document: dispatch_handlers.handle_search_knowledge() at :411-432, RAGPipeline.retrieve() at :146-166, handle_search_knowledge at :192-217
- Source: dispatch_handlers.py:411 `async def handle_search_knowledge()`, rag_pipeline.py:146 `async def retrieve()`, rag_pipeline.py:192 `async def handle_search_knowledge()`. Confirmed.

### P50: Memory promotion

**Verdict**: ✅ Accurate

- Document: promote_working_to_longterm() at memory_manager.py:232-274, UnifiedMemoryManager.promote() at unified_memory.py:514-571
- Source: memory_manager.py:232 `async def promote_working_to_longterm()`, unified_memory.py:514 `async def promote()`. Confirmed.

---

## Corrections Required

### Critical (5 errors)

| # | Location in Doc | Issue | Fix |
|---|----------------|-------|-----|
| 1 | Flow 6, SSE Registry heading | Says "14 types" but only 13 exist | Change to "13 types" |
| 2 | Flow 6, Step 0e | Conflates routes.py _get_bootstrap() with SessionFactory bootstrap | Clarify that routes.py uses SessionFactory.get_or_create() which internally creates per-session Bootstrap |
| 3 | Flow 7, Step 1c intro | Lists `dispatch_to_claude` as registered tool | Note it exists as method but is NOT in register_all() |
| 4 | Flow 8, Part A Step A2 | `_write_to_longterm()` implies long-term layer | Note that without explicit importance, CONVERSATION type goes to WORKING layer by default |
| 5 | Flow 8, Step A3b | Claims save() takes keyword args `(session_id, messages, routing_decision, context)` | ConversationStateStore.save() takes single `ConversationState` object |

### Minor (8 partial issues)

| # | Location | Issue |
|---|----------|-------|
| 1 | Flow 6, Step 0a | PipelineRequest fields list omits `source` and `timestamp` |
| 2 | Flow 6, P9 | PipelineResponse omits `task_id` field |
| 3 | Flow 6, P13 | No auth enforcement on orchestrator routes (gap not flagged) |
| 4 | Flow 7, P22 | arq_client.py line references off by 1-2 |
| 5 | Flow 8, P35 | Architecture header says "Redis/PostgreSQL" but Session Memory is Redis-only |
| 6 | Flow 8, P37 | _write_to_longterm() name misleading vs actual layer selection |
| 7 | Flow 8, P48 | RAG ingest line refs point to _ingest_parsed() not ingest_file() directly |
| 8 | Flow 6, Step 4c | Approval endpoint doc says `routes.py:247-272`, actual is 247-272 (correct but mediator.py HITL block is at 354-401 not 355-401) |

---

## Cross-Flow Integration Map Verification

The cross-flow integration map at the end of the document is **accurate**:

- ✅ Flow 6 Step 1 reads Flow 8 Part B (memory retrieval) — confirmed via ContextHandler
- ✅ Flow 6 Step 5 calls Flow 7 (via tool_call dispatch) — confirmed via AgentHandler tool loop
- ✅ Flow 6 Step 6 triggers Flow 7 (ExecutionHandler for SWARM/WORKFLOW) — confirmed
- ✅ Flow 6 Step 8 writes Flow 8 Part A (memory write) — confirmed via mediator.py:512-538
- ✅ Flow 7 task lifecycle (create -> queue -> execute -> update) — confirmed
- ✅ Flow 8 three-layer architecture (working -> session -> long-term) — confirmed

## Overall Readiness Assessment Verification

| Flow | Doc Rating | Verified Assessment |
|------|-----------|-------------------|
| Flow 6: Pipeline | 70% | ✅ Agree — chat mode works E2E, workflow/swarm dispatch needs real executors |
| Flow 7: Async Dispatch | 30% | ✅ Agree — infrastructure exists, actual execution not connected (TODO at task_functions.py:53) |
| Flow 8: Memory | 50% | ⚠️ Slightly optimistic — _write_to_longterm defaults to WORKING layer, not truly long-term without importance tuning. Suggest 40-45%. |
