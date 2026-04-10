# Wave 32: Complete Tool Interface Member Inventory

> **Source**: `src/Tool.ts` (793 lines)
> **Wave**: 32 of Claude Code Source Study
> **Issue**: M-18 — Only 13 of ~46 members documented
> **Date**: 2026-04-01

## Overview

The `Tool<Input, Output, P>` type is the central interface for all tools in Claude Code. It is generic over three type parameters:

| Parameter | Constraint | Default | Purpose |
|-----------|-----------|---------|---------|
| `Input` | `extends AnyObject` | `AnyObject` | Zod schema for tool input |
| `Output` | (none) | `unknown` | Type of tool result data |
| `P` | `extends ToolProgressData` | `ToolProgressData` | Progress event payload type |

Where `AnyObject = z.ZodType<{ [key: string]: unknown }>`.

---

## Complete Member Inventory (46 members)

### Category: Core Identity (4 members)

| # | Member | Type | Default | Purpose |
|---|--------|------|---------|---------|
| 1 | `name` | `readonly string` | (required) | Primary tool name used for lookup and API registration. |
| 2 | `aliases` | `string[]` | `undefined` | Optional alternative names for backwards compatibility when a tool is renamed. |
| 3 | `searchHint` | `string` | `undefined` | One-line capability phrase (3-10 words) used by ToolSearch for keyword matching on deferred tools. |
| 4 | `inputSchema` | `readonly Input` | (required) | Zod schema that defines and validates the tool's input parameters. |

### Category: Schema & Validation (4 members)

| # | Member | Type | Default | Purpose |
|---|--------|------|---------|---------|
| 5 | `inputJSONSchema` | `readonly ToolInputJSONSchema` | `undefined` | Raw JSON Schema for MCP tools that specify input directly rather than converting from Zod. |
| 6 | `outputSchema` | `z.ZodType<unknown>` | `undefined` | Zod schema for output validation (optional; TODO comment notes plan to make required). |
| 7 | `inputsEquivalent` | `(a: z.infer<Input>, b: z.infer<Input>) => boolean` | `undefined` | Custom equality check for two inputs, used to detect duplicate/redundant tool calls. |
| 8 | `validateInput` | `(input, context) => Promise<ValidationResult>` | `undefined` | Pre-execution validation that can reject a tool call with an error message and code. |

### Category: Execution (2 members)

| # | Member | Type | Default | Purpose |
|---|--------|------|---------|---------|
| 9 | `call` | `(args, context, canUseTool, parentMessage, onProgress?) => Promise<ToolResult<Output>>` | (required) | The main execution function — runs the tool and returns its result. |
| 10 | `description` | `(input, options) => Promise<string>` | (required) | Generates the tool's description string, potentially varying by input and permission context. |

### Category: Permission & Security (4 members)

| # | Member | Type | Default | Purpose |
|---|--------|------|---------|---------|
| 11 | `checkPermissions` | `(input, context) => Promise<PermissionResult>` | **`{ behavior: 'allow', updatedInput: input }`** | Tool-specific permission logic, called after validateInput passes; general logic is in permissions.ts. |
| 12 | `toAutoClassifierInput` | `(input) => unknown` | **`''` (empty string)** | Returns a compact representation for the auto-mode security classifier; `''` means skip. |
| 13 | `preparePermissionMatcher` | `(input) => Promise<(pattern: string) => boolean>` | `undefined` | Factory for hook `if`-condition matchers (e.g. "Bash(git *)"); parsed once per hook-input pair. |
| 14 | `getPath` | `(input) => string` | `undefined` | Extracts the file path a tool operates on, used by permission and file-tracking systems. |

### Category: Behavioral Flags (8 members)

| # | Member | Type | Default | Purpose |
|---|--------|------|---------|---------|
| 15 | `isEnabled` | `() => boolean` | **`() => true`** | Whether the tool is currently available for use. |
| 16 | `isConcurrencySafe` | `(input) => boolean` | **`() => false`** | Whether concurrent execution with other tools is safe; false = assume NOT safe (fail-closed). |
| 17 | `isReadOnly` | `(input) => boolean` | **`() => false`** | Whether the tool only reads (no writes); false = assume it writes (fail-closed). |
| 18 | `isDestructive` | `(input) => boolean` | **`() => false`** | Whether the tool performs irreversible operations (delete, overwrite, send). |
| 19 | `isOpenWorld` | `(input) => boolean` | `undefined` | Whether the tool can access external/open-world resources beyond the local filesystem. |
| 20 | `requiresUserInteraction` | `() => boolean` | `undefined` | Whether the tool requires interactive user input to function. |
| 21 | `interruptBehavior` | `() => 'cancel' \| 'block'` | `undefined` (defaults to `'block'`) | What happens when the user submits a new message while this tool runs: cancel it or block the new message. |
| 22 | `isSearchOrReadCommand` | `(input) => { isSearch: boolean; isRead: boolean; isList?: boolean }` | `undefined` | Classifies the operation type for UI collapse: search (grep/find), read (cat/head), or list (ls/tree). |

