# Wave 4 Path 2: Tool Invocation Flow — Source-Verified Trace

> Verification Date: 2026-04-01 | Verifier: Claude Opus 4.6 (1M) | Quality Target: 9.0+/10
> Source Files: query.ts, Tool.ts, tools.ts, toolExecution.ts, StreamingToolExecutor.ts, FileEditTool.ts

---

## 1. End-to-End Tool Invocation Sequence

When the Claude API returns a `tool_use` content block, the following chain executes:

```
API SSE stream (tool_use block)
  │
  ▼
query.ts L829-834: detect tool_use blocks in assistant message
  │
  ├─ Streaming mode (L562-567): StreamingToolExecutor.addTool()
  │     └─ StreamingToolExecutor.ts L76: findToolByName() + queue
  │     └─ StreamingToolExecutor.ts L144: executeTool() via processQueue()
  │           └─ calls runToolUse() from toolExecution.ts L11
  │
  └─ Legacy mode: batched after stream ends (L1012-1029)
        └─ also calls runToolUse()
  │
  ▼
toolExecution.ts L337-490: runToolUse()
  │
  ├─ L345: findToolByName(tools, name) — lookup by name or alias
  ├─ L369-411: unknown tool → yield error tool_result
  ├─ L415-453: aborted → yield cancel tool_result
  └─ L455-468: delegate to streamedCheckPermissionsAndCallTool()
        │
        ▼
toolExecution.ts L492-570: streamedCheckPermissionsAndCallTool()
  │  Wraps async flow in Stream<MessageUpdateLazy> for progress events
  │
  ▼
toolExecution.ts L599-1588: checkPermissionsAndCallTool()
  │
  ├─ L615-680: Zod schema validation (inputSchema.safeParse)
  ├─ L683-733: Tool-specific validateInput()
  ├─ L800-862: runPreToolUseHooks()
  ├─ L921-931: resolveHookPermissionDecision() → canUseTool
  ├─ L995-1103: DENY path → error tool_result + hooks
  ├─ L1130-1132: updatedInput from permission decision
  ├─ L1207-1222: tool.call(callInput, context, canUseTool, assistantMessage, onProgress)
  ├─ L1292-1295: tool.mapToolResultToToolResultBlockParam()
  ├─ L1403-1474: addToolResult() → processToolResultBlock → createUserMessage
  ├─ L1483-1531: runPostToolUseHooks()
  └─ L1589-end: catch → error tool_result with formatted error
```

---

## 2. Key Functions and Their Signatures

### 2.1 Tool Lookup — `findToolByName` (Tool.ts L358-360)

```typescript
export function findToolByName(tools: Tools, name: string): Tool | undefined {
  return tools.find(t => toolMatchesName(t, name))
}
```

`toolMatchesName` (Tool.ts L348-353) checks both `tool.name` and `tool.aliases`:

```typescript
export function toolMatchesName(
  tool: { name: string; aliases?: string[] },
  name: string,
): boolean {
  return tool.name === name || (tool.aliases?.includes(name) ?? false)
}
```

### 2.2 Tool Registration — `getTools` / `assembleToolPool` (tools.ts)

- **`getAllBaseTools()`** (L193-251): Returns the master list of ~40+ built-in tools. Feature-gated tools are conditionally included via `feature()` and `process.env` checks.
- **`getTools(permissionContext)`** (L271-327): Filters by deny rules, REPL mode hiding, and `isEnabled()`.
- **`assembleToolPool(permissionContext, mcpTools)`** (L345-367): Merges built-in + MCP tools, deduplicates by name (built-ins win), sorts for prompt-cache stability.

### 2.3 Tool Interface — `Tool` type (Tool.ts L362-695)

Critical methods in the invocation path:

| Method | Signature | Purpose |
|--------|-----------|---------|
| `call()` | `(args, context, canUseTool, parentMessage, onProgress?) → Promise<ToolResult<Output>>` | Execute the tool (L379-385) |
| `validateInput()` | `(input, context) → Promise<ValidationResult>` | Tool-specific input validation (L489-493) |
| `checkPermissions()` | `(input, context) → Promise<PermissionResult>` | Tool-specific permission logic (L500-503) |
| `mapToolResultToToolResultBlockParam()` | `(content, toolUseID) → ToolResultBlockParam` | Convert output to API format (L557-559) |
| `inputSchema` | `z.ZodType` | Zod schema for input validation |
| `isConcurrencySafe()` | `(input) → boolean` | Whether tool can run in parallel |
| `backfillObservableInput()` | `(input) → void` | Add legacy/derived fields for hooks/SDK |

### 2.4 `ToolResult<T>` (Tool.ts L321-336)

```typescript
export type ToolResult<T> = {
  data: T                                    // Tool output data
  newMessages?: (UserMessage | ...)[]        // Additional messages to inject
  contextModifier?: (ctx) => ToolUseContext   // Modify context for next tool
  mcpMeta?: { _meta?, structuredContent? }   // MCP protocol metadata
}
```

