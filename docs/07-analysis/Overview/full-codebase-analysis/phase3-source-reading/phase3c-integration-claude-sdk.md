# Phase 3C: Claude Agent SDK Integration Analysis

> **Scope**: `backend/src/integrations/claude_sdk/` (47 files, ~11,625 LOC)
> **Feature Reference**: E3 (Claude SDK) from sprint plan
> **Analysis Date**: 2026-03-15

---

## 1. Executive Summary

The Claude SDK integration is a **real, production-grade Anthropic SDK integration** — not a mock or wrapper. It uses `anthropic.AsyncAnthropic` directly, implements a full agentic loop with tool execution, and provides autonomous planning, lifecycle hooks, MCP server management, hybrid framework selection, and multi-agent coordination. The module spans 7 subpackages across 47 Python files.

**Verdict**: Genuine Anthropic SDK integration with substantial production logic.

---

## 2. Module Architecture

```
ClaudeSDKClient (client.py)
├── query() ──────────► QueryExecutor (query.py) ── one-shot agentic loop
├── create_session() ─► Session (session.py) ────── multi-turn agentic loop
├── send_with_attachments() ── Sprint 75 file/image attachments
└── execute_with_thinking() ── Sprint 104 Extended Thinking streaming
        │
        ├── Hook Chain (hooks/) ──► Approval → Audit → RateLimit → Sandbox
        ├── Built-in Tools (tools/) ── Read/Write/Edit/Glob/Grep/Bash/Task/WebSearch/WebFetch
        ├── MCP Servers (mcp/) ──── Stdio + HTTP transports, MCPManager lifecycle
        ├── Autonomous Engine (autonomous/) ── Analyzer → Planner → Executor → Verifier
        ├── Hybrid Selector (hybrid/) ── CapabilityMatcher → FrameworkSelector → HybridOrchestrator
        └── Orchestrator (orchestrator/) ── ClaudeCoordinator multi-agent coordination
```

---

## 3. Client Layer (`client.py`, `config.py`, `query.py`, `session.py`)

### 3.1 ClaudeSDKClient — Main Entry Point (357 LOC)

- **Uses `AsyncAnthropic` directly** — `from anthropic import AsyncAnthropic`
- Instantiates: `self._client = AsyncAnthropic(api_key=..., base_url=..., timeout=...)`
- Default model: `claude-sonnet-4-20250514`
- Supports API key from constructor or `ANTHROPIC_API_KEY` env var
- Manages session dict `_sessions: Dict[str, Session]`

**Key methods**:
| Method | Purpose |
|--------|---------|
| `query(prompt)` | One-shot autonomous task via `execute_query()` |
| `create_session()` | Multi-turn session with UUID tracking |
| `resume_session(id)` | Resume existing session |
| `send_with_attachments()` | Sprint 75: text + image (base64) attachments |
| `execute_with_thinking()` | Sprint 104: Extended Thinking streaming with `anthropic-beta: extended-thinking-2024-10` header |
| `close()` | Close all sessions + client |

### 3.2 ClaudeSDKConfig (`config.py`, 76 LOC)

- Dataclass with: `api_key`, `base_url`, `model`, `max_tokens` (4096), `timeout` (300s)
- `system_prompt`, `tools` list, `allowed_commands`, `denied_commands`
- Factory methods: `from_env()`, `from_yaml(path)`
- Default denied commands: `rm -rf /`, fork bomb, `curl | bash`, `wget | sh`
- Raises `AuthenticationError` if no API key found

### 3.3 QueryExecutor (`query.py`, 345 LOC)

Implements the **agentic loop** for one-shot queries:

```
1. Build messages + tool definitions
2. Loop: call client.messages.create()
3.   If no tool_use blocks → return final text
4.   For each tool_use block:
4a.    Run hook chain (on_tool_call) — reject if hook denies
4b.    execute_tool(name, args) via registry
4c.    Run hook chain (on_tool_result)
5.   Append assistant + tool_results to messages
6.   Continue loop until no more tool calls or timeout
```

