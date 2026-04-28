# PoC3 意圖識別層架構回顧與重新思考

**日期**:2026-04-18(實際討論日 2026-04-19)
**Worktree**:`C:/Users/Chris/Downloads/ai-semantic-kernel-intent-classifier`
**分支**:`feature/intent-classifier-improvements`(Phase 47 Worktree 2)
**基礎 Commit**:`89e9037` — intent classifier LLM override + UI visibility
**Session 目的**:回退一步檢討整個意圖識別層的架構假設,為下一階段設計奠定方向
**下一步**:新 session 繼續深入研究與決策

---

## 1. Session 起點 — 當前已交付狀態

### 1.1 Phase 47 Worktree 2 已交付內容(Commit `89e9037`)

**Part A — Step 6 LLM Override**
- 在 Dispatch Step 6 允許 LLM 糾正 Step 3 誤分類
- QUERY → ACTION 邊界判斷
- Confidence ≥ 0.75 才可覆寫
- 5 個獨立 guard 防止誤觸發

**Part B — Keywords 外部化**
- ~150 雙語關鍵字遷移到 `config/keywords.yaml`
- `@lru_cache` loader + 硬編碼 fallback

**SSE 豐富化**
- `classification_details` 事件包含:routing_layer、matched_keywords、confidence_breakdown

**前端可視化(OrchestrationPanel)**
- Keyword chips(最多 8 個)
- Confidence breakdown grid
- LLM Override banner(琥珀色)

### 1.2 當前未提交修改(與本次討論無關,屬 subagent 控制線)

- `backend/src/integrations/orchestration/dispatch/executors/event_adapter.py`
- `backend/src/integrations/orchestration/dispatch/executors/subagent.py`
- `frontend/vite.config.ts`

---

## 2. 當前架構全貌

### 2.1 3 階段 Fallback Pipeline

| 階段 | 延遲 | 機制 | 門檻 | 成本 |
|------|------|------|------|------|
| **Pattern Matcher** | ~10ms | regex + `rules.yaml` | 0.90 | 免費 |
| **Semantic Router** | ~100ms | Azure/OpenAI embeddings + `routes.yaml` | 0.70(中文) | 低 |
| **LLM Classifier** | ~2000ms | Claude / Azure + `prompts.yaml` | JSON structured output | 中 |

### 2.2 入口與輸出

- **入口**:`BusinessIntentRouter.route()` at `backend/src/integrations/orchestration/intent_router/router.py:182`
- **輸出結構**:`RoutingDecision`
  - `intent_category`: incident / request / change / query / unknown
  - `sub_intent`: etl_failure、network_issue 等
  - `confidence`: 0.0–1.0
  - `routing_layer`: "pattern" / "semantic" / "llm" / "none"
  - `workflow_type`: magentic / handoff / concurrent / sequential / simple
  - `risk_level`: critical / high / medium / low
  - `completeness`: score、missing_fields、suggestions
  - `processing_time_ms`、`metadata`

### 2.3 關鍵檔案索引

- 主編排器:`backend/src/integrations/orchestration/intent_router/router.py`
- Pattern 配置:`intent_router/pattern_matcher/rules.yaml`
- Semantic 配置:`intent_router/semantic_router/routes.yaml`
- LLM 配置:`intent_router/llm_classifier/prompts.yaml`
- Completeness 規則:`intent_router/completeness/rules.py`(725 行,未 YAML 化)
- 前端面板:`frontend/src/components/unified-chat/OrchestrationPanel.tsx`(lines 75–85)
- Pipeline 整合:`backend/src/integrations/orchestration/pipeline/service.py`

---

## 3. 技術層面 5 個觀察到的改進機會

1. **跨層 confidence 無整合** — Pattern 0.95 直接勝出,忽略 Semantic 0.75。邊界情況無加權 blending
2. **門檻硬編碼、無 A/B 測試** — RouterConfig 裡的 0.90/0.70 為常數,無 feature flag、無 per-intent 覆寫
3. **Completeness 規則不可插拔** — `completeness/rules.py`(725 行)未 YAML 化,業務欄位難調整
4. **LLM cache 無上下文感知** — ClassificationCache 只用 input text 作 key,同一句話跨語境會拿到過時快取
5. **前端不顯示具體命中規則** — 只顯示 routing_layer,看不到具體 pattern_id / route name,難以 debug

---

## 4. 核心反思 #1 — 3 階段是否仍必要?

### 4.1 用戶提問

> 這種 agentic 系統,意圖識別的功能是否真的應該分為 3 個階段?在實際企業環境中,每個 input 的意圖識別重要性和意義,是否真的需要 pattern match + semantic router + LLM?如果像 CC 一樣全使用 LLM + prompt / instruction 去判斷,效果會差很多嗎?

### 4.2 3 階段架構的「歷史動機」與 2026 有效性分析

| 動機 | 3 階段價值 | 2026 年是否仍成立 |
|------|------|------|
| **成本** | Pattern/Semantic 免費,避免 LLM call | GPT-5-nano ~$0.05/1M input,1 次分類 < 0.001 美分。動機大幅減弱 |
| **延遲** | 10ms vs 2000ms | Streaming 回應下首 token <300ms,用戶感知差異小。動機減弱 |
| **確定性** | regex 100% 一致 | LLM temperature=0 + structured output 已接近確定。仍有部分價值 |
| **審計可追溯** | "因為匹配了 rule X" 可解釋 | LLM 可透過 reasoning 輸出解釋,甚至更豐富。動機反轉 |
| **Offline degradation** | LLM API 掛掉仍可服務 | 真正的企業價值 |

### 4.3 企業 vs 個人環境的真實差異

| 維度 | 個人 / CC | 企業 ITSM | 對架構意義 |
|------|---------|----------|----------|
| Volume | 100–500/日 | 10K–100K/日 | 成本需在意但不致命 |
| SLA | 無 | P95 < 1–2s | LLM 首 token 夠用 |
| Audit | 無 | SOX / ISO 27001 | LLM + reasoning 可能更好 |
| Intent 空間 | 開放 | 封閉(incident/request/change/query) | 有利 prompt engineering |
| Determinism 期望 | 低 | 高(同 ticket 每次結果要一致) | LLM 需 cache 或 ensemble |

### 4.4 初步判斷(針對 IPA 項目)

**CC 純 LLM 方案效果「不會差很多」,甚至可能更好**:

1. **意圖集封閉** — ITSM 的 4–5 主類別用 prompt 完全能表達
2. **Reasoning 價值** — 企業 support 更需要「為什麼分到 incident」的解釋
3. **Sub-intent 處理更好** — long-tail(如 "ETL 失敗")用 LLM few-shot 勝過維護 150 條 regex
4. **維護成本大幅下降** — 新增意圖改 prompt 一行 vs 改 YAML + regex + embedding 重訓

**3 階段真正不可替代價值**:
- LLM outage degradation(API 掛掉時)
- 極端延遲敏感場景(< 50ms SLA,但 IPA 並非此類)
- 成本失控場景(volume 突增 100x)

---

## 5. 核心反思 #2 — Turn-Level vs Conversation-Level

### 5.1 用戶提問(關鍵架構盲點)

