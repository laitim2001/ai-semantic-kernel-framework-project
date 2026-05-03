# Sprint 53.6 — Frontend E2E (Playwright) + Production HITL Wiring — Checklist

**Plan**: [sprint-53-6-plan.md](sprint-53-6-plan.md)
**Branch**: `feature/sprint-53-6-frontend-e2e-prod-hitl`
**Day count**: 5 (Day 0-4) | **Estimated total**: ~18-25 hours

> **格式遵守**：每 Day 同 53.5 結構（progress.md update + sanity + commit + verify CI）。每 task 3-6 sub-bullets（case / DoD / Verify command）。

---

## Day 0 — Setup + Playwright 探勘 + Chat Router HITL Wiring 探勘 + 53.5 Components Verify (est. 2-3 hours)

### 0.1 Branch + plan + checklist commit
- [x] **Verify on main + clean** ✅ pre-branch only `phase-53-6-*/` untracked
  - Command: `git status && git branch --show-current` → expects `main` clean
  - DoD: working tree empty (untracked plan dir is the new sprint files only)
- [x] **Create branch + push plan/checklist** ✅ commit `10ab34a6`
  - Command: `git checkout -b feature/sprint-53-6-frontend-e2e-prod-hitl`
  - Stage: plan + checklist files
  - Commit: `docs(plan, sprint-53-6): plan + checklist for frontend e2e + production HITL wiring`
  - Push: `git push -u origin feature/sprint-53-6-frontend-e2e-prod-hitl`
  - DoD: branch on remote with plan + checklist visible (set up to track origin)

### 0.2 Playwright 探勘（US-1 prep — CRITICAL，53.5 Day 0 已確認未安裝）
- [x] **Re-confirm Playwright not installed** ✅ `grep -i playwright frontend/package.json` → 0 matches
  - Command: `cd frontend && cat package.json | grep -i playwright`
  - DoD: 確認 @playwright/test 不在 devDependencies
- [x] **Decide local install path** ✅ Day 1 will run `npm install -D @playwright/test` then `npx playwright install chromium` (~300MB)
  - Note: Day 1 才實際 install + browser download (~300MB)
  - DoD: 確認 npm registry 可達 + 預估安裝時間
- [x] **Inspect existing CI workflow shape** ✅ `frontend-ci.yml` 49 lines as template
  - Files: `.github/workflows/frontend-ci.yml`
  - Pattern: setup-node@v4 + cache npm + paths filter + lint + build steps；reuse for playwright-e2e.yml
  - DoD: 知道新 workflow 該複用哪些既有 pattern

### 0.3 Chat Router HITL Wiring 探勘（US-4 prep）
- [x] **Locate AgentLoopImpl construction sites in chat handler** ✅ `handler.py` line 102 (echo_demo) + line 138 (real_llm)
  - Both ctor calls do NOT pass `hitl_manager` → confirms AD-Front-2 gap
  - Command: `grep -n "AgentLoopImpl\|hitl_manager" backend/src/api/v1/chat/handler.py`
  - DoD: 找到 ctor 呼叫位置 + 確認 hitl_manager 目前是否傳入（預期：未傳）
- [x] **Verify ServiceFactory 是否已存在或需新建** ✅ NOT EXIST → US-5 全新建
  - Command: `find backend/src/platform_layer/governance -name "service_factory.py"`
  - DoD: 知道 US-5 是新建還是擴充
- [x] **Inspect existing DI patterns** ✅ Single-source = `platform_layer/identity/auth.py` (5 deps); `api/dependencies.py` does NOT exist (D1)
  - File: `backend/src/platform_layer/identity/auth.py` (canonical DI dep file per 53.5)
  - Existing deps: get_current_tenant / get_current_user_id / require_audit_role / require_approver_role / _require_role
  - Decision deferred to Day 4 code phase: `get_service_factory` lands in identity/auth.py OR new dedicated file
  - DoD: DI 注入模式清楚

