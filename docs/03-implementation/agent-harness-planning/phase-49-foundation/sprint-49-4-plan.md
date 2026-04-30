# Sprint 49.4 — Adapters + Worker Queue 選型 + OTel + Lint Rules

**建立日期**：2026-04-29
**所屬 Phase**：Phase 49 — Foundation（4 sprint）
**版本**：V1.0
**Sprint 編號**：49.4（Phase 49 第 4 個 / 全 22 sprint 第 4 個 / Phase 49 收尾）
**工作量**：1 週（5 工作天，估 32h）
**Story Points**：32 點
**狀態**：📋 計劃中（待用戶 approve）
**前一 Sprint**：49.3 ✅ DONE（RLS + Audit + Memory + Governance + Qdrant 隔離）
**下一 Sprint**：50.1（範疇 1 + 範疇 6 — 真 ReAct loop 跑通）— Phase 50 Loop Core 啟動

---

## Sprint Goal

> **完成 Phase 49 Foundation 收官四件大事：(A) `adapters/_base/chat_client.py` ABC 補齊 4 個新方法（count_tokens / get_pricing / supports_feature / model_info）+ Azure OpenAI 完整 adapter 實作；(B) Worker queue 選型決策（Celery vs Temporal spike PoC + 決策報告 + agent_loop_worker 框架）；(C) OpenTelemetry tracing + metrics + structured logging 全套整合（Tracer ABC 實作 + Jaeger / Prometheus exporter）；(D) 4 條 Lint rules 上線（duplicate-dataclass / cross-category-import / sync-callback / LLM SDK leak）+ 49.3 carryover 全清（pg_partman extension + postgres image 升級 + Dockerfile + production app_role guide + tool_calls.message_id FK 決策）。**

本 Sprint 完成後：Phase 50.1（真 ReAct loop）進入零阻礙狀態 — adapter 可呼叫 Azure OpenAI、worker 可接任務、OTel 可看 trace、CI lint 全強制、infrastructure 100% 就緒。所有後續 18 個 sprint 業務開發都直接走本 sprint 建好的 ABC + worker + OTel + lint baseline。

**不做**：
- Anthropic / OpenAI adapter（Phase 50+ 接 multi-provider router 時做；本 sprint 只 Azure OpenAI 一家）
- 完整 worker queue 業務邏輯（只 stub agent_loop_worker 框架，loop 本體在 50.1）
- Frontend Vite 啟動（49.1 已建好骨架；本 sprint 不動）
- FastAPI `/chat` endpoint（推到 50.2）
- OTel dashboard 完整 panel（先有 trace + metric exporter 就好；Grafana dashboard 在 Phase 55 production）
- Multi-provider routing 邏輯（Phase 50+）

---

## 前置條件

| 條件 | 狀態 |
|------|------|
| Sprint 49.3 完成（13 RLS tables + audit hash chain + 5 memory + governance）| ✅ |
| `backend/src/adapters/_base/chat_client.py` ABC stub 存在（49.1） | ✅ |
| `backend/src/adapters/azure_openai/` README 存在（49.1） | ✅ |
| `backend/src/agent_harness/observability/_abc.py` Tracer ABC stub（49.1） | ✅ |
| `backend/src/agent_harness/_contracts/` 13 型別檔案就緒（49.1） | ✅ |
| `backend/src/platform_layer/middleware/tenant_context.py`（49.3） | ✅ |
| `10-server-side-philosophy.md` 原則 2 ChatClient ABC 為權威 | ✅ |
| `17-cross-category-interfaces.md` §2.1（ABC 表）+ §1.1（型別表）+ §8.1-8.3（Lint rules） | ✅ |
| `13-deployment-and-devops.md` Worker queue + OTel + Docker 為權威 | ✅ |
| `.claude/rules/adapters-layer.md` ABC 5 原則 + 5 步上架 SOP | ✅ |
| `.claude/rules/llm-provider-neutrality.md` 強制規則（Lint 1-3） | ✅ |
| `.claude/rules/observability-instrumentation.md` 5 處必埋點 | ✅ |
| `.claude/rules/category-boundaries.md` cross-category lint 來源 | ✅ |
| 49.3 retrospective 9 項 carryover 清單就緒 | ✅ |