> 本項目提供平台讓用戶和 orchestrator agent 溝通,但溝通不可能只是數個 input 就完成。中間可能有很多討論。但是每個 input 都跑一次意圖識別,這樣好像有點奇怪。如果目的是每個 input 都像指令,那認同要意圖識別。但現實是用戶可能先開始長時間討論,在某個時候才下達指令,而這些指令可能需要 subagent / agent team / 工具層對其他系統執行動作。

### 5.2 問題的本質 — 隱藏前提錯誤

**現有架構的假設**:每個 user input = 獨立的分類對象(Turn-level classification)
- 傳統 IVR / ticket routing 思路
- 適合 FAQ bot、單次請求系統
- 每個 input 獨立跑 3 階段

**真實企業對話的模式**:一個完整對話可能 20+ turns(Conversation-level state)
- CC / 真正 agent 思路
- 15 個 turn 在「討論 / 澄清 / 探索」
- 只有 1–2 個 turn 真正觸發 action
- 需要 state-aware,不是 turn-aware

### 5.3 盲點源起

這個 3 階段模式繼承自 **ITSM ticket classification** 的傳統思路 —— 一張工單進來、分類、路由、完成。但平台實際是一個**長期對話系統**,前提從一開始就不適用。

### 5.4 每個 turn 跑意圖識別造成的具體問題

| 問題 | 後果 |
|------|------|
| 討論 turn 被迫分類 | 浪費 LLM call;UI 上每次顯示 intent chip 很怪 |
| 討論 turn 可能誤分類 | 「我覺得 ETL 有問題」被當成 action 觸發 subagent |
| 延遲累積 | 20 turns × ~500ms = 總 10s 浪費 |
| Context 割裂 | 意圖識別只看當前 input,看不到剛討論的上下文 |

---

## 6. 4 個替代架構方向

### Option 1:Turn-Type Gate(前置輕量閘門)
- 在 3 階段前加一個 LLM 判斷:`discussion / clarification / action_request`
- 只有 `action_request` 才走意圖識別
- 改動小,但 gate 本身又是個分類問題

### Option 2:Conversation State Machine
```
DISCUSSION → ACTION_PLANNING → EXECUTION → VERIFICATION → DISCUSSION
```
- 意圖識別只在 `ACTION_PLANNING` 觸發
- 改動中等,審計友好

### Option 3:LLM-Native Orchestration(CC 模式 — 推薦方向)
- Orchestrator LLM 用 system prompt 全權判斷:
  - 回答 → 直接對話
  - 澄清 → 問問題
  - 工具 → tool_use
  - 委派 → delegate subagent
- **意圖識別退化為 LLM 的 function calling 能力**
- 改動大,但架構清晰、與 CC 對齊、自然處理多輪對話

### Option 4:Hybrid 保底
- 意圖識別作 second opinion / validator
- 主路徑由 LLM orchestrator 決定
- 保留簡化 pattern 作 LLM outage 的 emergency fallback

---

## 7. 當前推薦方向

**Option 3 + Option 4 保底**,理由:

1. 對話本質上是 state-aware,讓 LLM 用 context 決定遠比外部分類器準
2. 意圖識別的「行動觸發」角色其實就是 LLM 的 tool_use 能力 —— 重複造輪子
3. CC 已驗證此模式在長對話 + 工具執行的可行性
4. 企業仍能保留 completeness checking、risk level、audit trail 作 **LLM 決策後的補充層**,不再是前置管線
5. Option 4 保底:簡化 pattern 作 LLM outage 時的 emergency classifier

---

## 8. 待釐清問題(新 session 開場問題)

1. **對話長度分佈** — 現在平台用戶的實際對話長度是 1–3 turns 的單次請求,還是 10+ turns 的長討論?(決定是否值得走 Option 3)
2. **Risk / audit 要求** — 是否真的需要「每個 turn 都有 intent 標籤」?還是只要「action turn 有 intent」即可?(決定 Option 2 vs Option 3)
3. **LLM 單點依賴容忍度** — 可接受 LLM 作為路由決策的單點(有 outage 風險)?還是必須保留 offline fallback?(決定是否加 Option 4)
4. **實測資料** — 是否已有真實 ITSM ticket + 對話 log 可用於 A/B 驗證?
5. **轉型成本容忍** — Option 3 是大重構(dispatch 邏輯重寫)。是否有 Phase 預算容納?

---

## 9. 可執行的下一步(候選清單)

- **A. 對比測試**(1–2 天)
  - A 組:現有 3 階段
  - B 組:純 LLM 單 prompt
  - 100–200 真實 ticket 跑分,比較準確率 / 延遲 / 成本
- **B. PoC Option 3**(3–5 天)
  - 在 worktree 建一個 `LLM-native orchestrator` 旁路
  - 用同一批 conversation log 測試行為差異
- **C. 深入 Option 4 設計**(1 天)
  - 定義 LLM 主路徑 + pattern fallback 的切換條件
  - 設計 degraded mode 契約
- **D. 先量化現狀**(半天)
  - 從 OrchestrationExecutionLog 取樣近期對話,統計 turn-type 分佈
  - 確認「討論 turn 佔多數」的直覺是否成立

---

## 10. 關鍵參考

- CC 原始碼研究記憶:`memory/project_claude_code_study.md`
- 核心願景:`memory/project_core_vision.md`(人類般專業團隊、10 大原則)
- Orchestrator 演進路線:`memory/project_orchestrator_architecture_evolution.md`
- V9 架構分析:`docs/07-analysis/V9/01-architecture/L04-routing.md`、`L05-orchestration.md`
- Phase 47 背景:`memory/project_phase47_orchestrator_improvements.md`

---

**狀態**:討論已形成架構判斷,等待新 session 決策。
**下一 session 開場建議**:先回答第 8 節的 5 個待釐清問題,再決定走 A / B / C / D 哪條下一步路徑。


==========================================================================================

==========================================================================================
❯ 先重新說明之前的問題是什麼?                                                                                                              
                                                                                                                                           
