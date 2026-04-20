# 15 - Wiring Audit Round 3（Pipeline Resume / Metrics / DB Migration / Frontend SSE）

**執行日期**：2026-04-20
**執行方式**：4 個 subagent 並行（root-cause-analyst × 2 + backend-architect + frontend-architect）
**Scope**：Round 1（Doc 10）/ Round 2（Doc 12）未覆蓋嘅 deep layers
**總 findings**：**25 個新 gap**，其中 **12 個 🔴 HIGH / CRITICAL**

**Scope coverage**：
- ✅ **C.1** Pipeline Service resume E2E（service.py + context.py + persistence.py + resume/）
- ✅ **C.2** OpenTelemetry metrics wiring（metrics.py 893 LOC vs 實際埋點）
- ✅ **C.3** DB migration / ORM drift（alembic/versions/ vs models）
- ✅ **C.4** Frontend SSE consumer（useOrchestratorPipeline / useOrchestratorSSE / types/ag-ui.ts）

---

## 零、Executive Summary

### 本輪最關鍵發現：**4 個系統性 pattern 被確認**

#### Pattern 1：🚨 **Dead Infrastructure**（`OrchestrationMetricsCollector`）

**`metrics.py` 893 LOC + 15 個定義 metrics = 100% dead code**
- 15/15 metrics 零 production emit（全部只喺 self-test 跑過）
- 4 個 Gauge 嘅 OTel 分支係 `pass` no-op
- Exporter pipeline（Azure Monitor / OTLP）wired 但無料可 export

**Doc 10/12 暗示「OpenTelemetry metrics integrated」係 false。** Phase 28 Sprint 99 完成 metric **定義**，但從未 wire 去 business logic。

#### Pattern 2：**Parallel Evolution**（多套冗餘系統並存）

- **兩條 resume 路徑**：chat_routes Path A（真 resume）vs ResumeService（只記錄 transcript，無 re-run）
- **兩個 SSE hooks**：`useOrchestratorPipeline`（prod）vs `useOrchestratorSSE`（PoC）— 處理 overlapping events
- **兩套 event schema**：Production STEP_* / AGENT_MEMBER_* vs PoC TASK_DISPATCHED / SWARM_* — 命名不統一

#### Pattern 3：**Baseline Missing**（Alembic migration 不完整）

- 11 個 ORM table 中 **9 個無 `create_table` migration**，依賴 `Base.metadata.create_all()` 隱式 bootstrap
- 新環境 `alembic upgrade head` **唔會重建全部 schema**
- 只有 Phase 47 Sprint 169（`orchestration_execution_logs`）+ 007 (`agent_experts`) 有完整 migration

#### Pattern 4：**PRD vs Reality Gap**（Bitemporal / WORM）

- `ingestion_time`: **0 hits** codebase-wide
- `bitemporal`: **0 hits**
- `audit_chain_id`: **0 hits**
- **A-04 / WORM-01 目標實作進度 = 0%**

---

## 一、C.1 — Pipeline Service Resume E2E

### 發現概要

系統有 **兩條獨立 resume 路徑，互不共用**：

**Path A（chat_routes.py）— 真 resume**
1. Request 帶 `checkpoint_id` → `IPACheckpointStorage.load()`（Redis）
2. `PipelineContext.from_checkpoint_state(checkpoint.state)` 重建
3. `start_from_step = checkpoint.iteration_count + 1`
4. `pipeline.run(context, start_from_step=N)` → skip 已完成 steps
5. 失敗 fallback 到 fresh context（**silent**）

**Path B（ResumeService）— 只記錄 transcript**
1. API → `ResumeService.resume(ResumeRequest)` → 依 mode 分派（hitl / reroute / retry / continue）
2. **只記錄 transcript + 回傳 metadata，唔會真正 re-run pipeline**
3. `resumed_from_step` **hardcoded**（service.py line 206 硬寫 `4`，line 250 硬寫 `6`）

### 新 Gap

