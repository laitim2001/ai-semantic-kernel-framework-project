# V2 Audit — 完整總圖（單頁 onboarding）

**Last updated**: 2026-05-01 evening
**Status**: 4 audit windows complete (W1, W2, W3, mini-W4-pre); 45% coverage; 8 P0 open; 1 cleanup sprint pending; W4 not yet triggered
**Authoritative index**: `V2-AUDIT-OPEN-ISSUES-20260501.md`（this doc 是縮版）

---

## 1. 為什麼有 V2 Audit

V1 的災難根源不只是「代碼寫錯」，而是「**audit / review / retrospective 寫了沒人看 → 同樣錯誤反覆出現**」。V2 從 Phase 49 開始（2026-04），由獨立 audit session 對 dev session 已完成的 sprint 做交叉驗證，目標：

1. 確認**對齐 18 份 V2 規劃文件**的設計理念
2. 確認**對齊整個 agent harness framework**的架構方向
3. 確認**實作的功能真實可執行**（不是「以為可以」、不是自欺測試、不是 Potemkin Feature）

權威排序：`agent-harness-planning/` 18 份規劃 > 本 audit findings > `.claude/rules/` > 既有代碼。

---

## 2. Scope + Coverage

V2 規劃 22 sprints（49.1 → 55.x）。已 audit：

```
Phase 49 ████████████████████ 100% (49.1/49.2/49.3/49.4 完整)
Phase 50 ████████████████████ 100% (50.1/50.2 完整)
Phase 51 ████████████████████ 100% (51.0/51.1/51.2 完整)
Phase 52 ░░░░░░░░░░░░░░░░░░░░   0% (52.1 完成未審 / 52.2 進行中)
Phase 53 ░░░░░░░░░░░░░░░░░░░░   0% (未開始)
Phase 54 ░░░░░░░░░░░░░░░░░░░░   0%
Phase 55 ░░░░░░░░░░░░░░░░░░░░   0%

共 9/22 完整 sprint = 約 45% 覆蓋率
```

未審：52.1（已完成）+ 52.2 Day 1-3（進行中）+ Phase 53-55（未開始）

---

## 3. 4 輪 Audit 結果摘要

| 輪 | 日期 | 範圍 | 結論 |
|----|------|------|------|
| W1 | 2026-04-29 | 49.1/49.2/49.3 + 49.4 Day 1-2 | ✅✅✅⚠️（W1-3 hash chain 缺 verify 程式）|
| W2 | 2026-04-29 | 49.4 Day 1-2 詳細（Adapter + Worker）| ✅⚠️（Worker 決策好、依賴髒）|
| W3 | 2026-05-01 | Carryover + 50.1 + 50.2 | ❌✅🟡（W3-0 process drift / 50.2 multi-tenant 鐵律違反）|
| mini-W4-pre | 2026-05-01 evening | 49.4 Day 3-5 + 51.0 + 51.1 + 51.2 | ⚠️✅🟡⚠️（揭露系統性 AP-4 pattern + 51.1 Windows sandbox 災難）|

**最有價值的發現**（mini-W4-pre）：
**「ABC Potemkin / Main Flow Integration Gap」** — AP-4 Potemkin 變體
- 每 sprint 自驗 ABC ✅，跨 sprint 主流量整合 ❌
- 3 案例：W3-2 50.2 chat router / W4P-1 49.4 Day 3 OTel / W4P-4 51.2 memory tools

---

## 4. Open P0/P1 速覽

### 8 P0（cleanup sprint 必清，Phase 53.x 阻塞）

| # | Title | Effort |
|---|-------|--------|
| #11 | chat router multi-tenant 隔離 | 1-2d |
| #12 | TraceContext propagation at chat handler | half day |
| #13 | audit_log hash chain verifier | 2-3d |
| #14 | JWT replace X-Tenant-Id header | 1-2d |
| #15 | OTel SDK version lock to ==1.22.0 | 30 min |
| #16 | OTel main-flow tracer span coverage 5 places | 2-3d |
| #17 | SubprocessSandbox Windows Docker isolation | 3-5d |
| #18 | memory_tools handler tenant from ExecutionContext | 1d |

