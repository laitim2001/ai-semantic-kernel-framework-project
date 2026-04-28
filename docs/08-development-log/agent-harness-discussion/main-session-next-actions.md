# 本主 Session 後續工作 Prompts（2026-04-23 更新）

**用途**：本主 session 可立即執行的後續工作
**使用方式**：複製對應 Prompt 在主 session 直接執行

---

## 更新說明（2026-04-23）

### 已完成（不需重做）
- ✅ 階段 A：3 子代理 review 02 / 04 / 09 已執行
- ✅ P0 修訂：9 個 P0 問題已修訂
- ✅ 3 大原則補強：00 / 01 / 05 強化 + 新建 10-server-side-philosophy.md
- ✅ 6 大缺口補完：新建 11 / 12 / 13 / 14 / 15 / 16

### 規劃文件最終版本（17 份）
詳見 `docs/03-implementation/agent-harness-planning/README.md`

---

## 推薦執行順序（更新版）

```
階段 A：（已完成 ✅）
  3 子代理 review 02 / 04 / 09 + P0 修訂

階段 B：用戶開新 session 跑優先 review
  ⭐ Prompt 1（max effort）→ review 01 + 10
  ⭐ Prompt 2（high effort）→ review 06
  可選：Prompt 3-8（review 12 / 11 / 14 / 15 / 16 / 13）
  
  （所有 prompts 在 new-session-review-prompts.md）

階段 C：用戶整合 review reports
  → Prompt C1：整合 reports + 修改規劃文件

階段 D：啟動 Phase 49 開發
  → Prompt D1：建立 Sprint 49.1 plan + checklist
  → Prompt D2：執行 V1 封存
  → Prompt D3：建立 V2 目錄骨架

階段 E：V2 持續開發
  → 每個 Sprint 重複 plan → execute → retro
```

---

## 三個啟動策略（用戶選擇）

| 策略 | 流程 | 適合 |
|------|------|------|
| **A 先 review 後動工** | B → C → D | 想要 review 後再動 |
| **B 直接動工** | D（跳過 B + C） | 想盡快動手 |
| **C 平行（推薦）** | B 同時 D | 最有效率 |

---

## Prompt A1：平行 Sub-Agent Review（立即執行）

**目標**：用 3 個子代理同時 review 文件 02 / 04 / 09，收集獨立意見

**直接複製貼上到主 session：**

```
請啟動 3 個子代理平行 review V2 規劃文件，收集獨立意見：

Agent 1（codebase-researcher）：
任務：以資深軟體架構師視角 review 02-architecture-design.md
位置：C:\Users\Chris\Downloads\ai-semantic-kernel-framework-project\docs\03-implementation\agent-harness-planning\02-architecture-design.md
評估：4 層分離合理性、依賴方向、API 設計、與 V1 對比、可擴展性
輸出：800 字內 review 報告，重點問題與改進建議

Agent 2（codebase-researcher）：
任務：對 V1 代碼掃描驗證 04-anti-patterns.md 中 10 個反模式真實性
反模式文件：C:\Users\Chris\Downloads\ai-semantic-kernel-framework-project\docs\03-implementation\agent-harness-planning\04-anti-patterns.md
掃描位置：backend/src/
針對每個 anti-pattern 提供：是否真實存在、嚴重度、典型案例（檔案+行號）、V2 緩解機制是否充分
輸出：1000 字內報告

Agent 3（codebase-researcher）：
任務：以資深 PostgreSQL DBA + 後端架構師視角 review 09-db-schema-design.md
位置：C:\Users\Chris\Downloads\ai-semantic-kernel-framework-project\docs\03-implementation\agent-harness-planning\09-db-schema-design.md
評估：Schema 完整性、設計品質、Multi-tenant 隔離、Append-only 機制、效能風險、資料完整性、與業界對比
輸出：1200 字內報告，按優先級給修改建議

3 個子代理平行執行，完成後整合 3 份報告給我看。
```

---

## Prompt C1：整合 5 份 Review Reports

**目標**：收齊 5 份 review（3 子代理 + 2 新 session）後，整合分析並修改文件

**前置條件**：
- ✅ Prompt A1 已執行完成（取得 3 份子代理 reports）
- ✅ 用戶已在新 session 跑完 Review Prompt 1 + 2 並貼回 reports

**直接複製貼上到主 session：**

```
以下是 5 份 V2 規劃文件的獨立 review reports：

## Report 1（新 session A）：01-eleven-categories-spec.md
[貼入 Review Prompt 1 的回應內容]

---

## Report 2（新 session B）：06-phase-roadmap.md
[貼入 Review Prompt 2 的回應內容]

---

## Report 3（子代理）：02-architecture-design.md
[貼入子代理回應]

---

## Report 4（子代理）：04-anti-patterns.md
[貼入子代理回應]

---

## Report 5（子代理）：09-db-schema-design.md
[貼入子代理回應]

---

## 整合任務

請進行以下整合分析：

### 1. 共通問題識別
列出**多份 report 都提到的問題**（信號最強）：
- 問題 X：被 Report A、B、C 提及，建議：...
- ...

### 2. 獨有問題評估
列出**單份 report 獨有問題**：
- 評估是否主觀 / 客觀
- 是否需修改

### 3. 衝突意見
列出 **report 之間有衝突**的部分：
- Report A 說 X，Report B 說 not X
- 我的判斷：...

### 4. 修訂優先級
- P0（必修）：...
- P1（應修）：...
- P2（可修）：...
- 不修的（解釋為何）：...

### 5. 執行修改
按 P0 → P1 順序，**直接修改對應規劃文件**：
- 文件 01：修改了 ___
- 文件 02：修改了 ___
- ...

完成後總結修改範圍與成果。
```

