# Sprint 53.5 — Governance Frontend + Cat 9 Loop Wiring + Audit HTTP API

> **Sprint Type**: V2 main sprint (53.4 frontend + integration carryover)
> **Owner Categories**: Frontend (V2 page 6 governance + chat-v2 SSE) / Cat 9 (Stage 3 loop wiring) / Cat 12 (Audit HTTP API)
> **Phase**: 53 (Cross-Cutting Production Hardening)
> **Workload**: 1 week (Day 0-4, ~22-31 hours)
> **Branch**: `feature/sprint-53-5-governance-frontend`
> **Plan Authority**: This document (per CLAUDE.md §Sprint Execution Workflow)
> **Roadmap Source**: `06-phase-roadmap.md` §Sprint 53.5 (split from 53.4 for clean scoping)
> **Carryover bundled**: 8 AD-Hitl-* (1-6 in scope; 7-8 deferred) + AD-Cat9-4 (Stage 3 loop wiring closes here)

---

## Sprint Goal

完成 Sprint 53.4 §HITL 中央化的**前端整合 + 主流量端到端閉環**：將 53.4 已建好的 backend HITL infrastructure（HITLManager / AuditQuery / TeamsWebhookNotifier）對接到 (a) governance approvals 頁面（List + Modal + Playwright e2e）、(b) chat-v2 inline ApprovalCard（SSE 事件 + 審批互動）、(c) Cat 9 ToolGuardrail Stage 3 → AgentLoop `_cat9_tool_check` → HITLManager 主流量 wiring（**closes AD-Cat9-4**），同時補齊 audit HTTP endpoint + chain verify endpoint，使 Cat 9 達 **Level 5（production-ready end-to-end）**。

**主流量驗收標準**：
- chat-v2 觸發敏感工具 → Cat 9 Stage 3 → AgentLoop pause → HITLManager pending → Teams 通知 → reviewer 在 governance page approve → loop resume → 完整 audit chain verify
- Frontend governance page 跨租戶隔離 + RBAC（reviewer 只看自己 tenant + 自己 role）
- Audit endpoint 可被 compliance 角色查詢（paginated + chain verify）

---

## Background

### V2 進度

- **16/22 sprints (73%)** completed (Phase 49-55 roadmap)
- 53.4 closed (backend §HITL central infrastructure: RiskPolicy + HITLManager production + Cat 7 reducers + AuditQuery service + TeamsWebhookNotifier + Cat 2 hitl_tools refactor)
- main HEAD: `872021ee`

### 為什麼 53.5 拆出獨立 sprint

53.4 retrospective Q4 旗標：「Frontend stack work (US-7 + US-8) requires Playwright runner + test infrastructure that's not part of `db_session` shared fixture pattern; estimating frontend-heavy days alongside backend is unrealistic in 1-week sprint。」因此 53.5 為 frontend-focused sprint，加 Day 0 explicit Playwright setup + 補回 53.4 deferred Cat 9 loop wiring（架構正確但 blast radius 大，獨立 sprint 處理）。

### 既有結構

```
backend/src/                                            # 53.4 backend 已就位
├── platform_layer/governance/
│   ├── hitl/manager.py                                 # ✅ DefaultHITLManager production
│   ├── hitl/notifier.py                                # ✅ HITLNotifier ABC + NoopNotifier
│   ├── hitl/teams_webhook.py                           # ✅ TeamsWebhookNotifier (per-tenant override)
│   ├── audit/query.py                                  # ✅ AuditQuery service (paginated + chain verify)
│   └── risk/policy.py                                  # ✅ DefaultRiskPolicy YAML
├── agent_harness/tools/hitl_tools.py                   # ✅ make_request_approval_handler factory
├── agent_harness/guardrails/tool/tool_guardrail.py     # 🚧 Stage 3 ESCALATE returns enum but loop wiring 未完
├── agent_harness/orchestrator_loop/loop.py             # 🚧 _cat9_tool_check stub for HITLManager call
├── api/v1/                                             # 🚧 audit router 未建
└── config/                                             # 🚧 notification.yaml 未建

frontend/src/                                           # 53.5 主要工作目標
├── pages/governance/
│   ├── index.tsx                                       # 既有 stub
│   ├── approvals/                                      # 🚧 不存在
│   │   ├── index.tsx                                   # 待建
│   │   ├── ApprovalList.tsx                            # 待建
│   │   └── DecisionModal.tsx                           # 待建
│   └── README.md
├── pages/chat-v2/ChatPage.tsx                          # 🚧 ApprovalRequested SSE handler 未實作
├── components/chat/                                    # 🚧 ApprovalCard 不存在
└── services/governance_service.ts                      # 🚧 不存在

frontend/tests/e2e/                                     # 🚧 governance + approval-card spec 未建
```

