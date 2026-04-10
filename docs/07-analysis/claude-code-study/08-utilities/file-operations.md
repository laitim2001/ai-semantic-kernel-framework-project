# File Operations

> Analysis of Claude Code's file read/write/edit tools, glob/grep search, file indexing, and persistence systems.

## Overview

File operations are the most frequently used tools in Claude Code. The system provides five core tools (FileRead, FileWrite, FileEdit, Glob, Grep) with extensive support for format detection, permission checking, large file handling, and intelligent search capabilities.

**Key source files:**
- `src/tools/FileReadTool/FileReadTool.ts` — File reading with format detection
- `src/tools/FileWriteTool/FileWriteTool.ts` — File creation and writing
- `src/tools/FileEditTool/FileEditTool.ts` — Surgical string replacement edits
- `src/tools/GlobTool/GlobTool.ts` — File pattern matching
- `src/tools/GrepTool/GrepTool.ts` — Content search with ripgrep
- `src/utils/filePersistence/` — File state persistence
- `src/native-ts/file-index/` — File indexing system

---

## FileReadTool

### Capabilities

`src/tools/FileReadTool/FileReadTool.ts` is a multi-format file reader:

**Supported formats:**
| Format | Handling |
|--------|----------|
| Text files | Line-numbered output with `cat -n` format |
| Images (PNG, JPG, etc.) | Compressed + resized, returned as base64 image blocks |
| PDF files | Extracted via `readPDF()` / `extractPDFPages()` with page limits |
| Jupyter notebooks | Parsed cells with outputs via `readNotebook()` |
| Binary files | Detected via `hasBinaryExtension()`, rejected gracefully |

### Input Schema

```typescript
{
  file_path: string      // Absolute path to file
  offset?: number        // Starting line number (0-based)
  limit?: number         // Number of lines to read
  pages?: string         // PDF page range (e.g., "1-5")
}
```

### Key Features

**Range reading:** `readFileInRange()` supports efficient partial file reads with offset and limit, avoiding loading entire large files.

**Image handling:**
- Detects image format from buffer (`detectImageFormatFromBuffer()`)
- Resizes and downsamples for API token efficiency (`maybeResizeAndDownsampleImageBuffer()`)
- Compresses with token limit awareness (`compressImageBufferWithTokenLimit()`)
- Creates metadata text with dimensions

**PDF handling:**
- Page count detection via `getPDFPageCount()`
- Maximum 20 pages per read (`PDF_MAX_PAGES_PER_READ`)
- Page range parsing via `parsePDFPageRange()`
- Size threshold for inline vs. extraction mode

**Token estimation:** Uses `roughTokenCountEstimationForFileType()` and `countTokensWithAPI()` to manage content size.

**Similar file suggestion:** When a file is not found, `findSimilarFile()` suggests alternatives. `suggestPathUnderCwd()` handles relative vs. absolute path confusion.

**Skill activation:** Reading files can trigger conditional skill loading via `activateConditionalSkillsForPaths()`.

**Memory file detection:** `isAutoMemFile()` detects memory-related files for special handling with freshness notes.

### Permission Checking

`checkReadPermissionForTool()` validates read access against:
- Filesystem permission rules
- Internal path protection (Claude config directories)
- Sandbox read restrictions

---

## FileWriteTool

### Purpose

`src/tools/FileWriteTool/FileWriteTool.ts` creates new files or completely overwrites existing ones.

### Features

- **Encoding detection:** `detectFileEncoding()` and `detectLineEndings()` preserve existing file encoding
- **Modification time tracking:** `getFileModificationTime()` checks for concurrent edits
- **File history:** When enabled, `fileHistoryTrackEdit()` records the change for undo support
- **VS Code integration:** `notifyVscodeFileUpdated()` signals the IDE about changes

### Safety

The tool requires that existing files be read before overwriting — this ensures the model has seen the current content and isn't blindly overwriting.

---

## FileEditTool

### Purpose

`src/tools/FileEditTool/FileEditTool.ts` performs surgical string replacement edits — replacing an exact `old_string` with a `new_string`.

### Input Schema

```typescript
{
  file_path: string       // Absolute path
  old_string: string      // Exact text to find (must be unique)
  new_string: string      // Replacement text (must differ)
  replace_all?: boolean   // Replace all occurrences (default: false)
}
```

### Key Behaviors

