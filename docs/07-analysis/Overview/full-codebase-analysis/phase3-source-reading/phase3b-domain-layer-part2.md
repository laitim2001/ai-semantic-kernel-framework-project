# Phase 3B: Domain Layer Analysis — Part 2: Orchestration Module

> **Agent**: B2 | **Module**: `backend/src/domain/orchestration/` | **Status**: DEPRECATED (migrated to adapters)
> **Total Files**: 22 | **Total LOC**: 11,465 | **Empty/Stub Methods**: 30
> **Feature Mapping**: A8 (Dynamic Planning), A9 (Nested Workflow)

---

## 1. Module Overview

The `domain/orchestration/` module is the **largest domain module** in the IPA Platform. It was originally built in Sprints 9-11 and has since been **deprecated** (Sprint 25/30) in favor of adapter-layer implementations in `integrations/agent_framework/`. Despite deprecation, all code remains intact and is still imported by API routes as "extension functionality."

### Deprecation Status

| Sub-module | Old Location | New Location | Status |
|------------|-------------|--------------|--------|
| `multiturn/` | `domain/orchestration/multiturn/` | `integrations/agent_framework/multiturn/` | Deprecated, still imported |
| `memory/` | `domain/orchestration/memory/` | `integrations/agent_framework/memory/` | Deprecated, still imported |
| `planning/` | `domain/orchestration/planning/` | `integrations/agent_framework/builders/` | Deprecated, still imported |
| `nested/` | `domain/orchestration/nested/` | `integrations/agent_framework/builders/` | Deprecated, still imported |

All `__init__.py` files emit `DeprecationWarning` on import. The root `__init__.py` re-exports all public symbols (35+ exports in `__all__`).

---

## 2. File Inventory

| # | File | Lines | Sprint |
|---|------|-------|--------|
| 1 | `__init__.py` | 109 | S25 |
| 2 | `multiturn/__init__.py` | 57 | S30 |
| 3 | `multiturn/session_manager.py` | 824 | S9 |
| 4 | `multiturn/turn_tracker.py` | 457 | S9 |
| 5 | `multiturn/context_manager.py` | 527 | S9 |
| 6 | `memory/__init__.py` | 54 | S30 |
| 7 | `memory/models.py` | 277 | S9 |
| 8 | `memory/base.py` | 414 | S9 |
| 9 | `memory/in_memory.py` | 331 | S9 |
| 10 | `memory/redis_store.py` | 480 | S9 |
| 11 | `memory/postgres_store.py` | 542 | S9 |
| 12 | `planning/__init__.py` | 87 | S30 |
| 13 | `planning/task_decomposer.py` | 791 | S10 |
| 14 | `planning/dynamic_planner.py` | 748 | S10 |
| 15 | `planning/decision_engine.py` | 724 | S10 |
| 16 | `planning/trial_error.py` | 888 | S10 |
| 17 | `nested/__init__.py` | 101 | S30 |
| 18 | `nested/workflow_manager.py` | 956 | S11 |
| 19 | `nested/sub_executor.py` | 614 | S11 |
| 20 | `nested/recursive_handler.py` | 683 | S11 |
| 21 | `nested/composition_builder.py` | 783 | S11 |
| 22 | `nested/context_propagation.py` | 918 | S11 |
| | **TOTAL** | **11,465** | |

---

## 3. Sub-Module: `multiturn/` (Multi-Turn Session Management)

**Purpose**: Manages multi-turn conversation sessions with lifecycle control, context persistence, and agent coordination.
**LOC**: 1,808 (session_manager: 824, turn_tracker: 457, context_manager: 527)
**Sprint**: S9 (8 story points)

### 3.1 `session_manager.py` (824 lines)

**Classes**:

| Class | Line | Description |
|-------|------|-------------|
| `SessionStatus` (Enum) | L23 | 7 states: CREATED, ACTIVE, PAUSED, WAITING_INPUT, EXPIRED, COMPLETED, TERMINATED |
| `SessionMessage` | L44 | Dataclass for messages within a session (message_id, session_id, turn_number, role, content) |
| `MultiTurnSession` | L101 | Dataclass representing a complete session with history, expiration, and turn tracking |
| `MultiTurnSessionManager` | L187 | Main manager class with in-memory session storage |

**MultiTurnSessionManager Methods** (22 methods):

