# Sprint 53.2.5 — CI Carryover (AD-CI-2 + AD-CI-3 + 4-checks resolution)

**Phase**: phase-53-2-error-handling (carryover sub-sprint)
**Sprint**: 53.2.5
**Duration**: 1 day (Day 0-1 compressed)
**Status**: TODO → IN PROGRESS → DONE
**Created**: 2026-05-03
**Owner**: same session continuation post-53.2 PR #48 merge
**Branch**: `chore/sprint-53-2-5-ci-carryover` (off main `a77878ad`)

---

## Sprint Goal

清理 53.2 留下的 CI infrastructure carryover bundle：**AD-CI-2** (`ci.yml` multi-line `if: |` form) + **AD-CI-3** (CI Pipeline workflow trigger semantics — push 觸發 0 jobs) + **branch protection 4 dropped checks** restoration question。investigation 發現 **AD-CI-3 的真正根因不是 trigger 配置，而是 `ci.yml` workflow 自 2026-04-10 起就以 broken parse state 註冊在 GitHub Actions（workflow API name 欄位返回檔案路徑而非顯示名 "CI Pipeline"）**。同時 ci.yml 5 個 jobs 全與 `backend-ci.yml` + `frontend-ci.yml` 重複 — V2 拆分後遺留的 zombie workflow。**結論：archive ci.yml**（單一動作同時解掉 AD-CI-2 + AD-CI-3）；4-dropped-checks 永久 drop（redundant，並非降級）。**這是 V2 第 14 sprint 之 carryover bundle**，不算入 22 sprint 主進度。

---

## Background

### 53.2 Audit Debt 來源

per `docs/03-implementation/agent-harness-execution/phase-53-2/sprint-53-2-error-handling/retrospective.md` §Q5：

| ID | Description | Initial Diagnosis | Target |
|----|------|---------|------|
| AD-CI-2 | `ci.yml` multi-line `if: |` form 修 | 投入 multi-line YAML escape 形式 | 53.x |
| AD-CI-3 | CI Pipeline workflow trigger semantics（push 觸發 0 jobs；pull_request 不 fire） | 投入 trigger filter 配置研究 | 53.x |
| Restore 4 dropped checks | branch protection restore Code Quality / Tests / Frontend Tests / CI Summary | 等 AD-CI-3 修好後 1-line PATCH 還原 | 53.x |

### 本 sprint Day 0 Investigation 結果（重大轉向）

實際診斷後發現原診斷不正確：

#### Finding 1：`ci.yml` 從未在 main 上成功過

```bash
$ gh run list --workflow=ci.yml --branch=main --limit 25 --json conclusion
全 25 runs 都是 `failure`，最早可追溯到 2026-04-10
```

不是 53.x carryover —— 是**自工作流程建立以來就壞**。AD-CI-1 (`since 0ec64c77` 2026-05-01) 是當時 reviewer 觀察到的時點，不是 root cause 開始時點。

#### Finding 2：`ci.yml` workflow 在 GitHub Actions 以 broken state 註冊

```bash
$ gh api repos/.../actions/workflows --jq '.workflows[] | select(.path|contains("ci.yml"))'
{"id":203492876,"name":".github/workflows/ci.yml","path":".github/workflows/ci.yml","state":"active"}
```

`name` 欄位返回**檔案路徑**而非 `name: CI Pipeline`（檔案 line 14 設定的 display name）。這是 GitHub Actions parser 在 workflow 初次註冊時 fail 的明確證據；之後即使修了檔案內容 `python -c "import yaml; yaml.safe_load(...)"` exit 0，GitHub 端仍 cache 該 broken parse state。每次 push 觸發 workflow 都會立即以 `conclusion=failure` 結束（jobs_count=null, run_duration_ms=null, run_started_at == updated_at 同秒）。

對比同一 list 其他 workflow：

