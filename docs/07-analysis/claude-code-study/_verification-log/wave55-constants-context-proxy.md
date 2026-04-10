# Wave 55: Constants, Context Providers & Upstream Proxy Deep Analysis

**Date**: 2026-04-01
**Directories**: `src/constants/` (21 files), `src/context/` (9 files), `src/upstreamproxy/` (2 files)
**Total Files**: 32 files analyzed

---

## 1. constants/ Directory — Complete Analysis

### 1.1 prompts.ts — THE System Prompt (54KB, ~915 lines) — CRITICAL

This is the single most important file in Claude Code. It constructs the entire system prompt sent to the Claude API on every turn.

#### System Prompt Architecture

The system prompt is built as an **ordered array of string sections**, split into two zones by a boundary marker:

```
[Static cacheable content]     ← scope: 'global' prefix (Blake2b hashed)
SYSTEM_PROMPT_DYNAMIC_BOUNDARY ← '__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__'
[Dynamic per-session content]  ← recomputed each turn
```

#### Identity Prefixes (from system.ts)

Three identity variants depending on execution context:

| Prefix | When Used |
|--------|-----------|
| `"You are Claude Code, Anthropic's official CLI for Claude."` | Interactive CLI (default) |
| `"...running within the Claude Agent SDK."` | Non-interactive + has appendSystemPrompt |
| `"You are a Claude agent, built on Anthropic's Claude Agent SDK."` | Non-interactive (pure SDK) |

#### Static Sections (Cacheable)

Built by `getSystemPrompt()` — the main entry point:

1. **Intro Section** (`getSimpleIntroSection`):
   - Identity: "interactive agent that helps users with software engineering tasks"
   - Includes `CYBER_RISK_INSTRUCTION` (security boundary)
   - URL generation prohibition

2. **System Section** (`getSimpleSystemSection`):
   - Markdown rendering (CommonMark, monospace)
   - Permission mode awareness
   - `<system-reminder>` tag explanation
   - Hooks awareness
   - Automatic context compression notice

3. **Doing Tasks Section** (`getSimpleDoingTasksSection`):
   - Software engineering focus
   - Code style rules:
     - No gold-plating, no speculative abstractions
     - No TODO comments for core functionality
     - No error handling for impossible scenarios
     - Three similar lines > premature abstraction
   - Ant-only extras:
     - Comment minimalism ("Default to writing no comments")
     - Verify-before-report directive
     - Anti-false-claims instruction
   - Tool preference: dedicated tools > Bash
   - Security: OWASP top 10 awareness
   - `AskUserQuestion` escalation guidance

4. **Actions Section** (`getActionsSection`):
   - Reversibility/blast-radius framework
   - Explicit examples of risky actions:
     - Destructive (delete, drop, kill, rm -rf)
     - Hard-to-reverse (force-push, reset --hard)
     - Visible to others (push, PR, Slack, email)
   - "measure twice, cut once" principle

5. **Using Your Tools Section** (`getUsingYourToolsSection`):
   - Dedicated tool preference matrix:
     - Read > cat/head/tail/sed
     - Edit > sed/awk
     - Write > cat heredoc/echo
     - Glob > find/ls
     - Grep > grep/rg
   - Task management tool awareness
   - Parallel tool call instruction
   - REPL mode variant (simplified)

6. **Tone and Style** (`getSimpleToneAndStyleSection`):
   - No emojis (unless requested)
   - `file_path:line_number` references
   - `owner/repo#123` GitHub format
   - No colon before tool calls

7. **Output Efficiency** (`getOutputEfficiencySection`):
   - **Ant variant** (detailed, ~400 words): "Communicating with the user"
     - Inverted pyramid writing
     - Assume user stepped away
     - No semantic backtracking
     - No superlatives
   - **External variant** (concise): "Go straight to the point"
     - Lead with answer, skip filler
     - Focus: decisions, status, errors

#### Dynamic Sections (Per-Session, Registry-Managed)

Managed via `systemPromptSection()` / `DANGEROUS_uncachedSystemPromptSection()`:

| Section Name | Cache | Content |
|-------------|-------|---------|
| `session_guidance` | Cached | Agent tool, skill discovery, verification agent |
| `memory` | Cached | CLAUDE.md + memory files via `loadMemoryPrompt()` |
| `ant_model_override` | Cached | Ant-only model overrides |
| `env_info_simple` | Cached | CWD, git, platform, shell, OS, model info, knowledge cutoff |
| `language` | Cached | User language preference |
| `output_style` | Cached | Custom output style prompt |
| `mcp_instructions` | **Uncached** | MCP server instructions (connect/disconnect between turns) |
| `scratchpad` | Cached | Session-specific temp directory path |
| `frc` | Cached | Function Result Clearing config |
| `summarize_tool_results` | Cached | "Write down important info" reminder |
| `numeric_length_anchors` | Cached (ant) | "<=25 words between tools, <=100 words final" |
| `token_budget` | Cached | Token target instructions when budget active |
| `brief` | Cached | Brief/Kairos proactive section |

#### Proactive (Autonomous) Mode

Completely different prompt when `isProactiveActive()`:
- "You are an autonomous agent"
- `<tick>` tag handling (wake-up prompts)
- Sleep tool for pacing
- Terminal focus awareness (focused = collaborative, unfocused = autonomous)
- "Bias toward action" principle
- First wake-up: greet and ask, don't explore unprompted

#### Agent Prompt

`DEFAULT_AGENT_PROMPT`: "Complete the task fully -- don't gold-plate, but don't leave it half-done."

`enhanceSystemPromptWithEnvDetails()` adds:
- Notes about absolute paths, no emojis, no colon before tools
- DiscoverSkills guidance for subagents
- Environment info block

#### Knowledge Cutoffs

| Model | Cutoff |
|-------|--------|
| claude-opus-4-6 | May 2025 |
| claude-sonnet-4-6 | August 2025 |
| claude-opus-4-5 | May 2025 |
| claude-haiku-4 | February 2025 |
| claude-opus-4 / claude-sonnet-4 | January 2025 |

#### Frontier Model Constants

```typescript
FRONTIER_MODEL_NAME = 'Claude Opus 4.6'
CLAUDE_4_5_OR_4_6_MODEL_IDS = {
  opus: 'claude-opus-4-6',
  sonnet: 'claude-sonnet-4-6',
  haiku: 'claude-haiku-4-5-20251001',
}
```

#### Feature Flags in System Prompt

- `CACHED_MICROCOMPACT` — Function Result Clearing
- `PROACTIVE` / `KAIROS` — Autonomous mode
- `KAIROS_BRIEF` — Brief tool section
- `EXPERIMENTAL_SKILL_SEARCH` — DiscoverSkills tool
- `TOKEN_BUDGET` — Token budget instructions
- `VERIFICATION_AGENT` — Adversarial verification agent
- `CONNECTOR_TEXT` — Summarize connector text

---

### 1.2 systemPromptSections.ts — Caching Infrastructure

Two-tier section system:

| Function | Behavior |
|----------|----------|
| `systemPromptSection(name, compute)` | Computed once, cached until /clear or /compact |
| `DANGEROUS_uncachedSystemPromptSection(name, compute, reason)` | Recomputes every turn, BREAKS prompt cache |

`resolveSystemPromptSections()` resolves all sections in parallel via `Promise.all()`, using a cache map from `bootstrap/state.js`.

`clearSystemPromptSections()` resets both section cache and beta header latches.

---

### 1.3 betas.ts — API Beta Headers

All beta feature headers for the Anthropic API:

| Header | Feature |
|--------|---------|
| `claude-code-20250219` | Claude Code baseline |
| `interleaved-thinking-2025-05-14` | Extended thinking |
| `context-1m-2025-08-07` | 1M context window |
| `context-management-2025-06-27` | Context management |
| `structured-outputs-2025-12-15` | Structured outputs |
| `web-search-2025-03-05` | Web search |
| `advanced-tool-use-2025-11-20` | Tool search (1P) |
| `tool-search-tool-2025-10-19` | Tool search (3P) |
| `effort-2025-11-24` | Effort control |
| `task-budgets-2026-03-13` | Task budgets |
| `prompt-caching-scope-2026-01-05` | Prompt cache scope |
| `fast-mode-2026-02-01` | Fast mode |
| `redact-thinking-2026-02-12` | Redact thinking |
| `token-efficient-tools-2026-03-28` | Token-efficient tools |
| `summarize-connector-text-2026-03-13` | Connector text (feature-gated) |
| `afk-mode-2026-01-31` | AFK mode (feature-gated) |
| `cli-internal-2026-02-09` | CLI internal (ant-only) |
| `advisor-tool-2026-03-01` | Advisor tool |

