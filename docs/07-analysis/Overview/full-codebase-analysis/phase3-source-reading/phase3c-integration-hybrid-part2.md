# Phase 3C: Hybrid Integration Layer — Part 2 Analysis

> **Scope**: `backend/src/integrations/hybrid/` — switching/, checkpoint/, execution/, claude_maf_fusion.py, swarm_mode.py
> **Agent**: C4 | **Date**: 2026-03-15

---

## 1. Module Inventory

| Subdirectory | Files | Key Classes | Sprint |
|---|---|---|---|
| `switching/` | 12 .py | ModeSwitcher, StateMigrator, 4 TriggerDetectors | S56 |
| `switching/redis_checkpoint.py` | 1 .py | RedisSwitchCheckpointStorage | S120 |
| `checkpoint/` | 10 .py | HybridCheckpoint, UnifiedCheckpointStorage, CheckpointSerializer, CheckpointVersionMigrator, 4 backends | S57 |
| `execution/` | 5 .py | UnifiedToolExecutor, ToolRouter, ResultHandler, MAFToolCallback | S54 |
| `claude_maf_fusion.py` | 1 .py | ClaudeMAFFusion, ClaudeDecisionEngine, DynamicWorkflow | S81 |
| `swarm_mode.py` | 1 .py | HybridSwarmMode, SwarmTaskRouter, SwarmCheckpointManager | S104 |

**Total files in scope**: 30 .py files

---

## 2. Mode Switching (`switching/`)

### 2.1 Architecture

```
User Input + ExecutionState
        |
  TriggerDetectors (priority-ordered)
  ├── UserRequestTriggerDetector  (explicit commands)
  ├── FailureTriggerDetector      (consecutive failures)
  ├── ResourceTriggerDetector     (token/memory/time)
  └── ComplexityTriggerDetector   (keyword + step analysis)
        |
  ModeSwitcher.should_switch() → SwitchTrigger (or None)
        |
  ModeSwitcher.execute_switch()
  ├── 1. Create SwitchCheckpoint (rollback point)
  ├── 2. StateMigrator.migrate() (state transformation)
  ├── 3. Initialize target mode
  ├── 4. Validate switch
  └── 5. Update ContextBridge
        |
  SwitchResult (success/fail + rollback ID)
```

### 2.2 Trigger Detectors

All four detectors extend `BaseTriggerDetector` (ABC) which implements the `TriggerDetectorProtocol`. BaseTriggerDetector provides:
- Configurable enable/disable, priority, min_confidence, cooldown
- Abstract `_detect_trigger()` method (subclasses implement)
- Concrete `detect()` wrapping with cooldown enforcement and error handling

| Detector | Config Class | Key Thresholds | Switching Direction |
|---|---|---|---|
| **ComplexityTriggerDetector** | `ComplexityConfig` | `step_threshold=3`, `tool_threshold=5`, keyword lists for multi-step/workflow/chat | Chat→Workflow when complexity high; Workflow→Chat when simple |
| **FailureTriggerDetector** | `FailureConfig` | `failure_threshold=3`, `recovery_window_seconds=300`, `base_confidence=0.6` | Current→opposite mode after N consecutive failures |
| **ResourceTriggerDetector** | `ResourceConfig` | `token_threshold=0.8`, `memory_threshold=0.85`, `context_threshold=0.9`, `time_threshold_seconds=600` | Claude→MAF when token/context limits hit; MAF→Claude when memory high |
| **UserRequestTriggerDetector** | `UserRequestConfig` | Phrase lists for workflow/chat, `explicit_command_prefix="/mode"` | Per user request, confidence 0.95 (explicit) or 0.7 (implicit) |

**Legitimate abstract methods**: `BaseTriggerDetector._detect_trigger()` is abstract and correctly implemented by all four concrete subclasses. No empty stubs.

### 2.3 ModeSwitcher Core (switcher.py, 837 LOC)

**Protocols defined** (all legitimate structural typing):
- `TriggerDetectorProtocol`: `detect(current_mode, state, new_input) → Optional[SwitchTrigger]`
- `StateMigratorProtocol`: `migrate(context, source_mode, target_mode) → MigratedState`
- `CheckpointStorageProtocol`: `save_checkpoint()`, `get_checkpoint()`, `delete_checkpoint()`
- `ContextBridgeProtocol`: `get_context()`, `update_context()`

**`should_switch()`**: Iterates detectors in order, returns first high-confidence trigger. Returns None if auto-switch disabled.

