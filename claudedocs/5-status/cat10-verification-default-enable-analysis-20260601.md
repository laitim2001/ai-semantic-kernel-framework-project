# B-8 深度分析:Cat 10 Verification 預設開啟前的成本/品質/風險評估

**Purpose**: 評估把 `chat_verification_mode` 預設 `disabled` → `enabled` 的成本、品質、風險。**結論:現在不應翻預設**——有 3 個 launch-blocker(billing 漏記 + 模板不適配 + 零 real-LLM 測試),且收益要等 real-LLM 上線才兌現。本檔為 research 分析(非 sprint plan,守 rolling 紀律)。
**Category**: 範疇 10 (Verification Loops) — operational rollout decision
**Scope**: B 區優化分析 / B-8
**Created**: 2026-06-01
**Status**: Active(analysis;decision deferred — 對應既有 `AD-Cat10-Wire-1-Production`)

**Modification History (newest-first)**:
- 2026-06-01: Initial creation — B-8 Cat 10 預設開啟成本/品質/風險分析(Explore 蒐證 + 主 session 親驗 4 根支柱)

**Related**:
- `integration-progress-20260531.md` §B-8
- `cat10-verifier-factory-disposition-analysis-20260531.md`(B-10,同 Cat 10)
- `docs/.../sprint-55-5/retrospective.md` §AD-Cat10-Wire-1-Production(既有 deferred 決策)
- `04-anti-patterns.md` AP-9(No Verification Loop)/ AP-4(Potemkin)
- CLAUDE.md §約束 2 主流量驗證 / §Multi-tenant(quota)

---

## 0. 一句話結論

> **不要現在翻預設。** 機制完整(`run_with_verification` + `LLMJudgeVerifier` 真的會跑、會發 SSE、會落 DB log),但翻 `enabled` 前有 **3 個 launch-blocker**:① judge 的 LLM 呼叫**不進 cost ledger 也不進 quota**(billing/quota 雙漏記)② 預設模板 `safety_review` 是為 **Cat 9 fallback** 寫的、不適合當通用 final-output judge(高假陽性風險)③ enabled 路徑**零 real-LLM 測試**(假陽性率、延遲、成本全未實測)。且收益要等 real-LLM 上線(需 Azure key)才存在。建議維持既有 `AD-Cat10-Wire-1-Production` deferred,翻預設與 real-LLM go-live + 下列修補配對。

---

## 1. 機制現況(均經主 session 親 Read 複核,行號連續)

| 面向 | 事實 | 證據 file:line |
|------|------|----------------|
| 包裝器 | `run_with_verification(*, ..., max_correction_attempts=2)`;passthrough:registry None/空 → 直接 `agent_loop.run()` 零開銷 | `correction_loop.py:110-117` |
| 只驗 end_turn | 非 end_turn(max_turns/budget/tripwire/cancelled)直接放行不驗 | `correction_loop.py:143-147` |
| Judge 獨立 LLM call | `LLMJudgeVerifier.verify()` 自建 `ChatRequest` 呼 `self._chat.chat()`,**共用主 loop 的同一 adapter**(非較便宜模型)| `llm_judge.py:86-89` + `handler.py:246-248` |
| Judge 只看 output | prompt 只 `{output}` 代入,**不含對話歷史** | `llm_judge.py:98-106` |
| Fail-closed | judge 任何例外 → `passed=False` | `llm_judge.py:90-96` |
| 落 DB log | 每個 verifier 結果 best-effort 寫 `verification_log` | `correction_loop.py:179-190` |
| 發 SSE | `verification_passed` / `verification_failed` 已序列化 | `sse.py:251-270` |

---

## 2. 成本實錘:correction 是「整個 loop 重跑」(非多一輪)

**親驗 `correction_loop.py:121-209`**:
- `while True`(L121)→ verifier 失敗(L197)→ `attempt += 1; current_input = _build_correction_input(...)`(L208-209)→ **回圈頂 `agent_loop.run()` 從頭重跑**(L126)。
- **不是**「多執行一個 turn」,是**重跑整個 agent loop**(所有 turn + 所有 tool call + 所有內部 LLM call)。

**每次 chat 的額外 LLM 成本(預設 1 verifier)**:
| 情境 | 額外 judge call | 額外 full-loop 重跑 | 總 LLM 成本倍數 |
|------|:---:|:---:|------|
| 通過(happy path)| +1 | 0 | 1× loop + 1 judge |
| 1 次失敗→修正通過 | +2 | +1 | **~2× loop + 2 judge** |
| 2 次失敗(用盡)| +3 | +2 | **~3× loop + 3 judge** |

> 即:最壞情況一次 chat 可變成 **3 倍 loop token + 3 個 judge call**。對 LLM-cost 敏感的 SaaS,這是必須先量化的開銷。

---

## 3. 🔴 Launch-blocker A:judge 呼叫不進 cost ledger + 不進 quota(billing 漏記)

**親驗**:
- cost ledger 只在 `LoopCompleted` 事件記帳(`router.py:412-421`,讀 `event.input_tokens/output_tokens/provider/model`)。
- judge 走 `llm_judge.py:88` `self._chat.chat()` **獨立呼叫**,token **不經 AgentLoop 的 accumulator** → 不會出現在任何 `LoopCompleted` → **完全不入 cost ledger**。
- 同理 quota:`router.py` 的 quota enforcement 讀 `LoopCompleted.total_tokens`,judge token 同樣漏記 → enabled 後 **實際 token 消耗被低估**,租戶可超用配額而不被擋。

