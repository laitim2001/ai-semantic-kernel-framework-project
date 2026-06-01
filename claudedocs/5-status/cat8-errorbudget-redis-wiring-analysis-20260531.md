# B-7 深度分析:Cat 8 ErrorBudget — RedisBudgetStore「已建好、未接線」

**Purpose**: 釐清 B 區優化項 B-7(Cat 8 ErrorBudget 跨實例正確性)的真實缺口性質、改動範圍、優先級。**重大校正**:原整合盤點寫「換成 RedisBudgetStore」,實際上 `RedisBudgetStore` **早已完整實作 + 有 fakeredis 整合測試**(Sprint 53.2),缺的純粹是 wiring —— 與 A 區同型(功能在但沒接通),非「建新 infra」。
**Category**: 範疇 8 (Error Handling) + cross-cutting wiring(`api/` startup + chat factory)
**Scope**: B 區優化分析 / B-7
**Created**: 2026-05-31
**Status**: Active(analysis;非 sprint plan)

**Modification History (newest-first)**:
- 2026-05-31: §3/§5/§7 更正 — 工具乾淨重試後證明初稿「build_real_llm_handler 無 caller/無 test」為截斷假象(實有 caller `handler.py:288` + 整合測試);改為 env-gated 未實跑 + 新增 per-request InMemoryBudgetStore 重建確證
- 2026-05-31: Initial creation — B-7 RedisBudgetStore wiring 缺口分析(Explore 蒐證 + 主 session 抽查複核)

**Related**:
- `integration-progress-20260531.md` §B-7
- `area-a-integration-sequencing-capstone-20260531.md`(同型「已建好未接線」方法論)
- `04-anti-patterns.md` AP-2(Side-Track Code Pollution)/ AP-6(Hybrid Bridge Debt)
- `.claude/rules/multi-tenant-data.md`(tenant 隔離)

---

## 0. 一句話結論

> **B-7 不是「建 RedisBudgetStore」,而是「把早已建好、已測試的 `RedisBudgetStore` 接上去」。** 改動極小(抄現成的 `_wire_rate_limit_counter` 模板),但**目前優先級低** —— 因為它要保護的 real-LLM 路徑(`build_real_llm_handler`)是 **env-gated**(缺 Azure key 即 `raise RuntimeError` 退回 echo_demo),目前未實跑;跨實例正確性只在「real-LLM 上線 + 水平擴展」後才真正咬人。
>
> ⚠️ **但有一個比跨實例更基本的問題**(乾淨重讀後確證):`make_chat_error_deps()` 在**每請求**的 `build_real_llm_handler` 內被呼叫(`handler.py:218`),每次 `new InMemoryBudgetStore()` → 連單實例跨請求都不累積 → 一旦 real-LLM 上線,即使只有 1 個實例,budget 計數也**形同失效**。所以接 Redis 不只是「多實例正確性」,而是「budget 要能運作的前提」。

---

## 1. 核心證據(均經主 session 親自 Read 複核,行號連續無截斷)

| # | 事實 | 證據 file:line |
|---|------|----------------|
| 1 | **`RedisBudgetStore` 已完整實作**(非 stub):真 MULTI/EXEC pipeline `increment` + `get` | `agent_harness/error_handling/_redis_store.py:35-61`(Sprint 53.2 建)|
| 2 | `BudgetStore` 是 **Protocol**(結構型,非 ABC):`increment(key, ttl_seconds)->int` + `get(key)->int` | `agent_harness/error_handling/budget.py:52-66` |
| 3 | `InMemoryBudgetStore` 自述 **「Not for production (state lost on restart, no cross-process sharing)」** | `budget.py:69-74` |
| 4 | budget key **已含 tenant_id**:`error_budget:{tenant_id}:day:{date}` / `:month:{ym}` | `budget.py:138-145` |
| 5 | **wiring 缺口白紙黑字**:工廠硬寫 `InMemoryBudgetStore()`,註解「RedisBudgetStore (cross-instance) is deferred — no shared error-budget Redis client is wired yet」 | `api/v1/chat/_category_factories.py:117-126`(L126 實例化)|
| 6 | **現成 wiring 模板**:`_wire_rate_limit_counter` 在 startup `Redis.from_url(settings.redis_url)` → `set_rate_limit_counter(...)` → `except Exception` fail-open | `api/main.py:95-117` |
| 7 | **RedisBudgetStore 已有 fakeredis 整合測試**(可直接複用做 wiring 測試) | `tests/integration/agent_harness/error_handling/test_redis_budget_store.py`(Explore 證;`FakeRedis` fixture)|
| 8 | error_budget 注入鏈:工廠 → `AgentLoopImpl(error_budget=...)` ctor → loop `_handle_tool_error` 內 `record()` | `_category_factories.py:126` → `loop.py` ctor + `_handle_tool_error`(Explore;loop.py 未逐行複核)|