| Method | Line | Type | Description |
|--------|------|------|-------------|
| `__init__` | L218 | sync | Initialize with default_timeout (1800s), max_turns (50), cleanup_interval (300s) |
| `create_session` | L246 | async | Create new session with UUID, track per-user |
| `get_session` | L296 | async | Get session by ID, auto-expire if past deadline |
| `update_session` | L314 | async | Update context/metadata with lock |
| `close_session` | L344 | async | Close session with reason |
| `delete_session` | L373 | async | Remove session from memory |
| `start_session` | L403 | async | Transition CREATED -> ACTIVE, set turn=1 |
| `pause_session` | L432 | async | Transition ACTIVE -> PAUSED |
| `resume_session` | L456 | async | Transition PAUSED -> ACTIVE |
| `start_turn` | L484 | async | Increment turn, check max_turns limit |
| `add_message` | L518 | async | Add message to session history with lock |
| `execute_turn` | L596 | async | Full turn: user input -> agent handler -> response |
| `list_sessions` | L669 | async | List with user_id/status/active_only filters |
| `list_active_sessions` | L709 | async | Shorthand for active-only listing |
| `get_user_session_count` | L725 | async | Count sessions per user |
| `_expire_session` | L743 | async | Mark session as expired |
| `cleanup_expired_sessions` | L751 | async | Batch cleanup of expired sessions |
| `start_cleanup_task` | L769 | async | Start background asyncio cleanup loop |
| `stop_cleanup_task` | L787 | async | Cancel background cleanup task |
| `on_event` | L802 | sync | Register event handler |
| `_emit_event` | L813 | async | Emit events to registered handlers |

**State Management**: In-memory `Dict[str, MultiTurnSession]` with per-session `asyncio.Lock`. User-session mapping via `Dict[str, Set[str]]`. Background cleanup task runs every 5 minutes.

**Business Logic**:
- Session lifecycle: CREATED -> ACTIVE -> (PAUSED <-> ACTIVE) -> COMPLETED/EXPIRED/TERMINATED
- Max turns enforcement (default 50)
- Session timeout with sliding window (default 30 min)
- Event-driven architecture with handler registration

### 3.2 `turn_tracker.py` (457 lines)

**Classes**:

| Class | Line | Description |
|-------|------|-------------|
| `TurnStatus` (Enum) | L21 | 5 states: STARTED, AWAITING_RESPONSE, COMPLETED, FAILED, CANCELLED |
| `TurnMessage` | L38 | Dataclass for individual messages within a turn |
| `Turn` | L68 | Dataclass for a single conversation turn with timing and status |
| `TurnTracker` | L151 | Tracks all turns within a session |

**TurnTracker Methods** (13 methods):

| Method | Line | Type | Description |
|--------|------|------|-------------|
| `__init__` | L181 | sync | Initialize with session_id |
| `start_turn` | L215 | sync | Create new turn, set as current |
| `end_turn` | L251 | sync | Complete or fail a turn with timing |
| `get_turn` | L288 | sync | Get turn by ID |
| `get_current_turn` | L299 | sync | Get active turn |
| `get_turn_by_number` | L307 | sync | Get turn by sequence number |
| `get_turn_history` | L321 | sync | Get turn list with optional filters |
| `add_message_to_current` | L351 | sync | Add message to active turn |
| `get_all_messages` | L376 | sync | Get all messages across turns |
| `get_statistics` | L404 | sync | Compute stats: total/completed/failed/avg_duration |
| `clear` | L437 | sync | Clear all turns |
| `cancel_current` | L444 | sync | Cancel active turn |

**Business Logic**: Turn-level statistics (success rate, average duration, messages per turn). Maintains ordered turn history.

### 3.3 `context_manager.py` (527 lines)

**Classes**:

| Class | Line | Description |
|-------|------|-------------|
| `ContextScope` (Enum) | L22 | 4 scopes: SESSION, TURN, TEMPORARY, PERSISTENT |
| `ContextEntry` | L37 | Dataclass for context entries with expiration |
| `SessionContextManager` | L79 | Full context manager with scoping and serialization |

**SessionContextManager Methods** (17 methods):

| Method | Line | Type | Description |
|--------|------|------|-------------|
| `__init__` | L108 | sync | Initialize with session_id and optional initial context |
| `set` | L145 | sync | Set context value with scope and optional expiry |
| `get` | L184 | sync | Get context value with expiry check |
| `remove` | L212 | sync | Remove context entry |
| `has` | L229 | sync | Check key existence (with expiry) |
| `keys` | L248 | sync | List keys filtered by scope |
| `get_context` | L272 | sync | Get full context dict filtered by scopes |
| `update_context` | L295 | sync | Batch update multiple values |
| `merge_context` | L311 | sync | Merge another context with override option |
| `clear_context` | L330 | sync | Clear entries by scope |
| `start_turn` | L364 | sync | Start new turn |
| `end_turn` | L375 | sync | End turn, clear TURN and TEMPORARY scopes |
| `build_agent_context` | L385 | sync | Build context dict for agent consumption |
| `register_transformer` | L426 | sync | Register context transformation function |
| `to_dict` | L443 | sync | Serialize state |
| `from_dict` | L457 | classmethod | Deserialize state |
| `clone` | L489 | sync | Deep copy context manager |
| `get_statistics` | L502 | sync | Stats: total/expired entries by scope |

**Business Logic**: Four-tier scoping system (SESSION > PERSISTENT > TURN > TEMPORARY). Context transformers pipeline for agent context building. Expiration-based cleanup.

---

## 4. Sub-Module: `memory/` (Conversation Memory Storage)

