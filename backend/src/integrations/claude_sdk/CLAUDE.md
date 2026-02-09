# Claude Agent SDK Integration

> Phase 12 | 44 Python files, ~15,000 LOC | Claude AI agent with autonomous planning, hooks, MCP, and tools

---

## Directory Structure

```
claude_sdk/
├── __init__.py             # 41 exports (client, types, exceptions, session state)
├── config.py               # ClaudeSDKConfig (API key, model, tokens, timeout)
├── exceptions.py           # Exception hierarchy (12+ types)
├── types.py                # ToolCall, Message, HookResult, QueryResult
├── client.py               # ClaudeSDKClient (356 LOC) — Main entry point
├── query.py                # QueryExecutor (344 LOC) — One-shot queries
├── session.py              # Session (286 LOC) — Multi-turn conversations
├── session_state.py        # SessionStateManager (575 LOC) — Persistence + mem0
│
├── autonomous/             # Autonomous planning engine (2,587 LOC)
│   ├── types.py            # EventSeverity, PlanStatus, StepStatus, RiskLevel
│   ├── analyzer.py         # EventAnalyzer — Extended Thinking event analysis
│   ├── planner.py          # AutonomousPlanner — Decision tree generation
│   ├── executor.py         # PlanExecutor — Streaming plan execution
│   ├── verifier.py         # ResultVerifier — Validation and learning
│   ├── retry.py            # RetryPolicy — Failure classification (S80)
│   └── fallback.py         # SmartFallback — Intelligent error recovery (S80)
│
├── hooks/                  # Tool call interception (1,384 LOC)
│   ├── base.py             # Hook, HookChain — Base classes
│   ├── approval.py         # ApprovalHook — Human confirmation for writes
│   ├── audit.py            # AuditHook — Logging with redaction
│   ├── rate_limit.py       # RateLimitHook — Rate limiting
│   └── sandbox.py          # SandboxHook — File access restrictions
│
├── hybrid/                 # Hybrid orchestration (2,166 LOC)
│   ├── types.py            # Framework, HybridResult, TaskAnalysis
│   ├── capability.py       # CapabilityMatcher — Task→framework mapping
│   ├── selector.py         # FrameworkSelector — Optimal framework choice
│   ├── orchestrator.py     # HybridOrchestrator (546 LOC) — Execution coordinator
│   └── synchronizer.py     # ContextSynchronizer (892 LOC) — Context format sync
│
├── mcp/                    # MCP client integration (3,207 LOC)
│   ├── types.py            # MCPServerConfig, MCPTransportType, MCPToolDefinition
│   ├── exceptions.py       # 11 MCP-specific exception types
│   ├── base.py             # MCPServer abstract base
│   ├── stdio.py            # MCPStdioServer — Local process servers
│   ├── http.py             # MCPHTTPServer — Remote HTTP servers
│   ├── discovery.py        # ToolDiscovery — Tool indexing (519 LOC)
│   └── manager.py          # MCPManager — Multi-server lifecycle (519 LOC)
│
├── orchestrator/           # Multi-agent coordination (1,630 LOC)
│   ├── types.py            # TaskComplexity, ExecutionMode, AgentStatus
│   ├── context_manager.py  # ContextManager — Cross-agent context
│   ├── task_allocator.py   # TaskAllocator — Subtask distribution
│   └── coordinator.py      # ClaudeCoordinator (522 LOC) — S81 agent coordination
│
└── tools/                  # Built-in tool implementations (1,462 LOC)
    ├── base.py             # Tool, ToolResult abstract classes
    ├── file_tools.py       # Read, Write, Edit, MultiEdit, Glob, Grep
    ├── command_tools.py    # Bash, Task
    ├── web_tools.py        # WebSearch, WebFetch
    └── registry.py         # ToolRegistry — Registration and discovery
```

---

## Architecture

```
┌──────────────────────────────────────────┐
│            ClaudeSDKClient               │
│  ├─ query(prompt) → One-shot            │
│  └─ create_session() → Multi-turn       │
└──────────┬───────────────────────────────┘
           │
    ┌──────▼──────────────────────┐
    │   QueryExecutor / Session   │
    └──────┬──────────────────────┘
           │
    ┌──────▼──────────────────────┐
    │      Hook Chain             │
    │  Approval → Audit →         │
    │  RateLimit → Sandbox        │
    └──────┬──────────────────────┘
           │
    ┌──────▼────────┬─────────────┐
    │ Built-in Tools│ MCP Servers │
    │ (file, cmd,   │ (stdio,     │
    │  web)         │  http)      │
    └───────────────┴─────────────┘
           │
    ┌──────▼──────────────────────┐
    │    Anthropic AsyncAPI       │
    └─────────────────────────────┘
```

---

## Key Classes

| Class | File | LOC | Purpose |
|-------|------|-----|---------|
| **ClaudeSDKClient** | client.py | 356 | Main entry: one-shot queries + session management |
| **ContextSynchronizer** | hybrid/synchronizer.py | 892 | Context format conversion (5 formats) |
| **SmartFallback** | autonomous/fallback.py | 587 | Intelligent fallback strategies |
| **SessionStateManager** | session_state.py | 575 | State persistence + compression + mem0 |
| **HybridOrchestrator** | hybrid/orchestrator.py | 546 | Routes tasks between MAF and Claude |
| **ClaudeCoordinator** | orchestrator/coordinator.py | 522 | Claude-led multi-agent coordination |
| **MCPManager** | mcp/manager.py | 519 | Multi-server lifecycle and tool discovery |
| **ToolDiscovery** | mcp/discovery.py | 519 | Discovers and indexes tools |
| **SandboxHook** | hooks/sandbox.py | 502 | File access control (strict/user modes) |

---

## Sprint History

| Sprint | Feature | Key Files |
|--------|---------|-----------|
| S48 | Core SDK Integration | client.py, query.py, session.py |
| S49 | Tools + Hooks System | tools/, hooks/ |
| S50 | Hybrid + MCP | hybrid/, mcp/ |
| S75 | File Attachments | query.py (attachment support) |
| S79 | Autonomous Planning | autonomous/ (analyzer, planner, executor) |
| S80 | State + Fallback | session_state.py, autonomous/fallback.py |
| S81 | Multi-Agent Orchestration | orchestrator/ |

---

## Autonomous Planning Flow

```
IT Event → EventAnalyzer (Extended Thinking)
    ↓
AutonomousPlanner → Decision tree
    ↓
PlanExecutor (streaming) → Execute steps
    ↓ (on failure)
SmartFallback → Retry / Switch framework / Degrade / Escalate
    ↓
ResultVerifier → Validate + Learn
```

---

## Exception Hierarchy

```
ClaudeSDKError
├── AuthenticationError
├── RateLimitError
├── TimeoutError
├── ToolError
├── HookRejectionError
└── MCPError
    ├── MCPConnectionError
    ├── MCPToolError
    ├── MCPTimeoutError
    └── MCPToolNotFoundError
```

---

**Last Updated**: 2026-02-09
