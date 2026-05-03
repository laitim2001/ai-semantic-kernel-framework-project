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

## Day 1 — TBD

（pending — Day 0 commit 後啟動）
