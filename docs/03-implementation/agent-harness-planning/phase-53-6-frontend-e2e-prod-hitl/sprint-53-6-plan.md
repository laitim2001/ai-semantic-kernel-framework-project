# Sprint 53.6 — Frontend E2E (Playwright) + Production HITL Wiring

> **Sprint Type**: V2 main sprint (53.5 frontend e2e + production wiring carryover)
> **Owner Categories**: Frontend (V2 page 6 governance + chat-v2 e2e coverage) / Cat 9 (production HITL boundary at chat router) / Cross-cutting (ServiceFactory consolidation)
> **Phase**: 53 (Cross-Cutting Production Hardening)
> **Workload**: 1 week (Day 0-4, ~18-25 hours)
> **Branch**: `feature/sprint-53-6-frontend-e2e-prod-hitl`
> **Plan Authority**: This document (per CLAUDE.md §Sprint Execution Workflow)
> **Roadmap Source**: 53.5 retrospective Q6 carryover (AD-Front-1 + AD-Front-2 + AD-Hitl-4-followup)
> **Carryover bundled**: AD-Front-1 (Playwright bootstrap + e2e specs) + AD-Front-2 (production HITL wiring at chat router) + AD-Hitl-4-followup (ServiceFactory consolidation)

---

## Sprint Goal

完成 Sprint 53.5 governance + chat ApprovalCard frontend 的 **e2e 覆蓋 + production HITL 鏈路 wiring**：(a) 建立 Playwright runner 基礎建設（install + config + CI workflow），(b) 為 53.5 US-1 governance approvals page 與 US-2 chat ApprovalCard 寫 Playwright e2e specs（reviewer 主流量 + 跨租戶隔離 + SSE 驅動 ApprovalCard），(c) 在 chat router 把 53.5 US-4 已建好的 `load_notifier_from_config` factory **真正接到 production AgentLoopImpl**（取代目前 chat 端點未注入 hitl_manager 的狀態），同時 (d) 把 governance / risk / audit / HITL 的 service constructors 整合到統一的 ServiceFactory（AD-Hitl-4-followup）。Sprint 結束後 governance 全鏈路（Cat 9 Stage 3 → AgentLoopImpl `_cat9_hitl_branch` → HITLManager → Teams notifier → reviewer UI → loop resume）達到 **production-deployable + e2e regression-protected**。

**主流量驗收標準**：
- chat 觸發敏感工具 → Stage 3 ESCALATE → AgentLoopImpl pause → HITLManager.request_approval → notification.yaml 驅動 Teams notifier → Playwright e2e 覆蓋 reviewer 在 governance page 看到 + decide → loop resume
- 同樣鏈路在 chat-v2 inline ApprovalCard：SSE ApprovalRequested → card 出現 → click approve → ApprovalReceived → card disabled
- ServiceFactory 一處構建 HITLManager（含 notifier）+ AuditQuery + RiskPolicy；chat router + governance router + audit router 全用 factory；無 ad-hoc constructor 散落
- Playwright e2e 在 CI 跑（headless chromium + GitHub Actions workflow）；2 specs green

---

## Background

### V2 進度

- **17/22 sprints (77%)** completed (Phase 49-55 roadmap)
- 53.5 closed (governance frontend page + chat ApprovalCard SSE wiring + Cat 9 Stage 3 → AgentLoop wiring + audit HTTP API + notification.yaml loader)
- main HEAD: `86fd42db`
- Cat 9 達 Level 5（production-ready end-to-end with reviewer UI）；但 AgentLoopImpl 在 chat 端點仍未注入 hitl_manager → production 觸發 Stage 3 仍走 53.3 baseline soft-block，尚未真正 wire 到 HITLManager

### 為什麼 53.6 是 53.5 直系延伸

