# MagenticOne Multi-Model Registry Integration Analysis

**Date**: 2026-03-22
**Author**: Backend Architect (Claude)
**Status**: Feasibility Analysis Complete

---

## 1. MAF MagenticBuilder Model Configuration Analysis

### 1.1 Official API Discovery

After reading the official MAF source (`reference/agent-framework/.../_magentic.py`), the key findings:

**MagenticBuilder** (`line 2082-2430`):
- `__init__()` takes NO model/kernel parameters — it is model-agnostic
- `participants(**participants: AgentProtocol | Executor)` — each participant is an Agent
- `with_standard_manager(manager=None, *, agent=None, ...)` — the manager takes an `AgentProtocol`

**StandardMagenticManager** (`line 711-860`):
- Constructor: `__init__(self, agent: AgentProtocol, ...)`
- The `agent` parameter is a full `AgentProtocol` instance (typically a `ChatAgent`)
- Internally calls `self._agent.run(messages)` for all LLM calls (planning, progress, final answer)

**ChatAgent** (`line 520-660`):
- Constructor: `__init__(self, chat_client: ChatClientProtocol, ...)`
- `chat_client` is the actual LLM backend (OpenAIChatClient, AzureOpenAIChatClient, etc.)
- Also accepts `model_id` to override the client's default model

### 1.2 Multi-Model Architecture in MAF

The MAF architecture naturally supports multi-model through its layered design:

```
MagenticBuilder
  ├── Manager Agent (ChatAgent + ChatClient_A + model_A)  ← e.g., GPT-4o for planning
  ├── Participant 1 (ChatAgent + ChatClient_B + model_B)  ← e.g., Claude for coding
  ├── Participant 2 (ChatAgent + ChatClient_A + model_C)  ← e.g., GPT-4o-mini for research
  └── Participant 3 (ChatAgent + ChatClient_C + model_D)  ← e.g., Anthropic for review
```

**Each ChatAgent holds its own ChatClient**, so different agents can use completely different LLM providers and models. This is a first-class design, not a workaround.

---

## 2. Current IPA Platform Gap Analysis

### 2.1 LLM Layer Gaps

| Component | Current State | Gap |
|-----------|--------------|-----|
| `LLMServiceProtocol` | `generate()`, `generate_structured()`, `chat_with_tools()` | Protocol is OpenAI-centric but extensible |
| `AzureOpenAILLMService` | Only implementation | Need `AnthropicLLMService`, `OpenAILLMService` |
| `LLMServiceFactory` | Only `azure` and `mock` providers | Need multi-provider registry |
| Singleton pattern | One instance per provider+cache combo | Need per-agent instance support |

### 2.2 MagenticBuilderAdapter Gaps

| Component | Current State | Gap |
|-----------|--------------|-----|
| `StandardMagenticManager` | Uses `agent_executor: Callable` (custom) | Official API uses `agent: AgentProtocol` |
| `MagenticBuilderAdapter.build()` | Creates `MagenticBuilder(participants=...)` | Does NOT pass manager agent with ChatClient |
| Participant agents | Stored as `MagenticParticipant` dataclass | No actual `ChatAgent` instances with ChatClients |
| LLM integration | Manager uses `_execute_prompt()` fallback | Not using MAF's native ChatAgent→ChatClient pipeline |

### 2.3 Bridge Gap: IPA LLMService vs MAF ChatClient

The IPA `LLMServiceProtocol` and MAF `ChatClientProtocol` serve the same purpose but have different interfaces:

```python
# IPA Protocol
class LLMServiceProtocol:
    async def generate(self, prompt: str, ...) -> str
    async def generate_structured(self, prompt: str, output_schema: dict, ...) -> dict
    async def chat_with_tools(self, messages: list, tools: list, ...) -> dict

# MAF Protocol
class ChatClientProtocol:
    async def get_response(self, messages: list[ChatMessage], chat_options: ChatOptions, ...) -> ChatResponse
    def get_streaming_response(self, messages: list[ChatMessage], ...) -> AsyncIterable[ChatResponseUpdate]
```

---

## 3. Recommended Architecture: Multi-Model Registry (Option B+C Hybrid)

### 3.1 Why Option B+C