### V2 紀律 9 項對齐確認

1. **Server-Side First** ✅ Frontend 純 SSE consumer + REST client；所有狀態在後端 DB
2. **LLM Provider Neutrality** ✅ 不引入新 LLM SDK（frontend 不打 LLM）
3. **CC Reference 不照搬** ✅ Anthropic CC 沒有 enterprise approval UI；參考 V1 governance page 設計但 V2 重做為 React + Zustand
4. **17.md Single-source** ✅ 所有 ApprovalRequest creation 已在 53.4 經 HITLManager；US-3 在 loop 層整合 = single-source 維持
5. **11+1 範疇歸屬** ✅ Frontend = 對應 Page 6（per `16-frontend-design.md`）；Cat 9 wiring = `agent_harness/orchestrator_loop/loop.py` ；audit endpoint = `api/v1/audit.py`
6. **04 anti-patterns** ✅ AP-3 cross-directory: governance components 集中 `pages/governance/approvals/`；AP-4 Potemkin: 每 US 必有 e2e；AP-9 verification: Stage 3 wiring 走過 HITLManager + audit
7. **Sprint workflow** ✅ plan → checklist → code（本文件 + 53.4 plan/checklist 為 template）
8. **File header convention** ✅ 所有新檔案需符合（含 .tsx）
9. **Multi-tenant rule** ✅ governance_service 強制 tenant filter；e2e 跨租戶測試覆蓋

---

## User Stories

### US-1: Frontend `pages/governance/approvals/` — Pending List + Decision Modal

**As** a reviewer (auditor / approver / admin role)
**I want** a dedicated page at `/governance/approvals` to see all pending approvals filtered by my tenant + role, with sortable columns and one-click approve/reject/escalate modal
**So that** I can quickly process approvals without context-switching to chat

**Acceptance**:
- Page route: `/governance/approvals` (React Router v6)
- ApprovalList: tenant + role 過濾；columns: request_uuid, tool_name, requested_by, age, risk_level, priority
- DecisionModal: approve / reject (with reason) / escalate (to higher role)
- 即時更新（SSE topic `governance.approvals.pending` 或 polling fallback）
- governance_service.ts: API client wrapping `/api/v1/governance/approvals/*`
- Playwright e2e: full approve flow（list → modal → backend state changes → loop resume）
- Multi-tenant test: tenant A reviewer 看不到 tenant B pending（403 / 空列）
- 對齐 16-frontend-design.md §Page 6 (Governance)

**Files**:
- 新建: `frontend/src/pages/governance/approvals/index.tsx`, `ApprovalList.tsx`, `DecisionModal.tsx`
- 新建: `frontend/src/services/governance_service.ts`
- 修改: `frontend/src/pages/governance/index.tsx`（加 link to approvals）
- 修改: `frontend/src/router/index.tsx`（register route）
- 新建: `frontend/tests/e2e/governance/approvals.spec.ts`

### US-2: Frontend Inline Chat ApprovalCard

**As** a chat user with reviewer role
**I want** an inline approval card to appear in the chat when an approval is requested, with quick approve/reject buttons + deep-link to governance page
**So that** simple approvals don't require leaving the chat

**Acceptance**:
- Component: `<ApprovalCard>` (React + Zustand subscription)
- SSE event handler in ChatPage: `ApprovalRequested` → render card; `ApprovalDecided` → update card to disabled+result
- Card 顯示: tool name, request reason, risk_level badge, deep-link to `/governance/approvals/{id}`
- Approve/Reject buttons → POST `/api/v1/governance/approvals/{id}/decide` (via governance_service)
- Risk level color coding (LOW=green / MEDIUM=yellow / HIGH=orange / CRITICAL=red)
- Playwright e2e: chat 觸發 → card 出現 → approve → backend state 變更 → loop resume
- 對齐 02-architecture-design.md §SSE 事件規範

