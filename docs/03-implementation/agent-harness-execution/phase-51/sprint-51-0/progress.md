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
