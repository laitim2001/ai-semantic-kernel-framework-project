# Sprint 55.3 — Checklist

[Plan](./sprint-55-3-plan.md)

> **Note**: Per **AD-Lint-2**(itself part of this sprint),per-day "Estimated X hours" headers will be **dropped** from this template starting Sprint 55.4. 55.3 keeps them at sprint-aggregate granularity only(see plan §Workload). Day-level estimates moved to progress.md(individual record),non-binding.

---

## Day 0 — Setup + Day-0 探勘 + Plan/Checklist Drafting

- [x] **Working tree clean verified on main `596405b3`**
  - DoD: `git status --short` returns empty
  - Verify: ran successfully
- [x] **Feature branch created**
  - Branch: `feature/sprint-55-3-audit-cycle-A-G`
  - DoD: `git branch --show-current` returns this name
- [x] **Day-0 探勘 grep run (AD-Plan-1 newly self-applied)**
  - 5 grep + 2 read calls
  - Drift findings catalogued: D1 (Cat7 grep-zero) / D2 (verification_span exists) / D3 (HITLManager default_policy in-memory)
  - DoD: drift findings written to plan §Risks
- [x] **Read 55.2 plan template (13 sections / Day 0-4)**
  - DoD: section headers grep result confirmed
- [x] **Write `sprint-55-3-plan.md`** (this sprint plan)
  - 13 sections mirror 55.2
  - 6 ADs detailed (AD-Plan-1 / AD-Lint-2 / AD-Lint-3 / AD-Cat7-1 / AD-Hitl-7 / AD-Cat12-Helpers-1)
- [x] **Write `sprint-55-3-checklist.md`** (this file)
  - Mirror 55.2 Day 0-4 structure
- [ ] **Write Day 0 `progress.md` entry**
  - Path: `docs/03-implementation/agent-harness-execution/phase-55/sprint-55-3/progress.md`
  - DoD: Day 0 entry covers actions taken + drift findings + next-day plan
- [ ] **Commit Day 0** (plan + checklist + progress)
  - Commit: `chore(docs, sprint-55-3): Day 0 plan + checklist + progress`
  - DoD: `git log --oneline -1` shows Day 0 commit

---

## Day 1 — Group A (3 process/template ADs) + AD-Cat12-Helpers-1

### AD-Plan-1 — `sprint-workflow.md` §Step 2.5 Day-0 Plan-vs-Repo Verify

