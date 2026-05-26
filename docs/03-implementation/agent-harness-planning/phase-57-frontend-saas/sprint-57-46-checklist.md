# Sprint 57.46 — Checklist

[Plan](./sprint-57-46-plan.md) — 3-AD multi-domain bundle (docs codify + backend schema + mockup capture); 1st `agent_factor = 0.45` validation.

---

## Day 0 — Plan + 三-Prong Verify (Sprint 57.45 closeout day)

### 0.1 Plan + Checklist Drafting
- [ ] **Sprint plan written** `phase-57-frontend-saas/sprint-57-46-plan.md`
  - DoD: 9 sections present (Goal / Context / Stories / Spec / Files / Workload / AC / Risks / Carryover); 4-segment Workload form
  - Verify: `Glob sprint-57-46-plan.md` returns 1
- [ ] **Sprint checklist written** (this file)
  - DoD: Day 0 / Day 1 / Day 2 structure; per-task DoD + Verify
  - Verify: `Glob sprint-57-46-checklist.md` returns 1

### 0.8 Day 0 三-Prong Verify (Step 2.5 mandatory)

**Prong 1 — Path Verify** (8 paths):
- [ ] `docs/rules-on-demand/frontend-mockup-fidelity.md` exists (Task 1 target)
- [ ] `backend/src/infrastructure/db/models/identity.py` exists (Task 2 ORM)
- [ ] `backend/src/api/v1/admin/tenants.py` exists (Task 2 API)
- [ ] `backend/src/infrastructure/db/migrations/versions/0017_verification_log.py` exists (migration head)
- [ ] `backend/src/infrastructure/db/migrations/versions/0018_*.py` does NOT exist yet (target slot)
- [ ] `frontend/scripts/mockup-sweep.mjs` exists (Task 3 target)
- [ ] `reference/design-mockups/` directory exists (Task 3 source)
- [ ] `backend/tests/api/v1/admin/test_tenants*.py` exists (Task 2 test pattern reference)

**Prong 2 — Content Verify** (5 claims):
- [ ] Tenant ORM in `identity.py` already has columns: id / tenant_code / display_name / plan_id / status / created_at (per Sprint 57.43 D-DAY0-6 + 57.44 D-DAY0-4 audit) — grep to confirm baseline before adding 5 new
- [ ] Tenant ORM does NOT already have: region / locale / retention_days / sso_enabled / seats (drift catch — if any exists, scope reduces)
- [ ] TenantSettingsResponse Pydantic in `tenants.py` current field set — grep + read
- [ ] Admin PATCH endpoint in `tenants.py` current input model — grep + read
- [ ] frontend-mockup-fidelity.md current sections — read TOC to find correct insertion point for AuditDocSync rule

**Prong 3 — Schema Verify** (Task 2 mandatory):
- [ ] Tenant table column declarations in `0014_phase56_1_saas_foundation.py` — list every column + type + nullable
- [ ] Confirm migration 0018 number not occupied: `ls migrations/versions/ | sort -V | tail -3` → 0017 is head
- [ ] RLS policy on Tenant table: confirm presence — `grep "ENABLE ROW LEVEL SECURITY\|tenant_isolation" migrations/versions/0014_*`
- [ ] Drift catch: confirm new column names + types match plan §4.2 table exactly

**Prong 2.5 — Frontend Tree Depth Audit** (N/A — Task 2 is pure backend; Task 1 + Task 3 are docs/tooling not frontend page re-point).

**Drift findings catalog**:
- [ ] All findings logged to `progress.md` Day 0 §Drift findings (format `D-DAY0-N + Finding + Implication + cross-ref to plan §Risks`)
- [ ] Go/no-go decision recorded (continue / revise plan / abort)

### 0.9 Branch + Day 0 commit
- [ ] Branch `feature/sprint-57-46-multi-domain-bundle` created ✓ (done 2026-05-26)
- [ ] Day 0.1 + 0.8 commit: `chore(sprint-57-46): Day 0 plan + checklist + 三-prong verify`

---

## Day 1 — Implementation (Code-Implementer Agent Delegation)

### 1.1 Task 1: AD-MockupFidelity-AuditDocSync-Rule Codification (Track A)
- [ ] **Add `Mockup File is Canonical (AuditDocSync Rule)` section** to `docs/rules-on-demand/frontend-mockup-fidelity.md`
  - DoD: New section between existing rule corpus and DoD; Sprint 57.45 case study referenced; cross-ref to `.claude/rules/sprint-workflow.md` §Step 2.5 Prong 2
  - Verify: `grep "AuditDocSync" docs/rules-on-demand/frontend-mockup-fidelity.md` → ≥1 match