> 證據 1/5/6 是本分析三根支柱,皆由主 session 直接 Read 確認(對照 A-5 捏造前車,刻意親驗)。

---

## 2. 缺口的真實性質:這是 AP-2(Side-Track Code),不是缺功能

- `RedisBudgetStore` + 其整合測試 **存在於 production 樹**,但 `_category_factories.py` 不用它 → 它目前是**沒有 production 呼叫點的旁支代碼**(Sprint 53.2 建好,至今未接)。
- 對照 `04-anti-patterns.md` **AP-2(Side-Track Code Pollution)**:「代碼存在但主流量無人呼叫」。B-7 的動作本質 = **消除這個 AP-2**(接上去,或讓那行 deferred 註解變成永久債)。
- 對照 **AP-6(Hybrid Bridge Debt)**:RedisBudgetStore **不是** AP-6 —— 它不是「為未來可能的供應商」預留的抽象,而是真實的跨實例 production 需求,且已測試。所以「接它」是還債,不是擴張投機抽象。

---

## 3. 優先級低,但原因是 env-gate + per-request 失效(非「無 caller」)

> 本節經工具乾淨重試後修正;初稿曾誤判「無 caller」(見 §5)。以下證據均為乾淨 `git grep` / Read 複核。

**事實 1 — 路徑已接線 + 有測試(初稿誤判更正)**:
- `build_real_llm_handler` 有真實 caller:`handler.py:288 return build_real_llm_handler(...)`(由 `build_handler` 每請求呼叫)。
- 有整合測試:`tests/integration/api/test_chat_category_activation_wiring.py:96/103/115/126/145/159` 多處呼叫;`CHANGE-031` 記載 Sprint 57.63 即透過它接 Cat 4/7/8/10。

**事實 2 — 但 env-gated,缺 key 不跑**:
- `handler.py:178-185`:缺 `AZURE_OPENAI_ENDPOINT/API_KEY/DEPLOYMENT_NAME` 任一 → `raise RuntimeError` → 路徑退回 echo_demo。
- 配合 A 區盤點:無 Azure key → real-LLM 路徑 ~0% 實跑。
- ∴ error_budget 目前**未在真實流量被執行**,「跨實例不一致」bug 目前不發生。

**事實 3 — per-request 重建,連單實例都失效(新確證)**:
- `make_chat_error_deps()` 在每請求的 `build_real_llm_handler` 內(`handler.py:212-218`)被呼叫,每次 `TenantErrorBudget(InMemoryBudgetStore())`(`_category_factories.py:126`)。
- ∴ InMemory counter **每請求歸零**,連同一進程跨請求都不累積 → 一旦 real-LLM 上線,即使單實例,daily/monthly budget 也永遠到不了上限 = **budget 形同失效**。

**結論**:B-7 是「**真實但尚未到期的債**」——接線成本低,但:
- 收益要等 **real-LLM go-live**(需 Azure key)才兌現;
- 屆時 Redis wiring **不只**解「多實例」,而是 budget 能運作的**前提**(per-request 重建讓 InMemory 對 budget 根本不適用);
- 最佳做法:與「real-LLM 真正上線」sprint **配對**,而非獨立趕工。

---

## 4. 若要做,改動範圍(Tier 化,對齊 A 區方法)

### Tier 1 — 接線(便宜,抄 rate-limit 模板,**不改 loop.py / 不改 budget.py**)

1. **新增 `_wire_error_budget()`**(`api/main.py`,鏡像 `_wire_rate_limit_counter` L95-117):
   - `Redis.from_url(settings.redis_url)` → `set_budget_store(RedisBudgetStore(client))`
   - 整段 `except Exception` fail-open(Redis 不可用時不擋 startup,退回 InMemory)
