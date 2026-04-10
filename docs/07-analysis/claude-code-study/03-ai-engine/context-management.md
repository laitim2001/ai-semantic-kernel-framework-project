# Context Management — Claude Code CLI

> Consolidated from base analysis + deep verification (2026-04-01, 9.0/10 confidence).
> Source: `src/services/compact/` (6 primary + 2 supplementary files verified)

---

## 1. Architecture Overview

Claude Code employs a **four-tier context compression strategy**, executed in priority order:

```
Tier 0: Time-Based Microcompact     (cold-cache opportunistic clearing)
Tier 1: Cached Microcompact         (cache-editing API, ant-only)
Tier 2: Session Memory Compact      (SM-based fast path, no LLM call)
Tier 3: Full Compact                (forked-agent LLM summarization)
```

All tiers are coordinated through `autoCompactIfNeeded()` in `autoCompact.ts`, with microcompact running as a pre-request filter in `microcompactMessages()`.

---

## 2. Exact Threshold Constants

### 2.1 autoCompact.ts Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `MAX_OUTPUT_TOKENS_FOR_SUMMARY` | `20_000` | Reserved output tokens for compact summary (based on p99.99 = 17,387 tokens) |
| `AUTOCOMPACT_BUFFER_TOKENS` | `13_000` | Buffer subtracted from effective window to get autocompact threshold |
| `WARNING_THRESHOLD_BUFFER_TOKENS` | `20_000` | Buffer for UI warning display |
| `ERROR_THRESHOLD_BUFFER_TOKENS` | `20_000` | Buffer for UI error display |
| `MANUAL_COMPACT_BUFFER_TOKENS` | `3_000` | Buffer for blocking limit (forces user action) |
| `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES` | `3` | Circuit breaker trip count |

### 2.2 compact.ts Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `POST_COMPACT_MAX_FILES_TO_RESTORE` | `5` | Max files re-read after compaction |
| `POST_COMPACT_TOKEN_BUDGET` | `50_000` | Total token budget for post-compact attachments |
| `POST_COMPACT_MAX_TOKENS_PER_FILE` | `5_000` | Per-file token cap for restored files |
| `POST_COMPACT_MAX_TOKENS_PER_SKILL` | `5_000` | Per-skill token cap (skills can be 18-20KB) |
| `POST_COMPACT_SKILLS_TOKEN_BUDGET` | `25_000` | Total budget for ~5 skills |
| `MAX_COMPACT_STREAMING_RETRIES` | `2` | Retry count for streaming fallback path |
| `MAX_PTL_RETRIES` | `3` | Max prompt-too-long retry attempts |

### 2.3 sessionMemoryCompact.ts Constants (DEFAULT_SM_COMPACT_CONFIG)

| Constant | Value | Purpose |
|----------|-------|---------|
| `minTokens` | `10_000` | Minimum tokens to preserve after SM compaction |
| `minTextBlockMessages` | `5` | Minimum messages with text blocks to keep |
| `maxTokens` | `40_000` | Hard cap on preserved tokens |

### 2.4 timeBasedMCConfig.ts Defaults

| Constant | Value | Purpose |
|----------|-------|---------|
| `enabled` | (from GrowthBook) | Feature flag controlled |
| `gapThresholdMinutes` | `60` | Minutes since last assistant message to trigger |
| `keepRecent` | `5` | Number of recent tool results to preserve |

### 2.5 microCompact.ts Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `IMAGE_MAX_TOKEN_SIZE` | `2_000` | Token estimate for image/document blocks |
| `TIME_BASED_MC_CLEARED_MESSAGE` | `'[Old tool result content cleared]'` | Replacement text for cleared tool results |

---

## 3. Effective Context Window Calculation

```
effectiveContextWindow = min(
    getContextWindowForModel(model, sdkBetas),
    CLAUDE_CODE_AUTO_COMPACT_WINDOW  // env override, optional
) - min(
    getMaxOutputTokensForModel(model),
    MAX_OUTPUT_TOKENS_FOR_SUMMARY     // 20,000
)
```

### Threshold Derivation Chain