**Purpose**: Abstract storage layer for conversation memory with multiple backend implementations.
**LOC**: 2,044 (models: 277, base: 414, in_memory: 331, redis: 480, postgres: 542)
**Sprint**: S9 (8 story points)

### 4.1 `models.py` (277 lines)

**Classes**:

| Class | Line | Description |
|-------|------|-------------|
| `SessionStatus` (Enum) | L18 | 5 states: ACTIVE, PAUSED, COMPLETED, EXPIRED, ARCHIVED |
| `MessageRecord` | L36 | Dataclass for individual messages (role, content, timestamps) |
| `ConversationTurn` | L93 | Dataclass for turns with user_input/agent_response pair |
| `ConversationSession` | L150 | Dataclass for sessions with turns, context, expiration |

**ConversationSession Methods**: `turn_count` (property), `is_expired` (property), `duration_seconds` (property), `add_turn()`, `get_last_turn()`, `get_turn_by_number()`, `to_dict()`, `from_dict()` (classmethod), `get_summary()`.

### 4.2 `base.py` (414 lines) — Abstract Base Class

**Class**: `ConversationMemoryStore(ABC)` — 21 abstract methods

| Method | Line | Category | Description |
|--------|------|----------|-------------|
| `add_message` | L47 | Message Ops | Add message to conversation |
| `get_messages` | L58 | Message Ops | Retrieve messages with filters |
| `get_message_count` | L79 | Message Ops | Count messages in session |
| `delete_messages` | L93 | Message Ops | Delete messages by session |
| `save_session` | L111 | Session Ops | Persist session |
| `load_session` | L122 | Session Ops | Load session by ID |
| `delete_session` | L136 | Session Ops | Delete session |
| `list_sessions` | L150 | Session Ops | List sessions with filters |
| `update_session_status` | L173 | Session Ops | Update session status |
| `save_turn` | L196 | Turn Ops | Save conversation turn |
| `get_turns` | L212 | Turn Ops | Get turns for session |
| `get_turn` | L231 | Turn Ops | Get specific turn |
| `search_by_content` | L254 | Search | Full-text content search |
| `get_session_summary` | L279 | Analytics | Generate session summary |
| `get_statistics` | L296 | Analytics | Storage statistics |
| `cleanup_expired_sessions` | L311 | Maintenance | Clean expired sessions |
| `archive_session` | L322 | Maintenance | Archive old sessions |
| `update_session_context` | L339 | Context (concrete) | Update session context |
| `get_session_context` | L364 | Context (concrete) | Get session context |
| `session_exists` | L385 | Context (concrete) | Check session existence |
| `get_latest_sessions` | L399 | Context (concrete) | Get recent sessions |

**NOTE**: 17 methods are `@abstractmethod` with `pass` body (expected for ABC). The last 4 methods (L339-L399) have concrete default implementations.

### 4.3 `in_memory.py` (331 lines) — In-Memory Implementation

**Class**: `InMemoryConversationMemoryStore(ConversationMemoryStore)` — 21 methods

Fully implemented using `Dict` storage: `_sessions`, `_turns`, `_messages`. Suitable for testing/development. Includes `clear()`, `get_session_count()`, `get_total_turn_count()` utility methods.

**All 17 abstract methods are fully implemented** with working business logic.

### 4.4 `redis_store.py` (480 lines) — Redis Implementation

**Class**: `RedisConversationMemoryStore(ConversationMemoryStore)` — 21 methods + 4 key helpers

**Protocol**: `RedisClientProtocol` with 10 empty stub methods (L35-L44):
- `rpush`, `lrange`, `llen`, `delete`, `expire`, `hset`, `hgetall`, `keys`, `exists`, `scan`

These are **protocol stubs** (expected pattern for dependency injection — the real Redis client implements these). The store class itself has full implementations using these protocol methods.

**Key Schema**: `ipa:conv:{session_id}:messages`, `ipa:conv:session:{session_id}`, `ipa:conv:{session_id}:turns`, `ipa:conv:user:{user_id}:sessions`

### 4.5 `postgres_store.py` (542 lines) — PostgreSQL Implementation

**Class**: `PostgresConversationMemoryStore(ConversationMemoryStore)` — 18 methods

**Protocol**: `DatabaseSessionProtocol` with 3 empty stub methods (L35-L37):
- `execute`, `fetch_all`, `fetch_one`

Again, these are protocol stubs for dependency injection. The store class has full SQL-based implementations using raw SQL queries (not SQLAlchemy ORM — **potential code standards violation**).

---

## 5. Sub-Module: `planning/` (Dynamic Planning & Decision Engine)

**Purpose**: Intelligent task decomposition, dynamic planning, autonomous decision-making, and trial-and-error learning.
**LOC**: 3,151 (task_decomposer: 791, dynamic_planner: 748, decision_engine: 724, trial_error: 888)
**Sprint**: S10 (42 story points across 4 user stories)
**Feature Mapping**: A8 (Dynamic Planning)