**Files**:
- 新建: `frontend/src/components/chat/ApprovalCard.tsx`
- 修改: `frontend/src/pages/chat-v2/ChatPage.tsx`（加 SSE event handler）
- 修改: `frontend/src/stores/chat_store.ts`（加 approvals slice）
- 新建: `frontend/tests/e2e/chat/approval-card.spec.ts`

### US-3: Cat 9 ToolGuardrail Stage 3 → AgentLoop → HITLManager 主流量 Wiring（closes AD-Cat9-4）

**As** a security engineer
**I want** the Cat 9 ToolGuardrail Stage 3 ESCALATE branch fully wired through AgentLoop's `_cat9_tool_check` to HITLManager.request_approval(), with loop pause + checkpoint + resume on decision, and audit trail every step
**So that** AD-Cat9-4 carryover is closed and Cat 9 reaches Level 5（production-ready end-to-end）

**Acceptance**:
- AgentLoop `_cat9_tool_check`: when ToolGuardrail returns `Stage.ESCALATE` → call `hitl_manager.request_approval()` → pause loop（Cat 7 checkpoint）→ wait_for_decision()
- Resume path: HITLDecisionReducer (53.4 US-5) merges decision → loop continues
- Tripwire 連帶：Stage 3 escalate 一律觸發 audit log (WORM hash chain link)
- Risk policy integration: ESCALATE 觸發前 evaluate(tool_name) → embed risk_level in ApprovalRequest
- Integration test: sensitive tool call → Stage 3 → HITLManager pending → mock approve → loop resume → audit chain verify
- e2e test (orchestrator-level): real loop + real HITLManager + mock notifier
- Cat 9 alignment: **Level 5**

**Files**:
- 修改: `backend/src/agent_harness/orchestrator_loop/loop.py`（implement `_cat9_tool_check` HITL branch）
- 修改: `backend/src/agent_harness/guardrails/tool/tool_guardrail.py`（return RiskLevel + ApprovalPayload context）
- 新建: `backend/tests/integration/agent_harness/governance/test_stage3_escalation_e2e.py`
- 修改: `backend/tests/integration/agent_harness/guardrails/test_loop_guardrails.py`（加 Stage 3 e2e case）

### US-4: `notification.yaml` + ServiceFactory wiring for TeamsWebhookNotifier

**As** an ops engineer
**I want** Teams webhook URL configurable per-tenant via YAML with environment variable fallback, and HITLManager automatically wired to the correct notifier via ServiceFactory
**So that** different tenants can route approvals to different Teams channels without code changes

**Acceptance**:
- Config: `backend/config/notification.yaml`（version + defaults + teams.webhooks.{default, per_tenant_overrides}）
- ServiceFactory wiring: HITLManager constructor receives notifier instance from factory
- Tenant-aware notifier resolution: `factory.get_hitl_manager(tenant_id)` returns HITLManager with correct notifier
- Environment variable interpolation: `${TEAMS_WEBHOOK_URL}` style
- Failure fallback: notification.yaml 不存在 → NoopNotifier；webhook URL 缺失 → log warning + NoopNotifier
- Unit test: YAML loading + env var interpolation + per-tenant override + fallback paths
- Integration test: ServiceFactory returns correct notifier per tenant

**Files**:
- 新建: `backend/config/notification.yaml`
- 修改: `backend/src/platform_layer/governance/hitl/notifier.py`（add factory function `load_notifier_from_config`）
- 新建/修改: `backend/src/platform_layer/governance/service_factory.py`（HITL manager factory; new file or extend existing）
- 修改: `backend/src/agent_harness/orchestrator_loop/loop.py`（use factory for HITLManager）
- 新建: `backend/tests/unit/platform_layer/governance/hitl/test_notification_config.py`

### US-5: Audit HTTP API endpoint (`api/v1/audit.py`)

**As** a compliance auditor
**I want** REST endpoints to query the WORM audit log with filters by tenant/user/operation/time-range, paginated, with RBAC enforcement
**So that** audit reports can be generated through API without DB access