```
autoCompactThreshold = effectiveContextWindow - AUTOCOMPACT_BUFFER_TOKENS (13,000)

warningThreshold = threshold - WARNING_THRESHOLD_BUFFER_TOKENS (20,000)
  where threshold = autoCompactThreshold (if autocompact enabled)
                  = effectiveContextWindow (if autocompact disabled)

errorThreshold = threshold - ERROR_THRESHOLD_BUFFER_TOKENS (20,000)

blockingLimit = effectiveContextWindow - MANUAL_COMPACT_BUFFER_TOKENS (3,000)
  // Overridable via CLAUDE_CODE_BLOCKING_LIMIT_OVERRIDE env var

// Testing override: CLAUDE_AUTOCOMPACT_PCT_OVERRIDE
// If set, autoCompactThreshold = min(effectiveWindow * pct/100, normalThreshold)
```

---

## 4. Complete Trigger Conditions

### 4.1 shouldAutoCompact() Decision Tree

```
shouldAutoCompact(messages, model, querySource, snipTokensFreed):
  |
  +-- querySource === 'session_memory' OR 'compact'?
  |   +-- YES -> return false  (recursion guard for forked agents)
  |
  +-- feature('CONTEXT_COLLAPSE') AND querySource === 'marble_origami'?
  |   +-- YES -> return false  (ctx-agent guard: resetContextCollapse would destroy main state)
  |
  +-- !isAutoCompactEnabled()?
  |   +-- YES -> return false
  |   |   Checks: DISABLE_COMPACT env, DISABLE_AUTO_COMPACT env, userConfig.autoCompactEnabled
  |
  +-- feature('REACTIVE_COMPACT') AND tengu_cobalt_raccoon flag?
  |   +-- YES -> return false  (reactive-only mode: let API's 413 trigger compact)
  |
  +-- feature('CONTEXT_COLLAPSE') AND isContextCollapseEnabled()?
  |   +-- YES -> return false  (collapse owns headroom at 90%/95% thresholds)
  |
  +-- tokenCount = tokenCountWithEstimation(messages) - snipTokensFreed
     threshold = getAutoCompactThreshold(model)
     return tokenCount >= threshold
```

### 4.2 autoCompactIfNeeded() Execution Flow

```
autoCompactIfNeeded(messages, toolUseContext, cacheSafeParams, querySource, tracking):
  |
  +-- DISABLE_COMPACT env? -> return {wasCompacted: false}
  |
  +-- Circuit breaker: tracking.consecutiveFailures >= 3?
  |   +-- YES -> return {wasCompacted: false}
  |
  +-- !shouldAutoCompact(...)? -> return {wasCompacted: false}
  |
  +-- Build RecompactionInfo (isRecompaction, turnsSince, threshold)
  |
  +-- ATTEMPT 1: trySessionMemoryCompaction(messages, agentId, threshold)
  |   +-- Success -> setLastSummarizedMessageId(undefined)
  |   |            runPostCompactCleanup(querySource)
  |   |            notifyCompaction() [if PROMPT_CACHE_BREAK_DETECTION]
  |   |            markPostCompaction()
  |   |            return {wasCompacted: true, compactionResult}
  |   +-- null -> fall through
  |
  +-- ATTEMPT 2: compactConversation(messages, ..., isAutoCompact=true)
  |   +-- Success -> setLastSummarizedMessageId(undefined)
  |   |            runPostCompactCleanup(querySource)
  |   |            return {wasCompacted: true, consecutiveFailures: 0}
  |   +-- Error -> if not USER_ABORT: logError
  |              consecutiveFailures++
  |              if failures >= 3: log circuit breaker trip
  |              return {wasCompacted: false, consecutiveFailures}
```

---

## 5. Circuit Breaker Logic

**Problem addressed**: BQ 2026-03-10 found 1,279 sessions with 50+ consecutive failures (up to 3,272 in one session), wasting ~250K API calls/day globally.

**Mechanism**:
- `AutoCompactTrackingState.consecutiveFailures` tracks consecutive failures per session
- Threshold: `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3`
- **Trip condition**: `tracking.consecutiveFailures >= 3` at entry of `autoCompactIfNeeded()`
- **Reset condition**: On any successful compaction, `consecutiveFailures` is set to `0`
- **Increment**: On error (except `ERROR_MESSAGE_USER_ABORT`), `prevFailures + 1`
- **Logging**: When tripped, logs warning: `"autocompact: circuit breaker tripped after N consecutive failures — skipping future attempts this session"`
- **Scope**: Per-session (tracked via `AutoCompactTrackingState` threaded through query loop)

---

