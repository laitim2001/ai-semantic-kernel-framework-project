# Sprint 49.4 — Checklist

[Plan](./sprint-49-4-plan.md)

**Sprint Goal**：完成 Phase 49 收官 — Adapters ABC 4 方法 + Azure OpenAI adapter / Worker queue 選型 + agent_loop_worker / OTel tracing+metrics+logging / 4 Lint rules / pg_partman + Dockerfile / FastAPI 啟動 + 49.3 carryover 全清。

**Total Story Points**：32
**Total Estimated Hours**：32h（5 days × ~6.4h avg）
**Status**：📋 計劃中（待用戶 approve）

---

## Day 1 — Adapters: ABC 4 方法 + Azure OpenAI Adapter（估 7h）

### 1.1 ChatClient ABC 補齊 4 新方法（90 min）
- [ ] **更新 `backend/src/adapters/_base/chat_client.py`** 補齊 4 abstract method
  - 預估：30 min
  - DoD：`count_tokens()` / `get_pricing()` / `supports_feature()` / `model_info()` 全 `@abstractmethod` + type hint 完整 + docstring 含 single-source 引用（17.md §2.1 + 10.md 原則 2）
  - Command：`mypy backend/src/adapters/_base/chat_client.py --strict`
- [ ] **建 `backend/src/adapters/_base/types.py`** 補完中性型別
  - 預估：30 min
  - DoD：`PricingInfo` / `ModelInfo` dataclass + `StopReason` enum 完整化（END_TURN / TOOL_USE / MAX_TOKENS / STOP_SEQUENCE / SAFETY_REFUSAL / PROVIDER_ERROR）+ frozen=True
  - Command：`pytest backend/tests/unit/adapters/_base/test_types.py -v`（後建）
- [ ] **建 `backend/src/adapters/_base/pricing.py`** PricingInfo 完整
  - 預估：15 min
  - DoD：input_per_million / output_per_million / cached_input_per_million 三欄位 + supports_caching bool + currency='USD'
- [ ] **更新 `backend/src/adapters/_base/__init__.py`** re-export 全新型別
  - 預估：15 min
  - DoD：`from adapters._base import ChatClient, PricingInfo, ModelInfo, StopReason` 可用

### 1.2 Azure OpenAI Adapter 實作（180 min）
- [ ] **建 `backend/src/adapters/azure_openai/config.py`** AzureOpenAIConfig
  - 預估：30 min
  - DoD：endpoint / api_version / deployment_name / model_name 區分 + timeout_sec / max_retries / retry_backoff_factor / rpm_limit / tpm_limit 全欄位 + Pydantic Settings 接 env
- [ ] **建 `backend/src/adapters/azure_openai/error_mapper.py`** AzureOpenAIErrorMapper
  - 預估：30 min
  - DoD：8+ Azure native error → ProviderError enum 映射（AUTH_FAILED / RATE_LIMITED / QUOTA_EXCEEDED / MODEL_UNAVAILABLE / CONTEXT_WINDOW_EXCEEDED / INVALID_REQUEST / TIMEOUT / SERVICE_UNAVAILABLE / UNKNOWN）
- [ ] **建 `backend/src/adapters/azure_openai/tool_converter.py`** ToolSpec → Azure 格式
  - 預估：30 min
  - DoD：ToolSpec → `{"type": "function", "function": {"name", "description", "parameters"}}` 轉換 + 反向 Azure tool_calls → ToolCall 解析
- [ ] **建 `backend/src/adapters/azure_openai/adapter.py`** AzureOpenAIAdapter
  - 預估：90 min
  - DoD：實作 ChatClient ABC 全 6 方法（chat / stream / count_tokens / get_pricing / supports_feature / model_info）+ tiktoken 接 count_tokens + cancellation 支援（asyncio.CancelledError → cleanup）+ trace_context 注入 + structured log
  - Command：`pytest backend/tests/unit/adapters/azure_openai/ -v`

