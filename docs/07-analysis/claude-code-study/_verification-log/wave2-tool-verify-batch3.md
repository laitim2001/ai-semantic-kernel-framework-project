# Wave 2 Tool Verification — Batch 3 (Tools 21-30)

> Verified: 2026-04-01 | Source: `CC-Source/src/tools/` | Verifier: Claude Opus 4.6
> Scope: ReadMcpResourceTool, RemoteTriggerTool, REPLTool, ScheduleCronTool, SendMessageTool, SkillTool, SleepTool, SyntheticOutputTool, TaskCreateTool, TaskGetTool

---

## Verification Summary

| # | Tool Name | Existing Analysis Accuracy | Discrepancies Found |
|---|-----------|---------------------------|---------------------|
| 21 | ReadMcpResourceTool | HIGH | Minor: description imprecise |
| 22 | RemoteTriggerTool | MEDIUM | Name/description corrections needed |
| 23 | REPLTool | HIGH | None significant |
| 24 | ScheduleCronTool (x3) | MEDIUM | Listed as 1 tool in tool-system.md, actually 3 separate tools |
| 25 | SendMessageTool | HIGH | Category confirmed; complexity understated |
| 26 | SkillTool | HIGH | None significant |
| 27 | SleepTool | LOW-CONFIDENCE | Source file missing from dump; only prompt.ts available |
| 28 | SyntheticOutputTool | MEDIUM | Description needs correction (not "synthetic output" — structured JSON output) |
| 29 | TaskCreateTool | HIGH | Minor: description says "background tasks" but it's TodoV2 tasks |
| 30 | TaskGetTool | HIGH | None significant |

**Overall Batch Accuracy**: ~7.5/10 — Most tools described correctly at high level. Main issues: ScheduleCronTool is actually 3 tools, SyntheticOutputTool description misleading, RemoteTriggerTool description imprecise.

---

## Tool-by-Tool Verification

### 21. ReadMcpResourceTool

| Field | Source Code Value |
|-------|-------------------|
| **Actual tool name** | `'ReadMcpResourceTool'` |
| **Input schema** | `{ server: string, uri: string }` |
| **Category** | MCP |
| **Key behavior** | Reads a specific resource from a connected MCP server by URI. Sends `resources/read` request to the named MCP server's client, intercepts binary blob responses (decodes base64, persists to disk, returns file path instead of raw blob), and returns text content items. |
| **Permission model** | Uses `buildTool` defaults — `checkPermissions()` returns `{ behavior: 'allow' }` |
| **isReadOnly()** | `true` |
| **isEnabled()** | Default (`true`) — always enabled when registered |
| **shouldDefer** | `true` |
| **isConcurrencySafe()** | `true` |

**Existing Analysis vs Source**:
- `tool-system.md` line 174: "Read MCP server resources" — **Correct** but understates the binary blob persistence behavior (base64 decode to disk).
- `00-stats.md` line 105: "Reads content from MCP server resources" — **Correct**.
- Category listed as "MCP" — **Correct**.

**Discrepancies**: None significant. Analysis is accurate.

---

### 22. RemoteTriggerTool

| Field | Source Code Value |
|-------|-------------------|
| **Actual tool name** | `REMOTE_TRIGGER_TOOL_NAME` = `'RemoteTrigger'` |
| **Input schema** | `{ action: enum('list','get','create','update','run'), trigger_id?: string (regex /^[\w-]+$/), body?: Record<string, unknown> }` |
| **Category** | Remote / API |
| **Key behavior** | Manages scheduled remote Claude Code agents (triggers) via the claude.ai CCR API. Supports CRUD operations (list/get/create/update) plus manual `run`. Authenticates with OAuth tokens (auto-refreshed), sends HTTP requests to `/v1/code/triggers` endpoint with proper headers including `anthropic-beta: ccr-triggers-2026-01-30`. |
| **Permission model** | Uses `buildTool` defaults — no custom `checkPermissions()` |
| **isReadOnly()** | `true` when `action === 'list'` or `action === 'get'`; `false` otherwise |
| **isEnabled()** | `getFeatureValue_CACHED_MAY_BE_STALE('tengu_surreal_dali', false) && isPolicyAllowed('allow_remote_sessions')` |
| **shouldDefer** | `true` |
| **isConcurrencySafe()** | `true` |

