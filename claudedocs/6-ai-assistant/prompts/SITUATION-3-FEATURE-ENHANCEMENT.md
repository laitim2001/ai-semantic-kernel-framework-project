# 🔄 情況3: 舊功能進階/修正開發

> **使用時機**: 對話進行中，正在開發舊功能的進階或修正
> **目標**: 保持開發流程順暢，及時記錄變更
> **適用場景**: Bug 修復、功能增強、代碼重構

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
   - 每完成一項，更新 TodoWrite 狀態
   - 遇到問題時記錄到 claudedocs/4-changes/

3. 測試驗證
   - 運行相關測試
   - 手動測試功能
   - 記錄測試結果

4. 記錄變更
   - Bug 修復: 記錄到 claudedocs/4-changes/bug-fixes/FIX-XXX.md
   - 功能增強: 記錄到 claudedocs/4-changes/feature-changes/CHANGE-XXX.md

請保持中文溝通。
```

---

## 🤖 AI 執行模式

### 模式A: Bug 修復流程

**適用場景**: 發現 Bug 或錯誤需要修復時

#### Step 1: 問題定位 (2 分鐘)

```bash
# 1. 根據錯誤訊息搜尋相關代碼
Grep: "錯誤關鍵字" backend/src/

# 2. 定位問題文件
Read: 相關文件的錯誤行附近代碼

# 3. 檢查相關日誌 (如適用)
Bash: docker-compose logs backend --tail=100
```

#### Step 2: 根因分析 (3 分鐘)

```markdown
# 🔍 問題分析報告

## 問題摘要
- **現象**: [問題描述]
- **位置**: [file:line]
- **影響**: [影響範圍]

## 根因分析
1. **直接原因**: [代碼層面的問題]
2. **深層原因**: [設計或邏輯問題]

## 相關代碼
[相關代碼片段]

## 修復方案
- **方案 A**: [描述] - 優點/缺點
- **方案 B**: [描述] - 優點/缺點 (如適用)
```

#### Step 3: 實施修復 (5 分鐘)

```bash
# 1. 創建修復分支 (如需要)
Bash: git checkout -b fix/問題簡述

# 2. 修改代碼
Edit: 修復問題代碼

# 3. 添加測試
Write: backend/tests/unit/test_xxx.py (針對這個 bug 的測試)

# 4. 運行測試
Bash: cd backend && pytest tests/unit/test_xxx.py -v
```

#### Step 4: 驗證修復 (2 分鐘)

```bash
# 1. 運行相關測試
Bash: cd backend && pytest tests/unit/{相關模組}/ -v --tb=short

# 2. 運行代碼品質檢查
Bash: cd backend && black . && isort . && flake8 src/

# 3. 手動驗證 (如適用)
Bash: curl http://localhost:8000/api/v1/...
```

---

### 模式B: 功能增強流程

**適用場景**: 需要修改、更新或增強現有功能時

#### Step 1: 理解現有實作 (3 分鐘)

```bash
# 1. 定位相關文件
Grep: "[功能關鍵字]" backend/src/
Glob: backend/src/**/*[相關名稱]*.py

# 2. 閱讀核心代碼
Read: [主要實作文件]
Read: [相關的 service/repository 文件]

# 3. 了解依賴關係
Grep: "from.*import.*[功能類名]" backend/src/

# 4. 查看現有測試
Glob: backend/tests/**/*[功能名稱]*.py
```

#### Step 2: 分析影響範圍 (2 分鐘)

```markdown
# 📊 影響範圍分析

## 直接影響的文件
| 文件 | 類型 | 修改內容 |
|------|------|----------|
| `path/to/file.py` | Service | [需要修改的部分] |
| `path/to/api.py` | API | [需要修改的部分] |

## 間接影響的文件
- `other/file.py` - 依賴此功能的文件

## 相關測試
- `tests/unit/test_xxx.py` - 需要更新的測試

## 風險評估
- 🟢 低風險: [安全的修改]
- 🟡 中風險: [需要注意的修改]
- 🔴 高風險: [可能破壞的部分]
```

#### Step 3: 執行修改 (主要時間)

```bash
# 1. 創建備份點
Bash: git status
Bash: git add . && git commit -m "chore: checkpoint before feature update"