- Timeout enforcement via `time.time()` elapsed check
- Returns `QueryResult(content, tool_calls, tokens_used, duration, status)`
- Also implements `execute_query_with_attachments()` for multimodal content (text + base64 images)

### 3.4 Session (`session.py`, 287 LOC)

Multi-turn conversation with persistent history:

- Maintains `_history: List[Message]` across queries
- Same agentic loop as QueryExecutor but within session context
- `fork(branch_name)` — creates branched session with copied history/context
- Hook lifecycle: `on_session_start`, `on_query_start`, `on_tool_call`, `on_tool_result`, `on_query_end`, `on_session_end`
- System prompt augmented with context variables

### 3.5 Session State Manager (`session_state.py`, 576 LOC)

Sprint 80 enhancement for state persistence:

- **Persistence**: saves to PostgreSQL via checkpoint service
- **Compression**: zlib compression for histories > 1000 chars, stored as base64
- **Expiration**: configurable TTL (default 24h), automatic cleanup
- **Checksum**: SHA-256 integrity verification
- **mem0 sync**: syncs session summaries to UnifiedMemoryManager for long-term memory
- **Context compression**: keeps last N messages (default 10), summarizes older ones
- In-memory cache with fallback to checkpoint service

---

## 4. Tools Subsystem (`tools/`)

### 4.1 Tool Base Class (`base.py`)

Abstract base with:
- `name: str`, `description: str` class attributes
- `async execute(**kwargs) -> ToolResult` — abstract
- `get_definition() -> Dict` — returns Claude API tool schema
- `ToolResult(success: bool, content: str, error: Optional[str])`

### 4.2 Built-in Tool Implementations

| Tool | File | Description |
|------|------|-------------|
| **Read** | `file_tools.py` | Read file contents with optional line offset/limit |
| **Write** | `file_tools.py` | Write/overwrite file content |
| **Edit** | `file_tools.py` | String replacement in files (old_string → new_string) |
| **MultiEdit** | `file_tools.py` | Batch edits across multiple files |
| **Glob** | `file_tools.py` | File pattern matching |
| **Grep** | `file_tools.py` | Regex content search across files |
| **Bash** | `command_tools.py` | Shell command execution with security controls |
| **Task** | `command_tools.py` | Delegate subtasks to specialized subagents |
| **WebSearch** | `web_tools.py` | Web search capability |
| **WebFetch** | `web_tools.py` | Fetch web page content |

### 4.3 Tool Registry (`registry.py`)

- Module-level `_TOOL_REGISTRY: Dict[str, Type[Tool]]` — maps names to classes
- `_TOOL_INSTANCES: Dict[str, Tool]` — singleton cache
- `register_tool(cls)` — decorator-style registration
- `get_tool_definitions(tools, mcp_servers)` — builds Claude API tool schemas
- `execute_tool(name, args, working_directory)` — resolves relative paths, executes
- **Note**: MCP server tool integration in registry is stubbed (`# TODO: Add MCP server tools`)

### 4.4 Security Controls (Bash tool)

- Dangerous pattern detection: `rm -rf /`, fork bombs, `del /s /f /q` (Windows)
- Configurable allowed/denied command lists
- Timeout (default 120s), max output (100,000 chars)
- Process execution via `asyncio.create_subprocess_shell`

---

## 5. Hooks Subsystem (`hooks/`)

### 5.1 Hook Base Class & Chain (`base.py`)

- `Hook(ABC)` with lifecycle methods:
  - `on_session_start(session_id)` / `on_session_end(session_id)`
  - `on_query_start(context)` / `on_query_end(context, result)`
  - `on_tool_call(context) -> HookResult` — primary interception point
  - `on_tool_result(context)`
  - `on_error(exception)`
- Priority system: 0-100 (higher executes first)
- `HookChain` — manages ordered execution; first rejection stops chain; modifications propagate to subsequent hooks

### 5.2 Hook Implementations

