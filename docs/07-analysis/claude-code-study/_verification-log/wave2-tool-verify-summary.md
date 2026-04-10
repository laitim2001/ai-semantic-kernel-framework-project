# Wave 2 — Tool Verification Summary

> Verified: 2026-04-01 | 4 batches × 10 tools | Source: CC-Source/src/tools/

---

## Overall Results

| Metric | Value |
|--------|-------|
| **Tools verified** | 40 directories + tools.ts registry |
| **Fully accurate** | ~30/40 (75%) |
| **Minor issues** | ~7/40 (17.5%) |
| **Incorrect/Missing** | ~3/40 (7.5%) |
| **Wave 1 quality estimate** | 6.5-7.0/10 |
| **Post-Wave 2 quality estimate** | 7.2/10 |

---

## Critical Corrections Needed

### 1. Tool Count is ~57+, NOT 52
**Source**: Batch 4 — `src/tools.ts` registry analysis

`tools.ts` references 14+ additional tool directories not present in the CC-Source dump (feature-gated/stripped from external builds). The conditional tools list in `00-stats.md` listed only 7, but actual count is 16+.

**Action**: Update `00-stats.md` tool count from "52" to "57+ (40 in source + 16+ conditional/feature-gated)"

### 2. BriefTool is Actually `SendUserMessage`
**Source**: Batch 1

The directory is named `BriefTool` but the registered tool name is `SendUserMessage`. Category should be `Interaction`, not `Files`. Description "Uploads attachments/briefs" is misleading — it actually sends messages/files to the user in KAIROS assistant mode.

**Action**: Rename in `00-stats.md` and `tool-system.md`

### 3. SyntheticOutputTool is Actually `StructuredOutput`
**Source**: Batch 3

Registered name is `StructuredOutput`, not `SyntheticOutput`. The tool emits structured JSON output for SDK consumers.

**Action**: Fix name in `00-stats.md`

### 4. TaskCreateTool Creates TodoV2, NOT "Background Tasks"
**Source**: Batch 3

`00-stats.md` describes TaskCreateTool as "Creates background tasks" — it actually creates TodoV2 task items (structured todo lists with status tracking). Background task creation is done by AgentTool.

**Action**: Fix description in `00-stats.md`

### 5. TaskOutputTool is Deprecated and Reads Output (Not Emits)
**Source**: Batch 4

Described as "Emits structured output from tasks" — it actually *reads/retrieves* task output. It's deprecated in favor of TaskGetTool.

**Action**: Fix description and add deprecation note

### 6. ScheduleCronTool is Actually 3 Separate Tools
**Source**: Batch 3

One directory contains CronCreateTool, CronDeleteTool, CronListTool — three distinct registered tools, not one.

**Action**: Split in `00-stats.md` catalog (already partially noted but needs explicit separation)

### 7. LSPTool Capabilities Understated
**Source**: Batch 2

Described as "diagnostics, symbols" — actually provides 9 operations: definitions, references, hover, symbols, call hierarchy, implementation, type definitions, document symbols, workspace symbols. Does NOT provide diagnostics.

**Action**: Fix description in `00-stats.md`

---

## Notable Discoveries (Not in Wave 1 Analysis)

### Architectural Patterns Found

| Pattern | Tools | Description |
|---------|-------|-------------|
| **shouldDefer: true** | AgentTool, BashTool, others | Lazy schema loading — defers Zod schema construction until first use |
| **Factory pattern** | McpAuthTool | `createMcpAuthTool()` generates dynamic tool instances per MCP server |
| **TodoV1/V2 mutual exclusivity** | TodoWriteTool, TaskCreateTool | Feature flag `TODOV2` switches between two incompatible implementations |
| **Teammate-aware scoping** | TaskCreateTool, TaskGetTool, TaskListTool, TaskUpdateTool, TodoWriteTool | Tools filter by `agentId` to scope data per-agent in swarm mode |
| **Verification nudge** | TodoWriteTool, TaskUpdateTool | Appends "verify work before marking complete" instruction to tool results |

### Security Details

| Tool | Security Feature |
|------|-----------------|
| BashTool | ~200KB security codebase (bashSecurity.ts + bashPermissions.ts), far more than "23 checks" |
| PowerShellTool | 11 supporting files with AST-based permission analysis |
| SendMessageTool | 6+ routing paths with shutdown protocol, plan approval, bridge/UDS messaging |
| WebSearchTool | Provider-based gating (Brave, Tavily) with API key validation |

### Missing Source Files
- `SleepTool` — only prompt.ts/constants.ts available (implementation stripped)
- `REPLTool` — only prompt.ts available (ant-only, fully stripped)
- 14 phantom directories referenced in tools.ts but absent from dump

---

## Per-Batch Accuracy

| Batch | Tools | Accuracy | Major Issues |
|-------|-------|----------|-------------|
| Batch 1 (#1-10) | 8/10 ✅, 2 ⚠️ | 8.5/10 | BriefTool name/category wrong |
| Batch 2 (#11-20) | 9/10 ✅, 1 ⚠️ | 9.0/10 | LSPTool capabilities understated |
| Batch 3 (#21-30) | 6/10 ✅, 3 ⚠️, 1 ❌ | 7.5/10 | ScheduleCron=3 tools, SyntheticOutput name wrong |
| Batch 4 (#31-40) | 8/10 ✅, 2 ⚠️ | 8.5/10 | TaskOutputTool deprecated, tool count wrong |

---

## Corrections Applied Status

| # | Correction | Status |
|---|-----------|--------|
| 1 | Tool count 52 → 57+ | ⏳ Pending |
| 2 | BriefTool → SendUserMessage | ⏳ Pending |
| 3 | SyntheticOutputTool → StructuredOutput | ⏳ Pending |
| 4 | TaskCreateTool description | ⏳ Pending |
| 5 | TaskOutputTool deprecated + read not emit | ⏳ Pending |
| 6 | ScheduleCronTool → 3 tools | ⏳ Pending |
| 7 | LSPTool capabilities | ⏳ Pending |

---

## Verification Files

| File | Size |
|------|------|
| `wave2-tool-verify-batch1.md` | 15.9 KB |
| `wave2-tool-verify-batch2.md` | 19.6 KB |
| `wave2-tool-verify-batch3.md` | 22.7 KB |
| `wave2-tool-verify-batch4.md` | 24.1 KB |
| **This summary** | — |
| **Total Wave 2 output** | ~82 KB |