---

## User Stories

### Story 49.4-1：ChatClient ABC 4 新方法 + 中性型別完整化

**作為** 範疇 4（Token Counter）/ 範疇 8（Cost / Error Handling）/ Phase 50.1 開發者
**我希望** `ChatClient` ABC 在 chat() / stream() 之外補齊 `count_tokens()` / `get_pricing()` / `supports_feature()` / `model_info()` 4 方法 + `PricingInfo` / `ModelInfo` / `StopReason` enum 中性型別
**以便** Phase 50+ 任何範疇都可透過 ABC 取 token 數 / 計費資訊 / 能力支援 / 模型 metadata，無需 import LLM SDK

### Story 49.4-2：Azure OpenAI Adapter 完整實作

**作為** Phase 50.1 主流量開發者
**我希望** `adapters/azure_openai/adapter.py` 完整實作 ChatClient ABC（含 deployment_name vs model_name / tool_calling 格式對應 / error mapping / cancellation 支援）+ Contract Test 套件全綠
**以便** Sprint 50.1 第一行 loop code 可直接拿 Azure adapter 跑通，零阻礙

### Story 49.4-3：Worker Queue 選型決策（Celery vs Temporal）

**作為** Phase 53.1 State Mgmt（HITL pause / resume）開發者 + 平台架構師
**我希望** Celery vs Temporal spike PoC 對比 + 決策報告（latency / 持久化 / re-entrant / Python ergonomics / 運維成本）+ `runtime/workers/agent_loop_worker.py` 框架就位
**以便** Phase 50+ 業務開發直接拿 worker 框架接 agent loop，不再返工 queue 選型

### Story 49.4-4：OpenTelemetry Tracing + Metrics + Logging 整合

**作為** 範疇 12（Observability）owner + 所有 11 範疇開發者
**我希望** `observability/_abc.py` Tracer ABC + OTel SDK 鎖版本實作 + Jaeger（trace） + Prometheus（metric） + 結構化 JSON log + TraceContext propagation 全套整合
**以便** Phase 50+ 業務開發每個範疇按 `observability-instrumentation.md` 5 處必埋點規則埋點時，後端 collector / exporter 立即可收

### Story 49.4-5：4 條 Lint Rules 上線（CI 強制）

**作為** 規劃文件 maintainer + V2 紀律守門人
**我希望** 4 條 Lint rules 全部在 pre-commit + GitHub Actions CI 強制：
1. **duplicate-dataclass-check**（17.md §8.1）— 跨範疇型別重複定義偵測
2. **cross-category-import-check**（17.md §8.2 + category-boundaries.md）— 私有模組跨範疇 import 偵測
3. **sync-callback-check**（17.md §8.3）— async/await 漏寫偵測
4. **LLM SDK direct import check**（llm-provider-neutrality.md）— `agent_harness/**` 禁 import openai / anthropic

**以便** PR review 自動擋反模式，不靠人眼

### Story 49.4-6：49.3 Carryover 清算（5 項）

**作為** Phase 49 收尾 maintainer
**我希望** 49.3 retrospective 列的 5 項基礎設施債務一次性清掉：
1. **pg_partman extension** — postgres image 升級（`postgres:16-alpine` → `postgres:16` full）+ Dockerfile + docker-compose env 調整 + create_parent for messages / message_events / audit_log（p_premake=6）
2. **Production app_role guide** — `13-deployment-and-devops.md` 補一段「生產 app role 必須 NOLOGIN + GRANT CRUD + 不可 BYPASSRLS / SUPERUSER」
3. **`tool_calls.message_id` FK 決策** — composite (id, created_at) FK 嘗試 vs 等 PG 18 partial-partition FK；本 sprint 至少做出決策（不一定要落地）
4. **CI .ini ASCII-only check** — 整合進 cross-category-import-check lint（複用同個 lint script）
5. **State_snapshots STATEMENT TRUNCATE trigger 已在 49.3 補裝** — 本 sprint 只需驗證 + 文件記錄為已清

