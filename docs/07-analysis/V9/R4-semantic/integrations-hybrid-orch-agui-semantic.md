# Round 4 Semantic Analysis: hybrid/ + orchestration/ + ag_ui/

> Generated: 2026-03-29 | Source: Full file reads of all .py files (excluding __init__.py)
> Modules analyzed: 3 | Total source files: ~130 | Estimated LOC: ~50,000

---

## Module 1: `integrations/hybrid/` (~85 files, ~24K LOC)

### 1.1 intent/ — Framework Selection (8 files, ~1,500 LOC)

| File | LOC | Summary |
|------|-----|---------|
| `intent/models.py` | 224 | Core data models: `ExecutionMode` (WORKFLOW/CHAT/HYBRID/SWARM), `IntentAnalysis` (mode + confidence + reasoning), `SessionContext`, `ClassificationResult`, `ComplexityScore`, `MultiAgentAnalysis`. Sprint 98 adds `FrameworkAnalysis` alias for backward compat. |
| `intent/router.py` | 501 | `FrameworkSelector` (renamed from IntentRouter in S98): runs multiple classifiers, aggregates via weighted voting, determines execution mode. Sprint 144 injects `RoutingDecisionClassifier` from Phase 28 three-tier routing. Also aliased as `IntentRouter`. |
| `intent/classifiers/base.py` | 99 | `BaseClassifier` ABC with `classify(input_text, context, history) -> ClassificationResult`. Supports name, weight, enabled flags. |
| `intent/classifiers/rule_based.py` | 468 | `RuleBasedClassifier`: keyword + regex pattern matching for EN + zh-TW. 50+ workflow keywords, 20+ chat keywords, 18+ workflow phrase patterns. Context boost for active workflows. |
| `intent/classifiers/routing_decision.py` | 185 | `RoutingDecisionClassifier` (Sprint 144): bridges Phase 28 `RoutingDecision` to `ExecutionMode`. Maps QUERY->CHAT, REQUEST/CHANGE->WORKFLOW, INCIDENT+CRITICAL->SWARM. Weight 1.5 (higher than rule-based). |
| `intent/analyzers/complexity.py` | 428 | `ComplexityAnalyzer`: heuristic complexity scoring via step indicators, dependency indicators, persistence needs, time requirements. Bilingual keywords (EN + zh-TW). Returns `ComplexityScore` with step count estimate. |
| `intent/analyzers/multi_agent.py` | 567 | `MultiAgentDetector`: detects multi-agent collaboration needs via keyword matching, skill domain detection (8 domains), role references, collaboration pattern regex. Returns `MultiAgentSignal` with agent count estimate and collaboration type. |

### 1.2 context/ — Cross-Framework Context Bridge (9 files, ~3,100 LOC)

| File | LOC | Summary |
|------|-----|---------|
| `context/models.py` | 590 | Rich data model layer: `MAFContext` (workflow state, checkpoints, agent states), `ClaudeContext` (session history, tool calls, context vars), `HybridContext` (merged view with sync status + version). Supporting types: `AgentState`, `ApprovalRequest`, `ExecutionRecord`, `Message`, `ToolCall`. 7 enums for sync/agent/approval/message/tool states. |
| `context/bridge.py` | 933 | `ContextBridge`: main bidirectional sync class. `sync_to_claude()` maps checkpoint_data->context_variables, execution_history->conversation, agent_states->system_prompt. `sync_to_maf()` reverses. `merge_contexts()` creates `HybridContext`. Uses Protocol-based DI for mappers and synchronizer. Includes `sync_after_execution()` for post-execution state updates. |
| `context/mappers/base.py` | 332 | `BaseMapper[T,U]` generic ABC with utility methods: `_safe_get()`, `_safe_map_list()`, `_truncate_string()`, `_parse_datetime()`, `_merge_dicts()`, `_prefix_keys()`. `MappingError` exception with source/target/field tracking. |
| `context/mappers/claude_mapper.py` | 467 | `ClaudeMapper`: Claude->MAF direction. `to_maf_checkpoint()` strips `claude_` prefix from context vars. `to_execution_records()` converts assistant messages to `ExecutionRecord`. `tool_call_to_approval_request()` for HITL bridge. |
| `context/mappers/maf_mapper.py` | 416 | `MAFMapper`: MAF->Claude direction. `to_claude_context_vars()` adds `maf_` prefix. `to_claude_history()` converts execution records to messages. `agent_state_to_system_prompt()` generates markdown agent context. |
| `context/sync/synchronizer.py` | 693 | `ContextSynchronizer` (Sprint 119 unified): Redis distributed lock with asyncio.Lock fallback. Sync lifecycle with retry logic (max 3), version tracking, rollback snapshots (max 5). Factory method `create()` for production use. `_state_lock` (asyncio.Lock) protects in-memory state even outside distributed lock. |
| `context/sync/conflict.py` | 498 | `ConflictResolver`: detects version mismatches and value divergence. 6 resolution strategies (SOURCE_WINS, TARGET_WINS, MAF_PRIMARY, CLAUDE_PRIMARY, MERGE, MANUAL). Intelligent merge: uses more recent MAF state and longer Claude history. |
| `context/sync/events.py` | 443 | `SyncEventPublisher`: async pub/sub for 10 sync event types (SYNC_STARTED/COMPLETED/FAILED, CONFLICT_DETECTED/RESOLVED, ROLLBACK_STARTED/COMPLETED, VERSION_UPDATED). Supports filtered subscriptions and event history (max 100). |

