# 11 範疇規格 + Server-Side 哲學 Review 報告

**Reviewer**：Independent expert review（Anthropic CC/SDK、OpenAI Agents/Codex、LangGraph、MAF、CrewAI、LangChain Deep Agents 框架知識基礎）
**日期**：2026-04-28
**Review 模式**：嚴格（寧可嚴格不要寬鬆）
**對照基準**：discussion-log-20260426.md L67-150 業界 11 範疇權威定義

## 整體評分：**7.0 / 10**

**評價總結**：規劃**架構正確、方向清晰**（這是它能拿到 7 分的原因），但**深度與細節不足**以支撐企業 production 開發（這是它離 9 分還有距離的原因）。最大風險不是錯，而是**缺**——許多企業 server-side 必須的機制（tracing、cost budget、prompt caching、rate limit、async callback、reducer pattern）在 spec 層級隱形，會在 Sprint 中爆發為「設計重做」。

---

## 文件 1：01-eleven-categories-spec.md

### 範疇 1：Orchestrator Loop (TAO/ReAct)
- 準確性：✅
- 完整性：⚠️
- 可實作性：⚠️
- 驗收標準：⚠️
- 企業適配：⚠️
- 對齊 3 大原則：✅

**發現的問題**：
1. `on_event: Callable[[LoopEvent], None]` — sync callback 在 async server 是反模式；server-side SSE/WebSocket 推送必須 `Awaitable[None]`，否則阻塞 event loop
2. **缺 streaming-first 設計**：Anthropic/OpenAI 都已 streaming-default，spec 未定義 partial tool_call 累積、增量 token emit
3. **缺 parallel tool execution policy**：業界共識（CC、Codex、LangGraph）是 read-only tool 並行 / mutating 序列；範疇 2 提了但範疇 1 loop 沒落到 API
4. **驗收偏 binary**：「真正用 while」「stop_reason 驅動」都是「存在性」檢查，缺 SLO（p95 latency、turns/min throughput、token efficiency）
5. **`on_event` 列表 ≠ tracing**：缺 trace_id / span_id 概念，無法接 OTel 或 LangSmith

**建議修改**：
- `on_event` → `AsyncIterator[LoopEvent]` 或 `Callable[[LoopEvent], Awaitable[None]]`
- 新增 `parallel_tool_policy: Literal["sequential","read_only_parallel","all_parallel"]`
- 新增 `trace_context: TraceContext`（含 OTel span）
- 驗收加：p95 loop latency < X ms、tracing span 完整覆蓋

---

### 範疇 2：Tool Layer
- 準確性：✅
- 完整性：⚠️
- 可實作性：✅
- 驗收標準：⚠️
- 企業適配：✅
- 對齊 3 大原則：✅

**發現的問題**：
1. **ToolSpec 缺 MCP-style annotations**：MCP 標準有 `readOnlyHint`、`destructiveHint`、`idempotentHint`、`openWorldHint` — 這些是 LLM 決策依據，不只是執行控制；V2 用 `is_mutating` 一個 bool 不夠
2. **8 大類分類過早固化**：把「業務領域工具」（patrol/correlation/rootcause）寫進 spec 是把 V1 IPA 業務鎖進 harness 規格，違反「11 範疇是通用 harness」的 framing；應該分離 `core tool categories` 與 `IPA business tools`
3. **缺 tool result content type 定義**：是 `str` 還是 `list[ContentBlock]`（image / json / text）？這會回頭限制範疇 6 的 ChatResponse 設計
4. **缺 schema validation failure 路徑**：JSON 解析失敗 → retry 還是 LLM-recoverable error 回注？範疇 8 提了但範疇 2 沒對接
5. **「parallel: read-only 可並行，mutating 序列」沒寫進 ToolSpec** — 應該是 `concurrency_policy: ConcurrencyPolicy` 欄位
6. **缺 tool versioning** — server-side 滾動部署時 v1 / v2 共存怎麼辦？

**建議修改**：
- 新增 ToolSpec 欄位：`annotations: ToolAnnotations`（4 hints）、`concurrency_policy`、`version`、`result_content_types`
- 拆 `08-domain-tools.md` 把 IPA 業務工具獨立規範

