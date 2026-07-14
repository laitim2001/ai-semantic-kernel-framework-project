# V2 誠實全現狀審計 — 引擎 vs 落地（驗證層級盤點）

**Purpose**: 在投入下一批 sprint 方向之前,用統一的「驗證層級 rubric」逐項盤點本專案的真實落地度,回答三個問題:(1) 核心引擎每個能力到底驗到哪一層(L3 drive-through / L2 probe / L1 gate-only / L0 paper);(2) 使用者願景四支柱(連接外部系統 / 跨代理 / 長壽個人代理 / 真實業務流程)的實際落地度;(3) 哪些是確認的 Potemkin(mock-as-real / 死控件 / 接了無人用)。核心結論:**引擎紮實(7/12 範疇 L3)、前端誠實(會主動標示假資料)、但「連接真實世界」那條主線是系統性空洞(願景四支柱合計 ~17%);最近 9 個 sprint 的引擎微調正在讓這個空洞繼續擴大。** 本文件設計為長期「決策錨點」——見 §9。
**Category / Scope**: Status / Reality audit (cross-cutting · 引擎 + 願景 + Potemkin + 前端)
**Created**: 2026-06-26
**Last Modified**: 2026-06-26
**Status**: Active (snapshot;基於 git HEAD Sprint 57.144,main `06d2ca59`)
**Method**: 4 個 Explore agent 平行盤點(切面 A 核心引擎 11+1 / 切面 B 願景四支柱 / 切面 C Potemkin 掃描 / 切面 D 前端 39 頁)+ 主 session 綜合 + 對抗式「宣稱 vs 實際」交叉驗證。**行號為探查所得近似錨點,會隨 repo 演進——使用時須重新 grep 驗證。**

> **上游文件鏈**:[`agent-harness-cc-parity-20260607.md`](agent-harness-cc-parity-20260607.md)(CC 部件級對照)→ [`harness-deepening-proposal-20260610.md`](../1-planning/harness-deepening-proposal-20260610.md)(三工作流深化方案)→ 本文(**把「部件對照」下沉到「驗證層級」,並把焦點從「對標 CC」轉回「對標使用者願景」**)。
>
> **為何需要這份文件**:cc-parity 回答「距離 CC 還差哪些齒輪」;本文回答**「距離『一個能訪問公司資源、跑通真實流程的個人代理』還差多遠,以及哪些『✅』其實只是 gate-green」**。前者用 CC 當標竿(永遠追不完),後者用「人能不能操作一條真實流程」當標竿(會收斂)。

---

## 0. 一句話結論

> **這套系統是「引擎紮實、車殼誠實、但還沒接上方向盤通往真實世界」。** 它沒有 V1 的紙上空殼病(核心 loop 是真的,有 real Azure gpt-5.2 drive-through),也沒有假裝完整(前端 fixture 頁會主動掛 `BackendGapBanner`)。但願景裡「連上真實系統、跑通真實流程」那條主線,是**系統性空洞,不是個別缺口**——而且最近的開發重心正在讓它繼續擴大。

兩極分化極清晰:**不是「平均做了一半」,是「引擎 ~80% + 落地 ~17%」**。中間那條「把引擎接到真實世界」的管道幾乎是空的。

> **Update 2026-06-26 (Sprint 57.145)**: §9 gate answered ONCE — the platform's **FIRST real external data-source connector** shipped (`knowledge_search` + `LocalDocsConnector`; drive-through PASS real Azure gpt-5.2: agent reads real in-repo `.md` → grounded answer cites 3 real source paths `08-glossary`/`04-anti-patterns`/`00-v2-vision`). **願景支柱 1(連接外部系統):0 → 1 real connector** (still keyword/local-files Slice 1 — embedding / external-sources / RBAC are Slice 2/3, see `next-phase-candidates.md` §Grounding pillars). The drive-through found+fixed a multi-word-query 0-hit bug the green gate couldn't catch — proving §9's thesis (gate-green≠連得上真實世界). The other 3 pillars + the broader「接到真實世界」pipe remain the systemic gap. CHANGE-112 + design note 49.

---

## 1. 驗證層級 Rubric(本審計的量尺)

