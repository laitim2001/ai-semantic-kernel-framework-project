# Phase 10: Session Mode 測試

## 概述

Phase 10 測試驗證 Session Mode API 的完整功能，包括互動式會話、文件處理、歷史管理和進階功能。

## 測試場景

### 場景：技術支援會話 (Technical Support Session)

**業務背景**：
用戶通過 Session Mode 進行技術問題諮詢，上傳錯誤日誌，與 AI 進行多輪對話獲取解決方案。

**測試流程**：

```
Step 1: 建立 Session
    └─ SessionService.create_session()

Step 2: 上傳錯誤日誌
    └─ 使用 attachments API 上傳日誌文件

Step 3: 發送問題描述
    └─ 發送第一條訊息描述問題

Step 4: AI 分析日誌
    └─ AI 分析上傳的日誌並回應

Step 5: 多輪對話追問
    └─ 進行多輪對話深入了解問題

Step 6: 獲取解決方案
    └─ AI 提供完整的解決方案

Step 7: 搜索歷史記錄
    └─ 測試對話歷史搜索功能

Step 8: 建立會話模板
    └─ 從當前會話建立可重用模板

Step 9: 查看統計信息
    └─ 獲取會話統計數據

Step 10: 結束 Session
    └─ 正確關閉會話
```

## 測試的 Session 組件

| 組件 | 功能 |
|------|------|
| SessionService | 會話生命週期管理 |
| Session Model | 會話狀態機 |
| Message Model | 訊息歷史 |
| Attachment Model | 文件附件 |
| HistoryManager | 歷史查詢 |
| SearchService | 全文搜索 |
| TemplateService | 模板管理 |
| StatisticsService | 統計分析 |

## Session 狀態機

```
CREATED → ACTIVE ⇄ SUSPENDED → ENDED
```

| 狀態 | 說明 |
|------|------|
| CREATED | 剛建立，未激活 |
| ACTIVE | 活躍中，可收發訊息 |
| SUSPENDED | 暫停，可恢復 |
| ENDED | 已結束 |

## 測試數據

模擬的錯誤日誌：

```
2024-12-22 10:15:23 ERROR [api.v1.handlers] Connection timeout to database
2024-12-22 10:15:24 ERROR [api.v1.handlers] Retry 1/3 failed
2024-12-22 10:15:25 ERROR [api.v1.handlers] Retry 2/3 failed
2024-12-22 10:15:26 CRITICAL [api.v1.handlers] All retries exhausted
2024-12-22 10:15:26 ERROR [api.v1.handlers] User request failed: 503
```

## 執行方式

```bash
cd scripts/uat/phase_tests
python -m phase_10_session_mode.scenario_tech_support
```

## 預期結果

1. **Session 建立**: 成功建立並激活 Session
2. **文件上傳**: 日誌文件正確上傳
3. **AI 回應**: AI 能夠分析日誌並提供有用建議
4. **多輪對話**: 對話狀態正確維護
5. **搜索功能**: 能夠搜索歷史訊息
6. **模板建立**: 成功建立可重用模板

## 驗證要點

| 功能 | 驗證方式 |
|------|----------|
| Session 狀態 | 狀態轉換正確 |
| 訊息持久化 | 歷史記錄完整 |
| 附件管理 | 上傳/下載成功 |
| AI 整合 | 回應有意義 |
| 搜索準確 | 關鍵字匹配 |
| 統計正確 | 數據一致 |

## 依賴

- PostgreSQL (Session 持久化)
- Redis (Session 快取)
- Azure OpenAI (AI 回應)

---

**建立日期**: 2025-12-22
