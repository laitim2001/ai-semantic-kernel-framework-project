# Day-0 Plan-vs-Repo Verify — full prong procedures (Step 2.5)

**Purpose**: Full procedures for the mandatory Day-0 three-prong (+2.5) plan-vs-repo grep verify — prong steps, drift-class grep tables, ROI evidence, worked examples. The trigger + summary live in `.claude/rules/sprint-workflow.md` §Step 2.5 (always-loaded); this file is Read on demand at every Day 0.
**Category / Scope**: Development Process / on-demand rule (REFACTOR-011)
**Created**: 2026-07-14 (REFACTOR-011; content dates to Sprint 55.3+ promotions)
**Last Modified**: 2026-07-14
**Status**: Active

> **Modification History**
> - 2026-07-14: REFACTOR-011 — extracted verbatim from sprint-workflow.md §Step 2.5 (always-loaded slimming)

**Trigger（什麼時候 Read）**: 每個 sprint 的 Day 0 — plan/checklist 起草後、Day 1 code 開始前（`sprint-workflow.md` §Step 2.5 強制）。

**回寫位置**: drift findings → progress.md Day 0 entry（格式 + go/no-go 門檻仍在 sprint-workflow.md §Step 2.5，未搬移）。

---

## Required actions (Day 0, before Day 1 code)

The verify is a **three-prong grep pass** (+ optional Prong 2.5 sub-prong for frontend page sprints); all prongs are mandatory when applicable (Prong 2.5 only when sprint involves frontend page re-point / restructure with existing child-component tree; Prong 3 only when sprint touches DB schema / migration / ORM models):

### Prong 1 — Path Verify (AD-Plan-2 from Sprint 55.3)

Every file path mentioned in plan §File Change List or §Technical Spec → `Glob` or `ls` to confirm exists / does not exist as expected.

- New files (creates): `Glob("path/to/new_file.py")` returns 0 results
- Edited files (edits): `Glob("path/to/existing.py")` returns 1 result
- DB tables: check `infrastructure/db/models/*.py` + `alembic/versions/*.py`
- Fixture paths: check `tests/**/conftest.py`
- Imports / re-exports: confirm package-level `__init__.py` if plan asserts exposure
- Public ABC methods: read the actual ABC file to confirm signature
- Test-infra files (pytest markers, fixtures, e2e specs) cited in plan §Technical Spec / §Acceptance — Glob-verify they exist, NOT just product files. Sprint 57.66 D-DAY0: a phantom `test_chat_e2e_real_llm.py` + `real_llm` marker propagated across 3 plans before a Prong-1 sweep caught they never existed (`AD-Day0-Prong1-TestInfra-File-Verify`).

### Prong 2 — Content Verify (AD-Plan-3 promoted Sprint 55.6)

Every plan §Technical Spec / §Background factual claim about existing code → **Grep** for the asserted symbol/pattern in real source. Path-verify alone (Prong 1) is **insufficient**: the file exists, but its body may have diverged from the plan's claim.

Common drift classes and matching grep query patterns:

| Drift class | Plan claim pattern | Grep verify pattern |
|-------------|--------------------|---------------------|
| **Claimed-but-unwired entry points** | "X is dead state" / "Y attribute is unused" | `grep -n "self\._{attribute}\b" {target_file}` — count call sites vs assignments (≥1 assignment / 0 call → confirmed dead) |
| **Claimed-but-missing imports** | "Z is publicly re-exported" / "consumer uses A" | `grep -rn "import {symbol}\|from .* import .*{symbol}" {target_dir}` — confirm import sites |
| **Claimed-but-renamed symbols** | "B was renamed to C" / "D class extends E" | `grep -rn "{old_name}\|{new_name}\|class .* {parent}" {target_dir}` — detect rename / inheritance drift |
| **Claimed-but-non-existent ABCs** | "extend ABC F" / "add G enum case" | `grep -rn "class F\|class G\|F\.{member}" {target_dir}` — confirm ABC actually exists before planning extension |
| **Claimed-but-wrong-units fields** | "uses backoff_seconds" / "stored as float" | `grep -n "{field_name}: " {target_file}` + read 1-3 lines — confirm unit / type assumption |
| **Claimed-but-silent-constraint-delta** | "frontend re-point shipped" / "+N tests added" / "bundle size unchanged" | `git diff $(git merge-base main HEAD)..HEAD -- 'frontend/src/**' \| grep -cE '^\+[^+].*oklch\('` — count delta against `HEX_OKLCH_BASELINE` in `check-mockup-fidelity.mjs`; same pattern applies to AP-N detector counts, Vite bundle size byte delta, pytest/Vitest count deltas. In agent-delegated migration sprints, the agent typically nails the visual/code change BUT silently exceeds baseline-constrained metrics (HEX_OKLCH literal count, AP-N count, bundle KB). Day 0 grep surfaces the delta upfront so baseline bump lands in same Day 1 commit (instead of next PR's CI hotfix). ROI evidence: Sprint 57.49 silent HEX_OKLCH +1 → PR #200 hotfix `74ed8a2f` post-merge fix-forward; AUDIT-001 (Sprint 57.51 Track C) Verdict A confirmed intended verbatim port + this rule extraction. |
| **Stale-docstring-Karpathy-3** | docstring/MHist claims "X uses Y" / "TODO remove Z next sprint" / "deprecated since Sprint N" | `grep -nE '"""\|^#\|^//\|^/\*' {target_file}` to find docstring/comment regions; then cross-grep the referenced symbol/file against repo reality. Docstrings + module-level comments + MHist entries are "code" for the dead-code rule (Karpathy §3) — when they reference symbols/features that have been removed, they're orphan claims that mislead Day 0 reviewers. ROI evidence: Sprint 57.50 D-DAY0-8 — `_fixtures.ts` L21 docstring referenced SEATS_FIXTURE which Sprint 57.49 had already removed; Day 0 caught the stale comment, Sprint 57.50 task 1.2.4 scope shrunk from ~5 min Day 1 surprise rework to ~1 min docstring cleanup. |
| **Claimed-but-missing-storage-path** (Sprint 57.57 PROMOTION) | "tenant overrides stored at `Tenant.<col>`" / "<Resource>OverrideStore table exists" / "PUT writes to dedicated `tenant_<resource>` table" | `grep -rn "meta_data\[.<key>.\]\|<Resource>Service\|class .*<Resource>.*Store\|tenant_<resource>" backend/src/` — discover actual storage architecture (dedicated table vs JSONB-on-registry-table vs JSONB-on-tenants-meta_data) BEFORE plan §4.1 commits to a Pydantic write shape. ROI evidence (3-data-point): Sprint 57.55 D-DAY0-B 🔴 RED (plan assumed `tenants.meta_data["tenant_overrides"]` → reality `feature_flags.tenant_overrides[str(tid)]` JSONB ON registry table; pivot saved ~30-45 min); Sprint 57.56 D-DAY0-A 🔴 RED (plan assumed Quotas has override storage → reality PlanQuota per-Plan template immutable; Option B `tenants.meta_data["quota_overrides"]` JSONB direct write; pivot saved ~60 min vs plan v0 abort); Sprint 57.57 D-DAY0-A ✅ GREEN inverse-validation (storage path `tenant.meta_data["rate_limits"]` established Sprint 57.48 Track D → no plan pivot needed; rule produces actionable outcome in BOTH directions). Codified Sprint 57.57 closeout per `AD-Day0-Prong2-Phase58-WriteSide-Resource-Storage-Grep` PROMOTION. |
| **Claimed-but-missing-canonical-service** (Sprint 57.57 PROMOTION) | "extend `<Resource>Service.set_override` method" / "add `<Resource>Store.put()` upsert" / "call canonical service for audit chain auto-emit" | `grep -rn "class .*<Resource>Service\|class .*<Resource>Store\|def set_\|def put_\|def update_" backend/src/<scope>/` — discover canonical service availability (exists → use canonical method for cleaner audit chain + cache invalidation; doesn't exist → direct ORM UPDATE + manual `append_audit` pattern Sprint 57.3 + 57.56 precedent). ROI evidence (2-data-point both directions actionable): Sprint 57.55 D-DAY0-T 🆕 NOTABLE positive direction (`FeatureFlagsService.set_tenant_override` Sprint 56.1 IS canonical setter auto-emitting audit chain → clean V2 service path; REMOVED `AD-FeatureFlags-PerFlag-AuditLog-Phase58` carryover positive side-effect); Sprint 57.56 D-DAY0-D 🆕 NOTABLE inverse direction (NO canonical service for Quotas → architectural simplification path = direct ORM UPDATE + manual `append_audit`; Sprint 57.3 PATCH precedent); Sprint 57.57 D-DAY0-B inverse continued (NO canonical service for RateLimits → same direct ORM path as Sprint 57.56). Both directions produce actionable plan pivots — codified Sprint 57.57 closeout per `AD-Day0-Prong2-CanonicalService-Grep` PROMOTION. |
| **Claimed-but-nested-shape-mismatch** (Sprint 57.60 PROMOTION) | "stored as `{resource, window, limit}`" / "config items are typed objects" / "the JSONB holds `{key: value}` dicts" | when the plan asserts the NESTED shape of a stored blob (JSONB / dict / list-of-dicts), READ the actual Pydantic model / dataclass / TypedDict BODY — do NOT infer from the key name alone. `grep -rn "class .*<Model>\|<field>:" backend/src/` to locate, THEN Read the model body to confirm the real nested shape. ROI evidence (2-data-point): Sprint 57.58 D-DAY1-1 (stored `meta_data["rate_limits"]` shape is UI display strings `{label, value}` e.g. `{"label":"API requests","value":"100 / min"}` NOT the assumed `{resource, window, limit}` — the runtime gate had to normalize via `parse_rate_limit_item`; caught mid-Day-1); Sprint 57.59 reinforced (both the live normalizer + the inline `0019` migration parser keyed off the `{label, value}` shape, not the assumed typed object). Reading the model body at Day 0 surfaces the real shape before plan §4 commits to a parse/write contract. Codified Sprint 57.60 closeout per `AD-Day0-Prong2-Nested-Shape-Read` PROMOTION. |
| **Claimed-but-flat-codegen-shape** (Sprint 57.67 — 4 data points, fold-in) | "codegen TS event/DTO types from existing Python types" / "interface mirrors the dataclass" | when GENERATING consumer types/schemas from existing producer types, capture the STRUCTURAL SHAPE (envelope nesting), NOT just field names — Read the producer/serializer body first. Sprint 57.67 stage-1 emitted flat `{type, ...fields}` but the wire is nested `{type, data:{...}}`; recurred 4× → `AD-Day0-Codegen-Existing-Shape-Capture`. Verify the wire envelope nesting before drafting the consumer type. |
| **Claimed-but-no-live-producer** ("fill/wrap/instrument every X" scopes; Sprint 57.71 + 57.72) | "wrap every loop span" / "fill all N Inspector tabs" / "instrument every call site" | for "fill/wrap/instrument every X" scopes, grep that EACH X has a live producer / call-site BEFORE planning to surface it — else the slot is an AP-4 Potemkin. Sprint 57.71: 2 of 6 tracer spans had no loop-level call site (deferred, not faked); 57.72: only 1 of 3 Inspector tabs had a live event producer (Tree shipped; Trace/Memory → ComingSoon). |

### Prong 2.5 — Child Component Tree Depth Audit (frontend page sprints only; AD-Plan-5 fold-in Sprint 57.40 — `chore/rules` ship via Item #2 of post-Sprint-57.39 4-AD micro-fix sequence)

**Applies when**: sprint plan involves frontend page re-point / restructure where the **entry component** (e.g. `frontend/src/pages/<route>/index.tsx`) and its **child components** (e.g. `frontend/src/features/<area>/components/*.tsx`) may carry DIFFERENT vintages of styling / structure. Prong 2 scopes only to the entry component file; this sub-prong extends grep depth into the child-component tree.

**Why this matters** (Sprint 57.39 D-DAY1-1 evidence): `/governance` + `/verification` entry components were migrated to mockup-ui `Tabs` primitive (closing the shell-level NEAR-PARITY), but the child components they import (`AuditLogViewer` / `VerificationList` / `CorrectionTraceView` / etc.) retained Sprint 57.5 / 57.9 / 57.11-vintage Tailwind shadcn-utility patterns. Day 0 plan-grep (Prong 2) only checked the entry component file → child drift was invisible until Day 1 code → mid-sprint scope expansion required (FIX-015 follow-up PR #183: +347 lines / 9 files).

**Required grep depth-2 sweep**:

For each target frontend page in plan §Technical Spec:

1. **Enumerate child component tree** (depth-1): `grep -nE "import.*from.*@/features/<area>" frontend/src/pages/<route>/index.tsx` → list child component file paths
2. **Per child file — anti-pattern grep**: run plan-relevant pattern greps against each enumerated child file. Common drift class queries:

| Drift class | Plan claim pattern (in §Technical Spec) | Grep verify pattern (on each child component file) |
|-------------|------------------------------------------|---------------------------------------------------|
| **Shadcn-utility token residue** (AP-Phase2-C) | "page is verbatim-CSS aligned" / "Phase-2 re-pointed" | `grep -E "bg-card\|text-foreground\|border-border\|bg-muted\|text-muted-foreground" {child_file}` — non-zero = residue (FIX-012 retired `--sc-border`; FIX-015 closed governance + verification residue) |
| **Inline `style=` missing escape comment** (STYLE.md §1 + §3) | "no inline style violations" / "STYLE.md §3 escape used" | `grep -E "style=\{\{" {child_file}` + verify each match has adjacent `eslint-disable-next-line no-restricted-syntax` comment (FIX-015 CI fail lesson: 28 sites missed by agent) |
| **Outer wrapper artifact** (AP-Phase2-A) | "mockup has no outer wrapper" / "matches mockup root" | `grep -nE "<div style=\{\{[^}]*padding" {child_file}` — production-only padding wrappers (FIX-011 lesson — Sprint 57.19 vintage drift) |
| **Layout-class fullBleed drop** (AP-FullBleed) | "preserves AppShellV2 chrome" / "fullBleed prop intact" | `grep -nE "fullBleed\|chat-shell\|loop-canvas\|page-head" {child_file}` (FIX-010 lesson) |
| **Tab-shell vs monolithic structural divergence** | "matches mockup tab structure" | compare entry component's `<Tabs>` children vs mockup file's `<>` fragment / `.tabs-shell` structure — structural mirror mismatch = production tab-shell wraps mockup-monolithic content (Sprint 57.39 D-DAY1-1 root cause) |

**Recursion depth**: typical N = 2 (entry → direct children). Recurse to N = 3 only when the page architecture involves nested feature-area imports (rare; e.g. `chat-v2` blocks-of-blocks).

**Cost / benefit**:
- Per-page cost: ~5-10 min (1 import-grep + N anti-pattern greps per child component)
- Benefit: catches Sprint 57.39-class scope expansion at Day 0 instead of Day 1+ (1-5 hr saved per drift caught, depending on child count)
- **Skip when**: scope is non-frontend, first-time scaffolding (no existing tree to audit), or pages with no `import.*@/features/` consumers (single-file pages)

### Prong 3 — Schema Verify (AD-Plan-4 promoted Sprint 57.1)

**Applies when**: sprint plan introduces NEW DB tables / Alembic migrations / ORM models / DB schema fields. Path verify (Prong 1) confirms file existence; content verify (Prong 2) confirms code patterns. Neither catches **column-level schema drift** between plan-time assumed schema and reality.

For every new table / migration / ORM model in plan §Technical Spec → grep DB column declarations against asserted schema before Day 1 starts:

- New table columns: `grep -A 30 "CREATE TABLE {table_name}\|class {ORM}\|table_args" backend/src/infrastructure/db/` — list every column + type + nullable
- Cross-table FK references: `grep -rn "ForeignKey.*{ref_table}\|REFERENCES {ref_table}" backend/src/infrastructure/db/` — confirm referenced table.column exists with matching type
- Migration head version: `ls backend/src/infrastructure/db/migrations/versions/ | sort -V | tail -3` — confirm next available number not already occupied
- RLS policy presence: `grep -A 3 "ENABLE ROW LEVEL SECURITY\|tenant_isolation_{table}" {migration_file}` — multi-tenant rule check (per `.claude/rules/multi-tenant-data.md` 鐵律)
- Plan-asserted column drift catch: re-read plan §Technical Spec column list; for each column → grep ORM file to confirm field name + type + nullable + default match exactly

Common schema drift classes:

| Drift class | Plan claim pattern | Schema-grep verify pattern |
|-------------|--------------------|----------------------------|
| **Claimed-but-missing column** | "table X has column Y" | `grep -n "{column_name}" {orm_file}` — 0 results = drift |
| **Claimed-but-wrong-type column** | "column Z is VARCHAR(64)" / "is NUMERIC(20, 4)" | `grep -A 1 "{column_name}" {migration_file}` — type mismatch |
| **Claimed-but-renamed table** | "INSERT into table_a" / FK to "table_b" | `grep -rn "table_a\|table_b" backend/src/infrastructure/db/` — actual name drift |
| **Claimed-but-occupied migration head** | "Alembic 0014_xxx" | `ls migrations/versions/ | sort -V | tail -3` — 0014 already exists → use 0015 |
| **Missing RLS policy** | new tenant_id table without RLS | `grep "ENABLE ROW LEVEL SECURITY\|tenant_isolation_{table}" {migration}` — 0 results = lint will fail |
| **Physical-column-vs-ORM-alias** (Sprint 57.60 PROMOTION) | "raw SQL `UPDATE tenants SET meta_data ...`" / "migration reads the `meta_data` column" | when a migration / raw SQL touches a column whose ORM attribute is an ALIAS (`mapped_column("physical_name", ...)`), the raw SQL MUST use the PHYSICAL column name, not the ORM attr. `grep -n "mapped_column(\"" backend/src/infrastructure/db/models/*.py` — any `mapped_column("X", ...)` where `X` ≠ the Python attr name = alias; raw SQL must quote `"X"`. ROI evidence (2-data-point): Sprint 57.59 D-DAY1-1 (tenants JSONB ORM attr `meta_data` is `mapped_column("metadata", ...)` in `identity.py`; the `0019` data-migration raw SQL had to use `"metadata"` not `meta_data` — caught mid-Day-1); Sprint 57.60 D-DAY0-M (applied pre-emptively at plan-time — `0020` raw SQL uses `"metadata"` from the start; 0 mid-sprint surprise). Codified Sprint 57.60 closeout per `AD-Day0-Prong3-Physical-Column-Read` PROMOTION. |


## ROI evidence (Sprint 55.6 promotion validation)

AD-Plan-3 was logged Sprint 55.4 candidate, validated Sprint 55.5 first application (5 drifts → 4-8× ROI), and **promoted to validated rule via Sprint 55.6 fold-in** based on cumulative evidence:

| Sprint | Application count | Drifts caught | Cost | Benefit prevented | ROI |
|--------|-------------------|---------------|------|-------------------|-----|
| 55.5 | 1st (Day 0 + 1 + 2) | 5 (D1+D2+D4+D5+D7) | ~55 min | ~3-4 hr re-work | 4-8× |
| 55.6 | 2nd-6th (Day 0-3) | 11 (D1-D11) | ~75 min | ~9-10 hr re-work + 2 production-grade bugs | 7-8× + 2 saves |

**D3 critical scope reduction in Sprint 55.6 alone**: AD-Cat8-2 dropped from "design + wire ~10-12 hr" to "wire-only ~5-6 hr" — caught via content grep (Prong 2), invisible to path verify (Prong 1).

**AD-Plan-4 Schema-Grep promotion ROI (Sprint 57.1 fold-in based on cumulative evidence)**:

| Sprint | Schema-Grep application | Drifts caught | Cost | Benefit prevented | ROI |
|--------|-------------------------|---------------|------|-------------------|-----|
| 56.1 | 1st (Day 0) | 2 (D26+D27 column-level) | ~30 min | ~1-2 hr re-work | 2-4× |
| 56.3 | 2nd (Day 0) | 1 (D6 sessions.total_cost_usd column) | ~20 min | ~1 hr re-work | 3× |
| **Cumulative** | **2 sprints** | **3 column drifts caught Day-0** | ~50 min | ~2-3 hr re-work | 3-4× |

Schema-Grep extends Prong 2 from code-pattern level to DB-column level. Without it, column drift surfaces at first migration / first ORM test run, costing 1-2 hr re-work per occurrence. With it, drift surfaces in Day 0 plan-verify pass at <30 min cost.

**AD-Plan-5 Frontend-Tree-Depth promotion ROI (Sprint 57.40 fold-in based on Sprint 57.39 + FIX-015 evidence)**:

| Sprint / FIX | Prong 2.5 application | Drifts caught | Cost | Benefit prevented | ROI |
|-------------|------------------------|---------------|------|-------------------|-----|
| Sprint 57.39 D-DAY1-1 | (pre-Prong-2.5 escape — Day 0 grep only checked entry component) | 1 drift surfaced mid-Day-1 (governance + verification child shadcn residue) | n/a (escape) | ~3-5 hr scope-expansion absorbed into follow-up PR #183 | (negative — what Prong 2.5 was designed to prevent) |
| FIX-015 post-hoc | Manual Day 0 grep across 6 child components | 6 drift files (4 confirmed AD-list + 2 NEW: ApprovalList + DecisionModal) | ~5 min | ~3-5 hr scope-creep avoided in original Sprint 57.39 | 36-60× |
| **Cumulative** | **2 applications** | **6 files (~28 inline-style sites secondary)** | ~5-10 min per Day 0 | scope-expansion avoidance | **20-60×** |

Frontend-Tree-Depth extends Prong 2 from entry-component grep to child-component-tree grep (depth N = 2). Without it, child drift surfaces at Day 1+ during code → either mid-sprint scope expansion OR follow-up FIX PR (Sprint 57.39 → FIX-015 pattern). With it, drift surfaces at Day 0 at <10 min cost, allowing scope adjustment in plan §Technical Spec before code starts.

## Examples

**Sprint 53.7 D4-D12** (9 path-drift findings cost ~1 hr re-work — _why Prong 1 exists_):
- D4: Plan referenced `check_promptbuilder.py --root` arg behavior that did not match script
- D7-D8: Plan assumed lint scripts would silently accept missing `--root` flag; reality = silent-OK or exit 2
- D10-D12: Plan-stated `pytest` count baselines off by 2-5 tests vs. real repo at branch-creation time

**Sprint 55.3 D1-D3** (3 path-drift findings caught _before_ Day 1 code — _Prong 1 ROI validation_):
- D1: Plan assumed sole-mutator refactor needed for `agent_harness/`; grep showed three target patterns already grep-zero → AD-Cat7-1 scope 收斂 to enforcement test + lint
- D2: Plan assumed `verification_span` would be created; `verification/_obs.py` already had it → AD-Cat12-Helpers-1 became `extract` (non-create)
- D3: Plan assumed DB-backed `HITLPolicy` already partially wired; `DefaultHITLManager.default_policy` was in-memory only → AD-Hitl-7 baseline confirmed cleanly

**Sprint 55.6 D3 critical catch** (Prong 2 content-verify — _why AD-Plan-3 promotion exists_):
- 55.4 retro Q4 + 55.5 retro Q4 both narrated "AD-Cat8-2 needs full retry-with-backoff design"
- Day-0 content grep on `loop.py:_handle_tool_error` revealed: ABC implemented, called from main exec, error_policy/error_budget/circuit_breaker ALL wired — **only `_retry_policy` attribute is dead**
- Scope dropped from ~10-12 hr to ~5-6 hr; saved ~5-6 hr scope-creep design work
- Path verify (Prong 1) alone could not catch this: all referenced files exist; content gap requires Prong 2 grep

