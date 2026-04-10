# Team System

> Consolidated from deep analysis. Authoritative reference for team creation/deletion, file-based mailbox communication, teammate backends, swarm coordination, and backend execution infrastructure.
> Source: `src/tools/TeamCreateTool/`, `src/tools/TeamDeleteTool/`, `src/tools/SendMessageTool/`, `src/utils/swarm/` (22 files), `src/utils/swarm/backends/` (9 files), `src/hooks/useSwarm*.ts`

## Architecture Overview

The team system enables multi-agent collaboration through file-based mailbox communication. Teams consist of a lead agent and teammates that coordinate via structured messages. The swarm backend system provides a pluggable execution infrastructure for spawning and managing teammate agents, abstracting three fundamentally different execution models behind two complementary interfaces.

```
                         +----------------------+
                         |  getTeammateExecutor()|   (registry.ts)
                         +----------+-----------+
                  +-----------------+-----------------+
                  v                 v                  v
         +---------------+ +---------------+  +------------------+
         | InProcessBack | | PaneBackend   |  | PaneBackend      |
         | end           | | Executor(Tmux)|  | Executor(iTerm2) |
         +---------------+ +-------+-------+  +--------+---------+
           TeammateExecutor        |                    |
                                   v                    v
                           +-------------+      +-------------+
                           | TmuxBackend |      | ITermBackend|
                           +-------------+      +-------------+
                             PaneBackend          PaneBackend
```

### Dual Interface Design

| Interface | Level | Purpose |
|-----------|-------|---------|
| `PaneBackend` | Low-level | Terminal pane CRUD: create, send-command, kill, hide/show, rebalance |
| `TeammateExecutor` | High-level | Agent lifecycle: spawn, sendMessage, terminate, kill, isActive |

`PaneBackendExecutor` is an **adapter** that wraps any `PaneBackend` into the `TeammateExecutor` interface, giving callers a uniform API regardless of backend type.

---

## TeamCreateTool (`src/tools/TeamCreateTool/TeamCreateTool.ts`)

### Input Schema

```typescript
const inputSchema = z.strictObject({
  team_name: z.string(),
  description: z.string().optional(),
  agent_type: z.string().optional(),  // Lead's type/role
})
```

### Creation Process

1. **Sanitize name**: `sanitizeName()` for filesystem safety
2. **Create team file**: JSON at `getTeamFilePath(team_name)`
3. **Register lead**: Unique agent ID via `formatAgentId()`
4. **Assign color**: `assignTeammateColor()` for UI distinction
5. **Init tasks dir**: `ensureTasksDir()` for output files
6. **Track cleanup**: `registerTeamForSessionCleanup()`
7. **Set leader**: `setLeaderTeamName()` for context

### Output

```typescript
type Output = {
  team_name: string
  team_file_path: string
  lead_agent_id: string
}
```

## TeamDeleteTool (`src/tools/TeamDeleteTool/`)

Tears down a team by killing all active teammates, cleaning up mailbox files, removing the team file, and unregistering from the session.

## SendMessageTool (`src/tools/SendMessageTool/SendMessageTool.ts`)

### Structured Message Types

```typescript
const StructuredMessage = z.discriminatedUnion('type', [
  z.object({ type: z.literal('shutdown_request'), reason: z.string().optional() }),
  z.object({ type: z.literal('shutdown_response'), request_id, approve, reason }),
  z.object({ type: z.literal('plan_approval_response'), request_id, ... }),
  // ... additional structured types
])
```

### Routing Logic

Messages are resolved by the `to` field:

| Target | Resolution Method |
|--------|-------------------|
| Agent name | Look up in team file |
| Agent ID | Direct ID addressing |
| `TEAM_LEAD_NAME` ("lead") | Route to team lead |
| Peer address | Cross-process via UDS inbox |
| Main session | Via `isMainSessionTask()` |

### Delivery Mechanisms

| Mechanism | When Used |
|-----------|-----------|
| `queuePendingMessage()` | In-process teammate or local agent task |
| `writeToMailbox()` | File-based mailbox for teammate communication |
| REPL bridge | Route through bridge for remote sessions |
| `resumeAgentBackground()` | Wake paused background agents |

---

## File-Based Mailbox (`src/utils/teammateMailbox.ts`)

### Core Operations

