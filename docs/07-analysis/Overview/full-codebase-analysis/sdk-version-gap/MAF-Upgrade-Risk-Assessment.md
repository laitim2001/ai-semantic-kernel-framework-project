# MAF 升級風險評估報告

**分析日期**: 2026-03-15
**升級路徑**: `agent-framework 1.0.0b260114` → `1.0.0rc4`
**分析基礎**: V8 全量代碼分析 + 6 份專家報告 + Architecture Review Board 共識報告 + 版本差異分析

---

## Executive Summary

本報告評估 IPA Platform 從 MAF `1.0.0b260114` 升級至 `1.0.0rc4` 的風險、依賴衝突、測試影響和回滾策略。

**核心結論**: 升級風險為 **MEDIUM-HIGH**，但因 IPA 的 Adapter Pattern 架構提供了良好的隔離層，實際影響範圍可控。主要風險集中在 7 個 builder adapter 的 import 命名空間遷移和工作流程事件重構。升級不會惡化 V8 已知的 62 個問題，反而可能自動修復 2-3 個問題。

**Go/No-Go 建議**: **GO — 有條件執行**。建議在 2 個 Sprint 內完成，採用功能分支隔離 + 三階段漸進式升級。

---

## 1. 依賴相容性分析

### 1.1 IPA 現有依賴清單（與 MAF 相關）

| 依賴套件 | IPA 版本約束 | MAF rc4 需求 | 相容性 |
|---------|-------------|-------------|--------|
| `pydantic` | `>=2.5.0` | `>=2.5.0` | **相容** — 無衝突 |
| `pydantic-settings` | `>=2.1.0` | **已從 MAF 移除** | **相容** — 見下方分析 |
| `sqlalchemy` | `>=2.0.25` | 無依賴 | **無影響** |
| `redis` | `>=5.0.0` | 無依賴 | **無影響** |
| `httpx` | `>=0.26.0` | `>=0.26.0`（間接） | **相容** |
| `opentelemetry-*` | `>=1.22.0` | `>=1.22.0`（可選） | **相容** |
| `azure-identity` | `>=1.15.0` | `>=1.15.0` | **相容** — 新 `credential` 參數需要 |

### 1.2 pydantic-settings 依賴分析（BC-10 關鍵問題）

**MAF 變更**: MAF rc1 移除了對 `pydantic-settings` 的依賴，將內部設定系統從 `AFBaseSettings`（pydantic-based）改為 `TypedDict` + `load_settings()`。

**IPA 影響評估**: **LOW — 不受影響**

原因：
- IPA 的 `pydantic-settings` 使用完全獨立於 MAF
- IPA 在 `backend/src/core/config.py:11` 自行 import：`from pydantic_settings import BaseSettings, SettingsConfigDict`
- IPA 的 `Settings(BaseSettings)` 類（`config.py:14`）是 IPA 自己的設定系統
- IPA 在 `requirements.txt` 中直接聲明 `pydantic-settings>=2.1.0`
- MAF 移除 `pydantic-settings` 不會影響 IPA 的獨立安裝

**唯一風險**: 如果 IPA 代碼中有任何地方直接使用 MAF 的 `AFBaseSettings`。經搜索確認：**零使用** — IPA 未使用 `AFBaseSettings` 或 `load_settings()`。

### 1.3 版本約束更新建議

```python
# requirements.txt 變更
# 舊版本：
agent-framework>=1.0.0b260114,<2.0.0

# 新版本：
agent-framework>=1.0.0rc4,<2.0.0
```

**無需調整其他依賴版本**。所有現有 pip 依賴與 MAF rc4 相容。

---

## 2. 與 V8 已知問題的交互

### 2.1 升級可能自動修復的問題

| V8 Issue | 問題描述 | MAF 修復來源 | 修復機制 |
|----------|---------|-------------|---------|
| 部分 C-01 | InMemoryCheckpointStorage 預設 source_id 不一致 | BC-11 (rc1) | `InMemoryHistoryProvider` 預設 `source_id` 標準化為 `"in_memory"` |
| — | AgentRunResponse.created_at UTC 時區錯誤 | Bug fix (rc4) | 修復本地時間被錯誤標記為 UTC |
| — | 空文字內容 pydantic 驗證失敗 | Bug fix (rc4) | 空內容的 Pydantic 驗證修正 |
| — | 重複 MCP 工具/提示註冊 | Bug fix (b251114) | 防止重複工具註冊 |

