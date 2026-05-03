# Sprint 53.4 — Governance Frontend + V1 HITL/Risk 遷移 + §HITL 中央化 — Checklist

**Plan**: [sprint-53-4-plan.md](sprint-53-4-plan.md)
**Branch**: `feature/sprint-53-4-governance-hitl`
**Day count**: 5 (Day 0-4) | **Estimated total**: ~25-28 hours

> **格式遵守**：每 Day 同 53.3 結構（progress.md update + sanity + commit + verify CI）。每 task 3-6 sub-bullets（case / DoD / Verify command）。

---

## Day 0 — Setup + V1 HITL/Risk 探勘 + Baseline (est. 3-4 hours)

### 0.1 Branch + plan + checklist commit
- [ ] **Verify on main + clean**
  - Command: `git status && git branch --show-current` → expects `main` clean
  - DoD: working tree empty
- [ ] **Create branch + push plan/checklist**
  - Command: `git checkout -b feature/sprint-53-4-governance-hitl`
  - Stage: plan + checklist files
  - Commit: `docs(plan, sprint-53-4): plan + checklist for Cat 9 §HITL 中央化 + governance frontend`
  - Push: `git push -u origin feature/sprint-53-4-governance-hitl`
  - DoD: branch on remote with plan + checklist visible

### 0.2 GitHub issues 建立
- [ ] **Open 9 issues for US-1 ~ US-9** (or carry-over labels)
  - Each issue: title = `Sprint 53.4 US-X: <description>`
  - Labels: `sprint-53-4`, `phase-53`, `governance` / `hitl` / `frontend`
  - Link to plan
  - DoD: 9 issues open

### 0.3 V1 HITL/Risk 探勘（CRITICAL — 找不到就純新建不假裝遷移）
- [ ] **grep V1 archive for HITL/Risk modules**
  - Command: `find archived/v1-phase1-48/backend/src -path '*hitl*' -o -path '*risk*' -o -path '*approval*' -o -path '*governance*' 2>&1 | grep -v __pycache__`
  - DoD: 列出 V1 HITL/Risk 邏輯位置（或確認不存在 → 純新建）
- [ ] **Document findings in progress.md Day 0**
  - 找到的檔案逐個記錄 + 行數 + 主要 class/function
  - 評估：哪些可遷移、哪些重寫、哪些 V1 邏輯已不適用 V2 多租戶
  - DoD: progress.md Day 0 §V1 探勘結果完整

### 0.4 V2 既有結構 baseline
- [ ] **Inspect existing V2 governance + HITL state**
  - Files: `backend/src/agent_harness/hitl/`, `backend/src/agent_harness/_contracts/hitl.py`, `backend/src/agent_harness/tools/hitl_tools.py`, `backend/src/platform_layer/governance/`
  - Record: 各檔案行數、existing ABC 方法簽名、existing tools 行為
  - DoD: 知道哪些是 stub 哪些已可用

### 0.5 Cat 9 ToolGuardrail Stage 3 stub 位置確認
- [ ] **grep "ESCALATE" in tool_guardrail.py**
  - Command: `grep -n "ESCALATE\|stage_3\|stub" backend/src/agent_harness/guardrails/tool/tool_guardrail.py`
  - DoD: 找到 53.3 留下的 ESCALATE branch 位置 + 知道 US-3/US-9 要修哪幾行

### 0.6 alembic baseline (US-2 prep)
- [ ] **Verify alembic working state**
  - Command: `cd backend && alembic current`
  - DoD: alembic CLI 可運行 + 知道當前 migration head

### 0.7 Day 0 progress.md
- [ ] **Create `docs/03-implementation/agent-harness-execution/phase-53-4/sprint-53-4-governance-hitl/progress.md`**
- [ ] **Day 0 sections**: Setup completion / V1 探勘結果 / V2 既有結構 / baseline records
- [ ] Commit: `docs(progress, sprint-53-4): Day 0 setup + V1 探勘 + baselines`
  - Push: `git push`

---

## Day 1 — US-1 Risk Policy + US-2 HITLManager (上半) (est. 6-7 hours)

### 1.1 US-1 RiskLevel + RiskPolicy ABC
- [ ] **Create `platform_layer/governance/risk/levels.py`**
  - Content: `RiskLevel` enum (LOW/MEDIUM/HIGH/CRITICAL)
  - File header: docstring + Modification History
  - DoD: imports clean
