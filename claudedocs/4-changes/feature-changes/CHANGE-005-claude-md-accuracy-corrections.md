# CHANGE-005: CLAUDE.md Accuracy Corrections

## Summary

Comprehensive accuracy corrections for all 17 CLAUDE.md files across the project. Verified every file against actual codebase on 2026-02-09. Fixes file count discrepancies, endpoint count errors, and updates 3 outdated files that were missed in the previous audit.

## Date

2026-02-09

## Sprint / Phase

Maintenance - Post Phase 29 Documentation Audit

## Type

Documentation Correction

## Status

✅ Completed

---

## Scope Overview

| Priority | Files | Issue Type |
|----------|-------|------------|
| CRITICAL | 1 | Self-contradicting file counts |
| HIGH | 2 | File count off by 46%+ |
| MEDIUM | 5 | Endpoint/file counts off by 10-50% |
| LOW | 4 | Minor off-by-one or off-by-three |
| OUTDATED | 3 | Not updated since 2026-01-23 |
| NO CHANGE | 5 | Already accurate |

---

## Priority 1: CRITICAL

### 1.1 `backend/src/integrations/mcp/CLAUDE.md`

| Field | Current Value | Correct Value |
|-------|---------------|---------------|
| Header file count | "45 Python files" | **43 Python files** |
| Body file count | "12 files" | **43 files** |

**Problem**: Header says 45, body says 12, actual is 43. Self-contradicting document.

**Root Cause**: Original doc counted only core+registry+security+1-per-server = 12; header was copy-pasted from parent index with wrong number.

**Fix**: Unify to 43 files. Add breakdown: core(4) + registry(2) + security(2) + 5 servers(~7 each) = 43.

---

## Priority 2: HIGH

### 2.1 `backend/src/integrations/CLAUDE.md` (parent index)

| Field | Current Value | Correct Value |
|-------|---------------|---------------|
| Total modules | 15 | **16** |
| Total .py files | ~216 | **~315** |
| mcp file count | 12 | **43** |
| hybrid file count | 25 | **60** |
| orchestration file count | 21 | **39** |

**Root Cause**: Initial audit undercounted `__init__.py`, `__main__.py`, and sub-handler files.

### 2.2 `backend/CLAUDE.md`

| Field | Current Value | Correct Value |
|-------|---------------|---------------|
| Integration .py files total | 216 | **~315** |
| Performance subsystem files | 8 | **9** |

**Root Cause**: Same undercounting issue as parent index. Performance missed `__init__.py`.

---

## Priority 3: MEDIUM

### 3.1 `CLAUDE.md` (root)

| Field | Current Value | Correct Value |
|-------|---------------|---------------|
| Integration modules | 15 | **16** |
| Domain modules | 19 | **20** |

**Note**: The text body already lists all 16/20 modules correctly; only the count number is wrong.

### 3.2 `backend/src/api/CLAUDE.md`

| Field | Current Value | Correct Value |
|-------|---------------|---------------|
| Route module directories | 39 | **41** |
| auth endpoints | 4 | **7** |
| ag_ui endpoints | 25 | **29** |

**Root Cause**: 2 new route directories added after audit; endpoint counts from quick estimate, not actual `@router` decorator count.

### 3.3 `backend/src/integrations/orchestration/CLAUDE.md`

| Field | Current Value | Correct Value |
|-------|---------------|---------------|
| File count | 21 | **39** |

**Root Cause**: Counted major files only, missed `__init__.py` files (+8), sub-handler files (+4), and helper files in each subdirectory.

### 3.4 `frontend/CLAUDE.md`

| Field | Current Value | Correct Value |
|-------|---------------|---------------|
| Component file count | ~127 | **~115** |
| Agent-swarm component count | 17 | **15 components + 4 hooks** |

**Root Cause**: Original count likely included test files (13) and type definition files (2).

### 3.5 `backend/src/integrations/claude_sdk/CLAUDE.md`

| Field | Current Value | Correct Value |
|-------|---------------|---------------|
| File count | 44 | **47** |

**Root Cause**: Missed 3 `__init__.py` files in subdirectories.

---

## Priority 4: LOW (Off-by-one, optional)

