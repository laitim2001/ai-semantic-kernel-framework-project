# Wave 4 Path 4: Auto-Compact Trigger Flow (Context Window Management)

> **Verification Date**: 2026-04-01 | **Wave**: 4 | **Path**: E2E #4
> **Source Files**: `src/query.ts`, `src/services/compact/autoCompact.ts`, `src/services/compact/compact.ts`, `src/services/compact/compactWarningState.ts`, `src/services/compact/microCompact.ts`, `src/services/compact/sessionMemoryCompact.ts`
> **Verified Against**: Existing `data-flow.md` Section 5, `03-ai-engine/context-management.md`

---

## 1. End-to-End Flow Summary

```
query.ts main loop iteration
  │
  ├─ 1. microcompactMessages()          ← lightweight pre-pass (time-based or cached MC)
  │     ├─ Time-based MC: clear old tool results when cache is cold
  │     └─ Cached MC: queue cache_edits to delete old tool results server-side
  │
  ├─ 2. contextCollapse (if enabled)    ← alternative context management system
  │
  ├─ 3. autoCompactIfNeeded()           ← main compaction decision point
  │     ├─ Circuit breaker check (MAX_CONSECUTIVE_FAILURES = 3)
  │     ├─ shouldAutoCompact() threshold check
  │     ├─ trySessionMemoryCompaction()  ← fast path (no API call)
  │     └─ compactConversation()         ← full LLM summarization via forked agent
  │
  └─ 4. Post-compact: replace messages, reset tracking, yield boundary + summary
```

---

## 2. Threshold Constants (Verified from Source)

| Constant | Value | Location | Purpose |
|----------|-------|----------|---------|
| `MAX_OUTPUT_TOKENS_FOR_SUMMARY` | 20,000 | autoCompact.ts:30 | Reserved for compact output (based on p99.99 = 17,387) |
| `AUTOCOMPACT_BUFFER_TOKENS` | 13,000 | autoCompact.ts:62 | Headroom before auto-compact fires |
| `WARNING_THRESHOLD_BUFFER_TOKENS` | 20,000 | autoCompact.ts:63 | UI yellow warning buffer |
| `ERROR_THRESHOLD_BUFFER_TOKENS` | 20,000 | autoCompact.ts:64 | UI red warning buffer |
| `MANUAL_COMPACT_BUFFER_TOKENS` | 3,000 | autoCompact.ts:65 | Blocking limit buffer |
| `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES` | 3 | autoCompact.ts:70 | Circuit breaker limit |
| `POST_COMPACT_TOKEN_BUDGET` | 50,000 | compact.ts:123 | Max tokens for post-compact file attachments |
| `POST_COMPACT_MAX_FILES_TO_RESTORE` | 5 | compact.ts:122 | Files re-attached after compact |
| `POST_COMPACT_MAX_TOKENS_PER_FILE` | 5,000 | compact.ts:124 | Per-file token cap |
| `POST_COMPACT_MAX_TOKENS_PER_SKILL` | 5,000 | compact.ts:129 | Per-skill token cap |
| `POST_COMPACT_SKILLS_TOKEN_BUDGET` | 25,000 | compact.ts:130 | Total skills token budget |
| `MAX_COMPACT_STREAMING_RETRIES` | 2 | compact.ts:131 | Streaming fallback retries |
| `MAX_PTL_RETRIES` | 3 | compact.ts:227 | Prompt-too-long retry limit |
| SM default `minTokens` | 10,000 | sessionMemoryCompact.ts:58 | Min tokens to preserve post-SM-compact |
| SM default `minTextBlockMessages` | 5 | sessionMemoryCompact.ts:59 | Min text messages to keep |
| SM default `maxTokens` | 40,000 | sessionMemoryCompact.ts:60 | Max tokens to preserve (hard cap) |

### Threshold Formula

```
effectiveContextWindow = min(contextWindowForModel, CLAUDE_CODE_AUTO_COMPACT_WINDOW)
                       - min(maxOutputTokensForModel, 20_000)

autoCompactThreshold   = effectiveContextWindow - 13_000

warningThreshold       = autoCompactThreshold - 20_000   (if auto-compact enabled)
                       = effectiveContextWindow - 20_000  (if disabled)

blockingLimit          = effectiveContextWindow - 3_000
```

**Percentage override**: `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` env var can set threshold as % of effective window, taking the minimum of percentage-based and standard threshold.

---

## 3. Decision Tree: `shouldAutoCompact()`