**Existing Analysis vs Source**:
- `tool-system.md` line 189: "Launch remote CCR agents" — **Imprecise**. The tool manages (CRUD + run) remote triggers/scheduled agents, not just "launches" them.
- `00-stats.md` line 106: "Triggers remote agent execution" — **Partially correct**. `run` triggers execution, but the tool also does list/get/create/update.
- Category listed as "Remote" in stats — **Correct** but could also be "API".
- Feature flag: stats says nothing about the flag; source uses GrowthBook `tengu_surreal_dali` + policy `allow_remote_sessions`.

**Discrepancies**:
1. Description should say "Manages scheduled remote agent triggers (CRUD + run)" not just "Launch/Trigger".
2. `isReadOnly()` is conditional on action, not mentioned in existing analysis.

---

### 23. REPLTool

| Field | Source Code Value |
|-------|-------------------|
| **Actual tool name** | `'REPL'` (from `REPL_TOOL_NAME` in constants.ts) |
| **Input schema** | Not directly visible — the directory only contains `constants.ts` and `primitiveTools.ts`. The actual tool implementation is loaded via `require()` in `tools.ts`. |
| **Category** | Shell / Meta |
| **Key behavior** | A VM-based REPL that wraps primitive tools (FileRead, FileWrite, FileEdit, Glob, Grep, Bash, NotebookEdit, AgentTool). When REPL mode is enabled, these 8 tools are hidden from direct model use and only accessible through the REPL VM context, forcing the model to use batch operations. |
| **Permission model** | Not directly visible in available source |
| **isReadOnly()** | Not directly visible in available source |
| **isEnabled()** | Gated by `isReplModeEnabled()`: returns true when `USER_TYPE === 'ant'` AND `CLAUDE_CODE_ENTRYPOINT === 'cli'`, unless `CLAUDE_CODE_REPL` is falsy. Also force-enabled by `CLAUDE_REPL_MODE=1`. |
| **Registration** | Conditionally loaded: `process.env.USER_TYPE === 'ant' && REPLTool ? [REPLTool] : []` |

**Existing Analysis vs Source**:
- `tool-system.md` line 134: "VM-based REPL wrapping Bash/Read/Edit (ant-only)" — **Correct** but incomplete; wraps 8 tools total (FileRead, FileWrite, FileEdit, Glob, Grep, Bash, NotebookEdit, AgentTool).
- `00-stats.md` line 131: "Interactive REPL for Anthropic internal use" — **Correct** at high level.
- Condition listed as `USER_TYPE=ant` — **Correct** but the full logic is more nuanced (also checks CLAUDE_CODE_ENTRYPOINT, CLAUDE_CODE_REPL, CLAUDE_REPL_MODE).

**Discrepancies**:
1. `tool-system.md` says "wrapping Bash/Read/Edit" — should list all 8 primitive tools.
2. The actual `.ts` implementation file (SleepTool pattern — compiled from elsewhere) is not in our source dump; only `constants.ts` and `primitiveTools.ts` are available.

---

### 24. ScheduleCronTool (3 tools: CronCreate, CronDelete, CronList)

**IMPORTANT**: The `ScheduleCronTool/` directory contains **3 separate tools**, not 1. The existing `tool-system.md` line 189 lists this as one tool "ScheduleCronTool — Cron scheduling (Create/Delete/List)" which is misleading.

#### 24a. CronCreateTool

