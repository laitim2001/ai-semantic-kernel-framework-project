# Layer 07: Claude SDK Worker Layer

## Identity

- Files: 47 | LOC: **15,406** (R4 verified via `wc -l`)
- Directory: `backend/src/integrations/claude_sdk/`
- Phase introduced: 12 (Sprint 48) | Phase last modified: 29 (Sprint 111)
- External dependency: `anthropic.AsyncAnthropic` (Anthropic Python SDK)

---

## File Inventory

| File | LOC | Purpose | Key Classes / Functions |
|------|-----|---------|------------------------|
| `__init__.py` | 95 | Package root, 41 exports | — |
| `config.py` | 76 | Configuration dataclass | `ClaudeSDKConfig`, `from_env()`, `from_yaml()` |
| `types.py` | 131 | Shared type definitions | `ToolCall`, `Message`, `ToolCallContext`, `ToolResultContext`, `QueryContext`, `HookResult`, `QueryResult`, `SessionResponse`, `ALLOW` |
| `exceptions.py` | 76 | Exception hierarchy (8 types) | `ClaudeSDKError`, `AuthenticationError`, `RateLimitError`, `TimeoutError`, `ToolError`, `HookRejectionError`, `MCPError`, `MCPConnectionError`, `MCPToolError` |
| `client.py` | 356 | Main entry point | `ClaudeSDKClient` (query, create_session, send_with_attachments, execute_with_thinking) |
| `query.py` | 345 | One-shot query execution | `execute_query()`, `execute_query_with_attachments()`, `build_content_with_attachments()` |
| `session.py` | 287 | Multi-turn conversation | `Session` (query, fork, close, agentic loop) |
| `session_state.py` | 576 | State persistence + compression + mem0 | `SessionStateManager`, `SessionState`, `SessionStateConfig` |
| **autonomous/__init__.py** | 129 | Autonomous engine exports | — |
| **autonomous/types.py** | 245 | Planning data types | `EventSeverity`, `EventComplexity`, `PlanStatus`, `StepStatus`, `RiskLevel`, `EventContext`, `AnalysisResult`, `PlanStep`, `AutonomousPlan`, `VerificationResult`, `COMPLEXITY_BUDGET_TOKENS` |
| **autonomous/analyzer.py** | 347 | Event analysis (Phase 1) | `EventAnalyzer` (analyze_event, extract_context, estimate_complexity) |
| **autonomous/planner.py** | 376 | Plan generation (Phase 2) | `AutonomousPlanner` (generate_plan, estimate_resources) |
| **autonomous/executor.py** | 398 | Plan execution (Phase 3) | `PlanExecutor`, `ExecutionEvent`, `ExecutionEventType` |
| **autonomous/verifier.py** | 354 | Result verification (Phase 4) | `ResultVerifier` (verify, verify_step, calculate_quality_score, extract_lessons) |
| **autonomous/retry.py** | 394 | Retry policy with backoff | `RetryPolicy`, `RetryConfig`, `RetryResult`, `FailureType`, `with_retry()` |
| **autonomous/fallback.py** | 588 | Smart fallback system | `SmartFallback`, `FallbackStrategy` (6 strategies), `FailureAnalysis`, `FallbackAction`, `FailurePattern` |
| **hooks/__init__.py** | 72 | Hooks sub-package exports | — |
| **hooks/base.py** | 245 | Abstract base + chain | `Hook` (ABC), `HookChain` (priority-sorted execution) |
| **hooks/approval.py** | 175 | Human-in-the-loop approval | `ApprovalHook` (priority=90) |
| **hooks/approval_delegate.py** | 275 | Unified approval bridge (Sprint 111) | `ClaudeApprovalDelegate` (delegates to UnifiedApprovalManager) |
| **hooks/sandbox.py** | 503 | File access control | `SandboxHook` (priority=85), `StrictSandboxHook`, `UserSandboxHook` |
| **hooks/rate_limit.py** | 330 | Rate + concurrency limiting | `RateLimitHook` (priority=80), `RateLimitConfig`, `RateLimitStats` |
| **hooks/audit.py** | 350 | Activity logging + redaction | `AuditHook` (priority=10), `AuditEntry`, `AuditLog` |
| **tools/__init__.py** | 48 | Tools sub-package exports | — |
| **tools/base.py** | 68 | Abstract tool base | `Tool` (ABC), `ToolResult` |
| **tools/registry.py** | 152 | Tool registration + execution | `register_tool()`, `get_tool_definitions()`, `execute_tool()`, `_register_builtin_tools()` |
| **tools/file_tools.py** | 608 | 6 file tools | `Read`, `Write`, `Edit`, `MultiEdit`, `Glob`, `Grep` |
| **tools/command_tools.py** | 345 | 2 command tools | `Bash` (security checks), `Task` (subagent delegation) |
| **tools/web_tools.py** | 487 | 2 web tools | `WebSearch` (Brave/Google/Bing), `WebFetch` (HTML text extraction) |
| **hybrid/__init__.py** | — | Hybrid sub-package exports | — |
| **hybrid/types.py** | — | Hybrid data types | `Framework`, `HybridResult`, `TaskAnalysis`, `TaskCapability`, `HybridSessionConfig` |
| **hybrid/capability.py** | — | Task-to-framework mapping | `CapabilityMatcher` |
| **hybrid/selector.py** | — | Framework selection logic | `FrameworkSelector`, `SelectionContext`, `SelectionStrategy` |
| **hybrid/orchestrator.py** | 547 | Hybrid execution coordinator | `HybridOrchestrator` (execute, execute_stream, analyze_task), `create_orchestrator()` |
| **hybrid/synchronizer.py** | ~892 | Context format sync (5 formats) | `ContextSynchronizer` |
| **mcp/__init__.py** | — | MCP sub-package exports | — |
| **mcp/types.py** | 260 | MCP protocol types | `MCPServerConfig`, `MCPServerState`, `MCPTransportType`, `MCPToolDefinition`, `MCPToolResult`, `MCPMessage`, `MCPErrorCode` |
| **mcp/exceptions.py** | — | 11 MCP exception types | `MCPError`, `MCPConnectionError`, `MCPToolNotFoundError`, `MCPTimeoutError`, `MCPToolExecutionError`, `MCPServerError`, `MCPDisconnectedError` |
| **mcp/base.py** | 381 | Abstract MCP server | `MCPServer` (connect, disconnect, list_tools, execute_tool, send_request, JSON-RPC) |
| **mcp/stdio.py** | — | Local process transport | `MCPStdioServer` |
| **mcp/http.py** | — | Remote HTTP transport | `MCPHTTPServer` |
| **mcp/discovery.py** | 520 | Tool indexing + search | `ToolDiscovery`, `ToolCategory` (9 categories), `ToolIndex` |
| **mcp/manager.py** | 520 | Multi-server lifecycle | `MCPManager` (connect_all, discover_tools, execute_tool, health_check, reconnect_unhealthy) |
| **orchestrator/__init__.py** | — | Orchestrator sub-package exports | — |
| **orchestrator/types.py** | 309 | Multi-agent coordination types | `TaskComplexity`, `ExecutionMode` (4 modes), `AgentInfo`, `ComplexTask`, `TaskAnalysis`, `Subtask`, `AgentSelection`, `SubtaskResult`, `CoordinationResult`, `CoordinationContext` |
| **orchestrator/coordinator.py** | 523 | Claude-led multi-agent coordinator | `ClaudeCoordinator` (coordinate_agents: analyze -> select -> execute -> aggregate) |
| **orchestrator/task_allocator.py** | 484 | Subtask distribution + execution | `TaskAllocator` (select_agents, execute_parallel, execute_sequential, execute_pipeline) |
| **orchestrator/context_manager.py** | 315 | Cross-agent context transfer | `ContextManager` (transfer_context, merge_results, aggregate_final_result) |

