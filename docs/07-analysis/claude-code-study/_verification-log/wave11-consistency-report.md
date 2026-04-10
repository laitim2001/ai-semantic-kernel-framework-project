# Wave 11: Cross-Report Consistency Verification

> **Date**: 2026-04-01 | **Verifier**: Claude Opus 4.6 (1M context)
> **Scope**: 8 analysis files checked for contradictions, stale claims, terminology drift, and number mismatches
> **Method**: All 8 files read in full; claims compared pairwise; Wave 4/6 corrections used as ground truth

---

## Files Examined

| ID | File | Wave |
|----|------|------|
| F1 | `01-architecture/system-overview.md` | W1 |
| F2 | `01-architecture/data-flow.md` | W1 |
| F3 | `02-core-systems/tool-system.md` | W2 |
| F4 | `02-core-systems/permission-system.md` | W2 |
| F5 | `03-ai-engine/query-engine.md` | W3 |
| F6 | `06-agent-system/agent-delegation.md` | W5 |
| F7 | `01-architecture/wave4-path1-input-to-response.md` | W4 (correction) |
| F8 | `02-core-systems/wave6-permission-deep-analysis.md` | W6 (correction) |

---

## 1. Contradictions (Same Concept Described Differently)

### C1: Permission Mode Count

| File | Claim | Source Truth |
|------|-------|-------------|
| **F1** (system-overview.md) | "PermissionMode: auto, manual, plan, bypassPermissions" — **4 modes** | **WRONG** |
| **F2** (data-flow.md) | Lists: AUTO, MANUAL, PLAN, BYPASS_PERMISSIONS — **4 modes** | **WRONG** |
| **F4** (permission-system.md) | Lists 5 external + 2 internal = **7 modes** (default, acceptEdits, plan, dontAsk, bypassPermissions, auto, bubble) | Partially correct |
| **F8** (wave6, ground truth) | **7 modes**: default, acceptEdits, plan, bypassPermissions, dontAsk (external 5) + auto, bubble (internal 2) | **CORRECT** |

**Inconsistencies**:
- F1 and F2 say "manual" — no such mode exists. The default interactive mode is called `default`, not `manual`.
- F1 and F2 omit `acceptEdits`, `dontAsk`, `bubble` entirely.
- F4 lists `dontAsk` correctly but uses the label "Full bypass (requires explicit enable)" for bypassPermissions, which is slightly misleading — bypass-immune checks still apply per F8 Section 7.

**Status**: F1 and F2 are **stale** — never updated after W6 corrections.

---

### C2: Permission Rule Priority Order

| File | Claim | Source Truth |
|------|-------|-------------|
| **F2** (data-flow.md) | Priority: 1. CLI flags, 2. Enterprise policy, 3. MDM, 4. Project settings, 5. Global user settings, 6. Default tool behavior | **WRONG order** |
| **F4** (permission-system.md) | Sources: policySettings, cliArg, projectSettings, localSettings, userSettings, session, command | Partially matches |
| **F8** (wave6, ground truth) | Sources: policySettings, flagSettings, userSettings, projectSettings, localSettings, cliArg, command, session | **CORRECT** |

**Inconsistencies**:
- F2 puts CLI flags at #1 and enterprise policy at #2. F8 shows `policySettings` first (enterprise managed policies override everything when `allowManagedPermissionRulesOnly` is set).
- F2 lists "MDM managed settings" as #3 — F8 has no separate MDM source; MDM feeds into `policySettings`.
- F4 omits `flagSettings` and reorders: it puts `cliArg` second, but F8 puts `cliArg` sixth.
- F2 lists 6 sources; F4 lists 7; F8 lists 8 (adds `flagSettings`).

**Status**: F2 priority order is **incorrect**. F4 is **incomplete**.

---

### C3: Data Flow — QueryEngine.ts Role