| File | Field | Current | Correct |
|------|-------|---------|---------|
| `integrations/CLAUDE.md` | module count | 15 | 16 |
| `CLAUDE.md` (root) | domain modules | 19 | 20 |
| `backend/CLAUDE.md` | performance files | 8 | 9 |
| `claude_sdk/CLAUDE.md` | file count | 44 | 47 |

---

## Priority 5: OUTDATED FILES (Need Phase 28-29 content)

### 5.1 `backend/src/integrations/agent_framework/CLAUDE.md`

- **Last Updated**: 2026-01-23 (17 days old)
- **Missing**: No Phase 29 swarm integration notes
- **Content Accuracy**: Core rules and adapter patterns still valid
- **Action**: Update date, add brief Phase 29 integration note

### 5.2 `backend/src/api/v1/sessions/CLAUDE.md`

- **Last Updated**: 2026-01-23 (17 days old)
- **Missing**: Phase 28 orchestration integration, Phase 29 swarm session endpoints
- **Content Accuracy**: Existing endpoints still valid, but incomplete
- **Action**: Add Phase 28-29 integration sections

### 5.3 `backend/src/domain/sessions/CLAUDE.md`

- **Last Updated**: 2026-01-23 (17 days old)
- **Missing**: Orchestration layer integration, swarm session lifecycle
- **Content Accuracy**: 33 files count still valid, state machine still accurate
- **Action**: Add Phase 28-29 integration sections

---

## Files Requiring NO Changes (Verified Accurate)

| File | Accuracy | Notes |
|------|----------|-------|
| `backend/src/infrastructure/CLAUDE.md` | 100% | messaging STUB, storage EMPTY both correct |
| `backend/src/integrations/hybrid/CLAUDE.md` | 100% | 60 files, all LOC exact match |
| `backend/src/integrations/swarm/CLAUDE.md` | 100% | 7 files, all LOC exact match |
| `claudedocs/CLAUDE.md` | 100% | Phase 29, 2379 pts all correct |
| `backend/src/domain/CLAUDE.md` | 95% | All 20 modules spot-checked, file counts match |

---

## Execution Plan

### Phase A: Critical + High (must-fix)
1. Fix `mcp/CLAUDE.md` header/body contradiction → 43 files
2. Fix `integrations/CLAUDE.md` parent index → 16 modules, ~315 files
3. Fix `backend/CLAUDE.md` integration total → ~315 files

### Phase B: Medium (should-fix)
4. Fix `CLAUDE.md` (root) module counts → 16 integrations, 20 domain
5. Fix `api/CLAUDE.md` endpoint counts → auth 7, ag_ui 29, 41 dirs
6. Fix `orchestration/CLAUDE.md` file count → 39 files
7. Fix `frontend/CLAUDE.md` component counts → ~115, swarm 15+4
8. Fix `claude_sdk/CLAUDE.md` file count → 47 files

### Phase C: Outdated files (update)
9. Update `agent_framework/CLAUDE.md` → add Phase 29 note, update date
10. Update `api/v1/sessions/CLAUDE.md` → add Phase 28-29 integration
11. Update `domain/sessions/CLAUDE.md` → add Phase 28-29 integration

### Phase D: Memory update
12. Update auto memory `MEMORY.md` with final accurate counts

---

## Estimated Impact

- **Files Modified**: 12 CLAUDE.md files
- **Files Unchanged**: 5 CLAUDE.md files (already accurate)
- **Risk**: LOW - documentation-only changes, no code modifications
- **Estimated Effort**: ~30 minutes for all phases

---

## Verification Method

Each correction was verified by:
1. `Glob` to count actual files/directories
2. `Grep` to count `@router` decorators for endpoints
3. `Read` to verify specific LOC claims
4. Cross-referencing between parent and child CLAUDE.md files

4 parallel verification agents were used, covering:
- Agent 1: Root + Backend CLAUDE.md
- Agent 2: API + Domain + Infrastructure CLAUDE.md
- Agent 3: 6 Integrations CLAUDE.md files
- Agent 4: Frontend + Claudedocs + 3 older files

---

**Prepared By**: AI Assistant (Claude)
**Approval Required**: Yes - pending user confirmation before execution