**Total: 47 files, 15,406 LOC (R4 verified)**

---

## Internal Architecture

```
backend/src/integrations/claude_sdk/
│
├── client.py                     [Entry Point]
│   └── ClaudeSDKClient           query() → one-shot  |  create_session() → multi-turn
│                                 send_with_attachments() (S75)
│                                 execute_with_thinking() (S104, Extended Thinking stream)
│
├── query.py                      [One-Shot Execution]
│   └── execute_query()           Agentic loop: API call → tool_use check → hook chain
│                                 → execute_tool → append results → repeat
│       execute_query_with_attachments()   S75: multimodal (text + image base64)
│
├── session.py                    [Multi-Turn Conversations]
│   └── Session                   Maintains history, context, hooks
│                                 fork() creates branched sessions
│                                 Agentic loop identical to query.py
│
├── session_state.py              [State Persistence — Sprint 80]
│   └── SessionStateManager       save/restore/delete/compress/cleanup
│                                 zlib compression, SHA-256 checksum
│                                 PostgreSQL persistence (via checkpoint service)
│                                 mem0 long-term memory sync
│
├── autonomous/                   [Autonomous Planning Engine — Sprint 79-80]
│   ├── types.py                  EventContext, AutonomousPlan, PlanStep, enums
│   ├── analyzer.py               Phase 1: Extended Thinking event analysis
│   ├── planner.py                Phase 2: Extended Thinking plan generation
│   ├── executor.py               Phase 3: Step-by-step execution + SSE events
│   ├── verifier.py               Phase 4: Result validation + lesson extraction
│   ├── retry.py                  Exponential backoff + failure classification
│   └── fallback.py               6-strategy SmartFallback + pattern learning
│
├── hooks/                        [Tool Call Interception — Sprint 49, 68, 111]
│   ├── base.py                   Hook ABC + HookChain (priority-sorted)
│   ├── approval.py               ApprovalHook (priority 90) — human confirmation
│   ├── approval_delegate.py      S111: bridges to UnifiedApprovalManager
│   ├── sandbox.py                SandboxHook (85) + StrictSandboxHook + UserSandboxHook
│   ├── rate_limit.py             RateLimitHook (80) — per-minute + concurrent
│   └── audit.py                  AuditHook (10) — logging + credential redaction
│
├── tools/                        [Built-in Tool Implementations — Sprint 49]
│   ├── base.py                   Tool ABC + ToolResult
│   ├── registry.py               Singleton registry, auto-registers 10 tools on import
│   ├── file_tools.py             Read, Write, Edit, MultiEdit, Glob, Grep
│   ├── command_tools.py          Bash (security patterns), Task (subagent)
│   └── web_tools.py              WebSearch (Brave/Google/Bing), WebFetch (HTML→text)
│
├── hybrid/                       [Hybrid Orchestration — Sprint 50]
│   ├── types.py                  Framework, HybridResult, TaskAnalysis
│   ├── capability.py             CapabilityMatcher — keyword-based task analysis
│   ├── selector.py               FrameworkSelector — chooses MAF or Claude
│   ├── orchestrator.py           HybridOrchestrator — session mgmt, execute()
│   └── synchronizer.py           ContextSynchronizer — 5 format conversions
│
├── mcp/                          [MCP Client Integration — Sprint 50]
│   ├── types.py                  MCPServerConfig, MCPMessage (JSON-RPC 2.0)
│   ├── exceptions.py             11 MCP-specific exceptions
│   ├── base.py                   MCPServer ABC (stdio + http)
│   ├── stdio.py                  MCPStdioServer — local subprocess
│   ├── http.py                   MCPHTTPServer — remote HTTP
│   ├── discovery.py              ToolDiscovery — categorization + search + validation
│   └── manager.py                MCPManager — lifecycle, parallel connect, health checks
│
└── orchestrator/                 [Multi-Agent Coordination — Sprint 81]
    ├── types.py                  ComplexTask, ExecutionMode, AgentInfo, CoordinationResult
    ├── coordinator.py            ClaudeCoordinator — 4-phase coordination cycle
    ├── task_allocator.py         TaskAllocator — agent scoring (70% capability, 30% availability)
    └── context_manager.py        ContextManager — inter-subtask data transfer + merge
```

