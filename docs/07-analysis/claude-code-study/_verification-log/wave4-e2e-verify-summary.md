# Wave 4 — E2E Path Verification Summary

> Verified: 2026-04-01 | 5 paths traced | Source: CC-Source/src/

---

## Overall Results

| Path | Existing Score | Corrections | Key Finding |
|------|---------------|-------------|-------------|
| **Path 1**: Input → API → Response | 6/10 | 7 major | QueryEngine.ts is SDK-only path, not REPL; missing handlePromptSubmit orchestration layer |
| **Path 2**: Tool Invocation | 9.1/10 | 6 omissions | StreamingToolExecutor enables parallel tool execution; 3-stage validation pipeline undocumented |
| **Path 3**: Permission Checking | 7/10 | 6 corrections | Wrong function name (`userPermissionResult` → `checkPermissions`); cascade order was wrong; 5-way concurrent resolver race |
| **Path 4**: Auto-Compact | 7-9/10 | 3 gaps | data-flow.md uses wrong percentages; context-management.md 9/10 accurate; undocumented REACTIVE_COMPACT and CONTEXT_COLLAPSE |
| **Path 5**: Agent Spawning | 9/10 | minor | 6-way routing decision tree confirmed; fork subagent byte-level cache sharing; foreground-background race pattern |

---

## Critical Corrections by Severity

### ❌ Factual Errors (must fix)

| # | Location | Error | Correct |
|---|----------|-------|---------|
| 1 | data-flow.md §1 | QueryEngine.ts is the REPL conversation loop | QueryEngine.ts is **SDK-only**; REPL uses REPL.tsx → handlePromptSubmit → query() directly |
| 2 | data-flow.md §3 | `userPermissionResult()` function | Correct name: **`checkPermissions()`** (tool) + **`hasPermissionsToUseTool()`** (hook) |
| 3 | data-flow.md §3 | Permission cascade: Mode checked first | Actual: deny rules → ask rules → tool.checkPermissions → **mode at step 4** |
| 4 | data-flow.md §1 | API call: `api.messages.stream()` | Actual: `anthropic.beta.messages.create({stream:true})` via **`deps.callModel()`** injection |
| 5 | data-flow.md §5 | Thresholds use percentages (">85%") | Actual: absolute token counts (`effectiveContextWindow - 13_000`) |
| 6 | data-flow.md §5 | `SDKCompactBoundaryMessage` | Correct type: **`SystemCompactBoundaryMessage`** |

### ⚠️ Major Omissions (should add)

| # | Missing Concept | Details |
|---|----------------|---------|
| 1 | **handlePromptSubmit.ts** | Critical orchestration layer between PromptInput and query() — handles exit commands, queuing, immediate commands |
| 2 | **StreamingToolExecutor** | Enables parallel execution of concurrency-safe tools during API streaming |
| 3 | **3-stage validation pipeline** | Zod parse → validateInput → PreToolUse hooks — all before permission check |
| 4 | **PreToolUse/PostToolUse hooks** | Can modify input, stop execution, override permission decisions |
| 5 | **5-way concurrent permission resolver** | Interactive handler races: user, hooks, classifier, bridge (claude.ai), channel (Telegram/iMessage) |
| 6 | **bypassPermissions immunity** | Content-specific ask rules and .git/.claude safety checks are bypass-immune |
| 7 | **deps injection layer** | query.ts calls `deps.callModel()` not the API directly — enables testing and provider abstraction |
| 8 | **REACTIVE_COMPACT / CONTEXT_COLLAPSE** | Both suppress autocompact; undocumented mutual exclusion |
| 9 | **Fork subagent `renderedSystemPrompt` threading** | Byte-level prompt cache sharing mechanism |
| 10 | **Foreground-background race pattern** | `Promise.race` between message iteration and background signal |

---

## Discovered Architectural Patterns

### 1. Deps Injection Pattern
`query.ts` receives a `deps` object with `callModel()`, `callTool()`, etc. — enables provider abstraction and test mocking without module mocking.

### 2. 5-Way Permission Race
Interactive permission prompts race 5 concurrent resolvers. First to resolve wins. Enables claude.ai web UI to approve permissions while terminal dialog is still showing.

### 3. StreamingToolExecutor Parallel Execution
Tools marked `isConcurrencySafe: true` can execute in parallel during streaming. Default is `false` (fail-closed).

### 4. Fork Subagent Cache Optimization
Fork children receive `renderedSystemPrompt` from parent + placeholder `tool_result` blocks → byte-identical API prefix → prompt cache hit.

### 5. Auto-Compact Circuit Breaker
After 3 consecutive failures, stops retrying. Added after BQ analysis found 1,279 sessions wasting ~250K API calls/day on irrecoverable contexts.

---

## Quality Impact

| Metric | Before Wave 4 | After Wave 4 |
|--------|--------------|-------------|
| Architecture accuracy | ~70% | **~85%** (with corrections) |
| data-flow.md accuracy | ~65% | **~80%** (6 errors identified) |
| Overall study quality | 7.4/10 | **7.7/10** |
| Confidence level | ~70% | **~75%** |

---

## Verification Files

| File | Path Traced |
|------|------------|
| `wave4-path1-input-to-response.md` | User input → API → response rendering |
| `wave4-path2-tool-invocation.md` | Tool detection → execution → result |
| `wave4-path3-permission-flow.md` | Permission cascade (20+ source files) |
| `wave4-path4-autocompact-flow.md` | Context threshold → compaction strategies |
| `wave4-path5-agent-spawning.md` | AgentTool → sub-agent lifecycle |
| **This summary** | — |
