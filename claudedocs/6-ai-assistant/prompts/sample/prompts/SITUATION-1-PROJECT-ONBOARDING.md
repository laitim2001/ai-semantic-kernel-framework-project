# 🚀 情況1: 專案入門 - 開發人員重新開始開發活動

> **使用時機**: 新對話開始前,開發人員需要快速了解專案
> **目標**: 讓 AI 助手在 5 分鐘內理解專案全貌
> **適用場景**: 新開發者、長時間未接觸專案、會話重啟

---

## 📋 Prompt 模板 (給開發人員)

```markdown
你好!我需要你幫我快速了解這個專案。

這是一個 IT 專案管理平台,我需要你:

1. 閱讀專案概覽
   - 請先閱讀 `README.md` 了解專案基本資訊
   - 閱讀 `CLAUDE.md` 了解開發指南
   - 閱讀 `claudedocs/1-planning/roadmap/MASTER-ROADMAP.md` 了解開發路線圖

2. 理解專案結構
   - 閱讀 `PROJECT-INDEX.md` 了解文件組織
   - 查看 `apps/web/src/app/[locale]/` 了解頁面結構
   - 查看 `packages/api/src/routers/` 了解 API 結構

3. 確認當前狀態
   - 檢查 Git 狀態: `git status` 和 `git log --oneline -10`
   - 閱讀 `claudedocs/3-progress/weekly/` 最新的每週進度
   - 閱讀 `DEVELOPMENT-LOG.md` 和 `FIXLOG.md` 了解最近的變更

4. 總結並回答
   - 這個專案是做什麼的?
   - 當前開發到哪個階段?
   - 最近完成了什麼功能?
   - 有沒有進行中的任務?
   - 技術棧是什麼?

請用中文回答,並保持簡潔。
```

---

## 🤖 AI 助手執行步驟

### Step 1: 快速理解專案 (2 分鐘)

```bash
# 1. 讀取核心文檔
Read: README.md (專案總覽)
Read: CLAUDE.md (開發指南)
Read: claudedocs/1-planning/roadmap/MASTER-ROADMAP.md (路線圖)

# 2. 檢查 Git 狀態
Bash: git status
Bash: git log --oneline -10
Bash: git branch

# 3. 讀取最新進度
Read: claudedocs/3-progress/weekly/2025-W45.md (如果存在)
Read: DEVELOPMENT-LOG.md (最後 200 行)
```

### Step 2: 理解項目結構 (2 分鐘)

```bash
# 1. 讀取項目索引
Read: PROJECT-INDEX.md (了解文件組織)

# 2. 快速掃描目錄結構
Bash: ls -la apps/web/src/app/[locale]/
Bash: ls -la packages/api/src/routers/
Bash: ls -la packages/db/prisma/

# 3. 檢查 package.json
Read: package.json (了解依賴和腳本)
```

### Step 3: 生成總結報告 (1 分鐘)

```markdown
# 📊 專案入門總結

## 專案概覽
- **名稱**: IT Project Process Management Platform
- **目標**: 統一化 IT 部門專案流程管理
- **技術棧**: Next.js 14 + tRPC + Prisma + PostgreSQL + Azure
- **開發模式**: Turborepo Monorepo

## 當前狀態
- **階段**: Post-MVP 完成 + Azure 部署架構完成,準備 Epic 9-10
- **完成度**: Epic 1-8 (100%), Azure 部署 (100%), Epic 9-10 (規劃中)
- **最新分支**: main
- **最後提交**: [commit message]

## 最近完成
- ✅ **Azure 部署架構重組** (2025-11-24): 43+ 個文件,4 層架構,6 個自動化腳本
- ✅ **FEAT-001 專案欄位擴展** (2025-11-17): Phase 1-6 完成,貨幣管理功能
- ✅ FIX-088~095: 系統性修復 (deprecated fields cleanup, API 優化)
- ✅ FIX-081~087: 搜尋/過濾/語言切換系統性修復
- ✅ claudedocs V2.0 流程導向重組
- ✅ 設計系統遷移完成
- ✅ I18N 實施完成 (繁中 + 英文)

## 進行中任務
- ⏳ [檢查 3-progress/weekly/ 或 2-sprints/]
- ⏳ [如果沒有,回答: 無進行中任務]

## 快速導航
- **文檔**: docs/, claudedocs/
- **前端**: apps/web/src/
- **API**: packages/api/src/
- **數據庫**: packages/db/prisma/
- **認證**: packages/auth/
- **Azure 部署**: azure/, docs/deployment/
- **AI 助手指引**: claudedocs/6-ai-assistant/prompts/

## 下一步建議
1. 檢查是否有 TODO 或 FIXME 註解
2. 運行 `pnpm dev` 啟動開發服務器
3. 檢查 `pnpm check:env` 確認環境配置
4. 閱讀 MASTER-ROADMAP.md 了解 Epic 9-10 規劃
5. 若需 Azure 部署,閱讀 `azure/README.md` 和 SITUATION-6/7 指引
```