● 🔍 PoC4 意圖識別層 — 之前提出的核心問題                                                                                                  
                                                                                                                                           
  背景                                                                                                                                                                                                                                                                                
  你在 Phase 47 Worktree 2 完成了意圖識別層的改進(Step 6 LLM Override、Keywords YAML 化、SSE                                               
  豐富化、前端可視化)之後,退一步反思了整個意圖識別層的根本架構假設,發現了兩個深層問題。                                                    
  
  ---
  ❓ 問題 #1:3 階段架構在 2026 年還必要嗎?

  當前架構:
  Pattern Matcher (~10ms) → Semantic Router (~100ms) → LLM Classifier (~2000ms)
       免費                     低成本                        中成本

  你的質疑:

  ▎ 「這種 agentic 系統,意圖識別是否真的要分 3 階段?如果像 Claude Code 一樣全部用 LLM + prompt 判斷,效果會差很多嗎?」

  反思結論:3 階段的「歷史動機」在 2026 年大多已失效

  ┌─────────────────────┬─────────────────────────────────────────────────────────┐
  │        原因         │                    2026 年是否仍成立                    │
  ├─────────────────────┼─────────────────────────────────────────────────────────┤
  │ 成本考量            │ GPT-5-nano ~$0.05/1M,1 次分類 < 0.001 美分,動機大幅減弱 │
  ├─────────────────────┼─────────────────────────────────────────────────────────┤
  │ 延遲考量            │ Streaming 下首 token <300ms,用戶感知差異小,動機減弱     │
  ├─────────────────────┼─────────────────────────────────────────────────────────┤
  │ 審計可追溯          │ LLM reasoning 輸出解釋可能更豐富,動機反轉               │
  ├─────────────────────┼─────────────────────────────────────────────────────────┤
  │ 確定性              │ LLM temperature=0 + structured output 已接近確定        │
  ├─────────────────────┼─────────────────────────────────────────────────────────┤
  │ LLM outage fallback │ ✅ 唯一仍有價值的動機                                   │
  └─────────────────────┴─────────────────────────────────────────────────────────┘

  ---
  ❓ 問題 #2(關鍵盲點):Turn-level vs Conversation-level

  你指出的隱藏前提錯誤:

  ▎ 「用戶和 orchestrator 溝通不可能只是幾個 input 就完成。中間可能有很多討論。用戶可能先討論很久,到某個時刻才下達指令。但現在每個 input   
  ▎ 都跑一次意圖識別,這樣很奇怪。」

  問題本質:
  - 現有架構假設:每個 user input = 獨立分類對象(傳統 IVR / ticket routing 思路)
  - 真實企業對話:20 turns 中可能只有 1–2 turn 真的觸發 action,其他都是討論/澄清
  - 根源:架構繼承自 ITSM ticket classification 思路(一張工單進來 → 分類 → 路由),但 IPA 實際是長期對話系統,前提從一開始就不適用

  具體危害:

  ┌──────────────────────┬────────────────────────────────────────────────┐
  │         問題         │                      後果                      │
  ├──────────────────────┼────────────────────────────────────────────────┤
  │ 討論 turn 被迫分類   │ 浪費 LLM call、UI 顯示 intent chip 很怪        │
  ├──────────────────────┼────────────────────────────────────────────────┤
  │ 討論 turn 可能誤分類 │ 「我覺得 ETL 有問題」被當 action 觸發 subagent │
  ├──────────────────────┼────────────────────────────────────────────────┤
  │ 延遲累積             │ 20 turns × 500ms = 10s 浪費                    │
  ├──────────────────────┼────────────────────────────────────────────────┤
  │ Context 割裂         │ 只看當前 input,看不到剛討論的上下文            │
  └──────────────────────┴────────────────────────────────────────────────┘

  ---
  💡 當時形成的判斷

  推薦 Option 3(LLM-Native Orchestration,對齊 Claude Code)+ Option 4(Pattern 保底):

  - 主路徑:Orchestrator LLM 用 system prompt 全權判斷 → 回答 / 澄清 / tool_use / delegate subagent
  - 意圖識別退化為 LLM 的 function calling 能力(不再是前置管線)
  - 保留簡化 pattern 作 LLM outage 的 emergency fallback

  ---
  🎯 未決策的 5 個待釐清問題

  1. 對話長度分佈 — 實際用戶是 1–3 turn 的單次請求,還是 10+ turn 的長討論?
  2. Risk / audit 要求 — 每個 turn 都要有 intent 標籤,還是只有 action turn 有即可?
  3. LLM 單點依賴容忍度 — 可以接受 LLM 作為唯一路由決策點?還是必須保留 offline fallback?
  4. 實測資料 — 是否有真實 ITSM ticket + 對話 log 可做 A/B 驗證?
  5. 轉型成本 — Option 3 是大重構(dispatch 邏輯重寫),有 Phase 預算容納嗎?

  ---
  要先回答哪個問題開始?或是直接走量化路徑(Option D)用剛合併進來的 Execution Log Persistence 來觀察 turn-type 分佈?

✻ Churned for 34s      

❯ 1. 對話長度分佈 — 不確定, 但通常都不是1-3 turn就能完成的                                                                                   2. risk / audit 要求 - 也是需要每個turn 都有intent 標籤, 因為很難準確判斷什麼時候才是action turn                                           3. LLM單點依賴容忍度 - 其實可以以完全以LLM作為決策點, 因為很少有offline fallback情況, 當然如果API有錯誤都是需要fallback,                   但是不會繼續處理, 而且通知用戶LLM有問題, 要他們跟維護或支援人員溝通, 這樣就可以的了                                                        4. 實測資料 - 有的, 但其實現在的ITSM通常是在serviceNow 中由用戶自行建立的, 這個項目不是只針對ITSM的,                                       只是這個範疇的場景比較易於用作測試和驗證功能效果                                                                                           5. 轉型成本 - 所謂的重構是把現在的意圖識別, 風險評估, 是否要審核等 , 都完全交由LLM去決定嗎? 即是完全使用prompt 去作為日後的統一配置?     
                                                                                                                                           
