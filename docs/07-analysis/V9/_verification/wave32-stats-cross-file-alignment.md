# Wave 32: 00-stats.md 跨文件數字對齊驗證

> Date: 2026-03-31 | Analyst: Claude Opus 4.6 (1M context)
> Method: 逐項比對 `00-stats.md` 與各 layer/module/feature 文件中的數字

---

## Layer 文件數/LOC 對齊（P1-P20）

| # | Layer | Metric | stats 值 | layer 文件值 | 結果 | 備註 |
|---|-------|--------|----------|-------------|------|------|
| P1 | L01 Frontend | Files | 236 | 236 (210 source + 26 tests) | ✅ 一致 | |
| P2 | L01 Frontend | LOC | 54,238 | ~54K | ✅ 一致 | layer 用約數 |
| P3 | L02 API Gateway | Files | 153 | **152** | ❌ 不一致 | layer-02 says "152 (107 non-init, 45 `__init__.py`)", stats says 153. **layer 文件的 R3/R4 verified 數字 152 應為準** |
| P4 | L02 API Gateway | LOC | 47,377 | **46,341** | ❌ 不一致 | layer-02 says "LOC: 46,341", stats says 47,377. **差額 1,036。layer 文件為 R4 verified，應以 layer 為準** |
| P5 | L03 AG-UI | Files | 27 | 27 (+1 mediator_bridge = 28 effective) | ✅ 一致 | header 提到 28 effective 但 Total 明確寫 27 |
| P6 | L03 AG-UI | LOC | 10,329 | 10,329 (但 header 寫 ~10,500) | ⚠️ 自身矛盾 | layer-03 header 寫 "~10,500" 但 file inventory total 寫 "10,329"。stats 與 inventory total 一致 |
| P7 | L04 Routing | Files | 55 | 55+ | ✅ 一致 | layer 用 "55+" 約數 |
| P8 | L04 Routing | LOC | 20,272 | **~16,000** | ❌ 不一致 | layer-04 header says "~16,000 LOC", stats says 20,272。**差額 ~4,272，嚴重不一致。需確認哪個是 wc -l 實測值** |
| P9 | L05 Orchestration | Files | 89 | **90+** | ❌ 不一致 | layer-05 says "90+ Python files", stats says 89。**layer 文件為源，應以 90+ 為準** |
| P10 | L05 Orchestration | LOC | 28,800 | **~26K** | ❌ 不一致 | layer-05 says "~26K LOC", stats says 28,800。**差額 ~2,800。需確認哪個是 wc -l 實測值** |
| P11 | L06 MAF Builders | Files | 57 | 57 (R7 verified) | ✅ 一致 | 但 scope line 寫 "56 Python files"，body 寫 57 — layer 自身矛盾 |
| P12 | L06 MAF Builders | LOC | 38,082 | 38,082 (R4 verified) | ✅ 一致 | |
| P13 | L07 Claude SDK | Files | 48 | **47** | ❌ 不一致 | layer-07 says "Files: 47", stats says 48。**差額 1。layer 文件為 R4 verified，應以 47 為準** |
| P14 | L07 Claude SDK | LOC | 15,406 | 15,406 (R4 verified) | ✅ 一致 | |
| P15 | L08 MCP Tools | Files | 73 | 73 (R4 verified) | ✅ 一致 | |
| P16 | L08 MCP Tools | LOC | 20,847 | 20,847 (R4 verified) | ✅ 一致 | |
| P17 | L09 Integrations | Files | 77 | **75** | ❌ 不一致 | layer-09 says "75 Python files", stats says 77。**差額 2。layer 文件為 R4 verified，應以 75 為準** |
| P18 | L09 Integrations | LOC | 22,604 | **~21,300** | ❌ 不一致 | layer-09 says "~21,300 LOC", stats says 22,604。**差額 ~1,304** |
| P19 | L10 Domain | Files | 117 | 117 | ✅ 一致 | |
| P20 | L10+L11 | LOC/Files | L10: 47,637 / L11: 95 files, 21,953 | L10: 47,637 / L11: 95 files, 21,953 | ✅ 一致 | |

**小計**: 20 點中 ✅ 12 / ❌ 7 / ⚠️ 1

---

## API 端點數對齊（P21-P30）