| ID | 描述 | 位置 | 嚴重度 | 估時 |
|----|------|------|-------|------|
| **RES-01** | ResumeService 與 Pipeline Path A 完全割裂，兩套 resume 語義衝突 | `resume/service.py:67` vs `chat_routes.py:141` | 🔴 HIGH | 4h |
| **RES-04** | `start_from_step = iteration_count + 1` — `iteration_count` 語義不明；若 HITL pause 於 step 5，resume 應重入 step 6 但邏輯依賴 checkpoint 寫入時 `iteration_count` 正確 | `chat_routes.py:154` | 🔴 HIGH | 3h |
| RES-02 | ResumeService `resumed_from_step` hardcoded（4/6），唔睇 checkpoint 實際 step | `resume/service.py:206,250` | 🟡 MED | 2h |
| RES-03 | `_resume_hitl` truncate `memory_context[:100]` / `knowledge_results[:100]` — 與 Phase 47 "full text no truncation" 設計矛盾 | `resume/service.py:172-173,218-219` | 🟡 MED | 1h |
| RES-06 | `selected_route` 已 serialize 但 `dispatch_result` 無 → resume 後若 step 6 已完成，step 7 dispatch 會 re-execute（waste LLM tokens）| `context.py:136-144` | 🟡 MED | 2h |
| RES-05 | Path A resume failure fallback silently 丟棄 checkpoint 並重跑 fresh，user 無告知 | `chat_routes.py:163-174` | 🟢 LOW | 1h |

### 確認 Round 2 預測

- **CTX-01** 確認但**影響分歧**：to_checkpoint_state 漏 5 欄位屬實，但 runtime 因 Path A `start_from_step` 跳過對應 step 而 masked — 只影響 UI / dialog resume，不 crash
- **CTX-02** 確認：from_checkpoint_state 無 restore `total_start_time` → `elapsed_ms` corrupt（`PIPELINE_COMPLETE.total_ms` 只反映 post-resume 時間）

### 未 explore 邊緣（建議 Round 4）

1. 多次連續 HITL pause → checkpoint 覆蓋策略
2. **`DialogPauseException` resume 完全無實作**（ResumeService 無對應 handler）🔴 新發現
3. Redis checkpoint TTL expire 行為
4. `iteration_count` field 來源

### `persistence.py` scope 釐清（原 A-05 解決）

Phase 47 Sprint 169 `PipelineExecutionPersistenceService` **非 checkpoint 系統**，係**獨立嘅 PostgreSQL 執行歷史歸檔**：
- 用途：Pipeline 完成後寫入 `PipelineExecution` ORM，供 UI 歷史查詢
- 與 Redis checkpoint **無 overlap**：Redis = mid-flight state；PG = completed execution audit log
- **唔係 audit 替代品**（與 A-04 / WORM-01 目標無關）

---

## 二、C.2 — OpenTelemetry Metrics Wiring

### 🚨 結論：**15/15 metrics 100% dead**

`OrchestrationMetricsCollector`（metrics.py:298，893 LOC）定義 15 個 metrics，**無一個喺 production 路徑 emit**。

### Dead Metric 清單（全部 ❌ DEAD）

| 類別 | Metric | Defined | 應該 emit 喺 | 實際 |
|------|--------|---------|--------------|------|
| Routing | `orchestration_routing_requests_total` | L66 | `intent_router/router.py` | ❌ 零 caller |
| Routing | `orchestration_routing_latency_seconds` | L73 | 三層 router | ❌ |
| Routing | `orchestration_routing_confidence` | L80 | 三層 router | ❌ |
| Routing | `orchestration_completeness_score` | L87 | completeness/checker.py | ❌ |
| Dialog | `orchestration_dialog_rounds_total` | L101 | guided_dialog/ | ❌ |
| Dialog | `orchestration_dialog_completion_rate` | L108 | 同上 | ❌ + OTel path 係 `pass` (L582) |
| Dialog | `orchestration_dialog_duration_seconds` | L115 | 同上 | ❌ |
| Dialog | `orchestration_dialog_active_count` | L122 | 同上 | ❌ + OTel path 係 `pass` (L568) |
| HITL | `orchestration_hitl_requests_total` | L136 | HITLController | ❌ 無 import |
| HITL | `orchestration_hitl_approval_time_seconds` | L143 | 同上 | ❌ |
| HITL | `orchestration_hitl_pending_count` | L150 | 同上 | ❌ + `pass` (L639) |
| HITL | `orchestration_hitl_approval_rate` | L157 | 同上 | ❌ + `pass` (L654) |
| System | `orchestration_system_source_requests_total` | L171 | InputGateway | ❌ 無 import |
| System | `orchestration_system_source_latency_seconds` | L178 | 同上 | ❌ |
| System | `orchestration_system_source_errors_total` | L185 | 同上 | ❌ |