| Option | Description | Verdict |
|--------|-------------|---------|
| A: Per-agent LLMService injection | Each agent gets its own LLMService | Too low-level, doesn't leverage MAF |
| B: Registry manages multiple providers | Central registry, create on demand | Good for management, but alone misses MAF integration |
| C: Extend LLMServiceFactory | Add multi-provider support | Good for factory, but alone misses registry |
| **B+C**: Registry + Extended Factory | Registry manages configs, Factory creates instances | Best of both — clean separation |

### 3.2 Architecture Overview

```
                     ┌──────────────────────┐
                     │   YAML Agent Config  │
                     │  (per-agent model)   │
                     └──────────┬───────────┘
                                │
                     ┌──────────▼───────────┐
                     │  LLMProviderRegistry  │  ← NEW: Manages provider configs
                     │  ├─ azure/gpt-4o     │
                     │  ├─ azure/gpt-4o-mini│
                     │  ├─ anthropic/claude  │
                     │  └─ openai/gpt-4o    │
                     └──────────┬───────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                  │
    ┌─────────▼──────┐ ┌───────▼────────┐ ┌──────▼───────────┐
    │ LLMServiceFactory│ │MAFChatClient   │ │AnthropicLLMService│
    │ (extended)      │ │Adapter         │ │(new)              │
    │ azure/anthropic │ │LLMService→     │ │                   │
    │ /openai/mock    │ │ChatClientProto │ │                   │
    └────────┬────────┘ └───────┬────────┘ └──────┬───────────┘
             │                  │                  │
             │           ┌──────▼───────┐          │
             │           │  ChatAgent   │          │
             │           │  (MAF)       │          │
             │           └──────┬───────┘          │
             │                  │                  │
             │    ┌─────────────▼──────────────┐   │
             │    │  MagenticBuilderAdapter    │   │
             │    │  ├─ Manager (ChatAgent+LLM)│   │
             │    │  ├─ Participant1 (Agent+LLM)│  │
             │    │  └─ Participant2 (Agent+LLM)│  │
             │    └────────────────────────────┘   │
             │                                     │
             └─────────── IPA Domain ──────────────┘
```

---

## 4. Implementation Plan

### Phase 1: LLM Provider Registry (New Module)

**New file**: `backend/src/integrations/llm/registry.py`

```python
@dataclass
class LLMProviderConfig:
    """Configuration for a single LLM provider instance."""
    provider_id: str          # e.g., "azure-gpt4o", "anthropic-claude-sonnet"
    provider_type: str        # "azure", "anthropic", "openai"
    model_id: str             # deployment name or model name
    endpoint: Optional[str]   # for Azure
    api_key: str              # provider API key
    api_version: Optional[str]
    max_retries: int = 3
    timeout: float = 180.0
    temperature: float = 0.7
    max_tokens: int = 4096
    extra: Dict[str, Any] = field(default_factory=dict)


class LLMProviderRegistry:
    """Central registry for managing multiple LLM provider configurations.

    Thread-safe singleton that manages provider configs and creates
    LLMService instances on demand.
    """
    _instance: Optional["LLMProviderRegistry"] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self):
        self._providers: Dict[str, LLMProviderConfig] = {}
        self._services: Dict[str, LLMServiceProtocol] = {}

    @classmethod
    def get_instance(cls) -> "LLMProviderRegistry":
        ...

    def register(self, config: LLMProviderConfig) -> None:
        """Register a provider configuration."""
        ...

    def get_service(self, provider_id: str) -> LLMServiceProtocol:
        """Get or create an LLMService for the given provider."""
        ...

    def list_providers(self) -> List[str]:
        ...

    def get_config(self, provider_id: str) -> LLMProviderConfig:
        ...
```

### Phase 2: Anthropic LLM Service (New Module)

**New file**: `backend/src/integrations/llm/anthropic.py`

```python
from anthropic import AsyncAnthropic

class AnthropicLLMService:
    """Anthropic Claude LLM Service implementing LLMServiceProtocol.

    Supports generate(), generate_structured(), and chat_with_tools().
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        max_retries: int = 3,
        timeout: float = 180.0,
    ):
        self._client = AsyncAnthropic(api_key=api_key, timeout=timeout)
        self.model = model
        self.max_retries = max_retries

    async def generate(self, prompt: str, ...) -> str:
        """Map to Anthropic messages API."""
        ...

    async def generate_structured(self, prompt: str, output_schema: dict, ...) -> dict:
        """Use Anthropic tool_use for structured output."""
        ...

    async def chat_with_tools(self, messages: list, tools: list, ...) -> dict:
        """Map OpenAI function calling format to Anthropic tool_use."""
        ...
```