| Field | Source Code Value |
|-------|-------------------|
| **Actual tool name** | `'CronCreate'` |
| **Input schema** | `{ cron: string, prompt: string, recurring?: boolean, durable?: boolean }` (strictObject) |
| **Category** | Scheduling / Tasks |
| **Key behavior** | Schedules a prompt to run at a future time — either recurring on a cron schedule or once (one-shot). Supports durable mode (persists to `.claude/scheduled_tasks.json`) and session-only mode (in-memory). Validates cron expressions, enforces max 50 jobs, prevents durable crons for teammates. Enables the scheduler tick loop after creation. |
| **Permission model** | Uses `buildTool` defaults |
| **isReadOnly()** | Default (`false`) |
| **isEnabled()** | `isKairosCronEnabled()` — requires `feature('AGENT_TRIGGERS')` build-time flag + `tengu_kairos_cron` GrowthBook flag (default true) + not `CLAUDE_CODE_DISABLE_CRON` |
| **shouldDefer** | `true` |
| **validateInput()** | Yes — validates cron expression syntax, checks next-run feasibility, enforces MAX_JOBS (50), blocks durable crons for teammates |

#### 24b. CronDeleteTool

| Field | Source Code Value |
|-------|-------------------|
| **Actual tool name** | `'CronDelete'` |
| **Input schema** | `{ id: string }` (strictObject) |
| **Category** | Scheduling / Tasks |
| **Key behavior** | Cancels a scheduled cron job by ID. Removes from either durable file or session store. Validates job exists and enforces teammate ownership (teammates can only delete their own crons). |
| **Permission model** | Uses `buildTool` defaults |
| **isReadOnly()** | Default (`false`) |
| **isEnabled()** | `isKairosCronEnabled()` |
| **shouldDefer** | `true` |
| **validateInput()** | Yes — verifies job exists, enforces teammate ownership |

#### 24c. CronListTool

| Field | Source Code Value |
|-------|-------------------|
| **Actual tool name** | `'CronList'` |
| **Input schema** | `{}` (empty strictObject) |
| **Category** | Scheduling / Tasks |
| **Key behavior** | Lists all scheduled cron jobs (both durable and session-only). Teammates only see their own crons; team lead sees all. Returns job details including human-readable schedule. |
| **Permission model** | Uses `buildTool` defaults |
| **isReadOnly()** | `true` |
| **isEnabled()** | `isKairosCronEnabled()` |
| **shouldDefer** | `true` |
| **isConcurrencySafe()** | `true` |

**Existing Analysis vs Source**:
- `tool-system.md` line 189: "ScheduleCronTool — Cron scheduling (Create/Delete/List)" — **Misleading**. There is no single "ScheduleCronTool". The directory contains 3 independent tools: CronCreate, CronDelete, CronList.
- `00-stats.md` lines 107-109: Correctly lists all 3 as separate tools (CronCreateTool, CronDeleteTool, CronListTool) — **Accurate**.
- Feature flag: stats line 132 mentions `feature('PROACTIVE') | feature('KAIROS')` for SleepTool. For cron tools, it's actually `feature('AGENT_TRIGGERS')` + GrowthBook `tengu_kairos_cron`.

**Discrepancies**:
1. `tool-system.md` merges 3 tools into 1 "ScheduleCronTool" — should list them separately.
2. `00-stats.md` correctly separates them — no discrepancy there.
3. Durable/session-only distinction and teammate scoping not mentioned in existing analysis.

---

### 25. SendMessageTool

| Field | Source Code Value |
|-------|-------------------|
| **Actual tool name** | `'SendMessage'` |
| **Input schema** | `{ to: string, summary?: string, message: string | StructuredMessage }` where StructuredMessage is a discriminated union of `shutdown_request`, `shutdown_response`, `plan_approval_response` |
| **Category** | Swarm / Agent Communication |
| **Key behavior** | Routes messages between agents/teammates in a swarm. Supports: (1) plain text messages to named teammates or broadcast via `*`, (2) structured shutdown request/response protocol, (3) plan approval/rejection protocol, (4) UDS socket messaging to local peers, (5) bridge messaging to Remote Control peers, (6) auto-resume of stopped agents when messaged. Writes messages to file-based mailboxes. |
| **Permission model** | Custom `checkPermissions()` — requires explicit user consent for cross-machine bridge messages (`safetyCheck` type, not classifier-approvable) |
| **isReadOnly()** | `true` when `message` is a plain string; `false` for structured messages |
| **isEnabled()** | `isAgentSwarmsEnabled()` |
| **shouldDefer** | `true` |
| **validateInput()** | Extensive — validates `to` not empty, rejects `@` in names, validates bridge/UDS connectivity, requires summary for plain text, blocks structured messages to broadcast, enforces shutdown_response target is team-lead, requires reason for shutdown rejection |

