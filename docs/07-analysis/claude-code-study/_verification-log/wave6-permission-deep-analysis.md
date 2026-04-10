# Wave 6: Permission System Deep Analysis

> **Source**: Claude Code source (`CC-Source/src/`) — 24 files in `utils/permissions/`, 6 files in `hooks/toolPermission/`, 8 files in `components/permissions/rules/`, plus `tools/BashTool/bashPermissions.ts` and `bashSecurity.ts`
> **Date**: 2026-04-01
> **Verification Quality**: Deep behavioral read of all files; corrects errors found in Wave 4 Path 3

---

## 1. Permission Modes (Complete Enumeration)

The system defines **7 permission modes** via a two-tier type system:

### External Modes (user-visible, persisted)
| Mode | Symbol | Behavior |
|------|--------|----------|
| `default` | (none) | Standard prompt-for-everything |
| `acceptEdits` | `>>` | Auto-allow file edits within working directory |
| `plan` | pause icon | Read-only; blocks tool execution unless bypass was originally available |
| `bypassPermissions` | `>>` | Allow everything except bypass-immune safety checks |
| `dontAsk` | `>>` | Convert all `ask` decisions to `deny` (never prompt) |

### Internal Modes (ant-only, not persisted externally)
| Mode | Symbol | Behavior |
|------|--------|----------|
| `auto` | `>>` | AI classifier decides instead of prompting user |
| `bubble` | - | Internal-only, excluded from external modes |

**Mode cycling** (Shift+Tab) follows a defined carousel:
- **External users**: `default` -> `acceptEdits` -> `plan` -> (`bypassPermissions` if available) -> (`auto` if available) -> `default`
- **Ant users**: `default` -> (`bypassPermissions` if available) -> (`auto` if available) -> `default` (skips acceptEdits and plan)

Source: `getNextPermissionMode.ts`

---

## 2. The Complete Permission Decision Cascade

The decision is made in two layers: the **inner function** (`hasPermissionsToUseToolInner`) and the **outer wrapper** (`hasPermissionsToUseTool`).

### 2.1 Inner Function: `hasPermissionsToUseToolInner(tool, input, context)`

This is the core cascade, executed in strict order:

```
Step 0:  Abort check (throw AbortError if signal.aborted)

Step 1a: DENY RULE — tool-level
         getDenyRuleForTool() checks all deny rules across all sources
         If match: return {deny}

Step 1b: ASK RULE — tool-level
         getAskRuleForTool() checks all ask rules across all sources
         If match AND NOT (Bash + sandbox auto-allow enabled + command is sandboxable):
           return {ask}
         Else: fall through to let tool.checkPermissions handle it

Step 1c: TOOL-SPECIFIC CHECK — tool.checkPermissions(parsedInput, context)
         Each tool implements its own permission logic
         Default result: {passthrough} if schema parse fails

Step 1d: TOOL DENIED
         If tool.checkPermissions returned {deny}: return {deny}

Step 1e: USER INTERACTION REQUIRED
         If tool.requiresUserInteraction() && result is {ask}: return {ask}
         (Bypass-immune: even bypassPermissions cannot skip this)

Step 1f: CONTENT-SPECIFIC ASK RULES
         If tool returned {ask} with decisionReason.type === 'rule' AND
         rule.ruleBehavior === 'ask': return {ask}
         (Bypass-immune: explicit ask rules always prompt)

Step 1g: SAFETY CHECK (bypass-immune)
         If tool returned {ask} with decisionReason.type === 'safetyCheck':
           return {ask}
         (Covers .git/, .claude/, .vscode/, shell configs)

Step 2a: BYPASS PERMISSIONS MODE
         If mode is bypassPermissions, OR mode is plan AND
         isBypassPermissionsModeAvailable: return {allow}

Step 2b: TOOL-LEVEL ALLOW RULE
         toolAlwaysAllowedRule() checks all allow rules across all sources
         If match: return {allow}

Step 3:  PASSTHROUGH -> ASK conversion
         If behavior is still 'passthrough', convert to 'ask'
         Return the result
```

