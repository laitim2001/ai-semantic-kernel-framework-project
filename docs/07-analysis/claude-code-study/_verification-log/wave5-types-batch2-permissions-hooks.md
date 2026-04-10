# Wave 5 — Type Signature Verification: Permissions & Hooks (Batch 2)

> Source-verified against `CC-Source/src/types/permissions.ts`, `CC-Source/src/types/hooks.ts`, `CC-Source/src/types/ids.ts`, and `CC-Source/src/entrypoints/sdk/coreSchemas.ts`.
> Date: 2026-04-01 | Verifier: Claude Opus 4.6

## 1. Source File Inventory

| File | Lines | Types Defined | Constants |
|------|-------|---------------|-----------|
| `src/types/permissions.ts` | 441 | 22 types | 4 const arrays |
| `src/types/hooks.ts` | 291 | 13 types + 4 Zod schemas + 3 type guards | 0 const |
| `src/types/ids.ts` | 44 | 2 branded types + 3 functions | 1 regex |
| `src/entrypoints/sdk/coreTypes.ts` | 63 | re-exports | 2 const arrays (HOOK_EVENTS, EXIT_REASONS) |
| `src/entrypoints/sdk/coreSchemas.ts` | ~975 | 27+ HookInput schemas, HookJSONOutput schemas | HOOK_EVENTS (27 events) |

---

## 2. Permission Types — Full Extraction

### 2.1 Permission Modes

```typescript
// External (user-configurable)
const EXTERNAL_PERMISSION_MODES = ['acceptEdits', 'bypassPermissions', 'default', 'dontAsk', 'plan'] as const
type ExternalPermissionMode = (typeof EXTERNAL_PERMISSION_MODES)[number]

// Internal (extends external)
type InternalPermissionMode = ExternalPermissionMode | 'auto' | 'bubble'
type PermissionMode = InternalPermissionMode  // alias

// Runtime set — feature-gated 'auto' via bun:bundle feature flag
const INTERNAL_PERMISSION_MODES = [
  ...EXTERNAL_PERMISSION_MODES,
  ...(feature('TRANSCRIPT_CLASSIFIER') ? (['auto'] as const) : ([] as const)),
] as const satisfies readonly PermissionMode[]
const PERMISSION_MODES = INTERNAL_PERMISSION_MODES  // alias
```

### 2.2 Permission Behavior & Rules

```typescript
type PermissionBehavior = 'allow' | 'deny' | 'ask'

type PermissionRuleSource =
  | 'userSettings' | 'projectSettings' | 'localSettings'
  | 'flagSettings' | 'policySettings' | 'cliArg' | 'command' | 'session'

type PermissionRuleValue = { toolName: string; ruleContent?: string }

type PermissionRule = {
  source: PermissionRuleSource
  ruleBehavior: PermissionBehavior
  ruleValue: PermissionRuleValue
}
```

### 2.3 Permission Updates (6-variant discriminated union)

```typescript
type PermissionUpdateDestination =
  | 'userSettings' | 'projectSettings' | 'localSettings' | 'session' | 'cliArg'

type PermissionUpdate =
  | { type: 'addRules'; destination: PermissionUpdateDestination; rules: PermissionRuleValue[]; behavior: PermissionBehavior }
  | { type: 'replaceRules'; destination: PermissionUpdateDestination; rules: PermissionRuleValue[]; behavior: PermissionBehavior }
  | { type: 'removeRules'; destination: PermissionUpdateDestination; rules: PermissionRuleValue[]; behavior: PermissionBehavior }
  | { type: 'setMode'; destination: PermissionUpdateDestination; mode: ExternalPermissionMode }
  | { type: 'addDirectories'; destination: PermissionUpdateDestination; directories: string[] }
  | { type: 'removeDirectories'; destination: PermissionUpdateDestination; directories: string[] }
```

### 2.4 Working Directory Types

```typescript
type WorkingDirectorySource = PermissionRuleSource  // alias for semantic clarity
type AdditionalWorkingDirectory = { path: string; source: WorkingDirectorySource }
```

### 2.5 Permission Decisions (Generic, 3-variant + passthrough)