Bedrock-specific: `INTERLEAVED_THINKING`, `CONTEXT_1M`, `TOOL_SEARCH_3P` go in extraBodyParams.

---

### 1.4 apiLimits.ts — API Constraints

| Constant | Value | Description |
|----------|-------|-------------|
| `API_IMAGE_MAX_BASE64_SIZE` | 5 MB | Max base64 image size |
| `IMAGE_TARGET_RAW_SIZE` | 3.75 MB | Target raw before encoding |
| `IMAGE_MAX_WIDTH/HEIGHT` | 2000 px | Client-side resize cap |
| `PDF_TARGET_RAW_SIZE` | 20 MB | Max raw PDF size |
| `API_PDF_MAX_PAGES` | 100 | Max PDF pages |
| `PDF_EXTRACT_SIZE_THRESHOLD` | 3 MB | Switch to page extraction |
| `PDF_MAX_EXTRACT_SIZE` | 100 MB | Max for extraction path |
| `PDF_MAX_PAGES_PER_READ` | 20 | Max pages per Read call |
| `PDF_AT_MENTION_INLINE_THRESHOLD` | 10 | Pages before reference mode |
| `API_MAX_MEDIA_PER_REQUEST` | 100 | Max images + PDFs per request |

---

### 1.5 toolLimits.ts — Tool Result Size Limits

| Constant | Value | Description |
|----------|-------|-------------|
| `DEFAULT_MAX_RESULT_SIZE_CHARS` | 50,000 | Per-tool max before disk persist |
| `MAX_TOOL_RESULT_TOKENS` | 100,000 | Token-based cap (~400KB) |
| `BYTES_PER_TOKEN` | 4 | Conservative estimate |
| `MAX_TOOL_RESULT_BYTES` | 400,000 | Derived byte limit |
| `MAX_TOOL_RESULTS_PER_MESSAGE_CHARS` | 200,000 | Per-message aggregate cap |
| `TOOL_SUMMARY_MAX_LENGTH` | 50 | Summary display truncation |

---

### 1.6 tools.ts — Tool Availability Sets

Four permission sets controlling which tools are available to agents:

| Set | Purpose | Key Tools |
|-----|---------|-----------|
| `ALL_AGENT_DISALLOWED_TOOLS` | Blocked for ALL agents | TaskOutput, ExitPlanMode, EnterPlanMode, AskUserQuestion, TaskStop |
| `CUSTOM_AGENT_DISALLOWED_TOOLS` | Blocked for custom agents | Same as above |
| `ASYNC_AGENT_ALLOWED_TOOLS` | Whitelist for async agents | Read, Search, Edit, Write, Shell, Glob, Grep, Notebook, Skill, ToolSearch, Worktree |
| `IN_PROCESS_TEAMMATE_ALLOWED_TOOLS` | Extra tools for teammates | TaskCreate/Get/List/Update, SendMessage, Cron tools |
| `COORDINATOR_MODE_ALLOWED_TOOLS` | Coordinator-only | Agent, TaskStop, SendMessage, SyntheticOutput |

Note: Ant builds allow nested agents (Agent tool not blocked for agents).

---

### 1.7 outputStyles.ts — Built-in Output Modes

Three modes:

| Mode | Description | `keepCodingInstructions` |
|------|-------------|------------------------|
| `default` | null (no override) | N/A |
| `Explanatory` | Insight blocks with educational points | true |
| `Learning` | Interactive "Learn by Doing" prompts | true |

**Learning Mode** is particularly elaborate:
- Requests user to write 2-10 line code pieces
- Uses `TODO(human)` markers in codebase
- Structured request format: Context / Your Task / Guidance
- TodoList integration for task tracking
- Post-contribution insight sharing

Custom styles can come from: plugins (with `forceForPlugin`), user settings, project settings, or managed (policy) settings. Priority: built-in < plugin < user < project < managed.

---

### 1.8 xml.ts — XML Tag Constants

Tags for structured message parsing:

| Category | Tags |
|----------|------|
| **Skill/Command** | `command-name`, `command-message`, `command-args` |
| **Terminal** | `bash-input`, `bash-stdout`, `bash-stderr`, `local-command-stdout/stderr/caveat` |
| **Task** | `task-notification`, `task-id`, `tool-use-id`, `task-type`, `output-file`, `status`, `summary`, `reason` |
| **Worktree** | `worktree`, `worktreePath`, `worktreeBranch` |
| **Planning** | `ultraplan` |
| **Review** | `remote-review`, `remote-review-progress` |
| **Communication** | `teammate-message`, `channel-message`, `channel`, `cross-session-message` |
| **Fork** | `fork-boilerplate` (prefix: "Your directive: ") |
| **Proactive** | `tick` |

Helper arrays: `TERMINAL_OUTPUT_TAGS`, `COMMON_HELP_ARGS`, `COMMON_INFO_ARGS`.

---

### 1.9 Remaining Constants Files

#### common.ts — Date Utilities
- `getLocalISODate()` — local ISO date with `CLAUDE_CODE_OVERRIDE_DATE` support
- `getSessionStartDate()` — memoized once at session start (prompt-cache stability)
- `getLocalMonthYear()` — "Month YYYY" format for tool prompts (monthly change)

#### system.ts — System Identity & Attribution
- Three CLI sysprompt prefixes (see above)
- `getCLISyspromptPrefix()` — selects prefix by context
- `getAttributionHeader()` — `x-anthropic-billing-header` with version, entrypoint, native client attestation placeholder (`cch=00000`), and workload hint

#### files.ts — Binary File Detection
- 112 binary extensions across 11 categories (images, video, audio, archives, executables, documents, fonts, bytecode, databases, design, flash, lock files)
- `hasBinaryExtension()` — extension check
- `isBinaryContent()` — null byte + non-printable ratio (>10% = binary)

#### product.ts — Product URLs & Remote Sessions
- `PRODUCT_URL`: `https://claude.com/claude-code`
- `CLAUDE_AI_BASE_URL`: `https://claude.ai`
- Staging/local detection via session ID patterns (`_staging_`, `_local_`)
- `getRemoteSessionUrl()` with `cse_` -> `session_` compat shim

#### oauth.ts — OAuth Configuration
- Three environments: prod, staging, local
- Prod client ID: `9d1c250a-e61b-44d9-88ed-5944d1962f5e`
- Scopes: `user:inference`, `user:profile`, `org:create_api_key`, `user:sessions:claude_code`, `user:mcp_servers`, `user:file_upload`
- MCP Client Metadata URL (CIMD / SEP-991): `https://claude.ai/oauth/claude-code-client-metadata`
- Custom OAuth URL restricted to FedStart/PubSec allowlist
- MCP proxy: `https://mcp-proxy.anthropic.com/v1/mcp/{server_id}`

#### keys.ts — GrowthBook Client Keys
- Three keys: ant-dev, ant-prod, external

#### errorIds.ts — Error Tracking
- Obfuscated numeric IDs for `logError()` tracing (next ID: 346)

#### cyberRiskInstruction.ts — Security Boundary (Safeguards-Owned)
- Single-paragraph instruction: assist with authorized security testing, refuse destructive/DoS/supply-chain attacks
- Dual-use tools require authorization context
- **DO NOT MODIFY without Safeguards team review**

#### figures.ts — Unicode Glyphs
- Platform-adaptive circles (darwin vs other)
- Effort indicators: `○` (low), `◐` (medium), `●` (high), `◉` (max/Opus 4.6)
- Status: play/pause, refresh, channel arrows, fork glyph, diamonds (review states)
- Bridge spinner frames

#### spinnerVerbs.ts — 204 Loading Verbs
- Alphabetical from "Accomplishing" to "Zigzagging"
- Includes gems like "Clauding", "Flibbertigibbeting", "Prestidigitating"
- Customizable via settings: `replace` or `append` mode

#### turnCompletionVerbs.ts — 8 Past-Tense Verbs
- "Baked", "Brewed", "Churned", "Cogitated", "Cooked", "Crunched", "Sauteed", "Worked"

#### messages.ts — Single Constant
- `NO_CONTENT_MESSAGE = '(no content)'`