| File | Claim | Source Truth |
|------|-------|-------------|
| **F1** (system-overview.md) | "QueryEngine.ts — Multi-turn conversation loop" (in main REPL path) | **MISLEADING** |
| **F2** (data-flow.md) | Shows QueryEngine.ts as box #2 in the REPL flow after REPL.tsx | **WRONG** |
| **F5** (query-engine.md) | "Implemented in `src/query.ts` (single-turn) and `src/QueryEngine.ts` (multi-turn wrapper)" — implies both are used | **AMBIGUOUS** |
| **F7** (wave4, ground truth) | "QueryEngine.ts is the **SDK/headless** path (non-interactive). The interactive REPL path goes: onSubmit -> handlePromptSubmit -> ... -> query()" | **CORRECT** |

**Inconsistencies**:
- F1 and F2 present QueryEngine.ts as part of the interactive REPL path. F7 proves it is **only** the SDK/headless path.
- F5 does not distinguish between REPL and SDK paths, making it appear both use QueryEngine.ts.

**Status**: F1, F2, F5 are **stale/misleading** — never updated after W4 correction.

---

### C4: API Call Function Name

| File | Claim | Source Truth |
|------|-------|-------------|
| **F2** (data-flow.md) | `api.messages.stream()` | **WRONG** |
| **F7** (wave4, ground truth) | `anthropic.beta.messages.create({...params, stream: true}).withResponse()` at claude.ts:1822 | **CORRECT** |
| **F5** (query-engine.md) | `client.beta.messages.stream()` | **WRONG** (close but still incorrect) |

**Inconsistencies**:
- F2 uses `api.messages.stream()` — wrong object name and wrong method.
- F5 uses `client.beta.messages.stream()` — correct client prefix and beta namespace but wrong method name (`.stream()` vs `.create({stream:true})`).
- F7 provides the verified call: `.beta.messages.create({...params, stream: true}).withResponse()`.

**Status**: Both F2 and F5 have **incorrect API call details**.

---

### C5: System Prompt Assembly Location

| File | Claim | Source Truth |
|------|-------|-------------|
| **F2** (data-flow.md) | `query.ts` does `fetchSystemPromptParts()` and `loadMemoryPrompt()` | **WRONG** |
| **F7** (wave4, ground truth) | System prompt built in `onQueryImpl` (REPL.tsx) via `buildEffectiveSystemPrompt()`. `query.ts` receives it as a parameter. | **CORRECT** |
| **F5** (query-engine.md) | Step 2 lists `getAttachmentMessages()` for memory injection, correctly implies query.ts receives prompt as param | Consistent with F7 |

**Inconsistencies**:
- F2 claims query.ts assembles the system prompt. F7 proves the REPL path builds it in REPL.tsx before calling query().

**Status**: F2 is **stale** — contradicted by W4.

---

### C6: Submit Path Entry Point

| File | Claim | Source Truth |
|------|-------|-------------|
| **F2** (data-flow.md) | "User types message -> useTextInput hook -> submitMessage()" | **WRONG** |
| **F7** (wave4, ground truth) | "`onSubmit` callback in REPL.tsx is the submit handler, not `useTextInput`. `useTextInput` handles keystroke input editing, not submission." | **CORRECT** |

**Status**: F2 is **stale**.

---

### C7: Missing handlePromptSubmit Layer

| File | Claim | Source Truth |
|------|-------|-------------|
| **F2** (data-flow.md) | Flow: REPL.tsx -> QueryEngine.ts -> query.ts (3 layers) | **INCOMPLETE** |
| **F7** (wave4, ground truth) | Flow: REPL.tsx onSubmit -> handlePromptSubmit.ts -> executeUserInput -> processUserInput -> onQuery -> onQueryImpl -> query() (7 layers) | **CORRECT** |

**Inconsistencies**:
- F2 omits 4 intermediate layers: handlePromptSubmit, executeUserInput, processUserInput, onQuery/onQueryImpl.
- handlePromptSubmit handles exit commands, queuing, reference expansion — critical orchestration entirely absent from F2.

