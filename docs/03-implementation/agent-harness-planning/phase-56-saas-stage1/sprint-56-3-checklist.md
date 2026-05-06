# Sprint 56.3 — Phase 56+ SaaS Stage 1 3rd of 3: SLA Monitor + Cost Ledger 聯合 — Checklist

**Plan**: [sprint-56-3-plan.md](sprint-56-3-plan.md)
**Branch**: `feature/sprint-56-3-sla-monitor-cost-ledger`
**Day count**: 5 (Day 0-4) | **Bottom-up est**: ~24 hr | **Calibrated commit**: ~13 hr (multiplier **0.55** per AD-Sprint-Plan-4 scope-class matrix `large multi-domain` 2nd application;reserved 0.50-0.55 band, picking 0.55 mid-band per 56.1 first application convention)

> **格式遵守**: 每 Day 同 56.2 結構(progress.md update + sanity + commit + verify CI)。每 task 3-6 sub-bullets(case / DoD / Verify command)。Per AD-Lint-2 (53.7) — 不寫 per-day calibrated hour targets;只寫 sprint-aggregate calibration verify in retro。Per AD-Plan-3 promoted (55.6) — Day 0 兩-prong 探勘(Path Verify + Content Verify)是 mandatory。Per AD-Plan-4-Schema-Grep candidate 2nd evidence — Day 0 含 schema column-level grep evaluation。Day count 5(scope-difference via content not structure)— 對比 56.2 10 hr/4 days,此 sprint 24 hr/5 days。

---

## Day 0 — Setup + Day-0 兩-prong 探勘 + Pre-flight Verify

