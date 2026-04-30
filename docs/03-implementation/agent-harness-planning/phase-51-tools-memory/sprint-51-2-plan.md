# Sprint 51.2 — Plan：範疇 3 Memory 層（Level 0 → Level 3）

**Sprint**：51.2 — Cat 3 Memory Layer（5 scope × 3 time scale）
**Phase**：51（Tools + Memory）/ 第 3 / 共 3 sprint
**Cumulative**：8/22 V2 sprints（Phase 51 進度 2/3 → 預計 3/3 = 100%）
**Branch**：`feature/phase-51-sprint-2-cat3-memory-layer`（待開）
**Plan 起草**：2026-04-30
**Status**：🟡 PLANNING — 待用戶 approve 後啟動 Day 1

---

## 0. Sprint 目標（一句話）

把 **51.1 placeholder 的 `memory_search` / `memory_write` 工具**換成真實 Cat 3 backend，交付 **5 scope × 3 time scale 雙軸記憶系統**：5 層 `MemoryLayer` 具體實作 + retrieval / extraction + 「線索→驗證」demo + 跨 tenant 隔離測試，使範疇 3 從 Level 0 進到 **Level 3**。

---

## 1. User Stories

### Story 1：Agent 能跨 5 層搜尋過去資料

> **作為** agent harness 主流量呼叫者
> **我希望** agent 呼叫 `memory_search` 時能跨 system / tenant / role / user / session 5 層回傳 top-k 線索
> **以便** 第二輪以後對話能參考 user 偏好 / tenant SOP / 過去結論

**驗收**：
- 工具呼叫實際路由到 `MemoryRetrieval.search()`，**不再** raise `NotImplementedError`
- top_k=5 預設；`scopes` 預設 `["session", "user", "tenant"]`（per 51.1 ToolSpec）
- 多租戶：tenant_a 看不到 tenant_b 的 session/user/tenant 層內容（red-team query 0 leak）

### Story 2：Agent 能把對話結論寫入 user / session / tenant 層

> **作為** agent
> **我希望** 呼叫 `memory_write(scope=user, key, content)` 把「user 偏好詳細財務拆解」這類結論落地到 PostgreSQL
> **以便** 下次同一 user 進來時 prompt 能注入該偏好

**驗收**：
- 寫入 `user_memory` table（含 `tenant_id` / `user_id` / `created_at` / `expires_at`）
- 同 tenant + user 的後續 `memory_search(scopes=["user"])` 能取回該 entry
- system 層 read-only（呼叫 `memory_write(scope=system)` 拒絕並回 error）

### Story 3：「線索→驗證」工作流落地

> **作為** agent
> **我希望** `MemoryHint` 帶 `verify_before_use=True` 標記，當我從 memory 拿到一個過時 hint 時，先呼叫 mock 業務工具驗證真實性才採信
> **以便** memory 不會變成「過期事實」誤導決策

**驗收**：
- `MemoryHint` dataclass 新增 4 欄位：`confidence: float` / `last_verified_at: datetime | None` / `verify_before_use: bool` / `source_tool_call_id: str | None`
- demo 案例 e2e：agent 取得 stale hint → 偵測 `verify_before_use=True` → 呼叫 `mock_crm_search_customer` 驗證 → 一致時直接用 / 不一致時呼叫 `memory_write` 更新
- 整合測試 pass

### Story 4：背景 Extraction Worker 把 session 沉澱到 user 層

> **作為** 平台
> **我希望** 當一個 session 結束（last activity > 30 min 或 explicit close），背景 worker 從 messages 萃取重要 user 偏好寫入 `user_memory`
> **以便** session 結束的有用資訊不會遺失

**驗收**：
- `MemoryExtractor` 類別 + `extract_session_to_user(session_id)` 方法
- **51.2 範圍**：手動觸發（test 直接呼叫；不接 Celery / Redis queue — 那是 Phase 53.1 工作）
- 萃取邏輯使用 LLM judge prompt（透過 ChatClient ABC，符合中性原則）
- 測試：feed 5-message session → extract → 至少 1 條 `MemoryHint` 寫入 user 層

### Story 5：範疇 3 達 Level 3 + Cat 1 Loop 整合就緒