### 0.4 53.5 Frontend Components Verify（US-2 + US-3 prep）
- [x] **Verify governance components exist** ✅ ApprovalsPage / ApprovalList / DecisionModal 3 files present
  - Files: `frontend/src/features/governance/components/{ApprovalsPage.tsx, ApprovalList.tsx, DecisionModal.tsx}`
  - DoD: 53.5 components 可 render（visual smoke deferred to Day 1 when dev server starts for Playwright config）
- [x] **Verify ChatV2 ApprovalCard wired to store** ✅
  - chatStore.ts line 55 (approvals slice) + lines 197 (approval_requested case) + 217 (approval_received case)
  - DoD: 確認 store slice + SSE event handler 已 wired
- [x] **Verify backend routes (governance + audit + chat) 全 mounted** ✅
  - api/main.py lines 95-98: health / chat / audit / governance 4 routers mounted at `/api/v1`
  - DoD: routes mounted; live HTTP smoke deferred to US-4 integration test (avoids spinning uvicorn now)

### 0.5 SSE serializer scope check（per `feedback_sse_serializer_scope_check.md`）
- [x] **Grep new LoopEvent emissions + check 53.5 events** ✅ 11 isinstance branches in sse.py
  - 53.5 ApprovalRequested (line 198) + ApprovalReceived (line 209) preserved ✅
  - 🚨 **CRITICAL D2**: `GuardrailTriggered` yielded **7×** in loop.py (lines 356/430/498/534/599/629/651) but **NO isinstance branch in sse.py**
  - Pre-existing bug from 53.3 (escaped 53.4 + 53.5 because chat router never wired guardrails); will crash production once US-4 wires hitl_manager
  - **Action**: Add to Day 1 scope as pre-Playwright fix (1 isinstance branch + 3 SSE serializer tests, ~1.5 hr); blocks US-2/US-3 e2e specs
  - Command: `grep -n "isinstance(event," backend/src/api/v1/chat/sse.py`

### 0.6 Day 0 progress.md
- [x] **Create progress.md** ✅
  - Path: `docs/03-implementation/agent-harness-execution/phase-53-6/sprint-53-6-frontend-e2e-prod-hitl/progress.md`
- [x] **Day 0 sections written**: Setup completion / Playwright readiness / Chat router 探勘 / 53.5 components verify / drift D1-D8 / time banking / next (Day 1)
- [ ] **Commit + push Day 0 progress + checklist updates**
  - Commit: `docs(progress, sprint-53-6): Day 0探勘 + drift D1-D8 (incl. critical D2 SSE GuardrailTriggered gap)`
  - Push: `git push`

---

## Day 1 — D2 SSE Serializer Fix + US-1 Playwright Bootstrap + Smoke Spec + CI Workflow (est. 5-7 hours)

### 1.0 D2 SSE Serializer GuardrailTriggered Fix (UNPLANNED — Day 0 探勘 finding)
- [x] **Add `GuardrailTriggered` isinstance branch in `backend/src/api/v1/chat/sse.py`** ✅
  - Wire-format type: `"guardrail_triggered"`; payload: guardrail_type / action / reason
  - Modification History updated with Sprint 53.6 D2 entry
  - DoD: serialize_loop_event(GuardrailTriggered(...)) returns dict, no NotImplementedError
- [x] **Add 3 SSE serializer test cases in `tests/unit/api/v1/chat/test_sse.py`** ✅ 20/20 green
  - test_guardrail_triggered_input_block (Stage 1 PII detection)
  - test_guardrail_triggered_output_sanitize (Stage 2 jailbreak detection)
  - test_guardrail_triggered_tool_escalate_block (Stage 3 reject/escalate/timeout block path)
  - DoD: 3 new cases + 17 existing = 20 passing
  - Verify: `python -m pytest tests/unit/api/v1/chat/test_sse.py -v` → 20 passed in 0.44s
