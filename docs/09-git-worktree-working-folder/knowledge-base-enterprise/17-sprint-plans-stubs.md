# 17 - Sprint 002-007 Plan Stubs

**目的**：Phase 48 每個 sprint 嘅 1-page plan stub（scope、gap 引用、估時、依賴）。詳細 plan + checklist 留待每個 sprint 啟動前補足（用 Doc 14 template）。

---

## Sprint 001（✅ DONE, 2026-04-20）

**Scope**：M-01（search_memory） + HITL-01（request_approval）
**Commit**：`5e513d8` on `fix/wiring-m01-hitl01`
**Deliverable**：2 handler 修復 + 10 unit tests + FIX-001 + FIX-002 docs
**Detail**：Doc 14 + `claudedocs/3-progress/daily/2026-04-20-sprint-wiring-fix-001-progress.md`

---

## Sprint 006（🔄 本 session 執行）

**Scope**：
- **RES-01**（🔴 HIGH）ResumeService 與 Pipeline Path A 統一
- **RES-04**（🔴 HIGH）`start_from_step = iteration_count + 1` 語義釐清
- **新功能**：`DialogPauseException` resume handler（Doc 15 Round 3 §1 發現完全無實作）

**估時**：3 天（壓縮後本 session ~1-2 小時）
**依賴**：無

**Branch**：`fix/wiring-sprint-006`（從 main）

**核心設計**：
1. 統一 ResumeService 與 Path A 嘅 resume semantics（不再雙路徑）
2. 釐清 `iteration_count` 來源 + update rule + 文件
3. 新增 `_resume_dialog` handler 於 `ResumeService`

**File changes**（預估）：
- `src/integrations/orchestration/resume/service.py`
- `src/integrations/orchestration/pipeline/service.py`（若 iteration_count 需改 semantics）
- `src/integrations/orchestration/pipeline/context.py`（若 dialog state 需擴展 serialization）
- `tests/unit/integrations/orchestration/resume/test_service.py`（新 / 更新）

**Acceptance criteria**：
- [ ] Pipeline Path A 與 ResumeService 共用同一個 resume source-of-truth
- [ ] `iteration_count` 語義文件化（docstring + Type hint）
- [ ] `DialogPauseException` pause 後 ResumeService 可正確 restore dialog state + re-enter pipeline
- [ ] Unit tests: 3 resume paths（hitl / dialog / reroute）各有 test
- [ ] `DialogPauseException` resume 流程 end-to-end 覆蓋

**FIX docs**：
- `claudedocs/4-changes/bug-fixes/FIX-00X-resume-path-unification.md`（RES-01）
- `claudedocs/4-changes/bug-fixes/FIX-00X-iteration-count-semantics.md`（RES-04）
- `claudedocs/4-changes/bug-fixes/FIX-00X-dialog-resume-handler.md`（新功能）

---

## Sprint 005

**Scope**：
- **OTL-01**（🔴 HIGH）15 dead metrics → Pipeline / Dispatch / Router 三層 wire-up
- **OTL-02**（🔴 HIGH）Pipeline 8 steps 加 latency + error metrics
- **OTL-03**（🔴 HIGH）Dispatch executors 加 dispatch_latency + errors metrics

**估時**：5 天
**依賴**：無

**Branch**：`fix/wiring-sprint-005`

**核心設計**：
1. 每個 PipelineStep 加 OTel histogram emission（`step_latency_ms` + `step_error_total`）
2. Dispatch executors 3 個（direct / subagent / team）各加 metrics
3. Intent Router 三層（pattern / semantic / LLM）wire up 現有 `track_routing_metrics` decorator
4. HITLController / InputGateway 加 metrics hook（依 OTL-06 延伸）

**File changes**：
- `src/integrations/orchestration/pipeline/steps/step{1-8}*.py`（wrap _execute with metrics）
- `src/integrations/orchestration/dispatch/executors/{direct_answer,subagent,team}.py`
- `src/integrations/orchestration/intent_router/router.py` + 3 layer routers
- `src/integrations/orchestration/metrics.py`（加 `pipeline_step_latency_ms` / `pipeline_step_error_total` definitions）
- Tests（verify emit via OTel InMemoryMetricReader）

**Acceptance**：Grafana dashboard（或 OTel in-memory reader）能見到 live data；metrics emit rate 與 chat request 成正比。

---

## Sprint 007

**Scope**：
- **FE-01**（🔴 HIGH）`TEXT_DELTA` payload shape 統一（兩 hooks）
- **FE-02**（🔴 HIGH）Frontend SSE event TS types 定義
- **FE-05**（🟡 MED）兩個並行 SSE hooks 合併（或明確 role 分工）

**估時**：5 天
**依賴**：無

**Branch**：`fix/wiring-sprint-007`

**核心設計**：
1. Backend emit source 統一：`context.py to_sse_summary()` + `event_adapter.py` 標準化
2. Backend Pydantic model → TS types codegen（`datamodel-code-generator` or OpenAPI schema）
3. Frontend `types/ag-ui.ts` 完整定義所有 event payload types
4. 合併 `useOrchestratorSSE` + `useOrchestratorPipeline`（選其一作主，另一 deprecate）

**File changes**：
- Backend：`pipeline/context.py`, `dispatch/executors/event_adapter.py`
- Backend 新增：`scripts/generate_sse_types.py`（codegen pipeline）
- Frontend：`frontend/src/types/ag-ui.ts`（大幅擴充）
- Frontend：`frontend/src/hooks/useOrchestratorPipeline.ts` + `useOrchestratorSSE.ts`（合併）

**Acceptance**：Frontend TypeScript strict mode 無 `Record<string, unknown>`；backend Pydantic model 改動 → TS types 自動更新；兩個 hooks 合併為一。

