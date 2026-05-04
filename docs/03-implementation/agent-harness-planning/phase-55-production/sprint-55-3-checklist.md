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

- [ ] **Verify grep-zero in 4 production paths**
  - `backend/src/agent_harness/**/*.py` (excluding `state_mgmt/reducer.py`)
  - `backend/src/api/**/*.py`
  - `backend/src/business_domain/**/*.py`
  - `backend/src/platform_layer/**/*.py`
  - Patterns: `state\.messages\.append`, `state\.scratchpad\[`, `state\.tool_calls\.append`, `state\.user_input\s*=`
  - DoD: grep returns 0 for each pattern (or audit log if any)
- [ ] **Catalog any residual violations**
  - If found: write violation list to progress.md Day 2 entry
  - Plan modular fix in same Day 2 (within ~30 min budget)
- [ ] **Write `backend/scripts/lint/check_sole_mutator.py`**
  - Disallowed patterns enumerated
  - Whitelist: `agent_harness/state_mgmt/reducer.py`, `tests/**`, `scripts/**`
  - Exit 1 on any production-code match;exit 0 if clean
  - Print violation file:line for failures
  - File header per convention
- [ ] **Wire into `backend/scripts/lint/run_all.py`**
  - Add 7th lint invocation
  - Update header comment "6 V2 lints" → "7 V2 lints"
  - Verify exit code aggregation correct(any sub-lint fail → run_all.py fail)
- [ ] **Write `backend/tests/unit/state_mgmt/test_sole_mutator_lint.py`**
  - Test 1: subprocess invokes `check_sole_mutator.py` on real codebase → exit 0
  - Test 2: inject violation into temp file → assert exit 1 + correct error message
  - Test 3: whitelist works (reducer.py mutation does NOT trigger lint)
- [ ] **Run all tests + 7 V2 lints**
  - `pytest backend/tests/unit/state_mgmt/ -v` green
  - `python backend/scripts/lint/run_all.py` exit 0 (now 7/7 green)
- [ ] **Update progress.md Day 2 entry**
  - Document grep-zero verification result
  - Any residual violations + fixes
  - 7 V2 lints all green confirmation
- [ ] **Commit AD-Cat7-1**
  - Commit: `feat(lint, state-mgmt, sprint-55-3): close AD-Cat7-1 (sole-mutator CI lint)`

---

## Day 3 — AD-Hitl-7 Per-Tenant HITLPolicy DB Persistence

- [ ] **Read existing HITLPolicy spec + DefaultHITLManager**
  - `backend/src/agent_harness/_contracts/hitl.py` HITLPolicy dataclass
  - `backend/src/platform_layer/governance/hitl/manager.py` `__init__` + `get_policy`
  - Confirm baseline: in-memory `default_policy` only
- [ ] **DB Schema design** — `hitl_policies` table
  - Columns: id UUID PK / tenant_id UUID NOT NULL FK tenants / risk_thresholds JSONB / approver_roles JSONB / sla_seconds INT / escalation_chain JSONB / created_at / updated_at
  - Constraint: UNIQUE (tenant_id)
  - RLS policy: tenant-isolation per `multi-tenant-data.md` §Rule 1
- [ ] **Write `backend/alembic/versions/0013_hitl_policies.py`**
  - upgrade(): CREATE TABLE + RLS policy + index
  - downgrade(): DROP TABLE
  - File header per convention
- [ ] **Verify alembic dry-run**
  - `cd backend && alembic upgrade head && alembic current`
  - `cd backend && alembic downgrade base && alembic current`
  - DoD: both commands return successfully (no schema drift)
- [ ] **Edit `backend/src/infrastructure/db/models/governance.py`**
  - Add `class HitlPolicyRow(Base)` mapping to `hitl_policies`
- [ ] **Edit `backend/src/agent_harness/hitl/_abc.py`**
  - Add `class HITLPolicyStore(ABC)` with `async def get(self, tenant_id: UUID) -> HITLPolicy | None`
- [ ] **Write `backend/src/platform_layer/governance/hitl/policy_store.py`**
  - `class DBHITLPolicyStore(HITLPolicyStore)` implementation
  - SELECT from `hitl_policies` WHERE tenant_id = :tid
  - Return None if no row;return HITLPolicy if row found
  - File header per convention
- [ ] **Edit `backend/src/platform_layer/governance/hitl/manager.py`**
  - `__init__` 接受 `policy_store: HITLPolicyStore | None = None`
  - `get_policy(tenant_id)`: if policy_store is provided → query DB; if None or no row → fallback to default_policy
- [ ] **Edit `backend/src/platform_layer/governance/service_factory.py`**
  - When constructing `DefaultHITLManager`, also instantiate `DBHITLPolicyStore` (in production mode)
  - Test mode: pass None policy_store(rely on default_policy)
- [ ] **Write `backend/tests/unit/governance/hitl/test_db_hitl_policy_store.py`**
  - Test 1: empty table → `get(tenant_id)` returns None
  - Test 2: insert sample policy → `get(tenant_id)` returns matching HITLPolicy
  - Test 3: 2 tenants → `get(tenant_a) ≠ get(tenant_b)`
