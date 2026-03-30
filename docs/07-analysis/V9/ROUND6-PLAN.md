# V9 Round 6: Cross-Validation — V9 Documents vs JSON Ground Truth

> **Goal**: Ensure EVERY claim in EVERY V9 markdown file is verified against R5 JSON ground truth.
> **Method**: Write a comprehensive Python script that reads ALL V9 .md files, extracts every
>   quantitative and structural claim, then cross-validates against the 8 R5 JSON files.
> **Output**: Per-file validation report + auto-patched V9 files where discrepancies found.

---

## What R5 Proved

R5 produced 8 JSON files that are the **ground truth** (AST-extracted, 100% file coverage):
- `r5-classes.json`: 2,507 classes, 6,286 methods
- `r5-routes.json`: 588 endpoints
- `r5-enums.json`: 339 enums, 1,844 values
- `r5-schemas.json`: 691 schemas, 3,766 fields
- `r5-imports.json`: 27 modules, 121 edges, 11 circular deps
- `r5-frontend.json`: 261 components, 418 interfaces, 120 props
- `backend-metadata.json`: 793 files, 273,345 LOC
- `frontend-metadata.json`: 236 files, 54,238 LOC

## What Round 6 Does

### R6-A: Comprehensive V9 Claim Extractor Script

A Python script that:
1. Reads EVERY .md file under `docs/07-analysis/V9/` (excluding JSON, R4-semantic/, verification files)
2. Extracts ALL claims: numbers (LOC, file counts, class counts), class names mentioned, endpoint paths mentioned, enum names mentioned
3. Outputs `r6-v9-claims.json` — structured catalog of every claim in every V9 file

### R6-B: Cross-Validation Script

A Python script that:
1. Loads `r6-v9-claims.json` (from R6-A)
2. Loads all 8 R5 JSON ground truth files
3. For EVERY claim, validates against ground truth:
   - Numeric claims: exact or within tolerance → PASS/FAIL
   - Class names: exists in r5-classes.json → PASS/MISSING
   - Endpoint paths: exists in r5-routes.json → PASS/MISSING
   - Enum names: exists in r5-enums.json → PASS/MISSING
4. Outputs `r6-validation-report.json` + `r6-validation-report.md`
   - Per-V9-file: PASS count, FAIL count, accuracy %
   - Overall: total claims verified, total passes, total fails

### R6-C: Auto-Correction Script

A Python script that:
1. Reads `r6-validation-report.json`
2. For each FAIL: generates the correction (old value → new value from ground truth)
3. Applies corrections to V9 .md files using string replacement
4. Outputs `r6-corrections-applied.md` — log of all changes made

### R6-D: Final Commit + Report

Commit all changes + produce `00-r6-final-report.md` with:
- Per-file validation scores
- Total accuracy before and after corrections
- What was fixed
- What remains as known V9 limitations

---

## Task Breakdown

| Task | Method | Input | Output |
|------|--------|-------|--------|
| R6-A | Python script | V9 .md files | r6-v9-claims.json |
| R6-B | Python script | r6-v9-claims.json + R5 JSONs | r6-validation-report.md |
| R6-C | Python script | r6-validation-report.json + V9 .md files | Corrected .md files |
| R6-D | git commit | all | 00-r6-final-report.md |

All sequential. R6-A → R6-B → R6-C → R6-D.
