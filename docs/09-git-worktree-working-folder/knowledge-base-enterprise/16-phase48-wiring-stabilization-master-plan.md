# 16 - Phase 48：Wiring Stabilization Master Plan

**Phase Name**：Phase 48 — Wiring Stabilization
**啟動日期**：2026-04-20
**預計時長**：**~2 個月**（8 週）
**範疇**：修復三輪 audit 累計發現嘅 **28 個 HIGH+ gap** + CI 防線建立
**前置**：Doc 10/12/15 三輪 wiring audit 完成
**後續**：Phase 49 — Doc 08 原企業 knowledge base 升級路線圖（L3 Ontology / L4 Specialist / L6 Bitemporal / L5 Verifier）

---

## 零、為何需要本 Phase

### 現況診斷
- IPA Platform 44 Phases 高速功能迭代 → **feature-rich / integration-poor** 反模式
- 三輪 audit 累計發現 **~65 個 wiring gap，28 個 HIGH+**
- 4 個系統性 pattern 被識別（見 §1.2）
- **在未修復 wiring 前啟動 Doc 08 Ontology/Bitemporal 升級係浪費** — 新功能只會加劇 parallel evolution 問題

### 為何訂 2 個月
- 28 HIGH+ gap × 平均 6-8 小時 = 170-220 小時 = **4-5 週 1 人工時**
- 加 Workshop 依賴 delay（Sprint 002/003/004）
- 加 CI 防線建立（CI-03/04/05/06/07）
- 加 Manual verification + PR merge overhead
- 保留 20% slack（Taleb antifragility panel 意見）
- → **2 個月 realistic**

### 不做本 Phase 嘅代價
- SOX §404 / EU AI Act Art. 12 legal exposure（A-01）
- Agent decision quality 持續差（M-01 / HITL-01 / TH-01~04 silent fail）
- 新 dev 跑 `alembic upgrade head` schema 不 reproducible（DB-01）
- 零 production observability（OTL-01~03）
- 未來 Doc 08 L3 Ontology 每個 feature 都要 retrofit wiring → 估增 30-50% 工時

---

## 一、Phase Goals（must-have deliverables）

### 1.1 Quantitative Goals

| 指標 | 目標 |
|------|------|
| Gap fixed | ≥ 24/28 HIGH+（85%）|
| New CI checks wired | 7（CI-01~07）|
| Sprint delivered | 7（001-007）|
| Regression introduced | 0 |
| Production deploy readiness | Yes（blue-green / feature flag）|

### 1.2 Qualitative Goals

- **Pattern 清理 4/4**：
  - ✅ PoC→Production SSOT（Round 1-2）— Sprint 001/002
  - ✅ Fake Dispatcher（Round 2）— Sprint 002
  - ✅ Dead Infrastructure（Round 3）— Sprint 005
  - ✅ Parallel Evolution（Round 3）— Sprint 006/007
  - ✅ Baseline Missing（Round 3）— Sprint 004
  - ✅ PRD vs Reality（Round 3）— Sprint 004

- **Org enablement**：CI 防線建立後，未來 sprint **結構上唔可能引入同類 bug**

---

## 二、Sprint Schedule

### Timeline（gantt 概覽）

```
Week 1 (Apr 20-26)
  ├── Sprint 001 ✅ DONE (2d) — M-01 + HITL-01
  ├── Sprint 005 (5d) — OTL metrics wire-up    [ 無依賴 ]
  └── Sprint 006 (3d) — Resume 統一 + Dialog    [ 無依賴 ]

Week 2 (Apr 27 - May 3)
  ├── Sprint 007 (5d) — FE SSE schema codegen   [ 無依賴 ]
  └── Workshop 執行（用戶主持，60-90 min）

Week 3-4 (May 4-17)
  ├── Sprint 002 (5-6d) — Knowledge + Fake Dispatcher [ Workshop Q10/Q12 ]
  └── Sprint 004 (3d) — DB baseline + bitemporal      [ Workshop Q7 ]

Week 5-6 (May 18-31)
  └── Sprint 003 (4-5d) — Main chat audit emission    [ Workshop Q5/Q7 ]

Week 7-8 (Jun 1-14)
  ├── Medium gap cleanup（合併 mini-sprint）
  ├── Low gap cleanup
  ├── CI-01~07 全部 wire + 測試
  └── Phase 48 retrospective + Phase 49 kickoff
```