**`execute_switch()`**: 5-step process (checkpoint → migrate → init target → validate → update context). On validation failure, auto-rollbacks. Records metrics (SwitcherMetrics) and transition history (ModeTransition).

**`rollback_switch()`**: Restores context from SwitchCheckpoint snapshot via ContextBridge. Records rollback in metrics and transition history with `rollback_of` reference.

**`manual_switch()`**: Creates a MANUAL trigger with confidence=1.0, delegates to execute_switch.

### 2.4 State Migration (`switching/migration/state_migrator.py`)

**StateMigrator** handles bidirectional state transformation:

| Direction | What's Preserved | Key Transformations |
|---|---|---|
| Chat→Workflow | Conversation history, tool results | Messages → workflow steps, tool calls → step inputs |
| Workflow→Chat | Step results, workflow variables | Steps → conversation messages, variables → context |
| Chat→Hybrid / Workflow→Hybrid | Both sides | Merges into unified HybridContext |
| Hybrid→Chat / Hybrid→Workflow | Relevant subset | Extracts framework-specific state |

**MigrationConfig**: `preserve_history=True`, `preserve_tool_results=True`, `max_history_items=50`, `transform_variables=True`.

**MigrationValidator**: Validates migrated state has required fields, checks data integrity, warns on data loss.

**MigrationError**: Custom exception for migration failures.

### 2.5 Redis Checkpoint Storage (redis_checkpoint.py, S120)

`RedisSwitchCheckpointStorage` replaces `InMemoryCheckpointStorage` for production:
- Key format: `switch_checkpoint:{id}` for data, `switch_checkpoint:session:{session_id}` (Redis Set) for per-session index
- TTL: 24 hours default
- Thread-safe via `asyncio.Lock`
- Cleans stale index entries on `list_checkpoints()`

### 2.6 Data Models (`switching/models.py`)

Rich dataclass hierarchy:
- **SwitchTriggerType**: COMPLEXITY, USER_REQUEST, FAILURE, RESOURCE, TIMEOUT, MANUAL
- **SwitchStatus**: PENDING, IN_PROGRESS, COMPLETED, FAILED, ROLLED_BACK
- **MigrationDirection**: 6 directions (all combinations of WORKFLOW, CHAT, HYBRID)
- **SwitchTrigger**: trigger_type, source_mode, target_mode, confidence, reason
- **SwitchResult**: success, status, trigger, migrated_state, checkpoint_id, validation, timing
- **ModeTransition**: Full audit record with rollback_of reference
- **SwitchCheckpoint**: context_snapshot dict + mode_before for rollback
- **ExecutionState**: Session metrics (failures, steps, messages, tool calls, resource usage)

All models have `to_dict()`/`from_dict()` serialization. No empty stubs.

---

## 3. Unified Checkpoint (`checkpoint/`)

### 3.1 Architecture

```
UnifiedCheckpointStorage
  ├── CheckpointSerializer (JSON + compression)
  ├── CheckpointVersionMigrator (v1→v2 upgrade)
  └── Backend (one of):
      ├── MemoryCheckpointStorage (dev/test)
      ├── RedisCheckpointStorage (distributed)
      ├── PostgresCheckpointStorage (durable)
      └── FilesystemCheckpointStorage (local)
```

### 3.2 HybridCheckpoint Model (checkpoint/models.py)

```python
@dataclass
class HybridCheckpoint:
    checkpoint_id: str
    session_id: str
    checkpoint_type: CheckpointType        # MANUAL, AUTO, PRE_SWITCH, ERROR_RECOVERY
    status: CheckpointStatus               # CREATED, ACTIVE, RESTORED, EXPIRED, DELETED
    version: int = 2                       # Format version for migration
    maf_state: Optional[MAFCheckpointState]      # Workflow steps, variables, agent state
    claude_state: Optional[ClaudeCheckpointState] # Messages, tool calls, tokens
    risk_snapshot: Optional[RiskSnapshot]         # Risk level at checkpoint time
    metadata: Dict[str, Any]
    created_at: datetime
    expires_at: Optional[datetime]
    compression: CompressionAlgorithm      # NONE, ZLIB, GZIP
```

**MAFCheckpointState**: workflow_id, current_step, completed_steps, variables, agent_states, pending_actions.

**ClaudeCheckpointState**: conversation_id, messages, tool_calls, token_usage, model_config.

**RestoreResult**: Returned by restore operations with success, restored checkpoint, warnings.

### 3.3 CheckpointSerializer (serialization.py)