- [ ] **MHist 1-line entry** on `frontend-mockup-fidelity.md`
  - DoD: Per `.claude/rules/file-header-convention.md` 1-line max + ≤100 char budget
  - Verify: Last MHist line ≤ E501

### 1.2 Task 2: TenantSettings Backend Schema Extension (Track B)
- [ ] **Alembic migration 0018** `backend/src/infrastructure/db/migrations/versions/0018_tenant_settings_extension.py`
  - DoD: `op.add_column()` for 5 columns (region/locale/retention_days/sso_enabled/seats) with defaults; backfill statement; down_revision='0017'; reversible down
  - Verify: `alembic upgrade head` succeeds locally; `alembic current` shows 0018
- [ ] **Tenant ORM extension** `backend/src/infrastructure/db/models/identity.py`
  - DoD: 5 typed `Mapped[T]` columns added with `mapped_column(server_default=...)`; mypy --strict 0 errors
  - Verify: `grep "region\|locale\|retention_days\|sso_enabled\|seats" identity.py` → 5 matches
- [ ] **TenantSettingsResponse Pydantic extension** `backend/src/api/v1/admin/tenants.py`
  - DoD: 5 new fields with type hints + defaults; PATCH input model also extended
  - Verify: `grep "region:\|locale:\|retention_days:\|sso_enabled:\|seats:" tenants.py` → 5+ matches
- [ ] **Admin PATCH endpoint extension** `tenants.py`
  - DoD: Accept 5 new optional fields; audit log entry per field change; admin role permission preserved
  - Verify: Read endpoint; trace fields → audit log
- [ ] **≥10 NEW pytest tests** `backend/tests/api/v1/admin/test_tenants_settings_extension.py`
  - DoD: GET defaults (5 cases) + PATCH each field (5 cases) + multi-tenant isolation (1 case) + invalid value 422 (3 cases) ≥10 total
  - Verify: `pytest test_tenants_settings_extension.py -v` → ≥10 PASSED
- [ ] **File headers updated** per convention (3 files: migration + ORM + API)
  - DoD: Each file has Purpose/Category/Created/MHist; MHist 1-line newest-first
  - Verify: Read each header
- [ ] **CHANGE record** `claudedocs/4-changes/feature-changes/CHANGE-XXX-tenant-settings-schema-extension.md`
  - DoD: Problem / Root cause / Solution / Verification / Impact sections
  - Verify: File exists; cross-ref AD-TenantSettings-Backend-Schema-Extension

### 1.3 Task 3: Mockup Capture Method Resolution (Track C)
- [ ] **Investigate** `frontend/scripts/mockup-sweep.mjs` current state + `reference/design-mockups/` directory structure
  - DoD: Document findings inline in Day 1 progress.md entry; choose Option A/B/C/D
  - Verify: Decision rationale logged
- [ ] **Implement chosen method** in `mockup-sweep.mjs`
  - DoD: Method works for at least 1 sample mockup PNG capture; inline rationale comment
  - Verify: `node frontend/scripts/mockup-sweep.mjs --target chat-v2` (or equivalent) produces PNG
- [ ] **Add §Mockup capture section** to `docs/rules-on-demand/frontend-mockup-fidelity.md`
  - DoD: Method + reproduction command + cross-ref to script
  - Verify: `grep "Mockup capture" frontend-mockup-fidelity.md` → ≥1 match
- [ ] **1 sanity PNG captured** + path noted
  - DoD: PNG file exists at `claudedocs/screenshots/mockup-<name>.png` or equivalent; size > 10 KB
  - Verify: `ls -lh` on target path
- [ ] **CHANGE record** `claudedocs/4-changes/feature-changes/CHANGE-XXX-mockup-capture-method.md`
  - DoD: Decision rationale (which option chosen + why) + reproduction guide
  - Verify: File exists; cross-ref AD-MockupCapture-Method-Resolution

### 1.4 Day 1 Validation Sweep
- [ ] **Backend lint chain**: `black backend/src backend/tests && isort backend/src backend/tests && flake8 backend/src backend/tests`
  - DoD: All 3 exit 0
  - Verify: `echo $?` after chain