#### github-app.ts — GitHub Actions Workflow Templates
- `WORKFLOW_CONTENT`: Claude Code GitHub Action (`anthropics/claude-code-action@v1`)
- `CODE_REVIEW_PLUGIN_WORKFLOW_CONTENT`: Auto-review on PR open/sync
- `PR_BODY`: Detailed PR description with security notes

---

## 2. context/ Directory — React Context Providers (9 files)

All files use React Compiler runtime (`react/compiler-runtime`) for automatic memoization.

### 2.1 notifications.tsx (~33KB)

**Context**: Notification queue and display system.

**Data Shape**:
```typescript
type Notification = {
  key: string
  invalidates?: string[]       // Keys to remove from queue
  priority: 'low' | 'medium' | 'high' | 'immediate'
  timeoutMs?: number           // Default: 8000ms
  fold?: (acc, incoming) => Notification  // Merge same-key notifications
  text?: string                // Text variant
  color?: keyof Theme
  jsx?: React.ReactNode        // JSX variant
}
```

**Hooks**:
- `useNotifications()` -> `{ addNotification, removeNotification }`

**Behavior**:
- Queue-based with priority ordering
- `immediate` priority bypasses queue, clears current timeout
- `fold` function for merging (like Array.reduce for same-key notifications)
- `invalidates` array removes conflicting notifications
- Stored in `AppState.notifications` (Zustand)

### 2.2 stats.tsx (~22KB)

**Context**: Metrics collection with reservoir sampling.

**Data Shape**:
```typescript
type StatsStore = {
  increment(name: string, value?: number): void  // Counters
  set(name: string, value: number): void         // Gauges
  observe(name: string, value: number): void     // Histograms
  add(name: string, value: string): void         // Sets (cardinality)
  getAll(): Record<string, number>               // Export all
}
```

**Histogram Implementation**:
- Algorithm R reservoir sampling (size 1024)
- Exports: `_count`, `_min`, `_max`, `_avg`, `_p50`, `_p95`, `_p99`

**Provider**: `StatsContext` with `createStatsStore()` factory.
Also integrates with `saveCurrentProjectConfig()` for persistence.

### 2.3 overlayContext.tsx (~14KB)

**Context**: Escape key coordination for overlays (Select, MultiSelect, etc.).

**Hooks**:
- `useRegisterOverlay(id, enabled?)` — Register on mount, unregister on unmount
- `useIsOverlayActive()` — Check if any overlay blocks Escape
- `useIsModalOverlayActive()` — Excludes non-modal overlays (e.g., `autocomplete`)

**Storage**: `AppState.activeOverlays` (Set<string>).

Non-modal overlays (like autocomplete) don't disable TextInput focus.

### 2.4 promptOverlayContext.tsx (~12KB)

**Context**: Floating content above prompt input (escapes `overflowY:hidden` clip).

**Two channels**:
1. **Suggestion overlay**: `PromptOverlayData` (suggestions list + selected index + max column width)
2. **Dialog overlay**: Arbitrary `ReactNode` (e.g., AutoModeOptInDialog)

**Hooks**:
- `usePromptOverlay()` — Read suggestion data
- `usePromptOverlayDialog()` — Read dialog node
- `useSetPromptOverlay(data)` — Write suggestions (auto-clears on unmount)
- `useSetPromptOverlayDialog(node)` — Write dialog

Split into data/setter context pairs to prevent re-renders on own writes.

### 2.5 voice.tsx (~8.7KB)

**Context**: Voice input state management.

**Data Shape**:
```typescript
type VoiceState = {
  voiceState: 'idle' | 'recording' | 'processing'
  voiceError: string | null
  voiceInterimTranscript: string
  voiceAudioLevels: number[]
  voiceWarmingUp: boolean
}
```

**Hooks**:
- `useVoiceState(selector)` — Subscribe to slice via `useSyncExternalStore`
- `useSetVoiceState()` — Stable setter reference (synchronous)

Uses custom `Store<T>` from `state/store.js`, not React state.

### 2.6 modalContext.tsx (~6.2KB)

**Context**: Modal slot sizing (set by FullscreenLayout).

**Data Shape**:
```typescript
type ModalCtx = {
  rows: number        // Available content rows
  columns: number     // Available content columns
  scrollRef: RefObject<ScrollBoxHandle | null> | null
}
```