### 2.2 升級不會惡化的問題

| V8 Issue ID | 問題描述 | 為何不受影響 |
|-------------|---------|-------------|
| CR-01 | InMemory 存儲（25+ 模組） | MAF 升級不觸及 IPA 自訂的 InMemory 存儲邏輯（AG-UI、Swarm、A2A 等）。這些是 IPA 層問題。 |
| CR-02 | 4 個 Mock API 假數據 | Mock 問題在 IPA API 層，與 MAF 版本無關 |
| CR-03 | SQL Injection | `postgres_store.py` 是 IPA 自訂代碼，非 MAF |
| CR-04 | MCP 權限 log-only | MCP 安全模型是 IPA 配置問題 |
| CR-05 | Shell/SSH 命令無控制 | IPA MCP Server 層實現，非 MAF |
| CR-06 | RabbitMQ 空殼 | IPA 基礎設施層，與 MAF 無關 |
| HI-01~HI-10 | 安全/前端問題 | 全部是 IPA 層問題 |

### 2.3 升級可能需要額外注意的交互

| V8 Issue | 交互風險 | 說明 |
|----------|---------|------|
| 架構健康度 52/100 — API→Integration 104 次直接依賴 | **MEDIUM** | 升級 MAF 後，如果任何 API 路由直接 import MAF 類（而非透過 Adapter），這些路由會立即斷裂。但經查證，所有 MAF import 都封裝在 `integrations/agent_framework/` 內部，API 層不直接 import MAF。**Adapter Pattern 在此發揮了關鍵保護作用。** |
| Singleton 擴散 20+ 處 | **LOW** | 升級不影響 Singleton 模式，但 module-level import 的 MAF 類如果命名空間變更，會在模組載入時立即失敗，幫助快速發現問題。 |
| `os.environ` 171 處直接調用 | **LOW** | MAF 設定系統變更（BC-10）不影響 IPA 的 `os.environ` 用法，因為 IPA 不使用 MAF 設定系統。 |
| `InMemoryCheckpointStorage` 使用 | **MEDIUM** | IPA 在 `checkpoint.py` 和 `multiturn/` 中直接 import 並使用 MAF 的 `InMemoryCheckpointStorage`。BC-11 的 `source_id` 範圍化變更和 BC-15 的 Checkpoint 模型重構需要驗證相容性。 |

### 2.4 結論

**升級與 V8 已知問題的交互為中性偏正面**。Adapter Pattern 成功隔離了大部分 MAF 變更的影響，使升級範圍限制在 `backend/src/integrations/agent_framework/` 目錄內。升級不會使任何已知的 62 個問題惡化，反而可修復 2-4 個 bug。

---

## 3. 測試影響評估

### 3.1 測試套件概況

| 測試類別 | 檔案數 | MAF 相關檔案數 | 升級影響風險 |
|---------|--------|--------------|------------|
| Unit tests | 289 | ~35+ | HIGH（直接測試 adapter 層） |
| Integration tests | 27 | ~5 | MEDIUM |
| E2E tests | 23 | ~5 | MEDIUM |
| MAF-specific tests | 10 | 10 | **CRITICAL**（全部受影響） |
| Performance tests | ~10 | ~4 | LOW |

### 3.2 最可能失敗的測試檔案（按優先級排序）

#### Tier 1 — 幾乎確定失敗（直接引用變更的 MAF API）

