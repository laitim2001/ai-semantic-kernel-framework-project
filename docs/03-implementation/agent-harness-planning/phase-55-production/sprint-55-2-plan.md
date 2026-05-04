# Sprint 55.2 — V2 22/22 Closure: Production Mode Swap + Chat Handler Wiring

> **Sprint Type**: V2 main progress sprint (Phase 55 final — V2 22/22 (100%) closure)
> **Owner Categories**: Business Domain (4 deferred domains tools.py mode swap) / Cat 2 Tools (handler swap completion) / API Layer (chat handler production wiring) / Cat 12 Observability (per-request factory tracing) / §Multi-tenant rule (tenant_id threading)
> **Phase**: 55 (Production — 2/2 final sprint, closes V2 22/22)
> **Workload**: 5 days (Day 0-4); bottom-up est ~17 hr → calibrated commit **~7 hr** (multiplier **0.40** per AD-Sprint-Plan-3; 4-sprint mean 0.76 BELOW [0.85, 1.20] band → lowered 0.50 → 0.40 per 55.1 retrospective Q2 recommendation)
> **Branch**: `feature/sprint-55-2-v2-closure`
> **Plan Authority**: This document (per CLAUDE.md §Sprint Execution Workflow)
> **Roadmap Source**: 06-phase-roadmap.md §Phase 55.2 (production deployment) + 08b-business-tools-spec.md (5 domains × 18 tools production swap completion) + 55.1 retrospective.md §Q5 next-steps candidates
> **AD closures (sub-scope)**: AD-BusinessDomainPartialSwap-1 (4 deferred domains full mode swap; closes 13 service handlers) + AD-Sprint-Plan-3 (multiplier 0.50 → 0.40 first application + 5-sprint window verification in retro Q2)

---

## Sprint Goal

Complete **V2 22/22 (100%) closure** by closing the two remaining production gaps left from 55.1:

- **US-1**: Mirror 55.1 incident `mode='mock'|'service'` swap to the **4 deferred domains** (patrol / correlation / rootcause / audit_domain); each `tools.py` adds `_build_service_handlers(factory_provider)` + `_serialize_*` ORM-ish helpers + `register_*_tools(... mode='service', factory_provider=)` kwarg; closes AD-BusinessDomainPartialSwap-1 (~13 service handlers across 4 domains)
- **US-2**: `_register_all.py` thread `mode` + `factory_provider` to all 5 `register_*_tools()` calls (currently only incident receives them); `make_default_executor()` propagates the kwargs uniformly
- **US-3**: Chat handler production wiring — inject `BusinessServiceFactory` per-request from `(db_session, tenant_id, tracer)`; read `settings.BUSINESS_DOMAIN_MODE` to decide path; preserve safety default `mode='mock'` so PoC unaffected; tracer auto-threaded for Cat 12 obs spans
- **US-4**: Tests — 4 deferred domains' service-mode handler tests (~12 tests; 3 per domain critical paths); production wiring integration tests (~4 tests covering DI / mode flag / tracer propagation / multi-tenant)
- **US-5**: V2 22/22 closure ceremony — Cat 12 obs verification (3 metrics emitted across all 5 services × all methods) + Day 4 retrospective (6 必答 + V2 final summary + AD-Sprint-Plan-3 calibration verify) + closeout PR + SITUATION-V2 + CLAUDE.md → V2 22/22 (100%) + memory snapshot

Sprint 結束後:
- (a) **All 5 business domains** production-deployable via `BUSINESS_DOMAIN_MODE=service` (was: only incident in 55.1)
- (b) Chat handler `business_domain` invocation routes through `BusinessServiceFactory` (was: hardcoded mock path)
- (c) Production deployment 主流量無 hard-coded `localhost:8001` HTTP call(全 service-backed)
- (d) AD-BusinessDomainPartialSwap-1 closed; `_register_all.py` 介面對齐;5 domain 單一 mode swap pattern
- (e) **V2 進度 21/22 → 22/22 (100%)** — Phase 55 完成 2/2;V2 重構達成 100% 主進度;Phase 56+ SaaS Stage 1 規劃可啟動
- (f) AD-Sprint-Plan-3 first application data point captured(5-sprint window calibration mean re-evaluate)