**Existing Analysis vs Source**:
- `tool-system.md` line 140: "Route messages between agents/teammates" — **Correct** but heavily understated. The tool handles 6+ distinct message routing paths.
- `00-stats.md` line 110: "Sends messages between agents in a swarm" — **Correct** at high level.
- Category "Swarm" — **Correct**.

**Discrepancies**:
1. Existing analysis does not capture the complexity: shutdown protocol, plan approval, bridge messaging, UDS sockets, auto-resume of stopped agents.
2. `isReadOnly()` being conditional on message type is not mentioned.
3. The safety check for cross-machine bridge messages is a significant security feature not documented.

---

### 26. SkillTool

| Field | Source Code Value |
|-------|-------------------|
| **Actual tool name** | `'Skill'` |
| **Input schema** | `{ skill: string, args?: string }` |
| **Category** | Skills / Meta |
| **Key behavior** | Invokes registered slash-command skills by name. Skills can be executed either **inline** (injected into current conversation as system prompt with optional tool/model constraints) or **forked** (run in an isolated sub-agent with its own token budget via `runAgent()`). Resolves commands from local registry, MCP skills, and experimental remote skills. Supports permission deny rules matching skill names and prefix patterns (e.g., `review:*`). |
| **Permission model** | Custom `checkPermissions()` — checks deny rules by skill name/prefix matching, auto-allows built-in/official/bundled skills, asks user for third-party skills |
| **isReadOnly()** | Default (`false`) |
| **isEnabled()** | Default (`true`) — always enabled |
| **shouldDefer** | Not set (default `false`) |
| **validateInput()** | Yes — validates skill name not empty, strips leading `/`, checks command exists, verifies not `disableModelInvocation`, ensures type is `prompt` |

**Existing Analysis vs Source**:
- `tool-system.md` line 180: "Invoke skills (markdown-based commands)" — **Correct** but incomplete. Does not mention forked execution, remote skills, or permission rule matching.
- `00-stats.md` line 111: "Executes registered slash-command skills" — **Correct**.

**Discrepancies**:
1. Analysis does not mention the inline vs forked execution model (a significant architectural feature).
2. The custom permission model with deny-rule matching is not documented.
3. Remote skill discovery (experimental, ant-only) not mentioned.

---

### 27. SleepTool

| Field | Source Code Value |
|-------|-------------------|
| **Actual tool name** | `'Sleep'` (from `SLEEP_TOOL_NAME` in prompt.ts) |
| **Input schema** | Not available — `SleepTool.ts` is not present in source dump (only `prompt.ts` exists). Tool is loaded via `require('./tools/SleepTool/SleepTool.js')` in tools.ts. |
| **Category** | Agent / Proactive |
| **Key behavior** | (From prompt.ts) Waits for a specified duration. User can interrupt. Preferred over `Bash(sleep ...)` because it doesn't hold a shell process. Can be called concurrently with other tools. Used when agent has nothing to do or is waiting. Responds to periodic `<tick>` check-in prompts. |
| **Permission model** | Unknown — source not available |
| **isReadOnly()** | Unknown — source not available |
| **isEnabled()** | Gated at registration level: `feature('PROACTIVE') || feature('KAIROS')` (from tools.ts line 26) |
| **shouldDefer** | Unknown — source not available |