```typescript
type PermissionCommandMetadata = { name: string; description?: string; [key: string]: unknown }
type PermissionMetadata = { command: PermissionCommandMetadata } | undefined

type PermissionAllowDecision<Input extends Record<string, unknown> = Record<string, unknown>> = {
  behavior: 'allow'
  updatedInput?: Input
  userModified?: boolean
  decisionReason?: PermissionDecisionReason
  toolUseID?: string
  acceptFeedback?: string
  contentBlocks?: ContentBlockParam[]
}

type PendingClassifierCheck = { command: string; cwd: string; descriptions: string[] }

type PermissionAskDecision<Input extends Record<string, unknown> = Record<string, unknown>> = {
  behavior: 'ask'
  message: string
  updatedInput?: Input
  decisionReason?: PermissionDecisionReason
  suggestions?: PermissionUpdate[]
  blockedPath?: string
  metadata?: PermissionMetadata
  isBashSecurityCheckForMisparsing?: boolean
  pendingClassifierCheck?: PendingClassifierCheck
  contentBlocks?: ContentBlockParam[]
}

type PermissionDenyDecision = {
  behavior: 'deny'
  message: string
  decisionReason: PermissionDecisionReason  // NOTE: required, not optional
  toolUseID?: string
}

type PermissionDecision<Input> = PermissionAllowDecision<Input> | PermissionAskDecision<Input> | PermissionDenyDecision

type PermissionResult<Input> = PermissionDecision<Input> | {
  behavior: 'passthrough'
  message: string
  decisionReason?: PermissionDecision<Input>['decisionReason']
  suggestions?: PermissionUpdate[]
  blockedPath?: string
  pendingClassifierCheck?: PendingClassifierCheck
}
```

### 2.6 Permission Decision Reason (10-variant discriminated union)

```typescript
type PermissionDecisionReason =
  | { type: 'rule'; rule: PermissionRule }
  | { type: 'mode'; mode: PermissionMode }
  | { type: 'subcommandResults'; reasons: Map<string, PermissionResult> }
  | { type: 'permissionPromptTool'; permissionPromptToolName: string; toolResult: unknown }
  | { type: 'hook'; hookName: string; hookSource?: string; reason?: string }
  | { type: 'asyncAgent'; reason: string }
  | { type: 'sandboxOverride'; reason: 'excludedCommand' | 'dangerouslyDisableSandbox' }
  | { type: 'classifier'; classifier: string; reason: string }
  | { type: 'workingDir'; reason: string }
  | { type: 'safetyCheck'; reason: string; classifierApprovable: boolean }
  | { type: 'other'; reason: string }
```

### 2.7 Classifier Types

```typescript
type ClassifierResult = { matches: boolean; matchedDescription?: string; confidence: 'high' | 'medium' | 'low'; reason: string }
type ClassifierBehavior = 'deny' | 'ask' | 'allow'
type ClassifierUsage = { inputTokens: number; outputTokens: number; cacheReadInputTokens: number; cacheCreationInputTokens: number }

type YoloClassifierResult = {
  thinking?: string; shouldBlock: boolean; reason: string; unavailable?: boolean
  transcriptTooLong?: boolean; model: string; usage?: ClassifierUsage; durationMs?: number
  promptLengths?: { systemPrompt: number; toolCalls: number; userPrompts: number }
  errorDumpPath?: string; stage?: 'fast' | 'thinking'
  stage1Usage?: ClassifierUsage; stage1DurationMs?: number; stage1RequestId?: string; stage1MsgId?: string
  stage2Usage?: ClassifierUsage; stage2DurationMs?: number; stage2RequestId?: string; stage2MsgId?: string
}
```

### 2.8 Permission Explainer

```typescript
type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH'
type PermissionExplanation = { riskLevel: RiskLevel; explanation: string; reasoning: string; risk: string }
```

### 2.9 ToolPermissionContext

```typescript
type ToolPermissionRulesBySource = { [T in PermissionRuleSource]?: string[] }

type ToolPermissionContext = {
  readonly mode: PermissionMode
  readonly additionalWorkingDirectories: ReadonlyMap<string, AdditionalWorkingDirectory>
  readonly alwaysAllowRules: ToolPermissionRulesBySource
  readonly alwaysDenyRules: ToolPermissionRulesBySource
  readonly alwaysAskRules: ToolPermissionRulesBySource
  readonly isBypassPermissionsModeAvailable: boolean
  readonly strippedDangerousRules?: ToolPermissionRulesBySource
  readonly shouldAvoidPermissionPrompts?: boolean
  readonly awaitAutomatedChecksBeforeDialog?: boolean
  readonly prePlanMode?: PermissionMode
}
```

