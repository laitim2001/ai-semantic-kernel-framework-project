# V1 Anti-Patterns（V2 必須避免的反模式）

**建立日期**：2026-04-23
**版本**：V2.0
**用途**：每個 PR 必須通過此檢查清單

---

## 為什麼建立此文件

V1 累積了 27% 真實對齊度的問題，根因可歸納為 10 個反模式。V2 必須在 Day 1 就建立防護機制，避免重蹈覆轍。

---

## Anti-Pattern 1：Pipeline 偽裝成 Loop

### V1 問題
`pipeline/service.py:173-394` 用 `for step in self._steps:` 線性執行 8 步，**包裝成 agent loop 的樣子**，但實際上是順序機。

### 症狀
- 代碼有「step」、「pipeline」字眼
- 流程是線性的：Step1 → Step2 → ... → Step8 → 結束
- 沒有「回到上一步」的機制
- 工具結果沒有回注 LLM 重新推理

### V2 防護
```python
# ❌ 禁止
class OrchestrationPipeline:
    async def run(self, ctx):
        for step in self._steps:
            await step.execute(ctx)
        return ctx

# ✅ 正確
class AgentLoop:
    async def run(self, state: LoopState):
        while True:
            response = await self.llm_client.chat(state.messages, ...)
            if not response.tool_calls:
                return response  # end_turn
            for tc in response.tool_calls:
                result = await self.execute_tool(tc)
                state.messages.append(to_user_message(result))  # ⭐ 回注
            if state.should_terminate():
                return state.compose_final()
```

### 檢查清單
- [ ] 主路徑使用 `while` 而非 `for` 固定迴數
- [ ] `stop_reason` 驅動退出
- [ ] 工具結果以 `user message` 形式 append 到 messages
- [ ] **代碼中不使用 "pipeline" 字眼**（除非真的是預處理 pipeline）

---

## Anti-Pattern 2：Side-Track Code Pollution

### V1 問題
Claude SDK 整合 30+ 檔案中，**大部分不在主流量**（autonomous / orchestrator / hooks），但被當成「項目能力」計算。

### 症狀
- 代碼存在但 `grep -r "from src.X import"` 找不到主流量呼叫
- 模組標 "PoC" / "Experimental" 但久不淘汰
- 多個版本並存（`orchestrator_v1.py`、`orchestrator_v2.py`）

### V2 防護
```python
# 主流量代碼必須通過：
# 1. 從 api/v1/ 進入點可達
# 2. 有 e2e 測試覆蓋
# 3. 在 V2 文件 `06-phase-roadmap.md` 明確列出

# Side-track 規則：
# - 任何 PoC 代碼放 `experimental/` 目錄（不在 src/ 下）
# - PoC 必須有 deadline（最多 2 sprint）
# - 過期未合併必須刪除
```

### 檢查清單
- [ ] 新代碼必須能從 `api/v1/` 追蹤到呼叫
- [ ] PoC 代碼放在 `experimental/`
- [ ] 沒有 `_v1`、`_v2`、`_old`、`_new` 後綴的多版本檔案
- [ ] 每月 retro 檢查無人使用的代碼

---

## Anti-Pattern 3：Cross-Directory Scattering

### V1 問題
Guardrails 散落 6 處：`core/security/`、`orchestration/hitl/`、`orchestration/risk_assessor/`、`orchestration/audit/`、`claude_sdk/hooks/`、`agent_framework/acl/`。

### 症狀
- 同一範疇代碼分布超過 2 個目錄
- 跨目錄相互不知對方存在
- 重複實作（多個 audit logger）

### V2 防護
**範疇單一歸屬原則**：
```
範疇 X 的所有代碼 → backend/src/agent_harness/0X_xxx/
平台級服務 → backend/src/platform/{governance, observability, ...}
```

新增代碼時 PR 模板要求：
```markdown
## 範疇歸屬
此 PR 屬於範疇 ___（必填）：
- [ ] 1. Orchestrator Loop
- [ ] 2. Tool Layer
- [ ] 3. Memory
... (11 選 1)
- [ ] 跨範疇基礎設施（platform/）
- [ ] 業務領域（business_domain/）
- [ ] 適配層（adapters/）
- [ ] 基礎設施（infrastructure/）

如選跨範疇，需說明：________
```