- **Uniqueness requirement:** `old_string` must appear exactly once in the file (unless `replace_all: true`)
- **Diff requirement:** `old_string` must differ from `new_string`
- **Indentation preservation:** The edit preserves surrounding indentation
- **Encoding preservation:** Maintains original file encoding and line endings

---

## GlobTool

### Purpose

`src/tools/GlobTool/GlobTool.ts` finds files matching glob patterns.

### Features

- Fast file pattern matching that works with any codebase size
- Supports standard glob patterns: `**/*.js`, `src/**/*.ts`
- Returns matching file paths sorted by modification time
- Respects `.gitignore` patterns
- Integrates with the file indexing system for performance

---

## GrepTool

### Purpose

`src/tools/GrepTool/GrepTool.ts` searches file contents using ripgrep (`rg`).

### Input Parameters

```typescript
{
  pattern: string                // Regex pattern
  path?: string                  // Search directory (default: cwd)
  glob?: string                  // File pattern filter (e.g., "*.js")
  type?: string                  // File type filter (e.g., "js", "py")
  output_mode?: 'content' | 'files_with_matches' | 'count'
  multiline?: boolean            // Cross-line matching
  '-i'?: boolean                 // Case insensitive
  '-n'?: boolean                 // Line numbers
  '-A'?: number                  // Lines after match
  '-B'?: number                  // Lines before match
  '-C'?: number                  // Context lines
  context?: number               // Alias for -C
  head_limit?: number            // Limit results (default: 250)
  offset?: number                // Skip first N results
}
```

### Implementation

- Uses `ripgrep` (`rg`) under the hood via the `ripgrepCommand()` utility
- Falls back to embedded search tools on ant-native builds
- Supports multiline mode (`-U --multiline-dotall`)
- Results are paginated via `head_limit` and `offset`

---

## File Indexing

### Native File Index

`src/native-ts/file-index/` provides a native TypeScript file indexing system:

- Builds and maintains an index of files in the project
- Enables fast file lookup by name, path, or pattern
- Updates incrementally as files change
- Integrates with Glob and Grep tools for performance

### Code Indexing

`src/utils/codeIndexing.ts` detects when commands trigger code indexing:
- `detectCodeIndexingFromCommand()` identifies indexing-related commands
- Used by the Bash tool to track when the model builds search indexes

---

## File State Persistence

### filePersistence

`src/utils/filePersistence/` manages persistent file state:
- Tracks file modifications across sessions
- Stores file metadata (encoding, line endings, modification times)
- Enables detecting external changes between tool calls

### fileStateCache

`src/utils/fileStateCache.ts` provides in-memory caching:
- `createFileStateCacheWithSizeLimit(size)` — Creates a bounded LRU cache
- `READ_FILE_STATE_CACHE_SIZE` — Default cache size for read operations
- `cloneFileStateCache()` — Creates independent copies for subagents

Subagents get cloned file state caches so their reads don't pollute the parent's cache.

---

## File Operation Analytics

`src/utils/fileOperationAnalytics.ts` provides `logFileOperation()`:
- Tracks file read/write/edit operations for analytics
- Captures file extension, operation type, and size
- Used for understanding tool usage patterns

---

## Large File Handling

### Tool Result Storage

`src/utils/toolResultStorage.ts` handles large tool results:
- `ensureToolResultsDir()` — Creates storage directory
- `getToolResultPath(id)` — Per-result storage path
- `generatePreview(content, PREVIEW_SIZE_BYTES)` — Creates size-limited previews
- `buildLargeToolResultMessage()` — Wraps large results with `<persisted-output>` tags

### Content Replacement

When file content exceeds inline limits:
1. Full content is written to disk at the tool result path
2. A preview (first N bytes) is sent inline
3. The `<persisted-output>` tag references the disk path
4. Subsequent reads can access the full content from disk

---

## Key Design Patterns

1. **Multi-format awareness** — FileRead handles text, images, PDFs, notebooks, binary detection
2. **Encoding preservation** — Write/Edit tools detect and maintain original encoding and line endings
3. **Safety gates** — Read-before-write requirement, uniqueness checks for edits
4. **Bounded caching** — LRU file state caches with size limits; cloned for subagents
5. **Tiered output** — Small results inline, large results to disk with preview
6. **Ripgrep delegation** — Grep uses native ripgrep for performance, not JavaScript regex
7. **Index-accelerated search** — File indexing enables fast pattern matching on large codebases
8. **Analytics integration** — All file operations tracked for usage analysis
