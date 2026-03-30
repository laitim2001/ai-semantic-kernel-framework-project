# V9 Round 4: Full Semantic Coverage

> **Problem**: Round 3 AST scan covered 100% of files structurally, but only ~17 files have exact path references in V9 analysis. Semantic analysis (what code DOES, not just what structures exist) is limited to ~100-200 key files read by agents.
> **Constraint**: All 832 files are under 2000 lines → Read tool CAN fully read every file.
> **Goal**: Every file's SEMANTIC content (logic, patterns, TODOs, docstrings, issues) captured.

---

## Strategy: Enhanced Automated Extraction + Batch Semantic Verification

### Phase R4-A: Enhanced Content Extraction Script

Upgrade the AST scanner to extract SEMANTIC content from every file:
- Module/class/function docstrings (full text)
- All TODO, FIXME, HACK, XXX, STUB, DEPRECATED comments
- All string literals that look like error messages
- All decorator patterns (@router, @pytest.mark, @tool, etc.)
- Import dependency graph (who imports whom)
- Enum values (all choices)
- All hardcoded config values (magic numbers, default timeouts, etc.)

This produces a MUCH richer metadata file that captures semantic meaning.

### Phase R4-B: Batch File Reading + V9 Sync (832 files in 56 batches of 15)

> **CRITICAL REQUIREMENT**: Round 4 is NOT just "looking" at code. Each batch agent MUST:
> 1. Read every file COMPLETELY (Read tool, no offset/limit)
> 2. Produce per-file semantic summary into NEW `R4-semantic/` files
> 3. **UPDATE existing V9 analysis files** — fix errors, add missing content, sync data
> 4. **ADD new content** to V9 if files/features/issues were previously undocumented
>
> The output is BOTH new semantic summaries AND updates to existing V9 files.

Split ALL 832 files into batches of ~15 files each.
Each batch agent:
1. Reads every file in its batch COMPLETELY (Read tool, no offset/limit)
2. For each file produces a one-paragraph summary: what the file does, key patterns, notable issues
3. Compares against existing V9 layer/module files and **EDITS them** to fix errors or add missing info
4. Writes new per-file summaries to `R4-semantic/` directory

Group batches by module to maintain context:
- backend/src/api/v1/ (7 batches, ~105 files)
- backend/src/integrations/hybrid/ (5 batches, ~75 files)
- backend/src/integrations/agent_framework/ (4 batches, ~62 files)
- backend/src/integrations/claude_sdk/ (3 batches, ~39 files)
- backend/src/integrations/orchestration/ (3 batches, ~39 files)
- backend/src/integrations/mcp/ (3 batches, ~43 files)
- backend/src/integrations/ag_ui/ (2 batches, ~22 files)
- backend/src/integrations/remaining/ (4 batches, ~60 files)
- backend/src/domain/ (6 batches, ~86 files)
- backend/src/infrastructure+core/ (5 batches, ~76 files)
- frontend/src/ (14 batches, ~236 files)

Total: ~56 batches

### Phase R4-C: V9 Consolidation + Final Report

> All changes from R4-B MUST be persisted into V9 files before this phase.

Aggregate all batch findings into:
1. Per-file semantic summaries — permanent record in `R4-semantic/`
2. **V9 files updated** — layer-*.md, mod-*.md, features-*.md, issue-registry.md all synced
3. **00-stats.md updated** with Round 4 corrected numbers
4. **00-index.md updated** with new R4 files
5. New issues discovered → added to `05-issues/issue-registry.md`
6. Final 100% semantic coverage report with diff against Round 3

---

## Task Breakdown

| Task | Files | Batches | Output |
|------|-------|---------|--------|
| R4-A | 832 | 1 script | enhanced-metadata.json |
| R4-B-API | 105 | 7 | api-semantic-*.md |
| R4-B-HYBRID | 75 | 5 | hybrid-semantic-*.md |
| R4-B-MAF | 62 | 4 | maf-semantic-*.md |
| R4-B-CLAUDE | 39 | 3 | claude-semantic-*.md |
| R4-B-ORCH | 39 | 3 | orch-semantic-*.md |
| R4-B-MCP | 43 | 3 | mcp-semantic-*.md |
| R4-B-AGUI | 22 | 2 | agui-semantic-*.md |
| R4-B-REMAINING | 60 | 4 | remaining-semantic-*.md |
| R4-B-DOMAIN | 86 | 6 | domain-semantic-*.md |
| R4-B-INFRA | 76 | 5 | infra-semantic-*.md |
| R4-B-FRONTEND | 236 | 14 | frontend-semantic-*.md |
| R4-C | all | 1 | 00-r4-final-report.md |

---

## Execution Strategy

R4-A runs first (automated script, fast).
R4-B runs in waves of 8-10 agents per wave, ~6 waves total.
R4-C runs last.

Estimated output: ~60 semantic analysis files + 1 enhanced metadata JSON + 1 final report.