53.5 retrospective 揭示兩塊缺口：
1. **e2e 覆蓋空白**：53.5 US-1 + US-2 frontend 元件透過 manual verification + backend integration tests 交付，但 Playwright e2e（governance reviewer 主流量 + ApprovalCard SSE 驅動主流量）整體 deferred 到 AD-Front-1
2. **Production wiring 缺口**：53.5 US-4 建好 `load_notifier_from_config` factory，但 chat router 在構造 `AgentLoopImpl` 時並未注入 `hitl_manager` 參數 → production 觸發 Stage 3 仍只 emit GuardrailTriggered("escalate") 而非真正進入 HITL 鏈路（AD-Front-2）。同時 53.4 ServiceFactory consolidation 也 deferred（AD-Hitl-4-followup）。

兩塊 deferred 都直系於 53.5 governance 主鏈路；合併處理可避免分兩個小 sprint 的 context-switch overhead，並一次性閉環整個 governance 全鏈路。

### 既有結構

```
backend/src/                                              # 53.5 已落地
├── api/v1/chat/router.py                                 # 🚧 AgentLoopImpl 構造未注入 hitl_manager（AD-Front-2）
├── api/v1/governance/router.py                           # ✅ 53.5 US-1 已建
├── api/v1/audit.py                                       # ✅ 53.5 US-5+US-6 已建
├── platform_layer/governance/
│   ├── hitl/manager.py                                   # ✅ DefaultHITLManager production
│   ├── hitl/notifier.py                                  # ✅ load_notifier_from_config factory（53.5 US-4）
│   ├── audit/query.py                                    # ✅ AuditQuery + verify_chain
│   └── risk/policy.py                                    # ✅ DefaultRiskPolicy
├── platform_layer/governance/service_factory.py          # 🚧 不存在或未整合（AD-Hitl-4-followup）
└── agent_harness/orchestrator_loop/loop.py               # ✅ _cat9_hitl_branch（53.5 US-3，opt-in via hitl_manager ctor param）

frontend/                                                 # 53.6 e2e 主要工作目標
├── package.json                                          # 🚧 無 @playwright/test（53.5 Day 0 探勘確認）
├── playwright.config.ts                                  # 🚧 不存在
├── tests/e2e/                                            # 🚧 不存在
│   ├── governance/approvals.spec.ts                      # 🚧 待建
│   └── chat/approval-card.spec.ts                        # 🚧 待建
└── src/features/governance/components/                   # ✅ ApprovalsPage / ApprovalList / DecisionModal（53.5 US-1）
└── src/features/chat_v2/components/ApprovalCard.tsx      # ✅ 53.5 US-2 已建

.github/workflows/                                        # 53.6 CI 工作目標
└── playwright-e2e.yml                                    # 🚧 待建
```

### V2 紀律 9 項對齐確認

1. **Server-Side First** ✅ Playwright e2e 走完整 frontend → backend HTTP / SSE 鏈路；ServiceFactory 強化後端責任邊界
2. **LLM Provider Neutrality** ✅ 不引入新 LLM SDK
3. **CC Reference 不照搬** ✅ Anthropic CC 沒有 enterprise governance e2e；參考 Playwright 官方 best practice 設置
4. **17.md Single-source** ✅ ServiceFactory 為 governance/risk/audit/HITL 的單一構造入口；不破壞既有 ABC
5. **11+1 範疇歸屬** ✅ Frontend e2e = `frontend/tests/e2e/`；ServiceFactory = `platform_layer/governance/service_factory.py`；chat router wiring = `api/v1/chat/router.py`
6. **04 anti-patterns** ✅ AP-3 cross-directory: e2e specs 集中 `tests/e2e/{governance,chat}/`；AP-4 Potemkin: 53.5 已落 components → 53.6 補 e2e；AP-9 verification: e2e 覆蓋主流量 = 真實 verification
7. **Sprint workflow** ✅ plan → checklist → code（本文件 + 53.5 plan/checklist 為 template）
8. **File header convention** ✅ 所有新檔案需符合（含 .ts spec / .yml workflow）
9. **Multi-tenant rule** ✅ governance e2e 含跨租戶隔離 case；ServiceFactory 強制 tenant 注入

