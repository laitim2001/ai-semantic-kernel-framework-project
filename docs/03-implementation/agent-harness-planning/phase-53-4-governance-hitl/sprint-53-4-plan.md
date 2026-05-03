# Sprint 53.4 — Governance Frontend + V1 HITL/Risk 遷移 + §HITL 中央化

> **Sprint Type**: V2 main sprint (governance integration + frontend completion)
> **Owner Categories**: §HITL (中央化) / Cat 7 (Reducers 配合) / Cat 9 (Stage 3 escalation 收尾)
> **Phase**: 53 (Cross-Cutting Production Hardening)
> **Workload**: 1 week (Day 0-4, ~25-28 hours)
> **Branch**: `feature/sprint-53-4-governance-hitl`
> **Plan Authority**: This document (per CLAUDE.md §Sprint Execution Workflow)
> **Roadmap Source**: `06-phase-roadmap.md` §Sprint 53.4
> **Carryover bundled**: AD-Cat9-4 (Stage 3 explicit confirmation Teams/UI) — overlaps with US-3 + US-7

---

## Sprint Goal

將 V1 的 HITL 政策、Risk 評估、Audit 查詢遷移到 V2 `platform_layer/governance/`，**完整實作 §HITL 中央化**（HITLManager 為唯一入口，Cat 2/9 呼叫端統一改用），加上 Frontend governance pages + Teams webhook + Cat 7 reducers 配合，使 **Cat 9 達 Level 4+**（連同 §HITL 中央化），並收尾 53.3 carryover AD-Cat9-4。

**主流量驗收標準**：
- HITL 審批流程（chat 內 ApprovalRequested → governance 頁批准/拒絕/升級 → loop resume）端到端可用
- 跨 session 4hr 後 resume；multi-instance 任一 worker 可 pickup pending；3 種 fallback 政策正確
- Cat 9 ToolGuardrail Stage 3 ESCALATE 不再是 stub，而是真正觸發 HITLManager

---

## Background

### V2 進度

- **15/22 sprints (68%)** completed (Phase 49-55 roadmap)
- 53.3 closed (Cat 9 core: GuardrailEngine + 4 detectors + Tripwire + WORM audit + AgentLoop 3-layer integration)
- main HEAD: `ca57ae86`

### 為什麼 53.4 拆出獨立 sprint

原 V2 roadmap 把「3 層 guardrails + V1 Risk/HITL 遷移 + audit + frontend governance」全擠進 53.3，PM review 評估約 2 週工作量；拆 53.3 (Guardrails 核心) + 53.4 (Governance 整合) 後各 1 週可控。

### 既有結構

```
backend/src/
├── agent_harness/hitl/                  # 53.3 已建 ABC + tools
│   ├── _abc.py                          # 78 lines (HITLProvider ABC)
│   ├── __init__.py
│   ├── README.md
│   └── (沒有具體 impl —— 由 53.4 補上)
├── agent_harness/_contracts/hitl.py     # 87 lines (ApprovalRequest/Decision)
├── agent_harness/tools/hitl_tools.py    # 53.3 殘留 (request_approval tool)
├── agent_harness/guardrails/tool/       # 53.3 完成 (ToolGuardrail Stage 1+2)
│   └── tool_guardrail.py                # Stage 3 ESCALATE 為 stub
└── platform_layer/governance/
    ├── hitl/                            # 53.4 主要工作目標
    │   ├── __init__.py                  # 空 stub
    │   └── README.md
    ├── risk/                            # 53.4 主要工作目標
    │   ├── __init__.py                  # 空 stub
    │   └── README.md
    └── (沒有 audit/ —— 由 53.4 建立)

frontend/src/pages/governance/           # 53.4 主要工作目標
├── index.tsx                            # 空 stub
└── README.md

archived/v1-phase1-48/backend/src/domain/audit/
├── logger.py                            # V1 audit logger (參考)
└── (V1 hitl/risk 在其他位置 —— Day 0 探勘)
```

### V2 紀律 9 項對齐確認