### 2.2 Outer Wrapper: `hasPermissionsToUseTool`

Wraps the inner result with mode-specific transformations:

```
On ALLOW result:
  - If auto mode: reset consecutive denial counter via recordSuccess()
  - Return allow

On ASK result, apply mode transformations in order:

  A. dontAsk mode:
     Convert ask -> deny with DONT_ASK_REJECT_MESSAGE

  B. auto mode (or plan mode with auto active):
     B1. Non-classifierApprovable safetyCheck -> deny (headless) or ask (interactive)
     B2. requiresUserInteraction -> return ask (cannot auto-approve)
     B3. PowerShell guard (unless POWERSHELL_AUTO_MODE feature flag)
     B4. acceptEdits fast-path: simulate acceptEdits mode check
         If would be allowed: return allow (skip classifier)
         Exception: Agent and REPL tools are excluded from this fast-path
     B5. Safe tool allowlist: isAutoModeAllowlistedTool()
         If tool is on allowlist: return allow (skip classifier)
     B6. YOLO Classifier: classifyYoloAction() via sideQuery API call
         - If shouldBlock AND transcriptTooLong: fall back to ask or abort
         - If shouldBlock AND unavailable: deny (fail-closed) or ask (fail-open)
         - If shouldBlock: record denial, check limits, return deny
         - If allowed: record success, return allow

  C. shouldAvoidPermissionPrompts (headless/background agents):
     Run PermissionRequest hooks first
     If hook provides decision: return it
     Else: auto-deny with AUTO_REJECT_MESSAGE
```

Source: `permissions.ts` lines 473-956

---

## 3. Rule System Architecture

### 3.1 Rule Sources (Priority Order)

Rules are loaded from multiple sources, all flattened into a single evaluation:

| Source | Persistence | Editability |
|--------|-------------|-------------|
| `policySettings` | Managed/enterprise | Read-only |
| `flagSettings` | Runtime flags | Read-only |
| `userSettings` | `~/.claude/settings.json` | Editable |
| `projectSettings` | `.claude/settings.json` | Editable |
| `localSettings` | `.claude/settings.local.json` | Editable |
| `cliArg` | CLI `--permission-mode` | Read-only |
| `command` | Slash command frontmatter | Read-only |
| `session` | In-memory only | Transient |

**Managed policy override**: When `allowManagedPermissionRulesOnly` is true in policySettings, ONLY policySettings rules are loaded. All other sources are ignored.

Source: `permissionsLoader.ts`

### 3.2 Rule Structure

```typescript
type PermissionRule = {
  source: PermissionRuleSource    // Where the rule came from
  ruleBehavior: 'allow' | 'deny' | 'ask'
  ruleValue: {
    toolName: string              // e.g., "Bash", "Edit", "mcp__server1"
    ruleContent?: string          // e.g., "npm install", "prefix:*"
  }
}
```

### 3.3 Rule Parsing (`permissionRuleParser.ts`)

Format: `ToolName` or `ToolName(content)`

- Parentheses in content must be escaped: `\(` and `\)`
- Empty content or `*` content treated as tool-wide rule
- Legacy tool names auto-normalized: `Task` -> `Agent`, `KillShell` -> `TaskStop`
- MCP tool matching: rule `mcp__server1` matches all tools from that server; `mcp__server1__*` also works

### 3.4 Shell Rule Matching (`shellRuleMatching.ts`)

Three rule types for Bash/PowerShell:

| Type | Format | Example | Matching |
|------|--------|---------|----------|
| Exact | `command` | `Bash(npm install)` | Exact string match |
| Prefix | `command:*` | `Bash(git:*)` | `command.startsWith(prefix + " ")` |
| Wildcard | `pattern*text` | `Bash(git commit *)` | Glob-style with `*` matching any chars |

### 3.5 Shadowed Rule Detection (`shadowedRuleDetection.ts`)

Detects unreachable rules, e.g.:
- An allow rule for `Bash(npm install)` shadowed by a tool-wide deny rule for `Bash`
- A content-specific allow shadowed by a tool-wide ask rule