| File | API name 欄位 | 狀態 |
|------|------|---------|
| `ci.yml` | `.github/workflows/ci.yml` | ❌ broken registration |
| `backend-ci.yml` | `Backend CI` | ✅ 正常 |
| `frontend-ci.yml` | `Frontend CI` | ✅ 正常 |
| `e2e-tests.yml` | `E2E Tests` | ✅ 正常 |
| `lint.yml` | `V2 Lint` | ✅ 正常 |
| `deploy-production.yml` | `Deploy to Production` | ✅ 正常 |

#### Finding 3：`ci.yml` 5 jobs 全與其他 workflow 重複

| `ci.yml` job | display name | 等價替代 workflow / job |
|----|-----|-----|
| `lint` | "Code Quality" (black/isort/flake8/mypy 後端) | `backend-ci.yml lint-and-test` |
| `frontend-test` | "Frontend Tests" (npm lint+typecheck+build) | `frontend-ci.yml lint-and-build` |
| `test` | "Tests" (pytest+PostgreSQL 16) | `backend-ci.yml lint-and-test`（含 alembic upgrade head + pytest） |
| `build` | "Build Docker Images" | 無等價（V2 Dockerfile 待 #31；目前 hashFiles guard skip） |
| `ci-summary` | "CI Summary" | meta-only；4 active required checks 已涵蓋 |

`ci.yml` 是 V1 monolithic CI，d5352359 拆出 backend-ci.yml + frontend-ci.yml 之後即為 zombie。

### 結論：直接 archive ci.yml

替換 53.2 retrospective 原計畫「fix ci.yml + restore 4 checks」為「archive 整個 ci.yml」。

**好處**：
- AD-CI-2（multi-line `if`）moot（檔案不存在則無 YAML 問題）
- AD-CI-3（broken registration）moot（archive workflow 後 GitHub 不再執行）
- main HEAD 不再產生紅 X CI runs
- 4 dropped checks 永久 drop（duplicates 移除非安全降級）

**風險評估**：
- ❌ 失去 Docker build 自動驗證 → 目前已是 hashFiles guard skip，本來就沒在做；待 #31 V2 Dockerfile 落地後在新 workflow 中重建即可
- ❌ 失去 ci-summary 元整合 → 4 active required checks 已直接是 PR-level gate，summary 多餘
- ✅ 其他工作（black/isort/mypy/flake8/pytest/frontend lint+build）都由 backend-ci.yml + frontend-ci.yml + lint.yml 涵蓋

---

## User Stories

### US-1：作為 CI 維護者，我希望 archive `ci.yml` 將其從 GitHub Actions active workflow list 移除，以便 main HEAD 不再產生失敗 run（解 AD-CI-3 + 順帶解 AD-CI-2）

- **驗收**：
  - `.github/workflows/ci.yml` 從 repo 中刪除（`git rm`）
  - 推送後 GitHub workflow API 顯示 ci.yml `state="disabled"` or 從 list 中消失
  - 推送 a commit 至 main 後，**不再**有 `ci.yml` workflow run 紀錄
  - 其他 5 workflows（backend-ci / frontend-ci / e2e-tests / lint / deploy-production）正常觸發 + 結果保持與 53.2 一致（4 active required checks 全綠）
- **影響檔案**：
  - 刪除 `.github/workflows/ci.yml`
  - **不**動其他 workflow 檔案
- **GitHub Issue**：本 sprint 建立 #49 (AD-CI-3 closure) + 關閉 #46（53.2 US-8 AD-CI-1，已被本 sprint 取代）

### US-2：作為 V2 紀律維護者，我希望明文記錄「4 dropped checks 永久 drop（redundant, not regression）」於 deployment doc + 13-deployment-and-devops.md，以便未來 reviewer 不再嘗試 restore 它們