```typescript
writeToMailbox(message)                    // Append message to mailbox file
createShutdownRequestMessage()             // Structured shutdown request
createShutdownApprovedMessage()            // Shutdown approval response
createShutdownRejectedMessage()            // Shutdown rejection response
```

### File Format

Each agent has a mailbox file in the team directory:
- Append-only message log (crash-safe)
- JSON-per-line format
- Read by polling (not filesystem watchers)

All backends use the same `writeToMailbox()` mechanism for inter-agent messaging. Messages are appended as JSON-per-line to agent-specific mailbox files in the team directory. Polling-based reads (no filesystem watchers).

---

## Backend Types

### BackendType Enum

```typescript
type BackendType = 'tmux' | 'iterm2' | 'in-process'
type PaneBackendType = 'tmux' | 'iterm2'   // subset for pane-only operations
```

### TmuxBackend (`backends/TmuxBackend.ts`, 764 lines)

**Execution model**: Each teammate runs as a separate OS process in a tmux pane.

**Two operational modes**:

| Mode | Condition | Layout | Socket |
|------|-----------|--------|--------|
| **Inside tmux** | User launched Claude from within tmux | Leader left 30%, teammates right 70% (main-vertical) | User's default tmux socket |
| **Outside tmux** | User in regular terminal, tmux installed | All teammates equal (tiled layout, no leader pane) | Isolated socket `claude-swarm-{pid}` |

**Key mechanisms**:
- **Pane creation lock**: Mutex via Promise chain prevents race conditions during parallel teammate spawns
- **Shell init delay**: 200ms wait (`PANE_SHELL_INIT_DELAY_MS`) after pane creation for shell rc files to load
- **Leader pane ID capture**: `TMUX_PANE` env var captured at module load time (before Shell.ts overrides it)
- **Window target caching**: `cachedLeaderWindowTarget` avoids repeated tmux queries
- **Layout strategy**: First teammate splits horizontally from leader; subsequent teammates alternate vertical/horizontal splits from existing teammate panes; after each split, `rebalancePanesWithLeader()` enforces main-vertical with leader at 30%
- **Hide/Show**: Uses `break-pane` to move pane to detached `claude-hidden` session; `join-pane` to restore

**External session isolation**: When running outside tmux, uses a PID-scoped socket name (`claude-swarm-{pid}`) so multiple Claude instances don't conflict.

**Self-registration**: `registerTmuxBackend(TmuxBackend)` called at module load as side effect.

### ITermBackend (`backends/ITermBackend.ts`, 371 lines)

**Execution model**: Each teammate runs as a separate OS process in an iTerm2 native split pane, controlled via the `it2` Python CLI.

**Layout strategy**:
- First teammate: vertical split (`-v`) from leader's session (extracted from `ITERM_SESSION_ID` env var)
- Subsequent teammates: horizontal split from last teammate's session ID
- No manual rebalancing needed (iTerm2 handles automatically)

**Dead session recovery**: If a targeted teammate session is dead (user closed pane), the backend prunes the stale ID and retries with the next-to-last session. Bounded at O(N+1) iterations.

**Performance trade-offs**:
- `setPaneBorderColor()`, `setPaneTitle()`, `enablePaneBorderStatus()`, `rebalancePanes()` are all **no-ops** because each `it2` call spawns a Python process (slow)
- Kill uses `-f` (force) flag to bypass iTerm2's "confirm before closing" preference

**Limitations**:
- `supportsHideShow = false` (no equivalent to tmux break-pane/join-pane)
- macOS only (iTerm2 is macOS-exclusive)

**Self-registration**: `registerITermBackend(ITermBackend)` at module load.

### InProcessBackend (`backends/InProcessBackend.ts`, 340 lines)

**Execution model**: Teammate runs in the **same Node.js process** with isolated context via `AsyncLocalStorage`.

**Key differences from pane backends**:

| Aspect | Pane Backends | InProcessBackend |
|--------|---------------|------------------|
| Process isolation | Separate OS process | Same process, AsyncLocalStorage isolation |
| Resource sharing | None (independent) | Shares API client, MCP connections |
| Communication | File-based mailbox | File-based mailbox (same mechanism) |
| Termination | kill-pane | AbortController.abort() |
| Lifecycle tracking | Pane existence | AppState.tasks with InProcessTeammateTaskState |
| Permission prompts | Own terminal UI | Leader's ToolUseConfirm dialog with worker badge |