1. **Server-Side First** ✅ HITL state 全持久化於 DB（pending → approved/rejected/escalated state machine 跨 session 可恢復）
2. **LLM Provider Neutrality** ✅ 不引入新 LLM SDK
3. **CC Reference 不照搬** ✅ Anthropic CC 沒有 enterprise HITL；V1 HITL 邏輯為主，CC 對話模式只作 frontend UX 參考
4. **17.md Single-source** ✅ HITLManager 實作 17.md §HITL contract; ApprovalRequest/Decision 已在 _contracts/hitl.py
5. **11+1 範疇歸屬** ✅ §HITL = 中央化 cross-cutting; Cat 7 Reducer 配合; Cat 2/9 呼叫端整合
6. **04 anti-patterns** ✅ AP-3 Bridge Debt（V1 HITL 真遷移不留 bridge）/ AP-4 Potemkin（Stage 3 ESCALATE 真做不留 stub）
7. **Sprint workflow** ✅ plan → checklist → code（本文件）
8. **File header convention** ✅ 所有新檔案需符合
9. **Multi-tenant rule** ✅ HITL pending list per-tenant 隔離；reviewer 只能看到自己 tenant 的 pending

---

## User Stories

### US-1: V1 Risk 政策遷移到 `platform_layer/governance/risk/`

**As** a security/compliance officer
**I want** the V1 risk assessment policies (categorical risk levels: low/medium/high/critical) ported into V2's governance layer
**So that** Cat 9 ToolGuardrail can consult risk policy when deciding stage escalation, and audit can record risk-tagged decisions

**Acceptance**:
- `platform_layer/governance/risk/policy.py` — RiskPolicy ABC + DefaultRiskPolicy（YAML config 驅動）
- `platform_layer/governance/risk/levels.py` — RiskLevel enum (LOW/MEDIUM/HIGH/CRITICAL)
- `backend/config/risk_policy.yaml` — tool_name → risk_level 映射；可被 capability_matrix.yaml 引用
- 與 Cat 9 ToolGuardrail 整合：stage decision 函數簽名 `decide(tool_call, context, risk_level) -> StageDecision`
- 單元測試：RiskPolicy 評估 + YAML 載入 + tenant override 路徑（per-tenant overlay）
- coverage ≥ 85%

**Files**:
- 新建: `backend/src/platform_layer/governance/risk/policy.py`, `levels.py`, `__init__.py`
- 新建: `backend/config/risk_policy.yaml`
- 修改: `backend/src/agent_harness/guardrails/tool/tool_guardrail.py`（注入 RiskPolicy 依賴）
- 新建: `backend/tests/unit/platform_layer/governance/risk/test_policy.py`

### US-2: HITLManager 核心實作（state machine + persistence）

**As** an AI engineer
**I want** a production-ready HITLManager that owns the approval state machine (pending → approved/rejected/escalated/expired) with DB persistence, multi-instance pickup, and 4hr resume window
**So that** any Cat 2/9 caller can request approval through a single entry point and rely on enterprise-grade state recovery

**Acceptance**:
- `platform_layer/governance/hitl/manager.py` — HITLManager 完整實作
- DB 表：`hitl_approvals` (id, tenant_id, request_uuid, state, payload_json, decision_json, created_at, decided_at, expires_at, decided_by_user_id, decided_by_role)
- alembic migration
- State machine：state 轉換規則 + 不可逆轉換驗證（rejected → approved 拒絕）
- 4hr 過期掃描（背景 task）：超時自動轉 expired + apply fallback policy
- Multi-instance：用 `SELECT ... FOR UPDATE SKIP LOCKED` 實作 pickup
- Tenant 隔離：所有 query 強制 `WHERE tenant_id = current_tenant`
- 單元測試 + 整合測試（含 multi-instance 並發 pickup 測試）
- coverage ≥ 85%

**Files**:
- 新建: `backend/src/platform_layer/governance/hitl/manager.py`, `state_machine.py`, `__init__.py`
- 新建: `backend/src/infrastructure/db/models/hitl_approval.py`
- 新建: `backend/alembic/versions/<timestamp>_add_hitl_approvals.py`
- 新建: `backend/tests/unit/platform_layer/governance/hitl/test_manager.py`, `test_state_machine.py`
- 新建: `backend/tests/integration/platform_layer/governance/hitl/test_multi_instance_pickup.py`

### US-3: §HITL 中央化 — Cat 2/9 callers 統一改用 HITLManager

**As** a V2 architect
**I want** all approval-requesting code paths (Cat 2 hitl_tools + Cat 9 ToolGuardrail Stage 3 + future callers) to flow through HITLManager
**So that** there's exactly one place to enforce approval policy, audit, multi-instance behavior, and tenant isolation (eliminates AP-3 Cross-Directory Scattering)