- [ ] **Create `platform_layer/governance/risk/policy.py`**
  - Content: `RiskPolicy` ABC with `evaluate()` abstract method + `DefaultRiskPolicy` impl with YAML loader
  - YAML loading: `risk_policy.yaml` + per-tenant overlay support
  - DoD: imports clean + ABC structure 完整

### 1.2 US-1 risk_policy.yaml + tests
- [ ] **Create `backend/config/risk_policy.yaml`**
  - 4 tool patterns + 1 per_tenant_overlay example (per plan §Technical Specifications)
- [ ] **Create test_policy.py**
  - Cases: default risk / pattern matching priority / per-tenant overlay / unknown tool fallback
  - DoD: ≥ 5 test cases; coverage ≥ 85%
  - Verify: `cd backend && python -m pytest tests/unit/platform_layer/governance/risk/ -v`

### 1.3 US-2 HITLManager skeleton
- [ ] **Create `platform_layer/governance/hitl/state_machine.py`**
  - Content: state transitions + validation
  - DoD: pending → approved/rejected/escalated/expired 5 states 都有測試案例位
- [ ] **Create `platform_layer/governance/hitl/manager.py`**
  - Content: HITLManager skeleton（method signatures + docstrings；impl 寬鬆放 stub 給 Day 2 完整）
  - DoD: imports clean

### 1.4 US-2 DB model + migration
- [ ] **Create `infrastructure/db/models/hitl_approval.py`**
  - Content: SQLAlchemy ORM model per plan §DB Schema
  - DoD: imports clean
- [ ] **Generate alembic migration**
  - Command: `cd backend && alembic revision --autogenerate -m "add_hitl_approvals"`
  - Edit migration: 加 RLS policy + indexes per plan §DB Schema
  - DoD: migration file 完整，包含 indexes + RLS

### 1.5 US-2 state_machine unit tests
- [ ] **Create test_state_machine.py**
  - Cases: valid transitions / invalid transitions raise / approved → rejected 拒絕 / expire timeout transition
  - DoD: ≥ 6 test cases; coverage ≥ 85%
  - Verify: `python -m pytest tests/unit/platform_layer/governance/hitl/test_state_machine.py -v`

### 1.6 Day 1 sanity checks
- [ ] **mypy --strict 無新錯誤**
  - Command: `cd backend && python -m mypy src/platform_layer/governance/risk/ src/platform_layer/governance/hitl/state_machine.py src/platform_layer/governance/hitl/manager.py`
- [ ] **black + isort + flake8 green**
  - Command: `cd backend && python -m black --check src/platform_layer/governance/ && python -m isort --check src/platform_layer/governance/ && python -m flake8 src/platform_layer/governance/ tests/unit/platform_layer/governance/`

### 1.7 Day 1 commit + push + verify CI
- [ ] **Stage + commit + push**
  - Verify branch: `git branch --show-current`
  - Commit: `feat(governance, sprint-53-4): US-1 Risk policy + US-2 HITLManager skeleton + DB schema`
  - Push: `git push`
- [ ] **Verify CI runs and (if applicable) passes lint**
  - Command: `gh run list --branch feature/sprint-53-4-governance-hitl --limit 3`

### 1.8 Day 1 progress.md update
- [ ] **Update progress.md with Day 1 actuals**
  - Sections: Today's accomplishments / drift / banked-or-burned hours / blockers
  - Commit: `docs(progress, sprint-53-4): Day 1 actuals + drift notes`
  - Push: `git push`

---

## Day 2 — US-2 HITLManager (下半) + US-5 Reducers (est. 6-7 hours)

### 2.1 US-2 HITLManager full implementation
- [ ] **Implement `request_approval()` method**
  - Validates state machine transition / writes DB / triggers notifier hook (注入 Day 3)
  - DoD: integration test pass
- [ ] **Implement `decide()` method**
  - Validates: tenant match / state machine / reviewer role authorized
  - DoD: tenant cross-leak rejected (404)
- [ ] **Implement `pickup_pending()` with SKIP LOCKED**
  - SQL: `SELECT ... FROM hitl_approvals WHERE tenant_id = :t AND state = 'pending' AND ... FOR UPDATE SKIP LOCKED LIMIT :n`
  - DoD: integration test 模擬並發 pickup