**Pipeline step / Dispatch executor / Router 三層**：完全零 metric 定義 + 零 emit

### 新 Gap

| ID | 描述 | 位置 | 嚴重度 | 估時 |
|----|------|------|-------|------|
| **OTL-01** | 15 個 metrics 全 dead，無 production caller | `metrics.py:64-191` vs pipeline/dispatch/router | 🔴 HIGH | 16h（wire 3 層）|
| **OTL-02** | Pipeline 8 steps 完全無 latency / error metrics | `pipeline/steps/step{1-8}*.py` | 🔴 HIGH | 6h |
| **OTL-03** | Dispatch executors 無 dispatch_latency / dispatch_errors | `dispatch/executors/*.py` | 🔴 HIGH | 4h |
| OTL-04 | 4 個 Gauge 嘅 OTel 分支係 `pass` (no-op) | `metrics.py:568, 582, 639, 654` | 🟡 MED | 2h（改 ObservableGauge callback）|
| OTL-05 | `track_routing_metrics` decorator 定義但零使用 | `metrics.py:807` | 🟡 MED | 1h |
| OTL-06 | HITLController / ApprovalHandler / InputGateway 無 import metrics | 各自 controller | 🟡 MED | 3h |
| OTL-07 | 錯誤路徑缺 metric emit（所有 `except` block） | pipeline / dispatch | 🟡 MED | 3h |
| OTL-08 | Pipeline `step_latency` / `step_error` metrics 連定義都冇 | metrics.py 缺失 | 🟢 LOW | 2h |

### Export Pipeline 現況

- ✅ `core/observability/setup.py:182` `_create_meter_provider()` 有 Azure Monitor + OTLP exporter（視 `OTEL_ENABLED`）
- ✅ `main.py:70-72` lifespan `setup_observability(...)` 正確呼叫
- ❌ **但 business logic 零 emit**，Grafana / Azure Monitor 會見 instrument metadata 但 data points 永遠 0

---

## 三、C.3 — DB Migration / ORM Drift

### 🚨 結論：**9/11 ORM tables 無 baseline migration**

只有 **2 個 table** 有 `create_table` migration：
- `agent_experts`（migration 007，Phase 46）
- `orchestration_execution_logs`（migration 008，Phase 47 Sprint 169）

**其餘 9 個 table**（`agents / checkpoints / executions / sessions / messages / attachments / users / workflows / audit_logs`）靠 `Base.metadata.create_all()` 隱式建立 → 新環境 `alembic upgrade head` **唔會重建 schema**。

### 關鍵 table 狀態

| Table | Migration | ORM | Drift | 影響 |
|-------|-----------|-----|-------|------|
| `approval` | 冇 | 冇獨立 model（復用 `checkpoints`） | — | HITL-01 靠 checkpoint row 當 approval |
| `audit_events` | 冇 | 冇 | 🔴 gap | A-04 / WORM-01 無 schema 基礎 |
| `audit_logs` | 冇 `create_table` | 有 `AuditLog` | 🟡 silent bootstrap | 無 WORM trigger、無 bitemporal |
| `checkpoints` | 005 `add_column` 補 7 欄 | 有 | ✅ sync | HITL-01 schema ready |
| `memory_records / sessions` | 冇 | 冇（mem0 用 Qdrant） | ℹ️ not PG | 冇 PG 持久化 |
| `pipeline_execution_log` | 008 | 有 | ✅ sync | Sprint 169 最新，唯一 healthy |
| `transcript` | 冇 | **Pydantic only**（非 ORM） | 🔴 不持久化 | Transcript 純 in-memory |
| `dialog_context` | 冇 | 冇 | 🔴 gap | GuidedDialog state 無持久化 |
| `tasks` | 冇 | **Pydantic only** | 🔴 gap | autonomous routes 引用但無 PG table |

