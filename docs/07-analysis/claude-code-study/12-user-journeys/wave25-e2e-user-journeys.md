# Wave 25-26: E2E User Journey Verification

> **Verification Date**: 2026-04-01
> **Source Commit**: Claude Code source (CC-Source)
> **Scope**: 5 end-to-end user journeys traced through source code
> **Quality Target**: Step-by-step with source file references

---

## Journey 1: New User First Session

**Trace**: `claude` command -> cli.tsx -> init -> onboarding -> trust dialog -> REPL -> first message -> response

### Step-by-Step Flow

#### Step 1: CLI Entry Point
- **File**: `src/entrypoints/cli.tsx` (L33-42)
- `main()` parses `process.argv`. Fast-path checks for `--version`, `--dump-system-prompt`, `--daemon`, `--bg`, etc.
- If none match, falls through to the full CLI path.

#### Step 2: Load Main Module
- **File**: `src/entrypoints/cli.tsx` (L295)
- Dynamically imports `../main.js` — the Commander.js program definition.
- `import('../main.js')` triggers heavy module evaluation (~135ms), profiled via `startupProfiler`.

#### Step 3: Initialization (`init()`)
- **File**: `src/entrypoints/init.ts` (L57-238)
- `init()` is memoized (runs once). Key steps:
  1. `enableConfigs()` — validate and enable configuration system (L63-69)
  2. `applySafeConfigEnvironmentVariables()` — apply safe env vars before trust (L74)
  3. `applyExtraCACertsFromConfig()` — TLS certs for Bun (L79)
  4. `setupGracefulShutdown()` — register cleanup handlers (L87)
  5. Initialize 1P event logging, OAuth, JetBrains detection (L94-128)
  6. `configureGlobalMTLS()` + `configureGlobalAgents()` — proxy/mTLS (L136-151)
  7. `preconnectAnthropicApi()` — overlap TCP+TLS handshake with setup (L159)
  8. `setShellIfWindows()` — configure git-bash on Windows (L186)
  9. `ensureScratchpadDir()` if scratchpad enabled (L203-209)

#### Step 4: Commander Action Handler
- **File**: `src/main.tsx` (L1006-1119)
- The `.action(async (prompt, options) => { ... })` handler fires.
- Extracts options: `debug`, `permissionMode`, `mcpConfig`, `tools`, `addDir`, etc.
- Seeds early input if `--prefill` provided.

#### Step 5: Onboarding Screen
- **File**: `src/interactiveHelpers.tsx` (L104-123)
- `showSetupScreens()` checks `config.hasCompletedOnboarding`.
- If first run: dynamically imports `Onboarding` component, renders theme picker and welcome.
- Calls `completeOnboarding()` on done — persists to global config.

#### Step 6: Trust Dialog
- **File**: `src/interactiveHelpers.tsx` (L131-171)
- Always shown for interactive sessions (unless already accepted).
- `checkHasTrustDialogAccepted()` — fast-path skip if CWD already trusted.
- Otherwise: imports `TrustDialog` component, warns about untrusted repos, checks CLAUDE.md external includes.
- After acceptance: `setSessionTrustAccepted(true)`, reinitialize GrowthBook, prefetch system context.
- Handles MCP `.mcp.json` server approvals and CLAUDE.md external includes warnings.

#### Step 7: Launch REPL
- **File**: `src/replLauncher.tsx` (L12-22)
- `launchRepl(root, appProps, replProps, renderAndRun)`:
  1. Imports `App` component (providers: theme, state, stats, notifications)
  2. Imports `REPL` screen component
  3. Renders `<App><REPL {...replProps} /></App>` via Ink's render pipeline.

#### Step 8: REPL Awaits Input
- **File**: `src/screens/REPL.tsx` (L1-80+)
- `REPL` component initializes:
  - File state cache, abort controller, messages array, tools
  - `PromptInput` component renders the `>` prompt with input handling
  - Waits for user to type and press Enter.

