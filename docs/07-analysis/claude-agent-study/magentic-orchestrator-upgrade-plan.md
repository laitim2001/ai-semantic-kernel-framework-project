# IPA Platform — Magentic Orchestrator Agent 升級規劃

> **文件版本**: 2.0（已校正）
> **原始日期**: 2026-03-22
> **校正日期**: 2026-03-22
> **定位**: Phase 44 架構升級規劃
> **前置文件**: `MAF-Claude-Hybrid-Architecture-V8.md`, `MAF-Features-Architecture-Mapping-V8.md`
> **狀態**: 規劃中（待 Phase 44 排期）
> **範疇**: L5 Hybrid Layer + L6 MAF Builder + L7 Claude SDK 升級
> **校正說明**: V2.0 基於 4 個平行研究 Agent 交叉驗證，修正了 V1.0 中 7 個嚴重錯誤和 7 個中等偏差

---

## 1. 背景與問題陳述

### 1.1 當前架構的瓶頸

IPA Platform 的 HybridOrchestratorV2 + OrchestratorMediator（Sprint 132 重構）本質上是一個**確定性的流程路由引擎**，而非自主推理的協調者。

當前的處理流程：

```
用戶輸入
  → [L4] BusinessIntentRouter（三層瀑布式分類：PatternMatcher → SemanticRouter → LLMClassifier）
  → [L4] CompletenessChecker（資訊是否足夠？不足 → GuidedDialogEngine 追問）
  → [L4] RiskAssessor（7 維度條件性評分 → LOW/MEDIUM/HIGH/CRITICAL）
  → [L4] HITLController（HIGH/CRITICAL 需審批）
  → [L5] FrameworkSelector（按規則選擇框架 → MAF / Claude / Hybrid）
  → [L6/L7] 執行層（MAF Builder 或 Claude SDK）
```

**核心限制**：

| 維度 | 當前狀態 | 問題 |
|------|---------|------|
| 決策機制 | 規則 + 靜態映射表（INCIDENT → MAF） | 不能根據具體情況動態判斷 |
| 任務分解 | ❌ 不能 — 只選預定義的 workflow type | 無法將複雜任務動態分解為子任務 |
| 進度追蹤 | ❌ 沒有 — 發射後不管 | 無 Task/Progress Ledger |
| 重規劃 | ❌ 沒有 — 失敗就 fallback | 不能自動判斷卡住原因並重新規劃 |
| 代理間通訊 | ❌ 無 — 單向分派到執行層 | Workers 之間不能互相交流 |
| Claude 角色 | 末端工具（被調用做推理） | 不參與編排決策 |
| Manager 模型 | `StandardMagenticManager()` 無參數預設 | 無法切換到更強的推理模型 |

### 1.2 目標狀態

將 MagenticBuilderAdapter 的 Manager Agent 從「`StandardMagenticManager()` 預設配置」升級為「Claude Opus 4.6 自主推理協調者」，同時支持在 Anthropic（Opus/Sonnet/Haiku）和 Azure OpenAI（GPT-5.2/4o/o3-mini）之間自由切換。

升級後的處理流程：

```
用戶輸入
  → [L4] BusinessIntentRouter → RiskAssessor → HITL    ← 保留不變
  → [L5] FrameworkSelector + ManagerModelSelector       ← 擴展
  → [L6] MagenticBuilder
      └── Manager Agent = Claude Opus 4.6 (Extended Thinking)
            ├── 自主分析：「這個問題需要什麼？」
            ├── 動態分解：「分成 N 個子任務」（Task Ledger）
            ├── 智能分派：「任務 1 給 Research Agent，任務 2 給 D365 Agent」
            ├── 持續監控：「任務 2 卡住了」（Progress Ledger）
            ├── 自動重規劃：「改用 MCP D365 Server 直接查詢」
            └── 綜合結果
```

### 1.3 關鍵設計原則

1. **Orchestrator 只需要「想」→ 用 `anthropic` SDK（輕量 API 調用）**
2. **Worker 需要「做」→ 用 `claude-agent-sdk` 或現有 L7 自建系統**
3. **最小改動** — 保留所有現有架構（L4 路由、L5 Mediator、L3 AG-UI、L8 MCP）
4. **YAML 零代碼配置** — 運維人員可直接切換模型
5. **自動 Fallback** — Claude 不可用時自動降級到 Azure OpenAI

---

## 2. SDK 選型分析

### 2.1 三個 SDK 的區別

IPA Platform 涉及三個不同的 SDK，各自有不同的定位和適用場景：

| SDK | 套件名稱 | 定位 | 運作方式 | 適用場景 |
|-----|---------|------|---------|---------|
| **anthropic SDK** | `pip install anthropic` | Claude API 客戶端 | Python 直接呼叫 REST API | 純推理（聊天、思考、分析） |
| **Claude Agent SDK** | `pip install claude-agent-sdk` | Claude Code as a library | 啟動 Claude Code CLI 子進程 | 完整 agentic（讀檔/跑命令/MCP） |
| **agent-framework-anthropic** | `pip install agent-framework-anthropic --pre` | MAF 的 Anthropic 附加套件 | 包裝 anthropic SDK 為 MAF 介面 | MAF 原生 Claude 支援 |

### 2.2 各 SDK 在本項目中的現狀