**以便** Phase 50+ 業務開發無 partition NOW() 撞牆 / 無 SUPERUSER 安全漏洞

### Story 49.4-7：FastAPI 啟動 + `/health` + tenant_context middleware 接入

**作為** Phase 50.2 API endpoint 開發者
**我希望** FastAPI app 真實啟動（uvicorn 跑通）+ `/health` endpoint 200 + 49.3 已建的 `TenantContextMiddleware` 真實接入 app + OTel FastAPI instrumentation 接上
**以便** Phase 50.2 接第一個 `/api/v1/chat` endpoint 時，tenant 注入 + tracing 已是預設行為

### Story 49.4-8：Phase 49 收尾驗收（4/4 sprint complete）

**作為** Phase 49 owner
**我希望** Phase 49 README 更新為 4/4 = 100%、整體基礎設施驗收清單全綠、Phase 50 prerequisites 全部 unblocked、`agent-harness-planning/06-phase-roadmap.md` Phase 49 段落標記為 ✅ DONE
**以便** Phase 50 啟動時所有依賴都明文標示為已就緒

---

## 範疇歸屬

| 工作項 | 範疇 | 文件位置 |
|--------|------|---------|
| ChatClient ABC 4 新方法 + PricingInfo / ModelInfo / StopReason | adapters/_base（跨 LLM provider） | `backend/src/adapters/_base/chat_client.py` + `types.py` + `pricing.py` |
| Azure OpenAI adapter 實作 | adapters/azure_openai | `backend/src/adapters/azure_openai/{adapter,config,error_mapper,tool_converter}.py` |
| Worker queue spike + 決策報告 | infrastructure（Celery vs Temporal） | `docs/03-implementation/agent-harness-execution/phase-49/sprint-49-4/worker-queue-decision.md` |
| `agent_loop_worker.py` 框架 | runtime/workers | `backend/src/runtime/workers/agent_loop_worker.py` |
| Tracer ABC 實作 + OTel SDK 整合 | 範疇 12 Observability | `backend/src/agent_harness/observability/{tracer,metrics,exporter}.py` + `backend/src/platform_layer/observability/` |
| 4 Lint rules（pre-commit + CI） | DevOps / Quality | `scripts/lint/{check_duplicate_dataclass,check_cross_category_import,check_sync_callback,check_llm_sdk_leak}.py` + `.pre-commit-config.yaml` + `.github/workflows/lint.yml` |
| pg_partman + Dockerfile 升級 | DevOps / Infrastructure | `docker/Dockerfile.postgres` + `docker-compose.dev.yml` + 0010 migration |
| FastAPI startup + /health + TenantContextMiddleware 接入 | api / platform_layer | `backend/src/api/main.py` + `api/v1/health.py` |
| Phase 49 收尾文件 | docs | `phase-49-foundation/README.md` + `06-phase-roadmap.md` |

---

## Day-by-Day 計劃

### Day 1（2026-04-30，估 7h）— Adapters: ABC 4 方法 + Azure OpenAI Adapter

**目標**：ChatClient ABC 完整化 + Azure OpenAI 可實際呼叫 + Contract Test 套件就位

**產出**：
- `_base/chat_client.py` 補齊 `count_tokens()` / `get_pricing()` / `supports_feature()` / `model_info()` 4 個 abstract method
- `_base/types.py` 新增 `PricingInfo` / `ModelInfo` dataclass + `StopReason` enum 完整化（END_TURN / TOOL_USE / MAX_TOKENS / STOP_SEQUENCE / SAFETY_REFUSAL / PROVIDER_ERROR）
- `_base/pricing.py` PricingInfo dataclass（input_per_million / output_per_million / cached_input_per_million）
- `azure_openai/adapter.py` AzureOpenAIAdapter 實作 ChatClient ABC 全 6 方法
- `azure_openai/config.py` AzureOpenAIConfig（endpoint / api_version / deployment_name / model_name 區分 + timeout / retry / rate limits）
- `azure_openai/error_mapper.py` AzureOpenAIErrorMapper（native error → ProviderError enum）
- `azure_openai/tool_converter.py` ToolSpec → Azure function calling format 轉換
- `_testing/mock_clients.py` MockChatClient（完整 ABC 實作，供 agent_harness 單元測試用）
- `azure_openai/tests/test_contract.py` Contract test 套件（≥ 7 tests：basic chat / tool calling / count_tokens / pricing / supports_feature / cancellation / error mapping）
- 49.1 staged `chat_client.py` 升級 commit