#### Step 9: First Message Submission
- **File**: `src/screens/REPL.tsx` (L3142-3260)
- `onSubmit(input, helpers)`:
  1. Re-pins scroll to bottom
  2. Checks for slash commands (`/` prefix) — if not, continues to normal message
  3. Expands pasted text references
  4. Adds input to history via `addToHistory()`
  5. Creates user message via `createUserMessage()`
  6. Calls `onQuery()` with the message array

#### Step 10: API Query
- **File**: `src/screens/REPL.tsx` (L2661-2740+)
- `onQueryImpl()`:
  1. Starts IDE diagnostic tracking
  2. Marks onboarding complete
  3. Generates session title via Haiku model (async, fire-and-forget)
  4. Sets additional allowed tools from skill frontmatter
  5. Calls the streaming API via `query()` from `src/query.ts`
  6. Streams response tokens back through `onQueryEvent` handler
  7. Renders assistant response in the message list

---

## Journey 2: File Edit Cycle

**Trace**: User asks "edit file X" -> Claude reads file -> proposes edit -> permission prompt -> file written -> diff shown

### Step-by-Step Flow

#### Step 1: User Request
- User types "edit file X to change Y to Z" in the REPL prompt.
- `onSubmit` -> `onQuery` -> streaming API call.

#### Step 2: Claude Decides to Read File (FileReadTool)
- **File**: `src/tools/FileReadTool/FileReadTool.ts` (L496+)
- Model returns `tool_use` block with `Read` tool and `{file_path, offset?, limit?}`.
- `FileReadTool.call()`:
  1. Expands path via `expandPath()` — handles `~`, relative paths, Windows normalization
  2. Checks read permission via `checkReadPermissionForTool()` (L71)
  3. Validates: not a blocked device path, not too large, not binary
  4. For text files: reads via `readFileInRange()` with offset/limit
  5. Adds line numbers via `addLineNumbers()` — the `cat -n` format
  6. Returns `{type: 'text', file: {filePath, content, numLines, startLine, totalLines}}`
  7. Updates `readFileState` cache with timestamp for staleness detection

#### Step 3: Claude Proposes Edit (FileEditTool)
- **File**: `src/tools/FileEditTool/FileEditTool.ts` (L86-574)
- Model returns `tool_use` block with `Edit` tool and `{file_path, old_string, new_string, replace_all?}`.

#### Step 4: Input Validation
- **File**: `src/tools/FileEditTool/FileEditTool.ts` (L137-270)
- `validateInput()`:
  1. Checks `old_string !== new_string` (no-op guard)
  2. Checks deny rules in permission settings
  3. Security: skips filesystem ops for UNC paths (NTLM leak prevention)
  4. Checks file size < 1 GiB limit
  5. Reads file content, checks if file exists
  6. For new files: `old_string === ''` allowed only if file doesn't exist
  7. For `.ipynb` files: rejects (use NotebookEditTool)

#### Step 5: Permission Check
- **File**: `src/tools/FileEditTool/FileEditTool.ts` (L122-132)
- `checkPermissions()` calls `checkWritePermissionForTool()`:
  - Checks against permission mode (ask/auto-accept/deny)
  - If "ask" mode: renders `PermissionRequest` component in the REPL
  - User sees the proposed edit and can Accept (y), Reject (n), or Always Allow

#### Step 6: Execute Edit
- **File**: `src/tools/FileEditTool/FileEditTool.ts` (L387-574)
- `call()`:
  1. Expands path, discovers skills from file path (L402-423)
  2. Tracks diagnostic state via `diagnosticTracker.beforeFileEdited()` (L425)
  3. Creates parent directory if needed (L430)
  4. Backs up file via `fileHistoryTrackEdit()` if file history enabled (L432-440)
  5. **Critical Section** (L444-468): Loads current content, checks staleness:
     - Compares `lastWriteTime` vs `readFileState` timestamp
     - Throws `FILE_UNEXPECTEDLY_MODIFIED_ERROR` if file changed since last read
  6. Uses `findActualString()` for quote normalization (L471-472)
  7. `getPatchForEdit()` generates structured patch (L482-488)
  8. `writeTextContent()` writes to disk with original encoding/line-endings (L491)
  9. Notifies LSP servers: `changeFile()` + `saveFile()` for diagnostics (L494-513)
  10. Notifies VSCode for diff view (L517)
  11. Updates `readFileState` with new content and timestamp (L520-525)
  12. Returns `{filePath, oldString, newString, originalFile, structuredPatch}`

