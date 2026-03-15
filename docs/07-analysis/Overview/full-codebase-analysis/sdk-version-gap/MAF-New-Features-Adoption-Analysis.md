# MAF 新功能採用可行性分析

**分析日期**: 2026-03-15
**目前版本**: `agent-framework>=1.0.0b260114`
**目標版本**: `1.0.0rc4`（2026-03-11）
**分析範圍**: 7 項新功能對 IPA Platform 的採用可行性
**相關文件**: [MAF-Version-Gap-Analysis.md](MAF-Version-Gap-Analysis.md) | [Claude-SDK-Version-Gap-Analysis.md](Claude-SDK-Version-Gap-Analysis.md)

---

## 執行摘要

IPA Platform 升級至 MAF `1.0.0rc4` 時，有 7 項新功能可考慮一併採用。經分析，建議分為三個採用批次：

| 批次 | 功能 | 時機 | 理由 |
|------|------|------|------|
| **A - 升級時立即啟用** | OpenTelemetry MCP 追蹤、背景回應 + Continuation Tokens | 與升級同步 | 配置即用，低風險 |
| **B - 升級後 1-2 Sprint** | Agent Skills、HITL 工具呼叫審批 | Sprint 108-109 | 中等工作量，高價值 |
| **C - 延後評估** | Claude SDK BaseAgent、宣告式 YAML 工作流程、自主切換流程 | Sprint 110+ | 大範圍重構，需謹慎規劃 |

---

## 各功能評估

---

### 功能 1: Claude SDK BaseAgent（b260130 - `agent-framework-claude`）