| 層級 | 定義 | 證明了什麼 |
|------|------|-----------|
| **L3 Drive-Through** | 有真 UI + 真後端 + 真 LLM 走通的記錄(progress/retro 裡明確的「drive-through PASS / session `<id>` / real Azure gpt-5.2」) | 整台車能開、人能用 |
| **L2 Curl/Probe** | API / harness 會回應,但無真 UI 驅動 | 零件對 + API 會回 |
| **L1 Gate-only** | 有實作 + mypy/pytest 綠,但找不到「人能用」證據 | 零件對 |
| **L-Mock** | 用 fixture/mock 驅動(關鍵:是否被誤導成「真」) | 視覺/結構對,資料假 |
| **L0 Paper/Potemkin** | 只有 interface/設計,主流量根本不呼叫 | 紙上有 |

> 對齊 CLAUDE.md §Drive-Through Acceptance Hard Constraint 的三層(gate / curl / drive-through),本文加 L-Mock 與 L0 兩層以分離「假資料」與「孤兒代碼」。

---

## 2. 四切面綜合總表

| 維度 | 真實層級分布 | 一句判斷 |
|------|-------------|---------|
| **核心引擎 11+1**(切面 A) | 7 紮實 L3 · 3 L2 · 1 L1 · 1 遺漏 | 引擎是真的,V1 病已治好 |
| **願景四支柱**(切面 B) | **合計 ~17%** | 連接真實世界的主線是空的 |
| **Potemkin 掃描**(切面 C) | 2 確認 · 3 疑似 · 多數真實 | mock-as-real 是最危險的一個 |
| **前端 39 頁**(切面 D) | L3 真接 9(23%) · fixture 13 · ComingSoon 14 · 死殼 3 | chat-v2 真、其餘多為 fixture(已誠實標示) |

---

## 3. 核心引擎 11+1 範疇逐項(切面 A)

| 範疇 | 層級 | 近似錨點 | 證據 / 落差 |
|------|------|---------|------------|
| Cat1 TAO while-loop | **L3** | `loop.py` run()→_run_turns() 主 `while True`(stop_reason 驅動,4 terminator) | Sprint 57.100 dt real Azure:多 turn + escalate pause + resume 續 turn。**紮實** |
| Cat2 工具 + Docker sandbox | **L3** | `tools/sandbox.py` DockerSandbox(--network=none --read-only --cap-drop=ALL);57.137 fail-closed | 57.102 dt:teammate 3-turn loop 內真執行工具 + 真輸出回注。**紮實** |
| Cat3 Memory 5-scope | **L2** | `memory/layers/*.py`;`prompt_builder` build() 內注入;loop emit MemoryAccessed | 5 層注入 gate 級綠,但**單次 chat 無跨輪 memory carry**(跨輪靠 MessageStore rehydration,非 memory layer)。見 §5 疑點 |
| Cat4 Context compaction | **L2** | `context_mgmt/compactor/*`;loop compaction 區段;57.109 dt | 真壓縮過(9824→2679 tokens);但需多輪 corpus 才觸發,plain Q&A 無機會。harness 級證實,非 Potemkin |
| Cat5 Prompt builder | **L3** | `prompt_builder/builder.py`;loop 每輪 build() | 57.64 dt:PromptBuilt + memory round-trip + FORK 同時驅動。**紮實**(拱心石) |
| Cat6 Output parser | **L3** | `output_parser/parser.py`;classify→3-way branch | 57.100/102/103 dt:FINAL/TOOL_USE/HANDOFF 分支真驅動。**紮實** |
| Cat7 State + DBMessageStore rehydration | **L3** | `state_mgmt/message_store.py` DBMessageStore;loop run() 起 load() | 57.127 dt:turn 1 persist → turn 2 load,messages 4→6 跨輪。**紮實** |
| Cat8 Error handling / retry | **L1** | `error_handling/retry.py`;loop llm_call 以 retry_policy wrap | 實作完整 + pytest 綠,但**無 real error(rate-limit/timeout)觸發 retry 的 drive-through**。gate-only |
| Cat9 Guardrails 4 閘 + HITL | **L3(部分)** | loop 5 個 `_cat9_*` method;`guardrails/engine.py` | input/between/output + tool-HITL 都有 57.100/101 dt;**tripwire(第4閘)無 dt**(需污染 audit log,高風險) |
| Cat10 Verification in-loop | **L3** | loop `_cat10_verify_gate`;57.98 A1 | 57.100 dt:judge fail → correction re-inject → bounded → escalate → coached turn。**紮實** |
| Cat11 Subagent | **L3(分模式)** | `subagent/modes/{fork,teammate,handoff,as_tool}.py` | FORK(57.95 並行)/TEAMMATE(57.102 real 3-turn)/HANDOFF(57.68 branch+子會話)皆 L3;**as_tool 僅工具層綠,無獨立 dt** |
| Cat12 Observability | **L3** | `observability/tracer.py` OTelTracer;57.71 + 57.142 | 57.142 dt real Azure:span tree 3/3 conformant,gen_ai mapping。**紮實** |

