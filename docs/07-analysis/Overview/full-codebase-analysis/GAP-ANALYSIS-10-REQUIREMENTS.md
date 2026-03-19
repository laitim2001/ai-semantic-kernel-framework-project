# Comprehensive Gap Analysis: 10 Core Requirements

**Date**: 2026-03-19
**Scope**: Full codebase evidence-based gap analysis
**Method**: Static source code reading of all referenced modules

---

## Summary Dashboard

| # | Requirement | Status | Severity of Gaps |
|---|------------|--------|-----------------|
| 1 | Multi-entry Input Gateway + Auth + Session | **PARTIAL** | HIGH |
| 2 | Concurrency / Multi-threading | **PARTIAL** | MEDIUM |
| 3 | Risk Assessment in Intent Routing | **PARTIAL** | MEDIUM |
| 4 | Orchestrator Gate-keeper + Execution Mode | **PARTIAL** | HIGH |
| 5 | Task Dispatch to Workers | **PARTIAL** | CRITICAL |
| 6 | Unified MCP Tool Layer | **PARTIAL** | HIGH |
| 7 | Observability + AG-UI Streaming | **PARTIAL** | MEDIUM |
| 8 | Result Aggregation + Unified Response | **PARTIAL** | MEDIUM |
| 9 | Session Resume + Checkpointing | **PARTIAL** | HIGH |
| 10 | Memory + Knowledge (RAG) | **PARTIAL** | HIGH |

---

## Requirement 1: Multi-entry Input Gateway + Auth + Session Management

### Status: PARTIAL

### What EXISTS

1. **InputGateway** (`backend/src/integrations/orchestration/input_gateway/gateway.py`)
   - `InputGateway` class with multi-source routing (user, ServiceNow, Prometheus)
   - Source handlers: `UserInputHandler`, `ServiceNowHandler`, `PrometheusHandler`
   - Schema validation via `schema_validator.py`
   - Models with `SourceType` enum, `IncomingRequest`, `GatewayConfig`, `GatewayMetrics`

2. **Auth API** (`backend/src/api/v1/auth/routes.py`)
   - `POST /register` - User registration with JWT token response
   - `POST /login` - OAuth2PasswordRequestForm-based login
   - `POST /refresh` - Token refresh
   - `GET /me` - Current user info
   - Rate limiting via `@limiter.limit("10/minute")`
   - Depends on `AuthService` + `UserRepository`

3. **Session CRUD** (`backend/src/api/v1/sessions/routes.py`)
   - Full CRUD: create, get, list, update, delete sessions
   - Redis caching via `SessionCache`
   - User ownership checks (user_id matching)
   - `SQLAlchemySessionRepository` for persistence

4. **Per-Session Orchestrator** (`backend/src/integrations/hybrid/orchestrator/session_factory.py`)
   - `OrchestratorSessionFactory` with LRU eviction (max 100 sessions)
   - `get_or_create(session_id)` returns per-session `OrchestratorMediator`
   - Each session gets its own `AgentHandler`, sharing global LLM pool + tool registry

5. **Session Resume Routes** (`backend/src/api/v1/orchestrator/session_routes.py`)
   - `GET /recoverable` - List recoverable sessions
   - Resume endpoint using `SessionRecoveryManager`

### What is MISSING / GAP

| Gap | Severity | Detail |
|-----|----------|--------|
| No E2E wiring from Auth -> Session -> SessionFactory -> Orchestrator | **HIGH** | Auth issues JWT, Sessions exist in DB, but there is NO code path that takes a logged-in user's request, creates/retrieves their session, calls `OrchestratorSessionFactory.get_or_create()`, and feeds into the mediator pipeline. These are separate islands. |
| InputGateway not wired to Mediator pipeline | **HIGH** | `RoutingHandler` has an `_input_gateway` parameter but it defaults to `None`. No bootstrap code instantiates the full chain. |
| No WebSocket/real-time session channel | **MEDIUM** | Sessions are HTTP-only. No persistent connection for real-time updates within a session. AG-UI SSE exists separately but is not session-aware. |
| Session-to-user binding is weak | **MEDIUM** | Session routes check `user_id` ownership, but the orchestrator's `OrchestratorSessionFactory` is keyed by `session_id` alone with no user validation. |

