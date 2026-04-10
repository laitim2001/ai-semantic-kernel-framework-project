# Claude Code CLI — System Overview

> **Wave 57 Updated** — Integrated discoveries from Waves 41-55 (API service subsystems, speculation COW overlay, pure-TS bash parser, 54KB system prompt, coordinator mode, Direct Connect).
> Previous: Wave 21-22 Corrected. All numbers, function names, and architectural claims cross-checked against source-verified ground truth.
> Original: 2026-04-01 | Wave 57 Update: 2026-04-01 | Verifier: Claude Opus 4.6 (1M context)

---

## 1. What is Claude Code?

Claude Code is Anthropic's official CLI tool for AI-assisted software development.
It is a TypeScript application that runs in the terminal, uses **Ink** (React for terminal)
for its interactive UI, and communicates with Claude AI models via the Anthropic API.

Key characteristics:
- Interactive REPL (Read-Eval-Print Loop) for conversational coding assistance
- Tool-based architecture: Claude decides which tools to invoke (file edit, bash, web search, etc.)
- Plugin system for extending capabilities via MCP (Model Context Protocol) servers
- Multi-agent support: Claude can spawn sub-agents (AgentTool) for parallel work
- Coordinator mode: Multi-agent orchestration brain for managing concurrent sub-agents (Wave 44)
- Speculation system: Predicts user's next prompt and pre-executes it in a COW overlay (Wave 44)
- Remote session support for cloud/IDE environments
- Direct Connect: Local WebSocket server protocol for IDE/bridge integration (Wave 44)

---

## 2. Entry Point Flow

Two distinct execution paths exist: the **interactive REPL** path and the **SDK/headless** path.

```
User runs: claude [args]
          |
          v
src/entrypoints/cli.tsx       <- Bootstrap; sets env vars, fast-paths for --version
          |
          | dynamic import
          v
src/main.tsx                  <- Full CLI; Commander.js setup, all command registration
          |
          |--[slash command]-> src/commands/<name>/index.ts  (e.g., /login, /mcp)
          |
          |--[REPL mode]----> src/replLauncher.ts
          |                         |
          |                         v
          |                  src/screens/REPL.tsx          <- Main interactive screen
          |                         |
          |                  handlePromptSubmit.ts         <- Orchestration layer
          |                         |                        (exit commands, queuing,
          |                         |                         reference expansion,
          |                         |                         queryGuard management)
          |                         |
          |                  executeUserInput -> processUserInput -> onQuery -> onQueryImpl
          |                         |
          |                  src/query.ts                  <- Single-turn API call + tool execution
          |                         |
          |                  @anthropic-ai/sdk             <- Streaming API call to Claude
          |                         |
          |                  StreamingToolExecutor          <- Parallel tool execution
          |                         |                        (concurrent-safe tools run in parallel)
          |                         |
          |                  src/tools/<ToolName>/Tool.ts  <- Tool implementation
          |
          |--[SDK mode]-----> src/QueryEngine.ts           <- SDK/headless multi-turn loop
                                    |                        (NOT used in interactive REPL)
                              src/query.ts                 <- Same single-turn engine
```

> **Critical note**: `QueryEngine.ts` is the **SDK/headless** path only. The interactive REPL path uses `handlePromptSubmit.ts` as its orchestration layer, routing through `executeUserInput -> processUserInput -> onQuery -> onQueryImpl -> query()`. See Wave 4 correction for full 7-layer flow.

### cli.tsx Fast-Paths

`src/entrypoints/cli.tsx` implements zero-import fast-paths:
- `--version` / `-v`: Outputs `MACRO.VERSION` without loading any modules (~0ms startup)
- `--dump-system-prompt`: Dumps rendered system prompt (ant-only feature flag)
- `CLAUDE_CODE_REMOTE=true`: Sets `--max-old-space-size=8192` for container environments
- `ABLATION_BASELINE`: Applies ablation study env vars for harness-science experiments

### init.ts Initialization

`src/entrypoints/init.ts` runs once (memoized) before the REPL starts:
1. Profile checkpoint logging
2. Graceful shutdown handler registration
3. Config file loading (`enableConfigs()`)
4. SSL/TLS certificate configuration (CA certs, mTLS)
5. Windows shell detection (`setShellIfWindows()`)
6. MDM (Mobile Device Management) settings loading
7. Proxy configuration (`configureGlobalAgents()`)
8. JetBrains IDE detection
9. OAuth account info prefetch
10. Policy limits initialization (enterprise)
11. Remote managed settings initialization (MDM)
12. API pre-connection (DNS warmup)
13. Telemetry initialization (lazy-loaded to defer 400KB OpenTelemetry modules)

