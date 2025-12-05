# 🆕 情況4: 新功能開發

> **使用時機**: 對話進行中,正在開發全新功能
> **目標**: 系統化開發,符合架構標準
> **適用場景**: Epic Story 實施, 新模組開發

---

## 📋 Prompt 模板

```markdown
我正在開發新功能: [功能名稱]

根據: [Epic X Story X.X / 用戶需求 / 設計文檔]

請幫我:

1. 建立功能規劃目錄
   - 在 claudedocs/1-planning/features/ 建立 FEAT-XXX-[功能名稱] 目錄
   - 建立 01-requirements.md (需求規格)
   - 建立 02-technical-design.md (技術設計)
   - 建立 03-implementation-plan.md (實施計劃)
   - 建立 04-progress.md (進度追蹤)

2. 確認規劃文檔
   - 閱讀 claudedocs/1-planning/epics/epic-X/[相關文檔]
   - 閱讀 claudedocs/2-sprints/epic-X/sprint-X/[相關文檔]
   - 確認驗收標準

3. 系統化開發
   - 後端: 數據模型 → API → 測試
   - 前端: 組件 → 頁面 → 整合
   - 使用 TodoWrite 追蹤進度

4. 遵循最佳實踐
   - 參考現有實現模式
   - 使用 shadcn/ui 組件
   - I18N 從一開始實施
   - 撰寫單元測試

5. 記錄開發過程
   - 更新 04-progress.md
   - 記錄技術決策
   - 更新 Sprint checklist

請用中文溝通。
```

---

## 🤖 AI 執行流程

### Phase 0: 規劃準備 (必須先執行)

```bash
# 1. 確認功能編號（查看現有 FEAT 編號）
Bash: ls claudedocs/1-planning/features/

# 2. 建立功能目錄結構
Bash: mkdir -p claudedocs/1-planning/features/FEAT-XXX-功能名稱

# 3. 建立規劃文檔
Write: claudedocs/1-planning/features/FEAT-XXX-功能名稱/01-requirements.md
Write: claudedocs/1-planning/features/FEAT-XXX-功能名稱/02-technical-design.md
Write: claudedocs/1-planning/features/FEAT-XXX-功能名稱/03-implementation-plan.md
Write: claudedocs/1-planning/features/FEAT-XXX-功能名稱/04-progress.md
```

**功能目錄結構範例：**
```
claudedocs/1-planning/features/
├── FEAT-001-project-fields-enhancement/
│   ├── 01-requirements.md      # 需求規格
│   ├── 02-technical-design.md  # 技術設計
│   ├── 03-implementation-plan.md # 實施計劃
│   └── 04-progress.md          # 進度追蹤
├── FEAT-002-currency-system-expansion/
│   └── ...
└── FEAT-003-om-summary-page/   # 新功能
    └── ...
```

**文檔內容指引：**

| 文檔 | 內容 |
|------|------|
| `01-requirements.md` | 功能概述、用戶需求、功能需求、驗收標準 |
| `02-technical-design.md` | 數據模型、API 設計、組件設計、技術架構 |
| `03-implementation-plan.md` | 開發階段、任務分解、時間估算、依賴關係 |
| `04-progress.md` | 開發日誌、完成狀態、問題記錄、測試結果 |

---

### Phase 1: 後端開發
```bash
# 1. 數據模型（如需新增或修改）
Edit: packages/db/prisma/schema.prisma
Bash: pnpm db:generate
Bash: pnpm db:migrate

# 2. API Router
Write: packages/api/src/routers/新功能.ts
Edit: packages/api/src/root.ts (合併 router)

# 3. API 測試
Write: packages/api/src/routers/新功能.test.ts
Bash: pnpm test --filter=api

# 4. 更新進度
Edit: claudedocs/1-planning/features/FEAT-XXX/04-progress.md
TodoWrite: 標記後端任務完成
```

### Phase 2: 前端開發
```bash
# 1. 組件開發
Write: apps/web/src/components/新功能/NewComponent.tsx

# 2. 頁面開發
Write: apps/web/src/app/[locale]/新功能/page.tsx

# 3. I18N
Edit: apps/web/src/messages/zh-TW.json
Edit: apps/web/src/messages/en.json

# 4. 測試
Bash: pnpm dev (手動測試)

# 5. 更新進度
Edit: claudedocs/1-planning/features/FEAT-XXX/04-progress.md
TodoWrite: 標記前端任務完成
```