| Hook | Priority | Purpose |
|------|----------|---------|
| **ApprovalHook** | 90 | Human confirmation for Write/Edit/MultiEdit/Bash. Configurable callback, session-level deduplication, 5-min timeout |
| **AuditHook** | 50 | Logs all tool calls with sensitive data redaction (API keys, passwords, tokens). Maintains `AuditLog` with `AuditEntry` records |
| **RateLimitHook** | 70 | Token bucket rate limiting. Configurable per-tool limits, concurrency caps, cooldown periods. Tracks `RateLimitStats` |
| **SandboxHook** | 85 | File access restrictions. Allowlist/blocklist modes. Blocks system dirs, `.env`, credentials, SSH keys. `StrictSandboxHook` variant for locked-down environments |

### 5.3 UserSandboxHook (Sprint 68)

- Per-user directory isolation: `{base_dir}/{user_id}/`
- `SOURCE_CODE_BLOCKED_PATTERNS` — prevents access to source code patterns
- `BLOCKED_WRITE_EXTENSIONS` — blocks writes to sensitive extensions
- Cross-platform support (Linux + Windows path patterns)

---

## 6. Autonomous Planning Engine (`autonomous/`)

### 6.1 Architecture

```
IT Event → EventAnalyzer (Extended Thinking) → AnalysisResult
    ↓
AutonomousPlanner → AutonomousPlan (decision tree with PlanSteps)
    ↓
PlanExecutor (streaming) → ExecutionEvents
    ↓ (on failure)
SmartFallback → Retry / Alternative / Skip / Escalate / Rollback / Abort
    ↓
ResultVerifier → VerificationResult + lessons learned
```

### 6.2 Components

**EventAnalyzer** (`analyzer.py`):
- Uses Claude Extended Thinking to analyze IT events
- Produces `AnalysisResult`: root cause hypothesis, affected components, recommended actions, complexity assessment, confidence score
- Complexity-based token budgets: SIMPLE=4096, MODERATE=8192, COMPLEX=16000, CRITICAL=32000

**AutonomousPlanner** (`planner.py`):
- Takes `AnalysisResult`, generates structured `AutonomousPlan`
- Each `PlanStep` has: action, tool_or_workflow, parameters, expected_outcome, fallback_action, requires_approval flag
- Available tools: `shell_command`, `azure_vm`, `azure_monitor`, `servicenow`, `teams_notify`, `file_operation`, `database_query`
- Plan includes risk_level, preconditions, success_criteria

**PlanExecutor** (`executor.py`):
- Streaming execution via `execute_stream(plan)` yielding `ExecutionEvent` objects
- Event types: `STEP_STARTED`, `STEP_COMPLETED`, `STEP_FAILED`, `PLAN_COMPLETED`, `PLAN_FAILED`
- Approval gate: pauses for human approval on `requires_approval` steps
- Tool executor callback pattern for actual tool invocation

**ResultVerifier** (`verifier.py`):
- Post-execution validation against success criteria
- Produces `VerificationResult`: expected_outcomes_met/failed, quality_score, lessons_learned
- Learning mechanism for future plan improvement

### 6.3 Error Recovery (Sprint 80)

**RetryPolicy** (`retry.py`):
- Failure classification: `TRANSIENT`, `RESOURCE`, `PERMISSION`, `CONFIGURATION`, `LOGIC`, `EXTERNAL`, `UNKNOWN`
- Configurable `RetryConfig`: max_attempts (3), base_delay (1.0s), max_delay (60s), exponential backoff, jitter
- `with_retry` decorator for wrapping async functions

**SmartFallback** (`fallback.py`, 587 LOC):
- 6 strategies: `RETRY`, `ALTERNATIVE`, `SKIP`, `ESCALATE`, `ROLLBACK`, `ABORT`
- `FailureAnalysis`: classifies errors, determines recoverability, recommends strategy with confidence score
- `FailurePattern` recording for learning from past failures
- Generates alternative `FallbackAction` with modified parameters and success probability estimates

---