**小結**:7 紮實 L3(Cat1/2/5/6/7/10/12)· 3 部分 L2(Cat3/4/9)· 1 gate-only(Cat8)· 1 遺漏(Cat11 as_tool FE 不可驅動)。**引擎本體不是 Potemkin——這是 V2 相對 V1 最大的健康指標。**

---

## 4. 願景四支柱(切面 B)— 這才是「能不能操作真實流程」

| 支柱 | 落地度 | 近似錨點 | 誠實判斷 |
|------|-------|---------|---------|
| **1 連接公司「既有外部系統」** | **~15%** | `adapters/` 只有 `azure_openai`/`anthropic`/`_mock`/`_base`/`maf`;`business_domain/_register_all.py` 18 工具全走 mock_executor;`incident/mock_executor.py:22` 硬連 `http://localhost:8001` | **零個外部系統連接器、零 MCP 工具層、零 ToolRegistry 橋接。** `service.py` 雖真但只連平台自建 PostgreSQL 表,非公司既有系統。通用連接能力 ≈ 0 |
| **2 跨人 / 跨代理互動** | **~50%** | `subagent/modes/*`;`subagent/dispatcher.py:97` | fork/teammate/as_tool 都是**同一 session 內** parent-child;**無「user X 的 agent ↔ user Y 的 agent」通訊機制**(無 mailbox / 事件總線 / API) |
| **3 個人代理(長壽 per-user)** | **~5%** | `chat/handler.py` `max_turns=8`;`loop.py` AgentLoopImpl 每 run() 新建 | 純 per-session 無狀態:每請求新 session_id → 8-turn 有界爆發 → 結束。**無 per-user 身份/狀態/長期記憶綁定** |
| **4 真實端到端業務流程** | **~0%** | `backend/tests/e2e/test_agent_loop_with_mock_patrol.py`(標題自承 demo);所有 sprint 證據圍繞技術特性 | **零個「真人從頭跑通一條多步驟真實業務流程」的記錄。** e2e 全是 echo/mock_patrol 工程 PoC |

**合計 (15+50+5+0)/4 ≈ 17.5%。** 平台目前是「工程技術展示」而非「可操作真實業務的系統」——LLM adapter 可用、loop 機制可用,但**缺所有連接真實世界的管道**。

---

## 5. Potemkin 掃描(切面 C)

### 🔴 確認的 Potemkin(2)

| 組件 | 錨點 | 問題 | 建議 |
|------|------|------|------|
| **business_domain_mode 預設 "mock"** | `core/config/__init__.py:104` `Literal["mock","service"]="mock"` | **最危險的 mock-as-real**:預設下 18 工具全打假後端,無啟動警示。讓「能訪問公司資源」看起來成立但其實全假 | 啟動時明示 MOCK 警告 OR 強制 env override OR 預設 raise |
| **SessionList Filter 死控件** | `frontend/.../chat_v2/components/SessionList.tsx:156-163` | `<button aria-label="Filter">` 無 onClick(2026-06-06 誠實化後僅修了 New session,Filter 殘留) | 移除或實作(無後端支撐,建議移除) |

### ⚠️ 疑似(接了但主流量無 driver)(3)