### Phase 3: 整合測試
```bash
# 1. E2E 測試
Write: tests/e2e/新功能.spec.ts

# 2. 運行測試
Bash: pnpm test:e2e

# 3. 記錄測試結果
Edit: claudedocs/1-planning/features/FEAT-XXX/04-progress.md
Write: claudedocs/5-status/testing/e2e/E2E-新功能-REPORT.md
```

---

## 📐 開發標準 Checklist

### 規劃階段
- [ ] 功能目錄已建立 (FEAT-XXX-功能名稱/)
- [ ] 01-requirements.md 已完成
- [ ] 02-technical-design.md 已完成
- [ ] 03-implementation-plan.md 已完成
- [ ] 04-progress.md 已初始化

### 後端標準
- [ ] Prisma 模型遵循命名規範
- [ ] API 使用 Zod 驗證
- [ ] 使用 protectedProcedure 保護路由
- [ ] 錯誤處理完整
- [ ] 單元測試覆蓋率 >80%

### 前端標準
- [ ] 使用 TypeScript 嚴格模式
- [ ] 使用 shadcn/ui 組件
- [ ] 實施 I18N (繁中 + 英文)
- [ ] 響應式設計 (mobile-first)
- [ ] 無障礙性 (WCAG 2.1 AA)
- [ ] Loading 和 Error 狀態處理

### 代碼品質
- [ ] ESLint 無錯誤
- [ ] TypeScript 無錯誤
- [ ] 格式化 (Prettier)
- [ ] 註解完整 (複雜邏輯)

### 部署準備 (如需 Azure 部署)
- [ ] 本地測試通過
- [ ] 環境變數確認 (新增變數已加入 Key Vault)
- [ ] Azure 環境配置已確認
- [ ] 部署指引已閱讀 (SITUATION-6 或 SITUATION-7)

---

## 📁 功能文檔模板

### 01-requirements.md 模板
```markdown
# FEAT-XXX: [功能名稱]

> **建立日期**: YYYY-MM-DD
> **狀態**: 📋 設計中 / 🚧 開發中 / ✅ 完成
> **優先級**: High / Medium / Low

## 1. 功能概述
### 1.1 背景
### 1.2 目標

## 2. 功能需求
### 2.1 用戶故事
### 2.2 功能列表

## 3. 驗收標準
### 3.1 功能驗收
### 3.2 技術驗收
### 3.3 用戶體驗

## 4. 相關文檔
```

### 04-progress.md 模板
```markdown
# FEAT-XXX: [功能名稱] - 開發進度

## 📊 整體進度
- [ ] Phase 0: 規劃準備
- [ ] Phase 1: 後端開發
- [ ] Phase 2: 前端開發
- [ ] Phase 3: 整合測試

## 📝 開發日誌

### YYYY-MM-DD
- 完成項目:
- 遇到問題:
- 下一步:

## 🐛 問題追蹤
| 問題 | 狀態 | 解決方案 |
|------|------|----------|

## ✅ 測試結果
```

---

## 🔗 相關文檔

### 開發流程指引
- [情況1: 專案入門](./SITUATION-1-PROJECT-ONBOARDING.md)
- [情況2: 開發前準備](./SITUATION-2-FEATURE-DEV-PREP.md)
- [情況3: 舊功能進階/修正](./SITUATION-3-FEATURE-ENHANCEMENT.md)
- [情況5: 保存進度](./SITUATION-5-SAVE-PROGRESS.md)

### Azure 部署指引 (新功能需部署測試時)
- [情況6: Azure 個人環境部署](./SITUATION-6-AZURE-DEPLOY-PERSONAL.md)
- [情況7: Azure 公司環境部署](./SITUATION-7-AZURE-DEPLOY-COMPANY.md)
- [情況8: Azure 個人環境問題排查](./SITUATION-8-AZURE-TROUBLESHOOT-PERSONAL.md)
- [情況9: Azure 公司環境問題排查](./SITUATION-9-AZURE-TROUBLESHOOT-COMPANY.md)

### 現有功能範例
- [FEAT-001: Project Fields Enhancement](../../1-planning/features/FEAT-001-project-fields-enhancement/)
- [FEAT-002: Currency System Expansion](../../1-planning/features/FEAT-002-currency-system-expansion/)

**最後更新**: 2025-11-29
**版本**: 1.2