> **作為** Phase 52+ 開發者
> **我希望** 範疇 3 是穩定的、可被 PromptBuilder（Cat 5）注入的、有完整 ABC + 5 layer + retrieval / extraction
> **以便** Sprint 52.2 可直接整合 memory layers 到 prompt 階層

**驗收**：
- mypy --strict 全 src（39 + ~8 new files）clean
- pytest 全綠（baseline 315 → 目標 ~340 PASS）
- 17.md §1.1 / §2.1 / §3.1 / §4.1 同步（MemoryHint 欄位 / MemoryLayer ABC / 移除 memory_search placeholder 標記 / MemoryAccessed event）
- Phase 51 README cumulative table 標 Cat 3 Level 0 → **Level 3**

---

## 2. 技術設計

### 2.1 雙軸記憶矩陣（5 scope × 3 time scale）

> **51.2 落地策略**：完整矩陣 15 cell；51.2 實作 **9 cell**（覆蓋 must-have），其餘 6 cell 留 stub + CARRY。

| Cell | Storage | 51.2 狀態 |
|------|---------|----------|
| L1 system × long_term | PostgreSQL `system_policies`（startup-loaded const） | ✅ 實作（read-only） |
| L1 system × semantic | Qdrant `system_index` | 🚧 stub → CARRY-026（Phase 53.x） |
| L2 tenant × long_term | PostgreSQL `tenant_memory` | ✅ 實作 |
| L2 tenant × semantic | Qdrant `tenant_{id}_kb` | 🚧 stub → CARRY-026 |
| L2 tenant × short_term | (in-mem session override) | ✅ 實作（簡化版：dict-backed） |
| L3 role × long_term | PostgreSQL `role_policies` | ✅ 實作 |
| L3 role × short_term/semantic | — | 🚧 N/A 或 CARRY-026 |
| L4 user × long_term | PostgreSQL `user_memory` | ✅ **核心**實作 |
| L4 user × semantic | Qdrant `user_{id}_history` | 🚧 stub → CARRY-026 |
| L4 user × short_term | in-session dict | ✅ 實作 |
| L5 session × short_term | Redis `session:{id}:messages`（既有） | ✅ wrapper（不重複造輪子） |
| L5 → L4 extraction | MemoryExtractor | ✅ 手動觸發版 |

> **scope 選擇策略**：51.2 必交付 4/5 scope（system/tenant/user/session 真實，role 簡化）+ 1 time scale（long_term 真實 + short_term 簡化）。Semantic 軸（Qdrant）整列延後到 CARRY-026。

### 2.2 `MemoryHint` 擴展（breaking change，Day 1 完成）

```python
# 現況（49.1）
@dataclass(frozen=True)
class MemoryHint:
    hint_id: UUID
    layer: Literal["system","tenant","role","user","session"]
    summary: str
    relevance_score: float
    full_content_pointer: str
    timestamp: datetime
    expires_at: datetime | None = None
    tenant_id: UUID | None = None

# 51.2 擴展（新增 4 欄位 + time_scale 軸）
@dataclass(frozen=True)
class MemoryHint:
    hint_id: UUID
    layer: Literal["system","tenant","role","user","session"]
    time_scale: Literal["short_term","long_term","semantic"]   # ← 新增
    summary: str
    confidence: float                                          # ← 新增（取代 relevance_score 或共存）
    relevance_score: float                                     # 保留（query-specific）
    full_content_pointer: str
    timestamp: datetime
    last_verified_at: datetime | None = None                   # ← 新增
    verify_before_use: bool = False                            # ← 新增
    source_tool_call_id: str | None = None                     # ← 新增
    expires_at: datetime | None = None
    tenant_id: UUID | None = None
```

**決策**：保留 `relevance_score`（per-query top-k 排序用）+ 新增 `confidence`（記憶本身可信度，獨立於 query）。兩個欄位語意不同，併存。

### 2.3 `MemoryLayer` ABC 微調

現況 `write` 用 `ttl: Literal["permanent","quarterly","daily"]`。51.2 改為 `time_scale: Literal["short_term","long_term","semantic"]` + 內部映射 TTL（per scope policy）：

