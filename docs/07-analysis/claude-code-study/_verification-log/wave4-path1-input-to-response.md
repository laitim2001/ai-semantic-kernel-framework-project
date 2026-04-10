# Wave 4 — E2E Path 1: User Input → API → Response

> Verification Date: 2026-04-01 | Verifier: Claude Opus 4.6 (1M context)
> Source files traced end-to-end against actual CC source code

---

## Actual Call Chain (from source)

### Phase A: User Submits Input (REPL → handlePromptSubmit)

1. **[REPL.tsx:3142]** `onSubmit(input, helpers, speculationAccept?, options?)` — `useCallback` in REPL component. User presses Enter.
   - Handles immediate `/` commands (keybinding-triggered), idle-return checks, history tracking
   - Calls `setUserInputOnProcessing(input)` to show placeholder immediately (line 3369)
   - Calls `awaitPendingHooks()` to ensure SessionStart hook context is ready (line 3489)

2. **[REPL.tsx:3490]** `await handlePromptSubmit({...})` — passes input, mode, messages, onQuery, pastedContents, etc.

3. **[handlePromptSubmit.ts:120]** `handlePromptSubmit(params)` — Entry point for input processing
   - Handles exit commands (exit/quit/:q/:wq) → redirects to `/exit` (line 194-211)
   - Expands `[Pasted text #N]` references via `expandPastedTextRefs()` (line 216)
   - Handles immediate local-jsx commands while loading (line 229-310)
   - If already loading → enqueues via `enqueue({value, mode, ...})` (line 336)
   - If idle → constructs `QueuedCommand` and calls `executeUserInput()` (line 368)

4. **[handlePromptSubmit.ts:396]** `executeUserInput(params)` — Core execution logic
   - Creates fresh `AbortController` (line 419)
   - Reserves `queryGuard` (line 437) — prevents concurrent execution
   - Iterates `queuedCommands` array, calling `processUserInput()` for each (line 476)

### Phase B: Input Classification & Message Creation (processUserInput)

5. **[processUserInput.ts:85]** `processUserInput({input, mode, ...})` — Main routing function
   - Shows user input placeholder via `setUserInputOnProcessing` (line 146)
   - Delegates to `processUserInputBase()` (line 153)
   - After base processing, runs `executeUserPromptSubmitHooks()` for hook blocking/context (line 182)

6. **[processUserInput.ts:281]** `processUserInputBase(input, mode, ...)` — Routing logic
   - Image processing: resizes pasted images via `maybeResizeAndDownsampleImageBlock()` (line 322)
   - Attachment extraction: `getAttachmentMessages()` for IDE selection, files, etc. (line 503)
   - **Routing decision (by mode + input prefix):**
     - `mode === 'bash'` → `processBashCommand()` (line 518)
     - `inputString.startsWith('/')` → `processSlashCommand()` (line 538)
     - Ultraplan keyword detected → rewritten to `/ultraplan` (line 467-493)
     - Otherwise → **`processTextPrompt()`** (line 578) — regular user prompt path

7. **[processTextPrompt.ts:19]** `processTextPrompt(normalizedInput, imageBlocks, ...)` — Creates `UserMessage`
   - Returns `{ messages: [UserMessage + attachments], shouldQuery: true }`

### Phase C: Query Initiation (executeUserInput → onQuery → onQueryImpl)

8. **[handlePromptSubmit.ts:560]** `await onQuery(newMessages, abortController, shouldQuery, allowedTools, model, onBeforeQuery, input, effort)`
   - This callback is defined in REPL.tsx

9. **[REPL.tsx:2855]** `onQuery(newMessages, abortController, ...)` — REPL's query handler
   - Acquires `queryGuard.tryStart()` (line 2869) — returns generation number or null
   - Appends `newMessages` to messages via `setMessages()` (line 2891)
   - Resets streaming state (responseLengthRef, apiMetricsRef, streamingToolUses)
   - Calls `onQueryImpl()` (line 2918)

