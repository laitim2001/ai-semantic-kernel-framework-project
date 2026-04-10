# Wave 2 Tool Verification — Batch 2 (Tools 11-20)

> Generated: 2026-04-01 | Verifier: Claude Opus 4.6 | Source: CC-Source/src/tools/
> Compared against: `02-core-systems/tool-system.md` + `00-stats.md`

---

## Verification Method

Each tool was verified by reading its primary implementation file (`*Tool.ts` or `*Tool.tsx`), its `prompt.ts` or `constants.ts` (for the registered name), and any supporting files. Extracted fields are compared against the existing analysis in `tool-system.md` and `00-stats.md`.

---

## Tool 11: FileReadTool

| Field | Source Code Finding |
|-------|-------------------|
| **Registered name** | `'Read'` (from `prompt.ts`: `FILE_READ_TOOL_NAME = 'Read'`) |
| **Input schema** | `{ file_path: string, offset?: number (int, nonneg), limit?: number (int, positive), pages?: string }` — Zod `strictObject` |
| **Category** | File Operations |
| **Key behavior** | Reads files from local filesystem. Handles text files (with line numbering), images (PNG/JPG/GIF/WEBP with resize/compression), PDFs (page extraction), Jupyter notebooks (cell rendering), and detects unchanged files to return stubs. Blocks dangerous device paths (`/dev/zero`, `/dev/stdin`, etc.). Resolves macOS screenshot space variants. |
| **Permission model** | `checkReadPermissionForTool(FileReadTool, input, toolPermissionContext)` — filesystem read permission check. Also uses `matchWildcardPattern` for permission rule matching. |
| **isReadOnly()** | `true` |
| **isEnabled()** | Not explicitly defined — uses `buildTool` default: `() => true` |
| **isConcurrencySafe()** | `true` |
| **shouldDefer** | Not set (default `false`) |
| **Extra files** | `imageProcessor.ts`, `limits.ts` — image processing and file-size limits |

### Discrepancy Check
- **00-stats.md** #11: "Reads file contents; handles images, token limits" — **Accurate** but incomplete. Also handles PDFs, notebooks, unchanged-file stubs, and device-path blocking.
- **tool-system.md**: "Read files with line ranges, images, PDFs, notebooks" — **Accurate**.
- **Name**: Both docs correctly state the tool name. The registered name is `'Read'`, not `'FileReadTool'`.

---

## Tool 12: FileWriteTool

| Field | Source Code Finding |
|-------|-------------------|
| **Registered name** | `'Write'` (from `prompt.ts`: `FILE_WRITE_TOOL_NAME = 'Write'`) |
| **Input schema** | `{ file_path: string, content: string }` — Zod `strictObject` |
| **Category** | File Operations |
| **Key behavior** | Creates or overwrites files. Validates that file was previously read (via `readFileState`), checks for external modifications since last read (mtime comparison), rejects writes to team memory files containing secrets. Discovers skill directories from written paths. Tracks file history and notifies LSP/VS Code of changes. |
| **Permission model** | `checkWritePermissionForTool(FileWriteTool, input, toolPermissionContext)`. Also checks deny rules via `matchingRuleForInput`. Rejects UNC paths to prevent NTLM credential leaks. |
| **isReadOnly()** | Not explicitly defined — uses `buildTool` default: `() => false` |
| **isEnabled()** | Not explicitly defined — uses `buildTool` default: `() => true` |
| **isConcurrencySafe()** | Not defined — default `() => false` |
| **shouldDefer** | Not set (default `false`) |

### Discrepancy Check
- **00-stats.md** #12: "Creates or overwrites files" — **Accurate**.
- **tool-system.md**: "Create or overwrite files" — **Accurate**.
- Pre-read validation (must Read before Write) is a significant behavioral detail not mentioned in existing analysis.

---

## Tool 13: GlobTool

