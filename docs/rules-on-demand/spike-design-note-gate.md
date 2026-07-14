# Spike Design-Note 8-Point Quality Gate (Step 5.5)

**Purpose**: Full 8-Point Quality Gate checklist + quality-is-verified-ratio table + Day-4 retrospective self-check record format for spike-sprint design-note extraction. The when-to-apply trigger lives in `.claude/rules/sprint-workflow.md` §Step 5.5 (always-loaded); this file is Read on demand at every spike sprint's Day 4 closeout.
**Category / Scope**: Development Process / on-demand rule (REFACTOR-011)
**Created**: 2026-07-14 (REFACTOR-011; content dates to 2026-05-08 doc-level rolling discipline)
**Last Modified**: 2026-07-14
**Status**: Active

> **Modification History**
> - 2026-07-14: REFACTOR-011 — extracted verbatim from sprint-workflow.md §Step 5.5 (always-loaded slimming)

**Trigger（什麼時候 Read）**: spike sprint 的 Day 4 closeout（feature continuation sprint 不適用 — 判準在 sprint-workflow.md §Step 5.5）。

**Template**: `claudedocs/templates/spike-design-note-template.md`

---

## 8-Point Quality Gate（design note submission checklist）

每個 spike-extract design note **必須**通過下列 8 條（reviewer 逐點驗證）：

- [ ] **1. Section header 對應 spike user story**
  - ❌ Generic：「OIDC overview」/「Authentication design」
  - ✅ Specific：「US-A2: OIDC PKCE Flow as wired in Sprint 57.7」

- [ ] **2. 每個技術 claim 有 file:line**
  - ❌「we use RS256」/「JWT validated via JWKS」
  - ✅「`JWTManager.encode()` at `backend/src/platform_layer/identity/jwt.py:42-58`」

- [ ] **3. Decision rationale 含比較矩陣**
  - ❌「Best practice」/「industry standard」
  - ✅ 三/四欄 vendor matrix + Cost / SCIM / SAML / Decision + 否決原因

- [ ] **4. Verification command（reproducible）**
  - ✅ `pytest tests/integration/auth/test_oidc_flow.py::test_real_entra_callback`
  - ✅ 或具體 manual reproduce step（curl + expected response）

- [ ] **5. Test fixture reference**
  - ✅ Link 到實際 test data / mock setup file
  - ✅ 若 real-LLM 測試，標明 `pytest -m real_llm` 與 cost 估算

- [ ] **6. Open invariant 明確分界**
  - ✅「Verified in this spike: A, B, C」+「Deferred to Phase XX.Y (NOT verified): D, E, F」
  - ❌ 將 deferred 內容寫入主 section 偽裝 verified

- [ ] **7. Rollback / fallback 路徑**
  - ✅「若設計後續證明錯，revert API routes at `auth.py` + DB column `external_id`；估 1-2 day」
  - ✅ 識別 sentinel / fallback 是否已存在
  - ❌ 假設「不會錯」

- [ ] **8. Cross-reference 17.md single-source**
  - ✅ 任何新 contract 必須在 `17-cross-category-interfaces.md` 對應 §section 登記
  - ✅ 若新增 ABC，標明 owner category
  - ❌ 在 design note 平行定義 contract（違反 single-source）

## Quality 不是頁數，是 verified ratio

| 維度 | 14.md 風格（high page low quality） | Spike-extract 風格（mid page high quality） |
|------|-------------------------------|------------------------------------------|
| Verified ratio | 10.6% (91/862 行) | ≥ 95% |
| 每 claim 對應 file:line | ❌ 大部分 pseudo-code | ✅ 強制 |
| Decision rationale | ❌ 「primary IdP = Entra」無矩陣 | ✅ vendor comparison matrix |
| Verification reproducibility | ❌ 無 | ✅ pytest command + fixture |
| Maintenance | ❌ 半年內過時（57.5 揭示） | ✅ 隨 PR 同步 |
| 結果頁數 | 800+ 行 | 通常 200-500（outcome，非 cap） |

**禁止**：用「regulated 200-300 行」當品質替代品。重點是**禁止 speculation 充頁數**，不是壓縮 verified content。若 spike 真的學到 600 行 worth verified invariants，就寫 600 行。

## Template

每個 spike-extract design note 使用 `claudedocs/templates/spike-design-note-template.md` 結構（含 8 sections：Spike Summary / Decision Matrix / Verified Invariants / Cross-Category Contracts / Open Invariants / Rollback / References / Modification History）。

## Day 4 closeout 自查 record

retrospective.md 必須記錄：

```markdown
## Design Note Extract（spike sprint only）

**File**: `docs/03-implementation/agent-harness-planning/<doc-number>-<topic>.md`
**Verified ratio (estimated)**: __%
**8-Point Quality Gate**:
- [ ] 1. Section header
- [ ] 2. file:line 引用
- [ ] 3. Decision matrix
- [ ] 4. Verification command
- [ ] 5. Test fixture
- [ ] 6. Open invariant 分界
- [ ] 7. Rollback path
- [ ] 8. 17.md cross-ref

**Reviewer pass**: <user / self-review>
```


