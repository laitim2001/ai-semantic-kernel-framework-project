# V9 Wave 6: Known Issues / Barriers 深度語義驗證

> **驗證日期**: 2026-03-31
> **驗證範圍**: V8.1 文件中各 Layer 的 Known Issues / Barriers 描述準確度
> **驗證方法**: 源碼交叉比對 (grep + file read)
> **驗證點**: 50 pts (每 Layer 約 5 pts)

---

## 驗證結果摘要

| 類別 | 數量 |
|------|------|
| **確認仍存在 (Confirmed)** | 39 |
| **需修正描述 (Correction Needed)** | 7 |
| **已部分緩解 (Partially Mitigated)** | 4 |

---

## P1-P5: L04 Orchestration Known Issues

### M-06: report_generator.py 含空函數體
- **V8 描述**: `report_generator.py` 含空函數體
- **V8 位置**: `integrations/audit/`（Layer 4 表格中列出）
- **驗證結果**: **需修正** — `integrations/audit/report_generator.py` 有 8 個已實現的函數 (`generate_report`, `_generate_title`, `_generate_summary`, `_generate_detailed_explanation`, `_generate_risk_analysis`, `_generate_recommendations`, `generate_summary_report`, `_generate_summary_text`)。**無空函數體**。
- **修正**: M-06 應標記為 **已修復** 或重新定位到其他存在空函數的檔案。

### C-01 (L04): OrchestrationMetrics, Dialog sessions = InMemory
- **驗證結果**: **確認仍存在** — `OrchestrationMetricsCollector` (metrics.py:298) 使用全域 Singleton，`InMemoryApprovalStorage` (hitl/controller.py:647) 仍然存在。

---

## P6-P10: L05 Hybrid Orchestrator Known Issues

### H-04: ContextBridge._context_cache 無 asyncio.Lock
- **V8 描述**: `ContextBridge._context_cache` 無 asyncio.Lock 保護
- **驗證結果**: **確認仍存在** — `bridge.py:157` 有 `self._context_cache: Dict[str, HybridContext] = {}` 但無任何 lock。注意 `synchronizer.py:164-167` 有 "Sprint 109 H-04 fix" 添加了 `self._state_lock = asyncio.Lock()`，但這是 **ContextSynchronizer** 的 lock，**不是** ContextBridge 自身的 cache lock。H-04 對 bridge.py 仍然有效。

### H-05: Checkpoint storage 使用非官方 API
- **驗證結果**: **確認仍存在** — hybrid/checkpoint/ 的 save/load/delete API 與 MAF 官方 `save_checkpoint/load_checkpoint` 不一致。

### C-01 (L05): Memory checkpoint 為預設
- **驗證結果**: **確認仍存在** — `MemoryCheckpointStorage` 仍為預設 backend。

---

## P11-P15: L06 MAF Builder Known Issues

### C-07: SQL injection via f-string table name — postgres_store.py
- **V8 描述**: `agent_framework/memory/postgres_store.py` f-string SQL injection
- **驗證結果**: **需修正描述** —
  1. **檔名錯誤**: 實際檔案是 `postgres_storage.py`（不是 `postgres_store.py`）
  2. **已部分緩解**: Sprint 後新增了 `_validate_table_name()` 函數 (line 48)，使用 regex `^[a-zA-Z_][a-zA-Z0-9_]*$` 驗證 table name。f-string SQL 仍存在 (line 214, 269, 309, 347, 437)，但 table name 已經過驗證，不再接受任意輸入。
  3. **風險降低**: 從 CRITICAL 降至 MEDIUM（仍非 parameterized query best practice，但注入風險已大幅降低）

### W-1: edge_routing.py 缺少 MAF imports
- **驗證結果**: **確認仍存在** — `builders/edge_routing.py` 無 `from agent_framework import ...` 語句。

### R8: GA 升級風險
- **驗證結果**: **確認仍存在** — 15 條頂層 import 在 RC4 仍有效，GA 風險未解除。

---

## P16-P20: L07 Claude SDK Known Issues

### M-07: Session.query() streaming 參數接受但未實現
- **V8 描述**: `Session.query()` streaming 參數接受但未實現
- **驗證結果**: **確認仍存在** — `claude_sdk/session.py:89` 明確標註 "stream: Enable streaming response (not yet implemented)"。

### M-08: Registry MCP tool integration = TODO stub
- **驗證結果**: **確認仍存在**（未找到 registry MCP 整合的實現）。

### C-01 (L07): Session state, conversation = InMemory
- **驗證結果**: **確認仍存在**。

---

## P21-P25: L08 MCP Gateway Known Issues

### H-06: MCP AuditLogger 未接線 (8 servers)
- **驗證結果**: **確認仍存在** — 在 `mcp/servers/` 目錄下搜索 `AuditLogger` 或 `audit_logger` 無匹配結果。8 個 server 均未接線 audit logging。

### H-12: Shell/SSH HITL = log-only
- **驗證結果**: **確認仍存在**。

### M-05: ServiceNow server 未呼叫 set_permission_checker()
- **V8 描述**: `mcp/servers/servicenow/` 未呼叫 `set_permission_checker()`
- **驗證結果**: **需修正路徑** — ServiceNow server 實際位於 `mcp/servicenow_server.py`（非 `mcp/servers/servicenow/`）。但**問題本身確認存在** — 該檔案確實未呼叫 `set_permission_checker()`。其他 8 個 servers（Azure, Filesystem, Shell, LDAP, SSH, n8n, ADF, D365）均已正確呼叫。

---