**驗收**：
- ChatClient ABC 4 新方法全 abstract（無預設實作）
- Azure adapter 可真實呼叫 Azure OpenAI（mock 端 + real env var 兩種測試）
- Contract test ≥ 7 PASS
- mypy strict 通過 / black + isort + flake8 clean
- LLM SDK leak grep：只有 `adapters/azure_openai/` 內部可見 `from openai import` / `import openai`

---

### Day 2（2026-05-01，估 7h）— Worker Queue 選型 Spike + agent_loop_worker 框架

**目標**：Celery vs Temporal 對比實測 + 決策報告 + worker 框架可接任務

**產出**：
- `docs/03-implementation/agent-harness-execution/phase-49/sprint-49-4/worker-queue-decision.md` — 5 軸對比（latency / 持久化 / re-entrant / Python ergonomics / 運維成本）+ 決策（推薦 + 理由 + carry-forward）
- Spike code（不入主 codebase；放 `experimental/` 或 PoC branch）：
  - Celery: 簡單 task + retry + result backend
  - Temporal: 簡單 workflow + activity + checkpoint
  - 兩者都跑「sleep 5s → return result」測延遲 + 持久化（kill worker 後 resume）
- `backend/src/runtime/workers/__init__.py` + `agent_loop_worker.py` 框架 stub（含 ABC interface for queue backend）
- `backend/src/runtime/workers/queue_backend.py` ABC（abstract submit / poll / cancel）
- 4 個 unit test：worker stub + queue ABC + cancel + retry 邏輯（不接實際 broker）
- 49.3 retrospective Action item 9（worker queue 選型）勾掉

**驗收**：
- 決策報告含明確推薦（無「兩家都行」模糊）
- Spike code 可重現執行（README + commands）
- Worker stub framework 通 4 unit test
- 不阻塞 Phase 50.1（loop 框架可走 mock backend）

---

### Day 3（2026-05-02，估 7h）— OpenTelemetry 整合（Tracing + Metrics + Logging）

**目標**：OTel SDK 鎖版本 + Jaeger + Prometheus + structured JSON log + Tracer ABC 可用

**產出**：
- `requirements.txt` 鎖 OTel 版本（opentelemetry-api==1.22.0 / opentelemetry-sdk==1.22.0 / opentelemetry-exporter-jaeger==1.22.0 / opentelemetry-exporter-prometheus==0.43b0 / opentelemetry-instrumentation-fastapi==0.43b0 / opentelemetry-instrumentation-sqlalchemy==0.43b0）
- `backend/src/agent_harness/observability/tracer.py` Tracer ABC 實作（OTelTracer 具體類）
- `backend/src/agent_harness/observability/metrics.py` MetricEvent dataclass + 7 必埋 metric 註冊（agent_loop_duration_seconds / tool_execution_duration_seconds / llm_chat_duration_seconds / llm_tokens_total / verification_pass_rate / loop_compaction_count / loop_subagent_dispatch_count）
- `backend/src/agent_harness/observability/exporter.py` JaegerExporter + PrometheusExporter 配置
- `backend/src/platform_layer/observability/setup.py` OTel global init（FastAPI + SQLAlchemy + Redis instrumentation）
- `backend/src/platform_layer/observability/logger.py` structured JSON log（含 PII redactor）
- `docker-compose.dev.yml` 加 jaeger + prometheus 服務
- 6 unit test：Tracer span hierarchy / TraceContext propagation / MetricEvent emission / JSON log format / PII redaction / OTel SDK init
- `observability-instrumentation.md` 規則對齊驗證（5 處必埋點 hook）