- [x] **Update `frontend/src/features/chat_v2/types.ts` + chatStore.ts** ✅
  - Added `GuardrailTriggeredEvent` to LoopEvent union + `"guardrail_triggered"` to KNOWN_LOOP_EVENT_TYPES
  - Added `case "guardrail_triggered"` in chatStore mergeEvent (routes to rawEvents only — no UI surface)
  - DoD: typecheck + build green (188.10 KB / 707ms)

### 1.1 Install Playwright + chromium browser
- [x] **`npm install -D @playwright/test`** ✅ `@playwright/test ^1.59.1` in devDependencies
- [x] **`npx playwright install chromium`** ✅ chromium 147.0.7727.15 (179 MiB) + headless shell (111 MiB) downloaded to `~/.cache/ms-playwright/`
- [x] **Add e2e + e2e:ui scripts to package.json** ✅ `"e2e": "playwright test"` + `"e2e:ui": "playwright test --ui"`

### 1.2 Create `frontend/playwright.config.ts`
- [x] **Write minimal viable config** ✅ testDir `./tests/e2e` / timeout 30s / retries CI=2 local=0 / reporter list+html on CI / baseURL `http://localhost:5173` / trace on-first-retry / webServer auto-start vite dev (local) or vite preview (CI) with strictPort / chromium project only
- [x] **Verify config + smoke spec runs** ✅ verified Day 1.3 (2 passed in 4.0s)

