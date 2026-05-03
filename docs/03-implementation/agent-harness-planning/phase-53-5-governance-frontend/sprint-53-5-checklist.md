# Sprint 53.5 — Governance Frontend + Cat 9 Loop Wiring + Audit HTTP API — Checklist

**Plan**: [sprint-53-5-plan.md](sprint-53-5-plan.md)
**Branch**: `feature/sprint-53-5-governance-frontend`
**Day count**: 5 (Day 0-4) | **Estimated total**: ~22-31 hours

> **格式遵守**：每 Day 同 53.4 結構（progress.md update + sanity + commit + verify CI）。每 task 3-6 sub-bullets（case / DoD / Verify command）。

---

## Day 0 — Setup + Playwright + Frontend Baseline + Cat 9 Loop Stub Locate (est. 3-4 hours)

### 0.1 Branch + plan + checklist commit
- [ ] **Verify on main + clean**
  - Command: `git status && git branch --show-current` → expects `main` clean
  - DoD: working tree empty
- [ ] **Create branch + push plan/checklist**
  - Command: `git checkout -b feature/sprint-53-5-governance-frontend`
  - Stage: plan + checklist files
  - Commit: `docs(plan, sprint-53-5): plan + checklist for governance frontend + Cat 9 loop wiring + audit HTTP API`
  - Push: `git push -u origin feature/sprint-53-5-governance-frontend`
  - DoD: branch on remote with plan + checklist visible

### 0.2 GitHub issues 建立
- [ ] **Open 6 issues for US-1 ~ US-6**
  - Each issue: title = `Sprint 53.5 US-X: <description>`
  - Labels: `sprint-53-5`, `phase-53`, `governance` / `frontend` / `cat-9`
  - Link to plan
  - DoD: 6 issues open