### 1.3 execution/ — Unified Tool Execution (5 files, ~2,200 LOC)

| File | LOC | Summary |
|------|-----|---------|
| `execution/unified_executor.py` | 797 | `UnifiedToolExecutor`: central tool execution with 8-step flow (context lookup, pre-hooks, approval check, execute, post-hooks, sync, metrics, log). Protocol-based DI for registry, hooks, context bridge, metrics, approval. `_ToolCallContextAdapter`/`_ToolResultContextAdapter` for hook compatibility. |
| `execution/tool_router.py` | 431 | `ToolRouter`: intelligent routing with 5 strategies (PREFER_CLAUDE, PREFER_MAF, CAPABILITY_BASED, LOAD_BALANCED, EXPLICIT). Rule-based routing with pattern matching (fnmatch). Tracks call counts per source. Factory `create_default_router()` with 4 default rules. |
| `execution/result_handler.py` | 492 | `ResultHandler`: transforms `ToolExecutionResult` to Claude/MAF/Unified/JSON formats via pluggable `ResultTransformer` protocol. LRU result cache (max 1000). Batch processing and aggregation. Statistics tracking (total, success, failed, blocked, by source). |
| `execution/tool_callback.py` | 515 | `MAFToolCallback`: intercepts MAF tool calls and routes through `UnifiedToolExecutor`. Configurable interception (all/allowlist/blocklist). Fallback to original handler on error. History tracking (max 1000 entries). Factory functions for common configs. |

### 1.4 risk/ — Risk Assessment Engine (7 files, ~2,400 LOC)

| File | LOC | Summary |
|------|-----|---------|
| `risk/models.py` | 303 | Core risk types: `RiskLevel` (LOW/MEDIUM/HIGH/CRITICAL with comparison), `RiskFactorType` (9 categories: OPERATION/CONTEXT/PATTERN/PATH/COMMAND/FREQUENCY/ESCALATION/USER/ENVIRONMENT), `RiskFactor` (score + weight + description), `RiskAssessment` (overall level + factors + approval requirement), `RiskConfig` (thresholds + weights + auto-approve settings), `OperationContext` (tool + paths + command + environment). |
| `risk/engine.py` | 561 | `RiskAssessmentEngine`: coordinates multiple analyzers, produces comprehensive assessments. Dangerous command bypass for environment multiplier (minimum HIGH threshold). History-based pattern detection (frequency + escalation). Lifecycle hooks (pre_assess, post_assess, on_high_risk). Batch assessment with cumulative risk. |
| `risk/scoring/scorer.py` | 312 | `RiskScorer`: 3 scoring strategies (WEIGHTED_AVERAGE, MAX_WEIGHTED, HYBRID=70%avg+30%max). Context adjustment for environment (dev=0.8x, prod=1.3x) and user trust. Session risk aggregation with recency weighting and escalation detection. |
| `risk/analyzers/operation_analyzer.py` | 430 | `OperationAnalyzer`: tool base risk matrix (Read=0.1, Bash=0.6), sensitive path detection (19 patterns including .env, SSH keys, system dirs), dangerous command detection (20+ patterns), critical command detection (5 patterns). Configurable scores and weights. |
| `risk/analyzers/context_evaluator.py` | 449 | `ContextEvaluator`: user trust levels (NEW/LOW/MEDIUM/HIGH/TRUSTED) with risk multipliers (1.3x-0.7x). Environment risk (dev=0.15, prod=0.5 base). Session context analysis (high-risk count, rejection rate). Trust level evolution based on operation history. |
| `risk/analyzers/pattern_detector.py` | 480 | `PatternDetector`: 5 pattern types (frequency anomaly, behavior deviation, risk escalation, temporal anomaly, tool sequence). Burst detection (5 ops in 5s). Off-hours detection (22:00-06:00). Suspicious tool sequences (Grep->Read->Write). Per-user behavior baselines. |