---

## User Stories

### US-1: Playwright Runner Bootstrap + CI Workflow

**As** a frontend engineer
**I want** Playwright installed in `frontend/` with a working `playwright.config.ts`, a smoke spec that verifies headless chromium spawns, and a GitHub Actions workflow that runs e2e on PR + main
**So that** subsequent sprints can write Playwright specs without re-tackling the bootstrap problem (closes AD-Front-1 install/config phase)

**Acceptance**:
- `frontend/package.json`: `@playwright/test` in devDependencies
- `npx playwright install chromium` succeeds locally
- `frontend/playwright.config.ts` 最小可行版：testDir / baseURL / headless / reporter / webServer（auto-start vite dev server for local + npm run preview for CI）
- `frontend/tests/e2e/smoke.spec.ts`：1 個最小 spec（visit `/` → assert page title）
- `npx playwright test` 本地通過
- `.github/workflows/playwright-e2e.yml`：on pull_request + push to main；setup-node + npm ci + playwright install + npm run build + npx playwright test；upload Playwright report on failure
- 加入 4 active CI checks 序列（Frontend CI / V2 Lint / E2E Tests / Backend CI）
- `.gitignore` 加入 `frontend/playwright-report/` + `frontend/test-results/`

**Files**:
- 修改: `frontend/package.json`（add @playwright/test devDep + scripts: e2e / e2e:ui）
- 新建: `frontend/playwright.config.ts`
- 新建: `frontend/tests/e2e/smoke.spec.ts`
- 新建: `.github/workflows/playwright-e2e.yml`
- 修改: `.gitignore`
- 修改: `frontend/README.md`（一段 e2e workflow 說明）

### US-2: Governance Approvals Reviewer E2E

**As** a security engineer
**I want** a Playwright e2e spec that exercises 53.5 US-1 reviewer 主流量 — login as reviewer → /governance/approvals → see pending list → click row → decision modal → approve → backend state changes → list updates — plus cross-tenant isolation case
**So that** governance reviewer page has regression protection (closes AD-Front-1 governance spec phase)

**Acceptance**:
- Spec: `frontend/tests/e2e/governance/approvals.spec.ts`
- Test fixtures: backend 啟動時 seed 2 tenant + 2 approver users + 3 pending approvals (2 in tenant A, 1 in tenant B); JWT 模擬透過 cookie / header injection
- 主流程 case：reviewer A 看到 tenant A 的 2 個 pending → click row → modal → approve with reason → backend POST /decide 200 → list 自動 refresh 顯示剩 1 個
- 跨租戶 case：reviewer A 不應看到 tenant B 的 approval；直接 navigate to `/governance/approvals/{tenant_b_request_id}` 應 404 / empty
- 拒絕 case：click row → modal → reject with reason → backend state = rejected → list 自動 refresh
- 升級 case：click row → modal → escalate → backend state = escalated
- Errors：故意 stub /decide 返回 500 → 顯示 error 提示；故意停掉 backend → 顯示 connection error
- 至少 4 cases（main flow / cross-tenant / reject / escalate）；error cases 額外加分
- Verify: `cd frontend && npx playwright test tests/e2e/governance/approvals.spec.ts`

**Files**:
- 新建: `frontend/tests/e2e/governance/approvals.spec.ts`
- 新建: `frontend/tests/e2e/fixtures/backend-fixtures.ts`（seed helper）
- 新建: `frontend/tests/e2e/fixtures/auth-fixtures.ts`（JWT injection helper）
- （可能）修改: `backend/src/api/v1/governance/router.py`（補一個 dev-only seed endpoint，by env flag）

### US-3: ChatV2 Inline ApprovalCard E2E

**As** a chat user with reviewer role
**I want** a Playwright e2e spec that drives the inline ApprovalCard 主流量 — chat triggers sensitive tool → SSE ApprovalRequested → card appears with risk badge + buttons → click approve → SSE ApprovalReceived → card shows approved → loop resume + tool result returned
**So that** chat-v2 inline ApprovalCard has regression protection (closes AD-Front-1 chat spec phase)