### Sprint 詳表

| # | Sprint | Scope（主要 gap） | 估時 | 依賴 | 狀態 |
|---|--------|------------------|------|------|------|
| 001 | M-01 + HITL-01 | search_memory + request_approval | 2 天 | 無 | ✅ **DONE** `5e513d8` |
| 005 | OTL Metrics Wire-up | OTL-01, OTL-02, OTL-03（Pipeline / Dispatch / Router 三層） | 5 天 | 無 | pending |
| 006 | Resume 統一 + Dialog | RES-01, RES-04 + DialogPauseException handler | 3 天 | 無 | **本 session 執行** |
| 007 | FE SSE Schema Codegen | FE-01, FE-02 + 兩 hooks 統一 | 5 天 | 無 | pending |
| 002 | Knowledge + Fake Dispatcher | K-01, E-01, TH-01, TH-02, TH-03, TH-04, ER-01 | 5-6 天 | **Workshop Q10/Q12** | pending workshop |
| 003 | Main Chat Audit Emission | A-01, CTX-01, A-02, A-03 | 4-5 天 | **Workshop Q5/Q7** | pending workshop |
| 004 | DB Baseline + Bitemporal | DB-01, DB-02, DB-03, DB-04, DB-05（部分併 A-04 / WORM-01 / PII-01）| 3-5 天 | **Workshop Q7** | pending workshop |

### Medium Gap Cleanup（合併 mini-sprint，Week 7-8）

| Gap | 來源 | 估時 |
|-----|------|------|
| CI-01 Import-existence check | Panel | 1 天 |
| CI-02 Config centralization test | Panel | 1 天 |
| CI-03 Fake dispatcher AST check | Panel | 1 天 |
| CI-04 Checkpoint round-trip test | Panel | 0.5 天 |
| CI-05 Metric emit coverage | Round 3 | 1 天 |
| CI-06 Alembic baseline check | Round 3 | 1 天 |
| CI-07 SSE event schema sync | Round 3 | 1 天 |
| P-01/P-03/P-05 Config drift | Round 2 | 1 天 |
| C-01, CTX-02, CTX-03 | Panel + Round 2 + Round 3 | 1 天 |
| RES-02/03/05/06 | Round 3 | 1 天 |
| OTL-04~08 | Round 3 | 1 天 |
| FE-03/04/05 | Round 3 | 1 天 |
| K-05, K-06 | Round 1 | 1 週 K-06 quick win |
| DB-06 | Round 3 | 0.5 天 |
| IR-01, ER-02, ER-03, TH-05 | Round 2 | 0.5 天 |

---

## 三、Sprint 執行 Policy

### 3.1 每個 Sprint 必做

按 CLAUDE.md Sprint Execution Workflow + Doc 14 template：

1. **Pre-execution**：讀目標代碼驗證 API signature（避免 Doc 14 API 錯誤重現）
2. **Branch**：從 main 開 `fix/wiring-sprint-{NNN}` branch
3. **Plan + Checklist**：每個 sprint 補 plan + checklist（Doc 14 係 template）
4. **Implementation + Tests**：最低標準 unit test；integration test 視環境而定
5. **Quality Gates**：black / isort / flake8（E501 ignored，line-length 100）/ pytest
6. **FIX doc**：每個 gap 一份 FIX-NNN.md 於 `claudedocs/4-changes/bug-fixes/`
7. **Doc 更新**：Doc 11/15 修復矩陣相應 gap 標 ✅ Fixed + 日期 + commit hash
8. **Commit**：符合 Conventional Commits；complex sprint 可多 commit
9. **Progress log**：`claudedocs/3-progress/daily/YYYY-MM-DD-sprint-{NNN}-progress.md`

### 3.2 CI Gates（新 sprint starting prerequisite）

- Sprint 001 merged 後啟 CI-01（import-existence check）— 防 M-01 reoccur
- Sprint 002 merged 後啟 CI-02（config centralization）+ CI-03（fake dispatcher AST）
- Sprint 004 merged 後啟 CI-06（alembic baseline check）
- Sprint 005 merged 後啟 CI-05（metric emit coverage）
- Sprint 006 merged 後啟 CI-04（checkpoint round-trip property test）
- Sprint 007 merged 後啟 CI-07（SSE event schema sync）

