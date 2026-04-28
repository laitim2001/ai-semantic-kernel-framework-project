# 反模式檢查清單（PR 必通）

**Purpose**: V1 教訓 11 條反模式；每個 PR merge 前必須能對下列全部回答 ✅ 或 N/A。

**Category**: Framework / Development Process
**Created**: 2026-04-28
**Last Modified**: 2026-04-28
**Status**: Active

**Modification History**:
- 2026-04-28: Initial creation from 04-anti-patterns.md

---

## 使用方法

**提交 PR 前的自檢**：對照下列 11 條，逐一填寫 ✅（通過）/ ❌（未通過）/ N/A（不適用）。

如有 ❌，必須修正後才能 merge。Reviewer 將此清單作為**強制 code review 項**。

---

## Anti-Pattern 1：Pipeline 偽裝成 Loop

**症狀**：代碼用 `for step in steps:` 線性執行固定步數，包裝成 loop 外殼，但工具結果不回注 LLM。

**自我檢查問題**：
- 此 PR 內是否有 `for step in …:` 的順序執行？
- 若有，工具結果是否用 `user message` 形式 append 回 messages 讓 LLM 重新推理？
- 是否有 `while True:` 由 stop_reason 驅動退出，還是固定次數迴圈？

**❌ 反面範例**：
```python
class OrchestrationPipeline:
    async def run(self, ctx):
        for step in [step1, step2, step3]:  # ← 固定 3 步
            await step.execute(ctx)
        return ctx  # 沒有回注，工具結果死在 step 內
```

**✅ 正面範例**：
```python
class AgentLoop:
    async def run(self, state: LoopState):
        while True:  # ← while 驅動
            response = await self.llm_client.chat(state.messages, ...)
            if response.stop_reason == StopReason.END_TURN:
                return response
            for tc in response.tool_calls:
                result = await self.tool_executor.execute(tc)
                state.messages.append(Message(role="tool", content=result))
```

**修補建議**：
- 改 `for` 為 `while True`
- 在 Loop 末尾檢查 stop_reason 決定是否繼續
- 工具結果以 Message 形式回注 state.messages

---

## Anti-Pattern 2：Side-Track Code Pollution

**症狀**：代碼存在但主流量無人呼叫；模組標 "PoC" / "Experimental" 但久不淘汰；多個版本並存（_v1 / _v2）。

**自我檢查問題**：
- 新代碼能從 `api/v1/` 或主入點追蹤到呼叫嗎？
- 若是 PoC，是否有明確的 deadline（≤ 2 sprint）？
- 是否有 `_v1`, `_v2`, `_old`, `_new` 後綴的多版本？

**修補建議**：
- 主流量代碼必須能從 API 進入點追蹤
- PoC 放 `experimental/` 目錄（不在 src）
- 每月檢查無人使用的代碼，逾期刪除
- 禁止多版本並存；重命名完整後刪舊版

---

## Anti-Pattern 3：Cross-Directory Scattering

**症狀**：同一範疇代碼分布超過 2 個目錄；跨目錄相互不知對方存在；重複實作。

**自我檢查問題**：
- 此 PR 涉及的功能集中在一個目錄嗎？
- 還是散落在 `tools/`, `orchestrator_loop/`, `guardrails/` 多個地方？
- 該功能的 dataclass / ABC 是否有重複定義？

**修補建議**：
- 每個範疇代碼集中於 `agent_harness/<范疇>/` 單一目錄
- 跨範疇共用邏輯放對應 cross-cutting 目錄（governance / identity / observability）
- 代碼評審時須檢查 `tools/` 中是否有不屬於 Tool 的邏輯

---

## Anti-Pattern 4：Potemkin Features（結構槽位但無內容）

**症狀**：模組存在 + 接口完整，但沒有實際邏輯；命名誤導（叫 verifier 但只 save）；empty stub 久未補。

**自我檢查問題**：
- 若此功能被關掉，會發生什麼錯誤？能明確回答嗎？
- 單元測試覆蓋率 ≥ 80%？
- 命名與行為一致嗎（e.g., verifier 真的在驗證）？

**修補建議**：
- Definition of Done：主流量 e2e 測試 + 負面測試（關掉會壞什麼）
- 測試覆蓋率 ≥ 80%
- Naming review：module / class / function 名稱是否與功能對齊

---

## Anti-Pattern 5：PoC Accumulation

**症狀**：`experimental/` 目錄持續累積但很少合併；多個 PoC 結束無「合併或淘汰」決策；新 PoC 變成永久代碼。

**自我檢查問題**：
- 若此 PR 是 PoC，是否有明確的 hypothesis（要驗證什麼）？
- 是否有明確的 deadline（≤ 2 sprint）？
- PoC 結束後是否有決策文件（合併 / 刪除）？

**修補建議**：
- PoC 最多 2 sprint，結束時必須決定合併或刪除
- 不合併 = 刪除；沒有「保留以備將來」
- 每月檢查 experimental 目錄清理

---

## Anti-Pattern 6：Hybrid Bridge Debt

**症狀**：為「未來可能的供應商切換」建橋接層，但實際只用 1-2 個；橋接層複雜度遠超實際需求。

**自我檢查問題**：
- 此 PR 中的抽象有當前**真實使用案例**嗎？
- 還是「為了將來可能」預留的？
- 有沒有「等下個版本可能會用」的代碼？

**修補建議**：
- YAGNI：只支援當下確定使用的供應商
- 新供應商實作時再加 adapter
- 禁止「為了未來預留」的抽象層

---

## Anti-Pattern 7：Context Rot Ignored