---

## Core Flow: One-Shot Query (Agentic Loop)

```
User prompt
    │
    ▼
ClaudeSDKClient.query()
    │
    ├── get_tool_definitions() ← ToolRegistry (10 built-in) + MCP tools
    │
    ▼
execute_query() — agentic loop
    │
    ├── client.messages.create() → Anthropic API
    │        │
    │        ▼
    │   Response has tool_use blocks?
    │        │
    │   No ──┤── Extract text content → return QueryResult(status="success")
    │        │
    │   Yes ─┤
    │        ▼
    │   For each tool_use block:
    │        │
    │        ├── Run HookChain.run_tool_call()
    │        │     ApprovalHook (90)   → requires human confirm for Write/Edit/Bash
    │        │     SandboxHook (85)    → checks path allowlist / blocklist
    │        │     RateLimitHook (80)  → checks calls/min + concurrent
    │        │     AuditHook (10)      → logs with credential redaction
    │        │
    │        ├── Any hook rejects? → append error tool_result, skip execution
    │        │
    │        ├── execute_tool() → registry lookup → tool.execute(**args)
    │        │
    │        └── Run hook.on_tool_result() for each hook
    │
    ├── Append assistant + tool_results to messages
    │
    └── Loop back to API call (continues until no tool_use)
```

---

## Autonomous Planning Engine (4-Phase Cycle)

The autonomous engine (Sprint 79-80) provides a full Analyze-Plan-Execute-Verify cycle for IT event handling, distinct from the basic agentic loop above.

### Phase 1: Analysis (`EventAnalyzer`)

```
IT Event (EventContext)
    │
    ▼
EventAnalyzer.analyze_event()
    │
    ├── Builds structured prompt from event context
    ├── Calls Claude API with Extended Thinking:
    │     thinking: { type: "enabled", budget_tokens: 4096-32000 }
    │
    ├── Parses JSON response → AnalysisResult
    │     complexity: simple | moderate | complex | critical
    │     root_cause_hypothesis
    │     affected_components[]
    │     recommended_actions[]
    │     confidence_score (0.0-1.0)
    │
    └── Fallback: severity-based heuristic if API fails
```

**Budget Token Allocation by Complexity:**

| Complexity | Budget Tokens | Example Scenario |
|------------|---------------|------------------|
| SIMPLE | 4,096 | Restart single service |
| MODERATE | 8,192 | Configuration change |
| COMPLEX | 16,000 | Multi-system failure |
| CRITICAL | 32,000 | Security incident |

### Phase 2: Planning (`AutonomousPlanner`)

```
AnalysisResult
    │
    ▼
AutonomousPlanner.generate_plan()
    │
    ├── Calls Claude API with Extended Thinking (budget from analysis)
    ├── Prompt includes available tools: shell_command, azure_vm,
    │     azure_monitor, servicenow, teams_notify, file_operation, database_query
    │
    ├── Parses JSON → AutonomousPlan
    │     steps[]: PlanStep (action, tool_or_workflow, parameters,
    │              fallback_action, requires_approval)
    │     risk_level: low | medium | high | critical
    │     estimated_duration_seconds
    │
    └── Fallback: single "Manual Investigation" step if parsing fails
```

### Phase 3: Execution (`PlanExecutor`)