Reports: which rule shadows it, the shadow type, and a suggested fix.

---

## 4. Per-Tool Permission Specializations

### 4.1 BashTool (`bashPermissions.ts`)

The most complex tool permission implementation. Key behaviors:

**Subcommand decomposition**: Compound commands (`cmd1 && cmd2 || cmd3`) are split into subcommands (up to `MAX_SUBCOMMANDS_FOR_SECURITY_CHECK = 50`), each evaluated independently.

**Safe env var stripping**: Leading `VAR=value` assignments are stripped if the var is in the safe list (e.g., `NODE_ENV`, `CI`). Non-safe vars prevent prefix rule matching.

**Prefix extraction**: `getSimpleCommandPrefix()` extracts `command subcommand` pairs (e.g., `git commit` from `git commit -m "msg"`). Must pass shape checks (lowercase alphanumeric).

**Bare shell prefix blocking**: Rules for `sh:*`, `bash:*`, `python:*`, `env:*`, `sudo:*` etc. are blocked from being suggested — they would bypass the classifier.

**Sandbox auto-allow**: When `autoAllowBashIfSandboxed` is enabled AND the command will run in sandbox, tool-wide ask rules are bypassed.

**Security validators** (`bashSecurity.ts`): ~23 distinct security check IDs covering:
- Command substitution patterns (`$()`, backticks, process substitution)
- Zsh-specific dangerous commands (`zmodload`, `sysopen`, `ztcp`, etc.)
- Shell metacharacter injection
- Obfuscated flags, IFS injection, control characters
- Unicode whitespace, mid-word hash, brace expansion
- Heredoc-in-substitution patterns

**Two classifier systems**:
1. **Bash Classifier** (feature flag `BASH_CLASSIFIER`): Per-command classifier that runs asynchronously during the permission prompt. Can auto-approve before user responds.
2. **YOLO/Auto-Mode Classifier** (feature flag `TRANSCRIPT_CLASSIFIER`): Full-transcript classifier that evaluates whether an action is safe based on conversation context.

### 4.2 Other Tools

Each tool implements `checkPermissions()` returning a `PermissionResult`:
- **Edit/Write tools**: Check path safety (`checkPathSafetyForAutoEdit`), working directory constraints
- **Agent tool**: Returns `allow` for acceptEdits mode; excluded from auto-mode acceptEdits fast-path
- **REPL tool**: Excluded from acceptEdits fast-path (VM escapes between inner tool calls)
- **PowerShell tool**: Requires explicit user permission in auto mode unless `POWERSHELL_AUTO_MODE` is on

---

## 5. The 5-Way Concurrent Permission Resolver

When the interactive handler runs (`interactiveHandler.ts`), it sets up a **race between 5 concurrent resolution paths**, using a `claim()` atomic guard to ensure exactly one wins:

### Path 1: User Interaction (Local CLI)
The permission dialog is pushed to the `ToolUseConfirmQueue`. User can:
- **Allow**: Optionally with permission updates (permanent rules) and feedback
- **Reject**: With optional feedback text and content blocks
- **Abort**: Cancels the entire operation
- **recheckPermission**: Re-evaluates rules (triggered by mode changes)

### Path 2: PermissionRequest Hooks
Async execution of `executePermissionRequestHooks()`. If a hook returns allow/deny before the user responds, it wins the race. Can include `updatedPermissions` for persistent rule changes.

### Path 3: Bash Classifier (BASH_CLASSIFIER feature)
For Bash commands only. `executeAsyncClassifierCheck()` runs asynchronously. If it approves before user interaction (with a 200ms grace period), it:
- Shows a checkmark transition UI (3s if terminal focused, 1s if not)
- User can dismiss early with Esc via `onDismissCheckmark`
- Sets `classifierAutoApproved` and `classifierMatchedRule` on the queue item

