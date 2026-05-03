# Sprint 53.2.5 — Progress

**Plan**: [sprint-53-2-5-plan.md](../../../agent-harness-planning/phase-53-2-error-handling/sprint-53-2-5-plan.md)
**Checklist**: [sprint-53-2-5-checklist.md](../../../agent-harness-planning/phase-53-2-error-handling/sprint-53-2-5-checklist.md)
**Branch**: `chore/sprint-53-2-5-ci-carryover` (off main `a77878ad`)

---

## Day 0 — 2026-05-03 (Investigation + Setup, ~1 hour)

### Investigation 顛覆原診斷

53.2 retrospective.md 列 AD-CI-2 + AD-CI-3 為 53.x carryover；本 sprint Day 0 investigation 發現原診斷不對：

#### Finding 1：`ci.yml` 從未在 main 上成功

```bash
$ gh run list --workflow=ci.yml --branch=main --limit 25 --json conclusion
全 25/25 = failure；最早可追溯到 2026-04-10
```

AD-CI-1 觀察的 `since 0ec64c77` (2026-05-01) 不是 root cause start time，是 reviewer 注意到的時點。實際**自工作流程建立以來就壞**。

#### Finding 2：`ci.yml` workflow 在 GitHub Actions 以 broken state 註冊

```bash
$ gh api repos/.../actions/workflows --jq '.workflows[] | select(.path|contains("ci.yml"))'
{"id":203492876,"name":".github/workflows/ci.yml","path":".github/workflows/ci.yml","state":"active"}
```

`name` 欄位返回**檔案路徑** (`.github/workflows/ci.yml`) 而非 `name: CI Pipeline`（檔案 line 14 設的 display name）。對比其他 5 workflow 全有正確 display name（"Backend CI" / "Frontend CI" / "E2E Tests" / "V2 Lint" / "Deploy to Production"）。

這是 GitHub Actions parser 在 workflow **初次註冊**時 fail 的明確證據；之後即使檔案修了 `python -c "import yaml; yaml.safe_load(...)"` exit 0，GitHub 端仍 cache broken parse state。每次 push 觸發 workflow 都立即以 `conclusion=failure` 結束（jobs_count=null, run_duration_ms=null, run_started_at == updated_at 同秒）。

#### Finding 3：`ci.yml` 5 jobs 全與其他 workflow 重複

| `ci.yml` job | display name | 等價替代 |
|----|-----|-----|
| `lint` | "Code Quality" (black/isort/flake8/mypy) | `backend-ci.yml lint-and-test` |
| `frontend-test` | "Frontend Tests" (npm lint+typecheck+build) | `frontend-ci.yml lint-and-build` |
| `test` | "Tests" (pytest+PG16) | `backend-ci.yml lint-and-test` |
| `build` | "Build Docker Images" | 無等價（V2 Dockerfile 待 #31；hashFiles guard skip） |
| `ci-summary` | "CI Summary" | meta-only；4 active required checks 已涵蓋 |

`ci.yml` 是 V1 monolithic CI；`backend-ci.yml + frontend-ci.yml` 在 d5352359 拆出後即為 zombie。

### 結論：archive ci.yml（替代原計畫修復方案）

替換 53.2 retro 原計畫「fix ci.yml + restore 4 checks」為「archive 整個 ci.yml」。1 個動作同時解 AD-CI-2 + AD-CI-3。4 dropped checks 永久 drop（duplicates，不是 regression）。

### Day 0 完成項

- [x] Investigation findings 0.1 全 confirm
- [x] Branch created: `chore/sprint-53-2-5-ci-carryover` off main `a77878ad`
- [x] Phase execution dir created
- [x] Plan + checklist drafted（mirror 53.2 結構，scope 縮減為半天）
- [x] Day 0 progress.md（this file）

### Day 0 next（commit）

- [ ] Commit Day 0 docs (plan + checklist + progress.md)
- [ ] GitHub issue #49 建立 (AD-CI-3 closure tracking)
- [ ] Comment on issue #46 (53.2 US-8 superseded)

---

## Day 1 — 2026-05-03 (Archive + Verify + Close, ~3h)

### 1.1 Delete ci.yml ✅
- `git rm .github/workflows/ci.yml` 完成
- `grep` 確認其他檔案 reference 全是 historical V1 sprint planning docs（archive / sprint-execution V1 / V9 analysis），無 active dependency
- Commit `8d45cdc9` -277 lines

