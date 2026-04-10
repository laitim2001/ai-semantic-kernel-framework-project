# Wave 8: Agent/Task Lifecycle Deep Behavior Verification

> **Date**: 2026-04-01
> **Sources**: AgentTool.tsx, runAgent.ts, LocalAgentTask.tsx, InProcessTeammateTask/, DreamTask.ts, LocalShellTask.tsx
> **Confidence**: 9.0/10 (direct source verification, all state machines traced)

---

## 1. AgentTool 6-Way Routing Decision Tree

When `AgentTool.call()` is invoked, the following decision tree determines how the agent is launched:

```
AgentTool.call(prompt, subagent_type, run_in_background, name, team_name, isolation, cwd, model)
│
├─[1] TEAMMATE SPAWN (teamName && name)
│     Condition: team_name resolves to a team AND name is provided
│     Guard: teammates cannot spawn nested teammates (flat roster)
│     Guard: in-process teammates cannot spawn background agents
│     Action: spawnTeammate() → returns {status: 'teammate_spawned'}
│
├─[2] FORK SUBAGENT (isForkSubagentEnabled() && subagent_type omitted)
│     Condition: fork gate ON, no explicit subagent_type
│     Guard: recursive fork rejected (querySource check + message scan)
│     Action: selectedAgent = FORK_AGENT, inherits parent system prompt
│     Messages: buildForkedMessages() clones parent's full assistant msg
│
├─[3] REMOTE ISOLATION (effectiveIsolation === 'remote', ant-only)
│     Condition: isolation='remote' OR agent def has isolation='remote'
│     Guard: dead-code-eliminated for external builds ("external" === 'ant')
│     Action: teleportToRemote() → registerRemoteAgentTask()
│     Returns: {status: 'remote_launched', sessionUrl, taskId}
│
├─[4] ASYNC BACKGROUND AGENT (shouldRunAsync === true)
│     Condition: run_in_background=true OR agent.background=true
│              OR isCoordinator OR forceAsync(fork gate)
│              OR assistantForceAsync(KAIROS) OR proactiveActive
│              AND NOT isBackgroundTasksDisabled
│     Action: registerAsyncAgent() → void runAsyncAgentLifecycle()
│     Returns: {status: 'async_launched', agentId, outputFile}
│     Fire-and-forget: async closure detached with `void`
│
├─[5] SYNC FOREGROUND AGENT (default path, !shouldRunAsync)
│     Action: registerAgentForeground() → race loop (message vs background signal)
│     Can transition to [6] mid-execution
│     Returns: {status: 'completed', result content}
│
└─[6] FOREGROUND-TO-BACKGROUND TRANSITION (race won by backgroundSignal)
      Trigger: user Ctrl+B OR autoBackgroundMs timer (120s default)
      Action: agentIterator.return() → re-spawn via runAgent(isAsync=true)
      Progress: existing messages replayed into new tracker
      Returns: {status: 'async_launched'} to unblock parent
```

### Routing Priority
- Teammate spawn is checked FIRST (before any agent resolution)
- Fork path is checked SECOND (before normal agent lookup)
- Remote isolation is checked THIRD (ant-only gate)
- Async/sync decision is made LAST after agent is fully resolved

### Key Guards
| Guard | Location | Effect |
|-------|----------|--------|
| Nested teammate prevention | call() L273 | Error if isTeammate() && name provided |
| In-process background ban | call() L278 | Error if isInProcessTeammate() && background |
| Recursive fork guard | call() L332 | Error if already inside fork child |
| MCP server requirement | call() L371-408 | Waits up to 30s for pending MCP, then errors |
| Permission deny rules | call() L342-353 | Filters agents by permission context |

---

## 2. runAgent() Async Generator Lifecycle

