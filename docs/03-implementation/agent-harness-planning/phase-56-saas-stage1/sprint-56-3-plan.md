# Sprint 56.3 — Phase 56+ SaaS Stage 1 3rd of 3: SLA Monitor + Cost Ledger 聯合

> **Sprint Type**: Phase 56+ third sprint — SaaS Stage 1 final backend sprint;closes Phase 56-58 Stage 1 main delivery (3/3) — joint scope SLA Monitor + Cost Ledger
> **Owner Categories**: Cat 12 Observability (SLAMonitor metric collection from real Tracer) / §Multi-tenant rule (per-tenant SLA + cost ledger isolation) / §Billing (Cost Ledger DB schema + auto-record hooks + aggregation)
> **Phase**: 56 (SaaS Stage 1 — 3/3 sprint of Phase 56-58 SaaS Stage 1)
> **Workload**: 5 days (Day 0-4); bottom-up est ~24 hr → calibrated commit **~13 hr** (multiplier **0.55** per AD-Sprint-Plan-4 scope-class matrix `large multi-domain` band 0.50-0.55, picking 0.55 mid-band — 2nd application after 56.1 ratio 1.00 ✅)
> **Branch**: `feature/sprint-56-3-sla-monitor-cost-ledger`
> **Plan Authority**: This document (per CLAUDE.md §Sprint Execution Workflow)
> **Roadmap Source**: 15-saas-readiness.md §SLA 與監控 + §Billing - Cost Ledger 整合 + Sprint 56.2 retrospective Q5 (Phase 56.3 candidate scope `large multi-domain` joint sprint user-approved 2026-05-06)
> **AD logging (sub-scope)**: AD-Sprint-Plan-4 scope-class matrix `large multi-domain` 2nd application (56.1 was 1st data point ratio 1.00 ✅);AD-Plan-4-Schema-Grep evaluation 2nd data point per 1-sprint evidence rule (56.2 retro Q3 deferred to this sprint)

---

## Sprint Goal

Close **Phase 56-58 SaaS Stage 1 backend stack** by delivering the two remaining business-value modules that depend on 56.2 polish bundle:

- **US-1**: SLA Metric Recorder — `platform_layer/observability/sla_monitor.py` `SLAMetricRecorder` class consuming Cat 12 Tracer span events (now real after 56.2 AD-Cat12-BusinessObs);computes per-tenant uptime / API p99 latency / loop latency (3 categories: 簡單 / 中等 / 複雜) / HITL queue notification latency;Redis-backed sliding window counters for real-time + Postgres `sla_metrics` table for monthly aggregation
- **US-2**: SLA Monthly Report Generator + DB schema — `sla_violations` + `sla_reports` tables (Alembic 0014);`generate_monthly_report(tenant_id, month) -> SLAReport` method;monthly cron stub (Phase 56.x runs);includes 4 SLA category breakdown per tenant tier (Standard 99.5% / Enterprise 99.9%);per-tenant violation alert hook (stub for Phase 57+ notification)
- **US-3**: Cost Ledger DB schema + ORM + LLM pricing config — `cost_ledger` table (Alembic 0014 same migration as US-2);`CostLedger` ORM + `CostLedgerService` with `record(tenant_id, cost_type, sub_type, quantity, unit, unit_cost_usd, total_cost_usd, session_id)` + `aggregate(tenant_id, month) -> AggregatedUsage`;`config/llm_pricing.yml` per-provider/per-model pricing
- **US-4**: Cost Ledger auto-record hooks — Chat router `_stream_loop_events` LLMResponded hook → `cost_ledger.record(cost_type="llm", quantity=actual_tokens, ...)` reusing 56.2 AD-QuotaPostCall-1 actual_tokens;Tool executor `tool_dispatcher` post-execution hook → `cost_ledger.record(cost_type="tool", sub_type=tool_name, quantity=1, unit="call")`;Both per-tenant scoped per multi-tenant rule
- **US-5**: Sprint 56.3 Closeout — Cross-AD e2e integration test (provision tenant via 53.4 RBAC + chat with quota reconcile from 56.2 + SLA span recording from US-1 + Cost Ledger entry from US-4 visible end-to-end);retrospective + AD-Sprint-Plan-4 `large multi-domain` 2nd application calibration verify (56.1 ratio 1.00 baseline);AD-Plan-4-Schema-Grep formal evaluation per 2nd data point evidence rule

Sprint 結束後:
- (a) **Phase 56-58 SaaS Stage 1 main backend stack 3/3 ✅** — provision (56.1) + polish (56.2) + monitor & ledger (56.3) 完整;Stage 2 commercial SaaS billing run / Stripe / public API / DR cross-region 等屬 Phase 57+ scope
- (b) **SLA monitoring 主流量 functional** — per-tenant uptime / latency / HITL queue notification metrics 透過 Cat 12 spans 即時計算;monthly report 可 generate(stub cron;Phase 56.x 真實 schedule)
- (c) **Cost Ledger 主流量 functional** — 每次 LLM call + tool call 自動 record;per-tenant aggregation method 為 Stage 2 billing run 預留 (Stripe / 月結 invoice 屬 Stage 2)
- (d) **AD-Sprint-Plan-4 `large multi-domain` 2-data-point baseline** — 56.1 ratio 1.00 + 56.3 ratio (this sprint) 形成 large multi-domain class window;若 ratio ∈ band → mean 計算 → mid-band 鎖定;若 outside → AD-Sprint-Plan-7 logged
- (e) **AD-Plan-4-Schema-Grep evaluation conclusive** — 2-sprint evidence(56.1 D26+D27 + 56.3 Day 0 column-level drift?)足以 promote OR drop;此 sprint retro Q3 寫 verdict