---

## Requirement 2: Concurrency / Multi-threading

### Status: PARTIAL

### What EXISTS

1. **Uvicorn with configurable workers** (`backend/main.py:325-330`)
   - `uvicorn.run()` with `workers=server_config.workers`
   - `ServerConfig` class controls worker count (from `src.core.server_config`)

2. **LLMCallPool** (`backend/src/core/performance/llm_pool.py`)
   - `asyncio.Semaphore` for max concurrent LLM calls (default: 5)
   - Priority queue: `CRITICAL > DIRECT_RESPONSE > INTENT_ROUTING > EXTENDED_THINKING > SWARM_WORKER`
   - Per-minute rate tracking
   - Token budget tracking
   - Singleton pattern (`LLMCallPool.get_instance()`)
   - Automatic backoff on 429 Too Many Requests

3. **Per-session isolation** via `OrchestratorSessionFactory`
   - Each session gets its own `OrchestratorMediator` instance
   - Shared global LLM pool prevents resource contention

### What is MISSING / GAP

| Gap | Severity | Detail |
|-----|----------|--------|
| No Redis-based distributed locking | **MEDIUM** | If running multiple uvicorn workers (multi-process), the in-memory `OrchestratorSessionFactory` is per-process. Session state would diverge across workers. Need sticky sessions or shared state. |
| No explicit request-level concurrency guard | **LOW** | FastAPI handles async natively, but there is no middleware to limit per-user concurrent requests to prevent abuse. |
| LLMCallPool is in-memory singleton | **MEDIUM** | Works for single-process, but multi-worker deployment would have separate pools per process. No cross-process coordination. |
| No load test evidence | **LOW** | No benchmarks or load test results to verify concurrent session handling. |

---

## Requirement 3: Risk Assessment in Intent Routing

### Status: PARTIAL

### What EXISTS

1. **RiskAssessor** (`backend/src/integrations/orchestration/risk_assessor/assessor.py`)
   - `RiskAssessment` dataclass: level, score (0.0-1.0), requires_approval, approval_type
   - `RiskFactor` with name, weight, value, impact
   - `AssessmentContext`: is_production, is_staging, is_weekend, is_business_hours, is_urgent, user_role, affected_systems
   - Policy-based assessment with contextual adjustments

2. **RiskAssessmentEngine** (`backend/src/integrations/hybrid/risk/engine.py`)
   - `RiskAssessmentEngine` class for multi-dimensional risk assessment
   - Referenced as "7 dimensions" in tool descriptions

3. **HITLController** (`backend/src/integrations/orchestration/hitl/controller.py`)
   - Full approval workflow: `ApprovalRequest`, `ApprovalStatus`, `ApprovalType`
   - `ApprovalType`: SINGLE, MULTI, SEQUENTIAL, UNANIMOUS
   - Expiration handling, approval/rejection tracking
   - `ApprovalNotifier` protocol for notifications

4. **ToolSecurityGateway** (`backend/src/core/security/tool_gateway.py`)
   - 4-layer security: Input Sanitization, Permission Check, Rate Limiting, Audit Logging
   - Role-based permissions: ADMIN (all), OPERATOR (5 tools), VIEWER (3 tools)
   - SQL/code injection pattern detection
   - High-risk tool stricter rate limits

5. **ApprovalHandler** in mediator pipeline (`backend/src/integrations/hybrid/orchestrator/handlers/approval.py`)
   - Integrated into the 7-step mediator pipeline at step 4

### What is MISSING / GAP

| Gap | Severity | Detail |
|-----|----------|--------|
| Two risk engines not unified | **MEDIUM** | `orchestration/risk_assessor/assessor.py` and `hybrid/risk/engine.py` are separate implementations. The Orchestrator tools reference `assess_risk` in dispatch_handlers but it's unclear which engine is actually called. |
| HITL approval is in-memory only | **HIGH** | `HITLController` stores `ApprovalRequest` objects in memory (`_pending_requests` dict). Server restart loses all pending approvals. No database persistence. |
| ToolSecurityGateway not wired to Orchestrator tools | **MEDIUM** | `ToolSecurityGateway` exists with role-based checks, but the `OrchestratorToolRegistry.execute()` does not call it before executing tools. The gateway is standalone. |
| No real notification channel for approvals | **MEDIUM** | `ApprovalNotifier` is a Protocol (interface) with no concrete implementation. No email/Slack/WebSocket notification for approval requests. |