---

## 3. Hook Types — Full Extraction

### 3.1 Hook Events (27 events from SDK)

```typescript
// From src/entrypoints/sdk/coreTypes.ts
const HOOK_EVENTS = [
  'PreToolUse', 'PostToolUse', 'PostToolUseFailure', 'Notification',
  'UserPromptSubmit', 'SessionStart', 'SessionEnd', 'Stop', 'StopFailure',
  'SubagentStart', 'SubagentStop', 'PreCompact', 'PostCompact',
  'PermissionRequest', 'PermissionDenied', 'Setup', 'TeammateIdle',
  'TaskCreated', 'TaskCompleted', 'Elicitation', 'ElicitationResult',
  'ConfigChange', 'WorktreeCreate', 'WorktreeRemove', 'InstructionsLoaded',
  'CwdChanged', 'FileChanged',
] as const

type HookEvent = (typeof HOOK_EVENTS)[number]  // inferred from schema
```

### 3.2 Base Hook Input (from SDK coreSchemas.ts)

```typescript
// BaseHookInputSchema fields:
{
  session_id: string
  transcript_path: string
  cwd: string
  permission_mode?: string
  agent_id?: string    // present only in subagent context
  agent_type?: string  // present in subagent or --agent sessions
}
```

HookInput is a 27-variant discriminated union (on `hook_event_name`) with `.and()` extensions per event type.

### 3.3 Hook Callback Types

```typescript
type HookCallbackContext = {
  getAppState: () => AppState
  updateAttributionState: (updater: (prev: AttributionState) => AttributionState) => void
}

type HookCallback = {
  type: 'callback'
  callback: (input: HookInput, toolUseID: string | null, abort: AbortSignal | undefined,
             hookIndex?: number, context?: HookCallbackContext) => Promise<HookJSONOutput>
  timeout?: number    // seconds
  internal?: boolean  // exclude from metrics
}

type HookCallbackMatcher = { matcher?: string; hooks: HookCallback[]; pluginName?: string }
```

### 3.4 Hook Progress & Errors

```typescript
type HookProgress = { type: 'hook_progress'; hookEvent: HookEvent; hookName: string; command: string; promptText?: string; statusMessage?: string }
type HookBlockingError = { blockingError: string; command: string }
```

### 3.5 Permission Request Result (from hooks)

```typescript
type PermissionRequestResult =
  | { behavior: 'allow'; updatedInput?: Record<string, unknown>; updatedPermissions?: PermissionUpdate[] }
  | { behavior: 'deny'; message?: string; interrupt?: boolean }
```

### 3.6 HookResult

```typescript
type HookResult = {
  message?: Message
  systemMessage?: Message
  blockingError?: HookBlockingError
  outcome: 'success' | 'blocking' | 'non_blocking_error' | 'cancelled'
  preventContinuation?: boolean
  stopReason?: string
  permissionBehavior?: 'ask' | 'deny' | 'allow' | 'passthrough'
  hookPermissionDecisionReason?: string
  additionalContext?: string
  initialUserMessage?: string
  updatedInput?: Record<string, unknown>
  updatedMCPToolOutput?: unknown
  permissionRequestResult?: PermissionRequestResult
  retry?: boolean
}
```

### 3.7 AggregatedHookResult

```typescript
type AggregatedHookResult = {
  message?: Message
  blockingErrors?: HookBlockingError[]
  preventContinuation?: boolean
  stopReason?: string
  hookPermissionDecisionReason?: string
  permissionBehavior?: PermissionResult['behavior']  // NOTE: uses PermissionResult from utils/permissions/
  additionalContexts?: string[]
  initialUserMessage?: string
  updatedInput?: Record<string, unknown>
  updatedMCPToolOutput?: unknown
  permissionRequestResult?: PermissionRequestResult
  retry?: boolean
}
```

### 3.8 Prompt Elicitation Protocol