- **驗收**：
  - `docs/03-implementation/agent-harness-planning/13-deployment-and-devops.md` §Branch Protection 加 changelog entry：「2026-05-03 Sprint 53.2.5: ci.yml archived; 4 redundant required checks (Code Quality / Tests / Frontend Tests / CI Summary) permanently dropped」
  - `feedback_branch_protection_solo_dev_policy.md` "What this does NOT change" 段裡關於 "4 CI Pipeline checks ... AD-CI-3 trigger issue; restore after fix" 改寫為 "permanently dropped because ci.yml redundant + archived in Sprint 53.2.5"
- **影響檔案**：
  - `docs/03-implementation/agent-harness-planning/13-deployment-and-devops.md`
  - `C:\Users\Chris\.claude\projects\C--Users-Chris-Downloads-ai-semantic-kernel-framework-project\memory\feedback_branch_protection_solo_dev_policy.md`
- **GitHub Issue**：N/A（純 docs）

### US-3：作為 sprint owner，我希望本 sprint 的 progress + retrospective 紀錄完整，以便 53.x 後續 sprint 透明繼承狀態

- **驗收**：
  - `docs/03-implementation/agent-harness-execution/phase-53-2/sprint-53-2-5-ci-carryover/progress.md` 含 Day 0 (investigation) + Day 1 (archive + verify) sections
  - `retrospective.md` 含 6 必答（What went well / What didn't / What we learned / Audit Debt / Next steps / Solo-dev policy validation）
  - 53.2 retrospective.md 加註 follow-up entry 指向本 sprint 結論
  - V2 milestone count **不變**（14/22；本 sprint 為 carryover bundle 不算主進度）
- **影響檔案**：
  - 新建 progress.md / retrospective.md
  - 更新 53.2 retrospective.md（一個 follow-up entry）
  - 更新 sprint-53-2-5-checklist.md（[ ] → [x]）
- **GitHub Issue**：N/A

---

## Technical Specifications

### Action 1：Delete ci.yml

```bash
git rm .github/workflows/ci.yml
git commit -m "chore(ci, sprint-53-2-5): archive redundant ci.yml — solves AD-CI-2 + AD-CI-3 (was V1 monolithic CI; backend-ci.yml + frontend-ci.yml replaced it d5352359)"
```

### Action 2：Verify GitHub Actions side-effect

After push to feature branch + merge to main:

```bash
# Workflow should disappear from active list (or show state=disabled_inactivity)
gh api repos/laitim2001/ai-semantic-kernel-framework-project/actions/workflows --jq '.workflows[] | select(.path == ".github/workflows/ci.yml")'

# Last run for ci.yml stays as historical artifact (cannot delete)
gh run list --workflow=ci.yml --branch=main --limit 1
# Expected: empty or shows historical run only
```

### Action 3：Branch protection — already aligned

Current state（per Day 0 Bash query）：
- `enforce_admins=true`
- `review_count=0`（solo-dev policy permanent）
- `required_status_checks=4 active`：
  - `Lint + Type Check + Test (with PostgreSQL 16)` (backend-ci.yml)
  - `Backend E2E Tests` (e2e-tests.yml)
  - `E2E Test Summary` (e2e-tests.yml)
  - `v2-lints` (lint.yml)

**No PATCH needed**. Branch protection 已經正確配置，4 dropped checks **本來就是 ci.yml 的重複 jobs**，原本所謂「restore」沒必要。

### Doc updates 範本

**13-deployment-and-devops.md §Branch Protection changelog**:
```markdown
- 2026-05-03 (Sprint 53.2.5): `.github/workflows/ci.yml` archived (V1 monolithic CI redundant after `backend-ci.yml`/`frontend-ci.yml` split at d5352359). 4 jobs (Code Quality / Tests / Frontend Tests / CI Summary) permanently dropped from required checks — they were duplicates of backend-ci.yml + frontend-ci.yml jobs, NOT regression. AD-CI-2 + AD-CI-3 closed.
```