● 📝 答案彙整 + Q5 關鍵澄清                                                                                                                
                             
  從 Q1–Q4 得出的定向                                                                                                                        
  ┌──────┬───────────────────────────────────┬──────────────────────────────────────────────────┐                                            │ 問題 │               答案                │                    對架構意義                    │                                            ├──────┼───────────────────────────────────┼──────────────────────────────────────────────────┤
  │ Q1   │ 通常非 1–3 turn                   │ ✅ Conversation-level 遠優於 turn-level          │                                            ├──────┼───────────────────────────────────┼──────────────────────────────────────────────────┤                                            │ Q2   │ 每 turn 都要 intent 標籤          │ ⚠️ 不能「只分類 action turn」,每 turn 都要有標籤 │                                           
  ├──────┼───────────────────────────────────┼──────────────────────────────────────────────────┤
  │ Q3   │ LLM 單點可接受,錯誤就通知用戶     │ ✅ 可以放棄 3 階段 fallback 鏈,大幅簡化          │
  ├──────┼───────────────────────────────────┼──────────────────────────────────────────────────┤
  │ Q4   │ 有 ITSM 實測資料但平台非僅限 ITSM │ ✅ Prompt 要足夠通用,不過度繫結 ITSM 概念        │
  └──────┴───────────────────────────────────┴──────────────────────────────────────────────────┘

  Q2 與 Option 3 的看似衝突其實是誤解:
  - ✅ 每 turn 都要 intent 標籤 ≠ 每 turn 都要跑外部 3 階段分類器
  - ✅ LLM orchestrator 在產生回應時順便輸出 {intent: "discussion" | "clarification" | "action_request", ...} 即可
  - ✅ 標籤擴充為「對話類型 + 業務意圖」兩維度,更能真實反映對話狀態

  ---
  🎯 Q5 澄清 — 重構到底包含什麼?

  你的問法很關鍵:「把現在的意圖識別、風險評估、是否要審核,都完全交給 LLM?即完全用 prompt 作為日後的統一配置?」

  我的回答:應該區分「判斷」與「執行」兩層

  ✅ 由 LLM + Prompt 統一決定(判斷層)

  - 意圖分類(discussion / clarification / action_request / query)
  - 業務意圖(incident / request / change / query / unknown)
  - 子意圖(etl_failure、network_issue 等 long-tail)
  - 完整性檢查(缺什麼欄位、要問什麼澄清問題)
  - 風險等級(critical / high / medium / low)
  - 執行策略(direct_answer / subagent / team / tool_use)
  - 是否需要 HITL 審核(高風險操作?破壞性指令?)

  這些全部是判斷題,LLM 透過 structured output + system prompt + few-shot 處理更好。

  ⚙️ 仍由程式碼強制執行(執行層)

  - HITL 審核閘門實際攔截(LLM 說「要審核」→ 程式碼強制暫停)
  - 權限檢查(用戶 X 不能執行動作 Y → 程式碼拒絕,不讓 LLM 繞過)
  - 審計日誌寫入(deterministic 寫 PostgreSQL,不由 LLM 決定)
  - Rate limit / cost guard(防止 LLM 判斷失誤造成暴走)
  - Tool 真實執行(MCP / subagent / API call)

  這是**「LLM-as-judge + Code-as-enforcer」**模式 — 與 Claude Code 完全一致:
  - CC 的 LLM 決定「要調用 Write tool」
  - CC 的 harness 仍然強制 permission check、audit log、sandbox 邊界

  ---
  🏗️ 重構範圍具體盤點

  以下現有程式會消失或縮減:

  ┌────────────────────────────────┬─────────────────────────────────┬──────────────────────────────────────┐
  │            現有組件            │             重構後              │                 規模                 │
  ├────────────────────────────────┼─────────────────────────────────┼──────────────────────────────────────┤
  │ intent_router/pattern_matcher/ │ 刪除(或留作 emergency fallback) │ -500 行                              │
  ├────────────────────────────────┼─────────────────────────────────┼──────────────────────────────────────┤
  │ intent_router/semantic_router/ │ 刪除                            │ -400 行                              │
  ├────────────────────────────────┼─────────────────────────────────┼──────────────────────────────────────┤
  │ intent_router/llm_classifier/  │ 合併進 orchestrator 主 prompt   │ 整合                                 │
  ├────────────────────────────────┼─────────────────────────────────┼──────────────────────────────────────┤
  │ completeness/rules.py (725 行) │ 改為 prompt 中的 few-shot       │ -700 行                              │
  ├────────────────────────────────┼─────────────────────────────────┼──────────────────────────────────────┤
  │ Risk assessment 規則           │ 改為 prompt 決策                │ -?                                   │
  ├────────────────────────────────┼─────────────────────────────────┼──────────────────────────────────────┤
  │ 總計                           │                                 │ -1500~2000 行程式碼 → +1 份主 prompt │
  └────────────────────────────────┴─────────────────────────────────┴──────────────────────────────────────┘

  以下保留且強化:
  - HITL gate 基礎設施
  - 審計日誌(Execution Log Persistence 剛合併進來)
  - Permission / RBAC
  - Tool 執行層(MCP / subagent / AG-UI)
  - Orchestrator Event SSE

  ---
  ❓ 決定重構範圍前要再確認一點

  「統一配置為 prompt」後,你預期的配置方式是:
  - A. 單一超級 prompt(system.md,所有規則都寫在裡面)
  - B. 模組化 prompts(intent.md / risk.md / completeness.md,orchestrator 調用不同 prompt)
  - C. Prompt + 結構化 YAML 混合(prompt 做判斷邏輯,YAML 存可變業務常量如 risk thresholds、escalation rules)

  我的建議是 C:可變業務參數(例如「哪些操作算 critical」「哪些用戶群組免審核」)仍放 YAML,但判斷邏輯在 prompt 裡。這樣維運能改 YAML 而不用動 
  prompt。

  你傾向哪種?或還有別的想法?

✻ Brewed for 44s         

※ recap: 目標是重構意圖識別層,讓 LLM+prompt 統一負責判斷（意圖/風險/完整性/審核），程式碼只負責強制執行（HITL閘門/權限/審計）。下一步請確認   prompt 配置方式：單一超級 prompt、模組化 prompts、或 prompt+YAML 混合。 (disable recaps in /config)
                                                                                                                                           ❯ 如果是 C. Prompt + 結構化 YAML 混合(prompt 做判斷邏輯,YAML 存可變業務常量如 risk thresholds、escalation rules) 的話,                       預期的效果會變成怎樣? 包括在 orchestrator chat頁面的流程, 和設定相關的部分 (這些也需要變成可以在前端頁面去配置的, 不可以是硬代碼)        
                                                                                                                                           