## 6. Forked Agent Mechanism (Prompt Cache Sharing)

The primary compact path uses a **forked agent** to share the main conversation's prompt cache:

```
streamCompactSummary():
  |
  +-- promptCacheSharingEnabled = tengu_compact_cache_prefix flag (default: true)
  |
  +-- IF enabled:
  |   +-- runForkedAgent({
  |   |     promptMessages: [summaryRequest],    // Just the compact prompt
  |   |     cacheSafeParams,                     // Inherits main thread's cache-key params
  |   |     canUseTool: deny-all,                // Tools rejected during compaction
  |   |     querySource: 'compact',
  |   |     forkLabel: 'compact',
  |   |     maxTurns: 1,
  |   |     skipCacheWrite: true,                // Don't pollute cache with compact output
  |   |     overrides: { abortController }       // ESC propagation
  |   |   })
  |   |
  |   +-- Cache sharing works because:
  |   |   - Fork inherits parent's full tool set (required for cache-key match)
  |   |   - Same system prompt, model, thinking config
  |   |   - cacheSafeParams.forkContextMessages = conversation messages (prefix match)
  |   |   - DO NOT set maxOutputTokens (would change thinking budget_tokens -> cache miss)
  |   |
  |   +-- Guard: isApiErrorMessage check prevents aborted compacts from producing
  |   |   fake summaries ("Request was aborted." doesn't start with "API Error")
  |   |
  |   +-- On success: return assistantMsg (log tengu_compact_cache_sharing_success)
  |   +-- On failure: log fallback reason, fall through to streaming path
  |
  +-- STREAMING FALLBACK:
      +-- retryEnabled = tengu_compact_streaming_retry flag (default: false)
      +-- maxAttempts = retryEnabled ? 2 : 1
      +-- queryModelWithStreaming({
      |     messages: normalizeForAPI(stripImages(stripReinjected(afterBoundary + summaryRequest))),
      |     systemPrompt: "You are a helpful AI assistant tasked with summarizing conversations.",
      |     thinkingConfig: { type: 'disabled' },
      |     tools: [FileReadTool] (or + ToolSearchTool + MCP if tool search enabled),
      |     maxOutputTokensOverride: min(COMPACT_MAX_OUTPUT_TOKENS, modelMax),
      |     querySource: 'compact'
      |   })
      +-- Keep-alive: 30s interval sends session activity signals during long API calls
      +-- On no response + retries left: sleep(getRetryDelay), retry
      +-- On final failure: throw ERROR_MESSAGE_INCOMPLETE_RESPONSE
```

### NO_TOOLS_PREAMBLE

The compact prompt starts with an aggressive no-tools preamble because the forked agent inherits the parent's full tool set (for cache-key match), and Sonnet 4.6+ adaptive-thinking models sometimes attempt tool calls despite weaker trailer instructions. With `maxTurns: 1`, a denied tool call = no text output = fallback (2.79% on 4.6 vs 0.01% on 4.5).

```
CRITICAL: Respond with TEXT ONLY. Do NOT call any tools.
- Do NOT use Read, Bash, Grep, Glob, Edit, Write, or ANY other tool.
- Tool calls will be REJECTED and will waste your only turn — you will fail the task.
- Your entire response must be plain text: an <analysis> block followed by a <summary> block.
```

---

## 7. Session Memory Fast Path Conditions

`trySessionMemoryCompaction()` is attempted **before** full LLM compaction:

### Entry Conditions (all must be true)

1. `shouldUseSessionMemoryCompaction()` returns true:
   - `ENABLE_CLAUDE_CODE_SM_COMPACT` env override OR
   - Both `tengu_session_memory` AND `tengu_sm_compact` feature flags are true
   - NOT disabled by `DISABLE_CLAUDE_CODE_SM_COMPACT` env

2. Session memory content exists and is non-empty (not just template)

3. Remote config initialized (once per session via `tengu_sm_compact_config` GrowthBook key)

### Two Scenarios

**Normal case** (lastSummarizedMessageId is set):
- Find the message index matching lastSummarizedMessageId
- If not found in current messages, return null (fall back to legacy)

**Resumed session** (no lastSummarizedMessageId but session memory has content):
- Set lastSummarizedIndex = messages.length - 1 (keep minimal messages initially)

### calculateMessagesToKeepIndex Algorithm

