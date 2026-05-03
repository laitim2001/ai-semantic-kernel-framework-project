# Sprint 53.2.5 — Retrospective (CI Carryover)

**Plan**: [sprint-53-2-5-plan.md](../../../agent-harness-planning/phase-53-2-error-handling/sprint-53-2-5-plan.md)
**Checklist**: [sprint-53-2-5-checklist.md](../../../agent-harness-planning/phase-53-2-error-handling/sprint-53-2-5-checklist.md)
**Progress**: [progress.md](./progress.md)
**Branch**: `chore/sprint-53-2-5-ci-carryover` (off main `a77878ad` → merged at `80b4a9e1`)
**PR**: #50 (merged 2026-05-03)
**Duration**: same-day (~4 hours; Day 0+1 compressed)
**V2 milestone**: 14/22 (64%) **unchanged**（carryover bundle 不算主進度）

---

## Q1：What went well？

### 1. Investigation 顛覆原診斷（Day 0 最大收穫）
- 53.2 retrospective 列 AD-CI-3 為 "trigger semantics 配置問題"。Day 0 5 個並行 Bash 調查（branch protection state / ci.yml 25 runs / workflow API name 欄位 / `python -c yaml.safe_load` / `gh run view total_count`）即發現真因：**workflow registration broken at GitHub Actions level since 2026-04-10**（API `name` 欄位返回檔案路徑）。
- 若沒做 investigation 直接執行原計畫「修 trigger 配置」，會花更久時間在錯誤方向，而且最後仍無法解決。

### 2. 「Archive 替代修復」決策乾淨
- 一旦發現 ci.yml 是 broken-since-day-1 + redundant V1 monolithic CI（5 jobs 全與 backend-ci.yml + frontend-ci.yml 重複），**不修復 + 直接 archive** 比「修一個沒人用的 workflow」簡潔太多。
- 1 個動作（`git rm`）同時解 AD-CI-2 + AD-CI-3 + 4-dropped-checks question。
- -277 lines / 0 src/ changes → low-risk pure infra cleanup。

### 3. 53.2 solo-dev policy 首次「自然」用上
- PR #50 走 0-review merge，無 temp-relax bootstrap，無 enforce_admins=false bypass。第 3 次「temp-relax 預期」被 53.2 結構性政策吸收，policy 真正生效（前 2 次：52.6 #28 + 53.1 #39 都用過 temp-relax）。

### 4. Plan/Checklist 格式一致性紀律
- 起草前讀完 53.2 plan 前 199 行作 template；compress 為半天 scope（保留 Sprint Goal / Background / User Stories / Technical Specifications / File Change List / Acceptance / Day-by-Day / Dependencies & Risks / Carry-out / Anti-Pattern self-check / V2 Discipline self-check 全 11 sections）。
- Checklist mirror 53.2 之 Day 0-1 結構 + DoD + Verify command pattern。
- 用戶一次 approve 即進入執行（無 v1→v2→v3 重寫迴圈，contrast 52.1 incident）。

---

## Q2：What didn't go well？

