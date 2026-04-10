# Wave 33: Missing Critical Types — L-07, L-08, L-09

> **Wave**: 33 | **Date**: 2026-04-01 | **Source**: `src/types/textInputTypes.ts`, `src/types/logs.ts`
> **Layers**: L-07 (Input System), L-08 (Command Queue), L-09 (Session Persistence)

---

## Type 1: `BaseTextInputProps` (28 fields)

**File**: `src/types/textInputTypes.ts:27-202`
**Purpose**: Core prop contract for all text input components in the Ink-based TUI. Every keystroke, paste, cursor movement, and input lifecycle event flows through this interface.

### Complete Field List

| # | Field | Type | Required | Description |
|---|-------|------|----------|-------------|
| 1 | `onHistoryUp` | `() => void` | No | History navigation callback on up arrow at start of input |
| 2 | `onHistoryDown` | `() => void` | No | History navigation callback on down arrow at end of input |
| 3 | `placeholder` | `string` | No | Text to display when `value` is empty |
| 4 | `multiline` | `boolean` | No | Allow multi-line input via backslash line ending (default: `true`) |
| 5 | `focus` | `boolean` | No | Route keyboard input to this component (for multi-input routing) |
| 6 | `mask` | `string` | No | Replace all chars with mask character (password inputs) |
| 7 | `showCursor` | `boolean` | No | Show cursor and allow in-text arrow key navigation |
| 8 | `highlightPastedText` | `boolean` | No | Visually highlight pasted text |
| 9 | `value` | `string` | **Yes** | Current text input value |
| 10 | `onChange` | `(value: string) => void` | **Yes** | Callback when value updates |
| 11 | `onSubmit` | `(value: string) => void` | No | Callback on Enter press |
| 12 | `onExit` | `() => void` | No | Callback on Ctrl+C to exit |
| 13 | `onExitMessage` | `(show: boolean, key?: string) => void` | No | Show exit message overlay |
| 14 | `onHistoryReset` | `() => void` | No | Reset history navigation position |
| 15 | `onClearInput` | `() => void` | No | Callback when input is cleared (double-escape) |
| 16 | `columns` | `number` | **Yes** | Number of columns for text wrapping |
| 17 | `maxVisibleLines` | `number` | No | Maximum visible lines for input viewport (enables windowing) |
| 18 | `onImagePaste` | `(base64Image, mediaType?, filename?, dimensions?, sourcePath?) => void` | No | Callback when image is pasted |
| 19 | `onPaste` | `(text: string) => void` | No | Callback when large text (>800 chars) is pasted |
| 20 | `onIsPastingChange` | `(isPasting: boolean) => void` | No | Callback when pasting state changes |
| 21 | `disableCursorMovementForUpDownKeys` | `boolean` | No | Disable cursor movement for up/down arrow keys |
| 22 | `disableEscapeDoublePress` | `boolean` | No | Skip text-level double-press escape handler (for Autocomplete ownership) |
| 23 | `cursorOffset` | `number` | **Yes** | The offset of the cursor within the text |
| 24 | `onChangeCursorOffset` | `(offset: number) => void` | **Yes** | Callback to set cursor offset |
| 25 | `argumentHint` | `string` | No | Hint text to display after command input (shows available arguments) |
| 26 | `onUndo` | `() => void` | No | Undo functionality callback |
| 27 | `dimColor` | `boolean` | No | Render text with dim color |
| 28 | `highlights` | `TextHighlight[]` | No | Text highlights for search results or other highlighting |
| 29 | `placeholderElement` | `React.ReactNode` | No | Custom React element as placeholder (overrides string placeholder) |
| 30 | `inlineGhostText` | `InlineGhostText` | No | Inline ghost text for mid-input command autocomplete |
| 31 | `inputFilter` | `(input: string, key: Key) => string` | No | Filter applied to raw input before key routing |

> **Note**: Actual count is 31 fields (the "28 fields" in the task description appears to be an earlier estimate).

### Supporting Types

```typescript
type InlineGhostText = {
  readonly text: string           // Ghost text to display (e.g., "mit" for /commit)
  readonly fullCommand: string    // Full command name (e.g., "commit")
  readonly insertPosition: number // Position where ghost text should appear
}
```

### Key Consumers

