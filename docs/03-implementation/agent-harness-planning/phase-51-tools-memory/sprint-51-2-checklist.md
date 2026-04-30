# Sprint 51.2 — Checklist：範疇 3 Memory 層

[Plan: sprint-51-2-plan.md](./sprint-51-2-plan.md) ｜ Branch: `feature/phase-51-sprint-2-cat3-memory-layer`（待開）

**規則**：
- `[ ]` → `[x]` 只可變化方向；不可刪除未勾選項
- 阻塞時加 🚧 + reason，繼續或 escalate
- 每個 task ≤ 60 min；超出拆細

---

## Day 0 — Plan + Checklist + README sync（估 4h）

### 0.1 Plan / Checklist 起草（已完成）
- [x] **撰寫 sprint-51-2-plan.md**（20 章節 / 風險 / DoD / 估時）
  - DoD：plan 文件存在、含 5 user stories + 9 acceptance + CARRY 處理 + 風險表
  - Verify：`ls docs/03-implementation/agent-harness-planning/phase-51-tools-memory/sprint-51-2-plan.md`
- [x] **撰寫 sprint-51-2-checklist.md**（本檔）
  - DoD：含 Day 0-5 全部 tasks + DoD + verify cmd
  - Verify：`ls docs/03-implementation/agent-harness-planning/phase-51-tools-memory/sprint-51-2-checklist.md`

### 0.2 Phase 51 README sync
- [x] **更新 Phase 51 README — Sprint 51.2 啟動標記**
  - DoD：Sprint 51.2 row 從「⏸ 待啟動」→「🟡 PLANNING」；範疇成熟度表加 Post-51.2 預期欄位
  - Verify：`grep -n "51.2" docs/03-implementation/agent-harness-planning/phase-51-tools-memory/README.md` 顯示 PLANNING 標記 ✅

### 0.3 啟動前環境確認
- [x] **確認 Sprint 51.1 working tree clean**
  - Cmd：`git status --short && git log -1 --oneline`
  - DoD：HEAD = `7595e60`（51.1 closeout）；working tree clean（除用戶 IDE 工作）✅
- [x] **確認 alembic migration 狀態 — PG memory tables 是否已建**
  - Cmd：`grep -r "user_memory\|tenant_memory\|role_policies\|system_policies" backend/alembic/ 2>/dev/null | head -5`
  - DoD：判定（A）migration 已存在（49.2 工作）→ Day 1 直接使用 / 或（B）尚未建 → 加 Day 1 任務 1.7 建 migration
  - 結果記錄：✅ **(A) 已存在** — `backend/src/infrastructure/db/migrations/versions/0007_memory_layers.py` + `db/models/memory.py` ORM + `infrastructure/vector/qdrant_namespace.py` 49.2 已建好；Day 1.7 標 N/A

### 0.4 Day 0 commit
- [x] **commit Day 0**
  - Cmd：`git add docs/03-implementation/agent-harness-planning/phase-51-tools-memory/{sprint-51-2-plan.md,sprint-51-2-checklist.md,README.md} && git commit -m "docs(memory, sprint-51-2): plan + checklist + Phase 51 README sync (Day 0)"`
  - DoD：commit 上 main 之前的 51.2 第一個 commit；branch 仍是 main 或新建 feature branch
  - ✅ Commit `eb17d64` on `feature/phase-51-sprint-2-cat3-memory-layer`（branched from 51.1 tip `7595e60`）；3 files / +694 / -17

---

## Day 1 — MemoryHint 擴展 + MemoryLayer ABC 微調 + 17.md sync（估 6h）

### 1.1 開新 feature branch
- [x] **`git checkout -b feature/phase-51-sprint-2-cat3-memory-layer`** ✅ branched from `7595e60` (51.1 closeout tip)
  - DoD：`git branch --show-current` = `feature/phase-51-sprint-2-cat3-memory-layer` ✅

### 1.2 擴展 `MemoryHint` dataclass
- [x] **編輯 `_contracts/memory.py` — 新增 5 欄位** ✅ commit `4ab5ef8`
  - 新增：`time_scale: Literal["short_term","long_term","semantic"]`（required，無 default — breaking）
  - 新增：`confidence: float`（required）
  - 新增：`last_verified_at: datetime | None = None`
  - 新增：`verify_before_use: bool = False`
  - 新增：`source_tool_call_id: str | None = None`
  - 保留：`relevance_score: float`（query-specific score；與 confidence 共存）
  - DoD：`mypy --strict src/agent_harness/_contracts/memory.py` clean
  - Verify：`python -m mypy backend/src/agent_harness/_contracts/memory.py --strict`