---

## Sprint 002（⚠️ Blocked Workshop）

**Scope**：
- **K-01**（🔴 CRITICAL）Knowledge 雙倉統一
- **E-01**（🔴 CRITICAL）Embedding model 三處漂移
- **TH-01~04**（🔴 HIGH × 4）Fake Dispatcher + Dual Risk Engine
- **ER-01**（🔴 HIGH）DOMAIN_TOOLS 補 dispatch tools
- **K-02/K-03**（併 K-01）

**估時**：5-6 天
**依賴**：Workshop Q10（Qdrant 模式）+ Q12（Embedding 維度）

**啟動前提**：Workshop 決定 Qdrant server / local / Azure AI Search，以及 embedding model 統一選擇（ada-002 / 3-large / Matryoshka）

**核心設計**（待 Workshop 後校正）：
1. Config centralization — 所有 embedding / collection / qdrant_mode 由 `core/config.py Settings` 讀
2. Step 2 delegate 至 `RAGPipeline.handle_search_knowledge()`
3. Data migration：existing `ipa_knowledge` collection（若有）→ unified `knowledge_base`
4. Fake Dispatcher 修復：TH-01/02/03 各自 call 對應 adapter/coordinator real method
5. TH-04 Dual Risk Engine：agent tool `handle_assess_risk` 改用 `orchestration.risk_assessor` 與 Pipeline 同步
6. `DOMAIN_TOOLS` 補 `dispatch_workflow/swarm/claude`

---

## Sprint 003（⚠️ Blocked Workshop）

**Scope**：
- **A-01**（🔴 HIGH→CRITICAL）Main chat flow audit emission
- **CTX-01**（🔴 HIGH）to_checkpoint_state 漏 5 欄位
- **A-02**（🟡 MED）刪 orphan AuditLogger
- **A-03**（🟡 MED）AuditLogger 命名衝突

**估時**：4-5 天
**依賴**：Workshop Q5（合規 regime 適用性）+ Q7（audit retention + WORM）

**啟動前提**：Workshop 決定 audit scope（observability-only vs SOX compliance-gate）

**核心設計**（待 Workshop 後校正）：
1. Pipeline base step 加 `AuditEventEmitter` hook
2. Async outbox pattern：`asyncio.create_task` + batch flush（避 sync write +160ms/chat latency）
3. 每 step emit 含：`trace_id, actor, obo_token_sub, action, resource, input_hash, output_hash, policy_decision`
4. Dispatch hook 亦 emit（agent tool call 記錄）
5. CTX-01 補 5 欄位 + `to_sse_summary` 加 risk_level / intent_category

**若 Workshop Q5 = SOX applicable**：加 Sprint 004 bitemporal schema 為 hard dependency

---

## Sprint 004（⚠️ Blocked Workshop）

**Scope**：
- **DB-01**（🔴 CRITICAL）9/11 ORM table 補 create_table migration
- **DB-02**（🔴 CRITICAL）audit_logs bitemporal + WORM schema
- **DB-03**（🟡 HIGH）transcript / dialog / tasks PG 持久化
- **DB-04**（🟡 HIGH）approval 獨立 table
- **DB-05**（🔴 HIGH）bitemporal / WORM / hash-chain 實作（依 A-04 + WORM-01 + PII-01）

**估時**：3-5 天
**依賴**：Workshop Q7（retention 年限 / WORM 是否 required）

**核心設計**：
1. 生成 baseline migration（`alembic revision --autogenerate`）covers existing 9 tables
2. 新 migration：`audit_events` bitemporal（`event_time` + `ingestion_time`）+ `audit_chain_id`（SHA-256 hash chain）+ WORM trigger（`REVOKE DELETE, UPDATE`）
3. 新 migration：`transcript` / `dialog_context` / `tasks` 由 Pydantic 升 SQLAlchemy ORM
4. 新 migration：`approval` 獨立 table（非復用 `checkpoints`）
5. PII redactor dual-layer：runtime Presidio + storage pgcrypto
6. Azure Immutable Blob Storage hash chain export（7-year retention per SOX §802）

**CI-06** 同步啟用：alembic baseline check（每個 ORM model 必須有對應 create_table）

---

## 四、Sprint 順序選擇策略

### 無依賴路徑（Week 1-2 可啟動）
```
Week 1: Sprint 001 ✅ → Sprint 006 ← 本 session
Week 1-2: Sprint 005
Week 2: Sprint 007
```

### 依賴 Workshop 路徑（Week 3+ 啟動）
```
Workshop → Sprint 002 (Q10/Q12)
         → Sprint 004 (Q7)
         → Sprint 003 (Q5/Q7 + depends on 004 if SOX)
```

### 合併清理路徑（Week 7-8）
```
CI-01~07 wire + MEDIUM / LOW gap batch fixes
```

---

## 五、Sprint 啟動 Template

每個 sprint 啟動前，從 Doc 14 複製 + 修改：

1. Copy `14-sprint-wiring-fix-001-plan.md` → `NN-sprint-wiring-fix-XXX-plan.md`
2. Copy `14-sprint-wiring-fix-001-checklist.md` → `NN-sprint-wiring-fix-XXX-checklist.md`
3. 替換 Sprint Name / Story Points / Branch / Stories / Acceptance
4. Reference 本文件（Doc 17）嘅 sprint stub 作 scope 起點
5. Reference Doc 11/15 嘅 gap registry 作 gap 詳情

---

## 六、版本記錄

| Version | Date | Author |
|---------|------|--------|
| 1.0 | 2026-04-20 | Claude + Chris — Phase 48 Sprint stubs |
