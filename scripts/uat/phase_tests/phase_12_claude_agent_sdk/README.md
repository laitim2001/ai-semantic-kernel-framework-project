# Phase 12: Claude Agent SDK Integration Tests

## 測試版本說明

本目錄包含兩個不同類型的測試套件：

### 📁 `api-validation/` - API 路由驗證測試

**用途**: 驗證 Phase 12 API 路由是否正確註冊和響應

**特點**:
- 測試 API 端點是否返回預期的 HTTP 狀態碼
- 當 API 返回 404 時使用模擬通過（simulated pass）
- 不需要真實的 LLM 調用
- 不需要 ANTHROPIC_API_KEY
- 快速執行，適合 CI/CD 管道

**運行方式**:
```bash
cd api-validation
python phase_12_claude_sdk_test.py
```

**測試場景**:
1. Scenario A: 核心 SDK 整合（Core SDK Integration）
2. Scenario B: 工具和鉤子（Tools & Hooks）
3. Scenario C: MCP 和混合（MCP & Hybrid）
4. Scenario D: API 路由（API Routes）

---

### 📁 `real-functional/` - 真實功能測試

**用途**: 驗證 Claude Agent SDK 的真實功能運作

**特點**:
- 使用真實的 ANTHROPIC_API_KEY 進行 LLM 調用
- 測試實際的工具執行（檔案讀寫、Shell 命令等）
- 測試真實的 MCP Server 整合
- 驗證端到端的使用案例
- 需要較長執行時間和 API 配額

**運行方式**:
```bash
cd real-functional
# 設置環境變數
export ANTHROPIC_API_KEY=sk-ant-api03-...
# 運行測試
python real_functional_test.py
```

**測試場景**:
1. Scenario A: 真實 LLM 對話（Real LLM Conversation）
2. Scenario B: 真實工具執行（Real Tool Execution）
3. Scenario C: 真實 MCP 整合（Real MCP Integration）
4. Scenario D: 端到端使用案例（End-to-End Use Cases）

---

## 版本對比

| 特性 | API Validation | Real Functional |
|------|----------------|-----------------|
| 需要 API Key | ❌ | ✅ |
| 真實 LLM 調用 | ❌ | ✅ |
| 真實工具執行 | ❌ | ✅ |
| 執行時間 | ~30秒 | ~5-10分鐘 |
| API 費用 | $0 | 約 $0.50-2.00 |
| 適用場景 | CI/CD、快速驗證 | 功能驗收、整合測試 |

---

## 環境配置

### API Validation（無需配置）
```bash
# 直接運行
python api-validation/phase_12_claude_sdk_test.py
```

### Real Functional（需要配置）
```bash
# 方法 1: 環境變數
export ANTHROPIC_API_KEY=sk-ant-api03-...

# 方法 2: .env 文件
cd real-functional
cp .env.example .env
# 編輯 .env 設置 ANTHROPIC_API_KEY

# 運行測試
python real_functional_test.py
```

---

**Last Updated**: 2025-12-27