### 1.3 Mock Client + Contract Test（120 min）
- [ ] **建 `backend/src/adapters/_testing/mock_clients.py`** MockChatClient
  - 預估：30 min
  - DoD：實作 ChatClient ABC 全方法 + 可注入 responses dict + count_tokens 硬編值
- [ ] **建 `backend/src/adapters/_testing/conftest.py`** 共用 fixture
  - 預估：15 min
  - DoD：mock_chat_client fixture + azure_adapter fixture（接 env var 或 mock）
- [ ] **建 `backend/tests/unit/adapters/azure_openai/test_contract.py`** ≥ 7 contract tests
  - 預估：60 min
  - DoD：test_chat_basic / test_tool_calling / test_count_tokens / test_pricing_info / test_supports_feature / test_model_info / test_cancellation 全 PASS
  - Command：`pytest backend/tests/unit/adapters/azure_openai/test_contract.py -v`
- [ ] **建 `backend/tests/unit/adapters/azure_openai/test_token_counting.py`** + `test_pricing.py` + `test_error_mapper.py`
  - 預估：15 min
  - DoD：token counting 對 gpt-5.4 模型準確 / pricing 對 USD-per-1M / error mapper 8 case 全 PASS

### 1.4 Day 1 收尾（30 min）
- [ ] **mypy strict + black + isort + flake8** 全綠
  - 預估：10 min
  - Command：`cd backend && black src/adapters && isort src/adapters && flake8 src/adapters && mypy src/adapters --strict`
- [ ] **LLM SDK leak grep 驗證**：openai / anthropic 只在 `adapters/azure_openai/` 內可見
  - 預估：5 min
  - Command：`grep -r "from openai\|import openai" backend/src/agent_harness backend/src/business_domain backend/src/platform_layer | grep -v __pycache__` → 0
- [ ] **Day 1 commit**：`feat(adapters-azure-openai, sprint-49-4): Day 1 ChatClient ABC 4 methods + Azure OpenAI adapter + 7 contract tests`
  - 預估：15 min

---

## Day 2 — Worker Queue 選型 Spike + agent_loop_worker 框架（估 7h）

### 2.1 Celery Spike（90 min）
- [ ] **建 spike branch / experimental folder**：`experimental/spike-celery/`
  - 預估：5 min
- [ ] **Celery + Redis broker setup**：簡單 task + retry + result backend
  - 預估：45 min
  - DoD：sleep 5s → return result；測延遲 + 持久化（kill worker resume from checkpoint）
- [ ] **Celery 量化指標**：latency P50 / P99、kill-worker resume 行為、Python ergonomics 評分（1-5）
  - 預估：40 min

### 2.2 Temporal Spike（90 min）
- [ ] **Temporal server + Python SDK setup**
  - 預估：30 min
- [ ] **Temporal workflow + activity**：sleep 5s → return result + checkpoint
  - 預估：45 min
  - DoD：kill worker → workflow 從 checkpoint resume；timer / signal / workflow vs activity 區分清楚
- [ ] **Temporal 量化指標**：latency / 持久化 / re-entrant / Python ergonomics
  - 預估：15 min

### 2.3 決策報告（90 min）
- [ ] **建 `docs/03-implementation/agent-harness-execution/phase-49/sprint-49-4/worker-queue-decision.md`**
  - 預估：60 min
  - DoD：5 軸對比表（latency / 持久化 / re-entrant / Python ergonomics / 運維成本） + 推薦（含理由 + 反方論點）+ carry-forward 條件（什麼情況需重新評估）
- [ ] **49.3 retrospective Action item 9 勾掉**（worker queue 選型 PoC）
  - 預估：5 min
  - DoD：retrospective.md Action item 9 標 ✅ + 連結決策報告

### 2.4 agent_loop_worker 框架（90 min）
- [ ] **建 `backend/src/runtime/__init__.py` + `backend/src/runtime/workers/__init__.py`**
  - 預估：10 min