### 5.1 `task_decomposer.py` (791 lines)

**Enums**: `TaskPriority` (4: CRITICAL/HIGH/MEDIUM/LOW), `TaskStatus` (6: PENDING/READY/IN_PROGRESS/COMPLETED/FAILED/BLOCKED), `DependencyType` (4: FINISH_TO_START/START_TO_START/FINISH_TO_FINISH/DATA_DEPENDENCY), `DecompositionStrategy` (4: HIERARCHICAL/SEQUENTIAL/PARALLEL/HYBRID)

**Protocols**: `LLMServiceProtocol` (async generate), `AgentRegistryProtocol` (get_agent_capabilities, find_agents_by_capability)

**Data Classes**:
- `SubTask`: Task with ID, name, priority, status, dependencies, estimated_duration, assigned_agent
- `DecompositionResult`: Contains subtasks list, strategy used, confidence score, execution_order

**Class**: `TaskDecomposer` — 15 methods

| Method | Line | Description |
|--------|------|-------------|
| `__init__` | L226 | Initialize with optional LLM service and agent registry |
| `decompose` | L255 | Main entry: decompose task using selected strategy |
| `_decompose_hierarchical` | L300 | Hierarchical decomposition via LLM |
| `_decompose_sequential` | L323 | Sequential task chain |
| `_decompose_parallel` | L351 | Parallel-capable decomposition |
| `_decompose_hybrid` | L376 | Combines sequential+parallel |
| `_build_decomposition_prompt` | L427 | Build LLM prompt for decomposition |
| `_parse_decomposition_result` | L461 | Parse LLM JSON response to SubTask list |
| `_extract_tasks_from_text` | L518 | Fallback: extract tasks from unstructured text |
| `_rule_based_decomposition` | L537 | Rule-based fallback when no LLM available |
| `_analyze_execution_order` | L578 | Topological sort for dependency ordering |
| `_estimate_total_duration` | L626 | Sum task durations considering parallelism |
| `_calculate_confidence` | L655 | Confidence scoring based on decomposition quality |
| `refine_decomposition` | L701 | Refine based on feedback |
| `get_task_by_id` | L755 | Lookup task in results |
| `update_task_status` | L763 | Update task status across all results |

**Business Logic**:
- 4 decomposition strategies with LLM-powered analysis
- Automatic dependency detection and topological ordering
- Confidence scoring for decomposition quality
- Rule-based fallback when LLM is unavailable
- Refinement loop based on execution feedback

### 5.2 `dynamic_planner.py` (748 lines)

**Enums**: `PlanStatus` (7: DRAFT/APPROVED/EXECUTING/PAUSED/COMPLETED/FAILED/REPLANNING), `PlanEvent` (events for plan lifecycle)

**Protocols**: `LLMServiceProtocol`, `DecisionEngineProtocol`

**Data Classes**:
- `PlanAdjustment`: Adjustment record with type, reason, approval status
- `ExecutionPlan`: Full plan with tasks, status, progress, adjustments

**Class**: `DynamicPlanner` — 20 methods

| Method | Line | Description |
|--------|------|-------------|
| `__init__` | L187 | Initialize with TaskDecomposer, LLM, DecisionEngine |
| `create_plan` | L225 | Create plan from task description using decomposition |
| `approve_plan` | L266 | Transition plan DRAFT -> APPROVED |
| `execute_plan` | L287 | Execute approved plan phase-by-phase |
| `_execute_phase` | L360 | Execute a single phase of tasks |
| `_update_progress` | L416 | Update plan progress percentage |
| `_should_replan` | L421 | Determine if replanning is needed |
| `_replan` | L451 | Generate and apply plan adjustments |
| `_analyze_situation` | L507 | LLM-based situation analysis |
| `_apply_adjustment` | L551 | Apply approved adjustment to plan |
| `_start_monitoring` | L588 | Start progress monitoring loop |
| `_stop_monitoring` | L603 | Stop monitoring |
| `_emit_event` | L609 | Event emission |
| `on_event` / `off_event` | L625/L639 | Event handler management |
| `pause_plan` / `resume_plan` | L649/L659 | Plan pause/resume |
| `approve_adjustment` | L674 | Approve a pending plan adjustment |
| `get_plan` / `get_plan_status` | L697/L701 | Plan retrieval |
| `list_plans` | L726 | List all plans with filters |
| `delete_plan` | L742 | Delete a plan |

**Business Logic**:
- Plan lifecycle: DRAFT -> APPROVED -> EXECUTING -> (REPLANNING -> EXECUTING) -> COMPLETED/FAILED
- Automatic replanning on task failures (configurable threshold)
- Human approval workflow for plan adjustments
- Phase-based execution with progress tracking
- Event-driven notification system
- Integration with TaskDecomposer for plan creation

### 5.3 `decision_engine.py` (724 lines)

**Enums**: `DecisionType` (5: ROUTING/RESOURCE/ERROR_HANDLING/PRIORITY/ESCALATION), `DecisionConfidence` (4: HIGH/MEDIUM/LOW/UNCERTAIN)

