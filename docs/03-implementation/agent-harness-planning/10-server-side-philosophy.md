# V2 Server-Side 哲學與 LLM Provider 中性原則

**建立日期**：2026-04-23
**版本**：V2.0
**重要性**：⭐⭐⭐ **本文件定義 V2 開發的最高指導原則**

---

## 為什麼建立此文件

V2 規劃過程中，發現有 **3 個容易被誤解** 的核心原則：

1. ❌ 誤解：「V2 是 Claude SDK 應用」
   ✅ 真實：**V2 是 LLM Provider 中性的企業 agent 平台**

2. ❌ 誤解：「V2 是 CC 移植」
   ✅ 真實：**V2 是參考 CC 架構，但完全 server-side 重新設計**

3. ❌ 誤解：「V2 是本地工具升級版」
   ✅ 真實：**V2 是企業 server-side 平台，工具是企業 API/服務**

本文件**權威定義**這 3 個原則，所有後續開發必須遵守。

---

## 原則 1：Server-Side First（伺服器端優先）

### 定義

V2 是**部署在企業伺服器上的後端服務**，前端是**遠端瀏覽器**。

### 與本地 Agent 的根本差異

| 維度 | CC（本地）| V2（企業 server）|
|------|----------|----------------|
| **執行位置** | 用戶 laptop | 企業 server / 雲 |
| **用戶位置** | 終端使用者本人 | 遠端 web browser |
| **檔案系統存取** | 完整 host fs | **零存取**（除非透過 API）|
| **Shell 執行** | 完整 Bash | **沙盒化 / 僅特定企業命令** |
| **多用戶** | 單用戶 | **multi-tenant + multi-user** |
| **生命週期** | 終端 session | **長期運行的 server** |
| **狀態** | local files / git | **DB / object store** |
| **安全模型** | trust user | **zero-trust + RBAC + audit** |

### 關鍵後果

#### 1. **「Tool」的含義完全不同**

CC 的 tool：
- Read / Write / Edit user files
- Bash 任意 shell
- Grep / Glob 本地檔案
- WebFetch（user 視角）

V2 的 tool：
- D365 / SAP / ServiceNow / SharePoint API 查詢
- 企業 SQL Database 查詢（受 RBAC 限制）
- 沙盒化的 Python / Shell（不能存取 host fs）
- 企業內部搜索（KB / Confluence）
- 業務工具（patrol / correlation / rootcause）

**V2 中沒有「Read user file」這種工具** — 因為 server 上沒有「user file」可讀。

#### 2. **「Memory」是 multi-tenant 持久化**

CC 的 memory：
- `~/.claude/memory/`（user 本地檔案）
- `CLAUDE.md`（project 本地檔案）

V2 的 memory：
- DB tables（per tenant 隔離）
- Vector DB namespace（per tenant）
- 5 層架構（system / tenant / role / user / session）

#### 3. **「State」是 DB snapshot 不是 git commit**

CC：git commits + progress files
V2：DB state_snapshots + checkpoint API

#### 4. **HITL 是核心，不是邊角**

CC：偶爾 confirm 危險操作
V2：**幾乎每個寫操作都可能觸發 HITL**（企業合規要求）

### V2 設計約束

- ❌ **不要設計需要存取 host fs 的工具**
- ❌ **不要假設「user 在前面」**（async via SSE / browser）
- ❌ **不要把 git 當 checkpoint**
- ✅ **所有工具透過 API 而非直接系統呼叫**
- ✅ **所有狀態進 DB**
- ✅ **所有資料 tenant-scoped**

---

## 原則 2：LLM Provider Neutrality（LLM 供應商中性）

### 定義

**Agent harness 核心邏輯不依賴任何特定 LLM 供應商或 SDK**。

支援的 LLM 透過 **Adapter 層** 統一介面：

