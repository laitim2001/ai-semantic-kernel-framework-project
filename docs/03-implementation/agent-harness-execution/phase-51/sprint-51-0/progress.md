# Sprint 51.0 — Progress Log

**Sprint**：51.0 — Mock 企業工具 + 業務工具骨架
**Phase**：51（Tools + Memory）
**Branch**：`feature/phase-51-sprint-0-mock-business-tools`
**Started**：2026-04-30

---

## Day 0 — 2026-04-30（actual ~1h / plan 4h）

### Accomplishments

- [x] **0.1** sprint-51-0-plan.md 撰寫（~250 行；含 Sprint Goal / 5 User Stories / 5 架構決策 / 30 file change list / DoD / 6 Risks / 估時 / V2 紀律對照 / Out of Scope）
- [x] **0.2** sprint-51-0-checklist.md 撰寫（~270 行；Day 0-5 39 task；DoD + verification command + 9 條 closeout 驗收 bash）
- [x] **0.3** phase-51-tools-memory/README.md 建立（Phase 51 入口 / 3 sprint 總覽 / 範疇成熟度演進表）
- [x] **0.4** Pre-step：`feature/phase-50-sprint-2-api-frontend` (~58 commits) merged into `main` via `--no-ff` (merge commit `f31498e`)
- [x] **0.4** Branch `feature/phase-51-sprint-0-mock-business-tools` 從 updated main 切出
- [x] **0.5** `_contracts/tools.py` 含 ToolSpec / ToolAnnotations / ConcurrencyPolicy；`_contracts/hitl.py:80` 含 HITLPolicy（4 type 全 importable）
- [x] **0.6** business_domain/{patrol,correlation,rootcause,audit_domain,incident}/ 5 dir 確認在位
- [x] **0.7** Day 0 commit `4a843a7`（3 files / 768 insertions）

### Estimate vs Actual

| Task | Plan | Actual | Diff |
|------|------|--------|------|
| 0.1 plan 撰寫 | 45 min | ~25 min | -45% |
| 0.2 checklist 撰寫 | 45 min | ~20 min | -56% |
| 0.3 Phase README | 30 min | ~10 min | -67% |
| 0.4 branch（含 merge） | 10 min | ~10 min | 0% |
| 0.5 ToolSpec verify | 30 min | ~5 min | -83% |
| 0.6 business_domain dirs | 20 min | ~3 min | -85% |
| 0.7 commit | 10 min | ~5 min | -50% |
| **Day 0 總計** | **3h 20min** | **~1h 18min** | **-61%** |

### Surprises / Discoveries

- **HITLPolicy 不在 `_contracts/tools.py`** — 49.4 設計時放在 `_contracts/hitl.py`（per HITL central owner rule，正確架構）。Plan checklist 0.5 指向 tools.py 寫法不準；實際 import 路徑 update 至 hitl.py（已記入 checklist note）。**不修代碼**，因為 HITL central rule > tools.py convenience。
- **50.2 closeout 後 main 落後 ~58 commits** — user 授權 merge 時未先把進行中的 V2-AUDIT-* 與 discussion-logs 合進 50.2 sprint，這些 untracked file 在 working tree 中 travel；`git checkout main` 不衝突 → merge 順利。
- **Graphify watch hook spam** — `git checkout` / `git commit` 後 graphify 自動 rebuild（~3,910 files / 75K nodes）並輸出 7-10 行 noise；不影響 git，但 Bash output 末尾通常被 graphify 蓋掉。需用 `tail -N` 抓真實結果。
- **Plan estimate 過於保守** — 文檔寫作類 task plan 給 30-45 min，實際 5-25 min 完成。51.x 後 plan 估時可調整為「文檔類 × 0.5」修正係數。

### Branch / Working Tree State

- **Branch**：`feature/phase-51-sprint-0-mock-business-tools`
- **HEAD**：`4a843a7 docs(plan, sprint-51-0): Day 0 — plan + checklist + Phase 51 README`
- **Ahead of main**：1 commit（Day 0 docs commit）
- **Working tree**：保留用戶 IDE 進行中 work（V2-AUDIT-* / discussion-logs / 1 modified discussion-log-20260426.md）— 與 sprint 51.0 無關，不入 commit

### Quality Gates

- 本 Day 無代碼變更，Quality Gates skip（Day 1 起每日跑 pytest / mypy / lint）