### 1.5 switching/ — Dynamic Mode Switching (10 files, ~2,900 LOC)

| File | LOC | Summary |
|------|-----|---------|
| `switching/models.py` | 657 | Rich model hierarchy: `SwitchTriggerType` (6 types), `SwitchStatus` (5 states), `MigrationDirection` (6 paths), `SwitchTrigger`, `MigratedState`, `SwitchValidation`, `SwitchCheckpoint`, `SwitchResult`, `ModeTransition`, `ExecutionState`, `SwitchConfig`. Full serialization support. |
| `switching/switcher.py` | 837 | `ModeSwitcher`: core mode switching with trigger detection, checkpoint creation, state migration, validation, rollback. `InMemoryCheckpointStorage` default with warning. `SwitcherMetrics` tracks success rate and timing. Factory `create_mode_switcher()`. |
| `switching/redis_checkpoint.py` | 263 | `RedisSwitchCheckpointStorage` (Sprint 120): Redis-backed checkpoint persistence with TTL (24h default). Per-session index via Redis Sets. Stale index cleanup on list operations. |
| `switching/migration/state_migrator.py` | 595 | `StateMigrator`: workflow->chat (execution records to conversation history + summary), chat->workflow (intent extraction + workflow state), hybrid (preserve all). `MigrationValidator` for pre/post validation. `MigrationConfig` controls history limits and inclusion options. |
| `switching/triggers/base.py` | 198 | `BaseTriggerDetector` ABC with config (enabled, priority, min_confidence, cooldown). `_create_trigger()` helper. Subclasses set `trigger_type`. |
| `switching/triggers/user.py` | 233 | `UserRequestTriggerDetector` (priority 1): detects `/mode workflow` commands and implicit phrases ("switch to chat", "use workflow mode"). Bilingual patterns. Confidence: 1.0 explicit, 0.85 implicit. |
| `switching/triggers/failure.py` | 221 | `FailureTriggerDetector` (priority 10): monitors consecutive failures (threshold 3). Error keyword detection in user input. Confidence scales with extra failures (+0.1 each). Switches to opposite mode for recovery. |
| `switching/triggers/resource.py` | 241 | `ResourceTriggerDetector` (priority 50): monitors token/memory/context usage thresholds (0.8/0.85/0.75). High chat resource->workflow for efficiency, high workflow memory->chat for simplification. |
| `switching/triggers/complexity.py` | 327 | `ComplexityTriggerDetector`: keyword-based complexity scoring. Multi-step + workflow keywords boost score; chat keywords reduce. Threshold: >=0.7 -> switch to workflow, <=0.3 + chat keywords -> switch to chat. |

### 1.6 checkpoint/ — State Persistence (8 files, ~4,300 LOC)