---

## Prompt D1：建立 Phase 49 Sprint 49.1 詳細規劃

**目標**：規劃整合完成後，建立第一個 Sprint 詳細文件

**前置條件**：✅ V2 規劃文件已經過 review + 整合修改

**直接複製貼上到主 session：**

```
V2 規劃文件 review 完成且整合修改完畢，現在進入執行階段。

請建立 Phase 49 Sprint 49.1 的詳細規劃文件。

## Sprint 49.1 概要（來自 06-phase-roadmap.md）
- **名稱**：V1 封存 + V2 目錄骨架
- **時程**：1 週
- **Deliverables**：
  - V1 完整移到 archived/v1-phase1-48/
  - V2 backend 目錄樹建立
  - V2 frontend 目錄樹建立
  - 每個範疇的 README + ABC（空殼）
  - pyproject.toml / requirements.txt V2
  - package.json V2
  - docker-compose.dev.yml

## 任務

請建立 2 份文件：

### 文件 1：Sprint Plan
路徑：`docs/03-implementation/agent-harness-planning/phase-49-foundation/sprint-49-1-plan.md`

內容包含：
- Sprint goal（清晰一句話）
- User stories（作為/我希望/以便 格式）
- 技術設計（具體技術決策）
- 待建立的目錄與檔案完整清單
- 依賴與風險
- Acceptance criteria（可勾選）
- 與 11 範疇的關係

### 文件 2：Sprint Checklist
路徑：`docs/03-implementation/agent-harness-planning/phase-49-foundation/sprint-49-1-checklist.md`

內容：
- 按工作天數分組的 checkbox 任務
- 每個任務有：
  - [ ] 任務描述
  - 預估時間
  - Definition of Done
- 末段：Sprint 結束驗收 checklist

兩份文件都用繁體中文，格式參考之前的 V2 規劃文件風格。
```

---

## Prompt D2：執行 V1 封存

**目標**：完成 Sprint 49.1 第一步，把 V1 完整封存

**前置條件**：✅ Sprint 49.1 plan 已建立並確認

**直接複製貼上到主 session：**

```
執行 V1 封存。請按以下步驟操作：

## Step 1：Git tag 標記 V1 終點
```bash
git tag v1-final-phase48
```

## Step 2：建立 archived 目錄
```bash
mkdir -p archived/v1-phase1-48
```

## Step 3：移動 V1 backend 與 frontend
```bash
git mv backend archived/v1-phase1-48/backend
git mv frontend archived/v1-phase1-48/frontend
```

## Step 4：建立封存 README
位置：`archived/v1-phase1-48/README.md`
內容包含：
- 封存說明
- V1 真實對齊度（27%）
- 為何重生（5 個原因摘要）
- 如何 git checkout 回來看
- 對應的 V9 分析位置
- 對應的 CC research 位置

## Step 5：提交
```bash
git add -A
git commit -m "chore: archive V1 (Phase 1-48) — V2 rebirth begins"
```

## 驗收
- [ ] backend 與 frontend 不再在根目錄
- [ ] archived/v1-phase1-48/ 含完整代碼
- [ ] git log 顯示 commit
- [ ] git tag 列表含 v1-final-phase48
- [ ] V9 分析、CC research、claudedocs 等知識資產**未動**
- [ ] reference/、graphify-out/ 等**未動**

請逐步執行並確認每步成功。如遇問題立即停下確認。
```

---

## Prompt D3：建立 V2 目錄骨架

**目標**：完成 Sprint 49.1 第二步，建立 V2 backend + frontend 目錄樹

**前置條件**：✅ V1 已封存

**直接複製貼上到主 session：**

