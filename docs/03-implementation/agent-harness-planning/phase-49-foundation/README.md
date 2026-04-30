# Phase 49 — Foundation

**Phase 進度**：Sprint 49.4 ✅ DONE — **4 / 4 sprint complete**（**100%**）
**啟動日期**：2026-04-28
**完成日期**：2026-04-29
**狀態**：✅ Phase 49 DONE — Phase 50.1 prerequisites unblocked

---

## Phase 49 目標

> 建立 V2 完整骨架（不寫業務邏輯）：CI / DB / RLS / Workers / Adapters / OTel + Lint。
> 所有後續 18 個 sprint 都依賴本 Phase 完成。

詳細路線圖見 [`../06-phase-roadmap.md` §Phase 49](../06-phase-roadmap.md#phase-49-foundation4-sprint-原-3)。

---

## Sprint 進度總覽

| Sprint | 狀態 | 主題 | 完成日期 | Branch / Commits |
|--------|------|------|---------|------------------|
| **49.1** | ✅ DONE | V1 封存 + V2 目錄骨架 + CI Pipeline | 2026-04-29 | `feature/phase-49-sprint-1-v2-foundation`（13 commits）|
| **49.2** | ✅ DONE | DB Schema + Async ORM 核心 | 2026-04-29 | `feature/phase-49-sprint-2-db-orm`（7 commits）|
| **49.3** | ✅ DONE | RLS + Audit Append-Only + Memory + Qdrant 隔離 | 2026-04-29 | `feature/phase-49-sprint-3-rls-audit-memory`（7 commits）|
| **49.4** | ✅ DONE | Adapters + Worker Queue + OTel + Lint Rules | 2026-04-29 | `feature/phase-49-sprint-4-adapters-otel-lint`（6 commits + closeout）|

---

## Sprint 文件導航

```
phase-49-foundation/
├── README.md                          ← (this file) Phase 49 入口
├── sprint-49-1-plan.md                ✅ DONE
├── sprint-49-1-checklist.md           ✅ DONE
├── sprint-49-2-plan.md                ✅ DONE
├── sprint-49-2-checklist.md           ✅ DONE
├── sprint-49-3-plan.md                ✅ DONE
├── sprint-49-3-checklist.md           ✅ DONE
├── sprint-49-4-plan.md                ✅ DONE
└── sprint-49-4-checklist.md           ✅ DONE
```

執行紀錄：
```
docs/03-implementation/agent-harness-execution/phase-49/
├── sprint-49-1/{progress,retrospective}.md + artifacts/
├── sprint-49-2/{progress,retrospective}.md
├── sprint-49-3/{progress,retrospective}.md
└── sprint-49-4/{progress,retrospective,worker-queue-decision,tool-calls-message-id-fk-decision}.md
```

---

## Phase 49 累計交付（4/4 sprint complete = 100%）

### Sprint 49.1 ✅
- V1 (Phase 1-48) → `archived/v1-phase1-48/`（READ-ONLY；tag `v1-final-phase48`）
- V2 backend 5 層骨架 + 11+1 ABC 全部可 import
- `_contracts/` single-source 跨範疇型別包
- `ChatClient` ABC（`adapters/_base/`）
- `HITLManager` ABC（中央化）
- V2 frontend 骨架（React 18 + Vite 5 + Zustand + ESLint flat）
- `docker-compose.dev.yml`（postgres / redis / rabbitmq / qdrant）
- GitHub Actions CI（backend-ci.yml + frontend-ci.yml + PR template）

### Sprint 49.2 ✅
- Alembic 系統 + 4 migrations（identity / sessions partition / tools / state）
- 13 ORM models + 1 mixin（TenantScopedMixin 強制鐵律 1）
- `engine.py` + `session.py` + `exceptions.py` 含 `StateConflictError`
- StateVersion 雙因子（counter + content_hash）樂觀鎖
- state_snapshots append-only trigger
- 3 個月 partition Day 1（messages + message_events × 2026-04/05/06）
- 29 unit tests + real docker compose PostgreSQL（AP-10 對策）
- CI 升級：spin up postgres service + alembic step + 嚴格 flake8

### Sprint 49.3 ✅
- Audit log append-only + hash chain（ROW UPDATE/DELETE + STATEMENT TRUNCATE）
- 5 layer memory schema（system / tenant / role / user / session_summary）
- API auth + quotas（api_keys + rate_limits）
- Governance（approvals + risk_assessments + guardrail_events）
- RLS policies on 13 tenant-scoped tables（26 policies；ENABLE + FORCE）
- platform_layer/middleware first launch：TenantContextMiddleware + get_db_session_with_tenant
- QdrantNamespaceStrategy（per-tenant collection + payload filter；client integration → 51.2）
- 紅隊 6 攻擊向量驗證 0 leak（AC-10 acceptance suite）
- 73 unit + security tests，0 SKIPPED

### Sprint 49.4 ✅
- ChatClient ABC 6 methods 完整化（count_tokens / get_pricing / supports_feature / model_info）
- AzureOpenAIAdapter 完整實作（lazy openai/tiktoken / cancellation / stream / 5-row finish_reason mapping）
- `_base/types.py` + `pricing.py` + `errors.py`（PricingInfo / ModelInfo / ProviderError / AdapterException）
- MockChatClient（test double sharing same ABC — AP-10）
- 41 contract tests
- Worker queue 選型決策：**Temporal**（5-axis 對比；HITL pause/resume = decisive）
- runtime/workers/queue_backend.py（QueueBackend ABC + MockQueueBackend）+ agent_loop_worker.py stub
- OpenTelemetry 整合：NoOpTracer + OTelTracer + 7 必埋 metrics + Jaeger + Prometheus
- platform_layer/observability/setup.py + JSON logger（PII redaction + auto trace_id 注入）
- 4 V2 lint rules：duplicate-dataclass / cross-category-import / sync-callback / LLM SDK leak
- pre-commit + GitHub Actions CI workflow lint.yml
- pg_partman extension（Dockerfile.postgres + 0010 migration with graceful skip）
- tool_calls.message_id FK 決策：DEFER 至 PG 18 LTS
- FastAPI `api/main.py` + `/api/v1/health` + `/api/v1/health/ready`（DB ping）
- Production App Role guide（NOLOGIN + GRANT CRUD + SUPERUSER/BYPASSRLS 警報）
- 49.3 retrospective 5/9 Action items RESOLVED
- 143 PASS / 0 SKIPPED 全套 unit suite（70 new in 49.4 + 73 from 49.3）

---

## Phase 49 結束驗收（依 06-phase-roadmap.md）

完成 49.4 後達到：
- ✅ 整體基礎設施 100% 就緒
- ✅ CI / Lint（4 V2 rules）/ OTel（Tracer + 7 metrics + Jaeger + Prometheus）全部上線
- ✅ DB schema 完整（13 RLS tables + audit hash chain + 5 memory + governance + pg_partman）
- ✅ 多租戶隔離 baseline 紅隊驗證 0 leak
- ✅ ChatClient ABC + Azure OpenAI adapter ready for Phase 50.1 wiring
- ✅ Worker framework + Temporal decision ready for Phase 53.1
- ✅ FastAPI app + /health + middleware + OTel instrumentation
- ✅ 11 範疇 + 範疇 12 成熟度全部 Level 0（合理 — 還沒實作；50.1 起進 Level 1+）
- ✅ 接下來可開始實作範疇

---

## Phase 50.1 Prerequisites — UNBLOCKED

- ✅ ChatClient ABC + AzureOpenAIAdapter — Cat 6 (output_parser) 可直接 wire
- ✅ MockChatClient + 41 contract tests — agent_harness/ 單元測試零依賴 Azure
- ✅ TaskHandler signature — AgentLoop.run() plugs into agent_loop_worker.py
- ✅ NoOpTracer — Cat 1-11 從 Day 1 即可 start_span(...)
- ✅ 7 V2 metrics 註冊 — emit() 含 KeyError 防 typo
- ✅ FastAPI app + /health 通 — Phase 50.2 endpoint 接入零阻礙
- ✅ TenantContextMiddleware + RLS 整合 — 鐵律 1+2+3 全鏈路就位
- ✅ alembic from-zero cycle 驗證（head = 0010_pg_partman）
- ✅ 4 V2 lint rules pre-commit + CI 強制 — PR review 自動擋反模式

---

## 下一步

**用戶下次 session 開始時**：
1. 用 `claudedocs/6-ai-assistant/prompts/SITUATION-V2-SESSION-START.md` onboarding
2. 指示「啟動 Sprint 50.1 — Cat 1 (Orchestrator Loop) + Cat 6 (Output Parsing)」
3. AI 助手依 rolling planning 建 50.1 plan + checklist 等用戶 approve 才 code

**用戶手動處理項**（從 49.x 累積）：
1. GitHub branch protection rule（49.1 carry）— admin UI
2. 49.1+49.2+49.3+49.4 merge to main 決策
3. npm audit 2 moderate vulnerabilities（49.1 carry）— 留待 frontend sprint
4. Production app role 在 staging 環境配置（per Day 5.2 guide）— Phase 53.1+
5. CI deploy gate 引入規範 E 警報（Production cutover Phase 55）

---

**Last Updated**：2026-04-29 (Sprint 49.4 closeout — Phase 49 ✅ DONE)
**Maintainer**：用戶 + AI 助手共同維護
