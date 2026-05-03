# Sprint 53.2 — Retrospective

**Phase**: phase-53-2-error-handling (V2 sprint **14/22 = 64%**)
**Sprint**: 53.2 — Error Handling (Cat 8)
**Duration**: 2 days (Day 0-4 compressed; 2026-05-03 same-day execution)
**Plan**: [sprint-53-2-plan.md](../../../agent-harness-planning/phase-53-2-error-handling/sprint-53-2-plan.md)
**Checklist**: [sprint-53-2-checklist.md](../../../agent-harness-planning/phase-53-2-error-handling/sprint-53-2-checklist.md)
**Branch**: `feature/sprint-53-2-error-handling` (off main `aaa3dd75`)

---

## Sprint Outcome

| Metric | Final | Plan Target |
|--------|-------|-------------|
| pytest | **680 passed / 4 skip / 0 xfail / 0 fail** | ≥ 615 PASS / ≤ 1 xfail / 0 fail ✅ |
| mypy --strict src | **210 source files clean** | 205+ ✅ |
| Cat 8 coverage | **94%** (297 stmts; budget/policy/retry/terminator 100%; circuit_breaker 97%; _redis_store 0% by design) | ≥ 80% ✅ |
| 6 V2 lint scripts | all green (added AP-8 allowlist for circuit_breaker_wrapper) | all green ✅ |
| black/isort/flake8/ruff | all green | all green ✅ |
| Cat 8 vs Cat 9 boundary | **0 Tripwire usage in error_handling/** | 0 ✅ |
| #38 reactivation | **xfail count 1 → 0** | reactivated ✅ |
| AD-CI-1 fix | conditional skip applied | applied ✅ |
| 53.1 closeout bundle | merged into 53.2 PR | bundled ✅ |
| Backend CI on feature branch | green on all 5 commits | green ✅ |

**V2 milestone**: 13/22 → **14/22 (64%)** ⭐

---

## Mandatory Retrospective Q&A (per plan §Retrospective 必答 6 條)

### Q1: 每個 US 真清了嗎？

| US | Issue | Commit | Verification | Status |
|----|-------|--------|--------------|--------|
| US-1 ErrorPolicy | #40 | `f87c4a2f` + `2f565b60` | 19 unit tests pass; coverage 100% | ✅ |
| US-2 RetryPolicyMatrix | #41 | `f87c4a2f` | 15 unit tests pass; YAML loaded; coverage 100% | ✅ |
| US-3 CircuitBreaker | #42 | `8c00b413` + `677cfcc6` | 15 unit + 6 integration tests; 3-state transitions; adapter wrapper pattern | ✅ |
| US-4 ErrorBudget | #43 | `8c00b413` | 11 unit tests; multi-tenant isolation; coverage 100% | ✅ |
| US-5 ErrorTerminator | #44 | `077865b4` | 13 unit tests; 4 termination reasons + non-Tripwire boundary | ✅ |
| US-6 AgentLoop integration | #45 | `077865b4` (deps) + `1e782813` (full wire) | 4 integration tests; opt-in pattern preserves 51.x + 53.1 baseline | ✅ |
| US-7 #38 flaky test fix | #38 | `39bf8648` | xfail removed; isolation 3/3 + full suite 680/4/0 | ✅ |
| US-8 AD-CI-1 ci.yml fix | #46 | `39bf8648` + `57cf923d` | hashFiles guard; auto-skip when V2 Dockerfile absent | ✅ |
| US-9 53.1 closeout bundle | #47 | merge `b4001430` | 2 commits from `docs/sprint-53-1-closeout-bookkeeping` bundled into 53.2 PR | ✅ |

**8 active CI workflow on main HEAD** (post-merge): _to-be-recorded after PR merge_.

### Q2: 跨切面紀律守住了嗎？

- **admin-merge count** = TBD (target = 0; 53.2 走 normal review flow per plan)
- **temp-relax count** = TBD (target = 0; 53.2 explicitly禁 temp-relax)
- **Cat 8 coverage** = 94% (target ≥ 80% ✅)
- **Cat 8 vs Cat 9 邊界 grep evidence**:
  - `grep "import.*Tripwire\|class Tripwire\|Tripwire(" backend/src/agent_harness/error_handling/` → **0 hits** ✅ (per 17.md §6)
  - Documentation mentions of Tripwire (in docstrings/README) intentional — they explain the boundary
- **Cat 8 production usage grep evidence**:
  - `grep "self._error_policy.classify\|error_classifier.classify" backend/src/agent_harness/orchestrator_loop/` → **1+ hit** (line 240) ✅
  - `grep "_circuit_breaker\|breaker.is_open\|breaker.record" backend/src/adapters/` → **8+ hits** ✅
  - `grep "error_terminator.evaluate\|self._error_terminator" backend/src/agent_harness/orchestrator_loop/` → **2+ hits** ✅
- **No silent xfail** ✅ — #38 reactivated; new audit debt explicitly listed below
- **No new Potemkin** ✅ — Cat 8 modules all real-execute via 13 unit + 6 adapter integration + 4 loop integration tests

### Q3: 有任何砍 scope 嗎？

**1. AD-CI-1 fix scope reduced**
- Plan §US-8 enumerated 3 hypothesised root causes (alembic / env vars / fixture order)
- Reality: Day 0 diagnose found single root cause — missing `backend/Dockerfile`
- Fix: simpler than estimated (one-line conditional in ci.yml)
- Net: less code, same outcome. Audit Debt **AD-CI-2** (multi-line `if:` YAML form) noted.

**2. fakeredis dependency skipped**
- Plan §US-4 said "fakeredis or in-memory mock"
- Chose InMemoryBudgetStore (no new dep). RedisBudgetStore production-only, 0% test coverage by design.
- Justification: keeps test environment minimal; redis interaction validated by code review only.

**3. Naming alignment with stub**
- Plan said `ErrorCategory` enum + `DefaultErrorClassifier` ABC + USER_FIXABLE/UNEXPECTED reasons
- Reality: Sprint 49.1 stub already had `ErrorClass` + `ErrorPolicy` ABC + HITL_RECOVERABLE/FATAL
- Aligned with stub (semantics map cleanly) — saved a day of refactor.

### Q4: GitHub issues #40-47 + #38 全處理了嗎？

| # | Status | Closed by |
|---|--------|-----------|
| 38 | ✅ Closed | commit `39bf8648` (asyncio.run fix) |
| 40 US-1 | ✅ Closed | commit `2f565b60` |
| 41 US-2 | ✅ Closed | commit `2f565b60` |
| 42 US-3 | ✅ Closed | commits `8c00b413` + `677cfcc6` |
| 43 US-4 | ✅ Closed | commit `8c00b413` |
| 44 US-5 | ✅ Closed | commit `077865b4` |
| 45 US-6 | ✅ Closed | commits `077865b4` + `1e782813` |
| 46 US-8 | ✅ Closed | commits `39bf8648` + `57cf923d` |
| 47 US-9 | ✅ Closed | merge commit `b4001430` |

### Q5: Audit Debt 累積了嗎？

| ID | Type | Description | Target Phase |
|----|------|-------------|--------------|
| **AD-Cat8-1** | **Test infra** | `_redis_store.py` 0% coverage (no Redis in CI). Add fakeredis dep + Redis integration test path. | Phase 53.x or 54.x |
| **AD-Cat8-2** | **Loop integration depth** | `_handle_tool_error` only fires on UNCAUGHT exceptions; soft-failure path (`result.success=False` from ToolExecutorImpl) only checks terminator, not retry. RetryPolicy + circuit_breaker not yet wired into AgentLoop end-to-end. Need design pass. | Phase 54.x |
| **AD-CI-2** | **CI infra** | `ci.yml` Build Docker job uses single-line `if:` because multi-line `if: |` broke parser. Investigate proper multi-line YAML escape sequence. | Phase 53.x |
| **AD-CI-3** | **CI infra** | CI Pipeline workflow triggers on feature branch push (despite `branches: [main, develop]` filter). Returns failure with job_count=0. May be GitHub Actions edge case when workflow file changed in same push. Investigate. | Phase 53.x |
| AD-Cat8-3 | Tool exec error transparency | `_handle_tool_error` synthesizes `Exception(error_str)` for soft-failure classification — loses original exception type. Consider extending ToolResult to carry `error_class: str` so classification preserves type info end-to-end. | Phase 54.x |

### Q6: 主流量整合驗收

- ✅ **ErrorClassifier 在 AgentLoop 真用嗎？** Yes — `self._error_policy.classify(error)` called in `_handle_tool_error` (loop.py:240). 3 of 4 integration tests exercise this path.
- ✅ **CircuitBreaker 在 Adapter 真接入嗎？** Yes — `CircuitBreakerWrapper` wraps any ChatClient; pre-checks `is_open(resource)` + records success/failure post-call. 6 integration tests prove failure→OPEN→short-circuit cycle.
- ✅ **ErrorBudget 真用嗎？** Yes — `_handle_tool_error` calls `self._error_budget.record(tenant_id, cls)` before terminator check. Budget-pre-exceeded integration test verifies BUDGET_EXCEEDED termination.
- ✅ **ErrorTerminator 真用嗎？** Yes — `self._error_terminator.evaluate(...)` called in `_handle_tool_error` (loop.py:248). FATAL_EXCEPTION + BUDGET_EXCEEDED termination paths verified.
- ✅ **LLM-recoverable 回注真實作嗎？** Yes — `TestLLMRecoverable` integration test: tool fails → loop synthesizes error ToolResult → feeds to messages → LLM second turn → end_turn.
- ✅ **Cat 8 vs Cat 9 邊界 grep ＝ 0?** Yes — `grep "import.*Tripwire|class Tripwire|Tripwire(" error_handling/` = 0 hits. Boundary守住 per 17.md §6.
- ✅ **Cat 8 coverage 真達標嗎？** 94% (target ≥ 80%). Detail: budget/policy/retry/terminator 100%; circuit_breaker 97%; _redis_store 0% by design (audit debt AD-Cat8-1).

---

## What Went Well

1. **Sprint 49.1 stub head start** — `ErrorClass` enum + `ErrorPolicy` / `CircuitBreaker` / `ErrorTerminator` ABCs already existed; saved naming/boundary design time.
2. **Wrapper pattern for adapter integration** — kept ChatClient ABC neutral; concrete adapters (azure_openai/anthropic/openai) untouched; composition over inheritance.
3. **Layer-2 separation (policy.py + retry.py)** — clean separation of "should retry?" (policy) vs "with what config?" (retry matrix). YAML-driven per-tool tuning.
4. **Cat 8 coverage 94%** — surpassed target; 64 new tests across 4 files.
5. **#38 root cause found Day 0** — diagnostic time saved by upfront reproduce; fix was 1-line change.
6. **AD-CI-1 simpler than feared** — single root cause (missing Dockerfile) → conditional skip with hashFiles guard.
7. **Plan format consistency** — 9 sections plan + Day 0-4 checklist mirrored Sprint 53.1 structure (per `feedback_sprint_plan_use_prior_template.md`).
8. **Branch protection lock-in** — Sprint 52.6 enforce_admins=true held; no admin override in 53.2.
9. **Cross-platform mypy `# type: ignore[type-arg, unused-ignore]` pattern** — standard fix from code-quality.md applied for Redis[bytes].
10. **53.x carryover bundling** — #38 + AD-CI-1 + 53.1 closeout all handled in same PR; avoids 3rd temp-relax bootstrap.

## What Could Improve Next Sprint

1. **YAML multi-line `if:` form** — `if: |` block scalar broke GitHub Actions parser. Single-line is documented form. Add to sprint-workflow.md "common gotchas". → AD-CI-2.
2. **CI Pipeline trigger on feature branch** — workflow file changes seem to bypass `branches: [main, develop]` filter, causing job_count=0 failure. Worth investigating to understand actual GH Actions semantics. → AD-CI-3.
3. **AgentLoop integration depth** — `_handle_tool_error` is fired for both uncaught exceptions and soft-failure ToolResult. But RetryPolicyMatrix isn't yet wired (Day 4 deferred); needs full retry-with-backoff loop in 54.x. → AD-Cat8-2.
4. **Tool-error type transparency** — Soft-failure synthetic `Exception(error_str)` loses original type info. Consider extending ToolResult schema. → AD-Cat8-3.
5. **fakeredis dep** — RedisBudgetStore 0% coverage. Add fakeredis to dev extras OR document Redis-required test path. → AD-Cat8-1.

## Process Improvements Validated

- **Same-day Sprint 53.2 execution** — all 4 days completed in 1 calendar day (2026-05-03). Possible because:
  - Plan/checklist quality (9 USs well-defined)
  - Stub head start (Sprint 49.1 ABCs ready)
  - Drift documented in progress.md (semantic alignment with stub names)
- **Wrapper pattern for cross-cutting integration** — proven safe; concrete adapters untouched.
- **InMemoryBudgetStore for tests** — no new dep needed.

## Sprint Summary

14/22 V2 sprints (64%) — Cat 8 Level 4 達成. Core infra delivered:
- DefaultErrorPolicy (4-class registry + MRO walk)
- RetryPolicyMatrix (per-tool/per-class matrix + YAML config)
- DefaultCircuitBreaker (3-state per-resource + asyncio.Lock)
- TenantErrorBudget (per-day/month + multi-tenant isolation)
- DefaultErrorTerminator (4 reasons + non-Tripwire boundary)
- CircuitBreakerWrapper (transparent ChatClient decorator)
- AgentLoop `_handle_tool_error` integration (opt-in chain)

Cat 8 ABC implementations now production-ready. Phase 53.3 (Cat 9 Guardrails) can proceed with Cat 8 building blocks already in place + non-Tripwire boundary守住.

---

## Follow-up — Sprint 53.2.5 (CI carryover)

**Added**: 2026-05-03 (post-PR #48 merge same day)

53.2 Audit Debt §Q5 列出 AD-CI-2 + AD-CI-3 為 53.x carryover；Sprint 53.2.5 Day 0 investigation 顛覆原診斷：

- **AD-CI-3 root cause 不是 trigger semantics**（原診斷推測 push/pull_request filter 設定錯）
- **真實根因**：`.github/workflows/ci.yml` workflow 在 GitHub Actions 以 broken state 註冊 since 2026-04-10 — workflow API `name` 欄位返回檔案路徑 (`.github/workflows/ci.yml`) 而非 `name: CI Pipeline` (line 14 設的 display name)；25/25 main runs all failed with 0 jobs
- **AD-CI-1** 觀察的 `since 0ec64c77` (2026-05-01) 不是 root cause start，是 reviewer 注意到的時點
- **53.2 US-8 hashFiles guard 不夠**：只對應 Build Docker job 的失敗，但 workflow 自身 broken at registration level

### Sprint 53.2.5 Resolution

- **Action**: archive entire ci.yml（`git rm`；單檔變更同時解 AD-CI-2 + AD-CI-3）
- **Justification**: ci.yml 5 jobs 全與 backend-ci.yml + frontend-ci.yml 重複（V1 monolithic CI；d5352359 拆分後即為 zombie）
- **4 dropped checks (Code Quality / Tests / Frontend Tests / CI Summary)**: permanently drop（duplicates，**非降級**；其他 4 active checks 已涵蓋同等驗證）
- **Branch protection**: 不需 PATCH（4 active checks 已正確配置）
- **Sprint**: 53.2.5（V2 14/22 主進度不變；carryover bundle）

詳見 [sprint-53-2-5-plan.md](../../../agent-harness-planning/phase-53-2-error-handling/sprint-53-2-5-plan.md)。

### Lesson Update

| 53.2 Retro 原 lesson | 53.2.5 update |
|------|------|
| AD-CI-3 視為 trigger semantics 問題 | 真因是 GitHub Actions cache 之 broken parse state |
| 4 dropped checks "restore after AD-CI-3 fix" | permanently dropped — they were duplicates |
| AD-CI-1 since 0ec64c77 (2026-05-01) | 真實 first failure since 2026-04-10（fail history > AD-CI-1 觀察日期） |

---

**權威排序**：本 retrospective 對齊 [sprint-53-2-plan.md](../../../agent-harness-planning/phase-53-2-error-handling/sprint-53-2-plan.md) §Retrospective 必答 6 條 + Sprint 53.1 retrospective format.