| # | Metric | stats 值 | 對照文件值 | 結果 | 備註 |
|---|--------|----------|-----------|------|------|
| P21 | 端點總數 (Section 4) | 560+ | — | — | stats Section 4 寫 "Estimated Endpoints: 560+" |
| P22 | 端點總數 (Architecture diagram) | **575** | — | — | stats 架構圖多次寫 "575 endpoints" |
| P23 | 端點總數 vs api-reference.md | 575 (diagram) / 560+ (S4) | **566** (api-reference) | ❌ 不一致 | api-reference.md says "563 REST + 3 WebSocket = 566 endpoints" |
| P24 | 端點總數 vs layer-02 | 575 (diagram) / 560+ (S4) | **594** (layer-02) | ❌ 不一致 | layer-02 says "594 (verified R3/R4 grep count)" |
| P25 | api-reference vs layer-02 | 566 | 594 | ❌ 不一致 | 三方數字完全不同: stats=575/560+, api-ref=566, layer-02=594 |
| P26 | Route Modules (stats) | 48 | layer-02: 43 directories | ❌ 不一致 | stats Section 4 says 48, layer-02 says "43 directories", stats diagram says "43 route modules" — stats 內部也矛盾 |
| P27 | Routers count | 48 routers (in diagram) | layer-02: 47 (1 public + 46 protected) | ❌ 不一致 | |
| P28 | Auth-Protected | ~530 | Not verified in layer file | ⚠️ 無法對照 | |
| P29 | Public Routes | ~30 | Not verified in layer file | ⚠️ 無法對照 | |
| P30 | Pydantic schemas | 38 schema files (stats S5) | layer-02: 634 BaseModel classes | ✅ 一致 | 不同維度，不矛盾。stats S5 另說 "~690 Pydantic BaseModel Classes"，與 634 有差異 |

**小計**: 10 點中 ✅ 1 / ❌ 5 / ⚠️ 2 / — 2

---

## 測試數對齊（P31-P40）

| # | Metric | stats 值 | testing-landscape 值 | 結果 | 備註 |
|---|--------|----------|---------------------|------|------|
| P31 | Total Test Files | **469** | **~378** (~354 backend + 24 frontend) | ❌ 不一致 | stats=469, testing-landscape=~378。差額 91 |
| P32 | Backend Unit Tests | **345** | **~289** | ❌ 不一致 | 差額 56 |
| P33 | Backend Integration Tests | **43** | **~28** | ❌ 不一致 | 差額 15 |
| P34 | Backend E2E Tests | **29** | **~23** | ❌ 不一致 | 差額 6 |
| P35 | Backend Security Tests | **5** | **3** | ❌ 不一致 | 差額 2 |
| P36 | Backend Performance Tests | **13** | **~15** (10 + 5) | ❌ 不一致 | stats=13, landscape=~15 |
| P37 | Backend Load Tests | **2** | **1** (locustfile.py) | ❌ 不一致 | |
| P38 | Backend Root (conftest etc.) | **6** | Not separately tracked | ⚠️ 無法對照 | |
| P39 | Frontend Unit Tests | 13 (12 swarm + 1 store) | 13 | ✅ 一致 | |
| P40 | Frontend E2E Tests | **13** | **11** | ❌ 不一致 | 差額 2 |

**小計**: 10 點中 ✅ 1 / ❌ 8 / ⚠️ 1

---

## 其他數字（P41-P50）

| # | Metric | stats 值 | 對照文件值 | 結果 | 備註 |
|---|--------|----------|-----------|------|------|
| P41 | Issue 總數 | TBD (Section 10 寫 "TBD") | **93** (issue-registry) | ⚠️ 未填入 | stats Section 10 留空 "TBD (V9 analysis)"，issue-registry 已有 93 issues |
| P42 | Issue CRITICAL | (未列) | 14 (issue-registry) | ⚠️ 未填入 | |
| P43 | Issue HIGH | (未列) | 22 (issue-registry) | ⚠️ 未填入 | |
| P44 | Features (Cat A-E) | TBD | 47 features (44 COMPLETE + 2 PARTIAL + 1 SPLIT) | ⚠️ 未填入 | |
| P45 | Features (Cat F-J) | TBD | 26+ features (Cat J has 15 V8 + 11 NEW) | ⚠️ 未填入 | |
| P46 | Features Total | TBD | ~73+ (47 + 26+) | ⚠️ 未填入 | |
| P47 | Enum 數量 | (未列 in stats) | **339** (enum-registry: r8 gap scan) | ⚠️ 未列 | stats 沒有 enum 統計 |
| P48 | Enum 數量 | — | 339 confirmed in r7-validation, r5-enums.json | ⚠️ 未列 | |
| P49 | Total Phases | 44 | 44 (delta files cover Phase 35-44) | ✅ 一致 | |
| P50 | Total Sprints | 152+ | ~152 (delta-phase-43-44: Sprints 148-152) | ✅ 一致 | |