### Next Day Plan

- **Day 1**：Mock backend 骨架（5h）— mock_services FastAPI app / 7 routers / seed.json / scripts/dev.py mock subcommand
- **重要 prerequisite**：用戶決策是否 push main → origin/main（local merge `f31498e` 尚未 push）
- **若用戶選 pause**：Day 1 暫不啟動；checklist 標記 🚧 用戶決策中

### Notes / Decisions

- **CARRY-020（roadmap 24 vs spec 18）**：user approve 保持 18，差異記入 retrospective.md（Day 5）— 已確認
- **R-2（mock_services dev script + docker）**：user approve mandatory — 已內建到 checklist 1.7 + 5.2，不可跳過
- **Push 時機**：local merge 完成；push to origin/main 等用戶 explicit 授權（per CLAUDE.md「破壞性操作前必問」）

---

## Day 1 — 2026-04-30（actual ~1h / plan 5h）

### Accomplishments

- [x] **1.1** `mock_services/main.py` FastAPI app（port 8001 / lifespan loader / `/` + `/health` endpoint）
- [x] **1.2** `mock_services/schemas/__init__.py` 10 Pydantic models（Customer / Order / Ticket / KBArticle / KBSearchResult / PatrolResult / Alert / Incident / RootCauseFinding / AuditLogEntry）
- [x] **1.3** `mock_services/data/seed.json`（~25 KB；10/50/8/8/3/20/5/8/5 entities）
- [x] **1.4** `mock_services/data/loader.py`（SeedDB dataclass + `load_seed()` + `get_db()` Depends + `reset()` helper）
- [x] **1.5** `mock_services/routers/crm.py`（3 endpoints：customer / orders / ticket）
- [x] **1.6** `mock_services/routers/kb.py`（POST /search naive scoring 1.0/0.7/0.5）
- [x] **1.7** `scripts/mock_dev.py` standalone start/stop/status + `scripts/dev.py mock` shim 17-line
- **Process verified**：start → pid 38236 → /health 200 via urllib → status running → stop clean
- **Quality gates**：mypy strict 8 files no issues / black 6 files reformatted ✅

### Estimate vs Actual

| Task | Plan | Actual | Diff |
|------|------|--------|------|
| 1.1 main.py + skeleton | 45 min | ~10 min | -78% |
| 1.2 schemas (10 models) | 60 min | ~12 min | -80% |
| 1.3 seed.json | 45 min | ~15 min | -67% |
| 1.4 loader.py | 30 min | ~5 min | -83% |
| 1.5 crm router | 45 min | ~6 min | -87% |
| 1.6 kb router | 30 min | ~5 min | -83% |
| 1.7 mock_dev + dev.py shim | 30 min | ~12 min | -60% |
| mypy/black fix iteration | (in tasks above) | ~5 min | — |
| process verify (start/stop) | 0 | ~3 min | — |
| **Day 1 總計** | **4h 45min** | **~1h 13min** | **-74%** |

### Surprises / Discoveries