10. **[REPL.tsx:2661]** `onQueryImpl(messagesIncludingNewMessages, newMessages, abortController, shouldQuery, ...)` — Core query implementation
    - Prepares IDE integration, generates session title from first user message (line 2684)
    - Builds system prompt via `buildEffectiveSystemPrompt()` (line 2781)
    - Loads context (CLAUDE.md, user context, system context) (line 2780)

### Phase D: Query Loop — API Call (query.ts → claude.ts)

11. **[REPL.tsx:2793]** `for await (const event of query({messages, systemPrompt, userContext, ...}))` — enters query loop
    - Each event passed to `onQueryEvent(event)` (line 2802)

12. **[query.ts:219]** `query(params)` → delegates to `queryLoop(params)` via `yield*` (line 230)

13. **[query.ts:241]** `queryLoop(params)` — The agentic loop (`while(true)`)
    - Destructures mutable state each iteration (messages, toolUseContext, turnCount) (line 311)
    - Yields `{ type: 'stream_request_start' }` (line 337)
    - Prepares `messagesForQuery` from post-compact-boundary messages (line 365)
    - Handles auto-compact and micro-compact if needed (lines 414, 454)

14. **[query.ts:659]** `for await (const message of deps.callModel({messages, systemPrompt, ...}))` — calls the model
    - `deps.callModel` = `queryModelWithStreaming` from `query/deps.ts` (line 35)

15. **[claude.ts:752]** `queryModelWithStreaming({messages, systemPrompt, thinkingConfig, tools, signal, options})`
    - Wraps `queryModel()` with VCR recording via `withStreamingVCR()` (line 770)

16. **[claude.ts:1017]** `queryModel(messages, systemPrompt, thinkingConfig, tools, signal, options)` — Core API function
    - Off-switch check (line 1031)
    - Resolves model, builds beta headers, tool schemas
    - Builds `params` object with system prompt blocks, message params, tools, thinking config

17. **[claude.ts:1822]** `anthropic.beta.messages.create({...params, stream: true}, {signal}).withResponse()` — **THE ACTUAL API CALL**
    - Uses `@anthropic-ai/sdk` client with raw streaming (not `BetaMessageStream`)
    - Returns `Stream<BetaRawMessageStreamEvent>` (line 1857)

### Phase E: Stream Processing & Rendering

18. **[claude.ts:1848-1857]** Stream iteration begins — yields `StreamEvent` objects wrapping raw SSE events
    - Each SSE event (`message_start`, `content_block_start`, `content_block_delta`, `message_delta`, `message_stop`) wrapped as `{ type: 'stream_event', event }` and yielded

19. **[query.ts:659-708]** Query loop receives streamed messages
    - Accumulates `assistantMessages`, `toolUseBlocks`, `toolResults`
    - On tool_use: executes via `StreamingToolExecutor` (parallel tool execution)
    - If tool results exist → appends to messages, continues loop (next API call)
    - If no tool_use → returns terminal result

20. **[REPL.tsx:2802]** `onQueryEvent(event)` — receives each event from query()

21. **[REPL.tsx:2584]** `onQueryEvent` calls `handleMessageFromStream(event, onMessage, onUpdateLength, ...)`

22. **[messages.ts:2930]** `handleMessageFromStream(message, onMessage, onUpdateLength, onSetStreamMode, ...)` — Stream event router
    - **Non-stream events** (assistant/user/system messages): calls `onMessage(message)` → `setMessages()` (line 2980)
    - **`stream_request_start`**: sets spinner to `'requesting'` (line 2985)
    - **`message_start`**: records TTFT metrics (line 2990)
    - **`content_block_start`**:
      - `thinking` → `onSetStreamMode('thinking')` (line 3014)
      - `text` → `onSetStreamMode('responding')` (line 3017)
      - `tool_use` → `onSetStreamMode('tool-input')` + adds to `streamingToolUses` (line 3020-3031)
    - **`content_block_delta`**: updates streaming text via `onStreamingText` and `onUpdateLength`
    - **`message_stop`**: sets mode to `'tool-use'`, clears streaming tool uses (line 2996)