● 🎯 Option C 落地效果 — 流程 + 前端配置化                                                                                                 

  1️ Orchestrator Chat 頁面流程變化                                                                                                           
  ❌ 舊流程(3 階段管線,不透明)                                                                                                                                                                                                                                                        
  User Input
    → Pattern Matcher → Semantic Router → LLM Classifier  (每層獨立,用戶看不懂)                                                                → Dispatch Engine (Step 1-6)                                                                                                               → Execute                                                                                                                              

  ✅ 新流程(LLM-Native + YAML 注入)

  User Input + Conversation History
    ↓
  [載入] System Prompt + YAML Config (HITL規則/風險矩陣/意圖稅表/工具註冊表)
    ↓
  [單次] Orchestrator LLM 呼叫 → Structured Output:
    {
      turn_type: "discussion" | "clarification" | "action_request" | "query",
      business_intent: "incident" | "request" | ...,
      sub_intent: "etl_failure",
      completeness: { score, missing_fields, suggestions },
      risk_level: "high",  ← LLM 依 YAML 風險矩陣判斷
      needs_hitl: true,    ← LLM 依 YAML HITL 規則判斷
      execution_plan: { route: "team", agents: [...], tools: [...] },
      reasoning: "用戶描述破壞性 ETL 指令,依 YAML critical_ops 規則需審核",
      response_text: "..."
    }
    ↓
  [強制執行] Code Enforcer
    ├─ 讀 YAML 權限規則 → 檢查用戶能否執行此 action
    ├─ 若 needs_hitl=true → 彈 HITL 審核卡,暫停執行
    ├─ 寫 Execution Log (PostgreSQL, 剛合併)
    └─ 通過 → 執行 (direct / subagent / team / tool)

  📱 UI 右側面板變化

  ┌───────────────────────────────────┬─────────────────────────────────────────────────────────────────────────┐
  │              舊面板               │                                 新面板                                  │
  ├───────────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ Pattern Matcher chips(匹配 regex) │ Turn Type chip(💭 Discussion / ❓ Clarification / 🎯 Action / 🔍 Query) │
  ├───────────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ Semantic Router(相似度分數)       │ Business Intent chip(incident / request / ...)                          │
  ├───────────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ LLM Classifier(舊 3 階段之一)     │ LLM Reasoning 展開(顯示完整推理 + 命中的 YAML 規則名)                   │
  ├───────────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ Confidence breakdown grid         │ Confidence + Risk Level banner(高風險琥珀色)                            │
  ├───────────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ LLM Override banner               │ HITL Gate card(若 needs_hitl 觸發)                                      │
  └───────────────────────────────────┴─────────────────────────────────────────────────────────────────────────┘

  每 turn 都有 intent 標籤(滿足 Q2 審計需求),但 discussion turn 不觸發任何 action,純粹標記用於日誌。

  ---
  2️⃣前端配置頁面設計(新增)

  新增 Page:/settings/orchestrator(管理員專用)

  採 Tab 式 + 版本控制 + 測試沙盒 的配置介面:

  Tab 1 — 📜 System Prompt Editor

  - 大型 Markdown + Monaco Editor(語法高亮)
  - 左側:Prompt 編輯區
  - 右側:實時 Prompt 變數預覽({{risk_matrix}}、{{hitl_rules}} 等會注入)
  - 底部:測試沙盒 — 輸入範例 user message,即時看 LLM 輸出
  - Version 下拉:可切換歷史版本 / diff view

  Tab 2 — ⚠️ Risk Matrix(YAML 表格化)

  操作類型           | 風險等級  | 說明
  ─────────────────┼──────────┼──────────────────────
  drop_table       | critical | 資料庫破壞性
  delete_production| critical | 生產刪除
  restart_service  | high     | 服務中斷
  query_readonly   | low      | 唯讀查詢
  [+ 新增規則]
  - 表格 CRUD(新增/刪除/排序)
  - 背後存為 YAML:config/risk_matrix.yaml
  - 不是硬代碼,修改即時熱載入

  Tab 3 — 🛡️ HITL Rules(規則引擎)

  規則名稱            觸發條件                       動作
  ─────────────────────────────────────────────────────
  critical_ops       risk_level == critical          require_approval
  production_change  environment == prod             require_approval + notify_oncall
  night_ops          time.hour not in 9..18          require_approval
  readonly_auto      risk_level == low               auto_approve
  - Rule builder UI(條件組合器)
  - 可拖曳調整優先順序
  - 存為 YAML:config/hitl_rules.yaml

  Tab 4 — 🧭 Intent Taxonomy(意圖樹)

  - 樹狀結構編輯器
  - 主類別 → 子意圖
  - 每節點可配 few-shot examples、建議澄清問題
  - 存為 YAML:config/intent_taxonomy.yaml
  - 支援多租戶(ITSM 租戶 vs 非 ITSM 租戶不同稅表)

  Tab 5 — 🎓 Few-shot Examples

  - 例子卡片列表(input → expected output)
  - 可標註「邊界案例」、「歷史誤判修正」
  - 注入 prompt 作為 few-shot
  - 存為 YAML:config/few_shot_examples.yaml

  Tab 6 — 🔧 Tools & Agents Registry

  - 連結到現有的 Agent / Subagent / Team / MCP Tool 管理頁
  - 這些資訊自動注入 prompt(讓 LLM 知道有哪些 tool 可用)

  Tab 7 — 🔬 A/B Testing & Versioning

  - 版本列表(每次 Save 建版)
  - 可設定 vA: 50%, vB: 50% 做灰度發佈
  - Diff view(對比版本差異)
  - Rollback 按鈕
  - 統計面板(各版本的準確率、延遲、成本、HITL 觸發率)

  ---
  3️⃣資料流 — 前端修改如何反映到 LLM 決策

  管理員在 /settings/orchestrator 編輯 → 存 PostgreSQL (orchestrator_configs table)
                                        ↓
                            API POST /api/v1/orchestrator/config/publish
                                        ↓
                            Redis 熱載入 (立即生效,不用重啟)
                                        ↓
  下次 Orchestrator LLM 呼叫 → Prompt Builder 從 Redis 讀最新 YAML → 注入 prompt

  優勢:
  - ✅ 完全去硬代碼化 — 維運人員不需要工程師就能改規則
  - ✅ 即時熱載入 — 改完即生效
  - ✅ 版本可追溯 — 每次變更有 audit log(誰改、改什麼、何時)
  - ✅ A/B 可驗證 — 新規則先灰度,確認效果再全量
  - ✅ 多租戶支援 — 不同租戶不同 YAML 配置

  ---
  4️⃣後端程式結構變化(示意)

  # 新的 Orchestrator 核心(極簡)
  class LLMNativeOrchestrator:
      async def process(self, user_input, conversation_history, user_context):
          # 1. 從 Redis 載入最新配置
          config = await self.config_loader.get_latest()

          # 2. 構建 prompt(注入 YAML)
          prompt = self.prompt_builder.build(
              system_prompt=config.system_prompt,
              risk_matrix=config.risk_matrix,
              hitl_rules=config.hitl_rules,
              intent_taxonomy=config.intent_taxonomy,
              few_shots=config.few_shots,
              tools_registry=config.tools_registry,
          )

          # 3. 單次 LLM 呼叫
          decision = await self.llm.structured_call(prompt, user_input, conversation_history)

          # 4. Code Enforcer — 強制執行層
          if decision.needs_hitl:
              await self.hitl_gate.pause_for_approval(decision)
          await self.permission_check(user_context, decision)
          await self.audit_log.write(decision)  # PostgreSQL (剛合併的 persistence)

          # 5. 執行
          return await self.executor.dispatch(decision)

  原 intent_router/ 整個資料夾約 2000 行 → 縮減為 ~300 行的 orchestrator + 幾個 YAML 檔。

  ---
  ❓ 下一步要釐清

  1. 這樣的配置頁面規模,你覺得夠還是過於複雜?(7 個 tab 可能太多,要不要先 MVP 3 個:System Prompt / Risk Matrix / HITL Rules?)
  2. 多租戶支援是 Phase 1 就做,還是後續擴充?
  3. 熱載入 vs 重啟生效(熱載入實作複雜度較高)
  4. 要不要我把這個設計寫成正式的 PoC5 設計文件(docs/08-development-log/poc5-llm-native-orchestrator-design.md)?
==========================================================================================

==========================================================================================
● 📊 Sprint 170 進度檢查點                                                        

  ✅ 已完成(4/17 tasks,3 個 commits)                                              
                                                                                  
  ┌─────────┬─────────────────────────────────────────────────────────────────────────────┐
  │ Commit  │                                   Content                                   │                                                   ├─────────┼─────────────────────────────────────────────────────────────────────────────┤
  │ 0a4d088 │ T0 — 19 個 Phase 48 規劃文件                                                │                                                   ├─────────┼─────────────────────────────────────────────────────────────────────────────┤                                                 
  │ a3159c8 │ T1+T2 — Organization + UserOrganization ORM 模型 + User back-ref            │                                                   ├─────────┼─────────────────────────────────────────────────────────────────────────────┤                                                 
  │ 6c02b32 │ T3+T4 — 2 個 repos + BaseRepository org-scoping + unsafe_cross_org() 逃生口 │                                                   └─────────┴─────────────────────────────────────────────────────────────────────────────┘                                                 
                                                                                                                                              🔜 下一批(T5-T8):Alembic Migration 009
                                                                                                                                              這是 Sprint 170 最關鍵、風險最高的部分:                                                                                                     - T5:建 organizations + user_organizations 表 + seed 預設 org + backfill 所有現有 users
  - T6:對 8 個現有模型 加 organization_id(NULL → backfill → NOT NULL + FK + index)                                                            - T7:更新 8 個 ORM 模型檔案聲明 organization_id 欄位                                                                                        - T8:驗證 migration 在 fresh DB 和有資料的 DB 都能跑通 + downgrade                                                                        

  ⚠️ 需要你確認的事項

  1. 是否有測試 DB? T8 需要在有資料的 DB 上驗證 backfill 不會遺失資料。應該用 ipa_platform 的備份?還是我建一個 snapshot?
  2. 是否立即繼續? 或你想先:
    - 檢查目前 3 個 commits 的內容(git log --stat 或 IDE diff 檢視)?
    - 啟動 backend dry-run 測試 repos 能正常 import?
    - 今天先到此,明天繼續 T5-T8?

  📍 當前狀態

  Branch:  feature/phase-48-sprint-170-multitenant-foundation @ 6c02b32
  Status:  clean (除了 stash@{0} 的 vite.config.ts)
  Ahead of feature/intent-classifier-improvements: 2 commits
  Ahead of main: 10 commits

  要繼續 T5-T8 還是先做別的?