```
Start from lastSummarizedIndex + 1
Calculate totalTokens and textBlockMessageCount for [startIndex..end]

IF totalTokens >= maxTokens (40,000): stop, adjust for tool pairs
IF totalTokens >= minTokens (10,000) AND textBlockMessageCount >= minTextBlockMessages (5): stop

ELSE expand backwards toward floor (last compact boundary + 1):
  For each message added:
    accumulate tokens and text block count
    IF totalTokens >= maxTokens: break
    IF both minimums met: break

Finally: adjustIndexToPreserveAPIInvariants(messages, startIndex)
  - Ensures tool_use/tool_result pairs are not split
  - Ensures thinking blocks sharing message.id with kept assistants are included
```

### Post-Compact Token Guard

If `autoCompactThreshold` is provided and `estimateMessageTokens(postCompactMessages) >= threshold`:
- Return null (SM-compact result would still be over threshold, fall back to full compact)

### Key Difference from Full Compact

- **No LLM call** — uses pre-extracted session memory as the summary
- Session memory sections are truncated via `truncateSessionMemoryForCompact()` if oversized
- Old compact boundary messages are filtered from messagesToKeep to prevent double-pruning

---

## 8. Micro-Compact vs Full Compact Decision Tree

```
microcompactMessages(messages, toolUseContext, querySource):
  |
  +-- clearCompactWarningSuppression()
  |
  +-- TIER 0: maybeTimeBasedMicrocompact(messages, querySource)
  |   +-- evaluateTimeBasedTrigger():
  |   |   +-- Config disabled? -> null
  |   |   +-- querySource undefined or not main thread? -> null
  |   |   +-- No last assistant message? -> null
  |   |   +-- gapMinutes = (now - lastAssistant.timestamp) / 60_000
  |   |   +-- gapMinutes < gapThresholdMinutes (default 60)? -> null
  |   |   +-- Return {gapMinutes, config}
  |   |
  |   +-- Collect compactable tool IDs (from COMPACTABLE_TOOLS set)
  |   +-- keepRecent = max(1, config.keepRecent)  // Floor at 1 to avoid slice(-0) bug
  |   +-- keepSet = last keepRecent compactable tool IDs
  |   +-- clearSet = all compactable tools NOT in keepSet
  |   +-- IF clearSet empty -> null
  |   |
  |   +-- Replace tool_result content with TIME_BASED_MC_CLEARED_MESSAGE
  |   +-- IF tokensSaved == 0 -> null
  |   |
  |   +-- suppressCompactWarning()
  |   +-- resetMicrocompactState()  // Invalidate cached MC state (cache is cold)
  |   +-- notifyCacheDeletion()     // Suppress false-positive cache break detection
  |   +-- Return {messages: result}  // Short-circuits; skips cached MC
  |
  +-- TIER 1: feature('CACHED_MICROCOMPACT') path
  |   +-- isCachedMicrocompactEnabled()?
  |   +-- isModelSupportedForCacheEditing(model)?
  |   +-- isMainThreadSource(querySource)?  // prefix-matches 'repl_main_thread'
  |   |   (prevents forked agents from corrupting global cachedMCState)
  |   +-- IF all true -> cachedMicrocompactPath(messages, querySource)
  |       +-- Register new tool_results into cachedMCState
  |       +-- getToolResultsToDelete(state) based on triggerThreshold/keepRecent from GrowthBook
  |       +-- Create cache_edits block (API-layer, does NOT modify local messages)
  |       +-- Queue as pendingCacheEdits for next API request
  |       +-- suppressCompactWarning()
  |       +-- notifyCacheDeletion()
  |       +-- Return {messages (unchanged), compactionInfo: {pendingCacheEdits}}
  |
  +-- DEFAULT: return {messages} (no compaction; autocompact handles pressure)
```

### COMPACTABLE_TOOLS Set

Only these tool results are eligible for microcompaction:
- `FileReadTool` (Read)
- All `SHELL_TOOL_NAMES` (Bash)
- `GrepTool` (Grep)
- `GlobTool` (Glob)
- `WebSearchTool`
- `WebFetchTool`
- `FileEditTool` (Edit)
- `FileWriteTool` (Write)

---

## 9. Time-Based Microcompact (Tier 0)

**Rationale**: When the gap since the last assistant message exceeds the threshold (default 60 minutes), the server-side prompt cache has expired. The full prefix will be rewritten regardless, so clearing old tool results before the request shrinks what gets rewritten.