### Category: MCP & Protocol (5 members)

| # | Member | Type | Default | Purpose |
|---|--------|------|---------|---------|
| 23 | `isMcp` | `boolean` | `undefined` | Marks the tool as originating from an MCP server. |
| 24 | `isLsp` | `boolean` | `undefined` | Marks the tool as originating from an LSP server. |
| 25 | `shouldDefer` | `readonly boolean` | `undefined` | When true, tool is deferred (sent with `defer_loading: true`) and requires ToolSearch before use. |
| 26 | `alwaysLoad` | `readonly boolean` | `undefined` | When true, tool is never deferred — full schema appears in initial prompt even with ToolSearch enabled. For MCP tools, set via `_meta['anthropic/alwaysLoad']`. |
| 27 | `mcpInfo` | `{ serverName: string; toolName: string }` | `undefined` | Original unnormalized MCP server and tool names; present on all MCP tools regardless of name prefixing. |

### Category: Result Handling (3 members)

| # | Member | Type | Default | Purpose |
|---|--------|------|---------|---------|
| 28 | `maxResultSizeChars` | `number` | (required) | Maximum character count before tool result is persisted to disk and replaced with a preview + file path. Set to `Infinity` for tools like Read that must never persist. |
| 29 | `strict` | `readonly boolean` | `undefined` | Enables strict mode causing the API to more strictly adhere to tool instructions and parameter schemas (only applied when tengu_tool_pear feature is enabled). |
| 30 | `mapToolResultToToolResultBlockParam` | `(content, toolUseID) => ToolResultBlockParam` | (required) | Converts the typed tool output into the Anthropic API's `ToolResultBlockParam` format for the message stream. |

### Category: Prompt & Description (2 members)

| # | Member | Type | Default | Purpose |
|---|--------|------|---------|---------|
| 31 | `prompt` | `(options) => Promise<string>` | (required) | Generates the tool's system prompt text, given permission context, agent definitions, and available tools. |
| 32 | `backfillObservableInput` | `(input: Record<string, unknown>) => void` | `undefined` | Mutates copies of tool_use input before observers see it (SDK stream, transcript, hooks); must be idempotent. Original API-bound input is never mutated to preserve prompt cache. |

### Category: Rendering — Names & Labels (5 members)

| # | Member | Type | Default | Purpose |
|---|--------|------|---------|---------|
| 33 | `userFacingName` | `(input) => string` | **`() => name`** | Human-readable tool name shown in the UI, potentially varying by input. |
| 34 | `userFacingNameBackgroundColor` | `(input) => keyof Theme \| undefined` | `undefined` | Optional theme key for the background color of the tool name badge in the UI. |
| 35 | `isTransparentWrapper` | `() => boolean` | `undefined` | When true, the tool (e.g. REPL) delegates all rendering to its progress handler and shows nothing itself. |
| 36 | `getToolUseSummary` | `(input) => string \| null` | `undefined` | Returns a short string summary of this tool use for compact views; null means don't display. |
| 37 | `getActivityDescription` | `(input) => string \| null` | `undefined` | Returns a present-tense activity description for spinner display (e.g. "Reading src/foo.ts"). |

### Category: Rendering — Messages (8 members)

| # | Member | Type | Default | Purpose |
|---|--------|------|---------|---------|
| 38 | `renderToolUseMessage` | `(input, options) => React.ReactNode` | (required) | Renders the tool use block (the "I'm calling tool X with Y" UI); input may be partial during streaming. |
| 39 | `renderToolResultMessage` | `(content, progressMessages, options) => React.ReactNode` | `undefined` | Renders the tool's result; when omitted the result renders nothing (e.g. TodoWrite updates a panel instead). |
| 40 | `renderToolUseProgressMessage` | `(progressMessages, options) => React.ReactNode` | `undefined` | Renders progress UI while the tool is running; when omitted no progress is shown. |
| 41 | `renderToolUseQueuedMessage` | `() => React.ReactNode` | `undefined` | Renders a message when the tool use is queued but not yet executing. |
| 42 | `renderToolUseRejectedMessage` | `(input, options) => React.ReactNode` | `undefined` | Custom rejection UI (e.g. showing rejected diff); falls back to `FallbackToolUseRejectedMessage`. |
| 43 | `renderToolUseErrorMessage` | `(result, options) => React.ReactNode` | `undefined` | Custom error UI (e.g. "File not found"); falls back to `FallbackToolUseErrorMessage`. |
| 44 | `renderToolUseTag` | `(input) => React.ReactNode` | `undefined` | Renders an optional tag after the tool use message for metadata like timeout, model, or resume ID. |
| 45 | `renderGroupedToolUse` | `(toolUses, options) => React.ReactNode \| null` | `undefined` | Renders multiple parallel instances of this tool as a group (non-verbose mode only); null falls back to individual rendering. |