2. **新增 `set_budget_store()` / `maybe_get_budget_store()` 單例**(`agent_harness/error_handling/` 或 `platform_layer/`,鏡像 `set_rate_limit_counter`)。
3. **改 `_category_factories.py:126`**:`store = maybe_get_budget_store() or InMemoryBudgetStore()` → `TenantErrorBudget(store)`;同步刪掉 L117-119 deferred 註解(已還債)。
4. **測試**:複用 `test_redis_budget_store.py` 的 `FakeRedis` fixture,加一個 wiring 測試證「set 後工廠拿到 Redis store」;InMemory fallback 路徑保留測試。

預估:**小**(1 個 wire 函式 + 1 對 setter/getter + 1 行工廠改 + 2-3 測試)。無 schema、無 migration、無 loop.py 改動。

### Tier 0 — 先決條件(必須先確認,見 §5)
- 確認 `build_real_llm_handler` 的真實 routing / 呼叫頻率(per-request?是否真的接到 live route?)。若它根本沒接到 router,B-7 接線後仍無主流量驗證點 → 應併入「real-LLM 真正接 router」的工作。

---

## 5. 工具可靠性事件(誠實全記:含一次被我寫進初稿的錯誤)

本次分析中工具一度異常,**且我初稿據錯誤輸出下了一個假結論**,後經乾淨重試更正:

**異常現象**(數次):
- handler.py 的 Read 兩次被截斷:行號跳號(180→202)、插入原始碼不存在的 `...` 省略符。
- 原生 Grep 一度回傳帶人類註解的合成行(`"...(called inside build_real_llm_handler)"`),非 raw 輸出。
- `git grep "build_real_llm_handler"` 一度**只回定義行**(漏掉所有 caller / test)。

**我犯的錯**:初稿 §3 據那次殘缺 git grep 寫下「無任何 caller / test」「real-LLM 路徑連呼叫點都查不到」——**這是錯的**。乾淨重跑後 `git grep` 回傳完整結果:caller 在 `handler.py:288`、整合測試在 `test_chat_category_activation_wiring.py`。已於本檔 §0/§3/§7 + MHist 更正並標明 RETRACT。

**處置**(對齊用戶「懷疑工具異常用最小指令實測、絕不捏造」鐵律):
- 異常時應**立即停下重試**,不該把殘缺輸出當完整結論寫入(這次先寫了才更正,是流程瑕疵,記取)。
- 乾淨重試後 `git grep` / Read 行號連續、結果與 Explore + `CHANGE-031` 三方一致 → 採信。
- §1/§3 修正後的證據已三方交叉(Read 複核 + git grep + 既有 CHANGE doc),可信。
- **Day-0 建議**:真開 B-7 sprint 時,凡關鍵 routing 用 `git grep` 多次一致才採信,單次殘缺輸出視為無效。

---

## 6. Multi-tenant 檢查

- ✅ budget key 已含 `tenant_id`(`budget.py:138-145`),跨租戶隔離在 key 層已具備。
- ✅ `RedisBudgetStore` 直接吃 `BudgetStore` Protocol 的 string key,tenant 隔離由 `TenantErrorBudget` 在上層保證 → 換 Redis **不影響** tenant 正確性。
- ⚠️ 注意:rate-limit 的 `RedisRateLimitCounter` 在 write-through DB 時要設 PG `app.tenant_id`(RLS);**RedisBudgetStore 純 Redis、無 DB write-through**,故無此需求 —— 不要照抄 rate-limit 的 `_set_tenant_context`,那是 over-engineering。

---

## 7. 給 sprint 選擇的最短建議

| 問題 | 答案 |
|------|------|
| 要建新東西嗎? | ❌ `RedisBudgetStore` 已建好 + 已測 |
| 改動大嗎? | 小(抄 `_wire_rate_limit_counter` 模板,~Tier 1) |
| 現在急嗎? | ❌ real-LLM 路徑 env-gated 未實跑(缺 Azure key → `handler.py:178-185` raise 退回 echo_demo);**已接線 + 有整合測試** |
| 但一上線就要? | ⚠️ 是 —— per-request `InMemoryBudgetStore` 重建(`handler.py:218`)讓 budget 連單實例都失效;real-LLM go-live 時 Redis 是 budget 能運作的前提 |
| 最佳時機? | 與「real-LLM 真正上線(配 Azure key)」sprint 配對 |
| 風險? | 低;fail-open 設計(Redis 掛退回 InMemory),已有測試 fixture |
| 順手該還的債 | AP-2:刪 `_category_factories.py:117-119` deferred 註解 + 接上旁支的 RedisBudgetStore |