**feedback_branch_protection_solo_dev_policy.md "What this does NOT change"**:
```markdown
- 4 CI Pipeline checks (Code Quality / Tests / Frontend Tests / CI Summary) **permanently dropped** — ci.yml archived in Sprint 53.2.5 as redundant (V1 monolithic CI; backend-ci.yml + frontend-ci.yml cover the same jobs since d5352359). Not a regression.
```

---

## File Change List

| File | Action | Lines | Reason |
|------|------|------|------|
| `.github/workflows/ci.yml` | DELETE | -278 | redundant V1 workflow (AD-CI-2 + AD-CI-3 closure) |
| `docs/03-implementation/agent-harness-planning/13-deployment-and-devops.md` | UPDATE | +5 | branch protection changelog entry |
| `docs/03-implementation/agent-harness-execution/phase-53-2/sprint-53-2-error-handling/retrospective.md` | UPDATE | +10 | 53.2 retro follow-up entry pointing to 53.2.5 |
| `docs/03-implementation/agent-harness-planning/phase-53-2-error-handling/sprint-53-2-5-plan.md` | NEW | +280 | this file |
| `docs/03-implementation/agent-harness-planning/phase-53-2-error-handling/sprint-53-2-5-checklist.md` | NEW | +180 | sub-sprint checklist |
| `docs/03-implementation/agent-harness-execution/phase-53-2/sprint-53-2-5-ci-carryover/progress.md` | NEW | +60 | Day 0+1 progress |
| `docs/03-implementation/agent-harness-execution/phase-53-2/sprint-53-2-5-ci-carryover/retrospective.md` | NEW | +80 | 6 必答 |
| `~/.claude/projects/.../memory/feedback_branch_protection_solo_dev_policy.md` | UPDATE | +2/-2 | drop "AD-CI-3 restore after fix" wording |
| `~/.claude/projects/.../memory/MEMORY.md` | UPDATE | +1 | new entry pointing to 53.2.5 sprint |
| `~/.claude/projects/.../memory/project_phase53_2_5_ci_carryover.md` | NEW | +60 | sprint memory |

**Total**: 1 file deleted, 9 files touched, ~+650/-280 lines.

---

## Acceptance Criteria

1. ✅ `.github/workflows/ci.yml` removed from main
2. ✅ Push to main 後**不再**產生 ci.yml workflow runs
3. ✅ 4 active required checks 在 main HEAD push 全綠（`backend-ci.yml lint-and-test` / `e2e-tests.yml Backend E2E Tests` / `e2e-tests.yml E2E Test Summary` / `lint.yml v2-lints`）
4. ✅ Branch protection 設定保持當前狀態（不需 PATCH）
5. ✅ 13-deployment-and-devops.md branch protection changelog 加 entry
6. ✅ feedback_branch_protection_solo_dev_policy.md 同步更新
7. ✅ Sprint 53.2 retrospective.md 加 follow-up entry
8. ✅ progress.md + retrospective.md 完整
9. ✅ MEMORY.md 加 53.2.5 entry + project memory file 建立
10. ✅ 不影響 53.2 任何 src/ 代碼變更（純 CI infra cleanup）

---

## Day-by-Day Plan

### Day 0 (~1 hour) — Investigation 已完成 + setup

- [x] Investigate AD-CI-3 root cause（**done in this turn**: workflow registration broken since 2026-04-10）
- [x] Verify ci.yml redundancy（**done**: 5 jobs 全有等價替代）
- [ ] Create branch `chore/sprint-53-2-5-ci-carryover` off main `a77878ad`
- [ ] Create plan + checklist + commit Day 0 docs

### Day 1 (~3 hours) — Archive + verify + close

