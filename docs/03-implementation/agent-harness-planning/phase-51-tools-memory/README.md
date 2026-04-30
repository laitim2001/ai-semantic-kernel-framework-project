# Phase 51 — Tools + Memory

**Phase 進度**：Sprint 51.0 ✅ DONE / Sprint 51.1 ✅ DONE / Sprint 51.2 🟡 PLANNING — **2 / 3 sprint complete（67%）**
**啟動日期**：2026-04-30（接 Phase 50 closeout）
**Sprint 51.0 完成日期**：2026-04-30
**Sprint 51.1 完成日期**：2026-04-30
**Sprint 51.2 plan 起草日期**：2026-04-30
**狀態**：🟢 Phase 51 進行中 — Sprint 51.0 + 51.1 ✅ DONE；**Sprint 51.2 plan + checklist 已起草**，待 user approve 後啟動 Day 1

---

## Phase 51 目標

> **Phase 51 是 demo 基礎設施 + 範疇 2/3 核心**（per `06-phase-roadmap.md` §Phase 51）。
> 本 phase 完成後：
> - 範疇 2（Tools）達 Level 3（51.1）
> - 範疇 3（Memory）達 Level 3（51.2）
> - 5 業務 domain 有 mock backend，52-54 demo 不再用 echo_tool（51.0）