| 組件 | 錨點 | 問題 |
|------|------|------|
| **memory_search / memory_write** | `tools/memory_tools.py`;`_register_all.py` opt-in | 真實作 + 條件註冊都對,但 demo system prompt **無任何文字引導 LLM 去用**。能力齊全、主流量從不觸發 |
| **read_skill / run_skill_script** | `skills/tool.py`;`_register_all.py` skill_registry 非空才註冊 | 同上:skills lazy-load 概念完整,但無 prompt driver,常規 chat 無跡象呼叫 |
| **handoff(spec-only)** | `subagent/tools.py` make_handoff_spec;loop OutputClassifier 攔截 | **刻意設計**(spec-only 宣告 intent,execution 歸 platform);57.68 dt 已驗運作,但設計意圖需明示以免誤判為斷裂 |

### ✅ 確認真實作(澄清先前懷疑)

- **HITL Manager**:`platform_layer/governance/hitl/manager.py:70`(~275 行 DB-backed 真實作),loop resume() `get_decision()` + 5 個 request_approval 呼叫點;57.x dt 驗證 approve→resume 真投遞。**非 stub**
- **SubagentDispatcher**:`subagent/dispatcher.py:97`,handler child-loop factory + dispatcher.spawn() 被 await;57.102 dt FORK/TEAMMATE 真跑。**非 stub**

---

## 6. 前端 39 頁分層(切面 D)

| 層級 | 頁數 | % | 代表頁 |
|------|------|----|--------|
| **L3 真接後端** | 9 | 23% | chat-v2 · admin-tenants · cost-dashboard · governance · loops · subagents · verification · memory · tenant-settings |
| **L-Fixture 寫死資料** | 13 | 33% | auth ×8 · overview · orchestrator · state-inspector(多數已掛 `BackendGapBanner` 誠實標示) |
| **L-Mockup ComingSoon** | 14 | 36% | models · cache-manager · pricing · rbac · sse · tools · 等 |
| **L-Dead 殼頁** | 3 | 8% | orchestrator/index · overview/index · state-inspector/index |

**chat-v2 主流量(逐控件驗)**:composer 送信(真 `POST /chat` SSE)· session list(真 `GET /sessions`)· model badge(SSE 動態填,非寫死)· answer block(真 LLM 串流)· Inspector 5 tab(Turn/Trace/Memory/Tree/Todos 全真資料 + 空狀態誠實不虛造)· **零死控件**。整體平台「可用度」(以頻繁使用權重)約 **25-30%**。

> **健康訊號**:fixture 頁主動掛 `BackendGapBanner reason="AP-4 honesty..."`、orchestrator 死路徑用 `window.alert` 揭露 backend gap、Inspector 空狀態寫「no plan yet」。**這個系統誠實地知道自己哪裡是假的**——這是 drive-through 鐵律已內化進制度的證明,是 V2 比 V1 根本健康的地方。

---

## 7. 三個最關鍵發現

1. **最危險的 Potemkin 是 business 工具的 mock-as-real。** 它讓「平台能訪問公司資源、執行業務動作」這個願景核心**看起來成立**(5 domain × 工具齊全 × service 層在),但預設一條真實連接都沒有。這與 V1「看起來對齊但實際 27%」同源,只是藏得更深。

2. **memory / skills 是「接了但沒人用」。** 零件對(定義+實作+註冊),但主流量 prompt 沒接那根線去觸發——一種特殊 Potemkin。

3. **好消息:drive-through 紀律真的在起作用。** 前端 fixture 標示、空狀態誠實、死控件從 5 降到 1。這是 V2 的免疫系統,要守住別退化。

---

## 8. 對「方向」的判斷

- ✅ **引擎方向對、且真落地**——V1 的病治好了,7/12 範疇有 real Azure drive-through。不要懷疑這點。
- 🔴 **「落地」維度是系統性空洞**——連接外部系統 / 真實業務流程 / 個人代理 / 跨代理合計 17%,不是補幾個 feature 能填。
- ⚠️ **重心正在偏離**——最近 9 sprint(57.136–144)是引擎微調,多個 A/B 結論「KEEP lever OFF / 收益 < 5%」(邊際報酬遞減),同期落地維度原地踏步。