**Acceptance**:
- Cat 2 `agent_harness/tools/hitl_tools.py` `request_approval` tool 改用 HITLManager（不再直接寫 DB）
- Cat 9 `guardrails/tool/tool_guardrail.py` Stage 3 ESCALATE branch 真實呼叫 HITLManager（不再是 stub）→ **closes AD-Cat9-4**
- HITLManager 為 single-source；grep 證據：所有 ApprovalRequest 創建點都經過 HITLManager
- 整合測試：Cat 9 主流量觸發 Stage 3 → HITLManager pending → mock approve → loop resume
- coverage ≥ 85% 跨呼叫端

**Files**:
- 修改: `backend/src/agent_harness/tools/hitl_tools.py`（refactor 用 HITLManager）
- 修改: `backend/src/agent_harness/guardrails/tool/tool_guardrail.py`（Stage 3 真整合）
- 新建: `backend/tests/integration/agent_harness/governance/test_hitl_centralization.py`

### US-4: Audit 查詢 API（read-only views）

**As** a compliance auditor
**I want** REST endpoints to query the WORM audit log (Sprint 49.3 + 53.3 hash chain) with filters by tenant/user/operation/time-range and chain-verify endpoint
**So that** audit reports can be generated without DB access

**Acceptance**:
- `platform_layer/governance/audit/query.py` — AuditQuery service
- API endpoints (FastAPI):
  - `GET /api/v1/audit/log?tenant_id=...&user_id=...&from=...&to=...&op_type=...` (paginated)
  - `GET /api/v1/audit/verify-chain?from=...&to=...` （call ChainVerifier）
- Tenant 隔離：強制 current_tenant filter
- RBAC：只允許 role=auditor 或 admin
- 整合測試：跨租戶不可見 + chain verify endpoint 正確報告
- coverage ≥ 80%

**Files**:
- 新建: `backend/src/platform_layer/governance/audit/query.py`, `__init__.py`
- 新建: `backend/src/api/v1/audit.py`（FastAPI router）
- 修改: `backend/src/api/v1/__init__.py`（register audit router）
- 新建: `backend/tests/integration/api/test_audit_endpoints.py`

### US-5: Cat 7 HITLDecisionReducer + SubagentResultReducer

**As** an agent loop developer
**I want** typed reducers that merge HITL decisions and subagent results back into LoopState during resume
**So that** Cat 7 state recovery (Sprint 53.1) handles HITL-paused loops correctly without state corruption

**Acceptance**:
- `agent_harness/state_mgmt/reducers/hitl_decision_reducer.py` — typed reducer
- `agent_harness/state_mgmt/reducers/subagent_result_reducer.py` — typed reducer
- 註冊到 DefaultReducer registry
- 單元測試：HITL decision 不同 state 路徑 + 並發 decision conflict resolution
- coverage ≥ 85%

**Files**:
- 新建: `backend/src/agent_harness/state_mgmt/reducers/hitl_decision_reducer.py`, `subagent_result_reducer.py`
- 修改: `backend/src/agent_harness/state_mgmt/reducers/__init__.py`（register）
- 新建: `backend/tests/unit/agent_harness/state_mgmt/reducers/test_hitl_decision_reducer.py`, `test_subagent_result_reducer.py`

### US-6: Teams Notification Webhook

**As** a reviewer
**I want** Teams notifications when an approval is pending for me/my role, with one-click links to the governance approvals page
**So that** I don't have to constantly check the UI

**Acceptance**:
- `platform_layer/governance/hitl/notifier.py` — HITLNotifier ABC + TeamsWebhookNotifier impl
- HITLManager hook：on pending → notifier.notify()
- Webhook URL per-tenant config（`backend/config/notification.yaml`）
- 失敗降級：notifier 失敗不阻 HITL flow（best-effort + audit log）
- 單元測試 + 整合測試（mock webhook server）
- coverage ≥ 80%

**Files**:
- 新建: `backend/src/platform_layer/governance/hitl/notifier.py`, `notifiers/teams_webhook.py`
- 修改: `backend/src/platform_layer/governance/hitl/manager.py`（注入 notifier）
- 新建: `backend/config/notification.yaml`
- 新建: `backend/tests/unit/platform_layer/governance/hitl/test_notifier.py`

