# 術語表（Glossary）

**建立日期**：2026-04-23
**版本**：V2.0

---

## 核心架構術語

### Agent Harness
> 包裹 LLM 的執行框架，實現完整 agent loop（包含 11 範疇）。本項目 V2 的核心建設目標。

### TAO Loop / ReAct Loop
> Thought-Action-Observation 循環。Agent 思考 → 行動（呼叫工具）→ 觀察結果 → 再思考。範疇 1 的核心。

### Loop / Pipeline 區別
- **Loop**：可多輪迭代，stop_reason 驅動退出，工具結果回注
- **Pipeline**：線性順序執行，跑完就結束（V1 的問題）

### 主流量（Main Flow / Production Path）
> UnifiedChat → API → Agent Loop 的完整路徑。V2 約束：所有功能必須能在主流量驗證。

### Side-track Code
> 代碼存在但不在主流量（PoC、實驗、僵屍代碼）。V1 的問題之一。

### Potemkin Feature
> 結構槽位但無實際內容的功能（如 V1 的 Step 1 memory_read 跑了但沒讀 mem0）。Anti-Pattern 4。

---

## 11 範疇術語

### 範疇 1：Orchestrator Loop
- **stop_reason**：LLM 回應中表示「為何停止」的欄位（end_turn / tool_use / max_tokens 等）
- **end_turn**：模型自然結束輸出
- **tool_use**：模型要求呼叫工具
- **turn**：loop 一輪迭代

### 範疇 2：Tool Layer
- **ToolSpec**：工具的統一規格（name / description / schema / handler / permissions）
- **ToolRegistry**：工具註冊中心
- **Sandbox**：工具執行的隔離環境
- **Mutating tool**：會改變狀態的工具（必須序列執行）
- **Read-only tool**：純讀取工具（可並行）

### 範疇 3：Memory
- **5 層記憶**：System / Tenant / Role / User / Session
- **Memory as Tool**：把 memory 暴露為 agent 可呼叫的工具（CC 模式）
- **線索→驗證**：CC 設計哲學，記憶視為線索，行動前用工具驗證

### 範疇 4：Context Management
- **Context Rot**：上下文劣化（30%+ 性能下降當關鍵內容在中間位置）
- **Lost in the Middle**：Stanford 研究，重要內容應在開頭/結尾
- **Compaction**：壓縮對話歷史
- **Observation Masking**：遮蔽舊工具輸出但保留呼叫記錄
- **Just-in-Time Retrieval**：按需載入而非全量載入

### 範疇 5：Prompt Construction
- **PromptBuilder**：統一的 prompt 組裝器
- **階層組裝**：System → Tools → Memory → History → User
- **Position Strategy**：位置策略（lost-in-middle aware / naive / tools_at_end）

### 範疇 6：Output Parsing
- **Native Tool Calling**：模型直接返回 tool_calls 物件（非文本解析）
- **tool_calls**：OpenAI / Anthropic 標準的工具呼叫結構

### 範疇 7：State Management
- **LoopState**：Typed dataclass 描述當前 loop 狀態
- **Checkpoint**：狀態快照（可恢復點）
- **Time-Travel Debug**：回到特定 checkpoint 重現狀態
- **Super-step**：每輪 loop 完成時的快照點

### 範疇 8：Error Handling
- **4 類錯誤**：Transient / LLM-Recoverable / User-Fixable / Unexpected
- **Retry Policy**：重試策略（cap = 2，業界標準）
- **LLM-Recoverable**：失敗回注 LLM 讓它自我修正

### 範疇 9：Guardrails & Safety
- **Input Guardrail**：輸入檢查（PII / jailbreak）
- **Output Guardrail**：輸出檢查（毒性 / 敏感）
- **Tool Guardrail**：工具檢查（權限 / 風險）
- **Tripwire**：觸發即中斷的安全機制
- **權限與推理分離**：LLM 決定意圖，Tool 系統決定能否執行
- **HITL（Human-in-the-Loop）**：人工介入審批

### 範疇 10：Verification Loops
- **Rules-Based Verifier**：規則驗證（schema / business rules）
- **LLM-as-Judge**：用獨立 LLM 評估輸出
- **Visual Verifier**：截圖驗證（UI 任務用，企業少用）
- **Self-Correction**：失敗自動修正並重試

### 範疇 11：Subagent Orchestration
- **Fork**：byte-identical 父 context 副本
- **Teammate**：獨立 context + mailbox 通信
- **Handoff**：完全交棒，父退出
- **As Tool**：subagent 包裝為 tool（OpenAI 模式）

---

## V2 架構術語

### 4 層架構
1. **Agent Harness**：11 範疇核心
2. **Platform**：治理 / 多租戶 / 認證 / 可觀測性
3. **Adapters**：LLM 供應商 / MAF / MCP 適配
4. **Infrastructure**：DB / Cache / MQ / Storage