**主流量驗收標準**:
- `pytest backend/tests/integration/api/test_chat_business_wiring.py` 跑 e2e: chat endpoint with `BUSINESS_DOMAIN_MODE=service` → LLM emits tool_call("mock_patrol_check_servers") → BusinessServiceFactory.get_patrol_service() → PatrolService.check_servers() → seeded fixture data → SSE event with deterministic result
- `BUSINESS_DOMAIN_MODE=service` 環境:18 tools 全走 service path, 0 HTTP call to localhost:8001
- `BUSINESS_DOMAIN_MODE=mock` 環境(default for PoC): 行為跟 51.0/55.1 一樣, 0 regression
- Multi-tenant integration test: tenant A + B 同時跑 patrol_check_servers → 各自獨立 tracer + factory(無 cross-tenant leakage)
- All 5 domain tools 在 chat handler 收到 `mode='service'` 時 raise ValueError if `factory_provider is None`(防錯)
- 4 deferred domains' service-mode handlers serialize ORM-ish models 不洩漏 SQLAlchemy state(JSON-friendly dict 同 incident 模式)
- `business_service_duration_seconds` metric 在 chat handler 主流量呼叫所有 5 domain 時都 emitted
- mypy --strict 0 errors on `business_domain/` + `api/v1/chat/`
- 6 V2 lints green(check_cross_category_import: chat handler import BusinessServiceFactory 為合法 cross-layer)

---

## Background

### V2 進度

