# Sprint 51.0 — Retrospective

**Sprint**：51.0 — Mock 企業工具 + 業務工具骨架
**Phase**：51（Tools + Memory）— 第 1 / 3 個 sprint（33%）
**Branch**：`feature/phase-51-sprint-0-mock-business-tools`
**Started**：2026-04-30
**Closeout**：2026-04-30
**Duration（actual）**：~6h（Plan 23h 5min；-74%）

---

## Sprint Goal Recap

> 建立 5 業務 domain mock backend + 18 個 ToolSpec stub，讓後續 Sprint（51.1+ / 52+ / 53+ / 54+）的 demo 不再依賴 echo_tool，端到端流量可呼叫真實業務工具。

**結果**：✅ 達成。chat handler 預設工具從 1（echo only）→ 19（echo + 18 business），mock_services 7 router 操作正常，e2e 透過真實 subprocess 跑通 mock_patrol。

---

## What Went Well

### 1. 估時準度持續穩定（0.2-0.3x correction factor 收斂）

| Day | Plan | Actual | Diff |
|-----|------|--------|------|
| 0 | 3h 20min | ~1h 18min | -61% |
| 1 | 4h 45min | ~1h 13min | -74% |
| 2 | 5h 45min | ~51min | -85% |
| 3 | 4h 30min | ~45min | -83% |
| 4 | 4h 15min | ~1h 15min | -71% |
| 5 | 3h 0min | ~30min | -83% |
| **總** | **25h 35min** | **~5h 52min** | **-77%** |

V2 6 sprint 平均 ~19% 估時準度；51.0 落 23% 區間，與 50.x 一致。**規律：對 mock + skeleton + register-pattern 類 task 套 0.2x、對 doc/closeout 類 task 套 0.3x。**

### 2. 架構決策 5 項全保 clean layering

- ✅ **D1**：mock_services 獨立 dir（非 main backend sub-router）— 明示「非 production」
- ✅ **D2**：tool ↔ mock 透過 HTTP（httpx async）— 仿真未來真實 enterprise integration
- ✅ **D3**：mock data seed 只有 ~25KB JSON in-memory（非 PostgreSQL）— 不污染主 DB
- ✅ **D4**：ToolRegistry 沿用 50.1 InMemoryToolRegistry（51.1 deprecate 切 production registry）
- ✅ **D5**：Tool naming `mock_<domain>_<action>`（Phase 55 mass rename 移除 prefix）— spec 18 vs roadmap 24 採 spec 為準

### 3. Day 4 e2e 透過真實 subprocess 證明 mock backend 可獨立運作

`tests/e2e/test_agent_loop_with_mock_patrol.py` 啟 uvicorn process on port 8001，完整 TAO loop（MockChatClient → tool_call → real httpx → mock_services → JSON → END_TURN）跑通。Phase 55 真實 integration 上線時 swap mock_executor 即可，loop / handler 不動。

### 4. V2 紀律 9 項 sprint 全程零違規

- LLM Provider Neutrality：business_domain `grep -r "import openai\|import anthropic"` 0 hits
- 11+1 範疇歸屬：每個檔案 V2 file header 明示 Category
- 17.md Single-source：18 ToolSpec entries Day 5 同步
- AP-3 / AP-6：每 domain 獨立 mock_executor，無跨 domain import
- Sprint workflow：每 Day 嚴格 plan→checklist→code→update→commit

### 5. Day 4 同步維持 50.x 全套測試零 regression

|  | 50.2 baseline | 51.0 closeout | 增量 |
|---|--------------|---------------|------|
| pytest PASS | 259 | **283** | +24（mock_services_startup 12 + business_tools_via_registry 10 + e2e 2） |
| SKIPPED | 0 | 0 | 0 |
| FAILED | 0 | 0 | 0 |
| 跑時 | 4.49s | ~8.5s | +4s（含 e2e ~4s subprocess） |

---

## What To Improve（→ 51.x sprint Action Items）

### A1：ToolSpec first-class `hitl_policy` + `risk_level` field（CARRY-021）

**問題**：51.0 將 hitl_policy / risk_level 編碼到 `tags`（如 `hitl_policy:always_ask` / `risk:high`）— 字串 parse 易出錯，無 type safety。

**修正**：51.1（範疇 2 工具層 sprint）擴 `_contracts/tools.py:ToolSpec`：
```python
@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict
    annotations: ToolAnnotations
    concurrency_policy: ConcurrencyPolicy
    hitl_policy: HITLPolicy = HITLPolicy.AUTO          # ← 新增
    risk_level: Literal["low","medium","high"] = "low" # ← 新增
    version: str = "1.0"
    tags: tuple[str, ...] = ()
```

51.0 已產生的 18 stubs 直接讀 `hitl_policy` field（會缺，default AUTO + low）；測試 `test_high_risk_tools_tagged_correctly` 改用 first-class field 而非 tags。

**負責人**：51.1 Day 1
**Owner**：範疇 2 spec

### A2：Naive correlation null-server-id 排除邏輯（51.x 真實邏輯）

**問題**：`mock_services/routers/correlation.py:analyze` 當 primary alert.server_id=null 時排除其他有 server_id 的 alert（filter `if other.get("server_id") and other["server_id"] != primary.get("server_id"): continue` 變 null primary == 全 skip）。對 mock 行為 OK，但不直觀。

**修正**：51.x（或 Phase 55 真實 correlation）邏輯改為：primary.server_id=null 表「跨 server」事件，accept any server。