```
AutonomousPlan
    │
    ▼
PlanExecutor.execute_stream()     (AsyncGenerator[ExecutionEvent])
    │
    ├── Emits PLAN_STARTED event
    │
    ├── For each PlanStep:
    │     ├── Emits STEP_STARTED
    │     ├── Check requires_approval → callback or auto-approve
    │     ├── Invoke tool_or_workflow via registered executors
    │     │     max_retries: 2 (exponential backoff: 2s, 4s)
    │     │     step_timeout: 300s
    │     ├── On success → STEP_COMPLETED
    │     ├── On failure → attempt fallback_action
    │     │     fallback format: "tool_name:action" or manual description
    │     └── On final failure → STEP_FAILED
    │
    ├── Emits PLAN_COMPLETED or PLAN_FAILED
    │
    └── Supports cancel_execution() → marks remaining steps as SKIPPED

ExecutionEventType enum:
  PLAN_STARTED, STEP_STARTED, STEP_PROGRESS, STEP_COMPLETED,
  STEP_FAILED, PLAN_COMPLETED, PLAN_FAILED, APPROVAL_REQUIRED
```

### Phase 4: Verification (`ResultVerifier`)

```
Executed AutonomousPlan
    │
    ▼
ResultVerifier.verify()
    │
    ├── Builds verification prompt with:
    │     expected_outcomes (from PlanStep.expected_outcome)
    │     actual_results (from PlanStep.result / error)
    │
    ├── Calls Claude API (no Extended Thinking, max_tokens=4000)
    │
    ├── Parses → VerificationResult
    │     success: bool
    │     quality_score: 0.0-1.0
    │     outcomes_met[] / outcomes_failed[]
    │     lessons_learned[]
    │     recommendations[]
    │
    └── Also provides local heuristics:
          calculate_quality_score() — completion_rate - failure_penalty
          extract_lessons() — detects slow steps, failed steps
```

### SmartFallback System (6 Strategies)

The `SmartFallback` class (Sprint 80) wraps the retry policy with intelligent error recovery:

```
Error occurs
    │
    ▼
SmartFallback.analyze_failure()
    │
    ├── RetryPolicy.classify_failure() → TRANSIENT | RECOVERABLE | FATAL | UNKNOWN
    │     TRANSIENT patterns: timeout, connection, 429, 503, gateway
    │     FATAL patterns: authentication, forbidden, invalid_request, 401, 403
    │
    ├── _categorize_error() → network | authentication | resource |
    │     rate_limit | validation | service | configuration
    │
    ├── _recommend_strategy() → (strategy, confidence)
    │     Checks learned patterns first
    │     Then uses category-based defaults:
    │       network     → RETRY (0.9)
    │       rate_limit  → RETRY (0.95)
    │       service     → RETRY (0.85)
    │       auth        → ESCALATE (0.9)
    │       resource    → ALTERNATIVE (0.7)
    │       validation  → ALTERNATIVE (0.8)
    │       config      → ESCALATE (0.85)
    │       fatal       → ABORT (0.95)
    │
    └── Returns FailureAnalysis

6 FallbackStrategy values:
  RETRY        — Simple retry with exponential backoff
  ALTERNATIVE  — Try alternative action (modified params or step fallback)
  SKIP         — Skip the step, continue execution
  ESCALATE     — Escalate to human operator
  ROLLBACK     — Rollback and retry earlier step
  ABORT        — Abort entire plan

Pattern Learning:
  record_failure_pattern() stores error_signature + successful_recovery
  Future failures consult learned patterns before defaults
  In-memory storage (Dict[str, FailurePattern])
```

**RetryPolicy Configuration:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| max_retries | 3 | Maximum retry attempts |
| initial_delay_seconds | 1.0 | First backoff delay |
| max_delay_seconds | 60.0 | Maximum backoff cap |
| exponential_base | 2.0 | Delay multiplier per retry |
| jitter | True | Randomized delay (10% factor) |

---

## Hook Chain (Priority-Sorted Interception)

Hooks intercept tool calls, queries, and session lifecycle events. The `HookChain` executes hooks in descending priority order. If any hook rejects, execution halts immediately. Modified args propagate to subsequent hooks.

### Hook Execution Order

| Priority | Hook | Responsibility | Sprint |
|----------|------|----------------|--------|
| 90 | `ApprovalHook` | Human confirmation for Write/Edit/MultiEdit/Bash | S49 |
| 85 | `SandboxHook` | File path allowlist/blocklist enforcement | S49 |
| 80 | `RateLimitHook` | Calls/minute + concurrent execution limits | S49 |
| 10 | `AuditHook` | Activity logging with credential redaction | S49 |

### Hook Base Class (`Hook` ABC)

```python
class Hook(ABC):
    priority: int = 50      # 0-100, higher = executes first
    name: str = "base"
    enabled: bool = True

    async def on_session_start(session_id)    → None
    async def on_session_end(session_id)      → None
    async def on_query_start(QueryContext)     → HookResult
    async def on_query_end(QueryContext, str)  → None
    async def on_tool_call(ToolCallContext)    → HookResult   # Primary interception
    async def on_tool_result(ToolResultContext) → None
    async def on_error(Exception)              → None
```

### HookResult Protocol

