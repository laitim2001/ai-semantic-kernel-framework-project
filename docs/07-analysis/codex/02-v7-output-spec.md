# V7-Aligned Output Specification (Codex)

> Version: 1.0
> Date: 2026-02-11
> Purpose: lock the target format and quality bar before full deep analysis

---

## 1. Target Documents

1. `03-architecture-deep-analysis.md`
2. `04-features-mapping-deep-analysis.md`

Both must be structurally compatible with:

1. `docs/07-analysis/MAF-Claude-Hybrid-Architecture-V7.md`
2. `docs/07-analysis/MAF-Features-Architecture-Mapping-V7.md`

---

## 2. Required Section Skeleton

### 2.1 Architecture report (V7-aligned)

1. Metadata block (version/date/status/scope/verification method)
2. Implementation status overview
3. Layer-by-layer implementation table
4. Known issues (severity-ranked)
5. Executive summary
6. Platform positioning and value proposition
7. End-to-end execution flow (text diagram + path verification)
8. 11-layer architecture deep dive
9. Parallelism/concurrency design review
10. Security/governance model review
11. Validation method and evidence quality notes

### 2.2 Feature mapping report (V7-aligned)

1. Metadata block (same style)
2. Overall implementation status
3. Category statistics summary
4. Version delta notes
5. Executive summary
6. Layer map and feature category map
7. Full feature status quick table
8. Feature-by-feature evidence mapping
9. Gaps and non-functional constraints
10. Remediation roadmap by priority

---

## 3. Status Taxonomy

Use this exact status vocabulary:

1. `REAL`: implemented and code-path validated
2. `PARTIAL`: core exists but with fallback/hard-coded constraints
3. `STUB`: API/signature exists but logic is placeholder
4. `EMPTY`: shell module/directory with no effective implementation
5. `MOCK-FALLBACK`: runtime can fall back to mock behavior in non-test path

---

## 4. Evidence Requirements

Every critical claim must include one or more of:

1. file path evidence
2. measured metric evidence
3. code-path evidence (entry -> handler -> service -> integration)
4. cross-check evidence (second method validates first method)

---

## 5. Quality Gates (must pass before finalizing)

1. No contradictory numbers across codex documents
2. Top-level architecture totals reconcile with module subtotals
3. Feature status counts reconcile with category summary
4. Risk findings include severity + impact + evidence path
5. All referenced paths exist in current repository

---

## 6. Improvements Beyond V7

Codex outputs should improve V7 in these areas:

1. Explicit status taxonomy (`REAL/PARTIAL/STUB/EMPTY/MOCK-FALLBACK`)
2. Reproducibility notes for each headline metric
3. Stronger consistency checks between architecture and feature mapping docs
4. Clear acceptance gates for declaring analysis complete
