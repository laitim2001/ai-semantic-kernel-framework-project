# Agent Team 可行性分析報告

## 日期：2026-03-22
## 分析團隊：5 個 Agent 平行分析

---

## 團隊組成

| Agent | 角色 | 分析重點 |
|-------|------|---------|
| 系統架構師 | 架構整合 | 11 層整合點、Registry 放置、YAML schema |
| 後端架構師 | MAF 可行性 | MagenticBuilder 模型配置、AnthropicLLMService、實作路徑 |
| 效能工程師 | 成本+延遲 | 雙循環開銷、模型定價、SLA 基準 |
| MAF 研究員 | MAF 模型機制 | Builder 的 kernel/model 注入點 |
| LLM 層研究員 | 現有 LLM 層 | Protocol/Factory/Provider 缺口 |

---

## 一致結論：可行，MAF 原生支援

### 系統架構師
- Registry 放 L7 基礎設施層，Selector 作為 L5.5 新子層
- L1-L4 不需改動
- 預估 5 Sprint (~44 SP)
- 最大挑戰：跨 Provider 語意差異（tool calling 格式）
- 完整報告：`docs/07-analysis/Overview/full-codebase-analysis/manager-model-registry-architecture-analysis.md`

### 後端架構師
- 推薦 Registry + Extended Factory 混合方案
- 關鍵橋接：`LLMServiceChatClientAdapter`（IPA Protocol → MAF ChatClient）
- MAF `Agent(chat_client=...)` 原生支援 per-agent 模型
- `MagenticBuilder` 支援 `manager_agent` 參數
- 完整報告：`claudedocs/6-ai-assistant/analysis/magentic-multi-model-registry-analysis.md`

### 效能工程師
- IT 故障排查（4 Workers）每次 ~$0.0006
- Manager（Opus）佔 83% 成本
- 簡單 Q&A 用 Haiku 節省 375 倍
- 建議 risk × complexity 二維矩陣選模型
- MagenticOne 雙循環比直接呼叫多 3-5 倍延遲
- 並行 Worker 可加速 3-4 倍
- 需要 token budget per request
- 完整報告：`claudedocs/6-ai-assistant/analysis/manager-model-registry-performance-analysis.md`

### MAF 研究員
- MAF `BaseChatClient` 是抽象基類，設計上預期被擴展
- `AgentExecutorAdapter` 已有 `_create_client_from_config()` 支援多 provider
- `MagenticBuilderAdapter` 和 `GroupChatBuilderAdapter` 目前未傳遞 per-agent model 配置
- 建議復用 `AgentExecutorAdapter` 的工廠模式

### LLM 層研究員
- 沒有 `AnthropicLLMService`，需要新建
- `anthropic>=0.84.0` 已安裝，env var 已定義
- `claude_sdk/` 是完全獨立路徑，不走 `LLMServiceProtocol`
- `LLMServiceFactory` 只支援 azure/mock，需擴展

---

## 架構整合方案

```
不改動：L1-L4（路由、風險、HITL）
                    ↓
L5:   FrameworkSelector → 輸出擴展 SelectionResult + model_hint
L5.5: ManagerModelSelector（新）→ YAML routing rules → 選模型
                    ↓
L6:   MagenticBuilderAdapter → 注入 per-agent ChatClient
      manager_agent = Agent(chat_client=AnthropicChatClient("claude-opus-4-6"))
      participants  = [Agent(chat_client=AzureOpenAIResponsesClient("gpt-5.2"))]
                    ↓
L7:   ManagerModelRegistry（新）→ YAML 配置多 provider
      AnthropicChatClient（新）→ 實作 BaseChatClient
      LLMServiceFactory → 擴展支援 anthropic/openai
```

## 需要新建的模組（6 個）

| 模組 | 層 | 用途 |
|------|---|------|
| `AnthropicChatClient` | L7 | 實作 MAF `BaseChatClient`（包裝 AsyncAnthropic） |
| `AnthropicLLMService` | L7 | 實作 `LLMServiceProtocol`（給非 MAF 路徑用） |
| `ManagerModelRegistry` | L7 | YAML 配置管理多個 provider/model |
| `LLMServiceChatClientAdapter` | L7 | IPA Protocol → MAF ChatClient 橋接 |
| `ManagerModelSelector` | L5.5 | 根據 intent + risk 選模型的 routing rules |
| `model_registry.yaml` | 配置 | 模型定義 + routing rules |

## 需要修改的模組（4 個）

| 模組 | 改動 |
|------|------|
| `llm/factory.py` | 擴展 provider（anthropic/openai） |
| `core/config.py` | 加入 anthropic_api_key Settings |
| `builders/magentic.py` | build() 注入 per-agent ChatClient |
| `builders/groupchat.py` | Participant 加 model_config |

## 風險

| 風險 | 等級 | 緩解 |
|------|------|------|
| MAF Preview API 變動 | 中 | Adapter 模式隔離 |
| 跨 Provider 語意差異 | 中 | LLMServiceProtocol 抽象層統一 |
| 雙循環成本失控 | 中 | token budget + cost_tier routing |

## 工作量預估

| Sprint | 內容 | SP |
|--------|------|-----|
| 151 | AnthropicLLMService + AnthropicChatClient + Factory 擴展 | ~8 |
| 152 | ManagerModelRegistry + YAML schema + ChatClientAdapter | ~10 |
| 153 | ManagerModelSelector + routing rules + FrameworkSelector 整合 | ~8 |
| 154 | MagenticBuilderAdapter per-agent model + GroupChat 擴展 | ~10 |
| 155 | Swarm UI 整合 + E2E 驗證 + 成本監控 | ~8 |
| | **總計** | **~44 SP** |