# 2. 修改代碼
Edit: [文件路徑] - 按計劃修改

# 3. 更新相關文件
Edit: [其他需要修改的文件]

# 4. 更新測試
Edit: [測試文件] - 添加/修改測試案例
```

#### Step 4: 驗證修改 (3 分鐘)

```bash
# 1. 運行相關測試
Bash: cd backend && pytest tests/unit/[相關測試目錄]/ -v --tb=short

# 2. 運行完整測試套件 (如時間允許)
Bash: cd backend && pytest tests/unit/ -v --tb=short -x

# 3. 檢查類型
Bash: cd backend && mypy src/domain/{module}/ src/api/v1/{module}/

# 4. 檢查代碼風格
Bash: cd backend && flake8 src/domain/{module}/ src/api/v1/{module}/
```

---

### 模式C: 代碼重構流程

**適用場景**: 改善代碼結構但不改變外部行為

#### 重構原則

1. **確保行為不變**: 修改前後功能完全一致
2. **分小步驟進行**: 每步都可驗證和回滾
3. **每步都運行測試**: 確保沒有破壞現有功能
4. **先測量，後優化**: 性能優化需基於實際數據

#### 重構執行步驟

```bash
# 1. 確認測試全部通過
Bash: cd backend && pytest tests/unit/ -v --tb=short

# 2. 小步驟重構
Edit: [文件] - 單一小改動

# 3. 立即驗證
Bash: cd backend && pytest tests/unit/[相關測試]/ -v

# 4. 重複直到完成

# 5. 最終驗證
Bash: cd backend && pytest tests/ -v --tb=short
```

---

## 📝 變更記錄模板

### Bug 修復記錄 (FIX-XXX)

```markdown
# FIX-XXX: [Bug 簡述]

## 問題描述
[詳細描述問題，包括復現步驟]

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

### 功能增強記錄 (CHANGE-XXX)

```markdown
# CHANGE-XXX: [功能增強簡述]

## 變更概述
- **功能**: [功能名稱]
- **變更類型**: 增強 / 重構 / 優化 / API 更新
- **影響範圍**: [低/中/高]

## 變更內容
| 文件 | 變更類型 | 說明 |
|------|----------|------|
| `file1.py` | 修改 | [說明] |
| `file2.py` | 新增 | [說明] |

## 測試結果
- 單元測試: ✅ X 個通過
- 類型檢查: ✅ 通過
- 代碼風格: ✅ 通過

## 向後兼容性
- [x] 舊 API 仍可使用
- [x] 舊行為保持不變
- [ ] 需要遷移: [遷移說明]
```

---

## ⚠️ 常見陷阱

### 避免這些錯誤

1. **不先理解現有代碼就修改**
   - 先 Read，後 Edit

2. **修改範圍過大**
   - 分批次修改
   - 每次修改後運行測試

3. **忽略邊界情況**
   - 檢查現有測試覆蓋的場景
   - 思考新修改對邊界情況的影響

4. **破壞向後兼容**
   - 舊的調用方式應該仍然工作
   - 使用默認參數而非必填參數

---

## ✅ 驗收標準

AI 助手完成修改後應確認：

1. **理解充分**
   - 已閱讀相關代碼
   - 了解依賴關係

2. **修改安全**
   - 所有測試通過
   - 向後兼容性保持

3. **文檔更新**
   - 變更記錄完整
   - 相關文檔已更新 (如需要)

4. **代碼品質**
   - Black 格式化通過
   - Flake8 無錯誤

---

## 🔗 相關文檔

### 開發流程指引
- [情況1: 專案入門](./SITUATION-1-PROJECT-ONBOARDING.md)
- [情況2: 開發前準備](./SITUATION-2-FEATURE-DEV-PREP.md)
- [情況4: 新功能開發](./SITUATION-4-NEW-FEATURE-DEV.md)
- [情況5: 保存進度](./SITUATION-5-SAVE-PROGRESS.md)

### 品質規範
- `.claude/rules/code-quality.md` - 代碼品質規則
- `.claude/rules/testing.md` - 測試規則

---

**維護者**: AI 助手 + 開發團隊
**最後更新**: 2025-12-27
**版本**: 3.0