- **Serialize**: `HybridCheckpoint → JSON string → optional compression → checksum`
- **Deserialize**: `verify checksum → decompress → JSON parse → HybridCheckpoint`
- **Compression**: Supports ZLIB (default) and GZIP. Configurable level (1-9).
- **Checksum**: SHA-256 integrity validation.
- **SerializationConfig**: compression_algorithm, compression_level, enable_checksum, max_uncompressed_size_bytes.
- **SerializationResult**: data bytes, checksum, original_size, compressed_size, compression_ratio.

### 3.4 CheckpointVersionMigrator (version.py)

**Version history**:
- **V1** (Sprint 52-54): Separate MAF and Claude checkpoints
- **V2** (Sprint 57): Unified HybridCheckpoint

**Migration chain**: Registers per-version migration functions. Applies sequentially: v1→v2.

**V1→V2 migration**: Merges separate `maf_checkpoint` and `claude_checkpoint` dicts into unified `maf_state`/`claude_state` fields. Adds `checkpoint_type`, `status`, `version=2`, `risk_snapshot`.

**MigrationResult**: success, original_version, target_version, warnings, migrated_data.

**Downgrade**: Not supported (forward-only migration).

### 3.5 UnifiedCheckpointStorage (storage.py)

**StorageConfig**: backend enum, ttl_seconds (86400), max_checkpoints_per_session (10), enable_compression, cleanup_interval_seconds.

**CheckpointQuery**: Filter by session_id, checkpoint_type, status, time range, limit/offset.

**Core operations**:
- `save_checkpoint(checkpoint)`: Serializes via CheckpointSerializer, delegates to backend
- `load_checkpoint(checkpoint_id)`: Loads from backend, deserializes, migrates version if needed
- `restore_checkpoint(checkpoint_id)`: Load + apply to current context
- `delete_checkpoint(checkpoint_id)`: Remove from backend
- `query_checkpoints(query)`: Filter/search checkpoints
- `cleanup_expired()`: Remove expired checkpoints

**StorageError**: Custom exception with error code and context.

**StorageStats**: total_checkpoints, total_size_bytes, by_status counts, by_backend info.

### 3.6 Storage Backends

| Backend | File | Key Features | Production Ready |
|---|---|---|---|
| **MemoryCheckpointStorage** | backends/memory.py | Dict-based, fast, no persistence | No (dev/test only) |
| **RedisCheckpointStorage** | backends/redis.py | TTL expiration, per-session index (Set), asyncio.Lock | Yes |
| **PostgresCheckpointStorage** | backends/postgres.py | SQLAlchemy async, JSONB storage, indexed queries | Yes |
| **FilesystemCheckpointStorage** | backends/filesystem.py | JSON files in directory tree, session subdirectories | Partial (single-node) |

All backends implement `CheckpointStorageProtocol`:
- `save(checkpoint_id, data) → str`
- `load(checkpoint_id) → Optional[bytes]`
- `delete(checkpoint_id) → bool`
- `list_by_session(session_id) → List[str]`
- `cleanup_expired() → int`

**No empty stubs** — all backends have full implementations.

---

## 4. Unified Execution (`execution/`)

### 4.1 Architecture

```
Tool Call (from MAF or Claude)
        |
  MAFToolCallback (intercepts MAF tool calls)
        |
  UnifiedToolExecutor
  ├── Pre-hooks: approval, audit, rate-limit, sandbox
  ├── ToolRouter.route() → determine framework
  ├── Execute via framework (MAF kernel or Claude tool_use)
  ├── Post-hooks: logging, metrics
  └── ResultHandler.normalize() → unified format
        |
  ToolExecutionResult (unified)
```

### 4.2 UnifiedToolExecutor (unified_executor.py, 797 LOC)

**ToolSource enum**: MAF, CLAUDE, HYBRID — identifies origin of tool call.

**ToolExecutionResult**: success, content, error, tool_name, execution_id, source, duration_ms, blocked_by_hook, approval_denied, metadata.

**Hook pipeline**:
- Pre-execution hooks run in order; any can block execution (e.g., approval denied)
- Tool execution via registered executor function
- Post-execution hooks for logging/metrics
- Hook protocol: `async (tool_name, args, context) → HookResult`

**Execution flow**:
1. Validate tool exists in registry
2. Run pre-hooks (approval, audit, rate-limit)
3. If blocked by hook, return early with `blocked_by_hook=True`
4. Execute tool via framework-specific executor
5. Run post-hooks
6. Return ToolExecutionResult