**Acceptance**:
- Spec: `frontend/tests/e2e/chat/approval-card.spec.ts`
- Test fixtures：用真實 backend + mock chat client (FakeChatClient that returns ESCALATE-trigger tool call) + real HITLManager + Noop notifier
- 主流程 case：navigate to /chat → send message that triggers sensitive tool → 等待 SSE ApprovalRequested event（透過 page.waitForRequest / waitForResponse）→ assert ApprovalCard 出現 + 顯示 tool name + risk badge → click Approve → assert SSE ApprovalReceived → assert card shows decision badge → assert tool result message 出現
- Reject case：同上 → click Reject with reason → assert card 顯示 rejected → assert tool blocked message
- 多 approval case：同 session 觸發 2 個 approval → 2 張 ApprovalCard 並排出現 → 各自 decide
- Risk badge color check：LOW=green / MEDIUM=orange / HIGH=red-orange / CRITICAL=dark-red（透過 computed style assertion）
- 至少 3 cases（approve / reject / risk badge）
- Verify: `cd frontend && npx playwright test tests/e2e/chat/approval-card.spec.ts`

**Files**:
- 新建: `frontend/tests/e2e/chat/approval-card.spec.ts`
- （可能）修改: `frontend/tests/e2e/fixtures/backend-fixtures.ts`（chat seed helper）

### US-4: Production HITL Wiring at Chat Router (closes AD-Front-2)

**As** a security engineer
**I want** the chat router to wire `AgentLoopImpl` with the production `hitl_manager`（透過 ServiceFactory + load_notifier_from_config factory）, so that hitting `POST /api/v1/chat` with a sensitive tool actually triggers the full Cat 9 Stage 3 → HITLManager → Teams notifier → reviewer UI flow in production
**So that** AD-Front-2 carryover is closed and Cat 9 Level 5 chain is end-to-end production-deployable

**Acceptance**:
- chat router 在 `_build_agent_loop` (or equivalent factory call) 注入 `hitl_manager=service_factory.get_hitl_manager(tenant_id)` + `hitl_timeout_s=14400`
- HITLManager 透過 ServiceFactory 構造，內部呼叫 `load_notifier_from_config` 取得 tenant-aware notifier
- Configuration: 預設 `notification.yaml` 在 `backend/config/notification.yaml`（53.5 US-4 已建）；env override `NOTIFICATION_CONFIG_PATH`
- Failure paths: notification.yaml 不存在 → log warning + Noop notifier；webhook URL 缺失 → Noop notifier；HITLManager DB error → fail-closed（53.5 US-3 already covers this）
- Backwards compat：若 `enable_hitl=False` (env flag or feature toggle) → AgentLoopImpl 不注入 hitl_manager（53.3 baseline）
- Integration test：真 backend + 真 HITLManager + Noop notifier；POST /api/v1/chat with sensitive tool → assert SSE 含 ApprovalRequested + checkpoint saved + （透過 governance API）pending request 可見
- 驗證 grep：chat router 不再有 `DefaultHITLManager(...)` 直接構造；全走 service_factory

**Files**:
- 修改: `backend/src/api/v1/chat/router.py`（注入 hitl_manager via factory）
- 新建/修改: `backend/src/platform_layer/governance/service_factory.py`（uniform getters: get_hitl_manager / get_audit_query / get_risk_policy）
- 修改: `backend/src/api/v1/governance/router.py`（governance endpoint also uses factory — drop ad-hoc construction if any）
- 修改: `backend/src/api/v1/audit.py`（audit endpoint also uses factory）
- 新建: `backend/tests/integration/api/test_chat_hitl_production_wiring.py`（main flow + feature toggle off）
- 修改: `backend/tests/integration/api/test_governance_endpoints.py`（factory-based fixtures）