- [ ] Delete `.github/workflows/ci.yml`
- [ ] Update 13-deployment-and-devops.md changelog
- [ ] Update 53.2 retrospective.md follow-up entry
- [ ] Update memory files (feedback + MEMORY.md + new project file)
- [ ] Commit + push to feature branch
- [ ] Open PR #49（or whatever next number）
- [ ] Verify CI runs on PR：4 active required checks 全綠；ci.yml 不再 trigger
- [ ] Merge PR
- [ ] Verify post-merge：main HEAD push 後 ci.yml workflow 不再有新 run
- [ ] Close issue #46（53.2 US-8 AD-CI-1）+ link to 53.2.5
- [ ] Write progress.md + retrospective.md
- [ ] Update checklist [x] entries

---

## Dependencies & Risks

### Dependencies

- 53.2 已 merge 到 main (a77878ad) ✅
- Branch protection solo-dev policy 已生效 ✅
- 4 active required checks 已驗證綠（53.2 PR #48 merge 顯示 all checks passed）✅

### Risks

| Risk | Probability | Mitigation |
|------|------|------|
| 刪除 ci.yml 後 GitHub Actions API 不立即更新 workflow list | Low | 不影響運作；只是 API list 顯示延遲，1-24h 自動清掉 disabled 狀態 |
| 有未發現的 dependency 引用 ci.yml jobs | Very Low | grep 全 repo 確認無 reference；branch protection 已用其他 workflow's job names |
| Reviewer 認為應改修而非 archive | Low | plan §Background §Finding 1-3 提供完整證據；archive 是更乾淨方案 |
| Merge 後 main 觸發新 pre-existing 紅 X | Very Low | 已驗證 4 active checks 全綠；ci.yml 是唯一紅源 |

---

## Carry-out（不本 sprint 處理）

| ID | Description | Target |
|----|------|------|
| AD-Cat8-1 | RedisBudgetStore 0% cov；需 fakeredis dep | 53.x or 54.x bundle |
| AD-Cat8-2 | RetryPolicyMatrix 完整 retry-with-backoff loop | 54.x |
| AD-Cat8-3 | ToolResult schema 加 error_class 欄位 | 54.x |
| AI-22 | dummy red PR enforce_admins chaos test (52.6 carryover) | 53.x or 54.x bundle |
| #31 | V2 Dockerfile + 新 build workflow（取代 ci.yml 之 build job） | infrastructure track（無 sprint binding） |

---

## Anti-Pattern Self-Check (per anti-patterns-checklist.md)

| AP | Status | Reason |
|----|------|------|
| AP-1 Pipeline-disguised-as-Loop | N/A | 本 sprint 無 LLM 呼叫 |
| AP-2 Side-track | ✅ | 純 CI infra cleanup；不增加未使用 code |
| AP-3 Cross-directory scattering | N/A | 不動 src/ |
| AP-4 Potemkin features | N/A | 純刪除 |
| AP-5 Undocumented PoC | ✅ | 完整 plan + checklist + retro |
| AP-6 "Future-proof" abstraction | ✅ | 不加抽象層 |
| AP-7 Context rot | N/A | 不動 LLM loop |
| AP-8 Bypass PromptBuilder | N/A | 不動 LLM 呼叫 |
| AP-9 No verification | ✅ | Day 1 verify steps 詳細 |
| AP-10 Mock vs real divergence | N/A | 不動 mock |
| AP-11 Naming version suffix | N/A | 純刪除 |

---

## V2 Discipline 9 Self-Check

1. **Server-Side First**: ✅ N/A (no src changes)
2. **LLM Provider Neutrality**: ✅ N/A
3. **CC Reference 不照搬**: ✅ N/A
4. **17.md Single-source**: ✅ N/A (no contracts touched)
5. **11+1 範疇歸屬**: ✅ N/A (CI infra is platform/cross-cutting)
6. **04 anti-patterns**: ✅ all green (above)
7. **Sprint workflow (plan→checklist→code)**: ✅ this file is plan; checklist sibling
8. **File header convention**: ✅ N/A (純刪檔；docs updates 用 inline edit)
9. **Multi-tenant rule**: ✅ N/A