```
HookResult.ALLOW                    — Pass through (singleton)
HookResult.reject(reason: str)      — Block execution, provide reason
HookResult.modify(new_args: dict)   — Allow but transform arguments
```

### ApprovalHook (Priority 90)

- **Targets**: Write, Edit, MultiEdit, Bash (configurable via `approval_tools`)
- **Auto-approves**: Read, Glob, Grep when `auto_approve_reads=True`
- **Deduplication**: Tracks `_approved_operations` set per session; same file+tool combo approved once
- **Timeout**: 300s default for approval callback
- **Delegation**: Sprint 111 added `ClaudeApprovalDelegate` which bridges to the unified `UnifiedApprovalManager` via the orchestration HITL system
- **Risk Assessment**: Delegate classifies tools into high-risk (execute_command, delete_resource, deploy_service, etc.) and safe (get_status, list_resources, read_file, etc.)

### SandboxHook (Priority 85) — Three Variants

| Variant | Mode | Reads Outside | Temp Access | Use Case |
|---------|------|---------------|-------------|----------|
| `SandboxHook` | Allowlist + blocklist | Configurable | Configurable | General use |
| `StrictSandboxHook` | Allowlist only | Blocked | Blocked | High-security |
| `UserSandboxHook` | Per-user directories | Blocked | Allowed | Agentic chat (S68) |

**Default Blocked Patterns** (23 regex patterns):
- System directories: `/etc/`, `/usr/`, `C:\Windows\`, `C:\Program Files`
- Sensitive files: `.ssh/`, `.aws/`, `.env`, `credentials`, `*.pem`, `*.key`, `id_rsa`

**UserSandboxHook** (Sprint 68):
- Auto-configures paths: `data/uploads/{user_id}`, `data/sandbox/{user_id}`, `data/outputs/{user_id}`
- Blocks 30+ source code patterns and 35+ write-protected file extensions (.py, .ts, .js, .yaml, .json, etc.)
- Factory methods: `for_guest(guest_id)`, `for_authenticated(user_id)`

### RateLimitHook (Priority 80)

- **Global limits**: calls_per_minute (default 60), max_concurrent (default 10)
- **Per-tool limits**: Optional `per_tool_limits` dict with separate `RateLimitConfig` per tool
- **Queue mode**: When `queue_on_limit=True`, waits `cooldown_seconds` before rejecting
- **Concurrency**: Uses `asyncio.Semaphore` per tool for concurrent call management
- **Sliding window**: Maintains `_call_timestamps` list, prunes entries older than 60s

### AuditHook (Priority 10)

- **Low priority**: Runs last so it captures the final decision from other hooks
- **Credential redaction**: 7 default regex patterns for API keys, tokens, GitHub/Slack/OpenAI keys
- **Key-based redaction**: 10 sensitive key names (password, secret, token, api_key, etc.)
- **Session logs**: `AuditLog` per session with `AuditEntry` records
- **Custom callback**: Optional `log_callback` for external audit systems

---

## 10 Built-in Tools

All tools inherit from `Tool` ABC and are auto-registered via `_register_builtin_tools()` on module import.

### File Tools (6)

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `Read` | Read file contents, optional line range | path, encoding, start_line, end_line; max 100K chars |
| `Write` | Write content to file | path, content, create_dirs, overwrite |
| `Edit` | Search-and-replace in file | path, old_text, new_text, replace_all |
| `MultiEdit` | Atomic batch edits across files | edits[]: [{path, old_text, new_text}] |
| `Glob` | Pattern-based file search | pattern, path, exclude[], include_hidden; max 10K files |
| `Grep` | Regex content search | pattern, path, regex, case_sensitive, before/after context; max 1K matches |

### Command Tools (2)

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `Bash` | Shell command execution with security | command, cwd, timeout (120s), env; 9 dangerous patterns blocked |
| `Task` | Subagent delegation | prompt, tools[], agent_type (code/research/analysis/writing/debug), system_prompt |

**Bash Security Patterns** (blocked by default):
- `rm -rf /`, fork bomb, `dd if=`, `curl | bash`, `wget | sh`, `mkfs.`, `format c:`, `del /fqs`

**Task Subagent**: Creates a new `ClaudeSDKClient` instance per delegation with specialized system prompts per agent_type.

### Web Tools (2)

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `WebSearch` | Web search via API | query, num_results (1-20); supports Brave, Google, Bing |
| `WebFetch` | URL content retrieval | url, headers, method, extract_text; HTML→text via `HTMLTextExtractor` |

**WebSearch** requires external API key configuration. Without key, returns usage instructions.
**WebFetch** uses `aiohttp` with custom User-Agent, 500K max content, automatic HTML text extraction.

### Tool Registry

```python
_TOOL_REGISTRY: Dict[str, Type[Tool]] = {}   # name → class
_TOOL_INSTANCES: Dict[str, Tool] = {}          # name → singleton instance