### 新 Gap

| ID | 描述 | 位置 | 嚴重度 | 估時 |
|----|------|------|-------|------|
| **DB-01** | 9/11 ORM table **無 `create_table` migration**；依賴 `create_all()` 隱式 bootstrap；新環境 schema 不 reproducible | `alembic/versions/001-006` | 🔴 CRITICAL | 8h（補 baseline） |
| **DB-02** | `audit_logs` 無 bitemporal 欄位（`event_time`/`ingestion_time`）、無 append-only trigger、無 hash-chain | `models/audit.py` | 🔴 CRITICAL | 16h（對應 A-04 + WORM-01）|
| **DB-05** | `ingestion_time` / `bitemporal` / `audit_chain_id` 全 codebase **0 hits** — WORM-01 / A-04 停留 PRD，實作 0% | — | 🔴 HIGH | 依 DB-02 |
| DB-03 | `transcript` / `dialog_context` / `tasks` 係 Pydantic-only，無 PG 持久化 → 跨 session / 重啟即失 | 3 處 Pydantic models | 🟡 HIGH | 12h |
| DB-04 | `approval` 冇獨立 table，用 `checkpoints` 復用 → approval-specific policy / retention / analytics 難做 | `checkpoints` reuse | 🟡 HIGH | 6h |
| DB-06 | Migration 005/006 用 `IF EXISTS` guard + `DO $$` block → 暗示 schema state 不確定，多環境 drift 風險 | `005/006` | 🟢 MED | 4h |

### Bitemporal / WORM 現況

```bash
grep "event_time" codebase    → 8 hits（全部 log 欄位，無 DB column）
grep "ingestion_time"         → 0 hits
grep "bitemporal"             → 0 hits
grep "audit_chain_id"         → 0 hits
grep "WORM|immutable"         → 9 hits（多數 ACL interface 註解）
```

**距離 A-04 / WORM-01 目標 ≈ 0% implementation**。

### Phase 47 persistence.py ↔ Migration 008 對齊

✅ **唯一 healthy path**：ORM `OrchestrationExecutionLog` 欄位與 migration column 15/15 一致。**可作為其他 table 補 migration 嘅 template**。

---

## 四、C.4 — Frontend SSE Consumer

### 概要

Frontend 有 **2 個並行 SSE hooks**：
- `useOrchestratorPipeline.ts`（921 lines，production）— 處理 STEP_* / AGENT_MEMBER_* 事件
- `useOrchestratorSSE.ts`（495 lines，PoC）— 處理 TASK_DISPATCHED / SWARM_* 事件

觀察到 **24 個 SSE event types**，主流程 backend emit + frontend consume 基本配對，但存在以下問題：

### 新 Gap

| ID | 描述 | 位置 | 嚴重度 | 估時 |
|----|------|------|-------|------|
| **FE-01** | `TEXT_DELTA` payload shape divergence：`useOrchestratorSSE` 期望 `{delta, source, agent}`，`useOrchestratorPipeline` 期望 `{content}` — 兩個 backend emitters 必須產不同 shape | `useOrchestratorSSE.ts:255-269` vs `useOrchestratorPipeline.ts:267-272` | 🔴 HIGH | 4h |
| **FE-02** | Frontend **TS types for SSE events 未定義** — payload typed as `Record<string, unknown>` inline，無 contract enforcement | `types/ag-ui.ts` 缺失 | 🔴 HIGH | 8h |
| FE-03 | `OrchestrationMetadata.riskLevel` / `intent` / `confidence` / `routingLayer` 類型已定義但**無 SSE event 填充** — orphan consumer | `types/ag-ui.ts:336-356` | 🟡 MED | 2h |
| FE-05 | 兩個並行 SSE hooks 處理 overlapping events，duplicate dispatch logic，drift risk | hooks folder | 🟡 MED | 6h |
| FE-04 | `AGUIEventType` union（TEXT_MESSAGE_*, RUN_*, STEP_*）定義但**從未 emit** — 從 AG-UI protocol 繼承嘅 dead types | `types/ag-ui.ts:257-273` | 🟢 LOW | 2h |