| File | LOC | Summary |
|------|-----|---------|
| `checkpoint/models.py` | 654 | `HybridCheckpoint` unified structure: MAFCheckpointState + ClaudeCheckpointState + RiskSnapshot. Supports compression (NONE/ZLIB/GZIP/LZ4), version control (v2 current), TTL expiration, integrity checksum. `RestoreResult` with partial restore support. |
| `checkpoint/storage.py` | ~200+ | `UnifiedCheckpointStorage` ABC: save/load/delete/query/cleanup. `StorageConfig` with backend selection, TTL, compression toggle. `CheckpointQuery` for filtered retrieval. |
| `checkpoint/serialization.py` | ~200+ | `CheckpointSerializer`: JSON serialization with zlib/gzip compression. Checksum generation and validation. Size-based compression threshold (1KB default). |
| `checkpoint/version.py` | ~200+ | `CheckpointVersionMigrator`: forward migration from v1 (separate checkpoints) to v2 (unified). Version detection and auto-migration. |
| `checkpoint/backends/memory.py` | ~200+ | `MemoryCheckpointStorage`: in-memory dict with threading Lock. TTL-based expiration. For dev/test only. |
| `checkpoint/backends/redis.py` | ~200+ | `RedisCheckpointStorage`: Redis with sorted sets for session indexing. Automatic TTL expiration. Atomic operations. |
| `checkpoint/backends/postgres.py` | ~200+ | `PostgresCheckpointStorage`: SQLAlchemy async with BYTEA for compressed data. Full SQL query support. Index on session_id and created_at. |
| `checkpoint/backends/filesystem.py` | ~200+ | `FilesystemCheckpointStorage`: JSON files organized by session directory. No external dependencies. |

### 1.7 hooks/ — HITL Approval (2 files, ~450 LOC)

| File | LOC | Summary |
|------|-----|---------|
| `hooks/approval_hook.py` | 440 | `RiskDrivenApprovalHook`: integrates RiskAssessmentEngine with 3 approval modes (AUTO/MANUAL/RISK_DRIVEN). Registers all 3 analyzers (OperationAnalyzer, ContextEvaluator, PatternDetector). Auto-approve for read-only tools (Read, Glob, Grep). Session-scoped approval caching. `from_tool_call_context()` helper for Claude SDK integration. |

### 1.8 orchestrator/ — Mediator Pipeline (18 files, ~5,500 LOC)

| File | LOC | Summary |
|------|-----|---------|
| `orchestrator/mediator.py` | ~845 | `OrchestratorMediator`: central coordinator with 9-step pipeline. Session management (in-memory + ConversationStateStore). HITL approval via asyncio.Event (120s timeout). Checkpoint resume support. SSE streaming via PipelineEventEmitter. |
| `orchestrator/bootstrap.py` | ~512 | `OrchestratorBootstrap`: DI factory wiring all 7 handlers with graceful degradation. Creates LLM service, tool registry, and MCP tool bridge. |
| `orchestrator/contracts.py` | ~133 | `HandlerType` (7 values), `Handler` ABC, `OrchestratorRequest`, `HandlerResult` (with short-circuit), `OrchestratorResponse`. |
| `orchestrator/events.py` | ~100 | `EventType` (17 pipeline events), `OrchestratorEvent`, `RoutingEvent`, `DialogEvent`, `ApprovalEvent`. Sprint 135 adds streaming events. |
| `orchestrator/agent_handler.py` | ~426 | `AgentHandler`: LLM decision engine with function calling loop (max 5 iterations). Uses `OrchestratorToolRegistry`. Short-circuits for CHAT_MODE. |
| `orchestrator/tools.py` | ~200+ | `OrchestratorToolRegistry`: tool definitions (SYNC/ASYNC types), execution dispatch. 8+ tools: dispatch_workflow, dispatch_swarm, create_task, assess_risk, search_memory, request_approval. |
| `orchestrator/dispatch_handlers.py` | ~200+ | `DispatchHandlers`: real implementations connecting to platform services (TaskService, RiskAssessmentEngine, SwarmIntegration, ClaudeCoordinator, MAF WorkflowExecutor). Sprint 136 adds ARQ background execution. |
| `orchestrator/mcp_tool_bridge.py` | ~100+ | `MCPToolBridge`: dynamic MCP tool discovery from ServerRegistry into OrchestratorToolRegistry. |
| `orchestrator/sse_events.py` | ~158 | `SSEEventType` (14 types), `PipelineEventEmitter`. PIPELINE_TO_AGUI_MAP bridges pipeline events to AG-UI protocol. |
| `orchestrator/session_factory.py` | ~100+ | `OrchestratorSessionFactory`: per-session mediator instances with LRU eviction (max 100). Uses OrchestratorBootstrap for full wiring. |
| `orchestrator/memory_manager.py` | ~100+ | `OrchestratorMemoryManager`: auto-summarize conversations for mem0 long-term memory. Auto-retrieve relevant memories for context injection. |
| `orchestrator/task_result_protocol.py` | ~100+ | `TaskResultEnvelope`: unified result format for MAF/Claude/Swarm workers. `TaskResultNormaliser` for format conversion. |
| `orchestrator/result_synthesiser.py` | ~100+ | `ResultSynthesiser`: LLM-powered aggregation of multi-worker results into coherent user response. |
| `orchestrator/session_recovery.py` | ~100+ | Session recovery from checkpoint storage. |
| `orchestrator/observability_bridge.py` | ~100+ | Bridge to OpenTelemetry metrics. |
| `orchestrator/e2e_validator.py` | ~100+ | End-to-end pipeline validation. |
| `orchestrator/handlers/routing.py` | ~227 | `RoutingHandler`: 3-tier routing + FrameworkSelector integration. |
| `orchestrator/handlers/execution.py` | ~459 | `ExecutionHandler`: dispatches to MAF/Claude/Hybrid/Swarm with parallel swarm execution (semaphore=3). |
| `orchestrator/handlers/dialog.py` | ~121 | `DialogHandler`: GuidedDialogEngine integration, short-circuits if needs_more_info. |
| `orchestrator/handlers/approval.py` | ~137 | `ApprovalHandler`: RiskAssessor + HITLController, short-circuits if pending/rejected. |
| `orchestrator/handlers/context.py` | ~131 | `ContextHandler`: ContextBridge + MemoryManager for context prep and post-sync. |
| `orchestrator/handlers/observability.py` | ~91 | `ObservabilityHandler`: metrics recording. |