### main.tsx Startup Sequence

`src/main.tsx` shows a highly optimized startup:
1. **Side-effect imports at top**: `profileCheckpoint`, `startMdmRawRead`, `startKeychainPrefetch` — all fired in parallel before other imports
2. **Lazy requires**: Circular dependencies broken via `require()` at call time
3. **Feature-gated modules**: `coordinatorMode`, `assistantModule` (KAIROS) only loaded when feature flags are set
4. **Model migrations**: 8 migration scripts run at startup to normalize stored model settings

---

## 3. Major Subsystems

### 3.1 Query Engine (`src/query.ts`, `src/QueryEngine.ts`)

The query engine is the heart of Claude Code. It manages the conversation loop:

**`query.ts`** (single-turn, used by both REPL and SDK paths):
- Receives the system prompt as a parameter (does NOT build it)
- Calls the Anthropic API with streaming via `deps.callModel()` (dependency injection pattern)
- The actual API call is `anthropic.beta.messages.create({...params, stream: true}).withResponse()` in `claude.ts`
- Processes the response stream, accumulating text and tool_use blocks
- For each `tool_use` block: looks up the tool, checks permissions, executes it
- Returns the complete assistant message + tool results
- Handles auto-compaction when context window approaches limits

**`QueryEngine.ts`** (multi-turn, **SDK/headless path only**):
- Manages the full conversation history for programmatic SDK consumers
- Calls `query.ts` in a loop until the model stops invoking tools
- Handles session persistence (transcript recording)
- Manages token budget and compaction triggers
- Emits stream events for consumers
- **NOT used in the interactive REPL path** — the REPL uses `handlePromptSubmit.ts` orchestration

### 3.2 handlePromptSubmit — REPL Orchestration Layer

`src/handlePromptSubmit.ts` is the critical orchestration layer between user input and the query engine in the interactive REPL path:

- Handles exit commands (exit/quit/:q/:wq) by redirecting to `/exit`
- Expands `[Pasted text #N]` references via `expandPastedTextRefs()`
- Manages command queuing when the engine is busy (`enqueue()`)
- Routes by mode: bash commands, slash commands, ultraplan keywords, text prompts
- Creates and manages `AbortController` for cancellation
- Reserves `queryGuard` to prevent concurrent execution
- Wraps execution in `runWithWorkload()` AsyncLocalStorage context

### 3.3 Tool System (`src/Tool.ts`, `src/tools.ts`)

The tool system defines how Claude interacts with the environment. **57+ tools** are available across built-in and feature-gated categories.

**`src/Tool.ts`**: Defines the `Tool` interface:
- `name`: Unique identifier sent to the API
- `description`: Natural language description for Claude
- `inputSchema`: Zod schema for input validation (JSON Schema generated from Zod for the API)
- `call()`: Async execution function returning tool result
- `checkPermissions()`: Tool-specific permission logic returning `PermissionResult`
- `validateInput()`: Tool-specific input validation
- `isConcurrencySafe()`: Whether tool can run in parallel with others
- `renderProgressInCompact()`: Optional terminal rendering
- `isEnabled()`: Feature-flag gated enablement

**`src/tools.ts`**: Tool registry:
- Imports all tool classes
- Applies feature flags to conditionally include tools
- Exports `getTools()` which returns the active tool set for a session
- Handles deduplication (MCP tools can shadow built-in tools)

**`StreamingToolExecutor`**: Enables parallel tool execution:
- Concurrent-safe tools (Read, Grep, Glob) run in parallel with each other
- Non-concurrent tools get exclusive access
- Results yielded in arrival order

### 3.4 API Service Layer (`src/services/api/`) — Wave 41 Deep Analysis

The API service layer (21 files, ~360KB) contains **10 previously undocumented subsystems** beyond the core query flow:

#### 3.4.1 Core API Orchestrator (`claude.ts`, 125KB)