**Acceptance**:
- Endpoint: `GET /api/v1/audit/log?from=...&to=...&op_type=...&user_id=...&page=...&page_size=...`
- RBAC: only `auditor` / `admin` / `compliance` roles allowed (403 otherwise)
- Tenant isolation: 強制 `current_tenant_id` filter (404 for cross-tenant attempts)
- Pagination: default 50, max 200
- Response schema: `{items: AuditLogEntry[], total: int, page: int, page_size: int}`
- Integration test: 6 cases (paginated query / cross-tenant 404 / non-auditor 403 / role accepted / time-range filter / op_type filter)
- coverage ≥ 80%

**Files**:
- 新建: `backend/src/api/v1/audit.py`（FastAPI router）
- 修改: `backend/src/api/v1/__init__.py`（register audit router）
- 修改: `backend/src/api/dependencies.py`（add RBAC dep `require_audit_role`）
- 新建: `backend/tests/integration/api/test_audit_endpoints.py`

### US-6: Audit Chain Verify Endpoint (`GET /api/v1/audit/verify-chain`)

**As** a compliance auditor
**I want** an endpoint to verify the WORM hash chain integrity over a time range
**So that** I can prove audit log immutability for compliance reports

**Acceptance**:
- Endpoint: `GET /api/v1/audit/verify-chain?from=...&to=...`
- Behavior: calls AuditQuery.verify_chain() → returns `{verified: bool, broken_at: int|null, chain_length: int, total_entries: int}`
- RBAC: same as US-5（auditor / admin / compliance）
- Tenant isolation: only verify chain within current_tenant
- Integration test: verified chain returns true / synthetic broken chain returns false + broken_at index / cross-tenant 404
- coverage ≥ 80%

**Files**:
- 修改: `backend/src/api/v1/audit.py`（add verify-chain endpoint）
- 修改: `backend/src/platform_layer/governance/audit/query.py`（add verify_chain method if not yet present）
- 修改: `backend/tests/integration/api/test_audit_endpoints.py`（add 3 verify-chain cases）

---

## Technical Specifications

### File Skeletons

```typescript
// frontend/src/services/governance_service.ts
export interface ApprovalRequestSummary {
  request_uuid: string;
  tenant_id: string;
  tool_name: string;
  reason: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  requested_by: string;
  created_at: string;
  expires_at: string;
  state: 'pending' | 'approved' | 'rejected' | 'escalated' | 'expired';
}

export const governanceService = {
  async listPending(role?: string): Promise<ApprovalRequestSummary[]> { ... },
  async decide(approvalId: string, decision: 'approved' | 'rejected' | 'escalated', reason?: string): Promise<void> { ... },
};
```

```typescript
// frontend/src/components/chat/ApprovalCard.tsx
interface ApprovalCardProps {
  approvalId: string;
  toolName: string;
  reason: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  state: 'pending' | 'approved' | 'rejected' | 'escalated';
  onDecide?: (decision: 'approved' | 'rejected') => void;
}

export function ApprovalCard({ ... }: ApprovalCardProps) {
  // SSE-driven; buttons → governance_service.decide(); deep-link to /governance/approvals/{id}
}
```

```python
# backend/src/agent_harness/orchestrator_loop/loop.py (excerpt)
async def _cat9_tool_check(self, tool_call: ToolCall, state: LoopState) -> ToolGuardrailDecision:
    decision = await self.tool_guardrail.evaluate(tool_call, state.context)
    if decision.stage == Stage.ESCALATE:
        # 53.5 US-3 wiring
        risk_level = self.risk_policy.evaluate(tool_call.name, tool_call.arguments, state.tenant_id)
        approval = await self.hitl_manager.request_approval(
            tenant_id=state.tenant_id,
            requester_id=state.user_id,
            payload=ApprovalRequestPayload(
                tool_name=tool_call.name,
                reason=decision.reason,
                risk_level=risk_level,
            ),
        )
        # Pause loop + checkpoint
        state = await self.checkpointer.save(state, pending_approval_id=approval.request_uuid)
        # Wait for decision (4hr window; cross-session resume supported)
        decision_event = await self.hitl_manager.wait_for_decision(
            tenant_id=state.tenant_id,
            request_uuid=approval.request_uuid,
            timeout_seconds=14400,
        )
        # Reduce decision into state (Cat 7 reducer)
        state = HITLDecisionReducer.reduce(state, decision_event)
        if decision_event.decision == ApprovalDecision.REJECTED:
            return ToolGuardrailDecision(stage=Stage.BLOCK, reason="Rejected by reviewer")
        # APPROVED → continue tool execution
    return decision
```