**小計**: 10 點中 ✅ 2 / ⚠️ 8

---

## 額外發現：stats 內部自相矛盾

| # | Metric | 位置 A | 值 A | 位置 B | 值 B | 備註 |
|---|--------|--------|------|--------|------|------|
| X1 | Source Files | Section 1 | 1,029 | Section 10 Delta table | 1,090 | **內部矛盾**：Section 1 says 1,029 but Section 10 V9 column says 1,090 |
| X2 | Total LOC | Section 1 | 327,583 | Section 10 Delta | ~250K | **內部矛盾**：Section 1 says 327,583 but Section 10 V9 column says ~250K |
| X3 | Endpoints | Diagram L2 | 575 | Section 4 | 560+ | **內部矛盾** |
| X4 | MCP Servers | Diagram L8 | 9 | Section 8 Config | 8 | **內部矛盾**：layer-08 verified = 9 servers |
| X5 | MCP Tools | Diagram L8 | 70 | Section 8 Config | 64 | **內部矛盾**：layer-08 verified = 70 tools |
| X6 | Route Modules | Diagram | 43 | Section 4 | 48 | **內部矛盾** |
| X7 | Frontend hooks | Diagram L1 | 33 | layer-01 file | 25 | **stats diagram says 33 hooks but layer-01 verified = 25 hooks** |
| X8 | Frontend components | Diagram L1 | 143 | layer-01 file | 116 source (127 with tests) | **stats diagram says 143 but layer-01 Component total = 116 source** |

---

## 總結

| 區域 | 點數 | ✅ | ❌ | ⚠️ |
|------|------|-----|-----|-----|
| Layer Files/LOC (P1-P20) | 20 | 12 | 7 | 1 |
| API Endpoints (P21-P30) | 10 | 1 | 5 | 4 |
| Testing (P31-P40) | 10 | 1 | 8 | 1 |
| Other (P41-P50) | 10 | 2 | 0 | 8 |
| **Total** | **50** | **16** | **20** | **14** |

另發現 **8 項 stats 內部自相矛盾** (X1-X8)。

### 嚴重不一致清單（需修正）

1. **L02 Files**: stats 153 → should be **152** (layer-02 R3/R4 verified)
2. **L02 LOC**: stats 47,377 → should be **46,341** (layer-02 R4 verified)
3. **L02 Endpoints**: stats 575 → at least 3 conflicting numbers (575/566/594), need re-count
4. **L04 LOC**: stats 20,272 vs layer-04 ~16,000 — **差額 ~4,272**
5. **L05 Files**: stats 89 vs layer-05 90+ — off by 1+
6. **L05 LOC**: stats 28,800 vs layer-05 ~26K — **差額 ~2,800**
7. **L07 Files**: stats 48 → should be **47** (layer-07 R4 verified)
8. **L09 Files**: stats 77 → should be **75** (layer-09 R4 verified)
9. **L09 LOC**: stats 22,604 vs layer-09 ~21,300 — **差額 ~1,300**
10. **Testing numbers**: stats 全面高估（total 469 vs 378，unit 345 vs 289，etc.）
11. **MCP Config section**: 8 servers/64 tools → should be **9 servers/70 tools**
12. **Source Files internal**: 1,029 (Section 1) vs 1,090 (Section 10 Delta)
13. **Total LOC internal**: 327,583 (Section 1) vs ~250K (Section 10 Delta)
14. **Frontend hooks**: stats 33 → should be **25** (layer-01 verified)
15. **Frontend components**: stats 143 → should be **116** source (layer-01 verified)

### 建議修正優先順序

1. **P1 (Critical)**: 修正 stats Section 8 MCP Servers 8→9, Tools 64→70
2. **P1 (Critical)**: 修正 L02 三方端點數不一致 (575 vs 566 vs 594)
3. **P1 (Critical)**: 解決 stats 內部 Source Files/LOC 矛盾 (Section 1 vs Section 10)
4. **P2 (High)**: 修正所有 layer files/LOC 差異 (L02, L04, L05, L07, L09)
5. **P2 (High)**: 修正 Testing 全面高估問題
6. **P2 (High)**: 修正 Frontend hooks (33→25) 和 components (143→116)
7. **P3 (Medium)**: 填入 TBD 欄位 (issues=93, features=~73+)
8. **P3 (Medium)**: 添加 enum 統計 (339)
