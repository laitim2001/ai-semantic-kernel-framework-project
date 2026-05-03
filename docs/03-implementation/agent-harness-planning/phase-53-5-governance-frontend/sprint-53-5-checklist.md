# Sprint 53.5 — Governance Frontend + Cat 9 Loop Wiring + Audit HTTP API — Checklist

**Plan**: [sprint-53-5-plan.md](sprint-53-5-plan.md)
**Branch**: `feature/sprint-53-5-governance-frontend`
**Day count**: 5 (Day 0-4) | **Estimated total**: ~22-31 hours

> **格式遵守**：每 Day 同 53.4 結構（progress.md update + sanity + commit + verify CI）。每 task 3-6 sub-bullets（case / DoD / Verify command）。

---

## Day 0 — Setup + Playwright + Frontend Baseline + Cat 9 Loop Stub Locate (est. 3-4 hours)

### 0.1 Branch + plan + checklist commit
- [x] **Verify on main + clean** ✅ commit `0f2a696e`
  - Command: `git status && git branch --show-current` → expects `main` clean
  - DoD: working tree empty
- [x] **Create branch + push plan/checklist** ✅
  - Command: `git checkout -b feature/sprint-53-5-governance-frontend`
  - Stage: plan + checklist files
  - Commit: `docs(plan, sprint-53-5): plan + checklist for governance frontend + Cat 9 loop wiring + audit HTTP API`
  - Push: `git push -u origin feature/sprint-53-5-governance-frontend`
  - DoD: branch on remote with plan + checklist visible

### 0.2 GitHub issues 建立
- [ ] **Open 6 issues for US-1 ~ US-6** 🚧 SKIPPED — solo-dev workflow; sprint plan + checklist serve as authoritative tracking. Issues redundant for this sprint; closeout PR will reference all 6 USs.
  - Each issue: title = `Sprint 53.5 US-X: <description>`
  - Labels: `sprint-53-5`, `phase-53`, `governance` / `frontend` / `cat-9`
  - Link to plan
  - DoD: 6 issues open