| time_scale | TTL 對應 | Storage |
|-----------|---------|---------|
| short_term | session.expires_at（Redis 24h）or in-mem | Redis / dict |
| long_term | NULL（永久）or 90d（per scope policy） | PostgreSQL |
| semantic | NULL + index | Qdrant（51.2 stub） |

**Why breaking change**：現況 `ttl` 詞彙與規格雙軸不對齐；51.2 是 Cat 3 Level 0 → 3 唯一機會修正，後續 Phase 52+ 整合時改成本更高。

### 2.4 目錄結構

```
backend/src/agent_harness/memory/
├── __init__.py                    （re-export 公開 API）
├── _abc.py                        （Phase 49.1 既有；Day 1 微調 ttl→time_scale）
├── README.md                      （update：標 Level 3）
├── layers/
│   ├── __init__.py
│   ├── system_layer.py            （L1 read-only constants + DB-backed policies）
│   ├── tenant_layer.py            （L2 PG-backed）
│   ├── role_layer.py              （L3 PG-backed simplified）
│   ├── user_layer.py              （L4 PG-backed — 核心）
│   └── session_layer.py           （L5 Redis-backed wrapper）
├── retrieval.py                   （MemoryRetrieval：跨 layer 多軸 search + score merge）
├── extraction.py                  （MemoryExtractor：session → user 萃取，LLM-judge based）
└── conflict_resolver.py           （4 條規則 — confidence / last_verified / layer specificity / HITL fallback）
```

### 2.5 工具 placeholder → 真實 handler

`backend/src/agent_harness/tools/memory_tools.py`：
- 保留 `MEMORY_SEARCH_SPEC` / `MEMORY_WRITE_SPEC` ToolSpec（schema 微調 — 加 `time_scales` 參數）
- `memory_placeholder_handler` → `memory_search_handler` / `memory_write_handler`
- 真實 handler 走 `MemoryRetrieval` / `MemoryLayer.write`
- handler `tags=("builtin", "memory")` 移除 `"placeholder"`

### 2.6 衝突解決規則（4 條）

```python
# memory/conflict_resolver.py
def resolve(hints: list[MemoryHint]) -> MemoryHint:
    # 1. confidence ≥ 0.8 直接勝出
    high_conf = [h for h in hints if h.confidence >= 0.8]
    if len(high_conf) == 1:
        return high_conf[0]

    # 2. last_verified_at < 7 day 的最新值
    fresh = [h for h in hints if h.last_verified_at and (now() - h.last_verified_at).days < 7]
    if fresh:
        return max(fresh, key=lambda h: h.last_verified_at)

    # 3. layer 越具體越優先（user > role > tenant > system）
    layer_priority = {"user": 4, "role": 3, "tenant": 2, "system": 1, "session": 5}
    return max(hints, key=lambda h: layer_priority[h.layer])

    # 4. 都不確定 → request_clarification 工具（HITL）— 51.2 stub，真實 trigger 在 Phase 53.3
```

### 2.7 17.md 同步點

| §  | 變更 |
|----|------|
| §1.1 | `MemoryHint` row 補 4 新欄位（`time_scale` / `confidence` / `last_verified_at` / `verify_before_use` / `source_tool_call_id`） |
| §2.1 | `MemoryLayer` ABC `write()` 簽名 `ttl` → `time_scale` |
| §3.1 | `memory_search` / `memory_write` 從「51.1 placeholder」改為「51.2 real handler」（移除 placeholder 標記） |
| §4.1 | `MemoryAccessed` event payload 補 `time_scale` / `confidence` |

---

## 3. File Change List