| SDK | 已安裝？ | 使用位置 | 版本 |
|-----|---------|---------|------|
| `anthropic` | ✅ 已安裝 | L7 Claude SDK 層（`claude_sdk/client.py` 中 `AsyncAnthropic`） | `>=0.84.0` |
| `claude-agent-sdk` | ❌ 未安裝 | — | — |
| `agent-framework-anthropic` | ❌ 未安裝 | — | Beta `1.0.0b260219` |

### 2.3 MAF 的實際情況

> **重要發現**：MAF 核心套件 `agent-framework>=1.0.0rc4,<2.0.0`（範圍約束，實際安裝版本需以 `pip freeze` 確認）**沒有**原生 Anthropic 支援。

| Import 路徑 | 所在套件 | 狀態 |
|------------|---------|------|
| `from agent_framework.azure import AzureOpenAIResponsesClient` | `agent-framework` (核心) | ✅ 存在且使用中 |
| `from agent_framework.anthropic import AnthropicClient` | `agent-framework-anthropic` (附加) | ❌ 核心套件中不存在 |
| `from agent_framework_claude import ClaudeAgent` | `agent-framework-claude` (附加) | ❌ 核心套件中不存在 |

MAF 核心提供的關鍵抽象：
- `Agent` / `BaseAgent` — Agent 基類
- `BaseChatClient` — ChatClient 抽象基類 ← **這是擴展點**（`reference/` 中有定義，項目自身代碼尚未使用）
- `AzureOpenAIResponsesClient` — 唯一的官方 ChatClient 實作
- `MagenticBuilder` / `ConcurrentBuilder` / `GroupChatBuilder` — 編排器
- `StandardMagenticManager` — 預設 Manager 實作

### 2.4 選型決策

**Magentic Manager Agent → 自建 `AnthropicChatClient`（基於 `anthropic` SDK）**

理由：
- Manager 只需要「想」（推理 + Structured Output），不需要「做」（操作檔案/跑命令）
- `anthropic` SDK 已安裝（L7 已有 `>=0.84.0`），零新依賴
- `BaseChatClient` 是 MAF 設計上預期的擴展方式，不是 hack
- 避免依賴 Beta 狀態的 `agent-framework-anthropic`（與 RC4 核心兼容性未驗證）
- 純 API 調用，無子進程，無 Node.js 依賴

**Specialist Worker Agents → 短期保留 L7 自建系統，中期評估 `claude-agent-sdk`**

理由：
- L7 自建系統已有 ~15,400 LOC，經 148+ Sprints 驗證
- `claude-agent-sdk` 可以在 FastAPI 服務中運行（它就是為此設計的），但需要 Node.js 運行時
- Worker 需要完整 agentic 能力（Read/Write/Bash/MCP tools）
- 遷移到 `claude-agent-sdk` 可以減少 L7 的維護負擔，但非此 Phase 優先

### 2.5 SDK 角色分工全景圖

```
MagenticBuilder
├── Manager Agent                              ← anthropic SDK（自建 ChatClient）
│   └── AnthropicChatClient(BaseChatClient)
│       └── anthropic.AsyncAnthropic.messages.create()
│           • Extended Thinking ✅
│           • Structured Output ✅（Task/Progress Ledger）
│           • 純 API 調用，無子進程
│           • ~150 LOC 自建
│
├── Worker: 診斷 Agent                         ← L7 自建系統（短期）
│   └── ClaudeSDKClient + MCP Azure Server     ← claude-agent-sdk（中期評估）
│       • 讀日誌、查 Azure 資源
│       • 需要 agentic 能力
│
├── Worker: 修復 Agent                         ← L7 自建系統（短期）
│   └── ClaudeSDKClient + MCP Shell Server     ← claude-agent-sdk（中期評估）
│       • 執行修復腳本、寫配置
│       • 需要 Bash/Write 工具
│
└── Worker: 報告 Agent                         ← Azure OpenAI（L6 已有）
    └── AzureOpenAIResponsesClient("gpt-4o")
        • 生成文件/報表
        • 不需要 agentic 能力，成本最低
```

---

## 3. 核心設計：ManagerModelRegistry + ManagerModelSelector

### 3.1 架構概覽

```
┌─────────────────────────────────────────────────┐
│            config/manager_models.yaml            │ ← 運維人員可直接修改
│  ┌───────────────────┐  ┌─────────────────────┐ │
│  │ Anthropic Models  │  │ Azure OpenAI Models │ │
│  │ • claude-opus-4-6 │  │ • gpt-5.2           │ │
│  │ • claude-sonnet   │  │ • gpt-4o            │ │
│  │ • claude-haiku    │  │ • o3-mini           │ │
│  └───────────────────┘  └─────────────────────┘ │
│  ┌───────────────────────────────────────────┐   │
│  │ selection_strategies:                     │   │
│  │   max_reasoning → claude-opus-4-6        │   │
│  │   balanced → claude-sonnet-4-6           │   │
│  │   cost_efficient → gpt-4o               │   │
│  │   fast_cheap → claude-haiku-4-5         │   │
│  └───────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────┘
                       │ YAML 載入
                       ▼
┌──────────────────────────────────────────────────┐
│          ManagerModelRegistry（單例）              │
│  • _models: dict[str, ModelConfig]               │
│  • create_manager_agent(model_key) → Agent       │
│  • list_models() → 列出所有可用模型               │
│  • get_default_model() → 預設模型                 │
│  • get_fallback_model() → Fallback 模型           │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│         ManagerModelSelector（自動選擇器）          │
│  • select_model(risk_level, complexity,           │
│                  user_override) → model_key       │
│  • CRITICAL → claude-opus-4-6                    │
│  • HIGH → claude-sonnet-4-6                      │
│  • MEDIUM → gpt-4o                              │
│  • LOW → claude-haiku-4-5                        │
│  • user_override 最高優先                         │
│  • _is_model_available() → Fallback 檢查          │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│    MagenticBuilderAdapter（需重構 build()）        │
│  • manager_agent = registry.create_manager_agent │
│  • ⚠️ 現有 build() 未將 manager 配置傳給官方 API  │
│  • 需先修復 build() 正確轉發 manager 到            │
│    MagenticBuilder.with_standard_manager()        │
└──────────────────────────────────────────────────┘
```

