# Wave 2 Tool Verification — Batch 4 (Tools 31-40 + Registry Verification)

> Verified: 2026-04-01 | Source: `CC-Source/src/tools/` + `src/tools.ts` | Verifier: Claude Opus 4.6

---

## Verification Method

Each tool was verified by reading:
1. Main implementation file (`<ToolName>.ts` or `.tsx`)
2. Constants file (for registered `name` string)
3. Prompt file (for user-facing descriptions)
4. Cross-reference against `src/tools.ts` registry and existing analysis in `tool-system.md` / `00-stats.md`

---

## Tool 31: TaskListTool

| Field | Source Code Value |
|-------|-------------------|
| **Registered name** | `TaskList` (from `constants.ts`) |
| **Input schema** | `z.strictObject({})` — no parameters |
| **Output schema** | `{ tasks: [{ id, subject, status, owner?, blockedBy[] }] }` |
| **Category** | Tasks (TodoV2 system) |
| **Key behavior** | Lists all tasks from the task list (excluding internal tasks), filters out resolved blockedBy references. Returns formatted `#id [status] subject (owner) [blocked by ...]` lines. |
| **Permission model** | No custom `checkPermissions` — uses `buildTool` default (allow) |
| **isReadOnly()** | `true` |
| **isEnabled()** | `isTodoV2Enabled()` — only available when TodoV2 feature is active |
| **isConcurrencySafe()** | `true` |
| **shouldDefer** | `true` |