23. **[REPL.tsx:2629]** `setMessages(oldMessages => [...oldMessages, newMessage])` — React state update triggers re-render
    - Messages component renders conversation including new assistant message
    - Spinner/streaming indicators controlled by `streamMode` state

---

## Discrepancies vs data-flow.md

### D1: Missing `handlePromptSubmit` layer
- **data-flow.md** shows: `REPL.tsx → submitMessage() → QueryEngine.ts`
- **Actual**: `REPL.tsx onSubmit → handlePromptSubmit.ts → executeUserInput → processUserInput → onQuery → onQueryImpl → query()`
- `handlePromptSubmit.ts` is a critical intermediate layer that handles exit commands, queuing, immediate commands, and reference expansion. It is entirely absent from the existing analysis.

### D2: `useTextInput` hook is not the submit path
- **data-flow.md** says: "User types message → useTextInput hook → submitMessage()"
- **Actual**: `onSubmit` callback in REPL.tsx is the submit handler, not `useTextInput`. `useTextInput` handles keystroke input editing, not submission.

### D3: QueryEngine.ts is NOT in the interactive REPL path
- **data-flow.md** shows QueryEngine.ts as the second box in the flow
- **Actual**: `QueryEngine.ts` is the **SDK/headless** path (non-interactive). The interactive REPL path goes: `onSubmit → handlePromptSubmit → executeUserInput → processUserInput → onQuery → onQueryImpl → query()`. QueryEngine has its own `submitMessage()` that calls `processUserInput` and `query()` directly, but this is only used by the programmatic SDK API, not the terminal REPL.

### D4: System prompt assembly location is wrong
- **data-flow.md** says: `query.ts` does `fetchSystemPromptParts()` and `loadMemoryPrompt()`
- **Actual**: In the REPL path, `fetchSystemPromptParts()` is called in `onQueryImpl` (REPL.tsx:2781 area) via `buildEffectiveSystemPrompt()`, NOT inside `query.ts`. In the SDK path, `fetchSystemPromptParts()` is called in `QueryEngine.ts:292`. `query.ts` receives the already-built system prompt as a parameter.

### D5: `normalizeMessagesForAPI()` not called in query.ts
- **data-flow.md** lists `normalizeMessagesForAPI()` as step 4 in query.ts
- **Actual**: Message normalization happens inside `claude.ts`'s `queryModel()` function (via `buildMessagesForAPI` / `userMessageToMessageParam` / `assistantMessageToMessageParam`), not in query.ts.

### D6: API call function name is wrong
- **data-flow.md** says: `api.messages.stream()`
- **Actual**: `anthropic.beta.messages.create({...params, stream: true}).withResponse()` at claude.ts:1822. It uses the beta API with raw streaming, NOT `messages.stream()`.

### D7: Missing `deps` indirection layer
- **data-flow.md** shows query.ts calling API directly
- **Actual**: query.ts calls `deps.callModel()` which maps to `queryModelWithStreaming` via `query/deps.ts`. This dependency injection pattern enables testing.

---

## Missing from existing analysis

### M1: `handlePromptSubmit.ts` — Critical orchestration layer
- Handles exit commands, reference expansion, immediate commands, queue management
- This is where `processUserInput` is actually called in the interactive path
- Manages `queryGuard` reservation to prevent concurrent execution

### M2: `onQueryEvent` + `handleMessageFromStream` — Stream-to-UI bridge
- The existing analysis jumps from "API streaming" to "REPL renders it"
- In reality, `handleMessageFromStream()` (messages.ts:2930) is a complex router that:
  - Sets spinner mode (requesting → thinking → responding → tool-input → tool-use)
  - Manages `streamingToolUses` state for live tool input display
  - Handles tombstone messages for orphaned streaming attempts
  - Replaces ephemeral progress messages (sleep/bash ticks) instead of appending
  - Manages `streamingThinking` and `streamingText` state