```
V1 已封存，現在建立 V2 目錄骨架。

## Step 1：建立 V2 backend 目錄樹

請參考 02-architecture-design.md 的目錄結構，建立完整目錄。

包含：
- backend/src/api/v1/ + 子目錄
- backend/src/agent_harness/ + 11 範疇子目錄（01_xxx 到 11_xxx）
- backend/src/platform/ + 子目錄
- backend/src/adapters/ + 子目錄
- backend/src/business_domain/
- backend/src/infrastructure/ + 子目錄
- backend/src/core/ + 子目錄
- backend/src/middleware/
- backend/tests/ + 子目錄

每個目錄放空 __init__.py。

## Step 2：每個範疇放 README.md

每個 agent_harness/0X_xxx/ 下放：
- README.md（簡短說明該範疇用途、Level 標籤、待實作項目）
- 該範疇主要 ABC 定義（空殼，只有 interface 簽名）

## Step 3：建立 V2 frontend 目錄

包含：
- frontend/src/pages/ + 子目錄
- frontend/src/features/ + 11 範疇對應子目錄
- frontend/src/shared/ + 子目錄
- frontend/src/stores/
- frontend/src/services/

## Step 4：建立 V2 配置檔

- backend/pyproject.toml（V2 版本，async 套件）
- backend/requirements.txt
- frontend/package.json（V2 版本）
- docker-compose.dev.yml（包含 postgres / redis / qdrant / rabbitmq / jaeger / backend / frontend）
- .env.example（V2 配置範本）

## Step 5：基本驗證

- [ ] tree 視覺化檢查目錄完整
- [ ] cd backend && pip install -e . 成功（即使無實作）
- [ ] cd frontend && npm install 成功
- [ ] docker compose up 啟動依賴服務成功

完成後給出 V2 骨架檔案清單摘要。
```

---

## Prompt E1+：每個 Sprint 開始時的範本

**未來每個 Sprint 啟動時的標準 prompt**

**範本：**

```
啟動 Phase XX Sprint XX.Y。

## 前置檢查
請先確認：
- [ ] 上個 Sprint 的 retrospective 已完成
- [ ] Sprint XX.Y plan + checklist 已建立
- [ ] 範疇成熟度狀態已更新

## Sprint 任務
（從 plan 文件摘要）

## 執行
按 checklist 順序執行，遇到問題立即提報。

## 每日進度
在 docs/03-implementation/agent-harness-execution/phase-XX/sprint-XX-Y/progress.md 記錄。

## Sprint 結束
建立 retrospective.md，包含：
- 範疇成熟度變化（Level X → Y）
- Anti-Pattern 違反次數
- 學到的經驗
- 下個 Sprint 改進
```

---

## 主 Session 工作節奏建議

### 每日節奏
```
早上：
  - 查看 progress.md 上次進度
  - 確認當天 checklist
  - 開始實作

中段：
  - 遇問題立即跟主 session 討論
  - 完成項目即時更新 checklist

晚上：
  - 更新 progress.md
  - 確認當天 deliverables
```

### 每週節奏（每 Sprint 結束）
```
Sprint 結束日：
  - 建立 retrospective.md
  - 更新範疇成熟度
  - Anti-pattern audit
  - 啟動下個 Sprint plan
```

### 每月節奏（每 Phase 結束）
```
Phase 結束：
  - Phase 整體 retro
  - 對齊度測量（11 範疇 Level 統計）
  - 主規劃文件更新（如有重大調整）
  - 啟動下個 Phase 規劃
```

---

## 緊急情況 Prompts

### 緊急 1：發現規劃有重大問題

```
我在執行 [Sprint XX.Y] 時發現規劃文件 [00 / 01 / 02 / ...] 有重大問題：

[描述問題]

請：
1. 評估問題嚴重度
2. 決定是否暫停 Sprint
3. 提出修改方案
4. 更新對應規劃文件
```

### 緊急 2：技術選型需重新評估

```
[GPT-5.4 / Worker queue / 某項技術] 在實際使用中發現問題：

[描述問題]

請：
1. 重新評估該技術選型
2. 對比候選方案
3. 給出新建議
4. 更新 07-tech-stack-decisions.md
```

### 緊急 3：時程超期

```
Phase XX 已超期 X 天，原因：[...]

請：
1. 分析超期根因
2. 重新評估剩餘時程
3. 給出兩個選項：
   - 延長時程
   - 砍 scope
4. 更新 06-phase-roadmap.md
```

---

## 工具性 Prompts

### 工具 1：產生範疇進度 Dashboard

```
請產生當前 11 範疇成熟度 dashboard，格式：

| 範疇 | 目標 Level | 當前 Level | 進度 % | 主要阻礙 |
|------|----------|----------|--------|---------|
| ... | | | | |

整體對齊度：__%
距 75% 目標：__%
```

### 工具 2：Anti-Pattern Audit

```
請對最近一個 Sprint 的代碼變更進行 Anti-Pattern audit：

10 個 anti-patterns 違反次數：
- AP-1: __
- AP-2: __
- ...

具體違例（如有）：
- 檔案: 行號: 違反 AP-X，原因 ___

建議行動：
- ...
```

### 工具 3：補規劃文件缺漏

```
請補齊以下規劃缺漏：

10-category-contracts.md（範疇間整合契約）
11-test-strategy.md（測試與驗收策略）

按目前已有文件風格撰寫。
```

---

## 結語

本文件涵蓋 V2 從 review 到啟動到執行的所有關鍵 prompt。

建議使用方式：
1. **保留此文件**作為 V2 開發 reference
2. **複製對應 prompt** 在主 session 或新 session 直接貼上
3. **定期更新**（隨開發進度新增 prompt）

下次工作時，從**階段 A 的 Prompt A1** 開始。