- [ ] **建 `backend/src/runtime/workers/queue_backend.py`** ABC
  - 預估：30 min
  - DoD：QueueBackend ABC（abstract submit / poll / cancel / get_status）+ MockQueueBackend 實作（in-memory）
- [ ] **建 `backend/src/runtime/workers/agent_loop_worker.py`** stub
  - 預估：45 min
  - DoD：AgentLoopWorker 類 + accept QueueBackend in init + run() async loop（poll task → execute stub → result）+ cancellation + retry policy stub
- [ ] **建 `backend/tests/unit/runtime/workers/test_agent_loop_worker.py`** 4 unit tests
  - 預估：35 min
  - DoD：test_worker_init / test_worker_poll_and_execute / test_worker_cancel / test_worker_retry 全 PASS
  - Command：`pytest backend/tests/unit/runtime/workers/ -v`

### 2.5 Day 2 收尾（30 min）
- [ ] **mypy + lint + tests 全綠**
  - 預估：10 min
- [ ] **Day 2 commit**：`feat(workers, sprint-49-4): Day 2 worker queue selection (Celery vs Temporal) + agent_loop_worker framework`
  - 預估：15 min

---

## Day 3 — OpenTelemetry 整合（Tracing + Metrics + Logging）（估 7h）

### 3.1 OTel SDK 鎖版本 + dependency（30 min）
- [ ] **更新 `backend/requirements.txt`** 鎖 OTel SDK 版本
  - 預估：15 min
  - DoD：opentelemetry-api==1.22.0 / opentelemetry-sdk==1.22.0 / opentelemetry-exporter-jaeger==1.22.0 / opentelemetry-exporter-prometheus==0.43b0 / opentelemetry-exporter-otlp==1.22.0 / opentelemetry-instrumentation-fastapi==0.43b0 / opentelemetry-instrumentation-sqlalchemy==0.43b0 / opentelemetry-instrumentation-redis==0.43b0
  - Command：`pip install -r backend/requirements.txt`
- [ ] **更新 `docker-compose.dev.yml`** 加 jaeger + prometheus 服務
  - 預估：15 min
  - DoD：jaeger:1.55（4317 OTLP / 16686 UI） + prometheus:v2.50（9090）+ depends_on 配置
  - Command：`docker compose up -d jaeger prometheus`

### 3.2 Tracer ABC 實作（90 min）
- [ ] **更新 `backend/src/agent_harness/observability/_abc.py`** Tracer ABC 完整化
  - 預估：30 min
  - DoD：Tracer ABC（start_span / set_attribute / record_metric / set_status / end）+ Span dataclass + signature 對齊 17.md §Contract 12
- [ ] **建 `backend/src/agent_harness/observability/tracer.py`** OTelTracer 具體類
  - 預估：60 min
  - DoD：實作 Tracer ABC + 包 OTel SDK + TraceContext propagation（trace_id / span_id / parent_span_id / tenant_id 沿鏈）+ context manager support

### 3.3 MetricEvent + 7 必埋 metric（90 min）
- [ ] **建 `backend/src/agent_harness/observability/metrics.py`** MetricEvent + registrar
  - 預估：60 min
  - DoD：MetricEvent dataclass（name / value / labels / timestamp）+ MetricRegistry 註冊 7 必埋 metric（agent_loop_duration_seconds / tool_execution_duration_seconds / llm_chat_duration_seconds / llm_tokens_total / verification_pass_rate / loop_compaction_count / loop_subagent_dispatch_count）+ histogram / counter / gauge 三類
- [ ] **建 `backend/src/agent_harness/observability/exporter.py`** Jaeger + Prometheus exporter
  - 預估：30 min
  - DoD：JaegerExporter（trace → :4317 OTLP）+ PrometheusExporter（metric → /metrics endpoint）+ ENV var 切換 console / real exporter

### 3.4 Platform 層 OTel setup + JSON Logger（90 min）
- [ ] **建 `backend/src/platform_layer/observability/__init__.py`**
  - 預估：5 min
