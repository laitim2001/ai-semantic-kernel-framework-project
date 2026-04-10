# Wave 4 Path 5: Agent Spawning Flow (AgentTool → Sub-Agent Lifecycle)

> E2E source-verified trace through the complete agent spawning path.
> Verified against: CC-Source as of 2026-04-01.

## 1. Entry Point: `AgentTool.call()`

**File**: `src/tools/AgentTool/AgentTool.tsx`

### 1.1 Input Schema

Base schema (always present):

```typescript
z.object({
  description: z.string(),           // 3-5 word task summary
  prompt: z.string(),                // Full task prompt
  subagent_type: z.string().optional(),
  model: z.enum(['sonnet', 'opus', 'haiku']).optional(),
  run_in_background: z.boolean().optional(),
})
```

Full schema adds multi-agent fields (when agent swarms enabled):

```typescript
{
  name: z.string().optional(),       // Addressable via SendMessage
  team_name: z.string().optional(),
  mode: permissionModeSchema().optional(),
  isolation: z.enum(['worktree', 'remote']).optional(),
  cwd: z.string().optional(),        // KAIROS-gated
}
```

Schema gating:
- `run_in_background` is **omitted** when `FORK_SUBAGENT` feature is on or `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` is set (fork forces all async)
- `cwd` is **omitted** unless `KAIROS` feature is on

### 1.2 Output Schema

Discriminated union with two primary shapes:

| Status | Shape | When |
|--------|-------|------|
| `completed` | `{ status, result, prompt }` | Sync agent finished |
| `async_launched` | `{ status, agentId, description, prompt, outputFile, canReadOutputFile }` | Background agent started |

Plus internal-only types (excluded from exported schema for dead code elimination):
- `teammate_spawned` — multi-agent swarm spawn
- `remote_launched` — CCR remote execution

## 2. Decision Tree (6 Execution Paths)

The `call()` function implements a 6-way routing decision:

```
call() entry
│
├─ [1] team_name + name → spawnTeammate()
│   └─ Returns: teammate_spawned
│
├─ [2] Resolve effectiveType:
│   ├─ subagent_type set → use it
│   ├─ subagent_type omitted + FORK_SUBAGENT on → undefined (fork path)
│   └─ subagent_type omitted + FORK_SUBAGENT off → 'general-purpose'
│
├─ [3] isForkPath (effectiveType === undefined)
│   ├─ Recursive fork guard: reject if already in fork child
│   └─ selectedAgent = FORK_AGENT
│
├─ [4] effectiveIsolation === 'remote' (ant-only)
│   └─ teleportToRemote() → Returns: remote_launched
│
├─ [5] shouldRunAsync === true
│   └─ registerAsyncAgent() → runAsyncAgentLifecycle() (fire-and-forget)
│   └─ Returns: async_launched
│
└─ [6] Synchronous (default)
    └─ runAgent() inline → finalizeAgentTool()
    └─ Returns: completed
```

### 2.1 Teammate Path (Path 1)

**Trigger**: `team_name` resolved AND `name` provided.

Guard rails:
- Teammates cannot spawn other teammates (flat roster)
- In-process teammates cannot spawn background agents

Calls `spawnTeammate()` from `src/tools/shared/spawnMultiAgent.js`, which creates a tmux pane or in-process teammate.

### 2.2 Fork Path (Path 3)

**Trigger**: `subagent_type` omitted AND `FORK_SUBAGENT` feature gate on AND not in coordinator mode AND not in non-interactive session.

The `FORK_AGENT` definition:

```typescript
{
  agentType: 'fork',
  tools: ['*'],              // Inherits parent's exact tool pool
  maxTurns: 200,
  model: 'inherit',
  permissionMode: 'bubble',  // Surfaces permission prompts to parent
  source: 'built-in',
}
```

Key cache-sharing mechanics:
- Child inherits parent's **rendered** system prompt bytes (not recomputed)
- `buildForkedMessages()` constructs initial messages with placeholder `tool_result` blocks for every `tool_use` in the parent's assistant message, ensuring byte-identical API prefixes across siblings
- `useExactTools: true` passes parent's tool array verbatim (no re-filtering)
- Inherits parent's `thinkingConfig` for matching token output