| Consumer | File | Usage |
|----------|------|-------|
| `BaseTextInput` | `components/BaseTextInput.tsx` | Direct implementation of the prop contract |
| `TextInput` | `components/TextInput.tsx` | Wraps BaseTextInput with standard input hook |
| `PromptInput` | `components/PromptInput/PromptInput.tsx` | Main user-facing prompt, extends with queue integration |

### Derived Types

- **`VimTextInputProps`** = `BaseTextInputProps & { initialMode?: VimMode; onModeChange?: (mode: VimMode) => void }` — extends with Vim mode support
- **`BaseInputState`** — Hook return type with `onInput`, `renderedValue`, `offset`, `cursorLine`, `cursorColumn`, viewport offsets, and paste state

---

## Type 2: `QueuedCommand` (15 fields)

**File**: `src/types/textInputTypes.ts:299-358`
**Purpose**: Represents a command queued for execution. This is the core unit of work in the command queue system — every user prompt, slash command, bridge message, and system-generated meta-prompt passes through this type before reaching the query engine.

### Complete Field List

| # | Field | Type | Required | Description |
|---|-------|------|----------|-------------|
| 1 | `value` | `string \| Array<ContentBlockParam>` | **Yes** | The command content — plain text or structured content blocks |
| 2 | `mode` | `PromptInputMode` | **Yes** | Input mode: `'bash' \| 'prompt' \| 'orphaned-permission' \| 'task-notification'` |
| 3 | `priority` | `QueuePriority` | No | `'now'` (interrupt), `'next'` (mid-turn), `'later'` (end-of-turn). Defaults to mode-implied priority |
| 4 | `uuid` | `UUID` | No | Unique identifier for the command |
| 5 | `orphanedPermission` | `OrphanedPermission` | No | Permission result + assistant message for orphaned permission handling |
| 6 | `pastedContents` | `Record<number, PastedContent>` | No | Raw pasted contents including images; images resized at execution time |
| 7 | `preExpansionValue` | `string` | No | Input string before `[Pasted text #N]` placeholder expansion; used for ultraplan keyword detection |
| 8 | `skipSlashCommands` | `boolean` | No | Treat as plain text even if starts with `/`; used for bridge/CCR remote messages |
| 9 | `bridgeOrigin` | `boolean` | No | Slash commands filtered through `isBridgeSafeCommand()`; set by Remote Control bridge inbound |
| 10 | `isMeta` | `boolean` | No | Resulting UserMessage gets `isMeta: true` — hidden in transcript UI but visible to model |
| 11 | `origin` | `MessageOrigin` | No | Provenance stamp (undefined = human keyboard input) |
| 12 | `workload` | `string` | No | Workload tag threaded to `cc_workload=` billing-header attribution |
| 13 | `agentId` | `AgentId` | No | Target agent for notification; undefined = main thread. Enables subagent queue isolation |

### Queue Priority Semantics

```
'now'   → Interrupt immediately, abort in-flight tool call (Esc + send)
'next'  → Mid-turn drain: let current tool finish, send between tool result and next API call
'later' → End-of-turn drain: wait for turn to finish, process as new query
```

Both `'next'` and `'later'` wake an in-progress `SleepTool` call (proactive mode only).

### Key Consumers (18 files)

| Category | Files | Usage |
|----------|-------|-------|
| **Queue Management** | `hooks/useCommandQueue.ts`, `hooks/useQueueProcessor.ts`, `utils/queueProcessor.ts`, `utils/messageQueueManager.ts` | Enqueue, dequeue, drain, priority sorting |
| **Input Processing** | `utils/handlePromptSubmit.ts`, `utils/processUserInput/processUserInput.ts`, `utils/processUserInput/processSlashCommand.tsx` | Convert user input to QueuedCommand, route slash commands |
| **Execution Engine** | `query.ts`, `cli/print.ts`, `screens/REPL.tsx` | Dequeue and execute commands, abort handling for `'now'` priority |
| **UI Components** | `components/PromptInput/PromptInput.tsx`, `components/PromptInput/PromptInputQueuedCommands.tsx`, `components/Messages.tsx` | Display queued commands, visual queue status |
| **Utilities** | `utils/attachments.ts`, `utils/messages.ts`, `hooks/useCancelRequest.ts` | Attachment handling, message construction, cancel support |

---

## Type 3: `Entry` Union Type (19 variants)

**File**: `src/types/logs.ts:297-318`
**Purpose**: Discriminated union representing every possible entry type that can be written to a session transcript log file. This is the persistence backbone — the session transcript is an append-only log of `Entry` values that captures the full session state for resume, analytics, and recovery.