```typescript
// Zod-defined (promptRequestSchema)
type PromptRequest = {
  prompt: string       // request ID (discriminator)
  message: string
  options: Array<{ key: string; label: string; description?: string }>
}

type PromptResponse = { prompt_response: string; selected: string }
```

### 3.9 Hook JSON Output (Zod + compile-time assertion)

```typescript
// AsyncHookJSONOutput
{ async: true; asyncTimeout?: number }

// SyncHookJSONOutput — hookSpecificOutput is a 16-variant discriminated union on hookEventName:
//   PreToolUse, UserPromptSubmit, SessionStart, Setup, SubagentStart,
//   PostToolUse, PostToolUseFailure, PermissionDenied, Notification,
//   PermissionRequest, Elicitation, ElicitationResult, CwdChanged,
//   FileChanged, WorktreeCreate

// HookJSONOutput = AsyncHookJSONOutput | SyncHookJSONOutput

// Compile-time assertion:
type _assertSDKTypesMatch = Assert<IsEqual<SchemaHookJSONOutput, HookJSONOutput>>
```

---

## 4. Branded ID Types (src/types/ids.ts)

```typescript
type SessionId = string & { readonly __brand: 'SessionId' }
type AgentId = string & { readonly __brand: 'AgentId' }

function asSessionId(id: string): SessionId       // unsafe cast
function asAgentId(id: string): AgentId           // unsafe cast
function toAgentId(s: string): AgentId | null     // validated: /^a(?:.+-)?[0-9a-f]{16}$/
```

---

## 5. Verification Against Existing Analysis

### 5.1 permission-system.md — Discrepancies Found

| # | Claim in Analysis | Source Truth | Severity |
|---|-------------------|-------------|----------|
| 1 | Lists 5 external modes | **Correct** — 5 modes: acceptEdits, bypassPermissions, default, dontAsk, plan | OK |
| 2 | Lists 2 internal modes (auto, bubble) | **Correct** | OK |
| 3 | `ToolPermissionContext` uses `DeepImmutable<{...}>` wrapper | **WRONG** — Source uses direct `readonly` on each field + `ReadonlyMap`, NOT `DeepImmutable`. The comment says "simplified DeepImmutable approximation for this types-only file" | MEDIUM |
| 4 | Shows `isAutoModeAvailable?: boolean` field on ToolPermissionContext | **WRONG** — This field does NOT exist in source. Source has `isBypassPermissionsModeAvailable` (required) only | MEDIUM |
| 5 | Lists 10 PermissionDecisionReason variants | **WRONG** — Source has **11 variants** (missing `permissionPromptTool` variant from analysis table) | MEDIUM |
| 6 | `flagSettings` listed as PermissionRuleSource | Present in source but **missing from analysis table** (table shows 7 sources, source has 8) | LOW |
| 7 | PermissionUpdate shows 6 variants | **Correct** | OK |
| 8 | YoloClassifierResult fields | Analysis is abbreviated but accurate for shown fields. Missing: `stage1MsgId`, `stage2MsgId`, `stage1RequestId`, `stage2RequestId`, `errorDumpPath` | LOW |
| 9 | Hook event count: "16 hook event types" | **WRONG** — SDK defines **27 hook events**. Analysis is severely outdated | HIGH |

### 5.2 hook-system.md — Discrepancies Found

| # | Claim in Analysis | Source Truth | Severity |
|---|-------------------|-------------|----------|
| 1 | "16 hook event types" listed | **WRONG** — Source has 27 events. Missing: SessionEnd, Stop, StopFailure, SubagentStop, PreCompact, PostCompact, TeammateIdle, TaskCreated, TaskCompleted, ConfigChange, InstructionsLoaded, WorktreeRemove | HIGH |
| 2 | HookCallback type signature | **Correct** — matches source exactly | OK |
| 3 | HookCallbackMatcher | **Correct** | OK |
| 4 | SyncHookJSONOutput schema | Analysis shows "13 hook event types" in hookSpecificOutput | **WRONG** — Source Zod schema has **16 variants** in hookSpecificOutput (hooks.ts local schema). SDK has separate 27-event HookInput | HIGH |
| 5 | HookResult fields | Analysis shows 12 fields | **WRONG** — Missing `systemMessage`, `updatedMCPToolOutput`, `permissionRequestResult` fields. Source has **15 fields** | MEDIUM |
| 6 | AggregatedHookResult fields | Analysis shows 11 fields | **WRONG** — Missing `updatedMCPToolOutput`, `permissionRequestResult`. Source has **12 fields** | MEDIUM |
| 7 | HookProgress type | **Correct** | OK |
| 8 | PromptRequest/PromptResponse | **Correct** | OK |
| 9 | Compile-time type assertion pattern | **Correct** | OK |
| 10 | BaseHookInput fields | Not documented in hook-system.md | GAP |

