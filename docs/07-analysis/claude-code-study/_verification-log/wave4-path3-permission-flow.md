# Wave 4 Path 3: Permission Checking Flow — E2E Verification

> Verification Date: 2026-04-01 | Wave: 4 | Path: Permission Decision Chain
> Source: Tool.ts, utils/permissions/, hooks/toolPermission/, components/permissions/, tools/BashTool/bashPermissions.ts

---

## 1. E2E Path Summary

This document traces the complete permission decision chain from tool call request to allow/deny decision, verified against actual source code.

```
API Response (tool_use block)
  → useCanUseTool hook (entry point)
    → hasPermissionsToUseTool() (outer wrapper)
      → hasPermissionsToUseToolInner() (core 3-step cascade)
        Step 1: Deny/Ask rules + tool.checkPermissions()
        Step 2: Mode checks (bypass/allow rules)
        Step 3: Passthrough→Ask conversion
      → Post-processing (dontAsk→deny, auto-mode classifier)
    → Handler dispatch:
        → coordinatorHandler (await hooks+classifier first)
        → swarmWorkerHandler (forward to leader)
        → interactiveHandler (show UI dialog, race hooks/classifier/bridge/channel)
  → PermissionDecision { allow | deny | ask }
```

---

## 2. Entry Point: `useCanUseTool` Hook

**File**: `src/hooks/useCanUseTool.tsx`

The React hook that wraps the entire permission flow. Called during tool execution in the query loop.

```typescript
// Signature
type CanUseToolFn = (
  tool: ToolType,
  input: Input,
  toolUseContext: ToolUseContext,
  assistantMessage: AssistantMessage,
  toolUseID: string,
  forceDecision?: PermissionDecision
) => Promise<PermissionDecision>
```

### Flow within useCanUseTool:

1. **Create PermissionContext** via `createPermissionContext()` — bundles tool, input, context, queue ops, logging
2. **Check abort** — if already aborted, resolve immediately
3. **Evaluate permissions** — call `hasPermissionsToUseTool()` (or use `forceDecision` if provided)
4. **Branch on result**:
   - **allow** → log decision, resolve with `buildAllow()`
   - **deny** → log decision, record auto-mode denial if applicable, resolve
   - **ask** → dispatch to handler chain (coordinator → swarm → speculative classifier → interactive)

### Handler Dispatch Chain (for `ask` decisions):

| Priority | Handler | Condition | Behavior |
|----------|---------|-----------|----------|
| 1 | `coordinatorHandler` | `awaitAutomatedChecksBeforeDialog` is true | Await hooks then classifier sequentially; fall through to dialog if neither resolves |
| 2 | `swarmWorkerHandler` | `isSwarmWorker()` is true | Try classifier, then forward to leader via mailbox file |
| 3 | Speculative classifier | `pendingClassifierCheck` + Bash tool + not coordinator | Race pre-computed classifier result (2s timeout) |
| 4 | `interactiveHandler` | Default fallback | Push to UI confirm queue; race user/hooks/classifier/bridge/channel |

---

## 3. Core Permission Engine: `hasPermissionsToUseTool`

**File**: `src/utils/permissions/permissions.ts`

### Outer Function (lines 473-598)

```typescript
export const hasPermissionsToUseTool: CanUseToolFn = async (tool, input, context, ...) => {
  const result = await hasPermissionsToUseToolInner(tool, input, context)
  // Post-processing...
}
```

**Post-processing after inner returns:**

1. **Allow** → reset consecutive denial counter (auto mode), return
2. **Ask + dontAsk mode** → convert to `deny` with `DONT_ASK_REJECT_MESSAGE`
3. **Ask + auto mode** → run auto-mode classifier pipeline:
   - Non-classifierApprovable safetyChecks → immune to auto-approve (stay as `ask` or `deny` in headless)
   - `requiresUserInteraction` tools → stay as `ask`
   - PowerShell without `POWERSHELL_AUTO_MODE` → stay as `ask`
   - acceptEdits fast-path → check if mode would allow (skip Agent/REPL)
   - Denial tracking fallback → if too many consecutive denials, fall back to prompting
   - **YOLO classifier** → call `classifyYoloAction()` with full transcript context

### Inner Function: `hasPermissionsToUseToolInner` (lines 1158-1319)