### 3.2 YAML 配置設計

```yaml
# config/manager_models.yaml

manager_model_registry:
  # ── Anthropic Models ──
  claude-opus-4-6:
    provider: anthropic
    model_id: "claude-opus-4-6"
    display_name: "Claude Opus 4.6 (深度推理)"
    default_options:
      max_tokens: 20000
      thinking:
        type: enabled
        budget_tokens: 10000
    capabilities: [structured_output, extended_thinking, vision]
    cost_tier: premium
    recommended_for: [critical_incidents, erp_migration, architecture_review]

  claude-sonnet-4-6:
    provider: anthropic
    model_id: "claude-sonnet-4-6"
    display_name: "Claude Sonnet 4.6 (平衡)"
    default_options:
      max_tokens: 16000
      thinking:
        type: enabled
        budget_tokens: 5000
    capabilities: [structured_output, extended_thinking, vision]
    cost_tier: standard
    recommended_for: [security_analysis, deployment_review, change_management]

  claude-haiku-4-5:
    provider: anthropic
    model_id: "claude-haiku-4-5-20251001"
    display_name: "Claude Haiku 4.5 (快速)"
    default_options:
      max_tokens: 8000
    capabilities: [structured_output]
    cost_tier: economy
    recommended_for: [simple_queries, status_checks, quick_triage]

  # ── Azure OpenAI Models ──
  gpt-5.2:
    provider: azure_openai
    model_id: "gpt-5.2"
    display_name: "GPT-5.2 (最新推理)"
    endpoint: ${AZURE_OPENAI_ENDPOINT}
    default_options:
      max_tokens: 16000
      reasoning_effort: high
    capabilities: [structured_output, reasoning, vision]
    cost_tier: premium
    recommended_for: [complex_analysis, multi_step_planning]

  gpt-4o:
    provider: azure_openai
    model_id: "gpt-4o"
    display_name: "GPT-4o (穩定)"
    endpoint: ${AZURE_OPENAI_ENDPOINT}
    default_options:
      max_tokens: 12000
    capabilities: [structured_output, vision]
    cost_tier: standard
    recommended_for: [routine_operations, document_generation]

  o3-mini:
    provider: azure_openai
    model_id: "o3-mini"
    display_name: "o3-mini (推理/低成本)"
    endpoint: ${AZURE_OPENAI_ENDPOINT}
    default_options:
      max_tokens: 8000
      reasoning_effort: medium
    capabilities: [structured_output, reasoning]
    cost_tier: economy
    recommended_for: [cost_sensitive_reasoning, batch_analysis]

# ── 自動選擇策略映射 ──
selection_strategies:
  max_reasoning:
    manager_model: claude-opus-4-6
    trigger:
      risk_level: [CRITICAL]
      complexity: [VERY_HIGH]
  balanced:
    manager_model: claude-sonnet-4-6
    trigger:
      risk_level: [HIGH]
      complexity: [HIGH]
  cost_efficient:
    manager_model: gpt-4o
    trigger:
      risk_level: [MEDIUM]
      complexity: [MEDIUM]
  fast_cheap:
    manager_model: claude-haiku-4-5
    trigger:
      risk_level: [LOW]
      complexity: [LOW]

# ── 預設值 ──
defaults:
  manager_model: claude-sonnet-4-6
  fallback_model: gpt-4o
  max_cost_per_task: 2.00  # USD
```

### 3.3 自動選擇策略

| 策略 | 觸發條件 | Manager 模型 | 場景 |
|------|---------|-------------|------|
| 🔴 MAX_REASONING | risk=CRITICAL or complexity=VERY_HIGH | claude-opus-4-6 + thinking 10K | 系統全面崩潰、ERP 遷移評估 |
| 🟠 BALANCED | risk=HIGH or complexity=HIGH | claude-sonnet-4-6 + thinking 5K | 安全事件分析、部署失敗排查 |
| 🟡 COST_EFFICIENT | risk=MEDIUM | gpt-4o | 常規變更管理、服務請求處理 |
| 🟢 FAST_CHEAP | risk=LOW | claude-haiku-4-5 | 資訊查詢、簡單狀態檢查 |
| ⚙️ USER_OVERRIDE | API 參數指定 | 任何已註冊模型 | 開發測試、手動指定 |

---

## 4. 核心實現

### 4.1 AnthropicChatClient — 自建 MAF ChatClient