**Existing Analysis vs Source**:
- `tool-system.md` line 190: "Sleep for proactive agents" — **Correct** based on available evidence.
- `00-stats.md` line 132: "Pauses agent execution", condition `feature('PROACTIVE') | feature('KAIROS')` — **Correct**.

**Discrepancies**: None detectable, but **LOW CONFIDENCE** due to missing implementation file. The `.ts` source for SleepTool is not in the CC-Source dump — likely compiled from a different build path or excluded.

---

### 28. SyntheticOutputTool

| Field | Source Code Value |
|-------|-------------------|
| **Actual tool name** | `'StructuredOutput'` (from `SYNTHETIC_OUTPUT_TOOL_NAME`) |
| **Input schema** | `z.object({}).passthrough()` — accepts any JSON object (schema provided dynamically via `createSyntheticOutputTool()`) |
| **Category** | SDK / Internal |
| **Key behavior** | Returns structured JSON output in a requested format for non-interactive SDK/CLI sessions. The base tool accepts any input and returns it as `structured_output`. The `createSyntheticOutputTool()` factory creates schema-validated variants using Ajv — validates input against a provided JSON Schema and throws on mismatch. Uses WeakMap caching for schema reuse efficiency. |
| **Permission model** | Always allows — `checkPermissions()` returns `{ behavior: 'allow' }` |
| **isReadOnly()** | `true` |
| **isEnabled()** | Always `true` once created (creation gated by `isSyntheticOutputToolEnabled()` which requires `isNonInteractiveSession`) |
| **isConcurrencySafe()** | `true` |
| **shouldDefer** | Not set (default `false`) |

**Existing Analysis vs Source**:
- `tool-system.md`: Not listed in the tool-system.md catalog at all (omitted from both core and specialized sections).
- `00-stats.md` line 112: "Generates synthetic tool output for SDK mode" — **Inaccurate**. The tool name is `StructuredOutput`, not `SyntheticOutput`. It validates and returns structured JSON against a schema, not "generates synthetic output."

**Discrepancies**:
1. **Tool name mismatch**: Registered as `'StructuredOutput'`, not `'SyntheticOutput'`. The class/export is `SyntheticOutputTool` but the runtime name is `StructuredOutput`.
2. **Description misleading**: "Generates synthetic tool output" suggests fake data; the actual behavior is schema-validated structured JSON return.
3. The `createSyntheticOutputTool()` factory with Ajv validation and WeakMap caching is a significant feature not documented.
4. Missing from `tool-system.md` catalog entirely.

---

### 29. TaskCreateTool

| Field | Source Code Value |
|-------|-------------------|
| **Actual tool name** | `'TaskCreate'` |
| **Input schema** | `{ subject: string, description: string, activeForm?: string, metadata?: Record<string, unknown> }` (strictObject) |
| **Category** | Tasks (TodoV2) |
| **Key behavior** | Creates a task in the TodoV2 task list system. Sets initial status to `pending`, executes `TaskCreated` hooks (can block creation if hooks return blocking errors — rolls back by deleting task), auto-expands the task list panel in UI. Supports `activeForm` for spinner text during progress. |
| **Permission model** | Uses `buildTool` defaults |
| **isReadOnly()** | Default (`false`) |
| **isEnabled()** | `isTodoV2Enabled()` |
| **shouldDefer** | `true` |
| **isConcurrencySafe()** | `true` |
| **userFacingName()** | `'TaskCreate'` |

**Existing Analysis vs Source**:
- `tool-system.md` line 144: "Create tasks (TodoV2)" — **Correct**.
- `00-stats.md` line 113: "Creates background tasks" — **Imprecise**. These are TodoV2 tasks (structured task items with subjects, descriptions, status tracking, dependency blocking), not "background tasks" (which are a different concept — see LocalAgentTask/ShellTask).

**Discrepancies**:
1. `00-stats.md` description "Creates background tasks" is misleading — should be "Creates TodoV2 tasks" or "Creates structured tasks in the task list".
2. Hook-based validation (TaskCreated hooks can block creation) not mentioned.
3. `activeForm` parameter for spinner text not documented.

