# V9 Verification Pass Plan (Round 2)

> **Purpose**: Verify and correct V9 analysis by reading ALL 832 source files
> **Trigger**: Round 1 coverage audit found only 14% (121/832) files were actually read
> **Date**: 2026-03-29

---

## 1. Coverage Gap Summary (Round 1)

| Module | Total | Read | Missing | Coverage |
|--------|-------|------|---------|----------|
| backend/integrations | 340 | 67 | 273 | 19% |
| frontend/components | 128 | 7 | 121 | 5% |
| backend/api | 107 | 2 | 105 | 1% |
| backend/domain | 86 | 6 | 80 | 6% |
| backend/infrastructure | 42 | 3 | 39 | 7% |
| frontend/pages | 46 | 15 | 31 | 32% |
| backend/core | 33 | 6 | 27 | 18% |
| frontend/hooks | 25 | 8 | 17 | 32% |
| frontend/api+stores+types | 23 | 7 | 16 | 30% |
| **Total** | **832** | **121** | **715** | **14%** |

---

## 2. Verification Strategy

### Approach: Batch File Reading + Correction

For each batch of files:
1. **Read every file** — extract: class names, function signatures, LOC, imports
2. **Cross-reference** against existing V9 claims — verify counts, names, descriptions
3. **Document corrections** — what V9 got wrong, what was missed
4. **Update analysis** — amend existing V9 files or create correction addenda

### NOT Re-Writing V9 From Scratch
Round 2 is a **verification and correction** pass, not a rewrite. V9 documents remain as base; corrections are appended or specific claims are fixed.

---

## 3. Verification Tasks

### V-A: Backend API Layer (105 files) — CRITICAL
**Scope**: `backend/src/api/v1/` — every routes.py and schemas.py
**Goal**: Verify endpoint counts, route paths, schema classes against api-reference.md
**Method**: Read every route file, extract all @router decorators, compare with V9 api-reference
**Output**: `V9/09-api-reference/api-reference-corrections.md`

### V-B: Backend Integration Layer (273 files) — CRITICAL
**Scope**: All unread files in `backend/src/integrations/`
**Goal**: Verify class inventories, function signatures, module boundaries
**Method**: Read every unread .py file, extract exports, compare with layer analysis
**Batch strategy**:
- V-B1: hybrid/ (remaining ~60 files)
- V-B2: agent_framework/ (remaining ~40 files)
- V-B3: orchestration/ (remaining ~25 files)
- V-B4: claude_sdk/ (remaining ~25 files)
- V-B5: mcp/ (remaining ~30 files)
- V-B6: ag_ui/ + remaining modules (~93 files)
**Output**: Corrections to `01-architecture/layer-*.md` and `02-modules/mod-*.md`

### V-C: Backend Domain Layer (80 files) — HIGH
**Scope**: All unread files in `backend/src/domain/`
**Goal**: Verify service APIs, model schemas, InMemory status
**Method**: Read every unread .py file
**Batch strategy**:
- V-C1: sessions/ (remaining ~20 files)
- V-C2: orchestration/ (remaining ~15 files)
- V-C3: all other domain modules (~45 files)
**Output**: Corrections to `01-architecture/layer-10-domain.md`

### V-D: Backend Infrastructure + Core (66 files) — HIGH
**Scope**: All unread files in `backend/src/infrastructure/` + `backend/src/core/`
**Goal**: Verify DB models, storage backends, security implementations
**Method**: Read every unread .py file
**Output**: Corrections to `01-architecture/layer-11-infrastructure.md`

### V-E: Frontend Components (121 files) — HIGH
**Scope**: All unread .tsx/.ts in `frontend/src/components/`
**Goal**: Verify component props, rendering patterns, hook usage
**Batch strategy**:
- V-E1: unified-chat/ remaining (~20 files)
- V-E2: ag-ui/ remaining (~12 files)
- V-E3: DevUI/ remaining (~10 files)
- V-E4: workflow-editor/ + ui/ + layout/ + shared/ (~25 files)
**Output**: Corrections to `01-architecture/layer-01-frontend.md`

### V-F: Frontend Pages + Hooks + API (64 files) — MEDIUM
**Scope**: All unread pages/, hooks/, api/, stores/, types/
**Goal**: Verify route map, hook APIs, store shapes
**Output**: Corrections to `01-architecture/layer-01-frontend.md` and `02-modules/mod-frontend.md`

### V-G: Cross-Reference Validation — FINAL
**Scope**: All V9 documents
**Goal**: Verify all quantitative claims (file counts, LOC, class counts, endpoint counts)
**Method**: Automated counting vs V9 stated numbers
**Output**: `V9/00-verification-report.md` — summary of all corrections made

---

## 4. Execution Order

```
V-A (API, 105 files) ──┐
V-B (Integrations, 273) ├──→ V-G (Cross-Reference)
V-C (Domain, 80)       │
V-D (Infra+Core, 66)   │
V-E (FE Components, 121)│
V-F (FE Pages+Hooks, 64)┘
```

V-A through V-F can run in parallel.
V-G runs after all others complete.

### Estimated Output
- 6-8 correction/addendum files
- 1 verification summary report
- Updates to existing V9 files where claims were wrong

---

## 5. Quality Gates

Each verification batch must:
- [ ] Read 100% of files in scope (not sampling)
- [ ] Extract all class/function names per file
- [ ] Compare against V9 stated inventory
- [ ] Flag any discrepancy with: V9 claim vs actual finding
- [ ] Produce correction with file:line evidence