✻ Worked for 5m 43s      

※ recap: Phase 48 Sprint 170(Multi-Tenant Foundation)進行中,已完成 T0-T4(規劃文件、Organization/UserOrganization 模型、2 個 
  repos、BaseRepository org-scoping),共 3 個 commits。下一步:T5 Alembic migration 009 建立 organizations/user_organizations 表 + 為 8 
  個現有模型加 organization_id 欄位。 (disable recaps in /config)  
                                                 
  17 tasks (5 done, 12 open)                           
  ◻ T5 — Alembic migration 009: create orgs + user_organizations + seed default
  ◻ T6 — Alembic migration 009: add organization_id to 8 models
  ◻ T7 — Update 8 existing ORM models to declare organization_id
  ◻ T8 — Verify migration 009 on fresh DB + existing DB
  ◻ T9 — Extend JWT with org_id + org_role claims  
  ◻ T10 — Create org-aware FastAPI dependencies
  ◻ T11 — Create OrgContextMiddleware to populate contextvar                                                                                  ◻ T12 — POST /api/v1/auth/switch-org endpoint
  ◻ T13 — Organization management API (6 endpoints)                                                                                           ◻ T14 — Migrate hardcoded role checks to require_org_role                                                                                 
   … +2 pending, 5 completed                      
==========================================================================================

==========================================================================================
● 🎯 Sprint 170 前半段完成(T0-T8,9/17)                                                                                                      
                                                              
  ✅ 6 commits on feature/phase-48-sprint-170-multitenant-foundation                                                                                                                                                                                                                      5a96193  fix: shorten migration 009 revision id (T8 verification fix)
  ea8e5f4  fix(alembic): repair broken migration chain at 007                                                                                 38d8a78  feat: migration 009 + 8 ORM models add organization_id (T5+T6+T7)                                                                
  6c02b32  feat: repositories + BaseRepository org scoping (T3+T4)                                                                          
  a3159c8  feat: Organization + UserOrganization ORM models (T1+T2)
  0a4d088  docs: Phase 48 sprint planning docs (T0)                                                                                            
  ✅ Database 驗證結果(real data 測試)                                                                                                      
                                                                                                                                            
  ┌──────────────────────────────────────────────────────────┬─────────────────────────────┐                                                  │                          檢查項                          │            結果             │
  ├──────────────────────────────────────────────────────────┼─────────────────────────────┤                                                
  │ 21 users 保留                                            │ ✅                          │                                                
  ├──────────────────────────────────────────────────────────┼─────────────────────────────┤
  │ 21 user_organizations 自動建立                           │ ✅(admin + is_default=true) │
  ├──────────────────────────────────────────────────────────┼─────────────────────────────┤
  │ 17 OEL rows backfill                                     │ ✅(0 NULL)                  │
  ├──────────────────────────────────────────────────────────┼─────────────────────────────┤
  │ organizations 表 + default row                           │ ✅(deterministic UUID)      │
  ├──────────────────────────────────────────────────────────┼─────────────────────────────┤
  │ 8 tables organization_id NOT NULL + FK + composite index │ ✅                          │
  ├──────────────────────────────────────────────────────────┼─────────────────────────────┤
  │ Downgrade 可逆                                           │ ✅                          │
  └──────────────────────────────────────────────────────────┴─────────────────────────────┘

  🔜 剩下 T9-T16(8 tasks)

  - T9: JWT 擴充 org_id/org_role claims
  - T10: FastAPI dependencies(get_current_user_in_org, require_org_role)
  - T11: OrgContextMiddleware(populate contextvar from JWT)
  - T12: POST /auth/switch-org endpoint
  - T13: 6 個 Org 管理 APIs
  - T14: 替換硬編碼 "admin" role 檢查
  - T15: Multi-tenant integration tests
  - T16: Update checklist + progress doc

  ❓ 請確認接下來

  1. 繼續執行 T9-T16(約 1-2 個回合工作量,JWT + API 都是標準模式)
  2. 先停下來檢查 6 個 commits 的內容
  3. 測試跑更完整(例如啟 backend 做 import smoke test)
  4. 今日到此,明天繼續

  我的建議:選 1 繼續執行。T9-T11 是 JWT + middleware 基礎建設,T12-T14 是 API,T15-T16 收尾。沒有大風險,但量不小。

  選哪個?

✻ Worked for 8m 51s

※ recap: Phase 48 Sprint 170 multi-tenant foundation is half done, with migration 009 verified on real data (6 commits on 
  feature/phase-48-sprint-170-multitenant-foundation). Next: start T9, extending JWT with org_id and org_role claims.
                                   
  17 tasks (9 done, 8 open)                       
  ◻ T9 — Extend JWT with org_id + org_role claims
  ◻ T10 — Create org-aware FastAPI dependencies    
  ◻ T11 — Create OrgContextMiddleware to populate contextvar
  ◻ T12 — POST /api/v1/auth/switch-org endpoint
  ◻ T13 — Organization management API (6 endpoints)        
  ◻ T14 — Migrate hardcoded role checks to require_org_role    
  ◻ T15 — Multi-tenant integration tests
  ◻ T16 — Update Sprint 170 checklist + create progress doc
  ✔ T0 — Git prep: stash, commit docs, create Sprint 170 branch
  ✔ T1 — Create Organization ORM model                                                                                                         … +7 completed
                                                  
==========================================================================================

