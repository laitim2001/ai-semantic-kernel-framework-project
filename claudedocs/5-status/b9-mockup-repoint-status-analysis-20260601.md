# B-9 深度分析:Mockup re-point 真實狀態(盤點前提已過時)

**Purpose**: 釐清 B 區優化項 B-9(Mockup re-point ~13 頁)的真實狀態。**重大校正:B-9 的前提「僅 overview 過 + ~13 頁待重建」已過時。** 實測 CI gate + drift audit 顯示 Phase-2 epic 已於 Sprint 57.40-57.45 全清(22/22 PARITY)。真正剩餘的不是「~13 頁待重建」,而是 (i) 14 個 PROP stub 待「promote→re-point」+ (ii) 4 個未追蹤的二階債(baseline 未下修 / shell 層未比對 / 無 per-page 視覺 CI / 5 頁無專屬 mockup)。本檔為 research 分析(非 sprint plan,守 rolling 紀律)。
**Category**: Frontend / Mockup-Fidelity — status reconciliation
**Scope**: B 區優化分析 / B-9
**Created**: 2026-06-01
**Status**: Active(analysis)

**Modification History (newest-first)**:
- 2026-06-01: Initial creation — B-9 真實狀態(Explore 蒐證 + 主 session 親跑 CI gate + 親驗 audit verdict)

**Related**:
- `integration-progress-20260531.md` §B-9(其前提已被本檔校正)
- `drift-audit-2026-05-25/audit-report.md`(22/22 PARITY 權威)
- `v2-investigation-20260522/02-frontend-status.md` + `03-mockup-consistency-rootcause.md`(舊狀態 + 根因)
- `docs/rules-on-demand/frontend-mockup-fidelity.md`(4-layer 協定 + 7 鐵律 + DoD)
- `frontend/scripts/check-mockup-fidelity.mjs`(CI gate)

---

## 0. 一句話結論

> **B-9 的「~13 頁待重建」前提已過時。** 親跑 CI gate 通過(byte-identical CSS + 48/48 baseline)、drift audit(2026-05-25)記載 **5 個 CATASTROPHIC 已於 Sprint 57.40-57.45 逐一重建 → 22/22 active 頁 PARITY**。真正剩餘的 B-9 工作**不是**重建已 drift 的頁,而是:① 14 個 PROP stub 的「promote→re-point」(每個是獨立 feature sprint,非 re-point)② 4 條未追蹤二階債(見 §4)。

---

## 1. 為何前提過時:盤點引用了 2026-05-22 的舊快照

| 來源 | 日期 | 說法 | 狀態 |
|------|------|------|------|
| `02-frontend-status.md:19,168` | **2026-05-22** | 「真正 parity ≈ 10 頁;只有 overview 經 Playwright 視覺驗證;~25+ P0 路由仍 drift」 | ⚠️ 舊快照 |
| `integration-progress-20260531.md:123`(B-9 來源)| 2026-05-31 | 「眼湊 HSL → ...;目前僅 overview 過」 | ❌ **沿用了上面的舊數字** |
| `drift-audit-2026-05-25/audit-report.md:14-75` | **2026-05-25** | 「22/22 PARITY;Phase-2 epic 全清 Sprint 57.40-57.45」 | ✅ **較新且權威** |

→ B-9 在 integration-progress 被寫下時,**沒同步 2026-05-25 audit 的進度**;`02-frontend-status.md` 的「僅 overview 過」被原樣帶入。實際上 5 頁 CATASTROPHIC 在 audit 後 6 個 sprint(57.40-57.45)已全部重建。

---

## 2. Ground truth:我親跑 CI gate(本次工具無異常)

`cd frontend && node scripts/check-mockup-fidelity.mjs` → **exit 0 通過**:
- ✅ **diff guard**:`styles-mockup.css` 與 `reference/design-mockups/styles.css` **byte-identical**(我另獨立 `diff <(tr -d '\r' ...)` 二次確認 = empty)。→ 4-layer 協定 Layer 2 守住。
- ✅ **grep guard**:48 hardcoded hex/oklch lines = `HEX_OKLCH_BASELINE = 48`(`check-mockup-fidelity.mjs:85`)。未超標。

→ 「眼湊 HSL 翻譯」時代的 drift 已不存在於 CSS 層;hex/oklch 殘留都是**有案可查的 verbatim-token 用法**(baseline MHist `check-mockup-fidelity.mjs:30-84` 逐筆記錄每次 bump 來源 mockup 行)。

---

## 3. Audit verdict 親驗:5 CATASTROPHIC → 0(Sprint 57.40-57.45)

