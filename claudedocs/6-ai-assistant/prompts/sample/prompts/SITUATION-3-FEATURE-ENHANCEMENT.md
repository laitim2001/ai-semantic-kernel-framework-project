# 🔄 情況3: 舊功能進階/修正開發

> **使用時機**: 對話進行中,正在開發舊功能的進階或修正
> **目標**: 保持開發流程順暢,及時記錄變更
> **適用場景**: Bug 修復, 功能增強, 重構

---

## 📋 Prompt 模板

```markdown
我正在 [修復 Bug / 增強功能 / 重構代碼]: [具體描述]

當前狀態: [剛開始 / 進行中 / 測試階段 / 完成]

請幫我:

1. 檢查當前任務狀態
   - 查看 TodoWrite 任務清單
   - 確認已完成和待完成的項目

2. 執行開發任務
   - 根據任務清單逐項執行
   - 每完成一項,更新 TodoWrite 狀態
   - 遇到問題時記錄到 4-changes/bug-fixes/

3. 測試驗證
   - 運行相關測試
   - 手動測試功能
   - 記錄測試結果

4. 記錄變更
   - 更新 4-changes/[對應目錄]/FIX-XXX.md
   - 記錄問題、解決方案、影響範圍

請保持中文溝通。
```

---

## 🤖 AI 執行模式

### 模式A: Bug 修復流程
```bash
# 1. 理解問題
Read: [相關代碼文件]
Grep: [搜尋錯誤相關代碼]

# 2. 修復
Edit: [修改文件]
Bash: [運行測試]

# 3. 驗證
Bash: pnpm typecheck
Bash: pnpm lint

# 4. 記錄
Write: claudedocs/4-changes/bug-fixes/FIX-XXX-[描述].md

# 5. 更新 TodoWrite
TodoWrite: 標記已完成任務
```

### 模式B: 功能增強流程
```bash
# 1. 檢查現有實現
Read: [現有功能文件]
Grep: [搜尋相關模式]

# 2. 實施增強
Edit/Write: [修改或新增文件]

# 3. 測試
Bash: pnpm dev (檢查運行狀態)

# 4. 記錄
Write: claudedocs/4-changes/feature-changes/CHANGE-XXX-[描述].md

# 5. 更新進度
TodoWrite: 更新任務狀態
```

---

## 📝 變更記錄模板

### Bug 修復記錄
```markdown
# FIX-XXX: [Bug 簡述]

## 問題描述
[詳細描述問題,包括復現步驟]

## 根本原因
[分析根本原因]

## 解決方案
[描述解決方案]

## 影響範圍
### 修改文件
- `文件路徑` - [變更說明]

### 測試驗證
- ✅ [測試項目 1]
- ✅ [測試項目 2]

## 相關 Issue/Commit
- Issue: #XXX
- Commit: [commit hash]
```

---

## 🔗 相關文檔

### 開發流程指引
- [情況1: 專案入門](./SITUATION-1-PROJECT-ONBOARDING.md)
- [情況2: 開發前準備](./SITUATION-2-FEATURE-DEV-PREP.md)
- [情況4: 新功能開發](./SITUATION-4-NEW-FEATURE-DEV.md)
- [情況5: 保存進度](./SITUATION-5-SAVE-PROGRESS.md)

### Azure 部署指引 (如修復涉及 Azure 環境)
- [情況6: Azure 個人環境部署](./SITUATION-6-AZURE-DEPLOY-PERSONAL.md)
- [情況8: Azure 個人環境問題排查](./SITUATION-8-AZURE-TROUBLESHOOT-PERSONAL.md)
- [情況9: Azure 公司環境問題排查](./SITUATION-9-AZURE-TROUBLESHOOT-COMPANY.md)

**最後更新**: 2025-11-25
**版本**: 1.1