**Spawn flow**:
1. Requires `setContext(toolUseContext)` before spawning
2. Calls `spawnInProcessTeammate()` to create TeammateContext and register in AppState
3. Fires `startInProcessTeammate()` (fire-and-forget) to begin agent execution loop
4. Strips parent conversation messages from context to prevent memory pinning

**Terminate flow** (graceful):
1. Creates deterministic `shutdown-{agentId}-{timestamp}` request ID
2. Sends structured `shutdown_request` message to teammate's mailbox
3. Sets `shutdownRequested` flag on task state
4. Teammate processes request and either approves (exits) or rejects (continues)

**Kill flow** (force):
1. Calls `killInProcessTeammate()` which aborts the AbortController
2. Updates task state to 'killed'
3. Removes from teamContext.teammates and team file
4. Evicts task output from disk
5. Unregisters from Perfetto tracing

**isActive check**: Verifies task exists, `status === 'running'`, and AbortController not aborted.

### PaneBackendExecutor (`backends/PaneBackendExecutor.ts`, 355 lines)

**Adapter pattern**: Wraps any `PaneBackend` into the `TeammateExecutor` interface.

**spawn() flow**:
1. Assigns color via `assignTeammateColor()`
2. Creates pane via `backend.createTeammatePaneInSwarmView()`
3. Builds Claude CLI command with teammate identity flags (`--agent-id`, `--agent-name`, `--team-name`, `--agent-color`, `--parent-session-id`)
4. Sends command to pane via `backend.sendCommandToPane()`
5. Tracks `agentId -> {paneId, insideTmux}` mapping
6. Registers cleanup handler to kill all panes on leader exit (SIGHUP)
7. Sends initial prompt to teammate's mailbox

**kill()**: Looks up paneId from spawned map, calls `backend.killPane()`.

**terminate()**: Sends `shutdown_request` JSON message to teammate's mailbox.

**isActive()**: Returns true if teammate exists in spawned map (best-effort, no pane existence check).

---

## TeammateExecutor Interface

```typescript
type TeammateExecutor = {
  readonly type: BackendType
  isAvailable(): Promise<boolean>
  spawn(config: TeammateSpawnConfig): Promise<TeammateSpawnResult>
  sendMessage(agentId: string, message: TeammateMessage): Promise<void>
  terminate(agentId: string, reason?: string): Promise<boolean>
  kill(agentId: string): Promise<boolean>
  isActive(agentId: string): Promise<boolean>
}
```

### TeammateSpawnConfig

```typescript
type TeammateSpawnConfig = TeammateIdentity & {
  prompt: string
  cwd: string
  model?: string
  systemPrompt?: string
  systemPromptMode?: 'default' | 'replace' | 'append'
  worktreePath?: string
  parentSessionId: string
  permissions?: string[]
  allowPermissionPrompts?: boolean
}
```

### TeammateSpawnResult

```typescript
type TeammateSpawnResult = {
  success: boolean
  agentId: string           // format: "agentName@teamName"
  error?: string
  abortController?: AbortController   // in-process only
  taskId?: string                      // in-process only
  paneId?: PaneId                      // pane-based only
}
```

---

## Backend Detection and Registry (`backends/registry.ts`, 465 lines)

### Detection Priority

```
1. Inside tmux?           -> TmuxBackend (native)
2. In iTerm2?
   a. User prefers tmux?  -> Skip iTerm2
   b. it2 CLI available?  -> ITermBackend (native)
   c. tmux available?     -> TmuxBackend (fallback, suggest it2 setup)
   d. Neither?            -> Error: install it2
3. tmux available?        -> TmuxBackend (external session)
4. Nothing available?     -> Error with platform-specific install instructions
```

### Mode Resolution (`isInProcessEnabled()`)

```
teammateMode = 'in-process'  -> always in-process
teammateMode = 'tmux'        -> always pane-based
teammateMode = 'auto'        -> environment-dependent:
  - Non-interactive (-p mode) -> in-process
  - Previous fallback active  -> in-process
  - Inside tmux or iTerm2     -> pane-based
  - Otherwise                 -> in-process
```

### Caching Strategy