### 1.9 Top-Level Files (3 files, ~2,300 LOC)

| File | LOC | Summary |
|------|-----|---------|
| `orchestrator_v2.py` | ~1,254 | `HybridOrchestratorV2`: DEPRECATED God Object. Imports all Phase 13+28 components. `OrchestratorMode` enum. `execute_with_routing()` integrates InputGateway, BusinessIntentRouter, GuidedDialogEngine, RiskAssessor, HITLController. Sprint 116 adds SwarmModeHandler integration. |
| `claude_maf_fusion.py` | ~892 | `ClaudeMAFFusion` (Sprint 81): Claude decisions in MAF workflows. `ClaudeDecisionEngine` makes route/skip/abort/continue decisions at workflow decision points. `WorkflowDefinition` with step-based execution. |
| `swarm_mode.py` | ~400+ | `SwarmModeHandler` (Sprint 116): Swarm execution integration. `SwarmExecutionConfig` from environment variables. `SwarmTaskDecomposition` for breaking tasks into sub-tasks. |

### 1.10 prompts/ (1 file)

| File | LOC | Summary |
|------|-----|---------|
| `prompts/orchestrator.py` | ~200 | `ORCHESTRATOR_SYSTEM_PROMPT`: Traditional Chinese system prompt for the Orchestrator Agent defining its role, capabilities, and tool usage instructions. |

---

## Module 2: `integrations/orchestration/` (~55 files, ~16K LOC)

### 2.1 intent_router/ — Three-Tier Routing (14+ files, ~3,815 LOC)