**影響**:多租戶 SaaS 的 billing 正確性 + quota 強制都會因 Cat 10 enabled 而失真。翻預設前**必須**先讓 judge call 入帳(可在 `LLMJudgeVerifier` 或 wrapper 加 cost-ledger 寫入點,對齊 `AD-Cost-Ledger-*` 既有模式)。

---

## 4. 🔴 Launch-blocker B:預設模板 `safety_review` 是 Cat 9-fitted,不適合當通用 judge

**親驗 `safety_review.txt`**:
- L1-3:judge 只判「harmful/unsafe/policy-violating」(武器/自殘/仇恨/非法/jailbreak)。
- **L17-18 白紙黑字**:「this judge is invoked as a **Cat 9 fallback** when regex-based detectors return low confidence. Be conservative: **borderline cases lean unsafe**。」

**問題**:
- 它是為 Cat 9(guardrail)低信心 fallback 設計,**不是**通用 final-output 品質 judge。
- 「borderline lean unsafe」的保守偏置用在**一般 chat 全流量** → 高**假陽性**:正常回答被判 unsafe → 觸發無謂的 correction 重跑(成本 §2 倍數 + 延遲 §6)。
- `factual_consistency.txt` 更糟:它要對照「conversation context」事實查核,但 judge prompt **只給 `{output}` 不給歷史**(`llm_judge.py:98-106`)→ 模板要的 context 根本拿不到。

**影響**:翻預設前需設計一個**通用 final-output judge 模板**(非 Cat 9 安全模板),並評估假陽性率。

---

## 5. 🔴 Launch-blocker C:enabled 路徑零 real-LLM 測試

**親驗(Explore + git grep)**:
- 全 verification 測試**無 `@pytest.mark.real_llm`**;smoke test 的 "enabled" 用 `RulesBasedVerifier(rules=[])`(no-op 永過),**不是真 `LLMJudgeVerifier`**。
- production 路徑(`build_real_llm_handler` + Azure + `safety_review`)**零測試覆蓋**。
- **無任何測試量測延遲或成本**。

**影響**:假陽性率、p95 延遲、每 chat 成本全是未知數。CLAUDE.md §約束 2(主流量驗證)+ §測試優先(端到端 ≥1 關鍵案例)未滿足。翻預設前需 real-LLM e2e(需 Azure key,與 B-7 / `AD-Cat4-7-8-10-RealLLM-E2E` 同前提)。

---

## 6. UX/延遲:judge 是 `loop_end` 前的 blocking tail

**親驗 `correction_loop.py:131-134`**:
- LLM 內容事件**即時 yield**(串流照常)。
- 但 `LoopCompleted` 被**扣住**(`continue` 不 yield)→ 先跑 judge → 通過才放行 `loop_end`。

**影響**:使用者看到內容串完後,要**多等一個完整 judge LLM call** 才收到 `loop_end`(Sprint 54.1 retro 稱 p95 < 5s,但無測試可複現)。若 correction,使用者收到 `verification_failed` 後**整個 loop 重跑**才 `loop_end` → 等待時間約翻倍 + 2× judge 延遲。

---

## 7. 風險彙整 + 翻預設前置清單

| # | 風險 | 嚴重度 | 翻預設前須做 |
|---|------|:---:|------|
| A | judge token 漏記 cost ledger + quota | 🔴 高(billing/合規)| judge call 入帳(LLMJudgeVerifier/wrapper 加 ledger 寫入)|
| B | `safety_review` 模板不適配通用 judge | 🔴 高(假陽性→無謂重跑)| 設計通用 final-output judge 模板 + 量假陽性率 |
| C | 零 real-LLM 測試 | 🔴 高(未實證)| real-LLM e2e(需 Azure key)|
| D | 成本最壞 3× loop + 3 judge | 🟡 中 | 量化平均成本;考慮降 `max_correction_attempts` 或 judge 用較便宜模型 |
| E | `loop_end` 前 blocking judge 延遲 | 🟡 中 | 量 p95;考慮 judge 並行/非阻塞設計 |
| F | non-end_turn correction 無 verification_failed 信號(KEY UNCERTAINTY 5)| 🟢 低 | 補事件 / 文件化行為 |

---

## 8. 給決策的最短建議

| 問題 | 答案 |
|------|------|
| 機制能跑嗎? | ✅ 完整(wrapper + judge + SSE + DB log 都在)|
| 現在能翻預設嗎? | ❌ 3 個 launch-blocker(billing 漏記 / 模板不適配 / 零 real 測試)|
| 急嗎? | ❌ 收益要等 real-LLM 上線(需 Azure key);現預設 disabled 是安全的 |
| 最佳時機? | 與 real-LLM go-live 配對,且**先**清 A+B+C |
| 對應既有 AD? | `AD-Cat10-Wire-1-Production`(Sprint 55.5 已 defer 為 operational 決策)— 本分析補上「為何還不能翻」的具體證據,維持 deferred |
| 順手可記的新債 | judge cost-ledger 漏記(建議獨立 AD)+ 通用 judge 模板缺(建議獨立 AD)|

> 不需任何 code 變更;本檔結論 = 維持 disabled + 列出翻預設的 3 前置 blocker。翻預設本身是未來與 real-LLM 上線配對的 sprint。
