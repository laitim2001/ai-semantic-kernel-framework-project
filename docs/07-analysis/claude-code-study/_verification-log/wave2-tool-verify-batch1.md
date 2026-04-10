# Wave 2 — Tool Verification Batch 1 (Tools 1-10)
> Verified: 2026-04-01 | Source: CC-Source/src/tools/ | Verifier: Claude Opus 4.6

## Verification Results

### 1. AgentTool
- **Name**: `Agent` (constant `AGENT_TOOL_NAME` in `constants.ts`; alias: `Task` via `LEGACY_AGENT_TOOL_NAME`)
- **Input Schema**: `{ description: string, prompt: string, subagent_type?: string, model?: enum('sonnet','opus','haiku'), run_in_background?: boolean, name?: string, team_name?: string, mode?: permissionModeSchema, isolation?: enum('worktree','remote'), cwd?: string }` — conditionally omits `run_in_background` (when background tasks disabled or fork subagent enabled), `cwd` (when KAIROS feature off)
- **Category**: Agent
- **Key Behavior**: `call()` spawns a sub-agent — either as a teammate (via `spawnTeammate()` when team_name+name set), a remote CCR agent (when isolation='remote'), a worktree-isolated agent, or a standard foreground/background subagent via `runAgent()`. Handles complex multi-agent orchestration including tmux split-pane teammates.
- **Permission Model**: `checkPermissions()` returns `{ behavior: 'passthrough' }` in auto mode for ant builds (routes through auto classifier); otherwise auto-allows. No filesystem permission checks — delegates to underlying tools.
- **isReadOnly**: `true` (delegates permission checks to its underlying tools)
- **isEnabled**: Not defined — uses buildTool default `() => true`
- **Accuracy vs existing docs**: ✅ Accurate
- **Discrepancies**: None significant. Docs correctly identify it as Agent category, spawning subagents. The alias `Task` and the complex multi-agent spawn paths (teammate, remote, worktree) are not fully detailed in the catalog table but are mentioned in the tool-system.md description.

### 2. AskUserQuestionTool
- **Name**: `AskUserQuestion` (constant `ASK_USER_QUESTION_TOOL_NAME` in `prompt.ts`)
- **Input Schema**: `{ questions: array(questionSchema, min 1, max 4), answers?: Record<string,string>, annotations?: annotationsSchema, metadata?: { source?: string } }` — uses `z.strictObject` with a uniqueness refine
- **Category**: Interaction
- **Key Behavior**: `call()` presents multiple-choice questions to the user via a permission-style UI dialog. Collects answers and returns them as a record of question-text to answer-string. Supports HTML preview format for rich question rendering.
- **Permission Model**: No custom `checkPermissions` — uses buildTool default (auto-allow). Has `requiresUserInteraction() => true`.
- **isReadOnly**: `true`
- **isEnabled**: Returns `false` when `--channels` is active (user on Telegram/Discord, no one at keyboard); otherwise `true`
- **shouldDefer**: `true`
- **Accuracy vs existing docs**: ✅ Accurate
- **Discrepancies**: Existing docs say "Prompts user for input during autonomous runs" which is correct but incomplete — it supports structured multi-question (1-4) input with options, not just free-text. The `shouldDefer: true` is not mentioned in the catalog.

### 3. BashTool
- **Name**: `Bash` (constant `BASH_TOOL_NAME` in `toolName.ts`)
- **Input Schema**: `{ command: string, timeout?: number, description?: string, run_in_background?: boolean, dangerouslyDisableSandbox?: boolean }` — internally also has `_simulatedSedEdit` (always omitted from model-facing schema). `run_in_background` conditionally omitted when background tasks disabled.
- **Category**: Shell
- **Key Behavior**: `call()` executes shell commands with extensive security validation (`bashSecurity.ts` — 98KB, `bashPermissions.ts` — 98KB), sandbox support (`shouldUseSandbox.ts`), read-only validation, path validation, sed edit detection/preview, and background task support. Processes stdout/stderr with image detection, large output persistence, and structured content blocks.
- **Permission Model**: `checkPermissions()` delegates to `bashToolHasPermission()` — an extensive permission system in `bashPermissions.ts` with compound command parsing, path validation, and security checks.
- **isReadOnly**: Conditional — calls `checkReadOnlyConstraints(input, compoundCommandHasCd)` and returns `true` only if result behavior is 'allow' (i.e., the command is determined to be read-only).
- **isEnabled**: Not defined — uses buildTool default `() => true`
- **Accuracy vs existing docs**: ✅ Accurate
- **Discrepancies**: Docs say "23 security checks" — the actual `bashSecurity.ts` is 102KB which likely contains many more than 23 checks. The `dangerouslyDisableSandbox` param and `_simulatedSedEdit` internal field are not mentioned in the catalog. The `strict: true` flag is set but not documented.