- [ ] **Implement `expire_overdue()` background task**
  - Scan: `WHERE state = 'pending' AND expires_at < NOW()`
  - Apply fallback policy (config-driven: reject / escalate / approve_with_audit)
  - DoD: 3 fallback paths 都有測試

### 2.2 US-2 HITLManager integration tests
- [ ] **Create test_manager.py (unit) + test_multi_instance_pickup.py (integration)**
  - Unit cases: request_approval / decide / state machine validation / tenant isolation / role validation
  - Integration cases: 並發 pickup（兩 connections 同時 pickup → 各取一個 + 不重）/ expire_overdue 3 fallback paths
  - DoD: ≥ 12 cases total; coverage ≥ 85%
  - Verify: `python -m pytest tests/unit/platform_layer/governance/hitl/ tests/integration/platform_layer/governance/hitl/ -v`

### 2.3 US-5 HITLDecisionReducer + SubagentResultReducer
- [ ] **Create `agent_harness/state_mgmt/reducers/hitl_decision_reducer.py`**
  - Content: typed reducer; merge HITLDecisionEvent into LoopState (immutable update)
  - Edge cases: pending → approved / pending → rejected / pending → escalated
- [ ] **Create `agent_harness/state_mgmt/reducers/subagent_result_reducer.py`**
  - Content: typed reducer for subagent result merging (per Cat 11 prep)
- [ ] **Register reducers in `__init__.py`**
- [ ] **Tests**: test_hitl_decision_reducer.py + test_subagent_result_reducer.py
  - DoD: ≥ 8 cases total; coverage ≥ 85%
  - Verify: `python -m pytest tests/unit/agent_harness/state_mgmt/reducers/ -v`

### 2.4 Day 2 sanity checks
- [ ] **All Day 2 tests green**
  - Command: `python -m pytest tests/unit/platform_layer/governance/ tests/unit/agent_harness/state_mgmt/reducers/ tests/integration/platform_layer/governance/ -v`
- [ ] **Lint chain green**
  - Command: `python -m black --check src/ tests/ && python -m isort --check src/ tests/ && python -m flake8 src/platform_layer/governance/ src/agent_harness/state_mgmt/reducers/ tests/unit/platform_layer/governance/ tests/unit/agent_harness/state_mgmt/reducers/ && python -m mypy src/platform_layer/governance/ src/agent_harness/state_mgmt/reducers/`

### 2.5 Day 2 commit + push + verify CI
- [ ] **Stage + commit + push**
  - Commit: `feat(governance+state-mgmt, sprint-53-4): US-2 HITLManager full impl + US-5 Cat 7 reducers`
  - Push + verify CI

### 2.6 Day 2 progress.md update
- [ ] **Update progress.md with Day 2 actuals + drift**
  - Commit: `docs(progress, sprint-53-4): Day 2 actuals`
  - Push

---

## Day 3 — US-3 §HITL 中央化 + US-4 Audit API + US-6 Notifier (est. 6-7 hours)

### 3.1 US-3 §HITL 中央化 — refactor Cat 2 hitl_tools
- [ ] **Refactor `agent_harness/tools/hitl_tools.py` `request_approval` tool**
  - 原行為: 直接寫 DB
  - 改為: 注入 HITLManager + 呼叫 `manager.request_approval()`
  - DoD: 既有測試仍 pass + 新 integration test 證明 single-source

### 3.2 US-3 §HITL 中央化 — Cat 9 ToolGuardrail Stage 3 真整合
- [ ] **Modify `agent_harness/guardrails/tool/tool_guardrail.py`**
  - Replace Stage 3 ESCALATE stub with HITLManager call
  - 整合 RiskPolicy（從 Day 1 US-1）：stage decision 包含 risk level
  - DoD: grep 證據 — 0 個 ESCALATE stub remaining

### 3.3 US-3 integration tests
- [ ] **Create test_hitl_centralization.py**
  - Cases: Cat 2 tool flow + Cat 9 Stage 3 flow + cross-call dedup + tenant isolation
  - DoD: ≥ 5 cases; coverage cross 涉及檔案 ≥ 85%
  - Verify: `python -m pytest tests/integration/agent_harness/governance/test_hitl_centralization.py -v`

### 3.4 US-4 Audit Query API
- [ ] **Create `platform_layer/governance/audit/query.py`**
  - Content: AuditQuery service with paginated query + chain verify
  - DoD: imports clean