**症狀**：沒有 compaction / observation masking / token 預算追蹤；10+ turn 對話必劣化。

**自我檢查問題**：
- Loop 是否在每輪開頭檢查是否需要 compact？
- Token 用量有 metrics / monitoring 嗎？
- 是否有 30+ turn 測試案例？
- Compaction 有品質測試（壓縮後不丟失關鍵資訊）？

**修補建議**：
- 範疇 4 Context Management 是 Phase 52.1 Day 1 必做
- Loop 每輪呼叫 compactor.compact_if_needed(state)
- Token 計數 + budget 監控必須主流量啟用
- 長對話測試（30+ turn）納入驗收

---

## Anti-Pattern 8：No Centralized PromptBuilder

**症狀**：Prompt 組裝散在多處；每個 LLM 呼叫處有自己的 prompt 組裝；memory layers 是否真的注入無人保證。

**自我檢查問題**：
- 此 PR 中所有 LLM 呼叫是否都透過 PromptBuilder？
- 有沒有地方裸組 `messages = [{"role": "system", ...}, ...]`？
- Memory layers 是否真的被注入有測試證明？

**修補建議**：
- PromptBuilder 是**唯一入口**
- Lint rule：禁止裸組 messages list
- PromptBuilder 必須注入所有 memory layers，有單元測試驗證

---

## Anti-Pattern 9：No Verification Loop

**症狀**：Agent 輸出後完全沒有驗證；沒有 self-correction；LLM 給的答案沒人檢查對不對。

**自我檢查問題**：
- 此 PR 若涉及 agent 輸出，是否有驗證步驟？
- Verifier 失敗後是否自動觸發 self-correction（最多 N 次）？
- Verification 結果是否在 SSE 事件 / 日誌中可見？

**修補建議**：
- 主 agent loop 結束前必須通過 verifier
- 至少 RulesBasedVerifier + LLMJudgeVerifier 各一個
- 失敗自動觸發 self-correction（max 2 次）
- Verification 結果有 audit log

---

## Anti-Pattern 10：Mock vs Real Divergence

**症狀**：開發環境用 mock，主流量用 real，但 mock 與 real 邏輯逐漸分歧；bug 在 dev 不重現，prod 才出現。

**自我檢查問題**：
- Mock 與 real 是否透過同一 ABC？
- CI 是否跑兩遍：mock 環境 + real 環境？
- Mock 是否簡化了關鍵 edge case（特別是錯誤處理）？

**修補建議**：
- Mock 與 real 共用 ABC（同 interface）
- CI 跑兩種環境驗證
- 範疇驗收必須通過 real 環境
- Mock 不簡化關鍵 edge case

---

## Anti-Pattern 11：命名版本後綴遺留

**症狀**：檔名 / class 名 / function 名出現 `_v1`, `_v2`, `_old`, `_new`, `_legacy` 後綴；命名與實際行為不符；重命名遺漏。

**自我檢查問題**：
- 此 PR 中有沒有 `_v1`, `_v2`, `_old` 等後綴的檔案 / class？
- 命名是否反映實際做的事（e.g., verifier 真的在驗證，postprocess 真的在後處理）？
- Refactor 時是否用 grep 確認全 codebase 無遺漏？

**修補建議**：
- 禁止版本後綴；若要重命名，完整 refactor + grep 確認無遺漏
- 命名 review：module 名稱是否反映功能、class 名稱反映職責
- 不留 alias / backwards compat 名稱（除非有明確 deprecation 計畫）

---

## PR Template（插入到 `.github/PULL_REQUEST_TEMPLATE.md`）

```markdown
## Anti-Pattern Checklist

每個 PR 必須對下列項回答 ✅（通過）/ ❌（未通過）/ N/A（不適用）：

- [ ] ✅ AP-1: 不是 Pipeline 偽裝 Loop（若有 LLM 呼叫）
- [ ] ✅ AP-2: 不是 side-track（從 api/ 可追蹤主流量）
- [ ] ✅ AP-3: 不跨目錄散落（同功能集中一處）
- [ ] ✅ AP-4: 不是 Potemkin（有實際邏輯 + 負面測試）
- [ ] ✅ AP-5: 不是無計畫 PoC（有 deadline + 決策）
- [ ] ✅ AP-6: 沒有「為未來預留」抽象（真實使用案例）
- [ ] ✅ AP-7: 處理 context rot（若涉及長對話）
- [ ] ✅ AP-8: 透過 PromptBuilder（若有 LLM 呼叫）
- [ ] ✅ AP-9: 有 verification（若為輸出產生點）
- [ ] ✅ AP-10: Mock 與 real 同 ABC（若涉及測試）
- [ ] ✅ AP-11: 無版本後綴 + 命名一致

## 若有 ❌

請在下方說明為何不適用或如何修正：
```

---

## 每 Sprint 結束的反模式審計

```markdown
### Sprint XXX Anti-Pattern Audit

- AP-1 違反次數：__
- AP-2 違反次數：__
- ... (AP-11)
- **總違反次數：__**

**Action Items**：
- ...
```

---

## 引用

- **04-anti-patterns.md** — V1 教訓完整論述與反面範例
- **CLAUDE.md** — §Anti-Pattern 檢查原則 / §Developer Preferences
- **category-boundaries.md** — AP-3 Cross-Directory Scattering 詳細規則
- **llm-provider-neutrality.md** — AP-2 / AP-6 相關強制規則

---

**維護責任**：Code reviewer 為 PR 自檢官；Scrum Master 於 Sprint 結束審計違反情況。
