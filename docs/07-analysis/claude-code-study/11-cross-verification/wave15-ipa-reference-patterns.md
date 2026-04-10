# IPA Platform Reference Patterns from Claude Code

> **Wave**: 15 | **Date**: 2026-04-01
> **Sources**: Wave 6 (Permission), Wave 7 (Context Compression), Wave 8 (Agent Lifecycle), Wave 10 (MCP), Design Patterns
> **Target**: IPA Platform V9 (Phase 1-44, 1,028 files, 327,582 LOC)

---

## Directly Applicable Patterns

### 1. Multi-Layer Permission Cascade with Bypass-Immune Safety Checks

- **Claude Code implementation**: A strict priority-ordered decision cascade in `permissions.ts` — deny rules checked first, then ask rules, then tool-specific `checkPermissions()`, then safety checks (protected paths like `.git/`, `.claude/`), then mode-specific transforms. Safety checks are **bypass-immune**: even `bypassPermissions` mode cannot skip them. Rules are loaded from 8 sources with clear precedence (enterprise > local > project > user > plugin > session). See Wave 6 Section 2 for the complete 3-step inner + mode-transform outer cascade.
- **IPA Platform application**: IPA's 6-Layer Defense-in-Depth security model (V9 `06-cross-cutting/security-architecture.md`) could adopt this cascading permission model for its tool execution layer. Currently, IPA has agent permission checks but lacks a unified cascade across all 591 API endpoints. The pattern maps directly to IPA's hybrid orchestration layer (Layer 5) where MAF and Claude SDK agents execute tools with varying trust levels.
- **Adaptation needed**: Replace CC's CLI-focused modes (acceptEdits, plan, bypassPermissions) with enterprise RBAC roles (admin, operator, viewer). Add tenant isolation at the rule source level. Map CC's 8 rule sources to IPA's equivalent: enterprise policy, organization config, project settings, user preferences, session overrides.
- **Priority**: HIGH — IPA Issue Registry shows 8 CRITICAL issues, several related to incomplete authorization checks.

### 2. Four-Tier Context Compression Strategy

- **Claude Code implementation**: A layered defense against context overflow in `autoCompact.ts` + `microCompact.ts` + `sessionMemoryCompact.ts`: Tier 0 (time-based microcompact clears stale tool results after 60min gap), Tier 1 (cached microcompact uses API-layer cache_edits), Tier 2 (session memory compact — no LLM call, uses pre-extracted memory), Tier 3 (full LLM summarization via forked agent). Exact thresholds: autocompact buffer 13K tokens, max output 20K tokens, post-compact restoration capped at 5 files / 50K tokens. Circuit breaker trips after 3 consecutive failures. See Wave 7 Sections 2-8.
- **IPA Platform application**: IPA's chat sessions (unified-chat with 27+ components) and agent execution contexts accumulate tool results, AG-UI events, and conversation history. The four-tier approach maps to: (1) clear stale AG-UI SSE event payloads from session state, (2) use Redis-cached summaries for recent context, (3) use mem0/Qdrant session memory as summary source (no LLM call), (4) LLM-based summarization for long-running workflow executions.
- **Adaptation needed**: Replace CC's token-counting with IPA's session state size tracking. Integrate with existing mem0 memory system (`QDRANT_PATH=./qdrant_data`). Add the circuit breaker pattern to IPA's LLM integration layer to prevent wasted API calls on repeated failures.
- **Priority**: HIGH — Long-running agent workflows and swarm sessions will hit context limits. This directly addresses enterprise cost control.

### 3. Agent Lifecycle with 6-Way Routing and Deterministic Cleanup