**Metrics**: Tracks total calls, success/failure counts, per-tool timing, hook block counts.

### 4.3 ToolRouter (tool_router.py)

**RoutingStrategy enum**:
- `PREFER_CLAUDE`: Default to Claude SDK execution
- `PREFER_MAF`: Default to MAF kernel execution
- `CAPABILITY_BASED`: Route based on tool registration source
- `LOAD_BALANCED`: Distribute across frameworks
- `EXPLICIT`: Use explicitly specified source

**ToolRoute dataclass**: tool_name, source, rule_applied, fallback_sources.

**ToolRouter class**:
- Maintains tool→framework registry
- `register_tool(name, source)`: Register tool with framework
- `route(tool_name, strategy)`: Determine execution framework
- `get_fallback(tool_name)`: Get alternative framework if primary fails
- Default strategy: CAPABILITY_BASED

### 4.4 ResultHandler (result_handler.py)

**ResultFormat enum**: CLAUDE, MAF, UNIFIED, JSON.

**FormattedResult**: format, data dict, original ToolExecutionResult, transformed_at.

**Key methods**:
- `to_claude_format(result)`: Convert to Claude tool_use result format
- `to_maf_format(result)`: Convert to MAF FunctionResult format
- `to_unified_format(result)`: Normalize to internal format
- `format_for_source(result, target_format)`: Dispatch to appropriate formatter

**ResultAggregator**: Collects multiple results, computes aggregate statistics (success rate, avg duration).

### 4.5 MAFToolCallback (tool_callback.py)

**Purpose**: Intercepts MAF kernel tool calls and routes them through UnifiedToolExecutor.

**CallbackConfig**:
- `intercept_all`: Whether to intercept all MAF tool calls (default True)
- `allowed_tools` / `blocked_tools`: Whitelist/blacklist
- `require_approval`: Tools needing human approval
- `default_approval_timeout`: 300 seconds
- `fallback_on_error`: Fall back to native MAF execution on error (default True)

**MAFToolCallback class**:
- `on_tool_call(function_name, arguments)`: Main interception point
- Checks if tool should be intercepted (allowed/blocked lists)
- Routes through UnifiedToolExecutor
- On error with `fallback_on_error=True`, falls back to native MAF execution
- Returns `MAFToolCallResult` (function_name, output, error, success)

**No empty abstract methods** — all methods have full implementations.

---

## 5. Claude-MAF Fusion (`claude_maf_fusion.py`)

### 5.1 Architecture (Sprint 81, 892 LOC)

Enables Claude to make **decisions at workflow branch points** within MAF workflows.

```
MAF Workflow Execution
        |
  WorkflowStep (is_decision_point=True?)
  ├── No  → Execute via MAF handler
  └── Yes → ClaudeDecisionEngine
             ├── Analyze context + step options
             ├── Claude LLM call for decision
             └── ClaudeDecision (route_selection, skip, abort, continue)
                    |
              DynamicWorkflow applies decision
              → next step determined by Claude
```

### 5.2 Key Classes

**WorkflowStep**: step_id, name, step_type (EXECUTE/DECISION), handler callable, is_decision_point, next_steps list.

**WorkflowDefinition**: workflow_id, name, steps list, entry_point.

**ClaudeDecision**: decision_id, decision_type (ROUTE_SELECTION/SKIP_STEP/ABORT/CONTINUE), selected_route, reasoning, confidence.

**ExecutionState**: execution_id, workflow_id, current_step, completed_steps, decisions list, context dict, status.

**StepResult**: step_id, success, output, error, duration_ms.

**WorkflowResult**: workflow_id, execution_id, success, step_results, decisions, total_duration_ms.

### 5.3 ClaudeDecisionEngine

- Receives workflow context + current step + available routes
- Calls Claude LLM to decide which route/action to take
- Returns ClaudeDecision with reasoning and confidence
- Decision types: select a route, skip step, abort workflow, or continue

### 5.4 DynamicWorkflow

- Manages workflow execution with Claude-augmented decision points
- Steps through WorkflowDefinition, executing handlers
- At decision points, delegates to ClaudeDecisionEngine
- Tracks execution state (completed steps, decisions made)
- Returns WorkflowResult with full audit trail

### 5.5 ClaudeMAFFusion (Main Facade)

- Orchestrates DynamicWorkflow + ClaudeDecisionEngine
- Entry point: `execute_workflow(workflow_definition, context)`
- Manages execution lifecycle: init → execute steps → handle decisions → complete
- Provides metrics on decision quality and workflow performance