> **新增檔案**: `integrations/agent_framework/clients/anthropic_chat_client.py`
> **預估 LOC**: ~150
> **依賴**: `anthropic>=0.84.0`（L7 已有）、`agent-framework>=1.0.0rc4`（L6 已有）

```python
"""
AnthropicChatClient — 把 Anthropic API 包裝成 MAF 的 BaseChatClient 介面。
用於 Magentic Manager Agent，提供 Extended Thinking + Structured Output。
"""

from __future__ import annotations
from typing import Any, Optional
from anthropic import AsyncAnthropic
from agent_framework import BaseChatClient  # MAF 核心套件的抽象基類


class AnthropicChatClient(BaseChatClient):
    """把 Anthropic API 包裝成 MAF 的 ChatClient 介面"""

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        api_key: str | None = None,
        thinking_config: dict | None = None,
        max_tokens: int = 16000,
    ):
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model
        self._thinking_config = thinking_config
        self._max_tokens = max_tokens

    async def get_response(self, messages: list, options: Any = None):
        """MAF ChatClient 介面 → Anthropic API"""

        # 1. MAF Message → Anthropic format
        anthropic_messages = self._convert_messages(messages)

        # 2. 構建請求
        kwargs = {
            "model": self._model,
            "messages": anthropic_messages,
            "max_tokens": getattr(options, "max_tokens", self._max_tokens),
        }

        # 3. Extended Thinking
        if self._thinking_config:
            kwargs["thinking"] = self._thinking_config

        # 4. Structured Output (Magentic Ledger 格式)
        # MAF StandardMagenticManager 會在 prompt 中要求 JSON 格式
        # Claude 原生支援 JSON 輸出，無需額外設定

        # 5. 呼叫 API
        response = await self._client.messages.create(**kwargs)

        # 6. 轉換回 MAF 格式
        return self._convert_response(response)

    def _convert_messages(self, maf_messages):
        """MAF Message[] → Anthropic message format"""
        result = []
        for msg in maf_messages:
            role = "assistant" if getattr(msg, "role", "") == "assistant" else "user"
            content = getattr(msg, "content", str(msg))
            result.append({"role": role, "content": content})
        return result

    def _convert_response(self, anthropic_response):
        """Anthropic Response → MAF ChatResponse"""
        # 提取文字內容
        text = ""
        for block in anthropic_response.content:
            if hasattr(block, "text"):
                text += block.text

        # 轉換為 MAF 期望的回應格式
        # ⚠️ 實作時需根據 MAF BaseChatClient 的具體 return type 調整
        # 需檢查 reference/agent-framework/ 中 BaseChatClient.get_response() 的 return type
        return self._build_chat_response(
            text=text,
            model=anthropic_response.model,
            usage={
                "input_tokens": anthropic_response.usage.input_tokens,
                "output_tokens": anthropic_response.usage.output_tokens,
            },
        )

    def _build_chat_response(self, text, model, usage):
        """構建 MAF 標準 ChatResponse 物件"""
        # 需要在實作時檢查 BaseChatClient 的 return type 定義
        # 參考 reference/agent-framework/python/packages/core/agent_framework/
        ...
```

### 4.2 ManagerModelRegistry — 統一模型注冊表

> **新增檔案**: `integrations/hybrid/orchestrator/manager_model_registry.py`
> **預估 LOC**: ~120