The 3-step cascade that is the heart of the permission system:

#### Step 1: Deny and Ask Checks

| Sub-step | Logic | Source |
|----------|-------|--------|
| **1a** | `getDenyRuleForTool()` — blanket deny on entire tool | Deny rules from all sources |
| **1b** | `getAskRuleForTool()` — blanket ask on entire tool | Ask rules (sandbox auto-allow exception for Bash) |
| **1c** | `tool.checkPermissions(input, context)` — tool-specific logic | Each tool implements its own |
| **1d** | If tool returned `deny` → return immediately | Tool-level denial |
| **1e** | If tool `requiresUserInteraction()` + returned `ask` → return | Tools like AskUserQuestion |
| **1f** | Content-specific ask rules (e.g., `Bash(npm publish:*)`) → return even in bypass | Explicit user-configured ask |
| **1g** | Safety checks (`.git/`, `.claude/`, shell configs) → bypass-immune | `safetyCheck` reason type |

#### Step 2: Mode and Allow-Rule Checks

| Sub-step | Logic | Source |
|----------|-------|--------|
| **2a** | `bypassPermissions` mode OR (plan mode + bypass available) → `allow` | Mode-based override |
| **2b** | `toolAlwaysAllowedRule()` — entire tool in allow list → `allow` | Allow rules from all sources |

#### Step 3: Passthrough Conversion

If tool returned `passthrough` (no opinion), convert to `ask` with appropriate message.

---

## 4. Tool-Specific Permission: `tool.checkPermissions()`

**File**: `src/Tool.ts` (interface, lines 500-503)

```typescript
checkPermissions(
  input: z.infer<Input>,
  context: ToolUseContext,
): Promise<PermissionResult>
```