### 0.1 Branch + plan + checklist commit
- [ ] **Verify on main + clean** — `git status --short` empty + HEAD `6236c098`(post-PR #100 56.2 closeout)
- [ ] **Create branch + push plan/checklist** — `git checkout -b feature/sprint-56-3-sla-monitor-cost-ledger`
- [ ] **Stage + commit plan + checklist + push branch** — commit msg `chore(docs, sprint-56-3): plan + checklist for Phase 56.3 SLA Monitor + Cost Ledger 聯合`

### 0.2 Day-0 兩-prong 探勘 — verify plan §Technical Spec assertions against actual repo state

Per AD-Plan-3 promoted (55.6) — Prong 1 Path Verify + Prong 2 Content Verify;catalogue D-findings.

**Prong 1: Path Verify (existence checks)**
- [ ] **Verify `platform_layer/observability/sla_monitor.py` not exists** — Glob check (expect: not exist; new file)
- [ ] **Verify `platform_layer/billing/` dir not exists** — Glob check (expect: not exist; new dir)
- [ ] **Verify `infrastructure/db/models/sla.py` + `cost_ledger.py` not exist** — Glob check (expect: not exist; new ORM)
- [ ] **Verify Alembic head version** — `ls infrastructure/db/migrations/versions/ | sort -V | tail -3` confirm latest head;若 0014 已被 56.1 占用 → use 0015 (catalogue as D-finding)
- [ ] **Verify `config/llm_pricing.yml` not exists** — Glob check (expect: not exist; new config)
- [ ] **Verify `api/v1/admin/sla_reports.py` + `cost_summary.py` not exist** — Glob check (expect: not exist; new endpoints)
- [ ] **Verify `scripts/cron/` dir** — Glob check;若不存在 → create with `__init__.py` + add to existing scripts structure
- [ ] **Verify Redis fakeredis test fixture** — `grep -rn "fakeredis\|FakeRedis" backend/tests/conftest.py backend/tests/integration/` confirm 53.3 + 56.1 + 56.2 baseline pattern reusable

**Prong 2: Content Verify (semantic checks)**
- [ ] **Verify 56.2 `platform_layer/observability/tracer.py` `get_tracer` factory exists** — `grep -A 5 "def get_tracer" platform_layer/observability/tracer.py` confirm signature
- [ ] **Verify 56.2 `agent_harness/_contracts/events.py` LoopCompleted.total_tokens field exists** — `grep -B 2 -A 10 "class LoopCompleted" agent_harness/_contracts/events.py` confirm `total_tokens: int = 0` field present
- [ ] **Verify LoopCompleted has provider/model/input_tokens/output_tokens fields** — `grep -A 20 "class LoopCompleted" agent_harness/_contracts/events.py` 評估 fields completeness;若缺 input_tokens / output_tokens / provider / model → catalogue D-finding(US-4 scope adjust)
- [ ] **Verify 56.2 chat router `_stream_loop_events` 56.2 quota.record_usage hook insertion point** — `grep -n "record_usage\|LoopCompleted" api/v1/chat/router.py` confirm baseline observer pattern
- [ ] **Verify tool_dispatcher post-execute event emission** — `grep -rn "ToolExecuted\|class ToolExecuted\|emit.*ToolExecuted" agent_harness/orchestrator_loop/ agent_harness/_contracts/events.py` confirm whether ToolExecuted event exists;若無 → catalogue D-finding (US-4 scope +1 hr add ToolExecuted event)
- [ ] **Verify 53.4 governance Role enum ADMIN_TENANT + ADMIN_PLATFORM exist** — `grep -B 2 -A 20 "class Role\|ADMIN_TENANT\|ADMIN_PLATFORM" platform_layer/identity/auth.py platform_layer/governance/` confirm 56.2 extension applied
- [ ] **Verify 53.4 `Depends(get_admin_user)` factory exists** — `grep -rn "def require_admin_platform_role\|def require_admin_tenant_role\|def get_admin_user" platform_layer/identity/auth.py` confirm 56.2 dep available
- [ ] **Verify 56.1 `tenants` table FK target** — `grep -A 10 "class Tenant" infrastructure/db/models/identity.py` confirm `tenants.id` UUID PK exists for FK reference

**Prong 3: Schema-Grep 評估 (AD-Plan-4-Schema-Grep 2nd evidence — 候選 promotion)**
- [ ] **Schema-grep 1: sla_violations columns** — assume columns(id / tenant_id / metric_type / threshold_pct / actual_pct / detected_at / resolved_at / severity);grep `infrastructure/db/models/` for any pre-existing similar table that might collide
- [ ] **Schema-grep 2: sla_reports columns** — assume columns(id / tenant_id / month / availability_pct / api_p99_ms / loop_simple_p99_ms / loop_medium_p99_ms / loop_complex_p99_ms / hitl_queue_notif_p99_ms / violations_count / generated_at);grep similar;若 audit_chain 或 metrics_log 已有 overlapping schema → catalogue D-finding
- [ ] **Schema-grep 3: cost_ledger columns** — assume columns(id / tenant_id / cost_type / sub_type / quantity / unit / unit_cost_usd / total_cost_usd / session_id / recorded_at);grep similar;若 quota_usage_log / audit_log 已有 overlapping schema → catalogue D-finding
- [ ] **Document Schema-Grep findings in progress.md Day 0** — caught column drift? OR 0 findings?

**Catalogue findings**
- [ ] **Catalogue all D-findings in progress.md** — format `D{N}` ID + Finding + Implication;link to plan §Risks update if scope shift > 20%
- [ ] **Decide go/no-go** — findings shift scope ≤ 20% → continue Day 1;20-50% → revise plan §Acceptance + §Workload + re-confirm with user;> 50% → abort sprint redraft

### 0.3 AD-Plan-4-Schema-Grep 2nd evidence shaping (for retro Q3)
- [ ] **Note schema-grep findings for retro Q3** — 56.1 D26+D27 = 1st data point caught column drift;此 sprint Day 0 Schema-Grep findings = 2nd data point;Day 4 retro Q3 verdict will be:promote (2-sprint evidence) / drop (56.1 outlier) / keep candidate (mixed signals)

### 0.4 Calibration multiplier pre-read
- [ ] **Read 56.2 retrospective Q2** — confirm 10-sprint window 6/10 in-band (53.7=1.01 / 55.2=1.10 / 55.5=1.14 / 55.6=0.92 / 56.1=1.00 / 56.2=1.17);mixed mean 1.09
- [ ] **Confirm AD-Sprint-Plan-4 scope-class matrix** — `large multi-domain` band 0.50-0.55;1-data-point baseline 56.1=1.00 ✅;此 sprint picks 0.55 mid-band as 2nd application
- [ ] **Compute 56.3 bottom-up** — 24 hr × 0.55 = 13.2 ≈ 13 hr commit
- [ ] **Document predicted vs banked** — `large multi-domain` 2nd application;1-data-point baseline 鎖定;若此 sprint ratio ∈ band → large multi-domain mean 從 1 → 2 data points;若 outside band → AD-Sprint-Plan-7 logged

### 0.5 Pre-flight verify (main green baseline)
- [ ] **pytest collect baseline** — expect `1530 collected` (per 56.2 closeout main HEAD `6236c098`)
- [ ] **8 V2 lints via run_all.py** — `python scripts/lint/run_all.py` → 8/8 green
- [ ] **Backend full pytest baseline** — `python -m pytest` → 1530 passed / 4 skipped / 0 fail
- [ ] **mypy --strict baseline** — `python -m mypy backend/src --strict` → 0 errors
- [ ] **LLM SDK leak baseline** — `grep -rn "^(from |import )(openai|anthropic|agent_framework)" backend/src/agent_harness backend/src/business_domain backend/src/platform_layer backend/src/core` → 0

### 0.6 Day 0 progress.md
- [ ] **Create `docs/03-implementation/agent-harness-execution/phase-56/sprint-56-3/progress.md`** — Day 0 entry with探勘 findings + Schema-Grep findings + baseline + Day 1 plan + scope shifts (if any)
- [ ] **Commit + push Day 0** — commit msg `docs(sprint-56-3): Day 0 progress + 兩-prong 探勘 baseline + Schema-Grep evaluation`

---

## Day 1 — US-1 SLA Metric Recorder

### 1.1 SLAMetricRecorder class
- [ ] **Create `platform_layer/observability/sla_monitor.py`** — `SLAMetricRecorder` class with `__init__(redis: Redis, db: AsyncSession)` + 4 record methods
- [ ] **`record_api_request(tenant_id, latency_ms, status_code)`** — Redis sliding window 5-min;ZADD + ZREMRANGEBYSCORE;EXPIRE 600
- [ ] **`record_loop_completion(tenant_id, latency_ms, complexity_category)`** — same pattern + complexity in key
- [ ] **`record_hitl_queue_notification(tenant_id, queue_to_notify_ms)`** — same pattern
- [ ] **`record_outage_window(tenant_id, start_ts, end_ts)`** — Postgres direct write (outage 持久 record)
- [ ] **`get_*_p99` query methods** — ZRANGE + sort + p99 index calc
- [ ] **File header docstring** — Purpose / Category 12 / Created / Modification History
- DoD: mypy strict green;import works
- Verify: `python -c "from platform_layer.observability.sla_monitor import SLAMetricRecorder; print(SLAMetricRecorder)"`

### 1.2 Loop complexity classifier
- [ ] **Add `_classify_loop_complexity(event: LoopCompleted) -> Literal["simple", "medium", "complex"]`** in sla_monitor.py
- [ ] **Logic per 15-saas-readiness.md** — ≤ 3 turns + ≤ 2 tool_calls + 0 subagent + < 4K input tokens = simple;4-10 turns + 多工具 + 0-1 subagent = medium;else = complex
- [ ] **Default fallback** — if event 缺 fields → return "complex" (most conservative)
- DoD: 3 unit tests cover boundary transitions

### 1.3 get_sla_recorder FastAPI dep
- [ ] **Create `get_sla_recorder` factory in sla_monitor.py** — module-level cache with `reset_sla_recorder()` helper per testing.md §Module-level Singleton Reset Pattern
- [ ] **Conftest autouse `reset_sla_recorder` fixture** — `tests/integration/api/conftest.py` add to existing reset list

### 1.4 Chat router SLA observer hook
- [ ] **Modify `api/v1/chat/router.py`** — add `Depends(get_sla_recorder)` to `_stream_loop_events`
- [ ] **LoopCompleted observer extension** — after 56.2 quota.record_usage → call `sla_recorder.record_loop_completion(tenant_id, elapsed_ms, complexity)`
- [ ] **chat_start_time = time.monotonic()** — measure end-to-end loop latency
- [ ] **Update file header MHist** — `Sprint 56.3 — wire SLA span observer (US-1 partial)`
- DoD: existing 56.2 tests still pass

### 1.5 5 unit US-1 + 1 integration US-1
**Unit (5)**
- [ ] **test_sla_metric_recorder_record_loop_completion_redis_zadd** — mock Redis;assert ZADD + ZREMRANGEBYSCORE called
- [ ] **test_sla_metric_recorder_get_loop_p99_returns_correct_index** — populate fakeredis with 100 records;assert p99 = 99th item sorted
- [ ] **test_classify_loop_complexity_simple** — 3 turns / 2 tools / 0 subagent / 3K tokens → "simple"
- [ ] **test_classify_loop_complexity_medium** — 5 turns / 3 tools / 1 subagent → "medium"
- [ ] **test_classify_loop_complexity_complex_fallback** — missing fields → "complex"

**Integration (1)**
- [ ] **test_chat_request_sla_recorded_in_redis** — fakeredis;POST chat → assert sla:metrics:{tenant}:loop_simple:5m key has entry with latency

DoD: 6 tests pass < 5s

### 1.6 Day 1 sanity checks
- [ ] **mypy --strict** — 0 errors
- [ ] **black + isort + flake8** — clean
- [ ] **8 V2 lints via run_all.py** — 8/8 green
- [ ] **Backend full pytest** — 1530 + 6 = 1536 passed
- [ ] **53.6 production HITL regression** — no regression
- [ ] **LLM SDK leak** — 0

### 1.7 Day 1 commit + push + progress.md
- [ ] **Stage + commit Day 1** — commit msg `feat(observability, sprint-56-3): SLAMetricRecorder + chat router observer (US-1 part 1 — Cat 12 SLA recording)`
- [ ] **Update progress.md** with Day 1 actuals + drift findings if any
- [ ] **Push to origin**

---

## Day 2 — US-2 SLA Monthly Report + US-3 Cost Ledger DB schema

### 2.1 SLA + Cost Ledger ORM models
- [ ] **Create `infrastructure/db/models/sla.py`** — SLAViolation + SLAReport ORM (per plan §Tech Spec)
- [ ] **Create `infrastructure/db/models/cost_ledger.py`** — CostLedger ORM (per plan §Tech Spec)
- [ ] **TenantScopedMixin reuse** — both ORMs inherit per 56.1 baseline
- [ ] **File header docstrings** — Category infrastructure/db (cross-domain;multi-tenant rule)
- DoD: mypy strict green
- Verify: `python -c "from infrastructure.db.models.sla import SLAViolation, SLAReport; from infrastructure.db.models.cost_ledger import CostLedger; print(SLAViolation, SLAReport, CostLedger)"`

### 2.2 Alembic 0014 migration (3 tables)
- [ ] **Create `infrastructure/db/migrations/versions/0014_sla_and_cost_ledger.py`** (or 0015 if 56.1 occupied 0014 — adjust per Day 0 D-finding)
- [ ] **Alembic upgrade direction** — 3 tables CREATE + indexes + RLS policies
- [ ] **Alembic downgrade direction** — DROP TABLE 3 tables (reverse order)
- [ ] **RLS policy 3 tables** — `ENABLE ROW LEVEL SECURITY` + `CREATE POLICY tenant_isolation_*` for each per multi-tenant-data.md §RLS template
- [ ] **Indexes** — `idx_sla_violations_tenant_detected` / `idx_sla_reports_tenant_month UNIQUE` / `idx_cost_ledger_tenant_recorded` / `idx_cost_ledger_session WHERE NOT NULL`
- [ ] **Run alembic upgrade head** — verify schema applied + RLS policies active
- DoD: alembic upgrade head success;3 tables visible in pg_tables;3 RLS policies in pg_policies
- Verify: `alembic upgrade head && python scripts/lint/check_rls_policies.py`

### 2.3 SLAReportGenerator
- [ ] **Add `SLAReportGenerator` class to sla_monitor.py** — `__init__(redis, db)`;`generate_monthly_report(tenant_id, month) -> SLAReport`
- [ ] **Query last 30 days Redis sliding window** — aggregate p99 per metric category
- [ ] **Persist SLAReport row** — write to sla_reports table
- [ ] **Violation detection** — if availability_pct < threshold (Standard 99.5% / Enterprise 99.9% per 15-saas-readiness.md) → write SLAViolation row
- [ ] **Tier lookup** — query tenants table for `plan` field;Standard threshold vs Enterprise threshold
- DoD: mypy strict green

### 2.4 SLA reports endpoint
- [ ] **Create `api/v1/admin/sla_reports.py`** — `GET /api/v1/admin/tenants/{tenant_id}/sla-report?month=YYYY-MM` endpoint
- [ ] **Auth dep** — `Depends(require_admin_tenant_role)` (multi-tier admin acceptable per 56.2 RBAC pattern)
- [ ] **Cache lookup** — query sla_reports for existing row;若無 → 即時 generate via SLAReportGenerator
- [ ] **Response model** — Pydantic SLAReportResponse
- [ ] **File header docstring**
- DoD: mypy strict green;endpoint registered in main router

### 2.5 Pricing config + PricingLoader
- [ ] **Create `config/llm_pricing.yml`** — initial entries per plan §Tech Spec(azure_openai gpt-4o-mini + gpt-5.4 + anthropic claude-3.7-sonnet stub + tools default + salesforce_query + d365_create)
- [ ] **Create `platform_layer/billing/__init__.py`** — re-export PricingLoader + CostLedgerService
- [ ] **Create `platform_layer/billing/pricing.py`** — PricingLoader class with `load_from_yaml(path)` + `get_llm_pricing(provider, model)` + `get_tool_pricing(tool_name)` + `last_updated` field
- [ ] **`get_pricing_loader` FastAPI dep + reset helper** — module-level cache;testing.md §Singleton reset
- [ ] **Conftest reset_pricing_loader fixture** — `tests/integration/api/conftest.py` add to reset list
- DoD: mypy strict green;yaml parsing works
- Verify: `python -c "from platform_layer.billing.pricing import PricingLoader; pl = PricingLoader(); pl.load_from_yaml('config/llm_pricing.yml'); print(pl.get_llm_pricing('azure_openai', 'gpt-5.4'))"`

### 2.6 4 unit US-2 + 2 integration US-2 + 3 unit US-3 (PricingLoader)
**Unit US-2 (4)**
- [ ] **test_sla_report_generator_generate_monthly_report_persists_row** — mock Redis + db;assert sla_reports row written
- [ ] **test_sla_report_generator_writes_violation_when_below_threshold** — set availability 99.0% under Standard 99.5% threshold;assert SLAViolation row
- [ ] **test_sla_report_endpoint_returns_cached_when_exists** — pre-populate sla_reports;assert cache hit
- [ ] **test_sla_report_endpoint_generates_on_demand_when_missing** — empty sla_reports;assert generate path called

**Integration US-2 (2)**
- [ ] **test_admin_sla_report_endpoint_403_without_admin_role** — non-admin user → 403
- [ ] **test_admin_sla_report_endpoint_returns_json_with_4_metrics** — auth as ADMIN_TENANT → 200 + JSON has availability/api_p99/loop_*/hitl_queue_notif

**Unit US-3 PricingLoader (3)**
- [ ] **test_pricing_loader_load_from_yaml_parses_3_providers** — fixture yaml;assert get_llm_pricing returns correct values for 3 providers
- [ ] **test_pricing_loader_get_tool_pricing_returns_default_when_unknown** — unknown tool → default_per_call
- [ ] **test_pricing_loader_get_tool_pricing_overrides_for_known** — salesforce_query → override value

DoD: 9 tests pass < 5s

### 2.7 Day 2 sanity checks
- [ ] **mypy --strict** — 0 errors
- [ ] **black + isort + flake8** — clean
- [ ] **8 V2 lints via run_all.py** — 8/8 green (含 check_rls_policies on 3 new tables PASS)
- [ ] **Backend full pytest** — 1536 + 9 = 1545 passed
- [ ] **LLM SDK leak** — 0

### 2.8 Day 2 commit + push + progress.md
- [ ] **Stage + commit Day 2** — commit msg `feat(billing, observability, db, sprint-56-3): SLA report + Cost Ledger ORM + Alembic 0014 + PricingLoader (US-2 close + US-3 part 1)`
- [ ] **Update progress.md** with Day 2 actuals
- [ ] **Push to origin**

---

## Day 3 — US-3 CostLedgerService + US-4 auto-record hooks

### 3.1 CostLedgerService
- [ ] **Create `platform_layer/billing/cost_ledger.py`** — CostLedgerService class
- [ ] **`record_llm_call(tenant_id, provider, model, input_tokens, output_tokens, cached_input_tokens, session_id)`** — split 2 entries (input cost + output cost);若 cached_input → use cached_input_per_million pricing
- [ ] **`record_tool_call(tenant_id, tool_name, session_id)`** — single entry with quantity=1, unit="call"
- [ ] **`aggregate(tenant_id, month) -> AggregatedUsage`** — SUM(total_cost_usd) GROUP BY cost_type + sub_type
- [ ] **`get_cost_ledger` FastAPI dep + reset helper** — module-level cache pattern
- [ ] **Conftest reset_cost_ledger fixture** — add to reset list
- DoD: mypy strict green
- Verify: `python -c "from platform_layer.billing.cost_ledger import CostLedgerService; print(CostLedgerService)"`

### 3.2 Cost summary endpoint
- [ ] **Create `api/v1/admin/cost_summary.py`** — `GET /api/v1/admin/tenants/{tenant_id}/cost-summary?month=YYYY-MM` endpoint
- [ ] **Auth dep** — `Depends(require_admin_tenant_role)`
- [ ] **Response model** — Pydantic AggregatedUsageResponse
- [ ] **File header docstring**
- DoD: mypy strict green;endpoint registered

### 3.3 Chat router Cost Ledger hook (US-4 LLM hook)
- [ ] **Modify `api/v1/chat/router.py`** — add `Depends(get_cost_ledger)` + `Depends(get_pricing_loader)`
- [ ] **LoopCompleted observer extension** — after 56.2 quota.record_usage + US-1 sla_recorder.record_loop_completion → call `cost_ledger.record_llm_call(tenant_id, provider, model, input_tokens, output_tokens, cached_input_tokens, session_id)`
- [ ] **Use 56.2 LoopCompleted.total_tokens + new fields** — provider / model / input_tokens / output_tokens (per Day 0 verify;若缺 fields,fallback to estimate via Cat 4 ChatClient.count_tokens from messages)
- [ ] **Update file header MHist** — `Sprint 56.3 — wire Cost Ledger LLM hook (US-4 part 1)`
- DoD: existing 56.2 tests still pass

### 3.4 Tool dispatcher event + observer (US-4 tool hook)
- [ ] **Verify Day 0: ToolExecuted event exists?** — if no → add ToolExecuted to `agent_harness/_contracts/events.py`(中性 event)
- [ ] **Modify `agent_harness/orchestrator_loop/tool_dispatcher.py`** — emit ToolExecuted after each tool execute(post-success + post-error)
- [ ] **Chat router ToolExecuted observer** — handle event in `_stream_loop_events`;call `cost_ledger.record_tool_call(tenant_id, tool_name, session_id)`
- [ ] **Update events.py + dispatcher MHist** — `Sprint 56.3 — emit ToolExecuted for Cost Ledger US-4`

### 3.5 2 unit US-3 (CostLedgerService) + 1 integration US-3 + 5 unit US-4 + 1 integration US-4
**Unit US-3 (2)**
- [ ] **test_cost_ledger_service_record_llm_call_writes_2_entries** — assert input + output 2 ledger rows
- [ ] **test_cost_ledger_service_aggregate_groups_by_cost_type** — populate 5 entries;assert aggregate returns dict by cost_type+sub_type with summed total_cost_usd

**Integration US-3 (1)**
- [ ] **test_admin_cost_summary_endpoint_returns_aggregated** — auth as ADMIN_TENANT;populate ledger;assert endpoint returns AggregatedUsageResponse

**Unit US-4 (5)**
- [ ] **test_chat_router_records_llm_cost_on_loop_completed** — mock chat;assert cost_ledger.record_llm_call called with input + output tokens
- [ ] **test_chat_router_records_tool_cost_on_tool_executed** — mock tool exec;assert cost_ledger.record_tool_call called
- [ ] **test_cost_ledger_record_llm_call_uses_cached_pricing_when_cached_input** — cached_input_tokens > 0 → unit_cost_usd uses cached_input_per_million
- [ ] **test_cost_ledger_record_llm_call_per_tenant_scoped** — assert ledger row tenant_id matches request tenant_id (multi-tenant 鐵律 1)
- [ ] **test_tool_executed_event_emitted_post_dispatch** — mock dispatcher;assert ToolExecuted event in stream

**Integration US-4 (1)**
- [ ] **test_chat_request_writes_cost_ledger_end_to_end** — fakeredis + real pg;POST chat → 2 LLM ledger rows + N tool ledger rows visible in cost_ledger table

DoD: 9 tests pass < 8s

### 3.6 Day 3 sanity checks
- [ ] **mypy --strict** — 0 errors
- [ ] **black + isort + flake8** — clean
- [ ] **8 V2 lints via run_all.py** — 8/8 green
- [ ] **Backend full pytest** — 1545 + 9 = 1554 passed
- [ ] **LLM SDK leak** — 0

### 3.7 Day 3 commit + push + progress.md
- [ ] **Stage + commit Day 3** — commit msg `feat(billing, sprint-56-3): CostLedgerService + chat/tool hooks + cost summary endpoint (US-3 close + US-4 close)`
- [ ] **Update progress.md** with Day 3 actuals
- [ ] **Push to origin**

---

## Day 4 — US-5 Closeout Ceremony

### 4.1 Cross-AD e2e integration test
- [ ] **Create `tests/integration/api/test_phase56_3_e2e.py`** — full flow:
  - Provision tenant via 53.4 RBAC POST /admin/tenants(56.1 + 56.2 RBAC)
  - Onboarding(56.1 onboarding API)
  - POST chat with 56.2 quota pre-call estimate + post-call reconcile
  - Assert SLA span recorded by US-1 in Redis sliding window
  - Assert Cost Ledger entries(2 LLM + 0-1 tool)written by US-4 in cost_ledger table
  - Assert all 4 ADs visible end-to-end
- [ ] **Use fakeredis + real pg testcontainer** — match 56.1 + 56.2 e2e pattern
- DoD: 1 test passes < 15s

### 4.2 Final pytest + lint + leak verify
- [ ] **Backend full pytest** — 1554 + 1 (e2e) = 1555 passed
- [ ] **8 V2 lints via run_all.py** — 8/8 green
- [ ] **mypy --strict** — 0 errors
- [ ] **LLM SDK leak** — `grep -rn "^(from |import )(openai|anthropic|agent_framework)" backend/src/agent_harness backend/src/business_domain backend/src/platform_layer backend/src/core` → 0
- [ ] **Anti-pattern checklist 11 項對齐** — review per .claude/rules/anti-patterns-checklist.md

### 4.3 Retrospective
- [ ] **Create `docs/03-implementation/agent-harness-execution/phase-56/sprint-56-3/retrospective.md`** — 6 必答 + sub-sections:
  - **Q1 What Went Well**
  - **Q2 Calibration verify** — `actual_total_hr / 13 = ratio`;若 ∈ [0.85, 1.20] → log mean(56.1=1.00 + 56.3=ratio);若 outside → log AD-Sprint-Plan-7;document delta
  - **Q3 AD-Plan-4-Schema-Grep formal verdict** — 56.1 D26+D27 + 56.3 Day 0 Schema-Grep findings 對比;promote (2-sprint evidence) / drop (56.1 outlier) / keep candidate
  - **Q4 What To Improve**
  - **Q5 Phase 57+ candidate scope** — list options(Citus PoC standalone / DR + WAL streaming / Compliance partial GDPR / Frontend Onboarding Wizard / Stripe月結 / Customer Status Page);user approval required per rolling planning 紀律;**不寫 Phase 57.1 plan task detail**
  - **Q6 Sprint 56.3 Final Stats** — pytest count delta / mypy / V2 lints / LLM SDK leak / 4-5 USs status / 5 ADs closed (4 from 56.x + 1 large multi-domain calibration verify)
- DoD: retrospective.md committed

### 4.4 Memory snapshot
- [ ] **Create `memory/project_phase56_3_sla_monitor_cost_ledger.md`** — Sprint summary + ADs closed + stats + Phase 57+ candidate scope (per memory 規則)
- [ ] **Update MEMORY.md index** — single-line entry for project_phase56_3
- [ ] **Update SITUATION-V2 §9** — Phase 56-58 SaaS Stage 1 progress 2/3 → 3/3
- [ ] **Update root CLAUDE.md** — Phase 56-58 SaaS Stage 1 status closure(per 56.2 closeout pattern)

### 4.5 Open PR + CI green + solo-dev merge
- [ ] **Open PR** — base main;title `Sprint 56.3 — Phase 56+ SaaS Stage 1 3/3: SLA Monitor + Cost Ledger 聯合`;body含 4 USs + 5 ADs closed + Phase 56-58 SaaS Stage 1 closure note + closing 4 ADs from carryover (or applicable subset)
- [ ] **Wait CI green** — 5 active checks(per 53.7 + 55.6 baseline)
- [ ] **Solo-dev squash merge to main** — per solo-dev policy(2026-05-03 review_count=0)
- [ ] **Capture main HEAD post-merge** — for SITUATION-V2 + memory + closeout PR

### 4.6 Closeout PR
- [ ] **Create closeout commit** — SITUATION-V2 §9 + CLAUDE.md + memory + MEMORY.md updates
- [ ] **Open closeout PR** — base main;title `chore(closeout, sprint-56-3): SITUATION + CLAUDE.md + memory sync to Phase 56-58 SaaS Stage 1 3/3`
- [ ] **Solo-dev squash merge** — per solo-dev policy
- [ ] **Capture main HEAD post-closeout** — final reference

### 4.7 Final push + Phase 56-58 SaaS Stage 1 ceremony note
- [ ] **Add ceremony note in progress.md final entry** — Phase 56-58 SaaS Stage 1 backend stack 3/3 ✅(56.1 provision + 56.2 polish + 56.3 monitor & ledger)
- [ ] **List Phase 57+ candidate scope** — Citus PoC / DR / Compliance partial GDPR / Frontend Onboarding Wizard / Stripe月結 / Customer Status Page
- [ ] **Final commit + push** — push final state

---

## Sprint 56.3 Definition of Done(覆核)

- [ ] All 5 USs acceptance criteria met
- [ ] Test count ≥ 1555 (1530 + 25 new)
- [ ] mypy --strict 0 errors
- [ ] 8 V2 lints green (含 check_rls_policies on 3 new tables PASS)
- [ ] LLM SDK leak: 0
- [ ] Anti-pattern checklist 11 項對齐
- [ ] AD-Sprint-Plan-4 `large multi-domain` 2nd application captured + verdict logged
- [ ] AD-Plan-4-Schema-Grep formal evaluation logged in retro Q3 (promote / drop / keep candidate verdict)
- [ ] Cross-AD e2e integration test passed
- [ ] PR opened, CI green (5 active checks), solo-dev merged to main
- [ ] Closeout PR merged
- [ ] SITUATION-V2 + memory + CLAUDE.md updated to **Phase 56-58 SaaS Stage 1 3/3 (Sprint 56.3 closed)**
- [ ] Phase 57+ candidate scope documented in retrospective Q5 (user approval required per rolling planning)