```python
"""統一模型注冊表 — 從 YAML 載入，提供 Agent 工廠方法"""

from __future__ import annotations
import os
import yaml
from pathlib import Path
from typing import Any, Optional
from enum import Enum


class CostTier(str, Enum):
    PREMIUM = "premium"
    STANDARD = "standard"
    ECONOMY = "economy"


class ModelConfig:
    """單個模型的配置"""
    def __init__(self, key: str, data: dict):
        self.key = key
        self.provider: str = data["provider"]
        self.model_id: str = data["model_id"]
        self.display_name: str = data.get("display_name", key)
        self.endpoint: str | None = self._resolve_env(data.get("endpoint"))
        self.default_options: dict = data.get("default_options", {})
        self.capabilities: list[str] = data.get("capabilities", [])
        self.cost_tier: CostTier = CostTier(data.get("cost_tier", "standard"))
        self.recommended_for: list[str] = data.get("recommended_for", [])

    @staticmethod
    def _resolve_env(value: str | None) -> str | None:
        if value and value.startswith("${") and value.endswith("}"):
            return os.getenv(value[2:-1])
        return value

    @property
    def supports_thinking(self) -> bool:
        return "extended_thinking" in self.capabilities


class ManagerModelRegistry:
    """統一模型注冊表 — 單例"""

    _instance: Optional[ManagerModelRegistry] = None

    def __init__(self, config_path: str = "config/manager_models.yaml"):
        self._models: dict[str, ModelConfig] = {}
        self._strategies: dict[str, dict] = {}
        self._defaults: dict[str, Any] = {}
        self._load_config(config_path)

    @classmethod
    def get_instance(cls, config_path: str = "config/manager_models.yaml"):
        if cls._instance is None:
            cls._instance = cls(config_path)
        return cls._instance

    def _load_config(self, path: str):
        with open(Path(path)) as f:
            config = yaml.safe_load(f)
        for key, data in config.get("manager_model_registry", {}).items():
            self._models[key] = ModelConfig(key, data)
        self._strategies = config.get("selection_strategies", {})
        self._defaults = config.get("defaults", {})

    def create_manager_agent(self, model_key: str):
        """根據模型 key 建立對應的 Agent 實例"""
        model = self._models[model_key]
        if model.provider == "anthropic":
            return self._create_anthropic_agent(model)
        elif model.provider == "azure_openai":
            return self._create_azure_openai_agent(model)
        raise ValueError(f"Unknown provider: {model.provider}")

    def _create_anthropic_agent(self, model: ModelConfig):
        from integrations.agent_framework.clients.anthropic_chat_client import (
            AnthropicChatClient,
        )
        from agent_framework import Agent

        thinking_config = model.default_options.get("thinking")
        client = AnthropicChatClient(
            model=model.model_id,
            thinking_config=thinking_config,
            max_tokens=model.default_options.get("max_tokens", 16000),
        )
        return Agent(
            chat_client=client,
            name="MagenticManager",
            instructions=self._get_manager_instructions(),
        )

    def _create_azure_openai_agent(self, model: ModelConfig):
        from agent_framework.azure import AzureOpenAIResponsesClient

        # ⚠️ 待驗證：AzureOpenAIResponsesClient 是否有 .as_agent() 方法
        # 需在實作時檢查 reference/agent-framework/ 中的實際 API
        # 可能需要改用 Agent(chat_client=AzureOpenAIResponsesClient(...))
        client = AzureOpenAIResponsesClient(
            model_id=model.model_id,
            endpoint=model.endpoint,
        )
        return Agent(
            chat_client=client,
            name="MagenticManager",
            instructions=self._get_manager_instructions(),
        )

    def _get_manager_instructions(self) -> str:
        return (
            "You are a strategic orchestrator for IT operations. "
            "Break complex tasks into subtasks, assign to specialists, "
            "monitor progress, and replan when blocked. "
            "Think deeply before planning. Consider dependencies and risks."
        )

    def get_model_config(self, model_key: str) -> Optional[ModelConfig]:
        return self._models.get(model_key)

    def list_models(self) -> list[dict]:
        return [{"key": k, "display": m.display_name, "provider": m.provider,
                 "cost_tier": m.cost_tier.value} for k, m in self._models.items()]

    def get_default_model(self) -> str:
        return self._defaults.get("manager_model", "claude-sonnet-4-6")

    def get_fallback_model(self) -> str:
        return self._defaults.get("fallback_model", "gpt-4o")
```

### 4.3 ManagerModelSelector — 自動選擇器

> **新增檔案**: `integrations/hybrid/orchestrator/manager_model_selector.py`
> **預估 LOC**: ~60

```python
"""根據風險等級和複雜度自動選擇最佳 Manager 模型"""

import os
from integrations.orchestration.intent_router.models import RiskLevel
from integrations.hybrid.orchestrator.manager_model_registry import ManagerModelRegistry


class ManagerModelSelector:

    def __init__(self, registry: ManagerModelRegistry):
        self._registry = registry

    def select_model(
        self,
        risk_level: RiskLevel,
        complexity: str = "MEDIUM",
        user_override: str | None = None,
    ) -> str:
        # 1. 用戶顯式指定 — 最高優先
        if user_override and user_override in self._registry._models:
            return user_override

        # 2. 根據風險 + 複雜度匹配策略
        if risk_level == RiskLevel.CRITICAL or complexity == "VERY_HIGH":
            return self._resolve("max_reasoning")
        elif risk_level == RiskLevel.HIGH or complexity == "HIGH":
            return self._resolve("balanced")
        elif risk_level == RiskLevel.MEDIUM:
            return self._resolve("cost_efficient")
        else:
            return self._resolve("fast_cheap")

    def _resolve(self, strategy_name: str) -> str:
        strategy = self._registry._strategies.get(strategy_name, {})
        model_key = strategy.get("manager_model", self._registry.get_default_model())

        if not self._is_available(model_key):
            model_key = self._registry.get_fallback_model()

        return model_key

    def _is_available(self, model_key: str) -> bool:
        model = self._registry._models.get(model_key)
        if not model:
            return False
        if model.provider == "anthropic":
            return bool(os.getenv("ANTHROPIC_API_KEY"))
        elif model.provider == "azure_openai":
            return bool(os.getenv("AZURE_OPENAI_ENDPOINT"))
        return False
```

### 4.4 MagenticBuilderAdapter 修改

> **修改檔案**: `integrations/agent_framework/builders/magentic.py`
> **修改量**: ~30 行（含前置修復）

#### 前置修復：build() 必須正確轉發 manager 配置

現有 `build()` 方法（第 1286-1293 行）的問題：
```python
# ── 現有代碼（有問題）──
# build() 只做 MagenticBuilder(participants=...).build()
# 完全沒有傳遞 manager、plan_review、stall_intervention 配置
self._builder = MagenticBuilder(participants=participant_agents)
workflow = self._builder.build()  # ← manager 配置被忽略
```

#### 修改後