| 測試檔案 | 原因 | 影響的 BC |
|---------|------|---------|
| `tests/unit/integrations/agent_framework/builders/test_planning_llm_injection.py` | patch `src.integrations.agent_framework.builders.planning.LLMServiceFactory`，planning.py import 路徑變更（BC-07） | BC-07 |
| `tests/unit/integrations/agent_framework/builders/test_concurrent_builder_adapter.py` | 測試 ConcurrentBuilder adapter，import 路徑變更 | BC-07 |
| `tests/unit/integrations/agent_framework/builders/test_groupchat_builder_adapter.py` | 測試 GroupChatBuilder adapter | BC-07, BC-03 |
| `tests/unit/integrations/agent_framework/builders/test_magentic_builder_adapter.py` | 測試 MagenticBuilder adapter | BC-07, BC-18 |
| `tests/unit/integrations/agent_framework/builders/test_handoff_builder_adapter.py` | 測試 HandoffBuilder adapter | BC-07 |
| `tests/unit/integrations/agent_framework/builders/test_nested_workflow_adapter.py` | 測試 WorkflowBuilder/Executor adapter | BC-07, BC-14 |

#### Tier 2 — 很可能失敗（間接引用或依賴變更的類型）

| 測試檔案 | 原因 | 影響的 BC |
|---------|------|---------|
| `tests/unit/infrastructure/checkpoint/adapters/test_agent_framework_adapter.py` | Checkpoint 行為變更 | BC-15 |
| `tests/unit/infrastructure/checkpoint/adapters/test_multi_provider_integration.py` | Provider 狀態範圍化 | BC-11 |
| `tests/unit/infrastructure/storage/test_storage_factories_sprint120.py` | `create_agent_framework_checkpoint_storage` 工廠 | BC-15 |
| `tests/unit/integrations/agent_framework/assistant/test_exceptions.py` | 例外處理層級變更 | BC-09 |

#### Tier 3 — 可能受影響（E2E/Integration 測試）

| 測試檔案 | 原因 | 影響的 BC |
|---------|------|---------|
| `tests/e2e/test_concurrent_workflow.py` | ConcurrentBuilder 端到端 | BC-07 |
| `tests/e2e/test_groupchat_workflow.py` | GroupChatBuilder 端到端 | BC-07, BC-03 |
| `tests/e2e/test_agent_execution.py` | Agent 執行流程 | BC-01, BC-02 |
| `tests/e2e/test_ai_autonomous_decision.py` | Planning adapter | BC-07 |
| `tests/integration/test_execution_adapter_e2e.py` | 執行 adapter 整合 | BC-02 |

### 3.3 測試中的 MAF Mock/Patch 模式

經分析，IPA 測試套件中 MAF 相關的 mock 模式主要為：

1. **`@patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory')`** — 這些 patch 路徑在 source 變更後仍然有效，因為 patch 的是 IPA 內部路徑，非 MAF 路徑。但如果被 patch 的模組因 import 失敗而無法載入，patch 也會失敗。

2. **直接引用 MAF 類型** — 測試中如果 `from agent_framework import ConcurrentBuilder` 用於 type assertion，需更新為新路徑。

3. **Checkpoint/Storage 工廠測試** — 這些測試依賴 `InMemoryCheckpointStorage` 和 `CheckpointStorage` 的行為，需驗證 BC-15 兼容性。

### 3.4 測試優先級排序（升級後驗證順序）

```
Phase 1 (Day 1): Import 驗證
  → python -c "from agent_framework.orchestrations import GroupChatBuilder"
  → python -c "from agent_framework import AgentResponse"
  → 確認所有新 import 路徑可用

Phase 2 (Day 1-2): Adapter 單元測試
  → pytest tests/unit/integrations/agent_framework/ -v
  → 修復所有 import 路徑相關失敗

Phase 3 (Day 2-3): Checkpoint/Storage 測試
  → pytest tests/unit/infrastructure/checkpoint/ -v
  → pytest tests/unit/infrastructure/storage/ -v

Phase 4 (Day 3-4): Integration 測試
  → pytest tests/integration/ -v -k "agent_framework or execution"

Phase 5 (Day 4-5): E2E 測試
  → pytest tests/e2e/ -v
  → 完整回歸驗證
```

---

## 4. 回滾策略

### 4.1 快速回滾方案

#### 方案 A: Git 分支回滾（推薦，<5 分鐘）

```bash
# 前提: 所有升級工作在 feature/maf-rc4-upgrade 分支進行
git checkout main
# 如已合併:
git revert <merge-commit-hash>
```

**前提條件**:
- 所有升級變更在獨立功能分支 `feature/maf-rc4-upgrade`
- 不在升級同時進行其他功能開發
- 合併前完成完整測試套件