All detection results are cached for process lifetime:
- `cachedBackend`: PaneBackend instance
- `cachedDetectionResult`: Full detection result with metadata
- `cachedInProcessBackend`: Singleton InProcessBackend
- `cachedPaneBackendExecutor`: Singleton PaneBackendExecutor
- `inProcessFallbackActive`: Sticky flag once in-process fallback triggers

### Self-Registration Pattern

Backends register themselves via side effects on import to avoid circular dependencies:
```
TmuxBackend.ts -> registerTmuxBackend(TmuxBackend)
ITermBackend.ts -> registerITermBackend(ITermBackend)
```
`ensureBackendsRegistered()` dynamically imports both modules.

---

## Environment Detection (`backends/detection.ts`, 129 lines)

| Check | Method | Notes |
|-------|--------|-------|
| Inside tmux | `TMUX` env var at module load | Captured before Shell.ts overrides it |
| Leader pane ID | `TMUX_PANE` env var at module load | Immutable reference to leader's original pane |
| tmux available | `tmux -V` | Checks PATH |
| In iTerm2 | `TERM_PROGRAM`, `ITERM_SESSION_ID`, `env.terminal` | Multiple indicators checked |
| it2 CLI available | `it2 session list` | Tests Python API connection, not just `--version` |

## Teammate Mode Snapshot (`backends/teammateModeSnapshot.ts`)

Captures teammate execution mode at session startup, following the same immutable-snapshot pattern as `hooksConfigSnapshot.ts`. This ensures runtime config changes don't affect the mode mid-session.

```
CLI override (--teammate-mode) > config (settings.json) > default ('auto')
```

The snapshot can be cleared when the user changes the setting in the UI, allowing their change to take effect for future spawns.

---

## Communication Channels

### Permission Synchronization (`permissionSync.ts`, 929 lines)

Dual-system permission flow:

1. **File-based**: `pending/` and `resolved/` directories with JSON files + lockfile for atomicity
2. **Mailbox-based**: Permission requests/responses sent as structured messages through the mailbox

The leader polls for permission requests and presents them via the standard `ToolUseConfirm` UI dialog. Workers poll for responses.

### Leader Permission Bridge (`leaderPermissionBridge.ts`)

Module-level bridge for in-process teammates to access the REPL's `setToolUseConfirmQueue` and `setToolPermissionContext` functions. This allows in-process teammates to present permission prompts through the leader's UI with a colored "worker badge" rather than creating their own permission UI.

---

## Spawn Utilities (`spawnUtils.ts`)

### CLI Flag Inheritance

Teammates inherit these settings from the parent:
- Permission mode (`--dangerously-skip-permissions`, `--permission-mode acceptEdits`)
- Model override (`--model`)
- Settings path (`--settings`)
- Inline plugins (`--plugin-dir`)
- Teammate mode (`--teammate-mode`)
- Chrome flag (`--chrome` / `--no-chrome`)

Plan mode takes precedence: if `planModeRequired`, bypass permissions are NOT inherited.

### Environment Variable Forwarding

Critical env vars forwarded to tmux-spawned teammates (tmux may start a new login shell):
- API provider selection: `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX`, `CLAUDE_CODE_USE_FOUNDRY`
- Custom endpoint: `ANTHROPIC_BASE_URL`
- Config directory: `CLAUDE_CONFIG_DIR`
- CCR markers: `CLAUDE_CODE_REMOTE`, `CLAUDE_CODE_REMOTE_MEMORY_DIR`
- Proxy settings: `HTTPS_PROXY`, `HTTP_PROXY`, `NO_PROXY` and variants
- TLS certificates: `SSL_CERT_FILE`, `NODE_EXTRA_CA_CERTS`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE`

Always includes: `CLAUDECODE=1`, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`

---

## In-Process Teammate Lifecycle

### Spawn (`spawnInProcess.ts`, 329 lines)

