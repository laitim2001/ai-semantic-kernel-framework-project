# Wave 50: Input Processing Utilities Deep Analysis

> Deep verification of `processUserInput/`, `suggestions/`, `messages/`, and `ultraplan/` utilities.
> Source: CC-Source, 13 files analyzed. Wave date: 2026-04-01.

## 1. processUserInput/ — Input Routing Pipeline (4 files, ~1,670 LOC)

### 1.1 processUserInput.ts (606 lines) — Master Router

**Exported types:**
- `ProcessUserInputContext` — intersection of `ToolUseContext & LocalJSXCommandContext`
- `ProcessUserInputBaseResult` — `{ messages[], shouldQuery, allowedTools?, model?, effort?, resultText?, nextInput?, submitNextInput? }`

**Exported function:**
```ts
async function processUserInput({
  input, preExpansionInput?, mode, setToolJSX, context, pastedContents?,
  ideSelection?, messages?, setUserInputOnProcessing?, uuid?,
  isAlreadyProcessing?, querySource?, canUseTool?, skipSlashCommands?,
  bridgeOrigin?, isMeta?, skipAttachments?
}): Promise<ProcessUserInputBaseResult>
```

**Routing logic (verifies and extends W4 Path 1 findings):**

1. **Early display** — If `mode === 'prompt'` and input is string and not `isMeta`, immediately shows user input via `setUserInputOnProcessing`.

2. **Core dispatch** — Calls `processUserInputBase()` (private, lines 281-589), which normalizes input and routes:

   a. **Input normalization** (lines 300-345):
      - String input: extracted directly.
      - Array input (ContentBlockParam[]): each image block resized via `maybeResizeAndDownsampleImageBlock()`, last text block extracted as `inputString`, preceding blocks kept separately.
      - Image metadata texts collected for later `isMeta` message.

   b. **Bridge-safe slash command override** (lines 428-453):
      - When `bridgeOrigin` is true and input starts with `/`, parses via `parseSlashCommand()`.
      - If command passes `isBridgeSafeCommand()`, clears the skip flag.
      - If command is known but unsafe, returns error message: "isn't available over Remote Control."
      - Unknown `/foo` falls through to plain text (prevents "Unknown skill" for mobile `/shrug`).

   c. **Ultraplan keyword detection** (lines 467-493):
      - Gated on: `feature('ULTRAPLAN')`, `mode === 'prompt'`, interactive session, non-slash input, no existing ultraplan session/launch.
      - Runs `hasUltraplanKeyword()` on `preExpansionInput ?? inputString` (pasted content cannot trigger).
      - Rewrites input via `replaceUltraplanKeyword()`, routes to `/ultraplan <rewritten>` via `processSlashCommand()`.

   d. **Attachment extraction** (lines 496-514):
      - Skipped if `skipAttachments`, or if slash command (attachments handled inside slash command processor).
      - Calls `getAttachmentMessages()` for `@file`, IDE selection, etc.

   e. **Bash mode** (lines 517-529):
      - If `mode === 'bash'`: dynamic import of `processBashCommand`, delegates.

   f. **Slash command** (lines 533-551):
      - If input starts with `/` and not `effectiveSkipSlash`: dynamic import of `processSlashCommand`, delegates.

   g. **Agent mention logging** (lines 554-574):
      - For `mode === 'prompt'`, detects `@agent-<name>` mentions in attachment messages, logs analytics.

   h. **Regular text prompt** (lines 577-588):
      - Falls through to `processTextPrompt()` with normalized input, image blocks, attachments.

3. **Hook execution** (lines 178-264, in outer `processUserInput()`):
   - After `processUserInputBase()`, if `shouldQuery` is true, runs `executeUserPromptSubmitHooks()`.
   - Handles: `blockingError` (aborts query), `preventContinuation` (stops with reason), `additionalContexts` (appended as attachment messages), `hook_success` messages.
   - Hook output truncated at `MAX_HOOK_OUTPUT_LENGTH = 10000` chars.

4. **Image metadata** — `addImageMetadataMessage()` (lines 592-605) appends image dimension/path info as an `isMeta: true` user message.