### US-7: Frontend `pages/governance/approvals/` — Pending List + Decision Modal

**As** a reviewer
**I want** a dedicated page to see all pending approvals assigned to me/my role, sorted by priority + age, with one-click approve/reject/escalate modal
**So that** I can quickly process approvals without context-switching to chat

**Acceptance**:
- Page route: `/governance/approvals`
- Pending list：tenant + role 過濾；columns: request_uuid, tool_name, requested_by, age, priority
- Decision modal：approve / reject (with reason) / escalate (to higher role)
- 即時更新（SSE 或 polling）
- E2E 測試（Playwright）：approve flow 從 list → modal → 後端 state 變 approved → loop resume
- 對齐 16-frontend-design.md §Page 6 (Governance)

**Files**:
- 新建: `frontend/src/pages/governance/approvals/index.tsx`, `ApprovalList.tsx`, `DecisionModal.tsx`
- 新建: `frontend/src/services/governance_service.ts`
- 修改: `frontend/src/pages/governance/index.tsx`（加 link）
- 新建: `frontend/tests/e2e/governance/approvals.spec.ts`

### US-8: Frontend Inline Chat Approval Card（SSE ApprovalRequested event）

**As** a chat user with reviewer role
**I want** an inline approval card to appear in the chat when an approval is requested, with quick approve/reject buttons, while still allowing me to deep-link to governance page
**So that** simple approvals don't require leaving the chat

**Acceptance**:
- Component: `<ApprovalCard>` (React)
- SSE event handler：`ApprovalRequested` event → render card; `ApprovalDecided` event → update card to disabled+result
- Approve/Reject buttons → POST to backend HITL decision endpoint
- Card shows: tool name, request reason, risk level, deep-link to `/governance/approvals/{id}`
- E2E 測試：chat 觸發 → card 出現 → approve → backend state 變更 → loop resume
- 對齐 02-architecture-design.md §SSE 事件規範

**Files**:
- 新建: `frontend/src/components/chat/ApprovalCard.tsx`
- 修改: `frontend/src/pages/chat-v2/ChatPage.tsx`（加 SSE event handler）
- 新建: `frontend/tests/e2e/chat/approval-card.spec.ts`

### US-9: AD-Cat9-4 Stage 3 explicit confirmation flow（53.3 carryover）

**As** a security engineer
**I want** the Cat 9 ToolGuardrail Stage 3 ESCALATE branch fully wired to HITLManager + Teams + UI, with audit trail every step
**So that** the carryover from 53.3 is closed and Cat 9 reaches Level 4+

**Acceptance** (overlaps with US-3 + US-6 + US-7 + US-8 — this US is the verification glue):
- E2E 測試覆蓋：sensitive tool call → Cat 9 GuardrailEngine → ToolGuardrail Stage 3 ESCALATE → HITLManager pending → Teams notification fired → reviewer 在 governance page 看到 pending → click approve → loop resume → audit chain integrity verify
- Audit log 完整：每個 stage transition 都記錄 with hash chain link
- AD-Cat9-4 標記 closed in retrospective
- Cat 9 alignment: **Level 4+** (production HITL infrastructure)

**Files**:
- 新建: `backend/tests/integration/agent_harness/governance/test_stage3_escalation_e2e.py`
- 修改: `backend/tests/integration/.../test_loop_guardrails.py`（加 Stage 3 e2e case）

---

## Technical Specifications

### File Skeletons

```python
# backend/src/platform_layer/governance/risk/levels.py
from enum import Enum

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
```

```python
# backend/src/platform_layer/governance/risk/policy.py
from abc import ABC, abstractmethod

class RiskPolicy(ABC):
    @abstractmethod
    def evaluate(self, tool_name: str, arguments: dict, tenant_id: UUID) -> RiskLevel: ...

class DefaultRiskPolicy(RiskPolicy):
    """YAML-config-driven default risk policy with per-tenant overlays."""
    def __init__(self, config_path: str): ...
    def evaluate(self, tool_name: str, arguments: dict, tenant_id: UUID) -> RiskLevel: ...
```