```
┌─────────────────────────────────────────┐
│      Agent Harness（11 範疇）           │
│   只依賴 ChatClient ABC                 │
└──────────────┬──────────────────────────┘
               ↓ 介面: ChatClient ABC
┌──────────────────────────────────────────┐
│         Adapter 層                        │
├──────────────────────────────────────────┤
│ AzureOpenAIAdapter  (主要 - 公司現況)    │
│ AnthropicAdapter    (公司開放後可加)      │
│ OpenAIAdapter       (備援)                │
│ FoundryAdapter      (Azure AI Foundry)    │
└──────────────────────────────────────────┘
```

### 強制規則

#### Rule 1：**Agent Harness 禁止 import 任何 LLM SDK**

```python
# ❌ 在 agent_harness/ 任何檔案下禁止：
from openai import AzureOpenAI
from anthropic import Anthropic
import anthropic
import openai

# ✅ 唯一允許方式：
from src.adapters._base.chat_client import ChatClient
```

V2 lint rule 強制檢查：`agent_harness/**/*.py` 中**任何**對 LLM SDK 的直接 import 都會 fail CI。

#### Rule 2：**ChatClient ABC 是唯一介面**

> **2026-04-28 review 修訂**：原 ABC 缺 4 個關鍵方法（`count_tokens` / `get_pricing` / `supports_feature` / 完整 `ModelInfo`）— 沒有這些，per-tenant cost tracking、capability detection、cache key 設計都做不到。本次補完。

```python
# adapters/_base/chat_client.py
from abc import ABC, abstractmethod
from typing import AsyncIterator, Literal

class ChatClient(ABC):
    """所有 LLM 供應商的統一介面。

    Agent Harness 只認識這個 ABC。
    Owner: 本檔（10-server-side-philosophy.md）；single-source 在 17.md §2.1。
    """

    # ── 核心呼叫 ─────────────────────────────────────
    @abstractmethod
    async def chat(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec],
        tool_choice: ToolChoice = "auto",
        max_tokens: int | None = None,
        temperature: float = 1.0,
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        trace_context: TraceContext | None = None,
        extra_options: dict | None = None,
    ) -> ChatResponse: ...

    @abstractmethod
    async def stream(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec],
        # 同 chat() 其他參數
        **kwargs,
    ) -> AsyncIterator[StreamEvent]: ...

    # ── Token 計算（範疇 4 caching / context mgmt 必需）──
    @abstractmethod
    async def count_tokens(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> int:
        """per-provider tokenizer。tiktoken / claude-tokenizer / o200k_base。"""
        ...

    # ── 計費資訊（per-tenant cost tracking 必需）──
    @abstractmethod
    def get_pricing(self) -> PricingInfo:
        """回報當前模型的單價（input/output/cached token USD per 1M）。"""
        ...

    # ── Capability detection（multi-provider routing 必需）──
    @abstractmethod
    def supports_feature(
        self,
        feature: Literal[
            "thinking",         # extended thinking
            "caching",          # prompt caching
            "vision",           # image input
            "audio",            # audio input/output
            "computer_use",     # computer use（Anthropic）
            "structured_output",
            "parallel_tool_calls",
        ],
    ) -> bool: ...

    # ── 模型資訊 ─────────────────────────────────────
    @abstractmethod
    def model_info(self) -> ModelInfo:
        """完整 model metadata；single-source 在 17.md §1.1。"""
        ...


@dataclass(frozen=True)
class ModelInfo:
    """ChatClient.model_info() 回傳；用於 routing / cache_key / metric attribute。"""
    model_name: str            # "gpt-5.4" / "claude-3.7-sonnet" / "gpt-4o"
    model_family: str          # "gpt" / "claude" / "azure-openai"
    provider: str              # "azure_openai" / "anthropic" / "openai" / "foundry"
    context_window: int        # max input tokens
    max_output_tokens: int
    knowledge_cutoff: datetime | None


@dataclass(frozen=True)
class PricingInfo:
    """ChatClient.get_pricing() 回傳。USD per 1M tokens。"""
    input_per_million: float
    output_per_million: float
    cached_input_per_million: float | None = None  # 若支援 caching
    currency: Literal["USD"] = "USD"
```