### 4. BriefTool
- **Name**: `SendUserMessage` (constant `BRIEF_TOOL_NAME` in `prompt.ts`; alias: `Brief` via `LEGACY_BRIEF_TOOL_NAME`)
- **Input Schema**: `{ message: string, attachments?: string[], status: enum('normal','proactive') }`
- **Category**: Interaction / Communication
- **Key Behavior**: `call()` sends a message (with optional file attachments) to the user. Resolves attachment paths, logs analytics events. This is the primary output channel for the model in "brief" / chat mode and KAIROS assistant mode.
- **Permission Model**: No custom `checkPermissions` — uses buildTool default (auto-allow).
- **isReadOnly**: `true`
- **isEnabled**: Complex gating via `isBriefEnabled()` — requires both entitlement (KAIROS or KAIROS_BRIEF feature flags + GrowthBook gate `tengu_kairos_brief` or env var `CLAUDE_CODE_BRIEF`) AND opt-in (kairosActive or userMsgOptIn set by `--brief` flag, `defaultView: 'chat'`, or `/brief` command).
- **Accuracy vs existing docs**: ⚠️ Minor issues
- **Discrepancies**:
  1. **Tool name is wrong in existing docs**: The catalog (00-stats.md row 4) lists the name as `BriefTool` with category "Files" and description "Uploads attachments/briefs to session context". The actual registered name is `SendUserMessage`, not `Brief`. `Brief` is just a legacy alias.
  2. **Category mismatch**: Listed as "Files" but it's really an Interaction/Communication tool — its primary purpose is sending messages to the user, not file operations.
  3. **Description inaccurate**: "Uploads attachments/briefs" is misleading. The core function is sending messages to the user; attachments are optional.

### 5. ConfigTool
- **Name**: `Config` (constant `CONFIG_TOOL_NAME` in `constants.ts`)
- **Input Schema**: `{ setting: string, value?: string | boolean | number }` — omit `value` for GET operation
- **Category**: Config
- **Key Behavior**: `call()` reads or writes Claude Code configuration settings. GET operation reads current value; SET operation validates against supported settings list, handles "default" reset, applies formatOnWrite/formatOnRead transformations, and writes to the appropriate config source.
- **Permission Model**: `checkPermissions()` auto-allows reading (when `value` is undefined); asks user permission for writes with message showing setting and new value.
- **isReadOnly**: Conditional — `true` when `input.value === undefined` (GET), `false` when setting a value (SET)
- **isEnabled**: Not defined — uses buildTool default `() => true`
- **shouldDefer**: `true`
- **Accuracy vs existing docs**: ⚠️ Minor issues
- **Discrepancies**: Existing docs (00-stats.md) say ConfigTool is "ant-only" (`process.env.USER_TYPE === 'ant'`). Looking at the source, ConfigTool itself has no `isEnabled` gate — it always returns the default `true`. The ant-only gating must happen at the registration level in `tools.ts`, not within the tool. The tool-system.md line 99 correctly notes `process.env.USER_TYPE === 'ant'` as a conditional loading mechanism for ConfigTool, which is accurate at the registration level.