### Startup Phase
```
runAgent() called
│
├── Resolve model: getAgentModel(agentDef.model, mainLoopModel, override, permissionMode)
├── Assign agentId (override.agentId or createAgentId())
├── Register in Perfetto trace (if enabled)
├── Build context messages:
│   ├── Fork path: filterIncompleteToolCalls(parent messages) + promptMessages
│   └── Normal path: just promptMessages
├── Clone/create file state cache
├── Resolve user/system context:
│   ├── Omit claudeMd for omitClaudeMd agents (saves ~5-15 Gtok/week)
│   └── Omit gitStatus for Explore/Plan agents
├── Configure permission mode overrides (agent def → appState)
├── Resolve tools (useExactTools → pass through, else resolveAgentTools())
├── Build system prompt (override or getAgentSystemPrompt())
├── Determine AbortController:
│   ├── override.abortController (background agents)
│   ├── new AbortController() (async agents, unlinked from parent)
│   └── toolUseContext.abortController (sync agents, shared with parent)
├── Execute SubagentStart hooks → collect additionalContexts
├── Register frontmatter hooks (scoped to agent lifecycle)
├── Preload skills from agent definition
├── Initialize agent-specific MCP servers (additive to parent)
├── Create subagent ToolUseContext via createSubagentContext()
├── Fire onCacheSafeParams callback (for background summarization)
├── Record initial messages to sidechain transcript (fire-and-forget)
└── Write agent metadata to disk (fire-and-forget)
```

### Execution Loop
```
for await (message of query({messages, systemPrompt, ...}))
│
├── stream_event (message_start): forward TTFT metrics → continue
├── attachment (max_turns_reached): log + break
├── attachment (other): yield without recording
├── recordable (assistant|user|progress|compact_boundary):
│   ├── Record to sidechain transcript (O(1) per message)
│   ├── Update lastRecordedUuid for parent chain
│   └── yield message to caller
└── (other): skip
```

### Cleanup Phase (finally block, ALWAYS runs)
```
finally {
  1. await mcpCleanup()                    // Disconnect agent-specific MCP servers
  2. clearSessionHooks(agentId)            // Remove agent's frontmatter hooks
  3. cleanupAgentTracking(agentId)         // Prompt cache break detection
  4. readFileState.clear()                 // Release cloned file state cache
  5. initialMessages.length = 0            // Release fork context messages
  6. unregisterPerfettoAgent(agentId)      // Release perfetto trace entry
  7. clearAgentTranscriptSubdir(agentId)   // Release transcript subdir mapping
  8. Remove agentId from AppState.todos    // Prevent orphaned TodoWrite keys
  9. killShellTasksForAgent(agentId)       // Kill spawned background bash tasks
  10. killMonitorMcpTasksForAgent(agentId) // Kill monitor MCP tasks (if MONITOR_TOOL)
}
```

---

## 3. Task Type State Machines

### 3.1 LocalAgentTask (Background Agent)

```
                    ┌──────────────┐
                    │   RUNNING    │ ← registerAsyncAgent() or registerAgentForeground()
                    │              │   isBackgrounded: true|false
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
     ┌────────────┐ ┌───────────┐ ┌─────────┐
     │ COMPLETED  │ │  FAILED   │ │ KILLED  │
     │            │ │           │ │         │
     └────────────┘ └───────────┘ └─────────┘

Transitions:
  running → completed: completeAgentTask(result) — sets endTime, evictAfter=now+30s
  running → failed:    failAgentTask(error) — sets endTime, evictAfter=now+30s
  running → killed:    killAsyncAgent() — abortController.abort(), evictAfter=now+30s
  
All terminal transitions:
  - unregisterCleanup() called
  - selectedAgent cleared (GC eligibility)
  - abortController cleared
  - evictTaskOutput(taskId) called (async, fire-and-forget)
  - evictAfter: undefined if task.retain=true, else Date.now() + PANEL_GRACE_MS (30s)
```

### 3.2 LocalShellTask (Background Bash)