```yaml
# backend/config/notification.yaml
version: "1.0"
defaults:
  enabled: true
  fallback_silent: false  # log warning when notifier unavailable

teams:
  webhooks:
    default: ${TEAMS_WEBHOOK_URL}
    per_tenant_overrides:
      # tenant_id: webhook_url
      # 00000000-0000-0000-0000-000000000001: ${TEAMS_WEBHOOK_TENANT_001}

  message_template: |
    🔔 Approval pending: {tool_name}
    Risk: {risk_level} | Tenant: {tenant_short_id}
    Requested by: {requester_email}
    Reason: {reason}

    [Review →]({approval_url})
```

### API Schemas

```python
# backend/src/api/v1/audit.py
@router.get("/log", response_model=AuditLogPage)
async def get_audit_log(
    current_user: User = Depends(require_audit_role),
    current_tenant: UUID = Depends(get_current_tenant),
    filter: AuditQueryFilter = Depends(),
    pagination: Pagination = Depends(),
) -> AuditLogPage: ...

@router.get("/verify-chain", response_model=ChainVerifyResult)
async def verify_chain(
    current_user: User = Depends(require_audit_role),
    current_tenant: UUID = Depends(get_current_tenant),
    from_ts: datetime,
    to_ts: datetime,
) -> ChainVerifyResult: ...
```

### SSE Event Schema (chat-v2)

```typescript
// frontend SSE events for ApprovalCard
type ApprovalSSEEvent =
  | { type: 'ApprovalRequested'; data: ApprovalRequestSummary }
  | { type: 'ApprovalDecided'; data: { approvalId: string; decision: 'approved' | 'rejected' | 'escalated'; decided_by: string } };
```

---

## File Change List

### 新建（11 backend + 6 frontend = 17 個）

**Backend**:
1. `backend/config/notification.yaml`
2. `backend/src/api/v1/audit.py` (FastAPI router; US-5 + US-6)
3. `backend/src/platform_layer/governance/service_factory.py` (or extend existing)
4. `backend/tests/integration/api/test_audit_endpoints.py`
5. `backend/tests/integration/agent_harness/governance/test_stage3_escalation_e2e.py`
6. `backend/tests/unit/platform_layer/governance/hitl/test_notification_config.py`

**Frontend**:
1. `frontend/src/pages/governance/approvals/index.tsx`
2. `frontend/src/pages/governance/approvals/ApprovalList.tsx`
3. `frontend/src/pages/governance/approvals/DecisionModal.tsx`
4. `frontend/src/services/governance_service.ts`
5. `frontend/src/components/chat/ApprovalCard.tsx`
6. `frontend/tests/e2e/governance/approvals.spec.ts`
7. `frontend/tests/e2e/chat/approval-card.spec.ts`

### 修改（10 個）

1. `backend/src/agent_harness/orchestrator_loop/loop.py` (`_cat9_tool_check` HITL wiring)
2. `backend/src/agent_harness/guardrails/tool/tool_guardrail.py` (return RiskLevel context)
3. `backend/src/api/v1/__init__.py` (register audit router)
4. `backend/src/api/dependencies.py` (add `require_audit_role`)
5. `backend/src/platform_layer/governance/hitl/notifier.py` (factory function)
6. `backend/src/platform_layer/governance/audit/query.py` (verify_chain if missing)
7. `backend/tests/integration/agent_harness/guardrails/test_loop_guardrails.py` (Stage 3 case)
8. `frontend/src/pages/governance/index.tsx` (link to approvals)
9. `frontend/src/pages/chat-v2/ChatPage.tsx` (SSE handler)
10. `frontend/src/stores/chat_store.ts` (approvals slice)

### 測試（4 unit + 4 integration + 2 frontend e2e = 10 新檔）

---

## Acceptance Criteria

### 主流量端到端驗收

