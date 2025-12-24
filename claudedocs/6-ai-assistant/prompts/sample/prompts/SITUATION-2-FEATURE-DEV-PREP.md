# 🔧 情況2: 開發新功能/修復前準備

> **使用時機**: 準備開發新功能或修復舊功能前
> **目標**: 驗證架構支援,制定實施計劃
> **適用場景**: 開始 Sprint, 接到新任務, 設計階段

---

## 📋 Prompt 模板

```markdown
我需要 [開發新功能 / 修復舊功能]: [功能/Bug 描述]

請幫我:

1. 快速回顧專案現況
   - 閱讀 `claudedocs/1-planning/roadmap/MASTER-ROADMAP.md`
   - 檢查當前 Git 分支和最近提交
   - 閱讀最新的每週進度報告

2. 驗證架構支援
   - 閱讀 `docs/fullstack-architecture/5-data-model-and-prisma-schema.md`
   - 檢查 `packages/db/prisma/schema.prisma` 相關數據模型
   - 檢查 `packages/api/src/routers/` 相關 API
   - 檢查 `apps/web/src/app/[locale]/` 相關頁面

3. 制定實施計劃
   - 識別需要修改的文件
   - 評估架構變更需求
   - 列出前置任務和依賴
   - 估算工作量

4. 創建任務清單
   - 使用 TodoWrite 創建任務清單
   - 分解為可執行的小任務
   - 標註優先級和依賴關係

請用中文回答。
```

---

## 🤖 AI 執行步驟

### 階段 1: 理解需求 (3 分鐘)
```bash
# 讀取相關文檔
Read: claudedocs/1-planning/roadmap/MASTER-ROADMAP.md
Read: docs/stories/epic-X/story-X.X-*.md (如果是 Epic 任務)
Read: claudedocs/3-progress/weekly/最新.md

# 檢查 Git 狀態
Bash: git status
Bash: git log --oneline -5
```

### 階段 2: 驗證架構 (5 分鐘)
```bash
# 檢查數據模型
Read: packages/db/prisma/schema.prisma

# 檢查相關 API
Grep: pattern="相關關鍵字" path="packages/api/src/routers/"

# 檢查相關頁面/組件
Glob: pattern="**/[相關名稱]*.tsx"
Read: [找到的相關文件]
```

### 階段 3: 制定計劃 (5 分鐘)
```markdown
# 實施計劃

## 需求分析
- **功能**: [描述]
- **用戶故事**: [如果有]
- **驗收標準**: [列出]

## 架構評估
- **數據模型**: ✅ 支援 / ⚠️ 需修改 / ❌ 需新增
- **API**: ✅ 可用 / ⚠️ 需擴展 / ❌ 需新增
- **前端組件**: ✅ 可重用 / ⚠️ 需調整 / ❌ 需新建
- **部署環境**: ✅ 本地開發 / ⚠️ 需 Azure 環境配置 / ⚠️ 需更新環境變數

## 文件變更清單
### 後端
- [ ] `packages/db/prisma/schema.prisma` - [變更描述]
- [ ] `packages/api/src/routers/xxx.ts` - [變更描述]

### 前端
- [ ] `apps/web/src/app/[locale]/xxx/page.tsx` - [變更描述]
- [ ] `apps/web/src/components/xxx/` - [變更描述]

### 測試
- [ ] `xxx.test.ts` - [測試計劃]

## 工作量估算
- **後端開發**: X 小時
- **前端開發**: X 小時
- **測試**: X 小時
- **總計**: X 小時 (~X 天)

## 風險評估
- ⚠️ [識別的風險] → [緩解措施]

## Azure 部署考量 (如需要)
- **環境**: 個人環境 / 公司環境
- **部署指引**: 參考 SITUATION-6 或 SITUATION-7
- **環境變數**: 確認 Key Vault 已配置新增變數
```

---

## 🔗 相關文檔

### 開發流程指引
- [情況1: 專案入門](./SITUATION-1-PROJECT-ONBOARDING.md)
- [情況3: 舊功能進階/修正](./SITUATION-3-FEATURE-ENHANCEMENT.md)
- [情況4: 新功能開發](./SITUATION-4-NEW-FEATURE-DEV.md)
- [情況5: 保存進度](./SITUATION-5-SAVE-PROGRESS.md)

### Azure 部署指引
- [情況6: Azure 個人環境部署](./SITUATION-6-AZURE-DEPLOY-PERSONAL.md)
- [情況7: Azure 公司環境部署](./SITUATION-7-AZURE-DEPLOY-COMPANY.md)
- [情況8: Azure 個人環境問題排查](./SITUATION-8-AZURE-TROUBLESHOOT-PERSONAL.md)
- [情況9: Azure 公司環境問題排查](./SITUATION-9-AZURE-TROUBLESHOOT-COMPANY.md)

**最後更新**: 2025-11-25
**版本**: 1.1