- [ ] **建 `backend/src/platform_layer/observability/setup.py`** OTel global init
  - 預估：45 min
  - DoD：setup_opentelemetry(app) 函數 + FastAPI instrumentation + SQLAlchemy instrumentation + Redis instrumentation + global tracer / meter provider 註冊
- [ ] **建 `backend/src/platform_layer/observability/logger.py`** structured JSON logger
  - 預估：40 min
  - DoD：JSON formatter + PIIRedactor（email / phone / SSN regex）+ trace_id 自動注入 + tenant_id label

### 3.5 Tests + 對齊驗證（90 min）
- [ ] **建 `backend/tests/unit/agent_harness/observability/test_tracer.py`** 3 tests
  - 預估：30 min
  - DoD：test_span_hierarchy / test_trace_context_propagation / test_attribute_set 全 PASS
- [ ] **建 `backend/tests/unit/agent_harness/observability/test_metrics.py`** 2 tests
  - 預估：20 min
  - DoD：test_metric_emission / test_7_required_metrics_registered 全 PASS
- [ ] **建 `backend/tests/unit/agent_harness/observability/test_logger.py`** 1 test
  - 預估：20 min
  - DoD：test_json_format_and_pii_redaction PASS
- [ ] **手動驗證 Jaeger UI**：`curl /api/v1/health` → Jaeger UI :16686 看到 span（hookup 在 Day 5）
  - 預估：20 min（部分推 Day 5）

### 3.6 Day 3 收尾（30 min）
- [ ] **mypy + lint + tests 全綠**
  - 預估：10 min
- [ ] **`.claude/rules/observability-instrumentation.md` 對齊驗證**：5 處必埋點 + 7 必埋 metric + TraceContext 規範對齊
  - 預估：5 min
- [ ] **Day 3 commit**：`feat(observability, sprint-49-4): Day 3 OpenTelemetry tracing+metrics+logging integration + Tracer ABC + 7 metrics + JSON logger`
  - 預估：15 min

---

## Day 4 — Lint Rules + pg_partman + Dockerfile 升級（估 6h）

### 4.1 Lint Rule 1: duplicate-dataclass-check（45 min）
- [ ] **建 `scripts/lint/check_duplicate_dataclass.py`**
  - 預估：30 min
  - DoD：AST scan `agent_harness/**/*.py` 找 `@dataclass` + class name；同名跨目錄報 ERROR；輸出 file:line + 衝突清單
- [ ] **建 `backend/tests/unit/scripts/lint/test_duplicate_dataclass.py`** 2 tests
  - 預估：15 min
  - DoD：test_no_duplicate（PASS）+ test_with_duplicate（FAIL with explicit message）

### 4.2 Lint Rule 2: cross-category-import-check（60 min）
- [ ] **建 `scripts/lint/check_cross_category_import.py`**
  - 預估：45 min
  - DoD：AST scan `agent_harness/<cat>/` 內 import；禁止 `from agent_harness.<其他 cat>.{私有模組}` 直接 import；只允許 `_contracts/` + `<cat>/__init__.py` 公開 re-export；含 `--allow-pattern` 配置
- [ ] **建 `backend/tests/unit/scripts/lint/test_cross_category_import.py`** 2 tests
  - 預估：15 min
  - DoD：test_legal_import（PASS）+ test_illegal_private_import（FAIL）

### 4.3 Lint Rule 3: sync-callback-check（45 min）
- [ ] **建 `scripts/lint/check_sync_callback.py`**
  - 預估：30 min
  - DoD：AST scan ABC subclass；abstract method 是 async → 子類必須 async + 對應 await；漏寫報 ERROR
- [ ] **建 `backend/tests/unit/scripts/lint/test_sync_callback.py`** 2 tests
  - 預估：15 min
  - DoD：test_async_method_with_await（PASS）+ test_sync_method_overriding_async_abc（FAIL）