#### Step 7: UI Renders Diff
- **File**: `src/tools/FileEditTool/UI.tsx`
- `renderToolResultMessage()` shows the edit result:
  - Green/red diff patch in the terminal
  - File path and line change count

---

## Journey 3: MCP Tool Usage

**Trace**: User has MCP server configured -> Claude discovers tools -> invokes MCP tool -> result displayed

### Step-by-Step Flow

#### Step 1: MCP Configuration Loading
- **File**: `src/services/mcp/client.ts` (L2226-2320)
- During startup, `getMcpToolsCommandsAndResources()` is called:
  1. Reads all MCP configs from `getAllMcpConfigs()` — merges user, project, local, `.mcp.json`
  2. Partitions into disabled and active servers
  3. Splits by transport type: local (stdio/sdk — lower concurrency) vs remote (SSE/HTTP — higher concurrency)
  4. Processes servers in parallel via `pMap()`

#### Step 2: Server Connection
- **File**: `src/services/mcp/client.ts` (L2282-2320)
- `processServer()` per config entry:
  1. Skips disabled servers (adds as `type: 'disabled'`)
  2. Skips servers with cached 401 auth (15-min TTL)
  3. For stdio: spawns child process with MCP protocol
  4. For SSE/HTTP: connects via HTTP with optional OAuth
  5. Calls `connectToServer(name, config)` — memoized for shared clients

#### Step 3: Tool Discovery
- **File**: `src/services/mcp/client.ts`
- After connection, `fetchToolsForClient(client)` retrieves available tools:
  1. Calls MCP `tools/list` method on the server
  2. For each tool: creates a `Tool` object wrapping `MCPTool` template
  3. Overrides `name`, `description`, `prompt`, `call`, `userFacingName` from MCP metadata
  4. Tool names are prefixed: `mcp__<serverName>__<toolName>`
  5. Tools are registered into the app state's tool pool via `onConnectionAttempt` callback

#### Step 4: User Sends Message Requiring MCP Tool
- User asks something that needs an MCP tool (e.g., "search the web for X").
- Claude's response includes a `tool_use` block targeting `mcp__<server>__<tool>`.

#### Step 5: MCP Tool Permission Check
- **File**: `src/tools/MCPTool/MCPTool.ts` (L56-61)
- `checkPermissions()` returns `{behavior: 'passthrough'}` — always requires permission.
- REPL renders `PermissionRequest` component for user approval.

#### Step 6: MCP Tool Execution
- **File**: `src/services/mcp/client.ts` (L2813-2910)
- `callMCPToolWithUrlElicitationRetry()`:
  1. Calls `callMCPTool()` which invokes `client.callTool({name, arguments})` on the MCP transport
  2. Handles URL elicitation errors (OAuth flows) with up to 3 retries
  3. Supports progress callbacks via `onProgress` for streaming status
  4. Returns `MCPToolCallResult` with content blocks (text, images, resources)

#### Step 7: Result Display
- **File**: `src/tools/MCPTool/UI.tsx`
- `renderToolResultMessage()` displays the MCP tool output.
- `classifyForCollapse.ts` determines if long output should be collapsed.
- Result is added to the conversation as a `tool_result` message.
- Claude continues reasoning with the tool result in context.

---

## Journey 4: Multi-Agent Task (Sub-Agent)

**Trace**: User asks complex task -> Claude spawns sub-agent -> agent works (foreground or background) -> notification -> result

### Step-by-Step Flow

#### Step 1: Claude Decides to Use AgentTool
- Model determines the task benefits from delegation.
- Returns `tool_use` with `Agent` tool: `{prompt, description, subagent_type?, model?, run_in_background?}`