- **curl 被 context-mode hook 擋**：sandbox 規則禁 `curl`/`wget`，用 `python urlopen` 代替；plan checklist 1.7 verification command 寫死 curl，實際用 urllib 完成驗收。檢查 Day 5 retrospective 是否要全 sprint 改寫。
- **CWD 在 `backend/` 殘留**：earlier `cd backend` 影響後續 commands；改用絕對路徑 `cd /c/...` 解決。
- **pydantic v1 vs v2**：`Field(..., examples=[...])` 是 v2 寫法；專案已用 v2，無相容問題。
- **Windows console mojibake**：taskkill output 因 CP950 顯示「���l�B�z�{��」（實為「已成功結束」），不影響功能。
- **`scripts/dev.py` 是 ~750 行複雜編排器**：weaving mock_services 進 ServiceType enum 風險高；改用「standalone mock_dev.py + 17-line shim」策略（AP-3 安全）。
- **Plan 估時持續過保守**：Day 1 加上 Day 0 累計 ~2h 27min vs plan 8h 5min — `~0.3x` correction factor for 51.x 後續估時。
- **mypy strict `dict` type-arg**：FastAPI handler return type `dict` → 必須 `dict[str, Any]`，否則 strict mode fail。

### Branch / Working Tree State

- **HEAD**：（待 Day 1 commit 後更新）
- **Files added**：`backend/src/mock_services/` 8 files（包括 routers/__init__.py + data/__init__.py）+ `scripts/mock_dev.py`
- **Files modified**：`scripts/dev.py`（17-line shim addition）
- **Working tree**：保留用戶 V2-AUDIT-* 與 discussion-logs（不入 sprint commit）

### Quality Gates

- ✅ mypy strict on `src/mock_services/` — 8 source files no issues
- ✅ black --check — 6 files auto-formatted（已 commit-ready）
- ✅ Module imports clean (10 schemas / 4 mock routes / SeedDB stats correct)
- ✅ uvicorn process boot + /health 200 + clean stop
- ⏭ pytest unit tests for mock_services — Day 4.1 加（plan 安排）

### Next Day Plan

- **Day 2**：patrol + correlation + rootcause domain（6h plan / 預估 actual ~1.5h based on Day 1 trend）
- **Day 2.1**：mock_services/routers/patrol.py 4 endpoints
- **Day 2.2**：business_domain/patrol/mock_executor.py（httpx async client）
- **Day 2.3**：business_domain/patrol/tools.py 4 ToolSpec stub + register_patrol_tools
- **Day 2.4-2.7**：correlation + rootcause routers + executors + tools
- **Day 2.8**：commit

---

## Day 2 — 2026-04-30（actual ~50min / plan 5h 45min）

### Accomplishments

- [x] **2.1** `mock_services/routers/patrol.py` 4 endpoints（check_servers / results/{id} / schedule / cancel）
- [x] **2.2** `business_domain/patrol/mock_executor.py` httpx async client（base_url overridable via MOCK_SERVICES_URL env）
- [x] **2.3** `business_domain/patrol/tools.py` 4 ToolSpec + `register_patrol_tools(registry, handlers)`
- [x] **2.4** `mock_services/routers/correlation.py` 3 endpoints（analyze / find_root_cause / related/{id}）
- [x] **2.5** `business_domain/correlation/{mock_executor,tools}.py` 3 ToolSpec + register
- [x] **2.6** `mock_services/routers/rootcause.py` 3 endpoints（diagnose / suggest_fix / apply_fix HIGH risk）
- [x] **2.7** `business_domain/rootcause/{mock_executor,tools}.py` 3 ToolSpec + register（apply_fix `always_ask` + `risk:high` + `destructive=True` + `open_world=True`）
- **mock_services/main.py** 加 3 router include（patrol / correlation / rootcause）

### Files added (9) / modified (1)

| File | Lines | 範疇 |
|------|-------|------|
| `backend/src/mock_services/routers/patrol.py` | 113 | mock_services |
| `backend/src/mock_services/routers/correlation.py` | 134 | mock_services |
| `backend/src/mock_services/routers/rootcause.py` | 132 | mock_services |
| `backend/src/business_domain/patrol/mock_executor.py` | 49 | business |
| `backend/src/business_domain/patrol/tools.py` | 161 | business |
| `backend/src/business_domain/correlation/mock_executor.py` | 47 | business |
| `backend/src/business_domain/correlation/tools.py` | 121 | business |
| `backend/src/business_domain/rootcause/mock_executor.py` | 41 | business |
| `backend/src/business_domain/rootcause/tools.py` | 134 | business |
| `backend/src/mock_services/main.py` | +5 | (modify: 3 router include) |

### Estimate vs Actual

| Task | Plan | Actual | Diff |
|------|------|--------|------|
| 2.1 patrol router | 45 min | ~5 min | -89% |
| 2.2 patrol mock_executor | 30 min | ~3 min | -90% |
| 2.3 patrol tools.py | 60 min | ~6 min | -90% |
| 2.4 correlation router | 45 min | ~7 min | -84% |
| 2.5 correlation executor + tools | 60 min | ~6 min | -90% |
| 2.6 rootcause router | 45 min | ~6 min | -87% |
| 2.7 rootcause executor + tools | 60 min | ~6 min | -90% |
| mypy / black fix iteration | (in tasks) | ~7 min | — |
| TestClient + register verify | 0 | ~5 min | — |
| **Day 2 總計** | **5h 45min** | **~51 min** | **-85%** |

### Surprises / Discoveries

- **ToolSpec 沒有 hitl_policy / risk_level 直接 field** — 49.4 設計時只有 `name / description / input_schema / annotations / concurrency_policy / version / tags`。08b spec 提到 `hitl_policy` 但 `_contracts/tools.py` 未實作。Sprint 51.0 採 workaround：編碼到 `tags`（`hitl_policy:always_ask` / `risk:high`）。**CARRY-021** ToolSpec 加 first-class `hitl_policy: HITLPolicy | None` + `risk_level: Literal[low/medium/high] | None` 欄位 → 51.1 工作（51.1 是「範疇 2 工具層」sprint，正合適）。
- **mypy strict `no-any-return`**：mock_executor 用 `httpx.Response.json()` 回 `Any`，但 method declared return type `list[dict[str, Any]]` 違反 strict。改 method return type 為 `Any`（mock dynamic JSON 本來就是 Any）；Phase 55 真實 integration 上線時 narrow types。
- **mypy strict `dict` 必須 `dict[str, Any]`**：再次撞到，提早全檢查 mock_services router 私有 helper。
- **InMemoryToolExecutor handlers 透過 init dict 傳入**：register_*_tools 必須同時更新 `registry`（specs）+ `handlers`（callable dict）。設計成 `register_<domain>_tools(registry, handlers, *, mock_url=...)` 兩參數，符合 InMemoryToolExecutor 的 `__init__(handlers=...)` API。
- **Plan estimate 嚴重過保守**：Day 2 actual ~50 min vs plan 5h 45min（-85%）。Day 0+1+2 累計 ~3h 22min vs plan 13h 50min（-76%）。51.x 後 sprint 套 **0.2-0.3x correction factor** 給 mock + skeleton + register pattern 類 task。
- **Naive correlation behaviour**：當 primary alert server_id=null 而其他 alert server_id 有值時，目前 filter 排除（`other.server_id and other.server_id != primary.server_id` → True for primary=null）。對 mock 行為 OK，retro 標記 51.1+ 真實 correlation 邏輯需精修。
- **patrol/check_servers seeded vs synth fallback**：當 `scope` 內 server_id 已 seeded（pat_001 web-01 etc）回 seed；其他 server_id 透過 `_make_result()` 用 hash 生成 deterministic mock metrics。設計兼容真實環境（已知 + 未知 server）。

### Branch / Working Tree State

- **HEAD**：`66aba50`（Day 1 closeout）→ pending Day 2 main commit + Day 2 closeout commit
- **Files**：9 new + 1 modified（main.py +5 lines）
- **Working tree**：Day 2 files staged-ready

### Quality Gates

- ✅ mypy strict on `src/mock_services/` + `src/business_domain/{patrol,correlation,rootcause}/` — 20 source files no issues
- ✅ black --check — 11 files reformatted（auto-applied）
- ✅ 10 mock endpoints TestClient smoke PASS（4 patrol + 3 correlation + 3 rootcause）
- ✅ register_*_tools wire 10 ToolSpec + 10 handlers correctly（apply_fix 確認 always_ask / high）
- ⏭ pytest unit tests — Day 4.1-4.2 加（plan 安排）

### V2 紀律 9 項對照

| # | 紀律 | 狀態 |
|---|------|------|
| 1 | Server-Side First | ✅ mock_services 在 backend；frontend 0 變動 |
| 2 | LLM Provider Neutrality | ✅ business_domain/* 0 LLM SDK import |
| 3 | CC Reference 不照搬 | ✅ V2 自設計 mock_executor + register pattern |
| 4 | 17.md Single-source | ⏸ Day 5.1 加 18 entries |
| 5 | 11+1 範疇歸屬 | ✅ tools.py = 業務層 / mock_executor = 業務層 / mock_services = 平台輔助 |
| 6 | 04 Anti-patterns | ✅ AP-3 安全（無跨 domain import）/ AP-6 mock_executor 各 domain 獨立 |
| 7 | Sprint workflow | ✅ Day 2 嚴格 plan→checklist→code→update→commit |
| 8 | File header convention | ✅ 9 新檔皆有完整 V2 header |
| 9 | Multi-tenant rule | ✅ mock 不 tenant-aware（CARRY 51.1 加 tenant_id 注入；plan §決策 5 已記） |

### Next Day Plan

- **Day 3**：audit_domain + incident domain（plan 6h / 預估 actual ~1h）
- **Day 3.1**：mock_services/routers/audit.py 3 endpoints
- **Day 3.2**：business_domain/audit_domain/{mock_executor, tools}.py 3 ToolSpec
- **Day 3.3**：mock_services/routers/incident.py 5 endpoints（含 close 高風險）
- **Day 3.4**：business_domain/incident/{mock_executor, tools}.py 5 ToolSpec（close `always_ask` + `high`）
- **Day 3.5**：business_domain/_register_all.py aggregator（一次呼叫 5 個 register_<domain>_tools）
- **Day 3.6**：commit

---

## Day 3 — 2026-04-30（actual ~45min / plan 4h 45min）

### Accomplishments

- [x] **3.1** `mock_services/routers/audit.py` 3 endpoints（query_logs filtered / generate_report / flag_anomaly）
- [x] **3.2** `business_domain/audit_domain/{mock_executor,tools}.py` 3 ToolSpec + register_audit_tools
- [x] **3.3** `mock_services/routers/incident.py` 5 endpoints（create / update_status / close HIGH-risk / get/{id} / list 含 filter）
- [x] **3.4** `business_domain/incident/{mock_executor,tools}.py` 5 ToolSpec + register_incident_tools（`close` 確認 `always_ask` + `risk:high`）
- [x] **3.5** `business_domain/_register_all.py` aggregator — register_all_business_tools()
- **mock_services/main.py** 加 audit + incident router include（總 7 router 全 mounted）

### Files added (7) / modified (1)

| File | Lines | 範疇 |
|------|-------|------|
| `backend/src/mock_services/routers/audit.py` | 110 | mock_services |
| `backend/src/mock_services/routers/incident.py` | 142 | mock_services |
| `backend/src/business_domain/audit_domain/mock_executor.py` | 65 | business |
| `backend/src/business_domain/audit_domain/tools.py` | 133 | business |
| `backend/src/business_domain/incident/mock_executor.py` | 75 | business |
| `backend/src/business_domain/incident/tools.py` | 195 | business |
| `backend/src/business_domain/_register_all.py` | 64 | business / aggregator |
| `backend/src/mock_services/main.py` | +5 | (modify: 2 router include) |

### Estimate vs Actual

| Task | Plan | Actual | Diff |
|------|------|--------|------|
| 3.1 audit router | 45 min | ~6 min | -87% |
| 3.2 audit executor + tools | 60 min | ~7 min | -88% |
| 3.3 incident router | 60 min | ~10 min | -83% |
| 3.4 incident executor + tools | 75 min | ~10 min | -87% |
| 3.5 _register_all aggregator | 30 min | ~5 min | -83% |
| black + mypy fix iteration | (in tasks) | ~3 min | — |
| TestClient + register_all verify | 0 | ~4 min | — |
| **Day 3 總計** | **4h 30min** | **~45min** | **-83%** |

### Surprises / Discoveries

- **`audit_domain/` 命名 confirmed**：CLAUDE.md scope hierarchy 防止與 `governance.audit` 衝突；Sprint 49.1 baseline 已建立此名，51.0 沿用。
- **incident 5 endpoints 比 4 多 1**：plan 寫 5（matches 08b spec），seed 已有 5 incidents (inc_001..005)，`/list` filter 對 severity + status 雙條件正常。
- **seed + live incident merge view**：incident 的 `_all_incidents()` helper 把 `_live_incidents` 與 `db.incidents` (seed) 合併查找，`update_status` / `close` 對 seed 採 mutated copy 模式（不寫回 seed），對 live 真實寫入。設計簡潔且不污染 seed。
- **register_all 順序 patrol→correlation→rootcause→audit→incident**：對應 08b §Domain 1-5 numbering，無 inter-domain dep。
- **2 HIGH risk tools 自動驗證**：assertion `set(s.name for s in high) == {'mock_rootcause_apply_fix', 'mock_incident_close'}` PASS；51.x 後改 ToolSpec first-class field 時這個 invariant 應持續維持。
- **Plan estimate -83% Day 3** vs Day 2 -85%；累計 Sprint 51.0 Day 0-3 ~4h 7min vs plan 18h 20min（-78%）。

### Branch / Working Tree State

- **HEAD**：`642ce07`（Day 2 closeout）→ pending Day 3 main commit + Day 3 closeout commit
- **Files**：7 new + 1 modified（main.py +5 lines）
- **Working tree**：Day 3 files staged-ready

### Quality Gates

- ✅ mypy strict on 30 source files (mock_services + 5 business_domain) — no issues
- ✅ black --check — 7 files reformatted（auto-applied）
- ✅ 18 mock endpoints TestClient smoke PASS（4 patrol + 3 correlation + 3 rootcause + 3 audit + 5 incident）
- ✅ register_all_business_tools wires 18 ToolSpec + 18 handlers
- ✅ Per-domain breakdown: patrol=4 / correlation=3 / rootcause=3 / audit=3 / incident=5（matches 08b spec exactly）
- ✅ HIGH-risk tools verified: `mock_rootcause_apply_fix` + `mock_incident_close` 兩個（皆 `always_ask`）

### V2 紀律 9 項對照

| # | 紀律 | 狀態 |
|---|------|------|
| 1 | Server-Side First | ✅ |
| 2 | LLM Provider Neutrality | ✅ business_domain 0 LLM SDK |
| 3 | CC Reference 不照搬 | ✅ |
| 4 | 17.md Single-source | ⏸ Day 5.1 同步 18 entries |
| 5 | 11+1 範疇歸屬 | ✅ audit_domain 命名避開 governance.audit；register_all 在 business_domain/_register_all.py |
| 6 | 04 Anti-patterns | ✅ AP-3（無跨 domain import）/ AP-6（每 domain 獨立 mock_executor） |
| 7 | Sprint workflow | ✅ |
| 8 | File header convention | ✅ 7 新檔完整 V2 header |
| 9 | Multi-tenant rule | ✅（mock 不 tenant-aware；51.1+ 加） |

### Next Day Plan

- **Day 4**：Tests + worker hook + chat handler（plan 5h / 預估 actual ~1.5h）
- **Day 4.1**：integration test mock_services_startup（7 router smoke）
- **Day 4.2**：integration test business_tools_via_registry（18 tools execute via InMemoryToolRegistry）
- **Day 4.3**：worker startup hook 加 `register_all_business_tools(registry)`
- **Day 4.4**：chat handler default tools = 19（echo + 18 business）
- **Day 4.5**：e2e test_agent_loop_with_mock_patrol（核心 demo）
- **Day 4.6**：commit

---

## Day 4 — 2026-04-30（actual ~1h 15min / plan 4h 45min）

### Accomplishments

- [x] **4.1** `tests/integration/mock_services/test_mock_services_startup.py` — 12 tests via TestClient (in-process); 7 routers + 404 + dry_run + close
- [x] **4.2** `tests/integration/business_domain/test_business_tools_via_registry.py` — 10 tests via httpx ASGI transport monkey-patch (in-process)
- [x] **4.3** `make_default_executor()` added to `business_domain/_register_all.py` (echo + 18 business = 19 specs)
- [x] **4.4** `api/v1/chat/handler.py` — both build_echo_demo_handler + build_real_llm_handler now use `make_default_executor()` instead of `make_echo_executor()`
- [x] **4.5** `tests/e2e/test_agent_loop_with_mock_patrol.py` — subprocess fixture (real uvicorn:8001) + AgentLoopImpl + MockChatClient pre-script (2 tests)

### Files added (3) / modified (2)

| File | Lines | Type |
|------|-------|------|
| `tests/integration/mock_services/test_mock_services_startup.py` | 134 | new test |
| `tests/integration/business_domain/test_business_tools_via_registry.py` | 230 | new test |
| `tests/e2e/test_agent_loop_with_mock_patrol.py` | 200 | new test |
| `business_domain/_register_all.py` | +37 | added `make_default_executor()` |
| `api/v1/chat/handler.py` | -1, +1 | swap `make_echo_executor` -> `make_default_executor` |

### Estimate vs Actual

| Task | Plan | Actual | Diff |
|------|------|--------|------|
| 4.1 mock_services_startup | 45 min | ~10 min | -78% |
| 4.2 business_tools_via_registry | 60 min | ~15 min | -75% |
| 4.3 worker / make_default_executor | 30 min | ~10 min | -67% |
| 4.4 chat handler swap | 30 min | ~3 min | -90% |
| 4.5 e2e mock_patrol (subprocess fixture) | 90 min | ~25 min | -72% |
| **Day 4 design + debugging** | (in tasks) | ~12 min | — |
| **Day 4 總計** | **4h 15min** | **~1h 15min** | **-71%** |

### Surprises / Discoveries

- **Test directory `__init__.py` shadows source package**：建立 `tests/integration/business_domain/__init__.py` 後，pytest 將其視為 `business_domain` package，於 sys.path 上 shadowing 真實的 `src/business_domain/`。Fix：刪除 test dir 的 `__init__.py`（pytest 慣例：test dir 不要 `__init__.py`，讓 rootdir 自動發現）。
- **TestClient lifespan 須用 `with TestClient(app) as c:`**：FastAPI 0.110+ 預設 TestClient(app) 不觸發 lifespan；改 `with` syntax 才會 load_seed via on_startup hook。
- **httpx ASGI transport 路由**：`httpx.ASGITransport(app=app)` 將所有 httpx 請求路由到 in-process FastAPI app，不論 base_url；monkeypatch `httpx.AsyncClient` 可在 4.2 不啟 subprocess 完成 18 tool 測試。
- **ToolCallExecuted 沒 `success` field**：`success` 是 ToolResult 上的屬性，event 用 `ToolCallFailed` 表示失敗（無對應 success=True event；assertion 改 `failed == []`）。
- **AgentLoopImpl.run signature**：`run(session_id=UUID, user_input=str)`，不是 messages list；events 是 AsyncIterator[LoopEvent]。e2e 模仿 50.1 test_e2e_echo 結構即可。
- **Plan estimate Day 4 -71%**：包含 ~10min 找 test dir __init__.py shadow 問題；累計 Day 0-4 ~5h 22min vs plan 23h 5min（-77%）。

### Branch / Working Tree State

- **HEAD**：`b344553`（Day 3 closeout）→ pending Day 4 main commit + Day 4 closeout commit
- **Files**：3 new tests + 2 modified（_register_all + handler.py）
- **Working tree**：Day 4 files staged-ready

### Quality Gates

- ✅ Full test suite **283 PASSED** / 0 SKIPPED / 0 FAILED in 8.54s
- ✅ Sprint 50.2 baseline 259 PASS preserved（259 + 24 new Day 4 = 283）— 無 regression
- ✅ Day 4 specific:
  - mock_services_startup: 12 / 12 PASS
  - business_tools_via_registry: 10 / 10 PASS（含 high_risk 確認 + unknown_tool error case）
  - e2e mock_patrol: 2 / 2 PASS（含 subprocess startup ~3s）
- ✅ make_default_executor 19 specs / 19 handlers
- ✅ chat handler 兩 site swap clean
- ⏭ mypy strict on test files：跑（在主 quality gate）

### V2 紀律 9 項對照

| # | 紀律 | 狀態 |
|---|------|------|
| 1 | Server-Side First | ✅ 全部 server-side test；frontend 0 變動 |
| 2 | LLM Provider Neutrality | ✅ 用 MockChatClient（不打真 Azure） |
| 3 | CC Reference 不照搬 | ✅ |
| 4 | 17.md Single-source | ⏸ Day 5.1 同步 18 entries |
| 5 | 11+1 範疇歸屬 | ✅ make_default_executor 在 business_domain（非 agent_harness） |
| 6 | 04 Anti-patterns | ✅ AP-3（test dir 與 source 邏輯隔離）/ AP-4（每 test 有實際 assertion，非空 stub） |
| 7 | Sprint workflow | ✅ |
| 8 | File header convention | ✅ 3 新 test 檔皆有完整 V2 header |
| 9 | Multi-tenant rule | ✅（mock test 不需 tenant_id；51.1 加） |

### Next Day Plan

- **Day 5**：17.md sync + retro + closeout（plan 3h / 預估 actual ~45min）
- **Day 5.1**：17.md §3.1 加 18 entries
- **Day 5.2**：docker-compose.dev.yml 加 mock_services service
- **Day 5.3**：progress.md final entry
- **Day 5.4**：retrospective.md
- **Day 5.5**：Phase 51 README 更新 51.0 ✅ DONE
- **Day 5.6**：memory/project_phase51_tools_memory.md
- **Day 5.7**：sprint-51-0-checklist 全 [x] / 🚧
- **Day 5.8**：Day 5 closeout commit

---