- [ ] **Backend mypy --strict**: `mypy backend/src`
  - DoD: 0 errors
  - Verify: Output last line `Success: no issues found`
- [ ] **9 V2 lints**: `python scripts/lint/run_all.py`
  - DoD: 9/9 green
  - Verify: Exit 0; last line summary
- [ ] **Backend pytest**: target test added file + tenant module
  - DoD: ≥10 NEW PASSED; existing tests unchanged
  - Verify: `pytest backend/tests/api/v1/admin/ -v` → all PASSED
- [ ] **LLM SDK leak guard**: existing CI lint
  - DoD: 0 imports of `openai`/`anthropic` in `agent_harness/`
  - Verify: V2 lints includes this check

### 1.5 Day 1 commit
- [ ] Commit: `feat(sprint-57-46): Day 1 multi-domain implementation (3 tracks)`

---

## Day 2 — Closeout

### 2.1 24-route sweep + audit trail (Track B/C verification)
- [ ] **Frontend build sanity** (no frontend change expected; verify untouched)
  - DoD: `npm run build` in `frontend/` exit 0; no Vite build delta
  - Verify: Bundle size delta < 1 KB
- [ ] **24-route Playwright sweep** (per `route-sweep.mjs`)
  - DoD: 24 IDENTICAL or expected-noise only; 0 unintended regressions
  - Verify: `node frontend/scripts/route-sweep.mjs` exit 0
- [ ] **Multi-tenant isolation manual probe** (Task 2 specific)
  - DoD: tenant_a admin JWT cannot PATCH tenant_b settings (existing pattern; verify still holds)
  - Verify: 1 e2e test case OR manual curl with 2 JWTs

### 2.2 Retrospective
- [ ] **Write `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-46/retrospective.md`**
  - DoD: Q1-Q7 6 必答格式; ratio actual/committed-with-agent-factor computed; calibration assessment for `mixed-multidomain-bundle` 0.65 baseline + `agent_factor = 0.45` 1st validation
  - Verify: Read retro; 7 sections present
- [ ] **`agent_factor = 0.45` 1st validation data point** logged
  - DoD: Q4 section explicitly states ratio + rollback decision (KEEP 0.45 / tighten 0.35 / roll back 0.65 / Option B split)
  - Verify: Q4 reads ratio + decision

### 2.3 Sprint-workflow.md updates (calibration matrix)
- [ ] **Add NEW class row** `mixed-multidomain-bundle` 0.65 1-data-point baseline
  - DoD: 1 row added to `.claude/rules/sprint-workflow.md` §Scope-class multiplier matrix
  - Verify: Read matrix
- [ ] **Update §Active Agent Delegation Factor Modifier** §Activation history with Sprint 57.46 1st validation entry
  - DoD: New history entry per 57.43+57.44+57.45 pattern; ratio + decision
  - Verify: Read history section last 5 entries

### 2.4 Memory subfile + MEMORY.md index
- [ ] **Write `memory/project_phase57_46_multi_domain_bundle.md`**
  - DoD: Sprint scope / 3 task closures / ratio / calibration / carryover ADs
  - Verify: File exists
- [ ] **Add MEMORY.md pointer entry**
  - DoD: 1 entry (~250-300 char) — subfile link + 1-sentence topic + keywords
  - Verify: Top of Recent Sprints list

### 2.5 CLAUDE.md Current Sprint row update
- [ ] **Update Current Sprint row** to Sprint 57.46 closed + 1-line goal
  - DoD: Only Current Sprint row + Last Updated footer (per `.claude/rules/sprint-workflow.md` §Sprint Closeout policy NAVIGATOR-ONLY rule)
  - Verify: No new history rows added; no per-sprint detail packed

### 2.6 PR + merge
- [ ] **Push branch + open PR** with description containing 3 AD closures + ratio + calibration
- [ ] **Wait CI green** (backend-ci + V2 Lint)
- [ ] **Merge PR** (squash)
- [ ] **Cleanup**: delete local feature branch

### 2.7 Final
- [ ] **Day 2 commit**: `chore(sprint-57-46): Day 2 retro + memory + closeout`
- [ ] **All checklist items above**: `[x]` (or 🚧 with reason if deferred)

---

**Modification History**:
- 2026-05-26: Sprint 57.46 Day 0.1 — Initial draft (3-AD multi-domain bundle; Day 0/1/2 structure mirrors Sprint 57.39 + 57.44 templates)