**Hooks**:
- `useIsInsideModal()` — Boolean check
- `useModalOrTerminalSize(fallback)` — Returns modal size or terminal size
- `useModalScrollRef()` — ScrollBox ref for scroll reset on tab switch

### 2.7 QueuedMessageContext.tsx (~5.5KB)

**Context**: Queued message rendering metadata.

**Data Shape**:
```typescript
type QueuedMessageContextValue = {
  isQueued: boolean
  isFirst: boolean
  paddingWidth: number  // Container padding (e.g., 4 for paddingX={2})
}
```

Brief layout mode sets padding to 0 to avoid double-indentation.

### 2.8 mailbox.tsx (~3.4KB)

**Context**: Inter-component message passing.

**Provider**: Creates a singleton `Mailbox` instance (from `utils/mailbox.js`) per app.

**Hook**: `useMailbox()` — throws if used outside provider.

### 2.9 fpsMetrics.tsx (~3.1KB)

**Context**: FPS metrics getter function.

**Data Shape**: `FpsMetricsGetter = () => FpsMetrics | undefined`

**Hook**: `useFpsMetrics()` — Returns the getter (not the metrics directly).

---

## 3. upstreamproxy/ Directory — CCR HTTPS Proxy (2 files)

### 3.1 upstreamproxy.ts — Container-Side Wiring

**Purpose**: MITM proxy for CCR (Claude Code Remote) sessions to inject org-configured credentials.

**Initialization Sequence**:
1. Read session token from `/run/ccr/session_token`
2. `prctl(PR_SET_DUMPABLE, 0)` — block ptrace heap scraping (Linux only, via Bun FFI)
3. Download CA cert from `{baseUrl}/v1/code/upstreamproxy/ca-cert`
4. Concatenate with system CA bundle (`/etc/ssl/certs/ca-certificates.crt`)
5. Start local CONNECT-over-WebSocket relay
6. Unlink token file (stays heap-only)
7. Export env vars for subprocesses

**Guard Conditions**: Only activates when ALL of:
- `CLAUDE_CODE_REMOTE` is truthy
- `CCR_UPSTREAM_PROXY_ENABLED` is truthy (injected server-side)
- `CLAUDE_CODE_REMOTE_SESSION_ID` is set
- Token file exists

**NO_PROXY List**: localhost, RFC1918, IMDS, `*.anthropic.com`, `*.github.com`, npm/pypi/crates/golang registries.

**Subprocess Env Vars**:
```
HTTPS_PROXY / https_proxy = http://127.0.0.1:<port>
NO_PROXY / no_proxy = <see list>
SSL_CERT_FILE / NODE_EXTRA_CA_CERTS / REQUESTS_CA_BUNDLE / CURL_CA_BUNDLE = <ca-bundle-path>
```

### 3.2 relay.ts — CONNECT-over-WebSocket Relay

**Protocol**: HTTP CONNECT requests tunneled over WebSocket using hand-encoded protobuf (`UpstreamProxyChunk { bytes data = 1; }`).

**Why WebSocket**: CCR ingress is GKE L7 with path-prefix routing; no `connect_matcher` in cdk-constructs.

**Architecture**:
1. Local TCP listener on ephemeral port (127.0.0.1:0)
2. Accepts HTTP CONNECT from curl/gh/kubectl
3. Opens WebSocket to `{baseUrl}/v1/code/upstreamproxy/ws`
4. Tunnels bytes bidirectionally with protobuf framing
5. Keepalive ping every 30 seconds

**Dual Runtime Support**:
- **Bun**: `Bun.listen()` with manual write backpressure (`sock.write()` returns partial count)
- **Node**: `net.createServer()` with `ws` package (auto-buffers)

**Connection State Machine**:
```
Phase 1: Accumulate CONNECT request (until CRLFCRLF)
  → Parse target host:port
  → Open WS tunnel
  → Send CONNECT line + Proxy-Authorization
Phase 2: Bidirectional byte forwarding
  → Client TCP data → encodeChunk → ws.send
  → ws.onmessage → decodeChunk → sock.write
```

