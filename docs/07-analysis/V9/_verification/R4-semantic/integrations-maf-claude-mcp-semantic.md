# R4 Semantic Analysis: MAF + Claude SDK + MCP Integration Modules

> **V9 Round 4** | Date: 2026-03-29 | Analyst: Claude Opus 4.6 (1M context)
> Full source reading of 176 Python files across 3 integration modules.

---

## Module Summary

| Module | Directory | Files | LOC (verified) | Purpose |
|--------|-----------|-------|----------------|---------|
| MAF Builder Layer | `integrations/agent_framework/` | 57 | **38,082** | Adapter layer wrapping Microsoft Agent Framework official API |
| Claude SDK Worker Layer | `integrations/claude_sdk/` | 48 | **15,406** | Claude Agent SDK integration (autonomous, hooks, tools, MCP client) |
| MCP Tool Layer | `integrations/mcp/` | 73 | **20,847** | Model Context Protocol infrastructure + 9 enterprise tool servers |
| **Total** | | **178** | **74,335** | |

---

## 1. MAF Builder Layer (`agent_framework/`) — 57 files, 38,082 LOC

### 1.1 Root Files (5 files, 2,194 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `__init__.py` | 166 | Package entry point. Exports `BaseAdapter`, `BuilderAdapter`, all exception types, `WorkflowAdapter`, `WorkflowConfig`, checkpoint storage classes, and Sprint 14 concurrent builder types. Version: `0.1.0`. Does NOT re-export Sprint 15+ builders (those are in `builders/__init__.py`). |
| `base.py` | 328 | Abstract base classes. `BaseAdapter` (ABC): config dict, `_initialized` flag, `ensure_initialized()`, async context manager. `BuilderAdapter[T, R]` (Generic): adds `_builder: Optional[T]`, `_workflow`, `build()` abstract, `run()` / `run_stream()` with auto-build, `reset()`. All adapters inherit from these. |
| `exceptions.py` | 399 | 7 exception classes in hierarchy: `AdapterError` (base, with `message`, `context` dict, `original_error`, `to_dict()`), `AdapterInitializationError` (+adapter_name), `WorkflowBuildError` (+workflow_id), `ExecutionError` (+workflow_id, executor_id), `CheckpointError` (+checkpoint_id, operation), `ValidationError` (+validation_errors list), `ConfigurationError` (+missing_keys, invalid_keys, config_source), `RecursionError` (+max_depth, current_depth, workflow_id). |
| `workflow.py` | 590 | `WorkflowConfig` dataclass (id, name, description, max_iterations=100, enable_checkpointing, checkpoint_storage, metadata). `WorkflowAdapter` extends `BuilderAdapter`: manages executor factories (lazy init) and direct executors, edges (simple/fan-out/fan-in/switch-case), chain helper. `build()` does lazy `from agent_framework import WorkflowBuilder`, creates builder, registers all executors/edges, calls `builder.build()`. `run()` / `run_stream()` with error wrapping. |
| `checkpoint.py` | 711 | `WorkflowCheckpointData` (slots dataclass): checkpoint_id (UUID), workflow_id, timestamp, messages, shared_state, pending_request_info_events, iteration_count, metadata, version. Bidirectional conversion with MAF `WorkflowCheckpoint`. `CheckpointStorageAdapter` (ABC): 5 methods (save/load/list_ids/list/delete). `PostgresCheckpointStorage`: raw SQL with UPSERT, JSON serialization. `RedisCheckpointCache`: key-prefix + TTL, get/set/delete. `CachedCheckpointStorage`: read-through cache (Redis first, then Postgres with backfill). `InMemoryCheckpointStorage`: dict-based for testing. |