### 1.3 grep 既有 MemoryHint callers + 修補
- [x] **掃描 src/ + tests/ MemoryHint usage** ✅ 0 constructor callers — 不需修補
  - Cmd：`grep -rn "MemoryHint(" backend/src backend/tests --include="*.py"`
  - DoD：列出所有 callers；49.1 stub 預期 ≤ 3 處
  - 修補：每個 caller 補 `time_scale` + `confidence` 必填欄位
  - Verify：`python -m mypy backend/src --strict` clean

### 1.4 微調 `MemoryLayer.write()` 簽名
- [x] **編輯 `memory/_abc.py` — `ttl` → `time_scale`** ✅ + read() 加 time_scales axis + MemoryTimeScale enum
  - 改 `ttl: Literal["permanent","quarterly","daily"]` → `time_scale: Literal["short_term","long_term","semantic"]`
  - 更新 docstring 說明 TTL 是 per-scope 內部映射
  - DoD：mypy strict clean；既有 stub 仍能 import
  - Verify：`python -m mypy backend/src/agent_harness/memory/_abc.py --strict`

### 1.5 17.md §1.1 同步（MemoryHint）
- [x] **更新 `17-cross-category-interfaces.md` §1.1** ✅ L56 補 5 新欄位
  - 找 `MemoryHint` row 補 5 新欄位（per plan §2.7）
  - DoD：grep 確認新欄位列入；single-source 規則維持

### 1.6 17.md §2.1 同步（MemoryLayer ABC）
- [x] **更新 `17-cross-category-interfaces.md` §2.1** ✅ L118 加 resolve() + 簽名變更註
  - 找 `MemoryLayer` row 簽名同步 `time_scale`
  - DoD：grep 確認

### 1.7 PG memory tables migration（若 Day 0 確認尚未建）
- [ ] 🚧 **N/A — 49.2 已建好** `0007_memory_layers.py` migration + `db/models/memory.py` ORM + `infrastructure/vector/qdrant_namespace.py`；Day 2 直接用既有 ORM。任務保留 unchecked 加 N/A 註（V2 sacred rule）。原 DoD 不執行：
  - 新增 alembic version `00XX_add_memory_tables.py`
  - 建 4 tables：`system_policies` / `tenant_memory` / `role_policies` / `user_memory`
  - 每張表 columns：`id UUID PK`, `tenant_id UUID NOT NULL FK`（除 system）, `user_id UUID FK`（user 表）, `category VARCHAR(64)`, `content TEXT`, `confidence FLOAT`, `last_verified_at TIMESTAMPTZ`, `verify_before_use BOOL DEFAULT FALSE`, `created_at`, `expires_at`
  - DoD：`alembic upgrade head` 在 dev DB 成功；`python -m alembic check` clean
  - Verify：psql 查 `\d user_memory` 顯示所有欄位
  - 🚧 若 Day 0 判定 already exists 則 skip

### 1.8 Day 1 commit
- [x] **commit Day 1** ✅ Commit `4ab5ef8 feat(memory, sprint-51-2): extend MemoryHint + MemoryLayer with time_scale axis (Day 1)` (3 files / +100 / -21)
  - Msg：`feat(memory, sprint-51-2): extend MemoryHint + MemoryLayer with time_scale axis (Day 1)`
  - DoD：commit 含 _contracts/memory.py + memory/_abc.py + 17.md（§1.1 §2.1）✅
  - 驗證：mypy 56 src clean / pytest unit/agent_harness 73 passed + 1 platform-skip ✅
  - Day 1 actual ~1.5h vs plan 6h ≈ **25%**（V2 7-sprint avg 20-24%；落區間內）

---

## Day 2 — 5 Layer concrete impl + 31 tests（估 7h / 實際 ~2h ≈ 29%）

### 2.1 `memory/layers/__init__.py`
- [x] **建 layers package** ✅ re-export 5 layer classes
  - Re-export 5 個 layer class
  - DoD：`from agent_harness.memory.layers import UserLayer, SessionLayer, ...` 成功 import

