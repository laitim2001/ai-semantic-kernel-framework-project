# Phase 8: Code Interpreter 測試

## 概述

Phase 8 測試驗證 Azure OpenAI Code Interpreter 的完整功能，使用真實 AI 模型 (gpt-5.2) 執行實際的數據分析任務。

## 測試場景

### 場景：財務數據智能分析 (Financial Data Analysis)

**業務背景**：
企業財務分析師需要分析 Q4 銷售數據，生成趨勢報告和視覺化圖表。

**測試流程**：

```
Step 1: 建立 Code Interpreter Assistant
    └─ 使用 AssistantManagerService 建立具有 code_interpreter 工具的 Assistant

Step 2: 上傳銷售數據 CSV
    └─ 使用 FileStorageService 上傳測試數據

Step 3: AI 數據分析
    └─ 使用真實 AI 執行 Python 代碼分析數據
    └─ 計算銷售趨勢、成長率、異常值

Step 4: 生成視覺化圖表
    └─ AI 生成銷售趨勢圖
    └─ 生成產品類別分佈圓餅圖

Step 5: 獲取 AI 洞察和建議
    └─ AI 根據分析結果提供業務建議

Step 6: 清理資源
    └─ 刪除上傳的文件和 Assistant
```

## 測試數據

測試使用模擬的 Q4 銷售數據：

| 日期 | 產品類別 | 銷售額 | 數量 | 區域 |
|------|----------|--------|------|------|
| 2024-10-01 | Electronics | 15000 | 50 | North |
| 2024-10-02 | Clothing | 8000 | 120 | South |
| ... | ... | ... | ... | ... |

## 執行方式

```bash
cd scripts/uat/phase_tests
python -m phase_8_code_interpreter.scenario_financial_analysis
```

## 預期結果

1. **代碼執行成功**: AI 能夠執行 Python 代碼進行數據分析
2. **分析準確**: 計算出正確的銷售趨勢和統計數據
3. **圖表生成**: 成功生成 PNG 格式的視覺化圖表
4. **洞察有價值**: AI 提供的業務建議具有實際參考價值

## 驗證要點

| 功能 | 驗證方式 |
|------|----------|
| AssistantManagerService | 建立 Assistant 成功返回 assistant_id |
| FileStorageService | 文件上傳成功返回 file_id |
| CodeInterpreterAdapter | 代碼執行返回有效結果 |
| 視覺化生成 | 圖表文件成功下載 |
| AI 回應 | 回應包含數據分析和建議 |

## 依賴

- Azure OpenAI 服務
- gpt-5.2 部署
- Code Interpreter 功能啟用

---

**建立日期**: 2025-12-22