### 1. Paths filter blocker 未在 plan 中預測
- Plan §Risks 列了 4 條 risks（low/very low），但**沒列 paths filter**：backend-ci.yml + lint.yml `paths:` 限制只觸發 backend/** + lint specific paths，docs-only PR 不 fire 那 2 個 required checks → mergeStateStatus=BLOCKED。
- PR #50 開啟後才發現，新增 1 commit (`9dbf35f1`) 擴展 paths 到 `.github/workflows/**` 才解。
- **Lesson**: 任何 docs-only / CI-config-only sprint 都應預先檢查 required checks 是否被 paths filter 排除；plan §Risks 漏了「PR 性質 vs paths filter」這層。

### 2. AD-CI-1 在 53.2 retrospective 的 timeline 寫錯
- 53.2 retro 寫 "since 0ec64c77 (2026-05-01)"，但實際 first failure 日期是 **2026-04-10**（25 runs 全 failure）。0ec64c77 只是 reviewer 注意到的時點。
- 改 follow-up entry 時補正 timeline；以後類似診斷需 grep 整 history 而不只看 reviewer 觀察日期。

### 3. ci.yml issue 從 sprint 0 (2025) 起就存在卻沒人發現
- ci.yml 是 V1 sprint 0 第一個 GitHub Actions workflow（commit `450d0394` MVP）。**自始**就在 GH Actions 上以 broken state 註冊，never worked on main branch。
- 但 V1 開發鏈上沒人注意（V1 階段對 push-to-main CI run 不太關心；V1 用 `dev` branch + manual deploy）。
- 直到 V2 Sprint 52.6 強制 8 required checks 包括 ci.yml-derived 之 Code Quality / Tests / Frontend Tests / CI Summary 後，每次 PR merge 都看到 main HEAD 紅 X，才被當 audit debt 寫入。
- **Lesson**: V1→V2 過渡時，V1 inherited workflows 應全 audit 是否仍 active + needed；本次 archive 應該是 Sprint 52.6 US-5 一併做的（若那時 audit 過）。

---

## Q3：What we learned（generalizable）

### 1. GitHub Actions 「workflow registration」是 sticky cache
- `python -c "import yaml; yaml.safe_load(...)"` 通過 ≠ GitHub Actions 認為 workflow 有效。GH 在初次註冊 workflow 時若解析失敗，**永久** cache broken state，後續修改 file 內容 GH 不會重新評估。
- 唯一恢復方式：rename file（forces new workflow ID 註冊）or delete + add back。
- **Diagnostic signal**: API `workflows.name` 欄位返回**檔案路徑**而非 `name:` 欄位定義的 display name = broken registration。

### 2. Required status checks vs paths filter 互相衝突
- Branch protection `required_status_checks` 假設那些 checks **總是會 fire**。
- workflow `paths:` filter 假設 **only fire when relevant files change**。
- Docs-only PR + 只觸發部分 required checks → BLOCKED。
- Solution: required workflows 應該不用 `paths:` filter；或 paths 包含 `.github/workflows/**`（讓 CI infra change 也驗證一遍）。

### 3. Archive over fix 是常常被忽略的選項
- V1 → V2 演進產生很多 zombie code / configs。「修舊的」往往沒「刪舊的」乾淨。
- 詢問順序：先問「這還在用嗎」，再問「這值得修嗎」，最後才問「這該怎麼修」。

---

## Q4：Audit Debt（deferred）

| ID | 描述 | Target | Notes |
|----|------|------|------|
| AD-Cat8-1 | RedisBudgetStore 0% cov（無 fakeredis dep） | 53.x or 54.x | 53.2 carryover；本 sprint 無關 |
| AD-Cat8-2 | RetryPolicyMatrix end-to-end retry-with-backoff loop | 54.x | 53.2 carryover |
| AD-Cat8-3 | ToolResult schema 加 error_class 欄位 | 54.x | 53.2 carryover |
| AD-CI-4 | sprint plan §Risks 應加「paths filter vs required checks」這類 risk | next sprint plan template | 直接寫進 sprint-workflow.md rule？ |
| AI-22 | dummy red PR enforce_admins chaos test | 53.x or 54.x | 52.6 carryover |
| #31 | V2 Dockerfile + 新 build workflow（取代 ci.yml 之 build job） | infrastructure track（無 sprint binding） | unchanged |

**Note**: 53.2.5 不再產生新 audit debt（除 meta-level AD-CI-4「sprint plan template 缺項」）。

---

## Q5：Next steps（rolling planning 紀律下）

### Open carryover bundle candidates 53.x
- AD-Cat8-1 (fakeredis + RedisBudgetStore integration test) — 53.x or bundled into 53.3 §Carry-in
- AI-22 (chaos test) — same bundle
- Sprint plan §Risks template fix（AD-CI-4）— 可單獨 small-scope sprint or rule update

### Sprint 53.3 (Cat 9 Guardrails) 仍待 user approve scope
- per `06-phase-roadmap.md`：input/output/tool guardrails + Tripwire ABC + plugin registry + WORM hash chain
- **Plan/Checklist 尚未起草**（per rolling planning 紀律，等 user 確認 scope 才寫）

### Solo-dev policy validated（structural fix）
- 53.2 設定的 `required_approving_review_count=0` 在 53.2.5 PR #50 merge 中**自然運作**，無 temp-relax 介入。replace 之前 52.6 #28 + 53.1 #39 各 1 次 temp-relax。
- 預期：未來所有 solo-dev PR 都走相同 path（PR + 4 active CI gate + admin enforce + 0 review count）。

---

## Q6：Solo-dev policy validation（sprint-specific）

### Test result
- ✅ PR #50 **沒有用** temp-relax bootstrap
- ✅ PR #50 **沒有用** `gh pr merge --admin` bypass
- ✅ PR #50 走 normal merge flow，4 required checks 全綠後 merge
- ✅ enforce_admins=true 仍生效（沒被觸發 / 無需 bypass）
- ✅ 0-review merge 是 GitHub-supported normal flow

### Before vs After
- **52.6 / 53.1**：merge 前 PATCH `review_count: 1 → 0` 暫降 → merge → restore（temp-relax bootstrap）
- **53.2 onward**：`review_count` 永久 0；solo-dev 直接 merge；無暫降

### When to revert
- 加入 2nd collaborator 時 1-line PATCH 還原（`13-deployment-and-devops.md` §gh api command 含 future un-do snippet）

---

## Sprint Summary

| Metric | Value |
|--------|-------|
| Duration | same-day（~4h Day 0+1 compressed） |
| Commits on branch | 4（plan/checklist + ci.yml deletion + batched docs + paths fix） |
| PR | #50（merged `80b4a9e1`） |
| Issues | #49 created + closed; #46 (53.2 US-8) supersede comment（already CLOSED state） |
| File changes | 1 deleted + 7 modified + 4 new (sprint docs + memory) |
| src/ changes | **0**（純 CI infra cleanup） |
| Audit debt closed | AD-CI-2 + AD-CI-3 + 4-dropped-checks resolution（3 items） |
| New audit debt | 1 meta-level (AD-CI-4 plan template) |
| V2 milestone | 14/22 (64%) **unchanged**（carryover bundle） |
| Solo-dev policy validation | ✅ no temp-relax used |

---

**權威排序**：本 retrospective 對齊 [sprint-53-2-5-plan.md](../../../agent-harness-planning/phase-53-2-error-handling/sprint-53-2-5-plan.md) §Acceptance Criteria + Sprint 53.2 retrospective format。