**Data Classes**:
- `DecisionOption`: Option with pros, cons, risk_score, benefit_score
- `Decision`: Final decision with chosen option, confidence, explanation
- `DecisionRule`: Custom rule with condition function and action

**Class**: `AutonomousDecisionEngine` — 16 methods

| Method | Line | Description |
|--------|------|-------------|
| `__init__` | L172 | Initialize with LLM, confidence threshold, max history |
| `_init_default_rules` | L199 | Setup 3 default decision rules |
| `make_decision` | L228 | Main entry: evaluate situation and decide |
| `_format_decision_result` | L303 | Format decision output |
| `_expand_options` | L322 | LLM-based option expansion |
| `_evaluate_options` | L395 | Score options on pros/cons/risks |
| `_select_best_option` | L432 | Select highest-scoring option |
| `_calculate_confidence` | L474 | Compute decision confidence level |
| `_generate_explanation` | L507 | LLM-based decision explanation |
| `_generate_mitigations` | L553 | Generate risk mitigations |
| `explain_decision` | L578 | Explain a past decision |
| `add_rule` | L601 | Add custom decision rule |
| `remove_rule` | L613 | Remove rule by name |
| `get_decision_history` | L621 | Retrieve past decisions |
| `clear_history` | L639 | Clear decision history |
| `get_statistics` | L646 | Decision engine statistics |

**Business Logic**:
- Multi-option evaluation with pros/cons analysis
- Risk assessment and confidence calculation
- Decision explainability via LLM
- Custom rule engine (3 default rules: auto-retry errors, escalate high-risk, escalate repeated failures)
- Decision history tracking for learning

### 5.4 `trial_error.py` (888 lines)

**Enums**: `TrialStatus` (5: PENDING/RUNNING/SUCCESS/FAILURE/TIMEOUT), `LearningType` (4: PARAMETER_TUNING/STRATEGY_SWITCH/ERROR_PATTERN/SUCCESS_PATTERN)

**Data Classes**:
- `Trial`: Individual trial with parameters, result, duration
- `LearningInsight`: Extracted learning with type, description, confidence
- `ErrorPattern`: Recognized error pattern
- `KnownFix`: Known fix for an error pattern with success rate tracking

**Class**: `TrialAndErrorEngine` — ~18 methods

| Method | Line | Description |
|--------|------|-------------|
| `__init__` | L179 | Initialize with LLM, max_retries (3), learning enabled |
| `execute_with_retry` | ~L210 | Execute task with automatic retry |
| `_execute_single_trial` | ~L260 | Execute one trial attempt |
| `_adjust_parameters` | ~L310 | Adaptive parameter adjustment |
| `_analyze_failure` | ~L360 | LLM-based failure analysis |
| `_find_known_fix` | ~L400 | Match error against known fixes |
| `_apply_known_fix` | ~L430 | Apply a known fix |
| `_learn_from_trial` | ~L470 | Extract learning from trial outcome |
| `_record_error_pattern` | ~L520 | Record new error pattern |
| `_record_success_pattern` | ~L560 | Record success pattern |
| `_generate_insights` | ~L600 | Generate learning insights via LLM |
| `get_trial_history` | ~L650 | Retrieve trial history |
| `get_error_patterns` | ~L680 | Get recognized error patterns |
| `get_known_fixes` | ~L710 | Get known fixes |
| `get_learning_insights` | ~L740 | Get learning insights |
| `get_statistics` | ~L780 | Engine statistics |
| `clear_history` | ~L830 | Clear trial history |
| `export_learnings` | ~L860 | Export all learnings |

**Business Logic**:
- Automatic retry with adaptive parameter adjustment
- Error pattern recognition and known-fix application
- Success pattern learning for optimization
- Parameter effectiveness analysis
- LLM-powered failure analysis and insight extraction

---

## 6. Sub-Module: `nested/` (Nested Workflow Orchestration)

**Purpose**: Manages nested/recursive workflow structures with context propagation, composition patterns, and sub-workflow execution.
**LOC**: 3,954 (workflow_manager: 956, sub_executor: 614, recursive_handler: 683, composition_builder: 783, context_propagation: 918)
**Sprint**: S11 (Nested Workflows & Advanced Orchestration)
**Feature Mapping**: A9 (Nested Workflow)

### 6.1 `workflow_manager.py` (956 lines)

**Enums**: `NestedWorkflowType` (4: INLINE/REFERENCE/DYNAMIC/RECURSIVE), `WorkflowScope` (4 scopes)

**Protocols**: `WorkflowServiceProtocol` (get_workflow), `ExecutionServiceProtocol` (execute_workflow, execute_workflow_definition, cancel_execution)

**Data Classes**:
- `NestedWorkflowConfig`: Configuration with max_depth, timeout, scope, propagation type
- `SubWorkflowReference`: Reference to a sub-workflow with input/output mappings
- `NestedExecutionContext`: Execution context with parent/child tracking, depth, variables