register_tool(tool_class)     — decorator or direct call
get_tool_instance(name)       — lazy singleton creation
get_tool_definitions(tools, mcp_servers) — builds Claude API format
execute_tool(name, args, working_directory, mcp_servers) — dispatches execution
```

Note: MCP server tool integration in `get_tool_definitions()` has a TODO comment — MCP tools are passed through but the unification is incomplete.

---

## ClaudeCoordinator (4 Execution Modes)

The `ClaudeCoordinator` (Sprint 81) provides Claude-led multi-agent coordination, distinct from the autonomous planning engine. It coordinates multiple registered agents to complete complex tasks.

### Coordination Cycle

```
ComplexTask
    │
    ▼
Phase 1: analyze_task()
    │  ├── Heuristic: requirement count → complexity + execution mode
    │  └── Optional Claude API analysis for intelligent recommendations
    │
    ▼
Phase 2: select_agents()
    │  ├── TaskAllocator.create_subtasks() — one subtask per capability
    │  └── TaskAllocator.select_agents() — score each agent:
    │       overall = capability_score * 0.7 + availability_score * 0.3
    │
    ▼
Phase 3: execute (mode-dependent)
    │  ├── SEQUENTIAL: respects dependency graph, batch-parallel within each tier
    │  ├── PARALLEL: asyncio.gather all assigned subtasks
    │  ├── PIPELINE: output of step N feeds into step N+1
    │  └── HYBRID: determined by analysis (maps to PARALLEL or SEQUENTIAL)
    │
    ▼
Phase 4: aggregate results
    │  └── ContextManager.aggregate_final_result() — summary/detailed/outputs_only
    │
    ▼
CoordinationResult
    success_rate = completed / total (threshold >= 0.5 for COMPLETED)
```

### 4 Execution Modes

| Mode | Enum | Behavior | When Used |
|------|------|----------|-----------|
| SEQUENTIAL | `ExecutionMode.SEQUENTIAL` | One-after-another, respects `depends_on` | 1 requirement, or >6 (critical) |
| PARALLEL | `ExecutionMode.PARALLEL` | All subtasks via `asyncio.gather` | 2-3 requirements |
| PIPELINE | `ExecutionMode.PIPELINE` | Chain: output N → input N+1 | Explicit pipeline tasks |
| HYBRID | `ExecutionMode.HYBRID` | Mix of parallel batches + sequential dependencies | 4-6 requirements |

### Agent Selection Scoring

```
capability_score = avg(skill_proficiency for each required_capability)
availability_score = 1.0 - (current_load / max_concurrent_tasks)
overall_score = capability_score * 0.7 + availability_score * 0.3
```

### Swarm Integration

`ClaudeCoordinator` optionally integrates with `SwarmIntegration` (Phase 29):
- `on_coordination_started()` — maps ExecutionMode to SwarmMode
- `_wrap_executor_for_swarm()` — wraps executors to emit subtask start/complete events
- `on_coordination_completed()` — notifies SwarmStatus.COMPLETED or FAILED
- Worker type inference from capabilities: research, write, review, code, custom

### Context Transfer

`ContextManager` handles inter-subtask data flow:
- `transfer_context(from_subtask, to_subtask, result)` — builds `dependencies_output` in target input_data
- `prepare_subtask_context()` — adds shared context + dependency outputs
- `merge_results()` — 4 strategies: combine (list), dict, first_success, last
- `aggregate_final_result()` — 3 types: summary, detailed, outputs_only

---

## MCP Client Integration

### MCPManager (Multi-Server Lifecycle)

```
MCPManager
    │
    ├── add_server(MCPServer)         — register by name
    ├── connect_all()                 — parallel connect with timeout (30s)
    ├── discover_tools()              — aggregate tools from all connected servers
    ├── execute_tool("server:tool")   — route to correct server
    ├── health_check()                — parallel health probe via list_tools()
    └── reconnect_unhealthy()         — auto-reconnect failed servers

async with MCPManager() as manager:
    tools = await manager.discover_tools()
    result = await manager.execute_tool("filesystem:read_file", {...})
```

### MCPServer Base (Abstract)

| Method | Description |
|--------|-------------|
| `connect()` | `_connect()` → `_initialize()` → `_discover_tools()` |
| `disconnect()` | `_disconnect()` + cancel pending requests |
| `list_tools()` | Return cached `MCPToolDefinition` list |
| `execute_tool()` | Validate connected + tool exists → `_execute_tool()` with timeout |
| `send_request()` | JSON-RPC 2.0 request with Future-based response tracking |

**Protocol**: JSON-RPC 2.0, protocol version `2024-11-05`, client info `claude-sdk/1.0.0`

### Transport Types

| Type | Class | Connection |
|------|-------|------------|
| STDIO | `MCPStdioServer` | Local subprocess (command + args) |
| HTTP | `MCPHTTPServer` | Remote URL with headers |
| WEBSOCKET | (enum defined, not implemented) | — |

### ToolDiscovery (Indexing Engine)

- **9 categories**: FILE_SYSTEM, DATABASE, WEB, CODE, SEARCH, COMMUNICATION, DATA, SYSTEM, OTHER
- **Auto-categorization**: Regex keyword matching on tool name + description
- **Tag extraction**: Splits tool name, extracts keywords from description
- **Search**: Relevance scoring (exact name 1.0, contains 0.8, description 0.3, tag 0.4)
- **Schema validation**: Checks JSON Schema structure (type, properties, required fields)

---

## Hybrid Orchestration (Claude-side)

The `hybrid/` subsystem is Claude SDK's side of the MAF-Claude hybrid bridge:

### HybridOrchestrator

```
prompt → CapabilityMatcher.analyze() → TaskAnalysis
    │
    ├── FrameworkSelector.select() → "claude_sdk" | "microsoft_agent_framework"
    │     Uses: task analysis, session framework history, switch threshold
    │     auto_switch: bool (config)
    │     switch_confidence_threshold: float (default 0.7)
    │
    ├── If framework == "claude_sdk" → _execute_claude()
    │     Delegates to injected claude_executor function
    │
    └── If framework == "microsoft_agent_framework" → _execute_ms_agent()
          Delegates to injected ms_executor function
