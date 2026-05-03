# Sprint 53.4 Progress — Governance Frontend + V1 HITL/Risk 遷移 + §HITL 中央化

**Branch**: `feature/sprint-53-4-governance-hitl`
**Plan**: [sprint-53-4-plan.md](../../../agent-harness-planning/phase-53-4-governance-hitl/sprint-53-4-plan.md)
**Checklist**: [sprint-53-4-checklist.md](../../../agent-harness-planning/phase-53-4-governance-hitl/sprint-53-4-checklist.md)

---

## Day 0 — 2026-05-03 — Setup + V1 探勘 + Baselines

### 0.1 Branch + plan + checklist commit ✅

- Branch: `feature/sprint-53-4-governance-hitl` from main `ca57ae86`
- Plan + checklist committed: `782b184a` (2 files, 950 insertions)
- Pushed to remote

### 0.2 GitHub issues 建立 ✅

9 issues opened (#63 — #71) with `sprint-53-4` label:

| # | Issue | US | Priority |
|---|-------|----|---------|
| #63 | US-1 V1 Risk policy migration | US-1 | P0 |
| #64 | US-2 HITLManager core | US-2 | P0 |
| #65 | US-3 §HITL 中央化 (Cat 2/9 callers) | US-3 | P0 |
| #66 | US-4 Audit Query API | US-4 | P0 |
| #67 | US-5 Cat 7 Reducers | US-5 | P0 |
| #68 | US-6 Teams Webhook Notifier | US-6 | P0 |
| #69 | US-7 Frontend governance/approvals | US-7 | P0 |
| #70 | US-8 Frontend chat ApprovalCard | US-8 | P0 |
| #71 | US-9 AD-Cat9-4 e2e verification | US-9 | P0 |

### 0.3 V1 HITL/Risk 探勘結果 ✅

#### V1 Risk modules (archive: `archived/v1-phase1-48/`)

| File | Lines | 評估 |
|------|-------|------|
| `integrations/hybrid/risk/engine.py` | 560 | **參考**：策略邏輯主入口（V1 hybrid orchestrator-driven）；V2 改為 YAML+ABC 結構 |
| `integrations/hybrid/risk/models.py` | 302 | **參考**：RiskLevel enum + RiskAssessment dataclass；V2 簡化（少了 hybrid 時代的 DAG state） |
| `integrations/hybrid/risk/scoring/scorer.py` | 311 | **參考**：rule-based scoring；V2 不直接遷移（Cat 9 已有 detector layer） |
| `integrations/hybrid/risk/analyzers/*` | ~600 | **不遷移**：V1 hybrid orchestrator 特有邏輯，V2 由 Cat 9 detectors 取代 |
| `api/v1/hybrid/risk_routes.py` | ? | **不遷移**：V1 API 結構 |

**V2 53.4 結論**：V1 Risk 邏輯**啟發**而非**直接遷移**。V2 RiskPolicy 為 ABC + YAML config（`risk_policy.yaml`），不重用 V1 engine.py 的 hybrid-specific 設計。

#### V1 HITL modules (archive)

| File | Lines | 評估 |
|------|-------|------|
| `integrations/orchestration/hitl/unified_manager.py` | ? | **參考**：V1 已有 manager 概念；V2 HITLManager 新建（Cat 2/9 真整合，不像 V1 散落） |
| `integrations/orchestration/hitl/controller.py` | ? | **不遷移**：V1 hybrid controller 邏輯 |
| `integrations/orchestration/hitl/approval_handler.py` | ? | **不遷移**：V1 callback-based handler |
| `integrations/orchestration/hitl/notification.py` | ? | **參考**：V1 notification template idea；V2 用 Teams webhook adaptive card |
| `integrations/orchestration/approval/service.py` | 181 | **參考**：approval state machine 概念；V2 在 platform_layer 重新實作 |
| `domain/sessions/approval.py` | 582 | **參考**：domain model；V2 多租戶 + state machine 簡化 |
| `infrastructure/storage/approval_store.py` | 450 | **參考**：DB persistence 邏輯；V2 用 SQLAlchemy + alembic 重做 |

**V2 53.4 結論**：V1 HITL **設計概念**有用（unified_manager 中央化精神 + state machine + DB persistence），但 V1 是 hybrid orchestrator-driven 架構與 V2 11+1 範疇結構不相容。V2 53.4 為**全新實作 + V1 概念啟發**，不是「程式碼搬運」。

### 0.4 V2 既有結構 baseline ✅

| Path | 狀態 |
|------|------|
| `agent_harness/hitl/_abc.py` | 78 行 — ABC 完整（HITLProvider）53.3 已建 |
| `agent_harness/_contracts/hitl.py` | 87 行 — ApprovalRequest/Decision dataclass 已定義 |
| `agent_harness/hitl/__init__.py` | 空 stub |
| `agent_harness/tools/hitl_tools.py` | 53.3 殘留（request_approval tool；Day 3 改用 HITLManager） |
| `platform_layer/governance/hitl/__init__.py` | 空 stub |
| `platform_layer/governance/hitl/README.md` | 存在（53.4 explore 用） |
| `platform_layer/governance/risk/__init__.py` | 空 stub |
| `platform_layer/governance/risk/README.md` | 存在 |
| `platform_layer/governance/audit/` | **不存在** — 53.4 新建 |
| `frontend/src/pages/governance/index.tsx` | 空 stub |
| `frontend/src/pages/governance/approvals/` | **不存在** — 53.4 新建 |

### 0.5 Cat 9 ToolGuardrail Stage 3 stub 位置確認 ✅

`backend/src/agent_harness/guardrails/tool/tool_guardrail.py`：
- Line 16: docstring "Stage 3 (explicit confirmation) — this guardrail returns ESCALATE"
- Line 29: comment "rule.requires_approval=True → ESCALATE (MEDIUM)"
- **Line 134**: `action=GuardrailAction.ESCALATE,` ← **此為 53.3 留下的 stub；US-3 + US-9 將替換為 HITLManager 真整合**

### 0.6 alembic baseline (US-2 prep) ✅

- alembic CLI working
- Current head: `0010_pg_partman`
- 53.4 US-2 將新增 `0011_add_hitl_approvals` migration

### 0.7 Day 0 progress.md ✅

This file (you are reading).

---

## Day 0 Summary

| Metric | Value |
|--------|-------|
| Hours estimated | 3-4 |
| Hours actual | ~2.5 (V1 探勘 efficient via grep) |
| Banked buffer | ~1 hour (drift docs Day 1+) |
| Blockers | 無 |
| Drift | 無（all checklist items completed as planned） |

### Key Findings

1. **V1 HITL/Risk 邏輯豐富但架構不相容** — 53.4 為**啟發式重新實作**，不是程式碼搬運
2. **V2 ABC + contracts 已就位**（53.3 留下）— 直接 build manager + impl
3. **Cat 9 Stage 3 stub 明確定位**（line 134）— US-3/US-9 修改清晰
4. **alembic baseline 穩定** — `0011_add_hitl_approvals` 安全添加

### Day 1 Plan

- 1.1 RiskLevel + RiskPolicy ABC + DefaultRiskPolicy YAML loader
- 1.2 risk_policy.yaml + 5+ test cases
- 1.3 HITLManager skeleton + state_machine.py
- 1.4 hitl_approval ORM model + alembic migration
- 1.5 state_machine unit tests (≥6 cases)
- 1.6 sanity (mypy/lint)
- 1.7 commit + push + verify CI
- 1.8 progress.md Day 1 update

Estimated 6-7 hours.

---

## Day 1 — 2026-05-03 — US-1 Risk Policy + US-2 HITL Skeleton

### Accomplishments

#### US-1 Risk Policy ✅ Production-ready

| File | LoC | Coverage |
|------|-----|---------|
| `platform_layer/governance/risk/policy.py` | 133 | **100%** |
| `platform_layer/governance/risk/__init__.py` | 8 | **100%** |
| `backend/config/risk_policy.yaml` | 35 | n/a |
| `tests/unit/.../test_policy.py` | 100 (8 cases) | n/a |

**Drift**: ⚠️ `RiskLevel` was already single-sourced at `agent_harness/_contracts/hitl.py` per 17.md §1. SKIPPED creation of `governance/risk/levels.py` to avoid duplicate definition. Imports from contracts.

#### US-2 HITL Skeleton ✅ State machine ready, manager stubs ready for Day 2

| File | LoC | Coverage | Status |
|------|-----|----------|--------|
| `platform_layer/governance/hitl/state_machine.py` | 87 | **100%** | Production-ready |
| `platform_layer/governance/hitl/manager.py` | 124 | 59% | Skeleton (Day 2 fills DB logic) |
| `platform_layer/governance/hitl/__init__.py` | 23 | 100% | Production-ready |
| `tests/unit/.../test_state_machine.py` | 89 (11 cases) | n/a | All pass |

**Drift**: ⚠️ Major buffer-banking discovery — `Approval` ORM model + table already exist at `infrastructure/db/models/governance.py` from Sprint 49.3 (per `0008_governance.py` migration + `09-db-schema-design.md` L566-601). Schema covers all required fields (id/session_id/action_*/risk_*/status/teams_*/created_at/expires_at/decided_at). SKIPPED:
- New ORM model creation
- New alembic migration

Day 2 will reuse existing `Approval` model. May add tiny migration only if `escalated` state needs DB CHECK constraint update (TBD Day 2).

### Sanity Status

| Check | Result |
|-------|--------|
| black --check | ✅ 9 files clean |
| isort --check | ✅ clean |
| flake8 | ✅ clean |
| mypy --strict | ✅ 5 source files clean |
| pytest tests/unit/platform_layer/governance/ | ✅ **19/19 pass** |
| Coverage governance/ | **90%** (manager 59% — Day 2 fills) |

### Day 1 Summary

| Metric | Value |
|--------|-------|
| Hours estimated | 6-7 |
| Hours actual | ~3 (huge buffer from existing approvals table + ABC) |
| Banked buffer | **+3-4 hours** (cumulative ~5 from Day 0+1) |
| Blockers | 無 |
| Drift | 2 documented (RiskLevel single-source + Approval ORM reuse) |

### Day 2 Plan

- 2.1 HITLManager.request_approval() — INSERT INTO approvals via session
- 2.1 HITLManager.decide() — UPDATE with state machine validation
- 2.1 HITLManager.get_pending() with FOR UPDATE SKIP LOCKED
- 2.1 HITLManager.expire_overdue() background scan
- 2.2 Integration tests (multi-instance pickup + 3 fallback policies)
- 2.3 US-5 Cat 7 HITLDecisionReducer + SubagentResultReducer
- 2.4-2.6 sanity / commit / progress.md

Estimated 6-7 hours; banked ~5 hours buffer makes Day 2 schedule comfortable.

---

## Day 2 — 2026-05-03 — US-2 Full Impl + US-5 Reducers

### Accomplishments

#### US-2 HITLManager Full Implementation ✅ Production-ready

| File | LoC | Coverage | Notes |
|------|-----|----------|-------|
| `platform_layer/governance/hitl/manager.py` | 248 | **97%** | 6 ABC methods + escalate() helper |

**Methods implemented**:
- `request_approval()` — INSERT into existing `approvals` table + best-effort notifier
- `decide()` — state machine validated UPDATE
- `get_pending()` — JOIN sessions for tenant filter + `with_for_update(skip_locked=True)`
- `wait_for_decision()` — poll-based DB check with timeout
- `get_policy()` — returns default_policy or fallback (Day 3+ extends with DB)
- `expire_overdue()` — background sweep transitioning pending→expired
- `escalate()` — helper: terminate current + create fresh PENDING under higher role

**Drift adjustment**: ABC method names match 17.md §5.2 exactly (`get_pending` not `pickup_pending`, `wait_for_decision` not `wait`).

#### US-2 Integration Tests ✅ 11/11 pass

`tests/integration/platform_layer/governance/hitl/test_manager.py` covers:
1. request_approval persists pending
2. decide approved transitions state
3. decide rejected → terminal (cannot re-decide)
4. decide unknown request raises LookupError
5. **tenant isolation** in get_pending (cross-tenant invisible)
6. expire_overdue transitions pending → expired
7. wait_for_decision returns after decide
8. wait_for_decision timeout
9. get_policy returns default
10. **escalate** creates new pending under higher role
11. **notifier called best-effort** (failure does not block)

#### US-5 Reducer Helpers ✅ 6/6 pass

`agent_harness/state_mgmt/decision_reducers.py` (single file, not directory):
- `HITLDecisionReducer.build_patch(decision)` → DefaultReducer-compatible patch (removes pending_approval_id + appends marker message)
- `SubagentResult` dataclass + `SubagentResultReducer.build_patch(result)` → patch (metadata keyed by subagent_id so parallel subagents disjoint)

**Drift**: Helpers do NOT subclass Reducer — they build patches consumed by the existing DefaultReducer. This preserves the Sprint 53.1 sole-mutator pattern (DefaultReducer = only Reducer impl).

### Sanity Status

| Check | Result |
|-------|--------|
| black --check | ✅ clean |
| isort --check | ✅ clean |
| flake8 | ✅ clean |
| mypy --strict | ✅ Success: no issues found |
| pytest unit + integration governance/ + state_mgmt/ | ✅ **36/36 pass** |
| Coverage governance/ | **98%** (manager 97% + state_machine 100% + risk policy 100%) |

### Day 2 Summary

| Metric | Value |
|--------|-------|
| Hours estimated | 6-7 |
| Hours actual | ~3 (existing schema + ABC + Reducer pattern reuse) |
| Banked buffer | **+3-4 hours** (cumulative ~8 from Day 0+1+2) |
| Blockers | 無 (one minor pytest __init__.py issue resolved within minutes) |
| Drift | 1 documented (Reducer helpers do NOT subclass Reducer ABC) |

### Day 3 Plan

- 3.1-3.3 US-3 §HITL 中央化 — refactor Cat 2 hitl_tools + Cat 9 ToolGuardrail Stage 3 真整合
- 3.4-3.5 US-4 Audit Query API + tests
- 3.6 US-6 HITLNotifier ABC + TeamsWebhookNotifier
- 3.7-3.8 sanity / commit / progress.md

Estimated 6-7 hours.

---

## Day 3 — 2026-05-03 — US-3 (Cat 2 part) + US-6 Notifier

### Accomplishments

#### US-3 part 1 — `hitl_tools.py` refactored ✅

- New: `make_request_approval_handler(hitl_manager, tenant_id_resolver, session_id_resolver)` — closure factory binding handler to a DefaultHITLManager. Production code uses this for real persistence.
- Kept: legacy `request_approval_handler(call)` — deprecated placeholder; tests confirm it returns DEPRECATED note + does NOT persist via manager. Backward-compatible while migration completes.
- `agent_harness/tools/__init__.py` — exported new factory.

#### US-6 — Notifier ABC + Teams webhook ✅

- New: `platform_layer/governance/hitl/notifier.py` — HITLNotifier ABC + NoopNotifier
- New: `platform_layer/governance/hitl/teams_webhook.py` — TeamsWebhookNotifier with AdaptiveCard payload, per-tenant URL override, best-effort failure handling (logs + swallows)
- Manager already wired to call notifier post-persist (Day 1 skeleton); failure best-effort verified by Day 2 test

#### Tests — 7 cases ✅

`test_hitl_centralization.py`:
- US-3: 4 cases — handler persists via manager / severity → risk mapping (low/medium/high) / unknown severity fallback / legacy handler does NOT persist
- US-6: 3 cases — AdaptiveCard with review link / no link when no template / per-tenant override

### Drift Documented (3 items)

1. **Cat 9 ToolGuardrail Stage 3 wiring 🚧 DEFERRED to Day 4** — bundled into US-9 e2e verification glue. The HITLManager integration belongs at the loop's `_cat9_tool_check` layer, not inside ToolGuardrail itself. ToolGuardrail correctly returns ESCALATE; orchestrator handles flow. This minimizes Cat 9 surface change.
2. **`teams_webhook.py` placement** — placed at `platform_layer/governance/hitl/` directly instead of a `notifiers/` subpackage (single-file subpackage was unnecessary).
3. **`notification.yaml` SKIPPED** — TeamsWebhookNotifier accepts URL via constructor; config wiring belongs to ServiceFactory layer (deferred to Day 4 if scope allows).

### Sanity Status

| Check | Result |
|-------|--------|
| black --check | ✅ clean |
| isort --check | ✅ clean |
| flake8 | ✅ clean |
| mypy --strict | ✅ Success: no issues found in 6 source files |
| pytest governance/ + hitl_centralization/ + state_mgmt/ | ✅ **43/43 pass** |

### Day 3 Summary

| Metric | Value |
|--------|-------|
| Hours estimated | 6-7 |
| Hours actual | ~2.5 (HITLManager already had notifier hook from Day 1; closure factory pattern straightforward) |
| Banked buffer | **+3-4 hours** (cumulative ~11 from Day 0+1+2+3) |
| Blockers | 無 |

### Day 4 Plan (full day, ~7-8 hours estimated)

- 4.1 US-7 Frontend `pages/governance/approvals/` (ApprovalList + DecisionModal + governance_service)
- 4.2 US-7 Playwright e2e
- 4.3 US-8 inline chat ApprovalCard + SSE event handler in ChatPage
- 4.4 US-9 Stage 3 e2e verification (closes AD-Cat9-4)
- 4.5 US-4 Audit Query API + endpoint (smaller scope; audit query only, defer chain verify endpoint to follow-up if time pressed)
- 4.6 Sprint final verification (lint chain + grep evidence + coverage gates + 6 V2 lint scripts)
- 4.7 retrospective.md + PR open + closeout
- 4.8 cleanup + memory update

Cumulative ~11 hours banked → Day 4 has plenty of headroom.