```
shouldAutoCompact(messages, model, querySource, snipTokensFreed)
  │
  ├─ querySource === 'session_memory' | 'compact'? → false (recursion guard)
  │
  ├─ querySource === 'marble_origami'? → false (ctx-agent guard, gated by CONTEXT_COLLAPSE)
  │
  ├─ isAutoCompactEnabled() === false? → false
  │     ├─ DISABLE_COMPACT env truthy? → disabled
  │     ├─ DISABLE_AUTO_COMPACT env truthy? → disabled
  │     └─ userConfig.autoCompactEnabled === false? → disabled
  │
  ├─ REACTIVE_COMPACT feature + tengu_cobalt_raccoon gate? → false (reactive-only mode)
  │
  ├─ CONTEXT_COLLAPSE feature + isContextCollapseEnabled()? → false
  │     (collapse owns headroom at 90% commit / 95% blocking;
  │      autocompact at ~93% would race and nuke granular context)
  │
  ├─ tokenCount = tokenCountWithEstimation(messages) - snipTokensFreed
  │
  └─ tokenCount >= autoCompactThreshold? → true
```

---

## 4. Execution: `autoCompactIfNeeded()`

```
autoCompactIfNeeded(messages, toolUseContext, cacheSafeParams, querySource, tracking, snipTokensFreed)
  │
  ├─ DISABLE_COMPACT? → { wasCompacted: false }
  │
  ├─ Circuit breaker: tracking.consecutiveFailures >= 3? → { wasCompacted: false }
  │     (BQ 2026-03-10: 1,279 sessions had 50+ failures, wasting ~250K API calls/day)
  │
  ├─ shouldAutoCompact() === false? → { wasCompacted: false }
  │
  ├─ Build recompactionInfo (isRecompactionInChain, turnsSincePreviousCompact, etc.)
  │
  ├─ FAST PATH: trySessionMemoryCompaction(messages, agentId, threshold)
  │     │
  │     ├─ Success? → reset lastSummarizedMessageId, runPostCompactCleanup,
  │     │             notifyCompaction, markPostCompaction
  │     │             → { wasCompacted: true, compactionResult }
  │     └─ null? → fall through to full compact
  │
  ├─ FULL PATH: compactConversation(messages, ..., isAutoCompact=true)
  │     │
  │     ├─ Success? → reset lastSummarizedMessageId, runPostCompactCleanup
  │     │             → { wasCompacted: true, consecutiveFailures: 0 }
  │     │
  │     └─ Error?
  │           ├─ User abort? → silently ignore
  │           └─ Other? → logError, increment consecutiveFailures
  │                        If >= 3: log circuit breaker tripped
  │                        → { wasCompacted: false, consecutiveFailures: N+1 }
```

---

## 5. Full Compaction: `compactConversation()` Deep Dive

### 5.1 Pre-Compact Phase

1. **Pre-compact hooks**: `executePreCompactHooks({ trigger: 'auto'|'manual' })` — external tools save state
2. **Merge hook instructions** into customInstructions
3. **UI signals**: `setStreamMode('requesting')`, `onCompactProgress({ type: 'compact_start' })`

### 5.2 Summary Generation (Forked Agent)

```
streamCompactSummary()
  │
  ├─ promptCacheSharingEnabled? (default: true, GB gate as kill-switch)
  │     │
  │     ├─ YES: runForkedAgent({
  │     │     promptMessages: [summaryRequest],
  │     │     cacheSafeParams,           ← shares parent's prompt cache prefix
  │     │     querySource: 'compact',
  │     │     maxTurns: 1,
  │     │     skipCacheWrite: true,
  │     │     canUseTool: createCompactCanUseTool()  ← rejects all tools
  │     │   })
  │     │   ├─ Success with text? → return assistantMsg
  │     │   ├─ API abort / no text? → fall through to streaming path
  │     │   └─ Error? → fall through to streaming path
  │     │
  │     └─ NO / FALLBACK: queryModelWithStreaming({
  │           messages: stripImagesFromMessages(stripReinjectedAttachments(messages)) + [summaryRequest],
  │           maxOutputTokensOverride: COMPACT_MAX_OUTPUT_TOKENS,
  │           systemPrompt: [compactPrompt system instructions],
  │           signal: context.abortController.signal
  │         })
  │
  ├─ Keep-alive: 30s interval sends heartbeat + re-emits 'compacting' SDK status
  │
  └─ PTL retry loop (up to MAX_PTL_RETRIES = 3):
        If summary starts with PROMPT_TOO_LONG_ERROR_MESSAGE:
          → truncateHeadForPTLRetry() drops oldest API-round groups
          → Retry with truncated messages
```