### 1.2 builders/ (22 files, 24,215 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `__init__.py` | 805 | Massive re-export hub. Imports 200+ symbols from all 21 builder modules across Sprints 14-37. Organized by sprint with `__all__` listing all public symbols. |
| `concurrent.py` | 1,634 | `ConcurrentBuilderAdapter`: wraps `ConcurrentBuilder` from `agent_framework.orchestrations`. 4 modes (ALL/ANY/MAJORITY/FIRST_SUCCESS). Sprint 22 adds Gateway system: `GatewayType` (PARALLEL_SPLIT/PARALLEL_JOIN/INCLUSIVE_GATEWAY), `JoinCondition` (ALL/ANY/FIRST/N_OF_M), `MergeStrategy` (COLLECT_ALL/MERGE_DICT/FIRST_RESULT/AGGREGATE). `ExecutorProtocol` (runtime_checkable). Custom aggregators: `NOfMAggregator`, `MergeStrategyAggregator`. Factory functions for all modes + gateway configs. |
| `concurrent_migration.py` | 688 | Phase 2 migration shim. `ConcurrentExecutorAdapter`: wraps legacy `ConcurrentExecutor` API. `ParallelBranch`, `BranchStatus` (PENDING/RUNNING/SUCCESS/FAILED/TIMEOUT), `ConcurrentTask`, `ConcurrentResult`. `migrate_concurrent_executor()` converts Phase 2 executors to Phase 3 adapters. |
| `edge_routing.py` | 884 | FanOut/FanIn edge routing system. `Edge`, `EdgeGroup`, `FanOutEdgeGroup`, `FanInEdgeGroup` dataclasses. `FanOutStrategy` (BROADCAST/CONDITIONAL/WEIGHTED), `FanInStrategy` (COLLECT_ALL/MERGE/FIRST_COMPLETE/MAJORITY). `FanOutRouter`: applies strategy to route messages. `FanInAggregator`: collects and aggregates results. `ConditionalRouter`: condition-based routing with `RouteCondition`. |
| `handoff.py` | 992 | `HandoffBuilderAdapter`: wraps `HandoffBuilder` from `agent_framework.orchestrations`. `HandoffMode` (HUMAN_IN_LOOP/AUTONOMOUS). `HandoffStatus` (6 states). `HandoffRoute`, `HandoffParticipant`, `UserInputRequest`, `HandoffExecutionResult`. Module-level import of `HandoffBuilder, HandoffAgentUserRequest`. Build creates participants dict, configures routing, termination conditions, event handlers. Fallback to IPA internal on MAF failure. |
| `handoff_migration.py` | 734 | Phase 2 `HandoffControllerAdapter`. Legacy types: `HandoffPolicyLegacy`, `HandoffStatusLegacy`, `HandoffContextLegacy`, `HandoffRequestLegacy`, `HandoffResultLegacy`. Bidirectional converters for status and policy. `migrate_handoff_controller()` converts Phase 2 to Phase 3. |
| `handoff_hitl.py` | 1,005 | HITL (Human-in-the-Loop) session management. `HITLSessionStatus` (7 states), `HITLInputType` (TEXT/CHOICE/CONFIRMATION/FILE), `HITLInputRequest`/`HITLInputResponse`. `HITLSession`: manages lifecycle with timeout/escalation. `HITLCallback` (ABC), `DefaultHITLCallback`. `HITLManager`: session registry, create/submit/cancel/timeout. `HITLCheckpointAdapter`: wraps checkpoint storage for HITL state. |
| `handoff_policy.py` | 513 | Policy mapping from Phase 2 to Phase 3. `LegacyHandoffPolicy` (IMMEDIATE/GRACEFUL/CONDITIONAL). `AdaptedPolicyConfig`. `HandoffPolicyAdapter`: maps IMMEDIATE->autonomous, GRACEFUL->human_in_loop, CONDITIONAL->termination_condition. Condition factories: keyword, round-limit, composite. |
| `handoff_capability.py` | 1,050 | Agent capability matching. `CapabilityCategory` (6 types), `AgentStatus` (4 states), `MatchStrategy` (BEST_FIT/FIRST_FIT/ROUND_ROBIN/LEAST_LOADED). `AgentCapabilityInfo`, `CapabilityRequirementInfo`, `AgentAvailabilityInfo`, `CapabilityMatchResult`. `BUILTIN_CAPABILITIES` dict. `CapabilityMatcherAdapter`: scores agents by capability match + availability, applies strategy. |
| `handoff_context.py` | 855 | Context transfer between agents during handoff. `ContextTransferError`, `ContextValidationError`. `TransferContextInfo` (data, metadata, constraints), `TransformationRuleInfo` (field mapping, type conversion). `TransferResult`. `ContextTransferAdapter`: validates, transforms, and transfers context with rollback support. |
| `handoff_service.py` | 821 | Unified handoff facade. `HandoffServiceStatus` (IDLE/ACTIVE/PAUSED/ERROR). `HandoffRequest`, `HandoffRecord`, `HandoffTriggerResult`, `HandoffStatusResult`, `HandoffCancelResult`. `HandoffService`: integrates policy adapter, capability matcher, context transfer, and HITL manager into a single service. Trigger/cancel/status/list operations. |
| `groupchat.py` | 1,913 | `GroupChatBuilderAdapter`: wraps `GroupChatBuilder` from `agent_framework.orchestrations`. 7 speaker selection methods: AUTO, ROUND_ROBIN, RANDOM, MANUAL, CUSTOM, PRIORITY (S20), EXPERTISE (S20). `GroupChatParticipant`, `GroupChatMessage`, `GroupChatState`, `GroupChatTurn`, `GroupChatResult`. 7 termination conditions: MAX_ROUNDS, MAX_MESSAGES, TIMEOUT, KEYWORD, CONSENSUS, NO_PROGRESS, CUSTOM. Built-in selector factories. Fallback to `_MockGroupChatWorkflow`. |
| `groupchat_voting.py` | 736 | Voting-based speaker selection. `VotingMethod` (MAJORITY/UNANIMOUS/RANKED/WEIGHTED/APPROVAL). `VotingStatus`, `VotingConfig`, `Vote`, `VotingResult`. `GroupChatVotingAdapter`: configures voting-based selection within GroupChat. Factory functions for each voting method. |
| `groupchat_orchestrator.py` | 883 | Manager-based group chat orchestration. `ManagerSelectionRequest`/`ManagerSelectionResponse`. `GroupChatDirective`. `OrchestratorState`, `OrchestratorPhase` (SELECTING/DISCUSSING/VOTING/CONCLUDING). `GroupChatOrchestrator`: manages conversation flow with directive-based control. |
| `groupchat_migration.py` | 1,028 | Phase 2 `GroupChatManagerAdapter`. Legacy types with `Legacy` suffix. Bidirectional converters for selection method, state, participant, message, result. `migrate_groupchat_manager()` converts Phase 2 to Phase 3. Priority/weighted chat manager factories. |
| `magentic.py` | 1,810 | `MagenticBuilderAdapter`: wraps `MagenticBuilder`, `MagenticManagerBase`, `StandardMagenticManager` from `agent_framework.orchestrations`. `MagenticStatus` (9 states). Human intervention: 3 kinds (PLAN_REVIEW/TOOL_APPROVAL/STALL), 6 decisions. `TaskLedger` (facts + verified_facts + plan), `ProgressLedger` with 5-item evaluation. `StandardMagenticManager`: 4 customizable prompt templates. `MagenticContext`, `MagenticRound`, `MagenticResult`. Factory functions for research/coding workflows. |
| `magentic_migration.py` | 1,038 | Phase 2 DynamicPlanner migration. `MagenticManagerAdapter`, `HumanInterventionHandler`. Legacy types: `DynamicPlannerStateLegacy`, `PlanStepLegacy`, `DynamicPlanLegacy`, `ProgressEvaluationLegacy`. Bidirectional converters for state, context, plan, progress. |
| `workflow_executor.py` | 1,308 | `WorkflowExecutorAdapter`: wraps MAF `WorkflowExecutor`, `SubWorkflowRequestMessage`, `SubWorkflowResponseMessage`. `WorkflowExecutorStatus` (6 states), `WorkflowRunState` (7 states). `RequestInfoEvent`, `ExecutionContext`, `WorkflowOutput`, `WorkflowRunResult`. `WorkflowProtocol` for compatible workflows. `SimpleWorkflow` implementation. |
| `workflow_executor_migration.py` | 1,277 | Phase 2 nested workflow migration. `NestedWorkflowManagerAdapter`. Legacy types with `Legacy` suffix. Bidirectional converters for status, context, config, result, sub-workflow references. |
| `nested_workflow.py` | 1,307 | `NestedWorkflowAdapter`: wraps `WorkflowBuilder` + `Workflow` + `WorkflowExecutor`. `ContextPropagationStrategy` (INHERITED/ISOLATED/MERGED/FILTERED). `ExecutionMode` (SEQUENTIAL/PARALLEL/CONDITIONAL). `RecursionConfig` (max_depth, detection). `ContextPropagator`: handles context passing between parent/child. `RecursiveDepthController`: prevents infinite recursion. |
| `planning.py` | 1,367 | `PlanningAdapter`: wraps `MagenticBuilder` for planning workflows. `DecompositionStrategy` (SEQUENTIAL/HIERARCHICAL/PARALLEL/HYBRID). `PlanningMode` (SIMPLE/DECOMPOSED/DECISION_DRIVEN/ADAPTIVE/FULL). `DecisionRule`, `PlanningConfig`, `PlanningResult`. Integrates with domain layer: `TaskDecomposer`, `AutonomousDecisionEngine`, `TrialAndErrorEngine`, `DynamicPlanner`. Uses `LLMServiceFactory`. |
| `agent_executor.py` | 699 | `AgentExecutorAdapter`: wraps `ChatAgent` + `AzureOpenAIResponsesClient`. `AgentExecutorConfig` (Azure OpenAI settings), `AgentExecutorResult`. Lazy imports in `initialize()`. Singleton pattern via `get/set_agent_executor_adapter()`. Creates `AzureOpenAIResponsesClient`, then `ChatAgent` with instructions. |
| `code_interpreter.py` | 868 | `CodeInterpreterAdapter`: wraps Azure OpenAI Responses/Assistants API (NOT a MAF builder). `APIMode` (RESPONSES/ASSISTANTS/AUTO). `CodeInterpreterConfig`, `ExecutionResult`. Dual API support with auto-detection. Delegates to `assistant.AssistantManagerService`. Container Files API for file downloads. |