### 5.3 type-system.md — Discrepancies Found

| # | Claim in Analysis | Source Truth | Severity |
|---|-------------------|-------------|----------|
| 1 | `ToolPermissionContext = DeepImmutable<{...}>` | **WRONG** — Same issue as permission-system.md. Source uses `readonly` directly, not `DeepImmutable` wrapper | MEDIUM |
| 2 | Shows `isAutoModeAvailable?: boolean` field | **WRONG** — Does not exist in source | MEDIUM |
| 3 | PermissionRuleSource lists 8 values | **Correct** — matches source exactly | OK |
| 4 | Permission mode feature-gating pattern | **Correct** — accurately describes `satisfies` + `feature()` pattern | OK |
| 5 | Branded ID types (SessionId, AgentId) | **Correct** but analysis in type-system.md only mentions them briefly | LOW |
| 6 | `toAgentId` validation function | **Not documented** — only `asSessionId`/`asAgentId` mentioned implicitly | LOW |

---

## 6. Discrepancy Summary

| Severity | Count | Key Issues |
|----------|-------|------------|
| **HIGH** | 3 | Hook event count (27 not 16), hookSpecificOutput variants (16 not 13), HookInput schema underdocumented |
| **MEDIUM** | 6 | DeepImmutable vs readonly (x2), phantom `isAutoModeAvailable` field (x2), missing PermissionDecisionReason variant, missing HookResult fields |
| **LOW** | 4 | Missing flagSettings from table, YoloClassifierResult field gaps, toAgentId undocumented, branded types under-described |
| **OK** | 12 | Verified correct |

### Accuracy Score

- **permission-system.md**: 7/10 — Core structure correct, but ToolPermissionContext has phantom field, DeepImmutable claim wrong, missing decision reason variant, hook event count severely wrong
- **hook-system.md**: 5.5/10 — Hook event count severely outdated (16 vs 27), HookResult/AggregatedHookResult missing fields, hookSpecificOutput variant count wrong
- **type-system.md**: 7.5/10 — Good pattern documentation, but inherits same ToolPermissionContext errors

### Combined Wave 5 Batch 2 Score: **6.7/10**

---

## 7. Correction Recommendations

### Priority 1 (HIGH — Factual errors)
1. Update hook event count from 16 to **27** in both hook-system.md and permission-system.md
2. Add missing 12 hook events: `SessionEnd`, `Stop`, `StopFailure`, `SubagentStop`, `PreCompact`, `PostCompact`, `TeammateIdle`, `TaskCreated`, `TaskCompleted`, `ConfigChange`, `InstructionsLoaded`, `WorktreeRemove`
3. Update hookSpecificOutput variant count to **16** (in hooks.ts local Zod schema)
4. Document BaseHookInput schema fields (session_id, transcript_path, cwd, permission_mode?, agent_id?, agent_type?)

### Priority 2 (MEDIUM — Field-level corrections)
5. Fix ToolPermissionContext: remove `DeepImmutable<>` wrapper claim, show direct `readonly` + `ReadonlyMap` usage
6. Remove phantom `isAutoModeAvailable` field from ToolPermissionContext
7. Add `permissionPromptTool` variant to PermissionDecisionReason documentation
8. Add missing HookResult fields: `systemMessage`, `updatedMCPToolOutput`, `permissionRequestResult`
9. Add missing AggregatedHookResult fields: `updatedMCPToolOutput`, `permissionRequestResult`

### Priority 3 (LOW — Completeness)
10. Add `flagSettings` to PermissionRuleSource table in permission-system.md
11. Document `toAgentId()` validation function with regex pattern
12. Expand YoloClassifierResult to include stage request/message ID fields