#### 方案 B: requirements.txt 版本回退（<10 分鐘）

```bash
# 回退版本約束
# requirements.txt: agent-framework>=1.0.0b260114,<1.0.0b260116

pip install agent-framework==1.0.0b260114
```

**注意**: 如果已修改代碼以適配新 API，僅回退套件版本會導致新代碼與舊 API 不相容。必須配合 Git 回滾使用。

#### 方案 C: 條件 Import 相容層（最安全，但增加複雜度）

```python
# backend/src/integrations/agent_framework/compat.py
try:
    # rc4+ 路徑
    from agent_framework.orchestrations import GroupChatBuilder
except ImportError:
    # b260114 路徑
    from agent_framework import GroupChatBuilder
```

**不推薦**: 增加技術債、增加測試矩陣、延長維護成本。僅作為緊急過渡方案。

### 4.2 回滾觸發條件

| 觸發條件 | 回滾方案 | 時間窗口 |
|---------|---------|---------|
| 升級後 >30% 單元測試失敗 | 方案 A（分支回滾） | 立即 |
| 升級後發現 MAF rc4 有未記錄的破壞性變更 | 方案 A + 回報 GitHub Issue | 24 小時內 |
| 升級後生產環境出現 Agent 執行異常 | 方案 B（版本回退）+ 方案 A | 1 小時內 |
| 升級後某些 Builder 功能不可用但核心功能正常 | 方案 C（相容層）暫時過渡 | 視影響範圍決定 |

### 4.3 回滾驗證清單

```
□ requirements.txt 已還原為舊版本約束
□ 所有 builder adapter import 路徑已還原
□ pip install -r requirements.txt 成功
□ pytest tests/unit/integrations/agent_framework/ 全部通過
□ pytest tests/e2e/ 全部通過
□ 手動驗證 Agent 建立和執行流程
□ 手動驗證 GroupChat/Handoff/Magentic 工作流程
```

---

## 5. 漸進式升級方案

### 5.1 三階段升級策略

#### 階段 1: 機械性遷移（Sprint N, 3-5 天, ~13 SP）

**目標**: 修復所有 import 路徑和 API 重新命名，使代碼能在 rc4 下編譯通過。

| 任務 | 檔案 | 變更類型 | 複雜度 | SP |
|------|------|---------|--------|-----|
| 建立功能分支 | — | git | 低 | 0 |
| BC-07: 編排命名空間遷移 | 7 builder 檔案 | import 路徑 | 低 | 3 |
| BC-02: 回應類型重命名 | 搜索所有 `AgentRunResponse` | find & replace | 低 | 2 |
| BC-01: `create_agent` → `as_agent` | `agent_executor.py` | 方法名 | 低 | 1 |
| BC-03: Agent 參數調整 | builder 檔案 | 移除 `display_name`、單數化 `context_provider`、列表化 `middleware` | 中 | 3 |
| BC-04: `source_executor_id` → `executor_id` | `workflow_executor.py`、`events.py` | 屬性名 | 低 | 1 |
| 更新 requirements.txt | 1 行 | 版本約束 | 低 | 1 |
| 單元測試修復 | ~15 檔案 | 更新 import/mock | 中 | 2 |

**驗證閘門**: `pytest tests/unit/integrations/agent_framework/ -v` 全部通過

#### 階段 2: 語意性遷移（Sprint N+1, 3-5 天, ~13 SP）

**目標**: 處理行為變更、例外處理和事件系統重構。

| 任務 | 檔案 | 變更類型 | 複雜度 | SP |
|------|------|---------|--------|-----|
| BC-09: 例外處理層級 | 搜索 `ServiceException` 等舊類 | 替換為 `AgentFrameworkException` | 中 | 3 |
| BC-14: 工作流程事件重構 | `workflow_executor.py`、`events.py` | `isinstance()` → `event.type` | 中高 | 5 |
| BC-08: 統一憑證處理 | `agent_executor.py` | `ad_token_provider` → `credential` | 低 | 1 |
| BC-11: Provider 狀態範圍化 | Checkpoint 相關 | 更新 state access 模式 | 中 | 2 |
| BC-15: Checkpoint 模型更新 | `checkpoint.py` | 適配新 checkpoint 行為 | 中 | 2 |