### 檢查清單
- [ ] 每個範疇代碼集中於一個目錄
- [ ] 跨範疇共用邏輯放對應 cross-cutting 目錄（governance / identity / observability）
- [ ] PR 必須宣告範疇歸屬
- [ ] 每月檢查跨目錄散落

### V2 強制 Lint 規則（2026-04-23 強化）

> **校正**：原版「PR 模板自檢」不夠強制。V1 全 10 個 AP 都中，AP-3 散落最容易復發。**lint 是必需的**。

V2 必須在 Phase 49.3 建立以下 CI lint rules（強制 fail PR）：

#### Lint Rule 3.1：範疇代碼歸屬檢查
```python
# scripts/lint_category_isolation.py
# 規則：
# 1. agent_harness/orchestrator_loop/** 不可 import agent_harness/tools/**
#    （除非透過明確 ABC 介面）
# 2. governance/** 內所有檔案命名必須含 hitl|risk|audit|compliance
# 3. identity/** 不可被 agent_harness 直接 import（必須透過 middleware）
```

#### Lint Rule 3.2：禁止散落關鍵字
```python
# 禁止以下檔名出現在多個範疇目錄：
FORBIDDEN_SCATTER = ["approval", "risk_check", "audit_log", "permission"]

# 例：
# agent_harness/tools/approval.py     ❌ FAIL（approval 應在 governance/hitl/）
# agent_harness/orchestrator_loop/audit.py  ❌ FAIL
# governance/hitl/approval.py         ✅ OK（唯一歸屬）
```

#### Lint Rule 3.3：禁止 LLM SDK 直接 import
```python
# agent_harness/** 不得：
FORBIDDEN_IMPORTS = [
    "from openai",
    "from anthropic",
    "import openai",
    "import anthropic",
]
```

#### Lint Rule 3.4：禁止裸組 messages
```python
# 禁止 pattern：
PATTERNS = [
    r'messages\s*=\s*\[\s*\{[\'"]role[\'"]',  # messages = [{"role": ...
    # 必須用 PromptBuilder
]
```

**lint scripts 在 Phase 49 Sprint 49.3 建立，CI 整合於 Phase 50 開始強制執行**。

---

## Anti-Pattern 4：Potemkin Features（結構槽位但無內容）

### V1 問題
- `pipeline/steps/step1_memory.py` 跑了，但**實際沒讀 mem0**
- `pipeline/steps/step8_postprocess.py` 名為 "postprocess"，**實為 finalize/persist，無驗證邏輯**
- `risk_assessor/assessor.py` 639 LOC，但主流量沒強制呼叫測試證據

### 症狀
- 模組存在 + 接口完整 + 但**沒有實際邏輯**
- 命名誤導（叫 verifier 但只 save）
- Empty stub 久未補實

### V2 防護
**Definition of Done**：
```markdown
任何範疇實作必須通過：
1. 範疇單元測試（覆蓋核心邏輯）
2. 範疇整合測試（與其他範疇協作）
3. 主流量端到端測試（從 API 到結果）
4. **負面測試**（如果關掉此範疇，會發生什麼？應該有明顯錯誤）

沒過第 4 點 = 是 Potemkin Feature。
```

### 檢查清單
- [ ] 每個功能有「關掉它會壞什麼」的明確答案
- [ ] 測試覆蓋率 ≥ 80%（範疇核心）
- [ ] 命名與行為一致
- [ ] 命名 review：每個 module / class / function 名稱與功能對齊

---

## Anti-Pattern 5：PoC Accumulation

### V1 問題
`integrations/poc/` 目錄持續累積但**很少合併**（agent_team_poc / claude_sdk_tools / orchestrator_tools / real_tools / team_tools / agent_work_loop / shared_task_list / memory_integration）。多數是 1-2 sprint 寫的，3-4 個月後仍在那。

### 症狀
- `poc/` 目錄持續增長
- PoC 結束後沒有「合併或淘汰」決策
- 新 PoC 看起來像「臨時的」但變成永久

### V2 防護
**PoC 生命週期管理**：
```
PoC 從建立到結束最多 2 sprint：
- Sprint X: 建立 + 驗證
- Sprint X+1: 決策（合併到主流量 / 完全刪除）

不合併 = 刪除。沒有「保留以備將來」選項。
```

### 檢查清單
- [ ] PoC 有明確的 hypothesis（要驗證什麼）
- [ ] PoC 有明確的 deadline
- [ ] PoC 結束有 retrospective
- [ ] `experimental/` 目錄定期清理

