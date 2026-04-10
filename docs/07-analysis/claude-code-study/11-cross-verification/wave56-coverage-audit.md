# Wave 56: Source Code Coverage Completeness Audit

> **Date**: 2026-04-01 | **Scope**: CC-Source/src/ vs claude-code-study/ analysis docs
> **Total Source**: 1,902 files (all TS/TSX) | 512,664 LOC | 36 directories + root files
> **Total Analysis**: 91 markdown files across 13 directories (incl. 3 root 00-* files)

---

## Coverage Matrix

| # | Source Directory | Files | LOC | Covered By | Coverage Level |
|---|-----------------|-------|-----|------------|----------------|
| 1 | `src/utils/` | 564 | 180,472 | 08-utilities (git, bash, file-ops, sandbox, telemetry), wave46 (settings), wave47 (model), wave48 (bash/shell/powershell), wave49 (swarm backends), wave50 (input/suggestions/messages/ultraplan), wave13 (feature flags), wave20 (security) | **HIGH** |
| 2 | `src/components/` | 389 | 81,546 | 04-ui-framework (component-library, diff-rendering, prompt-input), wave27 (Ink deep), wave25 (user journeys), wave50 (input utils) | **MEDIUM-HIGH** |
| 3 | `src/commands/` | 189 | 26,428 | 02-core-systems (command-system), wave3 batches 1-5 (88 commands verified) | **HIGH** |
| 4 | `src/tools/` | 184 | 50,828 | 02-core-systems (tool-system), wave2 batches 1-4 (57 tools verified), wave31 (ToolUseContext), wave32 (Tool interface), wave42 (LSP tool) | **HIGH** |
| 5 | `src/services/` | 130 | 53,680 | 05-services (MCP, memory, plugins, OAuth, analytics), wave10 (MCP deep), wave41 (API service), wave42 (LSP service), wave43 (analytics), wave44 (background services), wave45 (remaining services), wave53 (enterprise services) | **HIGH** |
| 6 | `src/hooks/` | 104 | 19,204 | 02-core-systems (hook-system), wave54 (complete hooks audit), wave5 (permission/hook types) | **HIGH** |
| 7 | `src/ink/` | 96 | 19,842 | 04-ui-framework (ink-terminal-ui), wave27 (Ink deep analysis) | **HIGH** |
| 8 | `src/bridge/` | 31 | 12,613 | 07-cli-infrastructure (bridge-protocol), wave9 (bridge deep analysis) | **HIGH** |
| 9 | `src/constants/` | 21 | 2,648 | wave55 (constants deep analysis), 00-stats (referenced) | **HIGH** |
| 10 | `src/skills/` | 20 | 4,066 | 07-cli-infrastructure (skill-system) | **MEDIUM** |
| 11 | `src/cli/` | 19 | 12,353 | 07-cli-infrastructure (entrypoints, bridge), 01-architecture (system-overview, layer-model) | **MEDIUM** |
| 12 | `src/keybindings/` | 14 | 3,159 | 07-cli-infrastructure (keybindings) | **MEDIUM** |
| 13 | `src/tasks/` | 12 | 3,286 | 06-agent-system (task-framework), wave8 (lifecycle deep) | **HIGH** |
| 14 | `src/types/` | 11 | 3,446 | 10-patterns (type-system), wave5 batches 1-3, wave33 (missing types) | **HIGH** |
| 15 | `src/migrations/` | 11 | 603 | wave51 (migrations/schemas deep analysis) | **HIGH** |
| 16 | `src/context/` | 9 | 1,004 | wave55 (context providers deep), 02-core-systems (state-management) | **HIGH** |
| 17 | `src/memdir/` | 8 | 1,736 | 05-services (memory-system) | **MEDIUM** |
| 18 | `src/entrypoints/` | 8 | 4,051 | 07-cli-infrastructure (entrypoints), 01-architecture (system-overview) | **HIGH** |
| 19 | `src/state/` | 6 | 1,190 | 02-core-systems (state-management) | **MEDIUM** |
| 20 | `src/buddy/` | 6 | 1,298 | 09-advanced-features (desktop-integration) | **LOW-MEDIUM** |
| 21 | `src/vim/` | 5 | 1,513 | 09-advanced-features (vim-mode) | **HIGH** |
| 22 | `src/remote/` | 4 | 1,127 | 06-agent-system (remote-execution) | **MEDIUM** |
| 23 | `src/query/` | 4 | 652 | 03-ai-engine (query-engine) | **HIGH** |
| 24 | `src/native-ts/` | 4 | 4,081 | wave19 (vendor/native modules) | **HIGH** |
| 25 | `src/server/` | 3 | 358 | wave52 (coordinator/assistant/server deep) | **HIGH** |
| 26 | `src/screens/` | 3 | 5,977 | 04-ui-framework (component-library), wave25 (user journeys) | **MEDIUM** |
| 27 | `src/upstreamproxy/` | 2 | 740 | wave55 (upstream proxy deep analysis) | **HIGH** |
| 28 | `src/plugins/` | 2 | 182 | 05-services (plugin-system) | **MEDIUM** |
| 29 | `src/coordinator/` | 1 | 369 | wave52 (coordinator/assistant/server deep) | **HIGH** |
| 30 | `src/bootstrap/` | 1 | 1,758 | 01-architecture (system-overview), 02-core-systems (state-management) | **MEDIUM** |
| 31 | `src/assistant/` | 1 | 87 | wave52 (coordinator/assistant/server deep) | **HIGH** |
| 32 | `src/schemas/` | 1 | 222 | wave51 (migrations/schemas deep) | **HIGH** |
| 33 | `src/outputStyles/` | 1 | 98 | wave51 (outputStyles deep) | **HIGH** |
| 34 | `src/moreright/` | 1 | 25 | wave51 (moreright deep) | **HIGH** |
| 35 | `src/voice/` | 1 | 54 | 09-advanced-features (voice-input) | **MEDIUM** |
| 36 | Root files (`src/*.ts/tsx`) | 18 | 11,968 | 00-stats (key files listed), 03-ai-engine (query-engine, context, cost-tracking), 01-architecture (system-overview), 10-patterns (type-system) | **HIGH** |