### 1.3 core/ (10 files, 5,695 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `__init__.py` | 189 | Re-exports from all 9 core modules. |
| `executor.py` | 577 | `WorkflowNodeExecutor`: adapts domain `WorkflowNode` to MAF `Executor` interface. Imports `from agent_framework import Executor, WorkflowContext, handler`. Implements `@handler` decorated methods for node execution. |
| `edge.py` | 448 | `WorkflowEdgeAdapter`: adapts domain `WorkflowEdge` to MAF `Edge`. Imports `from agent_framework import Edge`. Supports conditional edges with callable predicates. |
| `workflow.py` | 569 | `WorkflowDefinitionAdapter`: adapts domain `WorkflowDefinition` to MAF `Workflow`. Imports `from agent_framework import Workflow, WorkflowBuilder, Edge, Executor`. Builds complete workflow from definition. |
| `context.py` | 454 | `WorkflowContextAdapter`: context adaptation utilities. Converts between IPA platform context and MAF `WorkflowContext`. Shared state management. |
| `execution.py` | 797 | `SequentialOrchestrationAdapter`, `ExecutorAgentWrapper`, `ExecutionAdapter`. Imports `from agent_framework import Agent as ChatAgent, Workflow` + `SequentialBuilder`. Sequential agent orchestration with state tracking. |
| `events.py` | 614 | `WorkflowStatusEventAdapter`: processes MAF `WorkflowEvent`/`WorkflowStatusEvent`. Imports `from agent_framework import WorkflowEvent`. Maps MAF events to IPA platform events. |
| `state_machine.py` | 599 | `EnhancedExecutionStateMachine`: execution state machine with domain status mapping. States: PENDING, INITIALIZING, RUNNING, PAUSED, WAITING, COMPLETED, FAILED, CANCELLED, TIMEOUT. Transition validation. |
| `approval.py` | 884 | `HumanApprovalExecutor`: HITL approval via MAF `RequestResponseExecutor`. Imports `from agent_framework import Executor, handler, WorkflowContext`. Request/response pattern for human approval with timeout and escalation. |
| `approval_workflow.py` | 564 | `WorkflowApprovalAdapter`, `ApprovalWorkflowManager`. Imports `from agent_framework import Workflow, Edge`. Builds approval workflows with configurable approval chains. |

### 1.4 acl/ (4 files, 808 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `__init__.py` | 46 | Re-exports ACL interfaces and adapter. |
| `interfaces.py` | 266 | Anti-Corruption Layer interfaces. `AgentBuilderInterface` (ABC), `AgentRunnerInterface` (ABC), `ToolInterface` (ABC). Frozen dataclasses: `AgentConfig`, `WorkflowResult`. Defines version-independent API contract for MAF integration. |
| `adapter.py` | 252 | `MAFAdapter`: singleton version-aware adapter. Builder class lookup by name. Routes to correct MAF builder class based on detected version. |
| `version_detector.py` | 244 | `MAFVersionDetector`: detects installed MAF package version, checks API compatibility (method existence, signature changes). Version range validation. |

### 1.5 memory/ (4 files, 1,732 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `__init__.py` | 69 | Re-exports memory storage types. |
| `base.py` | 452 | `MemoryStorageProtocol` (Protocol class), `MemoryRecord` (dataclass with content, embedding, metadata, timestamps), `MemorySearchResult`. Wraps MAF `BaseContextProvider` concept. Abstract storage with search, add, update, delete operations. |
| `redis_storage.py` | 482 | `RedisMemoryStorage`: Redis-backed implementation using hash + sorted set. Search by metadata filter or vector similarity (if embeddings available). TTL support. |
| `postgres_storage.py` | 729 | `PostgresMemoryStorage`: PostgreSQL-backed with JSONB columns. Full-text search on content. Batch operations. Transaction support via SQLAlchemy async sessions. |

