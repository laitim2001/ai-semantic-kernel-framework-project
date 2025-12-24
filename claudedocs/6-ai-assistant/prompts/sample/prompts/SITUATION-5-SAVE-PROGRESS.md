# 💾 情況5: 保存現有進度

> **使用時機**: 對話進行中,需要保存當前工作進度
> **目標**: 完整記錄進度,更新文檔,同步 GitHub
> **適用場景**: 結束工作前, 里程碑達成, 定期檢查點

---

## 📋 Prompt 模板 (完整版)

```markdown
我需要保存當前的工作進度。

當前狀態: [開發功能中 / 規劃中 / 修復進行中 / 測試中]
工作內容: [簡述當前正在做什麼]

請幫我完成以下步驟:

## 1. 更新進度記錄
- 更新 `claudedocs/3-progress/weekly/2025-WXX.md` (本週進度)
- 如果有每日日誌,更新 `claudedocs/3-progress/daily/2025-MM/2025-MM-DD.md`
- 更新 `DEVELOPMENT-LOG.md` (添加今日變更)

## 2. 更新任務狀態
- 檢查 TodoWrite 任務清單
- 標記已完成的任務
- 添加新發現的任務
- 更新 Sprint checklist (如果有)

## 3. 執行索引維護
- 運行 `pnpm index:check` 檢查文件同步
- 運行 `pnpm index:check:incremental` 增量檢查（較快）
- 運行 `pnpm index:health` 完整健康檢查
- 如果需要,運行 `pnpm index:fix` 修復
- 手動檢查 `PROJECT-INDEX.md` 是否需要更新
- 參考: `INDEX-MAINTENANCE-GUIDE.md` 的 Azure 文件維護專項

## 3.5 Azure 文檔同步檢查 (如有 Azure 相關變更)
- 檢查 `azure/` 目錄文檔是否需要更新
- 檢查 `docs/deployment/` 是否需要更新
- 參考: `claudedocs/AZURE-DEPLOYMENT-FILE-STRUCTURE-GUIDE.md`
- 更新 AI 助手指引 (SITUATION-6~9) 如果部署流程有變更

## 4. 檢查代碼品質
- 運行 `pnpm typecheck` (TypeScript 檢查)
- 運行 `pnpm lint` (ESLint 檢查)
- 運行 `pnpm format:check` (格式檢查)

## 5. Git 提交和推送
- 檢查 `git status` 確認變更
- 使用有意義的 commit message
- 格式: `type(scope): 描述` (例如: `feat(api): 添加 AI 建議 API`)
- 執行 `git push origin main` (或當前分支)

## 6. 生成進度摘要
- 總結今日/本週完成的工作
- 列出遇到的挑戰和解決方案
- 記錄下次需要繼續的工作
- 標註需要關注的風險或問題

請用中文完成所有步驟,並提供詳細的執行記錄。
```

---

## 🤖 AI 完整執行流程

### Step 1: 更新進度記錄 (5 分鐘)

```bash
# 1. 檢查是否存在本週進度文件
Bash: ls -la claudedocs/3-progress/weekly/

# 2. 如果不存在,創建新文件
Write: claudedocs/3-progress/weekly/2025-W45.md
```

**每週進度模板**:
```markdown
# 2025-W45 每週進度 (11月4日 - 11月8日)

## 本週目標
- [列出本週計劃完成的目標]

## 完成情況
### 已完成
- ✅ [任務 1] - [簡述]
- ✅ [任務 2] - [簡述]

### 進行中
- ⏳ [任務 3] - [進度 XX%]

### 未開始
- ⏸️ [任務 4] - [原因]

## 遇到的挑戰
### 挑戰 1: [描述]
- **問題**: [詳細說明]
- **解決方案**: [如何解決]
- **學習**: [經驗總結]

## 技術決策
- **決策 1**: [描述] → [選擇的方案] → [理由]

## 下週計劃
- [ ] [任務 1]
- [ ] [任務 2]

## 風險提示
- ⚠️ [風險 1] - [緩解措施]

## 統計數據
- **代碼行數**: +XXX / -XXX
- **文件變更**: XX 個
- **Commits**: XX 次
- **工作時間**: XX 小時
```

```bash
# 3. 更新 DEVELOPMENT-LOG.md
Edit: DEVELOPMENT-LOG.md (添加今日記錄)
```

### Step 2: 更新任務狀態 (3 分鐘)