### Orphan Consumer / Dead Provider

- **Orphan consumer**（frontend 類型定義咗，backend 冇提供）：
  - `OrchestrationMetadata.{riskLevel, intent, confidence, routingLayer}` — 組件 `IntentStatusChip.tsx` / `RiskIndicator.tsx` 已存在但無料可顯示（**CTX-03 影響確認**）
- **Dead provider**（backend emit，frontend 冇讀）：
  - `to_sse_summary().elapsed_ms` / `.paused_at` / `.checkpoint_id` — frontend 直接從 event payload 讀

### AG-UI Protocol 同步狀態

**完全手動 sync，無自動生成**：
- `types/ag-ui.ts` 註釋 `// matches backend UIComponentType` — 純靠 code review 維持
- 無 OpenAPI / JSON-schema / TS codegen pipeline
- **AGUIEventType union 與 production PIPELINE_* 事件完全不相交** — 兩個事件體系並存

### CTX-03 影響確認

- ✅ HITL_REQUIRED event 直接帶 `risk_level` → HITL UI 正常
- ❌ `ChatMessage.orchestrationMetadata.*` 無來源填充 → `IntentStatusChip` / `RiskIndicator` 組件被 CTX-03 阻塞（設計意圖清晰但 emitter 未實現）

---

## 五、新 Gap 清單整合（25 個）

| ID | 類別 | 嚴重度 | 估時 |
|----|------|-------|------|
| RES-01 | Resume 雙路徑割裂 | 🔴 HIGH | 4h |
| RES-02 | ResumeService step hardcoded | 🟡 MED | 2h |
| RES-03 | Resume truncate 與 Phase 47 設計矛盾 | 🟡 MED | 1h |
| RES-04 | `iteration_count` semantics 不明 | 🔴 HIGH | 3h |
| RES-05 | Resume fallback silent | 🟢 LOW | 1h |
| RES-06 | `dispatch_result` 未 serialize → re-execute | 🟡 MED | 2h |
| OTL-01 | 15 metrics 全 dead | 🔴 HIGH | 16h |
| OTL-02 | Pipeline steps 無 metrics | 🔴 HIGH | 6h |
| OTL-03 | Dispatch 無 metrics | 🔴 HIGH | 4h |
| OTL-04 | Gauge no-op pass | 🟡 MED | 2h |
| OTL-05 | track_routing_metrics decorator 零用 | 🟡 MED | 1h |
| OTL-06 | HITL / InputGateway 無 import metrics | 🟡 MED | 3h |
| OTL-07 | 錯誤路徑缺 emit | 🟡 MED | 3h |
| OTL-08 | Pipeline step metric 連定義都冇 | 🟢 LOW | 2h |
| DB-01 | 9/11 ORM 無 create_table migration | 🔴 CRITICAL | 8h |
| DB-02 | audit_logs 無 bitemporal / WORM | 🔴 CRITICAL | 16h |
| DB-03 | transcript / dialog / tasks Pydantic-only | 🟡 HIGH | 12h |
| DB-04 | approval 復用 checkpoints | 🟡 HIGH | 6h |
| DB-05 | Bitemporal / WORM 0% 實作 | 🔴 HIGH | 依 DB-02 |
| DB-06 | Migration 005/006 IF EXISTS 風險 | 🟢 MED | 4h |
| FE-01 | TEXT_DELTA shape divergence | 🔴 HIGH | 4h |
| FE-02 | SSE events 無 TS types | 🔴 HIGH | 8h |
| FE-03 | OrchestrationMetadata orphan consumer | 🟡 MED | 2h |
| FE-04 | AGUIEventType 從未 emit | 🟢 LOW | 2h |
| FE-05 | 兩個並行 SSE hooks | 🟡 MED | 6h |