---

### 範疇 3：Memory（5 層）
- 準確性：✅
- 完整性：⚠️
- 可實作性：⚠️
- 驗收標準：⚠️
- 企業適配：✅
- 對齊 3 大原則：✅

**發現的問題**：
1. **5 層 vs CC 3 層的創新點未論證**：tenant + role 是合理擴充，但業界基準是 「short-term / long-term / semantic」三軸，5 層僅是 scope 軸，**缺第二軸**（time scale / modality）
2. **缺存儲後端對應**：哪層走 RDBMS、哪層走 Redis、哪層走 Vector DB、哪層走 KV？沒映射等於沒落地
3. **「線索→驗證」是核心理念但無 API**：CC 把它做成 prompt 教 agent「先 grep 再做事」；V2 spec 只寫概念，沒落到 PromptBuilder（範疇 5）或 tool annotations
4. **缺 memory extraction 流程**：CC 是 forked subagent 提取；V2 規格沒寫誰、何時、怎樣寫入 user memory
5. **缺衝突解決**：兩條記憶矛盾時的優先級規則
6. **缺 eviction / TTL / rotation**：Layer 5 提 TTL 24h，其他層沒提；user memory 累到上限怎辦？
7. **驗收「Tenant 隔離」過弱** — 應該是 「red-team test：跨 tenant prompt injection 0 leak」

**建議修改**：
- 補表：5 層 × {storage, write trigger, read pattern, eviction, conflict resolution}
- 「線索→驗證」做成 `MemoryHint` dataclass + `verify_before_use: bool`

---

### 範疇 4：Context Management
- 準確性：✅
- 完整性：⚠️
- 可實作性：⚠️
- 驗收標準：⚠️
- 企業適配：⚠️
- 對齊 3 大原則：✅

**發現的問題**：
1. **缺 prompt caching 策略**：Anthropic / Azure OpenAI 都有 prompt caching，是 multi-tenant cost 殺手鐧；context management 不談 caching 等於放棄 30-90% cost saving
2. **token counter 抽象未定義**：per-provider tokenizer 不同（tiktoken / claude-tokenizer / o200k_base），spec 寫「token_count」但沒說誰算
3. **Compaction 策略過簡**：「保留 system + 最近 N turn」是 baseline；缺 semantic compaction（用 LLM 摘要中段）vs structural（規則式刪減）的選擇
4. **缺 context isolation per subagent**：Codex/CC 模式是每個 subagent 獨立 context，這是範疇 11 與範疇 4 的接口，spec 沒寫
5. **「30+ turn 不會 OOM」是弱驗收**：應該是「context_used / window <= 75% 在 95% session 中保持」

**建議修改**：
- 新增 §「Prompt Caching」子節：cache key 設計、tenant 隔離、invalidation
- 新增 `TokenCounter ABC`（per-provider 實作）
- Compaction 加 `strategy: Literal["structural","semantic","hybrid"]`

---

### 範疇 5：Prompt Construction
- 準確性：✅
- 完整性：⚠️
- 可實作性：✅
- 驗收標準：⚠️
- 企業適配：⚠️
- 對齊 3 大原則：✅

**發現的問題**：
1. **Lost-in-middle 策略可配置但未實證**：spec 沒給「重要內容置首尾」的判定函數（誰是「重要」？memory hint? recent turn? user question?）
2. **缺 cache breakpoint marking**：Anthropic 的 `cache_control` 必須在 PromptBuilder 階段標記，spec 沒提
3. **缺 system prompt versioning**：tenant A 客製 vs 全局升級的衝突處理
4. **缺 prompt observability**：產出 prompt 是否該存 audit（合規 vs 隱私衝突）

**建議修改**：
- 新增 `CacheBreakpoint` 標記 API
- 新增 `PromptAudit` 政策（哪些 tenant 開啟 prompt log）

---

### 範疇 6：Output Parsing
- 準確性：✅
- 完整性：⚠️
- 可實作性：⚠️
- 驗收標準：✅
- 企業適配：✅
- 對齊 3 大原則：✅