**Key behaviors**:
- **Mutates message content directly** (unlike cached MC which uses API-layer cache_edits)
- **Requires explicit main-thread querySource** (undefined is NOT treated as main-thread, unlike cached MC)
- Replaces content with `'[Old tool result content cleared]'`
- Always keeps at least 1 recent tool result (`Math.max(1, config.keepRecent)`) to avoid `slice(-0)` returning full array
- Resets cached MC state because those stale tool IDs no longer have valid server-side entries
- Fires `notifyCacheDeletion()` to prevent false-positive cache break detection
- **Short-circuits**: If time-based MC fires, cached MC is skipped entirely

**evaluateTimeBasedTrigger** is also exported for use by other pre-request paths (e.g., snip force-apply) without coupling to the clearing action.

---

## 10. REACTIVE_COMPACT and CONTEXT_COLLAPSE Mutual Exclusion

Both `REACTIVE_COMPACT` and `CONTEXT_COLLAPSE` suppress proactive autocompact via `shouldAutoCompact()`, but through different mechanisms:

### REACTIVE_COMPACT

```typescript
if (feature('REACTIVE_COMPACT')) {
  if (getFeatureValue_CACHED_MAY_BE_STALE('tengu_cobalt_raccoon', false)) {
    return false  // Suppress proactive autocompact
  }
}
```

- **Ant-only** (feature flag string excluded from external builds)
- When active: autocompact never fires proactively; instead, reactive compact catches the API's `prompt-too-long` (413) error
- Side effect: `trySessionMemoryCompaction` is never reached via the query loop (but `/compact` manual call still tries SM first)

### CONTEXT_COLLAPSE

```typescript
if (feature('CONTEXT_COLLAPSE')) {
  if (isContextCollapseEnabled()) {
    return false  // Suppress proactive autocompact
  }
}
```

- Context Collapse IS the context management system when enabled
- Operates at **90% commit / 95% blocking-spawn** thresholds
- Autocompact's effective-13K buffer sits at ~93% of effective window, right between collapse's 90% and 95% thresholds
- If both ran simultaneously: autocompact would race collapse and usually win, "nuking granular context that collapse was about to save"
- **Gating in `shouldAutoCompact()`** (not `isAutoCompactEnabled()`) keeps:
  - `reactiveCompact` alive as the 413 fallback (checks `isAutoCompactEnabled` directly)
  - Session memory compact working
  - Manual `/compact` working
- Uses lazy `require()` to break init-time circular dependency (this file exports `getEffectiveContextWindowSize` which collapse imports)

### marble_origami Guard

```typescript
if (feature('CONTEXT_COLLAPSE')) {
  if (querySource === 'marble_origami') {
    return false  // Never autocompact the ctx-agent
  }
}
```

- `marble_origami` is the context-collapse agent (ctx-agent)
- If its context blows up and autocompact fires, `runPostCompactCleanup` calls `resetContextCollapse()` which destroys the MAIN thread's committed log (module-level state shared across forks)

### Post-Compact Cleanup Interaction

`runPostCompactCleanup()` conditionally resets context collapse:
- Only for main-thread compacts (`querySource` starts with `repl_main_thread` or is `sdk` or undefined)
- Subagents (`agent:*`) share module-level state; resetting when a subagent compacts would corrupt main thread state

---

## 11. Error Handling and Retry Logic

### Prompt-Too-Long (PTL) Retry in Full Compact

```
compactConversation() / partialCompactConversation():
  for (;;):
    response = streamCompactSummary(messagesToSummarize, ...)
    summary = getAssistantMessageText(response)

    IF summary starts with PROMPT_TOO_LONG_ERROR_MESSAGE:
      ptlAttempts++
      IF ptlAttempts <= MAX_PTL_RETRIES (3):
        truncated = truncateHeadForPTLRetry(messagesToSummarize, response)
        IF truncated:
          messagesToSummarize = truncated
          retryCacheSafeParams.forkContextMessages = truncated
          continue
      throw ERROR_MESSAGE_PROMPT_TOO_LONG
```