| 變更 | 檔案 | 估計 LOC |
|------|------|---------|
| **修改** | `_contracts/memory.py` | +20 / -5（擴 MemoryHint） |
| **修改** | `memory/_abc.py` | +5 / -3（time_scale 軸） |
| **新增** | `memory/layers/__init__.py` | ~5 |
| **新增** | `memory/layers/system_layer.py` | ~80 |
| **新增** | `memory/layers/tenant_layer.py` | ~120 |
| **新增** | `memory/layers/role_layer.py` | ~100 |
| **新增** | `memory/layers/user_layer.py` | ~150（核心） |
| **新增** | `memory/layers/session_layer.py` | ~90（Redis wrapper） |
| **新增** | `memory/retrieval.py` | ~120（多軸 search + score merge） |
| **新增** | `memory/extraction.py` | ~100（LLM-judge based） |
| **新增** | `memory/conflict_resolver.py` | ~50（4 條規則） |
| **修改** | `tools/memory_tools.py` | +60 / -10（real handler + schema 加 time_scales） |
| **修改** | `business_domain/_register_all.py` | +5（wire memory_handlers in default executor） |
| **修改** | `_contracts/__init__.py` | +2（re-export 新 enum 若需） |
| **新增** | `tests/unit/agent_harness/memory/test_user_layer.py` | ~150 / ~10 tests |
| **新增** | `tests/unit/agent_harness/memory/test_session_layer.py` | ~80 / ~6 tests |
| **新增** | `tests/unit/agent_harness/memory/test_retrieval.py` | ~120 / ~8 tests |
| **新增** | `tests/unit/agent_harness/memory/test_conflict_resolver.py` | ~80 / ~6 tests |
| **新增** | `tests/integration/memory/test_memory_tools_integration.py` | ~150 / ~6 tests |
| **新增** | `tests/integration/memory/test_tenant_isolation.py` | ~120 / ~5 tests（紅隊測試） |
| **新增** | `tests/e2e/test_lead_then_verify_workflow.py` | ~180 / ~2 tests（demo case） |
| **新增** | `tests/integration/memory/test_extraction_worker.py` | ~80 / ~3 tests |
| **修改** | 17.md（§1.1 §2.1 §3.1 §4.1） | +20 |
| **修改** | Phase 51 README | +5（Cat 3 Level 0 → 3） |

**累計**：~14 new src files（含 tests 約 22）/ ~5 modify files / ~2,000 LOC（含 tests）

---

## 4. Acceptance Criteria（DoD）

### 結構驗收
- [ ] `MemoryHint` 含 `time_scale` / `confidence` / `last_verified_at` / `verify_before_use` / `source_tool_call_id` 5 新欄位
- [ ] 5 層 `MemoryLayer` 具體實作（system / tenant / role / user / session）
- [ ] `MemoryRetrieval` 多軸 search 可組合 `scopes` × `time_scales` 參數
- [ ] `MemoryExtractor.extract_session_to_user()` 可手動觸發
- [ ] `conflict_resolver.resolve()` 4 條規則全落地
- [ ] `tools/memory_tools.py` 真實 handler（非 NotImplementedError）

### 工具驗收
- [ ] `memory_search` 工具呼叫 → 路由到 `MemoryRetrieval` → 回傳 list[MemoryHint]
- [ ] `memory_write` 工具呼叫 → 路由到對應 layer.write → 持久化到 PG / Redis
- [ ] schema 含 `time_scales` 參數（optional，default `["long_term"]`）
- [ ] `memory_write(scope="system", ...)` 拒絕並 error（read-only）

### 多租戶 / 安全驗收
- [ ] tenant_a `memory_search` 0 命中 tenant_b 的 user/tenant 層內容
- [ ] `user_memory` table 帶 `tenant_id` + RLS-ready（per `multi-tenant-data.md`）
- [ ] Session 跨 tenant 不混用（Redis key prefix `tenant:{tid}:session:{sid}`）

### 測試 / Quality 驗收
- [ ] pytest 全綠（baseline 315 PASS → 目標 ~340 PASS / 0-1 platform-skip）
- [ ] mypy --strict src/ clean（含 ~8 new files）
- [ ] black / isort / flake8 clean
- [ ] 4/5 V2 lints OK（AP-1 known skip per 51.1）
- [ ] 0 LLM SDK leak（`grep -r "from openai\|from anthropic" agent_harness/memory/` = 0）

### 整合 / Demo 驗收
- [ ] e2e demo `test_lead_then_verify_workflow.py`：agent 從 user 層拿到 stale hint → 偵測 `verify_before_use=True` → 呼叫 `mock_crm_search_customer` 驗證 → 不一致時 `memory_write` 更新 → 第二輪 query 取得新 entry
- [ ] 17.md §1.1 / §2.1 / §3.1 / §4.1 同步（4 處）

---

## 5. CARRY Items 處理計畫