### 6. EnterPlanModeTool
- **Name**: `EnterPlanMode` (constant `ENTER_PLAN_MODE_TOOL_NAME` in `constants.ts`)
- **Input Schema**: `{}` (empty strict object — no parameters)
- **Category**: Planning / Mode
- **Key Behavior**: `call()` transitions the session to plan mode by updating `toolPermissionContext.mode` to `'plan'` via `applyPermissionUpdate`. Throws if called from an agent context. Runs `prepareContextForPlanMode()` for classifier activation side effects.
- **Permission Model**: No custom `checkPermissions` — uses buildTool default (auto-allow).
- **isReadOnly**: `true`
- **isEnabled**: Returns `false` when `--channels` is active (KAIROS/KAIROS_CHANNELS + channels configured); otherwise `true`
- **shouldDefer**: `true`
- **Accuracy vs existing docs**: ✅ Accurate
- **Discrepancies**: None. Docs correctly identify it as Mode category, entering plan mode. The `shouldDefer: true` is not explicitly mentioned in the catalog table.

### 7. EnterWorktreeTool
- **Name**: `EnterWorktree` (constant `ENTER_WORKTREE_TOOL_NAME` in `constants.ts`)
- **Input Schema**: `{ name?: string }` — optional worktree name with validation (letters, digits, dots, underscores, dashes; max 64 chars; `/`-separated segments)
- **Category**: Mode / Git
- **Key Behavior**: `call()` creates an isolated git worktree via `createWorktreeForSession()`, changes the process working directory to the worktree, updates session state (originalCwd, system prompt sections, memory file caches). Validates not already in a worktree session. Resolves to canonical git root first.
- **Permission Model**: No custom `checkPermissions` — uses buildTool default (auto-allow).
- **isReadOnly**: Not defined — uses buildTool default `() => false`
- **isEnabled**: Not defined — uses buildTool default `() => true`
- **shouldDefer**: `true`
- **Accuracy vs existing docs**: ✅ Accurate
- **Discrepancies**: None significant. Docs correctly describe it as entering git worktree isolation.

### 8. ExitPlanModeV2Tool
- **Name**: `ExitPlanMode` (constant `EXIT_PLAN_MODE_V2_TOOL_NAME` in `constants.ts`; note: `EXIT_PLAN_MODE_TOOL_NAME` also exports the same string `'ExitPlanMode'`)
- **Input Schema**: `{ allowedPrompts?: array({ tool: string, pattern?: string, description: string }) }` — uses `.passthrough()` to accept additional fields. SDK-facing schema adds `plan?: string` and `planFilePath?: string` (injected by normalizeToolInput).
- **Category**: Planning / Mode
- **Key Behavior**: `call()` reads the plan from disk (or from input if provided by CCR web UI), presents it to the user for approval, handles teammate plan approval routing (sends to team leader via mailbox), and transitions out of plan mode. Writes plan to disk file. Handles plan editing by user.
- **Permission Model**: `checkPermissions()` returns `{ behavior: 'allow' }` for teammates (bypasses UI); returns `{ behavior: 'ask', message: 'Exit plan mode?' }` for non-teammates.
- **isReadOnly**: `false` (explicitly — "Now writes to disk")
- **isEnabled**: Returns `false` when `--channels` is active; otherwise `true`
- **requiresUserInteraction**: `false` for teammates (leader approves via mailbox); `true` for non-teammates
- **shouldDefer**: `true`
- **Accuracy vs existing docs**: ✅ Accurate
- **Discrepancies**: The exported name `ExitPlanModeV2Tool` in code vs the registered name `ExitPlanMode` is correctly documented. The docs note the file lives in `ExitPlanModeTool/` directory which is accurate.

### 9. ExitWorktreeTool
- **Name**: `ExitWorktree` (constant `EXIT_WORKTREE_TOOL_NAME` in `constants.ts`)
- **Input Schema**: `{ action: enum('keep','remove'), discard_changes?: boolean }` — `discard_changes` required as `true` when action is 'remove' and worktree has uncommitted changes
- **Category**: Mode / Git
- **Key Behavior**: `call()` exits the current worktree session, restoring the original working directory. For action='keep', preserves the worktree on disk. For action='remove', deletes the worktree and branch (with safety checks for uncommitted changes/unmerged commits). Restores all session state (cwd, projectRoot, system prompt sections, memory caches).
- **Permission Model**: No custom `checkPermissions` — uses buildTool default (auto-allow).
- **isReadOnly**: Not defined — uses buildTool default `() => false`
- **isEnabled**: Not defined — uses buildTool default `() => true`
- **isDestructive**: Conditional — `true` when `input.action === 'remove'`
- **shouldDefer**: `true`
- **Accuracy vs existing docs**: ✅ Accurate
- **Discrepancies**: None significant. The `isDestructive` conditional behavior is not mentioned in existing docs but is a notable detail.