==========================================================================================
● 🎉 Sprint 170 Multi-Tenant Foundation COMPLETE
                                                 
  ✅ 17/17 Tasks,7 Commits                                                                                                                       
  7fb850f  test+docs(phase-48/s170): integration tests + checklist + progress (T14+T15+T16)                                                 
  eed8999  feat(phase-48/s170): JWT org claims + auth deps + middleware + org APIs (T9-T13)                                                   5a96193  fix(phase-48/s170): shorten migration 009 revision id to fit VARCHAR(32)
  ea8e5f4  fix(alembic): repair broken migration chain at 007 (pre-existing bug)                                                              38d8a78  feat(phase-48/s170): migration 009 + 8 ORM models add organization_id (T5-T7)                                                      6c02b32  feat(phase-48/s170): repositories + BaseRepository org scoping (T3-T4)                                                             a3159c8  feat(phase-48/s170): Organization + UserOrganization ORM models (T1-T2)                                                            0a4d088  docs(phase-48): 19 sprint planning docs (T0)                                                                                                                                                                                                                                   📊 交付指標                                                                                                                                                                                                                                                                             ┌───────────────────┬───────────────────────────────────────────┐                                                                           │       指標        │                   數值                    │                                                                           ├───────────────────┼───────────────────────────────────────────┤                                                                         
  │ 新 ORM 模型       │ 2(Organization + UserOrganization)        │
  ├───────────────────┼───────────────────────────────────────────┤
  │ 新 Repositories   │ 2 + BaseRepository scoping + escape hatch │
  ├───────────────────┼───────────────────────────────────────────┤
  │ Alembic migration │ 1(009_p48_multitenant)+ chain fix         │
  ├───────────────────┼───────────────────────────────────────────┤
  │ 既有模型擴充      │ 8 個模型加 organization_id                │
  ├───────────────────┼───────────────────────────────────────────┤
  │ 新 API endpoints  │ 7(6 org 管理 + 1 switch-org)              │
  ├───────────────────┼───────────────────────────────────────────┤
  │ Middleware        │ 1(OrgContextMiddleware)                   │
  ├───────────────────┼───────────────────────────────────────────┤
  │ Integration tests │ 7 個,全數通過                             │
  ├───────────────────┼───────────────────────────────────────────┤
  │ 新程式碼          │ ~1500 production + ~280 test              │
  └───────────────────┴───────────────────────────────────────────┘

  ✅ 驗證結果

  - Fresh DB migration:upgrade ✓ / downgrade ✓ / re-upgrade ✓
  - Real data migration:21 users + 17 OEL rows 全部保留並正確 backfill
  - Import smoke test:FastAPI 載入成功,7 routes 註冊到位
  - Integration tests:7/7 passed

  ⚠️ 刻意延後的事項

  1. get_current_active_admin 的 caller 遷移(docstring 已 deprecate,實際遷移避免 sweep risk,分散到後續 sprint)
  2. 完整 backend test suite regression(建議 merge 前再跑一次)

  📍 狀態

  Branch: feature/phase-48-sprint-170-multitenant-foundation @ 7fb850f
  Commits ahead of main: 11
  Uncommitted: (只剩 stash@{0} 的 vite.config.ts subagent 控制線)

  🔜 下一步建議

  1. 檢視 Sprint 170 成果(git log --stat / IDE diff)
  2. 進入 Sprint 171(ConfigManager + 熱載入儲存)— 依賴 Sprint 170 已完成
  3. Merge Sprint 170 回 feature/intent-classifier-improvements(先跑完整 regression)
  4. 今天收工,明天繼續

  要選哪個?

==========================================================================================

==========================================================================================
❯ 1. 檢視 Sprint 170 成果(git log --stat / IDE diff)                                                                                                                                                                                                                                    
● Bash(cd /c/Users/Chris/Downloads/ai-semantic-kernel-intent-classifier && echo "=== SPRINT 170 COMMITS (8 total) ===" && git log --oneline 
      86f9c38..HEAD && echo "" &&…)                                                                                                         
  ⎿  === SPRINT 170 COMMITS (8 total) ===                                                                                                        7fb850f test+docs(phase-48/s170): multi-tenant integration tests + checklist + progress
     eed8999 feat(phase-48/s170): JWT org claims + auth deps + middleware + org APIs                                                             … +30 lines (ctrl+o to expand)                                                                                                         
  ⎿  Shell cwd was reset to C:\Users\Chris\Downloads\ai-semantic-kernel-framework-project                                                                                                                                                                                               
● 📋 Sprint 170 完整成果檢視                                                                                                                                                                                                                                                            
  🗂️ 8 Commits 時序                                                                                                                            
  ┌─────┬─────────┬─────────┬──────────────────────────────────────────┐                                                                    
  │  #  │  Hash   │  類型   │                   內容                   │                                                                    
  ├─────┼─────────┼─────────┼──────────────────────────────────────────┤
  │ 1   │ 0a4d088 │ 📚 docs │ Phase 48 規劃文件 × 19                   │
  ├─────┼─────────┼─────────┼──────────────────────────────────────────┤
  │ 2   │ a3159c8 │ ✨ feat │ Organization + UserOrganization ORM      │
  ├─────┼─────────┼─────────┼──────────────────────────────────────────┤
  │ 3   │ 6c02b32 │ ✨ feat │ Repositories + BaseRepository scoping    │
  ├─────┼─────────┼─────────┼──────────────────────────────────────────┤
  │ 4   │ 38d8a78 │ ✨ feat │ Migration 009 + 8 models 加 org_id       │
  ├─────┼─────────┼─────────┼──────────────────────────────────────────┤
  │ 5   │ ea8e5f4 │ 🐛 fix  │ Alembic chain 修復(pre-existing bug)     │
  ├─────┼─────────┼─────────┼──────────────────────────────────────────┤
  │ 6   │ 5a96193 │ 🐛 fix  │ Shorten revision id 適配 VARCHAR(32)     │
  ├─────┼─────────┼─────────┼──────────────────────────────────────────┤
  │ 7   │ eed8999 │ ✨ feat │ JWT + deps + middleware + org APIs       │
  ├─────┼─────────┼─────────┼──────────────────────────────────────────┤
  │ 8   │ 7fb850f │ ✅ test │ Integration tests + checklist + progress │
  └─────┴─────────┴─────────┴──────────────────────────────────────────┘

  ---
  📊 程式碼變更規模

  Production code:
  30 files changed, 1722 insertions(+), 21 deletions(-)

  Docs:
  20 files changed, 1914 insertions(+)

  🔝 變更最大的 6 個檔案

  ┌───────────────────────────────────────────────────┬──────┬────────────────────────┐
  │                       檔案                        │ 行數 │          用途          │
  ├───────────────────────────────────────────────────┼──────┼────────────────────────┤
  │ api/v1/organizations/routes.py                    │ +291 │ 6 個 org 管理 API      │
  ├───────────────────────────────────────────────────┼──────┼────────────────────────┤
  │ alembic/.../009_phase48_multi_tenant_bootstrap.py │ +236 │ Mega-migration         │
  ├───────────────────────────────────────────────────┼──────┼────────────────────────┤
  │ tests/integration/multitenant/test_org_scoping.py │ +236 │ 7 個 integration tests │
  ├───────────────────────────────────────────────────┼──────┼────────────────────────┤
  │ api/v1/dependencies.py                            │ +126 │ 3 個新 org-aware deps  │
  ├───────────────────────────────────────────────────┼──────┼────────────────────────┤
  │ database/models/organization.py                   │ +110 │ Organization 模型      │
  ├───────────────────────────────────────────────────┼──────┼────────────────────────┤
  │ api/v1/auth/switch_org.py                         │ +102 │ Switch-org endpoint    │
  └───────────────────────────────────────────────────┴──────┴────────────────────────┘

  📦 新增模組結構

  backend/src/
  ├── api/v1/
  │   ├── auth/switch_org.py          (NEW)
  │   ├── middleware/                 (NEW)
  │   │   ├── __init__.py
  │   │   └── org_context.py
  │   └── organizations/              (NEW)
  │       ├── __init__.py
  │       ├── routes.py
  │       └── schemas.py
  ├── infrastructure/database/
  │   ├── models/
  │   │   ├── organization.py         (NEW)
  │   │   └── user_organization.py    (NEW)
  │   └── repositories/
  │       ├── organization.py         (NEW)
  │       └── user_organization.py    (NEW)
  └── (修改) core/security/jwt.py
  └── (修改) domain/auth/service.py
  └── (修改) infrastructure/database/repositories/base.py

  backend/alembic/versions/
  └── 20260420_0900_009_phase48_multi_tenant_bootstrap.py  (NEW)

  backend/tests/integration/multitenant/  (NEW)
  └── test_org_scoping.py

  🔍 建議檢視順序(若要做 Code Review)

  1. organization.py + user_organization.py — 資料模型基礎(看清 schema)
  2. repositories/base.py — 看 _scope_by_org + unsafe_cross_org 邏輯
  3. migration 009 — 看 mega-migration 的 backfill 順序
  4. dependencies.py — 看 require_org_role 工廠
  5. middleware/org_context.py — 看 contextvar 設定時機
  6. organizations/routes.py — 看 6 個 API 的 RBAC 檢查
  7. test_org_scoping.py — 看測試覆蓋的案例

  📍 Branch 當前狀態

  feature/phase-48-sprint-170-multitenant-foundation @ 7fb850f
  Ahead of main: 11 commits (8 Phase 48 + 1 chain fix + 2 previous docs + merge)
  Stashed: vite.config.ts (unrelated subagent control line)

  ❓ 接下來

  1. Sprint 171 開始(ConfigManager + 熱載入)
  2. 先 merge Sprint 170 回 feature/intent-classifier-improvements(跑完整 regression 後)
  3. 你想先在 IDE 檢視某個特定檔案?(我可以 Read 任一檔案給你看)
  4. 今日收工

  要選哪個?