- [ ] **Create `api/v1/audit.py` FastAPI router**
  - Endpoints: GET /api/v1/audit/log + GET /api/v1/audit/verify-chain
  - RBAC: role check（auditor / admin only）
  - Tenant isolation: 強制 current_tenant filter
  - DoD: imports clean
- [ ] **Register router in `api/v1/__init__.py`**

### 3.5 US-4 audit API integration tests
- [ ] **Create test_audit_endpoints.py**
  - Cases: paginated query / cross-tenant rejected (404) / non-auditor role rejected (403) / chain verify endpoint correct
  - DoD: ≥ 6 cases; coverage ≥ 80%
  - Verify: `python -m pytest tests/integration/api/test_audit_endpoints.py -v`

### 3.6 US-6 HITLNotifier ABC + TeamsWebhookNotifier
- [ ] **Create `platform_layer/governance/hitl/notifier.py`**
  - Content: HITLNotifier ABC with `notify(approval: ApprovalRequest)` abstract method
- [ ] **Create `platform_layer/governance/hitl/notifiers/teams_webhook.py`**
  - Content: TeamsWebhookNotifier impl + AdaptiveCard message format
  - Failure handling: best-effort + audit log
- [ ] **Wire notifier into HITLManager**
  - On `request_approval()` success → call `notifier.notify()` (best-effort)
- [ ] **Create `backend/config/notification.yaml`**
- [ ] **Tests**: test_notifier.py
  - Cases: notify with mock webhook server / failure not blocking HITL flow / per-tenant override
  - DoD: ≥ 4 cases; coverage ≥ 80%

### 3.7 Day 3 mid-push (CI feedback intermediate)
- [ ] **All Day 3 tests green + lint chain**
- [ ] **Commit + push**
  - Commit: `feat(governance, sprint-53-4): US-3 §HITL 中央化 + US-4 Audit API + US-6 Teams notifier`
  - Push + verify CI

### 3.8 Day 3 progress.md update
- [ ] Update progress.md
- [ ] Commit + push

---

## Day 4 — US-7 + US-8 Frontend + US-9 e2e + Retrospective + PR (est. full day)

### 4.1 US-7 Frontend governance approvals page
- [ ] **Create `pages/governance/approvals/index.tsx`**
  - Route: `/governance/approvals`
  - Imports: ApprovalList component
- [ ] **Create `ApprovalList.tsx`**
  - Tenant + role filtered pending list with sortable columns
  - Real-time updates via SSE (or polling fallback)
- [ ] **Create `DecisionModal.tsx`**
  - Approve / Reject (with reason) / Escalate (to higher role)
  - POST to backend HITL decision endpoint