### 10. FileEditTool
- **Name**: `Edit` (constant `FILE_EDIT_TOOL_NAME` in `constants.ts`)
- **Input Schema**: `{ file_path: string, old_string: string, new_string: string, replace_all?: boolean (default false) }` — `replace_all` uses `semanticBoolean` wrapper for flexible input parsing
- **Category**: Files
- **Key Behavior**: `call()` performs exact string replacement in files. Reads the file, finds `old_string`, replaces with `new_string` (or all occurrences if `replace_all`). Includes extensive validation: file existence, old_string uniqueness (unless replace_all), file size limits (1 GiB max), git diff generation, line-ending preservation, team memory secret checking, settings file validation, and concurrent modification detection.
- **Permission Model**: `checkPermissions()` delegates to `checkWritePermissionForTool()` with filesystem permission rules and wildcard pattern matching.
- **isReadOnly**: Not defined — uses buildTool default `() => false`
- **isEnabled**: Not defined — uses buildTool default `() => true`
- **strict**: `true`
- **Accuracy vs existing docs**: ✅ Accurate
- **Discrepancies**: Docs describe it as "Exact string replacement edits with line-ending preservation" which is accurate. The `semanticBoolean` wrapper on `replace_all` and the `strict: true` flag are implementation details not captured in the catalog.

---

## Summary

| Metric | Count |
|--------|-------|
| Tools verified | 10/10 |
| Accurate | 8 |
| Minor issues | 2 |
| Incorrect | 0 |

### Corrections Needed

1. **BriefTool (Tool #4)** — Three issues:
   - **Registered name**: Should be `SendUserMessage`, not `Brief` (Brief is a legacy alias)
   - **Category**: Should be `Interaction` or `Communication`, not `Files`
   - **Description**: Should be "Sends messages (with optional attachments) to the user" not "Uploads attachments/briefs to session context"

2. **ConfigTool (Tool #5)** — Minor clarification:
   - The "ant-only" note is accurate at the registration level (`tools.ts`) but the tool itself has no `isEnabled` gate. The docs could clarify this distinction.

### Notable Findings Not in Existing Docs

| Tool | Finding |
|------|---------|
| AgentTool | Has alias `Task` (legacy); supports teammate spawn, remote CCR, worktree isolation modes |
| AskUserQuestionTool | `shouldDefer: true`; supports 1-4 structured questions with options, not just free-text |
| BashTool | `strict: true`; `_simulatedSedEdit` internal field; `dangerouslyDisableSandbox` param; security codebase is ~200KB (bashSecurity + bashPermissions) |
| BriefTool | Actual name `SendUserMessage`; complex entitlement+opt-in gating via KAIROS features |
| ExitPlanModeV2Tool | `requiresUserInteraction` is conditional (false for teammates); writes plan to disk |
| ExitWorktreeTool | `isDestructive` is conditional on action='remove' |
| FileEditTool | `strict: true`; `semanticBoolean` wrapper on replace_all; 1 GiB max file size; team memory secret checking |

### Deferred Tool Pattern (`shouldDefer: true`)

Several tools use `shouldDefer: true` — meaning their schema is NOT sent to the model upfront but loaded on demand via ToolSearchTool:
- AskUserQuestionTool
- ConfigTool
- EnterPlanModeTool (should be verified — it does set `shouldDefer: true`)
- EnterWorktreeTool
- ExitPlanModeV2Tool
- ExitWorktreeTool

This pattern is correctly described in tool-system.md's "shouldDefer flag" section but the specific tools using it are not enumerated there.