## 7. Hybrid Selector (`hybrid/`)

### 7.1 Types (`types.py`)

- `TaskCapability` enum: `CODE_EXECUTION`, `FILE_OPERATION`, `WEB_SEARCH`, `MULTI_AGENT`, `HANDOFF`, `DOCUMENT_PROCESSING`, `CONVERSATION`, `ANALYSIS`, `PLANNING`
- `TaskAnalysis`: prompt analysis result with detected capabilities and scores
- `HybridSessionConfig`: timeout, max_tokens, auto_switch, sync_interval settings

### 7.2 CapabilityMatcher (`capability.py`)

- Keyword-based capability detection from prompts
- `CAPABILITY_KEYWORDS` dict mapping TaskCapability → keyword lists
- `FRAMEWORK_CAPABILITIES` mapping:
  - **MAF**: `MULTI_AGENT`, `HANDOFF`, `CODE_EXECUTION`, `FILE_OPERATION`, `DOCUMENT_PROCESSING`
  - **Claude SDK**: `CONVERSATION`, `ANALYSIS`, `PLANNING`, `WEB_SEARCH`
- Returns `CapabilityScore` per capability with matched keywords and context relevance

### 7.3 FrameworkSelector (`selector.py`)

- Scores each framework based on capability matches
- Considers: keyword match strength, capability overlap, historical performance
- Returns framework recommendation: `"microsoft_agent_framework"` or `"claude_sdk"`
- Supports confidence threshold — falls back to default if below threshold

### 7.4 HybridOrchestrator (`orchestrator.py`, 546 LOC)

- Main execution coordinator between MAF and Claude SDK
- `execute_task(prompt)` flow:
  1. CapabilityMatcher analyzes prompt
  2. FrameworkSelector chooses framework
  3. Routes to `_execute_claude()` or `_execute_maf()`
  4. ContextSynchronizer maintains state across frameworks
- `ExecutionContext` tracks: conversation_history, current_framework, tool_results
- `HybridResult` contains: content, framework_used, tool_calls, duration, tokens

### 7.5 ContextSynchronizer (`synchronizer.py`, 892 LOC)

- Bidirectional context conversion between 5 formats:
  - `CLAUDE_SDK`, `MICROSOFT_AGENT`, `UNIFIED`, `AG_UI`, `RAW`
- `SyncDirection`: `CLAUDE_TO_MS`, `MS_TO_CLAUDE`, `BIDIRECTIONAL`
- `ContextSnapshot` for point-in-time state capture with restore
- Message history format conversion (Claude messages ↔ MAF activities)
- Metadata and tool state synchronization
- **Known issue**: In-memory dict without locks (noted in integrations CLAUDE.md); Sprint 119 unified version uses Redis distributed locks

---

## 8. MCP Integration (`mcp/`)

### 8.1 Transport Layer

**MCPServer** (abstract base, `base.py`):
- Abstract methods: `_connect()`, `_disconnect()`, `_send_message()`, `list_tools()`, `execute_tool()`
- State management: `DISCONNECTED` → `CONNECTING` → `CONNECTED` → `ERROR`
- Health check, reconnection logic, error handling

**MCPStdioServer** (`stdio.py`):
- Launches local process via `asyncio.create_subprocess_exec`
- JSON-RPC over stdin/stdout
- Configurable: `command`, `args`, `env`, `cwd`
- Process lifecycle management with cleanup

**MCPHTTPServer** (`http.py`):
- Remote HTTP POST with JSON-RPC protocol
- Uses `aiohttp.ClientSession` (optional dependency)
- Configurable: `url`, `headers`, auth tokens
- Connection pooling via aiohttp session

### 8.2 MCP Types (`types.py`)

- `MCPTransportType`: `STDIO`, `HTTP`
- `MCPServerConfig`: name, transport, command/args (stdio), url/headers (http), timeout, max_retries
- `MCPMessage`: JSON-RPC message structure (method, params, id)
- `MCPToolDefinition`: name, description, input_schema (maps to Claude tool format)
- `MCPToolResult`: content, is_error, metadata