| File | LOC | Summary |
|------|-----|---------|
| `intent_router/router.py` | 623 | `BusinessIntentRouter`: 3-layer cascade coordinator. `RouterConfig` from env vars. `RoutingMetrics` with rolling window. Pattern(>=0.90)->Semantic(>=0.85)->LLM fallback. Workflow type and risk level inference. Factory functions `create_router()`, `create_router_with_llm()`. |
| `intent_router/models.py` | 450 | Core enums: `ITIntentCategory` (INCIDENT/REQUEST/CHANGE/QUERY/UNKNOWN), `RiskLevel` (CRITICAL/HIGH/MEDIUM/LOW), `WorkflowType` (MAGENTIC/HANDOFF/CONCURRENT/SEQUENTIAL/SIMPLE). Data classes: `RoutingDecision`, `PatternMatchResult`, `SemanticRouteResult`, `LLMClassificationResult`, `CompletenessInfo`. |
| `intent_router/contracts.py` | ~100 | `RoutingLayerProtocol` ABC for individual routing layers. `LayerExecutionMetric` and `RoutingPipelineResult` for pipeline tracing. |
| `intent_router/pattern_matcher/matcher.py` | 411 | `PatternMatcher`: YAML-loaded regex rules, priority-sorted, pre-compiled. Confidence formula: 0.95 * (0.70 + coverage + priority + position). Dynamic rule CRUD. |
| `intent_router/semantic_router/router.py` | ~350 | `SemanticRouter`: vector similarity via Aurelio library or Azure AI Search. Similarity threshold >= 0.85. |
| `intent_router/semantic_router/routes.py` | 373 | 15 predefined routes with 75 Traditional Chinese utterances covering 4 ITIL categories. |
| `intent_router/semantic_router/azure_semantic_router.py` | ~300 | Azure AI Search backed semantic router (Sprint 116). |
| `intent_router/semantic_router/azure_search_client.py` | ~200 | Azure AI Search client wrapper. |
| `intent_router/semantic_router/embedding_service.py` | ~150 | Embedding generation service for semantic routing. |
| `intent_router/semantic_router/setup_index.py` | ~100 | Azure AI Search index setup script. |
| `intent_router/semantic_router/migration.py` | ~100 | Migration utilities between Aurelio and Azure backends. |
| `intent_router/semantic_router/route_manager.py` | ~200 | Route CRUD management. |
| `intent_router/llm_classifier/classifier.py` | 294 | `LLMClassifier`: uses `LLMServiceProtocol`, 0.0 temperature. Graceful degradation returns UNKNOWN. Sprint 128 migration from direct OpenAI to protocol. |
| `intent_router/llm_classifier/prompts.py` | 231 | Multi-task classification prompt in Traditional Chinese. Required fields per intent category. |
| `intent_router/llm_classifier/cache.py` | ~150 | `ClassificationCache` for LLM result caching. |
| `intent_router/llm_classifier/evaluation.py` | ~200 | Classification quality evaluation metrics. |
| `intent_router/completeness/checker.py` | ~250 | `CompletenessChecker`: field validation per intent category. |
| `intent_router/completeness/rules.py` | ~200 | Completeness field requirement rules per ITIL category. |

### 2.2 guided_dialog/ — Multi-Turn Dialog (4 files, ~3,530 LOC)

| File | LOC | Summary |
|------|-----|---------|
| `guided_dialog/engine.py` | 548 | `GuidedDialogEngine`: multi-turn orchestration (max 5 turns). Phases: initial->gathering->complete->handoff. Integrates BusinessIntentRouter, ConversationContextManager, QuestionGenerator, RefinementRules. |
| `guided_dialog/context_manager.py` | 1,102 | `ConversationContextManager` + `PersistentConversationContextManager` (Redis). Dialog state tracking with turn history. `RedisDialogSessionStorage` + `InMemoryDialogSessionStorage`. |
| `guided_dialog/generator.py` | ~1,151 | `QuestionGenerator`: template-based question generation per intent category. Generates follow-up questions based on missing fields. |
| `guided_dialog/refinement_rules.py` | ~622 | `RefinementRules`: rule-based sub-intent refinement. Keyword-to-sub-intent mapping per category. NEVER uses LLM re-classification. |

### 2.3 input_gateway/ — Source-Aware Routing (8 files, ~2,302 LOC)

| File | LOC | Summary |
|------|-----|---------|
| `input_gateway/gateway.py` | 370 | `InputGateway`: source detection via HTTP headers, handler dispatch. System sources (ServiceNow/Prometheus) use simplified handlers, user input gets full 3-layer routing. |
| `input_gateway/models.py` | 278 | `IncomingRequest` with factory methods (from_user_input, from_servicenow_webhook, from_prometheus_webhook). `SourceType` enum. `GatewayConfig` and `GatewayMetrics`. |
| `input_gateway/schema_validator.py` | ~200 | JSON schema validation for webhook payloads. |
| `input_gateway/source_handlers/base_handler.py` | ~100 | `BaseSourceHandler` abstract class. |
| `input_gateway/source_handlers/servicenow_handler.py` | ~300 | ServiceNow RITM/INC ticket field mapping to `RoutingDecision`. |
| `input_gateway/source_handlers/prometheus_handler.py` | ~250 | Prometheus alert mapping to INCIDENT `RoutingDecision`. |
| `input_gateway/source_handlers/user_input_handler.py` | ~200 | User text routing through full BusinessIntentRouter pipeline. |