### M3: Query guard mechanism
- `queryGuard` (QueryGuard.ts) is a state machine (idle → dispatching → running → idle)
- Prevents concurrent query execution; queues input when a query is active
- `tryStart()` atomically transitions state and returns generation number
- `end(generation)` validates ownership before transitioning back

### M4: `QueuedCommand` abstraction
- Both direct user input and queued commands go through the same `executeUserInput` path
- First command gets full treatment (attachments, IDE selection, pasted contents)
- Commands 2-N get `skipAttachments` to avoid duplicating context

### M5: UserPromptSubmit hooks
- After `processUserInputBase`, hooks are executed via `executeUserPromptSubmitHooks()`
- Hooks can block the query, add additional context, or prevent continuation
- Hook outputs are truncated to 10,000 characters

### M6: `StreamingToolExecutor` — Parallel tool execution
- query.ts uses `StreamingToolExecutor` for parallel tool execution during streaming
- Handles streaming fallback (tombstoning orphaned messages from failed streaming attempt)

### M7: `withStreamingVCR` wrapper
- `queryModelWithStreaming` wraps `queryModel` with VCR recording
- Enables replay/recording of API interactions

### M8: `runWithWorkload` context
- `executeUserInput` wraps the entire turn in `AsyncLocalStorage` context via `runWithWorkload`
- Propagates workload context across await boundaries for background agents

---

## Corrections needed

### C1: Rewrite the primary data flow diagram
Replace the current 5-box linear flow with the actual 7-layer chain:

```
REPL.tsx onSubmit
  → handlePromptSubmit.ts (orchestration: exit, queue, immediate cmds)
    → executeUserInput (queryGuard, abort controller)
      → processUserInput (routing: bash/slash/text + hooks)
        → onQuery callback (REPL.tsx — guard, state reset)
          → onQueryImpl (system prompt, context loading)
            → query() loop (query.ts — agentic while-loop)
              → deps.callModel → queryModelWithStreaming
                → queryModel → anthropic.beta.messages.create({stream:true})
```

### C2: Distinguish REPL path vs SDK/headless path
The existing analysis conflates QueryEngine.ts (SDK) with the REPL path. These should be documented as two separate flows:
- **Interactive REPL**: onSubmit → handlePromptSubmit → processUserInput → onQuery → query()
- **SDK/Headless**: QueryEngine.submitMessage() → processUserInput → query()

### C3: Fix API call details
- Change `api.messages.stream()` to `anthropic.beta.messages.create({...params, stream: true}).withResponse()`
- Note that it uses raw `Stream<BetaRawMessageStreamEvent>`, NOT `BetaMessageStream` (to avoid O(n^2) partial JSON parsing)

### C4: Add stream-to-render pipeline
Insert the missing rendering chain:
```
query() yields StreamEvent/Message
  → onQueryEvent (REPL.tsx callback)
    → handleMessageFromStream (messages.ts)
      → onMessage → setMessages → React re-render
      → onSetStreamMode → spinner/indicator updates
      → onStreamingText → live text display
      → onStreamingToolUses → live tool input display
```

### C5: Add handleMessageFromStream detail to stream processing section
The current "Stream Processing Loop" box is oversimplified. The actual stream processing involves:
- SpinnerMode state machine: `requesting → thinking → responding → tool-input → tool-use`
- Ephemeral progress message replacement (not append)
- Tombstone handling for streaming fallback
- TTFT metrics capture on `message_start`

---

## Confidence Assessment

| Aspect | Confidence | Notes |
|--------|-----------|-------|
| Call chain order | 95% | Verified via imports, function signatures, and line-by-line reads |
| Function names | 98% | Read directly from source |
| Line numbers | 90% | Source may have shifted since snapshot; numbers are from reading session |
| API call details | 98% | `anthropic.beta.messages.create({stream:true})` confirmed at claude.ts:1822 |
| Rendering pipeline | 90% | handleMessageFromStream confirmed; deeper Ink/React rendering not traced |
| Discrepancy assessment | 95% | Each discrepancy verified against both data-flow.md text and actual source |