```python
from integrations.hybrid.orchestrator.manager_model_registry import ManagerModelRegistry
from integrations.hybrid.orchestrator.manager_model_selector import ManagerModelSelector

class MagenticBuilderAdapter:
    def __init__(self):
        self._registry = ManagerModelRegistry.get_instance()
        self._selector = ManagerModelSelector(self._registry)
        self._builder = MagenticBuilder(participants=[])
        # ... 其餘現有初始化 ...

    def build(self) -> "MagenticBuilderAdapter":
        """Build the workflow — 修復版：正確轉發 manager 到官方 API"""
        if not self._participants:
            raise ValueError("No participants added to workflow")

        if self._manager is None:
            self._manager = StandardMagenticManager()

        participant_agents = []
        for p in self._participants.values():
            agent = p.metadata.get('agent') if p.metadata else None
            if agent:
                participant_agents.append(agent)

        try:
            if participant_agents:
                self._builder = MagenticBuilder(participants=participant_agents)
                # ⚠️ 修復：正確傳遞 manager 配置到官方 API
                # 官方 API 是 with_standard_manager()，接受 agent 參數
                self._builder = self._builder.with_standard_manager(
                    agent=self._manager,
                    max_stall_count=self._max_stall_count,
                    max_round_count=self._max_round_count,
                )
                if self._enable_plan_review:
                    self._builder = self._builder.with_plan_review(True)
                workflow = self._builder.build()
                self._workflow = workflow
            else:
                self._workflow = None
        except Exception as e:
            logger.warning(f"Official MagenticBuilder.build() failed: {e}")
            self._workflow = None

        self._is_built = True
        return self

    def build_with_model_selection(
        self,
        risk_level: "RiskLevel" = None,
        complexity: str = "MEDIUM",
        manager_model_override: str | None = None,
    ) -> "MagenticBuilderAdapter":
        """使用 ManagerModelSelector 自動選擇模型後構建"""
        from integrations.orchestration.intent_router.models import RiskLevel as RL
        if risk_level is None:
            risk_level = RL.MEDIUM

        model_key = self._selector.select_model(
            risk_level=risk_level,
            complexity=complexity,
            user_override=manager_model_override,
        )
        manager_agent = self._registry.create_manager_agent(model_key)
        self.with_manager(manager_agent)
        return self.build()
```

### 4.5 API 端點

> **新增檔案**: `api/v1/orchestration/manager_model_routes.py`
> **預估 LOC**: ~50

```python
from fastapi import APIRouter, Query
from integrations.hybrid.orchestrator.manager_model_registry import ManagerModelRegistry
from integrations.hybrid.orchestrator.manager_model_selector import ManagerModelSelector

router = APIRouter(prefix="/manager-models", tags=["Manager Models"])

@router.get("/")
async def list_available_models():
    registry = ManagerModelRegistry.get_instance()
    return {"models": registry.list_models(),
            "default": registry.get_default_model()}

@router.post("/test/{model_key}")
async def test_model_connection(model_key: str):
    registry = ManagerModelRegistry.get_instance()
    try:
        agent = registry.create_manager_agent(model_key)
        result = await agent.run("Respond with OK if you can hear me.")
        return {"status": "ok", "model": model_key, "preview": result.text[:100]}
    except Exception as e:
        return {"status": "error", "model": model_key, "error": str(e)}

@router.post("/select")
async def auto_select_model(
    risk_level: str = Query("MEDIUM"),
    complexity: str = Query("MEDIUM"),
):
    from integrations.orchestration.intent_router.models import RiskLevel
    registry = ManagerModelRegistry.get_instance()
    selector = ManagerModelSelector(registry)
    selected = selector.select_model(RiskLevel(risk_level), complexity)
    config = registry.get_model_config(selected)
    return {"selected_model": selected,
            "display_name": config.display_name if config else "Unknown",
            "provider": config.provider if config else "Unknown"}
```

---

## 5. 與現有架構的整合點

### 5.1 影響範圍分析

| 層級 | 影響 | 改動量 |
|------|------|--------|
| L1 Frontend | ❌ 無影響 | 0 |
| L2 API Routes | 新增 1 個 route 模組 | ~50 LOC |
| L3 AG-UI | ❌ 無影響 | 0 |
| L4 Orchestration | ❌ 無影響（路由/風險/HITL 不變） | 0 |
| L5 Hybrid | FrameworkSelector 傳遞 routing_decision（含 risk_level）到 Builder | ~15 行修改 |
| L6 MAF Builder | MagenticBuilderAdapter 使用 Registry + **修復 build() 轉發** | ~30 行修改 |
| L7 Claude SDK | ❌ 無影響（Worker 層不變） | 0 |
| L8 MCP | ❌ 無影響 | 0 |
| L9-L11 | ❌ 無影響 | 0 |

### 5.2 數據流