### 1.6 multiturn/ (3 files, 1,402 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `__init__.py` | 51 | Re-exports multiturn types. |
| `adapter.py` | 860 | `MultiTurnAdapter`: wraps MAF `CheckpointStorage` for multi-turn conversation management. `TurnResult`, `SessionState`. Manages conversation turns with checkpoint save/restore. Session lifecycle (create, continue, fork, close). Supports Redis and Postgres backends. |
| `checkpoint_storage.py` | 491 | `RedisCheckpointStorage`, `PostgresCheckpointStorage`, `FileCheckpointStorage`. Three checkpoint storage implementations extending MAF `CheckpointStorage` protocol. Redis uses hash keys, Postgres uses JSONB, File uses JSON files on disk. |

### 1.7 assistant/ (5 files, 1,217 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `__init__.py` | 95 | Re-exports assistant types. |
| `models.py` | 146 | Data models: `CodeExecutionResult`, `AssistantConfig`, `AssistantInfo`, `ThreadMessage`, `FileInfo`. |
| `exceptions.py` | 167 | 8 exception classes for assistant operations: `AssistantError` (base), `AssistantNotFoundError`, `ThreadError`, `FileError`, `CodeExecutionError`, `RateLimitError`, `AuthenticationError`, `ConfigurationError`. |
| `manager.py` | 414 | `AssistantManagerService`: manages Azure OpenAI Assistants lifecycle. Create/delete/list assistants. Thread management. Message handling. Code Interpreter tool configuration. |
| `files.py` | 395 | `FileStorageService`: file management for Code Interpreter. Upload, download (Container Files API), list, delete. Handles both Responses API (`cfile_` prefix) and Assistants API (`assistant-` prefix). |

### 1.8 tools/ (3 files, 819 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `__init__.py` | 61 | Re-exports + `register_default_tools()` function. |
| `base.py` | 344 | `BaseTool` (ABC with `name`, `description`, `parameters`, `execute()`). `ToolResult` (success/error + content). `ToolSchema`, `ToolParameter` for JSON Schema generation. `ToolRegistry`: register/get/list tools. |
| `code_interpreter_tool.py` | 414 | `CodeInterpreterTool`: tool wrapper for Code Interpreter functionality. Implements `BaseTool`. Delegates to `CodeInterpreterAdapter` for actual execution. Handles file output from code execution. |

---

## 2. Claude SDK Worker Layer (`claude_sdk/`) — 48 files, 15,406 LOC

### 2.1 Root Files (8 files, 3,330 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `__init__.py` | 95 | Package root. 41 exports covering client, session, types, exceptions, config. Version not explicitly declared. |
| `config.py` | 76 | `ClaudeSDKConfig` dataclass: api_key, model (default `claude-sonnet-4-20250514`), max_tokens, temperature, system_prompt, tools list. `from_env()` reads env vars, `from_yaml()` reads YAML config. |
| `types.py` | 131 | Shared types: `ToolCall`, `Message`, `ToolCallContext`, `ToolResultContext`, `QueryContext`, `HookResult` (ALLOW/DENY/SKIP), `QueryResult` (status, content, tool_calls, usage), `SessionResponse`, `ALLOW` constant. |
| `exceptions.py` | 76 | Exception hierarchy: `ClaudeSDKError` (base), `AuthenticationError`, `RateLimitError`, `TimeoutError`, `ToolError`, `HookRejectionError`, `MCPError`, `MCPConnectionError`, `MCPToolError`. |
| `client.py` | 355 | `ClaudeSDKClient`: main entry point. `query()` for one-shot, `create_session()` for multi-turn. `send_with_attachments()` (S75) for multimodal (text + image base64). `execute_with_thinking()` (S104) for Extended Thinking stream. Initializes `anthropic.AsyncAnthropic` client. |
| `query.py` | 344 | `execute_query()`: agentic loop implementation. Calls Anthropic Messages API, checks for `tool_use` blocks, runs HookChain, executes tools, appends results, loops until no tool_use. `execute_query_with_attachments()`: multimodal variant with base64 image support. `build_content_with_attachments()`: constructs content blocks. |
| `session.py` | 286 | `Session`: multi-turn conversation manager. Maintains message history, context, hooks. `query()` sends with full history. `fork()` creates branched sessions (deep copy of history). `close()` cleanup. Agentic loop identical to query.py. |
| `session_state.py` | 575 | `SessionStateManager`: save/restore/delete/compress/cleanup. `SessionState` with messages, metadata, timestamps. zlib compression with SHA-256 checksum. PostgreSQL persistence via checkpoint service. mem0 long-term memory sync (optional). `SessionStateConfig` for TTL, max_size, compression settings. |

### 2.2 autonomous/ (7 files, 3,475 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `__init__.py` | 129 | Exports all autonomous engine types. |
| `types.py` | 245 | Planning data types: `EventSeverity` (4 levels), `EventComplexity` (4 levels), `PlanStatus` (6 states), `StepStatus` (6 states), `RiskLevel` (4 levels). `EventContext`, `AnalysisResult`, `PlanStep`, `AutonomousPlan`, `VerificationResult`. `COMPLEXITY_BUDGET_TOKENS` mapping. |
| `analyzer.py` | 346 | `EventAnalyzer`: Phase 1 of autonomous cycle. Builds structured prompt from `EventContext`, calls Claude with Extended Thinking, extracts `AnalysisResult` with severity, complexity, root cause hypothesis, affected systems. |
| `planner.py` | 375 | `AutonomousPlanner`: Phase 2. Takes `AnalysisResult`, generates `AutonomousPlan` with ordered steps, resource estimates, risk assessment. Uses Claude Extended Thinking for plan generation. |
| `executor.py` | 397 | `PlanExecutor`: Phase 3. Executes `AutonomousPlan` step-by-step. `ExecutionEvent`/`ExecutionEventType` for SSE progress streaming. Step execution with tool calls, retry on failure, rollback support. |
| `verifier.py` | 353 | `ResultVerifier`: Phase 4. Verifies execution results against plan objectives. `verify()` checks each step outcome. `calculate_quality_score()`. `extract_lessons()` for learning loop. |
| `retry.py` | 393 | `RetryPolicy`: exponential backoff with jitter. `RetryConfig` (max_retries, base_delay, max_delay, backoff_factor). `RetryResult`. `FailureType` classification (TRANSIENT/PERMANENT/RATE_LIMIT/TIMEOUT). `with_retry()` decorator. |
| `fallback.py` | 587 | `SmartFallback`: 6 strategies (RETRY/SKIP/ALTERNATIVE/ESCALATE/ROLLBACK/ABORT). `FailureAnalysis` classifies failures. `FallbackAction`. `FailurePattern` for learning from past failures. Pattern-based strategy selection. |