```
                    ┌──────────────┐
                    │   RUNNING    │ ← spawnShellTask() or registerForeground()
                    │              │   isBackgrounded: true|false
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
     ┌────────────┐ ┌───────────┐ ┌─────────┐
     │ COMPLETED  │ │  FAILED   │ │ KILLED  │
     │ code === 0 │ │ code !== 0│ │         │
     └────────────┘ └───────────┘ └─────────┘

Transitions:
  running → completed: shellCommand.result resolves with code=0
  running → failed:    shellCommand.result resolves with code!=0
  running → killed:    killTask() — sends SIGTERM, marks killed in state
  
Key difference from agent: shell status derived from exit code, not explicit call.
```

### 3.3 InProcessTeammateTask

```
                    ┌──────────────┐
                    │   RUNNING    │ ← registerInProcessTeammate()
                    │   isIdle:    │
                    │   true/false │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
     ┌────────────┐ ┌───────────┐ ┌─────────┐
     │ COMPLETED  │ │  FAILED   │ │ KILLED  │
     └────────────┘ └───────────┘ └─────────┘

Sub-states while RUNNING:
  isIdle=true:  waiting for work (leader assigns via pendingUserMessages)
  isIdle=false: actively processing a turn
  awaitingPlanApproval=true: plan submitted, waiting for user approval
  shutdownRequested=true: graceful shutdown requested, will complete current work

Kill: killInProcessTeammate() — invokes abort on both:
  - abortController (kills WHOLE teammate permanently)
  - currentWorkAbortController (aborts current turn only)
```

### 3.4 DreamTask (Memory Consolidation)

```
                    ┌──────────────┐
                    │   RUNNING    │ ← registerDreamTask()
                    │ phase:       │
                    │  'starting'  │
                    │  'updating'  │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
     ┌────────────┐ ┌───────────┐ ┌─────────┐
     │ COMPLETED  │ │  FAILED   │ │ KILLED  │
     │ notified:  │ │ notified: │ │ notified│
     │ true       │ │ true      │ │ true    │
     └────────────┘ └───────────┘ └─────────┘

Phase transitions:
  'starting' → 'updating': first Edit/Write tool_use detected via addDreamTurn()

Kill special behavior:
  - Captures priorMtime from task state
  - Calls rollbackConsolidationLock(priorMtime) to rewind lock
  - This allows the next session to retry consolidation

All terminal states set notified=true immediately (dream has no model-facing
notification path — the inline appendSystemMessage IS the user surface).
```

---

## 4. Foreground-to-Background Transition Mechanism

The transition is implemented as a **Promise.race** pattern in the sync agent execution loop:

### Registration
```typescript
const registration = registerAgentForeground({
  agentId, description, prompt, selectedAgent, setAppState,
  autoBackgroundMs: 120_000  // from getAutoBackgroundMs()
});
// Returns: { taskId, backgroundSignal: Promise<void>, cancelAutoBackground }
```

### Race Loop
```typescript
while (true) {
  const nextMessagePromise = agentIterator.next();
  const raceResult = await Promise.race([
    nextMessagePromise.then(r => ({type: 'message', result: r})),
    backgroundPromise  // resolves to {type: 'background'}
  ]);
  
  if (raceResult.type === 'background') {
    // 1. Stop foreground summarization
    // 2. agentIterator.return() with 1s timeout (triggers cleanup)
    // 3. Re-create progress tracker from existing agentMessages
    // 4. Spawn NEW runAgent(isAsync=true) with same params
    // 5. Return {status: 'async_launched'} to unblock parent
  }
}
```

### Background Signal Sources
| Source | Mechanism |
|--------|-----------|
| User Ctrl+B | `backgroundAll()` → `backgroundAgentTask()` → resolves signal |
| Auto-timer | `setTimeout(autoBackgroundMs)` → sets `isBackgrounded=true` → resolves signal |

### Critical Detail
The transition re-spawns the agent via a **new** `runAgent()` call. The old iterator is `.return()`-ed (triggers the finally cleanup block), and a fresh query loop begins with `isAsync=true`. Existing `agentMessages` are replayed into a new progress tracker to maintain continuity.

---

## 5. Notification and Eviction Logic