### 4.4 Lint Rule 4: LLM SDK leak check（30 min）
- [ ] **建 `scripts/lint/check_llm_sdk_leak.py`**
  - 預估：15 min
  - DoD：grep `agent_harness/**` + `business_domain/**` + `platform_layer/**` 0 個 `from openai` / `import anthropic`；只允許 `adapters/<provider>/` 內可見
- [ ] **建 `backend/tests/unit/scripts/lint/test_llm_sdk_leak.py`** 2 tests
  - 預估：15 min
  - DoD：test_no_sdk_in_agent_harness（PASS）+ test_sdk_outside_adapter（FAIL）

### 4.5 Pre-commit + CI 整合（30 min）
- [ ] **更新 `.pre-commit-config.yaml`** 加 4 條 lint hooks
  - 預估：15 min
  - DoD：4 hooks 全 local + pass_filenames + always_run
  - Command：`pre-commit run --all-files`
- [ ] **建 `.github/workflows/lint.yml`** CI workflow
  - 預估：15 min
  - DoD：on pull_request + 4 lint scripts 順序跑 + fail-fast

### 4.6 pg_partman + Dockerfile 升級（90 min）
- [ ] **建 `docker/Dockerfile.postgres`** 基於 postgres:16 full
  - 預估：30 min
  - DoD：FROM postgres:16（不是 alpine）+ apt install postgresql-16-partman + initial config + 標明 image size 預期 +200MB
- [ ] **更新 `docker-compose.dev.yml`** postgres 用 Dockerfile.postgres
  - 預估：15 min
  - DoD：build context + Dockerfile 路徑 + 保留現有 env / volume / network
- [ ] **建 `backend/alembic/versions/0010_pg_partman.py`** migration
  - 預估：30 min
  - DoD：CREATE EXTENSION pg_partman + create_parent for messages / message_events / audit_log（p_premake=6）+ downgrade DROP
  - Command：`docker compose up -d postgres && alembic upgrade head && psql -c '\dx pg_partman'`
- [ ] **建 `backend/tests/unit/infrastructure/db/test_pg_partman.py`** 1 test
  - 預估：15 min
  - DoD：test_pg_partman_extension_loaded + test_partman_premake_6_partitions PASS

### 4.7 tool_calls.message_id FK 決策（30 min）
- [ ] **嘗試 composite FK**：(message_id, message_created_at) FK to messages(id, created_at)
  - 預估：15 min
  - DoD：alembic revision + 測試是否通過 PG 16 partition table FK 限制
- [ ] **建決策報告**（半頁，整合進 worker-queue-decision.md 同 sprint-49-4 folder）
  - 預估：10 min
  - DoD：FK 決策（接 / 推遲 / 替代方案）+ 寫入 carryover 列表
- [ ] **49.3 retrospective Action item 4（tool_calls.message_id FK）勾掉**（標 ✅ 或 🚧 + 引用決策報告）
  - 預估：5 min

### 4.8 Day 4 收尾（30 min）
- [ ] **`pre-commit run --all-files` 全綠**
  - 預估：10 min
- [ ] **手動製造 4 種違反，CI 全擋驗證**
  - 預估：5 min
- [ ] **Day 4 commit**：`feat(ci, sprint-49-4): Day 4 4 lint rules (duplicate-dataclass / cross-category-import / sync-callback / LLM SDK leak) + pg_partman + Dockerfile.postgres + 0010 migration + tool_calls.message_id FK decision`
  - 預估：15 min

---

## Day 5 — FastAPI 啟動 + 49.3 Carryover 清 + Phase 49 Closeout（估 5h）

### 5.1 FastAPI app + /health（90 min）
- [ ] **建 `backend/src/api/main.py`** FastAPI app
  - 預估：45 min
  - DoD：FastAPI() 實例 + TenantContextMiddleware（49.3 已建）接入 + setup_opentelemetry(app)（Day 3）接入 + lifespan（startup / shutdown）+ logger.info("FastAPI app started")