### Adapter Pattern
> 透過 ABC 解耦 agent_harness 與具體 LLM 供應商。所有 LLM 呼叫透過 `adapters/_base/chat_client.py`。

### Multi-Tenancy（多租戶）
> 同一系統服務多個 tenant（公司 / 部門），資料 / 記憶 / 權限隔離。

### Tenant Context
> 每個請求攜帶的 tenant_id，貫穿整個 agent loop。

### RBAC（Role-Based Access Control）
> 角色基礎的存取控制。User → Role → Permissions。

---

## V1 / V2 對應術語

| V1 術語 | V2 對應 | 說明 |
|--------|--------|------|
| Pipeline | Loop | 完全不同概念，V2 拋棄 Pipeline 思維 |
| Step | Turn | Loop 中的一輪 |
| Dispatch | Tool execution | 不再是分派，是工具呼叫 |
| Intent Router | （無） | LLM 自主路由，不需要 router |
| Pipeline Step | （無） | V2 沒有 step 概念 |
| Hybrid | （無） | V2 透過 adapter 解耦，不需要 hybrid bridge |
| Pipeline Context | LoopState | Typed state |
| MAF Builder | Subagent | MAF builders 透過 subagent tool 觸發 |
| HITLPauseException | Pause checkpoint | V2 用 state-based pause |
| DialogPauseException | Approval checkpoint | 同上 |

---

## CC 術語對應

| CC 術語 | V2 對應 |
|--------|--------|
| query() | AgentLoop.run() |
| StreamEvent | LoopEvent |
| ToolUseContext | ToolContext |
| canUseTool | GuardrailEngine.check_tool_call() |
| autoCompactIfNeeded | ContextCompactor.should_compact() |
| QueryEngine | （API + Worker） |
| getAttachmentMessages | PromptBuilder（注入 memory layers） |
| FallbackTriggeredError | RetryPolicy 觸發 |
| StreamingToolExecutor | ToolExecutor |
| AsyncGenerator | AsyncIterator (SSE 推送) |
| ~/.claude/memory/ | Layer 4 User Memory |
| CLAUDE.md（project）| Layer 2 Tenant Memory |
| CLAUDE.md（global）| Layer 1 System Memory |

---

## 評分系統術語

### Level（成熟度等級）
| Level | 含義 |
|-------|------|
| 0 | 完全沒實作 |
| 1 | 代碼存在但未接入主流量 |
| 2 | 已接入但未測試 |
| 3 | 接入且基本測試 |
| 4 | 主流量運行 + 測試 + 部分業界對齊 |
| 5 | 完整對齊業界最佳實踐 |

### 對齊度（Alignment）
> 與業界最佳實踐的吻合程度。V1 = 27%，V2 目標 = 75%+。

---

## 開發流程術語

### Sprint
> 1 週的工作週期。

### Phase
> 一組相關 Sprint 的集合（通常 2-3 sprint）。

### Plan + Checklist
> 每個 Sprint 必須有的兩個文件：
- Plan：說明做什麼、為什麼、預期成果
- Checklist：可勾選的任務清單

### Retrospective（Retro）
> Sprint 結束的回顧會議 / 文件。

### Anti-Pattern Audit
> 每 Sprint 結束檢查 10 個 anti-patterns 違反次數。

### Definition of Done (DoD)
> 完成標準。V2 對範疇實作的 DoD 包含「負面測試」要求。

---

## 部署術語

### Greenfield
> 全新建立（無歷史包袱）。V2 的 85%。

### Migration
> 從舊版過渡（漸進改）。V2 的 10%（infrastructure）。

### Wrap
> 邏輯保留 + 介面重寫。V2 用於業務領域。

### Archive
> 封存。V2 把 V1 整體 archive。

### Canary
> 小範圍試用部署。Phase 55 Sprint 2 用。

---

## 業務領域術語

### Patrol
> IT 巡檢。檢查伺服器、網路、資源狀態。

### Correlation
> 關聯分析。多個 alert 是否同一根因。

### Root Cause
> 根因分析。

### Incident
> 事件。需處理的問題。

### Audit（業務）
> 業務稽核（區別於 platform.governance.audit 的審計日誌）。

### IT-Ops
> IT Operations，本項目的業務領域。

---

## 文件導航

從這個 glossary 連到具體文件：
- 11 範疇詳細：→ `01-eleven-categories-spec.md`
- 架構：→ `02-architecture-design.md`
- 重生策略：→ `03-rebirth-strategy.md`
- 反模式：→ `04-anti-patterns.md`
- 參考策略：→ `05-reference-strategy.md`
- 路線圖：→ `06-phase-roadmap.md`
- 技術選型：→ `07-tech-stack-decisions.md`