**驗收**：
- `docker-compose up jaeger prometheus` 啟動成功
- Tracer.start_span() → 可在 Jaeger UI 看到 span（手動測試 + 自動測試）
- MetricEvent emit → Prometheus `/metrics` endpoint 可看到
- structured log JSON 格式正確（含 trace_id / tenant_id / timestamp）
- 6 PASS

---

### Day 4（2026-05-03，估 6h）— Lint Rules + pg_partman + Dockerfile 升級

**目標**：4 條 Lint rules 全綠 + pg_partman 真實裝起來 + Dockerfile 升級 + tool_calls FK 決策

**產出**：
- `scripts/lint/check_duplicate_dataclass.py`（17.md §8.1）— scan `agent_harness/**` 找重複 dataclass 定義（@dataclass + class name 唯一性）
- `scripts/lint/check_cross_category_import.py`（17.md §8.2 + category-boundaries.md）— scan `agent_harness/<cat>/` 內部不可 import `agent_harness/<其他 cat>/` 私有模組（只可 import `_contracts/` + 公開 `__init__.py`）
- `scripts/lint/check_sync_callback.py`（17.md §8.3）— AST 檢查 abstract method 簽名 async / 對應 await 不漏
- `scripts/lint/check_llm_sdk_leak.py`（llm-provider-neutrality.md）— grep `agent_harness/**` + `business_domain/**` + `platform_layer/**` 0 個 `from openai` / `import anthropic`
- `.pre-commit-config.yaml` 加 4 條 lint hooks
- `.github/workflows/lint.yml` 新 workflow（CI 強制 4 lint）
- `docker/Dockerfile.postgres` 新建（基於 `postgres:16` full + `apt install postgresql-16-partman`）
- `docker-compose.dev.yml` postgres service 改用 `Dockerfile.postgres`
- `backend/alembic/versions/0010_pg_partman.py` migration（CREATE EXTENSION pg_partman + create_parent for messages / message_events / audit_log，p_premake=6）
- `tool_calls.message_id` FK 決策報告（半頁）— composite FK 嘗試結果 + 結論（接 / 推遲 / 替代）
- 4 Lint rule unit test（每條 rule 一個 PASS test + 一個故意違反 FAIL test）
- pg_partman migration test：alembic upgrade 0010 後 `\d+ messages` 看到 partman config

**驗收**：
- `pre-commit run --all-files` 全綠
- 故意製造 4 種違反，CI 全擋
- `docker-compose up postgres` 啟動 + `\dx pg_partman` 顯示 1.0+
- alembic upgrade 0010 from base 通過
- 8 PASS（4 rule × 2 case）+ 1 partman migration test

---

### Day 5（2026-05-04，估 5h）— FastAPI 啟動 + 49.3 Carryover 清 + Closeout

**目標**：FastAPI app 跑起來 + production app_role 文件 + 全套整合 / 紅綠 / Phase 49 收尾

**產出**：
- `backend/src/api/main.py` FastAPI app 啟動（含 TenantContextMiddleware 接入 + OTel FastAPI instrumentation）
- `backend/src/api/v1/health.py` `/api/v1/health` endpoint（含 DB ping + Redis ping + RabbitMQ ping）
- `13-deployment-and-devops.md` 補一段「§Production App Role」— NOLOGIN + GRANT CRUD + 禁 BYPASSRLS / SUPERUSER + connection string 範例 + Sprint 49.3 ipa_v2 SUPERUSER 教訓
- 全套 alembic cycle from base：upgrade head → downgrade base → upgrade head（驗證 0010 + 0009 + 0001-0008 全可逆）
- 全套 pytest run：49.3 73 + 49.4 新增 ~25 = ~98 PASS / 0 SKIPPED
- 全套 mypy strict / black / isort / flake8 / 4 lint rules clean
- 全套 LLM SDK leak grep：0 in agent_harness + business_domain + platform_layer
- `phase-49-foundation/README.md` 更新（4/4 sprint complete = 100%）
- `06-phase-roadmap.md` Phase 49 標記 ✅ DONE
- `docs/03-implementation/agent-harness-execution/phase-49/sprint-49-4/{progress,retrospective}.md` 收尾
- `sprint-49-4-checklist.md` 全 [x]
- Phase 49 收尾驗收清單（11 範疇 + 範疇 12 全 Level 0 / CI / Lint / OTel / RLS / Audit / Memory 全就緒）
- Closeout commit