```bash
# 1. 檢查當前 TodoWrite 狀態
# (AI 助手內部檢查)

# 2. 更新 TodoWrite
TodoWrite: [更新所有任務狀態]

# 3. 如果有 Sprint checklist,更新
Edit: claudedocs/2-sprints/epic-X/sprint-X/checklist.md
```

### Step 3: 執行索引維護 (3 分鐘)

```bash
# 1. 快速檢查索引同步
Bash: pnpm index:check

# 2. 增量檢查（只檢查變更文件，較快）
Bash: pnpm index:check:incremental

# 3. 完整健康檢查（定期執行）
Bash: pnpm index:health

# 4. 如果有問題,嘗試自動修復
Bash: pnpm index:fix

# 5. 手動檢查 PROJECT-INDEX.md
Read: PROJECT-INDEX.md (檢查最後更新時間)

# 6. 如果需要,手動更新
Edit: PROJECT-INDEX.md (更新時間戳和新文件)
```

### Step 3.5: Azure 文檔同步檢查 (如有 Azure 相關變更)

```bash
# 1. 檢查 Azure 配置是否有變更
Bash: git diff --name-only | grep -E "^azure/|^docs/deployment/|^docker/"

# 2. 如果有變更,檢查對應文檔是否需要更新
Read: claudedocs/AZURE-DEPLOYMENT-FILE-STRUCTURE-GUIDE.md (了解 4 層架構)

# 3. 更新 AI 助手指引 (如部署流程有變更)
# - SITUATION-6: 個人環境部署
# - SITUATION-7: 公司環境部署
# - SITUATION-8: 個人環境問題排查
# - SITUATION-9: 公司環境問題排查

# 4. 更新環境變數文檔 (如有新增變數)
Edit: docs/deployment/environment-variables-map.md
Edit: azure/environments/personal/*.env.example
```

### Step 4: 檢查代碼品質 (3 分鐘)

```bash
# 1. TypeScript 檢查
Bash: pnpm typecheck

# 2. ESLint 檢查
Bash: pnpm lint

# 3. 格式檢查
Bash: pnpm format:check

# 4. 如果有錯誤,記錄問題
# (不一定要立即修復,但要記錄)
```

### Step 5: Git 提交和推送 (5 分鐘)

```bash
# 1. 檢查 Git 狀態
Bash: git status

# 2. 查看變更內容
Bash: git diff --stat

# 3. 添加文件
Bash: git add .

# 4. 提交 (使用 HEREDOC 格式)
Bash: git commit -m "$(cat <<'EOF'
type(scope): 簡短描述 (不超過 50 字)

詳細描述 (如果需要):
- 變更 1
- 變更 2
- 變更 3

相關 Issue/Epic:
- Epic 9 Story 9.1 開發中
- 修復 FIX-XXX

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

# 5. 推送到 GitHub
Bash: git push origin main

# 6. 確認推送成功
Bash: git log --oneline -1
```

### Step 6: 生成進度摘要 (5 分鐘)

```markdown
# 📊 進度保存摘要

## 時間
- **日期**: 2025-11-08
- **時間**: 14:30

## 工作內容
### 本次會話完成
- ✅ [完成項 1] - [詳細說明]
- ✅ [完成項 2] - [詳細說明]
- ⏳ [進行中項目] - [當前狀態]

### 代碼變更
- **新增文件**: XX 個
  - `file1.ts` - [用途]
  - `file2.tsx` - [用途]
- **修改文件**: XX 個
  - `file3.ts` - [變更內容]
- **刪除文件**: XX 個

### 測試狀態
- TypeScript: ✅ 通過
- ESLint: ✅ 通過
- 格式檢查: ✅ 通過
- 單元測試: ✅ XX/XX 通過

## 遇到的挑戰
### 挑戰 1: [描述]
- **問題**: [具體問題]
- **嘗試方案**: [方案 1], [方案 2]
- **最終解決**: [成功方案]
- **學習**: [經驗總結]

## 技術決策
- **決策**: [決策描述]
- **選項**: A) [選項A], B) [選項B]
- **選擇**: [選擇的方案]
- **理由**: [為什麼選擇]

## 下次繼續工作
### 待完成任務
- [ ] [任務 1] - [詳細說明]
- [ ] [任務 2] - [詳細說明]

### 前置準備
- [ ] [準備 1]
- [ ] [準備 2]

### 參考資料
- [文檔 1]: `path/to/doc1.md`
- [文檔 2]: `path/to/doc2.md`

## 風險提示
- ⚠️ [風險 1] - [影響] - [建議措施]
- ⚠️ [風險 2] - [影響] - [建議措施]

## Git 狀態
- **Branch**: main
- **Last Commit**: [commit hash]
- **Commit Message**: [message]
- **Pushed**: ✅ 已推送到 GitHub

## 文檔更新
- ✅ 每週進度報告已更新
- ✅ DEVELOPMENT-LOG.md 已更新
- ✅ PROJECT-INDEX.md 已檢查/更新
- ✅ Sprint checklist 已更新 (如果有)
- ✅ Azure 文檔已同步檢查 (如有相關變更)

## 下次開始前
**快速恢復指引**:
1. 閱讀本摘要
2. 閱讀 `claudedocs/3-progress/weekly/2025-WXX.md`
3. 檢查 TodoWrite 任務清單
4. 運行 `pnpm dev` 啟動開發環境
5. 繼續 [下次要做的具體任務]
```

