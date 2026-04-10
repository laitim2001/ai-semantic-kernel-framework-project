# Constants, Context Providers & Upstream Proxy

> Deep analysis of system prompt construction, API constants, React context providers, and the CCR upstream proxy.
> Source: `src/constants/` (21 files, ~115KB), `src/context/` (9 files, ~108KB), `src/upstreamproxy/` (2 files, ~25KB)

---

## 1. constants/ Directory -- Complete Analysis

### 1.1 prompts.ts -- THE System Prompt (54KB, ~915 lines) -- CRITICAL

This is the single most important file in Claude Code. It constructs the entire system prompt sent to the Claude API on every turn.

#### System Prompt Architecture

The system prompt is built as an **ordered array of string sections**, split into two zones by a boundary marker:

```
[Static cacheable content]     <-- scope: 'global' prefix (Blake2b hashed)
SYSTEM_PROMPT_DYNAMIC_BOUNDARY <-- '__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__'
[Dynamic per-session content]  <-- recomputed each turn
```

#### Identity Prefixes (from system.ts)

Three identity variants depending on execution context:

| Prefix | When Used |
|--------|-----------|
| `"You are Claude Code, Anthropic's official CLI for Claude."` | Interactive CLI (default) |
| `"...running within the Claude Agent SDK."` | Non-interactive + has appendSystemPrompt |
| `"You are a Claude agent, built on Anthropic's Claude Agent SDK."` | Non-interactive (pure SDK) |

#### Static Sections (Cacheable)

Built by `getSystemPrompt()` -- the main entry point:

1. **Intro Section** (`getSimpleIntroSection`): Identity, `CYBER_RISK_INSTRUCTION` (security boundary), URL generation prohibition
2. **System Section** (`getSimpleSystemSection`): Markdown rendering, permission mode awareness, `<system-reminder>` tag explanation, hooks awareness
3. **Doing Tasks Section** (`getSimpleDoingTasksSection`): Code style rules (no gold-plating, no TODO comments, no speculative abstractions), tool preference (dedicated tools > Bash), OWASP top 10 awareness
4. **Actions Section** (`getActionsSection`): Reversibility/blast-radius framework, explicit risky action examples
5. **Using Your Tools Section** (`getUsingYourToolsSection`): Dedicated tool preference matrix (Read > cat, Edit > sed, Glob > find, Grep > grep)
6. **Tone and Style** (`getSimpleToneAndStyleSection`): No emojis, `file_path:line_number` references, `owner/repo#123` format
7. **Output Efficiency** (`getOutputEfficiencySection`): Ant variant (inverted pyramid writing, ~400 words) vs external variant (concise)

#### Dynamic Sections (Per-Session, Registry-Managed)

Managed via `systemPromptSection()` / `DANGEROUS_uncachedSystemPromptSection()`:

| Section Name | Cache | Content |
|-------------|-------|---------|
| `session_guidance` | Cached | Agent tool, skill discovery, verification agent |
| `memory` | Cached | CLAUDE.md + memory files via `loadMemoryPrompt()` |
| `env_info_simple` | Cached | CWD, git, platform, shell, OS, model info, knowledge cutoff |
| `language` | Cached | User language preference |
| `output_style` | Cached | Custom output style prompt |
| `mcp_instructions` | **Uncached** | MCP server instructions (connect/disconnect between turns) |
| `scratchpad` | Cached | Session-specific temp directory path |
| `frc` | Cached | Function Result Clearing config |
| `token_budget` | Cached | Token target instructions when budget active |

#### Proactive (Autonomous) Mode

Completely different prompt when `isProactiveActive()`: "You are an autonomous agent", `<tick>` tag handling, Sleep tool for pacing, terminal focus awareness, "Bias toward action" principle.

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

---

### 1.2 systemPromptSections.ts -- Caching Infrastructure

Two-tier section system:

| Function | Behavior |
|----------|----------|
| `systemPromptSection(name, compute)` | Computed once, cached until /clear or /compact |
| `DANGEROUS_uncachedSystemPromptSection(name, compute, reason)` | Recomputes every turn, BREAKS prompt cache |

`resolveSystemPromptSections()` resolves all sections in parallel via `Promise.all()`.

---

### 1.3 betas.ts -- API Beta Headers

All beta feature headers for the Anthropic API:

| Header | Feature |
|--------|---------|
| `claude-code-20250219` | Claude Code baseline |
| `interleaved-thinking-2025-05-14` | Extended thinking |
| `context-1m-2025-08-07` | 1M context window |
| `context-management-2025-06-27` | Context management |
| `structured-outputs-2025-12-15` | Structured outputs |
| `web-search-2025-03-05` | Web search |
| `effort-2025-11-24` | Effort control |
| `task-budgets-2026-03-13` | Task budgets |
| `prompt-caching-scope-2026-01-05` | Prompt cache scope |
| `fast-mode-2026-02-01` | Fast mode |
| `token-efficient-tools-2026-03-28` | Token-efficient tools |

