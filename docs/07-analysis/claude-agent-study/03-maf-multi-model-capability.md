# MAF 1.0.0rc4 多模型能力調查

## 日期：2026-03-22
## 調查方式：5 個 Agent Team 平行分析 + 直接 import 驗證

---

## MAF 版本：1.0.0rc4

## 核心發現

### 1. MAF 原生支援 per-agent 模型配置

- `Agent(chat_client=任何ChatClient)` — 每個 Agent 可用不同 LLM
- `MagenticBuilder(manager_agent=..., participants=[...])` — Manager 和 Worker 可用不同模型
- `BaseChatClient` — ChatClient 的抽象基類，設計上預期被擴展

### 2. MAF 只提供 Azure OpenAI 一個 ChatClient 實作

| import 路徑 | 存在？ |
|------------|--------|
| `agent_framework.azure.AzureOpenAIResponsesClient` | ✅ 存在且正在使用 |
| `agent_framework.anthropic.AnthropicClient` | ❌ 不存在 |
| `agent_framework_claude.ClaudeAgent` | ❌ 不存在 |
| `agent_framework.models.anthropic` | ❌ 不存在 |

### 3. 需要自建 AnthropicChatClient

```python
from agent_framework import BaseChatClient

class AnthropicChatClient(BaseChatClient):
    """把 Anthropic API 包裝成 MAF 的 ChatClient 介面"""

    def __init__(self, model: str = "claude-sonnet-4-20250514", api_key: str = ...):
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def get_response(self, messages, options) -> ChatResponse:
        # 轉換 MAF Message → Anthropic format → 呼叫 API → 轉換回 MAF format
        ...
```

### 4. 項目已有的基礎

- `anthropic>=0.84.0` 已在 requirements.txt
- `.env.example` 已定義 `ANTHROPIC_API_KEY`
- `claude_sdk/client.py` 已有 `AsyncAnthropic` 使用經驗
- `AgentExecutorAdapter` 已有 `_create_client_from_config()` 支援多 provider
- `LLMServiceProtocol` 介面已夠用（generate + generate_structured + chat_with_tools）

### 5. 現有 LLM 層的缺口

| 現狀 | 缺口 |
|------|------|
| 只有 `AzureOpenAILLMService` | 沒有 `AnthropicLLMService` |
| `LLMServiceFactory` 只支援 azure/mock | 沒有 anthropic provider |
| `config.py` 沒有 anthropic_api_key Settings | env var 存在但未接入 |
| `claude_sdk/` 是獨立路徑 | 不走 `LLMServiceProtocol` |

## MAF 主要 exports（已驗證）

```
Agent, BaseAgent, BaseChatClient
WorkflowBuilder, Workflow, WorkflowExecutor
Edge, EdgeCondition, FanInEdgeGroup, FanOutEdgeGroup
CheckpointStorage, InMemoryCheckpointStorage, FileCheckpointStorage
FunctionTool, MCPStdioTool, MCPStreamableHTTPTool
Runner, RunnerContext
Message, Role, Content
```

**orchestrations 子模組**（from agent_framework.orchestrations）：
```
MagenticBuilder (+ StandardMagenticManager)
ConcurrentBuilder
GroupChatBuilder (+ GroupChatHandler)
HandoffBuilder
```