---

## ✅ 驗收標準

保存進度完成後,應該確認:

### 文檔更新
- [ ] 每週進度報告存在且最新
- [ ] DEVELOPMENT-LOG.md 包含今日記錄
- [ ] PROJECT-INDEX.md 時間戳更新
- [ ] Sprint checklist 反映實際進度 (如果有)

### 代碼品質
- [ ] TypeScript 檢查通過
- [ ] ESLint 檢查通過 (或記錄已知問題)
- [ ] 格式檢查通過 (或已格式化)

### Git 狀態
- [ ] 所有變更已提交
- [ ] Commit message 清晰有意義
- [ ] 已推送到 GitHub
- [ ] 無未追蹤的重要文件

### 進度摘要
- [ ] 生成完整的進度摘要
- [ ] 記錄所有挑戰和解決方案
- [ ] 列出下次繼續工作的清單
- [ ] 標註風險和注意事項

---

## 🔄 定期保存頻率建議

### 每日保存 (推薦)
- **時機**: 每天工作結束前
- **內容**: 快速保存,更新每日日誌
- **時間**: 10-15 分鐘

### 每週保存 (必須)
- **時機**: 每週五下午
- **內容**: 完整保存,生成每週報告
- **時間**: 20-30 分鐘

### 里程碑保存 (重要)
- **時機**: Sprint 結束, Story 完成, Epic 完成
- **內容**: 全面保存,生成階段報告
- **時間**: 30-60 分鐘

### 緊急保存 (特殊)
- **時機**: 長時間未保存 (>4 小時), 重大變更前
- **內容**: 快速保存,防止丟失
- **時間**: 5-10 分鐘

---

## 📱 快速保存 (簡化版)

**給開發人員的快速 Prompt**:

```markdown
快速保存進度:
1. 更新本週進度
2. Git 提交和推送
3. 生成簡短摘要
4. 檢查 Azure 配置同步 (如有變更)

當前工作: [一句話描述]
```

---

## 🔗 相關文檔

### 開發流程指引
- [情況1: 專案入門](./SITUATION-1-PROJECT-ONBOARDING.md)
- [情況2: 開發前準備](./SITUATION-2-FEATURE-DEV-PREP.md)
- [情況3: 舊功能進階](./SITUATION-3-FEATURE-ENHANCEMENT.md)
- [情況4: 新功能開發](./SITUATION-4-NEW-FEATURE-DEV.md)

### Azure 部署指引
- [情況6: Azure 個人環境部署](./SITUATION-6-AZURE-DEPLOY-PERSONAL.md)
- [情況7: Azure 公司環境部署](./SITUATION-7-AZURE-DEPLOY-COMPANY.md)
- [情況8: Azure 個人環境問題排查](./SITUATION-8-AZURE-TROUBLESHOOT-PERSONAL.md)
- [情況9: Azure 公司環境問題排查](./SITUATION-9-AZURE-TROUBLESHOOT-COMPANY.md)

### 索引和文檔維護
- [INDEX-MAINTENANCE-GUIDE.md](../../../INDEX-MAINTENANCE-GUIDE.md) - 索引維護策略
- [AZURE-DEPLOYMENT-FILE-STRUCTURE-GUIDE.md](../../AZURE-DEPLOYMENT-FILE-STRUCTURE-GUIDE.md) - Azure 文件結構

---

**維護者**: AI 助手 + 開發團隊
**最後更新**: 2025-11-25
**版本**: 1.1