**驗收**：
- `uvicorn backend.src.api.main:app` 啟動 + `curl /api/v1/health` 200
- 全套 pytest ~98 PASS / 0 SKIPPED
- 4 lint rules + mypy strict + black + isort + flake8 全清
- Alembic from-zero cycle 通過
- Phase 49 README 4/4 = 100%

---

## Acceptance Criteria（Sprint 級）

- [ ] **AC-1**：ChatClient ABC 6 方法（chat / stream / count_tokens / get_pricing / supports_feature / model_info）全 abstract + Contract Test ≥ 7 PASS
- [ ] **AC-2**：AzureOpenAIAdapter 實作 ABC 全方法 + 真實 Azure OpenAI 呼叫 PASS（env var 注入 OR mock fallback）
- [ ] **AC-3**：Worker queue 決策報告 commit + agent_loop_worker.py 框架 + 4 unit test PASS
- [ ] **AC-4**：OTel SDK 鎖版本 + Jaeger / Prometheus exporter 啟動 + Tracer / MetricEvent emission 6 unit test PASS
- [ ] **AC-5**：4 Lint rules（duplicate-dataclass / cross-category-import / sync-callback / LLM SDK leak）pre-commit + CI 強制 + 8 case test PASS
- [ ] **AC-6**：pg_partman extension 裝起來 + 0010 migration + Dockerfile.postgres 升級
- [ ] **AC-7**：FastAPI app 啟動 + `/health` 200 + TenantContextMiddleware 接入 + OTel FastAPI instrumentation
- [ ] **AC-8**：49.3 carryover 5 項全清（pg_partman / app_role guide / tool_calls FK 決策 / state_snapshots TRUNCATE 已驗證 / .ini lint 整合）
- [ ] **AC-9**：全套 pytest ~98 PASS / 0 SKIPPED / mypy strict / 4 lint clean / LLM SDK leak 0
- [ ] **AC-10**：Phase 49 收尾驗收清單 11 項全 ✅（11 範疇 + 範疇 12 全 Level 0 / CI / Lint / OTel / RLS / Audit / Memory / Worker / Adapter / Multi-tenant 鐵律 / pg_partman 全就緒）

---

## File Change List（預估）

### 新建（~25 檔）

```
backend/src/adapters/_base/types.py                                    (PricingInfo / ModelInfo / StopReason 完整化)
backend/src/adapters/_base/pricing.py                                  (PricingInfo dataclass)
backend/src/adapters/azure_openai/__init__.py
backend/src/adapters/azure_openai/adapter.py                           (AzureOpenAIAdapter)
backend/src/adapters/azure_openai/config.py
backend/src/adapters/azure_openai/error_mapper.py
backend/src/adapters/azure_openai/tool_converter.py
backend/src/adapters/_testing/__init__.py
backend/src/adapters/_testing/mock_clients.py                          (MockChatClient)
backend/src/adapters/_testing/conftest.py
backend/src/runtime/__init__.py
backend/src/runtime/workers/__init__.py
backend/src/runtime/workers/agent_loop_worker.py
backend/src/runtime/workers/queue_backend.py                           (ABC)
backend/src/agent_harness/observability/tracer.py
backend/src/agent_harness/observability/metrics.py
backend/src/agent_harness/observability/exporter.py
backend/src/platform_layer/observability/__init__.py
backend/src/platform_layer/observability/setup.py
backend/src/platform_layer/observability/logger.py
backend/src/api/main.py                                                (FastAPI app)
backend/src/api/v1/health.py                                           (/health endpoint)
backend/alembic/versions/0010_pg_partman.py
docker/Dockerfile.postgres
scripts/lint/check_duplicate_dataclass.py
scripts/lint/check_cross_category_import.py
scripts/lint/check_sync_callback.py
scripts/lint/check_llm_sdk_leak.py
.github/workflows/lint.yml
docs/03-implementation/agent-harness-execution/phase-49/sprint-49-4/worker-queue-decision.md
docs/03-implementation/agent-harness-execution/phase-49/sprint-49-4/progress.md
docs/03-implementation/agent-harness-execution/phase-49/sprint-49-4/retrospective.md
backend/tests/unit/adapters/azure_openai/test_contract.py              (≥ 7 contract tests)
backend/tests/unit/adapters/azure_openai/test_token_counting.py
backend/tests/unit/adapters/azure_openai/test_pricing.py
backend/tests/unit/adapters/azure_openai/test_error_mapper.py
backend/tests/unit/runtime/workers/test_agent_loop_worker.py
backend/tests/unit/agent_harness/observability/test_tracer.py
backend/tests/unit/agent_harness/observability/test_metrics.py
backend/tests/unit/agent_harness/observability/test_logger.py
backend/tests/unit/scripts/lint/test_duplicate_dataclass.py
backend/tests/unit/scripts/lint/test_cross_category_import.py
backend/tests/unit/scripts/lint/test_sync_callback.py
backend/tests/unit/scripts/lint/test_llm_sdk_leak.py
backend/tests/unit/api/test_health.py
backend/tests/unit/infrastructure/db/test_pg_partman.py
```