| Field | Source Code Finding |
|-------|-------------------|
| **Registered name** | `'Glob'` (from `prompt.ts`: `GLOB_TOOL_NAME = 'Glob'`) |
| **Input schema** | `{ pattern: string, path?: string }` — Zod `strictObject` |
| **Category** | Search |
| **Key behavior** | Pattern-based file matching using `glob()` utility. Returns filenames sorted by modification time, relativized to cwd. Results capped at 100 files (from `globLimits.maxResults`). Validates that path exists and is a directory. |
| **Permission model** | `checkReadPermissionForTool(GlobTool, input, toolPermissionContext)`. Skips UNC paths for NTLM security. |
| **isReadOnly()** | `true` |
| **isEnabled()** | Not explicitly defined — default `() => true`. But conditionally excluded from `getAllBaseTools()` when `hasEmbeddedSearchTools()` is true. |
| **isConcurrencySafe()** | `true` |
| **shouldDefer** | Not set (default `false`) |

### Discrepancy Check
- **00-stats.md** #13: "Pattern-based file path matching" — **Accurate**.
- **tool-system.md**: "Fast file pattern matching" — **Accurate**.
- The conditional exclusion via `hasEmbeddedSearchTools()` is documented in `tool-system.md` line 82: `...(hasEmbeddedSearchTools() ? [] : [GlobTool, GrepTool])` — **Accurate**.

---

## Tool 14: GrepTool