**驗證閘門**: 完整 `pytest` 通過 + E2E 測試通過

#### 階段 3: 新功能採用（Sprint N+2, 可選, ~8 SP）

**目標**: 利用 rc4 新功能增強 IPA Platform。

| 任務 | 收益 | 複雜度 | SP |
|------|------|--------|-----|
| Claude SDK BaseAgent 整合 | 原生 Claude adapter，取代部分自訂整合 | 低 | 3 |
| 背景回應 | 長時間 Agent 任務支持 | 中 | 3 |
| OpenTelemetry MCP 追蹤 | 端到端分散式追蹤（自動） | 低 | 2 |

### 5.2 功能分支策略

```
main
  └── feature/maf-rc4-upgrade          # 主升級分支
        ├── maf-upgrade/phase1-imports  # 階段 1: import 遷移
        ├── maf-upgrade/phase2-semantics # 階段 2: 語意遷移
        └── maf-upgrade/phase3-features # 階段 3: 新功能（可選）
```

每個子分支完成後 merge 回 `feature/maf-rc4-upgrade`，全部完成後合併回 `main`。

### 5.3 Feature Flag（不建議）

由於 MAF 升級是 import 層級的破壞性變更，Feature Flag 無法有效控制「使用舊 import 還是新 import」。推薦使用 Git 分支策略而非 Feature Flag。

唯一例外：如果需要在同一代碼庫中同時支持 beta 和 rc4，可使用 5.4.C 的條件 Import 相容層，但不推薦。

---

## 6. 風險矩陣

### 6.1 升級風險評估

| 風險項 | 概率 | 影響 | 風險等級 | 緩解措施 |
|--------|------|------|---------|---------|
| BC-07 import 路徑變更導致 7 個 adapter 載入失敗 | **100%** | HIGH | **HIGH** | 機械性搜索替換，低複雜度 |
| BC-14 工作流程事件 isinstance 模式變更導致事件處理異常 | **90%** | HIGH | **HIGH** | 需仔細重構 event handling |
| BC-09 例外處理類不存在導致 try/except 失效 | **80%** | MEDIUM | **MEDIUM** | 搜索替換例外類名稱 |
| BC-03 `context_providers` 單數化導致多 provider 場景失敗 | **70%** | HIGH | **HIGH** | 需重構為 `AggregateContextProvider` 替代方案 |
| BC-11 Provider state 範圍化導致 checkpoint 行為異常 | **60%** | MEDIUM | **MEDIUM** | 需測試驗證 |
| BC-15 Checkpoint 模型變更導致存儲/讀取不相容 | **50%** | MEDIUM | **MEDIUM** | 需詳細驗證 API 差異 |
| BC-08 憑證處理變更導致 Azure 連線失敗 | **40%** | HIGH | **MEDIUM** | 更新 `credential` 參數 |
| 未記錄的破壞性變更 | **20%** | HIGH | **MEDIUM** | 充分的 E2E 測試覆蓋 |
| pip 依賴衝突 | **5%** | LOW | **LOW** | 虛擬環境隔離測試 |
| 升級後效能退化 | **10%** | MEDIUM | **LOW** | 效能測試基線比較 |

### 6.2 不升級的風險

| 風險項 | 概率 | 影響 | 風險等級 |
|--------|------|------|---------|
| MAF 達到 GA 後從 beta API 跳級遷移成本更高 | **95%** | HIGH | **CRITICAL** |
| 錯過 Claude SDK BaseAgent 原生整合機會 | **100%** | MEDIUM | **HIGH** |
| 錯過已修復的 bug（UTC 時區、MCP 重複註冊等） | **100%** | LOW | **MEDIUM** |
| 安全漏洞未獲得 beta 版本修復 | **30%** | HIGH | **MEDIUM** |
| 開發團隊對過時 API 的知識投入浪費 | **80%** | LOW | **LOW** |

### 6.3 風險比較結論

**升級風險**（短期痛苦）< **不升級風險**（長期累積）