### 2.5 `buildTool` Factory (Tool.ts L783-792)

All tools use `buildTool(def)` which spreads `TOOL_DEFAULTS` (L757-769) under the definition:
- `isEnabled` defaults to `() => true`
- `isConcurrencySafe` defaults to `() => false` (fail-closed)
- `isReadOnly` defaults to `() => false`
- `checkPermissions` defaults to `Promise.resolve({ behavior: 'allow', updatedInput: input })`

---

## 3. StreamingToolExecutor — Concurrency Engine

**File**: `src/services/tools/StreamingToolExecutor.ts`

### 3.1 Architecture (L39-61)

```typescript
export class StreamingToolExecutor {
  private tools: TrackedTool[] = []          // Ordered queue
  private siblingAbortController: AbortController  // Child of parent's AC
}
```

Each `TrackedTool` (L18-31) tracks: `id`, `block`, `status` (queued|executing|completed|yielded), `isConcurrencySafe`, `promise`, `results`.

### 3.2 Concurrency Rules (L128-134)

```typescript
private canExecuteTool(isConcurrencySafe: boolean): boolean {
  const executingTools = this.tools.filter(t => t.status === 'executing')
  return (
    executingTools.length === 0 ||
    (isConcurrencySafe && executingTools.every(t => t.isConcurrencySafe))
  )
}
```

- Concurrent-safe tools run in parallel with each other
- Non-concurrent tools get exclusive access (no other tools running)
- Results are yielded in arrival order (L851: `getCompletedResults()`)

### 3.3 Tool Addition Flow (L75-123)

1. `addTool(block, assistantMessage)` called from query.ts L842
2. `findToolByName()` — unknown tool → immediate error result
3. Parse input with `inputSchema.safeParse()` to determine concurrency safety
4. Push to queue → `processQueue()` starts execution when conditions allow

### 3.4 Error Propagation (L152-200)

On sibling error, streaming fallback, or user interrupt, synthetic error `tool_result` messages are created via `createSyntheticErrorMessage()`.

---

## 4. Concrete Tool Trace: FileEditTool

**File**: `src/tools/FileEditTool/FileEditTool.ts`

### 4.1 Registration

```typescript
export const FileEditTool = buildTool({
  name: FILE_EDIT_TOOL_NAME,   // "Edit" (from constants.ts)
  strict: true,                 // Strict JSON schema enforcement
  maxResultSizeChars: 100_000,
  // ...
})
```

### 4.2 Permission Check — `checkPermissions` (L125-132)

```typescript
async checkPermissions(input, context): Promise<PermissionDecision> {
  return checkWritePermissionForTool(FileEditTool, input, appState.toolPermissionContext)
}
```

Delegates to `utils/permissions/filesystem.ts`.

### 4.3 Input Validation — `validateInput` (L137-386)

Multi-stage validation:
1. **L148**: `old_string === new_string` → reject (no-op edit)
2. **L160-174**: Check deny rules for file path
3. **L179-181**: UNC path security guard (prevents NTLM credential leaks)
4. **L186-200**: File size check (max 1 GiB)
5. **L224-246**: File existence check + similar file suggestion
6. **L266-273**: Jupyter notebook redirect to NotebookEditTool
7. **L275-287**: Read-before-write enforcement (`readFileState` check)
8. **L290-311**: Staleness detection (modification timestamp + content comparison on Windows)
9. **L316-340+**: `findActualString()` for quote normalization + uniqueness check

### 4.4 `call()` Method (L387-574)

Complete execution sequence:

| Step | Line | Action |
|------|------|--------|
| 1 | L402 | `expandPath(file_path)` → absolute path |
| 2 | L407-423 | Discover skills from file path (fire-and-forget) |
| 3 | L425 | `diagnosticTracker.beforeFileEdited()` |
| 4 | L430 | `fs.mkdir(dirname)` — ensure parent directory |
| 5 | L431-440 | `fileHistoryTrackEdit()` — backup pre-edit content |
| 6 | L444-449 | `readFileForEdit()` — synchronous read for atomicity |
| 7 | L451-468 | Staleness re-check (race condition guard) |
| 8 | L471-472 | `findActualString()` — quote normalization |
| 9 | L475-479 | `preserveQuoteStyle()` for new_string |
| 10 | L482-488 | `getPatchForEdit()` — generate unified diff |
| 11 | L491 | `writeTextContent()` — atomic write to disk |
| 12 | L494-514 | LSP notification (didChange + didSave) |
| 13 | L517 | VSCode diff view notification |
| 14 | L520-525 | Update `readFileState` with new content + timestamp |
| 15 | L561-573 | Return `ToolResult<FileEditOutput>` with patch data |