**嚴重度分佈**：2 CRITICAL + 10 HIGH + 10 MEDIUM + 3 LOW = **25 個 new gap**
**HIGH+ 合計工時**：~90 小時（~2.5 週）
**MEDIUM 合計**：~26 小時
**LOW 合計**：~5 小時
**總估時**：**~121 小時 / ~3 週 1 人**

---

## 六、三輪 Audit 累計統計

| 來源 | 新 Gap | CRITICAL | HIGH | MEDIUM | LOW |
|------|-------|---------|------|--------|-----|
| **Round 1（Doc 10）** | 13 | 4 | 2 | 5 | 2 |
| **Panel 新發現（Doc 11）** | 8+ | 1 | 3 | 2 | 2 |
| **Round 2（Doc 12）** | 19 | 0 | 6 | 7 | 6 |
| **Round 3（本文 Doc 15）** | 25 | 2 | 10 | 10 | 3 |
| **三輪累計** | **~65** | **7** | **21** | **24** | **13** |

**HIGH+ 合計 28 個** — 整個 orchestration / pipeline / DB / frontend / metrics 生態系統存在系統性 wiring gap。

---

## 七、系統性 Pattern 總結

本項目三輪 audit 識別 **4 個深層 pattern**：

### Pattern 1：「PoC → Production 未統一 SSOT」（Round 1-2）
- Config 散落各 step hardcode（E-01 embedding 三處漂移）
- 兩套 risk engine（TH-04）
- Knowledge 雙倉（K-01）

### Pattern 2：「Fake Dispatcher」（Round 2）
- import 成功、instantiate 成功、但 business method 不 call
- TH-01/02/03（workflow / swarm / claude dispatcher）

### Pattern 3：「Dead Infrastructure」（Round 3 新）
- 完整 class + method 定義但零 production emit
- `OrchestrationMetricsCollector` 893 LOC、`integrations/orchestration/audit/logger.py` 281 LOC orphan

### Pattern 4：「Parallel Evolution」（Round 3 新）
- 兩套 resume 路徑（chat_routes vs ResumeService）
- 兩個 SSE hooks（prod vs PoC）
- 兩套 event schema（PIPELINE_* vs AGUIEventType）

**根源**：IPA Platform 44 Phases 快速迭代，每 Phase 加新系統但少做「清理舊實作」紀律 → 典型 feature-rich / integration-poor 問題。

---

## 八、CI 防線建議（新增）

基於三輪發現，建議加入 5 個 CI 檢查：

| CI ID | 檢查內容 | 覆蓋 |
|-------|---------|------|
| CI-01 | Import-existence（所有 `from src.*` 確認 module 存在） | M-01 類 |
| CI-02 | Config centralization（無 module-level `DEFAULT_*`） | E-01 / P-01 類 |
| CI-03 | Fake dispatcher detection（AST 掃 handle_dispatch_* 必須 call async method） | TH-01~03 類 |
| CI-04 | Checkpoint round-trip test（`from_checkpoint_state(to_checkpoint_state(ctx)) == ctx`） | CTX-01/02 類 |
| **CI-05（新）** | **Metric emit coverage**（AST 掃所有 @instrument metric，確保 >0 caller） | OTL-01 類 |
| **CI-06（新）** | **Alembic baseline check**（所有 ORM model 必須有對應 `create_table` migration） | DB-01 類 |
| **CI-07（新）** | **SSE event schema sync**（backend Pydantic model → TS types codegen） | FE-02 類 |

---

## 九、Roadmap 影響

### 修復工期重估

| Phase | 原估時 | 三輪後估時 |
|-------|-------|-----------|
| **P0 CRITICAL（本 sprint 級）** | 4-6 天 | **~14 天**（含 DB-01 + DB-02 + TH-01~03 + K-01 + M-01 + HITL-01 + A-01）|
| **P1 HIGH（下幾 sprint）** | 2-4 天 | **~3 週**（含 OTL-01~03 wire + FE-01/02 + RES-01/04 + DB-03/04/05）|
| **P2 MED（背景處理）** | — | **~2 週** |
| **P2 LOW（清理）** | — | **1-2 天** |
| **Total P0-P2** | 原 9-month roadmap | **~2 個月 wiring-only**，然後才係 Doc 08 原計劃（L3 Ontology / Bitemporal / Verifier / L4 Specialist）|