- **Claude Code implementation**: `AgentTool.call()` implements a 6-way routing decision tree: teammate spawn > fork subagent > remote isolation > async background > sync foreground > foreground-to-background transition. Each path has explicit guards (nested teammate prevention, recursive fork guard, MCP server readiness with 30s timeout). The `runAgent()` async generator has a 10-step deterministic cleanup in a `finally` block: MCP disconnect, hook cleanup, tracking cleanup, file state release, message release, perfetto unregister, transcript cleanup, todo cleanup, shell task kill, monitor task kill. See Wave 8 Sections 1-2.
- **IPA Platform application**: IPA's agent system (Layer 6 MAF builders + Layer 7 Claude SDK) has 23+ builder types but lacks unified lifecycle management. The 6-way routing maps to IPA's three-tier intent routing (Layer 4): simple/complex/autonomous classification could be extended with teammate spawn (swarm), background execution, and foreground-to-background transition (critical for long-running enterprise workflows). The 10-step cleanup checklist is directly applicable to IPA's agent execution cleanup.
- **Adaptation needed**: Adapt CC's single-process model to IPA's distributed architecture (FastAPI + PostgreSQL + Redis + RabbitMQ). Replace CC's `AbortController` with IPA's existing cancellation mechanism via RabbitMQ messages. Add database state persistence for agent lifecycle (CC uses in-memory only). Map CC's task eviction (30s grace period) to IPA's execution history retention policy.
- **Priority**: HIGH — IPA V9 Issue Registry identifies resource leak issues in agent lifecycle. This pattern provides a proven cleanup model.

### 4. Promise.race Foreground-to-Background Transition