#### Rule 3：**ToolSpec 是中性格式**

工具定義使用 V2 自訂格式，**不直接用** OpenAI 或 Anthropic 的 tool schema：

```python
# V2 中性 ToolSpec
@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict  # JSON Schema (中性)
    # ... 其他欄位

# Adapter 負責轉換
class AzureOpenAIAdapter(ChatClient):
    def _convert_tools(self, specs: list[ToolSpec]) -> list[dict]:
        # ToolSpec → OpenAI function calling format
        ...

class AnthropicAdapter(ChatClient):
    def _convert_tools(self, specs: list[ToolSpec]) -> list[dict]:
        # ToolSpec → Anthropic tools format
        ...
```

#### Rule 4：**Message 格式中性**

```python
# V2 中性 Message
@dataclass
class Message:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str | list[ContentBlock]
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    
# Adapter 轉成各家格式
```

#### Rule 5：**Multi-Provider Routing**（新增）

> **2026-04-28 review 新增**：「換 provider」是初階場景；**同時跑多 provider 並按 request routing**才是 multi-provider 真正價值（cost-sensitive 用 GPT-4o-mini、quality 用 Claude）。

```python
# adapters/_base/router.py
class ProviderRouter(ABC):
    """根據 request 屬性選 provider。"""

    @abstractmethod
    async def select(
        self,
        *,
        tenant_id: UUID,
        intent: Literal["cheap","balanced","quality","compliance_strict"],
        required_features: set[str] | None = None,   # e.g. {"thinking","caching"}
    ) -> ChatClient:
        """選擇 ChatClient 實例；若 required_features 不滿足，graceful degrade。"""

    @abstractmethod
    def get_fallback_chain(self, primary: str) -> list[str]:
        """主 provider 失敗時的 fallback 鏈（配合 CircuitBreaker，見範疇 8）。"""
```

#### Rule 6：**StopReason / Stream Event 中性化**

per-provider stop reason 字串不同（Anthropic: `end_turn`/`tool_use`/`max_tokens`；OpenAI: `stop`/`tool_calls`/`length`），必須中性化：

```python
class StopReason(Enum):
    """Owner: 本檔；single-source 在 17.md §1.1。所有 ChatResponse 必用此 enum。"""
    END_TURN = "end_turn"
    TOOL_USE = "tool_use"
    MAX_TOKENS = "max_tokens"
    STOP_SEQUENCE = "stop_sequence"
    SAFETY_REFUSAL = "safety_refusal"
    PROVIDER_ERROR = "provider_error"


# Adapter 必須實作 mapping
class AzureOpenAIAdapter(ChatClient):
    def _map_stop_reason(self, openai_reason: str) -> StopReason:
        return {
            "stop": StopReason.END_TURN,
            "tool_calls": StopReason.TOOL_USE,
            "length": StopReason.MAX_TOKENS,
            "content_filter": StopReason.SAFETY_REFUSAL,
        }.get(openai_reason, StopReason.PROVIDER_ERROR)
```

### 驗收標準

> **2026-04-28 review 修訂**：原「30 分鐘換 provider」是樂觀目標；真實切換涉及 prompt re-tune、stop reason mapping、streaming 格式、token counting、caching 政策差異。改保守 SLA。

#### Provider 切換驗收（修訂）

- [ ] **「< 2 週切換 provider」**：把主流量從 Azure OpenAI 切到 Anthropic，**只改 config 不改 agent_harness 代碼**，2 週內完成
- [ ] **「< 1 月品質對齊」**：切換後 1 個月內 verifier pass rate / user satisfaction 與原 provider ±5%
- [ ] **同一 agent loop 跑兩家測試**：跑 provider A 拿結果 X、切 B 拿結果 Y，X 與 Y 在功能上等價（內容可不同）

#### ChatClient ABC 完整性驗收