| Field | Source Code Finding |
|-------|-------------------|
| **Registered name** | `'Grep'` (from `prompt.ts`: `GREP_TOOL_NAME = 'Grep'`) |
| **Input schema** | `{ pattern: string, path?: string, glob?: string, output_mode?: 'content'|'files_with_matches'|'count', '-B'?: number, '-A'?: number, '-C'?: number, context?: number, '-n'?: boolean, '-i'?: boolean, type?: string, head_limit?: number, offset?: number, multiline?: boolean }` — Zod `strictObject` with `semanticNumber`/`semanticBoolean` wrappers |
| **Category** | Search |
| **Key behavior** | Ripgrep-powered content search via `ripGrep()` utility. Supports three output modes (content, files_with_matches, count). Default head_limit of 250 to prevent context bloat. Excludes VCS directories (.git, .svn, .hg, .bzr, .jj, .sl). Supports multiline regex mode. |
| **Permission model** | `checkReadPermissionForTool(GrepTool, input, toolPermissionContext)`. Also applies `getFileReadIgnorePatterns()` and plugin cache exclusions. |
| **isReadOnly()** | `true` |
| **isEnabled()** | Not explicitly defined — default `() => true`. Conditionally excluded when `hasEmbeddedSearchTools()`. |
| **isConcurrencySafe()** | `true` |
| **shouldDefer** | Not set (default `false`) |
| **maxResultSizeChars** | `20_000` (notably lower than most tools' 100,000) |

### Discrepancy Check
- **00-stats.md** #14: "Regex content search across files" — **Accurate**.
- **tool-system.md**: "Ripgrep-powered content search" — **Accurate**.
- The rich input schema (13 parameters) is more complex than most other tools; existing analysis doesn't detail parameter count but this is not a discrepancy per se.

---

## Tool 15: ListMcpResourcesTool

| Field | Source Code Finding |
|-------|-------------------|
| **Registered name** | `'ListMcpResourcesTool'` (from `prompt.ts`: `LIST_MCP_RESOURCES_TOOL_NAME = 'ListMcpResourcesTool'`) |
| **Input schema** | `{ server?: string }` — Zod `object` (not strictObject) |
| **Category** | MCP |
| **Key behavior** | Lists available resources from connected MCP servers. Optionally filters by server name. Uses LRU-cached `fetchResourcesForClient()` with automatic cache invalidation on connection close or `resources/list_changed` notifications. Gracefully handles individual server reconnect failures. |
| **Permission model** | No explicit `checkPermissions` — uses `buildTool` default: `() => ({ behavior: 'allow', updatedInput: input })` |
| **isReadOnly()** | `true` |
| **isEnabled()** | Not explicitly defined — default `() => true` |
| **isConcurrencySafe()** | `true` |
| **shouldDefer** | `true` |

### Discrepancy Check
- **00-stats.md** #15: "Lists available MCP server resources" — **Accurate**.
- **tool-system.md**: "List MCP server resources" — **Accurate**.
- The `shouldDefer: true` flag means this tool is lazy-loaded via ToolSearch, which is consistent with the deferred tool design described in tool-system.md.

---

## Tool 16: LSPTool

| Field | Source Code Finding |
|-------|-------------------|
| **Registered name** | `'LSP'` (from `prompt.ts`: `LSP_TOOL_NAME = 'LSP'`) |
| **Input schema** | `{ operation: enum('goToDefinition'|'findReferences'|'hover'|'documentSymbol'|'workspaceSymbol'|'goToImplementation'|'prepareCallHierarchy'|'incomingCalls'|'outgoingCalls'), filePath: string, line: number (int, positive), character: number (int, positive) }` — Zod `strictObject` |
| **Category** | IDE / Code Intelligence |
| **Key behavior** | Interfaces with Language Server Protocol servers for code intelligence. Supports 9 operations: goToDefinition, findReferences, hover, documentSymbol, workspaceSymbol, goToImplementation, prepareCallHierarchy, incomingCalls, outgoingCalls. Validates against discriminated union schema. Waits for LSP initialization. Max file size: 10MB. |
| **Permission model** | `checkReadPermissionForTool(LSPTool, input, toolPermissionContext)` |
| **isReadOnly()** | `true` |
| **isEnabled()** | `isLspConnected()` — only enabled when an LSP server is connected |
| **isConcurrencySafe()** | `true` |
| **shouldDefer** | `true` |
| **Extra files** | `formatters.ts` (8 result formatters), `schemas.ts` (discriminated union validation), `symbolContext.ts` |

### Discrepancy Check
- **00-stats.md** #16: "Language Server Protocol integration (diagnostics, symbols)" — **Partially inaccurate**. The tool does NOT provide diagnostics. It provides: goToDefinition, findReferences, hover, documentSymbol, workspaceSymbol, goToImplementation, prepareCallHierarchy, incomingCalls, outgoingCalls. Diagnostics are handled separately by `LSPDiagnosticRegistry` in the services layer.
- **tool-system.md**: "Language Server Protocol operations" — **Accurate** (general enough).
- **Correction needed**: 00-stats.md should say "symbols, definitions, references, hover" instead of "diagnostics, symbols".

---

## Tool 17: McpAuthTool

| Field | Source Code Finding |
|-------|-------------------|
| **Registered name** | Dynamic: `mcp__<serverName>__authenticate` (via `buildMcpToolName(serverName, 'authenticate')`) |
| **Input schema** | `{}` — empty Zod object (no parameters needed) |
| **Category** | MCP |
| **Key behavior** | **Not built via `buildTool()`** — instead uses a factory function `createMcpAuthTool(serverName, config)` that returns a raw `Tool` object. Creates a pseudo-tool for unauthenticated MCP servers. When called, initiates OAuth flow via `performMCPOAuthFlow` with `skipBrowserOpen: true`, returns the authorization URL. After user completes browser auth, reconnects the server and swaps real tools into appState. Handles `claudeai-proxy` type separately. Only supports `sse` and `http` transport types for OAuth. |
| **Permission model** | Always allows: `() => ({ behavior: 'allow', updatedInput: input })` |
| **isReadOnly()** | `false` |
| **isEnabled()** | `() => true` |
| **isConcurrencySafe()** | `false` |
| **shouldDefer** | Not set on the raw tool object |

### Discrepancy Check
- **00-stats.md** #17: "Handles MCP server OAuth authentication" — **Accurate**.
- **tool-system.md**: "OAuth authentication for MCP servers" — **Accurate**.
- **Important detail**: This is NOT a standard `buildTool()` tool. It's a factory-created pseudo-tool that gets dynamically named per server. The existing analysis doesn't highlight this architectural distinction. The tool name is always `mcp__<server>__authenticate`, not a fixed `'McpAuthTool'`.

---

## Tool 18: MCPTool

| Field | Source Code Finding |
|-------|-------------------|
| **Registered name** | `'mcp'` (base name, but overridden in `mcpClient.ts` with the real MCP tool name) |
| **Input schema** | `z.object({}).passthrough()` — accepts any object (open schema for MCP tool delegation) |
| **Category** | MCP |
| **Key behavior** | **Template/bridge tool** — the base implementation is a skeleton. The `name`, `description()`, `prompt()`, `call()`, `isOpenWorld()`, and `userFacingName()` are all marked as "Overridden in mcpClient.ts". The actual MCP tool instances are created by cloning this template and replacing those methods with server-specific implementations. Base `call()` returns empty string. |
| **Permission model** | `checkPermissions` returns `{ behavior: 'passthrough', message: 'MCPTool requires permission.' }` — delegates to the permission system's passthrough logic (user prompt). |
| **isReadOnly()** | Not explicitly defined — default `() => false` |
| **isEnabled()** | Not explicitly defined — default `() => true` |
| **isConcurrencySafe()** | Not defined — default `() => false` |
| **isMcp** | `true` (special flag for MCP tools) |
| **shouldDefer** | Not set |

### Discrepancy Check
- **00-stats.md** #18: "Generic bridge to MCP server tools" — **Accurate**.
- **tool-system.md**: "Dynamic wrapper for MCP server tools" — **Accurate**.
- The `passthrough` permission behavior is a notable design: it means every MCP tool call requires explicit user permission unless allow-listed. This is documented in tool-system.md's permission section.

---

## Tool 19: NotebookEditTool

| Field | Source Code Finding |
|-------|-------------------|
| **Registered name** | `'NotebookEdit'` (from `constants.ts`: `NOTEBOOK_EDIT_TOOL_NAME = 'NotebookEdit'`) |
| **Input schema** | `{ notebook_path: string, cell_id?: string, new_source: string, cell_type?: 'code'|'markdown', edit_mode?: 'replace'|'insert'|'delete' }` — Zod `strictObject` |
| **Category** | File Operations / Notebooks |
| **Key behavior** | Edits Jupyter notebook (.ipynb) cells. Supports three edit modes: replace (default), insert (new cell after specified cell_id), delete. Validates .ipynb extension, cell existence for replace/delete modes. Parses notebook JSON, modifies cell source, writes back. Tracks file history. |
| **Permission model** | `checkWritePermissionForTool(NotebookEditTool, input, toolPermissionContext)` — write permission required |
| **isReadOnly()** | Not explicitly defined — default `() => false` |
| **isEnabled()** | Not explicitly defined — default `() => true` |
| **isConcurrencySafe()** | Not defined — default `() => false` |
| **shouldDefer** | `true` |
| **userFacingName** | `'Edit Notebook'` (differs from registered name) |

### Discrepancy Check
- **00-stats.md** #19: "Edits Jupyter notebook cells" — **Accurate**.
- **tool-system.md**: "Edit Jupyter notebooks" — **Accurate**.
- The three edit modes (replace/insert/delete) are not mentioned in existing analysis but are important behavioral details.

---

## Tool 20: PowerShellTool

| Field | Source Code Finding |
|-------|-------------------|
| **Registered name** | `'PowerShell'` (from `toolName.ts`: `POWERSHELL_TOOL_NAME = 'PowerShell'`) |
| **Input schema** | `{ command: string, timeout?: number, description?: string, run_in_background?: boolean, dangerouslyDisableSandbox?: boolean }` — Zod `strictObject`. `run_in_background` conditionally omitted when `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` is set. |
| **Category** | Shell |
| **Key behavior** | Executes PowerShell commands. Full parallel to BashTool with PS-specific adaptations: canonical cmdlet resolution, read-only detection via cmdlet allowlist, sleep pattern detection (`Start-Sleep`), search/read command classification, background task support, image output detection, large output persistence. Checks Windows sandbox policy compliance. Uses `powershellToolHasPermission` for PS-specific permission logic including AST-based read-only analysis. |
| **Permission model** | `powershellToolHasPermission(input, context)` — PS-specific permission handler that includes async AST parsing for more accurate read-only detection than the sync `isReadOnly()`. |
| **isReadOnly()** | Conditional: checks `hasSyncSecurityConcerns(command)` first, then `isReadOnlyCommand(command)`. Limited by sync interface — real read-only detection happens async in permission handler. |
| **isEnabled()** | `() => true` (always enabled, but conditionally included in tool list) |
| **isConcurrencySafe()** | Delegates to `isReadOnly()` result |
| **shouldDefer** | Not set |
| **Extra files** | `clmTypes.ts`, `commandSemantics.ts`, `commonParameters.ts`, `destructiveCommandWarning.ts`, `gitSafety.ts`, `modeValidation.ts`, `pathValidation.ts`, `powershellPermissions.ts`, `powershellSecurity.ts`, `readOnlyValidation.ts`, `toolName.ts` (11 supporting files — most of any tool) |

### Discrepancy Check
- **00-stats.md** #20: "Executes PowerShell commands (Windows)" — **Accurate**.
- **tool-system.md**: "Windows PowerShell (conditional)" — **Accurate**.
- The massive supporting file count (11 files) makes this the most complex tool alongside BashTool. The existing analysis underrepresents this complexity.

---

## Summary of Discrepancies Found

| # | Tool | Issue | Severity |
|---|------|-------|----------|
| 1 | LSPTool (#16) | 00-stats.md says "diagnostics, symbols" but tool does NOT provide diagnostics — it provides definitions, references, hover, symbols, call hierarchy | **Medium** — factual error in description |
| 2 | McpAuthTool (#17) | Not built with `buildTool()` — uses factory pattern `createMcpAuthTool()`. Name is dynamic `mcp__<server>__authenticate`, not fixed. Analysis doesn't capture this | **Low** — architectural nuance |
| 3 | MCPTool (#18) | Base implementation is a skeleton — all key methods overridden in `mcpClient.ts`. Analysis mentions "dynamic wrapper" which is correct but undersells the template-clone pattern | **Low** — description adequate |
| 4 | FileWriteTool (#12) | Must-read-before-write validation not documented in existing analysis | **Low** — behavioral detail |
| 5 | GrepTool (#14) | 13 input parameters (most of any tool) and 20K maxResultSizeChars (lowest of file/search tools) not highlighted | **Low** — detail level |
| 6 | PowerShellTool (#20) | 11 supporting files (most of any tool), PS-specific AST-based permission handler not documented | **Low** — complexity underrepresented |

### Overall Assessment

**Existing analysis accuracy: 9.0/10**

The `tool-system.md` and `00-stats.md` descriptions are fundamentally correct for all 10 tools. The only factual error is the LSPTool description mentioning "diagnostics" (which it does not provide). All tool names, categories, and primary descriptions are verified accurate. The main gap is in behavioral detail depth — the existing analysis provides good high-level descriptions but misses some important implementation specifics like FileWriteTool's must-read-first validation, GrepTool's 250-entry default limit, and PowerShellTool's AST-based permission analysis.

### Verified Tool Name Registry (Batch 2)

| # | Analysis Name | Actual Registered Name | Match? |
|---|--------------|----------------------|--------|
| 11 | FileReadTool | `Read` | Name in code differs from directory name |
| 12 | FileWriteTool | `Write` | Name in code differs from directory name |
| 13 | GlobTool | `Glob` | Matches |
| 14 | GrepTool | `Grep` | Matches |
| 15 | ListMcpResourcesTool | `ListMcpResourcesTool` | Matches |
| 16 | LSPTool | `LSP` | Name in code differs from directory name |
| 17 | McpAuthTool | `mcp__<server>__authenticate` | Dynamic — no fixed name |
| 18 | MCPTool | `mcp` (overridden per instance) | Base name only |
| 19 | NotebookEditTool | `NotebookEdit` | Name in code differs from directory name |
| 20 | PowerShellTool | `PowerShell` | Name in code differs from directory name |

**Note**: The directory names (e.g., `FileReadTool/`) differ from the registered tool names the model sees (e.g., `Read`). The existing analysis correctly uses directory names for indexing but should note the actual registered names more prominently for tools where they differ.