`audit-report.md:57-75` 親讀,逐 sprint 收斂鏈:
| Sprint | 重建頁 | 累計 |
|--------|--------|------|
| 57.40 | governance | 17 PARITY + 1 NEAR + 4 CATASTROPHIC |
| 57.41 | verification | 18 + 1 NEAR + 3 |
| 57.42 | memory | 19 + 1 NEAR + 2 |
| 57.43 | admin-tenants | 20 + 1 NEAR + 1 |
| 57.44 | tenant-settings | 21 + 1 NEAR + 0 CATASTROPHIC |
| 57.45 | chat-v2 NEAR→PARITY(Path B grep 推翻 audit row 9 transcription error)| **22 + 0 NEAR + 0** ✅ |

→ 與 §2 CI gate 結果一致(audit 是 per-page 視覺、gate 是 CSS+literal 結構代理,兩者都綠 = 互證)。

---

## 4. 真正剩餘的 B-9 工作(不是「重建 drift 頁」)

### (i) 14 個 PROP stub 待 promote→re-point
- `audit-report.md:51` + Explore:compaction / jit-retrieval / subagent-tree / incidents / redaction(註:redaction 已 PARITY,Explore 列入 stub 為誤,見 §5 不確定 4)/ cache-manager / sse / devui / models / tools / tenant-onboarding / pricing / rbac 等 render `ComingSoonPlaceholder`。
- **性質**:這些是「功能未實作」,不是「視覺 drift」。每個是**獨立 feature sprint**(後端 + 前端),re-point 只是其中一步。**不屬於** B-9 原意的「把 drift 頁重新 point」。

### (ii) 4 條未追蹤二階債(真正可列為 B-9 後續的)
| # | 債 | 證據 | 影響 |
|---|----|------|------|
| D1 | **HEX_OKLCH_BASELINE 可能未下修** | gate 顯示 live=48=baseline;rule(`check-mockup-fidelity.mjs:21`)要求「每次 re-point 移除 offender 應下修 baseline」。22 頁 PARITY 後仍 48,疑未隨重建下修 | baseline 過鬆 = 未來新 drift 較易溜過 |
| D2 | **Shell 層(AppShellV2/Sidebar)未比對 mockup** | `03-mockup-consistency-rootcause.md:144` 親述 PoC「未比對 AppShellV2 vs mockup shell.jsx」 | shell drift 是獨立未追蹤項,audit 22 頁是 content 層 |
| D3 | **無 per-page 視覺 CI** | `frontend-ci.yml:39-43` 只跑 CSS diff + literal count(結構代理),**無 Playwright 視覺回歸**;per-page parity 靠手動 sweep | 未來頁面內容 drift CSS gate 抓不到 |
| D4 | **5 頁無專屬 mockup `page-*.jsx`** | cost-dashboard / sla-dashboard / verification / redaction / error-policy 無獨立 mockup,靠 `page-platform*.jsx` 內嵌段落為來源 | 這些頁的「verbatim」標準較弱,future drift 無單一真相比對 |

---

## 5. 工具 / 證據可靠性

- 本次主 session 親跑 CI gate(`node check-mockup-fidelity.mjs` exit 0)+ 獨立 `diff` 二次確認 byte-identical,**無工具異常**。
- audit verdict 與 baseline MHist 為親 Read(行號連續)。
- **Explore 的兩處需修正**(我據親驗校正):
  1. Explore §9 結論「0 active pages with known fidelity debt remain」**過度樂觀** — 忽略了 §4 D1-D4 二階債。
  2. Explore §3 把 `redaction` 同時列 PARITY(§6)又列 PROP stub(§3 末)——矛盾;audit-report.md:45 明列 redaction **PARITY**(Sprint 57.39 clean),非 stub。本檔以 audit 為準。

---

## 6. 給決策的最短建議

| 問題 | 答案 |
|------|------|
| 「~13 頁待重建」還成立嗎? | ❌ 已過時;5 CATASTROPHIC 已於 57.40-57.45 全清,22/22 PARITY,CI gate 綠 |
| 還有 mockup 工作嗎? | ✅ 但性質不同:14 PROP stub promote(= feature sprint,非 re-point)+ §4 四條二階債 |
| 最高槓桿的小事? | **D3 加 per-page 視覺 CI** —— 把未來 drift 從「靠人眼 sweep」變成 CI 自動抓(對齊 A-5b schema-codegen 同精神)|
| 次高? | **D1 下修 baseline** —— 22 頁 PARITY 後 baseline 仍 48 疑過鬆,逐頁盤點可下修的 offender |
| 急嗎? | ❌ 現狀無 active drift;二階債是「防未來 drift」與「完成 stub」,可排程不需趕工 |
| 要改 integration-progress §B-9 嗎? | ⚠️ 建議:把 §B-9 措辭從「~13 頁待重建」更正為「22/22 PARITY 已達,剩 14 PROP promote + 4 二階債」(本檔即此校正的依據;改動原盤點需你授權)|

> 不需任何 frontend code 變更;B-9 的「重建」工作實際已完成。本檔結論 = 校正過時前提 + 列出真正剩餘的 4 條二階債 + 14 PROP promote。