---

## Requirement 4: Orchestrator Agent as Gate-keeper + Execution Mode Selection

### Status: PARTIAL

### What EXISTS

1. **OrchestratorMediator** (`backend/src/integrations/hybrid/orchestrator/mediator.py`)
   - 7-step pipeline: Context -> Routing -> Dialog -> Approval -> Agent -> Execution -> Observability
   - Session management with `_get_or_create_session()`
   - Short-circuit support (dialog/approval can terminate early)
   - Pipeline context shared across handlers

2. **AgentHandler** (`backend/src/integrations/hybrid/orchestrator/agent_handler.py`)
   - LLM-powered orchestrator agent with tool calling
   - Can invoke tools from `OrchestratorToolRegistry`
   - Decides whether to use tools or respond directly

3. **RoutingHandler** (`backend/src/integrations/hybrid/orchestrator/handlers/routing.py`)
   - Two flows: Phase 28 (InputGateway) and Direct (FrameworkSelector)
   - Swarm eligibility detection via `_swarm_handler.analyze_for_swarm()`
   - Sets `context["execution_mode"]` and `context["swarm_decomposition"]`

4. **FrameworkSelector** (`backend/src/integrations/hybrid/intent/router.py`)
   - Multi-classifier analysis (rule-based, complexity, LLM fallback)
   - Weighted voting with confidence threshold (0.7)
   - Modes: `WORKFLOW_MODE`, `CHAT_MODE`, `HYBRID_MODE`

5. **ExecutionHandler** (`backend/src/integrations/hybrid/orchestrator/handlers/execution.py`)
   - Dispatches to: `_execute_workflow()`, `_execute_chat()`, `_execute_hybrid()`, `_execute_swarm()`
   - Accepts injectable executors: `claude_executor`, `maf_executor`, `swarm_handler`

6. **Contracts** (`backend/src/integrations/hybrid/orchestrator/contracts.py`)
   - `OrchestratorRequest`, `OrchestratorResponse`, `HandlerResult`
   - `ExecutionMode` imported from `hybrid.intent`
   - `HandlerType` enum for all 7 handler types

### What is MISSING / GAP

| Gap | Severity | Detail |
|-----|----------|--------|
| No "extended thinking" mode | **HIGH** | `ExecutionMode` has WORKFLOW, CHAT, HYBRID, but no EXTENDED_THINKING mode. The `LLMCallPool` has `EXTENDED_THINKING` priority, but no corresponding execution path exists. |
| ExecutionHandler executors default to None | **HIGH** | `claude_executor`, `maf_executor`, `swarm_handler` all default to `None`. If not injected, execution falls through to error/empty responses. No bootstrap code wires real executors. |
| No factory/bootstrap assembles the full pipeline | **CRITICAL** | There is no `create_mediator()` or startup code that instantiates all 7 handlers with their real dependencies (InputGateway, RiskAssessor, FrameworkSelector, executors) and registers them. Each piece exists but the assembly is missing. |
| FrameworkSelector lacks swarm mode | **MEDIUM** | The `FrameworkSelector` classifiers output WORKFLOW/CHAT/HYBRID. Swarm eligibility is checked separately in `RoutingHandler` via `_swarm_handler`, bypassing the classifier system. |

---

## Requirement 5: Task Dispatch to Workers

### Status: PARTIAL (trending CRITICAL)

### What EXISTS