### 1.2 Update 13-deployment-and-devops.md ✅
§Branch Protection 全面 rewrite：
- §必選 Status Checks: 8 → 4 active（Lint+Type+Test / Backend E2E / E2E Summary / v2-lints）
- NEW §Permanently Dropped 子章節列出 4 條 + 替代 workflow
- §必選 Options: review_count 1→0（solo-dev policy）
- §gh api: 更新到當前指令 + future un-do snippet（2nd collaborator restoration）
- §維護紀律: 加 solo-dev policy 條目
- NEW §Changelog table: 52.6 baseline / 53.2 review_count / 53.2.5 ci.yml archive

### 1.3 Update 53.2 retrospective.md ✅
新增 §Follow-up — Sprint 53.2.5 (CI carryover) 含 investigation findings 表 + Resolution + Lesson Update 表（更正 AD-CI-3 真因 + AD-CI-1 since 0ec64c77 → 真實 since 2026-04-10）。

### 1.4 Memory files ✅
- `feedback_branch_protection_solo_dev_policy.md` line 62: "temporarily dropped ... restore after fix" → "permanently dropped ... not regression — duplicates removed"
- New `project_phase53_2_5_ci_carryover.md` (60+ lines)
- `MEMORY.md` 加新 entry under project section

### 1.5 + 1.6 Push + Open PR + Verify CI ✅
- Push: branch `chore/sprint-53-2-5-ci-carryover` to origin
- Open PR #50 with full body（investigation findings + redundancy table + V2 discipline self-check）
- **Initial CI**: 只 Backend E2E Tests + E2E Test Summary fired；Backend CI lint-and-test + V2 Lint NOT fired due to paths filter（docs-only PR + ci.yml deletion 不在 backend/** 也不在 lint paths）
- **mergeStateStatus = BLOCKED**

### 1.5b Paths filter blocker fix ✅ (discovered mid-merge)
- 問題：required_status_checks 假設那些 checks 總是 fire；workflow paths filter 假設 only fire when relevant files change → docs-only PR + 部分 required checks 不出現 → BLOCKED
- 解決：commit `9dbf35f1` 擴展 backend-ci.yml + lint.yml `paths:` 加 `.github/workflows/**`（future workflow file change 也觸發 backend 完整 test + V2 lint）
- 副作用：未來如再有 ci.yml-style "broken at registration" workflow 改動會更早 surface
- 同時 backend-ci push branches 加 `chore/**`（cover 本 sprint branch 命名）

### 1.6b CI verification ✅
4 required checks 全綠 at HEAD `9dbf35f1`：
- Lint + Type Check + Test (PG16): SUCCESS
- Backend E2E Tests: SUCCESS
- E2E Test Summary: SUCCESS
- v2-lints: SUCCESS

### 1.7 Merge PR ✅
- `gh pr merge 50 --merge --delete-branch`
- main HEAD: a77878ad → `80b4a9e1`
- Branch deleted local + remote

### 1.8 Post-merge verification ✅
- Workflow API list: 5 active workflows，**ci.yml 不在內** ✅
- main HEAD `80b4a9e1` push 觸發 4 expected workflows（Backend CI / V2 Lint / E2E Tests / Deploy to Production）
- **No ci.yml run** for new HEAD ✅（vs prior a77878ad 仍有 ci.yml failed run）

### 1.9 Close issues ✅
- #49 自動 closed by PR #50（"Closes #49" in body）
- 加 verification comment with post-merge evidence
- #46 (53.2 US-8 AD-CI-1) 已 CLOSED state；earlier supersede comment posted

### 1.10 Day 1 progress + retrospective ✅
- Day 1 section append（this section）
- retrospective.md 完整 6 必答 + Sprint Summary table

---

## Final Commits on `chore/sprint-53-2-5-ci-carryover`

| SHA | Description |
|-----|------|
| `31034b18` | Day 0 plan + checklist + Day 0 progress |
| `8d45cdc9` | ci.yml deletion (-277 lines) — closes AD-CI-2 + AD-CI-3 |
| `987d68ce` | Batched docs (branch protection + 53.2 follow-up + 53.2.5 checklist [x] partial) |
| `9dbf35f1` | paths expansion fix (backend-ci + lint to .github/workflows/**) |
| Final commit | Day 1 progress + retrospective + checklist 100% [x] (this commit) |

---

## Sprint Done — V2 14/22 unchanged（carryover bundle）