- [ ] **Write `backend/tests/integration/governance/test_hitl_manager_per_tenant_policy.py`**
  - Test 1: 2 tenants insert 不同 policy → manager `get_policy(tenant_a) ≠ get_policy(tenant_b)`
  - Test 2: tenant_c (no row) → falls back to default_policy
  - Test 3: RLS enforced (tenant_a cannot read tenant_b's policy via row-level)
  - Per `testing.md` §Module-level Singleton Reset Pattern: per-suite autouse fixture calling `reset_service_factory()`
- [ ] **Run tests + 7 V2 lints**
  - `pytest backend/tests/unit/governance/hitl/ backend/tests/integration/governance/ -v`
  - `python backend/scripts/lint/run_all.py` 7/7 green
- [ ] **Update progress.md Day 3 entry**
  - Document Alembic upgrade/downgrade verification
  - Document tests (2 unit + 3 integration ≈ 5 new tests)
  - Confirm RLS policy enforced
- [ ] **Commit AD-Hitl-7**
  - Commit: `feat(governance, db, sprint-55-3): close AD-Hitl-7 (per-tenant HITLPolicy DB)`

---

## Day 4 — Retrospective + Closeout

- [ ] **Verify all 6 ADs closed** (acceptance criteria checklist)
  - AD-Plan-1: §Step 2.5 in sprint-workflow.md ✅
  - AD-Lint-2: per-day targets dropped ✅
  - AD-Lint-3: MHist 1-line ✅
  - AD-Cat7-1: 7 V2 lints + grep-zero verified ✅
  - AD-Hitl-7: hitl_policies + DBHITLPolicyStore + 5 tests ✅
  - AD-Cat12-Helpers-1: category_span + 4 verifier refactors + tests ✅
- [ ] **Run full pytest baseline**
  - `cd backend && python -m pytest -q`
  - Target: 1416 → ≥1428 (+12 minimum)
- [ ] **Run full lint chain**
  - `cd backend && black --check src/ tests/`
  - `cd backend && isort --check-only --profile black src/ tests/`
  - `cd backend && flake8 src/ tests/`
  - `cd backend && mypy src/ --strict`
  - `cd backend && python scripts/lint/run_all.py` (now 7 lints)
- [ ] **LLM SDK leak check**
  - `cd backend && grep -rE "^(from |import )(openai|anthropic|agent_framework)" src/agent_harness/ src/infrastructure/`
  - DoD: zero matches
- [ ] **Compute calibration ratio**
  - Sum actual hours across Day 0-4 (from progress.md entries)
  - Ratio = actual / committed
  - Document in retro Q2
- [ ] **Catalog final drift findings**
  - D1-D3 from Day 0 + Dn from Day 1-3
- [ ] **Write `retrospective.md`** (6 必答 Q1-Q6)
  - Path: `docs/03-implementation/agent-harness-execution/phase-55/sprint-55-3/retrospective.md`
  - Q1 What went well
  - Q2 What didn't go well + calibration ratio + delta vs band
  - Q3 What we learned (generalizable)
  - Q4 Audit Debt deferred (carryover candidates for 55.4-55.6)
  - Q5 Next steps (rolling planning — 55.4 candidate scope only)
  - Q6 0.40 multiplier 2nd application validation + recommendation for Phase 56+
- [ ] **Update `claudedocs/6-ai-assistant/prompts/SITUATION-V2-SESSION-START.md`**
  - §8 close 6 ADs
  - Add new ADs (if any) from Day 1-3 drift catalog
  - §9 milestones row +Sprint 55.3 (V2 22/22 unchanged — audit cycle)
  - Footer Last Updated 2026-05-04
  - Update history table +1 row
- [ ] **Update memory**
  - `memory/project_phase55_3_audit_cycle_1.md` — new
  - `memory/MEMORY.md` — index +1 line
- [ ] **Commit Day 4**
  - Commit 1: `docs(retro, sprint-55-3): retrospective + 6 AD closure summary`
  - Commit 2: `chore(docs, sprint-55-3): SITUATION + memory sync`
- [ ] **Push branch**
  - `git push -u origin feature/sprint-55-3-audit-cycle-A-G`
- [ ] **Open PR**
  - Title: `Sprint 55.3: Audit Cycle Mini-Sprint #1 — close 6 ADs (Groups A + G)`
  - Body: 6 AD closure summary + plan/checklist links + retrospective link
  - Co-author footer
- [ ] **Watch CI green**
  - 5 active required CI checks all pass(backend-ci / V2 Lint / Frontend E2E / etc.)
  - paths-filter workaround if needed: touch `.github/workflows/backend-ci.yml` header(per AD-CI-5 pattern)
- [ ] **Merge PR** (after CI green)
  - Solo-dev policy: review_count=0;merge as author after CI green
  - Update main HEAD reference in memory + SITUATION
- [ ] **Closeout PR (docs sync)**
  - If SITUATION + memory updates lag main merge,open closeout PR per established pattern
  - Title: `Sprint 55.3 closeout: SITUATION + memory sync`
- [ ] **Final verify on main**
  - `git checkout main && git pull && git status` clean
  - V2 22/22 unchanged (audit cycle does not advance main progress)

---

## Tracker

| AD | Status | Tests Added | Commit |
|----|--------|-------------|--------|
| AD-Plan-1 | ⏳ pending | 0 | — |
| AD-Lint-2 | ⏳ pending | 0 | — |
| AD-Lint-3 | ⏳ pending | 0 | — |
| AD-Cat7-1 | ⏳ pending | 2-3 | — |
| AD-Hitl-7 | ⏳ pending | 5-7 | — |
| AD-Cat12-Helpers-1 | ⏳ pending | 3-4 | — |
| **Total** | **0/6 closed** | **0/+12** | — |

---

**Status**: Day 0 — Plan + Checklist + progress.md drafting (this commit pending). Pending user approval before Day 1 code starts.
