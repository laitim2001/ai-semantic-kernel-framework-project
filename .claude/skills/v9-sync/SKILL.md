---
name: v9-sync
description: AI-driven V9 codebase analysis sync — detects sprint/phase changes and semantically updates V9 analysis files
trigger: /v9-sync
---

# V9 Sync - AI-Driven Codebase Analysis Synchronization

Detect what source code changed since last V9 sync, AI reads the affected source code, and semantically updates the corresponding V9 analysis files to maintain accuracy.

## Invocation Modes

| Command | Behavior |
|---------|----------|
| `/v9-sync` | Full sync: detect + map + read source + update V9 files |
| `/v9-sync --report-only` | Detection only: show impact report without modifying V9 files |
| `/v9-sync --file <layer-name>` | Target a specific V9 file (e.g., `--file layer-02`, `--file issue-registry`) |
| `/v9-sync --stats-only` | Update only `00-stats.md` numbers (file counts, LOC, endpoints) |

---

## Execution Workflow

### Step 1: Scope Detection

Determine what source code has changed since the last sync.

```
1. Read: docs/07-analysis/V9/_verification/v9-sync-state.json
   → Extract: last_sync_commit, last_sync_date, last_sync_phase, last_sync_sprint

2. Bash: git diff --stat <last_sync_commit>..HEAD -- backend/src/ frontend/src/ backend/tests/
   → List of changed source files with line counts

3. Bash: git log --oneline <last_sync_commit>..HEAD
   → Commit messages for semantic context (what was the intent of each change?)

4. Bash: git diff --stat <last_sync_commit>..HEAD -- backend/src/ | wc -l
   → Quick count of changed files
```

**AI Analysis at this step**:
- Categorize changes: new module? new endpoints? bug fix? refactoring? new tests?
- Identify the scale: minor (< 10 files) vs moderate (10-30) vs major (30+)
- If `--report-only` mode AND zero changed files: report "V9 is up-to-date" and stop

**If no changes detected**: Report "V9 is up-to-date, last synced at Sprint {N}" and stop.

### Step 2: Impact Mapping

Map changed directories to affected V9 files.

#### Directory-to-V9 Mapping

| Changed Directory | Primary V9 File | Secondary V9 Files |
|---|---|---|
| `backend/src/api/v1/` | `01-architecture/layer-02-api-gateway.md` | `09-api-reference/`, `00-stats.md` |
| `backend/src/integrations/agent_framework/` | `01-architecture/layer-06-maf-builders.md` | `02-modules/`, `06-cross-cutting/` |
| `backend/src/integrations/claude_sdk/` | `01-architecture/layer-07-claude-sdk.md` | `02-modules/` |
| `backend/src/integrations/hybrid/` | `01-architecture/layer-05-orchestration.md` | `02-modules/` |
| `backend/src/integrations/orchestration/` | `01-architecture/layer-04-routing.md` | `02-modules/` |
| `backend/src/integrations/mcp/` | `01-architecture/layer-08-mcp-tools.md` | `02-modules/` |
| `backend/src/integrations/swarm/` | `01-architecture/layer-09-integrations.md` | `02-modules/` |
| `backend/src/integrations/a2a/` | `01-architecture/layer-09-integrations.md` | `02-modules/` |
| `backend/src/integrations/memory/` | `01-architecture/layer-09-integrations.md` | `06-cross-cutting/memory-architecture.md` |
| `backend/src/integrations/patrol/` | `01-architecture/layer-09-integrations.md` | `02-modules/` |
| `backend/src/integrations/correlation/` | `01-architecture/layer-09-integrations.md` | `02-modules/` |
| `backend/src/integrations/rootcause/` | `01-architecture/layer-09-integrations.md` | `02-modules/` |
| `backend/src/integrations/audit/` | `01-architecture/layer-09-integrations.md` | `02-modules/` |
| `backend/src/integrations/learning/` | `01-architecture/layer-09-integrations.md` | `02-modules/` |
| `backend/src/integrations/llm/` | `01-architecture/layer-09-integrations.md` | `02-modules/` |
| `backend/src/integrations/ag_ui/` | `01-architecture/layer-03-ag-ui.md` | `02-modules/` |
| `backend/src/domain/` | `01-architecture/layer-10-domain.md` | `08-data-model/` |
| `backend/src/infrastructure/` | `01-architecture/layer-11-infrastructure.md` | `08-data-model/`, `11-config-deploy/` |
| `backend/src/core/` | `01-architecture/layer-11-infrastructure.md` | `06-cross-cutting/` |
| `frontend/src/` | `01-architecture/layer-01-frontend.md` | — |
| `frontend/src/components/unified-chat/agent-swarm/` | `01-architecture/layer-01-frontend.md` | `01-architecture/layer-09-integrations.md` |
| `backend/tests/` | `12-testing/testing-landscape.md` | — |