- [ ] **Cat 9 Stage 3 真整合主流量**：sensitive tool 觸發 → ToolGuardrail Stage 3 → AgentLoop pause + checkpoint → HITLManager pending → Teams notification → reviewer governance page approve → loop resume → result returned to user
- [ ] **跨 session resume**：HITL pending 4hr 後 reviewer 仍可 approve；loop 從 Cat 7 checkpoint 恢復
- [ ] **Frontend governance page 主流量**：reviewer 登入 → /governance/approvals 顯示 tenant 內 pending → click → modal → approve → list 自動更新
- [ ] **Inline ApprovalCard 主流量**：chat 觸發 sensitive tool → ApprovalRequested SSE → card 出現 → approve → ApprovalDecided SSE → card 顯示已批准 → loop resume
- [ ] **Multi-tenant 隔離**：tenant A reviewer 看不到 tenant B pending（list 空 / decide 404）
- [ ] **Audit endpoint 主流量**：auditor role 查詢 → paginated response；非 auditor → 403；跨 tenant → 404
- [ ] **Chain verify endpoint**：完整鏈返回 verified=true；插入 synthetic break 後返回 broken_at index

### 品質門檻

- [ ] pytest 全綠 (預期 1020+ passed)
- [ ] mypy --strict 0 errors
- [ ] flake8 + black + isort + ruff green（含 pre-push 必跑）
- [ ] coverage：governance/hitl/ ≥ 85%; api/v1/audit.py ≥ 80%; orchestrator_loop._cat9_tool_check 路徑 ≥ 90%
- [ ] LLM SDK leak: 0
- [ ] 6 V2 lint scripts: all green
- [ ] Frontend Playwright e2e: 2 specs green
- [ ] Frontend lint + type check + build green

### 範疇對齐

- [ ] **Cat 9 達 Level 5**（Stage 3 production-ready end-to-end with HITL + audit chain）
- [ ] **AD-Cat9-4 closed**（Stage 3 explicit confirmation Teams/UI 完整鏈路 verified）
- [ ] **§HITL 中央化主流量驗證**：grep 證據 — Stage 3 ESCALATE 0 stub remaining；所有 ApprovalRequest 來自 HITLManager

---

## Deliverables（見 checklist 詳細）

US-1 到 US-6 共 6 個 User Stories；checklist 拆分到 Day 0-4。

---

## Dependencies & Risks

### Dependencies

| Dependency | 來自 | 必須狀態 |
|------------|------|---------|
| HITLManager production | 53.4 US-2 | ✅ merged main `872021ee` |
| Cat 7 HITLDecisionReducer | 53.4 US-5 | ✅ merged main |
| AuditQuery service | 53.4 US-4 | ✅ merged main |
| TeamsWebhookNotifier | 53.4 US-6 | ✅ merged main |
| Cat 9 ToolGuardrail Stage 1+2 | 53.3 | ✅ merged main |
| WORM audit log + chain verifier | 49.3 + 53.3 | ✅ merged main |
| chat-v2 SSE infrastructure | Phase 50 | ✅ merged main |

### Risks

| Risk | Mitigation |
|------|-----------|
| Playwright runner 在 CI 環境設置複雜 | Day 0 第一件事：本地 Playwright init + headless chromium 確認；CI 環境 Playwright workflow 用 `--reporter=list` 輕量級 reporter |
| Frontend SSE event 重複 / 漏訊（chat-v2 ApprovalCard 收兩次或漏一次） | 用 approval_uuid 為 key dedup；reconnect 時 replay last 50 approvals events |
| AgentLoop `_cat9_tool_check` HITL pause 與 Cat 7 checkpoint race | 先 checkpoint 再 wait_for_decision；wait timeout 在 4hr cross-session window |
| ServiceFactory 重構影響其他 sprint | 採 additive 策略：擴充現有 factory（如已存在）或新建小 factory 不破既有 wiring |
| YAML env var interpolation 失敗 | 用 `os.path.expandvars` + 缺失 fallback to NoopNotifier + log warning |
| Cross-tenant test 設置複雜（需多 tenant fixture） | 重用 53.4 既有 multi-tenant fixture（已驗證 cross-tenant 隔離） |
| Audit endpoint pagination 性能（大 audit log） | 加 `LIMIT/OFFSET` + `WHERE timestamp BETWEEN` index；max page_size = 200 |

### 主流量驗證承諾

53.5 不允許「stub-only」交付。每個 US 必須有 e2e 測試案例驗證主流量（per CLAUDE.md §Constraint 2 主流量驗證原則）。Frontend US 必須有 Playwright e2e green。