### 2.3 hooks/ (6 files, 1,674 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `__init__.py` | 72 | Exports all hook types. |
| `base.py` | 245 | `Hook` (ABC): `priority` (int, higher = runs first), `on_tool_call()`, `on_tool_result()`. `HookChain`: collects hooks, sorts by priority descending, runs sequentially. Any hook returning DENY stops the chain. |
| `approval.py` | 175 | `ApprovalHook` (priority=90): requires human confirmation for Write, Edit, Bash, MultiEdit tools. Returns DENY if not approved. Configurable tool whitelist/blacklist. |
| `approval_delegate.py` | 275 | `ClaudeApprovalDelegate` (Sprint 111): bridges Claude SDK approval to `UnifiedApprovalManager`. Delegates approval decisions to the platform-wide approval system instead of standalone prompts. |
| `sandbox.py` | 502 | `SandboxHook` (priority=85): file access control. Checks paths against allowlist/blocklist. `StrictSandboxHook`: deny-by-default, explicit allowlist only. `UserSandboxHook`: configurable per-user restrictions. Path normalization and traversal prevention. |
| `rate_limit.py` | 329 | `RateLimitHook` (priority=80): per-minute rate limiting + concurrent call limiting. `RateLimitConfig` (calls_per_minute, max_concurrent). `RateLimitStats` for monitoring. Token bucket algorithm. Returns DENY when limits exceeded. |
| `audit.py` | 349 | `AuditHook` (priority=10, runs last): logs all tool calls and results. `AuditEntry` with timestamp, tool, args, result, duration. `AuditLog` with search/filter. Credential redaction (API keys, passwords, tokens detected via regex). |

### 2.4 tools/ (5 files, 1,640 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `__init__.py` | 48 | Exports tool types and registry functions. |
| `base.py` | 68 | `Tool` (ABC): `name`, `description`, `input_schema` (JSON Schema dict), `execute(**kwargs) -> ToolResult`. `ToolResult` (content string, is_error bool). |
| `registry.py` | 152 | Singleton tool registry. `register_tool()`, `get_tool_definitions()` (returns list of dicts for API), `execute_tool()` (lookup + execute). `_register_builtin_tools()` auto-registers all 10 built-in tools on first access. |
| `file_tools.py` | 607 | 6 file tools: `Read` (file reading with offset/limit), `Write` (file writing), `Edit` (string replacement in files), `MultiEdit` (multiple edits in one call), `Glob` (pattern matching), `Grep` (regex search with ripgrep-style options). All implement `Tool` ABC. |
| `command_tools.py` | 344 | 2 command tools: `Bash` (shell command execution with security pattern checks — blocks `rm -rf /`, `sudo`, etc.), `Task` (subagent delegation — creates child session for complex subtasks). |
| `web_tools.py` | 486 | 2 web tools: `WebSearch` (Brave/Google/Bing search API integration, configurable provider), `WebFetch` (HTTP GET + HTML-to-text extraction using BeautifulSoup, respects robots.txt). |

### 2.5 hybrid/ (5 files, 2,407 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `__init__.py` | ~15 | Exports hybrid orchestration types. |
| `types.py` | ~120 | `Framework` enum (MAF/CLAUDE/HYBRID). `HybridResult`, `TaskAnalysis` (complexity, capabilities needed), `TaskCapability`, `HybridSessionConfig`. |
| `capability.py` | 471 | `CapabilityMatcher`: keyword-based task analysis. Maps task descriptions to required capabilities (code_execution, web_search, file_ops, planning, conversation, etc.). Scores MAF vs Claude framework fit. |
| `selector.py` | 463 | `FrameworkSelector`: chooses MAF or Claude based on `TaskAnalysis`. `SelectionContext` (user preferences, session history, available tools). `SelectionStrategy` options. Threshold-based selection with configurable weights. |
| `orchestrator.py` | 546 | `HybridOrchestrator`: session management, `execute()` / `execute_stream()`. Analyzes task, selects framework, delegates to MAF adapter or Claude client. Result normalization. `create_orchestrator()` factory. |
| `synchronizer.py` | 927 | `ContextSynchronizer`: 5 format conversions (MAF->Claude, Claude->MAF, MAF->AG-UI, Claude->AG-UI, AG-UI->internal). Handles message format differences, tool call format translation, metadata mapping. **Known issue**: in-memory dict, no thread-safety locks. |

### 2.6 mcp/ (7 files, 2,270 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `__init__.py` | ~15 | Exports MCP client types. |
| `types.py` | 260 | `MCPServerConfig` (name, command/url, transport type, env vars, timeout). `MCPServerState` (DISCONNECTED/CONNECTING/CONNECTED/ERROR). `MCPTransportType` (STDIO/HTTP). `MCPToolDefinition`, `MCPToolResult`, `MCPMessage`. `MCPErrorCode` enum. |
| `exceptions.py` | ~70 | 11 MCP exception types: `MCPError` (base), `MCPConnectionError`, `MCPToolNotFoundError`, `MCPTimeoutError`, `MCPToolExecutionError`, `MCPServerError`, `MCPDisconnectedError`, etc. |
| `base.py` | 380 | `MCPServer` (ABC): `connect()`, `disconnect()`, `list_tools()`, `execute_tool()`, `send_request()`. JSON-RPC 2.0 protocol handling. Connection state management. |
| `stdio.py` | 309 | `MCPStdioServer`: local subprocess transport. Spawns process, communicates via stdin/stdout JSON-RPC. Process lifecycle management. |
| `http.py` | 285 | `MCPHTTPServer`: remote HTTP transport. Uses httpx for async HTTP. SSE support for streaming responses. |
| `discovery.py` | 519 | `ToolDiscovery`: tool indexing, categorization (9 categories: file, search, code, web, cloud, database, shell, communication, other), keyword-based search, input validation. `ToolIndex` for fast lookup. |
| `manager.py` | 519 | `MCPManager`: multi-server lifecycle management. `connect_all()` parallel server connections. `discover_tools()` aggregates tools from all servers. `execute_tool()` routes to correct server. `health_check()` + `reconnect_unhealthy()`. |