- [ ] `count_tokens` / `get_pricing` / `supports_feature` / `model_info` 4 方法在所有 adapter 實作
- [ ] `ModelInfo` / `PricingInfo` / `StopReason` 中性化 enum 完整
- [ ] Tool result `result_content_types` 中性化（Anthropic 支援 image，OpenAI string-only）

#### Multi-Provider Routing 驗收（新增）

- [ ] `ProviderRouter` ABC 實作
- [ ] 4 種 intent（cheap / balanced / quality / compliance_strict）routing 測試通過
- [ ] `required_features` 不滿足時 graceful degrade（fallback to provider with 不同 capability）
- [ ] CircuitBreaker 整合（範疇 8）：primary provider 失敗自動切 fallback chain

#### CI 強制驗收

- [ ] `grep -r "from openai\|from anthropic\|import openai\|import anthropic" backend/src/agent_harness/` 結果為 0
- [ ] `grep -r "from openai\|from anthropic" backend/src/business_domain/` 結果為 0
- [ ] Adapter 之外的所有目錄禁止 LLM SDK 直接 import（Phase 49.4 lint rule）

### 為什麼這個原則重要

1. **公司現實**：目前只能用 Azure OpenAI，但**未來可能開放 Claude**
2. **議價能力**：不被任一供應商鎖定
3. **避險**：某供應商出問題（漲價 / 停服 / 政策變動）能切換
4. **對比測試**：可同時跑兩家比質量
5. **混合路由**（新增）：cheap / quality 分流，per-request 動態選 provider，cost-quality 雙贏

---

## 原則 3：CC 架構參考 + Server-Side 轉化（不照搬）

### 定義

V2 **架構模式參考 Claude Code**（業界最完整的 agent harness 實作），但**所有實作必須轉化為 server-side 版本**。

### 為什麼參考 CC

CC 是業界目前**最完整的 agent harness 實作**：
- 真正的 TAO loop（範疇 1）
- 完整的 tool 系統（範疇 2）
- 多層 memory（範疇 3）
- Compaction + JIT retrieval（範疇 4）
- 系統性 PromptBuilder（範疇 5）
- Native tool calls（範疇 6）
- Git checkpoint（範疇 7）
- 4 類錯誤處理（範疇 8）
- 三層 guardrails + tripwire（範疇 9）
- 自我驗證迴圈（範疇 10）
- Fork/Teammate/Worktree subagent（範疇 11）

**參考 CC 是合理的**，但**直接搬本地實作到企業 server 會死**。

### CC → V2 轉化映射表