Recursive fork guard:
- Primary: checks `querySource === 'agent:builtin:fork'` (compaction-resistant)
- Fallback: scans messages for `<fork-boilerplate>` tag

### 2.3 Remote Path (Path 4)

**Trigger**: `effectiveIsolation === 'remote'` (ant-only, dead-code-eliminated in external builds).

Calls `teleportToRemote()` → creates CCR session → `registerRemoteAgentTask()`.

### 2.4 Async vs Sync Decision (Paths 5 & 6)

```typescript
const shouldRunAsync = (
  run_in_background === true ||
  selectedAgent.background === true ||
  isCoordinator ||
  forceAsync ||               // FORK_SUBAGENT forces ALL spawns async
  assistantForceAsync ||      // KAIROS assistant mode
  isProactiveActive()
) && !isBackgroundTasksDisabled;
```

## 3. Agent Resolution & Setup

### 3.1 Agent Definition Lookup

```
allAgents = toolUseContext.options.agentDefinitions.activeAgents
  → filterDeniedAgents(agents, toolPermissionContext, AGENT_TOOL_NAME)
  → find(agent => agent.agentType === effectiveType)
```

If not found: checks if denied by permission rule (specific error) vs. truly missing.

### 3.2 MCP Server Requirement Check

If `selectedAgent.requiredMcpServers` is defined:
1. Waits up to 30s for pending MCP servers to connect
2. Verifies tools are available (connected + authenticated)
3. Throws with specific missing server names on failure

### 3.3 Tool Pool Assembly

Worker tools are assembled **independently** of parent:

```typescript
const workerPermissionContext = {
  ...appState.toolPermissionContext,
  mode: selectedAgent.permissionMode ?? 'acceptEdits'
};
const workerTools = assembleToolPool(workerPermissionContext, appState.mcp.tools);
```