#### Always-Check Files

These V9 files should always be checked regardless of which directories changed:

| V9 File | Check Condition |
|---------|----------------|
| `00-stats.md` | Any source file added or deleted |
| `05-issues/issue-registry.md` | Commit messages contain "fix", "resolve", "close", issue IDs (C-01, H-03, etc.) |
| `13-mock-real/mock-real-map.md` | Any file changed in integrations/ that was previously flagged as mock/stub |
| `06-cross-cutting/enum-registry.md` | Any new enum class detected in changed files |

**Output**: Present the impact map as a table to the user:

```markdown
## V9 Impact Report — Sprint {N} → Sprint {M}

| # | V9 File | Reason | Priority |
|---|---------|--------|----------|
| 1 | `00-stats.md` | 5 new .py files detected | HIGH |
| 2 | `layer-09-integrations.md` | 3 files changed in swarm/ | MEDIUM |
| 3 | `issue-registry.md` | Commit "fix(swarm): resolve C-12" | HIGH |
```

**If `--report-only` mode**: Present the report and stop here.

**Otherwise**: Ask user to confirm which V9 files to update (default: all flagged files).

### Step 3: AI Source Code Reading + V9 Update

For each confirmed V9 file, perform AI-driven semantic sync:

#### 3a. Read Current State

```
1. Read: The V9 analysis file (e.g., docs/07-analysis/V9/01-architecture/layer-09-integrations.md)
2. Read: Each changed source file in the affected directory
   - For small changes (< 5 files): Read all changed files completely
   - For large changes (> 5 files): Read new files completely, read modified files with focus on changed sections
```

#### 3b. Semantic Comparison

AI compares V9 content against actual source code:

| V9 Content Type | How to Verify | Update Action |
|-----------------|--------------|---------------|
| **File counts** | Count actual files in directory | Update number |
| **LOC** | Rough estimate from file sizes | Update number |
| **Class inventory tables** | Check if all classes listed exist, check for unlisted new classes | Add/remove rows |
| **Function signatures** | Read actual function definitions | Fix parameter lists, return types |
| **Behavioral descriptions** | Read function body, understand logic | Update description if behavior changed |
| **Import chains** | Read import statements | Update dependency descriptions |
| **Enum values** | Read actual enum definitions | Add new values, remove deleted ones |
| **Endpoint lists** | Read router decorators | Add new endpoints, update paths |
| **Issue status** | Check if the fix is present in source | Mark as FIXED with evidence |
| **Mock vs Real status** | Check if implementation is real or stub | Update maturity map |

#### 3c. Apply Updates

For each V9 file:
1. Make the edits using the Edit tool
2. Show the user what was changed (brief summary, not full diff)
3. Proceed to next file

#### Update Principles (CRITICAL)

- **Conservative**: If unsure whether a description is still accurate, DO NOT change it. Flag it for manual review instead.
- **Evidence-based**: Every change must cite the source file and line that proves the update is correct.
- **Preserve quality**: V9 was verified at 9.2/10. Updates must maintain or improve this quality. Never introduce speculative content.
- **No fabrication**: Never invent class names, function names, enum values, or behavioral descriptions. Only write what is confirmed by reading actual source code.
- **Cascade awareness**: If updating a number in one file, check if the same number appears in `00-stats.md` or other files and update those too.