### 2.4 risk_assessor/ (3 files, ~1,350 LOC)

| File | LOC | Summary |
|------|-----|---------|
| `risk_assessor/assessor.py` | 639 | `RiskAssessor`: 7 risk dimensions (impact, urgency, category, scope, system, environment, keyword). Context-aware scoring with `AssessmentContext`. Factory functions for common configurations. |
| `risk_assessor/policies.py` | 712 | `RiskPolicies`: 26 ITIL-aligned risk policies. Per-intent scoring rules. Factory functions for default and custom policy sets. |

### 2.5 hitl/ — Human-in-the-Loop (5 files, ~2,800 LOC)

| File | LOC | Summary |
|------|-----|---------|
| `hitl/controller.py` | 834 | `HITLController`: approval lifecycle (PENDING/APPROVED/REJECTED/EXPIRED/CANCELLED). `InMemoryApprovalStorage` with Redis factory. Quorum-based multi-approver support. Timeout handling. |
| `hitl/approval_handler.py` | 694 | `ApprovalHandler` + `RedisApprovalStorage`: persistent approval with TTL. CRUD operations for approval records. |
| `hitl/notification.py` | 733 | `TeamsNotificationService`: Microsoft Teams adaptive card notifications. `TeamsCardBuilder` for structured approval cards. `CompositeNotificationService` for multi-channel. |
| `hitl/unified_manager.py` | 546 | `UnifiedApprovalManager` (Sprint 111): consolidated approval for 5 sources (AG-UI, API, Claude SDK, MAF, Orchestrator). Priority-based processing. |

### 2.6 Cross-Cutting (5 files)

| File | LOC | Summary |
|------|-----|---------|
| `contracts.py` | 359 | L4a/L4b interface: `RoutingRequest`, `RoutingResult`, `InputGatewayProtocol`, `RouterProtocol`, `InputSource` enum (7 values). Bridge adapters for backward compatibility. |
| `metrics.py` | ~893 | `OrchestrationMetricsCollector`: OpenTelemetry counters/histograms for all routing layers, dialog turns, risk assessments, approval decisions. |
| `audit/logger.py` | ~281 | `AuditLogger`: structured JSON audit logging for compliance. |
| `input/servicenow_webhook.py` | ~150 | Legacy ServiceNow webhook handler. |
| `input/ritm_intent_mapper.py` | ~150 | RITM ticket to intent mapping. |
| `input/incident_handler.py` | ~150 | Incident processing handler. |
| `input/contracts.py` | ~100 | Input-specific contracts. |

---

## Module 3: `integrations/ag_ui/` (~27 files, ~10,329 LOC)

### 3.1 events/ — AG-UI Protocol Events (6 files, ~1,114 LOC)

| File | LOC | Summary |
|------|-----|---------|
| `events/base.py` | 115 | `AGUIEventType` (11 types: RUN_STARTED/FINISHED, TEXT_MESSAGE_START/CONTENT/END, TOOL_CALL_START/ARGS/END, STATE_SNAPSHOT/DELTA, CUSTOM). `BaseAGUIEvent` with `to_sse()` method. `RunFinishReason` (complete/error/cancelled/timeout). |
| `events/lifecycle.py` | 88 | `RunStartedEvent` (thread_id, run_id) and `RunFinishedEvent` (+ finish_reason, error, usage). |
| `events/message.py` | 99 | `TextMessageStartEvent`, `TextMessageContentEvent` (delta), `TextMessageEndEvent`. |
| `events/tool.py` | 146 | `ToolCallStartEvent`, `ToolCallArgsEvent` (delta), `ToolCallEndEvent` (status + result). `ToolCallStatus` (pending/running/success/error). |
| `events/state.py` | 168 | `StateSnapshotEvent`, `StateDeltaEvent` (list of operations), `StateDeltaOperation` (set/delete/append/increment), `CustomEvent` (event_name + payload). |
| `events/progress.py` | 422 | Sprint 69: `SubStep`, `SubStepStatus`, `StepProgressPayload`, `StepProgressTracker`, `create_step_progress_event()`, `emit_step_progress()`. Hierarchical step tracking via CustomEvent. |