### 8.3 Tool Discovery (`discovery.py`, 519 LOC)

- Discovers and indexes tools from all connected MCP servers
- `ToolIndex`: maps tool names to server + definition
- Handles tool name conflicts across servers (prefixing with server name)
- Caching with configurable TTL
- Search/filter tools by name pattern or capability

### 8.4 MCPManager (`manager.py`, 519 LOC)

- Manages lifecycle of multiple MCP servers
- `add_server()`, `remove_server()`, `start_all()`, `stop_all()`
- Context manager support: `async with manager:`
- `discover_tools()` — aggregates tools from all servers
- `execute_tool(server_name, tool_name, args)` — routes to correct server
- `health_check()` — checks all server health with latency reporting
- `list_servers()` — returns `ServerInfo` for each managed server

### 8.5 Exception Hierarchy (`exceptions.py`)

```
MCPError
├── MCPConnectionError (server_name, command)
├── MCPToolError (server_name, tool_name)
├── MCPTimeoutError
├── MCPToolNotFoundError
├── MCPServerError
├── MCPDisconnectedError
├── MCPProtocolError
├── MCPAuthenticationError
├── MCPRateLimitError
├── MCPInvalidResponseError
└── MCPResourceExhaustedError
```

---

## 9. Orchestrator / Multi-Agent Coordination (`orchestrator/`)

### 9.1 Types (`types.py`)

- `TaskComplexity`: `SIMPLE`, `MODERATE`, `COMPLEX`, `CRITICAL`
- `ExecutionMode`: `SEQUENTIAL`, `PARALLEL`, `PIPELINE`, `ADAPTIVE`
- `AgentStatus`: `IDLE`, `BUSY`, `ERROR`, `OFFLINE`
- `AgentInfo`: name, capabilities, status, max_concurrent_tasks
- `ComplexTask`: description, required_capabilities, constraints, priority
- `Subtask`: allocated portion with assigned agent, dependencies, timeout
- `CoordinationResult`: all subtask results, overall status, total duration

### 9.2 ClaudeCoordinator (`coordinator.py`, 522 LOC)

Sprint 81 — Claude-led multi-agent coordination:

1. **Task Analysis**: Analyzes complexity, identifies required capabilities
2. **Agent Selection**: Matches capabilities to available agents via `AgentSelection`
3. **Subtask Allocation**: Uses `TaskAllocator` to distribute work
4. **Execution**: Supports PARALLEL (asyncio.gather) and SEQUENTIAL modes
5. **Result Aggregation**: Merges subtask results via `ContextManager`
6. **Swarm Integration**: Optional `SwarmIntegration` callbacks for real-time tracking

### 9.3 TaskAllocator (`task_allocator.py`)

- Complexity analysis based on task description
- `AgentExecutor` callback pattern for actual agent invocation
- Dependency-aware execution ordering
- Timeout and retry handling per subtask
- Load balancing across available agents

### 9.4 ContextManager (`context_manager.py`)

- Cross-agent context sharing via `ContextTransfer`
- Result merging from multiple subtask executions
- Shared state management for coordinated agents
- Context scoping to prevent information leakage between unrelated subtasks

---

## 10. Type System & Exceptions

### 10.1 Core Types (`types.py`)

| Type | Purpose |
|------|---------|
| `ToolCall` | Tool invocation record (id, name, args, result, duration) |
| `Message` | Conversation message (role, content, tool_calls, timestamp) |
| `ToolCallContext` | Hook interception context (tool_name, args, session_id, tool_source) |
| `ToolResultContext` | Post-execution hook context (tool_name, result, success, duration) |
| `QueryContext` | Query-level hook context (prompt, session_id, tools) |
| `HookResult` | Hook decision: ALLOW, reject(reason), modify(args) |
| `QueryResult` | One-shot result (content, tool_calls, tokens_used, duration, status) |
| `SessionResponse` | Session query result (content, tool_calls, tokens_used, message_index) |