### US-5: ServiceFactory Consolidation (AD-Hitl-4-followup)

**As** a backend engineer
**I want** all governance / risk / audit / HITL service constructors unified under a single ServiceFactory class with consistent signatures (tenant_id arg, config-driven, lazy-cached)
**So that** future sprints (54.x) inheriting these services don't replicate ad-hoc construction logic + we eliminate the AD-Hitl-4-followup carryover

**Acceptance**:
- `service_factory.py` exports `ServiceFactory` class with methods:
  - `get_hitl_manager(tenant_id) -> HITLManager`（含 notifier resolution）
  - `get_audit_query(tenant_id) -> AuditQuery`
  - `get_risk_policy(tenant_id) -> RiskPolicy`
  - （optional）`get_chain_verifier(tenant_id) -> ChainVerifier`
- Lazy caching：第一次呼叫 build instance；後續呼叫從 dict 取（per process）
- Tenant-aware：notifier 與 risk_policy override 都依 tenant_id 解析（reuse 53.5 patterns）
- DI integration：FastAPI dependency `get_service_factory` 在 `api/dependencies.py` 或同類位置；router 用 `Depends(get_service_factory)` 取
- Tests：unit + integration（factory 構造正確性 + cache hit + tenant override resolution）
- 驗證 grep：production code（router + endpoint）不再有直接 `DefaultHITLManager(...)`, `AuditQuery(...)`, `DefaultRiskPolicy(...)` 構造（測試 fixture 例外）

**Files**:
- 新建/修改: `backend/src/platform_layer/governance/service_factory.py`
- 修改: `backend/src/api/dependencies.py`（add `get_service_factory` DI）
- 修改: `backend/src/api/v1/chat/router.py`（use factory）
- 修改: `backend/src/api/v1/governance/router.py`（use factory）
- 修改: `backend/src/api/v1/audit.py`（use factory）
- 新建: `backend/tests/unit/platform_layer/governance/test_service_factory.py`

---

## Technical Specifications

### File Skeletons

```typescript
// frontend/playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30_000,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  webServer: process.env.CI
    ? { command: 'npm run preview -- --port 5173', port: 5173, reuseExistingServer: false }
    : { command: 'npm run dev -- --port 5173', port: 5173, reuseExistingServer: true },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
```

```yaml
# .github/workflows/playwright-e2e.yml
name: Frontend E2E
on:
  pull_request:
    paths:
      - 'frontend/**'
      - '.github/workflows/playwright-e2e.yml'
  push:
    branches: [main]
    paths: ['frontend/**']

jobs:
  e2e:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm', cache-dependency-path: frontend/package-lock.json }
      - run: npm ci
        working-directory: frontend
      - run: npx playwright install --with-deps chromium
        working-directory: frontend
      - run: npm run build
        working-directory: frontend
      - run: npx playwright test --reporter=list
        working-directory: frontend
        env: { CI: '1' }
      - if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: frontend/playwright-report/
          retention-days: 7
```

```python
# backend/src/platform_layer/governance/service_factory.py
class ServiceFactory:
    def __init__(self, config_path: Path | None = None, db_session_factory: Callable | None = None):
        self._config_path = config_path or Path("config/notification.yaml")
        self._db_session_factory = db_session_factory
        self._hitl_cache: dict[UUID, HITLManager] = {}
        self._audit_cache: dict[UUID, AuditQuery] = {}
        self._risk_cache: dict[UUID, RiskPolicy] = {}

    def get_hitl_manager(self, tenant_id: UUID) -> HITLManager:
        if tenant_id not in self._hitl_cache:
            notifier = load_notifier_from_config(self._config_path, tenant_id)
            self._hitl_cache[tenant_id] = DefaultHITLManager(
                session_factory=self._db_session_factory,
                notifier=notifier,
            )
        return self._hitl_cache[tenant_id]

    def get_audit_query(self, tenant_id: UUID) -> AuditQuery: ...
    def get_risk_policy(self, tenant_id: UUID) -> RiskPolicy: ...
```