### 更新（~10 檔）

```
backend/src/adapters/_base/chat_client.py                              (補 4 abstract method)
backend/src/adapters/_base/__init__.py                                 (re-export)
backend/src/adapters/azure_openai/README.md                            (Sprint 49.4 deliverables)
backend/src/runtime/__init__.py
backend/src/agent_harness/observability/__init__.py
backend/src/agent_harness/observability/_abc.py                        (Tracer ABC 完整化)
backend/src/agent_harness/observability/README.md
backend/src/api/__init__.py
backend/src/api/v1/__init__.py
backend/requirements.txt                                               (OTel SDK + Celery / Temporal client lock)
backend/pyproject.toml                                                 (mypy + ruff + new lint scripts)
.pre-commit-config.yaml                                                (4 lint hooks)
docker-compose.dev.yml                                                 (postgres → Dockerfile.postgres / +jaeger / +prometheus)
docs/03-implementation/agent-harness-planning/13-deployment-and-devops.md (補 Production App Role + pg_partman setup)
docs/03-implementation/agent-harness-planning/phase-49-foundation/README.md (4/4 = 100%)
docs/03-implementation/agent-harness-planning/06-phase-roadmap.md      (Phase 49 ✅ DONE)
.claude/rules/observability-instrumentation.md                         (補 OTel 鎖版本實裝對應)
```

---

## Dependencies & Risks

### Dependencies

| 依賴 | 來源 | 風險 |
|------|------|------|
| Azure OpenAI 真實憑證（測試 adapter） | env var `AZURE_OPENAI_*` | 若無憑證 → mock fallback；contract test 仍可跑 |
| `postgres:16` full image（pg_partman） | Docker Hub | 比 alpine 大約 +200MB；接受 |
| OTel SDK 1.22.0 / 0.43b0 版本相容性 | PyPI | 鎖版本；若有 conflict 需降 1.21 / 0.42 |
| Celery 5.4 vs Temporal 1.5（spike 對比） | PyPI / Docker | 兩者都需 broker（Redis / Temporal server） |
| 49.3 已建 RLS + middleware | Sprint 49.3 ✅ DONE | 已就緒 |

### Risks

| 風險 | 機率 | 影響 | 緩解 |
|------|------|------|------|
| **Azure OpenAI 配額 / 限流影響 contract test** | 中 | 中 | Contract test 用 mock；real env test 標 `@pytest.mark.integration` 可選跑 |
| **Worker queue spike 兩家都不滿意 → 第三選項出現** | 低 | 高 | 決策報告先列「為什麼選這兩家對比」+ 留 escape hatch（推遲到 53.1 再選） |
| **OTel SDK 1.22.0 與 SQLAlchemy 2.0 instrumentation 衝突** | 中 | 中 | Day 3 上半天 spike 驗證；若 fail 改用 manual span |
| **pg_partman Dockerfile build 時間 > 2min** | 中 | 低 | 接受；CI cache layer + dev 一次 build 終身用 |
| **4 lint rules false positive 多** | 中 | 中 | 每條 rule 配 `--allow-pattern` config + 漸進嚴格化（first PR warning only / second PR error） |
| **49.3 production app_role guide 引發 dev container 修改需求** | 低 | 低 | 文件化但不強制；dev 仍可用 ipa_v2；production deploy 才換 |
| **tool_calls.message_id FK 決策卡住** | 中 | 低 | 本 sprint 只做決策不要求落地；推延到 PG 18 LTS |