**發現的問題**：
1. **ChatResponse 在範疇 6 引用，但定義散在原則 2** — spec 跨文件依賴未明示
2. **缺 streaming partial parsing**：tool_call 是 stream 完整累積還是 partial emit？這影響 SSE 設計
3. **`stop_reason` 字串 per-provider 不同**（Anthropic: `end_turn`/`tool_use`/`max_tokens`；OpenAI: `stop`/`tool_calls`/`length`）— 必須有 enum 中性化，spec 沒寫
4. **`HandoffRequest` 出現但未定義**：是 tool call 的特殊類型？還是另一個 response 欄位？

**建議修改**：
- 在 spec 顯式 import ChatResponse 從原則 2
- 新增 `StopReason` enum
- 釐清 handoff 是 tool 還是 first-class response field

---

### 範疇 7：State Management
- 準確性：✅
- 完整性：⚠️
- 可實作性：⚠️
- 驗收標準：⚠️
- 企業適配：⚠️
- 對齊 3 大原則：✅

**發現的問題**：
1. **缺 reducer pattern**：LangGraph 核心是 typed state + reducer merge，spec 只有 dataclass 沒有 merge 策略；HITL pause/resume、subagent return 都需要 reducer
2. **`time_travel(session_id, version: int)` — version 怎產生？** CC 用 git hash；V2 spec 沒指定 monotonic counter / hash / timestamp
3. **缺 state schema migration**：production server 滾動升級，舊 state schema 怎處理？
4. **驗收「checkpoint storage 抽象化」過寬鬆**：應該驗 「3 種 backend 可切換」（PostgreSQL / Redis / S3-compatible）
5. **HITL pending_approvals 在 LoopState 裡** — 但 HITL 可能跨多 session（人 4 小時後才回應），這跟 session_id 矛盾，需要顯式 split：transient state vs durable state

**建議修改**：
- 新增 `Reducer` ABC + 預設 reducer 集合
- 拆 `TransientState`（in-memory）vs `DurableState`（DB）
- `version` 改 `version: StateVersion = monotonic_counter | content_hash`

---

### 範疇 8：Error Handling
- 準確性：✅
- 完整性：⚠️
- 可實作性：✅
- 驗收標準：⚠️
- 企業適配：⚠️
- 對齊 3 大原則：✅

**發現的問題**：
1. **Stripe `max_attempts=2` 直接寫死** — 應該 per-tool / per-provider 配置；像 transient 網路錯誤可以 5 次，LLM call 可能 2 次，sandbox tool 可能 0 次
2. **缺 circuit breaker**：per-provider failure threshold 後切備援（這是 LLM-neutral 原則 2 的具體應用，spec 沒寫）
3. **缺 error budget**：tenant 月度錯誤預算用完直接拒絕（防 runaway loop 燒錢）
4. **與範疇 9 邊界模糊**：tripwire 觸發是 error 還是 guardrail？驗收沒釐清

**建議修改**：
- `RetryPolicy` 改 per-tool / per-error-type 矩陣
- 新增 `CircuitBreaker` ABC
- 新增 `ErrorBudget` per tenant per day/month

---

### 範疇 9：Guardrails & Safety
- 準確性：✅
- 完整性：⚠️
- 可實作性：⚠️
- 驗收標準：⚠️
- 企業適配：✅
- 對齊 3 大原則：✅

**發現的問題**：
1. **Tripwire 寫成字串 list** — 業界 (OpenAI Agents) 是 callback / hook 模式，可 plug-in；spec 應該是 `Tripwire ABC + register(name, fn)`
2. **缺 「output guardrail 觸發後」處置**：reroll? sanitize? abort? 沒寫等於行為未定
3. **CC ~40 capabilities 獨立 gating** — V2 缺對應的 capability matrix（哪些 tool 屬於哪些 capability bucket？）
4. **缺 prompt injection 防禦深度**：spec 提了 detect，沒提 defense in depth（LLM-as-judge / second-pass?）
5. **驗收「audit log 不可篡改」過弱** — 應該驗 「append-only WORM storage + hash chain」