### Phase 3: Extend LLMServiceFactory

**Modified file**: `backend/src/integrations/llm/factory.py`

Changes:
1. Add `"anthropic"` and `"openai"` to provider detection
2. Add `_create_anthropic_service()` method
3. Add `_create_openai_service()` method (direct OpenAI, not Azure)
4. Support `provider_id` for registry lookup

```python
# New provider detection
def _detect_provider(cls) -> str:
    # Check Azure first (existing)
    ...
    # Check Anthropic
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    # Check OpenAI direct
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    ...
```

### Phase 4: MAF ChatClient Adapter (Bridge)

**New file**: `backend/src/integrations/agent_framework/adapters/chat_client_adapter.py`

This bridges IPA's `LLMServiceProtocol` to MAF's `ChatClientProtocol`:

```python
from agent_framework._clients import BaseChatClient

class LLMServiceChatClientAdapter(BaseChatClient):
    """Adapts IPA LLMServiceProtocol to MAF ChatClientProtocol.

    Allows any IPA LLMService (Azure, Anthropic, OpenAI) to be used
    as a MAF ChatClient for ChatAgent construction.
    """

    def __init__(self, llm_service: LLMServiceProtocol, model_id: str = "default"):
        self._llm_service = llm_service
        self._model_id = model_id

    async def _inner_get_response(self, *, messages, chat_options, **kwargs) -> ChatResponse:
        """Convert MAF ChatMessage list to LLMService call."""
        # Convert ChatMessage[] -> messages format for chat_with_tools()
        formatted_messages = [
            {"role": msg.role.value, "content": msg.text}
            for msg in messages
        ]
        result = await self._llm_service.chat_with_tools(
            messages=formatted_messages,
            max_tokens=chat_options.max_tokens or 4096,
            temperature=chat_options.temperature or 0.7,
        )
        # Convert response back to ChatResponse
        ...
```

### Phase 5: Update MagenticBuilderAdapter

**Modified file**: `backend/src/integrations/agent_framework/builders/magentic.py`

Key changes to `MagenticBuilderAdapter`:

1. Accept per-agent model configuration
2. Create real `ChatAgent` instances with proper `ChatClient` per participant
3. Use official `StandardMagenticManager(agent=manager_agent)` pattern

```python
class MagenticBuilderAdapter:
    def __init__(self, id: str, ..., model_config: Optional[Dict[str, str]] = None):
        ...
        self._model_config = model_config or {}
        # model_config maps agent_name -> provider_id
        # e.g., {"manager": "azure-gpt4o", "researcher": "anthropic-claude", ...}

    def build(self) -> "MagenticBuilderAdapter":
        registry = LLMProviderRegistry.get_instance()

        # Create ChatAgent for each participant with their configured model
        participant_agents = {}
        for name, participant in self._participants.items():
            provider_id = self._model_config.get(name, "default")
            llm_service = registry.get_service(provider_id)
            chat_client = LLMServiceChatClientAdapter(llm_service, model_id=provider_id)
            agent = ChatAgent(
                chat_client=chat_client,
                name=name,
                description=participant.description,
            )
            participant_agents[name] = agent

        # Create manager agent (may use different model)
        manager_provider = self._model_config.get("manager", "default")
        manager_llm = registry.get_service(manager_provider)
        manager_chat_client = LLMServiceChatClientAdapter(manager_llm)
        manager_agent = ChatAgent(
            chat_client=manager_chat_client,
            name="magentic_manager",
            description="Task planning and coordination manager",
            temperature=0.3,  # Lower temp for planning
        )

        # Build with official API
        self._builder = MagenticBuilder()
        self._builder.participants(**participant_agents)
        self._builder.with_standard_manager(agent=manager_agent, ...)
        workflow = self._builder.build()
        ...
```

### Phase 6: YAML Configuration Mapping

**New/Modified file**: `backend/src/core/config.py` (add LLM provider configs)