---

## ✅ 驗收標準

AI 助手應該能回答以下問題:

1. **專案是什麼?**
   - IT 專案管理平台,統一化流程管理

2. **當前階段?**
   - Post-MVP 完成,準備 Epic 9-10 (AI Assistant + External Integration)

3. **最近完成?**
   - FIX-081~087, claudedocs V2.0 重組, 設計系統遷移, I18N 實施

4. **進行中任務?**
   - 檢查 3-progress/weekly/ 或 2-sprints/

5. **技術棧?**
   - Next.js 14, tRPC, Prisma, PostgreSQL, Azure AD B2C, shadcn/ui

6. **如何啟動?**
   - `pnpm install` → `pnpm dev`

7. **Azure 部署?**
   - 參考 SITUATION-6 (個人環境) 或 SITUATION-7 (公司環境)
   - 入口文檔: `azure/README.md`

---

## 📚 推薦閱讀順序 (深入了解)

### 新開發者 (Day 1)
1. README.md - 專案總覽
2. CLAUDE.md - 開發指南
3. DEVELOPMENT-SETUP.md - 環境設置
4. claudedocs/1-planning/roadmap/MASTER-ROADMAP.md - 路線圖

### 新開發者 (Day 2-3)
1. docs/fullstack-architecture/ - 技術架構
2. docs/prd/ - 產品需求
3. docs/stories/ - 用戶故事
4. PROJECT-INDEX.md - 文件索引

### 新開發者 (Week 2)
1. packages/db/prisma/schema.prisma - 數據模型
2. packages/api/src/routers/ - API 設計
3. apps/web/src/components/ - 組件庫
4. claudedocs/4-changes/bug-fixes/ - Bug 修復歷史

### Azure 部署 (按需)
1. azure/README.md - Azure 部署入口
2. SITUATION-6-AZURE-DEPLOY-PERSONAL.md - 個人環境部署指引
3. SITUATION-7-AZURE-DEPLOY-COMPANY.md - 公司環境部署指引
4. docs/deployment/ - 完整部署文檔
5. claudedocs/AZURE-DEPLOYMENT-FILE-STRUCTURE-GUIDE.md - 文件結構指引

---

## 🔗 相關文檔

### 開發流程指引
- [情況2: 開發新功能/修復前準備](./SITUATION-2-FEATURE-DEV-PREP.md)
- [情況3: 舊功能進階/修正](./SITUATION-3-FEATURE-ENHANCEMENT.md)
- [情況4: 新功能開發](./SITUATION-4-NEW-FEATURE-DEV.md)
- [情況5: 保存進度](./SITUATION-5-SAVE-PROGRESS.md)
- [AI 助手會話指引](../session-guides/START-NEW-EPIC.md)

### Azure 部署指引
- [情況6: Azure 個人環境部署](./SITUATION-6-AZURE-DEPLOY-PERSONAL.md)
- [情況7: Azure 公司環境部署](./SITUATION-7-AZURE-DEPLOY-COMPANY.md)
- [情況8: Azure 個人環境問題排查](./SITUATION-8-AZURE-TROUBLESHOOT-PERSONAL.md)
- [情況9: Azure 公司環境問題排查](./SITUATION-9-AZURE-TROUBLESHOOT-COMPANY.md)

---

**維護者**: AI 助手 + 開發團隊
**最後更新**: 2025-11-25
**版本**: 1.1