**Class**: `NestedWorkflowManager` — 20 methods

| Method | Line | Description |
|--------|------|-------------|
| `__init__` | L238 | Initialize with workflow/execution services, max_global_depth (10) |
| `register_sub_workflow` | L272 | Register sub-workflow with cycle detection |
| `unregister_sub_workflow` | L321 | Remove sub-workflow registration |
| `get_sub_workflows` | L358 | List registered sub-workflows |
| `_has_cycle` | L379 | DFS-based cycle detection in workflow graph |
| `get_dependency_chain` | L410 | Build dependency chain for a workflow |
| `execute_sub_workflow` | L446 | Execute a registered sub-workflow |
| `_execute_by_type` | L536 | Dispatch by workflow type |
| `_execute_reference_workflow` | L560 | Execute referenced workflow |
| `_execute_inline_workflow` | L584 | Execute inline-defined workflow |
| `_execute_dynamic_workflow` | L616 | Execute dynamically generated workflow |
| `_execute_recursive_workflow` | L655 | Execute recursive workflow |
| `_create_child_context` | L684 | Create child execution context with propagation |
| `_map_outputs` | L724 | Map child outputs to parent context |
| `get_execution_tree` | L743 | Build execution tree visualization |
| `get_active_executions` | L781 | List currently running executions |
| `cancel_nested_execution` | L801 | Cancel execution and all children |
| `clear_completed_executions` | L852 | Cleanup completed executions |
| `on_event` / `_emit_event` | L886/L904 | Event system |
| `get_statistics` | L921 | Execution statistics |

**Business Logic**:
- Workflow hierarchy management with max depth enforcement (default 10)
- DFS-based cycle detection to prevent infinite loops
- 4 execution types: reference, inline, dynamic, recursive
- Parent-child context propagation
- Output mapping between workflow levels
- Cancellation cascading to child workflows

### 6.2 `sub_executor.py` (614 lines)

**Enums**: `SubWorkflowExecutionMode` (4: SYNC/ASYNC/FIRE_AND_FORGET/CALLBACK)

**Protocols**: `WorkflowEngineProtocol` (execute), `CheckpointServiceProtocol` (save_checkpoint)

**Data Classes**: `SubExecutionState` — tracks execution ID, status, result, timing

**Class**: `SubWorkflowExecutor` — 14 methods

| Method | Line | Description |
|--------|------|-------------|
| `__init__` | L128 | Initialize with engine, checkpoint service, concurrency limit |
| `execute` | L162 | Execute sub-workflow in specified mode |
| `_execute_sync` | L239 | Synchronous blocking execution |
| `_execute_async` | L293 | Asynchronous non-blocking execution |
| `_execute_fire_forget` | L309 | Fire-and-forget execution |
| `_execute_with_callback` | L326 | Callback-based execution |
| `execute_parallel` | L349 | Execute multiple sub-workflows in parallel |
| `execute_sequential` | L389 | Execute sub-workflows sequentially |
| `get_execution_status` | L441 | Get status of an execution |
| `wait_for_completion` | L462 | Wait for execution with timeout |
| `cancel_execution` | L493 | Cancel a running execution |
| `get_active_executions` | L527 | List active executions |
| `get_all_executions` | L539 | List all executions with filters |
| `clear_completed` | L569 | Remove completed executions |
| `get_statistics` | L604 | Execution statistics |

**Business Logic**: 4 execution modes (sync, async, fire-and-forget, callback), parallel/sequential batch execution, checkpointing support.

### 6.3 `recursive_handler.py` (683 lines)

**Enums**: `RecursionStrategy` (3: DEPTH_FIRST/BREADTH_FIRST/PARALLEL), `TerminationType` (5: MAX_DEPTH/CONVERGENCE/CONDITION/TIMEOUT/MANUAL)

**Data Classes**: `RecursionConfig` (max_depth, strategy, termination, convergence_threshold, memoization), `RecursionState` (current_depth, iteration_count, converged, memo_cache)

**Class**: `RecursivePatternHandler` — 18 methods

| Method | Line | Description |
|--------|------|-------------|
| `__init__` | L161 | Initialize with default config |
| `execute_recursive` | L186 | Main entry: execute recursive workflow |
| `_recursive_execute` | L241 | Core recursive logic with memoization |
| `_execute_iteration` | L319 | Execute one iteration |
| `_execute_depth_first` | L342 | DFS execution strategy |
| `_execute_breadth_first` | L364 | BFS execution strategy |
| `_execute_parallel` | L401 | Parallel branch execution |
| `_check_termination` | L436 | Check all termination conditions |
| `_check_convergence` | L470 | Detect result convergence |
| `_calculate_diff` | L502 | Calculate difference between iterations |
| `_should_continue` | L524 | Combined continuation check |
| `_generate_memo_key` | L551 | Generate memoization key |
| `_build_termination_result` | L559 | Build result when termination reached |
| `_merge_results` | L576 | Merge results from parallel branches |
| `abort` | L616 | Abort all active recursions |
| `get_recursion_stats` | L627 | Stats for a specific recursion |
| `get_history` | L641 | Get recursion execution history |
| `clear_completed` | L656 | Clean up completed recursions |
| `get_statistics` | L669 | Overall statistics |