### Discrepancies with Existing Analysis
- **00-stats.md (#31)**: Lists as "Lists all tasks" — **ACCURATE**
- **tool-system.md**: Lists as "List all tasks" under Agent & Task Management — **ACCURATE**
- **Missing detail**: Existing analysis does not mention that input schema is empty (no parameters) or that it filters out `_internal` metadata tasks

---

## Tool 32: TaskOutputTool

| Field | Source Code Value |
|-------|-------------------|
| **Registered name** | `TaskOutput` (from `constants.ts`) |
| **Input schema** | `{ task_id: string, block: boolean (default true), timeout: number (0-600000, default 30000) }` |
| **Output schema** | `{ retrieval_status: 'success'|'timeout'|'not_ready', task: TaskOutput|null }` where TaskOutput includes `task_id, task_type, status, description, output, exitCode?, error?, prompt?, result?` |
| **Category** | Tasks |
| **Key behavior** | Retrieves output from running/completed background tasks (shell, agent, remote). Supports blocking wait (polls every 100ms up to timeout) and non-blocking check. Marked as DEPRECATED — prompt directs model to use `Read` on task output file path instead. |
| **Permission model** | No custom `checkPermissions` — uses default (allow) |
| **isReadOnly()** | `true` |
| **isEnabled()** | `"external" !== 'ant'` — always true for external users (disabled for ant-internal builds via dead-code elimination) |
| **isConcurrencySafe()** | Delegates to `isReadOnly()` — effectively `true` |
| **shouldDefer** | `true` |
| **aliases** | `['AgentOutputTool', 'BashOutputTool']` — backward compatibility |

### Discrepancies with Existing Analysis
- **00-stats.md (#32)**: Describes as "Emits structured output from tasks" — **INACCURATE**. It *retrieves/reads* output, not emits it.
- **tool-system.md**: "Read background task output" — **ACCURATE**
- **Missing detail**: Existing analysis does not mention deprecation status, aliases, or blocking/non-blocking modes

---

## Tool 33: TaskStopTool

| Field | Source Code Value |
|-------|-------------------|
| **Registered name** | `TaskStop` (from `prompt.ts`) |
| **Input schema** | `{ task_id?: string, shell_id?: string }` — shell_id is deprecated (KillShell compat) |
| **Output schema** | `{ message: string, task_id: string, task_type: string, command?: string }` |
| **Category** | Tasks |
| **Key behavior** | Stops a running background task by ID. Validates task exists and is in `running` status before stopping. Delegates to `stopTask()`. Supports legacy `shell_id` parameter for backward compatibility with deprecated KillShell tool. |
| **Permission model** | No custom `checkPermissions` — uses default (allow) |
| **isReadOnly()** | Not explicitly set — uses `buildTool` default (`false`) |
| **isEnabled()** | Not explicitly set — uses default (`true`, always enabled) |
| **isConcurrencySafe()** | `true` |
| **shouldDefer** | `true` |
| **aliases** | `['KillShell']` |

### Discrepancies with Existing Analysis
- **00-stats.md (#33)**: "Stops a running task" — **ACCURATE**
- **tool-system.md**: "Kill running tasks" — **ACCURATE** (though "kill" is legacy terminology)
- **Missing detail**: Existing analysis does not mention KillShell alias or shell_id backward compatibility

---

## Tool 34: TaskUpdateTool

| Field | Source Code Value |
|-------|-------------------|
| **Registered name** | `TaskUpdate` (from `constants.ts`) |
| **Input schema** | `{ taskId: string, subject?: string, description?: string, activeForm?: string, status?: TaskStatus|'deleted', addBlocks?: string[], addBlockedBy?: string[], owner?: string, metadata?: Record<string, unknown> }` |
| **Output schema** | `{ success: boolean, taskId: string, updatedFields: string[], error?: string, statusChange?: { from, to }, verificationNudgeNeeded?: boolean }` |
| **Category** | Tasks (TodoV2 system) |
| **Key behavior** | Updates task properties (subject, description, status, owner, blocks, metadata). Special handling for `status='deleted'` (deletes task file). Auto-sets owner on `in_progress` for swarm agents. Runs `TaskCompleted` hooks when marking completed. Sends mailbox notification on ownership change. Includes verification nudge logic (asks to spawn verification agent when 3+ tasks completed without a verification step). |
| **Permission model** | No custom `checkPermissions` — uses default (allow) |
| **isReadOnly()** | Not explicitly set — uses default (`false`) |
| **isEnabled()** | `isTodoV2Enabled()` |
| **isConcurrencySafe()** | `true` |
| **shouldDefer** | `true` |

### Discrepancies with Existing Analysis
- **00-stats.md (#34)**: "Updates task state" — **ACCURATE** but oversimplified
- **tool-system.md**: "Update task status" — **PARTIALLY ACCURATE**. It updates much more than status (subject, description, owner, blocks, metadata, deletion).
- **Missing detail**: Verification nudge, mailbox notifications, hook execution, and delete support are not documented

---

## Tool 35: TeamCreateTool

| Field | Source Code Value |
|-------|-------------------|
| **Registered name** | `TeamCreate` (from `constants.ts`) |
| **Input schema** | `{ team_name: string, description?: string, agent_type?: string }` |
| **Output schema** | `{ team_name: string, team_file_path: string, lead_agent_id: string }` |
| **Category** | Swarm |
| **Key behavior** | Creates a new agent swarm team. Generates unique team name if collision detected. Creates team file on disk, resets task list for the team, updates AppState with team context. Assigns team lead color, registers for session cleanup. Restricts to one team per leader. Loaded via lazy `require()` to break circular dependency. |
| **Permission model** | No custom `checkPermissions` — uses default (allow) |
| **isReadOnly()** | Not explicitly set — uses default (`false`) |
| **isEnabled()** | `isAgentSwarmsEnabled()` |
| **isConcurrencySafe()** | Not explicitly set — uses default (`false`) |
| **shouldDefer** | `true` |

### Discrepancies with Existing Analysis
- **00-stats.md (#35)**: "Creates an agent team (swarm)" — **ACCURATE**
- **tool-system.md**: "Create agent teams with file-based mailbox" — **ACCURATE**
- **Missing detail**: Auto-deduplication of team names, one-team-per-leader constraint, and session cleanup registration not documented

---

## Tool 36: TeamDeleteTool

| Field | Source Code Value |
|-------|-------------------|
| **Registered name** | `TeamDelete` (from `constants.ts`) |
| **Input schema** | `z.strictObject({})` — no parameters |
| **Output schema** | `{ success: boolean, message: string, team_name?: string }` |
| **Category** | Swarm |
| **Key behavior** | Disbands the current team. Checks for active non-lead members before proceeding (refuses if active members exist). Cleans up team directories, worktrees, color assignments, and leader team name. Clears team context and inbox from AppState. |
| **Permission model** | No custom `checkPermissions` — uses default (allow) |
| **isReadOnly()** | Not explicitly set — uses default (`false`) |
| **isEnabled()** | `isAgentSwarmsEnabled()` |
| **isConcurrencySafe()** | Not explicitly set — uses default (`false`) |
| **shouldDefer** | `true` |

### Discrepancies with Existing Analysis
- **00-stats.md (#36)**: "Dissolves an agent team" — **ACCURATE**
- **tool-system.md**: "Tear down agent teams" — **ACCURATE**
- **Missing detail**: Active member check (refuses deletion if active members exist) not documented

---

## Tool 37: TodoWriteTool

| Field | Source Code Value |
|-------|-------------------|
| **Registered name** | `TodoWrite` (from `constants.ts`) |
| **Input schema** | `{ todos: TodoListSchema[] }` — array of todo items with content/status fields |
| **Output schema** | `{ oldTodos: TodoListSchema[], newTodos: TodoListSchema[], verificationNudgeNeeded?: boolean }` |
| **Category** | Tasks/Planning |
| **Key behavior** | Writes/updates the session task checklist (TodoV1). Stores todos in AppState keyed by agentId or sessionId. Auto-clears list when all items are completed. Includes verification nudge (spawn verification agent when 3+ items completed without verification step). Mutually exclusive with TodoV2 (TaskCreate/Update/List/Get). |
| **Permission model** | Explicit `checkPermissions` that always returns `{ behavior: 'allow' }` |
| **isReadOnly()** | Not explicitly set — uses default (`false`) |
| **isEnabled()** | `!isTodoV2Enabled()` — only active when TodoV2 is OFF |
| **isConcurrencySafe()** | Not explicitly set — uses default (`false`) |
| **shouldDefer** | `true` |
| **strict** | `true` (strict JSON schema validation) |

### Discrepancies with Existing Analysis
- **00-stats.md (#38)**: "Writes structured todo lists" — **ACCURATE**
- **tool-system.md**: "Write to todo panel" — **ACCURATE**
- **Missing detail**: Mutual exclusivity with TodoV2 system, verification nudge, and auto-clear behavior not documented. The analysis places it under "Planning & Mode" which is reasonable.

---

## Tool 38: ToolSearchTool

| Field | Source Code Value |
|-------|-------------------|
| **Registered name** | `ToolSearch` (from `constants.ts`) |
| **Input schema** | `{ query: string, max_results?: number (default 5) }` |
| **Output schema** | `{ matches: string[], query: string, total_deferred_tools: number, pending_mcp_servers?: string[] }` |
| **Category** | Meta |
| **Key behavior** | Searches deferred tool schemas by keyword or direct selection. Supports: (1) `select:Name1,Name2` for direct fetch, (2) `mcp__prefix` for MCP prefix matching, (3) keyword search scoring tool names, searchHints, and descriptions. Returns `tool_reference` blocks that make matched tools callable. Caches tool descriptions. Reports pending MCP servers when no matches found. |
| **Permission model** | No custom `checkPermissions` — uses default (allow) |
| **isReadOnly()** | `true` |
| **isEnabled()** | `isToolSearchEnabledOptimistic()` — based on total tool count threshold |
| **isConcurrencySafe()** | `true` |
| **shouldDefer** | Not set — never deferred (explicitly excluded in `isDeferredTool()`) |

### Discrepancies with Existing Analysis
- **00-stats.md (#39)**: "Searches for available tools by description" — **PARTIALLY ACCURATE**. It searches by name, searchHint, and description (not just description).
- **tool-system.md**: "Search deferred tool schemas by keyword" — **ACCURATE**
- **Missing detail**: `select:` direct selection mode, `+required` term syntax, `tool_reference` return format, and MCP prefix matching not documented

---

## Tool 39: WebFetchTool

| Field | Source Code Value |
|-------|-------------------|
| **Registered name** | `WebFetch` (from `prompt.ts`) |
| **Input schema** | `{ url: string (URL format), prompt: string }` |
| **Output schema** | `{ bytes: number, code: number, codeText: string, result: string, durationMs: number, url: string }` |
| **Category** | Web |
| **Key behavior** | Fetches URL content, converts HTML to markdown, then processes with a secondary AI model (Haiku) using the provided prompt. Handles redirects (returns redirect info for cross-host redirects). Pre-approved hosts bypass prompt processing for small markdown. Binary content (PDFs) persisted to disk. Has 15-minute cache. Permission checks use domain-based rules. |
| **Permission model** | Custom `checkPermissions`: checks preapproved hosts list, then domain-based allow/deny/ask rules. Preapproved hosts auto-allowed. |
| **isReadOnly()** | `true` |
| **isEnabled()** | Not explicitly set — uses default (`true`, always enabled) |
| **isConcurrencySafe()** | `true` |
| **shouldDefer** | `true` |
| **validateInput** | Validates URL format |

### Discrepancies with Existing Analysis
- **00-stats.md (#40)**: "Fetches and extracts content from URLs" — **ACCURATE**
- **tool-system.md**: "Fetch and parse web pages" — **ACCURATE**
- **Missing detail**: Secondary model processing, preapproved host list, domain-based permission rules, redirect handling, and binary content persistence not documented

---

## Tool 40: WebSearchTool

| Field | Source Code Value |
|-------|-------------------|
| **Registered name** | `WebSearch` (from `prompt.ts`) |
| **Input schema** | `{ query: string (min 2 chars), allowed_domains?: string[], blocked_domains?: string[] }` |
| **Output schema** | `{ query: string, results: (SearchResult|string)[], durationSeconds: number }` where SearchResult has `{ tool_use_id, content: [{ title, url }] }` |
| **Category** | Web |
| **Key behavior** | Performs web search using Anthropic's server-side `web_search_20250305` tool via a streaming API call. Sends query to a secondary model with the web_search tool enabled (max 8 searches per call). Can optionally use Haiku for speed (feature-gated). Streams progress events (query updates, result counts). Validates that allowed_domains and blocked_domains are not both specified. |
| **Permission model** | Custom `checkPermissions` returns `{ behavior: 'passthrough' }` — defers to general permission system |
| **isReadOnly()** | `true` |
| **isEnabled()** | Provider-based: enabled for `firstParty` and `foundry` always; for `vertex` only with Claude 4.0+ models |
| **isConcurrencySafe()** | `true` |
| **shouldDefer** | `true` |
| **validateInput** | Checks non-empty query, validates allowed/blocked domain mutual exclusivity |

### Discrepancies with Existing Analysis
- **00-stats.md (#41)**: "Performs web searches" — **ACCURATE** but oversimplified
- **tool-system.md**: "Web search via API" — **ACCURATE**
- **Missing detail**: Server-side `web_search_20250305` tool usage, streaming progress, domain filtering, provider-based enablement, and the Haiku fast-path are not documented

---

## Tools Registry Verification (`src/tools.ts`)

### Complete `getAllBaseTools()` Registration Order

The following tools are registered in `getAllBaseTools()` in this exact order:

1. AgentTool
2. TaskOutputTool
3. BashTool
4. GlobTool, GrepTool (conditionally, when `!hasEmbeddedSearchTools()`)
5. ExitPlanModeV2Tool
6. FileReadTool
7. FileEditTool
8. FileWriteTool
9. NotebookEditTool
10. WebFetchTool
11. TodoWriteTool
12. WebSearchTool
13. TaskStopTool
14. AskUserQuestionTool
15. SkillTool
16. EnterPlanModeTool
17. ConfigTool (ant-only)
18. TungstenTool (ant-only)
19. SuggestBackgroundPRTool (ant-only)
20. WebBrowserTool (feature: WEB_BROWSER_TOOL)
21. TaskCreateTool, TaskGetTool, TaskUpdateTool, TaskListTool (when `isTodoV2Enabled()`)
22. OverflowTestTool (feature: OVERFLOW_TEST_TOOL)
23. CtxInspectTool (feature: CONTEXT_COLLAPSE)
24. TerminalCaptureTool (feature: TERMINAL_PANEL)
25. LSPTool (env: ENABLE_LSP_TOOL)
26. EnterWorktreeTool, ExitWorktreeTool (when `isWorktreeModeEnabled()`)
27. SendMessageTool (always, via lazy require)
28. ListPeersTool (feature: UDS_INBOX)
29. TeamCreateTool, TeamDeleteTool (when `isAgentSwarmsEnabled()`)
30. VerifyPlanExecutionTool (env: CLAUDE_CODE_VERIFY_PLAN)
31. REPLTool (ant-only + feature: PROACTIVE/KAIROS)
32. WorkflowTool (feature: WORKFLOW_SCRIPTS)
33. SleepTool (feature: PROACTIVE/KAIROS)
34. CronCreateTool, CronDeleteTool, CronListTool (feature: AGENT_TRIGGERS)
35. RemoteTriggerTool (feature: AGENT_TRIGGERS_REMOTE)
36. MonitorTool (feature: MONITOR_TOOL)
37. BriefTool
38. SendUserFileTool (feature: KAIROS)
39. PushNotificationTool (feature: KAIROS/KAIROS_PUSH_NOTIFICATION)
40. SubscribePRTool (feature: KAIROS_GITHUB_WEBHOOKS)
41. PowerShellTool (when `isPowerShellToolEnabled()`)
42. SnipTool (feature: HISTORY_SNIP)
43. TestingPermissionTool (test env only)
44. ListMcpResourcesTool
45. ReadMcpResourceTool
46. ToolSearchTool (when `isToolSearchEnabledOptimistic()`)

### Tools Referenced in `tools.ts` but NOT in `src/tools/` Directories

The following 14 tools are referenced via `require()` in `tools.ts` but their source directories are not present in the available source tree. These are likely feature-gated tools stripped from the public/external build, or exist in a separate package:

| Tool | Load Condition | Referenced Path |
|------|---------------|-----------------|
| **SuggestBackgroundPRTool** | `USER_TYPE === 'ant'` | `tools/SuggestBackgroundPRTool/` |
| **TungstenTool** | `USER_TYPE === 'ant'` | `tools/TungstenTool/` (imported statically) |
| **WebBrowserTool** | `feature('WEB_BROWSER_TOOL')` | `tools/WebBrowserTool/` |
| **OverflowTestTool** | `feature('OVERFLOW_TEST_TOOL')` | `tools/OverflowTestTool/` |
| **CtxInspectTool** | `feature('CONTEXT_COLLAPSE')` | `tools/CtxInspectTool/` |
| **TerminalCaptureTool** | `feature('TERMINAL_PANEL')` | `tools/TerminalCaptureTool/` |
| **SnipTool** | `feature('HISTORY_SNIP')` | `tools/SnipTool/` |
| **ListPeersTool** | `feature('UDS_INBOX')` | `tools/ListPeersTool/` |
| **WorkflowTool** | `feature('WORKFLOW_SCRIPTS')` | `tools/WorkflowTool/` |
| **MonitorTool** | `feature('MONITOR_TOOL')` | `tools/MonitorTool/` |
| **SendUserFileTool** | `feature('KAIROS')` | `tools/SendUserFileTool/` |
| **PushNotificationTool** | `feature('KAIROS')\|feature('KAIROS_PUSH_NOTIFICATION')` | `tools/PushNotificationTool/` |
| **SubscribePRTool** | `feature('KAIROS_GITHUB_WEBHOOKS')` | `tools/SubscribePRTool/` |
| **VerifyPlanExecutionTool** | `CLAUDE_CODE_VERIFY_PLAN=true` | `tools/VerifyPlanExecutionTool/` |

**Note**: `ExitPlanModeV2Tool` is imported from `tools/ExitPlanModeTool/ExitPlanModeV2Tool.js` (inside the `ExitPlanModeTool/` directory), so it is NOT missing — it shares a directory with the original ExitPlanModeTool.

### Tools in Directories but NOT in `getAllBaseTools()` Registry

| Directory | Reason Not Registered Directly |
|-----------|-------------------------------|
| `tools/MCPTool/` | Dynamic wrapper; instantiated per MCP server, not statically registered |
| `tools/McpAuthTool/` | Created dynamically when MCP auth is needed |
| `tools/SyntheticOutputTool/` | Only name constant is imported; never added to tools array (used in `specialTools` filter set) |
| `tools/TaskGetTool/` | Registered conditionally via `isTodoV2Enabled()` (included in registry above) |
| `tools/TaskCreateTool/` | Registered conditionally via `isTodoV2Enabled()` (included in registry above) |

---

## Existing Analysis Accuracy Summary

### `00-stats.md` Tool Catalog (Tools 31-41)

| # | Tool | Listed Description | Accuracy |
|---|------|--------------------|----------|
| 31 | TaskListTool | "Lists all tasks" | ACCURATE |
| 32 | TaskOutputTool | "Emits structured output from tasks" | INACCURATE — it *reads/retrieves* output, not emits |
| 33 | TaskStopTool | "Stops a running task" | ACCURATE |
| 34 | TaskUpdateTool | "Updates task state" | ACCURATE (simplified) |
| 35 | TeamCreateTool | "Creates an agent team (swarm)" | ACCURATE |
| 36 | TeamDeleteTool | "Dissolves an agent team" | ACCURATE |
| 37 | TestingPermissionTool | "Validates permission logic in tests" | NOT VERIFIED (test-only) |
| 38 | TodoWriteTool | "Writes structured todo lists" | ACCURATE |
| 39 | ToolSearchTool | "Searches for available tools by description" | PARTIALLY ACCURATE (searches name + hint + description) |
| 40 | WebFetchTool | "Fetches and extracts content from URLs" | ACCURATE |
| 41 | WebSearchTool | "Performs web searches" | ACCURATE |

### `tool-system.md` Tool Catalog

| Tool | Listed Description | Accuracy |
|------|--------------------|----------|
| TaskListTool | "List all tasks" | ACCURATE |
| TaskOutputTool | "Read background task output" | ACCURATE |
| TaskStopTool | "Kill running tasks" | ACCURATE |
| TaskUpdateTool | "Update task status" | PARTIALLY ACCURATE (updates much more than status) |
| TeamCreateTool | "Create agent teams with file-based mailbox" | ACCURATE |
| TeamDeleteTool | "Tear down agent teams" | ACCURATE |
| TodoWriteTool | "Write to todo panel" | ACCURATE |
| WebFetchTool | "Fetch and parse web pages" | ACCURATE |
| WebSearchTool | "Web search via API" | ACCURATE |
| ToolSearchTool | "Search deferred tool schemas by keyword" | ACCURATE |

### `00-stats.md` Conditional Tools Section

| Listed Tool | Accuracy |
|-------------|----------|
| REPLTool (ant-only) | ACCURATE |
| SleepTool (PROACTIVE/KAIROS) | ACCURATE |
| MonitorTool (MONITOR_TOOL) | ACCURATE |
| SendUserFileTool (KAIROS) | ACCURATE |
| PushNotificationTool (KAIROS) | ACCURATE |
| SubscribePRTool (KAIROS_GITHUB_WEBHOOKS) | ACCURATE |
| VerifyPlanExecutionTool (CLAUDE_CODE_VERIFY_PLAN) | ACCURATE |

**Missing from conditional tools list** (present in `tools.ts` but not listed in `00-stats.md`):
- SuggestBackgroundPRTool (ant-only)
- TungstenTool (ant-only)
- WebBrowserTool (feature: WEB_BROWSER_TOOL)
- OverflowTestTool (feature: OVERFLOW_TEST_TOOL)
- CtxInspectTool (feature: CONTEXT_COLLAPSE)
- TerminalCaptureTool (feature: TERMINAL_PANEL)
- SnipTool (feature: HISTORY_SNIP)
- ListPeersTool (feature: UDS_INBOX)
- WorkflowTool (feature: WORKFLOW_SCRIPTS)

**Total conditional tools**: 16 (not 7 as listed in stats; though 14 of these lack source in our tree)

### `tool-system.md` Category Accuracy

The category groupings are well-organized. One correction:
- TodoWriteTool is listed under "Planning & Mode (3 tools)" — this is reasonable since it serves planning purposes, but functionally it is a task-tracking tool in the same family as TaskCreate/Update/List/Get.

---

## Key Findings

1. **Tool count discrepancy**: `00-stats.md` lists "52 tools" with 41 core + 7 conditional. The actual `tools.ts` registry contains up to **46+ tool entries** (including conditionals), plus MCPTool (dynamic) and SyntheticOutputTool (internal). With all 16 conditional tools counted, the total is closer to **57+ tool slots** in the registry.

2. **14 phantom tool directories**: Referenced in `tools.ts` via `require()` but directories are not present in the available source tree. These are feature-gated tools likely stripped during public build or bundling.

3. **TodoV1 vs TodoV2 mutual exclusivity**: `TodoWriteTool.isEnabled = !isTodoV2Enabled()` while TaskCreate/Get/Update/List have `isEnabled = isTodoV2Enabled()`. The existing analysis does not clearly document this mutual exclusivity.

4. **TaskOutputTool deprecation**: The tool is explicitly marked deprecated in its prompt, directing the model to use `Read` on the task output file path instead. This deprecation is not mentioned in existing analysis.

5. **Verification nudge pattern**: Both `TodoWriteTool` and `TaskUpdateTool` include logic to nudge the model to spawn a verification agent when 3+ tasks are completed without a verification step. This cross-tool behavioral pattern is undocumented.

6. **WebSearchTool provider gating**: Not a simple "always available" tool — requires firstParty, foundry, or vertex (Claude 4.0+) provider. This platform constraint is undocumented.