### 2.2 `memory/layers/user_layer.py`（核心，估 1.5h）
- [x] **`UserLayer(MemoryLayer)` PG-backed 實作** ✅ MemoryUser ORM；4 spec 欄位（verify_before_use / last_verified_at / source_tool_call_id / time_scale）存 metadata JSONB；24h TTL for short_term
  - `read()`：query `user_memory` WHERE `tenant_id` AND `user_id` ORDER BY `confidence` DESC LIMIT max_hints；return `list[MemoryHint]`
  - `write()`：INSERT 含 `time_scale` 對應 TTL 計算
  - `evict()`：DELETE BY `id` AND `tenant_id`
  - `resolve()`：SELECT full content BY `id`
  - DoD：mypy strict clean；含 file header

### 2.3 `memory/layers/session_layer.py`（**改 in-memory dict** vs plan Redis wrapper，估 1h）
- [x] **`SessionLayer(MemoryLayer)` in-memory dict-backed** ✅ — 49.x infrastructure/cache 仍是 stub；Redis backend 延後到 **CARRY-029**（新增）。Composite key (tenant_id, session_id)；24h TTL；lazy expiry
  - `read()`：`redis.lrange("tenant:{tid}:session:{sid}:messages", 0, max_hints)` 回傳 hint 摘要
  - `write()`：`redis.rpush(...)` + 設 TTL 24h
  - 不重複造輪 — wrap 既有 V1 session store API
  - DoD：mypy strict clean

### 2.4 `memory/layers/system_layer.py`（read-only，估 30 min）
- [x] **`SystemLayer(MemoryLayer)` PG `memory_system`** ✅ — `SystemReadOnlyError` raise on write/evict；read 不需 tenant filter（global）
  - `read()`：startup-loaded const dict（簡化版；51.2 不做 hot reload）
  - `write()`：raise `PermissionError("system layer is read-only")`
  - DoD：write 拒絕測試 pass

### 2.5 `memory/layers/tenant_layer.py`（估 1h）
- [x] **`TenantLayer(MemoryLayer)` PG `memory_tenant`** ✅ — long_term only；short_term raise ValueError（caller 應走 SessionLayer）
  - 類比 user_layer 但 query 用 `tenant_id` 不用 `user_id`
  - DoD：mypy strict clean

### 2.6 `memory/layers/role_layer.py`（簡化版，估 30 min）
- [x] **`RoleLayer(MemoryLayer)` PG `memory_role`** ✅ — read-only impl；write/evict raise NotImplementedError；admin-managed in Phase 53+
  - 51.2 簡化：只 read（admin UI 寫入屬 Phase 53+）
  - `write()` raise NotImplementedError + log warning
  - DoD：仍 inherit ABC 全方法

### 2.7 Unit tests — UserLayer（估 1h）
- [x] **`tests/unit/agent_harness/memory/test_user_layer.py`** ✅ **11 tests**（超 plan 10）
  - `test_write_and_read_roundtrip`
  - `test_tenant_isolation_via_query`
  - `test_max_hints_limit`
  - `test_evict_removes_entry`
  - `test_resolve_returns_full_content`
  - `test_time_scale_long_term_no_expires`
  - `test_time_scale_short_term_sets_expires`
  - `test_confidence_ordering`
  - `test_user_id_required_for_user_layer`
  - `test_write_returns_uuid`
  - DoD：10/10 pass

### 2.8 Unit tests — SessionLayer + SystemLayer + TenantLayer + RoleLayer（估 1h）
- [x] **`test_session_layer.py`** ✅ **7 tests**（超 plan 6；in-memory direct，不需 Redis fixture）
- [x] **`test_system_layer.py`** ✅ **4 tests**（AsyncMock pattern；read + write/evict raise + time_scale filter）
- [x] **`test_tenant_layer.py`** ✅ **6 tests**（含 short_term reject + tenant required）
- [x] **`test_role_layer.py`** ✅ **3 tests**（write/evict raise + read returns hints）
  - 累計 Day 2 整體 **31 tests** ✅（超 plan 26；plan + 5 額外 edge cases）
  - DoD：31/31 pass ✅

### 2.9 Day 2 commit
- [x] **commit Day 2** ✅ Commit `f7d0614 feat(memory, sprint-51-2): 5-layer concrete impl + 31 unit tests (Day 2)` (12 files / +1483 / 0 del)
  - Msg：`feat(memory, sprint-51-2): 5-layer concrete impl + 31 unit tests (Day 2)`
  - 驗證：mypy 62 src clean / pytest unit/agent_harness/memory 31 passed / wider sanity 104 passed + 1 platform-skip
  - Day 2 actual ~2h vs plan 7h ≈ **29%**（V2 cumulative trend 20-25%；Day 2 略高因 mock pattern 設計時間）
  - 新增 **CARRY-029**：SessionLayer Redis backend（infrastructure/cache 待 Phase 52.x ship 真 client）