**版本引入**: `1.0.0b260130`（2026-01-30）
**官方套件**: `agent-framework-claude`
**相關 PR**: [#3653](https://github.com/microsoft/agent-framework/pull/3653), [#3655](https://github.com/microsoft/agent-framework/pull/3655), [#4137](https://github.com/microsoft/agent-framework/pull/4137), [#4278](https://github.com/microsoft/agent-framework/pull/4278)

#### 可行性: MEDIUM

#### 現狀分析

IPA Platform 的 `backend/src/integrations/claude_sdk/` 是一個**47 檔、~15K LOC 的完全自建抽象層**，包含：

| 子模組 | 檔案數 | 功能 | 官方替代 |
|--------|--------|------|----------|
| `autonomous/` | 8 | 自主規劃、執行、分析、驗證、重試、回退 | 無直接替代 |
| `hooks/` | 6 | 審批、稽核、速率限制、沙箱 | `claude-agent-sdk` hooks 部分重疊 |
| `hybrid/` | 6 | 能力選擇、編排、同步 | 無直接替代 |
| `mcp/` | 4+ | MCP 發現、整合、管理 | `agent-framework-claude` MCP 支援 |
| `tools/` | 4+ | 工具定義、路由 | `agent-framework-claude` 工具支援 |
| `orchestrator/` | 4+ | 編排邏輯 | 部分由 MAF orchestrators 覆蓋 |
| 根目錄 | 5 | client.py, session.py, session_state.py, query.py, config.py | `ClaudeAgent` BaseAgent |

#### 官方 `agent-framework-claude` 提供什麼

- `ClaudeAgent` 實作 MAF `BaseAgent` 介面
- 與 MAF orchestrators（Sequential, Concurrent, Handoff, GroupChat）無縫整合
- OpenTelemetry 自動 instrumentation（rc3 新增 [#4278](https://github.com/microsoft/agent-framework/pull/4278)）
- Structured output 支援（rc2 修復 [#4137](https://github.com/microsoft/agent-framework/pull/4137)）
- 串流支援（`run_stream()`）
- 嵌套 Pydantic 模型的 JSON schema 保留

#### 可替代 vs 必須保留

| 組件 | 可否替代 | 原因 |
|------|----------|------|
| `client.py` (基本 API 呼叫) | **可替代** | `ClaudeAgent` 已封裝 Anthropic API |
| `session.py` / `session_state.py` | **部分替代** | MAF 有 session/history provider，但 IPA 的跨會話狀態持久化較特殊 |
| `query.py` | **可替代** | `agent.run()` / `agent.run_stream()` |
| `autonomous/` (8 檔) | **必須保留** | 自主規劃/執行/驗證是 IPA 獨特功能，MAF 無對應 |
| `hooks/` (6 檔) | **部分替代** | 審批 hook 可映射到 MAF middleware，但沙箱/速率限制是自定義 |
| `hybrid/` (6 檔) | **必須保留** | MAF/Claude 混合編排是 IPA 核心架構 |
| `mcp/` (4+ 檔) | **可替代** | `agent-framework-claude` 已支援 MCP 工具 |
| `tools/` (4+ 檔) | **部分替代** | 基本工具定義可用 MAF `@tool`，但自定義路由需保留 |

#### 建議: **延後採用（Phase C）**

#### 影響範圍
- `backend/src/integrations/claude_sdk/` — 47 檔案
- `backend/src/integrations/hybrid/` — 全部依賴 claude_sdk
- `backend/src/api/v1/` — claude_sdk 相關的 API 路由

#### 工作量: **8-12 Story Points**（僅替代可替代部分），**20-30 Story Points**（全面重構）

#### 風險
- **HIGH**: 47 檔的自建模組與官方 `ClaudeAgent` 的 API 差異大，需要大量適配
- **MEDIUM**: `autonomous/` 和 `hybrid/` 完全無官方替代，必須保持混合架構
- **LOW**: `agent-framework-claude` 在 rc2-rc4 期間已修復多個 bug，穩定性可接受

#### 與現有程式碼的關係: **互補** — 建議在 Adapter 層引入 `ClaudeAgent` 作為新的後端選項，而非替代整個 claude_sdk 模組

---

### 功能 2: 宣告式 YAML 工作流程（b260114 - `agent-framework-declarative`）

**版本引入**: `1.0.0b260114`（初始），rc2 新增 `InvokeFunctionTool` [#3716](https://github.com/microsoft/agent-framework/pull/3716)
**官方套件**: `agent-framework-declarative`
**文件**: [Declarative Workflows - Overview](https://learn.microsoft.com/en-us/agent-framework/workflows/declarative)

#### 可行性: LOW-MEDIUM

#### 現狀分析

IPA Platform 的工作流程系統由兩層構成：

**Builder 層**（`backend/src/integrations/agent_framework/builders/`）— 24 個 Builder 檔案：
- `workflow_executor.py`, `workflow_executor_migration.py` — 工作流程執行
- `nested_workflow.py` — 巢狀工作流程
- `concurrent.py`, `concurrent_migration.py` — 並行執行
- `groupchat.py`, `groupchat_orchestrator.py`, `groupchat_voting.py` — 群組協作
- `handoff.py`, `handoff_capability.py`, `handoff_context.py`, `handoff_hitl.py`, `handoff_policy.py` — 交接
- `edge_routing.py`, `planning.py` — 路由與規劃

**Domain 層**（`backend/src/domain/workflows/`）— 業務邏輯層：
- `models.py`, `repository.py`, `service.py` — 工作流程 CRUD
- `execution_service.py`, `executor.py` — 執行引擎
- `state_machine.py` — 狀態管理

#### 官方宣告式工作流程提供什麼

- YAML 定義多代理編排（Variable Management, Control Flow, Agent/Tool Invocation, HITL）
- Python 支援 action 類型：`SetVariable`, `If`, `Foreach`, `RepeatUntil`, `SendActivity`, `EmitEvent`, `InvokeAzureAgent`, `InvokeFunctionTool`, `Question`, `Confirmation`, `WaitForInput`, `EndWorkflow`
- `WorkflowFactory` 載入 YAML 並執行
- 函式工具透過 `register_tool()` 註冊

#### 遷移可行性分析

| 現有模式 | YAML 可表達 | 限制 |
|----------|------------|------|
| Sequential workflow | **Yes** | 完全支援 |
| Concurrent execution | **Partial** | YAML 無原生並行 action |
| GroupChat orchestration | **No** | 需要程式碼定義投票/輪轉邏輯 |
| Handoff with context | **Partial** | 基本 handoff 可以，複雜策略需程式碼 |
| Edge routing | **No** | 動態路由邏輯超出 YAML 能力 |
| HITL approval | **Yes** | `Question`, `Confirmation`, `WaitForInput` |
| Nested workflow | **Yes** | 透過 `CreateConversation` |

#### 建議: **延後採用（Phase C）— 新工作流程優先使用，不遷移現有**

#### 影響範圍
- 新增 `backend/src/integrations/agent_framework/declarative/` 目錄
- 新增 YAML 工作流程定義檔案
- 不影響現有 24 個 Builder 檔案

#### 工作量: **5-8 Story Points**（建立基礎架構 + 1-2 個範例工作流程）

#### 風險
- **MEDIUM**: Python 的 `InvokeMcpTool` action 尚未支援（僅 C#），限制 MCP 整合
- **LOW**: 現有程式碼定義工作流程可與宣告式工作流程共存
- **LOW**: YAML 工作流程是可選的附加功能，不影響現有系統

#### 與現有程式碼的關係: **互補** — 建議新的簡單工作流程使用 YAML 定義，複雜工作流程保持程式碼定義

---

### 功能 3: Agent Skills（rc2 - `agent-framework-core`）

**版本引入**: `1.0.0rc2`（2026-02-25），rc4 新增 `forward runtime kwargs` [#4417](https://github.com/microsoft/agent-framework/pull/4417)
**官方文件**: [Agent Skills](https://learn.microsoft.com/en-us/agent-framework/agents/skills)
**相關部落格**: [Agent Skills Domain Expertise](https://devblogs.microsoft.com/semantic-kernel/give-your-agents-domain-expertise-with-agent-skills-in-microsoft-agent-framework/)

#### 可行性: HIGH

#### 現狀分析

IPA Platform 目前的工具/能力系統：
- `backend/src/integrations/agent_framework/builders/handoff_capability.py` — 能力匹配
- `backend/src/integrations/mcp/servers/` — 5 個 MCP server（ADF, Azure, Filesystem, LDAP, Shell/SSH）
- `backend/src/integrations/claude_sdk/tools/` — Claude 工具定義
- 各種分散的領域知識嵌入在 prompt 和程式碼中

#### 官方 Agent Skills 提供什麼

- **SKILL.md 格式**: YAML frontmatter + Markdown 指示，標準化技能定義
- **漸進式揭示（Progressive Disclosure）**: 3 階段模式
  1. **Advertise**（~100 tokens/skill）— 名稱 + 描述注入系統提示
  2. **Load**（< 5000 tokens）— 按需載入完整指示
  3. **Read Resources**（按需）— 載入參考文件、範本、腳本
- **SkillsProvider**: 從檔案系統掃描 `SKILL.md`，自動注入 `load_skill` 和 `read_skill_resource` 工具
- **Code Skills**: 可執行腳本（Python），帶審批機制
- **可移植性**: 跨 Agent Skills 相容產品共用

#### 採用策略

| 使用情境 | 適用性 | 範例 |
|----------|--------|------|
| MCP Server 操作指南 | **HIGH** | 將 ADF/Azure/LDAP 操作步驟封裝為 Skills |
| 企業政策知識 | **HIGH** | 費用報銷、合規檢查、安全政策 |
| 資料分析流程 | **HIGH** | 數據管線操作、報表生成 |
| 工具使用指南 | **MEDIUM** | 教 agent 如何使用特定工具 |
| 程式碼生成範本 | **MEDIUM** | 標準化程式碼模式 |

#### 建議: **升級後 1 Sprint 採用（Phase B）**

#### 影響範圍
- 新增 `backend/skills/` 目錄結構
- 修改 agent 建構邏輯，加入 `SkillsProvider` 作為 context provider
- 不影響現有工具定義

#### 工作量: **5-8 Story Points**
- 2 pts: 建立 Skills 基礎架構和 SkillsProvider 整合
- 3-6 pts: 將 3-5 個現有領域知識轉換為 SKILL.md 格式

#### 風險
- **LOW**: Agent Skills 是純附加功能，不修改現有程式碼
- **LOW**: Progressive disclosure 設計對 context window 友好
- **MEDIUM**: 需要團隊學習 SKILL.md 撰寫規範

#### 與現有程式碼的關係: **互補** — Skills 補充現有工具系統，不替代

---

### 功能 4: OpenTelemetry MCP 追蹤（rc1）

**版本引入**: `1.0.0rc1`（2026-02-19）[#3780](https://github.com/microsoft/agent-framework/pull/3780)
**增強**: rc3 新增 `ClaudeAgent` OpenTelemetry instrumentation [#4278](https://github.com/microsoft/agent-framework/pull/4278), [#4326](https://github.com/microsoft/agent-framework/pull/4326)
**官方文件**: [Observability](https://learn.microsoft.com/en-us/agent-framework/tutorials/agents/enable-observability)

#### 可行性: HIGH

#### 現狀分析

IPA Platform 的可觀測性系統：
- `backend/src/integrations/mcp/security/audit.py` — MCP 安全稽核（自建）
- `backend/src/integrations/mcp/security/redis_audit.py` — Redis 稽核儲存
- `backend/src/integrations/audit/` — 決策稽核追蹤器
- 無統一的分散式追蹤

#### 官方 OpenTelemetry 提供什麼

- **自動注入 trace context 到 MCP 請求** — 每個 MCP 工具呼叫自動帶有 trace ID
- **Agent invocation spans** — `invoke_agent` span 包含系統指令屬性
- **ClaudeAgent instrumentation** — Claude 代理的 API 呼叫自動追蹤
- **與 Azure Monitor / Jaeger / Zipkin 整合** — 標準 OTLP 匯出

#### 啟用方式

```python
# 僅需安裝 OpenTelemetry 套件並配置 exporter
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)

# MAF 自動 instrument — 無需修改應用程式碼
```

#### 建議: **升級時立即啟用（Phase A）**

#### 影響範圍
- `requirements.txt` — 新增 `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`
- `backend/src/core/` — 新增 OTel 初始化配置
- 現有 MCP 程式碼**無需修改** — MAF 自動注入

#### 工作量: **2-3 Story Points**
- 1 pt: 安裝 OTel 依賴並配置 exporter
- 1-2 pts: 整合 Azure Monitor 或自建 Jaeger 實例

#### 風險
- **LOW**: 純觀測功能，不影響業務邏輯
- **LOW**: OTel 是業界標準，成熟穩定
- **NEGLIGIBLE**: 效能影響極小（非同步 span 匯出）

#### 與現有程式碼的關係: **互補** — 增強現有的 audit/security 系統，提供端到端追蹤

---

### 功能 5: 背景回應 + Continuation Tokens（b260210）

**版本引入**: `1.0.0b260210`（2026-02-10）[#3808](https://github.com/microsoft/agent-framework/pull/3808)
**核心組件**: `ContinuationToken` TypedDict, `background` option in `OpenAIResponsesOptions`

#### 可行性: HIGH

#### 現狀分析

IPA Platform 的長時間運行任務處理：
- `backend/src/integrations/claude_sdk/autonomous/executor.py` — 自主執行器（同步等待）
- `backend/src/integrations/claude_sdk/autonomous/planner.py` — 規劃器（同步）
- `backend/src/integrations/hybrid/orchestrator_v2.py` — 54K LOC 混合編排器
- 前端使用 SSE 串流，但後端代理執行仍為阻塞式

#### 官方背景回應提供什麼

- **ContinuationToken**: 長時間運行的代理任務可以暫停並在稍後恢復
- **background 選項**: 代理可在背景執行，不阻塞 HTTP 請求
- **Token 傳播**: Continuation token 透過 response 類型自動傳播
- **適用場景**: 複雜分析、多步驟工作流程、需要外部審批的流程

#### 採用策略

| IPA 使用情境 | 適用性 | 效益 |
|-------------|--------|------|
| 自主規劃+執行 | **HIGH** | 避免 HTTP timeout，改善使用者體驗 |
| 多步驟工作流程 | **HIGH** | 長工作流程不再阻塞前端 |
| HITL 審批等待 | **MEDIUM** | 代理可暫停等待審批，不佔用資源 |
| Swarm 協作 | **MEDIUM** | 多代理協作可用 continuation tokens 協調 |

#### 建議: **升級時立即啟用（Phase A）**

#### 影響範圍
- `backend/src/integrations/agent_framework/core/execution.py` — 使用 `ContinuationToken`
- `backend/src/api/v1/executions/` — API 回應增加 continuation token
- 前端需調整以輪詢/恢復背景任務

#### 工作量: **3-5 Story Points**
- 2 pts: 後端整合 ContinuationToken 到執行引擎
- 1-3 pts: 前端輪詢機制和 UI 調整

#### 風險
- **LOW**: 背景回應是可選功能，不影響現有同步流程
- **MEDIUM**: 需要前後端協調，確保 token 正確傳遞和恢復
- **LOW**: 主要針對 OpenAI Responses API，Claude 路徑需額外適配

#### 與現有程式碼的關係: **互補** — 增強現有的執行引擎，不替代

---

### 功能 6: HITL 工具呼叫審批（rc1 - #4054）

**版本引入**: `1.0.0rc1`（2026-02-19）[#4054](https://github.com/microsoft/agent-framework/pull/4054)
**功能描述**: 修復 hosted MCP tool approval flow for all session/streaming combinations

#### 可行性: HIGH

#### 現狀分析

IPA Platform 有兩套 HITL 系統：

**MAF 側**（`backend/src/integrations/agent_framework/core/`）：
- `approval.py` — ~29K 的審批機制（自建，包裝 MAF API）
- `approval_workflow.py` — ~18K 的審批工作流程

**Orchestration 側**（`backend/src/integrations/orchestration/hitl/`）：
- `controller.py` — ~27K 的 HITL 控制器
- `approval_handler.py` — 審批處理器
- `notification.py` — 通知系統

**問題**: 兩套系統並行，存在邏輯重複和同步挑戰。

#### 官方 HITL 提供什麼

- **工具級審批**: 標記特定工具為需要人工審批
- **Session/Streaming 完整支援**: rc1 修復了所有 session/streaming 組合的審批流程
- **宣告式 HITL actions**: `Question`, `Confirmation`, `RequestExternalInput`, `WaitForInput`
- **與 MCP 工具整合**: hosted MCP 工具的審批流程

#### 整合策略

```
目前架構:
  approval.py (MAF 包裝) ──┐
                            ├── 審批決策
  hitl/controller.py ──────┘

建議架構:
  MAF 原生 tool approval ─── 工具呼叫審批（簡單場景）
  hitl/controller.py ──────── 複雜審批工作流程（多步驟、條件式）
  approval.py ────────────── 跨框架審批協調（MAF + Claude）
```

#### 建議: **升級後 1 Sprint 採用（Phase B）**

#### 影響範圍
- `backend/src/integrations/agent_framework/core/approval.py` — 重構以使用官方 API
- `backend/src/integrations/agent_framework/builders/handoff_hitl.py` — 更新
- `backend/src/integrations/orchestration/hitl/` — 簡化，移除與 MAF 重複的邏輯

#### 工作量: **5-8 Story Points**
- 3 pts: 重構 approval.py 使用官方 tool approval API
- 2-5 pts: 整合 orchestration/hitl 與 MAF 原生 HITL

#### 風險
- **MEDIUM**: 兩套 HITL 系統整合需要仔細測試所有審批路徑
- **LOW**: 官方 API 在 rc1 已修復所有 session/streaming 組合
- **MEDIUM**: 需要確保 Claude 路徑的審批流程也能對接

#### 與現有程式碼的關係: **部分替代** — 官方 HITL 可替代 MAF 側的自建審批，但 orchestration 側的複雜流程需保留

---

### 功能 7: 自主切換流程（#2497 — 模式切換優化）

**相關版本**: 多版本累積改進
**IPA 對應模組**: `backend/src/integrations/hybrid/switching/`

#### 可行性: LOW

#### 現狀分析

IPA Platform 有一套完整的自建切換系統（`hybrid/switching/`，12 檔案）：

| 檔案 | 功能 | LOC |
|------|------|-----|
| `switcher.py` | 核心切換邏輯（ModeSwitcher） | ~29K |
| `models.py` | 切換模型定義 | — |
| `redis_checkpoint.py` | Redis 檢查點 | — |
| `triggers/base.py` | 觸發器基類 | — |
| `triggers/complexity.py` | 複雜度觸發器 | — |
| `triggers/failure.py` | 失敗觸發器 | — |
| `triggers/resource.py` | 資源觸發器 | — |
| `triggers/user.py` | 使用者觸發器 | — |
| `migration/state_migrator.py` | 狀態遷移 | — |

#### 官方切換支援現狀

MAF rc4 的切換/handoff 機制：
- `HandoffAgent` — 代理間交接
- `as_tool()` + `propagate_session`（rc4 [#4439](https://github.com/microsoft/agent-framework/pull/4439)）— agent-as-tool 模式
- 但**無原生的 MAF ↔ Claude 框架切換**概念

#### 分析

IPA 的切換系統是**針對 MAF/Claude 混合架構的獨特設計**：
1. **Complexity Trigger**: 任務複雜度超過閾值 → 切換到 Claude 自主模式
2. **Failure Trigger**: MAF agent 失敗 → fallback 到 Claude
3. **Resource Trigger**: 資源使用超限 → 切換到輕量模式
4. **User Trigger**: 使用者明確要求切換

這個概念在 MAF 官方中**完全沒有對應物**。MAF 的 handoff 是代理間交接，不是框架間切換。

#### 建議: **不採用（保持自建）**

#### 影響範圍: 無

#### 工作量: N/A

#### 風險
- 無風險 — 保持現有架構
- 未來可關注 MAF 是否新增跨框架編排概念

#### 與現有程式碼的關係: **無關** — MAF 無對應功能，IPA 自建系統是獨特競爭優勢

---

## 採用優先級排序

| 優先級 | 功能 | 可行性 | 價值 | 風險 | 工作量 | 建議時機 |
|--------|------|--------|------|------|--------|----------|
| **P1** | OpenTelemetry MCP 追蹤 | HIGH | HIGH | LOW | 2-3 SP | 升級時 |
| **P2** | 背景回應 + Continuation Tokens | HIGH | HIGH | LOW-MED | 3-5 SP | 升級時 |
| **P3** | Agent Skills | HIGH | HIGH | LOW | 5-8 SP | Sprint 108 |
| **P4** | HITL 工具呼叫審批 | HIGH | MEDIUM | MEDIUM | 5-8 SP | Sprint 108-109 |
| **P5** | 宣告式 YAML 工作流程 | LOW-MED | MEDIUM | MEDIUM | 5-8 SP | Sprint 110+ |
| **P6** | Claude SDK BaseAgent | MEDIUM | MEDIUM | HIGH | 8-30 SP | Sprint 110+ |
| **P7** | 自主切換流程 | LOW | LOW | N/A | N/A | 不採用 |

---

## 採用路線圖建議

### Phase A: 與升級同步（Sprint 107）
**工作量**: 5-8 Story Points（與版本升級的 15+ SP 合併）

1. **OpenTelemetry MCP 追蹤** — 安裝依賴 + 配置 exporter，MAF 自動 instrument
2. **背景回應 + Continuation Tokens** — 在執行引擎啟用 background 選項

### Phase B: 升級後 1-2 Sprint（Sprint 108-109）
**工作量**: 10-16 Story Points

3. **Agent Skills** — 建立 Skills 基礎架構，轉換 3-5 個領域知識為 SKILL.md
4. **HITL 工具呼叫審批** — 重構 approval.py，整合官方 tool approval API

### Phase C: 延後評估（Sprint 110+）
**工作量**: 13-38 Story Points（視範圍而定）

5. **宣告式 YAML 工作流程** — 新工作流程使用 YAML，不遷移現有
6. **Claude SDK BaseAgent** — 在 Adapter 層引入 `ClaudeAgent`，逐步替代可替代組件

### 不採用
7. **自主切換流程** — IPA 的混合切換系統是獨特設計，MAF 無對應功能

---

## 依賴關係圖

```
MAF rc4 升級（先決條件）
    ├── Phase A（同步）
    │   ├── P1: OpenTelemetry（無依賴）
    │   └── P2: Continuation Tokens（依賴 API 更新）
    │
    ├── Phase B（升級穩定後）
    │   ├── P3: Agent Skills（無依賴）
    │   └── P4: HITL 審批（依賴 P1 的追蹤能力驗證審批流程）
    │
    └── Phase C（長期）
        ├── P5: YAML 工作流程（可獨立進行）
        └── P6: Claude BaseAgent（依賴 P4 的 HITL 整合經驗）
```

---

## 總結

升級至 MAF `1.0.0rc4` 是必要的（API 穩定化、bug 修復、安全改進），而新功能採用應分批進行。**Phase A 的 OTel 和 Continuation Tokens 幾乎是「免費」的收益**，僅需配置即可啟用。**Phase B 的 Agent Skills 和 HITL 改進帶來最高 ROI**，建議優先投入。Phase C 的大型重構應在充分驗證 rc4 穩定性後再啟動。

**關鍵決策點**: Claude SDK BaseAgent 的採用策略需要架構委員會討論 — 是維持 47 檔自建模組，還是逐步遷移到官方 `ClaudeAgent` + 保留自定義擴充。建議在 Phase B 完成後，基於實際 rc4 使用經驗做出決定。