### Step 4: Stats Cascade Verification

After all individual V9 files are updated:

```
1. Read: docs/07-analysis/V9/00-stats.md
2. Verify: All layer-level file counts sum to the total
3. Verify: All layer-level LOC sums to the total
4. Verify: Endpoint count matches api-reference catalog
5. Fix: Any cascade inconsistencies
```

If `00-index.md` needs updating (new V9 files added, which is rare):
```
1. Read: docs/07-analysis/V9/00-index.md
2. Add: New file entries to the appropriate category table
3. Update: Statistics Summary section
```

### Step 5: Finalize + Log

#### 5a. Update Sync State

```
1. Read: docs/07-analysis/V9/_verification/v9-sync-state.json
2. Update:
   - last_sync_commit → current HEAD commit hash
   - last_sync_date → today's date
   - last_sync_phase → current phase number
   - last_sync_sprint → current sprint number
   - total_sync_count → increment by 1
   - per_file_last_updated → update dates for files that were changed
3. Write: the updated JSON
```

#### 5b. Append Sync Log Entry

```
Append to: docs/07-analysis/V9/_verification/v9-sync-log.md

## Sync #{N} — Sprint {X} (Phase {Y}), {YYYY-MM-DD}

- **Commit range**: {old_commit}..{new_commit}
- **Changed source files**: {count} files across {dirs} directories
- **V9 files updated**: {list of updated V9 files}
- **Key changes**:
  - {bullet summary of each significant update}
- **Flagged for review**: {any items the AI was unsure about}
- **Quality assessment**: {AI's confidence in the updates}
```

#### 5c. Present Summary

```markdown
## V9 Sync Complete

| Item | Value |
|------|-------|
| Sprint | {N} → {M} |
| Source files changed | {count} |
| V9 files updated | {count} |
| Sync duration | {time} |

### Changes Made
{1-2 sentence summary per V9 file updated}

### Flagged for Manual Review
{Any items where AI was not confident}

### Next Steps
- Review flagged items if any
- Commit V9 updates: `git add docs/07-analysis/V9/ && git commit -m "docs(v9): sync V9 analysis for Sprint {M}"`
```

---

## Scope Control

### `--file <name>` Mode

When targeting a specific V9 file:
- Skip Step 1-2 (no need for full scope detection)
- Go directly to Step 3 for the specified file
- Still perform Step 4 cascade check and Step 5 logging

**Name matching**: The `<name>` argument matches against V9 filenames loosely:
- `layer-02` → `01-architecture/layer-02-api-gateway.md`
- `issue` or `issues` → `05-issues/issue-registry.md`
- `stats` → `00-stats.md`
- `api-ref` → `09-api-reference/api-reference.md`
- `mock` → `13-mock-real/mock-real-map.md`
- `enum` → `06-cross-cutting/enum-registry.md`
- `testing` → `12-testing/testing-landscape.md`

### `--stats-only` Mode

Quick numbers-only update:
- Run git diff to count new/deleted files
- Count actual files per directory using Glob
- Update `00-stats.md` numbers only
- Skip all semantic analysis
- Log as "stats-only sync" in sync log

---

## Important Rules

- **Language**: V9 analysis files are written in **English**. User-facing summaries in **Traditional Chinese**.
- **Confirmation**: Always present the impact map to the user before making changes. Never modify V9 files without user confirmation.
- **Quality preservation**: V9 was verified through 130 waves at 9.2/10 quality. The sync must not degrade this quality. When in doubt, flag for review rather than making a potentially incorrect change.
- **No speculative content**: Only update V9 based on what is actually confirmed in the source code. Do not add future plans, assumptions, or speculations.
- **Cascade consistency**: When updating a number (file count, LOC, endpoint count), always check if the same number appears in `00-stats.md` and update both locations.
- **Git awareness**: The sync relies on `v9-sync-state.json` for the baseline commit. If this file is missing or corrupted, fall back to scanning git log for the last V9-related commit.