---

## Anti-Pattern 6：Hybrid Bridge Debt

### V1 問題
`integrations/hybrid/` 是 V1 為了「同時支援 MAF 和 Claude SDK」建的橋接層，**Phase 48 後實質淘汰但代碼仍在**。佔 ~12,000 LOC，至今未刪。

### 症狀
- 為「未來可能的供應商切換」建橋接層
- 但實際只用 1-2 個供應商
- 橋接層複雜度遠超實際需求

### V2 防護
**YAGNI 強制**：
- Adapter 層只支援**當下確定使用**的供應商
- 新供應商實作時再加 adapter
- 禁止「為了未來預留」的抽象

### 檢查清單
- [ ] 任何抽象有當前真實使用案例
- [ ] 沒有「等下個版本可能會用」的代碼
- [ ] 移除 V1 hybrid 思維（一律走 adapter pattern）

---

## Anti-Pattern 7：Context Rot Ignored

### V1 問題
**完全沒有**處理 context rot：
- 沒有 compaction
- 沒有 observation masking
- 沒有 token 預算追蹤
- 10+ turn 對話必劣化

### 症狀
- 長對話品質下降
- LLM 開始忘記前面的指令
- Token 用量無感知

### V2 防護
**範疇 4 是 Day 1 必做**：
- Phase 52 Sprint 1 必須實作 `compactor.py` + `observation_masker.py`
- 範疇 1 Loop 必須在每輪開頭呼叫 compaction check
- 主流量啟用 token 計數 + budget 監控

### 檢查清單
- [ ] Loop 每輪 check 是否需要 compact
- [ ] Token 用量有 metrics
- [ ] 30+ turn 測試案例存在
- [ ] Compaction 有 quality 測試（壓縮後不丟失關鍵資訊）

---

## Anti-Pattern 8：No Centralized PromptBuilder

### V1 問題
Prompt 組裝散在多處：
- `team_agent_adapter.py:66-69` 直接組
- `subagent.py:175-229` 自己組
- `intent_router/llm_classifier/prompts.py` 又自己組
- 沒有統一的 PromptBuilder

### 症狀
- 每個 LLM 呼叫處有自己的 prompt 組裝
- Memory layers 是否真的注入無人保證
- Lost-in-middle 策略缺席

### V2 防護
**PromptBuilder 是唯一入口**：
```python
# ❌ 禁止任何處直接組
messages = [{"role": "system", ...}, ...]

# ✅ 強制走 PromptBuilder
from src.agent_harness.prompt_builder.builder import PromptBuilder
messages = PromptBuilder.build(...)
```

### 檢查清單
- [ ] 主流量 100% 透過 PromptBuilder
- [ ] PromptBuilder 是 singleton 或全局實例
- [ ] Memory layers 真的注入有測試證明
- [ ] Lint rule：禁止裸組 `messages` list

---

## Anti-Pattern 9：No Verification Loop

### V1 問題
Agent 輸出後**完全沒有驗證**：
- `step8_postprocess` 是 finalize 不是驗證
- `claude_sdk/autonomous/verifier.py` 不在主流量
- Agent 給的答案沒人檢查對不對

### 症狀
- LLM 給錯答案直接回給用戶
- 沒有 self-correction
- 沒有 LLM-as-judge

### V2 防護
**範疇 10 主流量強制**：
- 主 agent loop 結束前必須通過 verifier
- 至少 RulesBasedVerifier + LLMJudgeVerifier 各一個
- 失敗自動觸發 self-correction（max 2 次）

### 檢查清單
- [ ] 主流量啟用 verification
- [ ] Verifier 失敗有 audit log
- [ ] Self-correction 有上限
- [ ] Verification 結果在 SSE 事件中可見

---

## Anti-Pattern 10：Mock vs Real Divergence

### V1 問題
V9 分析的 `13-mock-real-map.md` 顯示大量功能：
- 開發環境用 mock
- 主流量用 real
- 但 mock 與 real 邏輯**逐漸分歧**
- Bug 在 dev 不重現，prod 才出現

### 症狀
- 測試用 mock，運行用 real
- Mock 簡化了關鍵 edge case
- Mock 與 real 的 API 不完全一致

