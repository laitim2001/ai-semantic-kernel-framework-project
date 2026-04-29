# SITUATION V2 — Compact Summary Prompt（V2 重構期間 /compact 用）

> **用法**：當需要 `/compact` session 時，把以下整份 prompt 貼到 `/compact` 後。比通用 compact 多 5 個 V2 紀律檢查項；字數限制放寬到 **1500 字**（中文）。
>
> **適用範圍**：Phase 49+（V2 重構期間）。非 V2 工作（如 KB worktree research）仍用原本 800 字版本即可。

---

## /compact prompt（複製以下整段給 AI 助手）

```
/compact

# IPA Platform V2 — Session Compact Summary

請以以下格式總結本 session，控制在 1500 字（中文）以內。

## 0. Session 座標（必填）

- 當前 Sprint: __ (例：49.2 Day 3 進行中 / 49.1 已收尾)
- 當前 branch: __ (auto-detect via `git branch --show-current`)
- Working tree: __ (auto-detect via `git status --short`)
- Phase 進度: __ / 22 sprint 完成

## 1. 本次 session 主要任務（一句話）

___

## 2. 已完成項目（按 V2 sprint workflow 順序）

### 🟢 Plan + Checklist（如本 session 啟動了新 sprint）

- [ ] `phase-XX-foundation/sprint-XX-Y-plan.md`（建立 / 更新 — Story Points、deliverables 數）
- [ ] `phase-XX-foundation/sprint-XX-Y-checklist.md`（建立 / 更新 — task 數）

### 🟢 Code 變更

- 新建：__ files（含範疇歸屬，例：`agent_harness/_contracts/X.py` Cat-cross / `adapters/_base/Y.py`）
- 修改：__ files（簡述改動）
- 刪除：__ files（原因）

### 🟢 文件變更

- progress.md（Day X 區段已加）
- retrospective.md（如為 sprint 收尾日）
- sprint-XX-Y-checklist.md（X 項從 [ ] → [x]，Y 項標記 🚧 延後）

### 🟢 測試 / 品質狀態

- `pytest`: __ passed / __ failed / __ skipped
- `mypy --strict`: __ errors（V2 要求 0）
- `black --check`、`isort --check`、`flake8`: ✅ / ❌
- `npm run lint` / `npm run build`: ✅ / ❌
- LLM SDK leak check（grep agent_harness/）: ✅ clean / ❌ leaked

## 3. V2 紀律檢查（每項必表態 ✅ / ⚠️ / ❌ / N/A）

| 項目 | 狀態 | 說明 |
|------|------|------|
| 原則 1 Server-Side First（無本地 fs / 多租戶安全）| __ | __ |
| 原則 2 LLM Provider Neutrality（agent_harness 無 SDK import）| __ | __ |
| 原則 3 CC Reference 不照搬 | __ | __ |
| 17.md Single-source（跨範疇型別從 `_contracts/` import）| __ | __ |
| 11+1 範疇歸屬（無跨範疇散落）| __ | __ |
| 04-anti-patterns 11 條 | __ | 違反項：__ |
| Sprint workflow（plan→checklist→code→update→progress）| __ | __ |
| File header convention（新檔有 Category/Scope/History）| __ | __ |
| Multi-tenant rule（新業務 table/endpoint 含 tenant_id）| N/A 此 session | __ |

## 4. 進行中 / 未完成

- **停留位置**：Sprint X.Y Day Z 步驟 N
- **阻塞**：__（含已嘗試的 workaround）
- **延後項 🚧**：__（含理由 + 何時補；per checklist sacred rule，**不可刪除未勾選項**，只能標 🚧）

## 5. 關鍵決策

- **設計決策**：__（對齐 17.md owner 表 / 04 anti-patterns / 10 server-side）
- **命名 / 路徑變更**：__（例：platform → platform_layer 因 stdlib shadow）
- **延後決策**（rolling planning）：__（例：49.3 plan 待 49.2 收尾再寫）

## 6. Commit 列表（每 commit 對應 sprint checklist 哪一項）

```
<short-hash> <type>(<scope>, sprint-XX-Y): <subject>
  → 對應 checklist 第 X.Y.Z 項
```

## 7. 下一步

- **接手第一件事（next session）**：__
- **本 sprint 仍剩**：__ days / __ tasks（從 checklist 數 [ ] 項）
- **下個 sprint plan 狀態**：（V2 滾動規劃）
  - 若當前 sprint 仍進行中 → **不應寫**下個 sprint plan
  - 若當前 sprint 收尾 → 才寫 sprint X.(Y+1) plan + checklist
- **Open items（從 retrospective.md / 🚧 延後項）**：__

## 8. ⚠️ Rolling Planning 紀律提醒（V2 核心）

請確認本 session 沒有違反 rolling planning：

- [ ] 沒預寫多個未來 sprint plan + checklist
- [ ] 沒跳過 plan / checklist 直接 code
- [ ] 沒刪除未勾選的 [ ] 項目
- [ ] 沒在 retrospective.md 寫「將會做」的具體 task（具體 task 屬下個 sprint plan）

如有違反，在此節說明 + 復原方案。

---

字數控制：≤ 1500 字（中文）。較舊版 800 字 budget 多 700 字，因 V2 紀律檢查項多。如必要可以再略增至 2000 字（極端 sprint 收尾日含大量驗收結果時）。

```

---

## 比較：通用 compact vs V2 compact

| 項目 | 通用 compact（原本）| V2 compact（本檔）|
|------|------------------|------------------|
| 字數 | 800 字 | 1500 字 |
| Sprint 座標 | ❌ | ✅ Section 0 |
| 3 大原則合規 | ❌ | ✅ Section 3 |
| 11 anti-patterns 抽查 | ❌ | ✅ Section 3 |
| 17.md Single-source 檢查 | ❌ | ✅ Section 3 |
| File header convention | ❌ | ✅ Section 3 |
| Multi-tenant rule | ❌ | ✅ Section 3 |
| 🚧 延後項追蹤 | ❌ 隱含 | ✅ Section 4 + sacred rule 提醒 |
| Rolling planning 紀律 | ❌ | ✅ Section 8 |
| Commit ↔ checklist mapping | ❌ | ✅ Section 6 |

---

## 何時用通用 compact、何時用 V2 compact

| 場景 | 用哪個 |
|------|-------|
| V2 sprint 期間（Phase 49-55）| **V2 compact**（本檔） |
| V2 retrospective day（sprint 收尾） | **V2 compact** + 額外貼 retrospective.md 內容 |
| 非 V2 工作（KB worktree / V1 archive 探索 / 一次性 docs） | 通用 compact 即可 |
| 緊急 token 壓力（context > 90%） | **通用 compact**（800 字較省）|

---

## 維護

- 與 `SITUATION-V2-SESSION-START.md` 配套使用
- V2 規劃文件大改（17.md / 04 / 10）時，第 3 節「V2 紀律檢查」對應更新
- Phase 切換（49 → 50）時不需改本檔（內容是 V2 通用）
- V2 完成（Phase 55）後退役 → 改用 V3 / SaaS Stage 1 對應 compact

---

**Last Updated**: 2026-04-29（Sprint 49.1 後）
**Maintainer**: 用戶 + AI 助手共同維護
**File location**: `claudedocs/6-ai-assistant/prompts/SITUATION-V2-COMPACT.md`
**Companion**: `SITUATION-V2-SESSION-START.md`（每個新 session 開頭用）