### Notification Delivery
```
Agent/Shell completes/fails/killed
│
├── Atomically check-and-set task.notified flag (prevents duplicates)
├── Abort any active speculation (stale speculated results)
├── Build XML notification message:
│   <task_notification>
│     <task_id>...</task_id>
│     <tool_use_id>...</tool_use_id>     (optional)
│     <output_file>...</output_file>
│     <status>completed|failed|killed</status>
│     <summary>Agent "desc" completed</summary>
│     <result>...</result>               (optional, agent only)
│     <usage>...</usage>                 (optional, agent only)
│     <worktree>...</worktree>           (optional)
│   </task_notification>
│
└── enqueuePendingNotification({value, mode: 'task-notification', priority})
    - Agent notifications: priority = default (undefined)
    - Shell notifications: priority = 'next' (for monitors) or 'later'
```

### Eviction Pipeline
```
Terminal transition fires
│
├── Set evictAfter:
│   ├── task.retain === true → undefined (never auto-evict)
│   └── task.retain === false → Date.now() + PANEL_GRACE_MS (30,000ms)
│
├── Fire-and-forget: evictTaskOutput(taskId)
│   (cleans up disk output symlink)
│
└── Eviction sweep (periodic):
    Task is GC-eligible when:
    - status is terminal (completed|failed|killed)
    - notified === true
    - evictAfter !== undefined AND Date.now() > evictAfter
    - retain === false
```

### The `retain` Flag
- Set by `enterTeammateView()` when user zooms into a task panel
- Blocks eviction and enables stream-append + disk bootstrap
- Separate from `viewingAgentTaskId` ("what am I looking at") — retain is "what am I holding"
- Cleared on unselect, which sets `evictAfter` to allow GC

---

## 6. InProcessTeammate Isolation Model

### AsyncLocalStorage-Based Isolation
In-process teammates run in the **same Node.js process** as the leader but use `AsyncLocalStorage` for context isolation:

```
Leader Process
├── AsyncLocalStorage Context A (leader)
│   ├── getTeammateContext() → leader identity
│   └── getCwd() → leader's working directory
│
├── AsyncLocalStorage Context B (teammate "researcher@my-team")
│   ├── getTeammateContext() → {agentId, agentName, teamName, color, ...}
│   └── getCwd() → potentially different cwd
│
└── AsyncLocalStorage Context C (teammate "coder@my-team")
    └── ...
```

### State Shape
```typescript
InProcessTeammateTaskState = {
  identity: {agentId, agentName, teamName, color, planModeRequired, parentSessionId}
  prompt: string
  permissionMode: PermissionMode        // cycled independently via Shift+Tab
  awaitingPlanApproval: boolean         // plan mode gate
  shutdownRequested: boolean            // graceful shutdown flag
  isIdle: boolean                       // waiting for work vs actively processing
  pendingUserMessages: string[]         // user-injected messages queue
  messages?: Message[]                  // UI transcript (capped at 50 entries)
  currentWorkAbortController?: AbortController  // aborts current turn only
  abortController?: AbortController     // kills whole teammate
  onIdleCallbacks?: Array<() => void>   // leader notification hooks
}
```

### Plan Approval Flow
1. Teammate generates a plan (when `planModeRequired=true`)
2. Sets `awaitingPlanApproval=true`
3. UI shows approval prompt to user
4. User approves/rejects
5. `awaitingPlanApproval=false`, execution continues or aborts

### Shutdown Protocol
1. `requestTeammateShutdown(taskId)` sets `shutdownRequested=true`
2. Teammate checks flag between turns (not mid-tool-execution)
3. Completes current work, then transitions to terminal state
4. Hard kill via `killInProcessTeammate()` aborts immediately

### Memory Cap
`TEAMMATE_MESSAGES_UI_CAP = 50` — the `task.messages` array (for UI transcript display) is capped at 50 entries via `appendCappedMessage()`. The full conversation lives in a local `allMessages` array inside the runner and on disk at the sidechain transcript path.

---