**Business Logic**: 3 recursion strategies, 5 termination types, memoization for repeated inputs, convergence detection for iterative refinement, stack overflow protection via max_depth.

### 6.4 `composition_builder.py` (783 lines)

**Enums**: `CompositionType` (5: SEQUENCE/PARALLEL/CONDITIONAL/LOOP/SWITCH)

**Data Classes**: `WorkflowNode` (node in composition graph), `CompositionBlock` (block containing nodes)

**Class**: `WorkflowCompositionBuilder` — 22 methods (fluent API)

| Method | Line | Description |
|--------|------|-------------|
| `__init__` | L156 | Initialize builder with empty stack |
| `sequence` | L173 | Start sequential composition block |
| `parallel` | L193 | Start parallel composition block |
| `conditional` | L213 | Start conditional branch block |
| `loop` | L239 | Start loop block with condition |
| `switch` | L270 | Start switch/case block |
| `case` | L300 | Add case to switch block |
| `default` | L323 | Add default case |
| `add_workflow` | L343 | Add workflow reference node |
| `add_inline` | L381 | Add inline workflow definition |
| `add_task` | L419 | Add task node |
| `end` | L457 | End current block |
| `_push_block` / `_pop_block` | L470/L480 | Stack management |
| `_add_node` | L487 | Add node to current block |
| `build` | L509 | Build final composition |
| `validate` | L530 | Validate composition structure |
| `_validate_block` | L554 | Recursive block validation |
| `reset` | L584 | Reset builder state |
| `create_map_reduce` | L604 | Convenience: map-reduce pattern |
| `create_pipeline` | L645 | Convenience: pipeline pattern |
| `create_scatter_gather` | L676 | Convenience: scatter-gather pattern |
| `create_retry_pattern` | L713 | Convenience: retry pattern |
| `create_saga` | L745 | Convenience: saga pattern |

**Business Logic**: Fluent builder API for workflow composition with 5 composition types. Includes 5 pre-built patterns (map-reduce, pipeline, scatter-gather, retry, saga). Stack-based block nesting with validation.

### 6.5 `context_propagation.py` (918 lines)

**Enums**: `PropagationType` (4: COPY/REFERENCE/MERGE/FILTER), `VariableScopeType` (4), `DataFlowDirection` (3: DOWNSTREAM/UPSTREAM/BIDIRECTIONAL)

**Data Classes**: `VariableDescriptor`, `PropagationRule`, `DataFlowEvent`

**Classes**:

| Class | Line | Methods | Description |
|-------|------|---------|-------------|
| `VariableScope` | L179 | 9 methods | Variable visibility and lifecycle tracking |
| `ContextPropagator` | L405 | 10 methods | Context flow between parent/child workflows |
| `DataFlowTracker` | L675 | 10 methods | Data flow monitoring through workflow hierarchy |

**VariableScope Methods**: `__init__`, `set`, `get`, `get_descriptor`, `delete`, `exists`, `list_variables`, `create_child_scope`, `to_dict`

**ContextPropagator Methods**: `__init__`, `add_rule`, `block_key`, `map_key`, `propagate_downstream`, `propagate_upstream`, `_find_rule`, `_apply_rule`, `create_child_context`, `merge_child_results`

**DataFlowTracker Methods**: `__init__`, `record_flow`, `get_events`, `get_variable_history`, `get_workflow_flow`, `get_workflow_children`, `get_variable_sources`, `build_dependency_graph`, `get_statistics`, `clear`

**Business Logic**:
- 4 propagation strategies (COPY: isolated, REFERENCE: shared, MERGE: combined, FILTER: selective)
- Key blocking and mapping for context transformation
- Bidirectional propagation (downstream to children, upstream to parent)
- Variable scope hierarchy with parent scope resolution
- Data flow event tracking for debugging/audit
- Dependency graph construction from flow events

---

## 7. Empty/Stub Methods Analysis

**Total empty/stub methods found: 30**

| File | Count | Type | Assessment |
|------|-------|------|------------|
| `memory/base.py` | 17 | Abstract methods (`pass`) | **Expected** — ABC pattern, all implemented by 3 subclasses |
| `memory/redis_store.py` | 10 | Protocol stubs (empty body) | **Expected** — `RedisClientProtocol` for DI |
| `memory/postgres_store.py` | 3 | Protocol stubs (empty body) | **Expected** — `DatabaseSessionProtocol` for DI |

**Assessment**: All 30 empty methods are **intentional design patterns** (abstract methods and protocol stubs). There are **no accidental empty implementations** or TODO stubs in this module. The AST scan that reported 43 empty functions may have counted differently or included `__init__.py` files.

---

## 8. Cross-Module Dependencies