---

## Day 3 — Retrieval + Extraction + ConflictResolver + tests（估 6h / 實際 ~1.5h ≈ 25%）

### 3.1 `memory/retrieval.py`
- [x] **`MemoryRetrieval` 類別 — 跨 layer 多軸 search** ✅
  - `async def search(query, scopes, time_scales, top_k, tenant_id, user_id) -> list[MemoryHint]`
  - 內部：對每個指定 scope 並行呼叫 `layer.read()` → merge → 按 `relevance_score * confidence` 排序 → return top_k
  - 加 trace context 埋點（per `observability-instrumentation.md`）
  - DoD：mypy strict clean；trace span 名稱 `memory_retrieval_search`

### 3.2 `memory/conflict_resolver.py`
- [x] **4 條規則實作** ✅ session > user > role > tenant > system 優先序；Rule 4 raise `RequiresHumanReviewError`
  - rule 1：confidence ≥ 0.8 直接勝出
  - rule 2：last_verified_at < 7 day 最新值
  - rule 3：layer specificity（user > role > tenant > system；session 邊界 case）
  - rule 4：HITL fallback stub（51.2 raise `RequiresHumanReviewError`，53.3 接 request_clarification）
  - DoD：mypy strict clean

### 3.3 `memory/extraction.py`
- [x] **`MemoryExtractor` — session → user 萃取（手動觸發）** ✅ 透過 ChatRequest + ChatClient ABC（中性）；JSON tolerant parser；0 LLM SDK leak
  - `async def extract_session_to_user(session_id, tenant_id, user_id, chat_client) -> list[MemoryHint]`
  - 內部：讀 session messages → LLM judge prompt（透過 ChatClient ABC，**禁止 import openai/anthropic**）→ 萃取候選 hints → 寫入 user_layer
  - DoD：grep 確認 0 LLM SDK leak

### 3.4 Unit tests — Retrieval / ConflictResolver / Extraction
- [x] **`test_retrieval.py`** ✅ **8 tests**（tenant required / layer dispatch / session_id routing / top_k / sort / exception isolation / time_scales prop / unmapped scopes）
- [x] **`test_conflict_resolver.py`** ✅ **8 tests**（超 plan 6；含 single-hint shortcut + empty raise + Rule 1 skipped when 2 high-conf）
- [x] **`test_extraction.py`** ✅ **4 tests**（超 plan 3；happy path + empty messages + invalid JSON + prose-around-JSON 用 MockChatClient）
  - 累計 Day 3 整體 **20 tests** ✅（超 plan 17；plan + 3 額外 edge cases）
  - DoD：20/20 pass ✅

### 3.5 Day 3 commit
- [x] **commit Day 3** ✅ Commit `948fcd5 feat(memory, sprint-51-2): retrieval + conflict_resolver + extraction + 20 tests (Day 3)` (6 files / +843 / 0 del)
  - Msg：`feat(memory, sprint-51-2): retrieval + conflict_resolver + extraction + 20 tests (Day 3)`
  - 驗證：mypy 65 src clean / pytest unit/agent_harness/memory 51 passed / wider sanity 124 passed + 1 platform-skip
  - Day 3 actual ~1.5h vs plan 6h ≈ **25%**（V2 cumulative 21-29%；落區間內）

---

## Day 4 — 工具 placeholder → real handler + integration tests（估 5h / 實際 ~1.5h ≈ 30%）

### 4.1 `tools/memory_tools.py` schema 擴展
- [x] **`MEMORY_SEARCH_SPEC` schema 加 `time_scales` 參數** ✅ + `MEMORY_WRITE_SPEC` 加 `time_scale` + `confidence`；移除 placeholder tag
  - JSON Schema：`{"type": "array", "items": {"enum": ["short_term","long_term","semantic"]}, "default": ["long_term"]}`
  - DoD：JSONSchema validate fixture 通過

### 4.2 `memory_search_handler` real impl
- [x] **`make_memory_search_handler(retrieval)` factory** ✅ — 路由到 MemoryRetrieval；JSON serialized list[MemoryHint]；placeholder 保留為 dev fallback
  - 從 `ToolCall.arguments` 解析 query/scopes/time_scales/top_k
  - 路由到 `MemoryRetrieval.search()`
  - 序列化 list[MemoryHint] 為 JSON string return
  - DoD：handler 不再 raise NotImplementedError