**W4 verification:** W4 described "Path 1: processUserInput dispatches to slash, bash, or text prompt." This is **confirmed and extended** — the dispatch also includes ultraplan keyword interception (before slash/bash/text), bridge-safe command override, attachment extraction, and post-dispatch hook execution. W4 missed all four of these intermediate stages.

### 1.2 processSlashCommand.tsx (921 lines) — Slash Command Processor

**Exported functions:**
- `processSlashCommand()` — main entry, parses `/command args`, validates, dispatches
- `looksLikeCommand(commandName)` — regex check: only `[a-zA-Z0-9:\-_]`
- `formatSkillLoadingMetadata(skillName, progressMessage?)` — XML metadata for skill loading UI
- `processPromptSlashCommand(commandName, args, commands, context, imageContentBlocks?)` — public API for SkillTool

**Key internal functions:**
- `executeForkedSlashCommand()` — runs prompt command as forked sub-agent (with Kairos background mode)
- `getMessagesForSlashCommand()` — main dispatch by command type
- `getMessagesForPromptSlashCommand()` — handles prompt-type commands (skills)
- `formatCommandInput()`, `formatSlashCommandLoadingMetadata()`

**Dispatch flow in `processSlashCommand()` (lines 309-524):**

1. Parse input via `parseSlashCommand()` — extracts `commandName`, `args`, `isMcp`.
2. If parse fails → error message "Commands are in the form `/command [args]`".
3. If command not found:
   - If `looksLikeCommand()` and not a file path → "Unknown skill: X".
   - Otherwise → treat as regular prompt (user typed `/var/log` etc.).
4. If found → delegates to `getMessagesForSlashCommand()`.
5. Post-processing: logs analytics with plugin metadata, handles compact results.

**Command type dispatch in `getMessagesForSlashCommand()` (lines 525-777):**

| Command type | Handling |
|---|---|
| `local-jsx` | Loads module, calls `mod.call(onDone, context, args)`, renders JSX. Handles fullscreen dismiss, early-exit guard, dead-promise guard. |
| `local` | Loads module, calls `mod.call(args, context)`. Handles `skip`, `compact` (full context compaction), and `text` result types. |
| `prompt` | If `context === 'fork'` → `executeForkedSlashCommand()`. Otherwise → `getMessagesForPromptSlashCommand()`. |

**Forked slash command (lines 62-295):**
- Creates sub-agent with `runAgent()`, shows progress UI via `renderToolUseProgressMessage`.
- **Kairos background mode**: If `feature('KAIROS')` and `kairosEnabled`, runs fire-and-forget — launches sub-agent in background, returns immediately, re-enqueues result as `isMeta` prompt via `enqueuePendingNotification`.
- Waits for MCP servers to settle (polls `pending` clients, 200ms interval, 10s timeout).
- Result wrapped in `<scheduled-task-result>` XML.

**Skill usage tracking**: `recordSkillUsage(commandName)` called for all user-invocable prompt commands.

### 1.3 processBashCommand.tsx (139 lines) — Bash Mode Processor

**Exported function:**
```ts
async function processBashCommand(
  inputString, precedingInputBlocks, attachmentMessages, context, setToolJSX
): Promise<{ messages: (UserMessage | AttachmentMessage | SystemMessage)[]; shouldQuery: boolean }>
```

**Key behaviors:**
1. **Shell routing**: Checks `isPowerShellToolEnabled()` + `resolveDefaultShell()` — uses PowerShell on Windows if configured, otherwise BashTool.
2. **Sandbox bypass**: User `!` commands run with `dangerouslyDisableSandbox: true`.
3. **Progress UI**: `BashModeProgress` React component shows real-time shell output.
4. **PowerShell lazy-loading**: `require()` only when actually needed (~300KB chunk).
5. **Output processing**: Uses `processToolResultBlock()` for formatting (handles persisted output paths).
6. **Error handling**: `ShellError` shows exit code + stderr, generic errors show message.
7. **Result format**: `<bash-stdout>` and `<bash-stderr>` XML tags wrapping output.

### 1.4 processTextPrompt.ts (100 lines) — Regular Prompt Handler

**Exported function:**
```ts
function processTextPrompt(
  input, imageContentBlocks, imagePasteIds, attachmentMessages,
  uuid?, permissionMode?, isMeta?
): { messages: (UserMessage | AttachmentMessage | SystemMessage)[]; shouldQuery: boolean }
```

