# PROMPT-10: UAT SESSION
# UAT 測試會話管理

> **用途**: 開始/結束 UAT 測試會話，追蹤測試進度
> **變數**: `{ACTION}`, `{MODULE}`
> **預估時間**: 5-15 分鐘
> **版本**: v1.0.0

---

## 變數定義

```yaml
{ACTION}:
  描述: 會話操作
  選項: "start", "end", "status"
  預設: "start"

{MODULE}:
  描述: 測試模組名稱
  選項: "dashboard", "workflows", "agents", "executions", "templates", "analytics", "settings", "all"
  預設: "all"
```

---

## 執行步驟

### 模式 1: 開始測試會話 (start)

```yaml
Step 1: 環境檢查
  - 確認 Frontend 運行 (http://localhost:3005)
  - 確認 Backend 運行 (http://localhost:8000/health)
  - 確認資料庫連接正常

Step 2: 建立會話記錄
  - 生成會話 ID: SESSION-{YYYY-MM-DD}-{NN}
  - 創建會話文件: claudedocs/uat/sessions/{SESSION_ID}.md
  - 記錄開始時間和測試範圍

Step 3: 載入測試清單
  - 讀取 claudedocs/uat/checklists/{MODULE}.md
  - 顯示待測試功能列表
  - 標記測試優先順序

Step 4: 準備測試環境
  - 開啟測試頁面 (提供 URL)
  - 準備測試數據 (如需要)
  - 顯示測試注意事項
```

### 模式 2: 結束測試會話 (end)

```yaml
Step 1: 收集測試結果
  - 統計已測試功能數
  - 統計發現的問題數
  - 計算通過率

Step 2: 更新會話記錄
  - 記錄結束時間
  - 記錄測試摘要
  - 列出待處理問題

Step 3: 更新主追蹤文件
  - 更新 UAT-MASTER-LOG.md
  - 更新模組完成率
  - 更新問題統計

Step 4: 生成會話報告
  - 輸出測試摘要
  - 列出下次待測項目
  - 建議後續行動
```

### 模式 3: 查看狀態 (status)

```yaml
Step 1: 讀取主追蹤文件
  - 顯示整體測試進度
  - 顯示各模組完成率
  - 顯示待處理問題

Step 2: 顯示當前會話 (如有)
  - 顯示進行中的測試
  - 顯示已發現問題
```

---

## 輸出格式

### 開始會話輸出

```markdown
# UAT 測試會話開始

**會話 ID**: SESSION-2025-12-09-01
**開始時間**: 2025-12-09 15:30:00
**測試模組**: {MODULE}
**測試人員**: User

---

## 環境狀態

| 服務 | 狀態 | URL |
|------|------|-----|
| Frontend | 運行中 | http://localhost:3005 |
| Backend | 健康 | http://localhost:8000 |
| Database | 連接正常 | PostgreSQL |

---

## 待測試功能

### {MODULE} 模組

| # | 功能 | 優先級 | 狀態 |
|---|------|--------|------|
| 1 | {功能名稱} | 高 | 待測試 |
| 2 | {功能名稱} | 中 | 待測試 |
| ... | ... | ... | ... |

---

## 測試入口

- 頁面 URL: http://localhost:3005/{path}
- API 文檔: http://localhost:8000/docs

---

## 測試指引

1. 按順序測試每個功能
2. 發現問題時執行: `@PROMPT-11-UAT-ISSUE.md {MODULE} {問題描述}`
3. 測試完成後執行: `@PROMPT-10-UAT-SESSION.md end`

---

**開始測試吧！**
```

### 結束會話輸出

```markdown
# UAT 測試會話結束

**會話 ID**: SESSION-2025-12-09-01
**開始時間**: 2025-12-09 15:30:00
**結束時間**: 2025-12-09 17:00:00
**持續時間**: 1.5 小時

---

## 測試摘要

| 項目 | 數量 |
|------|------|
| 總功能數 | {N} |
| 已測試 | {N} |
| 通過 | {N} |
| 失敗 | {N} |
| 通過率 | {N}% |

---

## 發現的問題

| Issue ID | 標題 | 嚴重程度 | 狀態 |
|----------|------|----------|------|
| ISSUE-001 | {標題} | {等級} | 待修復 |
| ... | ... | ... | ... |

---

## 下次待測項目

- [ ] {待測功能 1}
- [ ] {待測功能 2}

---

## 後續行動

1. 優先修復 Critical/High 問題
2. 執行 `@PROMPT-12-UAT-FIX.md {ISSUE_ID}` 記錄修復
3. 修復後重新驗證

---

**會話已保存至**: claudedocs/uat/sessions/SESSION-2025-12-09-01.md
```

---

## 使用範例

### 範例 1: 開始測試 Dashboard 模組

```bash
用戶: "@PROMPT-10-UAT-SESSION.md start dashboard"

AI 執行:
1. 檢查環境狀態
2. 創建會話 SESSION-2025-12-09-01
3. 載入 Dashboard 測試清單
4. 顯示待測試功能

輸出: (見上方開始會話輸出格式)
```

### 範例 2: 測試所有模組

```bash
用戶: "@PROMPT-10-UAT-SESSION.md start all"

AI 執行:
1. 載入所有模組測試清單
2. 按優先級排序功能
3. 建議測試順序

輸出: 完整功能列表和測試建議
```

### 範例 3: 結束當前會話

```bash
用戶: "@PROMPT-10-UAT-SESSION.md end"

AI 執行:
1. 收集測試結果
2. 更新 UAT-MASTER-LOG.md
3. 生成會話報告

輸出: (見上方結束會話輸出格式)
```

### 範例 4: 查看測試狀態

```bash
用戶: "@PROMPT-10-UAT-SESSION.md status"

AI 執行:
1. 讀取 UAT-MASTER-LOG.md
2. 顯示進度摘要

輸出: 當前測試進度和問題統計
```

---

## 相關文檔

- [UAT Master Log](../../uat/UAT-MASTER-LOG.md)
- [PROMPT-11: UAT Issue](./PROMPT-11-UAT-ISSUE.md)
- [PROMPT-12: UAT Fix](./PROMPT-12-UAT-FIX.md)
- [AI Assistant Instructions](../AI-ASSISTANT-INSTRUCTIONS.md)

---

**版本**: v1.0.0
**建立日期**: 2025-12-09