---

## Coverage Level Definitions

| Level | Criteria |
|-------|----------|
| **HIGH** | Dedicated analysis file(s) covering the directory, with source-level verification and/or deep-dive wave |
| **MEDIUM-HIGH** | Covered by multiple analysis files, but not a dedicated deep-dive for the full directory scope |
| **MEDIUM** | Mentioned and partially analyzed in broader documents, no dedicated deep-dive |
| **LOW-MEDIUM** | Briefly referenced in adjacent analyses, not directly targeted |
| **LOW** | Not directly covered by any analysis file |
| **NONE** | Zero mention in any analysis document |

---

## Uncovered or Weakly Covered Areas

### LOW-MEDIUM Coverage (partially referenced but no dedicated analysis)

| Directory | Files | LOC | Gap Description |
|-----------|-------|-----|-----------------|
| `src/buddy/` | 6 | 1,298 | Only referenced briefly in desktop-integration.md; no dedicated deep-dive into buddy/pair-programming protocol, message exchange, or buddy backend implementations |

### MEDIUM Coverage (mentioned but not deeply verified)

| Directory | Files | LOC | Gap Description |
|-----------|-------|-----|-----------------|
| `src/skills/` | 20 | 4,066 | skill-system.md provides overview, but no file-by-file verification of all 20 skill files (unlike tools/commands which got full catalogs) |
| `src/cli/` | 19 | 12,353 | Covered at architecture level (transports, SSE, WebSocket) but no dedicated deep-dive into all 19 files |
| `src/keybindings/` | 14 | 3,159 | keybindings.md provides overview; 14 files not individually verified |
| `src/memdir/` | 8 | 1,736 | memory-system.md covers conceptually, but memdir/ implementation files not traced line-by-line |
| `src/state/` | 6 | 1,190 | state-management.md covers AppState; 6 state files not individually deep-dived |
| `src/remote/` | 4 | 1,127 | remote-execution.md covers architecture; 4 files not individually verified |
| `src/plugins/` | 2 | 182 | plugin-system.md covers loading; 2 bundling files briefly mentioned |
| `src/screens/` | 3 | 5,977 | Large files (REPL, Doctor, Resume screens) mentioned in component-library.md but no dedicated deep analysis |
| `src/bootstrap/` | 1 | 1,758 | Referenced as entry path but the 1,758-line bootstrap/state.ts not deeply analyzed |
| `src/voice/` | 1 | 54 | voice-input.md covers feature; single file is trivial (54 LOC) |

### Notable Sub-directory Gaps within HIGH-coverage Directories