- **Claude Code implementation**: Sync agents run in a `Promise.race` loop between message iteration and a background signal (`backgroundPromise`). When Ctrl+B or auto-timer (120s) fires, the foreground iterator is `.return()`-ed (triggers cleanup), existing messages are replayed into a new progress tracker, and a **new** `runAgent()` is spawned with `isAsync=true`. This preserves continuity while unblocking the parent. See Wave 8 Section 4.
- **IPA Platform application**: IPA's workflow execution engine handles long-running processes that users may want to background. Currently, the AG-UI SSE streaming connection must remain open. Adopting this pattern allows users to start a workflow synchronously (seeing real-time progress), then background it when confident, receiving a notification on completion.
- **Adaptation needed**: Replace CC's in-process Promise.race with IPA's WebSocket/SSE connection management. Use RabbitMQ for the background signal instead of in-process Promise resolution. Store progress state in PostgreSQL so backgrounded tasks survive server restarts (CC's model is ephemeral).
- **Priority**: MEDIUM — Enhances UX for long-running enterprise workflows but not a blocking issue.

### 5. MCP Configuration Aggregation with Enterprise Override

- **Claude Code implementation**: `getAllMcpConfigs()` in `config.ts` merges MCP server configs from 6 scopes with strict precedence: enterprise (exclusive) > local > project > user > plugin > claude.ai. Enterprise `managed-mcp.json` has exclusive control — when present, all other scopes are ignored. Three dedup functions prevent duplicate connections using signature-based matching. Policy filtering via allowlist/denylist with name/command/URL matching (denylist always wins). See Wave 10 Section 1.1.
- **IPA Platform application**: IPA already has 5 MCP tool servers (Azure, Filesystem, LDAP, Shell, SSH) in Layer 8. The enterprise override pattern maps directly to IPA's multi-tenant deployment model: organization-level MCP configs override project-level configs. The dedup and policy filtering patterns are essential for preventing tool conflicts when multiple agents in a swarm share MCP servers.
- **Adaptation needed**: Replace CC's file-based config with IPA's database-backed configuration (PostgreSQL). Add tenant-scoped MCP configs alongside the existing global config. Implement the allowlist/denylist pattern in IPA's MCP integration layer for compliance (enterprise customers need to restrict which tools agents can access).
- **Priority**: HIGH — Enterprise MCP governance is a gap identified in V9 analysis. CC's pattern is production-proven.

### 6. Connection Batching with Transport-Aware Concurrency

- **Claude Code implementation**: MCP server connections are partitioned into local (stdio/sdk, concurrency=3) and remote (sse/http/ws, concurrency=20), using `pMap` for slot-based scheduling. 10 transport types supported. Connection timeout of 30s with Promise.race. Memoized tool/resource discovery with LRU cache (size 20), invalidated on `client.onclose`. See Wave 10 Sections 1.2-1.5.
- **IPA Platform application**: IPA's MCP integration connects to multiple tool servers during agent execution. Currently connections appear sequential. Adopting batched connection with transport-aware concurrency would improve swarm startup time (Phase 29+ swarm system with 15 components) where multiple agents need simultaneous MCP access.
- **Adaptation needed**: Implement in Python using `asyncio.Semaphore` for concurrency control instead of CC's `pMap`. Add connection pooling at the FastAPI application level (not per-request). Use IPA's Redis for memoized discovery cache instead of in-memory LRU.
- **Priority**: MEDIUM — Performance optimization for swarm scenarios.

### 7. Reconnection with Session Expiry Recovery

- **Claude Code implementation**: Three-tier error handling: (1) 3 consecutive terminal errors (`ECONNRESET`, `ETIMEDOUT`) trigger transport close, (2) HTTP 404 + JSON-RPC `-32001` triggers session expiry handling (close, clear cache, throw `McpSessionExpiredError`), (3) tool call retry on `McpSessionExpiredError` with fresh client via `ensureConnectedClient()`. Cleanup escalation for stdio: SIGINT > 100ms > SIGTERM > 400ms > SIGKILL. See Wave 10 Section 8.
- **IPA Platform application**: IPA's MCP tool servers run as subprocesses or remote services. The reconnection pattern with consecutive error tracking prevents cascading failures when a tool server becomes temporarily unavailable during a multi-step agent workflow.
- **Adaptation needed**: Replace CC's process signal escalation with Docker container health checks for IPA's containerized MCP servers. Implement the consecutive error counter in IPA's existing circuit breaker infrastructure. Add session expiry handling to IPA's MCP client wrapper.
- **Priority**: MEDIUM — Resilience pattern important for production enterprise deployment.

### 8. Circuit Breaker Pattern for Expensive Operations

- **Claude Code implementation**: Auto-compact circuit breaker trips after `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3`, preventing wasted API calls. Motivated by real production data: 1,279 sessions with 50+ consecutive failures consuming ~250K API calls/day. Resets on any success. Per-session scope. See Wave 7 Section 5.
- **IPA Platform application**: IPA's LLM integration layer makes Azure OpenAI API calls that can fail due to rate limits, model unavailability, or network issues. A circuit breaker per-session (or per-agent) would prevent runaway API costs when the LLM provider is degraded.
- **Adaptation needed**: Implement at the `backend/src/integrations/llm/` layer. Use IPA's Redis for cross-process circuit breaker state (CC uses in-memory only). Add configurable thresholds per LLM provider (Azure OpenAI vs Anthropic vs OpenAI).
- **Priority**: HIGH — Direct cost control mechanism for enterprise LLM usage.

### 9. Task State Machine with Eviction and Notification

- **Claude Code implementation**: Four distinct task types (LocalAgent, LocalShell, InProcessTeammate, Dream) each with explicit state machines: `running` > `completed|failed|killed`. Terminal transitions trigger: cleanup unregister, resource release, eviction timer (30s grace via `PANEL_GRACE_MS`), and notification delivery. Notifications are XML-structured and delivered at tool-round boundaries (not mid-execution). The `retain` flag blocks eviction when user is viewing a task. See Wave 8 Sections 3, 5.
- **IPA Platform application**: IPA's execution tracking (Layer 4-5) manages agent and workflow states but the V9 analysis shows inconsistent state management across different execution types. Adopting CC's unified state machine pattern with explicit terminal transitions, eviction, and notification would standardize behavior across IPA's agent types (MAF agents, Claude SDK agents, swarm workers, pipeline tasks).
- **Adaptation needed**: Persist state transitions to PostgreSQL (CC is in-memory). Replace CC's XML notifications with IPA's AG-UI SSE event format. Map CC's 30s eviction grace to IPA's configurable execution history retention. Add the `retain` flag concept to IPA's execution detail view.
- **Priority**: MEDIUM — Quality improvement for execution lifecycle consistency.

### 10. AsyncLocalStorage-Based Isolation for In-Process Agents

- **Claude Code implementation**: In-process teammates run in the same Node.js process as the leader but use `AsyncLocalStorage` for context isolation. Each teammate gets independent identity, permission mode, working directory, abort controller, and message queue. UI transcript capped at 50 entries while full conversation stored on disk. Shutdown protocol: graceful (flag-based, between turns) and hard (abort immediately). See Wave 8 Section 6.
- **IPA Platform application**: IPA's swarm system (Phase 29+) runs multiple agents that share backend resources. Python's `contextvars.ContextVar` is the equivalent of Node.js `AsyncLocalStorage`. This pattern enables IPA to run multiple swarm worker agents in the same FastAPI process with isolated contexts, reducing resource overhead compared to separate processes per agent.
- **Adaptation needed**: Use Python `contextvars` module for per-agent context isolation. Implement the message cap pattern for IPA's frontend swarm visualization (15 components). Add graceful shutdown protocol to IPA's existing swarm worker implementation.
- **Priority**: MEDIUM — Performance optimization for swarm density.

### 11. Factory Pattern for Agent/Tool Construction

- **Claude Code implementation**: Multiple factory patterns: `createCliExecutor()` with platform validation at construction time and native module loading once via closure; `generateTaskId()` with type-prefixed IDs using a safe alphabet; MCP tool factory that builds per-tool instances from a template `MCPTool` with overridden methods. See Design Patterns Sections 1, 3.1.
- **IPA Platform application**: IPA's 23+ MAF builders (Layer 6) already use a builder pattern, but tool construction in the MCP layer (Layer 8) could benefit from CC's factory approach. Creating typed tool instances with validation at construction time (fail-fast) would catch configuration errors before execution.
- **Adaptation needed**: Apply to IPA's `backend/src/integrations/mcp/` module. Add type-prefixed IDs for IPA's various entity types (agents, workflows, executions, tools) for easier debugging and log correlation.
- **Priority**: LOW — Code quality improvement.

### 12. Retry Strategy Composition

- **Claude Code implementation**: `withRetry` is an `AsyncGenerator` that yields status messages while retrying, composing 6 strategies: fast-mode fallback, cooldown, persistent retry, fallback model, auth refresh, and stale connection recovery. Each strategy has distinct trigger conditions and recovery actions. See Design Patterns Section 3.
- **IPA Platform application**: IPA's LLM integration and MCP tool calls would benefit from composed retry strategies instead of simple exponential backoff. The generator pattern allows streaming retry status to the frontend via AG-UI SSE events, giving users visibility into recovery attempts.
- **Adaptation needed**: Implement as a Python async generator in `backend/src/integrations/llm/`. Map CC's model fallback strategy to IPA's multi-model support (Azure OpenAI GPT-4o, GPT-5 family). Add retry status streaming via IPA's existing AG-UI SSE infrastructure.
- **Priority**: MEDIUM — Resilience and observability improvement.

### 13. Denial Tracking with Configurable Limits

- **Claude Code implementation**: `DenialTrackingState` tracks consecutive (max 3) and total (max 20) denials per session. Exceeding limits triggers fallback-to-prompting (interactive) or `AbortError` (headless). Total limit resets both counters after user review. Granular analytics via `logPermissionDecision()` with OTel integration. See Wave 6 Sections 8.
- **IPA Platform application**: IPA's agent execution can enter denial loops when tools are restricted or LLM calls fail. Implementing denial tracking would prevent agents from wasting tokens on repeated failed operations. The analytics integration maps to IPA's existing monitoring infrastructure.
- **Adaptation needed**: Track per-agent-execution rather than per-session. Store in Redis for cross-request persistence. Integrate with IPA's audit trail system (`backend/src/integrations/audit/`). Configure limits per agent type (autonomous agents may need higher thresholds).
- **Priority**: MEDIUM — Cost control and observability.

### 14. Elicitation (Human-in-the-Loop Mid-Execution Input)

- **Claude Code implementation**: MCP servers can request user input mid-execution via `ElicitRequestSchema` with two modes: form-based input dialog and URL-based external action. Hooks can resolve programmatically before showing UI. URL elicitation uses error code `-32042` with retry loop (max 3). Completion notification supports async external workflows. See Wave 10 Section 5.
- **IPA Platform application**: IPA already has HITL (Human-in-the-Loop) approval (V9 E2E Flow 4) but it is limited to approve/reject decisions. CC's elicitation pattern extends this to structured form input and external URL workflows — critical for enterprise scenarios like document signing, multi-level approval, or external system confirmation.
- **Adaptation needed**: Extend IPA's existing HITL components (`frontend/src/components/ag-ui/hitl/`) with form-based elicitation. Use IPA's AG-UI SSE events to deliver elicitation requests to the frontend. Add webhook support for external URL completion (replacing CC's notification schema).
- **Priority**: HIGH — Directly enhances IPA's HITL capability, a key enterprise differentiator.

---

## Architecture Insights for IPA

### Layered Defense Over Single Gatekeeping
CC's architecture demonstrates that security and resource management work best as **layered cascades** rather than single checkpoints. IPA should apply this principle to: permission checking (cascade across tenant > org > project > user), context management (tiered compression), and error handling (circuit breakers at each integration point).

### Deterministic Cleanup is Non-Negotiable
CC's 10-step cleanup in the `finally` block of `runAgent()` ensures zero resource leaks regardless of how an agent terminates. IPA's distributed architecture makes this harder but more important. Every agent execution should have a corresponding cleanup checklist persisted as a database record, with a background sweeper for orphaned resources.

### In-Memory State Machines with External Persistence
CC keeps state machines in-memory for performance but exports events for analytics. IPA should adopt this hybrid: fast in-memory state transitions during execution, with async persistence to PostgreSQL for audit trail and recovery. The current IPA approach of synchronous database writes on every state change adds latency.

### Forked Agent Pattern for Expensive Background Operations
CC uses forked agents for context compaction, sharing the parent's prompt cache to save ~98% of cache creation tokens. IPA could apply this for background operations like report generation, batch processing, or memory consolidation — forking from the current agent context rather than starting fresh.

### Configuration Precedence Must Be Explicit and Documented
CC's 6-scope configuration precedence (enterprise > local > project > user > plugin > claude.ai) with enterprise exclusive override is a model for multi-tenant enterprise software. IPA should formalize its configuration hierarchy with the same principle: managed policy always wins.

---

## Security Model Reference

### Permission Decision Cascade (CC -> IPA Mapping)

| CC Layer | CC Mechanism | IPA Equivalent | Gap |
|----------|-------------|----------------|-----|
| Deny rules (absolute) | Tool-level deny rules, always respected | API endpoint authorization | Need tool-level deny for MCP tools |
| Ask rules (conditional) | Content-specific prompts | HITL approval | Need content-aware approval triggers |
| Tool-specific checks | `tool.checkPermissions()` per tool | Per-builder permission check | Exists but inconsistent across 23 builders |
| Safety checks (bypass-immune) | Protected paths, shell security validators | Sensitive data protection | Need bypass-immune checks for PII/credentials |
| Mode transforms | bypassPermissions, auto, dontAsk | Role-based overrides | Need formalized mode system |
| Denial tracking | Consecutive (3) and total (20) limits | None | **Gap**: No denial tracking in IPA |
| Analytics | OTel + granular event logging | Audit trail | Need OTel integration for permission decisions |

### Bash Security Validators as Reference
CC's 23 security check IDs for shell commands (command substitution, shell metacharacter injection, obfuscated flags, IFS injection, Unicode whitespace, heredoc patterns) should be referenced when implementing IPA's Shell MCP server security. IPA's `backend/src/integrations/mcp/shell/` should implement equivalent validators.

### Enterprise Policy Override
CC's `managed-mcp.json` exclusive control pattern is the correct model for IPA's enterprise deployment. When an organization deploys IPA with managed policies, those policies should override all project-level and user-level settings without exception.

---

## Multi-Agent Coordination Reference

### Team/Swarm Architecture (CC -> IPA Mapping)

| CC Concept | CC Implementation | IPA Equivalent | Gap |
|-----------|------------------|----------------|-----|
| Teammate spawn | Flat roster, no nested teammates | Swarm worker agents | IPA allows nesting; consider CC's flat model |
| AsyncLocalStorage isolation | Per-teammate context in same process | `contextvars` for swarm workers | **Gap**: IPA uses separate processes |
| Message delivery timing | Tool-round boundary draining | AG-UI event queue | Need explicit delivery timing guarantees |
| Leader-to-worker messages | `pendingUserMessages` queue | RabbitMQ messages | Exists but lacks the idle/active state model |
| Permission forwarding | Swarm worker handler forwards to leader via mailbox | Centralized permission check | **Gap**: IPA has no delegated permission model |
| Plan approval flow | `awaitingPlanApproval` flag, UI prompt | HITL approval | Could extend HITL for swarm plan approval |
| Graceful shutdown | `shutdownRequested` flag, completes current work | Agent cancellation | **Gap**: IPA uses hard kill, no graceful shutdown |
| UI transcript cap | 50-message cap with full conversation on disk | Frontend message display | Should add cap for swarm visualization |

### Inter-Agent Communication Patterns

CC's message delivery model has a critical insight for IPA: **messages are delivered at tool-round boundaries, not mid-execution**. This prevents state corruption from concurrent message injection. IPA's swarm system should adopt this pattern:

1. **Enqueue**: Messages queued to agent's `pendingMessages` (Redis list in IPA's case)
2. **Drain**: At the boundary between tool executions, atomically read and clear the queue
3. **Inject**: Deliver as context for the next LLM call
4. **Never interrupt**: No message delivery during active tool execution

### Background Task Notification
CC's notification system uses priority levels (`next`, `later`, default) for task completion notifications. IPA's AG-UI event system should implement similar priority to ensure critical notifications (agent failure, HITL required) take precedence over informational ones (progress updates).

---

## Implementation Roadmap Summary

| Priority | Pattern | Effort | Impact |
|----------|---------|--------|--------|
| HIGH | Permission cascade with bypass-immune safety | Large | Security |
| HIGH | Four-tier context compression | Large | Cost + UX |
| HIGH | Agent lifecycle with deterministic cleanup | Medium | Reliability |
| HIGH | Circuit breaker for LLM calls | Small | Cost |
| HIGH | MCP enterprise configuration override | Medium | Enterprise |
| HIGH | Elicitation (extended HITL) | Medium | Feature |
| MEDIUM | FG-to-BG transition | Medium | UX |
| MEDIUM | Connection batching for MCP | Small | Performance |
| MEDIUM | MCP reconnection with session recovery | Small | Reliability |
| MEDIUM | Task state machine standardization | Medium | Quality |
| MEDIUM | AsyncLocalStorage isolation for swarm | Medium | Performance |
| MEDIUM | Retry strategy composition | Small | Resilience |
| MEDIUM | Denial tracking | Small | Observability |
| LOW | Factory pattern for tools | Small | Code quality |

---

*Analysis based on Claude Code source study (Waves 6, 7, 8, 10, Design Patterns) cross-referenced against IPA Platform V9 analysis (Phase 1-44, 1,028 files). All CC references point to verified source analysis documents in `docs/07-analysis/claude-code-study/`.*
