# Sprint 55.6 — Checklist

[Plan](./sprint-55-6-plan.md)

> **Note**: Per **AD-Lint-2** (Sprint 55.3), per-day "Estimated X hours" headers dropped from this template. Sprint-aggregate estimate in plan §Workload only. Day-level actuals → progress.md.
>
> Per **AD-Plan-2** (Sprint 55.3), every plan §File Change List entry was Day-0 path-verified (Glob-checked exists for edits / not-exist for creates).
>
> Per **AD-Plan-3 second application** (Sprint 55.6 — promoted to validated rule via this sprint's AD-Plan-3-Promotion fold-in), Day-0 探勘 ALSO greps plan-asserted code patterns within existing files. **5 wrong-content drifts caught at Day 0 (D1-D5)** — including **D3 critical scope reduction** (AD-Cat8-2 from ~11 hr "design + wire" to ~5-6 hr "wire-only").

---

## Day 0 — Setup + Day-0 探勘 + Plan/Checklist Drafting

- [x] **Working tree clean verified on main `d3876ff1`**
  - DoD: `git status --short` returns empty
- [x] **Feature branch created**
  - Branch: `feature/sprint-55-6-cat8-2-retry-group-h-process-ad-pair`
- [x] **Day-0 探勘 grep (AD-Plan-1 + AD-Plan-2 + AD-Plan-3 second application)**
  - 5 grep + 2 Glob covering 4 backend/infra ADs + 2 process ADs
  - **AD-Plan-3 content-keyword grep catches**:
    - **D1**: `loop.py:194-247` retry_policy attribute confirmed dead (constructor accepts + assigns `self._retry_policy = retry_policy` but 0 references in loop body) — confirms 55.4 D6 partial finding
    - **D2**: `RetryPolicyMatrix` class exists at `agent_harness/error_handling/retry.py:85` (53.2 implementation) — wire-only scope, no design from scratch
    - **D3 (CRITICAL CATCH)**: 55.4 retro Q4 + 55.5 retro Q4 narrative said "AD-Cat8-2 needs full retry-with-backoff design" implying broad Cat 8 dead. Day-0 探勘 reveals: `_handle_tool_error` IS implemented at L259+ AND IS called from main tool execution at L1049 + L1095; `_error_policy.classify*()` + `_error_budget.record()` + `_circuit_breaker` ALL wired. **ONLY `_retry_policy` is the dead attribute**. → AD-Cat8-2 scope drops from ~10-12 hr to ~5-6 hr (wire-only). Total sprint commitment drops from ~15.3 hr (Option A original) to ~12 hr.
    - **D4**: `.github/workflows/` has 6 workflows (`backend-ci.yml`, `frontend-ci.yml`, `lint.yml`, `e2e-tests.yml`, `deploy-production.yml`, `playwright-e2e.yml`); `deploy-production.yml` has health-check `exit 1` logic at L178/L192/L223 — AD-CI-6 chronic fail likely from health checks against non-existent V2 prod infra
    - **D5**: `.claude/rules/sprint-workflow.md` already has §Step 2.5 (L120) — AD-Plan-3-Promotion = extend in-place to add content-verify task as parallel mandatory; `file-header-convention.md` §格式 already enforces 1-line MHist (AD-Lint-3) — AD-Lint-MHist-Verbosity = add char-count budget guidance
- [x] **Read Sprint 55.5 plan template**
  - 13 sections / Day 0-4 confirmed; 55.6 expands to Day 0-5 (6 days) per Option A user approval
- [x] **Write `sprint-55-6-plan.md`**
  - 13 sections mirror 55.5
  - 4 backend/infra ADs (Cat8-2 + AD-CI-5 + AD-CI-6) + 2 process ADs (AD-Plan-3-Promotion + AD-Lint-MHist-Verbosity) detailed
  - 2 process AD applications (AD-Plan-3 second app + AD-Sprint-Plan-5 second app) explicit
- [x] **Write `sprint-55-6-checklist.md`** (this file)
- [x] **Write Day 0 `progress.md` entry**
  - Path: `docs/03-implementation/agent-harness-execution/phase-55/sprint-55-6/progress.md`
- [ ] **Commit Day 0** (plan + checklist + progress)
  - Commit: `chore(docs, sprint-55-6): Day 0 plan + checklist + progress + 5 探勘 drift catalogue (AD-Plan-3 2nd app)`
- [ ] **Push branch**

---

## Day 1 — AD-Cat8-2 Implementation Part 1 (ToolErrorDecision extend + _handle_tool_error wire)

### Day 1 Pre-code reading (~20 min) — AD-Plan-3 third application within sprint

- [ ] **Read `backend/src/agent_harness/error_handling/_abc.py`** — confirm `ToolErrorDecision` + `ToolErrorAction` enum exist; check if RETRY action already defined (53.2 implementation)
  - Drift catch potential: if RETRY already exists, scope shrinks; if missing, scope as planned
- [ ] **Read `backend/src/agent_harness/error_handling/retry.py:85+`** — confirm `RetryPolicyMatrix.should_retry()` signature
  - Verify return type (decision dataclass / tuple / bool)
  - Verify input params (error_class / tool_name / attempt)
- [ ] **Read `backend/src/agent_harness/orchestrator_loop/loop.py:259-340`** (full `_handle_tool_error` body)
  - Identify wire-in point (after `error_budget.record`, before terminator)
- [ ] **Read `backend/src/agent_harness/orchestrator_loop/loop.py:1040-1100`** (tool execution call sites)
  - Identify retry loop wrap target
- [ ] **Read `backend/src/agent_harness/error_handling/__init__.py`** — confirm public re-exports

### AD-Cat8-2 Part 1 — Implementation

- [ ] **Extend `ToolErrorDecision` + `ToolErrorAction` in `_abc.py`** (if RETRY missing)
  - Add `RETRY = "retry"` to `ToolErrorAction` enum
  - Extend `ToolErrorDecision` with `backoff_seconds: float = 0.0` + `attempts_remaining: int = 0`
  - Default values preserve backwards-compat for existing callers
  - File header MHist 1-line per AD-Lint-3
- [ ] **Extend `_handle_tool_error` body in `loop.py:259+`**
  - Add `attempt: int = 0` parameter (default 0; backwards-compat)
  - After `error_budget.record(...)` line: consult `self._retry_policy` if not None
  - Translate `RetryPolicyMatrix.should_retry(...)` decision into `ToolErrorDecision(action=RETRY, backoff_seconds=..., attempts_remaining=...)`
  - Fall through to existing terminator logic if retry not applicable
  - File header MHist 1-line
- [ ] **Lint chain**: black + isort + flake8 + mypy --strict + 7 V2 lints
- [ ] **LLM SDK leak check**: 0
- [ ] **Update Day 1 progress.md** entry — actual hours / drift findings (D6+ if any)
- [ ] **Commit Day 1**
  - Commit: `feat(orchestrator-loop, sprint-55-6): wire RetryPolicyMatrix into _handle_tool_error per AD-Cat8-2 (Part 1: ABC + body)`
- [ ] **Push branch**

---

## Day 2 — AD-Cat8-2 Implementation Part 2 (call site retry wrap + tests)

### Day 2 Pre-code reading (~10 min)

- [ ] **Re-read `loop.py:1049` + `loop.py:1095`** tool execution call sites — finalize retry loop wrap pattern
- [ ] **Check existing retry test fixtures** in `backend/tests/unit/agent_harness/orchestrator_loop/` for reusable mock patterns

### AD-Cat8-2 Part 2 — Call site wrap + Tests

- [ ] **Edit `loop.py:1049`** — wrap tool execution with retry loop consuming `ToolErrorDecision.action == RETRY`
- [ ] **Edit `loop.py:1095`** — same retry wrap pattern
- [ ] **Create `backend/tests/unit/agent_harness/orchestrator_loop/test_retry_policy_wire.py`** (NEW; 6-8 unit tests)
  - test_retry_on_transient_succeeds_after_one_retry
  - test_retry_exhausted_falls_through_to_terminator
  - test_retry_disabled_when_retry_policy_is_none (backwards-compat)
  - test_backoff_timing_calls_asyncio_sleep_with_correct_value (mock asyncio.sleep)
  - test_error_class_not_retryable_skips_retry_path
  - test_attempt_counter_increments_correctly
  - test_retry_decision_no_action_passes_through (RETRY decision with attempts_remaining=0 falls through)
  - (optional 8th) test_retry_with_circuit_breaker_open_skips_retry (interaction with circuit breaker)
  - DoD: 6-8/6-8 PASS ✅
- [ ] **Create `backend/tests/integration/agent_harness/test_loop_retry_integration.py`** (NEW or extend existing)
  - test_full_agent_loop_retry_with_flaky_tool_fixture (deterministic flaky tool that succeeds on attempt 2)
  - DoD: 1/1 PASS ✅

### Day 2 Wrap

- [ ] **Run pytest** — 6-8 unit (test_retry_policy_wire) + 1 integration (test_loop_retry_integration) + loop regression + full pytest target ≥1461
- [ ] **Lint chain**: black + isort + flake8 + mypy --strict + 7 V2 lints
- [ ] **LLM SDK leak check**: 0
- [ ] **Update Day 2 progress.md** entry — actual hours / drift findings
- [ ] **Commit Day 2**
  - Commit: `feat(orchestrator-loop, sprint-55-6): close AD-Cat8-2 (Part 2: tool execution retry wrap + 6-8 unit + 1 integration)`
- [ ] **Push branch**

---

## Day 3 — Group H CI/infra (AD-CI-5 paths-filter long-term + AD-CI-6 deploy-production disable)

### Day 3 Pre-code reading (~15 min)

- [ ] **Read `.github/workflows/backend-ci.yml`** — paths filter rules
- [ ] **Read `.github/workflows/playwright-e2e.yml`** — paths filter rules
- [ ] **Read `.github/workflows/deploy-production.yml`** — full file to understand disable surface
- [ ] **`gh api GET /repos/laitim2001/ai-semantic-kernel-framework-project/branches/main/protection`** — read current `required_status_checks.contexts` exact strings
  - DoD: capture all 5 current required check names verbatim

### AD-CI-5 — Aggregator Workflow

- [ ] **Create `.github/workflows/required-checks-aggregator.yml`** (NEW)
  - Aggregator job that always runs (no paths filter)
  - File header explaining AD-CI-5 long-term fix rationale
- [ ] **Test aggregator on this PR** — push + watch CI to confirm aggregator job appears + passes

### AD-CI-5 — Branch Protection PATCH

- [ ] **`gh api PATCH`** to add `All required checks` (aggregator job name) to `required_status_checks.contexts`
  - Capture full PATCH command in commit body for audit trail
  - Keep existing 5 contexts (don't remove; additive)
- [ ] **Verify** via `gh api GET` that aggregator is in contexts
- [ ] **Document** in commit body: what changed + before/after contexts

### AD-CI-6 — deploy-production Disable

- [ ] **Edit `deploy-production.yml`** — add `if: false` to all jobs OR change `on:` to `workflow_dispatch` only
  - Add re-enable criteria comment in file header (Azure App Service provisioned + Secrets configured + smoke-test gate)
  - Update workflow `name:` to `Deploy to Production (DISABLED — see AD-CI-6)`

### Day 3 Wrap

- [ ] **No new touch-header on backend-ci.yml / playwright-e2e.yml** (this sprint's PR is the LAST one needing those if AD-CI-5 lands successfully)
- [ ] **Lint chain** (sanity for YAML syntax via existing GH Actions parser)
- [ ] **Update Day 3 progress.md** entry — actual hours / drift findings (D6+ if branch protection schema differs)
- [ ] **Commit Day 3**
  - Commit: `chore(ci, sprint-55-6): close AD-CI-5 (aggregator workflow) + AD-CI-6 (deploy-production disable)`
  - Body: include `gh api PATCH` command + before/after contexts
- [ ] **Push branch**

---

## Day 4 — Process AD pair fold-in + Buffer

### Day 4 Pre-code reading (~10 min)

- [ ] **Read `.claude/rules/sprint-workflow.md` §Step 2.5** (around L120; full section)
- [ ] **Read `.claude/rules/file-header-convention.md` §格式** (locate via Grep)
- [ ] **Read `.claude/rules/anti-patterns-checklist.md` AP-2** (cross-reference target)

### AD-Plan-3-Promotion — Edit sprint-workflow.md

- [ ] **Extend §Step 2.5** in `.claude/rules/sprint-workflow.md`:
  - Add sub-section "Path Verify (AD-Plan-2 from 55.3)" — existing content
  - Add sub-section "Content Verify (AD-Plan-3 promoted in 55.6)" — NEW
  - Add ROI evidence sub-section: 55.5 first application 5 wrong-content drifts; 55.6 second application 5 drifts (D1-D5) including D3 critical scope reduction
  - Add "How to apply" sub-section with grep query patterns:
    - Claimed-but-unwired entry points: `grep "self\._{attribute}\b" {target_file}` to count call sites vs assignments
    - Claimed-but-missing imports: `grep "import {symbol}\|from .* import .*{symbol}" {target_dir}` to verify
    - Claimed-but-renamed symbols: `grep "{old_name}\|{new_name}" {target_dir}` to detect rename drift
  - Cross-reference from AP-2 + file-header-convention.md
  - File header MHist 1-line per AD-Lint-3

### AD-Lint-MHist-Verbosity — Edit file-header-convention.md

- [ ] **Extend §格式 MHist guidance** in `.claude/rules/file-header-convention.md`:
  - Add char-count budget reminder (≤ E501 = 100 chars including indent / blockquote prefix)
  - Add common-case templates with char counts
  - Add anti-pattern bullets:
    - "Don't pack 4-clause reasons in MHist; move to commit message body"
    - "Don't pack full sprint reference + AD ID + reason in single line; compress AD ID format"
  - Cross-reference 55.4 + 55.5 evidence in §Modification History of file-header-convention.md itself
  - File header MHist 1-line per existing AD-Lint-3 (self-validation)

### Day 4 Wrap + Buffer

- [ ] **Self-validate edits**: re-read both files end-to-end; ensure no inconsistency between sprint-workflow.md and file-header-convention.md
- [ ] **Lint chain** (docs-only edits should be neutral; mypy/black/etc skip Markdown)
- [ ] **Buffer time use**:
  - If Day 1-3 had overflow → absorb here
  - Else → SITUATION-V2-SESSION-START.md §8 pre-update + memory file pre-draft
- [ ] **Update Day 4 progress.md** entry — actual hours
- [ ] **Commit Day 4**
  - Commit: `docs(rules, sprint-55-6): close AD-Plan-3-Promotion + AD-Lint-MHist-Verbosity (process AD pair fold-in)`
- [ ] **Push branch**

---

## Day 5 — Retrospective + Closeout

- [ ] **Verify all 5 ADs closed** (acceptance criteria) ✅
  - AD-Cat8-2: retry wire + 6-8 unit + 1 integration tests green
  - AD-CI-5: aggregator workflow + branch protection PATCH verified
  - AD-CI-6: deploy-production disabled with re-enable criteria
  - AD-Plan-3-Promotion: sprint-workflow.md §Step 2.5 extended
  - AD-Lint-MHist-Verbosity: file-header-convention.md §格式 extended
- [ ] **Run full pytest baseline** → target 1454 → ≥1462 (cumulative +8)
- [ ] **Run full lint chain** → black + isort + flake8 + mypy --strict + 7 V2 lints all green
- [ ] **LLM SDK leak check** — 0
- [ ] **Compute calibration ratio** (AD-Sprint-Plan-5 medium-backend 0.85 second application)
- [ ] **Verify AD-CI-5 effectiveness**: confirm THIS PR's required checks all pass via aggregator route (no touch-header on backend-ci.yml or playwright-e2e.yml needed for THIS PR)
- [ ] **Catalog final drift findings** (D1-Dn)
- [ ] **Write `retrospective.md`** (6 必答 Q1-Q6 + sign-off)
  - Q1 What went well (highlight AD-Plan-3 second app validation + D3 critical catch)
  - Q2 What didn't go well + calibration ratio
  - Q3 Generalizable lessons (D3 catch + scope adjustment via plan revision commit)
  - Q4 Audit Debt deferred (carryover candidates for 55.7+)
  - Q5 Next steps (rolling planning candidate scope only)
  - Q6 AD-Sprint-Plan-5 second application + AD-Plan-3-Promotion ratification
- [ ] **Update `SITUATION-V2-SESSION-START.md`** (§8 close 5 ADs / §9 +Sprint 55.6 row + 累計 / footer + history row)
- [ ] **Update memory** (`project_phase55_6_audit_cycle_4.md` NEW + `MEMORY.md` +1 line)
- [ ] **Commit Day 5**
  - Commit: `docs(retro, sprint-55-6): retrospective + 5 AD closure summary + AD-Plan-3 2nd app validation + AD-CI-5 paths-filter retired`
- [ ] **Push branch**
- [ ] **Open PR**
  - Title: `Sprint 55.6: Audit Cycle Mini-Sprint #4 — close AD-Cat8-2 + AD-CI-5 + AD-CI-6 + Process AD pair`
- [ ] **Watch CI green** — if AD-CI-5 working: aggregator passes + paths-filtered jobs report independently; if not yet: ONE LAST touch-header on backend-ci.yml + playwright-e2e.yml as transitional workaround
- [ ] **Merge PR** — solo-dev policy, review_count=0
- [ ] **Closeout PR for SHA fill-in** (SITUATION §9 PR # + SHA + memory file SHA fill-in + branch protection PATCH evidence in PR description)
- [ ] **Final verify on main** — clean

---

## Tracker

| AD | Status | Tests Added | Commit |
|----|--------|-------------|--------|
| AD-Cat8-2 | ⏳ Day 1-2 (D3 wire-only scope) | 6-8 unit + 1 integration | Day 1+2 commits |
| AD-CI-5 | ⏳ Day 3 (aggregator + PATCH) | — (CI infra) | Day 3 commit |
| AD-CI-6 | ⏳ Day 3 (disable + re-enable criteria) | — (CI infra) | Day 3 commit |
| AD-Plan-3-Promotion | ⏳ Day 4 (sprint-workflow.md §Step 2.5 extend) | — (process AD) | Day 4 commit |
| AD-Lint-MHist-Verbosity | ⏳ Day 4 (file-header-convention.md §格式 extend) | — (process AD) | Day 4 commit |
| AD-Plan-3 second app (process; via fold-in) | ⏳ Day 0/1/2/3/4 ROI tracking | — (process AD) | embedded in Day 0-4 commits |
| AD-Sprint-Plan-5 second app (process; mult 0.85) | ⏳ Day 5 calibration | — (process AD) | Day 5 retro |
| **Total** | **5/5 backend+infra+process target** | **+8 target (1454 → ≥1462)** | — |

---

**Status**: Day 0 — Plan + Checklist drafted. Day 0 progress.md + commit pending. Pending user approval before Day 1 code starts.