1. Generate deterministic `agentId = formatAgentId(name, teamName)` (format: `name@team`)
2. Create independent `AbortController` (not linked to parent's query interruption)
3. Create `TeammateContext` for AsyncLocalStorage isolation
4. Register agent in Perfetto trace for hierarchy visualization
5. Create `InProcessTeammateTaskState` with status 'running'
6. Register cleanup handler (aborts on SIGHUP/exit)
7. Register task in AppState via `registerTask()`

### Execution (`inProcessRunner.ts`, 1552 lines)

The largest file in the swarm system. Key responsibilities:
- Wraps `runAgent()` with `runWithTeammateContext()` for identity isolation
- Creates `canUseTool` function that routes 'ask' decisions through leader's UI (via bridge) or mailbox (fallback)
- Manages plan mode approval flow
- Handles auto-compaction when context grows
- Sends idle notifications to leader on completion
- Tracks progress for AppState UI updates

### Kill (`spawnInProcess.ts`)

1. Abort the AbortController
2. Call cleanup handler
3. Fire pending idle callbacks (unblock waiters)
4. Remove from `teamContext.teammates`
5. Set status to 'killed'
6. Remove from team file
7. Evict task output from disk
8. Emit SDK task terminated event
9. Schedule UI eviction after `STOPPED_DISPLAY_MS`
10. Unregister from Perfetto tracing

---

## Reconnection (`reconnection.ts`, 120 lines)

Handles teammate context initialization for both fresh spawns and resumed sessions:

- **Fresh spawn**: `computeInitialTeamContext()` reads team file, sets up `teamContext` in initial AppState before first render
- **Resumed session**: `initializeTeammateContextFromSession()` reconstructs teamContext from stored `teamName`/`agentName` in transcript

Both paths read the team file to get `leadAgentId` and set `isLeader` based on whether the agent has an `agentId` assigned.

---

## Teammate Utilities

### teammateInit.ts

Registers a **Stop hook** for teammates that:
1. Marks the teammate as idle in the team config file
2. Sends an idle notification to the leader's mailbox with a summary of the last peer DM
3. Applies team-wide allowed paths as session-scoped permission rules

### teammateLayoutManager.ts

- **Color assignment**: Round-robin from `AGENT_COLORS` palette, cached per session
- **Facade functions**: `createTeammatePaneInSwarmView()`, `enablePaneBorderStatus()`, `sendCommandToPane()` delegate to detected backend

### teammateModel.ts

Fallback model for teammates when user hasn't set `teammateDefaultModel`: currently `CLAUDE_OPUS_4_6_CONFIG` with provider-aware model ID selection.

### teammatePromptAddendum.ts

System prompt addition explaining to teammates that they must use `SendMessage` tool for communication (plain text responses are not visible to team members).

### Teammate Detection (`src/utils/teammate.ts`)

```typescript
isTeammate()               // Is current execution a teammate?
isTeamLead()               // Is current execution the lead?
getTeamName()              // Current team name
getAgentId()               // This agent's unique ID
getAgentName()             // Display name
getTeammateColor()         // Assigned UI color
getParentSessionId()       // Parent's session ID
```

### In-Process Teammates (`src/utils/teammateContext.ts`)

```typescript
isInProcessTeammate()      // Runs in same process as parent
```

---

## Team Helpers (`src/utils/swarm/teamHelpers.ts`)

```typescript
getTeamFilePath()                     // Team file location
readTeamFile() / readTeamFileAsync()  // Read team state
writeTeamFileAsync()                  // Update team state
sanitizeName()                        // Filesystem-safe name transform
registerTeamForSessionCleanup()       // Auto-cleanup on exit
```

---

## React Integration

### useSwarmInitialization (`src/hooks/useSwarmInitialization.ts`)

Setup hook: detects team context, initializes mailbox watching, registers with team.

### useSwarmPermissionPoller (`src/hooks/useSwarmPermissionPoller.ts`)

Polls for permission requests from teammates -- team lead manages centralized permission decisions.

### useMailboxBridge (`src/hooks/useMailboxBridge.ts`)

Bridges mailbox to UI: polls for new messages, renders incoming, handles acknowledgment.

### useInboxPoller (`src/hooks/useInboxPoller.ts`)

Polls UDS inbox for cross-process peer messages.

---

## Constants (`src/utils/swarm/constants.ts`)

| Constant | Value | Purpose |
|----------|-------|---------|
| `TEAM_LEAD_NAME` | `'team-lead'` | Reserved name for leader |
| `SWARM_SESSION_NAME` | `'claude-swarm'` | External tmux session name |
| `SWARM_VIEW_WINDOW_NAME` | `'swarm-view'` | Window within swarm session |
| `TMUX_COMMAND` | `'tmux'` | tmux binary name |
| `HIDDEN_SESSION_NAME` | `'claude-hidden'` | Detached session for hidden panes |
| `getSwarmSocketName()` | `claude-swarm-{pid}` | PID-scoped socket for isolation |

## Feature Gate

```typescript
isAgentSwarmsEnabled()  // src/utils/agentSwarmsEnabled.ts
```

When disabled: TeamCreate/TeamDelete tools not registered; SendMessage still available for other messaging.

---

## Key Design Decisions

### Why Two Interfaces?

`PaneBackend` handles low-level pane operations (split, send-keys, kill-pane) that are terminal-specific. `TeammateExecutor` handles high-level agent lifecycle that is backend-agnostic. The adapter pattern (`PaneBackendExecutor`) bridges them, allowing callers to use a single `getTeammateExecutor()` entry point.

### Why File-Based Mailboxes Even for In-Process?

All backends use the same file-based mailbox for simplicity and consistency. In-process teammates could theoretically use direct function calls, but using the same mailbox mechanism means the messaging infrastructure is backend-agnostic and tested uniformly.

### Why Independent AbortControllers for In-Process?

In-process teammates get their own `AbortController` not linked to the parent. This prevents a leader's query interruption (Ctrl+C) from killing teammates. Teammates are only aborted via explicit `kill()` or process shutdown cleanup.

### Why Capture Env Vars at Module Load?

`TMUX` and `TMUX_PANE` are captured at import time because `Shell.ts` later overrides `process.env.TMUX` with Claude's own tmux socket. The original values are needed to correctly detect whether the user started Claude from within tmux.

---

## File Inventory

### backends/ (9 files)

| File | Lines | Purpose |
|------|-------|---------|
| `types.ts` | 312 | PaneBackend, TeammateExecutor interfaces, type guards |
| `registry.ts` | 465 | Backend detection, caching, executor factory |
| `detection.ts` | 129 | Environment detection (tmux, iTerm2, it2) |
| `TmuxBackend.ts` | 764 | tmux pane management (inside + external modes) |
| `ITermBackend.ts` | 371 | iTerm2 native split pane management via it2 CLI |
| `InProcessBackend.ts` | 340 | Same-process execution with AsyncLocalStorage |
| `PaneBackendExecutor.ts` | 355 | Adapter: PaneBackend -> TeammateExecutor |
| `teammateModeSnapshot.ts` | 88 | Immutable session mode snapshot |
| `it2Setup.ts` | 246 | it2 CLI detection, installation, verification |

### swarm/ root (13 files)

| File | Lines | Purpose |
|------|-------|---------|
| `inProcessRunner.ts` | 1552 | Agent execution loop for in-process teammates |
| `permissionSync.ts` | 929 | Cross-agent permission request/response coordination |
| `spawnInProcess.ts` | 329 | In-process teammate task creation and registration |
| `teamHelpers.ts` | ~500 | Team file CRUD, member management |
| `spawnUtils.ts` | 147 | CLI flag and env var inheritance for spawned teammates |
| `teammateInit.ts` | 130 | Teammate hook registration (idle notification, permissions) |
| `teammateLayoutManager.ts` | 108 | Color assignment and backend facade |
| `reconnection.ts` | 120 | Session resume/reconnection for teammates |
| `leaderPermissionBridge.ts` | 55 | Module bridge for in-process permission UI |
| `constants.ts` | 34 | Session/socket naming constants |
| `teammateModel.ts` | 10 | Default teammate model (Opus 4.6) |
| `teammatePromptAddendum.ts` | 18 | System prompt addendum for teammate communication |
| `It2SetupPrompt.tsx` | ~800 | React UI for it2 installation wizard |

**Total**: ~5,767 lines across 22 files (backends/ + swarm/ root).

## Key Source Files

| File | Purpose |
|------|---------|
| `src/tools/TeamCreateTool/` | Team creation |
| `src/tools/TeamDeleteTool/` | Team deletion |
| `src/tools/SendMessageTool/` | Message routing |
| `src/utils/teammateMailbox.ts` | File-based mailbox |
| `src/utils/teammate.ts` | Teammate detection |
| `src/utils/swarm/teamHelpers.ts` | Team file operations |
| `src/utils/swarm/backends/` | Execution backends |
| `src/utils/swarm/constants.ts` | Constants |
| `src/hooks/useSwarmInitialization.ts` | Swarm setup |
| `src/hooks/useMailboxBridge.ts` | Mailbox UI |
| `src/context/mailbox.ts` | Mailbox React context |