---

### 1.4 apiLimits.ts -- API Constraints

| Constant | Value | Description |
|----------|-------|-------------|
| `API_IMAGE_MAX_BASE64_SIZE` | 5 MB | Max base64 image size |
| `IMAGE_TARGET_RAW_SIZE` | 3.75 MB | Target raw before encoding |
| `IMAGE_MAX_WIDTH/HEIGHT` | 2000 px | Client-side resize cap |
| `PDF_TARGET_RAW_SIZE` | 20 MB | Max raw PDF size |
| `API_PDF_MAX_PAGES` | 100 | Max PDF pages |
| `API_MAX_MEDIA_PER_REQUEST` | 100 | Max images + PDFs per request |

### 1.5 toolLimits.ts -- Tool Result Size Limits

| Constant | Value | Description |
|----------|-------|-------------|
| `DEFAULT_MAX_RESULT_SIZE_CHARS` | 50,000 | Per-tool max before disk persist |
| `MAX_TOOL_RESULT_TOKENS` | 100,000 | Token-based cap (~400KB) |
| `MAX_TOOL_RESULTS_PER_MESSAGE_CHARS` | 200,000 | Per-message aggregate cap |

### 1.6 tools.ts -- Tool Availability Sets

| Set | Purpose |
|-----|---------|
| `ALL_AGENT_DISALLOWED_TOOLS` | Blocked for ALL agents (TaskOutput, ExitPlanMode, AskUserQuestion, etc.) |
| `ASYNC_AGENT_ALLOWED_TOOLS` | Whitelist for async agents (Read, Edit, Write, Shell, Glob, Grep, etc.) |
| `IN_PROCESS_TEAMMATE_ALLOWED_TOOLS` | Extra tools for teammates (TaskCreate/Get/List/Update, SendMessage, etc.) |
| `COORDINATOR_MODE_ALLOWED_TOOLS` | Coordinator-only (Agent, TaskStop, SendMessage, SyntheticOutput) |

### 1.7 outputStyles.ts -- Built-in Output Modes

Three modes: `default` (null), `Explanatory` (insight blocks), `Learning` (interactive "Learn by Doing" with `TODO(human)` markers).

### 1.8 xml.ts -- XML Tag Constants

Tags for structured message parsing: `command-name`, `bash-input`, `task-notification`, `worktree`, `teammate-message`, `channel-message`, `tick`, etc.

### 1.9 Remaining Constants Files

| File | Purpose |
|------|---------|
| `common.ts` | Date utilities (`getLocalISODate()`, `getSessionStartDate()`) |
| `system.ts` | System identity prefixes + attribution header |
| `files.ts` | Binary file detection (112 extensions across 11 categories) |
| `product.ts` | Product URLs, remote session URL construction |
| `oauth.ts` | OAuth config (prod/staging/local), client ID, scopes, MCP proxy URL |
| `keys.ts` | GrowthBook API keys |
| `errorIds.ts` | Obfuscated numeric IDs for error tracing |
| `cyberRiskInstruction.ts` | Security boundary instruction (Safeguards-owned, DO NOT MODIFY) |
| `figures.ts` | Unicode glyphs (platform-adaptive), effort indicators, status symbols |
| `spinnerVerbs.ts` | 204 loading verbs ("Accomplishing" to "Zigzagging") |
| `turnCompletionVerbs.ts` | 8 past-tense verbs |
| `messages.ts` | `NO_CONTENT_MESSAGE = '(no content)'` |
| `github-app.ts` | GitHub Actions workflow templates |

---

## 2. context/ Directory -- React Context Providers (9 files)

All files use React Compiler runtime (`react/compiler-runtime`) for automatic memoization.

### 2.1 notifications.tsx (~33KB)

Notification queue and display system with priority ordering, fold function for merging same-key notifications, and `invalidates` array for conflict resolution.

```typescript
type Notification = {
  key: string
  invalidates?: string[]
  priority: 'low' | 'medium' | 'high' | 'immediate'
  timeoutMs?: number  // Default: 8000ms
  fold?: (acc, incoming) => Notification
  text?: string
  jsx?: React.ReactNode
}
```

### 2.2 stats.tsx (~22KB)

Metrics collection with **Algorithm R reservoir sampling** (size 1024). Exports: `_count`, `_min`, `_max`, `_avg`, `_p50`, `_p95`, `_p99`. Supports counters (`increment`), gauges (`set`), histograms (`observe`), and sets (`add`).

### 2.3 overlayContext.tsx (~14KB)

