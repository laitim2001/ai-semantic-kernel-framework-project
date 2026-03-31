# Layer 05: Hybrid Orchestration

> **V9 Architecture Analysis** | 2026-03-29
> **Scope**: `backend/src/integrations/hybrid/` — 90+ Python files, ~26K LOC
> **Role**: Central mediation layer between MAF (Layer 06) and Claude SDK (Layer 07)
> **Phase History**: Phase 13-14 (S52-S57), Phase 28 (S93-S98), Phase 29 (S116), Phase 35 (S107), Phase 39-42 (S132-S148)

---

## 1. Identity

Layer 05 is the **Hybrid Orchestration Layer** — the largest and most architecturally complex integration module in the IPA Platform. It serves as the central nervous system that:

1. **Decides** which framework to use (MAF vs Claude vs Hybrid vs Swarm) for each request
2. **Bridges** context state bidirectionally between MAF workflows and Claude sessions
3. **Assesses** operational risk and triggers HITL approval for high-risk operations
4. **Executes** requests through the selected framework via a unified pipeline
5. **Persists** execution checkpoints across 4 storage backends
6. **Streams** real-time pipeline events via 13 SSE event types

The layer has undergone a major architectural evolution: from the monolithic `HybridOrchestratorV2` (Sprint 54, ~1,395 LOC God Object) to the current **Mediator Pattern** with 7 specialized handlers (Sprint 132+).

---

## 2. File Inventory

### 2.1 Complete File Map (90+ files)