**建議修改**：
- `Tripwire` 改 ABC + plug-in registry
- 新增 `OutputGuardrailAction: Literal["reroll","sanitize","abort","escalate"]`
- 新增 `CapabilityMatrix` (capability → tool list)

---

### 範疇 10：Verification Loops
- 準確性：✅
- 完整性：⚠️
- 可實作性：✅
- 驗收標準：⚠️
- 企業適配：⚠️
- 對齊 3 大原則：✅

**發現的問題**：
1. **LLM-Judge 用獨立 subagent，但 judge prompt 設計沒 spec**：判別品質 90% 取決於 judge prompt，spec 不能跳過
2. **缺 verifier 自身錯誤處理**：verifier 自己出錯怎辦（fail open vs fail closed）？
3. **企業場景 visual verifier 用例薄弱** — 但 enterprise UI test 仍存在（D365 form 截圖驗證），spec 沒給用例邊界
4. **驗收「3 種 verifier 至少 2 種實作」** — 沒指定哪 2 種；rules + judge 還是 visual + judge？

**建議修改**：
- 新增 §「Judge Prompt Template Library」
- 明定主流量必跑 rules + judge

---

### 範疇 11：Subagent Orchestration
- 準確性：✅
- 完整性：⚠️
- 可實作性：⚠️
- 驗收標準：⚠️
- 企業適配：⚠️
- 對齊 3 大原則：⚠️

**發現的問題**：
1. **Worktree 提了但 server-side 不存在** — philosophy 文件 L266 說「不對應」，但 spec 文件業界原文還在引用 worktree，未顯式註明 V2 不實作
2. **缺 subagent 資源 budget**：token + duration + concurrency 限制，否則 fork 出去燒爆
3. **MAF 5 模式整合方式只給 tool 形式（spawn_group_chat）** — 但 GroupChat 跟 Teammate 概念重疊，未釐清「同一概念兩個 API」是否要去重
4. **缺 subagent 失敗對父 agent 的傳播策略**：fail-fast vs fail-soft vs partial-result
5. **「強制 ≤ 2K token 摘要」過剛**：複雜任務 subagent 可能需要 4-8K，應該 configurable + caller-defined

**建議修改**：
- 顯式寫「Worktree → V2 不對應，理由：server-side 無 user git context」
- `SubagentBudget` dataclass（token/duration/concurrency）
- MAF 5 模式對應到 4 模式（FORK/TEAMMATE/HANDOFF/AS_TOOL）+ 表格說明

---

### 範疇間一致性檢查

| 問題 | 嚴重度 |
|---|---|
| ToolSpec 在範疇 2 與原則 2 重複定義 | 中 |
| ChatClient ABC 在範疇 6 引用但定義在文件 2 原則 2 | 中 |
| Memory 工具（`memory_search`）在範疇 2 與範疇 3 重複 | 中 |
| Subagent 工具（`task_spawn`）在範疇 2 與範疇 11 重複 | 中 |
| 範疇 8 (Error) tripwire 與範疇 9 (Guardrail) tripwire 邊界 | 中 |
| 範疇 4 (Context) subagent delegation 與範疇 11 (Subagent) 接口 | 高 |
| HITL 機制散落在範疇 2/7/8/9，缺中央定義 | 高 |

**建議**：建立 §「跨範疇接口表」附錄，明確標示哪些 dataclass 在哪個文件定義、哪些 tool 在哪個範疇 own。

---

## 文件 2：10-server-side-philosophy.md

### 原則 1：Server-Side First
**定義清晰度**：✅ 8 維對比表清楚
**落地可行性**：⚠️ 6 條 V2 設計約束太抽象
**缺漏**：
1. **認證 / 授權模型**：JWT? OAuth? SSO? Server-side 第一優先
2. **Session affinity**：multi-instance 下 session 黏在哪個 worker？
3. **Streaming channel**：SSE vs WebSocket 選擇（CC 用 stdout，V2 必選一）
4. **Rate limiting**：per-tenant / per-user / per-tool 三層
5. **Data residency**：multi-region 部署時資料駐留法規
6. **Graceful shutdown**：滾動部署時 in-flight loop 怎麼處理（必須跟範疇 7 state 對接）
7. **Async-First 應該獨立成原則**：原則 1 隱含 async，但很多人會忽略