**總工時**: 12-17 days → 推薦 **10-14 day cleanup sprint**

### 6 P1 待清（cleanup sprint Day 6）

W2-1 #4 / W2-2 #6 / W2-2 #7 / W2-2 #8 / W3-1 LoopState / W3-1 ToolCallExecuted owner

### 2 P1 已清（PR #10 merge 後）

W1-2 #3 stub 刪除 / W2-1 #5 CI lint scope（commit ab0d727d / d3070e12）

---

## 5. Process Fixes（防 W3-0 process drift 重演）

| # | Fix | 狀態 |
|---|-----|------|
| 1 | Sprint plan template 加 Audit Carryover | ✅ |
| 2 | Retrospective template 加 Audit Debt | ✅ |
| 3 | GitHub issue per P0/P1 | ✅（#11-18）|
| 4 | 每月 Audit Status Review | ⏳（next 2026-06-01）|
| 5 | Audit re-verify 每 2-3 sprint | ⏳（W4 待 cleanup 完）|
| 6 | Sprint retrospective 必答主流量整合驗收 | ⏳ Proposed |

---

## 6. 文件導航（21 份 audit 報告 + 1 cleanup template + 1 index + 1 onepage）

### 決策性報告（讀這 4 份就夠了）
- `V2-AUDIT-WEEK1-SUMMARY.md`
- `V2-AUDIT-WEEK2-SUMMARY.md`
- `V2-AUDIT-WEEK3-SUMMARY.md`（雙層問題：50.2 偏離 + W3-0 process drift）
- `V2-AUDIT-MINI-W4-PRE-SUMMARY.md`（系統性 AP-4 pattern）

### 詳細證據（要查 specific finding 才讀）
- W1: `V2-AUDIT-W1-{CONTRACTS,RLS,AUDIT-HASH,ORM-LOCK}.md`（4 份）
- W2: `V2-AUDIT-W2-{ADAPTER,WORKER}.md`（2 份）
- W3: `V2-AUDIT-W3-{0-CARRYOVER,1-PHASE50-1,2-PHASE50-2}.md`（3 份）
- W4P: `V2-AUDIT-W4P-{1-PHASE49-4-D3-5,2-PHASE51-0,3-PHASE51-1,4-PHASE51-2}.md`（4 份）
- Baseline: `V2-AUDIT-BASELINE-20260429.md`

### 工具
- `V2-AUDIT-CLEANUP-SPRINT-TEMPLATE.md` — cleanup session 客製模板
- `V2-AUDIT-OPEN-ISSUES-20260501.md` — 單一真相 index
- `V2-AUDIT-OVERVIEW-ONEPAGE.md` — **本文件**

---

## 7. 接下來的工作（pending）

### 🔴 Cleanup Sprint — 完全未啟動

**等 user 開新 cleanup session** + 採用 cleanup template 執行 8 P0。

預計 10-14 days，Phase 53.1 啟動前必清完。

### 🟡 主 session 52.2 — Day 1-3 已 ship 未審

Day 2 Memory + Cache wiring 是 W4P-4 留下的風險區，未確認是否守住「PromptBuilder 直接呼叫 memory store ABC，不走 memory_tools handler」紀律。

### 🟢 W4 Audit — 觸發條件未滿足

需 8 P0 全 close + 4 P1 全清 + cleanup sprint done + 52.2 done 才啟動。預估 6-8 小時。

---

## 8. 給未來 onboarding 的 1 句話

> V2 是 4 輪 audit / 21 份報告 / 8 open P0 / 1 個系統性 AP-4 pattern 警告 / 6 process fixes（4 done）的綜合工程治理產物。讀 4 份 SUMMARY 就掌握全貌；要修 P0 看 8 個 GitHub issues + cleanup template；要懂 V1 災難為何在 V2 早期重演看 W3-0 + mini-W4-pre §3 systematic pattern。

---

**維護紀律**：
- 此頁面在每輪 audit 結束時 audit session 更新
- 任何 P0 close → 也更新 OPEN-ISSUES doc
- W4 完成後此頁面升級為「V2 Audit Cycle 1 Complete」（含 cleanup 結果 + 52.x 結果）
