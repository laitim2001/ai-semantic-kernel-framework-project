# 風險缺口與整改路線圖（Codex 完整版）

> **文件版本**: 1.0
> **最後更新**: 2026-02-11
> **關聯文件**: `03-architecture-deep-analysis.md`, `04-features-mapping-deep-analysis.md`

---

## 1. 風險分級總覽

| 等級 | 數量 | 說明 |
|---|---:|---|
| 嚴重 | 1 | 併發一致性核心風險 |
| 高 | 4 | 配置/授權/運行邊界風險 |
| 中 | 4 | fallback 與維護性風險 |

---

## 2. 風險清單

| # | 風險 | 等級 | 影響 | 證據 |
|---|---|---|---|---|
| R1 | 雙 ContextSynchronizer 缺少鎖機制 | 嚴重 | 競爭條件、上下文污染 | `backend/src/integrations/hybrid/context/sync/synchronizer.py`, `backend/src/integrations/claude_sdk/hybrid/synchronizer.py` |
| R2 | Frontend proxy 與 backend port 不一致 | 高 | dev 環境 API 故障 | `frontend/vite.config.ts`, `backend/main.py` |
| R3 | CORS 預設 port 與 frontend dev port 不一致 | 高 | 跨域阻擋 | `backend/src/core/config.py`, `frontend/vite.config.ts` |
| R4 | API 授權覆蓋不均（pattern 命中低） | 高 | 未授權存取風險 | `backend/src/api/v1` scan |
| R5 | `reload=True` 啟動設定長期存在 | 高 | 生產行為風險 | `backend/main.py` |
| R6 | InMemory/Mock 類別大量存在 | 中 | fallback 行為不可預期 | pattern scan |
| R7 | 超大檔案集中 | 中 | 迭代與回歸風險上升 | size scan |
| R8 | 可視化依賴缺口（reactflow） | 中 | 部分功能不可用 | `frontend/package.json` |
| R9 | 前端 console.log 密度高 | 中 | 噪音/資訊外露 | `frontend/src` scan |

---

## 3. 90 天整改路線圖

## Phase 1（Week 1-2）

1. 修正 Vite proxy target 與 backend port。
2. 對齊 CORS allow_origins 與 frontend dev/prod domain。
3. 對 `main.py` 建立 dev/prod 啟動分離（移除硬編碼 `reload=True`）。

驗收：

- 前端本機 API 呼叫全綠
- CORS preflight 正常
- 生產 profile 不含 reload

## Phase 2（Week 3-6）

1. 為兩套 ContextSynchronizer 加入一致的鎖策略與壓測用例。
2. 定義 fallback policy：InMemory/Mock 僅在明確 flag 下啟用。
3. 高風險 API 路由補齊統一授權依賴。

驗收：

- 併發壓測無共享狀態污染
- fallback 使用有審計記錄
- 高風險路由 auth 覆蓋率達標

## Phase 3（Week 7-12）

1. 拆分 >1000 LOC 檔案（先 backend API 與核心 builders）。
2. 引入 workflow 視覺化依賴並完成最小可用頁。
3. 建立架構/功能報告自動化產生腳本。

驗收：

- 大檔案數量下降
- 視覺化頁可運行
- 分析報告可一鍵重建

---

## 4. 追蹤指標

1. `config_drift_count`：port/CORS 不一致項數
2. `auth_coverage_files`：命中 auth 依賴的 API 檔案數
3. `fallback_runtime_count`：InMemory/Mock 在非測試環境使用次數
4. `large_file_count`：>800 行與 >1000 行檔案數
5. `critical_path_test_pass_rate`：關鍵端到端路徑通過率

---

## 5. 結語

本專案下一階段成功關鍵不是加更多功能，而是把既有能力「制度化、可驗收化、可重現化」。完成本路線圖後，平台會從功能完整邁向生產穩定。