---

## Out of Scope（明確不做）

- ❌ Anthropic / OpenAI adapter（Phase 50+ multi-provider router）
- ❌ Worker 完整業務邏輯（loop 本體在 Sprint 50.1）
- ❌ FastAPI `/api/v1/chat` endpoint（Sprint 50.2）
- ❌ Frontend Vite 整合 OTel browser SDK（Phase 55）
- ❌ Grafana dashboard 完整 panel（Phase 55 production）
- ❌ ProviderRouter 實作（Phase 50+）
- ❌ Multi-provider routing rules（Phase 50+）
- ❌ Production deploy 配置（Phase 55）
- ❌ Branch protection rule（用戶 admin UI；49.1 carryover）
- ❌ npm audit moderate vulnerabilities 修復（49.1 carryover；deferred to frontend sprint）

---

## 驗收與 Definition of Done

完成本 Sprint 必須滿足：

1. ✅ AC-1 ~ AC-10 全綠（10 項驗收標準）
2. ✅ 所有新建 / 修改檔案有 file header + Modification History（per `.claude/rules/file-header-convention.md`）
3. ✅ 11 anti-pattern checklist 全綠（per `.claude/rules/anti-patterns-checklist.md`）
4. ✅ Sprint workflow 5 步全做（plan → checklist → code → update → progress + retrospective）
5. ✅ Multi-tenant rule 鐵律 1+2+3 cross-check（per `.claude/rules/multi-tenant-data.md`；本 sprint 主要是 OTel 不違反）
6. ✅ Observability instrumentation rule 5 處必埋點驗證（per `.claude/rules/observability-instrumentation.md`）
7. ✅ Adapter layer 5 原則 + 5 步上架 SOP 對齊（per `.claude/rules/adapters-layer.md`）
8. ✅ LLM provider neutrality 強制規則（per `.claude/rules/llm-provider-neutrality.md`）
9. ✅ Category boundaries 跨範疇 import 三層規則（per `.claude/rules/category-boundaries.md`）
10. ✅ Phase 49 README 更新為 4/4 = 100%；roadmap Phase 49 ✅ DONE

---

## 引用權威文件

- **06-phase-roadmap.md** §Phase 49.4 — 本 sprint scope 來源
- **10-server-side-philosophy.md** §原則 2 — ChatClient ABC + LLM provider neutrality
- **17-cross-category-interfaces.md** §1.1 / §2.1 / §8.1-8.3 — 型別 / ABC / Lint rules single-source
- **13-deployment-and-devops.md** §Worker queue / OTel / Docker / pg_partman / Production app_role
- **07-tech-stack-decisions.md** — 技術選型（adapter / worker / OTel）
- **01-eleven-categories-spec.md** §範疇 12 Observability — Tracer / MetricEvent / TraceContext
- **.claude/rules/adapters-layer.md** — ABC 5 原則 + 5 步上架 SOP + Azure OpenAI 細節
- **.claude/rules/llm-provider-neutrality.md** — 強制規則（Lint 1-3）
- **.claude/rules/observability-instrumentation.md** — 5 處必埋點 + TraceContext propagation + 7 必埋 metric
- **.claude/rules/category-boundaries.md** — 跨範疇 import 三層規則（Lint 來源）
- **sprint-49-3-retrospective.md** — Carryover 5 項清單

---

**Last Updated**：2026-04-29（Sprint 49.4 plan creation）
**Maintainer**：用戶 + AI 助手共同維護
**Approval Status**：📋 待用戶 approve；approve 後才能 code