```
[L4] BusinessIntentRouter.route(user_input)
    → RoutingDecision {intent_category: INCIDENT, sub_intent: system_down, confidence: 0.95}
    （三層瀑布：PatternMatcher → SemanticRouter → LLMClassifier）

[L4] RiskAssessor.assess(routing_decision)
    → RiskLevel.CRITICAL
    （路徑：integrations/orchestration/risk_assessor/assessor.py）

[L4] HITLController.check(risk_level)
    → Approved ✅

[L5] FrameworkSelector.select_framework(user_input, routing_decision=routing_decision)
    → IntentAnalysis {mode: ExecutionMode.SWARM_MODE, framework: SuggestedFramework.MAF}
    （路徑：integrations/hybrid/intent/router.py）

[L5→L6] ManagerModelSelector.select_model(risk_level=CRITICAL)
    → "claude-opus-4-6"
    （路徑：integrations/hybrid/orchestrator/manager_model_selector.py）

[L6] MagenticBuilderAdapter.build_with_model_selection(
    risk_level=CRITICAL,
    manager_model_override=None,  # 或 API 指定
)
    → manager = AnthropicChatClient("claude-opus-4-6", thinking=10K)
    → self._builder.with_standard_manager(agent=manager)
    → workflow = MagenticBuilder(participants=...).build()

[L6] workflow.run(task="APAC Glider ETL Pipeline 連續失敗")
    → Manager(Claude Opus): Task Ledger → 分解為 3 子任務
    → Worker 1 (MCP Azure): 查詢日誌
    → Worker 2 (Claude Thinking): 分析根因
    → Worker 3 (MCP Shell): 執行修復
    → Manager: Progress Ledger → 綜合結果
```

---

## 6. 遷移步驟

| Step | 任務 | 新增/修改 | 風險 | Story Points |
|------|------|----------|------|-------------|
| 0 | **前置修復** `MagenticBuilderAdapter.build()` 正確轉發 manager 配置 | 修改 ~15 行 | MEDIUM | 2 |
| 1 | 建立 `config/manager_models.yaml` | 新增 1 檔案 | LOW | 1 |
| 2 | 實現 `AnthropicChatClient` | 新增 1 檔案 (~150 LOC) | MEDIUM | 3 |
| 3 | 實現 `ManagerModelRegistry` | 新增 1 檔案 (~120 LOC) | LOW | 2 |
| 4 | 實現 `ManagerModelSelector` | 新增 1 檔案 (~60 LOC) | LOW | 1 |
| 5 | 修改 `MagenticBuilderAdapter` 整合 Registry | 修改 ~20 行 | MEDIUM | 2 |
| 6 | 修改 `FrameworkSelector` 傳遞 routing_decision 到 Builder | 修改 ~15 行 | LOW | 1 |
| 7 | 新增 API 端點 `manager_model_routes.py` | 新增 1 檔案 (~50 LOC) | LOW | 1 |
| 8 | 整合測試：先 gpt-4o → sonnet → opus | 測試 | MEDIUM | 3 |
| **合計** | | **新增 5 檔案 (~430 LOC)，修改 3 檔案 (~50 行)** | | **16 SP** |

### 6.1 測試策略

1. **Step 0**: 驗證修復後的 build() 正確呼叫 `with_standard_manager(agent=...)`
2. **Step 1-4**: 單元測試 — Registry 載入 YAML、Selector 策略匹配、ChatClient 格式轉換
3. **Step 5-6**: 整合測試 — MagenticBuilder + 新 Manager Agent 成功構建 workflow
4. **Step 8**: E2E 測試 — 按以下順序逐步驗證：
   - gpt-4o（你已驗證的模型，確認改動不破壞現有功能）
   - claude-haiku-4-5（最便宜，快速驗證 Anthropic 路徑）
   - claude-sonnet-4-6（驗證 Extended Thinking）
   - claude-opus-4-6（驗證完整 Magentic 能力 + Task/Progress Ledger）

### 6.2 Rollback 策略

- YAML 配置中 `defaults.fallback_model: gpt-4o` 確保 Claude 不可用時自動降級
- `ManagerModelSelector._is_available()` 檢查 API key 是否存在
- 不設 `ANTHROPIC_API_KEY` 環境變數 = 系統行為與升級前完全一致

---

## 7. 中期規劃：claude-agent-sdk 整合評估

### 7.1 評估時機

當 Phase 44 的 Manager 升級穩定後（預計 2-3 Sprints），開始評估將 L7 的部分 Worker 遷移到 `claude-agent-sdk`。

### 7.2 評估維度

| 維度 | 現有 L7 自建 | claude-agent-sdk |
|------|-------------|------------------|
| 維護成本 | ~15,400 LOC 需持續維護 | Anthropic 維護 |
| 功能完整度 | 10 個自建 tools | 完整 Claude Code 功能 |
| 部署複雜度 | 純 Python | 需 Node.js（CLI 子進程） |
| Docker 影響 | 無 | 需加 Node.js 到 Docker image |
| Session 管理 | 自建（InMemory） | 內建 session resume |
| Hook 系統 | 4 個自建 hooks | 完整 hook 系統（與 Claude Code 相同） |

### 7.3 建議遷移順序

1. 先在 Docker 中驗證 `claude-agent-sdk` 可運行（加 Node.js）
2. 選一個非關鍵 Worker（如報告生成）做概念驗證
3. 確認效能和穩定性後，逐步遷移其他 Workers
4. 保留 L7 自建系統作為 fallback

---

## 8. 風險與緩解

| 風險 | 影響 | 可能性 | 緩解措施 |
|------|------|--------|---------|
| AnthropicChatClient 格式轉換不完整 | Manager 回應解析失敗 | MEDIUM | 先用簡單 prompt 測試，逐步增加複雜度 |
| Structured Output 格式不兼容 | Task/Progress Ledger 解析失敗 | MEDIUM | Claude 原生支援 JSON，但需驗證 MAF 的解析邏輯 |
| Extended Thinking 增加延遲 | Manager 回應變慢 | LOW | 可調整 budget_tokens，或在 LOW 風險時不啟用 |
| API Key 管理 | 多個 provider 的 key 管理複雜 | LOW | YAML 配置 + 環境變數，DevOps 標準做法 |
| MAF GA 後 BaseChatClient 介面變更 | 自建 ChatClient 需更新 | MEDIUM | GA 發佈時檢查 breaking changes，預計改動量小 |
| 成本失控 | Opus 比 GPT-4o 貴 | LOW | max_cost_per_task 上限 + 自動降級策略 |
| **build() 轉發修復風險** | **改動現有 build() 可能影響已有功能** | **MEDIUM** | **先確認現有 E2E 測試通過，修復後逐步驗證** |

