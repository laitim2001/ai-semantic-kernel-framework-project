# Wave 44: Background Intelligence Services Deep Analysis

> **Date**: 2026-04-01
> **Scope**: autoDream (4 files), PromptSuggestion (2 files), tips (3 files), toolUseSummary (1 file), AgentSummary (1 file)
> **Total Files**: 11 source files
> **Source**: `CC-Source/src/services/`

---

## 1. autoDream — Background Memory Consolidation

### Files
| File | LOC | Purpose |
|------|-----|---------|
| `autoDream.ts` | 325 | Main orchestrator — gate checks, forked agent execution, progress watching |
| `config.ts` | 22 | Feature flag leaf module — `isAutoDreamEnabled()` |
| `consolidationLock.ts` | 141 | File-based distributed lock using mtime as `lastConsolidatedAt` timestamp |
| `consolidationPrompt.ts` | 66 | Builds the 4-phase `/dream` consolidation prompt |

### Purpose
Automatically consolidates scattered session memories into durable, well-organized memory files. Operates as a "dreaming" pass — reviewing recent sessions, merging new signal into existing topic files, pruning stale entries, and keeping the memory index (`CLAUDE.md`) tight.

### Trigger Conditions (Gate Order — Cheapest First)
1. **Feature gate**: `isAutoDreamEnabled()` — user setting overrides GrowthBook `tengu_onyx_plover` flag
2. **Environment gate**: Not in KAIROS mode, not remote mode, autoMemory must be enabled
3. **Time gate**: Hours since `lastConsolidatedAt` >= `minHours` (default 24h)
4. **Scan throttle**: At least 10 minutes since last session scan (prevents repeated stat storms when time-gate passes but session-gate doesn't)
5. **Session gate**: >= `minSessions` (default 5) transcripts with mtime > lastConsolidatedAt (excludes current session)
6. **Lock gate**: No other process mid-consolidation (PID-based lock file)

### Execution Model
- **Background/Forked**: Runs via `runForkedAgent()` as a forked subagent (`forkLabel: 'auto_dream'`)
- **Entry point**: `executeAutoDream()` called from `stopHooks` (post-sampling hooks) on every turn
- **Per-turn cost when enabled**: One GrowthBook cache read + one `stat()` call (extremely cheap)
- **Tool constraints**: Bash restricted to read-only commands only (`ls`, `find`, `grep`, `cat`, etc.)
- **Transcript**: Skipped (`skipTranscript: true`) — does not pollute session history
- **Task UI**: Registers a `DreamTask` for user visibility; tracks files touched, turn progress

### Consolidation Prompt (4 Phases)
1. **Orient** — `ls` memory directory, read index, skim existing topic files
2. **Gather recent signal** — Check daily logs, detect drifted memories, narrow grep on JSONL transcripts
3. **Consolidate** — Write/update memory files, merge rather than duplicate, convert relative dates to absolute, delete contradicted facts
4. **Prune and index** — Keep index under max lines/25KB, one-liner entries, resolve contradictions

### Lock Mechanism (`consolidationLock.ts`)
- Lock file path: `<autoMemPath>/.consolidate-lock`
- **mtime IS `lastConsolidatedAt`** — the file's modification time doubles as the consolidation timestamp
- Body contains holder PID for liveness detection
- Stale threshold: 60 minutes (PID reuse guard)
- Race resolution: Last writer wins PID → loser bails on re-read verification
- Rollback on failure: `utimes()` rewinds mtime to pre-acquire value

### Data Flow
```
stopHooks (every turn)
  → executeAutoDream()
    → gate checks (feature → env → time → throttle → session → lock)
    → buildConsolidationPrompt(memoryRoot, transcriptDir, extra)
    → runForkedAgent({..., canUseTool: createAutoMemCanUseTool})
    → makeDreamProgressWatcher → tracks text + file_path from Edit/Write
    → completeDreamTask() → appendSystemMessage("Improved N files")
    → logEvent('tengu_auto_dream_completed')
```

### Integration Points
- `backgroundHousekeeping` — initialization alongside `initExtractMemories`
- `DreamTask` system — `registerDreamTask`, `addDreamTurn`, `completeDreamTask`, `failDreamTask`
- `extractMemories` — shares `createAutoMemCanUseTool` for tool permission boundary
- `forkedAgent` — shared fork infrastructure with `createCacheSafeParams`
- Analytics — `tengu_auto_dream_fired`, `tengu_auto_dream_completed`, `tengu_auto_dream_failed`

### Key Design Decisions
- Closure-scoped state inside `initAutoDream()` (not module-level) so tests get fresh state
- `isForced()` always returns `false` in production (ant-build-only test override)
- Current session excluded from session count (its mtime is always recent)
- Lock rollback on fork failure ensures time-gate passes again; scan throttle provides backoff

---

## 2. PromptSuggestion — Predictive Next-Prompt Generation

### Files
| File | LOC | Purpose |
|------|-----|---------|
| `promptSuggestion.ts` | 524 | Core suggestion engine — generation, filtering, suppression, analytics |
| `speculation.ts` | 992 | Speculative execution — pre-runs suggested prompt in sandboxed overlay |

### Purpose
Predicts what the user will type next and displays it as a suggestion. When the user accepts, the speculation engine may have already pre-executed the work, providing instant results.

### Trigger Conditions
1. **Feature flag**: GrowthBook `tengu_chomp_inflection` + user setting `promptSuggestionEnabled`
2. **Environment**: Not non-interactive (not print mode, piped input, SDK)
3. **Swarm check**: Not a swarm teammate (only leader shows suggestions)
4. **Conversation maturity**: At least 2 assistant turns
5. **Error check**: Last assistant message must not be an API error
6. **Cache check**: Parent request uncached tokens <= 10,000 (avoids expensive re-processing)
7. **State checks**: No pending permission dialogs, no active elicitation, not in plan mode, no rate limit

### Execution Model
- **Background/Forked**: Runs via `runForkedAgent()` with `forkLabel: 'prompt_suggestion'`
- **Entry point**: `executePromptSuggestion()` called from post-sampling hooks, only for `repl_main_thread`
- **Abortable**: `currentAbortController` allows cancellation when user starts typing
- **Cache optimization**: Deliberately does NOT override any API parameter (effort, maxOutputTokens) — empirically, any divergence busts the prompt cache (PR #18143 caused 45x spike in cache writes)
- **Tool denial**: Tools denied via callback (not `tools:[]`) to preserve cache key
- **skipCacheWrite**: True — suggestion results don't need caching

### Suggestion Prompt Design
- System prompt: `[SUGGESTION MODE]` — predict what user would naturally type next
- Test criterion: "Would they think 'I was just about to type that'?"
- Format: 2-12 words matching user's style, or nothing
- Never suggest: evaluative phrases, questions, Claude-voice, new ideas, multiple sentences

### Filter Pipeline (`shouldFilterSuggestion`)
A 13-rule filter chain eliminates bad suggestions:

| Filter | Rule |
|--------|------|
| `done` | Exact match "done" |
| `meta_text` | "nothing found", "no suggestion", "stay silent", bare "silence" |
| `meta_wrapped` | Wrapped in `(...)` or `[...]` |
| `error_message` | API error strings, prompt too long, timeout |
| `prefixed_label` | Matches `word: ...` pattern |
| `too_few_words` | Single word unless in allowlist (yes/no/push/commit/continue/etc.) or slash command |
| `too_many_words` | > 12 words |
| `too_long` | >= 100 characters |
| `multiple_sentences` | Contains `.!?` followed by uppercase |
| `has_formatting` | Contains newlines, asterisks, bold markers |
| `evaluative` | "thanks", "looks good", "perfect", "awesome", etc. |
| `claude_voice` | Starts with "Let me", "I'll", "Here's", "You should", etc. |

### Speculation Engine (`speculation.ts`)

#### Purpose
When a suggestion is generated, speculation pre-executes it as if the user accepted — so when they do accept, results appear instantly.

#### Execution Model
- **Forked agent**: `runForkedAgent()` with `forkLabel: 'speculation'`
- **Overlay filesystem**: Copy-on-write isolation — writes go to `<claudeTempDir>/speculation/<pid>/<id>/`
- **Limits**: MAX_SPECULATION_TURNS=20, MAX_SPECULATION_MESSAGES=100
- **Tool permissions**:
  - **Write tools** (Edit, Write, NotebookEdit): Only allowed if user's permission mode is `acceptEdits`, `bypassPermissions`, or plan+bypass available. File paths rewritten to overlay
  - **Read tools** (Read, Glob, Grep, ToolSearch, LSP, TaskGet, TaskList): Allowed; redirected to overlay for previously-written files
  - **Bash**: Read-only commands only (validated via `checkReadOnlyConstraints`)
  - **All other tools**: Denied (creates a completion boundary)

#### Completion Boundaries
Speculation stops and records a boundary when it hits:
- **`bash`**: Non-read-only bash command
- **`edit`**: File edit when permissions don't allow auto-accept
- **`denied_tool`**: Unknown/unsupported tool
- **`complete`**: Agent finished naturally within limits

#### Accept Flow
1. Abort running speculation
2. Copy overlay files to main working directory
3. Clean overlay directory
4. Inject speculated messages into conversation (strip thinking blocks, incomplete tool calls, interrupts)
5. Track `timeSavedMs` in session state and transcript
6. If speculation completed fully, promote pipelined suggestion (next suggestion already generating)

#### Pipelined Suggestions
When speculation completes, it immediately generates the NEXT suggestion based on the augmented conversation (original + speculated messages). If the user accepts the first suggestion, the second suggestion is already ready — creating a chain of speculative execution.

### Data Flow
```
stopHooks
  → executePromptSuggestion()
    → tryGenerateSuggestion() [suppression checks → generateSuggestion() → filter]
    → setAppState({promptSuggestion: {text, promptId}})
    → if speculation enabled:
        → startSpeculation(suggestion, context)
          → overlay mkdir
          → runForkedAgent({canUseTool: overlay-aware permission check})
          → on boundary/completion: update state
          → generatePipelinedSuggestion() for next suggestion

User accepts suggestion:
  → handleSpeculationAccept()
    → acceptSpeculation() — copy overlay, inject messages
    → promote pipelinedSuggestion if complete
    → start new speculation on pipelined suggestion
```

### Analytics Events
- `tengu_prompt_suggestion_init` — tracks enabled/disabled state and source
- `tengu_prompt_suggestion` — outcome (accepted/ignored/suppressed), similarity, time-to-accept
- `tengu_speculation` — speculation_id, outcome, duration, tools_executed, boundary details, time_saved

---

## 3. tips — Contextual Tip Display System

### Files
| File | LOC | Purpose |
|------|-----|---------|
| `tipHistory.ts` | 18 | Persistence layer — records tip shown events keyed by `numStartups` |
| `tipRegistry.ts` | 687 | 40+ tip definitions with relevance predicates and cooldown periods |
| `tipScheduler.ts` | 59 | Selection algorithm — picks the tip least-recently shown |

### Purpose
Displays contextual tips in the spinner/loading UI. Tips are context-aware, respecting cooldown periods, user experience level, platform, and installed features.

### Trigger Conditions
- Triggered when spinner is displayed (during model inference)
- `spinnerTipsEnabled` setting must not be `false`
- Each tip has its own `isRelevant()` async predicate
- Each tip has a `cooldownSessions` — minimum sessions since last shown

### Execution Model
- **Foreground/Synchronous**: Tip selection is synchronous within the spinner display flow
- **Persistence**: `tipHistory` stores `{tipId: numStartups}` in global config
- **Selection algorithm**: Among all relevant tips that have passed cooldown, select the one with the longest time since last shown (`selectTipWithLongestTimeSinceShown`)

### Tip Categories (40+ tips)

| Category | Examples | Relevance Logic |
|----------|----------|-----------------|
| **New user onboarding** | "Start with small features" | `numStartups < 10` |
| **Feature discovery** | Plan mode, /memory, /theme, /permissions, /agents | Various experience thresholds |
| **Terminal setup** | Shift+Enter, Option+Enter | Based on OS and installation state |
| **Multi-session** | Git worktrees, /color, /rename | Concurrent session count, worktree count |
| **IDE integration** | VS Code command install, /ide | Terminal type, IDE detection |
| **Platform-specific** | PowerShell tool (Windows), paste images (macOS) | `getPlatform()` checks |
| **Plugin recommendations** | frontend-design, vercel | Marketplace installed + file pattern/CLI detection |
| **Feature nudges** | /effort high, subagent fanout, /loop | GrowthBook A/B test variants (`tengu_tide_elm`, etc.) |
| **Commercial** | Guest passes, overage credits, desktop/web/mobile apps | Eligibility checks, cached API data |
| **Internal-only** | CLAUDE.md IMPORTANT prefix, /skillify | `USER_TYPE === 'ant'` |
| **Custom tips** | User-defined via `spinnerTipsOverride` setting | Always relevant; can exclude defaults |

### Key Functions
- `getRelevantTips(context?)` — Parallel evaluation of all `isRelevant()` predicates, then cooldown filter
- `getTipToShowOnSpinner(context?)` — Full pipeline: settings check → relevance → selection
- `recordShownTip(tip)` — Persists to global config + logs `tengu_tip_shown` event

### Data Flow
```
Spinner display
  → getTipToShowOnSpinner(context)
    → getRelevantTips(context)
      → Promise.all(tips.map(isRelevant))
      → filter by cooldownSessions vs getSessionsSinceLastShown
    → selectTipWithLongestTimeSinceShown(filtered)
  → render tip text
  → recordShownTip(tip)
    → recordTipShown(tipId) → saveGlobalConfig
    → logEvent('tengu_tip_shown')
```

### Integration Points
- `globalConfig` — `numStartups`, `tipsHistory`, feature usage counters
- GrowthBook — A/B test variants for feature nudge copy
- IDE detection — `detectRunningIDEsCached`, `isSupportedTerminal`
- Plugin system — `isPluginInstalled`, marketplace config
- API services — referral passes, overage credits (cached)

---

## 4. toolUseSummary — Tool Batch Summarization

### Files
| File | LOC | Purpose |
|------|-----|---------|
| `toolUseSummaryGenerator.ts` | 113 | Generates human-readable labels for completed tool batches via Haiku |

### Purpose
Produces short, git-commit-style labels describing what a batch of tool calls accomplished. Designed for the SDK mobile app interface where space is limited (~30 character truncation).

### Trigger Conditions
- Called by the SDK when a batch of tool uses completes
- Requires at least 1 tool in the batch
- Non-critical — failures return `null` silently

### Execution Model
- **Foreground/Async**: Direct API call to Haiku model (not a forked agent)
- **Model**: `queryHaiku()` — lightweight, fast, cheap model
- **Prompt caching**: Enabled (`enablePromptCaching: true`)
- **Non-blocking**: Errors logged but never propagated — summaries are non-critical

### System Prompt Design
- Format: Single-line label, past tense verb + distinctive noun
- Target: ~30 characters (mobile app truncation point)
- Examples: "Searched in auth/", "Fixed NPE in UserService", "Created signup endpoint"
- Input truncation: JSON values truncated to 300 chars each

### Key Functions
- `generateToolUseSummary({tools, signal, isNonInteractiveSession, lastAssistantText})` — Main entry point
- `truncateJson(value, maxLength)` — Safe JSON serialization with length limit

### Data Flow
```
SDK tool batch completion
  → generateToolUseSummary({tools, signal, ...})
    → Build concise tool summaries (name + truncated input/output)
    → queryHaiku({systemPrompt, userPrompt: context + tools + "Label:"})
    → Extract text from response
    → Return summary string (or null on failure)
```

### Integration Points
- `queryHaiku` — Claude Haiku model API
- SDK push path — provides progress updates to mobile/desktop clients
- Error tracking — `E_TOOL_USE_SUMMARY_GENERATION_FAILED` constant

---

## 5. AgentSummary — Sub-Agent Progress Summarization

### Files
| File | LOC | Purpose |
|------|-----|---------|
| `agentSummary.ts` | 180 | Periodic forked-agent summarization for coordinator mode sub-agents |

### Purpose
Generates 3-5 word present-tense progress summaries for running sub-agents every ~30 seconds. Displayed in the UI so users can see what each sub-agent is currently doing.

### Trigger Conditions
- Started when a sub-agent is launched in coordinator mode
- Requires at least 3 messages in the sub-agent's transcript
- Runs on a 30-second interval timer

### Execution Model
- **Background/Periodic**: `setInterval`-style timer (30s), non-overlapping (schedules next after completion)
- **Forked agent**: `runForkedAgent()` with `forkLabel: 'agent_summary'`
- **Cache sharing**: Uses same `CacheSafeParams` as parent agent (minus `forkContextMessages` which are rebuilt each tick)
- **Tool denial**: All tools denied via callback (not `tools:[]`) to preserve cache key — same pattern as PromptSuggestion
- **Transcript reading**: Reads current agent transcript via `getAgentTranscript(agentId)` each tick
- **Abortable**: Per-summary `AbortController`, plus global stop function

### Summary Prompt Design
- Format: 3-5 words, present tense (-ing verbs)
- Must name the file or function, not the branch
- Previous summary included to force novelty ("say something NEW")
- Good: "Reading runAgent.ts", "Fixing null check in validate.ts"
- Bad: "Analyzed the branch diff" (past tense), "Investigating the issue" (too vague)

### Key Functions
- `startAgentSummarization(taskId, agentId, cacheSafeParams, setAppState)` — Returns `{stop: () => void}`
- `buildSummaryPrompt(previousSummary)` — Constructs the prompt with novelty constraint

### Data Flow
```
Sub-agent launch (coordinator mode)
  → startAgentSummarization(taskId, agentId, cacheSafeParams, setAppState)
    → scheduleNext() [30s timer]
    → runSummary()
      → getAgentTranscript(agentId) → filterIncompleteToolCalls
      → runForkedAgent({forkContextMessages: cleanMessages, canUseTool: deny-all})
      → Extract text from first assistant message
      → updateAgentSummary(taskId, summaryText, setAppState)
      → scheduleNext() [in finally block — prevents overlap]

Sub-agent completion
  → stop() → clearTimeout + abort
```

### Integration Points
- `LocalAgentTask` — `updateAgentSummary` writes to task state for UI display
- `AgentTool/runAgent` — `filterIncompleteToolCalls` cleans messages
- `forkedAgent` — shared fork infrastructure
- `sessionStorage` — `getAgentTranscript` reads sub-agent transcript from disk

---

## Cross-Service Patterns

### Shared Infrastructure

| Pattern | Services Using It | Mechanism |
|---------|------------------|-----------|
| **Forked Agent** (`runForkedAgent`) | autoDream, PromptSuggestion, Speculation, AgentSummary | Core background execution primitive |
| **Cache-safe fork** (`createCacheSafeParams`) | All forked services | Ensures prompt cache sharing with parent |
| **Tool denial via callback** | PromptSuggestion, Speculation, AgentSummary | `canUseTool: deny` preserves cache key (vs `tools:[]` which busts it) |
| **GrowthBook feature flags** | autoDream, PromptSuggestion, tips | `getFeatureValue_CACHED_MAY_BE_STALE` for remote config |
| **Analytics events** | All 5 services | `logEvent('tengu_*')` for telemetry |
| **AbortController** | autoDream, PromptSuggestion, Speculation, AgentSummary | Graceful cancellation |
| **skipTranscript** | autoDream, PromptSuggestion, AgentSummary | Prevent background work from polluting session history |

### Execution Model Comparison

| Service | Model | Trigger | Frequency | Cost Profile |
|---------|-------|---------|-----------|--------------|
| **autoDream** | Background forked agent | Post-sampling hook | ~1/day (24h + 5 sessions) | High per-run (full consolidation), cheap per-turn (stat) |
| **PromptSuggestion** | Background forked agent | Post-sampling hook | Every turn (when enabled) | Low (cache hit, short response) |
| **Speculation** | Background forked agent | After suggestion generated | Every suggestion | Medium-High (runs actual tools in overlay) |
| **tips** | Foreground sync | Spinner display | Every spinner | Negligible (local predicates) |
| **toolUseSummary** | Foreground Haiku call | SDK tool batch completion | Per tool batch | Low (Haiku, short response) |
| **AgentSummary** | Background forked agent | 30s timer per sub-agent | Every 30s per agent | Low (cache hit, short response) |

### Cache Strategy
The most critical cross-cutting concern is **prompt cache preservation**. Three services (PromptSuggestion, Speculation, AgentSummary) explicitly document that setting ANY API parameter differently from the parent request (effort, maxOutputTokens, tools array) invalidates the prompt cache. The solution is consistent:
1. Pass identical `CacheSafeParams` from the parent
2. Deny tools via callback, not by removing them from the request
3. Do not set `skipCacheWrite` except on PromptSuggestion (its results are ephemeral)
4. PR #18143 is cited as the cautionary tale (effort:'low' caused 92.7% → 61% cache hit rate)

### Feature Flag Naming Convention
All GrowthBook flags follow the `tengu_*` namespace:
- `tengu_onyx_plover` — autoDream enabled + scheduling config
- `tengu_chomp_inflection` — PromptSuggestion enabled
- `tengu_tide_elm` — effort high nudge tip (A/B)
- `tengu_tern_alloy` — subagent fanout nudge tip (A/B)
- `tengu_timber_lark` — /loop command nudge tip (A/B)

---

## Architecture Significance

These 5 services collectively form Claude Code's **background intelligence layer** — the system that makes the tool feel proactive rather than reactive:

1. **autoDream** ensures memory quality degrades gracefully over time through automatic consolidation
2. **PromptSuggestion + Speculation** create the illusion of instantaneous execution by predicting and pre-computing the user's next action
3. **tips** provides progressive disclosure of features calibrated to user experience level
4. **toolUseSummary** keeps SDK/mobile clients informed with minimal latency
5. **AgentSummary** provides real-time visibility into concurrent sub-agent activity

The `runForkedAgent` + `CacheSafeParams` pattern is the foundational primitive that makes all background LLM work economically viable by sharing the parent conversation's prompt cache.