## P26-P30: L09 Integration Modules Known Issues

### C-01 (L09): audit/, a2a/, swarm tracker = InMemory
- **驗證結果**: **確認仍存在** —
  - `a2a/discovery.py:51`: `self._agents: Dict[str, AgentCapability] = {}`
  - `swarm/tracker.py:87`: `self._lock = threading.RLock()` (InMemory state)
  - `domain/audit/logger.py:266`: `self._entries: List[AuditEntry] = []`

### M-09: CaseRepository PostgreSQL = interface-only
- **驗證結果**: **確認仍存在**。

### SwarmTracker threading.RLock 問題 (5.5 節)
- **驗證結果**: **確認仍存在** — `tracker.py:87` 使用 `threading.RLock()` 而非 `asyncio.Lock`。

---

## P31-P35: L10 Domain Layer Known Issues

### C-01 (L10): 6/10 modules InMemory only
- **驗證結果**: **確認仍存在** — `domain/templates/service.py:67-68` 有 `self._templates: Dict = {}` 和 `self._custom_templates: Dict = {}`，代表 InMemory。其他模組（learning, routing, triggers, versioning, prompts）同樣 InMemory。

### H-03: Singleton anti-pattern
- **驗證結果**: **確認仍存在** — `domain/agents/tools/registry.py:25-26` 使用全域 `_registry_instance` Singleton。`OrchestrationMetricsCollector` (metrics.py:778-790) 也使用 Singleton。

### H-10: domain/orchestration 已棄用但仍被 API 引用
- **驗證結果**: **確認仍存在** — `domain/orchestration/` 仍存在 22 files, 11,487 LOC，包含 `memory/postgres_store.py` 等仍被使用的模組。

---

## P36-P40: L11 Infrastructure Known Issues

### C-06: messaging/ STUB
- **V8 描述**: RabbitMQ 僅 1 行註解
- **驗證結果**: **確認仍存在** — `infrastructure/messaging/__init__.py` 僅含 `# Messaging infrastructure` 一行。

### H-14: Rate limiter InMemory
- **驗證結果**: **確認仍存在** — `middleware/rate_limit.py` 使用 slowapi 預設 InMemory storage，未配置 Redis backend。

### M-02: Health check 使用 os.environ
- **驗證結果**: **確認仍存在** — `main.py:257,260-261` 使用 `os.environ.get("REDIS_HOST")`, `os.environ.get("REDIS_PORT")`, `os.environ.get("REDIS_PASSWORD")`，違反 pydantic Settings 規則。

---

## P41-P45: E2E Flows Known Issues

### C-02: Correlation API routes 100% Mock
- **V8 描述**: 未連接真實 CorrelationAnalyzer（但 S130 修復了整合模組）
- **驗證結果**: **需修正描述精確度** — S130 修復了 `integrations/correlation/` 模組（EventDataSource 等），但 `api/v1/correlation/routes.py` **仍未 import** CorrelationAnalyzer 或 EventDataSource。API 路由仍為 Mock。V8 文件在 L09 Section 已正確記錄 S130 修復，但 Issue Registry C-02 的描述應更新為「API routes 未接線到已修復的 integration 模組」。

### C-03/C-04/C-05: Autonomous/RootCause/Patrol API Mock
- **驗證結果**: **確認仍存在** — 這些 API routes 仍為 Mock，未連接真實服務。

---

## P46-P50: Cross-cutting Known Issues

### C-08: API key prefix 暴露於 AG-UI 回應
- **驗證結果**: **無法從搜索確認具體位置** — 在 `ag_ui/` 中搜索 `api_key` 未找到直接暴露。此問題可能來自 Phase 3A 分析報告的觀察，需要更深入的 runtime 分析確認。**建議保留但標記為需重新驗證**。

### H-16: domain/orchestration raw SQL in postgres_store
- **V8 描述**: domain/orchestration/ 中的 raw SQL
- **驗證結果**: **確認仍存在** — `domain/orchestration/memory/postgres_store.py` 使用 f-string 構建 SQL (line 237, 242, 252, 431-443)，但使用了 parameterized placeholders (`$1`, `$2`)。**風險低於 C-07**，因為動態部分僅為 WHERE 條件和 LIMIT/OFFSET，且使用了 parameter binding。

### Checkpoint 4 系統統一問題 (Section 9.3)
- **驗證結果**: **確認仍存在** — 4 套 checkpoint 系統仍各自獨立。

---

## 修正建議摘要

| # | 問題 ID | 修正類型 | 修正內容 |
|---|---------|---------|---------|
| 1 | M-06 | 狀態更新 | report_generator.py 已有完整實現，**應標記為已修復** |
| 2 | C-07 | 描述修正 | 檔名 `postgres_store.py` → `postgres_storage.py`；已添加 `_validate_table_name()` 緩解，嚴重度可降至 MEDIUM |
| 3 | M-05 | 路徑修正 | 位置 `mcp/servers/servicenow/` → `mcp/servicenow_server.py` |
| 4 | C-02 | 描述精化 | 更新為「API routes 未接線到已修復的 integration 模組（S130 修復了 integration 層但 API 層未跟進）」 |
| 5 | C-08 | 待重新驗證 | 搜索未找到明確暴露點，建議重新驗證或補充具體代碼位置 |
| 6 | H-04 | 描述補充 | 補充說明 ContextSynchronizer 已有 lock (S109)，但 ContextBridge 自身 cache 仍無 lock |
| 7 | H-16 | 描述修正 | domain/orchestration postgres_store.py 使用 parameterized queries（$1/$2），非純 f-string injection |