### Category: Search & Transcript (2 members)

| # | Member | Type | Default | Purpose |
|---|--------|------|---------|---------|
| 46 | `extractSearchText` | `(out: Output) => string` | `undefined` | Returns flattened text of what renderToolResultMessage shows in transcript mode, for transcript search indexing; omitted means field-name heuristic in transcriptSearch.ts. |
| 47 | `isResultTruncated` | `(output: Output) => boolean` | `undefined` | Returns true when non-verbose rendering is truncated, gating the click-to-expand affordance in fullscreen. |

> **Note**: Total is 47 members (the original estimate of ~46 was approximate).

---

## Required vs Optional Members

### Always Required (9 members)
These must be provided in every `ToolDef` — `buildTool` does NOT supply defaults:

1. `name`
2. `inputSchema`
3. `call`
4. `description`
5. `prompt`
6. `maxResultSizeChars`
7. `mapToolResultToToolResultBlockParam`
8. `renderToolUseMessage`

> Note: `checkPermissions`, `isEnabled`, `isConcurrencySafe`, `isReadOnly`, `isDestructive`, `toAutoClassifierInput`, and `userFacingName` are also required on the final `Tool` type but are defaulted by `buildTool`.

### Defaulted by `buildTool` (7 members — `DefaultableToolKeys`)

| Member | Default Value | Design Rationale |
|--------|--------------|------------------|
| `isEnabled` | `() => true` | Tools are enabled by default. |
| `isConcurrencySafe` | `(_input?) => false` | **Fail-closed**: assume NOT safe for concurrent execution. |
| `isReadOnly` | `(_input?) => false` | **Fail-closed**: assume the tool writes. |
| `isDestructive` | `(_input?) => false` | Not destructive by default (low-risk default). |
| `checkPermissions` | `(input) => Promise.resolve({ behavior: 'allow', updatedInput: input })` | Defer to the general permission system in permissions.ts. |
| `toAutoClassifierInput` | `(_input?) => ''` | Skip classifier — security-relevant tools must override. |
| `userFacingName` | `() => def.name` | Falls back to the tool's primary `name`. |

### Fully Optional (31 members)
All remaining members are optional on both `ToolDef` and `Tool`. When absent, calling code checks for their existence (`tool.renderToolResultMessage?.(...)`).

---

## Key Types

### `ToolDef<Input, Output, P>`

```typescript
type ToolDef<Input, Output, P> =
  Omit<Tool<Input, Output, P>, DefaultableToolKeys> &
  Partial<Pick<Tool<Input, Output, P>, DefaultableToolKeys>>
```

The "input" type for `buildTool`. Same shape as `Tool` but makes the 7 defaultable methods optional. This is what individual tool files export before passing through `buildTool`.

### `BuiltTool<D>`

```typescript
type BuiltTool<D> = Omit<D, DefaultableToolKeys> & {
  [K in DefaultableToolKeys]-?: K extends keyof D
    ? undefined extends D[K]
      ? ToolDefaults[K]
      : D[K]
    : ToolDefaults[K]
}
```

Type-level mirror of `{ ...TOOL_DEFAULTS, ...def }`. Key behaviors:
- For each `DefaultableToolKeys` member: if `D` provides it as required, D's type wins; if D omits it or has it optional (from the `Partial<>` in the constraint), the default type fills in.
- All other keys come from `D` verbatim — **preserving arity, optional presence, and literal types exactly** as `satisfies Tool` formerly did.
- The `-?` modifier ensures all defaultable keys become required on the output.

### `ToolDefaults`

```typescript
type ToolDefaults = typeof TOOL_DEFAULTS
```

Inferred from the runtime `TOOL_DEFAULTS` object. Uses optional parameters (`_input?: unknown`) so both 0-arg and full-arg call sites type-check (tool stubs varied in arity).

### `Tools`

```typescript
type Tools = readonly Tool[]
```

A read-only collection type used instead of raw `Tool[]` to make it easier to track where tool sets are assembled, passed, and filtered.

---

## `buildTool()` Behavior