```python
# backend/src/api/v1/chat/router.py (excerpt)
async def _build_agent_loop(
    request: ChatRequest,
    current_tenant: UUID = Depends(get_current_tenant),
    factory: ServiceFactory = Depends(get_service_factory),
) -> AgentLoopImpl:
    hitl_manager = factory.get_hitl_manager(current_tenant) if settings.HITL_ENABLED else None
    return AgentLoopImpl(
        chat_client=...,
        tool_registry=...,
        hitl_manager=hitl_manager,            # ← 53.6 US-4 wiring
        hitl_timeout_s=settings.HITL_TIMEOUT_S,
        ...
    )
```

### CI Workflow Integration

53.6 加入 `Frontend E2E` 為新的 active CI check（與既有 4 個並列：Backend CI / V2 Lint / E2E Tests / Frontend CI），總計 5 個。Branch protection required_checks 待 53.6 merge 後同步更新（admin op）。

---

## File Change List

### 新建（11 個）

**Frontend** (4):
1. `frontend/playwright.config.ts`
2. `frontend/tests/e2e/smoke.spec.ts`
3. `frontend/tests/e2e/governance/approvals.spec.ts`
4. `frontend/tests/e2e/chat/approval-card.spec.ts`

**Frontend fixtures** (2):
5. `frontend/tests/e2e/fixtures/backend-fixtures.ts`
6. `frontend/tests/e2e/fixtures/auth-fixtures.ts`

**Backend** (2):
7. `backend/src/platform_layer/governance/service_factory.py`
8. `backend/tests/integration/api/test_chat_hitl_production_wiring.py`

**Backend tests** (1):
9. `backend/tests/unit/platform_layer/governance/test_service_factory.py`

**CI** (1):
10. `.github/workflows/playwright-e2e.yml`

**Docs** (1):
11. （possibly）`backend/src/api/v1/governance/router.py` add dev-only seed endpoint OR fixtures-only

### 修改（9 個）

1. `frontend/package.json`（@playwright/test devDep + scripts）
2. `frontend/README.md`（e2e workflow 段）
3. `.gitignore`（playwright-report / test-results）
4. `backend/src/api/v1/chat/router.py`（hitl_manager via factory）
5. `backend/src/api/v1/governance/router.py`（factory-based）
6. `backend/src/api/v1/audit.py`（factory-based）
7. `backend/src/api/dependencies.py`（get_service_factory DI）
8. `backend/tests/integration/api/test_governance_endpoints.py`（factory fixtures）
9. `backend/src/core/config.py` 或同類（HITL_ENABLED / HITL_TIMEOUT_S settings）

### 測試（2 frontend e2e + 1 unit + 1 integration = 4 新檔）

---

## Acceptance Criteria

### 主流量端到端驗收

- [ ] **Playwright runner production-ready**: 本地 `npx playwright test` green；CI workflow on PR + main green
- [ ] **Governance reviewer e2e green**: ≥ 4 cases (main / cross-tenant / reject / escalate)
- [ ] **ChatV2 ApprovalCard e2e green**: ≥ 3 cases (approve / reject / risk badge)
- [ ] **Production HITL wiring grep evidence**: chat router uses factory；無 `DefaultHITLManager(...)` 散落構造
- [ ] **ServiceFactory 替代率 100%**: production code （router + endpoint）全 factory；測試 fixture 例外
- [ ] **HITL feature toggle off path**: env `HITL_ENABLED=false` → AgentLoopImpl 不注入 → 53.3 baseline 保留
- [ ] **End-to-end production simulation**: real backend + real HITLManager + Noop notifier；chat → ApprovalRequested SSE → governance API pending → decide → loop resume

### 品質門檻

