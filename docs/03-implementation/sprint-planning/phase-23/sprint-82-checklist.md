# Sprint 82 Checklist: 主動巡檢與智能關聯

## Sprint Status

| Metric | Value |
|--------|-------|
| **Total Stories** | 2 |
| **Total Points** | 16 pts |
| **Completed** | 0 |
| **In Progress** | 0 |
| **Status** | 計劃中 |

---

## Stories

### S82-1: 主動巡檢模式 (8 pts)

**Status**: ⬜ 待開始

**Tasks**:
- [ ] 創建 `patrol/` 目錄
- [ ] 實現 PatrolScheduler class
  - [ ] `schedule_patrol()` 方法
  - [ ] `cancel_patrol()` 方法
  - [ ] `list_schedules()` 方法
- [ ] 實現 PatrolAgent class
  - [ ] `execute_patrol()` 方法
  - [ ] `analyze_results()` 方法
  - [ ] `generate_report()` 方法
- [ ] 創建巡檢檢查項目
  - [ ] `service_health.py` - 服務健康檢查
  - [ ] `api_response.py` - API 響應檢查
  - [ ] `resource_usage.py` - 資源使用檢查
  - [ ] `log_analysis.py` - 日誌分析檢查
  - [ ] `security_scan.py` - 安全掃描檢查
- [ ] 創建 API 端點
- [ ] 配置定時任務

**Acceptance Criteria**:
- [ ] 支援定時巡檢
- [ ] Claude 主動分析
- [ ] 自動風險評估
- [ ] 生成巡檢報告
- [ ] 支援手動觸發

---

### S82-2: 智能關聯與根因分析 (8 pts)

**Status**: ⬜ 待開始

**Tasks**:
- [ ] 創建 `correlation/` 目錄
- [ ] 實現 CorrelationAnalyzer class
  - [ ] `time_correlation()` 方法
  - [ ] `dependency_correlation()` 方法
  - [ ] `semantic_correlation()` 方法
  - [ ] `find_correlations()` 方法
- [ ] 實現 CorrelationGraph class
  - [ ] `build_graph()` 方法
  - [ ] `visualize()` 方法
- [ ] 創建 `rootcause/` 目錄
- [ ] 實現 RootCauseAnalyzer class
  - [ ] `analyze_root_cause()` 方法
  - [ ] `get_similar_patterns()` 方法
- [ ] 創建 API 端點

**Acceptance Criteria**:
- [ ] 事件時間關聯
- [ ] 系統依賴關聯
- [ ] 語義相似關聯
- [ ] 關聯圖譜視覺化
- [ ] Claude 根因分析

---

## Verification Checklist

### Functional Tests
- [ ] 巡檢定時執行
- [ ] 異常被識別
- [ ] 關聯分析正確
- [ ] 根因分析合理

### Performance Tests
- [ ] 巡檢報告生成 < 5 分鐘
- [ ] 關聯查詢 < 2 秒

---

**Last Updated**: 2026-01-12