**Status**: F2 is **severely incomplete**.

---

## 2. Stale Claims (Wave 1-3 Files Still Saying Things Later Waves Proved Wrong)

| # | File | Stale Claim | Corrected In | Correction |
|---|------|-------------|-------------|------------|
| S1 | F1 | "PermissionMode: auto, manual, plan, bypassPermissions" | F8 (W6) | 7 modes; no "manual" — it's "default" |
| S2 | F2 | QueryEngine.ts in REPL path | F7 (W4) | QueryEngine.ts is SDK-only |
| S3 | F2 | `api.messages.stream()` | F7 (W4) | `anthropic.beta.messages.create({stream:true})` |
| S4 | F2 | `fetchSystemPromptParts()` in query.ts | F7 (W4) | Built in REPL.tsx `onQueryImpl` |
| S5 | F2 | `useTextInput hook -> submitMessage()` | F7 (W4) | `onSubmit` callback, not useTextInput |
| S6 | F2 | 3-layer flow (REPL -> QueryEngine -> query) | F7 (W4) | 7-layer flow with handlePromptSubmit |
| S7 | F5 | `client.beta.messages.stream()` | F7 (W4) | `.create({stream:true}).withResponse()` |
| S8 | F1 | "permissionSetup.ts: Initializes permission context from CLI flags" | F8 (W6) | `permissionsLoader.ts` loads from 8 sources, not just CLI |
| S9 | F4 | Lists 7 rule sources, omits `flagSettings` | F8 (W6) | 8 sources including `flagSettings` |

**data-flow.md (F2) is the most stale file** with 6 uncorrected claims.

---

## 3. Terminology Inconsistencies (Same Thing, Different Names)

| # | Concept | File A Term | File B Term | Recommended |
|---|---------|-------------|-------------|-------------|
| T1 | Default permission mode | F1/F2: "manual" | F4/F8: "default" | `default` (source truth) |
| T2 | Permission bypass mode | F2: "BYPASS_PERMISSIONS" | F4/F8: "bypassPermissions" | `bypassPermissions` (camelCase, matches source) |
| T3 | Auto-mode classifier | F4: "Auto-Mode Classifier" | F8: "YOLO Classifier" / "Auto-Mode Classifier" | Both names are valid; "YOLO" is the internal code name, "auto-mode" is the user-facing name. F4 should mention YOLO as alias. |
| T4 | Tool permission check method | F1: "userPermissionResult()" | F3: "checkPermissions()" | Both exist but serve different roles. F1 incorrectly lists `userPermissionResult()` as the Tool interface method. F3 correctly identifies `checkPermissions()` as the Tool interface method. `userPermissionResult` is an older/wrapper term in data-flow.md. |
| T5 | Permission result type | F2: "ALLOW/DENY/ASK" | F3: "allow/deny/ask/passthrough" | `allow/deny/ask/passthrough` (F3 is correct; F2 omits passthrough) |
| T6 | Tool input validation | F1: "inputSchema: JSON Schema / Zod schema" | F3: "inputSchema: Input // Zod schema" | Zod only. JSON Schema is generated from Zod for the API, not used directly. |
| T7 | Message normalization | F2: "normalizeMessagesForAPI()" | F7: "`buildMessagesForAPI` / `userMessageToMessageParam`" in claude.ts | F7 is correct; the function name in F2 may be outdated or from a different code path. |

---

## 4. Number Mismatches