### 4.5 Result Mapping — `mapToolResultToToolResultBlockParam` (L575-594)

Converts `FileEditOutput` to a simple text `ToolResultBlockParam`:
```
"The file {filePath} has been updated successfully."
```
With optional notes for `userModified` and `replaceAll`.

---

## 5. Data Transformations Summary

```
API tool_use block { type, id, name, input }
  │
  ▼ findToolByName() → Tool instance
  │
  ▼ inputSchema.safeParse(input) → typed ParsedInput (Zod)
  │
  ▼ tool.validateInput(parsedInput) → ValidationResult
  │
  ▼ runPreToolUseHooks() → possible input modification
  │
  ▼ resolveHookPermissionDecision() → PermissionDecision { behavior, updatedInput }
  │
  ▼ tool.call(callInput, context) → ToolResult<Output> { data, newMessages?, contextModifier? }
  │
  ▼ tool.mapToolResultToToolResultBlockParam(data, toolUseID) → ToolResultBlockParam
  │
  ▼ processToolResultBlock() → size-limited, possibly persisted to disk
  │
  ▼ createUserMessage({ content: [toolResultBlock], toolUseResult }) → UserMessage
  │
  ▼ Yielded back to query.ts → appended to message history → sent in next API call
```

---

## 6. Verification Against Existing Analysis (data-flow.md Section 2)

### Confirmed Accurate

| Claim in data-flow.md | Source Evidence |
|------------------------|----------------|
| `findToolByName("BashTool")` searches tools array | Tool.ts L358-360: `tools.find(t => toolMatchesName(t, name))` |
| Permission result types: allow, deny, ask | types/permissions.ts imported; toolExecution.ts L995 checks `behavior !== 'allow'` |
| ALLOW path → tool.call() | toolExecution.ts L1207 |
| DENY path → synthetic tool_result with denial message | toolExecution.ts L1030-1071 |
| ASK path → render interactive prompt → await user | Handled by `canUseTool` (from useCanUseTool hook) called via `resolveHookPermissionDecision` L921 |
| Tool result types: text, image, error | Tool.ts ToolResultBlockParam from Anthropic SDK |

### Corrections and Additions

| Item | data-flow.md Said | Actual Source Shows |
|------|-------------------|---------------------|
| **Tool lookup scope** | "searches tools array (built-in + MCP tools)" | Correct — `assembleToolPool()` (tools.ts L345) merges both, and `toolUseContext.options.tools` carries the merged set |
| **Execution model** | Implied sequential | `StreamingToolExecutor` (L39) enables parallel execution of concurrency-safe tools during streaming |
| **Validation pipeline** | Not mentioned | Three-stage: Zod parse (L615) → validateInput (L683) → PreToolUse hooks (L800) — all before permission check |
| **Hook system** | Not mentioned | PreToolUse hooks run before permission, can modify input, stop execution, or make permission decisions (L800-862) |
| **PostToolUse hooks** | Not mentioned | Run after tool.call() succeeds, can modify MCP tool output (L1483-1531) |
| **Input backfill** | Not mentioned | `backfillObservableInput()` creates a clone with derived fields for hooks/SDK without mutating API-bound input (L784-793) |
| **Result size management** | Not mentioned | `processToolResultBlock()` / `processPreMappedToolResultBlock()` handles size limits, disk persistence for large results (L1410-1415) |
| **Alias support** | Not mentioned | Tools can have `aliases` array; `toolMatchesName` checks both (Tool.ts L348-353); deprecated tools found via alias fallback (toolExecution.ts L351-356) |

### Quality Score: 9.1/10

The existing data-flow.md Section 2 is structurally accurate but incomplete. It correctly captures the high-level flow (detect → find → permission → call → result) but omits the streaming concurrent executor, the three-stage validation pipeline, the hook system (PreToolUse/PostToolUse), input backfill, and result size management.

---

## 7. Key Source File Index

| File | Key Lines | Role |
|------|-----------|------|
| `src/Tool.ts` | L348-360, L362-695, L757-792 | Tool interface, findToolByName, buildTool factory |
| `src/tools.ts` | L193-251, L271-327, L345-367 | Tool registration, filtering, pool assembly |
| `src/query.ts` | L557-558, L562-567, L829-834, L841-844, L1012-1029 | Stream processing, tool_use detection, executor integration |
| `src/services/tools/StreamingToolExecutor.ts` | L39-61, L75-123, L128-150 | Concurrent tool execution engine |
| `src/services/tools/toolExecution.ts` | L337-490, L492-570, L599-1588 | runToolUse, permission resolution, tool.call() invocation |
| `src/tools/FileEditTool/FileEditTool.ts` | L85-595 | Concrete tool: validateInput, checkPermissions, call, mapResult |
| `src/tools/shared/gitOperationTracking.ts` | L135-186, L189-277 | Shared git operation detection and tracking |