1. **DispatchHandlers** (`backend/src/integrations/hybrid/orchestrator/dispatch_handlers.py`)
   - `handle_dispatch_workflow()` - Creates task, attempts MAF `WorkflowExecutorAdapter`
   - `handle_dispatch_swarm()` - Creates task, attempts `SwarmIntegration`
   - `handle_dispatch_to_claude()` - Creates task, attempts `ClaudeCoordinator`
   - `handle_create_task()`, `handle_update_task_status()`
   - `handle_search_memory()`, `handle_search_knowledge()`
   - `handle_assess_risk()`, `handle_request_approval()`
   - All handlers produce `TaskResultEnvelope`

2. **OrchestratorToolRegistry** (`backend/src/integrations/hybrid/orchestrator/tools.py`)
   - 9 built-in tools registered with schemas
   - Handler registration via `register_handler(tool_name, callable)`
   - Stub fallback: if no handler registered, returns `{"stub": True}`

3. **ClaudeCoordinator** (`backend/src/integrations/claude_sdk/orchestrator/coordinator.py`)
   - `coordinate_agents()` - Multi-agent coordination
   - `analyze_task()` - Task decomposition
   - `select_agents()` - Agent selection
   - `_wrap_executor_for_swarm()` - Swarm integration

4. **MAF Builders** (`backend/src/integrations/agent_framework/builders/`)
   - 30+ builder files exist for various agent types

### What is MISSING / GAP

| Gap | Severity | Detail |
|-----|----------|--------|
| Dispatch handlers use try/ImportError pattern | **CRITICAL** | `handle_dispatch_workflow()` wraps MAF calls in `try: from ... import WorkflowExecutorAdapter` with `except ImportError: logger.warning(...)`. If the import fails, the task is created but nothing actually executes. Same pattern for swarm and Claude dispatch. |
| No real background execution | **CRITICAL** | Dispatch handlers are synchronous within the request cycle. No ARQ/Celery/background worker. `BackgroundTasks` from FastAPI is used only in 2 places (planning routes, swarm demo) but NOT in the main orchestrator dispatch flow. Long-running workflows block the request. |
| DispatchHandlers not wired to ToolRegistry at startup | **HIGH** | `DispatchHandlers.get_all_handlers()` returns a dict mapping tool names to methods, but no startup code calls `tool_registry.register_handler()` for each. The `OrchestratorToolRegistry` would return stubs. |
| MAF Builders are not validated as callable end-to-end | **HIGH** | 30+ builder files exist but many may not produce working agents without the actual `agent_framework` SDK being properly installed and configured. |

---

## Requirement 6: Unified MCP Tool Layer

### Status: PARTIAL

### What EXISTS

1. **MCP Core** (`backend/src/integrations/mcp/core/`)
   - `MCPClient` - Multi-server connection manager
   - `MCPProtocol` - JSON-RPC protocol implementation
   - `BaseTransport`, `StdioTransport`, `InMemoryTransport`
   - `ToolSchema`, `ToolResult`, `ToolParameter` types

2. **MCP Servers** (`backend/src/integrations/mcp/servers/`)
   - 8 servers: `adf`, `azure`, `d365`, `filesystem`, `ldap`, `n8n`, `shell`, `ssh`
   - Each has `client.py`, `server.py`, and `tools/` directory

3. **MCP Security** (`backend/src/integrations/mcp/security/`)
   - `permission_checker.py`, `command_whitelist.py`, `audit.py`, `redis_audit.py`

4. **MCP Registry** (`backend/src/integrations/mcp/registry/`)
   - `server_registry.py`, `config_loader.py`

5. **MCP API** (`backend/src/api/v1/mcp/`)
   - Management API endpoints exist

### What is MISSING / GAP

| Gap | Severity | Detail |
|-----|----------|--------|
| MCP not wired to Orchestrator agent tools | **HIGH** | `grep` for `mcp_client` or `MCPClient` in `backend/src/integrations/hybrid/orchestrator/` returns **zero results**. The orchestrator agent cannot call MCP tools. MCP is a completely separate subsystem. |
| No MCP tool discovery in AgentHandler | **HIGH** | `AgentHandler` uses `OrchestratorToolRegistry` which has 9 hardcoded tools. There is no mechanism to dynamically discover and expose MCP server tools to the LLM agent. |
| Sub-agents cannot access MCP tools | **MEDIUM** | When a MAF workflow or Claude worker is dispatched, there is no MCP tool injection into their execution context. |
| InMemoryTransport limits testing | **LOW** | `InMemoryTransport` exists for tests, but real server transports (stdio) require external processes. No container orchestration for MCP servers. |