---

### 原則 2：LLM Provider Neutrality
**ChatClient ABC 設計**：⚠️
- 缺 `count_tokens(messages, tools) -> int`
- 缺 `get_pricing() -> PricingInfo`（per-tenant cost tracking 必需）
- 缺 `supports_feature(name: Literal["thinking","caching","vision",...]) -> bool`（capability detection）
- 缺 `model_name` / `model_family` / `context_window`（雖然 ModelInfo 提了，但欄位沒列）

**ToolSpec 中性格式**：⚠️ 大致夠，但 tool result 形式（str vs list[ContentBlock]）會在 Anthropic vs OpenAI 行為不同（Claude 支援 image in tool result，OpenAI 是 string-only）；spec 沒寫「結果如何中性化」。

**「30 分鐘換 provider」驗收**：❌ **不實際**
真實情況：
- Tool calling 行為差異（Claude 偏序列、GPT 偏並行）導致 prompt 需重 tune
- Stop reason 字串映射
- Streaming event 格式差異
- Token counting 差異
- Anthropic prompt caching vs OpenAI cached input 政策不同
- **真實 SLA**：「< 1 sprint（2 週）切換 + < 1 month 對齊品質」更實際

**缺漏**：
- **Multi-provider 同時跑**（per request routing：cost-sensitive 用 GPT-4o-mini、quality 用 Claude）— 比「換」更高階場景
- **Provider-specific feature degradation**：thinking、caching 在 fallback provider 缺失時如何降級

**建議修改**：
- ChatClient ABC 補 4 個方法
- 「30 分鐘」改「< 2 週」、新增「品質對齊 SLA < 1 月」
- 新增 §「Multi-Provider Routing」

---

### 原則 3：CC 架構參考但轉化
**轉化映射表完整度**：⚠️ 19 條覆蓋廣，但 **CC 重要機制有 5 項漏列**：

| CC 機制 | 缺漏 |
|---|---|
| **Hooks system**（PreToolUse/PostToolUse/SessionStart/SubagentStop 等 8+ 種） | ❌ 完全沒提，這是 CC 擴展核心 |
| **Slash commands**（/help, /loop, /sc:* 等使用者自訂指令） | ❌ V2 對應企業 workflow trigger? 沒寫 |
| **Skills system**（自治技能 plugin） | ❌ V2 對應 agent role / capability pack? 沒寫 |
| **Output styles**（控 verbosity、format） | ❌ V2 對應 tone control? 沒寫 |
| **Plan mode / Read-only mode**（行為模式切換） | ❌ V2 對應 dry-run? sandbox preview? 沒寫 |

**「概念複製，實作重寫」**：✅ 方法論正確
**「敵意環境 first」**：✅ 重要洞察，建議再強化

**建議修改**：
- 補 5 條轉化映射（Hooks、Slash、Skills、Output Styles、Plan Mode）
- 提升「敵意環境 first」為**第 4 原則**（zero-trust by design）

---

## 跨文件問題

### 衝突或矛盾

| 議題 | 文件 1 立場 | 文件 2 立場 | 結論 |
|---|---|---|---|
| Worktree subagent | 範疇 11 仍引用 | L266 表「不對應」 | 衝突，spec 應顯式刪除 worktree |
| ToolSpec 定義位置 | 範疇 2 完整定義 | 原則 2 又一次定義 | 重複，應 single source |
| ChatClient ABC 引用 | 範疇 6 用了 | 原則 2 才定義 | 跨文件依賴未明 |
| `on_event` callback | 範疇 1 sync callback | 原則 1 暗示 async-first | 違反 |
| `time_travel` version | 範疇 7 `version: int` | 原則 3 表 git→DB | DB version 來源未定 |

### 範疇是否違反原則

- **範疇 1 `on_event` sync** → 違反原則 1 async-first
- **範疇 11 worktree 殘留** → 違反原則 3 server-side 轉化
- **範疇 5 PromptBuilder 沒提 cache_control** → 違反原則 2（caching 是 provider-specific 但 abstraction 必須涵蓋）