### 1.3 Create `frontend/tests/e2e/smoke.spec.ts`
- [x] **Minimal smoke test (2 cases)** ✅ test 1: home page loads with /IPA Platform/ title; test 2: /governance/approvals route resolves without crash
- [x] **Run smoke locally** ✅ `npx playwright test tests/e2e/smoke.spec.ts` → 2 passed in 4.0s (Vite proxy ECONNREFUSED for /api/* expected — no backend running, SPA HTML still serves)

### 1.4 Update `.gitignore` + `frontend/README.md`
- [x] **Add to `.gitignore`** ✅ `frontend/playwright-report/`, `frontend/test-results/`, `frontend/playwright/.cache/`
- [x] **Add E2E section to `frontend/README.md`** ✅ inserted between Quickstart and Sprint roadmap (one-time install + npm run e2e / e2e:ui / single spec / show-report)

### 1.5 Create `.github/workflows/playwright-e2e.yml`
- [x] **Write workflow per plan §Technical Spec** ✅ paths filter (frontend/** + workflow self) / concurrency group / setup-node@v4 + npm cache / npm ci / actions/cache for `~/.cache/ms-playwright` / install chromium with deps / build / playwright test --reporter=list / upload report on failure (retention 7d)
- [x] **Validate workflow YAML on first push** ✅ commit `ea6bbbaa` triggered Playwright E2E run #25285348385; YAML parsed cleanly
- [x] **First push triggers workflow** ✅ Playwright E2E **success in 59s** (chromium install + build + 2 smoke tests)

### 1.6 Day 1 sanity checks
- [x] **mypy --strict src/api/v1/chat/sse.py** ✅ Success: no issues found in 1 source file
- [x] **black + isort + flake8 green on touched backend files** ✅ (1 E501 fixed: shortened test docstring at line 193)
- [x] **6 V2 lint scripts green** ✅ (check_ap1 + check_promptbuilder need `--root backend/src/agent_harness`; both 0 violations; cross_category_import / duplicate_dataclass / llm_sdk_leak / sync_callback all OK)
- [x] **Backend full pytest** ✅ **1059 passed / 4 skipped / 0 fail** (+3 from main 1056 = exactly the 3 new SSE tests)
- [x] **Frontend lint + build green** ✅ ESLint clean / build 188.10 KB / 52 modules / 707ms

### 1.7 Day 1 commit + push + verify CI
- [x] **Stage + commit + push** ✅ commit `ea6bbbaa` (14 files; 3 new + 11 modified) on branch `feature/sprint-53-6-frontend-e2e-prod-hitl`
- [x] **Verify CI runs and passes** ✅ 3 workflows green:
  - Backend CI: success in 1m34s
  - Frontend CI: success in 26s
  - Playwright E2E (new!): success in 59s
  - Note: V2 Lint + E2E Tests didn't trigger this push — likely paths filters exclude frontend-heavy commits; will trigger on Day 4 backend US-4/US-5 commits

### 1.8 Day 1 progress.md update
- [x] **Update progress.md with Day 1 actuals** ✅ included in `ea6bbbaa` commit (progress.md updated before commit, batched with code per 53.5 pattern)

---

## Day 2 — US-2 Governance Approvals Reviewer E2E (est. 4-5 hours)

### 2.1 Design decision (D11) — Mock at network layer instead of booting backend + seeding DB
- [x] **Day 2 mini-探勘 finding**: 53.5 governance integration tests use FastAPI `dependency_overrides` (in-process mocking, NOT browser e2e applicable). For Playwright e2e three options considered:
  - (a) Dev-only `/api/v1/_test/issue-jwt` + `/seed-approvals` endpoints — extra prod surface area; require env flag mounting
  - (b) Boot uvicorn + seed DB via Python helper — slow (~60s/spec); CI port conflicts; auth complexity
  - (c) **Playwright `page.route()` network mocks** — fast (~1s/spec); isolated; standard SPA e2e pattern
- [x] **D11 decision: Option (c) selected** ✅
  - Rationale: backend integration is exercised by 11 cases in `tests/integration/api/test_governance_endpoints.py` (incl. cross-tenant 404). e2e specs OWN frontend behavior validation (rendering / interaction / payload shape / error UI). Mocking at network layer keeps specs fast + isolated + standard pattern.
  - Documented in: `frontend/tests/e2e/fixtures/approval-fixtures.ts` header

### 2.2 Create fixture module
- [x] **Create `frontend/tests/e2e/fixtures/approval-fixtures.ts`** ✅
  - Exports: `sampleApprovals()` (3 canned items: HIGH delete_customer_record / MEDIUM send_external_email / CRITICAL execute_db_migration)
  - Helper: `mockGovernanceList(page, items)` — wires `page.route('**/api/v1/governance/approvals')` GET handler with mutable item slot (allows tests to swap response between calls; e.g. main flow approve removes item)
  - Helper: `mockGovernanceDecide(page, opts)` — wires POST handler; captures records in returned array; supports `respondWith` override for error cases
  - DoD: imports clean; helpers usable from spec

### 2.3 Write `frontend/tests/e2e/governance/approvals.spec.ts`
- [x] **5 cases written and passing** ✅ 5/5 in 5.3s
  - **main flow**: list 3 → click "delete_customer_record" Review → modal → fill reason → Approve → list refresh shows 2 → decide POST captured (decision=approved, reason matches)
  - **reject flow**: row "send_external_email" → modal → fill reason → Reject → decide POST captured (decision=rejected)
  - **escalate flow**: row "execute_db_migration" → modal → Escalate (no reason) → decide POST captured (decision=escalated, reason=null)
  - **decide error**: mock /decide 404 → modal stays open → `[role="alert"]` shows backend detail "Approval not found" (covers cross-tenant 404 surface)
  - **empty list**: mock returns [] → renders "No pending approvals." text
- [x] **Spec covers main flow + 3 decision paths + error UI + empty state** ✅ exceeds plan minimum (≥4 cases)
- [x] Verify: `npx playwright test tests/e2e/governance/approvals.spec.ts` → 5 passed in 5.3s

### 2.4 Day 2 sanity checks
- [x] **Full e2e suite green locally** ✅ 7/7 in 5.4s (2 smoke + 5 governance)
- [x] **Frontend lint + build green** ✅ ESLint clean / 188.10 KB / 52 modules / 563ms
- [x] **Backend full pytest unaffected** — 53.6 Day 2 changes are frontend-only; baseline 1059 maintained (verified Day 1 last run; no backend code touched Day 2)
- [ ] **CI Playwright E2E run passes** 🚧 will verify after Day 2.5 push

### 2.5 Day 2 commit + push + verify CI
- [ ] **Stage + commit + push**
  - Commit: `feat(frontend-e2e, sprint-53-6): US-2 governance approvals reviewer e2e (5 cases incl. error + empty)`
  - Push + verify CI

### 2.6 Day 2 progress.md update
- [ ] **Update progress.md with Day 2 actuals**
  - Commit: batched into Day 2.5 commit per 53.5 pattern
  - Push

---

## Day 3 — US-3 ChatV2 Inline ApprovalCard E2E (est. 4-5 hours)

### 3.1 Backend test setup (FakeChatClient + sensitive tool fixture)
- [ ] **Create or reuse FakeChatClient that emits ESCALATE-trigger tool call**
  - File: `backend/tests/e2e_fixtures/fake_chat_client.py` (or extend 53.5 既有 FakeChatClient)
  - Behavior: 第 1 turn 返回 sensitive tool call；第 2 turn （after approval）返回 final answer
  - DoD: fixture importable + used by integration tests
- [ ] **Wire fixture into dev-only mode**
  - Backend env flag: `USE_FAKE_CHAT_CLIENT=1` enables fixture in chat router
  - DoD: prod 不影響；e2e 模式可用

### 3.2 Write `frontend/tests/e2e/chat/approval-card.spec.ts`
- [ ] **Main approve flow**: navigate to /chat → send msg triggering sensitive tool → wait SSE ApprovalRequested → assert ApprovalCard 出現 + tool name + risk badge → click Approve → wait SSE ApprovalReceived → assert card decision badge → assert final tool result message
  - Verify: `await page.waitForResponse(r => r.url().includes('/chat') && r.status() === 200)`
  - Verify: `await expect(page.getByText('Approved')).toBeVisible()`
- [ ] **Reject flow**: same as above but click Reject with reason → assert card rejected → assert tool blocked message
- [ ] **Risk badge color check**: 觸發 HIGH risk approval → assert card 有 `data-risk-level="high"` + computed style 含 red-orange
- [ ] **(Optional) Multiple approvals in same session**: 觸發 2 個 sensitive tool → 2 張 ApprovalCard 並排 → 各自 decide
- [ ] DoD: ≥ 3 cases；spec 跑通；CI green
- [ ] Verify: `cd frontend && npm run e2e tests/e2e/chat/approval-card.spec.ts`

### 3.3 Day 3 sanity checks
- [ ] **All 3+ chat cases green locally**
- [ ] **Both governance + chat e2e suites green**
  - Command: `cd frontend && npm run e2e`
- [ ] **Backend full pytest unaffected**
- [ ] **CI Playwright E2E full suite green**

### 3.4 Day 3 commit + push + verify CI
- [ ] **Stage + commit + push**
  - Commit: `feat(frontend-e2e, sprint-53-6): US-3 ChatV2 ApprovalCard e2e (approve/reject/risk badge)`
  - Push + verify CI

### 3.5 Day 3 progress.md update
- [ ] **Update progress.md with Day 3 actuals**
  - Commit + push

---

## Day 4 — US-4 Production HITL Wiring + US-5 ServiceFactory + Final Verification + Retrospective + PR (est. 5-7 hours)

### 4.1 US-5 Create ServiceFactory class
- [ ] **Create or extend `backend/src/platform_layer/governance/service_factory.py`**
  - File header per convention
  - Class: `ServiceFactory` with config_path + db_session_factory ctor
  - Methods: `get_hitl_manager(tenant_id)` / `get_audit_query(tenant_id)` / `get_risk_policy(tenant_id)` / `get_chain_verifier(tenant_id)` (optional)
  - Cache: lazy dict per tenant_id
  - DoD: imports clean + class instantiable
- [ ] **Add `get_service_factory` DI in `api/dependencies.py`**
  - Singleton pattern (per-process); reads config_path from settings
  - DoD: dep usable in `Depends(...)`

### 4.2 US-5 ServiceFactory unit tests
- [ ] **Create `backend/tests/unit/platform_layer/governance/test_service_factory.py`**
  - Cases (≥ 5): factory constructs DefaultHITLManager / cache hit on 2nd call / per-tenant notifier override resolution / get_audit_query returns AuditQuery / get_risk_policy returns DefaultRiskPolicy
  - DoD: 5+ cases green
  - Verify: `python -m pytest tests/unit/platform_layer/governance/test_service_factory.py -v`

### 4.3 US-4 Wire chat router to factory
- [ ] **Modify `backend/src/api/v1/chat/router.py`**
  - Replace direct `DefaultHITLManager(...)` (if any) or 加 hitl_manager param to AgentLoopImpl construction
  - Use `Depends(get_service_factory)` + `factory.get_hitl_manager(current_tenant)`
  - Feature toggle: settings.HITL_ENABLED (default true production)
  - DoD: chat 端點 production 觸發 sensitive tool 真正進入 _cat9_hitl_branch

### 4.4 US-4 Migrate governance + audit routers to factory
- [ ] **Modify `backend/src/api/v1/governance/router.py`**
  - Use `Depends(get_service_factory)` + `factory.get_hitl_manager`
  - Drop ad-hoc DefaultHITLManager construction
  - DoD: existing 11 governance tests still pass
- [ ] **Modify `backend/src/api/v1/audit.py`**
  - Use `Depends(get_service_factory)` + `factory.get_audit_query`
  - DoD: existing 13 audit tests still pass

### 4.5 US-4 Production wiring integration test
- [ ] **Create `backend/tests/integration/api/test_chat_hitl_production_wiring.py`**
  - Cases (3): main flow (chat → sensitive tool → ApprovalRequested SSE → governance API pending visible) / feature toggle off (HITL_ENABLED=false → 53.3 baseline soft-block) / cross-tenant isolation (tenant A chat 不會在 tenant B governance 出現)
  - Real backend + real HITLManager + Noop notifier + FakeChatClient
  - DoD: 3 cases green
  - Verify: `python -m pytest tests/integration/api/test_chat_hitl_production_wiring.py -v`

### 4.6 Sprint final verification
- [ ] **Production wiring grep evidence**
  - Command: `grep -rn "DefaultHITLManager(" backend/src/api/`
  - DoD: 0 results in production code (allowed in tests/fixtures)
- [ ] **ServiceFactory adoption grep**
  - Command: `grep -rn "AuditQuery(\|DefaultRiskPolicy(" backend/src/api/`
  - DoD: 0 results in production code
- [ ] **LLM SDK leak check**
  - Command: `grep -rn "from openai\|from anthropic" backend/src/api/v1/ backend/src/platform_layer/`
  - DoD: 0 results
- [ ] **Coverage gates**
  - Command: `python -m pytest --cov=src/platform_layer/governance --cov=src/api/v1 --cov-report=term-missing`
  - DoD: service_factory.py ≥ 85%; chat router HITL path ≥ 80%
- [ ] **Full pytest run**
  - Command: `python -m pytest --tb=line -q`
  - DoD: ≥ 1066 passed / 0 fail (baseline 1056 + ~10 new)
- [ ] **6 V2 lint scripts green**
  - Command: 6 `scripts/lint/check_*.py` scripts
- [ ] **mypy --strict src** all touched files clean
- [ ] **Frontend lint + build green**
- [ ] **Frontend Playwright e2e: 3 specs green** (smoke + governance + chat)

### 4.7 Day 4 retrospective.md
- [ ] **Create `docs/03-implementation/agent-harness-execution/phase-53-6/sprint-53-6-frontend-e2e-prod-hitl/retrospective.md`**
- [ ] **Answer 6 mandatory questions** (per plan §Retrospective 必答)
  1. Sprint Goal achieved + e2e 主流量 evidence + production wiring grep
  2. estimated vs actual hours per US + total
  3. What went well (≥ 3 items)
  4. What can improve (≥ 3 items)
  5. Drift documented (V2 9 disciplines)
  6. Audit Debt logged (AD-E2E-* + 6 closed)
- [ ] **Sprint Closeout Checklist** (verbatim from plan §Sprint Closeout)

### 4.8 PR open + closeout
- [ ] **Final commit + push**
  - Commit: `docs(closeout, sprint-53-6): retrospective + Day 4 progress + final marks`
  - Push
- [ ] **Open PR**
  - Title: `Sprint 53.6: Frontend E2E (Playwright) + Production HITL Wiring`
  - Body: Summary + plan link + checklist link + 5 USs status + Anti-pattern checklist + verification evidence
  - Command: `gh pr create --title "..." --body "..."`
- [ ] **Wait for 5 active CI checks** (Backend CI / V2 Lint / E2E Tests / Frontend CI / Playwright E2E)
- [ ] **Normal merge after green** (solo-dev policy: review_count=0)
  - Command: `gh pr merge <num> --merge --delete-branch`
- [ ] **Verify main HEAD has merge commit**

### 4.9 Cleanup + memory update + branch protection
- [ ] **Pull main + verify**
  - Command: `git checkout main && git pull origin main && git log --oneline -3`
- [ ] **Delete local feature branch**
  - Command: `git branch -d feature/sprint-53-6-frontend-e2e-prod-hitl`
- [ ] **Verify main 5 active CI green post-merge**
  - Command: `gh run list --branch main --limit 5`
- [ ] **Update branch protection required_checks to include Playwright E2E**
  - Admin op: `gh api -X PUT /repos/.../branches/main/protection/required_status_checks --field contexts[]=Playwright%20E2E`
  - DoD: 5 required checks listed
- [ ] **Memory update**
  - Create: `memory/project_phase53_6_frontend_e2e_prod_hitl.md`
  - Add to MEMORY.md index
  - Mark V2 progress: 18/22 (82%); AD-Front-1 + AD-Front-2 + AD-Hitl-4-followup closed
- [ ] **Working tree clean check**
  - Command: `git status --short`

---

## Verification Summary（Day 4 final 必填）

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | All 5 USs delivered | [ ] | PR #__ merged |
| 2 | Playwright runner + smoke spec working | [ ] | `npm run e2e tests/e2e/smoke.spec.ts` green |
| 3 | Governance reviewer e2e green (≥ 4 cases) | [ ] | spec output |
| 4 | ChatV2 ApprovalCard e2e green (≥ 3 cases) | [ ] | spec output |
| 5 | Production HITL wiring grep evidence | [ ] | grep DefaultHITLManager = 0 in api/ |
| 6 | ServiceFactory adoption grep | [ ] | grep AuditQuery / RiskPolicy direct = 0 in api/ |
| 7 | HITL feature toggle off path verified | [ ] | integration test green |
| 8 | Cross-tenant isolation e2e | [ ] | governance spec green |
| 9 | CI Playwright E2E workflow green on main | [ ] | gh run list |
| 10 | pytest 1066+ / 0 fail | [ ] | command output |
| 11 | mypy --strict clean | [ ] | command output |
| 12 | 6 V2 lint scripts green | [ ] | CI |
| 13 | LLM SDK leak: 0 | [ ] | grep |
| 14 | Frontend lint + build + 3 e2e specs green | [ ] | CI + local |
| 15 | coverage gates met (factory ≥ 85% / chat router HITL path ≥ 80%) | [ ] | pytest --cov report |
| 16 | Anti-pattern checklist 11 points | [ ] | retrospective |
| 17 | retrospective.md filled (6 questions) | [ ] | file exists with all 6 |
| 18 | Memory updated (project + index) | [ ] | files |
| 19 | Branches deleted (local + remote) | [ ] | git branch -a |
| 20 | Branch protection updated to 5 required checks | [ ] | gh api repos/.../branches/main/protection |
| 21 | V2 progress: 18/22 (82%) | [ ] | memory + GitHub |
| 22 | AD-Front-1 + AD-Front-2 + AD-Hitl-4-followup closed | [ ] | retrospective AD log |