| Subsystem | Directory | Files | Est. LOC | Primary Class |
|-----------|-----------|-------|----------|---------------|
| **Root** | `hybrid/` | 4 | ~2,850 | `HybridOrchestratorV2`, `ClaudeMAFFusion`, `SwarmModeHandler`, `__init__.py` |
| **orchestrator/** | `hybrid/orchestrator/` | 18 | ~5,500 | `OrchestratorMediator`, `OrchestratorBootstrap`, `AgentHandler` |
| **orchestrator/handlers/** | `hybrid/orchestrator/handlers/` | 7 | ~1,200 | `RoutingHandler`, `ExecutionHandler`, etc. |
| **intent/** | `hybrid/intent/` | 9 | ~2,500 | `FrameworkSelector`, `RuleBasedClassifier`, `RoutingDecisionClassifier` |
| **context/** | `hybrid/context/` | 9 | ~3,700 | `ContextBridge`, `ContextSynchronizer` |
| **execution/** | `hybrid/execution/` | 5 | ~2,235 | `UnifiedToolExecutor`, `ToolRouter` |
| **risk/** | `hybrid/risk/` | 7 | ~2,535 | `RiskAssessmentEngine`, `RiskScorer` |
| **switching/** | `hybrid/switching/` | 11 | ~3,370 | `ModeSwitcher`, `StateMigrator`, `RedisSwitchCheckpointStorage` |
| **checkpoint/** | `hybrid/checkpoint/` | 9 | ~4,300 | `UnifiedCheckpointStorage`, 4 backends |
| **hooks/** | `hybrid/hooks/` | 2 | ~450 | `RiskDrivenApprovalHook` |
| **prompts/** | `hybrid/prompts/` | 2 | ~200 | `ORCHESTRATOR_SYSTEM_PROMPT` |

### 2.2 Key File Reference

| File | LOC | Sprint | Description |
|------|-----|--------|-------------|
| `orchestrator/mediator.py` | ~845 | S132+ | **OrchestratorMediator** — Central coordinator, 9-step pipeline |
| `orchestrator_v2.py` | ~1,395 | S54 | **HybridOrchestratorV2** — DEPRECATED God Object facade |
| `orchestrator/bootstrap.py` | ~512 | S134 | **OrchestratorBootstrap** — Full pipeline DI assembly |
| `orchestrator/contracts.py` | ~133 | S132 | Handler ABC, OrchestratorRequest/Response, HandlerResult |
| `orchestrator/sse_events.py` | ~158 | S145 | 13 SSE event types + PipelineEventEmitter |
| `orchestrator/agent_handler.py` | ~426 | S107/S144 | **AgentHandler** — LLM + Function Calling loop |
| `orchestrator/handlers/routing.py` | ~227 | S132 | **RoutingHandler** — 3-tier routing + FrameworkSelector |
| `orchestrator/handlers/execution.py` | ~459 | S132 | **ExecutionHandler** — MAF/Claude/Hybrid/Swarm dispatch |
| `orchestrator/handlers/dialog.py` | ~121 | S132 | **DialogHandler** — GuidedDialogEngine integration |
| `orchestrator/handlers/approval.py` | ~137 | S132 | **ApprovalHandler** — RiskAssessor + HITLController |
| `orchestrator/handlers/context.py` | ~131 | S132 | **ContextHandler** — ContextBridge + MemoryManager |
| `orchestrator/handlers/observability.py` | ~91 | S132 | **ObservabilityHandler** — Metrics recording |
| `intent/router.py` | ~501 | S52/S98 | **FrameworkSelector** — Weighted classifier aggregation |
| `intent/models.py` | 223 | S52/S98/S116 | ExecutionMode (4 modes: WORKFLOW/CHAT/HYBRID/SWARM), IntentAnalysis, SessionContext, ClassificationResult, ComplexityScore, MultiAgentAnalysis. `FrameworkAnalysis` alias (S98) |
| `intent/classifiers/rule_based.py` | 468 | S52 | RuleBasedClassifier — 50+ workflow keywords, 20+ chat keywords, 18+ phrase patterns (EN + zh-TW). Context boost for active workflows |
| `intent/classifiers/routing_decision.py` | 185 | S144 | RoutingDecisionClassifier — IT intent to ExecutionMode bridge (weight=1.5, higher than rule-based) |
| `intent/analyzers/complexity.py` | 428 | S52 | ComplexityAnalyzer — heuristic scoring via step/dependency/persistence/time indicators. Bilingual keywords |
| `intent/analyzers/multi_agent.py` | 567 | S52 | MultiAgentDetector — 8 skill domains, role references, collaboration patterns. Returns agent count estimate |
| `context/bridge.py` | 933 | S53 | **ContextBridge** — Bidirectional MAF-Claude sync with `_context_cache`, `sync_after_execution()`, `validate_context()` |
| `context/models.py` | 590 | S53 | MAFContext, ClaudeContext, HybridContext + 7 enums (SyncStatus, SyncDirection, SyncStrategy, AgentStatus, ApprovalStatus, MessageRole, ToolCallStatus) + supporting dataclasses |
| `context/mappers/base.py` | 332 | S53 | `BaseMapper[T,U]` generic ABC + `MappingError` exception + utility methods |
| `context/mappers/claude_mapper.py` | 467 | S53 | `ClaudeMapper`: Claude->MAF with prefix stripping, message->ExecutionRecord, tool call->ApprovalRequest |
| `context/mappers/maf_mapper.py` | 416 | S53 | `MAFMapper`: MAF->Claude with prefix adding, execution records->messages, agent states->system prompt |
| `context/sync/synchronizer.py` | 693 | S53/S119 | ContextSynchronizer — Redis distributed lock (with asyncio.Lock fallback), retry logic (max 3), version tracking, rollback snapshots (max 5) |
| `context/sync/conflict.py` | 498 | S53 | `ConflictResolver` — 6 strategies (SOURCE_WINS, TARGET_WINS, MAF_PRIMARY, CLAUDE_PRIMARY, MERGE, MANUAL). Intelligent merge by recency |
| `context/sync/events.py` | 443 | S53 | `SyncEventPublisher` — async pub/sub for 10 sync event types. Filtered subscriptions, event history (max 100) |
| `execution/unified_executor.py` | ~797 | S54 | **UnifiedToolExecutor** — Hook pipeline + tool dispatch |
| `risk/engine.py` | ~561 | S55 | **RiskAssessmentEngine** — Multi-dimensional scoring |
| `risk/models.py` | ~200+ | S55 | RiskLevel (4 levels), RiskFactor (9 types), RiskConfig |
| `switching/switcher.py` | ~836 | S56 | **ModeSwitcher** — Trigger detection + state migration |
| `checkpoint/storage.py` | ~200+ | S57 | UnifiedCheckpointStorage — Abstract storage interface |
| `checkpoint/backends/memory.py` | — | S57 | MemoryCheckpointStorage (dev default) |
| `checkpoint/backends/redis.py` | — | S57 | RedisCheckpointStorage |
| `checkpoint/backends/postgres.py` | — | S57 | PostgresCheckpointStorage |
| `checkpoint/backends/filesystem.py` | — | S57 | FilesystemCheckpointStorage |
| `claude_maf_fusion.py` | ~171 | S81 | ClaudeMAFFusion — Claude decisions in MAF workflows |
| `swarm_mode.py` | ~400+ | S116 | SwarmModeHandler — Swarm eligibility + execution |

---

## 3. Internal Architecture

### 3.1 Architectural Evolution

```
Phase 13-14 (S52-S57):           Phase 28 (S93-S98):           Phase 39-42 (S132-S148):
┌──────────────────────┐   ┌──────────────────────────┐   ┌──────────────────────────────┐
│ HybridOrchestratorV2 │   │ HybridOrchestratorV2     │   │ OrchestratorMediator         │
│  (God Object)        │   │  + Phase 28 Components   │   │  (Mediator Pattern)          │
│  - FrameworkSelector │   │  + InputGateway           │   │  7 Handlers:                 │
│  - ContextBridge     │   │  + BusinessIntentRouter   │   │  1. ContextHandler           │
│  - ToolExecutor      │   │  + GuidedDialogEngine     │   │  2. RoutingHandler           │
│  - ModeSwitcher      │   │  + RiskAssessor           │   │  3. DialogHandler            │
│  - Checkpoint        │   │  + HITLController         │   │  4. ApprovalHandler          │
│  - RiskEngine        │   │  + SwarmModeHandler       │   │  5. AgentHandler (LLM+FC)    │
└──────────────────────┘   └──────────────────────────┘   │  6. ExecutionHandler         │
                                                           │  7. ObservabilityHandler     │
                                                           │  + PipelineEventEmitter (SSE)│
                                                           │  + OrchestratorBootstrap (DI)│
                                                           └──────────────────────────────┘
```

### 3.2 Current Pipeline Architecture (Sprint 148)

```
                              OrchestratorRequest
                                     │
                        OrchestratorMediator.execute()
                                     │
                     ┌───────────────┼───────────────┐
                     │          Pipeline              │
                     │    (Dict shared context)       │
                     │               │                │
                     │  Step 1: ContextHandler        │──→ ContextBridge.get_or_create_hybrid()
                     │       + MemoryManager          │    + memory retrieval
                     │               │                │
                     │  Step 2: RoutingHandler         │──→ BusinessIntentRouter.route()
                     │       + FrameworkSelector       │    + RoutingDecisionClassifier
                     │               │                │
                     │  Step 3: DialogHandler          │──→ GuidedDialogEngine (conditional)
                     │       (short-circuit?)          │    short-circuit if should_short_circuit
                     │               │                │
                     │  Step 4: ApprovalHandler         │──→ RiskAssessor + HITLController
                     │       (short-circuit?)          │    short-circuit if pending/rejected
                     │               │                │
                     │  Step 4b: HITL via SSE          │──→ asyncio.Event wait (120s timeout)
                     │       (high/critical risk)      │    APPROVAL_REQUIRED event
                     │               │                │
                     │  Step 5: AgentHandler            │──→ LLM chat_with_tools() loop
                     │       (Function Calling)        │    short-circuit if CHAT_MODE
                     │               │                │
                     │  Step 6: ExecutionHandler        │──→ MAF / Claude / Hybrid / Swarm
                     │               │                │
                     │  Step 7: ContextHandler.sync()   │──→ Post-execution context sync
                     │               │                │
                     │  Step 8: ObservabilityHandler    │──→ Metrics recording
                     │               │                │
                     │  Step 9: Memory write            │──→ Long-term memory persistence
                     │               │                │
                     └───────────────┼───────────────┘
                                     │
                        OrchestratorResponse
```

### 3.3 Dependency Injection via Bootstrap

The `OrchestratorBootstrap` (Sprint 134) assembles the full pipeline at startup:

```python
class OrchestratorBootstrap:
    def build(self) -> OrchestratorMediator:
        # 1. Create LLM service via LLMServiceFactory
        # 2. Create OrchestratorToolRegistry + DispatchHandlers
        # 3. Wire 7 handlers in dependency order:
        #    ContextHandler  (ContextBridge + MemoryManager)
        #    RoutingHandler  (InputGateway + BusinessIntentRouter + FrameworkSelector + SwarmHandler)
        #    DialogHandler   (GuidedDialogEngine)
        #    ApprovalHandler (RiskAssessor + HITLController)
        #    AgentHandler    (LLM + ToolRegistry)
        #    ExecutionHandler(ClaudeCoordinator + MAF WorkflowExecutor + SwarmHandler)
        #    ObservabilityHandler (ObservabilityBridge ⚠️ — see Issue 8.11)
        # 4. Register MCP tools via MCPToolBridge
        # 5. Assemble OrchestratorMediator
```

All wiring uses **graceful degradation**: if any dependency is unavailable (ImportError, missing config), the handler is created with a `None` dependency and a warning is logged.

> **⚠️ V9 Wiring Bug**: Bootstrap injects `ObservabilityBridge` (G3/G4/G5 dispatcher) as `metrics` into `ObservabilityHandler`, but the handler expects an object with `record_execution()` / `to_dict()` / `reset()` (i.e., `OrchestratorMetrics`). See Issue 8.11.

---

## 4. Subsystem Analysis

### 4.1 orchestrator/ — Mediator Pipeline

#### 4.1.1 OrchestratorMediator (`mediator.py`)

The central coordinator replacing HybridOrchestratorV2's God Object pattern.

**Core Execute Flow:**
1. Get or create session (with `ConversationStateStore` persistence, Sprint 147)
2. Build shared `pipeline_context` dict
3. Check for checkpoint to resume from (Sprint 147)
4. Emit `PIPELINE_START` SSE event
5. Run handler chain: Context -> Routing -> Dialog -> Approval -> Agent -> Execution -> Context Sync -> Observability
6. Write conversation to long-term memory (Phase 41)
7. Emit `PIPELINE_COMPLETE` SSE event

**Key Features:**
- **Session Management**: In-memory dict with `ConversationStateStore` persistence fallback
- **HITL Approval (Sprint 146)**: `asyncio.Event`-based blocking for high/critical risk operations (120s timeout)
- **Checkpoint Resume (Sprint 147)**: Saves checkpoint after routing and agent steps; can resume from last checkpoint
- **SSE Streaming (Sprint 145)**: `_emit()` helper sends events at each pipeline step via `PipelineEventEmitter`
- **Short-Circuit Support**: Dialog, Approval, and Agent handlers can short-circuit the pipeline

**State Storage:**
- `_sessions: Dict[str, Dict]` — In-memory session cache
- `_conversation_store` — `ConversationStateStore` for persistence (Sprint 147)
- `_checkpoint_storage` — Redis/Memory checkpoint backend (Sprint 147)
- `_pending_approvals: Dict[str, asyncio.Event]` — HITL approval events (Sprint 146)

#### 4.1.2 Contracts (`contracts.py`)

Sprint 132 handler interfaces:

```python
class HandlerType(str, Enum):
    ROUTING, DIALOG, APPROVAL, AGENT, EXECUTION, CONTEXT, OBSERVABILITY

class Handler(ABC):
    handler_type -> HandlerType
    handle(request, context) -> HandlerResult
    can_handle(request, context) -> bool  # Default True

@dataclass OrchestratorRequest:
    content, session_id, user_id, requester, force_mode, tools, max_tokens, timeout,
    metadata, source_request, request_id, timestamp

@dataclass HandlerResult:
    success, handler_type, data, error, should_short_circuit, short_circuit_response

@dataclass OrchestratorResponse:
    success, content, error, framework_used, execution_mode, session_id,
    intent_analysis, tool_results, sync_result, duration, tokens_used,
    metadata, handler_results
```

#### 4.1.3 Handler Chain Detail

| # | Handler | Condition | Short-Circuit | Purpose |
|---|---------|-----------|---------------|---------|
| 1 | **ContextHandler** | Always | No | Prepare HybridContext + inject memories |
| 2 | **RoutingHandler** | Always | No (error stops pipeline) | 3-tier routing + framework selection |
| 3 | **DialogHandler** | `guided_dialog` configured AND `needs_dialog=True` | Yes (`should_short_circuit`) | Gather missing information |
| 4 | **ApprovalHandler** | `source_request` AND (`risk_assessor` OR `hitl_controller`) | Yes (pending/rejected) | Risk assessment + HITL |
| 5 | **AgentHandler** | Always | Yes (CHAT_MODE) | LLM response + Function Calling |
| 6 | **ExecutionHandler** | Always | No | Framework dispatch (MAF/Claude/Swarm) |
| 7 | **ObservabilityHandler** | Always | No | Metrics recording |

#### 4.1.4 AgentHandler — LLM Decision Engine (`agent_handler.py`)

Sprint 107 (Phase 35) + Sprint 144 (Function Calling):

- Uses `LLMServiceProtocol` for LLM interaction
- **Function Calling Loop** (max 5 iterations):
  1. Call `llm_service.chat_with_tools()` with tool schemas
  2. If model returns `tool_calls`, execute each via `OrchestratorToolRegistry`
  3. Append tool results as `role: tool` messages
  4. Loop until model produces final text or max iterations
- **Short-circuit logic**: If `CHAT_MODE` and no swarm needed, returns directly (skips ExecutionHandler)
- **Graceful degradation**: Falls back to `generate()` if `chat_with_tools` unavailable
- **Memory integration**: Includes retrieved memories in system prompt

#### 4.1.5 ExecutionHandler — Framework Dispatch (`handlers/execution.py`)

Dispatches to 4 execution modes:

| Mode | Primary Executor | Fallback |
|------|-----------------|----------|
| `CHAT_MODE` | `ClaudeCoordinator.coordinate_agents` | Simulated response |
| `WORKFLOW_MODE` | `WorkflowExecutorAdapter.run` | Claude fallback |
| `HYBRID_MODE` | Dynamic (MAF if `maf_confidence > 0.7`) | Chat fallback |
| `SWARM_MODE` | `SwarmWorkerExecutor` (Sprint 148, parallel) | Legacy `SwarmModeHandler.execute_swarm()` |

**Swarm Execution (Sprint 148):**
1. Create `TaskDecomposer` with LLM service
2. Decompose request into sub-tasks
3. Create `SwarmWorkerExecutor` per sub-task
4. Execute in parallel with `asyncio.Semaphore(3)` concurrency limit
5. Emit `SWARM_WORKER_START` and `SWARM_PROGRESS` SSE events
6. Combine worker results into single response

### 4.2 intent/ — Framework Selection

#### 4.2.1 FrameworkSelector (`router.py`)

Renamed from `IntentRouter` (Sprint 98) to avoid confusion with `BusinessIntentRouter`.

**Decision Flow:**
1. Run all enabled classifiers on user input
2. Aggregate results using **weighted voting**
3. If confidence >= threshold (class default 0.7, **Bootstrap overrides to 0.6**), use detected mode
4. Otherwise, use default mode (`CHAT_MODE`)

**Classifier Chain (Sprint 144 Bootstrap):**

| Classifier | Weight | Speed | Description |
|------------|--------|-------|-------------|
| `RuleBasedClassifier` | 1.0 | < 1ms | Keyword patterns (EN + zh-TW) |
| `RoutingDecisionClassifier` | 1.5 | ~0ms | Bridges 3-tier `RoutingDecision` to `ExecutionMode` |

**Weighted Aggregation Algorithm:**
```
For each classifier result:
  mode_scores[mode] += confidence * weight
  mode_weights[mode] += weight

best_mode = max(mode_scores)
final_confidence = mode_scores[best_mode] / mode_weights[best_mode]
```

#### 4.2.2 RoutingDecisionClassifier (`classifiers/routing_decision.py`)

Sprint 144 bridge from Layer 04 (Orchestration) three-tier routing to execution mode:

| Intent Category | Risk Level | Mapped Mode | Confidence |
|----------------|------------|-------------|------------|
| QUERY / greeting | LOW | CHAT_MODE | 0.90 |
| QUERY | MEDIUM+ | CHAT_MODE | 0.75 |
| REQUEST | Any | WORKFLOW_MODE | 0.85 |
| CHANGE | HIGH/CRITICAL | WORKFLOW_MODE | 0.90 |
| CHANGE | LOW/MEDIUM | WORKFLOW_MODE | 0.80 |
| INCIDENT | CRITICAL | SWARM_MODE | 0.90 |
| INCIDENT | HIGH | WORKFLOW_MODE | 0.85 |
| INCIDENT | MEDIUM/LOW | WORKFLOW_MODE | 0.75 |
| UNKNOWN | Any | CHAT_MODE | 0.50 |

#### 4.2.3 ExecutionMode Enum

```python
class ExecutionMode(str, Enum):
    WORKFLOW_MODE = "workflow"   # MAF-led multi-step
    CHAT_MODE     = "chat"      # Claude-led conversational
    HYBRID_MODE   = "hybrid"    # Dynamic switching
    SWARM_MODE    = "swarm"     # Multi-agent collaboration (S116)
```

#### 4.2.4 SuggestedFramework Mapping

```
WORKFLOW_MODE -> SuggestedFramework.MAF
CHAT_MODE     -> SuggestedFramework.CLAUDE
SWARM_MODE    -> SuggestedFramework.MAF
HYBRID_MODE   -> SuggestedFramework.HYBRID (or MAF if workflow_active)
```

### 4.3 context/ — Cross-Framework Context Bridge

#### 4.3.1 ContextBridge (`bridge.py`, 933 LOC)

Bidirectional state synchronization between MAF Workflow and Claude Session.

**sync_to_claude(MAFContext) -> ClaudeContext:**
- `checkpoint_data` -> `context_variables` (with `maf_` prefix)
- `execution_history` -> `conversation_history` (last 50, summarized)
- `agent_states` -> `system_prompt` addition
- `pending_approvals` -> `tool_call_history`
- workflow metadata -> `metadata` dict

**sync_to_maf(ClaudeContext) -> MAFContext:**
- `context_variables` -> `checkpoint_data` (strip `maf_` prefix)
- `conversation_history` -> `execution_history`
- tool_call_history -> `checkpoint_data.tool_calls_summary`

**merge_contexts(MAFContext, ClaudeContext) -> HybridContext:**
- Merges both contexts with configurable primary framework
- Detects conflicts (both modified since last sync, > 60s drift)
- Caches result in `_context_cache[session_id]`

**Sync Strategies:**
- `SyncStrategy.MAF_PRIMARY` — MAF wins conflicts
- `SyncStrategy.CLAUDE_PRIMARY` — Claude wins conflicts
- `SyncStrategy.MERGE` — Bidirectional merge based on primary_framework

#### 4.3.2 Data Models (`context/models.py`)

```
MAFContext:
  workflow_id, workflow_name, current_step, total_steps,
  checkpoint_data, execution_history, agent_states, pending_approvals

ClaudeContext:
  session_id, conversation_history, tool_call_history,
  context_variables, current_system_prompt

HybridContext:
  context_id, maf (Optional), claude (Optional),
  primary_framework, sync_status, version, last_sync_at
```

#### 4.3.3 Context Synchronizer (`sync/synchronizer.py`, 692 LOC)

Manages the sync lifecycle with version tracking. Includes:
- `SyncEventPublisher` — publishes sync events
- `ConflictResolver` — resolves sync conflicts by strategy

### 4.4 execution/ — Unified Tool Execution

#### 4.4.1 UnifiedToolExecutor (`unified_executor.py`, 797 LOC)

Central tool execution layer with pre/post hook pipeline.

**Execution Flow:**
1. Lookup tool in registry
2. Run **pre-hooks** (approval check, rate limiting, audit)
3. Execute tool via appropriate framework
4. Run **post-hooks** (result sync, metrics)
5. Return `ToolExecutionResult`

**Tool Sources:**
```python
class ToolSource(Enum):
    MAF     = "maf"      # From MAF Workflow
    CLAUDE  = "claude"   # From Claude Session
    HYBRID  = "hybrid"   # From Hybrid Mode
```

**Hook Pipeline:**
- `ApprovalHook` — blocks execution if HITL approval required
- Pre/post hook chain via `HookExecutionResult`

#### 4.4.2 Supporting Components

| Component | File | Purpose |
|-----------|------|---------|
| `ToolRouter` | `tool_router.py` | Routes tool calls by source framework |
| `ResultHandler` | `result_handler.py` | Normalizes tool execution results |
| `MAFToolCallback` | `tool_callback.py` | MAF tool callback integration |

### 4.5 risk/ — Risk Assessment Engine

#### 4.5.1 RiskAssessmentEngine (`engine.py`, 561 LOC)

Multi-dimensional risk scoring with pluggable analyzers.

**Assessment Flow:**
1. Run pre-assessment hooks
2. Collect `RiskFactor`s from all registered analyzers
3. If no analyzers registered, use base tool-risk lookup
4. Analyze historical patterns (frequency anomalies, escalation)
5. Calculate composite score via `RiskScorer`
6. Apply context adjustment (environment multiplier)
7. **Special handling**: Dangerous commands bypass environment multiplier with minimum score floors
8. Determine `RiskLevel` and approval requirement
9. Run post-assessment hooks
10. Record metrics and history

**Risk Level Thresholds:**
```python
class RiskLevel(Enum):
    LOW      = "low"       # Auto-approved
    MEDIUM   = "medium"    # Auto-approved with logging
    HIGH     = "high"      # Requires human approval
    CRITICAL = "critical"  # Immediate attention + approval
```

**Risk Factor Types (9):**
`OPERATION`, `CONTEXT`, `PATTERN`, `PATH`, `COMMAND`, `FREQUENCY`, `ESCALATION`, `USER`, `ENVIRONMENT`

**Base Tool Risk Scores:**
```
Read/Glob/Grep: 0.1 | Write/Edit: 0.4 | MultiEdit: 0.5 | Bash: 0.6 | Task: 0.3
```

**History-Based Detection:**
- Frequency anomaly: > 10 operations in window -> risk factor (score = count * 0.03, max 0.5)
- Escalation pattern: 3 consecutive increasing scores -> 0.4 risk factor

#### 4.5.2 Risk Models

```python
@dataclass RiskFactor:
    factor_type: RiskFactorType
    score: float (0.0-1.0)
    weight: float (0.0-1.0)
    description: str
    source: Optional[str]
    metadata: Dict

@dataclass RiskAssessment:
    overall_level: RiskLevel
    overall_score: float
    factors: List[RiskFactor]
    requires_approval: bool
    approval_reason: Optional[str]
    session_id: Optional[str]
```

### 4.6 switching/ — Dynamic Mode Switching

#### 4.6.1 ModeSwitcher (`switcher.py`, 836 LOC)

Manages dynamic mode transitions between execution modes.

**Switch Flow:**
1. Run all trigger detectors
2. If trigger detected, validate switch feasibility
3. Create pre-switch checkpoint
4. Migrate state via `StateMigrator`
5. Update execution context
6. On failure: rollback to checkpoint

**Trigger Types:**

| Trigger | Detector | Condition |
|---------|----------|-----------|
| `COMPLEXITY` | `ComplexityTriggerDetector` | Task complexity change |
| `USER_REQUEST` | `UserRequestTriggerDetector` | User explicitly requests |
| `FAILURE` | `FailureTriggerDetector` | Failure recovery needed |
| `RESOURCE` | `ResourceTriggerDetector` | Resource constraints |
| `TIMEOUT` | — | Timeout in current mode |
| `MANUAL` | — | Manual API trigger |

**Migration Directions:**
```
WORKFLOW_TO_CHAT, CHAT_TO_WORKFLOW,
WORKFLOW_TO_HYBRID, CHAT_TO_HYBRID,
HYBRID_TO_WORKFLOW, HYBRID_TO_CHAT
```

#### 4.6.2 StateMigrator (`migration/state_migrator.py`)

Transforms execution state between modes:
- MAF checkpoint -> Claude context variables
- Claude conversation -> MAF execution records
- Preserves tool call history across transitions

### 4.7 checkpoint/ — Unified Checkpoint Storage

#### 4.7.1 Architecture

```
UnifiedCheckpointStorage (Abstract)
    ├── MemoryCheckpointStorage    (dev/testing)
    ├── RedisCheckpointStorage     (recommended)
    ├── PostgresCheckpointStorage  (durable)
    └── FilesystemCheckpointStorage (backup)
```

**Checkpoint Model:**
```python
class CheckpointType(str, Enum):
    AUTO, MANUAL, MODE_SWITCH, HITL, RECOVERY

class CheckpointStatus(str, Enum):
    ACTIVE, EXPIRED, RESTORED, DELETED, CORRUPTED

@dataclass HybridCheckpoint:
    session_id, step_name, step_index, state,
    checkpoint_type, status, created_at
```

**Storage Configuration:**
```python
@dataclass StorageConfig:
    backend: StorageBackend  # REDIS / POSTGRES / FILESYSTEM / MEMORY
    ttl_seconds: int = 86400  # 24 hours
    max_checkpoints_per_session: int = 100
    enable_compression: bool = True
```

**Query API:**
```python
@dataclass CheckpointQuery:
    session_id, checkpoint_type, status, execution_mode,
    created_after, created_before, limit, offset, order_by
```

#### 4.7.2 Serialization (`serialization.py`)

`CheckpointSerializer` with compression support:
- `CompressionAlgorithm`: NONE, ZLIB, GZIP, LZ4
- `CheckpointVersionMigrator` (`version.py`): Schema migration between checkpoint versions

### 4.8 hooks/ — Execution Hooks

#### 4.8.1 RiskDrivenApprovalHook (`approval_hook.py`, 440 LOC)

Full risk-driven approval hook with 3 modes (AUTO/MANUAL/RISK_DRIVEN):
1. Auto-approve read-only tools (Read, Glob, Grep)
2. Run RiskAssessmentEngine with all 3 analyzers (OperationAnalyzer, ContextEvaluator, PatternDetector)
3. If `requires_approval`, blocks execution and invokes `approval_callback`
4. Session-scoped approval caching for deduplication
5. `from_tool_call_context()` helper for Claude SDK integration
6. Returns `ApprovalDecision(approved, reason, risk_assessment)`

**NOTE**: The class is named `RiskDrivenApprovalHook` (not `ApprovalHook`). V8 used the generic name.

### 4.9 prompts/ — Orchestrator Prompts

`ORCHESTRATOR_SYSTEM_PROMPT` in `prompts/orchestrator.py`:
- Used by `AgentHandler` as the system prompt for LLM calls
- Includes routing context, memory context, and tool descriptions

### 4.10 Root-Level Components

#### 4.10.1 HybridOrchestratorV2 (`orchestrator_v2.py`)

**Status: DEPRECATED** (Sprint 132)

The original monolithic orchestrator (~1,395 LOC) that contained all logic in a single class. Now superseded by `OrchestratorMediator` but still exists for backward compatibility. Exports `OrchestratorConfig`, `OrchestratorMetrics`, `ExecutionContextV2`, `HybridResultV2`.

#### 4.10.2 ClaudeMAFFusion (`claude_maf_fusion.py`, 171 LOC)

Sprint 81 fusion layer enabling Claude decisions within MAF workflows:
- `ClaudeDecisionEngine` — LLM-based decision making
- `DynamicWorkflow` — Runtime workflow generation
- `WorkflowDefinition` / `WorkflowStep` — Workflow DSL

#### 4.10.3 SwarmModeHandler (`swarm_mode.py`)

Sprint 116 handler that:
- Analyzes routing decisions for swarm eligibility
- Decomposes tasks into subtasks
- Manages swarm execution configuration from environment variables
- `SwarmExecutionConfig.from_env()` for feature flag support

---

## 5. Pipeline SSE Events (13 Types)

### 5.1 SSEEventType Enum

Sprint 145 (Phase 42) introduced 13 pipeline SSE event types for real-time streaming:

| # | Event Type | Emitted At | Data Fields |
|---|-----------|------------|-------------|
| 1 | `PIPELINE_START` | Pipeline begin | `session_id`, `mode` |
| 2 | `ROUTING_COMPLETE` | After RoutingHandler | `intent`, `risk_level`, `mode`, `confidence`, `routing_layer`, `suggested_mode` |
| 3 | `AGENT_THINKING` | Before AgentHandler | `status: "thinking"` |
| 4 | `TOOL_CALL_START` | Before tool execution | tool metadata |
| 5 | `TOOL_CALL_END` | After tool execution | `tool_name`, `result`, `iteration` |
| 6 | `TEXT_DELTA` | Streaming text chunks | `delta` |
| 7 | `TASK_DISPATCHED` | Before ExecutionHandler | `mode`, `description` |
| 8 | `SWARM_WORKER_START` | Swarm worker launch | `swarm_id`, `mode`, `total_workers`, `tasks` |
| 9 | `SWARM_PROGRESS` | Swarm status update | `completed_workers`, `failed_workers` |
| 10 | `APPROVAL_REQUIRED` | HITL approval needed | `approval_id`, `action`, `risk_level`, `description`, `details` |
| 11 | `CHECKPOINT_RESTORED` | Resuming from checkpoint | `step_name`, `step_index` |
| 12 | `PIPELINE_COMPLETE` | Pipeline success | `content`, `mode`, `processing_time_ms` |
| 13 | `PIPELINE_ERROR` | Pipeline failure | `error` |

(Note: 13 events listed in the SSEEventType enum; `TOOL_CALL_START` is defined but emitted by tool execution code rather than mediator directly.)

### 5.2 AG-UI Protocol Bridge

`PIPELINE_TO_AGUI_MAP` maps Pipeline events to AG-UI protocol events:

| Pipeline Event | AG-UI Event |
|---------------|-------------|
| `PIPELINE_START` | `RUN_STARTED` |
| `ROUTING_COMPLETE` | `STEP_FINISHED` |
| `AGENT_THINKING` | `TEXT_MESSAGE_START` |
| `TOOL_CALL_START` | `TOOL_CALL_START` |
| `TOOL_CALL_END` | `TOOL_CALL_END` |
| `TEXT_DELTA` | `TEXT_MESSAGE_CONTENT` |
| `TASK_DISPATCHED` | `STEP_STARTED` |
| `SWARM_WORKER_START` | `STEP_STARTED` |
| `SWARM_PROGRESS` | `STATE_SNAPSHOT` |
| `APPROVAL_REQUIRED` | `STATE_SNAPSHOT` |
| `CHECKPOINT_RESTORED` | `STATE_SNAPSHOT` |
| `PIPELINE_COMPLETE` | `RUN_FINISHED` |
| `PIPELINE_ERROR` | `RUN_ERROR` |

### 5.3 PipelineEventEmitter

```python
class PipelineEventEmitter:
    _queue: asyncio.Queue[SSEEvent]
    _closed: bool

    emit(event_type, data)        # Push event to queue
    emit_text_delta(delta)        # Convenience: TEXT_DELTA
    emit_complete(content, meta)  # PIPELINE_COMPLETE + close
    emit_error(error)             # PIPELINE_ERROR + close
    stream(agui_format=False)     # AsyncGenerator for SSE endpoint
```

- Stream terminates on `PIPELINE_COMPLETE` or `PIPELINE_ERROR`
- 120-second timeout with keepalive comments
- Dual format: native Pipeline events or AG-UI protocol events

---

## 6. FrameworkSelector Decision Logic (Detail)

### 6.1 Two-Path Routing

The `RoutingHandler` supports two routing flows:

**Phase 28 Flow** (when `source_request` present):
1. `InputGateway.process(source_request)` -> `RoutingDecision`
2. Check completeness (`routing_decision.completeness.is_sufficient`)
3. Check swarm eligibility via `SwarmModeHandler.analyze_for_swarm()`
4. `FrameworkSelector.select_framework(user_input, routing_decision=routing_decision)`

**Direct Flow** (no source_request):
1. `BusinessIntentRouter.route(content)` -> `RoutingDecision` (3-tier: Pattern -> Semantic -> LLM)
2. If `force_mode` set by user: override with confidence=1.0
3. Otherwise: `FrameworkSelector.select_framework(user_input, routing_decision=routing_decision)`
4. Generate `suggested_mode` from routing_decision for UI display

### 6.2 Mode Suggestion Logic

Sprint 144 generates a UI suggestion (display only, user controls actual mode):

```python
if "incident" in intent and "critical" in risk:
    suggested_mode = "swarm"
elif "incident" in intent and "high" in risk:
    suggested_mode = "workflow"
elif "request" in intent or "change" in intent:
    suggested_mode = "workflow"
```

### 6.3 Classifier Interaction

```
                    User Input
                        │
            ┌───────────┼───────────┐
            │                       │
    RuleBasedClassifier     RoutingDecisionClassifier
       (weight=1.0)            (weight=1.5)
       keyword match        IT intent -> ExecutionMode
            │                       │
            └───────────┬───────────┘
                        │
                Weighted Aggregation
                        │
                    ExecutionMode
                 (if confidence >= 0.6, Bootstrap override)
```

---

## 7. Mediator Pattern Details

### 7.1 Handler Protocol

```python
class Handler(ABC):
    @property
    def handler_type(self) -> HandlerType: ...
    async def handle(self, request, context) -> HandlerResult: ...
    def can_handle(self, request, context) -> bool:
        return True  # Default: always handle
```

### 7.2 Pipeline Context (Shared Dict)

The `pipeline_context` dict is shared across all handlers as the communication mechanism:

| Key | Set By | Used By | Type |
|-----|--------|---------|------|
| `session_id` | Mediator | All | `str` |
| `conversation_history` | Mediator | RoutingHandler, AgentHandler | `List[Dict]` |
| `current_mode` | Mediator | RoutingHandler | `ExecutionMode` |
| `event_emitter` | Mediator | ExecutionHandler, Mediator | `PipelineEventEmitter` |
| `hybrid_context` | ContextHandler | ContextHandler (post-sync) | `HybridContext` |
| `memory_manager` | ContextHandler | Mediator (memory write) | `OrchestratorMemoryManager` |
| `memory_context` | ContextHandler | AgentHandler | `str` |
| `retrieved_memories` | ContextHandler | — | `List` |
| `routing_decision` | RoutingHandler | ApprovalHandler, AgentHandler, Mediator | `RoutingDecision` |
| `needs_dialog` | RoutingHandler | DialogHandler | `bool` |
| `swarm_decomposition` | RoutingHandler | ExecutionHandler | `SwarmTaskDecomposition` |
| `intent_analysis` | RoutingHandler | ExecutionHandler, Mediator | `IntentAnalysis` |
| `execution_mode` | RoutingHandler | AgentHandler, ExecutionHandler, Mediator | `ExecutionMode` |
| `suggested_mode` | RoutingHandler | Mediator (response metadata) | `Optional[str]` |
| `risk_assessment` | ApprovalHandler | Mediator (response metadata) | `RiskAssessment` |
| `agent_response` | AgentHandler | Mediator (_build_response fallback) | `Dict` |
| `framework_used` | ExecutionHandler | ObservabilityHandler | `str` |
| `execution_success` | ExecutionHandler | ObservabilityHandler | `bool` |
| `execution_duration` | ExecutionHandler | ObservabilityHandler | `float` |

### 7.3 Short-Circuit Mechanism

Three handlers support short-circuiting:

1. **DialogHandler**: When `result.should_short_circuit` — returns questions to user
2. **ApprovalHandler**: When `approval_result.status == PENDING/REJECTED` — blocks execution
3. **AgentHandler**: When `CHAT_MODE` and no swarm needed — returns direct LLM response

Short-circuit produces a `HandlerResult` with:
```python
should_short_circuit=True
short_circuit_response={"content": "...", "status": "..."}
```

The mediator converts this via `_build_short_circuit_response()`.

---

## 8. Known Issues

### 8.1 CRITICAL: ContextBridge Race Condition

**Location**: `context/bridge.py`, `_context_cache: Dict[str, HybridContext]`

The `ContextBridge` uses a plain Python `dict` (`_context_cache`) without any `asyncio.Lock`. Multiple concurrent requests for the same session could interleave reads/writes, causing:
- Stale context being served
- Context overwrites losing updates
- Inconsistent sync status

**Impact**: Medium-High in production with concurrent users sharing sessions.

**Fix**: Add `asyncio.Lock` per session_id or use a concurrent-safe cache.

### 8.2 ~~CRITICAL~~ RESOLVED (Sprint 119): ContextSynchronizer Thread-Safety

**Location**: `context/sync/synchronizer.py`

**Status: FIXED in Sprint 119.** The `ContextSynchronizer` was upgraded to use:
1. `self._lock` — Redis distributed lock (via `_create_lock()`) with `_AsyncioLockAdapter` fallback
2. `self._state_lock` — dedicated `asyncio.Lock` protecting `_context_versions` and `_rollback_snapshots`

The V8 analysis documented this as an in-memory dict without locks, but Sprint 109 (H-04 fix) added `_state_lock` and Sprint 119 added the full distributed lock. The `CLAUDE.md` known issue description is now outdated.

**Remaining risk**: `ContextBridge._context_cache` (Issue 8.1) is still unprotected — the Synchronizer fix does NOT cover the Bridge's cache.

### 8.3 HIGH: MemoryCheckpointStorage as Default

**Location**: `orchestrator/mediator.py:100-110`

The Mediator falls back to `MemoryCheckpointStorage` when `RedisCheckpointStorage` is unavailable. In-memory storage loses all checkpoints on process restart, which defeats the purpose of checkpoint-based recovery.

```python
# Current fallback chain:
try: RedisCheckpointStorage()
except: try: MemoryCheckpointStorage()  # <- Production risk
```

### 8.4 HIGH: Session State In-Memory Only

**Location**: `orchestrator/mediator.py:89`

`self._sessions: Dict[str, Dict]` is the primary session store. While Sprint 147 added `ConversationStateStore` persistence, session lookup still checks in-memory first and only falls back to the store. Process restart loses all active sessions.

### 8.5 MEDIUM: HybridOrchestratorV2 Still Exported

The deprecated `HybridOrchestratorV2` is still exported from `hybrid/__init__.py` and imported in various locations. This creates confusion about which orchestrator is the canonical one. The module should deprecation-warn all imports.

### 8.6 MEDIUM: HITL Approval Timeout

**Location**: `orchestrator/mediator.py:377`

HITL approval uses `asyncio.wait_for(event.wait(), timeout=120)`. If timeout occurs:
- The approval is silently discarded
- Pipeline continues execution without approval
- This is a security gap: high-risk operations execute without approval after 120s

### 8.7 LOW: Dual Swarm Execution Paths

**Location**: `handlers/execution.py:223-392`

`_execute_swarm()` first tries the new `SwarmWorkerExecutor` (Sprint 148), then falls back to legacy `SwarmModeHandler.execute_swarm()`. The two paths have different behavior and result formats, making debugging complex.

### 8.8 LOW: Enum String Comparison

**Location**: Multiple files

Several places use string matching on enum values (e.g., `"high" in rd_risk`) instead of proper enum comparison, which is fragile.

### 8.9 MEDIUM: ModeSwitcher InMemoryCheckpointStorage Default (R4 finding)

**Location**: `switching/switcher.py:277-283`

`ModeSwitcher.__init__()` falls back to `InMemoryCheckpointStorage()` with only a warning log when no `checkpoint_storage` is provided. Sprint 120 added `RedisSwitchCheckpointStorage` but it is not wired as default. Rollback checkpoints are lost on restart.

### 8.10 LOW: datetime.utcnow() Widespread Usage (R4 finding)

**Location**: `context/models.py`, `checkpoint/models.py`, `risk/models.py`, `switching/models.py`, `execution/unified_executor.py`, and ~20 more files

Almost all dataclass `default_factory` uses `datetime.utcnow()` which is deprecated in Python 3.12+. Only Sprint 111+ files use `datetime.now(timezone.utc)`.

### 8.11 MEDIUM: ObservabilityHandler Wiring Mismatch (V9 finding)

**Location**: `orchestrator/bootstrap.py:472-489`, `orchestrator/handlers/observability.py:31-35`

`OrchestratorBootstrap._wire_observability_handler()` injects `ObservabilityBridge` as the `metrics` parameter. However, `ObservabilityBridge` is a G3/G4/G5 subsystem dispatcher (Patrol, Correlation, RootCause) and does NOT implement the `record_execution()`, `execution_count`, `to_dict()`, or `reset()` methods that `ObservabilityHandler.handle()` calls. The handler's fallback (`metrics or OrchestratorMetrics()`) does not trigger because the injected `ObservabilityBridge` is not `None`.

**Impact**: Every pipeline execution hits the `except` branch in `ObservabilityHandler.handle()`, returning `recorded: False`. Metrics are silently lost.

**Fix**: Bootstrap should inject `OrchestratorMetrics()` (from `orchestrator_v2.py`) as `metrics`, or create a new `PipelineMetrics` class. `ObservabilityBridge` should be wired separately for G3/G4/G5 dispatch.

### 8.12 LOW: ComplexityAnalyzer and MultiAgentDetector Not Wired (R4 finding)

**Location**: `intent/analyzers/complexity.py`, `intent/analyzers/multi_agent.py`

Both analyzers exist (428 + 567 LOC) but are not registered as classifiers in the `FrameworkSelector` pipeline. The Bootstrap wires only `RuleBasedClassifier` and `RoutingDecisionClassifier`. The complexity and multi-agent analysis is duplicated — similar logic exists in the `ComplexityTriggerDetector` (switching/triggers/complexity.py) and `SwarmModeHandler`.

---

## 9. Phase Evolution

| Phase | Sprints | Focus | Key Changes |
|-------|---------|-------|-------------|
| **Phase 13** | S52-S54 | Hybrid Core Architecture | `FrameworkSelector`, `ContextBridge`, `UnifiedToolExecutor`, `HybridOrchestratorV2` |
| **Phase 14** | S55-S57 | HITL & Approval | `RiskAssessmentEngine`, `ModeSwitcher`, `UnifiedCheckpointStorage` (4 backends) |
| **Phase 17** | S81 | Claude+MAF Fusion | `ClaudeMAFFusion`, `ClaudeDecisionEngine`, `DynamicWorkflow` |
| **Phase 28** | S93-S98 | Three-Tier Routing | Phase 28 component integration, `FrameworkSelector` rename (was `IntentRouter`) |
| **Phase 29** | S116 | Agent Swarm | `SwarmModeHandler`, `SwarmExecutionConfig`, SWARM_MODE execution mode |
| **Phase 35** | S107 | A0 Validation | `AgentHandler` — first LLM-powered handler in pipeline |
| **Phase 39** | S132-S134 | Mediator Refactor | `OrchestratorMediator`, 6 Handlers, `OrchestratorBootstrap`, `contracts.py` |
| **Phase 41** | S135 | Memory Integration | `ContextHandler` + `OrchestratorMemoryManager`, long-term memory writes |
| **Phase 42** | S144-S148 | Deep Integration | Function Calling, `RoutingDecisionClassifier`, 13 SSE events, HITL via SSE, session persistence, checkpoint resume, Swarm parallel execution |

---

## 10. Cross-Layer Dependencies

### 10.1 Upstream (Layer 05 depends on)

| Layer | Component | Used For |
|-------|-----------|----------|
| **Layer 04 (Orchestration)** | `BusinessIntentRouter` | 3-tier IT intent classification |
| **Layer 04** | `InputGateway` | Source identification + routing |
| **Layer 04** | `GuidedDialogEngine` | Multi-turn dialog guidance |
| **Layer 04** | `RiskAssessor` | Phase 28 risk assessment |
| **Layer 04** | `HITLController` | Approval workflow management |
| **Layer 06 (MAF)** | `WorkflowExecutorAdapter` | MAF workflow execution |
| **Layer 07 (Claude SDK)** | `ClaudeCoordinator` | Claude agent coordination |
| **Layer 08 (MCP)** | `MCPToolBridge` | MCP tool discovery + registration |
| **Layer 09 (LLM)** | `LLMServiceFactory` | LLM service for AgentHandler |
| **Layer 10 (Memory)** | `UnifiedMemoryManager` | Long-term memory storage |
| **Layer 11 (Infrastructure)** | `ConversationStateStore`, `TaskStore` | Persistent storage |
| **Layer 12 (Swarm)** | `TaskDecomposer`, `SwarmWorkerExecutor` | Swarm task execution |

### 10.2 Downstream (depends on Layer 05)

| Consumer | Component | Usage |
|----------|-----------|-------|
| **API Layer** | `api/v1/orchestration/` | HTTP endpoint -> `OrchestratorMediator.execute()` |
| **API Layer** | `api/v1/hybrid/` | Legacy V2 endpoints |
| **AG-UI** | SSE endpoints | Consume `PipelineEventEmitter.stream()` |

---

## 11. Export Summary

The `hybrid/__init__.py` exports 42 symbols organized by sprint:

| Sprint | Exports |
|--------|---------|
| S52/S98 | `ExecutionMode`, `FrameworkAnalysis`, `FrameworkSelector`, `IntentAnalysis`, `IntentRouter`, `SessionContext` |
| S53 | `ContextBridge`, `HybridContext`, `MAFContext`, `ClaudeContext`, `SyncDirection`, `SyncResult`, `SyncStrategy` |
| S54 | `UnifiedToolExecutor`, `ToolSource`, `ToolExecutionResult`, `ToolRouter`, `MAFToolCallback`, `MAFToolResult` |
| S54 | `HybridOrchestratorV2`, `OrchestratorMode`, `OrchestratorConfig`, `ExecutionContextV2`, `HybridResultV2`, `OrchestratorMetrics`, `create_orchestrator_v2` |
| S116 | `SwarmModeHandler`, `SwarmExecutionConfig`, `SwarmExecutionResult`, `SwarmTaskDecomposition` |
| S132 | `OrchestratorMediator`, `Handler`, `HandlerResult`, `HandlerType`, `OrchestratorRequest`, `OrchestratorResponse`, `EventType`, `OrchestratorEvent`, `AgentHandler`, all 6 handler classes |
| S81 | `ClaudeMAFFusion`, `ClaudeDecisionEngine`, `DynamicWorkflow`, `WorkflowDefinition`, `WorkflowStep`, `WorkflowStepType`, `DecisionType`, `ClaudeDecision`, `ExecutionState`, `StepResult`, `WorkflowResult` |

---

## 12. Metrics and Observability

### 12.1 OrchestratorMetrics

Tracks per-execution metrics:
- `execution_count` by mode and framework
- `success_rate` per framework
- `average_duration` per mode
- Exportable via `ObservabilityHandler.get_metrics()`

> **⚠️ V9 Note**: Due to Issue 8.11 (Bootstrap wires `ObservabilityBridge` instead of `OrchestratorMetrics`), pipeline metrics recording and `get_metrics()` are currently non-functional in the bootstrapped pipeline. The `OrchestratorMetrics` class itself works correctly when instantiated directly.

### 12.2 RiskAssessmentEngine Metrics

```python
@dataclass EngineMetrics:
    total_assessments: int
    assessments_by_level: Dict[str, int]  # low/medium/high/critical
    average_score: float
    approval_rate: float
    average_latency_ms: float
```

### 12.3 ModeSwitcher Metrics

```python
@dataclass SwitcherMetrics:
    total_switches: int
    successful_switches: int
    failed_switches: int
```

---

*Analysis generated by reading 85 source files from `backend/src/integrations/hybrid/`. All code references are based on the actual implementation as of the current branch (`feature/phase-42-deep-integration`).*