---

## Audit Carryover Section（per W3 process fix #1）

### 從 53.4 reactivated（in scope）

- ✅ **AD-Hitl-1** US-1 (Frontend governance approvals page)
- ✅ **AD-Hitl-2** US-2 (Frontend inline chat ApprovalCard)
- ✅ **AD-Hitl-3** US-3 (Cat 9 loop wiring → closes AD-Cat9-4)
- ✅ **AD-Hitl-4** US-4 (notification.yaml + ServiceFactory)
- ✅ **AD-Hitl-5** US-5 (Audit HTTP endpoint)
- ✅ **AD-Hitl-6** US-6 (Audit chain verify endpoint)

### Defer 至 53.6 / audit cycle / 後續 sprint

- 🚧 **AD-Hitl-7** Per-tenant HITLPolicy DB persistence → 54.x
- 🚧 **AD-Hitl-8** approvals.status DB CHECK constraint update for 'escalated' → audit cycle
- 🚧 **AD-Cat9-1** LLM-as-judge fallback → 53.6+
- 🚧 **AD-Cat9-2/3** SANITIZE replace + REROLL replay → 54.1 (Cat 10)
- 🚧 **AD-Cat9-5** Max-calls counter → 53.6+
- 🚧 **AD-Cat9-6** WORMAuditLog real-DB integration tests → audit cycle
- 🚧 **AD-Cat9-7** Audit FATAL escalation → 54.x
- 🚧 **AD-Cat9-8** Known-FP fixture → 53.6+
- 🚧 **AD-Cat9-9** Detector fixture expansion → audit cycle
- 🚧 **AD-Cat8-2** (53.2 carryover) → audit cycle
- 🚧 **AD-CI-4/5/6** plan template + required_checks vs paths + Deploy to Production → audit cycle

### 53.5 新 Audit Debt（保留位置；retro 補充）

`AD-Front-1`, `AD-Front-2` 等 will be logged in retrospective Q4.

---

## §10 Process 修補落地檢核

- [ ] Plan 文件起草前讀 53.4 plan 作 template (per `feedback_sprint_plan_use_prior_template.md`) ✅ done
- [ ] Checklist 同樣以 53.4 為 template（Day 0-4，每 task 3-6 sub-bullets，含 DoD + Verify command）
- [ ] Pre-push lint 完整跑 black + isort + flake8 + mypy（53.3 教訓）
- [ ] Pre-push 也跑 6 個 V2 lint scripts（53.4 教訓 — `feedback_v2_lints_must_run_locally.md`）
- [ ] PR commit message 含 scope + sprint ID + Co-Authored-By
- [ ] Anti-pattern checklist 11 條 PR 前自檢
- [ ] CARRY items 清單可追溯到 53.4 retrospective
- [ ] V2 lint 6 scripts CI green
- [ ] Frontend lint + type check + build green
- [ ] Playwright e2e green

---

## Retrospective 必答（per W3-2 + 52.6 + 53.1 + 53.2 + 53.3 + 53.4 教訓）

Day 4 retrospective.md 必答 6 題：

1. **Sprint Goal achieved?**（Yes/No + 主流量驗證證據）
2. **estimated vs actual hours**（per US；總計）
3. **What went well**（≥ 3 items；含 banked buffer 來源）
4. **What can improve**（≥ 3 items + 對應的 follow-up action）
5. **Drift documented?**（V2 紀律 9 項自查；逐項 ✅/⚠️ 評估）
6. **Audit Debt logged?**（AD-Front-* + 任何新發現的 issue）

---

## Sprint Closeout

- [ ] All 6 USs delivered with 主流量 verification
- [ ] PR open + 4 active CI checks → green
- [ ] Normal merge to main (solo-dev policy: review_count=0; no temp-relax needed)
- [ ] retrospective.md filled
- [ ] Memory update (project_phase53_5_governance_frontend.md + index)
- [ ] Branch deleted (local + remote)
- [ ] V2 progress: **17/22 (77%)**
- [ ] Cat 9 達 Level 5
- [ ] AD-Cat9-4 closed
- [ ] Frontend governance + chat ApprovalCard live
- [ ] Audit HTTP API live