### 4.3 `memory_write_handler` real impl
- [x] **`make_memory_write_handler(layers)` factory** ✅ — scope=system 拒絕；scope=session 路由 session_id 槽；session 層 short_term-only 約束 + tenant 層 long_term-only 約束 honor
  - 從 ToolCall 解析 scope/key/content/time_scale
  - 路由到對應 `layer.write()`
  - `scope=system` 拒絕並 return error JSON
  - DoD：write → search 整合通過

### 4.4 移除 placeholder tag + register
- [x] **`tags=("builtin", "memory", "placeholder")` → `tags=("builtin", "memory")`** ✅
- [x] **`agent_harness/tools/__init__.py register_builtin_tools` wire memory_handlers** ✅（取代 plan 的 `business_domain/_register_all.py`，因 51.1 memory 在 builtin tools 不在 business tools）
  - DoD 微調：`register_builtin_tools(memory_retrieval=..., memory_layers=...)` 注入時走 real handler；無注入時走 placeholder（dev fallback）

### 4.5 Integration tests — memory tools via registry
- [x] **`tests/integration/memory/test_memory_tools_integration.py`** ✅ **8 tests**（超 plan 6）
  - test_memory_write_then_search_via_registry
  - test_memory_write_system_scope_rejected
  - test_memory_search_default_scopes
  - test_memory_search_with_time_scales_filter
  - test_memory_search_top_k_limit
  - test_memory_handler_no_longer_raises_not_implemented
  - DoD：6/6 pass

### 4.6 17.md §3.1 sync
- [x] **更新 `17-cross-category-interfaces.md` §3.1** ✅ memory_search/memory_write rows 移除「51.1 placeholder」標記、加註「51.2 Day 4 ships real handler」；memory_extract row 改為 internal worker 註記
  - `memory_search` / `memory_write` 移除「51.1 placeholder」標記
  - 新增「51.2 real handler」備註
  - DoD：grep 確認 placeholder 字串只剩 51.0 echo / memory_extract

### 4.7 17.md §4.1 sync — MemoryAccessed event
- [x] **`MemoryAccessed` event payload 補 `time_scale` / `confidence`** ✅ + 加 `scope` / `verify_before_use` / `tenant_id`
  - DoD：event types 與 retrieval.py 埋點 attributes 一致

### 4.8 Day 4 commit
- [x] **commit Day 4** ✅ → see commit hash in Day 4 commit footer below
  - Msg：`feat(memory, sprint-51-2): real memory_tools handlers + register_builtin_tools wiring + 8 integration tests (Day 4)`
  - 驗證：mypy 65 src clean / pytest unit + integration/memory **132 passed + 1 platform-skip**
  - Day 4 actual ~1.5h vs plan 5h ≈ **30%**（V2 cumulative 25-30%；落區間內）
  - Plan 偏差 1：plan 寫 "business_domain/_register_all.py wire" → 改為 `agent_harness/tools/__init__.py register_builtin_tools`（51.1 memory 屬 builtin 非 business）
  - Plan 偏差 2：tests 6 → 實際 8（+2 edge cases：missing query / unknown scope）
  - 額外 fix：刪除 `tests/unit/agent_harness/memory/__init__.py` + `tests/integration/memory/__init__.py`（pytest 套件名衝突 — Day 2 加錯，convention 為 path-based discovery 不放 __init__.py）
  - 新增 **CARRY-030**：tenant 上下文目前從 ToolCall.arguments 讀（loop 預注入），未來改 ExecutionContext threading（Phase 53.3 / 並進 CARRY-023）

---

## Day 5 — Tenant isolation + 「線索→驗證」demo + retro + closeout（估 4h）

### 5.1 跨 tenant red-team test
- [ ] **`tests/integration/memory/test_tenant_isolation.py`** ~5 tests
  - test_tenant_a_search_zero_leak_from_tenant_b
  - test_tenant_a_write_isolated_storage
  - test_session_redis_key_prefix_per_tenant
  - test_user_layer_query_filtered_by_tenant_id
  - test_extraction_worker_no_cross_tenant_pollution
  - DoD：5/5 pass；0 leak