---

## 附錄 A：Magentic Manager 能力對比（升級前 vs 升級後）

| 維度 | 升級前（`StandardMagenticManager()` 預設） | 升級後（Claude Opus + Extended Thinking） |
|------|------------------------------------------|------------------------------------------|
| 推理深度 | StandardMagenticManager 預設行為 | Adaptive thinking 自動調整推理深度 |
| Context 容量 | 取決於底層模型 | 1M tokens + auto compaction |
| 思考過程 | 不可見 | Extended thinking 可觀察推理鏈 |
| 重規劃能力 | 按模板判斷 stall | 深度分析為什麼 stall，生成新策略 |
| 模型切換 | ❌ 無配置（預設） | ✅ YAML 配置 + 自動選擇 + API override |
| 成本控制 | 固定（底層模型定價） | 按風險動態選擇（Haiku → Sonnet → Opus） |
| Fallback | ❌ 無 | ✅ Claude 不可用 → 自動切換 Azure OpenAI |

## 附錄 B：檔案清單

| 操作 | 檔案路徑 | LOC |
|------|---------|-----|
| **前置修復** | `integrations/agent_framework/builders/magentic.py` | ~15 行修改 |
| 新增 | `config/manager_models.yaml` | ~80 |
| 新增 | `integrations/agent_framework/clients/anthropic_chat_client.py` | ~150 |
| 新增 | `integrations/hybrid/orchestrator/manager_model_registry.py` | ~120 |
| 新增 | `integrations/hybrid/orchestrator/manager_model_selector.py` | ~60 |
| 新增 | `api/v1/orchestration/manager_model_routes.py` | ~50 |
| 修改 | `integrations/agent_framework/builders/magentic.py` | ~20 行 |
| 修改 | `integrations/hybrid/intent/router.py` | ~15 行 |
| **合計** | **5 新增 + 2 修改（含前置修復）** | **~430 LOC 新增 + ~50 行修改** |

## 附錄 C：V2.0 校正記錄

以下是 V1.0 → V2.0 的所有校正項目，基於 4 個平行研究 Agent 的交叉驗證結果：

### 嚴重錯誤（已修正）

| # | V1.0 錯誤內容 | V2.0 修正 | 影響位置 |
|---|-------------|----------|---------|
| 1 | Phase 35 架構升級規劃 | → Phase 44 | 標題、第 5-7 行 |
| 2 | `ChatAgent(chat_client=OpenAIChatClient())` 硬編碼 | → `StandardMagenticManager()` 無參數預設 | §1.1、§4.4 |
| 3 | `FrameworkChoice.MAGENTIC` enum | → `SuggestedFramework.MAF` | §5.2 |
| 4 | `integrations/orchestration/risk/assessor.py` | → `integrations/orchestration/risk_assessor/assessor.py` | §4.3 |
| 5 | `integrations/hybrid/intent/framework_selector.py` | → `integrations/hybrid/intent/router.py` | §5.1、附錄 B |
| 6 | `framework_selector.select(intent_result, risk_level)` | → `FrameworkSelector.select_framework(user_input, routing_decision=...)` | §5.2 |
| 7 | `self._builder.with_manager(agent=manager)` 直接轉發 | → build() 未轉發 manager 配置，需前置修復 | §4.4 |

### 中等偏差（已修正）

| # | V1.0 偏差 | V2.0 修正 |
|---|----------|----------|
| 8 | Regex → Embedding → LLM | → PatternMatcher → SemanticRouter → LLMClassifier |
| 9 | 133 Sprints 驗證 | → 148+ Sprints |
| 10 | 15,180 LOC | → ~15,400 LOC |
| 11 | `agent-framework==1.0.0rc4` | → `>=1.0.0rc4,<2.0.0`（範圍約束） |
| 12 | `chat_with_tools` 與 generate 並列 | → chat_with_tools 是可選方法（非 abstract） |
| 13 | 修改 2 檔案 ~35 行 | → 修改 2 檔案 + 前置修復 ~50 行、合計 16 SP |
| 14 | `AzureOpenAIResponsesClient.as_agent()` | → 待驗證，改用 `Agent(chat_client=...)` 模式 |

### 新增前置步驟

- **Step 0（新增）**：修復 `MagenticBuilderAdapter.build()` 正確呼叫 `with_standard_manager(agent=...)` 轉發 manager 配置到官方 MagenticBuilder API

---

> **文件結束**
>
> V2.0 基於 4 個平行研究 Agent 對實際代碼庫的交叉驗證。
> 所有路徑、enum 名稱、方法簽名均已與代碼比對修正。
> 實現時仍需根據 MAF `BaseChatClient` 的具體 return type 完成 `AnthropicChatClient` 的格式轉換。