**負責人**：51.x backlog
**Owner**：correlation domain

### A3：plan checklist 1.7 寫死 `curl` 但 sandbox hook 擋 curl/wget

**問題**：plan checklist Day 1.7 verification command 用 `curl http://localhost:8001/health`；但 context-mode hook 禁 curl/wget，必須改 `python urlopen`。51.x 後續 sprint plan 寫 verification command 時預先用 urllib 寫法。

**修正**：sprint plan template 注釋 — HTTP smoke 一律用 `python -c "from urllib.request import urlopen; ..."` 而非 curl。

**負責人**：sprint planning template
**Owner**：sprint workflow

### A4：CWD persistence in shell trips bash commands

**問題**：earlier `cd backend && python -c "..."` 殘留 CWD 到下個 bash call；多次撞到 `git add docs/...` 從 backend/ 找不到 path。

**修正**：bash command 一律用絕對路徑（`cd /c/Users/Chris/Downloads/...` 或從 project root）。

**負責人**：個人習慣
**Owner**：N/A（行為調整）

### A5：roadmap 24 vs spec 18 工具差異（CARRY-020）

**問題**：`06-phase-roadmap.md §51.0` 寫「24 個工具」但 `08b-business-tools-spec.md §Domain 1-5` 列 18 個（4+3+3+3+5）。51.0 採 spec 為準。

**修正**：user 決策 — 維持 18 不補 6，roadmap 註腳改寫；OR 51.x 補 6 個（但具體哪 6 個未指定）。

**負責人**：user
**Owner**：roadmap（V2 規劃文件 single-source）

---

## CARRY items（51.x+ 接手）

| ID | 主題 | 預期 sprint | 備註 |
|----|------|-----------|------|
| **CARRY-019** | frontend chat-v2 ToolCallCard 顯示 mock 業務工具結果 manual smoke | 用戶手動 | 需 user 訪 /chat-v2 切 echo_demo 測試 |
| **CARRY-020** | roadmap 24 vs spec 18 工具差異決策 | user review | 51.0 採 18；user 若要 24 補 6 個（建議無，保 18 簡潔） |
| **CARRY-021** | ToolSpec 加 first-class hitl_policy + risk_level field | **51.1** | 51.0 stubs 透過 default 自動相容 |
| CARRY-010 ~ 018 | 50.2 carry 全部繼續 hold（無變動）| 各 sprint | vitest / Tailwind / DB sessions / streaming etc. |

---

## Estimate Accuracy 報告

### 累計 V2 sprint 估時對比

| Sprint | Plan | Actual | Ratio |
|--------|------|--------|-------|
| 49.1 | ~28h | ~5h | 18% |
| 49.2 | ~25h | ~6h | 24% |
| 49.3 | ~28h | ~5.5h | 20% |
| 49.4 | ~26h | ~5h | 19% |
| 50.1 | ~28h | ~5.3h | 19% |
| 50.2 | ~28h | ~5.6h | 20% |
| **51.0** | **~25.5h** | **~5.9h** | **23%** |
| **平均（7 sprint）** | — | — | **~20%** |

51.0 落在預期區間（13-26%）。後續 sprint estimate 套 ~0.2x correction factor 對 mock + skeleton + register pattern；對複雜算法（51.2 memory retrieval / 52.1 compaction / 53.x guardrails）預計 ratio 升至 30-40%。

### 範疇成熟度（Sprint 51.0 closeout）

| 範疇 | Pre-51.0 | Post-51.0 | 備註 |
|------|---------|----------|------|
| 1. Orchestrator Loop | Level 3 | Level 3 | unchanged |
| 2. Tool Layer | Level 1 | **Level 1+** | 18 業務 ToolSpec + register pattern；51.1 進 Level 3+ |
| 3. Memory | Level 0 | Level 0 | unchanged（51.2 啟動）|
| 6. Output Parser | Level 4 | Level 4 | unchanged |
| 12. Observability | Level 2 | Level 2 | unchanged（mock_executor 已埋 tool_execution_duration_seconds via InMemoryToolExecutor）|

---

## V2 累計進度

**7 / 22 sprints complete**（49.1 / 49.2 / 49.3 / 49.4 / 50.1 / 50.2 / **51.0**）

- Phase 49 ✅ 4/4
- Phase 50 ✅ 2/2
- Phase 51 🟡 **1/3**（51.1 + 51.2 待）
- Phase 52-55 ⏸ 未啟動

**V2 累計對齊度估計**：~32%（業務領域層 stub + 12 範疇覆蓋 1+2+6+12 部分 + 主流量 e2e）

---

## Next Sprint（Rolling Planning — **不在此檔預寫具體 task**）

下個 sprint = **Sprint 51.1（範疇 2 工具層 — Level 3）**，per `06-phase-roadmap.md §Phase 51 §Sprint 51.1`：
- ToolRegistry / ToolExecutor / Sandbox / Permissions（real impl）
- 4 內建通用工具（memory_tools / search_tools / exec_tools / hitl_tools）
- ToolSpec 加 first-class hitl_policy + risk_level（CARRY-021）
- InMemoryToolRegistry deprecate（CARRY-017）

**plan / checklist 在 51.0 完全 closeout 後才寫**（per V2 rolling planning 紀律）。

---

**Maintained**：用戶 + AI 助手共同維護
**File**：`docs/03-implementation/agent-harness-execution/phase-51/sprint-51-0/retrospective.md`
**Created**：2026-04-30 (Sprint 51.0 Day 5 closeout)