### V2 防護
**Mock 紀律**：
1. Mock 必須與 real 共用 ABC（同 interface）
2. Mock 必須在每個 Sprint 結束跑一次「mock vs real」對比測試
3. 主流量測試**必須跑 real**（除非外部 API 限制）
4. CI 跑兩遍：一次 mock 環境，一次 real 環境

### 檢查清單
- [ ] Mock 與 real 透過同一 ABC
- [ ] CI 跑兩種環境
- [ ] 範疇驗收必須通過 real 環境
- [ ] Mock 不簡化關鍵 edge case（特別是錯誤處理）

---

---

## Anti-Pattern 11：命名版本後綴遺留（新增）

### V1 證據
- `hybrid/orchestrator_v2.py`（v2 後綴留在代碼）
- `step8_postprocess.py` 名為 postprocess 實為 finalize/persist
- `OrchestratorPipeline` 命名為 pipeline 但聲稱是 loop

### 症狀
- 檔名 / class 名 / function 名出現 `_v1`、`_v2`、`_old`、`_new`、`_legacy` 後綴
- 命名與實際行為不符（如 `verifier` 內無驗證邏輯、`postprocess` 不是後處理）
- 重命名遺漏（refactor 後舊名仍在）

### V2 防護

#### Rule 11.1：禁止版本後綴
```python
FORBIDDEN_SUFFIXES = ["_v1", "_v2", "_v3", "_old", "_new", "_legacy", "_tmp"]
# CI 掃描所有檔名 / class 名 / function 名
```

#### Rule 11.2：命名行為驗證
PR review checklist：
- [ ] 該 module 名稱反映實際做的事？
- [ ] 該 class 名稱反映其職責？
- [ ] 該 function 名稱與其行為一致？

#### Rule 11.3：Refactor 完整性
任何重命名必須：
- 全 codebase grep 確認無遺漏
- 包含 docs / tests / config 的引用都更新
- 不留 alias / backwards compat 名稱（除非有明確 deprecation 計畫）

### 檢查清單
- [ ] 沒有版本後綴檔案
- [ ] 命名與行為一致（lint 檢查 module docstring vs 實際 import）
- [ ] Refactor 完整無遺漏

---

## V2 PR 範本（Pull Request Template）

```markdown
## 變更說明
（簡述）

## 範疇歸屬
此 PR 屬於：
- [ ] 範疇 1: Orchestrator Loop
- [ ] 範疇 2: Tool Layer
- [ ] 範疇 3: Memory
- [ ] 範疇 4: Context Management
- [ ] 範疇 5: Prompt Construction
- [ ] 範疇 6: Output Parsing
- [ ] 範疇 7: State Management
- [ ] 範疇 8: Error Handling
- [ ] 範疇 9: Guardrails & Safety
- [ ] 範疇 10: Verification Loops
- [ ] 範疇 11: Subagent Orchestration
- [ ] 跨範疇基礎設施（platform / adapters / infrastructure / business_domain）

## Anti-Pattern 自檢
- [ ] AP-1: 不是 Pipeline 偽裝 Loop
- [ ] AP-2: 不是 side-track（從 api/ 可追蹤）
- [ ] AP-3: 不跨目錄散落
- [ ] AP-4: 不是 Potemkin（有實際邏輯 + 負面測試）
- [ ] AP-5: 不是無計畫的 PoC
- [ ] AP-6: 沒有「為未來預留」抽象
- [ ] AP-7: 處理 context rot（如適用）
- [ ] AP-8: 透過 PromptBuilder（如有 LLM 呼叫）
- [ ] AP-9: 有 verification（如為輸出產生點）
- [ ] AP-10: Mock 與 real 同 ABC

## 測試
- [ ] 單元測試覆蓋率 ≥ 80%
- [ ] 整合測試
- [ ] 主流量 e2e 測試（如適用）
- [ ] 負面測試（關掉此功能會壞什麼）

## 範疇成熟度
此 PR 將該範疇從 Level X 推進到 Level Y。
（附上 Level 評分依據）
```

---

## 每 Sprint 結束的 Anti-Pattern Audit

```markdown
Sprint XXX Anti-Pattern Audit
- AP-1 違反次數：__
- AP-2 違反次數：__
- ...
- AP-10 違反次數：__

Action items:
- ...
```

---

## 下一步

確認 anti-patterns 後：
- `05-reference-strategy.md`：參考資料策略
- `06-phase-roadmap.md`：詳細 Sprint 規劃