Escape key coordination for overlays. `useRegisterOverlay(id)` registers on mount, `useIsOverlayActive()` checks if any overlay blocks Escape. Non-modal overlays (like autocomplete) don't disable TextInput focus.

### 2.4 promptOverlayContext.tsx (~12KB)

Floating content above prompt input with two channels: suggestion overlay and dialog overlay. Split into data/setter context pairs to prevent re-renders on own writes.

### 2.5 voice.tsx (~8.7KB)

Voice input state management: `'idle' | 'recording' | 'processing'` with interim transcript, audio levels, warming-up flag. Uses custom `Store<T>` with `useSyncExternalStore`.

### 2.6 modalContext.tsx (~6.2KB)

Modal slot sizing (rows, columns, scrollRef). `useModalOrTerminalSize(fallback)` returns modal size or terminal size.

### 2.7 QueuedMessageContext.tsx (~5.5KB)

Queued message rendering metadata: `isQueued`, `isFirst`, `paddingWidth`.

### 2.8 mailbox.tsx (~3.4KB)

Inter-component message passing. Creates singleton `Mailbox` instance per app.

### 2.9 fpsMetrics.tsx (~3.1KB)

FPS metrics getter function context.

---

## 3. upstreamproxy/ Directory -- CCR HTTPS Proxy (2 files, ~25KB)

### 3.1 upstreamproxy.ts -- Container-Side Wiring

**Purpose**: MITM proxy for CCR (Claude Code Remote) sessions to inject org-configured credentials.

**Initialization Sequence**:
1. Read session token from `/run/ccr/session_token`
2. `prctl(PR_SET_DUMPABLE, 0)` -- block ptrace heap scraping (Linux only, via Bun FFI)
3. Download CA cert from `{baseUrl}/v1/code/upstreamproxy/ca-cert`
4. Concatenate with system CA bundle (`/etc/ssl/certs/ca-certificates.crt`)
5. Start local CONNECT-over-WebSocket relay
6. Unlink token file (stays heap-only)
7. Export env vars for subprocesses

**Guard Conditions**: Only activates when ALL of:
- `CLAUDE_CODE_REMOTE` is truthy
- `CCR_UPSTREAM_PROXY_ENABLED` is truthy
- `CLAUDE_CODE_REMOTE_SESSION_ID` is set
- Token file exists

**NO_PROXY List**: localhost, RFC1918, IMDS, `*.anthropic.com`, `*.github.com`, npm/pypi/crates/golang registries.

### 3.2 relay.ts -- CONNECT-over-WebSocket Relay

**Protocol**: HTTP CONNECT requests tunneled over WebSocket using hand-encoded protobuf (`UpstreamProxyChunk { bytes data = 1; }`).

**Why WebSocket**: CCR ingress is GKE L7 with path-prefix routing; no `connect_matcher` in cdk-constructs.

**Architecture**:
1. Local TCP listener on ephemeral port (127.0.0.1:0)
2. Accepts HTTP CONNECT from curl/gh/kubectl
3. Opens WebSocket to `{baseUrl}/v1/code/upstreamproxy/ws`
4. Tunnels bytes bidirectionally with protobuf framing
5. Keepalive ping every 30 seconds

**Dual Runtime Support**:
- **Bun**: `Bun.listen()` with manual write backpressure
- **Node**: `net.createServer()` with `ws` package (auto-buffers)

**Max chunk**: 512KB (`MAX_CHUNK_BYTES`)

**Error Handling**: Fails open -- any error disables proxy, never breaks the session.

---

## 4. Cross-Cutting Observations

### Prompt Cache Optimization
- Static/dynamic boundary marker enables cross-org prompt caching
- `systemPromptSection()` memoizes sections
- `DANGEROUS_uncachedSystemPromptSection()` requires explicit reason
- Session start date is memoized to avoid midnight cache busting

### Dead Code Elimination (DCE)
- `process.env.USER_TYPE === 'ant'` is a build-time define
- Must be inlined at each callsite (not hoisted to const)
- External builds eliminate ant-only branches entirely

### Ant vs External Differences
| Feature | Ant Build | External Build |
|---------|-----------|----------------|
| Comment guidance | "Default to writing no comments" | Not included |
| Output style | Detailed "Communicating with user" | Concise "Output efficiency" |
| False claims | Explicit anti-hallucination | Not included |
| Nested agents | Allowed | Blocked |
| Numeric length anchors | <=25 words between tools | Not included |

### Security Patterns
- `CYBER_RISK_INSTRUCTION` owned by Safeguards team
- `prctl(PR_SET_DUMPABLE, 0)` blocks heap ptrace
- Token file unlinked after relay starts
- OAuth custom URL restricted to FedStart allowlist
