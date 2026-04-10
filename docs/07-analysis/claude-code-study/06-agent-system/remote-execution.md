# Remote Execution

> Analysis of Claude Code's remote session management, triggers, cron scheduling, and background execution.

## Overview

Remote execution enables Claude Code to run agent sessions on Anthropic's cloud infrastructure (CCR — Claude Code Remote), manage scheduled triggers, and schedule recurring cron jobs. This system provides persistent, server-side agent execution that survives local session termination.

**Key source files:**
- `src/remote/RemoteSessionManager.ts` — Remote session WebSocket management
- `src/remote/SessionsWebSocket.ts` — WebSocket subscription client
- `src/remote/remotePermissionBridge.ts` — Permission proxying for remote sessions
- `src/remote/sdkMessageAdapter.ts` — SDK message adaptation
- `src/tools/RemoteTriggerTool/RemoteTriggerTool.ts` — Trigger CRUD API
- `src/tools/RemoteTriggerTool/prompt.ts` — Trigger API documentation
- `src/tools/ScheduleCronTool/` — Cron scheduling tools (Create, Delete, List)
- `src/commands/remote-setup/` — Remote environment setup command
- `src/utils/background/remote/` — Remote session preconditions and management

---

## Remote Session Manager

### Architecture

`src/remote/RemoteSessionManager.ts` manages the client-side connection to a CCR session:

```
Local Claude Code  ←— WebSocket —→  CCR (Cloud)
     │                                    │
     ├─ Receives SDKMessages              ├─ Runs agent loop
     ├─ Handles permission requests       ├─ Executes tools
     ├─ Sends user messages (HTTP POST)   ├─ Streams responses
     └─ Manages reconnection              └─ Sends permission requests
```

### Configuration

```typescript
type RemoteSessionConfig = {
  sessionId: string
  getAccessToken: () => string
  orgUuid: string
  hasInitialPrompt?: boolean  // Session created with a prompt being processed
  viewerOnly?: boolean        // Pure viewer mode (no interrupt, no title updates)
}
```

**Viewer-only mode** is used by `claude assistant` — Ctrl+C/Escape do NOT send interrupt to the remote agent, 60-second reconnect timeout is disabled, and session title is never updated.

### Communication Flow

**Inbound (CCR → Local):**
1. WebSocket receives messages via `SessionsWebSocket`
2. Messages are typed as `SDKMessage | SDKControlRequest | SDKControlResponse | SDKControlCancelRequest`
3. `isSDKMessage()` type guard separates data messages from control messages
4. SDK messages delivered via `onMessage` callback
5. Permission requests delivered via `onPermissionRequest` callback with `requestId`
6. Permission cancellations via `onPermissionCancelled`

**Outbound (Local → CCR):**
- User messages sent via HTTP POST through `sendEventToRemoteSession()` from `src/utils/teleport/api.ts`
- Permission responses sent as `SDKControlResponse` messages

### Callbacks

```typescript
type RemoteSessionCallbacks = {
  onMessage: (message: SDKMessage) => void
  onPermissionRequest: (request: SDKControlPermissionRequest, requestId: string) => void
  onPermissionCancelled?: (requestId: string, toolUseId?: string) => void
  onConnected?: () => void
  onDisconnected?: () => void    // Connection lost permanently
  onReconnecting?: () => void    // Transient drop, backoff in progress
  onError?: (error: Error) => void
}
```

### Permission Bridge

`src/remote/remotePermissionBridge.ts` proxies permission decisions between the local terminal and the remote agent. When the remote agent needs to execute a sensitive tool, the request flows:

```
CCR agent → WebSocket → Local UI → User decision → HTTP response → CCR agent continues
```

Permission responses are typed as:
```typescript
type RemotePermissionResponse =
  | { behavior: 'allow', updatedInput: Record<string, unknown> }
  | { behavior: 'deny', message: string }
```

---

## Remote Triggers (RemoteTriggerTool)

### Purpose

`src/tools/RemoteTriggerTool/RemoteTriggerTool.ts` provides CRUD access to the CCR triggers API — scheduled remote agent sessions that run on Anthropic's infrastructure.

### API Actions

| Action | HTTP Method | Endpoint | Description |
|--------|-------------|----------|-------------|
| `list` | GET | `/v1/code/triggers` | List all triggers |
| `get` | GET | `/v1/code/triggers/{id}` | Get trigger details |
| `create` | POST | `/v1/code/triggers` | Create new trigger |
| `update` | POST | `/v1/code/triggers/{id}` | Update trigger (partial) |
| `run` | POST | `/v1/code/triggers/{id}/run` | Manually run trigger |

### Implementation Details

- **Auth:** OAuth tokens managed in-process — "the token never reaches the shell"
- **Beta header:** Uses `ccr-triggers-2026-01-30` beta flag
- **Feature gates:** Requires `tengu_surreal_dali` GrowthBook flag AND `allow_remote_sessions` policy
- **Concurrency safe:** `isConcurrencySafe() = true`
- **Read-only detection:** `list` and `get` operations are marked read-only for permission classification

### Input Schema

```typescript
{
  action: 'list' | 'get' | 'create' | 'update' | 'run'
  trigger_id?: string    // Required for get, update, run
  body?: Record<string, unknown>  // JSON body for create, update
}
```

---

## Cron Scheduling (ScheduleCronTool)

### Architecture

`src/tools/ScheduleCronTool/` provides three tools for local cron scheduling:

| Tool | Name | Purpose |
|------|------|---------|
| `CronCreateTool.ts` | `CronCreate` | Schedule recurring or one-shot prompts |
| `CronDeleteTool.ts` | `CronDelete` | Cancel a scheduled job by ID |
| `CronListTool.ts` | `CronList` | List all active cron jobs |

### Feature Gates

`isKairosCronEnabled()` in `src/tools/ScheduleCronTool/prompt.ts` combines:
1. Build-time `feature('AGENT_TRIGGERS')` — dead code elimination
2. Runtime `tengu_kairos_cron` GrowthBook gate (5-minute refresh, default: `true`)
3. Local override: `CLAUDE_CODE_DISABLE_CRON` environment variable

**Durable cron** has a separate gate `isDurableCronEnabled()` via `tengu_kairos_cron_durable`.

### Scheduling Model

**Cron syntax:** Standard 5-field format in user's local timezone:
```
minute hour day-of-month month day-of-week
```

**Recurring jobs** (`recurring: true`, default):
- `*/5 * * * *` — every 5 minutes
- `0 9 * * 1-5` — weekdays at 9am local
- Auto-expire after configurable max age days

**One-shot tasks** (`recurring: false`):
- Pin specific minute/hour/day values
- Fire once then auto-delete

### Jitter and Load Distribution

The system explicitly discourages `:00` and `:30` minute marks to prevent API thundering herd:

> "Every user who asks for '9am' gets `0 9`, and every user who asks for 'hourly' gets `0 *` — which means requests from across the planet land on the API at the same instant."

Additional deterministic jitter:
- Recurring tasks: up to 10% of period (max 15 minutes)
- One-shot tasks on `:00`/`:30`: up to 90 seconds early

### Durability Modes

| Mode | Storage | Lifetime | Use Case |
|------|---------|----------|----------|
| Session-only | In-memory | Dies with process | "Remind me in 5 min" |
| Durable | `.claude/scheduled_tasks.json` | Survives restarts | "Every day at 9am" |

Durable jobs resume automatically on next launch. Missed one-shot tasks are surfaced for catch-up.

### Runtime Behavior

- Jobs only fire while the REPL is idle (not mid-query)
- Recurring tasks auto-expire after a configurable maximum age (bounds session lifetime)
- The scheduler checks for kill-switch on each poll tick via `isKairosCronEnabled()`

---

## Remote Setup

### Command: `/remote-setup`

`src/commands/remote-setup/` provides interactive setup for remote execution:

- `index.ts` — Command registration
- `remote-setup.tsx` — React/Ink UI for the setup flow
- `api.ts` — API calls for remote configuration

### Preconditions

`src/utils/background/remote/preconditions.ts` checks:
- OAuth authentication is valid and refreshed
- Organization UUID is available
- Remote sessions policy allows execution
- Network connectivity to CCR endpoints

### Remote Session Management

`src/utils/background/remote/remoteSession.ts` provides:
- Session creation with initial prompt
- Session lifecycle management (start, monitor, terminate)
- Integration with the `RemoteSessionManager` for real-time communication

---

## Remote Agent Task Integration

Remote sessions appear as `remote_agent` tasks in the local task system:

### RemoteAgentTask State

Extends `TaskStateBase` with:
- `isUltraplan: boolean` — Whether this is an ultraplan session
- `ultraplanPhase?: 'plan_ready' | 'needs_input'` — Current ultraplan phase

### Ultraplan UI

The footer pill shows special indicators for ultraplan sessions:
- `◇ ultraplan` — Running/processing
- `◇ ultraplan needs your input` — Waiting for user
- `◆ ultraplan ready` — Plan ready for approval (filled diamond)

The `pillNeedsCta()` function determines when to show the "↓ to view" call-to-action — only for attention states (`needs_input`, `plan_ready`).

---

## Agent Isolation Modes

Agent definitions support two isolation modes:

### Worktree Isolation (`isolation: 'worktree'`)

- Creates a temporary git worktree (separate working copy)
- Agent operates on isolated files — changes don't affect parent
- Worktree path and branch returned in result if changes were made
- Automatically cleaned up if no changes

### Remote Isolation (`isolation: 'remote'`)

- Ant-only feature (internal Anthropic)
- Runs agent in a remote CCR environment
- Always a background task
- Notification on completion

---

## Security Considerations

1. **OAuth tokens in-process** — RemoteTriggerTool manages tokens in-process; they never reach the shell
2. **Permission proxying** — Remote agents must request permission through the local user for sensitive operations
3. **Viewer-only mode** — `claude assistant` viewers cannot interrupt or control the remote agent
4. **Policy enforcement** — `allow_remote_sessions` policy must be enabled
5. **Connection resilience** — WebSocket reconnection with backoff; permanent disconnection reported

---

## Key Design Patterns

1. **WebSocket + HTTP** — Bidirectional: WebSocket for receiving, HTTP POST for sending
2. **Permission bridging** — Remote agents preserve the local permission model
3. **Feature layering** — Build-time gates (dead code elimination) + runtime gates (GrowthBook) + local overrides
4. **Jitter engineering** — Explicit load distribution to prevent API thundering herd
5. **Dual durability** — Session-only vs. persistent cron jobs with automatic migration
6. **Task system integration** — Remote sessions appear as standard tasks in the unified framework
7. **Graceful degradation** — Default `true` for cron enables operation when GrowthBook is unreachable