---

## 缺漏的範疇 / 原則

### 第 12 範疇候選：**Observability / Tracing**（強烈建議）
**理由**：
- OpenAI Agents SDK 內建 trace
- LangGraph + LangSmith 是業界標配
- enterprise SLA 必須 OTel
- 文件 1 的「事件流」是雛形但未獨立成範疇
- 11 範疇沒列 ≠ 不必要（業界研究文章是 educational framing，企業部署必補）

**建議內容**：
- TraceContext propagation
- Span 切點（每 turn / 每 tool / 每 LLM call）
- Metric 三軸（latency、token、cost）
- Log structured + correlation id

### 第 13 範疇候選：**Cost & Budget Tracking**
**理由**：
- multi-tenant 必須 per-tenant 計費
- LLM cost 是 #1 OPEX
- 11 範疇完全沒涵蓋
- ChatClient ABC `get_pricing()` 是入口但不夠

### 第 4 原則候選：**Async-First**
**理由**：
- server-side 一切 async
- 文件 2 提了但沒原則化
- 範疇 1 `on_event` 違反就是因為這個

### 第 5 原則候選：**Defense in Depth (Zero-Trust by Design)**
**理由**：
- 文件 2「敵意環境 first」洞察正確但被埋在原則 3 裡
- Multi-tenant + RBAC + audit + sandbox + tripwire 都是同一原則的展開
- 升級為獨立原則更容易強制執行

---

## 總體建議

### 🔴 優先修改（影響可實作性，必改）

1. **建立「跨範疇接口附錄」** — 列出 ToolSpec / ChatClient / Message / LoopState / Tripwire 在哪個檔案 single-source 定義，其他檔案 import 不複製
2. **`on_event` 改 async** — 範疇 1 API 修正
3. **顯式刪除 worktree** — 範疇 11 對齊原則 3
4. **新增第 12 範疇 Observability** — server-side 必備
5. **ChatClient ABC 補完** — `count_tokens` / `get_pricing` / `supports_feature`
6. **Reducer pattern 補進範疇 7** — HITL pause/resume 的隱形依賴
7. **`30 分鐘換 provider` 改 `< 2 週`** — 避免 Sprint 期望管理失敗

### 🟡 次要修改（影響品質，建議改）

1. **每個範疇加 SLO 量化驗收**（latency p95、accuracy threshold、cost budget）
2. **拆 IPA 業務工具到獨立檔案**（範疇 2 通用化）
3. **prompt caching 進範疇 4**
4. **第 13 範疇 Cost Tracking** + **第 4 原則 Async-First**
5. **轉化映射表補 5 條 CC 機制**（Hooks / Slash / Skills / Output Styles / Plan Mode）
6. **HITL 中央化** — 散落 4 個範疇，建議獨立成第 14 範疇或附錄
7. **5 層 Memory 加第二軸**（time scale / modality）

### 🟢 推薦修改（提升完整度）

1. Tool annotations 對齊 MCP 標準（4 hints）
2. Tripwire 改 ABC + plug-in
3. Verifier judge prompt template library
4. RetryPolicy per-tool 矩陣
5. State 拆 transient / durable
6. Capability matrix（CC ~40 capability gating）

---

## 結論

**規劃方向正確、原則站得住、CC 轉化思路成熟**。最大價值在 **3 大原則**（特別是 LLM Neutrality），這比「11 範疇規格」本身更有戰略價值。

**最大風險不是錯，是缺**：tracing、cost、caching、async callback、reducer、capability matrix 這些 enterprise 必備物在 spec 層級隱形，實作 Sprint 才浮現會導致設計重做（V1 對齊度從 27% → 75% 的關鍵就在這些細節）。

**進入 Sprint 前必補**：🔴 7 條優先項。補完後可達 8.5/10，Sprint 風險顯著下降。

**關鍵警告**：「30 分鐘換 provider」是樂觀目標，建議改保守 SLA 避免初期 PR 卡關。

---

**Reviewer 簽署**：Independent expert review
**信心度**：對 11 範疇定義準確性 95%、對 CC 機制完整度 90%、對企業 server-side 適配 85%
