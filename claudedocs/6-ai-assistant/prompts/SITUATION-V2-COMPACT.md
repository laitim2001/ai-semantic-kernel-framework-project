# SITUATION V2 — Compact Summary Prompt（V2 重構期間 /compact 用）

> **用法**：直接 copy「複製貼上區」這一節到 Claude Code 對話框送出即可。下方「設計說明」是給維護者看的背景，**不需要每次貼**。
>
> **適用範圍**：Phase 49+（V2 重構期間）。非 V2 工作（如 KB worktree research）仍用原本 800 字版本即可。

---

## ✂️ 複製貼上區（直接送出，無需修改）

```
/compact

## V2 Compact 格式（≤1500 字，中文）

### 0. Sprint 座標
Sprint X.Y / Day Z / Phase 累計 N/22 / Branch / Working tree 狀態

### 1. 本次主要任務（一句話）

### 2. 已完成（按 V2 sprint workflow 順序）
- Plan/Checklist 變更（路徑、新建/更新）
- Code 變更：新建/修改/刪除（含範疇歸屬）
- 文件：progress.md / retrospective.md / checklist 勾選 X 項
- 測試:pytest / mypy strict / lint / build / LLM SDK leak

### 3. V2 紀律 9 項（每項 ✅/⚠️/❌/N/A）
1. Server-Side First   2. LLM Provider Neutrality   3. CC Reference 不照搬
4. 17.md Single-source   5. 11+1 範疇歸屬   6. 04 anti-patterns
7. Sprint workflow（plan→checklist→code）   8. File header convention   9. Multi-tenant rule

### 4. 進行中 / 阻塞 / 🚧 延後項
（per CLAUDE.md sacred rule:不可刪 unchecked，必須標 🚧 + 理由）

### 5. 關鍵決策
- 設計 / 命名變更 / 延後決策（rolling planning）

### 6. Commit ↔ Sprint checklist mapping

### 7. 下一步
- Next session 第 1 件事
- 本 sprint 剩 X days / Y tasks
- 下個 sprint plan 狀態（rolling:當前 sprint 收尾才寫，禁止預寫）
- Open items（從 retrospective.md / 🚧 延後項）

### 8. Rolling Planning 紀律自檢
☐ 沒預寫多個未來 sprint plan
☐ 沒跳過 plan/checklist 直接 code
☐ 沒刪除未勾選的 [ ] 項目
☐ 沒在 retrospective.md 寫具體未來 sprint task
```

> **就這樣 — 上方代碼塊整段 copy 後送出即可。** 下方都是背景說明，不必每次貼。

---

## 為什麼比通用 compact 多 5 項

通用 800 字 compact 不檢查 V2 紀律。V2 重構期間，下列違反是**直接 PR revert 級**問題，必須每次 compact 強制驗證：

1. **Sprint 座標**（§0）— rolling planning 必要前提
2. **3 大原則合規**（§3 #1-3）— LLM SDK leak = revert
3. **17.md Single-source**（§3 #4）— 跨範疇型別重複定義 = 全範疇連鎖污染
4. **11 條 anti-patterns**（§3 #6）— V1 教訓不可重蹈
5. **Rolling planning 自檢**（§8）— 防 AI 在 compact 中順手「規劃未來 sprint」

---

## 何時用 V2 compact、何時用通用 compact

| 場景 | 用哪個 |
|------|-------|
| V2 sprint 期間（Phase 49-55）| **V2 compact**（本檔上方代碼塊）|
| V2 retrospective day（sprint 收尾）| V2 compact + 額外 paste retrospective.md 內容 |
| 非 V2 工作（KB worktree / V1 explore / 一次性 docs）| 通用 800 字 compact |
| 緊急 token 壓力（context > 90%）| 通用 800 字 compact（省 700 字 budget）|

---

## 比較：通用 compact vs V2 compact

| 項目 | 通用 compact（你既有的）| V2 compact（本檔）|
|------|----------------------|------------------|
| 字數 | 800 字 | 1500 字 |
| Sprint 座標 | ❌ | ✅ §0 |
| 3 大原則合規 | ❌ | ✅ §3 #1-3 |
| 11 anti-patterns 抽查 | ❌ | ✅ §3 #6 |
| 17.md Single-source 檢查 | ❌ | ✅ §3 #4 |
| File header convention | ❌ | ✅ §3 #8 |
| Multi-tenant rule | ❌ | ✅ §3 #9 |
| 🚧 延後項追蹤 | ❌ 隱含 | ✅ §4 + sacred rule 提醒 |
| Rolling planning 紀律 | ❌ | ✅ §8 |
| Commit ↔ checklist mapping | ❌ | ✅ §6 |

---

## 維護

- 與 `SITUATION-V2-SESSION-START.md` 配套使用（一個 session 開頭、一個 session 結尾）
- V2 規劃文件大改（17.md / 04 / 10）時，§3「V2 紀律檢查 9 項」對應更新
- Phase 切換（49 → 50）時不需改本檔（內容是 V2 通用）
- V2 完成（Phase 55）後退役 → 改用 V3 / SaaS Stage 1 對應 compact

---

**Last Updated**: 2026-04-29（Sprint 49.1 後重構為「短版上+說明下」結構）
**Maintainer**: 用戶 + AI 助手共同維護
**File location**: `claudedocs/6-ai-assistant/prompts/SITUATION-V2-COMPACT.md`
**Companion**: `SITUATION-V2-SESSION-START.md`（每個新 session 開頭用）