#### Step 2: AgentTool Input Schema
- **File**: `src/tools/AgentTool/AgentTool.tsx` (L82-125)
- Base schema: `description` (3-5 words), `prompt`, `subagent_type?`, `model?` (sonnet/opus/haiku), `run_in_background?`
- Extended schema (multi-agent): `name?`, `team_name?`, `mode?`, `isolation?` (worktree/remote), `cwd?`

#### Step 3: Permission Check & Agent Selection
- **File**: `src/tools/AgentTool/AgentTool.tsx` (L239-340)
- `call()`:
  1. Checks team access if `team_name` provided
  2. If `team_name` + `name`: routes to `spawnTeammate()` (multi-agent path)
  3. Otherwise: selects agent definition:
     - Explicit `subagent_type` -> find in `activeAgents`
     - Fork gate on -> fork subagent path
     - Default -> `GENERAL_PURPOSE_AGENT`
  4. Validates agent has required MCP servers via `hasRequiredMcpServers()`

#### Step 4: Agent MCP Server Initialization
- **File**: `src/tools/AgentTool/runAgent.ts` (L95-199)
- `initializeAgentMcpServers()`:
  1. Agents can define their own MCP servers in frontmatter (additive to parent)
  2. String references: reuse parent's memoized connections
  3. Inline definitions: create new connections, tracked for cleanup
  4. Returns merged clients, agent-specific tools, and cleanup function

#### Step 5: Run Agent
- **File**: `src/tools/AgentTool/runAgent.ts`
- `runAgent()`:
  1. Creates sub-agent context via `createSubagentContext()` — own file state cache, own abort signal
  2. Builds system prompt: `getSystemPrompt()` + `enhanceSystemPromptWithEnvDetails()` + agent-specific instructions
  3. Assembles tool pool: inherits parent tools + agent-specific MCP tools
  4. Registers frontmatter hooks if defined
  5. Enters query loop via `query()` — same streaming API as main REPL but with agent context
  6. Agent processes tool calls autonomously (no user permission prompts in auto mode)

#### Step 6: Background Mode (if `run_in_background: true`)
- **File**: `src/tools/AgentTool/AgentTool.tsx` (L63-77)
- Background hint shown after `PROGRESS_THRESHOLD_MS` (2 seconds)
- Agent registers via `registerAsyncAgent()` in `LocalAgentTask`
- Progress updates sent via `updateAsyncAgentProgress()`
- User can continue working; notification appears when agent completes

#### Step 7: Result Collection
- Agent completes its query loop.
- `finalizeAgentTool()` extracts partial results, classifies handoff if needed.
- Returns `{status: 'completed', result, prompt}` or `{status: 'async_launched', agentId, outputFile}`.
- Result is rendered in parent conversation.
- Cleanup: disconnects agent-specific MCP servers, cleans up shell tasks, removes worktree if isolation was used.

---

## Journey 5: Session Resume

**Trace**: User runs `claude --resume` or `/resume` -> session list -> select -> restore messages -> continue conversation

### Step-by-Step Flow

#### Step 1: Resume Entry Points

**CLI flag path** (`claude --resume`):
- **File**: `src/main.tsx` (L90+)
- Commander option `--resume [id]` / `-r [id]` triggers resume flow.
- If session ID provided: loads directly. Otherwise: shows session picker.

**Slash command path** (`/resume` in REPL):
- **File**: `src/commands/resume/index.ts` (L1-12)
- Registered as command type `local-jsx`, name `resume`, alias `continue`.
- Loads `resume.tsx` component.

#### Step 2: Load Session Logs
- **File**: `src/commands/resume/resume.tsx` (L89-150)
- `ResumeCommand` component:
  1. Gets worktree paths via `getWorktreePaths(getOriginalCwd())`
  2. Loads logs via `loadSameRepoMessageLogs(paths)` — scoped to current repo
  3. Filters resumable sessions via `filterResumableSessions()` — excludes current session
  4. If no conversations found: shows "No conversations found to resume"