---

## Requirement 7: Observability + AG-UI Real-time Streaming

### Status: PARTIAL

### What EXISTS

1. **AG-UI Infrastructure** (`backend/src/integrations/ag_ui/`)
   - Rich event system: `base.py`, `lifecycle.py`, `message.py`, `progress.py`, `state.py`, `tool.py`
   - `HybridEventBridge` - Converts orchestrator results to SSE events
   - Features: `agentic_chat`, `human_in_loop`, `approval_delegate`, `generative_ui`, `tool_rendering`
   - Advanced: `predictive.py`, `shared_state.py`, `tool_ui.py`
   - Thread management with Redis storage

2. **AG-UI API** (`backend/src/api/v1/ag_ui/routes.py`)
   - `POST /run` - SSE streaming endpoint
   - `POST /run/sync` - Synchronous execution
   - Thread state management (get/update)
   - HITL approval endpoints
   - Bridge status and reset

3. **ObservabilityHandler** (`backend/src/integrations/hybrid/orchestrator/handlers/observability.py`)
   - Part of the 7-step mediator pipeline (step 7)

4. **ObservabilityBridge** (`backend/src/integrations/hybrid/orchestrator/observability_bridge.py`)
   - G3 (Patrol), G4 (Correlation), G5 (RootCause) dispatch
   - Circuit breaker integration for LLM API protection

5. **Swarm Events** (`backend/src/integrations/swarm/events/`)
   - Event files exist for swarm-specific SSE

### What is MISSING / GAP

| Gap | Severity | Detail |
|-----|----------|--------|
| AG-UI bridge uses old HybridOrchestratorV2, not new Mediator | **HIGH** | `HybridEventBridge.__init__` accepts `orchestrator: HybridOrchestratorV2`. The new `OrchestratorMediator` is not connected to AG-UI streaming. Two parallel systems. |
| No real-time thinking/tool-call streaming | **MEDIUM** | The AG-UI bridge converts final results to events. It does NOT stream intermediate LLM thinking tokens or tool-call progress in real-time. Events are generated after execution completes. |
| ObservabilityBridge G3/G4/G5 are dispatch-only | **MEDIUM** | Bridge creates tasks for Patrol/Correlation/RootCause but uses `try: from ... import` pattern. If engines aren't available, it just logs warnings. |
| OpenTelemetry is optional/fragile | **LOW** | `main.py` wraps OTel init in `try/except` with `logger.warning`. No guaranteed tracing in production. |

---

## Requirement 8: Result Aggregation + Unified Response

### Status: PARTIAL

### What EXISTS

1. **TaskResultEnvelope** (`backend/src/integrations/hybrid/orchestrator/task_result_protocol.py`)
   - `WorkerType`: MAF_WORKFLOW, CLAUDE_WORKER, SWARM, DIRECT
   - `ResultStatus`: SUCCESS, PARTIAL, FAILED, TIMEOUT, CANCELLED
   - `WorkerResult`: worker_id, worker_type, status, output, error, tool_calls, tokens_used, duration_ms
   - `TaskResultEnvelope`: aggregates multiple `WorkerResult`, tracks totals
   - `TaskResultNormaliser`: static methods `from_maf_execution()`, `from_claude_response()`, `from_swarm_coordination()`

2. **ResultSynthesiser** (`backend/src/integrations/hybrid/orchestrator/result_synthesiser.py`)
   - Single worker: pass-through formatting
   - Multi-worker: LLM-powered synthesis with Chinese prompt template
   - Fallback: structured concatenation without LLM
   - Accepts `llm_service` for synthesis calls

### What is MISSING / GAP