- **21/22 sprints (95%)** completed (Phase 49-55 roadmap; 1 main sprint remaining = THIS sprint)
- 55.1 closed (Business domain production service layer + Incident DB schema + IncidentService + 4 read-only services + BUSINESS_DOMAIN_MODE flag + BusinessServiceFactory; calibration ratio 0.68; 4-sprint mean 0.76)
- main HEAD: `7ef94d30` (Sprint 55.1 closeout PR #83)
- 11+1 範疇全 Level 4;business 領域 incident 已 production-capable;**本 sprint = V2 22/22 closure** = Phase 55 完成 2/2;V2 主進度 **21/22 → 22/22 (100%)**

### 為什麼 55.2 是 closure(不是新範疇)

User approved Option A (2026-05-04 session):

1. **AD-BusinessDomainPartialSwap-1 必須關閉**:55.1 D9 為時間管理只完成 incident 完整 mode swap;4 deferred domains(patrol/correlation/rootcause/audit_domain)的 `tools.py` 仍只接受 `mock_url` kwarg(無 mode + factory_provider)。生產環境若設 `BUSINESS_DOMAIN_MODE=service` 會因為這 4 個 domain handler 不知道 service 怎麼建而 crash
2. **單一 swap pattern 必須統一**:55.1 incident 模式 `register_incident_tools(... mode='mock'|'service', factory_provider=)` 已驗證可行;55.2 把同一 pattern 機械式 mirror 到 4 deferred domains, 風險低
3. **Chat handler 是 production wiring 唯一缺口**:55.1 BusinessServiceFactory 已就緒但無人從 chat 主流量注入(目前由 test fixture 構造);55.2 把 factory 接到 chat handler 的 DI 鏈
4. **V2 22/22 ceremony 值得獨立 sprint**:除了 production scope,V2 closure 需要完整 retrospective 涵蓋 Phase 49-55 全部進度,以及 Phase 56+ SaaS roadmap 啟動條件確認
5. **Calibration multiplier 0.40 需 first application**:AD-Sprint-Plan-3 是 55.1 retro Q2 logged 的 follow-up;55.2 是首次套用 0.40 的 sprint(4-sprint mean 0.76 BELOW band → 0.50 太寬鬆 → 試 0.40)

### 既有結構(Day 0 探勘已 grep 確認)

```
backend/src/business_domain/
├── _base.py                                       # ✅ BusinessServiceBase (55.1)
├── _obs.py                                        # ✅ business_service_span ctx mgr (55.1)
├── _service_factory.py                            # ✅ BusinessServiceFactory (55.1) — 5 service builders
├── _register_all.py                               # ⚠️ make_default_executor + register_all_business_tools — currently threads mode only to incident
├── incident/
│   ├── tools.py                                   # ✅ register_incident_tools(... mode='mock'|'service', factory_provider=)
│   └── service.py                                 # ✅ IncidentService (55.1 production CRUD)
├── patrol/
│   ├── tools.py                                   # ❌ register_patrol_tools(... mock_url=)  — NO mode kwarg
│   └── service.py                                 # ✅ PatrolService (55.1 read-only stub)
├── correlation/
│   ├── tools.py                                   # ❌ NO mode kwarg
│   └── service.py                                 # ✅ CorrelationService (55.1 read-only stub)
├── rootcause/
│   ├── tools.py                                   # ❌ NO mode kwarg
│   └── service.py                                 # ✅ RootCauseService (55.1 read-only stub)
└── audit_domain/
    ├── tools.py                                   # ❌ NO mode kwarg
    └── service.py                                 # ✅ AuditService (55.1 read-only stub)

backend/src/api/v1/chat/
└── handler.py                                     # ⚠️ wires business_domain (mock-only currently)
```

### 4 deferred domains 服務介面(來自 55.1 BusinessServiceFactory builders)

| Domain | Service class methods | tools.py spec count | Service handlers needed |
|--------|----------------------|---------------------|------------------------|
| patrol | check_servers / get_results / schedule / cancel | 4 | 4 |
| correlation | analyze / find_root_cause / get_related | 3 | 3 |
| rootcause | diagnose / suggest_fix / apply_fix | 3 | 3 |
| audit_domain | query_logs / generate_report / flag_anomaly | 3 | 3 |
| **Total** | — | **13** | **13** |

### V2 紀律 9 項對齐確認

1. **Server-Side First** ✅ Service layer 全 server-side;chat handler DI 注入 factory;無 client-side state
2. **LLM Provider Neutrality** ✅ `business_domain/` 不 import LLM SDK;CI lint check_llm_sdk_leak 強制
3. **CC Reference 不照搬** ✅ 不模仿 CC tool wrappers;用 V2 service factory + dependency injection
4. **17.md Single-source** ✅ 不新增 cross-category type;`BusinessServiceFactory` 是 internal 不是 cross-category contract;mode kwarg 是 internal kwarg 不是 dataclass
5. **11+1 範疇歸屬** ✅ 全部 modify 在 `business_domain/{domain}/tools.py` + `_register_all.py` + `api/v1/chat/handler.py`;無 AP-3 (Cross-Directory Scattering)
6. **04 anti-patterns** ✅ AP-3 範疇歸屬合規;AP-4 (Potemkin) — 每 service handler 必有 unit test;AP-6 (Hybrid Bridge Debt) — `BUSINESS_DOMAIN_MODE` flag 是 55.1 既有兩條 path 統一(不是新加抽象);AP-9 N/A (verification 已在 chat 主流量);AP-10 (mock vs real divergence) — mode 強制兩條 path 用同一 service interface
7. **Sprint workflow** ✅ plan → checklist → Day 0 探勘 → code → progress → retro;本文件依 55.1 plan 結構鏡射(14 sections / Day 0-4)
8. **File header convention** ✅ 所有 modify 的 .py 含 Modification History 加新 entry
9. **Multi-tenant rule** 🔴 **CORE FOCUS** — chat handler 把 tenant_id 注入 factory;factory 把 tenant_id 注入 service;service 在每 query WHERE tenant_id 強制(55.1 已驗證)

---

## User Stories

### US-1: 4 Deferred Domains tools.py Mode Swap (closes AD-BusinessDomainPartialSwap-1)

**As** a Phase 55.2 implementer
**I want** patrol/correlation/rootcause/audit_domain 各自的 `tools.py` 接受 `mode='mock'|'service'` + `factory_provider` kwarg(機械式鏡射 55.1 incident pattern);每個 domain 加 `_build_service_handlers(factory_provider) -> dict[str, ToolHandler]` + `_serialize_*` helper(若 service 返回 ORM model)
**So that** 5 domain 統一介面;`BUSINESS_DOMAIN_MODE=service` 不會在 chat 主流量 crash;AD-BusinessDomainPartialSwap-1 closed

**Acceptance**:
- [ ] `patrol/tools.py` 加 `_build_service_handlers(factory_provider)` (4 handlers) + `register_patrol_tools(... mode='mock'|'service', factory_provider=None)` kwarg
- [ ] `correlation/tools.py` 同上 (3 handlers)
- [ ] `rootcause/tools.py` 同上 (3 handlers; rootcause_apply_fix 維持 ALWAYS_ASK + service 返回 "approval_pending" sentinel)
- [ ] `audit_domain/tools.py` 同上 (3 handlers)
- [ ] 每 domain `mode='service'` without `factory_provider` raise ValueError(防錯,鏡射 incident)
- [ ] 每 service handler 用 `factory_provider().get_*_service()` per-call(鏡射 incident; 無 module-level cache)
- [ ] mypy --strict 0 errors;6 V2 lints green
- [ ] 4 domain × ~3 service-mode handler tests = ~12 tests

### US-2: _register_all.py Uniform Mode Threading

**As** a Phase 55.2 implementer
**I want** `_register_all.py make_default_executor(... mode=, factory_provider=)` 把 kwargs 統一傳給所有 5 個 `register_*_tools()`(目前只傳給 incident);`register_all_business_tools()` 介面也一致接受
**So that** 上層 caller 設一次 mode, 5 domain 全部對齐;chat handler 不需個別調 5 次 register_*

**Acceptance**:
- [ ] `_register_all.py` 修改 `register_all_business_tools(... mode='mock', factory_provider=None)` 把 kwargs 傳給 5 個 register_*_tools
- [ ] `make_default_executor(... mode=None, factory_provider=None)` 讀 settings 預設 + override
- [ ] mode='service' without factory_provider raise ValueError 在 register_all 層(early)
- [ ] 4 V2 lints green(包含 check_cross_category_import)
- [ ] 2 unit tests (register_all mode='mock' / mode='service' factory threading)

### US-3: Chat Handler Production Wiring (BusinessServiceFactory DI)

**As** a Phase 55.2 implementer
**I want** `api/v1/chat/handler.py`(or relevant DI module)在 chat endpoint 處理時建立 per-request `BusinessServiceFactory(db, tenant_id, tracer)` 並把 `factory_provider` 傳給 `make_default_executor`;`BUSINESS_DOMAIN_MODE` 從 settings 讀
**So that** 主流量 chat → tool → business service → DB 全鏈打通;tracer 自動透過 factory 注入到 service 層;multi-tenant 隔離 enforced

**Acceptance**:
- [ ] chat handler 注入 `db_session: AsyncSession = Depends(get_db)` + `tenant_id: UUID = Depends(get_current_tenant)` + `tracer: Tracer = Depends(get_tracer)`
- [ ] 建 `factory = BusinessServiceFactory(db=db_session, tenant_id=tenant_id, tracer=tracer)`
- [ ] `factory_provider = lambda: factory`(per-request closure)傳給 `make_default_executor(mode=settings.BUSINESS_DOMAIN_MODE, factory_provider=factory_provider)`
- [ ] 預設行為 unchanged: `BUSINESS_DOMAIN_MODE=mock` (51.0/55.1 既有 test 0 regression)
- [ ] mode='service' 時 5 domain 全走 service path(覆蓋 chat → tool_executor → tools.py service handlers → BusinessServiceFactory → 各 service)
- [ ] 4 integration tests (mode='mock' regression / mode='service' patrol+correlation+rootcause+audit_domain / multi-tenant cross-tenant deny / tracer span emitted)

### US-4: Tests + Coverage Verification

**As** a Phase 55.2 implementer
**I want** 4 deferred domains' service-mode handler tests + chat handler integration tests(US-1 + US-3 中已 split 出);全 sprint test count baseline 1395 → ≥ 1410(+15 new)
**So that** AD-BusinessDomainPartialSwap-1 可被 test 證明 closed;production wiring 有迴歸防護

**Acceptance**:
- [ ] 4 domain × ~3 critical-path service-mode handler tests = ~12 tests
- [ ] 4 chat handler integration tests
- [ ] All tests via real DB(per testing.md AP-10)
- [ ] mypy --strict 0 errors;6 V2 lints green;LLM SDK leak 0
- [ ] BUSINESS_DOMAIN_MODE=mock 0 regression(完整 51.0+55.1 test suite green)
- [ ] BUSINESS_DOMAIN_MODE=service test suite green

### US-5: V2 22/22 Closure Ceremony + AD-Sprint-Plan-3 Validation

**As** a Phase 55.2 implementer
**I want** Day 4 完整 V2 closure ceremony — retrospective 6 必答 + Phase 49-55 全 sprint 總結 + Phase 56+ SaaS Stage 1 啟動條件 + AD-Sprint-Plan-3 multiplier 0.40 first-application calibration verify
**So that** V2 重構正式完成 22/22 (100%);SITUATION-V2 + CLAUDE.md + memory 全更新;Phase 56+ 規劃工作可由用戶 approve 啟動

**Acceptance**:
- [ ] retrospective.md 6 必答(Q1-Q6 per 53.2.5 樣板)
- [ ] retro Q2: actual hr / committed hr → ratio (期望 [0.85, 1.20]);5-sprint window mean re-evaluate;如 < 0.85 → AD-Sprint-Plan-4(0.40→0.30);如 ∈ [0.85, 1.20] → 鎖 0.40 為 stable for Phase 56+
- [ ] retro Q5 V2 closure summary: Phase 49-55 共 22 sprints + 2 carryover bundles + 11+1 範疇全 Level 4 + 5 business domain production-capable
- [ ] retro Q6 Phase 56+ readiness: SaaS Stage 1 啟動條件清單(multi-tenant DB / billing / SLA / DR — 已知 deferred)
- [ ] V2 22/22 milestone visualisation: SITUATION-V2 §9 milestones row + CLAUDE.md 高層 status 更新

---

## Technical Specifications

### Architecture: Mode Threading Through 4 Layers

```
┌─────────────────────────────────────────────────┐
│ Chat Handler (api/v1/chat/handler.py)           │  ← US-3 NEW wiring
│   - Depends(get_db, get_current_tenant, tracer) │
│   - factory = BusinessServiceFactory(...)        │
│   - executor = make_default_executor(            │
│       mode=settings.BUSINESS_DOMAIN_MODE,        │
│       factory_provider=lambda: factory           │
│     )                                            │
└──────────────────────────┬──────────────────────┘
                           ↓
┌─────────────────────────────────────────────────┐
│ _register_all.py make_default_executor          │  ← US-2 thread mode through
│   register_all_business_tools(                   │
│     ... mode=mode, factory_provider=...           │
│   )                                              │
└──────────────────────────┬──────────────────────┘
                           ↓
┌─────────────────────────────────────────────────┐
│ register_*_tools (5 domain)                     │  ← US-1 4 deferred domains
│   - mode='mock'  → mock_executor.method()       │  ← Phase 51.0 path
│   - mode='service' → factory_provider().get_*().method()  ← Phase 55.1+55.2 path
└──────────────────────────┬──────────────────────┘
                           ↓ (mode=service)
┌─────────────────────────────────────────────────┐
│ Service Class (5 domain)                        │  ← Phase 55.1 production
│   - tenant_id filter                             │
│   - business logic                               │
│   - business_service_span obs                    │
└──────────────────────────────────────────────────┘
```

### File Layout

```
backend/src/
├── business_domain/
│   ├── _register_all.py                       MODIFIED — uniform mode/factory threading
│   ├── patrol/tools.py                         MODIFIED — mode swap (US-1)
│   ├── correlation/tools.py                    MODIFIED — mode swap (US-1)
│   ├── rootcause/tools.py                      MODIFIED — mode swap (US-1)
│   └── audit_domain/tools.py                   MODIFIED — mode swap (US-1)
├── api/v1/chat/
│   └── handler.py                              MODIFIED — production wiring (US-3)
└── tests/
    ├── unit/business_domain/                   NEW — ~12 service-mode handler tests
    └── integration/api/                        NEW — ~4 chat business wiring tests
```

### Mode Swap Pattern (mirror 55.1 incident exactly)

每個 deferred domain 的 `tools.py` 加:

```python
# === imports (add) ===
from collections.abc import Callable
from business_domain._service_factory import BusinessServiceFactory


# === serialize helper (per ORM model returned) ===
def _serialize_<entity>(obj) -> dict[str, object]:
    """Convert service result → JSON-friendly dict (avoid leaking SQLAlchemy/dataclass state)."""
    return {...}


# === service handlers (rebuild from factory per call) ===
def _build_service_handlers(
    factory_provider: Callable[[], BusinessServiceFactory],
) -> dict[str, ToolHandler]:
    async def h_method1(call: ToolCall) -> str:
        svc = factory_provider().get_<domain>_service()
        result = await svc.method1(...)
        return json.dumps(_serialize_<entity>(result))
    # ... other handlers ...
    return {"mock_<domain>_method1": h_method1, ...}


# === entry function with mode kwarg ===
def register_<domain>_tools(
    registry: ToolRegistry,
    handlers: dict[str, ToolHandler],
    *,
    mock_url: str = DEFAULT_BASE_URL,
    mode: str = "mock",
    factory_provider: Callable[[], BusinessServiceFactory] | None = None,
) -> None:
    for spec in <DOMAIN>_SPECS:
        registry.register(spec)
    if mode == "mock":
        executor = <Domain>MockExecutor(base_url=mock_url)
        handlers.update(_build_handlers(executor))
    elif mode == "service":
        if factory_provider is None:
            raise ValueError(f"register_<domain>_tools(mode='service') requires factory_provider")
        handlers.update(_build_service_handlers(factory_provider))
    else:
        raise ValueError(f"register_<domain>_tools: invalid mode {mode!r}")
```

### Chat Handler Wiring Pattern

```python
# api/v1/chat/handler.py (excerpt)
from business_domain._service_factory import BusinessServiceFactory
from business_domain._register_all import make_default_executor
from core.config import settings


async def chat_endpoint(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
    tracer: Tracer = Depends(get_tracer),
) -> StreamingResponse:
    factory = BusinessServiceFactory(db=db, tenant_id=tenant_id, tracer=tracer)
    executor = make_default_executor(
        mode=settings.BUSINESS_DOMAIN_MODE,
        factory_provider=lambda: factory,
    )
    # ... rest of handler unchanged ...
```

---

## Acceptance Criteria

### Sprint-Wide

- [ ] V2 進度 21/22 → 22/22 (100%)
- [ ] All 6 V2 lints green
- [ ] mypy --strict 0 errors
- [ ] LLM SDK leak: 0
- [ ] Anti-pattern checklist 11 項對齐
- [ ] 5 active CI checks green (Backend CI / V2 Lint / E2E Backend / E2E Summary / Frontend E2E chromium)
- [ ] Test count baseline 1395 → ≥ 1410 (≥ +15 new = ~12 service-mode handler + ~4 chat wiring + obs assertions)
- [ ] AD-BusinessDomainPartialSwap-1 closed
- [ ] AD-Sprint-Plan-3 first application captured + verdict logged

### Per-User-Story

詳見 §User Stories acceptance per US.

---

## Day-by-Day Plan

### Day 0 — Setup + Day-0 探勘 + Pre-flight Verify (~1 hr)

- 0.1 Branch + plan + checklist commit
- 0.2 Day-0 探勘 — grep against repo state (verify 4 deferred domain tools.py current shape / chat handler current wiring / settings.BUSINESS_DOMAIN_MODE present from 55.1 / BusinessServiceFactory builders all present)
- 0.3 Calibration multiplier pre-read (55.1 ratio 0.68; 4-sprint mean 0.76; lower 0.50→0.40 first application this sprint per AD-Sprint-Plan-3)
- 0.4 Pre-flight verify (pytest baseline 1395 / 6 V2 lints baseline / mypy baseline)
- 0.5 Day 0 progress.md commit + push

### Day 1 — US-1 patrol + correlation tools.py Mode Swap (~2 hr commit)

- 1.1 patrol/tools.py: imports + `_serialize_*` (if needed) + `_build_service_handlers(factory_provider)` (4 handlers) + register_patrol_tools mode kwarg
- 1.2 correlation/tools.py: 同上 (3 handlers)
- 1.3 6 unit tests (patrol 3 + correlation 3 critical paths)
- 1.4 mypy + 6 V2 lints green
- 1.5 Day 1 progress.md + commit + push

### Day 2 — US-1 rootcause + audit_domain tools.py Mode Swap (~2 hr commit)

- 2.1 rootcause/tools.py: 同 Day 1 pattern (3 handlers; apply_fix 維持 ALWAYS_ASK + return "approval_pending" sentinel)
- 2.2 audit_domain/tools.py: 同上 (3 handlers)
- 2.3 6 unit tests (rootcause 3 + audit_domain 3)
- 2.4 mypy + 6 V2 lints green
- 2.5 Day 2 progress.md + commit + push

### Day 3 — US-2 + US-3 (_register_all uniform threading + chat handler wiring) (~2 hr commit)

- 3.1 `_register_all.py`: uniform mode/factory_provider threading to all 5 register_*_tools
- 3.2 2 unit tests (register_all mode='mock' / mode='service' factory threading)
- 3.3 `api/v1/chat/handler.py`: BusinessServiceFactory DI injection + factory_provider lambda + make_default_executor mode flag
- 3.4 4 integration tests (chat business wiring: mock regression / service path / multi-tenant / tracer span)
- 3.5 mypy + 6 V2 lints green
- 3.6 Day 3 progress.md + commit + push

### Day 4 — US-5 V2 22/22 Closure Ceremony + Retro + Closeout (~1.5 hr commit)

- 4.1 Final pytest + 6 V2 lints + LLM SDK leak final verify
- 4.2 Multi-tenant integration test cross-domain (5 domains, 2 tenants)
- 4.3 Main flow e2e test (chat → 5 domain calls → all service-backed)
- 4.4 retrospective.md (6 必答 + V2 closure summary + AD-Sprint-Plan-3 first-application calibration verify + 5-sprint window mean recalc + Phase 56+ readiness)
- 4.5 Open PR → CI green → solo-dev merge to main
- 4.6 Closeout PR (SITUATION-V2 + CLAUDE.md update to V2 22/22 (100%))
- 4.7 Memory snapshot: project_phase55_2_v2_closure.md + project_v2_closure_summary.md (Phase 49-55 grand summary)
- 4.8 Final push + delete merged branches + verify main HEAD

---

## File Change List

| File | Status | Lines (est) |
|------|--------|-------------|
| `business_domain/patrol/tools.py` | MODIFIED | +60 |
| `business_domain/correlation/tools.py` | MODIFIED | +50 |
| `business_domain/rootcause/tools.py` | MODIFIED | +50 |
| `business_domain/audit_domain/tools.py` | MODIFIED | +50 |
| `business_domain/_register_all.py` | MODIFIED | +30 |
| `api/v1/chat/handler.py` | MODIFIED | ~30 |
| Tests (~16 new) | NEW | ~250 |
| `docs/agent-harness-execution/phase-55/sprint-55-2/{progress,retrospective}.md` | NEW | ~500 |
| `memory/project_phase55_2_v2_closure.md` | NEW | ~50 |
| `memory/project_v2_closure_summary.md` | NEW | ~80 |

**Total**: ~270 source LOC + ~250 test LOC + ~630 docs LOC

---

## Dependencies & Risks

### Dependencies (must exist before code starts)

- ✅ Phase 55.1 BusinessServiceFactory + 5 service classes — verified Day 0
- ✅ Phase 55.1 incident mode swap pattern — reference implementation
- ✅ Phase 55.1 BUSINESS_DOMAIN_MODE flag in settings — verified Day 0
- ✅ Phase 55.1 business_service_span obs ctx mgr — verified Day 0
- ⚠️ Chat handler current DI structure (db / tenant / tracer Depends) — Day 0 探勘 confirm shape
- ⚠️ get_tracer Depends factory exists — Day 0 探勘 verify

### Risk Classes (per sprint-workflow.md §Common Risk Classes)

**Risk Class A (paths-filter vs required_status_checks)**: backend-only sprint → backend-ci will fire (paths include `backend/**`). Frontend E2E required check → must touch `.github/workflows/playwright-e2e.yml` header per AD-CI-5 workaround. Mitigation: Day 4 closeout commit touches workflow header.

**Risk Class B (cross-platform mypy unused-ignore)**: low risk; no new optional dependencies introduced. Mitigation: standard `# type: ignore[X, unused-ignore]` if encountered.

**Risk Class C (module-level singleton across event loops)**: LOW RELEVANCE — BusinessServiceFactory is per-request (no module-level cache); 55.1 已驗證 conftest.py reset_service_factory autouse fixture pattern works. Mitigation: 重用 55.1 fixture pattern;新 chat integration tests 加 autouse fixture if needed.

### Sprint-specific Risks

| Risk | Mitigation |
|------|-----------|
| 4 deferred domain service handlers serialize 邏輯不一致 | Mirror 55.1 incident `_serialize_incident` pattern;每 service method 確認 return type |
| Chat handler DI 結構與 55.1 假設不一致 | Day 0 grep 探勘確認 current Depends 結構;若 db/tenant/tracer 已存在 Depends, 直接 reuse;若 missing 加 |
| AD-Sprint-Plan-3 first application multiplier 0.40 過於激進 | 已參考 55.1 ratio 0.68(0.50 仍 too generous);0.40 從 4-sprint mean 0.76 推算合理;若 < 0.40 → AD-Sprint-Plan-4 |
| rootcause_apply_fix HIGH-RISK service path 未 production | 55.1 已 deferred;55.2 service handler 返回 "approval_pending" sentinel(同 mock_executor 行為);實際 production logic → Phase 56+ |
| audit_domain query_logs 跨 53.4 audit_log table 介面變動 | Day 0 verify audit_log table schema 不變;若有變動,記入 risks 不在 sprint scope |

---

## Workload

> **Bottom-up est ~17 hr → calibrated commit ~7 hr (multiplier 0.40)**
> **4-sprint window ratio mean 0.76 BELOW [0.85, 1.20] band** → multiplier reduction 0.50 → 0.40 first application this sprint per 55.1 retrospective Q2 + AD-Sprint-Plan-3

| US | Bottom-up (hr) |
|----|---------------|
| US-1 4 deferred domains tools.py mode swap | 5 |
| US-2 _register_all.py uniform mode threading | 1 |
| US-3 Chat handler production wiring | 4 |
| US-4 Tests + coverage verification | 3 |
| US-5 V2 22/22 closure ceremony + retro + closeout | 4 |
| **Total bottom-up** | **17** |
| **× 0.40 calibrated** | **6.8 ≈ 7** |

Day 4 retrospective Q2 must verify: `actual_total_hr / 7 → ratio` compared to [0.85, 1.20] band; document delta + 5-sprint window recalc + AD-Sprint-Plan-4 if needed.

---

## Out of Scope

- ❌ Real enterprise integrations (PagerDuty / Opsgenie / ServiceNow / D365 / SAP) — Phase 56+ canary / SaaS Stage 1
- ❌ patrol/correlation/rootcause/audit_domain DB schema (only incident has table from 55.1; others stay seeded) — Phase 56+
- ❌ rootcause_apply_fix HIGH-RISK production logic — already requires HITL ALWAYS_ASK; service stub returns "approval_pending"
- ❌ Frontend pages for business domain management — Phase 56+
- ❌ SaaS Stage 1 multi-tenant infrastructure (billing / SLA / DR) — Phase 56-58
- ❌ V2 → V3 migration plan — post-V2 closure decision (not Phase 55.2)
- ❌ Refactor any 5 domain ToolSpec — sealed in 51.1 / 53.3+
- ❌ V1 archive cleanup or further deprecation — sealed at Sprint 49.1

---

## AD Carryover Sub-Scope

### AD-BusinessDomainPartialSwap-1 (4 deferred domains full mode swap)

**Source**: Sprint 55.1 D9 deferral (incident-only mode swap due to time management; 4 domains' tools.py never received mode kwarg)

**Closure plan**:
1. Sprint 55.2 US-1 mirrors 55.1 incident pattern to all 4 domains
2. 13 service handlers (4 patrol + 3 correlation + 3 rootcause + 3 audit_domain) implemented
3. Each domain raises ValueError if mode='service' without factory_provider (defensive)
4. Day 2 closeout: all 4 domains pass `register_*_tools(mode='service', factory_provider=...)` smoke test
5. AD-BusinessDomainPartialSwap-1 closed in retrospective.md Q4

### AD-Sprint-Plan-3 (calibration multiplier reduction 0.50 → 0.40)

**Source**: Sprint 55.1 retrospective Q2 (4-sprint mean 0.76 BELOW band; recommended 0.50 → 0.40)

**Closure plan**:
1. Sprint 55.2 plan §Workload uses **0.40** (first application)
2. Day 4 retrospective Q2 computes `actual / 7`
3. If ratio ∈ [0.85, 1.20] → close AD-Sprint-Plan-3 ✅; rule 0.40 = stable for Phase 56+
4. If ratio < 0.85 → log AD-Sprint-Plan-4 (next reduction 0.40 → 0.30)
5. If ratio > 1.20 → log AD-Sprint-Plan-4 (reverse: 0.40 → 0.55+)

---

## Definition of Done

- [ ] All 5 USs acceptance criteria met
- [ ] Test count ≥ 1410 (1395 + 15 new)
- [ ] mypy --strict 0 errors
- [ ] 6 V2 lints green
- [ ] LLM SDK leak: 0
- [ ] BUSINESS_DOMAIN_MODE=mock 0 regression (51.0 + 51.1 + 55.1 tests pass)
- [ ] BUSINESS_DOMAIN_MODE=service 5 domains × all methods 主流量 e2e green
- [ ] AD-BusinessDomainPartialSwap-1 closed in retrospective.md Q4
- [ ] AD-Sprint-Plan-3 closure or escalation logged in retrospective.md Q2
- [ ] PR opened, CI green (5 active checks), merged to main
- [ ] Closeout PR merged
- [ ] SITUATION-V2 + memory + CLAUDE.md updated to **V2 22/22 (100%)**
- [ ] Phase 56+ SaaS Stage 1 readiness checklist documented in retrospective Q6
- [ ] V2 closure summary memory: project_v2_closure_summary.md (Phase 49-55 grand summary)

---

## References

- 06-phase-roadmap.md §Phase 55.2 (production deployment)
- 08b-business-tools-spec.md §Domain 1-5 (5 domains × 18 tool spec)
- 10-server-side-philosophy.md §原則 1 Server-Side First + §multi-tenant
- 14-security-deep-dive.md §multi-tenant tenant_id propagation through DI chain
- 17-cross-category-interfaces.md §Contract 12 Tracer (used by Cat 12 obs)
- .claude/rules/multi-tenant-data.md (3 鐵律 + DI tenant propagation)
- .claude/rules/observability-instrumentation.md (5 必埋點 + ctx mgr pattern)
- .claude/rules/testing.md §Module-level Singleton Reset Pattern (53.6+55.1 ServiceFactory)
- .claude/rules/sprint-workflow.md §Common Risk Classes (3 classes A/B/C)
- Sprint 55.1 plan + retrospective (multiplier 0.50 → 0.40 reasoning + incident mode swap pattern reference)
- Sprint 51.0/51.1 mock skeleton + Sprint 55.1 service skeleton (existing 5 domain × 18 tool implementation)