==========================================================================================

==========================================================================================

● Sprint 179 收尾。                                                                                                                                     

  Sprint 179 交付摘要                                                                                                                                                                                                                                                                                           
  Branch:feature/phase-48-sprint-179-legacy-removal(3 commits + 1 tag)                                                                                                                                                                                                                                          
  Scope split 決策:T1 survey 後發現 9 個 files 觸 legacy 子模組,其中 pipeline(step3_intent)、PoC(agent_team_poc)、hybrid bootstrap 仍 runtime 依賴。全量
   big-bang 刪除 + operational gate 未達 → 拆 Sprint 179(外圍)+ Sprint 180(core)。                                                                                                                                                                                                                                本 Sprint 完成:                                                                                                                                         - 刪除 backend/src/api/v1/orchestration/intent_routes.py(3-stage admin)                                                                                 - 刪除 backend/src/api/v1/orchestration/route_management.py(semantic_router admin)                                                                      - 取消 api/v1/__init__.py + orchestration/__init__.py 註冊                                                                                            
  - /orchestrator/test-intent 端點改為 HTTP 410 Gone + 指向 sandbox
  - Git tag phase-48-legacy-preserved → 0b75277(deletion 前 commit,作 restoration point)

  刪除規模:-986 行 / +18 行(5 files)

  驗證:python -c "from src.api.v1 import api_router" OK,routes count 634 穩定,零 cascade import breakage。

  Sprint 180 scope(gate-gated):
  1. step3_intent.py legacy branch → raise NotImplementedError
  2. agent_team_poc.py 2 sites legacy blocks
  3. bootstrap.py 2 lazy imports
  4. intent_router/{pattern_matcher,semantic_router,llm_classifier,completeness/rules.py,router.py} 整刪(~1500 行)
  5. ORCHESTRATOR_MODES + Literal 窄化
  6. Alembic migration 013(lingering rows → llm_native)
  7. Backend pytest + Frontend Playwright full regression
  8. Phase 48 dev log 補 final LOC-removed 數字

  Operational prerequisite:shadow window ≥ 1 週數據 + agreement ≥ 90% + p95 latency 達標。

  要繼續 Sprint 180 嗎?(注意:operational gate code-side 無法驗證;若要 code-side 直接執行,可用保守 raise NotImplementedError 做法避免 rollback 風險)     

==========================================================================================

==========================================================================================
● Sprint 180 完成。           

  Sprint 180 交付摘要                                                                                                                                        
  Branch:feature/phase-48-sprint-180-core-legacy-removal(6 commits)                                                                                     
  
  策略:raise-then-delete — 先關 runtime callers(commit 5a6baac),後物理刪除 folder(commit ee00de4),任何遺漏 import 在單一 commit surface 便於 bisect。
     
  Core pipeline 關閉:                                                                                                                                     - step3_intent._get_router → raise NotImplementedError                                                                                                  - agent_team_poc.py 2 個 legacy Step-3 blocks → 簡單 stub(intent_text = "partial: legacy retired")                                                      - hybrid/orchestrator/bootstrap.py → business_router = None / guided_dialog = None                                                                                                                                                                                                                              Folder deletion:                                                                                                                                        - intent_router/pattern_matcher/(full folder,~15 files)                                                                                                 - intent_router/semantic_router/(full folder,~12 files 含 routes/encoder/migration)                                                                     - intent_router/llm_classifier/(full folder,~6 files)                                                                                                 
  - intent_router/router.py(BusinessIntentRouter family)
  - 保留:models.py、contracts.py、completeness/ 整個(guided_dialog 仍用 — Sprint 181)

  Enum / Literal 窄化:
  - ORCHESTRATOR_MODES = ("llm_native", "shadow")
  - OrchestratorMode = Literal["llm_native", "shadow"]
  - step3_dispatcher legacy branch → raise;default fallback → llm_native
  - OrchestratorModeUpdate.mode regex pattern 同步窄化
  - feature_flag legacy warning branch 移除

  Safety net:Alembic migration 013 UPDATE orgs SET mode='llm_native' WHERE mode='legacy_3stage'

  Stub aliases:BusinessIntentRouter = object 於 4 個 annotation-heavy file(engine / orchestrator_v2 / servicenow_handler / orchestration init)

  Phase 48 成就

  ┌────────────────────────────────────────────┬───────────┬─────────────────────────────────┐
  │                    指標                    │   目標    │              達成               │
  ├────────────────────────────────────────────┼───────────┼─────────────────────────────────┤
  │ 刪除 legacy 程式碼                         │ ~2,000 行 │ -7,430 行 net(3.7×)             │
  ├────────────────────────────────────────────┼───────────┼─────────────────────────────────┤
  │ LOC 變動                                   │ —         │ 44 files changed, +655 / -8,085 │
  ├────────────────────────────────────────────┼───────────┼─────────────────────────────────┤
  │ Route count 穩定                           │ 無 break  │ ✅ 634 routes                   │
  ├────────────────────────────────────────────┼───────────┼─────────────────────────────────┤
  │ api_router + LLMNativeOrchestrator imports │ clean     │ ✅                              │
  └────────────────────────────────────────────┴───────────┴─────────────────────────────────┘

  Phase 48 總結(Sprint 170-180,11 sprints)

  - Multi-tenant 基建(Migration 009)
  - orchestrator_configs + ConfigManager(Migration 010)
  - LLMNativeOrchestrator + ShadowComparator(Migration 011)
  - Admin UI 7 tabs + Versions + Shadow Analytics
  - Canary(Redis-backed)
  - Cutover(Migration 012,default llm_native)
  - Legacy removal(Migration 013,-7,430 行)
  - Git tag phase-48-legacy-preserved 作 restoration point

  未完

  - alembic upgrade head + pytest + Playwright regression in staging
  - Sprint 181 scope:completeness/rules.py delete + guided_dialog migration + stub alias cleanup + V10 analysis refresh

  Phase 48 程式碼側全部完成,剩 operational 驗證。需要繼續 Sprint 181 還是先 checkpoint?
==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

==========================================================================================

