# V9 Round 3: Programmatic Full-Coverage Verification

> **Problem**: Round 1 read 14% of files. Round 2 claimed 100% but audit shows only 54% have per-file evidence.
> **Root Cause**: Agent context windows physically cannot hold 832 files. Manual reading approach is fundamentally limited.
> **Solution**: Automated programmatic extraction + targeted manual verification of gaps.

---

## Strategy: Two-Phase Approach

### Phase R3-A: Automated Metadata Extraction (100% coverage guaranteed)

Write and run Python/Shell scripts that programmatically extract from EVERY file:

**For Python files (609 files)**:
- Script uses `ast` module to parse each .py file
- Extracts: file path, LOC, all class names (with base classes), all function/method names, all imports
- Outputs structured JSON/CSV

**For TypeScript files (223 files)**:
- Script uses regex to parse each .ts/.tsx file
- Extracts: file path, LOC, all export names, all interface/type names, all import statements
- Outputs structured JSON/CSV

**Output**: Two complete metadata files:
- `V9/backend-metadata.json` — 609 entries, every Python file
- `V9/frontend-metadata.json` — 223 entries, every TS file

This is NOT reading by Agent — it's automated AST/regex extraction that physically touches every file.

### Phase R3-B: Gap-Targeted Manual Verification

Using the metadata from R3-A, identify the ~382 files that Round 2 missed:
1. Compare metadata JSON against all V9 documents
2. For files with NO V9 coverage: batch-read and document
3. Focus on the 4 weak verification areas:
   - API routes (60 files with 0 per-file evidence)
   - Infrastructure (65 files with 0 per-file evidence)
   - Domain non-sessions (57 files with module-level only)
   - Frontend pages+hooks (66 files with partial evidence)

### Phase R3-C: Corrections and Final Report

1. Cross-reference R3-A metadata against ALL V9 quantitative claims
2. Produce automated diff: V9 claimed LOC vs actual LOC per file
3. Update 00-verification-report.md with R3 findings
4. Final coverage: 832/832 with programmatic evidence

---

## Task Breakdown

| Task | Method | Files | Output |
|------|--------|-------|--------|
| R3-A1 | Python AST script | 609 .py | backend-metadata.json |
| R3-A2 | TypeScript regex script | 223 .ts/.tsx | frontend-metadata.json |
| R3-B1 | Manual read: API routes | ~60 files | api-r3-verification.md |
| R3-B2 | Manual read: Infrastructure+Core | ~65 files | infra-r3-verification.md |
| R3-B3 | Manual read: Domain (non-sessions) | ~57 files | domain-r3-verification.md |
| R3-B4 | Manual read: FE pages+hooks | ~66 files | frontend-r3-verification.md |
| R3-C | Automated cross-reference | all metadata | 00-r3-final-report.md |

R3-A1 and R3-A2 run first (automated, fast).
R3-B1-B4 run in parallel after R3-A.
R3-C runs last.