**truncateHeadForPTLRetry algorithm**:
1. Strip own synthetic PTL_RETRY_MARKER from previous retry (prevents stall on retry 2+)
2. Group messages by API round
3. If tokenGap parseable from error: drop groups until accumulated tokens >= gap
4. If tokenGap not parseable (Vertex/Bedrock): drop 20% of groups (`Math.floor(groups.length * 0.2)`)
5. Always keep at least 1 group
6. If first remaining message is assistant: prepend synthetic user marker (API requires user-first)

### Streaming Retry (Fallback Path Only)

```
tengu_compact_streaming_retry flag (default: false)
maxAttempts = retryEnabled ? MAX_COMPACT_STREAMING_RETRIES (2) : 1

On no response + attempts left:
  logEvent('tengu_compact_streaming_retry', {attempt, ...})
  sleep(getRetryDelay(attempt), abortController.signal)
  continue

On final failure:
  throw ERROR_MESSAGE_INCOMPLETE_RESPONSE
    = 'Compaction interrupted - This may be due to network issues -- please try again.'
```

### Error Categories

| Error | Constant | Behavior |
|-------|----------|----------|
| User abort (ESC) | `ERROR_MESSAGE_USER_ABORT` | Not logged as error; not counted in circuit breaker |
| Not enough messages | `ERROR_MESSAGE_NOT_ENOUGH_MESSAGES` | No error notification shown |
| Prompt too long | `ERROR_MESSAGE_PROMPT_TOO_LONG` | After 3 PTL retries exhausted |
| Incomplete response | `ERROR_MESSAGE_INCOMPLETE_RESPONSE` | After streaming retries exhausted |
| API error prefix | (detected by `startsWithApiErrorPrefix`) | Thrown as-is |
| No summary text | (custom message) | "Failed to generate conversation summary" |

### Error Notification Policy

- **Manual compact**: Shows error notification for all errors except USER_ABORT and NOT_ENOUGH_MESSAGES
- **Auto compact**: No error notification (failures are retried next turn; notification would confuse when it eventually succeeds)

---

## 12. Compact Warning State

`compactWarningState.ts` manages a simple boolean store:

- `suppressCompactWarning()`: Called after successful compaction (any tier) to suppress the "context left until autocompact" warning since accurate token counts aren't available until the next API response
- `clearCompactWarningSuppression()`: Called at the start of every `microcompactMessages()` invocation to reset suppression for the new attempt

Warning state structure:
```typescript
{
  percentLeft: number,
  isAboveWarningThreshold: boolean,   // yellow warning
  isAboveErrorThreshold: boolean,     // red warning
  isAboveAutoCompactThreshold: boolean, // triggers auto-compact
  isAtBlockingLimit: boolean,         // blocks input
}
```

---

## 13. Summarization Prompt Structure

The compact prompt (`prompt.ts`) has three variants:

### BASE_COMPACT_PROMPT (Full Compact)

9-section structured summary:
1. Primary Request and Intent
2. Key Technical Concepts
3. Files and Code Sections (with code snippets)
4. Errors and Fixes
5. Problem Solving
6. All User Messages (non-tool-result)
7. Pending Tasks
8. Current Work
9. Optional Next Step (with verbatim quotes)

### PARTIAL_COMPACT_PROMPT (direction='from')

Same 9 sections, but scoped to "RECENT portion of the conversation" (messages after retained context).

### PARTIAL_COMPACT_UP_TO_PROMPT (direction='up_to')

Sections 1-7 identical, then:
8. Work Completed (instead of Current Work)
9. Context for Continuing Work (instead of Next Step)

### Common Elements

- All prompts wrapped with `NO_TOOLS_PREAMBLE` (front) and `NO_TOOLS_TRAILER` (end)
- `<analysis>` block serves as drafting scratchpad (stripped by `formatCompactSummary()`)
- `<summary>` tags replaced with "Summary:" header
- Custom instructions appended after "Additional Instructions:" if provided
- Proactive/autonomous mode continuation instruction appended when active

### Post-Summary User Message

```
"This session is being continued from a previous conversation that ran out of context.
The summary below covers the earlier portion of the conversation.
{formatted summary}
If you need specific details... read the full transcript at: {transcriptPath}
{if recentMessagesPreserved: "Recent messages are preserved verbatim."}
Continue the conversation from where it left off without asking the user any further questions.
Resume directly -- do not acknowledge the summary..."
```

---

## 14. Post-Compact Cleanup

`runPostCompactCleanup()` centralizes cache/state invalidation for all compaction paths:

| Action | Main-Thread Only | Purpose |
|--------|:---:|---------|
| `resetMicrocompactState()` | No | Clear cached MC tool tracking + pending edits |
| `resetContextCollapse()` | Yes | Reset collapse committed log (if CONTEXT_COLLAPSE) |
| `getUserContext.cache.clear()` | Yes | Clear memoized outer context layer |
| `resetGetMemoryFilesCache('compact')` | Yes | Re-arm InstructionsLoaded hook for CLAUDE.md |
| `clearSystemPromptSections()` | No | Clear cached system prompt sections |
| `clearClassifierApprovals()` | No | Clear tool permission classifier cache |
| `clearSpeculativeChecks()` | No | Clear bash permission speculative checks |
| `clearBetaTracingState()` | No | Clear beta session tracing state |
| `sweepFileContentCache()` | No | Clear file content cache (if COMMIT_ATTRIBUTION) |
| `clearSessionMessagesCache()` | No | Clear session message cache |

**Not cleaned**: `sentSkillNames` (intentionally preserved; re-injecting ~4K skill_listing is wasteful cache_creation).

---

## 15. Token Estimation for Messages

`estimateMessageTokens()` in `microCompact.ts`:

- Walks all user/assistant messages, counting text blocks via `roughTokenCountEstimation()`
- `tool_result`: Sums text content + 2,000 per image/document
- `thinking`: Counts thinking text only (not JSON wrapper or signature)
- `redacted_thinking`: Counts data field
- `tool_use`: Counts name + JSON-stringified input
- Other block types (server_tool_use, web_search_tool_result): JSON-stringified
- **Pads estimate by 4/3** (conservative since approximating)

---

## 16. Image Stripping for Compact

`stripImagesFromMessages()` removes images/documents before sending to the compact API:
- Replaces image blocks with `[image]` text marker
- Replaces document blocks with `[document]` text marker
- Handles nested images inside tool_result content arrays
- Only processes user messages (assistant messages don't contain images)
- Prevents compact API call itself from hitting prompt-too-long (especially in CCD sessions with frequent image attachments)

---

## 17. System Prompt Construction

Components assembled by REPL screen:
1. CLI system prompt prefix — security + tool usage guidelines
2. CLAUDE.md contents — project + user instructions
3. Memory files — relevant memories from `~/.claude/projects/<path>/`
4. MCP instructions delta — incremental tool instructions
5. User/system context key-value pairs

---

## 18. Environment Overrides

| Variable | Effect |
|----------|--------|
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | Cap effective context window |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | Set threshold as percentage |
| `CLAUDE_CODE_BLOCKING_LIMIT_OVERRIDE` | Override blocking limit |
| `DISABLE_COMPACT` | Disable all compaction |
| `DISABLE_AUTO_COMPACT` | Disable auto-compact only |
| `ENABLE_CLAUDE_CODE_SM_COMPACT` | Force-enable session memory compact |
| `DISABLE_CLAUDE_CODE_SM_COMPACT` | Force-disable session memory compact |

---

## 19. Key Architectural Observations

1. **Layered defense**: Four tiers ensure context never exceeds limits, with graceful degradation from lightweight (time-based clear) to heavyweight (LLM summarization)

2. **Cache-aware design**: Time-based MC mutates content directly (cache is cold); cached MC uses API-layer `cache_edits` (cache is warm); the distinction is fundamental to each approach

3. **Forked agent trade-off**: Cache sharing saves ~98% of cache_creation tokens on compaction, but introduces complexity (tool set inheritance for cache-key match, NO_TOOLS_PREAMBLE for model discipline, maxOutputTokens cannot be set)

4. **Mutual exclusion is deliberate**: REACTIVE_COMPACT and CONTEXT_COLLAPSE each suppress proactive autocompact because they implement their own context management philosophy. Autocompact at ~93% would race collapse (90%/95%) and destroy granular context

5. **Session memory compaction avoids LLM calls entirely**: When SM is available, it replaces the summary with pre-extracted session memory + preserved recent messages, making compaction nearly instant

6. **Circuit breaker prevents waste**: The 3-failure breaker was motivated by real data (250K wasted API calls/day from 1,279 sessions stuck in failure loops)

7. **Post-compact restoration is bounded**: Max 5 files, 5K tokens each, 50K total budget, plus skill content capped at 5K per skill / 25K total. This prevents post-compact context from immediately re-triggering compaction