---

## 6. Swarm Mode (`swarm_mode.py`)

### 6.1 Purpose (Sprint 104)

Extends hybrid orchestration to support agent swarm scenarios where multiple agents collaborate.

### 6.2 Key Classes

**HybridSwarmMode**: Coordinates swarm execution within the hybrid framework.
- Manages swarm lifecycle (create, execute, monitor, terminate)
- Integrates with ModeSwitcher for per-agent mode selection
- Uses UnifiedCheckpointStorage for swarm-level checkpoints

**SwarmTaskRouter**: Routes tasks to appropriate agents based on capability matching.
- Considers agent mode (MAF/Claude) when routing
- Supports parallel and sequential task distribution

**SwarmCheckpointManager**: Manages checkpoints for swarm operations.
- Creates aggregate checkpoints across all swarm agents
- Supports partial rollback (rollback individual agents)

---

## 7. Protocol/ABC Verification

### All Abstract Methods — Verified Legitimate

| Class | Abstract Method | Implemented By |
|---|---|---|
| `BaseTriggerDetector._detect_trigger()` | ComplexityTriggerDetector, FailureTriggerDetector, ResourceTriggerDetector, UserRequestTriggerDetector |
| `CheckpointStorageProtocol.save()` | Memory, Redis, Postgres, Filesystem backends |
| `CheckpointStorageProtocol.load()` | Memory, Redis, Postgres, Filesystem backends |
| `CheckpointStorageProtocol.delete()` | Memory, Redis, Postgres, Filesystem backends |
| `CheckpointStorageProtocol.list_by_session()` | Memory, Redis, Postgres, Filesystem backends |
| `CheckpointStorageProtocol.cleanup_expired()` | Memory, Redis, Postgres, Filesystem backends |
| `TriggerDetectorProtocol.detect()` | Protocol (structural typing), implemented by BaseTriggerDetector |
| `StateMigratorProtocol.migrate()` | Protocol (structural typing), implemented by StateMigrator |
| `CheckpointStorageProtocol` (switcher) | InMemoryCheckpointStorage, RedisSwitchCheckpointStorage |
| `ContextBridgeProtocol` | Protocol (structural typing), implemented by ContextBridge |

**No empty stubs found.** All abstract/protocol methods have concrete implementations.

---

## 8. Cross-Reference with Feature Plan

### B4: Mode Switcher
- **Status**: Fully implemented
- **Trigger detection**: 4 concrete detectors covering complexity, failure, resource, user request
- **State migration**: Bidirectional with 6 migration directions, history/tool preservation
- **Rollback**: Checkpoint-based with context restoration via ContextBridge
- **Redis storage**: Production-ready replacement (S120) for switch checkpoints
- **Audit trail**: ModeTransition records with rollback_of references

### B5: Unified Checkpoint
- **Status**: Fully implemented
- **Structure**: HybridCheckpoint with MAF + Claude states, risk snapshot, versioning
- **Version migration**: V1→V2 forward migration with CheckpointVersionMigrator
- **Serialization**: JSON + ZLIB/GZIP compression + SHA-256 integrity
- **4 backends**: Memory (dev), Redis (distributed), Postgres (durable), Filesystem (local)
- **Storage management**: TTL expiration, per-session limits, cleanup

---

## 9. Key Findings

1. **Well-architected switching**: The trigger→switch→checkpoint→rollback pipeline is complete with proper error handling and metrics.

2. **Two separate checkpoint systems**: Note there are TWO checkpoint subsystems:
   - `switching/redis_checkpoint.py` + `switching/switcher.py:InMemoryCheckpointStorage` — for **switch operation rollback** (SwitchCheckpoint)
   - `checkpoint/` — for **hybrid execution state persistence** (HybridCheckpoint)
   These serve different purposes but could cause confusion.

3. **Execution layer is framework-agnostic**: ToolRouter + UnifiedToolExecutor + ResultHandler provide clean abstraction over MAF and Claude tool systems.

4. **ClaudeMAFFusion adds AI decision-making to MAF workflows**: Novel pattern where Claude LLM acts as decision engine at workflow branch points.

5. **No thread-safety issues in this scope**: Redis backends use asyncio.Lock, in-memory backends are single-process safe. (Note: ContextSynchronizer thread-safety issue is in context/ scope, covered by C3.)

6. **All Protocol/ABC methods are legitimate**: No placeholder implementations found. Every abstract method has at least one concrete implementation.