### 0.3 Playwright runner setup（CRITICAL — frontend-heavy sprint pre-req per 53.4 retrospective Q4）
- [ ] **Verify Playwright already installed in frontend/**
  - Command: `cd frontend && cat package.json | grep -i playwright`
  - DoD: 確認 @playwright/test 已在 devDependencies；若無 → `npm install -D @playwright/test` + `npx playwright install chromium`
- [ ] **Verify playwright.config.ts exists or create minimal**
  - Path: `frontend/playwright.config.ts`
  - Required: testDir, baseURL (http://localhost:3000), reporter
  - DoD: `npx playwright test --list` runs without error
- [ ] **Smoke run with example spec**
  - Command: `cd frontend && npx playwright test --reporter=list 2>&1 | head -20`
  - DoD: runner spawns headless chromium successfully; no missing-binary errors

### 0.4 Frontend baseline 探勘
- [ ] **Inspect existing governance + chat-v2 + components/chat structure**
  - Files: `frontend/src/pages/governance/`, `frontend/src/pages/chat-v2/`, `frontend/src/components/chat/`, `frontend/src/services/`
  - Record: 檔案清單 + 行數 + 既有 routing pattern + Zustand store 結構
  - DoD: progress.md Day 0 §Frontend baseline 完整
- [ ] **Verify SSE event handler pattern in ChatPage**
  - File: `frontend/src/pages/chat-v2/ChatPage.tsx`
  - Look for: existing `EventSource` / `useSSE` hook / event type union
  - DoD: 知道 ApprovalRequested SSE handler 怎麼注入（US-2 prep）

### 0.5 Cat 9 loop wiring stub locate（US-3 prep）
- [ ] **Locate `_cat9_tool_check` in AgentLoop**
  - Command: `grep -n "_cat9_tool_check\|cat9_check\|Stage.ESCALATE" backend/src/agent_harness/orchestrator_loop/loop.py`
  - DoD: 找到 53.3 留下的 ESCALATE branch + 53.4 deferred wiring 位置
- [ ] **Verify HITLManager wait_for_decision API**
  - File: `backend/src/platform_layer/governance/hitl/manager.py`
  - Confirm: method signature for cross-session wait + 4hr timeout
  - DoD: 知道 US-3 _cat9_tool_check 會呼叫哪個方法

### 0.6 Audit endpoint baseline（US-5 prep）
- [ ] **Inspect existing api/v1/ structure**
  - Files: `backend/src/api/v1/__init__.py`, `backend/src/api/dependencies.py`
  - Look for: existing RBAC dep pattern (`get_current_user`, role checks)
  - DoD: 知道 `require_audit_role` 怎麼建（依循既有 dep pattern）
- [ ] **Verify AuditQuery service interface**
  - File: `backend/src/platform_layer/governance/audit/query.py`
  - Confirm: 53.4 已有的 list / verify_chain method signatures
  - DoD: 知道 US-5 router 直接呼叫哪些 method

### 0.7 Day 0 progress.md
- [ ] **Create `docs/03-implementation/agent-harness-execution/phase-53-5/sprint-53-5-governance-frontend/progress.md`**
- [ ] **Day 0 sections**: Setup completion / Playwright readiness / Frontend baseline / Cat 9 loop stub location / Audit endpoint baseline
- [ ] Commit: `docs(progress, sprint-53-5): Day 0 setup + Playwright + frontend/Cat9/audit baselines`
  - Push: `git push`

---

## Day 1 — US-5 Audit HTTP API + US-6 Chain Verify + US-4 notification.yaml (est. 5-6 hours)

### 1.1 US-5 Audit HTTP endpoint
- [ ] **Create `backend/src/api/v1/audit.py`**
  - Content: FastAPI router with `GET /log` endpoint
  - Filters: from_ts / to_ts / op_type / user_id / page / page_size
  - DoD: imports clean + endpoint registered
- [ ] **Add RBAC dependency `require_audit_role`**
  - File: `backend/src/api/dependencies.py`
  - Roles allowed: auditor / admin / compliance
  - 403 for other roles
  - DoD: dep can be tested independently
- [ ] **Register audit router in `api/v1/__init__.py`**

### 1.2 US-6 Chain verify endpoint
- [ ] **Add `GET /verify-chain` endpoint to `audit.py`**
  - Calls `AuditQuery.verify_chain()` (extend service if needed)
  - Returns: `{verified, broken_at, chain_length, total_entries}`
  - DoD: endpoint registered + tenant isolation enforced
- [ ] **Extend AuditQuery.verify_chain() if missing**
  - File: `backend/src/platform_layer/governance/audit/query.py`
  - Logic: iterate audit_log entries by previous_log_hash, verify hash chain
  - DoD: returns ChainVerifyResult dataclass

### 1.3 US-5 + US-6 integration tests
- [ ] **Create `tests/integration/api/test_audit_endpoints.py`**
  - US-5 cases: paginated query / cross-tenant 404 / non-auditor 403 / role accepted / time-range filter / op_type filter
  - US-6 cases: verified chain returns true / synthetic broken chain returns false + broken_at index / cross-tenant 404
  - DoD: ≥ 9 cases total; coverage ≥ 80%
  - Verify: `python -m pytest tests/integration/api/test_audit_endpoints.py -v`

### 1.4 US-4 notification.yaml + factory
- [ ] **Create `backend/config/notification.yaml`**
  - Content: version + defaults + teams.webhooks.{default, per_tenant_overrides} + message_template
  - DoD: YAML parseable
- [ ] **Add `load_notifier_from_config` factory in `notifier.py`**
  - File: `backend/src/platform_layer/governance/hitl/notifier.py`
  - Behavior: parse YAML + env var interpolation + fallback to NoopNotifier
  - DoD: function callable; env var `${...}` resolves
- [ ] **Wire ServiceFactory or extend HITLManager construction**
  - File: `backend/src/platform_layer/governance/service_factory.py` (new) OR extend existing factory
  - Behavior: `factory.get_hitl_manager(tenant_id)` returns HITLManager with correct notifier
  - DoD: factory testable; tenant override resolves

### 1.5 US-4 unit tests
- [ ] **Create `tests/unit/platform_layer/governance/hitl/test_notification_config.py`**
  - Cases: YAML loading / env var interpolation / per-tenant override / missing webhook → NoopNotifier / missing YAML → NoopNotifier
  - DoD: ≥ 5 cases; coverage ≥ 85%

### 1.6 Day 1 sanity checks
- [ ] **mypy --strict 無新錯誤**
  - Command: `cd backend && python -m mypy --strict src/api/v1/audit.py src/platform_layer/governance/hitl/notifier.py`
- [ ] **black + isort + flake8 green**
  - Command: standard pre-push chain
- [ ] **V2 lint scripts green**
  - Command: 6 `scripts/lint/check_*.py` scripts (per `feedback_v2_lints_must_run_locally.md`)

### 1.7 Day 1 commit + push + verify CI
- [ ] **Stage + commit + push**
  - Verify branch: `git branch --show-current`
  - Commit: `feat(api+governance, sprint-53-5): US-5 Audit HTTP + US-6 chain verify + US-4 notification config`
  - Push: `git push`
- [ ] **Verify CI runs and passes lint**
  - Command: `gh run list --branch feature/sprint-53-5-governance-frontend --limit 3`

### 1.8 Day 1 progress.md update
- [ ] **Update progress.md with Day 1 actuals**
  - Sections: Today's accomplishments / drift / banked-or-burned hours / blockers
  - Commit: `docs(progress, sprint-53-5): Day 1 actuals + drift notes`
  - Push: `git push`

---

## Day 2 — US-3 Cat 9 Stage 3 → AgentLoop → HITLManager Wiring (est. 5-7 hours)

### 2.1 US-3 ToolGuardrail returns RiskLevel context
- [ ] **Modify `backend/src/agent_harness/guardrails/tool/tool_guardrail.py`**
  - Add risk_level field to Stage.ESCALATE decision return
  - Pull from RiskPolicy.evaluate() (53.4 US-1)
  - DoD: existing tests pass + new field on ESCALATE returns

### 2.2 US-3 AgentLoop `_cat9_tool_check` HITL wiring
- [ ] **Implement `_cat9_tool_check` HITL branch in `loop.py`**
  - File: `backend/src/agent_harness/orchestrator_loop/loop.py`
  - Behavior:
    1. ToolGuardrail returns Stage.ESCALATE → call HITLManager.request_approval()
    2. Pause loop + Cat 7 checkpoint with pending_approval_id
    3. Wait for decision (4hr timeout via wait_for_decision)
    4. Apply HITLDecisionReducer → loop continues / blocks
  - DoD: imports clean + 4 paths covered (APPROVED/REJECTED/ESCALATED/EXPIRED)

### 2.3 US-3 integration tests
- [ ] **Create `tests/integration/agent_harness/governance/test_stage3_escalation_e2e.py`**
  - Cases:
    - sensitive tool → Stage 3 → HITLManager pending → approve → loop resume
    - sensitive tool → Stage 3 → reject → loop blocked
    - sensitive tool → Stage 3 → expire (timeout) → fallback policy applied
    - cross-session 4hr resume after worker restart
    - audit chain integrity verified at each transition
  - DoD: ≥ 5 cases; full e2e + audit hash chain verify
  - Verify: `python -m pytest tests/integration/agent_harness/governance/test_stage3_escalation_e2e.py -v`

### 2.4 US-3 add Stage 3 case to existing loop guardrails test
- [ ] **Modify `tests/integration/agent_harness/guardrails/test_loop_guardrails.py`**
  - Add Stage 3 e2e case (lighter than test_stage3_escalation_e2e.py)
  - DoD: existing 53.3 cases still pass

### 2.5 Day 2 sanity checks
- [ ] **All Day 2 tests green**
  - Command: `python -m pytest tests/integration/agent_harness/ -v`
- [ ] **Lint chain green**
  - Standard chain + V2 lint scripts
- [ ] **mypy --strict src/agent_harness/orchestrator_loop/loop.py**

### 2.6 Day 2 commit + push + verify CI
- [ ] **Stage + commit + push**
  - Commit: `feat(orchestrator-loop+guardrails, sprint-53-5): US-3 Cat 9 Stage 3 → AgentLoop → HITLManager wiring (closes AD-Cat9-4)`
  - Push + verify CI

### 2.7 Day 2 progress.md update
- [ ] **Update progress.md with Day 2 actuals**
  - Commit: `docs(progress, sprint-53-5): Day 2 actuals`
  - Push

---

## Day 3 — US-1 Frontend governance approvals page (est. 6-8 hours)

### 3.1 US-1 governance_service.ts
- [ ] **Create `frontend/src/services/governance_service.ts`**
  - Content: ApprovalRequestSummary type + listPending() + decide() API client
  - DoD: imports clean + types match backend ApprovalRequest

### 3.2 US-1 ApprovalList + DecisionModal components
- [ ] **Create `pages/governance/approvals/ApprovalList.tsx`**
  - Tenant + role 過濾 list with sortable columns (request_uuid, tool_name, requested_by, age, risk_level, priority)
  - Real-time updates via SSE topic `governance.approvals.pending` OR polling fallback (30s)
  - DoD: list renders + sort works
- [ ] **Create `pages/governance/approvals/DecisionModal.tsx`**
  - Approve / Reject (with reason text) / Escalate (to higher role) buttons
  - POST via governance_service.decide()
  - DoD: modal renders + 3 paths callable
- [ ] **Create `pages/governance/approvals/index.tsx`**
  - Route page combining ApprovalList + DecisionModal
  - DoD: route renders without errors

### 3.3 US-1 router + governance index update
- [ ] **Register route `/governance/approvals` in router**
  - File: `frontend/src/router/index.tsx` (or wherever routes defined)
  - DoD: route resolvable
- [ ] **Modify `pages/governance/index.tsx`**
  - Add link / nav button to /governance/approvals
  - DoD: link clickable

### 3.4 US-1 Playwright e2e
- [ ] **Create `frontend/tests/e2e/governance/approvals.spec.ts`**
  - Test: login as reviewer → /governance/approvals → list pending → click row → modal → approve → backend state changes → loop resume → list updates
  - Multi-tenant test: tenant A reviewer 看不到 tenant B pending
  - DoD: e2e green
  - Verify: `cd frontend && npx playwright test tests/e2e/governance/approvals.spec.ts`

### 3.5 Day 3 sanity checks
- [ ] **Frontend lint + type check + build green**
  - Command: `cd frontend && npm run lint && npm run type-check && npm run build`
- [ ] **Playwright e2e green**

### 3.6 Day 3 commit + push + verify CI
- [ ] **Stage + commit + push**
  - Commit: `feat(frontend-governance, sprint-53-5): US-1 governance approvals page (List + Modal + service + e2e)`
  - Push + verify CI

### 3.7 Day 3 progress.md update
- [ ] **Update progress.md with Day 3 actuals**
  - Commit + push

---

## Day 4 — US-2 ApprovalCard + Final Verification + Retrospective + PR (est. full day)

### 4.1 US-2 ApprovalCard component
- [ ] **Create `frontend/src/components/chat/ApprovalCard.tsx`**
  - Props: approvalId, toolName, reason, riskLevel, state, onDecide
  - Risk level color coding (LOW=green / MEDIUM=yellow / HIGH=orange / CRITICAL=red)
  - Buttons: Approve / Reject (governance_service.decide())
  - Deep-link to `/governance/approvals/{id}`
  - DoD: component renders + buttons callable

### 4.2 US-2 ChatPage SSE integration
- [ ] **Modify `frontend/src/pages/chat-v2/ChatPage.tsx`**
  - Add SSE event handler for `ApprovalRequested` → render ApprovalCard inline
  - Add handler for `ApprovalDecided` → update card to disabled + result
  - DoD: existing chat flow not broken
- [ ] **Modify `frontend/src/stores/chat_store.ts`**
  - Add approvals slice (Map<approvalId, ApprovalState>)
  - Dedup by approval_uuid
  - DoD: store handles 50+ approvals without leak

### 4.3 US-2 Playwright e2e
- [ ] **Create `frontend/tests/e2e/chat/approval-card.spec.ts`**
  - Test: chat triggers sensitive tool → ApprovalRequested SSE → card appears → approve → ApprovalDecided SSE → card shows approved → loop resume
  - DoD: e2e green
  - Verify: `cd frontend && npx playwright test tests/e2e/chat/approval-card.spec.ts`

### 4.4 Sprint final verification
- [ ] **Cat 9 主流量 e2e**
  - Manual or scripted: chat triggers sensitive tool → Cat 9 Stage 3 → ApprovalCard → approve → Teams notification → governance page reflects → audit chain verify
- [ ] **Cross-tenant isolation grep**
  - Command: `grep -rn "tenant_id" backend/src/api/v1/audit.py backend/src/platform_layer/governance/audit/query.py` (verify enforcement)
- [ ] **LLM SDK leak check**
  - Command: `grep -rn "from openai\|from anthropic" backend/src/platform_layer/ backend/src/agent_harness/` → 0 results
- [ ] **Stage 3 stub elimination evidence**
  - Command: `grep -rn "ESCALATE.*stub\|TODO.*stage 3\|TODO.*HITL" backend/src/agent_harness/` → 0 results
- [ ] **Coverage gates**
  - governance/hitl/ ≥ 85%; api/v1/audit.py ≥ 80%; orchestrator_loop._cat9_tool_check 路徑 ≥ 90%
- [ ] **Full pytest run**
  - Command: `cd backend && python -m pytest -v --tb=short 2>&1 | tail -20`
  - DoD: 1020+ passed / 0 fail
- [ ] **6 V2 lint scripts green**
  - Command: 6 `scripts/lint/check_*.py` per `feedback_v2_lints_must_run_locally.md`
- [ ] **mypy --strict src/ tests/**
- [ ] **Frontend lint + type check + build + e2e all green**

### 4.5 Day 4 retrospective.md
- [ ] **Create `docs/03-implementation/agent-harness-execution/phase-53-5/sprint-53-5-governance-frontend/retrospective.md`**
- [ ] **Answer 6 mandatory questions** (per plan §Retrospective 必答)
  1. Sprint Goal achieved + 主流量 evidence
  2. estimated vs actual hours per US + total
  3. What went well (≥ 3 items + banked buffer source)
  4. What can improve (≥ 3 items + follow-up action)
  5. Drift documented (V2 9 disciplines self-check)
  6. Audit Debt logged (AD-Front-* + new findings)
- [ ] **Sprint Closeout Checklist** (verbatim from plan §Sprint Closeout)

### 4.6 PR open + closeout
- [ ] **Final commit + push**
  - Commit: `docs(closeout, sprint-53-5): retrospective + Day 4 progress + final marks`
  - Push
- [ ] **Open PR**
  - Title: `Sprint 53.5: Governance Frontend + Cat 9 Loop Wiring + Audit HTTP API`
  - Body: Summary + plan link + checklist link + 6 USs status + Anti-pattern checklist + verification evidence
  - Command: `gh pr create --title "..." --body "..."`
- [ ] **Wait for 4 active CI checks** (Backend CI / V2 Lint / E2E Tests / Lint+Type Check)
- [ ] **Normal merge after green** (solo-dev policy: review_count=0)
  - Command: `gh pr merge <num> --merge --delete-branch`
- [ ] **Verify main HEAD has merge commit**

### 4.7 Cleanup + memory update
- [ ] **Pull main + verify**
  - Command: `git checkout main && git pull origin main && git log --oneline -3`
- [ ] **Delete local feature branch**
  - Command: `git branch -d feature/sprint-53-5-governance-frontend`
- [ ] **Verify main 4 active CI green post-merge**
  - Command: `gh run list --branch main --limit 4`
- [ ] **Memory update**
  - Create: `memory/project_phase53_5_governance_frontend.md`
  - Add to MEMORY.md index
  - Mark V2 progress: 17/22 (77%); Cat 9 Level 5; AD-Cat9-4 closed; AD-Hitl-1~6 closed
- [ ] **Working tree clean check**
  - Command: `git status --short`

---

## Verification Summary（Day 4 final 必填）

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | All 6 USs delivered | [ ] | PR #__ merged |
| 2 | Cat 9 Level 5 achieved | [ ] | grep evidence + e2e test |
| 3 | AD-Cat9-4 closed | [ ] | retrospective AD log + Stage 3 e2e green |
| 4 | AD-Hitl-1~6 closed | [ ] | retrospective AD log |
| 5 | Frontend governance page live | [ ] | Playwright e2e green |
| 6 | Inline ApprovalCard live | [ ] | Playwright e2e green |
| 7 | 4hr resume window working | [ ] | integration test green |
| 8 | Cross-tenant isolation verified | [ ] | cross-tenant tests green |
| 9 | Audit endpoint paginated query | [ ] | integration tests green |
| 10 | Chain verify endpoint working | [ ] | integration tests green (verified + broken) |
| 11 | notification.yaml + ServiceFactory wired | [ ] | unit tests green + e2e Teams notification |
| 12 | pytest 1020+ / 0 fail | [ ] | command output |
| 13 | mypy --strict clean | [ ] | command output |
| 14 | 6 V2 lint scripts green | [ ] | CI |
| 15 | LLM SDK leak: 0 | [ ] | grep |
| 16 | Frontend lint + build + e2e green | [ ] | CI + local |
| 17 | coverage gates met | [ ] | pytest --cov report |
| 18 | Anti-pattern checklist 11 points | [ ] | retrospective |
| 19 | retrospective.md filled (6 questions) | [ ] | file exists with all 6 |
| 20 | Memory updated (project + index) | [ ] | files |
| 21 | Branches deleted (local + remote) | [ ] | git branch -a |
| 22 | V2 progress: 17/22 (77%) | [ ] | memory + GitHub |