| Gap | Severity | Detail |
|-----|----------|--------|
| ResultSynthesiser not wired to Mediator pipeline | **HIGH** | The mediator's `ExecutionHandler` does not call `ResultSynthesiser`. It returns raw handler results. Synthesis would need to happen between execution and response building. |
| No streaming synthesis | **MEDIUM** | Synthesis is a single LLM call that blocks until complete. For multi-worker results, the user waits for all workers + synthesis. No incremental result delivery. |
| LLM service injection for synthesis is unresolved | **MEDIUM** | `ResultSynthesiser(llm_service=None)` defaults to fallback mode. No startup code injects the actual LLM service. |

---

## Requirement 9: Session Resume + Checkpointing

### Status: PARTIAL

### What EXISTS

1. **SessionRecoveryManager** (`backend/src/integrations/hybrid/orchestrator/session_recovery.py`)
   - Three-layer recovery: L1 (Conversation/Redis), L2 (Tasks/PostgreSQL), L3 (Execution/PostgreSQL)
   - `list_recoverable_sessions()` - Scans all 3 layers
   - `recover_session()` - Restores state from all available layers
   - `SessionSummary` and `RecoveryResult` models

2. **L1 ConversationStateStore** (`backend/src/infrastructure/storage/conversation_state.py`)
   - Redis-backed ephemeral conversation state
   - Message history, metadata, TTL-based expiration

3. **L3 ExecutionStateStore** (`backend/src/infrastructure/storage/execution_state.py`)
   - PostgreSQL-backed permanent execution state
   - `AgentExecutionState`: agent context snapshots, tool call history
   - Index by both `execution_id` and `session_id`
   - No TTL (permanent storage)

4. **Checkpoint System** (`backend/src/integrations/hybrid/checkpoint/`)
   - `models.py`, `storage.py`, `serialization.py`, `version.py`
   - `backends/` directory for storage backends

5. **Session Resume API** (`backend/src/api/v1/orchestrator/session_routes.py`)
   - `GET /recoverable` - List recoverable sessions
   - Recovery manager initialization with L1/L2/L3 stores

### What is MISSING / GAP

| Gap | Severity | Detail |
|-----|----------|--------|
| No background task execution | **CRITICAL** | If a user closes the browser, there is NO background worker (ARQ/Celery) to continue running tasks. All execution is request-scoped. A disconnected SSE stream kills the running task. |
| L2 TaskStore not implemented in recovery | **HIGH** | `SessionRecoveryManager.__init__` accepts `task_service` but recovery of pending tasks requires a background executor to resume them. There is no mechanism to restart a half-completed workflow. |
| Checkpoint system appears unused by Mediator | **MEDIUM** | The `checkpoint/` directory has models and storage but the `OrchestratorMediator` does not call checkpoint save/restore during execution. |
| Recovery creates summary but doesn't restart execution | **HIGH** | `recover_session()` returns a `RecoveryResult` with `resume_context`, but there is no code that takes this context and actually re-feeds it into the mediator pipeline to continue execution. |

---

## Requirement 10: Memory + Knowledge (RAG / Agentic RAG)

### Status: PARTIAL

### What EXISTS

1. **Memory Integration** (`backend/src/integrations/memory/`)
   - mem0 integration files exist
   - `UnifiedMemoryManager` referenced

2. **OrchestratorMemoryManager** (`backend/src/integrations/hybrid/orchestrator/memory_manager.py`)
   - `summarise_and_store()` - Conversation summarization to long-term memory
   - `retrieve_relevant_memories()` - Semantic search with time filtering
   - `build_memory_context()` - Format memories for LLM context
   - `promote_working_to_longterm()` - Memory tier promotion
   - `handle_search_memory()` - Tool handler for orchestrator agent

3. **Knowledge/RAG Pipeline** (`backend/src/integrations/knowledge/`)
   - `RAGPipeline` with full pipeline: Parse -> Chunk -> Embed -> Index -> Retrieve -> Augment
   - `DocumentParser`, `DocumentChunker` (recursive strategy), `EmbeddingManager`
   - `VectorStoreManager`, `KnowledgeRetriever`
   - `AgentSkills` - ITIL SOP knowledge packs (Incident Mgmt, Change Mgmt, Enterprise Arch)