**Key behaviors:**
1. Generates `promptId` via `randomUUID()`, stores via `setPromptId()`.
2. Starts interaction span for telemetry via `startInteractionSpan()`.
3. Emits `user_prompt` OTel event (fixed in #33301 to also emit for array/SDK input).
4. Detects negative keywords (`matchesNegativeKeyword`) and keep-going keywords (`matchesKeepGoingKeyword`) — logs analytics.
5. If pasted images present: combines text + image content blocks into single user message.
6. Otherwise: creates simple user message with `permissionMode` and `isMeta` flags.
7. Always returns `shouldQuery: true` — regular prompts always query the model.

---

## 2. suggestions/ — Autocomplete & Ranking System (5 files, ~778 LOC)

### 2.1 commandSuggestions.ts (568 lines) — Slash Command Fuzzy Search

**Exported functions:**
| Function | Purpose |
|---|---|
| `generateCommandSuggestions(input, commands)` | Main suggestion generator — Fuse.js fuzzy search |
| `applyCommandSuggestion(suggestion, shouldExecute, commands, ...)` | Applies selected suggestion to input |
| `isCommandInput(input)` | Checks if starts with `/` |
| `hasCommandArgs(input)` | Checks if command has arguments |
| `formatCommand(command)` | Formats with trailing space |
| `findMidInputSlashCommand(input, cursorOffset)` | Finds `/cmd` mid-input for ghost text |
| `getBestCommandMatch(partialCommand, commands)` | Returns completion suffix for inline completion |
| `findSlashCommandPositions(text)` | Finds all `/command` positions for highlighting |

**Fuse.js configuration:**
- Threshold: 0.3 (strict), location: 0 (prefer start), distance: 100.
- Key weights: `commandName` (3), `partKey` (2, command segments), `aliasKey` (2), `descriptionKey` (0.5).
- Fuse index cached by commands array identity — only rebuilds when commands change.

**Suggestion ranking (when query is empty `/`):**
1. Top 5 recently used skills (by `getSkillUsageScore()`).
2. Built-in commands (local, local-jsx).
3. User settings commands.
4. Project settings commands.
5. Policy settings commands.
6. Other commands.
Each category sorted alphabetically.

**Suggestion ranking (with query):**
Priority: exact name > exact alias > prefix name (shorter wins) > prefix alias (shorter wins) > Fuse score (with usage tiebreaker at 0.1 threshold).

**Hidden command handling:** If a hidden command's exact name is typed, it is prepended to results (handles OAuth expiry, GrowthBook kill-switch edge cases).

**Mid-input slash command detection:** Regex `\s\/([a-zA-Z0-9_:-]*)$` finds `/cmd` after whitespace. Avoids lookbehind for JSC YARR JIT performance.

### 2.2 directoryCompletion.ts (264 lines) — Path Autocomplete

**Exported functions:**
| Function | Purpose |
|---|---|
| `parsePartialPath(partialPath, basePath?)` | Splits into directory + prefix |
| `scanDirectory(dirPath)` | Returns subdirectories (LRU cached) |
| `scanDirectoryForPaths(dirPath, includeHidden?)` | Returns files + directories (LRU cached) |
| `getDirectoryCompletions(partialPath, options?)` | Directory-only suggestions |
| `getPathCompletions(partialPath, options?)` | File + directory suggestions |
| `clearDirectoryCache()` | Clears directory LRU cache |
| `clearPathCache()` | Clears both caches |
| `isPathLikeToken(token)` | Checks for `~/`, `/`, `./`, `../` prefixes |

**Caching:** Two LRU caches (`lru-cache`), each max 500 entries, 5-minute TTL. Separate caches for directory-only and file+directory scans. Results capped at 100 entries per scan, 10 per suggestion list.

**Path handling:** Uses `expandPath()` for `~` expansion. Handles both forward slash and platform `sep` for Windows compatibility. Strips leading `./` from display.

### 2.3 shellHistoryCompletion.ts (119 lines) — Shell History Ghost Text

**Exported functions:**
- `getShellHistoryCompletion(input)` — finds best prefix match from history
- `clearShellHistoryCache()` — invalidates cache
- `prependToShellHistoryCache(command)` — adds new command to front without full reload

**Mechanism:**
- Reads from `getHistory()` iterator, filters entries starting with `!` prefix.
- Caches up to 50 most recent unique commands, 60-second TTL.
- Returns first exact prefix match as `{ fullCommand, suffix }` for ghost text.
- Minimum input length: 2 characters.

### 2.4 skillUsageTracking.ts (55 lines) — Skill Ranking by Recency/Frequency

**Exported functions:**
- `recordSkillUsage(skillName)` — increments count + updates timestamp (debounced 60s per skill)
- `getSkillUsageScore(skillName)` — exponential decay score

**Scoring algorithm:**
```
score = usageCount * max(0.5^(daysSinceUse / 7), 0.1)
```
- Half-life: 7 days (usage from 7 days ago = half value of today).
- Floor factor: 0.1 (heavily used old skills never fully disappear).
- Debounce: 60s per skill to avoid lock + file I/O on rapid invocations.
- Persisted in global config via `saveGlobalConfig()`.

### 2.5 slackChannelSuggestions.ts (210 lines) — Slack Channel Autocomplete

**Exported functions:**
- `getSlackChannelSuggestions(clients, searchToken)` — returns `SuggestionItem[]` for `#channel` mentions
- `hasSlackMcpServer(clients)` — checks if Slack MCP server is connected
- `findSlackChannelPositions(text)` — finds `#channel` positions for highlighting (only confirmed-real channels)
- `getKnownChannelsVersion()` — version counter for React re-render optimization
- `subscribeKnownChannels` — signal subscription for known channels changes
- `clearSlackChannelCache()` — clears all caches

**Architecture:**
- Calls `slack_search_channels` MCP tool with 5-second timeout.
- Slack tokenizes on hyphens — `mcpQueryFor()` strips trailing partial segment to avoid 0-result queries.
- Response unwrapped from JSON envelope `{"results":"..."}`, parsed via regex `^Name:\s*#?([a-z0-9][a-z0-9_-]{0,79})\s*$`.
- **Cache strategy:** Plain Map (not LRU) — needs prefix iteration for reuse. Max 50 entries. `findReusableCacheEntry()` finds longest cached prefix that still has matches.
- `knownChannels` Set tracks all ever-seen channels for highlighting gating.
- In-flight dedup: single `inflightPromise` per `mcpQuery`.

---

## 3. messages/ — Message Mapping Utilities (2 files, ~388 LOC)

### 3.1 mappers.ts (291 lines) — SDK/Internal Message Conversion

**Exported functions:**
| Function | Purpose |
|---|---|
| `toInternalMessages(sdkMessages)` | SDK → internal `Message[]` |
| `toSDKMessages(messages)` | Internal → `SDKMessage[]` |
| `toSDKCompactMetadata(meta)` | Internal → SDK compact metadata |
| `fromSDKCompactMetadata(meta)` | SDK → internal compact metadata |
| `localCommandOutputToSDKAssistantMessage(rawContent, uuid)` | Converts local command output for SDK consumers |
| `toSDKRateLimitInfo(limits)` | Internal → SDK rate limit info |

**Key conversions:**
- **SDK → Internal**: `assistant` maps directly; `user` gets `isMeta` from `isSynthetic`; `system/compact_boundary` maps compact metadata (camelCase ↔ snake_case); other system types dropped.
- **Internal → SDK**: Adds `session_id` to all messages. `user` messages carry `tool_use_result` in protobuf catchall for web viewers. `system/local_command` only converts stdout/stderr content (not command input metadata). `system/compact_boundary` maps metadata back.
- **Local command output**: Strips ANSI codes (chalk.dim), unwraps `<local-command-stdout>` and `<local-command-stderr>` XML tags, creates synthetic assistant message. Needed because Android's SdkMessageTypes.kt and api-go session-ingress don't handle `local_command_output`.
- **Assistant normalization**: Injects plan content into `ExitPlanModeV2` tool inputs since V2 reads from file, but SDK consumers expect `tool_input.plan`.
- **Rate limit mapping**: Strips internal-only fields like `unifiedRateLimitFallbackAvailable`.

### 3.2 systemInit.ts (97 lines) — System Init Message Builder

**Exported functions:**
- `buildSystemInitMessage(inputs)` — builds `system/init` SDKMessage
- `sdkCompatToolName(name)` — maps `Agent` → `Task` for backward compat (pending next minor)

**SystemInitInputs type:**
```ts
{
  tools, mcpClients, model, permissionMode, commands, agents, skills, plugins, fastMode
}
```

**Init message contents:** `cwd`, `session_id`, `tools` (with compat name mapping), `mcp_servers` (name + status), `model`, `permissionMode`, `slash_commands` (user-invocable only), `apiKeySource`, `betas`, `claude_code_version`, `output_style`, `agents`, `skills`, `plugins`, `fast_mode_state`. Conditionally adds `messaging_socket_path` when `feature('UDS_INBOX')`.

**Called from two paths:** QueryEngine (spawn-bridge/print-mode/SDK) and useReplBridge (REPL Remote Control on connect).

---

## 4. ultraplan/ — Ultraplan Keyword Detection (2 files, ~478 LOC)

### 4.1 keyword.ts (128 lines) — Keyword Detection & Replacement

**Exported functions:**
- `findUltraplanTriggerPositions(text)` — returns `TriggerPosition[]`
- `findUltrareviewTriggerPositions(text)` — same for "ultrareview"
- `hasUltraplanKeyword(text)` — boolean shorthand
- `hasUltrareviewKeyword(text)` — boolean shorthand
- `replaceUltraplanKeyword(text)` — replaces first "ultraplan" with "plan" (preserves casing of "plan" suffix)

**Detection algorithm (`findKeywordTriggerPositions`):**

1. **Fast exit**: regex test for keyword, return empty if absent or input starts with `/`.

2. **Quoted range exclusion** — builds `quotedRanges[]` by scanning for paired delimiters:
   - Backticks, double quotes, angle brackets (tag-like only: `<` followed by `[a-zA-Z/]`), curly braces, square brackets, parentheses.
   - Single quotes: only delimiters when preceded by non-word char (apostrophe exclusion — "let's ultraplan it's" still triggers).

3. **Word boundary matching** — `\b{keyword}\b` global regex, then filters out:
   - Positions inside any quoted range.
   - Path/identifier context: preceded by `/`, `\`, `-`; followed by `/`, `\`, `-`, `?`.
   - File extension context: followed by `.` + word char (e.g., `ultraplan.tsx`).
   - Question context: followed by `?` (asking about feature shouldn't invoke it).

4. **Result**: Array of `{ word, start, end }` — shape matches `findThinkingTriggerPositions` for uniform PromptInput handling.

**Replacement**: `replaceUltraplanKeyword()` replaces first trigger with `word.slice('ultra'.length)` — e.g., "ultraplan" → "plan", "UltraPlan" → "Plan". Returns empty string if nothing meaningful remains after replacement.

### 4.2 ccrSession.ts (350 lines) — CCR Session Polling for Ultraplan

**Exported types:**
- `PollFailReason` — `'terminated' | 'timeout_pending' | 'timeout_no_plan' | 'extract_marker_missing' | 'network_or_unknown' | 'stopped'`
- `UltraplanPollError` — Error subclass with `reason` and `rejectCount`
- `ScanResult` — `'approved' | 'teleport' | 'rejected' | 'pending' | 'terminated' | 'unchanged'`
- `UltraplanPhase` — `'running' | 'needs_input' | 'plan_ready'`
- `PollResult` — `{ plan, rejectCount, executionTarget: 'local' | 'remote' }`

**Exported classes:**
- `ExitPlanModeScanner` — pure stateful classifier for CCR event stream

**Exported functions:**
- `pollForApprovedExitPlanMode(sessionId, timeoutMs, onPhaseChange?, shouldStop?)` — main poll loop

**Exported constants:**
- `ULTRAPLAN_TELEPORT_SENTINEL = '__ULTRAPLAN_TELEPORT_LOCAL__'`

**ExitPlanModeScanner internals:**
- Tracks `exitPlanCalls[]` (tool_use IDs for ExitPlanModeV2), `results` Map (tool_results), `rejectedIds` Set.
- `ingest(newEvents)`: scans SDKMessages, builds state, returns verdict.
- Precedence: approved > terminated > rejected > pending > unchanged.
- `hasPendingPlan`: true when an ExitPlanMode tool_use exists with no tool_result yet.

**Poll loop:**
- 3-second interval, configurable timeout.
- Max 5 consecutive network failures (transient errors retried).
- Phase transitions: `running` → `needs_input` (idle session, no events) → `plan_ready` (pending ExitPlanMode).
- Plan extraction:
  - **Approved**: scrapes after `## Approved Plan:` or `## Approved Plan (edited by user):` marker.
  - **Teleport**: scrapes after `ULTRAPLAN_TELEPORT_SENTINEL` in denied tool_result (user clicked "teleport back to terminal").
  - **Rejected**: tracked and skipped (user can iterate in browser).

---

## 5. Cross-Cutting Observations

### 5.1 W4 Verification Summary

| W4 Claim | Status | Detail |
|---|---|---|
| processUserInput dispatches to slash, bash, or text | **Partially correct** | Misses ultraplan keyword interception, bridge-safe override, attachment extraction, hook execution |
| Slash commands route to command system | **Confirmed** | Three command types: local-jsx, local, prompt (with fork sub-variant) |
| Regular text sent to model | **Confirmed** | Via processTextPrompt, always returns shouldQuery: true |

### 5.2 Dynamic Import Pattern

All three sub-processors use dynamic `import()`:
- `processBashCommand` — lazy-loaded only in bash mode
- `processSlashCommand` — lazy-loaded only when input starts with `/` or ultraplan triggers
- PowerShellTool — lazy `require()` only when PowerShell is default shell (~300KB savings)

### 5.3 Feature Flags

| Flag | Controls |
|---|---|
| `ULTRAPLAN` | Ultraplan keyword detection and routing |
| `KAIROS` | Background fire-and-forget mode for forked slash commands |
| `UDS_INBOX` | UDS messaging socket path in system init |

### 5.4 Analytics Events

| Event | Location | Purpose |
|---|---|---|
| `tengu_ultraplan_keyword` | processUserInput.ts | Ultraplan keyword detected |
| `tengu_input_prompt` | processTextPrompt.ts | Regular prompt submitted |
| `tengu_input_bash` | processBashCommand.tsx | Bash command executed |
| `tengu_input_command` | processSlashCommand.tsx | Valid slash command executed |
| `tengu_input_slash_invalid` | processSlashCommand.tsx | Unknown slash command |
| `tengu_input_slash_missing` | processSlashCommand.tsx | Malformed slash syntax |
| `tengu_slash_command_forked` | processSlashCommand.tsx | Forked sub-agent launched |
| `tengu_subagent_at_mention` | processUserInput.ts | @agent-X mention used |
| `tengu_pasted_image_resize_attempt` | processUserInput.ts | Image resize attempt |

### 5.5 File-Level Statistics

| File | Lines | Exports |
|---|---|---|
| processUserInput.ts | 606 | 2 types, 1 function |
| processSlashCommand.tsx | 921 | 4 functions |
| processBashCommand.tsx | 139 | 1 function |
| processTextPrompt.ts | 100 | 1 function |
| commandSuggestions.ts | 568 | 8 functions, 1 type |
| directoryCompletion.ts | 264 | 7 functions, 4 types |
| shellHistoryCompletion.ts | 119 | 3 functions, 1 type |
| skillUsageTracking.ts | 55 | 2 functions |
| slackChannelSuggestions.ts | 210 | 6 functions |
| mappers.ts | 291 | 6 functions |
| systemInit.ts | 97 | 2 functions, 1 type |
| keyword.ts | 128 | 5 functions |
| ccrSession.ts | 350 | 1 class, 1 function, 4 types, 1 constant |
| **Total** | **~3,848** | **51 exports** |

---

## 6. Confidence Assessment

| Aspect | Confidence | Notes |
|---|---|---|
| Routing logic | 9.5/10 | Full source read of processUserInput.ts |
| Slash command processing | 9.0/10 | Read 800/921 lines, all functions identified |
| Bash command processing | 8.5/10 | Read 100/139 lines, key structure confirmed via grep |
| Text prompt processing | 10/10 | Full 100-line file read |
| Suggestion system | 10/10 | All 5 files fully read |
| Message utilities | 10/10 | Both files fully read |
| Ultraplan utilities | 10/10 | Both files fully read |
| **Overall Wave 50** | **9.5/10** | High-confidence deep analysis |