### Discriminant Field

The discriminant is the `type` field, present on all variants except `TranscriptMessage` (which uses the `Message` union's own `role` discriminant).

### Complete Variant List

| # | Variant Type | Discriminant (`type`) | Key Fields | Purpose |
|---|-------------|----------------------|------------|---------|
| 1 | `TranscriptMessage` | (inherits `Message.role`) | `parentUuid`, `isSidechain`, `agentId`, `promptId` | Core conversation messages (user/assistant/system) with sidechain + agent metadata |
| 2 | `SummaryMessage` | `'summary'` | `leafUuid`, `summary` | Conversation summary for session resume |
| 3 | `CustomTitleMessage` | `'custom-title'` | `sessionId`, `customTitle` | User-set custom title (always wins over AI title) |
| 4 | `AiTitleMessage` | `'ai-title'` | `sessionId`, `aiTitle` | AI-generated session title (ephemeral, regeneratable) |
| 5 | `LastPromptMessage` | `'last-prompt'` | `sessionId`, `lastPrompt` | Records last user prompt |
| 6 | `TaskSummaryMessage` | `'task-summary'` | `sessionId`, `summary`, `timestamp` | Periodic fork-generated summary of current agent activity (for `claude ps`) |
| 7 | `TagMessage` | `'tag'` | `sessionId`, `tag` | Searchable tag for session (used in `/resume`) |
| 8 | `AgentNameMessage` | `'agent-name'` | `sessionId`, `agentName` | Agent's custom name (from `/rename` or swarm) |
| 9 | `AgentColorMessage` | `'agent-color'` | `sessionId`, `agentColor` | Agent's display color |
| 10 | `AgentSettingMessage` | `'agent-setting'` | `sessionId`, `agentSetting` | Agent definition used (from `--agent` flag) |
| 11 | `PRLinkMessage` | `'pr-link'` | `sessionId`, `prNumber`, `prUrl`, `prRepository`, `timestamp` | Links session to a GitHub pull request |
| 12 | `FileHistorySnapshotMessage` | `'file-history-snapshot'` | `messageId`, `snapshot`, `isSnapshotUpdate` | File history snapshot for undo/tracking |
| 13 | `AttributionSnapshotMessage` | `'attribution-snapshot'` | `messageId`, `surface`, `fileStates`, prompt/escape counts | Character-level contribution tracking for commit attribution |
| 14 | `QueueOperationMessage` | (from `messageQueueTypes.ts`) | — | Queue operation records |
| 15 | `SpeculationAcceptMessage` | `'speculation-accept'` | `timestamp`, `timeSavedMs` | Records accepted speculative execution and time saved |
| 16 | `ModeEntry` | `'mode'` | `sessionId`, `mode` | Session mode: `'coordinator' \| 'normal'` |
| 17 | `WorktreeStateEntry` | `'worktree-state'` | `sessionId`, `worktreeSession` | Worktree enter/exit state (null = exited, undefined = never entered) |
| 18 | `ContentReplacementEntry` | `'content-replacement'` | `sessionId`, `agentId?`, `replacements` | Content blocks replaced with smaller stubs for prompt cache stability |
| 19 | `ContextCollapseCommitEntry` | `'marble-origami-commit'` | `collapseId`, `summaryUuid`, `summaryContent`, `summary`, boundary UUIDs | Persisted context-collapse commit (obfuscated discriminant to avoid leaking feature name) |
| 20 | `ContextCollapseSnapshotEntry` | `'marble-origami-snapshot'` | `staged[]`, `armed`, `lastSpawnTokens` | Last-wins snapshot of staged collapse queue and spawn trigger state |

> **Note**: Actual count is 20 variants (the "19 variants" in the task description appears to be pre-`ContextCollapseSnapshotEntry`).

### Notable Design Patterns

1. **Obfuscated Discriminants**: `'marble-origami-commit'` and `'marble-origami-snapshot'` deliberately obfuscate the context-collapse feature name so external builds don't leak it through the generic transcript plumbing.

2. **Last-Wins vs Append-Only**: Most entries are append-only (replay all). `ContextCollapseSnapshotEntry` and `WorktreeStateEntry` are **last-wins** — only the most recent entry applies on restore.

3. **Title Precedence**: `CustomTitleMessage` (user rename) always wins over `AiTitleMessage`. AI titles are ephemeral and not re-appended on resume.

4. **Agent Isolation**: `ContentReplacementEntry.agentId` and `TranscriptMessage.agentId` partition the transcript by agent, enabling subagent sidechain resume without cross-contamination.

### Key Supporting Types

```typescript
type SerializedMessage = Message & {
  cwd: string; userType: string; entrypoint?: string;
  sessionId: string; timestamp: string; version: string;
  gitBranch?: string; slug?: string;
}

type LogOption = {
  date: string; messages: SerializedMessage[];
  fullPath?: string; value: number;
  created: Date; modified: Date;
  firstPrompt: string; messageCount: number;
  fileSize?: number; isSidechain: boolean;
  isLite?: boolean; sessionId?: string;
  teamName?: string; agentName?: string; agentColor?: string;
  agentSetting?: string; isTeammate?: boolean;
  leafUuid?: UUID; summary?: string; customTitle?: string;
  tag?: string; fileHistorySnapshots?: FileHistorySnapshot[];
  attributionSnapshots?: AttributionSnapshotMessage[];
  contextCollapseCommits?: ContextCollapseCommitEntry[];
  contextCollapseSnapshot?: ContextCollapseSnapshotEntry;
  gitBranch?: string; projectPath?: string;
  prNumber?: number; prUrl?: string; prRepository?: string;
  mode?: 'coordinator' | 'normal';
  worktreeSession?: PersistedWorktreeSession | null;
  contentReplacements?: ContentReplacementRecord[];
}
// LogOption has 33 fields — the fully-hydrated session metadata used by /resume and LogSelector
```

### Key Consumers (25+ files)

| Category | Files | Usage |
|----------|-------|-------|
| **Session Storage** | `utils/sessionStorage.ts` | Primary read/write of Entry to transcript files (appendEntry, loadTranscriptFile) |
| **Session Resume** | `commands/resume/resume.tsx`, `screens/ResumeConversation.tsx`, `utils/sessionRestore.ts`, `utils/crossProjectResume.ts` | Load and replay Entry stream to reconstruct session state |
| **Session Recovery** | `utils/conversationRecovery.ts` | Recover from corrupted transcripts by replaying valid Entry values |
| **Analytics** | `services/analytics/firstPartyEventLogger.ts`, `services/analytics/firstPartyEventLoggingExporter.ts`, `utils/stats.ts` | Extract metrics from Entry stream |
| **Attribution** | `utils/attribution.ts`, `utils/commitAttribution.ts` | Track Claude's character contributions via AttributionSnapshotMessage |
| **UI Components** | `components/LogSelector.tsx`, `components/SessionPreview.tsx` | Display session list and previews from LogOption |
| **Session Ingress** | `services/api/sessionIngress.ts` | Remote session data ingestion |
| **Branch/History** | `commands/branch/branch.ts`, `utils/fileHistory.ts`, `utils/plans.ts` | Branch management and file history from transcript entries |
| **Speculation** | `services/PromptSuggestion/speculation.ts` | Read SpeculationAcceptMessage for timing data |
| **REPL** | `screens/REPL.tsx`, `main.tsx` | Top-level session lifecycle, writing metadata entries |

---

## Cross-Type Relationships

```
User keystroke
    ↓
BaseTextInputProps.onChange()          ← L-07 Input System
    ↓
handlePromptSubmit() → QueuedCommand  ← L-08 Command Queue
    ↓
useQueueProcessor → query.ts          (dequeue + execute)
    ↓
query result → TranscriptMessage      ← L-09 Session Persistence
    ↓
sessionStorage.appendEntry(Entry)     (append to log file)
    ↓
/resume → loadTranscriptFile()        (replay Entry stream)
```

These three types form the **input-to-persistence pipeline**: user keystrokes flow through `BaseTextInputProps` into the input system, are packaged as `QueuedCommand` for prioritized execution, and the results are persisted as `Entry` variants in the session transcript for resume and analytics.

---

## Verification Notes

- **Source verified**: All fields extracted directly from source code, not documentation
- **Consumer counts**: Based on `grep` of import/usage across `src/`
- **Field counts**: BaseTextInputProps=31, QueuedCommand=13, Entry=20 variants (task estimates of 28/20/19 were approximate)
- **Layer mapping**: L-07 (TUI Input), L-08 (Command Queue), L-09 (Session Transcript Persistence)