- [ ] **建 `backend/src/api/v1/__init__.py`** + `backend/src/api/v1/health.py` /health endpoint
  - 預估：30 min
  - DoD：GET /api/v1/health 200 + 含 DB ping + Redis ping + RabbitMQ ping（用 anyio.to_thread.run_sync 避免 blocking）+ 結構化 JSON response
- [ ] **建 `backend/tests/unit/api/test_health.py`** 2 tests
  - 預估：15 min
  - DoD：test_health_200 + test_health_db_ping_included PASS
  - Command：`pytest backend/tests/unit/api/test_health.py -v`

### 5.2 Production app_role 文件（30 min）
- [ ] **更新 `13-deployment-and-devops.md`** 補 §Production App Role
  - 預估：30 min
  - DoD：「生產 app_role 必須 NOLOGIN + GRANT CRUD（不可 ALL / SUPERUSER / BYPASSRLS）」+ connection string 範例 + Sprint 49.3 ipa_v2 SUPERUSER 教訓 + 49.3 retrospective Action item 2 引用
- [ ] **49.3 retrospective Action item 2（生產 app_role）勾掉** ✅
  - 預估：5 min（含 above）

### 5.3 全套整合 / 紅綠（90 min）
- [ ] **`uvicorn backend.src.api.main:app --reload --host 0.0.0.0 --port 8000` 啟動驗證**
  - 預估：15 min
  - Command：`curl http://localhost:8000/api/v1/health` → 200 + DB/Redis/MQ 全 ✅
- [ ] **Jaeger UI 手動驗證**：`curl /api/v1/health` 後 Jaeger UI :16686 看到 health span
  - 預估：10 min
- [ ] **Prometheus 手動驗證**：`curl http://localhost:8000/metrics` 看到 7 metrics
  - 預估：10 min
- [ ] **全套 alembic from-zero cycle**：downgrade base → upgrade head（驗 0010 + 0009 + 0001-0008 全可逆）
  - 預估：15 min
- [ ] **全套 pytest run**：49.3 73 + 49.4 新增 ~25 = ~98 PASS / 0 SKIPPED
  - 預估：20 min
- [ ] **全套 mypy strict / black / isort / flake8 / 4 lint rules / pre-commit 全綠**
  - 預估：15 min
- [ ] **LLM SDK leak grep 驗證**：`agent_harness + business_domain + platform_layer` 全 0 import
  - 預估：5 min

### 5.4 49.3 Carryover 5 項驗證 + 標完成（30 min）
- [ ] **(1) pg_partman extension** ✅ — 0010 migration 通過 + extension 裝起來
- [ ] **(2) Production app_role guide** ✅ — 13.md §Production App Role 已寫
- [ ] **(3) tool_calls.message_id FK 決策** ✅ / 🚧 — 決策報告 commit
- [ ] **(4) CI .ini ASCII-only check** ✅ — 整合進 cross-category-import-check（複用同 lint）
- [ ] **(5) state_snapshots STATEMENT TRUNCATE** ✅ — 49.3 已補裝 + 本 sprint 驗證 alembic cycle 通過
- [ ] **49.3 retrospective Action items 全部勾掉**（updates 49.3 retrospective.md）
  - 預估：30 min（含 above 5 項）

### 5.5 Phase 49 收尾文件（60 min）
- [ ] **建 `docs/03-implementation/agent-harness-execution/phase-49/sprint-49-4/progress.md`**
  - 預估：20 min
  - DoD：5 days estimate vs actual + ratio + daily highlights + surprises 列表
- [ ] **建 `docs/03-implementation/agent-harness-execution/phase-49/sprint-49-4/retrospective.md`**
  - 預估：20 min
  - DoD：what went well / what surprised / improvements / Action items for Phase 50.1 / Approvals & sign-off