```python
# backend/src/platform_layer/governance/hitl/manager.py
class HITLManager:
    """Owner: §HITL 中央化 single-source. All approval requests flow through here."""

    def __init__(self, db: AsyncSession, notifier: HITLNotifier, expiry_seconds: int = 14400):
        self.db = db
        self.notifier = notifier
        self.expiry_seconds = expiry_seconds

    async def request_approval(
        self, *, tenant_id: UUID, requester_id: UUID, payload: ApprovalRequestPayload,
        expected_role: str | None = None
    ) -> ApprovalRequest:
        """Create pending approval; trigger notification."""

    async def decide(
        self, *, tenant_id: UUID, request_uuid: UUID, decision: ApprovalDecision,
        decided_by_user_id: UUID, decided_by_role: str
    ) -> ApprovalRequest:
        """Apply decision (state machine validated; tenant isolated)."""

    async def pickup_pending(
        self, *, tenant_id: UUID, role: str, limit: int = 10
    ) -> list[ApprovalRequest]:
        """Multi-instance pickup using SELECT ... FOR UPDATE SKIP LOCKED."""

    async def expire_overdue(self) -> int:
        """Background scan; transition expired pending → expired with fallback policy."""
```

```python
# backend/src/agent_harness/state_mgmt/reducers/hitl_decision_reducer.py
class HITLDecisionReducer(Reducer):
    """Merge HITL decision into LoopState during resume."""

    def reduce(self, state: LoopState, event: HITLDecisionEvent) -> LoopState:
        """state.hitl_pending → state.hitl_decided (immutable)."""
```

```typescript
// frontend/src/components/chat/ApprovalCard.tsx
interface ApprovalCardProps {
  approvalId: string;
  toolName: string;
  reason: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
}

export function ApprovalCard({ approvalId, toolName, reason, riskLevel }: ApprovalCardProps) {
  // SSE event handler (consumed by parent ChatPage); buttons POST to backend
}
```

### DB Schema (alembic migration)

```sql
CREATE TABLE hitl_approvals (
  id BIGSERIAL PRIMARY KEY,
  request_uuid UUID NOT NULL UNIQUE,
  tenant_id UUID NOT NULL,
  requester_id UUID NOT NULL,
  expected_role VARCHAR(64),
  state VARCHAR(32) NOT NULL DEFAULT 'pending',
  payload_json JSONB NOT NULL,
  decision_json JSONB,
  decided_by_user_id UUID,
  decided_by_role VARCHAR(64),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  decided_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ NOT NULL,
  CONSTRAINT chk_state CHECK (state IN ('pending', 'approved', 'rejected', 'escalated', 'expired'))
);

CREATE INDEX idx_hitl_tenant_state ON hitl_approvals (tenant_id, state, expires_at);
CREATE INDEX idx_hitl_role ON hitl_approvals (tenant_id, expected_role, state) WHERE state = 'pending';

-- RLS policy
ALTER TABLE hitl_approvals ENABLE ROW LEVEL SECURITY;
CREATE POLICY hitl_tenant_isolation ON hitl_approvals
  USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

### YAML Config

```yaml
# backend/config/risk_policy.yaml
version: "1.0"
default_risk: medium

tool_overrides:
  - pattern: "salesforce_*"
    risk: high
  - pattern: "send_email"
    risk: medium
  - pattern: "delete_*"
    risk: critical
  - pattern: "read_*"
    risk: low

per_tenant_overlays:
  enterprise_strict:
    delete_*: critical  # 升 high → critical
```

```yaml
# backend/config/notification.yaml
version: "1.0"
defaults:
  enabled: true
  fallback_silent: false

teams:
  webhooks:
    default: ${TEAMS_WEBHOOK_URL}
    per_tenant_overrides: {}

  message_template: |
    🔔 Approval pending: {tool_name}
    Risk: {risk_level} | Tenant: {tenant_id}
    Requested by: {requester_email}
    Reason: {reason}

    [Review →]({approval_url})