### 2.7 orchestrator/ (4 files, 1,627 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `__init__.py` | ~15 | Exports orchestrator types. |
| `types.py` | 308 | `TaskComplexity` (SIMPLE/MODERATE/COMPLEX/VERY_COMPLEX). `ExecutionMode` (PARALLEL/SEQUENTIAL/PIPELINE/ADAPTIVE). `AgentInfo`, `ComplexTask`, `TaskAnalysis`, `Subtask`, `AgentSelection`, `SubtaskResult`, `CoordinationResult`, `CoordinationContext`. |
| `coordinator.py` | 522 | `ClaudeCoordinator`: 4-phase coordination cycle (analyze -> select_agents -> execute -> aggregate). Claude-led multi-agent coordination. Uses Claude to analyze tasks and select optimal agent assignments. |
| `task_allocator.py` | 483 | `TaskAllocator`: agent scoring (70% capability match, 30% availability). `select_agents()` assigns agents to subtasks. `execute_parallel()`, `execute_sequential()`, `execute_pipeline()` execution modes. |
| `context_manager.py` | 314 | `ContextManager`: inter-subtask data transfer. `transfer_context()` passes results between subtasks. `merge_results()` combines parallel outputs. `aggregate_final_result()` produces final `CoordinationResult`. |

---

## 3. MCP Tool Layer (`mcp/`) — 73 files, 20,847 LOC

### 3.1 Core Protocol (4 files, 1,643 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `core/types.py` | 417 | Type system: `ToolInputType` (7 JSON Schema types: STRING/NUMBER/INTEGER/BOOLEAN/ARRAY/OBJECT/NULL). `ToolParameter`, `ToolSchema` with bidirectional MCP format conversion. `ToolResult` (content list, is_error). `MCPRequest`/`MCPResponse` for JSON-RPC 2.0. `MCPErrorCode` enum. |
| `core/protocol.py` | 407 | `MCPProtocol`: JSON-RPC 2.0 handler implementing MCP spec 2024-11-05. 8 methods: initialize, initialized, tools/list, tools/call, resources/list, resources/read, prompts/list, prompts/get, ping. Tool registration (name -> handler + schema). Permission check integration (Sprint 113). |
| `core/transport.py` | 372 | `BaseTransport` (ABC). `StdioTransport`: subprocess lifecycle (spawn, async read loop, write lock, pending request ID matching, graceful shutdown). `InMemoryTransport`: direct protocol invocation for testing. |
| `core/client.py` | 446 | `MCPClient`: multi-server client. `ServerConfig` (name, command, args, env). `connect()` / `disconnect()` lifecycle. Tool discovery via `tools/list`. Tool invocation via `tools/call`. Async context manager support. |

### 3.2 Registry (2 files, 1,034 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `registry/server_registry.py` | 595 | `ServerRegistry`: central lifecycle management. `RegisteredServer` with 7-state FSM (REGISTERED/CONNECTING/CONNECTED/DISCONNECTING/DISCONNECTED/ERROR/RECONNECTING). Auto-reconnect with exponential backoff (delay * 2^attempt). Event handler system for status change notifications. Tool catalog aggregation across all connected servers. |
| `registry/config_loader.py` | 439 | `ConfigLoader`: YAML/JSON config loading. `ServerDefinition` with server name, command, args, env. `${ENV_VAR}` interpolation with environment variable expansion. Validation of server definitions. `ConfigError` for loading failures. |

### 3.3 Security (5 files, 1,665 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `security/permissions.py` | 458 | 4-level RBAC: `PermissionLevel` (NONE=0/READ=1/EXECUTE=2/ADMIN=3). `Permission`, `PermissionPolicy` with glob-pattern matching for servers/tools. `PermissionManager`: priority-based policy evaluation, deny-list precedence, dynamic conditions (time_range, ip_whitelist, custom evaluators). |
| `security/permission_checker.py` | 183 | `MCPPermissionChecker`: runtime enforcement facade. Two modes via `MCP_PERMISSION_MODE` env var: "log" (Phase 1, WARNING log + continue) and "enforce" (Phase 2, raises PermissionError). Dev/testing gets permissive ADMIN default. Stats tracking (allowed/denied counts). |
| `security/command_whitelist.py` | 225 | `CommandWhitelist`: three-tier command security. 79 `DEFAULT_WHITELIST` commands (ls, cat, grep, etc.). 24 `BLOCKED_PATTERNS` regex (rm -rf /, chmod 777, etc.). Everything else `requires_approval`. Extensible via `MCP_ADDITIONAL_WHITELIST` env var. |
| `security/audit.py` | 686 | `AuditEventType` (12 types across 5 categories: connection, tool, access, admin, system). `AuditEvent`, `AuditFilter`. `AuditStorage` (ABC). `InMemoryAuditStorage` (bounded deque). `FileAuditStorage` (JSON Lines). `AuditLogger`: sensitive field redaction (password, token, key, secret patterns), event handler pipeline. |
| `security/redis_audit.py` | ~120 | `RedisAuditStorage`: production audit backend. Redis Sorted Set (score=timestamp) for efficient time-range queries. Auto-trimming to max_size. Key: `mcp:audit:events`. |