```typescript
export function buildTool<D extends AnyToolDef>(def: D): BuiltTool<D> {
  return {
    ...TOOL_DEFAULTS,
    userFacingName: () => def.name,  // special: uses def.name, not empty string
    ...def,
  } as BuiltTool<D>
}
```

### Execution semantics

1. **Spread `TOOL_DEFAULTS` first** — all 7 defaults are placed as a base layer.
2. **Override `userFacingName`** — replaced with `() => def.name` (the TOOL_DEFAULTS has `() => ''` but buildTool overrides this with the actual tool name).
3. **Spread `def` last** — any member the tool definition provides overwrites the default.
4. **Cast to `BuiltTool<D>`** — the `as` bridges the structural-any constraint and the precise return type.

### Design principles

- **Fail-closed by default**: `isConcurrencySafe` defaults to `false` (assume unsafe), `isReadOnly` defaults to `false` (assume writes). Security-sensitive tools MUST override `toAutoClassifierInput`.
- **Literal type preservation**: `BuiltTool<D>` preserves the exact literal types from D's definition — this is why tools previously used `satisfies Tool` and why the migration to `buildTool` was safe.
- **Single source of truth**: All 60+ tools go through `buildTool`, so defaults live in one place and callers never need `tool.isEnabled?.() ?? true`.

---

## Supporting Types

### `ValidationResult`

```typescript
type ValidationResult =
  | { result: true }
  | { result: false; message: string; errorCode: number }
```

### `ToolResult<T>`

```typescript
type ToolResult<T> = {
  data: T
  newMessages?: (UserMessage | AssistantMessage | AttachmentMessage | SystemMessage)[]
  contextModifier?: (context: ToolUseContext) => ToolUseContext  // only honored for non-concurrency-safe tools
  mcpMeta?: { _meta?: Record<string, unknown>; structuredContent?: Record<string, unknown> }
}
```

### `ToolProgress<P>`

```typescript
type ToolProgress<P extends ToolProgressData> = {
  toolUseID: string
  data: P
}
```

### `ToolCallProgress<P>`

```typescript
type ToolCallProgress<P> = (progress: ToolProgress<P>) => void
```

### `ToolInputJSONSchema`

```typescript
type ToolInputJSONSchema = {
  [x: string]: unknown
  type: 'object'
  properties?: { [x: string]: unknown }
}
```

---

## Member Count Summary

| Category | Count | Required | Defaulted | Optional |
|----------|-------|----------|-----------|----------|
| Core Identity | 4 | 2 | 0 | 2 |
| Schema & Validation | 4 | 1 | 0 | 3 |
| Execution | 2 | 2 | 0 | 0 |
| Permission & Security | 4 | 0 | 2 | 2 |
| Behavioral Flags | 8 | 0 | 3 | 5 |
| MCP & Protocol | 5 | 0 | 0 | 5 |
| Result Handling | 3 | 2 | 0 | 1 |
| Prompt & Description | 2 | 1 | 0 | 1 |
| Rendering — Names | 5 | 0 | 1 | 4 |
| Rendering — Messages | 8 | 1 | 0 | 7 |
| Search & Transcript | 2 | 0 | 0 | 2 |
| **Total** | **47** | **9** | **7** (+1 special) | **31** |

---

## Comparison with Previous Documentation (M-18)

The previous Wave 5 documentation (`wave5-types-batch1-tool-task.md`) covered only 13 members. This inventory adds 34 previously undocumented members:

- **Newly documented**: `aliases`, `searchHint`, `inputJSONSchema`, `outputSchema`, `inputsEquivalent`, `validateInput`, `isDestructive`, `interruptBehavior`, `isSearchOrReadCommand`, `isOpenWorld`, `requiresUserInteraction`, `isMcp`, `isLsp`, `shouldDefer`, `alwaysLoad`, `mcpInfo`, `maxResultSizeChars`, `strict`, `backfillObservableInput`, `preparePermissionMatcher`, `getPath`, `userFacingNameBackgroundColor`, `isTransparentWrapper`, `getToolUseSummary`, `getActivityDescription`, `renderToolUseProgressMessage`, `renderToolUseQueuedMessage`, `renderToolUseRejectedMessage`, `renderToolUseErrorMessage`, `renderToolUseTag`, `renderGroupedToolUse`, `extractSearchText`, `isResultTruncated`, `toAutoClassifierInput`
- **`buildTool()` and `BuiltTool<D>`**: Fully documented for the first time
- **`TOOL_DEFAULTS`**: All 7 defaults with rationale
- **`ToolDef`**: Relationship to `Tool` type explained

---

*Wave 32 complete. Issue M-18 resolved: 47/47 members documented.*