詳細路線圖見 [`../06-phase-roadmap.md` §Phase 51](../06-phase-roadmap.md#phase-51-tools--memory3-sprint-原-2)。

---

## Sprint 進度總覽

| Sprint | 狀態 | 主題 | 完成日期 | Branch / Commits |
|--------|------|------|---------|------------------|
| **51.0** | ✅ DONE | Mock 企業工具 + 業務工具骨架（**新增 sprint**） | 2026-04-30 | `feature/phase-51-sprint-0-mock-business-tools`（12 commits）→ merged main `8cd47ca` |
| **51.1** | ✅ DONE | 範疇 2 工具層（Level 3）— ToolSpec first-class field + ToolRegistryImpl + Sandbox + 6 內建工具 + 18 業務 stub migration + _inmemory deletion | 2026-04-30 | `feature/phase-51-sprint-1-cat2-tool-layer`（5 commits + Day 5 closeout） |
| **51.2** | 🟡 PLANNING | 範疇 3 記憶層（Level 3）— MemoryHint 擴展 + 5 layer concrete impl + retrieval / extraction / conflict_resolver + memory_tools placeholder→real handler + tenant isolation + 「線索→驗證」demo | TBD | `feature/phase-51-sprint-2-cat3-memory-layer`（待開） |

---

## Sprint 文件導航

```
phase-51-tools-memory/
├── README.md                          ← (this file) Phase 51 入口
├── sprint-51-0-plan.md                🟡 PLANNING（待用戶 approve）
├── sprint-51-0-checklist.md           🟡 PLANNING
├── sprint-51-1-plan.md                ⏸ 51.0 closeout 後 rolling 寫
├── sprint-51-1-checklist.md           ⏸ 同上
├── sprint-51-2-plan.md                🟡 PLANNING（已起草，待用戶 approve）
└── sprint-51-2-checklist.md           🟡 PLANNING（已起草，待用戶 approve）
```

執行紀錄（51.0 啟動後建立）：
```
docs/03-implementation/agent-harness-execution/phase-51/
└── sprint-51-0/{progress,retrospective}.md
```

---

## 範疇成熟度演進（規劃）

| 範疇 | Pre-51.0 | Post-51.0 ✅ | Post-51.1 ✅ | Post-51.2（51.2 plan 預期）|
|------|---------|-------------|-------------|-----------|
| 1. Orchestrator Loop | Level 3 | **Level 3** | **Level 3** | Level 3（unchanged）|
| 2. Tool Layer | Level 1 | **Level 1+**（18 業務 stub + register pattern + e2e via real subprocess）| **Level 3** ✅（ToolRegistryImpl + ToolExecutorImpl + PermissionChecker + SandboxBackend + 6 builtin + 18 business migrated to first-class hitl_policy/risk_level） | Level 3（unchanged；memory_tools placeholder→real handler 不影響 Cat 2 等級）|
| 3. Memory | Level 0 | Level 0 | Level 0 | **Level 3 ⏸ 預期**（5 layer concrete + retrieval + extraction + conflict_resolver + MemoryHint verify_before_use + 9/15 cell 真實實作 / Qdrant semantic 軸 → CARRY-026）|
| 6. Output Parser | Level 4 | Level 4 | **Level 4** | Level 4（unchanged）|
| 12. Observability | Level 2 | Level 2（mock_executor 已埋 tool_execution_duration_seconds via InMemoryToolExecutor）| **Level 2**（ToolExecutorImpl 持續埋 metric；status label 擴展 unknown / denied / approval_required / schema_invalid / success / error） | Level 2（51.2 加 `memory_retrieval_search` span + MemoryAccessed event payload 擴 time_scale/confidence）|

> Sprint 51.0 不直接提升範疇 2/3 等級，但**解鎖 51.1+ 的 demo 場景**：移除 echo_tool 依賴，讓 52-54 sprint 有真實業務工具可呼叫。

---

## Sprint 51.0 範圍預覽

**核心交付（per Sprint 51.0 plan）**：
- 5 業務 domain 各 1 個 `tools.py`（含 `register_<domain>_tools(registry)` 入口）
- 18 個業務 ToolSpec stub（指向 mock backend HTTP endpoint）
- Mock backend FastAPI 子服務（CRM / KB / 5 domain 的 mock 資料路由）
- Mock data seed（10 customer / 50 order / 20 alert / 5 incident）
- e2e demo：agent loop 呼叫 `mock_patrol_check_servers` 拿到 mock 結果

**範疇歸屬**：
- 18 ToolSpec 在 `business_domain/` — 業務領域層（per `08b-business-tools-spec.md`）
- Mock backend 在 `mock_services/` — 平台輔助層（測試與 demo 用，**非 production**）
- ToolRegistry 持續用 50.1 `InMemoryToolRegistry`（51.1 升級為 Level 3）

> **與 spec 差異**：roadmap 寫「24 個工具」，08b spec 列 **18 個**（4+3+3+3+5）。51.0 採 spec 為準，差異記入 retrospective.md。

---

## Phase 51 結束驗收（per 51.0 + 51.1 + 51.2）

- ✅ Tool layer 三大能力齊備：registry / spec / executor / sandbox / permissions（51.1）
- ✅ 5 層記憶獨立可測 + tenant 隔離（51.2）
- ✅ Agent 可主動呼叫 memory_search + 業務工具混合運作（51.2）
- ✅ 「線索→驗證」工作流範例（51.2）
- ✅ 第二個 demo 案例「memory_search 找過去資料 + 用工具驗證」可跑（51.2）
- ✅ 不再有 echo_tool dependency（51.0 起）

---

## Sprint 51.0 累計交付

### Backend（17 new files / 3 modified）
- `mock_services/` 11 file — FastAPI app + 7 routers + schemas + seed.json + loader
- `business_domain/{patrol,correlation,rootcause,audit_domain,incident}/{mock_executor,tools}.py` 10 file
- `business_domain/_register_all.py` — `register_all_business_tools()` + `make_default_executor()`
- `api/v1/chat/handler.py` — swap `make_echo_executor` → `make_default_executor`（chat default 1→19 tools）
- `runtime/workers/agent_loop_worker.py` — unchanged（cleaner layering decision）

### Tests（3 new files / 24 new tests）
- `tests/integration/mock_services/test_mock_services_startup.py`（12 tests，TestClient + lifespan）
- `tests/integration/business_domain/test_business_tools_via_registry.py`（10 tests，httpx ASGI monkey-patch）
- `tests/e2e/test_agent_loop_with_mock_patrol.py`（2 tests，real uvicorn subprocess + AgentLoopImpl）

### Dev tooling
- `scripts/mock_dev.py` — standalone start/stop/status
- `scripts/dev.py` — 17-line shim dispatching `mock <cmd>` → mock_dev.py
- `docker-compose.dev.yml` — `mock_services` service block（python:3.12-slim + uvicorn 8001）

### 文件
- `sprint-51-0-plan.md` （~250 行）
- `sprint-51-0-checklist.md` （39 task / Day 0-5 全 [x]）
- `progress.md` （Day 0-5 全紀錄）
- `retrospective.md`（5 Improve / 3 CARRY / 估時準度報告）
- `17-cross-category-interfaces.md` §3.1 — 加 18 mock business tools entries（+ echo_tool entry）
- `phase-51-tools-memory/README.md`（本檔）

### Test 累計
- 50.2 baseline 259 PASS → **51.0 closeout 283 PASS / 0 SKIPPED / 0 FAILED**（+24 new tests）
- mypy strict 30 source files no issues
- 5 V2 lints all OK / black formatted

### 估時準度
- Plan ~25.5h / Actual ~5.9h / **23%**（V2 7-sprint 平均 ~20%；落 13-26% 區間）

---

## 下一步

1. ✅ **51.0 closeout 完成**
2. ✅ **Sprint 51.1 closeout 完成**：Cat 2 Level 1+ → **Level 3**（HEAD `7595e60`）
3. 🟡 **Sprint 51.2 啟動準備中**：plan + checklist 已起草（2026-04-30）
   - 主題：範疇 3 記憶層（5 layer concrete + retrieval + extraction + memory_tools real handler + tenant isolation + 「線索→驗證」demo）
   - 預期：Cat 3 Level 0 → **Level 3**；新增 CARRY-026/027/028（Qdrant semantic / extraction worker queue / red-team OWASP LLM Top 10）
   - 啟動條件：用戶 approve plan + checklist 後切 `feature/phase-51-sprint-2-cat3-memory-layer` branch 開 Day 1
4. **Sprint 52.1 待啟動**（51.2 closeout 後）：範疇 4 Context Mgmt（Compaction + token counter + 30+ turn 對話）

---

**Last Updated**：2026-04-30 (Sprint 51.1 ✅ DONE / 51.2 🟡 PLANNING — Phase 51 progress 2/3 = 67%; V2 cumulative 8/22 sprints = 36%)
**Maintainer**：用戶 + AI 助手共同維護