The `queryModel()` generator pipeline: off-switch check, model resolution, beta header merge, tool schema building, message normalization, tool_use/tool_result repair, prompt cache breakpoint placement, thinking/effort/speed configuration, streaming with raw `Stream<BetaRawMessageStreamEvent>` (avoids O(n^2) partial JSON parsing), and non-streaming fallback.

#### 3.4.2 Stream Watchdog

Configurable idle timeout (`CLAUDE_STREAM_IDLE_TIMEOUT_MS`, default **90 seconds**). Fires warning at 50% threshold (45s). On timeout, releases stream resources and falls through to non-streaming fallback. Prevents socket/TLS memory leaks (GH #32920).

#### 3.4.3 Anti-Distillation System

`fake_tools` opt-in for first-party CLI (feature-gated). Injects decoy tool schemas to prevent model distillation from API traffic patterns.

#### 3.4.4 Beta Header Latching

Sticky-on pattern: once a beta header is first sent, it stays for the entire session. Prevents 50-70K token prompt cache busts from mid-session toggles. Latched headers: AFK mode, fast mode, cached microcompact, context management. Non-latched: model betas, effort, structured outputs, task budgets, advisor, tool search.

#### 3.4.5 Prompt Cache Break Detection (`promptCacheBreakDetection.ts`, 26KB)

Entire subsystem for diagnosing cache invalidation. Tracks per-source state (system prompt hash, tool schemas hash, model, beta headers, effort, etc.). After each API response, compares `cache_read_input_tokens`; if drop >2,000, identifies the cause via pending change diffs. Memory bounded to 10 tracked sources.

#### 3.4.6 Tool Search & Deferred Tools

Complex filtering/discovery system for dynamic tool loading. Tools can be deferred (schema loaded on demand) or discovered at runtime. Integrates with tool search beta headers.

#### 3.4.7 Advisor Tool

Server-side tool with model selection, beta header (`advisor-tool-2026-03-01`), and interruption tracking. Provides Claude with access to a secondary model for consultation.

#### 3.4.8 Cached Microcompact (Function Result Clearing)

`cache_edits` deletions, pinned edits, `cache_editing` beta header. Enables server-side compaction of tool results while preserving cache stability.

#### 3.4.9 Persistent Retry Mode

`CLAUDE_CODE_UNATTENDED_RETRY` enables infinite retry with 5-minute max backoff, 30-second heartbeat yields, and 6-hour reset cap. Designed for unattended CI/batch sessions where dropping a request is worse than waiting.

#### 3.4.10 Supporting API Clients (10 clients)

| Client | Purpose |
|--------|---------|
| `bootstrap.ts` | Fetch `client_data` + `additional_model_options` at startup |
| `filesApi.ts` | File upload/download via Anthropic Files API (500MB max, 3 retries) |
| `sessionIngress.ts` | Remote session log persistence (append-only JSONL, optimistic concurrency) |
| `grove.ts` | Privacy settings for conversation data training (24h cache) |
| `referral.ts` | Guest pass eligibility/redemption (Max subscribers, 24h cache) |
| `overageCreditGrant.ts` | Overage credit eligibility (1h cache, fire-and-forget refresh) |
| `metricsOptOut.ts` | Org-level metrics toggle (1h memory + 24h disk, fail-safe: disabled) |
| `ultrareviewQuota.ts` | Ultrareview usage tracking |
| `usage.ts` | Utilization API (five_hour/seven_day rate limits) |
| `firstTokenDate.ts` | First Claude Code usage date (cached to global config) |

### 3.5 Speculation System — COW Overlay Filesystem (Wave 44)

The speculation system pre-executes predicted user prompts in a **copy-on-write isolated overlay**:

- **Trigger**: After `PromptSuggestion` generates a predicted next prompt
- **Overlay path**: `<claudeTempDir>/speculation/<pid>/<id>/`
- **Write tools** (Edit, Write, NotebookEdit): File paths rewritten to overlay; only allowed if user's permission mode permits auto-accept
- **Read tools** (Read, Glob, Grep, etc.): Redirected to overlay for previously-written files, otherwise read from real filesystem
- **Bash**: Read-only commands only (validated via `checkReadOnlyConstraints`)
- **Completion boundaries**: Non-read-only bash, file edit without permissions, denied tool, or natural completion
- **Accept flow**: Abort speculation, copy overlay to working directory, inject speculated messages into conversation, track `timeSavedMs`
- **Pipelined suggestions**: When speculation completes, immediately generates the NEXT suggestion, creating chains of speculative execution
- **Limits**: MAX_SPECULATION_TURNS=20, MAX_SPECULATION_MESSAGES=100

### 3.6 Background Intelligence Services (Wave 44)

Five services form the **background intelligence layer** that makes Claude Code proactive:

| Service | Model | Trigger | Purpose |
|---------|-------|---------|---------|
| **autoDream** | Forked agent | Post-sampling, ~1/day | Automatic memory consolidation (4-phase `/dream` pass) |
| **PromptSuggestion** | Forked agent | Post-sampling, every turn | Predicts user's next prompt (13-rule filter chain) |
| **Speculation** | Forked agent | After suggestion generated | Pre-executes predicted prompt in COW overlay |
| **tips** | Foreground sync | Spinner display | 40+ contextual tips calibrated to user experience |
| **toolUseSummary** | Haiku API call | SDK tool batch completion | Git-commit-style labels for mobile/SDK interface |
| **AgentSummary** | Forked agent, 30s interval | Sub-agent running | 3-5 word progress summaries for coordinator mode UI |

All forked services share the `runForkedAgent()` + `CacheSafeParams` primitive to share the parent conversation's prompt cache. Tools are denied via callback (not `tools:[]`) to preserve cache keys.

### 3.7 Coordinator Mode — Multi-Agent Orchestration (Wave 44)

Coordinator mode enables a lead agent to orchestrate multiple concurrent sub-agents:

- **Tool set**: `COORDINATOR_MODE_ALLOWED_TOOLS` = Agent, TaskStop, SendMessage, SyntheticOutput
- **AgentSummary**: Generates 3-5 word present-tense progress summaries every 30 seconds per sub-agent, displayed in UI
- **Visibility**: Users see real-time sub-agent activity via `LocalAgentTask` state
- **Feature-gated**: `coordinatorMode` module only loaded when flag is set

### 3.8 Screen / UI System (`src/screens/`, `src/components/`)

Built with **Ink v5** (React renderer for terminal):

**`src/screens/REPL.tsx`**: Main interactive screen component:
- Renders the conversation history
- Shows the text input area (user input via `onSubmit` callback, NOT `useTextInput`)
- Displays tool execution progress
- Handles keyboard shortcuts
- Shows status bar (model, cost, context usage)
- Builds the system prompt via `buildEffectiveSystemPrompt()` in `onQueryImpl`

**`src/components/`**: 389 files of React/Ink components:
- `design-system/`: Base UI components (Dialog, Pane, ProgressBar, Tabs)
- `agents/`: Agent management UI
- `diff/`: Diff visualization
- `permissions/`: Permission request dialogs and rule management UI

### 3.9 Command System (`src/commands/`, `src/commands.ts`)

Slash commands (`/login`, `/mcp`, `/compact`, etc.) — **88+ commands** registered:
- Registered in `src/commands.ts` via `getCommands()`
- Each command exports an index.ts with Commander.js registration
- Some are interactive (render React components)
- Some are non-interactive (pure TypeScript logic)
- Remote mode filtering: `filterCommandsForRemoteMode()` removes commands unavailable in remote sessions

### 3.10 Bootstrap State (`src/bootstrap/state.ts`)

Global singleton state with strict isolation rules:
- Session ID, original CWD, project root
- Cost tracking (totalCostUSD, modelUsage)
- Model settings (mainLoopModelOverride, initialMainLoopModel)
- Flags: isInteractive, kairosActive, strictToolResultPairing
- OpenTelemetry meter/provider references
- Registered hook matchers (SDK callbacks + plugin hooks)
- Comment: "DO NOT ADD MORE STATE HERE — BE JUDICIOUS WITH GLOBAL STATE"

### 3.11 MCP Integration (`src/services/mcp/`)

Model Context Protocol enables extensibility via **10 transport types**:
- `client.ts`: MCP server connection management, tool/resource discovery
- `config.ts`: Parses MCP server configurations from settings files
- `auth.ts`: OAuth authentication for MCP servers
- `InProcessTransport.ts`: In-process MCP transport (no subprocess needed)
- `SdkControlTransport.ts`: SDK-controlled MCP transport
- Additional transports: stdio, SSE, WebSocket, Hybrid, CCR, StreamableHTTP, and more

MCP tools appear alongside built-in tools in the `getTools()` result.

### 3.12 Permission System (`src/utils/permissions/`)

Multi-layer permission architecture with **7 modes** and **8 rule sources**:

**Permission Modes**:

| Mode | Scope | Behavior |
|------|-------|----------|
| `default` | External | Standard prompt-for-everything (interactive) |
| `acceptEdits` | External | Auto-allow file edits within working directory |
| `plan` | External | Read-only; blocks tool execution |
| `bypassPermissions` | External | Allow everything except bypass-immune safety checks |
| `dontAsk` | External | Convert all `ask` decisions to `deny` (never prompt) |
| `auto` | Internal | AI classifier decides instead of prompting user |
| `bubble` | Internal | Bubble up to parent (for subagents) |

> **Note**: There is no "manual" mode. The default interactive mode is called `default`. Previous analysis incorrectly listed only 4 modes.

**Rule Sources** (loaded from `permissionsLoader.ts`):
1. `policySettings` — Managed/enterprise (highest priority when `allowManagedPermissionRulesOnly` is set)
2. `flagSettings` — Runtime flags
3. `userSettings` — `~/.claude/settings.json`
4. `projectSettings` — `.claude/settings.json`
5. `localSettings` — `.claude/settings.local.json`
6. `cliArg` — CLI `--permission-mode`
7. `command` — Slash command frontmatter
8. `session` — In-memory only (transient)

**Key components**:
- `permissionsLoader.ts`: Loads rules from all 8 sources (not just CLI flags)
- `permissionRuleParser.ts`: Parses allow/deny/ask rules from settings
- `denialTracking.ts`: Tracks denied tool calls with limits (maxConsecutive: 3, maxTotal: 20)
- `bashSecurity.ts`: ~23 distinct security check IDs for shell command validation
- `interactiveHandler.ts`: 5-way concurrent permission resolver (user + hooks + classifier + bridge + channel)
- Per-session overrides, per-tool allow/deny rules

### 3.13 Pure-TypeScript Bash Parser (`src/utils/bash/bashParser.ts`) — Wave 48

A **pure-TS recursive-descent parser** (~2,500 LOC) that replaced the WASM-based tree-sitter parser to eliminate native module dependencies:

- **Output**: Tree-sitter-bash-compatible AST nodes
- **Golden corpus**: 3,449 test cases for validation against tree-sitter output
- **Safety limits**: 50ms parse timeout + 50,000 node budget (prevents DoS from malformed input)
- **Integration**: Used by the 4-layer security model in `ast.ts` for fail-closed allowlist walking

The broader bash execution infrastructure (35 files: 22 bash/ + 10 shell/ + 3 powershell/) implements **defense-in-depth**:
1. **Pre-parse**: Control char, Unicode whitespace, brace+quote obfuscation rejection
2. **AST walk**: Fail-closed allowlist, variable scope tracking with isolation
3. **Permission matching**: Fig-spec prefix extraction + LLM-powered fallback (Haiku)
4. **Read-only validation**: Per-subcommand flag allowlists, UNC credential leak prevention

### 3.14 System Prompt Architecture (`src/constants/prompts.ts`, 54KB) — Wave 55

The **single most important file** in Claude Code. Constructs the entire system prompt (~915 lines) with a **static/dynamic cache boundary**:

```
[Static cacheable content]     <- scope: 'global' prefix (Blake2b hashed)
SYSTEM_PROMPT_DYNAMIC_BOUNDARY <- '__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__'
[Dynamic per-session content]  <- recomputed each turn
```

**Static sections** (cacheable across orgs):
1. Intro (identity + `CYBER_RISK_INSTRUCTION` security boundary)
2. System (markdown rendering, permission awareness, hooks)
3. Doing Tasks (code style rules, no gold-plating, no TODO comments, OWASP top 10)
4. Actions (reversibility/blast-radius framework, risky action examples)
5. Using Your Tools (dedicated tool preference matrix: Read > cat, Edit > sed, etc.)
6. Tone and Style (no emojis, file_path:line_number references)
7. Output Efficiency (ant: inverted pyramid ~400 words; external: concise)

**Dynamic sections** (per-session, registry-managed via `systemPromptSection()` / `DANGEROUS_uncachedSystemPromptSection()`):
- `session_guidance`, `memory` (CLAUDE.md files), `env_info_simple` (CWD, git, platform, model, knowledge cutoff), `mcp_instructions` (UNCACHED -- MCP servers connect/disconnect between turns), `token_budget`, `brief`, and 7 more sections

**Three identity variants**: Interactive CLI, SDK with appendSystemPrompt, pure SDK agent.

**Proactive/autonomous mode** (`isProactiveActive()`): Completely different prompt with `<tick>` tag handling, Sleep tool, terminal focus awareness.

**Caching infrastructure** (`systemPromptSections.ts`): Sections computed once and cached until `/clear` or `/compact`. Dangerous uncached sections require explicit reason and break prompt cache. All sections resolved in parallel via `Promise.all()`.

### 3.15 Memory System (`src/memdir/`)

Persistent memory via CLAUDE.md files:
- `memdir.ts`: Loads memory from `~/.claude/CLAUDE.md` and project `.claude/CLAUDE.md`
- `findRelevantMemories.ts`: Semantic search for relevant memory sections
- `extractMemories.ts` (service): AI-powered extraction of learnings to memory
- `autoDream.ts` (service): Background memory consolidation during idle time (Wave 44: 4-phase consolidation with file-based distributed lock, 24h + 5 session gate)

### 3.16 Bridge System (`src/bridge/`)

Enables remote/IDE connections to the REPL:
- `replBridge.ts`: Core bridge implementation
- `bridgeMessaging.ts`: Message protocol
- `remoteBridgeCore.ts`: Remote connection handling
- `sessionRunner.ts`: Session lifecycle in bridge mode
- Used by Claude.ai web, IDE extensions, mobile apps

### 3.17 Direct Connect Protocol (Wave 44)

Local WebSocket server protocol enabling IDE extensions and bridge clients to connect directly to a running Claude Code session. Part of the bridge system infrastructure for real-time bidirectional communication without requiring remote session infrastructure.

---

## 4. Key Architectural Decisions

### 4.1 Ink + React for Terminal UI

Instead of imperative terminal output, Claude Code uses React components rendered by Ink.
This enables:
- Declarative UI updates (state changes automatically re-render)
- Reusable component library
- Complex interactive UI (dialogs, progress bars, multi-column layouts)
- Easy testing of UI components

### 4.2 Tool-per-Directory Pattern

Each tool lives in its own directory with a consistent structure:
```
tools/BashTool/
  BashTool.tsx        <- Main tool implementation
  UI.tsx              <- Terminal rendering component
  prompt.ts           <- System prompt contribution
  bashSecurity.ts     <- Security validation
  bashPermissions.ts  <- Permission checks
  ...
```

This enforces separation of concerns and makes tools independently testable.

### 4.3 Feature Flag Dead-Code Elimination

`bun:bundle`'s `feature('FLAG_NAME')` function enables build-time DCE:
- Ant-only tools (REPLTool, etc.) are completely absent from external builds
- KAIROS assistant mode code is eliminated when not enabled
- Coordinator mode only loaded when feature flag set
- `process.env.USER_TYPE === 'ant'` must be inlined at each callsite (not hoisted to const) for DCE to work
- This keeps the external binary lean

### 4.4 Bootstrap Isolation

`src/bootstrap/state.ts` is intentionally restricted:
- Minimal imports (no circular dependencies)
- Global mutable state (but explicitly flagged as such)
- All session state flows through this singleton
- Guards against state leaks between sessions

### 4.5 Lazy Require for Circular Dependencies

Several modules use `require()` at call time instead of ES import at module load:
```typescript
const getTeammateUtils = () => require('./utils/teammate.js')
```
This breaks circular import cycles while preserving TypeScript type safety.

### 4.6 Streaming-First API Design

The entire response pipeline is streaming:
- API calls use `anthropic.beta.messages.create({...params, stream: true}).withResponse()` returning `Stream<BetaRawMessageStreamEvent>` (raw streaming avoids O(n^2) partial JSON parsing)
- Tool results are streamed back to the model
- UI updates happen incrementally as tokens arrive
- Stream watchdog (90s idle timeout) with non-streaming fallback (Wave 41)
- This minimizes time-to-first-render

### 4.7 Dependency Injection in Query Pipeline

`query.ts` uses a `deps` object for dependency injection:
- `deps.callModel` = `queryModelWithStreaming` (from `query/deps.ts`)
- Enables testing by substituting mock callModel implementations
- Separates concerns: query.ts handles orchestration, claude.ts handles API specifics

### 4.8 Prompt Cache Preservation (Wave 41, 44)

The most critical cross-cutting concern across background services:
- **Beta header latching**: Once sent, headers stay for the session to avoid 50-70K token cache busts
- **CacheSafeParams**: Forked agents share identical params with parent to maximize cache hits
- **Tool denial via callback**: Services deny tools through `canUseTool` callback, NOT by removing them from `tools:[]` (which changes the cache key)
- **PR #18143 cautionary tale**: Setting `effort:'low'` on PromptSuggestion caused 92.7% to 61% cache hit rate drop
- **Static/dynamic boundary**: System prompt split enables cross-org global caching of static sections

### 4.9 Copy-on-Write Speculation (Wave 44)

Speculation uses a filesystem overlay pattern from OS design:
- Writes are redirected to a temporary overlay directory
- Reads check the overlay first, then fall through to the real filesystem
- On accept: overlay files are promoted to the working directory
- On reject/timeout: overlay is discarded with zero side effects
- Enables chains of speculative execution via pipelined suggestions

---

## 5. Technology Stack Summary

| Concern | Solution |
|---------|---------|
| Terminal UI | Ink v5 (React for terminal) |
| CLI parsing | @commander-js/extra-typings |
| AI API | @anthropic-ai/sdk (streaming) |
| MCP | @modelcontextprotocol/sdk |
| Schema validation | zod/v4 |
| Build / DCE | Bun bundle with `feature()` flags |
| Telemetry | OpenTelemetry (metrics + logs + traces) |
| A/B Testing | GrowthBook (`tengu_*` namespace) |
| Storage | Local filesystem (~/.claude/) |
| Auth | OAuth 2.0 PKCE + Keychain (macOS/Windows) |
| Settings | Layered JSON settings with MDM override support |
| Bash parsing | Pure-TS recursive-descent (2,500 LOC, 3,449 golden corpus) |
| Shell security | 4-layer defense-in-depth (pre-parse, AST walk, permission match, read-only validation) |
| System prompt | 54KB `prompts.ts` with static/dynamic cache boundary |

---

## 6. Hook System

The hook system provides **27 hook event types** for extensibility:

Hooks are registered via SDK callbacks and plugin hooks, stored in `bootstrap/state.ts`. They fire at specific lifecycle points throughout the application:
- **PreToolUse / PostToolUse**: Before/after tool execution
- **PermissionRequest**: During permission resolution (can auto-approve/deny)
- **SubagentStart / SubagentEnd**: Agent lifecycle events
- **PreCompact / PostCompact**: Context window compaction events
- **SessionStart / SessionEnd**: Session lifecycle
- And more across the 27 event types

Hooks participate in the 5-way concurrent permission resolver and can modify tool inputs/outputs.

---

## 7. Wave 41-55 Discovery Summary

Key subsystems discovered in Waves 41-55 that were **not documented** in prior analysis:

| Discovery | Wave | Significance |
|-----------|------|-------------|
| 10 undocumented API subsystems (stream watchdog, anti-distillation, beta header latching, prompt cache break detection, tool search, advisor tool, cached microcompact, persistent retry, task budget, 10 supporting API clients) | 41 | API layer is 3x more complex than previously understood |
| Speculation COW overlay filesystem | 44 | OS-level design pattern for zero-side-effect pre-execution |
| Pipelined suggestion chains | 44 | Speculation can chain multiple predicted prompts |
| autoDream 4-phase memory consolidation | 44 | Background "dreaming" with distributed file lock |
| Coordinator mode + AgentSummary | 44 | Multi-agent orchestration with real-time progress visibility |
| Pure-TS bash parser (2,500 LOC) | 48 | Replaced WASM tree-sitter; 3,449 golden corpus for validation |
| 4-layer bash security model | 48 | Defense-in-depth from pre-parse to read-only validation |
| 54KB system prompt with static/dynamic boundary | 55 | Most important file; enables cross-org global caching |
| 18 beta feature headers | 55 | Full API feature surface enumeration |
| Ant vs External build differences | 55 | 6 categories of divergence (comments, output style, nested agents, etc.) |