升級預估 2-3 Sprint (~34 SP)；延遲升級後從 GA 跳級預估 4-6 Sprint (~60+ SP)。越早升級成本越低。

---

## 7. Go/No-Go 檢查清單

### 7.1 升級前檢查（Pre-Upgrade Checklist）

| # | 檢查項 | 狀態 | 備註 |
|---|--------|------|------|
| 1 | 已建立功能分支 `feature/maf-rc4-upgrade` | □ | 不在 main 上直接操作 |
| 2 | 現有測試套件基線已記錄 | □ | `pytest --tb=no -q > baseline.txt` |
| 3 | 現有測試通過率已知 | □ | V8 盲點 BS-02 指出通過率未知 |
| 4 | 虛擬環境已隔離 | □ | 新 venv 安裝 rc4 |
| 5 | 版本差異分析已讀（本報告 + MAF-Version-Gap-Analysis.md） | □ | 所有 BC-01 至 BC-18 已理解 |
| 6 | [Microsoft Learn 遷移指南](https://learn.microsoft.com/agent-framework/support/upgrade/python-2026-significant-changes) 已讀 | □ | 權威遷移參考 |
| 7 | 團隊成員已知會升級計劃 | □ | 避免同時修改 adapter 檔案 |

### 7.2 階段 1 完成閘門

| # | 驗證項 | 通過標準 |
|---|--------|---------|
| 1 | `pip install agent-framework==1.0.0rc4` 成功 | 無依賴衝突 |
| 2 | `python -c "from agent_framework.orchestrations import GroupChatBuilder"` | import 成功 |
| 3 | `python scripts/verify_official_api_usage.py` | 所有 5 項檢查通過 |
| 4 | `pytest tests/unit/integrations/agent_framework/ -v` | >90% 通過 |
| 5 | 所有 7 個 builder adapter import 已更新 | 無 import 錯誤 |

### 7.3 階段 2 完成閘門

| # | 驗證項 | 通過標準 |
|---|--------|---------|
| 1 | `pytest tests/unit/ -v` | >95% 通過（允許非 MAF 相關失敗） |
| 2 | `pytest tests/integration/ -v` | >90% 通過 |
| 3 | `pytest tests/e2e/ -v` | >85% 通過 |
| 4 | 例外處理測試通過 | 無 `ServiceException` 殘留引用 |
| 5 | 工作流程事件測試通過 | 事件處理正常 |

### 7.4 合併至 main 閘門

| # | 驗證項 | 通過標準 |
|---|--------|---------|
| 1 | 完整測試套件 | 通過率 >= 基線通過率 |
| 2 | 手動 E2E 驗證 | Agent 建立/執行/GroupChat/Handoff/Magentic 正常 |
| 3 | 效能基線比較 | 無顯著退化（<10% 差異） |
| 4 | 代碼審查 | 至少 1 人 review |
| 5 | 回滾測試 | 已驗證 `git revert` 可恢復 |

### 7.5 最終 Go/No-Go 決策

**建議: GO**

| 決策因素 | 評估 |
|---------|------|
| 技術可行性 | **HIGH** — Adapter Pattern 隔離使變更範圍可控（~15-20 檔案, ~225 行） |
| 依賴相容性 | **HIGH** — 無 pip 依賴衝突，pydantic-settings 獨立 |
| 測試覆蓋 | **MEDIUM** — 10 個 MAF 專用測試 + 35+ 相關測試，但 V8 通過率基線未知 |
| 回滾能力 | **HIGH** — Git 分支策略確保快速回滾 |
| 業務價值 | **HIGH** — Claude SDK BaseAgent、背景回應、OTel 追蹤 |
| 延遲成本 | **CRITICAL** — GA 後跳級遷移成本指數增長 |

**執行條件**: 在執行升級前，**必須**先完成以下前提：
1. 確認現有測試套件通過率基線（解決 V8 盲點 BS-02）
2. 建立功能分支並隔離開發
3. 確保 2 個完整 Sprint 的團隊容量

---

## 附錄 A: 受影響檔案完整清單

### Builder Adapters（CRITICAL — 必須修改）

| 檔案 | 現有 MAF Import | 需要變更 | BC 編號 |
|------|----------------|---------|--------|
| `builders/concurrent.py` | `from agent_framework import ConcurrentBuilder` | → `from agent_framework.orchestrations import ConcurrentBuilder` | BC-07 |
| `builders/groupchat.py` | `from agent_framework import GroupChatBuilder` | → `from agent_framework.orchestrations import GroupChatBuilder` | BC-07 |
| `builders/handoff.py` | `from agent_framework import HandoffBuilder, HandoffAgentUserRequest` | → `from agent_framework.orchestrations import ...` | BC-07 |
| `builders/magentic.py` | `from agent_framework import MagenticBuilder, MagenticManagerBase, StandardMagenticManager` | → `from agent_framework.orchestrations import ...` | BC-07 |
| `builders/nested_workflow.py` | `from agent_framework import WorkflowBuilder, Workflow, WorkflowExecutor` | → `from agent_framework.orchestrations import ...` | BC-07 |
| `builders/planning.py` | `from agent_framework import MagenticBuilder, Workflow` | → `from agent_framework.orchestrations import ...` | BC-07 |
| `builders/workflow_executor.py` | `from agent_framework import WorkflowExecutor, SubWorkflowRequestMessage, SubWorkflowResponseMessage` | → `from agent_framework.orchestrations import ...` | BC-07 |

### Core / Checkpoint（HIGH — 需要修改）

| 檔案 | 現有 MAF Import | 需要變更 | BC 編號 |
|------|----------------|---------|--------|
| `builders/agent_executor.py` | `from agent_framework import ChatAgent, ChatMessage, Role` + `AzureOpenAIResponsesClient` | 更新 `create_agent`→`as_agent`，`credential`參數 | BC-01, BC-08 |
| `core/events.py` | `from agent_framework import WorkflowStatusEvent` | 驗證事件類型是否仍存在或改為 `WorkflowEvent[DataT]` | BC-14 |
| `core/approval.py` | `from agent_framework import Executor, handler, WorkflowContext` | 驗證是否仍在 root namespace | BC-07 |
| `core/approval_workflow.py` | `from agent_framework import Workflow, Edge` | 驗證是否遷移至子命名空間 | BC-07 |
| `core/edge.py` | `from agent_framework import Edge` | 驗證是否遷移至子命名空間 | BC-07 |
| `checkpoint.py` | `from agent_framework import WorkflowCheckpoint` | 驗證 checkpoint 模型變更 | BC-15 |
| `multiturn/checkpoint_storage.py` | `from agent_framework import CheckpointStorage, InMemoryCheckpointStorage` | 驗證 `source_id` 預設值變更 | BC-11 |

### 測試檔案（需同步更新）

升級後需修改的測試檔案約 35+ 個，詳見第 3 節。

---

## 附錄 B: 關鍵 Breaking Change 快速參考卡

| BC | 變更 | 搜索關鍵字 | 替換為 |
|----|------|-----------|--------|
| BC-01 | `create_agent()` → `as_agent()` | `create_agent` | `as_agent` |
| BC-02 | `AgentRunResponse` → `AgentResponse` | `AgentRunResponse` | `AgentResponse` |
| BC-03 | `display_name` 移除 | `display_name` | （刪除） |
| BC-03 | `context_providers` → `context_provider` | `context_providers` | `context_provider` |
| BC-03 | `middleware=single` → `middleware=[list]` | `middleware=` | `middleware=[...]` |
| BC-04 | `source_executor_id` → `executor_id` | `source_executor_id` | `executor_id` |
| BC-07 | `from agent_framework import *Builder` | `from agent_framework import` | `from agent_framework.orchestrations import` |
| BC-08 | `ad_token_provider` → `credential` | `ad_token_provider` | `credential` |
| BC-09 | `ServiceException` → `AgentFrameworkException` | `ServiceException` | `AgentFrameworkException` |
| BC-14 | `isinstance(event, SubClass)` → `event.type` | `isinstance.*Event` | `event.type ==` |

---

*Report generated: 2026-03-15*
*Analyst: Architecture Review Agent*
*Based on: V8 Analysis (2026-03-15) + MAF Version Gap Analysis + 6 Expert Reports + ARB Consensus Report*