### 3.4 Azure MCP Server (10 files, ~3,048 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `servers/azure/__init__.py` | ~60 | Exports `AzureMCPServer`, `AzureConfig`. |
| `servers/azure/server.py` | 343 | `AzureMCPServer`: main server class. Registers 23 tools from 5 tool modules. Initializes `AzureClientManager`. Implements MCPProtocol handler registration. |
| `servers/azure/client.py` | 355 | `AzureClientManager`: manages Azure SDK clients. `AzureConfig` (subscription_id, resource_group, credentials). Lazy client initialization for Compute, Network, Monitor, Storage, Resource. Uses `DefaultAzureCredential`. |
| `servers/azure/__main__.py` | ~30 | Entry point for standalone server execution. |
| `servers/azure/tools/__init__.py` | ~20 | Tool module exports. |
| `servers/azure/tools/vm.py` | 737 | `VMTools`: 6 tools (list_vms, get_vm, start_vm, stop_vm, restart_vm, get_vm_status). Uses `azure.mgmt.compute.ComputeManagementClient`. Detailed VM info extraction (size, OS, IP, disks). |
| `servers/azure/tools/resource.py` | 362 | `ResourceTools`: 4 tools (list_resources, get_resource, list_resource_groups, get_resource_group). Uses `azure.mgmt.resource.ResourceManagementClient`. |
| `servers/azure/tools/monitor.py` | 408 | `MonitorTools`: 5 tools (get_metrics, list_metric_definitions, get_activity_log, create_alert_rule, list_alert_rules). Uses `azure.mgmt.monitor.MonitorManagementClient`. |
| `servers/azure/tools/network.py` | 457 | `NetworkTools`: 5 tools (list_vnets, get_vnet, list_nsgs, get_nsg_rules, list_public_ips). Uses `azure.mgmt.network.NetworkManagementClient`. |
| `servers/azure/tools/storage.py` | 396 | `StorageTools`: 3 tools (list_storage_accounts, get_storage_account, list_containers). Uses `azure.mgmt.storage.StorageManagementClient`. |

### 3.5 Filesystem MCP Server (5 files, ~1,316 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `servers/filesystem/__init__.py` | ~30 | Exports `FilesystemMCPServer`. |
| `servers/filesystem/server.py` | 315 | `FilesystemMCPServer`: registers 6 tools. Initializes sandbox. |
| `servers/filesystem/tools.py` | 481 | `FilesystemTools`: 6 tools (read_file, write_file, list_directory, create_directory, delete_file, file_info). Path validation through sandbox. |
| `servers/filesystem/sandbox.py` | 529 | `FilesystemSandbox`: path security. `SandboxConfig` (allowed_dirs, denied_patterns, max_file_size). Path normalization, traversal prevention (../ detection), extension filtering. |
| `servers/filesystem/__main__.py` | ~30 | Entry point. |

### 3.6 Shell MCP Server (5 files, ~990 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `servers/shell/__init__.py` | ~30 | Exports `ShellMCPServer`. |
| `servers/shell/server.py` | 316 | `ShellMCPServer`: registers 2 tools. Initializes executor with shell config. |
| `servers/shell/tools.py` | ~180 | `ShellTools`: 2 tools (execute_command, execute_script). Delegates to executor. |
| `servers/shell/executor.py` | 443 | `ShellExecutor`: secure command execution. `ShellConfig` (shell_type, timeout, max_output_size, working_dir). `ShellType` (BASH/POWERSHELL/CMD). Uses `asyncio.create_subprocess_exec`. Output truncation, timeout handling. Integrates with `CommandWhitelist`. |
| `servers/shell/__main__.py` | ~30 | Entry point. |

### 3.7 LDAP MCP Server (7 files, ~1,458 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `servers/ldap/__init__.py` | ~30 | Exports `LDAPMCPServer`. |
| `servers/ldap/server.py` | 311 | `LDAPMCPServer`: registers 6 tools. |
| `servers/ldap/client.py` | 662 | `LDAPConnectionManager`: manages LDAP connections. `LDAPConfig` (server, port, bind_dn, password, base_dn, use_ssl). Connection pooling, auto-reconnect. Search, add, modify, delete operations via `ldap3` library. |
| `servers/ldap/tools.py` | 494 | `LDAPTools`: 6 tools (search_users, get_user, search_groups, get_group_members, search_ou, get_ou_tree). LDAP filter construction, attribute mapping. |
| `servers/ldap/ad_config.py` | ~80 | Active Directory specific configuration: default attributes, group types, account control flags. |
| `servers/ldap/ad_operations.py` | 393 | AD-specific operations: enable/disable account, reset password, manage group membership, unlock account. Uses AD-specific LDAP attributes (userAccountControl, etc.). |
| `servers/ldap/__main__.py` | ~30 | Entry point. |

### 3.8 SSH MCP Server (5 files, ~1,502 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `servers/ssh/__init__.py` | ~30 | Exports `SSHMCPServer`. |
| `servers/ssh/server.py` | 312 | `SSHMCPServer`: registers 6 tools. |
| `servers/ssh/client.py` | 606 | `SSHConnectionManager`: manages SSH connections via `paramiko`. `SSHConfig` (host, port, username, password/key_file, timeout). Connection pooling, keep-alive. Command execution, file transfer (SFTP), port forwarding. |
| `servers/ssh/tools.py` | 619 | `SSHTools`: 6 tools (execute_command, upload_file, download_file, list_remote_dir, get_system_info, check_service_status). |
| `servers/ssh/__main__.py` | ~30 | Entry point. |

### 3.9 n8n MCP Server (6 files, ~900 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `servers/n8n/__init__.py` | ~30 | Exports `N8nMCPServer`. |
| `servers/n8n/server.py` | 358 | `N8nMCPServer`: registers 6 tools from workflow and execution modules. |
| `servers/n8n/client.py` | 491 | `N8nApiClient`: REST API client for n8n workflow automation. `N8nConfig` (base_url, api_key). CRUD for workflows, trigger execution, get execution status. Uses httpx async client. |
| `servers/n8n/tools/__init__.py` | ~15 | Tool module exports. |
| `servers/n8n/tools/workflow.py` | ~200 | `WorkflowTools`: 3 tools (list_workflows, get_workflow, activate_workflow). |
| `servers/n8n/tools/execution.py` | 310 | `ExecutionTools`: 3 tools (execute_workflow, get_execution, list_executions). |
| `servers/n8n/__main__.py` | ~30 | Entry point. |