**Key design**: The forked agent does NOT set `maxOutputTokens` — doing so would clamp `budget_tokens` via `Math.min(budget, maxOutputTokens-1)`, creating a thinking config mismatch that invalidates the shared prompt cache.

### 5.3 Post-Compact Phase

1. **Clear file state cache** (`readFileState.clear()`, `loadedNestedMemoryPaths.clear()`)
2. **Generate file attachments** (up to 5 files, 5K tokens each, 50K budget)
3. **Re-announce deltas**: deferred tools, agent listing, MCP instructions
4. **Run session start hooks** (restore CLAUDE.md etc.)
5. **Create boundary marker**: `SystemCompactBoundaryMessage` with pre-compact token count, pre-compact discovered tools
6. **Create summary message**: `UserMessage` with `isCompactSummary: true`, `isVisibleInTranscriptOnly: true`
7. **Notify cache break detection**: reset baseline so post-compact cache drop is not flagged
8. **Re-append session metadata**: keeps custom title/tag in 16KB tail window for `--resume`
9. **Execute post-compact hooks**

### 5.4 Return Structure: `CompactionResult`

```typescript
{
  boundaryMarker: SystemCompactBoundaryMessage,
  summaryMessages: UserMessage[],         // The LLM-generated summary
  attachments: AttachmentMessage[],       // File re-attachments, plan, skills, deltas
  hookResults: HookResultMessage[],       // Session start hook results
  messagesToKeep?: Message[],             // For SM-compact: preserved recent messages
  preCompactTokenCount?: number,
  postCompactTokenCount?: number,         // Actually the compact API call's total usage
  truePostCompactTokenCount?: number,     // Estimated resulting context size
  compactionUsage?: { input_tokens, output_tokens, cache_* }
}
```

Post-compact message ordering: `boundaryMarker → summaryMessages → messagesToKeep → attachments → hookResults`

---

## 6. Microcompact: Lightweight Pre-Pass

Runs BEFORE autocompact in the query loop (query.ts:414). Three paths:

### 6.1 Time-Based Microcompact

- **Trigger**: Gap since last assistant message exceeds `gapThresholdMinutes` (from GrowthBook config)
- **Action**: Content-clears all but most recent N compactable tool results (replaces with `[Old tool result content cleared]`)
- **Mutates** messages directly (cache is cold anyway)
- **Resets** cached MC state to avoid stale tool ID references
- **Keep floor**: At least 1 tool result always kept (`Math.max(1, config.keepRecent)`)

### 6.2 Cached Microcompact (cache_edits API)

- **Trigger**: Count-based threshold from GrowthBook config
- **Action**: Queues `cache_edits` blocks for API layer to delete old tool results server-side
- **Does NOT mutate** local messages (preserves cached prefix)
- **Main-thread only**: Prevents forked agents from corrupting global state
- **Requires**: Model support for cache editing

### 6.3 Compactable Tools Set

Only these tool results are candidates for microcompact:
- `FileReadTool`, `FileEditTool`, `FileWriteTool`
- Shell tools (all variants)
- `GrepTool`, `GlobTool`
- `WebSearchTool`, `WebFetchTool`

---

## 7. Session Memory Compaction: Fast Path

`trySessionMemoryCompaction()` — avoids the LLM API call entirely.

### Prerequisites
- `tengu_session_memory` AND `tengu_sm_compact` feature flags both true (or `ENABLE_CLAUDE_CODE_SM_COMPACT` env)
- Session memory file exists and is not empty/template-only
- Config loaded from GrowthBook (`tengu_sm_compact_config`)

### Algorithm: `calculateMessagesToKeepIndex()`

```
1. Find lastSummarizedMessageId in messages
2. Start with messages after that index
3. Calculate tokens + text-block message count
4. If below minimums (10K tokens OR 5 text messages), expand backwards
5. Stop expanding if maxTokens (40K) reached
6. adjustIndexToPreserveAPIInvariants():
   - Don't split tool_use/tool_result pairs
   - Include thinking blocks sharing same message.id
   - Floor at last compact boundary (prevents loader walk bypass)
```

### Post-SM-Compact Threshold Check

After building result, if `postCompactTokenCount >= autoCompactThreshold`, returns `null` (falls through to full compact). This prevents SM-compact from producing a result that would immediately re-trigger autocompact.

---

## 8. Warning State: `compactWarningState.ts`