```yaml
# Example agent-config.yaml
llm_providers:
  azure-gpt4o:
    type: azure
    endpoint: ${AZURE_OPENAI_ENDPOINT}
    api_key: ${AZURE_OPENAI_API_KEY}
    model_id: gpt-4o
    api_version: "2024-02-01"

  azure-gpt4o-mini:
    type: azure
    endpoint: ${AZURE_OPENAI_ENDPOINT}
    api_key: ${AZURE_OPENAI_API_KEY}
    model_id: gpt-4o-mini

  anthropic-claude-sonnet:
    type: anthropic
    api_key: ${ANTHROPIC_API_KEY}
    model_id: claude-sonnet-4-20250514

  anthropic-claude-haiku:
    type: anthropic
    api_key: ${ANTHROPIC_API_KEY}
    model_id: claude-haiku-3-5-20250620

# Agent model assignments
agent_models:
  default: azure-gpt4o
  magentic:
    manager: azure-gpt4o          # Manager needs strong reasoning
    researcher: azure-gpt4o-mini  # Researcher can use cheaper model
    coder: anthropic-claude-sonnet # Claude excels at coding
    reviewer: azure-gpt4o         # Review needs good judgment
```

---

## 5. File Change Summary

### New Files (6)

| File | Purpose | Estimated LOC |
|------|---------|---------------|
| `backend/src/integrations/llm/registry.py` | LLMProviderRegistry | ~200 |
| `backend/src/integrations/llm/anthropic.py` | AnthropicLLMService | ~350 |
| `backend/src/integrations/llm/openai_direct.py` | OpenAILLMService (direct, not Azure) | ~300 |
| `backend/src/integrations/agent_framework/adapters/chat_client_adapter.py` | LLMService→ChatClient bridge | ~150 |
| `backend/config/llm-providers.yaml` | Provider configuration | ~50 |
| `backend/tests/unit/integrations/llm/test_registry.py` | Registry unit tests | ~200 |

### Modified Files (4)

| File | Changes |
|------|---------|
| `backend/src/integrations/llm/factory.py` | Add anthropic/openai provider creation, registry integration |
| `backend/src/integrations/llm/__init__.py` | Export new classes |
| `backend/src/integrations/agent_framework/builders/magentic.py` | Accept model_config, create real ChatAgents with ChatClients |
| `backend/src/core/config.py` | Add LLM provider config settings |

---

## 6. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Anthropic API format differs from OpenAI | MEDIUM | Careful mapping in AnthropicLLMService, comprehensive test coverage |
| MAF ChatClientProtocol changes in future versions | LOW | Adapter pattern isolates changes |
| Multiple concurrent LLM providers increase complexity | MEDIUM | Registry singleton with thread safety, connection pooling |
| YAML config with secrets | HIGH | Use env var interpolation (`${VAR}`), never store raw keys |
| Performance overhead of adapter layers | LOW | Adapter is thin wrapper, no serialization overhead |
| Existing tests may break | MEDIUM | All changes are additive; existing code paths remain default |

---

## 7. Key Insight: MAF Already Supports This

The most important finding is that **MAF already has first-class multi-model support**. The architecture is:

```
ChatAgent(chat_client=AnyLLMClient) → each agent can have its own model
```

The IPA platform's gap is NOT in MAF, but in:
1. **Missing LLM providers** — only Azure OpenAI exists
2. **Missing bridge** — IPA's `LLMServiceProtocol` is not adapted to MAF's `ChatClientProtocol`
3. **MagenticBuilderAdapter doesn't create real ChatAgents** — uses simplified `_execute_prompt()` fallback

The fix is straightforward: build the bridge adapter (`LLMServiceChatClientAdapter`), add provider implementations (Anthropic, OpenAI direct), and update `MagenticBuilderAdapter` to create real `ChatAgent` instances with per-agent model configs.

---

## 8. Implementation Priority

1. **P0**: `AnthropicLLMService` — unlocks Claude as a provider
2. **P0**: `LLMProviderRegistry` — manages multi-provider configs
3. **P1**: `LLMServiceChatClientAdapter` — bridges IPA→MAF
4. **P1**: Update `MagenticBuilderAdapter.build()` — use real ChatAgents
5. **P2**: YAML config mapping — externalize provider assignments
6. **P2**: `OpenAILLMService` (direct) — for non-Azure OpenAI