**Protobuf Encoding** (`encodeChunk`/`decodeChunk`):
- Tag byte: `0x0a` (field 1, wire type 2)
- Varint-encoded length
- Raw bytes
- Max chunk: 512KB (`MAX_CHUNK_BYTES`)

**Error Handling**: Fails open — any error disables proxy, never breaks the session.

---

## 4. Cross-Cutting Observations

### 4.1 Prompt Cache Optimization
- Static/dynamic boundary marker enables cross-org prompt caching
- `systemPromptSection()` memoizes sections
- `DANGEROUS_uncachedSystemPromptSection()` requires explicit reason
- Session start date is memoized to avoid midnight cache busting
- `getLocalMonthYear()` changes monthly (for tool prompts)

### 4.2 Dead Code Elimination (DCE)
- `process.env.USER_TYPE === 'ant'` is a build-time define
- Must be inlined at each callsite (not hoisted to const)
- External builds eliminate ant-only branches entirely
- `feature('...')` from `bun:bundle` gates conditional imports

### 4.3 Ant vs External Differences
| Feature | Ant Build | External Build |
|---------|-----------|----------------|
| Comment guidance | "Default to writing no comments" | Not included |
| Output style | Detailed "Communicating with user" | Concise "Output efficiency" |
| False claims | Explicit anti-hallucination | Not included |
| Nested agents | Allowed | Blocked |
| Numeric length anchors | <=25 words between tools | Not included |
| CLI internal beta | Enabled | Disabled |

### 4.4 Security Patterns
- `CYBER_RISK_INSTRUCTION` owned by Safeguards team
- prctl(PR_SET_DUMPABLE, 0) blocks heap ptrace
- Token file unlinked after relay starts
- OAuth custom URL restricted to FedStart allowlist
- Native client attestation (`cch=00000` placeholder)

---

## 5. File Inventory Summary

### constants/ (21 files, ~115KB total)

| File | Size | Purpose |
|------|------|---------|
| prompts.ts | 54.3KB | **System prompt construction** |
| outputStyles.ts | 9.9KB | Built-in output modes (Explanatory, Learning) |
| oauth.ts | 9.0KB | OAuth config (prod/staging/local) |
| github-app.ts | 5.3KB | GitHub Actions workflow templates |
| tools.ts | 4.7KB | Tool availability sets for agents |
| system.ts | 3.9KB | Identity prefixes + attribution header |
| xml.ts | 3.3KB | XML tag constants |
| spinnerVerbs.ts | 3.5KB | 204 loading spinner verbs |
| apiLimits.ts | 3.4KB | API size/page limits |
| files.ts | 2.6KB | Binary file detection |
| product.ts | 2.6KB | Product URLs + remote session routing |
| betas.ts | 2.2KB | API beta feature headers |
| toolLimits.ts | 2.2KB | Tool result size limits |
| systemPromptSections.ts | 1.8KB | Section caching infrastructure |
| cyberRiskInstruction.ts | 1.5KB | Security boundary instruction |
| common.ts | 1.5KB | Date utilities |
| figures.ts | 2.1KB | Unicode glyphs |
| keys.ts | 0.4KB | GrowthBook API keys |
| errorIds.ts | 0.5KB | Error tracking IDs |
| turnCompletionVerbs.ts | 0.3KB | 8 past-tense verbs |
| messages.ts | 0.05KB | Single constant |

### context/ (9 files, ~108KB total)

| File | Size | Purpose |
|------|------|---------|
| notifications.tsx | 33.0KB | Notification queue system |
| stats.tsx | 22.0KB | Metrics with reservoir sampling |
| overlayContext.tsx | 14.1KB | Escape key coordination |
| promptOverlayContext.tsx | 12.1KB | Floating prompt overlays |
| voice.tsx | 8.8KB | Voice input state |
| modalContext.tsx | 6.3KB | Modal sizing context |
| QueuedMessageContext.tsx | 5.6KB | Queued message metadata |
| mailbox.tsx | 3.4KB | Inter-component messaging |
| fpsMetrics.tsx | 3.2KB | FPS metrics getter |

### upstreamproxy/ (2 files, ~25KB total)

| File | Size | Purpose |
|------|------|---------|
| relay.ts | 14.9KB | CONNECT-over-WebSocket tunnel |
| upstreamproxy.ts | 9.8KB | CCR proxy initialization |