```

---

## File Change List

### 新建（17 backend + 5 frontend = 22 個）

**Backend**:
1. `backend/src/platform_layer/governance/risk/policy.py`
2. `backend/src/platform_layer/governance/risk/levels.py`
3. `backend/src/platform_layer/governance/risk/__init__.py`
4. `backend/src/platform_layer/governance/hitl/manager.py`
5. `backend/src/platform_layer/governance/hitl/state_machine.py`
6. `backend/src/platform_layer/governance/hitl/notifier.py`
7. `backend/src/platform_layer/governance/hitl/notifiers/teams_webhook.py`
8. `backend/src/platform_layer/governance/hitl/notifiers/__init__.py`
9. `backend/src/platform_layer/governance/audit/query.py`
10. `backend/src/platform_layer/governance/audit/__init__.py`
11. `backend/src/infrastructure/db/models/hitl_approval.py`
12. `backend/alembic/versions/<timestamp>_add_hitl_approvals.py`
13. `backend/src/api/v1/audit.py`
14. `backend/src/api/v1/governance.py` (HITL decision endpoint)
15. `backend/src/agent_harness/state_mgmt/reducers/hitl_decision_reducer.py`
16. `backend/src/agent_harness/state_mgmt/reducers/subagent_result_reducer.py`
17. `backend/config/risk_policy.yaml`, `backend/config/notification.yaml`

**Frontend**:
1. `frontend/src/pages/governance/approvals/index.tsx`
2. `frontend/src/pages/governance/approvals/ApprovalList.tsx`
3. `frontend/src/pages/governance/approvals/DecisionModal.tsx`
4. `frontend/src/components/chat/ApprovalCard.tsx`
5. `frontend/src/services/governance_service.ts`

### 修改（8 個）

1. `backend/src/agent_harness/tools/hitl_tools.py`（改用 HITLManager）
2. `backend/src/agent_harness/guardrails/tool/tool_guardrail.py`（Stage 3 真整合）
3. `backend/src/api/v1/__init__.py`（register routers）
4. `backend/src/agent_harness/state_mgmt/reducers/__init__.py`（register reducers）
5. `frontend/src/pages/governance/index.tsx`（加 link to approvals）
6. `frontend/src/pages/chat-v2/ChatPage.tsx`（加 SSE event handler）
7. `backend/src/platform_layer/governance/hitl/__init__.py`（export HITLManager）
8. `backend/src/platform_layer/governance/risk/__init__.py`（export RiskPolicy）

### 測試（13 個新檔）

- 6 unit + 5 integration + 2 frontend e2e (Playwright)

---

## Acceptance Criteria

### 主流量端到端驗收

- [ ] **Cat 9 ToolGuardrail Stage 3 真整合**：sensitive tool 觸發 → ESCALATE → HITLManager pending → Teams 通知 → reviewer 在 governance page approve → loop resume
- [ ] **跨 session resume**：HITL pending 4hr 後 reviewer 仍可 approve；loop 從 checkpoint 恢復
- [ ] **Multi-instance pickup**：兩個 backend 實例同時運行；同一 pending 只被一個處理（SKIP LOCKED 驗證）
- [ ] **3 種 fallback 政策正確**：reject / escalate / approve_with_audit 都有測試覆蓋
- [ ] **Tenant 隔離**：tenant A reviewer 看不到 tenant B pending（list / decide 都拒絕）
- [ ] **Teams 通知**：pending 觸發 webhook；失敗不阻 HITL flow

### 品質門檻

- [ ] pytest 全綠 (預期 970+ passed)
- [ ] mypy --strict 0 errors
- [ ] flake8 + black + isort + ruff green（包含 pre-push 必跑 flake8）
- [ ] coverage：governance/hitl/ ≥ 85%; governance/risk/ ≥ 85%; governance/audit/ ≥ 80%
- [ ] LLM SDK leak: 0
- [ ] 6 V2 lint scripts: all green
- [ ] Frontend Playwright e2e: 2 specs green

### 範疇對齐

- [ ] **Cat 9 達 Level 4+**（連同 §HITL 中央化）
- [ ] **§HITL 中央化完成**：grep 證據顯示所有 ApprovalRequest 創建點都經過 HITLManager
- [ ] AD-Cat9-4 closed in retrospective

---

## Deliverables（見 checklist 詳細）

US-1 到 US-9 共 9 個 User Stories；checklist 拆分到 Day 0-4。

---

## Dependencies & Risks

### Dependencies

| Dependency | 來自 | 必須狀態 |
|------------|------|---------|
| Cat 9 GuardrailEngine + ToolGuardrail | 53.3 | ✅ merged main `ca57ae86` |
| Cat 7 DefaultReducer + DBCheckpointer | 53.1 | ✅ merged main |
| WORM audit log + chain verifier | 49.3 + 53.3 | ✅ merged main |
| Cat 8 Error Handling | 53.2 | ✅ merged main |

### Risks

| Risk | Mitigation |
|------|-----------|
| V1 HITL 邏輯位置不明（archive 找不到具體 module） | Day 0 第一件事：grep V1 archive 找 HITL/Risk 邏輯位置；找不到就純新建，不假裝是「遷移」 |
| Multi-instance pickup race condition | 用 PostgreSQL `SELECT ... FOR UPDATE SKIP LOCKED`；整合測試模擬並發 |
| 4hr resume window 跨 worker restart | HITL state 全持久化於 DB；checkpoint by Cat 7 reducer |
| Teams webhook 失敗影響 HITL flow | Best-effort + audit log 記錄失敗；不 block HITL state machine |
| Frontend SSE event 重複 / 漏訊 | 用 event_uuid dedup；reconnect 時 replay last 50 events |
| §HITL 中央化遷移漏修 caller | grep `ApprovalRequest(` + `request_approval(` 全 codebase 確認 |
| DB migration 與 53.1 既有 hitl 邏輯衝突 | Day 0 alembic baseline 確認；migration 使用 `IF NOT EXISTS` 防衝突 |

### 主流量驗證承諾

53.4 不允許「stub-only」交付。每個 US 必須有真實 e2e 測試案例驗證主流量（per CLAUDE.md §Constraint 2 主流量驗證原則）。

---

## Audit Carryover Section（per W3 process fix #1）

### 從 53.3 reactivated

- ✅ **AD-Cat9-4** Stage 3 explicit confirmation Teams/UI → bundled into US-9 (verification glue)

### Defer 至 53.5 / 後續 audit cycle

- 🚧 **AD-Cat9-1** LLM-as-judge fallback → 53.5 (Cat 9 polish)
- 🚧 **AD-Cat9-2/3** SANITIZE replace + REROLL replay → 54.1 (Cat 10)
- 🚧 **AD-Cat9-5** Max-calls counter → 53.5
- 🚧 **AD-Cat9-6** WORMAuditLog real-DB integration tests → audit cycle
- 🚧 **AD-Cat9-7** Audit FATAL escalation → 54.x
- 🚧 **AD-Cat9-8** Known-FP fixture for "what does jailbreak mean" → 53.5
- 🚧 **AD-Cat9-9** Detector fixture expansion → audit cycle
- 🚧 **AD-Cat8-2** (53.2 carryover) → audit cycle
- 🚧 **AD-CI-4/5** plan template + required_checks vs paths → audit cycle
- 🚧 **AD-CI-6 (新)** Deploy to Production chronic fail → audit cycle

### 53.4 新 Audit Debt（保留位置；retro 補充）

`AD-Hitl-1`, `AD-Hitl-2` 等 will be logged in retrospective Q4.

---

## §10 Process 修補落地檢核

- [ ] Plan 文件起草前讀 53.3 plan 作 template (per `feedback_sprint_plan_use_prior_template.md`)
- [ ] Checklist 同樣以 53.3 為 template（Day 0-4，每 task 3-6 sub-bullets，含 DoD + Verify command）
- [ ] Pre-push lint 完整跑 black + isort + flake8 + mypy（53.3 教訓）
- [ ] PR commit message 含 scope + sprint ID + Co-Authored-By
- [ ] Anti-pattern checklist 11 條 PR 前自檢
- [ ] CARRY items 清單可追溯到 53.3 retrospective
- [ ] V2 lint 6 scripts CI green

---

## Retrospective 必答（per W3-2 + 52.6 + 53.1 + 53.2 + 53.3 教訓）

Day 4 retrospective.md 必答 6 題：

1. **Sprint Goal achieved?**（Yes/No + 主流量驗證證據）
2. **estimated vs actual hours**（per US；總計）
3. **What went well**（≥ 3 items；含 banked buffer 來源）
4. **What can improve**（≥ 3 items + 對應的 follow-up action）
5. **Drift documented?**（V2 紀律 9 項自查；逐項 ✅/⚠️ 評估）
6. **Audit Debt logged?**（AD-Hitl-* + 任何新發現的 issue）

---

## Sprint Closeout

- [ ] All 9 USs delivered with main流量 verification
- [ ] PR open + CI green + normal merge to main
- [ ] retrospective.md filled
- [ ] Memory update (project_phase53_4_governance_hitl.md + index)
- [ ] Branch deleted (local + remote)
- [ ] V2 progress: 16/22 (73%)
- [ ] Cat 9 Level 4+; §HITL 中央化 complete
- [ ] Frontend governance + chat approval card live
