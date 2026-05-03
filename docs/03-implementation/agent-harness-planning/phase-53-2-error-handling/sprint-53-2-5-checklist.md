# Sprint 53.2.5 — CI Carryover Checklist

**Plan**: [sprint-53-2-5-plan.md](./sprint-53-2-5-plan.md)
**Branch**: `chore/sprint-53-2-5-ci-carryover` (off main `a77878ad`)
**Duration**: 1 day (Day 0-1 compressed)

---

## Day 0 — Investigation + Setup (est. 1 hour)

### 0.1 Investigation findings (already completed)
- [x] **Confirm AD-CI-3 = broken workflow registration** _(workflow id 203492876 has API name=".github/workflows/ci.yml" instead of "CI Pipeline"; all 25/25 main runs since 2026-04-10 = failure with 0 jobs)_
- [x] **Verify ci.yml redundancy: 5 jobs all duplicated** _(lint=Code Quality / frontend-test=Frontend Tests / test=Tests / build=Build Docker Images [V2 Dockerfile #31 deferred] / ci-summary=meta — all covered by backend-ci.yml + frontend-ci.yml + 4 active required checks)_
- [x] **Verify branch protection state** _(enforce_admins=true / review_count=0 / 4 active required checks = backend-ci lint-and-test + e2e Backend + e2e Summary + v2-lints)_
- [x] **Identify d5352359 as workflow split commit** _(backend-ci.yml + frontend-ci.yml introduced; ci.yml became zombie thereafter)_

### 0.2 Branch + plan + checklist commit
- [x] **Verify on main + clean working tree** _(HEAD a77878ad)_
- [x] **Create feature branch** _(`chore/sprint-53-2-5-ci-carryover` created off a77878ad)_
- [x] **Verify phase folder structure exists** _(planning dir already exists; execution dir mkdir'd `sprint-53-2-5-ci-carryover/`)_
- [x] **Commit Day 0 plan + checklist + progress.md** _(commit `31034b18`; 3 files / 474 insertions)_

### 0.3 GitHub issues
- [x] **Create issue #49 — AD-CI-3 closure tracking** _(labels: sprint-53-2-5, ci-infrastructure, audit-carryover; new labels created)_
- [x] **Comment on existing #46 (53.2 US-8 AD-CI-1)** _(already CLOSED state from 53.2 PR #48 ref; comment 4365932527 marks superseded by #49)_

### 0.4 Day 0 progress.md
- [x] **Write Day 0 progress.md** _(written with 3 investigation findings + decision rationale + Day 1 next list)_

---

## Day 1 — Archive + Verify + Close (est. 3 hours)

### 1.1 Delete ci.yml
- [x] **Run `git rm .github/workflows/ci.yml`** _(file removed; -277 lines; commit `8d45cdc9`)_
- [x] **Verify no other file references ci.yml** _(grep result: only historical V1 sprint planning docs + 53.2 plan US-8 historical mention; no active dependency)_
- [x] **Commit deletion** _(commit `8d45cdc9`; full message includes investigation findings + redundancy table + no-regression rationale)_

### 1.2 Update 13-deployment-and-devops.md
- [x] **Locate §Branch Protection section** _(line 121-200; updated subsections: §必選 Status Checks → 4 active + new §Permanently Dropped; §必選 Options → review_count 1→0 entry; §gh api → updated command + future un-do snippet)_
- [x] **Add 2026-05-03 Sprint 53.2.5 entry** _(new §Changelog subsection with 3-row table: 52.6 baseline / 53.2 review_count change / 53.2.5 ci.yml archive)_
- [ ] **Commit (batched)** _(will be combined with 1.3+1.4 docs commit)_

### 1.3 Update 53.2 retrospective.md
- [x] **Add follow-up entry at end of retrospective.md** _(new §Follow-up — Sprint 53.2.5 with investigation findings + resolution + lesson update table)_
- [ ] **Commit (batched)** _(combined with 1.2+1.4)_

### 1.4 Update memory files
- [x] **Update `feedback_branch_protection_solo_dev_policy.md`** _(line 62 changed: "temporarily dropped ... restore after fix" → "permanently dropped ... not regression — duplicates removed")_
- [x] **Create `project_phase53_2_5_ci_carryover.md`** _(60+ lines memory; investigation findings + resolution + sprint workflow compliance + methodology demonstration)_
- [x] **Update `MEMORY.md`** _(new line under project section after 53.2 entry)_

### 1.5 Push + open PR
- [ ] **Push branch to origin** _(`git push -u origin chore/sprint-53-2-5-ci-carryover`)_
- [ ] **Open PR #49 (or next number)** _(title: `chore(ci, sprint-53-2-5): archive redundant ci.yml — closes AD-CI-2 + AD-CI-3`; body: link to plan + investigation findings + redundancy table + risk assessment)_
- [ ] **PR labels: sprint-53-2-5, ci-infrastructure, carryover**

### 1.6 Verify CI on PR
- [ ] **Wait for CI runs to start** _(should trigger backend-ci.yml + frontend-ci.yml + e2e-tests.yml + lint.yml on this PR; ci.yml 在 PR diff 包含其刪除 → ci.yml 仍可能 fire 一次最後 run)_
- [ ] **Verify 4 active required checks all green** _(`gh pr checks <PR-number>`)_
- [ ] **Verify ci.yml NOT in required checks blocking list** _(`gh pr view <PR-number> --json statusCheckRollup`)_

### 1.7 Merge PR
- [ ] **Merge PR via `gh pr merge <PR-number> --merge --delete-branch`** _(solo-dev policy = no review needed; enforce_admins=true 仍 active；4 required checks must pass)_
- [ ] **Verify main HEAD** _(`git pull && git log --oneline -3` — confirms merge commit on main)_

### 1.8 Post-merge verification
- [ ] **Wait for main HEAD push to trigger workflows** _(~30s)_
- [ ] **Confirm ci.yml does NOT trigger new run** _(`gh run list --workflow=ci.yml --branch=main --limit 1` should show empty or only historical run)_
- [ ] **Confirm 4 active required checks green on main HEAD** _(`gh run list --branch=main --limit 8 --json conclusion,workflowName | python -m json.tool`)_
- [ ] **Confirm GitHub workflow API state** _(`gh api repos/.../actions/workflows --jq '.workflows[] | select(.path|contains("ci.yml")) | {state}'` — expect empty or `state: disabled_inactivity`)_

### 1.9 Close issues
- [ ] **Close issue #46 (53.2 US-8 AD-CI-1)** _(comment: "superseded by 53.2.5 / PR #49 / archived ci.yml entirely")_
- [ ] **Close issue #49 (53.2.5 AD-CI-3)** _(comment with verification evidence)_

### 1.10 Day 1 progress.md + retrospective.md
- [ ] **Append Day 1 progress.md** _(archive action + verify + close issues)_
- [ ] **Write retrospective.md with 6 必答** _(What went well / What didn't / What we learned / Audit Debt deferred / Next steps / Solo-dev policy validation)_
- [ ] **Mark all checklist [ ] → [x]** _(no scope cuts expected)_
- [ ] **Final commit: closeout docs** _(message: `docs(closeout, sprint-53-2-5): Day 1 progress + retrospective + checklist 100%`)_

---

## Sanity Checks（all green required before closeout）

- [ ] **Source code unchanged** _(`git diff main..HEAD -- backend/ frontend/` should be empty — pure CI cleanup)_
- [ ] **Branch protection unchanged** _(`gh api repos/.../branches/main/protection --jq '.required_status_checks.contexts'` returns same 4 active checks)_
- [ ] **No new issues opened** _(only #49 created + #46/#49 closed)_
- [ ] **V2 14/22 milestone unchanged** _(carryover bundle, not main progress)_
- [ ] **Memory files consistent** _(MEMORY.md line count +1; feedback file line count ±0; new project file)_

---

## DoD（Definition of Done）

1. ✅ `git ls-files .github/workflows/ci.yml` returns empty on main
2. ✅ `gh run list --workflow=ci.yml --branch=main --limit 1` empty
3. ✅ Latest main HEAD has all 4 required checks green
4. ✅ 13-deployment-and-devops.md changelog entry present
5. ✅ feedback memory file updated
6. ✅ Sprint memory files complete (progress + retrospective + plan + checklist)
7. ✅ MEMORY.md index updated
8. ✅ Issues #46 + #49 closed with cross-links
9. ✅ Branch deleted post-merge