```

- **Session management**: create_session / close_session / session context manager
- **Streaming**: `execute_stream()` currently wraps non-streaming result with simulated chunking
- **Metrics**: Tracks execution_count, total_duration, framework_usage breakdown
- **Factory**: `create_orchestrator(primary_framework, auto_switch, switch_threshold)`

### ContextSynchronizer (~892 LOC)

Converts context between 5 formats: Claude messages, MAF messages, AG-UI events, Hybrid internal, and raw dict. This is the largest single class in the module.

**Known Issue**: Uses in-memory dict without locks — thread-safety concern noted in V8 analysis.

---

## Session State Management (Sprint 80)

### SessionStateManager

| Feature | Implementation |
|---------|---------------|
| **Persistence** | Checkpoint service (PostgreSQL) via `save_checkpoint()` / `load_checkpoint()` |
| **Compression** | zlib + base64 when history exceeds `compression_threshold` (1000 chars) |
| **Integrity** | SHA-256 checksum (first 16 hex chars) on save, verified on restore |
| **Expiration** | TTL-based (default 24h), `cleanup_expired_sessions()` batch removal |
| **Context compression** | Keep last N messages (default 10), summarize older ones, truncate large values |
| **mem0 sync** | Stores session summary to UnifiedMemoryManager for long-term memory |
| **Cache** | In-memory `_state_cache` dict, checked before DB |

### Extended Thinking Support (Sprint 104)

`ClaudeSDKClient.execute_with_thinking()` provides streaming Extended Thinking:
- Uses `anthropic-beta: interleaved-thinking-2025-05-14` header
- Captures thinking blocks separately from text blocks
- Provides `thinking_callback(content, token_count)` for real-time updates
- Yields structured events: `thinking_delta`, `thinking_complete`, `text_delta`, `tool_input_delta`

---

## Exception Hierarchy

```
ClaudeSDKError (base)
├── AuthenticationError              — API key missing or invalid
├── RateLimitError                   — API rate limit (has retry_after field)
├── TimeoutError                     — Operation timeout
├── ToolError                        — Tool execution failure (has tool_name, tool_args)
├── HookRejectionError               — Hook blocked operation (has hook_name)
└── MCPError (base for MCP)
    ├── MCPConnectionError            — Server connection failure (has server_name, command)
    ├── MCPToolError                  — MCP tool execution failure (has server_name, tool_name)
    ├── MCPToolNotFoundError          — Tool not found on server
    ├── MCPTimeoutError               — MCP operation timeout
    ├── MCPToolExecutionError         — Tool execution error with details
    ├── MCPServerError                — JSON-RPC server error
    └── MCPDisconnectedError          — Operation on disconnected server
```

---

## Sprint Evolution

| Sprint | Phase | Feature | Key Files |
|--------|-------|---------|-----------|
| S48 | 12 | Core SDK: client, query, session | client.py, query.py, session.py, config.py, types.py |
| S49 | 12 | Tools (10) + Hooks (4) | tools/*, hooks/* |
| S50 | 12 | Hybrid + MCP integration | hybrid/*, mcp/* |
| S68 | 18 | UserSandboxHook per-user isolation | hooks/sandbox.py (UserSandboxHook) |
| S75 | 20 | File attachment support | query.py (build_content_with_attachments), client.py |
| S79 | 21 | Autonomous planning engine | autonomous/analyzer.py, planner.py, executor.py, verifier.py |
| S80 | 21 | Session state + SmartFallback + Retry | session_state.py, autonomous/fallback.py, autonomous/retry.py |
| S81 | 21 | Multi-agent coordination | orchestrator/* |
| S104 | 27 | Extended Thinking streaming | client.py (execute_with_thinking) |
| S111 | 29 | Unified approval delegation | hooks/approval_delegate.py |

---

## Known Issues and Technical Debt

### ISSUE-01: ContextSynchronizer Thread Safety (MEDIUM)

- **Location**: `hybrid/synchronizer.py`
- **Problem**: Uses in-memory dict without locks for context storage
- **Impact**: Potential race conditions in concurrent hybrid sessions
- **Recommendation**: Add `asyncio.Lock` or switch to thread-safe data structure

### ISSUE-02: MCP Tool Integration Incomplete (LOW)

- **Location**: `tools/registry.py:81-82`
- **Problem**: `get_tool_definitions()` has `# TODO: Add MCP server tools when implemented` — MCP tools passed through but not unified into the built-in tool format
- **Impact**: MCP tools work via `MCPManager.execute_tool()` but are not transparently available alongside built-in tools in the agentic loop
- **Recommendation**: Implement MCP tool bridging in `get_tool_definitions()`