### 10.2 Exception Hierarchy

```
ClaudeSDKError (base, with message + details dict)
├── AuthenticationError — API key missing/invalid
├── RateLimitError — with retry_after seconds
├── TimeoutError — operation exceeded timeout
├── ToolError — tool execution failure (tool_name, tool_args)
├── HookRejectionError — hook denied operation (hook_name)
└── MCPError — MCP operation failure
    ├── MCPConnectionError, MCPToolError, MCPTimeoutError
    ├── MCPToolNotFoundError, MCPServerError, MCPDisconnectedError
    ├── MCPProtocolError, MCPAuthenticationError
    ├── MCPRateLimitError, MCPInvalidResponseError
    └── MCPResourceExhaustedError
```

---

## 11. Sprint History

| Sprint | Phase | Feature | Key Files |
|--------|-------|---------|-----------|
| S48 | 12 | Core SDK Integration | client.py, query.py, session.py, config.py, types.py, exceptions.py |
| S49 | 12 | Tools + Hooks System | tools/*, hooks/* |
| S50 | 12 | Hybrid + MCP | hybrid/*, mcp/* |
| S68 | 17 | UserSandboxHook | hooks/sandbox.py (per-user isolation) |
| S75 | 19 | File Attachments | query.py (multimodal content) |
| S79 | 21 | Autonomous Planning | autonomous/analyzer.py, planner.py, executor.py, verifier.py |
| S80 | 21 | State + Fallback | session_state.py, autonomous/retry.py, autonomous/fallback.py |
| S81 | 21 | Multi-Agent Orchestration | orchestrator/* |
| S104 | 27 | Extended Thinking | client.py (execute_with_thinking streaming) |

---

## 12. Verification: Real Integration Assessment

### Evidence of Real Anthropic SDK Usage

1. **Direct import**: `from anthropic import AsyncAnthropic` in client.py line 6
2. **Client instantiation**: `self._client = AsyncAnthropic(api_key=..., base_url=..., timeout=...)` in client.py line 67-71
3. **API calls**: `self._client.messages.create(model=..., max_tokens=..., messages=..., tools=...)` in query.py line 117 and session.py line 121
4. **Streaming**: `self._client.messages.stream(**kwargs, extra_headers={"anthropic-beta": "extended-thinking-2024-10"})` in client.py line 262
5. **Response parsing**: Accesses `response.content`, `block.type == "tool_use"`, `block.id`, `block.name`, `block.input`, `response.usage.input_tokens` — all real Anthropic SDK response structures
6. **Token tracking**: Accumulates `input_tokens + output_tokens` from `response.usage`

### What Is NOT Mocked

- The `AsyncAnthropic` client is the real Anthropic Python SDK client
- Tool definitions follow the real Claude API tool schema format
- The agentic loop (tool_use detection → execute → feed back → repeat) matches the official Claude agent pattern
- Extended Thinking uses the real beta header protocol

### Limitations / Gaps

| Item | Status |
|------|--------|
| MCP tool integration in registry | Stubbed (`# TODO` in registry.py line 85) |
| Streaming in Session.query() | Not implemented (`stream` param accepted but unused) |
| ContextSynchronizer thread safety | In-memory dict without locks (fixed in Sprint 119 unified version) |
| Tool auto-registration | Tools must be manually registered; no auto-discovery from tool classes |

---

## 13. Cross-Reference: Feature E3 (Claude SDK)

The Claude SDK integration fully implements Feature E3 requirements:

- **E3.1 Core Client**: AsyncAnthropic client with config management ✅
- **E3.2 Session Management**: Multi-turn sessions with history ✅
- **E3.3 Tool System**: 10 built-in tools with registry ✅
- **E3.4 Hook System**: 4 hooks with chain execution ✅
- **E3.5 MCP Integration**: Stdio + HTTP transports with manager ✅
- **E3.6 Hybrid Selection**: Capability matching + framework routing ✅
- **E3.7 Autonomous Planning**: Full analyze→plan→execute→verify pipeline ✅
- **E3.8 Multi-Agent Coordination**: ClaudeCoordinator with task allocation ✅
- **E3.9 State Persistence**: PostgreSQL + mem0 sync ✅
- **E3.10 Extended Thinking**: Streaming with beta header ✅

---

## 14. File Inventory

```
backend/src/integrations/claude_sdk/
├── __init__.py              (94 lines)    # 41 exports
├── client.py                (357 lines)   # ClaudeSDKClient — AsyncAnthropic
├── config.py                (76 lines)    # ClaudeSDKConfig dataclass
├── exceptions.py            (76 lines)    # 7 exception types
├── query.py                 (345 lines)   # One-shot agentic loop + attachments
├── session.py               (287 lines)   # Multi-turn agentic loop + fork
├── session_state.py         (576 lines)   # Persistence + compression + mem0
├── types.py                 (130 lines)   # Core type definitions
│
├── autonomous/              (7 files, ~2,587 LOC)
│   ├── __init__.py          # Exports all autonomous types
│   ├── types.py             # EventSeverity, PlanStatus, StepStatus, RiskLevel
│   ├── analyzer.py          # EventAnalyzer — Extended Thinking analysis
│   ├── planner.py           # AutonomousPlanner — decision tree generation
│   ├── executor.py          # PlanExecutor — streaming execution
│   ├── verifier.py          # ResultVerifier — validation + learning
│   ├── retry.py             # RetryPolicy — failure classification
│   └── fallback.py          # SmartFallback — 6 recovery strategies
│
├── hooks/                   (5 files, ~1,384 LOC)
│   ├── __init__.py          # Exports all hooks
│   ├── base.py              # Hook ABC + HookChain
│   ├── approval.py          # ApprovalHook (priority 90)
│   ├── audit.py             # AuditHook (priority 50) + redaction
│   ├── rate_limit.py        # RateLimitHook (priority 70)
│   └── sandbox.py           # SandboxHook (priority 85) + UserSandboxHook
│
├── hybrid/                  (6 files, ~2,166 LOC)
│   ├── __init__.py          # Exports hybrid orchestration
│   ├── types.py             # TaskCapability, HybridSessionConfig
│   ├── capability.py        # CapabilityMatcher — keyword scoring
│   ├── selector.py          # FrameworkSelector — MAF vs Claude
│   ├── orchestrator.py      # HybridOrchestrator (546 LOC)
│   └── synchronizer.py      # ContextSynchronizer (892 LOC) — 5 formats
│
├── mcp/                     (7 files, ~3,207 LOC)
│   ├── __init__.py          # Exports MCP types + factories
│   ├── types.py             # MCPServerConfig, MCPToolDefinition
│   ├── exceptions.py        # 11 MCP exception types
│   ├── base.py              # MCPServer abstract base
│   ├── stdio.py             # MCPStdioServer — local process
│   ├── http.py              # MCPHTTPServer — remote HTTP
│   ├── discovery.py         # ToolDiscovery (519 LOC)
│   └── manager.py           # MCPManager (519 LOC)
│
├── orchestrator/            (4 files, ~1,630 LOC)
│   ├── __init__.py          # Exports coordination types
│   ├── types.py             # TaskComplexity, ExecutionMode, AgentInfo
│   ├── context_manager.py   # ContextManager — cross-agent context
│   ├── task_allocator.py    # TaskAllocator — subtask distribution
│   └── coordinator.py       # ClaudeCoordinator (522 LOC)
│
└── tools/                   (6 files, ~1,462 LOC)
    ├── __init__.py           # Exports all tools + registry
    ├── base.py               # Tool ABC + ToolResult
    ├── file_tools.py         # Read, Write, Edit, MultiEdit, Glob, Grep
    ├── command_tools.py      # Bash (security controls), Task (subagents)
    ├── web_tools.py          # WebSearch, WebFetch
    └── registry.py           # ToolRegistry — registration + dispatch
```

**Total**: 47 files, ~11,625 LOC