- [ ] pytest 全綠 (預期 1056+10 ≈ 1066+ passed)
- [ ] mypy --strict 0 errors（service_factory.py + chat router + audit.py + governance router）
- [ ] flake8 + black + isort + ruff green（含 pre-push 必跑）
- [ ] 6 V2 lint scripts green（特別 check_cross_category_import + check_duplicate_dataclass）
- [ ] LLM SDK leak: 0
- [ ] Frontend ESLint + TypeScript build green
- [ ] Playwright e2e: 3 specs green (smoke + governance + chat)
- [ ] CI: 5 active checks green (Backend / V2 Lint / E2E / Frontend CI / Frontend E2E)

### 範疇對齐

- [ ] **AD-Front-1 closed**：Playwright bootstrap + 2 e2e specs delivered
- [ ] **AD-Front-2 closed**：chat router production HITL wiring grep evidence
- [ ] **AD-Hitl-4-followup closed**：ServiceFactory consolidation grep evidence
- [ ] **Cat 9 Level 5 production-deployable**：governance 全鏈路 e2e regression-protected + production wiring 完整

---

## Deliverables（見 checklist 詳細）

US-1 到 US-5 共 5 個 User Stories；checklist 拆分到 Day 0-4。

---

## Dependencies & Risks

### Dependencies

| Dependency | 來自 | 必須狀態 |
|------------|------|---------|
| 53.5 US-1 governance approvals page (frontend) | 53.5 | ✅ merged main `86fd42db` |
| 53.5 US-2 ChatV2 ApprovalCard | 53.5 | ✅ merged main |
| 53.5 US-3 AgentLoop `_cat9_hitl_branch` (opt-in) | 53.5 | ✅ merged main |
| 53.5 US-4 `load_notifier_from_config` factory | 53.5 | ✅ merged main |
| 53.4 HITLManager production / AuditQuery / DefaultRiskPolicy | 53.4 | ✅ merged main |
| Cat 9 ToolGuardrail Stage 1+2+3 | 53.3 | ✅ merged main |

### Risks

| Risk | Mitigation |
|------|-----------|
| Playwright chromium download (~300MB) 在 CI 拉取慢 / 不穩定 | 用 setup-node cache + `--with-deps`；考慮 actions/cache for `~/.cache/ms-playwright` |
| Backend dev server 與 Playwright e2e 啟動時序 race（vite + uvicorn 都要啟） | webServer config 用 reuseExistingServer + healthcheck wait；CI 用 npm run preview 避免 vite watch overhead |
| JWT injection in e2e（auth fixtures）難度 | 用 cookie injection via storageState 或 page.context.addCookies；backend 加 dev-only token endpoint by env flag |
| ServiceFactory 重構觸發 53.5 既有 governance / audit 測試失敗 | 用 additive 策略：service_factory.py 為新 class；router 改用 factory 但保留 backwards-compatible direct construction（feature flagged） |
| Production HITL wiring 在 chat router 改動破壞 53.5 baseline | feature flag `HITL_ENABLED` (default true production / false test) + 整合測試覆蓋 toggle on/off 兩條路徑 |
| Cross-tenant e2e 設置複雜（需多 tenant fixture + JWT） | 重用 53.5 既有 multi-tenant fixture pattern；e2e 用 storageState 切 reviewer 身份 |
| Playwright spec 在 CI 比 local 慢 / flaky | 加 retries: 2 in CI；用 `await expect(locator).toBeVisible({ timeout: 5000 })` 而非 hardcoded sleep；trace on first retry |

### 主流量驗證承諾

53.6 不允許「Playwright runner 安裝但 spec 為 stub」交付。每個 e2e US 必須有 ≥ 3 cases 覆蓋主流量 + edge case；US-4 production wiring 必須有 integration test 證明 chat → ApprovalRequested SSE 鏈路 in production-like setup。

---

## Audit Carryover Section

### 從 53.5 reactivated（in scope）

- ✅ **AD-Front-1** Playwright bootstrap + e2e specs (US-1 + US-2 + US-3)
- ✅ **AD-Front-2** Production HITL wiring at chat router (US-4)
- ✅ **AD-Hitl-4-followup** ServiceFactory consolidation (US-5)