### Path 4: Bridge (Claude.ai CCR)
When connected to Claude.ai via bridge:
- Sends permission request with `bridgeCallbacks.sendRequest()`
- Subscribes for response via `bridgeCallbacks.onResponse()`
- Supports both allow (with `updatedInput` and `updatedPermissions`) and deny

### Path 5: Channel Relay (Telegram, iMessage, etc.)
When Kairos channels are configured:
- Sends structured `permission_request` notification to all allowed channel MCP servers
- Each channel server formats for its platform (Telegram markdown, iMessage rich text)
- Reply `yes <requestId>` or `no <requestId>` is intercepted before reaching conversation
- Only for tools that don't require user interaction

**Concurrency control**: The `createResolveOnce` utility provides:
- `resolve(value)`: Delivers the value (idempotent after first call)
- `isResolved()`: Check if already resolved
- `claim()`: Atomic check-and-mark — returns true only for the first caller

Source: `interactiveHandler.ts`, `PermissionContext.ts`

---

## 6. Handler Dispatch: Three Permission Flows

### 6.1 Interactive Handler (Main Agent)
- Full 5-way race as described above
- All automated checks run asynchronously (non-blocking)
- User always has a dialog to interact with

### 6.2 Coordinator Handler (Coordinator Workers)
- Automated checks run **sequentially before** the dialog
- First tries hooks, then classifier
- If either resolves: return immediately (no dialog needed)
- If neither resolves: fall through to interactive handler with `awaitAutomatedChecksBeforeDialog = true`

### 6.3 Swarm Worker Handler
- Tries classifier first (awaited, not raced)
- If not resolved: forwards request to leader via mailbox (`sendPermissionRequestViaMailbox`)
- Registers callback for leader response (`registerPermissionCallback`)
- Shows pending indicator (`pendingWorkerRequest` in AppState)
- Supports abort signal for cleanup
- Falls back to local interactive handling if swarm submission fails

Source: `handlers/interactiveHandler.ts`, `handlers/coordinatorHandler.ts`, `handlers/swarmWorkerHandler.ts`

---

## 7. Safety Checks That Bypass All Modes

These checks return `{ask, decisionReason: {type: 'safetyCheck'}}` and are **immune to bypass**:

1. **Protected paths**: `.git/`, `.claude/`, `.vscode/`, shell config files
   - Checked via `checkPathSafetyForAutoEdit()`
   - Some are `classifierApprovable: true` (sensitive files — classifier can decide)
   - Some are `classifierApprovable: false` (Windows path bypass, cross-machine bridge — always prompt)

2. **requiresUserInteraction tools** (Step 1e):
   - `ExitPlanMode`, `AskUserQuestion`, `ReviewArtifact`
   - Always prompt even in bypassPermissions mode

3. **Content-specific ask rules** (Step 1f):
   - Explicit user-configured ask rules like `Bash(npm publish:*)` 
   - Respected even in bypassPermissions mode, same as deny rules

4. **Tool-level deny rules** (Step 1a):
   - Always respected, no mode can override

---

## 8. Denial Tracking and Analytics

### 8.1 Denial Tracking State (`denialTracking.ts`)

```typescript
type DenialTrackingState = {
  consecutiveDenials: number   // Reset to 0 on any success
  totalDenials: number         // Monotonically increasing (reset at limit)
}

DENIAL_LIMITS = {
  maxConsecutive: 3,
  maxTotal: 20
}
```

**Behavior when limits exceeded** (`shouldFallbackToPrompting`):
- **Interactive mode**: Falls back to user prompting with warning message
- **Headless mode**: Throws `AbortError` to abort the agent

**Total limit reset**: When `maxTotal` is hit in interactive mode, both counters reset to 0 to allow continued operation after user review.

**State persistence**: For async subagents with `localDenialTracking`, state is mutated in-place via `Object.assign` (since `setAppState` is a no-op). Otherwise written to AppState.

### 8.2 Analytics Events

The system emits granular analytics via `logPermissionDecision()`:

| Event | Trigger |
|-------|---------|
| `tengu_tool_use_granted_in_config` | Auto-approved by allowlist |
| `tengu_tool_use_granted_in_prompt_permanent` | User approved with permanent rule |
| `tengu_tool_use_granted_in_prompt_temporary` | User approved one-time |
| `tengu_tool_use_granted_by_classifier` | Classifier auto-approved |
| `tengu_tool_use_granted_by_permission_hook` | Hook approved |
| `tengu_tool_use_rejected_in_prompt` | User or hook rejected |
| `tengu_tool_use_denied_in_config` | Denied by denylist |
| `tengu_tool_use_cancelled` | User aborted |
| `tengu_auto_mode_decision` | Auto mode classifier result (with full overhead telemetry) |
| `tengu_auto_mode_denial_limit_exceeded` | Denial limit hit |

**OTel integration**: `logOTelEvent('tool_decision', ...)` for distributed tracing. Code editing tools (Edit, Write, NotebookEdit) get additional language-enriched counter metrics.

**Decision storage**: Each decision is persisted on `toolUseContext.toolDecisions` map (keyed by `toolUseID`) for downstream inspection.

Source: `permissionLogging.ts`

---

## 9. Auto-Mode Classifier Architecture

### 9.1 Safe Tool Allowlist (`classifierDecision.ts`)

Tools that skip the classifier entirely (always auto-allowed in auto mode):

- **Read-only**: FileRead, Grep, Glob, LSP, ToolSearch, ListMcpResources, ReadMcpResource
- **Task management**: TodoWrite, TaskCreate/Get/Update/List/Stop/Output
- **Plan/UI**: AskUserQuestion, EnterPlanMode, ExitPlanMode
- **Swarm coordination**: TeamCreate, TeamDelete, SendMessage
- **Workflow**: WorkflowTool (subagents have their own permission checks)
- **Misc**: Sleep, TerminalCapture (ant), OverflowTest (ant), VerifyPlanExecution (ant)

**NOT on allowlist** (must go through classifier or acceptEdits fast-path): Bash, Edit, Write, Agent, REPL, PowerShell, NotebookEdit, MCP tools.

### 9.2 AcceptEdits Fast-Path

Before running the expensive classifier API call, the system checks if `acceptEdits` mode would allow the action:
- Simulates `tool.checkPermissions()` with mode set to `acceptEdits`
- If would be allowed: skip classifier, return allow
- **Excluded**: Agent tool and REPL tool (to prevent silent classifier bypass)

### 9.3 YOLO Classifier (`yoloClassifier.ts`)

- Uses `sideQuery()` for a separate API call (does NOT count toward session token totals)
- Two-stage classifier with separate usage tracking per stage
- Custom system prompt loaded from `.txt` template files
- Separate Anthropic-internal vs external permission templates
- User-customizable rules via `settings.autoMode` config (allow, soft_deny, environment sections)
- Computes classifier cost in USD for overhead analysis
- Logs prompt component lengths for debugging

### 9.4 Fail-Closed vs Fail-Open

When the classifier is unavailable (API error):
- **`tengu_iron_gate_closed` gate = true**: Deny with retry guidance (fail-closed)
- **`tengu_iron_gate_closed` gate = false**: Fall back to normal permission handling (fail-open)
- Gate is refreshed every 30 minutes (`CLASSIFIER_FAIL_CLOSED_REFRESH_MS`)

When transcript exceeds classifier context window:
- **Interactive**: Fall back to manual approval
- **Headless**: Throw `AbortError` (permanent condition, transcript only grows)

---

## 10. Bypass Permissions Killswitch

`bypassPermissionsKillswitch.ts` provides two run-once checks:

1. **`checkAndDisableBypassPermissionsIfNeeded()`**: Checks Statsig gate to potentially disable bypassPermissions mode. Runs once before first query.

2. **`checkAndDisableAutoModeIfNeeded()`**: Verifies auto mode gate access. Runs on mount AND whenever model or fast mode changes. Can:
   - Kick user out of auto mode
   - Show a notification explaining why
   - Set `autoModeCircuitBroken` flag to prevent re-entry