### Sprint 分組建議（更新）

| Sprint | Scope | 工期 | 依賴 |
|--------|-------|------|------|
| Sprint Wiring Fix 001 | M-01 + HITL-01 | 2 天 | 無（✅ Done）|
| Sprint Wiring Fix 002 | K-01 + E-01 + TH-01~04 | 5-6 天 | Workshop Q10/Q12 |
| Sprint Wiring Fix 003 | A-01 + ER-01 + CTX-01 | 4-5 天 | Workshop Q5/Q7 |
| **Sprint Wiring Fix 004（新）** | **DB-01 baseline migration + DB-02 bitemporal audit schema** | **3 天** | **Workshop Q7（retention）**|
| **Sprint Wiring Fix 005（新）** | **OTL-01~03 metrics wire up（Pipeline + Dispatch + Router）**| **1 週** | **無** |
| **Sprint Wiring Fix 006（新）** | **RES-01/04 resume path 統一 + DialogPauseException handler** | **3 天** | **無** |
| **Sprint Wiring Fix 007（新）** | **FE-01/02 SSE schema codegen + 兩 hooks 統一** | **1 週** | **無** |

---

## 十、Methodology Reflection

本輪 audit 仍未覆蓋嘅層：

1. **多次連續 HITL pause cycle** — checkpoint 覆蓋策略
2. **Dialog pause resume** 完全無實作（C.1 發現但未深 explore）
3. **`iteration_count` field 來源** trace
4. **Redis TTL 對 resume 行為影響**
5. **Session metrics**（`domain/sessions/metrics.py`）未驗證 wiring
6. **PoC module**（`integrations/poc/`）與 production 依賴關係（O-01 已發現，未深入）

**建議 Round 4 scope**（optional）：
- HITL multi-pause cycle + Dialog resume 完整 E2E
- PoC module retire plan

---

## 十一、結論

**研究階段完整結束**：

| 輪次 | 新 Gap | 最關鍵發現 |
|------|-------|-----------|
| Round 1 | 13 | Knowledge 三路徑不一致、Memory tool 永久 broken、Main chat 零 audit |
| Panel | 8+ | Fake dispatcher 初現、HITL-01、E-01 三處 embedding drift |
| Round 2 | 19 | **Fake Dispatcher pattern 確立** (TH-01~03)、dual risk engine、checkpoint 5 欄位漏 |
| **Round 3** | **25** | **Dead infrastructure pattern (metrics)、Parallel evolution pattern (resume/SSE)、Baseline missing (9/11 tables)、PRD vs Reality 0% (bitemporal)** |

**IPA Platform 雖有 44 Phases 高速功能迭代，但 wiring 紀律落後**。三輪 audit 揭示 ~65 gap、28 個 HIGH+。建議 **啟動 2 個月 wiring stabilization phase** 先於 Doc 08 原計劃（L3 Ontology / Bitemporal / Verifier / Specialist）。

**本份 Doc 15 完成後，研究階段（Doc 01-15 + 13a）全數交付**。剩餘工作 100% 係 sprint execution + workshop，與研究分析無關。

---

## 十二、版本記錄

| Version | Date | Author |
|---------|------|--------|
| 1.0 | 2026-04-20 | 4 subagent audit + Claude 整合 |

**Related docs**：
- Doc 10 — Wiring Audit Round 1
- Doc 11 — Agent Team Review v1.1（已整合至 Doc 15 pattern 列表）
- Doc 12 — Wiring Audit Round 2
- Doc 13 / 13a — Workshop Agenda + Handout
- Doc 14 — Sprint Wiring Fix 001 Plan + Checklist
- **Doc 15（本文）**：Wiring Audit Round 3

**Raw subagent transcripts**：
- C.1 Resume：`...a95a23db9ec86cca8.output`
- C.2 Metrics：`...a3e1f5f33cb3c3a71.output`
- C.3 DB：`...a373690a16e81aede.output`
- C.4 Frontend：`...a97996ee916adcd8b.output`