### ISSUE-03: Fallback Pattern Storage is In-Memory (LOW)

- **Location**: `autonomous/fallback.py` (`_failure_patterns: Dict`)
- **Problem**: Learned failure patterns are lost on process restart
- **Impact**: Pattern learning provides no cross-session benefit
- **Recommendation**: Persist patterns to PostgreSQL or Redis

### ISSUE-04: SessionStateManager Requires Explicit Initialization (LOW)

- **Location**: `session_state.py:182-187`
- **Problem**: `_ensure_initialized()` raises RuntimeError if `initialize()` not called
- **Impact**: Easy to forget; could cause runtime failures
- **Recommendation**: Consider lazy initialization or constructor injection

### ISSUE-05: Executor Default is Mock (LOW)

- **Location**: `orchestrator/coordinator.py:431-454`
- **Problem**: `_default_executor()` returns simulated results without actual agent execution
- **Impact**: ClaudeCoordinator works in tests but requires explicit executor injection for production use
- **Recommendation**: Document clearly or raise error when no executor provided

### ISSUE-06: Query Module Duplicates Agentic Loop (LOW)

- **Location**: `query.py` and `session.py`
- **Problem**: Both implement nearly identical agentic loops (API call → tool check → execute → loop)
- **Impact**: Bug fixes must be applied in two places
- **Recommendation**: Extract shared agentic loop into a common function

### ISSUE-07: UserSandboxHook Accesses Undefined Attribute (BUG)

- **Location**: `hooks/sandbox.py:448`
- **Problem**: `result.action == "reject"` — `HookResult` has no `action` attribute. Should check `result.is_rejected`
- **Impact**: Logging of blocked attempts silently fails (AttributeError caught by general exception handling)
- **Recommendation**: Change to `if result.is_rejected:`

### ISSUE-08: Bash Tool Uses asyncio.get_event_loop() (DEPRECATION)

- **Location**: `tools/command_tools.py` (indirectly via `PlanExecutor._invoke_tool`)
- **Problem**: `asyncio.get_event_loop()` is deprecated in Python 3.12+ for non-main threads
- **Impact**: May raise DeprecationWarning or RuntimeError in future Python versions
- **Recommendation**: Use `asyncio.get_running_loop()` instead

---

## Cross-Layer Dependencies

```
Layer 07 (Claude SDK)
    │
    ├── Upstream (depends on):
    │   ├── anthropic.AsyncAnthropic          — External: Anthropic Python SDK
    │   ├── aiohttp                           — External: HTTP client (WebSearch, WebFetch)
    │   ├── src.core.sandbox_config           — SandboxConfig (UserSandboxHook)
    │   ├── src.infrastructure.storage        — ApprovalStore (approval_delegate)
    │   └── src.integrations.orchestration    — UnifiedApprovalManager (S111 delegate)
    │
    ├── Downstream (depended upon by):
    │   ├── Layer 05 (Hybrid)                 — hybrid/ subsystem provides Claude-side bridge
    │   ├── Layer 04 (Orchestration)          — autonomous engine used by intent routing
    │   ├── Layer 03 (AG-UI)                  — HybridEventBridge routes through Claude SDK
    │   └── Layer 10 (Swarm)                  — ClaudeCoordinator integrates SwarmIntegration
    │
    └── Peer:
        └── Layer 06 (MAF)                    — HybridOrchestrator routes between MAF and Claude
```

---

## Configuration Reference

### ClaudeSDKConfig

| Parameter | Default | Env Var | Description |
|-----------|---------|---------|-------------|
| api_key | None | `ANTHROPIC_API_KEY` | Required; raises AuthenticationError if missing |
| model | `claude-haiku-4-5-20251001` | `CLAUDE_SDK_MODEL` | Model identifier |
| max_tokens | 4096 | `CLAUDE_SDK_MAX_TOKENS` | Default response token limit |
| timeout | 300 | `CLAUDE_SDK_TIMEOUT` | Request timeout (seconds) |
| system_prompt | None | — | System prompt for all queries |
| tools | [] | — | Default enabled tool names |
| allowed_commands | [] | — | Bash whitelist |
| denied_commands | [5 defaults] | — | Bash blacklist (rm -rf /, fork bomb, curl pipe, etc.) |

### SessionStateConfig

| Parameter | Default | Description |
|-----------|---------|-------------|
| enable_persistence | True | Save to PostgreSQL via checkpoint service |
| compression_enabled | True | zlib compress large histories |
| compression_threshold | 1000 | Compress if > N characters |
| session_ttl_hours | 24 | Session expiration time |
| max_context_tokens | 10000 | Token limit for context compression |
| preserve_recent_messages | 10 | Messages kept during compression |
| enable_mem0_sync | True | Sync summaries to mem0 |

---

*Analysis generated from source code reading of 47 files in `backend/src/integrations/claude_sdk/`. All class names, method signatures, and constants verified against actual implementation.*
