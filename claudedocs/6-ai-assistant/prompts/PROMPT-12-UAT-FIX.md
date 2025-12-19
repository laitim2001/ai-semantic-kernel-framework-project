# PROMPT-12: UAT FIX
# UAT 問題修復記錄

> **用途**: 記錄問題修復過程和驗證結果
> **變數**: `{ISSUE_ID}`
> **預估時間**: 10-30 分鐘
> **版本**: v1.0.0

---

## 變數定義

```yaml
{ISSUE_ID}:
  描述: 要修復的問題 ID
  格式: "ISSUE-NNN"
  範例: "ISSUE-001", "ISSUE-015"
```

---

## 執行步驟

### Step 1: 讀取問題詳情

```yaml
讀取文件: claudedocs/uat/issues/{ISSUE_ID}.md
獲取信息:
  - 問題描述
  - 重現步驟
  - 嚴重程度
  - 相關代碼位置
```

### Step 2: 分析問題原因

```yaml
分析項目:
  - 錯誤訊息解讀
  - 代碼審查
  - API 日誌檢查
  - 前端 Console 檢查

輸出:
  - 根本原因分析
  - 影響範圍評估
  - 修復方案建議
```

### Step 3: 執行修復

```yaml
修復流程:
  1. 確認修復方案
  2. 修改相關代碼
  3. 本地驗證
  4. 提交代碼

記錄項目:
  - 修改的文件清單
  - 修改內容摘要
  - Git commit 信息
```

### Step 4: 生成 Fix 記錄

```yaml
生成文件: claudedocs/uat/fixes/FIX-{NNN}.md
內容:
  - 關聯的 Issue ID
  - 修復方案描述
  - 修改的文件
  - 驗證步驟
```

### Step 5: 驗證修復

```yaml
驗證步驟:
  1. 按原重現步驟測試
  2. 確認問題已解決
  3. 確認無副作用
  4. 回歸測試相關功能

驗證結果:
  - 通過: 更新 Issue 狀態為 "已修復"
  - 失敗: 記錄原因，重新修復
```

### Step 6: 更新追蹤文件

```yaml
更新項目:
  - Issue 文件狀態
  - UAT-MASTER-LOG.md 修復記錄
  - UAT-MASTER-LOG.md 問題統計
```

---

## 輸出格式

### Fix 文件模板

```markdown
# FIX-{NNN}: {修復標題}

> **建立日期**: {YYYY-MM-DD HH:MM}
> **關聯 Issue**: {ISSUE_ID}
> **修復者**: AI Assistant
> **驗證狀態**: 待驗證 | 已驗證 | 驗證失敗

---

## 問題摘要

**Issue**: {ISSUE_ID} - {Issue 標題}
**嚴重程度**: {SEVERITY}
**模組**: {MODULE}

---

## 根本原因分析

{問題根本原因的詳細分析}

---

## 修復方案

{修復方案的詳細描述}

---

## 修改的文件

| 文件 | 變更類型 | 說明 |
|------|----------|------|
| `{file_path}` | 修改 | {變更說明} |
| `{file_path}` | 新增 | {變更說明} |

---

## 代碼變更摘要

### {file_path}

```diff
- {舊代碼}
+ {新代碼}
```

---

## Git Commit

```
{commit_type}({scope}): {commit_message}

Fixes: {ISSUE_ID}

Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## 驗證步驟

1. [ ] {驗證步驟 1}
2. [ ] {驗證步驟 2}
3. [ ] {驗證步驟 3}
4. [ ] 確認無副作用
5. [ ] 回歸測試通過

---

## 驗證結果

**狀態**: 待驗證 | 已驗證 | 驗證失敗
**驗證時間**: -
**驗證者**: -
**備註**: -

---

## 狀態歷史

| 日期 | 狀態變更 | 備註 |
|------|----------|------|
| {DATE} | 建立 | 初始修復記錄 |
```

### 控制台輸出

```markdown
# 問題修復完成

**Fix ID**: FIX-001
**關聯 Issue**: ISSUE-001
**修復者**: AI Assistant

---

## 修復摘要

**問題**: {Issue 標題}
**根因**: {根本原因簡述}
**方案**: {修復方案簡述}

---

## 修改的文件

- `backend/src/api/v1/dashboard/routes.py` (修改)
- `frontend/src/pages/Dashboard.tsx` (修改)

---

## Git Commit

```
fix(dashboard): resolve statistics loading issue

Fixes: ISSUE-001
```

---

## 驗證步驟

請按以下步驟驗證修復:

1. 重新載入 Dashboard 頁面
2. 確認統計數據正常顯示
3. 測試刷新功能
4. 確認無 Console 錯誤

---

## 後續行動

驗證通過後:
> "@PROMPT-12-UAT-FIX.md verify ISSUE-001"

驗證失敗:
> 描述失敗原因，AI 將重新分析

---

**文件已創建**:
- Fix 記錄: `claudedocs/uat/fixes/FIX-001.md`
- Issue 已更新: `claudedocs/uat/issues/ISSUE-001.md`
```

---

## 使用範例

### 範例 1: 修復單一問題

```bash
用戶: "@PROMPT-12-UAT-FIX.md ISSUE-001"

AI 執行:
1. 讀取 ISSUE-001 詳情
2. 分析問題原因
3. 提出修復方案
4. 執行修復
5. 創建 Fix 記錄
6. 提供驗證步驟

輸出: 修復完成報告
```

### 範例 2: 驗證修復結果

```bash
用戶: "@PROMPT-12-UAT-FIX.md verify ISSUE-001"

AI 執行:
1. 讀取 Fix 記錄
2. 確認驗證結果
3. 更新 Issue 狀態
4. 更新 Master Log

輸出: 驗證結果確認
```

### 範例 3: 修復失敗重試

```bash
用戶: "ISSUE-001 修復後問題仍然存在，錯誤訊息是 xxx"

AI 執行:
1. 分析新的錯誤訊息
2. 更新根因分析
3. 提出新的修復方案
4. 執行第二次修復

輸出: 重新修復報告
```

---

## 修復優先級指引

| Issue 嚴重程度 | 修復優先級 | 建議時間 |
|---------------|------------|----------|
| Critical | P0 | 立即處理 |
| High | P1 | 當天完成 |
| Medium | P2 | 3 天內 |
| Low | P3 | 下個迭代 |

---

## 驗證狀態定義

| 狀態 | 定義 | 後續行動 |
|------|------|----------|
| **待驗證** | 修復完成，等待驗證 | 執行驗證步驟 |
| **已驗證** | 驗證通過，問題已解決 | 關閉 Issue |
| **驗證失敗** | 問題仍存在 | 重新分析和修復 |

---

## 相關文檔

- [UAT Master Log](../../uat/UAT-MASTER-LOG.md)
- [PROMPT-10: UAT Session](./PROMPT-10-UAT-SESSION.md)
- [PROMPT-11: UAT Issue](./PROMPT-11-UAT-ISSUE.md)

---

**版本**: v1.0.0
**建立日期**: 2025-12-09