### 3.3 Risk Management

| Risk | Mitigation |
|------|-----------|
| Workshop 延誤 | Sprint 005/006/007 無依賴可並行，不阻 Sprint 002/003/004 |
| Integration test 需 live services | Docker compose up as pre-sprint checklist |
| Large refactor regression | Blue-green deploy + feature flag（尤其 Sprint 003 audit emission）|
| Cross-sprint conflict（e.g. Sprint 002 改 dispatch_handlers 與 Sprint 006 改 resume）| Sequence sprint 合併；rebase before PR |
| Scope creep（discover new gaps mid-sprint）| 記入 gap registry，延後 cleanup mini-sprint；**不 in-flight 擴 scope**|

---

## 四、Phase 48 Tracking

### 4.1 Gap Registry Status（即時更新）

完整 registry 維護於 Doc 11 §4.1 + Doc 15 §5：

- **CRITICAL gap**: 7
- **HIGH gap**: 21
- **MEDIUM gap**: 24
- **LOW gap**: 13
- **合計**: ~65

Status legend：
- ✅ Fixed — 已 merge 入 main
- 🔄 In Sprint — 有 active sprint 處理中
- ⏳ Planned — sprint 已計劃，未啟動
- ⚠️ Blocked — 待 Workshop / 外部決策

### 4.2 Dashboard（每週更新）

建議於 `claudedocs/3-progress/weekly/` 維護：

```
Week X dashboard:
├── Sprints completed this week
├── HIGH+ gap 修復數：X/28
├── CI checks live：X/7
├── Blockers
└── Next week focus
```

### 4.3 完成判定

**Phase 48 完成條件**：
- [ ] Sprint 001-007 全部 merge 入 main
- [ ] ≥ 24/28 HIGH+ gap 標 ✅ Fixed
- [ ] 7 個 CI check live + 跑通
- [ ] 無新 regression 進入 main（CI 驗證）
- [ ] Phase 48 retrospective 完成
- [ ] Phase 49 kickoff plan 開始

---

## 五、Phase 49 Preview（本 phase 完成後）

**Phase 49 — Doc 08 原企業 Knowledge Base 升級路線圖**（預計 6-9 個月）：

基於 Doc 08 + Workshop 決策：

- L3 Ontology（Graphiti / Kuzu PoC → Neo4j decision）— 10 週 critical path
- L4 Specialist Agents（Finance Variance / Compliance / Analogy / Authorization）— 12-16 週
- L5 Verifier Agent two-stage + risk-gated — 2-3 週
- L6 Bitemporal / WORM / PII dual-layer — 4-6 週（併 Sprint 004 成果延伸）
- K-04 Agent Skills YAML 化 + 與 Qdrant 統一 — 1-2 週

**Phase 49 前提**：Phase 48 完成 + 28 HIGH+ gap 修復，確保新功能建基於穩固 wiring。

---

## 六、立即啟動（本 session）

| 動作 | 狀態 |
|------|------|
| 寫 Doc 16 Master Plan（本文） | ✅ 本 session |
| 寫 Sprint 002-007 plan stubs | ✅ 本 session |
| Commit Phase 48 planning docs | ✅ 本 session |
| **執行 Sprint 006**（RES-01/04 + Dialog resume）| ✅ **本 session 壓縮執行** |
| 更新 MEMORY.md 反映 Phase 48 launch | ✅ 本 session |

**Sprint 006 係 Phase 48 嘅第二個 deliver sprint**（Sprint 001 係第一個）。完成後本 session 結束；Sprint 002/003/004/005/007 留俾後續 session / day。

---

## 七、Reference

- Doc 10/11/12/15 — Wiring Audit series（所有 gap 來源）
- Doc 13/13a — Workshop agenda（解鎖 Sprint 002/003/004）
- Doc 14 — Sprint 001 plan template（適用其餘 sprint）
- `claudedocs/3-progress/daily/2026-04-20-sprint-wiring-fix-001-progress.md` — Sprint 001 retrospective
- CLAUDE.md — Sprint Execution Workflow policy

---

## 八、版本記錄

| Version | Date | Author |
|---------|------|--------|
| 1.0 | 2026-04-20 | Claude + Chris — Phase 48 kickoff |