Default implementation (for tools that don't override):
```typescript
checkPermissions: (input, _ctx) => Promise.resolve({ behavior: 'allow', updatedInput: input })
```

### PermissionResult Type

```typescript
type PermissionResult =
  | PermissionAllowDecision   // { behavior: 'allow', updatedInput?, decisionReason? }
  | PermissionAskDecision     // { behavior: 'ask', message, suggestions?, pendingClassifierCheck? }
  | PermissionDenyDecision    // { behavior: 'deny', message, decisionReason }
  | { behavior: 'passthrough', message, ... }  // No opinion — defer to global rules
```

The `passthrough` behavior is unique to `PermissionResult` (not in `PermissionDecision`) — it means the tool has no specific permission logic and defers entirely to the global permission engine.

---

## 5. Bash-Specific Permission: `bashToolHasPermission`

**File**: `src/tools/BashTool/bashPermissions.ts` (line 1663+)

The most complex tool-specific permission implementation. Called by BashTool's `checkPermissions()`.

### Processing Pipeline:

```
Input: { command: string }
  │
  ▼
Step 0: AST-based security parse (tree-sitter)
  ├─ parse-unavailable → fall back to legacy shell-quote
  ├─ too-complex → check deny rules, then ask
  ├─ simple → check semantics (eval, zsh builtins)
  │   ├─ semantics fail → check deny rules, then ask
  │   └─ semantics ok → extract subcommands
  │
  ▼
Step 1: Legacy shell-quote pre-check (if AST unavailable)
  │
  ▼
Step 2: Per-subcommand permission checks
  ├─ Check mode (plan mode read-only validation)
  ├─ Check sandbox enforcement
  ├─ Check path constraints
  ├─ Check sed constraints
  ├─ Check command operator permissions
  ├─ Match against allow/deny/ask rules (prefix, wildcard, exact)
  │
  ▼
Step 3: Aggregate subcommand results
  ├─ All allow → allow
  ├─ Any deny → deny
  ├─ Any ask → ask with pendingClassifierCheck
  └─ Generate permission suggestions for UI
```

### Rule Matching Types (from `shellRuleMatching.ts`):

```typescript
type ShellPermissionRule =
  | { type: 'exact', command: string }     // "npm test"
  | { type: 'prefix', prefix: string }     // "npm:*" (legacy) or "npm *"
  | { type: 'wildcard', pattern: string }  // "git commit *"
```

### Security Caps:

- `MAX_SUBCOMMANDS_FOR_SECURITY_CHECK = 50` — prevent exponential expansion
- `MAX_SUGGESTED_RULES_FOR_COMPOUND = 5` — cap UI suggestion noise

---

## 6. Permission Modes

**File**: `src/types/permissions.ts`, `src/utils/permissions/PermissionMode.ts`

### Mode Definitions

| Mode | External | Behavior |
|------|----------|----------|
| `default` | Yes | Prompt for write/destructive operations |
| `acceptEdits` | Yes | Auto-allow file edits; prompt for shell |
| `plan` | Yes | Read-only mode; writes blocked |
| `bypassPermissions` | Yes | Full bypass (explicit enable required) |
| `dontAsk` | Yes | Convert all `ask` to `deny` silently |
| `auto` | No (ant-only) | AI classifier decides; gated by `TRANSCRIPT_CLASSIFIER` |
| `bubble` | No | Bubble up to parent (for subagents) |

### Auto-Mode State (`autoModeState.ts`):

Simple module-level boolean flags:
- `autoModeActive` — whether auto mode is currently engaged
- `autoModeFlagCli` — whether `--auto` was passed on CLI
- `autoModeCircuitBroken` — kill-switch from GrowthBook when feature disabled remotely

---

## 7. Permission Rules Engine

**File**: `src/utils/permissions/permissions.ts` (lines 122-359)

### Rule Loading

Rules are loaded from `ToolPermissionRulesBySource` keyed by source:

```typescript
const PERMISSION_RULE_SOURCES = [
  'userSettings', 'projectSettings', 'localSettings',
  'flagSettings', 'policySettings',
  'cliArg', 'command', 'session'
]
```

### Rule Functions

| Function | Purpose |
|----------|---------|
| `getAllowRules(context)` | Flatten all allow rules from all sources |
| `getDenyRules(context)` | Flatten all deny rules from all sources |
| `getAskRules(context)` | Flatten all ask rules from all sources |
| `toolMatchesRule(tool, rule)` | Check if tool name matches rule (handles MCP server-level matching) |
| `toolAlwaysAllowedRule(context, tool)` | Find first allow rule matching entire tool |
| `getDenyRuleForTool(context, tool)` | Find first deny rule matching entire tool |
| `getRuleByContentsForTool(context, tool, behavior)` | Get content-specific rules (e.g., `Bash(git *)`) |

### Rule Parsing (`permissionRuleParser.ts`):

Format: `"ToolName"` or `"ToolName(content)"` with escaped parentheses.

```
"Bash"              → { toolName: "Bash" }
"Bash(npm install)" → { toolName: "Bash", ruleContent: "npm install" }
"Bash(*)"           → { toolName: "Bash" }  // wildcard = tool-wide
"mcp__server1"      → matches all tools from server1
```

Legacy tool name aliases are resolved via `LEGACY_TOOL_NAME_ALIASES` (e.g., `Task` → `Agent`).

---

## 8. Interactive Permission Flow

**File**: `src/hooks/toolPermission/handlers/interactiveHandler.ts`

When permission is `ask` and no automated check resolves it, the interactive handler:

### Race Architecture (5 concurrent resolvers):

```
                    ┌─ User interaction (onAllow/onReject/onAbort)
                    ├─ Permission hooks (executePermissionRequestHooks)
Permission Ask ─────├─ Bash classifier (executeAsyncClassifierCheck)
                    ├─ Bridge response (CCR / claude.ai web UI)
                    └─ Channel response (Telegram, iMessage via MCP)
                    
                    First to claim() wins via atomic ResolveOnce guard
```

### ResolveOnce Guard (`PermissionContext.ts`):

```typescript
function createResolveOnce<T>(resolve: (value: T) => void): ResolveOnce<T> {
  let claimed = false
  let delivered = false
  return {
    resolve(value) { if (delivered) return; delivered = true; claimed = true; resolve(value) },
    isResolved() { return claimed },
    claim() { if (claimed) return false; claimed = true; return true },
  }
}
```

The `claim()` method is the atomic check-and-mark used by all async callbacks to prevent double-resolution.

### UI Component Dispatch (`PermissionRequest.tsx`):

```typescript
function permissionComponentForTool(tool: Tool): React.ComponentType<PermissionRequestProps> {
  switch (tool) {
    case BashTool:         return BashPermissionRequest
    case FileEditTool:     return FileEditPermissionRequest
    case FileWriteTool:    return FileWritePermissionRequest
    case PowerShellTool:   return PowerShellPermissionRequest
    case WebFetchTool:     return WebFetchPermissionRequest
    case NotebookEditTool: return NotebookEditPermissionRequest
    case SkillTool:        return SkillPermissionRequest
    // ... 13 total tool-specific components
    default:               return FallbackPermissionRequest
  }
}
```

### ToolUseConfirm Queue Item:

```typescript
type ToolUseConfirm = {
  tool, input, description, toolUseID, permissionResult,
  classifierCheckInProgress?: boolean,
  classifierAutoApproved?: boolean,
  onUserInteraction(),   // Cancels async auto-approve
  onAllow(updatedInput, permissionUpdates, feedback?, contentBlocks?),
  onReject(feedback?, contentBlocks?),
  onAbort(),
  recheckPermission(),   // Re-evaluate after config change
  onDismissCheckmark?,   // Esc during classifier checkmark
}
```

---

## 9. Denial Tracking

**File**: `src/utils/permissions/denialTracking.ts`

Prevents infinite retry loops in auto mode:

```typescript
type DenialTrackingState = {
  consecutiveDenials: number   // Reset on any success
  totalDenials: number         // Never reset
}

const DENIAL_LIMITS = {
  maxConsecutive: 3,           // After 3 consecutive denials → fall back to prompting
  maxTotal: 20,                // After 20 total denials → fall back to prompting
}
```

---

## 10. Verification Against Existing Analysis

### data-flow.md Section 3 Accuracy

| Claim | Verdict | Notes |
|-------|---------|-------|
| "PermissionMode from session config" | **Partially Accurate** | Mode comes from `ToolPermissionContext.mode`, which is assembled from CLI flags, settings, and runtime changes — not just session config |
| "AUTO mode: classifier result → SAFE: allow, RISKY: deny and switch to manual" | **Inaccurate** | Auto mode has a multi-stage pipeline: acceptEdits fast-path → denial tracking check → YOLO classifier. Classifier result is `shouldBlock: true/false`, not "SAFE/RISKY". Does not automatically switch to manual |
| "MANUAL mode: global settings → session overrides → tool-specific → prompt user" | **Partially Accurate** | The actual cascade is: deny rules → ask rules → tool.checkPermissions() → mode check → allow rules → passthrough→ask. Source priority exists but within each step, not as a sequential chain |
| "PLAN mode: only read-only tools allowed" | **Accurate** | Plan mode with bypass available allows through; otherwise read-only enforced by tool.checkPermissions() |
| "BYPASS_PERMISSIONS: all tools allowed without prompting" | **Mostly Accurate** | Bypass is NOT absolute: content-specific ask rules (step 1f) and safety checks (step 1g) are bypass-immune |
| "Rule Sources priority order" | **Inaccurate ordering** | Listed as "CLI flags → Enterprise policy → MDM → Project → Global → Default". Actual code: rules from ALL sources are flattened with `PERMISSION_RULE_SOURCES` and first-match wins, not strict priority ordering. Deny rules checked before allow rules in the cascade, which IS the real priority |
| "tool.userPermissionResult()" function name | **Inaccurate** | Correct function is `tool.checkPermissions()`. The hook-level entry is `hasPermissionsToUseTool()` |

### permission-system.md Accuracy

| Claim | Verdict | Notes |
|-------|---------|-------|
| Mermaid flow diagram | **Partially Inaccurate** | Shows `tool.validateInput()` as step 1b between deny rules and checkPermissions — but in actual code, validateInput is called separately in the tool execution pipeline, NOT in the permission checking flow |
| PermissionMode list | **Accurate** | All 7 modes correctly listed including internal `auto` and `bubble` |
| Rule structure types | **Accurate** | Matches `src/types/permissions.ts` exactly |
| Rule matching patterns | **Accurate** | `Bash`, `Bash(git *)`, `mcp__server` all verified |
| YOLO Classifier two-stage | **Accurate** | Stage 1 (fast) + Stage 2 (thinking) confirmed in `YoloClassifierResult` |
| Denial tracking limits | **Accurate** | maxConsecutive: 3, maxTotal: 20 confirmed |
| 23 security checks claim | **Unverified** | Could not count exactly 23 in bashPermissions.ts; the number appears approximate |
| `shouldAvoidPermissionPrompts` for background agents | **Accurate** | Confirmed in multiple locations |
| Mode hierarchy "bypassPermissions > dontAsk > auto > acceptEdits > default > plan" | **Misleading** | These are not a strict hierarchy — they are separate mode values that trigger different code paths. The cascade logic in `hasPermissionsToUseToolInner` + post-processing is what determines effective behavior |

---

## 11. Key Corrections to Existing Analysis

### Critical Corrections

1. **Function name**: The tool-level permission check is `checkPermissions()`, NOT `userPermissionResult()`. The entry hook is `hasPermissionsToUseTool()`.

2. **Cascade order**: The permission cascade is NOT "mode check first, then rules". It is: **(1) deny rules → (2) ask rules → (3) tool.checkPermissions() → (4) mode bypass check → (5) allow rules → (6) passthrough→ask conversion**. Mode checks happen at step 4, AFTER tool-specific checks.

3. **Bypass is not absolute**: `bypassPermissions` mode is checked at step 2a, but steps 1d (tool deny), 1e (requiresUserInteraction), 1f (content-specific ask rules), and 1g (safety checks) all execute BEFORE bypass and can override it.

4. **Auto mode is not a simple classifier call**: The auto-mode path in the outer function is a complex pipeline with 6+ sub-checks before the YOLO classifier is even invoked (safetyCheck immunity, requiresUserInteraction guard, PowerShell guard, acceptEdits fast-path, denial tracking fallback, fail-closed GrowthBook gate).

5. **Interactive handler has 5 concurrent race paths**: Not just "show dialog, await user". The handler races user interaction, permission hooks, bash classifier, bridge (CCR/claude.ai), and channel (Telegram/iMessage) responses simultaneously via the `ResolveOnce` atomic guard.

### Minor Corrections

6. **`validateInput()` is NOT part of permission flow**: It's called separately in the tool execution pipeline before permission checking begins.

7. **Rule source priority**: Sources are not strictly ordered by priority. All rules from all sources are collected into flat arrays. The cascade order (deny checked before allow) is the actual priority mechanism, not source ordering.

8. **`passthrough` is a PermissionResult-only behavior**: Not present in `PermissionDecision`. It indicates "tool has no opinion" and gets converted to `ask` at step 3.

---

## 12. Complete Type Registry

### Core Types (from `src/types/permissions.ts`)

| Type | Values/Shape |
|------|-------------|
| `PermissionMode` | `'default' \| 'acceptEdits' \| 'plan' \| 'bypassPermissions' \| 'dontAsk' \| 'auto' \| 'bubble'` |
| `ExternalPermissionMode` | `'acceptEdits' \| 'bypassPermissions' \| 'default' \| 'dontAsk' \| 'plan'` |
| `PermissionBehavior` | `'allow' \| 'deny' \| 'ask'` |
| `PermissionRuleSource` | `'userSettings' \| 'projectSettings' \| 'localSettings' \| 'flagSettings' \| 'policySettings' \| 'cliArg' \| 'command' \| 'session'` |
| `PermissionDecisionReason.type` | `'rule' \| 'mode' \| 'hook' \| 'classifier' \| 'sandboxOverride' \| 'safetyCheck' \| 'workingDir' \| 'asyncAgent' \| 'subcommandResults' \| 'permissionPromptTool' \| 'other'` |
| `PermissionUpdateDestination` | `'userSettings' \| 'projectSettings' \| 'localSettings' \| 'session' \| 'cliArg'` |

---

## 13. Confidence Assessment

| Aspect | Score | Notes |
|--------|-------|-------|
| Core cascade logic | 9.5/10 | Read complete `hasPermissionsToUseToolInner` source |
| Post-processing (auto/dontAsk) | 9.0/10 | Read lines 479-598; complex feature-gated paths |
| Interactive handler race | 9.0/10 | Read full `interactiveHandler.ts` (536 lines) |
| Bash-specific permissions | 8.5/10 | Read entry + AST pipeline; full subcommand loop not traced |
| UI component dispatch | 9.0/10 | Read `permissionComponentForTool` mapping |
| Type system | 9.5/10 | Read complete `src/types/permissions.ts` |
| Existing analysis accuracy | 9.0/10 | Systematic comparison completed |
| **Overall** | **9.1/10** | Strong source-verified path trace |