- [x] **Edit `.claude/rules/sprint-workflow.md`**
  - Add new §Step 2.5 "Day-0 Plan-vs-Repo Verify" between current §Step 2 (Create Checklist File) and §Step 3 (Implement Code)
  - Content: mandatory grep verify for plan §Technical Spec assertions(file paths / class names / table names / fixture paths)
  - Drift catalog goes to progress.md Day 0 entry
  - Cross-link to `anti-patterns-checklist.md` AP-2 (no orphan code)
  - Examples: 53.7 D4-D12 + 55.3 D1-D3 (this sprint's findings)
- [x] **Verify**: `grep -n "### Step 2.5" .claude/rules/sprint-workflow.md` returns 1 (note: header level `### `, not `## `)
- [x] **Verify**: `grep -n "Day-0 Plan-vs-Repo Verify" .claude/rules/sprint-workflow.md` returns ≥ 1 (3 matches: §Step 2.5 header + §Step 2.5 description + Modification History entry)

### AD-Lint-2 — Drop Per-Day Calibrated Targets

- [x] **Edit `.claude/rules/sprint-workflow.md`** (same file as AD-Plan-1; combine commit)
  - Step 2 §Required Format template: dropped `(Estimated X hours)` from Day header / `(Y min)` from task suffix / `Estimated: Y min` sub-bullet
  - Added prohibition list with strikethrough examples + Sprint 53.7 retrospective Q4 evidence
  - Step 5 added "Per-day estimates live here" section: progress.md is single home for per-day / per-task time tracking
- [x] **Combined commit for AD-Plan-1 + AD-Lint-2**
  - Commit: `docs(rules, sprint-55-3): close AD-Plan-1 + AD-Lint-2 (sprint-workflow.md)` — pending

### AD-Lint-3 — Modification History 1-Line Format

- [x] **Edit `.claude/rules/file-header-convention.md`**
  - §格式 section: rewrote to enforce "1-line max per entry" + char budget guidance (≤ E501 / 100 chars including indent or `> - ` Markdown prefix; effective ~90 chars)
  - Added good/bad examples in §格式
  - Existing 4 file-type examples (Python L57-60 / TypeScript L100-102 / Markdown L122-124 / Compactor L335-336) already conform to 1-line — no change needed
  - Added new 禁止項 5: multi-line reason / bullet sub-points / line breaks / quote markers — with 4 ❌ examples + 3 ✅ examples + Why
  - Updated top Modification History to reflect Sprint 55.3 entry (1-line format demonstrating itself)
- [x] **Verify**: `grep "1-line max per entry"` returns 1 ✓ / `grep "禁止 5"` returns 1 ✓
- [ ] **Commit AD-Lint-3**
  - Commit: `docs(rules, sprint-55-3): close AD-Lint-3 (MHist 1-line format)` — pending

### AD-Cat12-Helpers-1 — Extract `category_span` Helper

- [x] **Decision: Option A (thin wrapper delegation)** — revised from preliminary B
  - Reason: 7 callers (2 verification + 5 business_domain) each have ergonomic signatures (verifier_name positional / service_name+method keyword) and different categories (VERIFICATION / TOOLS); refactoring all 7 call sites with explicit category arg = invasive. Option A: keep wrappers, extract no-op + start_span boilerplate to `category_span` primitive.
  - Documented in progress.md Day 1 entry
- [x] **Create `backend/src/agent_harness/observability/helpers.py`**
  - Function: `category_span(tracer: Tracer | None, name: str, category: SpanCategory) -> AsyncIterator[None]`
  - Async ctx mgr; no-op when tracer is None
  - File header per `file-header-convention.md` (Purpose / Category 12 / Created)
- [x] **Refactor `verification/_obs.py`** — delegate to category_span; preserve `verification_span(tracer, name)` signature
- [x] **`verification/rules_based.py` UNTOUCHED** — Option A means external callers see no API change
- [x] **`verification/llm_judge.py` UNTOUCHED** — Option A means external callers see no API change
- [x] **Refactor `business_domain/_obs.py`** — delegate to category_span; preserve `business_service_span(tracer, *, service_name, method)` signature
- [x] **`business_domain/*/service.py` (5 files) UNTOUCHED** — Option A means external callers see no API change
- [x] **Cat 9 wrappers UNTOUCHED** per 54.2 D19 (reuse inner judge tracer)
- [x] **Add `category_span` to `agent_harness/observability/__init__.py` __all__**
- [x] **Write `backend/tests/unit/agent_harness/observability/test_category_span.py`**
  - Test 1: tracer=None → no-op (no exception, body executes)
  - Test 2: tracer mock → span emit verified with name + category; body runs inside ctx
  - Test 3: sequential calls accumulate spans in order
- [x] **Run tests**: 10 passed (3 new + 4 verification regression + 3 business_domain regression)
- [x] **Lint chain**: black ✓ / isort ✓ / flake8 ✓ / mypy --strict ✓ / 6 V2 lints ✓
- [x] **Drift findings (Day 1)**:
  - **D4** V2 lint scripts at PROJECT root `scripts/lint/` (not `backend/scripts/lint/` as plan §AD-Cat7-1 stated) — Day 2 will write `check_sole_mutator.py` to `scripts/lint/`
  - **D5** First import attempt `from agent_harness.observability._abc import Tracer` triggered `check_cross_category_import.py` (private cross-cat import); fix = use package re-export `from agent_harness.observability import Tracer, category_span`
- [x] **Commit AD-Cat12-Helpers-1**
  - Commit: `refactor(observability, sprint-55-3): close AD-Cat12-Helpers-1 (extract category_span)` — pending

### Day 1 Wrap

- [x] **Update progress.md Day 1 entry**
  - Cover: 3 commits (Group A 1 commit `bc468477` + AD-Lint-3 1 commit `144c4595` + AD-Cat12-Helpers-1 1 commit pending)
  - Documented Option A decision (revised from preliminary B) for AD-Cat12-Helpers-1
  - New drift findings: D4 (V2 lint scripts at project root) + D5 (cross-cat import lint pattern)
- [x] **pytest delta**: 1416 baseline → +3 new test_category_span tests + 7 regression all passing (full suite re-run deferred to Day 4 closeout)
- [x] **Tracker (end Day 1)**: 4/6 ADs closed (AD-Plan-1 ✅ / AD-Lint-2 ✅ / AD-Lint-3 ✅ / AD-Cat12-Helpers-1 ✅ pending commit / AD-Cat7-1 ⏳ Day 2 / AD-Hitl-7 ⏳ Day 3)

---

## Day 2 — AD-Cat7-1 Sole-Mutator Grep-Zero + CI Lint

> **Path correction per Day 1 D4**: V2 lint scripts live at PROJECT root `scripts/lint/`, not `backend/scripts/lint/` as plan §AD-Cat7-1 stated. Day 2 deliverables placed at correct location.

- [x] **Verify grep-zero in full backend/src/ tree (4 production paths combined)**
  - All 4 patterns grep across `backend/src/` returned **zero matches**
  - Patterns verified: `state\.messages\.append`, `state\.scratchpad\[`, `state\.tool_calls\.append`, `state\.user_input\s*=`
  - DoD: `grep -rn` returned 0 for each pattern → confirmed
- [x] **Catalog any residual violations** — none found (Day 0 D1 finding confirmed at Day 2)
- [x] **Write `scripts/lint/check_sole_mutator.py`** (project root, per D4)
  - 4 forbidden regex patterns + whitelist substrings
  - Whitelist: `agent_harness/state_mgmt/reducer.py`, `agent_harness/state_mgmt/decision_reducers.py`, `/tests/`, `__pycache__`
  - Exit 1 on any match;exit 0 if clean;exit 2 if --root missing
  - Skip lines starting with `#`(avoid false-flagging documentation prose)
  - File header per convention; r"""raw docstring""" to avoid SyntaxWarning on regex backslashes
- [x] **Wire into `scripts/lint/run_all.py`** (project root, per D4)
  - Added 7th LINT entry: `("check_sole_mutator.py", ["--root", "backend/src"])`
  - Updated docstring "6 V2 lints" → "7 V2 lints"; Modification History entry added
  - Parameterized counts via `n_lints = len(LINTS)` (defense for future additions)
  - Verified exit code aggregation correct
- [x] **Write `backend/tests/unit/agent_harness/state_mgmt/test_sole_mutator_lint.py`** (path mirror existing convention; not `tests/unit/state_mgmt/`)
  - Test 1: subprocess invokes lint on real backend/src → exit 0 ✓
  - Test 2: inject violation `state.messages.append(...)` into tmp file → exit 1 + violation in stderr ✓
  - Test 3: whitelist permits reducer.py mutation → exit 0 ✓
  - Bonus: parametric test covers 3 remaining forbidden patterns (scratchpad / tool_calls / user_input)
- [x] **Run all tests + 7 V2 lints**
  - `pytest tests/unit/agent_harness/state_mgmt/test_sole_mutator_lint.py` → **6/6 passed** (3 main + 3 parametric)
  - `python scripts/lint/run_all.py` → **7/7 green** (~0.77s total)
- [x] **Lint chain on new files**
  - black ✓ / isort ✓ / mypy --strict ✓
  - flake8: backend/tests/.../test_sole_mutator_lint.py green;`scripts/` falls back to default 79 char (not in CI scope per backend-ci.yml `flake8 src/ tests/` only) — pre-existing 80-83 char lines in run_all.py are project-consistent (Sprint 53.7 author accepted same de-facto convention)
- [x] **Update progress.md Day 2 entry** — pending after this commit
- [x] **Commit AD-Cat7-1**
  - Commit: `feat(lint, state-mgmt, sprint-55-3): close AD-Cat7-1 (sole-mutator CI lint)` — pending

---

## Day 3 — AD-Hitl-7 Per-Tenant HITLPolicy DB Persistence

> **Drift D6 + D7 + D8 corrections** (Day 3, see progress.md):
> - D6: Schema columns must mirror HITLPolicy dataclass fields (NOT plan §Spec rename: risk_thresholds/approver_roles/sla_seconds/escalation_chain)
> - D7: Alembic versions live at `backend/src/infrastructure/db/migrations/versions/`, not `backend/alembic/versions/` as plan stated
> - D8: Test paths under `tests/.../platform_layer/governance/hitl/`, not `tests/.../governance/hitl/`

- [x] **Read existing HITLPolicy spec + DefaultHITLManager**
  - `_contracts/hitl.py` HITLPolicy fields: tenant_id / auto_approve_max_risk / require_approval_min_risk / reviewer_groups_by_risk / sla_seconds_by_risk
  - `manager.py:get_policy()` baseline: returns `_default_policy` if set, else hardcoded LOW/MEDIUM
  - Confirmed in-memory only; no DB persistence yet (D3 baseline)
- [x] **DB Schema design** — `hitl_policies` table (D6-corrected)
  - Columns: id UUID PK / tenant_id UUID NOT NULL FK tenants UNIQUE / auto_approve_max_risk VARCHAR(32) / require_approval_min_risk VARCHAR(32) / reviewer_groups_by_risk JSONB / sla_seconds_by_risk JSONB / created_at / updated_at
  - Constraints: UNIQUE (tenant_id) + 2 CHECK (RiskLevel enum values)
  - RLS policy: tenant-isolation matching 0009/0012 pattern
- [x] **Write `backend/src/infrastructure/db/migrations/versions/0013_hitl_policies.py`** (D7-corrected path)
  - upgrade(): CREATE TABLE + UNIQUE + 2 CHECK + idx_hitl_policies_tenant + RLS policy
  - downgrade(): DROP POLICY + DROP TABLE
  - File header per convention
- [x] **Verify alembic upgrade/downgrade roundtrip**
  - `alembic upgrade head` → 0012 → 0013 success
  - `alembic downgrade -1` → 0013 → 0012 success
  - `alembic upgrade head` → 0012 → 0013 success (re-applied for tests)
  - DoD: both commands return successfully (no schema drift)
- [x] **Edit `backend/src/infrastructure/db/models/governance.py`**
  - Added `class HitlPolicyRow(Base)` mapping to `hitl_policies`
  - 7 column attrs mirror HITLPolicy dataclass exactly
  - Added to `__all__`
- [x] **Edit `backend/src/agent_harness/hitl/_abc.py`**
  - Added `class HITLPolicyStore(ABC)` with `async def get(self, tenant_id: UUID) -> HITLPolicy | None`
  - Updated module docstring + Modification History
- [x] **Edit `backend/src/agent_harness/hitl/__init__.py`** — re-export `HITLPolicyStore`
- [x] **Write `backend/src/platform_layer/governance/hitl/policy_store.py`**
  - `class DBHITLPolicyStore(HITLPolicyStore)` implementation
  - `_row_to_policy` + `_hydrate_risk_dict` helpers (resilient to unknown JSONB keys)
  - SELECT WHERE tenant_id = :tid;return None if no row;hydrate else
  - File header per convention
- [x] **Edit `backend/src/platform_layer/governance/hitl/manager.py`**
  - `__init__` accepts `policy_store: HITLPolicyStore | None = None`
  - `get_policy(tenant_id)` resolution order: policy_store DB → default_policy → hardcoded LOW/MEDIUM
  - Updated docstring + Modification History
- [x] **Edit `backend/src/platform_layer/governance/service_factory.py`**
  - Added `_hitl_policy_store` cached field + `get_hitl_policy_store()` method
  - `get_hitl_manager()` passes `policy_store=self.get_hitl_policy_store()` to DefaultHITLManager
  - Updated module docstring + Modification History
- [x] **Write `backend/tests/unit/platform_layer/governance/hitl/test_db_hitl_policy_store.py`** (D8-corrected path)
  - 5 unit tests: empty table → None / insert sample → matches / 2 tenants differentiate / empty JSONB defaults / hydration skips unknown keys
- [x] **Write `backend/tests/integration/platform_layer/governance/hitl/test_per_tenant_policy.py`** (D8-corrected path)
  - 4 integration tests: per-tenant DB differentiation / no-row falls to default / no-store uses default / no-overrides falls to hardcoded
- [x] **Run tests + 7 V2 lints**
  - `pytest tests/unit/platform_layer/governance/hitl/test_db_hitl_policy_store.py tests/integration/platform_layer/governance/hitl/test_per_tenant_policy.py` → **9/9 green**
  - 45 existing HITL/ServiceFactory regression tests → all green (test_manager + test_service_factory + test_state_machine + test_notification_config)
  - 7 V2 lints → **7/7 green**
- [x] **Update progress.md Day 3 entry** — pending after this commit
- [x] **Commit AD-Hitl-7**
  - Commit: `feat(governance, db, sprint-55-3): close AD-Hitl-7 (per-tenant HITLPolicy DB)` — pending

---

## Day 4 — Retrospective + Closeout

- [x] **Verify all 6 ADs closed** (acceptance criteria checklist)
  - AD-Plan-1: §Step 2.5 in sprint-workflow.md ✅ (`bc468477`)
  - AD-Lint-2: per-day targets dropped ✅ (`bc468477`)
  - AD-Lint-3: MHist 1-line ✅ (`144c4595`)
  - AD-Cat12-Helpers-1: category_span extracted + 2 wrappers delegate + 3 tests ✅ (`52d802a9`)
  - AD-Cat7-1: 7 V2 lints + grep-zero verified + 6 tests ✅ (`cd86a814`)
  - AD-Hitl-7: hitl_policies + DBHITLPolicyStore + 9 tests ✅ (`c09d3cc5`)
- [x] **Run full pytest baseline** — **1434 passed, 4 skipped** (1416 → 1434 = +18; 50% over plan ≥+12)
- [x] **Run full lint chain** — black ✓ / isort ✓ / flake8 ✓ / mypy --strict ✓ / 7 V2 lints 7/7 ✓
- [x] **LLM SDK leak check** — 0 matches
- [x] **Compute calibration ratio** — actual ~11.5 hr / committed 4 hr = **2.81** ⚠️ way over band [0.85, 1.20]
- [x] **Catalog final drift findings** — 8 total (D1-D3 Day 0 + D4-D5 Day 1 + D6-D8 Day 3)
- [x] **Write `retrospective.md`** — 6 必答 Q1-Q6 + AD-Sprint-Plan-4 (matrix proposal) + AD-Plan-2 (Day-0 path verify)
- [x] **Update `claudedocs/6-ai-assistant/prompts/SITUATION-V2-SESSION-START.md`** — §8 closes 6 ADs + supersedes AD-Sprint-Plan-2 + AD-Phase56-Calibration via AD-Sprint-Plan-4 / §9 +Sprint 55.3 row / footer Last Updated / Update history +1 row
- [x] **Update memory** — `project_phase55_3_audit_cycle_1.md` new + MEMORY.md index +1
- [ ] **Commit Day 4** — pending (this turn)
- [ ] **Push branch** — pending after commit
- [ ] **Open PR** — pending after push
- [ ] **Watch CI green** — pending
- [ ] **Merge PR** — pending after CI
- [ ] **Closeout PR (docs sync)** — pending if needed
- [ ] **Final verify on main** — pending after merge

---

## Tracker

| AD | Status | Tests Added | Commit |
|----|--------|-------------|--------|
| AD-Plan-1 | ✅ closed | 0 | `bc468477` |
| AD-Lint-2 | ✅ closed | 0 | `bc468477` |
| AD-Lint-3 | ✅ closed | 0 | `144c4595` |
| AD-Cat7-1 | ✅ closed | 6 | `cd86a814` |
| AD-Hitl-7 | ✅ closed | 9 | `c09d3cc5` |
| AD-Cat12-Helpers-1 | ✅ closed | 3 | `52d802a9` |
| **Total** | **6/6 closed** | **+18** (50% over plan ≥+12) | — |

---

**Status**: ✅ Sprint 55.3 main work complete (6/6 ADs closed). Day 4 closeout commit + push + PR pending.