**主流量驗收標準**:
- POST chat → LLM completes → SLA span recorded with latency category (簡單 / 中等 / 複雜) → SLAMetricRecorder updates Redis sliding window
- POST chat → LLM completes → Cost Ledger record entry visible in `cost_ledger` table with tenant_id + actual tokens (從 56.2 AD-QuotaPostCall-1 LoopCompleted total_tokens) + computed total_cost_usd
- Tool execution → Cost Ledger record entry with cost_type="tool" + sub_type=tool_name
- `GET /api/v1/admin/tenants/{id}/sla-report?month=YYYY-MM` (stub endpoint) → returns SLAReport JSON with 4 metric categories + violation count
- `GET /api/v1/admin/tenants/{id}/cost-summary?month=YYYY-MM` (stub endpoint) → returns AggregatedUsage JSON with LLM tokens + tool calls breakdown
- pytest baseline 1530 → ≥ 1555 (≥ +25 new)
- mypy --strict 0 errors on `platform_layer/observability/sla_monitor.py`, `platform_layer/billing/`, `infrastructure/db/models/sla_*.py`, `infrastructure/db/models/cost_ledger.py`, `api/v1/admin/sla_reports.py`, `api/v1/admin/cost_summary.py`
- 8 V2 lints green (含 56.1 check_rls_policies — 新表 sla_violations / sla_reports / cost_ledger 必含 RLS policy)
- LLM SDK leak: 0 (LLM pricing 從 yaml config 讀,不 import provider SDK)

---

## Background

### V2 進度