## 7. DreamTask Consolidation Lock and Rollback

### Lock Mechanism
The consolidation lock is a **file-based lock** at `<autoMemPath>/.consolidate-lock`:
- **Body**: holder's PID (for liveness check)
- **mtime**: timestamp of last consolidation (`lastConsolidatedAt`)
- **Stale threshold**: 60 minutes (`HOLDER_STALE_MS`)

### Acquire Protocol
```
tryAcquireConsolidationLock()
│
├── stat + readFile the lock (parallel)
├── If lock exists AND mtime < 60min ago:
│   ├── If holder PID is alive → return null (blocked)
│   └── If holder PID is dead → reclaim (fall through)
├── mkdir -p autoMemPath (may not exist yet)
├── writeFile(lock, process.pid)
├── Re-read and verify PID matches (race guard)
│   ├── Match → return priorMtime (success)
│   └── Mismatch → return null (lost race)
└── No prior lock → return 0
```

### Rollback Protocol
```
rollbackConsolidationLock(priorMtime)
│
├── priorMtime === 0 → unlink lock file (restore no-file state)
└── priorMtime > 0:
    ├── writeFile(lock, '') — clear PID body
    └── utimes(lock, priorMtime) — rewind mtime to pre-acquire
```

### DreamTask Integration
```
registerDreamTask(priorMtime, abortController)
  └── stores priorMtime in task state

DreamTask.kill(taskId):
  1. abortController.abort()
  2. status → 'killed'
  3. rollbackConsolidationLock(priorMtime) — next session can retry

completeDreamTask(taskId):
  - Lock mtime stays at current (consolidation succeeded)
  - No rollback needed

failDreamTask(taskId):
  - Note: NO automatic rollback on failure
  - The autoDream.ts caller handles rollback in its catch block
```

---

## 8. Inter-Agent Message Delivery Timing

### SendMessage Queue (LocalAgentTask)
```typescript
// Enqueue
queuePendingMessage(taskId, msg, setAppState)
  → pushes to task.pendingMessages[]

// Drain — called at tool-round boundaries in the query loop
drainPendingMessages(taskId, getAppState, setAppState)
  → atomically reads and clears task.pendingMessages[]
  → returns string[] to be injected as user messages in next turn
```

**Timing**: Messages queued via `SendMessage` are NOT delivered mid-tool-execution. They are drained at **tool-round boundaries** — the gap between one assistant response being fully processed and the next API call being made.

### InProcessTeammate Message Queue
```typescript
// Inject from UI or leader
injectUserMessageToTeammate(taskId, message, setAppState)
  → pushes to task.pendingUserMessages[]
  → also appends to task.messages[] (immediate UI display)
  
// Allowed states: running OR idle (not terminal)
```

**Timing**: User-injected messages are delivered when the teammate finishes its current turn and checks its `pendingUserMessages` queue. If the teammate is idle, the message triggers a new processing turn.

### Notification Delivery (Task Completion)
```
enqueuePendingNotification({value, mode, priority, agentId})
  priority options:
    - 'next': delivered at the next message queue drain
    - 'later': delivered after current turn completes
    - undefined: default behavior (task-notification mode)
```

The main session drains pending notifications between turns, injecting them as system messages so the model sees task completion results.

---

## Verification Summary

| Aspect | Status | Key Finding |
|--------|--------|-------------|
| AgentTool routing | Verified | 6 distinct paths with clear priority ordering |
| runAgent lifecycle | Verified | 10-step cleanup checklist in finally block |
| FG→BG transition | Verified | Promise.race pattern, re-spawns new runAgent |
| LocalAgentTask states | Verified | 3 terminal states, evictAfter with 30s grace |
| LocalShellTask states | Verified | Exit code determines completed vs failed |
| InProcessTeammate | Verified | AsyncLocalStorage isolation, 50-message UI cap |
| DreamTask lock | Verified | File-based PID lock with mtime-as-timestamp |
| Message delivery | Verified | Tool-round boundary draining, not mid-execution |