### 處理（51.2 涵蓋）
- ✅ 51.1 留下「memory_search/write placeholder」→ 51.2 替換真實 handler
- ✅ MemoryHint 規格 vs 實作差距（Phase 49.1 stub 缺 4 欄位）

### 延後（記入 51.2 retrospective）
- 🚧 **CARRY-026**（新）：Qdrant semantic 軸實作（L1/L2/L4 vector store）→ Phase 53.x
- 🚧 **CARRY-027**（新）：MemoryExtractor 接 Celery / Redis queue（自動觸發）→ Phase 53.1（範疇 7 State Mgmt）
- 🚧 **CARRY-028**（新）：Cross-tenant red-team prompt injection 完整測試（OWASP LLM Top 10）→ Phase 53.3 + 53.4 Guardrails sprint
- 🚧 **CARRY-023**（51.1 留下）：Tenant-aware permission RBAC → Phase 53.3（不變）
- 🚧 **CARRY-022 / 024 / 025**（51.1 留下）：不變

---

## 6. Day 估時 + Theme（rolling 5-day）

| Day | Theme | Plan | 預估 actual (24%) |
|-----|-------|------|------|
| 0 | Plan + checklist + Phase README sync | 4h | 1h |
| 1 | MemoryHint 擴展 + MemoryLayer ABC 微調 + `_contracts` sync + 17.md §1.1/§2.1 sync | 6h | 1.5h |
| 2 | 5 layer concrete impl（user_layer / session_layer / system_layer / tenant_layer / role_layer）+ 16 tests | 7h | 2h |
| 3 | MemoryRetrieval + MemoryExtractor + conflict_resolver + 14 tests | 6h | 1.5h |
| 4 | tools/memory_tools.py real handler + register_all wire + schema sync + 17.md §3.1 sync + 6 integration tests | 5h | 1.5h |
| 5 | tenant isolation tests + 「線索→驗證」demo + retro + closeout | 4h | 1h |
| **Total** | — | **32h** | **~7-8h（24%）** |

> 估時模式延續 V2 7-sprint 平均（~20-24%）；51.0 23% / 51.1 24% — 51.2 預估 ~24%。

---

## 7. Sprint 結構決策（rolling）

- **51.2 是 Phase 51 最後 sprint**；完成後 Phase 51 達 100%（3/3 sprints DONE）
- **51.2 → 52.1 銜接**：Cat 3 Level 3 完成後，Phase 52.1 (Cat 4 Context Mgmt) 才能整合 memory layers 到 PromptBuilder（Sprint 52.2）
- **51.2 plan 範圍嚴格 5 day**；不擴入 Cat 4 / Cat 5 預備工作（rolling 紀律）

---

## 8. 風險與緩解

| 風險 | 機率 | 影響 | 緩解 |
|------|------|------|------|
| `MemoryHint` 擴展 breaking 既有 49.1 import callers | 低 | 中 | Day 1 grep 全 codebase MemoryHint usage（49.1 stub 階段，預期 callers ≤ 3 處） |
| PG memory tables migration 在 49.2 已建表 vs 還沒？ | 中 | 高 | Day 0 確認 — 若無 alembic migration，加入 Day 1 任務 |
| LLM-judge based extraction 成本 vs 精度 | 中 | 中 | 51.2 用最簡 prompt + 限定 5-message session；CARRY-027 才優化 |
| Redis session_layer 與既有 V1 session 機制重疊 | 高 | 中 | session_layer 只當 thin wrapper / read API；寫入仍由既有 `runtime/workers/agent_loop_worker.py` 主導 |
| 跨 tenant red-team 測試需要 prompt injection 樣本 | 中 | 中 | 51.2 用 5 個簡單 fixture（cf. spec §跨 tenant prompt injection 0 leak）；完整 OWASP CARRY-028 |

---

## 9. 啟動條件

- ✅ Sprint 51.1 closeout commit `7595e60` working tree clean
- ⏸ 用戶 approve 此 plan
- ⏸ 確認 PG memory tables migration 狀態（Day 0 第一件事 grep alembic）
- ⏸ Branch open：`git checkout -b feature/phase-51-sprint-2-cat3-memory-layer`

---

**Plan 維護**：用戶 + AI 助手共同維護
**Created**: 2026-04-30（Sprint 51.1 closeout 後當日起草）