- [ ] **Create `services/governance_service.ts`**
  - API client for /api/v1/governance/approvals/*

### 4.2 US-7 Playwright e2e
- [ ] **Create `frontend/tests/e2e/governance/approvals.spec.ts`**
  - Test: list pending → click → approve flow → backend state changes → loop resume
  - DoD: e2e green

### 4.3 US-8 Inline Chat ApprovalCard
- [ ] **Create `frontend/src/components/chat/ApprovalCard.tsx`**
  - Component: tool name + reason + risk + buttons + deep-link
- [ ] **Modify `frontend/src/pages/chat-v2/ChatPage.tsx`**
  - Add SSE event handler for `ApprovalRequested` + `ApprovalDecided`
  - Render ApprovalCard inline
- [ ] **Create `frontend/tests/e2e/chat/approval-card.spec.ts`**
  - Test: chat triggers approval → card appears → approve → loop resume
  - DoD: e2e green

### 4.4 US-9 Stage 3 e2e (carryover AD-Cat9-4)
- [ ] **Create `tests/integration/agent_harness/governance/test_stage3_escalation_e2e.py`**
  - Test: sensitive tool → Cat 9 GuardrailEngine → ToolGuardrail Stage 3 → HITLManager pending → Teams notification fired → approve → loop resume → audit chain verify
  - DoD: full e2e + audit hash chain integrity

### 4.5 Sprint final verification
- [ ] **Cat 8 ↔ Cat 9 ↔ §HITL boundary check**
  - Command: `python scripts/check_cross_category_imports.py`
- [ ] **LLM SDK leak check**
  - Command: `grep -rn "from openai\|from anthropic" backend/src/platform_layer/ backend/src/agent_harness/` → 0 results
- [ ] **Anti-pattern grep evidence (主流量)**
  - Stage 3 ESCALATE 0 stubs left
  - All ApprovalRequest creation centralized through HITLManager
- [ ] **Coverage gates**
  - governance/hitl/ ≥ 85%
  - governance/risk/ ≥ 85%
  - governance/audit/ ≥ 80%
- [ ] **Full pytest run**
  - Command: `python -m pytest -v --tb=short 2>&1 | tail -20`
  - DoD: 970+ passed / 0 fail
- [ ] **6 V2 lint scripts green**
  - Command: 6 scripts per project lint config
- [ ] **mypy --strict src/ tests/**

### 4.6 Day 4 retrospective.md
- [ ] **Create `docs/03-implementation/agent-harness-execution/phase-53-4/sprint-53-4-governance-hitl/retrospective.md`**
- [ ] **Answer 6 mandatory questions** (per plan §Retrospective 必答)
  1. Sprint Goal achieved + main流量 evidence
  2. estimated vs actual hours per US + total
  3. What went well (≥ 3 items + banked buffer source)
  4. What can improve (≥ 3 items + follow-up action)
  5. Drift documented (V2 9 disciplines self-check)
  6. Audit Debt logged (AD-Hitl-* + new findings)
- [ ] **Sprint Closeout Checklist** (verbatim from plan §Sprint Closeout)

### 4.7 PR open + closeout
- [ ] **Final commit + push**
  - Commit: `docs(closeout, sprint-53-4): retrospective + Day 4 progress + final marks`
  - Push
- [ ] **Open PR**
  - Title: `Sprint 53.4: Governance Frontend + V1 HITL/Risk 遷移 + §HITL 中央化`
  - Body: Summary + plan link + checklist link + 9 USs status + Anti-pattern checklist + verification evidence
  - Command: `gh pr create --title "..." --body "..."`
- [ ] **Wait for 4 active CI checks** (Lint+Type Check+Test PG16 / Backend E2E / E2E Summary / v2-lints)
- [ ] **Normal merge after green** (solo-dev policy: review_count=0)
  - Command: `gh pr merge <num> --merge --delete-branch`
- [ ] **Verify main HEAD has merge commit**

### 4.8 Cleanup + memory update
- [ ] **Pull main + verify**
  - Command: `git checkout main && git pull origin main && git log --oneline -3`
- [ ] **Delete local feature branch**
  - Command: `git branch -d feature/sprint-53-4-governance-hitl`
- [ ] **Verify main 4 active CI green post-merge**
  - Command: `gh run list --branch main --limit 4`
- [ ] **Memory update**
  - Create: `memory/project_phase53_4_governance_hitl.md`
  - Add to MEMORY.md index
  - Mark V2 progress: 16/22 (73%); Cat 9 Level 4+; §HITL 中央化 complete; AD-Cat9-4 closed
- [ ] **Working tree clean check**
  - Command: `git status --short`

---

## Verification Summary（Day 4 final 必填）

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | All 9 USs delivered | [ ] | PR #__ merged |
| 2 | Cat 9 Level 4+ achieved | [ ] | grep evidence + e2e test |
| 3 | §HITL 中央化 complete | [ ] | grep ApprovalRequest creation points all via HITLManager |
| 4 | AD-Cat9-4 closed | [ ] | retrospective AD log + e2e test |
| 5 | Frontend governance + chat approval card live | [ ] | 2 Playwright e2e green |
| 6 | Multi-instance pickup verified | [ ] | integration test green |
| 7 | 4hr resume window working | [ ] | integration test green |
| 8 | Tenant isolation verified | [ ] | cross-tenant tests green |
| 9 | Teams webhook integrated (best-effort) | [ ] | notifier test green + failure-not-blocking verified |
| 10 | pytest 970+ / 0 fail | [ ] | command output |
| 11 | mypy --strict clean | [ ] | command output |
| 12 | 6 V2 lint scripts green | [ ] | CI |
| 13 | LLM SDK leak: 0 | [ ] | grep |
| 14 | coverage gates met (85/85/80) | [ ] | pytest --cov report |
| 15 | Anti-pattern checklist 11 points | [ ] | retrospective |
| 16 | retrospective.md filled (6 questions) | [ ] | file exists with all 6 |
| 17 | Memory updated (project + index) | [ ] | files |
| 18 | Branches deleted (local + remote) | [ ] | git branch -a |
| 19 | V2 progress: 16/22 (73%) | [ ] | memory + GitHub |
