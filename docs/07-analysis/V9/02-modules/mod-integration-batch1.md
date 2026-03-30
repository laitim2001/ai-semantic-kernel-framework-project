# V9 Phase C — Integration Modules Deep-Dive (Batch 1)

> **Generated**: 2026-03-29 | **Scope**: 10 integration modules under `backend/src/integrations/`
> **Method**: Source-reading of 40+ key files, CLAUDE.md cross-reference, test directory scan

---

## Table of Contents

1. [hybrid/](#module-hybrid) — MAF + Claude SDK Bridge
2. [agent_framework/](#module-agent_framework) — MAF Adapters
3. [orchestration/](#module-orchestration) — Three-tier Intent Routing
4. [claude_sdk/](#module-claude_sdk) — Claude Agent SDK
5. [mcp/](#module-mcp) — Model Context Protocol
6. [ag_ui/](#module-ag_ui) — AG-UI Protocol
7. [swarm/](#module-swarm) — Agent Swarm
8. [llm/](#module-llm) — LLM Service Abstraction
9. [knowledge/](#module-knowledge) — RAG Pipeline
10. [memory/](#module-memory) — Unified Memory

---

### 整合模組中心樞紐架構

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                Integration Modules 中心樞紐 (Batch 1)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐   ┌──────────────┐   ┌───────────────┐                    │
│  │orchestration│   │agent_framework│   │  claude_sdk   │                    │
│  │ 三層意圖路由 │   │ MAF Adapters  │   │ Claude Agent  │                    │
│  │ (22 files)  │   │ (30+ builders)│   │  SDK (40 files)│                   │
│  └──────┬──────┘   └──────┬───────┘   └──────┬────────┘                    │
│         │                 │                   │                              │
│         └────────────┬────┴───────────────────┘                              │
│                      │                                                       │
│                      ↓                                                       │
│         ┌────────────────────────────┐                                       │
│         │     hybrid/ (89 files)     │  ← 中央協調器                         │
│         │  OrchestratorMediator      │                                       │
│         │  ContextBridge             │                                       │
│         │  FrameworkSelector         │                                       │
│         │  MediatorEventBridge       │                                       │
│         └────────────┬───────────────┘                                       │
│                      │                                                       │
│         ┌────────────┼─────────────────┐                                     │
│         │            │                 │                                     │
│         ↓            ↓                 ↓                                     │
│  ┌──────────┐  ┌──────────┐   ┌──────────────┐                              │
│  │  ag_ui/  │  │   mcp/   │   │   swarm/     │                              │
│  │ AG-UI SSE│  │ 5 Servers│   │ 多Agent協作  │                              │
│  │(14 files)│  │(25 files)│   │ (21 files)   │                              │
│  └──────────┘  └──────────┘   └──────────────┘                              │
│                                                                             │
│  ┌──────────┐  ┌──────────┐   ┌──────────────┐                              │
│  │   llm/   │  │knowledge/│   │   memory/    │                              │
│  │ LLM 抽象 │  │RAG Pipeline│  │ 統一記憶    │                              │
│  │(14 files)│  │(14 files)│   │ (11 files)   │                              │
│  └──────────┘  └──────────┘   └──────────────┘                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

<a id="module-hybrid"></a>
## Module: hybrid

- **Path**: `backend/src/integrations/hybrid/`
- **Files**: 89 `.py` files | **Phase**: 13–42 (Sprint 52–148)

### Public API

#### OrchestratorMediator (`orchestrator/mediator.py`) — 845 LOC
Central coordinator replacing the earlier HybridOrchestratorV2 God Object.

```python
class OrchestratorMediator:
    def __init__(self, *, routing_handler, dialog_handler, approval_handler,
                 agent_handler, execution_handler, context_handler, observability_handler)
    def register_handler(self, handler: Handler) -> None
    def get_handler(self, handler_type: HandlerType) -> Optional[Handler]
    def create_session(self, session_id=None, metadata=None) -> str
    def get_session(self, session_id: str) -> Optional[Dict]
    def close_session(self, session_id: str) -> bool
    def resolve_approval(self, approval_id: str, action: str) -> bool
    async def execute(self, request: OrchestratorRequest, event_emitter=None) -> OrchestratorResponse
    async def execute_tool(self, tool_name, arguments, *, source, session_id, ...) -> ToolExecutionResult
    def get_metrics(self) -> Dict[str, Any]
    def reset_metrics(self) -> None
```

**Pipeline**: Context → Routing → Dialog (conditional) → Approval (conditional) → Agent (LLM) → Execution → Observability

#### OrchestratorMediator 7-Handler Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  OrchestratorMediator 處理管線                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  OrchestratorRequest                                                    │
│       │                                                                 │
│       ↓                                                                 │
│  ① CONTEXT Handler ──→ 載入 Session/Memory/Checkpoint 上下文            │
│       │                                                                 │
│       ↓                                                                 │
│  ② ROUTING Handler ──→ 三層意圖路由 (Pattern→Semantic→LLM)             │
│       │                  ↓ 判斷意圖類型 + 風險等級                       │
│       ↓                                                                 │
│  ③ DIALOG Handler ──→ [條件] 需要澄清? → 引導式對話                    │
│       │                  ↓ short_circuit 如需更多資訊                    │
│       ↓                                                                 │
│  ④ APPROVAL Handler ─→ [條件] 高風險? → HITL 審批閘門                  │
│       │                  ↓ 等待人工審批或自動放行                        │
│       ↓                                                                 │
│  ⑤ AGENT Handler ────→ 選擇框架 (MAF / Claude / Hybrid / Swarm)        │
│       │                  ↓ LLM 推理 + 工具調用                          │
│       ↓                                                                 │
│  ⑥ EXECUTION Handler → 執行工具/子任務 + 結果整合                      │
│       │                                                                 │
│       ↓                                                                 │
│  ⑦ OBSERVABILITY Handler → 指標收集 + SSE 事件串流 + Audit Log         │
│       │                                                                 │
│       ↓                                                                 │
│  OrchestratorResponse                                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Contracts (`orchestrator/contracts.py`)
```python
class HandlerType(Enum): ROUTING, DIALOG, APPROVAL, AGENT, EXECUTION, CONTEXT, OBSERVABILITY
@dataclass class OrchestratorRequest: content, session_id, user_id, force_mode, tools, ...
@dataclass class HandlerResult: success, handler_type, data, should_short_circuit, ...
@dataclass class OrchestratorResponse: success, content, framework_used, execution_mode, ...
class Handler(ABC): handler_type, handle(), can_handle()
```

#### SSE Events (`orchestrator/sse_events.py`)
```python
class SSEEventType(Enum):  # 13 event types
    PIPELINE_START, ROUTING_COMPLETE, AGENT_THINKING, TOOL_CALL_START/END,
    TEXT_DELTA, TASK_DISPATCHED, SWARM_WORKER_START, SWARM_PROGRESS,
    APPROVAL_REQUIRED, CHECKPOINT_RESTORED, PIPELINE_COMPLETE, PIPELINE_ERROR

class PipelineEventEmitter:
    async def emit(self, event_type: SSEEventType, data: Dict) -> None
    async def emit_text_delta(self, delta: str) -> None
    async def emit_complete(self, content: str, metadata=None) -> None
    async def emit_error(self, error: str) -> None
    async def stream(self, agui_format: bool = False) -> AsyncGenerator[str, None]
```

#### ContextBridge (`context/bridge.py`) — 933 LOC
```python
class ContextBridge:
    def __init__(self, maf_mapper=None, claude_mapper=None, synchronizer=None)
    async def sync_to_claude(self, maf_context, existing_claude=None) -> ClaudeContext
    async def sync_to_maf(self, claude_context, existing_maf=None) -> MAFContext
    async def merge_contexts(self, maf_context=None, claude_context=None, primary="maf") -> HybridContext
    async def get_or_create_hybrid(self, session_id: str) -> HybridContext
    async def sync_after_execution(self, result, hybrid_context) -> Optional[SyncResult]
    async def sync_bidirectional(self, hybrid_context, strategy=SyncStrategy.MERGE) -> SyncResult
```

#### RiskAssessmentEngine (`risk/engine.py`) — 561 LOC
```python
class RiskAssessmentEngine:
    def __init__(self, config=None, scorer=None, analyzers=None)
    def register_analyzer(self, analyzer: AnalyzerProtocol) -> None
    def register_hook(self, hook_type: str, callback: Callable) -> None
    def assess(self, context: OperationContext, include_history=True) -> RiskAssessment
    def assess_batch(self, contexts: List[OperationContext]) -> List[RiskAssessment]
    def get_session_risk(self, session_id: str, window_seconds=None) -> ScoringResult
    def get_metrics(self) -> EngineMetrics

def create_engine(config=None, with_default_analyzers=False) -> RiskAssessmentEngine
```

#### UnifiedCheckpointStorage (`checkpoint/storage.py`)
```python
class UnifiedCheckpointStorage(ABC):
    async def save(self, checkpoint: HybridCheckpoint) -> str
    async def load(self, checkpoint_id: str) -> Optional[HybridCheckpoint]
    async def delete(self, checkpoint_id: str) -> bool
    async def query(self, query: CheckpointQuery) -> List[HybridCheckpoint]
    async def load_latest(self, session_id: str) -> Optional[HybridCheckpoint]
    async def restore(self, checkpoint_id: str) -> RestoreResult
    async def enforce_retention(self, session_id: str) -> int
    async def cleanup_expired(self) -> int

class StorageBackend(Enum): REDIS, POSTGRES, FILESYSTEM, MEMORY
```

### Dependencies (imports from)

| Dependency | Usage |
|---|---|
| `hybrid.intent` | ExecutionMode, IntentAnalysis, SessionContext |
| `hybrid.context` | ContextBridge, HybridContext, SyncResult, MAFContext, ClaudeContext |
| `hybrid.execution` | UnifiedToolExecutor, ToolExecutionResult, ToolSource |
| `hybrid.checkpoint.backends` | RedisCheckpointStorage, MemoryCheckpointStorage |
| `hybrid.orchestrator.handlers.*` | RoutingHandler, DialogHandler, ApprovalHandler, ExecutionHandler, ContextHandler, ObservabilityHandler |
| `infrastructure.storage` | ConversationStateStore (Sprint 147) |

### Dependents (imported by)

| Consumer | Usage |
|---|---|
| `api/v1/hybrid/` | HTTP endpoints for orchestrator |
| `api/v1/orchestration/` | Pipeline SSE streaming |
| `ag_ui/bridge.py` | HybridEventBridge wraps HybridOrchestratorV2 |
| `orchestration/` | Framework selection via hybrid intent |

### Configuration

| Env Var | Default | Purpose |
|---|---|---|
| `REDIS_HOST` / `REDIS_PORT` | localhost:6379 | Checkpoint storage (Redis backend) |
| `DB_HOST` / `DB_PORT` | localhost:5432 | Checkpoint storage (Postgres backend) |
| (none explicit) | — | Session storage uses in-memory dict by default |

### Test Coverage

- `tests/unit/integrations/hybrid/` — 29+ test files (context, intent, risk, checkpoint, execution, switching)
- `tests/integration/hybrid/` — 5 integration tests (context_bridge, orchestrator_v2, phase14, swarm_routing)
- `tests/e2e/` — E2E pipeline tests via orchestration

### Known Issues

- **ContextSynchronizer**: In-memory dict without locks (thread-safety risk)
- **MemoryCheckpointStorage**: Used as production default; should use PostgreSQL/Redis
- **God Object legacy**: `orchestrator_v2.py` (1,254 LOC) still exists alongside Mediator pattern

---

<a id="module-agent_framework"></a>
## Module: agent_framework

- **Path**: `backend/src/integrations/agent_framework/`
- **Files**: 57 `.py` files | **Phase**: 1–37 (Sprint 14–37)

### Public API

**`builders/__init__.py`** exports 200+ symbols across 12 builder adapters + migration layers:

| Builder Adapter | Official MAF Class | Sprint | Key Factory Functions |
|---|---|---|---|
| `ConcurrentBuilderAdapter` | `ConcurrentBuilder` | S14 | `create_all_concurrent()`, `create_any_concurrent()` |
| `HandoffBuilderAdapter` | `HandoffBuilder` | S15 | `create_handoff_adapter()`, `create_human_in_loop_handoff()` |
| `GroupChatBuilderAdapter` | `GroupChatBuilder` | S16 | `create_groupchat_adapter()`, `create_round_robin_chat()` |
| `MagenticBuilderAdapter` | `MagenticBuilder` | S17 | `create_magentic_adapter()`, `create_research_workflow()` |
| `WorkflowExecutorAdapter` | `WorkflowExecutor` | S18 | `create_workflow_executor()` |
| `GroupChatVotingAdapter` | — | S20 | `create_voting_chat()`, `create_majority_voting_chat()` |
| `HandoffPolicyAdapter` | — | S21 | `adapt_policy()`, `adapt_immediate()` |
| `CapabilityMatcherAdapter` | — | S21 | `create_capability_matcher()` |
| `ContextTransferAdapter` | — | S21 | `create_context_transfer_adapter()` |
| `HandoffService` | — | S21 | `create_handoff_service()` |
| `NestedWorkflowAdapter` | — | S23 | `create_nested_workflow_adapter()` |
| `PlanningAdapter` | — | S24 | `create_planning_adapter()`, `create_full_planner()` |
| `AgentExecutorAdapter` | — | S31 | `create_agent_executor_adapter()` |
| `CodeInterpreterAdapter` | — | S37 | Direct class usage |
| `MultiTurnAdapter` | `CheckpointStorage` | S24 | `create_multiturn_adapter()` |

Additional subsystems: `core/` (WorkflowAdapter, ExecutorAdapter, Edge, Events), `multiturn/`, `memory/`.

### MAF Compliance Status

All builder adapters follow the required Adapter Pattern:
1. Import official class from `agent_framework` package
2. Create `self._builder = OfficialBuilder()` in `__init__`
3. Call `self._builder.build()` in `build()` method

Verification: `python scripts/verify_official_api_usage.py` (5 checks must pass)

### Dependencies (imports from)

| Dependency | Usage |
|---|---|
| `agent_framework` (pip package) | All official MAF classes: ConcurrentBuilder, GroupChatBuilder, HandoffBuilder, MagenticBuilder, etc. |

### Dependents (imported by)

| Consumer | Usage |
|---|---|
| `hybrid/execution/` | UnifiedToolExecutor dispatches to MAF builders |
| `claude_sdk/hybrid/` | Claude-MAF fusion layer |
| `orchestration/` | Workflow type selection (MAGENTIC, SEQUENTIAL, etc.) |
| `api/v1/agents/`, `api/v1/workflows/` | Agent CRUD, workflow execution endpoints |

### Configuration

| Env Var | Default | Purpose |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | — | LLM for MagenticBuilder planning |
| `AZURE_OPENAI_API_KEY` | — | LLM authentication |

### Test Coverage

- `tests/unit/integrations/agent_framework/` — 20+ test files covering all builders
- `tests/unit/integrations/agent_framework/builders/` — Per-builder unit tests

### Known Issues

- **Preview SDK**: `agent_framework` 1.0.0b251204 — API may change
- **Large export surface**: 200+ symbols in `builders/__init__.py` (maintenance overhead)
- **Migration layers**: 5 legacy migration modules still present (concurrent, handoff, groupchat, magentic, workflow_executor)

---

<a id="module-orchestration"></a>
## Module: orchestration

- **Path**: `backend/src/integrations/orchestration/`
- **Files**: 39 `.py` files | **Phase**: 28 (Sprint 91–99) + Sprint 116

### Public API

#### BusinessIntentRouter (`intent_router/router.py`) — 623 LOC
```python
class BusinessIntentRouter:
    def __init__(self, pattern_matcher, semantic_router, llm_classifier,
                 completeness_checker=None, config=None)
    async def route(self, user_input: str) -> RoutingDecision
    def get_metrics(self) -> Dict[str, Any]
    def reset_metrics(self) -> None

def create_router(...) -> BusinessIntentRouter  # Manual wiring
def create_router_with_llm(config=None) -> BusinessIntentRouter  # Auto LLM from env
```

Three-tier routing: Pattern (<10ms) → Semantic (<100ms) → LLM (<2000ms)

#### Contracts (`contracts.py`) — L4a/L4b Interface
```python
class InputSource(Enum): WEBHOOK_SERVICENOW, WEBHOOK_PROMETHEUS, HTTP_API, SSE_STREAM, USER_CHAT, RITM
@dataclass class RoutingRequest: query, intent_hint, context, source, request_id, ...
@dataclass class RoutingResult: intent, sub_intent, confidence, matched_layer, workflow_type, risk_level, ...
class InputGatewayProtocol(ABC): receive(), validate()
class RouterProtocol(ABC): route(), get_available_layers()

def incoming_request_to_routing_request(incoming, source) -> RoutingRequest
def routing_decision_to_routing_result(decision) -> RoutingResult
```

#### Key Models (`intent_router/models.py`)
```python
class ITIntentCategory(Enum): INCIDENT, REQUEST, CHANGE, QUERY, UNKNOWN
class WorkflowType(Enum): MAGENTIC, HANDOFF, CONCURRENT, SEQUENTIAL, SIMPLE
class RiskLevel(Enum): CRITICAL, HIGH, MEDIUM, LOW
@dataclass class RoutingDecision: intent_category, sub_intent, confidence, workflow_type, risk_level, completeness, routing_layer, ...
```

#### Other Components
- `GuidedDialogEngine` — Multi-turn dialog for incomplete requests
- `InputGateway` — Source-aware routing (ServiceNow, Prometheus, User)
- `HITLController` + `UnifiedHITLManager` — Approval workflows
- `RiskAssessor` — Context-aware risk evaluation
- `OrchestrationMetricsCollector` — OpenTelemetry metrics

### Dependencies (imports from)

| Dependency | Usage |
|---|---|
| `llm` (factory) | `LLMServiceFactory.create()` for Layer 3 LLM classifier |
| `orchestration/intent_router/*` | PatternMatcher, SemanticRouter, LLMClassifier, CompletenessChecker |

### Dependents (imported by)

| Consumer | Usage |
|---|---|
| `hybrid/orchestrator/handlers/routing.py` | RoutingHandler uses BusinessIntentRouter |
| `api/v1/orchestration/` | HTTP endpoints for routing, dialog, HITL |
| `api/v1/hybrid/` | Pipeline SSE streaming |

### Configuration

| Env Var | Default | Purpose |
|---|---|---|
| `PATTERN_CONFIDENCE_THRESHOLD` | 0.90 | Layer 1 pattern matcher threshold |
| `SEMANTIC_SIMILARITY_THRESHOLD` | 0.85 | Layer 2 semantic threshold |
| `ENABLE_LLM_FALLBACK` | true | Enable Layer 3 LLM |
| `ENABLE_COMPLETENESS` | true | Enable completeness checking |
| `AZURE_OPENAI_*` | — | Required for LLM classifier |

### Test Coverage

- `tests/unit/integrations/orchestration/` — 15+ test files (router, dialog, gateway, hitl, risk)
- `tests/e2e/orchestration/` — 3 E2E tests (AD scenario, semantic routing)
- `tests/integration/hybrid/test_swarm_routing.py` — Integration with hybrid layer

### Known Issues

- **Semantic Router accuracy**: Vector similarity requires tuning per deployment
- **LLM Classifier latency**: Up to 2s fallback can impact UX
- **Pattern rules**: Hardcoded in YAML; no runtime update mechanism

---

<a id="module-claude_sdk"></a>
## Module: claude_sdk

- **Path**: `backend/src/integrations/claude_sdk/`
- **Files**: 48 `.py` files | **Phase**: 12 (Sprint 48) + Phase 29, 41–42

### Public API

#### ClaudeSDKClient (`client.py`)
```python
class ClaudeSDKClient:
    def __init__(self, config: ClaudeSDKConfig = None)
    async def query(self, prompt: str, **kwargs) -> QueryResult
    async def create_session(self) -> Session
```

#### Session (`session.py`)
```python
class Session:
    async def query(self, prompt: str) -> SessionResponse
    async def close(self) -> None
```

#### Autonomous Engine (`autonomous/engine.py`)
- Full autonomous agent loop with tool use
- Extended thinking support
- Hook chain integration

#### Hook Chain (`hooks/`)
- Approval → Audit → RateLimit → Sandbox
- Each hook implements `HookResult` protocol

#### Tools Registry (`tools/`)
- Tool registration and discovery
- MCP tool integration bridge

#### Orchestrator (`orchestrator/coordinator.py`)
- `ClaudeCoordinator` — Multi-agent coordination for swarm execution
- Callback-driven worker lifecycle

### Dependencies (imports from)

| Dependency | Usage |
|---|---|
| `anthropic` (pip) | `AsyncAnthropic` client for Claude API |
| `claude_sdk/hooks/*` | Hook chain for tool interception |
| `claude_sdk/tools/*` | Tool registry |
| `claude_sdk/mcp/*` | MCP tool bridge |

### Dependents (imported by)

| Consumer | Usage |
|---|---|
| `hybrid/execution/` | Claude execution path in UnifiedToolExecutor |
| `hybrid/claude_maf_fusion.py` | Claude decisions in MAF workflows |
| `swarm/swarm_integration.py` | ClaudeCoordinator callbacks for swarm |
| `api/v1/claude_sdk/` | Direct Claude API endpoints |

### Configuration

| Env Var | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Claude API authentication |
| `CLAUDE_MODEL` | claude-sonnet-4-20250514 | Default model |
| `CLAUDE_MAX_TOKENS` | 4096 | Default max tokens |

### Test Coverage

- `tests/unit/integrations/claude_sdk/` — 18+ test files
- `tests/e2e/` — E2E flow tests via hybrid pipeline

### Known Issues

- **No official Claude Agent SDK package**: Uses `anthropic` pip package directly
- **Autonomous engine**: Complex loop with extended thinking; error recovery paths need hardening

---

<a id="module-mcp"></a>
## Module: mcp

- **Path**: `backend/src/integrations/mcp/`
- **Files**: 43 `.py` files | **Phase**: 9–10 (Sprint 36–40)

### Public API

#### MCPClient (`core/client.py`) — 447 LOC
```python
class MCPClient:
    async def connect(self, config: ServerConfig, transport=None) -> bool
    async def disconnect(self, server_name: str) -> bool
    async def list_tools(self, server_name=None, refresh=False) -> Dict[str, List[ToolSchema]]
    def get_tool_schema(self, server: str, tool: str) -> Optional[ToolSchema]
    async def call_tool(self, server, tool, arguments=None, timeout=None) -> ToolResult
    def is_connected(self, server_name: str) -> bool
    @property connected_servers -> List[str]
    async def close(self) -> None

@dataclass class ServerConfig: name, command, args, env, transport, timeout, cwd
```

#### ServerRegistry (`registry/server_registry.py`) — 595 LOC
- Server registration and lifecycle management
- Health monitoring with periodic checks
- Connection pooling

#### Security (`security/`)
- `PermissionManager` — RBAC with PermissionLevel (NONE, READ, EXECUTE, ADMIN)
- `AuditLogger` — Event logging with InMemory and File backends
- `CommandWhitelist` — Shell command restrictions

### 9 MCP Server Implementations

| Server | Directory | Tools | External SDK |
|---|---|---|---|
| Azure | `servers/azure/` | VM, Resource, Storage, Monitor, Network | azure-identity, azure-mgmt-* |
| Filesystem | `servers/filesystem/` | Read, Write, List, Search | pathlib |
| Shell | `servers/shell/` | Execute, Script | subprocess |
| LDAP | `servers/ldap/` | Search, Bind, Modify | ldap3 |
| SSH | `servers/ssh/` | Connect, Execute, Transfer | paramiko |
| ADF | `servers/adf/` | Pipeline management | azure-mgmt-datafactory |
| D365 | `servers/d365/` | Dynamics 365 integration | — |
| N8N | `servers/n8n/` | Workflow automation | — |

### Dependencies (imports from)

| Dependency | Usage |
|---|---|
| `mcp/core/protocol.py` | MCPProtocol (JSON-RPC 2.0) |
| `mcp/core/transport.py` | StdioTransport, InMemoryTransport |
| `mcp/core/types.py` | ToolSchema, ToolResult, ToolParameter |

### Dependents (imported by)

| Consumer | Usage |
|---|---|
| `claude_sdk/mcp/` | MCP tool bridge for Claude |
| `hybrid/execution/` | Tool execution via MCP servers |
| `api/v1/mcp/` | MCP management API endpoints |

### Configuration

| Env Var | Default | Purpose |
|---|---|---|
| `AZURE_SUBSCRIPTION_ID` | — | Azure server |
| `AZURE_TENANT_ID` | — | Azure authentication |
| `LDAP_SERVER_URL` | — | LDAP server connection |
| `SSH_*` | — | SSH server credentials |

### Test Coverage

- `tests/unit/integrations/mcp/` — 10+ test files (client, protocol, transport, registry, security)
- `tests/integration/mcp/` — MCP server integration tests

### Known Issues

- **Azure server**: Requires full Azure SDK credentials
- **Only stdio transport**: SSE/WebSocket transport not yet implemented
- **InMemoryAuditStorage**: Default in dev; production should use FileAuditStorage

---

<a id="module-ag_ui"></a>
## Module: ag_ui

- **Path**: `backend/src/integrations/ag_ui/`
- **Files**: 27 `.py` files | **Phase**: 15 (Sprint 58–75)

### Public API

#### HybridEventBridge (`bridge.py`)
```python
class HybridEventBridge:
    def __init__(self, *, orchestrator=None, converters=None, config=None)
    def set_orchestrator(self, orchestrator: HybridOrchestratorV2) -> None
    async def stream_events(self, input: RunAgentInput) -> AsyncGenerator[str, None]
    @property swarm_emitter -> Optional[SwarmEventEmitter]

@dataclass class RunAgentInput: prompt, thread_id, run_id, session_id, force_mode, tools, file_ids
@dataclass class BridgeConfig: chunk_size, heartbeat_interval, enable_swarm_events, ...
```

#### Events (`events/`)
11 event types across 6 files:

| File | Events |
|---|---|
| `base.py` | `BaseAGUIEvent`, `RunStartedEvent`, `RunFinishedEvent`, `CustomEvent` |
| `message.py` | `TextMessageStartEvent`, `TextMessageContentEvent`, `TextMessageEndEvent` |
| `tool.py` | `ToolCallStartEvent`, `ToolCallEndEvent` |
| `state.py` | `StateSnapshotEvent` |
| `lifecycle.py` | `RunFinishReason` enum |
| `progress.py` | Progress-related events |

#### ThreadManager (`thread/manager.py`)
- Thread state management
- Redis-backed storage (`thread/redis_storage.py`)
- Thread models and CRUD operations

### Dependencies (imports from)

| Dependency | Usage |
|---|---|
| `ag_ui/converters.py` | EventConverters for result → event transformation |
| `ag_ui/events/*` | All AG-UI event types |
| `hybrid/orchestrator_v2` | HybridOrchestratorV2 (TYPE_CHECKING) |
| `swarm/events` | SwarmEventEmitter (TYPE_CHECKING) |

### Dependents (imported by)

| Consumer | Usage |
|---|---|
| `api/v1/ag_ui/` | SSE streaming endpoints |
| `swarm/events/emitter.py` | Emits AG-UI CustomEvent |
| `hybrid/orchestrator/sse_events.py` | PIPELINE_TO_AGUI_MAP bridging |

### Configuration

| Env Var | Default | Purpose |
|---|---|---|
| `REDIS_HOST` / `REDIS_PORT` | localhost:6379 | Thread storage (Redis backend) |

### Test Coverage

- `tests/unit/integrations/ag_ui/` — 8+ test files
- `tests/e2e/ag_ui/test_full_flow.py` — Full E2E flow test

### Known Issues

- **Heartbeat interval**: 2s default may be aggressive for some deployments
- **Large bridge file**: `bridge.py` handles too many concerns (streaming, swarm, file attachments)

---

<a id="module-swarm"></a>
## Module: swarm

- **Path**: `backend/src/integrations/swarm/`
- **Files**: 8 `.py` files | **Phase**: 29 (Sprint 100–106)

### Public API

#### SwarmTracker (`tracker.py`) — 694 LOC
```python
class SwarmTracker:
    def __init__(self, use_redis=False, redis_client=None, on_swarm_update=None, on_worker_update=None)
    def create_swarm(self, swarm_id, mode: SwarmMode, metadata=None) -> AgentSwarmStatus
    def get_swarm(self, swarm_id: str) -> Optional[AgentSwarmStatus]
    def complete_swarm(self, swarm_id, status=SwarmStatus.COMPLETED) -> AgentSwarmStatus
    def start_worker(self, swarm_id, worker_id, worker_name, worker_type, role, ...) -> WorkerExecution
    def update_worker_progress(self, swarm_id, worker_id, progress, current_task=None) -> WorkerExecution
    def update_worker_status(self, swarm_id, worker_id, status) -> WorkerExecution
    def add_worker_thinking(self, swarm_id, worker_id, content, token_count=None) -> ThinkingContent
    def add_worker_tool_call(self, swarm_id, worker_id, tool_id, tool_name, is_mcp, input_params) -> ToolCallInfo
    def update_tool_call_result(self, swarm_id, worker_id, tool_id, result=None, error=None) -> ToolCallInfo
    def add_worker_message(self, swarm_id, worker_id, role, content) -> WorkerMessage
    def complete_worker(self, swarm_id, worker_id, status=COMPLETED, error=None) -> WorkerExecution
    def list_swarms(self) -> List[AgentSwarmStatus]
    def list_active_swarms(self) -> List[AgentSwarmStatus]
    def delete_swarm(self, swarm_id: str) -> bool

def get_swarm_tracker() -> SwarmTracker  # Singleton
def set_swarm_tracker(tracker: SwarmTracker) -> None
```

#### Models (`models.py`) — 394 LOC

| Enum | Values |
|---|---|
| `WorkerType` | RESEARCH, WRITER, DESIGNER, REVIEWER, COORDINATOR, ANALYST, CODER, TESTER, CUSTOM |
| `WorkerStatus` | PENDING, RUNNING, THINKING, TOOL_CALLING, COMPLETED, FAILED, CANCELLED |
| `SwarmMode` | SEQUENTIAL, PARALLEL, HIERARCHICAL |
| `SwarmStatus` | INITIALIZING, RUNNING, PAUSED, COMPLETED, FAILED |

Key dataclasses: `AgentSwarmStatus`, `WorkerExecution`, `ToolCallInfo`, `ThinkingContent`, `WorkerMessage`

#### 9 SSE Event Types (`events/types.py`)
`swarm_created`, `swarm_status_update`, `swarm_completed`, `worker_started`, `worker_progress`, `worker_thinking`, `worker_tool_call`, `worker_message`, `worker_completed`

### Dependencies (imports from)

| Dependency | Usage |
|---|---|
| `swarm/models` | All data models and enums |
| `ag_ui/events` | CustomEvent for SSE emission |

### Dependents (imported by)

| Consumer | Usage |
|---|---|
| `claude_sdk/orchestrator/` | ClaudeCoordinator triggers swarm callbacks |
| `ag_ui/bridge.py` | SwarmEventEmitter integration |
| `hybrid/orchestrator/mediator.py` | SWARM_WORKER_START / SWARM_PROGRESS events |
| `api/v1/swarm/` | Swarm status + demo endpoints |

### Configuration

| Env Var | Default | Purpose |
|---|---|---|
| `REDIS_HOST` / `REDIS_PORT` | — | Optional Redis persistence for SwarmTracker |

### Test Coverage

- `tests/unit/integrations/hybrid/` — Swarm-related tests in hybrid module
- `tests/e2e/swarm/test_swarm_execution.py` — E2E swarm test

### Known Issues

- **Thread-safe but not async-safe**: Uses `threading.RLock`, not `asyncio.Lock`
- **In-memory default**: No persistence by default; Redis optional
- **Singleton pattern**: `_default_tracker` global — complicates testing

---

<a id="module-llm"></a>
## Module: llm

- **Path**: `backend/src/integrations/llm/`
- **Files**: 5 `.py` files | **Phase**: 1 (Sprint 34)

### Public API

#### LLMServiceProtocol (`protocol.py`) — 234 LOC
```python
@runtime_checkable
class LLMServiceProtocol(Protocol):
    async def generate(self, prompt: str, max_tokens=2000, temperature=0.7, stop=None, **kwargs) -> str
    async def generate_structured(self, prompt: str, output_schema: Dict, max_tokens=2000, temperature=0.3, **kwargs) -> Dict
    async def chat_with_tools(self, messages: List[Dict], tools=None, tool_choice="auto", max_tokens=2048, temperature=0.7, **kwargs) -> Dict

# Exceptions
class LLMServiceError(Exception): ...
class LLMTimeoutError(LLMServiceError): ...
class LLMRateLimitError(LLMServiceError): retry_after
class LLMParseError(LLMServiceError): raw_response
class LLMValidationError(LLMServiceError): expected_schema, actual_output
```

#### LLMServiceFactory (`factory.py`) — 351 LOC
```python
class LLMServiceFactory:
    @classmethod def create(cls, provider=None, use_cache=False, cache_ttl=3600, singleton=True, **kwargs) -> LLMServiceProtocol
    @classmethod def create_mock(cls, responses=None, default_response="...", latency=0.0) -> MockLLMService
    @classmethod def create_for_testing(cls, structured_responses=None) -> MockLLMService
    @classmethod def clear_instances(cls) -> None
```

**Provider detection logic**: Azure OpenAI (env vars) → Mock (TESTING=true) → RuntimeError (production) → Mock with warning (development)

#### Implementations
- `AzureOpenAILLMService` (`azure_openai.py`) — Production Azure OpenAI
- `MockLLMService` (`mock.py`) — Testing with configurable responses
- `CachedLLMService` (`cached.py`) — Redis-backed cache wrapper

### Dependencies (imports from)

| Dependency | Usage |
|---|---|
| `openai` (pip) | Azure OpenAI SDK |
| `redis` (pip) | Optional caching |
| `src.core.config` | Settings for Azure endpoint detection |

### Dependents (imported by)

| Consumer | Usage |
|---|---|
| `orchestration/intent_router/router.py` | `create_router_with_llm()` uses `LLMServiceFactory.create()` |
| `orchestration/intent_router/llm_classifier.py` | LLM classifier uses `LLMServiceProtocol` |
| `hybrid/orchestrator/handlers/agent.py` | AgentHandler uses LLM for response generation |
| `domain/` | Various domain services for LLM calls |

### Configuration

| Env Var | Default | Purpose |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | — | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | — | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | gpt-5.2 | Model deployment name |
| `AZURE_OPENAI_API_VERSION` | 2024-02-01 | API version |
| `REDIS_HOST` / `REDIS_PORT` | — | Optional cache backend |
| `TESTING` / `LLM_MOCK` | false | Force mock mode |
| `APP_ENV` | development | Environment detection |

### Test Coverage

- `tests/unit/integrations/llm/` — Unit tests for protocol, factory, mock
- `tests/e2e/test_llm_integration.py` — E2E LLM integration test

### Known Issues

- **Silent mock fallback**: Development env gets mock service with only a WARNING log
- **Singleton caching**: `_instances` dict never cleared automatically (memory leak potential)
- **No streaming support**: Protocol lacks streaming/SSE generation method

---

<a id="module-knowledge"></a>
## Module: knowledge

- **Path**: `backend/src/integrations/knowledge/`
- **Files**: 8 `.py` files | **Phase**: 38 (Sprint 118)

### Public API

#### RAGPipeline (`rag_pipeline.py`) — 230 LOC
```python
class RAGPipeline:
    def __init__(self, chunk_size=1000, chunk_overlap=200, collection="knowledge_base")
    # Ingestion
    async def ingest_file(self, file_path: str, metadata=None) -> Dict[str, Any]
    async def ingest_text(self, text: str, title="inline", metadata=None) -> Dict[str, Any]
    # Retrieval
    async def retrieve(self, query: str, limit=5, collection=None) -> List[RetrievalResult]
    async def retrieve_and_format(self, query: str, limit=5) -> str  # For LLM injection
    # Tool handler
    async def handle_search_knowledge(self, query, collection=None, limit=5) -> Dict[str, Any]
    # Collection management
    async def get_collection_info(self) -> Dict[str, Any]
    async def delete_collection(self) -> bool
```

#### VectorStoreManager (`vector_store.py`) — 178 LOC
```python
class VectorStoreManager:
    def __init__(self, collection_name="knowledge_base", qdrant_path="./qdrant_data")
    async def initialize(self, dimension=3072) -> None
    async def index_documents(self, documents: List[IndexedDocument], collection=None) -> int
    async def search(self, query_embedding, limit=5, collection=None, score_threshold=0.0) -> List[IndexedDocument]
    async def delete_collection(self, collection=None) -> bool
    async def get_collection_info(self, collection=None) -> Dict[str, Any]

@dataclass class IndexedDocument: doc_id, content, embedding, metadata, score
```

#### Internal Components
- `DocumentParser` — File parsing (PDF, Markdown, text)
- `DocumentChunker` — Recursive text splitting with overlap
- `EmbeddingManager` — Embedding generation (Azure OpenAI)
- `KnowledgeRetriever` — Retrieve + rerank

### Dependencies (imports from)

| Dependency | Usage |
|---|---|
| `qdrant_client` (pip) | Vector database (local mode) |
| `knowledge/document_parser` | File parsing |
| `knowledge/chunker` | Text chunking |
| `knowledge/embedder` | Embedding generation |
| `knowledge/retriever` | Retrieval with reranking |

### Dependents (imported by)

| Consumer | Usage |
|---|---|
| `hybrid/orchestrator/handlers/agent.py` | `search_knowledge` tool handler |
| `api/v1/knowledge/` | Knowledge base management endpoints |

### Configuration

| Env Var | Default | Purpose |
|---|---|---|
| `QDRANT_PATH` | `./qdrant_data` | Local Qdrant storage path |
| `AZURE_OPENAI_*` | — | Embedding model access |

### Test Coverage

- No dedicated test directory found; likely covered by integration tests

### Known Issues

- **Local Qdrant only**: No remote Qdrant server support
- **In-memory fallback**: Falls back to list storage when `qdrant_client` not installed (no similarity)
- **Embedding dimension hardcoded**: 3072 default assumes specific model

---

<a id="module-memory"></a>
## Module: memory

- **Path**: `backend/src/integrations/memory/`
- **Files**: 4 `.py` files | **Phase**: 22 (Sprint 79)

### Public API

#### UnifiedMemoryManager (`unified_memory.py`) — 686 LOC
```python
class UnifiedMemoryManager:
    def __init__(self, config: Optional[MemoryConfig] = None)
    async def initialize(self) -> None
    async def add(self, content, user_id, memory_type=CONVERSATION, metadata=None, layer=None) -> MemoryRecord
    async def search(self, query, user_id, memory_types=None, layers=None, min_importance=0.0, limit=10) -> List[MemorySearchResult]
    async def get_context(self, user_id, session_id=None, query=None, limit=10) -> List[MemoryRecord]
    async def promote(self, memory_id, user_id, from_layer, to_layer) -> Optional[MemoryRecord]
    async def delete(self, memory_id, user_id, layer=None) -> bool
    async def get_user_memories(self, user_id, memory_types=None, layers=None) -> List[MemoryRecord]
    async def close(self) -> None
```

**3-Layer Architecture**:

| Layer | Backend | TTL | Purpose |
|---|---|---|---|
| Working Memory | Redis | 30 min | Short-term context |
| Session Memory | Redis/PostgreSQL | 7 days | Medium-term persistence |
| Long-term Memory | mem0 + Qdrant | Permanent | Semantic storage |

#### Mem0Client (`mem0_client.py`)
```python
class Mem0Client:
    def __init__(self, config=None)
    async def initialize(self) -> None
    async def add_memory(self, content, user_id, memory_type, metadata) -> MemoryRecord
    async def search_memory(self, query: MemorySearchQuery) -> List[MemorySearchResult]
    async def get_all(self, user_id, memory_types=None) -> List[MemoryRecord]
    async def get_memory(self, memory_id) -> Optional[MemoryRecord]
    async def update_memory(self, memory_id, content) -> Optional[MemoryRecord]
    async def delete_memory(self, memory_id) -> bool
    async def close(self) -> None
```

#### Types (`types.py`)
```python
class MemoryLayer(Enum): WORKING, SESSION, LONG_TERM
class MemoryType(Enum): CONVERSATION, EVENT_RESOLUTION, BEST_PRACTICE, SYSTEM_KNOWLEDGE, USER_PREFERENCE, FEEDBACK
@dataclass class MemoryConfig: working_memory_ttl, session_memory_ttl, embedding_provider, embedding_model, llm_provider, ...
@dataclass class MemoryRecord: id, user_id, content, memory_type, layer, metadata, created_at, ...
@dataclass class MemorySearchResult: memory, score
```

### Dependencies (imports from)

| Dependency | Usage |
|---|---|
| `mem0` (pip) | Long-term memory SDK |
| `qdrant_client` (pip) | Vector storage for mem0 |
| `redis.asyncio` (pip) | Working + session memory |
| `memory/embeddings` | EmbeddingService for similarity search |
| `memory/types` | All data models |

### Dependents (imported by)

| Consumer | Usage |
|---|---|
| `hybrid/orchestrator/mediator.py` | Phase 41: `_write_to_longterm()` after execution |
| `api/v1/memory/` | Memory management endpoints |

### Configuration

| Env Var | Default | Purpose |
|---|---|---|
| `MEM0_ENABLED` | false | Enable mem0 integration |
| `QDRANT_PATH` | `./qdrant_data` | Local Qdrant storage |
| `REDIS_HOST` / `REDIS_PORT` | localhost:6379 | Working + session memory |
| `AZURE_OPENAI_*` | — | Embedding model for mem0 |
| `ANTHROPIC_API_KEY` | — | LLM for memory extraction (mem0) |

### Test Coverage

- No dedicated test directory found in scan

### Known Issues

- **Session memory uses Redis**: Not PostgreSQL as designed; Redis acts as cache for both Working + Session layers
- **mem0 configuration complexity**: Requires both Azure OpenAI (embeddings) and Anthropic (extraction)
- **No automatic promotion**: Memory promotion from Working → Session → Long-term is manual only

---

## Cross-Module Dependency Graph

```
                         ┌──────────┐
                         │   llm/   │  <── orchestration, hybrid, domain
                         └────┬─────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
   ┌──────────▼──────┐ ┌─────▼─────┐ ┌───────▼──────┐
   │ agent_framework/ │ │ claude_sdk │ │ orchestration│
   │ (MAF Adapters)   │ │ (Claude)  │ │ (3-tier Rtr) │
   └────────┬─────────┘ └─────┬─────┘ └──────┬───────┘
            │                 │               │
            └────────┬────────┘               │
                     │                        │
              ┌──────▼──────┐                 │
              │   hybrid/   │ ←───────────────┘
              │ (Mediator)  │
              └──────┬──────┘
                     │
         ┌───────────┼───────────┬────────────┐
         │           │           │            │
    ┌────▼───┐ ┌─────▼────┐ ┌───▼────┐ ┌─────▼─────┐
    │  mcp/  │ │  swarm/  │ │ ag_ui/ │ │ knowledge/ │
    │(Tools) │ │(Workers) │ │ (SSE)  │ │   (RAG)   │
    └────────┘ └──────────┘ └────────┘ └───────────┘
                                              │
                                        ┌─────▼─────┐
                                        │  memory/  │
                                        │ (3-layer) │
                                        └───────────┘
```

## Summary Statistics

| Module | Files | Key Classes | Phases | Test Files |
|---|---|---|---|---|
| hybrid/ | 89 | OrchestratorMediator, ContextBridge, RiskAssessmentEngine | 13–42 | 34+ |
| agent_framework/ | 57 | 12 Builder Adapters, 5 Migration Layers | 1–37 | 20+ |
| orchestration/ | 39 | BusinessIntentRouter, GuidedDialogEngine, HITLController | 28 | 18+ |
| claude_sdk/ | 48 | ClaudeSDKClient, Session, AutonomousEngine | 12, 29, 41 | 18+ |
| mcp/ | 43 | MCPClient, ServerRegistry, PermissionManager | 9–10 | 10+ |
| ag_ui/ | 27 | HybridEventBridge, 11 Event Types, ThreadManager | 15 | 9+ |
| swarm/ | 8 | SwarmTracker, 9 SSE Event Types | 29 | 3+ |
| llm/ | 5 | LLMServiceProtocol, LLMServiceFactory | 1 | 3+ |
| knowledge/ | 8 | RAGPipeline, VectorStoreManager | 38 | 0 |
| memory/ | 4 | UnifiedMemoryManager, Mem0Client | 22 | 0 |
| **Total** | **328** | — | — | **115+** |