Both have `reset*()` functions called after `/login` to re-check with new org credentials.

Source: `bypassPermissionsKillswitch.ts`, `autoModeState.ts`

---

## 11. Permission Rule UI (`components/permissions/rules/`)

### Tab Structure (`PermissionRuleList.tsx`)
- **Recent**: Shows `AutoModeDenial` entries from `getAutoModeDenials()` — recently blocked actions
- **Allow**: Lists all allow rules across all sources
- **Ask**: Lists all ask rules
- **Deny**: Lists all deny rules  
- **Workspace**: Working directory management

### UI Components
| Component | Purpose |
|-----------|---------|
| `AddPermissionRules.tsx` | UI for adding new rules |
| `AddWorkspaceDirectory.tsx` | Add working directories |
| `RemoveWorkspaceDirectory.tsx` | Remove working directories |
| `PermissionRuleDescription.tsx` | Human-readable rule description |
| `PermissionRuleInput.tsx` | Editable rule input field |
| `RecentDenialsTab.tsx` | Shows recent auto-mode denials with approve/retry actions |
| `WorkspaceTab.tsx` | Workspace directory management |

### RecentDenialsTab
- Displays denials from auto-mode classifier
- User can mark entries as "approved" (add allow rule) or "retry" (re-run)
- State changes reported to parent via `onStateChange` callback

---

## 12. Permission Explainer (`permissionExplainer.ts`)

Uses a separate LLM `sideQuery()` call to generate human-readable explanations:
- Risk level: LOW / MEDIUM / HIGH
- Explanation: What the command does
- Reasoning: Why Claude is running it (first-person)
- Risk assessment: Potential dangers

Uses forced tool use for structured output (no beta required).

---

## 13. Key Corrections from Wave 4

| Previous Claim | Correction |
|----------------|------------|
| "3 permission modes" | **7 modes**: default, acceptEdits, plan, bypassPermissions, dontAsk, auto, bubble |
| Cascade was incompletely described | Full 3-step inner + mode-transform outer cascade with 7 sub-steps documented |
| No mention of auto mode classifier | Two-stage YOLO classifier with acceptEdits fast-path, safe-tool allowlist, fail-closed/fail-open gates |
| "Bridge is for CCR only" | 5-way concurrent resolver: user + hooks + classifier + bridge + channel relay |
| Safety checks loosely described | Precise enumeration: safetyCheck (classifierApprovable flag), requiresUserInteraction, content-specific ask rules |
| No denial tracking described | Full DenialTrackingState with consecutive (3) and total (20) limits, fallback-to-prompting behavior |
| Missing handler dispatch | Three distinct handlers: interactive (5-way race), coordinator (sequential-then-dialog), swarm (classifier-then-leader-mailbox) |
| bashSecurity underspecified | 23 security check IDs, Zsh-specific dangerous command set, command substitution pattern detection |

---

## 14. Architecture Summary Diagram

```
                    hasPermissionsToUseTool (outer)
                              |
                    hasPermissionsToUseToolInner
                              |
        +---------------------+---------------------+
        |                     |                      |
    1a. Deny Rules     1b. Ask Rules        1c. tool.checkPermissions()
        |                     |                      |
        v                     v                      v
    1d. Tool Deny     1e. requiresUser      1f. Content Ask Rules
        |             Interaction             |
        v                                    v
                    1g. Safety Checks
                         |
        +----------------+----------------+
        |                                 |
   2a. Bypass Mode              2b. Allow Rules
        |                                 |
        v                                 v
                    3. passthrough -> ask
                              |
              +---------------+---------------+
              |               |               |
         dontAsk          auto mode      headless agent
         -> deny          classifier     -> hooks -> deny
                              |
              +-------+-------+-------+-------+
              |       |       |       |       |
           accept  safe    yolo    fail     denial
           Edits   allow  classify  mode    limits
           fast    list           (closed/  (3/20)
           path                   open)
```

---

*Analysis based on source files read 2026-04-01. All function names, step numbers, and behaviors verified against actual source code.*