Simple boolean store using `createStore<boolean>(false)`:
- `suppressCompactWarning()` — called after successful compaction
- `clearCompactWarningSuppression()` — called at start of new microcompact attempt

This prevents showing stale "X% context remaining" warnings immediately after compaction when accurate token counts are not yet available.

---

## 9. Query Loop Integration (query.ts)

```typescript
// State tracked across loop iterations:
type State = {
  autoCompactTracking: AutoCompactTrackingState | undefined
  // { compacted: boolean, turnCounter: number, turnId: string, consecutiveFailures?: number }
}

// Per-iteration flow:
1. microcompactMessages(messagesForQuery, toolUseContext, querySource)
2. contextCollapse.applyCollapsesIfNeeded() [if CONTEXT_COLLAPSE]
3. deps.autocompact(messagesForQuery, toolUseContext, cacheSafeParams, querySource, tracking, snipTokensFreed)
4. If compactionResult:
   - Log tengu_auto_compact_succeeded event
   - Reset tracking = { compacted: true, turnId: uuid(), turnCounter: 0, consecutiveFailures: 0 }
   - messagesForQuery = buildPostCompactMessages(compactionResult)
   - yield post-compact messages
5. If consecutiveFailures returned:
   - Update tracking with new failure count
   - tracking = { ...tracking, consecutiveFailures }
```

---

## 10. Verification Against Existing Analysis

### `data-flow.md` Section 5 (Accuracy: 7/10)

| Claim | Verdict | Detail |
|-------|---------|--------|
| "CRITICAL (> 85%): trigger auto-compact" | **Imprecise** | The threshold is `effectiveContextWindow - 13_000`, not a fixed 85%. For a 200K model, 13K/180K = ~93% utilization |
| "compact.ts -> call API with compaction prompt" | **Correct** | Via `streamCompactSummary()` using forked agent |
| "Replace old messages with summary" | **Correct** | Boundary + summary + attachments + hookResults |
| "Insert SDKCompactBoundaryMessage marker" | **Naming imprecise** | Actually `SystemCompactBoundaryMessage` (type: `'system'`) |
| Lists "apiMicrocompact.ts" as strategy | **Outdated** | File is now `cachedMicrocompact.ts` (cache_edits API path within microCompact.ts) |
| "WARNING (70-85%)" range | **Imprecise** | Warning is `threshold - 20_000`, not a fixed percentage range |

### `03-ai-engine/context-management.md` (Accuracy: 9/10)

| Claim | Verdict | Detail |
|-------|---------|--------|
| Threshold formula | **Correct** | Matches source exactly |
| "p99.99 of compact summary output being 17,387 tokens" | **Correct** | Comment at autoCompact.ts:29 |
| Circuit breaker = 3 | **Correct** | MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3 |
| Priority: session memory first, then full compact | **Correct** | autoCompact.ts:288-313 |
| "runForkedAgent() — child conversation with shared prompt cache" | **Correct** | compact.ts:1188 |
| Lists "API micro" as `apiMicrocompact.ts` | **Outdated** | Now handled by cached microcompact path inside microCompact.ts |
| Missing: time-based MC, context collapse interaction, PTL retry loop, SM threshold check | **Gap** | These are significant mechanisms not documented |
| Missing: REACTIVE_COMPACT and CONTEXT_COLLAPSE suppression of autocompact | **Gap** | Important interaction not documented |

---

## 11. Key Findings

1. **Three-tier compaction hierarchy**: microcompact (pre-pass) -> session memory (fast, no API) -> full LLM compact (expensive). This is well-designed for cost optimization.

2. **Circuit breaker prevents API waste**: The 3-failure limit was added after discovering 1,279 sessions with 50+ consecutive failures wasting ~250K API calls/day globally (BQ 2026-03-10).

3. **Context Collapse mutual exclusion**: When context collapse is enabled, autocompact is suppressed because collapse operates at 90% commit / 95% blocking, and autocompact at ~93% would race it. This is a critical interaction not documented in the existing analysis.

4. **Forked agent cache sharing**: The compaction agent deliberately omits `maxOutputTokens` to avoid invalidating the shared prompt cache prefix. This is a subtle but important performance optimization.

5. **SM-compact post-threshold guard**: Session memory compaction checks if its result would still exceed the autocompact threshold, and falls through to full compact if so. This prevents infinite recompaction loops.

6. **PTL self-rescue**: When the compact request itself hits prompt-too-long, it truncates oldest API-round groups and retries up to 3 times, preventing the user from being stuck.