Exception: Fork path uses `toolUseContext.options.tools` (parent's exact tools) for cache-identical prefixes.

### 3.4 System Prompt Construction

| Path | System Prompt Source |
|------|---------------------|
| Fork | Parent's `renderedSystemPrompt` (byte-exact copy) |
| Normal | `selectedAgent.getSystemPrompt()` + `enhanceSystemPromptWithEnvDetails()` |
| Normal + worktree/cwd | Deferred to `runAgent()` (computed inside `wrapWithCwd`) |

### 3.5 Worktree Isolation Setup

When `effectiveIsolation === 'worktree'`:

```typescript
const slug = `agent-${earlyAgentId.slice(0, 8)}`;
worktreeInfo = await createAgentWorktree(slug);
```

After agent completes: `cleanupWorktreeIfNeeded()` checks `hasWorktreeChanges()` — removes worktree if unchanged, keeps if modified.

## 4. Core Execution: `runAgent()`

**File**: `src/tools/AgentTool/runAgent.ts`

### 4.1 Signature

```typescript
async function* runAgent({
  agentDefinition, promptMessages, toolUseContext, canUseTool,
  isAsync, canShowPermissionPrompts, forkContextMessages,
  querySource, override, model, maxTurns, preserveToolUseResults,
  availableTools, allowedTools, onCacheSafeParams,
  contentReplacementState, useExactTools, worktreePath,
  description, transcriptSubdir, onQueryProgress,
}): AsyncGenerator<Message, void>
```

Returns an **async generator** yielding `Message` objects.

### 4.2 Setup Sequence

1. **Resolve model**: `getAgentModel(agentDef.model, mainLoopModel, override, permissionMode)`
2. **Create agent ID**: `createAgentId()` (or use override)
3. **Build context messages**: Fork messages (filtered for incomplete tool calls) + prompt messages
4. **Clone file state**: Fork → clone parent's cache; Normal → fresh cache with size limit
5. **Resolve user/system context**: Optionally omit `claudeMd` (for Explore/Plan agents) and `gitStatus` (Explore/Plan)
6. **Configure permission mode**: Agent definition can override; async agents auto-deny prompts (unless `bubble` mode)
7. **Resolve tools**: `useExactTools` → pass through; normal → `resolveAgentTools()` filtering
8. **Build system prompt**: Override or computed via `getAgentSystemPrompt()`
9. **Create abort controller**: Override → use it; async → new unlinked; sync → share parent's
10. **Execute `SubagentStart` hooks**: Collect additional context strings
11. **Register frontmatter hooks**: Scoped to agent lifecycle, converted `Stop` → `SubagentStop`
12. **Preload skills**: From `agentDefinition.skills` frontmatter
13. **Initialize agent MCP servers**: Additive to parent's, with proper cleanup
14. **Create subagent context**: `createSubagentContext()` with isolation boundaries

### 4.3 Query Loop

```typescript
for await (const message of query({
  messages: initialMessages,
  systemPrompt: agentSystemPrompt,
  userContext, systemContext,
  canUseTool,
  toolUseContext: agentToolUseContext,
  querySource,
  maxTurns: maxTurns ?? agentDefinition.maxTurns,
})) {
  // Forward API metrics (TTFT)
  // Handle max_turns_reached
  // Record to sidechain transcript (O(1) per message)
  // Yield recordable messages (assistant, user, progress, compact_boundary)
}
```

### 4.4 Cleanup (finally block)

Comprehensive cleanup in `finally`:
1. MCP server cleanup (agent-specific connections)
2. Clear session hooks
3. Cleanup prompt cache tracking
4. Release file state cache memory
5. Release fork context messages
6. Unregister Perfetto agent
7. Clear transcript subdir mapping
8. Remove agent's TodoWrite entries from AppState
9. Kill background bash tasks spawned by this agent
10. Kill MCP monitor tasks (if `MONITOR_TOOL` feature)

## 5. Background Agent Lifecycle

### 5.1 Async Launch (Path 5)

```typescript
// Register task in AppState
const agentBackgroundTask = registerAsyncAgent({
  agentId, description, prompt, selectedAgent,
  setAppState: rootSetAppState,
  toolUseId: toolUseContext.toolUseId
});

// Register name for SendMessage routing
if (name) {
  rootSetAppState(prev => ({
    ...prev,
    agentNameRegistry: new Map([...prev.agentNameRegistry, [name, agentId]])
  }));
}

// Fire-and-forget execution
void runWithAgentContext(asyncAgentContext, () =>
  wrapWithCwd(() => runAsyncAgentLifecycle({...}))
);
```

### 5.2 `registerAsyncAgent()`

**File**: `src/tasks/LocalAgentTask/LocalAgentTask.tsx`

Creates `LocalAgentTaskState`:

```typescript
{
  type: 'local_agent',
  status: 'running',
  agentId, prompt, selectedAgent,
  agentType: selectedAgent.agentType,
  abortController,
  retrieved: false,
  isBackgrounded: true,        // Immediately backgrounded
  pendingMessages: [],          // For SendMessage queueing
  retain: false,
  diskLoaded: false,
  // ... TaskStateBase fields (id, description, startTime, outputFile, etc.)
}
```

Registers cleanup handler via `registerCleanup()` for process exit safety.

### 5.3 Progress Tracking

`ProgressTracker` structure:

```typescript
{
  toolUseCount: number,
  latestInputTokens: number,     // Cumulative (latest API response)
  cumulativeOutputTokens: number, // Summed across turns
  recentActivities: ToolActivity[] // Last 5 tool uses
}
```

Updated via `updateProgressFromMessage()` on every assistant message. Activity descriptions resolved from `Tool.getActivityDescription()`.

### 5.4 Completion Flow

```
runAsyncAgentLifecycle()
  → runAgent() yields messages (progress tracked)
  → finalizeAgentTool() extracts result
  → completeAgentTask() sets status='completed'
  → classifyHandoffIfNeeded() (optional)
  → cleanupWorktreeIfNeeded() (optional)
  → enqueueAgentNotification() sends <task-notification> XML
```

### 5.5 Notification Format

```xml
<task-notification>
  <task-id>{taskId}</task-id>
  <tool-use-id>{toolUseId}</tool-use-id>
  <output-file>{outputPath}</output-file>
  <status>completed|failed|killed</status>
  <summary>Agent "{description}" completed</summary>
  <result>{finalMessage}</result>
  <usage>
    <total_tokens>{n}</total_tokens>
    <tool_uses>{n}</tool_uses>
    <duration_ms>{n}</duration_ms>
  </usage>
  <worktree>...</worktree>
</task-notification>
```

Delivered via `enqueuePendingNotification()` with mode `'task-notification'`.

## 6. Synchronous Agent Lifecycle (Path 6)

### 6.1 Foreground-to-Background Transition

Sync agents register as foreground tasks immediately:

```typescript
const registration = registerAgentForeground({
  agentId, description, prompt, selectedAgent,
  setAppState, toolUseId,
  autoBackgroundMs: getAutoBackgroundMs() || undefined  // 120s default
});
foregroundTaskId = registration.taskId;
backgroundPromise = registration.backgroundSignal;
```

Main loop **races** between next message and background signal:

```typescript
const raceResult = await Promise.race([
  agentIterator.next().then(r => ({ type: 'message', result: r })),
  backgroundPromise  // Resolves when user/timer backgrounds the task
]);
```

If backgrounded:
1. Stop foreground summarization
2. Return `.return()` on the iterator (triggers cleanup)
3. Restart `runAgent()` with `isAsync: true` in a detached `void` closure
4. Return `async_launched` result to parent

### 6.2 Normal Sync Completion

If agent completes without backgrounding:

```typescript
const agentResult = finalizeAgentTool(agentMessages, syncAgentId, metadata);
// Unregister foreground task
// Cleanup worktree
// Return { status: 'completed', ...agentResult, prompt }
```

## 7. Built-in Agent Definitions

**File**: `src/tools/AgentTool/built-in/`

| Agent | Type | Model | Tools | Key Properties |
|-------|------|-------|-------|----------------|
| **General Purpose** | `general-purpose` | inherited | `['*']` | Default agent; full tool access |
| **Explore** | `Explore` | `haiku` (external) / `inherit` (ant) | All minus write tools | Read-only; `omitClaudeMd: true` |
| **Plan** | `Plan` | `haiku` (external) / `inherit` (ant) | All minus write tools | Read-only architect; `omitClaudeMd: true` |
| **Verification** | `verification` | `inherit` | All minus write tools | `background: true`; `color: 'red'`; strict PASS/FAIL/PARTIAL verdict |
| **Claude Code Guide** | see file | — | — | Onboarding/help agent |

### 7.1 Tool Filtering

`filterToolsForAgent()` in `agentToolUtils.ts`:

| Filter Set | Scope |
|------------|-------|
| `ALL_AGENT_DISALLOWED_TOOLS` | Blocked for all agents |
| `CUSTOM_AGENT_DISALLOWED_TOOLS` | Additionally blocked for non-built-in agents |
| `ASYNC_AGENT_ALLOWED_TOOLS` | Whitelist for async agents |
| `IN_PROCESS_TEAMMATE_ALLOWED_TOOLS` | Whitelist for in-process teammates |

MCP tools (`mcp__*`) always pass through all filters.

## 8. Inter-Agent Communication: SendMessageTool

**File**: `src/tools/SendMessageTool/SendMessageTool.ts`

### 8.1 Input Schema

```typescript
z.object({
  to: z.string(),     // Teammate name, "*" for broadcast, or "uds:<path>"
  summary: z.string().optional(),
  message: z.union([
    z.string(),
    StructuredMessage()  // shutdown_request | shutdown_response | plan_approval_response
  ]),
})
```

### 8.2 Message Routing

| Target | Handler | Mechanism |
|--------|---------|-----------|
| Named teammate | `handleMessage()` | `writeToMailbox()` → filesystem mailbox |
| `"*"` | `handleBroadcast()` | Iterates team file members, writes to each mailbox |
| `"uds:<path>"` | UDS peer routing | Unix domain socket (feature-gated) |
| `"bridge:<id>"` | REPL bridge | Remote control peer |

### 8.3 Mailbox System

`writeToMailbox(recipientName, message, teamName)` writes a JSON envelope to the recipient's filesystem mailbox:

```typescript
{
  from: senderName,
  text: content,
  summary,
  timestamp: new Date().toISOString(),
  color: senderColor,
}
```

### 8.4 Structured Messages

Beyond plain text, agents can send structured protocol messages:
- **shutdown_request**: Ask teammate to shut down
- **shutdown_response**: Approve/reject shutdown with optional pane ID
- **plan_approval_response**: Approve/reject a plan with feedback

### 8.5 Background Agent Messaging

For non-teammate background agents, `queuePendingMessage()` in LocalAgentTask queues messages that are `drainPendingMessages()` at tool-round boundaries. Also `resumeAgentBackground()` can inject messages into a running background agent.

## 9. Existing Analysis Accuracy Verification

### `06-agent-system/agent-delegation.md` — Accuracy: **HIGH (9/10)**

Verified claims:
- Input/output schemas: **Correct** (base + full schemas match)
- Execution modes table: **Correct** (5 modes listed, all verified)
- Built-in agent types: **Correct** (general-purpose, Explore details match)
- Spawn flow 7 steps: **Correct** (validate → context → tools → prompt → model → execute → finalize)
- Fork subagent cache sharing: **Correct** (byte-identical system prompt, buildForkedMessages)
- Agent color management: **Correct**
- Tool restriction constants: **Correct**

Minor gaps:
- Missing the 6th execution path (teammate spawn via `spawnTeammate()`)
- Missing `registerAgentForeground()` and the foreground-to-background race
- `runAsyncAgentLifecycle` mentioned but internal flow not detailed
- Missing `autoBackgroundMs` (120s auto-background timer)

### `06-agent-system/task-framework.md` — Accuracy: **HIGH (9/10)**

Verified claims:
- 7 task types with ID prefixes: **Correct**
- Task state machine (pending → running → completed/failed/killed): **Correct**
- `TaskStateBase` fields: **Correct**
- Task ID generation (prefix + 8 alphanumeric): **Correct**
- `LocalAgentTaskState` extensions: **Correct** (verified `pendingMessages`, `isBackgrounded`, `retain`, `diskLoaded`, `evictAfter`)
- `registerAsyncAgent` / `completeAgentTask` / `failAgentTask` / `killAsyncAgent`: All verified
- `enqueueAgentNotification` XML format: **Correct**

Minor gaps:
- Missing `updateAgentSummary()` for periodic background summarization
- Missing `appendMessageToLocalAgent()` for transcript display
- Missing `registerAgentForeground()` (foreground → background transition mechanism)
- `PANEL_GRACE_MS` eviction deadline not documented

## 10. Key Findings

### Architecture Insights

1. **Fork subagent is the most sophisticated path**: Byte-level prompt cache sharing via `renderedSystemPrompt` threading, placeholder `tool_result` blocks for cache-identical prefixes, and `useExactTools` to avoid tool-definition divergence.

2. **Foreground-to-background is a race pattern**: Sync agents compete `agentIterator.next()` against a `backgroundSignal` promise. On background transition, the iterator is `.return()`-ed (triggering cleanup) and a fresh `runAgent()` starts in a detached async closure.

3. **`runAgent()` is an async generator, not a simple function**: The caller (AgentTool) iterates the generator, allowing it to intercept progress, handle backgrounding, and track messages incrementally.

4. **Cleanup is comprehensive**: The `finally` block in `runAgent()` handles 10 distinct cleanup operations, from MCP servers to Perfetto traces to orphaned bash tasks.

5. **SendMessage uses filesystem mailboxes, not IPC**: Inter-agent communication goes through `writeToMailbox()` which writes JSON files, not direct memory sharing. Background agents receive messages via `queuePendingMessage()` drained at tool-round boundaries.

6. **Agent tool pool is rebuilt independently**: Workers get their tools from `assembleToolPool()` with their own permission mode, not inherited from parent. Exception: fork path uses parent's exact tools.

---

**Wave**: 4 | **Path**: 5 of 6 | **Quality**: 9.0/10
**Files analyzed**: 9 source files, 2 existing analysis docs
**Verification points**: ~85 claims verified across source code
