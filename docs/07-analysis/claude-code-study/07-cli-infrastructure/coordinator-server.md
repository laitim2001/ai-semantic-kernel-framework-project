# Coordinator Mode, Session History & Direct Connect Server

> Deep analysis of coordinator orchestration, cloud session rehydration, and headless server protocol.
> Source: `src/coordinator/coordinatorMode.ts`, `src/assistant/sessionHistory.ts`, `src/server/` (3 files)

---

## 1. Coordinator Mode (`coordinatorMode.ts`, 369 LOC)

### Purpose

Enables **Coordinator Mode** -- a fundamentally different operating mode where Claude Code acts as an orchestrator that delegates work to parallel "worker" sub-agents instead of executing tools directly. This is the multi-agent architecture's control plane toggle.

### Feature Flags Required

| Flag/Gate | Mechanism | Purpose |
|-----------|-----------|---------|
| `COORDINATOR_MODE` | `feature()` from `bun:bundle` (compile-time) | Build-level gate; if off, coordinator mode is impossible |
| `CLAUDE_CODE_COORDINATOR_MODE` | `process.env` (runtime) | Runtime toggle; must be truthy |
| `tengu_scratch` | Statsig feature gate (`checkStatsigFeatureGate_CACHED_MAY_BE_STALE`) | Enables scratchpad directory for cross-worker shared state |
| `CLAUDE_CODE_SIMPLE` | `process.env` (runtime) | Restricts worker tool set to Bash + Read + Edit only |

### How It's Loaded

- **Conditional, not lazy**. The module is imported directly but all behavior is gated behind `isCoordinatorMode()` which checks both the compile-time bundle feature AND the runtime env var. Returns `false` immediately if either is off.
- No dynamic `import()` -- always bundled but functionally inert when disabled.

### Key Functions

| Function | Signature | Role |
|----------|-----------|------|
| `isCoordinatorMode()` | `() => boolean` | Central predicate -- checks bundle feature + env var |
| `matchSessionMode(sessionMode)` | `('coordinator' \| 'normal' \| undefined) => string \| undefined` | Session resumption: flips env var to match stored session mode, returns warning message if switched. Emits `tengu_coordinator_mode_switched` analytics event |
| `getCoordinatorUserContext(mcpClients, scratchpadDir?)` | `(ReadonlyArray<{name}>, string?) => Record<string,string>` | Builds context injection describing worker capabilities -- tool list, MCP servers, scratchpad path |
| `getCoordinatorSystemPrompt()` | `() => string` | Returns the full coordinator system prompt (~250 lines of structured instructions) |

### Architecture Role

This is the **brain of the multi-agent system**. The coordinator system prompt (returned by `getCoordinatorSystemPrompt()`) defines:

1. **Role**: Orchestrator that spawns/manages workers via `Agent`, `SendMessage`, `TaskStop` tools
2. **Worker Communication**: Workers report results as `<task-notification>` XML in user-role messages
3. **Task Workflow**: Research (parallel) -> Synthesis (coordinator) -> Implementation (workers) -> Verification (workers)
4. **Concurrency Rules**: Read-only tasks run in parallel freely; write-heavy tasks serialized per file set
5. **Prompt Discipline**: Workers have no conversation context -- coordinator must write self-contained prompts with file paths, line numbers, and explicit "done" criteria