### 3.2 thread/ — Conversation State (4 files, ~1,450 LOC)

| File | LOC | Summary |
|------|-----|---------|
| `thread/models.py` | 266 | `AGUIThread` (id, status, messages, state, metadata, run_count). `AGUIMessage` (id, role, content, tool_calls). Pydantic schemas for API serialization. |
| `thread/storage.py` | 378 | `CacheProtocol` + `ThreadCache` (Redis-backed, key: `ag_ui:thread:{id}`, TTL: 2h). `ThreadRepository` ABC + `InMemoryThreadRepository`. |
| `thread/redis_storage.py` | 275 | Sprint 119: `RedisCacheBackend`, `RedisThreadRepository` (key: `ag_ui:thread_repo:{id}`, TTL: 24h, status index sets). |
| `thread/manager.py` | 471 | `ThreadManager`: Write-Through pattern (cache + repo). Full lifecycle: create, append messages, update state, archive, delete. |

### 3.3 Bridge Layer (3 files, ~1,378 LOC)

| File | LOC | Summary |
|------|-----|---------|
| `bridge.py` | 1,079 | `HybridEventBridge`: primary SSE bridge. Wraps HybridOrchestratorV2 execution into AG-UI event stream. Heartbeat mechanism (2s interval). File attachment support (S75-5). SwarmEventEmitter integration. Prediction + workflow progress custom events. |
| `mediator_bridge.py` | 191 | `MediatorEventBridge` (Sprint 135): alternate bridge for OrchestratorMediator. EVENT_MAP maps mediator events to AG-UI types. 50-char chunked text simulation. SSEEventBuffer reconnection support. |
| `sse_buffer.py` | 108 | `SSEEventBuffer`: Redis-backed (with in-memory fallback) event replay buffer for SSE reconnection. Max 100 events, 5 min TTL. |

### 3.4 converters.py (1 file, 690 LOC)

| File | LOC | Summary |
|------|-----|---------|
| `converters.py` | 690 | `EventConverters`: transforms HybridResultV2 into AG-UI event sequences. `HybridEventType` (11 internal types). `content_to_chunks()` splits text into 100-char pieces. HITL_APPROVAL_REQUIRED CustomEvent for high-risk tools. |

### 3.5 features/ — AG-UI Feature Handlers (8 files, ~5,632 LOC)

| File | LOC | Summary |
|------|-----|---------|
| `features/agentic_chat.py` | 543 | `AgenticChatHandler`: streaming chat via HybridEventBridge. `ChatSession` tracks per-session history. Configurable chunk size, max history. |
| `features/tool_rendering.py` | 659 | `ToolRenderingHandler`: formats raw tool results for UI (JSON/TABLE/TEXT/CODE/IMAGE/ERROR). Configurable max output size. |
| `features/human_in_loop.py` | 744 | `HITLHandler`: checks RiskAssessmentEngine, emits `approval_required` CustomEvents. `ApprovalStorage` in-memory with TTL (5 min). Approval wait with timeout. |
| `features/generative_ui.py` | 892 | `GenerativeUIHandler`: workflow step visualization + mode switch info. `WorkflowProgress` multi-step tracker. `ModeSwitchReason` (4 reasons). |
| `features/approval_delegate.py` | 218 | `AGUIApprovalDelegate` (Sprint 111): bridges to `UnifiedApprovalManager` for consolidated approval tracking across 5 sources. |
| `features/advanced/shared_state.py` | 805 | `SharedStateHandler` + `StateSyncManager`: CRDT-style bidirectional state sync. Version vectors, conflict detection, 4 resolution strategies. |
| `features/advanced/tool_ui.py` | 879 | `ToolBasedUIHandler`: generates dynamic UI component specs (FORM/TABLE/CHART/CARD/BUTTON) from tool call metadata. |
| `features/advanced/predictive.py` | 710 | `PredictiveStateHandler`: optimistic state updates before LLM response. Confidence-based prediction with TTL expiry. |