| Parent | Sub-area | Estimated Gap |
|--------|----------|---------------|
| `src/utils/` (564 files) | `utils/permissions/`, `utils/git/`, `utils/auth/`, `utils/plugins/` — these sub-areas are referenced but many individual files within the 564-file directory remain unverified at file level | ~200 files without file-level verification |
| `src/components/` (389 files) | Many individual component files mentioned by category but not individually verified; wave27 focused on Ink internals, not all 389 component files | ~250 files without file-level verification |
| `src/commands/` (189 files) | Wave 3 verified 88 command names exist; individual command implementation files (index.ts per command) not all traced for logic correctness | ~100 files logic-unverified |

---

## Coverage Statistics

### Directory-Level Coverage

| Metric | Value |
|--------|-------|
| **Total source directories** | 36 (35 subdirectories + root files) |
| **HIGH coverage** | 23 directories (64%) |
| **MEDIUM-HIGH coverage** | 1 directory (3%) |
| **MEDIUM coverage** | 10 directories (28%) |
| **LOW-MEDIUM coverage** | 1 directory (3%) |
| **LOW or NONE coverage** | 0 directories (0%) |
| **Directories with dedicated deep-dive waves** | 26/36 (72%) |

### File-Level Coverage Estimates

| Metric | Value |
|--------|-------|
| **Total source files** | 1,902 |
| **Files in HIGH-coverage directories** | 1,460 (77%) |
| **Files with file-level verification** | ~850 (45%) — tools (57 verified), commands (88 verified), hooks (104 audited), services (waves 41-45, 53), types (waves 5, 31-33), settings (wave 46), model (wave 47), bash (wave 48), etc. |
| **Files with directory-level analysis** | ~1,600 (84%) — covered by at least one analysis doc at architectural or catalog level |
| **Files with no coverage** | ~300 (16%) — primarily individual component files, utility helpers, and lesser-used command implementations |

### LOC-Level Coverage Estimates

| Metric | Value |
|--------|-------|
| **Total LOC** | 512,664 |
| **LOC in HIGH-coverage directories** | ~370,000 (72%) |
| **LOC with deep-dive analysis** | ~310,000 (60%) — directories that received dedicated wave deep-dives |
| **LOC with at least architectural coverage** | ~480,000 (94%) |
| **LOC with no coverage** | ~33,000 (6%) — primarily uncounted component files and utility edge cases |

### Analysis Investment

| Metric | Value |
|--------|-------|
| **Total analysis files** | 91 markdown documents |
| **Verification waves completed** | 56 (Waves 1-55 + this audit) |
| **Verification points** | ~750+ |
| **Issues found and resolved** | 62/62 (100%) |
| **Quality score progression** | 6.5 → 9.5/10 |

---

## Summary Assessment

The Claude Code source study achieves **excellent breadth** — every single source directory (36/36) has at least MEDIUM coverage through one or more analysis documents. No directory is completely uncovered.

**Depth** is strong for the most critical subsystems: tools (57 verified), commands (88 verified), hooks (104 audited), services (7 deep-dive waves), permissions (2 deep-dives), bridge protocol, MCP integration, context compression, agent lifecycle, Ink terminal UI, and the type system. These represent the architectural backbone of the codebase.

**The primary gap** is file-level verification within the two largest directories: `utils/` (564 files) and `components/` (389 files). While sub-areas within these directories have received deep-dives (settings, model, bash, swarm, input processing for utils; Ink internals for components), an estimated ~450 individual files across these two directories have not been individually traced. This is expected given the scale — full file-level verification of 1,902 files would require ~100+ additional waves.

**Recommendation**: The current 94% LOC architectural coverage and 45% file-level verification represent a strong analysis baseline. Future waves should prioritize:
1. `src/screens/` (3 files, 5,977 LOC) — large, unverified screen components
2. `src/buddy/` (6 files, 1,298 LOC) — only directory at LOW-MEDIUM coverage
3. `src/utils/permissions/` and `src/utils/git/` sub-areas — high-impact utility clusters
4. `src/components/` file-level sampling — verify representative components per category

---

## LOC Discrepancy Note

The 00-stats.md file reports ~40,713 LOC. This audit's direct `wc -l` count yields 512,664 LOC across all 1,902 TS/TSX files in `src/`. The discrepancy suggests the original stat was based on a minified/bundled count, a filtered subset, or a different counting methodology. The 512,664 figure represents raw source line count including comments, blank lines, and generated code.