**Internal Worker Tools** (hidden from coordinator's tool list):
- `TeamCreate`, `TeamDelete`, `SendMessage`, `SyntheticOutput` -- internal plumbing tools

**Worker Tool Set** (two modes):
- **Simple mode** (`CLAUDE_CODE_SIMPLE`): Bash, FileRead, FileEdit only
- **Full mode**: All `ASYNC_AGENT_ALLOWED_TOOLS` minus internal worker tools, plus MCP tools and Skills

### Key Design Insights

- The scratchpad feature (`tengu_scratch` gate) enables a shared filesystem directory where workers can read/write without permission prompts -- this is the cross-worker knowledge persistence mechanism.
- `matchSessionMode()` handles the edge case where a user resumes a coordinator-mode session from a normal-mode CLI (or vice versa) by dynamically flipping the env var.
- The coordinator system prompt is the most detailed prompt in the codebase (~250 lines), with explicit anti-patterns ("Never write 'based on your findings'") and decision tables for when to continue vs. spawn fresh workers.

---

## 2. Session History (`assistant/sessionHistory.ts`, 88 LOC)

### Purpose

Paginated fetcher for **remote session event history** from the Anthropic cloud API. Enables resuming sessions that were started on a different machine or in a different Claude Code instance by downloading the conversation transcript.

### Key Functions

| Function | Signature | Role |
|----------|-----------|------|
| `createHistoryAuthCtx(sessionId)` | `(string) => Promise<HistoryAuthCtx>` | Prepares auth context (base URL + OAuth headers + org UUID + beta header) for paginated fetching |
| `fetchLatestEvents(ctx, limit?)` | `(HistoryAuthCtx, number?) => Promise<HistoryPage \| null>` | Fetches the newest page of events using `anchor_to_latest` parameter |
| `fetchOlderEvents(ctx, beforeId, limit?)` | `(HistoryAuthCtx, string, number?) => Promise<HistoryPage \| null>` | Fetches older events before a cursor ID for backward pagination |
| `fetchPage(ctx, params, label)` | (private) | Core HTTP GET with 15s timeout, null-safe error handling |

### Key Types

```typescript
type HistoryPage = {
  events: SDKMessage[]      // Chronological order within page
  firstId: string | null    // Cursor for next-older page
  hasMore: boolean          // More older events exist?
}
```

### Architecture Role

This module is the **remote session rehydration layer**. It enables the "continue session from cloud" feature:

1. Client calls `createHistoryAuthCtx(sessionId)` to set up authenticated access
2. Calls `fetchLatestEvents()` to get the most recent page (default 100 events)
3. If `hasMore` is true, paginates backward with `fetchOlderEvents(ctx, page.firstId)`
4. The `SDKMessage[]` events are replayed to reconstruct the local session state

**API Endpoint**: `${BASE_API_URL}/v1/sessions/{sessionId}/events`
**Beta Header**: `anthropic-beta: ccr-byoc-2025-07-29` (Cloud Code Runner, Bring Your Own Compute)

### Key Design Insights

- The `HISTORY_PAGE_SIZE = 100` constant is exported for use by callers to control pagination.
- Error handling is graceful -- returns `null` on any HTTP error or network failure rather than throwing.
- The `ccr-byoc` beta header reveals this is part of the "Bring Your Own Compute" feature where sessions run on user infrastructure but sync state to Anthropic's cloud.

---

## 3. Direct Connect Server (`server/`, 3 files, 271 LOC total)

### 3a. Types (`server/types.ts`, 57 LOC)

Type definitions and Zod schema for the **Direct Connect server** protocol -- the HTTP/WebSocket server mode where Claude Code runs as a headless service.

| Type | Purpose |
|------|---------|
| `connectResponseSchema` | Zod schema validating server's session creation response: `{ session_id, ws_url, work_dir? }` |
| `ServerConfig` | Server configuration: port, host, authToken, unix socket path, idle timeout, max sessions, default workspace |
| `SessionState` | Lifecycle enum: `'starting' \| 'running' \| 'detached' \| 'stopping' \| 'stopped'` |
| `SessionInfo` | Runtime session metadata: id, status, createdAt, workDir, ChildProcess reference, sessionKey |
| `SessionIndexEntry` | Persistent session metadata (saved to `~/.claude/server-sessions.json`): sessionId, transcriptSessionId, cwd, permissionMode, timestamps |
| `SessionIndex` | `Record<string, SessionIndexEntry>` -- key is stable session key |

Uses `lazySchema()` wrapper for the Zod schema -- **lazy initialization** to avoid import-time parsing cost. Sessions persist across server restarts via `~/.claude/server-sessions.json`, supporting the `--resume` flow with `transcriptSessionId`.

### 3b. Session Creation (`server/createDirectConnectSession.ts`, 89 LOC)

Client-side function to **create a new session** on a Direct Connect server by POSTing to `/sessions`.

| Function | Signature | Role |
|----------|-----------|------|
| `createDirectConnectSession({serverUrl, authToken?, cwd, dangerouslySkipPermissions?})` | `=> Promise<{config: DirectConnectConfig, workDir?: string}>` | POST to `${serverUrl}/sessions`, validate response with Zod, return config |

- `DirectConnectError` -- custom error class for connection/HTTP/parsing failures.
- Uses native `fetch` (not axios). Validates response with `connectResponseSchema().safeParse()`.
- The `dangerouslySkipPermissions` flag maps to the `--dangerously-skip-permissions` CLI flag.

### 3c. Session Manager (`server/directConnectManager.ts`, 214 LOC)

WebSocket-based **session manager** for Direct Connect mode. Handles bidirectional real-time communication between a Claude Code client and a remote Claude Code server process.

#### Key Class: `DirectConnectSessionManager`

| Method | Purpose |
|--------|---------|
| `constructor(config, callbacks)` | Initialize with server config and event callbacks |
| `connect()` | Open WebSocket to `config.wsUrl` with auth headers, set up message routing |
| `sendMessage(content)` | Send user message in `SDKUserMessage` format via WebSocket |
| `respondToPermissionRequest(requestId, result)` | Reply to server's tool-use permission request (allow/deny) |
| `sendInterrupt()` | Send interrupt signal to cancel current request |
| `disconnect()` | Close WebSocket cleanly |
| `isConnected()` | Check WebSocket readyState |

#### Callback Interface

```typescript
type DirectConnectCallbacks = {
  onMessage: (message: SDKMessage) => void          // SDK messages (assistant, result, system)
  onPermissionRequest: (request, requestId) => void  // Tool permission prompts
  onConnected?: () => void
  onDisconnected?: () => void
  onError?: (error: Error) => void
}
```

#### Message Routing Logic

The WebSocket receives newline-delimited JSON messages. The manager routes them by type:

| Message Type | Action |
|-------------|--------|
| `control_request` (subtype: `can_use_tool`) | Forward to `onPermissionRequest` callback |
| `control_request` (other subtypes) | Send error response back (prevent server hang) |
| `control_response`, `keep_alive`, `control_cancel_request` | **Filtered out** (not forwarded to client) |
| `streamlined_text`, `streamlined_tool_use_summary` | **Filtered out** |
| `system` (subtype: `post_turn_summary`) | **Filtered out** |
| Everything else (`assistant`, `result`, etc.) | Forward to `onMessage` callback |

The permission system works remotely: server asks "can I use tool X?", client UI shows the prompt, user approves/denies, client sends response back. This maintains the human-in-the-loop safety model even in remote/headless mode.

---

## Cross-Module Architecture

```
                     +------------------+
                     |   CLI / REPL     |
                     +--------+---------+
                              |
              +---------------+---------------+
              |                               |
    +---------v----------+          +---------v-----------+
    | coordinator/       |          | server/             |
    | coordinatorMode.ts |          | types.ts            |
    | (multi-agent       |          | createDC Session.ts |
    | orchestration)     |          | directConnect Mgr   |
    +--------------------+          +---------------------+
                                             |
                                    WebSocket (bidirectional)
                                             |
                                    +--------v---------+
                                    | Remote Claude    |
                                    | Code Process     |
                                    +------------------+

    +-----------------------+
    | assistant/            |
    | sessionHistory.ts     |
    | (cloud session        |
    |  rehydration via API) |
    +-----------------------+
```

### Module Interaction Map

| Module | Depends On | Depended On By |
|--------|-----------|---------------|
| `coordinator/coordinatorMode.ts` | `bun:bundle` features, Statsig gates, tool constants, analytics | QueryEngine (system prompt injection), session resume logic |
| `assistant/sessionHistory.ts` | OAuth config, axios, SDK message types | Session resume UI, cloud session continuation |
| `server/types.ts` | Zod, lazySchema utility | createDirectConnectSession, directConnectManager, server startup |
| `server/createDirectConnectSession.ts` | server/types, utils/errors, utils/slowOperations | CLI `--connect` flag handler, REPL Direct Connect init |
| `server/directConnectManager.ts` | SDK types, control types, RemoteSessionManager types, utils | REPL WebSocket session, headless runner |

### Loading Patterns

| Module | Loading | Activation |
|--------|---------|------------|
| coordinatorMode | Eager import, conditional execution | `feature('COORDINATOR_MODE')` + env var |
| sessionHistory | Eager import, always available | Called when cloud session resume is requested |
| server/types | Lazy Zod schema, eager types | Always available as types |
| createDirectConnectSession | Eager import | Called during `--connect` startup |
| directConnectManager | Eager import | Instantiated when WebSocket session begins |

---

## Key Findings

1. **Coordinator Mode is the multi-agent brain**: The 250-line system prompt is the most detailed in the codebase, encoding the full orchestration philosophy (parallel research, synthesized specs, verification discipline).

2. **Three distinct remote/distributed patterns**:
   - **Coordinator Mode**: Local orchestrator, local workers (multi-process on same machine)
   - **Direct Connect**: Client connects to remote server via WebSocket (remote execution)
   - **Session History**: Cloud API for cross-device session continuity (state sync)

3. **Permission system extends to remote**: Direct Connect preserves human-in-the-loop by forwarding permission requests over WebSocket -- the safety model is maintained even in headless/remote modes.

4. **Scratchpad is the cross-worker shared state**: Gated behind `tengu_scratch`, it provides a filesystem-based communication channel between coordinator workers, bypassing the permission system for efficiency.

5. **Session persistence across restarts**: `SessionIndex` saved to `~/.claude/server-sessions.json` enables resuming Direct Connect sessions even after server process restarts, using `transcriptSessionId` for transcript continuity.