| CC 機制 | V2 server-side 對應 | 轉化說明 |
|---------|--------------------|---------|
| **Bash tool** | Sandbox container Python/SQL/Shell | 沙盒化 + 限制企業命令白名單 |
| **Read tool**（讀本地檔案） | API Tools（D365 / SAP / KB / SharePoint） | 「檔案」變成「企業資料源」 |
| **Write tool**（寫本地檔案） | API Tools（建工單 / 更新 record） | 「寫」變成「呼叫企業 mutation API」 |
| **Edit tool** | 不對應 | V2 不編輯本地檔案；改為「更新企業記錄」 |
| **Grep / Glob**（本地搜索） | KB Search / Vector Search | 「搜檔案」變成「搜知識庫」 |
| **WebFetch / WebSearch** | 保留概念，加企業代理 / 白名單 | 同概念，加治理 |
| **CLAUDE.md（global）** | DB `memory_system` 表 | 全局規則改 DB |
| **CLAUDE.md（project）** | DB `memory_tenant` 表 | per-tenant 隔離 |
| **~/.claude/memory/** | DB `memory_user` 表 + Vector DB | per-user 持久化 |
| **Memory extraction（forked agent）** | Background worker job | server 必須 async + queue |
| **Git commits as checkpoint** | DB `state_snapshots` 表 | DB-based |
| **Progress file scratchpad** | TodoWrite tool + DB | 工具化 |
| **`canUseTool` permission** | GuardrailEngine.check_tool_call() | 加 RBAC + tenant policy |
| **`autoCompactIfNeeded`** | ContextCompactor | 同概念，配合 server context |
| **Streaming tool executor** | ToolExecutor + asyncio | server async |
| **Fork subagent** | DB-backed subagent_runs + worker | 跨 process |
| **Teammate（terminal pane）** | DB-backed subagent_messages mailbox | 跨 process 訊息 |
| **Worktree（git）** | 不對應 | server 不用 git worktree |
| **Permission（trust establishment at project load）** | Session 開始 = tenant policy load | 同概念，per session |
| **三階段審批（trust → check → confirm）** | RBAC pre-check → tool guardrail → HITL approval | 同模式，分層實作 |
| **Hooks system**（PreToolUse / PostToolUse / SessionStart / SubagentStop 等 8+ 種，CC 擴展核心） | **Lifecycle Hooks** 系統（Phase 53.3） | tenant 可註冊 pre/post tool / session / subagent hook，必經 guardrail engine |
| **Slash commands**（/help, /loop, /sc:* 使用者自訂指令） | **Workflow Triggers**（Phase 55.1） | 企業 admin 配置「快速指令」對應 agent workflow（如 `/incident.report` 觸發 incident_create） |
| **Skills system**（自治技能 plugin） | **Capability Packs**（Phase 54.x） | per-role / per-tenant 能力包，bundle prompt + tools + memory hints；hot-reloadable |
| **Output styles**（控 verbosity / format） | **Tone Profiles**（Phase 52.2） | per-tenant / per-role 輸出風格配置（formal / casual / technical），由 PromptBuilder 注入 |
| **Plan mode / Read-only mode**（行為模式切換） | **Dry-Run Mode + Sandbox Preview**（Phase 53.x） | dry_run flag 強制所有 destructive tool 走「預覽輸出」而不執行；sandbox preview 允許 reviewer 先看效果 |

### 轉化原則

#### 原則 A：**「概念複製，實作重寫」**

✅ 複製：架構模式、流程順序、解決問題的思路
❌ 不複製：具體 API、資料結構、本地假設

#### 原則 B：**「向上抽象，向下適配」**

CC 的具體機制 → 抽象成 ABC → server 端重新實作

#### 原則 C：**「敵意環境 first」**

CC 是「friendly host」（用戶自己 laptop）
V2 是「hostile multi-tenant」（多租戶 + 跨用戶 + 合規）

每個 CC 設計都要問：「這個在 multi-tenant 場景會出什麼問題？」

### 實際範例：範疇 1 Loop 的轉化

#### CC 原版（簡化）
```typescript
// CC: src/query.ts
while (true) {
  const response = await anthropic.messages.create({...})
  if (response.stop_reason === "end_turn") return response
  for (const tc of response.tool_calls) {
    const result = await executeToolWithPermission(tc)
    messages.push(toolResultMessage(result))
  }
}
```

#### V2 轉化版
```python
# V2: agent_harness/01_orchestrator_loop/loop.py
class AgentLoop:
    def __init__(
        self,
        chat_client: ChatClient,    # ← 不綁 Anthropic
        tool_executor: ToolExecutor,  # ← 沙盒化執行
        guardrail: GuardrailEngine,   # ← 三層 guardrail
        compactor: ContextCompactor,  # ← 範疇 4
        verifier: Verifier,            # ← 範疇 10
        state_store: StateStore,      # ← DB-backed
    ): ...
    
    async def run(self, state: LoopState) -> LoopResult:
        await self.guardrail.check_input(state.user_input)  # 範疇 9
        
        while True:
            await self.compactor.compact_if_needed(state)    # 範疇 4
            await state_store.checkpoint(state)              # 範疇 7
            
            response = await self.chat_client.chat_with_tools(...)
            
            if not response.tool_calls:
                verification = await self.verifier.verify(response, state)  # 範疇 10
                if not verification.passed and state.correction_count < 2:
                    state.messages.append(verification_feedback_message)
                    continue
                return LoopResult(response, state)
            
            for tc in response.tool_calls:
                guardrail_result = await self.guardrail.check_tool_call(tc, state)  # 範疇 9
                if guardrail_result.requires_hitl:
                    return LoopResult.paused_for_hitl(...)
                
                result = await self.tool_executor.execute(tc, state.context)
                state.messages.append(self.format_tool_result(result))
            
            if state.should_terminate():  # max_turns / budget / tripwire
                return LoopResult.terminated(reason=...)
```

**對比看出**：
- CC 是 30 行
- V2 是 30+ 行 **但每行做的事不一樣**
- 多了 multi-tenant、guardrail、compactor、verifier、state_store
- LLM 透過 ChatClient ABC 而非直接 anthropic SDK
- 工具執行透過 ToolExecutor 而非直接 shell

---

## 原則應用矩陣

每個範疇實作時必須過 3 個 check：

| 範疇 | Server-Side check | LLM-Neutral check | CC 轉化 check |
|------|------------------|-----------------|------------|
| 1. Loop | ✅ async + worker | ✅ ChatClient ABC | ✅ TAO 概念，server 實作 |
| 2. Tools | ✅ 企業 API + 沙盒 | ✅ 中性 ToolSpec | ✅ CC 6 大類 → 企業 8 大類 |
| 3. Memory | ✅ DB + tenant 隔離 | N/A | ✅ 5 層（CC 3 層 + tenant + role） |
| 4. Context Mgmt | ✅ DB-backed | ✅ token 計算抽象 | ✅ 同概念 |
| 5. Prompt | ✅ 中性組裝 | ✅ provider-agnostic 模板 | ✅ 階層注入 |
| 6. Output | N/A | ✅ 中性 ChatResponse | ✅ native tool_calls |
| 7. State | ✅ DB snapshot | N/A | ✅ git → DB |
| 8. Error | ✅ 4 類 + audit | ✅ provider 錯誤抽象 | ✅ 同概念 |
| 9. Guardrails | ✅ RBAC + audit | N/A | ✅ 3 層 + tripwire |
| 10. Verification | ✅ 跨 LLM | ✅ judge 用 ChatClient | ✅ self-correction |
| 11. Subagent | ✅ DB + worker | ✅ 子 agent 也用 ChatClient | ✅ Fork/Teammate → DB |

---

## 違反這 3 原則的後果

### 後果 1：違反 Server-Side（如做了存取本地 fs 的 tool）
- 部署時崩潰（server 沒有用戶的 fs）
- 安全災難（跨 tenant 洩漏）
- **必須立即重做**

### 後果 2：違反 LLM-Neutral（如直接 import anthropic）
- 無法切換供應商
- CI 強制 fail
- **PR 必須 revert**

### 後果 3：違反 CC 轉化（如照搬 CC 本地實作）
- multi-tenant 場景出現安全 / 性能問題
- 未來規模化困難
- **架構 review 拒絕通過**

---

## 文件交叉引用

本原則影響以下規劃文件：

- `00-v2-vision.md` — 核心理念 4 對應原則 2
- `01-eleven-categories-spec.md` — 每個範疇都應對齊 3 原則（Section M「應用矩陣」是依據）
- `02-architecture-design.md` — 約束 3「Adapter 層強制」對應原則 2
- `04-anti-patterns.md` — AP-2「Side-track」與 AP-6「Hybrid Bridge Debt」防止違反原則 2
- `05-reference-strategy.md` — 「CC 是參考不是模板」對應原則 3
- `07-tech-stack-decisions.md` — Adapter pattern 落實原則 2

---

## 結語

本文件是 V2 的**最高指導原則**。

任何規劃修訂、Sprint plan、PR 必須過 3 原則 check：
- [ ] 是否違反 Server-Side 假設？
- [ ] 是否綁定特定 LLM 供應商？
- [ ] 是否 CC 本地照搬未轉化？

3 個都過，才能往下走。
