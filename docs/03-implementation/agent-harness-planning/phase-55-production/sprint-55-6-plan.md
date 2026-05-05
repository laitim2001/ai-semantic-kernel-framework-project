# Sprint 55.6 — Plan

**Sprint**: 55.6
**Phase**: 55 (V2 Production / Audit Cycle)
**Type**: Audit Cycle Mini-Sprint #4 (combined: Cat 8 retry-with-backoff dedicated + Group H CI/infra + Process AD pair fold-in)
**Branch**: `feature/sprint-55-6-cat8-2-retry-group-h-process-ad-pair`
**Start Date**: 2026-05-05
**Target End Date**: 2026-05-10 (6 days, Day 0-5 — expanded from 5-day standard per Option A user approval 2026-05-05)
**Plan Format Template**: Sprint 55.5 (13 sections / Day-by-Day; expanded Day 0-5 vs 55.5 Day 0-4)
**Status**: Day 0 — pending user approval before Day 1 code starts

> **Note**: Per **AD-Lint-2** (Sprint 55.3), per-day "Estimated X hours" headers dropped from checklist template. Sprint-aggregate estimate in §Workload only. Day-level actuals → progress.md.
>
> Per **AD-Plan-2** (Sprint 55.3), every plan §File Change List entry was Day-0 path-verified.
>
> Per **AD-Plan-3 second application** (Sprint 55.6 — promoted from candidate to validated rule via this sprint's AD-Plan-3-Promotion fold-in), Day-0 探勘 ALSO greps plan-asserted code patterns within existing files. **5 drifts caught at Day 0 (D1-D5)** — including **D3 critical catch** that scoped down AD-Cat8-2 from ~11 hr "design + wire" to ~5-6 hr "wire-only".

---

## Sprint Goal

Wire `RetryPolicyMatrix` into `AgentLoop._handle_tool_error` body to close AD-Cat8-2 (medium-backend dedicated work), apply long-term fixes for Group H CI/infra ADs (AD-CI-5 paths-filter strategy + AD-CI-6 deploy-production chronic fail), and fold in process AD pair (AD-Plan-3-Promotion + AD-Lint-MHist-Verbosity) — closing 4 backend ADs + 2 process AD applications in audit cycle Mini-Sprint #4 expanded scope (Option A approved by user 2026-05-05).

---

## Background

V2 22/22 (100%) closure achieved at Sprint 55.2 (2026-05-04). Phase 55+ enters audit cycle phase that systematically closes Audit Debts accumulated during V2 build phases (49-55):

- **53.2.5** = CI carryover bundle
- **53.7** = audit cleanup (9 ADs closed)
- **55.3** = Mini-Sprint #1 (Groups A + G — Cat 7 lint + Cat 12 helper + Hitl-7) — 6 ADs closed
- **55.4** = Mini-Sprint #2 (Groups B + C — Cat 8 + Cat 9 backend) — 4 ADs closed (AD-Cat8-2 deferred)
- **55.5** = Mini-Sprint #3 narrow (Group D — Cat 10 backend audit) — 2 ADs closed (AD-Cat10-Wire-1 + AD-Cat10-Obs-Cat9Wrappers)
- **55.6** (this sprint) = Mini-Sprint #4 expanded (Cat 8 retry-policy + Group H CI/infra + Process AD pair)

**Combined scope rationale (Option A user-approved 2026-05-05)**:
1. **AD-Cat8-2** (primary, medium-backend dedicated): retry-with-backoff wire — D3 catch revealed it's wire-only not design-from-scratch (see §Audit Debt Items)
2. **Group H CI/infra** (secondary, infra-track): AD-CI-5 paths-filter long-term fix + AD-CI-6 deploy-production chronic fail — both have been carried since Sprint 53.2 with documented workarounds; Option A bundles them while Cat 8 sprint is open
3. **Process AD pair** (tertiary, ~45 min): AD-Plan-3-Promotion (sprint-workflow.md §Step 2.5 extension) + AD-Lint-MHist-Verbosity (file-header-convention.md §格式 trim) — natural fold-in since both edit-target files are touched by every sprint

This sprint also serves as:
- **Second application of AD-Plan-3** (now promoted to validated rule via fold-in) — 5 wrong-content drifts caught at Day 0 (D1-D5) including D3 critical scope reduction
- **Second application of AD-Sprint-Plan-5** medium-backend multiplier — KEEP 0.80 per 55.5 retro Q6 recommendation #1 (don't over-iterate after single in-band data point); + audit-cycle-overhead surcharge 0.05 (this sprint includes Process AD pair work + Group H infra investigation)

---

## Audit Debt Items

### AD-Cat8-2 — Wire RetryPolicyMatrix into Loop Body (medium-backend primary)

**Origin**: 53.2 retrospective Q5 (Cat 8 carryover); deferred 55.4 via D6 + Selection D; deferred 55.5 (scope mismatch with Cat 10 audit)
**Severity**: ⚠️ Medium — RetryPolicyMatrix is fully implemented (53.2) but the AgentLoop's `_retry_policy` attribute is dead state; tool errors are classified + recorded but never auto-retried
**Day-0 探勘 finding (D1+D2+D3 — AD-Plan-3 second application; D3 = critical scope reduction)**:
- **D1**: `loop.py:195` constructor accepts `retry_policy: RetryPolicyMatrix | None = None`; `loop.py:246` assigns `self._retry_policy = retry_policy` — but **0 references** to `self._retry_policy` anywhere in loop body (confirmed via grep)
- **D2**: `RetryPolicyMatrix` class exists at `agent_harness/error_handling/retry.py:85` (53.2 implementation) — public API with `should_retry()` + backoff logic — wire-only scope, no design from scratch
- **D3 (CRITICAL CATCH)**: 55.4 retro Q4 + 55.5 retro Q4 narrative said "AD-Cat8-2 needs full retry-with-backoff design" implying Cat 8 broadly dead. Day-0 探勘 reveals: `_handle_tool_error` IS implemented (loop.py:259) and IS called from main tool execution (loop.py:1049 + L1095); `_error_policy.classify*()` + `_error_budget.record()` + `_circuit_breaker` ALL wired. **ONLY `_retry_policy` is the dead attribute**. → Scope drops from "full design + wire" (~10-12 hr) to "wire-only" (~5-6 hr).

**Acceptance**:
- `_handle_tool_error` body extended: after `error_policy.classify()` + `error_budget.record()` lines, consult `self._retry_policy` (if not None) to determine retry action
- Wire returns retry decision tuple `(should_retry: bool, backoff_seconds: float, attempts_remaining: int)` to caller
- Caller at `loop.py:1049` + `loop.py:1095` consumes retry decision; if retry → `await asyncio.sleep(backoff_seconds)` then re-execute tool call; if max_attempts exceeded → fall through to existing error_policy terminator path
- Per-tool retry attempt counter (in-loop transient state, not persisted)
- 6-8 unit tests covering: retry-on-transient (success after 1 retry), retry-exhausted (max attempts hit, falls through), retry-disabled (RetryPolicyMatrix=None preserves existing behavior), backoff timing assertion (mock asyncio.sleep), error-class-not-retryable (skip retry path)
- 1 integration test (full AgentLoop run with deterministic flaky-tool fixture)
- Backwards-compatible: production default `retry_policy=None` → wrapper no-op (existing behavior preserved byte-for-byte)
- 17.md §Cat 8 contracts unchanged (no new ABC, no schema change; pure wire-up of existing 53.2 RetryPolicyMatrix)

### AD-CI-5 — Paths-filter Long-term Fix (Group H secondary)

**Origin**: 53.2.5 retrospective; carried via touch-header workaround through 53.7 / 54.1 / 54.2 / 55.1 / 55.2 / 55.3 / 55.4 / 55.5 (8 sprints accumulated touch-header noise on backend-ci.yml + playwright-e2e.yml)
**Severity**: 🟡 Low-Medium — current touch-header workaround works but accumulates per-sprint header noise; long-term unsustainable
**Day-0 探勘 finding (D4)**: 6 workflows in `.github/workflows/` (`backend-ci.yml` / `frontend-ci.yml` / `lint.yml` / `e2e-tests.yml` / `deploy-production.yml` / `playwright-e2e.yml`); paths-filter rules in backend-ci.yml + playwright-e2e.yml are causing required-status-checks to not fire on docs-only / cross-area PRs

**Acceptance**:
- Decision: **Option Y (recommended)** — split required CI workflows into two layers:
  - **Always-run aggregator job** (no paths filter; runs on every PR) — passes if downstream paths-filtered jobs pass OR are skipped
  - **Paths-filtered domain jobs** (existing backend-ci / playwright-e2e) — runs only when relevant paths changed
  - Required-status-check points to the aggregator, not the domain jobs
  - Removes need for touch-header workaround
- Implement aggregator workflow `.github/workflows/required-checks-aggregator.yml`
- Update branch protection `required_status_checks` contexts (1-line `gh api` PATCH; documented + commit-message-recorded for audit)
- Verify on a docs-only PR that aggregator passes without touching backend-ci.yml header
- Document touch-header history archive: backend-ci.yml + playwright-e2e.yml header comments stay (history reference) but no new touches needed going forward

### AD-CI-6 — Deploy to Production Chronic Fail Investigation (Group H secondary)

**Origin**: 53.2 retrospective; carried as non-blocking infra track since deploy-production.yml is not in `required_status_checks` (failures don't block PR merges) but accumulates noisy red checks since 2026-05-03
**Severity**: 🟢 Low — non-blocking, no production deployment dependency on this workflow today (V2 not deployed; pre-launch)
**Day-0 探勘 finding (D4)**: `deploy-production.yml` has health-check `exit 1` logic (L178+L192+L223+L224); root cause likely (a) Azure App Service not provisioned for V2 yet OR (b) blue-green slot swap targets resources that don't exist
**Acceptance**:
- Decision: **Option Z (recommended)** — temporarily disable workflow (rename to `.disabled` extension OR add `if: false` to all jobs) until V2 launch infrastructure is provisioned, with explicit comment + tracking issue link
- Document workflow re-enable criteria in workflow header comment (Azure App Service provisioned + secrets configured + smoke-test stage gated)
- Optionally: convert to manual-trigger only (`workflow_dispatch`) instead of automatic-on-push
- Final state: workflow stops contributing red checks to PR view; chronic noise removed

### AD-Plan-3-Promotion — Promote AD-Plan-3 from Candidate to Validated Rule (Process AD; tertiary)

**Origin**: 55.5 retrospective Q6 — first application caught 5 wrong-content drifts (ROI 4-8×; ~55 min cost prevented ~3-4 hr re-work)
**Severity**: 🟢 Low (process AD; ~30 min)
**Day-0 探勘 finding (D5)**: `.claude/rules/sprint-workflow.md` already has §Step 2.5 (header at L120) — extend in-place to add content-keyword grep as required Day-0 task

**Acceptance**:
- Edit `.claude/rules/sprint-workflow.md` §Step 2.5: extend the existing "Day-0 Plan-vs-Repo Verify" section to enumerate two parallel verifications:
  1. **Path verify (AD-Plan-2 from 55.3)**: every File Change List entry → Glob exists/not-exists
  2. **Content verify (AD-Plan-3 promoted in 55.6)**: every plan §Spec / §Background factual claim about existing code → Grep for the asserted symbol/pattern
- Add ROI evidence sub-section (55.5 first application 5 wrong-content drifts caught; promotion criteria met)
- Add "How to apply" sub-section: list of Grep query patterns for common drift classes (claimed-but-unwired entry points / claimed-but-missing imports / claimed-but-renamed symbols)
- Cross-reference from `.claude/rules/anti-patterns-checklist.md` AP-2 (no orphan code)
- Cross-reference from `.claude/rules/file-header-convention.md` (drift findings in MHist)

### AD-Lint-MHist-Verbosity — Trim Default MHist Verbosity (Process AD; tertiary)

**Origin**: 55.5 retrospective Q6 — 2 consecutive sprints (55.4 + 55.5) had new MHist entries exceeding E501 by 1-3 chars on first draft (recurring pattern)
**Severity**: 🟢 Low (process AD; ~15 min)
**Day-0 探勘 finding (D5)**: `.claude/rules/file-header-convention.md` already has §格式 with 1-line MHist constraint (AD-Lint-3 Sprint 55.3) — extend with char-count writing guidance

**Acceptance**:
- Edit `.claude/rules/file-header-convention.md` §格式: add char-count budget section to MHist guidance:
  - Effective budget reminder (≤ E501 = 100 chars including indent / blockquote prefix)
  - Common-case templates with char counts (e.g., `- YYYY-MM-DD: <verb> <scope> — <reason>` ≈ 60-70 chars)
  - Patterns that frequently exceed: full sprint reference + AD ID + reason in single line → split or compress
- Add anti-pattern bullets: "Don't pack 4-clause reasons in MHist; move to commit message body / FIX-XXX file / 4-changes record"
- Cross-reference 55.4 + 55.5 evidence in §Modification History of file-header-convention.md itself
- 55.6 retrospective Q3 should validate: did Day 1-5 MHist entries fit budget on first draft? (≥ 80% target)

### Process AD applications (apply during this sprint, not closed)

**AD-Plan-3 second application** (now validated by AD-Plan-3-Promotion fold-in):
- Day-0 探勘 grep: 5 grep + 2 Glob covering 4 backend/infra ADs + 2 process ADs
- 5 wrong-content drifts caught at Day 0 (D1-D5) — including **D3 critical scope reduction**
- ROI: ~30 min Day 0 cost prevented ~3 hr mid-Day-1 re-work + ~3 hr scope-creep work that wasn't actually needed
- Document outcome in retro Q1 + Q3 for promotion validation

**AD-Sprint-Plan-5 second application** (medium-backend multiplier confirmation):
- Apply medium-backend multiplier 0.80 (KEEP per 55.5 retro Q6 #1)
- Apply audit-cycle-overhead surcharge +0.05 (this sprint has Process AD pair + Group H infra investigation overhead) → **0.85**
- Apply Day 0 fixed offset (~2 hr) excluded from bottom-up est
- Document calibration in retro Q2 + Q6 for matrix iteration; 7-sprint window check

---

## Technical Specifications

### AD-Cat8-2 Implementation (D3-scoped wire-only)

**File**: `backend/src/agent_harness/orchestrator_loop/loop.py` (edit `_handle_tool_error` body L259+ and tool execution sites L1049 + L1095)

```python
# Sprint 55.6 — wire RetryPolicyMatrix into _handle_tool_error per AD-Cat8-2
# (D3-scoped: existing 53.2 RetryPolicyMatrix is plug-in, not design-from-scratch)

# In _handle_tool_error (after error_policy.classify + error_budget.record):
async def _handle_tool_error(
    self,
    *,
    error: BaseException | None = None,
    error_class_str: str | None = None,
    tool_call_id: str,
    tool_name: str,
    attempt: int = 0,  # NEW: per-tool retry attempt counter (transient)
) -> ToolErrorDecision:
    # ... existing classify + budget.record code ...

    # NEW: consult retry_policy if present
    if self._retry_policy is not None:
        decision = self._retry_policy.should_retry(
            error_class=cls,
            tool_name=tool_name,
            attempt=attempt,
        )
        if decision.should_retry:
            return ToolErrorDecision(
                action=ToolErrorAction.RETRY,
                backoff_seconds=decision.backoff_seconds,
                attempts_remaining=decision.attempts_remaining,
            )

    # ... existing terminator / fall-through code ...
```

```python
# In tool execution sites (loop.py:1049 + L1095) — wrap with retry loop:
attempt = 0
while True:
    try:
        result = await tool_executor.execute(...)
        if result.success:
            break
        decision = await self._handle_tool_error(
            error_class_str=result.error_class,
            tool_call_id=tc.id,
            tool_name=tc.name,
            attempt=attempt,
        )
    except BaseException as e:
        decision = await self._handle_tool_error(
            error=e,
            tool_call_id=tc.id,
            tool_name=tc.name,
            attempt=attempt,
        )
    if decision.action != ToolErrorAction.RETRY:
        break
    attempt += 1
    await asyncio.sleep(decision.backoff_seconds)
```

**File**: `backend/src/agent_harness/error_handling/_abc.py` (extend `ToolErrorDecision` dataclass)

```python
class ToolErrorAction(Enum):
    TERMINATE = "terminate"  # existing
    RETRY = "retry"  # NEW (Sprint 55.6)
    SKIP = "skip"  # existing

@dataclass(frozen=True)
class ToolErrorDecision:
    action: ToolErrorAction
    backoff_seconds: float = 0.0  # NEW
    attempts_remaining: int = 0  # NEW
    # ... existing fields ...
```

> **Note**: confirm 53.2 `_abc.py` already exposes `ToolErrorDecision` and `ToolErrorAction` enum. If not, scope adjusts in Day 1 morning to add them.

### AD-CI-5 Implementation (paths-filter long-term)

**File**: `.github/workflows/required-checks-aggregator.yml` (NEW)

```yaml
# Sprint 55.6 — aggregator workflow per AD-CI-5 long-term fix
# Replaces touch-header workaround pattern accumulated since 53.2.5

name: Required Checks Aggregator

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  aggregate:
    name: All required checks
    runs-on: ubuntu-latest
    steps:
      - name: Mark this PR/push as ready for required-status-check
        run: echo "Aggregator passed; downstream domain jobs (backend-ci / playwright-e2e / v2-lints / Frontend E2E) report independently."
```

**File**: branch protection update (1-line `gh api` PATCH; documented in commit body)

```bash
gh api \
  --method PATCH \
  /repos/laitim2001/ai-semantic-kernel-framework-project/branches/main/protection \
  --field 'required_status_checks[contexts][]=All required checks' \
  --field 'required_status_checks[contexts][]=Lint + Type Check + Test (PG16)' \
  --field 'required_status_checks[contexts][]=v2-lints' \
  --field 'required_status_checks[contexts][]=Frontend E2E (chromium headless)' \
  --field 'required_status_checks[contexts][]=Backend E2E'
```

> **Confirmation needed at Day 4 pre-impl**: current `required_status_checks` exact context names. Day 4 first task is `gh api` GET to read current contexts.

### AD-CI-6 Implementation (deploy-production disable)

**File**: `.github/workflows/deploy-production.yml` (edit header + add `if: false` OR rename to `.disabled`)

```yaml
# Sprint 55.6 — temporary disable per AD-CI-6
# Re-enable when: (1) Azure App Service provisioned for V2; (2) GitHub Secrets configured;
# (3) smoke-test stage gated. Tracking: Phase 56+ infra sprint.

name: Deploy to Production (DISABLED — see AD-CI-6)

on:
  workflow_dispatch:  # manual-trigger only; no automatic on-push
  # push:
  #   branches: [main]  # disabled until V2 launch infra ready

jobs:
  deploy-production:
    if: false  # Sprint 55.6 — disabled per AD-CI-6
    # ... existing jobs ...
```

### Process AD pair Implementation

**File**: `.claude/rules/sprint-workflow.md` (extend §Step 2.5)

Edit existing §Step 2.5 (L120+) to add AD-Plan-3 content-verify as parallel mandatory task; add ROI evidence; add "How to apply" sub-section with grep query patterns.

**File**: `.claude/rules/file-header-convention.md` (extend §格式)

Add char-count budget guidance to MHist 1-line section (AD-Lint-3 enforced 1-line; AD-Lint-MHist-Verbosity now adds char-count writing tip).

---

## Acceptance Criteria

- [ ] **AD-Cat8-2**: `_handle_tool_error` body extended with `_retry_policy` consultation (after classify + record, before terminator)
- [ ] **AD-Cat8-2**: Tool execution sites L1049 + L1095 wrapped with retry loop consuming retry decision
- [ ] **AD-Cat8-2**: `ToolErrorDecision` extended with RETRY action + backoff_seconds + attempts_remaining (if not already present in 53.2 ABC)
- [ ] **AD-Cat8-2**: 6-8 unit tests covering retry-on-transient / retry-exhausted / retry-disabled / backoff-timing / error-class-not-retryable / attempt-counter
- [ ] **AD-Cat8-2**: 1 integration test (full AgentLoop run with deterministic flaky-tool fixture)
- [ ] **AD-Cat8-2**: Backwards-compatible — production default `retry_policy=None` preserves existing behavior byte-for-byte
- [ ] **AD-CI-5**: Aggregator workflow created + branch protection updated to point at aggregator
- [ ] **AD-CI-5**: Verified on docs-only PR that aggregator passes without touch-header workaround
- [ ] **AD-CI-6**: deploy-production.yml disabled (workflow_dispatch only OR `if: false`) with re-enable criteria documented
- [ ] **AD-Plan-3-Promotion**: sprint-workflow.md §Step 2.5 extended with content-verify task + ROI evidence + grep query patterns
- [ ] **AD-Lint-MHist-Verbosity**: file-header-convention.md §格式 extended with char-count budget guidance + anti-patterns
- [ ] Pytest delta ≥ +8 (1454 → ≥1462)
- [ ] 7 V2 lints 7/7 green
- [ ] mypy --strict 0 errors
- [ ] black + isort + flake8 clean
- [ ] LLM SDK leak 0
- [ ] AD-Plan-3 second application retrospective Q1 + Q3 (validate promotion success)
- [ ] AD-Sprint-Plan-5 second application retrospective Q2 + Q6 (medium-backend mult 0.80 + 0.05 surcharge = 0.85 calibration)

---

## Day-by-Day Plan

### Day 0 — Setup + 探勘 + Plan/Checklist Drafting (~2 hr fixed offset) ✅

- Working tree clean check on main `d3876ff1`
- Feature branch creation `feature/sprint-55-6-cat8-2-retry-group-h-process-ad-pair`
- Day-0 探勘: 5 grep + 2 Glob covering 4 backend/infra ADs + 2 process ADs
- AD-Plan-3 second application: content-keyword grep catches **5 drifts** (D1-D5) — D3 critical catch
- 5 drift findings catalogued (D1-D5)
- Plan + checklist drafting (mirror 55.5 13 sections / Day 0-5 expanded)
- Day 0 progress.md entry
- Commit Day 0 + push

### Day 1 — AD-Cat8-2 Implementation Part 1 (~3 hr; ToolErrorDecision + _handle_tool_error wire)

- Read `agent_harness/error_handling/_abc.py` to confirm `ToolErrorDecision` + `ToolErrorAction` exist; read `retry.py` for `RetryPolicyMatrix.should_retry()` signature
- Read `loop.py:259-330` (full `_handle_tool_error` body) + `loop.py:1040-1100` (tool execution call sites)
- Extend `ToolErrorDecision` dataclass + `ToolErrorAction` enum with RETRY action / backoff / attempts (if not already present)
- Extend `_handle_tool_error` body — consult `self._retry_policy` (if not None) after classify + record
- Add `attempt` parameter to `_handle_tool_error` signature (default 0; backwards-compat)
- Lint chain: black + isort + flake8 + mypy strict + 7 V2 lints
- Commit + push
- Day 1 progress.md entry

### Day 2 — AD-Cat8-2 Implementation Part 2 (~2.5 hr; tool execution retry wrap + tests)

- Edit `loop.py:1049` + `loop.py:1095` tool execution sites — wrap with retry loop
- Add 6-8 unit tests in `backend/tests/unit/agent_harness/orchestrator_loop/test_retry_policy_wire.py` (NEW)
- Add 1 integration test in `backend/tests/integration/agent_harness/test_loop_retry_integration.py` (NEW or extend existing)
- Run pytest cumulative target 1454 → ≥1461
- Lint chain
- Commit + push
- Day 2 progress.md entry

### Day 3 — Group H CI/infra (AD-CI-5 paths-filter long-term + AD-CI-6 deploy-production disable) (~3.5 hr)

- Read all 6 workflows briefly to map paths-filter usage
- Create `.github/workflows/required-checks-aggregator.yml`
- `gh api` GET to read current `required_status_checks` contexts
- `gh api` PATCH to update branch protection contexts (point at aggregator)
- Commit aggregator + document PATCH command in commit body for audit
- Disable `deploy-production.yml` (option: `if: false` on jobs OR rename); add re-enable criteria header
- Commit deploy-production change
- Push branch
- Verify on the in-flight 55.6 PR that aggregator + skipped paths-filter workflows pass per branch protection
- Day 3 progress.md entry — note any drift findings (D-classes if branch protection schema differs from plan)

### Day 4 — Process AD pair fold-in + Buffer (~1.5 hr)

- Edit `.claude/rules/sprint-workflow.md` §Step 2.5 (AD-Plan-3-Promotion)
- Edit `.claude/rules/file-header-convention.md` §格式 (AD-Lint-MHist-Verbosity)
- Verify both edits don't break the file's own MHist constraints (self-validation)
- Lint chain (sanity; docs-only edits should be neutral)
- Buffer: if Day 1-3 had overflow, absorb here; else use for SITUATION + memory pre-draft
- Commit + push
- Day 4 progress.md entry

### Day 5 — Retrospective + Closeout (~1.5 hr)

- Run full pytest baseline (target 1454 → ≥1462)
- Run full lint chain (black + isort + flake8 + mypy strict + 7 V2 lints)
- LLM SDK leak check
- Calibration ratio computation (AD-Sprint-Plan-5 second application; medium-backend mult 0.80 + surcharge 0.05 = 0.85)
- Catalog final drift findings (D1-Dn)
- Write retrospective.md (6 必答 Q1-Q6) — Q6 specifically AD-Sprint-Plan-5 medium-backend 0.80 + 0.05 second application validation + AD-Plan-3-Promotion ratification
- Update SITUATION-V2-SESSION-START.md §8 + §9 + history row
- Update memory: `project_phase55_6_audit_cycle_4.md` + MEMORY.md +1 line
- Commit closeout
- Push branch + open PR
- Watch CI green (apply paths-filter workaround if needed for the FINAL TIME — after AD-CI-5 lands, future sprints don't need it)
- Merge PR (solo-dev policy)
- Closeout PR for SHA fill-in if needed
- Final verify on main (clean)

---

## File Change List (Day-0 Path-Verified per AD-Plan-2 + Content-Verified per AD-Plan-3)

### Backend (NEW files)

| Path | Verified | Purpose |
|------|----------|---------|
| `backend/tests/unit/agent_harness/orchestrator_loop/test_retry_policy_wire.py` | ✅ Glob: not-exists (will create) | AD-Cat8-2 unit tests (6-8) |
| `backend/tests/integration/agent_harness/test_loop_retry_integration.py` | ⚠️ Day 1 confirm path; may extend existing instead | AD-Cat8-2 integration test (1) |

### Backend (EDIT existing files)

| Path | Verified | Edit |
|------|----------|------|
| `backend/src/agent_harness/orchestrator_loop/loop.py` | ✅ Grep: L194-247 retry_policy attribute confirmed dead; L259+ _handle_tool_error confirmed implemented; L1049+L1095 confirmed call sites | Wire `_retry_policy` into `_handle_tool_error` + retry loop wrap at call sites |
| `backend/src/agent_harness/error_handling/_abc.py` | ⚠️ Day 1 confirm — extend `ToolErrorDecision` + `ToolErrorAction` if RETRY action not already present | Add RETRY action + backoff_seconds + attempts_remaining |
| `backend/src/agent_harness/error_handling/retry.py` | ✅ Grep: L85 `class RetryPolicyMatrix` confirmed | Maybe extend `should_retry()` return type if signature mismatch (Day 1 confirm) |

### CI/Infra (NEW files)

| Path | Verified | Purpose |
|------|----------|---------|
| `.github/workflows/required-checks-aggregator.yml` | ✅ Glob: not-exists (will create) | AD-CI-5 long-term fix |

### CI/Infra (EDIT existing files)

| Path | Verified | Edit |
|------|----------|------|
| `.github/workflows/deploy-production.yml` | ✅ Glob: exists; Grep: health-check exit 1 logic at L178/192/223 | AD-CI-6 disable (workflow_dispatch + if: false) |
| `.github/workflows/backend-ci.yml` | ✅ exists | NO new touch-header (after AD-CI-5 lands; final touch may be needed for THIS PR if 55.6 lands before aggregator activates) |
| `.github/workflows/playwright-e2e.yml` | ✅ exists | NO new touch-header (same rationale) |

### Process / Rules (EDIT existing files)

| Path | Verified | Edit |
|------|----------|------|
| `.claude/rules/sprint-workflow.md` | ✅ Grep: L11 history + L120 §Step 2.5 confirmed | AD-Plan-3-Promotion: extend §Step 2.5 with content-verify task + ROI evidence + grep query patterns |
| `.claude/rules/file-header-convention.md` | ⚠️ Day 4 confirm §格式 location | AD-Lint-MHist-Verbosity: extend §格式 MHist guidance with char-count budget |
| `.claude/rules/anti-patterns-checklist.md` | ⚠️ Day 4 confirm AP-2 location | AD-Plan-3-Promotion cross-reference |

### Branch Protection (1-line `gh api` operation, no file change)

| Operation | Verified | Action |
|-----------|----------|--------|
| `gh api PATCH /repos/.../branches/main/protection` | ⚠️ Day 3 confirm current contexts via `gh api GET` first | Add `All required checks` aggregator to required_status_checks |

### Docs

| Path | Edit |
|------|------|
| `docs/03-implementation/agent-harness-planning/phase-55-production/sprint-55-6-plan.md` | NEW (this file) |
| `docs/03-implementation/agent-harness-planning/phase-55-production/sprint-55-6-checklist.md` | NEW |
| `docs/03-implementation/agent-harness-execution/phase-55/sprint-55-6/progress.md` | NEW (Day 0-5 entries) |
| `docs/03-implementation/agent-harness-execution/phase-55/sprint-55-6/retrospective.md` | NEW (Day 5) |
| `claudedocs/6-ai-assistant/prompts/SITUATION-V2-SESSION-START.md` | EDIT (§8 close 4 ADs + new ADs;§9 +Sprint 55.6 row;footer + history) |

**Total**: 2-3 NEW backend test files + 1-3 EDIT backend files (loop.py + _abc.py + maybe retry.py) + 1 NEW CI/Infra file + 2 EDIT CI/Infra files + 2-3 EDIT process/rules files + 4-5 docs = **~14-17 files**

---

## Dependencies & Risks

### Dependencies

- `agent_harness.error_handling.RetryPolicyMatrix` shipped 53.2 (D2 confirmed) → wire-only
- `agent_harness.error_handling.ToolErrorDecision` + `ToolErrorAction` enum from 53.2 (Day 1 will confirm RETRY action presence)
- `loop.py:_handle_tool_error` already implemented 53.2 (D3 confirmed) → extend body only
- `gh CLI` for branch protection PATCH (used in 53.2 + 53.4 + 53.5 + 53.6 successfully)
- 17.md §Cat 8 contracts (Verifier ABC + LoopEvents) → unchanged

### Risks (per .claude/rules/sprint-workflow.md §Common Risk Classes)

| Class | Symptom | Workaround | Long-term |
|-------|---------|------------|-----------|
| **A: paths-filter** | This sprint's PR may need ONE LAST touch-header before aggregator lands | Touch backend-ci.yml + playwright-e2e.yml header before Day 5 PR open | AD-CI-5 closes self in this sprint |
| **B: cross-platform mypy** | strict mode platform divergence on retry test mocks | `# type: ignore[X, unused-ignore]` pattern | AD-Test-1 closed by 53.7 |
| **C: module-level singleton** | TestClient event-loop reset for retry integration test | `tests/integration/api/conftest.py` autouse fixture | DI-injected per-request refactor (deferred) |

### Sprint-specific risks

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| `ToolErrorDecision` ABC missing RETRY action — extends scope by 30-60 min | Medium | Day 1 first task: read _abc.py + confirm; if missing, scope adjusts in plan revision commit (per AD-Plan-1 audit-trail rule) |
| `RetryPolicyMatrix.should_retry()` signature mismatch with planned consumer site | Low | Day 1 read retry.py first; if mismatch, adjust _handle_tool_error consumer logic |
| Branch protection PATCH locks me out (typo in context name) | Low | Day 3: GET current contexts first, copy-paste exact strings; PATCH with full set (no removal) |
| AD-CI-6 deploy-production disable affects some other dependency | Very Low | Workflow not in required_status_checks (D4 confirmed); already non-blocking; disable is safe |
| AD-Plan-3-Promotion edit to sprint-workflow.md introduces inconsistency with file-header-convention.md | Low | Day 4: read both files end-to-end first; cross-reference correctly |
| Day 0-5 (6 days) over-allocation if Cat8-2 wire is even smaller than D3 estimate (~3 hr instead of ~5-6 hr) | Medium (good problem) | Day 4-5 absorbs as buffer; ratio stays in band; SITUATION pre-update consumes spare time |

---

## Workload (per AD-Sprint-Plan-5 medium-backend class second application)

**Calibration formula** (AD-Sprint-Plan-5 second application; KEEP 0.80 per 55.5 retro Q6 #1):

```
multiplier = 0.80 (medium-backend, KEEP from Sprint 55.5 first refinement ratio 1.14 ✅)
            + 0.05 (audit-cycle-overhead surcharge: this sprint includes Process AD pair + Group H infra investigation)
            = 0.85

Day 0 ~2 hr fixed offset (excluded from bottom-up)
Day 5 retro + closeout ~1.5 hr (process overhead, included in committed)
```

### Bottom-up estimate (feature work only; Day 1-4)

| Item | Hours |
|------|-------|
| AD-Cat8-2 Day 1 (ToolErrorDecision extend + _handle_tool_error wire) | 3 |
| AD-Cat8-2 Day 2 (call site retry wrap + 6-8 unit + 1 integration) | 2.5 |
| AD-CI-5 Day 3 (aggregator workflow + branch protection PATCH) | 2 |
| AD-CI-6 Day 3 (deploy-production disable + re-enable criteria docs) | 1 |
| AD-Plan-3-Promotion Day 4 (sprint-workflow.md §Step 2.5 extend) | 0.5 |
| AD-Lint-MHist-Verbosity Day 4 (file-header-convention.md §格式 extend) | 0.25 |
| Day 4 buffer / SITUATION pre-draft | 0.5 |
| **Bottom-up total (feature)** | **~9.75** |

### Calibrated commitment

```
Bottom-up est ~9.75 hr → calibrated commit ~9.75 × 0.85 = 8.3 hr (multiplier 0.85)
                       → + Day 0 fixed offset 2 hr
                       → + Day 5 retro + closeout 1.5 hr
                       → total committed ≈ 11.8 hr (rounded to ~12 hr)
```

**Plan committed: ~12 hr total over 6 days (Day 0-5)**

> **Note vs Option A original ~15.3 hr est**: D3 critical catch dropped Cat8-2 from ~11 hr to ~5.5 hr → total drops from ~15.3 to ~12 hr. 6-day allocation provides buffer for any Day 1 ABC-extension scope adjustment.

---

## Out of Scope

| Item | Reason | Target |
|------|--------|--------|
| Cat 8 ErrorTerminator new actions (e.g. ESCALATE) | Out of audit cycle scope; existing TERMINATE / SKIP / RETRY sufficient | Phase 56+ if needed |
| Multi-tenant retry budget (per-tenant rate limit) | Phase 56+ SaaS Stage 1 scope | Phase 56+ |
| Distributed retry coordination (multi-instance Redis-backed) | Out of audit cycle scope | Phase 56+ if multi-instance |
| AD-Cat10-VisualVerifier + AD-Cat10-Frontend-Panel | Pure frontend feature | Phase 56+ frontend Group F sprint |
| Branch protection: enforce review_count back to 1 | Solo-dev policy permanent (53.2) | When 2nd collaborator joins |
| Deploy-production.yml full re-implementation | AD-CI-6 disable is sufficient for audit cycle; full re-implementation needs Azure infra | Phase 56+ infra sprint |

---

## AD Carryover Sub-Scope

If 55.6 hits time-box pressure, **rolling carryover** priority (largest to smallest):

1. AD-CI-6 (deploy-production disable) → 55.7+ (lowest priority; non-blocking, current red checks already noisy but tolerable)
2. AD-Lint-MHist-Verbosity → 55.7+ (low-effort process AD; could fold into any sprint)
3. AD-Plan-3-Promotion → 55.7+ (low-effort process AD; could fold into any sprint)
4. AD-CI-5 partial (aggregator workflow created but branch protection PATCH deferred) → 55.7+ (workflow file only; PATCH is 1-line and can be done in 55.7 Day 0)

> **Note**: AD-Cat8-2 is sprint critical path; carryover would reset 55.6 from "main progress" to "audit cycle bundle only" status. Avoid if possible.

---

## Definition of Done

- ☐ **4 ADs** closed per acceptance criteria (AD-Cat8-2 + AD-CI-5 + AD-CI-6 + AD-Plan-3-Promotion + AD-Lint-MHist-Verbosity = 5 ADs total — Process AD pair counted as 2)
- ☐ Tests added ≥ +8 (cumulative 1454 → ≥1462)
- ☐ 7 V2 lints green
- ☐ pytest unit + integration green
- ☐ mypy --strict 0 errors
- ☐ LLM SDK leak 0 (CI enforced)
- ☐ black + isort + flake8 green
- ☐ Calibration ratio computed in retro Q2 (AD-Sprint-Plan-5 medium-backend 0.85 second application)
- ☐ Drift findings catalogued (D1-Dn)
- ☐ retrospective.md with 6 必答 Q1-Q6
- ☐ SITUATION-V2-SESSION-START.md §8 updated (close 5 ADs; ratify AD-Plan-3 from candidate to validated; mark AD-Sprint-Plan-5 second application evidence)
- ☐ PR opened + CI green + merged to main
- ☐ Closeout PR for SHA fill-in if needed
- ☐ AD-CI-5 verified post-merge: future docs-only PRs no longer need touch-header workaround

---

## References

- **`SITUATION-V2-SESSION-START.md`** §8 Open Items (source of 4 backend ADs + 2 process ADs)
- **Sprint 55.5 retrospective.md** — origin of AD-Plan-3-Promotion + AD-Lint-MHist-Verbosity + AD-Sprint-Plan-5 KEEP 0.80
- **Sprint 55.4 retrospective.md** — origin of AD-Cat8-2 promotion (D6 100% dead state evidence — D3 catch refines this)
- **Sprint 55.5 plan + checklist** — format template (13 sections / Day 0-4; 55.6 expands to Day 0-5)
- **Sprint 53.2 retrospective.md** — origin of AD-CI-5 + AD-CI-6 + AD-Cat8-2; Cat 8 53.2 implementation reference
- **Sprint 53.2.5 retrospective.md** — paths-filter workaround documentation
- **`.claude/rules/sprint-workflow.md`** §Step 2.5 (existing) + §Workload Calibration + §Common Risk Classes
- **`.claude/rules/file-header-convention.md`** §格式 (1-line MHist; AD-Lint-3)
- **`.claude/rules/anti-patterns-checklist.md`** AP-2 no orphan code + AP-9 verification
- **`backend/src/agent_harness/error_handling/retry.py`** — RetryPolicyMatrix (53.2)
- **`backend/src/agent_harness/orchestrator_loop/loop.py`** — `_handle_tool_error` (53.2) + `_retry_policy` attribute (53.2 dead)
- **17-cross-category-interfaces.md** §Cat 8 ABC + LoopEvents (unchanged)

---

**Status**: Day 0 — pending user approval before Day 1 code starts.