| # | Metric | File A | File B | Source Truth | Notes |
|---|--------|--------|--------|-------------|-------|
| N1 | Permission modes | F1/F2: 4 | F4: 7 | **F8: 7** | F1/F2 stale |
| N2 | Permission rule sources | F2: 6 | F4: 7 | **F8: 8** | F8 adds `flagSettings` |
| N3 | Components count | F1: "389 files" in components/ | (no other file states a count) | Unverified | Single-source claim, cannot cross-check |
| N4 | Bash security checks | F1: (not mentioned) | F4: "23 security checks" | **F8: "~23 distinct security check IDs"** | F4 and F8 agree |
| N5 | Tool categories in F3 | F3: Core File Ops (5) + Shell (3) + Agent/Task (10) + Planning (3) + Web (3) + MCP (4) + Specialized (10+) = **38+** | F1: lists ~12 tools in overview | F3 is comprehensive | F1 only mentions major subsystems, not full catalog |
| N6 | Permission decision types | F2: 3 (ALLOW/DENY/ASK) | F3: 4 (allow/deny/ask/passthrough) | **F8: 3 in inner (allow/deny/ask) + passthrough-to-ask conversion** | F3's "passthrough" is an intermediate state, not a final decision |
| N7 | Init.ts initialization steps | F1: 13 steps | (no other file counts) | Unverified | Single-source |
| N8 | Denial tracking limits | F4: (not mentioned) | F8: consecutive=3, total=20 | **F8: {maxConsecutive: 3, maxTotal: 20}** | F4 has no denial tracking section |
| N9 | Concurrent permission resolver paths | F4: (not mentioned) | F8: 5 paths | **F8: 5** (user + hooks + classifier + bridge + channel) | F4 omits concurrent resolver entirely |

---

## 5. Internal Consistency Within Correction Files

### F7 (Wave 4) vs F8 (Wave 6)

These two correction files are **consistent with each other**:
- F7 focuses on data flow; F8 focuses on permissions. No overlapping claims conflict.
- F7 says "permission check" happens in tool execution; F8 details exactly how.
- Both agree query.ts receives the system prompt as a parameter (not building it).

### F7 self-consistency check
- F7 lists 7 discrepancies (D1-D7), 8 missing items (M1-M8), and 5 corrections (C1-C5). All are internally consistent.

### F8 self-consistency check
- F8 Section 13 explicitly lists 8 corrections from Wave 4. All match the detailed analysis in Sections 1-12.

---

## 6. Summary: Severity Assessment

| Severity | Count | Description |
|----------|-------|-------------|
| **CRITICAL** | 3 | C1 (permission mode count wrong), C3 (QueryEngine in wrong path), C7 (missing 4 layers) |
| **HIGH** | 3 | C2 (rule priority order wrong), C4 (API function name wrong), C5 (system prompt location wrong) |
| **MEDIUM** | 4 | C6 (submit path entry wrong), S7-S9 (stale claims), T4 (method name confusion) |
| **LOW** | 5 | T1-T3, T5-T7 (terminology drift, cosmetic) |

---

## 7. Recommended Actions

### Priority 1: Update data-flow.md (F2) — 6 stale claims
This file has the most contradictions with later waves. It should either:
- Be rewritten incorporating W4 corrections, OR
- Have a prominent "Superseded by wave4-path1-input-to-response.md" banner added

### Priority 2: Update system-overview.md (F1) — 3 stale claims
- Fix permission mode list (4 -> 7, remove "manual")
- Clarify QueryEngine.ts role (SDK only, not REPL)
- Fix `userPermissionResult()` -> `checkPermissions()` in Tool interface description

### Priority 3: Update query-engine.md (F5) — 1 stale claim
- Fix API call from `client.beta.messages.stream()` to `anthropic.beta.messages.create({stream:true})`
- Add note distinguishing REPL path from SDK/headless path

### Priority 4: Update permission-system.md (F4) — 1 incomplete claim
- Add `flagSettings` to rule sources (8 total, not 7)
- Add cross-reference to F8 for the full 5-way concurrent resolver

### No Action Needed
- **F3** (tool-system.md): Internally consistent, no contradictions found
- **F6** (agent-delegation.md): Internally consistent, no contradictions with other files
- **F7** (wave4 correction): Ground truth, consistent
- **F8** (wave6 correction): Ground truth, consistent

---

*Wave 11 cross-verification complete. 15 inconsistencies identified across 8 files. data-flow.md is the primary source of stale claims.*