---

### 30. TaskGetTool

| Field | Source Code Value |
|-------|-------------------|
| **Actual tool name** | `'TaskGet'` |
| **Input schema** | `{ taskId: string }` (strictObject) |
| **Category** | Tasks (TodoV2) |
| **Key behavior** | Retrieves a task by ID from the TodoV2 task list. Returns task details including id, subject, description, status, blocks (tasks this blocks), and blockedBy (tasks blocking this). Returns `{ task: null }` if task not found. |
| **Permission model** | Uses `buildTool` defaults |
| **isReadOnly()** | `true` |
| **isEnabled()** | `isTodoV2Enabled()` |
| **shouldDefer** | `true` |
| **isConcurrencySafe()** | `true` |
| **userFacingName()** | `'TaskGet'` |

**Existing Analysis vs Source**:
- `tool-system.md` line 145: "Get task details" — **Correct**.
- `00-stats.md` line 114: "Gets task status/details" — **Correct**.

**Discrepancies**: None. Analysis is accurate.

---

## Cross-Cutting Findings

### 1. ScheduleCronTool Decomposition
The `ScheduleCronTool/` directory is a container for 3 independent tools (CronCreate, CronDelete, CronList), each with its own `buildTool()` call, name, and schema. The `tool-system.md` incorrectly treats it as a single tool. The `00-stats.md` correctly lists all 3 separately.

### 2. SyntheticOutputTool Name Mismatch
The runtime tool name is `'StructuredOutput'`, not `'SyntheticOutput'`. This is a pattern where the export name differs from the registered name — could cause confusion when searching logs or debugging.

### 3. TodoV2 vs Background Tasks Confusion
`TaskCreateTool`, `TaskGetTool` (and presumably TaskUpdate/TaskList/TaskStop) operate on the **TodoV2 task list** system — structured task items with subjects, dependencies, and status tracking. These are distinct from **background tasks** (LocalAgentTask, ShellTask) which are async execution contexts. The existing stats describe them as "background tasks" which is incorrect.

### 4. Teammate/Swarm Scoping Pattern
Multiple tools (SendMessageTool, CronCreateTool, CronDeleteTool, CronListTool) implement **teammate-aware scoping**: teammates can only see/modify their own resources, while the team lead sees all. This cross-cutting pattern is not documented in the existing analysis.

### 5. Feature Flag Complexity
The cron tools use a multi-layered gating system: build-time `feature('AGENT_TRIGGERS')` for dead-code elimination + runtime GrowthBook `tengu_kairos_cron` (default true) + env var `CLAUDE_CODE_DISABLE_CRON` override. A second flag `tengu_kairos_cron_durable` independently gates durable (persistent) cron. This is more sophisticated than the existing analysis implies.

### 6. Missing Source Files
- `SleepTool/SleepTool.ts` — not present in source dump (only prompt.ts)
- `REPLTool/REPLTool.ts` — not present (only constants.ts and primitiveTools.ts)
Both are loaded via dynamic `require()` in tools.ts, suggesting they may be generated at build time or excluded from the source dump.

---

## Recommendations for Analysis Updates

1. **tool-system.md**: Split "ScheduleCronTool" into 3 entries (CronCreate, CronDelete, CronList)
2. **tool-system.md**: Add SyntheticOutputTool/StructuredOutput to the catalog
3. **00-stats.md**: Fix SyntheticOutputTool description — "Schema-validated structured JSON output for SDK/CLI" not "Generates synthetic tool output"
4. **00-stats.md**: Fix TaskCreateTool description — "Creates TodoV2 tasks" not "Creates background tasks"
5. **tool-system.md**: Document SendMessageTool's 6 routing paths and safety checks
6. **tool-system.md**: Document SkillTool's inline vs forked execution model
7. **Cross-cutting**: Document teammate-aware resource scoping pattern
8. **Cross-cutting**: Document the multi-layered feature gating pattern (build-time + GrowthBook + env var)
