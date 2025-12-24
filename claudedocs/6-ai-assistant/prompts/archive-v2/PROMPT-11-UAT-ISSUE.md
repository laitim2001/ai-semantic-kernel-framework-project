# PROMPT-11: UAT ISSUE
# UAT 問題記錄

> **用途**: 記錄 UAT 測試中發現的問題
> **變數**: `{MODULE}`, `{DESCRIPTION}`
> **預估時間**: 3-5 分鐘
> **版本**: v1.0.0

---

## 變數定義

```yaml
{MODULE}:
  描述: 問題所在模組
  選項: "dashboard", "workflows", "agents", "executions", "templates", "analytics", "settings", "api", "other"

{DESCRIPTION}:
  描述: 問題簡短描述
  範例: "頁面載入錯誤", "按鈕無反應", "數據顯示不正確"
```

---

## 執行步驟

### Step 1: 生成 Issue ID

```yaml
格式: ISSUE-{NNN}
範例: ISSUE-001, ISSUE-002
來源: 遞增編號，從 UAT-MASTER-LOG.md 讀取最新編號
```

### Step 2: 收集問題詳情

```yaml
必填項:
  - 問題標題 (簡短描述)
  - 問題模組
  - 嚴重程度 (Critical/High/Medium/Low)
  - 重現步驟
  - 預期結果
  - 實際結果

選填項:
  - 截圖路徑
  - 錯誤訊息
  - 相關 API 端點
  - Console 錯誤
```

### Step 3: 評估嚴重程度

```yaml
Critical (緊急):
  - 系統崩潰或無法使用
  - 數據丟失或損壞
  - 安全漏洞
  - 核心功能完全失效

High (高):
  - 主要功能無法使用
  - 無 workaround
  - 影響多數用戶

Medium (中):
  - 功能異常但有 workaround
  - 次要功能問題
  - UI/UX 問題

Low (低):
  - 美觀問題
  - 小型 UI 瑕疵
  - 非功能性問題
```

### Step 4: 創建 Issue 文件

```yaml
文件路徑: claudedocs/uat/issues/ISSUE-{NNN}.md
內容: 完整問題記錄 (見輸出格式)
```

### Step 5: 更新追蹤文件

```yaml
更新項目:
  - UAT-MASTER-LOG.md 問題統計
  - UAT-MASTER-LOG.md 問題追蹤清單
  - 當前會話記錄 (如有)
```

---

## 輸出格式

### Issue 文件模板

```markdown
# ISSUE-{NNN}: {問題標題}

> **建立日期**: {YYYY-MM-DD HH:MM}
> **模組**: {MODULE}
> **嚴重程度**: {SEVERITY}
> **狀態**: 待修復
> **發現者**: User
> **會話 ID**: {SESSION_ID}

---

## 問題描述

{詳細問題描述}

---

## 重現步驟

1. {步驟 1}
2. {步驟 2}
3. {步驟 3}
4. ...

---

## 預期結果

{預期應該發生的情況}

---

## 實際結果

{實際發生的情況}

---

## 環境信息

```yaml
瀏覽器: Chrome 120
作業系統: Windows 11
Frontend URL: http://localhost:3005
Backend URL: http://localhost:8000
```

---

## 錯誤訊息 (如有)

```
{Console 錯誤或 API 錯誤訊息}
```

---

## 截圖 (如有)

![問題截圖](./screenshots/ISSUE-{NNN}-screenshot.png)

---

## 相關資訊

- **相關頁面**: {頁面 URL}
- **相關 API**: {API 端點}
- **相關代碼**: {文件路徑:行號}

---

## 狀態歷史

| 日期 | 狀態變更 | 備註 |
|------|----------|------|
| {DATE} | 建立 | 初始記錄 |

---

## 修復記錄

**修復 ID**: -
**修復日期**: -
**修復者**: -
**驗證狀態**: -
```

### 控制台輸出

```markdown
# 問題記錄完成

**Issue ID**: ISSUE-001
**標題**: {問題標題}
**模組**: {MODULE}
**嚴重程度**: {SEVERITY}
**狀態**: 待修復

---

## 問題摘要

{簡短問題描述}

**重現步驟**:
1. {步驟 1}
2. {步驟 2}

---

## 文件已創建

- Issue 文件: `claudedocs/uat/issues/ISSUE-001.md`
- Master Log 已更新

---

## 後續行動

1. 繼續測試其他功能
2. 或立即修復: `@PROMPT-12-UAT-FIX.md ISSUE-001`
3. 查看所有問題: `@PROMPT-10-UAT-SESSION.md status`
```

---

## 使用範例

### 範例 1: 記錄 Dashboard 載入問題

```bash
用戶: "@PROMPT-11-UAT-ISSUE.md dashboard 統計數據載入失敗"

AI 執行:
1. 生成 Issue ID: ISSUE-001
2. 詢問補充信息:
   - 完整錯誤訊息?
   - 重現步驟?
   - 嚴重程度?
3. 創建 Issue 文件
4. 更新 Master Log

輸出: Issue 記錄確認
```

### 範例 2: 記錄 API 錯誤

```bash
用戶: "@PROMPT-11-UAT-ISSUE.md api 創建 Workflow 返回 500 錯誤"

AI 執行:
1. 生成 Issue ID
2. 記錄 API 錯誤詳情
3. 檢查 Backend 日誌 (如可能)
4. 創建 Issue 文件

輸出: Issue 記錄確認
```

### 範例 3: 快速記錄 (互動模式)

```bash
用戶: "@PROMPT-11-UAT-ISSUE.md workflows"

AI 回應:
> 請描述發現的問題:
> 1. 問題簡述?
> 2. 重現步驟?
> 3. 嚴重程度 (Critical/High/Medium/Low)?

用戶:
> 1. 拖拽節點時頁面卡頓
> 2. 打開編輯器 → 添加 5+ 節點 → 拖拽
> 3. Medium

AI 執行並生成 Issue 記錄
```

---

## 嚴重程度指引

| 等級 | 定義 | 處理時效 | 範例 |
|------|------|----------|------|
| **Critical** | 系統無法使用 | 立即處理 | 登入失敗、數據丟失 |
| **High** | 主功能失效 | 24 小時內 | API 錯誤、頁面崩潰 |
| **Medium** | 功能異常 | 3 天內 | 顯示錯誤、性能問題 |
| **Low** | 小問題 | 下次迭代 | UI 瑕疵、文字錯誤 |

---

## 相關文檔

- [UAT Master Log](../../uat/UAT-MASTER-LOG.md)
- [PROMPT-10: UAT Session](./PROMPT-10-UAT-SESSION.md)
- [PROMPT-12: UAT Fix](./PROMPT-12-UAT-FIX.md)

---

**版本**: v1.0.0
**建立日期**: 2025-12-09