**風險形態**:不是 V1 的「過度建設」,而是「過度打磨一台已夠好的引擎,卻沒接上通往真實世界的那根管子」。結果相同——落不了地。

---

## 9. ⭐ 決策用法(本文件作為基準錨點)

> **每次有人想開一個「引擎微調 / parity 補洞」sprint 之前,先對照本表回答這 5 個問題。任一答「否」就要先問:這個 sprint 是在擰已經夠好的螺絲,還是在接通往真實世界的管子?**

**落地維度 Gate(開新 sprint 前自問)**:

1. **落地維度動了沒?** 這個 sprint 讓「願景四支柱」(§4)任何一項的百分比上升了嗎?還是只動引擎內部(§3)?
2. **有沒有真實連接?** 它有沒有讓 agent 接觸到**任何一個非平台自建的真實系統 / 真實資料源**?(對照 §5 mock-as-real)
3. **有沒有更靠前的落地工作被它擠掉?** §4 支柱 1(連接層)或支柱 4(真實流程)是否有更高 ROI 的工作被推遲?
4. **A/B 預期收益 ≥ 5% 嗎?** 若這是 evidence-first spike,先估收益區間——若大概率落在「KEEP lever OFF」,它是打磨不是落地(對照 57.136–144 趨勢)。
5. **它能被一個真人 drive-through 嗎?** 還是又一個只能 gate / probe 驗的內部齒輪?(對照 §6 健康訊號)

**北極星(取代「parity 表還剩幾項紅」)**:

> **「一條真實的、窄的、端到端業務流程,能不能讓一個真人從頭跑通。」**
> CC parity 表永遠追不完(CC 一直更新);「一條真實流程跑通」會收斂。用後者驅動。

**快速健康指標(下次審計對照)**:

| 指標 | 2026-06-26 基準 | 目標方向 |
|------|----------------|---------|
| 願景四支柱合計 | ~17% | ↑ |
| 連接外部系統(支柱 1) | ~15%(零真實連接器) | ↑(接第 1 個真實系統) |
| 真實業務流程(支柱 4) | 0%(零真人跑通) | ↑(跑通第 1 條) |
| 確認 Potemkin 數 | 2(mock-as-real + Filter 死鈕) | ↓ |
| 前端 L3 真接 | 9/39(23%) | ↑ |
| 引擎 L3 範疇 | 7/12 | 維持(別再過度投) |

---

## 10. 建議下一步(有順序)

1. **拆掉最危險的 mock-as-real**:`business_domain_mode` 預設要嘛真接一個外部系統,要嘛啟動時明示「MOCK 模式」。不讓假連接繼續偽裝成「能訪問公司資源」。
2. **選一條窄而真的流程當第一條**:連**一個**真實系統 → agent 自主規劃(write_todos 已是真的)→ 調用 → 分析 → 輸出。這會強迫補上願景最大缺口——connector / MCP 層(`adapters/` 目前零外部連接器)。
3. **順帶接通 memory/skills 那根沒接的線**:在 demo prompt 真正引導 agent 使用,否則它們永遠是 17% 裡的虛數。
4. **修掉 Filter 死控件**(小,但守住誠實紀律)。

> 三工作流深化方案(harness-deepening-proposal A/B/C)**不作廢**,但應**服務於那條真實流程**——流程跑通過程中真正卡住的引擎缺口才補,而非預先把 parity 表擰滿。proposal §4.4 已自承「10 切片連跑 = ~10-15 sprint 無對外新價值」的張力,本文給出解法:用 §9 的落地 Gate 穿插決策。

---

## Modification History (newest-first)
- 2026-06-26: Initial creation — 4 Explore agent 平行盤點(引擎 11+1 / 願景四支柱 / Potemkin / 前端 39 頁)+ 主 session 綜合;核心結論「引擎 ~80% L3、落地 ~17%、最危險 Potemkin = business mock-as-real」;§9 設計為長期決策錨點(落地維度 Gate 5 問 + 北極星 + 健康指標基準)。上游接 agent-harness-cc-parity-20260607 + harness-deepening-proposal-20260610。
