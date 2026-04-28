# 參考資料策略（Reference Strategy）

**建立日期**：2026-04-23
**版本**：V2.0

---

## 參考資料層級

V2 開發過程中可隨時參考以下 4 層資料：

```
Layer 1: 業界標準（最權威）
  └─ 11 範疇定義（本規劃文件）

Layer 2: CC 源碼研究（最完整實作參考）
  └─ docs/07-analysis/claude-code-study/

Layer 3: V1 寶貴邏輯（避免重複造輪子）
  └─ archived/v1-phase1-48/

Layer 4: 業界其他框架（次要參考）
  └─ MAF / OpenAI SDK / LangGraph / CrewAI
```

---

## Layer 1：業界標準（最權威）

### 主要文件
- `01-eleven-categories-spec.md` — 11 範疇規格（V2 開發的權威依據）
- `00-v2-vision.md` — V2 願景

### 使用時機
- 設計新 API 前
- 範疇實作前的 spec review
- PR review 時的標準依據

### 注意
**11 範疇文字描述來自業界研究**，是「是什麼」的權威定義。**具體實作機制可參考 Layer 2-4**。

---

## Layer 2：Claude Code 源碼研究（最完整實作參考）

### 位置
```
docs/07-analysis/claude-code-study/
├── 00-final-summary.md             ← 30 wave 研究總結
├── 00-index.md                     ← 全文索引
├── 01-architecture/                ← 架構分析
│   ├── system-overview.md
│   ├── layer-model.md
│   └── data-flow.md
├── 02-core-systems/                ← 核心系統
│   ├── tool-system.md              ← 範疇 2 參考
│   ├── permission-system.md        ← 範疇 9 參考
│   └── ...
├── 03-ai-engine/                   ← AI 引擎
│   ├── query-engine.md             ← 範疇 1 參考（最重要）
│   ├── context-management.md       ← 範疇 4 參考
│   └── ...
├── 06-agent-system/                ← Agent 系統
│   ├── agent-delegation.md         ← 範疇 11 參考
│   ├── task-framework.md           ← 範疇 11 參考
│   └── ...
└── _verification-log/              ← 30 wave 詳細驗證
    └── (75+ wave 驗證紀錄)
```

### 範疇 ↔ CC 文件對應表

| 範疇 | 主要 CC 參考文件 |
|------|-----------------|
| 1 Orchestrator Loop | `03-ai-engine/query-engine.md`, `_verification-log/wave4-path1-input-to-response.md`, `_verification-log/wave4-path2-tool-invocation.md` |
| 2 Tool Layer | `02-core-systems/tool-system.md`, `_verification-log/wave2-tool-verify-*.md` |
| 3 Memory | `05-services/memory-system.md` |
| 4 Context Management | `03-ai-engine/context-management.md`, `_verification-log/wave4-path4-autocompact-flow.md` |
| 5 Prompt Construction | `03-ai-engine/query-engine.md`（Section 2 Message Preparation） |
| 6 Output Parsing | `03-ai-engine/query-engine.md`（Section 4-5） |
| 7 State Management | `02-core-systems/state-management.md` |
| 8 Error Handling | `10-patterns/error-handling.md`, `03-ai-engine/query-engine.md`（Retry Logic） |
| 9 Guardrails | `02-core-systems/permission-system.md`, `02-core-systems/hook-system.md` |
| 10 Verification | `_verification-log/wave4-path*.md` |
| 11 Subagent | `06-agent-system/agent-delegation.md`, `06-agent-system/task-framework.md`, `_verification-log/wave4-path5-agent-spawning.md` |

### 使用時機
- 範疇實作前查 CC 怎麼做
- 卡關時看 CC 解法
- 設計細節抉擇時參考

### ⚠️ 關鍵注意事項

**CC 是本地工具，V2 是企業 server-side 平台。參考 CC 架構，但實作必須完全 server-side 化。**

> **權威 CC→V2 轉化映射見 `10-server-side-philosophy.md` 原則 3**

#### 簡要轉化原則

| CC 機制 | V2 對應 |
|---------|--------|
| 「user files」 | 「企業資料 API」（D365 / SAP / KB） |
| Bash 任意 shell | 沙盒化 + 白名單命令 |
| 本地 memory（CLAUDE.md / ~/.claude/memory）| Multi-tenant DB + Vector DB（5 層）|
| Git commits as checkpoint | DB state_snapshots |
| Forked agent extraction | Background worker + queue |
| Single user trust | Multi-tenant + RBAC + audit |
| Streaming tool executor | Async + worker process |

#### 不要照搬的部分

❌ **絕對不要**：
- 複製 CC 的 TypeScript 代碼到 Python
- 假設「用戶在前面」（CC 是同步互動）
- 用 git 當資料層
- 把任何 LLM SDK 用法照搬（V2 是 LLM 中性的）

✅ **應該做的**：
- 參考 CC 的**架構模式**（loop 結構、3 層 memory、tool 註冊機制）
- 參考 CC 的**設計哲學**（記憶為線索、native tool calling、Gather-Act-Verify）
- 參考 CC 的**問題解法**（autoCompact、observation masking、subagent 摘要）