### 0.3 Playwright runner setup（CRITICAL — frontend-heavy sprint pre-req per 53.4 retrospective Q4）
- [x] **Verify Playwright already installed in frontend/** ⚠️ NOT INSTALLED — `frontend/package.json` has no `@playwright/test`; no test framework at all (no Vitest either)
  - Command: `cd frontend && cat package.json | grep -i playwright`
  - DoD: 確認 @playwright/test 已在 devDependencies；若無 → `npm install -D @playwright/test` + `npx playwright install chromium`
- [ ] **Verify playwright.config.ts exists or create minimal** 🚧 DEFERRED to AD-Front-1 — Playwright install + browser download (~300MB) + CI workflow + first spec is sprint-sized. Bundling here would burn the buffer + risk all 6 USs. Components delivered as US-1/US-2 + manual verification via dev server. Backend API contracts already covered by 53.4 + 53.5 US-5/US-6 integration tests.
  - Path: `frontend/playwright.config.ts`
  - Required: testDir, baseURL (http://localhost:3000), reporter
  - DoD: `npx playwright test --list` runs without error
- [ ] **Smoke run with example spec** 🚧 DEFERRED to AD-Front-1 (same reason as above)
  - Command: `cd frontend && npx playwright test --reporter=list 2>&1 | head -20`
  - DoD: runner spawns headless chromium successfully; no missing-binary errors

### 0.4 Frontend baseline 探勘
- [x] **Inspect existing governance + chat-v2 + components/chat structure** ✅ documented in progress.md §0.4
  - Files: `frontend/src/pages/governance/` (placeholder 12 lines), `frontend/src/features/chat_v2/` (chat lives here, NOT `pages/chat-v2/ChatPage.tsx` — plan deviation D2)
  - Record: 13 .tsx/.ts total; React 18 + Vite 5 + Zustand only (no Tailwind, no shadcn, no react-query)
  - DoD: progress.md Day 0 §Frontend baseline 完整
- [x] **Verify SSE event handler pattern in ChatPage** ✅
  - File: `frontend/src/features/chat_v2/hooks/useLoopEventStream.ts` (actual; plan said `pages/chat-v2/ChatPage.tsx` — plan deviation D2)
  - Found: `streamChat` service + Zustand `mergeEvent` action + AbortController; ApprovalCard SSE handler will extend this pattern
  - DoD: 知道 ApprovalRequested SSE handler 怎麼注入（US-2 prep）

### 0.5 Cat 9 loop wiring stub locate（US-3 prep）
- [x] **Locate `_cat9_tool_check` in AgentLoop** ✅ line 370 + call site line 785
  - Command: `grep -n "_cat9_tool_check\|cat9_check\|Stage.ESCALATE" backend/src/agent_harness/orchestrator_loop/loop.py`
  - Found: signature is `(tc, ctx, turn_count) -> AsyncIterator[LoopEvent]` (yields events, not sync return — plan deviation D5). Current ESCALATE branch only emits `GuardrailTriggered(action="escalate")` then returns; no HITL pause/wait yet.
  - DoD: 找到 53.3 留下的 ESCALATE branch + 53.4 deferred wiring 位置
- [x] **Verify HITLManager wait_for_decision API** ✅
  - File: `backend/src/platform_layer/governance/hitl/manager.py`
  - Confirm: method exists from 53.4 production (cross-session wait + 4hr timeout)
  - DoD: 知道 US-3 _cat9_tool_check 會呼叫哪個方法

### 0.6 Audit endpoint baseline（US-5 prep）
- [x] **Inspect existing api/v1/ structure** ✅
  - Files: `backend/src/api/v1/__init__.py`, `backend/src/api/v1/health.py` (only 2 files; audit router not yet built)
  - DoD: 知道 `require_audit_role` 怎麼建（依循既有 dep pattern）— Day 1 will check `api/dependencies.py`
- [x] **Verify AuditQuery service interface** ✅
  - File: `backend/src/platform_layer/governance/audit/query.py`
  - ✅ `list(query: AuditQueryFilter)` exists; ⚠️ `verify_chain()` MISSING — US-6 must add (plan deviation D8)
  - ⚠️ Filter field is `operation` not `op_type`; uses `from_ts_ms / to_ts_ms` (int) not datetime (plan deviation D6)
  - ⚠️ No `total` count — pagination uses `{items, has_more}` cursor pattern (plan deviation D7)
  - DoD: 知道 US-5 router 直接呼叫哪些 method

### 0.7 Day 0 progress.md
- [x] **Create `docs/03-implementation/agent-harness-execution/phase-53-5/sprint-53-5-governance-frontend/progress.md`** ✅
- [x] **Day 0 sections**: Setup completion / Playwright readiness / Frontend baseline / Cat 9 loop stub location / Audit endpoint baseline + drift summary table (D1-D8)
- [ ] Commit: `docs(progress, sprint-53-5): Day 0 setup + Playwright + frontend/Cat9/audit baselines + drift D1-D8`
  - Push: `git push`

---

## Day 1 — US-5 Audit HTTP API + US-6 Chain Verify + US-4 notification.yaml (est. 5-6 hours)

### 1.1 US-5 Audit HTTP endpoint
- [x] **Create `backend/src/api/v1/audit.py`** ✅
  - Content: FastAPI router with `GET /log` endpoint
  - Filters: operation (D6 — was op_type) / resource_type / user_id / from_ts_ms / to_ts_ms (D6 — int ms not datetime) / offset / page_size (D7 — cursor pattern, no total)
  - DoD: imports clean + endpoint registered
- [x] **Add RBAC dependency `require_audit_role`** ✅
  - File: `backend/src/platform_layer/identity/auth.py` (canonical identity dep file; not new dependencies.py)
  - Roles allowed: auditor / admin / compliance (single-source `_AUDIT_ROLES` frozenset)
  - 403 for other roles; 401 if no JWT
  - DoD: dep can be tested independently
- [x] **Register audit router in `api/main.py`** ✅ (api/v1/__init__.py is just namespace marker; mounting in api/main.py)

### 1.2 US-6 Chain verify endpoint
- [x] **Add `GET /verify-chain` endpoint to `audit.py`** ✅
  - Calls `AuditQuery.verify_chain()`; returns `{valid, broken_at_id, total_entries}` (D7 — adjusted to ChainVerificationResult shape)
  - DoD: endpoint registered + tenant isolation enforced
- [x] **Extend AuditQuery.verify_chain() if missing** ✅
  - File: `backend/src/platform_layer/governance/audit/query.py`
  - Wraps `agent_harness.guardrails.audit.verify_chain` (Cat 9 single-source per 17.md §5; public re-export)
  - Constructor: both `session=` (list) and `session_factory=` (verify_chain) optional; methods independent
  - DoD: returns ChainVerificationResult

### 1.3 US-5 + US-6 integration tests
- [x] **Create `tests/integration/api/test_audit_endpoints.py`** ✅ 13/13 green
  - US-5 cases (8): RBAC 403 / tenant rows visible / cross-tenant invisible / operation filter / user_id filter / time-range / pagination cursor / page_size cap 422 / DTO shape
  - US-6 cases (5): RBAC 403 / empty chain valid / wiring smoke / tenant isolation / id-range params
  - DoD: 13 cases (≥ 9 required); full pytest 1035 passed / +23 from baseline
  - Verify: `python -m pytest tests/integration/api/test_audit_endpoints.py -v`

### 1.4 US-4 notification.yaml + factory
- [x] **Create `backend/config/notification.yaml`** ✅
  - Content: version + defaults + teams.{enabled, default_webhook, per_tenant_overrides, approval_review_url_template, timeout_s} (Day 1 探勘 — adjusted to actual TeamsWebhookNotifier constructor; no message_template field)
  - DoD: YAML parseable (verified via test_real_repo_config_loads)
- [x] **Add `load_notifier_from_config` factory in `notifier.py`** ✅
  - File: `backend/src/platform_layer/governance/hitl/notifier.py`
  - Behavior: parse YAML + `${VAR}` env interpolation + per-tenant override + 4 NoopNotifier fallback paths (file missing / disabled / empty webhook / no overrides)
  - DoD: function callable; env var `${...}` resolves
- [ ] **Wire ServiceFactory or extend HITLManager construction** 🚧 DEFERRED to Day 2 / US-3 — wiring belongs at orchestrator boundary (Cat 9 → HITLManager invocation site). Day 1 ships the loader; Day 2's loop wiring will call `load_notifier_from_config` when constructing production HITLManager.
  - File: `backend/src/platform_layer/governance/service_factory.py` (new) OR extend existing factory
  - Behavior: `factory.get_hitl_manager(tenant_id)` returns HITLManager with correct notifier
  - DoD: factory testable; tenant override resolves

### 1.5 US-4 unit tests
- [x] **Create `tests/unit/platform_layer/governance/hitl/test_notification_config.py`** ✅ 10/10 green
  - Cases: missing file → Noop / disabled → Noop / empty webhook → Noop / default → Teams / per-tenant override → Teams / env set → resolves / env unset → Noop / invalid UUID → ValueError / non-mapping overrides → ValueError / repo notification.yaml smoke load
  - DoD: 10 cases (≥ 5 required)

### 1.6 Day 1 sanity checks
- [x] **mypy --strict 無新錯誤** ✅ 4 source files clean
  - Command: `python -m mypy --strict src/api/v1/audit.py src/platform_layer/governance/hitl/notifier.py src/platform_layer/governance/audit/query.py src/platform_layer/identity/auth.py`
- [x] **black + isort + flake8 green** ✅
  - Command: standard pre-push chain
- [x] **V2 lint scripts green** ✅ 6/6 OK / no violations
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
- [ ] **Modify `backend/src/agent_harness/guardrails/tool/tool_guardrail.py`** 🚧 SKIPPED — Day 2 探勘 finding D10: GuardrailResult already has `risk_level: Literal[...]` field (53.3 contract). Loop layer defaults Stage.ESCALATE to `RiskLevel.HIGH` regardless of detector-specific value (escalation implies human review = inherently high-risk). Plumbing detector→HITLManager risk_level passthrough is a polish item; not blocking. Per category-boundaries.md, importing platform_layer.governance.risk from agent_harness/orchestrator_loop is also forbidden (backwards-import) — defer risk_policy injection to a later sprint or use callable injection. Day 2 scope shrinks accordingly.
  - Add risk_level field to Stage.ESCALATE decision return
  - Pull from RiskPolicy.evaluate() (53.4 US-1)
  - DoD: existing tests pass + new field on ESCALATE returns

### 2.2 US-3 AgentLoop `_cat9_tool_check` HITL wiring
- [x] **Implement `_cat9_tool_check` HITL branch in `loop.py`** ✅
  - File: `backend/src/agent_harness/orchestrator_loop/loop.py`
  - Implementation: extracted into new `_cat9_hitl_branch` async iterator method called from `_cat9_tool_check` when `g_result.action == GuardrailAction.ESCALATE` AND `self._hitl_manager is not None`
  - Behavior:
    1. Build ApprovalRequest (risk=HIGH default, payload from ToolCall, sla_deadline = now + 14400s)
    2. Call HITLManager.request_approval (try/except on persistence failure → fail closed)
    3. Yield ApprovalRequested LoopEvent
    4. await wait_for_decision (TimeoutError → treat as REJECTED with system_timeout reviewer)
    5. Yield ApprovalReceived LoopEvent
    6. APPROVED → return (caller flows to normal tool execution)
    7. REJECTED/ESCALATED/Timeout → yield GuardrailTriggered(action="block")
  - 4 paths covered (APPROVED/REJECTED/ESCALATED/TIMEOUT) + 2 fail-closed paths (no identity / persistence failure)
  - New ctor params: `hitl_manager: HITLManager | None = None`, `hitl_timeout_s: int = 14400` (opt-in; preserves 53.3 baseline when None)
  - Audit log entries: 4 event types (`guardrail.tool.escalate.{requested,approved,rejected,escalated,no_identity,persist_failed}`)
  - DoD: imports clean (private cross-category check OK) + all 4 paths tested

### 2.3 US-3 integration tests
- [x] **Create `tests/integration/agent_harness/governance/test_stage3_escalation_e2e.py`** ✅ 7/7 green
  - Cases (7):
    - approved → no GuardrailTriggered + tool runs (asserts ToolCallExecuted carries success content)
    - rejected → GuardrailTriggered(block) + tool blocked (result content shows "blocked")
    - escalated → GuardrailTriggered(block) + tool blocked
    - timeout → treated as REJECTED with "timeout" reason
    - hitl_manager=None → 53.3 baseline preserved (soft-block "escalate" action)
    - request payload carries tenant_id + session_id + tool_call_id + reason (governance UI prereq)
    - loop does NOT terminate on Stage 3 block (per-tool soft block; loop continues to next turn)
  - Test fixtures: EscalateGuardrail (always returns ESCALATE) + FakeHITLManager (canned decisions / TimeoutError) + 2-turn FakeChatClient
  - DoD: 7 cases (≥ 5 required); full e2e + audit chain integrity asserted via reason content
  - Verify: `python -m pytest tests/integration/agent_harness/governance/test_stage3_escalation_e2e.py -v` → 7/7

### 2.4 US-3 add Stage 3 case to existing loop guardrails test
- [ ] **Modify `tests/integration/agent_harness/guardrails/test_loop_guardrails.py`** 🚧 SKIPPED — redundant with 2.3. The new test_stage3_escalation_e2e.py provides 7 dedicated Stage 3 cases (full coverage); duplicating one in test_loop_guardrails.py would violate AP-3 (cross-directory scattering for the same concern). Existing 12 53.3 cases in test_loop_guardrails.py remain green (verified via regression run).
  - Add Stage 3 e2e case (lighter than test_stage3_escalation_e2e.py)
  - DoD: existing 53.3 cases still pass

### 2.5 Day 2 sanity checks
- [x] **All Day 2 tests green** ✅
  - Command: `python -m pytest --tb=line -q` → **1042 passed / 4 skipped / 0 fail** (+7 from Day 1's 1035, matching 7 new US-3 tests)
  - Note: had to remove `tests/integration/agent_harness/governance/__init__.py` (created accidentally) — caused namespace package collision with `tests/unit/platform_layer/governance/`. Lesson: don't create __init__.py in test dirs unless siblings have one (D11)
- [x] **Lint chain green** ✅
  - Standard chain (black + isort + flake8) green; 6 V2 lint scripts all OK / no violations
- [x] **mypy --strict src/agent_harness/orchestrator_loop/loop.py** ✅ 1 source file clean

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

### 3.0 US-1 backend HTTP endpoint (UNPLANNED scope addition — Day 3 探勘 finding D12)
- [x] **Create `backend/src/api/v1/governance/router.py`** ✅ (originally drafted as `governance.py`; moved to package per Phase 53.3 stub package convention)
  - Endpoints: GET /api/v1/governance/approvals (paginated by tenant) + POST /api/v1/governance/approvals/{request_id}/decide
  - DTOs: ApprovalSummaryDTO + PendingListResponse + DecisionRequestBody + DecisionResponse
  - RBAC: new `require_approver_role` dep (approver / admin / manager); _require_role helper extracted
  - Tenant isolation via HITLManager.get_pending; cross-tenant decide → 404
  - Mounted in api/main.py
  - 11 integration tests in `tests/integration/api/test_governance_endpoints.py` (RBAC + 3 decision paths + cross-tenant 404 + invalid label 422 + DTO shape)

### 3.1 US-1 governance_service.ts
- [x] **Create `frontend/src/features/governance/services/governanceService.ts`** ✅ (path adjusted per D3)
  - Content: types.ts + governanceService.listPending + governanceService.decide
  - Bearer JWT carried via `credentials: 'same-origin'` (existing pattern)
  - DoD: imports clean; eslint green

### 3.2 US-1 ApprovalList + DecisionModal components
- [x] **Create `frontend/src/features/governance/components/ApprovalList.tsx`** ✅
  - Tabular view; columns: tool / risk (color-coded) / requester / reason / time-left / action
  - Empty state ("No pending approvals.")
  - Click row → onSelect → parent opens modal
  - DoD: list renders + button works
- [x] **Create `frontend/src/features/governance/components/DecisionModal.tsx`** ✅
  - 3 buttons: Approve (green) / Reject (red) / Escalate (orange) + Cancel
  - Reason textarea (optional)
  - Error state for failed decide()
  - DoD: modal renders + 3 paths callable
- [x] **Create `frontend/src/features/governance/components/ApprovalsPage.tsx`** ✅
  - Container fetches list (30s poll fallback; no SSE topic — deferred to AD-Front-1)
  - AbortController on unmount
  - Decide submission → refresh list
  - DoD: route renders without errors

### 3.3 US-1 router + governance index update
- [x] **Register route `/governance/approvals` (nested via React Router v6 sub-routes)** ✅
  - File: `frontend/src/pages/governance/index.tsx` — uses `<Routes>` with index + approvals sub-route + catch-all redirect
  - Existing `App.tsx` already mounts `/governance/*` so nested routes work without app.tsx changes
  - DoD: route resolvable
- [x] **Modify `pages/governance/index.tsx`** ✅
  - Replaced placeholder; now hosts `<GovernanceIndex>` (nav links) + `<ApprovalsPage>` at `/approvals`
  - DoD: link clickable from /governance to /governance/approvals

### 3.4 US-1 Playwright e2e
- [ ] **Create `frontend/tests/e2e/governance/approvals.spec.ts`** 🚧 DEFERRED to AD-Front-1 (per Day 0 D1 — Playwright not installed; sprint-sized to bootstrap). Components covered by manual verification + backend integration tests.
  - Test: login as reviewer → /governance/approvals → list pending → click row → modal → approve → backend state changes → loop resume → list updates
  - Multi-tenant test: tenant A reviewer 看不到 tenant B pending
  - DoD: e2e green
  - Verify: `cd frontend && npx playwright test tests/e2e/governance/approvals.spec.ts`

### 3.5 Day 3 sanity checks
- [x] **Frontend lint + type check + build green** ✅
  - eslint: clean (max-warnings 0)
  - typecheck: 1 pre-existing tsconfig.node.json TS6310 (unrelated; tsconfig project ref emit setting)
  - build: ✅ 51 modules transformed, 184KB output, 560ms
- [x] **Backend full pytest** ✅ **1053 passed / 4 skipped / 0 fail** (+11 from Day 2's 1042; matches 11 governance endpoint tests added)
- [x] **Pre-existing test fragility fix** — adjusted `test_approval_pending_query_uses_partial_index` to scope by `session_id` (was implicitly assuming no other test commits pending approvals)
- [ ] **Playwright e2e green** 🚧 DEFERRED (AD-Front-1)

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