```
planning/dynamic_planner.py
    └── imports from planning/task_decomposer.py (TaskDecomposer, DecompositionResult, SubTask, TaskStatus)

planning/decision_engine.py
    └── standalone (uses LLMServiceProtocol)

planning/trial_error.py
    └── standalone (uses LLMServiceProtocol)

memory/in_memory.py, redis_store.py, postgres_store.py
    └── all import from memory/base.py (ConversationMemoryStore)
    └── all import from memory/models.py (ConversationSession, ConversationTurn, etc.)

nested/ sub-modules
    └── mostly standalone, use Protocol-based DI
    └── no direct imports between nested files

multiturn/ sub-modules
    └── mostly standalone, no cross-imports between files
```

**External Dependencies**: Only standard library + internal protocols. No third-party imports (Redis/Postgres clients injected via protocols).

---

## 9. State Management Summary

| Component | Storage | Persistence | State Tracking |
|-----------|---------|-------------|----------------|
| MultiTurnSessionManager | In-memory Dict | None | Session lifecycle (7 states) |
| TurnTracker | In-memory Dict | None | Turn lifecycle (5 states) |
| SessionContextManager | In-memory Dict | Serializable (to_dict/from_dict) | 4 scope levels |
| ConversationMemoryStore | Pluggable (memory/Redis/Postgres) | Yes (Redis/Postgres) | Session status (5 states) |
| TaskDecomposer | In-memory Dict | None | Task status (6 states) |
| DynamicPlanner | In-memory Dict | None | Plan lifecycle (7 states) |
| AutonomousDecisionEngine | In-memory list | None | Decision history |
| TrialAndErrorEngine | In-memory lists | None | Trial history + learned patterns |
| NestedWorkflowManager | In-memory Dict | None | Execution tree with depth tracking |
| SubWorkflowExecutor | In-memory Dict | None | Execution states per sub-workflow |
| RecursivePatternHandler | In-memory Dict | None | Recursion state with memoization |
| WorkflowCompositionBuilder | Stack-based | None | Builder state (reset on build) |
| VariableScope | In-memory Dict | None | Variable descriptors with scoping |
| ContextPropagator | In-memory rules | None | Propagation rules |
| DataFlowTracker | In-memory lists | None | Flow events with dependency graph |

**Critical Observation**: Only the memory sub-module offers persistent storage (via Redis/Postgres). All other components use **in-memory state only**, which means all planning, nested workflow, and multiturn session state is **lost on restart**.

---

## 10. Problems and Findings

### 10.1 Architectural Concerns

1. **Deprecation without removal**: The entire module is deprecated but still actively imported by API routes. This creates maintenance burden and confusion.

2. **Dual implementations**: Both the domain layer and adapter layer contain similar functionality, leading to code duplication.

3. **No persistent state for planning/nested**: All planning, decision, trial-and-error, and nested workflow state is in-memory only. Production use would lose all state on restart.

4. **Raw SQL in postgres_store.py**: Uses raw SQL queries instead of SQLAlchemy ORM, violating the project's code standards that mandate ORM usage.

### 10.2 Quality Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| Code completeness | HIGH | All classes fully implemented, no TODO stubs |
| Documentation | HIGH | Bilingual docstrings (English + Traditional Chinese) |
| Type hints | HIGH | Comprehensive typing throughout |
| Error handling | MEDIUM | Basic try/except, could be more granular |
| Test coverage | UNKNOWN | Tests exist in separate test directory |
| Protocol usage | HIGH | Clean dependency injection via Protocol classes |

### 10.3 Empty Methods Clarification

The 30 empty methods found are all **intentional design patterns**:
- 17 abstract methods in `ConversationMemoryStore` (ABC)
- 10 protocol stubs in `RedisClientProtocol`
- 3 protocol stubs in `DatabaseSessionProtocol`

**No accidental stubs or incomplete implementations were found.**

---

## 11. Feature Mapping Cross-Reference

### A8: Dynamic Planning
- **TaskDecomposer**: 4 strategies (hierarchical/sequential/parallel/hybrid), LLM-powered with rule-based fallback
- **DynamicPlanner**: Plan lifecycle management with auto-replanning
- **AutonomousDecisionEngine**: Multi-option evaluation with explainability
- **TrialAndErrorEngine**: Adaptive retry with pattern learning
- **Status**: Fully implemented at domain level, wrapped by PlanningAdapter

### A9: Nested Workflow
- **NestedWorkflowManager**: Workflow hierarchy with cycle detection
- **SubWorkflowExecutor**: 4 execution modes (sync/async/fire-forget/callback)
- **RecursivePatternHandler**: 3 strategies (DFS/BFS/parallel), memoization, convergence
- **WorkflowCompositionBuilder**: Fluent API with 5 patterns (map-reduce/pipeline/scatter-gather/retry/saga)
- **ContextPropagator + DataFlowTracker**: 4 propagation types, dependency graph
- **Status**: Fully implemented at domain level, wrapped by NestedWorkflowAdapter