**Screen entry** (from CLI `--resume`):
- **File**: `src/screens/ResumeConversation.tsx` (L67-200)
- `ResumeConversation` component:
  1. Uses progressive loading: `loadSameRepoMessageLogsProgressive(worktreePaths)`
  2. Supports `loadMoreLogs()` for incremental loading
  3. Toggle: `showAllProjects` switches between same-repo and all-projects view
  4. Filters by PR number if `filterByPr` specified

#### Step 3: Session Picker UI
- **File**: `src/components/LogSelector.tsx`
- `LogSelector` renders interactive session list:
  - Session title (custom or auto-generated from first message)
  - Timestamp, message count, session ID preview
  - Keyboard navigation (up/down arrows, Enter to select)
  - Search/filter by text
  - Toggle all-projects view

#### Step 4: Session Selection & Cross-Project Check
- **File**: `src/commands/resume/resume.tsx` (L136-150)
- `handleSelect(log)`:
  1. Extracts session ID via `getSessionIdFromLog(log)` + `validateUuid()`
  2. Loads full log if lite: `loadFullLog(log)`
  3. `checkCrossProjectResume()` — detects if session is from a different directory:
     - Same repo worktree: can resume directly
     - Different project: copies command to clipboard, shows instruction to user

- **File**: `src/screens/ResumeConversation.tsx` (L178-199)
- `onSelect(log)`:
  1. `loadConversationForResume(log)` — deserializes JSONL transcript
  2. Checks coordinator mode compatibility
  3. Restores agent context if session had a main-thread agent

#### Step 5: Session Restoration
- **File**: `src/screens/ResumeConversation.tsx` (L190+)
- `loadConversationForResume()`:
  1. Reads session JSONL file from `~/.claude/projects/<hash>/<sessionId>.jsonl`
  2. Deserializes messages, content replacements, file history snapshots
  3. Detects session mode (coordinator, agent, standard)
  4. Returns `{messages, fileHistorySnapshots, contentReplacements, agentName?, agentColor?}`

#### Step 6: Switch to Resumed Session
- **File**: `src/screens/ResumeConversation.tsx` + `src/bootstrap/state.ts`
- After loading:
  1. `switchSession(newSessionId)` — updates global session ID
  2. `restoreCostStateForSession()` — restores cost tracking
  3. `adoptResumedSessionFile()` — points session file pointer to resumed log
  4. `restoreSessionMetadata()` — restores agent metadata, custom title
  5. `computeStandaloneAgentContext()` / `restoreAgentFromSession()` if agent session
  6. `restoreWorktreeForResume()` if session used worktree isolation
  7. `recordContentReplacement()` for any stored tool result content

#### Step 7: REPL Renders with Restored Messages
- **File**: `src/screens/ResumeConversation.tsx`
- Sets `resumeData` state with loaded messages.
- Transitions to `<REPL>` component with:
  - `initialMessages` — the restored conversation history
  - `fileHistorySnapshots` — file edit history for undo support
  - `contentReplacements` — stored tool result content
  - Agent definition if resuming an agent session
- User sees full conversation history and can continue typing.

---

## Cross-Journey Patterns

### Permission System
All tool invocations flow through a unified permission check:
1. Tool's `checkPermissions()` returns a `PermissionResult`
2. `PermissionRequest` component renders accept/reject UI
3. User can set "Always Allow" rules per tool/path pattern
4. Permission mode (ask/auto/plan) controls default behavior

### Streaming Architecture
All API calls use the same streaming pipeline:
1. `onQuery()` -> `onQueryImpl()` -> API client
2. `onQueryEvent()` processes each stream event (tokens, tool_use, tool_result)
3. `handleMessageFromStream()` updates message state
4. React re-renders incrementally as tokens arrive

### File State Cache
Read/Edit tools share a `fileStateCache`:
- `FileReadTool` populates cache on read (content + timestamp)
- `FileEditTool` validates cache before write (staleness detection)
- Prevents lost-update race conditions

### Session Storage
All sessions persist to `~/.claude/projects/<hash>/<sessionId>.jsonl`:
- Append-only JSONL format
- Content replacements stored separately for large tool results
- Session metadata (title, agent, mode) in companion files
