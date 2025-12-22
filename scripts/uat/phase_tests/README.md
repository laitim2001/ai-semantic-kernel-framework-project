# Phase 獨立功能測試

本目錄包含 Phase 8, 9, 10 三個階段的獨立功能測試，用於在整合到完整 UAT 場景之前驗證各階段功能。

## 目錄結構

```
phase_tests/
├── README.md                      # 本文件
├── base.py                        # 共用測試基礎類
├── config.py                      # 共用配置
│
├── phase_8_code_interpreter/      # Phase 8: Code Interpreter 測試
│   ├── README.md
│   ├── scenario_financial_analysis.py  # 財務數據分析場景
│   └── test_results.json
│
├── phase_9_mcp_architecture/      # Phase 9: MCP 架構測試
│   ├── README.md
│   ├── scenario_infra_diagnostics.py   # 基礎設施診斷場景
│   └── test_results.json
│
└── phase_10_session_mode/         # Phase 10: Session Mode 測試
    ├── README.md
    ├── scenario_tech_support.py   # 技術支援會話場景
    └── test_results.json
```

## 測試場景設計

### Phase 8: Code Interpreter (Sprint 37-38, 35 pts)

**場景：財務數據智能分析** (Financial Data Analysis)

模擬企業財務分析師使用 AI 進行季度銷售數據分析：
1. 上傳銷售數據 CSV 文件
2. 使用 AI 分析數據趨勢
3. 生成視覺化圖表
4. 獲取 AI 洞察和建議

**測試的功能**:
- AssistantManagerService 建立和管理
- CodeInterpreterAdapter 代碼執行
- FileStorageService 文件上傳
- 數據分析和視覺化

---

### Phase 9: MCP Architecture (Sprint 39-41, 110 pts)

**場景：雲端基礎設施診斷** (Cloud Infrastructure Diagnostics)

模擬 IT 運維人員進行 Azure 基礎設施問題診斷：
1. 列出所有 Azure VM
2. 檢查特定 VM 狀態
3. 執行診斷命令
4. 驗證權限和審計日誌

**測試的功能**:
- MCPClient 連接和工具調用
- Azure MCP Server VM 操作
- MCPPermissionManager 權限檢查
- MCPAuditLogger 審計記錄

---

### Phase 10: Session Mode (Sprint 42-44, 100 pts)

**場景：技術支援會話** (Technical Support Session)

模擬用戶通過 Session Mode 進行技術問題諮詢：
1. 建立互動式會話
2. 上傳錯誤日誌文件
3. 進行多輪對話獲取解答
4. 搜索歷史記錄和建立模板

**測試的功能**:
- SessionService 生命週期管理
- 文件上傳和分析
- 對話歷史管理
- 搜索和模板功能

---

## 執行方式

### 單獨執行某個 Phase 測試

```bash
# Phase 8
cd scripts/uat/phase_tests
python -m phase_8_code_interpreter.scenario_financial_analysis

# Phase 9
python -m phase_9_mcp_architecture.scenario_infra_diagnostics

# Phase 10
python -m phase_10_session_mode.scenario_tech_support
```

### 執行所有 Phase 測試

```bash
python run_all_phase_tests.py
```

## 前置需求

1. **環境變數** (`.env` 文件):
   ```
   AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
   AZURE_OPENAI_API_KEY=<key>
   AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5.2

   # Phase 9 需要
   AZURE_SUBSCRIPTION_ID=<subscription_id>
   AZURE_RESOURCE_GROUP=<resource_group>
   ```

2. **後端服務**: 確保 FastAPI 後端在 `localhost:8000` 運行

3. **依賴套件**: `pip install httpx asyncio`

## 測試報告

每個 Phase 測試完成後會生成 `test_results.json`，包含：
- 測試執行時間
- 各步驟通過/失敗狀態
- AI 模型實際回應
- 錯誤詳情（如有）

---

**建立日期**: 2025-12-22
**版本**: 1.0.0