- **22/22 sprints (100%) main progress completed** + **Phase 56-58 SaaS Stage 1 2/3** (Sprint 56.2 closed 2026-05-06)
- main HEAD: `6236c098` (Sprint 56.2 closeout PR #100)
- pytest baseline 1530 / mypy --strict 0/284 source files / 8 V2 lints 8/8 green
- 56.2 calibration `mixed` 0.60 mid-band 2nd application ratio **1.17 ✅** in band — `mixed` 2-data-point mean 1.09 (KEEP 0.60 per AD-Sprint-Plan-4)
- 10-sprint window 6/10 in-band (53.7=1.01 / 55.2=1.10 / 55.5=1.14 / 55.6=0.92 / 56.1=1.00 / 56.2=1.17) — first crossing 60% threshold
- **本 sprint = Phase 56+ SaaS Stage 1 第 3 個 sprint** (3/3 of Phase 56-58 SaaS Stage 1 main backend stack)

### 為什麼 56.3 是 SLA Monitor + Cost Ledger 聯合

User approved 2026-05-06 session Option A(`large multi-domain` joint sprint — SaaS Stage 1 收尾):

1. **56.2 已解阻 SLA Monitor 前置依賴** — AD-Cat12-BusinessObs closed → 5 business services + chat handler 全鏈路真 Tracer spans available;SLAMetricRecorder 可 attach 為 span observer
2. **56.2 已解阻 Cost Ledger 前置依賴** — AD-QuotaEstimation-1 + AD-QuotaPostCall-1 closed → 精確 input + actual tokens 可從 LoopCompleted.total_tokens 取(56.2 events.py field);Cost Ledger 可基於精確 token usage 計算 cost
3. **聯合 sprint 共用 obs + DB infrastructure** — SLA + Cost 兩 module 共用 Cat 12 spans observer + Alembic 0014 single migration + 同 chat router hook point;split 成兩 sprint 會多 ~3 hr ceremony overhead
4. **`large multi-domain` 2nd application** — 56.1 ratio 1.00 ✅ 為 1st data point;56.3 為 2nd;mean 將從 1-data-point 升到 2-data-point 較穩固;若 ratio ∈ band → AD-Sprint-Plan-4 large multi-domain mid-band 鎖定 0.55
5. **AD-Plan-4-Schema-Grep 2nd evidence** — 56.1 D26+D27 column-level drift caught at first test run;56.2 Day 0 探勘無 column drift(1-sprint evidence);此 sprint 為 2nd application 含新表(sla_violations / sla_reports / cost_ledger),Day 0 兩-prong 探勘足以 evaluate Schema-Grep promotion candidate
6. **Phase 56-58 Stage 1 closure** — 56.3 完成 SaaS Stage 1 backend stack;Phase 57+ 候選 = Citus PoC + DR + Compliance + Frontend Onboarding Wizard + Stripe / 月結;此 sprint 不 attempt Stage 2 scope

### 既有結構(Day 0 探勘 grep 將驗證以下假設)

⚠️ **以下 layout 是 plan-time 推斷;Day 0 grep 將 confirm 或 catalogue 為 D-finding**:

```
backend/src/
├── platform_layer/
│   ├── observability/
│   │   ├── tracer.py                          # ✅ 56.2 AD-Cat12-BusinessObs (get_tracer factory)
│   │   ├── helpers.py                         # ✅ 55.3 AD-Cat12-Helpers-1 (category_span)
│   │   └── sla_monitor.py                     # ❌ NEW (US-1: SLAMetricRecorder + 4 metrics)
│   ├── billing/                               # ❌ NEW directory
│   │   ├── __init__.py                        # ❌ NEW
│   │   ├── cost_ledger.py                     # ❌ NEW (US-3: CostLedgerService)
│   │   └── pricing.py                         # ❌ NEW (US-3: PricingLoader from yaml)
│   └── tenant/
│       └── quota.py                           # ✅ 56.1 + 56.2 (LoopCompleted total_tokens reconcile)
├── infrastructure/db/
│   ├── models/
│   │   ├── sla.py                             # ❌ NEW (US-2: SLAViolation + SLAReport ORM)
│   │   └── cost_ledger.py                     # ❌ NEW (US-3: CostLedger ORM)
│   └── migrations/versions/
│       └── 0014_sla_and_cost_ledger.py        # ❌ NEW (US-2 + US-3 single Alembic migration)
├── config/
│   └── llm_pricing.yml                        # ❌ NEW (US-3: per-provider/model pricing)
├── agent_harness/_contracts/events.py         # ✅ 56.2 LoopCompleted.total_tokens field exists
├── api/v1/
│   ├── admin/
│   │   ├── sla_reports.py                     # ❌ NEW (US-2: GET sla-report endpoint)
│   │   └── cost_summary.py                    # ❌ NEW (US-3: GET cost-summary endpoint)
│   └── chat/
│       └── router.py                          # ⚠️ MODIFY (US-1 + US-4: SLA span observer + Cost Ledger LLMResponded hook)
└── agent_harness/orchestrator_loop/
    └── tool_dispatcher.py                     # ⚠️ MODIFY (US-4: post-tool-exec Cost Ledger hook)
```

### Sprint 56.2 retrospective Q5 對齐確認

Sprint 56.2 retrospective Q5 列出 Phase 56.3 candidate scope:
- SLA Monitor (medium-backend ~12-15 hr) ✅ 此 sprint US-1 + US-2 (joint with Cost Ledger reduces overhead)
- Cost Ledger (medium-backend ~10-13 hr) ✅ 此 sprint US-3 + US-4 (joint with SLA Monitor)
- Citus PoC (large research, standalone worktree ~9-12 hr) ⛔ 不入 main sprint;defer Phase 57+
- Compliance partial GDPR (medium-backend ~10-13 hr) ⛔ defer Phase 57+
- Recommendation: Joint sprint as `large multi-domain` 0.55 mid-band → ~13 hr commit ✅ this sprint exact match
- AD-Plan-4-Schema-Grep 2nd evidence ✅ 此 sprint Day 0 探勘 2nd data point + retro Q3 verdict

### V2 紀律 9 項對齐確認

1. **Server-Side First** ✅ 全 server-side;SLA Redis sliding window + Postgres aggregation / Cost Ledger DB-backed / pricing yaml server-side config
2. **LLM Provider Neutrality** ✅ Pricing 從 yaml config 讀;不 import openai / anthropic SDK;Cat 12 Tracer 透過 ABC;LLMResponded event 用 56.2 LoopCompleted.total_tokens (中性 events.py)
3. **CC Reference 不照搬** ✅ SLA + Cost Ledger 全 server-side enterprise pattern;不抄 CC tracing 模型(CC is local);Cat 12 用 OpenTelemetry SDK
4. **17.md Single-source** ✅ Tracer ABC + LoopEvent + ToolExecuted event 已 17.md single-source;此 sprint 是 attach observer + record DB,不重新定義 ABC;新表 ORM + DB schema in 17.md §Contract n/a (DB schema 不在 17.md scope per architecture)
5. **11+1 範疇歸屬** ✅ US-1 = 範疇 12 / US-2+US-3+US-4 = §Billing(新平台 module 不在 11 範疇,屬 platform_layer);Cost Ledger 範疇歸屬 = `platform_layer/billing/`;每檔案明確歸屬;無 AP-3
6. **04 anti-patterns** ✅ AP-3 範疇歸屬合規 / AP-4(Potemkin)— SLA + Cost 全有實際 wire-up + 主流量 e2e 測試 / AP-6(Hybrid Bridge Debt)— 不為 Stage 2 commercial SaaS 預寫 Stripe abstraction;billing run 是 Stage 2 / AP-9(Verification)— 主流量 verification 仍走;新 hooks 不 break verifier loop
7. **Sprint workflow** ✅ plan → checklist → Day 0 探勘 → code → progress → retro;本文件依 56.1 plan 結構鏡射(13 sections / 5 days Day 0-4)
8. **File header convention** ✅ 所有 new 檔案含 file header docstring;modify 檔案加 Modification History entry per `.claude/rules/file-header-convention.md`;MHist 1-line max per AD-Lint-3
9. **Multi-tenant rule** ✅ 3 鐵律全套用:`sla_violations` / `sla_reports` / `cost_ledger` 表全含 `tenant_id NOT NULL` + RLS policy + API endpoint via `Depends(get_admin_user)`;query 全 by tenant_id 過濾;check_rls_policies lint 必過

---

## User Stories

### US-1: SLA Metric Recorder — Cat 12 Span Observer

**As** a SaaS platform operator
**I want** an SLAMetricRecorder consuming real Cat 12 Tracer spans (post-56.2 AD-Cat12-BusinessObs) to compute per-tenant uptime / API p99 latency / loop latency (3 categories) / HITL queue notification latency in real-time (Redis sliding window) so that SLA violations are detectable within the SLA evaluation window
**So that** I can verify Standard 99.5% / Enterprise 99.9% commitment per 15-saas-readiness.md §SLA 承諾

**Acceptance**:
- `platform_layer/observability/sla_monitor.py` `SLAMetricRecorder` class
- Methods: `record_api_request(tenant_id, latency_ms, status_code)`, `record_loop_completion(tenant_id, latency_ms, complexity_category)`, `record_hitl_queue_notification(tenant_id, queue_to_notify_ms)`, `record_outage_window(tenant_id, start_ts, end_ts)`
- Redis sliding window: per-tenant key `sla:metrics:{tenant_id}:{metric}:{window}` with 5-min / 1-hour / 24-hour TTL
- Cat 12 span observer hook in chat router → `record_loop_completion` from existing chat_handler span timing
- Loop complexity categorization: ≤ 3 turns + ≤ 2 tool_calls + 0 subagent + < 4K input tokens = 簡單;4-10 turns + 多工具 + 0-1 subagent = 中等;10+ turns 或多 subagent = 複雜
- 5 unit tests + 1 integration test (real Redis fakeredis)

### US-2: SLA Monthly Report Generator + DB Schema

**As** a tenant admin
**I want** an HTTP endpoint returning per-month SLA report with 4 metric categories breakdown + violation count per tier
**So that** I can verify whether my tenant met Standard 99.5% / Enterprise 99.9% commitment for billing transparency

**Acceptance**:
- `infrastructure/db/models/sla.py`:
  - `SLAViolation` ORM(id / tenant_id / metric_type / threshold_pct / actual_pct / detected_at / resolved_at / severity)
  - `SLAReport` ORM(id / tenant_id / month / availability_pct / api_p99_ms / loop_simple_p99_ms / loop_medium_p99_ms / loop_complex_p99_ms / hitl_queue_notif_p99_ms / violations_count / generated_at)
- Alembic 0014_sla_and_cost_ledger.py migration含 RLS policy + indexes
- `SLAReportGenerator.generate_monthly_report(tenant_id, month) -> SLAReport`(query Redis sliding window 過去 30 天 + Postgres aggregation)
- `GET /api/v1/admin/tenants/{tenant_id}/sla-report?month=YYYY-MM` endpoint(stub return cached SLAReport row;若無 → 即時 generate)
- Monthly cron stub(Phase 56.x 真實 schedule;此 sprint 只 stub `monthly_sla_report_run.py` script + register in scripts/cron/)
- 4 unit tests + 2 integration tests

### US-3: Cost Ledger DB Schema + ORM + LLM Pricing Config

**As** a SaaS platform operator
**I want** a per-tenant cost_ledger table tracking every LLM call + tool call cost with config-driven pricing
**So that** Stage 2 billing run can aggregate per-month invoice and quota over-charge detection works

**Acceptance**:
- `infrastructure/db/models/cost_ledger.py`:
  - `CostLedger` ORM(id / tenant_id / cost_type [llm/tool/storage] / sub_type [provider_model_input or tool_name] / quantity / unit / unit_cost_usd / total_cost_usd / session_id / recorded_at)
- Alembic 0014 same migration as US-2(combine SLA + Cost Ledger 一個 migration head)
- `platform_layer/billing/cost_ledger.py` `CostLedgerService` with `record(...)` + `aggregate(tenant_id, month) -> AggregatedUsage`
- `platform_layer/billing/pricing.py` `PricingLoader` from `config/llm_pricing.yml` per-provider/per-model `input_per_million` + `output_per_million` + `cached_input_per_million`
- `config/llm_pricing.yml` initial entries: azure_openai/gpt-4o-mini + azure_openai/gpt-5.4 + anthropic/claude-3.7-sonnet stub
- `GET /api/v1/admin/tenants/{tenant_id}/cost-summary?month=YYYY-MM` endpoint
- 5 unit tests + 1 integration test

### US-4: Cost Ledger Auto-Record Hooks

**As** a SaaS platform operator
**I want** every LLM call + tool call automatically record a CostLedger entry without any explicit code path in chat router
**So that** cost tracking has 100% coverage and billing run can trust the ledger as source-of-truth

**Acceptance**:
- Chat router `_stream_loop_events` LoopCompleted observer extension:已有 56.2 quota_enforcer.record_usage hook;新增 cost_ledger.record(cost_type="llm", sub_type=f"{provider}_{model}_input/output", quantity=actual_input_tokens / actual_output_tokens, ...)
- `agent_harness/orchestrator_loop/tool_dispatcher.py` post-tool-exec hook:每次 tool execute 後 emit ToolExecuted event;chat router observer接 event → cost_ledger.record(cost_type="tool", sub_type=tool_name, quantity=1, unit="call", unit_cost_usd=0.0001 (default tool cost from pricing.yml), ...)
- Per-tenant scoped:cost_ledger.record 永遠帶 tenant_id;multi-tenant rule 鐵律 1+2+3 全套用
- LLM call cost split:input + output 各記一筆(2 ledger entries per LLM call);若 cached input → cached_input_per_million pricing
- 5 unit tests + 1 integration test

### US-5: Sprint 56.3 Closeout Ceremony

**As** the V2 sprint executor
**I want** end-to-end cross-AD integration test + retrospective + AD-Sprint-Plan-4 large multi-domain 2nd application calibration verify + AD-Plan-4-Schema-Grep formal evaluation
**So that** Sprint 56.3 closes Phase 56-58 SaaS Stage 1 main backend stack with full audit trail

**Acceptance**:
- Cross-AD e2e integration test `test_phase56_3_e2e.py`:provision tenant via 53.4 RBAC → onboard → POST chat with 56.2 quota reconcile → SLA span recorded by US-1 SLAMetricRecorder → Cost Ledger entry (LLM input + output 2 entries + 0-1 tool entry) recorded by US-4
- retrospective.md(6 必答 + AD-Sprint-Plan-4 large multi-domain 2nd app calibration verify + AD-Plan-4-Schema-Grep verdict + AD-Sprint-Plan-7 if calibration outside band)
- Memory snapshot `memory/project_phase56_3_sla_monitor_cost_ledger.md`
- SITUATION-V2 §9 + CLAUDE.md sync to **Phase 56-58 SaaS Stage 1 3/3 (Sprint 56.3 closed)**

---

## Technical Specifications

### Cat 12 SLA Span Observer Pattern

```python
# platform_layer/observability/sla_monitor.py
class SLAMetricRecorder:
    def __init__(self, redis: Redis, db: AsyncSession):
        self.redis = redis
        self.db = db

    async def record_loop_completion(
        self,
        tenant_id: UUID,
        latency_ms: int,
        complexity_category: Literal["simple", "medium", "complex"],
    ) -> None:
        # 5-min sliding window key
        key = f"sla:metrics:{tenant_id}:loop_{complexity_category}:5m"
        await self.redis.zadd(key, {f"{time.time()}:{uuid4()}": latency_ms})
        await self.redis.zremrangebyscore(key, 0, time.time() - 300)  # 5 min window
        await self.redis.expire(key, 600)  # 10 min TTL

    async def get_loop_p99(
        self,
        tenant_id: UUID,
        complexity_category: str,
        window_sec: int = 300,
    ) -> float | None:
        key = f"sla:metrics:{tenant_id}:loop_{complexity_category}:5m"
        all_values = await self.redis.zrange(key, 0, -1, withscores=True)
        if not all_values:
            return None
        latencies = sorted([score for _, score in all_values])
        p99_idx = int(len(latencies) * 0.99)
        return latencies[p99_idx]
```

### Cat 12 Tracer Span Observer Hook (chat router)

```python
# api/v1/chat/router.py (modify)
async def _stream_loop_events(...):
    sla_recorder: SLAMetricRecorder = Depends(get_sla_recorder)
    cost_ledger: CostLedgerService = Depends(get_cost_ledger)
    chat_start_time = time.monotonic()

    async for event in loop.run(...):
        if isinstance(event, LoopCompleted):
            elapsed_ms = int((time.monotonic() - chat_start_time) * 1000)
            complexity = _classify_loop_complexity(event)  # 簡單/中等/複雜
            # SLA recording (US-1)
            await sla_recorder.record_loop_completion(
                tenant_id=tenant_id,
                latency_ms=elapsed_ms,
                complexity_category=complexity,
            )
            # 56.2 quota reconcile (existing)
            await quota_enforcer.record_usage(...)
            # Cost Ledger recording (US-4 — LLM input + output 2 entries)
            await cost_ledger.record_llm_call(
                tenant_id=tenant_id,
                provider=event.provider,
                model=event.model,
                input_tokens=event.input_tokens,
                output_tokens=event.output_tokens,
                cached_input_tokens=event.cached_input_tokens,
                session_id=session_id,
            )
        yield event
```

### Cost Ledger DB Schema

```sql
CREATE TABLE cost_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cost_type VARCHAR(32) NOT NULL,  -- 'llm' | 'tool' | 'storage'
    sub_type VARCHAR(128) NOT NULL,  -- 'azure_openai_gpt-4o-mini_input' | 'salesforce_query' | 's3_storage'
    quantity NUMERIC(20, 4) NOT NULL,
    unit VARCHAR(32) NOT NULL,  -- 'tokens' | 'call' | 'gb_hour'
    unit_cost_usd NUMERIC(20, 10) NOT NULL,
    total_cost_usd NUMERIC(20, 10) NOT NULL,
    session_id UUID,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_cost_ledger_tenant_recorded ON cost_ledger(tenant_id, recorded_at DESC);
CREATE INDEX idx_cost_ledger_session ON cost_ledger(session_id) WHERE session_id IS NOT NULL;

-- RLS policy (per multi-tenant-data.md 鐵律 + 56.1 check_rls_policies lint)
ALTER TABLE cost_ledger ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_cost_ledger ON cost_ledger
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

### LLM Pricing Config

```yaml
# config/llm_pricing.yml
version: "1.0"
last_updated: "2026-05-06"

providers:
  azure_openai:
    gpt-4o-mini:
      input_per_million: 0.15
      output_per_million: 0.60
      cached_input_per_million: 0.075
    gpt-5.4:
      input_per_million: 2.50
      output_per_million: 10.00
      cached_input_per_million: 1.25
  anthropic:
    claude-3.7-sonnet:
      input_per_million: 3.00
      output_per_million: 15.00
      cached_input_per_million: 0.30

tools:
  default_per_call: 0.0001  # USD;override per tool below
  salesforce_query: 0.001
  d365_create: 0.0005
```

### Risk Class C Mitigation (Module-level Singleton)

`SLAMetricRecorder` + `CostLedgerService` 透過 FastAPI dependency injection per-request 注入(`get_sla_recorder` / `get_cost_ledger` factories);**不**用 module-level singleton。Pricing config loader (yaml read) 可 cache per-process(read-only;config 改動需 restart),但 PricingLoader instance 由 FastAPI Depends 注入;測試環境 conftest.py autouse `reset_pricing_loader` fixture per testing.md §Module-level Singleton Reset Pattern.

---

## Acceptance Criteria

### Sprint-Wide

- [ ] V2 主進度 22/22 (100%) 不變;Phase 56-58 SaaS Stage 1 進度 2/3 → 3/3 (closure)
- [ ] All 8 V2 lints green (含 check_rls_policies 對 sla_violations / sla_reports / cost_ledger 必綠)
- [ ] mypy --strict 0 errors
- [ ] LLM SDK leak: 0
- [ ] Anti-pattern checklist 11 項對齐
- [ ] 5 active CI checks green
- [ ] Test count baseline 1530 → ≥ 1555 (+25 new = 5+1 unit/int US-1 + 4+2 US-2 + 5+1 US-3 + 5+1 US-4 + 1 cross-AD US-5)
- [ ] AD-Sprint-Plan-4 `large multi-domain` 2nd application captured + verdict logged in retro Q2
- [ ] AD-Plan-4-Schema-Grep formal evaluation logged in retro Q3 (2-sprint evidence: 56.1 + 56.3 → promote OR drop verdict)

### Per-User-Story

詳見 §User Stories acceptance per US.

---

## Day-by-Day Plan

### Day 0 — Setup + Day-0 兩-prong 探勘 + Pre-flight Verify

- 0.1 Branch + plan + checklist commit
- 0.2 Day-0 兩-prong 探勘(per AD-Plan-3 promoted)— **Prong 1 Path Verify**:`platform_layer/observability/sla_monitor.py` 不存在(expect)/ `platform_layer/billing/` 不存在(expect)/ `infrastructure/db/models/sla.py` + `cost_ledger.py` 不存在(expect)/ `infrastructure/db/migrations/versions/` 最新 head(expect 0013 from 55.3 OR 0014 from 56.1 if 56.1 used 0014?)/ `config/llm_pricing.yml` 不存在(expect)/ `api/v1/admin/sla_reports.py` + `cost_summary.py` 不存在;**Prong 2 Content Verify**:56.2 events.py LoopCompleted.total_tokens field exists / LoopCompleted has provider + model + input_tokens + output_tokens fields(若不全,US-4 scope 含 events.py extension)/ chat router `_stream_loop_events` 56.2 quota.record_usage hook insertion point / tool_dispatcher post-execute event emission point(若無 ToolExecuted event,US-4 scope 含 event class new)/ 53.4 governance Role enum ADMIN_TENANT / ADMIN_PLATFORM 已 56.2 extended / 56.1 tenants table schema for FK reference
- 0.3 **Schema-Grep 評估 (AD-Plan-4-Schema-Grep 2nd evidence application)** — 對新表 sla_violations / sla_reports / cost_ledger schema 假設執行 column-level grep verify;catalogue findings;為 retro Q3 promotion verdict 蒐集 evidence
- 0.4 Calibration multiplier pre-read(10-sprint window 6/10 in-band per 56.2 retro;`large multi-domain` 1-data-point 56.1=1.00;此 sprint 為 large multi-domain 2nd application 取 0.55 mid-band)
- 0.5 Pre-flight verify(pytest baseline 1530 / 8 V2 lints baseline / mypy baseline / LLM SDK leak baseline)
- 0.6 Day 0 progress.md commit + push;catalogue D-findings;若 scope shift > 20% revise plan §Risks per AD-Plan-1 audit-trail

### Day 1 — US-1 SLA Metric Recorder

- 1.1 `platform_layer/observability/sla_monitor.py` `SLAMetricRecorder` class
- 1.2 Redis sliding window methods(`record_api_request` / `record_loop_completion` / `record_hitl_queue_notification` / `record_outage_window` + `get_*_p99` queries)
- 1.3 Loop complexity classifier helper `_classify_loop_complexity(LoopCompleted) -> Literal["simple", "medium", "complex"]`
- 1.4 Chat router `_stream_loop_events` SLA span observer hook(LoopCompleted → record_loop_completion)
- 1.5 `get_sla_recorder` FastAPI dependency factory
- 1.6 5 unit US-1 + 1 integration US-1(real Redis fakeredis)
- 1.7 mypy + 8 V2 lints green
- 1.8 Day 1 progress.md + commit + push

### Day 2 — US-2 SLA Monthly Report + US-3 Cost Ledger DB schema

- 2.1 `infrastructure/db/models/sla.py` SLAViolation + SLAReport ORM
- 2.2 `infrastructure/db/models/cost_ledger.py` CostLedger ORM
- 2.3 Alembic 0014_sla_and_cost_ledger.py migration (3 tables + RLS + indexes)
- 2.4 Run alembic upgrade head + verify schema applied
- 2.5 `platform_layer/observability/sla_monitor.py` `SLAReportGenerator.generate_monthly_report` method
- 2.6 `api/v1/admin/sla_reports.py` GET endpoint(via Depends(get_admin_user(roles=[ADMIN_TENANT, ADMIN_PLATFORM])))
- 2.7 `platform_layer/billing/__init__.py` + `pricing.py` PricingLoader
- 2.8 `config/llm_pricing.yml` initial entries
- 2.9 4 unit US-2 + 2 integration US-2 + 3 unit US-3 (PricingLoader)
- 2.10 mypy + 8 V2 lints green (含 check_rls_policies 對 3 新表)
- 2.11 Day 2 progress.md + commit + push

### Day 3 — US-3 CostLedgerService + US-4 auto-record hooks

- 3.1 `platform_layer/billing/cost_ledger.py` `CostLedgerService.record_llm_call` + `record_tool_call` + `aggregate(tenant_id, month)`
- 3.2 `api/v1/admin/cost_summary.py` GET endpoint
- 3.3 Chat router `_stream_loop_events` Cost Ledger LLMResponded hook(reuse 56.2 LoopCompleted total_tokens for actual_tokens;split input + output 2 entries)
- 3.4 Tool dispatcher post-execute event emission(若 Day 0 確認無現有 event,則 add ToolExecuted 中性 event in events.py);chat router observer ToolExecuted → cost_ledger.record_tool_call
- 3.5 `get_cost_ledger` FastAPI dependency factory
- 3.6 2 unit US-3 (CostLedgerService) + 1 integration US-3 + 5 unit US-4 + 1 integration US-4
- 3.7 mypy + 8 V2 lints green
- 3.8 Day 3 progress.md + commit + push

### Day 4 — US-5 Closeout Ceremony

- 4.1 Cross-AD e2e integration test `test_phase56_3_e2e.py`(provision RBAC + onboard + chat with quota reconcile + SLA span + Cost Ledger entry visible)
- 4.2 Final pytest + 8 V2 lints + LLM SDK leak verify
- 4.3 retrospective.md(6 必答 + AD-Sprint-Plan-4 large multi-domain 2nd app calibration verify + AD-Plan-4-Schema-Grep verdict)
- 4.4 Memory snapshot `memory/project_phase56_3_sla_monitor_cost_ledger.md`
- 4.5 Open PR → CI green → solo-dev squash merge to main
- 4.6 Closeout PR(SITUATION-V2 §9 + CLAUDE.md + memory MEMORY.md index)
- 4.7 Final push + Phase 56-58 SaaS Stage 1 3/3 ceremony note

---

## File Change List

| File | Status | Lines (est) |
|------|--------|-------------|
| `platform_layer/observability/sla_monitor.py` | NEW | ~250 |
| `platform_layer/billing/__init__.py` | NEW | ~10 |
| `platform_layer/billing/cost_ledger.py` | NEW | ~180 |
| `platform_layer/billing/pricing.py` | NEW | ~80 |
| `infrastructure/db/models/sla.py` | NEW | ~80 |
| `infrastructure/db/models/cost_ledger.py` | NEW | ~50 |
| `infrastructure/db/migrations/versions/0014_sla_and_cost_ledger.py` | NEW | ~150 |
| `config/llm_pricing.yml` | NEW | ~40 |
| `api/v1/admin/sla_reports.py` | NEW | ~80 |
| `api/v1/admin/cost_summary.py` | NEW | ~60 |
| `api/v1/chat/router.py` | MODIFIED | +50 |
| `agent_harness/orchestrator_loop/tool_dispatcher.py` | MODIFIED | +20 |
| `agent_harness/_contracts/events.py` | MODIFIED (if needed per Day 0) | +10 |
| `scripts/cron/monthly_sla_report_run.py` | NEW (stub) | ~40 |
| Tests (~25 new) | NEW | ~700 |
| `docs/.../sprint-56-3/{progress,retrospective}.md` | NEW | ~600 |
| `memory/project_phase56_3_sla_monitor_cost_ledger.md` | NEW | ~60 |

**Total**: ~1,170 source LOC + ~700 test LOC + ~660 docs LOC

---

## Dependencies & Risks

### Dependencies (must exist before code starts)

- ⚠️ Phase 56.2 `platform_layer/observability/tracer.py` `get_tracer` factory — Day 0 grep verify (closed by 56.2)
- ⚠️ Phase 56.2 `agent_harness/_contracts/events.py` `LoopCompleted.total_tokens` field — Day 0 grep verify (closed by 56.2)
- ⚠️ Phase 56.2 chat router LoopCompleted observer 56.2 quota.record_usage hook — Day 0 grep verify (closed by 56.2)
- ⚠️ Phase 56.1 `tenants` table for FK references — Day 0 grep verify (closed by 56.1 lifecycle)
- ⚠️ Phase 53.4 governance Role enum ADMIN_TENANT + ADMIN_PLATFORM — Day 0 grep verify (closed by 56.2 extension if needed)
- ⚠️ Phase 53.4 `Depends(get_admin_user)` factory — Day 0 grep verify (closed by 56.2)
- ⚠️ Alembic head version — Day 0 verify (expect 0013 from 55.3 OR 0014 if 56.1 occupied — adjust migration filename)
- ⚠️ Redis fakeredis test fixture available — Day 0 grep verify (used by 53.3 + 55.4 + 56.1)
- ⚠️ Tool executor `tool_dispatcher` post-execute event emission point — Day 0 grep verify (若無 ToolExecuted event,US-4 scope +1 hr)

### Risk Classes (per sprint-workflow.md §Common Risk Classes)

**Risk Class A (paths-filter vs required_status_checks)**: 已 closed by 55.6 Option Z (paths-filter retired 永久);此 sprint 不適用。

**Risk Class B (cross-platform mypy unused-ignore)**: medium risk;新檔較多(~10 new modules),Alembic types may need `# type: ignore[X, unused-ignore]`;Redis async types known issue.

**Risk Class C (module-level singleton across event loops)**: HIGH RELEVANCE — `SLAMetricRecorder` 共享 Redis client / `CostLedgerService` 共享 DB pool / `PricingLoader` cache yaml — 3 個 module 都可能 module-level cache。Mitigation: 全 FastAPI Depends per-request 注入(no module-level cache);測試 conftest.py autouse `reset_pricing_loader` + `reset_sla_recorder` + `reset_cost_ledger` fixtures per testing.md §Module-level Singleton Reset Pattern.

### Day 0 探勘 D-findings (catalogued during Day 0 兩-prong 探勘)

> 起草時無 D-findings;Day 0 探勘後 fill in this table per AD-Plan-1 + AD-Plan-3 promoted.

### Sprint-specific Risks

| Risk | Mitigation |
|------|-----------|
| Alembic 0014 already occupied by 56.1 | Day 0 grep verify;若是 → use 0015_sla_and_cost_ledger.py(MHist log path correction;plan §File Layout 保 0014 audit trail per AD-Plan-1) |
| LoopCompleted event 缺 provider / model / input_tokens / output_tokens fields | Day 0 grep verify;若缺 → US-4 scope 含 events.py field extension(~30 min);若 56.2 LoopCompleted.total_tokens 是 single value 不分 input/output → US-4 estimate input via Cat 4 ChatClient.count_tokens (從 messages) + output = total - input |
| Tool dispatcher 缺 post-execute event emission | Day 0 grep verify;若缺 → US-4 scope add ToolExecuted event in events.py + emission in dispatcher(+1 hr);若有現有 event → wire observer |
| RLS policy lint check_rls_policies fail on 3 new tables | 3 tables migration 必含 ALTER TABLE … ENABLE ROW LEVEL SECURITY + tenant_isolation policy;Day 2 完整測試;若 lint fail → 補 migration |
| Redis sliding window memory growth | Per-tenant key TTL 10 min(2× window);ZREMRANGEBYSCORE 每 record 清舊;production mem growth need Phase 57+ DBA review |
| LLM pricing yaml stale | `last_updated` field in yaml;Phase 56.x audit cycle 評估自動 sync(Stripe / Anthropic API price endpoint);此 sprint stub manual edit |
| Cost Ledger high write rate (every LLM call) | Bulk insert via async batch (write-behind queue);此 sprint sync write 即可(production load test → Phase 57+);indexes covered |
| `large multi-domain` 0.55 mult 2nd app ratio outside band | 若 ratio > 1.20 → AD-Sprint-Plan-7 lift(0.55 → 0.60);若 < 0.85 → AD-Sprint-Plan-7 reduce(0.55 → 0.50);each case logged in retro Q2 |
| AD-Plan-4-Schema-Grep evidence inconclusive | 56.1 D26+D27 was column-level drift caught at first test;56.3 Day 0 schema-grep 探勘 = 2nd evidence;若 56.3 Day 0 也 catch column drift → promote;若 catch 0 → 仍 candidate(3-sprint evidence rule);each retro Q3 documented |

---

## Workload

> **Bottom-up est ~24 hr → calibrated commit ~13 hr (multiplier 0.55 per AD-Sprint-Plan-4 scope-class matrix `large multi-domain` 2nd application;56.1 1-data-point baseline ratio 1.00 ✅)**
> **10-sprint window 6/10 in-band(`large multi-domain` 1-data-point 56.1=1.00)** — `large multi-domain` 從 AD-Sprint-Plan-4 matrix 取 0.50-0.55 band, 取 0.55 mid (per 56.1 first application convention)

| US | Bottom-up (hr) |
|----|---------------|
| US-1 SLA Metric Recorder (sla_monitor.py + Redis sliding + chat router observer + 5+1 tests) | 6 |
| US-2 SLA Monthly Report + DB schema (SLAReport ORM + Alembic + GenerateReport + endpoint + 4+2 tests) | 4 |
| US-3 Cost Ledger DB + ORM + Pricing config + Service + endpoint (cost_ledger ORM + Alembic + CostLedgerService + PricingLoader + yaml + endpoint + 5+1 tests) | 5 |
| US-4 Cost Ledger auto-record hooks (chat router LLM hook + tool_dispatcher event + observer + 5+1 tests) | 5 |
| US-5 Closeout (cross-AD e2e + retro + ceremony + memory + closeout PR) | 4 |
| **Total bottom-up** | **24** |
| **× 0.55 calibrated** | **13.2 ≈ 13** |

Day 4 retrospective Q2 must verify: `actual_total_hr / 13 → ratio` compared to [0.85, 1.20] band;document delta + log calibration verdict for `large multi-domain` class 2nd data point;若 ratio in band → mean 計算(56.1=1.00 + 56.3=ratio)mid-band 鎖定 0.55。

---

## Out of Scope

- ❌ Stripe / 月結 invoice / billing run — Phase 57+ Stage 2 commercial SaaS
- ❌ SLA auto-credit when threshold missed — Phase 56.x audit / Stage 2(此 sprint 只 generate report,不 charge credit)
- ❌ Customer-facing Status Page UI — Phase 56+ frontend
- ❌ Cross-region DR + WAL streaming — Phase 57+
- ❌ Citus PoC / horizontal sharding — Phase 57+(standalone worktree)
- ❌ Compliance partial GDPR right-to-erasure — Phase 57+
- ❌ Frontend Onboarding Wizard UI — Phase 57+ frontend
- ❌ Real cron schedule for monthly SLA report — 此 sprint stub script,Phase 56.x 真實 schedule(via Celery beat / cron)
- ❌ Auto-sync LLM pricing from provider APIs — 此 sprint stub manual yaml edit;Phase 56.x audit
- ❌ Multi-worker quota / cost ledger race condition production load test — Phase 57+ SLA Monitor 整合測試
- ❌ Storage / GB-hour cost tracking — 此 sprint cost_type 預留 'storage' 但 record path 不實作(無 storage event);Phase 57+
- ❌ Real Webhook for SLA violation alert — Phase 57+(此 sprint stub log + audit log entry)
- ❌ Public API / customer-facing cost API — 此 sprint admin-only endpoints;Public API Phase 57+
- ❌ Cost Ledger 7-year retention archival to cold storage — Phase 57+ DBA / compliance scope

---

## AD Carryover Sub-Scope

### AD-Sprint-Plan-4 `large multi-domain` 2nd application

**Source**: Sprint 55.3 retrospective Q2 (calibration matrix proposed) → 56.1 retro Q2 1.00 baseline (large multi-domain 1-data-point) → 此 sprint 為 large multi-domain 2nd application

**Closure plan**:
1. Sprint 56.3 plan §Workload uses **0.55** for `large multi-domain` class (2nd application;mid-band per 56.1 convention)
2. Day 4 retrospective Q2 computes `actual / 13`
3. If ratio ∈ [0.85, 1.20] → record `large multi-domain` 2-data-point baseline (56.1=1.00 + 56.3=ratio);large multi-domain mean 計算 → mid-band 鎖定 0.55
4. If ratio < 0.85 → log AD-Sprint-Plan-7 (lower 0.55 → 0.50)
5. If ratio > 1.20 → log AD-Sprint-Plan-7 (raise 0.55 → 0.60)
6. large multi-domain window 從 1 → 2 data points;3 data points 之前不調整 mid-band

### AD-Plan-4-Schema-Grep formal evaluation (2nd evidence)

**Source**: Sprint 56.1 retrospective Q3 process insight (D26+D27 column-level drift caught at first test) → Sprint 56.2 retro Q3 (Day 0 探勘 produced no column drift; 1-sprint evidence rule defer 2nd) → 此 sprint Day 0 schema-grep 探勘 = 2nd evidence application

**Closure plan**:
1. Day 0 探勘 specific schema-grep on 3 new tables(sla_violations / sla_reports / cost_ledger column assertions)
2. Catalogue findings — column-level drift caught? OR 0 findings?
3. Day 4 retrospective Q3 compute promotion verdict:
   - **Promote AD-Plan-4-Schema-Grep to validated rule** if 56.1 + 56.3 both catch column-level drift(2-sprint evidence;ROI confirmed)
   - **Drop AD-Plan-4-Schema-Grep** if 56.3 catches 0 column drift(56.1 was outlier;not worth process overhead)
   - **Keep candidate** if 56.3 catches partial / mixed signals(continue evaluation Phase 57+)
4. Update sprint-workflow.md §Step 2.5 if promoted(add Schema-Grep as Prong 3 OR extension to Prong 2)

### Phase 56-58 SaaS Stage 1 closure

**Source**: Phase 56-58 SaaS Stage 1 design = provisioning (56.1) + polish (56.2) + monitor & ledger (56.3) backend stack

**Closure plan**:
1. Sprint 56.3 closure → Phase 56-58 SaaS Stage 1 backend 3/3 ✅
2. retrospective.md Q5 lists Phase 57+ candidate scope (Citus PoC / DR / Compliance partial GDPR / Frontend Onboarding Wizard / Stripe月結 / Customer Status Page);user approval required per rolling planning 紀律
3. SITUATION-V2 §9 + CLAUDE.md sync to **Phase 56-58 SaaS Stage 1 3/3 (Sprint 56.3 closed)**
4. Memory snapshot `memory/project_phase56_3_sla_monitor_cost_ledger.md` + Phase 56 SaaS summary update

---

## Definition of Done

- [ ] All 5 USs acceptance criteria met
- [ ] Test count ≥ 1555 (1530 + 25 new)
- [ ] mypy --strict 0 errors
- [ ] 8 V2 lints green (含 check_rls_policies on 3 new tables)
- [ ] LLM SDK leak: 0
- [ ] Anti-pattern checklist 11 項對齐
- [ ] AD-Sprint-Plan-4 `large multi-domain` 2nd application captured + verdict logged
- [ ] AD-Plan-4-Schema-Grep formal evaluation logged in retro Q3 (promote / drop / keep candidate verdict)
- [ ] Cross-AD e2e integration test passed (provision RBAC + chat quota reconcile + SLA span + Cost Ledger entries visible)
- [ ] PR opened, CI green (5 active checks), solo-dev merged to main
- [ ] Closeout PR merged
- [ ] SITUATION-V2 + memory + CLAUDE.md updated to **Phase 56-58 SaaS Stage 1 3/3 (Sprint 56.3 closed)**
- [ ] Phase 57+ candidate scope documented in retrospective Q5 (Citus PoC / DR / Compliance / Frontend / Stripe / Status Page;user approval required per rolling planning)

---

## References

- 15-saas-readiness.md §SLA 與監控 + §Billing - Cost Ledger 整合(authoritative spec for SLA + Cost Ledger)
- 17-cross-category-interfaces.md §Contract 12 Tracer + §Contract 8 ChatClient.count_tokens (Cat 4 + Cat 12 contracts)
- 10-server-side-philosophy.md §原則 1 Server-Side First + §multi-tenant
- 14-security-deep-dive.md §RBAC + §multi-tenant tenant_id propagation + §audit log
- 09-db-schema-design.md (DB schema patterns + RLS templates)
- .claude/rules/observability-instrumentation.md (Cat 12 5 必埋點 + ctx mgr pattern)
- .claude/rules/multi-tenant-data.md (3 鐵律 + RLS policy templates)
- .claude/rules/sprint-workflow.md §Step 2.5 Day-0 兩-prong 探勘 + §Common Risk Classes
- .claude/rules/file-header-convention.md (MHist 1-line max per AD-Lint-3 + char-count guidance per AD-Lint-MHist-Verbosity)
- Sprint 56.2 plan + checklist (format template per AD-Sprint-Plan-1 + AD-Lint-2)
- Sprint 56.1 plan + checklist (large multi-domain class first application baseline)
- Sprint 56.2 retrospective Q5 (Phase 56.3 candidate scope user approval 2026-05-06)
- Sprint 56.1 retrospective Q3 (AD-Plan-4-Schema-Grep candidate first observation D26+D27)
- Sprint 53.4 (governance Role enum + RBAC infrastructure)
- Sprint 49.4 (OpenTelemetry SDK initialization)