### Defer 至 53.7 / audit cycle / 後續 sprint

- 🚧 **AD-Hitl-7** Per-tenant HITLPolicy DB persistence → 54.x
- 🚧 **AD-Hitl-8** approvals.status DB CHECK constraint update for 'escalated' → audit cycle
- 🚧 **AD-Cat9-1** LLM-as-judge fallback → 53.7+
- 🚧 **AD-Cat9-2/3** SANITIZE replace + REROLL replay → 54.1 (Cat 10)
- 🚧 **AD-Cat9-5** Max-calls counter → 53.7+
- 🚧 **AD-Cat9-6** WORMAuditLog real-DB integration tests → audit cycle
- 🚧 **AD-Cat9-7** Audit FATAL escalation → 54.x
- 🚧 **AD-Cat9-8** Known-FP fixture → 53.7+
- 🚧 **AD-Cat9-9** Detector fixture expansion → audit cycle
- 🚧 **AD-Cat8-2** (53.2 carryover) → audit cycle
- 🚧 **AD-CI-4/5/6** plan template + required_checks vs paths + Deploy to Production → audit cycle

### 53.6 新 Audit Debt（保留位置；retro 補充）

`AD-E2E-*` 可能在 retrospective Q4 加入（e.g., flaky spec resolution / fixture refactor / additional cross-browser）。

---

## §10 Process 修補落地檢核

- [x] Plan 文件起草前讀 53.5 plan 作 template (per `feedback_sprint_plan_use_prior_template.md`) ✅ done
- [ ] Checklist 同樣以 53.5 為 template（Day 0-4，每 task 3-6 sub-bullets，含 DoD + Verify command）
- [ ] Pre-push lint 完整跑 black + isort + flake8 + mypy（53.3 教訓）
- [ ] Pre-push 也跑 6 個 V2 lint scripts（53.4 教訓 — `feedback_v2_lints_must_run_locally.md`）
- [ ] Day 0 探勘 必 grep 新增的 LoopEvent 類型（per `feedback_sse_serializer_scope_check.md`，本 sprint 預期 0 new event 但檢核仍跑）
- [ ] PR commit message 含 scope + sprint ID + Co-Authored-By
- [ ] Anti-pattern checklist 11 條 PR 前自檢
- [ ] CARRY items 清單可追溯到 53.5 retrospective
- [ ] V2 lint 6 scripts CI green
- [ ] Frontend lint + type check + build green
- [ ] Playwright e2e green (3 specs)

---

## Retrospective 必答（per W3-2 + 52.6 + 53.1 + 53.2 + 53.3 + 53.4 + 53.5 教訓）

Day 4 retrospective.md 必答 6 題：

1. **Sprint Goal achieved?**（Yes/No + e2e 主流量驗證證據 + production wiring grep）
2. **estimated vs actual hours**（per US；總計）
3. **What went well**（≥ 3 items；含 banked buffer 來源）
4. **What can improve**（≥ 3 items + 對應的 follow-up action）
5. **Drift documented?**（V2 紀律 9 項自查；逐項 ✅/⚠️ 評估）
6. **Audit Debt logged?**（AD-E2E-* + 任何新發現的 issue）

---

## Sprint Closeout

- [ ] All 5 USs delivered with 主流量 verification
- [ ] PR open + 5 active CI checks → green (含新加 Frontend E2E)
- [ ] Normal merge to main (solo-dev policy: review_count=0; no temp-relax needed)
- [ ] retrospective.md filled
- [ ] Memory update (project_phase53_6_frontend_e2e_prod_hitl.md + index)
- [ ] Branch deleted (local + remote)
- [ ] V2 progress: **18/22 (82%)**
- [ ] Cat 9 production-deployable end-to-end
- [ ] AD-Front-1 closed
- [ ] AD-Front-2 closed
- [ ] AD-Hitl-4-followup closed
- [ ] Branch protection required_checks updated to include Frontend E2E（admin op post-merge）