- [ ] **更新 `phase-49-foundation/README.md`** 4/4 = 100%
  - 預估：10 min
  - DoD：Sprint 49.4 標 ✅ DONE + 累計交付（4/4 sprint）+ Phase 49 結束驗收 11 項全 ✅ + Phase 50.1 prerequisites unblocked 列表
- [ ] **更新 `06-phase-roadmap.md`** Phase 49 標 ✅ DONE
  - 預估：10 min
  - DoD：Phase 49 標題 + 各 Sprint 49.1-49.4 全 ✅ + 累計 4/22 sprint = 18.2%

### 5.6 Sprint Checklist + Closeout commit（30 min）
- [ ] **本 checklist 全 [x]**（or 🚧 + 理由）
  - 預估：10 min
- [ ] **Day 5 closeout commit**：`docs(sprint-49-4, phase-49): Phase 49 Foundation closeout — 4/4 sprint complete + ~98 tests + 4 lint rules + OTel + pg_partman + FastAPI /health`
  - 預估：20 min

---

## Sprint Acceptance Criteria（Final Validation）

執行 closeout commit 前必須全 ✅：

- [ ] **AC-1**：ChatClient ABC 6 方法全 abstract + Contract Test ≥ 7 PASS
- [ ] **AC-2**：AzureOpenAIAdapter 實作 ABC + 真實 Azure OpenAI 呼叫 PASS（or mock fallback）
- [ ] **AC-3**：Worker queue 決策報告 + agent_loop_worker 框架 + 4 unit test PASS
- [ ] **AC-4**：OTel SDK 鎖版本 + Jaeger / Prometheus exporter + Tracer / MetricEvent / Logger 6 unit test PASS
- [ ] **AC-5**：4 Lint rules pre-commit + CI 強制 + 8 case test PASS
- [ ] **AC-6**：pg_partman 裝起來 + 0010 migration + Dockerfile.postgres
- [ ] **AC-7**：FastAPI app 啟動 + /health 200 + TenantContextMiddleware + OTel instrumentation
- [ ] **AC-8**：49.3 carryover 5 項全清
- [ ] **AC-9**：~98 PASS / 0 SKIPPED / mypy strict / 4 lint clean / LLM SDK leak 0
- [ ] **AC-10**：Phase 49 收尾 4/4 = 100% + roadmap Phase 49 ✅ DONE + Phase 50.1 prerequisites unblocked

---

## Anti-Pattern Checklist（PR review 前自檢）

- [ ] **AP-1** — 不是 Pipeline 偽裝 Loop（本 sprint 無 LLM loop；adapter 層不適用）N/A
- [ ] **AP-2** — 不是 side-track（adapter / worker / OTel / lint 全主流量必需）✅
- [ ] **AP-3** — 不跨目錄散落（adapters/azure_openai 集中 / observability 集中 / lint 在 scripts/lint/）✅
- [ ] **AP-4** — 不是 Potemkin（每個交付都有 unit test + 主流量驗證 hookup）✅
- [ ] **AP-5** — 不是無計畫 PoC（worker queue spike 有 deadline + 決策報告）✅
- [ ] **AP-6** — 沒有「為未來預留」抽象（不接 Anthropic / OpenAI adapter；只實作真實使用）✅
- [ ] **AP-7** — 處理 context rot（本 sprint 無長對話；不適用）N/A
- [ ] **AP-8** — 透過 PromptBuilder（本 sprint 無 LLM 呼叫；不適用）N/A
- [ ] **AP-9** — 有 verification（本 sprint 無 agent 輸出；不適用）N/A
- [ ] **AP-10** — Mock 與 real 同 ABC（MockChatClient + AzureOpenAIAdapter 都繼承 ChatClient ABC）✅
- [ ] **AP-11** — 無版本後綴 + 命名一致（無 `_v1` / `_v2`；adapter / worker / observability 命名一致）✅

---

**Last Updated**：2026-04-29（Sprint 49.4 checklist creation）
**Maintainer**：用戶 + AI 助手共同維護