### 5.2 「線索→驗證」e2e demo
- [ ] **`tests/e2e/test_lead_then_verify_workflow.py`** ~2 tests
  - test_agent_uses_stale_hint_then_verifies_with_mock_tool
    - Setup：write user hint with `verify_before_use=True` + `last_verified_at=30d ago`
    - Trigger：agent loop with query referencing hint
    - Assert：agent 呼叫 `mock_crm_search_customer` 驗證
    - Assert：當 mock 結果與 hint 不一致 → 觸發 `memory_write` 更新
  - test_lead_then_verify_consistent_path（一致時直接用，不重複呼叫工具）
  - DoD：2/2 pass

### 5.3 Extraction worker integration test
- [ ] **`tests/integration/memory/test_extraction_worker.py`** ~3 tests
  - test_extract_5_message_session_creates_user_hints
  - test_extraction_uses_mock_chat_client（無 LLM SDK leak）
  - test_extraction_writes_under_correct_tenant_user
  - DoD：3/3 pass

### 5.4 Phase 51 README 更新（DONE 標記）
- [ ] **更新 README — Sprint 51.2 row 改為 ✅ DONE + 完成日期**
  - DoD：cumulative table Cat 3 Level 0 → **Level 3** ✅；Phase 51 progress 3/3 = 100%；V2 cumulative 9/22 sprints = 41%

### 5.5 Sprint 51.2 retrospective
- [ ] **撰寫 `docs/03-implementation/agent-harness-execution/phase-51/sprint-51-2/retrospective.md`**
  - 5 必述：outcome / estimates accuracy / went-well / surprises / Action Items
  - 列入 CARRY-026 / 027 / 028 + 51.1 留下 22/23/24/25 carry forward
  - DoD：retro 文件存在；含估時表 + DoD 驗收表

### 5.6 Sprint 51.2 progress.md（如分日累進，最後 closeout）
- [ ] **`docs/03-implementation/agent-harness-execution/phase-51/sprint-51-2/progress.md`**
  - Day 0-5 累進紀錄
  - DoD：每 Day 至少一段（estimate vs actual）

### 5.7 全綠驗收
- [ ] **`pytest backend/tests` 全綠**
  - 預期 baseline 315 → ~340 PASS / 0-1 platform-skip
- [ ] **`mypy backend/src --strict` clean**
- [ ] **`black --check && isort --check`** clean
- [ ] **4/5 V2 lints OK**（AP-1 known skip）
- [ ] **`grep -r "from openai\|from anthropic" backend/src/agent_harness/memory/`** = 0
- [ ] **`grep -r "NotImplementedError" backend/src/agent_harness/tools/memory_tools.py`** = 0

### 5.8 Day 5 closeout commit
- [ ] **commit Day 5**
  - Msg：`feat(memory, sprint-51-2): tenant isolation + lead-then-verify demo + Cat 3 to Level 3 (Day 5 closeout)`

### 5.9 等用戶 review + decide merge
- [ ] **🚧 等用戶 review**：merge to main pattern 51.0 / 51.1 已用過 — 用戶決定本 sprint 走同樣 pattern 或先 review 再 merge

---

## 完成驗收（per Sprint 51.2 DoD）

| # | Item | 驗收 cmd / DoD |
|---|------|---------------|
| 1 | Test suite 全綠 | `pytest backend/tests` ≥ 340 PASS / 0-1 platform-skip |
| 2 | mypy strict src clean | `python -m mypy backend/src --strict` |
| 3 | black --check clean | `black --check backend/src` |
| 4 | flake8 / isort clean | 同 51.1 流程 |
| 5 | 4/5 V2 lints OK | AP-1 known skip |
| 6 | 0 LLM SDK leak in memory/ | `grep -r "from openai\|from anthropic" backend/src/agent_harness/memory/` |
| 7 | 0 NotImplementedError in memory_tools | `grep "NotImplementedError" backend/src/agent_harness/tools/memory_tools.py` |
| 8 | MemoryHint 含 5 新欄位 | `grep -E "verify_before_use\|time_scale\|confidence" backend/src/agent_harness/_contracts/memory.py` |
| 9 | 5 layer 全在 layers/ | `ls backend/src/agent_harness/memory/layers/*.py` |
| 10 | tenant isolation 5 tests pass | 見 5.1 |
| 11 | 「線索→驗證」demo 2 tests pass | 見 5.2 |
| 12 | 17.md §1.1 §2.1 §3.1 §4.1 同步 | 各 grep 確認 |
| 13 | Phase 51 README cumulative 標 Cat 3 Level 3 | grep 確認 |

---

**維護**：用戶 + AI 助手共同維護
**Created**：2026-04-30（Sprint 51.1 closeout 後當日起草）