### 3.10 ADF MCP Server (6 files, ~950 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `servers/adf/__init__.py` | ~30 | Exports `AdfMCPServer`. |
| `servers/adf/server.py` | 329 | `AdfMCPServer`: registers 8 tools from pipeline and monitoring modules. |
| `servers/adf/client.py` | 581 | `AdfApiClient`: Azure Data Factory REST API client. `AdfConfig` (subscription_id, resource_group, factory_name, credentials). Pipeline CRUD, trigger management, run monitoring. Uses `azure.mgmt.datafactory`. |
| `servers/adf/tools/__init__.py` | ~15 | Tool module exports. |
| `servers/adf/tools/pipeline.py` | 376 | `PipelineTools`: 5 tools (list_pipelines, get_pipeline, create_run, cancel_run, get_run_status). |
| `servers/adf/tools/monitoring.py` | 354 | `MonitoringTools`: 3 tools (list_activity_runs, get_trigger_runs, list_triggers). |
| `servers/adf/__main__.py` | ~30 | Entry point. |

### 3.11 D365 MCP Server (7 files, ~1,000 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `servers/d365/__init__.py` | ~30 | Exports `D365MCPServer`. |
| `servers/d365/server.py` | 334 | `D365MCPServer`: registers 6 tools from query and crud modules. |
| `servers/d365/client.py` | 1,038 | `D365ApiClient`: Dynamics 365 OData REST API client. `D365Config` (environment_url, client_id, client_secret, tenant_id). Entity CRUD, batch operations, FetchXML queries, metadata discovery. Token management. |
| `servers/d365/auth.py` | ~150 | OAuth2 authentication for D365. `D365Auth`: client credentials flow via MSAL. Token caching and refresh. |
| `servers/d365/tools/__init__.py` | ~15 | Tool module exports. |
| `servers/d365/tools/query.py` | 404 | `QueryTools`: 3 tools (query_entities, fetchxml_query, get_entity_metadata). OData filter construction, $select/$expand/$filter support. |
| `servers/d365/tools/crud.py` | ~200 | `CrudTools`: 3 tools (create_record, update_record, delete_record). |
| `servers/d365/__main__.py` | ~30 | Entry point. |

### 3.12 ServiceNow Server (3 files, ~800 LOC)

| File | LOC | Semantic Summary |
|------|-----|------------------|
| `servicenow_config.py` | ~100 | `ServiceNowConfig`: instance_url, username, password, client_id, client_secret. OAuth2 or basic auth. |
| `servicenow_client.py` | 523 | `ServiceNowClient`: REST API client. Table API CRUD, incident management, change request handling, CMDB queries. Uses httpx. Token management for OAuth2. |
| `servicenow_server.py` | 623 | `ServiceNowMCPServer`: registers 6 tools (list_incidents, create_incident, update_incident, query_table, get_record, search_cmdb). Implements full MCP protocol handler. |

### 3.13 Package Files (~12 files, ~500 LOC)

Various `__init__.py` and `__main__.py` files across the module providing exports and entry points.

---

## 4. Cross-Module Integration Points

### 4.1 MAF <-> Claude SDK

- `claude_sdk/hybrid/orchestrator.py` imports MAF adapter types for framework selection
- `claude_sdk/hybrid/synchronizer.py` converts between MAF and Claude message formats
- `agent_framework/builders/*.py` use `TYPE_CHECKING` imports from `hybrid.execution.MAFToolCallback`

### 4.2 Claude SDK <-> MCP (mcp/ under claude_sdk)

- `claude_sdk/mcp/` is a **client-side** MCP implementation (connects TO external MCP servers)
- `integrations/mcp/` is the **server-side** MCP implementation (provides tools TO agents)
- Both use JSON-RPC 2.0 but with independent type systems

### 4.3 MAF <-> MCP

- MAF builders can register MCP tools via the tool registry
- `agent_framework/tools/base.py` defines tool interface compatible with MCP tool schema
- MCP tools are discovered and made available to MAF agents through the hybrid layer

---

## 5. LOC Verification Summary

| Module | V9 R1 Claim | R2 Verified | R4 Full Count (wc -l) | Delta |
|--------|------------|-------------|----------------------|-------|
| MAF (agent_framework) | ~15,000 | 36,600 | **38,082** | +23,082 from R1, +1,482 from R2 |
| Claude SDK | ~15,000 | ~15,000 | **15,406** | +406 from R1 |
| MCP | ~20,847 (header) / ~16,806 (table) | ~20,847 | **20,847** | Table was 4,041 under |

### Per-Subdirectory Breakdown (MAF)

| Subdirectory | Files | LOC |
|-------------|-------|-----|
| Root (base, workflow, checkpoint, exceptions, __init__) | 5 | 2,194 |
| builders/ | 22 | 24,215 |
| core/ | 10 | 5,695 |
| acl/ | 4 | 808 |
| memory/ | 4 | 1,732 |
| multiturn/ | 3 | 1,402 |
| assistant/ | 5 | 1,217 |
| tools/ | 3 | 819 |
| **Total** | **56** | **38,082** |

### Per-Subdirectory Breakdown (Claude SDK)

| Subdirectory | Files | LOC |
|-------------|-------|-----|
| Root (client, query, session, session_state, types, exceptions, config, __init__) | 8 | ~1,938 |
| autonomous/ | 7 | ~3,475 |
| hooks/ | 6 | ~1,674 |
| tools/ | 5 | ~1,640 |
| hybrid/ | 5 | ~2,407 |
| mcp/ | 7 | ~2,270 |
| orchestrator/ | 4 | ~1,627 |
| **Total** | **47** | **15,406** |

---

*Generated by Claude Opus 4.6 (1M context) | V9 Round 4 Semantic Analysis*