**核心原則**：**參考其架構模式，不是複製其實作**。

---

## Layer 3：V1 寶貴邏輯（避免重複造輪子）

### 位置
```
archived/v1-phase1-48/
├── backend/
└── README.md
```

### V1 → V2 邏輯遷移清單（從 03-rebirth-strategy.md 重述）

| V1 模組 | 邏輯價值 | 遷移到 V2 |
|---------|---------|----------|
| `risk_assessor/assessor.py` (639 LOC) | 風險評估規則設計 | `platform/governance/risk/policies/`（提取規則 YAML） |
| `hitl/controller.py` (788 LOC) | Teams 通知整合 | `platform/governance/hitl/teams_notifier.py`（重寫） |
| `audit/logger.py` | Audit log 格式 | `platform/governance/audit/`（借鑒欄位） |
| `intent_router/llm_classifier/prompts.py` | LLM 分類 prompts | `agent_harness/05_prompt_builder/templates/` |
| `dispatch/executors/team_agent_adapter.py` | MAF GroupChat 整合 | `adapters/maf/group_chat.py`（直接遷移） |
| `mcp/servers/*` | 企業 MCP 整合 | `adapters/mcp/`（直接遷移） |
| `agent_framework/builders/` | MAF Builder 包裝 | `adapters/maf/`（重新整理） |
| `core/security/*` | 加密 / 認證工具 | `core/crypto/` + `platform/identity/`（提取） |
| `core/sandbox/*` | Sandbox 抽象 | `agent_harness/02_tools/sandbox.py`（提取） |

### 使用時機
**遇到「V1 是怎麼做的？」**：
```bash
git checkout v1-final-phase48 -- archived/v1-phase1-48/backend/src/integrations/orchestration/risk_assessor/

# 看完後 checkout 回 V2
git checkout HEAD
```

或直接瀏覽（不切換）：
```bash
# Read-only 瀏覽
ls archived/v1-phase1-48/backend/src/integrations/orchestration/
```

### 注意事項
**V1 邏輯有 27% 對齊度的問題**，**參考其想法，不是複製其實作**：
- ✅ 參考：規則設計、欄位設計、整合模式
- ❌ 避免：直接 copy code、Pipeline 思維、散落結構

---

## Layer 4：業界其他框架（次要參考）

### MAF (Microsoft Agent Framework)
**位置**：`reference/agent-framework/`

**參考時機**：
- 多 agent workflow 模式（Concurrent / Handoff / GroupChat / Magentic）
- Provider 整合接口設計

**注意**：MAF 整合代碼在 V2 是 `adapters/maf/`，不是核心。

### OpenAI Agents SDK
**參考來源**：官方文件（每次需要時查）

**參考時機**：
- 範疇 9 Guardrails 的 input/output/tool 三層設計
- 範疇 11 agents-as-tools 模式
- Runner 抽象

### LangGraph
**參考時機**：
- 範疇 7 typed state + reducers 設計
- 範疇 8 4 類錯誤分類
- Time-travel checkpointing

### CrewAI
**參考時機**：
- Role-based multi-agent 設計
- Task / Crew 抽象

### Anthropic Claude Agent SDK
**位置**：可在 `reference/` 加入（如有）

**參考時機**：
- `query()` 函式介面設計（範疇 1）
- Hook / Permission / Tool 設計（範疇 2, 9）

---

## 參考查詢工作流

當在 V2 開發遇到設計疑問時：

```
1. 是否屬於 11 範疇之一？
   ↓ 是
2. 查 Layer 1（11 範疇規格）— 業界定義是什麼？
   ↓ 確認需求
3. 查 Layer 2（CC 研究）— CC 怎麼做？
   ↓ 取得實作模式
4. 查 Layer 3（V1）— 我們之前怎麼做？
   ↓ 借鑒邏輯
5. 查 Layer 4（其他框架）— 業界還有什麼方案？
   ↓ 取得多元視角
6. 設計 V2 方案：
   - 採用 CC 的實作模式（為主）
   - 借鑒 V1 的邏輯（為輔）
   - 適配企業 server-side 場景
   - 落地到 11 範疇對應目錄
```

---

## 每 Sprint 結束的「參考使用 retro」

```markdown
Sprint XXX 參考使用紀錄
- 引用 CC 文件：______
- 引用 V1 模組：______
- 引用其他框架：______
- 學到的設計模式：______
- 避開的陷阱：______
```

幫助累積項目自身的知識資產。

---

## 反例：什麼不該做

### ❌ 不該做：直接照搬 CC 代碼到 V2
CC 是 TypeScript + 本地工具 + 單用戶。直接搬到 V2 = 文化衝突 + 範疇不對齊。

### ❌ 不該做：完全不看 V1 從零想
V1 有 5 年累積的設計知識，無視 = 重複造輪子 + 重蹈覆轍。

### ❌ 不該做：盲目追隨單一框架
LangGraph / CrewAI / MAF 各有強項，盲信任一個 = 失去項目特色（**企業 governance + agent 智能混合**）。

---

## 下一步

- `06-phase-roadmap.md`：詳細 Sprint 規劃
- `07-tech-stack-decisions.md`：關鍵技術選型
- `08-glossary.md`：術語表