4. **Dispatch Integration**
   - `handle_search_memory()` in `DispatchHandlers` -> calls `OrchestratorMemoryManager`
   - `handle_search_knowledge()` in `DispatchHandlers` -> calls RAG pipeline

### What is MISSING / GAP

| Gap | Severity | Detail |
|-----|----------|--------|
| NOT agentic RAG | **HIGH** | The orchestrator does NOT autonomously decide when to search knowledge. `search_knowledge` is a tool the LLM agent CAN call, but the agent has no system prompt instruction to proactively search before answering domain questions. It's reactive tool-calling, not agentic RAG. |
| search_knowledge tool not registered in ToolRegistry | **HIGH** | `OrchestratorToolRegistry._register_builtin_tools()` registers 9 tools but `search_knowledge` was added later in dispatch_handlers. The tool schema may not be exposed to the LLM, meaning the agent cannot discover it. |
| Vector store requires external setup | **MEDIUM** | `VectorStoreManager` and `EmbeddingManager` need Qdrant and an embedding model. No auto-initialization or health check at startup. |
| Memory manager not wired to Mediator pipeline | **HIGH** | The mediator's `ContextHandler` should inject memory context into the pipeline, but `OrchestratorMemoryManager` is not referenced in the mediator or any handler's constructor. Memory retrieval only happens if the LLM explicitly calls the `search_memory` tool. |
| No automatic conversation-to-memory persistence | **MEDIUM** | `summarise_and_store()` exists but is never called automatically at session end or on a schedule. Memory promotion is manual/tool-triggered only. |

---

## Cross-Cutting Critical Findings

### 1. THE ASSEMBLY GAP (CRITICAL)

The single most impactful gap across ALL requirements is the **absence of a bootstrap/factory/startup assembly**. Every major component exists as a well-designed class, but there is NO code that:

- Creates `InputGateway` with real source handlers
- Creates `OrchestratorMediator` with all 7 handlers wired to real dependencies
- Registers `DispatchHandlers` into `OrchestratorToolRegistry`
- Connects `OrchestratorSessionFactory` to the auth/session layer
- Injects `ToolSecurityGateway` into the tool execution path
- Wires `MCPClient` tools into the orchestrator agent's tool set
- Connects the new Mediator to the AG-UI `HybridEventBridge`

**Impact**: The system has ~80% of the code written but ~20% of the wiring done. It cannot execute an end-to-end flow from user request to worker dispatch to result synthesis.

### 2. TWO PARALLEL SYSTEMS

- **Old**: `HybridOrchestratorV2` (used by AG-UI bridge, has real execution logic)
- **New**: `OrchestratorMediator` (clean architecture, handler-based, but unwired)

The AG-UI bridge still points to the old orchestrator. The new mediator is not connected to anything that receives HTTP requests.

### 3. NO BACKGROUND EXECUTION

Every execution path is request-scoped. Long-running workflows, swarm coordination, and multi-agent tasks will timeout or die with the HTTP connection. This is the most fundamental architectural gap for a production system.

---

## Priority Remediation Roadmap

### Phase A: Assembly (Addresses Gaps in Req 1, 4, 5, 6, 8, 10)
1. Create `OrchestratorBootstrap` that wires all components at startup
2. Register all dispatch handlers into tool registry
3. Wire MCP client tools into orchestrator tool set
4. Connect memory manager to context handler
5. Wire result synthesiser into execution -> response path

### Phase B: Bridge Migration (Addresses Gaps in Req 7)
1. Create `MediatorEventBridge` that adapts new Mediator to AG-UI events
2. Or modify `HybridEventBridge` to accept `OrchestratorMediator`
3. Add real-time streaming for intermediate events

### Phase C: Background Execution (Addresses Gaps in Req 5, 9)
1. Integrate ARQ or similar async task queue
2. Make dispatch_workflow/swarm/claude submit to background workers
3. Implement task status polling and SSE push for completion
4. Enable session resume to restart background tasks

### Phase D: Security Hardening (Addresses Gaps in Req 3)
1. Wire ToolSecurityGateway into OrchestratorToolRegistry.execute()
2. Persist HITL approvals to database
3. Unify the two risk assessment engines
4. Implement approval notification channel
